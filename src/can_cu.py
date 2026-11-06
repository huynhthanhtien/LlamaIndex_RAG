"""Kiểm căn cứ trước khi gọi LLM: không trích đoạn nào đủ điểm rerank thì từ chối thay vì để LLM trả lời.

Tách khỏi retriever.py để kiểm thử chạy được trên CI (retriever.py nạp index_builder, kéo theo thư viện embedding).
"""
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle


class NguongCanCu(BaseNodePostprocessor):
    """Bỏ hết Node khi điểm rerank cao nhất dưới ngưỡng: query engine nhận 0 Node thì không gọi LLM, và nơi gọi
    trả câu từ chối. Lấy điểm cao nhất chứ không lấy Node đầu vì UuTienSuaDoi đã sắp lại thứ tự."""

    nguong: float

    @classmethod
    def class_name(cls) -> str:
        return "NguongCanCu"

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        return nodes if max((n.score or 0.0 for n in nodes), default=0.0) >= self.nguong else []
