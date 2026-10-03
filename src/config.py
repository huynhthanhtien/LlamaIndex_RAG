import os
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from dotenv import load_dotenv

from corpus import CORPUS_DIR, PROCESSED_ROOT, SGU_HIEU_LUC

load_dotenv()


@dataclass
class RAGConfig:
    # --- Profile (tách thư mục index: mỗi model embedding có số chiều riêng) ---
    name: str

    # --- Embedding ---
    embed_model_name: str
    embed_device: str  # "cpu" hoặc "cuda"

    # --- LLM ---
    llm_model_name: str
    ollama_base_url: str
    request_timeout: float = 180.0

    # --- Thiết bị ---
    use_fp16: bool = False  # nạp embedding + reranker ở fp16 (chỉ khi cuda) để vừa GPU 4 GB

    # --- Reranker (tuỳ chọn) — mặc định tắt: đã đo trên corpus hiện tại, rerank làm giảm Recall@1 ---
    reranker_model_name: str | None = None
    reranker_top_n: int = 3
    use_rerank: bool = False

    # --- Model server (tuỳ chọn) — có URL thì gọi src/model_server.py thay vì nạp model tại chỗ ---
    model_server_url: str | None = field(default_factory=lambda: os.environ.get("MODEL_SERVER_URL") or None)

    # --- Retriever ---
    similarity_top_k: int = 10

    # --- Response Synthesis ---
    response_mode: str = "compact"
    streaming: bool = True

    # --- Dữ liệu (tầng 2, sinh bởi scripts/clean_md.py) — sửa danh sách ở src/corpus.py ---
    corpus_dir: str = CORPUS_DIR
    corpus_files: tuple[str, ...] = tuple(SGU_HIEU_LUC)  # tiền tố tên file; rỗng = nạp hết
    ten_van_ban: dict[str, str] = field(default_factory=lambda: dict(SGU_HIEU_LUC))  # tiền tố -> tên hiển thị

    # --- Đường dẫn index; để trống = storage/<name>/<corpus> ---
    persist_dir: str = ""

    def __post_init__(self) -> None:
        if not self.persist_dir:
            corpus = PurePosixPath(self.corpus_dir).relative_to(PROCESSED_ROOT)
            self.persist_dir = f"storage/{self.name}/{corpus}"
        if "://" not in self.ollama_base_url:  # .env hay ghi thiếu, vd "1.2.3.4:11434"
            self.ollama_base_url = f"http://{self.ollama_base_url}"


# ===== Định nghĩa 2 profile =====

CONFIG_LOCAL = RAGConfig(
    name="local",
    embed_model_name="bkai-foundation-models/vietnamese-bi-encoder",
    embed_device="cuda",
    llm_model_name="qwen3:4b",
    ollama_base_url="http://localhost:11434",
    reranker_model_name=None,  # bỏ qua rerank khi test nhẹ cho nhanh
)

CONFIG_SERVER = RAGConfig(
    name="server",
    embed_model_name="AITeamVN/Vietnamese_Embedding",
    embed_device="cuda",
    use_fp16=True,
    llm_model_name="qwen3:8b",
    ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    reranker_model_name="AITeamVN/Vietnamese_Reranker",
)

PROFILES: dict[str, RAGConfig] = {
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