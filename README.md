# SGU RAG (LlamaIndex)

Hệ thống hỏi-đáp RAG (Retrieval-Augmented Generation) cho các văn bản quy chế đào tạo của Trường Đại học Sài Gòn (SGU), xây dựng trên [LlamaIndex](https://www.llamaindex.ai/) với LLM chạy local qua [Ollama](https://ollama.com/).

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
│   └── results/        # Kết quả đánh giá hệ thống RAG
├── notebooks/          # Notebook thử nghiệm
├── scripts/            # Script tiện ích (OCR, thử nghiệm nhanh...)
├── src/
│   └── config.py        # Cấu hình RAG (embedding, LLM, retriever...)
├── storage/
│   └── vector_index/    # Vector index đã build (không commit)
└── requirements.txt
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

Dự án đang trong giai đoạn xây dựng ban đầu: pipeline OCR đã hoạt động, các bước index hoá và pipeline truy vấn/RAG hoàn chỉnh đang được phát triển tiếp.

## Giấy phép

Chưa xác định.
