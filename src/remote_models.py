"""Client gọi model server (src/model_server.py) thay vì nạp embedding/reranker tại chỗ.

Chỉ override các phương thức `_...` mà lớp cha gọi tới; phần còn lại của LlamaIndex
(index, retriever, query engine) dùng 2 class này y như HuggingFaceEmbedding / SentenceTransformerRerank.
"""
import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import MetadataMode, NodeWithScore, QueryBundle


def check_server(base_url: str, embed_model_name: str, reranker_model_name: str | None) -> None:
    """Server phải nạp đúng model của profile, nếu không vector sẽ lệch với index đã build."""
    try:
        info = httpx.get(f"{base_url}/health", timeout=5).json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Không kết nối được model server {base_url}: {e}") from e
    if info["embed_model"] != embed_model_name:
        raise RuntimeError(f"Server đang chạy embedding {info['embed_model']!r}, config cần {embed_model_name!r}")
    if reranker_model_name and info["reranker_model"] != reranker_model_name:
        raise RuntimeError(f"Server đang chạy reranker {info['reranker_model']!r}, config cần {reranker_model_name!r}")


class RemoteEmbedding(BaseEmbedding):
    base_url: str
    timeout: float = 120.0

    @classmethod
    def class_name(cls) -> str:
        return "RemoteEmbedding"

    # kind = "query" | "text": server áp đúng prompt tương ứng như HuggingFaceEmbedding
    def _post(self, texts: list[str], kind: str) -> list[list[float]]:
        r = httpx.post(f"{self.base_url}/embed", json={"texts": texts, "kind": kind}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["embeddings"]

    async def _apost(self, texts: list[str], kind: str) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/embed", json={"texts": texts, "kind": kind})
            r.raise_for_status()
            return r.json()["embeddings"]

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._post([query], "query")[0]

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return (await self._apost([query], "query"))[0]

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._post([text], "text")[0]

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._post(texts, "text")  # 1 request cho cả batch thay vì từng câu

    async def _aget_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return await self._apost(texts, "text")


class RemoteRerank(BaseNodePostprocessor):
    base_url: str
    top_n: int = 3
    timeout: float = 120.0

    @classmethod
    def class_name(cls) -> str:
        return "RemoteRerank"

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        if query_bundle is None:
            raise ValueError("Rerank cần câu hỏi (query_bundle).")
        if not nodes:
            return []
        # MetadataMode.EMBED giống SentenceTransformerRerank để reranker thấy cùng nội dung
        texts = [n.node.get_content(metadata_mode=MetadataMode.EMBED) for n in nodes]
        r = httpx.post(
            f"{self.base_url}/rerank",
            json={"query": query_bundle.query_str, "texts": texts},
            timeout=self.timeout,
        )
        r.raise_for_status()
        for node, score in zip(nodes, r.json()["scores"], strict=True):
            node.score = score
        return sorted(nodes, key=lambda n: n.score or 0.0, reverse=True)[: self.top_n]
