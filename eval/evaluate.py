"""Đánh giá truy hồi trên 2 bộ câu hỏi, chấm theo (văn bản, Điều).

Corpus có nhiều văn bản cùng số Điều (QC SGU 2021, QĐ 3183 sửa đổi...), nên chỉ so số Điều cho kết quả ảo:
mỗi bộ câu hỏi có luật riêng xác định Node nào là đúng.

Cách dùng (từ thư mục gốc repo):
    RAG_PROFILE=server venv/bin/python eval/evaluate.py            # vector top-k
    RAG_PROFILE=server venv/bin/python eval/evaluate.py --rerank   # + so sánh vector vs vector + rerank
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

from llama_index.core.schema import NodeWithScore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import get_config
from index_builder import build_or_load_index
from retriever import get_postprocessors, node_label, search

ChamDung = Callable[[NodeWithScore, str], bool]
TimKiem = Callable[[str], list[NodeWithScore]]


def dung_bo_01(n: NodeWithScore, d: str) -> bool:
    """Bộ 01 hỏi về QC SGU 2021: đúng là Điều đó (phần chính) hoặc mục QĐ 3183 sửa đổi chính Điều đó."""
    m = n.node.metadata
    goc = str(m["file"]).startswith("25_") and m["phan"] == "chinh" and m["dieu"] == d
    sua_doi = str(m["file"]).startswith("QD 3183") and m["sua_doi_dieu"] == d
    return goc or sua_doi


def dung_bo_02(n: NodeWithScore, d: str) -> bool:
    """Bộ 02 hỏi về nội dung sửa đổi: đúng là mục QĐ 3183 sửa đổi Điều đó; nhãn "2 (QĐ 3183)" là Điều 2 của QĐ."""
    m = n.node.metadata
    if not str(m["file"]).startswith("QD 3183"):
        return False
    return m["sua_doi_dieu"] == d or (m["phan"] == "chinh" and m["dieu"] == d)


BO_CAU_HOI: list[tuple[str, ChamDung]] = [
    ("test_questions_01.json", dung_bo_01),
    ("test_questions_02.json", dung_bo_02),
]


@dataclass
class KetQua:
    bo_cau_hoi: str
    so_cau: int
    hang: list[int | None] = field(default_factory=lambda: [])          # hạng Node đúng đầu tiên mỗi câu
    thoi_gian_ms: list[float] = field(default_factory=lambda: [])
    top1: Counter[str] = field(default_factory=lambda: Counter[str]())
    ngoai_top3: list[tuple[str, str, list[str]]] = field(default_factory=lambda: [])

    def recall(self, k: int) -> float:
        return sum(1 for r in self.hang if r is not None and r <= k) / self.so_cau

    def mrr(self, toi_da: int | None = None) -> float:
        return sum(1 / r for r in self.hang if r is not None and (toi_da is None or r <= toi_da)) / self.so_cau


def danh_gia(ten_file: str, dung: ChamDung, tim: TimKiem) -> KetQua:
    questions = json.loads((ROOT / "eval" / ten_file).read_text(encoding="utf-8"))
    kq = KetQua(ten_file, len(questions))
    for q in questions:
        d = q["dieu_dung"].split()[0]
        t0 = time.perf_counter()
        res = tim(q["question"])
        kq.thoi_gian_ms.append((time.perf_counter() - t0) * 1000)
        rank = next((i for i, n in enumerate(res, 1) if dung(n, d)), None)
        kq.hang.append(rank)
        kq.top1[node_label(res[0]).split(" – ")[0][:40]] += 1
        if rank is None or rank > 3:
            kq.ngoai_top3.append((q["question"], q["dieu_dung"], [node_label(n) for n in res[:3]]))
    return kq


def in_ket_qua(kq: KetQua, ks: tuple[int, ...]) -> None:
    print(f"{kq.bo_cau_hoi} ({kq.so_cau} câu): " + "  ".join(f"R@{k}={kq.recall(k):.0%}" for k in ks)
          + f"  MRR={kq.mrr():.3f}")
    print("  Văn bản của Node top-1:", kq.top1.most_common())
    for q, d, got in kq.ngoai_top3:
        print(f"  ngoài top-3: {q} | đúng Điều {d} | top-3: {got}")
    tg = sorted(kq.thoi_gian_ms)
    print(f"  Thời gian/câu: trung bình {sum(tg) / len(tg):.1f} ms, p95 {tg[max(0, int(len(tg) * 0.95) - 1)]:.1f} ms\n")


def chay(tim: TimKiem, ks: tuple[int, ...]) -> list[KetQua]:
    tim("khởi động")  # lần đầu chậm hơn (khởi tạo CUDA kernel), không tính vào thời gian
    ket_qua = [danh_gia(f, dung, tim) for f, dung in BO_CAU_HOI]
    for kq in ket_qua:
        in_ket_qua(kq, ks)
    return ket_qua


def in_so_sanh(vector: list[KetQua], rerank: list[KetQua]) -> None:
    """Bảng vector vs vector + rerank trên cùng thang (rerank chỉ giữ top-n nên dùng R@1, R@3, MRR@3)."""
    print(f"{'Bộ câu hỏi':24} {'Chỉ số':7} {'Vector':>7} {'+Rerank':>8} {'Chênh':>7}")
    for a, b in zip(vector, rerank):
        for ten, x, y in (("R@1", a.recall(1), b.recall(1)), ("R@3", a.recall(3), b.recall(3)),
                          ("MRR@3", a.mrr(3), b.mrr(3))):
            print(f"{a.bo_cau_hoi:24} {ten:7} {x:7.1%} {y:8.1%} {y - x:+7.1%}")

    def trung_binh(ds: list[KetQua]) -> float:
        return sum(t for k in ds for t in k.thoi_gian_ms) / sum(len(k.thoi_gian_ms) for k in ds)

    print(f"{'Thời gian trung bình':32} {trung_binh(vector):6.1f}ms {trung_binh(rerank):6.1f}ms")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerank", action="store_true", help="đánh giá thêm vector + rerank và so sánh")
    args = ap.parse_args()

    cfg = dataclasses.replace(get_config(), use_rerank=False)
    index = build_or_load_index(cfg)
    print(f"Index: {cfg.persist_dir} | {len(index.docstore.docs)} Node | embedding: {cfg.embed_model_name}\n")

    print(f"=== Vector top-{cfg.similarity_top_k} ===")
    vector = chay(lambda q: search(index, cfg, q, postprocessors=[]), (1, 3, 5, 10))
    if not args.rerank:
        return

    cfg_rr = dataclasses.replace(cfg, use_rerank=True)
    rerankers = get_postprocessors(cfg_rr)
    if not rerankers:
        sys.exit(f"Profile {cfg.name!r} không có reranker_model_name — dùng RAG_PROFILE=server")
    print(f"=== Vector top-{cfg.similarity_top_k} + rerank top-{cfg.reranker_top_n} ({cfg.reranker_model_name}) ===")
    rerank = chay(lambda q: search(index, cfg_rr, q, postprocessors=rerankers), (1, 3))
    in_so_sanh(vector, rerank)


if __name__ == "__main__":
    main()
