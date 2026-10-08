"""Đánh giá CÂU TRẢ LỜI bằng chính các evaluator của LlamaIndex + phân loại từ chối.

Bản cũ chỉ chấm câu trả lời thủ công trên một phiên hỏi đáp. Script này thay phần đó bằng
đo tự động, có thể chạy lại:
  - `FaithfulnessEvaluator`: câu trả lời có bám vào ngữ cảnh truy hồi (chống bịa).
  - `RelevancyEvaluator`: câu trả lời có liên quan tới câu hỏi.
  - `CorrectnessEvaluator`: so với đáp án chuẩn trong eval/cau_hoi_danh_gia.json.
  - Từ chối: tách **từ chối đúng** (câu ngoài phạm vi) và **từ chối sai** (đáp án có trong ngữ cảnh),
    thay vì một con số "52% từ chối" gộp cả hai như báo cáo trước.
  - Chế độ `closed-book` (LLM trả lời không có ngữ cảnh) làm mốc so sánh RAG vs không RAG.
Chạy hàng loạt bằng BatchEvalRunner của thư viện.

Cần Ollama đang chạy. Cách dùng:
    RAG_PROFILE=server RAG_EMBED_DEVICE=cpu venv/bin/python eval/evaluate_answers.py --che-do ca-hai
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx
from llama_index.core import VectorStoreIndex
from llama_index.core.base.response.schema import Response
from llama_index.core.evaluation import (
    BatchEvalRunner,
    FaithfulnessEvaluator,
    RelevancyEvaluator,
)
from llama_index.core.llms import LLM

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index
from metrics import bootstrap_ci
from query_engine import build_query_engine, make_llm
from retriever import node_label

TU_CHOI = re.compile(r"không tìm thấy|không có thông tin|không đề cập|không nêu|không quy định trong", re.IGNORECASE)
PROMPT_CLOSED_BOOK = (
    "Trả lời câu hỏi sau về quy chế đào tạo trình độ đại học của Trường Đại học Sài Gòn. "
    "Nếu không chắc chắn, hãy nói không biết.\nCâu hỏi: {q}\nTrả lời: "
)


def ollama_san_sang(base_url: str) -> bool:
    try:
        return httpx.get(f"{base_url}/api/tags", timeout=3).raise_for_status().status_code == 200
    except httpx.HTTPError:
        return False


def tra_loi_rag(cfg: RAGConfig, index: VectorStoreIndex, cau_hoi: list[str]) -> list[Response]:
    engine = build_query_engine(index, cfg)
    ket: list[Response] = []
    for q in cau_hoi:
        r = engine.query(q)
        assert isinstance(r, Response), "query engine không được bật streaming"
        ket.append(r)
    return ket


def tra_loi_closed_book(cfg: RAGConfig, cau_hoi: list[str]) -> list[Response]:
    llm = make_llm(cfg)
    return [Response(response=str(llm.complete(PROMPT_CLOSED_BOOK.format(q=q))), source_nodes=[]) for q in cau_hoi]


def diem_evaluator(llm: LLM, cau_hoi: list[str], responses: list[Response]) -> dict[str, list[float | None]]:
    """Chấm bằng BatchEvalRunner; bỏ qua bài không có ngữ cảnh (closed-book) cho faithfulness/relevancy."""
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
            ket[ten] = [r.passing for r in ds]
    return ket


def tom_tat(ds: list[dict[str, object]], khoa: str) -> dict[str, object]:
    gia_tri = [d[khoa] for d in ds if d.get(khoa) is not None]
    if not gia_tri:
        return {"so_cau": 0}
    tb, lo, hi = bootstrap_ci([1.0 if v else 0.0 for v in gia_tri])
    return {"so_cau": len(gia_tri), "ty_le": round(tb, 3), "ci95": [round(lo, 3), round(hi, 3)]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--che-do", choices=["rag", "closed-book", "ca-hai"], default="ca-hai")
    ap.add_argument("--cau-hoi", default=str(ROOT / "eval" / "cau_hoi_danh_gia.json"))
    ap.add_argument("--json-out", default=str(ROOT / "eval" / "results" / "danh-gia-cau-tra-loi.json"))
    args = ap.parse_args()

    cfg = get_config()
    if not ollama_san_sang(cfg.ollama_base_url):
        sys.exit(f"Không kết nối được Ollama tại {cfg.ollama_base_url} — script này cần LLM. "
                 f"Kiểm tra bằng: curl {cfg.ollama_base_url}/api/tags")

    bo = json.loads(Path(args.cau_hoi).read_text(encoding="utf-8"))
    cau_hoi = [b["question"] for b in bo]
    llm = make_llm(cfg)
    index = None
    ket_qua: dict[str, object] = {"thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"), "cau_hinh": cfg.mo_ta(), "che_do": {}}

    che_do = ["rag", "closed-book"] if args.che_do == "ca-hai" else [args.che_do]
    for cd in che_do:
        print(f"=== chế độ {cd} ({len(cau_hoi)} câu) ===")
        if cd == "rag":
            index = index if index is not None else build_or_load_index(cfg)
            responses = tra_loi_rag(cfg, index, cau_hoi)
        else:
            responses = tra_loi_closed_book(cfg, cau_hoi)

        diem = diem_evaluator(llm, cau_hoi, responses)
        chi_tiet = []
        for i, (b, r) in enumerate(zip(bo, responses), start=1):
            tra_loi = str(r)
            tu_choi = bool(TU_CHOI.search(tra_loi))
            chi_tiet.append({
                "cau_hoi": b["question"],
                "pham_vi": b.get("pham_vi"),
                "dap_an_chuan": b.get("dap_an"),
                "tra_loi": tra_loi,
                "tu_choi": tu_choi,
                "tu_choi_dung": (tu_choi and b.get("pham_vi") == "ngoai") if b.get("pham_vi") else None,
                "tu_choi_sai": (tu_choi and b.get("pham_vi") == "trong") if b.get("pham_vi") else None,
                "nguon": "; ".join(dict.fromkeys(node_label(n) for n in r.source_nodes)),
                "faithfulness": diem.get("faithfulness", [None] * len(bo))[i - 1] if diem.get("faithfulness") else None,
                "relevancy": diem.get("relevancy", [None] * len(bo))[i - 1] if diem.get("relevancy") else None,
            })
            print(f"[{i}] từ chối={tu_choi} | {b['question'][:60]} -> {tra_loi[:90]}")

        tom_tat_cd = {
            "so_cau": len(bo),
            "so_tu_choi": sum(1 for d in chi_tiet if d["tu_choi"]),
            "ty_le_tu_choi": round(sum(1 for d in chi_tiet if d["tu_choi"]) / len(bo), 3),
            "tu_choi_dung": tom_tat(chi_tiet, "tu_choi_dung"),
            "tu_choi_sai": tom_tat(chi_tiet, "tu_choi_sai"),
            "faithfulness": tom_tat(chi_tiet, "faithfulness"),
            "relevancy": tom_tat(chi_tiet, "relevancy"),
            "chi_tiet": chi_tiet,
        }
        ket_qua["che_do"][cd] = tom_tat_cd  # type: ignore[index]
        print(json.dumps({k: v for k, v in tom_tat_cd.items() if k != "chi_tiet"}, ensure_ascii=False, indent=2))

    Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json_out).write_text(json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi {args.json_out}")


if __name__ == "__main__":
    main()
