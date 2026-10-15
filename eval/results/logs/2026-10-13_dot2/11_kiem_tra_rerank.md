# Kiểm tra lại rerank (`AITeamVN/Vietnamese_Reranker`)

Log: `09_eval_rerank.log` (model server Colab, max_length mặc định 512) và `10_eval_rerank_maxlen2048.log`
(GPU local, max_length 2048). Kết quả: `eval/results/truy-hoi-rerank-dot2.{json,md}`,
`eval/results/truy-hoi-rerank2048-dot2.{json,md}`. `rerank-top10` = rerank giữ cả 10 Node để đo R@10.

## R@1 (vector top-10 → rerank)

| Bộ câu hỏi | vector | rerank (512) | hybrid+rerank (512) | **rerank (2048)** |
|---|---|---|---|---|
| test_questions_01 (31) | 80,6% | 80,6% | 83,9% | **87,1%** |
| test_questions_02 (10, QĐ 3183) | **90,0%** | 60,0% | 60,0% | 50,0% |
| dev đợt 1 (20) | **95,0%** | 80,0% | 80,0% | 90,0% |
| dev đợt 2 (15, tiếng Anh) | 66,7% | 73,3% | 80,0% | **93,3%** |
| **Tổng 76 câu** | 63 (82,9%) | 58 (76,3%) | 60 (78,9%) | **64 (84,2%)** |
| Thời gian / câu | ~13 ms | ~1,2 s (qua tunnel) | ~1,2 s | ~0,6 s (GPU local) |

McNemar từng bộ: không cặp nào có ý nghĩa thống kê (p ≥ 0,125). Bộ câu hỏi còn nhỏ.

## Phát hiện

1. **Lỗi cấu hình: reranker chỉ đọc 512 token đầu.** `SentenceTransformerRerank` của LlamaIndex đặt cứng
   `max_length=512` (`DEFAULT_SENTENCE_TRANSFORMER_MAX_LENGTH`), trong khi model hỗ trợ 8192. 30/108 Node (28%) dài hơn
   512 token (trung vị 266, lớn nhất 1212), đúng các Node bảng và Điều dài: TB 2366 1145, TB 2567 875, QyĐ 2101 Điều 2
   902, QĐ 898 Điều 7 1188. Phần bị cắt chứa đúng dòng cần tìm (vd bảng PTE khóa từ 2022 ở nửa sau TB 2567), nên điểm
   rerank bão hòa 0.00 / 1.00 và thứ hạng gần như ngẫu nhiên. Đây là lý do kết luận cũ "rerank làm giảm Recall@1".
   Cả `src/retriever.py` (local) và `src/model_server.py` (Colab) đều dính lỗi này.
2. **Sửa max_length thì rerank tốt nhất tổng thể** (+1 câu so với vector), nhất là bảng quy đổi theo khóa
   (đợt 2: 10 → 14/15; nhầm khóa ở top-1 còn 1 câu).
3. **Nhưng rerank khuếch đại lỗi phiên bản**: nó chấm theo độ khớp nội dung nên ưu tiên bản gốc / văn bản cũ khi nội
   dung giống nhau:
   - "Khi nào được chính thức bỏ lớp học phần sau khi xin rút?" → QC 2021 Điều 7 **gốc** (0.97) trên QĐ 3183 sửa đổi
     (0.84);
   - "Lệ phí phúc khảo?" → CV 3248/2018 (100.000đ) và QĐ 898/2025 (150.000đ) cùng 1.00, văn bản cũ đứng trước.
   Bộ 02 (hỏi đúng nội dung sửa đổi) vì vậy tụt 90% → 50%. Một phần còn do nhãn bộ 02 chỉ chấp nhận đúng một Điều
   (vd B+ thang 10: nhãn Điều 9, rerank chọn mục sửa đổi Điều 10 cũng có bảng này).
4. `reranker_top_n=3` (mặc định) làm R@5/R@10 = R@3; với ngữ cảnh LLM thì đây lại là ưu điểm (ít nhiễu) — chưa đo
   ảnh hưởng tới câu trả lời.

## Đề xuất

1. **Sửa lỗi 512 token**: thêm `reranker_max_length` vào `RAGConfig` (2048 đủ cho Node dài nhất hiện tại + câu hỏi),
   truyền vào `SentenceTransformerRerank` ở `make_local_reranker` và `load_reranker` trong `model_server.py`
   (đặt `rerank._model.max_length`). Ghi giá trị này vào `mo_ta()`.
2. **Chưa bật rerank mặc định** cho tới khi có lọc phiên bản: loại Node có `tinh_trang=bi_sua_doi`/`het_hieu_luc`
   (hoặc văn bản bị `thay_the`) **trước** khi rerank, rồi đo lại cả 4 bộ. Kỳ vọng giữ được +4 câu ở đợt 2 mà không mất
   4 câu ở bộ 02.
3. Đo ảnh hưởng tới câu trả lời: `make test-llm` + 2 bộ dev với rerank (2048, `top_n` 3–5) — có thể sửa luôn các hồi
   quy do nhiễu ngữ cảnh (buộc thôi học, điểm rèn luyện).
4. Cho bộ 02 nhận nhiều nhãn đúng (mục sửa đổi Điều 9 hoặc Điều 10 đều chứa bảng thang điểm) để không phạt nhầm.
