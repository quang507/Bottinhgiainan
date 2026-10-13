"""Bóc tách tin nhắn khách thành thông số JSON bằng Claude. Chỉ bóc tách, không tính tiền.

Lưu ý API: schema structured output chỉ cho tối đa 16 trường union/nullable, nên ở đây KHÔNG dùng Optional.
Giá trị "chưa nói" dùng sentinel (0, "", [], -1) và được đổi về None trong chuan_hoa()."""
import json
import os
import re
from typing import List, Literal

import anthropic
import httpx
from pydantic import BaseModel, Field

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5")   # bóc tách đơn giản, Haiku đủ và rẻ
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")


def provider() -> str:
    """'gemini' nếu có GEMINI_API_KEY (miễn phí, mặc định), 'claude' nếu LLM_PROVIDER=claude."""
    p = os.environ.get("LLM_PROVIDER", "").lower()
    if p in ("gemini", "claude"):
        return p
    return "gemini" if os.environ.get("GEMINI_API_KEY") else "claude"

GiaCong = Literal["can_mo", "can_bong", "ep_kim", "dap_noi", "uv_dinh_vi", "be", "dan_may", "dan_tay", "dan_tui", "boi_giay", "cua_so", "xo_day"]


class GiaCongTuyChinh(BaseModel):
    ten: str = Field(description="Tên gia công khách/My nêu kèm đơn giá, ví dụ 'Dán dây'")
    gia_moi_cai: float = Field(description="đ/cái")


class Spec(BaseModel):
    san_pham: str = Field(description="Tên ngắn sản phẩm, ví dụ 'Hộp âm dương 30×25×5'")
    loai: Literal["hop_gap", "hop_cung", "tui_giay", "thiep", "tem_decal", "chua_ro"] = Field(
        description="hop_gap: hộp giấy gập (nắp gài, đáy gài, âm dương giấy, bao diêm giấy). "
                    "hop_cung: hộp cứng bồi chipboard/carton lạnh/bìa cứng. tui_giay: túi giấy có quai. "
                    "thiep: thiệp, card, thẻ bài/hangtag/tag treo giấy (thẻ bài thì gia_cong có 'be', có dây thì thêm 'xo_day'). "
                    "tem_decal: tem nhãn decal tờ. chua_ro: không xác định được hoặc thuộc dong_hang_khac.")
    dong_hang_khac: Literal["", "nhan_det", "nhan_in_vai", "nhan_ep_nhiet", "ruy_bang", "tem_cuon", "giay_cuon_bo_hang", "phu_lieu", "thung_carton", "the_nhua"] = Field(
        description="Chỉ điền khi khách hỏi sản phẩm KHÔNG phải hộp giấy/hộp cứng/túi giấy/thiệp-thẻ bài giấy/tem decal tờ: "
                    "nhan_det (nhãn dệt, woven label), nhan_in_vai (nhãn in satin/cotton, care label, nhãn mác vải), nhan_ep_nhiet (nhãn ép/chuyển nhiệt), "
                    "ruy_bang (dây ruy băng, ribbon), tem_cuon (tem nhãn dạng cuộn, barcode, tem size), giay_cuon_bo_hang, "
                    "phu_lieu (dây treo, đạn nhựa, kim băng, kẹp, bìa lưng, gói hút ẩm, khuy, dây kéo), thung_carton (thùng/hộp carton sóng), the_nhua. Còn lại để rỗng.")
    kieu_hop: str = Field(description="Kiểu kết cấu nếu có: nắp gài, đáy gài, đáy khóa, âm dương, nắp rời, bao diêm, nắp kéo/rút, nam châm. Rỗng nếu không nói.")
    dai: float = Field(description="cm, 0 nếu chưa biết")
    rong: float = Field(description="cm, 0 nếu chưa biết")
    cao: float = Field(description="cm, 0 nếu chưa biết; thiệp/tem không cần")
    so_luong: List[int] = Field(description="Các mức số lượng khách hỏi; rỗng nếu chưa nói")
    giay: Literal["Ivory", "Couche", "Couche Matt", "Bristol", "Kraft", "Duplex", "Ford", "Decal", "chua_ro"] = Field(
        description="Loại giấy chính. C150/C300 = Couche. I300/I210 = Ivory. Chipboard là lõi, không phải giấy chính. chua_ro nếu không nói.")
    dinh_luong: int = Field(description="gsm, ví dụ C150 → 150, Ivory 300 → 300; 0 nếu không nói")
    so_mau: int = Field(description="4 nếu 'in màu/4 màu/offset màu'; 1 nếu 1 màu; 0 nếu nói rõ không in; -1 nếu không nói")
    so_mat: int = Field(description="1 hoặc 2 mặt in; 0 nếu không nói")
    gia_cong: List[GiaCong] = Field(description="cán mờ→can_mo, cán bóng→can_bong, ép kim/ép nhũ→ep_kim, dập nổi/chìm→dap_noi, UV định vị→uv_dinh_vi, bế→be, dán máy→dan_may, dán tay→dan_tay, bồi giấy/bồi 2 lớp→boi_giay, cửa sổ/support cửa sổ→cua_so, xỏ dây→xo_day")
    thieu: List[str] = Field(description="Các thông tin bắt buộc còn thiếu để báo giá: loại sản phẩm, kích thước, số lượng. Giấy/màu/gia công thiếu thì dùng mặc định, không liệt kê.")
    cau_hoi: str = Field(description="Nếu 'thieu' không rỗng: 1 câu hỏi tiếng Việt ngắn, thân thiện, hỏi đúng các mục thiếu. Nếu không thiếu: chuỗi rỗng.")
    gia_giay_tr_tan: float = Field(description="Giá giấy triệu đ/tấn nếu tin nói rõ (vd '18tr/tấn' → 18); 0 nếu không nói")
    tu_sua_bai: int = Field(description="Số tờ sửa bài nếu tin nói rõ; -1 nếu không")
    kho_giay: Literal["65x43", "65x86", "79x109", ""] = Field(description="Khổ giấy in nếu tin nói rõ; rỗng nếu không")
    so_con_to: int = Field(description="Số con/tờ nếu tin nói rõ; 0 nếu không")
    pct_loi_nhuan: float = Field(description="Lợi nhuận dạng thập phân nếu tin nói rõ (vd 'lợi nhuận 0' → 0, '38%' → 0.38); -1 nếu không nói")
    khuon_be_nghin: int = Field(description="Tiền khuôn bế nghìn đồng nếu tin nói rõ (vd 'khuôn 500k' → 500); -1 nếu không")
    khong_proof: bool = Field(description="true nếu tin nói 'không proof'/'bỏ proof'")
    khuon_co_san: bool = Field(description="true nếu tin nói khuôn có sẵn / đã có khuôn / khách in lại / đơn lặp lại (không tính tiền khuôn)")
    gia_cong_tuy_chinh: List[GiaCongTuyChinh] = Field(description="Các gia công có kèm đơn giá đ/cái trong tin (vd 'bế 1401đ/cái', 'dán dây 1500'). Gia công nào đã có ở đây thì KHÔNG đưa vào gia_cong nữa.")
    ep_kim_kt: List[float] = Field(description="[dài, rộng] cm vùng ép kim nếu tin nói (vd 'ép kim logo 5x3cm' → [5,3]); rỗng nếu không")
    dap_noi_kt: List[float] = Field(description="[dài, rộng] cm vùng dập nổi nếu tin nói; rỗng nếu không")
    dap_noi_am_duong: bool = Field(description="true nếu dập nổi âm dương / dập nổi 2 khuôn")
    so_mep_dan: int = Field(description="Số mép dán của hộp nếu tin nói (nắp gài 1 mép, đáy khóa/đáy cài 3 mép); 0 nếu không")
    tui_2_manh: bool = Field(description="true nếu túi giấy dán 2 mảnh")
    gia_quai: float = Field(description="Giá quai túi đ/cặp nếu tin nói; 0 nếu không")
    can_mang_2_mat: bool = Field(description="true nếu tin nói cán màng (mờ/bóng) 2 mặt")
    khong_can_mang: bool = Field(description="true nếu tin nói rõ KHÔNG cán màng")
    kieu_in_2_mat: Literal["AB", "tu_tro", "tro_nhip", ""] = Field(description="Chỉ khi in 2 mặt và tin nói rõ: bình AB/sheet-wise → AB; tự trở/work and turn → tu_tro; trở nhíp/work and tumble → tro_nhip; rỗng nếu không nói")
    loai_anh: Literal["san_pham", "khuon", "bang_gia", "khac", ""] = Field(description="Chỉ khi có ảnh kèm: ảnh sản phẩm/mockup → san_pham; file khuôn/dieline → khuon; bảng giá → bang_gia; khác → khac. Không có ảnh → rỗng.")
    noi_dung_anh: str = Field(description="Chỉ khi có ảnh: mô tả ngắn nội dung ảnh (ví dụ bảng giá thì liệt kê các dòng giá; khuôn thì ghi kích thước trải nếu đọc được). Không có ảnh → rỗng.")
    y_dinh: Literal["bao_gia", "tom_tat", "khac"] = Field(description="bao_gia: tin có thông số sản phẩm mới hoặc bổ sung. tom_tat: chỉ hỏi lại giá/tóm tắt/giá 1 cái của báo giá vừa rồi, không thêm thông số nào. khac: chào hỏi, cảm ơn, nói chuyện khác.")
    in_kts: Literal["kts", "offset", ""] = Field(description="kts nếu tin nói in KTS / kỹ thuật số / in nhanh; offset nếu nói rõ in offset; rỗng nếu không nói")


SYSTEM = """Bạn là nhân viên xưởng in bao bì GÓI, nhiệm vụ DUY NHẤT là bóc tách yêu cầu in ấn thành thông số có cấu trúc.
Quy tắc:
- Quy ước kích thước:
  • Hộp / thùng (sản phẩm khối): Dài × Rộng × Cao đúng thứ tự khách ghi (L×W×H). 'hộp 13x4x21' → dai=13, rong=4, cao=21. 'hộp dài 35x12x7' → dai=35, rong=12, cao=7. Ghi mm thì đổi sang cm.
  • Ấn phẩm phẳng (thiệp, card, tem, tờ rơi): Ngang × Dọc → dai=ngang, rong=dọc, cao=0. 'thiệp 8x12' → dai=8, rong=12.
  • Túi giấy: dai = ngang (miệng túi), rong = hông (đáy), cao = chiều cao. Nếu tin ghi rõ từ 'cao', 'hông', 'ngang' thì theo chữ. Nếu chỉ có 3 số không chú thích: hông = số nhỏ nhất, cao = số lớn nhất, ngang = số còn lại. 'túi cao 30*25*8' → cao=30, dai=25, rong=8.
- 'Chipboard', 'bìa cứng', 'carton lạnh', 'hộp cứng', 'bồi' → loai = hop_cung; giấy áo thường là Couche 150.
- 'Hộp gập', 'nắp gài', 'Ivory', 'hộp giấy' thường → hop_gap.
- 'Cán màng mờ' = can_mo. 'Cán mờ 2 mặt' → can_mo và can_mang_2_mat = true.
- Khách có thể nhắn nhiều lần: nếu có THÔNG SỐ ĐÃ BIẾT, giữ nguyên các giá trị cũ và chỉ cập nhật/bổ sung từ tin mới. Tin mới ghi 'reset' hoặc sản phẩm hoàn toàn khác thì bỏ thông số cũ.
- Túi giấy: kích thước là Dài (miệng) × Rộng (hông) × Cao. Nếu ghi 'túi cao 30*25*8' thì 30 là cao, 25 dài, 8 hông → dai=25, rong=8, cao=30. Hộp: 'hộp 13*4*21' → dai=13, rong=4, cao=21 theo thứ tự ghi.
- 'Hũ nhựa', 'chai', 'lọ', 'sản phẩm bên trong' là thứ khách ĐỰNG trong hộp, không phải dong_hang_khac. the_nhua chỉ khi khách hỏi in thẻ nhựa PVC.
- 'thieu' chỉ được chứa: loại sản phẩm, kích thước, số lượng. KHÔNG hỏi loại giấy, số màu, gia công (bot có mặc định).
- Không bịa kích thước hay số lượng. Thiếu thì ghi vào 'thieu' và đặt 1 câu hỏi.
- Nhiều sản phẩm trong một tin: chọn sản phẩm đầu tiên, ghi các sản phẩm còn lại vào san_pham dạng '... (còn: ...)'.
- Trường không có thông tin: số → 0 (hoặc -1 nếu mô tả nói vậy), chuỗi → rỗng, danh sách → rỗng. Không đoán.
"""


def chuan_hoa(spec: "Spec") -> dict:
    """Đổi sentinel về None để engine dùng như trước."""
    d = spec.model_dump()
    for k in ("dai", "rong", "cao", "dinh_luong", "so_con_to", "gia_giay_tr_tan", "gia_quai", "so_mep_dan"):
        if not d[k]:
            d[k] = None
    for k in ("so_mau", "tu_sua_bai", "pct_loi_nhuan", "khuon_be_nghin"):
        if d[k] is not None and d[k] < 0:
            d[k] = None
    if not d["so_mat"]:
        d["so_mat"] = None
    for k in ("kieu_hop", "kho_giay", "kieu_in_2_mat", "cau_hoi"):
        if d[k] == "":
            d[k] = None if k != "cau_hoi" else ""
    if d["loai"] == "chua_ro":
        d["loai"] = None
    if d["giay"] == "chua_ro":
        d["giay"] = None
    d["in_kts"] = {"kts": True, "offset": False}.get(d["in_kts"])
    for k in ("ep_kim_kt", "dap_noi_kt"):
        if len(d[k]) != 2:
            d[k] = None
    return d


def _schema_gemini() -> dict:
    """JSON schema của Spec, inline $defs (Gemini không nhận $ref)."""
    sch = Spec.model_json_schema()
    defs = sch.pop("$defs", {})

    def deref(o):
        if isinstance(o, dict):
            if "$ref" in o:
                return deref(defs[o["$ref"].split("/")[-1]])
            return {k: deref(v) for k, v in o.items() if k not in ("title",)}
        if isinstance(o, list):
            return [deref(x) for x in o]
        return o
    return deref(sch)


def _goi_gemini(noi_dung: str, anh: tuple = None) -> "Spec":
    key = os.environ["GEMINI_API_KEY"]
    parts = []
    if anh:
        parts.append({"inline_data": {"mime_type": anh[0], "data": anh[1]}})
    parts.append({"text": noi_dung})
    if anh:
        parts.append({"text": "Có ảnh kèm theo: phân loại vào loai_anh và mô tả vào noi_dung_anh. Nếu là ảnh sản phẩm/khuôn, lấy thông số từ ảnh."})
    body = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": _schema_gemini(), "temperature": 0},
    }
    import time as _t
    last = None
    models = [m.strip() for m in os.environ.get("GEMINI_MODELS", "gemini-3.5-flash-lite,gemini-3.5-flash").split(",") if m.strip()]
    for model in models:
        if _HET_HAN.get(model, 0) > _t.time():
            last = last or RuntimeError(f"Gemini {model} 429: hết hạn mức ngày")
            continue
        for lan in range(2):
            r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                           params={"key": key}, json=body, timeout=45)
            if r.status_code == 200:
                text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
                return Spec.model_validate(json.loads(text))
            last = RuntimeError(f"Gemini {model} {r.status_code}: {r.text[:200]}")
            if r.status_code == 429:
                m = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                cho = int(m.group(1)) if m else 60
                if cho > 20 or "PerDay" in r.text:          # hết hạn mức ngày/phút dài → bỏ model này, không chờ
                    _HET_HAN[model] = _t.time() + min(cho, 6 * 3600)
                    break
                _t.sleep(min(cho, 5) + 1)
                continue
            if r.status_code == 503 and lan == 0:
                _t.sleep(2)
                continue
            break
    raise last


_HET_HAN = {}      # model → thời điểm (epoch) được thử lại


def boc_tach(client: anthropic.Anthropic, tin_moi: str, da_biet: dict = None, anh: tuple = None) -> dict:
    """anh = (media_type, base64) nếu khách gửi ảnh; tin_moi khi đó là caption (có thể rỗng)."""
    noi_dung = ""
    if da_biet:
        noi_dung += "THÔNG SỐ ĐÃ BIẾT (từ các tin trước):\n" + json.dumps(da_biet, ensure_ascii=False) + "\n\n"
    noi_dung += "TIN NHẮN MỚI:\n" + (tin_moi or "(khách gửi ảnh, không có chữ)")
    if provider() == "gemini":
        try:
            return chuan_hoa(_goi_gemini(noi_dung, anh))
        except RuntimeError as e:
            # hết credit / quá hạn mức Gemini → thử Claude nếu có key
            if client is None:
                raise
    if client is None:
        raise RuntimeError("Chưa cấu hình LLM nào có tiền (GEMINI_API_KEY hoặc ANTHROPIC_API_KEY)")
    content = [{"type": "text", "text": noi_dung}]
    if anh:
        content.insert(0, {"type": "image", "source": {"type": "base64", "media_type": anh[0], "data": anh[1]}})
        content.append({"type": "text", "text": "Có ảnh kèm theo: phân loại vào loai_anh và mô tả vào noi_dung_anh. Nếu là ảnh sản phẩm/khuôn, lấy thông số từ ảnh."})
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": content}],
        output_format=Spec,
    )
    return chuan_hoa(resp.parsed_output)
