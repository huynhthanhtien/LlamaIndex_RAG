import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from config import get_config
from index_builder import build_or_load_index
from query_engine import build_query_engine, format_sources


def main():
    cfg = get_config()
    cfg.streaming = False

    print(f"Khởi tạo Index & Query Engine với profile: {cfg.name} (LLM: {cfg.llm_model_name})...")
    index = build_or_load_index(cfg)
    engine = build_query_engine(index, cfg)

    input_file = ROOT / "eval" / "results" / "cau-hoi01.md"
    questions = []
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\d+\.\s*(.+)$", line.strip())
            if m:
                questions.append(m.group(1).strip())

    output_file = ROOT / "eval" / "results" / "cau-hoi01-result.md"
    print(f"Bắt đầu chạy {len(questions)} câu hỏi -> {output_file}")

    rerank_str = "bật" if cfg.use_rerank else "tắt"
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"Hỏi đáp quy chế, quy định đào tạo SGU ({cfg.corpus_dir}, rerank: {rerank_str}). Gõ 'thoat' để dừng.\n\n")
        out.flush()

        t0_all = time.time()
        for i, q in enumerate(questions, 1):
            t0 = time.time()
            resp = engine.query(q)
            ans = str(resp).strip()
            sources = format_sources(resp)
            entry = f"Câu hỏi: {q}\n{ans}\nNguồn: {sources}\n\n"
            out.write(entry)
            out.flush()
            dt = time.time() - t0
            print(f"[{i}/{len(questions)}] ({dt:.1f}s) {q[:45]}...")

    print(f"Hoàn thành tất cả trong {time.time() - t0_all:.1f}s! Kết quả tại: {output_file}")


if __name__ == "__main__":
    main()
