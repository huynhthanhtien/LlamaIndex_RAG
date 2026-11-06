# Hướng dẫn viết báo cáo cá nhân (khoảng 10 trang)

Báo cáo nhóm trả lời câu hỏi "hệ thống làm được gì". Báo cáo cá nhân trả lời câu hỏi khác: **bạn đã làm gì, làm
như thế nào, học được gì và có minh chứng nào**. Người chấm sẽ đối chiếu với git log, PR và Phụ lục A của báo cáo
nhóm, nên mọi câu trong báo cáo cá nhân phải truy được về một commit, một file hoặc một con số đã đo.

> Nếu giảng viên có mẫu báo cáo cá nhân riêng, theo mẫu đó; dùng tài liệu này để điền nội dung.

## 1. Quy tắc chung

1. **Chỉ viết việc của mình.** Việc làm chung thì ghi rõ phần của mình trong đó. Không chép nguyên đoạn báo cáo
   nhóm; được dẫn chiếu ("xem Mục 8.3 báo cáo nhóm").
2. **Mỗi việc một minh chứng**: mã commit, số PR, đường dẫn file, dòng log hoặc bảng số liệu. Việc không có commit
   (đọc tài liệu, sửa tay OCR, chấm tay, họp chốt nhãn) thì ghi vào nhật ký `docs/nhat-ky/<ten>.md` và dẫn tới đó.
3. **Số liệu lấy từ file kết quả**, ghi kèm ngày đo và file (ví dụ `eval/results/truy-hoi-kiem-chung.md`). Không
   làm tròn khác báo cáo nhóm.
4. **Viết cả cái sai.** Một lỗi của chính mình, phát hiện ra sao và sửa thế nào thường có giá trị hơn một trang liệt
   kê việc đã xong.
5. **Khai AI trung thực**: phần nào AI viết hoặc gợi ý, AI sai ở đâu. Khai thiếu nặng hơn khai thừa.
6. Tài khoản git `solozy` và `huynhthanhtien` là của Huỳnh Thanh Tiến (email commit); `phwkha` và "Phan Hữu Kha" là
   của Phan Hữu Kha. Ghi một lần trong báo cáo để người chấm đối chiếu được.

## 2. Định dạng

- A4, Times New Roman 13, lề 2–2,5 cm, giãn dòng 1,3 (giống báo cáo nhóm).
- Khoảng 10 trang nội dung, **không tính** bìa, mục lục, phụ lục. Một trang khoảng 450–500 chữ; bảng và hình đếm
  theo diện tích thực.
- Bảng/hình có chú thích "Bảng N: …", "Hình N: …"; đoạn mã ngắn (dưới 15 dòng), ghi file nguồn.
- Bìa: tên đồ án, Nhóm 08, họ tên, MSSV, vai trò (N1–N4), giảng viên, ngày nộp.

## 3. Khung báo cáo và số trang

| Mục | Nội dung | Trang |
|---|---|---|
| 1. Vai trò trong nhóm | Bạn phụ trách mảng nào, nhánh git nào, làm từ tuần nào đến tuần nào | 0,5 |
| 2. Bối cảnh ngắn | Bài toán RAG quy chế SGU trong 5–6 câu, chỉ đủ để hiểu phần việc của bạn; dẫn chiếu báo cáo nhóm | 0,5 |
| 3. Các việc đã làm | Mỗi việc một tiểu mục: vấn đề → cách làm → minh chứng → kết quả (số) → khó khăn | 4–5 |
| 4. Kiến thức kỹ thuật | Giải thích 1–2 cơ chế gắn trực tiếp với việc của bạn (xem gợi ý từng người) | 1,5 |
| 5. Một lỗi và bài học | Một sai sót thật của bạn hoặc trong phần bạn phụ trách: hiện tượng, nguyên nhân, cách phát hiện, đã/chưa sửa | 1 |
| 6. AI Disclosure cá nhân | Công cụ AI đã dùng, dùng vào việc gì, tỷ trọng, ít nhất 2 lần AI trả sai, nếu không có AI thì phần nào vẫn tự làm được | 1 |
| 7. Làm việc nhóm và tự đánh giá | Phối hợp với ai, qua PR/review nào; điểm mạnh, điểm cần cải thiện | 0,5–1 |
| 8. Định hướng bản thân | Kỹ năng học được dùng vào đâu; muốn học tiếp gì | 0,5–1 |
| Phụ lục | Nhật ký tuần (bảng Việc / File / Minh chứng / Giờ), danh sách commit | không tính |

### Mẫu một tiểu mục ở Mục 3

> **3.2 Gán nhãn độc lập 40 câu tập kiểm chứng (tuần 6)**
> *Vấn đề.* Tập dev đã dùng để chỉnh hệ thống nên số đo lạc quan; cần tập kiểm chứng có nhãn do người khác gán.
> *Cách làm.* Chỉ xem câu hỏi (`*_K1.json`), đọc văn bản trong `data/processed` và PDF, ghi Điều đúng…
> *Minh chứng.* commit `5747020`, `d4471f5`; PR #17, #19; `eval/test_kiem_chung_nhan_B.json`.
> *Kết quả.* Trùng 40/40 nhãn với người viết câu, κ = 1,00 (`eval/results/do_dong_thuan.md`).
> *Khó khăn.* …

### Mục 6 – AI Disclosure: viết thế nào

- Ghi theo việc, không theo cảm nhận: "Dùng AI để gợi ý regex tách heading; tự viết phần còn lại" tốt hơn "dùng AI
  một chút".
- Mỗi lần AI sai ghi đủ: mình hỏi gì, AI trả gì, sai ở đâu, phát hiện bằng cách nào (chạy test, đối chiếu PDF…),
  sửa ra sao. Lấy từ trải nghiệm thật; không có thì ghi "không ghi nhận", không bịa.
- Phần câu hỏi dev đợt 4 (69 câu) và trang chấm tay, lab, các hàm khóa tái lập/vị trí trích dẫn đã khai là có AI ở
  Bảng 11.4 báo cáo nhóm. Ai phụ trách các phần đó thì khai lại ở đây cho khớp.

## 4. Gợi ý nội dung cho từng thành viên

Danh sách dưới lấy từ git log và Phụ lục A báo cáo nhóm. **Tự kiểm và bổ sung** việc không có commit; xóa việc
không phải của mình.

### 4.1 Huỳnh Thanh Tiến (N1, tài khoản `solozy`, `huynhthanhtien`)

**Việc có minh chứng (chọn 4–6 việc quan trọng nhất, không kể hết):**
- Tuần 3–4: khởi tạo repo, hai profile cấu hình (`src/config.py`), RAG cơ bản, tiền xử lý Markdown hai tầng,
  `src/processed_loader.py`, fingerprint chỉ mục (`src/index_builder.py`), model server.
- Tuần 5: chạy LLM và model server trên Colab (`scripts/setup_server_v2.sh`), hybrid BM25, baseline, bootstrap và
  McNemar (`eval/metrics.py`), Gradio có nhật ký câu hỏi.
- Tuần 6: reranker đọc 2 048 token, lọc phiên bản (`src/phien_ban.py`), luật chấm, đo chốt cấu hình, so sánh
  LangChain, tính độ đồng thuận K3; merge PR #16–#21.
- Tuần 7: sửa CI, đo lại 12 cấu hình (Bảng 8.2), đánh giá câu trả lời 99 câu dev, dev đợt 4.
- Tuần 8: chấm tay 99 câu dev (`cham-tay-tien.csv`, 93/99 đúng); đóng băng và chạy tập kiểm chứng (commit
  `08bdea5`, R@1 50% / 62,5%).

**Mục 4 – kiến thức nên giải thích:** vì sao `SentenceTransformerRerank` cắt ở 512 token và cách đặt lại 2 048; hoặc
fingerprint chỉ mục (vì sao chỉ so tên model là không đủ).

**Mục 5 – lỗi nên phân tích:** số trên tập dev (87%) so với tập kiểm chứng (50%): quá khớp với câu có dấu, câu khẩu
ngữ 0/5. Hoặc lỗi rerank đẩy Điều gốc lên trên mục sửa đổi.

**Mục 6:** phần tỷ trọng AI cao nhất nằm ở mảng này (mã nguồn, dev đợt 4, lab, trang chấm). Khai rõ từng phần và
cách đã kiểm (`make test`, chạy lại số liệu).

### 4.2 Phan Hữu Kha (N2, tài khoản `phwkha`)

**Việc có minh chứng:**
- Tuần 3: `src/node_parser.py` tách văn bản theo Điều (commit `ebf8ecb`); sửa kiểm tra bộ nhớ trong
  `scripts/check_model_memory.py` (commit `350bb15`).
- Tuần 6 (PR #18):
  - D1 xác minh hiệu lực và metadata cho mọi văn bản đang nạp, ghi nguồn trong `_bao_cao_kiem_tra.md` (`50e73f0`);
  - D2 nạp đợt 3: hướng dẫn phúc khảo, tiết học, chuẩn đầu ra 2020 (`bfe96f9`);
  - D3 chép 5 bảng quy đổi chứng chỉ tiếng Anh ra CSV (`7bf3a27`);
  - D5 15 câu dev đợt 3 (`a54ea28`);
  - R6, R8, R12 phần báo cáo (`5e3bbf9`, `68cdcf0`, `5035ca2`).
- Tuần 7: Phụ lục A ghi "viết kiểm thử (ca biên lọc phiên bản, manifest đóng băng, chấm tự động)". **Git log không
  có commit nào của `phwkha` sau 16/10**: tìm lại PR hoặc commit tương ứng; nếu code được người khác commit hộ thì
  ghi rõ.

**Mục 4:** metadata hiệu lực trong front matter (`sua_doi`, `ap_dung_khoa_tu_theo_dieu`) được bộ lọc phiên bản dùng
thế nào; hoặc vì sao `node_parser.py` (regex trên văn bản thô) được thay bằng loader theo heading.

**Mục 5:** lần đối chiếu CSV với PDF phát hiện 24 ô sai biên ở TB 2366 (bất đẳng thức chặt bị chép thành khoảng có
hai đầu); hoặc OCR đọc số hiệu 3089 thành 3084.

### 4.3 Võ Thị Như Ý (N3, nhánh `nhuy`)

**Việc có minh chứng:**
- Tuần 3: bộ câu hỏi 01 (31 câu về Quy chế 2021, commit `6b82337`), đang là bộ đo chính ở Chương 4 và 8.
- Tuần 6 (PR #16, #21): K1 viết 40 câu tập kiểm chứng, 6 loại câu (`2b79aa3`, `418be41`); R2 sửa tham chiếu chéo,
  R4 cây thư mục (`835aa8d`); nhật ký `docs/nhat-ky/Nhu-Y.md` (`cede59b`).
- Tuần 7: viết và sửa báo cáo theo nhận xét tuần 6 (ghi phần cụ thể đã sửa).

**Mục 4:** vì sao cần tập kiểm chứng độc lập (quá khớp trên dev), và cách chia 6 loại câu đo được điểm yếu
(kết quả 31/10: khẩu ngữ 0/5, diễn đạt khác 1/8, hỏi thẳng 6/7).

**Mục 5 – nên viết:** 12/32 nhãn của bộ Quy chế 2021 đánh số Điều theo Quy chế mẫu của Bộ (Thông tư 08/2021) thay vì
bản SGU (từ Điều 12 lệch một số), và 3 đáp án (KC-QC-017, 024, 031) không có trong Quy chế SGU. Phân tích vì sao
xảy ra, ảnh hưởng (R@1 chính thức 50%, nếu đúng số Điều là 72%) và quy trình nên có (đối chiếu câu trích với
`data/processed` trước khi chốt). Đây là bài học có giá trị, viết thẳng thắn.

### 4.4 Trần Hà Thanh Thùy (N4, nhánh `ththuy-K2`)

**Việc có minh chứng:**
- Tuần 3: dữ liệu sổ tay sinh viên và bộ câu hỏi 02 (10 câu về nội dung QĐ 3183, commit `35d35df`).
- Tuần 6 (PR #17, #19): K2 gán nhãn độc lập 40 câu khi chỉ thấy câu hỏi, viết 20 câu ngoài phạm vi kèm hành vi mong
  đợi (6 ngoài hẳn, 8 sát biên, 6 câu bẫy), gán phạm vi cho 56 câu phiên hỏi đáp cũ (`779b163`, `5747020`,
  `d4471f5`).
- Tuần 7: viết và sửa báo cáo theo nhận xét tuần 6 (ghi phần cụ thể).

**Mục 4:** Cohen's κ (công thức, p_e) và giới hạn của nó; hoặc cách thiết kế câu ngoài phạm vi (sát biên, bẫy).

**Mục 5 – nên viết:** κ = 1,00 nhưng không phát hiện được lỗi đánh số Điều, vì hai người cùng dùng một nguồn
(Thông tư 08/2021) chứ không phải bản SGU: đồng thuận cao không có nghĩa là nhãn đúng. Kết quả 31/10 của các câu
bạn viết: hệ thống từ chối 18/20 câu ngoài phạm vi; 2 câu bẫy (KC-NG-016, 020) được trả lời và đính chính, chờ người
chấm.

## 5. Kiểm tra trước khi nộp

- [ ] Mỗi việc ở Mục 3 có ít nhất một minh chứng (commit/PR/file) và khớp dòng của mình trong Bảng A.1.
- [ ] Số liệu trùng với báo cáo nhóm và có ghi file nguồn, ngày đo.
- [ ] Có ít nhất một lỗi/sai sót được phân tích thật (Mục 5).
- [ ] AI Disclosure khớp Bảng 11.4 báo cáo nhóm; có ít nhất 2 lần AI sai, hoặc ghi rõ "không ghi nhận".
- [ ] Không có đoạn chép nguyên từ báo cáo nhóm hay từ báo cáo của thành viên khác.
- [ ] Khoảng 10 trang nội dung; bìa có MSSV và vai trò; xuất PDF và kiểm lại bảng không bị tràn trang.
