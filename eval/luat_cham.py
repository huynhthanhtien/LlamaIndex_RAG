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
    nhiều nhãn đúng ngăn bởi ";" (cùng nội dung có ở nhiều văn bản, vd KSTAĐV trong TB 2366 và QyĐ 2626)."""
    m = n.node.metadata
    for nhan in d.split(";"):
        tien_to, _, dieu = nhan.partition("|")
        if str(m.get("file", "")).startswith(tien_to) and (not dieu or (m.get("phan") == "chinh" and m.get("dieu") == dieu)):
            return True
    return False


def chuan_hoa_nhan(nhan: str | list[str]) -> str:
    """`dieu_dung` dạng list (nhiều nhãn đúng) -> chuỗi "a;b" mà các hàm dung_bo_* đọc; chuỗi giữ nguyên."""
    return nhan if isinstance(nhan, str) else ";".join(x.strip() for x in nhan if x.strip())
