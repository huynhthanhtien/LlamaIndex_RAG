"""Biến Colab GPU thành server cho dự án: in ra link LLM (Ollama) và link embedding/reranker (model_server)
để dán vào .env trên máy bạn. Index, retriever, query engine, đánh giá vẫn chạy ở máy bạn như cũ.

Cách dùng trong Colab (Runtime > Change runtime type > T4 GPU):
    1. Upload 2 file lên /content: scripts/colab_server.py và src/model_server.py
       (hoặc clone repo; script tìm model_server.py cạnh nó hoặc ở ../src/)
    2. Chạy một ô:
        !python colab_server.py
    3. Chép khối .env script in ra vào .env của máy bạn, rồi chạy như thường:
        venv/bin/python src/pipeline.py

Link dùng Cloudflare quick tunnel (*.trycloudflare.com): không cần tài khoản và mở được 2 link cùng lúc.
ngrok free chỉ có 1 domain nên không mở được 2 endpoint song song.

Chạy lại script là an toàn: server và tunnel còn sống thì dùng lại, token giữ nguyên (lưu ở /content/logs).
Mọi thứ sống tới khi runtime Colab bị ngắt; khi đó chạy lại script và sửa .env vì link sẽ đổi.

Bảo mật: model_server đòi token (MODEL_SERVER_TOKEN). Ollama không có xác thực — ai biết link đều gọi được LLM,
đừng chia sẻ link và tắt runtime khi dùng xong.
"""
import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

OLLAMA_PORT = 11434
MODEL_PORT = 8001
EMBED_MODEL = "AITeamVN/Vietnamese_Embedding"  # = CONFIG_SERVER trong src/config.py; khác là index lệch vector
RERANK_MODEL = "AITeamVN/Vietnamese_Reranker"
# Cùng phiên bản với requirements.txt để vector trên Colab khớp vector index đã build ở máy bạn.
# Không ghim torch: Colab có sẵn bản CUDA.
PIP_MODEL_SERVER = [
    "fastapi", "uvicorn",
    "llama-index-core==0.14.24", "llama-index-embeddings-huggingface==0.8.0",
    "sentence-transformers==6.0.1", "sentencepiece==0.2.2",
]
CLOUDFLARED = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
LOG_DIR = Path("/content/logs") if Path("/content").exists() else Path.cwd() / "logs"
TOKEN_FILE = LOG_DIR / "model_server_token.txt"


def log(msg: str) -> None:
    print(f"[colab] {msg}", flush=True)


def run(cmd: str) -> None:
    subprocess.run(cmd, shell=True, check=True)


def http(url: str, token: str = "", body: Any = None, timeout: float = 5) -> Any:
    headers = {"Content-Type": "application/json"} | ({"Authorization": f"Bearer {token}"} if token else {})
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def song(url: str, token: str = "") -> bool:
    try:
        http(url, token)
        return True
    except (urllib.error.URLError, OSError, ValueError):
        return False


def cho(dieu_kien: Callable[[], bool], ten: str, giay: int, log_file: Path) -> None:
    """Chờ `dieu_kien()` đúng trong `giay` giây; quá hạn thì in đuôi log và dừng."""
    for _ in range(giay):
        if dieu_kien():
            return
        time.sleep(1)
    if log_file.exists():
        print("\n".join(log_file.read_text(errors="replace").splitlines()[-25:]))
    sys.exit(f"{ten} không lên sau {giay}s — xem log ở {log_file}")


def chay_nen(cmd: list[str], log_file: Path, env: dict[str, str] | None = None) -> None:
    """Tiến trình nền tách khỏi script (start_new_session) để sống sau khi ô Colab chạy xong."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_file, "ab") as f:
        subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         env={**os.environ, **(env or {})}, start_new_session=True)


# ---------- 1. LLM: Ollama ----------
def chay_ollama(model: str) -> None:
    url = f"http://127.0.0.1:{OLLAMA_PORT}"
    if not shutil.which("ollama"):
        log("Cài Ollama (zstd, pciutils cần cho script cài đặt và dò GPU)")
        run("apt-get -qq update && apt-get -qq install -y zstd pciutils lshw >/dev/null")
        run("curl -fsSL https://ollama.com/install.sh | sh")
    if not song(f"{url}/api/tags"):
        log("Khởi động ollama serve")
        log_file = LOG_DIR / "ollama.log"
        chay_nen(["ollama", "serve"], log_file, env={
            "OLLAMA_HOST": f"127.0.0.1:{OLLAMA_PORT}",
            "OLLAMA_KEEP_ALIVE": "-1",  # giữ model trên VRAM, tránh nạp lại giữa các câu hỏi
        })
        cho(lambda: song(f"{url}/api/tags"), "Ollama", 60, log_file)
    co_san = [m["name"] for m in http(f"{url}/api/tags").get("models", [])]
    if model not in co_san and f"{model}:latest" not in co_san:
        log(f"Pull {model} (vài phút)")
        run(f"OLLAMA_HOST=127.0.0.1:{OLLAMA_PORT} ollama pull {model}")
    log(f"Nạp {model} lên GPU")  # để câu hỏi đầu tiên từ máy bạn không bị timeout
    http(f"{url}/api/generate", body={"model": model, "prompt": "", "keep_alive": -1}, timeout=600)
    log(f"Ollama OK tại {url}")


# ---------- 2. Embedding + reranker: src/model_server.py ----------
def tim_model_server() -> Path:
    here = Path(__file__).resolve().parent
    for p in (here / "model_server.py", here.parent / "src" / "model_server.py", Path("/content/model_server.py")):
        if p.exists():
            return p
    sys.exit("Không thấy model_server.py — upload src/model_server.py lên cùng thư mục với script này")


def lay_token() -> str:
    token = os.environ.get("MODEL_SERVER_TOKEN") or (TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else "")
    if not token:
        token = secrets.token_urlsafe(24)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(token)
    return token


def chay_model_server(token: str, rerank: bool) -> None:
    url = f"http://127.0.0.1:{MODEL_PORT}"
    if song(f"{url}/health", token):
        log(f"model_server đã chạy tại {url}")
        return
    log("Cài thư viện cho model_server")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", *PIP_MODEL_SERVER], check=True)
    ms = tim_model_server()
    log(f"Khởi động {ms.name} (lần đầu tải model từ HuggingFace, ~2-3 phút)")
    log_file = LOG_DIR / "model_server.log"
    chay_nen([sys.executable, "-m", "uvicorn", "model_server:app", "--app-dir", str(ms.parent),
              "--host", "127.0.0.1", "--port", str(MODEL_PORT)], log_file, env={
        "EMBED_MODEL": EMBED_MODEL,
        "RERANK_MODEL": RERANK_MODEL if rerank else "",
        "FP16": "1",
        "MODEL_SERVER_TOKEN": token,
    })
    # /health chỉ trả lời sau khi lifespan nạp xong model
    cho(lambda: song(f"{url}/health", token), "model_server", 900, log_file)
    log(f"model_server OK tại {url}: {http(f'{url}/health', token)}")


# ---------- 3. Link công khai: Cloudflare quick tunnel ----------
def cai_cloudflared() -> str:
    exe = shutil.which("cloudflared") or "/usr/local/bin/cloudflared"
    if not Path(exe).exists():
        log("Tải cloudflared")
        run(f"curl -fsSL -o {exe} {CLOUDFLARED} && chmod +x {exe}")
    return exe


def mo_tunnel(ten: str, port: int, kiem_tra: Callable[[str], bool], host_header: bool = False) -> str:
    """Mở tunnel tới 127.0.0.1:port; tunnel cũ (URL ghi trong log) còn dùng được thì giữ nguyên."""
    log_file = LOG_DIR / f"tunnel-{ten}.log"
    tim_url = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def url_trong_log() -> str | None:
        urls = tim_url.findall(log_file.read_text(errors="replace")) if log_file.exists() else []
        return urls[-1] if urls else None

    cu = url_trong_log()
    if cu and kiem_tra(cu):
        log(f"Dùng lại tunnel {ten}: {cu}")
        return cu
    log_file.unlink(missing_ok=True)
    cmd = [cai_cloudflared(), "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"]
    if host_header:
        # Ollama từ chối request mang Host lạ (*.trycloudflare.com) -> ghi đè thành localhost
        cmd += ["--http-host-header", f"localhost:{port}"]
    chay_nen(cmd, log_file)
    cho(lambda: url_trong_log() is not None, f"tunnel {ten}", 60, log_file)
    url = url_trong_log()
    assert url is not None
    # DNS của link mới cần vài giây mới phân giải được
    cho(lambda: kiem_tra(url), f"tunnel {ten} ({url})", 90, log_file)
    return url


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="qwen3:8b", help="LLM Ollama, mặc định = CONFIG_SERVER.llm_model_name")
    ap.add_argument("--khong-rerank", action="store_true", help="không nạp reranker (tiết kiệm ~1GB VRAM)")
    args = ap.parse_args()

    if shutil.which("nvidia-smi"):
        run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader")
    else:
        log("CẢNH BÁO: không thấy GPU — Runtime > Change runtime type > T4 GPU, nếu không sẽ rất chậm")

    token = lay_token()
    chay_ollama(args.model)
    chay_model_server(token, rerank=not args.khong_rerank)

    ollama_url = mo_tunnel("ollama", OLLAMA_PORT, lambda u: song(f"{u}/api/tags"), host_header=True)
    model_url = mo_tunnel("model", MODEL_PORT, lambda u: song(f"{u}/health", token))

    # Kiểm tra qua link công khai, giống cách máy bạn sẽ gọi
    vec = http(f"{model_url}/embed", token, {"texts": ["Điều 9. Thang điểm"], "kind": "text"}, timeout=60)["embeddings"][0]
    log(f"Qua link công khai: embedding OK ({len(vec)} chiều), Ollama có {[m['name'] for m in http(f'{ollama_url}/api/tags', timeout=15)['models']]}")

    print(f"""
=============== Dán vào .env trên máy bạn ===============
RAG_PROFILE=server
OLLAMA_BASE_URL={ollama_url}
MODEL_SERVER_URL={model_url}
MODEL_SERVER_TOKEN={token}
=========================================================
LLM: {args.model} | embedding: {EMBED_MODEL} | reranker: {"tắt" if args.khong_rerank else RERANK_MODEL}
Log: {LOG_DIR}/  — runtime bị ngắt thì chạy lại script và cập nhật 2 link (token giữ nguyên).""")


if __name__ == "__main__":
    main()
