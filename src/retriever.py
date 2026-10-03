import sys
from pathlib import Path
from typing import TYPE_CHECKING

from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle

if TYPE_CHECKING:
    from llama_index.core.postprocessor import SentenceTransformerRerank

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index


def get_retriever(index: VectorStoreIndex, cfg: RAGConfig) -> BaseRetriever:
    return index.as_retriever(similarity_top_k=cfg.similarity_top_k)


def get_postprocessors(cfg: RAGConfig) -> list[BaseNodePostprocessor]:
    """Rerank chỉ bật khi cfg.use_rerank và có reranker_model_name (profile server)."""
    if not (cfg.use_rerank and cfg.reranker_model_name):
        return []
    if cfg.model_server_url:
        from remote_models import RemoteRerank
        return [RemoteRerank(base_url=cfg.model_server_url, top_n=cfg.reranker_top_n)]
    return [make_local_reranker(cfg)]


def search(
    index: VectorStoreIndex,
    cfg: RAGConfig,
    question: str,
    postprocessors: list[BaseNodePostprocessor] | None = None,
) -> list[NodeWithScore]:
    """Truy hồi top-k rồi cho qua postprocessor (rerank). Truyền postprocessors để không nạp lại reranker mỗi lần."""
    nodes = get_retriever(index, cfg).retrieve(question)
    for p in get_postprocessors(cfg) if postprocessors is None else postprocessors:
        nodes = p.postprocess_nodes(nodes, QueryBundle(question))
    return nodes


def node_label(n: NodeWithScore) -> str:
    """Nhãn dạng "<văn bản> – Điều N" hoặc "<văn bản> – sửa đổi Điều N" để in kết quả và trích nguồn."""
    m = n.node.metadata
    if m.get("dieu"):
        return f"{m.get('van_ban', '')} – Điều {m['dieu']}"
    if m.get("sua_doi_dieu"):
        return f"{m.get('van_ban', '')} – sửa đổi Điều {m['sua_doi_dieu']}"
    return str(m.get("van_ban", ""))  # văn bản không chia Điều


def make_local_reranker(cfg: RAGConfig) -> "SentenceTransformerRerank":
    from llama_index.core.postprocessor import SentenceTransformerRerank
    if not cfg.reranker_model_name:
        raise ValueError(f"Profile {cfg.name!r} không có reranker_model_name")
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
    import dataclasses

    cfg = dataclasses.replace(get_config(), use_rerank="--rerank" in sys.argv)
    index = build_or_load_index(cfg)
    question = " ".join(a for a in sys.argv[1:] if a != "--rerank") or "Một năm học có bao nhiêu học kỳ?"
    print(f"Câu hỏi: {question}" + (" (có rerank)" if cfg.use_rerank else ""))
    for i, n in enumerate(search(index, cfg, question), start=1):
        print(f"[{i}] score={n.score or 0:.4f} | {node_label(n)} | {n.node.get_content()[:80]!r}")
