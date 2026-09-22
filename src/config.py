import os 

from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class RAGConfig:

    # --- Embedding ---
    embed_model_name: str
    embed_device: str  # "cpu" hoặc "cuda"

    # --- LLM ---
    llm_model_name: str
    ollama_base_url: str
    request_timeout: float = 180.0

    # --- Reranker (tuỳ chọn — để trống nếu chưa dùng) ---
    reranker_model_name: str | None = None
    reranker_top_n: int = 3

    # --- Retriever ---
    similarity_top_k: int = 10

    # --- Response Synthesis ---
    response_mode: str = "compact"
    streaming: bool = True

    # --- Đường dẫn ---
    persist_dir: str = "storage/vector_index"
    corpus_sources: list[tuple[str, str]] | None = None

    def __post_init__(self):
        if self.corpus_sources is None:
            self.corpus_sources = [
                ("data/raw/quy_che_dao_tao_2021.pdf", "Quy chế đào tạo 2021"),
                ("data/raw/qd_sua_doi_2025.pdf", "QĐ sửa đổi 2025"),
            ]


# ===== Định nghĩa 2 profile =====

CONFIG_LOCAL = RAGConfig(
    embed_model_name="bkai-foundation-models/vietnamese-bi-encoder",
    embed_device="cuda",
    llm_model_name="qwen3:4b",
    ollama_base_url="http://localhost:11434",
    reranker_model_name=None,  # bỏ qua rerank khi test nhẹ cho nhanh
)

CONFIG_SERVER = RAGConfig(
    embed_model_name="AITeamVN/Vietnamese_Embedding",
    embed_device="cuda",
    llm_model_name="qwen3:8b",
    ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    reranker_model_name="AITeamVN/Vietnamese_Reranker",
)

PROFILES = {
    "local": CONFIG_LOCAL,
    "server": CONFIG_SERVER,
}


def get_config() -> RAGConfig:
    """Lấy config theo profile đang chọn qua biến môi trường RAG_PROFILE."""
    profile_name = os.environ.get("RAG_PROFILE", "local")
    if profile_name not in PROFILES:
        raise ValueError(
            f"RAG_PROFILE='{profile_name}' không hợp lệ. "
            f"Chỉ chấp nhận: {list(PROFILES.keys())}"
        )
    return PROFILES[profile_name]


if __name__ == "__main__":
    cfg = get_config()
    print(f"Profile đang dùng: {os.environ.get('RAG_PROFILE', 'local')}")
    print(cfg)