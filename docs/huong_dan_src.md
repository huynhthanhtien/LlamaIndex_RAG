# Hướng dẫn mã nguồn `src/`

Tài liệu mô tả luồng dữ liệu, vai trò từng module, cấu hình và cách chạy hệ thống hỏi-đáp RAG quy chế đào tạo SGU.
Mọi lệnh chạy từ **thư mục gốc repo** (đường dẫn trong code tính từ thư mục gốc).

## 1. Luồng tổng thể

```
data/raw (PDF, .docx)
   │  scripts/extract_to_md.py      text layer / OCR Tesseract, chọn bản tốt hơn
   ▼
data/ocr (tầng 1 — Markdown thô, nơi DUY NHẤT sửa tay)
   │  scripts/clean_md.py           làm sạch + dựng heading # / ## / ### / ####
   ▼
data/processed (tầng 2 — Markdown sạch, luôn sinh lại từ tầng 1)
   │  src/processed_loader.py       mỗi Điều / mục sửa đổi -> 1 TextNode + metadata
   ▼
src/index_builder.py                embedding -> VectorStoreIndex, lưu storage/<profile>/<corpus>
   │
   ▼
src/retriever.py                    top-k theo vector (+ rerank tuỳ chọn)
   │
   ▼
src/query_engine.py                 prompt tiếng Việt + LLM Ollama + trích nguồn
   │
   ▼
src/pipeline.py                     hỏi-đáp qua terminal
```

Khi hỏi một câu có hai lần gọi model:

1. **Embedding** câu hỏi (trong `retriever`) để tìm Node gần nhất.
2. **LLM** sinh câu trả lời từ các Node đó (trong `query_engine`, chế độ `compact`, streaming).

Traceback có `response_synthesizers` / `llms/ollama` là lỗi ở bước 2 (LLM). Traceback có `remote_models.py` (`/embed`, `/rerank`) hoặc `HuggingFaceEmbedding` là lỗi ở bước 1.

## 2. Các module

| File | Vai trò | Chạy trực tiếp |
|---|---|---|
| `corpus.py` | **Nội dung đầu vào**: `PROCESSED_ROOT`, `CORPUS_DIR`, dict `SGU_HIEU_LUC` (tiền tố tên file → tên hiển thị) | — |
| `config.py` | `RAGConfig` + 2 profile `local` / `server`, chọn qua `RAG_PROFILE`; `resolve_device()` tự hạ cấp về CPU khi không có CUDA; `mo_ta()` để ghi kèm kết quả đo | `python src/config.py` in config đang dùng |
| `processed_loader.py` | Đọc Markdown tầng 2 → `TextNode` | in số Node theo file / phần |
| `index_builder.py` | Chọn embedding (local hoặc model server), build/load index, kiểm tra fingerprint | `--rebuild` để build lại |
| `retriever.py` | Retriever top-k, tuỳ chọn hybrid BM25 (`--hybrid`), ngưỡng tương đồng, reranker (local hoặc remote), `search()`, `node_label()` | `"câu hỏi" [--rerank] [--hybrid]` |
| `query_engine.py` | Prompt `QA_PROMPT`, LLM Ollama, `ask()` in câu trả lời + nguồn | hỏi thử 1 câu cố định |
| `pipeline.py` | Vòng lặp hỏi-đáp terminal, gõ `thoat` để dừng | ✓ |
| `bm25.py` | BM25 Okapi thuần Python + `BM25Retriever` (BaseRetriever) cho hybrid search | tự chạy thử với 2 Node mẫu |
| `remote_models.py` | Client HTTP: `RemoteEmbedding`, `RemoteRerank`, `check_server` | — |
| `model_server.py` | Server FastAPI giữ embedding + reranker trên GPU (`/health`, `/embed`, `/rerank`). **Độc lập**, chép riêng lên máy GPU được | qua `uvicorn` |
| `ingestion.py`, `node_parser.py` | **Bản cũ** (OCR trực tiếp + cắt theo regex "Điều X") — pipeline hiện tại không dùng, giữ lại để đối chiếu trong báo cáo | — |
| `ingestion.py` (đầu vào OCR) | `scripts/extract_to_md.py` → `scripts/clean_md.py` (tầng 1 → tầng 2) | — |

### 2.1 `corpus.py` — thêm / bớt văn bản

```python
SGU_HIEU_LUC = {
    "25_quy-che-dao-tao": "Quy chế đào tạo trình độ đại học SGU 2021",
    ...
}
```

- Khoá là **tiền tố tên file** `.md` trong `CORPUS_DIR`. File bắt đầu bằng `_` (báo cáo của `clean_md.py`) luôn bị bỏ qua.
- Giá trị là tên hiển thị. Tên này được ghép vào metadata `van_ban`, nên được dùng **cả khi embedding lẫn khi trích nguồn**.
- Tiền tố không khớp file nào sẽ báo `FileNotFoundError` liệt kê các tiền tố thiếu.
- Sửa danh sách hoặc đổi tên hiển thị thì index tự build lại ở lần chạy sau (xem 2.4).

### 2.2 `config.py` — profile

| | `local` | `server` |
|---|---|---|
| Embedding | `bkai-foundation-models/vietnamese-bi-encoder` (256 token) | `AITeamVN/Vietnamese_Embedding`, fp16 |
| LLM (Ollama) | `qwen3:4b` tại `localhost:11434` | `qwen3:8b` tại `OLLAMA_BASE_URL` |
| Reranker | không có | `AITeamVN/Vietnamese_Reranker` (nhưng `use_rerank=False`) |

Tham số chung: `similarity_top_k=10`, `response_mode="compact"`, `streaming=True`, `request_timeout=180`.
Index lưu ở `storage/<profile>/<đường dẫn corpus sau data/processed>`.

Biến môi trường (`.env`):

| Biến | Ý nghĩa |
|---|---|
| `RAG_PROFILE` | `local` (mặc định) hoặc `server` |
| `OLLAMA_BASE_URL` | Chỉ profile `server` đọc. Thiếu `http://` thì tự thêm |
| `MODEL_SERVER_URL` | Có giá trị thì embedding/rerank gọi model server thay vì nạp lên GPU local. **Phải có `http://`** |
| `MODEL_SERVER_TOKEN` | Tuỳ chọn; trùng với token đặt khi chạy server |
| `RAG_EMBED_DEVICE` | Ép thiết bị embedding/reranker (`cpu` khi máy không có GPU) |
| `RAG_TEMPERATURE`, `RAG_SEED` | Ghi đè độ ngẫu nhiên của LLM (mặc định `0.0` và `42`) |

### 2.3 `processed_loader.py` — cắt Node

Heading do `clean_md.py` dựng: `#` văn bản → `##` Chương → `###` Điều → `####` mục sửa đổi (QĐ 3183).

- Mỗi `###` / `####` là một Node. Nội dung nằm ngay dưới `#` / `##` chỉ thành Node khi dài ≥ `MIN_TU_NOI_DUNG` (30 từ), dành cho văn bản không chia Điều.
- Node dài hơn `MAX_TU` (1024 từ) được cắt bằng `SentenceSplitter`, metadata thêm `phan_doan`.
- Metadata: `van_ban`, `chuong`, `dieu`, `sua_doi_dieu`, `phan` (`chinh` / `sua_doi` / `ban_hanh` / `noi_dung`), `file`, `file_goc`, `url`, và `nguon_trich`.
- **Metadata rỗng bị loại bỏ** khỏi Node (trước đây Node nào cũng mang `chuong: `, `dieu: `, `sua_doi_dieu: ` rỗng gây nhiễu vector).
- **Chỉ `nguon_trich`** ("Điều 9 — Quy chế ... 2021") được đưa vào embedding; `file`, `file_goc`, `url`, `phan` không vào prompt (`KHONG_LLM`). Nhờ vậy "Điều 9" của hai văn bản khác nhau vẫn cho vector khác nhau mà vector không bị pha tạp bởi khóa kỹ thuật.
- `LOADER_VERSION`, `MAX_TU`, `MIN_TU_NOI_DUNG` được ghi vào fingerprint của index.

### 2.4 `index_builder.py` — khi nào build lại

`corpus.json` lưu cạnh index gồm: tên model embedding, `corpus_dir`, `loader` (`phien_ban`, `max_tu`, `min_tu_noi_dung`), và sha256 + tên hiển thị của từng file.
Fingerprint khác thì tự build lại — kể cả khi chỉ đổi `MAX_TU`/`MIN_TU_NOI_DUNG`. Khi sửa **logic** cắt trong `processed_loader.py` mà không đổi `LOADER_VERSION` thì vẫn phải chạy `--rebuild`.

### 2.5 `retriever.py` / `query_engine.py`

- `get_postprocessors()` trả `[]` khi `use_rerank=False`. Rerank đã đo làm giảm Recall@1 trên corpus hiện tại.
- Reranker local nạp trên CPU, ép fp16 rồi mới đưa lên GPU, để không tràn card 4 GB.
- `QA_PROMPT` buộc trả lời bằng tiếng Việt, chỉ dựa trên trích đoạn, nêu tên văn bản + Điều, và ưu tiên nội dung đã sửa đổi.
- LLM dùng `thinking=False` (tắt chế độ suy nghĩ của Qwen3), `context_window=8192`.

## 3. Ba cách chạy

### A. Toàn bộ trên máy local (`RAG_PROFILE=local`)

```bash
ollama serve & ollama pull qwen3:4b
RAG_PROFILE=local venv/bin/python src/pipeline.py
```

### B. Embedding trên GPU local, LLM trên server (`.env` hiện tại)

```
RAG_PROFILE=server
OLLAMA_BASE_URL=<IP>:<cổng map tới 11434>
```

Embedding `AITeamVN/Vietnamese_Embedding` fp16 chiếm khoảng 1.1 GB VRAM. Tiến trình chỉ hiện trong `nvidia-smi` khi chương trình đang chạy.

### C. Cả embedding và LLM trên server

Trên server (container image Ollama), chỉ cần một file:

```bash
curl -fsSLO https://raw.githubusercontent.com/huynhthanhtien/LlamaIndex_RAG/<branch>/scripts/setup_server.sh
bash setup_server.sh          # MODEL_SERVER_TOKEN=xxx bash setup_server.sh nếu cần xác thực
```

Script tự: bật Ollama (0.0.0.0) và pull LLM; tạo venv và cài thư viện; ghi `model_server.py`; chạy uvicorn cổng 8001; thử `/embed`, `/rerank`; in các dòng cần chép vào `.env`:

```
RAG_PROFILE=server
OLLAMA_BASE_URL=http://<IP>:<cổng map tới 11434>
MODEL_SERVER_URL=http://<IP>:<cổng map tới 8001>
```

Khi khởi động, client gọi `/health` và báo lỗi nếu server chạy embedding hoặc reranker **khác** profile. Index đã build không cần build lại vì cùng tên model.

## 3.5. Kiểm thử và đánh giá

| Lệnh | Việc |
|---|---|
| `make test` | 26 kiểm thử offline (`unittest`) cho `processed_loader`, `bm25`, `metrics`, `config`, corpus thật |
| `make eval` | Đo truy hồi 4 cấu hình (vector / +rerank / hybrid / hybrid+rerank), ghi `eval/results/truy-hoi.{json,md}` |
| `make baseline` | Baseline BM25 và "không xếp hạng" — sàn so sánh cho báo cáo |
| `make eval-answers` | Chấm câu trả lời bằng `FaithfulnessEvaluator`, `RelevancyEvaluator`, `CorrectnessEvaluator` của LlamaIndex (cần Ollama) |
| `make report` | Build PDF báo cáo |

Chỉ số truy hồi do `eval/metrics.py` tính: Recall@k, MRR, nDCG, khoảng tin cậy bootstrap, kiểm định McNemar
cho so sánh cặp. `eval/evaluate.py --kiem-chung` chấm chéo bằng `RetrieverEvaluator` của thư viện.

## 4. Lệnh thường dùng

```bash
RAG_PROFILE=server venv/bin/python src/processed_loader.py         # đếm Node theo file
RAG_PROFILE=server venv/bin/python src/index_builder.py [--rebuild]
RAG_PROFILE=server venv/bin/python src/retriever.py "câu hỏi" [--rerank]
RAG_PROFILE=server venv/bin/python src/query_engine.py
RAG_PROFILE=server venv/bin/python eval/evaluate.py [--rerank]     # Recall@k, MRR theo (văn bản, Điều)
RAG_PROFILE=server venv/bin/python src/pipeline.py
```

Thêm văn bản mới: `extract_to_md.py <thư mục raw>` → sửa tay ở `data/ocr` → `clean_md.py <thư mục ocr>` → thêm tiền tố vào `SGU_HIEU_LUC` trong `src/corpus.py` → chạy lại (index tự build lại).

## 5. Lỗi thường gặp

| Triệu chứng | Nguyên nhân / cách xử lý |
|---|---|
| `httpx.ConnectError: [Errno 111] Connection refused` trong `llms/ollama` | Ollama tại `OLLAMA_BASE_URL` không chạy hoặc sai cổng. Kiểm tra bằng `curl http://<IP>:<cổng>/api/tags` |
| `Không kết nối được model server ...` | Model server chưa chạy, hoặc `MODEL_SERVER_URL` thiếu `http://` / sai cổng |
| `Server đang chạy embedding/reranker ..., config cần ...` | Server nạp model khác profile. Lưu ý: reranker vẫn được kiểm tra dù `use_rerank=False` |
| `401 Sai hoặc thiếu token` | Server có đặt `MODEL_SERVER_TOKEN` nhưng `.env` local thiếu hoặc sai |
| `corpus_files không khớp file nào` | Tiền tố trong `SGU_HIEU_LUC` không khớp file `.md` nào trong `CORPUS_DIR` |
| `Không thấy data/processed/...` | Chưa chạy `extract_to_md.py` → `clean_md.py`, hoặc không chạy từ thư mục gốc repo |
| Sửa logic `processed_loader.py` mà kết quả không đổi | Fingerprint theo dõi `LOADER_VERSION` và các ngưỡng, nhưng không theo dõi toàn bộ mã: đổi cách cắt thì tăng `LOADER_VERSION` hoặc chạy `index_builder.py --rebuild` |
