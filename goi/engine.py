"""Cửa vào duy nhất của phần tính giá. bot.py và test chỉ cần `from goi import engine`.

    bang_gia.py   bảng giá (prices.json) + đặc tính từng loại sản phẩm
    binh_bai.py   một tờ giấy xếp được mấy con
    san_pham.py   dựng DonHang từ thông số đã bóc tách (mỗi loại sản phẩm một hàm)
    tinh_gia.py   tính giá vốn và giá bán (6 bước)
    soan_tin.py   soạn tin Zalo: bản nội bộ và bản gửi khách

Kiểm chứng với Excel của My: python -m goi.engine
"""
from .bang_gia import P, LOAI                                                  # noqa: F401
from .binh_bai import ups, ups_bot_tai, lot_kho_giay                           # noqa: F401
from .san_pham import ThanhPhan, DonHang, dung_don                             # noqa: F401
from .tinh_gia import (tinh, gia_to, cong_in, gia_in_nhanh_to, giay_in_nhanh_duoc,   # noqa: F401
                       nen_in_nhanh, gia_niem_yet_decal)
from .soan_tin import fmt, fmt_k, soan_tin, soan_tin_khach, thong_bao_vuot_kho  # noqa: F401


def doi_chieu_excel() -> bool:
    """Sheet 'Đơn SLL' của My: 1.000 hộp Ivory 300 giá 18tr/tấn, 1 con/tờ 65×43, 4 màu, sửa bài 300.
    Kỳ vọng: giấy 2.007.369 · công in 1.200.000 · kẽm CTP 440.000."""
    P["giay_tr_tan"]["Ivory"] = 18
    P["tu_sua_bai"] = 300
    P["tu_sua_bai_theo_kho"] = {"65x43": 300}
    P["kho_giay"] = [[65, 43]]
    P["binh_bai"] = {"le_nhip_cm": 0, "bu_xen_cm": {}}
    r = tinh(DonHang("Đối chiếu", [ThanhPhan("Hộp giấy", "Ivory", 300, 40, 60, 1, 4, 1)], [], khuon_be=0), 1000)
    for ten, tien in r["dong"]:
        print(f"{ten:60} {tien:>14,.1f}")
    return abs(r["dong"][0][1] - 2007369) < 1 and r["dong"][1][1] == 1200000 and r["dong"][2][1] == 440000


if __name__ == "__main__":
    print("KHỚP EXCEL" if doi_chieu_excel() else "LỆCH EXCEL")
