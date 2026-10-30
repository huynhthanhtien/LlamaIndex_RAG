# LlamaIndex: Chunking, đánh giá truy hồi và tách truy hồi khỏi sinh câu trả lời

Nhóm 08 — Hệ thống hỏi đáp quy chế đào tạo Trường Đại học Sài Gòn (SGU)

Nếu đã dựng thử một hệ thống RAG, bạn sẽ thấy câu trả lời đúng hay sai phụ thuộc trước hết vào **bước truy hồi**: LLM
chỉ đọc những trích đoạn mà retriever đưa cho nó. Đoạn đúng không được truy hồi thì LLM giỏi đến đâu cũng không trả
lời đúng; đoạn sai được truy hồi thì LLM sẽ trả lời sai một cách rất tự tin. Vì vậy trước khi đổi LLM hay sửa prompt,
cần đo được retriever đang làm tốt đến đâu.

Trong lab này bạn sẽ dựng một retriever bằng LlamaIndex trên văn bản thật — **Quy chế đào tạo trình độ đại học SGU 2021**
(21 Điều) — và đo nó bằng **Recall@k** và **MRR** trên một bộ câu hỏi có nhãn Điều. Bạn sẽ thấy kích thước chunk và cách
chia văn bản thay đổi kết quả ra sao, và vì sao giới hạn **256 token** của model embedding lại quan trọng.

Ngoài ra, bạn sẽ nạp thêm **QĐ 3183/2025** (văn bản sửa đổi Quy chế 2021) để gặp một lỗi rất hay xảy ra với văn bản pháp
quy: **nhầm phiên bản** — câu hỏi của khóa cũ được trả lời bằng quy định mới. Cuối cùng, bạn sẽ tách hệ thống thành ba
bước truy hồi → kiểm căn cứ → sinh câu trả lời, để từ chối câu hỏi ngoài phạm vi mà không cần gọi LLM, và biết lỗi nằm ở
truy hồi hay ở LLM.

> **Lưu ý**
>
> Toàn bộ mã nguồn của lab nằm trong thư mục `lab/` của repo. File `lab/bai_lam.py` là điểm bắt đầu (**Begin**): các hàm
> bạn sẽ viết đang để trống. File `lab/dap_an.py` là kết quả cuối (**End**). Thêm tùy chọn `--dap-an` vào bất kỳ lệnh nào
> để chạy bằng lời giải khi cần đối chiếu.

### Mục tiêu

Trong Hands-On Lab này, bạn sẽ học cách:

- Chia văn bản thành Node bằng `SentenceSplitter` và bằng cấu trúc Điều, gắn metadata để trích nguồn.
- Dựng `VectorStoreIndex`, truy hồi top-k và đo Recall@k, MRR theo một luật chấm rõ ràng.
- Chọn chunk size và top-k dựa trên số đo, có tính tới giới hạn token của model embedding.
- Sửa lỗi nhầm phiên bản văn bản bằng metadata hiệu lực.
- Tách truy hồi khỏi sinh câu trả lời và từ chối câu hỏi ngoài phạm vi.

### Điều kiện tiên quyết

Bạn cần có các thành phần sau để hoàn thành lab:

- Python 3.10 trở lên và repo của nhóm đã clone về máy (xem **Phụ lục A**).
- Khoảng 1 GB dung lượng trống cho thư viện và model embedding `bkai-foundation-models/vietnamese-bi-encoder`. Model
  chạy trên **CPU**, không cần GPU.
- (Tùy chọn, chỉ cho Bài tập 4 – Nhiệm vụ 3) Ollama với model `qwen3:4b` (mặc định của lab; kết quả của nhóm dùng
  `qwen3:8b`), chạy trên máy của bạn hoặc trên Colab (xem **Phụ lục B**).

### Cài đặt

**Cài thư viện và tải model**

Làm theo **Phụ lục A** để tạo môi trường ảo, cài thư viện và tải trước model embedding. Mọi lệnh trong lab chạy **từ thư
mục gốc của repo**, với môi trường ảo đã kích hoạt.

**Sử dụng các đoạn code**

Các đoạn code bạn cần chép vào `lab/bai_lam.py` được ghi nhãn *(Đoạn code – tên đoạn)*. Các khối ghi kết quả là đầu ra
thật khi nhóm chạy lab (điều kiện đo ở **Phụ lục E**); số của bạn phải khớp nếu dùng cùng model.

---

## Các bài tập

Các bài tập sau tạo thành Hands-On Lab này:

1. Dựng index và đo truy hồi với cách chia mặc định
2. Chia văn bản theo cấu trúc Điều
3. Thêm văn bản sửa đổi và xử lý nhầm phiên bản
4. Tách truy hồi khỏi sinh câu trả lời

> **Lưu ý**
>
> Mỗi bài tập đi kèm lời giải trong `lab/dap_an.py`. Bạn có thể dùng lời giải để đối chiếu nếu cần trợ giúp khi làm bài.

Thời gian ước tính để hoàn thành lab: **45 phút**

### Bài tập 1: Dựng index và đo truy hồi với cách chia mặc định

Cách chia mặc định của LlamaIndex là `SentenceSplitter`: cắt văn bản thành các đoạn có số token gần bằng `chunk_size`
và cố giữ nguyên câu. Nó không biết văn bản có các Điều.

Trong bài tập này, bạn sẽ xem các Node được tạo, dựng index, đo Recall@k và MRR, rồi đổi chunk size và top-k để thấy
ảnh hưởng của từng tham số.

#### Nhiệm vụ 1 – Xem các Node do SentenceSplitter tạo

1. Mở file **lab/chung.py** và tìm hàm **chia_co_dinh**. Chú ý rằng metadata `cac_dieu` được gắn **sau khi cắt**, theo vị
   trí ký tự của đoạn trong văn bản (`start_char_idx`, `end_char_idx`): một đoạn vắt qua hai Điều được ghi cả hai.

    ```python
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    for n in splitter.get_nodes_from_documents([Document(text=text)]):
        nodes.append(gan_metadata(n, van_ban, dieu_trong_khoang(text, n.start_char_idx, n.end_char_idx)))
    ```

2. Mở file **lab/cau_hoi.json**. Bộ câu hỏi có 14 câu, chia theo trường `loai`:

    | loai | Số câu | Ví dụ | Nhãn đúng |
    |---|---|---|---|
    | `trong` | 10 | Vắng thi không có lý do chính đáng thì bị điểm bao nhiêu? | Quy chế 2021, Điều 9 |
    | `phien_ban` | 2 | Sinh viên **khóa 2025** / **khóa 2022** có điểm học phần 8,0 thì được xếp loại điểm chữ gì? | QĐ 3183 Điều 9 (B+) / Quy chế 2021 Điều 9 (B) |
    | `ngoai` | 2 | Học phí mỗi tín chỉ năm học 2025-2026 là bao nhiêu? | Không có: phải từ chối |

3. Trong terminal, chạy lệnh sau để chia Quy chế 2021 với `chunk_size=256`:

    ```bash
    python lab/lab_rag.py chia --chia co-dinh --chunk 256
    ```

    ```
      1. [qc2021 | Điều 1 | 88 token] # QUY CHẾ ĐÀO TẠO TRÌNH ĐỘ ĐẠI HỌC (Ban hành kèm theo Quyết định số ÔŠ /QĐ-ĐHSG, ngày ÔÔ t…
      2. [qc2021 | Điều 1 | 107 token] Văn bản này cụ thể hóa Ouy chế đào tạo trình độ đại học ban hành kèm theo Thông tư số 08/2…
      3. [qc2021 | Điều 1;2 | 130 token] 2. Quy chế này áp dụng đối với người học và giảng viên các chương trình đào tạo trình độ đ…
    ...
    78 Node | token TB 111, lớn nhất 154 | 0 Node dài hơn 256 token mà model embedding đọc được
    ```

    *Các Node do SentenceSplitter tạo với chunk_size=256*

    Mỗi dòng ghi văn bản, các Điều mà Node chứa, số token và đầu nội dung. Chú ý Node 3 vắt qua Điều 1 và Điều 2. Bạn cũng sẽ thấy lỗi OCR trong văn bản ("Ouy chế", "ÔŠ"): đây là dữ liệu thật.

4. Chạy lại với `--chunk 1024`:

    ```bash
    python lab/lab_rag.py chia --chunk 1024 | tail -1
    ```

    ```
    17 Node | token TB 495, lớn nhất 582 | 17 Node dài hơn 256 token mà model embedding đọc được
    ```

    *Chunk 1024: mọi Node đều dài hơn giới hạn của model embedding*

    Chú ý: đặt `chunk_size=256` thì Node chỉ dài trung bình 111 token. Lý do là `SentenceSplitter` đếm token bằng
    **tiktoken** (tokenizer của OpenAI), còn số in ra được đếm bằng tokenizer **PhoBERT** của model embedding. Tiếng Việt
    có dấu bị tiktoken tách nhỏ hơn. Model embedding chỉ đọc **256 token PhoBERT** đầu tiên của mỗi Node; phần sau bị bỏ
    khi tính vector.

#### Nhiệm vụ 2 – Dựng index và đo Recall@k

Ở nhiệm vụ này, bạn sẽ dựng `VectorStoreIndex`, truy hồi top-k cho từng câu hỏi và đo kết quả.

Một Node trong top-k được tính là **đúng** khi cùng văn bản với nhãn và chứa Điều của nhãn (hàm `la_dung` trong
`lab/chung.py`). Với mỗi câu, lab ghi **hạng** của Node đúng đầu tiên. **R@k** là tỉ lệ câu có Node đúng trong k kết quả
đầu; **MRR** là trung bình của 1/hạng (không có Node đúng thì tính 0). Câu ngoài phạm vi không có Node đúng nên không
tính vào R@k.

1. Mở file **lab/lab_rag.py**, tìm hàm **tim**. Đây là toàn bộ bước truy hồi:

    ```python
    nodes = index.as_retriever(similarity_top_k=top_k).retrieve(cau_hoi)
    ```

2. Chạy lệnh đo:

    ```bash
    python lab/lab_rag.py do --chia co-dinh --chunk 256 --top-k 1,3,5
    ```

    ```
    id   loại      hạng    điểm  top-1
    Q01  trong        1   0.529  Quy chế đào tạo SGU 2021 – Điều 2
    Q02  trong        1   0.524  Quy chế đào tạo SGU 2021 – Điều 4
    ...
    Q07  trong        1   0.297  Quy chế đào tạo SGU 2021 – Điều 12, 13
    ...
    V01  phien_ban    —   0.338  Quy chế đào tạo SGU 2021 – Điều 9
    V02  phien_ban    1   0.382  Quy chế đào tạo SGU 2021 – Điều 9
    O01  ngoai        —   0.266  Quy chế đào tạo SGU 2021 – Điều 10, 11
    O02  ngoai        —   0.214  Quy chế đào tạo SGU 2021 – Điều 1

    Cấu hình: chia=co-dinh chunk=256 them_3183=False phien_ban=False
    78 Node | token TB 111 | 0 Node > 256 token (bị cắt khi embed) | dựng index 7.2s
      10 câu trong phạm vi   R@1=10/10  R@3=10/10  R@5=10/10  MRR=1.000
      2 câu phiên bản        R@1=1/2  R@3=1/2  R@5=1/2  MRR=0.500
      Điểm top-1: câu có đáp án thấp nhất 0.297 | câu ngoài miền cao nhất 0.266
    ```

    *Kết quả đo với cách chia mặc định*

3. Đọc kết quả:

    1. 10/10 câu trong phạm vi có Node đúng ở hạng 1.
    2. **V01 trượt** (`—`): câu khóa 2025 cần bảng điểm của QĐ 3183, nhưng index chưa có văn bản này. Không cách chia
       hay top-k nào sửa được lỗi **thiếu văn bản**. Bạn sẽ xử lý ở Bài tập 3.
    3. Q07 được tính đúng nhờ một Node chứa cả Điều 12 và Điều 13, nên nguồn trích sẽ là "Điều 12, 13" thay vì đúng Điều
       12. Bạn sẽ xử lý ở Bài tập 2.
    4. Luật chấm theo Điều có một điểm mù: Node được tính đúng nếu **thuộc** Điều của nhãn, kể cả khi đoạn đó không chứa
       câu trả lời. Bài tập 4 – Nhiệm vụ 3 cho thấy Q03 "đúng ở hạng 1" nhưng đoạn đó dừng ngay trước khoản chứa đáp án.
    5. Dòng cuối ghi điểm top-1 thấp nhất của câu có đáp án và cao nhất của câu ngoài phạm vi. Bạn sẽ dùng hai số này ở
       Bài tập 4.

#### Nhiệm vụ 3 – Đổi chunk size

1. Chạy lại lệnh đo của Nhiệm vụ 2 với `--chunk` lần lượt là **64**, **128**, **512** và **1024**, mỗi lần khoảng 15 giây:

    ```bash
    for c in 64 128 512 1024; do python lab/lab_rag.py do --chunk $c --top-k 1,3,5 | tail -4; done
    ```

2. Ghi kết quả vào bảng. Kết quả của nhóm:

    | chunk_size | Số Node | Token TB | Node > 256 token | R@1 | R@3 | Điểm top-1 thấp nhất (có đáp án) / cao nhất (ngoài phạm vi) |
    |---|---|---|---|---|---|---|
    | 64 | 347 | 31 | 0 | 9/10 | 10/10 | 0,393 / **0,441** |
    | 128 | 161 | 56 | 0 | 10/10 | 10/10 | 0,340 / **0,352** |
    | 256 | 78 | 111 | 0 | 10/10 | 10/10 | 0,297 / 0,266 |
    | 512 | 36 | 237 | 12 | 10/10 | 10/10 | 0,286 / 0,242 |
    | 1024 | 17 | 495 | **17** | **8/10** | 9/10 | 0,251 / 0,189 |

    *Ảnh hưởng của chunk size (10 câu trong phạm vi, top-k = 5)*

3. Chú ý hai đầu của bảng:

    1. **Chunk quá nhỏ (64):** mỗi Node chỉ còn vài câu, mất ngữ cảnh. Q07 bị một Node của Điều 18 có cùng từ khóa chen
       lên hạng 1. Câu ngoài phạm vi còn có điểm (0,441) **cao hơn** câu có đáp án (0,393), vì Node ngắn dễ khớp vu vơ.
    2. **Chunk quá lớn (1024):** cả 17 Node dài hơn 256 token, model embedding bỏ phần đuôi, nơi có thể chứa đáp án. Q03
       tụt xuống hạng 3, Q07 rơi khỏi top-5.
    3. **256 và 512** đều 10/10. Với 10 câu, chênh một câu đã là 10 điểm phần trăm, nên bảng này **không đủ** để kết
       luận 256 tốt hơn 512; nó chỉ cho thấy xu hướng ở hai đầu.

#### Nhiệm vụ 4 – Đổi top-k

1. Ở chunk 256, R@1 đã là 10/10 nên top-k không đổi gì. Chạy cấu hình chunk 64, nơi có câu không đứng hạng 1:

    ```bash
    python lab/lab_rag.py do --chunk 64 --top-k 1,3,5,10 | tail -4
    ```

    ```
      10 câu trong phạm vi   R@1=9/10  R@3=10/10  R@5=10/10  R@10=10/10  MRR=0.950
    ```

2. Chú ý: tăng top-k **sửa được** lỗi xếp hạng (Node đúng có trong danh sách nhưng không đứng đầu), nhưng **không sửa
   được** lỗi thiếu văn bản (V01 vẫn trượt). Đổi lại, số token đưa vào LLM tăng theo k: với chunk 256 (111 token mỗi
   Node), top-3 là khoảng 330 token, top-10 là khoảng 1 100 token. Nhiều đoạn không liên quan hơn thì LLM cũng dễ lấy
   nhầm đoạn hơn.

#### Nhiệm vụ 5 – Lưu và nạp lại index (tùy chọn)

Mỗi lần chạy, lab embed lại toàn bộ Node. Với corpus lớn, việc này tốn nhiều thời gian; LlamaIndex cho phép lưu index ra
đĩa rồi nạp lại.

1. Mở file **lab/lab_rag.py**, tìm hàm **dung_index**. Chú ý hai lời gọi `index.storage_context.persist(...)` và
   `load_index_from_storage(...)`, và tên thư mục lưu gồm cả **tên model** lẫn **cách chia**.
2. Chạy hai lần liên tiếp với `--luu`:

    ```bash
    python lab/lab_rag.py do --luu --top-k 1 | grep "dựng index"
    python lab/lab_rag.py do --luu --top-k 1 | grep "dựng index"
    ```

    ```
    78 Node | token TB 111 | 0 Node > 256 token (bị cắt khi embed) | dựng index 5.8s
    78 Node | token TB 111 | 0 Node > 256 token (bị cắt khi embed) | dựng index 0.3s
    ```

    *Lần thứ hai nạp index từ lab/storage thay vì embed lại*

    Nếu thư mục lưu không có tên model, đổi model embedding mà vẫn nạp index cũ sẽ gây lỗi lệch số chiều vector (xem
    **Phụ lục C**).

### Bài tập 2: Chia văn bản theo cấu trúc Điều

Văn bản quy chế có cấu trúc sẵn: mỗi Điều là một đơn vị nghĩa và là đơn vị người dùng trích dẫn ("theo Điều 9 Quy chế
2021"). Chia theo Điều giúp mỗi Node mang đúng một số Điều, nên nhãn nguồn trong metadata chính xác tới từng Điều.

Trong bài tập này, bạn sẽ viết hàm chia theo Điều, so sánh với cách chia mặc định, rồi xử lý các Điều quá dài.

#### Nhiệm vụ 1 – Viết hàm chia_theo_dieu

1. Mở file **lab/bai_lam.py**. Thêm các dòng import sau vào đầu file, ngay dưới dòng `from llama_index.core.schema import ...`:

    (Đoạn code – *Lab RAG – Bài 2 import*)

    ```python
    import re

    from llama_index.core.node_parser import SentenceSplitter

    HEADING = re.compile(r"(?m)^(?=#{1,4} )")
    ```

    `HEADING` tách văn bản ngay **trước** mỗi dòng heading Markdown (`#` đến `####`), nên dòng heading vẫn nằm ở đầu mỗi
    khối.

2. Thay thân hàm **chia_theo_dieu** (dòng `raise NotImplementedError(...)`) bằng đoạn code sau:

    (Đoạn code – *Lab RAG – Bài 2 chia_theo_dieu*)

    ```python
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
    ```

    `DIEU` (trong `lab/chung.py`) khớp heading `### Điều N` của văn bản và `#### ... Điều N` của mục sửa đổi; `m[1]` là
    số Điều. `gan_metadata` gắn metadata giống hệt cách chia mặc định, nên luật chấm không đổi.

3. Lưu file và kiểm tra:

    ```bash
    python lab/lab_rag.py chia --chia dieu
    ```

    ```
      1. [qc2021 | Điều 1 | 165 token] Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng 1. Văn bản này cụ thể hóa Ouy chế đào tạo …
      2. [qc2021 | Điều 2 | 649 token > 256 BỊ CẮT] Điều 2. Chương trình đào tạo và thời gian học tập 1. Chương trình đào tạo được xây dựng th…
      3. [qc2021 | Điều 3 | 201 token] Điều 3. Phương thức tổ chức đào tạo l, Nhà trường tổ chức đào tạo theo tín chỉ đối với chư…
    ...
     21. [qc2021 | Điều 21 | 467 token > 256 BỊ CẮT] Điều 21. Chế độ báo cáo, lưu trữ, công khai thông tin 1. Trước ngày 31 tháng 12 hàng năm: …

    21 Node | token TB 393, lớn nhất 823 | 14 Node dài hơn 256 token mà model embedding đọc được
    ```

    *Chia theo Điều: 21 Node, mỗi Node một Điều*

    Kiểm tra có đúng **21 Node** và mỗi Node mang **một** số Điều. Thiếu hoặc thừa Node thường do regex bắt nhầm heading
    vì lỗi OCR (xem **Phụ lục C**).

#### Nhiệm vụ 2 – So sánh với cách chia mặc định

1. Chạy lệnh đo:

    ```bash
    python lab/lab_rag.py do --chia dieu --top-k 1,3,5
    ```

    ```
    Q01  trong        4   0.261  Quy chế đào tạo SGU 2021 – Điều 19
    ...
    Q06  trong        2   0.560  Quy chế đào tạo SGU 2021 – Điều 10
    ...
      10 câu trong phạm vi   R@1=8/10  R@3=9/10  R@5=10/10  MRR=0.875
    ```

    *Chia theo Điều, không cắt tiếp*

2. Chú ý R@1 **giảm** từ 10/10 xuống 8/10. Lý do là 14/21 Điều dài hơn 256 token (Điều 8, 9, 10 dài khoảng 600 token),
   model chỉ đọc phần đầu mỗi Điều. Q01 hỏi thời gian tối đa của khóa học, nằm ở khoản 5, cuối Điều 2 (649 token).

#### Nhiệm vụ 3 – Cắt tiếp các Điều dài

1. Chạy lại với `--chunk 256`. Với cách chia theo Điều, tham số này cắt tiếp những Điều dài hơn 256 token tiktoken; mọi
   đoạn giữ metadata của Điều gốc:

    ```bash
    python lab/lab_rag.py do --chia dieu --chunk 256 --top-k 1,3,5
    ```

    ```
    86 Node | token TB 98 | 0 Node > 256 token (bị cắt khi embed) | dựng index 6.3s
      10 câu trong phạm vi   R@1=9/10  R@3=10/10  R@5=10/10  MRR=0.950
    ```

2. Tổng hợp ba cách chia:

    | Cách chia | Số Node | Node > 256 token | R@1 | R@3 | Nguồn trích |
    |---|---|---|---|---|---|
    | Cố định 256 | 78 | 0 | 10/10 | 10/10 | Có thể nhiều Điều ("Điều 12, 13") |
    | Theo Điều, không cắt | 21 | 14 | 8/10 | 9/10 | Đúng một Điều |
    | Theo Điều + cắt Điều dài ở 256 | 86 | 0 | 9/10 | 10/10 | Đúng một Điều |

3. Chú ý: trên bộ câu này, chia theo Điều **không** cho R@1 cao hơn chia cố định. Một phần vì luật chấm của chia cố định
   dễ dãi hơn: Node vắt qua hai Điều được tính đúng cho cả hai. Lợi ích thật của chia theo Điều là **nhãn nguồn chính
   xác** tới từng Điều trong metadata, để hệ thống in đúng "Điều 12" thay vì "Điều 12, 13" và người dùng mở đúng Điều
   đối chiếu. Hệ thống chính của nhóm chọn chia theo Điều vì lý do này, và dùng model embedding đọc được 8 192 token
   (`AITeamVN/Vietnamese_Embedding`) nên không gặp vấn đề cắt đuôi.

    > **Lưu ý**
    >
    > Nhãn nguồn chính xác trong metadata **không** có nghĩa là LLM tự ghi đúng số Điều trong câu trả lời. Bài tập 4 –
    > Nhiệm vụ 3 cho thấy LLM vẫn ghi sai Điều ở cả hai cách chia. Vì vậy nguồn hiển thị cho người dùng nên lấy từ
    > metadata của Node, không lấy từ câu chữ của LLM.

### Bài tập 3: Thêm văn bản sửa đổi và xử lý nhầm phiên bản

QĐ 3183/2025 sửa đổi Điều 6, 7, 9, 10 của Quy chế 2021. Theo Điều 2 của QĐ này, phần sửa Điều 9 và 10 (thêm điểm chữ B+,
C+, D+) **chỉ áp dụng cho khóa tuyển sinh từ 2025**. Cùng câu hỏi "điểm 8,0 được điểm chữ gì?", khóa 2025 được **B+**,
khóa 2022 vẫn là **B**.

Trong bài tập này, bạn sẽ nạp văn bản sửa đổi, quan sát lỗi nhầm phiên bản, rồi viết hàm sắp xếp lại kết quả theo hiệu
lực.

#### Nhiệm vụ 1 – Nạp văn bản sửa đổi

1. Chạy lệnh đo có thêm `--them-3183`:

    ```bash
    python lab/lab_rag.py do --chunk 256 --them-3183 --top-k 1,3,5
    ```

    ```
    V01  phien_ban    1   0.394  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 9
    V02  phien_ban    3   0.437  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 9
    ...
    87 Node | token TB 111 | 0 Node > 256 token (bị cắt khi embed) | dựng index 6.7s
      10 câu trong phạm vi   R@1=10/10  R@3=10/10  R@5=10/10  MRR=1.000
      2 câu phiên bản        R@1=1/2  R@3=2/2  R@5=2/2  MRR=0.667
    ```

    *Sau khi nạp QĐ 3183: V01 đúng, V02 sai*

2. Chú ý V01 (khóa 2025) **đã đúng**, nhưng V02 (khóa 2022) **tụt từ hạng 1 xuống hạng 3**: thêm văn bản mới đã làm hỏng
   một câu trước đó đúng.

3. Xem tận mắt ba Node mà LLM sẽ đọc cho câu V02:

    ```bash
    python lab/lab_rag.py hoi "Sinh viên khóa 2022 có điểm học phần 8,0 thì được xếp loại điểm chữ gì?" --them-3183
    ```

    ```
    [1] 0.437  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 9
        #### 3. Sửa đổi, bồ sung điểm a khoản 3 Điều 9: | “a) Loại đạt có phân mức, ... A: từ 8,5 đến 10.0; B+: từ 7,8 đến 8,4; ...
    [2] 0.386  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 10, 2, 3
        Để tính điểm trung bình, điểm chữ của học phần phải được quy đổi về điểm số như dưới đây: A quy đồi thành 4,0; B+ ...
    [3] 0.382  Quy chế đào tạo SGU 2021 – Điều 9
        | a) Loại đạt có phân mức, ... A: từ 8,5 đến 10,0; B: từ 7,0 đến 8,4; C: từ 5,5 đến 6,9; ...
    ```

    *Bảng điểm mới (khóa 2025) đứng trên bảng điểm gốc trong câu hỏi khóa 2022*

    Embedding chỉ đo **độ giống nội dung**. Hai bảng điểm gần như giống nhau, nên nó không biết bảng nào áp dụng cho
    khóa nào. LLM đọc trích đoạn đầu tiên sẽ trả lời B+, trong khi đúng phải là B.

#### Nhiệm vụ 2 – Viết hàm sap_xep_theo_phien_ban

1. Mở file **data/processed/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc/QD 3183.2025 - Sua doi Quy che Dao tao trinh do
   DH_LienQuanRutMonHoc.md** và đọc **Điều 2** ở cuối file:

    > Quyết định này có hiệu lực kể từ ngày ký. Khoản 3, 4, 5 Điều 1 áp dụng đối với các khóa tuyển sinh từ năm 2025 trở đi.

    Đối chiếu với các heading `####` của Điều 1: khoản 1, 2 sửa Điều 6, 7 (áp dụng ngay cho mọi khóa); khoản 3, 4, 5 sửa
    Điều 9, 9, 10 (chỉ từ khóa 2025).

2. Mở file **lab/bai_lam.py**. Thêm bảng hiệu lực ngay dưới `HEADING` (đã thêm ở Bài tập 2):

    (Đoạn code – *Lab RAG – Bài 3 bảng hiệu lực*)

    ```python
    # Điều bị QĐ 3183 sửa -> khóa bắt đầu áp dụng (None = áp dụng cho mọi khóa)
    SUA_DOI_3183: dict[str, int | None] = {"6": None, "7": None, "9": 2025, "10": 2025}


    def ap_dung(n: NodeWithScore, khoa: int) -> bool | None:
        """Node là mục sửa đổi của QĐ 3183: True/False = áp dụng/không áp dụng cho khóa; None = không phải mục sửa đổi."""
        if n.node.metadata.get("van_ban") != "qd3183":
            return None
        tu = [SUA_DOI_3183[d] for d in cac_dieu(n) if d in SUA_DOI_3183]
        return any(t is None or khoa >= t for t in tu) if tu else None
    ```

3. Thay thân hàm **sap_xep_theo_phien_ban** bằng đoạn code sau:

    (Đoạn code – *Lab RAG – Bài 3 sap_xep_theo_phien_ban*)

    ```python
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
    ```

    Hàm **không xóa** Node nào, chỉ đổi thứ tự: Điều gốc vẫn là căn cứ cho khóa cũ. `khoa_trong_cau_hoi` (trong
    `lab/chung.py`) đọc "khóa 2025" từ câu hỏi bằng regex.

#### Nhiệm vụ 3 – Kiểm tra

1. Chạy lại lệnh đo có thêm `--phien-ban`:

    ```bash
    python lab/lab_rag.py do --chunk 256 --them-3183 --phien-ban --top-k 1,3,5
    ```

    ```
    V01  phien_ban    1   0.394  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 9
    V02  phien_ban    1   0.437  Quy chế đào tạo SGU 2021 – Điều 9
    ...
      10 câu trong phạm vi   R@1=10/10  R@3=10/10  R@5=10/10  MRR=1.000
      2 câu phiên bản        R@1=2/2  R@3=2/2  R@5=2/2  MRR=1.000
    ```

    *Sau khi sắp xếp theo hiệu lực: cả hai câu phiên bản đúng ở hạng 1*

2. Chạy lại lệnh `hoi` của Nhiệm vụ 1 với `--phien-ban`. Chú ý bảng điểm gốc của Quy chế 2021 giờ đứng đầu, hai mục sửa
   đổi chỉ áp dụng từ khóa 2025 xuống cuối:

    ```
    [1] 0.382  Quy chế đào tạo SGU 2021 – Điều 9
    [2] 0.437  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 9
    [3] 0.386  QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 – Điều 10, 2, 3
    ```

3. Tổng hợp:

    | Cấu hình (cố định 256) | V01 (khóa 2025) | V02 (khóa 2022) | 10 câu trong phạm vi R@1 |
    |---|---|---|---|
    | Chỉ Quy chế 2021 | — (thiếu văn bản) | 1 | 10/10 |
    | + QĐ 3183 | 1 | **3** (nhầm phiên bản) | 10/10 |
    | + QĐ 3183 + sắp xếp theo hiệu lực | 1 | **1** | 10/10 |

    > **Lưu ý**
    >
    > Bảng `SUA_DOI_3183` viết tay ở đây để học. Hệ thống chính của nhóm ghi thông tin hiệu lực vào **front matter** của
    > từng văn bản (`sua_doi`, `ap_dung_khoa_tu_theo_dieu`) và đọc tự động trong `src/phien_ban.py`. Hàm chỉ sắp lại những
    > Node **đã truy hồi**: với cách chia theo Điều + cắt 256, V02 vẫn ở hạng 2 vì Node đứng đầu là Điều 10. Đó là lỗi
    > truy hồi, không phải lỗi phiên bản, nên hàm này không sửa.

### Bài tập 4: Tách truy hồi khỏi sinh câu trả lời

Lệnh `tra-loi` chạy ba bước tách rời và in kết quả của từng bước:

1. **Truy hồi**: lấy top-k Node (giống lệnh `do`).
2. **Kiểm căn cứ**: gọi `co_can_cu(nodes, nguong)`. Không đạt thì **từ chối ngay, không gọi LLM**.
3. **Sinh câu trả lời**: `get_response_synthesizer(...).synthesize(câu_hỏi, nodes=nodes)`. LLM chỉ đọc đúng các Node của
   bước 1, không tự truy hồi thêm.

Tách như vậy để biết lỗi nằm ở đâu: bước 1 không có Node đúng là **lỗi truy hồi**; bước 1 có Node đúng mà bước 3 vẫn sai là
**lỗi sinh** (LLM đọc sai bảng, trộn hai phiên bản, bịa thêm).

Trong bài tập này, bạn sẽ chọn ngưỡng từ chối, viết hàm kiểm căn cứ, rồi (tùy chọn) chạy cả ba bước với Ollama.

#### Nhiệm vụ 1 – Chọn ngưỡng và viết hàm co_can_cu

1. Xem lại dòng cuối của lệnh đo ở chunk 256 (Bài tập 1, Nhiệm vụ 2):

    ```
    Điểm top-1: câu có đáp án thấp nhất 0.297 | câu ngoài miền cao nhất 0.266
    ```

    Ngưỡng cần nằm giữa hai số này để mọi câu có đáp án vẫn được trả lời và hai câu ngoài phạm vi bị từ chối. Lab dùng
    **0,28**.

2. Mở file **lab/bai_lam.py** và thay thân hàm **co_can_cu** bằng đoạn code sau:

    (Đoạn code – *Lab RAG – Bài 4 co_can_cu*)

    ```python
    # Lấy điểm cao nhất chứ không lấy nodes[0]: sau Bài tập 3 thứ tự không còn giảm dần theo điểm
    return max((n.score or 0.0 for n in nodes), default=0.0) >= nguong
    ```

    > **Lưu ý**
    >
    > Khoảng cách giữa hai số chỉ 0,03, và ngưỡng được chọn trên chính 14 câu này. Gặp câu mới, câu có đáp án có thể dưới
    > 0,28 (từ chối nhầm) hoặc câu ngoài phạm vi có thể vượt 0,28. Ngưỡng cũng phụ thuộc cách chia: ở chunk 64 và 128,
    > câu ngoài phạm vi có điểm cao hơn câu có đáp án (Bài tập 1, Nhiệm vụ 3), nên không có ngưỡng nào tách được. Muốn
    > dùng thật phải hiệu chỉnh trên bộ câu lớn và kiểm lại trên bộ khác chưa dùng để chỉnh.

#### Nhiệm vụ 2 – Từ chối câu hỏi ngoài phạm vi

Nhiệm vụ này không cần Ollama, vì câu bị từ chối ở bước 2 thì không gọi LLM.

1. Chạy lệnh:

    ```bash
    python lab/lab_rag.py tra-loi "Học phí mỗi tín chỉ năm học 2025-2026 là bao nhiêu?" --nguong 0.28
    ```

    ```
    === ? Học phí mỗi tín chỉ năm học 2025-2026 là bao nhiêu?
    Bước 1 – truy hồi: Quy chế đào tạo SGU 2021 – Điều 10, 11 (0.266); Quy chế đào tạo SGU 2021 – Điều 17 (0.264); Quy chế đào tạo SGU 2021 – Điều 2, 3 (0.237)
    Bước 2 – không có trích đoạn nào đạt ngưỡng 0.28: từ chối, KHÔNG gọi LLM
    Không tìm thấy trong các văn bản quy định.
    ```

    *Câu ngoài phạm vi bị từ chối ngay ở bước kiểm căn cứ*

2. Chạy với một câu trong phạm vi để thấy bước 2 cho qua:

    ```bash
    python lab/lab_rag.py tra-loi "Vắng thi không có lý do chính đáng thì bị điểm bao nhiêu?" --nguong 0.28
    ```

    ```
    Bước 1 – truy hồi: Quy chế đào tạo SGU 2021 – Điều 9 (0.574); Quy chế đào tạo SGU 2021 – Điều 9 (0.258); Quy chế đào tạo SGU 2021 – Điều 19 (0.228)
    Bước 2 – đủ căn cứ
    ```

    Không có Ollama thì lệnh dừng ở đây với thông báo `Không gọi được Ollama (ConnectionError)`. Đó là hành vi đúng:
    bước 1 và 2 không phụ thuộc LLM.

#### Nhiệm vụ 3 – Sinh câu trả lời bằng Ollama (tùy chọn)

1. Chuẩn bị Ollama theo **Phụ lục B**.

2. Mở file **lab/lab_rag.py**, tìm biến **PROMPT**. Chú ý hai yêu cầu: ghi tên văn bản và số Điều làm căn cứ; nếu trích
   đoạn không có thông tin thì trả lời đúng câu "Không tìm thấy trong các văn bản quy định." Đây là lớp chặn thứ hai, cho
   những câu ngoài phạm vi lọt qua ngưỡng.

3. Chạy cả bộ câu hỏi qua ba bước:

    ```bash
    python lab/lab_rag.py tra-loi tat-ca --nguong 0.28 --them-3183 --phien-ban
    ```

    Với mỗi câu, lab in kết quả bước 1, bước 2, câu trả lời của LLM và dòng "Đáp án chuẩn".

4. Với mỗi câu, ghi vào bảng: bước 1 có Node đúng không; câu trả lời đúng hay sai; trích đúng văn bản/Điều không; nếu sai
   thì là lỗi truy hồi hay lỗi sinh.

5. Chạy lại **không có** `--phien-ban` và so câu trả lời của V02. Bạn sẽ thấy sắp xếp ở bước truy hồi ảnh hưởng thế nào
   tới câu trả lời cuối.

6. Đối chiếu với kết quả của nhóm (`qwen3:8b` trên Colab, chia cố định 256, có `--them-3183 --phien-ban`). Cột "Ngữ cảnh"
   được kiểm bằng cách tìm câu chữ của đáp án trong ba Node của bước 1:

    | Câu | Ngữ cảnh có đáp án? | Câu trả lời của LLM | Nội dung | LLM tự ghi Điều | Lỗi nằm ở |
    |---|---|---|---|---|---|
    | Q01 | Có | 02 lần thời gian kế hoạch chuẩn | Đúng | Điều 2 — đúng | — |
    | Q02 | Có | 06–20 giờ, Thứ 2–Thứ 7 | Đúng | Điều 4 — đúng | — |
    | Q03 | **Không**: đoạn Điều 7 dừng ngay trước khoản 3 | Không tìm thấy | Sai | — | **Truy hồi** (chunk cắt giữa Điều) |
    | Q04 | Có | Điểm 0 | Đúng | Điều 2 — **sai** (Điều 9) | Sinh: trích sai |
    | Q05 | Có | 3,2 đến cận 3,6 | Đúng | Điều 4 — **sai** (Điều 10) | Sinh: trích sai |
    | Q06 | Có (cả 0,80 và 1,00) | Chỉ "dưới 0,80" | Thiếu ý | Điều 11 — đúng | **Sinh**: bỏ sót ý |
    | Q07 | Có | 50% | Đúng | Điều 12 — đúng | — |
    | Q08 | Có | 03 tháng | Đúng | Điều 2 — **sai** (Điều 13) | Sinh: trích sai |
    | Q09 | Một phần: chỉ có mục a) | Chỉ "lực lượng vũ trang" | Thiếu ý | Điều 14 — đúng | **Truy hồi** (chunk cắt giữa danh sách) |
    | Q10 | Có | Năm thứ hai của chương trình thứ nhất | Đúng | Điều 1 — **sai** (Điều 17) | Sinh: trích sai |
    | V01 | Có | B+ | Đúng | QĐ 3183 Điều 9 — đúng | — |
    | V02 | Có (bảng gốc đứng đầu) | Không tìm thấy | Sai | — | **Sinh**: hai bảng mâu thuẫn |
    | O01, O02 | — | Từ chối ở bước 2, không gọi LLM | Đúng | — | — |

    *Chấm câu trả lời: chia cố định 256, qwen3:8b*

    Tổng: **8/12** câu đúng nội dung, nhưng chỉ **4/12** câu đúng cả nội dung lẫn số Điều; 2/2 câu ngoài phạm vi bị từ chối
    mà không cần gọi LLM.

7. Chú ý bốn điều mà R@k ở Bài tập 1 không cho thấy:

    1. **R@1 = 10/10 vẫn có thể thiếu đáp án.** Q03 và Q09 được luật chấm tính đúng, nhưng đoạn truy hồi bị cắt trước phần
       chứa đáp án. LLM từ chối ở Q03 là hành vi **đúng** với ngữ cảnh nó nhận được.
    2. **Đúng nội dung chưa chắc đúng nguồn.** Ở Q04, Q05, Q08, Q10, LLM nhầm số khoản trong nội dung ("2. Người học vắng
       mặt...") thành số Điều. Trong khi đó, nhãn nguồn ở bước 1 (lấy từ metadata) vẫn đúng. Vì vậy cần chấm riêng hai tiêu chí, và
       nguồn hiển thị nên lấy từ metadata.
    3. **Sắp đúng thứ tự chưa đủ để LLM chọn đúng phiên bản.** Ở V02, bảng điểm gốc đã đứng đầu, nhưng LLM thấy hai bảng
       mâu thuẫn và chọn từ chối; chạy không có `--phien-ban` (bảng mới đứng đầu) LLM cũng từ chối. Thông tin "áp dụng cho
       khóa nào" phải nằm trong ngữ cảnh LLM đọc (metadata hoặc tên văn bản), không chỉ ở thứ tự.
    4. **Hai lớp từ chối bổ sung cho nhau.** Chạy cùng lệnh với `--chia dieu --chunk 256`, câu O01 có điểm 0,312, vượt
       ngưỡng 0,28 (ngưỡng chọn cho cách chia cố định), nhưng prompt vẫn khiến LLM trả lời "Không tìm thấy trong các văn bản
       quy định."

    Với `--chia dieu --chunk 256`, nhóm đo được 7/12 câu đúng nội dung, 4/12 câu đúng cả nội dung lẫn số Điều; LLM vẫn ghi
    sai Điều ở Q01, Q04, Q08 và trả lời V01 là B thay vì B+. Kết quả LLM thay đổi theo model và lần chạy: dùng bảng trên để
    đối chiếu cách phân tích, không phải để so từng chữ.

---

## Tổng kết

Trong Hands-On Lab này, bạn đã dựng một retriever bằng LlamaIndex trên văn bản quy chế thật và đo nó bằng Recall@k, MRR.
Bạn đã thấy chunk quá nhỏ làm mất ngữ cảnh và khiến câu ngoài phạm vi khớp vu vơ, còn chunk quá lớn vượt 256 token của
model embedding và bị cắt đuôi. Bạn đã chia văn bản theo cấu trúc Điều để nhãn nguồn trong metadata chính xác tới từng
Điều (dù LLM vẫn có thể tự ghi sai Điều), phát hiện lỗi nhầm phiên bản khi thêm văn bản sửa đổi và sửa nó bằng metadata
hiệu lực. Cuối cùng, bạn đã tách truy hồi khỏi sinh câu trả lời để từ chối câu ngoài phạm vi mà không cần gọi LLM, và
biết lỗi nằm ở bước nào.

---

## Phụ lục A: Cài đặt môi trường

1. Clone repo và chuyển vào thư mục gốc:

    ```bash
    git clone https://github.com/huynhthanhtien/LlamaIndex_RAG.git
    cd LlamaIndex_RAG
    ```

2. Tạo và kích hoạt môi trường ảo:

    ```bash
    python3 -m venv venv
    source venv/bin/activate          # fish: source venv/bin/activate.fish; Windows: venv\Scripts\activate
    ```

3. Cài thư viện:

    ```bash
    pip install -r requirements.txt
    ```

    Lab cần `llama-index-core`, `llama-index-embeddings-huggingface`, `transformers` và `sentence-transformers`;
    `llama-index-llms-ollama` chỉ cần cho Bài tập 4 – Nhiệm vụ 3.

4. Tải trước model embedding (khoảng 540 MB) để các bài tập không phải chờ:

    ```bash
    python -c "from sentence_transformers import SentenceTransformer; \
    m = SentenceTransformer('bkai-foundation-models/vietnamese-bi-encoder'); print(m.max_seq_length)"
    ```

    Kết quả mong đợi: in ra `256`, là số token tối đa model đọc được cho mỗi Node.

5. Kiểm tra lab chạy được:

    ```bash
    python lab/lab_rag.py chia --chunk 256 | tail -1
    ```

    ```
    78 Node | token TB 111, lớn nhất 154 | 0 Node dài hơn 256 token mà model embedding đọc được
    ```

## Phụ lục B: Chuẩn bị Ollama

Chỉ cần cho Bài tập 4 – Nhiệm vụ 3. Chọn một trong hai cách.

**Cách 1: Ollama trên máy của bạn**

1. Cài Ollama theo hướng dẫn tại [ollama.com/download](https://ollama.com/download).
2. Tải model và khởi động server:

    ```bash
    ollama pull qwen3:4b
    ollama serve
    ```

3. Kiểm tra: `curl http://localhost:11434/api/tags` phải liệt kê `qwen3:4b`.

**Cách 2: Ollama trên Google Colab (máy không đủ RAM/GPU)**

1. Trên Colab (runtime T4 GPU), chạy hai lệnh trong mục "Chạy LLM + embedding trên colab" của `README.md` ở thư mục gốc
   repo. Script in ra dòng `OLLAMA_BASE_URL=...`.
2. Trên máy của bạn, đặt biến môi trường trước khi chạy lab:

    ```bash
    export OLLAMA_BASE_URL=<URL in ra từ Colab>
    export LAB_LLM=qwen3:8b               # model mà script Colab đã pull
    ```

3. Tắt runtime Colab khi không dùng: URL công khai không có xác thực.

## Phụ lục C: Xử lý lỗi thường gặp

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| `NotImplementedError: BÀI TẬP ...` | Chưa thay thân hàm trong `lab/bai_lam.py` | Làm nhiệm vụ tương ứng, hoặc thêm `--dap-an` để chạy lời giải |
| `NameError: name 'HEADING' is not defined` (hoặc `re`, `SentenceSplitter`, `SUA_DOI_3183`) | Chưa thêm đoạn import/bảng ở đầu `lab/bai_lam.py` | Làm lại Bài tập 2 – Nhiệm vụ 1 bước 1, Bài tập 3 – Nhiệm vụ 2 bước 2 |
| Lỗi lệch số chiều vector, ví dụ `shapes (1024,) and (768,) not aligned` | Index lưu bằng model embedding A, đổi sang model B khác số chiều mà vẫn nạp index cũ | Mỗi model một thư mục index; `--luu` của lab lưu vào `lab/storage/<model>/<cách chia>`. Hệ thống chính so "vân tay" (model + loader + sha256 từng file) trước khi nạp (`src/index_builder.py`) |
| Đổi chunk size mà số đo không đổi | Nạp lại index đã lưu của cấu hình cũ | Đưa mọi tham số ảnh hưởng tới Node vào tên thư mục lưu hoặc vân tay index |
| Mỗi lần chạy đều chậm vì embed lại | Không lưu index | `index.storage_context.persist(...)` rồi `load_index_from_storage(...)`; trong lab thêm `--luu` |
| R@1 tụt khi tăng chunk size | Node dài hơn 256 token, model embedding bỏ phần đuôi | Đếm token bằng tokenizer của model embedding (không phải tiktoken); giữ Node dưới giới hạn hoặc dùng model đọc dài hơn |
| Chia theo Điều ra nhiều hoặc ít hơn 21 Node | Lỗi OCR làm hỏng heading: nội dung dính vào dòng tiêu đề ("Điều 12. Công nhận ... bL Kết quả"), "1." thành "]." | Sửa ở bước làm sạch dữ liệu, không vá trong regex; kiểm bằng `lab_rag.py chia --chia dieu` |
| Câu khóa 2022 được trả lời bằng bảng điểm khóa 2025 | Nhầm phiên bản: embedding không biết hiệu lực | Bài tập 3 |
| `Không gọi được Ollama (ConnectionError)` | Ollama chưa chạy, sai `OLLAMA_BASE_URL`, hoặc chưa `ollama pull` | Phụ lục B |
| Câu trả lời có khối `<think>...</think>` | qwen3 vẫn trả phần suy luận dù đã tắt | Lab đã lọc bằng regex; hệ thống chính tắt `thinking` khi gọi model |
| Lỗi mạng khi tải model dù đã tải trước đó | Máy không có Internet | Đặt `HF_HUB_OFFLINE=1` để dùng bản trong `~/.cache/huggingface` |

## Phụ lục D: Câu hỏi tự kiểm tra

1. Vì sao không nên chọn chunk size chỉ dựa vào R@1 trên 10 câu?
2. Một câu hỏi ra đáp án sai. Làm sao biết lỗi nằm ở truy hồi hay ở LLM?
3. Vì sao `co_can_cu` lấy điểm cao nhất thay vì điểm của `nodes[0]`?
4. Khi thêm một văn bản sửa đổi mới vào index, cần kiểm lại những câu hỏi nào?
5. Tăng top-k từ 3 lên 10 có sửa được câu V01 ở Bài tập 1 không? Vì sao?
6. Q03 đạt R@1 nhưng LLM trả lời "Không tìm thấy". Đây là lỗi của LLM không?

<details>
<summary><b>Đáp án</b></summary>

1. Chênh một câu là 10 điểm phần trăm; chunk 256 và 512 hòa nhau trên bộ này. Cần bộ câu lớn hơn, kiểm định thống kê, và
   xem cả số Node bị cắt khi embed.
2. Xem bước 1 của `tra-loi`: Node đúng không có trong danh sách là lỗi truy hồi; có mà câu trả lời vẫn sai là lỗi sinh.
3. Sau `sap_xep_theo_phien_ban`, Node đầu danh sách có thể không phải Node có điểm cao nhất (ví dụ V02: Node đầu có điểm
   0,382, Node thứ hai 0,437).
4. Các câu về những Điều bị sửa, cho **cả** khóa áp dụng bản mới và khóa còn áp dụng bản cũ (như cặp V01/V02).
5. Không. Lúc đó index chưa có QĐ 3183, Node đúng không tồn tại; top-k chỉ sửa được lỗi xếp hạng.
6. Không. Đoạn hạng 1 thuộc Điều 7 nên luật chấm tính đúng, nhưng nó dừng trước khoản 3 chứa đáp án. LLM từ chối là đúng
   với ngữ cảnh; lỗi nằm ở cách chia và ở luật chấm theo Điều (không kiểm đoạn có chứa câu trả lời).
</details>

## Phụ lục E: Điều kiện đo các kết quả trong lab

- Ngày đo: 30/10/2026. Máy: CPU 16 luồng, không dùng GPU. `llama-index-core` 0.14.24, `sentence-transformers` 6.0.1.
- Model embedding: `bkai-foundation-models/vietnamese-bi-encoder` (768 chiều, đọc tối đa 256 token).
- Văn bản: `data/processed/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc/`. Quy chế 2021 chỉ lấy phần Quy chế, bỏ quyết
  định ban hành; QĐ 3183/2025 lấy cả thân văn bản.
- Bài tập 1–3 và Bài tập 4 – Nhiệm vụ 1, 2 chạy lại được và ra cùng số trên cùng model.
- Bài tập 4 – Nhiệm vụ 3: `qwen3:8b` (Q4_K_M, digest `500a1f067a9f…`) qua Ollama trên Google Colab, temperature 0,
  seed 42, tắt thinking. Câu trả lời của LLM có thể khác giữa các lần chạy và các máy.
- Bộ 14 câu chỉ dùng để học, không phải bộ đánh giá của hệ thống chính (xem thư mục `eval/`).
