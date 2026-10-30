import csv
import unittest
from pathlib import Path

from doi_chieu_cham import bao_cao, chon_mau, doc_csv, la_judge, loai_loi, nhan_nguoi
from tests import tmp_dir

COT = ["bo", "id", "question", "ket_qua", "ly_do", "nguoi_cham", "do_tu_tin", "trich_dan_sai"]


def ghi(path: Path, dong: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COT)
        w.writeheader()
        for d in dong:
            w.writerow({c: d.get(c, "") for c in COT})


def cau(i: str, ket_qua: str = "", **khac: str) -> dict[str, str]:
    return {"bo": "dev_questions_dot4.json", "id": i, "question": f"câu {i}", "ket_qua": ket_qua, **khac}


class TestDoiChieuCham(unittest.TestCase):
    def test_judge_khong_tinh_la_nguoi(self) -> None:
        with tmp_dir() as d:
            ghi(d / "cham-tay-claude.csv", [cau("1", "dung", nguoi_cham="Claude (AI)", do_tu_tin="cao")])
            ghi(d / "cham-tay-ai-lan2.csv", [cau("1", "dung")])
            ghi(d / "cham-tay-nhuy.csv", [cau("1", "sai", nguoi_cham="Như Ý")])
            ghi(d / "cham-tay-thuy.csv", [cau("1", "dung", nguoi_cham="Claude (AI)")])  # tên người nhưng ghi AI
            self.assertTrue(la_judge(d / "cham-tay-claude.csv", doc_csv(d / "cham-tay-claude.csv")))
            self.assertTrue(la_judge(d / "cham-tay-ai-lan2.csv", doc_csv(d / "cham-tay-ai-lan2.csv")))
            self.assertTrue(la_judge(d / "cham-tay-thuy.csv", doc_csv(d / "cham-tay-thuy.csv")))
            self.assertFalse(la_judge(d / "cham-tay-nhuy.csv", doc_csv(d / "cham-tay-nhuy.csv")))

    def test_hai_nguoi_lech_thi_chua_co_nhan(self) -> None:
        k1, k2, k3 = ("b", "1"), ("b", "2"), ("b", "3")
        a = {k1: {"ket_qua": "dung"}, k2: {"ket_qua": "dung"}, k3: {"ket_qua": "sai"}}
        b = {k1: {"ket_qua": "dung"}, k2: {"ket_qua": "sai"}, k3: {"ket_qua": "dung"}}
        chot = {k3: {"ket_qua": "sai", "ly_do": "lệch, đã chốt"}}
        nhan, lech = nhan_nguoi({"a": a, "b": b}, chot)
        self.assertEqual(nhan[k1]["ket_qua"], "dung")
        self.assertEqual(nhan[k3]["ket_qua"], "sai")  # nhãn chốt thắng
        self.assertNotIn(k2, nhan)
        self.assertEqual(lech, [k2])

    def test_lech_trich_dan_cung_la_lech(self) -> None:
        k = ("b", "1")
        _, lech = nhan_nguoi({"a": {k: {"ket_qua": "dung", "trich_dan_sai": "co"}},
                              "b": {k: {"ket_qua": "dung", "trich_dan_sai": ""}}}, {})
        self.assertEqual(lech, [k])

    def test_loai_loi(self) -> None:
        self.assertEqual(loai_loi("synthesis: lấy bảng khóa 2021"), "synthesis")
        self.assertEqual(loai_loi("Thieu_van_ban: QĐ 736 ngoài corpus"), "thieu_van_ban")
        self.assertIsNone(loai_loi("sai số tín chỉ"))

    def test_mau_chi_lay_cau_cao_va_tat_dinh(self) -> None:
        judge = {("b", str(i)): {"ket_qua": "dung", "do_tu_tin": "cao", "trich_dan_sai": ""} for i in range(20)}
        judge[("b", "x")] = {"ket_qua": "dung", "do_tu_tin": "thap", "trich_dan_sai": ""}
        judge[("b", "y")] = {"ket_qua": "dung", "do_tu_tin": "cao", "trich_dan_sai": "co"}
        mau = chon_mau(judge, 5)
        self.assertEqual(mau, chon_mau(judge, 5))
        self.assertEqual(len(mau), 5)
        self.assertFalse({("b", "x"), ("b", "y")} & set(mau))

    def test_bao_cao(self) -> None:
        with tmp_dir() as d:
            ghi(d / "cham-tay.csv", [cau("1"), cau("2"), cau("3")])
            ghi(d / "cham-tay-claude.csv", [cau("1", "dung", do_tu_tin="cao", nguoi_cham="Claude (AI)"),
                                            cau("2", "dung", do_tu_tin="cao", nguoi_cham="Claude (AI)"),
                                            cau("3", "sai", do_tu_tin="thap", nguoi_cham="Claude (AI)")])
            ghi(d / "cham-tay-nhuy.csv", [cau("1", "dung", nguoi_cham="Như Ý"),
                                          cau("2", "dung", nguoi_cham="Như Ý", trich_dan_sai="co",
                                              ly_do="synthesis: trích QC 2021 thay vì QĐ 3183")])
            md = bao_cao(d)
        self.assertIn("Có nhãn người xác nhận: 2/3 câu", md)
        self.assertIn("trùng đúng/không đúng 2/2", md)
        self.assertIn("dot4#2 (judge dung, người dung+trích sai)", md)
        self.assertIn("| **Nội dung đúng** | 1 | 1 |", md)
        self.assertIn("| synthesis | 1 | dot4#2 |", md)


if __name__ == "__main__":
    unittest.main()
