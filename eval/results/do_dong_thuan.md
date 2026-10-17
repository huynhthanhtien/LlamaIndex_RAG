# Độ đồng thuận nhãn tập kiểm chứng (K3)

Ngày tính: 17/10/2026. Cách tính theo `docs/task-tap-kiem-chung-va-phan-cong.md`, mục 5.1–5.2.

- **Nhãn A** (N3, người viết câu): `eval/test_kiem_chung_qc2021.json` (32 câu) + `eval/test_kiem_chung_3183.json` (8 câu).
- **Nhãn B** (N4, gán độc lập từ bản chỉ có câu hỏi `*_K1.json`): `eval/test_kiem_chung_nhan_B.json` (40 câu).
- So sánh ở mức **Điều** (số Điều trong `dieu_dung`; nhãn B dạng "Điều 9 Quyết định 3183" được quy về "9", vì 8 câu `sua_doi`
  nằm riêng trong bộ QĐ 3183).

## Kết quả

| n | Trùng nhãn | p_e | Cohen's κ |
|---|---|---|---|
| 40 | 40/40 (100%) | 0,142 | **1,00** |

Không có câu lệch nên không cần chốt lại nhãn nào. κ ≥ 0,8 là mức tốt theo hướng dẫn.

Hạn chế khi báo cáo con số này: hai người chỉ gán nhãn ở mức Điều, không gán ở mức khoản. Mỗi câu của A lại được viết để
"chỉ một Điều trả lời được" (mục 3.1), nên đồng thuận tuyệt đối là hợp lý chứ không phải dấu hiệu bất thường. Tuy vậy, con số
không nói gì về độ khó phân biệt ở mức Node/khoản.

## Kiểm trùng với bộ dev (mục 5.1)

So mỗi câu của 3 file kiểm chứng (60 câu) với 160 câu dev (`test_questions_01/02`, `cau_hoi_danh_gia`, `dev_questions_dot1–3`,
`results/cau-hoi01.md`) bằng `difflib` sau khi bỏ dấu. Có 6 câu có độ giống ≥ 0,7:

| id | Loại | Độ giống | Câu dev gần nhất | Đánh giá |
|---|---|---|---|---|
| KC-QC-001 | `thang` | 0,74 | "Thời gian tối đa để hoàn thành khóa học là bao lâu?" | **Cùng ý**, chỉ đổi từ |
| KC-QC-004 | `thang` | 0,77 | "Sinh viên được phép học trực tuyến tối đa bao nhiêu phần trăm chương trình?" | **Cùng ý** |
| KC-QC-006 | `thang` | 0,82 | "Tín chỉ được công nhận chuyển đổi tối đa bao nhiêu phần trăm chương trình?" | **Cùng ý** |
| KC-3183-008 | `sua_doi` | 0,72 | "Điểm chưa hoàn thiện do được phép hoãn thi, kiểm tra được ghi nhận bằng điểm chữ nào?" | **Cùng ý** |
| KC-QC-012 | `dong_nghia` | 0,70 | (câu học trực tuyến) | Khác ý (học trao đổi, Điều 17): giống bề mặt, giữ |
| KC-3183-004 | `sua_doi` | 0,71 | (câu điểm C+ thang 4) | Khác ý (hỏi B+): giữ |

**Cần N3 quyết định trước khi đóng băng:** 4 câu "cùng ý" ở trên. Theo mục 5.1 thì phải viết lại. Riêng 3 câu loại `thang`
("dùng đúng từ của văn bản") gần như chắc chắn trùng câu dev cùng Điều. Nếu giữ thì ghi lý do vào `ghi_chu` và nêu trong báo cáo
rằng 4/40 câu là diễn đạt lại câu dev.

## Còn lại của K3 (việc của người, không tự động hóa)

1. N3 xử lý 4 câu trên (viết lại hoặc ghi lý do giữ). Nếu viết lại, N4 gán nhãn độc lập lại đúng các câu đó.
2. Đóng băng **sau khi N1 chốt cấu hình (C3)**: ghi `sha256sum eval/test_kiem_chung_*.json`, ngày, số câu theo loại, người viết,
   người gán nhãn và κ vào `eval/results/dong_bang_tap_kiem_chung.md`, mỗi người mở PR bằng tài khoản của mình.
3. N1 thêm hai file vào `BO_CAU_HOI` (`qc2021` → `dung_bo_01`, `3183` → `dung_bo_02`) và chạy `make eval` đúng một lần.
