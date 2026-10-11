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


def chon_kho(w, h):
    """Chọn khổ giấy công nghiệp cho tỉ lệ dùng giấy cao nhất. Trả về ((W,H), số con) hoặc None."""
    best = None
    for W, H in P["kho_giay"]:
        u = ups(W, H, w, h)
        if u == 0:
            continue
        eff = u * w * h / (W * H)
        if best is None or eff > best[2] + 1e-9:
            best = ((W, H), u, eff)
    return best


def gia_to(W, H, loai, gsm):
    """Giá 1 tờ giấy = Dài × Rộng × gsm × giá/gam ÷ 10.000 (ô B28)."""
    if loai == "Chipboard":
        return P["chipboard_gia_to_65x86"] * (W * H) / (65 * 86)
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
        return so_tay * so_mau * P["cong_in_toi_thieu_1_kem"]
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


def tinh(don: DonHang, SL: int):
    r = {"SL": SL, "dong": [], "co_dinh": 0.0, "uoc_tinh": list(don.uoc_tinh)}
    tong = 0.0
    dien_tich_sp = 0.0
    kem = 0
    for tp in don.thanh_phan:
        k = chon_kho(tp.trai_w, tp.trai_h)
        if not k:
            r["dong"].append((f"{tp.ten}: khổ trải {tp.trai_w}×{tp.trai_h} vượt khổ giấy", 0))
            continue
        (W, H), u, _ = k
        so_to = SL * tp.con_moi_sp / u * P["hao_hut"] + (P["tu_sua_bai"] if tp.so_mau else 10)
        tien_giay = so_to * gia_to(W, H, tp.loai, tp.gsm)
        tien_in = cong_in(so_to, tp.so_mau, tp.so_mat)
        kem += tp.so_mau * tp.so_mat
        if tp.so_mau and so_to * tp.so_mat < 3000:
            r["co_dinh"] += tien_in
        dien_tich_sp += tp.trai_w * tp.trai_h * tp.con_moi_sp / 10000
        r["dong"].append((f"{tp.ten} {tp.loai} {tp.gsm}g ({u} con/tờ {W}×{H}, {so_to:,.0f} tờ)", tien_giay))
        if tien_in:
            r["dong"].append((f"Công in {tp.so_mau} màu {tp.so_mat} mặt {tp.ten.lower()}", tien_in))
        tong += tien_giay + tien_in
        if tp.uoc_tinh:
            r["uoc_tinh"].append(tp.ten)
    ctp = kem * P["gia_kem"]
    if ctp:
        r["dong"].append((f"Kẽm CTP {kem} bản", ctp))
        tong += ctp
        r["co_dinh"] += ctp
    for key in don.gia_cong:
        g = P["gia_cong"].get(key)
        if not g:
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
    if don.khuon_be:
        kb = don.khuon_be * P["khuon_be"]
        r["dong"].append((f"Khuôn bế ×{don.khuon_be}", kb))
        tong += kb
        r["co_dinh"] += kb
    r["vat_tu"] = tong
    r["van_chuyen"] = tong * P["pct_van_chuyen"]
    r["chi_phi"] = tong + r["van_chuyen"]
    r["gia_von"] = r["chi_phi"] / SL
    r["gia_ban"] = r["chi_phi"] * (1 + P["pct_loi_nhuan"]) / SL
    lt = P["lam_tron"]
    r["gia_ban_tron"] = math.ceil(r["gia_ban"] / lt) * lt
    return r


# ---------- Dựng đơn hàng từ thông số đã bóc tách ----------
MAC_DINH_GSM = {"hop_gap": 300, "thiep": 300, "tui_giay": 250, "hop_cung": 150, "tem_decal": 1}


def dung_don(spec: dict) -> DonHang:
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
        gc = [g for g in gc if not g.startswith("dan")] + ["be", "boi_hop_cung"]
        return DonHang(ten or "Hộp cứng bồi chipboard", tp, gc, khuon_be=2,
                       uoc_tinh=["đơn giá hộp cứng chờ My chốt"])
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


def soan_tin(spec: dict, don: DonHang, ket_qua: list) -> str:
    kt = " × ".join(str(x) for x in (spec.get("dai"), spec.get("rong"), spec.get("cao")) if x)
    L = [f"📦 {don.ten}" + (f" {kt} cm" if kt else "")]
    L.append("• " + "; ".join(f"{tp.ten}: {tp.loai} {tp.gsm}g" for tp in don.thanh_phan))
    gc_ten = [P["gia_cong"][g]["ten"] for g in don.gia_cong if g in P["gia_cong"]]
    if gc_ten:
        L.append("• Gia công: " + ", ".join(gc_ten))
    L.append("")
    L.append(f"💰 BÁO GIÁ (chưa VAT {int(P['vat'] * 100)}%, đã gồm lợi nhuận {int(P['pct_loi_nhuan'] * 100)}%)")
    for r in ket_qua:
        L.append(f"🔹 {fmt(r['SL'])} cái: {fmt(r['gia_ban_tron'])} đ/cái · tổng {fmt(r['gia_ban_tron'] * r['SL'])} đ "
                 f"(giá vốn {fmt(r['gia_von'])} đ/cái)")
    r0 = ket_qua[0]
    L.append("")
    L.append(f"📌 Chi phí cố định (kẽm, công in tối thiểu, khuôn): {fmt(r0['co_dinh'])} đ "
             f"= {fmt(r0['co_dinh'] / r0['SL'])} đ/cái ở mức {fmt(r0['SL'])} cái.")
    L.append("🧾 Bóc tách @" + fmt(r0["SL"]) + ": " + "; ".join(f"{t} {fmt(v)}" for t, v in r0["dong"] if v) + ".")
    uoc = list(dict.fromkeys(r0["uoc_tinh"]))
    if uoc:
        L.append("⚠️ Ước tính: " + ", ".join(uoc) + ".")
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
