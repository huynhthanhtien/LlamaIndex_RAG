"""Phần dùng chung của lab: đọc văn bản, gắn metadata, chia đoạn cố định và luật chấm. Học viên không cần sửa file này.

Văn bản lấy từ tầng 2 của repo (data/processed, đã OCR và làm sạch): Quy chế đào tạo SGU 2021 (21 Điều, chỉ lấy phần
Quy chế, bỏ quyết định ban hành) và QĐ 3183/2025 sửa đổi Điều 6, 7, 9, 10 của Quy chế đó.
"""
import re
from pathlib import Path

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore, TextNode

LAB = Path(__file__).resolve().parent
ROOT = LAB.parent
THU_MUC = ROOT / "data" / "processed" / "01_quy_che_dao_tao" / "1_quy_che_dao_tao_dai_hoc"

# mã văn bản -> (file, dòng bắt đầu lấy nội dung hoặc None = lấy cả thân, tên hiển thị khi trích nguồn)
VAN_BAN: dict[str, tuple[Path, str | None, str]] = {
    "qc2021": (THU_MUC / "25_quy-che-dao-tao-trinh-do-dai-hoc-tai-truong-dai-hoc-sai-gon.md",
               "# QUY CHẾ ĐÀO TẠO TRÌNH ĐỘ ĐẠI HỌC", "Quy chế đào tạo SGU 2021"),
    "qd3183": (THU_MUC / "QD 3183.2025 - Sua doi Quy che Dao tao trinh do DH_LienQuanRutMonHoc.md",
               None, "QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021"),
}

# Heading cấp 3 ("### Điều 9. ...") là Điều của văn bản; cấp 4 ("#### 3. Sửa đổi ... Điều 9:") là mục sửa đổi Điều đó
DIEU = re.compile(r"(?m)^#{3,4} .*?Điều (\d+)")
KHOA = re.compile(r"\bkh(?:óa|oá|oa)\s*(?:tuyển\s*sinh\s*)?(?:năm\s*)?(20\d\d)\b", re.IGNORECASE)


def doc_van_ban(ma: str) -> str:
    """Thân văn bản (bỏ front matter "---"); với Quy chế thì bỏ cả phần quyết định ban hành ở đầu file."""
    path, bat_dau, _ = VAN_BAN[ma]
    text = path.read_text(encoding="utf-8").split("---\n", 2)[2]
    return text[text.index(bat_dau):] if bat_dau else text


def gan_metadata(node: TextNode, van_ban: str, cac_dieu: list[str]) -> TextNode:
    """Metadata để chấm và trích nguồn. Embedding chỉ nhận nội dung (so sánh cách chia cho công bằng); LLM thấy tên
    văn bản và số Điều để trích dẫn."""
    node.metadata = {"van_ban": van_ban, "ten": VAN_BAN[van_ban][2], "cac_dieu": ";".join(cac_dieu)}
    node.excluded_embed_metadata_keys = list(node.metadata)
    node.excluded_llm_metadata_keys = ["van_ban"]
    return node


def dieu_trong_khoang(text: str, dau: int, cuoi: int) -> list[str]:
    """Các Điều có nội dung giao với đoạn text[dau:cuoi]. Mỗi Điều kéo dài từ heading của nó tới heading kế tiếp."""
    moc = [(m.start(), m[1]) for m in DIEU.finditer(text)] + [(len(text), "")]
    ket: list[str] = []
    for (bd, so), (kt, _) in zip(moc, moc[1:]):
        if bd < cuoi and kt > dau and so not in ket:
            ket.append(so)
    return ket


def chia_co_dinh(text: str, van_ban: str, chunk_size: int, chunk_overlap: int = 20) -> list[TextNode]:
    """Cách chia mặc định của LlamaIndex: SentenceSplitter cắt theo số token (tokenizer tiktoken), không biết Điều.

    Metadata `cac_dieu` gắn SAU khi cắt, theo vị trí ký tự của đoạn trong văn bản: một đoạn vắt qua hai Điều
    được ghi cả hai.
    """
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes: list[TextNode] = []
    for n in splitter.get_nodes_from_documents([Document(text=text)]):
        assert isinstance(n, TextNode) and n.start_char_idx is not None and n.end_char_idx is not None
        nodes.append(gan_metadata(n, van_ban, dieu_trong_khoang(text, n.start_char_idx, n.end_char_idx)))
    return nodes


def khoa_trong_cau_hoi(cau_hoi: str) -> int | None:
    """"Sinh viên khóa 2025 ..." -> 2025; không nêu khóa -> None."""
    m = KHOA.search(cau_hoi)
    return int(m[1]) if m else None


def cac_dieu(n: NodeWithScore) -> list[str]:
    return [x for x in str(n.node.metadata.get("cac_dieu", "")).split(";") if x]


def la_dung(n: NodeWithScore, q: dict[str, str]) -> bool:
    """Luật chấm: Node đúng khi cùng văn bản với nhãn và chứa Điều của nhãn."""
    return n.node.metadata.get("van_ban") == q["nguon"] and q["dieu"] in cac_dieu(n)


def nhan_nguon(n: NodeWithScore) -> str:
    """"Quy chế đào tạo SGU 2021 – Điều 9" (đoạn vắt qua nhiều Điều: "Điều 9, 10")."""
    ds = cac_dieu(n)
    return f"{n.node.metadata.get('ten', '')} – Điều {', '.join(ds)}" if ds else str(n.node.metadata.get("ten", ""))
