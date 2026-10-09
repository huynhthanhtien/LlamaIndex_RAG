"""Cấu hình RAG: profile, model, tham số truy hồi và sinh câu trả lời.

Mọi tham số ảnh hưởng tới kết quả đo đều nằm ở đây, và RAGConfig.mo_ta() trả về
bản tóm tắt để phần đánh giá ghi kèm vào file kết quả ("con số này do cấu hình nào").
"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from dotenv import load_dotenv

from corpus import CORPUS_DIR, PROCESSED_ROOT, SGU_HIEU_LUC

load_dotenv()

logger = logging.getLogger(__name__)


def resolve_device(device: str) -> str:
    """Trả về thiết bị chạy được: giữ 'cuda' nếu GPU dùng được, ngược lại 'cpu'.

    Trước đây hai profile đặt cứng embed_device='cuda', nên máy không có driver
    NVIDIA (hoặc CI không GPU) lỗi ngay khi nạp model. Hàm này cho phép suy giảm
    mềm và vẫn ghi log để không âm thầm chạy sai thiết bị.
    """
    if device != "cuda":
        return device
    try:
        import torch
    except ImportError:  # torch chưa cài -> chắc chắn không có GPU
        logger.warning("Không import được torch — chuyển thiết bị sang CPU")
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    logger.warning("CUDA không khả dụng — chuyển thiết bị sang CPU")
    return "cpu"


@dataclass
class RAGConfig:
    # --- Profile (tách thư mục index: mỗi model embedding có số chiều riêng) ---
    name: str

    # --- Embedding ---
    embed_model_name: str
    embed_device: str  # "cpu" hoặc "cuda" (qua resolve_device() để tự hạ cấp)

    # --- LLM ---
    llm_model_name: str
    ollama_base_url: str
    request_timeout: float = 180.0
    temperature: float = 0.0  # 0 = tất định; trước đây không đặt nên câu trả lời đổi giữa các lần hỏi
    seed: int = 42            # truyền xuống Ollama qua additional_kwargs
    thinking: bool = False    # chế độ suy luận của qwen3: đúng hơn khi tra bảng số, chậm ~4 lần (RAG_THINKING=1)

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
    similarity_cutoff: float | None = None  # None = tắt; đặt >0 để bỏ Node dưới ngưỡng (K4)

    # --- Hybrid search: BM25 + vector, trộn bằng QueryFusionRetriever (K7) ---
    use_hybrid: bool = False
    bm25_top_k: int = 10
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    fusion_mode: str = "reciprocal_rerank"  # xem llama_index.core.retrievers.fusion_retriever.FUSION_MODES
    vector_weight: float = 1.0
    bm25_weight: float = 1.0

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
        # Cho phép ép từ môi trường khi máy không có GPU (CI, máy chấm bài)
        if os.environ.get("RAG_EMBED_DEVICE"):
            self.embed_device = os.environ["RAG_EMBED_DEVICE"]
        if os.environ.get("RAG_SEED"):
            self.seed = int(os.environ["RAG_SEED"])
        if os.environ.get("RAG_TEMPERATURE"):
            self.temperature = float(os.environ["RAG_TEMPERATURE"])
        if os.environ.get("RAG_THINKING"):
            self.thinking = os.environ["RAG_THINKING"] == "1"

    def mo_ta(self) -> dict[str, object]:
        """Tóm tắt cấu hình để ghi kèm vào kết quả đánh giá (tái lập được thí nghiệm)."""
        return {
            "profile": self.name,
            "embed_model": self.embed_model_name,
            "embed_device": self.embed_device,
            "llm_model": self.llm_model_name,
            "temperature": self.temperature,
            "seed": self.seed,
            "thinking": self.thinking,
            "similarity_top_k": self.similarity_top_k,
            "similarity_cutoff": self.similarity_cutoff,
            "use_rerank": bool(self.use_rerank and self.reranker_model_name),
            "reranker_model": self.reranker_model_name if self.use_rerank else None,
            "reranker_top_n": self.reranker_top_n,
            "use_hybrid": self.use_hybrid,
            "bm25_top_k": self.bm25_top_k if self.use_hybrid else None,
            "fusion_mode": self.fusion_mode if self.use_hybrid else None,
            "response_mode": self.response_mode,
            "corpus_dir": self.corpus_dir,
            "persist_dir": self.persist_dir,
        }


# ===== Định nghĩa 2 profile =====

CONFIG_LOCAL = RAGConfig(
    name="local",
    embed_model_name="bkai-foundation-models/vietnamese-bi-encoder",
    embed_device=os.environ.get("RAG_EMBED_DEVICE", "cuda"),
    llm_model_name="qwen3:4b",
    ollama_base_url="http://localhost:11434",
    reranker_model_name=None,  # bỏ qua rerank khi test nhẹ cho nhanh
)

CONFIG_SERVER = RAGConfig(
    name="server",
    embed_model_name="AITeamVN/Vietnamese_Embedding",
    embed_device=os.environ.get("RAG_EMBED_DEVICE", "cuda"),
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
    import json

    cfg = get_config()
    print(f"Profile đang dùng: {os.environ.get('RAG_PROFILE', 'local')}")
    print(json.dumps(cfg.mo_ta(), ensure_ascii=False, indent=2))
