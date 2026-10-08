"""Đánh giá truy hồi trên 2 bộ câu hỏi, chấm theo (văn bản, Điều).

Corpus có nhiều văn bản cùng số Điều (QC SGU 2021, QĐ 3183 sửa đổi...), nên chỉ so số Điều
cho kết quả ảo: mỗi bộ câu hỏi có luật riêng xác định Node nào là đúng.

Khác bản cũ:
  - Mọi chỉ số đi kèm khoảng tin cậy bootstrap và nDCG (eval/metrics.py).
  - Xuất kết quả ra JSON + bảng Markdown (eval/results/) để báo cáo lấy số tự động.
  - Có thể kiểm chứng chéo bằng `RetrieverEvaluator` của LlamaIndex (--kiem-chung).
  - So sánh nhiều cấu hình trên cùng bộ câu hỏi và kiểm định McNemar cho từng cặp.

Cách dùng (từ thư mục gốc repo):
    RAG_PROFILE=server RAG_EMBED_DEVICE=cpu venv/bin/python eval/evaluate.py
    ... eval/evaluate.py --cau-hinh vector,rerank,hybrid
    ... eval/evaluate.py --cau-hinh vector --kiem-chung
"""
import argparse
import dataclasses
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
from metrics import bootstrap_ci, hang_dau_tien, mcnemar, mrr, ndcg_at_k, p95, recall_at_k
from retriever import get_postprocessors, get_retriever, node_label, search

ChamDung = Callable[[NodeWithScore, str], bool]
TimKiem = Callable[[str], list[NodeWithScore]]
KS = (1, 3, 5, 10)


def dung_bo_01(n: NodeWithScore, d: str) -> bool:
    """Bộ 01 hỏi về QC SGU 2021: đúng là Điều đó (phần chính) hoặc mục QĐ 3183 sửa đổi chính Điều đó."""
    m = n.node.metadata
    goc = str(m.get("file", "")).startswith("25_") and m.get("phan") == "chinh" and m.get("dieu") == d
    sua_doi = str(m.get("file", "")).startswith("QD 3183") and m.get("sua_doi_dieu") == d
    return bool(goc or sua_doi)


def dung_bo_02(n: NodeWithScore, d: str) -> bool:
    """Bộ 02 hỏi về nội dung sửa đổi: đúng là mục QĐ 3183 sửa đổi Điều đó; nhãn "2 (QĐ 3183)" là Điều 2 của QĐ."""
    m = n.node.metadata
    if not str(m.get("file", "")).startswith("QD 3183"):
        return False
    return bool(m.get("sua_doi_dieu") == d or (m.get("phan") == "chinh" and m.get("dieu") == d))


BO_CAU_HOI: list[tuple[str, ChamDung]] = [
    ("test_questions_01.json", dung_bo_01),
    ("test_questions_02.json", dung_bo_02),
]

# Tên cấu hình -> thay đổi so với config gốc. Dùng cho bảng ablation trong báo cáo.
CAU_HINH: dict[str, dict[str, object]] = {
    "vector": {},
    "rerank": {"use_rerank": True},
    "hybrid": {"use_hybrid": True},
    "hybrid+rerank": {"use_hybrid": True, "use_rerank": True},
    # Biến thể để tách nguyên nhân: nếu RRF (trọng số bằng nhau) là thủ phạm thì cấu hình này
    # (relative_score, ưu tiên vector 3:1) phải tốt hơn hybrid thuần.
    "hybrid-uu-tien-vector": {"use_hybrid": True, "fusion_mode": "relative_score", "vector_weight": 3.0, "bm25_weight": 1.0},
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


def doc_cau_hoi(ten_file: str) -> list[dict[str, str]]:
    return json.loads((ROOT / "eval" / ten_file).read_text(encoding="utf-8"))


def danh_gia(ten_file: str, dung: ChamDung, tim: TimKiem, cau_hinh: str, mo_ta: dict[str, object]) -> KetQua:
    questions = doc_cau_hoi(ten_file)
    kq = KetQua(ten_file, cau_hinh, mo_ta, len(questions))
    for q in questions:
        d = q["dieu_dung"].split()[0]
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


def kiem_chung_thu_vien(cfg: RAGConfig, ten_file: str, dung: ChamDung, index: VectorStoreIndex) -> dict[str, float]:
    """Chấm lại cùng bộ câu hỏi bằng `RetrieverEvaluator` của LlamaIndex để đối chiếu hai cách đo."""
    from llama_index.core.evaluation import RetrieverEvaluator

    ev = RetrieverEvaluator.from_metric_names(["mrr", "hit_rate"], retriever=get_retriever(index, cfg))
    diem: dict[str, list[float]] = {"mrr": [], "hit_rate": []}
    for q in doc_cau_hoi(ten_file):
        d = q["dieu_dung"].split()[0]
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="vector",
                    help=f"danh sách cấu hình, cách nhau dấu phẩy. Có: {', '.join(CAU_HINH)}")
    ap.add_argument("--kiem-chung", action="store_true", help="chấm chéo bằng RetrieverEvaluator của LlamaIndex (chỉ cấu hình vector)")
    ap.add_argument("--cutoff", type=float, default=None, help="đặt similarity_cutoff cho mọi cấu hình")
    ap.add_argument("--json-out", default=str(ROOT / "eval" / "results" / "truy-hoi.json"))
    ap.add_argument("--md-out", default=str(ROOT / "eval" / "results" / "truy-hoi.md"))
    args = ap.parse_args()

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
        posts = get_postprocessors(cfg)
        tim = lambda q, r=retriever, p=posts: search(index, cfg, q, postprocessors=p, retriever=r)  # noqa: E731
        tim("khởi động")  # lần đầu chậm hơn (khởi tạo CUDA kernel / nạp model), không tính vào thời gian
        print(f"=== {ten} ===")
        for ten_file, dung in BO_CAU_HOI:
            kq = danh_gia(ten_file, dung, tim, ten, cfg.mo_ta())
            in_ket_qua(kq)
            tat_ca.append(kq)
            if args.kiem_chung and ten == "vector":
                kq_tv = kiem_chung_thu_vien(cfg, ten_file, dung, index)
                print(f"  Kiểm chứng bằng RetrieverEvaluator của LlamaIndex: "
                      f"hit_rate={kq_tv.get('hit_rate', 0):.3f}, mrr={kq_tv.get('mrr', 0):.3f}\n")

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
