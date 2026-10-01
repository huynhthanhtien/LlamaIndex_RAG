"""Công cụ quản lý tập trung: ckey.vn, Ollama và embedding server.

Biến môi trường (.env):
    CKEY_API_KEY          API key ckey.vn (trang Profile)
    CKEY_GPU_INSTANCE_ID  Instance ID GPU đã thuê (dùng cho `ckey-gpu-info`)

Usage:
    python3 scripts/manager.py ckey-apis
    python3 scripts/manager.py ckey-gpu-info [--id 12345]
    python3 scripts/manager.py ckey-gpu-list [--gpu rtx50series --sort price_asc --count 5]
    python3 scripts/manager.py ckey-gpu-rent --id NODE --template 12 --password PW --ports 22,11434
    python3 scripts/manager.py ckey-gpu-delete|ckey-gpu-reboot [--id 12345]
    python3 scripts/manager.py ckey-profile | ckey-deposit-info --amount 50000
    python3 scripts/manager.py ckey-deposit-check | ckey-deposit-history
    python3 scripts/manager.py ckey-ai-models | ckey-ai-keys | ckey-ai-usage | ckey-ai-stats
    python3 scripts/manager.py ollama [--model qwen3:8b --prompt "Xin chào"]
    python3 scripts/manager.py embedding-server [--model ... --device cuda --port 8081]

Mở rộng: thêm một method vào `ServiceManager` và đăng ký subcommand trong `build_parser`.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, NoReturn

import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()


class ServiceManager:
    CKEY_URL = "https://ckey.vn"

    # Chỉ các API đọc (GET) — bỏ qua API có thể thay đổi dữ liệu/tốn phí.
    CKEY_READ_ONLY_ENDPOINTS = [
        ("Profile", "/api/profile", {}),
        ("Lịch sử nạp tiền", "/api/deposit-history", {"page": "1", "limit": "5"}),
        # ("Check nạp tiền gần đây", "/api/deposit-check", {"minutes": "1440", "limit": "5"}),
        # ("Danh sách API key AI", "/api/llm/keys", {}),
        # ("Danh sách model AI", "/api/llm/models", {}),
        # ("Thống kê dùng AI", "/api/llm/usage-stats", {}),
        # ("Danh sách proxy tĩnh", "/api/proxy-static/list", {}),
    ]

    def __init__(self, ckey_api_key: str | None = None):
        self.ckey_api_key = ckey_api_key or os.environ.get("CKEY_API_KEY")

    # ---------- ckey.vn ----------

    def _require_ckey_key(self) -> str:
        if not self.ckey_api_key:
            self._die("Thiếu API key. Thêm CKEY_API_KEY vào .env hoặc dùng --key.")
        return self.ckey_api_key

    def _ckey_get(
        self, path: str, params: dict[str, str] | None = None, timeout: float = 15
    ) -> Any:
        query: dict[str, str] = {"key": self._require_ckey_key()}
        if params:
            query.update(params)
        resp = requests.get(f"{self.CKEY_URL}{path}", params=query, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def ckey_check_apis(self) -> None:
        """Gọi thử toàn bộ API chỉ-đọc của ckey.vn."""
        key = self._require_ckey_key()
        for label, path, extra in self.CKEY_READ_ONLY_ENDPOINTS:
            print(f"\n=== {label} ({path}) ===")
            try:
                resp = requests.get(
                    f"{self.CKEY_URL}{path}", params={"key": key, **extra}, timeout=15
                )
                print(f"HTTP {resp.status_code}")
                try:
                    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
                except ValueError:
                    print(resp.text[:500])
            except requests.exceptions.RequestException as e:
                print(f"[LỖI] {e}")

    # ---------- API trả dữ liệu (dùng trong notebook/code) ----------

    def find_gpus(
        self,
        gpu: str = "all",
        continent: str = "All",
        sort: str = "price_asc",
        count: str = "1",
        access: str = "all",
        host_type: str = "all",
    ) -> list[dict[str, Any]]:
        """Tìm GPU khả dụng (/api/getgpu3), trả về danh sách node."""
        data: Any = self._ckey_get(
            "/api/getgpu3",
            {
                "gpu": gpu,
                "continent": continent,
                "sort": sort,
                "count": count,
                "access": access,
                "host_type": host_type,
            },
            timeout=20,
        )
        items: Any = data if isinstance(data, list) else data.get("data", [])
        return items if isinstance(items, list) else []

    def rent_gpu(
        self, node_id: str, template: str, password: str, ports: str, env: str | None = None
    ) -> Any:
        """Thuê GPU (/api/thuegpu3) — TỐN PHÍ, KHÔNG hỏi xác nhận (người gọi tự xác nhận)."""
        params = {"id": node_id, "templates": template, "password": password, "port": ports}
        if env:
            params["env"] = env
        return self._ckey_get("/api/thuegpu3", params, timeout=60)

    def gpu_info(self, instance_id: str) -> Any:
        """Thông tin GPU đã thuê (/api/infogpu3)."""
        return self._ckey_get("/api/infogpu3", {"id": instance_id})

    def gpu_action(self, instance_id: str, option: str) -> Any:
        """delete/reboot GPU (/api/option_gpu3) — KHÔNG hỏi xác nhận."""
        return self._ckey_get(
            "/api/option_gpu3", {"id": instance_id, "option": option}, timeout=30
        )

    def profile(self) -> Any:
        """Thông tin tài khoản và số dư (/api/profile)."""
        return self._ckey_get("/api/profile")

    def ckey_gpu_info(self, instance_id: str | None = None) -> None:
        """Xem thông tin GPU đã thuê (/api/infogpu3)."""
        instance_id = instance_id or os.environ.get("CKEY_GPU_INSTANCE_ID")
        if not instance_id:
            self._die("Thiếu Instance ID. Thêm CKEY_GPU_INSTANCE_ID vào .env hoặc dùng --id.")
        self._print_json(self.gpu_info(instance_id))

    def ckey_gpu_list(
        self,
        gpu: str = "all",
        continent: str = "All",
        sort: str = "price_asc",
        count: str = "1",
        access: str = "all",
        host_type: str = "all",
    ) -> None:
        """Tìm GPU khả dụng để thuê (/api/getgpu3)."""
        items = self.find_gpus(gpu, continent, sort, count, access, host_type)
        print(f"Tìm được {len(items)} GPU:\n")
        for g in items:
            print(
                f"- id={g.get('id')} | {g.get('gpu_name')} | "
                f"CPU: {g.get('cpu')} | RAM: {g.get('ram')} | Giá: {g.get('price')}"
            )

    def ckey_gpu_rent(
        self,
        node_id: str,
        template: str,
        password: str,
        ports: str,
        env: str | None = None,
        yes: bool = False,
    ) -> None:
        """Thuê GPU mới (/api/thuegpu3) — TỐN PHÍ, hỏi xác nhận trước khi gọi."""
        self._confirm(f"Thuê GPU node {node_id} với template '{template}', port {ports}", yes)
        self._print_json(self.rent_gpu(node_id, template, password, ports, env))

    def ckey_gpu_option(self, instance_id: str | None, option: str, yes: bool = False) -> None:
        """Xoá hoặc reboot GPU đã thuê (/api/option_gpu3) — hỏi xác nhận trước khi gọi."""
        instance_id = instance_id or os.environ.get("CKEY_GPU_INSTANCE_ID")
        if not instance_id:
            self._die("Thiếu Instance ID. Thêm CKEY_GPU_INSTANCE_ID vào .env hoặc dùng --id.")
        self._confirm(f"{option.upper()} GPU instance {instance_id}", yes)
        self._print_json(self.gpu_action(instance_id, option))

    def ckey_profile(self) -> None:
        """Thông tin tài khoản và số dư (/api/profile)."""
        self._print_json(self.profile())

    def ckey_deposit_info(self, amount: str) -> None:
        """Thông tin chuyển khoản/QR nạp tiền (/api/deposit-info)."""
        self._print_json(self._ckey_get("/api/deposit-info", {"amount": amount}))

    def ckey_deposit_check(self, minutes: str, limit: str) -> None:
        """Kiểm tra giao dịch nạp gần đây (/api/deposit-check)."""
        self._print_json(self._ckey_get("/api/deposit-check", {"minutes": minutes, "limit": limit}))

    def ckey_deposit_history(self, page: str, limit: str) -> None:
        """Lịch sử nạp tiền có phân trang (/api/deposit-history)."""
        self._print_json(self._ckey_get("/api/deposit-history", {"page": page, "limit": limit}))

    def ckey_ai_models(self) -> None:
        """Danh sách model AI kèm bảng giá (/api/llm/models)."""
        self._print_json(self._ckey_get("/api/llm/models"))

    def ckey_ai_keys(self) -> None:
        """Danh sách API key AI (/api/llm/keys); che phần giữa của key khi in."""
        data: Any = self._ckey_get("/api/llm/keys")
        items: list[dict[str, Any]] = (
            data.get("data", {}).get("items", []) if isinstance(data, dict) else []
        )
        for item in items:
            token = item.get("api_key")
            if isinstance(token, str) and len(token) > 10:
                item["api_key"] = f"{token[:6]}...{token[-4:]}"
        self._print_json(data)

    def ckey_ai_usage(self, **filters: str | None) -> None:
        """Lịch sử dùng AI (/api/llm/usage). filters: page, limit, model, key_id, ai_key."""
        self._print_json(self._ckey_get("/api/llm/usage", self._drop_none(filters)))

    def ckey_ai_stats(self, **filters: str | None) -> None:
        """Thống kê dùng AI (/api/llm/usage-stats). filters: since, key_id, ai_key."""
        self._print_json(self._ckey_get("/api/llm/usage-stats", self._drop_none(filters)))

    # ---------- Ollama ----------

    def ollama_check(self, model: str | None, prompt: str, timeout: float | None) -> None:
        """Kiểm tra version, danh sách model và chat thử trên Ollama server."""
        from src.config import get_config

        cfg = get_config()
        model = model or cfg.llm_model_name
        timeout = timeout or cfg.request_timeout
        base_url = cfg.ollama_base_url.rstrip("/")
        print(f"== Kiểm tra Ollama server: {base_url} (model: {model}) ==\n")

        try:
            resp = requests.get(f"{base_url}/api/version", timeout=10)
            resp.raise_for_status()
            print(f"[OK] /api/version -> {resp.json()}")

            resp = requests.get(f"{base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            print(f"[OK] /api/tags -> {len(models)} model(s): {models}")
            if model in models:
                print(f"[OK] Model '{model}' đã sẵn sàng trên server.")
            else:
                print(
                    f"[CẢNH BÁO] Model '{model}' chưa có trên server. "
                    f"Chạy: OLLAMA_HOST={base_url} ollama pull {model}"
                )

            t0 = time.time()
            resp = requests.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=timeout,
            )
            elapsed = time.time() - t0
            resp.raise_for_status()
            reply = resp.json().get("message", {}).get("content", "")
            print(f"[OK] /api/chat trả lời sau {elapsed:.2f}s:")
            print(f"     {reply[:300]}{'...' if len(reply) > 300 else ''}")
        except requests.exceptions.ConnectionError as e:
            self._die(f"Không kết nối được tới {base_url}: {e}")
        except requests.exceptions.Timeout:
            self._die(f"Hết thời gian chờ ({timeout}s) khi gọi {base_url}.")
        except requests.exceptions.HTTPError as e:
            self._die(f"Server trả về lỗi HTTP: {e}")

        print("\nHoàn tất — Ollama server hoạt động bình thường.")

    # ---------- Embedding server ----------

    def embedding_server(
        self, model_name: str, device: str | None, host: str, port: int
    ) -> None:
        """Expose embedding model qua HTTP, giả lập format API của TEI.

            POST /embed {"inputs": "text" | ["a", "b"]} -> [[float, ...], ...]
            GET  /health
        """
        # Import nặng, chỉ nạp khi thật sự chạy server.
        import torch
        import uvicorn
        from fastapi import FastAPI
        from pydantic import BaseModel
        from sentence_transformers import SentenceTransformer

        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Đang tải model '{model_name}' lên '{device}'...")
        model = SentenceTransformer(model_name, device=device)
        print("Model đã sẵn sàng.")

        class EmbedRequest(BaseModel):
            inputs: str | list[str]

        app = FastAPI()

        @app.get("/health")
        def health():
            return {
                "status": "ok",
                "model": model_name,
                "device": device,
                "dim": model.get_embedding_dimension(),
            }

        @app.post("/embed")
        def embed(req: EmbedRequest):
            texts = [req.inputs] if isinstance(req.inputs, str) else req.inputs
            return model.encode(texts, normalize_embeddings=True).tolist()

        uvicorn.run(app, host=host, port=port)

    # ---------- helpers ----------

    @staticmethod
    def _print_json(data: Any) -> None:
        print(json.dumps(data, indent=2, ensure_ascii=False))

    @staticmethod
    def _drop_none(params: dict[str, str | None]) -> dict[str, str]:
        return {k: v for k, v in params.items() if v is not None}

    @classmethod
    def _confirm(cls, action: str, yes: bool) -> None:
        """Hỏi xác nhận cho thao tác tốn phí/không hoàn tác, trừ khi có --yes."""
        if yes:
            return
        if not sys.stdin.isatty():
            cls._die(f"{action}: cần xác nhận. Chạy trong terminal hoặc thêm --yes.")
        if input(f"{action}. Tiếp tục? [y/N] ").strip().lower() != "y":
            cls._die("Đã huỷ.")

    @staticmethod
    def _die(message: str) -> NoReturn:
        print(f"[LỖI] {message}", file=sys.stderr)
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--key", help="CKEY_API_KEY (mặc định đọc từ .env)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ckey-apis", help="Gọi thử các API chỉ-đọc của ckey.vn")

    p = sub.add_parser("ckey-gpu-info", help="Thông tin GPU đã thuê")
    p.add_argument("--id", help="Ghi đè CKEY_GPU_INSTANCE_ID")

    p = sub.add_parser("ckey-gpu-list", help="Tìm GPU khả dụng để thuê")
    p.add_argument("--gpu", default="all", help="all hoặc tên model, vd rtx50series")
    p.add_argument("--continent", default="All")
    p.add_argument("--sort", default="price_asc", choices=["price_asc", "price_desc"])
    p.add_argument("--count", default="1")
    p.add_argument("--access", default="all", choices=["all", "public"])
    p.add_argument("--host-type", default="all", choices=["all", "community", "datacenter"])

    p = sub.add_parser("ckey-gpu-rent", help="Thuê GPU mới (TỐN PHÍ)")
    p.add_argument("--id", required=True, dest="node_id", help="GPU node ID (từ ckey-gpu-list)")
    p.add_argument(
        "--template",
        required=True,
        help="ID template (vd 12=Open WebUI+Ollama, 15=vLLM, 9=Jupyter) hoặc image namespace/image:tag",
    )
    p.add_argument("--password", required=True)
    p.add_argument("--ports", required=True, help="vd 22,11434 (phải gồm port template yêu cầu)")
    p.add_argument("--env", help="Biến môi trường tuỳ chỉnh, dạng JSON")
    p.add_argument("--yes", action="store_true", help="Bỏ qua bước xác nhận")

    for name, help_text in [
        ("ckey-gpu-delete", "Xoá GPU đã thuê (không hoàn tác)"),
        ("ckey-gpu-reboot", "Reboot GPU đã thuê"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--id", help="Ghi đè CKEY_GPU_INSTANCE_ID")
        p.add_argument("--yes", action="store_true", help="Bỏ qua bước xác nhận")

    sub.add_parser("ckey-profile", help="Thông tin tài khoản và số dư")

    p = sub.add_parser("ckey-deposit-info", help="Thông tin chuyển khoản/QR nạp tiền")
    p.add_argument("--amount", required=True, help="Số tiền (VND)")

    p = sub.add_parser("ckey-deposit-check", help="Giao dịch nạp gần đây")
    p.add_argument("--minutes", default="1440")
    p.add_argument("--limit", default="5")

    p = sub.add_parser("ckey-deposit-history", help="Lịch sử nạp tiền")
    p.add_argument("--page", default="1")
    p.add_argument("--limit", default="5")

    sub.add_parser("ckey-ai-models", help="Model AI và bảng giá")
    sub.add_parser("ckey-ai-keys", help="Danh sách API key AI (key được che)")

    p = sub.add_parser("ckey-ai-usage", help="Lịch sử dùng AI")
    p.add_argument("--page")
    p.add_argument("--limit", help="Tối đa 100")
    p.add_argument("--model")
    p.add_argument("--key-id", dest="key_id")
    p.add_argument("--ai-key", dest="ai_key")

    p = sub.add_parser("ckey-ai-stats", help="Thống kê dùng AI")
    p.add_argument("--since", help="Unix timestamp")
    p.add_argument("--key-id", dest="key_id")
    p.add_argument("--ai-key", dest="ai_key")

    p = sub.add_parser("ollama", help="Kiểm tra kết nối Ollama server")
    p.add_argument("--model")
    p.add_argument("--prompt", default="Chào bạn, bạn là ai?")
    p.add_argument("--timeout", type=float)

    p = sub.add_parser("embedding-server", help="Chạy embedding server (FastAPI)")
    p.add_argument("--model", default="bkai-foundation-models/vietnamese-bi-encoder")
    p.add_argument("--device", help="cuda/cpu (mặc định tự phát hiện)")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8081)

    return parser


def main() -> None:
    args = build_parser().parse_args()
    mgr = ServiceManager(ckey_api_key=args.key)

    match args.command:
        case "ckey-apis":
            mgr.ckey_check_apis()
        case "ckey-gpu-info":
            mgr.ckey_gpu_info(args.id)
        case "ckey-gpu-list":
            mgr.ckey_gpu_list(
                gpu=args.gpu,
                continent=args.continent,
                sort=args.sort,
                count=args.count,
                access=args.access,
                host_type=args.host_type,
            )
        case "ckey-gpu-rent":
            mgr.ckey_gpu_rent(
                args.node_id, args.template, args.password, args.ports, args.env, args.yes
            )
        case "ckey-gpu-delete":
            mgr.ckey_gpu_option(args.id, "delete", args.yes)
        case "ckey-gpu-reboot":
            mgr.ckey_gpu_option(args.id, "reboot", args.yes)
        case "ckey-profile":
            mgr.ckey_profile()
        case "ckey-deposit-info":
            mgr.ckey_deposit_info(args.amount)
        case "ckey-deposit-check":
            mgr.ckey_deposit_check(args.minutes, args.limit)
        case "ckey-deposit-history":
            mgr.ckey_deposit_history(args.page, args.limit)
        case "ckey-ai-models":
            mgr.ckey_ai_models()
        case "ckey-ai-keys":
            mgr.ckey_ai_keys()
        case "ckey-ai-usage":
            mgr.ckey_ai_usage(
                page=args.page,
                limit=args.limit,
                model=args.model,
                key_id=args.key_id,
                ai_key=args.ai_key,
            )
        case "ckey-ai-stats":
            mgr.ckey_ai_stats(since=args.since, key_id=args.key_id, ai_key=args.ai_key)
        case "ollama":
            mgr.ollama_check(args.model, args.prompt, args.timeout)
        case "embedding-server":
            mgr.embedding_server(args.model, args.device, args.host, args.port)
        case _:
            raise ValueError(f"Lệnh không hợp lệ: {args.command}")


if __name__ == "__main__":
    main()
