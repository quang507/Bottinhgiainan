"""Engine tính giá GÓI - cùng công thức sheet 'Đơn SLL' / 'Đơn số ít' trong Báo giá My.xlsx.
Thuần số học, không có AI; kiểm chứng bằng `python -m goi.engine`."""
import json
import math
import os
from dataclasses import dataclass, field

P = json.load(open(os.path.join(os.path.dirname(__file__), "prices.json"), encoding="utf-8"))


def _grid_plus_strip(W, H, w, h):
    """Lưới chính w×h, phần dư bên phải và bên dưới xếp con xoay 90°."""
    c, r = math.floor(W / w), math.floor(H / h)
    if c == 0 or r == 0:
        return 0
    n = c * r
    phai = math.floor((W - c * w) / h) * math.floor(H / w)          # dải dư bên phải, con xoay
    duoi = math.floor(W / h) * math.floor((H - r * h) / w)          # dải dư bên dưới, con xoay
    return n + max(phai, duoi)


def ups(W, H, w, h, bu_xen=None):
    """Số con/tờ: trừ lề kẹp nhíp 1 cạnh, cộng bù xén quanh mỗi con, thử 2 chiều, lưới + dải dư xoay con."""
    if not w or not h:
        return 0
    BB = P.get("binh_bai", {})
    le = BB.get("le_nhip_cm", 0)
    bx = BB.get("bu_xen_cm", {}).get("hop_gap", 0) if bu_xen is None else bu_xen
    W2, H2, w2, h2 = W, H - le, w + bx, h + bx
    return max(_grid_plus_strip(W2, H2, w2, h2), _grid_plus_strip(W2, H2, h2, w2), _grid_plus_strip(H2, W2, w2, h2), _grid_plus_strip(H2, W2, h2, w2))


CAT_TAI = (0, 0.5, 1.0, 1.5)   # mức bớt tai dán (cm) được phép thử


def ups_cat_tai(W, H, w, h, cho_phep=True):
    """Trả về (số con, cm đã bớt) – chỉ bớt tai khi nhờ đó thêm được con."""
    best = (ups(W, H, w, h), 0)
    if not cho_phep:
        return best
    for t in CAT_TAI[1:]:
        u = max(ups(W, H, w - t, h), ups(W, H, w, h - t), ups(W, H, w - t, h - t))
        if u > best[0]:
            best = (u, t)
    return best


def chon_kho(w, h, kho_list=None):
    """Chọn khổ giấy cho tỉ lệ dùng giấy cao nhất. Trả về ((W,H), số con, hiệu suất) hoặc None."""
    best = None
    for W, H in (kho_list or P["kho_giay"]):
        u = ups(W, H, w, h)
        if u == 0:
            continue
        eff = u * w * h / (W * H)
        if best is None or eff > best[2] + 1e-9:
            best = ((W, H), u, eff)
    return best


def gia_to(W, H, loai, gsm):
    """Giá 1 tờ giấy = Dài × Rộng × gsm × giá/gam ÷ 10.000 (ô B28)."""
    if loai == "Decal":
        return W * H / 10000 * P["decal_gia_m2"]
    tr_tan = P["giay_tr_tan"].get(loai, P["giay_tr_tan"]["Couche"])
    m = P.get("phu_phi_giay_mong")
    if m and loai != "Chipboard" and gsm < m["duoi_gsm"]:
        tr_tan *= 1 + m["pct"]
    return W * H * gsm * tr_tan / 10000


def cong_in(so_to, so_mau, so_mat, so_tay=1):
    """Ô B74: dưới 3.000 lượt tính tối thiểu theo kẽm, từ 3.000 tính theo lượt."""
    if so_mau == 0:
        return 0
    luot = so_to * so_mat
    if luot < 3000:
        bang = P.get("cong_in_toi_thieu_theo_mau") or {}
        return so_tay * bang.get(str(int(so_mau)), so_mau * P["cong_in_toi_thieu_1_kem"])
    for nguong, rate in P["bac_cong_in"]:
        if luot < nguong:
            return so_tay * so_to * rate * so_mau * so_mat
    return so_tay * so_to * 60 * so_mau * so_mat


@dataclass
class ThanhPhan:
    ten: str
    loai: str
    gsm: int
    trai_w: float
    trai_h: float
    con_moi_sp: int = 1      # số miếng loại này cho 1 sản phẩm
    so_mau: int = 4
    so_mat: int = 1
    uoc_tinh: bool = False


@dataclass
class DonHang:
    ten: str
    thanh_phan: list
    gia_cong: list = field(default_factory=list)   # key trong prices.gia_cong
    khuon_be: int = 1
    uoc_tinh: list = field(default_factory=list)
    # tuỳ chỉnh theo tin nhắn (None = dùng prices.json)
    gia_giay: float = None
    tu_sua_bai: int = None
    kho: tuple = None
    con: int = None
    pct_ln: float = None
    khuon_be_tien: float = None
    proof: bool = True
    gc_tuy_chinh: list = field(default_factory=list)   # [(tên, đ/cái)]
    mac_dinh: list = field(default_factory=list)       # thông số khách không nói, bot tự lấy
    kts: bool = None                                   # None = tự chọn theo số lượng
    khuon_co_san: bool = False
    kieu_2_mat: str = None                             # AB | tu_tro | tro_nhip | None = tự chọn rẻ nhất
    loai_sp: str = ""
    ep_kim_kt: tuple = None
    dap_noi_kt: tuple = None
    dap_noi_am_duong: bool = False
    so_mep_dan: int = 1
    tui_2_manh: bool = False
    gia_quai: float = None
    can_mang_2_mat: bool = False


def nen_in_nhanh(don: DonHang, SL: int) -> bool:
    """Quy tắc My: dưới 500 tờ và mọi thành phần in lọt khổ 33×60 thì in nhanh."""
    K = P["don_kts"]
    tong_to = 0
    for tp in don.thanh_phan:
        if not tp.so_mau:
            continue
        u = max(ups(*k["kho"], tp.trai_w, tp.trai_h) for k in K["kho_in_nhanh"])
        if u == 0:
            return False
        tong_to += SL * tp.con_moi_sp / u
    return 0 < tong_to < K["nguong_to"]


def tinh(don: DonHang, SL: int, kts: bool = None):
    K = P["don_kts"]
    if kts is None:
        kts = don.kts if don.kts is not None else nen_in_nhanh(don, SL)
    r = {"SL": SL, "dong": [], "co_dinh": 0.0, "uoc_tinh": list(don.uoc_tinh), "mac_dinh": list(don.mac_dinh), "kts": kts}
    tong = 0.0
    dien_tich_sp = 0.0
    kem = 0
    tong_nhip = 0.0
    for tp in don.thanh_phan:
        # Chọn khổ theo tổng chi phí giấy + in thấp nhất (bình bài ảo), trừ khi tin đã chỉ định khổ/số con
        ung_vien = [(don.kho, don.con)] if (don.kho and don.con) else             [((W, H), ups_cat_tai(W, H, tp.trai_w, tp.trai_h, don.loai_sp in ("hop_gap", "tui_giay") and tp.loai not in ("Chipboard", "Decal") and tp.con_moi_sp == 1)) for W, H in (([k["kho"] for k in K["kho_in_nhanh"]]) if (kts and tp.so_mau) else P["kho_giay"])]
        ung_vien = [(k, u) for k, u in ung_vien if (u[0] if isinstance(u, tuple) else u)]
        if not ung_vien:
            r["dong"].append((f"{tp.ten}: khổ trải {tp.trai_w}×{tp.trai_h} vượt khổ giấy", 0))
            continue
        tot_nhat = None
        for (W, H), u in ung_vien:
            u, cat = (u if isinstance(u, tuple) else (u, 0))
            if don.tu_sua_bai is not None:
                sua = don.tu_sua_bai
            elif kts:
                sua = K["tu_sua_bai"]
            else:
                sua = P.get("tu_sua_bai_theo_kho", {}).get(f"{W}x{H}", P["tu_sua_bai"])
            so_to = SL * tp.con_moi_sp / u * P["hao_hut"] + (sua if tp.so_mau else 10)
            gt = (W * H * tp.gsm * don.gia_giay / 10000) if (don.gia_giay and tp.loai not in ("Chipboard", "Decal")) else gia_to(W, H, tp.loai, tp.gsm)
            phuong_an = []
            if kts:
                kk = next((k for k in K["kho_in_nhanh"] if k["kho"] == [W, H]), None)
                gia_to_in = (kk["gia_2_mat"] if tp.so_mat == 2 else kk["gia_1_mat"]) if kk else None
                if gia_to_in is None and tp.so_mau:
                    continue   # khổ này không in được số mặt yêu cầu
                if tp.so_mau and kk:
                    tien_in = so_to * gia_to_in
                    if kk.get("uoc_tinh") or (tp.so_mat != 2 and kk.get("uoc_tinh_1_mat")):
                        nhan_kts = f"in KTS {kk['ten']} {fmt(gia_to_in)}đ/tờ (ước tính)"
                    else:
                        nhan_kts = f"in KTS {kk['ten']} {fmt(gia_to_in)}đ/tờ {tp.so_mat} mặt"
                else:
                    tien_in, nhan_kts = 0, ""
                phuong_an.append((so_to * gt + tien_in, u, so_to, tien_in, 0, nhan_kts))
            elif tp.so_mat == 2 and tp.so_mau:
                # AB: 2 bộ kẽm, đủ con/tờ, 2 tay in
                if don.kieu_2_mat in (None, "AB"):
                    ti = cong_in(so_to, tp.so_mau, 1, so_tay=2)
                    phuong_an.append((so_to * gt + ti + tp.so_mau * 2 * P["gia_kem"], u, so_to, ti, tp.so_mau * 2, "bình AB (2 bộ kẽm)"))
                # Tự trở / trở nhíp: 1 bộ kẽm, nửa số con, in 2 lượt
                if u >= 2 and don.kieu_2_mat in (None, "tu_tro", "tro_nhip"):
                    u2 = u // 2
                    so_to2 = SL * tp.con_moi_sp / u2 * P["hao_hut"] + sua
                    ti = cong_in(so_to2, tp.so_mau, 2, so_tay=1)
                    ten = "bình trở nhíp" if don.kieu_2_mat == "tro_nhip" else "bình tự trở"
                    phuong_an.append((so_to2 * gt + ti + tp.so_mau * P["gia_kem"], u2, so_to2, ti, tp.so_mau, f"{ten} (1 bộ kẽm, {u2} con/tờ)"))
            else:
                tien_in = cong_in(so_to, tp.so_mau, tp.so_mat)
                phuong_an.append((so_to * gt + tien_in + tp.so_mau * tp.so_mat * P["gia_kem"], u, so_to, tien_in, tp.so_mau * tp.so_mat, ""))
            for tong_tp, u_, so_to_, tien_in_, kem_, nhan in phuong_an:
                if tot_nhat is None or tong_tp < tot_nhat[0]:
                    tot_nhat = (tong_tp, W, H, u_, so_to_, gt, tien_in_, cat, kem_, nhan)
        if tot_nhat is None:
            r["dong"].append((f"{tp.ten}: không có phương án in phù hợp (khổ {tp.trai_w}×{tp.trai_h}, {tp.so_mat} mặt)", 0))
            r["uoc_tinh"].append(f"{tp.ten.lower()} chưa tính được, kiểm tra khổ/số mặt")
            continue
        _, W, H, u, so_to, gt, tien_in, cat, kem_tp, nhan = tot_nhat
        r.setdefault("bai_binh", []).append((W, H, u, tp.trai_w - cat, tp.trai_h))
        if nhan and "(ước tính)" in nhan:
            r["uoc_tinh"].append(nhan)
        elif nhan:
            r["dong"].append((f"{tp.ten}: {nhan}", 0))
        if cat:
            r["uoc_tinh"].append(f"{tp.ten.lower()}: bớt tai dán {cat} cm để xếp {u} con/tờ {W}×{H}, My duyệt")
        if not kts:
            kem += kem_tp
            if tp.so_mau and so_to * tp.so_mat < 3000:
                r["co_dinh"] += tien_in
        tien_giay = so_to * gt
        tong_nhip += so_to
        dien_tich_sp += tp.trai_w * tp.trai_h * tp.con_moi_sp / 10000
        nhan_giay = "Decal giấy" if tp.loai == "Decal" else f"{tp.ten} {tp.loai} {tp.gsm}g"
        def _so(x):
            return str(int(x)) if float(x).is_integer() else f"{x:.1f}"
        trai = f"trải {_so(tp.trai_w - cat)}×{_so(tp.trai_h)}, " if don.loai_sp in ("hop_gap", "hop_cung", "tui_giay") else ""
        r["dong"].append((f"{nhan_giay} ({trai}{u} con/tờ {W}×{H}, {fmt(so_to)} tờ)", tien_giay))
        if tien_in:
            r["dong"].append(((f"In KTS {fmt(so_to)} tờ" if kts else f"Công in {tp.so_mau} màu {tp.so_mat} mặt") + f" {tp.ten.lower()}", tien_in))
        tong += tien_giay + tien_in
        if tp.uoc_tinh and don.loai_sp != "hop_cung":
            r["uoc_tinh"].append(tp.ten)
    ctp = kem * P["gia_kem"]
    if ctp:
        r["dong"].append((f"Kẽm CTP {kem} bản", ctp))
        tong += ctp
        r["co_dinh"] += ctp
        if don.proof and P.get("proof_toi_thieu"):
            r["dong"].append(("Proof", P["proof_toi_thieu"]))
            tong += P["proof_toi_thieu"]
            r["co_dinh"] += P["proof_toi_thieu"]
    for ten, gia in don.gc_tuy_chinh:
        r["dong"].append((ten, SL * gia))
        tong += SL * gia
    thay_the = {k for f in K["phi_lo"].values() for k in f["thay_cho"]} if kts else set()
    for key in don.gia_cong:
        g = P["gia_cong"].get(key)
        if not g or key in thay_the:
            continue
        nhan = g["ten"]
        khuon_gc = g.get("khuon", 0)
        if g["don_vi"] == "m2":
            he_so = 2 if (key in ("can_mo", "can_bong") and don.can_mang_2_mat) else 1
            tien = max(SL * dien_tich_sp * g["gia"] * he_so, g.get("san", 0))
            if he_so == 2:
                nhan = g["ten"] + " 2 mặt"
        elif g["don_vi"] == "lo":
            tien = g["gia"]
        elif g["don_vi"] == "nhip":
            rate = next((rt for nguong, rt in g["bac_nhip"] if tong_nhip < nguong), g["gia_toi_thieu"])
            tien = max(tong_nhip * rate, g.get("san", 0))
            nhan = f"{g['ten']} ({fmt(tong_nhip)} nhịp × {rate}đ)"
        elif g["don_vi"] == "mep":
            tien = max(SL * g["gia"] * don.so_mep_dan, g.get("san", 0))
            nhan = f"{g['ten']} ({don.so_mep_dan} mép × {g['gia']}đ)"
        elif g["don_vi"] == "cm2":
            kt_spec = don.ep_kim_kt if key == "ep_kim" else don.dap_noi_kt
            kt = kt_spec or (10, 5)
            if not kt_spec:
                r["mac_dinh"].append(f"vùng {g['ten'].lower()} 10×5 cm")
            am_duong = key == "dap_noi" and don.dap_noi_am_duong
            dg = g["gia_am_duong"] if am_duong else g["gia"]
            if am_duong:
                khuon_gc *= 2
                nhan = "Dập nổi âm dương"
            tien = max(SL * kt[0] * kt[1] * dg, g.get("san", 0))
            nhan += f" ({kt[0]}×{kt[1]} cm × {dg}đ)"
        elif key == "dan_tui":
            tien = max(SL * (g["gia_2_manh"] if don.tui_2_manh else g["gia"]), g["san_2_manh"] if don.tui_2_manh else g["san"])
            nhan = g["ten"] + (" (2 mảnh)" if don.tui_2_manh else " (1 mảnh)")
        elif key == "quai_tui":
            tien = SL * (don.gia_quai or g["gia"])
            if not don.gia_quai:
                r["mac_dinh"].append("quai dây phổ thông 350đ/cặp")
        else:
            tien = max(SL * g["gia"], g.get("san", 0))
        r["dong"].append((nhan, tien))
        tong += tien
        if khuon_gc:
            r["dong"].append(("Khuôn " + nhan.split(" (")[0].lower(), khuon_gc))
            tong += khuon_gc
            r["co_dinh"] += khuon_gc
        if g.get("uoc_tinh") and don.loai_sp != "hop_cung":
            r["uoc_tinh"].append(g["ten"])
    if kts:
        for ten, f in K["phi_lo"].items():
            if any(k in don.gia_cong for k in f["thay_cho"]):
                r["dong"].append((ten, f["gia"]))
                tong += f["gia"]
                r["co_dinh"] += f["gia"]
        r["uoc_tinh"].append("phí lô in nhanh")
    if don.khuon_be and getattr(don, "khuon_co_san", False):
        r["dong"].append(("Khuôn bế: có sẵn", 0))
    elif don.khuon_be:
        if don.khuon_be_tien is not None:
            kb = don.khuon_be_tien
        elif kts and don.loai_sp in K.get("khuon_cho_loai", []):
            kb = K["khuon"]
        else:
            KB = P.get("khuon_be_theo_kich_thuoc")
            if KB:
                dt_bai = max((u_ * w_ * h_ for (_, _, u_, w_, h_) in r.get("bai_binh", [])), default=KB["full_kho_cm2"])
                mot_khuon = KB["toi_da"] if don.loai_sp in KB["loai_cao_nhat"] else                     min(KB["toi_da"], max(KB["toi_thieu"], KB["toi_thieu"] + (KB["toi_da"] - KB["toi_thieu"]) * dt_bai / KB["full_kho_cm2"]))
                kb = don.khuon_be * round(mot_khuon / 10000) * 10000
            else:
                kb = don.khuon_be * P["khuon_be"]
        r["dong"].append((f"Khuôn bế ×{don.khuon_be}", kb))
        tong += kb
        r["co_dinh"] += kb
    r["vat_tu"] = tong
    r["van_chuyen"] = tong * P["pct_van_chuyen"]
    r["chi_phi"] = tong + r["van_chuyen"]
    r["gia_von"] = r["chi_phi"] / SL
    if don.pct_ln is not None:
        ln = don.pct_ln
    else:
        ln = next((pc for nguong, pc in P.get("bac_loi_nhuan", {}).get("bac", []) if SL < nguong), P["pct_loi_nhuan"])
    r["pct_ln"] = ln
    r["gia_ban"] = r["chi_phi"] * (1 + ln) / SL
    lt = 10 if r["gia_ban"] < 1000 else 100 if r["gia_ban"] < 10000 else P["lam_tron"]
    r["gia_ban_tron"] = math.ceil(r["gia_ban"] / lt) * lt
    if don.loai_sp == "tem_decal" and don.thanh_phan:
        tp = don.thanh_phan[0]
        ny = gia_niem_yet_decal(tp.trai_w - 0.4, tp.trai_h - 0.4, SL)
        if ny:
            r["niem_yet"] = ny
            r["gia_ban_tron"] = math.ceil(ny / 10) * 10
            r["gia_ban"] = ny
    return r


# ---------- Dựng đơn hàng từ thông số đã bóc tách ----------
MAC_DINH_GSM = {"hop_gap": 300, "thiep": 300, "tui_giay": 250, "hop_cung": 150, "tem_decal": 1}


def dung_don(spec: dict) -> DonHang:
    don = _dung_don(spec)
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
    don.khuon_co_san = bool(spec.get("khuon_co_san"))
    don.kieu_2_mat = spec.get("kieu_in_2_mat")
    don.ep_kim_kt = tuple(spec["ep_kim_kt"]) if spec.get("ep_kim_kt") else None
    don.dap_noi_kt = tuple(spec["dap_noi_kt"]) if spec.get("dap_noi_kt") else None
    don.dap_noi_am_duong = bool(spec.get("dap_noi_am_duong"))
    kieu = (spec.get("kieu_hop") or "").lower()
    don.so_mep_dan = spec.get("so_mep_dan") or (3 if any(k in kieu for k in ("đáy khóa", "đáy cài", "khóa đáy")) else 1)
    don.tui_2_manh = bool(spec.get("tui_2_manh"))
    don.gia_quai = spec.get("gia_quai")
    don.can_mang_2_mat = bool(spec.get("can_mang_2_mat"))
    don.loai_sp = spec.get("loai") or "hop_gap"
    don.gc_tuy_chinh = [(g["ten"], g["gia_moi_cai"]) for g in (spec.get("gia_cong_tuy_chinh") or [])]
    if don.loai_sp != "tem_decal":
        if not spec.get("giay"):
            don.mac_dinh.append(f"giấy {don.thanh_phan[0].loai}")
        if not spec.get("dinh_luong"):
            don.mac_dinh.append(f"định lượng {don.thanh_phan[0].gsm}g")
    if spec.get("so_mau") is None:
        don.mac_dinh.append(f"in {don.thanh_phan[0].so_mau} màu")
    if not spec.get("so_mat") and don.thanh_phan[0].so_mau:
        don.mac_dinh.append(f"{don.thanh_phan[0].so_mat} mặt")
    if not spec.get("gia_cong") and not don.gc_tuy_chinh:
        don.mac_dinh.append("gia công cơ bản (bế, dán)")
    if not don.kho and don.loai_sp in ("hop_gap", "hop_cung", "tui_giay"):
        don.uoc_tinh.append("khổ trải tính từ kích thước (chưa có file khuôn)")
    if don.loai_sp in ("hop_gap", "tui_giay") and don.thanh_phan and don.thanh_phan[0].gsm >= 300 \
            and not any(g in don.gia_cong for g in ("can_mo", "can_bong")):
        don.mac_dinh.append("không cán màng → " + P["canh_bao"]["giay_day_khong_can_mang"])
    if don.gc_tuy_chinh:
        # gia công đã có đơn giá riêng thì bỏ bản mặc định cùng tên
        ten_tc = " ".join(t.lower() for t, _ in don.gc_tuy_chinh)
        don.gia_cong = [g for g in don.gia_cong if P["gia_cong"][g]["ten"].split()[0].lower() not in ten_tc]
    return don


def _dung_don(spec: dict) -> DonHang:
    loai = spec.get("loai") or "hop_gap"
    D, R, C = spec.get("dai") or 0, spec.get("rong") or 0, spec.get("cao") or 0
    giay = spec.get("giay") or ("Couche" if loai in ("hop_cung", "tui_giay") else "Ivory")
    gsm = spec.get("dinh_luong") or MAC_DINH_GSM.get(loai, 300)
    mau = 4 if spec.get("so_mau") is None else spec["so_mau"]
    mat = spec.get("so_mat") or 1
    gc = [g for g in (spec.get("gia_cong") or []) if g in P["gia_cong"]]
    ten = spec.get("san_pham") or ""
    kieu = (spec.get("kieu_hop") or "").lower()

    if loai == "hop_cung":
        ao_w, ao_h = D + 2 * C + 4, R + 2 * C + 4
        tp = [ThanhPhan("Áo giấy nắp + đáy", giay, gsm, ao_w, ao_h, 2, mau, 1),
              ThanhPhan("Lót ruột trơn", giay, gsm, ao_w, ao_h, 2, 0, 0),
              ThanhPhan("Chipboard nắp + đáy", "Chipboard", 1200, D + 2 * C, R + 2 * C, 2, 0, 0, uoc_tinh=True)]
        gc = [g for g in gc if not g.startswith("dan") and g != "be"] + ["be_hop_cung", "phay_ranh", "dung_hop", "boi_hop_cung"]
        nap_keo = any(k in kieu for k in ("kéo", "rút", "bao diêm", "diêm", "hộc"))
        if nap_keo:
            gc.append("boi_nap_keo")
        ten_hc = ten or ("Hộp cứng nắp kéo (bao diêm)" if nap_keo else "Hộp cứng âm dương / nắp rời")
        # 4 khuôn bế: áo nắp, áo đáy, carton nắp, carton đáy (theo My)
        return DonHang(ten_hc, tp, gc, khuon_be=4, uoc_tinh=["chipboard, phay rãnh, dựng hộp chờ My chốt"])
    if loai == "thiep":
        w, h = (D or 8), (R or 12)
        tp = [ThanhPhan("Thiệp" if mau else "Tấm giấy", giay, gsm, w + 0.6, h + 0.6, 1, mau, (mat if spec.get("so_mat") else 2) if mau else 1)]
        if "be" not in gc:
            gc.append("cat_tp")
        return DonHang(ten or ("Tấm giấy bế" if "be" in gc else "Thiệp"), tp, gc, khuon_be=1 if "be" in gc else 0)
    if loai == "tem_decal":
        tp = [ThanhPhan("Tem decal", "Decal", 1, (D or 5) + 0.4, (R or 5) + 0.4, 1, mau, 1)]
        gc = [g for g in gc if g != "be"]
        if "be_demi" not in gc:
            gc.append("be_demi")
        return DonHang(ten or "Tem decal", tp, gc, khuon_be=1)
    if loai == "tui_giay":
        tp = [ThanhPhan("Túi giấy", giay, gsm, 2 * (D + R) + 3, C + R + 5, 1, mau, 1)]
        gc = [g for g in gc if not g.startswith("dan")] + ["be", "dan_tui", "quai_tui"]
        return DonHang(ten or "Túi giấy", tp, gc, khuon_be=1)

    # Hộp giấy gập
    hai_mieng = any(k in kieu for k in ("âm dương", "nắp rời", "bao diêm", "kéo", "rút"))
    if hai_mieng:
        day_in = 0 if any(k in kieu for k in ("bao diêm", "kéo", "rút")) else mau
        tp = [ThanhPhan("Nắp", giay, gsm, D + 2 * C + 3, R + 2 * C + 3, 1, mau, 1),
              ThanhPhan("Đáy", giay, gsm, D + 2 * C + 3, R + 2 * C + 3, 1, day_in, 1)]
        kb = 2
        if not any(g.startswith("dan") for g in gc):
            gc.append("dan_tay")
    else:
        tp = [ThanhPhan("Hộp", giay, gsm, 2 * (D + R) + 2, C + 2 * R + 3, 1, mau, mat)]
        kb = 1
        if not any(g.startswith("dan") for g in gc):
            gc.append("dan_may")
    if "be" not in gc:
        gc.append("be")
    return DonHang(ten or "Hộp giấy", tp, gc, khuon_be=kb)


def gia_niem_yet_decal(dai, rong, SL):
    """Giá bán đ/tem theo bảng My (decal giấy, cán bóng, cắt TP, offset). None nếu ngoài điều kiện."""
    B = P.get("bang_gia_decal_offset")
    if not B or not dai or not rong or SL < B["dieu_kien"]["so_luong_toi_thieu"]:
        return None
    cot = max(i for i, q in enumerate(B["so_luong"]) if SL >= q)
    diem = sorted(((float(k.split("x")[0]) * float(k.split("x")[1]), v[cot]) for k, v in B["kich_thuoc"].items()))
    a = dai * rong
    if a <= diem[0][0]:
        return diem[0][1]
    if a >= diem[-1][0]:
        return diem[-1][1]
    for (a1, g1), (a2, g2) in zip(diem, diem[1:]):
        if a1 <= a <= a2:
            return g1 + (g2 - g1) * (a - a1) / (a2 - a1)
    return None


def fmt(n):
    return f"{n:,.0f}".replace(",", ".")


def fmt_vn(n):
    return f"{n:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_k(n):
    """Tiền gọn: 1,6tr · 432k · 950đ."""
    if n >= 1_000_000:
        v = n / 1_000_000
        return (f"{v:.1f}".rstrip("0").rstrip(".") + "tr").replace(".", ",")
    if n >= 1000:
        return f"{round(n / 1000)}k"
    return f"{n:,.0f}đ".replace(",", ".")


def soan_tin(spec: dict, don: DonHang, ket_qua: list) -> str:
    """Một tin Zalo gọn: quy cách · giá 3 mức · bóc tách 1 dòng · so sánh · ước tính/mặc định · chính sách."""
    def so(x):
        return str(int(x)) if float(x).is_integer() else str(x)
    kt = "×".join(so(x) for x in (spec.get("dai"), spec.get("rong"), spec.get("cao")) if x)
    tp0 = don.thanh_phan[0] if don.thanh_phan else None
    def ten_giay(tp):
        return "Decal giấy" if tp.loai == "Decal" else f"{tp.loai} {tp.gsm}g"
    quy_cach = (f"{ten_giay(tp0)}, " + (f"in {tp0.so_mau} màu {tp0.so_mat} mặt" if tp0.so_mau else "không in")) if tp0 else ""
    gc = [P["gia_cong"][g]["ten"] for g in don.gia_cong if g in P["gia_cong"]] + [f"{t} {fmt(g)}đ" for t, g in don.gc_tuy_chinh]
    ten_chuan = don.ten.replace("×", "x").replace("*", "x")
    ten = don.ten if (kt and kt.replace("×", "x") in ten_chuan) else f"{don.ten} {kt} cm"
    trai = ""
    r0_bai = (ket_qua[0].get("bai_binh") or [None])[0]
    if don.loai_sp in ("hop_gap", "hop_cung", "tui_giay") and r0_bai:
        trai = f" · khổ trải {so(round(r0_bai[3], 1))}×{so(round(r0_bai[4], 1))}"
    L = [f"📦 {ten} · {quy_cach}" + (" · " + ", ".join(gc) if gc else "") + trai]
    for r in ket_qua:
        duoi = "(theo bảng giá My)" if r.get("niem_yet") else f"(vốn {fmt(r['gia_von'])}, lãi {int(round(r['pct_ln'] * 100))}%)"
        L.append(f"🔹 {fmt(r['SL'])} cái: giá bán {fmt(r['gia_ban_tron'])} đ/cái · tổng {fmt(r['gia_ban_tron'] * r['SL'])} đ ({'KTS' if r['kts'] else 'offset'}, {duoi.strip('()')})")
    r0 = ket_qua[0]
    if any(r.get("niem_yet") for r in ket_qua):
        L.append("📋 Giá bán theo bảng decal offset của My (cán bóng, cắt TP, nội suy theo kích thước); vốn bên dưới chỉ để tham khảo.")
    boc = " · ".join(f"{t.split(' (')[0].replace('Công in', 'in').replace(' thành phẩm', '')} {fmt_k(v)}" for t, v in r0["dong"] if v)
    L.append(f"🧾 @{fmt(r0['SL'])}: {boc}. Cố định {fmt_k(r0['co_dinh'])} = {fmt_k(r0['co_dinh'] / r0['SL'])}/cái.")
    khac = tinh(don, r0["SL"], kts=not r0["kts"])
    if r0.get("niem_yet") or not any(tp.so_mau for tp in don.thanh_phan):
        kha_thi = None
    else:
        kha_thi = r0["kts"] or all(max(ups(*k["kho"], tp.trai_w, tp.trai_h) for k in P["don_kts"]["kho_in_nhanh"]) for tp in don.thanh_phan if tp.so_mau)
    if kha_thi is None:
        pass
    elif kha_thi:
        L.append(f"🔁 Nếu {'offset' if r0['kts'] else 'in nhanh'} @{fmt(r0['SL'])}: vốn {fmt(khac['gia_von'])}, bán {fmt(khac['gia_ban_tron'])}. (Ghi 'in offset'/'in KTS' để chọn.)")
    else:
        L.append("🔁 Khổ trải vượt 33×60 nên buộc in offset.")
    uoc = [u.replace(" (ước tính)", "") for u in dict.fromkeys(r0["uoc_tinh"])]
    md = r0["mac_dinh"]
    can_them = []
    if any("khổ trải" in u for u in uoc):
        can_them.append("file khuôn để chốt khổ trải (bot đang tự tính, xem dòng đầu)")
    if any(m.startswith("giấy") or m.startswith("định lượng") for m in md):
        can_them.append("loại giấy, định lượng")
    if any("gia công" in m for m in md):
        can_them.append("gia công cần làm (cán màng, ép kim…)")
    if any("vùng" in m for m in md):
        can_them.append("kích thước vùng ép kim/dập nổi")
    if any("quai" in m for m in md):
        can_them.append("loại dây quai")
    if any("My chốt" in u for u in uoc):
        can_them.append("đơn giá hộp cứng (chờ My)")
    khac = [u for u in uoc if "khổ trải" not in u and "My chốt" not in u]
    canh_bao = [m for m in md if "→" in m]
    dong = []
    if can_them:
        dong.append("📝 Gửi thêm để chuẩn hơn: " + "; ".join(can_them) + ".")
    elif not uoc:
        dong.append("✅ Đủ thông số.")
    if khac:
        dong.append("Tạm tính: " + "; ".join(khac) + ".")
    if canh_bao:
        dong.append("⚠️ " + " ".join(m.split("→ ", 1)[1] for m in canh_bao))
    L.append(" ".join(dong))
    L.append("📎 Chưa VAT 8%, chưa vận chuyển, không tặng khuôn. SX 7–10 ngày sau duyệt file, mẫu 3–7 ngày.")
    msg = "\n".join(L)
    return msg if len(msg) <= 1990 else msg[:1985] + "…"


if __name__ == "__main__":
    # Đối chiếu sheet Đơn SLL: 1.000 hộp Ivory 300 giá 18tr/tấn, 1 con/tờ 65×43, 4 màu, sửa bài 300
    # Kỳ vọng: giấy 2.007.369 · công in 1.200.000 · CTP 440.000
    P["giay_tr_tan"]["Ivory"] = 18
    P["tu_sua_bai"] = 300
    P["tu_sua_bai_theo_kho"] = {"65x43": 300}
    P["kho_giay"] = [[65, 43]]
    P["binh_bai"] = {"le_nhip_cm": 0, "bu_xen_cm": {}}
    r = tinh(DonHang("Đối chiếu", [ThanhPhan("Hộp giấy", "Ivory", 300, 40, 60, 1, 4, 1)], [], khuon_be=0), 1000)
    for d in r["dong"]:
        print(f"{d[0]:60} {d[1]:>14,.1f}")
    ok = abs(r["dong"][0][1] - 2007369) < 1 and r["dong"][1][1] == 1200000 and r["dong"][2][1] == 440000
    print("KHỚP EXCEL" if ok else "LỆCH EXCEL")
