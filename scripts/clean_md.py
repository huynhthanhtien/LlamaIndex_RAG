"""Làm sạch và dựng cấu trúc Markdown: data/ocr (tầng 1, thô) -> data/processed (tầng 2, sạch).

Tầng 1 là nơi duy nhất sửa tay; tầng 2 luôn được sinh lại từ tầng 1 nên chạy lại bao nhiêu lần cũng được.

1. Làm sạch: bỏ "## Trang N", số trang, khối quốc hiệu, khối "Nơi nhận"/chữ ký; nối các trang;
   nối dòng bị ngắt giữa câu; chuẩn hóa đầu khoản bị OCR đọc sai ("2," -> "2.").
2. Cấu trúc: tách Quyết định ban hành khỏi văn bản chính (số Điều bắt đầu lại từ 1),
   heading "# văn bản" / "## Chương" / "### Điều"; mục "Sửa đổi ... Điều X" của văn bản sửa đổi thành "####".
3. Kiểm tra (không tự sửa): số Điều không liên tục, khoảng số "từ a đến b" với a > b, trang điểm thấp/rỗng
   -> ghi vào _bao_cao_kiem_tra.md để người duyệt rồi sửa ở tầng 1.
4. Metadata văn bản: lấy từ <thư mục tầng 1>/_metadata_van_ban.csv (người điền; script chỉ tạo lần đầu,
   không ghi đè), báo cáo kèm các câu ứng viên (số hiệu, ngày, hiệu lực, phạm vi áp dụng) để điền.

File sinh từ .docx (mẫu đơn) không đưa vào tầng 2.

Cách dùng:
    python scripts/clean_md.py data/ocr/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc
"""
import argparse
import csv
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OCR = ROOT / "data" / "ocr"
PROCESSED = ROOT / "data" / "processed"

Page = dict[str, Any]  # {"trang": int, "nguon": str, "diem": float, "text": str}

META_FIELDS = ["file", "ten_van_ban", "loai", "so_hieu", "co_quan", "ngay_ban_hanh", "ap_dung", "tinh_trang", "bi_sua_doi_boi", "ghi_chu"]
TINH_TRANG = {"", "con_hieu_luc", "het_hieu_luc", "bi_sua_doi"}

PAGE_SPLIT = re.compile(r"^## Trang (\d+) \(nguon: (\w+), diem: ([\d.]+)\)\s*$", re.M)
DIEU = re.compile(r"^[-_•.\s]*[ĐÐD]i[eêèéẻẽẹềếểễệ]u\s+(\d+)\s*(?:[.:]|,(?=\s*[A-ZĐÀ-Ỹ]))\s*(.*)$")  # OCR: "Diều 5.", "Điều 13, Nghỉ ốm"
CHUONG = re.compile(r"^Ch[ưu]ơng\s+([IVXLC]+|\d+)\b[.:]?\s*(.*)$")
SUA_DOI = re.compile(r"^\d{1,2}\.\s*(S\w{1,2}a\s+đ\w{1,2}i|B\w\s+sung|Bãi\s+bỏ).*?Điều\s+(\d+)", re.I)

HEADER = re.compile(
    r"CỘNG\s+H[ÒO]A\s+X[ÃA]\s+H[ỘO]I|Độc\s+lập\s*[-—–]|Ủ?Y\s+BAN\s+NH[ÂẦA]N|BỘ\s+GIÁO\s+DỤC|"
    r"^\s*Số\s*:|^THÀNH\s+PH[ỐÓO]\s+H[ỒỔÔO]\s+CH[ÍI]\s+MINH\s*$|^TRƯỜNG\s+ĐẠI\s+HỌC\s+SÀI\s+GÒN\b|^[\W_]{3,}$"
)
SIGN = re.compile(r"^(KT\.?\s*)?(PHÓ\s+)?(HIỆU|BỘ|THỨ)\s+TR[ƯU][ỞỚỎƠO]NG\b|^\(?Đã\s+ký\)?$")
MARKER = re.compile(
    r"^([-_•.\s]*[ĐÐD]i[eêèéẻẽẹềếểễệ]u\s+\d+|Ch[ưu]ơng\s+|Mục\s+\d+|Phần\s+|\d{1,2}[.)]\s|[a-zđ]\)\s|[-–•+*]\s|[“\"]|[A-Z]\+?\s*:)"
)
RANGE = re.compile(r"từ\s+(\d+(?:[,.]\d+)?)\s+(?:đến|tới)\s+(?:cận\s+)?(\d+(?:[,.]\d+)?)")
CANDIDATE = re.compile(
    r"Số\s*:|ngày\s+\d{1,2}\s*(?:tháng|/)|có\s+hiệu\s+lực|áp\s+dụng\s+(?:đối\s+với|cho|từ)|"
    r"thay\s+thế|bãi\s+bỏ|sửa\s+đổi,?\s+bổ\s+sung|Ban\s+hành\s+kèm\s+theo",
    re.I,
)


def read_tier1(path: Path) -> tuple[dict[str, str], list[Page]]:
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in front.strip().splitlines() if ": " in line)
    parts = PAGE_SPLIT.split(body)
    pages = [
        {"trang": int(parts[i]), "nguon": parts[i + 1], "diem": float(parts[i + 2]), "text": parts[i + 3].strip()}
        for i in range(1, len(parts), 4)
    ]
    return meta, pages


def is_caps_title(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 6 and sum(c.isupper() for c in letters) / len(letters) > 0.85


def clean_page(text: str, stats: dict[str, int]) -> list[str]:
    lines = [l.strip() for l in text.splitlines()]
    nonblank = [i for i, l in enumerate(lines) if l]
    # Số trang in ở đầu/cuối trang
    for idx in (nonblank[:1] + nonblank[-1:]) if nonblank else []:
        if re.fullmatch(r"[-–]?\s*\d{1,3}\s*[-–]?", lines[idx]):
            lines[idx] = ""
            stats["so_trang"] += 1
    # Khối quốc hiệu: chỉ xét 10 dòng có chữ đầu tiên
    for idx in [i for i, l in enumerate(lines) if l][:10]:
        if HEADER.search(lines[idx]):
            lines[idx] = ""
            stats["quoc_hieu"] += 1
    # Khối "Nơi nhận" + chữ ký: bỏ từ "Nơi nhận" tới hết trang
    out: list[str] = []
    in_sign = False
    for line in lines:
        if re.match(r"^Nơi\s+nhận", line):
            in_sign = True
        elif in_sign and (DIEU.match(line) or CHUONG.match(line) or line.startswith("(Ban hành")
                          or (is_caps_title(line) and re.search(r"QUY\s+(CHẾ|ĐỊNH)", line))):
            in_sign = False  # văn bản kế tiếp bắt đầu ngay trên trang này
        if in_sign:
            stats["noi_nhan"] += bool(line)
            continue
        if line and len(line) < 45 and SIGN.match(line):
            stats["chu_ky"] += 1
            continue
        out.append(line)
    return out


def join_lines(lines: list[str], stats: dict[str, int]) -> list[str]:
    paras: list[str] = []
    blank_before = False
    for line in lines:
        if not line:
            blank_before = True
            continue
        line = re.sub(r"^([“\"]?)(\d{1,2}),\s+(?=[A-ZĐÀ-Ỹ])", r"\1\2. ", line)  # "2, Kế hoạch" -> "2. Kế hoạch"
        if paras:
            prev = paras[-1]
            starts_lower = line[0].islower()
            new_para = (
                (MARKER.match(line) and not starts_lower)
                or is_caps_title(line) or is_caps_title(prev)
                or (re.search(r"[.;:!?”\"]$", prev) and not starts_lower)
                or (blank_before and not starts_lower)
            )
            if not new_para:
                paras[-1] = f"{prev} {line}"
                stats["noi_dong"] += 1
                blank_before = False
                continue
        paras.append(line)
        blank_before = False
    return paras


def split_parts(paras: list[str]) -> list[list[str]]:
    """Tách khi số Điều bắt đầu lại từ 1 (Quyết định ban hành + văn bản chính trong cùng một file)."""
    parts: list[list[str]] = []
    current: list[str] = []
    last = 0
    for p in paras:
        m = DIEU.match(p)
        if m and int(m[1]) == 1 and last >= 1:
            # phần mở đầu của văn bản sau (tiêu đề in hoa ngay trước "Điều 1") đi theo văn bản sau
            head: list[str] = []
            while current and (is_caps_title(current[-1]) or CHUONG.match(current[-1]) or current[-1].startswith("(")):
                head.insert(0, current.pop())
            parts.append(current)
            current, last = head, 0
        if m:
            last = int(m[1])
        current.append(p)
    parts.append(current)
    return [p for p in parts if p]


def part_title(part: list[str], fallback: str) -> str:
    caps: list[str] = []
    for p in part[:15]:
        if DIEU.match(p) or CHUONG.match(p):
            break
        if is_caps_title(p) and not SIGN.match(p):
            caps.append(p)
        elif caps:
            break
    title = " ".join(caps)
    return title if re.search(r"QUY\s+(CHẾ|ĐỊNH)|QUY[EÉẾ]T\s+Đ[IỊ]NH|HƯỚNG\s+DẪN|THÔNG\s+TƯ|VĂN\s+BẢN", title) else fallback


def to_markdown(part: list[str], title: str) -> list[str]:
    md = [f"# {title}", ""]
    i = 0
    while i < len(part):
        p = part[i]
        if p in title and is_caps_title(p):  # dòng tiêu đề đã đưa lên heading
            i += 1
            continue
        if m := CHUONG.match(p):
            name = m[2]
            if not name and i + 1 < len(part) and is_caps_title(part[i + 1]):
                name, i = part[i + 1], i + 1
            md += [f"## Chương {m[1]}. {name}".rstrip(". "), ""]
        elif m := DIEU.match(p):
            md += [f"### Điều {m[1]}. {m[2]}".rstrip(), ""]
        elif m := SUA_DOI.match(p):
            md += [f"#### {p}", ""]
        else:
            md += [p, ""]
        i += 1
    return md


def check(meta: dict[str, str], pages: list[Page], parts: list[list[str]], text: str) -> list[str]:
    issues: list[str] = []
    for k, part in enumerate(parts, start=1):
        nums = [int(m[1]) for p in part if (m := DIEU.match(p))]
        if not nums:
            continue
        expected = list(range(1, max(nums) + 1))
        missing = sorted(set(expected) - set(nums))
        dup = sorted({n for n in nums if nums.count(n) > 1})
        jumps = [f"{a}->{b}" for a, b in zip(nums, nums[1:]) if b != a + 1]
        if missing or dup or jumps:
            issues.append(f"Phần {k}: Điều {nums[0]}..{nums[-1]} — thiếu {missing or '-'}, trùng {dup or '-'}, nhảy {jumps or '-'}")
    for m in RANGE.finditer(text):
        a, b = (float(x.replace(",", ".")) for x in m.groups())
        if a > b:
            ctx = text[max(0, m.start() - 50):m.end() + 10].replace("\n", " ")
            issues.append(f"Khoảng số giảm dần: «{ctx}»")
    for p in pages:
        if not p["text"]:
            issues.append(f"Trang {p['trang']} rỗng (kiểm tra có phải trang trắng)")
        elif p["diem"] < 0.9:
            issues.append(f"Trang {p['trang']} điểm thấp {p['diem']:.3f} (nguồn {p['nguon']})")
    return issues


def load_metadata(path: Path, names: list[str]) -> dict[str, dict[str, str]]:
    if not path.exists():
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=META_FIELDS)
            w.writeheader()
            for n in names:
                w.writerow({"file": n})
        print(f"Đã tạo {path.relative_to(ROOT)} — điền metadata rồi chạy lại")
    rows = {r["file"]: r for r in csv.DictReader(open(path, encoding="utf-8"))}
    for n in names:
        if n not in rows:
            print(f"CẢNH BÁO: {path.name} chưa có dòng cho {n}")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path, help="thư mục trong data/ocr")
    folder = ap.parse_args().folder.resolve()
    out_dir = PROCESSED / folder.relative_to(OCR)
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in folder.glob("*.md") if not p.name.startswith("_"))
    docs = [(p, *read_tier1(p)) for p in sources]
    keep = [(p, m, pg) for p, m, pg in docs if not m.get("file_goc", "").rstrip('"').lower().endswith(".docx")]
    skipped = [p.name for p, m, _ in docs if (p, m) not in [(k[0], k[1]) for k in keep]]
    metadata = load_metadata(folder / "_metadata_van_ban.csv", [p.name for p, _, _ in keep])

    report = ["# Báo cáo kiểm tra", "", f"Nguồn: `{folder.relative_to(ROOT)}`", ""]
    if skipped:
        report += ["Không đưa vào tầng 2 (mẫu đơn .docx): " + ", ".join(f"`{s}`" for s in skipped), ""]
    for path, meta, pages in keep:
        stats = dict.fromkeys(["so_trang", "quoc_hieu", "noi_nhan", "chu_ky", "noi_dong"], 0)
        lines = [l for p in pages for l in clean_page(p["text"], stats) + [""]]
        paras = join_lines(lines, stats)
        parts = split_parts(paras)
        doc_meta = metadata.get(path.name, {})

        tieu_de = meta.get("tieu_de", "").strip('"')
        fallback = path.stem if re.search(r"download|xem chi tiết|tải về|^$", tieu_de, re.I) else tieu_de
        md: list[str] = []
        for k, part in enumerate(parts):
            is_bh = len(parts) > 1 and k < len(parts) - 1 and max(
                (int(m[1]) for p in part if (m := DIEU.match(p))), default=0) <= 5
            title = "Quyết định ban hành" if is_bh else (doc_meta.get("ten_van_ban") or part_title(part, fallback))
            md += to_markdown(part, title)
        front = ["---"] + [f"{k}: {meta[k]}" for k in ("file_goc", "sha256", "url", "tieu_de", "trung_noi_dung_voi") if k in meta]
        front += [f"nguon_tang_1: \"{path.relative_to(ROOT)}\""]
        front += [f"{k}: \"{doc_meta.get(k, '')}\"" for k in META_FIELDS[1:]]
        front += [f"so_phan: {len(parts)}", "---", ""]
        (out_dir / path.name).write_text("\n".join(front + md).rstrip() + "\n", encoding="utf-8")

        text = "\n".join(paras)
        issues = check(meta, pages, parts, text)
        if doc_meta.get("tinh_trang", "") not in TINH_TRANG:
            issues.append(f"tinh_trang không hợp lệ: {doc_meta['tinh_trang']!r} (chỉ nhận {sorted(TINH_TRANG - {''})})")
        raw = "\n".join(p["text"] for p in pages)
        candidates = list(dict.fromkeys(l.strip() for l in raw.splitlines() if CANDIDATE.search(l)))[:12]

        n_dieu = [sum(1 for p in part if DIEU.match(p)) for part in parts]
        report += [
            f"## {path.name}", "",
            f"- Phần: {len(parts)} (số Điều mỗi phần: {n_dieu}); đoạn sau khi nối: {len(paras)}",
            f"- Đã bỏ: {stats['so_trang']} số trang, {stats['quoc_hieu']} dòng quốc hiệu, "
            f"{stats['noi_nhan']} dòng khối Nơi nhận, {stats['chu_ky']} dòng chữ ký; nối {stats['noi_dong']} dòng",
            f"- Metadata còn trống: {[k for k in META_FIELDS[1:] if not doc_meta.get(k)] or 'không'}",
        ]
        report += ["- **Cần kiểm tra:**"] + [f"  - {i}" for i in issues] if issues else ["- Không phát hiện bất thường"]
        report += ["- Câu ứng viên cho metadata (trích nguyên văn từ tầng 1):"] + [f"  - `{c[:160]}`" for c in candidates]
        report.append("")
        print(f"{path.name[:60]:60} phần={len(parts)} Điều={n_dieu} vấn đề={len(issues)}")

    (out_dir / "_bao_cao_kiem_tra.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Báo cáo: {(out_dir / '_bao_cao_kiem_tra.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
