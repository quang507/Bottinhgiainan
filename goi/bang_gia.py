"""Bảng giá xưởng (prices.json). Mọi module dùng chung MỘT đối tượng P, nên sửa P tại chỗ là có hiệu lực ở mọi nơi."""
import json
import os

P = json.load(open(os.path.join(os.path.dirname(__file__), "prices.json"), encoding="utf-8"))

# Đặc tính từng loại sản phẩm, thay cho việc ghi cứng tên loại rải rác trong code.
LOAI = {
    #             có khổ trải 3D (hộp/túi)   được bớt tai dán khi bình bài   giấy mặc định   định lượng mặc định
    "hop_gap":   {"co_kho_trai": True,  "bot_tai_dan": True,  "giay": "Ivory",  "gsm": 300},
    "hop_cung":  {"co_kho_trai": True,  "bot_tai_dan": False, "giay": "Couche", "gsm": 150},
    "tui_giay":  {"co_kho_trai": True,  "bot_tai_dan": True,  "giay": "Couche", "gsm": 250},
    "thiep":     {"co_kho_trai": False, "bot_tai_dan": False, "giay": "Ivory",  "gsm": 300},
    "tem_decal": {"co_kho_trai": False, "bot_tai_dan": False, "giay": "Ivory",  "gsm": 1},
}
LOAI_MAC_DINH = "hop_gap"


def dac_tinh(loai: str) -> dict:
    return LOAI.get(loai, LOAI[LOAI_MAC_DINH])
