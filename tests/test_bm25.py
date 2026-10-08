import unittest

from bm25 import BM25, BM25Retriever, bo_dau, tach_tu
from llama_index.core.schema import TextNode


def node(text: str, **meta: str) -> TextNode:
    return TextNode(text=text, metadata=meta or {"van_ban": "QC thử"})


NODES = [
    node("Điều 9. Thang điểm chữ gồm A, B+, B, C+, C, D+, D, F.", dieu="9", van_ban="QC thử"),
    node("Điều 6. Một năm học có 02 học kì chính và 01 học kì phụ.", dieu="6", van_ban="QC thử"),
    node("Điều 19. Sinh viên dùng bằng giả bị buộc thôi học.", dieu="19", van_ban="QC thử"),
]


class TestBM25(unittest.TestCase):
    def setUp(self) -> None:
        self.r = BM25Retriever(nodes=NODES, similarity_top_k=3)

    def test_bo_dau_va_tach_tu(self) -> None:
        self.assertEqual(bo_dau("Điều"), "Dieu")  # bo_dau giữ nguyên chữ hoa
        self.assertEqual(tach_tu("Điều")[0], "dieu")  # tach_tu mới hạ chữ
        self.assertIn("dieu", tach_tu("Điều 9"))
        self.assertIn("9", tach_tu("Điều 9"))

    def test_truy_hoi_theo_ky_hieu(self) -> None:
        """Điểm yếu của embedding: ký hiệu B+ / số hiệu. BM25 phải bắt được."""
        top = self.r.retrieve("điểm B+ nằm ở đâu")
        self.assertEqual(top[0].node.metadata["dieu"], "9")

    def test_truy_hoi_khi_thieu_dau(self) -> None:
        top = self.r.retrieve("dieu 6 mot nam hoc co may hoc ki")
        self.assertEqual(top[0].node.metadata["dieu"], "6")

    def test_khong_khop_thi_tra_rong(self) -> None:
        self.assertEqual(self.r.retrieve("zzz qqq"), [])

    def test_diem_giam_dan(self) -> None:
        diem = [n.score or 0.0 for n in self.r.retrieve("học kì chính")]
        self.assertEqual(diem, sorted(diem, reverse=True))

    def test_bm25_tinh_toan(self) -> None:
        bm = BM25([tach_tu("học kì chính"), tach_tu("bằng giả")])
        diem = bm.scores(tach_tu("bằng giả"))
        self.assertEqual(len(diem), 2)
        self.assertGreater(diem[1], diem[0])


if __name__ == "__main__":
    unittest.main()
