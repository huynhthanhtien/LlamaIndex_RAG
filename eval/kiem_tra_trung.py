"""Tìm câu trong tập kiểm chứng gần trùng câu dev (rò rỉ đánh giá).

Nhận xét tuần 6 (ý 3): "4 câu kiểm chứng gần trùng ý dev — thay hoặc báo riêng". So mọi câu kiểm chứng với mọi câu
dev (bộ 01, 02, đợt 1–3, cau_hoi_danh_gia.json, 56 câu của eval/results/cau-hoi01.md) theo ba cách:
  - chữ: tỉ lệ giống nhau (difflib) sau khi viết thường, bỏ dấu câu — bắt câu chép gần nguyên văn;
  - nhãn: hai câu cùng trỏ tới ít nhất một Node đúng (luật chấm eval/luat_cham.py) — hỏi cùng một chỗ trong văn bản;
  - nghĩa (tùy chọn --embedding): cosine embedding hai câu, bằng model embedding của profile (qua MODEL_SERVER_URL nếu
    có, không thì nạp tại chỗ).
Một cặp bị báo khi chữ >= NGUONG_CHU, hoặc cùng Node và (chữ >= NGUONG_CHU_CUNG_NODE hoặc nghĩa >= NGUONG_NGHIA).
Cùng Node một mình không bị báo: hỏi cùng Điều bằng cách khác là điều tập kiểm chứng cần có.

    venv/bin/python eval/kiem_tra_trung.py [--embedding]     # ghi eval/results/trung-lap.md
"""
import argparse
import difflib
import json
import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from llama_index.core.schema import NodeWithScore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import get_config
from luat_cham import BO_CAU_HOI, BO_KIEM_CHUNG, BO_NGOAI_PHAM_VI, ChamDung, chuan_hoa_nhan
from processed_loader import load_corpus_nodes

NGUONG_CHU = 0.75
NGUONG_CHU_CUNG_NODE = 0.5
NGUONG_NGHIA = 0.85


def chuan_hoa(cau: str) -> str:
    cau = unicodedata.normalize("NFC", cau).lower()
    return " ".join(re.sub(r"[^\w\s]", " ", cau).split())


def giong_chu(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, chuan_hoa(a), chuan_hoa(b)).ratio()


def cosine(u: list[float], v: list[float]) -> float:
    tu = sum(x * y for x, y in zip(u, v, strict=True))
    mau = math.sqrt(sum(x * x for x in u)) * math.sqrt(sum(y * y for y in v))
    return tu / mau if mau else 0.0


@dataclass(frozen=True)
class Cau:
    nguon: str
    id: str
    question: str
    node: frozenset[int]  # Node mà nhãn trỏ tới (rỗng nếu câu không có nhãn Node)


def doc_bo(ten_file: str, dung: ChamDung | None, nodes: list[NodeWithScore]) -> list[Cau]:
    ds: list[dict[str, str | list[str]]] = json.loads((ROOT / "eval" / ten_file).read_text(encoding="utf-8"))
    ket: list[Cau] = []
    for i, q in enumerate(ds, start=1):
        nhan = q.get("dieu_dung")
        node = frozenset(j for j, n in enumerate(nodes) if dung(n, chuan_hoa_nhan(nhan))) if dung and nhan else frozenset[int]()
        ket.append(Cau(ten_file, str(q.get("id", str(i))), str(q["question"]), node))
    return ket


def doc_phien_56_cau() -> list[Cau]:
    p = ROOT / "eval" / "results" / "cau-hoi01.md"
    if not p.exists():
        return []
    dong = [m[1].strip() for m in (re.match(r"^\d+\.\s*(.+)$", x.strip()) for x in p.read_text(encoding="utf-8").splitlines()) if m]
    return [Cau("cau-hoi01.md", str(i), q, frozenset[int]()) for i, q in enumerate(dong, start=1)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedding", action="store_true", help="so thêm theo nghĩa bằng model embedding của profile")
    args = ap.parse_args()

    cfg = get_config()
    nodes = [NodeWithScore(node=n) for n in load_corpus_nodes(cfg)]
    dev = [c for f, d in BO_CAU_HOI for c in doc_bo(f, d, nodes)]
    dev += doc_bo("cau_hoi_danh_gia.json", None, nodes) + doc_phien_56_cau()
    test = [c for f, d in BO_KIEM_CHUNG for c in doc_bo(f, d, nodes)] + doc_bo(BO_NGOAI_PHAM_VI, None, nodes)

    vec: dict[str, list[float]] = {}
    if args.embedding:
        from llama_index.core import Settings

        from index_builder import setup_embedding

        setup_embedding(cfg)
        cau = sorted({c.question for c in dev + test})
        vec = dict(zip(cau, (Settings.embed_model.get_query_embedding(q) for q in cau), strict=True))

    bao: list[tuple[Cau, Cau, float, bool, float | None, str]] = []
    for t in test:
        for d in dev:
            chu = giong_chu(t.question, d.question)
            cung_node = bool(t.node & d.node)
            nghia = cosine(vec[t.question], vec[d.question]) if vec else None
            if chu >= NGUONG_CHU:
                ly_do = "gần nguyên văn"
            elif cung_node and chu >= NGUONG_CHU_CUNG_NODE:
                ly_do = "cùng Node, chữ gần giống"
            elif cung_node and nghia is not None and nghia >= NGUONG_NGHIA:
                ly_do = "cùng Node, cùng nghĩa"
            else:
                continue
            bao.append((t, d, chu, cung_node, nghia, ly_do))

    so_cau_test = len({(t.nguon, t.id) for t, *_ in bao})
    dong = ["# Câu kiểm chứng gần trùng câu dev", "",
            f"So {len(test)} câu kiểm chứng với {len(dev)} câu dev. Ngưỡng: chữ ≥ {NGUONG_CHU}; hoặc cùng Node và "
            f"(chữ ≥ {NGUONG_CHU_CUNG_NODE}{f' hoặc nghĩa ≥ {NGUONG_NGHIA}' if vec else ''})."
            f"{'' if vec else ' Chưa so theo nghĩa (chạy lại với --embedding).'}", "",
            f"**{so_cau_test} câu kiểm chứng** có ít nhất một cặp bị báo ({len(bao)} cặp).", "",
            "| Câu kiểm chứng | Câu dev | Chữ | Cùng Node | Nghĩa | Lý do |", "|---|---|---|---|---|---|"]
    for t, d, chu, cung_node, nghia, ly_do in sorted(bao, key=lambda x: (x[0].id, -x[2])):
        dong.append(f"| {t.id}: {t.question} | {d.nguon}#{d.id}: {d.question} | {chu:.2f} | "
                    f"{'có' if cung_node else 'không'} | {'—' if nghia is None else f'{nghia:.2f}'} | {ly_do} |")
    out = ROOT / "eval" / "results" / "trung-lap.md"
    out.write_text("\n".join(dong) + "\n", encoding="utf-8")
    print("\n".join(dong))
    print(f"Đã ghi {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
