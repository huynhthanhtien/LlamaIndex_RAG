"""Độ đo và kiểm định thống kê cho phần đánh giá — chỉ dùng thư viện chuẩn.

Bổ sung so với bản cũ (eval/evaluate.py chỉ có Recall@k và MRR):
  - nDCG@k,
  - khoảng tin cậy bootstrap cho mọi chỉ số (bộ câu hỏi nhỏ nên sai số chuẩn quan trọng),
  - kiểm định McNemar chính xác cho so sánh cặp hai cấu hình trên cùng bộ câu hỏi.
"""
from __future__ import annotations

import math
import random
from collections.abc import Callable, Sequence


def hang_dau_tien(so_node: int, dung: Callable[[int], bool]) -> int | None:
    """Hạng (1-based) của Node đúng đầu tiên trong danh sách; None nếu không có Node nào đúng."""
    for i in range(so_node):
        if dung(i):
            return i + 1
    return None


def recall_at_k(hang: Sequence[int | None], k: int) -> float:
    """Tỷ lệ câu có Node đúng nằm trong k hạng đầu (hit rate@k)."""
    if not hang:
        return 0.0
    return sum(1 for r in hang if r is not None and r <= k) / len(hang)


def mrr(hang: Sequence[int | None], toi_da: int | None = None) -> float:
    """Mean Reciprocal Rank; chỉ tính các câu có hạng <= toi_da (None = mọi hạng)."""
    if not hang:
        return 0.0
    return sum(1 / r for r in hang if r is not None and (toi_da is None or r <= toi_da)) / len(hang)


def ndcg_at_k(hang: Sequence[int | None], k: int, so_lien_quan: int = 1) -> float:
    """nDCG@k với `so_lien_quan` Node đúng cho mỗi câu (mặc định 1 -> IDCG = 1)."""
    if not hang:
        return 0.0
    dcg = sum(1 / math.log2(r + 1) for r in hang if r is not None and r <= k)
    idcg = sum(1 / math.log2(i + 1) for i in range(1, so_lien_quan + 1))
    return dcg / (len(hang) * idcg) if idcg else 0.0


def bootstrap_ci(
    gia_tri: Sequence[float],
    n_lan: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Khoảng tin cậy percentile bootstrap cho giá trị trung bình.

    Trả về (trung bình, cận dưới, cận trên). Dùng để không kết luận từ chênh lệch nhỏ
    trên bộ câu hỏi ít (ví dụ bộ 02 chỉ có 10 câu).
    """
    if not gia_tri:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(gia_tri)
    tb: list[float] = []
    for _ in range(n_lan):
        mau = [gia_tri[rng.randrange(n)] for _ in range(n)]
        tb.append(sum(mau) / n)
    tb.sort()
    lo = tb[max(0, int(n_lan * alpha / 2) - 1)]
    hi = tb[min(n_lan - 1, int(n_lan * (1 - alpha / 2)))]
    return sum(gia_tri) / n, lo, hi


def mcnemar(hits_a: Sequence[bool], hits_b: Sequence[bool]) -> tuple[int, int, float]:
    """Kiểm định McNemar chính xác (hai phía) cho hai cấu hình trên cùng bộ câu hỏi.

    Trả về (b, c, p) với b = số câu chỉ A đúng, c = số câu chỉ B đúng.
    """
    b = sum(1 for x, y in zip(hits_a, hits_b) if x and not y)
    c = sum(1 for x, y in zip(hits_a, hits_b) if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return b, c, min(1.0, p)


def p95(gia_tri: Sequence[float]) -> float:
    if not gia_tri:
        return 0.0
    sx = sorted(gia_tri)
    return sx[min(len(sx) - 1, max(0, math.ceil(len(sx) * 0.95) - 1))]


def dinh_dang_ci(gt: Sequence[float]) -> str:
    tb, lo, hi = bootstrap_ci(gt)
    return f"{tb:.1%} [{lo:.1%}–{hi:.1%}]"
