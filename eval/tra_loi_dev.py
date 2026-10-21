"""Sinh câu trả lời cho các bộ dev (và bộ 01/02) để chấm tay, kèm số token và độ trễ lấy từ Ollama.

Thay cho wrapper ngoài repo dùng ngày 13/10 (eval/results/logs/2026-10-13_dot2/): cùng định dạng file .md
(tra-loi-dev-*.md) để so được với lần trước, thêm file .json ghi cho từng câu:
  - thời gian truy hồi + sinh của lần gọi thành công (lần thử lỗi mạng không tính vào độ trễ),
  - số lượt gọi LLM (response_mode=compact có thể chia nhiều lượt khi ngữ cảnh dài),
  - prompt_eval_count / eval_count / eval_duration do Ollama trả về (số token thật, không ước lượng).

Cấu hình so sánh:
  cu   = vector top-10, không rerank, không lọc phiên bản (cấu hình mặc định trước 16/10)
  moi  = cấu hình mặc định profile server hiện tại (rerank 2048 token top-3 + lọc phiên bản)

    RAG_PROFILE=server venv/bin/python eval/tra_loi_dev.py --cau-hinh cu,moi \\
        --bo dev_questions_dot1.json,dev_questions_dot2.json,dev_questions_dot3.json --nhan 2026-10-16
"""
import argparse
import dataclasses
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from ollama import ResponseError
from llama_index.core import Settings
from llama_index.core.base.response.schema import Response
from llama_index.core.callbacks import CallbackManager, CBEventType, EventPayload
from llama_index.core.callbacks.base_handler import BaseCallbackHandler

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


def tra_loi_mot_cau(engine: Any, dem: DemLLM, cau_hoi: str) -> dict[str, object]:
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
            "tra_loi": str(r).strip(),
            "nguon": list(dict.fromkeys(node_label(n) for n in r.source_nodes)),
            "thoi_gian_s": round(giay, 2),
            "so_lan_thu": lan,
            "loi": loi,
            "so_luot_llm": len(dem.luot),
            "token_vao": tong(dem.luot, "prompt_eval_count"),
            "token_ra": so_token_ra,
            "token_moi_giay": round(so_token_ra / (eval_ns / 1e9), 1) if so_token_ra and eval_ns else None,
        }
    return {"tra_loi": "", "nguon": [], "thoi_gian_s": None, "so_lan_thu": SO_LAN_THU, "loi": loi}


def ghi_md(duong_dan: Path, tieu_de: str, ket: list[dict[str, object]]) -> None:
    dong = [f"# {tieu_de}", ""]
    for i, k in enumerate(ket, start=1):
        dong += [
            f"## {i}. {k['question']}",
            f"_Nhãn đúng: `{k['dieu_dung']}` · đáp án: {k.get('dap_an') or '—'} · {k['thoi_gian_s']}s"
            f" · token vào/ra: {k.get('token_vao')}/{k.get('token_ra')}_",
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
        "so_cau_loi": sum(1 for k in ket if not k["tra_loi"]),
        "so_cau_phai_thu_lai": sum(1 for k in ket if k.get("so_lan_thu") != 1),
        "thoi_gian_trung_vi_s": round(statistics.median(tg), 2) if tg else None,
        "thoi_gian_p90_s": p90(tg),
        "token_vao_tb": round(statistics.mean(tv)) if tv else None,
        "token_ra_tb": round(statistics.mean(tr)) if tr else None,
        "token_moi_giay_tb": round(statistics.mean(ts), 1) if ts else None,
        "so_luot_llm_toi_da": int(max(luot)) if luot else None,
        "so_cau_nhieu_luot_llm": sum(1 for x in luot if x > 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cau-hinh", default="cu,moi", help=f"có: {', '.join(CAU_HINH)}")
    ap.add_argument("--bo", default="dev_questions_dot1.json,dev_questions_dot2.json,dev_questions_dot3.json")
    ap.add_argument("--nhan", default=time.strftime("%Y-%m-%d"), help="hậu tố tên file kết quả")
    ap.add_argument("--thu-muc", default=str(ROOT / "eval" / "results"))
    args = ap.parse_args()

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
        engine.query("Một năm học có bao nhiêu học kỳ?")  # khởi động (nạp model LLM/reranker), không tính
        for bo in [b.strip() for b in args.bo.split(",") if b.strip()]:
            cau_hoi: list[dict[str, str]] = json.loads((ROOT / "eval" / bo).read_text(encoding="utf-8"))
            ket: list[dict[str, object]] = []
            print(f"=== {ten} | {bo} ({len(cau_hoi)} câu) ===", flush=True)
            for i, q in enumerate(cau_hoi, start=1):
                k = tra_loi_mot_cau(engine, dem, q["question"])
                ket.append({"id": q.get("id", str(i)), "question": q["question"], "dieu_dung": q.get("dieu_dung"),
                            "dap_an": q.get("dap_an"), **k})
                print(f"{i}/{len(cau_hoi)} xong ({k['thoi_gian_s']}s, lượt LLM {k.get('so_luot_llm')}, "
                      f"token {k.get('token_vao')}/{k.get('token_ra')})", flush=True)
            goc_ten = bo.removesuffix(".json").replace("_questions", "").replace("_", "-")
            stem = out / f"tra-loi-{goc_ten}-{ten}-{args.nhan}"
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
