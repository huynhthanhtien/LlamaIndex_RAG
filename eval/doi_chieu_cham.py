"""Đối chiếu nhãn người chấm với nhãn judge AI của một lượt chạy `eval/results/danh-gia-tra-loi-*/`.

Nhận xét tuần 7: "94/99 là kết quả Claude chấm đang chờ người rà lại, không phải 94 nhãn chuẩn do người xác nhận"
(ý 10); "mức tự tin của judge không phải nhãn chuẩn độc lập" (ý 3); "đúng nội dung và đúng nguồn là hai tiêu chí"
(ý 2); "phân loại lỗi nhãn, thiếu văn bản, retrieval, rerank và synthesis" (ý 4). Script này không gọi LLM, chỉ đọc
các file chấm trong thư mục lượt chạy:

  cham-tay-<tên>.csv   mỗi người một bản, chấm độc lập (không mở file của judge trước khi chấm xong)
  cham-tay-claude.csv  judge AI: tên file chứa "claude"/"ai" hoặc cột nguoi_cham ghi Claude/AI -> KHÔNG là người chấm
  cham-tay.csv         nhãn chốt sau khi hai người họp đối chiếu; câu nào có nhãn ở đây thì lấy nhãn này

Ghi `doi-chieu-cham.md` cạnh các file chấm:
  1. số câu có nhãn người xác nhận; câu hai người lệch mà chưa chốt thì liệt kê để họp;
  2. judge so với người: trùng x/n và Cohen κ (đúng/không đúng), tách theo `do_tu_tin` của judge, kèm câu lệch;
  3. bảng chéo nội dung (`ket_qua`) × nguồn (`trich_dan_sai`) theo nhãn người;
  4. loại lỗi: `ly_do` bắt đầu bằng một mã trong LOAI_LOI, vd "synthesis: lấy bảng khóa 2021".

    venv/bin/python eval/doi_chieu_cham.py eval/results/danh-gia-tra-loi-2026-10-23-2336-a6e63eb-chua-commit
    venv/bin/python eval/doi_chieu_cham.py <thư mục> --mau 15   # bốc mẫu câu judge chấm "cao" để người rà
"""
import argparse
import csv
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import cohen_kappa

Khoa = tuple[str, str]  # (bộ câu hỏi, id câu)
Dong = dict[str, str]

# Nhãn tính là trả lời đúng: rubric hai mức (dung/sai) và nhãn câu ngoài phạm vi (tu_choi_dung)
DUNG = {"dung", "tu_choi_dung"}
LOAI_LOI = ("nhan", "thieu_van_ban", "retrieval", "rerank", "synthesis")
FILE_CHOT = "cham-tay.csv"


def doc_csv(path: Path) -> dict[Khoa, Dong]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return {(r["bo"], r["id"]): {k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(fh)}


def la_judge(path: Path, dong: dict[Khoa, Dong]) -> bool:
    """File của judge AI: theo tên file hoặc theo cột nguoi_cham (file người chấm phải ghi tên người thật)."""
    ten = path.stem.removeprefix("cham-tay-").lower()
    if ten in ("claude", "ai") or ten.startswith(("claude-", "ai-")):
        return True
    nguoi = {r.get("nguoi_cham", "").lower() for r in dong.values() if r.get("ket_qua")}
    return any("claude" in x or "(ai)" in x for x in nguoi)


def da_cham(dong: dict[Khoa, Dong]) -> dict[Khoa, Dong]:
    """Chỉ giữ câu đã có nhãn; `loi` (không có câu trả lời) do script gán, không phải nhãn của người."""
    return {k: r for k, r in dong.items() if r.get("ket_qua") and r["ket_qua"] != "loi"}


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


def loai_loi(ly_do: str) -> str | None:
    """"synthesis: lấy bảng khóa 2021" -> "synthesis"; không ghi mã thì None."""
    ma = ly_do.split(":", 1)[0].strip().lower()
    return ma if ma in LOAI_LOI else None


def la_dung(r: Dong) -> bool:
    return r["ket_qua"] in DUNG


def chon_mau(judge: dict[Khoa, Dong], n: int, seed: int = 42) -> list[Khoa]:
    """n câu ngẫu nhiên trong các câu judge chấm đúng, tự tin cao và không trích sai (ý 3: kiểm mẫu cao-confidence).

    Bốc theo thứ tự dòng trong file (thứ tự câu hỏi trong các bộ), nên cùng file + cùng seed luôn ra cùng mẫu.
    """
    cao = [k for k, r in judge.items() if la_dung(r) and r.get("do_tu_tin") == "cao" and not r.get("trich_dan_sai")]
    return sorted(random.Random(seed).sample(cao, min(n, len(cao))))


def ten_cau(k: Khoa) -> str:
    return f"{k[0].removesuffix('.json').removeprefix('dev_questions_')}#{k[1]}"


def bang_judge(judge: dict[Khoa, Dong], nguoi: dict[Khoa, Dong]) -> list[str]:
    chung = sorted(set(judge) & set(nguoi))
    if not chung:
        return ["Chưa có câu nào vừa có nhãn judge vừa có nhãn người."]
    a = [str(la_dung(judge[k])) for k in chung]
    b = [str(la_dung(nguoi[k])) for k in chung]
    dong = [f"Trên {len(chung)} câu có cả hai nhãn: trùng đúng/không đúng {sum(x == y for x, y in zip(a, b))}/{len(chung)}, "
            f"κ = {cohen_kappa(a, b):.2f}.", "",
            "| Mức tự tin của judge | Số câu | Người đồng ý với judge |", "|---|---|---|"]
    for muc in sorted({judge[k].get("do_tu_tin") or "—" for k in chung}):
        ds = [k for k in chung if (judge[k].get("do_tu_tin") or "—") == muc]
        dong.append(f"| {muc} | {len(ds)} | {sum(la_dung(judge[k]) == la_dung(nguoi[k]) for k in ds)}/{len(ds)} |")
    lech = [k for k in chung if la_dung(judge[k]) != la_dung(nguoi[k])
            or bool(judge[k].get("trich_dan_sai")) != bool(nguoi[k].get("trich_dan_sai"))]
    dong += ["", "Câu judge lệch người (nội dung hoặc nguồn): " + (", ".join(
        f"{ten_cau(k)} (judge {judge[k]['ket_qua']}{'+trích sai' if judge[k].get('trich_dan_sai') else ''}, "
        f"người {nguoi[k]['ket_qua']}{'+trích sai' if nguoi[k].get('trich_dan_sai') else ''})" for k in lech) or "không có")]
    return dong


def bang_cheo(nguoi: dict[Khoa, Dong], co_cot_nguon: bool) -> list[str]:
    """Nội dung × nguồn: một tỉ lệ accuracy gộp che mất câu đúng nội dung nhưng trích sai văn bản (ý 2)."""
    if not co_cot_nguon:
        return ["File của người chấm chưa có cột `trich_dan_sai` — chưa lập được bảng chéo nội dung × nguồn."]
    o = Counter((la_dung(r), not r.get("trich_dan_sai")) for r in nguoi.values())
    return ["| | Nguồn đúng | Nguồn sai (`trich_dan_sai = co`) |", "|---|---|---|",
            f"| **Nội dung đúng** | {o[(True, True)]} | {o[(True, False)]} |",
            f"| **Nội dung sai** | {o[(False, True)]} | {o[(False, False)]} |",
            "", f"Đạt cả hai tiêu chí: {o[(True, True)]}/{len(nguoi)}."]


def bang_loai_loi(nguoi: dict[Khoa, Dong]) -> list[str]:
    loi = {k: r for k, r in nguoi.items() if not la_dung(r) or r.get("trich_dan_sai")}
    if not loi:
        return ["Không có câu sai hoặc trích sai trong nhãn người."]
    c = Counter(loai_loi(r.get("ly_do", "")) or "chua_phan_loai" for r in loi.values())
    dong = ["| Loại lỗi | Số câu | Câu |", "|---|---|---|"]
    for ma in [*LOAI_LOI, "chua_phan_loai"]:
        if c[ma]:
            ds = [ten_cau(k) for k, r in sorted(loi.items()) if (loai_loi(r.get("ly_do", "")) or "chua_phan_loai") == ma]
            dong.append(f"| {ma} | {c[ma]} | {', '.join(ds)} |")
    return dong


def bao_cao(thu_muc: Path) -> str:
    nguoi_cham: dict[str, dict[Khoa, Dong]] = {}
    judge: dict[Khoa, Dong] = {}
    co_cot_nguon = True
    for f in sorted(thu_muc.glob("cham-tay-*.csv")):
        dong = doc_csv(f)
        if la_judge(f, dong):
            judge.update(da_cham(dong))
            continue
        co_cot_nguon &= all("trich_dan_sai" in r for r in dong.values())
        nguoi_cham[f.stem.removeprefix("cham-tay-")] = da_cham(dong)
    chot = da_cham(doc_csv(thu_muc / FILE_CHOT)) if (thu_muc / FILE_CHOT).exists() else {}
    nguoi, lech = nhan_nguoi(nguoi_cham, chot)
    tong = len(doc_csv(thu_muc / FILE_CHOT)) if (thu_muc / FILE_CHOT).exists() else len(judge)

    md = [f"# Đối chiếu chấm tay — {thu_muc.name}", "",
          f"- Người chấm: {', '.join(nguoi_cham) or 'chưa có'}; nhãn chốt trong `{FILE_CHOT}`: {len(chot)} câu.",
          f"- Judge AI: {len(judge)} câu ({sum(la_dung(r) for r in judge.values())} đúng). "
          "Đây **không** phải nhãn chuẩn; chỉ nhãn người dưới đây mới là kết quả đã xác nhận.",
          f"- **Có nhãn người xác nhận: {len(nguoi)}/{tong} câu**, trong đó đúng {sum(la_dung(r) for r in nguoi.values())}.",
          f"- Hai người lệch, chưa chốt ({len(lech)}): {', '.join(ten_cau(k) for k in lech) or 'không có'}.",
          "", "## Judge so với người", "", *bang_judge(judge, nguoi),
          "", "## Nội dung × nguồn (nhãn người)", "", *bang_cheo(nguoi, co_cot_nguon and bool(nguoi_cham)),
          "", "## Loại lỗi (nhãn người)", "", *bang_loai_loi(nguoi), ""]
    return "\n".join(md)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("thu_muc", type=Path, help="thư mục eval/results/danh-gia-tra-loi-*")
    ap.add_argument("--mau", type=int, default=0, help="in N câu ngẫu nhiên judge chấm đúng + cao để người rà")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    thu_muc: Path = args.thu_muc
    if not thu_muc.is_dir():
        sys.exit(f"Không thấy thư mục {thu_muc}")
    if args.mau:
        judge: dict[Khoa, Dong] = {}
        for f in sorted(thu_muc.glob("cham-tay-*.csv")):
            dong = doc_csv(f)
            if la_judge(f, dong):
                judge.update(da_cham(dong))
        print(f"Mẫu {args.mau} câu (seed {args.seed}):", ", ".join(ten_cau(k) for k in chon_mau(judge, args.mau, args.seed)))
        return
    md = bao_cao(thu_muc)
    (thu_muc / "doi-chieu-cham.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
