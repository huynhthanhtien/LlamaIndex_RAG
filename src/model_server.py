"""Model server: nạp embedding + reranker lên GPU một lần, các tiến trình RAG gọi qua HTTP.

File này độc lập, không import code nào khác của dự án: có thể chép riêng nó lên máy GPU (cloud) để chạy,
còn index, retriever, query engine vẫn chạy trên máy local và gọi sang qua MODEL_SERVER_URL.
Cách nạp model giống hệt make_local_embedding() / make_local_reranker() trong src/ để vector trùng khớp;
client (remote_models.check_server) báo lỗi nếu server chạy model khác config.

Biến môi trường (mặc định = profile "server"):
    EMBED_MODEL          AITeamVN/Vietnamese_Embedding
    RERANK_MODEL         AITeamVN/Vietnamese_Reranker   (để rỗng = không bật rerank)
    DEVICE               cuda nếu có GPU, ngược lại cpu
    FP16                 1  (chỉ có tác dụng khi DEVICE=cuda)
    MODEL_SERVER_TOKEN   nếu đặt: mọi request phải có header "Authorization: Bearer <token>"

Chạy trên máy local:
    venv/bin/uvicorn model_server:app --app-dir src --port 8001
Chạy trên máy cloud (chỉ cần file này):
    pip install fastapi uvicorn torch sentence-transformers llama-index-core llama-index-embeddings-huggingface
    MODEL_SERVER_TOKEN=<bí mật> uvicorn model_server:app --host 0.0.0.0 --port 8001
Phía client đặt trong .env: MODEL_SERVER_URL=http://<ip>:<port>, MODEL_SERVER_TOKEN=<bí mật>.
"""
import os
import secrets
import threading
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Literal

import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pydantic import BaseModel

EMBED_MODEL = os.environ.get("EMBED_MODEL", "AITeamVN/Vietnamese_Embedding")
RERANK_MODEL = os.environ.get("RERANK_MODEL", "AITeamVN/Vietnamese_Reranker") or None
DEVICE = os.environ.get("DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
FP16 = os.environ.get("FP16", "1") == "1" and DEVICE == "cuda"
TOKEN = os.environ.get("MODEL_SERVER_TOKEN") or None

embed_model: HuggingFaceEmbedding | None = None
reranker: SentenceTransformerRerank | None = None
gpu_lock = threading.Lock()  # endpoint sync chạy trong threadpool: mỗi lúc chỉ 1 request dùng GPU


def load_embedding() -> HuggingFaceEmbedding:
    # Giữ giống make_local_embedding() trong src/index_builder.py
    return HuggingFaceEmbedding(
        model_name=EMBED_MODEL,
        device=DEVICE,
        embed_batch_size=4 if FP16 else 10,  # batch nhỏ để không tràn VRAM trên card 4 GB
        model_kwargs={"torch_dtype": torch.float16} if FP16 else {},
    )


def load_reranker(model_name: str) -> SentenceTransformerRerank:
    # Giữ giống make_local_reranker() trong src/retriever.py
    rerank = SentenceTransformerRerank(model=model_name, device="cpu" if FP16 else DEVICE)
    if FP16:
        # SentenceTransformerRerank không nhận dtype: nạp trên CPU, ép fp16 rồi mới đưa lên GPU
        rerank._model.half().to(DEVICE)  # pyright: ignore[reportPrivateUsage]
        rerank.device = DEVICE
    return rerank


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    global embed_model, reranker
    embed_model = load_embedding()
    reranker = load_reranker(RERANK_MODEL) if RERANK_MODEL else None
    yield
    embed_model = reranker = None


def check_token(authorization: str | None = Header(default=None)) -> None:
    if TOKEN and not (authorization and secrets.compare_digest(authorization, f"Bearer {TOKEN}")):
        raise HTTPException(status_code=401, detail="Sai hoặc thiếu token (header Authorization: Bearer ...)")


app = FastAPI(lifespan=lifespan, dependencies=[Depends(check_token)])


class EmbedRequest(BaseModel):
    texts: list[str]
    kind: Literal["query", "text"] = "text"


class RerankRequest(BaseModel):
    query: str
    texts: list[str]


@app.get("/health")
def health() -> dict[str, str | bool | None]:
    return {"embed_model": EMBED_MODEL, "reranker_model": RERANK_MODEL, "device": DEVICE, "fp16": FP16}


@app.post("/embed")
def embed(req: EmbedRequest) -> dict[str, list[list[float]]]:
    if embed_model is None:
        raise HTTPException(status_code=503, detail="Model embedding chưa nạp xong")
    with gpu_lock:
        if req.kind == "query":
            vectors = [embed_model.get_query_embedding(q) for q in req.texts]
        else:
            vectors = embed_model.get_text_embedding_batch(req.texts)
    return {"embeddings": vectors}


@app.post("/rerank")
def rerank(req: RerankRequest) -> dict[str, list[float]]:
    if reranker is None:
        raise HTTPException(status_code=400, detail="Server không bật reranker (RERANK_MODEL rỗng)")
    with gpu_lock:
        scores = reranker._model.predict([(req.query, t) for t in req.texts])  # pyright: ignore[reportPrivateUsage]
    return {"scores": [float(s) for s in scores]}
