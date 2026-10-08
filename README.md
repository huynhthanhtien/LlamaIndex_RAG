# SGU RAG (LlamaIndex)

Hệ thống hỏi-đáp RAG (Retrieval-Augmented Generation) cho các văn bản quy chế đào tạo của Trường Đại học Sài Gòn (SGU), xây dựng trên [LlamaIndex](https://www.llamaindex.ai/) với LLM chạy local qua [Ollama](https://ollama.com/).

## Trạng thái hiện tại: 6 văn bản quy chế SGU đang áp dụng (Quy chế 2021 + QĐ sửa đổi 3183/2025 + 4 quy định)

Chuẩn bị dữ liệu (chạy một lần cho mỗi thư mục `data/raw/...`):
`scripts/extract_to_md.py` (PDF → Markdown thô `data/ocr/`) → sửa tay nếu cần → `scripts/clean_md.py` (→ Markdown sạch có heading `data/processed/`).

Pipeline: `processed_loader` (mỗi Điều / mục sửa đổi một Node, gắn tên văn bản) → `index_builder` → `retriever` (+ rerank tuỳ chọn) → `query_engine` (Ollama) → `pipeline` (hỏi-đáp terminal).

## Chạy thử

Chạy từ thư mục gốc của repo (đường dẫn trong code là tương đối so với thư mục gốc), cần Ollama đang chạy và đã pull model trong `src/config.py`:

```bash
RAG_PROFILE=server venv/bin/python src/index_builder.py            # build/load Index (thêm --rebuild để build lại)
RAG_PROFILE=server venv/bin/python src/retriever.py "câu hỏi"      # thử truy hồi (thêm --rerank)
RAG_PROFILE=server venv/bin/python src/query_engine.py             # thử hỏi-đáp 1 câu
RAG_PROFILE=server venv/bin/python eval/evaluate.py [--rerank]     # Recall@k, MRR, nDCG, CI bootstrap, 2 bộ câu hỏi
RAG_PROFILE=server venv/bin/python eval/baselines.py              # baseline BM25 / không xếp hạng
make test                                                          # 26 kiểm thử offline (không cần GPU/Ollama)
RAG_PROFILE=server venv/bin/python src/pipeline.py                 # hỏi-đáp qua terminal, gõ 'thoat' để dừng
```

- Văn bản nạp vào index: `corpus_dir`, `corpus_files` và tên hiển thị `ten_van_ban` lấy mặc định từ `src/corpus.py` (`CORPUS_DIR`, dict `SGU_HIEU_LUC`).
- Index lưu ở `storage/<profile>/<thư mục corpus>` kèm `corpus.json`; tự build lại khi văn bản, tên hiển thị hoặc model embedding đổi.
- Rerank: `use_rerank` trong `src/config.py`, mặc định **tắt** — trên corpus hiện tại rerank làm giảm Recall@1 (xem `make eval`).
- Hybrid BM25 + vector: `use_hybrid` trong `src/config.py` (mặc định tắt), chạy thử bằng `eval/evaluate.py --cau-hinh hybrid`.
- Trả lời tất định: `temperature=0`, `seed=42` trong `make_llm()`; đổi qua `RAG_TEMPERATURE`, `RAG_SEED`.
- Máy không có GPU: `RAG_EMBED_DEVICE=cpu` hoặc để `resolve_device()` tự hạ cấp về CPU.
- Notebook `notebooks/build_check_processed.ipynb`: build + đo RAM/VRAM + so sánh có/không rerank, gọi đúng code trên.

## Giới hạn đã biết (chưa triển khai, để ở Chương 5 báo cáo sau)

- Rerank có sẵn nhưng mặc định tắt (xem trên); profile `local` không có reranker
- Profile `local` (`vietnamese-bi-encoder`) chỉ nhận 256 token và cần tách từ — Recall thấp hơn hẳn profile `server`
- Chưa nhớ ngữ cảnh hội thoại (câu hỏi nối tiếp), chưa có Router giữa nhiều nhóm văn bản
- Giao diện Gradio mới ở mức chạy thử: `RAG_PROFILE=server venv/bin/python app/app.py` (http://127.0.0.1:7860)

## Kiến trúc

- **OCR**: chuyển PDF quy chế thành văn bản Markdown bằng `pytesseract` + `pdf2image` (hỗ trợ tiếng Việt).
- **Embedding**: mô hình embedding tiếng Việt (`bkai-foundation-models/vietnamese-bi-encoder` khi chạy local, `AITeamVN/Vietnamese_Embedding` khi chạy server/GPU).
- **LLM**: mô hình Qwen3 chạy qua Ollama (`qwen3:4b` local, `qwen3:8b` server).
- **Reranker** (tuỳ chọn): `AITeamVN/Vietnamese_Reranker` khi chạy ở profile server.
- **Giao diện**: dự kiến dùng [Gradio](https://www.gradio.app/) (`app/`).

Cấu hình cho từng profile (`local` / `server`) được định nghĩa tập trung tại `src/config.py`.

## Cấu trúc thư mục

```
.
├── app/                # Giao diện người dùng (Gradio) — đang xây dựng
├── data/
│   ├── raw/            # PDF gốc (không commit, xem .gitignore)
│   ├── ocr/            # Kết quả OCR dạng Markdown
│   └── processed/      # Dữ liệu đã tiền xử lý, sẵn sàng để index
├── docs/
│   └── giao_trinh/     # Tài liệu tham khảo, giáo trình
├── eval/
│   ├── evaluate.py      # truy hồi: Recall@k, MRR, nDCG, CI bootstrap, McNemar
│   ├── baselines.py     # baseline BM25 / không xếp hạng
│   ├── evaluate_answers.py  # chấm câu trả lời bằng evaluator của LlamaIndex
│   ├── metrics.py       # độ đo + kiểm định thống kê
│   └── results/         # Kết quả đánh giá (JSON + Markdown)
├── notebooks/          # Notebook thử nghiệm
├── scripts/            # Script tiện ích (OCR, thử nghiệm nhanh...)
├── src/
│   ├── config.py           # Cấu hình RAG: profile, model, tham số truy hồi, văn bản nạp vào index
│   ├── bm25.py             # BM25 thuần Python (không cần gói ngoài) cho hybrid search
│   ├── processed_loader.py # Markdown tầng 2 -> Node
│   ├── index_builder.py    # build/load index theo profile
│   ├── retriever.py        # tìm kiếm + rerank
│   ├── query_engine.py     # prompt + LLM (temperature=0, seed) + trích nguồn
│   └── model_server.py     # (tuỳ chọn) server embedding + reranker, chạy riêng trên GPU
├── storage/
│   └── <profile>/...       # Vector index đã build (không commit)
├── tests/              # kiểm thử offline (unittest)
├── Makefile            # make test / eval / baseline / report
└── requirements.txt    # đã ghim phiên bản
```

## Cài đặt

### Yêu cầu

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) đã cài đặt hệ thống, kèm gói ngôn ngữ tiếng Việt (`tesseract-ocr-vie`)
- [Poppler](https://poppler.freedesktop.org/) (cần cho `pdf2image`)
- [Ollama](https://ollama.com/) đã cài đặt và chạy local (hoặc trên server) với các model tương ứng đã `ollama pull`

### Thiết lập môi trường

```bash
python3 -m venv venv
source venv/bin/activate.fish   # hoặc venv/bin/activate với bash/zsh
pip install -r requirements.txt
```

Tạo file `.env` ở thư mục gốc (không commit) nếu cần tuỳ chỉnh, ví dụ:

```bash
RAG_PROFILE=local            # "local" hoặc "server"
OLLAMA_BASE_URL=http://localhost:11434
```

## Sử dụng

### 1. OCR văn bản PDF

```bash
python3 scripts/test_ocr.py data/raw/<ten-file>.pdf
```

Kết quả được lưu dưới dạng Markdown trong `data/ocr/`.

### 2. Kiểm tra cấu hình

```bash
python3 src/config.py
```

In ra profile đang dùng (`local`/`server`) và các thông số tương ứng.

## Trạng thái dự án

Sáu giai đoạn của pipeline đã chạy được trên 6 văn bản quy chế đang áp dụng: `scripts/extract_to_md.py` +
`scripts/clean_md.py` (dữ liệu) → `src/processed_loader.py` (Node) → `src/index_builder.py` (index) →
`src/retriever.py` (vector, tuỳ chọn hybrid BM25) → `src/query_engine.py` (LLM + trích nguồn) →
`eval/` (truy hồi, baseline, chấm câu trả lời). Phần chưa làm: router theo nhóm văn bản, lọc theo hiệu lực,
bộ đánh giá có đáp án chuẩn đủ lớn. Xem `docs/bao_cao_cai_tien_rag.md` và báo cáo MD trong `docs/`.

## Giấy phép

Chưa xác định.
