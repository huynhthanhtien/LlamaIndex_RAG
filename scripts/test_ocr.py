import sys
from pathlib import Path

import pytesseract
from pdf2image import convert_from_path


def ocr_full_to_md(pdf_path: str, dpi: int = 300, output_dir: str = "data/ocr"):
    path = Path(pdf_path)
    if not path.exists():
        print(f"[LỖI] Không tìm thấy file: {pdf_path}")
        sys.exit(1)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / f"{path.stem}.md"

    print(f"Đang render {pdf_path} thành ảnh (dpi={dpi})...")
    pages = convert_from_path(str(path), dpi=dpi)
    print(f"File có {len(pages)} trang. Đang OCR toàn bộ...\n")

    tong_ky_tu = 0
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# OCR: {path.name}\n\n")
        f.write(f"Tổng số trang: {len(pages)}\n\n---\n\n")

        for i, page in enumerate(pages, start=1):
            print(f"  Đang OCR trang {i}/{len(pages)}...")
            text = pytesseract.image_to_string(page, lang="vie")
            tong_ky_tu += len(text)

            f.write(f"## Trang {i} ({len(text)} ký tự)\n\n")
            f.write(text.strip() + "\n\n---\n\n")

    print(f"\nHoàn tất. Tổng {tong_ky_tu} ký tự, trung bình {tong_ky_tu // len(pages)} ký tự/trang.")
    print(f"Đã lưu vào: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cách dùng: python3 scripts/test_ocr.py <đường_dẫn_pdf>")
        sys.exit(1)

    ocr_full_to_md(sys.argv[1])