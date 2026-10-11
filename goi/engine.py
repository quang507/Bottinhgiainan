"""Engine tính giá GÓI - cùng công thức sheet 'Đơn SLL' / 'Đơn số ít' trong Báo giá My.xlsx.
Thuần số học, không có AI; kiểm chứng bằng `python -m goi.engine`."""
import json
import math
import os
from dataclasses import dataclass, field

P = json.load(open(os.path.join(os.path.dirname(__file__), "prices.json"), encoding="utf-8"))


def ups(W, H, w, h):
    if not w or not h:
        return 0
    return max(math.floor(W / w) * math.floor(H / h), math.floor(W / h) * math.floor(H / w))


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


def nen_in_nhanh(don: DonHang, SL: int) -> bool:
    """Quy tắc My: dưới 500 tờ và mọi thành phần in lọt khổ 33×60 thì in nhanh."""
    K = P["don_kts"]
    tong_to = 0
    for tp in don.thanh_phan:
        if not tp.so_mau:
            continue
        u = ups(*K["kho_in_nhanh"], tp.trai_w, tp.trai_h)
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
    for tp in don.thanh_phan:
        k = ((don.kho, don.con, 0) if don.kho and don.con else chon_kho(tp.trai_w, tp.trai_h, [K["kho_in_nhanh"]] if (kts and tp.so_mau) else None))
        if not k:
            r["dong"].append((f"{tp.ten}: khổ trải {tp.trai_w}×{tp.trai_h} vượt khổ giấy", 0))
            continue
        (W, H), u, _ = k
        sua = don.tu_sua_bai if don.tu_sua_bai is not None else (K["tu_sua_bai"] if kts else P["tu_sua_bai"])
        so_to = SL * tp.con_moi_sp / u * P["hao_hut"] + (sua if tp.so_mau else 10)
        gt = (W * H * tp.gsm * don.gia_giay / 10000) if (don.gia_giay and tp.loai not in ("Chipboard", "Decal")) else gia_to(W, H, tp.loai, tp.gsm)
        tien_giay = so_to * gt
        if kts:
            tien_in = so_to * tp.so_mat * K["in_kts_to_33x60"] if tp.so_mau else 0
        else:
            tien_in = cong_in(so_to, tp.so_mau, tp.so_mat)
            kem += tp.so_mau * tp.so_mat
            if tp.so_mau and so_to * tp.so_mat < 3000:
                r["co_dinh"] += tien_in
        dien_tich_sp += tp.trai_w * tp.trai_h * tp.con_moi_sp / 10000
        r["dong"].append((f"{tp.ten} {tp.loai} {tp.gsm}g ({u} con/tờ {W}×{H}, {fmt(so_to)} tờ)", tien_giay))
        if tien_in:
            r["dong"].append(((f"In KTS {fmt(so_to * tp.so_mat)} lượt" if kts else f"Công in {tp.so_mau} màu {tp.so_mat} mặt") + f" {tp.ten.lower()}", tien_in))
        tong += tien_giay + tien_in
        if tp.uoc_tinh:
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
        if g["don_vi"] == "m2":
            tien = max(SL * dien_tich_sp * g["gia"], g.get("san", 0))
        elif g["don_vi"] == "lo":
            tien = g["gia"]
        else:
            tien = max(SL * g["gia"], g.get("san", 0))
        r["dong"].append((g["ten"], tien))
        tong += tien
        if g.get("khuon"):
            r["dong"].append((f"Khuôn {g['ten'].lower()}", g["khuon"]))
            tong += g["khuon"]
            r["co_dinh"] += g["khuon"]
        if g.get("uoc_tinh"):
            r["uoc_tinh"].append(g["ten"])
    if kts:
        for ten, f in K["phi_lo"].items():
            if any(k in don.gia_cong for k in f["thay_cho"]):
                r["dong"].append((ten, f["gia"]))
                tong += f["gia"]
                r["co_dinh"] += f["gia"]
        r["uoc_tinh"].append("đơn số ít tính theo phí trọn gói lô in KTS")
    if don.khuon_be:
        kb = don.khuon_be_tien if don.khuon_be_tien is not None else (K["khuon"] if kts else don.khuon_be * P["khuon_be"])
        r["dong"].append((f"Khuôn bế ×{don.khuon_be}", kb))
        tong += kb
        r["co_dinh"] += kb
    r["vat_tu"] = tong
    r["van_chuyen"] = tong * P["pct_van_chuyen"]
    r["chi_phi"] = tong + r["van_chuyen"]
    r["gia_von"] = r["chi_phi"] / SL
    ln = don.pct_ln if don.pct_ln is not None else (K["pct_loi_nhuan"] if kts else P["pct_loi_nhuan"])
    r["pct_ln"] = ln
    r["gia_ban"] = r["chi_phi"] * (1 + ln) / SL
    lt = P["lam_tron"]
    r["gia_ban_tron"] = math.ceil(r["gia_ban"] / lt) * lt
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
    don.gc_tuy_chinh = [(g["ten"], g["gia_moi_cai"]) for g in (spec.get("gia_cong_tuy_chinh") or [])]
    if not spec.get("giay"):
        don.mac_dinh.append(f"giấy {don.thanh_phan[0].loai}")
    if not spec.get("dinh_luong"):
        don.mac_dinh.append(f"định lượng {don.thanh_phan[0].gsm}g")
    if spec.get("so_mau") is None:
        don.mac_dinh.append(f"in {don.thanh_phan[0].so_mau} màu")
    if not spec.get("so_mat"):
        don.mac_dinh.append(f"{don.thanh_phan[0].so_mat} mặt")
    if not spec.get("gia_cong") and not don.gc_tuy_chinh:
        don.mac_dinh.append("gia công cơ bản (bế, dán)")
    if not don.kho:
        don.uoc_tinh.append("khổ trải tính từ kích thước, có file khuôn sẽ chính xác hơn")
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
        return DonHang(ten_hc, tp, gc, khuon_be=4, uoc_tinh=["chipboard đ/tờ, phay rãnh, dựng hộp, bồi tay chờ My chốt"])
    if loai == "thiep":
        w, h = (D or 8), (R or 12)
        tp = [ThanhPhan("Thiệp", giay, gsm, w + 0.6, h + 0.6, 1, mau, mat if spec.get("so_mat") else 2)]
        if "be" not in gc:
            gc.append("cat_tp")
        return DonHang(ten or "Thiệp", tp, gc, khuon_be=0)
    if loai == "tem_decal":
        tp = [ThanhPhan("Tem decal", "Decal", 1, (D or 5) + 0.4, (R or 5) + 0.4, 1, mau, 1)]
        if "be" not in gc:
            gc.append("be")
        return DonHang(ten or "Tem decal", tp, gc, khuon_be=1)
    if loai == "tui_giay":
        tp = [ThanhPhan("Túi giấy", giay, gsm, 2 * (D + R) + 3, C + R + 5, 1, mau, 1)]
        gc = [g for g in gc if not g.startswith("dan")] + ["be", "dan_tui"]
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


def fmt(n):
    return f"{n:,.0f}".replace(",", ".")


def fmt_vn(n):
    return f"{n:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def soan_tin(spec: dict, don: DonHang, ket_qua: list) -> str:
    kt = " × ".join(str(x) for x in (spec.get("dai"), spec.get("rong"), spec.get("cao")) if x)
    L = [f"📦 {don.ten}" + (f" {kt} cm" if kt else "")]
    L.append("• " + "; ".join(f"{tp.ten}: {tp.loai} {tp.gsm}g" for tp in don.thanh_phan))
    gc_ten = [P["gia_cong"][g]["ten"] for g in don.gia_cong if g in P["gia_cong"]] + [f"{t} {fmt(g)}đ" for t, g in don.gc_tuy_chinh]
    if gc_ten:
        L.append("• Gia công: " + ", ".join(gc_ten))
    L.append("")
    che_do = "in KTS, phí trọn gói lô" if ket_qua[0]["kts"] else "in offset"
    L.append(f"💰 BÁO GIÁ ({che_do}; chưa VAT {int(P['vat'] * 100)}%, đã gồm lợi nhuận {int(ket_qua[0]['pct_ln'] * 100)}%)")
    for r in ket_qua:
        L.append(f"🔹 {fmt(r['SL'])} cái: {fmt(r['gia_ban_tron'])} đ/cái · tổng {fmt(r['gia_ban_tron'] * r['SL'])} đ "
                 f"(chi phí {fmt(r['chi_phi'])} đ = {fmt_vn(r['gia_von'])} đ/cái)")
    r0 = ket_qua[0]
    L.append("")
    L.append(f"📌 Chi phí cố định (kẽm, công in tối thiểu, khuôn): {fmt(r0['co_dinh'])} đ "
             f"= {fmt(r0['co_dinh'] / r0['SL'])} đ/cái ở mức {fmt(r0['SL'])} cái.")
    L.append("🧾 Bóc tách @" + fmt(r0["SL"]) + ": " + "; ".join(f"{t} {fmt(v)}" for t, v in r0["dong"] if v) + ".")
    khac = tinh(don, r0["SL"], kts=not r0["kts"])
    kha_thi = r0["kts"] or all(ups(*P["don_kts"]["kho_in_nhanh"], tp.trai_w, tp.trai_h) for tp in don.thanh_phan if tp.so_mau)
    if not kha_thi:
        L.append("🔁 Khổ trải vượt 33×60 cm nên bắt buộc in offset.")
    else:
        L.append(f"🔁 Nếu {'in offset' if r0['kts'] else 'in KTS'} ở mức {fmt(r0['SL'])} cái: chi phí {fmt(khac['gia_von'])} đ/cái, bán {fmt(khac['gia_ban_tron'])} đ/cái. Ghi 'in offset' hoặc 'in KTS' trong tin để chọn.")
    if r0["mac_dinh"]:
        L.append("ℹ️ Mặc định đã dùng (khách chưa nói): " + ", ".join(r0["mac_dinh"]) + ".")
    uoc = list(dict.fromkeys(r0["uoc_tinh"]))
    if uoc:
        L.append("⚠️ Ước tính: " + ", ".join(uoc) + ".")
    else:
        L.append("✅ Đủ thông số, không có khoản ước tính.")
    msg = "\n".join(L)
    return msg if len(msg) <= 1990 else msg[:1985] + "…"


if __name__ == "__main__":
    # Đối chiếu sheet Đơn SLL: 1.000 hộp Ivory 300 giá 18tr/tấn, 1 con/tờ 65×43, 4 màu, sửa bài 300
    # Kỳ vọng: giấy 2.007.369 · công in 1.200.000 · CTP 440.000
    P["giay_tr_tan"]["Ivory"] = 18
    P["tu_sua_bai"] = 300
    P["kho_giay"] = [[65, 43]]
    r = tinh(DonHang("Đối chiếu", [ThanhPhan("Hộp giấy", "Ivory", 300, 40, 60, 1, 4, 1)], [], khuon_be=0), 1000)
    for d in r["dong"]:
        print(f"{d[0]:60} {d[1]:>14,.1f}")
    ok = abs(r["dong"][0][1] - 2007369) < 1 and r["dong"][1][1] == 1200000 and r["dong"][2][1] == 440000
    print("KHỚP EXCEL" if ok else "LỆCH EXCEL")
