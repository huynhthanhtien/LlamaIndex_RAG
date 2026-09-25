import logging
import re
from pathlib import Path
from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

logger = logging.getLogger(__name__)

DIEU_PATTERN = re.compile(r"(Điều\s+\d+[.:].*?)(?=Điều\s+\d+[.:]|\Z)", re.DOTALL)
DIEU_NUMBER_PATTERN = re.compile(r"Điều\s+(\d+)")


def extract_dieu_number(text: str) -> str:
    """Trích xuất số thứ tự của Điều từ đoạn văn bản (ví dụ: 'Điều 15.' -> '15')."""
    match = DIEU_NUMBER_PATTERN.match(text.strip())
    return match.group(1) if match else "khong_ro"


def parse_by_dieu(documents: list[Document], max_chunk_tokens: int = 1024) -> list[TextNode]:
    """Phân tách danh sách Document thành các TextNode theo từng Điều.

    - Nếu một Điều dài hơn max_chunk_tokens, tiến hành sub-chunking bằng SentenceSplitter.
    - Giữ nguyên toàn bộ metadata gốc của Document và gắn thêm metadata['dieu'].
    - Trường hợp Document không có 'Điều', giữ nguyên toàn bộ và gắn dieu='khong_co_dieu'.
    """
    sub_splitter = SentenceSplitter(chunk_size=max_chunk_tokens, chunk_overlap=50)
    all_nodes: list[TextNode] = []
    dieu_khong_khop = 0

    for doc in documents:
        matches = DIEU_PATTERN.findall(doc.text)

        if not matches:
            dieu_khong_khop += 1
            all_nodes.append(
                TextNode(
                    text=doc.text.strip(),
                    metadata={"dieu": "khong_co_dieu", **doc.metadata},
                )
            )
            continue

        for dieu_text in matches:
            dieu_so = extract_dieu_number(dieu_text)
            base_metadata = {"dieu": dieu_so, **doc.metadata}
            estimated_tokens = len(dieu_text.split())

            if estimated_tokens <= max_chunk_tokens:
                all_nodes.append(TextNode(text=dieu_text.strip(), metadata=base_metadata))
            else:
                sub_texts = sub_splitter.split_text(dieu_text)
                for j, sub_text in enumerate(sub_texts):
                    all_nodes.append(
                        TextNode(
                            text=sub_text,
                            metadata={**base_metadata, "phan": j + 1},
                        )
                    )

    if dieu_khong_khop:
        logger.warning(f"{dieu_khong_khop} Document không khớp mẫu 'Điều X'.")

    return all_nodes


def validate_nodes(nodes: list[TextNode]) -> dict[str, Any]:
    """Thống kê định lượng chất lượng của danh sách TextNode sau khi parse."""
    total = len(nodes)
    khong_ro = sum(1 for n in nodes if n.metadata.get("dieu") in ("khong_ro", "khong_co_dieu"))
    avg_len = sum(len(n.text) for n in nodes) // max(total, 1)
    return {
        "tong_so_node": total,
        "node_khong_ro_dieu": khong_ro,
        "ty_le_khong_ro": f"{khong_ro / max(total, 1):.1%}",
        "do_dai_trung_binh_ky_tu": avg_len,
    }


if __name__ == "__main__":
    sample_ocr_path = Path(__file__).resolve().parent.parent / "data" / "ocr" / "4. QuyCheDaoTaoDHSG 2021.md"

    if sample_ocr_path.exists():
        print(f"Đang đọc dữ liệu kiểm tra từ: {sample_ocr_path.name}")
        with open(sample_ocr_path, "r", encoding="utf-8") as f:
            content = f.read()

        sample_doc = Document(
            text=content,
            metadata={"source": sample_ocr_path.name, "doc_type": "quy_che"},
        )
        nodes = parse_by_dieu([sample_doc])
        stats = validate_nodes(nodes)

        print("\n--- KẾT QUẢ THỐNG KÊ NODES ---")
        for k, v in stats.items():
            print(f"- {k}: {v}")

        print(f"\n--- 3 NODES ĐẦU TIÊN (Tổng cộng {len(nodes)} nodes) ---")
        for idx, node in enumerate(nodes[:3], start=1):
            print(f"\n[Node {idx}] - Metadata: {node.metadata}")
            preview = node.text[:120].replace('\n', ' ')
            print(f"Nội dung: {preview}...")
    else:
        print("Không tìm thấy file mẫu để test.")
