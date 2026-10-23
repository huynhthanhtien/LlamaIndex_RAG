"""Đánh giá truy hồi trên các bộ câu hỏi trong BO_CAU_HOI, chấm theo (văn bản, Điều).

Corpus có nhiều văn bản cùng số Điều (QC SGU 2021, QĐ 3183 sửa đổi...), nên chỉ so số Điều
cho kết quả ảo: mỗi bộ câu hỏi có luật riêng xác định Node nào là đúng.

Khác bản cũ:
  - Mọi chỉ số đi kèm khoảng tin cậy bootstrap và nDCG (eval/metrics.py).
  - Xuất kết quả ra JSON + bảng Markdown (eval/results/) để báo cáo lấy số tự động.
  - Có thể đối chiếu cách đo với `RetrieverEvaluator` của LlamaIndex (--doi-chieu-thu-vien). Đây chỉ là chấm lại
    các bộ dev bằng thư viện, KHÔNG phải chạy tập kiểm chứng eval/test_kiem_chung_*.json; `hit_rate` của thư viện
    tính trên cả top-k (similarity_top_k = 10) nên so với R@10, không phải R@1.
  - So sánh nhiều cấu hình trên cùng bộ câu hỏi và kiểm định McNemar cho từng cặp.

Luật chấm (một Node top-k được tính là đúng khi):
  - Bộ 01 (QC SGU 2021, so_hieu 258): Node phần chính của QC 2021 có `dieu` thuộc nhãn, hoặc mục QĐ 3183 có
    `sua_doi_dieu` thuộc nhãn (mục sửa đổi chính Điều đó cũng là câu trả lời đúng).
  - Bộ 02 (QĐ 3183): chỉ Node có so_hieu 3183, với `sua_doi_dieu` thuộc nhãn hoặc Điều phần chính thuộc nhãn
    (nhãn "2 (QĐ 3183)" là Điều 2 của chính QĐ 3183).
  - Bộ dev (đợt 1–4): nhãn "<tiền tố file>" (văn bản chỉ có 1 Node) hoặc "<tiền tố file>|<Điều>" (Điều
    thuộc phần chính của văn bản đó); "|bh:<Điều>" là Điều của quyết định ban hành, "|sd:<Điều>" là mục sửa đổi.
  - Nhiều nhãn cùng đúng: viết "a;b" hoặc `"dieu_dung": ["a", "b"]`; Node khớp một nhãn bất kỳ là đúng.
    JSON cũ có `dieu_dung` là chuỗi (định dạng tập kiểm chứng K1/K2) vẫn đọc được như trước.

Cách dùng (từ thư mục gốc repo):
    RAG_PROFILE=server RAG_EMBED_DEVICE=cpu venv/bin/python eval/evaluate.py
    ... eval/evaluate.py --cau-hinh vector,rerank,hybrid
    ... eval/evaluate.py --cau-hinh vector --doi-chieu-thu-vien
    ... eval/evaluate.py --tap-kiem-chung     # tập kiểm chứng: chỉ chạy sau `eval/dong_bang.py tao`, đúng một lần
"""
import argparse
import dataclasses
import gc
import json
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index
from luat_cham import BO_CAU_HOI, BO_KIEM_CHUNG, ChamDung, chuan_hoa_nhan
from metrics import bootstrap_ci, hang_dau_tien, mcnemar, mrr, ndcg_at_k, p95, recall_at_k
from retriever import get_postprocessors, get_retriever, node_label, search

TimKiem = Callable[[str], list[NodeWithScore]]
KS = (1, 3, 5, 10)


# Tên cấu hình -> thay đổi so với config gốc. Dùng cho bảng ablation trong báo cáo.
# Ghi tường minh use_rerank / loc_phien_ban vì profile server đã bật cả hai mặc định (16/10).
_TAT = {"use_rerank": False, "loc_phien_ban": False}
CAU_HINH: dict[str, dict[str, object]] = {
    "vector": dict(_TAT),
    "rerank": {"use_rerank": True, "loc_phien_ban": False},
    # rerank giữ lại cả 10 Node (thay vì top_n=3) để đo được R@5/R@10 sau khi xếp hạng lại
    "rerank-top10": {"use_rerank": True, "reranker_top_n": 10, "loc_phien_ban": False},
    "loc": {"use_rerank": False, "loc_phien_ban": True},
    "rerank+loc": {"use_rerank": True, "loc_phien_ban": True},
    "rerank-top10+loc": {"use_rerank": True, "reranker_top_n": 10, "loc_phien_ban": True},
    "hybrid": {"use_hybrid": True, **_TAT},
    "hybrid+rerank": {"use_hybrid": True, "use_rerank": True, "loc_phien_ban": False},
    "hybrid+rerank+loc": {"use_hybrid": True, "use_rerank": True, "loc_phien_ban": True},
    # Biến thể để tách nguyên nhân: nếu RRF (trọng số bằng nhau) là thủ phạm thì cấu hình này
    # (relative_score, ưu tiên vector 3:1) phải tốt hơn hybrid thuần.
    "hybrid-uu-tien-vector": {"use_hybrid": True, "fusion_mode": "relative_score", "vector_weight": 3.0,
                              "bm25_weight": 1.0, **_TAT},
}


@dataclass
class KetQua:
    bo_cau_hoi: str
    cau_hinh: str
    mo_ta: dict[str, object]
    so_cau: int
    hang: list[int | None] = field(default_factory=lambda: [])
    thoi_gian_ms: list[float] = field(default_factory=lambda: [])
    top1: Counter[str] = field(default_factory=lambda: Counter[str]())
    ngoai_top3: list[tuple[str, str, list[str]]] = field(default_factory=lambda: [])

    # --- các chỉ số ---
    def hit(self, k: int) -> list[bool]:
        return [r is not None and r <= k for r in self.hang]

    def recall(self, k: int) -> float:
        return recall_at_k(self.hang, k)

    def mrr(self, toi_da: int | None = None) -> float:
        return mrr(self.hang, toi_da)

    def ndcg(self, k: int) -> float:
        return ndcg_at_k(self.hang, k)

    def ci(self, k: int) -> tuple[float, float, float]:
        return bootstrap_ci([1.0 if h else 0.0 for h in self.hit(k)])

    def to_dict(self) -> dict[str, object]:
        return {
            "bo_cau_hoi": self.bo_cau_hoi,
            "cau_hinh": self.cau_hinh,
            "cau_hinh_chi_tiet": self.mo_ta,
            "so_cau": self.so_cau,
            "hang": self.hang,
            "thoi_gian_ms": [round(t, 2) for t in self.thoi_gian_ms],
            "thoi_gian_trung_binh_ms": round(sum(self.thoi_gian_ms) / len(self.thoi_gian_ms), 1) if self.thoi_gian_ms else 0.0,
            "thoi_gian_p95_ms": round(p95(self.thoi_gian_ms), 1),
            "top1_van_ban": dict(self.top1.most_common()),
            "ngoai_top3": [{"cau_hoi": q, "dung": d, "top3": got} for q, d, got in self.ngoai_top3],
            "chi_so": {
                **{f"R@{k}": round(self.recall(k), 4) for k in KS},
                **{f"R@{k}_ci95": [round(x, 4) for x in self.ci(k)] for k in KS},
                "MRR": round(self.mrr(), 4),
                "MRR@3": round(self.mrr(3), 4),
                **{f"nDCG@{k}": round(self.ndcg(k), 4) for k in (1, 3, 10)},
            },
        }


def giai_phong_gpu() -> None:
    gc.collect()
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def doc_cau_hoi(ten_file: str) -> list[dict[str, str]]:
    ds: list[dict[str, str | list[str]]] = json.loads((ROOT / "eval" / ten_file).read_text(encoding="utf-8"))
    # Chỉ dieu_dung có thể là list; các trường khác (question, ...) là chuỗi nên chuan_hoa_nhan giữ nguyên.
    return [{k: chuan_hoa_nhan(v) for k, v in q.items()} for q in ds]


def danh_gia(ten_file: str, dung: ChamDung, tim: TimKiem, cau_hinh: str, mo_ta: dict[str, object]) -> KetQua:
    questions = doc_cau_hoi(ten_file)
    kq = KetQua(ten_file, cau_hinh, mo_ta, len(questions))
    for q in questions:
        # Truyền nguyên nhãn: nhãn dev có dấu cách ("TB so 2567", "HD-Quy trinh phuc khao"); trước đây
        # split()[0] cắt còn "TB" / "HD-Quy" nên tiền tố khớp lỏng (TB_ChuanDauRa cũng tính là đúng).
        d = q["dieu_dung"]
        t0 = time.perf_counter()
        res = tim(q["question"])
        kq.thoi_gian_ms.append((time.perf_counter() - t0) * 1000)
        kq.hang.append(hang_dau_tien(len(res), lambda i: dung(res[i], d)))
        if res:
            kq.top1[node_label(res[0]).split(" – ")[0][:40]] += 1
        if kq.hang[-1] is None or kq.hang[-1] > 3:
            kq.ngoai_top3.append((q["question"], q["dieu_dung"], [node_label(n) for n in res[:3]]))
    return kq


def in_ket_qua(kq: KetQua) -> None:
    chi_so = "  ".join(f"R@{k}={kq.recall(k):.0%} [{kq.ci(k)[1]:.0%}–{kq.ci(k)[2]:.0%}]" for k in KS)
    print(f"{kq.bo_cau_hoi} | {kq.cau_hinh} ({kq.so_cau} câu): {chi_so}")
    print(f"  MRR={kq.mrr():.3f}  MRR@3={kq.mrr(3):.3f}  nDCG@1={kq.ndcg(1):.3f}  "
          f"thời gian/câu: {sum(kq.thoi_gian_ms) / len(kq.thoi_gian_ms):.1f} ms (p95 {p95(kq.thoi_gian_ms):.1f} ms)")
    print(f"  Văn bản của Node top-1: {kq.top1.most_common()}")
    for q, d, got in kq.ngoai_top3:
        print(f"  ngoài top-3: {q} | đúng Điều {d} | top-3: {got}")
    print()


def doi_chieu_thu_vien(cfg: RAGConfig, ten_file: str, dung: ChamDung, index: VectorStoreIndex) -> dict[str, float]:
    """Chấm lại cùng bộ câu hỏi bằng `RetrieverEvaluator` của LlamaIndex để đối chiếu hai cách đo.

    hit_rate = có Node đúng trong cả similarity_top_k Node -> tương ứng R@k với k = similarity_top_k.
    """
    from llama_index.core.evaluation import RetrieverEvaluator

    ev = RetrieverEvaluator.from_metric_names(["mrr", "hit_rate"], retriever=get_retriever(index, cfg))
    diem: dict[str, list[float]] = {"mrr": [], "hit_rate": []}
    for q in doc_cau_hoi(ten_file):
        d = q["dieu_dung"]
        mong_doi = [nid for nid, n in index.docstore.docs.items() if dung(NodeWithScore(node=n), d)]
        if not mong_doi:
            continue
        res = ev.evaluate(query=q["question"], expected_ids=mong_doi)
        for ten, gt in res.metric_dict.items():
            diem[ten].append(float(gt.score))
    return {ten: (sum(v) / len(v) if v else 0.0) for ten, v in diem.items()}


def bang_markdown(ds: list[KetQua]) -> str:
    dong = ["| Bộ câu hỏi | Cấu hình | R@1 | R@3 | R@10 | MRR | nDCG@3 | ms/câu |",
            "|---|---|---|---|---|---|---|---|"]
    for kq in ds:
        dong.append(
            f"| {kq.bo_cau_hoi} | {kq.cau_hinh} | {kq.recall(1):.1%} | {kq.recall(3):.1%} | {kq.recall(10):.1%} | "
            f"{kq.mrr():.3f} | {kq.ndcg(3):.3f} | {sum(kq.thoi_gian_ms) / len(kq.thoi_gian_ms):.0f} |"
        )
    return "\n".join(dong) + "\n"


def so_sanh_cap(ds: list[KetQua]) -> None:
    """Kiểm định McNemar cho từng cặp cấu hình trên cùng bộ câu hỏi (mức R@1)."""
    theo_bo: dict[str, list[KetQua]] = {}
    for kq in ds:
        theo_bo.setdefault(kq.bo_cau_hoi, []).append(kq)
    for bo, ds_bo in theo_bo.items():
        if len(ds_bo) < 2:
            continue
        print(f"So sánh cặp (McNemar, R@1) — {bo}:")
        for i in range(len(ds_bo)):
            for j in range(i + 1, len(ds_bo)):
                a, b = ds_bo[i], ds_bo[j]
                bb, cc, p = mcnemar(a.hit(1), b.hit(1))
                print(f"  {a.cau_hinh} vs {b.cau_hinh}: chỉ {a.cau_hinh} đúng {bb}, chỉ {b.cau_hinh} đúng {cc}, p={p:.3f}")
        print()


def chay_tap_kiem_chung(chay_lai: bool) -> None:
    """Chạy tập kiểm chứng ĐÚNG MỘT LẦN bằng cấu hình đã đóng băng (eval/dong_bang.py), báo riêng từng bộ và từng loại câu.

    Chạy lại sau khi đã nhìn kết quả thì tập này không còn là tập kiểm chứng (đã có thể dùng để chỉnh): phải bật
    --chay-lai-kiem-chung, kết quả được đánh dấu "chay_lai" để báo cáo ghi rõ.
    """
    from dong_bang import MANIFEST, kiem_khop

    khop, dong = kiem_khop()
    if not khop:
        sys.exit("Trạng thái hiện tại không khớp manifest đóng băng, không chạy tập kiểm chứng:\n" + "\n".join(dong))
    json_out = ROOT / "eval" / "results" / "truy-hoi-kiem-chung.json"
    if json_out.exists() and not chay_lai:
        sys.exit(f"Tập kiểm chứng đã chạy ({json_out.relative_to(ROOT)}). Chỉ chạy lại khi thật sự cần, bằng "
                 "--chay-lai-kiem-chung, và ghi rõ trong báo cáo.")

    cfg = get_config()  # cấu hình chốt của profile, đúng cấu hình đã ghi trong manifest
    index = build_or_load_index(cfg)
    retriever = get_retriever(index, cfg)
    posts = get_postprocessors(cfg, index)
    tim = lambda q: search(index, cfg, q, postprocessors=posts, retriever=retriever)  # noqa: E731
    tim("khởi động")
    tat_ca: list[KetQua] = []
    theo_loai: dict[str, list[int | None]] = {}
    for ten_file, dung in BO_KIEM_CHUNG:
        kq = danh_gia(ten_file, dung, tim, "chot-dong-bang", cfg.mo_ta())
        in_ket_qua(kq)
        tat_ca.append(kq)
        for q, hang in zip(doc_cau_hoi(ten_file), kq.hang, strict=True):
            theo_loai.setdefault(q.get("loai", "-"), []).append(hang)

    dong_loai = ["| Loại câu | Số câu | R@1 | R@3 | MRR |", "|---|---|---|---|---|"]
    for loai, hang in sorted(theo_loai.items()):
        dong_loai.append(f"| {loai} | {len(hang)} | {recall_at_k(hang, 1):.1%} | {recall_at_k(hang, 3):.1%} | "
                         f"{mrr(hang):.3f} |")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    json_out.write_text(json.dumps({
        "thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chay_lai": chay_lai,
        "dong_bang": {"thoi_diem": manifest.get("thoi_diem"), "commit": manifest.get("commit")},
        "ket_qua": [k.to_dict() for k in tat_ca],
        "theo_loai": {loai: {"so_cau": len(h), "R@1": round(recall_at_k(h, 1), 4), "R@3": round(recall_at_k(h, 3), 4),
                             "MRR": round(mrr(h), 4)} for loai, h in theo_loai.items()},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    md = (f"# Tập kiểm chứng — cấu hình đóng băng {manifest.get('thoi_diem')} (commit {manifest.get('commit')})"
          f"{' — CHẠY LẠI' if chay_lai else ''}\n\n" + bang_markdown(tat_ca) + "\n### Theo loại câu\n\n"
          + "\n".join(dong_loai) + "\n")
    json_out.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md)
    print(f"Đã ghi {json_out.relative_to(ROOT)} và .md")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="vector",
                    help=f"danh sách cấu hình, cách nhau dấu phẩy. Có: {', '.join(CAU_HINH)}")
    # "--kiem-chung" giữ làm tên cũ; tên mới tránh nhầm với tập kiểm chứng eval/test_kiem_chung_*.json
    ap.add_argument("--doi-chieu-thu-vien", "--kiem-chung", dest="doi_chieu", action="store_true",
                    help="chấm lại bằng RetrieverEvaluator của LlamaIndex (chỉ cấu hình vector; hit_rate so với R@10)")
    ap.add_argument("--cutoff", type=float, default=None, help="đặt similarity_cutoff cho mọi cấu hình")
    ap.add_argument("--tap-kiem-chung", action="store_true",
                    help="chạy tập kiểm chứng bằng cấu hình đã đóng băng (eval/dong_bang.py), bỏ qua --cau-hinh")
    ap.add_argument("--chay-lai-kiem-chung", action="store_true", help="cho phép chạy lại tập kiểm chứng (ghi rõ lý do)")
    ap.add_argument("--json-out", default=str(ROOT / "eval" / "results" / "truy-hoi.json"))
    ap.add_argument("--md-out", default=str(ROOT / "eval" / "results" / "truy-hoi.md"))
    args = ap.parse_args()
    if args.tap_kiem_chung:
        chay_tap_kiem_chung(args.chay_lai_kiem_chung)
        return

    ten_cau_hinh = [t.strip() for t in args.cau_hinh.split(",") if t.strip()]
    la = [t for t in ten_cau_hinh if t not in CAU_HINH]
    if la:
        sys.exit(f"Cấu hình không hợp lệ: {la}. Chỉ nhận: {list(CAU_HINH)}")

    goc = get_config()
    index = build_or_load_index(goc)
    print(f"Index: {goc.persist_dir} | {len(index.docstore.docs)} Node | embedding: {goc.embed_model_name}\n")

    tat_ca: list[KetQua] = []
    for ten in ten_cau_hinh:
        thay_doi = dict(CAU_HINH[ten])
        if args.cutoff is not None:
            thay_doi["similarity_cutoff"] = args.cutoff
        cfg = dataclasses.replace(goc, **thay_doi)
        retriever = get_retriever(index, cfg)
        posts = get_postprocessors(cfg, index)
        tim = lambda q, r=retriever, p=posts: search(index, cfg, q, postprocessors=p, retriever=r)  # noqa: E731
        tim("khởi động")  # lần đầu chậm hơn (khởi tạo CUDA kernel / nạp model), không tính vào thời gian
        print(f"=== {ten} ===")
        for ten_file, dung in BO_CAU_HOI:
            kq = danh_gia(ten_file, dung, tim, ten, cfg.mo_ta())
            in_ket_qua(kq)
            tat_ca.append(kq)
            if args.doi_chieu and ten == "vector":
                kq_tv = doi_chieu_thu_vien(cfg, ten_file, dung, index)
                k = cfg.similarity_top_k
                print(f"  Đối chiếu bằng RetrieverEvaluator của LlamaIndex: "
                      f"hit_rate={kq_tv.get('hit_rate', 0):.3f} (so với R@{k}={kq.recall(k):.3f}), "
                      f"mrr={kq_tv.get('mrr', 0):.3f} (so với MRR={kq.mrr():.3f})\n")
        # Mỗi cấu hình rerank nạp một CrossEncoder riêng; không giải phóng thì cấu hình rerank thứ hai tràn card 4 GB
        del tim, posts, retriever
        giai_phong_gpu()

    so_sanh_cap(tat_ca)

    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(
        json.dumps({"thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"), "ket_qua": [k.to_dict() for k in tat_ca]},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    Path(args.md_out).write_text(bang_markdown(tat_ca), encoding="utf-8")
    print(f"Đã ghi {args.json_out} và {args.md_out}")


if __name__ == "__main__":
    main()
