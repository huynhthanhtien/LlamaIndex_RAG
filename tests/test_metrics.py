import unittest

from metrics import bootstrap_ci, hang_dau_tien, mcnemar, mrr, ndcg_at_k, p95, recall_at_k


class TestMetrics(unittest.TestCase):
    def test_hang_dau_tien(self) -> None:
        self.assertEqual(hang_dau_tien(5, lambda i: i == 2), 3)
        self.assertIsNone(hang_dau_tien(5, lambda i: False))

    def test_recall_va_mrr(self) -> None:
        hang = [1, 3, None, 10]
        self.assertEqual(recall_at_k(hang, 3), 0.5)
        self.assertEqual(recall_at_k(hang, 10), 0.75)
        self.assertAlmostEqual(mrr(hang), (1 + 1 / 3 + 0 + 1 / 10) / 4)
        self.assertAlmostEqual(mrr(hang, toi_da=3), (1 + 1 / 3 + 0 + 0) / 4)

    def test_ndcg_giam_theo_hang(self) -> None:
        self.assertAlmostEqual(ndcg_at_k([1], 3), 1.0)
        self.assertLess(ndcg_at_k([3], 3), ndcg_at_k([1], 3))
        self.assertEqual(ndcg_at_k([None], 3), 0.0)

    def test_bootstrap_ci_bao_quanh_trung_binh(self) -> None:
        tb, lo, hi = bootstrap_ci([1.0] * 8 + [0.0] * 2)
        self.assertAlmostEqual(tb, 0.8)
        self.assertLessEqual(lo, tb)
        self.assertLessEqual(tb, hi)
        self.assertGreaterEqual(lo, 0.0)
        self.assertLessEqual(hi, 1.0)

    def test_bootstrap_tat_dinh(self) -> None:
        self.assertEqual(bootstrap_ci([1, 0, 1, 1]), bootstrap_ci([1, 0, 1, 1]))

    def test_mcnemar(self) -> None:
        b, c, p = mcnemar([True, True, False, False], [True, False, True, False])
        self.assertEqual((b, c), (1, 1))
        self.assertAlmostEqual(p, 1.0)
        # A đúng 5 câu mà B sai hết -> p nhỏ
        _, _, p2 = mcnemar([True] * 5, [False] * 5)
        self.assertLess(p2, 0.1)

    def test_p95(self) -> None:
        self.assertEqual(p95([1, 2, 3, 4, 5]), 5)
        self.assertEqual(p95([]), 0.0)


if __name__ == "__main__":
    unittest.main()
