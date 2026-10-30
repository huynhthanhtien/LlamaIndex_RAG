"""Lời giải Bài tập 2, 3, 4 của lab (xem lab/README.md). Cùng chữ ký hàm với lab/bai_lam.py."""
import re

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore, TextNode

from chung import DIEU, cac_dieu, gan_metadata, khoa_trong_cau_hoi

HEADING = re.compile(r"(?m)^(?=#{1,4} )")

# QĐ 3183 Điều 2: "có hiệu lực kể từ ngày ký. Khoản 3, 4, 5 Điều 1 áp dụng đối với các khóa tuyển sinh từ năm 2025".
# Khoản 1, 2 sửa Điều 6, 7 (áp dụng mọi khóa: None); khoản 3, 4, 5 sửa Điều 9, 9, 10 (từ khóa 2025).
SUA_DOI_3183: dict[str, int | None] = {"6": None, "7": None, "9": 2025, "10": 2025}


def chia_theo_dieu(text: str, van_ban: str, chunk_size: int = 0) -> list[TextNode]:
    nodes: list[TextNode] = []
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=20) if chunk_size else None
    for khoi in HEADING.split(text):
        m = DIEU.match(khoi)
        if not m:
            continue  # tiêu đề văn bản, tên Chương: không thuộc Điều nào
        tieu_de, _, than = khoi.partition("\n")
        noi_dung = f"{tieu_de.lstrip('# ').strip()}\n{than.strip()}".strip()
        doan = splitter.split_text(noi_dung) if splitter else [noi_dung]
        nodes += [gan_metadata(TextNode(text=d), van_ban, [m[1]]) for d in doan]
    return nodes


def ap_dung(n: NodeWithScore, khoa: int) -> bool | None:
    """Node là mục sửa đổi của QĐ 3183: True/False = áp dụng/không áp dụng cho khóa; None = không phải mục sửa đổi."""
    if n.node.metadata.get("van_ban") != "qd3183":
        return None
    tu = [SUA_DOI_3183[d] for d in cac_dieu(n) if d in SUA_DOI_3183]
    return any(t is None or khoa >= t for t in tu) if tu else None


def sap_xep_theo_phien_ban(nodes: list[NodeWithScore], cau_hoi: str) -> list[NodeWithScore]:
    khoa = khoa_trong_cau_hoi(cau_hoi)
    if khoa is None:
        return nodes  # không biết khóa: giữ thứ tự của retriever (bản gốc và bản sửa đổi đều có thể đúng)
    da_sua = {d for d, tu in SUA_DOI_3183.items() if tu is None or khoa >= tu}

    def hang(n: NodeWithScore) -> int:
        if ap_dung(n, khoa):
            return 0  # mục sửa đổi áp dụng cho khóa này
        if ap_dung(n, khoa) is False:
            return 3  # mục sửa đổi không áp dụng cho khóa này
        if n.node.metadata.get("van_ban") == "qc2021" and set(cac_dieu(n)) & da_sua:
            return 2  # Điều gốc đã bị sửa cho khóa này
        return 1

    return sorted(nodes, key=hang)  # sorted ổn định: cùng hạng thì giữ thứ tự điểm của retriever


def co_can_cu(nodes: list[NodeWithScore], nguong: float) -> bool:
    # Lấy điểm cao nhất chứ không lấy nodes[0]: sau Bài tập 3 thứ tự không còn giảm dần theo điểm
    return max((n.score or 0.0 for n in nodes), default=0.0) >= nguong
