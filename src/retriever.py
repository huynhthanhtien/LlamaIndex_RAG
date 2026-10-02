import sys
from pathlib import Path
from typing import TYPE_CHECKING

from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.retrievers import BaseRetriever

if TYPE_CHECKING:
    from llama_index.core.postprocessor import SentenceTransformerRerank

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index


def get_retriever(index: VectorStoreIndex, cfg: RAGConfig) -> BaseRetriever:
    return index.as_retriever(similarity_top_k=cfg.similarity_top_k)


def get_postprocessors(cfg: RAGConfig) -> list[BaseNodePostprocessor]:
    """Rerank chỉ bật khi config đặt reranker_model_name."""
    if not cfg.reranker_model_name:
        return []
    if cfg.model_server_url:
        from remote_models import RemoteRerank
        return [RemoteRerank(base_url=cfg.model_server_url, top_n=cfg.reranker_top_n)]
    return [make_local_reranker(cfg)]


def make_local_reranker(cfg: RAGConfig) -> "SentenceTransformerRerank":
    from llama_index.core.postprocessor import SentenceTransformerRerank
    fp16 = cfg.use_fp16 and cfg.embed_device == "cuda"
    reranker = SentenceTransformerRerank(
        model=cfg.reranker_model_name,
        top_n=cfg.reranker_top_n,
        device="cpu" if fp16 else cfg.embed_device,
    )
    if fp16:
        # SentenceTransformerRerank không nhận dtype: nạp trên CPU, ép fp16 rồi mới đưa lên GPU,
        # tránh việc bản fp32 chiếm VRAM cùng lúc với embedding (tràn card 4 GB).
        reranker._model.half().to(cfg.embed_device)  # pyright: ignore[reportPrivateUsage]
        reranker.device = cfg.embed_device
    return reranker


if __name__ == "__main__":
    cfg = get_config()
    retriever = get_retriever(build_or_load_index(cfg), cfg)
    question = "Một năm học có bao nhiêu học kỳ?"
    print(f"Câu hỏi: {question}")
    for i, n in enumerate(retriever.retrieve(question), start=1):
        print(f"[{i}] score={n.score:.4f} | Điều {n.node.metadata.get('dieu')} | {n.node.get_content()[:100]!r}")
