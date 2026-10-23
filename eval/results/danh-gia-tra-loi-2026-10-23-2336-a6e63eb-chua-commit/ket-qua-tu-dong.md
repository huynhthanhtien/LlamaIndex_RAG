# Câu trả lời cấu hình chốt — 2026-10-23 23:53:07, commit `a6e63eb`, qwen3:8b

### Chỉ số tự động theo bộ (không gộp)

| Bộ | Số câu | Lỗi | Từ chối | Ngữ cảnh có đoạn đúng | Khớp số: đủ / thiếu / không (trên số câu có số) | Token vào / ra TB | Giây/câu (trung vị / p90) |
|---|---|---|---|---|---|---|---|
| Dev đợt 2 (tiếng Anh) | 15 | 0 | 0 | 15/15 (100%) | 11 / 1 / 2 (trên 14) | 3071 / 151 | 9.29 / 15.78 |
| Dev đợt 3 | 15 | 0 | 1 | 15/15 (100%) | 9 / 4 / 0 (trên 13) | 2469 / 157 | 10.11 / 15.99 |
| Dev đợt 4 | 69 | 0 | 0 | 69/69 (100%) | 25 / 5 / 2 (trên 32) | 2124 / 108 | 7.84 / 10.34 |

### Tách lỗi tạm tính bằng khớp số (59 câu có con số trong đáp án)

| | Khớp đủ số | Không đúng |
|---|---|---|
| **Ngữ cảnh có đoạn đúng** | 45 — hệ thống đúng | 14 — **lỗi LLM** |
| **Ngữ cảnh không có đoạn đúng** | 0 — đúng dù thiếu căn cứ | 0 — **lỗi truy hồi** |

> Khớp số chỉ là chỉ số phụ: đúng số chưa chắc đúng ý (vd đúng số nhưng sai khóa), và câu định tính không chấm được. Kết luận dùng bảng của người chấm ở mục 6.
