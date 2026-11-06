# 100 đề tài code rút từ dự án

Mỗi đề tài là một yêu cầu viết code; đáp án là đoạn code **trích nguyên văn** từ repo (commit `08bdea5`, kèm số dòng) bằng script, không gõ lại. Khi trình bày: mở đúng file và dòng, chạy được, giải thích được từng dòng. Số dòng đúng tại commit trên; code đổi thì số dòng có thể lệch.

## A. Dữ liệu và OCR

### 1. Tính chỉ số chất lượng OCR: tỷ lệ từ là âm tiết tiếng Việt hợp lệ

`scripts/extract_to_md.py`: quality (dòng 48–53). Dùng để chọn bản scan tốt hơn; QĐ 3183 thấp nhất (94,9%).

```python
def quality(text: str) -> tuple[float, int]:
    """(tỷ lệ từ là âm tiết tiếng Việt hợp lệ, số từ). Text hỏng dấu/font cho tỷ lệ thấp."""
    words = [w.lower() for w in WORD.findall(nfc(text))]
    if not words:
        return 0.0, 0
    return sum(bool(SYLLABLE.match(w)) for w in words) / len(words), len(words)
```

### 2. Lấy lớp văn bản của một trang PDF bằng pdftotext

`scripts/extract_to_md.py`: text_layer (dòng 56–62). Gom khoảng trắng do -layout sinh ra, chuẩn hóa NFC.

```python
def text_layer(pdf: Path, page: int) -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True, text=True, errors="replace",
    ).stdout
    # -layout giữ thụt lề bằng nhiều khoảng trắng: gom lại cho gọn, giữ xuống dòng
    return nfc("\n".join(re.sub(r"[ \t]{2,}", " ", line).strip() for line in out.splitlines()))
```

### 3. OCR một trang ảnh bằng Tesseract tiếng Việt

`scripts/extract_to_md.py`: ocr (dòng 65–67)

```python
def ocr(image: Image, tess_config: str) -> str:
    text = pytesseract.image_to_string(image.convert("L"), lang="vie", config=tess_config)  # pyright: ignore[reportUnknownMemberType]
    return nfc(cast(str, text))
```

### 4. Trích một file PDF: dùng lớp văn bản nếu tốt, ngược lại OCR ở 300 dpi

`scripts/extract_to_md.py`: extract_pdf (dòng 75–94)

```python
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
```

### 5. Trích văn bản từ file .docx mà không cần thư viện ngoài

`scripts/extract_to_md.py`: extract_docx (dòng 97–113). Đọc word/document.xml trong file zip.

```python
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
```

### 6. Ghi Markdown tầng 1 kèm front matter (file gốc, sha256, chất lượng)

`scripts/extract_to_md.py`: write_md (dòng 120–144)

```python
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
```

### 7. Kiểm tra nhanh một PDF có lớp văn bản hay là bản scan

`src/ingestion.py`: has_text_layer (dòng 23–31)

```python
def has_text_layer(pdf_path: str, min_chars: int = 50) -> bool:
    """Kiểm tra nhanh một PDF có text layer hay là bản scan thuần ảnh."""
    from llama_index.core import SimpleDirectoryReader
    try:
        docs = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
        return sum(len(d.text) for d in docs) >= min_chars
    except Exception as e:
        logger.warning(f"Không đọc thử được {pdf_path}: {e}")
        return False
```

### 8. Nạp PDF scan thành Document bằng OCR (cách làm tuần 3)

`src/ingestion.py`: load_scanned_pdf (dòng 34–76). Mỗi trang một Document; đã thay bằng Markdown hai tầng.

```python
def load_scanned_pdf(pdf_path: str, source_name: str, lang: str = "vie", dpi: int = 300) -> list[Document]:
    path = Path(pdf_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise ScannedPDFLoadError(f"Không tìm thấy file: {pdf_path}")

    logger.info(f"Bắt đầu OCR: {pdf_path} (nguồn: {source_name})")

    try:
        pages = convert_from_path(str(path), dpi=dpi)
    except Exception as e:
        raise ScannedPDFLoadError(f"Lỗi khi render PDF thành ảnh ({pdf_path}): {e}") from e

    documents: list[Document] = []
    failed_pages: list[int] = []

    for i, page in enumerate(pages, start=1):
        try:
            text = pytesseract.image_to_string(page, lang=lang)
        except Exception as e:
            logger.error(f"OCR lỗi ở trang {i} của {pdf_path}: {e}")
            failed_pages.append(i)
            text = ""

        documents.append(Document(
            text=text,
            metadata={"nguon": source_name, "trang": i, "file_goc": path.name},
        ))

    if failed_pages:
        logger.warning(f"{len(failed_pages)}/{len(pages)} trang OCR lỗi: {failed_pages}")

    total_chars = sum(len(d.text) for d in documents)
    logger.info(f"Hoàn tất OCR {path.name}: {len(documents)} trang, tổng {total_chars} ký tự")

    if total_chars < 100:
        logger.warning(
            f"Tổng ký tự OCR rất thấp ({total_chars}) cho {pdf_path} — "
            "kiểm tra chất lượng bản scan hoặc gói ngôn ngữ 'vie'."
        )

    return documents
```

### 9. Nhận dạng dòng tiêu đề viết hoa

`scripts/clean_md.py`: is_caps_title (dòng 68–70)

```python
def is_caps_title(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 6 and sum(c.isupper() for c in letters) / len(letters) > 0.85
```

### 10. Làm sạch một trang OCR: bỏ số trang, khối quốc hiệu

`scripts/clean_md.py`: clean_page (dòng 73–102)

```python
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
        if HEADER.search(lines[idx]) and not TABLE_ROW.match(lines[idx]):  # "|---|" của bảng khớp ^[\W_]{3,}$
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
```

### 11. Nối các dòng bị ngắt thành đoạn văn, giữ nguyên bảng Markdown

`scripts/clean_md.py`: join_lines (dòng 105–137)

```python
def join_lines(lines: list[str], stats: dict[str, int]) -> list[str]:
    paras: list[str] = []
    blank_before = False
    for line in lines:
        if not line:
            blank_before = True
            continue
        # Bảng Markdown (chép tay ở tầng 1): các dòng "|" liền nhau giữ nguyên thành một khối, không nối với văn xuôi
        if TABLE_ROW.match(line):
            if paras and TABLE_ROW.match(paras[-1].split("\n")[-1]) and not blank_before:
                paras[-1] += "\n" + line
            else:
                paras.append(line)
            blank_before = False
            continue
        line = re.sub(r"^([“\"]?)(\d{1,2}),\s+(?=[A-ZĐÀ-Ỹ])", r"\1\2. ", line)  # "2, Kế hoạch" -> "2. Kế hoạch"
        if paras and not TABLE_ROW.match(paras[-1].split("\n")[-1]):
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
```

### 12. Tách Quyết định ban hành khỏi văn bản chính khi số Điều bắt đầu lại từ 1

`scripts/clean_md.py`: split_parts (dòng 140–158)

```python
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
```

### 13. Dựng lại heading Markdown (#, ##, ###, ####) cho văn bản quy chế

`scripts/clean_md.py`: to_markdown (dòng 174–194)

```python
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
```

### 14. Kiểm tra số Điều thiếu hoặc trùng sau khi làm sạch

`scripts/clean_md.py`: check (dòng 197–219)

```python
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
```

### 15. Đọc file metadata CSV, tạo mẫu nếu chưa có

`scripts/clean_md.py`: load_metadata (dòng 222–234)

```python
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
```

### 16. Đặt tên file không dấu (slug) cho văn bản

`scripts/reorganize_raw.py`: slugify (dòng 159–164)

```python
def slugify(text: str, max_len: int = 70) -> str:
    text = re.sub(r"^\s*(?:[\d.]+\s*|[>\-]\s*)", "", " ".join(text.split()))  # bỏ "5. ", "> ", "- "
    text = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_len].rsplit("-", 1)[0] if len(text) > max_len else text
```

### 17. Sửa tên file bị lỗi mã hóa (mojibake)

`scripts/reorganize_raw.py`: fix_mojibake (dòng 167–172)

```python
def fix_mojibake(name: str) -> str:
    try:
        name = name.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass  # tên đã là UTF-8 đúng
    return unicodedata.normalize("NFC", name)
```

## B. Chia Node và metadata

### 18. Khai báo các hằng của loader: ngưỡng cắt, phiên bản loader, regex heading

`src/processed_loader.py`: MAX_TU (dòng 34–34), MIN_TU_NOI_DUNG (dòng 35–35), LOADER_VERSION (dòng 36–36), KHONG_LLM (dòng 42–42), KHONG_EMBED (dòng 44–44), HEADING (dòng 48–48), SO_DIEU (dòng 50–50), _splitter (dòng 53–53)

```python
MAX_TU = 1024  # Điều dài hơn MAX_TU từ thì cắt nhỏ, như node_parser.parse_by_dieu

MIN_TU_NOI_DUNG = 30  # chữ nằm ngay dưới "#"/"##" (không thuộc Điều nào) ngắn hơn thì bỏ (tiêu đề, dòng trích yếu)

LOADER_VERSION = "processed_loader/3"  # đổi khi cách cắt hoặc schema metadata thay đổi

KHONG_LLM = ["file", "file_goc", "url", "phan", *QUAN_HE, *KHOA_AP_DUNG]

KHONG_EMBED = ["file", "file_goc", "url", "phan", "chuong", "dieu", "sua_doi_dieu", "van_ban"]

HEADING = re.compile(r"(?m)^(?=#{1,4} )")

SO_DIEU = re.compile(r"Điều (\d+)")

_splitter = SentenceSplitter(chunk_size=MAX_TU, chunk_overlap=50)  # 1024 / 50 token tiktoken (xem MAX_TU)
```

### 19. Tách front matter YAML đầu file Markdown

`src/processed_loader.py`: front_matter (dòng 56–64)

```python
def front_matter(text: str) -> tuple[dict[str, str], str]:
    """Tách khối "---" đầu file thành dict và phần thân."""
    # File bắt đầu bằng "---\n", nên phần tử đầu (trước dấu "---" thứ nhất) rỗng, bỏ qua;
    # maxsplit=2 để các "---" trong thân văn bản (vd kẻ ngang) không bị cắt tiếp
    _, front, body = text.split("---\n", 2)
    # Front matter dạng "khoa: gia_tri" mỗi dòng; chỉ tách ở ": " đầu tiên vì giá trị có thể chứa ": "
    pairs = (line.split(": ", 1) for line in front.strip().splitlines() if ": " in line)
    # Bỏ ngoặc kép bao quanh giá trị (YAML kiểu "..."); giá trị JSON như '["a", "b"]' giữ nguyên vì không bắt đầu bằng '"'
    return {k: v.strip().strip('"') for k, v in pairs}, body
```

### 20. Chuyển danh sách số hiệu (JSON) thành chuỗi cho metadata

`src/processed_loader.py`: danh_sach_so_hieu (dòng 67–75)

```python
def danh_sach_so_hieu(gia_tri: str) -> str:
    """'["2451/TB-ĐHSG", "2567/TB-ĐHSG"]' -> "2451/TB-ĐHSG; 2567/TB-ĐHSG" (metadata Node giữ kiểu chuỗi)."""
    try:
        ds = json.loads(gia_tri)
    except json.JSONDecodeError:
        # Không phải JSON (ghi tay một số hiệu trần) -> dùng nguyên chuỗi
        return gia_tri.strip()
    # JSON hợp lệ nhưng là giá trị đơn (vd một chuỗi) cũng đổi về str
    return "; ".join(str(x) for x in ds) if isinstance(ds, list) else str(ds)
```

### 21. Đọc khóa áp dụng theo từng Điều của văn bản sửa đổi

`src/processed_loader.py`: khoa_theo_dieu (dòng 78–87)

```python
def khoa_theo_dieu(meta: dict[str, str]) -> dict[str, int]:
    """`ap_dung_khoa_tu_theo_dieu: {"9": 2025}` — văn bản sửa đổi mà mỗi Điều áp dụng từ khóa khác nhau
    (QĐ 3183 Điều 2: khoản 3–5, tức các mục sửa Điều 9 và 10, chỉ áp dụng từ khóa 2025)."""
    try:
        # Khóa không có hoặc rỗng -> coi như dict rỗng
        ds = json.loads(meta.get("ap_dung_khoa_tu_theo_dieu") or "{}")
    except json.JSONDecodeError:
        return {}
    # Chuẩn hóa: số Điều là str (khớp với metadata "dieu"), khóa là int (để so sánh với năm)
    return {str(k): int(v) for k, v in ds.items()} if isinstance(ds, dict) else {}
```

### 22. Sinh nhãn nguồn trích dẫn cho Node

`src/processed_loader.py`: nguon_trich (dòng 90–100)

```python
def nguon_trich(meta: dict[str, str | int]) -> str:
    """Một dòng tiếng Việt mô tả Node, dùng làm ngữ cảnh khi embedding."""
    # Thứ tự ưu tiên: mục sửa đổi > Điều > phần ban hành > tên văn bản / tên file.
    # .strip(" —") bỏ " — " thừa ở cuối khi không có tên văn bản
    if meta.get("sua_doi_dieu"):
        return f"Sửa đổi Điều {meta['sua_doi_dieu']} — {meta.get('van_ban', '')}".strip(" —")
    if meta.get("dieu"):
        return f"Điều {meta['dieu']} — {meta.get('van_ban', '')}".strip(" —")
    if meta.get("phan") == "ban_hanh":
        return f"Phần ban hành — {meta.get('van_ban', '')}".strip(" —")
    return str(meta.get("van_ban") or meta.get("file") or "")
```

### 23. Gắn metadata đã lọc rỗng và chọn trường nào vào embedding / prompt

`src/processed_loader.py`: _gan_metadata (dòng 103–113). Chỉ nguon_trich được embed.

```python
def _gan_metadata(node: TextNode, meta: dict[str, str | int]) -> TextNode:
    """Gắn metadata đã lọc rỗng + `nguon_trich`, và đặt đúng trường nào được embed / vào prompt."""
    # Bỏ các khóa có giá trị rỗng / chỉ khoảng trắng (str(v) để xử lý cả giá trị int)
    sach = {k: v for k, v in meta.items() if str(v).strip()}
    sach["nguon_trich"] = nguon_trich(sach)
    node.metadata = sach
    # Embedding: loại MỌI khóa trừ `nguon_trich` (rộng hơn KHONG_EMBED, để khóa mới thêm sau này cũng không lọt vào vector)
    node.excluded_embed_metadata_keys = [k for k in sach if k != "nguon_trich"]
    # Prompt LLM: chỉ loại các khóa kỹ thuật / lọc phiên bản; van_ban, chuong, dieu... vẫn hiện cho LLM trích dẫn
    node.excluded_llm_metadata_keys = [k for k in KHONG_LLM if k in sach]
    return node
```

### 24. Cắt file Markdown tầng 2 thành TextNode theo Điều

`src/processed_loader.py`: load_processed (dòng 116–185)

```python
def load_processed(path: Path, ten_hien_thi: str = "") -> list[TextNode]:
    """ten_hien_thi: tên văn bản dùng cho embedding / trích nguồn; rỗng thì lấy heading "#" (tiêu đề OCR)."""
    meta, body = front_matter(path.read_text(encoding="utf-8"))
    # Ưu tiên tên cấu hình trong cfg.ten_van_ban, rồi đến `ten_van_ban` trong front matter
    ten_van_ban = ten_hien_thi or meta.get("ten_van_ban", "")
    nodes: list[TextNode] = []
    # Trạng thái heading hiện tại khi duyệt tuần tự: "#" gần nhất và "##" gần nhất
    van_ban = chuong = ""
    for block in HEADING.split(body):
        if not block.strip():
            continue
        # Dòng đầu là heading, phần còn lại là nội dung của heading đó
        head, _, rest = block.partition("\n")
        # Số dấu "#" đầu dòng = cấp heading (1..4)
        level = len(head) - len(head.lstrip("#"))
        title = head.lstrip("# ").strip()
        if level == 1:
            # Sang văn bản mới (vd "Quyết định ban hành" rồi đến quy chế kèm theo) -> reset Chương
            van_ban, chuong = title, ""
        elif level == 2:
            chuong = title
        if level <= 2:
            # Văn bản không chia Điều (vd quy định 1 trang) có toàn bộ nội dung ngay dưới "#"
            if len(rest.split()) < MIN_TU_NOI_DUNG:
                continue
            phan = "ban_hanh" if van_ban == "Quyết định ban hành" else "noi_dung"
            m = None  # heading "#"/"##" không mang số Điều
        else:
            # Điều ngắn có thể nằm trọn trên dòng heading (rest rỗng) — vẫn tạo Node
            m = SO_DIEU.search(title)
            # "###" là Điều của văn bản chính, "####" là mục sửa đổi Điều của văn bản khác
            phan = "ban_hanh" if van_ban == "Quyết định ban hành" else ("sua_doi" if level == 4 else "chinh")
        node_meta: dict[str, str | int] = {
            # Có tên cấu hình: phần ban hành ghi "Quyết định ban hành – <tên>", phần còn lại chỉ ghi <tên>;
            # không có tên cấu hình: dùng heading "#" hiện tại
            "van_ban": (f"{van_ban} – {ten_van_ban}" if phan == "ban_hanh" else ten_van_ban) if ten_van_ban else van_ban,
            "chuong": chuong,
            # Số Điều đi vào "dieu" (Điều của chính văn bản) hoặc "sua_doi_dieu" (Điều bị sửa), tùy cấp heading
            "dieu": m[1] if (m and level == 3) else "",
            "sua_doi_dieu": m[1] if (m and level == 4) else "",
            "phan": phan,
            "file": path.name,
            "file_goc": meta.get("file_goc", ""),
            "url": meta.get("url", ""),
        }
        # front matter của clean_md.py có thể bổ sung các khóa này; chỉ nhận nếu có giá trị
        for khoa in ("so_hieu", "ngay_ban_hanh", "tinh_trang", "nhom"):
            if meta.get(khoa):
                node_meta[khoa] = meta[khoa]
        # Quan hệ sửa đổi / thay thế: list JSON -> chuỗi "a; b" (metadata vector store không nhận list lồng)
        for khoa in QUAN_HE:
            if meta.get(khoa):
                node_meta[khoa] = danh_sach_so_hieu(meta[khoa])
        # Khóa áp dụng cấp văn bản: chỉ nhận khi là số (năm), lưu int để phien_ban.py so sánh
        for khoa in KHOA_AP_DUNG:
            if meta.get(khoa, "").isdigit():
                node_meta[khoa] = int(meta[khoa])
        # Khóa áp dụng riêng theo Điều (nếu có) ghi đè khóa áp dụng chung của văn bản
        dieu_node = str(node_meta["sua_doi_dieu"] or node_meta["dieu"])
        if dieu_node in khoa_theo_dieu(meta):
            node_meta["ap_dung_khoa_tu"] = khoa_theo_dieu(meta)[dieu_node]
        # Giữ tiêu đề trong text để Node tự đủ nghĩa ("Điều 9. Xét tuyển\n...")
        text = f"{title}\n{rest.strip()}"
        # Điều vừa đủ ngắn -> 1 Node; dài quá thì cắt thành nhiều đoạn chung metadata
        chunks = [text] if len(text.split()) <= MAX_TU else _splitter.split_text(text)
        for j, chunk in enumerate(chunks, start=1):
            # "phan_doan" (1, 2, ...) chỉ thêm khi Điều bị cắt, để phân biệt các đoạn của cùng một Điều
            node = TextNode(text=chunk, metadata=node_meta | ({"phan_doan": j} if len(chunks) > 1 else {}))
            nodes.append(_gan_metadata(node, node.metadata))
    return nodes
```

### 25. Liệt kê file corpus theo danh sách tiền tố cấu hình

`src/processed_loader.py`: corpus_files (dòng 188–202)

```python
def corpus_files(cfg: RAGConfig) -> list[Path]:
    """File .md trong cfg.corpus_dir (kể cả thư mục con) được nạp: khớp tiền tố tên file trong cfg.corpus_files (rỗng = tất cả)."""
    folder = ROOT / cfg.corpus_dir
    if not folder.is_dir():
        raise FileNotFoundError(f"Không thấy {cfg.corpus_dir} — chạy scripts/extract_to_md.py rồi scripts/clean_md.py")
    # File bắt đầu bằng "_" (ghi chú, file phụ) không phải văn bản -> bỏ; sorted để thứ tự Node ổn định giữa các lần chạy
    files = sorted(p for p in folder.rglob("*.md") if not p.name.startswith("_"))
    if cfg.corpus_files:
        # str.startswith nhận tuple -> khớp bất kỳ tiền tố nào trong danh sách
        files = [p for p in files if p.name.startswith(cfg.corpus_files)]
        # Báo lỗi sớm nếu có tiền tố cấu hình sai / file chưa sinh, tránh âm thầm index thiếu văn bản
        thieu = [t for t in cfg.corpus_files if not any(p.name.startswith(t) for p in files)]
        if thieu:
            raise FileNotFoundError(f"corpus_files không khớp file nào trong {cfg.corpus_dir}: {thieu}")
    return files
```

### 26. Tìm số dòng bắt đầu của một Node trong file gốc

`src/processed_loader.py`: dong_bat_dau (dòng 210–232)

```python
def dong_bat_dau(path: Path, text: str) -> int | None:
    """Số dòng (đếm từ 1) trong file tầng 2 nơi đoạn `text` của một Node bắt đầu; None nếu không tìm thấy.

    Node giữ tiêu đề ở dòng đầu (đã bỏ "#"). Một file có thể có hai heading trùng chữ (Điều 1 của quyết định ban hành
    và Điều 1 của quy chế kèm theo), nên khi có dòng thứ hai thì phải khớp cả dòng nội dung ngay sau heading.
    Đoạn thứ 2 trở đi của một Điều bị cắt không bắt đầu bằng heading (SentenceSplitter có thể cắt giữa dòng): tìm dòng
    chứa đầu đoạn, nhiều dòng cùng chứa thì chọn dòng có dòng kế tiếp khớp dòng thứ hai của đoạn.
    """
    dong_node = [x.strip() for x in text.splitlines() if x.strip()]
    if not dong_node:
        return None
    dong_file = path.read_text(encoding="utf-8").splitlines()

    def sau(i: int) -> str:
        return next((y.strip() for y in dong_file[i + 1:] if y.strip()), "")

    for i, x in enumerate(dong_file):
        if x.lstrip("#").strip() == dong_node[0] and (len(dong_node) < 2 or sau(i) == dong_node[1]):
            return i + 1
    ung_vien = [i for i, x in enumerate(dong_file) if dong_node[0][:60] in x]
    if len(ung_vien) > 1 and len(dong_node) > 1:
        ung_vien = [i for i in ung_vien if dong_node[1][:60] in sau(i)] or ung_vien
    return ung_vien[0] + 1 if ung_vien else None
```

### 27. Trả về vị trí trích dẫn dạng file:dòng

`src/processed_loader.py`: vi_tri_goc (dòng 235–246)

```python
def vi_tri_goc(cfg: RAGConfig, meta: dict[str, object], text: str) -> str:
    """"data/processed/.../<file>.md:<dòng>" để mở đúng đoạn gốc của một Node trích dẫn (nhận xét tuần 7, ý 8).

    Mức truy nguồn là văn bản/Điều trong file tầng 2; số trang PDF không còn sau bước làm sạch nên không có ở đây
    (`file_goc` trong metadata chỉ tên PDF gốc, không có trang).
    """
    ten = str(meta.get("file", ""))
    path = next((p for p in corpus_files(cfg) if p.name == ten), None)
    if path is None:
        return ten
    dong = dong_bat_dau(path, text)
    return f"{path.relative_to(ROOT)}" + (f":{dong}" if dong else "")
```

### 28. Thống kê chất lượng Node (số Node, Node không gắn được Điều)

`src/processed_loader.py`: thong_ke (dòng 254–266)

```python
def thong_ke(nodes: list[TextNode]) -> dict[str, object]:
    """Thống kê chất lượng Node — dùng cho báo cáo và cho kiểm thử tự động."""
    from collections import Counter

    theo_file = Counter(str(n.metadata.get("file")) for n in nodes)
    return {
        "tong_so_node": len(nodes),
        "so_van_ban": len(theo_file),
        # Node không gắn được số Điều (phần ban hành, văn bản không chia Điều...) — tăng bất thường là dấu hiệu cắt sai
        "node_khong_ro_dieu": sum(1 for n in nodes if not n.metadata.get("dieu") and not n.metadata.get("sua_doi_dieu")),
        "do_dai_trung_binh_ky_tu": round(sum(len(n.text) for n in nodes) / len(nodes)) if nodes else 0,
        "theo_file": dict(sorted(theo_file.items())),
    }
```

### 29. Lấy số Điều từ tiêu đề (bộ cắt cũ)

`src/node_parser.py`: extract_dieu_number (dòng 16–19)

```python
def extract_dieu_number(text: str) -> str:
    """Trích xuất số thứ tự của Điều từ đoạn văn bản (ví dụ: 'Điều 15.' -> '15')."""
    match = DIEU_NUMBER_PATTERN.match(text.strip())
    return match.group(1) if match else "khong_ro"
```

### 30. Cắt Document theo Điều bằng regex, Điều dài thì cắt tiếp (bộ cắt cũ)

`src/node_parser.py`: parse_by_dieu (dòng 23–70)

```python
def parse_by_dieu(documents: list[Document], max_chunk_tokens: int = 1024) -> list[TextNode]:
    """Phân tách danh sách Document thành các TextNode theo từng Điều.

    - Nếu một Điều dài hơn max_chunk_tokens, tiến hành sub-chunking bằng SentenceSplitter.
    - Giữ nguyên toàn bộ metadata gốc của Document và gắn thêm metadata['dieu'].
    - Trường hợp Document không có 'Điều', giữ nguyên toàn bộ và gắn dieu='khong_co_dieu'.
    """
    # khai báo số lượng token tối đa, chuck_overlap là chồng lấp tức là sẽ có một đoạn văn bản xuất hiện ở 2 node mục tiêu là không làm mất ngữ cảnh của văn bản khi nó quá dài, cắt ngang
    sub_splitter = SentenceSplitter(chunk_size=max_chunk_tokens, chunk_overlap=50)
    all_nodes: list[TextNode] = []
    dieu_khong_khop = 0
    # điều đọc lạo bàng biểu thức re bên trên DIEU_PATTERN
    for doc in documents:
        # trả về danh sách diều trong document này 
        matches = DIEU_PATTERN.findall(doc.text)
        # if khôgn tìm tháy <==> danh sách rỗng 
        if not matches:
            dieu_khong_khop += 1
            all_nodes.append(
                TextNode(
                    text=doc.text.strip(),
                    metadata={"dieu": "khong_co_dieu", **doc.metadata},
                )
            )
            continue
        # tách nội dung text theo điều X 
        for dieu_text in matches:
            dieu_so = extract_dieu_number(dieu_text)
            base_metadata = {"dieu": dieu_so, **doc.metadata}
            estimated_tokens = len(dieu_text.split())
            # nếu đội dài <= max_chunk_tokens thì sẽ được lưu thành 1 node 
            # nguợc lại dữ liệu quá dài không lưu được một node thì sẽ chia ra nhiều phần, thêm metadata để nhận biết 
            if estimated_tokens <= max_chunk_tokens:
                all_nodes.append(TextNode(text=dieu_text.strip(), metadata=base_metadata))
            else:
                sub_texts = sub_splitter.split_text(dieu_text)
                for j, sub_text in enumerate(sub_texts):
                    all_nodes.append(
                        TextNode(
                            text=sub_text,
                            metadata={**base_metadata, "phan": j + 1},
                        )
                    )
    # log văn bản này có cấu trúc theo điều
    if dieu_khong_khop:
        logger.warning(f"{dieu_khong_khop} Document không khớp mẫu 'Điều X'.")

    return all_nodes
```

### 31. Thống kê kết quả cắt của bộ cắt cũ

`src/node_parser.py`: validate_nodes (dòng 73–83)

```python
def validate_nodes(nodes: list[TextNode]) -> dict[str, Any]:
    """Thống kê định lượng chất lượng của danh sách TextNode sau khi parse."""
    total = len(nodes)
    khong_ro = sum(1 for n in nodes if n.metadata.get("dieu") in ("khong_ro", "khong_co_dieu"))
    avg_len = sum(len(n.text) for n in nodes) // max(total, 1)
    return {
        "tong_so_node": total,
        "node_khong_ro_dieu": khong_ro,
        "ty_le_khong_ro": f"{khong_ro / max(total, 1):.1%}",
        "do_dai_trung_binh_ky_tu": avg_len,
    }
```

## C. Cấu hình, embedding và chỉ mục

### 32. Chọn thiết bị: tự hạ về CPU khi không có CUDA

`src/config.py`: resolve_device (dòng 21–38)

```python
def resolve_device(device: str) -> str:
    """Trả về thiết bị chạy được: giữ 'cuda' nếu GPU dùng được, ngược lại 'cpu'.

    Trước đây hai profile đặt cứng embed_device='cuda', nên máy không có driver
    NVIDIA (hoặc CI không GPU) lỗi ngay khi nạp model. Hàm này cho phép suy giảm
    mềm và vẫn ghi log để không âm thầm chạy sai thiết bị.
    """
    if device != "cuda":
        return device
    try:
        import torch
    except ImportError:  # torch chưa cài -> chắc chắn không có GPU
        logger.warning("Không import được torch — chuyển thiết bị sang CPU")
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    logger.warning("CUDA không khả dụng — chuyển thiết bị sang CPU")
    return "cpu"
```

### 33. Dataclass cấu hình RAG tập trung

`src/config.py`: RAGConfig (dòng 41–131)

```python
@dataclass
class RAGConfig:
    # --- Profile (tách thư mục index: mỗi model embedding có số chiều riêng) ---
    name: str

    # --- Embedding ---
    embed_model_name: str
    embed_device: str  # "cpu" hoặc "cuda" (qua resolve_device() để tự hạ cấp)

    # --- LLM ---
    llm_model_name: str
    ollama_base_url: str
    request_timeout: float = 180.0
    temperature: float = 0.0  # 0 = tất định; trước đây không đặt nên câu trả lời đổi giữa các lần hỏi
    seed: int = 42            # truyền xuống Ollama qua additional_kwargs
    thinking: bool = False    # chế độ suy luận của qwen3: đúng hơn khi tra bảng số, chậm ~4 lần (RAG_THINKING=1)

    # --- Thiết bị ---
    use_fp16: bool = False  # nạp embedding + reranker ở fp16 (chỉ khi cuda) để vừa GPU 4 GB

    # --- Reranker (tuỳ chọn) ---
    # Kết luận cũ "rerank làm giảm Recall@1" là do SentenceTransformerRerank cắt cứng 512 token: 28% Node (bảng,
    # Điều dài) bị mất đúng đoạn cần tìm. Đọc 2048 token thì rerank top-3 tăng câu trả lời đúng 75,6% -> 86,7%
    # (eval/results/logs/2026-10-13_dot2/15_rerank_va_cau_tra_loi.md); profile server bật mặc định.
    reranker_model_name: str | None = None
    reranker_top_n: int = 3
    reranker_max_length: int = 2048  # token tối đa mỗi cặp (câu hỏi, Node); model hỗ trợ 8192
    use_rerank: bool = False

    # --- Lọc phiên bản (src/phien_ban.py): bỏ văn bản hết hiệu lực, lọc theo khóa, đưa bản sửa đổi lên trước ---
    loc_phien_ban: bool = True

    # --- Model server (tuỳ chọn) — có URL thì gọi src/model_server.py thay vì nạp model tại chỗ ---
    model_server_url: str | None = field(default_factory=lambda: os.environ.get("MODEL_SERVER_URL") or None)

    # --- Retriever ---
    similarity_top_k: int = 10
    similarity_cutoff: float | None = None  # None = tắt; đặt >0 để bỏ Node dưới ngưỡng (K4)

    # --- Hybrid search: BM25 + vector, trộn bằng QueryFusionRetriever (K7) ---
    use_hybrid: bool = False
    bm25_top_k: int = 10
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    fusion_mode: str = "reciprocal_rerank"  # xem llama_index.core.retrievers.fusion_retriever.FUSION_MODES
    vector_weight: float = 1.0
    bm25_weight: float = 1.0

    # --- Response Synthesis ---
    response_mode: str = "compact"
    streaming: bool = True

    # --- Dữ liệu (tầng 2, sinh bởi scripts/clean_md.py) — sửa danh sách ở src/corpus.py ---
    corpus_dir: str = CORPUS_DIR
    corpus_files: tuple[str, ...] = tuple(SGU_HIEU_LUC)  # tiền tố tên file; rỗng = nạp hết
    ten_van_ban: dict[str, str] = field(default_factory=lambda: dict(SGU_HIEU_LUC))  # tiền tố -> tên hiển thị

    # --- Đường dẫn index; để trống = storage/<name>/<corpus> ---
    persist_dir: str = ""

    def __post_init__(self) -> None:
        if not self.persist_dir:
            corpus = PurePosixPath(self.corpus_dir).relative_to(PROCESSED_ROOT)
            self.persist_dir = f"storage/{self.name}/{corpus}"
        if "://" not in self.ollama_base_url:  # .env hay ghi thiếu, vd "1.2.3.4:11434"
            self.ollama_base_url = f"http://{self.ollama_base_url}"

    def mo_ta(self) -> dict[str, object]:
        """Tóm tắt cấu hình để ghi kèm vào kết quả đánh giá (tái lập được thí nghiệm)."""
        return {
            "profile": self.name,
            "embed_model": self.embed_model_name,
            "embed_device": self.embed_device,
            "llm_model": self.llm_model_name,
            "temperature": self.temperature,
            "seed": self.seed,
            "thinking": self.thinking,
            "similarity_top_k": self.similarity_top_k,
            "similarity_cutoff": self.similarity_cutoff,
            "use_rerank": bool(self.use_rerank and self.reranker_model_name),
            "reranker_model": self.reranker_model_name if self.use_rerank else None,
            "reranker_top_n": self.reranker_top_n,
            "reranker_max_length": self.reranker_max_length if self.use_rerank else None,
            "loc_phien_ban": self.loc_phien_ban,
            "use_hybrid": self.use_hybrid,
            "bm25_top_k": self.bm25_top_k if self.use_hybrid else None,
            "fusion_mode": self.fusion_mode if self.use_hybrid else None,
            "response_mode": self.response_mode,
            "corpus_dir": self.corpus_dir,
            "persist_dir": self.persist_dir,
        }
```

### 34. Khai báo hai profile local và server

`src/config.py`: CONFIG_LOCAL (dòng 136–143), CONFIG_SERVER (dòng 145–154), PROFILES (dòng 156–159)

```python
CONFIG_LOCAL = RAGConfig(
    name="local",
    embed_model_name="bkai-foundation-models/vietnamese-bi-encoder",
    embed_device=os.environ.get("RAG_EMBED_DEVICE", "cuda"),
    llm_model_name="qwen3:4b",
    ollama_base_url="http://localhost:11434",
    reranker_model_name=None,  # bỏ qua rerank khi test nhẹ cho nhanh
)

CONFIG_SERVER = RAGConfig(
    name="server",
    embed_model_name="AITeamVN/Vietnamese_Embedding",
    embed_device=os.environ.get("RAG_EMBED_DEVICE", "cuda"),
    use_fp16=True,
    llm_model_name="qwen3:8b",
    ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    reranker_model_name="AITeamVN/Vietnamese_Reranker",
    use_rerank=True,
)

PROFILES: dict[str, RAGConfig] = {
    "local": CONFIG_LOCAL,
    "server": CONFIG_SERVER,
}
```

### 35. Ghi đè cấu hình bằng biến môi trường

`src/config.py`: theo_moi_truong (dòng 162–182)

```python
def theo_moi_truong(cfg: RAGConfig) -> RAGConfig:
    """Bản sao của cfg có ghi đè từ biến môi trường RAG_* (ép từ môi trường khi máy không có GPU, khi so sánh...).

    Chỉ áp một lần ở get_config(). Trước đây phần này nằm trong __post_init__, mà dataclasses.replace() chạy lại
    __post_init__, nên mọi cấu hình ablation dựng bằng replace() trong eval/ bị ép theo RAG_RERANK /
    RAG_LOC_PHIEN_BAN của shell (cấu hình "vector" vẫn chạy rerank + lọc phiên bản).
    """
    thay: dict[str, object] = {}
    if os.environ.get("RAG_EMBED_DEVICE"):
        thay["embed_device"] = os.environ["RAG_EMBED_DEVICE"]
    if os.environ.get("RAG_SEED"):
        thay["seed"] = int(os.environ["RAG_SEED"])
    if os.environ.get("RAG_TEMPERATURE"):
        thay["temperature"] = float(os.environ["RAG_TEMPERATURE"])
    if os.environ.get("RAG_THINKING"):
        thay["thinking"] = os.environ["RAG_THINKING"] == "1"
    if os.environ.get("RAG_RERANK"):  # ép bật/tắt rerank khi so sánh (RAG_RERANK=0 = cấu hình cũ)
        thay["use_rerank"] = os.environ["RAG_RERANK"] == "1"
    if os.environ.get("RAG_LOC_PHIEN_BAN"):
        thay["loc_phien_ban"] = os.environ["RAG_LOC_PHIEN_BAN"] == "1"
    return dataclasses.replace(cfg, **thay)
```

### 36. Lấy cấu hình theo RAG_PROFILE, báo lỗi khi tên sai

`src/config.py`: get_config (dòng 185–196)

```python
def get_config() -> RAGConfig:
    """Lấy config theo profile đang chọn qua biến môi trường RAG_PROFILE.

    Trả về bản sao: sửa thuộc tính (vd `cfg.streaming = False`) không làm đổi profile dùng chung.
    """
    profile_name = os.environ.get("RAG_PROFILE", "local")
    if profile_name not in PROFILES:
        raise ValueError(
            f"RAG_PROFILE='{profile_name}' không hợp lệ. "
            f"Chỉ chấp nhận: {list(PROFILES.keys())}"
        )
    return theo_moi_truong(PROFILES[profile_name])
```

### 37. Nạp model embedding HuggingFace, có fp16 khi chạy CUDA

`src/index_builder.py`: make_local_embedding (dòng 29–37)

```python
def make_local_embedding(cfg: RAGConfig) -> HuggingFaceEmbedding:
    device = resolve_device(cfg.embed_device)
    fp16 = cfg.use_fp16 and device == "cuda"
    return HuggingFaceEmbedding(
        model_name=cfg.embed_model_name,
        device=device,
        embed_batch_size=4 if fp16 else 10,  # batch nhỏ để không tràn VRAM trên card 4 GB
        model_kwargs={"torch_dtype": torch.float16} if fp16 else {},
    )
```

### 38. Đặt Settings.embed_model: tại chỗ hoặc qua model server

`src/index_builder.py`: setup_embedding (dòng 40–52)

```python
def setup_embedding(cfg: RAGConfig) -> None:
    if cfg.model_server_url:
        from remote_models import RemoteEmbedding, check_server

        check_server(
            cfg.model_server_url, cfg.embed_model_name, cfg.reranker_model_name if cfg.use_rerank else None,
            cfg.reranker_max_length,
        )
        Settings.embed_model = RemoteEmbedding(
            base_url=cfg.model_server_url, model_name=cfg.embed_model_name, embed_batch_size=32
        )
    else:
        Settings.embed_model = make_local_embedding(cfg)
```

### 39. Tính fingerprint corpus để biết khi nào phải build lại index

`src/index_builder.py`: corpus_fingerprint (dòng 55–67)

```python
def corpus_fingerprint(cfg: RAGConfig) -> dict[str, object]:
    """Model embedding + phiên bản loader + sha256 và tên hiển thị từng file tầng 2.

    Trước đây fingerprint chỉ gồm tên model và nội dung file, nên sửa cách cắt Node trong
    processed_loader.py mà quên `--rebuild` sẽ dùng index cũ (bẫy đã ghi trong huong_dan_src.md).
    """
    files = {str(p.relative_to(ROOT / cfg.corpus_dir)): f"{hashlib.sha256(p.read_bytes()).hexdigest()} | {ten_hien_thi(cfg, p)}" for p in corpus_files(cfg)}
    return {
        "embed_model": cfg.embed_model_name,
        "corpus_dir": cfg.corpus_dir,
        "loader": {"phien_ban": LOADER_VERSION, "max_tu": MAX_TU, "min_tu_noi_dung": MIN_TU_NOI_DUNG},
        "files": files,
    }
```

### 40. Dựng hoặc nạp lại VectorStoreIndex (persist)

`src/index_builder.py`: build_or_load_index (dòng 70–96)

```python
def build_or_load_index(cfg: RAGConfig, rebuild: bool = False) -> VectorStoreIndex:
    setup_embedding(cfg)
    persist_dir = ROOT / cfg.persist_dir
    fingerprint = corpus_fingerprint(cfg)
    saved = persist_dir / FINGERPRINT
    # nếu không chọn rebuild sẽ load dữ liêu từ thư mục 
    if not rebuild and (persist_dir / "docstore.json").exists():
        # kiểm tra vân tay dữ liệu có khớp không
        # vân tay dữ liệu được tổng hợp từ cac tham số 
        if saved.exists() and json.loads(saved.read_text(encoding="utf-8")) == fingerprint:
            logger.info(f"Load Index từ {persist_dir}")
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(persist_dir)))
            assert isinstance(index, VectorStoreIndex)
            return index
        logger.warning("Corpus, model embedding hoặc loader đã đổi so với index đã lưu — build lại")
    # load model theo file cấu hình 
    nodes = load_corpus_nodes(cfg)
    # lấy thông tin file dữ liệu để nạp
    files = fingerprint["files"]
    assert isinstance(files, dict)
    logger.info(f"Build Index mới từ {len(nodes)} node ({len(files)} văn bản)")
    # load index từ vecoterStoreIndex đã lưu từ máy 
    index = VectorStoreIndex(nodes, show_progress=True)
    persist_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(persist_dir))
    saved.write_text(json.dumps(fingerprint, ensure_ascii=False, indent=1), encoding="utf-8")
    return index
```

## D. Model server và client từ xa

### 41. Nạp model embedding trên server

`src/model_server.py`: load_embedding (dòng 48–55)

```python
def load_embedding() -> HuggingFaceEmbedding:
    # Giữ giống make_local_embedding() trong src/index_builder.py
    return HuggingFaceEmbedding(
        model_name=EMBED_MODEL,
        device=DEVICE,
        embed_batch_size=4 if FP16 else 10,  # batch nhỏ để không tràn VRAM trên card 4 GB
        model_kwargs={"torch_dtype": torch.float16} if FP16 else {},
    )
```

### 42. Nạp reranker trên server, đặt độ dài 2 048 token và fp16

`src/model_server.py`: load_reranker (dòng 58–70)

```python
def load_reranker(model_name: str) -> SentenceTransformerRerank:
    # Giữ giống make_local_reranker() trong src/retriever.py
    rerank = SentenceTransformerRerank(model=model_name, device="cpu" if FP16 else DEVICE)
    # Như dat_do_dai_toi_da() trong src/retriever.py: sentence-transformers >= 5 dùng max_seq_length
    if isinstance(getattr(type(rerank._model), "max_seq_length", None), property):  # pyright: ignore[reportPrivateUsage]
        rerank._model.max_seq_length = RERANK_MAX_LENGTH  # pyright: ignore[reportPrivateUsage]
    else:
        rerank._model.max_length = RERANK_MAX_LENGTH  # pyright: ignore[reportPrivateUsage]
    if FP16:
        # SentenceTransformerRerank không nhận dtype: nạp trên CPU, ép fp16 rồi mới đưa lên GPU
        rerank._model.half().to(DEVICE)  # pyright: ignore[reportPrivateUsage]
        rerank.device = DEVICE
    return rerank
```

### 43. Kiểm tra token Bearer của request

`src/model_server.py`: check_token (dòng 82–84)

```python
def check_token(authorization: str | None = Header(default=None)) -> None:
    if TOKEN and not (authorization and secrets.compare_digest(authorization, f"Bearer {TOKEN}")):
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu token (header Authorization: Bearer ...)")
```

### 44. Endpoint /embed: embedding câu hỏi hoặc văn bản

`src/model_server.py`: embed (dòng 106–115)

```python
@app.post("/embed")
def embed(req: EmbedRequest) -> dict[str, list[list[float]]]:
    if embed_model is None:
        raise HTTPException(status_code=503, detail="Model embedding chưa nạp xong")
    with gpu_lock:
        if req.kind == "query":
            vectors = [embed_model.get_query_embedding(q) for q in req.texts]
        else:
            vectors = embed_model.get_text_embedding_batch(req.texts)
    return {"embeddings": vectors}
```

### 45. Endpoint /rerank: chấm điểm cặp (câu hỏi, đoạn văn)

`src/model_server.py`: rerank (dòng 118–124)

```python
@app.post("/rerank")
def rerank(req: RerankRequest) -> dict[str, list[float]]:
    if reranker is None:
        raise HTTPException(status_code=400, detail="Server không bật reranker (RERANK_MODEL rỗng)")
    with gpu_lock:
        scores = reranker._model.predict([(req.query, t) for t in req.texts])  # pyright: ignore[reportPrivateUsage]
    return {"scores": [float(s) for s in scores]}
```

### 46. Gọi model server có thử lại khi lỗi mạng tạm thời

`src/remote_models.py`: goi_server (dòng 30–44)

```python
def goi_server(method: str, url: str, timeout: float, json: dict[str, Any] | None = None) -> httpx.Response:
    """Gọi model server, thử lại khi lỗi mạng tạm thời hoặc mã 502/503/504/530 (chờ 1, 2, 4 giây)."""
    for lan in range(1, SO_LAN_THU + 1):
        try:
            r = httpx.request(method, url, json=json, headers=auth_headers(), timeout=timeout)
            if r.status_code not in MA_LOI_TAM_THOI or lan == SO_LAN_THU:
                return r.raise_for_status()
            loi = f"HTTP {r.status_code}"
        except httpx.TransportError as e:
            if lan == SO_LAN_THU:
                raise
            loi = f"{type(e).__name__}: {e}"
        logger.warning("Model server lỗi tạm thời (%s), thử lại lần %d/%d", loi, lan + 1, SO_LAN_THU)
        time.sleep(2 ** (lan - 1))
    raise AssertionError("không tới được")  # vòng lặp luôn return hoặc raise ở lần cuối
```

### 47. Kiểm tra server đang chạy đúng model của profile

`src/remote_models.py`: check_server (dòng 47–67)

```python
def check_server(
    base_url: str, embed_model_name: str, reranker_model_name: str | None, reranker_max_length: int | None = None
) -> None:
    """Server phải nạp đúng model của profile, nếu không vector sẽ lệch với index đã build.

    reranker_max_length: server cũ (trước 16/10) không trả khóa này và cắt Node ở 512 token -> báo lỗi
    thay vì âm thầm cho điểm rerank sai.
    """
    try:
        info = goi_server("GET", f"{base_url}/health", timeout=15).json()
    except httpx.HTTPError as e:
        raise RuntimeError(f"Không kết nối được model server {base_url}: {e}") from e
    if info["embed_model"] != embed_model_name:
        raise RuntimeError(f"Server đang chạy embedding {info['embed_model']!r}, config cần {embed_model_name!r}")
    if reranker_model_name and info["reranker_model"] != reranker_model_name:
        raise RuntimeError(f"Server đang chạy reranker {info['reranker_model']!r}, config cần {reranker_model_name!r}")
    if reranker_model_name and reranker_max_length and info.get("reranker_max_length") != reranker_max_length:
        raise RuntimeError(
            f"Reranker trên server đọc {info.get('reranker_max_length') or 512} token, config cần {reranker_max_length}. "
            "Chạy lại scripts/setup_server_v2.sh bản mới, hoặc bỏ MODEL_SERVER_URL để rerank trên máy."
        )
```

### 48. Lớp embedding gọi qua HTTP (BaseEmbedding của LlamaIndex)

`src/remote_models.py`: RemoteEmbedding (dòng 70–102)

```python
class RemoteEmbedding(BaseEmbedding):
    base_url: str
    timeout: float = 120.0

    @classmethod
    def class_name(cls) -> str:
        return "RemoteEmbedding"

    # kind = "query" | "text": server áp đúng prompt tương ứng như HuggingFaceEmbedding
    def _post(self, texts: list[str], kind: str) -> list[list[float]]:
        r = goi_server("POST", f"{self.base_url}/embed", self.timeout, json={"texts": texts, "kind": kind})
        return r.json()["embeddings"]

    async def _apost(self, texts: list[str], kind: str) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=auth_headers()) as client:
            r = await client.post(f"{self.base_url}/embed", json={"texts": texts, "kind": kind})
            r.raise_for_status()
            return r.json()["embeddings"]

    def _get_query_embedding(self, query: str) -> list[float]:
        return self._post([query], "query")[0]

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return (await self._apost([query], "query"))[0]

    def _get_text_embedding(self, text: str) -> list[float]:
        return self._post([text], "text")[0]

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self._post(texts, "text")  # 1 request cho cả batch thay vì từng câu

    async def _aget_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        return await self._apost(texts, "text")
```

### 49. Postprocessor rerank gọi qua HTTP

`src/remote_models.py`: RemoteRerank (dòng 105–127)

```python
class RemoteRerank(BaseNodePostprocessor):
    base_url: str
    top_n: int = 3
    timeout: float = 120.0

    @classmethod
    def class_name(cls) -> str:
        return "RemoteRerank"

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        if query_bundle is None:
            raise ValueError("Rerank cần câu hỏi (query_bundle).")
        if not nodes:
            return []
        # MetadataMode.EMBED giống SentenceTransformerRerank để reranker thấy cùng nội dung
        texts = [n.node.get_content(metadata_mode=MetadataMode.EMBED) for n in nodes]
        r = goi_server("POST", f"{self.base_url}/rerank", self.timeout,
                       json={"query": query_bundle.query_str, "texts": texts})
        for node, score in zip(nodes, r.json()["scores"], strict=True):
            node.score = score
        return sorted(nodes, key=lambda n: n.score or 0.0, reverse=True)[: self.top_n]
```

## E. Truy hồi, BM25 và rerank

### 50. Tạo retriever: vector top-k, hoặc hybrid với BM25 bằng QueryFusionRetriever

`src/retriever.py`: get_retriever (dòng 22–53)

```python
def get_retriever(index: VectorStoreIndex, cfg: RAGConfig) -> BaseRetriever:
    """Vector top-k; khi cfg.use_hybrid thì trộn thêm BM25 bằng QueryFusionRetriever."""
    vector = index.as_retriever(similarity_top_k=cfg.similarity_top_k)
    if not cfg.use_hybrid:
        return vector

    from llama_index.core.retrievers import QueryFusionRetriever
    from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
    from llama_index.llms.ollama import Ollama

    from bm25 import BM25Retriever

    nodes = list(index.docstore.docs.values())
    bm25 = BM25Retriever(
        nodes=nodes,
        similarity_top_k=cfg.bm25_top_k,
        k1=cfg.bm25_k1,
        b=cfg.bm25_b,
    )
    logger.info("Hybrid: vector top-%d + BM25 top-%d, fusion=%s", cfg.similarity_top_k, cfg.bm25_top_k, cfg.fusion_mode)
    return QueryFusionRetriever(
        retrievers=[vector, bm25],
        mode=FUSION_MODES(cfg.fusion_mode),
        similarity_top_k=cfg.similarity_top_k,
        num_queries=1,  # 1 = không gọi LLM sinh truy vấn phụ, giữ phép đo tất định
        use_async=False,
        retriever_weights=[cfg.vector_weight, cfg.bm25_weight],
        # QueryFusionRetriever.__init__ làm `llm if llm else Settings.llm`, mà Settings.llm mặc định
        # là OpenAI -> ImportError nếu chưa cài llama-index-llms-openai. Vì num_queries=1 nên LLM
        # không bao giờ được gọi; truyền vào chỉ để tránh việc thư viện đi resolve LLM mặc định.
        llm=Ollama(model=cfg.llm_model_name, base_url=cfg.ollama_base_url, request_timeout=cfg.request_timeout),
    )
```

### 51. Ghép chuỗi postprocessor: ngưỡng, lọc phiên bản, rerank, ưu tiên sửa đổi

`src/retriever.py`: get_postprocessors (dòng 56–90)

```python
def get_postprocessors(cfg: RAGConfig, index: VectorStoreIndex | None = None) -> list[BaseNodePostprocessor]:
    """Thứ tự: ngưỡng tương đồng -> lọc phiên bản -> rerank -> đưa bản sửa đổi lên trước rồi cắt top_n.

    `index` cho phép bước lọc phiên bản kéo kèm mục sửa đổi chưa được truy hồi (cần docstore);
    thiếu `index` thì vẫn lọc hiệu lực/khóa và sắp xếp lại, chỉ không kéo thêm Node.
    """
    ps: list[BaseNodePostprocessor] = []
    if cfg.similarity_cutoff is not None:
        if cfg.use_hybrid:
            # Điểm sau fusion (RRF) không cùng thang với cosine -> ngưỡng chỉ áp cho vector thuần
            logger.warning("Bỏ qua similarity_cutoff vì đang bật hybrid (thang điểm đã đổi)")
        else:
            from llama_index.core.postprocessor import SimilarityPostprocessor

            ps.append(SimilarityPostprocessor(similarity_cutoff=cfg.similarity_cutoff))
    if cfg.loc_phien_ban:
        from phien_ban import LocPhienBan

        ps.append(LocPhienBan.tu_nodes(index.docstore.docs.values()) if index is not None else LocPhienBan())
    rerank = bool(cfg.use_rerank and cfg.reranker_model_name)
    if rerank:
        # Có lọc phiên bản thì reranker giữ đủ Node; UuTienSuaDoi sắp lại theo quan hệ sửa đổi rồi mới cắt top_n
        top_n = 1000 if cfg.loc_phien_ban else cfg.reranker_top_n
        if cfg.model_server_url:
            from remote_models import RemoteRerank

            ps.append(RemoteRerank(base_url=cfg.model_server_url, top_n=top_n))
        else:
            ps.append(make_local_reranker(cfg, top_n))
    if cfg.loc_phien_ban:
        from phien_ban import UuTienSuaDoi

        # Không rerank thì điểm là cosine, không cùng thang với ngưỡng tỉ lệ (hiệu chỉnh trên điểm reranker)
        ps.append(UuTienSuaDoi(top_n=cfg.reranker_top_n) if rerank else UuTienSuaDoi(ti_le_toi_thieu=None))
    return ps
```

### 52. Hàm tìm kiếm dùng chung cho đánh giá

`src/retriever.py`: search (dòng 93–108)

```python
def search(
    index: VectorStoreIndex,
    cfg: RAGConfig,
    question: str,
    postprocessors: list[BaseNodePostprocessor] | None = None,
    retriever: BaseRetriever | None = None,
) -> list[NodeWithScore]:
    """Truy hồi top-k rồi cho qua postprocessor (ngưỡng, rerank).

    Truyền sẵn `retriever`/`postprocessors` để vòng lặp đánh giá không dựng lại retriever
    và không nạp lại reranker mỗi câu.
    """
    nodes = (retriever or get_retriever(index, cfg)).retrieve(question)
    for p in get_postprocessors(cfg, index) if postprocessors is None else postprocessors:
        nodes = p.postprocess_nodes(nodes, QueryBundle(question))
    return nodes
```

### 53. In nhãn nguồn của Node

`src/retriever.py`: node_label (dòng 111–118)

```python
def node_label(n: NodeWithScore) -> str:
    """Nhãn dạng "<văn bản> – Điều N" hoặc "<văn bản> – sửa đổi Điều N" để in kết quả và trích nguồn."""
    m = n.node.metadata
    if m.get("dieu"):
        return f"{m.get('van_ban', '')} – Điều {m['dieu']}"
    if m.get("sua_doi_dieu"):
        return f"{m.get('van_ban', '')} – sửa đổi Điều {m['sua_doi_dieu']}"
    return str(m.get("van_ban", ""))  # văn bản không chia Điều
```

### 54. Đặt lại độ dài tối đa của CrossEncoder (512 → 2 048)

`src/retriever.py`: dat_do_dai_toi_da (dòng 121–130)

```python
def dat_do_dai_toi_da(cross_encoder: Any, so_token: int) -> None:
    """SentenceTransformerRerank tạo CrossEncoder với max_length=512 cố định, không cho truyền vào.

    sentence-transformers >= 5 đổi tên thuộc tính thành `max_seq_length` (`max_length` còn nhưng báo deprecated);
    bản cũ hơn chỉ có `max_length`. Dùng chung cho src/model_server.py qua bản sao trong file đó.
    """
    if isinstance(getattr(type(cross_encoder), "max_seq_length", None), property):
        cross_encoder.max_seq_length = so_token
    else:
        cross_encoder.max_length = so_token
```

### 55. Nạp reranker tại chỗ, ép fp16 để vừa GPU 4 GB

`src/retriever.py`: make_local_reranker (dòng 133–151)

```python
def make_local_reranker(cfg: RAGConfig, top_n: int | None = None) -> "SentenceTransformerRerank":
    from llama_index.core.postprocessor import SentenceTransformerRerank

    if not cfg.reranker_model_name:
        raise ValueError(f"Profile {cfg.name!r} không có reranker_model_name")
    device = resolve_device(cfg.embed_device)
    fp16 = cfg.use_fp16 and device == "cuda"
    reranker = SentenceTransformerRerank(
        model=cfg.reranker_model_name,
        top_n=cfg.reranker_top_n if top_n is None else top_n,
        device="cpu" if fp16 else device,
    )
    dat_do_dai_toi_da(reranker._model, cfg.reranker_max_length)  # pyright: ignore[reportPrivateUsage]
    if fp16:
        # SentenceTransformerRerank không nhận dtype: nạp trên CPU, ép fp16 rồi mới đưa lên GPU,
        # tránh việc bản fp32 chiếm VRAM cùng lúc với embedding (tràn card 4 GB).
        reranker._model.half().to(device)  # pyright: ignore[reportPrivateUsage]
        reranker.device = device
    return reranker
```

### 56. Bỏ dấu tiếng Việt

`src/bm25.py`: bo_dau (dòng 25–28)

```python
def bo_dau(s: str) -> str:
    """Bỏ dấu tiếng Việt: 'Điều' -> 'dieu'."""
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
```

### 57. Tách từ cho BM25 (có tùy chọn bigram)

`src/bm25.py`: tach_tu (dòng 31–36)

```python
def tach_tu(text: str, bigrams: bool = False) -> list[str]:
    """Tách thành âm tiết đã bỏ dấu; bigrams=True thêm cặp âm tiết liền kề (cụm từ)."""
    toks = [bo_dau(t).lower() for t in TOKEN.findall(text)]
    if bigrams and len(toks) > 1:
        toks += [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    return toks
```

### 58. Cài thuật toán BM25 Okapi

`src/bm25.py`: BM25 (dòng 39–66)

```python
class BM25:
    """BM25 Okapi trên tập tài liệu đã tách từ."""

    def __init__(self, docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.n = len(docs)
        self.tf = [Counter(d) for d in docs]
        self.do_dai = [len(d) for d in docs]
        self.do_dai_tb = (sum(self.do_dai) / self.n) if self.n else 0.0
        df: Counter[str] = Counter()
        for tfc in self.tf:
            df.update(tfc.keys())
        # Công thức IDF có làm trơn (Robertson): luôn dương nên không cần xử lý idf âm
        self.idf = {t: math.log(1 + (self.n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def scores(self, query_tokens: Sequence[str]) -> list[float]:
        diem = [0.0] * self.n
        for t in set(query_tokens):
            idf = self.idf.get(t)
            if idf is None:
                continue
            for i, tfc in enumerate(self.tf):
                f = tfc.get(t)
                if not f:
                    continue
                mau = f + self.k1 * (1 - self.b + self.b * self.do_dai[i] / (self.do_dai_tb or 1))
                diem[i] += idf * f * (self.k1 + 1) / mau
        return diem
```

### 59. Bọc BM25 thành BaseRetriever của LlamaIndex

`src/bm25.py`: BM25Retriever (dòng 69–94)

```python
class BM25Retriever(BaseRetriever):
    """Retriever BM25 đóng vai một BaseRetriever của LlamaIndex (ghép được vào QueryFusionRetriever)."""

    def __init__(
        self,
        nodes: Sequence[BaseNode],
        similarity_top_k: int = 10,
        k1: float = 1.5,
        b: float = 0.75,
        bigrams: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.nodes = list(nodes)
        self.similarity_top_k = similarity_top_k
        self.bigrams = bigrams
        self._bm25 = BM25([tach_tu(n.get_content(metadata_mode=MetadataMode.EMBED), bigrams) for n in self.nodes], k1, b)

    @classmethod
    def class_name(cls) -> str:
        return "BM25Retriever"

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        diem = self._bm25.scores(tach_tu(query_bundle.query_str, self.bigrams))
        thu_tu = sorted(range(len(diem)), key=lambda i: diem[i], reverse=True)[: self.similarity_top_k]
        return [NodeWithScore(node=self.nodes[i], score=diem[i]) for i in thu_tu if diem[i] > 0]
```

## F. Lọc phiên bản theo hiệu lực

### 60. Đọc khóa tuyển sinh nêu trong câu hỏi

`src/phien_ban.py`: khoa_trong_cau_hoi (dòng 37–43)

```python
def khoa_trong_cau_hoi(cau_hoi: str) -> int | None:
    """Khóa tuyển sinh nêu trong câu hỏi (năm 4 chữ số), None nếu không nêu."""
    m = KHOA.search(unicodedata.normalize("NFC", cau_hoi))
    if not m:
        return None
    so = m[1] or m[2]
    return int(so) if len(so) == 4 else 2000 + int(so)
```

### 61. Gom văn bản thành chuỗi liên thông (union-find)

`src/phien_ban.py`: chuoi_van_ban (dòng 64–85)

```python
def chuoi_van_ban(nodes: Iterable[BaseNode]) -> dict[str, int]:
    """Gom văn bản thành các chuỗi liên thông (union-find): số văn bản -> mã chuỗi.

    TB 2366 -> 2451, 2567 -> QyĐ 2626 -> 2101 nối với nhau qua TB 2567, nên cả 5 văn bản quy đổi tiếng Anh
    là một chuỗi; QC 2021 và QĐ 3183 là một chuỗi khác.
    """
    cha: dict[str, str] = {}

    def goc(x: str) -> str:
        while cha.setdefault(x, x) != x:
            cha[x] = cha[cha[x]]
            x = cha[x]
        return x

    for n in nodes:
        ds = sorted(lien_quan(n.metadata))
        for x in ds[1:]:
            cha[goc(x)] = goc(ds[0])
        if ds:
            goc(ds[0])
    ma: dict[str, int] = {}
    return {x: ma.setdefault(goc(x), len(ma)) for x in cha}
```

### 62. Kiểm tra một Node có áp dụng cho khóa không

`src/phien_ban.py`: ap_dung_cho_khoa (dòng 88–90)

```python
def ap_dung_cho_khoa(meta: dict[str, object], khoa: int) -> bool:
    tu, den = meta.get("ap_dung_khoa_tu"), meta.get("ap_dung_khoa_den")
    return not ((isinstance(tu, int) and khoa < tu) or (isinstance(den, int) and khoa > den))
```

### 63. Tạo khóa tra mục sửa đổi theo Điều

`src/phien_ban.py`: khoa_sua_doi (dòng 93–98)

```python
def khoa_sua_doi(meta: dict[str, object]) -> str | None:
    """Khóa tra mục sửa đổi: "<số văn bản bị sửa>|<Điều>" cho Node `sua_doi_dieu`."""
    if not meta.get("sua_doi_dieu"):
        return None
    dich = danh_sach(meta.get("sua_doi"))
    return f"{dich[0]}|{meta['sua_doi_dieu']}" if dich else None
```

### 64. Postprocessor LocPhienBan: bỏ văn bản hết hiệu lực và không áp dụng cho khóa

`src/phien_ban.py`: LocPhienBan (dòng 101–149)

```python
class LocPhienBan(BaseNodePostprocessor):
    # "<số văn bản>|<Điều>" -> các Node mục sửa đổi Điều đó (dựng từ docstore của index)
    muc_sua_doi: dict[str, list[BaseNode]] = Field(default_factory=lambda: dict[str, list[BaseNode]]())
    chuoi: dict[str, int] = Field(default_factory=lambda: dict[str, int]())

    @classmethod
    def class_name(cls) -> str:
        return "LocPhienBan"

    @classmethod
    def tu_nodes(cls, nodes: Iterable[BaseNode]) -> "LocPhienBan":
        ds = list(nodes)
        muc: dict[str, list[BaseNode]] = {}
        for n in ds:
            k = khoa_sua_doi(n.metadata)
            if k:
                muc.setdefault(k, []).append(n)
        return cls(muc_sua_doi=muc, chuoi=chuoi_van_ban(ds))

    def ma_chuoi(self, meta: dict[str, object]) -> int | None:
        so = so_van_ban(str(meta.get("so_hieu", "")))
        return self.chuoi.get(so) if so else None

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        nodes = [n for n in nodes if n.node.metadata.get("tinh_trang") not in HET_HIEU_LUC]
        khoa = khoa_trong_cau_hoi(query_bundle.query_str) if query_bundle else None

        # T2: kéo kèm mục sửa đổi của Điều gốc đã lấy ra, đặt ngay trước Điều gốc
        co_san = {n.node.node_id for n in nodes}
        ket: list[NodeWithScore] = []
        for n in nodes:
            m = n.node.metadata
            if m.get("phan") == "chinh" and m.get("dieu") and m.get("so_hieu"):
                for sd in self.muc_sua_doi.get(f"{so_van_ban(str(m['so_hieu']))}|{m['dieu']}", []):
                    if sd.node_id not in co_san:
                        co_san.add(sd.node_id)
                        ket.append(NodeWithScore(node=sd, score=n.score))
            ket.append(n)

        # T1: theo khóa — chỉ bỏ khi cùng chuỗi văn bản còn Node áp dụng được, để không mất hết căn cứ
        if khoa is None:
            return ket
        hop_le = {self.ma_chuoi(n.node.metadata) for n in ket if ap_dung_cho_khoa(n.node.metadata, khoa)}
        return [
            n for n in ket
            if ap_dung_cho_khoa(n.node.metadata, khoa) or self.ma_chuoi(n.node.metadata) not in hop_le
        ]
```

### 65. Postprocessor UuTienSuaDoi: đưa bản sửa đổi lên trước (ngưỡng 0,5)

`src/phien_ban.py`: UuTienSuaDoi (dòng 152–185)

```python
class UuTienSuaDoi(BaseNodePostprocessor):
    top_n: int | None = None  # None = không cắt (khi không rerank)
    # Chỉ áp cho quan hệ cả văn bản và chỉ khi điểm là điểm rerank; None = không so điểm (xem docstring đầu file)
    ti_le_toi_thieu: float | None = 0.5

    @classmethod
    def class_name(cls) -> str:
        return "UuTienSuaDoi"

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        ket = list(nodes)
        # Lặp tới khi ổn định: mỗi lượt đưa một Node "mới hơn" lên ngay trước Node nó sửa đổi/thay thế
        for _ in range(len(ket) ** 2 + 1):
            doi = False
            for i, cu in enumerate(ket):
                for j in range(i + 1, len(ket)):
                    if moi_hon(ket[j].node.metadata, cu.node.metadata) and self.du_lien_quan(ket[j], cu):
                        ket.insert(i, ket.pop(j))
                        doi = True
                        break
                if doi:
                    break
            if not doi:
                break
        return ket if self.top_n is None else ket[: self.top_n]

    def du_lien_quan(self, moi: NodeWithScore, cu: NodeWithScore) -> bool:
        if moi.node.metadata.get("sua_doi_dieu") or self.ti_le_toi_thieu is None:
            return True
        if moi.score is None or cu.score is None:
            return True
        return moi.score >= self.ti_le_toi_thieu * cu.score
```

### 66. Xác định văn bản mới có sửa đúng phần của văn bản cũ

`src/phien_ban.py`: moi_hon (dòng 188–207)

```python
def moi_hon(moi: dict[str, object], cu: dict[str, object]) -> bool:
    """`moi` sửa đổi/thay thế đúng phần của `cu` đang nói tới.

    - Mục sửa đổi Điều X của QĐ 3183 mới hơn Điều X bản gốc của QC 2021 (cùng Điều mới tính).
    - Văn bản E mới hơn văn bản D khi D ghi `bi_sua_doi_boi`/`bi_thay_the_boi` E, hoặc E ghi `sua_doi`/`thay_the` D,
      chỉ khi Node của D không thuộc Điều nào: Node chia theo Điều chỉ bị đẩy xuống bởi đúng mục sửa đổi Điều đó
      (QĐ 3183 Điều 2 "hiệu lực" không phải bản mới của QC 2021 Điều 13; QyĐ 2101 thay 2626 chỉ cho khóa từ 2024).
    """
    so_cu = so_van_ban(str(cu.get("so_hieu", "")))
    so_moi = so_van_ban(str(moi.get("so_hieu", "")))
    if not so_cu or not so_moi or so_cu == so_moi:
        return False
    if moi.get("sua_doi_dieu"):
        return so_cu in danh_sach(moi.get("sua_doi")) and moi.get("sua_doi_dieu") == cu.get("dieu")
    if cu.get("dieu"):
        return False
    return (
        so_moi in danh_sach(cu.get("bi_sua_doi_boi")) + danh_sach(cu.get("bi_thay_the_boi"))
        or so_cu in danh_sach(moi.get("sua_doi")) + danh_sach(moi.get("thay_the"))
    )
```

## G. Sinh câu trả lời và tái lập

### 67. Prompt tiếng Việt cho query engine

`src/query_engine.py`: QA_PROMPT (dòng 19–39)

```python
QA_PROMPT = PromptTemplate(
    "Dưới đây là các trích đoạn từ các văn bản quy chế, quy định đào tạo của Trường Đại học Sài Gòn "
    "(mỗi trích đoạn ghi rõ tên văn bản và Điều).\n"
    "---------------------\n{context_str}\n---------------------\n"
    "Chỉ dựa vào các trích đoạn trên, trả lời câu hỏi bằng tiếng Việt, ngắn gọn và chính xác.\n"
    "Bắt buộc trích nguyên văn câu quy định làm căn cứ trước khi kết luận, kèm tên văn bản và số Điều.\n"
    "Không tự suy diễn, không tự quy đổi thang điểm hay đổi đơn vị; nếu cần tra bảng thì chép đúng "
    "hàng của bảng có trong trích đoạn.\n"
    "Nếu có văn bản sửa đổi thì dùng nội dung đã sửa đổi.\n"
    # Trích đoạn sửa đổi chỉ chứa bảng, không ghi thang điểm: thiếu chú giải này LLM lấy bảng quy đổi
    # hệ 4 (Điều 10) để trả lời câu hỏi về hệ 10 (Điều 9).
    # Bản vá miền, CHƯA đánh giá riêng (chưa có A/B giữ/bỏ đoạn này); không dùng lại được cho văn bản khác.
    "Lưu ý về thang điểm: điểm thành phần và điểm học phần chấm theo thang điểm 10 (\"hệ 10\"), rồi xếp loại "
    "thành điểm chữ (A, B+, B, ...) theo khoảng điểm ở khoản 3 Điều 9. Điểm chữ được quy đổi sang thang điểm 4 "
    "(\"hệ 4\") chỉ để tính điểm trung bình, theo khoản 2 Điều 10. Hỏi về hệ 10 hoặc khoảng điểm thì dùng bảng "
    "Điều 9; hỏi về hệ 4 hoặc quy đổi để tính điểm trung bình thì dùng bảng Điều 10. "
    "Khi tra khoảng điểm, so sánh con số với cả cận dưới và cận trên của từng hàng.\n"
    "Nếu trích đoạn không có thông tin, hãy nói không tìm thấy trong các văn bản quy định.\n"
    "Câu hỏi: {query_str}\n"
    "Trả lời: "
)
```

### 68. Tạo LLM Ollama tất định (temperature 0, seed, tắt thinking)

`src/query_engine.py`: make_llm (dòng 42–55)

```python
def make_llm(cfg: RAGConfig) -> Ollama:
    """LLM tất định: temperature=0 và seed cố định (trước đây không đặt nên đáp án đổi giữa các lần hỏi).

    cfg.thinking bật chế độ suy luận của qwen3: tra bảng khoảng điểm chính xác hơn nhưng chậm ~4 lần.
    """
    return Ollama(
        model=cfg.llm_model_name,
        base_url=cfg.ollama_base_url,
        request_timeout=cfg.request_timeout,
        temperature=cfg.temperature,
        additional_kwargs={"seed": cfg.seed},
        thinking=cfg.thinking,
        context_window=8192,
    )
```

### 69. Lấy digest của model trên Ollama

`src/query_engine.py`: digest_llm (dòng 62–68)

```python
def digest_llm(cfg: RAGConfig) -> str | None:
    """Digest của model trên Ollama (`/api/tags`): cùng tên "qwen3:8b" nhưng kéo lại có thể là bản khác."""
    try:
        ds = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=10).raise_for_status().json()["models"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None
    return next((str(m.get("digest")) for m in ds if m.get("name") == cfg.llm_model_name), None)
```

### 70. Khóa tái lập: sha256 prompt, LLM, index và cấu hình

`src/query_engine.py`: sha256_json (dòng 58–59), khoa_tai_lap (dòng 71–85)

```python
def sha256_json(x: object) -> str:
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

def khoa_tai_lap(cfg: RAGConfig, llm_digest: str | None = None) -> dict[str, object]:
    """Những gì quyết định một câu trả lời: prompt, model, index và cấu hình (nhận xét tuần 7, ý 6).

    `ma` là sha256 rút gọn của cả khối: ghi `ma` vào log từng câu thì biết câu nào chạy với prompt/model/index nào,
    và hai lượt chạy có `ma` khác nhau thì không được gộp chung một bảng.
    """
    khoa: dict[str, object] = {
        "prompt_sha256": hashlib.sha256(QA_PROMPT.get_template().encode("utf-8")).hexdigest(),
        "llm": cfg.llm_model_name,
        "llm_digest": llm_digest,
        "index_sha256": sha256_json(corpus_fingerprint(cfg)),  # model embedding + loader + sha256 từng file
        # Bỏ khóa phụ thuộc máy chạy: cùng cấu hình chạy trên CPU hay GPU vẫn là một cấu hình
        "cau_hinh": {k: v for k, v in cfg.mo_ta().items() if k not in ("embed_device", "persist_dir")},
    }
    return {"ma": sha256_json(khoa)[:12], **khoa}
```

### 71. Dựng RetrieverQueryEngine

`src/query_engine.py`: build_query_engine (dòng 88–98)

```python
def build_query_engine(index: VectorStoreIndex, cfg: RAGConfig) -> RetrieverQueryEngine:
    llm = make_llm(cfg)
    Settings.llm = llm
    return RetrieverQueryEngine.from_args(
        retriever=get_retriever(index, cfg),
        llm=llm,
        response_mode=ResponseMode(cfg.response_mode),
        streaming=cfg.streaming,
        text_qa_template=QA_PROMPT,
        node_postprocessors=get_postprocessors(cfg, index),
    )
```

### 72. In nguồn trích dẫn và hỏi đáp có streaming

`src/query_engine.py`: format_sources (dòng 101–102), ask (dòng 105–113)

```python
def format_sources(response: RESPONSE_TYPE) -> str:
    return "; ".join(dict.fromkeys(node_label(n) for n in response.source_nodes))

def ask(engine: RetrieverQueryEngine, question: str, cfg: RAGConfig) -> None:
    response = engine.query(question)
    if isinstance(response, StreamingResponse):
        for token in response.response_gen:
            print(token, end="", flush=True)
        print()
    elif isinstance(response, Response):
        print(response.response)
    print(f"Nguồn: {format_sources(response)}")
```

## H. Độ đo và đánh giá

### 73. Tìm hạng của Node đúng đầu tiên

`eval/metrics.py`: hang_dau_tien (dòng 15–20)

```python
def hang_dau_tien(so_node: int, dung: Callable[[int], bool]) -> int | None:
    """Hạng (1-based) của Node đúng đầu tiên trong danh sách; None nếu không có Node nào đúng."""
    for i in range(so_node):
        if dung(i):
            return i + 1
    return None
```

### 74. Tính Recall@k

`eval/metrics.py`: recall_at_k (dòng 23–27)

```python
def recall_at_k(hang: Sequence[int | None], k: int) -> float:
    """Tỷ lệ câu có Node đúng nằm trong k hạng đầu (hit rate@k)."""
    if not hang:
        return 0.0
    return sum(1 for r in hang if r is not None and r <= k) / len(hang)
```

### 75. Tính MRR

`eval/metrics.py`: mrr (dòng 30–34)

```python
def mrr(hang: Sequence[int | None], toi_da: int | None = None) -> float:
    """Mean Reciprocal Rank; chỉ tính các câu có hạng <= toi_da (None = mọi hạng)."""
    if not hang:
        return 0.0
    return sum(1 / r for r in hang if r is not None and (toi_da is None or r <= toi_da)) / len(hang)
```

### 76. Tính nDCG@k

`eval/metrics.py`: ndcg_at_k (dòng 37–43)

```python
def ndcg_at_k(hang: Sequence[int | None], k: int, so_lien_quan: int = 1) -> float:
    """nDCG@k với `so_lien_quan` Node đúng cho mỗi câu (mặc định 1 -> IDCG = 1)."""
    if not hang:
        return 0.0
    dcg = sum(1 / math.log2(r + 1) for r in hang if r is not None and r <= k)
    idcg = sum(1 / math.log2(i + 1) for i in range(1, so_lien_quan + 1))
    return dcg / (len(hang) * idcg) if idcg else 0.0
```

### 77. Khoảng tin cậy bootstrap

`eval/metrics.py`: bootstrap_ci (dòng 46–68)

```python
def bootstrap_ci(
    gia_tri: Sequence[float],
    n_lan: int = 2000,
    alpha: float = 0.05,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Khoảng tin cậy percentile bootstrap cho giá trị trung bình.

    Trả về (trung bình, cận dưới, cận trên). Dùng để không kết luận từ chênh lệch nhỏ
    trên bộ câu hỏi ít (ví dụ bộ 02 chỉ có 10 câu).
    """
    if not gia_tri:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    n = len(gia_tri)
    tb: list[float] = []
    for _ in range(n_lan):
        mau = [gia_tri[rng.randrange(n)] for _ in range(n)]
        tb.append(sum(mau) / n)
    tb.sort()
    lo = tb[max(0, int(n_lan * alpha / 2) - 1)]
    hi = tb[min(n_lan - 1, int(n_lan * (1 - alpha / 2)))]
    return sum(gia_tri) / n, lo, hi
```

### 78. Kiểm định McNemar chính xác giữa hai cấu hình

`eval/metrics.py`: mcnemar (dòng 71–83)

```python
def mcnemar(hits_a: Sequence[bool], hits_b: Sequence[bool]) -> tuple[int, int, float]:
    """Kiểm định McNemar chính xác (hai phía) cho hai cấu hình trên cùng bộ câu hỏi.

    Trả về (b, c, p) với b = số câu chỉ A đúng, c = số câu chỉ B đúng.
    """
    b = sum(1 for x, y in zip(hits_a, hits_b) if x and not y)
    c = sum(1 for x, y in zip(hits_a, hits_b) if y and not x)
    n = b + c
    if n == 0:
        return b, c, 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return b, c, min(1.0, p)
```

### 79. Cohen κ giữa hai người gán nhãn

`eval/metrics.py`: cohen_kappa (dòng 98–112)

```python
def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float:
    """Độ đồng thuận Cohen κ giữa hai người/cách chấm trên cùng các câu (nhãn phân loại bất kỳ).

    1 = trùng hoàn toàn, 0 = chỉ ngang mức ngẫu nhiên. Dùng cho hai người chấm câu trả lời, và cho chỉ số tự động so
    với người chấm (chỉ tin chỉ số tự động khi κ đủ cao).
    """
    if len(a) != len(b):
        raise ValueError("hai dãy nhãn phải cùng độ dài")
    if not a:
        return 0.0
    n = len(a)
    quan_sat = sum(1 for x, y in zip(a, b) if x == y) / n
    nhan = set(a) | set(b)
    ky_vong = sum((sum(1 for x in a if x == k) / n) * (sum(1 for y in b if y == k) / n) for k in nhan)
    return 1.0 if ky_vong == 1 else (quan_sat - ky_vong) / (1 - ky_vong)
```

### 80. Luật chấm bộ 01: Điều của Quy chế 2021 hoặc mục sửa đổi Điều đó

`eval/luat_cham.py`: dung_bo_01 (dòng 27–33)

```python
def dung_bo_01(n: NodeWithScore, d: str) -> bool:
    """Bộ 01 hỏi về QC SGU 2021: đúng là Điều đó (phần chính) hoặc mục QĐ 3183 sửa đổi chính Điều đó."""
    m = n.node.metadata
    ds = cac_dieu(d)
    goc = so_vb(m) == QC_2021 and m.get("phan") == "chinh" and m.get("dieu") in ds
    sua_doi = so_vb(m) == QD_3183 and m.get("sua_doi_dieu") in ds
    return bool(goc or sua_doi)
```

### 81. Luật chấm bộ dev theo tiền tố văn bản và Điều

`eval/luat_cham.py`: dung_bo_dev (dòng 45–63)

```python
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
```

### 82. Đánh giá một bộ câu hỏi với một cấu hình

`eval/evaluate.py`: danh_gia (dòng 143–158)

```python
def danh_gia(ten_file: str, dung: ChamDung, tim: TimKiem, cau_hinh: str, mo_ta: dict[str, object]) -> KetQua:
    questions = doc_cau_hoi(ten_file)
    kq = KetQua(ten_file, cau_hinh, mo_ta, len(questions))
    for q in questions:
        # Truyền nguyên nhãn: nhãn dev có dấu cách ("TB so 2567", "HD-Quy trinh phuc khao"); trước đây
        # split()[0] cắt còn "TB" / "HD-Quy" nên tiền tố khớp lỏng (TB_ChuanDauRa cũng tính là đúng).
        d = q["dieu_dung"]
        t0 = time.perf_counter()
        res = tim(q["question"])
        kq.thoi_gian_ms.append((time.perf_counter() - t0) * 1000)
        kq.hang.append(hang_dau_tien(len(res), lambda i: dung(res[i], d)))
        if res:
            kq.top1[node_label(res[0]).split(" – ")[0][:40]] += 1
        if kq.hang[-1] is None or kq.hang[-1] > 3:
            kq.ngoai_top3.append((q["question"], q["dieu_dung"], [node_label(n) for n in res[:3]]))
    return kq
```

### 83. Đối chiếu độ đo tự viết với RetrieverEvaluator của LlamaIndex

`eval/evaluate.py`: doi_chieu_thu_vien (dòng 172–189)

```python
def doi_chieu_thu_vien(cfg: RAGConfig, ten_file: str, dung: ChamDung, index: VectorStoreIndex) -> dict[str, float]:
    """Chấm lại cùng bộ câu hỏi bằng `RetrieverEvaluator` của LlamaIndex để đối chiếu hai cách đo.

    hit_rate = có Node đúng trong cả similarity_top_k Node -> tương ứng R@k với k = similarity_top_k.
    """
    from llama_index.core.evaluation import RetrieverEvaluator

    ev = RetrieverEvaluator.from_metric_names(["mrr", "hit_rate"], retriever=get_retriever(index, cfg))
    diem: dict[str, list[float]] = {"mrr": [], "hit_rate": []}
    for q in doc_cau_hoi(ten_file):
        d = q["dieu_dung"]
        mong_doi = [nid for nid, n in index.docstore.docs.items() if dung(NodeWithScore(node=n), d)]
        if not mong_doi:
            continue
        res = ev.evaluate(query=q["question"], expected_ids=mong_doi)
        for ten, gt in res.metric_dict.items():
            diem[ten].append(float(gt.score))
    return {ten: (sum(v) / len(v) if v else 0.0) for ten, v in diem.items()}
```

### 84. Chạy tập kiểm chứng đúng một lần với cấu hình đóng băng

`eval/evaluate.py`: chay_tap_kiem_chung (dòng 220–269)

```python
def chay_tap_kiem_chung(chay_lai: bool) -> None:
    """Chạy tập kiểm chứng ĐÚNG MỘT LẦN bằng cấu hình đã đóng băng (eval/dong_bang.py), báo riêng từng bộ và từng loại câu.

    Chạy lại sau khi đã nhìn kết quả thì tập này không còn là tập kiểm chứng (đã có thể dùng để chỉnh): phải bật
    --chay-lai-kiem-chung, kết quả được đánh dấu "chay_lai" để báo cáo ghi rõ.
    """
    from dong_bang import MANIFEST, kiem_khop

    khop, dong = kiem_khop()
    if not khop:
        sys.exit("Trạng thái hiện tại không khớp manifest đóng băng, không chạy tập kiểm chứng:\n" + "\n".join(dong))
    json_out = ROOT / "eval" / "results" / "truy-hoi-kiem-chung.json"
    if json_out.exists() and not chay_lai:
        sys.exit(f"Tập kiểm chứng đã chạy ({json_out.relative_to(ROOT)}). Chỉ chạy lại khi thật sự cần, bằng "
                 "--chay-lai-kiem-chung, và ghi rõ trong báo cáo.")

    cfg = get_config()  # cấu hình chốt của profile, đúng cấu hình đã ghi trong manifest
    index = build_or_load_index(cfg)
    retriever = get_retriever(index, cfg)
    posts = get_postprocessors(cfg, index)
    tim = lambda q: search(index, cfg, q, postprocessors=posts, retriever=retriever)  # noqa: E731
    tim("khởi động")
    tat_ca: list[KetQua] = []
    theo_loai: dict[str, list[int | None]] = {}
    for ten_file, dung in BO_KIEM_CHUNG:
        kq = danh_gia(ten_file, dung, tim, "chot-dong-bang", cfg.mo_ta())
        in_ket_qua(kq)
        tat_ca.append(kq)
        for q, hang in zip(doc_cau_hoi(ten_file), kq.hang, strict=True):
            theo_loai.setdefault(q.get("loai", "-"), []).append(hang)

    dong_loai = ["| Loại câu | Số câu | R@1 | R@3 | MRR |", "|---|---|---|---|---|"]
    for loai, hang in sorted(theo_loai.items()):
        dong_loai.append(f"| {loai} | {len(hang)} | {recall_at_k(hang, 1):.1%} | {recall_at_k(hang, 3):.1%} | "
                         f"{mrr(hang):.3f} |")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    json_out.write_text(json.dumps({
        "thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chay_lai": chay_lai,
        "dong_bang": {"thoi_diem": manifest.get("thoi_diem"), "commit": manifest.get("commit")},
        "ket_qua": [k.to_dict() for k in tat_ca],
        "theo_loai": {loai: {"so_cau": len(h), "R@1": round(recall_at_k(h, 1), 4), "R@3": round(recall_at_k(h, 3), 4),
                             "MRR": round(mrr(h), 4)} for loai, h in theo_loai.items()},
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    md = (f"# Tập kiểm chứng — cấu hình đóng băng {manifest.get('thoi_diem')} (commit {manifest.get('commit')})"
          f"{' — CHẠY LẠI' if chay_lai else ''}\n\n" + bang_markdown(tat_ca) + "\n### Theo loại câu\n\n"
          + "\n".join(dong_loai) + "\n")
    json_out.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md)
    print(f"Đã ghi {json_out.relative_to(ROOT)} và .md")
```

### 85. Chấm tự động: các con số của đáp án có trong câu trả lời không

`eval/cham_tu_dong.py`: TU_CHOI (dòng 14–14), chuan_hoa_so (dòng 24–30), su_kien (dòng 33–35), khop_su_kien (dòng 38–45), la_tu_choi (dòng 48–49)

```python
TU_CHOI = re.compile(r"không tìm thấy|không có thông tin|không đề cập|không nêu|không (được )?quy định trong", re.IGNORECASE)

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
```

### 86. Chụp trạng thái để đóng băng (sha256 mã nguồn, corpus, cấu hình)

`eval/dong_bang.py`: trang_thai (dòng 59–74)

```python
def trang_thai() -> dict[str, Any]:
    """Ảnh chụp những gì quyết định con số đo được ở thời điểm hiện tại."""
    from config import get_config
    from index_builder import corpus_fingerprint
    from luat_cham import BO_CAU_HOI, BO_KIEM_CHUNG, BO_NGOAI_PHAM_VI

    cfg = get_config()
    bo = [*BO_CAU_HOI, *BO_KIEM_CHUNG]
    return {
        "profile": cfg.name,
        "cau_hinh": cfg.mo_ta(),
        "corpus": corpus_fingerprint(cfg),
        "ma_nguon": {str(p.relative_to(ROOT)): sha256(p) for p in ma_nguon()},
        "luat_cham": {f: f"{dung.__name__} — {LUAT_CHAM.get(dung.__name__, '')}" for f, dung in bo},
        "cau_hoi": {f: sha256(ROOT / "eval" / f) for f in [*(f for f, _ in bo), BO_NGOAI_PHAM_VI]},
    }
```

### 87. Kiểm trạng thái hiện tại khớp manifest đóng băng

`eval/dong_bang.py`: so_sanh (dòng 77–91), kiem_khop (dòng 94–101)

```python
def so_sanh(cu: object, moi: object, duong: str = "") -> list[str]:
    """Danh sách khóa (dạng "a.b.c") có giá trị khác nhau giữa hai manifest, trừ BO_QUA_KHI_SO."""
    if duong in BO_QUA_KHI_SO:
        return []
    if isinstance(cu, dict) and isinstance(moi, dict):
        khac: list[str] = []
        for k in sorted(set(cu) | set(moi), key=str):  # pyright: ignore[reportUnknownArgumentType]
            con = f"{duong}.{k}" if duong else str(k)
            if k not in cu or k not in moi:
                if con not in BO_QUA_KHI_SO:
                    khac.append(f"{con} ({'thêm mới' if k not in cu else 'bị xóa'})")
            else:
                khac += so_sanh(cu[k], moi[k], con)
        return khac
    return [] if cu == moi else [duong]

def kiem_khop() -> tuple[bool, list[str]]:
    """(khớp hay không, các dòng giải thích). Không có manifest cũng là không khớp."""
    if not MANIFEST.exists():
        return False, [f"Chưa có {MANIFEST.relative_to(ROOT)} — chạy `eval/dong_bang.py tao` trước"]
    cu = json.loads(MANIFEST.read_text(encoding="utf-8"))
    khac = so_sanh({k: v for k, v in cu.items() if k in ("profile", "cau_hinh", "corpus", "ma_nguon", "luat_cham", "cau_hoi")},
                   trang_thai())
    return not khac, [f"lệch: {k}" for k in khac]
```

### 88. Độ tương đồng cosine để kiểm câu trùng

`eval/kiem_tra_trung.py`: cosine (dòng 47–50)

```python
def cosine(u: list[float], v: list[float]) -> float:
    tu = sum(x * y for x, y in zip(u, v, strict=True))
    mau = math.sqrt(sum(x * x for x in u)) * math.sqrt(sum(y * y for y in v))
    return tu / mau if mau else 0.0
```

### 89. Gộp nhãn người chấm, liệt kê câu hai người lệch

`eval/doi_chieu_cham.py`: nhan_nguoi (dòng 59–73)

```python
def nhan_nguoi(nguoi: dict[str, dict[Khoa, Dong]], chot: dict[Khoa, Dong]) -> tuple[dict[Khoa, Dong], list[Khoa]]:
    """Nhãn người cuối cùng của từng câu và danh sách câu hai người lệch mà chưa chốt.

    Ưu tiên nhãn chốt; chưa chốt thì câu mọi người chấm cùng nhãn `ket_qua` được dùng (một người chấm cũng tính,
    báo cáo ghi rõ số người); lệch nhau thì chưa có nhãn.
    """
    ket: dict[Khoa, Dong] = dict(chot)
    lech: list[Khoa] = []
    for k in sorted({k for ds in nguoi.values() for k in ds} - set(chot)):
        cac = [ds[k] for ds in nguoi.values() if k in ds]
        if len({r["ket_qua"] for r in cac}) == 1 and len({r.get("trich_dan_sai", "") for r in cac}) == 1:
            ket[k] = cac[0]
        else:
            lech.append(k)
    return ket, lech
```

### 90. Bốc mẫu ngẫu nhiên (seed 42) để người rà lại

`eval/doi_chieu_cham.py`: chon_mau (dòng 86–92)

```python
def chon_mau(judge: dict[Khoa, Dong], n: int, seed: int = 42) -> list[Khoa]:
    """n câu ngẫu nhiên trong các câu judge chấm đúng, tự tin cao và không trích sai (ý 3: kiểm mẫu cao-confidence).

    Bốc theo thứ tự dòng trong file (thứ tự câu hỏi trong các bộ), nên cùng file + cùng seed luôn ra cùng mẫu.
    """
    cao = [k for k, r in judge.items() if la_dung(r) and r.get("do_tu_tin") == "cao" and not r.get("trich_dan_sai")]
    return sorted(random.Random(seed).sample(cao, min(n, len(cao))))
```

### 91. Bảng chéo nội dung × nguồn của nhãn người

`eval/doi_chieu_cham.py`: bang_cheo (dòng 119–127)

```python
def bang_cheo(nguoi: dict[Khoa, Dong], co_cot_nguon: bool) -> list[str]:
    """Nội dung × nguồn: một tỉ lệ accuracy gộp che mất câu đúng nội dung nhưng trích sai văn bản (ý 2)."""
    if not co_cot_nguon:
        return ["File của người chấm chưa có cột `trich_dan_sai` — chưa lập được bảng chéo nội dung × nguồn."]
    o = Counter((la_dung(r), not r.get("trich_dan_sai")) for r in nguoi.values())
    return ["| | Nguồn đúng | Nguồn sai (`trich_dan_sai = co`) |", "|---|---|---|",
            f"| **Nội dung đúng** | {o[(True, True)]} | {o[(True, False)]} |",
            f"| **Nội dung sai** | {o[(False, True)]} | {o[(False, False)]} |",
            "", f"Đạt cả hai tiêu chí: {o[(True, True)]}/{len(nguoi)}."]
```

### 92. Callback đếm token và số lượt gọi LLM từ Ollama

`eval/tra_loi_dev.py`: DemLLM (dòng 70–97)

```python
class DemLLM(BaseCallbackHandler):
    """Ghi lại `raw` của mỗi lượt gọi LLM (Ollama trả prompt_eval_count, eval_count, eval_duration)."""

    def __init__(self) -> None:
        super().__init__(event_starts_to_ignore=[], event_ends_to_ignore=[])
        self.luot: list[dict[str, Any]] = []

    def on_event_start(
        self, event_type: CBEventType, payload: dict[str, Any] | None = None, event_id: str = "",
        parent_id: str = "", **kwargs: Any,
    ) -> str:
        return event_id

    def on_event_end(
        self, event_type: CBEventType, payload: dict[str, Any] | None = None, event_id: str = "", **kwargs: Any
    ) -> None:
        if event_type != CBEventType.LLM or not payload:
            return
        raw = getattr(payload.get(EventPayload.RESPONSE), "raw", None)
        if isinstance(raw, dict):
            self.luot.append({k: raw.get(k) for k in ("prompt_eval_count", "eval_count", "eval_duration",
                                                         "prompt_eval_duration", "total_duration")})

    def start_trace(self, trace_id: str | None = None) -> None:
        return None

    def end_trace(self, trace_id: str | None = None, trace_map: dict[str, list[str]] | None = None) -> None:
        return None
```

### 93. Sinh câu trả lời một câu, thử lại khi lỗi, ghi evidence

`eval/tra_loi_dev.py`: tra_loi_mot_cau (dòng 105–145)

```python
def tra_loi_mot_cau(
    engine: Any, dem: DemLLM, cau_hoi: str,
    dung: Callable[[NodeWithScore, str], bool] | None = None, nhan: str | None = None, cfg: RAGConfig | None = None,
) -> dict[str, object]:
    """Gọi engine (thử lại khi lỗi mạng/Ollama). Có `dung` + `nhan` (luật chấm eval/luat_cham.py) thì ghi thêm
    `ngu_canh_co_doan_dung`: ngữ cảnh đưa vào LLM có Node đúng không — để tách lỗi truy hồi khỏi lỗi sinh.
    Có `cfg` thì mỗi evidence ghi thêm `vi_tri` (file tầng 2 + dòng) để mở đúng đoạn gốc khi chấm nguồn."""
    loi: list[str] = []
    for lan in range(1, SO_LAN_THU + 1):
        dem.luot.clear()
        t0 = time.perf_counter()
        try:
            r = engine.query(cau_hoi)
        except (httpx.HTTPError, ResponseError, ConnectionError, OSError) as e:
            loi.append(f"{type(e).__name__}: {e}")
            print(f"  lỗi lần {lan}: {loi[-1][:120]}", flush=True)
            time.sleep(10 * lan)
            continue
        assert isinstance(r, Response), "query engine phải tắt streaming"
        giay = time.perf_counter() - t0
        eval_ns = tong(dem.luot, "eval_duration")
        so_token_ra = tong(dem.luot, "eval_count")
        return {
            "ket_qua": "chua_cham",
            "tra_loi": str(r).strip(),
            "nguon": list(dict.fromkeys(node_label(n) for n in r.source_nodes)),
            "bang_chung": [{"nguon": node_label(n), "diem": round(n.score, 4) if n.score is not None else None,
                            **({"vi_tri": vi_tri_goc(cfg, n.node.metadata, n.node.get_content())} if cfg else {}),
                            "doan": n.node.get_content()[:DO_DAI_BANG_CHUNG]} for n in r.source_nodes],
            "thoi_gian_s": round(giay, 2),
            "so_lan_thu": lan,
            "loi": loi,
            "so_luot_llm": len(dem.luot),
            "token_vao": tong(dem.luot, "prompt_eval_count"),
            "token_ra": so_token_ra,
            "token_moi_giay": round(so_token_ra / (eval_ns / 1e9), 1) if so_token_ra and eval_ns else None,
            **({"ngu_canh_co_doan_dung": any(dung(n, nhan) for n in r.source_nodes)} if dung and nhan else {}),
        }
    # Lỗi là một outcome: vẫn ghi câu vào kết quả, tính riêng trong tom_tat thay vì bỏ qua
    return {"ket_qua": "loi", "tra_loi": "", "nguon": [], "bang_chung": [], "thoi_gian_s": None,
            "so_lan_thu": SO_LAN_THU, "loi": loi}
```

### 94. Chấm câu trả lời bằng evaluator của LlamaIndex (BatchEvalRunner)

`eval/evaluate_answers.py`: diem_evaluator (dòng 74–94)

```python
def diem_evaluator(llm: LLM, cau_hoi: list[str], responses: list[Response]) -> dict[str, list[float | None]]:
    """Chấm bằng BatchEvalRunner; bỏ qua bài không có ngữ cảnh (closed-book) cho faithfulness/relevancy.

    Mỗi danh sách trả về dài bằng `responses` (None ở câu không có ngữ cảnh) để chỉ số i khớp đúng câu hỏi i.
    """
    co_ngu_canh = [bool(r.source_nodes) for r in responses]
    ket: dict[str, list[float | None]] = {}
    if any(co_ngu_canh):
        runner = BatchEvalRunner(
            {"faithfulness": FaithfulnessEvaluator(llm=llm), "relevancy": RelevancyEvaluator(llm=llm)},
            workers=2,
            show_progress=True,
        )
        kq = runner.evaluate_responses(
            queries=[q for q, ok in zip(cau_hoi, co_ngu_canh) if ok],
            responses=[r for r, ok in zip(responses, co_ngu_canh) if ok],
        )
        for ten, ds in kq.items():
            diem = iter(ds)
            ket[ten] = [next(diem).passing if ok else None for ok in co_ngu_canh]
    return ket
```

### 95. Bọc sentence-transformers thành Embeddings của LangChain

`eval/so_sanh_langchain.py`: STEmbeddings (dòng 40–51)

```python
class STEmbeddings(Embeddings):
    """sentence-transformers -> giao diện Embeddings của LangChain, cùng cách nạp với make_local_embedding()."""

    def __init__(self, model_name: str, device: str, fp16: bool) -> None:
        self.model = SentenceTransformer(model_name, device=device,
                                         model_kwargs={"torch_dtype": torch.float16} if fp16 else {})

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, batch_size=4, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()
```

## I. Giao diện và lab

### 96. Hiện nguồn trích dẫn trong giao diện Gradio

`app/app.py`: hien_thi_nguon (dòng 90–102)

```python
def hien_thi_nguon(nodes: list[NodeWithScore]) -> str:
    if not nodes:
        return "_Không có trích đoạn nào._"
    parts: list[str] = []
    for i, n in enumerate(nodes, start=1):
        noi_dung = n.node.get_content().strip()
        # Mở đúng đoạn gốc: file tầng 2 + số dòng (mức truy nguồn là văn bản/Điều, không có số trang PDF)
        parts.append(
            f"**[{i}] {node_label(n)}** — score `{n.score or 0:.4f}`\n\n"
            f"`{vi_tri_goc(cfg, n.node.metadata, noi_dung)}`\n\n"
            f"<details><summary>{' '.join(noi_dung[:120].split())}…</summary>\n\n{noi_dung}\n\n</details>"
        )
    return "\n\n---\n\n".join(parts)
```

### 97. Ghi nhật ký câu hỏi của người dùng

`app/app.py`: ghi_log (dòng 66–79)

```python
def ghi_log(question: str, nodes: list[NodeWithScore], tra_loi: str, cau_hinh: dict[str, object]) -> None:
    """Ghi lại câu hỏi thật của người dùng để mở rộng bộ đánh giá (nguồn dữ liệu cho Chương 5)."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cau_hoi": question,
                "cau_hinh": cau_hinh,
                "nguon": [node_label(n) for n in nodes],
                "tra_loi": tra_loi,
            }, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"Không ghi được log câu hỏi: {e}")
```

### 98. Chia cố định bằng SentenceSplitter, gắn số Điều theo vị trí ký tự (lab)

`lab/chung.py`: dieu_trong_khoang (dòng 46–53), chia_co_dinh (dòng 56–67)

```python
def dieu_trong_khoang(text: str, dau: int, cuoi: int) -> list[str]:
    """Các Điều có nội dung giao với đoạn text[dau:cuoi]. Mỗi Điều kéo dài từ heading của nó tới heading kế tiếp."""
    moc = [(m.start(), m[1]) for m in DIEU.finditer(text)] + [(len(text), "")]
    ket: list[str] = []
    for (bd, so), (kt, _) in zip(moc, moc[1:]):
        if bd < cuoi and kt > dau and so not in ket:
            ket.append(so)
    return ket

def chia_co_dinh(text: str, van_ban: str, chunk_size: int, chunk_overlap: int = 20) -> list[TextNode]:
    """Cách chia mặc định của LlamaIndex: SentenceSplitter cắt theo số token (tokenizer tiktoken), không biết Điều.

    Metadata `cac_dieu` gắn SAU khi cắt, theo vị trí ký tự của đoạn trong văn bản: một đoạn vắt qua hai Điều
    được ghi cả hai.
    """
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes: list[TextNode] = []
    for n in splitter.get_nodes_from_documents([Document(text=text)]):
        assert isinstance(n, TextNode) and n.start_char_idx is not None and n.end_char_idx is not None
        nodes.append(gan_metadata(n, van_ban, dieu_trong_khoang(text, n.start_char_idx, n.end_char_idx)))
    return nodes
```

### 99. Chia văn bản theo Điều trong lab (lời giải)

`lab/dap_an.py`: HEADING (dòng 9–9), chia_theo_dieu (dòng 16–27)

```python
HEADING = re.compile(r"(?m)^(?=#{1,4} )")

def chia_theo_dieu(text: str, van_ban: str, chunk_size: int = 0) -> list[TextNode]:
    nodes: list[TextNode] = []
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=20) if chunk_size else None
    for khoi in HEADING.split(text):
        m = DIEU.match(khoi)
        if not m:
            continue  # tiêu đề văn bản, tên Chương: không thuộc Điều nào
        tieu_de, _, than = khoi.partition("\n")
        noi_dung = f"{tieu_de.lstrip('# ').strip()}\n{than.strip()}".strip()
        doan = splitter.split_text(noi_dung) if splitter else [noi_dung]
        nodes += [gan_metadata(TextNode(text=d), van_ban, [m[1]]) for d in doan]
    return nodes
```

### 100. Sắp xếp Node theo hiệu lực QĐ 3183 trong lab (lời giải)

`lab/dap_an.py`: SUA_DOI_3183 (dòng 13–13), ap_dung (dòng 30–35), sap_xep_theo_phien_ban (dòng 38–53)

```python
SUA_DOI_3183: dict[str, int | None] = {"6": None, "7": None, "9": 2025, "10": 2025}

def ap_dung(n: NodeWithScore, khoa: int) -> bool | None:
    """Node là mục sửa đổi của QĐ 3183: True/False = áp dụng/không áp dụng cho khóa; None = không phải mục sửa đổi."""
    if n.node.metadata.get("van_ban") != "qd3183":
        return None
    tu = [SUA_DOI_3183[d] for d in cac_dieu(n) if d in SUA_DOI_3183]
    return any(t is None or khoa >= t for t in tu) if tu else None

def sap_xep_theo_phien_ban(nodes: list[NodeWithScore], cau_hoi: str) -> list[NodeWithScore]:
    khoa = khoa_trong_cau_hoi(cau_hoi)
    if khoa is None:
        return nodes  # không biết khóa: giữ thứ tự của retriever (bản gốc và bản sửa đổi đều có thể đúng)
    da_sua = {d for d, tu in SUA_DOI_3183.items() if tu is None or khoa >= tu}

    def hang(n: NodeWithScore) -> int:
        if ap_dung(n, khoa):
            return 0  # mục sửa đổi áp dụng cho khóa này
        if ap_dung(n, khoa) is False:
            return 3  # mục sửa đổi không áp dụng cho khóa này
        if n.node.metadata.get("van_ban") == "qc2021" and set(cac_dieu(n)) & da_sua:
            return 2  # Điều gốc đã bị sửa cho khóa này
        return 1

    return sorted(nodes, key=hang)  # sorted ổn định: cùng hạng thì giữ thứ tự điểm của retriever
```
