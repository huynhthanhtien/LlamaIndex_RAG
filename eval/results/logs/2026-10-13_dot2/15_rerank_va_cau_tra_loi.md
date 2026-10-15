# Rerank có ảnh hưởng tới chất lượng câu trả lời không?

So sánh trên cùng corpus 17 văn bản, cùng LLM `qwen3:8b` (temperature 0, seed 42), cùng prompt:
- **Không rerank**: vector top-10 → 10 Node vào ngữ cảnh (cấu hình mặc định hiện tại).
- **Rerank top_n=3**: vector top-10 → `AITeamVN/Vietnamese_Reranker` với `max_length=2048` (đã sửa lỗi 512) → 3 Node.

Chạy bằng wrapper ngoài repo (không sửa code): `scratchpad/chay_voi_rerank.py`. Lần chạy `top_n=5` hỏng vì runtime
Colab tắt giữa chừng (log `12_*rerank5`, `13_*rerank5`, `14_*rerank5` chỉ có lỗi kết nối — bỏ qua).

## Kết quả (chấm tay theo văn bản gốc)

| Bài | Không rerank | Rerank top_n=3 |
|---|---|---|
| `make test-llm` (10) | 6 qua | **9 qua** |
| Dev đợt 1 (20) | 16 đúng · 3 một phần · 1 sai | **20 đúng** |
| Dev đợt 2 (15) | **12 đúng** · 2 đúng số, trích sai · 1 sai | 10 đúng · 3 đúng số, trích sai · 2 sai |
| **Tổng 45** | 34 đúng (75,6%) · 6 sai hẳn | **39 đúng (86,7%) · 3 sai hẳn** |
| Thời gian / câu (trung vị) | ~20 s | ~10 s |

## Thay đổi từng câu

Rerank **sửa được** (8 câu):
- `make test-llm` — buộc thôi học (cảnh báo kỳ 1 và 3: "không"), từ chối điểm rèn luyện, từ chối học phí
  (hết lỗi `/ no_think`). Đây đúng là 3 hồi quy do nhiễu ngữ cảnh khi nạp đợt 1–2.
- Đợt 1 — thi 90 phút: nêu đúng quy tắc "sau 2/3 thời gian" (trước: "90 phút", sai); khiếu nại điểm quá trình: trích
  nguyên văn, hết bịa bước; ai được xin bảng điểm và giấy tờ xin bản sao: đủ cả người đại diện/người thân (trước thiếu);
  cảnh báo học tập liên hệ ai: đủ "văn phòng khoa và cố vấn học tập".
- Đợt 2 — APTIS B1 khóa 2022: trích đúng QyĐ 2626 (trước trích QyĐ 2101, văn bản không có dòng này).

Rerank **làm hỏng** (1 câu) và **không sửa** được:
- Đợt 2 câu 2 — TOEIC 520/110/110 khóa 2022: trả **8** (đúng 9). Bảng đúng có trong ngữ cảnh nhưng LLM đọc nhầm hàng 1
  (450–500). Lỗi đọc bảng; ít Node hơn không giúp được.
- Đợt 2 câu 6 — PTE 50 khóa 2021: vẫn sai (9, đúng 8) và lập luận lạc sang thang điểm hệ 4 (Node QC 2021 Điều 10 lọt
  vào 3 Node). Lỗi chọn sai bảng theo khóa vẫn còn.
- `test_rut_hoc_phan`: vẫn trích Điều 7 gốc thay vì QĐ 3183 sửa đổi (lỗi phiên bản có từ trước).
- Trích sai văn bản dù đáp án đúng tăng ở đợt 2 (câu 4, 5, 13: ghi QyĐ 2626 cho khóa 2020/2021/PTE) — với 3 Node,
  bảng của khóa khác vẫn chen vào và LLM ghi nhầm nguồn.

## Kết luận

1. **Có, rerank (đã sửa max_length) cải thiện rõ chất lượng câu trả lời**: +5 câu đúng / 45, số câu sai hẳn giảm một
   nửa, và nhanh gấp đôi vì ngữ cảnh ngắn hơn. Lợi ích chủ yếu đến từ **giảm nhiễu ngữ cảnh** (10 → 3 Node), đúng loại
   lỗi gây 3 hồi quy khi nạp thêm văn bản.
2. **Rerank không giải quyết lỗi phiên bản / khóa** — loại lỗi phổ biến nhất. Các lỗi còn lại ở đợt 2 và câu rút học
   phần đều thuộc loại này → vẫn cần metadata `khoa_tu/khoa_den`, `thay_the` và lọc trước khi rerank.
3. Mẫu nhỏ (45 câu, một lần chạy, chấm tay); chưa đo `top_n=5`. Nên chạy lại khi có Colab.

## Đề xuất

1. Sửa lỗi `max_length=512` trong `src/retriever.py` và `src/model_server.py` (tham số `reranker_max_length=2048`).
2. Bật rerank `top_n=3` làm cấu hình mặc định của query engine **sau khi** thêm lọc phiên bản (bỏ Node
   `bi_sua_doi`/`het_hieu_luc`/bị `thay_the` trước rerank) — để tránh rerank xếp văn bản cũ lên đầu (phúc khảo, rút học
   phần).
3. Đo thêm `top_n=5` và chạy lại `make eval` + `make test-llm` sau khi sửa để chốt cấu hình.
