import os
import unittest
from pathlib import Path

from config import PROFILES, get_config, resolve_device
from processed_loader import corpus_files, load_corpus_nodes, thong_ke

ROOT = Path(__file__).resolve().parent.parent
CO_CORPUS = (ROOT / "data" / "processed" / "01_quy_che_dao_tao" / "1_quy_che_dao_tao_dai_hoc").is_dir()


@unittest.skipUnless(CO_CORPUS, "chưa có data/processed — bỏ qua kiểm thử trên corpus thật")
class TestCorpusThat(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = get_config()
        cls.nodes = load_corpus_nodes(cls.cfg)

    def test_moi_tien_to_khop_dung_mot_file(self) -> None:
        files = corpus_files(self.cfg)
        self.assertEqual(len(files), len(self.cfg.corpus_files))

    def test_node_co_nguon_trich_va_khong_rong(self) -> None:
        self.assertGreater(len(self.nodes), 40)
        for n in self.nodes:
            self.assertTrue(n.metadata.get("nguon_trich"), f"Node thiếu nguon_trich: {n.node_id}")
            self.assertTrue(n.metadata.get("file"))

    def test_thong_ke_khop(self) -> None:
        tk = thong_ke(self.nodes)
        self.assertEqual(tk["tong_so_node"], len(self.nodes))
        self.assertEqual(tk["so_van_ban"], len(self.cfg.corpus_files))


class TestConfig(unittest.TestCase):
    def test_resolve_device_cpu(self) -> None:
        self.assertEqual(resolve_device("cpu"), "cpu")

    def test_hai_profile(self) -> None:
        self.assertEqual(set(PROFILES), {"local", "server"})

    def test_mo_ta_du_khoa(self) -> None:
        mo_ta = PROFILES["server"].mo_ta()
        for khoa in ("profile", "embed_model", "temperature", "seed", "similarity_top_k", "use_hybrid", "persist_dir"):
            self.assertIn(khoa, mo_ta)
        self.assertEqual(mo_ta["temperature"], 0.0)

    def test_profile_khong_hop_le(self) -> None:
        cu = os.environ.get("RAG_PROFILE")
        os.environ["RAG_PROFILE"] = "khong-ton-tai"
        try:
            with self.assertRaises(ValueError):
                get_config()
        finally:
            if cu is None:
                del os.environ["RAG_PROFILE"]
            else:
                os.environ["RAG_PROFILE"] = cu


if __name__ == "__main__":
    unittest.main()
