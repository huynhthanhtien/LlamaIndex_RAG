# SGU RAG (LlamaIndex)

Hệ thống hỏi-đáp RAG (Retrieval-Augmented Generation) cho các văn bản quy chế đào tạo của Trường Đại học Sài Gòn (SGU), xây dựng trên [LlamaIndex](https://www.llamaindex.ai/) với LLM chạy qua [Ollama](https://ollama.com/) (local, server GPU hoặc Google Colab).

## Báo cáo GG docs
```bash
https://docs.google.com/document/d/1TQZR0Qk_NSef59e24KFiL4X1CC3u3WQZq2tp6z1sjok/edit?usp=sharing
```

## Chạy LLM + embedding trên colab
```bash
!wget -q -O setup_server_v2.sh https://raw.githubusercontent.com/huynhthanhtien/LlamaIndex_RAG/main/scripts/setup_server_v2.sh
!bash setup_server_v2.sh
```

Script chạy trên Colab (T4 GPU): cài + chạy Ollama, dựng model server (embedding + reranker), mở URL công khai qua Cloudflare quick tunnel và in ra các dòng cần chép vào `.env` ở máy local (`OLLAMA_BASE_URL`, `MODEL_SERVER_URL`, ...). Sau đó index, retriever, query engine, đánh giá vẫn chạy ở máy local như bình thường. Notebook `notebooks/demo.ipynb` chứa sẵn hai lệnh trên.

## Trạng thái hiện tại: 20 văn bản Đào tạo của SGU (118 Node, profile server)

Index gồm Quy chế đào tạo SGU 2021 + QĐ sửa đổi 3183/2025 + 4 quy định, cộng 6 văn bản của đợt 1 (thi, phúc khảo, thủ tục, cố vấn học tập), 5 văn bản của đợt 2 (quy đổi chứng chỉ tiếng Anh, bảng chép tay từ bản scan) và 3 văn bản của đợt 3 (quy trình phúc khảo, tiết học, chuẩn đầu ra). Corpus là cả thư mục `data/processed/01_quy_che_dao_tao` (kể cả thư mục con); danh sách văn bản trong `src/corpus.py`, dict `SGU_HIEU_LUC`:

| Tiền tố file | Tên hiển thị (dùng khi embedding và trích nguồn) |
|---|---|
| `25_quy-che-dao-tao` | Quy chế đào tạo trình độ đại học SGU 2021 |
| `QD 3183.2025` | QĐ 3183/2025 sửa đổi Quy chế đào tạo SGU 2021 |
| `8_QD810` | QĐ 810 về học cùng lúc hai chương trình |
| `2022-2375` | QĐ 2375/2022 về chuyển chương trình, ngành đào tạo |
| `22_quy-dinh-ve-khoi-luong` | Quy định khối lượng đào tạo hệ chính quy theo tín chỉ |
| `Quydinh150tc` | Quy định số tín chỉ tối thiểu kỹ sư CNTT (khóa 2017 trở đi) |
| `3260-QD-Hoan-thi` | QĐ 3260/2025 về việc hoãn thi |
| `QD898` | QĐ 898/2025 ban hành Quy định tổ chức thi học kì |
| `CV_3248` | Quy định 3248/2018 giải quyết thắc mắc, khiếu nại kết quả học tập |
| `QuyDinh_CapBangDiem` | Quy định cấp bảng điểm học tập (2018) |
| `QuyDinh_CapBanSao` | Quy định cấp bản sao văn bằng, chứng chỉ (2018) |
| `QĐ_CVHT` | Quy chế công tác cố vấn học tập (QĐ 367/2019) |
| `202111_2366` | TB 2366/2021 tiếng Anh không chuyên, quy đổi chứng chỉ (khóa tuyển sinh 2021 trở về trước) |
| `30_TB so 2451` | TB 2451/2024 bổ sung chứng chỉ quy đổi tiếng Anh (khóa tuyển sinh 2021 trở về trước) |
| `CV2626` | QyĐ 2626/2022 tiếng Anh không chuyên, quy đổi chứng chỉ (khóa tuyển sinh 2022, 2023) |
| `29_2101` | QyĐ 2101/2024 tiếng Anh không chuyên, quy đổi chứng chỉ (khóa tuyển sinh từ 2024) |
| `TB so 2567` | TB 2567/2024 bổ sung chứng chỉ PTE Academic quy đổi tiếng Anh (các khóa) |
| `HD-Quy trinh phuc khao` | HD 1181/2022 thực hiện quy trình phúc khảo bài thi kết thúc học phần |
| `02.-Tiethoc_phonghoc` | Quy định thời gian tiết học, ca học và mã phòng học |
| `TB_ChuanDauRa_2020` | TB 536/2020 áp dụng chuẩn đầu ra ngoại ngữ xét công nhận tốt nghiệp |

Văn bản hết hiệu lực / văn bản của Bộ không nạp vào index: đã đo, chúng lấn át QC SGU 2021 khi truy hồi. `data/raw/` còn nhiều nhóm tài liệu khác (công tác sinh viên, chương trình đào tạo, khóa luận, biểu mẫu) chưa đưa vào index — xem `docs/ke_hoach_them_du_lieu_dao_tao.md`.

**Chuẩn bị dữ liệu** (chạy một lần cho mỗi thư mục `data/raw/...`):
`scripts/extract_to_md.py` (PDF/DOCX → Markdown thô `data/ocr/`) → sửa tay nếu cần → `scripts/clean_md.py` (→ Markdown sạch có heading `data/processed/`).

**Pipeline**: `processed_loader` (mỗi Điều / mục sửa đổi một Node, gắn tên văn bản) → `index_builder` → `retriever` (vector, tuỳ chọn hybrid BM25 + rerank) → `query_engine` (Ollama, trích nguồn) → `pipeline` (terminal) / `app/app.py` (Gradio).

## Kiến trúc

- **Trích văn bản**: `scripts/extract_to_md.py` lấy cả text layer (`pdftotext`) lẫn OCR (`pytesseract` + `pdf2image`, `tessdata_best` tiếng Việt) cho từng trang rồi giữ bản tốt hơn; `.docx` đọc thẳng XML.
- **Làm sạch + cấu trúc**: `scripts/clean_md.py` dựng heading `#` văn bản / `##` Chương / `###` Điều / `####` mục sửa đổi, ghi báo cáo kiểm tra `_bao_cao_kiem_tra.md`.
- **Embedding**: mô hình embedding tiếng Việt (`bkai-foundation-models/vietnamese-bi-encoder` ở profile `local`, `AITeamVN/Vietnamese_Embedding` ở profile `server`).
- **LLM**: Qwen3 qua Ollama (`qwen3:4b` local, `qwen3:8b` server), `temperature=0`, `seed=42`.
- **Reranker** (tuỳ chọn, mặc định tắt): `AITeamVN/Vietnamese_Reranker` ở profile `server`.
- **Hybrid search** (tuỳ chọn): BM25 thuần Python (`src/bm25.py`, tách từ bỏ dấu) trộn với vector bằng `QueryFusionRetriever`.
- **Model server** (tuỳ chọn): `src/model_server.py` nạp embedding + reranker lên GPU một lần, client gọi qua HTTP (`MODEL_SERVER_URL`).
- **Giao diện**: [Gradio](https://www.gradio.app/) (`app/app.py`) — hỏi-đáp + xem các trích đoạn được truy hồi.

Cấu hình cho từng profile (`local` / `server`) được định nghĩa tập trung tại `src/config.py`.

## Cài đặt

### Yêu cầu

- Python 3.10+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) kèm gói ngôn ngữ tiếng Việt (`tesseract-ocr-vie`) và [Poppler](https://poppler.freedesktop.org/) (`pdftotext`, `pdf2image`) — chỉ cần khi trích văn bản từ PDF
- [Ollama](https://ollama.com/) chạy local / trên server / trên Colab với model tương ứng đã `ollama pull` (xem `scripts/pull_models.sh`)

### Thiết lập môi trường

```bash
python3 -m venv venv
source venv/bin/activate.fish   # hoặc venv/bin/activate với bash/zsh
pip install -r requirements.txt
cp .env.example .env            # rồi chỉnh giá trị
```

Các biến trong `.env` (không commit):

```bash
RAG_PROFILE=local                        # "local" hoặc "server"
OLLAMA_BASE_URL=http://localhost:11434   # profile "server" đọc biến này
# MODEL_SERVER_URL=http://localhost:8001 # (tuỳ chọn) dùng model server thay vì nạp model tại chỗ
# MODEL_SERVER_TOKEN=                    # trùng với token đặt khi chạy server
```

Biến tuỳ chỉnh thêm: `RAG_EMBED_DEVICE=cpu` (máy không GPU), `RAG_TEMPERATURE`, `RAG_SEED`, `RAG_THINKING=1` (bật chế độ suy luận của qwen3: đúng hơn khi tra bảng số, chậm ~4 lần).

Kiểm tra cấu hình đang dùng:

```bash
python3 src/config.py
```

## Chạy thử

Chạy từ thư mục gốc của repo (đường dẫn trong code là tương đối so với thư mục gốc), cần Ollama đang chạy và đã pull model trong `src/config.py`:

```bash
RAG_PROFILE=server venv/bin/python src/index_builder.py            # build/load Index (thêm --rebuild để build lại)
RAG_PROFILE=server venv/bin/python src/retriever.py "câu hỏi"      # thử truy hồi (thêm --rerank)
RAG_PROFILE=server venv/bin/python src/query_engine.py             # thử hỏi-đáp 1 câu
RAG_PROFILE=server venv/bin/python src/pipeline.py                 # hỏi-đáp qua terminal, gõ 'thoat' để dừng
RAG_PROFILE=server venv/bin/python app/app.py                      # giao diện Gradio http://127.0.0.1:7860 (thêm --share)
```

- Văn bản nạp vào index: `corpus_dir`, `corpus_files` và tên hiển thị `ten_van_ban` lấy mặc định từ `src/corpus.py` (`CORPUS_DIR`, dict `SGU_HIEU_LUC`).
- Index lưu ở `storage/<profile>/<thư mục corpus>` kèm `corpus.json`; tự build lại khi văn bản, tên hiển thị, logic cắt Node hoặc model embedding đổi.
- Rerank: `use_rerank` trong `src/config.py`, mặc định **tắt** — trên corpus hiện tại rerank làm giảm Recall@1 (xem `make eval`).
- Hybrid BM25 + vector: `use_hybrid` trong `src/config.py` (mặc định tắt), chạy thử bằng `eval/evaluate.py --cau-hinh hybrid`.
- Trả lời tất định: `temperature=0`, `seed=42` trong `make_llm()`; đổi qua `RAG_TEMPERATURE`, `RAG_SEED`.
- Máy không có GPU: `RAG_EMBED_DEVICE=cpu` hoặc để `resolve_device()` tự hạ cấp về CPU.
- Model server tự chạy trên máy local: `venv/bin/uvicorn model_server:app --app-dir src --port 8001`.

### Trích văn bản mới vào corpus

```bash
python scripts/extract_to_md.py data/raw/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc   # → data/ocr/ (thêm --force để ghi đè)
python scripts/clean_md.py data/ocr/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc         # → data/processed/
```

`data/ocr/` (tầng 1) là nơi duy nhất sửa tay (bảng trong bản scan: chép tay thành bảng Markdown `| … |`, `clean_md.py` giữ nguyên khối bảng); `data/processed/` (tầng 2) luôn sinh lại từ tầng 1. Sau đó thêm tiền tố file vào `SGU_HIEU_LUC` trong `src/corpus.py` (mỗi tiền tố phải khớp đúng một file trong cả cây thư mục) — index tự build lại ở lần chạy sau. Thêm câu hỏi dev cho văn bản mới (ví dụ `eval/dev_questions_dot1.json`, `dev_questions_dot2.json`; nhiều nhãn đúng ngăn bởi `;`, nhãn `"<tiền tố file>"` hoặc `"<tiền tố file>|<Điều>"`) để `make eval` đo được.

## Kiểm thử và đánh giá

```bash
make test           # 71 kiểm thử: 59 chạy offline (không cần GPU/Ollama), 2 ca biên lọc phiên bản chưa xử lý (expected failure),
                    # 10 của test_llm.py bị skip nếu không đặt RAG_TEST_LLM=1; CI chạy lệnh này
make test-llm       # kiểm thử có LLM: gọi Ollama thật trong .env (RAG_PROFILE=server)
make eval           # truy hồi 6 cấu hình vector/rerank/loc/rerank+loc/hybrid/hybrid+rerank+loc: Recall@k, MRR, nDCG, CI bootstrap, McNemar
make baseline       # baseline BM25 / không xếp hạng
make eval-answers   # chấm câu trả lời bằng evaluator của LlamaIndex (Faithfulness, Relevancy — LLM tự chấm) + từ chối đúng/sai
```

Tập kiểm chứng chỉ chạy **một lần**, sau khi đóng băng: `eval/dong_bang.py tao` (ghi `eval/results/dong-bang.json`: sha256 mã nguồn, corpus, cấu hình chốt, luật chấm, file câu hỏi; code phải đã commit) → commit manifest → `eval/evaluate.py --tap-kiem-chung` (từ chối chạy nếu lệch manifest hoặc đã chạy). Trước đó: `eval/kiem_tra_trung.py [--embedding]` (câu kiểm chứng gần trùng dev → `trung-lap.md`) và `eval/bao_phu.py` (Node/văn bản mỗi bộ chạm tới → `bao-phu.md`). Câu trả lời sinh (`eval/tra_loi_dev.py`) ghi outcome từng câu (`loi` / `chua_cham`, chấm tay theo `docs/rubric-cham-tra-loi.md`, đếm lại bằng `--tong-hop`), evidence và chạy bổ sung câu lỗi bằng `--chi-cau-loi`.

Hoặc gọi trực tiếp: `RAG_PROFILE=server venv/bin/python eval/evaluate.py [--cau-hinh vector,rerank,hybrid] [--doi-chieu-thu-vien]`, `eval/baselines.py`, `eval/evaluate_answers.py --che-do ca-hai`. Kết quả (JSON + Markdown) ghi vào `eval/results/`, kèm tóm tắt cấu hình (`RAGConfig.mo_ta()`) để tái lập.

## Cấu trúc thư mục

```
.
├── app/
│   └── app.py              # Giao diện Gradio: hỏi-đáp + xem trích đoạn truy hồi
├── data/
│   ├── raw/                # Văn bản gốc PDF/DOCX theo nhóm + metadata_manifest.csv
│   ├── ocr/                # Tầng 1: Markdown thô (sửa tay ở đây)
│   └── processed/          # Tầng 2: Markdown sạch có heading, sẵn sàng để index
├── docs/                   # Báo cáo phân tích, đề xuất cải tiến, kế hoạch, phân công
│   └── giao_trinh/         # Tài liệu cơ sở lý thuyết RAG (HTML)
├── eval/
│   ├── evaluate.py         # truy hồi: Recall@k, MRR, nDCG, CI bootstrap, McNemar
│   ├── baselines.py        # baseline BM25 / không xếp hạng
│   ├── evaluate_answers.py # chấm câu trả lời bằng evaluator của LlamaIndex
│   ├── metrics.py          # độ đo + kiểm định thống kê
│   ├── run_batch_cau_hoi.py, compare_results.py  # chạy hàng loạt câu hỏi, so sánh kết quả
│   ├── cau_hoi_danh_gia.json, test_questions_0*.json  # bộ câu hỏi
│   └── results/            # Kết quả đánh giá (JSON + Markdown)
├── notebooks/              # build_check_processed, chay_thu_pipeline, chay_cau_hoi01, ckey_gpu_pipeline, demo (Colab)
├── report/                 # Báo cáo LaTeX (main.tex, chapters/, appendices/) — `make report`
├── scripts/
│   ├── extract_to_md.py    # PDF/DOCX -> Markdown (text layer + OCR)
│   ├── clean_md.py         # Markdown thô -> Markdown sạch có cấu trúc
│   ├── reorganize_raw.py   # tái cấu trúc data/raw + manifest
│   ├── setup_server_v2.sh  # dựng Ollama + model server trên Colab/máy GPU (tunnel công khai)
│   ├── colab_server.py     # phương án Python cho Colab
│   ├── pull_models.sh      # pull model theo profile
│   ├── manager.py          # quản lý ckey.vn GPU / Ollama / embedding server
│   └── check_model_memory.py, test_ocr.py, hello_world.py
├── src/
│   ├── config.py           # Cấu hình RAG: profile, model, tham số truy hồi
│   ├── corpus.py           # Thư mục corpus + danh sách văn bản nạp vào index
│   ├── processed_loader.py # Markdown tầng 2 -> Node
│   ├── index_builder.py    # build/load index theo profile, kiểm tra fingerprint
│   ├── bm25.py             # BM25 thuần Python (không cần gói ngoài) cho hybrid search
│   ├── retriever.py        # vector + hybrid BM25 + rerank
│   ├── query_engine.py     # prompt + LLM (temperature=0, seed) + trích nguồn
│   ├── pipeline.py         # hỏi-đáp qua terminal
│   ├── model_server.py     # (tuỳ chọn) server embedding + reranker, chạy riêng trên GPU
│   ├── remote_models.py    # client gọi model server
│   └── ingestion.py, node_parser.py  # pipeline cũ đọc PDF trực tiếp (giữ để tham khảo)
├── storage/<profile>/...   # Vector index đã build (không commit)
├── tests/                  # kiểm thử offline (unittest) + test_llm.py (cần Ollama)
├── Makefile                # make test / test-llm / eval / baseline / eval-answers / report
└── requirements.txt        # đã ghim phiên bản
```

## Trạng thái dự án

Sáu giai đoạn của pipeline đã chạy được trên 20 văn bản Đào tạo: `scripts/extract_to_md.py` +
`scripts/clean_md.py` (dữ liệu) → `src/processed_loader.py` (Node) → `src/index_builder.py` (index) →
`src/retriever.py` (vector, tuỳ chọn hybrid BM25) → `src/query_engine.py` (LLM + trích nguồn) →
`eval/` (truy hồi, baseline, chấm câu trả lời). Xem `docs/bao_cao_cai_tien_rag.md` và các báo cáo MD trong `docs/`.

### Giới hạn đã biết (chưa triển khai, để ở Chương 5 báo cáo sau)

- Rerank có sẵn nhưng mặc định tắt (xem trên); profile `local` không có reranker
- Profile `local` (`vietnamese-bi-encoder`) chỉ nhận 256 token và cần tách từ — Recall thấp hơn hẳn profile `server`
- Chưa nhớ ngữ cảnh hội thoại (câu hỏi nối tiếp), chưa có Router giữa nhiều nhóm văn bản, chưa lọc theo hiệu lực văn bản
- Bộ đánh giá có đáp án chuẩn còn nhỏ
- Giao diện Gradio mới ở mức chạy thử

## Tài liệu tham khảo
```bash
https://learn.microsoft.com/en-us/aspnet/mvc/overview/older-versions/hands-on-labs/aspnet-mvc-4-entity-framework-scaffolding-and-migrations?fbclid=IwY2xjawU2p9dleHRuA2FlbQIxMQBwZG9mAXNydGMGYXBwX2lkEDIyMjAzOTE3ODgyMDA4OTIAAR5jGCWpCstzuv-IKmqc3X_ytbYl8mNtIrIJ5eK3C79lj0SrbEI1trXUr9V2yg_aem_QKHRO6FdJjWXUVYEtRp6TA
```

[Tài liệu LlamaIndex(AI gen) ](https://htmlpreview.github.io/?https://github.com/huynhthanhtien/LlamaIndex_RAG/blob/main/docs/giao_trinh/co_so_ly_thuyet_rag.html)

[Tổng quan LlamaIndex](https://htmlpreview.github.io/?https://github.com/huynhthanhtien/LlamaIndex_RAG/blob/main/docs/llamaindex_tong_quan.html)

## Giấy phép

Chưa xác định.
