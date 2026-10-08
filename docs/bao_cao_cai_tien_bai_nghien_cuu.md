# Báo cáo cải tiến bài nghiên cứu công nghệ LlamaIndex

> **Nhánh:** `nghien-cuu-llamaindex-cai-tien` (tạo từ `GUI`, giữ nguyên các thay đổi WIP có sẵn)
> **Ngày:** 2026-10-05 · **Chưa commit, chưa `git add`** theo yêu cầu.
> **Phạm vi:** toàn bộ repo — lõi RAG, bộ đánh giá, kiểm thử, hạ tầng, tài liệu và báo cáo LaTeX.

---

## 1. Tóm tắt những gì đã làm

| # | Việc | Kết quả |
|---|---|---|
| 1 | Đồng bộ báo cáo LaTeX với mã nguồn thật | Chương 1–5 viết lại phần lệch; pipeline cũ (`ingestion.py`, `node_parser.py`) không còn bị mô tả như pipeline thật |
| 2 | Sửa lõi RAG | `temperature=0` + `seed`, tự hạ cấp CPU khi không có CUDA, metadata Node sạch, chỉ một trường được embedding |
| 3 | Thêm hybrid BM25 + vector | Viết `src/bm25.py` thuần Python (không cần cài thêm gói), ghép bằng `QueryFusionRetriever` |
| 4 | Nâng cấp bộ đánh giá | `RetrieverEvaluator` của LlamaIndex để kiểm chứng chéo, khoảng tin cậy bootstrap, nDCG, kiểm định McNemar, baseline, chấm câu trả lời bằng evaluator của thư viện |
| 5 | Đo lại toàn bộ trên corpus thật | 6 cấu hình truy hồi + 2 baseline, số liệu mới thay cho số liệu cũ trong Chương 5 |
| 6 | Kiểm thử + CI + ghim phiên bản | 26 kiểm thử offline (`make test`), GitHub Actions, `requirements.txt` ghim đúng phiên bản |
| 7 | Thêm danh mục tài liệu tham khảo | 19 mục BibTeX, trích dẫn trong Chương 1, 2, 4, 5 (trước đây báo cáo **không có một `\cite` nào**) |
| 8 | Vá các lỗi phát hiện trong lúc làm | Bug `QueryFusionRetriever` đòi `Settings.llm`, off-by-one của `p95`, fingerprint không theo dõi loader |

---

## 2. Số liệu đo lại (thay số cũ ở Chương 5)

Môi trường: profile `server` (`AITeamVN/Vietnamese_Embedding`, 1024 chiều), **CPU** (máy chạy lại không có driver NVIDIA),
corpus 6 văn bản / 54 Node. Sinh lại bằng `make eval` và `make baseline`.

| Bộ câu hỏi | Cấu hình | R@1 (CI 95%) | R@3 | MRR | nDCG@1 | ms/câu |
|---|---|---|---|---|---|---|
| 01 (31 câu) | vector (mặc định) | 81% [68–94] | 100% | 0,892 | 0,806 | 165 |
| 01 | + rerank | 81% [65–94] | 100% | 0,892 | 0,806 | 8 487 |
| 01 | hybrid (RRF, trọng số bằng) | 77% [61–90] | 94% | 0,866 | 0,774 | 155 |
| 01 | hybrid + rerank | 81% [65–94] | 100% | 0,892 | 0,806 | 8 193 |
| 01 | hybrid ưu tiên vector 3:1 | **84%** [71–97] | 100% | **0,914** | **0,839** | 148 |
| 02 (10 câu) | vector (mặc định) | **90%** [70–100] | 90% | **0,910** | **0,900** | 149 |
| 02 | + rerank | 60% [30–90] | 100% | 0,783 | 0,600 | 7 854 |
| 02 | hybrid (RRF, trọng số bằng) | 60% [30–90] | 90% | 0,717 | 0,600 | 166 |
| 02 | hybrid + rerank | 60% [30–90] | 90% | 0,750 | 0,600 | 8 811 |
| 02 | hybrid ưu tiên vector 3:1 | 80% [50–100] | 90% | 0,850 | 0,800 | 137 |
| 01 | **baseline** BM25 | 58% [42–74] | 84% | 0,727 | — | 0,2 |
| 01 | **baseline** không xếp hạng | 0% | 0% | 0,053 | — | 0,05 |
| 02 | **baseline** BM25 | 40% [10–70] | 60% | 0,537 | — | 0,3 |
| 02 | **baseline** không xếp hạng | 0% | 0% | 0,020 | — | 0,05 |

**Kiểm chứng chéo bằng thư viện** (`--kiem-chung`): `RetrieverEvaluator` cho `mrr` = 0,892 (bộ 01) và 0,910 (bộ 02),
trùng khớp cách đo tự viết; `hit_rate` = 1,000.

**Kiểm định McNemar (R@1):** vector vs BM25 bộ 01: 9/2, p = 0,065; bộ 02: 5/0, p = 0,062; vector vs hybrid ưu tiên
vector bộ 01: 0/1, p = 1,000 → chênh lệch nhỏ nằm trong nhiễu, đã ghi rõ trong phần hạn chế.

**Ba kết luận rút ra:** (1) embedding tiếng Việt + cắt theo Điều là yếu tố quyết định (81%/100% so với BM25 58%/84%);
(2) rerank không giúp trên kho 54 Node và làm R@1 bộ 02 tụt 90%→60%, chậm ~50× trên CPU → giữ mặc định tắt;
(3) hybrid RRF trọng số bằng *làm giảm* chất lượng, nhưng biến thể `relative_score` 3:1 cho kết quả tốt nhất ở bộ 01
→ **cách trộn quan trọng hơn việc có trộn hay không**, và phải đo trước khi bật.

Artifact sinh ra (đã ghi vào repo, không commit):
`eval/results/truy-hoi.json|md`, `truy-hoi-rerank.json|md`, `truy-hoi-hybrid.json|md`,
`truy-hoi-hybrid-w.json|md`, `baseline.json|md`.

---

## 3. Bảng tổng hợp file

| File | Loại | Việc đã làm |
|---|---|---|
| `src/config.py` | sửa | `resolve_device()`, `temperature`, `seed`, `similarity_cutoff`, cụm tham số hybrid, `mo_ta()` |
| `src/processed_loader.py` | sửa | loại metadata rỗng, thêm `nguon_trich`, chỉ embed một trường, `LOADER_VERSION`, `thong_ke()` |
| `src/bm25.py` | **mới** | BM25 Okapi + `BM25Retriever` (BaseRetriever), tách từ bỏ dấu |
| `src/retriever.py` | sửa | hybrid qua `QueryFusionRetriever`, ngưỡng tương đồng, `resolve_device`, `search()` nhận retriever |
| `src/query_engine.py` | sửa | `temperature=0` + `seed`, prompt chống bịa chặt hơn (trích nguyên văn, cấm tự quy đổi) |
| `src/index_builder.py` | sửa | fingerprint gồm phiên bản loader + ngưỡng cắt, dùng `resolve_device` |
| `eval/metrics.py` | **mới** | Recall@k, MRR, nDCG, bootstrap CI, McNemar, p95 |
| `eval/evaluate.py` | sửa | nhiều cấu hình, CI, nDCG, JSON + Markdown, kiểm chứng bằng `RetrieverEvaluator` |
| `eval/baselines.py` | **mới** | baseline BM25 và "không xếp hạng" |
| `eval/evaluate_answers.py` | **mới** | Faithfulness / Relevancy / Correctness + tách từ chối đúng–sai + chế độ closed-book |
| `eval/cau_hoi_danh_gia.json` | **mới** | 13 câu có đáp án chuẩn + nhãn `pham_vi` |
| `tests/` (5 file) | **mới** | 26 kiểm thử offline |
| `Makefile` | **mới** | `test`, `eval`, `baseline`, `eval-answers`, `report`, `clean` |
| `pyproject.toml` | **mới** | cấu hình pytest/ruff |
| `.github/workflows/ci.yml` | **mới** | CI chạy kiểm thử offline |
| `requirements.txt` | sửa | ghim đúng phiên bản, bổ sung `httpx`, `ollama` còn thiếu |
| `.gitignore` | sửa | thêm `.tmp/` |
| `app/app.py` | sửa | disclaimer pháp lý + ghi log câu hỏi thật ra `eval/results/questions_log.jsonl` |
| `README.md` | sửa | trạng thái dự án, lệnh mới, cấu trúc thư mục |
| `docs/huong_dan_src.md` | sửa | thêm `bm25.py`, mục kiểm thử/đánh giá, sửa mô tả fingerprint |
| `report/main.tex` | sửa | bật `\printbibliography` vào mục lục |
| `report/config/preamble.tex` | sửa | `\DeclareLanguageMapping{vietnamese}{english}` để biblatex hiện đúng chuỗi tiếng Anh |
| `report/references.bib` | sửa | 19 mục tài liệu tham khảo (trước đây rỗng) |
| `report/chapters/01..05` | sửa | đồng bộ với code, thêm trích dẫn, thêm mục "điểm ma sát với LlamaIndex", thay số liệu mới |

---

## 4. Chi tiết theo từng file

### 4.1 `src/config.py`
- **Vấn đề:** hai profile đặt cứng `embed_device="cuda"` → máy không có GPU (và CI) lỗi ngay khi nạp model;
  LLM không có `temperature` nên câu trả lời đổi giữa các lần hỏi; không có tham số cho ngưỡng tương đồng và hybrid.
- **Đã sửa:** thêm `resolve_device()` (import `torch` bên trong hàm, chỉ hạ cấp khi thật sự cần);
  thêm `temperature=0.0`, `seed=42`, `similarity_cutoff`, `use_hybrid`, `bm25_top_k`, `bm25_k1`, `bm25_b`,
  `fusion_mode`, `vector_weight`, `bm25_weight`; thêm ghi đè qua `RAG_EMBED_DEVICE`, `RAG_SEED`, `RAG_TEMPERATURE`;
  thêm `mo_ta()` trả về bản tóm tắt cấu hình để ghi kèm mọi kết quả đo.
- **Kiểm chứng:** `RAG_PROFILE=server RAG_EMBED_DEVICE=cpu venv/bin/python src/config.py` in ra JSON cấu hình;
  `tests/test_corpus.py::TestConfig` kiểm tra khoá và `temperature`.

### 4.2 `src/processed_loader.py`
- **Vấn đề:** mọi Node đều mang `chuong: `, `dieu: `, `sua_doi_dieu: ` **rỗng**; LlamaIndex ghép metadata vào văn bản
  trước khi embedding nên vector bị nhiễu; không có cách ghi lại "logic cắt đã đổi" cho fingerprint.
- **Đã sửa:** lọc bỏ mọi metadata rỗng; sinh thêm `nguon_trich` dạng "Điều 9 — Quy chế ... 2021";
  `excluded_embed_metadata_keys` chỉ để lại đúng `nguon_trich`; nhận thêm `so_hieu`, `ngay_ban_hanh`, `tinh_trang`,
  `nhom` từ front matter nếu có; thêm `LOADER_VERSION` và hàm `thong_ke()`.
- **Kiểm chứng:** `tests/test_processed_loader.py` (7 test) khoá lại toàn bộ hành vi;
  `python src/processed_loader.py` in ra "nguon_trich: ..." là nội dung duy nhất được embed.

### 4.3 `src/bm25.py` (mới)
- **Vấn đề:** câu hỏi quy chế chứa ký hiệu/con số mà embedding nắm kém ("B+", "Điều 10", "150 tín chỉ");
  `BM25Retriever` chính thức không có trong `llama-index-core` (nằm ở package riêng) nên không dùng được ngay.
- **Đã làm:** BM25 Okapi (k1=1,5; b=0,75) + `BM25Retriever` kế thừa `BaseRetriever`; tách từ **bỏ dấu** để khớp câu hỏi
  gõ thiếu dấu; hỗ trợ bigram tuỳ chọn; trả về rỗng khi không token nào khớp (tránh đưa Node nhiễu vào prompt).
- **Kiểm chứng:** `tests/test_bm25.py` (6 test) + `python src/bm25.py` in kết quả cho 3 câu hỏi mẫu.

### 4.4 `src/retriever.py`
- **Vấn đề:** chỉ có vector top-k; ngưỡng tương đồng chưa có; chưa có hybrid; reranker không tự hạ cấp CPU.
- **Đã sửa:** `get_retriever()` trả `QueryFusionRetriever` khi `use_hybrid`; `get_postprocessors()` thêm
  `SimilarityPostprocessor` và **tự bỏ qua ngưỡng khi đang hybrid** (điểm RRF khác thang cosine) kèm log cảnh báo;
  `search()` nhận sẵn `retriever`/`postprocessors` để vòng lặp đánh giá không nạp lại model; dùng `resolve_device`.
- **Bug thật gặp phải:** `QueryFusionRetriever.__init__` gọi `Settings.llm` khi không được truyền `llm`, mà mặc định là
  OpenAI → `ImportError: llama-index-llms-openai` dù chỉ định tìm kiếm. Đã xử lý bằng cách truyền thẳng đối tượng
  `Ollama` (với `num_queries=1` nó không bao giờ được gọi) và ghi lại vào bảng "điểm ma sát" của Chương 4.

### 4.5 `src/query_engine.py`
- **Đã sửa:** `make_llm()` truyền `temperature=cfg.temperature` và `additional_kwargs={"seed": cfg.seed}` — sửa trực tiếp
  lỗi "câu trả lời không ổn định" đã ghi trong báo cáo; `QA_PROMPT` thêm hai ràng buộc nhắm đúng lỗi đã đo:
  trích nguyên văn câu quy định trước khi kết luận, và không tự quy đổi thang điểm/đổi đơn vị.

### 4.6 `src/index_builder.py`
- **Vấn đề:** fingerprint chỉ gồm model + nội dung file, nên sửa cách cắt Node mà quên `--rebuild` là dùng index cũ
  (đã ghi thành "lỗi thường gặp" trong tài liệu).
- **Đã sửa:** fingerprint thêm khối `loader` (`phien_ban`, `max_tu`, `min_tu_noi_dung`); dùng `resolve_device()`.

### 4.7 `eval/metrics.py` (mới)
Recall@k, MRR, nDCG@k, `bootstrap_ci` (2 000 lần, seed cố định → tất định), `mcnemar` chính xác bằng `math.comb`
(không cần scipy), `p95`. **Kiểm chứng:** `tests/test_metrics.py` (7 test).

### 4.8 `eval/evaluate.py`
- **Vấn đề:** chỉ có Recall@k/MRR, một cấu hình, không CI, không kiểm định, không lưu kết quả, luật chấm dùng
  `m["dieu"]` nên sẽ `KeyError` với metadata đã lọc rỗng.
- **Đã sửa:** nhiều cấu hình qua `--cau-hinh`; in và ghi JSON/Markdown; luật chấm dùng `.get()`;
  thêm `--kiem-chung` chấm chéo bằng `RetrieverEvaluator`; thêm `so_sanh_cap()` chạy McNemar.

### 4.9 `eval/baselines.py` (mới)
Baseline BM25 và "không xếp hạng" (trả Node theo thứ tự docstore). Đây là thứ bản báo cáo trước **hoàn toàn thiếu**:
không có baseline thì không chứng minh được thiết kế mang lại gì.

### 4.10 `eval/evaluate_answers.py` (mới)
Chấm câu trả lời bằng `FaithfulnessEvaluator`, `RelevancyEvaluator`, `CorrectnessEvaluator` chạy qua `BatchEvalRunner`;
thêm chế độ `closed-book` làm mốc so RAG/không RAG; tách **từ chối đúng** và **từ chối sai**.
Kiểm tra kết nối Ollama trước khi chạy và thoát với thông báo rõ ràng nếu không có.
**Chưa chạy được trong môi trường này vì không có Ollama** — đã ghi rõ trong báo cáo LaTeX.

### 4.11 `tests/` (mới) và hạ tầng
- `tests/__init__.py` (đặt `sys.path` + thư mục tạm trong `.tmp/` để không phụ thuộc `/tmp`),
  `test_processed_loader.py`, `test_bm25.py`, `test_metrics.py`, `test_corpus.py` — **26 test, chạy 0,03 giây,
  không cần GPU, không cần Ollama, không tải model**.
- `Makefile` (dùng `.RECIPEPREFIX` để không phụ thuộc tab), `pyproject.toml`, `.github/workflows/ci.yml`.
- `requirements.txt` ghim đúng phiên bản đo được và bổ sung `httpx`, `ollama` (trước đây `app/app.py` dùng hai gói này
  nhưng không khai báo, chỉ chạy được nhờ phụ thuộc bắc cầu).

### 4.12 `app/app.py`
Thêm cảnh báo "câu trả lời không có giá trị pháp lý, hãy đối chiếu trích đoạn" và ghi log mọi câu hỏi thật
(profile, top-k, rerank, nguồn, câu trả lời) ra `eval/results/questions_log.jsonl` để làm nguồn mở rộng bộ đánh giá.
*(File này đã có thay đổi WIP từ trước; phần trên là phần thêm của lần này.)*

### 4.13 Báo cáo LaTeX
- **Chương 1:** thêm mục tiêu về kiểm thử/đánh giá; viết lại phần "Phạm vi" (6 văn bản, 54 Node, Gradio đã có,
  phần nào chưa làm) và thêm đoạn "những gì đã sửa so với bản trước"; nêu cách tái lập bằng `make`.
- **Chương 2:** thêm trích dẫn cho RAG, bi-encoder, MTEB, chunking/lost-in-the-middle, DPR, BM25, rerank, OCR, Ollama/Qwen3;
  thêm mục con **"Đánh giá câu trả lời"** (faithfulness/relevancy/correctness, RAGAS, LLM-as-a-judge).
- **Chương 3:** ghim phiên bản trong bảng thư viện; cập nhật cây thư mục; sửa phần "hai profile dùng chung thư mục index"
  và "`corpus_sources` trỏ file không tồn tại"; cập nhật trạng thái fp16; thêm Makefile/CI; cập nhật bảng 6 giai đoạn.
- **Chương 4:** viết lại giai đoạn 1–2 theo pipeline thật (`extract_to_md` → `clean_md` → `processed_loader`),
  giữ phần phân tích regex cũ như "bản cũ + lý do chuyển"; thêm mục 4.6 **"Điểm ma sát với LlamaIndex"** (8 dòng)
  và cập nhật số liệu Node/index.
- **Chương 5:** viết lại bằng số liệu mới, có CI/nDCG/McNemar/baseline/kiểm chứng chéo; giữ bảng chấm tay 56 câu
  và ghi rõ đó là số liệu phiên chạy trước; cập nhật hạn chế và hướng phát triển (đánh dấu việc đã xong).
- `references.bib`: 19 mục; `main.tex`: bật in tài liệu tham khảo và đưa vào mục lục;
  `preamble.tex`: ánh xạ ngôn ngữ biblatex sang tiếng Anh (biblatex không hỗ trợ tiếng Việt → trước đó in ra
  "andothers", "inNeurIPS").

---

## 5. Đã kiểm chứng bằng cách nào

| Kiểm chứng | Kết quả |
|---|---|
| `make test` | 26 test, OK, 0,03 s |
| `python -m compileall src` | OK |
| `python src/processed_loader.py` | 54 Node / 6 văn bản, metadata sạch |
| `python src/bm25.py` | xếp hạng đúng cho "B+", câu hỏi không dấu, và rỗng khi không khớp |
| `eval/evaluate.py --cau-hinh vector --kiem-chung` | MRR trùng khớp với `RetrieverEvaluator` |
| `eval/evaluate.py` (6 cấu hình) | Số ở mục 2 |
| `eval/baselines.py` | Số ở mục 2 |
| `latexmk -pdf main.tex` | **48 trang, không lỗi**, 19 mục tài liệu tham khảo, 0 cảnh báo "untranslated" |

---

## 6. Việc chưa làm được (và lý do)

1. **Chấm câu trả lời tự động** — cần Ollama; máy chạy lại không có (`curl localhost:11434` không trả lời).
   Chạy `make eval-answers` trên máy có LLM là xong.
2. **Số liệu trên GPU** — máy không có driver NVIDIA; mọi phép đo dùng CPU, thời gian tuyệt đối lớn hơn GPU.
   Chỉ số chất lượng không bị ảnh hưởng (fp32 trên CPU so với fp16 trên GPU chỉ khác ở mức làm tròn).
3. **`csquotes`** — biblatex khuyến nghị gói này nhưng máy không cài; chỉ sinh cảnh báo, không ảnh hưởng nội dung.
4. **Xoá `src/ingestion.py` / `src/node_parser.py`** — giữ lại để đối chiếu trong Chương 4; nếu muốn dọn thì chuyển
   sang `legacy/` và sửa một dòng trong `docs/huong_dan_src.md`.

---

## 7. Cách tái lập

```bash
git checkout nghien-cuu-llamaindex-cai-tien      # nhánh chứa toàn bộ thay đổi (chưa commit)
make test                                        # 26 kiểm thử offline
make eval                                        # bảng truy hồi 4 cấu hình + kiểm chứng chéo
make baseline                                    # baseline BM25 / không xếp hạng
make eval-answers                                # cần Ollama
make report                                      # build PDF (XeLaTeX + biber)
```

Ghi chú: các file `notebooks/*.ipynb`, `scripts/setup_server.sh`, `eval/compare_results.py`,
`eval/run_batch_cau_hoi.py`, `eval/results/cau-hoi01*.md` đã có thay đổi **từ trước** trên nhánh `GUI`,
lần này không sửa thêm.
