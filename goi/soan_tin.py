"""Soạn tin Zalo từ kết quả tính giá: bản nội bộ (có giá vốn, bóc tách) và bản gửi khách."""
from .bang_gia import P
from .binh_bai import ups
from .san_pham import DonHang
from .tinh_gia import tinh, giay_in_nhanh_duoc


# ---------------------------------------------------------------- định dạng số
def fmt(n):
    """1234567 → 1.234.567"""
    return f"{n:,.0f}".replace(",", ".")


def fmt_k(n):
    """Tiền gọn: 1,6tr · 432k · 950đ."""
    if n >= 1_000_000:
        return (f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "tr").replace(".", ",")
    if n >= 1000:
        return f"{round(n / 1000)}k"
    return f"{n:,.0f}đ".replace(",", ".")


def _so(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def _kich_thuoc(spec: dict, dau: str) -> str:
    return dau.join(_so(x) for x in (spec.get("dai"), spec.get("rong"), spec.get("cao")) if x)


# ---------------------------------------------------------------- thông báo
def thong_bao_vuot_kho(spec: dict, don: DonHang, r: dict) -> str:
    _, w, h = r["vuot_kho"][0]
    lon = max(P["kho_giay"], key=lambda k: k[0] * k[1])
    return (f"⚠️ {don.ten} {_kich_thuoc(spec, '×')} cm: khổ trải khoảng {w:g}×{h:g} cm, vượt khổ giấy lớn nhất {lon[0]}×{lon[1]} nên không làm được hộp giấy 1 mảnh.\n"
            "Cỡ này thường làm thùng carton sóng hoặc ghép nhiều mảnh, cần My tư vấn kết cấu.\n"
            "Anh/chị kiểm tra lại kích thước giúp em (có nhầm mm với cm không?).")


# ---------------------------------------------------------------- bản nội bộ
def _dong_dau(spec, don, r0) -> str:
    """📦 tên · kích thước · giấy, in · gia công · khổ trải."""
    kt = _kich_thuoc(spec, "×")
    tp0 = don.thanh_phan[0] if don.thanh_phan else None
    quy_cach = ""
    if tp0:
        giay = "Decal giấy" if tp0.loai == "Decal" else f"{tp0.loai} {tp0.gsm}g"
        quy_cach = f"{giay}, " + (f"in {tp0.so_mau} màu {tp0.so_mat} mặt" if tp0.so_mau else "không in")
    gia_cong = [P["gia_cong"][g]["ten"] for g in don.gia_cong if g in P["gia_cong"]] + [f"{t} {fmt(g)}đ" for t, g in don.gc_tuy_chinh]
    da_co_kt = kt and kt.replace("×", "x") in don.ten.replace("×", "x").replace("*", "x")
    ten = don.ten if da_co_kt else f"{don.ten} {kt} cm"
    trai = ""
    bai = (r0.get("bai_binh") or [None])[0]
    if don.co_kho_trai and bai and not don.kho:
        trai = f" · khổ trải {_so(round(bai[3], 1))}×{_so(round(bai[4], 1))}"
    if tp0 and "2 mảnh" in tp0.ten:
        trai += " mỗi mảnh (túi 2 mảnh)"
    return f"📦 {ten} · {quy_cach}" + (" · " + ", ".join(gia_cong) if gia_cong else "") + trai


def _dong_gia(r) -> str:
    if r.get("niem_yet"):
        chu_thich = "theo bảng giá My"
    else:
        chu_thich = ("in nhanh, " if r["kts"] else "offset, ") + f"vốn {fmt(r['gia_von'])}, lãi {int(round(r['pct_ln'] * 100))}%"
    return f"🔹 {fmt(r['SL'])} cái: giá bán {fmt(r['gia_ban_tron'])} đ/cái · tổng {fmt(r['gia_ban_tron'] * r['SL'])} đ ({chu_thich})"


def _dong_boc_tach(don, r0) -> str:
    cac_khoan = " · ".join(f"{t.split(' (')[0].replace('Công in', 'in').replace(' thành phẩm', '')} {fmt_k(v)}" for t, v in r0["dong"] if v)
    co_dinh = f" Cố định {fmt_k(r0['co_dinh'])} = {fmt_k(r0['co_dinh'] / r0['SL'])}/cái." if r0["co_dinh"] else ""
    co_san = " Khuôn có sẵn nên không tính tiền khuôn." if don.khuon_co_san and don.khuon_be else ""
    return f"🧾 @{fmt(r0['SL'])}: {cac_khoan}.{co_dinh}{co_san}"


def _dong_so_sanh(don, r0):
    """🔁 so sánh với cách in còn lại, hoặc nói vì sao không in nhanh được. None nếu không cần."""
    if r0.get("niem_yet") or not don.co_in or don.loai_sp == "hop_cung":
        return None
    giay_vuot = [f"{tp.loai} {tp.gsm}g" for tp in don.thanh_phan if tp.so_mau and not giay_in_nhanh_duoc(tp)]
    if giay_vuot and not r0["kts"]:
        return f"🔁 {giay_vuot[0]} vượt mức máy in nhanh nhận nên in offset."
    lot_kho_nhanh = all(max(ups(*k["kho"], tp.trai_w, tp.trai_h) for k in P["don_kts"]["kho_in_nhanh"]) for tp in don.thanh_phan if tp.so_mau)
    if r0["kts"] or lot_kho_nhanh:
        khac = tinh(don, r0["SL"], kts=not r0["kts"])
        return (f"🔁 Nếu {'offset' if r0['kts'] else 'in nhanh'} @{fmt(r0['SL'])}: vốn {fmt(khac['gia_von'])}, bán {fmt(khac['gia_ban_tron'])}. "
                "(Ghi 'in offset'/'in KTS' để chọn.)")
    return "🔁 Khổ trải vượt 33×60 nên buộc in offset."


# mặc định nào thì gợi ý khách gửi thêm gì
GOI_Y_GUI_THEM = [
    (lambda uoc, md: any("khổ trải" in u for u in uoc), "file khuôn để chốt khổ trải (bot đang tự tính, xem dòng đầu)"),
    (lambda uoc, md: any(m.startswith("giấy") or m.startswith("định lượng") for m in md), "loại giấy, định lượng"),
    (lambda uoc, md: any("gia công" in m for m in md), "gia công cần làm (cán màng, ép kim…)"),
    (lambda uoc, md: any("vùng" in m for m in md), "kích thước vùng ép kim/dập nổi"),
    (lambda uoc, md: any("quai" in m for m in md), "loại dây quai"),
    (lambda uoc, md: any("My chốt" in u for u in uoc), "đơn giá hộp cứng (chờ My)"),
]


def _dong_ghi_chu(r0) -> str:
    """📝 cần gửi thêm gì · khoản tạm tính · ⚠️ cảnh báo."""
    uoc = [u.replace(" (ước tính)", "") for u in dict.fromkeys(r0["uoc_tinh"])]
    md = r0["mac_dinh"]
    can_them = [goi_y for dieu_kien, goi_y in GOI_Y_GUI_THEM if dieu_kien(uoc, md)]
    tam_tinh = [u for u in uoc if "khổ trải" not in u and "My chốt" not in u and "kết cấu đặc biệt" not in u]
    dac_biet = [u for u in uoc if "kết cấu đặc biệt" in u]
    canh_bao = [m for m in md if "→" in m]
    cau = []
    if can_them:
        cau.append("📝 Gửi thêm để chuẩn hơn: " + "; ".join(can_them) + ".")
    elif not uoc:
        cau.append("✅ Đủ thông số.")
    if tam_tinh:
        cau.append("Tạm tính: " + "; ".join(tam_tinh) + ".")
    if dac_biet:
        cau.append("⚠️ " + dac_biet[0][0].upper() + dac_biet[0][1:] + ".")
    if canh_bao:
        cau.append("⚠️ " + " ".join(m.split("→ ", 1)[1] for m in canh_bao))
    return " ".join(cau)


def soan_tin(spec: dict, don: DonHang, ket_qua: list) -> str:
    """Một tin Zalo gọn: quy cách · giá từng mức · bóc tách · so sánh cách in · ghi chú · chính sách."""
    r0 = ket_qua[0]
    L = [_dong_dau(spec, don, r0)]
    L += [_dong_gia(r) for r in ket_qua]
    if any(r.get("niem_yet") for r in ket_qua):
        nguon = next((r.get("niem_yet_nguon") for r in ket_qua if r.get("niem_yet_nguon")), "bảng giá My")
        L.append(f"📋 Giá bán theo {nguon}; chi phí bên dưới chỉ để tham khảo.")
    L.append(_dong_boc_tach(don, r0))
    so_sanh = _dong_so_sanh(don, r0)
    if so_sanh:
        L.append(so_sanh)
    L.append(_dong_ghi_chu(r0))
    L.append("📎 Chưa VAT 8%, chưa vận chuyển, không tặng khuôn. Gõ 'gửi khách' để lấy bản báo giá gửi khách.")
    msg = "\n".join(L)
    return msg if len(msg) <= 1990 else msg[:1985] + "…"


# ---------------------------------------------------------------- bản gửi khách
GC_KHONG_GHI_CHO_KHACH = ("dan_may", "dan_tay", "be", "be_hop_cung", "phay_ranh", "dung_hop", "boi_hop_cung", "cat_tp", "quai_tui", "dan_tui", "boi_nap_keo")
DONG_THANH_PHAM = {"hop_cung": "Bồi, bế thành phẩm hộp cứng", "tui_giay": "Bế, dán thành phẩm, xỏ quai", "tem_decal": "Bế demi thành phẩm", "hop_gap": "Bế, dán thành phẩm"}


def _quy_cach_cho_khach(don: DonHang, r0) -> list:
    tp0 = don.thanh_phan[0]
    L = []
    if don.loai_sp == "hop_cung":
        L += [f"- Giấy áo {tp0.loai} {tp0.gsm}gsm, lót ruột trơn", "- Bồi giấy Chipboard 2mm"]
    elif tp0.loai == "Decal":
        L.append("- Decal giấy")
    else:
        L.append(f"- Giấy {tp0.loai} {tp0.gsm}gsm")
    L.append(f"- In {'KTS' if r0['kts'] else 'offset'} {tp0.so_mau} màu {tp0.so_mat} mặt" if tp0.so_mau else "- Không in")
    for g in don.gia_cong:
        if g in P["gia_cong"] and g not in GC_KHONG_GHI_CHO_KHACH:
            ten = P["gia_cong"][g]["ten"]
            if g in ("can_mo", "can_bong"):
                ten += " 2 mặt" if don.can_mang_2_mat else " 1 mặt"
            L.append(f"- {ten}")
    L += [f"- {ten}" for ten, _ in don.gc_tuy_chinh if not any(k in ten.lower() for k in ("bế", "dán"))]
    L.append("- " + (DONG_THANH_PHAM.get(don.loai_sp) or ("Bế thành phẩm" if "be" in don.gia_cong else "Cắt thành phẩm")))
    return L


def soan_tin_khach(spec: dict, don: DonHang, ket_qua: list) -> str:
    """Bản gửi khách: cùng bố cục file báo giá PDF của NAHT, không có giá vốn / lãi / bóc tách."""
    r0 = ket_qua[0]
    kt = _kich_thuoc(spec, "x")
    L = [f"BÁO GIÁ: {don.ten}" + (f" KT {kt}cm" if kt and kt not in don.ten.replace("×", "x") else "")]
    L += _quy_cach_cho_khach(don, r0)
    L.append("")
    vat = P["vat"]
    for r in ket_qua:
        thanh_tien = r["gia_ban_tron"] * r["SL"]
        L.append(f"• {fmt(r['SL'])} cái: {fmt(r['gia_ban_tron'])} đ/cái · thành tiền {fmt(thanh_tien)} đ · gồm VAT {int(vat * 100)}%: {fmt(thanh_tien * (1 + vat))} đ")
    L += ["",
          "Thời gian sản xuất: 7-10 ngày kể từ ngày chốt đơn hàng. Thời gian mẫu: 3-7 ngày kể từ ngày chốt mẫu.",
          "Giá chưa gồm phí vận chuyển. Báo giá có hiệu lực 30 ngày."]
    con_tam_tinh = [u for u in dict.fromkeys(r0["uoc_tinh"]) if any(k in u for k in ("My chốt", "kết cấu đặc biệt", "CHƯA gồm", "em tính k"))]
    if con_tam_tinh:
        L.insert(0, "(Nội bộ, xoá dòng này trước khi gửi: còn khoản tạm tính, My duyệt giá trước. " + "; ".join(con_tam_tinh) + ")")
    return "\n".join(L)
