# Kế hoạch: thêm dữ liệu Đào tạo (nhiều định dạng) → cải tiến → chốt hệ thống

> Ngày 11/10/2026. Phạm vi: **chỉ nhóm `data/raw/01_quy_che_dao_tao/`** (48 PDF + 1 docx), tức dữ liệu Đào tạo.
> Không gồm CTSV, CTĐT hay biểu mẫu. Tài liệu này đi sâu hơn mục "Lớp A/B" của
> [`phan_loai_tai_lieu_va_huong_giai_quyet.md`](phan_loai_tai_lieu_va_huong_giai_quyet.md), dựa trên việc **mở
> từng tệp ra xem** (`pdftotext` cho tệp có lớp chữ, OCR thử 1–2 trang đầu cho tệp scan; kết quả OCR thử chỉ để
> trong scratchpad, không ghi vào `data/`). Code đề xuất đã có ở
> [`de_xuat_code_cai_tien_pipeline.md`](de_xuat_code_cai_tien_pipeline.md) (ĐX-3, ĐX-4, ĐX-5, ĐX-8). Tài liệu này
> không lặp lại phần đó.

---

## 0. Kết luận ngắn

1. Trong 49 tệp Đào tạo, sau khi bỏ bản trùng, bản hết hiệu lực và biểu mẫu, còn khoảng **15 văn bản mới** cho
   sinh viên đại học chính quy và **4 văn bản hệ khác** (vừa làm vừa học, liên thông, thạc sĩ, tiến sĩ). Thêm vào
   6 văn bản đang có, dự kiến khoảng **150–220 Node**.
2. Khó khăn chính không nằm ở số lượng mà ở chỗ **có 7 định dạng khác nhau** (§2). Bộ cắt hiện tại chỉ hiểu
   *Chương → Điều → mục sửa đổi*, tức chỉ 1 trong 7 định dạng.
3. Hai định dạng **rủi ro nhất** cũng là hai định dạng **sinh viên hỏi nhiều nhất**:
   - **Bảng quy đổi chứng chỉ ngoại ngữ (F4).** OCR làm hỏng số trong bảng: "§ § §" thay cho "8 8 8", "I0" thay cho
     "10", "IBLTS" thay cho "IELTS". Mà đáp án chính là các con số này.
   - **Chuỗi văn bản bổ sung/thay thế theo khóa tuyển sinh (F5).** Quy đổi tiếng Anh có 5 văn bản, mỗi văn bản áp
     dụng cho một nhóm khóa khác nhau. Đây đúng là dạng lỗi "không phân biệt khóa" đã thấy với QĐ 3183, và câu
     "IELTS 5.5" bị bịa căn cứ ở phiên 10/10 cũng thuộc chủ đề này.
4. Vì vậy các kỹ thuật nâng cao nên chọn **bám theo định dạng**: lọc metadata theo khóa/hệ/hiệu lực, liên kết văn
   bản sửa đổi/bổ sung/thay thế, công cụ tra bảng, small-to-big. Không thêm kỹ thuật chung chung.
5. Trình tự giữ nguyên nguyên tắc chống overfit: **chốt danh sách văn bản → A và B viết tập test → nạp và cải tiến
   trên dev → chốt cấu hình → chạy test một lượt**.

---

## 1. Kiểm kê dữ liệu Đào tạo

Ký hiệu cột "Lớp chữ": **text** = có lớp chữ dùng được; **scan** = phải OCR; **hỏng** = có lớp chữ nhưng font
cũ (VNI/TCVN3), phải OCR. Mã định dạng F1–F7 xem §2. Cột "Hiệu lực" ghi **(?)** khi **chưa xác minh** bằng nội dung
văn bản. Nhóm phải tự xác minh, không đoán theo năm ban hành.

### 1.1 `1_quy_che_dao_tao_dai_hoc` (17 tệp)

| Tệp | Lớp chữ | Định dạng | Hiệu lực | Quyết định |
|---|---|---|---|---|
| `25_quy-che-…-sai-gon.pdf` (QC SGU 2021) | scan | F1 + F2 | đang áp dụng | **đã nạp** |
| `4. QuyCheDaoTaoDHSG 2021.pdf`, `…__daotao.pdf` | scan | — | — | trùng với `25_` |
| `QD 3183.2025 …` (3 bản) | scan | F5 (sửa đổi Điều) | đang áp dụng | **đã nạp** 1 bản |
| `8_QD810…` | scan | F1 | đang áp dụng | **đã nạp** |
| `2022-2375…` | scan | F1 | đang áp dụng | **đã nạp** (trùng `5_…/CV2375…`) |
| `22_quy-dinh-ve-khoi-luong…`, `Quydinh150tc.pdf` | text / scan | F7 | đang áp dụng | **đã nạp** |
| `QuyCheDaoTao_2017.pdf`, `3_…vbhn-17…2014`, `QC_…he-chuan.pdf` (QC tín chỉ của Bộ, theo QĐ 43/2007), `01.Quyche43.pdf` | scan / text / text / **hỏng** | F1 | hết hiệu lực | **không nạp** vào index trả lời (chỉ dùng để đối chứng) |
| `05.-QD_trienkhaiTT57…` (công văn 2013) | text | F7 | hết hiệu lực (?) | không nạp |
| `2_qui-che-…-08-nam-2021…` (TT 08/2021 của Bộ) | text | F1 | đang áp dụng ở cấp Bộ | **mặc định không nạp**: trùng số Điều với QC SGU, dễ chen top-1. Nếu nạp thì gắn `cap=bo` và lọc |
| `1a. QuyDinhChuyenNganhDaoTao_Don.docx` | docx | biểu mẫu | — | loại (đã chốt: không nạp biểu mẫu) |

### 1.2 `2_quy_doi_tieng_anh` (6 tệp): chuỗi văn bản theo khóa

| Tệp | Lớp chữ | Định dạng | Phạm vi áp dụng (đọc từ bản OCR thử, cần kiểm lại) | Quyết định |
|---|---|---|---|---|
| `2366-TB-ĐHSG …(1).pdf` = `202111_2366…` | scan | F4 (thông báo + bảng) | Tổ chức dạy học từ năm học 2021–2022 | **nạp** 1 bản |
| `30_TB so 2451…` | scan | F4 + F5 (bổ sung chứng chỉ cho TB 2366) | khóa 2021 trở về trước | **nạp** |
| `CV2626…` (QyĐ 2626/2022) | scan | F1 + bảng | khóa tuyển sinh từ 2022 (chu kỳ 2020–2024) | **nạp** |
| `29_2101…` (QyĐ 2101/2024) | scan | F1 + bảng (Điều 2 là bảng quy đổi) | khóa tuyển sinh từ 2024 (chu kỳ 2024–2028) | **nạp** |
| `TB so 2567…` (PTE Academic) | scan | F4 + F5 (bổ sung vào 2366, 2626, 2101, 2451) | chia theo nhóm khóa ngay trong văn bản | **nạp** |

### 1.3 `3_cong_tac_thi_ket_thuc_hoc_phan` (8 tệp)

| Tệp | Lớp chữ | Định dạng | Hiệu lực | Quyết định |
|---|---|---|---|---|
| `3260-QD-Hoan-thi-.pdf` = `20251120…_HoanThi.pdf` | scan | F3 (mục `1.`, `2.`, `3.`) | đang áp dụng | **nạp** 1 bản. Câu "ốm có được hoãn thi" trong nhật ký đang bị từ chối |
| `QD898BanHanhQuyDinhToChucThiHocKi.pdf` | scan | F2 (Điều 1–4 của QĐ) + F3 (quy định kèm theo) | đang áp dụng; **Điều 3 thay thế QyĐ 3089/2020** | **nạp** |
| `Quy dinh ve cong tac to chuc thi hoc ki.pdf` | scan | F3 | **là QyĐ 3089/2020, đã bị QĐ 898 thay thế** (OCR đọc nhầm số hiệu thành "3084") | không nạp (đối chứng) |
| `HD-Quy trinh phuc khao….pdf` (2 bản giống nhau) | scan | F6 (quy trình theo Bước, dạng bảng) | (?) căn cứ vào 3089 đã bị thay thế | **nạp** 1 bản, sau khi xác minh |
| `CV_3248_001_khieunai.pdf` | scan | F3 / F7 (công văn 2 trang, mục 1–3) | (?) | **nạp** |
| `ChienLuoc_001.pdf` (QĐ 2018, chiến lược và phương pháp dạy học, kiểm tra đánh giá) | scan | F2 + F3 | (?) căn cứ vào VBHN 17/2014 | ưu tiên thấp; xác minh rồi mới quyết định |

### 1.4 `4_xet_tot_nghiep` (5 tệp): chuỗi phiên bản

| Tệp | Lớp chữ | Định dạng | Hiệu lực | Quyết định |
|---|---|---|---|---|
| `03.-QyD_xetCNTN_2014.pdf` (TB 1166/2014) | text | F4 | hết hiệu lực (?) | đối chứng |
| `CDR1.pdf` (chính quy, theo CV 2897/2016), `CDR2.pdf` (vừa làm vừa học, theo 2695) | scan | F3 + F4 | (?) | xác minh |
| `06.-QuyDinhXetTN2017.pdf` | scan | F3 + F4 (bảng chứng chỉ ngoại ngữ) | (?) | xác minh |
| `TB_ChuanDauRa_2020.pdf` | scan | F4 (theo năm tốt nghiệp) | (?) mới nhất trong nhóm | ứng viên **nạp** |

> Lưu ý: điều kiện tốt nghiệp chính đã có ở Điều 13 QC 2021. Các thông báo chuẩn đầu ra ngoại ngữ có thể đã bị
> thay bằng QyĐ 2626/2101 (nhóm 1.2). **Phải đọc nội dung để xác định** trước khi nạp. Nếu không, hệ thống sẽ đưa
> ra hai chuẩn đầu ra khác nhau cho cùng một câu hỏi.

### 1.5 `5_quy_dinh_hoc_vu_khac` (8 tệp)

| Tệp | Lớp chữ | Định dạng | Hiệu lực | Quyết định |
|---|---|---|---|---|
| `QuyDinh_CapBangDiem.pdf`, `QuyDinh_CapBanSao.pdf` | scan | F3 (`1.`, `2.1.`, `3.4.`) | (?) | **nạp** (thủ tục hay hỏi) |
| `QĐ_CVHT.pdf` (QĐ 2019, cố vấn học tập) | scan | F2 + F1 | (?) | **nạp** |
| `02.-Tiethoc_phonghoc.pdf` | text | F4 (bảng ca, tiết, giờ) | (?) | **nạp**. `pdftotext` mặc định rã bảng thành từng ô một dòng, phải dùng `-layout` hoặc chép tay |
| `24_quy-dinh-so-736…`, `04.-QyD_736…`, `DHSG_quy-dinh-thoi-gian-toi-da…` | text | F3 (ma trận hình thức × trình độ) | **xung đột với QC 2021 Điều 2** (thời gian tối đa) | **không nạp** vào index trả lời; dùng làm ca kiểm thử xung đột phiên bản |
| `CV2375…` | scan | F1 | — | trùng `2022-2375` |

### 1.6 `6_he_dao_tao_khac` (5 tệp)

| Tệp | Lớp chữ | Định dạng | Quyết định |
|---|---|---|---|
| `10_quy-che-…-vua-lam-vua-hoc.pdf` | text | F1 | đợt cuối, gắn `he_dao_tao=vlvh` |
| `9_quy-che-dao-tao-lien-thong.pdf` = `QD_dao-tao-lien-thong.pdf` | text | F1 | đợt cuối, 1 bản, `he_dao_tao=lien_thong` |
| `QC_dao-tao-trinh-do-thac-si-1.pdf`, `QC_dao-tao-trinh-do-tien-si.pdf` | text | F1 (47 và 39 Điều) | đợt cuối, `trinh_do=thac_si/tien_si` |

> Bốn văn bản này **cùng cấu trúc Điều** nên dễ nạp. Nhưng chúng **trùng chủ đề** với QC 2021 (thang điểm, thời
> gian đào tạo…). Không lọc theo `he_dao_tao`/`trinh_do` thì câu hỏi của sinh viên chính quy sẽ lấy nhầm quy chế
> thạc sĩ. Đây là ca thử tốt cho kỹ thuật lọc metadata (T1).

---

## 2. Bảy định dạng và cách xử lý từng loại

| Mã | Định dạng | Ví dụ | Đơn vị Node đề xuất | Metadata riêng | Bộ cắt hiện tại xử lý được? |
|---|---|---|---|---|---|
| **F1** | Quy chế/quy định chia **Chương → Điều** | 2101, 2626, CVHT, 2375, VLVH, thạc sĩ | 1 Điều = 1 Node (như hiện tại) | `dieu`, `chuong` | **Có** |
| **F2** | **Quyết định ban hành** (Điều 1–4 ngắn) + **văn bản kèm theo** | 898, CVHT, Chiến lược 2018 | Phần QĐ **không thành Node riêng**. Lấy *hiệu lực / thay thế văn bản nào* đưa vào metadata của văn bản kèm theo | `so_hieu`, `ngay_hieu_luc`, `thay_the` | Một phần (`phan=ban_hanh`, nhưng vẫn tạo Node: Y4) |
| **F3** | Quy định **đánh số mục** `1.` → `1.1.` → `a)`, không có Điều | hoãn thi 3260, cấp bảng điểm, bản sao, 3089, khiếu nại | 1 mục cấp 1 = 1 Node. Mục dài thì tách theo cấp 2, **ghép đường dẫn mục vào đầu text** ("QĐ 3260 > 1. Hoãn thi > 1.2 …") | `muc`, `duong_dan_muc` | **Không**: cả văn bản thành 1 Node lớn, hoặc mất nhãn |
| **F4** | **Thông báo/quy định mà nội dung chính là bảng** (chứng chỉ → điểm Tiếng Anh I/II/III; chuẩn đầu ra theo ngôn ngữ; ca–tiết–giờ) | 2366, 2451, 2567, 2101 Điều 2, TB CĐR 2020, tiết học | 1 bảng = 1 Node, gồm **câu dẫn + khóa áp dụng + bảng Markdown**. Bảng dài thì tách theo nhóm dòng, **lặp lại dòng tiêu đề** | `loai=bang`, `ap_dung_khoa`, `bang_da_kiem_tay` | **Không**, và OCR làm hỏng số |
| **F5** | Văn bản **sửa đổi / bổ sung / thay thế** văn bản khác | 3183 (sửa Điều QC 2021), 2451 và 2567 (bổ sung dòng vào bảng của 2366/2626/2101), 898 (thay 3089) | Như F1/F3/F4, cộng **quan hệ** tới văn bản gốc | `sua_doi`, `bo_sung`, `thay_the` (trỏ tới `nguon` của văn bản kia) | Chỉ có `sua_doi_dieu` cho kiểu của 3183 |
| **F6** | **Hướng dẫn quy trình theo Bước** (bảng Bước / Mô tả / Thời hạn / Đơn vị) | HD phúc khảo | **Cả quy trình 1 Node** (không cắt giữa các bước). Nếu quá dài thì mỗi bước 1 Node có tiền tố tên quy trình | `loai=quy_trinh`, `thoi_han` | **Không** |
| **F7** | Văn xuôi / công văn **1–2 trang** | 150 tín chỉ, khối lượng đào tạo, CV 3248 | 1 Node / văn bản (`MIN_TU_NOI_DUNG` hiện có) | — | **Có** |

Ngoài ra có hai vấn đề **ở tầng trích chữ** (tầng 1), không thuộc về định dạng:
- **Lớp chữ hỏng** (`01.Quyche43.pdf`: "ƥ GIAƧO DU…"). `extract_to_md.py` đã tự chuyển sang OCR khi điểm âm tiết
  thấp. Chỉ cần kiểm lại điểm chất lượng trong front matter.
- **Bảng có lớp chữ** (`02.-Tiethoc_phonghoc.pdf`). `pdftotext` không có `-layout` sẽ in mỗi ô một dòng. Cần
  `-layout` hoặc chép tay.

### 2.1 Riêng F4: bảng trong bản scan (quan trọng nhất)

Trích đoạn OCR thử của TB 2451 và 2366 (300 dpi khi chạy thật; bản thử 200 dpi):

```text
1. | -PET: từ 140 - 152 do Cambridpe cấp. § § §        ← đúng: 8 8 8
3. | cấp. l I0 10 10                                    ← đúng: 10 10 10
86l02 | Tiếng Anhl 02 ~ — 866101                        ← mã học phần và tên bị vỡ
3 |- IBLTS > 5.0 do IDP Education hoặc British          ← IELTS
```

Lỗi OCR ở văn xuôi chỉ làm câu khó đọc. Lỗi ở bảng thì **đổi luôn đáp án**. Đề xuất:
1. **Chép tay bảng vào tầng 1** (`data/ocr/…`, nơi duy nhất được sửa tay). Đánh dấu `<!-- bang: da_kiem_tay -->`.
   Cả nhóm Đào tạo chỉ có khoảng 10–15 bảng nhỏ, làm tay trong 1 buổi là chắc chắn nhất.
2. Thêm **kiểm tra tự động** trong `clean_md.py` (chỉ báo lỗi, không tự sửa, giống các kiểm tra hiện có): ô điểm
   phải thuộc tập hợp hợp lệ (ví dụ 0–10), không chứa ký tự lạ như `§`, `I0`, `l`.
3. Xuất thêm **bảng có cấu trúc** (CSV) cho các bảng quy đổi:
   `van_ban, ap_dung_khoa, chung_chi, nguong_tu, nguong_den, diem_TA1, diem_TA2, diem_TA3`.
   Bảng này là đầu vào cho công cụ tra bảng (T5), đồng thời là "đáp án chuẩn" để chấm exact-match.
4. Nếu muốn so sánh với cách tự động: thử `MarkdownElementNodeParser` của LlamaIndex. Bộ cắt này tách bảng thành
   Node riêng, nhưng **gọi LLM để tóm tắt từng bảng**, nên tốn lượt gọi và có nguy cơ LLM viết lại con số. Chỉ dùng
   làm đối chứng, không dùng làm mặc định.

### 2.2 Riêng F5: một câu hỏi, nhiều văn bản, đáp án theo khóa

Ví dụ câu "IELTS 5.0 được quy đổi mấy điểm Tiếng Anh II?" có **đáp án khác nhau** tùy khóa. Có thể phải đọc 2366 +
2451 (khóa ≤ 2021), 2626 (khóa 2022–2023) hoặc 2101 (khóa ≥ 2024), cộng 2567 nếu là PTE. Hệ thống cần:
- metadata `ap_dung_khoa_tu` / `ap_dung_khoa_den` cho mỗi Node bảng;
- khi câu hỏi không nêu khóa: **trình bày theo từng nhóm khóa**, hoặc hỏi lại;
- khi câu hỏi nêu khóa ("em khóa 2023"): **lọc theo khóa** trước khi đưa vào LLM.

Đây là phiên bản tổng quát của lỗi QĐ 3183 đã đo được ("8,4 hệ 10" cho ra 3,0 hoặc 3,5 tùy cách hỏi). Giải quyết
dứt điểm ở đây thì sửa được cả lỗi cũ.

---

## 3. Thay đổi pipeline cần làm (đề xuất, chưa sửa code)

| Bước | Thay đổi | Phục vụ định dạng | Tham chiếu |
|---|---|---|---|
| Tầng 1 | Giữ nguyên `extract_to_md.py`. Với trang có bảng: OCR 300–400 dpi, `--psm 6`, rồi chép tay bảng | F4, F6 | §2.1 |
| Tầng 2 | `clean_md.py --kieu dieu|so_muc|buoc|bang`. Nhận dạng ranh giới "Ban hành kèm theo Quyết định…". **Giữ `<!-- trang: N -->`** thay vì xóa | F2, F3, F4, F6 | ĐX-3, Y3 |
| Manifest | `configs/corpus_sgu.yaml`: mỗi văn bản có `kieu_cat`, `so_hieu` (**nhập tay và đối chiếu**, vì OCR đọc 3089 thành 3084), `tinh_trang`, `ap_dung_khoa_tu/den`, `he_dao_tao`, `sua_doi/bo_sung/thay_the` | mọi định dạng | ĐX-5 |
| Loader | `processed_loader.py`: nhãn `muc` + `duong_dan_muc`; `nguon_trich` dạng "Mục 1.2 — QĐ 3260/2025 hoãn thi"; `id_` Node cố định; ngưỡng cắt đếm bằng tokenizer của embedding | F3, F4, F6 | ĐX-4, R2, R3 |
| Synthesis | `refine_template` tiếng Việt (bảng và quy trình làm prompt dài ra, `compact` sẽ chia nhiều lượt hơn) | F4, F6 | R1 |
| Đánh giá | Luật chấm theo `(nguon, dieu|muc)` thay vì tiền tố tên file | mọi định dạng | ĐX-8 |

Ghi chú về lọc theo khóa: lọc theo khoảng (`ap_dung_khoa_tu <= K <= ap_dung_khoa_den`) cần các toán tử `>=`, `<=`
của `MetadataFilters`. Phải **kiểm `SimpleVectorStore` có hỗ trợ đủ không** (Bảng 1.3 của báo cáo đã ghi nhận
SimpleVectorStore lọc hạn chế). Nếu không hỗ trợ thì lọc trong một postprocessor tự viết, hoặc dùng `IN` với danh
sách khóa liệt kê sẵn.

---

## 4. Thứ tự nạp: theo độ khó định dạng và giá trị hỏi đáp

| Đợt | Văn bản | Định dạng mới phải làm | Vì sao làm trước/sau | Câu dev thêm |
|---|---|---|---|---|
| **0** | Sửa nền: R1–R6, dedupe, `.gitignore` | — | Mọi đợt sau đều cần | — |
| **1** | Hoãn thi 3260, thi học kỳ 898, cấp bảng điểm, cấp bản sao, khiếu nại 3248, CVHT | **F3, F2** | Văn xuôi đánh số dễ làm; giá trị cao (câu hoãn thi đang bị từ chối) | 20–25 |
| **2** | Chuỗi quy đổi tiếng Anh: 2366, 2451, 2626, 2101, 2567 | **F4, F5** (bảng + theo khóa) | Khó nhất nhưng hỏi nhiều nhất; câu IELTS đang bị bịa. Làm cùng lúc với T1, T2, T5 | 20–25 (trải đều các khóa) |
| **3** | Phúc khảo (HD), tiết học/phòng học; nhóm xét tốt nghiệp/chuẩn đầu ra **sau khi xác minh hiệu lực** | **F6**, F4 có lớp chữ | Cần xác minh hiệu lực trước | 10–15 |
| **4** (tùy chọn) | VLVH, liên thông, thạc sĩ, tiến sĩ | F1 (sẵn có) + lọc `he_dao_tao` | Dễ nạp nhưng dễ gây nhiễu; chỉ làm khi T1 đã chạy | 10 |

**Cổng sau mỗi đợt:**
- `make test` xanh. Số Node trong index bằng số Node từ loader.
- R@1 dev **theo từng nguồn**, nhất là nhóm câu QC 2021 cũ, không tụt quá **5 điểm**. Nếu tụt thì ghi bảng "Node
  nào chen lên top-1", sửa (thường bằng lọc hoặc metadata) rồi mới sang đợt sau.
- Câu dev của định dạng mới đạt ngưỡng tối thiểu. Gợi ý R@3 ≥ 80% cho đợt 1, 3, 4. Riêng đợt 2 thêm
  **exact-match câu trả lời** ≥ 80% trên các câu tra bảng.

---

## 5. Đánh giá theo định dạng

| Định dạng | Loại câu dev / test | Đo bằng |
|---|---|---|
| F1/F3 | Hỏi nội dung một Điều/mục | R@k theo `(nguon, dieu|muc)` |
| F4 | Tra bảng ("IELTS 5.0 được mấy điểm TA II") | R@k **và exact-match số** so với CSV đã kiểm tay |
| F5 | Cùng câu hỏi, khác khóa ("khóa 2021" / "khóa 2024" / không nêu khóa) | Tỷ lệ **đúng khóa**; với câu không nêu khóa: có nêu đủ các nhóm khóa không |
| F6 | Hỏi bước, thời hạn, nơi nộp ("phúc khảo trong mấy ngày") | Câu trả lời có đủ bước hay thiếu bước (chấm tay hoặc `CorrectnessEvaluator`) |
| Xung đột phiên bản | Thời gian tối đa (QC 2021 so với QĐ 736), thi học kỳ (898 so với 3089) | Có trả lời theo văn bản đang hiệu lực không |
| Ngoài phạm vi sát biên | Chủ đề CTSV chưa nạp (điểm rèn luyện, học bổng) | Tỷ lệ từ chối đúng (ma trận 2×2) |

**Ảnh hưởng tới tập test của A và B** (`task-tap-kiem-chung-va-phan-cong.md`): phạm vi test là **danh sách văn bản
đã chốt ở đợt 0** (manifest), không chỉ QC 2021 + QĐ 3183. Gợi ý thay bảng §3.1 trong file task bằng phân bổ theo
định dạng: F1 10, F3 10, F4/F5 12 (trải đều các khóa), F6 4, xung đột phiên bản 4, tổng 40 câu, cộng 20 câu ngoài
phạm vi.

---

## 6. Kỹ thuật nâng cao gắn với định dạng

| Mã | Kỹ thuật | API LlamaIndex | Định dạng / lỗi nhắm tới | Ưu tiên |
|---|---|---|---|---|
| **T1** | Lọc metadata: `ap_dung_khoa`, `he_dao_tao`, `tinh_trang` | `MetadataFilters`, `FilterOperator` (`>=`, `<=`, `in`) | F5; hệ khác (đợt 4); văn bản hết hiệu lực | **Bắt buộc** |
| **T2** | Liên kết văn bản sửa đổi / bổ sung / thay thế | `NodeRelationship` + `BaseNodePostprocessor` tự viết: lấy được Node gốc thì kéo kèm Node bổ sung (và ngược lại) | F5 (3183, 2451, 2567, 898) | **Bắt buộc** |
| **T5** | Công cụ tra bảng quy đổi (chứng chỉ → điểm; thang 10 → chữ → thang 4 theo khóa) | `FunctionTool` trên CSV §2.1. Gọi trực tiếp khi câu hỏi thuộc loại "quy đổi", hoặc qua `ReActAgent` | F4; lỗi "8,4 → 3,0/3,5", "4,0 thuộc loại D" | Cao |
| **T6** | Đo lại hybrid BM25 và rerank | Đã có | Tên chứng chỉ (IELTS, TOEIC, PTE, VSTEP) và số hiệu văn bản là **token hiếm**, đúng chỗ BM25 mạnh. Giả thuyết: hybrid sẽ có ích với F4, khác kết luận ở 54 Node | **Bắt buộc**, rẻ |
| **T3** | Small-to-big cho Điều/mục dài | `HierarchicalNodeParser` + `AutoMergingRetriever`, hoặc `SentenceWindowNodeParser` | F1 dài (QC 2021, thạc sĩ); lỗi "30 tuần" | Trung bình |
| T4 | Viết lại câu hỏi + nhớ hội thoại | `CondensePlusContextChatEngine` | Câu nối tiếp ("còn khóa 2024 thì sao?"), rất tự nhiên với F5 | Tùy thời gian |

Mỗi kỹ thuật báo cáo theo khung: *lỗi đã đo → cơ chế → mã → bật/tắt trên dev (R@k, exact-match, đúng khóa, token,
độ trễ) → giữ hay tắt*. Kỹ thuật đo ra không giúp vẫn báo cáo và để tắt.

---

## 7. Chốt hệ thống

1. Mọi kỹ thuật đã có quyết định bật/tắt **dựa trên dev**.
2. Ghi `eval/results/chot_he_thong.md`: commit, `mo_ta()` cấu hình, manifest văn bản, số Node, phiên bản
   embedding/Ollama.
3. Tập test đã đóng băng từ trước. Chạy **một lượt** cho mọi cấu hình đã đo, cấu hình chính là cấu hình đã chọn
   từ dev.
4. Báo cáo hai cột **dev | test**, thêm bảng theo định dạng F1–F6.
5. Niêm phong. Sau đó chỉ sửa báo cáo.

---

## 8. Phân công gợi ý

| Việc | Người | Ghi chú |
|---|---|---|
| Xác minh hiệu lực + nhập metadata manifest (số hiệu, ngày, khóa áp dụng, thay thế) | 1 người giữ manifest | Việc đọc văn bản, không cần code; quyết định đúng sai của mọi việc sau |
| Chép tay và kiểm tra các bảng F4 + CSV quy đổi | 1–2 người | Khoảng 10–15 bảng; người thứ hai đối chiếu lại với PDF |
| `clean_md --kieu`, loader nhãn mục, luật chấm mới | Người giữ code | ĐX-3, ĐX-4, ĐX-8 |
| T1/T2/T5/T6 | Mỗi kỹ thuật 1 người chính + 1 người đọc lại | Buổi thực hành có thể hỏi bất kỳ ai |
| Tập test | A, B (độc lập) | Viết theo manifest, không xem kết quả hệ thống |

---

## 9. Việc cần bạn chốt

1. **Phạm vi:** chỉ sinh viên đại học chính quy (đợt 1–3), hay thêm cả hệ khác (đợt 4)?
2. **Bảng F4:** đồng ý chép tay vào tầng 1 (khuyến nghị), hay thử OCR tốt hơn trước (PaddleOCR/VietOCR, tốn công
   cài và phải ghim phiên bản)?
3. **Câu hỏi không nêu khóa:** trả lời theo tất cả các nhóm khóa (khuyến nghị, an toàn hơn), hay hỏi lại người dùng?
4. **TT 08/2021 của Bộ:** không nạp (khuyến nghị), hay nạp với `cap=bo` và lọc?
5. **Nhóm xét tốt nghiệp/chuẩn đầu ra:** ai xác minh hiệu lực, hạn chót khi nào? Nhóm này chưa rõ thì đợt 3 phải chờ.
