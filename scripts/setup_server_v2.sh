#!/usr/bin/env bash
# setup_server.sh v2 — như setup_server.sh nhưng chạy được trên Google Colab và tự mở URL công khai.
#
#   - Ollama: tự cài nếu chưa có, chạy nền, pull LLM_MODEL, gọi thử.
#   - Model server (embedding + reranker, file model_server.py nhúng ở giữa script): cài thư viện,
#     bật bằng uvicorn chạy nền.
#   - URL công khai qua Cloudflare quick tunnel (*.trycloudflare.com, không cần tài khoản) cho cả hai cổng.
#   - In ra các dòng cần chép vào .env trên máy local (URL thật, không phải <IP>:<CỔNG>).
#
# Trên Colab (Runtime > Change runtime type > T4 GPU), upload file này rồi chạy một ô:
#     !bash setup_server_v2.sh
# Máy/container khác:  bash scripts/setup_server_v2.sh
# Chạy lại được nhiều lần: bước nào đã xong thì bỏ qua; model server được khởi động lại;
# tunnel còn sống thì giữ nguyên URL.
#
# Khác v1:
#   - Colab: dùng python3 + torch có sẵn của Colab (không tạo venv, không tải lại torch ~2GB).
#   - Không có ollama thì tự cài (v1 dừng lại).
#   - Tiến trình nền chạy bằng setsid để sống sau khi ô Colab chạy xong.
#   - PUBLIC_TUNNEL=cloudflared (mặc định): server chỉ nghe 127.0.0.1, ra ngoài qua tunnel.
#     Như v1, model server không có token trừ khi tự đặt MODEL_SERVER_TOKEN.
#   - Thư viện của model server ghim cùng phiên bản requirements.txt để vector khớp index đã build ở local.
#
# Cấu hình bằng biến môi trường (mặc định khớp profile "server" trong src/config.py):
#   LLM_MODEL=qwen3:8b  OLLAMA_PORT=11434  MODEL_SERVER_PORT=8001
#   EMBED_MODEL=AITeamVN/Vietnamese_Embedding  RERANK_MODEL=AITeamVN/Vietnamese_Reranker (rỗng = tắt rerank)
#   MODEL_SERVER_TOKEN=   (rỗng: không xác thực)   WORKDIR=/content/sgu-rag-server trên Colab, $HOME/sgu-rag-server nơi khác
#   PUBLIC_TUNNEL=cloudflared   (none = như v1: nghe 0.0.0.0, tự ánh xạ cổng)
#   USE_VENV=     (mặc định 0 trên Colab, 1 nơi khác)   TORCH_INDEX_URL=   (chỉ dùng khi USE_VENV=1)
#   SKIP_LLM=0    (1 = không cài/pull/kiểm tra LLM, chỉ dựng model server)
set -euo pipefail

IS_COLAB=0; { [ -n "${COLAB_RELEASE_TAG:-}" ] || [ -d /content ]; } && IS_COLAB=1
LLM_MODEL="${LLM_MODEL:-qwen3:8b}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"
MODEL_SERVER_PORT="${MODEL_SERVER_PORT:-8001}"
EMBED_MODEL="${EMBED_MODEL:-AITeamVN/Vietnamese_Embedding}"
RERANK_MODEL="${RERANK_MODEL-AITeamVN/Vietnamese_Reranker}"
if [ "$IS_COLAB" = 1 ]; then WORKDIR="${WORKDIR:-/content/sgu-rag-server}"; else WORKDIR="${WORKDIR:-$HOME/sgu-rag-server}"; fi
USE_VENV="${USE_VENV:-$((1 - IS_COLAB))}"
TORCH_INDEX_URL="${TORCH_INDEX_URL:-}"
MODEL_SERVER_TOKEN="${MODEL_SERVER_TOKEN:-}"
PUBLIC_TUNNEL="${PUBLIC_TUNNEL:-cloudflared}"
SKIP_LLM="${SKIP_LLM:-0}"
export HF_HOME="${HF_HOME:-$WORKDIR/hf_cache}"   # cache model HuggingFace, giữ lại giữa các lần chạy

OLLAMA_URL="http://127.0.0.1:$OLLAMA_PORT"
SERVER_URL="http://127.0.0.1:$MODEL_SERVER_PORT"
LISTEN="0.0.0.0"; [ "$PUBLIC_TUNNEL" = "none" ] || LISTEN="127.0.0.1"   # có tunnel thì không mở cổng trực tiếp
# Ghim như requirements.txt (embedding phải khớp index đã build ở local). Không ghim torch: Colab có sẵn bản CUDA.
# sentencepiece + protobuf: tokenizer của Vietnamese_Reranker chỉ có sentencepiece.bpe.model (không có tokenizer.json)
PY_PACKAGES=(sentence-transformers==6.0.1 sentencepiece==0.2.2 protobuf llama-index-core==0.14.24
             llama-index-embeddings-huggingface==0.8.0 fastapi uvicorn)
CLOUDFLARED_URL="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"

log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { echo "[LỖI] $*" >&2; exit 1; }
alive() { [ -s "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null; }
# Chạy nền, tách khỏi phiên của ô Colab: $1 = file pid, $2 = file log, còn lại là lệnh
bg() { local pidf=$1 logf=$2; shift 2; setsid nohup "$@" </dev/null >"$logf" 2>&1 & echo $! >"$pidf"; }
SUDO=""; [ "$(id -u)" -eq 0 ] || SUDO="sudo"
apt_install() {
    command -v apt-get >/dev/null 2>&1 || die "Thiếu $* và không có apt-get để cài"
    log "Cài gói hệ thống: $*"
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get update -qq
    $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends "$@" >/dev/null
}
mkdir -p "$WORKDIR"
cd "$WORKDIR"
log "Môi trường: $([ "$IS_COLAB" = 1 ] && echo Colab || echo máy thường) | WORKDIR=$WORKDIR | tunnel: $PUBLIC_TUNNEL"

# ---------- 1. GPU ----------
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
    log "GPU: $(nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader | head -1)"
else
    goi_y=""; [ "$IS_COLAB" = 1 ] && goi_y=". Colab: Runtime > Change runtime type > T4 GPU"
    log "CẢNH BÁO: không thấy GPU (nvidia-smi) — model chạy trên CPU, rất chậm$goi_y"
fi

# ---------- 2. Gói hệ thống ----------
need=()
command -v curl >/dev/null 2>&1 || need+=(curl ca-certificates)
command -v python3 >/dev/null 2>&1 || need+=(python3)
[ "$USE_VENV" = 1 ] && ! python3 -c "import venv, ensurepip" >/dev/null 2>&1 && need+=(python3-venv python3-pip)
# zstd: script cài Ollama giải nén .tar.zst; pciutils/lshw: Ollama dò GPU
[ "$SKIP_LLM" = 1 ] || command -v ollama >/dev/null 2>&1 || need+=(zstd pciutils lshw)
((${#need[@]} == 0)) || apt_install "${need[@]}"
log "Python: $(python3 --version)"

# ---------- 3. Ollama ----------
ollama_ok() { curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; }
if [ "$SKIP_LLM" = "1" ]; then
    log "Bỏ qua Ollama (SKIP_LLM=1)"
else
    if ! command -v ollama >/dev/null 2>&1; then
        log "Cài Ollama"
        curl -fsSL https://ollama.com/install.sh | sh >/dev/null
    fi
    if ollama_ok; then
        log "Ollama đã chạy tại cổng $OLLAMA_PORT"
    else
        log "Khởi động ollama serve (nghe $LISTEN:$OLLAMA_PORT)"
        # KEEP_ALIVE=-1: giữ LLM trên VRAM, không nạp lại giữa các câu hỏi
        OLLAMA_HOST="$LISTEN:$OLLAMA_PORT" OLLAMA_KEEP_ALIVE=-1 bg "$WORKDIR/ollama.pid" "$WORKDIR/ollama.log" ollama serve
        for _ in $(seq 60); do ollama_ok && break; sleep 1; done
        ollama_ok || { tail -20 "$WORKDIR/ollama.log"; die "Ollama không lên sau 60s"; }
    fi
    if OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" ollama list | awk 'NR>1 {print $1}' | grep -qx "$LLM_MODEL"; then
        log "LLM $LLM_MODEL đã có"
    else
        log "Pull LLM $LLM_MODEL (lần đầu mất vài phút)"
        OLLAMA_HOST="127.0.0.1:$OLLAMA_PORT" ollama pull "$LLM_MODEL"
    fi
    log "Thử LLM (đồng thời nạp model lên GPU)..."
    t0=$(date +%s)
    curl -sf --max-time 600 "$OLLAMA_URL/api/chat" \
        -d "{\"model\": \"$LLM_MODEL\", \"stream\": false, \"think\": false, \"messages\": [{\"role\": \"user\", \"content\": \"Trả lời đúng một từ: xin chào\"}]}" \
        >"$WORKDIR/llm_test.json" || die "Gọi thử LLM thất bại"
    log "LLM trả lời sau $(( $(date +%s) - t0 ))s"
fi

# ---------- 4. Python + thư viện ----------
if [ "$USE_VENV" = 1 ]; then
    [ -x "$WORKDIR/venv/bin/python" ] || { log "Tạo venv $WORKDIR/venv"; python3 -m venv "$WORKDIR/venv"; }
    PY="$WORKDIR/venv/bin/python"
else
    PY="$(command -v python3)"   # Colab: dùng python3 hệ thống, đã có torch bản CUDA
fi
PIP=("$PY" -m pip install -q --disable-pip-version-check)
stamp="$WORKDIR/.installed-$(echo "$PY $USE_VENV $TORCH_INDEX_URL ${PY_PACKAGES[*]}" | md5sum | cut -c1-8)"
if [ -f "$stamp" ]; then
    log "Thư viện Python đã cài"
else
    if [ "$USE_VENV" = 1 ]; then
        log "Cài torch${TORCH_INDEX_URL:+ (từ $TORCH_INDEX_URL)} — lần đầu tải vài GB"
        if [ -n "$TORCH_INDEX_URL" ]; then "${PIP[@]}" torch --index-url "$TORCH_INDEX_URL"; else "${PIP[@]}" torch; fi
    fi
    log "Cài ${PY_PACKAGES[*]}"
    "${PIP[@]}" "${PY_PACKAGES[@]}"
    touch "$stamp"
fi
"$PY" -c "import torch; print('[torch]', torch.__version__, '| CUDA:', torch.cuda.is_available())"

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

# ---------- 6. Token (tuỳ chọn: chỉ khi tự đặt MODEL_SERVER_TOKEN) ----------
AUTH=()
[ -z "$MODEL_SERVER_TOKEN" ] || AUTH=(-H "Authorization: Bearer $MODEL_SERVER_TOKEN")

# ---------- 7. Chạy model server (dừng bản cũ nếu có) ----------
if alive "$WORKDIR/server.pid"; then
    log "Dừng model server cũ (pid $(cat "$WORKDIR/server.pid"))"
    kill "$(cat "$WORKDIR/server.pid")"; sleep 3
fi
log "Khởi động model server tại $LISTEN:$MODEL_SERVER_PORT (embedding: $EMBED_MODEL, rerank: ${RERANK_MODEL:-tắt})"
EMBED_MODEL="$EMBED_MODEL" RERANK_MODEL="$RERANK_MODEL" MODEL_SERVER_TOKEN="$MODEL_SERVER_TOKEN" \
    bg "$WORKDIR/server.pid" "$WORKDIR/server.log" \
    "$PY" -m uvicorn model_server:app --app-dir "$WORKDIR" --host "$LISTEN" --port "$MODEL_SERVER_PORT"

log "Đợi model server nạp model (lần đầu tải model từ HuggingFace, có thể vài phút)..."
for _ in $(seq 900); do
    curl -sf "${AUTH[@]}" "$SERVER_URL/health" >/dev/null 2>&1 && break
    alive "$WORKDIR/server.pid" || { tail -30 "$WORKDIR/server.log"; die "Model server đã dừng, xem log ở trên"; }
    sleep 2
done
curl -sf "${AUTH[@]}" "$SERVER_URL/health" >/dev/null || { tail -30 "$WORKDIR/server.log"; die "Model server không lên sau 30 phút"; }
log "health: $(curl -sf "${AUTH[@]}" "$SERVER_URL/health")"

# ---------- 8. Kiểm tra nhanh (tại chỗ) ----------
check_embed() {  # $1 = base URL
    curl -sf --max-time 60 "${AUTH[@]}" -H "Content-Type: application/json" "$1/embed" \
        -d '{"texts": ["Sinh viên được rút học phần trong bao lâu?"], "kind": "query"}' \
        | "$PY" -c "import json, sys; print(len(json.load(sys.stdin)['embeddings'][0]))"
}
dim=$(check_embed "$SERVER_URL") || die "/embed lỗi"
log "/embed OK (vector $dim chiều)"
if [ -n "$RERANK_MODEL" ]; then
    curl -sf "${AUTH[@]}" -H "Content-Type: application/json" "$SERVER_URL/rerank" \
        -d '{"query": "rút học phần", "texts": ["Việc rút bớt học phần thực hiện trong 03 tuần đầu học kì.", "Công nhận tốt nghiệp"]}' \
        >/dev/null || die "/rerank lỗi"
    log "/rerank OK"
fi
command -v nvidia-smi >/dev/null 2>&1 && log "VRAM: $(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader | head -1)"

# ---------- 9. URL công khai (Cloudflare quick tunnel) ----------
PUB_OLLAMA=""; PUB_SERVER=""
if [ "$PUBLIC_TUNNEL" = "cloudflared" ]; then
    CF="$(command -v cloudflared || echo "$WORKDIR/cloudflared")"
    if [ ! -x "$CF" ]; then
        log "Tải cloudflared"
        curl -fsSL -o "$CF" "$CLOUDFLARED_URL" && chmod +x "$CF"
    fi
    # `|| true`: log chưa có URL thì grep trả 1, với `set -e` + pipefail sẽ làm script thoát im lặng
    tunnel_url() { { grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$WORKDIR/tunnel-$1.log" 2>/dev/null || true; } | tail -1; }
    # $1 = tên, $2 = cổng, $3 = lệnh curl kiểm tra (nhận URL), còn lại = tham số thêm cho cloudflared.
    # Đặt TUNNEL_URL. Tunnel cũ còn sống thì giữ nguyên URL (model server khởi động lại vẫn cùng cổng).
    open_tunnel() {
        local name=$1 port=$2 check=$3; shift 3
        TUNNEL_URL=""
        # Tunnel cũ còn sống VÀ gọi được thì giữ; còn sống mà lỗi (vd 530 khi mất kết nối tới Cloudflare) thì mở lại
        if alive "$WORKDIR/tunnel-$name.pid" && TUNNEL_URL="$(tunnel_url "$name")" && [ -n "$TUNNEL_URL" ] && $check "$TUNNEL_URL"; then
            log "Giữ tunnel $name đang chạy: $TUNNEL_URL"
        else
            if alive "$WORKDIR/tunnel-$name.pid"; then kill "$(cat "$WORKDIR/tunnel-$name.pid")"; sleep 1; fi
            log "Mở tunnel $name -> 127.0.0.1:$port"
            bg "$WORKDIR/tunnel-$name.pid" "$WORKDIR/tunnel-$name.log" \
                "$CF" tunnel --no-autoupdate --url "http://127.0.0.1:$port" "$@"
            for _ in $(seq 60); do TUNNEL_URL="$(tunnel_url "$name")"; [ -n "$TUNNEL_URL" ] && break; sleep 1; done
            [ -n "$TUNNEL_URL" ] || { tail -20 "$WORKDIR/tunnel-$name.log"; die "cloudflared không trả URL cho $name"; }
        fi
        # URL mới cần vài giây để DNS phân giải được
        for _ in $(seq 45); do $check "$TUNNEL_URL" && return 0; sleep 2; done
        tail -20 "$WORKDIR/tunnel-$name.log"; die "Không gọi được $name qua $TUNNEL_URL"
    }
    check_ollama_pub() { curl -sf --max-time 15 "$1/api/tags" >/dev/null 2>&1; }
    check_server_pub() { curl -sf --max-time 15 "${AUTH[@]}" "$1/health" >/dev/null 2>&1; }

    if [ "$SKIP_LLM" != "1" ]; then
        # Ollama từ chối request mang Host lạ (*.trycloudflare.com) -> ghi đè Host thành localhost
        open_tunnel ollama "$OLLAMA_PORT" check_ollama_pub --http-host-header "localhost:$OLLAMA_PORT"
        PUB_OLLAMA="$TUNNEL_URL"
    fi
    open_tunnel server "$MODEL_SERVER_PORT" check_server_pub
    PUB_SERVER="$TUNNEL_URL"
    dim=$(check_embed "$PUB_SERVER") || die "/embed qua URL công khai lỗi"
    log "Qua URL công khai: /embed OK ($dim chiều)${PUB_OLLAMA:+, Ollama OK}"
fi

# ---------- 10. Hướng dẫn cho máy local ----------
if [ -n "$PUB_SERVER" ]; then
    LINE_OLLAMA="OLLAMA_BASE_URL=${PUB_OLLAMA:-<bỏ qua: SKIP_LLM=1>}"
    LINE_SERVER="MODEL_SERVER_URL=$PUB_SERVER"
    GHI_CHU="URL công khai (Cloudflare quick tunnel); runtime/máy khởi động lại thì URL đổi — chạy lại script và sửa .env."
else
    LINE_OLLAMA="OLLAMA_BASE_URL=http://<IP>:<CỔNG của $OLLAMA_PORT>"
    LINE_SERVER="MODEL_SERVER_URL=http://<IP>:<CỔNG của $MODEL_SERVER_PORT>"
    GHI_CHU="Thay <IP> và <CỔNG> bằng địa chỉ công khai mà nhà cung cấp ánh xạ cho cổng của container."
fi
NO_AUTH="Ollama và model server"; [ -z "$MODEL_SERVER_TOKEN" ] || NO_AUTH="Ollama"
cat <<EOF

=====================================================================
Xong. Trên MÁY LOCAL, ghi vào .env của dự án:

RAG_PROFILE=server
$LINE_OLLAMA
$LINE_SERVER
${MODEL_SERVER_TOKEN:+MODEL_SERVER_TOKEN=$MODEL_SERVER_TOKEN
}
$GHI_CHU
Log:      tail -f $WORKDIR/server.log   (Ollama: $WORKDIR/ollama.log, tunnel: $WORKDIR/tunnel-*.log)
Dừng:     kill \$(cat $WORKDIR/server.pid)   (tunnel: kill \$(cat $WORKDIR/tunnel-*.pid))
Chạy lại: bash $0
Lưu ý: $NO_AUTH không có xác thực — ai biết địa chỉ cũng gọi được; chạy thử xong nhớ tắt máy/runtime.
=====================================================================
EOF
