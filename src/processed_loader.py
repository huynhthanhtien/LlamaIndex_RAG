"""Đọc văn bản đã làm sạch (tầng 2, data/processed, sinh bởi scripts/clean_md.py) thành TextNode.

Cắt theo heading do clean_md.py dựng: "#" văn bản -> "##" Chương -> "###" Điều -> "####" mục sửa đổi
(văn bản sửa đổi như QĐ 3183). Mỗi Điều / mục sửa đổi là một Node; tên văn bản, Chương, Điều nằm trong
metadata và được ghép vào khi embedding, nên Điều 9 của hai văn bản khác nhau cho vector khác nhau.
"""
import re
import sys
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config

ROOT = Path(__file__).resolve().parent.parent
MAX_TU = 1024  # Điều dài hơn thì cắt nhỏ, như node_parser.parse_by_dieu
MIN_TU_NOI_DUNG = 30  # chữ nằm ngay dưới "#"/"##" (không thuộc Điều nào) ngắn hơn thì bỏ (tiêu đề, dòng trích yếu)
KHONG_EMBED = ["file", "file_goc", "url", "phan"]  # metadata chỉ để lọc / trích dẫn, không đưa vào embedding & prompt
HEADING = re.compile(r"(?m)^(?=#{1,4} )")
SO_DIEU = re.compile(r"Điều (\d+)")

_splitter = SentenceSplitter(chunk_size=MAX_TU, chunk_overlap=50)


def front_matter(text: str) -> tuple[dict[str, str], str]:
    """Tách khối "---" đầu file thành dict và phần thân."""
    _, front, body = text.split("---\n", 2)
    pairs = (line.split(": ", 1) for line in front.strip().splitlines() if ": " in line)
    return {k: v.strip().strip('"') for k, v in pairs}, body


def load_processed(path: Path, ten_hien_thi: str = "") -> list[TextNode]:
    """ten_hien_thi: tên văn bản dùng cho embedding / trích nguồn; rỗng thì lấy heading "#" (tiêu đề OCR)."""
    meta, body = front_matter(path.read_text(encoding="utf-8"))
    ten_van_ban = ten_hien_thi or meta.get("ten_van_ban", "")
    nodes: list[TextNode] = []
    van_ban = chuong = ""
    for block in HEADING.split(body):
        if not block.strip():
            continue
        head, _, rest = block.partition("\n")
        level = len(head) - len(head.lstrip("#"))
        title = head.lstrip("# ").strip()
        if level == 1:
            van_ban, chuong = title, ""
        elif level == 2:
            chuong = title
        if level <= 2:
            # Văn bản không chia Điều (vd quy định 1 trang) có toàn bộ nội dung ngay dưới "#"
            if len(rest.split()) < MIN_TU_NOI_DUNG:
                continue
            phan = "ban_hanh" if van_ban == "Quyết định ban hành" else "noi_dung"
            m = None
        else:
            # Điều ngắn có thể nằm trọn trên dòng heading (rest rỗng) — vẫn tạo Node
            m = SO_DIEU.search(title)
            phan = "ban_hanh" if van_ban == "Quyết định ban hành" else ("sua_doi" if level == 4 else "chinh")
        node_meta: dict[str, str | int] = {
            "van_ban": (f"{van_ban} – {ten_van_ban}" if phan == "ban_hanh" else ten_van_ban) if ten_van_ban else van_ban,
            "chuong": chuong,
            "dieu": m[1] if (m and level == 3) else "",
            "sua_doi_dieu": m[1] if (m and level == 4) else "",
            "phan": phan,
            "file": path.name,
            "file_goc": meta.get("file_goc", ""),
            "url": meta.get("url", ""),
        }
        text = f"{title}\n{rest.strip()}"
        chunks = [text] if len(text.split()) <= MAX_TU else _splitter.split_text(text)
        for j, chunk in enumerate(chunks, start=1):
            node = TextNode(text=chunk, metadata=node_meta | ({"phan_doan": j} if len(chunks) > 1 else {}))
            node.excluded_embed_metadata_keys = KHONG_EMBED
            node.excluded_llm_metadata_keys = KHONG_EMBED
            nodes.append(node)
    return nodes


def corpus_files(cfg: RAGConfig) -> list[Path]:
    """File .md trong cfg.corpus_dir được nạp: khớp tiền tố trong cfg.corpus_files (rỗng = tất cả)."""
    folder = ROOT / cfg.corpus_dir
    if not folder.is_dir():
        raise FileNotFoundError(f"Không thấy {cfg.corpus_dir} — chạy scripts/extract_to_md.py rồi scripts/clean_md.py")
    files = sorted(p for p in folder.glob("*.md") if not p.name.startswith("_"))
    if cfg.corpus_files:
        files = [p for p in files if p.name.startswith(cfg.corpus_files)]
        thieu = [t for t in cfg.corpus_files if not any(p.name.startswith(t) for p in files)]
        if thieu:
            raise FileNotFoundError(f"corpus_files không khớp file nào trong {cfg.corpus_dir}: {thieu}")
    return files


def ten_hien_thi(cfg: RAGConfig, path: Path) -> str:
    return next((ten for tien_to, ten in cfg.ten_van_ban.items() if path.name.startswith(tien_to)), "")


def load_corpus_nodes(cfg: RAGConfig) -> list[TextNode]:
    return [n for p in corpus_files(cfg) for n in load_processed(p, ten_hien_thi(cfg, p))]


if __name__ == "__main__":
    from collections import Counter

    cfg = get_config()
    nodes = load_corpus_nodes(cfg)
    print(f"{len(nodes)} Node từ {len(corpus_files(cfg))} văn bản trong {cfg.corpus_dir}")
    for (f, phan), c in sorted(Counter((str(n.metadata["file"]), str(n.metadata["phan"])) for n in nodes).items()):
        print(f"{c:4}  {phan:9} {f}")
