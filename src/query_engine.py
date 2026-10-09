"""Ghép retriever + LLM (Ollama) thành query engine và in câu trả lời kèm nguồn."""
import sys
from pathlib import Path

from llama_index.core import PromptTemplate, Settings, VectorStoreIndex
from llama_index.core.base.response.schema import RESPONSE_TYPE, Response, StreamingResponse
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.llms.ollama import Ollama

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index
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


def build_query_engine(index: VectorStoreIndex, cfg: RAGConfig) -> RetrieverQueryEngine:
    llm = make_llm(cfg)
    Settings.llm = llm
    return RetrieverQueryEngine.from_args(
        retriever=get_retriever(index, cfg),
        llm=llm,
        response_mode=ResponseMode(cfg.response_mode),
        streaming=cfg.streaming,
        text_qa_template=QA_PROMPT,
        node_postprocessors=get_postprocessors(cfg),
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
