"""Giao diện Gradio để chạy thử hệ thống RAG: hỏi-đáp + xem các trích đoạn được truy hồi.

Truy hồi và sinh câu trả lời tách riêng: LLM (Ollama) lỗi thì vẫn thấy các Node đã truy hồi,
dùng để thử retriever khi chưa có LLM (bỏ chọn "Sinh câu trả lời").

Cách dùng (từ thư mục gốc repo):
    RAG_PROFILE=server venv/bin/python app/app.py            # mở http://127.0.0.1:7860
    RAG_PROFILE=server venv/bin/python app/app.py --share    # thêm link công khai tạm của Gradio
"""
import dataclasses
import json
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import gradio as gr
import httpx
import ollama
from llama_index.core import get_response_synthesizer
from llama_index.core.base.response.schema import StreamingResponse
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.response_synthesizers import ResponseMode
from gradio.components.chatbot import MessageDict
from llama_index.core.schema import NodeWithScore

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import get_config
from index_builder import build_or_load_index
from query_engine import QA_PROMPT, make_llm
from retriever import get_postprocessors, node_label, search

Message = MessageDict | gr.ChatMessage  # Chatbot trả history dạng dict, ta thêm ChatMessage

CAU_HOI_MAU = [
    "Một năm học có bao nhiêu học kỳ?",
    "Sinh viên được rút học phần trong thời gian nào?",
    "Điều kiện để được học cùng lúc hai chương trình?",
    "Kỹ sư CNTT cần tối thiểu bao nhiêu tín chỉ?",
]

cfg = get_config()
index = build_or_load_index(cfg)  # nạp embedding + index một lần khi khởi động
llm = make_llm(cfg)
synthesizer = get_response_synthesizer(
    llm=llm, response_mode=ResponseMode(cfg.response_mode), streaming=True, text_qa_template=QA_PROMPT
)
_rerankers: list[BaseNodePostprocessor] | None = None  # nạp lần đầu khi bật rerank
LOG_PATH = Path(__file__).resolve().parent.parent / "eval" / "results" / "questions_log.jsonl"


def rerankers() -> list[BaseNodePostprocessor]:
    global _rerankers
    if _rerankers is None:
        _rerankers = get_postprocessors(dataclasses.replace(cfg, use_rerank=True))
    return _rerankers


def ghi_log(question: str, nodes: list[NodeWithScore], tra_loi: str, cau_hinh: dict[str, object]) -> None:
    """Ghi lại câu hỏi thật của người dùng để mở rộng bộ đánh giá (nguồn dữ liệu cho Chương 5)."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({
                "thoi_diem": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cau_hoi": question,
                "cau_hinh": cau_hinh,
                "nguon": [node_label(n) for n in nodes],
                "tra_loi": tra_loi,
            }, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"Không ghi được log câu hỏi: {e}")


def trang_thai_llm() -> str:
    try:
        httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=3).raise_for_status()
        return f"🟢 LLM `{cfg.llm_model_name}` tại `{cfg.ollama_base_url}` sẵn sàng"
    except httpx.HTTPError as e:
        return f"🔴 Không kết nối được LLM tại `{cfg.ollama_base_url}` ({type(e).__name__}) — vẫn thử truy hồi được"


def hien_thi_nguon(nodes: list[NodeWithScore]) -> str:
    if not nodes:
        return "_Không có trích đoạn nào._"
    parts: list[str] = []
    for i, n in enumerate(nodes, start=1):
        noi_dung = n.node.get_content().strip()
        parts.append(
            f"**[{i}] {node_label(n)}** — score `{n.score or 0:.4f}`\n\n"
            f"<details><summary>{' '.join(noi_dung[:120].split())}…</summary>\n\n{noi_dung}\n\n</details>"
        )
    return "\n\n---\n\n".join(parts)


def hoi(
    question: str, history: list[Message], top_k: int, dung_rerank: bool, sinh_tra_loi: bool
) -> Iterator[tuple[list[Message], str, str]]:
    question = question.strip()
    if not question:
        yield history, "", ""
        return
    history = [*history, gr.ChatMessage(role="user", content=question)]
    tra_loi = gr.ChatMessage(role="assistant", content="_Đang truy hồi…_")
    history.append(tra_loi)
    yield history, "", ""

    c = dataclasses.replace(cfg, similarity_top_k=int(top_k))
    nodes = search(index, c, question, rerankers() if dung_rerank else [])
    nguon = hien_thi_nguon(nodes)
    if not sinh_tra_loi:
        tra_loi.content = f"_Chỉ truy hồi: {len(nodes)} trích đoạn, xem cột bên phải._"
        yield history, "", nguon
        return

    tra_loi.content = ""
    try:
        response = synthesizer.synthesize(question, nodes=nodes)
        if isinstance(response, StreamingResponse):
            for token in response.response_gen:
                tra_loi.content += token
                yield history, "", nguon
        else:
            tra_loi.content = str(response)
    except (httpx.HTTPError, ollama.ResponseError) as e:
        tra_loi.content = f"⚠️ Lỗi gọi LLM tại `{cfg.ollama_base_url}`: `{e}`\n\nCác trích đoạn truy hồi vẫn ở cột bên phải."
    nhan = "; ".join(dict.fromkeys(node_label(n) for n in nodes))
    tra_loi.content += f"\n\n**Nguồn:** {nhan}"
    ghi_log(question, nodes, str(tra_loi.content), {"profile": cfg.name, "top_k": int(top_k),
                                              "rerank": bool(dung_rerank), "sinh_tra_loi": bool(sinh_tra_loi)})
    yield history, "", nguon


with gr.Blocks(title="SGU RAG — chạy thử") as demo:
    gr.Markdown(
        f"## Hỏi đáp quy chế đào tạo SGU — chạy thử\n"
        f"Profile `{cfg.name}` · embedding `{cfg.embed_model_name}` · corpus `{cfg.corpus_dir}`"
    )
    gr.Markdown(
        "> ⚠️ Câu trả lời do mô hình sinh ra từ trích đoạn quy chế, **không có giá trị pháp lý**. "
        "Hãy mở cột *Trích đoạn truy hồi* để đối chiếu nguyên văn Điều được dẫn."
    )
    trang_thai = gr.Markdown(trang_thai_llm())
    with gr.Row():
        with gr.Column(scale=3):
            chat = gr.Chatbot(height=520, label="Hội thoại")
            o_hoi = gr.Textbox(placeholder="Nhập câu hỏi rồi Enter…", show_label=False)
            gr.Examples(CAU_HOI_MAU, inputs=o_hoi)
            with gr.Row():
                top_k = gr.Slider(1, 20, value=cfg.similarity_top_k, step=1, label="top-k")
                dung_rerank = gr.Checkbox(
                    value=cfg.use_rerank,
                    label="Rerank",
                    interactive=cfg.reranker_model_name is not None,
                    info=None if cfg.reranker_model_name else f"profile {cfg.name} không có reranker",
                )
                sinh_tra_loi = gr.Checkbox(value=True, label="Sinh câu trả lời (LLM)")
            with gr.Row():
                gr.Button("Xoá hội thoại").click(lambda: ([], ""), outputs=[chat, o_hoi])
                gr.Button("Kiểm tra LLM").click(trang_thai_llm, outputs=trang_thai)
        with gr.Column(scale=2):
            gr.Markdown("### Trích đoạn truy hồi")
            nguon = gr.Markdown()

    o_hoi.submit(hoi, inputs=[o_hoi, chat, top_k, dung_rerank, sinh_tra_loi], outputs=[chat, o_hoi, nguon])


if __name__ == "__main__":
    demo.launch(share="--share" in sys.argv)
