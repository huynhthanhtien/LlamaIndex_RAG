"""Kiểm thử có LLM: gọi Ollama thật (OLLAMA_BASE_URL trong .env) qua đúng query engine của dự án.

Mặc định bị bỏ qua để `make test` và CI vẫn chạy offline. Bật bằng:
    make test-llm
    # hoặc: RAG_TEST_LLM=1 RAG_PROFILE=server venv/bin/python -m unittest tests.test_llm -v

Mỗi câu hỏi gọi LLM một lần (temperature=0, seed=42 nên kết quả tất định). Các khẳng định chỉ kiểm
những con số / cụm từ bắt buộc phải có trong câu trả lời đúng, không so nguyên văn.
"""
import dataclasses
import os
import re
import unittest
from typing import TYPE_CHECKING, ClassVar

import httpx

from config import RAGConfig, get_config

if TYPE_CHECKING:
    from llama_index.core.query_engine import RetrieverQueryEngine

BAT = os.environ.get("RAG_TEST_LLM") == "1"


def chuan_hoa(s: str) -> str:
    """Chữ thường, dấu thập phân về dấu phẩy ("8.5" -> "8,5"), gộp khoảng trắng."""
    s = re.sub(r"(?<=\d)\.(?=\d)", ",", s.lower())
    return re.sub(r"\s+", " ", s)


def ollama_co_model(cfg: RAGConfig) -> str | None:
    """None nếu Ollama gọi được và đã có model của profile; ngược lại trả lý do để bỏ qua."""
    try:
        r = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        return f"không gọi được Ollama {cfg.ollama_base_url}: {e}"
    ten = {str(m.get("name", "")) for m in r.json().get("models", [])}
    if cfg.llm_model_name not in ten:
        return f"Ollama chưa có model {cfg.llm_model_name} (đang có: {sorted(ten)})"
    return None


@unittest.skipUnless(BAT, "đặt RAG_TEST_LLM=1 để chạy kiểm thử có LLM")
class TestLLM(unittest.TestCase):
    cfg: ClassVar[RAGConfig]
    engine: ClassVar["RetrieverQueryEngine | None"] = None  # dựng một lần cho cả lớp
    tra_loi: ClassVar[dict[str, tuple[str, str]]] = {}  # câu hỏi -> (câu trả lời, dòng nguồn), hỏi mỗi câu một lần

    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = dataclasses.replace(get_config(), streaming=False)
        ly_do = ollama_co_model(cls.cfg)
        if ly_do:
            raise unittest.SkipTest(ly_do)

    def hoi(self, cau_hoi: str) -> tuple[str, str]:
        """Hỏi qua RetrieverQueryEngine của dự án; trả (câu trả lời đã chuẩn hoá, dòng nguồn)."""
        if cau_hoi not in self.tra_loi:
            # import muộn: index_builder kéo theo torch, không có trong CI offline
            from index_builder import build_or_load_index
            from query_engine import build_query_engine, format_sources

            if TestLLM.engine is None:
                TestLLM.engine = build_query_engine(build_or_load_index(self.cfg), self.cfg)
            response = TestLLM.engine.query(cau_hoi)
            self.tra_loi[cau_hoi] = (str(response).strip(), format_sources(response))
        tra_loi, nguon = self.tra_loi[cau_hoi]
        return chuan_hoa(tra_loi), nguon

    # --- LLM và cấu hình ---

    def test_tat_dinh(self) -> None:
        """temperature=0 + seed: cùng prompt gọi hai lần cho cùng kết quả."""
        from query_engine import make_llm

        llm = make_llm(self.cfg)
        prompt = "Trả lời đúng một số: 2 cộng 3 bằng mấy?"
        self.assertEqual(llm.complete(prompt).text, llm.complete(prompt).text)

    def test_khong_lo_suy_luan(self) -> None:
        """thinking=False: câu trả lời không chứa khối <think> hay chuỗi điều khiển /no_think."""
        tra_loi, _ = self.hoi("Một năm học có bao nhiêu học kỳ chính?")
        self.assertNotIn("<think>", tra_loi)
        self.assertNotIn("/no_think", tra_loi)

    # --- Câu hỏi trong phạm vi: đáp án có trong văn bản ---

    def test_rut_hoc_phan(self) -> None:
        """QĐ 3183 sửa đổi khoản 4 Điều 7: rút học phần trong 03 tuần đầu của học kỳ.

        Bản gốc Quy chế 2021 ghi "sau 02 tuần ... không muộn quá 05 tuần"; trả lời theo bản gốc là sai.
        """
        tra_loi, nguon = self.hoi("Sinh viên được rút học phần trong thời gian nào?")
        self.assertRegex(tra_loi, r"\b0?3 tuần")
        self.assertIn("Điều 7", nguon)

    def test_tin_chi_cu_nhan(self) -> None:
        """Quy chế 2021, Điều 2: cử nhân tối thiểu 120 tín chỉ."""
        tra_loi, _ = self.hoi("Học cử nhân cần tích lũy tối thiểu bao nhiêu tín chỉ?")
        self.assertIn("120", tra_loi)

    def test_xep_loai_xuat_sac(self) -> None:
        """Quy chế 2021, khoản 4 Điều 10: xuất sắc từ 3,6 đến 4,0."""
        tra_loi, _ = self.hoi("Điểm trung bình tích lũy bao nhiêu thì được xếp loại xuất sắc?")
        self.assertIn("3,6", tra_loi)

    def test_buoc_thoi_hoc_hai_lan_lien_tiep(self) -> None:
        """Khoản 2 Điều 11: buộc thôi học khi *quá hai lần* bị cảnh báo *liên tiếp*.

        Cảnh báo ở kỳ 1 và kỳ 3 là hai lần, không liên tiếp, nên không bị buộc thôi học.
        """
        tra_loi, _ = self.hoi(
            "Kỳ 1 tôi bị cảnh báo học tập, kỳ 2 bình thường, kỳ 3 bị cảnh báo thì có bị buộc thôi học không?"
        )
        self.assertRegex(tra_loi, r"\bkhông\b")
        self.assertIn("liên tiếp", tra_loi)

    # --- Hồi quy: lỗi nhầm thang điểm hệ 10 / hệ 4 (Mục 4.5.2 của báo cáo) ---

    def test_diem_a_he_10(self) -> None:
        """A ứng với 8,5--10 trên thang 10; trước khi sửa prompt, LLM trả lời "4,0 điểm hệ 10"."""
        tra_loi, _ = self.hoi("A thì được bao nhiêu điểm hệ 10?")
        self.assertIn("8,5", tra_loi)
        self.assertNotRegex(tra_loi, r"4,0 điểm (hệ|thang điểm) 10")

    def test_diem_d_cong_he_10(self) -> None:
        """QĐ 3183: D+ từ 4,8 đến 5,4 trên thang 10."""
        tra_loi, _ = self.hoi("Điểm D+ tương ứng với khoảng điểm nào trên thang điểm 10?")
        self.assertIn("4,8", tra_loi)
        self.assertIn("5,4", tra_loi)

    # --- Câu hỏi ngoài phạm vi: phải từ chối, không bịa ---

    def assertTuChoi(self, tra_loi: str) -> None:
        """Cùng tiêu chí nhận dạng từ chối với eval/evaluate_answers.py."""
        from evaluate_answers import TU_CHOI

        self.assertRegex(tra_loi, TU_CHOI)

    def test_tu_choi_hoc_phi(self) -> None:
        tra_loi, _ = self.hoi("Bao nhiêu tiền một tín chỉ?")
        self.assertTuChoi(tra_loi)
        self.assertNotIn("/no_think", tra_loi)
        self.assertNotRegex(tra_loi, r"\d[\d.,]* ?(đồng|vnđ|vnd)")

    def test_tu_choi_diem_ren_luyen(self) -> None:
        tra_loi, _ = self.hoi("Điểm rèn luyện được tính như thế nào?")
        self.assertTuChoi(tra_loi)


if __name__ == "__main__":
    unittest.main()
