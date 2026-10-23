"""Luật chấm truy hồi: Node nào là đúng cho nhãn `dieu_dung` của từng bộ câu hỏi (xem docstring eval/evaluate.py).

Tách khỏi eval/evaluate.py để kiểm thử offline chỉ cần llama-index-core (evaluate.py kéo theo index_builder -> torch).
"""
from collections.abc import Callable

from llama_index.core.schema import NodeWithScore

ChamDung = Callable[[NodeWithScore, str], bool]


# Bộ 01/02 chấm theo cặp (số hiệu văn bản, Điều) lấy từ front matter, không theo tên file
QC_2021 = "258"  # 258/QĐ-ĐHSG — Quy chế đào tạo trình độ đại học SGU 2021
QD_3183 = "3183"  # 3183/QĐ-ĐHSG — sửa đổi QC 2021


def so_vb(m: dict[str, object]) -> str:
    """Số văn bản của Node: "3183/QĐ-ĐHSG" -> "3183" ("" nếu Node không có so_hieu)."""
    return str(m.get("so_hieu", "")).split("/")[0].strip()


def cac_dieu(nhan: str) -> list[str]:
    """Nhãn bộ 01/02: "9", "9;10" (nhiều Điều cùng đúng) hoặc "2 (QĐ 3183)" -> ["9"], ["9", "10"], ["2"]."""
    return [x.split()[0] for x in nhan.split(";") if x.strip()]


def dung_bo_01(n: NodeWithScore, d: str) -> bool:
    """Bộ 01 hỏi về QC SGU 2021: đúng là Điều đó (phần chính) hoặc mục QĐ 3183 sửa đổi chính Điều đó."""
    m = n.node.metadata
    ds = cac_dieu(d)
    goc = so_vb(m) == QC_2021 and m.get("phan") == "chinh" and m.get("dieu") in ds
    sua_doi = so_vb(m) == QD_3183 and m.get("sua_doi_dieu") in ds
    return bool(goc or sua_doi)


def dung_bo_02(n: NodeWithScore, d: str) -> bool:
    """Bộ 02 hỏi về nội dung sửa đổi: đúng là mục QĐ 3183 sửa đổi Điều đó; nhãn "2 (QĐ 3183)" là Điều 2 của QĐ."""
    m = n.node.metadata
    if so_vb(m) != QD_3183:
        return False
    ds = cac_dieu(d)
    return bool(m.get("sua_doi_dieu") in ds or (m.get("phan") == "chinh" and m.get("dieu") in ds))


def dung_bo_dev(n: NodeWithScore, d: str) -> bool:
    """Bộ dev theo đợt: nhãn "<tiền tố file>" (văn bản 1 Node) hoặc "<tiền tố file>|<Điều>" (Điều của phần chính);
    "<tiền tố>|bh:<Điều>" là Điều của quyết định ban hành (vd QC 2021 "áp dụng từ khóa 2021"), "<tiền tố>|sd:<Điều>" là mục
    sửa đổi Điều đó — để nhắm đúng một Node thay vì nhãn cả văn bản (nhãn cả văn bản làm độ bao phủ và R@k bị thổi phồng).
    Nhiều nhãn đúng ngăn bởi ";" (cùng nội dung có ở nhiều văn bản, vd KSTAĐV trong TB 2366 và QyĐ 2626)."""
    m = n.node.metadata
    for nhan in d.split(";"):
        tien_to, _, dieu = nhan.partition("|")
        if not str(m.get("file", "")).startswith(tien_to):
            continue
        if not dieu:
            return True
        loai, _, so = dieu.rpartition(":")
        if loai == "sd":
            if m.get("phan") == "sua_doi" and m.get("sua_doi_dieu") == so:
                return True
        elif m.get("phan") == ("ban_hanh" if loai == "bh" else "chinh") and m.get("dieu") == so:
            return True
    return False


def chuan_hoa_nhan(nhan: str | list[str]) -> str:
    """`dieu_dung` dạng list (nhiều nhãn đúng) -> chuỗi "a;b" mà các hàm dung_bo_* đọc; chuỗi giữ nguyên."""
    return nhan if isinstance(nhan, str) else ";".join(x.strip() for x in nhan if x.strip())


# Tập phát triển (dev): đã dùng để chỉnh loader, prompt và chọn cấu hình -> chỉ số có thể lạc quan.
BO_CAU_HOI: list[tuple[str, ChamDung]] = [
    ("test_questions_01.json", dung_bo_01),
    ("test_questions_02.json", dung_bo_02),
    ("dev_questions_dot1.json", dung_bo_dev),
    ("dev_questions_dot2.json", dung_bo_dev),
    ("dev_questions_dot3.json", dung_bo_dev),
    # Đợt 4 (23/10): phủ các văn bản/Điều chưa có câu hỏi và câu phụ thuộc khóa; do AI soạn, có trường cong_cu_tao
    ("dev_questions_dot4.json", dung_bo_dev),
]

# Tập kiểm chứng (test): chưa dùng để chỉnh, chỉ chạy một lần sau khi đóng băng (eval/dong_bang.py,
# evaluate.py --tap-kiem-chung). Chỉ phủ QC 2021 và QĐ 3183, nên không đại diện cho cả corpus (eval/bao_phu.py).
BO_KIEM_CHUNG: list[tuple[str, ChamDung]] = [
    ("test_kiem_chung_qc2021.json", dung_bo_01),
    ("test_kiem_chung_3183.json", dung_bo_02),
]
# Câu ngoài phạm vi của tập kiểm chứng: không có nhãn Node, chấm bằng hành vi (từ chối) ở eval/tra_loi_dev.py
BO_NGOAI_PHAM_VI = "test_kiem_chung_ngoai.json"
