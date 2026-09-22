#!/usr/bin/env bash
#
# Pull các model (LLM qua Ollama, embedding/reranker qua HuggingFace) cần thiết
# cho một profile của dự án, đồng bộ với định nghĩa trong src/config.py.
#
# Usage:
#   ./scripts/pull_models.sh [local|server]
#
# Biến môi trường:
#   RAG_PROFILE      profile mặc định nếu không truyền tham số (mặc định: server)
#   OLLAMA_BASE_URL  base URL của Ollama daemon (mặc định: http://localhost:11434)

set -euo pipefail

PROFILE="${1:-${RAG_PROFILE:-server}}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

case "$PROFILE" in
  local)
    LLM_MODEL="qwen3:4b"
    EMBED_MODEL="bkai-foundation-models/vietnamese-bi-encoder"
    RERANKER_MODEL=""
    ;;
  server)
    LLM_MODEL="qwen3:8b"
    EMBED_MODEL="AITeamVN/Vietnamese_Embedding"
    RERANKER_MODEL="AITeamVN/Vietnamese_Reranker"
    ;;
  *)
    echo "Profile không hợp lệ: '$PROFILE' (chỉ chấp nhận 'local' hoặc 'server')" >&2
    exit 1
    ;;
esac

echo "== Profile: $PROFILE =="
echo "LLM (Ollama):    $LLM_MODEL"
echo "Embedding (HF):  $EMBED_MODEL"
if [[ -n "$RERANKER_MODEL" ]]; then
  echo "Reranker (HF):   $RERANKER_MODEL"
fi
echo

# --- 1. Pull LLM qua Ollama ---
if ! command -v ollama >/dev/null 2>&1; then
  echo "Lỗi: không tìm thấy lệnh 'ollama'. Cài đặt tại https://ollama.com/" >&2
  exit 1
fi

if ! curl -sf "${OLLAMA_BASE_URL}/api/version" >/dev/null 2>&1; then
  echo "Lỗi: không kết nối được Ollama daemon tại ${OLLAMA_BASE_URL}." >&2
  echo "Chạy 'ollama serve' (hoặc kiểm tra OLLAMA_BASE_URL) rồi thử lại." >&2
  exit 1
fi

echo "-> ollama pull ${LLM_MODEL}"
OLLAMA_HOST="$OLLAMA_BASE_URL" ollama pull "$LLM_MODEL"

# --- 2. Tải model embedding (và reranker nếu có) từ HuggingFace ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Lỗi: không tìm thấy 'python3'." >&2
  exit 1
fi

if ! python3 -c "import huggingface_hub" >/dev/null 2>&1; then
  echo "Lỗi: thiếu package 'huggingface_hub' (cài kèm sentence-transformers trong requirements.txt)." >&2
  echo "Chạy: pip install -r requirements.txt" >&2
  exit 1
fi

download_hf_model() {
  local repo_id="$1"
  echo "-> huggingface: snapshot_download(${repo_id})"
  python3 - "$repo_id" <<'PY'
import sys
from huggingface_hub import snapshot_download

repo_id = sys.argv[1]
path = snapshot_download(repo_id=repo_id)
print(f"   đã tải về: {path}")
PY
}

download_hf_model "$EMBED_MODEL"
if [[ -n "$RERANKER_MODEL" ]]; then
  download_hf_model "$RERANKER_MODEL"
fi

echo
echo "Hoàn tất pull model cho profile '$PROFILE'."
