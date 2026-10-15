# Phân công tuần này: 4 người, làm từ nhánh `main`

> Tổng hợp từ `docs/de_xuat_xu_ly_nhan_xet.md` (nhận xét mục 2–10), `docs/ke_hoach_them_du_lieu_dao_tao.md` (đợt 3 và kỹ thuật T1/T2/T6),
> `docs/task-tap-kiem-chung-va-phan-cong.md` (tập kiểm chứng, chưa bắt đầu) và kết luận thí nghiệm rerank ngày 13/10
> (`eval/results/logs/2026-10-13_dot2/`). Trạng thái được kiểm lại trên repo ngày 15/10/2026.
>
> Tên người để trống, trưởng nhóm điền vào bảng ở mục 1.

---

## 0. Điểm xuất phát và quy trình nhánh

`main` (commit `af3cc2e`) đã có đủ code và dữ liệu đợt 1–2: 17 văn bản, 108 Node, bộ dev `eval/dev_questions_dot{1,2}.json`,
log thí nghiệm `eval/results/logs/2026-10-13_dot2/`. `make test`: 36 test, OK (skipped=10).

1. Mỗi người tách nhánh riêng **từ `main` mới nhất**:

   ```bash
   git switch main
   git pull
   git switch -c <ten-nhanh>
   ```

2. Không ai push thẳng lên `main`. Mỗi việc mở **một PR riêng về `main`**, do người làm việc đó đứng tên. PR này cũng là minh chứng cho Phụ lục A (nhận xét mục 10).
3. Khi `main` có PR mới được merge, cập nhật nhánh của mình bằng `git pull origin main` (merge), sửa xung đột ngay trong nhánh của mình.
4. Trước khi mở PR: chạy `make test`. Với nhánh sửa báo cáo, chạy `make report` và báo cáo phải build không lỗi.

**Quy ước tên nhánh:** `<ten>/<ma-viec>-<mo-ta-ngan>`, ví dụ `khaph/D1-manifest-hieu-luc`.

---

## 1. Bảng phân công tổng

| Người | Vai trò | Việc chính | Nhánh gợi ý | Ràng buộc |
|---|---|---|---|---|
| **N1** ……… | Giữ code, đo đạc | C1–C5, R7, R9, R10 | `…/C-rerank-loc-phien-ban`, `…/R-ket-qua` | Chờ manifest D1 trước khi làm C2 |
| **N2** ……… | Dữ liệu | D1–D5, R6, R8 | `…/D-manifest`, `…/D-dot3`, `…/R-minh-chung` | D1 phải xong sớm (ngày 2), vì C2 cần nó |
| **N3** ……… | Viết câu kiểm chứng (A) + dọn báo cáo | K1, K3, R2, R4, R11 | `…/K-cau-hoi-A`, `…/R-repo-thamchieu` | **Quy tắc độc lập** (mục 4) |
| **N4** ……… | Gán nhãn độc lập (B) + dọn báo cáo | K2, K3, R1, R3, R5, D4 (đối chiếu) | `…/K-nhan-B`, `…/R-giong-van` | **Quy tắc độc lập** (mục 4) |
| **Cả 4** | | R12 (Phụ lục A, nhật ký, hướng phát triển cá nhân) | mỗi người một PR nhỏ | |

**Vì sao chia như vậy:**
- N3 và N4 viết tập kiểm chứng nên **không được xem kết quả hoặc chạy hệ thống** cho đến khi đóng băng. Vì vậy hai người chỉ nhận phần báo cáo về cấu trúc và câu chữ, không nhận phần có số liệu.
- Phần nào cần chạy hệ thống thì giao cho N1 và N2: đo, thí nghiệm, LangChain, cập nhật bảng kết quả.
- Mỗi người sửa một nhóm file `.tex` riêng (mục 6) để ít xung đột khi merge.

---

## 2. Nhóm C: code và pipeline (N1)

### C1. Sửa lỗi reranker chỉ đọc 512 token

- **Vấn đề:** `SentenceTransformerRerank` của LlamaIndex đặt cứng `max_length=512`, trong khi `AITeamVN/Vietnamese_Reranker` hỗ trợ 8192.
  Có 30/108 Node (28%) dài hơn 512 token, đúng các Node bảng và Điều dài. Phần bị cắt chứa dòng cần tìm, nên điểm rerank bão hòa ở 0 hoặc 1.
  Chi tiết ở `eval/results/logs/2026-10-13_dot2/11_kiem_tra_rerank.md`.
- **File:** `src/config.py` (thêm `reranker_max_length: int = 2048` cạnh `reranker_top_n`, dòng 60–63), `src/retriever.py`
  (`make_local_reranker()`, dòng 106), `src/model_server.py` (`load_reranker()`, dòng 56; thêm biến môi trường `RERANK_MAX_LENGTH`).
- **Cách làm:** truyền `max_length` khi tạo `SentenceTransformerRerank`. Kiểm bằng cách in `reranker._model.max_length` (hoặc thuộc tính tương đương) sau khi nạp.
  Ghi giá trị này vào `as_dict()` của config để log thí nghiệm có ghi lại.
- **Xong khi:** `make test` xanh. Chạy lại `eval/evaluate.py --cau-hinh rerank` cho R@1 khớp số "rerank (2048)" đã đo ngày 13/10
  (tổng 64/76 = 84,2%), sai lệch không quá 1 câu.

### C2. Lọc phiên bản trước khi rerank (kỹ thuật T1 + T2), sau đó bật rerank mặc định

- **Vấn đề:** rerank chấm theo độ khớp nội dung, nên khi bản gốc và bản sửa đổi giống nhau thì bản gốc thắng. Ví dụ:
  - QC 2021 Điều 7 bản gốc được 0,97, cao hơn mục sửa đổi của QĐ 3183 (0,84).
  - CV 3248/2018 (100.000đ) đứng trước QĐ 898/2025 (150.000đ).

  Hậu quả: bộ 02 tụt từ 90% xuống 50%. Nhầm phiên bản/khóa là loại lỗi phổ biến nhất (46% số câu trượt top-1, xem `08_phan_tich_loi.md`).
- **Phụ thuộc:** cần front matter `tinh_trang`, `bi_sua_doi_boi`, `thay_the`, `ap_dung_khoa_tu/den` đã điền đúng (việc **D1** của N2).
  Trong lúc chờ, viết code với dữ liệu giả trong unit test.
- **File:**
  - `src/processed_loader.py` dòng 105: hiện chỉ nhận `so_hieu`, `ngay_ban_hanh`, `tinh_trang`, `nhom`. Thêm `bi_sua_doi_boi`, `thay_the`, `ap_dung_khoa_tu`, `ap_dung_khoa_den`.
  - `src/retriever.py`: thêm một bước lọc trước reranker. Có hai cách:
    - `MetadataFilters` khi truy hồi, để loại `tinh_trang in {het_hieu_luc, bi_thay_the}`.
    - Một `BaseNodePostprocessor` tự viết, đặt **trước** reranker. Khi lấy được Node gốc có `bi_sua_doi_boi`, nó kéo kèm Node sửa đổi tương ứng (T2).
- **Lưu ý:** không loại Node gốc của QC 2021 chỉ vì có vài Điều bị sửa. Chỉ hạ hoặc loại **đúng các Điều** đã bị QĐ 3183 sửa, theo `sua_doi_dieu`.
- **Bật mặc định:** sau khi lọc chạy đúng, đặt `use_rerank=True`, `reranker_top_n=3` cho profile `server`.
  Cập nhật comment dòng 60 trong `src/config.py`, vì câu "rerank làm giảm Recall@1" đã không còn đúng.
- **Xong khi:** có unit test mới trong `tests/` cho bộ lọc. Bộ 02 với rerank quay về ít nhất 80% R@1, đồng thời không mất phần tăng của dev đợt 2 (14/15).

### C3. Đo lại để chốt cấu hình

- Dựng server Colab bằng `scripts/setup_server_v2.sh`. **Tắt runtime khi không dùng**, vì server không có xác thực.
- Chạy và lưu log vào `eval/results/logs/<ngay>_chot-cau-hinh/`:
  - `make eval` (vector, rerank, hybrid, hybrid+rerank) **trên bộ dev**: 01, 02, dev đợt 1, 2 và đợt 3 nếu D5 đã xong.
  - `make test-llm`.
  - Câu trả lời cho dev đợt 1–2 với `top_n=3` và `top_n=5` (việc chưa đo được hôm 13/10 vì Colab tắt).
- Chấm câu trả lời theo cách đã làm trong `eval/results/tra-loi-dev-dot1-rerank3.md`: đúng / một phần / sai / trích sai văn bản.
- **Xong khi:** có bảng "cấu hình chốt" (embedding, top_k, rerank, top_n, lọc phiên bản) kèm số. Bảng này dùng cho R9.
- **Không** chạy trên tập kiểm chứng ở bước này. Tập kiểm chứng chỉ chạy một lần, ở K3.

### C4. Sửa luật chấm

- **File:** `eval/evaluate.py` dòng 43–72 (`dung_bo_01`, `dung_bo_02`, `dung_bo_dev`).
- **Vấn đề:**
  - Bộ 02 chỉ nhận Node sửa đổi Điều 9, trong khi mục sửa đổi Điều 10 cũng chứa bảng B+.
  - Luật chấm đang dựa vào tiền tố tên file.
- **Cách làm:**
  - Đổi sang chấm theo cặp `(nguon/so_hieu, dieu|muc)`.
  - Cho phép một câu có danh sách nhiều nhãn đúng (`dieu_dung` nhận cả list).
  - Giữ tương thích với JSON cũ có `dieu_dung` là chuỗi, vì tập kiểm chứng K1/K2 dùng định dạng này.
- **Xong khi:** `tests/test_metrics.py` có ca kiểm cho câu nhiều nhãn. Ghi rõ luật chấm của từng bộ ở đầu file, để R9 chép vào chú thích bảng.

### C5. Hybrid BM25 cho tên chứng chỉ (kỹ thuật T6, rẻ)

- **Giả thuyết** (kế hoạch, mục 6): IELTS, TOEIC, PTE, VSTEP và số hiệu văn bản là token hiếm, đúng chỗ BM25 mạnh.
  Khi corpus đã có các bảng quy đổi, hybrid có thể có ích, khác với kết luận cũ đo trên 54 Node.
- Dùng luôn số của C3 (cấu hình `hybrid` và `hybrid+rerank`), tách riêng kết quả dev đợt 2. Viết 1 đoạn kết luận: giữ hay bỏ hybrid.

---

## 3. Nhóm D: dữ liệu (N2)

### D1. Xác minh hiệu lực và điền metadata phiên bản (làm trước tiên, xong trong 2 ngày)

- **Ở đâu:** front matter YAML đầu mỗi file `data/processed/01_quy_che_dao_tao/*/*.md`. Các khóa `so_hieu`, `ngay_ban_hanh`, `tinh_trang`, `bi_sua_doi_boi` đã có sẵn.
  Hiện `ngay_ban_hanh` mới ghi năm, và nhiều file để trống `bi_sua_doi_boi`.
- **Cần điền cho mọi văn bản đang nạp:**

  | Khóa | Ý nghĩa | Ví dụ |
  |---|---|---|
  | `so_hieu` | Nhập tay và đối chiếu với PDF, vì OCR từng đọc 3089 thành 3084 | `898/QĐ-ĐHSG` |
  | `ngay_ban_hanh` | Đủ ngày/tháng/năm, định dạng `YYYY-MM-DD` | `2025-…` |
  | `tinh_trang` | `con_hieu_luc` / `bi_sua_doi` / `bi_thay_the` / `het_hieu_luc` | |
  | `bi_sua_doi_boi`, `sua_doi`, `thay_the` | Số hiệu văn bản liên quan; danh sách nếu có nhiều | QC 2021 `bi_sua_doi_boi: ["3183/QĐ-ĐHSG"]` |
  | `ap_dung_khoa_tu`, `ap_dung_khoa_den` | Khóa tuyển sinh áp dụng (bắt buộc cho nhóm `2_quy_doi_tieng_anh`) | 2366: `…–2021`; 2626: `2022–2023`; 2101: `2024–` |

- **Các văn bản phải xác minh hiệu lực** (đang đánh dấu "(?)" trong kế hoạch, mục 1):
  - `CV_3248_001_khieunai` (2018): lệ phí phúc khảo 100.000đ mâu thuẫn với QĐ 898/2025 (150.000đ). Nhiều khả năng đã bị 898 thay thế phần này.
  - `QD898…`: Điều 3 thay thế QyĐ 3089/2020. Ghi `thay_the: ["3089/…"]`.
  - `HD-Quy trinh phuc khao…`: căn cứ vào 3089 (đã bị thay thế), nên cần kiểm tra quy trình còn dùng không.
  - `ChienLuoc_001`: căn cứ VBHN 17/2014.
  - Nhóm `4_xet_tot_nghiep` (5 tệp): xác định văn bản nào mới nhất và còn hiệu lực.
- **Nguồn xác minh:** đọc phần "căn cứ" và "điều khoản thi hành" trong PDF gốc ở `data/raw/`, trang web Phòng Đào tạo SGU. Ghi nguồn và ngày truy cập vào `_bao_cao_kiem_tra.md` của từng thư mục.
- **Xong khi:** mọi file đang nạp có đủ các khóa trên. Có bảng tóm tắt "văn bản → hiệu lực → căn cứ xác minh" trong PR. Báo N1 ngay khi merge để làm C2.

### D2. Nạp đợt 3

| Văn bản (`data/raw/01_quy_che_dao_tao/…`) | Định dạng | Cách xử lý |
|---|---|---|
| `3_…/HD-Quy trinh phuc khao bai thi ket thuc hoc phan.pdf` (bản `__khoa_luat` trùng, bỏ) | F6: quy trình theo Bước, dạng bảng | OCR 300–400 dpi, `--psm 6`. Chép tay bảng các bước. `clean_md --kieu buoc` |
| `5_…/02.-Tiethoc_phonghoc.pdf` | F4: bảng ca/tiết/giờ, có lớp chữ | `pdftotext -layout` (bản mặc định rã bảng thành từng ô một dòng), sau đó sửa tay thành bảng Markdown |
| `4_xet_tot_nghiep/` | F3 + F4 | **Chỉ nạp sau khi D1 xác định được văn bản còn hiệu lực** (ứng viên: `TB_ChuanDauRa_2020.pdf`). Bản cũ để làm đối chứng, không nạp |

- **Quy trình:** `scripts/extract_to_md.py` → `data/ocr/…` → `scripts/clean_md.py` → `data/processed/…`. Đọc lại toàn bộ bản processed và so với PDF.
- **Không nạp:** QĐ 736 và `DHSG_quy-dinh-thoi-gian-toi-da…` (xung đột với QC 2021 Điều 2, chỉ dùng làm ca kiểm thử xung đột), `Quy dinh ve cong tac to chuc thi hoc ki.pdf` (là 3089, đã bị thay thế).
- **Xong khi:** `make test` xanh; số Node trong index bằng số Node từ loader. R@1 dev của các nhóm câu cũ không tụt quá 5 điểm. Nếu tụt, ghi Node nào chen lên top-1.

### D3. CSV bảng quy đổi (chuẩn bị cho kỹ thuật T5)

- Chép các bảng quy đổi chứng chỉ → điểm từ 2366, 2451, 2626, 2101, 2567 sang `data/bang_quy_doi/<so_hieu>.csv`, mỗi bảng một file.
  Cột gợi ý: `chung_chi, muc_tu, muc_den, hoc_phan, diem, ap_dung_khoa_tu, ap_dung_khoa_den, nguon_trang`.
- CSV vừa là đáp án exact-match cho câu dev F4, vừa là dữ liệu cho `FunctionTool` tra bảng sau này.

### D4. Đối chiếu bảng (người thứ hai: N4)

- N4 đối chiếu từng dòng của CSV D3 và các bảng Markdown trong `2_quy_doi_tieng_anh/` với PDF gốc. Ghi kết quả "đã đối chiếu, sửa X ô" vào PR của N2.
- Việc này chỉ đọc PDF và CSV, không chạy hệ thống, nên không vi phạm quy tắc độc lập.

### D5. Câu dev đợt 3

- Viết 10–15 câu vào `eval/dev_questions_dot3.json`, cùng định dạng với `dev_questions_dot2.json`. Phân bổ:
  - Bước và thời hạn phúc khảo.
  - Giờ của tiết/ca.
  - Điều kiện tốt nghiệp/chuẩn đầu ra (nếu đã nạp).
  - 2–3 câu xung đột phiên bản: thời gian tối đa (QC 2021 so với QĐ 736), lệ phí phúc khảo (3248 so với 898).
- Đây là bộ **dev**: được xem kết quả và được chỉnh hệ thống theo nó.

---

## 4. Nhóm K: tập kiểm chứng chống overfit (N3 = A, N4 = B)

Hướng dẫn chi tiết, kèm định dạng JSON, script kiểm trùng và tính kappa, đã có ở `docs/task-tap-kiem-chung-va-phan-cong.md`, mục 3–5.
Phần dưới chỉ tóm tắt và cập nhật theo tình hình mới.

**Quy tắc độc lập** (giữ cho tới khi đóng băng):
- Không mở `eval/test_questions_0*.json`, `eval/dev_questions_*.json`, `eval/results/*`, nhật ký Gradio.
- Không chạy Gradio, `pipeline.py` hay `make eval`.
- Chỉ đọc văn bản trong `data/processed/01_quy_che_dao_tao/` hoặc PDF trong `data/raw/`.
- Không xem PR C1–C5 và R7, R9, R10 của N1, vì các PR này có số liệu.

| Việc | Người | Sản phẩm |
|---|---|---|
| **K1** | N3 (A) | 40 câu trong phạm vi, mỗi câu có `dieu_dung` và câu trích nguyên văn. Phân bổ 6 loại câu theo mục 3.1 của file hướng dẫn. **Cập nhật:** phạm vi mở rộng ra 17 văn bản đã nạp. Khoảng 25 câu từ QC 2021 + QĐ 3183, khoảng 15 câu từ các văn bản đợt 1–2 (hoãn thi, thi học kỳ, bảng điểm, bản sao, CVHT, quy đổi tiếng Anh theo khóa) → `eval/test_kiem_chung.json` |
| **K2** | N4 (B) | (1) Gán nhãn độc lập 40 câu của A mà không xem nhãn của A. (2) Viết 20 câu ngoài phạm vi: ngoài hẳn, sát biên (điểm rèn luyện, học bổng: chủ đề CTSV chưa nạp), câu bẫy → `eval/test_kiem_chung_ngoai.json`. (3) Gán `pham_vi` cho 56 câu cũ → `eval/results/nhan_pham_vi_cau-hoi01.csv` |
| **K3** | N3 + N4 | Họp đối chiếu nhãn, tính Cohen's kappa → `eval/results/do_dong_thuan.md`. Đóng băng: ghi sha256 của các file JSON cùng ngày đóng băng, merge PR. **Sau đó** N1 chạy `make eval` trên tập kiểm chứng **đúng một lần**, với cấu hình đã chốt ở C3 |

**Thứ tự:** K3 phải làm **sau** C3. Hệ thống phải chốt cấu hình trước, rồi mới chạy test. Nếu chạy test xong mà còn chỉnh hệ thống thì tập này trở thành tập dev.

---

## 5. Nhóm R: báo cáo (xử lý nhận xét mục 2–10)

Chi tiết từng chỗ cần sửa có trong `docs/de_xuat_xu_ly_nhan_xet.md`, theo đúng số mục. Bảng dưới ghi rõ người làm và file `.tex`.

| Mã | Nhận xét | Người | Việc cụ thể | File chính |
|---|---|---|---|---|
| **R1** | Mục 5.1: giọng "bản trước/bản mới" | N4 | Còn 24 cụm như "bản trước", "Bản mới", "bản này", "bản đầu". Viết lại thành mô tả hệ thống hiện tại; dồn lịch sử thay đổi vào Bảng 10.3 và Phụ lục A. Danh sách file:dòng ở tài liệu đề xuất, mục 5.1 | `03`, `04`, `05`, `06`, `10`, `11`, `12`, `p1-01` |
| **R2** | Mục 4: tham chiếu chéo | N3 | (1) Xóa các file `.aux` cũ (`report/chapters/*.aux`, nhất là `05-danh-gia.aux`). (2) Sửa 4 `\ref` trỏ sai nghĩa: `loi-mo-dau.tex:52` → thêm `\label` cho mục 11.1 rồi trỏ tới đó; `03:54` → `sec:danh-gia-thuc-nghiem` + `tab:recall`; `p1-01:243` → `sec:hybrid`; `07:19` → giữ hoặc trỏ `tab:top-k`. (3) Build lại `main.pdf` và sinh lại `main.docx` từ bản LaTeX mới (bản hiện có là của 9–10/10, mang số mục cũ) | `loi-mo-dau`, `03` (chỉ dòng 54, phần `\ref`), `p1-01:243`, `07` |
| **R3** | Mục 5.2–5.4: kế hoạch 12 tuần, lỗi ký tự, công thức | N4 | Theo tài liệu đề xuất, mục 5.2–5.4 | theo danh sách trong đề xuất |
| **R4** | Mục 6: mô tả repo mâu thuẫn | N3 | Sinh lại cây thư mục 3.3.1 từ `git ls-files`. Sửa mô tả `test_ocr.py` (3.3.3), Bảng 3.2 (thiết bị embedding), Bảng 3.3 (kiểm thử = Tầng 2), Bảng 11.1 và Phụ lục C ("Đạt 6/6" → ghi rõ phần đánh giá câu trả lời) | `03`, `11`, phụ lục C |
| **R5** | Mục 9: hai mục "(Chưa làm)" | N4 | Mục 2.2 (`p1-02-vi-the.tex:17`): số GitHub stars và contributors của `run-llama/llama_index`, lượt tải PyPI của `llama-index-core` (pypistats), kèm số tương ứng của LangChain và Haystack, **ghi ngày truy cập** | `p1-02` |
| **R6** | Mục 8.1: placeholder | N2 | Thay `<nguyên văn Điều 9>` (`05-node-parser.tex:35`) bằng Node thật in từ loader | `05` (chỉ dòng 35) |
| **R7** | Mục 7: chunk/embedding | N1 | Đưa bảng số đo độ dài Node vào báo cáo (đề xuất, mục 7). Sửa câu về `MAX_TU` (đếm theo từ, splitter đếm theo token). Ghi chú profile local cắt đuôi Node. Đo số lượt gọi LLM thực tế khi top-10 | `04` |
| **R8** | Mục 8.2, 8.4, 8.5: minh chứng | N2 | (1) Bảng độ trễ, token vào/ra, token/s lấy từ log Ollama (`eval_count`, `prompt_eval_count`, `eval_duration`), với `thinking` bật và tắt. (2) Ví dụ từ chối ngoài corpus có kèm Node truy hồi được. (3) Ghi lỗi `/no_think` rò ra đầu ra và cách xử lý | `07`, `10` |
| **R9** | Mục 9: đánh giá thực nghiệm | N1 | Bỏ cột nDCG@1 ở `08-nang-cao.tex:57` (trùng R@1 về toán học), thay bằng nDCG@3 hoặc R@5. Ghi luật chấm trong chú thích Bảng 4.4 và 8.1 (lấy từ C4). Tách hai cột dev và test (test điền sau K3) | `04`, `08` |
| **R10** | Mục 9: LangChain 1.3.2 | N1 | Cách tối thiểu: dựng lại **chỉ phần truy hồi** bằng LangChain trên cùng Node và embedding, dùng `InMemoryVectorStore`. So số dòng code, cách xử lý metadata khi embed, cách lưu chỉ mục và R@k (phải bằng nhau nếu cài đúng). Nếu không kịp: đổi tiêu đề thành "So sánh theo tài liệu" và ghi rõ chưa dựng thử | `p1-01:214` |
| **R11** | Cập nhật nội dung theo hệ thống mới | N3 | Viết phần **mô tả** (không có số) cho dữ liệu đợt 1–3: danh sách văn bản, 7 định dạng F1–F7, cách xử lý bảng và văn bản theo khóa. Lấy từ `docs/ke_hoach_them_du_lieu_dao_tao.md`, mục 1–2. **Số liệu kết quả do N1 điền ở R9** | `04` hoặc `09` (thống nhất với N1) |
| **R12** | Mục 10: Phụ lục A | **Cả 4** | (1) Mỗi người ghi nhật ký cá nhân theo mẫu ở `task-tap-kiem-chung-va-phan-cong.md`, mục 7.1, kèm link PR/commit. (2) Điền dòng của mình trong Bảng A.1 (`appendices/a-nhat-ky-tuan.tex`). (3) Đoạn "hướng phát triển" cá nhân (`12-huong-phat-trien.tex:46`). (4) Nhật ký dùng AI (`11-danh-gia-nhin-lai.tex:97`) | `a-nhat-ky-tuan`, `11`, `12` |

**Nhận xét mục 2** (kiến thức miền nằm trong prompt): giải quyết bằng C2 và D1. Khóa áp dụng và quan hệ sửa đổi được chuyển từ prompt sang metadata.
Sau C3, N1 viết một đoạn A/B trong báo cáo: kết quả khi bỏ phần kiến thức miền khỏi prompt so với khi giữ.

---

## 6. Tránh xung đột khi sửa `.tex`

| File | Người sửa chính | Người khác chỉ sửa |
|---|---|---|
| `03-moi-truong-kien-truc.tex` | N3 (R4) | N4 sửa câu chữ dòng 9 và 54; N3 sửa `\ref` dòng 54. **PR của N4 merge trước** |
| `04-cong-nghe-cot-loi.tex` | N1 (R7, R9) | N4 sửa câu chữ (R1), N3 phần mô tả dữ liệu (R11) |
| `05-node-parser.tex` | N4 (R1) | N2 chỉ dòng 35 (R6) |
| `08-nang-cao.tex` | N1 | |
| `p1-01-gioi-thieu-llamaindex.tex` | N1 (R10) | N3 dòng 243, N4 dòng 162 |
| `a-nhat-ky-tuan.tex` | mỗi người một dòng | |

**Thứ tự merge báo cáo:** R1 và R3 (giọng văn) → R2 và R4 → R6, R7, R8, R10, R11 → R9 (số liệu cuối cùng) → R12 → build PDF/DOCX lần cuối (N3).
Khi nhánh của mình bị lệch, cập nhật bằng `git pull origin main` rồi sửa xung đột trong nhánh của mình.

---

## 7. Lịch gợi ý (7 ngày làm việc)

| Ngày | N1 (code) | N2 (dữ liệu) | N3 (A) | N4 (B) |
|---|---|---|---|---|
| 1 | C1, C4 | D1 | K1: viết câu | K2: câu ngoài phạm vi, `pham_vi` |
| 2 | C2 (code + test với dữ liệu giả) | D1 xong → báo N1; bắt đầu D3 | K1 | R1 |
| 3 | C2 với manifest thật | D2 (phúc khảo, tiết học) | K1 xong, gửi bản chỉ có câu hỏi cho B; R2 | K2: gán nhãn độc lập; D4 |
| 4 | C3 đo lại (Colab), C5 | D2 (tốt nghiệp), D5 | R4, R11 | K2 xong; R3, R5 |
| 5 | Chốt cấu hình; R7, R10 | R6, R8 | **K3: họp chốt nhãn, kappa, đóng băng** | **K3** |
| 6 | Chạy tập kiểm chứng **1 lần**; R9 | Đọc lại R9 | Viết đoạn kết quả kiểm chứng (từ đây được xem số) | Như N3 |
| 7 | R12 | R12 | R12; build PDF/DOCX cuối | R12 |

---

## 8. Định nghĩa "xong" cho cả tuần

- [x] Đợt 1–2 đã có trên `main`.
- [ ] Đợt 3 đã nạp, hoặc ghi rõ lý do chưa nạp văn bản nào.
- [ ] Mọi văn bản đang nạp có metadata hiệu lực và khóa áp dụng đã xác minh.
- [ ] Reranker đọc 2048 token, có lọc phiên bản, cấu hình mặc định đã chốt và có số đo kèm theo.
- [ ] Tập kiểm chứng đã đóng băng (có hash, kappa) và chạy đúng một lần. Báo cáo có hai cột dev và test riêng.
- [ ] Không còn cụm "bản trước/bản mới", không còn `\chualam{…}` (hoặc mỗi chỗ còn lại có lý do), không còn placeholder.
- [ ] PDF và DOCX build lại từ LaTeX mới nhất, tham chiếu chéo đúng.
- [ ] Phụ lục A có dòng của cả 4 người, mỗi dòng có link PR đứng tên chính người đó.
