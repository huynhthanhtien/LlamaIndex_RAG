import dataclasses
import unittest

from can_cu import NguongCanCu
from cham_tu_dong import la_tu_choi
from config import CONFIG_LOCAL, CONFIG_SERVER
from llama_index.core.llms import MockLLM
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode


def nodes(*diem: float | None) -> list[NodeWithScore]:
    return [NodeWithScore(node=TextNode(text=f"n{i}"), score=d) for i, d in enumerate(diem)]


class CoDinh(BaseRetriever):
    """Retriever trả đúng các Node cho trước (không cần index, không cần model embedding)."""

    def __init__(self, ds: list[NodeWithScore]) -> None:
        super().__init__()
        self.ds = ds

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        return list(self.ds)


class TestNguongCanCu(unittest.TestCase):
    def test_duoi_nguong_bo_het(self) -> None:
        self.assertEqual(NguongCanCu(nguong=0.001).postprocess_nodes(nodes(0.0004, 0.0007)), [])

    def test_lay_diem_cao_nhat_khong_lay_node_dau(self) -> None:
        # UuTienSuaDoi có thể đưa Node điểm thấp lên đầu: vẫn giữ nếu một Node bất kỳ đạt ngưỡng
        ds = nodes(0.0002, 0.64, 0.0001)
        self.assertEqual(NguongCanCu(nguong=0.001).postprocess_nodes(ds), ds)

    def test_khong_co_diem_va_rong(self) -> None:
        self.assertEqual(NguongCanCu(nguong=0.001).postprocess_nodes(nodes(None)), [])
        self.assertEqual(NguongCanCu(nguong=0.001).postprocess_nodes([]), [])

    def test_khong_goi_llm_khi_bi_tu_choi(self) -> None:
        """0 Node sau postprocessor: synthesizer trả "Empty Response" mà không gọi LLM, nơi gọi in câu từ chối."""
        goi: list[str] = []

        class DemLLM(MockLLM):
            def complete(self, prompt: str, formatted: bool = False, **kwargs: object):  # type: ignore[override]
                goi.append(prompt)
                return super().complete(prompt, formatted=formatted, **kwargs)

        engine = RetrieverQueryEngine.from_args(
            retriever=CoDinh(nodes(0.0004)), llm=DemLLM(max_tokens=None),
            node_postprocessors=[NguongCanCu(nguong=0.001)])
        r = engine.query("Nếu giảng viên đòi tiền để nâng điểm thì sinh viên tố cáo ở đâu?")
        self.assertEqual(r.source_nodes, [])
        self.assertEqual(goi, [])

        engine = RetrieverQueryEngine.from_args(
            retriever=CoDinh(nodes(0.8)), llm=DemLLM(max_tokens=None),
            node_postprocessors=[NguongCanCu(nguong=0.001)])
        self.assertEqual(len(engine.query("Điểm F quy đổi hệ 4 là bao nhiêu?").source_nodes), 1)
        self.assertEqual(len(goi), 1)


class TestCauHinhCanCu(unittest.TestCase):
    def test_profile(self) -> None:
        self.assertEqual(CONFIG_SERVER.nguong_can_cu, 0.001)
        self.assertEqual(CONFIG_SERVER.mo_ta()["nguong_can_cu"], 0.001)
        self.assertIsNone(CONFIG_LOCAL.nguong_can_cu)
        # Không rerank thì điểm là cosine: ngưỡng không áp, mo_ta() ghi None để kết quả không bị hiểu nhầm
        self.assertIsNone(dataclasses.replace(CONFIG_SERVER, use_rerank=False).mo_ta()["nguong_can_cu"])

    def test_cau_tu_choi_duoc_cham_tu_dong_nhan_ra(self) -> None:
        # Giữ đồng bộ với query_engine.TU_CHOI (không import được ở CI vì kéo theo llama-index-llms-ollama)
        self.assertTrue(la_tu_choi("Không tìm thấy trong các văn bản quy định."))


if __name__ == "__main__":
    unittest.main()
