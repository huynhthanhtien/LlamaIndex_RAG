"""Chấm tự động câu trả lời sinh so với đáp án chuẩn — chỉ số rẻ, tất định, để đối chiếu với người chấm.

Nhận xét tuần 6 (ý 4): đánh giá phải dựa trên câu trả lời, evidence và rubric. Người chấm theo
docs/rubric-cham-tra-loi.md là chuẩn; các hàm dưới đây chỉ là chỉ số phụ, và chỉ được tin khi đồng thuận cao với
người chấm (Cohen κ trong eval/metrics.py):
  - khop_su_kien: các con số trong đáp án (số tín chỉ, ngày, %, mốc khóa, khoảng điểm) có xuất hiện trong câu trả lời
    không. Bỏ số chỉ là số hiệu văn bản/Điều/khoản ("Điều 9", "QĐ 810", "số 258/QĐ-ĐHSG") vì câu trả lời đúng không
    bắt buộc nhắc lại chúng.
  - la_tu_choi: câu trả lời có phải câu "không tìm thấy trong văn bản" không (cùng mẫu với eval/evaluate_answers.py).
Không dùng LLM làm giám khảo: model sinh câu trả lời tự chấm mình thì thiên lệch.
"""
import re

TU_CHOI = re.compile(r"không tìm thấy|không có thông tin|không đề cập|không nêu|không (được )?quy định trong", re.IGNORECASE)
# Số chỉ là số hiệu/vị trí trong văn bản, không phải nội dung trả lời
_SO_HIEU = re.compile(
    r"(?:Điều|khoản|điểm|Chương|Mục|QĐ|QyĐ|TB|CV|HD|Thông tư|Quyết định|Quy định|Thông báo|Mẫu|số)\s*(?:số\s*)?\d+[\w/.\-]*",
    re.IGNORECASE)
# Mã biểu mẫu/ký hiệu có chữ và số dính nhau qua dấu chấm: "ĐT.ChuyenNganh.01"
_MA = re.compile(r"\b[^\W\d]\w*\.[^\W\d][\w.]*\d+")
_SO = re.compile(r"\d+(?:[.,]\d+)?")


def chuan_hoa_so(s: str) -> str:
    """"08" -> "8", "4.0" / "4,0" -> "4", "7,8" -> "7.8": cùng một giá trị thì cùng một chuỗi."""
    s = s.replace(",", ".")
    nguyen, _, le = s.partition(".")
    nguyen = nguyen.lstrip("0") or "0"
    le = le.rstrip("0")
    return f"{nguyen}.{le}" if le else nguyen


def su_kien(van_ban: str) -> set[str]:
    """Các con số mang nội dung trong một đoạn văn (đã bỏ số hiệu văn bản/Điều/khoản)."""
    return {chuan_hoa_so(x) for x in _SO.findall(_SO_HIEU.sub(" ", _MA.sub(" ", van_ban)))}


def khop_su_kien(dap_an: str, tra_loi: str) -> str:
    """"du" | "thieu" | "khong" theo tỉ lệ con số của đáp án có trong câu trả lời; "khong_ap_dung" khi đáp án không
    có con số nào (câu hỏi định tính: phải để người chấm)."""
    can = su_kien(dap_an)
    if not can:
        return "khong_ap_dung"
    co = can & {chuan_hoa_so(x) for x in _SO.findall(tra_loi)}
    return "du" if co == can else ("thieu" if co else "khong")


def la_tu_choi(tra_loi: str) -> bool:
    return bool(TU_CHOI.search(tra_loi))
