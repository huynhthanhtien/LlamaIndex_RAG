# Đề xuất xử lý nhận xét báo cáo Nhóm 08

> Phạm vi: nhận xét mục 2–10 về bản `report/Nhom 08 - … .docx`.
> Cách làm: đối chiếu từng ý với nguồn LaTeX (`report/`), bản PDF (`report/main.pdf`, build 09/10 23:17),
> mã nguồn và các file kết quả trong `eval/results/`. **Không sửa code.** Các con số trong tài liệu này
> là số tự đo khi kiểm tra (ghi rõ cách đo); nếu một chỗ chỉ là giả thuyết thì có ghi là giả thuyết.

---

## 0. Tóm tắt nhanh

| # | Nhóm vấn đề | Nguyên nhân gốc (đã kiểm) | Việc cần làm | Ưu tiên |
|---|---|---|---|---|
| 4 | Tham chiếu chéo hỏng | File .docx **không sinh từ bản LaTeX hiện tại**: `main.pdf` đã đánh số đúng (Mục 10.2.2.4, Chương 11), còn .docx mang số của cấu trúc cũ. Vẫn còn `.aux` cũ (`chapters/05-danh-gia.aux` ghi `ch:danh-gia = 5`) | Dọn `.aux`, build lại, sinh lại .docx; sửa thêm 4 tham chiếu trỏ **sai về nghĩa** ngay trong LaTeX | Cao (nhanh) |
| 5 | Giọng văn "bản trước/bản mới", lỗi ký tự | Báo cáo được sửa tăng dần qua từng bản nộp; có chỗ sửa tay trong .docx | Viết lại thành mô tả hệ thống hiện tại, dồn lịch sử vào Bảng 10.3 + Phụ lục A | Cao |
| 6 | Mô tả repo mâu thuẫn | Cây thư mục và mô tả script `test_ocr.py` còn từ pipeline cũ | Sinh lại cây thư mục từ `git ls-files`; sửa 4 bảng | Cao (nhanh) |
| 7 | Chunk/embedding/context | Ngưỡng cắt đếm theo **từ**, splitter đếm theo **token tiktoken**; profile local cắt mất đuôi Node; số lượt gọi LLM chưa được đo | Thêm số đo (đã có sẵn bên dưới), sửa câu chữ; đo thêm bằng tokenizer Qwen | Cao |
| 8 | Minh chứng còn mỏng | Placeholder, chưa có token/độ trễ, từ chối chỉ có 3 câu | In Node thật, lấy số từ Ollama, mở rộng bộ câu ngoài corpus | Trung bình–cao |
| 9 | Đánh giá thực nghiệm | Dev set trùng test set; luật chấm hai bộ khác nhau; nDCG@1 thừa | Tách tập kiểm chứng, ghi rõ luật chấm, bỏ cột thừa | Trung bình |
| 2 | Kiến thức miền nằm trong prompt | Mục sửa đổi QĐ 3183 chỉ chứa bảng, không có câu dẫn hay khóa áp dụng | Chuyển kiến thức sang dữ liệu/metadata, đo A/B | Trung bình |
| 10 | Phụ lục làm việc nhóm | Bảng A.1 bản .docx khác bản LaTeX; thiếu phần việc của 2 thành viên | Cả nhóm tự điền, kèm minh chứng | Cao (bắt buộc) |

**Nguyên tắc chung:** chọn **một nguồn duy nhất** là LaTeX. Mọi sửa trong .docx (tên người làm ở Bảng A.1, …)
phải chép ngược vào `.tex`, sau đó sinh lại .docx từ bản build sạch. Nếu cứ sửa song song thì lỗi ở
mục 4–5 sẽ lặp lại ở mỗi lần nộp.

---

## Mục 2. Rủi ro miền quy chế và kiến thức miền đặt trong prompt

### Kiểm chứng
- `src/query_engine.py` (`QA_PROMPT`) có chú giải cứng: thang 10 ↔ Điều 9, thang 4 ↔ Điều 10.
- Phiên chạy 110 câu ngày 10/10 (`eval/results/tra-loi-toan-bo-2026-10-10.jsonl`, prompt đã có chú giải)
  cho thấy lỗi vẫn còn và giờ **phụ thuộc vào cách hỏi**:
  - "Điểm 8,4 hệ 10 thì hệ 4 được bao nhiêu?" → **3,0** (bảng khóa trước 2025);
  - "nếu tôi được 8.4 hệ 10 thì hệ 4 được bao nhiêu điểm" → **3,5** (bảng QĐ 3183, khóa 2025 trở đi);
  - không câu nào nói đáp án áp dụng cho khóa nào;
  - "rớt một môn nhưng các kỳ còn lại 4.0…" → "Điểm 4,0 thuộc phạm vi của loại **D**" (vẫn lẫn thang 4 với thang 10).
- Câu "A thì được bao nhiêu điểm hệ 10" đã trả lời đúng (8,5–10). Vậy chú giải có tác dụng một phần, nhưng
  **chưa có phép đo** (đúng như 4.5.2 tự thừa nhận).

### Giải pháp đề xuất
1. **Đo trước khi bàn tiếp (không cần sửa code):** lập một tập con khoảng 10–15 câu về điểm và thang điểm
   (lấy từ 110 câu sẵn có). So hai phiên đã có: 08/10 (chưa có chú giải) và 10/10 (đã có chú giải). Ghi
   bảng đúng/sai cho từng câu. Nhớ ghi rằng giữa hai phiên còn khác nhau ở các yếu tố khác (top-k).
2. **Chuyển kiến thức từ prompt sang dữ liệu** (hướng đã nêu ở 12.1; nên viết thành kế hoạch cụ thể):
   - Gắn câu dẫn của văn bản gốc vào mục sửa đổi, ví dụ "Điểm học phần chấm theo thang điểm 10 …" cho
     mục sửa đổi Điều 9 và "quy đổi sang thang điểm 4 để tính điểm trung bình" cho mục sửa đổi Điều 10.
     Có thể làm ở tầng 1 (`data/ocr`, nơi được phép sửa tay) hoặc thêm vào metadata.
   - Thêm metadata **khóa áp dụng** (`ap_dung`, ví dụ "khóa tuyển sinh từ 2025") lấy từ Điều 2 QĐ 3183.
     `scripts/clean_md.py` đã có sẵn trường `ap_dung` trong `META_FIELDS`, chỉ cần điền và đưa trường này
     vào phần nội dung LLM nhận.
   - Yêu cầu câu trả lời về điểm phải nêu khóa áp dụng, hoặc trình bày **cả hai bảng** khi người hỏi không nói khóa.
3. **Quy đổi điểm là phép tra bảng** (chính báo cáo đã viết ở 1.3.4): nên đưa ra khỏi LLM bằng một
   `FunctionTool` tra bảng theo khóa. Nếu chưa kịp làm thì ghi rõ trong phần Hạn chế.
4. Trong báo cáo, đổi cách viết chú giải miền thành **"giải pháp tạm, chưa dùng lại được, đã/chưa đo"**,
   kèm kết quả A/B ở bước 1.

---

## Mục 3. Điểm làm tốt

Giữ nguyên. Lưu ý khi sửa các mục khác: **đừng làm mất** chuỗi "cơ chế → mã → kết quả → giải thích" ở
Ch.4, Bảng 4.2, phép kiểm chéo với `RetrieverEvaluator`, các số McNemar, Bảng 1.3 và 10.2.

---

## Mục 4. Tham chiếu chéo hỏng

### Nguyên nhân (đã kiểm)
- Trong LaTeX, mọi tham chiếu đều dùng `\ref{…}`. `report/main.pdf` (build 09/10) in **đúng**:
  "Mục 10.2.2.4", "Chương 11".
- Bản .docx in "Mục 5.2.4", "Mục 5.2.2", "Bảng 5.1", "Bảng 5.3", "Chương 5", "Mục 5.4". Đây là số của cấu trúc
  cũ. Trong repo vẫn còn các file aux cũ ghi đúng những số đó:
  `report/chapters/05-danh-gia.aux`, `01-gioi-thieu.aux`, `02-co-so-ly-thuyet.aux` (và bản sao trong
  `report/build/chapters/`). Ví dụ `05-danh-gia.aux` có `\newlabel{ch:danh-gia}{{5}…}` và
  `\newlabel{tab:recall}{{5.1}…}`.
- Bản .docx còn có chỗ **sửa tay** không có trong LaTeX (Bảng A.1 ghi tên người làm, chuỗi rác "ttuan05ruy hồi").
  Vậy .docx đã tách khỏi nguồn LaTeX.

### Giải pháp
1. Xóa các file `.aux` không còn chương tương ứng (`01-gioi-thieu`, `02-co-so-ly-thuyet`, `05-danh-gia`), chạy
   `latexmk -C` rồi build lại hai lần (`make report`).
2. Sinh lại .docx từ bản build sạch, rồi soát bằng cách tìm chuỗi `Mục 5.`, `Bảng 5.`, `Chương 5`. Trong bản
   đúng chỉ còn những chỗ thực sự thuộc Ch.5 (node parser).
3. **Bốn tham chiếu sai về nghĩa ngay trong LaTeX** (build lại vẫn sai):

| Vị trí | Hiện tại | Nên trỏ tới |
|---|---|---|
| `frontmatter/loi-mo-dau.tex:52` (Lời mở đầu, mục 3) | `Chương~\ref{ch:danh-gia}` (cả Ch.11) | Mục 11.1 "Các quyết định đổi hướng". Cần thêm `\label` cho section 11.1 |
| `chapters/03-moi-truong-kien-truc.tex:54` (3.1.4) | "Các số liệu ở Chương~\ref{ch:danh-gia}" | `Mục~\ref{sec:danh-gia-thuc-nghiem}` và `Bảng~\ref{tab:recall}` (Ch.4 và Ch.8) |
| `chapters/p1-01-gioi-thieu-llamaindex.tex:243` (Bảng 1.3, dòng BM25) | `Mục~\ref{sec:retriever}` (4.4) | `Mục~\ref{sec:hybrid}` (8.2) |
| `chapters/07-trich-dan-tu-choi.tex:19` | `Mục~\ref{sec:retriever}` | Đúng nếu ý là "điểm cosine thấp" (4.4.2). Giữ nguyên, nên trỏ tới `tab:top-k` cho rõ |

4. **Danh sách kết quả 1–6 bị tách:** 4.6.2 còn đoạn "1.", "5.", "6."; đoạn "2–4" nằm ở Ch.8. Nên **bỏ số thứ tự**
   và đặt tên ngắn cho từng đoạn ("Embedding là yếu tố quyết định", "Kiểm chứng chéo", "Ca trượt còn lại"). Ch.8
   tự đánh lại "Rerank", "Hybrid", "Kiểm định". Nếu muốn có một danh sách đủ 6 ý, đặt danh sách đó ở Kết luận
   12.3, mỗi ý kèm `\ref`.
5. **"Bốn độ đo và hai loại kiểm định"** (`04-cong-nghe-cot-loi.tex:351`): danh sách thật gồm 3 độ đo (Recall@k,
   MRR, nDCG@k), 1 cách ước lượng khoảng tin cậy (bootstrap) và 1 kiểm định (McNemar). Sửa thành *"Ba độ đo,
   khoảng tin cậy bootstrap và kiểm định McNemar được cài trong eval/metrics.py"*.

---

## Mục 5. Giọng "bản trước/bản mới", kế hoạch 12 tuần, lỗi ký tự, công thức

### 5.1 Giọng nhật ký sửa bản
Danh sách chỗ cần viết lại (theo `grep` trên `.tex`):

| File:dòng | Cụm cần bỏ |
|---|---|
| `03-moi-truong-kien-truc.tex:9` | "(trước đây chỉ ghi tên gói…)" |
| `03-moi-truong-kien-truc.tex:54` | "Ở bản báo cáo trước… Bản hiện tại… ở bản trước" |
| `04-cong-nghe-cot-loi.tex:90, 175, 262, 267, 374` | "bản đầu", "đo trước đây", "từ tuần 05–09/10", "ở bản trước", "bản báo cáo trước" |
| `05-node-parser.tex:10, 23, 26, 28, 38` | "Giai đoạn 1 của bản báo cáo trước", "Bản trước/Bản mới", "Trước đây" |
| `06-persistent-index.tex:18–19, 32` | "Bản trước/Bản mới/Từ bản này" |
| `10-trien-khai.tex:35, 48, 51, 93–94, 110, 115, 118` | "Bản báo cáo trước/Bản này" |
| `11-danh-gia-nhin-lai.tex:53` | "ở bản báo cáo trước" |
| `12-huong-phat-trien.tex:7–11` | đoạn "Đã xong trong bản này" |
| `p1-01-gioi-thieu-llamaindex.tex:162` | "Bản đầu dùng (ingestion.py)" |

**Cách viết lại:**
- Thân bài chỉ mô tả **hệ thống hiện tại** và **lý do thiết kế**. Ví dụ ở 5.2: *"Loader chỉ gắn khóa metadata
  có giá trị, vì LlamaIndex ghép metadata vào văn bản trước khi embedding; khóa rỗng tạo ra các dòng `chuong:`
  vô nghĩa trong vector."* Lý do vẫn còn, không cần chữ "bản trước".
- Những thay đổi **có số đo trước–sau** là minh chứng tối ưu, nên giữ, nhưng chỉ ở **Bảng 10.3**.
- Lịch sử theo thời gian (OCR theo trang → Markdown hai tầng, OOM → fp16, …) chuyển sang **Phụ lục A**,
  thành mục "Các quyết định đổi hướng theo tuần".
- Bỏ đoạn "Đã xong trong bản này" ở 12.1. Mục 12.1 chỉ giữ danh sách việc **còn lại**.

### 5.2 Kế hoạch 12 tuần
Vấn đề: bảng ở Lời mở đầu mục 4 ghi "trạng thái tại tuần 5" nhưng nhiều ô tuần 6–10 đã ghi "xong sớm". Phụ lục A
lại dùng mốc theo ngày (tuần 3 = 21–27/09, tuần 5 = 05–09/10). Cụm "tuần 05–09/10" dễ đọc nhầm thành "tuần 5 đến 9".

Giải pháp:
- Lấy **lịch học phần chính thức** (đề cương/thông báo của GV) làm cột mốc. Repo không có lịch này
  (`docs/bao_cao_phan_tich_yeu_cau.md` chỉ có khung môn học), nên **nhóm phải tự đối chiếu**. Không suy ra lịch từ ngày commit.
- Bảng nên có các cột: *Tuần (theo lịch học phần) | Ngày | Nội dung khung | Việc của nhóm | Người phụ trách | Trạng thái thật*.
- Luôn viết ngày theo dạng "tuần 5 (05/10–09/10/2026)".

### 5.3 Lỗi ký tự và cụm chen giữa câu
- "ttuan05ruy hồi" (12.3) **chỉ có trong .docx**, LaTeX vẫn đúng ("truy hồi"). Đây là lỗi sửa tay trong Word,
  sẽ hết khi sinh lại .docx.
- 4.5.1, "từ tuần 05–09/10 có thể bật…" (`04-cong-nghe-cot-loi.tex:262`): bỏ mốc thời gian, viết *"Chế độ suy nghĩ
  mặc định tắt; bật bằng `RAG_THINKING=1`…"*.

### 5.4 Công thức
Đã kiểm file .docx: công thức ở dạng OMML và **vẫn còn** ký hiệu ∑ (10 phần tử `m:nary` có `m:chr="∑"`, các chỉ số
dưới vẫn nằm trong cấu trúc OMML). Thường thì Σ và chỉ số chỉ mất khi chép sang văn bản thuần hoặc khi chuyển
đổi bằng công cụ khác. Việc cần làm:
1. Mở .docx bằng **Microsoft Word** (không dùng trình xem rút gọn) và kiểm tra ba công thức cosine, Recall@k, MRR.
2. Nếu nộp PDF thì nộp `main.pdf` build từ LaTeX, không xuất PDF từ .docx.
3. Nếu Word vẫn hiển thị sai, viết lại ba công thức này bằng Equation Editor. Chỉ có 3 công thức chính nên làm tay nhanh.

---

## Mục 6. Mâu thuẫn mô tả repo

| Chỗ sai | Thực tế trong repo | Sửa thành |
|---|---|---|
| 3.3.1 cây thư mục thiếu `scripts/extract_to_md.py`, `clean_md.py`, `setup_server_v2.sh`, `colab_server.py`, `reorganize_raw.py`, `eval/run_batch_cau_hoi.py`, `eval/compare_results.py`, `tests/test_llm.py` | Các file này đều có | Sinh lại cây từ `git ls-files` (hoặc `tree -I 'venv\|__pycache__\|storage'`), giữ chú thích ngắn |
| 3.3.3 "`test_ocr.py` tạo bản OCR … mà `index_builder.py` dùng làm đầu vào" | `index_builder` → `processed_loader` → đọc `data/processed` (`src/corpus.py: PROCESSED_ROOT`). `test_ocr.py` chỉ OCR một PDF ra `data/ocr`, không nằm trong pipeline | *"`test_ocr.py`: script thử OCR ban đầu, không còn trong pipeline. Đầu vào thật: `extract_to_md.py` → `clean_md.py` (Mục 4.1.2)"* |
| Bảng 3.3: "Kiểm thử — Bắt buộc lõi" | Bảng 4.1 có 6 mục lõi, không có kiểm thử; Bảng 10.4 xếp unit test vào Tầng 2 | Cột "Mức" dùng thống nhất ký hiệu tầng: 1A/1B/2/3. Kiểm thử = **Tầng 2** |
| Bảng 3.2: embedding_device "cuda" cho cả hai profile | `config.py:138,147`: mặc định `RAG_EMBED_DEVICE` = "cuda", `resolve_device()` tự hạ xuống CPU | Ghi *"cuda (mặc định, tự hạ về cpu khi không có GPU)"* và thêm dòng **"Thiết bị khi đo số liệu trong báo cáo: CPU"** |
| Bảng 11.1: "Đạt 6/6" | Mục 6 = đánh giá thực nghiệm. Truy hồi đã đo, câu trả lời chưa chấm tự động | *"Đạt 6/6 (mục 6: đánh giá truy hồi đạt; đánh giá câu trả lời bằng evaluator chưa chạy)"*. Sửa giống vậy ở Phụ lục C dòng 1A |

Gợi ý thêm: bỏ hẳn hai module cũ `ingestion.py` và `node_parser.py` khỏi cây chính, hoặc ghi chúng ở một dòng
"legacy". Ghi xen trong cây như hiện nay dễ khiến người đọc tưởng chúng còn dùng.

---

## Mục 7. Kỹ thuật chunk/embedding

Số liệu dưới đây được đo ngày 11/10 trên 54 Node thật, profile `server`, bằng `load_corpus_nodes()` với các
tokenizer đã có trong cache HF. Script đo chỉ đọc dữ liệu, không sửa gì. Nên đưa bảng này vào 4.2.2.

| Độ dài mỗi Node (văn bản embed) | Trung bình | Trung vị | Lớn nhất |
|---|---|---|---|
| Ký tự | **1 129** | 902 | 3 220 (Điều 5 QC 2021) |
| Từ (tách theo khoảng trắng) | 242 | 196 | 734 |
| Token tiktoken (tokenizer mặc định của LlamaIndex) | 548 | 432 | 1 651 |
| Token `AITeamVN/Vietnamese_Embedding` | 297 | 225 | 910 |
| Token `vietnamese-bi-encoder` (chưa tách từ) | 307 | 229 | 1 012 |

### (a) Đơn vị `MAX_TU` lệch với `SentenceSplitter`
- `processed_loader.py:109`: so `len(text.split()) <= MAX_TU` (đếm **từ**). Nếu vượt thì gọi
  `SentenceSplitter(chunk_size=1024, chunk_overlap=50)`, mà splitter này đếm **token tiktoken**.
- Đo được: trung bình **2,27 token tiktoken cho mỗi từ** tiếng Việt. Khi một Điều vượt 1 024 từ, splitter sẽ cắt
  thành các đoạn khoảng **450 từ**, chứ không phải 1 024 từ. Overlap 50 token tương đương khoảng 22 từ.
- Trên corpus hiện tại **không Node nào vượt 1 024 từ** (dài nhất 734 từ), nên splitter **chưa từng chạy**:
  có 0 Node mang `phan_doan`. Nếu đếm theo tiktoken thì có 7 Node vượt 1 024 token.
- Hệ quả khi viết báo cáo:
  - 4.2.2 cần nói rõ: *ngưỡng là 1 024 từ, splitter đếm theo token tiktoken; trên corpus hiện tại splitter không
    kích hoạt, nên kết quả hiện tại thực chất là "mỗi Điều/mục sửa đổi = một Node"*.
  - Sửa số "khoảng 1 500 ký tự/Node" thành **1 129** (trung vị 902).
  - Bảng 4.2 ghi "QĐ 3183 – sửa đổi Điều 9 (**phần đoạn khác**)". Thực tế QĐ 3183 có **hai mục sửa đổi Điều 9
    riêng biệt**, cả hai đều mang nhãn "Sửa đổi Điều 9", không phải `phan_doan`. Cần sửa chú thích. Đây cũng là lý do
    nên phân biệt nhãn theo khoản (xem mục 8).
- Hướng sửa (đề xuất, chưa làm): đếm ngưỡng bằng **cùng một tokenizer** với splitter. Tốt nhất là tokenizer của mô
  hình embedding, truyền vào qua `SentenceSplitter(tokenizer=…)`. Khi đó `MAX_TU` đổi tên thành `MAX_TOKEN`.

### (b) Profile local: `vietnamese-bi-encoder` cắt mất đuôi Node
- `sentence_bert_config.json` của mô hình ghi `max_seq_length = 256`. Đo được **25/54 Node (46%) dài hơn 256
  token**. Phần sau token 256 bị bỏ khi embed, mà phần này thường chứa các khoản cuối của Điều.
- Model card yêu cầu **tách từ tiếng Việt** (PyVi) trước khi encode. Repo hiện không gọi `pyvi`/`underthesea` ở
  đâu cả (`grep` không có kết quả), nên profile local đang embed văn bản chưa tách từ.
- Profile `server` (`AITeamVN/Vietnamese_Embedding`) có `max_seq_length = 8192`, Node dài nhất 910 token, nên
  **không bị cắt**. Câu "1 024 vì mô hình server nhận chuỗi dài" ở 4.2.2 vẫn đúng, chỉ cần nói thêm là câu này
  không đúng cho profile local.
- Giải pháp, chọn một:
  1. Ghi rõ trong Phụ lục D: profile local bị cắt ở 256 token và chưa tách từ, nên **không dùng để báo cáo chất
     lượng**. Kết quả chỉ để tham khảo.
  2. Nếu muốn so sánh nghiêm túc: thêm bước tách từ (cho cả Node lẫn câu hỏi), cắt Node theo khoản cho profile
     local, rồi đo lại R@k trên 54 Node (việc đã hẹn ở Phụ lục D).
  3. Đổi profile local sang `AITeamVN/Vietnamese_Embedding` chạy CPU. Embed 54 Node mất khoảng 77 s, chấp nhận được.

### (c) "10 Node vẫn vừa một lượt gọi LLM" chưa được đo
Những gì đã kiểm:
- `llama-index-llms-ollama` truyền `context_window=8192` xuống Ollama dưới dạng `num_ctx`.
- Chế độ `compact` của LlamaIndex dồn Node vào prompt dựa trên **tokenizer toàn cục (mặc định tiktoken cl100k)**,
  không dùng tokenizer của Qwen. Hạn mức là `context_window − num_output (256) − độ dài prompt`, khoảng 7 400 token.
- Văn bản LLM nhận (metadata chế độ LLM) đo theo tiktoken: trung bình 590 token/Node, nên 10 Node trung bình
  khoảng **5 900** (vừa). Nhưng 10 Node dài nhất cộng lại **12 685**, vượt hạn mức. Với những câu truy hồi trúng
  các Điều dài (Điều 2, 5, 8 QC 2021; Điều 3, 4 QĐ 2375), `compact` sẽ chia thành **2 lượt gọi**, và lượt 2 chạy
  theo kiểu refine.
- **Điểm quan trọng:** `build_query_engine()` chỉ đặt `text_qa_template=QA_PROMPT`. **Prompt refine vẫn là prompt
  mặc định tiếng Anh**, nên ở lượt 2 mô hình không còn thấy các ràng buộc "trích nguyên văn", "không tự quy đổi"
  hay "nói không tìm thấy". Đây là nghi vấn hợp lý cho lỗi **"30 tuần"** (Điều 6, vẫn sai ở phiên 10/10) và cho
  các câu trả lời không ổn định theo cách diễn đạt. **Cần đo trước khi kết luận.**

Cách đo (không cần sửa mã nguồn của hệ thống, chỉ cần chạy một script đo riêng hoặc dùng notebook):
1. Đếm token bằng tokenizer Qwen thật: `AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")`, áp lên prompt đã ghép
   cho từng câu trong 110 câu.
2. Đếm số lượt gọi LLM cho mỗi câu: gắn `LlamaDebugHandler` (hoặc `TokenCountingHandler`) vào
   `Settings.callback_manager` rồi đếm sự kiện `CBEventType.LLM`.
3. Lấy số thật từ Ollama: response thô có `prompt_eval_count`. Nếu con số này gần 8 192 thì Ollama đang
   **cắt bớt ngữ cảnh**.
4. Báo cáo bảng: *số câu gọi 1 lượt / 2 lượt / nhiều hơn*, *token prompt trung bình và lớn nhất (theo Qwen)*,
   và kiểm tra riêng câu "khối lượng học kỳ chính".

Hướng sửa nếu nghi vấn đúng (đề xuất): đặt `refine_template` tiếng Việt có cùng các ràng buộc; hoặc đặt
`Settings.tokenizer` bằng tokenizer Qwen để LlamaIndex đếm đúng; hoặc giới hạn số Node đưa vào LLM (ví dụ 5)
bằng một postprocessor.

---

## Mục 8. Minh chứng còn thiếu chi tiết

### 8.1 Đoạn mã 5.1 chỉ có placeholder "<nguyên văn Điều 9>"
In **một Node thật** lấy từ chỉ mục đã lưu, không lấy từ loader. Lý do: `node_id` do loader sinh là UUID ngẫu nhiên
(hai lần chạy `load_corpus_nodes()` cho hai bộ id khác nhau, đã kiểm). Chỉ id trong `storage/.../docstore.json` mới
cố định. Nội dung cần in:

```python
# chạy trong notebook / python -i, KHÔNG phải sửa src
from llama_index.core.schema import MetadataMode
node = next(n for n in index.docstore.docs.values()
            if n.metadata.get("nguon_trich", "").startswith("Điều 9 — Quy chế"))
print("node_id :", node.node_id)
print("metadata:", node.metadata)
print("excluded_embed:", node.excluded_embed_metadata_keys)
print("--- EMBED ---\n", node.get_content(MetadataMode.EMBED)[:800])
print("--- LLM ---\n",   node.get_content(MetadataMode.LLM)[:300])
```

Nên in hai Node: một Điều thường (Điều 9 QC 2021) và một mục sửa đổi (sửa đổi Điều 9 của QĐ 3183). Như vậy thấy được
sự khác nhau về `phan` và `sua_doi_dieu`, đúng yêu cầu "in ra nội dung vài node". Nếu quá dài thì cắt bớt, nhưng
phải giữ đủ dòng `nguon_trich` cùng 2–3 khoản đầu.

Đề xuất mã nguồn (chưa làm): đặt `id_` cố định cho Node, ví dụ băm `file + dieu + phan + phan_doan`, để trích dẫn
và nhãn đánh giá có thể gắn theo Node.

### 8.2 Độ trễ sinh, số token, chi phí
Đã có dữ liệu chưa dùng: phiên 10/10 (`tra-loi-toan-bo-2026-10-10.jsonl`, 110 câu, `qwen3:8b` trên Colab, top-10,
không rerank). Thời gian end-to-end mỗi câu: **trung bình 13,0 s, trung vị 12,0 s, p90 20,3 s, lớn nhất 62,7 s**.

Cần tách riêng và bổ sung:
- Thời gian **truy hồi** (đã có, khoảng 0,15 s/câu trên CPU) và thời gian **sinh** (bằng tổng trừ truy hồi, hoặc lấy
  `total_duration`/`eval_duration` từ Ollama).
- `prompt_eval_count` (token vào) và `eval_count` (token ra) cho mỗi câu, từ đó tính **token/giây**.
- Chi phí: Colab miễn phí (ghi loại GPU, ví dụ T4) hoặc compute unit; máy thuê ckey.vn thì lấy đơn giá/giờ × thời
  gian chạy 110 câu, quy ra **đồng/câu**. Ghi kèm một dòng so sánh khi bật `RAG_THINKING` (chậm khoảng 4 lần,
  cần số đo thật).

Bảng gợi ý (đặt ở 10.2.2):

| Cấu hình | Truy hồi (s) | Sinh trung vị / p90 (s) | Token vào / ra (TB) | Token/s | Chi phí / 100 câu |
|---|---|---|---|---|---|
| qwen3:8b, top-10, thinking=False | | | | | |
| qwen3:8b, top-10, thinking=True | | | | | |

### 8.3 Trích dẫn mới tới Điều, chưa có trang/khoản
- Thông tin trang **có sẵn ở tầng 1**: `extract_to_md.py` ghi `## Trang N (nguon…, diem…)`. Thông tin này
  **bị xóa** ở `clean_md.py` (bước "bỏ `## Trang N`").
- Giải pháp (đề xuất): `clean_md.py` thay `## Trang N` bằng chú thích ẩn `<!-- trang: N -->` thay vì xóa. Sau đó
  `processed_loader` ghi `trang_bat_dau`/`trang_ket_thuc` vào metadata và `node_label()` in "Điều 9, tr. 6–7".
- Khoản: hoặc small-to-big (Node con theo khoản, đã nêu ở 12.1), hoặc yêu cầu LLM nêu khoản và **kiểm** khoản đó
  có trong Node nguồn hay không. Hiện tại câu trả lời thường đã tự ghi "khoản 4 Điều 9" nhưng chưa ai kiểm.
- Trong báo cáo: ghi rõ yêu cầu "metadata tên file/trang/chương" mới **đạt một phần**. Có tên file, chương, Điều;
  chưa có trang. Ghi kèm kế hoạch ở trên.

### 8.4 Từ chối ngoài corpus chưa chứng minh "không bịa"
Bằng chứng mới từ phiên 10/10 (bộ `cau_hoi_danh_gia.json`):
- Có 3 câu "ngoài": 2 câu bị từ chối đúng. Câu thứ ba, **"IELTS 5.5 có được miễn học phần tiếng Anh không?"**,
  được hệ thống trả lời "được coi là đáp ứng điều kiện…" và dẫn Điều 3 QĐ 810 (điều kiện học ngành thứ hai). Đây là
  **bịa căn cứ**, đúng loại lỗi cần chứng minh là không xảy ra.
- Phiên 10/10 có 13/56 câu "không tìm thấy" (23%), so với 52% và 41% ở các phiên trước. Cả ba con số đều gộp từ chối
  đúng với từ chối sai.

Giải pháp:
1. Gán nhãn `pham_vi` (trong/ngoài) cho **toàn bộ 56 câu** của `cau-hoi01.md`, sau đó tách mỗi phiên thành ma trận
   2×2 (trong/ngoài × trả lời/từ chối). Báo cáo **tỷ lệ từ chối sai** (trong phạm vi mà bị từ chối) và **tỷ lệ bịa**
   (ngoài phạm vi mà vẫn trả lời).
2. Mở rộng bộ câu "ngoài" lên **ít nhất 20–30 câu**, chia ba loại:
   - hoàn toàn ngoài (học phí, ký túc xá);
   - **sát biên**: chủ đề có văn bản trong `data/raw` nhưng chưa nạp vào corpus (quy đổi chứng chỉ tiếng Anh, điểm
     rèn luyện, học bổng). Loại này dễ bịa nhất, như câu IELTS;
   - **câu bẫy**: hỏi về "Điều 45 Quy chế 2021" (không tồn tại) hoặc gắn số sai vào câu hỏi.
3. Viết lại kết luận 7.4 thành: *"tỷ lệ bịa trên N câu ngoài phạm vi là x/N"*, thay cho cách nói chung chung.

### 8.5 `/no_think` rò ra đầu ra
Đã kiểm:
- Trong repo, chuỗi `/no_think` chỉ xuất hiện ở `tests/test_llm.py` (kiểm rằng không có) và
  `eval/compare_results.py` (đếm như lỗi). Vậy chuỗi này **không đến từ prompt của nhóm**.
- Phiên 10/10 (110 câu): **0 lần** xuất hiện `/no_think` hay `<think>`. Lỗi ở phiên 08/10 chưa tái hiện lại được.

Giả thuyết (cần kiểm, chưa xác nhận): template chat của model Qwen3 trong Ollama, hoặc cách phiên bản Ollama trên
Colab xử lý `think=false`, đã chèn soft-switch `/no_think` vào lượt user, và mô hình lặp lại chuỗi đó khi không có
gì để trả lời. Cách tìm nguồn:
1. Ghi `ollama --version` của phiên 08/10 và của phiên 10/10. Nếu khác nhau thì đó là manh mối đầu tiên.
2. Chạy `ollama show qwen3:8b --template` (và `--modelfile`), tìm `no_think` hoặc `.Think`.
3. Gọi thẳng `/api/chat` với cùng prompt của câu "Bao nhiêu tiền 01 tín" theo ba cách: `think:false`, không truyền
   `think`, và tự thêm `/no_think` vào cuối. So các đầu ra.
4. Ghi kết quả vào Bảng 1.3 (cột Nguyên nhân). Lọc đầu ra chỉ là biện pháp **phòng thủ** và chỉ nên nêu sau cùng.

---

## Mục 9. Đánh giá thực nghiệm

| Vấn đề | Giải pháp |
|---|---|
| **Nguy cơ overfit**: bộ 01/02 do nhóm viết và đã dùng để chỉnh loader/prompt | Gọi bộ 01/02 là **tập phát triển (dev)**. Lập **tập kiểm chứng** khoảng 30–50 câu và *đóng băng* ở một commit trước khi xem kết quả. Người viết nên là thành viên không chỉnh pipeline; nguồn câu nên là câu hỏi thật trong `questions_log.jsonl` thu **sau** ngày đóng băng, cùng các cách diễn đạt khác của câu cũ. Báo cáo dev và test thành hai cột riêng. |
| **Luật "đúng" khác nhau**: bộ 01 nhận cả Node gốc lẫn Node sửa đổi QĐ 3183 (`dung_bo_01`), bộ 02 chỉ nhận Node QĐ 3183 (`dung_bo_02`) | Ghi luật chấm ngay trong chú thích Bảng 4.4 và 8.1. Không đặt R@1 81% cạnh 90% như hai số so sánh được. Nếu muốn so: thêm cột "bộ 01 – luật chặt" (chỉ Node gốc QC 2021) để thấy phần đóng góp của Node sửa đổi. |
| **nDCG@1 trùng R@1** | Với nhãn nhị phân, DCG@1 = rel₁ và IDCG@1 = 1, nên nDCG@1 ≡ R@1 về toán học. Bỏ cột này ở Bảng 8.1 và thay bằng **nDCG@3** (đã có ở Bảng 4.4) hoặc R@5. |
| **Đo ở mức Điều, không ở mức Node** | Hiện đã có trường hợp 2 Node cùng nhãn "Sửa đổi Điều 9". Cần (1) `id_` Node cố định (mục 8.1), (2) gán nhãn Node vàng, hoặc ít nhất khoản vàng, cho các câu bị ảnh hưởng, rồi báo cáo R@k mức Node bên cạnh mức Điều. Nếu chưa làm thì ghi rõ trong Hạn chế. |
| **1.3.2 LangChain "(Chưa làm)"** | Cách tối thiểu khả thi: dựng lại **chỉ phần truy hồi** bằng LangChain (cùng 54 Node, cùng `AITeamVN/Vietnamese_Embedding`, `InMemoryVectorStore`). So số dòng code, cách gắn và chọn metadata vào embedding (LangChain không có `excluded_embed_metadata_keys`), cách lưu chỉ mục, và R@k (phải bằng nhau nếu cài đúng). Nếu không kịp: đổi tiêu đề thành "So sánh theo tài liệu", trích tài liệu chính thức và ghi rõ là chưa dựng thử. |
| **2.2 "(Chưa làm)"** | Lấy số GitHub stars và contributors của `run-llama/llama_index`, số lượt tải PyPI của `llama-index-core` (pypistats), ghi **ngày truy cập**. Làm tương tự cho LangChain và Haystack để có số đối chiếu. |
| **Haystack chỉ một dòng ở 2.3** | Thêm một hàng vào bảng so sánh: mô hình pipeline/component, điểm mạnh (pipeline tìm kiếm, đánh giá), điểm yếu so với LlamaIndex ở tầng Node/metadata. Ghi rõ nhóm không dựng thử. |

---

## Mục 10. Phụ lục làm việc nhóm

### Kiểm chứng
- Bảng A.1 bản **.docx**: tuần 4 ghi "Huỳnh Thanh Tiến", tuần 5 ghi "Huỳnh Thanh Tiến, Phan Hữu Kha". Bản **LaTeX**
  cùng chỗ đó ghi `solozy`. Hai bản đã lệch nhau (xem mục 4).
- `git log` hiện tại: `solozy` 19 commit, `huynhthanhtien` 3, `phwkha` và "Phan Hữu Kha" 3 + 2, "Như Ý" 1,
  "Tran Ha Thanh Thuy" 1. Sau tuần 3 không còn commit nào của Võ Thị Như Ý hay Trần Hà Thanh Thùy.

### Giải pháp (cả nhóm phải tự điền, không suy ra hộ)
1. Ghi rõ tài khoản `solozy` là của thành viên nào. Cột "Người làm" phải là tên người, không phải tên tài khoản.
2. Thêm bảng **phân công theo thành viên × tuần**, kể cả việc không có commit: sửa tay OCR tầng 1, gán nhãn bộ câu
   hỏi, chấm tay 56 câu, viết chương báo cáo, làm slide/video, thử nghiệm Colab. Mỗi ô kèm **minh chứng**: commit,
   PR, file, hoặc mục báo cáo.
3. Nếu thành viên nào thực sự ít tham gia từ tuần 4 thì ghi trung thực. Không chép tên vào ô mình không làm.
4. Bật lại Phụ lục B (đang bị comment trong `main.tex`) khi có ảnh GitHub Insights.
5. **Phụ lục C (bản .docx gọi là B), "Điểm sâu nhất … chưa chốt"**: cần chọn một điểm *giải thích và sửa tại chỗ
   được trong vài phút*. Đề xuất:
   - **Hybrid + kiểm định**: đổi `fusion_mode` hoặc trọng số, chạy lại phần truy hồi không rerank (khoảng
     0,15 s/câu), đọc McNemar. Chứng minh được câu "tham số trộn quyết định nhiều hơn việc có BM25 hay không".
   - Phương án dự phòng: **chọn metadata vào embedding** (`nguon_trich` + `excluded_embed_metadata_keys`). In
     `MetadataMode.EMBED` trước và sau, rồi giải thích fingerprint tự build lại chỉ mục.

---

## Phụ lục: thứ tự làm đề xuất

1. **Ngay** (khoảng 1 buổi, chỉ sửa báo cáo): mục 4 (dọn aux, sửa 4 `\ref`, danh sách 1–6, "Bốn độ đo"); mục 6 (cây
   thư mục, 4 bảng); mục 5.3; chép phần sửa tay của .docx về LaTeX.
2. **Viết lại** (khoảng 1–2 buổi): mục 5.1 (giọng văn), 5.2 (lịch, sau khi có lịch chính thức), mục 7 (đưa bảng
   số đo ở trên vào 4.2.2 và Phụ lục D), mục 9 (chú thích luật chấm, bỏ nDCG@1).
3. **Cần chạy thêm** (dùng Colab, không đổi mã hệ thống): đo token và số lượt gọi (7c), độ trễ và token (8.2), tìm
   nguồn `/no_think` (8.5), A/B chú giải thang điểm (mục 2), gán nhãn `pham_vi` cho 56 câu (8.4).
4. **Cần sửa mã nguồn** (để nhóm quyết định, ghi trong 12.1 nếu chưa làm): refine prompt tiếng Việt, tokenizer
   thống nhất cho `MAX_TU`, `id_` Node cố định, giữ số trang qua `clean_md`, metadata khóa áp dụng, tập kiểm chứng
   đóng băng.
5. **Cả nhóm**: mục 10 (phân công, minh chứng), định hướng nghề nghiệp, AI Disclosure.
