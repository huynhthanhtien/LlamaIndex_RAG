"""BM25 thuần Python cho LlamaIndex — không cần cài thêm gói ngoài.

Lý do tồn tại: câu hỏi về quy chế thường chứa ký hiệu và con số mà embedding nắm kém
("B+", "Điều 10", "150 tín chỉ", "QĐ 3183"). BM25 khớp chính xác những token này, còn
vector lo phần diễn đạt khác nghĩa; trộn hai nguồn bằng QueryFusionRetriever (xem retriever.py).

Quyết định thiết kế: tách từ về dạng **bỏ dấu** trước khi chấm điểm. Nhờ vậy câu hỏi gõ
thiếu dấu hoặc lỗi OCR ("dieu 9", "hoc cung luc") vẫn khớp văn bản có dấu. Đánh đổi: mất
phân biệt các cặp chỉ khác dấu (má/ma) — hiếm gặp và ít ảnh hưởng trong văn bản quy chế.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Sequence

from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import BaseNode, MetadataMode, NodeWithScore, QueryBundle, TextNode

TOKEN = re.compile(r"[0-9a-zA-Z\u00c0-\u1ef9]+", re.UNICODE)


def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt: 'Điều' -> 'dieu'."""
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def tach_tu(text: str, bigrams: bool = False) -> list[str]:
    """Tách thành âm tiết đã bỏ dấu; bigrams=True thêm cặp âm tiết liền kề (cụm từ)."""
    toks = [bo_dau(t).lower() for t in TOKEN.findall(text)]
    if bigrams and len(toks) > 1:
        toks += [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    return toks


class BM25:
    """BM25 Okapi trên tập tài liệu đã tách từ."""

    def __init__(self, docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.tf = [Counter(d) for d in docs]
        self.do_dai = [len(d) for d in docs]
        self.do_dai_tb = (sum(self.do_dai) / self.n) if self.n else 0.0
        df: Counter[str] = Counter()
        for tfc in self.tf:
            df.update(tfc.keys())
        # Công thức IDF có làm trơn (Robertson): luôn dương nên không cần xử lý idf âm
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query_tokens: Sequence[str]) -> list[float]:
        diem = [0.0] * self.n
        for t in set(query_tokens):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, tfc in enumerate(self.tf):
                f = tfc.get(t)
                if not f:
                    continue
                mau = f + self.k1 * (1 - self.b + self.b * self.do_dai[i] / (self.do_dai_tb or 1))
                diem[i] += idf * f * (self.k1 + 1) / mau
        return diem


class BM25Retriever(BaseRetriever):
    """Retriever BM25 đóng vai một BaseRetriever của LlamaIndex (ghép được vào QueryFusionRetriever)."""

    def __init__(
        self,
        nodes: Sequence[BaseNode],
        similarity_top_k: int = 10,
        k1: float = 1.5,
        b: float = 0.75,
        bigrams: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.nodes = list(nodes)
        self.similarity_top_k = similarity_top_k
        self.bigrams = bigrams
        self._bm25 = BM25([tach_tu(n.get_content(metadata_mode=MetadataMode.EMBED), bigrams) for n in self.nodes], k1, b)

    @classmethod
    def class_name(cls) -> str:
        return "BM25Retriever"

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        diem = self._bm25.scores(tach_tu(query_bundle.query_str, self.bigrams))
        thu_tu = sorted(range(len(diem)), key=lambda i: diem[i], reverse=True)[: self.similarity_top_k]
        return [NodeWithScore(node=self.nodes[i], score=diem[i]) for i in thu_tu if diem[i] > 0]


if __name__ == "__main__":
    nodes = [
        TextNode(text="Điều 9. Thang điểm chữ có B+, C+, D+.", metadata={"van_ban": "QC SGU 2021", "dieu": "9"}),
        TextNode(text="Điều 6. Một năm học có 02 học kì chính.", metadata={"van_ban": "QC SGU 2021", "dieu": "6"}),
    ]
    r = BM25Retriever(nodes=nodes, similarity_top_k=2)
    for q in ("B+ là gì", "dieu 6 may hoc ki", "học phí"):
        print(q, "->", [(round(n.score or 0.0, 3), n.node.get_content()[:30]) for n in r.retrieve(q)])
