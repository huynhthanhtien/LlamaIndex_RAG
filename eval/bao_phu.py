"""Độ bao phủ corpus của từng bộ câu hỏi: nhãn `dieu_dung` trỏ tới bao nhiêu Node / văn bản.

Nhận xét tuần 6 (ý 2, 3): con số R@k chỉ nói về phần corpus mà bộ câu hỏi chạm tới. Tập kiểm chứng hiện chỉ hỏi
QC 2021 và QĐ 3183, nên báo cáo phải ghi rõ nó không đại diện cho cả 20 văn bản. Dùng đúng luật chấm của
eval/luat_cham.py để quy nhãn ra Node; không cần model, không cần GPU.

    venv/bin/python eval/bao_phu.py        # ghi eval/results/bao-phu.md
"""
import json
import sys
from collections import Counter
from pathlib import Path

from llama_index.core.schema import NodeWithScore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import get_config
from luat_cham import BO_CAU_HOI, BO_KIEM_CHUNG, ChamDung, chuan_hoa_nhan
from processed_loader import load_corpus_nodes


def node_cua_bo(nodes: list[NodeWithScore], ten_file: str, dung: ChamDung) -> tuple[set[int], int]:
    """(chỉ số các Node mà nhãn của bộ trỏ tới, số câu có nhãn không khớp Node nào)."""
    ds: list[dict[str, str | list[str]]] = json.loads((ROOT / "eval" / ten_file).read_text(encoding="utf-8"))
    phu: set[int] = set()
    khong_khop = 0
    for q in ds:
        nhan = q.get("dieu_dung")
        if not nhan:
            continue
        d = chuan_hoa_nhan(nhan)
        trung = {i for i, n in enumerate(nodes) if dung(n, d)}
        khong_khop += not trung
        phu |= trung
    return phu, khong_khop


def main() -> None:
    nodes = [NodeWithScore(node=n) for n in load_corpus_nodes(get_config())]
    file_cua = [str(n.node.metadata.get("file")) for n in nodes]
    tong_theo_file = Counter(file_cua)
    nhom = {"Dev (bộ 01, 02, các đợt dev)": BO_CAU_HOI, "Kiểm chứng": BO_KIEM_CHUNG}

    dong = ["# Độ bao phủ corpus của các bộ câu hỏi", "",
            f"Corpus: {len(nodes)} Node từ {len(tong_theo_file)} văn bản. Nhãn được quy ra Node bằng luật chấm của "
            "`eval/luat_cham.py` (các đợt dev chấm theo văn bản/Điều nên một nhãn có thể phủ nhiều Node).", "",
            "| Bộ | Node được hỏi tới | Văn bản được hỏi tới | Câu có nhãn không khớp Node |", "|---|---|---|---|"]
    phu_nhom: dict[str, set[int]] = {}
    for ten_nhom, bo in nhom.items():
        gop: set[int] = set()
        for ten_file, dung in bo:
            phu, khong_khop = node_cua_bo(nodes, ten_file, dung)
            gop |= phu
            dong.append(f"| {ten_file} | {len(phu)}/{len(nodes)} | {len({file_cua[i] for i in phu})}/{len(tong_theo_file)} "
                        f"| {khong_khop} |")
        phu_nhom[ten_nhom] = gop
        dong.append(f"| **{ten_nhom}** | **{len(gop)}/{len(nodes)}** | "
                    f"**{len({file_cua[i] for i in gop})}/{len(tong_theo_file)}** | |")
    tat_ca = set().union(*phu_nhom.values())
    dong += [f"| **Tất cả** | **{len(tat_ca)}/{len(nodes)}** | **{len({file_cua[i] for i in tat_ca})}/{len(tong_theo_file)}** | |",
             "", "## Theo văn bản", "",
             "| Văn bản | Số Node | " + " | ".join(nhom) + " |", "|---|---|" + "---|" * len(nhom)]
    for f, tong in sorted(tong_theo_file.items(), key=lambda x: -x[1]):
        cot = [str(sum(1 for i in phu if file_cua[i] == f)) for phu in phu_nhom.values()]
        dong.append(f"| {f} | {tong} | " + " | ".join(cot) + " |")
    chua_hoi = [f for f in tong_theo_file if not any(file_cua[i] == f for i in tat_ca)]
    dong += ["", f"Văn bản chưa có câu hỏi nào: {', '.join(chua_hoi) if chua_hoi else 'không'}.", ""]

    out = ROOT / "eval" / "results" / "bao-phu.md"
    out.write_text("\n".join(dong), encoding="utf-8")
    print("\n".join(dong))
    print(f"Đã ghi {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
