"""Nội dung đầu vào của RAG: thư mục corpus và danh sách văn bản được nạp vào index.

Thêm / bớt văn bản chỉ cần sửa file này. Đổi danh sách thì index tự build lại
(fingerprint trong index_builder.py so sha256 và tên hiển thị từng file).
"""

PROCESSED_ROOT = "data/processed"

# Thư mục chứa file tầng 2 (sinh bởi scripts/clean_md.py), nằm dưới PROCESSED_ROOT; đọc cả thư mục con.
CORPUS_DIR = f"{PROCESSED_ROOT}/01_quy_che_dao_tao"

# Văn bản nạp vào index: tiền tố tên file trong CORPUS_DIR -> tên hiển thị (dùng khi embedding và trích nguồn).
# Mỗi tiền tố phải khớp đúng một file trong toàn bộ cây thư mục (tests/test_corpus.py kiểm tra).
# Chỉ các văn bản SGU đang áp dụng: đã đo, văn bản hết hiệu lực / của Bộ lấn át QC SGU 2021 khi truy hồi.
SGU_HIEU_LUC: dict[str, str] = {
    "25_quy-che-dao-tao": "Quy chế đào tạo trình độ đại học SGU 2021",
    "QD 3183.2025": "QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021",
    "8_QD810": "QĐ 810 về học cùng lúc hai chương trình",
    "2022-2375": "QĐ 2375/2022 về chuyển chương trình, ngành đào tạo",
    "22_quy-dinh-ve-khoi-luong": "Quy định khối lượng đào tạo hệ chính quy theo tín chỉ",
    "Quydinh150tc": "Quy định số tín chỉ tối thiểu kỹ sư CNTT (khóa 2017 trở đi)",
    # Đợt 1 (docs/ke_hoach_them_du_lieu_dao_tao.md §4): văn bản đánh số mục (F3) và QĐ ban hành + quy định (F2)
    "3260-QD-Hoan-thi": "QĐ 3260/2025 về việc hoãn thi",
    "QD898": "QĐ 898/2025 ban hành Quy định tổ chức thi học kì",
    "CV_3248": "Quy định 3248/2018 giải quyết thắc mắc, khiếu nại kết quả học tập",
    "QuyDinh_CapBangDiem": "Quy định cấp bảng điểm học tập (2018)",
    "QuyDinh_CapBanSao": "Quy định cấp bản sao văn bằng, chứng chỉ (2018)",
    "QĐ_CVHT": "Quy chế công tác cố vấn học tập (QĐ 367/2019)",
    # Đợt 2: quy đổi chứng chỉ tiếng Anh (bảng chép tay, F4) — đáp án khác nhau theo khóa tuyển sinh (F5),
    # nên tên hiển thị ghi rõ khóa áp dụng để vector và LLM phân biệt được
    "202111_2366": "TB 2366/2021 tiếng Anh không chuyên, quy đổi chứng chỉ (khóa tuyển sinh 2021 trở về trước)",
    "30_TB so 2451": "TB 2451/2024 bổ sung chứng chỉ quy đổi tiếng Anh (khóa tuyển sinh 2021 trở về trước)",
    "CV2626": "QyĐ 2626/2022 tiếng Anh không chuyên, quy đổi chứng chỉ (khóa tuyển sinh 2022, 2023)",
    "29_2101": "QyĐ 2101/2024 tiếng Anh không chuyên, quy đổi chứng chỉ (khóa tuyển sinh từ 2024)",
    "TB so 2567": "TB 2567/2024 bổ sung chứng chỉ PTE Academic quy đổi tiếng Anh (các khóa)",
    # Đợt 3: quy trình phúc khảo, tiết học và chuẩn đầu ra tốt nghiệp
    "HD-Quy trinh phuc khao": "HD 1181/2022 thực hiện quy trình phúc khảo bài thi kết thúc học phần",
    "02.-Tiethoc_phonghoc": "Quy định thời gian tiết học, ca học và mã phòng học",
    "TB_ChuanDauRa_2020": "TB 536/2020 áp dụng chuẩn đầu ra ngoại ngữ xét công nhận tốt nghiệp",
}
