"""Truy hồi: vector top-k, tuỳ chọn trộn BM25 (hybrid) và xếp hạng lại (rerank)."""
import logging
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
from config import RAGConfig, get_config, resolve_device
from index_builder import build_or_load_index

logger = logging.getLogger(__name__)


def get_retriever(index: VectorStoreIndex, cfg: RAGConfig) -> BaseRetriever:
    """Vector top-k; khi cfg.use_hybrid thì trộn thêm BM25 bằng QueryFusionRetriever."""
    vector = index.as_retriever(similarity_top_k=cfg.similarity_top_k)
    if not cfg.use_hybrid:
        return vector

    from llama_index.core.retrievers import QueryFusionRetriever
    from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
    from llama_index.llms.ollama import Ollama

    from bm25 import BM25Retriever

    nodes = list(index.docstore.docs.values())
    bm25 = BM25Retriever(
        nodes=nodes,
        similarity_top_k=cfg.bm25_top_k,
        k1=cfg.bm25_k1,
        b=cfg.bm25_b,
    )
    logger.info("Hybrid: vector top-%d + BM25 top-%d, fusion=%s", cfg.similarity_top_k, cfg.bm25_top_k, cfg.fusion_mode)
    return QueryFusionRetriever(
        retrievers=[vector, bm25],
        mode=FUSION_MODES(cfg.fusion_mode),
        similarity_top_k=cfg.similarity_top_k,
        num_queries=1,  # 1 = không gọi LLM sinh truy vấn phụ, giữ phép đo tất định
        use_async=False,
        retriever_weights=[cfg.vector_weight, cfg.bm25_weight],
        # QueryFusionRetriever.__init__ làm `llm if llm else Settings.llm`, mà Settings.llm mặc định
        # là OpenAI -> ImportError nếu chưa cài llama-index-llms-openai. Vì num_queries=1 nên LLM
        # không bao giờ được gọi; truyền vào chỉ để tránh việc thư viện đi resolve LLM mặc định.
        llm=Ollama(model=cfg.llm_model_name, base_url=cfg.ollama_base_url, request_timeout=cfg.request_timeout),
    )


def get_postprocessors(cfg: RAGConfig) -> list[BaseNodePostprocessor]:
    """Ngưỡng tương đồng (nếu đặt) rồi tới rerank (chỉ khi cfg.use_rerank và có reranker_model_name)."""
    ps: list[BaseNodePostprocessor] = []
    if cfg.similarity_cutoff is not None:
        if cfg.use_hybrid:
            # Điểm sau fusion (RRF) không cùng thang với cosine -> ngưỡng chỉ áp cho vector thuần
            logger.warning("Bỏ qua similarity_cutoff vì đang bật hybrid (thang điểm đã đổi)")
        else:
            from llama_index.core.postprocessor import SimilarityPostprocessor

            ps.append(SimilarityPostprocessor(similarity_cutoff=cfg.similarity_cutoff))
    if not (cfg.use_rerank and cfg.reranker_model_name):
        return ps
    if cfg.model_server_url:
        from remote_models import RemoteRerank

        ps.append(RemoteRerank(base_url=cfg.model_server_url, top_n=cfg.reranker_top_n))
        return ps
    ps.append(make_local_reranker(cfg))
    return ps


def search(
    index: VectorStoreIndex,
    cfg: RAGConfig,
    question: str,
    postprocessors: list[BaseNodePostprocessor] | None = None,
    retriever: BaseRetriever | None = None,
) -> list[NodeWithScore]:
    """Truy hồi top-k rồi cho qua postprocessor (ngưỡng, rerank).

    Truyền sẵn `retriever`/`postprocessors` để vòng lặp đánh giá không dựng lại retriever
    và không nạp lại reranker mỗi câu.
    """
    nodes = (retriever or get_retriever(index, cfg)).retrieve(question)
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
    device = resolve_device(cfg.embed_device)
    fp16 = cfg.use_fp16 and device == "cuda"
    reranker = SentenceTransformerRerank(
        model=cfg.reranker_model_name,
        top_n=cfg.reranker_top_n,
        device="cpu" if fp16 else device,
    )
    if fp16:
        # SentenceTransformerRerank không nhận dtype: nạp trên CPU, ép fp16 rồi mới đưa lên GPU,
        # tránh việc bản fp32 chiếm VRAM cùng lúc với embedding (tràn card 4 GB).
        reranker._model.half().to(device)  # pyright: ignore[reportPrivateUsage]
        reranker.device = device
    return reranker


if __name__ == "__main__":
    import dataclasses

    co_hybrid = "--hybrid" in sys.argv
    cfg = dataclasses.replace(get_config(), use_rerank="--rerank" in sys.argv, use_hybrid=co_hybrid)
    index = build_or_load_index(cfg)
    question = " ".join(a for a in sys.argv[1:] if not a.startswith("--")) or "Một năm học có bao nhiêu học kỳ?"
    nhan = ", ".join(k for k in ("rerank", "hybrid") if k in " ".join(sys.argv).replace("--", ""))
    print(f"Câu hỏi: {question}" + (f" ({nhan})" if nhan else ""))
    for i, n in enumerate(search(index, cfg, question), start=1):
        print(f"[{i}] score={n.score or 0:.4f} | {node_label(n)} | {n.node.get_content()[:80]!r}")
