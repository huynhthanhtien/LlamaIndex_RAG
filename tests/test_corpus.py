import dataclasses
import os
import unittest
from pathlib import Path

from config import PROFILES, get_config, resolve_device
from processed_loader import ROOT as ROOT_LOADER, corpus_files, load_corpus_nodes, thong_ke, vi_tri_goc

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

    def test_trich_dan_mo_dung_doan_goc(self) -> None:
        """Mapping trích dẫn -> đoạn gốc (nhận xét tuần 7, ý 8): mỗi Node trỏ tới một dòng riêng trong file tầng 2,
        dòng đó chứa đầu Node, và mọi Node cùng nhãn nguồn "<văn bản> – Điều N" đều nằm trong cùng một file."""
        vi_tri: dict[str, str] = {}
        file_cua_nhan: dict[str, set[str]] = {}
        for n in self.nodes:
            v = vi_tri_goc(self.cfg, n.metadata, n.text)
            self.assertIn(":", v, f"không tìm được dòng gốc của Node {n.metadata.get('nguon_trich')}")
            path, dong = v.rsplit(":", 1)
            dau = next(x.strip() for x in n.text.splitlines() if x.strip())
            self.assertIn(dau[:40], (ROOT_LOADER / path).read_text(encoding="utf-8").splitlines()[int(dong) - 1])
            self.assertNotIn(v, vi_tri, f"hai Node cùng trỏ {v}: {vi_tri.get(v)} và {n.metadata.get('nguon_trich')}")
            vi_tri[v] = str(n.metadata.get("nguon_trich"))
            # Cùng khóa với retriever.node_label (không import retriever: kéo theo torch qua index_builder)
            nhan = "|".join(str(n.metadata.get(k, "")) for k in ("van_ban", "dieu", "sua_doi_dieu"))
            file_cua_nhan.setdefault(nhan, set()).add(path)
        self.assertEqual({k: f for k, f in file_cua_nhan.items() if len(f) > 1}, {})


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

    def test_replace_khong_ap_lai_bien_moi_truong(self) -> None:
        """RAG_RERANK / RAG_LOC_PHIEN_BAN chỉ áp ở get_config(); cấu hình ablation dựng bằng replace() phải giữ đúng
        giá trị yêu cầu (trước đây __post_init__ ép lại theo shell: cấu hình "vector" vẫn rerank + lọc phiên bản)."""
        cu = {k: os.environ.get(k) for k in ("RAG_PROFILE", "RAG_RERANK", "RAG_LOC_PHIEN_BAN")}
        os.environ.update(RAG_PROFILE="server", RAG_RERANK="0", RAG_LOC_PHIEN_BAN="0")
        try:
            cfg = get_config()
            self.assertFalse(cfg.use_rerank)
            self.assertFalse(cfg.loc_phien_ban)
            vector = dataclasses.replace(cfg, use_rerank=True, loc_phien_ban=True)
            self.assertTrue(vector.use_rerank)
            self.assertTrue(vector.loc_phien_ban)
            # get_config() trả bản sao: profile dùng chung giữ nguyên
            self.assertTrue(PROFILES["server"].use_rerank)
        finally:
            for k, v in cu.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
