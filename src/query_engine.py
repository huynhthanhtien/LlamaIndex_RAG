"""Ghép retriever + LLM (Ollama) thành query engine và in câu trả lời kèm nguồn."""
import hashlib
import json
import sys
from pathlib import Path

import httpx
from llama_index.core import PromptTemplate, Settings, VectorStoreIndex
from llama_index.core.base.response.schema import RESPONSE_TYPE, Response, StreamingResponse
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.llms.ollama import Ollama

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index, corpus_fingerprint
from retriever import get_postprocessors, get_retriever, node_label

QA_PROMPT = PromptTemplate(
    "Dưới đây là các trích đoạn từ các văn bản quy chế, quy định đào tạo của Trường Đại học Sài Gòn "
    "(mỗi trích đoạn ghi rõ tên văn bản và Điều).\n"
    "---------------------\n{context_str}\n---------------------\n"
    "Chỉ dựa vào các trích đoạn trên, trả lời câu hỏi bằng tiếng Việt, ngắn gọn và chính xác.\n"
    "Bắt buộc trích nguyên văn câu quy định làm căn cứ trước khi kết luận, kèm tên văn bản và số Điều.\n"
    "Không tự suy diễn, không tự quy đổi thang điểm hay đổi đơn vị; nếu cần tra bảng thì chép đúng "
    "hàng của bảng có trong trích đoạn.\n"
    "Nếu có văn bản sửa đổi thì dùng nội dung đã sửa đổi.\n"
    # Trích đoạn sửa đổi chỉ chứa bảng, không ghi thang điểm: thiếu chú giải này LLM lấy bảng quy đổi
    # hệ 4 (Điều 10) để trả lời câu hỏi về hệ 10 (Điều 9).
    # Bản vá miền, CHƯA đánh giá riêng (chưa có A/B giữ/bỏ đoạn này); không dùng lại được cho văn bản khác.
    "Lưu ý về thang điểm: điểm thành phần và điểm học phần chấm theo thang điểm 10 (\"hệ 10\"), rồi xếp loại "
    "thành điểm chữ (A, B+, B, ...) theo khoảng điểm ở khoản 3 Điều 9. Điểm chữ được quy đổi sang thang điểm 4 "
    "(\"hệ 4\") chỉ để tính điểm trung bình, theo khoản 2 Điều 10. Hỏi về hệ 10 hoặc khoảng điểm thì dùng bảng "
    "Điều 9; hỏi về hệ 4 hoặc quy đổi để tính điểm trung bình thì dùng bảng Điều 10. "
    "Khi tra khoảng điểm, so sánh con số với cả cận dưới và cận trên của từng hàng.\n"
    "Nếu trích đoạn không có thông tin, hãy nói không tìm thấy trong các văn bản quy định.\n"
    "Câu hỏi: {query_str}\n"
    "Trả lời: "
)


def make_llm(cfg: RAGConfig) -> Ollama:
    """LLM tất định: temperature=0 và seed cố định (trước đây không đặt nên đáp án đổi giữa các lần hỏi).

    cfg.thinking bật chế độ suy luận của qwen3: tra bảng khoảng điểm chính xác hơn nhưng chậm ~4 lần.
    """
    return Ollama(
        model=cfg.llm_model_name,
        base_url=cfg.ollama_base_url,
        request_timeout=cfg.request_timeout,
        temperature=cfg.temperature,
        additional_kwargs={"seed": cfg.seed},
        thinking=cfg.thinking,
        context_window=8192,
    )


def sha256_json(x: object) -> str:
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def digest_llm(cfg: RAGConfig) -> str | None:
    """Digest của model trên Ollama (`/api/tags`): cùng tên "qwen3:8b" nhưng kéo lại có thể là bản khác."""
    try:
        ds = httpx.get(f"{cfg.ollama_base_url}/api/tags", timeout=10).raise_for_status().json()["models"]
    except (httpx.HTTPError, KeyError, ValueError):
        return None
    return next((str(m.get("digest")) for m in ds if m.get("name") == cfg.llm_model_name), None)


def khoa_tai_lap(cfg: RAGConfig, llm_digest: str | None = None) -> dict[str, object]:
    """Những gì quyết định một câu trả lời: prompt, model, index và cấu hình (nhận xét tuần 7, ý 6).

    `ma` là sha256 rút gọn của cả khối: ghi `ma` vào log từng câu thì biết câu nào chạy với prompt/model/index nào,
    và hai lượt chạy có `ma` khác nhau thì không được gộp chung một bảng.
    """
    khoa: dict[str, object] = {
        "prompt_sha256": hashlib.sha256(QA_PROMPT.get_template().encode("utf-8")).hexdigest(),
        "llm": cfg.llm_model_name,
        "llm_digest": llm_digest,
        "index_sha256": sha256_json(corpus_fingerprint(cfg)),  # model embedding + loader + sha256 từng file
        # Bỏ khóa phụ thuộc máy chạy: cùng cấu hình chạy trên CPU hay GPU vẫn là một cấu hình
        "cau_hinh": {k: v for k, v in cfg.mo_ta().items() if k not in ("embed_device", "persist_dir")},
    }
    return {"ma": sha256_json(khoa)[:12], **khoa}


def build_query_engine(index: VectorStoreIndex, cfg: RAGConfig) -> RetrieverQueryEngine:
    llm = make_llm(cfg)
    Settings.llm = llm
    return RetrieverQueryEngine.from_args(
        retriever=get_retriever(index, cfg),
        llm=llm,
        response_mode=ResponseMode(cfg.response_mode),
        streaming=cfg.streaming,
        text_qa_template=QA_PROMPT,
        node_postprocessors=get_postprocessors(cfg, index),
    )


def format_sources(response: RESPONSE_TYPE) -> str:
    return "; ".join(dict.fromkeys(node_label(n) for n in response.source_nodes))


def ask(engine: RetrieverQueryEngine, question: str, cfg: RAGConfig) -> None:
    response = engine.query(question)
    if isinstance(response, StreamingResponse):
        for token in response.response_gen:
            print(token, end="", flush=True)
        print()
    elif isinstance(response, Response):
        print(response.response)
    print(f"Nguồn: {format_sources(response)}")


if __name__ == "__main__":
    cfg = get_config()
    engine = build_query_engine(build_or_load_index(cfg), cfg)
    ask(engine, "Một năm học có bao nhiêu học kỳ?", cfg)
