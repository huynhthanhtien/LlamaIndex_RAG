#!/usr/bin/env bash
# Cài đặt và chạy toàn bộ phần server của SGU RAG trên một container có Ollama (vd image ollama/ollama).
#
#   - Ollama: đảm bảo đang chạy (nghe 0.0.0.0) và đã pull LLM_MODEL.
#   - Model server (embedding + reranker, file model_server.py nhúng ở cuối script): cài Python/venv/thư viện,
#     bật bằng uvicorn chạy nền (không token, trừ khi đặt MODEL_SERVER_TOKEN).
#   - In ra các dòng cần chép vào .env trên máy local.
#
# Chỉ cần mỗi file này:   bash setup_server.sh
# Chạy lại được nhiều lần: bước nào đã xong thì bỏ qua; model server được khởi động lại.
#
# Cấu hình bằng biến môi trường (mặc định khớp profile "server" trong src/config.py):
#   LLM_MODEL=qwen3:8b  OLLAMA_PORT=11434  MODEL_SERVER_PORT=8001
#   EMBED_MODEL=AITeamVN/Vietnamese_Embedding  RERANK_MODEL=AITeamVN/Vietnamese_Reranker (rỗng = tắt rerank)
#   MODEL_SERVER_TOKEN=   (rỗng: không xác thực — đủ cho chạy thử ngắn)     WORKDIR=$HOME/sgu-rag-server
#   TORCH_INDEX_URL=      (vd https://download.pytorch.org/whl/cpu khi máy không có GPU)
#   SKIP_LLM=0            (1 = không pull/kiểm tra LLM, chỉ dựng model server)
set -euo pipefail

LLM_MODEL="${LLM_MODEL:-qwen3:8b}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
MODEL_SERVER_PORT="${MODEL_SERVER_PORT:-8001}"
EMBED_MODEL="${EMBED_MODEL:-AITeamVN/Vietnamese_Embedding}"
RERANK_MODEL="${RERANK_MODEL-AITeamVN/Vietnamese_Reranker}"
WORKDIR="${WORKDIR:-$HOME/sgu-rag-server}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-}"
MODEL_SERVER_TOKEN="${MODEL_SERVER_TOKEN:-}"
SKIP_LLM="${SKIP_LLM:-0}"
export HF_HOME="${HF_HOME:-$WORKDIR/hf_cache}"   # cache model HuggingFace, giữ lại giữa các lần chạy

OLLAMA_URL="http://127.0.0.1:$OLLAMA_PORT"
SERVER_URL="http://127.0.0.1:$MODEL_SERVER_PORT"
# sentencepiece + protobuf: tokenizer của Vietnamese_Reranker chỉ có sentencepiece.bpe.model (không có tokenizer.json)
PY_PACKAGES=(sentence-transformers sentencepiece protobuf llama-index-core llama-index-embeddings-huggingface fastapi uvicorn)

log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { echo "[LỖI] $*" >&2; exit 1; }
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# ---------- 1. GPU ----------
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    log "GPU: $(nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader | head -1)"
else
    log "CẢNH BÁO: không thấy GPU (nvidia-smi) — model chạy trên CPU, rất chậm"
fi

# ---------- 2. Gói hệ thống ----------
need=()
command -v curl >/dev/null 2>&1 || need+=(curl ca-certificates)
command -v python3 >/dev/null 2>&1 || need+=(python3)
python3 -c "import venv, ensurepip" >/dev/null 2>&1 || need+=(python3-venv python3-pip)
if ((${#need[@]})); then
    command -v apt-get >/dev/null 2>&1 || die "Thiếu ${need[*]} và không có apt-get để cài"
    SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"
    log "Cài gói hệ thống: ${need[*]}"
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get update -qq
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends "${need[@]}" >/dev/null
fi
log "Python: $(python3 --version)"

# ---------- 3. Ollama ----------
ollama_ok() { curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; }
if [ "$SKIP_LLM" = "1" ]; then
    log "Bỏ qua Ollama (SKIP_LLM=1)"
else
    command -v ollama >/dev/null 2>&1 || die "Không có lệnh ollama — container này không phải image Ollama?"
    if ollama_ok; then
        log "Ollama đã chạy tại cổng $OLLAMA_PORT"
    else
        log "Khởi động ollama serve (nghe 0.0.0.0:$OLLAMA_PORT)"
        OLLAMA_HOST="0.0.0.0:$OLLAMA_PORT" nohup ollama serve >"$WORKDIR/ollama.log" 2>&1 &
        for _ in $(seq 60); do ollama_ok && break; sleep 1; done
        ollama_ok || { tail -20 "$WORKDIR/ollama.log"; die "Ollama không lên sau 60s"; }
    fi
    if OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" ollama list | awk 'NR>1 {print $1}' | grep -qx "$LLM_MODEL"; then
        log "LLM $LLM_MODEL đã có"
    else
        log "Pull LLM $LLM_MODEL (lần đầu mất vài phút)"
        OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" ollama pull "$LLM_MODEL"
    fi
    log "Thử LLM..."
    t0=$(date +%s)
    curl -sf --max-time 600 "$OLLAMA_URL/api/chat" \
        -d "{\"model\": \"$LLM_MODEL\", \"stream\": false, \"think\": false, \"messages\": [{\"role\": \"user\", \"content\": \"Trả lời đúng một từ: xin chào\"}]}" \
        >"$WORKDIR/llm_test.json" || die "Gọi thử LLM thất bại"
    log "LLM trả lời sau $(( $(date +%s) - t0 ))s"
fi

# ---------- 4. Python venv + thư viện ----------
if [ ! -x "$WORKDIR/venv/bin/python" ]; then
    log "Tạo venv $WORKDIR/venv"
    python3 -m venv "$WORKDIR/venv"
fi
PIP=("$WORKDIR/venv/bin/python" -m pip install -q --disable-pip-version-check)
stamp="$WORKDIR/venv/.installed-$(echo "$TORCH_INDEX_URL ${PY_PACKAGES[*]}" | md5sum | cut -c1-8)"
if [ -f "$stamp" ]; then
    log "Thư viện Python đã cài"
else
    log "Cài torch${TORCH_INDEX_URL:+ (từ $TORCH_INDEX_URL)} — lần đầu tải vài GB"
    if [ -n "$TORCH_INDEX_URL" ]; then "${PIP[@]}" torch --index-url "$TORCH_INDEX_URL"; else "${PIP[@]}" torch; fi
    log "Cài ${PY_PACKAGES[*]}"
    "${PIP[@]}" "${PY_PACKAGES[@]}"
    touch "$stamp"
fi
"$WORKDIR/venv/bin/python" -c "import torch; print('[torch]', torch.__version__, '| CUDA:', torch.cuda.is_available())"

# ---------- 5. model_server.py (nhúng nguyên văn từ src/model_server.py) ----------
cat >"$WORKDIR/model_server.py" <<'MODEL_SERVER_PY_EOF'
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
MODEL_SERVER_PY_EOF
log "Đã ghi $WORKDIR/model_server.py"

# ---------- 6. Chạy model server (dừng bản cũ nếu có) ----------
if [ -s "$WORKDIR/server.pid" ] && kill -0 "$(cat "$WORKDIR/server.pid")" 2>/dev/null; then
    log "Dừng model server cũ (pid $(cat "$WORKDIR/server.pid"))"
    kill "$(cat "$WORKDIR/server.pid")"; sleep 3
fi
log "Khởi động model server tại 0.0.0.0:$MODEL_SERVER_PORT (embedding: $EMBED_MODEL, rerank: ${RERANK_MODEL:-tắt})"
EMBED_MODEL="$EMBED_MODEL" RERANK_MODEL="$RERANK_MODEL" MODEL_SERVER_TOKEN="$MODEL_SERVER_TOKEN" \
    nohup "$WORKDIR/venv/bin/python" -m uvicorn model_server:app --app-dir "$WORKDIR" \
    --host 0.0.0.0 --port "$MODEL_SERVER_PORT" >"$WORKDIR/server.log" 2>&1 &
echo $! >"$WORKDIR/server.pid"

AUTH=()
[ -z "$MODEL_SERVER_TOKEN" ] || AUTH=(-H "Authorization: Bearer $MODEL_SERVER_TOKEN")
log "Đợi model server nạp model (lần đầu tải model từ HuggingFace, có thể vài phút)..."
for _ in $(seq 900); do
    curl -sf "${AUTH[@]}" "$SERVER_URL/health" >/dev/null 2>&1 && break
    kill -0 "$(cat "$WORKDIR/server.pid")" 2>/dev/null || { tail -30 "$WORKDIR/server.log"; die "Model server đã dừng, xem log ở trên"; }
    sleep 2
done
curl -sf "${AUTH[@]}" "$SERVER_URL/health" >/dev/null || { tail -30 "$WORKDIR/server.log"; die "Model server không lên sau 30 phút"; }
log "health: $(curl -sf "${AUTH[@]}" "$SERVER_URL/health")"

# ---------- 7. Kiểm tra nhanh ----------
dim=$(curl -sf "${AUTH[@]}" -H "Content-Type: application/json" "$SERVER_URL/embed" \
    -d '{"texts": ["Sinh viên được rút học phần trong bao lâu?"], "kind": "query"}' \
    | "$WORKDIR/venv/bin/python" -c "import json, sys; print(len(json.load(sys.stdin)['embeddings'][0]))") || die "/embed lỗi"
log "/embed OK (vector $dim chiều)"
if [ -n "$RERANK_MODEL" ]; then
    curl -sf "${AUTH[@]}" -H "Content-Type: application/json" "$SERVER_URL/rerank" \
        -d '{"query": "rút học phần", "texts": ["Việc rút bớt học phần thực hiện trong 03 tuần đầu học kì.", "Công nhận tốt nghiệp"]}' \
        >/dev/null || die "/rerank lỗi"
    log "/rerank OK"
fi
command -v nvidia-smi >/dev/null 2>&1 && log "VRAM: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | head -1)"

# ---------- 8. Hướng dẫn cho máy local ----------
NO_AUTH="Ollama và model server"; [ -z "$MODEL_SERVER_TOKEN" ] || NO_AUTH="Ollama"
cat <<EOF

=====================================================================
Xong. Trên MÁY LOCAL, ghi vào .env của dự án (thay <IP> và <CỔNG> bằng địa chỉ
công khai mà nhà cung cấp ánh xạ cho cổng $OLLAMA_PORT và $MODEL_SERVER_PORT của container):

RAG_PROFILE=server
OLLAMA_BASE_URL=http://<IP>:<CỔNG của $OLLAMA_PORT>
MODEL_SERVER_URL=http://<IP>:<CỔNG của $MODEL_SERVER_PORT>
${MODEL_SERVER_TOKEN:+MODEL_SERVER_TOKEN=$MODEL_SERVER_TOKEN
}
Log:      tail -f $WORKDIR/server.log   (Ollama tự bật: $WORKDIR/ollama.log)
Dừng:     kill \$(cat $WORKDIR/server.pid)
Chạy lại: bash $0     (container khởi động lại thì phải chạy lại)
Lưu ý: $NO_AUTH không có xác thực — ai biết địa chỉ cũng gọi được; chạy thử xong nhớ tắt máy.
=====================================================================
EOF
