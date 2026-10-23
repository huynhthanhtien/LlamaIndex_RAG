import unittest
from pathlib import Path

from dong_bang import BO_QUA_KHI_SO, so_sanh
from llama_index.core.schema import NodeWithScore
from luat_cham import BO_CAU_HOI, BO_KIEM_CHUNG, BO_NGOAI_PHAM_VI, chuan_hoa_nhan

ROOT = Path(__file__).resolve().parent.parent
CO_CORPUS = (ROOT / "data" / "processed" / "01_quy_che_dao_tao" / "1_quy_che_dao_tao_dai_hoc").is_dir()


class TestBoCauHoi(unittest.TestCase):
    def test_file_ton_tai_va_khong_trung_giua_dev_va_kiem_chung(self) -> None:
        dev = [f for f, _ in BO_CAU_HOI]
        test = [f for f, _ in BO_KIEM_CHUNG] + [BO_NGOAI_PHAM_VI]
        for f in dev + test:
            self.assertTrue((ROOT / "eval" / f).exists(), f)
        self.assertFalse(set(dev) & set(test))

    @unittest.skipUnless(CO_CORPUS, "chưa có data/processed")
    def test_moi_nhan_khop_it_nhat_mot_node(self) -> None:
        """Nhãn gõ sai (không khớp Node nào) làm câu đó luôn tính là trượt, kéo R@k xuống mà không ai biết."""
        import json

        from config import get_config
        from processed_loader import load_corpus_nodes

        nodes = [NodeWithScore(node=n) for n in load_corpus_nodes(get_config())]
        for f, dung in [*BO_CAU_HOI, *BO_KIEM_CHUNG]:
            for q in json.loads((ROOT / "eval" / f).read_text(encoding="utf-8")):
                d = chuan_hoa_nhan(q["dieu_dung"])
                self.assertTrue(any(dung(n, d) for n in nodes), f"{f}: nhãn {d!r} không khớp Node nào ({q['question']})")


class TestDongBang(unittest.TestCase):
    def test_so_sanh_bao_khoa_khac_them_xoa(self) -> None:
        cu = {"cau_hinh": {"use_rerank": True, "top_k": 10}, "cau_hoi": {"a.json": "1"}}
        moi = {"cau_hinh": {"use_rerank": False, "top_k": 10}, "cau_hoi": {"b.json": "1"}}
        self.assertEqual(so_sanh(cu, moi),
                         ["cau_hinh.use_rerank", "cau_hoi.a.json (bị xóa)", "cau_hoi.b.json (thêm mới)"])

    def test_so_sanh_bo_qua_khoa_phu_thuoc_may(self) -> None:
        self.assertIn("cau_hinh.embed_device", BO_QUA_KHI_SO)
        cu = {"cau_hinh": {"embed_device": "cuda", "persist_dir": "a"}}
        moi = {"cau_hinh": {"embed_device": "cpu", "persist_dir": "b"}}
        self.assertEqual(so_sanh(cu, moi), [])


if __name__ == "__main__":
    unittest.main()
