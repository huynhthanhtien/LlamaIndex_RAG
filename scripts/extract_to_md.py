"""Trích văn bản từ data/raw sang Markdown trong data/ocr (cùng cấu trúc thư mục).

Mỗi trang PDF được lấy 2 bản: text layer (pdftotext) và OCR (Tesseract, model tessdata_best),
rồi giữ bản có tỷ lệ âm tiết tiếng Việt hợp lệ cao hơn. Text layer hỏng (dấu tách rời, font VNI)
hoặc trống sẽ tự rơi về OCR. File .docx đọc thẳng XML.

- Bỏ bản trùng nội dung theo sha256 trong data/raw/metadata_manifest.csv (chỉ xử lý 1 bản/nhóm).
- Không ghi đè file .md đã có (để giữ các bản sửa tay), trừ khi có --force.

Cách dùng:
    python scripts/extract_to_md.py data/raw/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc
    python scripts/extract_to_md.py <thư mục hoặc file> [--force] [--dpi 400]
"""
import argparse
import csv
import re
import subprocess
import sys
import time
import unicodedata
import zipfile
from datetime import date
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

import pytesseract  # pyright: ignore[reportMissingTypeStubs]
from pdf2image import convert_from_path  # pyright: ignore[reportUnknownVariableType]
from PIL.Image import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "ocr"
TESSDATA_BEST = Path.home() / ".local" / "share" / "tessdata_best"

# Âm tiết tiếng Việt: phụ âm đầu + vần (1-3 nguyên âm, có thể mang dấu) + phụ âm cuối
_V = "aàáảãạăằắẳẵặâầấẩẫậeèéẻẽẹêềếểễệiìíỉĩịoòóỏõọôồốổỗộơờớởỡợuùúủũụưừứửữựyỳýỷỹỵ"
SYLLABLE = re.compile(rf"^(ngh|ng|nh|ch|gh|gi|kh|ph|qu|th|tr|[bcdđghklmnpqrstvx])?[{_V}]{{1,3}}(ch|ng|nh|[cmnpt])?$")
WORD = re.compile(r"[^\W\d_]+")

Page = dict[str, Any]  # {"trang", "nguon", "diem", "diem_text", "diem_ocr", "text"}


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def quality(text: str) -> tuple[float, int]:
    """(tỷ lệ từ là âm tiết tiếng Việt hợp lệ, số từ). Text hỏng dấu/font cho tỷ lệ thấp."""
    words = [w.lower() for w in WORD.findall(nfc(text))]
    if not words:
        return 0.0, 0
    return sum(bool(SYLLABLE.match(w)) for w in words) / len(words), len(words)


def text_layer(pdf: Path, page: int) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, text=True, errors="replace",
    ).stdout
    # -layout giữ thụt lề bằng nhiều khoảng trắng: gom lại cho gọn, giữ xuống dòng
    return nfc("\n".join(re.sub(r"[ \t]{2,}", " ", line).strip() for line in out.splitlines()))


def ocr(image: Image, tess_config: str) -> str:
    text = pytesseract.image_to_string(image.convert("L"), lang="vie", config=tess_config)  # pyright: ignore[reportUnknownMemberType]
    return nfc(cast(str, text))


def clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\f", ""))
    return text.strip()


def extract_pdf(pdf: Path, dpi: int, tess_config: str) -> list[Page]:
    pages: list[Page] = []
    images: list[Image] = convert_from_path(str(pdf), dpi=dpi)
    for i, image in enumerate(images, start=1):
        t0 = time.time()
        layer, ocr_text = text_layer(pdf, i), ocr(image, tess_config)
        q_layer, n_layer = quality(layer)
        q_ocr, n_ocr = quality(ocr_text)
        # Ưu tiên text layer (chính xác tuyệt đối khi tốt); chỉ dùng OCR khi layer trống/kém rõ rệt
        use_layer = n_layer >= 0.8 * n_ocr and q_layer >= q_ocr - 0.01
        pages.append({
            "trang": i,
            "nguon": "text" if use_layer else "ocr",
            "diem": q_layer if use_layer else q_ocr,
            "diem_text": q_layer, "diem_ocr": q_ocr,
            "text": clean(layer if use_layer else ocr_text),
        })
        print(f"    trang {i}/{len(images)}: text={q_layer:.3f} ({n_layer} từ) ocr={q_ocr:.3f} ({n_ocr} từ)"
              f" -> {pages[-1]['nguon']} [{time.time() - t0:.1f}s]", flush=True)
    return pages


def extract_docx(path: Path) -> list[Page]:
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    body = ElementTree.fromstring(zipfile.ZipFile(path).read("word/document.xml")).find("w:body", ns)
    if body is None:
        return [{"trang": 1, "nguon": "docx", "diem": 0.0, "diem_text": 0.0, "diem_ocr": 0.0, "text": ""}]
    lines: list[str] = []
    for block in body:
        tag = block.tag.split("}")[1]
        if tag == "p":
            lines.append("".join(t.text or "" for t in block.iter(f"{{{ns['w']}}}t")))
        elif tag == "tbl":  # bảng: mỗi hàng một dòng, ô cách nhau bằng " | "
            for row in block.iter(f"{{{ns['w']}}}tr"):
                cells = ["".join(t.text or "" for t in c.iter(f"{{{ns['w']}}}t")).strip() for c in row.iter(f"{{{ns['w']}}}tc")]
                lines.append(" | ".join(cells))
    text = clean(nfc("\n".join(lines)))
    q, _ = quality(text)
    return [{"trang": 1, "nguon": "docx", "diem": q, "diem_text": q, "diem_ocr": 0.0, "text": text}]


def yaml_str(value: object) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_md(src: Path, row: dict[str, str], pages: list[Page], dups: list[str], dpi: int) -> Path:
    out = OUT / src.relative_to(RAW).with_suffix(".md")
    out.parent.mkdir(parents=True, exist_ok=True)
    n_ocr = sum(p["nguon"] == "ocr" for p in pages)
    avg = sum(p["diem"] for p in pages if p["text"]) / max(1, sum(bool(p["text"]) for p in pages))
    head = [
        "---",
        f"file_goc: {yaml_str(src.relative_to(RAW))}",
        f"sha256: {row.get('sha256', '')}",
        f"tieu_de: {yaml_str(row.get('tieu_de', ''))}",
        f"url: {yaml_str(row.get('url', ''))}",
        f"trung_noi_dung_voi: [{', '.join(yaml_str(d) for d in dups)}]",
        f"so_trang: {len(pages)}",
        f"trang_ocr: {n_ocr}",
        f"trang_text_layer: {sum(p['nguon'] == 'text' for p in pages)}",
        f"diem_chat_luong: {avg:.3f}",
        f"cong_cu: {yaml_str(f'pdftotext + tesseract {pytesseract.get_tesseract_version()} (tessdata_best vie, {dpi} dpi)')}",
        f"ngay_trich: {date.today().isoformat()}",
        "da_sua_tay: false",
        "---",
        "",
    ]
    body = [f"## Trang {p['trang']} (nguon: {p['nguon']}, diem: {p['diem']:.3f})\n\n{p['text']}\n" for p in pages]
    out.write_text("\n".join(head) + "\n".join(body), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", type=Path, help="thư mục hoặc file trong data/raw")
    ap.add_argument("--force", action="store_true", help="ghi đè file .md đã có")
    ap.add_argument("--dpi", type=int, default=400)
    args = ap.parse_args()

    if not (TESSDATA_BEST / "vie.traineddata").exists():
        sys.exit(f"Thiếu {TESSDATA_BEST}/vie.traineddata (tải từ github.com/tesseract-ocr/tessdata_best)")
    tess_config = f"--tessdata-dir {TESSDATA_BEST} --oem 1 --psm 3 -c preserve_interword_spaces=0"

    target = args.target.resolve()
    manifest = {r["file"]: r for r in csv.DictReader(open(RAW / "metadata_manifest.csv", encoding="utf-8"))}
    files = sorted(p for p in ([target] if target.is_file() else target.rglob("*")) if p.suffix.lower() in {".pdf", ".docx"})

    done_hashes: dict[str, Path] = {}
    t_all = time.time()
    for src in files:
        rel = str(src.relative_to(RAW))
        row = manifest.get(rel, {})
        sha = row.get("sha256", "")
        if sha and sha in done_hashes:
            print(f"BỎ (trùng với {done_hashes[sha].name}): {rel}")
            continue
        done_hashes[sha] = src
        out = OUT / src.relative_to(RAW).with_suffix(".md")
        if out.exists() and not args.force:
            print(f"BỎ (đã có .md, dùng --force để chạy lại): {rel}")
            continue
        print(f"XỬ LÝ: {rel}", flush=True)
        t0 = time.time()
        pages = extract_pdf(src, args.dpi, tess_config) if src.suffix.lower() == ".pdf" else extract_docx(src)
        dups = [d for d in row.get("trung_noi_dung_voi", "").split(";") if d]
        out = write_md(src, row, pages, dups, args.dpi)
        print(f"  -> {out.relative_to(ROOT)} ({sum(len(p['text']) for p in pages)} ký tự, {time.time() - t0:.0f}s)", flush=True)
    print(f"Xong sau {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()
