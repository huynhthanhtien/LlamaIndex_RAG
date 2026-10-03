import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import get_config
from index_builder import build_or_load_index
from query_engine import ask, build_query_engine

if __name__ == "__main__":
    cfg = get_config()
    engine = build_query_engine(build_or_load_index(cfg), cfg)
    print(f"Hỏi đáp quy chế, quy định đào tạo SGU ({cfg.corpus_dir}, rerank: {'bật' if cfg.use_rerank else 'tắt'}). "
          "Gõ 'thoat' để dừng.")
    while True:
        try:
            question = input("\nCâu hỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() == "thoat":
            break
        if question:
            ask(engine, question, cfg)
