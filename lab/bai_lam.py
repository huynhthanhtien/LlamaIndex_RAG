"""File học viên tự viết: ba hàm của Bài tập 2, 3, 4 (xem lab/README.md).

Chưa viết xong thì chạy lab với `--dap-an` để dùng lời giải trong lab/dap_an.py. Không mở dap_an.py trước khi tự làm.
"""
from llama_index.core.schema import NodeWithScore, TextNode

# Các hàm có sẵn để dùng khi làm bài ("x as x": nhập sẵn cho học viên dù file khung chưa dùng tới)
from chung import DIEU as DIEU, cac_dieu as cac_dieu, gan_metadata as gan_metadata, khoa_trong_cau_hoi as khoa_trong_cau_hoi


def chia_theo_dieu(text: str, van_ban: str, chunk_size: int = 0) -> list[TextNode]:
    """BÀI TẬP 2: mỗi Điều (heading "### Điều N") hoặc mục sửa đổi (heading "#### ... Điều N") thành một Node.

    - Gắn metadata bằng `gan_metadata(node, van_ban, [so_dieu])`.
    - Bỏ các khối không thuộc Điều nào (tiêu đề văn bản, tên Chương).
    - Giữ dòng tiêu đề Điều trong nội dung Node (bỏ các dấu "#").
    - Mở rộng: chunk_size > 0 thì Điều dài hơn chunk_size token được cắt tiếp bằng SentenceSplitter, mọi đoạn giữ
      metadata của Điều.
    Gợi ý: re.split(r"(?m)^(?=#{1,4} )", text) tách ngay trước mỗi heading; số Điều lấy bằng chung.DIEU.
    """
    raise NotImplementedError("BÀI TẬP 2: viết chia_theo_dieu trong lab/bai_lam.py (hoặc chạy với --dap-an)")


def sap_xep_theo_phien_ban(nodes: list[NodeWithScore], cau_hoi: str) -> list[NodeWithScore]:
    """BÀI TẬP 3: sắp lại Node đã truy hồi theo hiệu lực của QĐ 3183/2025.

    Đọc Điều 2 của QĐ 3183 để biết mục sửa đổi nào áp dụng cho khóa nào. Khi câu hỏi nêu khóa (khoa_trong_cau_hoi):
      - mục sửa đổi ÁP DỤNG cho khóa đó đứng trước Điều gốc tương ứng của Quy chế 2021;
      - mục sửa đổi KHÔNG áp dụng cho khóa đó xuống cuối danh sách.
    Không bỏ Node nào: chỉ đổi thứ tự (Điều gốc vẫn là căn cứ cho khóa cũ).
    """
    raise NotImplementedError("BÀI TẬP 3: viết sap_xep_theo_phien_ban trong lab/bai_lam.py (hoặc chạy với --dap-an)")


def co_can_cu(nodes: list[NodeWithScore], nguong: float) -> bool:
    """BÀI TẬP 4: có đủ căn cứ để gọi LLM không. False thì hệ thống từ chối ngay, không sinh câu trả lời."""
    raise NotImplementedError("BÀI TẬP 4: viết co_can_cu trong lab/bai_lam.py (hoặc chạy với --dap-an)")
