# Phân tích cơ hội cải tiến (từ mã nguồn hiện tại) và kỹ thuật nâng cao khả dụng

> **Ngày:** 2026-10-05 · **Chỉ phân tích — không sửa file mã nguồn nào.**
> **Nguồn:** đọc trực tiếp mã nguồn hiện tại (2 348 dòng `src/` + `eval/` + `app/` + `tests/`) và **8 tài liệu MD** trong `docs/`;
> toàn bộ API LlamaIndex nêu dưới đây **đã kiểm tra bằng `importlib`** trên đúng bản đã cài (`llama-index-core==0.14.24`).

---

## 1. Đã đọc những gì

| Tài liệu | Dùng cho phần nào |
|---|---|
| [`bao_cao_phan_tich_yeu_cau.md`](bao_cao_phan_tich_yeu_cau.md) §7.3–7.8 | **Danh mục kỹ thuật nâng cao A1–A5, B1–B8, C1–C4, D1–D3, E1–E3, F1–F3** + §7.9 "không nên làm" + §7.10 bốn tổ hợp đề xuất |
| [`bao_cao_cai_tien_rag.md`](bao_cao_cai_tien_rag.md) §3 | K1–K12 (ưu tiên 1/2/3) + 3 đợt bổ sung tài liệu |
| [`bao_cao_mo_rong_corpus.md`](bao_cao_mo_rong_corpus.md) §5–6 | Phương án P1–P4, 4 cách cắt cho văn bản không có "Điều" (A/B/C/D), định dạng front matter + metadata |
| [`phan_loai_tai_lieu_va_huong_giai_quyet.md`](phan_loai_tai_lieu_va_huong_giai_quyet.md) | Lớp A–G tài liệu, 5 cặp xung đột phiên bản, lộ trình 4 đợt |
| [`de_xuat_code_cai_tien_pipeline.md`](de_xuat_code_cai_tien_pipeline.md) | ĐX-1…ĐX-9 (code đề xuất, chưa áp dụng) |
| [`task-0.md`](task-0.md), [`kha-task-1.md`](kha-task-1.md) | 14 tầng dựng `ingestion.py` / `node_parser.py` — dùng làm chất liệu "bản chất công nghệ" cho Chương 4 |
| [`huong_dan_src.md`](huong_dan_src.md), [`bao_cao_cai_tien_bai_nghien_cuu.md`](bao_cao_cai_tien_bai_nghien_cuu.md) | Trạng thái module + việc đã làm ở lượt trước |

**Mã nguồn đã đọc:** `src/{config,corpus,processed_loader,bm25,index_builder,retriever,query_engine,remote_models,model_server,pipeline,ingestion,node_parser}.py`,
`eval/{evaluate,baselines,evaluate_answers,metrics,compare_results,run_batch_cau_hoi}.py`, `app/app.py`, `tests/*.py`, `scripts/{extract_to_md,clean_md,dedupe?}`.

---

## 2. Hiện trạng: những kỹ thuật **đã** dùng (để không đề xuất lại)

| Nhóm | Đã có | Ở đâu |
|---|---|---|
| Node/parse | Custom parser theo Điều/mục sửa đổi, lọc metadata rỗng, chỉ 1 trường vào embedding | `src/processed_loader.py` |
| Index | `VectorStoreIndex` từ `TextNode`, persist, fingerprint theo model + loader + sha256 | `src/index_builder.py` |
| Truy hồi | Vector top-k, `QueryFusionRetriever` (RRF / relative_score) + BM25 tự viết, `SimilarityPostprocessor`, `SentenceTransformerRerank` | `src/retriever.py`, `src/bm25.py` |
| Sinh | `RetrieverQueryEngine`, prompt tiếng Việt chống bịa, `temperature=0` + `seed`, streaming, trích nguồn từ metadata | `src/query_engine.py` |
| Mở rộng thư viện | `RemoteEmbedding(BaseEmbedding)`, `RemoteRerank(BaseNodePostprocessor)` + FastAPI model server | `src/remote_models.py`, `src/model_server.py` |
| Hạ tầng | 2 profile, fp16, tự hạ cấp CPU, `storage/<profile>/<corpus>` | `src/config.py`, `src/index_builder.py` |
| Đánh giá | `RetrieverEvaluator` (kiểm chứng chéo), Recall/MRR/nDCG, bootstrap CI, McNemar, baseline BM25/không xếp hạng, `BatchEvalRunner` + 3 evaluator của thư viện | `eval/*.py` |
| Kỹ nghệ | 26 test offline, CI, `Makefile`, ghim phiên bản, Gradio + log câu hỏi | `tests/`, `.github/`, `Makefile`, `requirements.txt`, `app/app.py` |

---

## 3. Điểm yếu còn lại của mã nguồn hiện tại

### 3.1. Lỗi và lỗi tiềm ẩn (nên sửa trước khi thêm kỹ thuật)

| ID | Vị trí | Hiện tượng | Hệ quả | Cách sửa ngắn |
|---|---|---|---|---|
| **Y1** | `src/retriever.py:91` | `search()` gọi `get_postprocessors(cfg)` **mỗi lần** nếu caller không truyền `postprocessors` → dựng lại reranker (393 weight) từng câu | Bất kỳ caller mới nào (chat engine, agent, script) gọi `search()` trong vòng lặp sẽ nạp model mỗi câu — chậm kinh khủng, dễ tưởng là "tại máy yếu" | Cache bằng `functools.lru_cache` theo `id(cfg)` hoặc **bắt buộc** truyền postprocessors (đổi chữ ký) |
| **Y2** | `eval/evaluate_answers.py:133` | Điểm evaluator được ánh xạ theo `[i-1]`, nhưng `diem_evaluator()` (dòng 66–78) **chỉ chấm các câu có ngữ cảnh** → danh sách ngắn hơn `bo` | Nếu một câu không truy hồi được Node nào (bật `similarity_cutoff`), điểm faithfulness/relevancy bị **lệch hàng** giữa các câu | Trả về list cùng độ dài `responses`, điền `None` cho câu bị bỏ qua |
| **Y3** | `src/processed_loader.py` (không có `trang`) + `scripts/clean_md.py` | Tầng 2 **bỏ mốc `## Trang N`**, metadata Node không có số trang | **Không thể trích dẫn theo trang** — tức là không làm được A1 của chính tài liệu phân tích yêu cầu | Giữ `<!-- trang: N -->` trong tầng 2; `processed_loader` ghi `trang_tu`/`trang_den` cho mỗi Node |
| **Y4** | `src/processed_loader.py` | Node `phan="ban_hanh"` vẫn được index (8/54 Node) | Node "Căn cứ…, ban hành kèm theo…" ít thông tin nhưng nhiều từ khoá chung, dễ chen top-k (đúng như K3 đã ghi) | Bỏ khi build, hoặc `MetadataFilters(phan != ban_hanh)` |
| **Y5** | `src/remote_models.py:45,93` | Gọi HTTP một lần, không retry; timeout 120 s | Model server 503/ngắt giữa → cả phiên `make eval` gãy | `httpx.Client(transport=RetryTransport)` hoặc vòng thử 3 lần có backoff |
| **Y6** | `eval/evaluate.py:226` | Mỗi cấu hình có rerank nạp lại reranker; `KetQua.ci()` tính bootstrap lại mỗi lần in (mỗi chỉ số một lần) | `make eval` nạp reranker 2 lần, in bảng tốn thêm vài giây vô ích | Cache reranker theo tên model; tính CI một lần rồi lưu vào `KetQua` |

### 3.2. Thiếu so với chính tài liệu phân tích yêu cầu

| ID | Thiếu gì | Đối chiếu | Vì sao quan trọng |
|---|---|---|---|
| **Y7** | Không có nhãn **loại câu hỏi** (đơn / số liệu / multi-hop / điều bị sửa / ngoài phạm vi) | F3 | Không có nó thì không thấy được cải thiện của C1/C2/C3/E1 — tài liệu §7.10 đã cảnh báo đúng điểm này |
| **Y8** | Kết quả eval chưa thành **test hồi quy** | B5 | Đổi cấu hình là phải tự đọc số; không có cổng chặn "R@1 tụt" |
| **Y9** | Không đo **token và độ trễ theo bước** | B7, A1 | Không chứng minh được chi phí của rerank/hybrid/prompt dài |
| **Y10** | Corpus hardcode trong `src/corpus.py`; `data/raw` chưa `.gitignore` | — | Chặn việc chạy thí nghiệm nhiều tập văn bản; rủi ro 578 MB vào git |
| **Y11** | Bộ câu hỏi cho **kỹ thuật mới** chưa có (chỉ 31 + 10 + 13 câu, chủ yếu tra cứu đơn) | §7.10 | C2/C3/E1 không có gì để đo |
| **Y12** | Chưa có chính sách từ chối cho **nội dung biểu mẫu** | ĐX-6.2 | Đã chốt ở lượt trước, chưa vào code |

### 3.3. Kỹ nghệ (không phải kỹ thuật RAG)

- `src/ingestion.py` và `src/node_parser.py` là **code chết** (không module nào import) nhưng vẫn nằm trong `src/` → dễ gây hiểu nhầm cả khi đọc code lẫn khi viết báo cáo (đã gây ra đúng lỗi lệch ở Chương 3–4 bản trước). Đề xuất chuyển sang `legacy/`.
- `docs/` chưa có file mục lục; hiện đã có 9 tài liệu, khó tra.
- `pyproject.toml` đã cấu hình `ruff` nhưng CI **không chạy ruff**.
- `tests/` chưa có test cho `eval/evaluate.py` (các luật chấm) và `src/retriever.py` — có thể test bằng `TextNode` giả, không cần model.

---

## 4. Danh mục kỹ thuật nâng cao khả dụng (API đã kiểm tra trên 0.14.24)

Chú thích cột **Trạng thái**: `✅ đã có` · `🟡 một phần` · `⬜ chưa`.
Cột **API** chỉ ghi những gì **đã import thành công** trong môi trường này; phần **không có trong core** ghi rõ ở §4.7.

### 4.1. Dữ liệu và Node (nhóm mạnh nhất của đề tài)

| # | Kỹ thuật | API cụ thể | Giải quyết | Công | Đo bằng | Trạng thái |
|---|---|---|---|---|---|---|
| C1 | Small-to-big: cắt theo khoản, truy hồi trên node con, gộp lên Điều | `HierarchicalNodeParser`, `AutoMergingRetriever`, `RecursiveRetriever`, `NodeRelationship.PARENT/CHILD` | Node hiện tại dài ~1.500 ký tự làm loãng vector và LLM đọc sai chi tiết số | ★★★ | R@k cấp khoản, số token vào prompt, độ đúng câu trả lời | ⬜ |
| — | Biến thể nhẹ của C1 | `SentenceWindowNodeParser` + `MetadataReplacementPostProcessor` | Cùng vấn đề, ít code hơn (không cần cây) | ★★☆ | như trên | ⬜ |
| C2 | Xử lý văn bản sửa đổi theo hiệu lực | `NodeRelationship` + **postprocessor tự viết** (`BaseNodePostprocessor`) | QC 2021 Đ7 vs QĐ 3183 "sửa đổi Điều 7": nếu chỉ 1 trong 2 lọt top-k thì LLM trả lời theo bản cũ | ★★★ | Bộ câu hỏi "điều bị sửa" (chưa có — Y11) | ⬜ |
| C3 | Giải tham chiếu chéo (multi-hop) | `RecursiveRetriever` hoặc postprocessor tự viết theo regex "theo quy định tại Điều X" | Câu hỏi cần 2 Điều (Đ9 + Đ10 + Đ13) | ★★★ | 10–15 câu 2 Điều: R@k của **cả hai** | ⬜ |
| B1 | Thí nghiệm chunking có đối chứng | `SentenceSplitter`, `MarkdownNodeParser`, `SemanticSplitterNodeParser`, `TokenTextSplitter` | Chưa có bằng chứng "cắt theo Điều" tốt hơn baseline | ★★☆ | R@1/3/5, MRR, nDCG, số node | 🟡 (khung đo có, đối chứng chưa) |
| — | Làm giàu metadata Node bằng LLM | `QuestionsAnsweredExtractor`, `SummaryExtractor`, `TitleExtractor`, `KeywordExtractor` | Câu hỏi của sinh viên khác từ ngữ trong văn bản; sinh "câu hỏi giả định" cho mỗi Node giúp khớp | ★★☆ | R@1 trước/sau; chi phí 1 lượt LLM/Node | ⬜ |
| — | Cập nhật tăng dần + khử trùng lặp khi nạp | `IngestionPipeline`, `IngestionCache`, `DocstoreStrategy.UPSERTS` | 290 văn bản: build lại toàn bộ mỗi lần rất tốn; có bản trùng | ★★☆ | thời gian nạp, số Node trùng | ⬜ |

### 4.2. Truy hồi

| # | Kỹ thuật | API cụ thể | Giải quyết | Công | Đo bằng | Trạng thái |
|---|---|---|---|---|---|---|
| A3 | Ngưỡng tương đồng + từ chối câu ngoài phạm vi | `SimilarityPostprocessor` | Câu "fghjkl", "chán" vẫn gọi LLM với 10 Node rác | ★☆☆ | 10 câu ngoài corpus: từ chối đúng / từ chối nhầm | 🟡 (đã cài, **chưa chọn ngưỡng bằng số**) |
| A2 | Lọc theo metadata (nhóm, hiệu lực, khóa) | `MetadataFilters`, `MetadataFilter`, `VectorIndexAutoRetriever` | Thêm văn bản làm R@1 tụt 87% → 81%; CTĐT sẽ chen vào câu hỏi học vụ | ★★☆ | R@1 theo **từng nguồn** | ⬜ |
| C4 | Router / sub-question | `RouterRetriever`, `RouterQueryEngine`, `LLMSingleSelector`, `PydanticSingleSelector`, `SubQuestionQueryEngine`, `QueryEngineTool` | 3 index (học vụ/CTSV/CTĐT); câu so sánh nhiều văn bản | ★★☆ | tỉ lệ chọn đúng hướng; độ trễ (+1 lượt LLM) | ⬜ |
| B3 | Hybrid BM25 + vector | `QueryFusionRetriever` (đã dùng) + BM25 tự viết | Ký hiệu "B+", số hiệu văn bản | ★★☆ | đã đo: RRF làm giảm, relative_score 3:1 tốt nhất bộ 01 | ✅ |
| B2 | Rerank | `SentenceTransformerRerank` (đã), `LLMRerank`, `StructuredLLMRerank` | R@1 | ★★☆ | đã đo: không lợi trên 54 Node | 🟡 (đối chứng LLM-rerank chưa) |
| — | Chống "lost in the middle" | `LongContextReorder` | 10 Node đưa vào prompt, thông tin quan trọng nằm giữa dễ bị bỏ qua | ★☆☆ | độ đúng câu hỏi có 2–3 nguồn | ⬜ |
| D3 | Giảm chi phí suy luận | `SentenceEmbeddingOptimizer` (cắt token theo ngữ nghĩa trước khi gửi LLM), ONNX/int8 cho embedding | Prompt 10 Điều ~ 4.000 token | ★★☆ | độ trễ, token, chất lượng | ⬜ |

### 4.3. Tổng hợp và sinh câu trả lời

| # | Kỹ thuật | API cụ thể | Giải quyết | Công | Đo bằng | Trạng thái |
|---|---|---|---|---|---|---|
| A1 | Trích dẫn nguồn chính xác (kèm trang/khoản) | `format_sources()` + metadata `trang` (Y3) | Hiện chỉ in tên Điều, không có trang/khoản | ★☆☆ | 5 câu hỏi kèm trích đoạn nguồn | 🟡 (thiếu `trang`) |
| E2 | Kiểm chứng trích dẫn theo số [1][2] | `CitationQueryEngine` | Câu trả lời trích Điều đúng nhưng nội dung sai (lỗi nguy hiểm nhất đã đo) | ★★☆ | tỉ lệ câu có căn cứ | ⬜ |
| E3 | Structured output cho câu định lượng | `PydanticOutputParser`/`.as_structured_llm()` (Ollama hỗ trợ format JSON) | "8,4 hệ 10 → 3,4" là lỗi tự suy luận, không tra bảng | ★★☆ | exact-match trên `{gia_tri, don_vi, dieu}` | ⬜ |
| K11 | Công cụ tra bảng quy đổi điểm | `FunctionTool`, `ReActAgent`, `AgentWorkflow`, `ToolMetadata` | Cùng lỗi trên, cách chắc chắn hơn E3 | ★★★ | exact-match; số lượt gọi công cụ | ⬜ |
| A5 | Nhớ ngữ cảnh hội thoại | `CondensePlusContextChatEngine`, `CondenseQuestionChatEngine`, `ChatMemoryBuffer`, `Memory` | "còn kỹ sư?" bị từ chối; sinh viên hỏi nối tiếp | ★★☆ | 3 kịch bản hỏi tiếp | ⬜ |
| — | Chịu lỗi LLM/timeout | `RetryQueryEngine`, `RetrySourceQueryEngine` | Ollama timeout 180 s → cả phiên gãy | ★☆☆ | tỉ lệ câu chạy xong khi LLM chậm | ⬜ |
| — | Giảm số lần gọi LLM ở chế độ compact | `get_response_synthesizer`, `CompactAndRefine`, `Refine`, `TreeSummarize` | Đổi `response_mode` chưa được đo | ★☆☆ | token, độ trễ, độ đúng | 🟡 (mới dùng `compact`) |
| E1 | Corrective RAG nhiều bước | `llama-index-workflows` **2.24.0 đã cài** (`Workflow`, event-driven) | Từ chối quá tay (52%) + không ổn định | ★★★ | độ đúng, từ chối đúng/sai, số vòng | ⬜ |

### 4.4. Đánh giá

| # | Kỹ thuật | API cụ thể | Giải quyết | Công | Trạng thái |
|---|---|---|---|---|---|
| — | Chấm truy hồi bằng thư viện | `RetrieverEvaluator` + `HitRate/MRR/Precision/Recall/AP/NDCG` | Đã kiểm chứng chéo cách đo tự viết | ★☆☆ | ✅ |
| — | Chấm câu trả lời tự động | `FaithfulnessEvaluator`, `RelevancyEvaluator`, `ContextRelevancyEvaluator`, `AnswerRelevancyEvaluator`, `CorrectnessEvaluator`, `SemanticSimilarityEvaluator`, `PairwiseComparisonEvaluator`, `GuidelineEvaluator` | Thay chấm tay 56 câu | ★★☆ | 🟡 (đã viết, **chưa chạy vì không có Ollama**) |
| F2 | Hiệu chỉnh LLM judge | `PairwiseComparisonEvaluator` + tính **Cohen's κ** với nhãn người | Biết judge có đáng tin không (qwen3:4b/8b có thể chấm kém) | ★★★ | ⬜ |
| — | Mở rộng bộ câu hỏi | `DatasetGenerator` (`RagDatasetGenerator`) sinh nháp rồi duyệt tay | 41 câu là quá ít; CI rộng | ★★☆ | ⬜ |
| F3 | Phân loại câu hỏi để báo cáo theo loại | (không cần API — thêm trường `loai` vào JSON) | Chỉ ra kỹ thuật nào giúp loại câu nào | ★☆☆ | ⬜ |
| B8 | Kiểm thử prompt injection | (không cần API — 5–10 câu tấn công) | An toàn khi demo | ★☆☆ | ⬜ |

### 4.5. Vận hành và quan sát

| # | Kỹ thuật | API cụ thể | Giải quyết | Trạng thái |
|---|---|---|---|---|
| B7 | Đếm token và thời gian từng bước | `TokenCountingHandler`, `CallbackManager`, `LlamaDebugHandler`, `llama_index.core.instrumentation` | Chưa có số token/chi phí; không biết thời gian nằm ở retrieve hay LLM | ⬜ |
| — | Vector store ngoài | `llama-index-vector-stores-chroma` / `-qdrant` (cần cài thêm) | Lọc metadata phức tạp, cập nhật từng phần khi corpus lớn | ⬜ |

### 4.6. Từ tài liệu khác (đã có sẵn đề xuất, không lặp lại chi tiết)

- **K1–K12** ([`bao_cao_cai_tien_rag.md`](bao_cao_cai_tien_rag.md) §3): K1 ✅, K2 ✅, K3 ⬜ (=Y4), K4 🟡 (=A3), K5 ⬜, K6 ⬜ (=C2), K7 ✅ (đã đo, kết quả **âm**), K8 ⬜ (=C1), K9 ⬜, K10 ⬜ (=A5), K11 ⬜, K12 ⬜ (=E2).
- **ĐX-1…ĐX-9** ([`de_xuat_code_cai_tien_pipeline.md`](de_xuat_code_cai_tien_pipeline.md)): dedupe, `--kieu` cho `clean_md`, manifest corpus, nhãn eval theo `(nguồn, mục)`, router 3 index.
- **D1** (đo CER của OCR, so Tesseract với VietOCR/PaddleOCR) và **D2** (adapter embedding bằng `EmbeddingAdapterFinetuneEngine`) là hai kỹ thuật **chỉ thuộc nhóm D**, công lớn, chỉ nên làm nếu chọn tổ hợp 4.

### 4.7. API **không** có trong bản đã cài (đừng hứa trong báo cáo)

| API | Tình trạng |
|---|---|
| `BM25Retriever` | Không có trong `llama-index-core` → phải cài `llama-index-retrievers-bm25` hoặc dùng `src/bm25.py` tự viết (đang dùng) |
| `RankGPTRerank`, `NodeRecencyPostprocessor` | Không có trong core (cần package/phiên bản khác) |
| `FLAREQueryEngine` | Cần package riêng (`llama-index-query-engines-flare`) |
| `MetadataExtractor` | Không có trong `llama_index.core.extractors` ở bản này |
| Chroma/Qdrant, Phoenix/Langfuse, Ragas | Cần cài package ngoài → phải ghim vào `requirements.txt` nếu dùng |

---

## 5. Ưu tiên theo ROI (nối vào lộ trình 4 đợt đã có)

| Mức | Việc | Vì sao mức này | Công |
|---|---|---|---|
| **P0 — sửa và mở khoá đo** | Y1 (cache postprocessor), Y2 (lệch hàng điểm), Y3 (**metadata `trang`**), Y4 (bỏ Node `ban_hanh`), Y5 (retry HTTP) | Sửa ít, nhưng Y3 **mở khoá A1** và Y4 là K3 đã ghi từ lâu; Y1/Y2 là lỗi thật | 0,5–1 ngày |
| **P1 — đo cho ra số** | Y9 (`TokenCountingHandler` + độ trễ theo bước), Y8 (kết quả eval thành test hồi quy), F3 + Y11 (phân loại và bổ sung câu hỏi), A3 (chọn `similarity_cutoff` bằng phân bố điểm thật) | Tài liệu §7.1 nói rõ: một kỹ thuật chỉ có giá trị khi **đo được**; không có P1 thì mọi kỹ thuật sau không chứng minh được | 1–2 ngày |
| **P2 — kỹ thuật đặc thù pháp quy** | C2 (liên kết gốc ↔ sửa đổi), A1 (trích dẫn kèm trang), `LongContextReorder`, B1 đối chứng chunking | Đúng tổ hợp 1–2 mà tài liệu §7.10 khuyến nghị; dùng đúng thế mạnh dữ liệu (nhiều cặp gốc–sửa đổi) | 3–5 ngày |
| **P3 — cấu trúc và độ tin cậy** | C1 (small-to-big), C3 (tham chiếu chéo), E2 (`CitationQueryEngine`), E3/K11 (tra bảng quy đổi điểm), A5 (chat memory) | Đây là phần "chọn thêm" của báo cáo, mỗi thứ cần bộ câu hỏi riêng | 1–2 tuần |
| **P4 — chỉ khi còn thời gian** | E1 (corrective RAG bằng Workflow), D1 (CER), D2 (adapter embedding), router 3 index + metadata hiệu lực, vector store ngoài | Công lớn, rủi ro cao (LLM 4B/8B yếu), và **không được** ôm nhiều theo yêu cầu "giải thích được tại buổi thực hành" | — |

---

## 6. Rủi ro và điều kiện

1. **LLM nhỏ.** `qwen3:4b/8b` có thể viết lại truy vấn, sinh câu hỏi con, chấm điểm kém → mọi kỹ thuật "dùng LLM thêm một lần" (C4, E1, F2, `QuestionsAnsweredExtractor`) **phải đo**, không được mặc định là tốt hơn.
2. **Mỗi kỹ thuật cần bộ câu hỏi riêng.** Bộ 31 câu hiện tại chủ yếu tra cứu đơn → sẽ **không thấy** cải thiện của C1/C2/C3/E1 (đúng như §7.10 cảnh báo). Đây là ràng buộc phải làm trước, không phải sau.
3. **Môi trường chạy lại không có GPU/Ollama** → đo được chất lượng truy hồi, **không** đo được độ trễ tuyệt đối của LLM và không chạy được evaluator. Các con số độ trễ phải ghi rõ môi trường.
4. **Ràng buộc của bản 1409:** kỹ thuật nào khai trong báo cáo thì mọi thành viên phải giải thích và sửa được tại buổi thực hành. Vì vậy thà làm **một tổ hợp sâu** (khuyến nghị: tổ hợp 1 "cấu trúc pháp quy" = C1 + C3 + F3, cộng C2) hơn là ghép 10 kỹ thuật nông.
5. **Không nên làm** (chính tài liệu §7.9): Agent/MCP, fine-tune LLM, GraphRAG/multimodal, LLM ≥ 8B trên GPU 3,7 GB.

---

## 7. Năm việc nên làm ngay (nếu chỉ chọn 5)

1. **Y3 — giữ số trang trong tầng 2** (mở khoá trích dẫn theo trang, yêu cầu A1 của chính đề tài).
2. **Y4 — bỏ Node `ban_hanh`** khỏi index (K3; giảm nhiễu top-k ngay, đo được bằng `make eval`).
3. **Y9 — `TokenCountingHandler` + đo độ trễ theo bước** (biến mọi tuyên bố về chi phí thành số).
4. **F3 + Y11 — phân loại câu hỏi và bổ sung câu hỏi cho đúng loại** (điều kiện tiên quyết để đo C1/C2/C3/E1).
5. **Y1/Y2 — sửa hai lỗi tiềm ẩn** trước khi nhân bản code sang chat engine/router (nếu không, lỗi sẽ lan rộng).

> **Xác nhận:** lần này chỉ tạo tài liệu này; không file `.py`, `.yaml`, `.tex` nào bị sửa.
