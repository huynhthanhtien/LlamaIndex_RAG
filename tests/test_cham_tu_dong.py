import unittest

from cham_tu_dong import chuan_hoa_so, khop_su_kien, la_tu_choi, su_kien
from metrics import cohen_kappa


class TestChamTuDong(unittest.TestCase):
    def test_chuan_hoa_so(self) -> None:
        self.assertEqual([chuan_hoa_so(x) for x in ("08", "4.0", "4,0", "7,8", "150")], ["8", "4", "4", "7.8", "150"])

    def test_bo_so_hieu_van_ban_va_dieu(self) -> None:
        # "QĐ 810", "Điều 17", "số 258/QĐ-ĐHSG" không phải nội dung trả lời
        self.assertEqual(su_kien("Giỏi trở lên (QĐ 810/2024, Điều 3). Quyết định số 258/QĐ-ĐHSG"), set())
        self.assertEqual(su_kien("143 tín chỉ: 132 chuyên môn, 03 thể chất, 08 quốc phòng"), {"143", "132", "3", "8"})
        self.assertEqual(su_kien("Đơn đề nghị (Mẫu ĐT.ChuyenNganh.01), bảng điểm"), set())
        self.assertEqual(su_kien("4,5 năm, 150 tín chỉ"), {"4.5", "150"})

    def test_khop_su_kien(self) -> None:
        dap_an = "4,5 năm, 150 tín chỉ."
        self.assertEqual(khop_su_kien(dap_an, "Học 4.5 năm và tích lũy 150 tín chỉ (Điều 2)."), "du")
        self.assertEqual(khop_su_kien(dap_an, "Phải tích lũy 150 tín chỉ."), "thieu")
        self.assertEqual(khop_su_kien(dap_an, "Không tìm thấy trong các văn bản quy định."), "khong")
        self.assertEqual(khop_su_kien("Không.", "Có."), "khong_ap_dung")

    def test_tu_choi(self) -> None:
        self.assertTrue(la_tu_choi("Không tìm thấy trong các văn bản quy định."))
        self.assertFalse(la_tu_choi("Có, sinh viên được hoãn thi."))

    def test_cohen_kappa(self) -> None:
        self.assertEqual(cohen_kappa(["dung", "sai", "dung"], ["dung", "sai", "dung"]), 1.0)
        self.assertAlmostEqual(cohen_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]), 0.0)
        with self.assertRaises(ValueError):
            cohen_kappa(["a"], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
