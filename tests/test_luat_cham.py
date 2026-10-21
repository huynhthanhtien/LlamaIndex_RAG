import unittest

from luat_cham import cac_dieu, chuan_hoa_nhan, dung_bo_01, dung_bo_02, dung_bo_dev
from llama_index.core.schema import NodeWithScore, TextNode


def node(**meta: str) -> NodeWithScore:
    return NodeWithScore(node=TextNode(text="x", metadata=dict(meta)))


QC = "258/QĐ-ĐHSG"
QD = "3183/QĐ-ĐHSG"


class TestNhan(unittest.TestCase):
    def test_cac_dieu(self) -> None:
        self.assertEqual(cac_dieu("9"), ["9"])
        self.assertEqual(cac_dieu("9;10"), ["9", "10"])
        self.assertEqual(cac_dieu("2 (QĐ 3183)"), ["2"])

    def test_chuan_hoa_nhan_list_va_chuoi(self) -> None:
        self.assertEqual(chuan_hoa_nhan("9"), "9")
        self.assertEqual(chuan_hoa_nhan(["9", " 10 "]), "9;10")
        self.assertEqual(chuan_hoa_nhan(["TB so 2567", "CV2626|3"]), "TB so 2567;CV2626|3")


class TestLuatCham(unittest.TestCase):
    def test_bo_01_nhieu_nhan(self) -> None:
        dieu10 = node(so_hieu=QC, phan="chinh", dieu="10")
        sua10 = node(so_hieu=QD, sua_doi_dieu="10")
        self.assertFalse(dung_bo_01(dieu10, "9"))
        self.assertTrue(dung_bo_01(dieu10, "9;10"))
        self.assertTrue(dung_bo_01(sua10, "9;10"))
        # phụ lục của QC 2021 có cùng số Điều nhưng không phải phần chính
        self.assertFalse(dung_bo_01(node(so_hieu=QC, phan="phu_luc", dieu="10"), "10"))
        # quy chế khác (QC 2017) có cùng số Điều: chấm theo số hiệu nên không tính đúng
        self.assertFalse(dung_bo_01(node(so_hieu="1234/QĐ-ĐHSG", phan="chinh", dieu="10"), "10"))

    def test_bo_02_chi_nhan_qd_3183(self) -> None:
        self.assertTrue(dung_bo_02(node(so_hieu=QD, sua_doi_dieu="10"), "9;10"))
        self.assertFalse(dung_bo_02(node(so_hieu=QD, sua_doi_dieu="10"), "9"))
        self.assertTrue(dung_bo_02(node(so_hieu=QD, phan="chinh", dieu="2"), "2 (QĐ 3183)"))
        self.assertFalse(dung_bo_02(node(so_hieu=QC, phan="chinh", dieu="9"), "9;10"))

    def test_bo_dev_nhan_co_dau_cach_va_nhieu_nhan(self) -> None:
        tb = node(file="TB so 2567.md")
        self.assertTrue(dung_bo_dev(tb, "TB so 2567"))
        # trước đây nhãn bị cắt còn "TB" nên văn bản TB khác cũng bị tính đúng
        self.assertFalse(dung_bo_dev(node(file="TB_ChuanDauRa_2020.md"), "TB so 2567"))
        cv = node(file="CV2626.md", phan="chinh", dieu="3")
        self.assertTrue(dung_bo_dev(cv, "202111_2366;CV2626|3"))
        self.assertFalse(dung_bo_dev(cv, "202111_2366;CV2626|2"))


if __name__ == "__main__":
    unittest.main()
