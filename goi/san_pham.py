"""Dựng đơn hàng (DonHang) từ thông số đã bóc tách: mỗi loại sản phẩm một hàm, tra qua bảng XAY_DUNG."""
from dataclasses import dataclass, field

from .bang_gia import P, dac_tinh, LOAI_MAC_DINH
from .binh_bai import lot_kho_giay


@dataclass
class ThanhPhan:
    """Một loại miếng giấy/carton của sản phẩm (áo, lót, chipboard, thân hộp…)."""
    ten: str
    loai: str                # loại giấy
    gsm: int
    trai_w: float            # khổ trải (cm)
    trai_h: float
    con_moi_sp: int = 1      # số miếng loại này cho 1 sản phẩm
    so_mau: int = 4
    so_mat: int = 1


@dataclass
class DonHang:
    ten: str
    thanh_phan: list
    gia_cong: list = field(default_factory=list)       # key trong prices.gia_cong
    khuon_be: int = 1                                  # số khuôn bế
    uoc_tinh: list = field(default_factory=list)       # ghi chú khoản còn ước tính
    mac_dinh: list = field(default_factory=list)       # thông số khách không nói, bot tự lấy
    loai_sp: str = ""
    # --- tuỳ chỉnh theo tin nhắn (None = dùng prices.json) ---
    gia_giay: float = None           # triệu đ/tấn
    tu_sua_bai: int = None
    kho: tuple = None                # khổ in chỉ định
    con: int = None                  # số con/tờ chỉ định
    pct_ln: float = None
    khuon_be_tien: float = None
    proof: bool = True
    gc_tuy_chinh: list = field(default_factory=list)   # [(tên, đ/cái)]
    kts: bool = None                 # None = tự chọn cách rẻ hơn
    khuon_co_san: bool = False
    kieu_2_mat: str = None           # AB | tu_tro | tro_nhip | None = tự chọn rẻ nhất
    ep_kim_kt: tuple = None
    dap_noi_kt: tuple = None
    dap_noi_am_duong: bool = False
    so_mep_dan: int = 1
    tui_2_manh: bool = False
    gia_quai: float = None
    can_mang_2_mat: bool = False
    uv_kt: tuple = None              # vùng UV định hình (cm)
    cua_so_kt: tuple = None          # kích thước cửa sổ (cm)
    day_2_gut: bool = False          # dây treo thẻ bài thắt 2 gút
    con_khuon: int = None            # số con trên khuôn bế; None = bằng số con/tờ của bài bình
    khuon_co_chi_tiet: bool = False  # ép tính 750 đ/nhịp dù là hàng phẳng

    @property
    def co_kho_trai(self) -> bool:
        return dac_tinh(self.loai_sp)["co_kho_trai"]

    @property
    def bot_tai_dan(self) -> bool:
        return dac_tinh(self.loai_sp)["bot_tai_dan"]

    @property
    def khuon_don_gian(self) -> bool:
        return bool(dac_tinh(self.loai_sp).get("khuon_don_gian")) and not self.khuon_co_chi_tiet

    @property
    def co_in(self) -> bool:
        return any(tp.so_mau for tp in self.thanh_phan)


@dataclass
class _DauVao:
    """Thông số chung đã chuẩn hoá, truyền cho các hàm dựng từng loại."""
    spec: dict
    D: float
    R: float
    C: float
    giay: str
    gsm: int
    mau: int
    mat: int
    gc: list
    ten: str
    kieu: str


def _hop_cung(v: _DauVao) -> DonHang:
    ao_w, ao_h = v.D + 2 * v.C + 4, v.R + 2 * v.C + 4
    tp = [ThanhPhan("Áo giấy nắp + đáy", v.giay, v.gsm, ao_w, ao_h, 2, v.mau, 1),
          ThanhPhan("Lót ruột trơn", v.giay, v.gsm, ao_w, ao_h, 2, 0, 0),
          ThanhPhan("Chipboard nắp + đáy", "Chipboard", 1200, v.D + 2 * v.C, v.R + 2 * v.C, 2, 0, 0)]
    gc = [g for g in v.gc if not g.startswith("dan") and g != "be"] + ["be_hop_cung", "phay_ranh", "dung_hop", "boi_hop_cung"]
    nap_keo = any(k in v.kieu for k in ("kéo", "rút", "bao diêm", "diêm", "hộc"))
    if nap_keo:
        gc.append("boi_nap_keo")
    ten = v.ten or ("Hộp cứng nắp kéo (bao diêm)" if nap_keo else "Hộp cứng âm dương / nắp rời")
    # 4 khuôn bế: áo nắp, áo đáy, carton nắp, carton đáy (theo My)
    return DonHang(ten, tp, gc, khuon_be=4, uoc_tinh=["đơn giá dựng hộp chờ My chốt"])


def _thiep(v: _DauVao) -> DonHang:
    """Ấn phẩm phẳng: thiệp, card, thẻ bài, tấm giấy, đai, vòng cổ."""
    w, h = (v.D or 8), (v.R or 12)
    gc = list(v.gc)
    mot_mat = any(k in v.ten.lower() for k in ("đai", "vòng", "tấm", "tờ rơi"))
    ten_tp = " ".join(v.ten.split(" ")[:2]) if (mot_mat and v.ten) else ("Thiệp" if v.mau else "Tấm giấy")
    so_mat = (v.mat if v.spec.get("so_mat") else (1 if mot_mat else 2)) if v.mau else 1
    tp = [ThanhPhan(ten_tp, v.giay, v.gsm, w + 0.6, h + 0.6, 1, v.mau, so_mat)]
    if "be" not in gc:
        gc.append("cat_tp")
    la_the_bai = any(k in (v.ten + " " + v.kieu).lower() for k in ("thẻ bài", "the bai", "hangtag", "tag", "thẻ treo", "nhãn treo"))
    ten_mac_dinh = "Thẻ bài" if la_the_bai else ("Tấm giấy bế" if "be" in gc else "Thiệp")
    uoc = []
    if la_the_bai:
        tp[0].ten = "Thẻ bài"
        if "xo_day" in gc:   # thẻ bài: My tính theo dây treo (1 gút 200 đ, 2 gút 300 đ), không tính công xỏ dây riêng
            gc = [("day_treo" if g == "xo_day" else g) for g in gc]
    don = DonHang(v.ten or ten_mac_dinh, tp, gc, khuon_be=1 if "be" in gc else 0, uoc_tinh=uoc)
    if "be" in gc and not v.mau:      # tấm giấy không in: My làm khuôn 1 con, bế từng tấm, 750 đ/nhịp
        don.con_khuon, don.khuon_co_chi_tiet = 1, True
        don.mac_dinh.append("khuôn bế 1 con (khác thì ghi 'khuôn 2 con')")
    return don


def _tem_decal(v: _DauVao) -> DonHang:
    tp = [ThanhPhan("Tem decal", "Decal", 1, (v.D or 5) + 0.4, (v.R or 5) + 0.4, 1, v.mau, 1)]
    gc = [g for g in v.gc if g != "be"]
    if "be_demi" not in gc:
        gc.append("be_demi")
    return DonHang(v.ten or "Tem decal", tp, gc, khuon_be=1)


def _tui_giay(v: _DauVao) -> DonHang:
    """Khổ trải theo sổ tay My: ngang = 2×(ngang+hông) + mép dán; dọc = mép trên + cao + đáy (đáy = 2/3 hông)."""
    T = P.get("tui_giay", {})
    mep_dan, mep_tren = T.get("mep_dan_cm", 2), T.get("mep_tren_cm", 3)
    trai_h = round(mep_tren + v.C + v.R * T.get("ty_le_day_theo_hong", 2 / 3), 1)
    trai_w = 2 * (v.D + v.R) + mep_dan
    hai_manh = bool(v.spec.get("tui_2_manh")) or not lot_kho_giay(trai_w, trai_h)
    if hai_manh:
        tp = [ThanhPhan("Túi giấy (2 mảnh)", v.giay, v.gsm, v.D + v.R + mep_dan, trai_h, 2, v.mau, 1)]
    else:
        tp = [ThanhPhan("Túi giấy", v.giay, v.gsm, trai_w, trai_h, 1, v.mau, 1)]
    gc = [g for g in v.gc if not g.startswith("dan")] + ["be", "dan_tui", "quai_tui"]
    return DonHang(v.ten or "Túi giấy", tp, gc, khuon_be=1, tui_2_manh=hai_manh)


def _hop_gap_2_manh(v: _DauVao) -> DonHang:
    """Hộp giấy 2 mảnh: âm dương, nắp rời, bao diêm, nắp kéo."""
    w, h = v.D + 2 * v.C + 3, v.R + 2 * v.C + 3
    day_in = 0 if any(k in v.kieu for k in ("bao diêm", "kéo", "rút")) else v.mau
    if day_in == v.mau:      # nắp và đáy in giống nhau → bình chung 1 bài, 1 bộ kẽm
        tp = [ThanhPhan("Nắp + đáy", v.giay, v.gsm, w, h, 2, v.mau, 1)]
    else:
        tp = [ThanhPhan("Nắp", v.giay, v.gsm, w, h, 1, v.mau, 1), ThanhPhan("Đáy", v.giay, v.gsm, w, h, 1, day_in, 1)]
    gc = list(v.gc)
    if not any(g.startswith("dan") for g in gc):
        gc.append("dan_tay")
    if "be" not in gc:
        gc.append("be")
    return DonHang(v.ten or "Hộp giấy", tp, gc, khuon_be=2)


def _hop_gap_1_manh(v: _DauVao) -> DonHang:
    """Hộp nắp gài 1 mảnh: thân quấn quanh (a, b), sâu c → khổ trải 2(a+b)+2 × c+2b+3.
    Theo đúng thứ tự khách ghi; nếu vượt khổ giấy thì thử xoay kết cấu, rồi tới 2 mảnh âm dương."""
    def trai(a, b, c):
        return 2 * (a + b) + 2, c + 2 * b + 3

    D, R, C = v.D, v.R, v.C
    gc = list(v.gc)
    w0, h0 = trai(D, R, C)
    ghi_chu, khuon = None, 1
    tp = [ThanhPhan("Hộp", v.giay, v.gsm, w0, h0, 1, v.mau, v.mat)]     # mặc định; cũng là phương án để tinh() báo vượt khổ
    if (D and R and C) and not lot_kho_giay(w0, h0):
        xoay = [(wh, ten) for wh, ten in ((trai(D, C, R), "mở ở cạnh dài"), (trai(R, C, D), "mở ở cạnh ngắn")) if lot_kho_giay(*wh)]
        if xoay:
            (w1, h1), ten_xoay = min(xoay, key=lambda x: x[0][0] * x[0][1])
            tp = [ThanhPhan("Hộp", v.giay, v.gsm, w1, h1, 1, v.mau, v.mat)]
            ghi_chu = f"nắp gài mở mặt lớn cần khổ trải {w0:g}×{h0:g} (vượt khổ giấy) nên em tính kết cấu {ten_xoay}"
        elif lot_kho_giay(D + 2 * C + 3, R + 2 * C + 3):
            tp = [ThanhPhan("Nắp + đáy", v.giay, v.gsm, D + 2 * C + 3, R + 2 * C + 3, 2, v.mau, 1)]
            khuon = 2
            ghi_chu = "hộp 1 mảnh vượt khổ giấy nên em tính kiểu âm dương 2 mảnh"
            if not any(g.startswith("dan") for g in gc):
                gc.append("dan_tay")
    if not any(g.startswith("dan") for g in gc):
        gc.append("dan_may")
    if "be" not in gc:
        gc.append("be")
    return DonHang(v.ten or "Hộp giấy", tp, gc, khuon_be=khuon, uoc_tinh=[ghi_chu] if ghi_chu else [])


def _hop_gap(v: _DauVao) -> DonHang:
    if any(k in v.kieu for k in ("âm dương", "nắp rời", "bao diêm", "kéo", "rút")):
        return _hop_gap_2_manh(v)
    return _hop_gap_1_manh(v)


XAY_DUNG = {"hop_cung": _hop_cung, "thiep": _thiep, "tem_decal": _tem_decal, "tui_giay": _tui_giay, "hop_gap": _hop_gap}


def _ap_tuy_chinh(don: DonHang, spec: dict) -> None:
    """Chép các tham số My/khách ghi thẳng trong tin vào đơn."""
    if "boi_giay" in don.gia_cong and don.thanh_phan:
        a = don.thanh_phan[0]
        don.thanh_phan.append(ThanhPhan("Lớp giấy bồi", a.loai, a.gsm, a.trai_w, a.trai_h, a.con_moi_sp, 0, 0))
    don.gia_giay = spec.get("gia_giay_tr_tan") or None
    don.tu_sua_bai = spec.get("tu_sua_bai")
    if spec.get("kho_giay") and spec.get("so_con_to"):
        W, H = (int(x) for x in spec["kho_giay"].split("x"))
        don.kho, don.con = (W, H), spec["so_con_to"]
    don.pct_ln = spec.get("pct_loi_nhuan")
    if spec.get("khuon_be_nghin") is not None:
        don.khuon_be_tien = spec["khuon_be_nghin"] * 1000
    don.proof = not spec.get("khong_proof")
    don.kts = spec.get("in_kts")
    if don.kts is None and don.loai_sp == "hop_cung":
        don.kts = False            # My: hộp cứng luôn in offset, kể cả dưới 100 cái, vì in nhanh không đủ khổ
    don.khuon_co_san = bool(spec.get("khuon_co_san"))
    don.kieu_2_mat = spec.get("kieu_in_2_mat")
    don.ep_kim_kt = tuple(spec["ep_kim_kt"]) if spec.get("ep_kim_kt") else None
    don.dap_noi_kt = tuple(spec["dap_noi_kt"]) if spec.get("dap_noi_kt") else None
    don.dap_noi_am_duong = bool(spec.get("dap_noi_am_duong"))
    kieu = (spec.get("kieu_hop") or "").lower()
    don.so_mep_dan = spec.get("so_mep_dan") or (3 if any(k in kieu for k in ("đáy khóa", "đáy cài", "khóa đáy")) else 1)
    don.tui_2_manh = don.tui_2_manh or bool(spec.get("tui_2_manh"))
    don.gia_quai = spec.get("gia_quai")
    don.can_mang_2_mat = bool(spec.get("can_mang_2_mat"))
    don.uv_kt = tuple(spec["uv_kt"]) if spec.get("uv_kt") else None
    don.cua_so_kt = tuple(spec["cua_so_kt"]) if spec.get("cua_so_kt") else None
    don.day_2_gut = bool(spec.get("day_2_gut"))
    if spec.get("con_khuon"):
        don.con_khuon = spec["con_khuon"]
        don.mac_dinh = [m for m in don.mac_dinh if not m.startswith("khuôn bế 1 con")]
    don.gc_tuy_chinh = [(g["ten"], g["gia_moi_cai"]) for g in (spec.get("gia_cong_tuy_chinh") or [])]


def _ghi_mac_dinh_va_canh_bao(don: DonHang, spec: dict) -> None:
    """Ghi lại những gì bot tự lấy mặc định và những khoản còn ước tính, để tin trả lời nói rõ."""
    tp0 = don.thanh_phan[0]
    if don.loai_sp != "tem_decal":
        if not spec.get("giay"):
            don.mac_dinh.append(f"giấy {tp0.loai}")
        if not spec.get("dinh_luong"):
            don.mac_dinh.append(f"định lượng {tp0.gsm}g")
    if spec.get("so_mau") is None:
        don.mac_dinh.append(f"in {tp0.so_mau} màu")
    if not spec.get("so_mat") and tp0.so_mau:
        don.mac_dinh.append(f"{tp0.so_mat} mặt")
    if not spec.get("gia_cong") and not don.gc_tuy_chinh:
        don.mac_dinh.append("gia công cơ bản (bế, dán)")
    dac_biet = [x for x in (spec.get("ket_cau_dac_biet") or []) if not (x == "cửa sổ" and "cua_so" in don.gia_cong)]
    if dac_biet and don.co_kho_trai:
        don.uoc_tinh.append("kết cấu đặc biệt (" + ", ".join(dac_biet) + ") em tính như hộp thường, cần My xem lại")
    if not don.kho and don.co_kho_trai:
        don.uoc_tinh.append("khổ trải tính từ kích thước (chưa có file khuôn)")
    if don.bot_tai_dan and tp0.gsm >= 300 and not any(g in don.gia_cong for g in ("can_mo", "can_bong")):
        don.mac_dinh.append("không cán màng → " + P["canh_bao"]["giay_day_khong_can_mang"])


def dung_don(spec: dict) -> DonHang:
    loai = spec.get("loai") or LOAI_MAC_DINH
    mac = dac_tinh(loai)
    v = _DauVao(spec=spec,
                D=spec.get("dai") or 0, R=spec.get("rong") or 0, C=spec.get("cao") or 0,
                giay=spec.get("giay") or mac["giay"], gsm=spec.get("dinh_luong") or mac["gsm"],
                mau=4 if spec.get("so_mau") is None else spec["so_mau"], mat=spec.get("so_mat") or 1,
                gc=[g for g in (spec.get("gia_cong") or []) if g in P["gia_cong"]],
                ten=spec.get("san_pham") or "", kieu=(spec.get("kieu_hop") or "").lower())
    don = XAY_DUNG.get(loai, _hop_gap)(v)
    don.loai_sp = loai
    _ap_tuy_chinh(don, spec)
    _ghi_mac_dinh_va_canh_bao(don, spec)
    if don.gc_tuy_chinh:
        # gia công đã có đơn giá riêng trong tin thì bỏ bản mặc định cùng tên
        ten_tuy_chinh = " ".join(t.lower() for t, _ in don.gc_tuy_chinh)
        don.gia_cong = [g for g in don.gia_cong if P["gia_cong"][g]["ten"].split()[0].lower() not in ten_tuy_chinh]
    return don
