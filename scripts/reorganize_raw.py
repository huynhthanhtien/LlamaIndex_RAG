"""Tái cấu trúc data/raw theo mục 4 của docs/bao_cao_danh_gia_du_lieu_raw.md.

- Chỉ di chuyển/đổi tên bằng `git mv` (không xoá file nào, kể cả bản trùng nội dung).
- Sửa tên mojibake, thêm đuôi .pdf cho file mất đuôi, đặt tên có nghĩa cho file chỉ đánh số.
- Ghi data/raw/metadata_manifest.csv: đường dẫn mới <-> cũ, URL gốc, sha256, các bản trùng.

Mặc định chỉ in kế hoạch (dry-run). Thực hiện: python scripts/reorganize_raw.py --apply
"""
import argparse
import csv
import hashlib
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OLD_MANIFEST = "sgu_web/manifest.csv"

QC = "01_quy_che_dao_tao"
CTSV = "02_cong_tac_sinh_vien"
CTDT = "03_chuong_trinh_dao_tao"
KLTN = "04_khoa_luan_thuc_tap"
BM = "05_bieu_mau_thu_tuc"

# Nhóm con của 01 lấy theo cách bạn đã chia trong ~/Downloads/SGU_QuyChe_QuyDinh, thêm nhóm 6
QC1 = f"{QC}/1_quy_che_dao_tao_dai_hoc"
QC2 = f"{QC}/2_quy_doi_tieng_anh"
QC3 = f"{QC}/3_cong_tac_thi_ket_thuc_hoc_phan"
QC4 = f"{QC}/4_xet_tot_nghiep"
QC5 = f"{QC}/5_quy_dinh_hoc_vu_khac"
QC6 = f"{QC}/6_he_dao_tao_khac"

# Từng file (đường dẫn cũ đã sửa mojibake, tương đối data/raw) -> thư mục mới. Thư mục cũ ở RULES bên dưới.
FILES = {
    "4. QuyCheDaoTaoDHSG 2021.pdf": QC1,
    "QD 3183.2025 - Sua doi Quy che Dao tao trinh do DH_LienQuanRutMonHoc.pdf": QC1,
    # --- daotao/quy_che_quy_dinh: đúng như bản phân loại trong Downloads ---
    "sgu_web/daotao/quy_che_quy_dinh/2022-2375-QyD Chuyen Chuong Trinh Dao Tao DoiVoiSinhVenDHCQ.pdf": QC1,
    "sgu_web/daotao/quy_che_quy_dinh/1a. QuyDinhChuyenNganhDaoTao_Don.docx": QC1,
    "sgu_web/daotao/quy_che_quy_dinh/8_QD810QuyDinhVeHocCungLucHaiChuongTrinhDoiVoiSVDHCQ.pdf": QC1,
    "sgu_web/daotao/quy_che_quy_dinh/4. QuyCheDaoTaoDHSG 2021.pdf": QC1,
    "sgu_web/daotao/quy_che_quy_dinh/QuyCheDaoTao_2017.pdf": QC1,
    "sgu_web/daotao/quy_che_quy_dinh/QD 3183.2025 - Sua doi Quy che Dao tao trinh do DH_LienQuanRutMonHoc.pdf": QC1,
    "sgu_web/daotao/quy_che_quy_dinh/CV2626ToChucDayHocCacHPTAKoChuyenTheoChuongTrinhApDungMoiChoCacKhoaTSTuNam2022TroDi.pdf": QC2,
    "sgu_web/daotao/quy_che_quy_dinh/TB so 2567- Bo sung chung chi tieng Anh PTE Academic de xet quy doi diem cac HP TA khong chuyen.pdf": QC2,
    "sgu_web/daotao/quy_che_quy_dinh/30_TB so 2451 vv bo sung chung chi TA quy doi thanh diem hoc tap cac HP TA khong chuyen danh cho khoa 2021 tro ve truoc.pdf": QC2,
    "sgu_web/daotao/quy_che_quy_dinh/29_2101-Qui dinh vv to chuc day hoc cac HP tieng Anh khong chuyen ap dung cho cac khoa TS tu nam 2024 tro di.pdf": QC2,
    "sgu_web/daotao/quy_che_quy_dinh/202111_2366-TB-DHSG_ to chuc day hoc cac hoc phan tieng Anh khong chuyen ap dung tu nam hoc 2021 - 2022.pdf": QC2,
    "sgu_web/daotao/quy_che_quy_dinh/20251120143954840_HoanThi.pdf": QC3,
    "sgu_web/daotao/quy_che_quy_dinh/CV_3248_001_khieunai.pdf": QC3,
    "sgu_web/daotao/quy_che_quy_dinh/ChienLuoc_001.pdf": QC3,
    "sgu_web/daotao/quy_che_quy_dinh/HD-Quy trinh phuc khao bai thi ket thuc hoc phan.pdf": QC3,
    "sgu_web/daotao/quy_che_quy_dinh/Quy dinh ve cong tac to chuc thi hoc ki.pdf": QC3,
    "sgu_web/daotao/quy_che_quy_dinh/QD898BanHanhQuyDinhToChucThiHocKi.pdf": QC3,
    "sgu_web/daotao/quy_che_quy_dinh/CDR1.pdf": QC4,
    "sgu_web/daotao/quy_che_quy_dinh/CDR2.pdf": QC4,
    "sgu_web/daotao/quy_che_quy_dinh/TB_ChuanDauRa_2020.pdf": QC4,
    "sgu_web/daotao/quy_che_quy_dinh/QuyDinh_CapBangDiem.pdf": QC5,
    "sgu_web/daotao/quy_che_quy_dinh/CV2375ChuyenChuongTrinhDaoTaoDoiVoiSinhVenDHCQ.pdf": QC5,
    "sgu_web/daotao/quy_che_quy_dinh/QuyDinh_CapBanSao.pdf": QC5,
    # --- ctsv/van_ban_ctsv: tách theo nội dung (tiêu đề trong manifest) ---
    "sgu_web/ctsv/van_ban_ctsv/2.pdf": QC1,   # Quy chế 08/2021 của Bộ
    "sgu_web/ctsv/van_ban_ctsv/3.pdf": QC1,   # 17/VBHN-BGDĐT quy chế ĐH, CĐ 2014
    "sgu_web/ctsv/van_ban_ctsv/22.pdf": QC1,  # khối lượng đào tạo theo tín chỉ
    "sgu_web/ctsv/van_ban_ctsv/25.pdf": QC1,  # Quy chế ĐT ĐHSG 2021 (trùng)
    "sgu_web/ctsv/van_ban_ctsv/24.pdf": QC5,  # QĐ 736 thời gian học tối đa
    "sgu_web/ctsv/van_ban_ctsv/9.pdf": QC6,   # liên thông
    "sgu_web/ctsv/van_ban_ctsv/10.pdf": QC6,  # vừa làm vừa học
    "sgu_web/ctsv/van_ban_ctsv/11.pdf": f"{CTSV}/che_do_chinh_sach_hoc_bong",  # NĐ 238 học phí
    "sgu_web/ctsv/van_ban_ctsv/27.pdf": f"{CTSV}/che_do_chinh_sach_hoc_bong",  # học bổng tuyển sinh
    "sgu_web/ctsv/van_ban_ctsv/28.pdf": f"{CTSV}/che_do_chinh_sach_hoc_bong",
    "sgu_web/ctsv/van_ban_ctsv/26.pdf": f"{CTSV}/diem_ren_luyen",
    "sgu_web/ctsv/van_ban_ctsv/23.pdf": f"{KLTN}/quy_dinh_chung",  # quy định KLTN
    "sgu_web/ctsv/trang_chu/CAMNANGTSVSGU2022.pdf": f"{CTSV}/so_tay_sinh_vien",
    "sgu_web/ctsv/trang_chu/BienCheNamHoc_2026-2027.pdf": f"{CTDT}/bien_che_nam_hoc",
    # --- khoa CNTT ---
    "sgu_web/khoa_cntt/quy_che/2366-TB-ĐHSG_ tô chức dạy học các học phần tiếng Anh không chuyên áp dụng từ năm học 2021 - 2022 (1).pdf": QC2,
    "sgu_web/khoa_cntt/quy_che/QC_dao-tao-trinh-do-dai-hoc-he-chuan.pdf": QC1,
    "sgu_web/khoa_cntt/quy_che/Quydinh150tc.pdf": QC1,
    "sgu_web/khoa_cntt/quy_che/DHSG_quy-dinh-thoi-gian-toi-da-de-hoan-thanh-chuong-trinh-dai-hoc.pdf": QC5,
    "sgu_web/khoa_cntt/quy_che/QĐ_CVHT.pdf": QC5,
    "sgu_web/khoa_cntt/quy_che/QC_dao-tao-trinh-do-thac-si-1.pdf": QC6,
    "sgu_web/khoa_cntt/quy_che/QC_dao-tao-trinh-do-tien-si.pdf": QC6,
    "sgu_web/khoa_cntt/quy_che/QD_dao-tao-lien-thong.pdf": QC6,
    "sgu_web/khoa_cntt/diem_ren_luyen/DRL_Huong-dan-danh-gia-diem-ren-luyen.pdf": f"{CTSV}/diem_ren_luyen",
    "sgu_web/khoa_cntt/diem_ren_luyen/DRL_Quy-dinh-danh-gia-ket-qua-ren-luyen.pdf": f"{CTSV}/diem_ren_luyen",
    "sgu_web/khoa_cntt/diem_ren_luyen/DRL_Bieu-mau-danh-gia-diem-ren-luyen.doc": f"{BM}/theo_khoa/khoa_cntt",
    "sgu_web/khoa_cntt/diem_ren_luyen/DRL_Mau-bien-ban-hop-danh-gia-diem-ren-luyen-theo-hoc-ky.pdf": f"{BM}/theo_khoa/khoa_cntt",
    "sgu_web/khoa_cntt/khoa_luan/2022-11-15-2590-QĐ-ĐHSG-QĐ về việc ban hành QUy định quản lí, tổ chức hoạt động khóa luận tốt nghiệp đối với sinh v": f"{KLTN}/quy_dinh_chung",
    "sgu_web/khoa_cntt/khoa_luan/QD_DieuChinhKLTN_2025.pdf": f"{KLTN}/quy_dinh_chung",
    "sgu_web/khoa_cntt/khoa_luan/KLTN_Kehoachthuchien.pdf": f"{KLTN}/khoa_cntt",
    "sgu_web/khoa_cntt/khoa_luan/Danh-sach-khoa-luan-tot-nghiep-CNTT.xlsx": "_archive",
    "sgu_web/khoa_cntt/thuc_tap/TTTN_Kehoachthuctap.pdf": f"{KLTN}/khoa_cntt",
    # --- khoa QTKD ---
    "sgu_web/khoa_qtkd/quy_dinh/01.Quyche43.pdf": QC1,
    "sgu_web/khoa_qtkd/quy_dinh/05.-QD_trienkhaiTT57_daotaotinchi_DHSG_HK121.pdf": QC1,
    "sgu_web/khoa_qtkd/quy_dinh/02.-Tiethoc_phonghoc.pdf": QC5,
    "sgu_web/khoa_qtkd/quy_dinh/04.-QyD_736_thgiantoidahoctaitruong_CQ_2014.pdf": QC5,
    "sgu_web/khoa_qtkd/quy_dinh/03.-QyD_xetCNTN_2014.pdf": QC4,
    "sgu_web/khoa_qtkd/quy_dinh/06.-QuyDinhXetTN2017.pdf": QC4,
    "sgu_web/khoa_qtkd/quy_dinh/07.-Quy-dinh-dinh-danh-gia-diem-RL.pdf": f"{CTSV}/diem_ren_luyen",
    # --- khoa TCKT ---
    "sgu_web/khoa_tckt/sua_doi_quy_che/QD-3183.2025-Sua-doi-Quy-che-Dao-tao-trinh-do-DH.pdf": QC1,
    "sgu_web/khoa_tckt/hoan_thi/3260-QD-Hoan-thi-.pdf": QC3,
    # --- khoa Luật ---
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/HD-Quy trinh phuc khao bai thi ket thuc hoc phan.pdf": QC3,
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/QD2590-QuanliTochucKLTN.pdf": f"{KLTN}/quy_dinh_chung",
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/QD_DieuChinhKLTN_2025.pdf": f"{KLTN}/quy_dinh_chung",
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/01 De tai goi y cho sv lua chon.pdf": f"{KLTN}/khoa_luat",
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/KE HOACH KLTN_20252026.pdf": f"{KLTN}/khoa_luat",
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/KE HOACH_TTTN_APDUNG_20252026.pdf": f"{KLTN}/khoa_luat",
    "sgu_web/khoa_luat/bieu_mau_quy_dinh/Thong bao ve Quy dinh to chuc hoc phan Thuc te chuyen mon tu nam hoc 2022-2023.pdf": f"{KLTN}/khoa_luat",
    # --- khoa Ngoại ngữ ---
    "sgu_web/khoa_ngoai_ngu/quy_che/QD2590QuiDinh_KhoaLuanTN_2022.pdf": f"{KLTN}/quy_dinh_chung",
    "sgu_web/khoa_ngoai_ngu/quy_che/QD_DieuChinhKLTN_2025.pdf": f"{KLTN}/quy_dinh_chung",
    "sgu_web/khoa_ngoai_ngu/quy_che/Danh sách Hội đồng khóa luận 2025-2026_GuiSV.pdf": f"{KLTN}/khoa_ngoai_ngu",
    # --- khoa KHXH&NT ---
    "sgu_web/khoa_khxhnt/bieu_mau/ND116.2020_Ho-tro-HP-SVSP.pdf": f"{CTSV}/che_do_chinh_sach_hoc_bong",
    "sgu_web/khoa_khxhnt/bieu_mau/QUY-DINH-VE-DANH-GIA-KET-QUA-REN-LUYEN-SV-DHSG.pdf": f"{CTSV}/diem_ren_luyen",
    "sgu_web/khoa_khxhnt/bieu_mau/fileManager": "_archive",    # lỗi 404 "File not found"
    "sgu_web/khoa_khxhnt/bieu_mau/fileManager_1": "_archive",
}

# Thư mục cũ -> thư mục mới, cho các file không có trong FILES (khớp tiền tố dài nhất).
# Giá trị là hàm (path, manifest_row) -> thư mục, để phân loại theo đuôi file hoặc trang nguồn.
def _form_or(default: str, form_dir: str):
    return lambda p, _row: form_dir if p.suffix.lower() in {".doc", ".docx"} else default


def _ctdt_cycle(_p: Path, row: dict[str, str]) -> str:
    m = re.search(r"chu-k[iy]-(\d{4})-(\d{4})", row.get("trang", ""))
    return f"{CTDT}/chu_ky_{m[1]}_{m[2]}" if m else f"{CTDT}/khac"


RULES = {
    "sgu_web/daotao/chuong_trinh_dao_tao/": _ctdt_cycle,
    "sgu_web/daotao/bien_che_nam_hoc/": lambda *_: f"{CTDT}/bien_che_nam_hoc",
    "sgu_web/daotao/quy_trinh_bieu_mau/": lambda *_: f"{BM}/daotao",
    "sgu_web/ctsv/van_ban_ctsv/": lambda *_: f"{CTSV}/van_ban_quy_dinh",
    "sgu_web/ctsv/che_do_chinh_sach/": _form_or(f"{CTSV}/che_do_chinh_sach_hoc_bong", f"{BM}/ctsv"),
    "sgu_web/ctsv/diem_ren_luyen/": _form_or(f"{CTSV}/diem_ren_luyen", f"{BM}/ctsv"),
    "sgu_web/ctsv/thu_tuc/": _form_or(f"{CTSV}/quy_trinh_thu_tuc", f"{BM}/ctsv"),
    "sgu_web/ctsv/so_tay_sinh_vien/": lambda *_: f"{CTSV}/so_tay_sinh_vien",
    "sgu_web/ctsv/trang_chu/": lambda *_: f"{CTSV}/thong_bao",
    # Phần còn lại ở các khoa là biểu mẫu (doc/docx và PDF mẫu phụ lục)
    "sgu_web/khoa_cntt/": lambda *_: f"{BM}/theo_khoa/khoa_cntt",
    "sgu_web/khoa_qtkd/bieu_mau/": lambda *_: f"{BM}/theo_khoa/khoa_qtkd",
    "sgu_web/khoa_luat/": lambda *_: f"{BM}/theo_khoa/khoa_luat",
    "sgu_web/khoa_ngoai_ngu/": lambda *_: f"{BM}/theo_khoa/khoa_ngoai_ngu",
    "sgu_web/khoa_khxhnt/": lambda *_: f"{BM}/theo_khoa/khoa_khxhnt",
}


def slugify(text: str, max_len: int = 70) -> str:
    text = re.sub(r"^\s*(?:[\d.]+\s*|[>\-]\s*)", "", " ".join(text.split()))  # bỏ "5. ", "> ", "- "
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].rsplit("-", 1)[0] if len(text) > max_len else text


def fix_mojibake(name: str) -> str:
    try:
        name = name.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass  # tên đã là UTF-8 đúng
    return unicodedata.normalize("NFC", name)


def new_name(old: Path, row: dict[str, str]) -> str:
    name = fix_mojibake(old.name)
    if not Path(name).suffix and RAW.joinpath(old).read_bytes()[:4] == b"%PDF":
        name += ".pdf"
    stem, suffix = Path(name).stem, Path(name).suffix
    # File chỉ có số (25.pdf, 21-1.doc): thêm tiêu đề từ manifest cho dễ đọc, giữ số gốc để truy vết
    if re.fullmatch(r"\d+(-\d+)?", stem) and row.get("tieu_de", "").strip():
        name = f"{stem}_{slugify(row['tieu_de'])}{suffix}"
    return name


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def target_dir(old: str, row: dict[str, str]) -> str:
    fixed = "/".join(fix_mojibake(part) for part in old.split("/"))
    if fixed in FILES:
        return FILES[fixed]
    prefix = max((p for p in RULES if old.startswith(p)), key=len, default=None)
    if prefix is None:
        raise SystemExit(f"Chưa phân loại: {old!r}")
    return RULES[prefix](Path(old), row)


def build_plan() -> list[dict[str, Any]]:
    manifest = {r["file"]: r for r in csv.DictReader(open(RAW / OLD_MANIFEST, encoding="utf-8")) if r["file"]}
    tracked = subprocess.run(
        ["git", "ls-files", "-z", "data/raw"], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8", "surrogateescape").split("\0")
    priority = ("sgu_web/daotao/", "sgu_web/ctsv/", "sgu_web/khoa_")
    olds = sorted(
        (p.removeprefix("data/raw/") for p in tracked if p and not p.endswith(".gitkeep")),
        key=lambda o: (next((i + 1 for i, pre in enumerate(priority) if o.startswith(pre)), 0), o),
    )

    plan, taken = [], set()
    for old in olds:
        if old == OLD_MANIFEST:
            continue
        row = manifest.get(old.removeprefix("sgu_web/"), {})
        name = new_name(Path(old), row)
        new = f"{target_dir(old, row)}/{name}"
        if new in taken:  # trùng tên (thường là bản trùng nội dung): thêm nguồn vào tên
            src = old.split("/")[1] if old.startswith("sgu_web/") else "goc"
            new = f"{target_dir(old, row)}/{Path(name).stem}__{src}{Path(name).suffix}"
        assert new not in taken, new
        taken.add(new)
        plan.append({"old": old, "new": new, "row": row, "sha256": row.get("sha256") or sha256(RAW / old)})
    plan.append({"old": OLD_MANIFEST, "new": "manifest_crawl_goc.csv", "row": {}, "sha256": ""})
    return plan


def write_manifest(plan: list[dict[str, Any]]) -> None:
    by_hash = defaultdict(list)
    for p in plan:
        if p["sha256"]:
            by_hash[p["sha256"]].append(p["new"])
    cols = ["file", "nhom", "file_goc", "nguon", "tieu_de", "url", "trang", "bytes", "sha256", "trung_noi_dung_voi"]
    with open(RAW / "metadata_manifest.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for p in plan:
            if not p["sha256"]:
                continue
            r = p["row"]
            w.writerow({
                "file": p["new"],
                "nhom": p["new"].split("/")[0],
                "file_goc": p["old"],
                "nguon": r.get("nguon", "tai_tay"),
                "tieu_de": " ".join(r.get("tieu_de", "").split()),
                "url": r.get("url", ""),
                "trang": r.get("trang", ""),
                "bytes": (RAW / p["new"]).stat().st_size,
                "sha256": p["sha256"],
                "trung_noi_dung_voi": ";".join(x for x in by_hash[p["sha256"]] if x != p["new"]),
            })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="thực hiện git mv (mặc định chỉ in kế hoạch)")
    args = ap.parse_args()

    plan = build_plan()
    for p in plan:
        print(f"{p['old']}\n    -> {p['new']}")
    print(f"\n{len(plan)} file", file=sys.stderr)
    if not args.apply:
        return

    for p in plan:
        dst = RAW / p["new"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", str(RAW / p["old"]), str(dst)], cwd=ROOT, check=True)
    write_manifest(plan)
    for d in sorted((RAW / "sgu_web").glob("**/"), reverse=True):  # dọn thư mục cũ đã rỗng
        d.rmdir() if not any(d.iterdir()) else None
    print("Đã di chuyển xong, ghi data/raw/metadata_manifest.csv", file=sys.stderr)


if __name__ == "__main__":
    main()
