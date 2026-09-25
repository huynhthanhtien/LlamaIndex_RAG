# Báo cáo: Xây dựng node_parser.py từ cơ bản đến nâng cao

Tài liệu ghi lại quá trình tự xây dựng `node_parser.py` — Module 2 (Node) của pipeline RAG — theo lối tăng dần độ phức tạp: mỗi tầng chỉ thêm đúng một ý mới, chạy thử và quan sát vấn đề trước khi thêm tầng tiếp theo. Không viết thẳng bản hoàn chỉnh — mục tiêu là hiểu **vì sao** mỗi dòng code tồn tại.

---

## Tầng 0 — Đặt vấn đề (chưa code)

Nếu không cắt Document thành Node nhỏ hơn:

```python
from llama_index.core import Document, VectorStoreIndex

doc = Document(text="... 5000 từ liên tục ...")
index = VectorStoreIndex.from_documents([doc])
```

Vẫn chạy được, không lỗi — nhưng một vector duy nhất phải đại diện cho toàn bộ nội dung trộn lẫn. Hỏi về "học phí" hay "nghỉ học" đều trả về cùng một Node, vì chỉ có một Node tồn tại.

> **Kết luận:** Cắt nhỏ không phải yêu cầu kỹ thuật bắt buộc, mà là điều kiện tiên quyết để tìm kiếm phân biệt được chủ đề.

---

## Tầng 1 — Cắt thô nhất, tự tay, không dùng thư viện

```python
def cat_tho(text: str, so_ky_tu_moi_doan: int = 100) -> list[str]:
    doan = []
    for i in range(0, len(text), so_ky_tu_moi_doan):
        doan.append(text[i:i + so_ky_tu_moi_doan])
    return doan
```

**Thử nghiệm:**

```python
text = "Điều 1. Sinh viên phải đóng học phí đúng hạn theo thông báo của trường."
for d in cat_tho(text, 30):
    print(repr(d))
```

**Kết quả — thấy vấn đề ngay:**

```text
'Điều 1. Sinh viên phải đóng h'
'ọc phí đúng hạn theo thông bá'
'o của trường.'
```

_Vấn đề:_ Cắt giữa từ "học" → "h" + "ọc". Cắt cứng theo số lượng ký tự không hiểu ranh giới từ/câu.

---

## Tầng 2 — Dùng SentenceSplitter, cắt theo câu

```python
from llama_index.core.node_parser import SentenceSplitter

splitter = SentenceSplitter(chunk_size=30, chunk_overlap=0)
doan = splitter.split_text(text)
```

Giải quyết vấn đề Tầng 1 (không chặt giữa từ), nhưng lộ vấn đề mới: `SentenceSplitter` không hiểu khái niệm "Điều" — không biết đoạn nào thuộc Điều mấy.

---

## Tầng 3 — Thử cách đơn giản: cắt theo dòng trống

```python
text_nhieu_doan = """Điều 1. Nội dung điều một.

Điều 2. Nội dung điều hai."""

doan = text_nhieu_doan.split("\n\n")
```

Hoạt động với dữ liệu sạch, nhưng **không đáng tin** với corpus OCR thật — nhiều Điều không cách nhau bằng dòng trống rõ ràng do quá trình OCR xuất văn bản liền mạch. Cần cách bám vào chính chữ "Điều X", không phụ thuộc khoảng trắng.

---

## Tầng 4 — Regex: chỉ TÌM, chưa cắt

```python
import re

ket_qua = re.findall(r"Điều \d+", "Điều 1. Nội dung một. Điều 2. Nội dung hai.")
# Kết quả: ['Điều 1', 'Điều 2']
```

Tìm được vị trí "Điều X" xuất hiện, nhưng chưa có nội dung đi kèm phía sau.

---

## Tầng 5 — Regex cắt full đoạn, dùng string thuần

```python
pattern = re.compile(r"(Điều \d+\..*?)(?=Điều \d+\.|\Z)", re.DOTALL)

text = "Điều 1. Nội dung một. Điều 2. Nội dung hai. Điều 3. Nội dung ba."
cac_doan = pattern.findall(text)
```

**Kết quả:**

```python
['Điều 1. Nội dung một. ', 'Điều 2. Nội dung hai. ', 'Điều 3. Nội dung ba.']
```

### Thử nghiệm hiểu từng ký hiệu (quan trọng — tự tay gây lỗi để hiểu)

- **Thử greedy (`.*`) thay vì non-greedy (`.*?`):**

  ```python
  pattern_sai = re.compile(r"(Điều \d+\..*)(?=Điều \d+\.|\Z)", re.DOTALL)
  print(pattern_sai.findall(text))  # Kết quả: [] — RỖNG
  ```

  `.*` (greedy) nuốt tới tận cuối văn bản trước, lùi lại tìm lookahead nhưng vị trí đó đã bị nuốt mất. Ngược lại, `.*?` (non-greedy) khớp ít nhất có thể, dừng ngay khi gặp lookahead "Điều X." kế tiếp.

- **Thử bỏ `re.DOTALL`:**
  ```python
  pattern_sai2 = re.compile(r"(Điều \d+\..*?)(?=Điều \d+\.|\Z)")
  text_nhieu_dong = "Điều 1. Dòng một.\nDòng hai vẫn thuộc điều 1. Điều 2. Nội dung hai."
  print(pattern_sai2.findall(text_nhieu_dong))  # cắt sai — dấu . không khớp \n
  ```
  Không có `re.DOTALL`, dấu `.` không khớp ký tự xuống dòng `\n` — nội dung Điều trải dài qua nhiều dòng sẽ bị cắt sót.

---

## Tầng 6 — Ghép vào TextNode, CHƯA có metadata

```python
from llama_index.core import Document
from llama_index.core.schema import TextNode

def cat_don_gian(documents: list[Document]) -> list[TextNode]:
    nodes = []
    for doc in documents:
        cac_doan = pattern.findall(doc.text)
        for doan in cac_doan:
            nodes.append(TextNode(text=doan.strip()))
    return nodes
```

Tạo đúng Node, nhưng nếu retrieval trả về Node này, ta không biết nó là Điều mấy — đây là động lực để chuyển sang tầng tiếp theo.

---

## Tầng 7 — Thêm metadata["dieu"]

```python
def extract_dieu_number(text: str) -> str:
    match = re.match(r"Điều (\d+)", text.strip())
    return match.group(1) if match else "khong_ro"

def cat_co_metadata(documents: list[Document]) -> list[TextNode]:
    nodes = []
    for doc in documents:
        cac_doan = pattern.findall(doc.text)
        for doan in cac_doan:
            so_dieu = extract_dieu_number(doan)
            nodes.append(TextNode(text=doan.strip(), metadata={"dieu": so_dieu}))
    return nodes
```

> **Vì sao dùng `.match()` thay vì `.search()`?**  
> `match()` chỉ tìm ở đầu chuỗi — đúng ý vì `doan` đã bắt đầu bằng "Điều X" từ Tầng 5. `search()` có thể bắt nhầm nếu nội dung bên trong Điều nhắc tới một Điều khác (ví dụ: _"theo quy định tại Điều 2"_).

---

## Tầng 8 — Giữ metadata gốc của Document (nguồn, trang)

```python
def cat_giu_metadata_goc(documents: list[Document]) -> list[TextNode]:
    nodes = []
    for doc in documents:
        cac_doan = pattern.findall(doc.text)
        for doan in cac_doan:
            so_dieu = extract_dieu_number(doan)
            nodes.append(TextNode(
                text=doan.strip(),
                metadata={"dieu": so_dieu, **doc.metadata},
            ))
    return nodes
```

`**doc.metadata` giúp unpack dict, sao chép toàn bộ metadata gốc (nguồn, trang) sang Node, đồng thời bổ sung thêm trường `dieu`. Nếu thiếu bước này, ta sẽ mất khả năng trích dẫn nguồn ở các bước sau trong pipeline RAG.

---

## Tầng 9 — Xử lý ca biên: trang không có "Điều" nào

**Phát hiện bug trước khi sửa:**

```python
doc = Document(text="Trang bìa không có gì cả.")
nodes = cat_giu_metadata_goc([doc])
print(nodes)  # [] — MẤT DỮ LIỆU
```

**Sửa lại:**

```python
def cat_hoan_chinh(documents: list[Document]) -> list[TextNode]:
    nodes = []
    for doc in documents:
        cac_doan = pattern.findall(doc.text)
        if not cac_doan:
            nodes.append(TextNode(
                text=doc.text.strip(),
                metadata={"dieu": "khong_co_dieu", **doc.metadata},
            ))
            continue
        for doan in cac_doan:
            so_dieu = extract_dieu_number(doan)
            nodes.append(TextNode(text=doan.strip(), metadata={"dieu": so_dieu, **doc.metadata}))
    return nodes
```

---

## Tầng 10 — Xử lý Điều quá dài (sub-chunking có kiểm soát)

Nếu một Điều dài bất thường, vector embedding sẽ bị "loãng" — quay về đúng vấn đề Tầng 0 nhưng ở quy mô nhỏ hơn.

```python
sub_splitter = SentenceSplitter(chunk_size=100, chunk_overlap=20)

def cat_co_gioi_han_do_dai(documents: list[Document], max_tu: int = 100) -> list[TextNode]:
    nodes = []
    for doc in documents:
        cac_doan = pattern.findall(doc.text)
        if not cac_doan:
            nodes.append(TextNode(
                text=doc.text.strip(),
                metadata={"dieu": "khong_co_dieu", **doc.metadata},
            ))
            continue

        for doan in cac_doan:
            so_dieu = extract_dieu_number(doan)
            base_meta = {"dieu": so_dieu, **doc.metadata}
            so_tu = len(doan.split())

            if so_tu <= max_tu:
                nodes.append(TextNode(text=doan.strip(), metadata=base_meta))
            else:
                mang_con = sub_splitter.split_text(doan)
                for j, mieng in enumerate(mang_con):
                    nodes.append(TextNode(
                        text=mieng,
                        metadata={**base_meta, "phan": j + 1},
                    ))
    return nodes
```

> **Điểm mấu chốt:** Dù một Điều bị cắt thành nhiều mảnh con, mọi mảnh vẫn giữ `metadata["dieu"]` — retrieval trả về bất kỳ mảnh nào cũng biết chính xác nó thuộc Điều nào để trích dẫn nguồn.

**Kiểm chứng:**

```python
doan_dai = "Điều 9. " + "nội dung lặp lại nhiều lần để test. " * 30
nodes = cat_co_gioi_han_do_dai([Document(text=doan_dai)], max_tu=20)
print(set(n.metadata["dieu"] for n in nodes))  # {'9'} — dù sinh ra nhiều Node con
```

---

## Tầng 11 — Chấp nhận nhiều biến thể dấu câu

Dữ liệu thực tế có thể gặp cả `Điều 5.` (dấu chấm) và `Điều 15:` (dấu hai chấm), hoặc khoảng trắng kép (`Điều  15.`):

```python
pattern = re.compile(r"(Điều\s+\d+[.:].*?)(?=Điều\s+\d+[.:]|\Z)", re.DOTALL)
```

**So sánh trước / sau:**

```python
text_hai_kieu = "Điều 1. Kiểu chấm. Điều 2: Kiểu hai chấm."

pattern_cu = re.compile(r"(Điều \d+\..*?)(?=Điều \d+\.|\Z)", re.DOTALL)
print(pattern_cu.findall(text_hai_kieu))  # Chỉ bắt Điều 1, bỏ sót Điều 2

pattern_moi = re.compile(r"(Điều\s+\d+[.:].*?)(?=Điều\s+\d+[.:]|\Z)", re.DOTALL)
print(pattern_moi.findall(text_hai_kieu))  # Bắt trọn cả 2
```

`\s+` (thay vì space cứng) giúp chống được lỗi OCR tạo khoảng trắng thừa ("Điều 15.").

---

## Tầng 12 — Đo chất lượng bằng số, không đoán bằng mắt

Với văn bản lớn (nhiều Điều), không thể đọc kiểm tra từng Node bằng mắt — cần thước đo định lượng:

```python
from typing import Any

def validate_nodes(nodes: list[TextNode]) -> dict[str, Any]:
    total = len(nodes)
    khong_ro = sum(1 for n in nodes if n.metadata.get("dieu") in ("khong_ro", "khong_co_dieu"))
    do_dai_tb = sum(len(n.text) for n in nodes) // max(total, 1)
    return {
        "tong_so_node": total,
        "node_khong_ro_dieu": khong_ro,
        "ty_le_khong_ro": f"{khong_ro / max(total, 1):.1%}",
        "do_dai_trung_binh_ky_tu": do_dai_tb,
    }
```

Bước này biến việc đánh giá chunking từ cảm tính thành số liệu đo lường cụ thể.

---

## Tầng 13 — So sánh với phương pháp baseline

```python
def cat_fixed_size_baseline(documents: list[Document]) -> list[TextNode]:
    """Baseline để so sánh — cắt cố định, không hiểu cấu trúc Điều."""
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    return splitter.get_nodes_from_documents(documents)

nodes_theo_dieu = cat_hoan_chinh(documents)
nodes_baseline = cat_fixed_size_baseline(documents)

print("Theo Điều:", validate_nodes(nodes_theo_dieu))
print("Baseline:", validate_nodes(nodes_baseline))
```

Số lượng và độ dài Node là chỉ báo sơ bộ — hiệu quả thực sự sẽ được kiểm chứng khi kết nối với Retriever và đo Recall@k.

---

## Bảng tổng kết lộ trình

|  Tầng  | Thêm gì                    | Vấn đề nó giải quyết                                     |
| :----: | :------------------------- | :------------------------------------------------------- |
| **0**  | Đặt vấn đề (chưa code)     | Hiểu lý do cần cắt trước khi viết giải pháp              |
| **1**  | Cắt cứng theo ký tự        | Thấy lỗi cắt đôi từ ngữ                                  |
| **2**  | `SentenceSplitter`         | Không chặt giữa từ, nhưng thiếu định danh Điều           |
| **3**  | Cắt theo dòng trống `\n\n` | Không đáng tin cậy với dữ liệu OCR thực tế               |
| **4**  | `re.findall` tìm "Điều X"  | Tách bước tìm kiếm khỏi bước cắt đoạn                    |
| **5**  | Regex cắt full đoạn        | Hiểu non-greedy `.*?` và cờ `re.DOTALL`                  |
| **6**  | Ghép vào `TextNode`        | Thấy rõ việc thiếu metadata sẽ gây khó khăn khi truy hồi |
| **7**  | `metadata["dieu"]`         | Định danh Node chính xác theo số Điều                    |
| **8**  | Giữ `doc.metadata` gốc     | Không làm mất thông tin nguồn và số trang                |
| **9**  | Xử lý trang không có Điều  | Xử lý trường hợp trang bìa, tránh mất dữ liệu            |
| **10** | Sub-chunking Điều dài      | Tránh vector embedding bị loãng ở quy mô nhỏ             |
| **11** | Nhiều biến thể dấu câu     | Chống lỗi OCR, định dạng không đồng nhất                 |
| **12** | `validate_nodes()`         | Định lượng hóa chất lượng chunking bằng con số           |
| **13** | So sánh baseline           | Chứng minh lựa chọn bằng số liệu thực nghiệm             |

---

## Bản hoàn chỉnh — `src/node_parser.py`

```python
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
            preview = node.text[:120].replace("\n", " ")
            print(f"Nội dung: {preview}...")
    else:
        print("Không tìm thấy file mẫu để test.")
```

---

## Bước kiểm chứng cuối cùng

Sau khi triển khai đầy đủ các tầng, chạy thử trực tiếp file [src/node_parser.py](file:///home/phanhuukha/Dev/major%20project/LlamaIndex_RAG/src/node_parser.py):

```bash
python3 src/node_parser.py
```

Kỳ vọng: Toàn bộ kịch bản kiểm thử đều **PASS**.
