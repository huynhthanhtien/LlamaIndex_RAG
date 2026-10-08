import unittest

from llama_index.core.schema import MetadataMode
from processed_loader import front_matter, load_processed, nguon_trich, thong_ke
from tests import tmp_dir

VAN_BAN = """---
ten_van_ban: "Văn bản thử"
file_goc: "x.pdf"
---

# Quy chế thử

## Chương I

### Điều 1. Nội dung một
Sinh viên phải hoàn thành đủ khối lượng tín chỉ theo quy định của nhà trường.

#### Sửa đổi Điều 1
Nội dung sửa đổi được áp dụng từ năm học mới cho tất cả sinh viên.
"""


class TestProcessedLoader(unittest.TestCase):
    def setUp(self) -> None:
        self._ctx = tmp_dir()
        d = self._ctx.__enter__()
        self.path = d / "van-ban-thu.md"
        self.path.write_text(VAN_BAN, encoding="utf-8")
        self.nodes = load_processed(self.path, "Văn bản thử")

    def tearDown(self) -> None:
        self._ctx.__exit__(None, None, None)

    def test_front_matter(self) -> None:
        meta, body = front_matter(VAN_BAN)
        self.assertEqual(meta["file_goc"], "x.pdf")
        self.assertIn("Quy chế thử", body)

    def test_so_node_va_nhan_dieu(self) -> None:
        self.assertEqual(len(self.nodes), 2)
        self.assertEqual(self.nodes[0].metadata["dieu"], "1")
        self.assertEqual(self.nodes[0].metadata["chuong"], "Chương I")
        # Node sửa đổi: nhãn nằm ở sua_doi_dieu, không có dieu
        self.assertEqual(self.nodes[1].metadata["sua_doi_dieu"], "1")
        self.assertNotIn("dieu", self.nodes[1].metadata)

    def test_metadata_rong_bi_loai(self) -> None:
        """Trước đây Node nào cũng mang chuong/dieu/sua_doi_dieu rỗng, làm nhiễu embedding."""
        for n in self.nodes:
            for k, v in n.metadata.items():
                self.assertTrue(str(v).strip(), f"metadata {k!r} rỗng vẫn còn trong Node")

    def test_chi_nguon_trich_duoc_embed(self) -> None:
        n = self.nodes[0]
        self.assertNotIn("nguon_trich", n.excluded_embed_metadata_keys)
        for k in ("file", "van_ban", "dieu", "chuong"):
            self.assertIn(k, n.excluded_embed_metadata_keys)
        embed = n.get_content(metadata_mode=MetadataMode.EMBED)
        self.assertIn("nguon_trich:", embed)
        self.assertIn("Điều 1 — Văn bản thử", embed)
        self.assertNotIn("file:", embed)

    def test_nguon_trich(self) -> None:
        self.assertEqual(nguon_trich({"dieu": "9", "van_ban": "QC SGU 2021"}), "Điều 9 — QC SGU 2021")
        self.assertEqual(
            nguon_trich({"sua_doi_dieu": "7", "van_ban": "QĐ 3183"}), "Sửa đổi Điều 7 — QĐ 3183"
        )
        self.assertEqual(nguon_trich({"phan": "ban_hanh", "van_ban": "QĐ 810"}), "Phần ban hành — QĐ 810")

    def test_thong_ke(self) -> None:
        tk = thong_ke(self.nodes)
        self.assertEqual(tk["tong_so_node"], 2)
        self.assertEqual(tk["so_van_ban"], 1)


if __name__ == "__main__":
    unittest.main()
