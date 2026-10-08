"""Kiểm thử offline: không cần GPU, không cần Ollama, không tải model.

Chạy: `make test` hoặc `python -m unittest discover -s tests -t . -v`.
Thư mục tạm được tạo trong .tmp/ của repo (một số môi trường không cho ghi /tmp).
"""
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _p in (ROOT / "src", ROOT / "eval", ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


@contextmanager
def tmp_dir():
    """Thư mục tạm nằm trong repo để không phụ thuộc /tmp."""
    base = ROOT / ".tmp"
    base.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(dir=base))
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)
