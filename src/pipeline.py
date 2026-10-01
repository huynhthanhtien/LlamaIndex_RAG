import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import get_config
from index_builder import build_or_load_index
from query_engine import ask, build_query_engine

if __name__ == "__main__":
    cfg = get_config()
    engine = build_query_engine(build_or_load_index(cfg), cfg)
    print("Hỏi đáp Quy chế đào tạo SGU. Gõ 'thoat' để dừng.")
    while True:
        try:
            question = input("\nCâu hỏi: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() == "thoat":
            break
        if question:
            ask(engine, question, cfg)
