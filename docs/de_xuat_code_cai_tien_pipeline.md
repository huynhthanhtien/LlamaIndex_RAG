# Đề xuất mã nguồn cải tiến pipeline dữ liệu → RAG

> **Ngày:** 2026-10-05 · Bổ sung cho [`phan_loai_tai_lieu_va_huong_giai_quyet.md`](phan_loai_tai_lieu_va_huong_giai_quyet.md)
>
> ⚠️ **Toàn bộ mã trong tài liệu này là ĐỀ XUẤT. Không file mã nguồn nào đã bị sửa.**
> Mỗi đề xuất ghi rõ: file đích · mới/sửa · chỗ chèn (theo số dòng hiện tại) · cách kiểm thử · rủi ro.
> Áp dụng theo thứ tự ở [Mục 12](#12-thứ-tự-áp-dụng).

## 0. Bảng tổng hợp đề xuất

| # | File đích | Loại | Phụ thuộc | Kiểm thử | Ưu tiên |
|---|---|---|---|---|---|
| ĐX-1 | `scripts/dedupe_raw.py` | **mới** | `metadata_manifest.csv` | `--dry-run` (mặc định) | P0 |
| ĐX-2 | `scripts/convert_doc.py` + sửa `scripts/extract_to_md.py` | **không làm** (xem quyết định ở ĐX-6) | LibreOffice | — | ~~P2~~ |
| ĐX-3 | `scripts/clean_md.py` thêm `--kieu` | sửa | — | `tests/test_clean_md_kieu.py` | P1 |
| ĐX-4 | `src/processed_loader.py` thêm `muc`/`duong_dan_muc` | sửa | ĐX-3 | `tests/test_processed_loader.py` | P1 |
| ĐX-5 | `configs/corpus_sgu.yaml` + `src/corpus.py` | mới + sửa | `PyYAML` (đã có) | `tests/test_corpus_manifest.py` | P1 |
| ĐX-6 | `scripts/build_catalog_bieu_mau.py` + `src/policy.py` | **mới** | ĐX-5 | `tests/test_policy_bieu_mau.py` | **P1** |
| ĐX-7 | `src/router.py` + `index_builder.py` đa index | mới + sửa | ĐX-5 | đo lại `make eval` | P3 |
| ĐX-8 | `eval/evaluate.py` nhãn theo `(nguồn, Điều/mục)` | sửa | ĐX-4 | giữ nguyên số của bộ 01/02 | P1 |
| ĐX-9 | `tests/…` cho 4 module trên | **mới** | ĐX-1..8 | `make test` | P1 |

---

## 1. ĐX-1 — `scripts/dedupe_raw.py` (mới)

**Vì sao:** `metadata_manifest.csv` đã có `sha256`: 12 nhóm trùng, **18 tệp dư**. Hiện `extract_to_md.py` chỉ bỏ qua bản trùng *trong cùng một lần chạy* (`done_hashes`, dòng 162–171), nên chạy từng thư mục vẫn sinh ra `.md` trùng và làm nhiễu top-k.

**Nguyên tắc an toàn:** mặc định chỉ in đề xuất; chỉ **di chuyển** (không xóa) khi có `--apply`.

```python
"""Dọn tệp trùng nội dung trong data/raw theo sha256 của metadata_manifest.csv.

Mặc định CHỈ IN đề xuất. Khi có --apply thì DI CHUYỂN tệp dư vào
data/raw/_duplicates/<đường dẫn gốc> (không xóa) và ghi lại cột `giu_lai` trong manifest.

Cách dùng:
    python scripts/dedupe_raw.py                     # xem đề xuất
    python scripts/dedupe_raw.py --apply             # di chuyển 18 tệp dư
    python scripts/dedupe_raw.py --apply --keep "01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc/25_quy-che-dao-tao-trinh-do-dai-hoc-tai-truong-dai-hoc-sai-gon.pdf"
"""
import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "metadata_manifest.csv"
DUP_DIR = RAW / "_duplicates"

# Tiền tố đang được src/corpus.py dùng -> ưu tiên giữ đúng bản đó
try:
    sys.path.insert(0, str(ROOT / "src"))
    from corpus import SGU_HIEU_LUC  # type: ignore

    UU_TIEN = list(SGU_HIEU_LUC)
except Exception:  # corpus.py đổi cấu trúc thì vẫn chạy được
    UU_TIEN = []


def diem_uu_tien(rel: str) -> tuple:
    """Nhỏ hơn = nên giữ. (1) khớp tiền tố đang dùng, (2) không có hậu tố nguồn, (3) tên ngắn, (4) A→Z."""
    ten = Path(rel).name
    khop = next((i for i, t in enumerate(UU_TIEN) if ten.startswith(t)), len(UU_TIEN))
    return (khop, "__" in Path(rel).stem, len(ten), rel)


def doc_manifest() -> tuple[list[dict[str, str]], list[str]]:
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd), list(rd.fieldnames or [])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="thực sự di chuyển tệp (mặc định chỉ in)")
    ap.add_argument("--keep", action="append", default=[], help="đường dẫn (tương đối data/raw) ép giữ lại")
    args = ap.parse_args()

    rows, fields = doc_manifest()
    nhom: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r.get("sha256"):
            nhom[r["sha256"]].append(r)

    giu: dict[str, str] = {}      # sha256 -> file được giữ
    bo: list[dict[str, str]] = []  # các dòng sẽ bị di chuyển
    for sha, ds in sorted(nhom.items(), key=lambda kv: -len(kv[1])):
        if len(ds) < 2:
            continue
        ep = [r for r in ds if r["file"] in args.keep]
        ds_sap = sorted(ep or ds, key=lambda r: diem_uu_tien(r["file"]))
        giu[sha] = ds_sap[0]["file"]
        bo += ds_sap[1:]
        print(f"\n[{len(ds)} bản] giữ: {ds_sap[0]['file']}")
        for r in ds_sap[1:]:
            print(f"          bỏ : {r['file']}")

    print(f"\nTổng: {len(giu)} nhóm, {len(bo)} tệp dư, "
          f"{sum(int(r.get('bytes') or 0) for r in bo) / 1e6:.1f} MB")
    if not args.apply:
        print("Chạy lại với --apply để di chuyển (không xóa).")
        return

    for r in bo:
        src = RAW / r["file"]
        dst = DUP_DIR / r["file"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.exists():
            src.rename(dst)
        print(f"đã chuyển {r['file']}")

    if "giu_lai" not in fields:
        fields.append("giu_lai")
    bo_set = {r["file"] for r in bo}
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            r["giu_lai"] = "0" if r["file"] in bo_set else "1"
            w.writerow(r)
    print(f"Cập nhật {MANIFEST.relative_to(ROOT)} (cột giu_lai). Tệp dư ở {DUP_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

**Tiêu chí nghiệm thu:** `python scripts/dedupe_raw.py` in ra 12 nhóm / 18 tệp; sau `--apply` thì `python -c "import pandas as pd; d=pd.read_csv('data/raw/metadata_manifest.csv'); print(d[d.giu_lai=='1'].sha256.nunique(), len(d[d.giu_lai=='1']))"` cho `286 286`.
**Rủi ro:** ép giữ sai bản (bản scan mờ hơn). Cách lùi: `mv data/raw/_duplicates/<đường dẫn> data/raw/<đường dẫn>`.

---

## 2. ĐX-2 — hỗ trợ `.doc` (41 tệp biểu mẫu) — ⛔ ĐÃ CHỐT: **KHÔNG LÀM**

> **Quyết định:** biểu mẫu chỉ dùng để **gợi ý mẫu cần nộp**; nội dung chi tiết của mẫu **không nạp vào RAG**
> và hệ thống **không trả lời** khi người dùng hỏi nội dung mẫu. Vì vậy không cần chuyển 41 tệp `.doc` sang `.docx`.
> Phần code dưới đây **giữ lại để tham khảo**, chỉ dùng nếu sau này đổi quyết định (ví dụ muốn kiểm tra tự động
> rằng mẫu nào thiếu trường bắt buộc).

### 2.1 `scripts/convert_doc.py` (mới)

```python
"""Chuyển .doc (nhị phân cũ) sang .docx bằng LibreOffice headless.

extract_to_md.py chỉ đọc .pdf và .docx, nên 41 tệp .doc hiện không có đường đi trong pipeline.
Cách dùng:
    python scripts/convert_doc.py --check                 # kiểm tra đã có soffice chưa
    python scripts/convert_doc.py data/raw/05_bieu_mau_thu_tuc/ctsv
"""
import argparse
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = RAW / "_converted"


def co_soffice() -> bool:
    return shutil.which("soffice") is not None or shutil.which("libreoffice") is not None


def convert(src: Path, out_dir: Path | None = None) -> Path:
    """Trả về đường dẫn .docx; ném RuntimeError nếu không chuyển được."""
    if not co_soffice():
        raise RuntimeError("Chưa có LibreOffice. Cài: sudo dnf install libreoffice  (hoặc apt install libreoffice)")
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    out_dir = out_dir or (OUT / src.relative_to(RAW).parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([exe, "--headless", "--convert-to", "docx", "--outdir", str(out_dir), str(src)],
                       capture_output=True, text=True, timeout=180)
    dst = out_dir / (src.stem + ".docx")
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError(f"Không chuyển được {src.name}: {r.stdout[-200:]} {r.stderr[-200:]}")
    return dst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", type=Path, default=RAW)
    ap.add_argument("--check", action="store_true", help="chỉ kiểm tra LibreOffice")
    args = ap.parse_args()
    if args.check:
        print("soffice:", "có" if co_soffice() else "KHÔNG có")
        return
    target = args.target.resolve()
    files = sorted(p for p in ([target] if target.is_file() else target.rglob("*")) if p.suffix.lower() == ".doc")
    ok = 0
    for src in files:
        try:
            print(f"{src.relative_to(RAW)} -> {convert(src).relative_to(RAW)}", flush=True)
            ok += 1
        except RuntimeError as e:
            print(f"LỖI {src.relative_to(RAW)}: {e}")
    print(f"Xong {ok}/{len(files)} tệp .doc")


if __name__ == "__main__":
    main()
```

### 2.2 Sửa `scripts/extract_to_md.py` (3 chỗ)

```python
# (1) thêm hàm, đặt cạnh extract_docx()
def convert_doc(src: Path) -> Path:
    """Chuyển .doc sang .docx trong .tmp/ để extract_docx() đọc được."""
    import shutil, subprocess
    exe = shutil.which("soffice") or shutil.which("libreoffice")
    if not exe:
        raise RuntimeError("Cần LibreOffice để đọc .doc — xem scripts/convert_doc.py")
    tmp = ROOT / ".tmp" / "doc"
    tmp.mkdir(parents=True, exist_ok=True)
    subprocess.run([exe, "--headless", "--convert-to", "docx", "--outdir", str(tmp), str(src)],
                   capture_output=True, text=True, timeout=180, check=True)
    return tmp / (src.stem + ".docx")
```

```python
# (2) dòng 160 — nhận thêm .doc
files = sorted(p for p in ([target] if target.is_file() else target.rglob("*"))
               if p.suffix.lower() in {".pdf", ".docx", ".doc"})
```

```python
# (3) dòng 178 — phân nhánh; write_md() vẫn nhận `src` gốc nên đường dẫn data/ocr giữ nguyên
        if src.suffix.lower() == ".pdf":
            pages = extract_pdf(src, args.dpi, tess_config)
        elif src.suffix.lower() == ".doc":
            pages = extract_docx(convert_doc(src))
        else:
            pages = extract_docx(src)
```

**Lưu ý:** với `.doc` thì front matter `cong_cu` nên đổi thành `libreoffice + docx`; đề xuất thêm `p.nguon` = `"docx"` (hàm `extract_docx` đã trả `nguon="docx"`).
**Vì sao ưu tiên P2:** cả 41 tệp `.doc` đều là biểu mẫu → chỉ cần làm catalog (ĐX-6) là đủ cho RAG.

---

## 3. ĐX-3 — `scripts/clean_md.py` thêm `--kieu` (sửa)

**Vấn đề:** `to_markdown()` (dòng 164–184) chỉ nhận `CHUONG`/`DIEU`/`SUA_DOI`. Với QĐ 736, sổ tay, quy trình thủ tục, biên chế năm học, hàm này trả về **một Node khổng lồ không có heading** → `processed_loader` chỉ tạo được 1 Node/văn bản, không trích dẫn được mục.

### 3.1 Thêm hằng số + hàm (đặt sau dòng 52)

```python
# ===== Chế độ cắt (--kieu) =====
KIEU = ("dieu", "so_muc", "buoc", "bang")

LA_MA = re.compile(r"^([IVXLC]{1,6})[.)]\s+(\S.*)$")            # I. / IV.
SO_MUC = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,2})[.)]?\s+(\S.*)$")  # 1. / 1.1. / 2.3.
CHU_CAI = re.compile(r"^([a-zđ])\)\s+(\S.*)$")                    # a) / đ)
BUOC = re.compile(r"^(?:Bước|BƯỚC)\s*(\d{1,2})\s*[:.)]?\s*(.*)$")
NHOM_BUOC = re.compile(r"^(Thành phần|Hồ sơ|Thời hạn|Cách thức|Trình tự|Lưu ý|Căn cứ|Đối tượng)\b", re.I)
BANG_DONG = re.compile(r"\S\s{2,}\S.*\s{2,}\S")                    # >= 3 cột tách bởi >= 2 khoảng trắng


def to_markdown_so_muc(part: list[str], title: str) -> list[str]:
    """Văn bản đánh số I. / 1. / 1.1. / a) — dùng cho QĐ 736, sổ tay, quy định không chia Điều."""
    md = [f"# {title}", ""]
    for p in part:
        if m := LA_MA.match(p):
            md += [f"## {m[1]}. {m[2]}", ""]
        elif m := SO_MUC.match(p):
            cap = min(m[1].count(".") + 2, 4)
            md += [f"{'#' * cap} {m[1]}. {m[2]}", ""]
        elif m := CHU_CAI.match(p):
            md += [f"- **{m[1]})** {m[2]}", ""]
        else:
            md += [p, ""]
    return md


def to_markdown_buoc(part: list[str], title: str) -> list[str]:
    """Quy trình thủ tục: mỗi bước thành một mục để Node giữ trọn các bước liền nhau."""
    md = [f"# {title}", ""]
    for p in part:
        if m := BUOC.match(p):
            md += [f"### Bước {m[1]}. {m[2]}".rstrip(), ""]
        elif NHOM_BUOC.match(p):
            md += [f"## {p}", ""]
        else:
            md += [p, ""]
    return md


def to_markdown_bang(part: list[str], title: str, so_dong_moi_node: int = 15) -> list[str]:
    """Bảng: nhóm `so_dong_moi_node` dòng thành một mục và LẶP LẠI dòng tiêu đề cột.

    Vì sao lặp header: nếu Node chỉ có các con số mà mất tên cột thì câu trả lời vô nghĩa
    (đúng loại lỗi đã ghi ở nhóm 1 của báo cáo raw).
    """
    md = [f"# {title}", ""]
    header = next((p for p in part if BANG_DONG.search(p)), None)
    rows = [p for p in part if p is not header]
    for i in range(0, len(rows), so_dong_moi_node):
        nhom = rows[i:i + so_dong_moi_node]
        if not nhom:
            continue
        md += [f"## {nhom[0][:60].strip()}…", ""]
        if header:
            md += [header, ""]
        md += [*nhom, ""]
    return md


TO_MARKDOWN = {
    "dieu": to_markdown,
    "so_muc": to_markdown_so_muc,
    "buoc": to_markdown_buoc,
    "bang": to_markdown_bang,
}
```

### 3.2 Sửa `main()` (dòng 227–262)

```python
    ap.add_argument("--kieu", choices=KIEU, default="dieu",
                    help="dieu: văn bản chia Điều | so_muc: I./1./1.1. | buoc: quy trình | bang: bảng")
    ...
    kieu = args.kieu
    for path, meta, pages in keep:
        ...
        # Chỉ văn bản chia Điều mới cần tách phần "Quyết định ban hành"; các kiểu khác giữ nguyên 1 phần
        parts = split_parts(paras) if kieu == "dieu" else [paras]
        ...
        for k, part in enumerate(parts):
            is_bh = kieu == "dieu" and len(parts) > 1 and k < len(parts) - 1 and max(
                (int(m[1]) for p in part if (m := DIEU.match(p))), default=0) <= 5
            title = "Quyết định ban hành" if is_bh else (doc_meta.get("ten_van_ban") or part_title(part, fallback))
            md += TO_MARKDOWN[kieu](part, title)
        ...
        # check() chỉ có nghĩa với kiểu dieu; các kiểu khác bỏ qua để không báo lỗi giả
        issues = check(meta, pages, parts, text) if kieu == "dieu" else []
```

**Ghi chú thiết kế:** `processed_loader.py` chỉ cần heading đúng cấp, nên **không phải sửa gì thêm** cho 3 kiểu mới (xem ĐX-4 để có nhãn mục đẹp hơn).
**Tiêu chí nghiệm thu:** với QĐ 736, tầng 2 phải có `## 1. Hình thức đào tạo chính quy` và `### 1.1. Trình độ đại học…` (hiện chỉ có `#` duy nhất).

---

## 4. ĐX-4 — `src/processed_loader.py`: nhãn mục và đường dẫn mục (sửa)

**Vì sao:** câu hỏi trích dẫn cần "QĐ 736 > 2. Vừa làm vừa học > 2.3. Liên thông", vì `1.3` và `2.3` có tiêu đề giống hệt nhau. Hiện metadata chỉ có `dieu`/`sua_doi_dieu`, nên mọi mục lớp B/C/D đều ra `nguon_trich` = tên văn bản.

```python
# thêm hằng số cạnh SO_DIEU
SO_MUC = re.compile(r"^(?:(\d{1,2}(?:\.\d{1,2}){0,2})|([IVXLC]{1,6})|([a-zđ]))[.)]?\s")


def duong_dan_muc(van_ban: str, chuong: str, title: str) -> str:
    return " > ".join(x for x in (van_ban, chuong, title) if x)


# trong load_processed(), nhánh level > 2:
            m = SO_DIEU.search(title)
            phan = "ban_hanh" if van_ban == "Quyết định ban hành" else ("sua_doi" if level == 4 else "chinh")
            mm = None if m else SO_MUC.match(title)      # <-- thêm
        node_meta = {
            ...
            "dieu": m[1] if (m and level == 3) else "",
            "sua_doi_dieu": m[1] if (m and level == 4) else "",
            "muc": (mm.group(1) or mm.group(2) or mm.group(3)) if mm else "",   # <-- thêm
            "duong_dan_muc": duong_dan_muc(ten_van_ban, chuong, title),          # <-- thêm
            ...
        }


# nguon_trich(): thêm nhánh mục, đặt trước nhánh ban_hanh
    if meta.get("muc"):
        return f"Mục {meta['muc']} — {meta.get('duong_dan_muc') or meta.get('van_ban', '')}".strip(" —")
```

**Tác động lên ĐX-8:** đánh giá theo mục dùng `duong_dan_muc` để so tiền tố, không cần thêm cột nào khác.
**Rủi ro:** `SO_MUC` có thể khớp nhầm dòng nội dung bắt đầu bằng "1." trong văn bản chia Điều → vì chỉ chạy khi `SO_DIEU` **không** khớp, và chỉ ở heading do tầng 2 sinh ra, nên an toàn.

---

## 5. ĐX-5 — Manifest corpus (mới + sửa)

### 5.1 `configs/corpus_sgu.yaml` (mới)

```yaml
# Nguồn dữ liệu của RAG. Mỗi `collection` = một thư mục tầng 2 + danh sách văn bản nạp vào index.
# Thêm/bớt văn bản chỉ cần sửa file này; index tự build lại nhờ fingerprint trong index_builder.py.
collections:
  hoc_vu:
    corpus_dir: data/processed/01_quy_che_dao_tao
    kieu_cat: dieu
    van_ban:
      - tien_to: "25_quy-che-dao-tao"
        ten: "Quy chế đào tạo trình độ đại học SGU 2021"
        so_hieu: "258/QĐ-ĐHSG"
        ngay_ban_hanh: "2022-01-20"
        tinh_trang: con_hieu_luc
      - tien_to: "QD 3183.2025"
        ten: "QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021"
        sua_doi: "25_quy-che-dao-tao"
        tinh_trang: con_hieu_luc
      - tien_to: "8_QD810"
        ten: "QĐ 810 về học cùng lúc hai chương trình"
      - tien_to: "2022-2375"
        ten: "QĐ 2375/2022 về chuyển chương trình, ngành đào tạo"
      - tien_to: "22_quy-dinh-ve-khoi-luong"
        ten: "Quy định khối lượng đào tạo hệ chính quy theo tín chỉ"
      - tien_to: "Quydinh150tc"
        ten: "Quy định số tín chỉ tối thiểu kỹ sư CNTT (khóa 2017 trở đi)"

  ctsv:
    corpus_dir: data/processed/02_cong_tac_sinh_vien
    kieu_cat: buoc          # 14 quy trình + chính sách
    van_ban: []             # rỗng = nạp hết file .md trong corpus_dir

  ctdt:
    corpus_dir: data/processed/03_chuong_trinh_dao_tao
    kieu_cat: bang
    van_ban: []
```

### 5.2 `src/corpus.py` (sửa, giữ tương thích ngược)

```python
"""Nội dung đầu vào của RAG: đọc từ configs/corpus_sgu.yaml, có fallback về hằng số cũ."""
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "configs" / "corpus_sgu.yaml"

PROCESSED_ROOT = "data/processed"
CORPUS_DIR = f"{PROCESSED_ROOT}/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc"   # giữ để tương thích
SGU_HIEU_LUC: dict[str, str] = { ... }   # giữ nguyên như hiện tại (fallback + dedupe_raw.py dùng)


@dataclass(frozen=True)
class VanBan:
    tien_to: str
    ten: str
    so_hieu: str = ""
    ngay_ban_hanh: str = ""
    tinh_trang: str = "con_hieu_luc"
    sua_doi: str = ""


@dataclass(frozen=True)
class Collection:
    ten: str
    corpus_dir: str
    kieu_cat: str = "dieu"
    van_ban: tuple[VanBan, ...] = ()


def load_manifest(path: Path | None = None) -> dict[str, Collection]:
    p = path or MANIFEST
    if not p.exists():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {
        ten: Collection(
            ten=ten,
            corpus_dir=c["corpus_dir"],
            kieu_cat=c.get("kieu_cat", "dieu"),
            van_ban=tuple(
                VanBan(
                    tien_to=v["tien_to"], ten=v["ten"], so_hieu=v.get("so_hieu", ""),
                    ngay_ban_hanh=v.get("ngay_ban_hanh", ""),
                    tinh_trang=v.get("tinh_trang", "con_hieu_luc"), sua_doi=v.get("sua_doi", ""),
                )
                for v in (c.get("van_ban") or [])
            ),
        )
        for ten, c in (data.get("collections") or {}).items()
    }


def collection_mac_dinh() -> Collection:
    """Dùng khi chưa có manifest — đúng bằng cấu hình đang chạy hiện nay."""
    return Collection(
        ten="hoc_vu", corpus_dir=CORPUS_DIR, kieu_cat="dieu",
        van_ban=tuple(VanBan(t, n) for t, n in SGU_HIEU_LUC.items()),
    )
```

Trong `src/config.py`, `RAGConfig` chỉ cần thêm 1 trường và tính lại trong `__post_init__`:

```python
    collection: str = "hoc_vu"     # tên mục trong configs/corpus_sgu.yaml

    def __post_init__(self) -> None:
        cols = load_manifest()
        col = cols.get(self.collection) or collection_mac_dinh()
        self.corpus_dir = col.corpus_dir
        self.corpus_files = tuple(v.tien_to for v in col.van_ban) or ()   # rỗng = nạp hết
        self.ten_van_ban = {v.tien_to: v.ten for v in col.van_ban}
        ...  # phần persist_dir, ollama_base_url giữ nguyên
        self.persist_dir = self.persist_dir or f"storage/{self.name}/{PurePosixPath(self.corpus_dir).relative_to(PROCESSED_ROOT)}"
```

**Lưu ý:** khi `van_ban` rỗng (collection `ctdt`), `corpus_files = ()` → `processed_loader.corpus_files()` nạp **hết** `.md` trong thư mục, đúng hành vi đã có.
**Tương thích ngược:** chưa tạo manifest thì `load_manifest()` trả `{}` → rơi về `collection_mac_dinh()`, kết quả **y hệt hôm nay** (đã kiểm chứng: 6 văn bản / 54 Node).

---

## 6. ĐX-6 — Bảng gợi ý biểu mẫu + chính sách từ chối nội dung mẫu (mới)

> **Quyết định thiết kế (đã chốt):**
> 1. Biểu mẫu **không được nạp nội dung** vào index — chỉ nạp **bảng gợi ý**: mẫu nào dùng cho việc gì, tải ở đâu.
> 2. Khi người dùng hỏi **nội dung chi tiết / cách điền** biểu mẫu, hệ thống **chủ động từ chối** và chỉ đưa liên kết tải mẫu.
> 3. Vì (1) và (2) là hai việc khác nhau, cần **cả** hai lớp: dữ liệu (không có nội dung mẫu để mà trả lời)
>    **và** chính sách (chặn cả trường hợp LLM tự bịa nội dung mẫu từ mô tả trong quy trình).

### 6.1 `scripts/build_catalog_bieu_mau.py` — sinh bảng gợi ý

**Dữ liệu đầu vào đã có sẵn và rất tốt:** cả **103** tệp trong `05_bieu_mau_thu_tuc` đều có `url` trong
`metadata_manifest.csv`, và nhiều tệp đã có `tieu_de` đúng nghĩa ("Đơn xin hoãn thi", "Mẫu đơn xin công nhận và
chuyển điểm") — tốt hơn hẳn tên tệp kiểu `mau_1_baoluu_quydoi_kgghinhan_NEW.doc`.

```python
"""Sinh bảng gợi ý biểu mẫu. KHÔNG nạp nội dung biểu mẫu vào RAG.

Vì sao tên file không bắt đầu bằng "_": processed_loader.corpus_files() bỏ qua mọi file "_*"
(dòng `if not p.name.startswith("_")`), nên file cần nạp phải tên là catalog_bieu_mau.md;
chỉ file .jsonl cho máy đọc mới đặt tiền tố "_".

Cách dùng:
    python scripts/build_catalog_bieu_mau.py --dry-run
python scripts/build_catalog_bieu_mau.py --dry-run
    python scripts/build_catalog_bieu_mau.py
"""
import argparse
import csv
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
MANIFEST = RAW / "metadata_manifest.csv"
OUT_DIR = ROOT / "data" / "processed" / "05_bieu_mau_thu_tuc"
PREFIX = "05_bieu_mau_thu_tuc"

JUNK = re.compile(r"download|xem chi tiết|tải về|tại đây|^$", re.I)
NHOM = [
    ("Bảo lưu kết quả học tập", r"bao-luu|tam-nghi-hoc"),
    ("Học lại sau thời gian bảo lưu", r"vao-hoc-lai|hoc-lai"),
    ("Xin thôi học", r"thoi-hoc"),
    ("Chuyển trường", r"chuyen-truong"),
    ("Điểm rèn luyện", r"diem-ren-luyen|phieu-danh-gia-diem-ren-luyen"),
    ("Học bổng khuyến khích học tập", r"hoc-bong"),
    ("Miễn giảm học phí, trợ cấp", r"mien-giam-hoc-phi|tro-cap|chinh-sach"),
    ("Phúc khảo, hoãn thi, thi lại", r"phuckhao|hoan_thi|hoan-thi|thi_lai|thi-lai"),
    ("Chuyển điểm, điều chỉnh đăng ký môn học", r"chuyendiem|dieuchinhDKMH|rut-mon|dang-ky-mon"),
    ("Xác nhận, bảng điểm, bản sao", r"xac-nhan|bang-diem|ban-sao"),
    ("Khác", r"."),
]


def bo_dau(s: str) -> str:
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()


def ten_mau(row: dict[str, str]) -> str:
    """Ưu tiên `tieu_de` của manifest; nhãn rác thì lấy từ tên tệp (giống fallback của clean_md.py)."""
    t = (row.get("tieu_de") or "").strip()
    return Path(row["file"]).stem.replace("_", " ").strip() if JUNK.search(t) else t


def xep_nhom(ten_file: str) -> str:
    t = bo_dau(ten_file)
    return next(n for n, rx in NHOM if re.search(rx, t))


def gan_quy_trinh(row: dict[str, str], quy_trinh: list[str]) -> str:
    """Ghép mẫu với quy trình theo số token chung (đã bỏ dấu) — đủ tốt vì tên đều có từ khoá nghiệp vụ."""
    tu_mau = set(bo_dau(ten_mau(row) + " " + Path(row["file"]).stem).split())
    diem = [(len(tu_mau & set(bo_dau(q).split())), q) for q in quy_trinh]
    diem.sort(reverse=True)
    return diem[0][1] if diem and diem[0][0] >= 2 else ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(open(MANIFEST, encoding="utf-8")))
    mau = [r for r in rows if r["file"].startswith(PREFIX) and r.get("giu_lai", "1") == "1"]
    quy_trinh = [Path(r["file"]).stem for r in rows if "quy_trinh_thu_tuc" in r["file"]]
    for r in mau:
        r["_ten"] = ten_mau(r)
        r["_nhom"] = xep_nhom(Path(r["file"]).name)
        r["_qt"] = gan_quy_trinh(r, quy_trinh)

    md = [
        "---",
        'ten_van_ban: "Biểu mẫu và thủ tục"',
        "loai: bieu_mau",
        'nguon_tang_1: "(sinh tự động bởi scripts/build_catalog_bieu_mau.py)"',
        "---",
        "",
        "# Biểu mẫu và thủ tục",
        "",
        "## Bảng tổng hợp biểu mẫu",
        "",
        "Hệ thống chỉ gợi ý **mẫu cần dùng** và nơi tải; không chứa nội dung chi tiết của mẫu.",
        "",
        "| Biểu mẫu | Dùng cho | Tải mẫu |",
        "|---|---|---|",
    ]
    for r in mau:
        md.append(f"| {r['_ten']} | {r['_nhom']} | {r['url']} |")
    for nhom in dict.fromkeys(r["_nhom"] for r in mau):
        md += ["", f"## {nhom}", ""]
        for r in [r for r in mau if r["_nhom"] == nhom]:
            md += [
                f"### {r['_ten']}",
                f"- Dùng cho: {r['_nhom']}",
            ]
            if r["_qt"]:
                md += [f"- Quy trình liên quan: {r['_qt']}"]
            md += [
                f"- Tải mẫu: {r['url']}",
                "- Lưu ý: hệ thống chỉ gợi ý mẫu cần dùng, không chứa nội dung chi tiết của mẫu.",
                "",
            ]

    if args.dry_run:
        print("
".join(md[:20]) + f"
... ({len(mau)} mẫu, {len(md)} dòng)")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "catalog_bieu_mau.md").write_text("
".join(md), encoding="utf-8")
    print(f"{len(mau)} mẫu -> {(OUT_DIR / 'catalog_bieu_mau.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

**Vì sao thiết kế này khớp pipeline hiện có (không cần sửa gì thêm):**

| Chi tiết | Lý do |
|---|---|
| Mỗi mẫu là một `###` | `processed_loader` tạo 1 Node cho mỗi heading cấp 3 → truy hồi theo đúng tên mẫu |
| `## Bảng tổng hợp biểu mẫu` (~800 từ) | Trả lời được câu "có những mẫu đơn nào"; dưới `MAX_TU`=1024 nên không bị cắt |
| Bắt buộc có front matter `---` | `processed_loader.front_matter()` dùng `text.split("---\n", 2)`; thiếu là lỗi ngay |
| `ten_van_ban` trong front matter | Tên tệp không khớp tiền tố nào trong `ten_van_ban` nên `nguon_trich` lấy từ front matter |
| `loai: bieu_mau` | Cần cho guard ở 6.2 (xem ĐX-4: phải thêm `loai` vào danh sách khoá đọc từ front matter) |
| Không đặt tên `_catalog...` | `corpus_files()` bỏ qua file `_*` |
| Không có nội dung mẫu | Không có gì để LLM trích ra, kể cả khi bị hỏi |

### 6.2 `src/policy.py` — chính sách "gợi ý được, nội dung mẫu thì không"

**Vì sao cần lớp thứ hai:** không nạp nội dung mẫu **không đủ** để hệ thống không trả lời. Các văn bản quy trình
(lớp C) có nhắc "nộp đơn xin bảo lưu" và có thể mô tả vài trường trong đơn; LLM hoàn toàn có thể dựng lại một
"mẫu đơn" nghe hợp lý từ đó. Vì vậy phải chặn ở tầng truy vấn.

```python
"""Chính sách trả lời của hệ thống: gợi ý biểu mẫu được, nội dung biểu mẫu thì không.

Nguyên tắc: guard này phải **thận trọng** (chỉ khớp câu hỏi nói rõ về mẫu/đơn/điền),
vì từ chối sai đang là vấn đề đã đo được (52% từ chối trong nhật ký 56 câu).
"""
import re

HOI_NOI_DUNG_MAU = re.compile(
    r"(nội\s+dung|chi\s+tiết|mẫu|đơn|biểu\s+mẫu)[^?]{0,40}?(ghi|điền|viết|gồm|ra\s+sao|thế\s+nào|những\s+gì)"
    r"|(điền|ghi|viết)\s+(vào\s+)?(mẫu|đơn|biểu\s+mẫu)"
    r"|mẫu\s+(đơn|này)\s+[^?]{0,20}?(gồm|ghi|có\s+gì)"
    r"|cách\s+(điền|ghi|viết)\s+(mẫu|đơn)",
    re.I,
)

CAU_TU_CHOI = (
    "Hệ thống chỉ tra cứu quy chế, quy định và **gợi ý biểu mẫu cần dùng**, "
    "không chứa nội dung chi tiết của biểu mẫu. Bạn vui lòng mở tệp mẫu theo đường dẫn dưới đây để xem và điền."
)


def la_hoi_noi_dung_mau(question: str) -> bool:
    return bool(HOI_NOI_DUNG_MAU.search(question))


def node_bieu_mau(nodes: list) -> list:
    """Lọc các Node thuộc bảng gợi ý biểu mẫu (dựa vào metadata `loai`)."""
    return [n for n in nodes if n.node.metadata.get("loai") == "bieu_mau"]
```

```python
# src/query_engine.py — thêm hàm bọc, dùng cho pipeline.py và app/app.py
from policy import CAU_TU_CHOI, la_hoi_noi_dung_mau, node_bieu_mau


def tra_loi(engine, question: str, cfg: RAGConfig, index=None) -> None:
    """Trả lời câu hỏi, trừ câu hỏi về nội dung biểu mẫu (ĐX-6.2)."""
    if la_hoi_noi_dung_mau(question):
        print(CAU_TU_CHOI)
        if index is not None:
            from retriever import node_label, search

            mau = node_bieu_mau(search(index, cfg, question))
            if mau:
                print("Mẫu có thể cần: " + "; ".join(dict.fromkeys(node_label(n) for n in mau[:3])))
        return
    ask(engine, question, cfg)
```

Và thêm **một dòng vào `QA_PROMPT`** làm lớp mềm cho các cách hỏi mà regex không khớp:

```text
"Hệ thống không chứa nội dung chi tiết của biểu mẫu; nếu được hỏi nội dung, cách điền hoặc các mục trong "
"biểu mẫu, hãy nói rằng chỉ gợi ý được mẫu cần dùng và đề nghị người dùng mở tệp mẫu."
```

### 6.3 Kiểm thử và đo lường chính sách (bắt buộc, vì đây là chỗ dễ từ chối sai)

```python
# tests/test_policy_bieu_mau.py
import unittest

from policy import la_hoi_noi_dung_mau


class TestChinhSachBieuMau(unittest.TestCase):
    PHAI_TU_CHOI = [
        "mẫu đơn xin bảo lưu ghi những nội dung gì",
        "điền đơn xin hoãn thi như thế nào",
        "mẫu đơn này gồm những mục nào",
        "cách ghi đơn xin thôi học",
    ]
    PHAI_TRA_LOI = [   # chống từ chối quá tay
        "xin bảo lưu kết quả học tập cần nộp đơn nào",
        "quy trình xin thôi học gồm những bước nào",
        "hồ sơ xin hoãn thi gồm những giấy tờ gì",
        "thời hạn nộp đơn xin phúc khảo là bao lâu",
    ]

    def test_phai_tu_choi(self):
        for q in self.PHAI_TU_CHOI:
            self.assertTrue(la_hoi_noi_dung_mau(q), q)

    def test_khong_tu_choi_qua_tay(self):
        for q in self.PHAI_TRA_LOI:
            self.assertFalse(la_hoi_noi_dung_mau(q), q)


if __name__ == "__main__":
    unittest.main()
```

Thêm vào `eval/cau_hoi_danh_gia.json` (dùng đúng cơ chế `pham_vi` đã có):

```json
[
  {"question": "Mẫu đơn xin bảo lưu ghi những nội dung gì?", "pham_vi": "ngoai",
   "dap_an": "Chỉ gợi ý mẫu + link; không trả lời nội dung mẫu"},
  {"question": "Điền đơn xin hoãn thi như thế nào?", "pham_vi": "ngoai",
   "dap_an": "Chỉ gợi ý mẫu + link; không trả lời nội dung mẫu"},
  {"question": "Xin bảo lưu kết quả học tập cần nộp đơn nào?", "pham_vi": "trong",
   "dap_an": "Mẫu đơn xin tạm nghỉ học/bảo lưu kết quả học tập (kèm link tải)"}
]
```

**Chỉ số cần báo cáo thêm** (đã có sẵn cơ chế tách trong `eval/evaluate_answers.py`):
`từ chối đúng` (câu ngoài phạm vi) **và** `từ chối sai` (câu trong phạm vi bị từ chối) — mục tiêu là
từ chối đúng tăng mà từ chối sai **không** tăng.

---

## 7. ĐX-7 — Ba index, lọc metadata rồi mới tới router

### 7.1 Bước 1 (khuyến nghị làm trước): lọc metadata trên một index

```python
# src/retriever.py — thêm tham số lọc
def get_retriever(index: VectorStoreIndex, cfg: RAGConfig, nhom: str | None = None) -> BaseRetriever:
    filters = MetadataFilters(filters=[MetadataFilter(key="nhom", value=nhom)]) if nhom else None
    vector = index.as_retriever(similarity_top_k=cfg.similarity_top_k, filters=filters)
    ...
```

```python
# src/query_engine.py — truyền nhóm qua tham số thay vì sửa Settings
def build_query_engine(index, cfg: RAGConfig, nhom: str | None = None) -> RetrieverQueryEngine:
    ...  retriever=get_retriever(index, cfg, nhom=nhom), ...
```

**Vì sao làm trước:** `MetadataFilters` không tốn thêm lượt gọi LLM, đo được ngay bằng `make eval`.

### 7.2 Bước 2 (khi đã tách index): `src/router.py` (mới)

```python
"""Router chọn index theo loại câu hỏi. Chỉ dùng khi đã tách 3 index.

Lưu ý chi phí: RouterQueryEngine tốn THÊM một lượt gọi LLM cho mỗi câu hỏi; phải đo lại độ trễ
(xem Chương 5) trước khi bật mặc định.
"""
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool

MO_TA = {
    "hoc_vu": "Quy chế, quy định học vụ: tín chỉ, điểm, thi, tốt nghiệp, rút học phần, cảnh báo học tập.",
    "ctsv": "Công tác sinh viên và thủ tục hành chính: điểm rèn luyện, học bổng, học phí, bảo lưu, thôi học, biểu mẫu.",
    "ctdt": "Chương trình đào tạo theo ngành và khóa tuyển sinh: môn học từng học kỳ, tổng tín chỉ.",
}


def build_router(engines: dict[str, object], llm) -> RouterQueryEngine:
    tools = [
        QueryEngineTool.from_defaults(query_engine=eng, description=MO_TA[ten], name=ten)
        for ten, eng in engines.items()
    ]
    return RouterQueryEngine(selector=LLMSingleSelector.from_defaults(llm=llm), query_engine_tools=tools)
```

```python
# src/index_builder.py — không cần đổi: persist_dir đã tách theo profile + corpus_dir (dòng 49-55),
# nên collection "ctdt" tự có thư mục riêng storage/<profile>/03_chuong_trinh_dao_tao/
```

---

## 8. ĐX-8 — `eval/evaluate.py`: nhãn theo `(nguồn, Điều/mục)` (sửa)

**Vì sao:** khi corpus có ~290 văn bản, `dieu_dung: "7"` mơ hồ (nhiều văn bản cùng Điều 7). Hiện đã có 2 hàm luật riêng cho bộ 01/02; cách dưới đây tổng quát hoá mà **không đổi kết quả** hai bộ đang có.

```python
@dataclass(frozen=True)
class Nhan:
    nguon: str = ""     # tiền tố tên tệp, vd "25_quy-che" hoặc "QD 3183"
    dieu: str = ""
    muc: str = ""


def khop(n: NodeWithScore, nhan: Nhan) -> bool:
    m = n.node.metadata
    if nhan.nguon and not str(m.get("file", "")).startswith(nhan.nguon):
        return False
    if nhan.dieu:
        return m.get("dieu") == nhan.dieu or m.get("sua_doi_dieu") == nhan.dieu
    if nhan.muc:
        return str(m.get("duong_dan_muc", "")).startswith(nhan.muc) or m.get("muc") == nhan.muc
    return bool(nhan.nguon)


def doc_nhan(q: dict) -> Nhan:
    """Nhận cả định dạng cũ ({"question","dieu_dung"}) lẫn mới ({"question","nhan":{...}})."""
    if "nhan" in q:
        return Nhan(**q["nhan"])
    return Nhan(nguon="25_quy-che", dieu=q["dieu_dung"].split()[0])   # = luật bộ 01 hiện nay
```

Câu hỏi mới cho lớp C/D/E dùng dạng:

```json
[
  {"question": "Sinh viên muốn bảo lưu kết quả học tập thì nộp hồ sơ gồm những gì?",
   "nhan": {"nguon": "8_qui-trinh-bao-luu", "muc": "Hồ sơ"}},
  {"question": "Ngành Công nghệ thông tin khóa 2024 học bao nhiêu tín chỉ?",
   "nhan": {"nguon": "CTDT_CNTT_2024", "muc": "Tổng"}}
]
```

**Bắt buộc giữ:** chạy lại bộ 01/02 sau khi sửa phải ra **đúng** R@1 81% / MRR 0,892 và 90% / 0,910.

---

## 9. ĐX-9 — Kiểm thử mới

```python
# tests/test_clean_md_kieu.py
import unittest

from clean_md import to_markdown_bang, to_markdown_buoc, to_markdown_so_muc


class TestKieuCat(unittest.TestCase):
    def test_so_muc_qd736(self):
        part = ["1. Hình thức đào tạo chính quy", "1.1. Trình độ đại học, cao đẳng   +06 học kỳ",
                "1.2. Trình độ trung cấp           +2 năm học"]
        md = "\n".join(to_markdown_so_muc(part, "QĐ 736/2014"))
        self.assertIn("## 1. Hình thức đào tạo chính quy", md)
        self.assertIn("#### 1.1. Trình độ đại học", md)

    def test_buoc_quy_trinh(self):
        part = ["Hồ sơ", "Bước 1. Sinh viên nộp đơn tại Phòng CTSV",
                "Bước 2. Phòng CTSV xét duyệt trong 05 ngày làm việc"]
        md = "\n".join(to_markdown_buoc(part, "Quy trình bảo lưu"))
        self.assertIn("## Hồ sơ", md)
        self.assertIn("### Bước 1. Sinh viên nộp đơn", md)
        self.assertIn("### Bước 2. Phòng CTSV", md)

    def test_bang_lap_header(self):
        part = ["Học kỳ   Mã môn   Tên môn   Số TC", "1   IT001   Nhập môn lập trình   3",
                "1   IT002   Cấu trúc dữ liệu   3"]
        md = to_markdown_bang(part, "CTĐT CNTT", so_dong_moi_node=2)
        self.assertEqual(md.count("Học kỳ   Mã môn   Tên môn   Số TC"), 1)  # 3 dòng -> 1 nhóm


if __name__ == "__main__":
    unittest.main()
```

```python
# tests/test_corpus_manifest.py
import unittest

from corpus import Collection, VanBan, collection_mac_dinh, load_manifest


class TestManifest(unittest.TestCase):
    def test_fallback_khi_chua_co_manifest(self):
        col = load_manifest(path=None) or {}
        # Chưa tạo configs/corpus_sgu.yaml -> rơi về cấu hình cũ, đúng 6 văn bản
        if not col:
            self.assertEqual(len(collection_mac_dinh().van_ban), 6)

    def test_manifest_doc_dung_kieu(self):
        col = load_manifest()
        self.assertIsInstance(col, dict)
        for c in col.values():
            self.assertIsInstance(c, Collection)
            for v in c.van_ban:
                self.assertIsInstance(v, VanBan)
                self.assertTrue(v.tien_to and v.ten)
```

```python
# tests/test_dedupe_raw.py — chỉ kiểm tra hàm thuần, không đụng đĩa
import unittest

from scripts.dedupe_raw import diem_uu_tien


class TestUuTien(unittest.TestCase):
    def test_uutien_tien_to_dang_dung(self):
        a = "01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc/25_quy-che-dao-tao-trinh-do-dai-hoc-tai-truong-dai-hoc-sai-gon.pdf"
        b = "01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc/4. QuyCheDaoTaoDHSG 2021__daotao.pdf"
        self.assertLess(diem_uu_tien(a), diem_uu_tien(b))


if __name__ == "__main__":
    unittest.main()
```

**Lưu ý import:** `scripts/` không nằm trong `sys.path` của `tests/__init__.py`; đề xuất thêm
`sys.path.insert(0, str(ROOT / "scripts"))` vào `tests/__init__.py` (1 dòng).

---

## 10. Lệnh chạy và tiêu chí nghiệm thu

```bash
# Đợt 0 — dọn dữ liệu
python scripts/dedupe_raw.py                     # xem 12 nhóm / 18 tệp
python scripts/dedupe_raw.py --apply
make test                                        # 26 test cũ + test mới phải xanh

# Đợt 1 — lớp A vào index
python scripts/extract_to_md.py data/raw/01_quy_che_dao_tao/3_cong_tac_thi_ket_thuc_hoc_phan
python scripts/clean_md.py data/ocr/01_quy_che_dao_tao/3_cong_tac_thi_ket_thuc_hoc_phan --kieu dieu
RAG_PROFILE=server RAG_EMBED_DEVICE=cpu venv/bin/python eval/evaluate.py --cau-hinh vector --kiem-chung

# Đợt 2 — lớp C/D
python scripts/clean_md.py data/ocr/02_cong_tac_sinh_vien/quy_trinh_thu_tuc --kieu buoc
python scripts/build_catalog_bieu_mau.py

# Đợt 3 — lớp E
python scripts/clean_md.py data/ocr/03_chuong_trinh_dao_tao --kieu bang
```

| Tiêu chí | Ngưỡng |
|---|---|
| `make test` | 26 test cũ vẫn xanh + test mới xanh |
| Bộ 01 (31 câu) sau Đợt 1 | R@1 **≥ 81%**, MRR **≥ 0,892** (không được giảm) |
| Bộ 02 (10 câu) sau Đợt 1 | R@1 ≥ 90% |
| Câu hỏi thủ tục sau Đợt 2 | "bảo lưu cần hồ sơ gì", "thôi học thế nào" trả lời đúng, không bị từ chối |
| Câu hỏi **nội dung biểu mẫu** | luôn từ chối + đưa link mẫu (kiểm bằng `tests/test_policy_bieu_mau.py`) |
| Từ chối sai sau khi thêm guard | **không tăng** so với hiện tại (đo bằng `make eval-answers`) |
| Câu hỏi CTĐT sau Đợt 3 | "ngành CNTT khóa 2024 bao nhiêu tín chỉ" đúng; câu hỏi học vụ **không** bị CTĐT chen vào top-3 |

---

## 11. Rủi ro và cách lùi

| Rủi ro | Cách lùi |
|---|---|
| `clean_md.py --kieu so_muc` khớp nhầm số La Mã trong câu văn | Chạy `--kieu dieu` cho văn bản quy phạm; kiểm `_bao_cao_kiem_tra.md`; chạy `--kieu so_muc` trên **một** thư mục rồi đọc lại 20 dòng đầu |
| `dedupe_raw.py --apply` giữ nhầm bản scan mờ | Mọi tệp chỉ **được di chuyển**; phục hồi bằng `mv data/raw/_duplicates/<path> data/raw/<path>` |
| Manifest YAML sai → index rỗng | `load_manifest()` trả `{}` thì rơi về hằng số cũ; thêm test `test_manifest_doc_dung_kieu` |
| Thêm 80 CTĐT làm giảm R@1 bộ 01 | Đo bằng `--cau-hinh vector` **trước và sau**; nếu giảm > 3 điểm thì tách Index 3 ngay (ĐX-7) |
| Router tốn thêm 1 lượt LLM/câu | Chỉ bật sau khi đo độ trễ; mặc định vẫn dùng `MetadataFilters` |
| OCR toàn bộ 80 CTĐT tốn nhiều giờ | Chỉ OCR 8 tệp chu kỳ 2024–2028 trước |

---

## 12. Thứ tự áp dụng

| Bước | Làm gì | Vì sao thứ tự này |
|---|---|---|
| 1 | ĐX-1 (dedupe) | Dọn trước để mọi phép đo sau không bị nhiễu bởi bản trùng |
| 2 | ĐX-9 một phần (test khung) + ĐX-3 + ĐX-4 | Ba đề xuất này đi liền: `--kieu` sinh heading, `processed_loader` đọc nhãn mục |
| 3 | ĐX-5 (manifest) | Sau khi có 2 file tầng 2 mới thì mới khai báo collection |
| 4 | ĐX-8 (nhãn đánh giá) | Phải có `muc`/`duong_dan_muc` từ bước 2 |
| 5 | ĐX-6.1 (bảng gợi ý biểu mẫu) + ĐX-6.2 (`src/policy.py` + test) | Không phụ thuộc OCR; **phải làm cùng nhau**, vì chỉ bỏ nội dung mẫu là chưa đủ để hệ thống không trả lời |
| 6 | ~~ĐX-2 (`.doc`)~~ | **Bỏ** — đã chốt không nạp nội dung biểu mẫu |
| 7 | ĐX-7 (router) | Chỉ sau khi đã có ≥2 index và số liệu đo lại |

---

## 13. Những gì **không** đề xuất

- ❌ Không OCR toàn bộ 80 CTĐT ngay (406 MB, phần lớn là bảng scan) — chỉ làm khóa 2024–2028 trước.
- ❌ Không nạp 14 thông báo (`gdct*`, `tbc*`) và cẩm nang 42 MB (gần như toàn ảnh).
- ❌ Không dùng LLM để "làm sạch" văn bản quy chế (rủi ro đổi con số); chỉ dùng regex, như `clean_md.py` đang làm.
- ❌ Không nhúng vector cho 97 biểu mẫu, **và không nạp nội dung mẫu** dưới bất kỳ hình thức nào.
- ❌ Không trả lời câu hỏi về nội dung/cách điền biểu mẫu — chỉ gợi ý mẫu + link (ĐX-6.2).
- ❌ Không bật `use_hybrid`/`use_rerank` mặc định — số đo ở Chương 5 cho thấy chưa có lợi trên quy mô này.

> **Xác nhận:** trong lần làm này chỉ có file tài liệu này được tạo; **không** file `.py`, `.yaml`, `.tex` nào bị sửa.
