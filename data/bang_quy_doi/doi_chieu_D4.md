# D4. Đối chiếu bảng quy đổi với PDF gốc

Ngày đối chiếu: 17/10/2026. Nguồn: các PDF trong `data/raw/01_quy_che_dao_tao/2_quy_doi_tieng_anh/`, đối chiếu từng dòng với
CSV của D3 (`data/bang_quy_doi/*.csv`) và với bảng Markdown trong `data/processed/01_quy_che_dao_tao/2_quy_doi_tieng_anh/`.

**Kết quả: đã đối chiếu 300 dòng CSV, sửa 24 ô (12 dòng) trong `2366_TB_DHSG.csv`. Bảng Markdown khớp PDF, không phải sửa.**

| Văn bản | Trang PDF | Dòng CSV | Khớp PDF | Sửa |
|---|---|---|---|---|
| TB 2366/2021 | 1–2 | 45 | 33/45 | 12 dòng (24 ô), xem mục 1 |
| QyĐ 2101/2024 | 1–2 | 99 | 99/99 | — |
| TB 2451/2024 | 1–2 | 54 | 54/54 | — |
| QyĐ 2626/2022 | 3–4 | 84 | 84/84 | — |
| TB 2567/2024 | 1–2 | 18 | 18/18 | — |

Mọi mốc điểm trong CSV đều xuất hiện trong bảng Markdown tương ứng (kiểm bằng script). Bảng Markdown chép đúng cả ký hiệu
`=`, `<`, `≥` của PDF.

## 1. Đã sửa: TB 2366, hàng 2 (điểm 9) dùng bất đẳng thức chặt

PDF ghi: *"TOEIC 4 kỹ năng: 450 < Nghe và Đọc < 600; 105 < Nói < 140; 90 < Viết < 130"* và *"45 < TOEFL iBT < 61"*.
CSV cũ ghi `muc_tu=450, muc_den=600`…, trong khi mọi file khác dùng `muc_tu`/`muc_den` theo nghĩa "từ … đến …" (gồm cả hai đầu).
Vì vậy điểm 450 khớp cả hàng 1 (= 450 → 8) lẫn hàng 2 (→ 9), điểm 600 khớp cả hàng 2 lẫn hàng 3 (≥ 600 → 10).

Điểm các chứng chỉ này là số nguyên, nên "a < x < b" tương đương đúng với "a+1 … b−1":

| Chứng chỉ | Cũ | Mới |
|---|---|---|
| TOEIC Nghe Doc | 450–600 | 451–599 |
| TOEIC Noi | 105–140 | 106–139 |
| TOEIC Viet | 90–130 | 91–129 |
| TOEFL iBT | 45–61 | 46–60 |

(mỗi chứng chỉ 3 dòng: Tiếng Anh I, II, III)

## 2. Ghi nhận, không sửa (nhóm cần quyết định)

1. **Văn bản gốc tự chồng biên — QyĐ 2626:** Linguaskill hàng 1 "140 – 149", hàng 2 "149 – 158"; VSTEP hàng 1 "= 4.0", hàng 2
   "4.0 – 5.0". CSV chép đúng nguyên văn (front matter cũng đã ghi chú). Công cụ tra bảng (T5) phải có quy tắc cho trường hợp này,
   ví dụ trả cả hai mức và trích nguyên văn, không tự chọn.
2. **TOEIC 4 kỹ năng là điều kiện "và":** PDF yêu cầu đạt đồng thời Nghe-Đọc, Nói, Viết. CSV tách thành 3 dòng `TOEIC Nghe Doc`,
   `TOEIC Noi`, `TOEIC Viet` độc lập. Công cụ T5 phải tra cả ba và lấy mức **thấp nhất**, không được trả điểm theo riêng
   Nghe-Đọc.
3. **Khóa áp dụng của TB 2366 và TB 2451:** PDF 2451 ghi "các khóa tuyển sinh từ năm 2021 trở về trước" (không có cận dưới);
   PDF 2366 không nêu khóa. CSV và front matter (D1) ghi `ap_dung_khoa_tu=2020`. Nếu cận dưới 2020 không có căn cứ văn bản thì
   nên để trống `ap_dung_khoa_tu`. TB 2567 mục 1 thì ghi rõ "khóa 20 … và khóa 21", nên 2020 ở 2567 là đúng.
