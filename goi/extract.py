"""Bóc tách tin nhắn khách thành thông số JSON bằng Claude. Chỉ bóc tách, không tính tiền."""
import json
from typing import List, Literal, Optional

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-5-5"

GiaCong = Literal["can_mo", "can_bong", "ep_kim", "dap_noi", "uv_dinh_vi", "be", "dan_may", "dan_tay", "dan_tui", "boi_giay", "cua_so", "xo_day"]


class GiaCongTuyChinh(BaseModel):
    ten: str = Field(description="Tên gia công khách/My nêu kèm đơn giá, ví dụ 'Dán dây'")
    gia_moi_cai: float = Field(description="đ/cái")


class Spec(BaseModel):
    san_pham: str = Field(description="Tên ngắn sản phẩm, ví dụ 'Hộp âm dương 30×25×5'")
    loai: Optional[Literal["hop_gap", "hop_cung", "tui_giay", "thiep", "tem_decal"]] = Field(
        description="hop_gap: hộp giấy gập (nắp gài, đáy gài, âm dương giấy, bao diêm giấy). "
                    "hop_cung: hộp cứng bồi chipboard/carton lạnh/bìa cứng. tui_giay: túi giấy có quai. "
                    "thiep: thiệp, card, tag. tem_decal: tem nhãn decal.")
    kieu_hop: Optional[str] = Field(description="Kiểu kết cấu nếu có: nắp gài, đáy gài, âm dương, nắp rời, bao diêm, nắp kéo/rút, nam châm")
    dai: Optional[float] = Field(description="cm")
    rong: Optional[float] = Field(description="cm")
    cao: Optional[float] = Field(description="cm; thiệp/tem không cần")
    so_luong: List[int] = Field(description="Các mức số lượng khách hỏi; rỗng nếu chưa nói")
    giay: Optional[Literal["Ivory", "Couche", "Couche Matt", "Bristol", "Kraft", "Duplex", "Ford", "Decal"]] = Field(
        description="Loại giấy chính. C150/C300 = Couche. I300 = Ivory. Chipboard là lõi, không phải giấy chính.")
    dinh_luong: Optional[int] = Field(description="gsm, ví dụ C150 → 150, Ivory 300 → 300")
    so_mau: Optional[int] = Field(description="4 nếu 'in màu/4 màu/offset màu'; 1 nếu 1 màu; 0 nếu không in; null nếu không nói")
    so_mat: Optional[int] = Field(description="1 hoặc 2 mặt in; null nếu không nói")
    gia_cong: List[GiaCong] = Field(description="cán mờ→can_mo, cán bóng→can_bong, ép kim/ép nhũ→ep_kim, dập nổi/chìm→dap_noi, UV định vị→uv_dinh_vi, bế→be, dán máy→dan_may, dán tay→dan_tay, bồi giấy/bồi 2 lớp→boi_giay, cửa sổ/support cửa sổ→cua_so, xỏ dây→xo_day")
    kieu_in_2_mat: Optional[Literal["AB", "tu_tro", "tro_nhip"]] = Field(description="Chỉ khi in 2 mặt và tin nói rõ: bình AB/sheet-wise → AB; tự trở/work and turn → tu_tro; trở nhíp/work and tumble → tro_nhip; null nếu không nói")
    in_kts: Optional[bool] = Field(description="true nếu tin nói in KTS / kỹ thuật số / in nhanh; false nếu nói rõ in offset; null nếu không nói")
    thieu: List[str] = Field(description="Các thông tin bắt buộc còn thiếu để báo giá: loại sản phẩm, kích thước, số lượng. Giấy/màu/gia công thiếu thì dùng mặc định, không liệt kê.")
    gia_giay_tr_tan: Optional[float] = Field(description="Giá giấy triệu đ/tấn nếu tin nói rõ (vd '18tr/tấn' → 18); null nếu không nói")
    tu_sua_bai: Optional[int] = Field(description="Số tờ sửa bài nếu tin nói rõ; null nếu không")
    kho_giay: Optional[Literal["65x43", "65x86", "79x109"]] = Field(description="Khổ giấy in nếu tin nói rõ")
    so_con_to: Optional[int] = Field(description="Số con/tờ nếu tin nói rõ")
    pct_loi_nhuan: Optional[float] = Field(description="Lợi nhuận dạng thập phân nếu tin nói rõ (vd 'lợi nhuận 0' → 0, '38%' → 0.38); null nếu không")
    khuon_be_nghin: Optional[int] = Field(description="Tiền khuôn bế nghìn đồng nếu tin nói rõ (vd 'khuôn 500k' → 500)")
    khong_proof: bool = Field(description="true nếu tin nói 'không proof'/'bỏ proof'")
    gia_cong_tuy_chinh: List[GiaCongTuyChinh] = Field(description="Các gia công có kèm đơn giá đ/cái trong tin (vd 'bế 1401đ/cái', 'dán dây 1500'). Gia công nào đã có ở đây thì KHÔNG đưa vào gia_cong nữa.")
    cau_hoi: str = Field(description="Nếu 'thieu' không rỗng: 1 câu hỏi tiếng Việt ngắn, thân thiện, hỏi đúng các mục thiếu. Nếu không thiếu: chuỗi rỗng.")


SYSTEM = """Bạn là nhân viên xưởng in bao bì GÓI, nhiệm vụ DUY NHẤT là bóc tách yêu cầu in ấn thành thông số có cấu trúc.
Quy tắc:
- Kích thước ghi dạng 30x25x5 là Dài×Rộng×Cao cm. Nếu ghi mm thì đổi sang cm. '12x35x7' với hộp dài: dài là số lớn nhất.
- 'Chipboard', 'bìa cứng', 'carton lạnh', 'hộp cứng', 'bồi' → loai = hop_cung; giấy áo thường là Couche 150.
- 'Hộp gập', 'nắp gài', 'Ivory', 'hộp giấy' thường → hop_gap.
- 'Cán màng mờ' = can_mo. 'Cán mờ 2 mặt' vẫn là can_mo (số mặt ghi vào so_mat).
- Khách có thể nhắn nhiều lần: nếu có THÔNG SỐ ĐÃ BIẾT, giữ nguyên các giá trị cũ và chỉ cập nhật/bổ sung từ tin mới. Tin mới ghi 'reset' hoặc sản phẩm hoàn toàn khác thì bỏ thông số cũ.
- Không bịa kích thước hay số lượng. Thiếu thì ghi vào 'thieu' và đặt 1 câu hỏi.
- Nhiều sản phẩm trong một tin: chọn sản phẩm đầu tiên, ghi các sản phẩm còn lại vào san_pham dạng '... (còn: ...)'.
"""


def boc_tach(client: anthropic.Anthropic, tin_moi: str, da_biet: Optional[dict] = None) -> Spec:
    noi_dung = ""
    if da_biet:
        noi_dung += "THÔNG SỐ ĐÃ BIẾT (từ các tin trước):\n" + json.dumps(da_biet, ensure_ascii=False) + "\n\n"
    noi_dung += "TIN NHẮN MỚI:\n" + tin_moi
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": noi_dung}],
        output_format=Spec,
    )
    return resp.parsed_output
