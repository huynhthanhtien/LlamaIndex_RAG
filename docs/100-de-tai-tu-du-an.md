# 100 đề tài rút từ dự án và nội dung trả lời

Dùng để ôn tập và để lập dàn ý khi giảng viên giao một đề tài lấy từ chính dự án. Mỗi đề tài có **ý chính**, **số
liệu** (đã đo trong repo) và **nguồn** để mở ra đối chiếu. Đây là dàn ý, không phải bài viết sẵn: mỗi người tự viết
bằng lời của mình, chạy lại hoặc mở file nguồn để kiểm, và ghi rõ trong AI Disclosure nếu dùng tài liệu này.

Số liệu chính (dùng chung cho nhiều đề tài):

| Đại lượng | Giá trị | Nguồn |
|---|---|---|
| Corpus | 20 văn bản, 118 Node | `src/processed_loader.py`, Mục 4.1.3 |
| R@1 cấu hình chốt trên dev (bộ 01, 02, dev đợt 1–3) | 27/31, 7/10, 20/20, 15/15, 14/15 | Bảng 8.2 |
| R@1 vector đơn thuần trên dev | 25/31, 9/10, 19/20, 10/15, 12/15 | Bảng 8.2 |
| BM25 trên bộ 01 | R@1 18/31 (58%) | Bảng 4.4 |
| Tập kiểm chứng (đóng băng 31/10, commit `08bdea5`) | R@1 50% (Quy chế 2021), 62,5% (QĐ 3183); 72% nếu sửa số Điều theo bản SGU | `eval/results/truy-hoi-kiem-chung.md` |
| Câu trả lời 99 câu dev (người chấm) | 93/99 đúng | `cham-tay-tien.csv` |
| Kiểm thử | 80 (68 chạy offline, 10 cần Ollama, 2 expected failure) | `make test` |

---

## A. LlamaIndex và kiến trúc RAG (1–10)

**1. RAG giải quyết vấn đề gì của LLM?**
- LLM không biết quy chế riêng của SGU, và có thể bịa ra quy định. RAG truy hồi các trích đoạn liên quan rồi đưa vào prompt.
- Hệ thống có hai pha: chuẩn bị (dữ liệu → Node → index, chạy một lần) và truy vấn (truy hồi → tổng hợp câu trả lời, chạy mỗi câu hỏi).
- Nguồn: Mục 1.2.1, `src/pipeline.py`.

**2. Sáu thành phần lõi của LlamaIndex trong đồ án**
- Document/Node, NodeParser, embedding cùng VectorStoreIndex, Retriever, NodePostprocessor, ResponseSynthesizer/QueryEngine.
- Mỗi thành phần tương ứng một file: `processed_loader.py`, `index_builder.py`, `retriever.py`, `phien_ban.py`, `query_engine.py`.
- Nguồn: Bảng 3.3, Bảng 4.1.

**3. Document và TextNode khác nhau thế nào?**
- Document là văn bản nguồn. TextNode là đơn vị dùng để truy hồi, mang metadata và quan hệ với văn bản gốc.
- Đồ án dựng index trực tiếp từ TextNode đã cắt sẵn, vì nếu truyền Document thì LlamaIndex tự cắt bằng SentenceSplitter và làm mất ranh giới Điều.
- Nguồn: Mục 4.3.2.

**4. Hello World với LlamaIndex**
- Script tạo một Document, dựng SummaryIndex rồi đếm số Document trong docstore. Không cần LLM hay model embedding.
- Mỗi Document có `doc_id` dạng UUID do LlamaIndex tự sinh.
- Nguồn: `scripts/hello_world.py`, Đoạn mã 3.1.

**5. Settings toàn cục của LlamaIndex**
- `Settings.embed_model` là model embedding dùng chung cho mọi thành phần cần embedding.
- Đồ án đặt giá trị này trong `setup_embedding(cfg)`: nạp model tại chỗ (local) hoặc gọi `RemoteEmbedding` qua model server.
- Nguồn: `src/index_builder.py`.

**6. Retriever tách khỏi postprocessor: lợi ích**
- Có thể cắm BM25 tự viết, bộ lọc phiên bản và reranker mà không phải sửa phần truy hồi hay phần sinh câu trả lời.
- Thứ tự áp dụng: ngưỡng tương đồng → LocPhienBan → rerank → UuTienSuaDoi.
- Nguồn: Mục 8.2, `get_postprocessors()`.

**7. Response mode `compact`**
- Gom nhiều Node vào ít lượt gọi LLM nhất có thể. Nếu ngữ cảnh vượt cửa sổ mới chia lượt và dùng refine.
- Với 3 Node sau rerank (prompt khoảng 2 100–3 100 token), cả 99 câu dev đều chỉ cần **1 lượt** gọi LLM.
- Nguồn: Bảng 10.5.

**8. Khi nào không nên dùng LlamaIndex?**
- Khi kho dữ liệu rất nhỏ (đưa thẳng vào prompt là đủ), khi cần pipeline tùy biến sâu, hoặc khi phiên bản thư viện thay đổi nhanh.
- Nguồn: Mục 1.3.4.

**9. Hệ sinh thái tích hợp**
- Đồ án dùng các gói `llama-index-embeddings-huggingface` và `llama-index-llms-ollama`.
- BM25Retriever chính thức nằm ở gói riêng, nên nhóm tự viết BM25 trong `src/bm25.py`.
- Nguồn: Mục 1.2.8, Mục 8.2.

**10. Điều gì chỉ có ở LlamaIndex mà dự án tự viết sẽ không có?**
- Metadata tự quyết định trường nào đưa vào embedding, trường nào đưa vào prompt.
- Ba interface tách rời: truy hồi, hậu xử lý, tổng hợp câu trả lời.
- StorageContext cùng docstore để lưu và nạp lại index.
- Nguồn: Mục 4.6.3.

## B. Dữ liệu, OCR và metadata (11–20)

**11. Vì sao phải OCR?**
- Quy chế SGU là bản scan, không có lớp văn bản, nên bộ đọc PDF thông thường gần như không lấy được chữ.
- Quy trình: pdf2image render ở 300 dpi, rồi Tesseract với `lang="vie"`.
- Nguồn: Mục 4.1.1, `scripts/extract_to_md.py`.

**12. Markdown hai tầng**
- Tầng 1 (`data/ocr`) là nơi duy nhất được sửa tay.
- Tầng 2 (`data/processed`) luôn sinh lại được từ tầng 1, với heading `#` cho văn bản, `##` cho Chương, `###` cho Điều, `####` cho mục sửa đổi.
- Nguồn: `scripts/clean_md.py`, Mục 4.1.2.

**13. Đo chất lượng OCR**
- Chỉ số là tỷ lệ âm tiết tiếng Việt hợp lệ, dùng để chọn bản scan tốt hơn khi có nhiều bản.
- QĐ 3183/2025 có tỷ lệ thấp nhất (94,9%) và vẫn còn lỗi "Sửa đồi".
- Nguồn: Mục 4.1.3.

**14. Front matter và metadata của văn bản**
- Gồm `so_hieu`, `ngay_ban_hanh`, `tinh_trang`, `sua_doi`, `bi_thay_the_boi`, `ap_dung_khoa_tu/den`, `ap_dung_khoa_tu_theo_dieu`.
- Các trường này là đầu vào cho bước lọc phiên bản.
- Nguồn: Mục 4.1.2, `_metadata_van_ban.csv`.

**15. Bảy định dạng văn bản (F1–F7) và cách xử lý từng loại**
- Ví dụ: quy chế có Chương/Điều, quyết định ban hành kèm văn bản, thông báo mà nội dung chính là bảng, hướng dẫn quy trình theo bước, công văn ngắn.
- Mỗi định dạng có cách cắt Node riêng.
- Nguồn: Bảng 4.5.

**16. Mở rộng corpus từ 1 lên 20 văn bản**
- Nhóm đọc 49 tệp, loại bản trùng, bản hết hiệu lực và biểu mẫu.
- QĐ 736 được giữ làm ca kiểm thử xung đột thay vì nạp vào corpus.
- Văn bản hết hiệu lực lấn át văn bản đang áp dụng khi truy hồi, nên không nạp.
- Nguồn: Mục 4.1.5.

**17. Xác minh hiệu lực văn bản**
- Số hiệu được nhập tay và đối chiếu với PDF (OCR từng đọc 3089 thành 3084).
- Nhóm đọc phần căn cứ và điều khoản thi hành để xác định quan hệ sửa đổi, thay thế và khóa áp dụng.
- Nguồn: `_bao_cao_kiem_tra.md`, commit `50e73f0`.

**18. Bảng quy đổi chứng chỉ tiếng Anh dạng CSV**
- 5 bảng, 300 dòng, 8 cột.
- Đối chiếu với PDF đã sửa 24 ô sai biên ở TB 2366: bất đẳng thức chặt bị chép thành khoảng có cả hai đầu.
- Nguồn: `data/bang_quy_doi/`, Mục 4.1.5.

**19. Phần "Quyết định ban hành" làm hỏng nhãn**
- Điều 1–3 của quyết định ban hành trùng số với Điều 1–3 của Quy chế, nên phép chấm theo số Điều bị sai.
- Cách sửa: tách riêng phần này với `phan="ban_hanh"`.
- Nguồn: Mục 5.1, Mục 5.3.

**20. Lỗi OCR ảnh hưởng tới các bước sau**
- Heading Điều bị hỏng ("Điều 12 … bL Kết quả", "1." thành "]."), số trong bảng bị đọc thành "§ § §".
- Cách sửa là sửa ở bước làm sạch dữ liệu, không vá bằng regex.
- Nguồn: Bảng 4.5, `lab/README.md` Phụ lục C.

## C. Chia Node (chunking) (21–32)

**21. Chia theo Điều thay vì theo số token**
- Mỗi Điều là một đơn vị nghĩa và là đơn vị người dùng trích dẫn.
- Cắt cố định theo token dễ chia đôi một bảng điểm hoặc tách điều kiện khỏi hệ quả của nó.
- Nguồn: Mục 4.2.2, Chương 5.

**22. Thuật toán của `processed_loader`**
- Tách văn bản bằng regex `(?m)^(?=#{1,4} )` (lookahead nên giữ lại dòng heading).
- Mỗi `###` hoặc `####` thành một Node.
- Nội dung nằm ngay dưới `#`/`##` chỉ thành Node khi dài từ 30 từ trở lên (`MIN_TU_NOI_DUNG`).
- Nguồn: Mục 4.2.1.

**23. MAX_TU và SentenceSplitter đếm hai đơn vị khác nhau**
- `MAX_TU = 1024` đếm theo từ. `SentenceSplitter(1024, 50)` đếm theo token tiktoken.
- Tiếng Việt trung bình 2,21 token tiktoken mỗi từ, nên mỗi đoạn sau khi cắt dài khoảng 460 từ.
- Nguồn: Mục 4.2.1.

**24. Độ dài Node theo từng tokenizer**
- Trung bình 372 token AITeamVN, lớn nhất 1 210. Trung bình 651 token tiktoken, lớn nhất 2 128.
- 63/118 Node dài hơn 256 token, giới hạn của model bkai.
- Nguồn: Bảng 4.6.

**25. Ảnh hưởng của chunk size (thí nghiệm trong lab)**
- Chunk 256 và 512 đều đạt R@1 10/10.
- Chunk 1024 làm cả 17 Node vượt 256 token và R@1 còn 8/10.
- Chunk 64: câu ngoài phạm vi có điểm 0,441, cao hơn câu có đáp án thấp nhất (0,393).
- Nguồn: `lab/README.md` Bài tập 1.

**26. Giới hạn token của model embedding**
- Model bkai chỉ đọc 256 token PhoBERT đầu mỗi Node, phần sau bị bỏ khi tính vector.
- Model AITeamVN đọc tới 8 192 token, nên ở profile server không Node nào bị cắt.
- Nguồn: Mục 4.2.2.

**27. Chunk overlap 50**
- Chỉ có tác dụng khi một Điều bị cắt tiếp: giữ câu dẫn của khoản trước để đoạn sau không mất ngữ cảnh.
- Nguồn: Mục 4.2.2.

**28. Chia theo Điều có làm R@1 cao hơn không? (lab)**
- Không cắt tiếp: 8/10, vì 14/21 Điều dài hơn 256 token. Cắt tiếp ở 256 token: 9/10. Cắt cố định 256: 10/10.
- Lợi ích thật của chia theo Điều là nhãn nguồn chính xác tới từng Điều.
- Nguồn: `lab/README.md` Bài tập 2.

**29. Metadata không được làm nhiễu vector**
- Nếu để mặc định, vector sẽ nhúng cả các dòng rỗng như `chuong:`, `dieu:`.
- Cách làm: chỉ gắn những khóa có giá trị, và chỉ `nguon_trich` được đưa vào embedding (`excluded_embed_metadata_keys`).
- Nguồn: Mục 5.2.

**30. Metadata nào đưa vào prompt?**
- `excluded_llm_metadata_keys` loại các khóa kỹ thuật và khóa dùng để lọc phiên bản (file, url, quan hệ, khóa áp dụng).
- Giữ lại tên văn bản và số Điều để LLM trích dẫn.
- Nguồn: Bảng 9.1, `KHONG_LLM`.

**31. Ý tưởng small-to-big**
- Truy hồi trên Node con (khoản), rồi đưa cả Điều cha cho LLM (HierarchicalNodeParser cùng AutoMergingRetriever).
- Nhắm vào lỗi đọc sai chi tiết số trong các Điều dài.
- Nguồn: Mục 12.1.

**32. Hạn chế của bộ cắt hiện tại**
- Phụ thuộc vào heading do `clean_md.py` dựng. 10 văn bản không chia Điều chỉ thành 1 Node mỗi văn bản.
- Đã đề xuất đổi ngưỡng sang đếm bằng tokenizer của model embedding.
- Nguồn: Mục 5.6.

## D. Embedding, index và persist (33–40)

**33. Chọn model embedding tiếng Việt**
- Local: bkai vietnamese-bi-encoder, 768 chiều. Server: AITeamVN/Vietnamese_Embedding, 1 024 chiều.
- Vector được chuẩn hóa nên tích vô hướng chính là cosine.
- Nguồn: Mục 4.3.1.

**34. Model bkai cần tách từ**
- Model card yêu cầu input đã tách từ (ví dụ bằng pyvi).
- Mã nguồn hiện chưa tách từ, nên số đo của profile local chỉ để tham khảo.
- Nguồn: Phụ lục C báo cáo nhóm.

**35. Hai profile local và server**
- Khác nhau ở model embedding, LLM (qwen3:4b hay qwen3:8b), có reranker hay không, và có dùng fp16 không.
- Chọn profile qua biến `RAG_PROFILE`; giá trị sai thì báo `ValueError`.
- Nguồn: `src/config.py`, Bảng 3.2.

**36. Lưu và nạp lại index**
- Dùng `storage_context.persist()` và `load_index_from_storage()`.
- Dựng mới khoảng 4 giây trên GPU fp16; nạp lại khoảng 0,5 giây. Trong lab trên CPU: 5,8 giây so với 0,3 giây.
- Nguồn: Chương 6.

**37. Fingerprint chống dùng nhầm index cũ**
- `corpus.json` lưu tên model, thư mục corpus, phiên bản loader cùng các ngưỡng cắt, và sha256 kèm tên hiển thị của từng file.
- Chỉ cần một thứ đổi là index tự build lại.
- Nguồn: Đoạn mã 6.1.

**38. Lỗi lệch số chiều vector**
- Lỗi `shapes (1024,) and (768,)` xảy ra khi đổi model embedding mà vẫn nạp index cũ.
- Cách tránh: mỗi profile lưu index ở thư mục riêng `storage/<profile>/<corpus>`, kèm fingerprint.
- Nguồn: Mục 6.2.1.

**39. SimpleVectorStore và khi nào cần vector DB ngoài**
- Tìm vét cạn là đủ với vài trăm Node.
- Cần Chroma hoặc Qdrant khi kho lớn, cần lọc metadata phức tạp hoặc cập nhật từng phần.
- Nguồn: Mục 12.1.

**40. fp16 để vừa GPU 4 GB**
- fp32 chiếm khoảng 3,5 GB rồi báo CUDA OOM khi nạp reranker. fp16 tổng chỉ khoảng 2,2 GB.
- `SentenceTransformerRerank` không nhận tham số dtype, nên nạp trên CPU, ép `.half()` rồi mới đưa lên GPU.
- Nguồn: Mục 11.3.2.

## E. Truy hồi, rerank, hybrid và lọc phiên bản (41–54)

**41. Truy hồi vector top-k**
- `as_retriever(similarity_top_k=10)` trả về 10 Node có cosine cao nhất.
- Điểm cosine thấp (0,3–0,6) và sát nhau (chênh 0,004), nên không đặt được ngưỡng cố định.
- Nguồn: Bảng 4.2.

**42. Vector và BM25**
- Trên bộ 01: vector R@1 81% so với BM25 58%. Chênh 23 điểm là kết quả thực tiễn lớn nhất của đồ án.
- Nguồn: Bảng 4.3, Bảng 4.4.

**43. Cài BM25 tự viết**
- BM25 Okapi với k1 = 1,5 và b = 0,75. `tach_tu()` bỏ dấu tiếng Việt, nên câu gõ không dấu vẫn khớp.
- Đánh đổi: không phân biệt được hai từ chỉ khác dấu.
- Nguồn: `src/bm25.py`, Mục 8.2.

**44. Hybrid bằng RRF**
- `QueryFusionRetriever` trộn hai nguồn ở chế độ `reciprocal_rerank`.
- Điểm RRF không cùng thang với cosine, nên khi bật hybrid thì bỏ qua `similarity_cutoff`.
- Nguồn: Mục 8.2.

**45. Vì sao hybrid không giúp?**
- Dev đợt 2 chỉ tăng từ 10 lên 11, trong khi bộ 02 tụt từ 9 xuống 6.
- RRF trọng số bằng nhau kéo lên các Node chứa nhiều tên chứng chỉ thuộc khóa khác.
- Khi đã có rerank thì thêm hybrid không đổi kết quả.
- Nguồn: Mục 8.3.

**46. Bi-encoder và cross-encoder**
- Bi-encoder mã hóa câu hỏi và đoạn văn riêng rẽ, nên nhanh.
- Cross-encoder đọc cả cặp câu hỏi–đoạn văn, nên chính xác hơn nhưng chậm (khoảng 800 ms/câu so với 47 ms/câu).
- Nguồn: Mục 1.2.6, Bảng 8.1.

**47. Reranker chỉ đọc 512 token**
- `SentenceTransformerRerank` cố định `max_length = 512`, trong khi 35/118 Node dài hơn mức này.
- `dat_do_dai_toi_da()` đặt lại 2 048: bộ 01 tăng từ 25 lên 27, dev đợt 2 tăng từ 10 lên 14.
- Nguồn: Mục 8.3.

**48. Lọc phiên bản: LocPhienBan**
- Bỏ văn bản hết hiệu lực hoặc bị thay thế.
- Nếu câu hỏi nêu khóa thì bỏ Node không áp dụng cho khóa đó, nhưng chỉ khi cùng chuỗi văn bản vẫn còn Node áp dụng được.
- Nguồn: `src/phien_ban.py`, Mục 8.2.

**49. UuTienSuaDoi và ngưỡng 0,5**
- Bản sửa đổi cả văn bản chỉ được đưa lên trước khi điểm rerank của nó đạt ít nhất 0,5 lần văn bản cũ.
- Lý do: TB 2567 chỉ bổ sung chứng chỉ PTE nhưng bị đẩy lên top-1 cho cả câu hỏi về IELTS.
- Nguồn: Mục 8.3.

**50. Metadata quyết định giữ hay bỏ, điểm rerank chỉ quyết định thứ tự**
- Việc loại Node chỉ dựa vào metadata hiệu lực. Ngưỡng 0,5 không loại Node nào, chỉ ảnh hưởng thứ tự trước khi cắt lấy 3 Node.
- Nguồn: Mục 8.3.

**51. So sánh 12 cấu hình truy hồi**
- 3 kiểu truy hồi × có/không rerank × có/không lọc phiên bản.
- Rerank đóng góp nhiều nhất. Lọc phiên bản chỉ an toàn khi đi cùng rerank.
- Nguồn: Bảng 8.2.

**52. Kiểm định McNemar giữa các cấu hình**
- Cấu hình chốt hơn BM25 có ý nghĩa ở bộ 01 (p = 0,012) và dev đợt 2 (p = 0,031).
- So với vector đơn thuần thì không bộ nào đạt p < 0,05.
- Nguồn: Mục 8.3.

**53. Lỗi nhầm phiên bản (thí nghiệm trong lab)**
- Thêm QĐ 3183 làm câu hỏi của khóa 2022 tụt từ hạng 1 xuống hạng 3.
- Sắp lại theo khóa áp dụng đưa câu này về hạng 1.
- Nguồn: `lab/README.md` Bài tập 3.

**54. Đáp án nằm ở điều khoản hiệu lực**
- Câu "B+, C+, D+ áp dụng từ khóa nào" cần Điều 2 của QĐ 3183, nhưng Điều này xếp hạng 47/118 khi truy hồi vector.
- Các mục sửa đổi Điều 9, 10 chứa ký hiệu "B+" nhiều hơn nên lấn lên trên.
- Nguồn: Mục 11.3.4, KC-3183-005.

## F. Sinh câu trả lời, prompt, từ chối và trích dẫn (55–66)

**55. Vì sao chạy LLM qua Ollama?**
- Dữ liệu không phải gửi qua dịch vụ AI bên thứ ba.
- Dùng qwen3:8b chạy trên Colab T4, request timeout 180 giây.
- Nguồn: Mục 3.1.3.

**56. Câu trả lời tất định**
- `temperature = 0` và `seed = 42`. Trước khi đặt hai tham số này, cùng một câu hỏi lần đầu bị từ chối, lần sau lại được trả lời "Không".
- Nguồn: Mục 4.5.1, `make_llm()`.

**57. Chế độ thinking của Qwen3**
- Tắt mặc định. Bật bằng `RAG_THINKING=1` thì tra bảng cẩn thận hơn nhưng chậm khoảng 4 lần.
- Đã có lần lộ chuỗi `/no_think` trong câu trả lời; giờ có kiểm thử chặn lỗi này.
- Nguồn: Mục 4.5.1, Mục 10.2.2.4.

**58. Các ràng buộc trong prompt**
- Chỉ dựa vào trích đoạn. Trích nguyên văn câu quy định trước khi kết luận. Không tự quy đổi thang điểm. Không có thông tin thì trả lời "không tìm thấy".
- Nguồn: `QA_PROMPT` trong `src/query_engine.py`.

**59. Lỗi nhầm thang điểm hệ 10 và hệ 4**
- Câu "A thì được bao nhiêu điểm hệ 10" được trả lời "4,0". Truy hồi đúng; lỗi do mục sửa đổi chỉ chứa bảng mà không ghi tên thang điểm.
- Cách sửa tạm là thêm chú giải miền vào prompt; phần này chưa đo riêng.
- Nguồn: Mục 4.5.2.

**60. Trích dẫn nguồn lấy từ metadata**
- `format_sources()` in "Nguồn: <văn bản> – Điều N" từ metadata của Node, không để LLM tự ghi.
- Lý do: trong lab, LLM ghi sai số Điều ở 4/12 câu, và chỉ 4/12 câu đúng cả nội dung lẫn số Điều.
- Nguồn: Chương 7, `lab/README.md` Bài tập 4.

**61. Vị trí trích dẫn tới dòng của file gốc**
- `vi_tri_goc()` trả về `data/processed/…md:<dòng>`. Kiểm thử xác nhận cả 118 Node đều trỏ đúng đoạn gốc.
- Số trang PDF bị mất ở bước làm sạch dữ liệu.
- Nguồn: Mục 7.4, `src/processed_loader.py`.

**62. Hai lớp từ chối câu ngoài phạm vi**
- Lớp 1: prompt cho LLM lối ra "không tìm thấy". Lớp 2: `similarity_cutoff` (có cài nhưng tắt, vì điểm thấp và sát nhau).
- Trên tập kiểm chứng: từ chối 18/20 câu ngoài phạm vi (đếm tự động).
- Nguồn: Chương 7, Mục 10.2.2.6.

**63. Chọn ngưỡng từ chối (thí nghiệm trong lab)**
- Ngưỡng 0,28 nằm giữa điểm 0,297 (câu có đáp án thấp nhất) và 0,266 (câu ngoài phạm vi cao nhất).
- Ngưỡng này chọn trên chính bộ câu đang dùng và hỏng ngay khi đổi cách chia.
- Nguồn: `lab/README.md` Bài tập 4.

**64. Từ chối quá tay**
- Phiên chạy đầu từ chối 52% câu. Sau khi đổi prompt và top-k thì còn 41%; hai thay đổi cùng lúc nên chưa tách được tác dụng.
- Cần tách từ chối đúng (câu ngoài phạm vi) khỏi từ chối sai (đáp án đã có trong ngữ cảnh).
- Nguồn: Mục 10.2.2.3–10.2.2.4.

**65. Không nhớ hội thoại**
- Câu hỏi nối tiếp như "còn kỹ sư?" bị từ chối.
- Hướng sửa: dùng CondensePlusContextChatEngine để viết lại câu hỏi dựa trên lịch sử.
- Nguồn: Mục 4.5.3, Mục 12.1.

**66. Câu trả lời không nêu khóa áp dụng**
- Trên tập kiểm chứng, KC-QC-025 và KC-QC-026 được trả lời theo bảng của QĐ 3183 (chỉ áp dụng từ khóa 2025) mà không nói rõ điều này.
- Thông tin khóa áp dụng chỉ được dùng để lọc, không có trong prompt.
- Nguồn: Mục 11.3.4.

## G. Đánh giá thực nghiệm (67–84)

**67. Recall@k và MRR**
- R@k là tỷ lệ câu có Node đúng trong k kết quả đầu. MRR là trung bình của 1/hạng của Node đúng đầu tiên.
- Nguồn: Mục 4.6.1, `eval/metrics.py`.

**68. nDCG@k**
- Giống Recall nhưng có tính vị trí. Với nhãn nhị phân thì nDCG@1 trùng R@1.
- Nguồn: Mục 4.6.1, Bảng 8.1.

**69. Khoảng tin cậy bootstrap**
- Lấy mẫu lại 2 000 lần. Bắt buộc phải có khi mỗi bộ chỉ có 10–31 câu.
- Ví dụ: R@1 của bộ 02 là 70% [40–100].
- Nguồn: `bootstrap_ci()`.

**70. Luật chấm theo cặp (văn bản, Điều)**
- Corpus có nhiều văn bản trùng số Điều. Bộ 01 nhận Quy chế 2021 hoặc mục QĐ 3183 sửa đổi chính Điều đó. Bộ 02 chỉ nhận QĐ 3183.
- Nguồn: `eval/luat_cham.py`, Mục 4.6.1.

**71. Điểm mù của luật chấm theo Điều**
- Node được tính đúng nếu thuộc đúng Điều, kể cả khi đoạn đó không chứa đáp án.
- Ví dụ trong lab: Q03 đạt R@1 nhưng đoạn truy hồi dừng ngay trước khoản chứa đáp án.
- Nguồn: `lab/README.md` Bài tập 4.

**72. Đối chiếu với RetrieverEvaluator của LlamaIndex**
- MRR do thư viện tính trùng với MRR tự viết ở cả 5 bộ (0,882; 0,900; 0,963; 0,813; 0,900).
- Nguồn: Mục 4.6.2.

**73. Tập dev và tập kiểm chứng**
- Tập dev có 91 câu (thêm 69 câu đợt 4) dùng để chỉnh hệ thống. Tập kiểm chứng có 60 câu, do người không chỉnh pipeline viết.
- Tập kiểm chứng chỉ chạy một lần sau khi đóng băng.
- Nguồn: Mục 4.6.4.

**74. Đóng băng cấu hình**
- `dong_bang.py` ghi sha256 của mã nguồn, fingerprint corpus, cấu hình và file câu hỏi. Script đòi code đã commit hết.
- `evaluate.py --tap-kiem-chung` chỉ chạy khi trạng thái hiện tại khớp manifest.
- Nguồn: `eval/dong_bang.py`, commit `08bdea5`.

**75. Kết quả trên tập kiểm chứng**
- R@1 50% (Quy chế 2021) và 62,5% (QĐ 3183), trong khi trên dev là 87% và 70%.
- Chia theo loại câu: khẩu ngữ không dấu 0/5, diễn đạt khác 1/8, tra bảng 6/6.
- Nguồn: Bảng 10.6, `eval/results/truy-hoi-kiem-chung.md`.

**76. Quá khớp trên tập dev**
- Tập dev gần như toàn câu viết chuẩn có dấu, nên không cho thấy điểm yếu với câu không dấu và câu diễn đạt khác.
- Bài học: tập dev phải có đủ các loại câu như tập kiểm chứng.
- Nguồn: Mục 11.2.

**77. Lỗi nhãn trong tập kiểm chứng**
- 12/32 câu đánh số Điều theo Thông tư 08/2021 chứ không theo bản SGU (từ Điều 12 trở đi lệch một số).
- Nếu sửa số Điều theo bản SGU thì R@1 là 72%, nhưng số chính thức vẫn giữ 50%.
- Nguồn: Mục 4.6.4, Mục 10.2.2.6.

**78. Cohen κ và giới hạn của nó**
- Hai người gán nhãn trùng 40/40, κ = 1,00, nhưng vẫn sai vì cùng dùng một nguồn.
- Đồng thuận cao không có nghĩa là nhãn đúng.
- Nguồn: `eval/results/do_dong_thuan.md`.

**79. Kiểm tra câu kiểm chứng trùng với câu dev**
- So 60 câu kiểm chứng với 229 câu dev, ngưỡng độ giống 0,75: 15 câu có câu dev gần giống, 2 cặp gần như nguyên văn.
- Nguồn: `eval/kiem_tra_trung.py`.

**80. Độ bao phủ corpus của bộ câu hỏi**
- 91 câu dev cũ chỉ hỏi tới 53/118 Node. Thêm dev đợt 4 nâng lên 102/118 Node (86%), phủ 20/20 văn bản.
- Nguồn: `eval/bao_phu.py`, Bảng 4.8.

**81. Rubric chấm câu trả lời hai mức**
- Hai nhãn đúng/sai. Câu trích sai Điều vẫn tính đúng nhưng được đánh dấu riêng ở cột `trich_dan_sai`.
- Lỗi được phân loại thành: nhan, thieu_van_ban, retrieval, rerank, synthesis.
- Nguồn: `docs/rubric-cham-tra-loi.md`.

**82. Kết quả chấm tay 99 câu dev**
- Người chấm: 93/99 đúng, 6 câu sai. Ba trong sáu câu sai là đọc sai bảng quy đổi tiếng Anh. Ngữ cảnh có đoạn đúng ở cả 99/99 câu.
- Nguồn: Mục 10.2.2.5.

**83. Chỉ số chấm tự động**
- `khop_su_kien` kiểm các con số của đáp án có xuất hiện trong câu trả lời không; bắt được 4/6 câu sai.
- Không dùng LLM làm giám khảo, vì model tự chấm câu trả lời của mình sẽ thiên lệch.
- Nguồn: `eval/cham_tu_dong.py`.

**84. Quy trình chấm tay và đối chiếu**
- Chấm trên trang `cham_tay.html`, nhãn AI được ẩn cho tới khi người chấm xong câu đó.
- `doi_chieu_cham.py` lập bảng chéo nội dung × nguồn, bảng loại lỗi và liệt kê câu hai người lệch.
- Nguồn: `eval/cham_tay.html`, `eval/doi_chieu_cham.py`.

## H. Kỹ nghệ phần mềm và tái lập (85–94)

**85. Cấu hình tập trung bằng dataclass**
- `RAGConfig` gom mọi tham số. Hàm `mo_ta()` ghi lại cấu hình vào kết quả đánh giá.
- Nguồn: `src/config.py`, Đoạn mã 3.4.

**86. Ghim phiên bản thư viện**
- `requirements.txt` ghim `llama-index-core==0.14.24` và các gói khác, để người khác cài lại vẫn ra đúng số.
- Nguồn: Bảng 3.1.

**87. Kiểm thử và CI**
- 80 kiểm thử. CI chỉ cài `llama-index-core` và `python-dotenv` (không torch, không model) và chạy phần offline.
- Có bước khóa quyền ghi `nltk_cache` để tránh lỗi trên runner.
- Nguồn: `tests/`, `.github/workflows/ci.yml`.

**88. Expected failure**
- Hai ca biên của bộ lọc phiên bản chưa xử lý được ghi thành `expectedFailure`, để lỗi đã biết không bị quên.
- Nguồn: `tests/test_phien_ban.py`, Mục 8.3.

**89. Model server và Colab**
- Embedding và reranker chạy qua HTTP (`src/model_server.py`). Colab mở URL công khai bằng Cloudflare quick tunnel.
- Client kiểm tra server đang chạy đúng model của profile. Tunnel không có xác thực, nên phải tắt runtime khi xong.
- Nguồn: `scripts/setup_server_v2.sh`, Mục 8.2.

**90. Khóa tái lập**
- `khoa_tai_lap()` ghi sha256 prompt, tên và digest LLM, fingerprint index và cấu hình vào từng câu.
- Chạy tiếp một lần chạy dở mà khóa đã khác thì script dừng.
- Nguồn: `src/query_engine.py`, Mục 10.2.2.5.

**91. Log thí nghiệm làm minh chứng**
- `make test-log` ghi log kèm mã commit và danh sách file chưa commit.
- `.gitignore` đã mở lại `eval/results/logs/**/*.log` để log được commit cùng kết quả.
- Nguồn: `Makefile`, `.gitignore`.

**92. Chạy lại để loại trừ lỗi hạ tầng**
- Trước khi tin kết quả tập kiểm chứng, nhóm chạy lại cấu hình chốt trên dev qua cùng server Colab và nhận lại đúng số cũ.
- Nguồn: `eval/results/logs/2026-10-31_kiem-chung/03_kiem_tra_server_tren_dev.log`.

**93. Kiểm kiểu bằng Pylance/pyright strict**
- Dự án cấu hình chế độ strict trong `.vscode/settings.json`; một số cảnh báo "unknown type" được tắt.
- Nguồn: `.vscode/settings.json`.

**94. Giao diện Gradio**
- Có nhật ký câu hỏi `questions_log.jsonl`, hiện nguồn kèm vị trí trong file, và các ô chọn bật/tắt rerank, lọc phiên bản.
- Nguồn: `app/app.py`.

## I. So sánh, mở rộng và bài học (95–100)

**95. LlamaIndex và LangChain**
- Dựng lại phần truy hồi bằng LangChain trên cùng dữ liệu cho kết quả trùng từng câu (25/31, 9/10…).
- Khác biệt giữa hai framework nằm ở mức trừu tượng; với LangChain phải tự viết lớp Embeddings.
- Nguồn: Mục 1.3.2, `eval/so_sanh_langchain.py`.

**96. Điểm ma sát khi dùng LlamaIndex thật**
- Reranker cố định 512 token; BM25 nằm ở gói riêng; refine dùng prompt tiếng Anh mặc định; SentenceSplitter đếm token tiktoken.
- Nguồn: Mục 1.3.3.

**97. Công cụ tra bảng quy đổi (agent)**
- Ba câu sai do đọc bảng có thể sửa bằng FunctionTool tra trực tiếp trên CSV quy đổi, thay vì để LLM tự đọc bảng.
- Nguồn: Mục 11.3.3, Mục 12.1.

**98. Tách truy hồi khỏi sinh để định vị lỗi**
- Nếu bước truy hồi không lấy được Node đúng thì đó là lỗi truy hồi. Nếu có Node đúng mà câu trả lời vẫn sai thì đó là lỗi sinh.
- Trên dev: 0/99 câu thiếu đoạn đúng, nên cả 6 câu sai đều thuộc tầng sinh.
- Nguồn: Bảng 11.2, `lab/README.md` Bài tập 4.

**99. Đánh giá trung thực**
- Giữ số chính thức 50% dù biết nhãn có lỗi. Ghi rõ những chỗ chưa có nhãn người. Khai báo phần dùng AI.
- Nguồn: Mục 10.2.2.6, Mục 11.4.

**100. Hướng phát triển ưu tiên**
- Thêm câu không dấu và câu diễn đạt khác vào tập dev; sửa nhãn tập kiểm chứng; công cụ tra bảng; nêu khóa áp dụng trong câu trả lời; chat engine có nhớ hội thoại; small-to-big.
- Nguồn: Chương 12.
