# Câu kiểm chứng gần trùng câu dev

So 60 câu kiểm chứng với 229 câu dev. Ngưỡng: chữ ≥ 0.75; hoặc cùng Node và (chữ ≥ 0.5). Chưa so theo nghĩa (chạy lại với --embedding).

**15 câu kiểm chứng** có ít nhất một cặp bị báo (19 cặp).

| Câu kiểm chứng | Câu dev | Chữ | Cùng Node | Nghĩa | Lý do |
|---|---|---|---|---|---|
| KC-3183-003: Ký hiệu điểm chữ nào dùng để đánh dấu học phần do sinh viên tự xin rút? | test_questions_02.json#9: Ký hiệu điểm chữ nào dùng cho học phần được miễn học và công nhận tín chỉ? | 0.64 | có | — | cùng Node, chữ gần giống |
| KC-3183-004: Điểm chữ B+ được quy đổi tương ứng bằng mấy điểm trong hệ thống thang điểm 4? | test_questions_02.json#6: Điểm C+ được quy đổi thành bao nhiêu điểm số trên thang điểm 4? | 0.69 | có | — | cùng Node, chữ gần giống |
| KC-3183-004: Điểm chữ B+ được quy đổi tương ứng bằng mấy điểm trong hệ thống thang điểm 4? | test_questions_01.json#15: Điểm chữ A quy đổi thành bao nhiêu điểm số để tính trung bình? | 0.51 | có | — | cùng Node, chữ gần giống |
| KC-3183-005: Các quy định về thang điểm chữ phân mức mới như B+, C+, D+ áp dụng bắt đầu từ khóa sinh viên năm nào? | test_questions_02.json#10: Thang điểm chữ bổ sung (B+, C+, D+) và quy đổi điểm mới áp dụng cho khóa tuyển sinh nào? | 0.51 | có | — | cùng Node, chữ gần giống |
| KC-3183-007: Điểm chữ C+ được quy đổi tương ứng với mấy điểm trong thang điểm 4 theo quy định mới? | test_questions_02.json#6: Điểm C+ được quy đổi thành bao nhiêu điểm số trên thang điểm 4? | 0.65 | có | — | cùng Node, chữ gần giống |
| KC-3183-007: Điểm chữ C+ được quy đổi tương ứng với mấy điểm trong thang điểm 4 theo quy định mới? | test_questions_01.json#15: Điểm chữ A quy đổi thành bao nhiêu điểm số để tính trung bình? | 0.50 | có | — | cùng Node, chữ gần giống |
| KC-3183-008: Điểm chữ chưa hoàn thiện do được phép hoãn thi theo quy định sửa đổi được ký hiệu bằng chữ gì? | test_questions_02.json#8: Điểm chưa hoàn thiện do được phép hoãn thi, kiểm tra được ghi nhận bằng điểm chữ nào? | 0.72 | có | — | cùng Node, chữ gần giống |
| KC-QC-001: Thời gian tối đa để học xong toàn khóa là bao nhiêu năm vậy ạ? | test_questions_01.json#2: Thời gian tối đa để hoàn thành khóa học là bao lâu? | 0.68 | có | — | cùng Node, chữ gần giống |
| KC-QC-004: Trường cho phép học trực tuyến tối đa bao nhiêu phần trăm tổng số tín chỉ của chương trình? | test_questions_01.json#10: Sinh viên được phép học trực tuyến tối đa bao nhiêu phần trăm chương trình? | 0.76 | có | — | gần nguyên văn |
| KC-QC-006: Nhà trường xét công nhận và chuyển đổi tín chỉ cũ tối đa bao nhiêu phần trăm chương trình? | test_questions_01.json#20: Tín chỉ được công nhận chuyển đổi tối đa bao nhiêu phần trăm chương trình? | 0.80 | không | — | gần nguyên văn |
| KC-QC-007: Một năm học chính quy bắt buộc phải có tối thiểu bao nhiêu tuần lên lớp? | test_questions_02.json#3: Một năm học theo quy định sửa đổi có thể tổ chức bao nhiêu học kỳ chính? | 0.58 | có | — | cùng Node, chữ gần giống |
| KC-QC-007: Một năm học chính quy bắt buộc phải có tối thiểu bao nhiêu tuần lên lớp? | test_questions_01.json#6: Một năm học có bao nhiêu học kỳ? | 0.51 | có | — | cùng Node, chữ gần giống |
| KC-QC-021: Học kỳ đầu năm nhất mà điểm trung bình của em dưới 0.8 thì có bị cảnh báo học tập không? | test_questions_01.json#18: Điểm trung bình học kỳ dưới bao nhiêu thì bị cảnh báo học tập? | 0.66 | có | — | cùng Node, chữ gần giống |
| KC-QC-024: Thi lại điểm thành phần để cải thiện điểm rớt thì điểm học phần tối đa chỉ được tính ở mức nào? | test_questions_01.json#14: Học cải thiện điểm thì điểm chính thức được tính như thế nào? | 0.61 | có | — | cùng Node, chữ gần giống |
| KC-QC-025: Sinh viên được phép hoãn thi có lý do chính đáng thì trên bảng điểm ghi nhận ký hiệu chữ gì? | test_questions_01.json#13: Vắng thi không có lý do chính đáng thì bị điểm bao nhiêu? | 0.57 | có | — | cùng Node, chữ gần giống |
| KC-QC-025: Sinh viên được phép hoãn thi có lý do chính đáng thì trên bảng điểm ghi nhận ký hiệu chữ gì? | test_questions_02.json#8: Điểm chưa hoàn thiện do được phép hoãn thi, kiểm tra được ghi nhận bằng điểm chữ nào? | 0.53 | có | — | cùng Node, chữ gần giống |
| KC-QC-028: Điểm trung bình tích lũy hệ 4 đạt từ 3,2 đến dưới 3,6 được xếp loại học lực gì? | test_questions_01.json#16: Điểm trung bình bao nhiêu thì được xếp loại Giỏi? | 0.56 | có | — | cùng Node, chữ gần giống |
| KC-QC-031: Sinh viên năm hai học theo tín chỉ bị buộc thôi học nếu điểm trung bình tích lũy dưới mức bao nhiêu? | test_questions_01.json#19: Sinh viên bị buộc thôi học trong những trường hợp nào? | 0.50 | có | — | cùng Node, chữ gần giống |
| KC-QC-032: Hình thức đánh giá bảo vệ đồ án trực tuyến cần tối thiểu bao nhiêu thành viên trong hội đồng chuyên môn? | test_questions_01.json#11: Mỗi học phần được đánh giá qua tối thiểu bao nhiêu điểm thành phần? | 0.51 | có | — | cùng Node, chữ gần giống |
