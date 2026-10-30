"""Hands-on lab: chunking, đánh giá truy hồi và tách truy hồi khỏi sinh câu trả lời với LlamaIndex.

Hướng dẫn từng bước: lab/README.md. Chạy từ thư mục gốc repo:

    venv/bin/python lab/lab_rag.py chia --chia co-dinh --chunk 256            # xem các Node được tạo
    venv/bin/python lab/lab_rag.py do   --chia co-dinh --chunk 256 --top-k 1,3,5
    venv/bin/python lab/lab_rag.py hoi  "Vắng thi không có lý do thì bị điểm bao nhiêu?"
    venv/bin/python lab/lab_rag.py tra-loi "..." --nguong 0.28                # cần Ollama

Thêm `--dap-an` để dùng lời giải (lab/dap_an.py) thay cho bài làm (lab/bai_lam.py).
"""
import argparse
import importlib
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path
from typing import Protocol, cast

import httpx

from llama_index.core import PromptTemplate, Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chung import LAB, chia_co_dinh, doc_van_ban, la_dung, nhan_nguon

MODEL = os.environ.get("LAB_EMBED", "bkai-foundation-models/vietnamese-bi-encoder")
CAU_HOI: list[dict[str, str]] = json.loads((LAB / "cau_hoi.json").read_text(encoding="utf-8"))

# Bước 3 (sinh câu trả lời) chỉ nhận các trích đoạn đã truy hồi ở bước 1; LLM không tự tìm thêm
PROMPT = PromptTemplate(
    "Dưới đây là các trích đoạn văn bản quy chế đào tạo của Trường Đại học Sài Gòn, mỗi trích đoạn ghi tên văn bản "
    "và số Điều.\n---------------------\n{context_str}\n---------------------\n"
    "Chỉ dựa vào các trích đoạn trên, trả lời ngắn gọn bằng tiếng Việt và ghi rõ tên văn bản, số Điều làm căn cứ. "
    "Nếu có văn bản sửa đổi áp dụng cho khóa trong câu hỏi thì dùng nội dung sửa đổi. "
    "Nếu trích đoạn không có thông tin, trả lời đúng câu: Không tìm thấy trong các văn bản quy định.\n"
    "Câu hỏi: {query_str}\nTrả lời: "
)
TU_CHOI = "Không tìm thấy trong các văn bản quy định."


class BaiLam(Protocol):
    """Ba hàm học viên viết trong lab/bai_lam.py (lời giải: lab/dap_an.py)."""

    def chia_theo_dieu(self, text: str, van_ban: str, chunk_size: int = 0) -> list[TextNode]: ...
    def sap_xep_theo_phien_ban(self, nodes: list[NodeWithScore], cau_hoi: str) -> list[NodeWithScore]: ...
    def co_can_cu(self, nodes: list[NodeWithScore], nguong: float) -> bool: ...


def nap_nodes(bl: BaiLam, chia: str, chunk: int, them_3183: bool) -> list[TextNode]:
    nodes: list[TextNode] = []
    for ma in ["qc2021", *(["qd3183"] if them_3183 else [])]:
        text = doc_van_ban(ma)
        nodes += chia_co_dinh(text, ma, chunk) if chia == "co-dinh" else bl.chia_theo_dieu(text, ma, chunk)
    return nodes


def dung_index(nodes: list[TextNode], args: argparse.Namespace) -> VectorStoreIndex:
    """Không có --luu: index trong bộ nhớ. Có --luu: lưu ra lab/storage/<model>/<cách chia>, lần sau nạp lại không embed.

    Tên thư mục gồm model và cách chia: đổi model mà nạp index cũ sẽ lệch số chiều vector, đổi cách chia mà nạp index
    cũ thì đo nhầm cấu hình cũ (xem mục Lỗi thường gặp trong README).
    """
    if not args.luu:
        return VectorStoreIndex(nodes)
    ten = f"{args.chia}-{args.chunk}{'-3183' if args.them_3183 else ''}{'-dap-an' if args.dap_an else ''}"
    thu_muc = LAB / "storage" / MODEL.replace("/", "__") / ten
    if (thu_muc / "docstore.json").exists():
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(thu_muc)))
        assert isinstance(index, VectorStoreIndex)
        return index
    index = VectorStoreIndex(nodes)
    index.storage_context.persist(persist_dir=str(thu_muc))
    return index


def tim(index: VectorStoreIndex, cau_hoi: str, top_k: int, bl: BaiLam, phien_ban: bool) -> list[NodeWithScore]:
    nodes = index.as_retriever(similarity_top_k=top_k).retrieve(cau_hoi)
    return bl.sap_xep_theo_phien_ban(nodes, cau_hoi) if phien_ban else nodes


def so_token(nodes: list[TextNode]) -> list[int]:
    """Số token theo tokenizer của chính model embedding (không phải tiktoken mà SentenceSplitter dùng để cắt)."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(MODEL)
    return [len(tok(n.get_content())["input_ids"]) for n in nodes]


def lenh_chia(bl: BaiLam, args: argparse.Namespace) -> None:
    nodes = nap_nodes(bl, args.chia, args.chunk, args.them_3183)
    tk = so_token(nodes)
    gioi_han = cast(HuggingFaceEmbedding, Settings.embed_model).max_length
    for i, (n, t) in enumerate(zip(nodes, tk), start=1):
        dau = " ".join(n.get_content().split())[:90]
        print(f"{i:3}. [{n.metadata['van_ban']} | Điều {n.metadata['cac_dieu'] or '—'} | {t} token"
              f"{' > ' + str(gioi_han) + ' BỊ CẮT' if t > gioi_han else ''}] {dau}…")
    print(f"\n{len(nodes)} Node | token TB {statistics.mean(tk):.0f}, lớn nhất {max(tk)} | "
          f"{sum(t > gioi_han for t in tk)} Node dài hơn {gioi_han} token mà model embedding đọc được")


def lenh_do(bl: BaiLam, args: argparse.Namespace) -> None:
    ks = sorted({int(k) for k in args.top_k.split(",")})
    nodes = nap_nodes(bl, args.chia, args.chunk, args.them_3183)
    t0 = time.perf_counter()
    index = dung_index(nodes, args)
    t_index = time.perf_counter() - t0
    tk = so_token(nodes)
    gioi_han = cast(HuggingFaceEmbedding, Settings.embed_model).max_length

    hang: dict[str, int | None] = {}
    diem_top1: dict[str, float] = {}
    print(f"{'id':4} {'loại':9} {'hạng':>4}  {'điểm':>6}  top-1")
    for q in CAU_HOI:
        res = tim(index, q["question"], max(ks), bl, args.phien_ban)
        diem_top1[q["id"]] = max((n.score or 0.0 for n in res), default=0.0)
        h = next((i for i, n in enumerate(res, start=1) if la_dung(n, q)), None) if q["loai"] != "ngoai" else None
        hang[q["id"]] = h
        print(f"{q['id']:4} {q['loai']:9} {h if h else '—':>4}  {diem_top1[q['id']]:6.3f}  "
              f"{nhan_nguon(res[0]) if res else '(rỗng)'}")

    co_nhan = [q for q in CAU_HOI if q["loai"] != "ngoai"]
    print(f"\nCấu hình: chia={args.chia} chunk={args.chunk} them_3183={args.them_3183} phien_ban={args.phien_ban}")
    print(f"{len(nodes)} Node | token TB {statistics.mean(tk):.0f} | {sum(t > gioi_han for t in tk)} Node > {gioi_han} "
          f"token (bị cắt khi embed) | dựng index {t_index:.1f}s")
    for ten, ds in (("10 câu trong phạm vi", [q for q in co_nhan if q["loai"] == "trong"]),
                    ("2 câu phiên bản", [q for q in co_nhan if q["loai"] == "phien_ban"])):
        r = "  ".join(f"R@{k}={sum(1 for q in ds if (h := hang[q['id']]) and h <= k)}/{len(ds)}" for k in ks)
        mrr = sum(1 / h for q in ds if (h := hang[q["id"]])) / len(ds)
        print(f"  {ten:22} {r}  MRR={mrr:.3f}")
    trong = [diem_top1[q["id"]] for q in co_nhan]
    ngoai = [diem_top1[q["id"]] for q in CAU_HOI if q["loai"] == "ngoai"]
    print(f"  Điểm top-1: câu có đáp án thấp nhất {min(trong):.3f} | câu ngoài miền cao nhất {max(ngoai):.3f}")


def lenh_hoi(bl: BaiLam, args: argparse.Namespace) -> None:
    index = dung_index(nap_nodes(bl, args.chia, args.chunk, args.them_3183), args)
    for i, n in enumerate(tim(index, args.cau_hoi, int(args.top_k), bl, args.phien_ban), start=1):
        print(f"[{i}] {n.score or 0:.3f}  {nhan_nguon(n)}\n    {' '.join(n.get_content().split())[:200]}…")


def lenh_tra_loi(bl: BaiLam, args: argparse.Namespace) -> None:
    """Ba bước tách rời: (1) truy hồi, (2) kiểm căn cứ, (3) sinh câu trả lời từ đúng các trích đoạn của bước 1."""
    from llama_index.core import get_response_synthesizer
    from llama_index.core.response_synthesizers import ResponseMode
    from llama_index.llms.ollama import Ollama

    index = dung_index(nap_nodes(bl, args.chia, args.chunk, args.them_3183), args)
    llm = Ollama(model=os.environ.get("LAB_LLM", "qwen3:4b"),
                 base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
                 temperature=0.0, additional_kwargs={"seed": 42}, thinking=False, request_timeout=300.0,
                 context_window=8192)
    synth = get_response_synthesizer(llm=llm, response_mode=ResponseMode.COMPACT, text_qa_template=PROMPT)
    ds = CAU_HOI if args.cau_hoi == "tat-ca" else [{"id": "?", "question": args.cau_hoi, "dap_an": ""}]
    for q in ds:
        print(f"\n=== {q['id']} {q['question']}")
        nodes = tim(index, q["question"], int(args.top_k), bl, args.phien_ban)
        print("Bước 1 – truy hồi: " + "; ".join(f"{nhan_nguon(n)} ({n.score or 0:.3f})" for n in nodes))
        if args.nguong is not None and not bl.co_can_cu(nodes, args.nguong):
            print(f"Bước 2 – không có trích đoạn nào đạt ngưỡng {args.nguong}: từ chối, KHÔNG gọi LLM\n{TU_CHOI}")
            continue
        print("Bước 2 – đủ căn cứ" if args.nguong is not None else "Bước 2 – bỏ qua (chưa đặt --nguong)")
        try:
            tra_loi = str(synth.synthesize(q["question"], nodes=nodes))
        except (ConnectionError, httpx.HTTPError) as e:
            sys.exit(f"Không gọi được Ollama ({type(e).__name__}): kiểm tra `ollama serve` và OLLAMA_BASE_URL, "
                     f"model {llm.model} đã `ollama pull` chưa.")
        tra_loi = re.sub(r"(?s)<think>.*?</think>", "", tra_loi).strip()  # qwen3 đôi khi vẫn trả khối suy luận
        print(f"Bước 3 – LLM: {tra_loi}")
        if q.get("dap_an"):
            print(f"Đáp án chuẩn: {q['dap_an']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lenh", choices=["chia", "do", "hoi", "tra-loi"])
    ap.add_argument("cau_hoi", nargs="?", default="", help="câu hỏi cho lệnh hoi / tra-loi ('tat-ca' = cả bộ câu hỏi)")
    ap.add_argument("--chia", choices=["co-dinh", "dieu"], default="co-dinh")
    ap.add_argument("--chunk", type=int, default=None,
                    help="co-dinh: kích thước đoạn (token, mặc định 256); dieu: cắt tiếp Điều dài hơn N token (0 = không)")
    ap.add_argument("--top-k", default="3", help="lệnh do nhận danh sách, vd 1,3,5")
    ap.add_argument("--them-3183", action="store_true", help="nạp thêm QĐ 3183/2025 (văn bản sửa đổi)")
    ap.add_argument("--phien-ban", action="store_true", help="sắp lại theo hiệu lực (Bài tập 3)")
    ap.add_argument("--nguong", type=float, default=None, help="ngưỡng điểm để có căn cứ (Bài tập 4)")
    ap.add_argument("--luu", action="store_true", help="lưu/nạp index ở lab/storage/<model>/<cách chia>")
    ap.add_argument("--dap-an", action="store_true", help="dùng lời giải lab/dap_an.py thay cho lab/bai_lam.py")
    args = ap.parse_args()
    if args.chunk is None:
        args.chunk = 256 if args.chia == "co-dinh" else 0
    if args.lenh in ("hoi", "tra-loi") and not args.cau_hoi:
        ap.error(f"lệnh {args.lenh} cần câu hỏi")

    bl = cast(BaiLam, importlib.import_module("dap_an" if args.dap_an else "bai_lam"))
    Settings.embed_model = HuggingFaceEmbedding(model_name=MODEL, device=os.environ.get("LAB_DEVICE", "cpu"))
    {"chia": lenh_chia, "do": lenh_do, "hoi": lenh_hoi, "tra-loi": lenh_tra_loi}[args.lenh](bl, args)


if __name__ == "__main__":
    main()
