# Báo cáo: Xây dựng ingestion.py từ cơ bản đến nâng cao

> Tài liệu ghi lại quá trình tự xây dựng `ingestion.py` — Module 1 (Ingestion) của pipeline RAG — theo lối tăng dần độ phức tạp. Mỗi tầng chỉ thêm đúng một ý, chạy thử và thấy vấn đề bằng mắt trước khi thêm tầng tiếp theo.

---

## Tầng 0 — Đặt vấn đề: thử cách "ngây thơ" nhất trước

Cách nhanh nhất LlamaIndex cung cấp để đọc PDF:

```python
from llama_index.core import SimpleDirectoryReader

documents = SimpleDirectoryReader(input_files=["data/raw/quy_che_dao_tao_2021.pdf"]).load_data()
print(len(documents))
print(documents[0].text[:200])
```

**Chạy thử với file Quy chế thật — kết quả:**
```python
print(len(documents[0].text))   # gần bằng 0, hoặc rất ít ký tự
```

Không lỗi, không crash — nhưng gần như **không có nội dung**. Đây là vấn đề gốc cần giải quyết, không phải giả định trước.

---

## Tầng 1 — Tìm hiểu vì sao: PDF là gì bên trong

Một file PDF có thể chứa hai loại nội dung khác nhau:

| Loại | Bên trong PDF có gì | `SimpleDirectoryReader` đọc được không |
|---|---|---|
| PDF có text layer | Ký tự đã số hoá, máy đọc trực tiếp được | Có |
| PDF scan (ảnh chụp) | Chỉ là ảnh bitmap, không có "chữ" theo nghĩa máy hiểu | **Không** |

**Tự kiểm tra file mình có bằng cách này (không cần code, thử tay):** mở file PDF, thử bôi đen một đoạn chữ bằng chuột. Nếu chọn được và copy ra chữ bình thường → có text layer. Nếu không chọn được gì → là bản scan.

**Kết luận:** file Quy chế đào tạo là bản scan — cần OCR (Optical Character Recognition), không đọc trực tiếp được.

---

## Tầng 2 — OCR một ảnh đơn giản trước, chưa đụng tới PDF

Tách vấn đề: hiểu OCR hoạt động ra sao trên **một ảnh tĩnh** trước khi ghép với PDF.

```python
import pytesseract
from PIL import Image

# Giả sử có sẵn một ảnh chụp màn hình có chữ, ví dụ "test.png"
img = Image.open("test.png")
text = pytesseract.image_to_string(img, lang="vie")
print(text)
```

Nếu dòng này chạy được và ra chữ đúng — xác nhận Tesseract + gói ngôn ngữ `vie` đã cài đúng, tách biệt hoàn toàn khỏi vấn đề PDF. Nếu lỗi `TesseractNotFoundError` ở bước này, biết ngay lỗi nằm ở cài đặt hệ thống, không phải logic code.

---

## Tầng 3 — Biến 1 trang PDF thành ảnh

Tesseract chỉ nhận ảnh, không nhận PDF trực tiếp — cần một bước trung gian.

```python
from pdf2image import convert_from_path

pages = convert_from_path("data/raw/quy_che_dao_tao_2021.pdf", dpi=300)
print(f"Số trang: {len(pages)}")
print(type(pages[0]))   # <class 'PIL.PpmImagePlugin.PpmImageFile'> — đúng là ảnh PIL
```

`convert_from_path` render từng trang PDF thành một đối tượng ảnh (PIL Image) — cùng loại dữ liệu mà `pytesseract` ở Tầng 2 đã nhận vào thành công.

---

## Tầng 4 — Ghép Tầng 2 + Tầng 3: OCR đúng 1 trang PDF

```python
trang_dau = pages[0]
text = pytesseract.image_to_string(trang_dau, lang="vie")
print(text[:300])
```

Đây là lần đầu tiên **thật sự đọc được nội dung** từ file PDF scan. Đọc kỹ đoạn in ra — kiểm tra dấu tiếng Việt có đúng không trước khi đi tiếp.

---

## Tầng 5 — Vòng lặp OCR toàn bộ trang

```python
tat_ca_text = []
for i, page in enumerate(pages, start=1):
    text = pytesseract.image_to_string(page, lang="vie")
    tat_ca_text.append(text)
    print(f"Đã OCR trang {i}/{len(pages)}")

print(f"Tổng {sum(len(t) for t in tat_ca_text)} ký tự")
```

Chạy chậm hơn hẳn Tầng 4 (OCR mất vài giây/trang, nhân với số trang) — quan sát để biết thời gian thực tế, quan trọng khi ước lượng thời gian chạy toàn bộ pipeline.

---

## Tầng 6 — Đưa vào Document của LlamaIndex, CHƯA có metadata

```python
from llama_index.core import Document

documents = []
for i, page in enumerate(pages, start=1):
    text = pytesseract.image_to_string(page, lang="vie")
    documents.append(Document(text=text))

print(len(documents))
print(documents[0].text[:100])
```

Có `Document` hợp lệ — nhưng nếu sau này gộp nhiều file PDF khác nhau vào chung một danh sách `documents`, **không biết Document nào đến từ file nào, trang nào**. Vấn đề này chưa xuất hiện rõ khi chỉ có 1 file, nhưng sẽ lộ ra ngay ở tầng sau.

---

## Tầng 7 — Thêm metadata: nguồn và số trang

```python
documents = []
for i, page in enumerate(pages, start=1):
    text = pytesseract.image_to_string(page, lang="vie")
    documents.append(Document(
        text=text,
        metadata={"nguon": "Quy chế đào tạo 2021", "trang": i},
    ))

print(documents[5].metadata)   # {'nguon': 'Quy chế đào tạo 2021', 'trang': 6}
```

`metadata["trang"]` sẽ cần thiết về sau — nếu OCR sai ở đâu, biết chính xác trang nào để quay lại kiểm tra thủ công, không phải dò cả file.

---

## Tầng 8 — Đóng gói thành hàm tái sử dụng

Tới đây, đoạn code đã lặp lại cấu trúc khá rõ — đóng thành hàm để dùng cho nhiều file khác nhau:

```python
def load_scanned_pdf(pdf_path: str, source_name: str, lang: str = "vie", dpi: int = 300) -> list[Document]:
    pages = convert_from_path(pdf_path, dpi=dpi)
    documents = []
    for i, page in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page, lang=lang)
        documents.append(Document(
            text=text,
            metadata={"nguon": source_name, "trang": i},
        ))
    return documents
```

**Test:**
```python
docs = load_scanned_pdf("data/raw/quy_che_dao_tao_2021.pdf", "Quy chế đào tạo 2021")
print(len(docs))
```

---

## Tầng 9 — Ca biên: file không tồn tại

```python
docs = load_scanned_pdf("data/raw/file_khong_ton_tai.pdf", "Test")
```

**Kết quả:** một traceback lỗi khó đọc từ bên trong `pdf2image`, không rõ ràng cho người dùng. Cần tự bắt lỗi và báo rõ ràng hơn:

```python
from pathlib import Path

class ScannedPDFLoadError(Exception):
    """Ném ra khi không đọc/OCR được một file PDF."""


def load_scanned_pdf(pdf_path: str, source_name: str, lang: str = "vie", dpi: int = 300) -> list[Document]:
    path = Path(pdf_path)
    if not path.exists():
        raise ScannedPDFLoadError(f"Không tìm thấy file: {pdf_path}")

    pages = convert_from_path(str(path), dpi=dpi)
    documents = []
    for i, page in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page, lang=lang)
        documents.append(Document(text=text, metadata={"nguon": source_name, "trang": i}))
    return documents
```

**Test lại:**
```python
try:
    load_scanned_pdf("data/raw/khong_ton_tai.pdf", "Test")
except ScannedPDFLoadError as e:
    print(f"Bắt được lỗi rõ ràng: {e}")
```

---

## Tầng 10 — Ca biên: một trang OCR lỗi không được làm hỏng cả file

Nếu trang thứ 5 (trong 17 trang) vì lý do nào đó khiến `pytesseract` ném lỗi, code hiện tại sẽ **crash toàn bộ**, mất luôn 16 trang đã OCR thành công trước đó.

```python
def load_scanned_pdf(pdf_path: str, source_name: str, lang: str = "vie", dpi: int = 300) -> list[Document]:
    path = Path(pdf_path)
    if not path.exists():
        raise ScannedPDFLoadError(f"Không tìm thấy file: {pdf_path}")

    pages = convert_from_path(str(path), dpi=dpi)
    documents = []
    failed_pages = []

    for i, page in enumerate(pages, start=1):
        try:
            text = pytesseract.image_to_string(page, lang=lang)
        except Exception as e:
            print(f"[LỖI] Trang {i}: {e}")
            failed_pages.append(i)
            text = ""   # vẫn tạo Document, chỉ là rỗng — không mất cả file

        documents.append(Document(text=text, metadata={"nguon": source_name, "trang": i}))

    if failed_pages:
        print(f"Cảnh báo: {len(failed_pages)} trang lỗi OCR: {failed_pages}")

    return documents
```

**Nguyên tắc rút ra:** lỗi cục bộ (1 trang) không nên làm sập toàn bộ tiến trình (17 trang) — xử lý lỗi ở đúng phạm vi nhỏ nhất có thể.

---

## Tầng 11 — Cảnh báo chất lượng thấp một cách chủ động

Có trường hợp OCR "chạy thành công" (không ném exception) nhưng **kết quả gần như rỗng** — do trang mờ, hoặc gói ngôn ngữ `vie` không cài đúng. Đây là lỗi âm thầm, khó phát hiện nếu không chủ động kiểm tra:

```python
total_chars = sum(len(d.text) for d in documents)

if total_chars < 100:
    print(
        f"CẢNH BÁO: Tổng ký tự OCR rất thấp ({total_chars}) cho {pdf_path} — "
        "kiểm tra lại chất lượng bản scan hoặc gói ngôn ngữ 'vie' đã cài chưa."
    )
```

**Test cố tình gây lỗi này để thấy cảnh báo hoạt động:**
```python
# Giả lập bằng cách gọi image_to_string với lang sai (ví dụ "eng" cho ảnh tiếng Việt)
text_sai = pytesseract.image_to_string(pages[0], lang="eng")
print(len(text_sai))   # vẫn ra ký tự, nhưng sai lệch nhiều — không phải 0, khó phát hiện bằng đếm ký tự đơn thuần
```

Lưu ý: đếm ký tự chỉ phát hiện được trường hợp **quá ít** chữ — không phát hiện được trường hợp có đủ chữ nhưng **sai ngôn ngữ/sai dấu**. Cách đáng tin cậy hơn vẫn là tự đọc thử vài đoạn bằng mắt.

---

## Tầng 12 — Đọc nhiều file cùng lúc (load_corpus)

Toàn bộ các tầng trên chỉ xử lý 1 file. Corpus thật có 2 file (Quy chế 2021 + Sửa đổi 2025) — cần một hàm gộp:

```python
CORPUS_SOURCES = [
    ("data/raw/quy_che_dao_tao_2021.pdf", "Quy chế đào tạo 2021"),
    ("data/raw/qd_sua_doi_2025.pdf", "QĐ sửa đổi 2025"),
]

def load_corpus(sources: list[tuple[str, str]] | None = None) -> list[Document]:
    sources = sources or CORPUS_SOURCES
    all_documents = []

    for pdf_path, source_name in sources:
        try:
            docs = load_scanned_pdf(pdf_path, source_name)
            all_documents.extend(docs)
        except ScannedPDFLoadError as e:
            print(f"Bỏ qua nguồn '{source_name}' do lỗi: {e}")
            continue

    return all_documents
```

**Nguyên tắc giống Tầng 10, áp dụng ở cấp cao hơn:** một file lỗi (ví dụ chưa tải về) không nên chặn việc xử lý các file còn lại — dùng `try/except` quanh từng file, không quanh cả vòng lặp.

**Test:**
```python
documents = load_corpus()
print(f"Tổng: {len(documents)} Document từ {len(CORPUS_SOURCES)} nguồn")
```

---

## Tầng 13 — Nâng cao: tự động phát hiện có cần OCR hay không

Ở các tầng trên, ta **luôn giả định** file là bản scan, luôn OCR. Nhưng nếu sau này thêm một file **có sẵn text layer** (không phải scan), việc luôn OCR sẽ chậm và không cần thiết một cách vô ích.

```python
def has_text_layer(pdf_path: str, min_chars: int = 50) -> bool:
    """Kiểm tra nhanh một PDF có text layer hay là bản scan thuần ảnh."""
    from llama_index.core import SimpleDirectoryReader

    try:
        docs = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
        total_chars = sum(len(d.text) for d in docs)
        return total_chars >= min_chars
    except Exception:
        return False
```

**Test với file đã biết là scan:**
```python
print(has_text_layer("data/raw/quy_che_dao_tao_2021.pdf"))   # False — đúng như đã xác nhận từ đầu
```

Hàm này **chưa được gọi tự động** trong `load_corpus()` — để vậy có chủ đích: OCR luôn tốn thời gian hơn đọc trực tiếp, nên việc quyết định "có OCR hay không" nên là lựa chọn tường minh của người gọi hàm, không nên tự động ẩn đi quyết định quan trọng này.

---

## Tầng 14 — Nâng cao: logging thay vì print

Toàn bộ các tầng trên dùng `print()` để quan sát — đủ dùng khi tự học/debug, nhưng không phù hợp khi ráp vào pipeline chạy thật (không phân biệt được đâu là log thường, đâu là lỗi nghiêm trọng khi nhìn lại sau).

```python
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Thay print(f"Đã OCR trang {i}") bằng:
logger.info(f"Đã OCR trang {i}/{len(pages)}")

# Thay print(f"[LỖI] Trang {i}: {e}") bằng:
logger.error(f"OCR lỗi ở trang {i}: {e}")

# Thay print("CẢNH BÁO: ...") bằng:
logger.warning("Tổng ký tự OCR rất thấp...")
```

**Lợi ích thấy được ngay:** mỗi dòng log tự có timestamp và mức độ (INFO/WARNING/ERROR) — khi chạy pipeline dài (OCR 2 file, vài chục trang), dễ dàng lọc lại xem có bao nhiêu WARNING/ERROR mà không phải đọc lại toàn bộ output.

---

## Bảng tổng kết lộ trình

| Tầng | Thêm gì | Vấn đề nó giải quyết |
|---|---|---|
| 0 | Thử `SimpleDirectoryReader` | Thấy PDF scan không đọc được — đặt đúng vấn đề |
| 1 | Tìm hiểu PDF scan vs có text layer | Hiểu nguyên nhân gốc |
| 2 | OCR 1 ảnh tĩnh | Tách riêng, xác nhận Tesseract hoạt động |
| 3 | `convert_from_path` | Biến PDF thành ảnh để Tesseract đọc được |
| 4 | Ghép OCR + PDF-to-image | Lần đầu đọc được nội dung thật từ PDF scan |
| 5 | Vòng lặp nhiều trang | Xử lý toàn văn bản, không chỉ 1 trang |
| 6 | Đưa vào `Document` | Chuẩn hoá theo định dạng LlamaIndex |
| 7 | Thêm metadata nguồn/trang | Chuẩn bị cho khả năng gộp nhiều file sau này |
| 8 | Đóng gói thành hàm | Tái sử dụng, không lặp code |
| 9 | Xử lý file không tồn tại | Lỗi rõ ràng thay vì traceback khó đọc |
| 10 | Xử lý lỗi từng trang riêng | 1 trang lỗi không phá cả file |
| 11 | Cảnh báo chất lượng thấp | Phát hiện lỗi âm thầm (OCR "thành công" nhưng rỗng) |
| 12 | `load_corpus()` nhiều file | Gộp nhiều nguồn, lỗi 1 nguồn không chặn nguồn khác |
| 13 | `has_text_layer()` | Tự động phát hiện, tránh OCR khi không cần |
| 14 | Logging thay `print()` | Log có cấu trúc, lọc được khi pipeline lớn |

---

## Bản hoàn chỉnh — gộp mọi tầng thành `ingestion.py`

```python
import logging
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from llama_index.core import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CORPUS_SOURCES = [
    ("data/raw/quy_che_dao_tao_2021.pdf", "Quy chế đào tạo 2021"),
    ("data/raw/qd_sua_doi_2025.pdf", "QĐ sửa đổi 2025"),
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
```

---

## Bước kiểm chứng cuối cùng

```fish
cd src
python3 ingestion.py
```

