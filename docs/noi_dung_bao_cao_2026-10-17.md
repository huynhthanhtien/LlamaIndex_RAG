# Nội dung đưa vào báo cáo (đo ngày 17/10/2026)

Báo cáo nay viết trên Google Docs; file này gom số liệu và đoạn văn đã kiểm chứng để dán vào đúng mục.
Mọi số đều có log trong `eval/results/logs/2026-10-17_chot-cau-hinh/`. Corpus: 20 văn bản, **118 Node**, profile `server`
(`AITeamVN/Vietnamese_Embedding`, reranker `AITeamVN/Vietnamese_Reranker`), chạy trên GPU RTX A2000 4 GB, fp16.

---

## C3 / R9. Cấu hình chốt và bảng truy hồi trên tập dev

**Cấu hình chốt** (= mặc định profile `server` trong `src/config.py`):

| Thành phần | Giá trị |
|---|---|
| Embedding | `AITeamVN/Vietnamese_Embedding`, chỉ embed trường `nguon_trich` + nội dung |
| Truy hồi | vector `similarity_top_k = 10` |
| Lọc phiên bản | bật (`src/phien_ban.py`: bỏ văn bản hết hiệu lực, lọc theo khóa, kéo kèm mục sửa đổi, đưa bản sửa đổi lên trước) |
| Rerank | `AITeamVN/Vietnamese_Reranker`, đọc **2 048 token**/cặp, giữ `top_n = 3` |
| Hybrid BM25 | tắt (xem C5) |

**Bảng R@1 trên 91 câu dev** (log `01_eval_truy_hoi.log`, tổng hợp `04_tong_hop.md`):

| Cấu hình | Bộ 01 (31) | Bộ 02 (10) | Dev đợt 1 (20) | Dev đợt 2 (15) | Dev đợt 3 (15) | **R@1 gộp** | R@3 gộp | MRR gộp | ms/câu |
|---|---|---|---|---|---|---|---|---|---|
| vector | 25 | 9 | 19 | 10 | 12 | **82,4%** | 95,6% | 0,893 | 47 |
| rerank | 27 | 5 | 18 | 14 | 12 | **83,5%** | 97,8% | 0,903 | 779 |
| lọc phiên bản | 25 | 9 | 18 | 11 | 14 | **84,6%** | 94,5% | 0,897 | 59 |
| **rerank + lọc (chốt)** | **27** | **7** | **20** | **15** | **14** | **91,2%** | **98,9%** | **0,947** | 887 |
| hybrid | 25 | 6 | 18 | 11 | 10 | 76,9% | 94,5% | 0,857 | 45 |
| hybrid + rerank | 27 | 5 | 18 | 14 | 12 | 83,5% | 97,8% | 0,903 | 854 |
| hybrid + rerank + lọc | 27 | 7 | 20 | 15 | 14 | 91,2% | 98,9% | 0,947 | 861 |

Kiểm định McNemar chính xác trên top-1 (91 câu):
- rerank → rerank + lọc: 0 câu chỉ rerank đúng, 7 câu chỉ rerank + lọc đúng, **p = 0,016**.
- vector → rerank + lọc: 3 so với 11, p = 0,057 (gần ngưỡng 0,05, chưa đủ để khẳng định).
- vector → rerank: 8 so với 9, p = 1,000. Rerank một mình **không** tốt hơn vector: tăng ở bộ 01 và dev đợt 2 nhưng tụt mạnh ở
  bộ 02 (9 → 5) vì đẩy Điều gốc lên trên mục sửa đổi. Lọc phiên bản bù đúng chỗ này.

Thời gian: rerank cộng khoảng 0,8 s/câu trên GPU 4 GB (trung vị), không đáng kể so với thời gian sinh câu trả lời.

**Chú thích luật chấm** (chép vào chú thích các bảng truy hồi, R9):
> Một câu được tính đúng ở hạng k nếu trong k Node đầu có Node khớp nhãn. Bộ 01 (QC 2021): Node phần chính của văn bản số hiệu
> 258/QĐ-ĐHSG có Điều thuộc nhãn, **hoặc** mục QĐ 3183 sửa đổi chính Điều đó. Bộ 02 (QĐ 3183): **chỉ** Node của QĐ 3183 (mục sửa
> đổi Điều thuộc nhãn hoặc Điều của chính QĐ). Bộ dev đợt 1–3: Node của văn bản ghi trong nhãn (và đúng Điều, nếu nhãn có Điều).
> Một câu có thể có nhiều nhãn cùng đúng. Vì luật chấm bộ 01 rộng hơn bộ 02, không so trực tiếp R@1 của hai bộ với nhau.

**Thay cột nDCG@1:** với nhãn nhị phân nDCG@1 trùng R@1 về toán học, nên bỏ cột này, dùng R@3 và MRR như bảng trên.

**Bộ 02 chưa đạt mục tiêu ≥ 80%** (đạt 7/10). Ba câu còn trượt top-1 đều là lỗi truy hồi thật, không phải lỗi nhãn:
- "Điểm B+ / D+ tương ứng khoảng điểm nào trên thang 10?" → top-1 là mục sửa đổi **Điều 10** (bảng quy đổi sang thang 4), trong
  khi khoảng thang 10 nằm ở mục sửa đổi **Điều 9** (đứng hạng 2–3).
- "Thang điểm chữ bổ sung áp dụng cho khóa nào?" → cần Điều 2 của QĐ 3183 (hiệu lực), hệ thống trả các mục sửa đổi Điều 9/10.

**Cột tập kiểm chứng (test):** để trống, điền sau khi đóng băng (K3) và chạy đúng một lần.

---

## C5. Hybrid BM25 cho tên chứng chỉ

Kết luận: **bỏ hybrid.** Giả thuyết là BM25 giúp các token hiếm (IELTS, TOEIC, VSTEP, số hiệu văn bản). Đo trên dev đợt 2 (15 câu
quy đổi tiếng Anh) thì hybrid chỉ tăng từ 10 lên 11 câu đúng top-1, nhưng làm tụt bộ 02 (9 → 6) và dev đợt 3 (12 → 10); gộp 91 câu
còn 76,9% so với 82,4% của vector. Khi đã có rerank, thêm hybrid không đổi kết quả câu nào (McNemar 0/0, p = 1,0) mà còn chậm hơn.
Lý do: trộn RRF với trọng số bằng nhau kéo các Node chứa nhiều tên chứng chỉ lên (bảng của văn bản khác khóa), còn reranker đọc
cả câu nên đã phân biệt được tên chứng chỉ mà không cần BM25.

---

## C2. Lọc phiên bản: một chỉnh sửa sau khi đo

Lần đo đầu (17/10, trước khi sửa), rerank + lọc làm dev đợt 2 tụt còn 12/15 và dev đợt 1 còn 18/20. Nguyên nhân: front matter
ghi TB 2567 (chỉ bổ sung chứng chỉ PTE) là `sua_doi` của TB 2366/2451, nên bước "đưa bản sửa đổi lên trước" đẩy 2567 lên top-1
cho cả câu hỏi về IELTS/VSTEP/TOEFL; tương tự QĐ 898 bị đẩy lên trên CV 3248 cho câu "khiếu nại điểm quá trình".

Sửa (`UuTienSuaDoi.du_lien_quan`): mục sửa đổi theo Điều (`sua_doi_dieu`) vẫn luôn được đưa lên vì biết chính xác phần bị sửa; quan
hệ sửa đổi **cả văn bản** chỉ được đưa lên khi điểm rerank của văn bản mới ≥ 0,5 lần văn bản cũ. Trên dev, các lần đưa lên đúng
(QĐ 898 Điều 5 về lệ phí/thời hạn phúc khảo) có tỉ lệ ≥ 0,92; các lần sai đều < 0,35. Sau khi sửa: dev đợt 2 15/15, dev đợt 1 20/20.

---

## R5. Vị thế của LlamaIndex (mục 2.2) — thay `\chualam`

Số liệu truy cập ngày **17/10/2026**, nguồn GitHub REST API (`api.github.com/repos/...`) và pypistats.org (`/api/packages/.../recent`):

| Dự án | GitHub stars | Forks | Contributors* | Repo tạo | Lượt tải PyPI 30 ngày | Gói PyPI |
|---|---|---|---|---|---|---|
| LlamaIndex (`run-llama/llama_index`) | 52 524 | 8 361 | ~2 007 | 11/2022 | 6 574 473 | `llama-index-core` (0.14.25) |
| LangChain (`langchain-ai/langchain`) | 147 936 | 24 833 | ~3 745 | 10/2022 | 144 826 657 | `langchain-core` |
| Haystack (`deepset-ai/haystack`) | 26 747 | 3 297 | ~508 | 11/2019 | 566 454 | `haystack-ai` |

\* Số contributors tính theo API GitHub, kể cả tài khoản ẩn danh (`anon=true`).

Đoạn văn gợi ý:
> Tính đến 17/10/2026, LlamaIndex có khoảng 52,5 nghìn sao và hơn 2 000 người đóng góp trên GitHub; gói lõi `llama-index-core`
> được tải khoảng 6,6 triệu lượt mỗi tháng trên PyPI. LangChain phổ biến hơn rõ rệt (khoảng 148 nghìn sao, 145 triệu lượt tải
> `langchain-core`/tháng, một phần do được kéo theo làm phụ thuộc của nhiều gói khác), còn Haystack nhỏ hơn (khoảng 26,7 nghìn sao,
> 0,57 triệu lượt tải `haystack-ai`/tháng). LlamaIndex vì vậy là framework RAG phổ biến thứ hai, với cộng đồng đủ lớn để tài liệu
> và ví dụ cập nhật liên tục.

Mục "tin tuyển dụng" trong `\chualam` cũ chưa thu thập; nếu không làm thì bỏ khỏi câu.

---

## R7. Chunk / embedding (mục 4.2.2)

Đo lại trên 118 Node hiện tại (log `02_do_dai_node.log`; số cũ 54 Node trong đề xuất đã lỗi thời):

| Độ dài mỗi Node (văn bản embed) | Trung bình | Trung vị | Lớn nhất |
|---|---|---|---|
| Ký tự | 1 352 | 1 108 | 4 641 (Điều 4 QĐ 898) |
| Từ (tách theo khoảng trắng) | 295 | 238 | 1 032 |
| Token tiktoken cl100k (mặc định của LlamaIndex) | 651 | 536 | 2 128 |
| Token `AITeamVN/Vietnamese_Embedding` / Reranker | 372 | 275 | 1 210 |
| Token `vietnamese-bi-encoder` | 379 | 285 | 1 213 |
| Token Qwen3-8B | 428 | 335 | 1 402 |

Các điểm cần sửa trong báo cáo:
1. **`MAX_TU` đếm theo từ, `SentenceSplitter` đếm theo token tiktoken.** Trung bình 2,21 token tiktoken/từ, nên khi một Điều vượt
   1 024 từ, splitter cắt thành đoạn khoảng 460 từ chứ không phải 1 024 từ. Trên corpus hiện tại splitter **đã chạy**: 19 Node mang
   `phan_doan`, cắt từ 5 Điều/văn bản dài (HD 1181, QĐ 898 Điều 3, TB 536, QyĐ 2626 Điều 3, QĐ 367 Điều 6). 23 Node vượt
   1 024 token tiktoken.
2. **Profile local cắt đuôi Node:** `vietnamese-bi-encoder` có `max_seq_length = 256`; **63/118 Node (53%)** dài hơn 256 token nên
   phần cuối không được embed. Mô hình này cũng yêu cầu tách từ (PyVi) mà repo không làm. Ghi rõ: kết quả profile local chỉ để
   tham khảo, không dùng để báo cáo chất lượng.
3. **Reranker trước đây cắt ở 512 token:** 35/118 Node (30%) dài hơn 512 token reranker; với 2 048 token thì không Node nào bị cắt
   (dài nhất 1 210). Đây là lý do kết luận cũ "rerank làm giảm R@1" không còn đúng.
4. **Số Node đưa vào LLM:** văn bản LLM nhận trung bình 738 token tiktoken/Node. 10 Node trung bình đã khoảng **7 381** token,
   sát hạn mức khoảng 7 400 của chế độ `compact` (`context_window` 8 192 − 256 − prompt), và 10 Node dài nhất lên tới 17 701. Vì
   vậy với top-10 không rerank, nhiều câu phải gọi LLM **2 lượt**, lượt sau dùng prompt refine mặc định tiếng Anh (không có ràng
   buộc "trích nguyên văn", "không tự quy đổi"). Với rerank top-3, trường hợp xấu nhất 3 Node dài nhất là 6 226 token → luôn một
   lượt. **Số lượt gọi thật** sẽ lấy từ `eval/tra_loi_dev.py` (cột `so_luot_llm`) khi chạy được với Ollama.

---

## R10. So sánh với LangChain (mục 1.3.2) — thay `\chualam`

Đã dựng lại **chỉ phần truy hồi vector** bằng LangChain (`eval/so_sanh_langchain.py`, `langchain-core` 1.6.12,
`InMemoryVectorStore`), trên cùng 118 Node, cùng mô hình embedding (fp16, chuẩn hóa L2), cùng top-10 và cùng luật chấm.
Log `03_so_sanh_langchain.log`.

| Tiêu chí | LlamaIndex | LangChain |
|---|---|---|
| R@1 / R@3 / R@10 trên 91 câu dev | 82,4% / 95,6% / 98,9% | **giống hệt**; 0/91 câu có hạng câu đúng khác nhau |
| Đơn vị dữ liệu | `TextNode` có metadata, quan hệ, `id_` | `Document` (nội dung + metadata dạng dict) |
| Chọn metadata đưa vào embedding / vào LLM | khai báo `excluded_embed_metadata_keys`, `excluded_llm_metadata_keys` trên Node | không có cơ chế tương đương; phải tự ghép chuỗi đem embed (`page_content`) |
| Mô hình embedding HuggingFace | `HuggingFaceEmbedding` có sẵn | `langchain-core` không có; phải viết lớp `Embeddings` (~10 dòng) hoặc cài thêm `langchain-huggingface` |
| Lưu chỉ mục | `storage_context.persist()` + `load_index_from_storage()` (docstore + vector) | `InMemoryVectorStore.dump()/load()` chỉ lưu vector + document; phát hiện corpus đổi phải tự làm |
| Số dòng phần truy hồi (không tính dòng trống/chú thích) | `get_retriever()` 26 dòng (gồm cả nhánh hybrid BM25); dựng index dùng `VectorStoreIndex(nodes)` có sẵn | `dung_kho_langchain()` + `tim_langchain()` 9 dòng, cộng lớp `Embeddings` tự viết 9 dòng; không có hybrid |

Đoạn văn gợi ý:
> Để so sánh thực tế, nhóm dựng lại riêng phần truy hồi vector bằng LangChain trên cùng 118 Node và cùng mô hình embedding. Hai
> cách cài cho kết quả trùng khớp hoàn toàn trên 91 câu dev (R@1 82,4%), xác nhận khác biệt giữa hai framework không nằm ở chất
> lượng truy hồi mà ở mức trừu tượng. LlamaIndex có sẵn khái niệm Node với cơ chế chọn metadata riêng cho embedding và cho LLM, và
> có cơ chế lưu, nạp chỉ mục; ở LangChain, nhóm phải tự ghép chuỗi đem đi embed và tự viết lớp bọc mô hình embedding. Với bài
> toán văn bản quy chế cần metadata phiên bản/hiệu lực đi kèm từng Node, cách tiếp cận của LlamaIndex phù hợp hơn.

---

## D4 và K3 (tóm tắt để đưa vào báo cáo / Phụ lục A)

- **D4:** đối chiếu 300 dòng CSV quy đổi tiếng Anh với PDF gốc, sửa 24 ô (bất đẳng thức chặt ở TB 2366). Chi tiết và 3 vấn đề cần
  nhóm quyết định: `data/bang_quy_doi/doi_chieu_D4.md`.
- **K3:** độ đồng thuận nhãn A–B trên 40 câu: trùng 40/40, **κ = 1,00**. Kiểm trùng với dev: 4 câu gần như cùng ý với câu dev, N3
  cần viết lại hoặc ghi lý do trước khi đóng băng. Chi tiết: `eval/results/do_dong_thuan.md`.

---

## Còn chờ Ollama (server)

- `eval/tra_loi_dev.py --cau-hinh cu,moi`: câu trả lời dev đợt 1–3 cho cấu hình cũ (top-10, không rerank) và cấu hình chốt, kèm
  token vào/ra, độ trễ, số lượt gọi LLM (R7 mục 4, R8, C3 phần chấm câu trả lời).
- `make test-llm`.
- Sau K3: chạy tập kiểm chứng đúng một lần, điền cột test.
