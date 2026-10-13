"""Tính giá vốn và giá bán của một đơn hàng. Cùng công thức sheet 'Đơn SLL' / 'Đơn số ít' trong Báo giá My.xlsx,
cộng các quy tắc My bổ sung (hộp cứng, in nhanh, gia công). Thuần số học, không có AI.

tinh() chạy lần lượt 6 bước, mỗi bước một hàm:
  1. chọn cách in (offset hay in nhanh)      4. kẽm + proof
  2. bình bài + giấy + tiền in từng thành phần   5. khuôn bế
  3. gia công                                  6. định giá bán
"""
import math
from dataclasses import dataclass

from .bang_gia import P
from .binh_bai import ups, ups_bot_tai
from .san_pham import DonHang, ThanhPhan


# ---------------------------------------------------------------- đơn giá cơ bản
def gia_to(W, H, loai, gsm):
    """Giá 1 tờ giấy = Dài × Rộng × gsm × giá/gam ÷ 10.000 (ô B28 trong Excel)."""
    if loai == "Decal":
        return W * H / 10000 * P["decal_gia_m2"]
    tr_tan = P["giay_tr_tan"].get(loai, P["giay_tr_tan"]["Couche"])
    mong = P.get("phu_phi_giay_mong")
    if mong and loai != "Chipboard" and gsm < mong["duoi_gsm"]:
        tr_tan *= 1 + mong["pct"]
    return W * H * gsm * tr_tan / 10000


def cong_in(so_to, so_mau, so_mat, so_tay=1):
    """Công in offset (ô B74): dưới 3.000 lượt tính tối thiểu theo số màu, từ 3.000 tính theo lượt."""
    if so_mau == 0:
        return 0
    luot = so_to * so_mat
    if luot < 3000:
        bang = P.get("cong_in_toi_thieu_theo_mau") or {}
        return so_tay * bang.get(str(int(so_mau)), so_mau * P["cong_in_toi_thieu_1_kem"])
    for nguong, don_gia in P["bac_cong_in"]:
        if luot < nguong:
            return so_tay * so_to * don_gia * so_mau * so_mat
    return so_tay * so_to * 60 * so_mau * so_mat


def gia_in_nhanh_to(W, H, so_mat):
    """Tiền in nhanh 1 tờ, ĐÃ GỒM GIẤY (My): tờ A4 in 1 mặt 2.000 đ, 2 mặt 3.000 đ; tờ dài hơn nhân theo số bản in."""
    bang = P["don_kts"]["bang_in"]
    dai = max(W, H)
    so_ban = next((n for gioi_han, n in bang["so_ban_in_theo_chieu_dai_cm"] if dai <= gioi_han), None)
    if so_ban is None:
        return None
    return so_ban * bang["gia_to_a4_gom_giay"]["2" if so_mat >= 2 else "1"]


def so_nhip(don: DonHang, tp: ThanhPhan, SL, con_to) -> int:
    """Số nhịp bế (My): số miếng cần bế ÷ số con trên khuôn. Khuôn 1 con: 1.600 cái = 1.600 nhịp; khuôn 2 con: 800 nhịp."""
    return math.ceil(SL * tp.con_moi_sp / (don.con_khuon or con_to))


def don_gia_nhip(don: DonHang, g: dict) -> float:
    """Đơn giá bế mỗi nhịp (My): khuôn chỉ có viền 450 đ, khuôn nhiều chi tiết bên trong (hộp, túi) 750 đ."""
    return g.get("gia_khuon_don_gian", g["gia"]) if don.khuon_don_gian else g["gia"]


def giay_in_nhanh_duoc(tp: ThanhPhan) -> bool:
    gioi_han = P["don_kts"].get("giay_cho_phep_gsm", {})
    return tp.loai in gioi_han and tp.gsm <= gioi_han[tp.loai]


def nen_in_nhanh(don: DonHang, SL: int) -> bool:
    """In nhanh được khi mọi thành phần có in đều lọt khổ in nhanh và giấy nằm trong mức máy nhận."""
    K = P["don_kts"]
    tong_to = 0
    for tp in don.thanh_phan:
        if not tp.so_mau:
            continue
        if not giay_in_nhanh_duoc(tp):
            return False
        u = max((ups(*k["kho"], tp.trai_w, tp.trai_h, le=K.get("le_cm")) for k in K["kho_in_nhanh"]), default=0)
        if u == 0:
            return False
        tong_to += SL * tp.con_moi_sp / u
    return tong_to > 0


def gia_niem_yet_decal(dai, rong, SL):
    """Giá bán đ/tem theo bảng My (decal giấy, cán bóng, cắt TP, offset), nội suy theo diện tích. None nếu ngoài điều kiện."""
    bang = P.get("bang_gia_decal_offset")
    if not bang or not dai or not rong or SL < bang["dieu_kien"]["so_luong_toi_thieu"]:
        return None
    cot = max(i for i, q in enumerate(bang["so_luong"]) if SL >= q)
    diem = sorted((float(k.split("x")[0]) * float(k.split("x")[1]), v[cot]) for k, v in bang["kich_thuoc"].items())
    dt = dai * rong
    if dt <= diem[0][0]:
        return diem[0][1]
    if dt >= diem[-1][0]:
        return diem[-1][1]
    for (a1, g1), (a2, g2) in zip(diem, diem[1:]):
        if a1 <= dt <= a2:
            return g1 + (g2 - g1) * (dt - a1) / (a2 - a1)
    return None


# ---------------------------------------------------------------- bước 2: bình bài + giấy + in
@dataclass
class PhuongAn:
    """Một cách in một thành phần trên một khổ giấy."""
    diem: float        # tổng tiền dùng để so sánh (giấy + in + kẽm + bế theo nhịp)
    W: float
    H: float
    con: int           # số con/tờ
    so_to: float
    gia_to: float
    tien_in: float
    bot_tai: float     # cm tai dán đã bớt
    so_kem: int
    nhan: str          # ghi chú kiểu bình (AB, tự trở…)


def _kho_ung_vien(don: DonHang, tp: ThanhPhan, kts: bool):
    """Các khổ giấy có thể in thành phần này, kèm (số con, cm bớt tai)."""
    K = P["don_kts"]
    if don.kho and don.con:                       # tin đã chỉ định khổ in và số con/tờ
        return [(don.kho, (don.con, 0))]
    in_nhanh = kts and tp.so_mau
    cac_kho = [k["kho"] for k in K["kho_in_nhanh"]] if in_nhanh else P["kho_giay"]
    duoc_bot_tai = don.bot_tai_dan and tp.loai not in ("Chipboard", "Decal") and tp.con_moi_sp == 1
    le = K.get("le_cm") if in_nhanh else None
    ung_vien = [((W, H), ups_bot_tai(W, H, tp.trai_w, tp.trai_h, duoc_bot_tai, le=le)) for W, H in cac_kho]
    return [(kho, uc) for kho, uc in ung_vien if uc[0]]


def _to_sua_bai(don: DonHang, W, H, kts: bool) -> int:
    if don.tu_sua_bai is not None:
        return don.tu_sua_bai
    if kts:
        return P["don_kts"]["tu_sua_bai"]
    return P.get("tu_sua_bai_theo_kho", {}).get(f"{W}x{H}", P["tu_sua_bai"])


def _cac_cach_in(don: DonHang, tp: ThanhPhan, SL, kts, W, H, con, bot_tai):
    """Các cách in thành phần trên một khổ: in nhanh; offset 1 mặt; offset 2 mặt bình AB hoặc tự trở."""
    sua = _to_sua_bai(don, W, H, kts)
    so_to = SL * tp.con_moi_sp / con * P["hao_hut"] + (sua if tp.so_mau else 10)
    if don.gia_giay and tp.loai not in ("Chipboard", "Decal"):
        gt = W * H * tp.gsm * don.gia_giay / 10000
    else:
        gt = gia_to(W, H, tp.loai, tp.gsm)
    kem = P["gia_kem"]
    if kts and not tp.so_mau:                      # thành phần không in của lô in nhanh: chỉ có tiền giấy
        return [PhuongAn(so_to * gt, W, H, con, so_to, gt, 0, bot_tai, 0, "")]
    if kts:
        gia_1_to = gia_in_nhanh_to(W, H, tp.so_mat)
        if gia_1_to is None:                       # tờ dài quá mức máy in nhanh
            return []
        tien_in = so_to * gia_1_to                 # đã gồm giấy thường nên giá tờ = 0; decal vẫn tính tiền decal
        gt = gt if tp.loai == "Decal" else 0
        return [PhuongAn(so_to * gt + tien_in, W, H, con, so_to, gt, tien_in, bot_tai, 0, "")]
    if tp.so_mat == 2 and tp.so_mau:
        cach = []
        if don.kieu_2_mat in (None, "AB"):         # AB: 2 bộ kẽm, đủ con/tờ, 2 tay in
            ti = cong_in(so_to, tp.so_mau, 1, so_tay=2)
            cach.append(PhuongAn(so_to * gt + ti + tp.so_mau * 2 * kem, W, H, con, so_to, gt, ti, bot_tai, tp.so_mau * 2, "bình AB (2 bộ kẽm)"))
        if con >= 2 and don.kieu_2_mat in (None, "tu_tro", "tro_nhip"):   # tự trở / trở nhíp: 1 bộ kẽm, nửa số con, in 2 lượt
            con2 = con // 2
            so_to2 = SL * tp.con_moi_sp / con2 * P["hao_hut"] + sua
            ti = cong_in(so_to2, tp.so_mau, 2, so_tay=1)
            ten = "bình trở nhíp" if don.kieu_2_mat == "tro_nhip" else "bình tự trở"
            cach.append(PhuongAn(so_to2 * gt + ti + tp.so_mau * kem, W, H, con2, so_to2, gt, ti, bot_tai, tp.so_mau, f"{ten} (1 bộ kẽm, {con2} con/tờ)"))
        return cach
    tien_in = cong_in(so_to, tp.so_mau, tp.so_mat)
    so_kem = tp.so_mau * tp.so_mat
    return [PhuongAn(so_to * gt + tien_in + so_kem * kem, W, H, con, so_to, gt, tien_in, bot_tai, so_kem, "")]


def _binh_bai_re_nhat(don: DonHang, tp: ThanhPhan, SL, kts, ung_vien):
    """Bình bài ảo: thử mọi khổ và mọi cách in, lấy phương án rẻ nhất (tính cả bế theo nhịp: ít tờ hơn thì bế rẻ hơn)."""
    be = next((k for k in ("be", "be_hop_cung", "be_demi") if k in don.gia_cong), None)
    gia_nhip = don_gia_nhip(don, P["gia_cong"][be]) if (be and P["gia_cong"][be].get("don_vi") == "nhip") else 0
    tot = None
    for (W, H), (con, bot_tai) in ung_vien:
        for pa in _cac_cach_in(don, tp, SL, kts, W, H, con, bot_tai):
            pa.diem += so_nhip(don, tp, SL, pa.con) * gia_nhip
            if tot is None or pa.diem < tot.diem:
                tot = pa
    return tot


def _so(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


def _tinh_thanh_phan(don: DonHang, SL, kts, r, tam):
    """Bước 2. Ghi dòng giấy + in của từng thành phần vào r, cộng dồn số liệu trung gian vào tam."""
    for tp in don.thanh_phan:
        ung_vien = _kho_ung_vien(don, tp, kts)
        if not ung_vien:
            r.setdefault("vuot_kho", []).append((tp.ten, tp.trai_w, tp.trai_h))
            continue
        pa = _binh_bai_re_nhat(don, tp, SL, kts, ung_vien)
        if pa is None:
            r["dong"].append((f"{tp.ten}: không có phương án in phù hợp (khổ {tp.trai_w}×{tp.trai_h}, {tp.so_mat} mặt)", 0))
            r["uoc_tinh"].append(f"{tp.ten.lower()} chưa tính được, kiểm tra khổ/số mặt")
            continue
        r.setdefault("bai_binh", []).append((pa.W, pa.H, pa.con, tp.trai_w - pa.bot_tai, tp.trai_h))
        if pa.nhan:
            r["dong"].append((f"{tp.ten}: {pa.nhan}", 0))
        if pa.bot_tai:
            r["uoc_tinh"].append(f"{tp.ten.lower()}: bớt tai dán {pa.bot_tai} cm để xếp {pa.con} con/tờ {pa.W}×{pa.H}, My duyệt")
        if not kts:
            tam["so_kem"] += pa.so_kem
            if tp.so_mau and pa.so_to * tp.so_mat < 3000:      # công in tối thiểu là chi phí cố định
                r["co_dinh"] += pa.tien_in
        tien_giay = pa.so_to * pa.gia_to
        tam["tong_nhip"] += so_nhip(don, tp, SL, pa.con)
        ten_giay = "Decal giấy" if tp.loai == "Decal" else f"{tp.ten} {tp.loai} {tp.gsm}g"
        trai = f"trải {_so(tp.trai_w - pa.bot_tai)}×{_so(tp.trai_h)}, " if don.co_kho_trai else ""
        bai = f"{trai}{pa.con} con/tờ {pa.W}×{pa.H}, {_fmt(pa.so_to)} tờ"
        if kts and tp.so_mau:                      # in nhanh: một dòng, giá tờ đã gồm giấy
            if tien_giay:
                r["dong"].append((f"{ten_giay} ({bai})", tien_giay))
            r["dong"].append((f"In nhanh {tp.ten if tien_giay else ten_giay} {tp.so_mat} mặt{'' if tien_giay else ', gồm giấy'} ({bai})", pa.tien_in))
            tam["dong_in_nhanh"].append(len(r["dong"]) - 1)
            tam["in_nhanh"] += pa.tien_in
        else:
            r["dong"].append((f"{ten_giay} ({bai})", tien_giay))
            if pa.tien_in:
                r["dong"].append((f"Công in {tp.so_mau} màu {tp.so_mat} mặt {tp.ten.lower()}", pa.tien_in))
        tam["tong"] += tien_giay + pa.tien_in


def thiep_cat_thang(don: DonHang) -> bool:
    """Thiệp / card chỉ in rồi cắt, không bế: My có giá riêng theo tờ A4 nên không áp tối thiểu lô in nhanh."""
    return don.loai_sp == "thiep" and "be" not in don.gia_cong


def _ap_toi_thieu_lo_in_nhanh(don: DonHang, r, tam):
    """My: đơn ít tính tiền in nhanh theo lô (dàn bài, set máy, khấu hao, thợ), không theo con."""
    san = P["don_kts"].get("in_toi_thieu_lo", 0)
    if not tam["dong_in_nhanh"] or tam["in_nhanh"] >= san or thiep_cat_thang(don):
        return
    i = tam["dong_in_nhanh"][0]
    ten, tien = r["dong"][i]
    r["dong"][i] = (ten.replace(" (", ", tối thiểu lô (", 1), tien + san - tam["in_nhanh"])
    tam["tong"] += san - tam["in_nhanh"]


# ---------------------------------------------------------------- bước 3: gia công
def dien_tich_gia_cong(key, don: DonHang) -> float:
    """m² giấy của MỘT sản phẩm mà công đoạn tính theo diện tích phải làm (cán màng, bồi). Không tính carton.
    Hộp cứng: áo + lót (My: cả hai đều cán màng, đều bồi lên carton). Bồi giấy 2 lớp: diện tích một lớp bồi.
    Còn lại: cán màng phần có in."""
    def m2(ds):
        return sum(tp.trai_w * tp.trai_h * tp.con_moi_sp for tp in ds) / 10000
    giay = [tp for tp in don.thanh_phan if tp.loai != "Chipboard"]
    lop_boi = [tp for tp in giay if tp.ten == "Lớp giấy bồi"]
    if key == "boi_giay":
        return m2(lop_boi or giay[:1])
    if don.loai_sp == "hop_cung":
        return m2(giay)
    return m2([tp for tp in giay if tp.so_mau] or [tp for tp in giay if tp not in lop_boi] or giay)


def _gc_theo_m2(key, g, don, SL, tam, r):
    he_so = 2 if (key in ("can_mo", "can_bong") and don.can_mang_2_mat) else 1
    tien = max(SL * dien_tich_gia_cong(key, don) * g["gia"] * he_so, g.get("san", 0))
    return (g["ten"] + " 2 mặt" if he_so == 2 else g["ten"]), tien, 0


def _gc_theo_lo(key, g, don, SL, tam, r):
    return g["ten"], g["gia"], 0


def _gc_theo_nhip(key, g, don, SL, tam, r):
    """Bế: mỗi tờ một nhịp; đơn giá theo độ phức tạp của khuôn; hộp cứng tối thiểu tính theo số khuôn (mỗi khuôn một lô)."""
    nhip = tam["tong_nhip"]
    don_gia = don_gia_nhip(don, g)
    so_lo = max(don.khuon_be, 1)
    san = g["san_moi_khuon"] * so_lo if g.get("san_moi_khuon") else g.get("san", 0)
    tien = max(nhip * don_gia, san)
    cham_san = f", tối thiểu {so_lo} lô" if tien == san and g.get("san_moi_khuon") else ""
    khuon = f", khuôn {don.con_khuon} con" if don.con_khuon else ""
    return f"{g['ten']} ({_fmt(nhip)} nhịp × {don_gia}đ{khuon}{cham_san})", tien, 0


def _gc_theo_mep(key, g, don, SL, tam, r):
    """Dán hộp (My): khoảng 100 đ mỗi mép dán, một hộp ít nhất 200 đ."""
    moi_cai = max(g["gia"] * don.so_mep_dan, g.get("toi_thieu_moi_cai", 0))
    tien = max(SL * moi_cai, g.get("san", 0))
    return f"{g['ten']} ({don.so_mep_dan} mép, {_fmt(moi_cai)}đ/cái)", tien, 0


VUNG_MAC_DINH = {"ep_kim": (10, 5), "dap_noi": (10, 5), "uv_dinh_vi": (10, 5), "cua_so": (8, 8)}


def _gc_theo_cm2(key, g, don, SL, tam, r):
    """Ép kim, dập nổi, UV định hình, dán cửa sổ: dài × rộng (cm) × đơn giá.
    Khuôn ép kim / dập nổi tính theo diện tích ép; dập nổi âm dương có đơn giá riêng và 2 khuôn."""
    kt_tin = {"ep_kim": don.ep_kim_kt, "dap_noi": don.dap_noi_kt, "uv_dinh_vi": don.uv_kt, "cua_so": don.cua_so_kt}.get(key)
    kt = kt_tin or VUNG_MAC_DINH.get(key, (10, 5))
    if not kt_tin:
        r["mac_dinh"].append(f"vùng {g['ten'].lower()} {kt[0]}×{kt[1]} cm")
    am_duong = key == "dap_noi" and don.dap_noi_am_duong
    don_gia = g["gia_am_duong"] if am_duong else g["gia"]
    ten = "Dập nổi âm dương" if am_duong else g["ten"]
    dien_tich = kt[0] * kt[1]
    tien = max(SL * dien_tich * don_gia, g.get("san", 0))
    khuon = dien_tich * g.get("khuon_cm2", 0) * (2 if am_duong else 1)
    return f"{ten} ({_so(kt[0])}×{_so(kt[1])} cm × {_so(don_gia)}đ)", tien, khuon


def _gc_theo_met_toi(key, g, don, SL, tam, r):
    """Phay rãnh chipboard (My): 3 đ/mét tới, ít nhất 300k/lô. Mỗi miếng phay 4 đường nên mét tới ≈ chu vi miếng."""
    met = SL * sum(2 * (tp.trai_w + tp.trai_h) / 100 * tp.con_moi_sp for tp in don.thanh_phan if tp.loai == "Chipboard")
    san = g.get("san", 0)
    tien = max(met * g["gia"], san)
    return f"{g['ten']} ({_fmt(met)} mét tới × {_so(g['gia'])}đ{', tối thiểu lô' if tien == san else ''})", tien, 0


def _gc_day_treo(key, g, don, SL, tam, r):
    if don.day_2_gut:
        return g["ten"] + " (2 gút)", SL * g["gia_2_gut"], 0
    r["mac_dinh"].append("dây treo 1 gút 200đ (2 gút 300đ)")
    return g["ten"] + " (1 gút)", SL * g["gia"], 0


def _gc_dan_tui(key, g, don, SL, tam, r):
    if don.tui_2_manh:
        return g["ten"] + " (2 mảnh)", max(SL * g["gia_2_manh"], g["san_2_manh"]), 0
    return g["ten"] + " (1 mảnh)", max(SL * g["gia"], g["san"]), 0


def _gc_quai_tui(key, g, don, SL, tam, r):
    if not don.gia_quai:
        r["mac_dinh"].append("quai dây phổ thông 350đ/cặp")
    return g["ten"], SL * (don.gia_quai or g["gia"]), 0


def _gc_theo_con(key, g, don, SL, tam, r):
    return g["ten"], max(SL * g["gia"], g.get("san", 0)), 0


CACH_TINH_GIA_CONG = {"m2": _gc_theo_m2, "lo": _gc_theo_lo, "nhip": _gc_theo_nhip, "mep": _gc_theo_mep, "cm2": _gc_theo_cm2,
                      "met_toi": _gc_theo_met_toi}
CACH_TINH_RIENG = {"dan_tui": _gc_dan_tui, "quai_tui": _gc_quai_tui, "day_treo": _gc_day_treo}


def _tinh_gia_cong(don: DonHang, SL, kts, r, tam):
    """Bước 3. Gia công có đơn giá trong tin trước, rồi tới gia công theo bảng giá. Lô in nhanh: mỗi nhóm công đoạn tối thiểu 300k."""
    for ten, gia in don.gc_tuy_chinh:
        r["dong"].append((ten, SL * gia))
        tam["tong"] += SL * gia
    vi_tri, tien_theo_key = {}, {}
    for key in don.gia_cong:
        g = P["gia_cong"].get(key)
        if not g:
            continue
        if g.get("cong_vao_gia_ban"):              # My cộng thẳng vào giá bán, không nhân lãi (nắp kéo +15k/hộp)
            r["phu_thu_ban"] = r.get("phu_thu_ban", 0) + g["gia"]
            continue
        cach_tinh = CACH_TINH_GIA_CONG.get(g["don_vi"]) or CACH_TINH_RIENG.get(key) or _gc_theo_con
        nhan, tien, khuon = cach_tinh(key, g, don, SL, tam, r)
        r["dong"].append((nhan, tien))
        vi_tri[key], tien_theo_key[key] = len(r["dong"]) - 1, tien
        tam["tong"] += tien
        if khuon:
            r["dong"].append(("Khuôn " + nhan.split(" (")[0].lower(), khuon))
            tam["tong"] += khuon
            r["co_dinh"] += khuon
        if g.get("uoc_tinh") and not (don.loai_sp == "hop_cung" and key == "dung_hop"):
            r["uoc_tinh"].append(f"đơn giá {g['ten'].lower()}")
    if not kts:
        return
    if don.co_in:
        vuot = [f"{tp.loai} {tp.gsm}g" for tp in don.thanh_phan if tp.so_mau and not giay_in_nhanh_duoc(tp)]
        if vuot:
            r["uoc_tinh"].append("máy in nhanh chỉ nhận Couche ≤300g, Ivory/Bristol ≤250g; " + ", ".join(vuot) + " cần My xem")
    for nhom in P["don_kts"]["phi_lo"].values():                 # sổ tay My: cán, bế, bồi, dán, support mỗi khoản 300k/lô
        co = [k for k in nhom["thay_cho"] if k in tien_theo_key]
        con_thieu = nhom["gia"] - sum(tien_theo_key[k] for k in co)
        if co and con_thieu > 0:
            i = vi_tri[co[0]]
            r["dong"][i] = (r["dong"][i][0] + " (tối thiểu lô)", r["dong"][i][1] + con_thieu)
            tam["tong"] += con_thieu


# ---------------------------------------------------------------- bước 4, 5: kẽm, proof, khuôn
def _tinh_kem_proof(don: DonHang, r, tam):
    tien_kem = tam["so_kem"] * P["gia_kem"]
    if not tien_kem:
        return
    r["dong"].append((f"Kẽm CTP {tam['so_kem']} bản", tien_kem))
    tam["tong"] += tien_kem
    r["co_dinh"] += tien_kem
    if don.proof and P.get("proof_toi_thieu"):
        r["dong"].append(("Proof", P["proof_toi_thieu"]))
        tam["tong"] += P["proof_toi_thieu"]
        r["co_dinh"] += P["proof_toi_thieu"]


def _gia_mot_khuon(don: DonHang, r) -> float:
    """Khuôn bế 150k–600k theo diện tích bài bình; túi và hộp carton lấy mức cao nhất (My)."""
    KB = P.get("khuon_be_theo_kich_thuoc")
    if not KB:
        return P["khuon_be"]
    if don.loai_sp in KB["loai_cao_nhat"]:
        gia = KB["toi_da"]
    else:
        dt_bai = max(((don.con_khuon or con) * w * h for (_, _, con, w, h) in r.get("bai_binh", [])), default=KB["full_kho_cm2"])
        gia = min(KB["toi_da"], max(KB["toi_thieu"], KB["toi_thieu"] + (KB["toi_da"] - KB["toi_thieu"]) * dt_bai / KB["full_kho_cm2"]))
    return round(gia / 10000) * 10000


def _tinh_khuon(don: DonHang, r, tam):
    if not don.khuon_be:
        return
    if don.khuon_co_san:
        r["dong"].append(("Khuôn bế: có sẵn", 0))
        return
    tien = don.khuon_be_tien if don.khuon_be_tien is not None else don.khuon_be * _gia_mot_khuon(don, r)
    r["dong"].append((f"Khuôn bế ×{don.khuon_be}", tien))
    tam["tong"] += tien
    r["co_dinh"] += tien


# ---------------------------------------------------------------- bước 6: định giá
def _lam_tron_len(gia: float) -> float:
    """Từ 10.000 đ: tròn LÊN 1.000 đ. Dưới 10.000 đ: tròn về mức gần nhất (100 đ, hoặc 10 đ nếu dưới 1.000 đ),
    vì tròn lên 100 đ làm hàng rẻ đội thêm 5–6% (đơn tấm C100: tính ra 1.609 đ, My báo 1.600 đ)."""
    if gia >= 10000:
        return math.ceil(gia / P["lam_tron"]) * P["lam_tron"]
    buoc = 10 if gia < 1000 else 100
    return max(buoc, math.floor(gia / buoc + 0.5) * buoc)


def _ap_gia_niem_yet(don: DonHang, SL, kts, r):
    """Hai trường hợp My có giá bán sẵn, không tính từ giá vốn: decal offset lô lớn, thiệp in nhanh 2 mặt."""
    if not don.thanh_phan:
        return
    tp = don.thanh_phan[0]
    if don.loai_sp == "tem_decal":
        gia = gia_niem_yet_decal(tp.trai_w - 0.4, tp.trai_h - 0.4, SL)
        if gia:
            r["niem_yet_nguon"] = "bảng decal offset của My (cán bóng, cắt thành phẩm, nội suy theo kích thước)"
            r["niem_yet"] = r["gia_ban"] = gia
            r["gia_ban_tron"] = math.ceil(gia / 10) * 10
    K = P["don_kts"]
    thiep = K.get("thiep_a4_2_mat")
    if kts and thiep and thiep_cat_thang(don) and tp.so_mau and tp.so_mat == 2 and don.pct_ln is None:
        con_a4 = ups(21, 29.7, tp.trai_w, tp.trai_h, bu_xen=0, le=K.get("le_cm"))
        if con_a4:
            gia = math.ceil(SL / con_a4) * thiep["gia_ban_moi_to"] / SL
            r["niem_yet"] = r["gia_ban"] = gia
            r["niem_yet_nguon"] = f"giá My cho thiệp in nhanh: 10.000 đ một tờ A4 in 2 mặt, {con_a4} con/tờ"
            r["gia_ban_tron"] = math.ceil(gia / 100) * 100


def _dinh_gia(don: DonHang, SL, kts, r, tam):
    r["vat_tu"] = tam["tong"]
    r["van_chuyen"] = tam["tong"] * P["pct_van_chuyen"]
    r["chi_phi"] = tam["tong"] + r["van_chuyen"]
    r["gia_von"] = r["chi_phi"] / SL
    if don.pct_ln is not None:
        lai = don.pct_ln
    else:
        lai = next((pc for nguong, pc in P.get("bac_loi_nhuan", {}).get("bac", []) if SL < nguong), P["pct_loi_nhuan"])
        lai = max(lai, P.get("pct_loi_nhuan_theo_loai", {}).get(don.loai_sp, 0))      # hộp cứng ít nhất 40% (My)
    r["pct_ln"] = lai
    r["gia_ban"] = r["chi_phi"] * (1 + lai) / SL + r.get("phu_thu_ban", 0)
    r["gia_ban_tron"] = _lam_tron_len(r["gia_ban"])
    _ap_gia_niem_yet(don, SL, kts, r)


# ---------------------------------------------------------------- hàm chính
def tinh(don: DonHang, SL: int, kts: bool = None) -> dict:
    """Tính một mức số lượng. kts=None: theo tin nhắn, nếu tin không nói thì lấy cách in rẻ hơn.
    Trả về dict: SL, dong [(tên khoản, tiền)], co_dinh, vat_tu, chi_phi, gia_von, pct_ln, gia_ban, gia_ban_tron, kts,
    uoc_tinh, mac_dinh, và nếu có: vuot_kho, bai_binh, niem_yet, niem_yet_nguon, phu_thu_ban (đ/cái cộng thẳng vào giá bán)."""
    if kts is None:
        if don.kts is not None:
            kts = don.kts
        elif nen_in_nhanh(don, SL):               # bước 1: in nhanh khả thi → lấy cách có giá bán thấp hơn
            nhanh, offset = tinh(don, SL, True), tinh(don, SL, False)      # so giá bán vì thiệp in nhanh có giá niêm yết riêng
            re_hon = (nhanh["gia_ban"], nhanh["chi_phi"]) <= (offset["gia_ban"], offset["chi_phi"])
            return nhanh if (offset.get("vuot_kho") or re_hon) else offset
        else:
            kts = False
    r = {"SL": SL, "dong": [], "co_dinh": 0.0, "uoc_tinh": list(don.uoc_tinh), "mac_dinh": list(don.mac_dinh), "kts": kts}
    tam = {"tong": 0.0, "so_kem": 0, "tong_nhip": 0.0, "in_nhanh": 0.0, "dong_in_nhanh": []}
    _tinh_thanh_phan(don, SL, kts, r, tam)
    if kts:
        _ap_toi_thieu_lo_in_nhanh(don, r, tam)
    _tinh_kem_proof(don, r, tam)
    _tinh_gia_cong(don, SL, kts, r, tam)
    _tinh_khuon(don, r, tam)
    _dinh_gia(don, SL, kts, r, tam)
    return r


def _fmt(n):
    return f"{n:,.0f}".replace(",", ".")
