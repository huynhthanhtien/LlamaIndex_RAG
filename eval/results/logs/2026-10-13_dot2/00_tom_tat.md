# Đợt 2 (quy đổi tiếng Anh) — tóm tắt kiểm thử, metadata và đề xuất

Ngày 13/10/2026. Corpus: `data/processed/01_quy_che_dao_tao` — **17 văn bản, 108 Node** (trước đợt 1: 6 văn bản/54 Node;
sau đợt 1: 12/92). Embedding `AITeamVN/Vietnamese_Embedding` (GPU local, fp16), LLM `qwen3:8b` (Ollama trên Colab),
`temperature=0`, `seed=42`, `top_k=10`, rerank tắt.

## Log trong thư mục này

| File | Nội dung | Kết quả |
|---|---|---|
| `01_make_test.log` | `make test` (offline) | 26 qua, 10 bỏ qua (test LLM) |
| `02_build_index.log` | build index | 108 Node, khớp loader |
| `03_eval_truy_hoi.log` | `eval/evaluate.py --cau-hinh vector,hybrid` → `eval/results/truy-hoi-dot2.{json,md}` | xem bảng dưới |
| `04_make_test_llm.log` | `make test-llm` | **6/10 qua** (4 fail, chi tiết dưới) |
| `05_tra_loi_dot2.log` | 15 câu dev đợt 2 qua LLM → `eval/results/tra-loi-dev-dot2.md` | 12 đúng · 2 đúng số, trích sai · 1 sai |
| `06_tra_loi_dot1_17vb.log` | 20 câu dev đợt 1 chạy lại trên 17 văn bản → `eval/results/tra-loi-dev-dot1-17vb.md` | 16 đúng · 3 một phần · 1 sai |
| `07_pyright.log` | Pyright strict cho các file Python đã sửa | 0 lỗi |

## Truy hồi (vector, R@1 / R@3)

| Bộ câu hỏi | 6 văn bản | 12 văn bản (đợt 1) | 17 văn bản (đợt 2) |
|---|---|---|---|
| test_questions_01 (QC 2021, 31 câu) | 80,6% / 100% | 80,6% / 100% | 80,6% / 100% |
| test_questions_02 (QĐ 3183, 10 câu) | 90% / 90% | 90% / 90% | 90% / 90% |
| dev đợt 1 (20 câu) | — | 95% / 95% | 95% / 95% |
| dev đợt 2 (15 câu) | — | — | **66,7% / 93,3%** |

5/15 câu đợt 2 trượt top-1 đều do **nhầm khóa tuyển sinh**: "khóa 2024" → top-1 là QyĐ 2626 (khóa 2022–2023);
"khóa 2020, VSTEP" → TB 2366 thay vì TB 2451. Tên hiển thị đã ghi khóa nhưng embedding không phân biệt con số năm.

## `make test-llm`: 4 fail

| Test | Trên 6 văn bản | Trên 17 văn bản | Nguyên nhân |
|---|---|---|---|
| `test_rut_hoc_phan` | fail | fail | Có sẵn: LLM trích bản gốc Điều 7 thay vì QĐ 3183 sửa đổi |
| `test_buoc_thoi_hoc_hai_lan_lien_tiep` | qua | fail | Hồi quy sinh câu trả lời: Node mới (CVHT Điều 6, QĐ 898) làm nhiễu ngữ cảnh |
| `test_tu_choi_diem_ren_luyen` | qua | fail | Hồi quy: Quy chế CVHT nhắc "đánh giá kết quả rèn luyện" → LLM bịa câu trả lời mơ hồ thay vì từ chối |
| `test_tu_choi_hoc_phi` | qua | fail | LLM trả chuỗi rác `/ no_think` (lỗi qwen3, có thể không ổn định) |

## Metadata: hiện trạng

1. **Chỉ một trường vào embedding**: `nguon_trich` (= tên hiển thị trong `src/corpus.py` + Điều). Mọi trường khác
   bị loại khỏi vector (`KHONG_EMBED`), nên thông tin khóa/hiệu lực chỉ tác động qua chuỗi tên hiển thị.
2. **Front matter → Node chỉ nhận 4 khóa**: `so_hieu`, `ngay_ban_hanh`, `tinh_trang`, `nhom`
   (`processed_loader.load_processed`). Các cột `ap_dung`, `bi_sua_doi_boi`, `ghi_chu` trong `_metadata_van_ban.csv`
   **không đi vào Node**, LLM không thấy, retriever không lọc được.
3. **Mức điền CSV không đều**:

   | Thư mục | Văn bản | ten_van_ban | so_hieu | tinh_trang | ap_dung |
   |---|---|---|---|---|---|
   | `1_quy_che_dao_tao_dai_hoc` (6 văn bản gốc) | 12 dòng | 0 | 0 | 0 | 0 |
   | `2_quy_doi_tieng_anh` | 5 | 5 | 5 | 5 | 5 |
   | `3_cong_tac_thi_ket_thuc_hoc_phan` | 3 | 2 | 3 | 2 | 1 |
   | `5_quy_dinh_hoc_vu_khac` | 3 | 3 | 1 | 0 | 0 |

4. **Chưa có dạng có cấu trúc cho khóa áp dụng**: `ap_dung` là chữ tự do ("Khóa tuyển sinh từ 2024 trở đi"), không
   lọc được bằng `MetadataFilters`.
5. **Quan hệ sửa đổi/thay thế** chỉ có ở dạng chữ (`bi_sua_doi_boi`, `ghi_chu`). Đã thấy 2 xung đột cần quan hệ này:
   lệ phí phúc khảo (QĐ 898/2025: 150.000đ ↔ CV 3248/2018: 100.000đ); QyĐ 2101 thay QyĐ 2626 cho khóa từ 2024.
6. **Bảng gốc có khoảng chồng lấn** (QyĐ 2626: Linguaskill 140–149 / 149–158; VSTEP = 4.0 / 4.0–5.0) — giữ nguyên văn,
   ghi ở `ghi_chu`.

## Đề xuất (theo thứ tự ưu tiên)

1. **Thêm cột có cấu trúc** vào `_metadata_van_ban.csv`: `khoa_tu`, `khoa_den` (năm tuyển sinh, rỗng = không giới hạn),
   `he_dao_tao`, `thay_the`, `bo_sung_cho` (trỏ tới tiền tố file văn bản khác). Loader đưa các cột này vào metadata Node
   (thêm vào danh sách khóa nhận ở `load_processed`), không đưa vào embedding.
2. **Lọc theo khóa khi câu hỏi nêu khóa**: tách "khóa 20xx"/"K2x" trong câu hỏi bằng regex, rồi bỏ các Node có
   `khoa_tu > K` hoặc `khoa_den < K` (postprocessor tự viết — `SimpleVectorStore` không hỗ trợ đủ `>=`/`<=`). Câu không
   nêu khóa: giữ nguyên, prompt yêu cầu trình bày theo từng nhóm khóa. Dự kiến sửa được 5/15 câu trượt top-1 và câu 6
   (PTE khóa 2021) ở bước LLM.
3. **Đưa khóa áp dụng vào ngữ cảnh LLM**: thêm `khoa_tu`/`khoa_den` (hoặc 1 dòng "Áp dụng: khóa …") vào metadata LLM
   thấy, để LLM không dùng bảng sai khóa (câu 6, 13 đợt 2).
4. **Điền metadata cho 6 văn bản gốc** (`1_quy_che_dao_tao_dai_hoc`): số hiệu, ngày, `tinh_trang`, `khoa_tu`. Hiện 0/12.
5. **Giảm nhiễu ngữ cảnh** (3 hồi quy sinh câu trả lời: buộc thôi học, điểm rèn luyện, câu 7 đợt 1): thử
   `similarity_cutoff` hoặc rerank với `top_n` 3–5 trên cả 4 bộ + `make test-llm`; giữ cấu hình nào không làm tụt R@1.
6. **Xử lý văn bản bị thay thế**: CV 3248 (lệ phí phúc khảo cũ) — xác minh rồi đặt `tinh_trang=bi_sua_doi` +
   `thay_the`, và loại khỏi ngữ cảnh khi đã có văn bản thay thế trong top-k.
7. **Prompt**: thêm chỉ dẫn "nếu trích đoạn chỉ nhắc chủ đề mà không nêu cách làm/con số thì nói không tìm thấy" để
   chống câu trả lời mơ hồ như điểm rèn luyện; và theo dõi lỗi `/ no_think` của qwen3.
