# Báo cáo phân tích và đề xuất cải tiến RAG

> Ngày lập: 03/10/2026 · Nhánh `preprocessing` · Bổ sung cho [`bao_cao_mo_rong_corpus.md`](bao_cao_mo_rong_corpus.md)
>
> Số liệu ở mục 2 được đo trực tiếp trên index hiện tại (profile `server`, `AITeamVN/Vietnamese_Embedding`).

## 1. Tóm tắt

- **Corpus vẫn rất nhỏ:** 6 văn bản, 54 Node. `similarity_top_k=10` lấy về 18% corpus mỗi lần hỏi, nên Recall@10 = 100% gần như không nói lên điều gì.
- **Thêm văn bản làm truy hồi kém đi:** sau khi nạp thêm QĐ 3183, QĐ 810, QĐ 2375…, Recall@1 của bộ 01 giảm từ **87,1% xuống 81%**. Các văn bản mới chen lên vị trí top-1. Corpus càng lớn thì vấn đề này càng nặng, nên phải xử lý trước khi mở rộng tiếp.
- **Metadata văn bản bỏ trống hoàn toàn:** `_metadata_van_ban.csv` chưa có số hiệu, ngày ban hành, tình trạng hiệu lực. Vì vậy chưa áp dụng được các kỹ thuật lọc theo hiệu lực hay theo khóa.
- **Lỗi câu trả lời phần lớn không nằm ở truy hồi** (theo `eval/results/test-basic.md`). Các lỗi gồm: sai khi tra bảng quy đổi điểm, không hiểu câu hỏi nối tiếp, từ chối quá tay (52%), câu trả lời không ổn định giữa các lần hỏi (nhiệt độ sinh chưa đặt).
- **Đề xuất:** 12 kỹ thuật, chia 3 mức ưu tiên (mục 3), và bổ sung tài liệu theo 3 đợt (mục 4). Đợt 1 nhắm đúng các câu sinh viên đã hỏi mà hệ thống không trả lời được: cấm thi, hoãn thi, phúc khảo, điểm rèn luyện, chuẩn tiếng Anh, khóa luận.

## 2. Hiện trạng tài liệu đầu vào và index

### 2.1 Tài liệu

| Văn bản (tiền tố trong `src/corpus.py`) | Node | Loại Node | Chất lượng OCR* |
|---|---|---|---|
| Quy chế đào tạo SGU 2021 (`25_`) | 25 | 21 Điều + 4 ban hành | 98,4% |
| QĐ 3183/2025 sửa đổi QC 2021 | 9 | 3 Điều + 5 mục sửa đổi + 1 | **94,9%** (thấp nhất) |
| QĐ 810 học cùng lúc hai chương trình | 13 | 9 Điều + 4 ban hành | 96,2% |
| QĐ 2375/2022 chuyển chương trình | 5 | 4 Điều + 1 | 95,8% |
| Quy định khối lượng đào tạo | 1 | không chia Điều | 96,4% |
| Quy định 150 tín chỉ kỹ sư CNTT | 1 | không chia Điều | 99,5% |

\* Tỷ lệ từ là âm tiết tiếng Việt hợp lệ, dùng hàm `quality()` trong `scripts/extract_to_md.py`.

**Vấn đề:**

1. **Văn bản quan trọng nhất lại có OCR kém nhất.** QĐ 3183 (94,9%) chứa toàn bộ quy định mới về rút học phần và thang điểm B+/C+/D+, nhưng vẫn còn lỗi như "Sửa đồi" (3 lần). Các văn bản khác cũng có lỗi kiểu "Dại học", "Đảo tạo". Văn bản ngắn nên sửa tay ở tầng 1 là rẻ nhất.
2. **Metadata trống.** `data/ocr/.../_metadata_van_ban.csv` có đủ cột (`so_hieu`, `ngay_ban_hanh`, `ap_dung`, `tinh_trang`, `bi_sua_doi_boi`) nhưng tất cả các dòng đều rỗng. `_bao_cao_kiem_tra.md` đã liệt kê sẵn các câu ứng viên để điền.
3. **Quan hệ sửa đổi chưa được biểu diễn.** Điều 7 của QC 2021 và mục "sửa đổi Điều 7" của QĐ 3183 là hai Node độc lập. Hệ thống chỉ dựa vào câu trong prompt ("Nếu có văn bản sửa đổi thì dùng nội dung đã sửa đổi"), nên nếu chỉ một trong hai Node lọt vào top-k thì LLM không biết đã có bản sửa đổi.
4. **Node "ban hành" gây nhiễu.** Có 8/54 Node là phần quyết định ban hành ("Căn cứ…", "Điều 1. Ban hành kèm theo…"). Chúng mang ít thông tin nhưng chứa nhiều từ khóa chung, dễ chen vào top-k.

### 2.2 Index

| Chỉ số | Giá trị |
|---|---|
| Số Node | 54 (median 182 từ, max 720 từ; 6 Node dưới 40 từ) |
| Token khi embedding (gồm metadata) | median 243, max 920; 12 Node trên 512 token. Model nhận 8192 token nên không bị cắt |
| Vector store | `SimpleVectorStore` (JSON, tìm vét cạn trong RAM), chỉ có dense vector |
| Văn bản đưa vào embedding | `van_ban: …\nchuong: \ndieu: \nsua_doi_dieu:\n\n<nội dung>`. **Trường rỗng vẫn được ghi vào**, khóa tiếng Anh/không dấu |

### 2.3 Đo lại truy hồi (03/10/2026, vector top-10)

| Bộ | R@1 | R@3 | R@10 | MRR | Báo cáo Chương 5 (khi chỉ có QC 2021) |
|---|---|---|---|---|---|
| 01 (31 câu, QC 2021) | **81%** | 100% | 100% | 0,887 | R@1 87,1%, MRR 0,935 |
| 02 (10 câu, QĐ 3183) | 80% | 90% | 100% | 0,843 | không so sánh được (khi đó chưa nạp QĐ 3183) |

Ở bộ 01, Node top-1 thuộc QĐ 810 trong 3 câu và QĐ 2375 trong 1 câu: văn bản khác chủ đề nhưng dùng từ ngữ tương tự. Ở bộ 02, câu duy nhất trượt top-3 là "B+, C+, D+ áp dụng cho khóa nào": đáp án nằm ở Điều 2 (điều khoản hiệu lực) của QĐ 3183, trong khi retriever trả về các mục sửa đổi Điều 9, 10 vì chúng khớp từ "B+".

**Bảng trong `report/chapters/05-danh-gia.tex` đã cũ, cần cập nhật số liệu này.**

### 2.4 Lỗi câu trả lời (nhật ký `test-basic.md`, 56 câu)

| Nhóm lỗi | Ví dụ | Nguyên nhân |
|---|---|---|
| Tra bảng / tính toán | 8,4 hệ 10 → "3,4" (đúng: B → 3) | LLM 8B tự suy luận thay vì tra bảng |
| Đọc sai chi tiết số | "mỗi học kỳ 30 tuần" (đúng: hai học kỳ cộng lại) | Node dài, khoản cần thiết bị lẫn trong nhiều khoản khác |
| Câu hỏi nối tiếp | "còn kỹ sư" → từ chối | Mỗi câu hỏi được xử lý độc lập |
| Từ chối sai | "ra trường xuất sắt" → từ chối dù Điều 10 có trong ngữ cảnh | Sai chính tả/viết tắt không khớp văn bản; prompt chống bịa quá chặt |
| Không ổn định | Cùng câu hỏi, lần đầu từ chối, lần sau trả lời | `Ollama(...)` không đặt `temperature`, nên dùng mặc định của model (lấy mẫu ngẫu nhiên) |
| Ngoài phạm vi | Điểm rèn luyện, học phí, cấm thi | Corpus chưa có văn bản (mục 4) |

## 3. Kỹ thuật cải tiến

Ký hiệu: **Ưu tiên 1** là làm ngay, ít code, sửa lỗi đã đo được. **Ưu tiên 2** là kỹ thuật RAG nâng cao, cần đo trước và sau. **Ưu tiên 3** là khi corpus đã lớn.

### Ưu tiên 1

| # | Kỹ thuật | Giải quyết | Cách làm trong LlamaIndex |
|---|---|---|---|
| K1 | **Sinh câu trả lời ổn định** | Câu trả lời không ổn định | `Ollama(temperature=0, additional_kwargs={"seed": 42})` trong `make_llm` |
| K2 | **Làm sạch văn bản đưa vào embedding** | Trường rỗng, khóa không dấu làm nhiễu vector | Bỏ trường rỗng khỏi metadata; đặt `metadata_template`/`text_template` với nhãn tiếng Việt ("Văn bản: …, Điều 7: …") |
| K3 | **Loại hoặc hạ trọng số Node ban hành** | 8 Node ít thông tin chen vào top-k | Không index phần `ban_hanh`, hoặc lọc bằng `MetadataFilters(phan != ban_hanh)` (cần vector store hỗ trợ toán tử `!=`) |
| K4 | **Ngưỡng tương đồng, xử lý câu ngoài phạm vi** | "fghjkl", "chán" vẫn gọi LLM với 10 Node không liên quan | `SimilarityPostprocessor(similarity_cutoff=…)`. Ngưỡng chọn từ phân bố score của bộ câu hỏi; không còn Node nào thì trả lời luôn, không gọi LLM |
| K5 | **Điền metadata văn bản** | Chưa lọc theo hiệu lực / khóa được | Điền `_metadata_van_ban.csv` (12 dòng, có sẵn câu ứng viên); `processed_loader` đưa `so_hieu`, `ngay_ban_hanh`, `ap_dung` vào metadata Node |

### Ưu tiên 2: kỹ thuật RAG nâng cao

| # | Kỹ thuật | Giải quyết | Cách làm / ghi chú |
|---|---|---|---|
| K6 | **Mở rộng theo quan hệ sửa đổi** (amendment-aware retrieval) | Lấy được Điều gốc mà không lấy bản sửa đổi, hoặc ngược lại | Postprocessor tự viết: với mỗi Node `dieu=X` của QC 2021, thêm Node `sua_doi_dieu=X` của QĐ 3183, và ngược lại; gắn nhãn "đã bị sửa đổi bởi …". Có thể biểu diễn bằng `NodeRelationship`. Đây là kỹ thuật riêng của văn bản pháp quy, đáng làm thành một mục trong báo cáo |
| K7 | **Hybrid search: BM25 + vector** | Câu hỏi chứa số hiệu, ký hiệu ("B+", "Điều 10", "150 tín chỉ"), vốn là điểm yếu của embedding | `QueryFusionRetriever(mode="reciprocal_rerank")` kết hợp `BM25Retriever` và vector retriever. BM25 tiếng Việt cần tách từ (`pyvi`/`underthesea`) |
| K8 | **Small-to-big: Node theo khoản, ngữ cảnh theo Điều** | Đọc sai chi tiết trong Điều dài (Node tới 920 token) | Cắt thêm Node con theo khoản ("1.", "2.", "a)"); truy hồi trên Node con, đưa Điều cha cho LLM (`AutoMergingRetriever` hoặc `RecursiveRetriever`). Cũng giúp trích dẫn tới mức khoản |
| K9 | **Viết lại câu hỏi** (query rewriting) | Viết tắt, sai chính tả, tiếng lóng ("chỉ", "rớt", "xuất sắt", "cấm thi") | (a) Từ điển đồng nghĩa trong lĩnh vực: rớt → không đạt, chỉ → tín chỉ…; (b) LLM viết lại câu hỏi trước khi truy hồi; (c) thử `HyDEQueryTransform`. Cả ba phải đo, vì viết lại có thể làm lệch nghĩa |
| K10 | **Chat engine có ngữ cảnh hội thoại** | "còn kỹ sư" | `CondensePlusContextChatEngine` gộp lịch sử thành câu hỏi độc lập. Gradio (`app/app.py`) đã có lịch sử chat để dùng |
| K11 | **Công cụ tính toán, tra bảng** (agent / function calling) | Quy đổi điểm 10 → 4 → chữ, xếp loại tốt nghiệp | Trích bảng ở Điều 9, 10 thành dữ liệu; `FunctionTool` quy đổi tất định; `ReActAgent` hoặc router chọn giữa tool và RAG. Đưa bảng thành Markdown table khi cắt Node cũng giúp LLM đọc đúng |
| K12 | **Prompt trích dẫn trước, kết luận sau** | LLM nhớ quy tắc của trường khác ("lấy điểm lần cuối") | Yêu cầu trích nguyên văn câu quy định rồi mới trả lời; hoặc `CitationQueryEngine` (chia nhỏ nguồn, đánh số trích dẫn) |

### Ưu tiên 3: khi corpus đã lớn (sau đợt 2 ở mục 4)

- **Lọc metadata tự động hoặc router:** `VectorIndexAutoRetriever` để LLM tự sinh bộ lọc (`nhom=thi`, `ap_dung_khoa>=2022`), hoặc `RouterQueryEngine` theo nhóm (đào tạo / CTSV / thủ tục / lịch năm học).
- **Đánh giá lại reranker:** khi có vài trăm Node, kết luận "rerank làm giảm Recall@1" có thể không còn đúng. Khi đo lại nên tăng `reranker_top_n` lên 5.
- **Vector DB** (Chroma/Qdrant) thay `SimpleVectorStore`: cần cho bộ lọc phức tạp (K3, lọc theo hiệu lực) và cập nhật từng phần, không phải build lại toàn bộ.
- **Sinh câu hỏi giả định cho mỗi Node** (`QuestionsAnsweredExtractor`): thêm cách hỏi kiểu sinh viên vào embedding. Tốn một lượt LLM cho mỗi Node lúc index.

### Đánh giá đi kèm (bắt buộc để chứng minh cải tiến)

- **Mở rộng bộ câu hỏi có nhãn:** thêm câu viết tắt/sai chính tả, câu hỏi nối tiếp, câu ngoài phạm vi (nhãn "từ chối"), câu cần tra bảng. Có thể sinh nháp bằng `RagDatasetGenerator` rồi duyệt tay.
- **Chấm câu trả lời tự động:** `CorrectnessEvaluator` (so với đáp án chuẩn), `FaithfulnessEvaluator` (có bịa ngoài ngữ cảnh không), cộng tỷ lệ từ chối đúng/sai.
- **Bảng ablation:** baseline → +K2/K3 → +K7 → +K8 → +K6…, mỗi dòng ghi R@1, MRR, độ đúng câu trả lời, độ trễ. Đây chính là phần "80% công nghệ" mà khung đánh giá yêu cầu.

## 4. Đề xuất tài liệu bổ sung

Tiêu chí chọn: (1) sinh viên đã hỏi mà hệ thống không trả lời được (theo nhật ký); (2) văn bản đang có hiệu lực; (3) văn bản giúp chứng minh một kỹ thuật ở mục 3.
Tất cả đã có trong `data/raw`. **Phải khử trùng lặp.** Bản trùng hoàn toàn đã được đánh dấu theo sha256 trong `data/raw/metadata_manifest.csv` (cột `trung_noi_dung_voi`), ví dụ quyết định hoãn thi 2 bản, biên chế năm học 2026–2027 2 bản. Tuy vậy, QĐ 2590 về khóa luận có **4 file khác sha256** (scan khác nhau của cùng một văn bản), nên phải chọn tay một bản.

### Đợt 1: văn bản học vụ hiện hành có cấu trúc Điều (dùng lại `clean_md.py` + `processed_loader`)

| Nhóm | File trong `data/raw/01_quy_che_dao_tao/…` hoặc `04_…` | Trả lời câu hỏi kiểu | Kỹ thuật minh họa |
|---|---|---|---|
| Thi học kỳ | `3_cong_tac_thi_ket_thuc_hoc_phan/QD898BanHanhQuyDinhToChucThiHocKi.pdf` | "vắng nhiều có bị cấm thi không" (đã bị từ chối trong nhật ký) | — |
| Hoãn thi, thi lại | `3_…/3260-QD-Hoan-thi-.pdf` (trùng `20251120…_HoanThi.pdf`) | "ốm có được hoãn thi" | — |
| Khiếu nại, phúc khảo | `3_…/CV_3248_001_khieunai.pdf`, `3_…/HD-Quy trinh phuc khao bai thi ket thuc hoc phan.pdf` | "phúc khảo thế nào, bao lâu" | Văn bản dạng quy trình (theo bước) |
| Chuẩn tiếng Anh | `2_quy_doi_tieng_anh/29_2101-…2024 tro di.pdf`, `CV2626…`, `TB so 2567…PTE…`, `30_TB so 2451…` | "IELTS 5.5 quy đổi được không" | **Lọc theo khóa** (`ap_dung` khác nhau theo khóa tuyển sinh) |
| Khóa luận tốt nghiệp | `04_khoa_luan_thuc_tap/quy_dinh_chung/QD2590…2022.pdf` + `QD_DieuChinhKLTN_2025.pdf` | "điều kiện làm khóa luận" | **Cặp gốc + sửa đổi thứ hai** để kiểm chứng K6 |
| Thời gian học tối đa | `5_quy_dinh_hoc_vu_khac/DHSG_quy-dinh-thoi-gian-toi-da-…pdf` (đối chiếu QĐ 736/2014) | "tối đa mấy năm" | Xác định văn bản nào còn hiệu lực trước khi nạp |
| Cố vấn học tập, bảng điểm, bản sao | `5_…/QĐ_CVHT.pdf`, `QuyDinh_CapBangDiem.pdf`, `QuyDinh_CapBanSao.pdf` | "xin bảng điểm ở đâu" | — |

### Đợt 2: công tác sinh viên và tài liệu khác cấu trúc (cần parser mới, nên làm cùng router)

| Nhóm | File trong `data/raw/02_…` / `03_…` | Ghi chú |
|---|---|---|
| Điểm rèn luyện | `02_cong_tac_sinh_vien/diem_ren_luyen/QUY-DINH-VE-DANH-GIA-KET-QUA-REN-LUYEN-SV-DHSG.pdf` + `2_thong-bao-…bo-sung-dieu-chinh…phieu…pdf` | Câu bị từ chối nhiều nhất trong nhật ký. Thư mục có 7 bản, phải chọn bản mới nhất |
| Học bổng | `che_do_chinh_sach_hoc_bong/27_…1357…2026…` + `28_…2946…sua-doi…` | Thêm một cặp gốc + sửa đổi (K6) |
| Quy trình thủ tục CTSV | `quy_trinh_thu_tuc/*.pdf` (14 quy trình: bảo lưu, thôi học, học lại, xác nhận, chuyển trường…) | Parser theo bước; câu hỏi dạng "làm thế nào" |
| Biên chế năm học | `03_chuong_trinh_dao_tao/bien_che_nam_hoc/BienChe_2025-2026_chinhthuc.pdf`, `BienCheNamHoc_2026-2027.pdf` | Bảng ngày tháng ("khi nào thi", "nghỉ Tết"); hợp với K11 (tra bảng) hơn là vector |
| Quy tắc ứng xử | `van_ban_quy_dinh/21_qui-tac-ung-xu-cua-nguoi-hoc…pdf` | Có cấu trúc Điều |

**Học phí:** `11_nghi-dinh-238…` chỉ quy định **mức trần** của Chính phủ, không phải học phí thực tế của SGU. Nếu nạp văn bản này, hệ thống sẽ trả lời sai câu "bao nhiêu tiền một tín chỉ". Chỉ nên thêm khi có thông báo học phí của trường.

### Đợt 3: chỉ dùng để đối chứng phiên bản, không đưa vào corpus trả lời

QC 43/2007 (`01.Quyche43`), VBHN 17/2014, QC 2017, QC 08/2021 của Bộ, TT 57. Các file này **đã có ở tầng 2** nhưng đang bị loại khỏi `SGU_HIEU_LUC`, đúng như kết luận đã đo. Chúng chỉ có ích nếu làm kỹ thuật "truy hồi theo thời điểm hiệu lực" (lọc theo `ngay_ban_hanh`, `tinh_trang`), vì khi để chung chúng lấn át QC 2021.

**Không đưa vào:** biểu mẫu `.doc/.docx`; 80 file chương trình đào tạo theo ngành (cần index riêng + router nếu muốn làm); thông báo `gdct*`, `tbc*`; video, file nén.

### Thay đổi code cần có trước khi mở rộng

- `src/corpus.py` hiện chỉ có **một** `CORPUS_DIR`, còn `SGU_HIEU_LUC` khớp theo tiền tố tên file trong thư mục đó. Để nạp nhiều nhóm thư mục, đổi khóa thành đường dẫn tương đối dưới `data/processed` và thêm metadata `nhom` (đào tạo / thi / CTSV…), dùng cho lọc và router.
- Các thư mục mới phải chạy `extract_to_md.py` → sửa tay → `clean_md.py`. Hiện chỉ `01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc` đã có tầng 1 và tầng 2.
- Tách đường dẫn index theo tập văn bản để so sánh trước/sau khi mở rộng (hiện `persist_dir` chỉ theo profile + thư mục).

## 5. Lộ trình gợi ý

1. **K1, K2, K3, K4, K5** + sửa OCR QĐ 3183 → đo lại (vẫn dùng bộ 01, 02).
2. Mở rộng bộ câu hỏi có nhãn và bộ chấm câu trả lời (mục 3, Đánh giá).
3. Hỗ trợ nhiều thư mục trong `corpus.py` → nạp **đợt 1** → đo lại. Recall dự kiến giảm như vừa đo được, tạo lý do để làm bước 4.
4. **K7 (hybrid), K6 (sửa đổi), K8 (small-to-big)**, đo ablation từng kỹ thuật.
5. **K10, K9, K11, K12** cho phần sinh câu trả lời.
6. **Đợt 2** + router / lọc metadata tự động + đánh giá lại reranker.
