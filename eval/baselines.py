"""Baseline truy hồi để so với hệ thống: BM25 thuần và "không xếp hạng".

Vì sao cần: báo cáo phải chứng minh thiết kế (embedding tiếng Việt + cắt theo Điều) đóng góp gì,
không thể chỉ khoe Recall@10 = 100% của chính hệ thống. Hai mốc dưới đây là sàn so sánh:
  - `bm25`: tìm từ khóa thuần (đúng thứ mà tìm kiếm PDF hiện tại của trường làm).
  - `khong-xep-hang`: trả về Node theo thứ tự docstore, tức không có bước xếp hạng nào.

Cách dùng:
    RAG_PROFILE=server RAG_EMBED_DEVICE=cpu venv/bin/python eval/baselines.py
"""
import argparse
import json
import sys
from pathlib import Path

from llama_index.core.schema import NodeWithScore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bm25 import BM25Retriever
from config import get_config
from evaluate import BO_CAU_HOI, KetQua, bang_markdown, danh_gia, in_ket_qua
from index_builder import build_or_load_index


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-out", default=str(ROOT / "eval" / "results" / "baseline.json"))
    ap.add_argument("--md-out", default=str(ROOT / "eval" / "results" / "baseline.md"))
    args = ap.parse_args()

    cfg = get_config()
    index = build_or_load_index(cfg)
    nodes = list(index.docstore.docs.values())
    print(f"Index: {cfg.persist_dir} | {len(nodes)} Node | baseline không dùng embedding\n")

    bm25 = BM25Retriever(nodes=nodes, similarity_top_k=cfg.similarity_top_k, k1=cfg.bm25_k1, b=cfg.bm25_b)
    timers = {
        "bm25": bm25.retrieve,
        "khong-xep-hang": lambda _q: [NodeWithScore(node=n) for n in nodes],
    }

    tat_ca: list[KetQua] = []
    for ten, tim in timers.items():
        print(f"=== baseline: {ten} ===")
        for ten_file, dung in BO_CAU_HOI:
            kq = danh_gia(ten_file, dung, tim, ten, {"baseline": ten})
            in_ket_qua(kq)
            tat_ca.append(kq)

    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(
        json.dumps({"ket_qua": [k.to_dict() for k in tat_ca]}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    Path(args.md_out).write_text(bang_markdown(tat_ca), encoding="utf-8")
    print(bang_markdown(tat_ca))
    print(f"Đã ghi {args.json_out} và {args.md_out}")


if __name__ == "__main__":
    main()
