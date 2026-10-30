"""Đọc văn bản đã làm sạch (tầng 2, data/processed, sinh bởi scripts/clean_md.py) thành TextNode.

Cắt theo heading do clean_md.py dựng: "#" văn bản -> "##" Chương -> "###" Điều -> "####" mục sửa đổi
(văn bản sửa đổi như QĐ 3183). Mỗi Điều / mục sửa đổi là một Node; tên văn bản, Chương, Điều nằm trong
metadata và được ghép vào khi embedding, nên Điều 9 của hai văn bản khác nhau cho vector khác nhau.

Thay đổi so với bản cũ (xem docs/bao_cao_cai_tien_bai_nghien_cuu.md):
  - Bỏ hẳn metadata rỗng khỏi Node. Trước đây mọi Node đều mang "chuong: ", "dieu: ",
    "sua_doi_dieu: " kể cả khi rỗng, làm văn bản đưa vào embedding bị nhiễu.
  - Chỉ đưa MỘT trường vào embedding: `nguon_trich` ("Điều 9 — Quy chế ... 2021").
    Các khóa kỹ thuật (file, phan, ...) không còn lọt vào vector.
  - Ghi rõ LOADER_VERSION để index_builder phát hiện khi logic cắt thay đổi.
  - Metadata hiệu lực (tinh_trang, sua_doi/thay_the, khóa áp dụng) đi vào Node để src/phien_ban.py lọc phiên bản;
    không vào embedding, không vào prompt.
"""
import json
import re
import sys
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode, TextNode

# Cho phép `from config import ...` khi chạy file trực tiếp (python src/processed_loader.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config

# Thư mục gốc của repo (src/..); cfg.corpus_dir là đường dẫn tương đối so với đây
ROOT = Path(__file__).resolve().parent.parent
# Hai đơn vị khác nhau: MAX_TU đếm TỪ (tách theo khoảng trắng) để quyết định có cắt Điều hay không, còn
# chunk_size của SentenceSplitter đếm TOKEN theo tokenizer mặc định của LlamaIndex (tiktoken), không phải token của
# model embedding/reranker. Đo 21/10 bằng tokenizer AITeamVN: cặp (câu hỏi, Node) dài nhất 1233 token (< 2048 của
# reranker), 63/118 Node vượt 256 token của embedding profile local.
MAX_TU = 1024  # Điều dài hơn MAX_TU từ thì cắt nhỏ, như node_parser.parse_by_dieu
MIN_TU_NOI_DUNG = 30  # chữ nằm ngay dưới "#"/"##" (không thuộc Điều nào) ngắn hơn thì bỏ (tiêu đề, dòng trích yếu)
LOADER_VERSION = "processed_loader/3"  # đổi khi cách cắt hoặc schema metadata thay đổi

# Quan hệ giữa các văn bản (front matter ghi dạng list JSON) và khóa tuyển sinh áp dụng — dùng cho src/phien_ban.py
QUAN_HE = ("sua_doi", "bi_sua_doi_boi", "thay_the", "bi_thay_the_boi")
KHOA_AP_DUNG = ("ap_dung_khoa_tu", "ap_dung_khoa_den")
# Metadata chỉ để lọc / trích dẫn: không đưa vào prompt
KHONG_LLM = ["file", "file_goc", "url", "phan", *QUAN_HE, *KHOA_AP_DUNG]
# Metadata kỹ thuật: không đưa vào embedding (embedding chỉ nhận `nguon_trich`)
KHONG_EMBED = ["file", "file_goc", "url", "phan", "chuong", "dieu", "sua_doi_dieu", "van_ban"]

# Lookahead độ rộng 0: split ngay TRƯỚC mỗi dòng bắt đầu bằng 1–4 dấu "#" + khoảng trắng, nên heading
# vẫn nằm ở đầu mỗi block (không bị nuốt mất như khi split theo chính heading)
HEADING = re.compile(r"(?m)^(?=#{1,4} )")
# Lấy số Điều trong tiêu đề, vd "Điều 9. Xét tuyển" -> "9", "Sửa đổi Điều 10" -> "10"
SO_DIEU = re.compile(r"Điều (\d+)")

# Chỉ dùng cho Điều quá dài (> MAX_TU từ); cắt theo ranh giới câu, chồng lấn 50 token để không mất ngữ cảnh ở mép
_splitter = SentenceSplitter(chunk_size=MAX_TU, chunk_overlap=50)  # 1024 / 50 token tiktoken (xem MAX_TU)


def front_matter(text: str) -> tuple[dict[str, str], str]:
    """Tách khối "---" đầu file thành dict và phần thân."""
    # File bắt đầu bằng "---\n", nên phần tử đầu (trước dấu "---" thứ nhất) rỗng, bỏ qua;
    # maxsplit=2 để các "---" trong thân văn bản (vd kẻ ngang) không bị cắt tiếp
    _, front, body = text.split("---\n", 2)
    # Front matter dạng "khoa: gia_tri" mỗi dòng; chỉ tách ở ": " đầu tiên vì giá trị có thể chứa ": "
    pairs = (line.split(": ", 1) for line in front.strip().splitlines() if ": " in line)
    # Bỏ ngoặc kép bao quanh giá trị (YAML kiểu "..."); giá trị JSON như '["a", "b"]' giữ nguyên vì không bắt đầu bằng '"'
    return {k: v.strip().strip('"') for k, v in pairs}, body


def danh_sach_so_hieu(gia_tri: str) -> str:
    """'["2451/TB-ĐHSG", "2567/TB-ĐHSG"]' -> "2451/TB-ĐHSG; 2567/TB-ĐHSG" (metadata Node giữ kiểu chuỗi)."""
    try:
        ds = json.loads(gia_tri)
    except json.JSONDecodeError:
        # Không phải JSON (ghi tay một số hiệu trần) -> dùng nguyên chuỗi
        return gia_tri.strip()
    # JSON hợp lệ nhưng là giá trị đơn (vd một chuỗi) cũng đổi về str
    return "; ".join(str(x) for x in ds) if isinstance(ds, list) else str(ds)


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


def ten_hien_thi(cfg: RAGConfig, path: Path) -> str:
    """Tên văn bản cấu hình cho file (khớp tiền tố đầu tiên trong cfg.ten_van_ban); không có thì trả "" ."""
    return next((ten for tien_to, ten in cfg.ten_van_ban.items() if path.name.startswith(tien_to)), "")


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


def load_corpus_nodes(cfg: RAGConfig) -> list[TextNode]:
    """Toàn bộ Node của corpus, theo thứ tự file rồi thứ tự trong file."""
    return [n for p in corpus_files(cfg) for n in load_processed(p, ten_hien_thi(cfg, p))]


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


if __name__ == "__main__":
    # Chạy thử: in số Node mỗi file và văn bản thực sự đưa vào embedding để kiểm tra bằng mắt
    cfg = get_config()
    nodes = load_corpus_nodes(cfg)
    tk = thong_ke(nodes)
    print(f"{tk['tong_so_node']} Node từ {tk['so_van_ban']} văn bản trong {cfg.corpus_dir}")
    theo_file = tk["theo_file"]
    assert isinstance(theo_file, dict)  # thu hẹp kiểu `object` cho Pylance strict
    for f, c in theo_file.items():
        print(f"{c:4}  {f}")
    print("\nVí dụ văn bản đưa vào embedding của Node đầu tiên:")
    # MetadataMode.EMBED: metadata (chỉ `nguon_trich`) + text, đúng như model embedding nhận
    print(nodes[0].get_content(metadata_mode=MetadataMode.EMBED)[:200] if nodes else "(rỗng)")
