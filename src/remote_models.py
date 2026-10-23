"""Client gọi model server (src/model_server.py) thay vì nạp embedding/reranker tại chỗ.

Chỉ override các phương thức `_...` mà lớp cha gọi tới; phần còn lại của LlamaIndex
(index, retriever, query engine) dùng 2 class này y như HuggingFaceEmbedding / SentenceTransformerRerank.
"""
import logging
import os
import time
from typing import Any

import httpx
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import MetadataMode, NodeWithScore, QueryBundle

logger = logging.getLogger(__name__)

# Cloudflare quick tunnel tới Colab chập chờn: request đơn lẻ bị cắt (Connection reset, SSL timeout) hoặc nhận 530
# khi tunnel đang nối lại. Trước đây gọi đúng một lần nên một request hỏng là cả câu hỏi lỗi.
SO_LAN_THU = 4
MA_LOI_TAM_THOI = {502, 503, 504, 530}


def auth_headers() -> dict[str, str]:
    """Token cho model server chạy trên máy cloud (src/model_server.py đọc cùng biến MODEL_SERVER_TOKEN)."""
    token = os.environ.get("MODEL_SERVER_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def goi_server(method: str, url: str, timeout: float, json: dict[str, Any] | None = None) -> httpx.Response:
    """Gọi model server, thử lại khi lỗi mạng tạm thời hoặc mã 502/503/504/530 (chờ 1, 2, 4 giây)."""
    for lan in range(1, SO_LAN_THU + 1):
        try:
            r = httpx.request(method, url, json=json, headers=auth_headers(), timeout=timeout)
            if r.status_code not in MA_LOI_TAM_THOI or lan == SO_LAN_THU:
                return r.raise_for_status()
            loi = f"HTTP {r.status_code}"
        except httpx.TransportError as e:
            if lan == SO_LAN_THU:
                raise
            loi = f"{type(e).__name__}: {e}"
        logger.warning("Model server lỗi tạm thời (%s), thử lại lần %d/%d", loi, lan + 1, SO_LAN_THU)
        time.sleep(2 ** (lan - 1))
    raise AssertionError("không tới được")  # vòng lặp luôn return hoặc raise ở lần cuối


def check_server(
    base_url: str, embed_model_name: str, reranker_model_name: str | None, reranker_max_length: int | None = None
) -> None:
    """Server phải nạp đúng model của profile, nếu không vector sẽ lệch với index đã build.

    reranker_max_length: server cũ (trước 16/10) không trả khóa này và cắt Node ở 512 token -> báo lỗi
    thay vì âm thầm cho điểm rerank sai.
    """
    try:
        info = goi_server("GET", f"{base_url}/health", timeout=15).json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Không kết nối được model server {base_url}: {e}") from e
    if info["embed_model"] != embed_model_name:
        raise RuntimeError(f"Server đang chạy embedding {info['embed_model']!r}, config cần {embed_model_name!r}")
    if reranker_model_name and info["reranker_model"] != reranker_model_name:
        raise RuntimeError(f"Server đang chạy reranker {info['reranker_model']!r}, config cần {reranker_model_name!r}")
    if reranker_model_name and reranker_max_length and info.get("reranker_max_length") != reranker_max_length:
        raise RuntimeError(
            f"Reranker trên server đọc {info.get('reranker_max_length') or 512} token, config cần {reranker_max_length}. "
            "Chạy lại scripts/setup_server_v2.sh bản mới, hoặc bỏ MODEL_SERVER_URL để rerank trên máy."
        )


class RemoteEmbedding(BaseEmbedding):
    base_url: str
    timeout: float = 120.0

    @classmethod
    def class_name(cls) -> str:
        return "RemoteEmbedding"

    # kind = "query" | "text": server áp đúng prompt tương ứng như HuggingFaceEmbedding
    def _post(self, texts: list[str], kind: str) -> list[list[float]]:
        r = goi_server("POST", f"{self.base_url}/embed", self.timeout, json={"texts": texts, "kind": kind})
        return r.json()["embeddings"]

    async def _apost(self, texts: list[str], kind: str) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=auth_headers()) as client:
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
        r = goi_server("POST", f"{self.base_url}/rerank", self.timeout,
                       json={"query": query_bundle.query_str, "texts": texts})
        for node, score in zip(nodes, r.json()["scores"], strict=True):
            node.score = score
        return sorted(nodes, key=lambda n: n.score or 0.0, reverse=True)[: self.top_n]
