import hashlib
import json
import logging
import sys
from pathlib import Path

import torch
from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from processed_loader import corpus_files, load_corpus_nodes, ten_hien_thi

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
FINGERPRINT = "corpus.json"  # lưu cạnh index: index được build từ những file / model nào


def make_local_embedding(cfg: RAGConfig) -> HuggingFaceEmbedding:
    fp16 = cfg.use_fp16 and cfg.embed_device == "cuda"
    return HuggingFaceEmbedding(
        model_name=cfg.embed_model_name,
        device=cfg.embed_device,
        embed_batch_size=4 if fp16 else 10,  # batch nhỏ để không tràn VRAM trên card 4 GB
        model_kwargs={"torch_dtype": torch.float16} if fp16 else {},
    )


def setup_embedding(cfg: RAGConfig) -> None:
    if cfg.model_server_url:
        from remote_models import RemoteEmbedding, check_server
        check_server(cfg.model_server_url, cfg.embed_model_name, cfg.reranker_model_name)
        Settings.embed_model = RemoteEmbedding(
            base_url=cfg.model_server_url, model_name=cfg.embed_model_name, embed_batch_size=32
        )
    else:
        Settings.embed_model = make_local_embedding(cfg)


def corpus_fingerprint(cfg: RAGConfig) -> dict[str, str | dict[str, str]]:
    """Model embedding + sha256 và tên hiển thị từng file tầng 2; khác đi thì index cũ không còn đúng
    (tên hiển thị được ghép vào văn bản khi embedding)."""
    files = {p.name: f"{hashlib.sha256(p.read_bytes()).hexdigest()} | {ten_hien_thi(cfg, p)}" for p in corpus_files(cfg)}
    return {"embed_model": cfg.embed_model_name, "corpus_dir": cfg.corpus_dir, "files": files}


def build_or_load_index(cfg: RAGConfig, rebuild: bool = False) -> VectorStoreIndex:
    setup_embedding(cfg)
    persist_dir = ROOT / cfg.persist_dir
    fingerprint = corpus_fingerprint(cfg)
    saved = persist_dir / FINGERPRINT

    if not rebuild and (persist_dir / "docstore.json").exists():
        if saved.exists() and json.loads(saved.read_text(encoding="utf-8")) == fingerprint:
            logger.info(f"Load Index từ {persist_dir}")
            index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(persist_dir)))
            assert isinstance(index, VectorStoreIndex)
            return index
        logger.warning("Corpus hoặc model embedding đã đổi so với index đã lưu — build lại")

    nodes = load_corpus_nodes(cfg)
    logger.info(f"Build Index mới từ {len(nodes)} node ({len(fingerprint['files'])} văn bản)")
    index = VectorStoreIndex(nodes, show_progress=True)
    persist_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(persist_dir))
    saved.write_text(json.dumps(fingerprint, ensure_ascii=False, indent=1), encoding="utf-8")
    return index


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cfg = get_config()
    index = build_or_load_index(cfg, rebuild="--rebuild" in sys.argv)
    n_index = len(index.docstore.docs)
    n_loader = len(load_corpus_nodes(cfg))
    print(f"Index: {cfg.persist_dir} | số node trong Index: {n_index} | từ processed_loader: {n_loader} | khớp: {n_index == n_loader}")
