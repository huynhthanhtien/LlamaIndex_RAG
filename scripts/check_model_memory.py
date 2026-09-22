"""Do RAM/VRAM khi load va chay mot model embedding hoac reranker.

Usage:
    python3 scripts/check_model_memory.py <repo_id> [--type embedding|reranker] [--device cpu|cuda]

Vi du:
    python3 scripts/check_model_memory.py AITeamVN/Vietnamese_Embedding --device cuda
    python3 scripts/check_model_memory.py AITeamVN/Vietnamese_Reranker --type reranker --device cuda
"""

import argparse
import re

import torch


def get_rss_mb() -> float:
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmRSS:"):
                kb = int(re.search(r"\d+", line).group())
                return kb / 1024
    return -1.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_id")
    parser.add_argument("--type", choices=["embedding", "reranker"], default="embedding")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    rss_before = get_rss_mb()
    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    if args.type == "embedding":
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(args.repo_id, device=args.device)
        rss_after_load = get_rss_mb()
        model.encode(["Đây là một câu ví dụ tiếng Việt để kiểm tra bộ nhớ."])
    else:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(args.repo_id, device=args.device)
        rss_after_load = get_rss_mb()
        model.predict([("câu hỏi mẫu", "đoạn văn bản mẫu để rerank")])

    rss_after_run = get_rss_mb()

    print(f"\n=== {args.repo_id} ({args.type}, device={args.device}) ===")
    print(f"RAM truoc khi load:     {rss_before:8.1f} MB")
    print(f"RAM sau khi load model: {rss_after_load:8.1f} MB  (+{rss_after_load - rss_before:.1f} MB)")
    print(f"RAM sau khi chay 1 lan: {rss_after_run:8.1f} MB  (+{rss_after_run - rss_after_load:.1f} MB)")

    if args.device == "cuda":
        vram_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
        print(f"VRAM peak (GPU):        {vram_mb:8.1f} MB")


if __name__ == "__main__":
    main()
