import unittest

from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode
from phien_ban import LocPhienBan, UuTienSuaDoi, khoa_trong_cau_hoi, moi_hon
from processed_loader import load_processed
from tests import tmp_dir


def node(ma: str, **meta: str | int) -> TextNode:
    return TextNode(id_=ma, text=ma, metadata=dict(meta))


# Mô phỏng corpus thật: QC 2021 (258) bị QĐ 3183 sửa Điều 7 và Điều 9 (Điều 9 chỉ áp dụng từ khóa 2025);
# chuỗi tiếng Anh 2366 (khóa ≤2021) <- 2451, 2626 (2022–2023), 2101 (từ 2024) thay 2626; CV 3248 bị QĐ 898 sửa.
QC7 = node("qc7", so_hieu="258/QĐ-ĐHSG", phan="chinh", dieu="7", bi_sua_doi_boi="3183/QĐ-ĐHSG", ap_dung_khoa_tu=2021)
QC9 = node("qc9", so_hieu="258/QĐ-ĐHSG", phan="chinh", dieu="9", bi_sua_doi_boi="3183/QĐ-ĐHSG", ap_dung_khoa_tu=2021)
QC13 = node("qc13", so_hieu="258/QĐ-ĐHSG", phan="chinh", dieu="13", bi_sua_doi_boi="3183/QĐ-ĐHSG", ap_dung_khoa_tu=2021)
SD7 = node("sd7", so_hieu="3183/QĐ-ĐHSG", phan="sua_doi", sua_doi_dieu="7", sua_doi="258/QĐ-ĐHSG")
SD9 = node("sd9", so_hieu="3183/QĐ-ĐHSG", phan="sua_doi", sua_doi_dieu="9", sua_doi="258/QĐ-ĐHSG", ap_dung_khoa_tu=2025)
QD3183_D2 = node("3183d2", so_hieu="3183/QĐ-ĐHSG", phan="chinh", dieu="2", sua_doi="258/QĐ-ĐHSG")
TB2366 = node("2366", so_hieu="2366/TB-ĐHSG", bi_sua_doi_boi="2451/TB-ĐHSG", ap_dung_khoa_tu=2020, ap_dung_khoa_den=2021)
TB2451 = node("2451", so_hieu="2451/TB-ĐHSG", sua_doi="2366/TB-ĐHSG", ap_dung_khoa_tu=2020, ap_dung_khoa_den=2021)
QD2626 = node("2626", so_hieu="2626/QyĐ-ĐHSG", phan="chinh", dieu="3", bi_sua_doi_boi="2101/QyĐ-ĐHSG",
              ap_dung_khoa_tu=2022, ap_dung_khoa_den=2023)
QD2101 = node("2101", so_hieu="2101/QyĐ-ĐHSG", phan="chinh", dieu="2", thay_the="2626/QyĐ-ĐHSG", ap_dung_khoa_tu=2024)
TB2567 = node("2567", so_hieu="2567/TB-ĐHSG", sua_doi="2366/TB-ĐHSG; 2626/QyĐ-ĐHSG", ap_dung_khoa_tu=2020)
CV3248 = node("3248", so_hieu="3248/QyĐ-ĐHSG-ĐT", bi_sua_doi_boi="898/QĐ-ĐHSG", tinh_trang="bi_sua_doi")
QD898 = node("898d6", so_hieu="898/QĐ-ĐHSG", phan="chinh", dieu="6")
HET = node("het", so_hieu="3522/QĐ-ĐHSG-ĐT", tinh_trang="het_hieu_luc")
CORPUS = [QC7, QC9, QC13, SD7, SD9, QD3183_D2, TB2366, TB2451, QD2626, QD2101, TB2567, CV3248, QD898, HET]


def chay(p: LocPhienBan | UuTienSuaDoi, cau_hoi: str, *nodes: TextNode) -> list[str]:
    ds = [NodeWithScore(node=n, score=1.0 - i / 100) for i, n in enumerate(nodes)]
    return [n.node.node_id for n in p.postprocess_nodes(ds, QueryBundle(cau_hoi))]


class TestKhoa(unittest.TestCase):
    def test_doc_khoa(self) -> None:
        self.assertEqual(khoa_trong_cau_hoi("Sinh viên khóa 2020 có VSTEP 4.0"), 2020)
        self.assertEqual(khoa_trong_cau_hoi("khoá tuyển sinh năm 2024 thì sao"), 2024)
        self.assertEqual(khoa_trong_cau_hoi("SV K22 nộp chứng chỉ"), 2022)
        self.assertIsNone(khoa_trong_cau_hoi("Một năm học có bao nhiêu học kỳ?"))
        self.assertIsNone(khoa_trong_cau_hoi("khóa luận tốt nghiệp 10 tín chỉ"))


class TestLocPhienBan(unittest.TestCase):
    def setUp(self) -> None:
        self.loc = LocPhienBan.tu_nodes(CORPUS)

    def test_bo_van_ban_het_hieu_luc(self) -> None:
        self.assertEqual(chay(self.loc, "học kỳ", HET, QC13), ["qc13"])

    def test_keo_kem_muc_sua_doi(self) -> None:
        # Vector chỉ lấy Điều 7 gốc: mục sửa đổi Điều 7 phải được kéo vào, đứng trước
        self.assertEqual(chay(self.loc, "rút học phần", QC13, QC7), ["qc13", "sd7", "qc7"])

    def test_khoa_bo_bang_cua_khoa_khac(self) -> None:
        kq = chay(self.loc, "khóa 2020 có VSTEP 4.0", QD2101, QD2626, TB2451, TB2366)
        self.assertEqual(kq, ["2451", "2366"])

    def test_khoa_khong_bo_het_can_cu(self) -> None:
        # Không có văn bản nào của chuỗi áp dụng cho khóa 2019 -> giữ nguyên để LLM còn căn cứ
        self.assertEqual(chay(self.loc, "khóa 2019 có VSTEP 4.0", QD2101, QD2626), ["2101", "2626"])

    def test_sua_doi_theo_dieu_chi_tu_khoa_2025(self) -> None:
        # QĐ 3183 Điều 2: mục sửa Điều 9 chỉ áp dụng từ khóa 2025 -> khóa 2023 dùng Điều 9 bản gốc
        self.assertEqual(chay(self.loc, "khóa 2023 có điểm B+ không", QC9), ["qc9"])
        self.assertEqual(chay(self.loc, "điểm B+ thang 10", QC9), ["sd9", "qc9"])
        self.assertEqual(chay(self.loc, "khóa 2023 rút học phần", QC7), ["sd7", "qc7"])


class TestCaBienPhienBan(unittest.TestCase):
    """Ca biên theo nhận xét tuần 6 (ý 5): khóa ở ranh giới, khóa áp dụng của TB 2366/2451, văn bản sửa đổi không thay
    toàn bộ văn bản gốc. Ca hệ thống CHƯA xử lý được ghi bằng expectedFailure: báo cáo chỉ kết luận trên các ca chạy qua;
    khi sửa được, test báo "unexpected success" để chuyển thành test thường."""

    def setUp(self) -> None:
        self.loc = LocPhienBan.tu_nodes(CORPUS)

    def test_ranh_gioi_khoa_tieng_anh(self) -> None:
        # 2366/2451: khóa 2020–2021; 2626: 2022–2023; 2101: từ 2024 — mỗi năm biên chỉ còn văn bản của khóa đó
        self.assertEqual(chay(self.loc, "khóa 2021 có IELTS 5.0", QD2626, TB2366), ["2366"])
        self.assertEqual(chay(self.loc, "khóa 2022 có IELTS 5.0", TB2366, QD2626), ["2626"])
        self.assertEqual(chay(self.loc, "khóa 2023 có IELTS 5.0", QD2101, QD2626), ["2626"])
        self.assertEqual(chay(self.loc, "khóa 2024 có IELTS 5.0", QD2626, QD2101), ["2101"])

    def test_tb_2451_bo_sung_cho_2366_cung_khoa(self) -> None:
        # 2451 chỉ bổ sung chứng chỉ cho 2366 (cùng khóa ≤ 2021): giữ cả hai, bỏ văn bản của khóa khác
        self.assertEqual(chay(self.loc, "K21 có TOEIC 500", TB2451, QD2101, TB2366), ["2451", "2366"])

    def test_khoa_cu_bo_muc_sua_doi_khi_co_dieu_goc(self) -> None:
        # Khóa 2023 lấy được cả Điều 9 gốc và mục sửa Điều 9 (từ 2025): chỉ giữ bản gốc
        self.assertEqual(chay(self.loc, "khóa 2023 có điểm B+ không", SD9, QC9), ["qc9"])

    @unittest.expectedFailure
    def test_khoa_cu_chi_lay_duoc_muc_sua_doi(self) -> None:
        # CHƯA XỬ LÝ: chỉ lấy được mục sửa Điều 9 (áp dụng từ 2025) cho câu khóa 2023 -> bộ lọc giữ nó vì "không bỏ hết
        # căn cứ", không thay bằng Điều 9 gốc từ docstore; LLM trả lời khóa 23 theo thang có B+ (thử giao diện 23/10)
        self.assertEqual(chay(self.loc, "khóa 2023 8,4 điểm quy đổi hệ 4", SD9), ["qc9"])

    @unittest.expectedFailure
    def test_van_ban_sua_mot_phan_khong_dua_len_khi_khong_rerank(self) -> None:
        # CHƯA XỬ LÝ: QĐ 898 chỉ sửa một phần CV 3248 (lệ phí phúc khảo). Không rerank thì không có điểm để biết văn bản
        # mới có liên quan không, nên cả QĐ 898 bị đưa lên trước CV 3248 cho mọi câu — câu "khiếu nại điểm quá trình"
        # rơi từ hạng 1 xuống 5 ở cấu hình vector+loc (eval/results/so-sanh-truy-hoi-2026-10-23-a6e63eb). Có rerank thì
        # ngưỡng tỉ lệ điểm chặn được (test_van_ban_bo_sung_diem_thap_khong_len_truoc).
        p = UuTienSuaDoi(ti_le_toi_thieu=None)
        self.assertEqual(chay(p, "khiếu nại điểm quá trình", CV3248, QD898), ["3248", "898d6"])


class TestUuTienSuaDoi(unittest.TestCase):
    def test_sua_doi_len_truoc_roi_cat(self) -> None:
        p = UuTienSuaDoi(top_n=2)
        self.assertEqual(chay(p, "rút học phần", QC7, QC13, SD7), ["sd7", "qc7"])

    def test_van_ban_moi_len_truoc_van_ban_bi_sua(self) -> None:
        self.assertEqual(chay(UuTienSuaDoi(), "lệ phí phúc khảo", CV3248, QD898), ["898d6", "3248"])

    def test_khong_day_dieu_khong_bi_sua(self) -> None:
        # Điều 2 (hiệu lực) của QĐ 3183 không phải bản mới của QC Điều 13; 2101 thay 2626 chỉ cho khóa từ 2024
        self.assertFalse(moi_hon(QD3183_D2.metadata, QC13.metadata))
        self.assertEqual(chay(UuTienSuaDoi(), "x", QD2626, QD2101), ["2626", "2101"])


TB2567_PTE = node("2567pte", so_hieu="2567/TB-ĐHSG", sua_doi="2366/TB-ĐHSG; 2451/TB-ĐHSG", ap_dung_khoa_tu=2020)
TB2366_SUA = node("2366s", so_hieu="2366/TB-ĐHSG", bi_sua_doi_boi="2451/TB-ĐHSG; 2567/TB-ĐHSG", tinh_trang="bi_sua_doi")


def chay_diem(p: UuTienSuaDoi, *cap: tuple[TextNode, float]) -> list[str]:
    """Như chay() nhưng với điểm rerank cho trước."""
    ds = [NodeWithScore(node=n, score=d) for n, d in cap]
    return [n.node.node_id for n in p.postprocess_nodes(ds, QueryBundle("x"))]


class TestUuTienTheoDiem(unittest.TestCase):
    def test_van_ban_bo_sung_diem_thap_khong_len_truoc(self) -> None:
        # Số đo thật 17/10: câu IELTS 5.5 khóa 2021 — 2366 được 0,542, 2567 (chỉ có PTE) được 0,001
        self.assertEqual(chay_diem(UuTienSuaDoi(), (TB2366_SUA, 0.542), (TB2567_PTE, 0.001)), ["2366s", "2567pte"])

    def test_van_ban_moi_diem_gan_bang_thi_len_truoc(self) -> None:
        # Câu lệ phí phúc khảo: 3248 được 1,000, QĐ 898 Điều 6 được 0,999
        self.assertEqual(chay_diem(UuTienSuaDoi(), (CV3248, 1.0), (QD898, 0.999)), ["898d6", "3248"])

    def test_muc_sua_doi_theo_dieu_luon_len_truoc(self) -> None:
        self.assertEqual(chay_diem(UuTienSuaDoi(), (QC7, 0.97), (SD7, 0.01)), ["sd7", "qc7"])

    def test_khong_rerank_thi_khong_so_ti_le(self) -> None:
        # Không rerank: điểm là cosine, không cùng thang với ngưỡng 0,5 -> quan hệ cả văn bản luôn đưa lên
        p = UuTienSuaDoi(ti_le_toi_thieu=None)
        self.assertEqual(chay_diem(p, (TB2366_SUA, 0.542), (TB2567_PTE, 0.001)), ["2567pte", "2366s"])


VAN_BAN_SUA_DOI = """---
so_hieu: "3183/QĐ-ĐHSG"
sua_doi: ["258/QĐ-ĐHSG"]
ap_dung_khoa_tu_theo_dieu: {"9": 2025}
---

# Quyết định sửa đổi

### Điều 1. Sửa đổi, bổ sung một số điều của Quy chế đào tạo trình độ đại học

#### 1. Sửa đổi, bổ sung khoản 4 Điều 7:
Việc rút bớt học phần được thực hiện trong 03 tuần đầu tiên của học kì chính.

#### 2. Sửa đổi, bổ sung điểm a khoản 3 Điều 9:
Loại đạt có phân mức gồm A, B+, B, C+, C, D+, D theo thang điểm 10.
"""


class TestLoaderMetadataPhienBan(unittest.TestCase):
    def test_quan_he_va_khoa_theo_dieu(self) -> None:
        with tmp_dir() as d:
            p = d / "qd.md"
            p.write_text(VAN_BAN_SUA_DOI, encoding="utf-8")
            nodes = {n.metadata.get("sua_doi_dieu"): n for n in load_processed(p, "QĐ 3183")}
        self.assertEqual(nodes["7"].metadata["sua_doi"], "258/QĐ-ĐHSG")
        self.assertNotIn("ap_dung_khoa_tu", nodes["7"].metadata)
        self.assertEqual(nodes["9"].metadata["ap_dung_khoa_tu"], 2025)
        # Metadata lọc không lọt vào prompt
        self.assertIn("sua_doi", nodes["9"].excluded_llm_metadata_keys)


if __name__ == "__main__":
    unittest.main()
