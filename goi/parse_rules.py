"""Đọc tin nhắn báo giá bằng quy tắc (regex), không cần AI.

Trả về (spec, chac, y_dinh):
- spec: dict cùng dạng với extract.chuan_hoa()
- chac: True nếu đủ tự tin để KHÔNG cần gọi AI (1 sản phẩm, có loại + kích thước + số lượng, không có từ lạ)
- y_dinh: 'bao_gia' | 'tom_tat' | 'khac'
"""
import re

NUM = r"\d+(?:[.,]\d+)?"
DIM = re.compile(rf"({NUM})\s*(?:cm|mm)?\s*[x×*]\s*({NUM})(?:\s*(?:cm|mm)?\s*[x×*]\s*({NUM}))?\s*(mm|cm)?", re.I)
DON_VI_SL = r"(?:cái|chiếc|hộp|túi|tem|thiệp|thẻ|tấm|tờ|bộ|cuộn|nhãn|pcs|sp|hangtag|tag|decal|sticker|đai|ống|vòng|khay|set|combo|bao|c)\b"

DONG_HANG = [
    ("nhan_det", r"nhãn dệt|mác dệt|woven"),
    ("nhan_ep_nhiet", r"ép nhiệt|chuyển nhiệt|heat transfer"),
    ("nhan_in_vai", r"nhãn (?:in )?(?:satin|cotton|vải)|care label|nhãn mác vải|mác vải|nhãn sườn"),
    ("ruy_bang", r"ruy băng|ribbon"),
    ("tem_cuon", r"tem (?:nhãn )?cuộn|tem mã vạch|tem barcode|decal cuộn"),
    ("giay_cuon_bo_hang", r"giấy cuộn|bó hàng"),
    ("thung_carton", r"thùng|carton sóng|\d lớp|hộp sóng"),
    ("the_nhua", r"thẻ nhựa"),
    ("ong_giay", r"ống tròn|ống giấy|hộp trụ|hộp tròn"),
    ("phu_lieu", r"phụ liệu|dây treo thẻ|đạn nhựa|kim băng|kẹp nhựa|bìa lưng|hút ẩm|khuy|dây kéo"),
]
LOAI = [
    ("hop_cung", r"hộp cứng|chipboard|carton lạnh|bìa cứng|bồi carton|nam châm"),
    ("tui_giay", r"\btúi\b"),
    ("tem_decal", r"decal|đề can|tem nhãn|tem dán|sticker|\btem\b"),
    ("thiep", r"thiệp|card|danh thiếp|thẻ bài|hangtag|hang tag|tag treo|thẻ treo|nhãn treo|\btấm\b|tờ rơi|ấn phẩm|đai giấy|\bđai\b|vòng cổ"),
    ("hop_gap", r"\bhộp\b"),
]
GIAY = [
    ("Couche Matt", r"couch[eé] ?matt?|c ?matt"),
    ("Ivory", r"ivory|\bi ?\d{3}(?!\d)"),
    ("Couche", r"couch[eé]|\bc ?\d{2,3}(?!\d)"),
    ("Kraft", r"kraft|\bk ?\d{3}(?!\d)"),
    ("Duplex", r"duplex|\bd ?\d{3}(?!\d)"),
    ("Bristol", r"bristol|\bb ?\d{3}(?!\d)"),
    ("Ford", r"\bfor[dt]\b"),
]
KIEU = r"nắp gài|đáy khóa|đáy khoá|đáy cài|đáy gài|âm dương|nắp rời|bao diêm|nắp kéo|hộp rút|nam châm|hộp gối|móc đáy"
TU_LA = r"mỹ thuật|metalize|met\b|pantone|pha màu|nhũ bạc|hologram|decal nhựa|màng nhựa|hộp nhựa|túi nhựa|nilon|vải|gỗ|lót xốp|cán vân|7 màu"


def ket_cau_dac_biet(tin: str, P: dict) -> list:
    t = (tin or "").lower()
    return list(dict.fromkeys(v for k, v in P.get("ket_cau_dac_biet", {}).items() if not k.startswith("_") and k in t))


def thieu_cua(s: dict) -> list:
    """Chỉ 3 thứ bắt buộc: loại, kích thước, số lượng. Giấy/màu/gia công thiếu thì dùng mặc định."""
    thieu = []
    loai = s.get("loai")
    if not loai:
        thieu.append("loại sản phẩm (hộp giấy, hộp cứng, túi, thiệp, thẻ bài, tem decal)")
    if not s.get("dai") or not s.get("rong") or (loai in ("hop_gap", "hop_cung", "tui_giay") and not s.get("cao")):
        thieu.append("kích thước (dài × rộng × cao cm)" if loai in ("hop_gap", "hop_cung", "tui_giay", None) else "kích thước (ngang × dọc cm)")
    if not s.get("so_luong"):
        thieu.append("số lượng")
    return thieu


def _f(x):
    return float(str(x).replace(",", "."))


def _int(x):
    return int(re.sub(r"[.,\s]", "", x))


# kích thước đứng sau các từ này là vùng gia công, không phải kích thước sản phẩm
VUNG_GIA_CONG = [("ep_kim_kt", r"ép kim|ép nhũ"), ("dap_noi_kt", r"dập nổi|dập chìm"),
                 ("cua_so_kt", r"cửa sổ(?=[^,;.\n]{0,12}$)"), ("uv_kt", r"\buv\b(?=[^,;.\n]{0,14}$)")]


def _vung_gia_cong(truoc: str, so_chieu: int, ca_tin: str):
    """Kích thước này thuộc vùng gia công nào: lấy từ khoá đứng gần nhất phía trước. None nếu là kích thước sản phẩm."""
    gan = [(m.start(), key) for key, mau in VUNG_GIA_CONG for m in re.finditer(mau, truoc)
           if so_chieu == 2 or key in ("ep_kim_kt", "dap_noi_kt")]
    if gan:
        return max(gan)[1]
    if re.search(r"logo", truoc) and re.search(r"ép kim|ép nhũ", ca_tin):
        return "ep_kim_kt"
    return None


def _spec_trong():
    return {"san_pham": "", "loai": None, "kieu_hop": None, "dai": None, "rong": None, "cao": None, "so_luong": [],
            "giay": None, "dinh_luong": None, "so_mau": None, "so_mat": None, "gia_cong": [], "thieu": [], "cau_hoi": "",
            "gia_giay_tr_tan": None, "tu_sua_bai": None, "kho_giay": None, "so_con_to": None, "pct_loi_nhuan": None,
            "khuon_be_nghin": None, "khong_proof": False, "khuon_co_san": False, "gia_cong_tuy_chinh": [],
            "ep_kim_kt": None, "dap_noi_kt": None, "dap_noi_am_duong": False, "so_mep_dan": None, "tui_2_manh": False,
            "gia_quai": None, "can_mang_2_mat": False, "uv_kt": None, "cua_so_kt": None, "day_2_gut": False, "con_khuon": None, "khong_can_mang": False, "kieu_in_2_mat": None, "in_kts": None, "y_dinh": "bao_gia",
            "dong_hang_khac": "", "loai_anh": "", "noi_dung_anh": ""}


def phan_tich(tin: str, da_biet: dict = None):
    t = " " + (tin or "").lower().replace("\n", " , ") + " "
    t = t.replace("cáng", "cán").replace("ko ", "không ").replace(" k ", " không ").replace(" hok ", " không ")
    co_cu = bool(da_biet and da_biet.get("loai"))
    s = _spec_trong()
    if da_biet:
        for k, v in da_biet.items():
            if k in s and k not in ("thieu", "cau_hoi", "y_dinh", "loai_anh", "noi_dung_anh"):
                s[k] = list(v) if isinstance(v, list) else v
    moi = set()          # các trường tin này vừa đặt

    # ---- dòng hàng chưa có giá ----
    dh = next((k for k, p in DONG_HANG if re.search(p, t)), "")
    vi_tri = [(re.search(p, t).start(), k) for k, p in LOAI if re.search(p, t)]
    loai_moi = min(vi_tri)[1] if vi_tri else None
    if loai_moi == "hop_gap" and any(k == "hop_cung" for _, k in vi_tri):
        loai_moi = "hop_cung"                       # "hộp ... chipboard" là hộp cứng
    la_bao_bi = loai_moi in ("hop_gap", "hop_cung", "tui_giay")
    if dh == "tem_cuon":
        la_bao_bi = False
    if dh and not (la_bao_bi and dh != "thung_carton") and not (dh == "thung_carton" and loai_moi == "hop_cung"):
        s2 = _spec_trong(); s2["dong_hang_khac"] = dh
        return s2, True, "bao_gia"

    # ---- đơn giá gia công tuỳ chỉnh (trước khi bóc số khác) ----
    tuy_chinh = []
    for m in re.finditer(r"(bế|dán dây|dán hộp|dán|ép kim|ép nhũ|dập nổi|cán màng mờ|cán màng bóng|cán mờ|cán bóng|xỏ dây)\s*:?\s*(\d[\d.]*)\s*đ\s*/\s*(?:cái|con|hộp|c)\b", t):
        tuy_chinh.append({"ten": m.group(1).capitalize(), "gia_moi_cai": float(_int(m.group(2)))})
    t_gc = re.sub(r"(bế|dán dây|dán hộp|dán|ép kim|ép nhũ|dập nổi|cán màng mờ|cán màng bóng|cán mờ|cán bóng|xỏ dây)\s*:?\s*\d[\d.]*\s*đ\s*/\s*(?:cái|con|hộp|c)\b", " ", t)
    if tuy_chinh:
        s["gia_cong_tuy_chinh"] = tuy_chinh; moi.add("gia_cong_tuy_chinh")

    # ---- tham số kiểu My ----
    m = re.search(rf"({NUM})\s*(?:tr|triệu)\s*/\s*tấn", t_gc)
    if m: s["gia_giay_tr_tan"] = _f(m.group(1)); moi.add("x")
    m = re.search(r"sửa bài\s*(\d+)", t_gc)
    if m: s["tu_sua_bai"] = int(m.group(1)); moi.add("x")
    m = re.search(r"khổ(?: in| giấy)?\s*(65\s*x\s*43|65\s*x\s*86|79\s*x\s*109)", t_gc)
    if m: s["kho_giay"] = m.group(1).replace(" ", ""); moi.add("x")
    m = re.search(r"(\d+)\s*con\s*/\s*tờ", t_gc)
    if m: s["so_con_to"] = int(m.group(1)); moi.add("x")
    m = re.search(rf"(?:lợi nhuận|lãi)\s*:?\s*({NUM})\s*(%?)", t_gc)
    if m:
        v = _f(m.group(1)); s["pct_loi_nhuan"] = v / 100 if (m.group(2) or v > 1) else v; moi.add("x")
    m = re.search(r"khuôn(?: bế)?\s*:?\s*(\d+)\s*con\b(?!\s*/)", t_gc)
    if m: s["con_khuon"] = int(m.group(1)); moi.add("x")
    m = re.search(r"khuôn(?: bế)?\s*:?\s*(\d+)\s*k\b", t_gc)
    if m: s["khuon_be_nghin"] = int(m.group(1)); moi.add("x")
    if re.search(r"không proof|bỏ proof", t_gc): s["khong_proof"] = True; moi.add("x")
    if re.search(r"khuôn có sẵn|có sẵn khuôn|đã có khuôn|có khuôn rồi|in lại|đơn lặp|tái bản", t_gc): s["khuon_co_san"] = True; moi.add("x")
    if re.search(r"in offset|chạy offset|\boffset\b", t_gc): s["in_kts"] = False; moi.add("x")
    if re.search(r"in kts|kỹ thuật số|in nhanh|in số|\bkts\b", t_gc): s["in_kts"] = True; moi.add("x")
    for k, p in (("AB", r"bình ab|sheet-?wise"), ("tu_tro", r"tự trở|work and turn"), ("tro_nhip", r"trở nhíp|work and tumble")):
        if re.search(p, t_gc): s["kieu_in_2_mat"] = k; moi.add("x")
    m = re.search(r"quai[^,;.\n]{0,25}?(\d[\d.]*)\s*đ", t_gc)
    if m: s["gia_quai"] = float(_int(m.group(1))); moi.add("x")
    if re.search(r"2 mảnh|hai mảnh", t_gc): s["tui_2_manh"] = True; moi.add("x")
    m = re.search(r"(\d)\s*mép dán", t_gc)
    if m: s["so_mep_dan"] = int(m.group(1)); moi.add("x")

    # bỏ các cụm đã đọc để không lẫn vào kích thước/số lượng
    t2 = re.sub(rf"{NUM}\s*(?:tr|triệu)\s*/\s*tấn|sửa bài\s*\d+\s*(?:tờ)?|khổ(?: in| giấy)?\s*\d+\s*x\s*\d+|\d+\s*con\s*/\s*tờ|khuôn(?: bế)?\s*:?\s*\d+\s*con\b(?!\s*/)|khuôn(?: bế)?\s*:?\s*\d+\s*k\b|(?:lợi nhuận|lãi)\s*:?\s*{NUM}\s*%?|quai[^,;.\n]{{0,25}}?\d[\d.]*\s*đ(?:\s*/\s*cặp)?|\d+[.,]?\d*\s*đ\s*/\s*m2", " ", t_gc)

    # ---- kích thước ----
    dims_sp = []
    for m in DIM.finditer(t2):
        truoc = t2[max(0, m.start() - 28):m.start()]
        a = [_f(x) for x in m.groups()[:3] if x]
        if m.group(4) == "mm" or re.search(r"mm", t2[m.start():m.end() + 3]):
            a = [x / 10 for x in a]
        vung = _vung_gia_cong(truoc, len(a), t2)
        if vung:
            s[vung] = a[:2]; moi.add("x")
        else:
            dims_sp.append(a)
    t3 = DIM.sub(" ", t2)
    nhan = {}
    for ten, key in (("ngang|dài|rộng miệng", "dai"), ("hông|đáy|rộng", "rong"), ("cao", "cao")):
        m = re.search(rf"(?:chiều\s*)?(?:{ten})\s*:?\s*({NUM})\s*(cm|mm)?", t3)
        if m: nhan[key] = _f(m.group(1)) / (10 if m.group(2) == "mm" else 1)
    m = re.search(rf"(?:đường kính|phi|ø|Ø|đk)\s*:?\s*({NUM})\s*(cm|mm)?", t3)
    if m and not dims_sp:
        d = _f(m.group(1)) / (10 if (m.group(2) == "mm" or (not m.group(2) and _f(m.group(1)) > 40)) else 1)
        nhan = {"dai": d, "rong": d}
        t3 = t3[:m.start()] + " " + t3[m.end():]
    if not loai_moi and not s.get("loai") and not dims_sp and set(nhan) == {"dai", "cao"}:
        loai_moi = "thiep"                          # chỉ có ngang × cao, không hông/rộng → ấn phẩm phẳng
        if not s.get("san_pham"): s["san_pham"] = "Ấn phẩm"
    nhieu_sp = len(dims_sp) > 1
    mm_doan = False
    if dims_sp:
        a = dims_sp[0]
        if max(a) > 130 and not re.search(r"\bcm\b", t2):       # 120x80x40 không ghi đơn vị → mm
            a = [x / 10 for x in a]; mm_doan = True
        loai_tam = loai_moi or s.get("loai")
        if loai_tam == "tui_giay" and len(a) == 3 and not nhan:
            b = sorted(a); s["rong"], s["dai"], s["cao"] = b[0], b[1], b[2]
        else:
            s["dai"], s["rong"], s["cao"] = a[0], a[1], (a[2] if len(a) == 3 else None)
        moi.add("kt")
    elif nhan:
        if "dai" in nhan: s["dai"] = nhan["dai"]
        if "rong" in nhan: s["rong"] = nhan["rong"]
        elif (loai_moi or s.get("loai")) in ("thiep", "tem_decal") and "cao" in nhan:
            s["rong"] = nhan.pop("cao")          # ấn phẩm phẳng: ngang × cao
        if "cao" in nhan: s["cao"] = nhan["cao"]
        moi.add("kt")
        t3 = re.sub(rf"(?:chiều\s*)?(?:ngang|dài|rộng miệng|hông|đáy|rộng|cao)\s*:?\s*{NUM}\s*(?:cm|mm)?", " ", t3)

    # ---- loại sản phẩm ----
    if loai_moi and (loai_moi != s.get("loai")) and ("kt" in moi or not co_cu):
        giu = {k: s[k] for k in ("dai", "rong", "cao", "ep_kim_kt", "dap_noi_kt")}
        if co_cu and "kt" in moi:                     # sản phẩm mới hẳn → bỏ thông số cũ
            s0 = _spec_trong(); s0.update({k: v for k, v in s.items() if k in moi}); s = s0
            s.update(giu)
        s["loai"] = loai_moi; moi.add("loai")
    m = re.search(KIEU, t3)
    if m: s["kieu_hop"] = m.group(0).replace("khoá", "khóa"); moi.add("x")

    # ---- giấy, định lượng ----
    for ten, p in GIAY:
        m = re.search(p, t3)
        if m:
            s["giay"] = ten; moi.add("x")
            d = re.search(r"(\d{2,3})", m.group(0)) or re.search(rf"(?:{p})\s*(\d{{2,3}})\b", t3)
            if d: s["dinh_luong"] = int(d.group(1))
            break
    m = re.search(r"(\d{2,3})\s*(?:gsm|g\b|gr\b)", t3)
    if m: s["dinh_luong"] = int(m.group(1)); moi.add("x")
    if s.get("loai") == "tem_decal": s["giay"] = "Decal"

    # ---- in ----
    t_in = re.sub(r"(?:mặt trong|bên trong|ruột|lót|đáy)[^,;.]{0,12}không in", " ", t3)
    m = re.search(r"(\d)\s*màu", t_in)
    if m: s["so_mau"] = int(m.group(1)); moi.add("x")
    elif re.search(r"in màu|full màu|cmyk", t_in): s["so_mau"] = 4; moi.add("x")
    elif re.search(r"không in|khỏi in|hộp trơn|để trơn", t_in): s["so_mau"] = 0; moi.add("x")
    m = re.search(r"in\s*(?:\d\s*màu\s*)?(\d)\s*mặt|(\d)\s*mặt\s*in", t3)
    if m: s["so_mat"] = int(m.group(1) or m.group(2)); moi.add("x")

    # ---- gia công ----
    gc = list(s.get("gia_cong") or [])
    def them(k):
        if k not in gc: gc.append(k)
        moi.add("gc")
    def bo(k):
        if k in gc: gc.remove(k); moi.add("gc")
    if re.search(r"không c[áa]ng? màng|không cán|bỏ cán|khỏi cán", t3): bo("can_mo"); bo("can_bong"); s["khong_can_mang"] = True
    else:
        if re.search(r"cán (?:màng )?bóng", t3): bo("can_mo"); them("can_bong")
        elif re.search(r"cán (?:màng )?mờ|cán màng", t3): bo("can_bong"); them("can_mo")
        if re.search(r"cán[^,;.\n]{0,14}2 mặt", t3): s["can_mang_2_mat"] = True
    if re.search(r"ép kim|ép nhũ", t3) and not any("ép" in g["ten"].lower() for g in s["gia_cong_tuy_chinh"]): them("ep_kim")
    if re.search(r"dập nổi|dập chìm", t3) and not any("dập" in g["ten"].lower() for g in s["gia_cong_tuy_chinh"]): them("dap_noi")
    if re.search(r"dập nổi âm dương|dập 2 khuôn", t3): s["dap_noi_am_duong"] = True
    if re.search(r"\buv\b", t3): them("uv_dinh_vi")
    if re.search(r"bồi giấy|bồi 2 lớp", t3) and s.get("loai") != "hop_cung": them("boi_giay")
    if re.search(r"cửa sổ", t3): them("cua_so")
    if re.search(r"2 gút|hai gút", t3): s["day_2_gut"] = True
    if re.search(r"xỏ dây|dây treo", t3) and not any("dây" in g["ten"].lower() for g in s["gia_cong_tuy_chinh"]): them("xo_day")
    if re.search(r"\bbế\b", t3) and s.get("loai") in ("thiep",) and not tuy_chinh: them("be")
    if re.search(r"bỏ ép kim|không ép kim", t3): bo("ep_kim")
    if re.search(r"bỏ dập nổi|không dập", t3): bo("dap_noi")
    s["gia_cong"] = gc

    # ---- số lượng ----
    sl = []
    for m in re.finditer(rf"((?:\d[\d.]*\s*(?:,|;|/|và|\s)\s*)*\d[\d.]*)\s*{DON_VI_SL}", t3):
        for x in re.findall(r"\d[\d.]*", m.group(1)):
            v = _int(x)
            if 10 <= v <= 5_000_000: sl.append(v)
    m = re.search(r"(?:số lượng|sl|slg)\s*:?\s*((?:\d[\d.]*\s*(?:,|;|/|và)?\s*)+)", t3)
    if m:
        for x in re.findall(r"\d[\d.]*", m.group(1)):
            v = _int(x)
            if 10 <= v <= 5_000_000 and v not in sl: sl.append(v)
    if not sl:
        m = re.search(r"(?:mức|mốc)\s*((?:\d[\d.]*\s*(?:,|;|/|và)?\s*)+)", t3)
        if m: sl = [v for v in (_int(x) for x in re.findall(r"\d[\d.]*", m.group(1))) if 10 <= v <= 5_000_000]
    if not sl:
        m = re.match(r"\s*(?:báo giá|tính giá|tính giúp|cần|in|làm|đặt|e cần|em cần|a cần|anh cần)?\s*(\d[\d.]*)\s+(?!màu|mặt|gsm|cm|mm|g\b|tr\b|k\b|đ\b|lớp|x\b)[a-zà-ỹ]", t3)
        if m and 10 <= _int(m.group(1)) <= 5_000_000:
            sl = [_int(m.group(1))]
    if sl:
        s["so_luong"] = sorted(dict.fromkeys(sl)); moi.add("sl")

    # ---- ý định ----
    hoi_gia = bool(re.search(r"tóm (?:lại|tắt)|chốt giá|giá (?:bán )?(?:bao nhiêu|sao|nhiêu)|bao nhiêu (?:tiền|1 cái|một cái|vậy)|nhiêu (?:tiền|1 cái)", t))
    chao = bool(re.fullmatch(r"[\s,.!]*(?:xin chào|chào|hi|hello|alo|cảm ơn|cám ơn|thanks|ok|oke|dạ|vâng)[\s\w,.!]{0,25}", t.strip()))
    if not moi and hoi_gia and co_cu: y = "tom_tat"
    elif not moi and (chao or not re.search(r"\d", t)) and not loai_moi: y = "khac"
    else: y = "bao_gia"
    s["y_dinh"] = y

    # ---- tên + thiếu ----
    ten_loai = {"hop_gap": "Hộp giấy", "hop_cung": "Hộp cứng", "tui_giay": "Túi giấy", "thiep": "Thiệp", "tem_decal": "Tem decal"}
    if "loai" in moi or not s.get("san_pham"):
        ten = ten_loai.get(s.get("loai"), "")
        if s.get("loai") == "thiep":
            if re.search(r"thẻ bài|hangtag|hang tag|tag treo|thẻ treo|nhãn treo", t): ten = "Thẻ bài"
            elif re.search(r"\btấm\b", t): ten = "Tấm giấy"
            elif re.search(r"đai", t): ten = "Đai giấy"
            elif re.search(r"vòng cổ", t): ten = "Vòng cổ hũ"
            elif re.search(r"tờ rơi", t): ten = "Tờ rơi"
            elif not re.search(r"thiệp|card|danh thiếp", t): ten = "Ấn phẩm"
        if s.get("loai") == "hop_cung" and s.get("kieu_hop"): ten = f"Hộp cứng {s['kieu_hop']}"
        elif s.get("loai") == "hop_gap" and s.get("kieu_hop"): ten = f"Hộp {s['kieu_hop']}" if "hộp" not in s["kieu_hop"] else s["kieu_hop"].capitalize()
        s["san_pham"] = ten
    thieu = thieu_cua(s)
    s["thieu"] = thieu
    s["cau_hoi"] = ("Dạ anh/chị cho em xin thêm " + ", ".join(thieu) + " để em báo giá ạ.") if thieu else ""

    s["nhieu_sp"] = nhieu_sp
    tu_la = bool(re.search(TU_LA, t))
    chac = (y != "bao_gia") or (not nhieu_sp and not tu_la and not mm_doan and bool(s.get("loai")) and (bool(moi) or not thieu))
    return s, chac, y
