import sys
from pathlib import Path

from llama_index.core import PromptTemplate, Settings, VectorStoreIndex
from llama_index.core.base.response.schema import RESPONSE_TYPE, Response, StreamingResponse
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.ollama import Ollama

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from index_builder import build_or_load_index
from retriever import get_postprocessors, get_retriever

QA_PROMPT = PromptTemplate(
    "Dưới đây là các trích đoạn từ Quy chế đào tạo trình độ đại học Trường Đại học Sài Gòn.\n"
    "---------------------\n{context_str}\n---------------------\n"
    "Chỉ dựa vào các trích đoạn trên, trả lời câu hỏi bằng tiếng Việt, ngắn gọn và chính xác. "
    "Nếu trích đoạn không có thông tin, hãy nói không tìm thấy trong quy chế.\n"
    "Câu hỏi: {query_str}\n"
    "Trả lời: "
)


def build_query_engine(index: VectorStoreIndex, cfg: RAGConfig) -> RetrieverQueryEngine:
    llm = Ollama(
        model=cfg.llm_model_name,
        base_url=cfg.ollama_base_url,
        request_timeout=cfg.request_timeout,
        thinking=False,
        context_window=8192,
    )
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
    dieu = []
    for n in response.source_nodes:
        d = n.node.metadata.get("dieu")
        if d not in dieu:
            dieu.append(d)
    return ", ".join(f"Điều {d}" for d in dieu)


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
