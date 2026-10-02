import logging
import re
import sys
from pathlib import Path

import torch
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RAGConfig, get_config
from node_parser import parse_by_dieu, validate_nodes

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OCR_FILE = ROOT / "data" / "ocr" / "4. QuyCheDaoTaoDHSG 2021.md"
SOURCE_NAME = "Quy chế đào tạo 2021"


def load_documents() -> list[Document]:
    """Nạp Quy chế dưới dạng 1 Document duy nhất để Điều không bị cắt ngang theo trang.

    Ưu tiên bản OCR đã có (data/ocr). Bỏ trang 1 (Quyết định ban hành, có Điều 1-3 riêng
    của Quyết định) để số Điều khớp với số Điều của Quy chế.
    """
    if OCR_FILE.exists():
        text = OCR_FILE.read_text(encoding="utf-8")
        start = text.find("## Trang 2")
        if start != -1:
            text = text[start:]
        text = re.sub(r"^## Trang \d+.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE)
        return [Document(text=text, metadata={"nguon": SOURCE_NAME, "file_goc": OCR_FILE.name})]

    from ingestion import load_corpus
    logger.warning("Không thấy bản OCR sẵn, chạy OCR từ PDF (chậm)...")
    return load_corpus()


def setup_embedding(cfg: RAGConfig) -> None:
    fp16 = cfg.use_fp16 and cfg.embed_device == "cuda"
    Settings.embed_model = HuggingFaceEmbedding(
        model_name=cfg.embed_model_name,
        device=cfg.embed_device,
        embed_batch_size=4 if fp16 else 10,  # batch nhỏ để không tràn VRAM trên card 4 GB
        model_kwargs={"torch_dtype": torch.float16} if fp16 else {},
    )


def build_or_load_index(cfg: RAGConfig, rebuild: bool = False) -> VectorStoreIndex:
    setup_embedding(cfg)
    persist_dir = ROOT / cfg.persist_dir

    if not rebuild and (persist_dir / "docstore.json").exists():
        logger.info(f"Load Index từ {persist_dir}")
        index = load_index_from_storage(StorageContext.from_defaults(persist_dir=str(persist_dir)))
        assert isinstance(index, VectorStoreIndex)
        return index

    nodes = parse_by_dieu(load_documents())
    logger.info(f"Build Index mới từ {len(nodes)} node: {validate_nodes(nodes)}")
    index = VectorStoreIndex(nodes, show_progress=True)
    persist_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(persist_dir))
    return index


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    cfg = get_config()
    index = build_or_load_index(cfg, rebuild="--rebuild" in sys.argv)
    n_index = len(index.docstore.docs)
    n_parser = len(parse_by_dieu(load_documents()))
    print(f"Số node trong Index: {n_index} | số node từ node_parser: {n_parser} | khớp: {n_index == n_parser}")
