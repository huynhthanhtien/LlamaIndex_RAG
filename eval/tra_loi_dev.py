"""Sinh câu trả lời cho các bộ dev (và bộ 01/02) để chấm tay, kèm số token và độ trễ lấy từ Ollama.

Thay cho wrapper ngoài repo dùng ngày 13/10 (eval/results/logs/2026-10-13_dot2/): cùng định dạng file .md
(tra-loi-dev-*.md) để so được với lần trước, thêm file .json ghi cho từng câu:
  - thời gian truy hồi + sinh của lần gọi thành công (lần thử lỗi mạng không tính vào độ trễ),
  - số lượt gọi LLM (response_mode=compact có thể chia nhiều lượt khi ngữ cảnh dài),
  - prompt_eval_count / eval_count / eval_duration do Ollama trả về (số token thật, không ước lượng).

Cấu hình so sánh:
  cu   = vector top-10, không rerank, không lọc phiên bản (cấu hình mặc định trước 16/10)
  moi  = cấu hình mặc định profile server hiện tại (rerank 2048 token top-3 + lọc phiên bản)

Theo nhận xét tuần 6 (ý 4: "lưu câu trả lời, evidence, rubric, số token/latency và xử lý lỗi như một outcome"):
  - mỗi câu có `ket_qua`: "loi" khi hết số lần thử vẫn không có câu trả lời, ngược lại "chua_cham"; người chấm sửa
    thành một nhãn trong KET_QUA_CHAM theo docs/rubric-cham-tra-loi.md rồi chạy --tong-hop để đếm lại;
  - `bang_chung`: các trích đoạn đã đưa vào LLM (nhãn nguồn, điểm, nội dung) để kiểm lại vì sao đúng/sai;
  - câu khởi động lỗi không làm dừng cả lần chạy (lần 17/10 cấu hình cũ dừng ngay vì Ollama báo lỗi 500);
  - --chi-cau-loi: chạy lại đúng các câu "loi" của file kết quả cùng --nhan, giữ nguyên các câu đã có/đã chấm;
  - chạy được bộ ngoài phạm vi (eval/test_kiem_chung_ngoai.json): ghi kèm `hanh_vi_mong_doi` để chấm từ chối.
    Bộ này thuộc tập kiểm chứng: chỉ chạy sau khi đóng băng (eval/dong_bang.py).

    RAG_PROFILE=server venv/bin/python eval/tra_loi_dev.py --cau-hinh cu,moi \\
        --bo dev_questions_dot1.json,dev_questions_dot2.json,dev_questions_dot3.json --nhan 2026-10-16
    ... eval/tra_loi_dev.py --cau-hinh cu --nhan 2026-10-17 --chi-cau-loi     # bổ sung các câu lỗi của lần trước
    ... eval/tra_loi_dev.py --tong-hop eval/results/tra-loi-dev-dot2-moi-2026-10-17.json   # sau khi chấm tay
"""
import argparse
import dataclasses
import json
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from ollama import ResponseError
from llama_index.core import Settings
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager, CBEventType, EventPayload
from llama_index.core.callbacks.base_handler import BaseCallbackHandler
from llama_index.core.schema import NodeWithScore

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from config import RAGConfig, get_config
from index_builder import build_or_load_index
from query_engine import build_query_engine
from retriever import node_label

CAU_HINH: dict[str, dict[str, object]] = {
    "cu": {"use_rerank": False, "loc_phien_ban": False},
    "moi": {},
}
SO_LAN_THU = 4
# Nhãn chấm theo rubric (docs/rubric-cham-tra-loi.md); "loi" và "chua_cham" do script gán
KET_QUA_CHAM = ("dung", "mot_phan", "sai", "tu_choi_dung", "tu_choi_sai", "bia")
KET_QUA_HOP_LE = (*KET_QUA_CHAM, "loi", "chua_cham")
DO_DAI_BANG_CHUNG = 800  # ký tự đầu mỗi trích đoạn lưu làm evidence


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


def tong(luot: list[dict[str, Any]], khoa: str) -> int | None:
    gia_tri = [x[khoa] for x in luot if isinstance(x.get(khoa), int)]
    return sum(gia_tri) if gia_tri else None


def tra_loi_mot_cau(
    engine: Any, dem: DemLLM, cau_hoi: str,
    dung: Callable[[NodeWithScore, str], bool] | None = None, nhan: str | None = None,
) -> dict[str, object]:
    """Gọi engine (thử lại khi lỗi mạng/Ollama). Có `dung` + `nhan` (luật chấm eval/luat_cham.py) thì ghi thêm
    `ngu_canh_co_doan_dung`: ngữ cảnh đưa vào LLM có Node đúng không — để tách lỗi truy hồi khỏi lỗi sinh."""
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


def ket_qua_cua(k: dict[str, object]) -> str:
    """Outcome của một câu; file cũ (trước 23/10) chưa có trường ket_qua thì suy ra từ câu trả lời."""
    return str(k.get("ket_qua") or ("chua_cham" if k.get("tra_loi") else "loi"))


def ghi_md(duong_dan: Path, tieu_de: str, ket: list[dict[str, object]]) -> None:
    dong = [f"# {tieu_de}", ""]
    for i, k in enumerate(ket, start=1):
        mong_doi = f" · hành vi mong đợi: {k['hanh_vi_mong_doi']}" if k.get("hanh_vi_mong_doi") else ""
        dong += [
            f"## {i}. {k['question']}",
            f"_Kết quả: **{ket_qua_cua(k)}** · nhãn đúng: `{k.get('dieu_dung')}` · đáp án: {k.get('dap_an') or '—'}"
            f"{mong_doi} · {k['thoi_gian_s']}s · token vào/ra: {k.get('token_vao')}/{k.get('token_ra')}_",
            "",
            str(k["tra_loi"]) or "_(không có câu trả lời — lỗi kết nối)_",
            "",
            f"**Nguồn:** {'; '.join(str(x) for x in k['nguon'])}",  # type: ignore[union-attr]
            "",
        ]
    duong_dan.write_text("\n".join(dong), encoding="utf-8")


def tom_tat(ket: list[dict[str, object]]) -> dict[str, object]:
    def so(khoa: str) -> list[float]:
        return [float(v) for k in ket if isinstance(v := k.get(khoa), (int, float))]

    tg, tv, tr, ts, luot = so("thoi_gian_s"), so("token_vao"), so("token_ra"), so("token_moi_giay"), so("so_luot_llm")
    p90 = (lambda xs: sorted(xs)[max(0, round(0.9 * len(xs)) - 1)] if xs else None)
    return {
        "so_cau": len(ket),
        "ket_qua": dict(Counter(ket_qua_cua(k) for k in ket).most_common()),
        "so_cau_loi": sum(1 for k in ket if ket_qua_cua(k) == "loi"),
        "so_cau_phai_thu_lai": sum(1 for k in ket if k.get("so_lan_thu") != 1),
        "thoi_gian_trung_vi_s": round(statistics.median(tg), 2) if tg else None,
        "thoi_gian_p90_s": p90(tg),
        "token_vao_tb": round(statistics.mean(tv)) if tv else None,
        "token_ra_tb": round(statistics.mean(tr)) if tr else None,
        "token_moi_giay_tb": round(statistics.mean(ts), 1) if ts else None,
        "so_luot_llm_toi_da": int(max(luot)) if luot else None,
        "so_cau_nhieu_luot_llm": sum(1 for x in luot if x > 1),
    }


def tong_hop(files: list[str]) -> None:
    """Đếm lại tom_tat sau khi chấm tay trường ket_qua trong file JSON (không gọi LLM)."""
    for f in files:
        p = Path(f)
        du_lieu = json.loads(p.read_text(encoding="utf-8"))
        sai_nhan = [(k.get("id"), ket_qua_cua(k)) for k in du_lieu["chi_tiet"] if ket_qua_cua(k) not in KET_QUA_HOP_LE]
        if sai_nhan:
            sys.exit(f"{p.name}: nhãn ket_qua không hợp lệ {sai_nhan}; chỉ nhận {KET_QUA_HOP_LE}")
        du_lieu["tom_tat"] = tom_tat(du_lieu["chi_tiet"])
        p.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=1), encoding="utf-8")
        print(p.name, json.dumps(du_lieu["tom_tat"]["ket_qua"], ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="cu,moi", help=f"có: {', '.join(CAU_HINH)}")
    ap.add_argument("--bo", default="dev_questions_dot1.json,dev_questions_dot2.json,dev_questions_dot3.json,"
                                          "dev_questions_dot4.json")
    ap.add_argument("--nhan", default=time.strftime("%Y-%m-%d"), help="hậu tố tên file kết quả")
    ap.add_argument("--thu-muc", default=str(ROOT / "eval" / "results"))
    ap.add_argument("--chi-cau-loi", action="store_true",
                    help="chỉ chạy lại các câu ket_qua=loi trong file kết quả đã có (cùng --cau-hinh, --bo, --nhan)")
    ap.add_argument("--tong-hop", nargs="+", metavar="JSON", help="đếm lại tom_tat sau khi chấm tay, không gọi LLM")
    args = ap.parse_args()
    if args.tong_hop:
        tong_hop(args.tong_hop)
        return

    goc = get_config()
    try:
        httpx.get(f"{goc.ollama_base_url}/api/tags", timeout=10).raise_for_status()
    except httpx.HTTPError as e:
        sys.exit(f"Không kết nối được Ollama {goc.ollama_base_url}: {e}")
    index = build_or_load_index(goc)
    dem = DemLLM()
    Settings.callback_manager = CallbackManager([dem])
    out = Path(args.thu_muc)
    out.mkdir(parents=True, exist_ok=True)

    for ten in [t.strip() for t in args.cau_hinh.split(",") if t.strip()]:
        cfg: RAGConfig = dataclasses.replace(goc, streaming=False, **CAU_HINH[ten])  # type: ignore[arg-type]
        engine = build_query_engine(index, cfg)
        k0 = tra_loi_mot_cau(engine, dem, "Một năm học có bao nhiêu học kỳ?")  # khởi động (nạp LLM/reranker), không tính
        if k0["ket_qua"] == "loi":
            print(f"CẢNH BÁO: câu khởi động của cấu hình {ten} lỗi, vẫn chạy tiếp và ghi lỗi từng câu", flush=True)
        for bo in [b.strip() for b in args.bo.split(",") if b.strip()]:
            cau_hoi: list[dict[str, str]] = json.loads((ROOT / "eval" / bo).read_text(encoding="utf-8"))
            goc_ten = bo.removesuffix(".json").replace("_questions", "").replace("_", "-")
            stem = out / f"tra-loi-{goc_ten}-{ten}-{args.nhan}"
            cu: dict[str, dict[str, object]] = {}
            if args.chi_cau_loi:
                if not stem.with_suffix(".json").exists():
                    sys.exit(f"--chi-cau-loi: không thấy {stem.with_suffix('.json')}")
                cu = {str(k["id"]): k for k in json.loads(stem.with_suffix(".json").read_text(encoding="utf-8"))["chi_tiet"]}
            ket: list[dict[str, object]] = []
            print(f"=== {ten} | {bo} ({len(cau_hoi)} câu) ===", flush=True)
            for i, q in enumerate(cau_hoi, start=1):
                ma = str(q.get("id", str(i)))
                if ma in cu and ket_qua_cua(cu[ma]) != "loi":
                    ket.append(cu[ma])  # giữ nguyên câu đã có (và đã chấm) của lần trước
                    continue
                k = tra_loi_mot_cau(engine, dem, q["question"])
                ket.append({"id": ma, "question": q["question"], "dieu_dung": q.get("dieu_dung"),
                            "dap_an": q.get("dap_an") or q.get("dap_an_ngan"), "loai": q.get("loai"),
                            "hanh_vi_mong_doi": q.get("hanh_vi_mong_doi"), **k})
                print(f"{i}/{len(cau_hoi)} {k['ket_qua']} ({k['thoi_gian_s']}s, lượt LLM {k.get('so_luot_llm')}, "
                      f"token {k.get('token_vao')}/{k.get('token_ra')})", flush=True)
            tt = tom_tat(ket)
            mo_ta = cfg.mo_ta()
            stem.with_suffix(".json").write_text(json.dumps(
                {"thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"), "cau_hinh": mo_ta, "tom_tat": tt, "chi_tiet": ket},
                ensure_ascii=False, indent=1), encoding="utf-8")
            ghi_md(stem.with_suffix(".md"),
                   f"Trả lời {bo} — {ten} ({cfg.llm_model_name}, temperature={cfg.temperature}, seed={cfg.seed}, "
                   f"top_k={cfg.similarity_top_k}, rerank={mo_ta['use_rerank']}"
                   f"{' top_n=' + str(cfg.reranker_top_n) + ' max_length=' + str(cfg.reranker_max_length) if mo_ta['use_rerank'] else ''}, "
                   f"lọc phiên bản={cfg.loc_phien_ban})", ket)
            print(json.dumps(tt, ensure_ascii=False), flush=True)
            print(f"Đã ghi {stem}.md / .json", flush=True)


if __name__ == "__main__":
    main()
