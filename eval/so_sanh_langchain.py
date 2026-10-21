"""R10: dựng lại riêng phần truy hồi vector bằng LangChain để so với LlamaIndex trên cùng dữ liệu.

Cùng Node (processed_loader.load_corpus_nodes), cùng mô hình embedding (AITeamVN/Vietnamese_Embedding, chuẩn hóa L2
như HuggingFaceEmbedding của LlamaIndex), cùng top-k và cùng luật chấm (dung_bo_* trong eval/evaluate.py). Cài đúng thì
R@k của hai bên phải bằng nhau; lệch chỉ do sai số fp16 khi hai Node gần bằng điểm.

Khác biệt cần viết thêm bên LangChain (không có sẵn như LlamaIndex):
  - `Document` không có `excluded_embed_metadata_keys`: phải tự ghép chuỗi đem đi embed (ở đây lấy đúng chuỗi
    MetadataMode.EMBED của Node để hai bên cùng vector).
  - Không có lớp bọc HuggingFace trong langchain-core: tự viết `Embeddings` trên sentence-transformers
    (gói langchain-huggingface làm việc này nhưng kéo thêm phụ thuộc).

Cần `langchain-core` (không có trong requirements.txt, chỉ dùng cho thí nghiệm này):
    pip install langchain-core
    RAG_PROFILE=server venv/bin/python eval/so_sanh_langchain.py
"""
import dataclasses
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "eval"))

import torch
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from llama_index.core.schema import MetadataMode, NodeWithScore, TextNode
from sentence_transformers import SentenceTransformer

from config import get_config
from evaluate import BO_CAU_HOI, CAU_HINH, danh_gia, in_ket_qua
from index_builder import build_or_load_index
from processed_loader import load_corpus_nodes
from retriever import get_retriever, search


class STEmbeddings(Embeddings):
    """sentence-transformers -> giao diện Embeddings của LangChain, cùng cách nạp với make_local_embedding()."""

    def __init__(self, model_name: str, device: str, fp16: bool) -> None:
        self.model = SentenceTransformer(model_name, device=device,
                                         model_kwargs={"torch_dtype": torch.float16} if fp16 else {})

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, batch_size=4, normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], normalize_embeddings=True)[0].tolist()


# ---- Phần truy hồi bằng LangChain (đem so số dòng với get_retriever() + build_or_load_index()) ----
def dung_kho_langchain(nodes: list[TextNode], emb: Embeddings) -> InMemoryVectorStore:
    docs = [Document(id=n.node_id, page_content=n.get_content(metadata_mode=MetadataMode.EMBED),
                     metadata={"node_id": n.node_id}) for n in nodes]
    kho = InMemoryVectorStore(embedding=emb)
    kho.add_documents(docs)
    return kho


def tim_langchain(kho: InMemoryVectorStore, theo_id: dict[str, TextNode], cau_hoi: str, k: int) -> list[NodeWithScore]:
    return [NodeWithScore(node=theo_id[d.metadata["node_id"]], score=s)
            for d, s in kho.similarity_search_with_score(cau_hoi, k=k)]
# ---- hết phần LangChain ----


def main() -> None:
    goc = dataclasses.replace(get_config(), model_server_url=None)
    cfg = dataclasses.replace(goc, **CAU_HINH["vector"])  # vector top-k, không rerank, không lọc phiên bản
    nodes = load_corpus_nodes(cfg)
    theo_id = {n.node_id: n for n in nodes}
    device = "cuda" if torch.cuda.is_available() else "cpu"

    t0 = time.perf_counter()
    kho = dung_kho_langchain(nodes, STEmbeddings(cfg.embed_model_name, device, cfg.use_fp16 and device == "cuda"))
    print(f"LangChain: embed {len(nodes)} Node trong {time.perf_counter() - t0:.1f} s ({device})\n")

    index = build_or_load_index(cfg)
    retriever = get_retriever(index, cfg)
    tim_li = lambda q: search(index, cfg, q, postprocessors=[], retriever=retriever)  # noqa: E731
    tim_lc = lambda q: tim_langchain(kho, theo_id, q, cfg.similarity_top_k)  # noqa: E731
    tim_li("khởi động")
    tim_lc("khởi động")

    lech = 0
    for ten_file, dung in BO_CAU_HOI:
        kq_li = danh_gia(ten_file, dung, tim_li, "llamaindex", cfg.mo_ta())
        kq_lc = danh_gia(ten_file, dung, tim_lc, "langchain", cfg.mo_ta())
        in_ket_qua(kq_li)
        in_ket_qua(kq_lc)
        cau_lech = [i for i, (a, b) in enumerate(zip(kq_li.hang, kq_lc.hang, strict=True)) if a != b]
        lech += len(cau_lech)
        print(f"  -> {ten_file}: {len(cau_lech)} câu có hạng câu trả lời đúng khác nhau giữa hai bên {cau_lech}\n")
    print(f"Tổng số câu lệch hạng: {lech}")


if __name__ == "__main__":
    main()
