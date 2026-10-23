# Rubric chấm câu trả lời sinh (eval/tra_loi_dev.py)

Nhận xét tuần 6, ý 4: lưu câu trả lời, evidence, **rubric**, số token/latency và **xử lý lỗi như một outcome**.
Mỗi câu trong file `eval/results/tra-loi-*.json` có trường `ket_qua`. Script ghi sẵn `loi` hoặc `chua_cham`; người chấm
sửa `chua_cham` thành một nhãn dưới đây, ghi lý do ngắn vào `ly_do`, rồi chạy

```bash
venv/bin/python eval/tra_loi_dev.py --tong-hop eval/results/tra-loi-<bo>-<cau-hinh>-<nhan>.json
```

để đếm lại `tom_tat.ket_qua`.

## Chấm hai mức (đang dùng cho dev, từ 24/10)

Nhóm chấm câu trong phạm vi bằng **hai nhãn** `dung` / `sai`:

- `dung`: kết luận trả lời đúng điều được hỏi và đủ ý chính. Trích sai số Điều/văn bản **không** làm câu thành `sai`,
  nhưng đánh dấu cột `trich_dan_sai = co` để thống kê riêng.
- `sai`: kết luận sai, thiếu ý chính, không trả lời đúng điều được hỏi, bịa thông tin hoặc từ chối khi đáp án có trong
  ngữ cảnh. Ghi loại lỗi vào `ly_do`.
- `loi` vẫn do script gán (không có câu trả lời), tính riêng.

Bảng nhiều mức dưới đây giữ để mô tả loại lỗi trong `ly_do`.

## Câu trong phạm vi (có `dieu_dung` / `dap_an`)

| Nhãn | Khi nào |
|---|---|
| `dung` | Kết luận khớp đáp án (đúng con số, đúng điều kiện, đủ ý chính) **và** căn cứ trích đúng văn bản/Điều có trong `bang_chung` |
| `mot_phan` | Kết luận đúng nhưng thiếu ý chính (thiếu bước, thiếu điều kiện), hoặc đúng nhưng trích sai Điều/văn bản |
| `sai` | Kết luận sai (sai số, sai phiên bản/khóa, sai thang điểm), kể cả khi trích dẫn đúng chỗ |
| `tu_choi_sai` | Trả lời "không tìm thấy" trong khi đáp án có trong `bang_chung` (lỗi sinh) hoặc trong corpus (lỗi truy hồi — ghi vào `ly_do`) |
| `bia` | Đưa thông tin không có trong `bang_chung` (con số, khóa, điều kiện tự đặt ra) |

## Câu ngoài phạm vi (`test_kiem_chung_ngoai.json`, có `hanh_vi_mong_doi`)

| Nhãn | Khi nào |
|---|---|
| `tu_choi_dung` | Nói không có thông tin trong các văn bản quy định, không bịa thêm (đúng `hanh_vi_mong_doi`) |
| `bia` | Trả lời như thể có căn cứ, hoặc chấp nhận tiền đề sai của câu bẫy |
| `mot_phan` | Từ chối nhưng kèm thông tin không có căn cứ, hoặc sửa tiền đề sai nhưng không nói rõ là không có trong văn bản |

## Do script gán

| Nhãn | Ý nghĩa |
|---|---|
| `loi` | Hết số lần thử (lỗi mạng, Ollama lỗi) mà không có câu trả lời. **Vẫn tính trong mẫu số**; không so hai cấu hình khi một bên còn câu `loi` — chạy bổ sung bằng `--chi-cau-loi` |
| `chua_cham` | Đã có câu trả lời, chưa chấm |

## Quy tắc chung

- Chấm theo văn bản gốc (`data/processed`, PDF), không theo trí nhớ. Câu nào đáp án phụ thuộc khóa tuyển sinh thì
  chỉ `dung` khi đúng phiên bản áp dụng cho khóa trong câu hỏi.
- Hai người chấm độc lập trên cùng file (sao file trước khi chấm), rồi đối chiếu các câu lệch nhãn.
- Không sửa prompt/cấu hình dựa trên kết quả chấm của tập kiểm chứng.
