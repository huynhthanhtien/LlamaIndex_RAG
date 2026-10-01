import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import get_config
from index_builder import build_or_load_index
from retriever import get_retriever

QUESTIONS_FILE = ROOT / "eval" / "test_questions_01.json"
K_VALUES = (1, 3, 5, 10)


def evaluate(questions: list[dict], retriever) -> dict[int, float]:
    hits = {k: 0 for k in K_VALUES}
    for q in questions:
        retrieved = [n.node.metadata.get("dieu") for n in retriever.retrieve(q["question"])]
        for k in K_VALUES:
            if q["dieu_dung"] in retrieved[:k]:
                hits[k] += 1
        if q["dieu_dung"] not in retrieved:
            print(f"MISS: {q['question']} | đúng: Điều {q['dieu_dung']} | truy hồi: {retrieved}")
    return {k: hits[k] / len(questions) for k in K_VALUES}


if __name__ == "__main__":
    cfg = get_config()
    questions = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    retriever = get_retriever(build_or_load_index(cfg), cfg)
    recall = evaluate(questions, retriever)
    print(f"\nBộ câu hỏi: {QUESTIONS_FILE.name} ({len(questions)} câu)")
    for k, v in recall.items():
        print(f"Recall@{k}: {v:.1%}")
