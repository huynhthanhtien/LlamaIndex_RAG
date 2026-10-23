"""Đóng băng cấu hình trước khi chạy tập kiểm chứng.

Nhận xét tuần 6 (ý 2): "đóng băng corpus, luật đúng ở mức Điều/Node và cấu hình trước khi chạy tập kiểm chứng chưa
dùng để chỉnh". File manifest eval/results/dong-bang.json ghi lại mọi thứ quyết định con số đo được:
  - mã nguồn ảnh hưởng tới kết quả (src/*.py, luật chấm, độ đo, evaluate.py) theo sha256;
  - fingerprint corpus (sha256 từng file tầng 2, phiên bản loader, model embedding);
  - cấu hình chốt (cfg.mo_ta() của profile server);
  - luật chấm từng bộ (mức Điều; dev đợt 1–3 chấm theo văn bản/Điều nên Điều cắt nhiều Node được tính đúng khi lấy
    được bất kỳ mảnh nào);
  - sha256 file câu hỏi dev và kiểm chứng.
So theo NỘI DUNG chứ không theo commit: commit chính file manifest làm đổi HEAD nhưng không đổi những gì được đo.
`evaluate.py --tap-kiem-chung` chỉ chạy khi trạng thái hiện tại khớp manifest.

    RAG_PROFILE=server venv/bin/python eval/dong_bang.py tao    # code và dữ liệu phải đã commit
    RAG_PROFILE=server venv/bin/python eval/dong_bang.py kiem   # in các mục lệch so với manifest
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

MANIFEST = ROOT / "eval" / "results" / "dong-bang.json"
# Khóa ghi lại để tra cứu nhưng không đem so: phụ thuộc máy chạy, không đổi cách hệ thống xếp hạng
BO_QUA_KHI_SO = {"cau_hinh.embed_device", "cau_hinh.persist_dir"}
LUAT_CHAM = {
    "dung_bo_01": "mức Điều: Điều của QC 2021 (phần chính) hoặc mục QĐ 3183 sửa đổi chính Điều đó",
    "dung_bo_02": "mức Điều: chỉ Node QĐ 3183 (mục sửa đổi Điều thuộc nhãn hoặc Điều của chính QĐ)",
    "dung_bo_dev": "mức văn bản/Điều theo tiền tố file (bh:/sd: cho Điều ban hành/mục sửa đổi): Điều cắt thành nhiều "
                   "Node đúng khi lấy được bất kỳ mảnh nào",
}


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def ma_nguon() -> list[Path]:
    """File code quyết định kết quả truy hồi (đổi một dòng ở đây là phải đóng băng lại)."""
    return sorted(ROOT.glob("src/*.py")) + [ROOT / "eval" / f for f in ("evaluate.py", "luat_cham.py", "metrics.py")]


def chua_commit() -> str:
    """Thay đổi chưa commit trong code/dữ liệu đo (bỏ qua eval/results, nơi ghi kết quả)."""
    return git("status", "--porcelain", "--", "src", "eval", "data/processed", ":!eval/results")


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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lenh", choices=["tao", "kiem"])
    ap.add_argument("--ghi-de", action="store_true", help="tạo lại manifest dù đã có (ghi lý do vào báo cáo)")
    args = ap.parse_args()

    if args.lenh == "kiem":
        khop, dong = kiem_khop()
        print("Khớp manifest đóng băng." if khop else "\n".join(dong))
        sys.exit(0 if khop else 1)

    if chua_commit():
        sys.exit("Code/dữ liệu đo còn thay đổi chưa commit — commit trước khi đóng băng:\n" + chua_commit())
    if MANIFEST.exists() and not args.ghi_de:
        sys.exit(f"Đã có {MANIFEST.relative_to(ROOT)}. Đóng băng lại nghĩa là cấu hình đã đổi sau khi đóng băng: "
                 "dùng --ghi-de và ghi rõ lý do trong báo cáo.")
    tt = trang_thai()
    if tt["profile"] != "server":
        sys.exit("Kết quả chính đo trên profile server: đặt RAG_PROFILE=server")
    manifest = {"thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"), "commit": git("rev-parse", "--short", "HEAD"),
                "nhanh": git("branch", "--show-current"), **tt}
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Đã ghi {MANIFEST.relative_to(ROOT)} (commit {manifest['commit']}). Commit file này rồi mới chạy "
          "`evaluate.py --tap-kiem-chung` (đúng một lần).")


if __name__ == "__main__":
    main()
