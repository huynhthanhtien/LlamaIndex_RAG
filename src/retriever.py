import sys
from pathlib import Path

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import BaseRetriever

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index


def get_retriever(index: VectorStoreIndex, cfg: RAGConfig) -> BaseRetriever:
    return index.as_retriever(similarity_top_k=cfg.similarity_top_k)


def get_postprocessors(cfg: RAGConfig) -> list:
    """Rerank chỉ bật khi config đặt reranker_model_name."""
    if not cfg.reranker_model_name:
        return []
    from llama_index.core.postprocessor import SentenceTransformerRerank
    return [SentenceTransformerRerank(model=cfg.reranker_model_name, top_n=cfg.reranker_top_n)]


if __name__ == "__main__":
    cfg = get_config()
    retriever = get_retriever(build_or_load_index(cfg), cfg)
    question = "Một năm học có bao nhiêu học kỳ?"
    print(f"Câu hỏi: {question}")
    for i, n in enumerate(retriever.retrieve(question), start=1):
        print(f"[{i}] score={n.score:.4f} | Điều {n.node.metadata.get('dieu')} | {n.node.text[:100]!r}")
