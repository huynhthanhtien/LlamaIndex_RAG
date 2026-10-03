"""Nội dung đầu vào của RAG: thư mục corpus và danh sách văn bản được nạp vào index.

Thêm / bớt văn bản chỉ cần sửa file này. Đổi danh sách thì index tự build lại
(fingerprint trong index_builder.py so sha256 và tên hiển thị từng file).
"""

PROCESSED_ROOT = "data/processed"

# Thư mục chứa file tầng 2 (sinh bởi scripts/clean_md.py), nằm dưới PROCESSED_ROOT.
CORPUS_DIR = f"{PROCESSED_ROOT}/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc"

# Văn bản nạp vào index: tiền tố tên file trong CORPUS_DIR -> tên hiển thị (dùng khi embedding và trích nguồn).
# Chỉ các văn bản SGU đang áp dụng: đã đo, văn bản hết hiệu lực / của Bộ lấn át QC SGU 2021 khi truy hồi.
SGU_HIEU_LUC: dict[str, str] = {
    "25_quy-che-dao-tao": "Quy chế đào tạo trình độ đại học SGU 2021",
    "QD 3183.2025": "QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021",
    "8_QD810": "QĐ 810 về học cùng lúc hai chương trình",
    "2022-2375": "QĐ 2375/2022 về chuyển chương trình, ngành đào tạo",
    "22_quy-dinh-ve-khoi-luong": "Quy định khối lượng đào tạo hệ chính quy theo tín chỉ",
    "Quydinh150tc": "Quy định số tín chỉ tối thiểu kỹ sư CNTT (khóa 2017 trở đi)",
}
