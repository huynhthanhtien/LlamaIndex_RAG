# Phân tích lỗi sai phổ biến (17 văn bản, 108 Node)

Nguồn số liệu: 76 câu truy hồi (bộ 01: 31, bộ 02: 10, dev đợt 1: 20, dev đợt 2: 15; cấu hình vector) và 45 câu qua
LLM (dev đợt 1 chạy lại: 20, dev đợt 2: 15, `make test-llm`: 10). Log và câu trả lời gốc nằm cùng thư mục.

## 1. Lỗi truy hồi: 13/76 câu trượt top-1

| Loại | Số câu | Ví dụ | Nguyên nhân |
|---|---|---|---|
| **A1. Nhầm khóa tuyển sinh / phiên bản** | 6 (46%) | "khóa 2024, IELTS 4.5" → QyĐ 2626 (khóa 2022–23); "khóa 2020, VSTEP 4.0" → TB 2366 thay vì TB 2451; câu bộ 02 "thang điểm B+… áp dụng cho khóa nào" bị TB 2567 kéo ra **ngoài top-10** | Embedding không phân biệt con số năm; các văn bản cùng chủ đề chỉ khác khóa áp dụng |
| **A2. Văn bản chuyên đề "chiếm" câu hỏi của quy chế gốc** | 4 (31%) | "điều kiện chuyển ngành" → QĐ 2375; "điều kiện học chương trình thứ hai" → QĐ 810; "cảnh báo học tập liên hệ ai" → QC 2021 Điều 11 thay vì CV 3248 | Phần lớn là **nhãn đánh giá quá hẹp**: văn bản chuyên đề cũng là câu trả lời hợp lệ, nhưng luật chấm bộ 01 chỉ nhận QC 2021 |
| **A3. Điều lân cận / trùng từ khóa** | 3 (23%) | "vừa làm vừa học kéo dài bao nhiêu %" → Điều 4 thay vì Điều 2; "khối lượng tối thiểu/tối đa mỗi học kỳ" → Điều 6 thay vì Điều 7 | Các Điều cùng văn bản có từ vựng gần nhau; đều nằm ở hạng 2–3 nên LLM vẫn thấy |

R@3 của cả 4 bộ ≥ 90% nên phần lớn lỗi truy hồi **không làm mất ngữ cảnh**. Ngoại lệ nguy hiểm là A1, vì Node đúng
và Node sai cùng có mặt, và chính LLM phải chọn đúng khóa (xem B1).

## 2. Lỗi sinh câu trả lời: 11/45 câu sai hoặc thiếu (Node đúng thường đã có trong ngữ cảnh)

| Loại | Số câu | Ví dụ |
|---|---|---|
| **B1. Dùng sai phiên bản / sai khóa** | 4 | Rút học phần: trích Điều 7 gốc ("sau 02 tuần… không muộn quá 05 tuần") dù QĐ 3183 sửa đổi đứng top-1; PTE 50 điểm khóa 2021 trả 9 (đúng là 8, bảng khóa 2020–21); TOEFL ITP 500 khóa 2021 trích khoảng 476–498 của QyĐ 2626 (đúng số nhờ may mắn); APTIS B1 trích QyĐ 2101 (văn bản này không có dòng APTIS B1) |
| **B2. Suy luận / số học sai** | 2 | "Thi 90 phút, sau bao lâu được ra" → 90 phút (đúng: 2/3 = 60 phút; lần chạy trước trả đúng); "cảnh báo kỳ 1 và kỳ 3" coi là "hai lần liên tiếp" → buộc thôi học |
| **B3. Không từ chối / bịa khi chỉ có thông tin bề mặt** | 2 | "Điểm rèn luyện tính thế nào?" → câu trả lời mơ hồ dựa trên Quy chế CVHT; khiếu nại điểm quá trình: thêm bước "nộp đơn cho giảng viên", "bằng chứng hỗ trợ" không có trong văn bản |
| **B4. Trả lời thiếu ý** | 2 | Ai được xin bảng điểm: chỉ nêu người học, thiếu người đại diện/người thân (mục 2.2, 2.3); cảnh báo học tập liên hệ ai: chỉ nêu cố vấn học tập, thiếu văn phòng khoa |
| **B5. Lỗi đầu ra của mô hình** | 1 | Câu học phí: trả chuỗi `/ no_think` |

Ngoài ra **trích dẫn sai vị trí dù đáp án đúng** gặp ở 3 câu: lệ phí phúc khảo ghi "Điều 1" (đúng: Điều 5 QĐ 898);
"khoản 2 Điều 2" cho QĐ 3260 (văn bản không chia Điều); KSTAĐV ghi "Điều 3 khoản 3" (đúng: khoản 4).

### Hồi quy khi thêm dữ liệu

Có 3 câu đang đúng thì sai sau khi nạp thêm văn bản (buộc thôi học, điểm rèn luyện, thi 90 phút), trong khi truy hồi
top-3 không đổi. Nguyên nhân chung: `top_k=10`, không có ngưỡng điểm, không rerank → Node mới cùng chủ đề lọt vào
ngữ cảnh và làm LLM đổi kết luận. Corpus càng lớn thì loại lỗi này càng tăng.

## 3. Lỗi ở tầng dữ liệu (đã gặp khi nạp đợt 1–2)

| Loại | Ví dụ | Trạng thái |
|---|---|---|
| OCR hỏng số / mất cột trong bảng scan | Bảng quy đổi tiếng Anh mất hẳn cột điểm; "§" thay "8" | Đã chép tay 5 văn bản |
| OCR hỏng heading → mất cấu trúc Điều | Quy chế CVHT chỉ nhận 8/14 Điều ("Điều S", "l Điều 7") | Đã sửa tầng 1 |
| Phụ lục / mẫu đơn lẫn vào Node | QĐ 3260: 1 Node gồm cả 2 mẫu đơn (trang điểm OCR 0,79) | Chưa xử lý |
| Xung đột phiên bản trong corpus | Lệ phí phúc khảo: QĐ 898/2025 150.000đ ↔ CV 3248/2018 100.000đ; bảng QyĐ 2626 tự chồng lấn khoảng điểm | Chưa xử lý (cần xác minh) |
| Số hiệu / ngày không đọc được | Cấp bảng điểm "?124", cấp bản sao "?" | Ghi `?`, chưa xác minh |

## 4. Kết luận

1. **Lỗi số 1 xuyên suốt là phiên bản / khóa áp dụng**: 6/13 lỗi truy hồi + 4/11 lỗi LLM, cộng lỗi rút học phần có
   từ trước. Đây là lỗi F5 kế hoạch đã dự báo; càng nạp thêm văn bản theo khóa (đợt 3 xét tốt nghiệp, đợt 4 hệ khác)
   càng nặng. → Metadata `khoa_tu/khoa_den`, `thay_the` + lọc theo khóa + cho LLM thấy khóa áp dụng.
2. **Lỗi số 2 là nhiễu ngữ cảnh** (B2, B3 và 3 hồi quy): → ngưỡng `similarity_cutoff` hoặc rerank `top_n` 3–5, đo lại
   trên cả 4 bộ + `make test-llm`.
3. **Đánh giá đang đếm sai một phần**: A2 phần lớn là nhãn quá hẹp → cho bộ 01 nhận nhiều nhãn đúng (văn bản chuyên
   đề), tránh tối ưu nhầm hướng.
4. **Trích dẫn sai vị trí** cần một kiểm tra tự động (so số Điều trong câu trả lời với `dieu` của Node nguồn) vì
   chấm thủ công dễ bỏ qua khi đáp án đúng.
