"""Model server: nạp embedding + reranker lên GPU một lần, các tiến trình RAG gọi qua HTTP.

Chạy (profile lấy từ RAG_PROFILE, giống pipeline):
    venv/bin/uvicorn model_server:app --app-dir src --port 8001
Rồi đặt MODEL_SERVER_URL=http://localhost:8001 trong .env cho phía client.
"""
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import get_config
from index_builder import make_local_embedding
from retriever import make_local_reranker

cfg = get_config()
models = {}
gpu_lock = threading.Lock()  # endpoint sync chạy trong threadpool: mỗi lúc chỉ 1 request dùng GPU


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dùng chung hàm nạp với chế độ local nên vector giống hệt (cùng prompt, normalize, fp16)
    models["embed"] = make_local_embedding(cfg)
    if cfg.reranker_model_name:
        models["rerank"] = make_local_reranker(cfg)
    yield
    models.clear()


app = FastAPI(lifespan=lifespan)


class EmbedRequest(BaseModel):
    texts: list[str]
    kind: Literal["query", "text"] = "text"


class RerankRequest(BaseModel):
    query: str
    texts: list[str]


@app.get("/health")
def health():
    return {"embed_model": cfg.embed_model_name, "reranker_model": cfg.reranker_model_name}


@app.post("/embed")
def embed(req: EmbedRequest):
    emb = models["embed"]
    with gpu_lock:
        if req.kind == "query":
            vectors = [emb.get_query_embedding(q) for q in req.texts]
        else:
            vectors = emb.get_text_embedding_batch(req.texts)
    return {"embeddings": vectors}


@app.post("/rerank")
def rerank(req: RerankRequest):
    reranker = models.get("rerank")
    if reranker is None:
        raise HTTPException(status_code=400, detail="Profile này không bật reranker")
    with gpu_lock:
        scores = reranker._model.predict([(req.query, t) for t in req.texts])  # pyright: ignore[reportPrivateUsage]
    return {"scores": [float(s) for s in scores]}
