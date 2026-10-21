"""Lọc phiên bản văn bản trước và sau rerank (T1 + T2 trong docs/ke_hoach_them_du_lieu_dao_tao.md §6).

Đo ngày 13/10 (eval/results/logs/2026-10-13_dot2/08_phan_tich_loi.md): 46% câu trượt top-1 là do nhầm
phiên bản/khóa — QC 2021 Điều 7 bản gốc đứng trên mục QĐ 3183 sửa đổi, CV 3248/2018 đứng trên QĐ 898/2025,
bảng quy đổi của khóa 2022 trả lời cho câu hỏi khóa 2020. Rerank chấm theo độ khớp nội dung nên còn làm
lỗi này nặng hơn (bộ 02: 90% -> 50%). Hai postprocessor dưới đây dùng metadata hiệu lực trong front matter
(processed_loader đưa vào Node) để sửa:

  - `LocPhienBan` (đặt TRƯỚC rerank):
      1. bỏ Node của văn bản `het_hieu_luc` / `bi_thay_the`;
      2. câu hỏi nêu khóa tuyển sinh -> bỏ Node không áp dụng cho khóa đó, nhưng chỉ khi trong danh sách còn
         Node áp dụng được của cùng chuỗi văn bản (vd hỏi khóa 2020: bỏ QyĐ 2626/2101 khi đã có TB 2366/2451);
      3. lấy được Điều gốc mà Điều đó có mục sửa đổi -> kéo kèm mục sửa đổi (kể cả khi vector không lấy ra).
  - `UuTienSuaDoi` (đặt SAU rerank): văn bản sửa đổi/thay thế đứng ngay trước văn bản bị sửa, rồi mới cắt top_n.
    Reranker vì thế phải giữ đủ Node (retriever.get_postprocessors đặt top_n đủ lớn), việc cắt dồn về đây.
    Mục sửa đổi theo Điều (`sua_doi_dieu`) luôn được đưa lên. Quan hệ sửa đổi cả văn bản thì không biết phần nào bị sửa
    (TB 2567 chỉ bổ sung PTE nhưng ghi `sua_doi` 2366/2451), nên chỉ đưa lên khi reranker cũng thấy văn bản mới liên
    quan: điểm >= `ti_le_toi_thieu` x điểm văn bản cũ. Đo 17/10 trên dev: các lần đưa lên đúng (QĐ 898 Điều 5 trên
    CV 3248) có tỉ lệ >= 0,92; các lần sai (2567 cho câu IELTS/VSTEP, 898 Điều khác cho câu khiếu nại) đều < 0,35.
    Ngưỡng này hiệu chỉnh trên điểm reranker; khi không rerank (điểm là cosine của vector, các Node sát điểm nhau)
    thì `ti_le_toi_thieu=None`: không so điểm, quan hệ sửa đổi cả văn bản luôn được đưa lên. Việc giữ/bỏ Node do
    metadata hiệu lực quyết định (LocPhienBan); điểm chỉ ảnh hưởng thứ tự.
"""
import re
import unicodedata
from collections.abc import Iterable

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import BaseNode, NodeWithScore, QueryBundle
from pydantic import Field

HET_HIEU_LUC = {"het_hieu_luc", "bi_thay_the"}
# "khóa 2020", "khoá tuyển sinh năm 2021", "K21", "khóa 22"
KHOA = re.compile(r"\bkh(?:óa|oá|oa)\s*(?:tuyển\s*sinh\s*)?(?:năm\s*)?(20\d\d|\d\d)\b|\bK(\d\d)\b", re.IGNORECASE)


def khoa_trong_cau_hoi(cau_hoi: str) -> int | None:
    """Khóa tuyển sinh nêu trong câu hỏi (năm 4 chữ số), None nếu không nêu."""
    m = KHOA.search(unicodedata.normalize("NFC", cau_hoi))
    if not m:
        return None
    so = m[1] or m[2]
    return int(so) if len(so) == 4 else 2000 + int(so)


def so_van_ban(so_hieu: str) -> str:
    """"3183/QĐ-ĐHSG" -> "3183": các văn bản tham chiếu nhau ghi ký hiệu không thống nhất (QĐ/QyĐ/TB)."""
    return so_hieu.split("/")[0].strip()


def danh_sach(gia_tri: object) -> list[str]:
    """Metadata quan hệ lưu dạng "a; b" (processed_loader) -> ["a", "b"] đã chuẩn hóa về số văn bản."""
    return [so_van_ban(x) for x in str(gia_tri or "").split(";") if x.strip()]


def lien_quan(meta: dict[str, object]) -> set[str]:
    """Số văn bản của chính Node và mọi văn bản nó sửa đổi/bị sửa đổi/thay thế/bị thay thế."""
    ket = {so_van_ban(str(meta["so_hieu"]))} if meta.get("so_hieu") else set[str]()
    for khoa in ("sua_doi", "bi_sua_doi_boi", "thay_the", "bi_thay_the_boi"):
        ket.update(danh_sach(meta.get(khoa)))
    return ket


def chuoi_van_ban(nodes: Iterable[BaseNode]) -> dict[str, int]:
    """Gom văn bản thành các chuỗi liên thông (union-find): số văn bản -> mã chuỗi.

    TB 2366 -> 2451, 2567 -> QyĐ 2626 -> 2101 nối với nhau qua TB 2567, nên cả 5 văn bản quy đổi tiếng Anh
    là một chuỗi; QC 2021 và QĐ 3183 là một chuỗi khác.
    """
    cha: dict[str, str] = {}

    def goc(x: str) -> str:
        while cha.setdefault(x, x) != x:
            cha[x] = cha[cha[x]]
            x = cha[x]
        return x

    for n in nodes:
        ds = sorted(lien_quan(n.metadata))
        for x in ds[1:]:
            cha[goc(x)] = goc(ds[0])
        if ds:
            goc(ds[0])
    ma: dict[str, int] = {}
    return {x: ma.setdefault(goc(x), len(ma)) for x in cha}


def ap_dung_cho_khoa(meta: dict[str, object], khoa: int) -> bool:
    tu, den = meta.get("ap_dung_khoa_tu"), meta.get("ap_dung_khoa_den")
    return not ((isinstance(tu, int) and khoa < tu) or (isinstance(den, int) and khoa > den))


def khoa_sua_doi(meta: dict[str, object]) -> str | None:
    """Khóa tra mục sửa đổi: "<số văn bản bị sửa>|<Điều>" cho Node `sua_doi_dieu`."""
    if not meta.get("sua_doi_dieu"):
        return None
    dich = danh_sach(meta.get("sua_doi"))
    return f"{dich[0]}|{meta['sua_doi_dieu']}" if dich else None


class LocPhienBan(BaseNodePostprocessor):
    # "<số văn bản>|<Điều>" -> các Node mục sửa đổi Điều đó (dựng từ docstore của index)
    muc_sua_doi: dict[str, list[BaseNode]] = Field(default_factory=lambda: dict[str, list[BaseNode]]())
    chuoi: dict[str, int] = Field(default_factory=lambda: dict[str, int]())

    @classmethod
    def class_name(cls) -> str:
        return "LocPhienBan"

    @classmethod
    def tu_nodes(cls, nodes: Iterable[BaseNode]) -> "LocPhienBan":
        ds = list(nodes)
        muc: dict[str, list[BaseNode]] = {}
        for n in ds:
            k = khoa_sua_doi(n.metadata)
            if k:
                muc.setdefault(k, []).append(n)
        return cls(muc_sua_doi=muc, chuoi=chuoi_van_ban(ds))

    def ma_chuoi(self, meta: dict[str, object]) -> int | None:
        so = so_van_ban(str(meta.get("so_hieu", "")))
        return self.chuoi.get(so) if so else None

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        nodes = [n for n in nodes if n.node.metadata.get("tinh_trang") not in HET_HIEU_LUC]
        khoa = khoa_trong_cau_hoi(query_bundle.query_str) if query_bundle else None

        # T2: kéo kèm mục sửa đổi của Điều gốc đã lấy ra, đặt ngay trước Điều gốc
        co_san = {n.node.node_id for n in nodes}
        ket: list[NodeWithScore] = []
        for n in nodes:
            m = n.node.metadata
            if m.get("phan") == "chinh" and m.get("dieu") and m.get("so_hieu"):
                for sd in self.muc_sua_doi.get(f"{so_van_ban(str(m['so_hieu']))}|{m['dieu']}", []):
                    if sd.node_id not in co_san:
                        co_san.add(sd.node_id)
                        ket.append(NodeWithScore(node=sd, score=n.score))
            ket.append(n)

        # T1: theo khóa — chỉ bỏ khi cùng chuỗi văn bản còn Node áp dụng được, để không mất hết căn cứ
        if khoa is None:
            return ket
        hop_le = {self.ma_chuoi(n.node.metadata) for n in ket if ap_dung_cho_khoa(n.node.metadata, khoa)}
        return [
            n for n in ket
            if ap_dung_cho_khoa(n.node.metadata, khoa) or self.ma_chuoi(n.node.metadata) not in hop_le
        ]


class UuTienSuaDoi(BaseNodePostprocessor):
    top_n: int | None = None  # None = không cắt (khi không rerank)
    # Chỉ áp cho quan hệ cả văn bản và chỉ khi điểm là điểm rerank; None = không so điểm (xem docstring đầu file)
    ti_le_toi_thieu: float | None = 0.5

    @classmethod
    def class_name(cls) -> str:
        return "UuTienSuaDoi"

    def _postprocess_nodes(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle | None = None
    ) -> list[NodeWithScore]:
        ket = list(nodes)
        # Lặp tới khi ổn định: mỗi lượt đưa một Node "mới hơn" lên ngay trước Node nó sửa đổi/thay thế
        for _ in range(len(ket) ** 2 + 1):
            doi = False
            for i, cu in enumerate(ket):
                for j in range(i + 1, len(ket)):
                    if moi_hon(ket[j].node.metadata, cu.node.metadata) and self.du_lien_quan(ket[j], cu):
                        ket.insert(i, ket.pop(j))
                        doi = True
                        break
                if doi:
                    break
            if not doi:
                break
        return ket if self.top_n is None else ket[: self.top_n]

    def du_lien_quan(self, moi: NodeWithScore, cu: NodeWithScore) -> bool:
        if moi.node.metadata.get("sua_doi_dieu") or self.ti_le_toi_thieu is None:
            return True
        if moi.score is None or cu.score is None:
            return True
        return moi.score >= self.ti_le_toi_thieu * cu.score


def moi_hon(moi: dict[str, object], cu: dict[str, object]) -> bool:
    """`moi` sửa đổi/thay thế đúng phần của `cu` đang nói tới.

    - Mục sửa đổi Điều X của QĐ 3183 mới hơn Điều X bản gốc của QC 2021 (cùng Điều mới tính).
    - Văn bản E mới hơn văn bản D khi D ghi `bi_sua_doi_boi`/`bi_thay_the_boi` E, hoặc E ghi `sua_doi`/`thay_the` D,
      chỉ khi Node của D không thuộc Điều nào: Node chia theo Điều chỉ bị đẩy xuống bởi đúng mục sửa đổi Điều đó
      (QĐ 3183 Điều 2 "hiệu lực" không phải bản mới của QC 2021 Điều 13; QyĐ 2101 thay 2626 chỉ cho khóa từ 2024).
    """
    so_cu = so_van_ban(str(cu.get("so_hieu", "")))
    so_moi = so_van_ban(str(moi.get("so_hieu", "")))
    if not so_cu or not so_moi or so_cu == so_moi:
        return False
    if moi.get("sua_doi_dieu"):
        return so_cu in danh_sach(moi.get("sua_doi")) and moi.get("sua_doi_dieu") == cu.get("dieu")
    if cu.get("dieu"):
        return False
    return (
        so_moi in danh_sach(cu.get("bi_sua_doi_boi")) + danh_sach(cu.get("bi_thay_the_boi"))
        or so_cu in danh_sach(moi.get("sua_doi")) + danh_sach(moi.get("thay_the"))
    )
