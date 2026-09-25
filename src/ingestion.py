import logging
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from llama_index.core import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CORPUS_SOURCES = [
    ("data/raw/4. QuyCheDaoTaoDHSG 2021.pdf", "Quy chế đào tạo 2021"),
    # ("data/raw/qd_sua_doi_2025.pdf", "QĐ sửa đổi 2025"),
]


class ScannedPDFLoadError(Exception):
    """Ném ra khi không đọc/OCR được một file PDF."""


def has_text_layer(pdf_path: str, min_chars: int = 50) -> bool:
    """Kiểm tra nhanh một PDF có text layer hay là bản scan thuần ảnh."""
    from llama_index.core import SimpleDirectoryReader
    try:
        docs = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
        return sum(len(d.text) for d in docs) >= min_chars
    except Exception as e:
        logger.warning(f"Không đọc thử được {pdf_path}: {e}")
        return False


def load_scanned_pdf(pdf_path: str, source_name: str, lang: str = "vie", dpi: int = 300) -> list[Document]:
    path = Path(pdf_path)
    if not path.exists():
        raise ScannedPDFLoadError(f"Không tìm thấy file: {pdf_path}")

    logger.info(f"Bắt đầu OCR: {pdf_path} (nguồn: {source_name})")

    try:
        pages = convert_from_path(str(path), dpi=dpi)
    except Exception as e:
        raise ScannedPDFLoadError(f"Lỗi khi render PDF thành ảnh ({pdf_path}): {e}") from e

    documents: list[Document] = []
    failed_pages: list[int] = []

    for i, page in enumerate(pages, start=1):
        try:
            text = pytesseract.image_to_string(page, lang=lang)
        except Exception as e:
            logger.error(f"OCR lỗi ở trang {i} của {pdf_path}: {e}")
            failed_pages.append(i)
            text = ""

        documents.append(Document(
            text=text,
            metadata={"nguon": source_name, "trang": i, "file_goc": path.name},
        ))

    if failed_pages:
        logger.warning(f"{len(failed_pages)}/{len(pages)} trang OCR lỗi: {failed_pages}")

    total_chars = sum(len(d.text) for d in documents)
    logger.info(f"Hoàn tất OCR {path.name}: {len(documents)} trang, tổng {total_chars} ký tự")

    if total_chars < 100:
        logger.warning(
            f"Tổng ký tự OCR rất thấp ({total_chars}) cho {pdf_path} — "
            "kiểm tra chất lượng bản scan hoặc gói ngôn ngữ 'vie'."
        )

    return documents


def load_corpus(sources: list[tuple[str, str]] | None = None) -> list[Document]:
    sources = sources or CORPUS_SOURCES
    all_documents: list[Document] = []

    for pdf_path, source_name in sources:
        try:
            docs = load_scanned_pdf(pdf_path, source_name)
            all_documents.extend(docs)
        except ScannedPDFLoadError as e:
            logger.error(f"Bỏ qua nguồn '{source_name}' do lỗi: {e}")
            continue

    logger.info(f"Tổng cộng nạp được {len(all_documents)} Document từ {len(sources)} nguồn.")
    return all_documents


if __name__ == "__main__":
    documents = load_corpus()
    for d in documents[:3]:
        print("---")
        print("Metadata:", d.metadata)
        print("Trích đoạn:", d.text[:200].replace("\n", " "))
