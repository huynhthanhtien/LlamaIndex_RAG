# Nhiệm vụ: tập kiểm chứng chống overfit và minh chứng phân công

> Giao cho 2 thành viên (gọi là **A** và **B**, nhóm tự điền tên). Tài liệu này xử lý nhận xét **mục 9 (overfit)**
> và **mục 10 (phần việc từng thành viên)** trong `docs/de_xuat_xu_ly_nhan_xet.md`.
> Hai việc gắn với nhau: làm tập kiểm chứng chính là phần việc có minh chứng (commit, PR, file) cho hai bạn ở Phụ lục A.
> **Không cần sửa code.** Chỉ tạo file dữ liệu JSON/Markdown. Người giữ code chỉ cần thêm tên file vào danh sách
> bộ câu hỏi trong `eval/evaluate.py` (1 dòng).

---

## 1. Vì sao phải làm

Bộ `test_questions_01.json` (31 câu) và `test_questions_02.json` (10 câu) do chính nhóm viết. Nhóm cũng đã dùng hai bộ
này để chỉnh loader, prompt và chọn cấu hình. Vì vậy R@1 81%/90% là số trên **tập phát triển (dev)**: nó cho biết
hệ thống khớp với câu hỏi mình đã nhìn thấy, chưa cho biết hệ thống có tổng quát hay không.

Cách sửa chuẩn là có thêm một **tập kiểm chứng (test)**, gồm câu hỏi:
1. do người **không chỉnh pipeline** viết;
2. viết **trước khi** thấy hệ thống trả lời thế nào;
3. được **đóng băng** (khóa nội dung, ghi hash và ngày) trước lần chạy đầu tiên;
4. sau khi đóng băng, **không** dùng để chỉnh hệ thống. Nếu đã nhìn lỗi trên tập này rồi sửa code, tập đó trở thành
   dev và phải viết tập mới.

Báo cáo sau đó trình bày **hai cột riêng: dev và test**. Nếu test thấp hơn dev nhiều thì đó là bằng chứng có overfit.
Phải ghi trung thực con số đó, vì đây chính là kết quả.

---

## 2. Phân công

| | Thành viên A, người viết câu hỏi | Thành viên B, người gán nhãn độc lập và lo phần "ngoài phạm vi" |
|---|---|---|
| Việc chính | Viết **40 câu** trong phạm vi (QC 2021 + QĐ 3183), kèm Điều đúng và trích nguyên văn | (1) Gán nhãn lại Điều đúng cho 40 câu của A mà **không xem nhãn của A**; (2) viết **20 câu ngoài phạm vi**; (3) gán `pham_vi` cho 56 câu của `cau-hoi01.md` |
| Sản phẩm | `eval/test_kiem_chung_qc2021.json`, `eval/test_kiem_chung_3183.json` | `eval/test_kiem_chung_ngoai.json`, `eval/results/nhan_pham_vi_cau-hoi01.csv`, `eval/results/do_dong_thuan.md` |
| Cùng làm | Họp đối chiếu các câu hai người gán nhãn khác nhau, chốt nhãn, **đóng băng**, viết mục báo cáo + dòng Phụ lục A | |

**Quy tắc độc lập**, cả hai phải giữ cho đến khi đóng băng:
- **Không mở** `eval/test_questions_01.json`, `test_questions_02.json`, `eval/results/*` và nhật ký Gradio.
- **Không chạy** hệ thống (Gradio, `pipeline.py`) để thử câu của mình.
- Chỉ đọc văn bản trong `data/processed/01_quy_che_dao_tao/1_quy_che_dao_tao_dai_hoc/`, hoặc PDF gốc trong `data/raw/`.

---

## 3. Việc của A: viết 40 câu trong phạm vi

### 3.1 Phân bổ theo loại câu
Phân tầng để kết quả không bị dồn vào loại câu dễ. Mục tiêu là hỏi giống **sinh viên thật**, không chép lại câu
trong văn bản.

| Mã loại | Mô tả | Số câu | Ví dụ cách hỏi (minh họa, không đưa vào tập) |
|---|---|---|---|
| `thang` | Hỏi thẳng, dùng đúng từ của văn bản | 6 | "Thời gian tối đa hoàn thành khóa học là bao lâu?" |
| `dong_nghia` | Diễn đạt khác, không dùng từ khóa của Điều | 8 | "Nghỉ học nhiều quá có bị cấm thi không?" |
| `khau_ngu` | Viết tắt, không dấu, sai chính tả, văn nói | 6 | "hoc ky he co bat buoc ko", "bn chỉ thì ra trường" |
| `tinh_huong` | Tình huống cá nhân, phải suy từ quy định | 6 | "Em bị cảnh báo 2 kỳ liền thì sao?" |
| `bang_so` | Tra bảng hoặc khoảng số (điểm chữ, quy đổi, xếp loại) | 6 | "7,9 điểm thì được điểm chữ gì?" |
| `sua_doi` | Nội dung QĐ 3183 sửa đổi, gồm cả **khóa áp dụng** | 8 | "Khóa 2025 rút môn trong mấy tuần?" |

- 32 câu thuộc QC 2021 → `test_kiem_chung_qc2021.json`; 8 câu `sua_doi` → `test_kiem_chung_3183.json`.
  Lý do tách: `eval/evaluate.py` chấm hai bộ theo hai luật khác nhau (`dung_bo_01`, `dung_bo_02`).
- Rải câu trên **ít nhất 12 Điều khác nhau**, mỗi Điều tối đa 4 câu. Không dồn vào Điều 9/10 (điểm).
- Viết câu hỏi không mơ hồ: chỉ có **một** Điều trả lời được. Nếu thấy cần hai Điều thì ghi `ghi_chu` và chọn Điều chính.

### 3.2 Định dạng JSON
Hai trường `question` và `dieu_dung` giữ **đúng định dạng** bộ cũ để `evaluate.py` đọc được ngay. Các trường còn lại
dùng cho phân tích và cho minh chứng; `evaluate.py` bỏ qua chúng.

```json
[
  {
    "id": "KC-QC-001",
    "question": "rut bot mon da dang ky thi trong may tuan dau",
    "dieu_dung": "7",
    "loai": "khau_ngu",
    "trich_nguyen_van": "<chép đúng câu trong Điều 7 trả lời câu hỏi>",
    "khoan": "4",
    "dap_an_ngan": "<đáp án 1 dòng>",
    "nguoi_viet": "A",
    "ngay_viet": "2026-10-12",
    "ghi_chu": ""
  }
]
```

- Với bộ 3183, `dieu_dung` theo **số Điều được sửa đổi** (ví dụ `"9"`). Câu hỏi về khóa áp dụng hoặc hiệu lực thì ghi
  `"2 (QĐ 3183)"`, giống bộ 02 (`evaluate.py` chỉ lấy phần trước khoảng trắng).
- `trich_nguyen_van` là **bắt buộc**. Nếu không chép được câu nào trả lời câu hỏi thì câu hỏi đó chưa có đáp án rõ, nên bỏ.

### 3.3 Tự kiểm trước khi giao cho B
- [ ] 40 câu, đúng số lượng từng loại ở bảng 3.1.
- [ ] Không câu nào gần giống câu đã có trong bộ dev. Kiểm bằng script ở **mục 5.1**, script do B chạy vì A không được mở bộ dev.
- [ ] Mỗi câu có `trich_nguyen_van` tìm thấy được bằng Ctrl+F trong file `data/processed`.
- [ ] Chuyển cho B **bản đã xóa** `dieu_dung`, `khoan`, `trich_nguyen_van` (chỉ còn `id` và `question`).

---

## 4. Việc của B

### 4.1 Gán nhãn độc lập 40 câu của A
- Nhận file chỉ có `id` + `question`. Với mỗi câu, tự tìm Điều đúng (và khoản) trong `data/processed`, rồi ghi vào
  `eval/results/nhan_B.csv`:

```csv
id,dieu_dung,khoan,chac_chan,ghi_chu
KC-QC-001,7,4,cao,
KC-QC-002,10,3,thap,có thể là Điều 9
```

- `chac_chan` nhận `cao` hoặc `thap`. Các câu `thap` sẽ được đưa ra thảo luận trước tiên.

### 4.2 Viết 20 câu ngoài phạm vi → `eval/test_kiem_chung_ngoai.json`
Dùng đúng định dạng `cau_hoi_danh_gia.json` để `evaluate_answers.py` và phần chấm từ chối dùng lại được:

| Loại | Số câu | Ý tưởng | Hệ thống nên làm gì |
|---|---|---|---|
| `ngoai_han` | 6 | Học phí, ký túc xá, gửi xe, wifi | Từ chối |
| `sat_bien` | 8 | Chủ đề **có văn bản trong `data/raw` nhưng chưa nạp**: quy đổi chứng chỉ tiếng Anh (`2_quy_doi_tieng_anh`), điểm rèn luyện, học bổng, phúc khảo, hoãn thi | Từ chối. Đây là loại dễ bịa nhất, như câu "IELTS 5.5" ở phiên 10/10 |
| `bay` | 6 | Hỏi Điều không tồn tại ("Điều 45 Quy chế 2021 nói gì"), gắn số sai vào câu hỏi ("rút môn trong 8 tuần đầu đúng không"), hỏi văn bản không có trong corpus | Từ chối, hoặc sửa lại giả định sai |

```json
[
  {
    "id": "KC-NG-001",
    "question": "IELTS 6.0 thì được quy đổi mấy điểm học phần tiếng Anh?",
    "pham_vi": "ngoai",
    "loai": "sat_bien",
    "dap_an": "Không có trong 6 văn bản đã nạp (thuộc quy định quy đổi tiếng Anh, chưa nạp)",
    "nguon": "data/raw/01_quy_che_dao_tao/2_quy_doi_tieng_anh/",
    "nguoi_viet": "B"
  }
]
```

Với câu `sat_bien`, B phải **kiểm chắc** nội dung đó không có trong 6 văn bản ở `data/processed`. Nếu có thì câu đó
thuộc phạm vi, nên bỏ hoặc chuyển cho A.

### 4.3 Gán `pham_vi` cho 56 câu của `cau-hoi01.md`
Việc này **không** thuộc tập kiểm chứng, nên B được mở file. Mục đích là tách tỷ lệ "không tìm thấy" (52% → 41% → 23%)
thành từ chối đúng và từ chối sai. Chỉ gán nhãn theo **văn bản**, không xem câu trả lời của hệ thống:

```csv
stt,cau_hoi,pham_vi,dieu_dung,ghi_chu
1,học cử nhân bao nhiêu chỉ,trong,2,
14,điểm rèn luyện là gì,ngoai,,văn bản CTSV chưa nạp
22,còn kỹ sư,noi_tiep,,cần ngữ cảnh câu trước
```

`pham_vi` nhận một trong ba giá trị `trong` / `ngoai` / `noi_tiep`. Tách riêng `noi_tiep` vì hệ thống hiện không có
bộ nhớ hội thoại, nên câu nối tiếp là một loại lỗi riêng.

---

## 5. Đối chiếu, đo độ đồng thuận, đóng băng

### 5.1 Kiểm trùng với bộ dev (B chạy)
Script độc lập, chạy từ thư mục gốc, không sửa file nào của dự án:

```python
# scratch/kiem_trung.py
import json, difflib, unicodedata, re
def chuan(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")
    return re.sub(r"[^a-z0-9 ]", " ", s)
dev = [q["question"] for f in ("test_questions_01.json", "test_questions_02.json", "cau_hoi_danh_gia.json")
       for q in json.load(open(f"eval/{f}", encoding="utf-8"))]
dev += [re.sub(r"^\d+\.\s*", "", l).strip() for l in open("eval/results/cau-hoi01.md", encoding="utf-8")
        if re.match(r"^\d+\.", l)]  # dòng dạng "1. câu hỏi"
for f in ("test_kiem_chung_qc2021.json", "test_kiem_chung_3183.json", "test_kiem_chung_ngoai.json"):
    for q in json.load(open(f"eval/{f}", encoding="utf-8")):
        best = max(dev, key=lambda d: difflib.SequenceMatcher(None, chuan(q["question"]), chuan(d)).ratio())
        r = difflib.SequenceMatcher(None, chuan(q["question"]), chuan(best)).ratio()
        if r >= 0.7:
            print(f"{q['id']}  {r:.2f}\n   test: {q['question']}\n   dev : {best}")
```

Câu nào có độ giống ≥ 0,7 thì B chỉ báo **id** cho A (không đưa câu dev), để A viết lại câu đó.

### 5.2 Độ đồng thuận giữa A và B
Ghép nhãn `dieu_dung` của A và B, rồi tính tỷ lệ trùng và Cohen's kappa:

```python
# scratch/kappa.py
import json, csv
from collections import Counter
a = {q["id"]: q["dieu_dung"].split()[0]
     for f in ("test_kiem_chung_qc2021.json", "test_kiem_chung_3183.json")
     for q in json.load(open(f"eval/{f}", encoding="utf-8"))}
b = {r["id"]: r["dieu_dung"].strip() for r in csv.DictReader(open("eval/results/nhan_B.csv", encoding="utf-8"))}
ids = sorted(a.keys() & b.keys())
po = sum(a[i] == b[i] for i in ids) / len(ids)
ca, cb = Counter(a[i] for i in ids), Counter(b[i] for i in ids)
pe = sum(ca[k] * cb[k] for k in ca) / len(ids) ** 2
print(f"n={len(ids)}  trùng={po:.1%}  kappa={(po - pe) / (1 - pe):.2f}")
print("lệch:", [i for i in ids if a[i] != b[i]])
```

Ghi kết quả vào `eval/results/do_dong_thuan.md`: n, tỷ lệ trùng, kappa, danh sách câu lệch, và **nhãn chốt cho từng câu
lệch kèm lý do**. Kappa ≥ 0,8 là tốt. Nếu dưới 0,6 thì câu hỏi đang mơ hồ, nên viết lại các câu lệch.

### 5.3 Đóng băng
1. Sau khi chốt nhãn, A sửa file JSON theo nhãn chốt. Không thêm hay bớt câu nào nữa.
2. Tính hash và ghi vào `eval/results/dong_bang_tap_kiem_chung.md`:

   ```bash
   sha256sum eval/test_kiem_chung_*.json
   ```

   Nội dung file: ngày đóng băng, hash từng file, số câu theo loại, người viết, người gán nhãn, kappa.
3. Mỗi bạn làm trên **nhánh riêng** và mở **PR riêng** (A: câu hỏi; B: nhãn, câu ngoài, kiểm trùng, đồng thuận). Commit
   bằng tài khoản git của chính mình. Đây là minh chứng cho Phụ lục A, nên đừng nhờ người khác commit hộ.
4. Sau khi merge, người giữ code thêm hai file vào `BO_CAU_HOI` trong `eval/evaluate.py` (`qc2021` dùng `dung_bo_01`,
   `3183` dùng `dung_bo_02`) rồi chạy `make eval` **một lần**. Kết quả đó là con số test. Không chỉnh hệ thống dựa trên
   các câu sai của tập này.

---

## 6. Đưa vào báo cáo

### 6.1 Bảng kết quả mới (thay Bảng 4.4 / 8.1)

| Tập | Số câu | Luật chấm | R@1 (CI 95%) | R@3 | MRR |
|---|---|---|---|---|---|
| Dev 01 (QC 2021) | 31 | Điều gốc hoặc mục sửa đổi | 81% [68–94] | 100% | 0,892 |
| **Test QC 2021** | 32 | như trên | | | |
| Dev 02 (QĐ 3183) | 10 | chỉ mục sửa đổi / Điều QĐ | 90% [70–100] | 90% | 0,910 |
| **Test QĐ 3183** | 8 | như trên | | | |

Thêm một bảng phụ: R@1 trên tập test **theo loại câu** (`thang`, `dong_nghia`, `khau_ngu`, …). Bảng này cho thấy hệ
thống yếu ở loại nào. Bảng thứ hai là ma trận từ chối 2×2 trên 20 câu ngoài và 56 câu đã gán `pham_vi`.

### 6.2 Đoạn văn mẫu (mục 4.6, phần "Thiết kế đánh giá")
> Bộ 01/02 được dùng trong quá trình phát triển (chỉnh loader, prompt, chọn cấu hình), nên đóng vai trò tập dev. Để
> kiểm tra nguy cơ quá khớp, hai thành viên không tham gia chỉnh pipeline đã viết và gán nhãn độc lập một tập kiểm
> chứng gồm 40 câu trong phạm vi (6 loại câu) và 20 câu ngoài phạm vi. Độ đồng thuận nhãn Điều đạt κ = … trên 40 câu.
> Tập được đóng băng ngày … (sha256 ghi ở `eval/results/dong_bang_tap_kiem_chung.md`) trước lần chạy đầu tiên, và
> không được dùng để chỉnh hệ thống.

---

## 7. Phần việc của từng thành viên (mục 10)

### 7.1 Mỗi người tự ghi nhật ký cá nhân
Mỗi thành viên tạo `docs/nhat-ky/<ten>.md`. Ghi **mỗi tuần một khối**, kể cả việc không có commit: đọc tài liệu, sửa
tay OCR, chấm tay, viết báo cáo, làm slide.

```markdown
## Tuần 6 (12/10–16/10/2026)
| Việc | Kết quả / file | Minh chứng | Giờ |
|---|---|---|---|
| Viết 40 câu tập kiểm chứng | eval/test_kiem_chung_qc2021.json | PR #12, commit abc1234 | 6 |
| Họp chốt nhãn với B | eval/results/do_dong_thuan.md | biên bản trong file | 1 |
Khó khăn: 5 câu về Điều 9/10 mơ hồ, phải viết lại.
```

### 7.2 Dòng mẫu cho Bảng A.1 (LaTeX)
Cột "Người làm" ghi **tên người**. Ghi rõ một lần ở chú thích bảng rằng tài khoản `solozy` là của ai.

```latex
6 (12--16/10) & Tập kiểm chứng 40 câu trong phạm vi, viết độc lập với bộ dev & A (tên) &
  PR \#.., \texttt{eval/test\_kiem\_chung\_*.json} \\
              & Gán nhãn độc lập, 20 câu ngoài phạm vi, nhãn \texttt{pham\_vi} cho 56 câu, đo $\kappa$ & B (tên) &
  PR \#.., $\kappa = \ldots$ \\
```

### 7.3 Bảng phân công tổng (đặt đầu Phụ lục A)

| Thành viên | Phần phụ trách chính | Chương/mục báo cáo viết | Minh chứng chính |
|---|---|---|---|
| Huỳnh Thanh Tiến | … | … | commit/PR … |
| Phan Hữu Kha | … | … | … |
| Võ Thị Như Ý | … | … | … |
| Trần Hà Thanh Thùy | … | … | … |

Nguyên tắc: **chỉ ghi việc có minh chứng hoặc có người khác xác nhận**. Tuần nào một bạn không làm gì thì để trống
cho trung thực, đừng chép tên vào.

---

## 8. Mốc thời gian gợi ý (khoảng 1 tuần, điều chỉnh theo lịch học phần)

| Ngày | A | B |
|---|---|---|
| 1–2 | Đọc QC 2021 + QĐ 3183, viết 40 câu | Viết 20 câu ngoài phạm vi (kiểm `data/raw`), gán `pham_vi` cho 56 câu |
| 3 | Tự kiểm, gửi bản chỉ có câu hỏi cho B | Chạy kiểm trùng (5.1), báo id trùng cho A |
| 4 | Viết lại các câu trùng | Gán nhãn độc lập 40 câu |
| 5 | Họp chốt nhãn, tính kappa, đóng băng, mở PR | |
| 6 | Người giữ code chạy `make eval` một lần; A và B viết đoạn 6.2 và điền bảng 6.1 | |
| 7 | Mỗi người hoàn thành nhật ký cá nhân và dòng Bảng A.1 | |

**Định nghĩa "xong":** 3 file JSON đã đóng băng và có hash; có `do_dong_thuan.md` với kappa; có CSV `pham_vi` của 56 câu;
hai PR đứng tên hai bạn đã merge; có bảng 6.1 với số test; nhật ký cá nhân và dòng Bảng A.1 đã điền.
