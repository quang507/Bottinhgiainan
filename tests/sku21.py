"""Đo độ phủ: cho bot báo giá toàn bộ 21 SKU của GÓI + các đơn thật. Dùng: python tests/sku21.py <out.txt> [--no-ai]"""
import sys, time, pathlib, tempfile, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import os
os.chdir(ROOT)
import bot  # noqa: E402
bot.STATE_FILE = pathlib.Path(tempfile.mkdtemp()) / "state.json"
bot.state.clear()
GOI_AI = []
_goc = bot.boc_tach
def _dem(client, tin, da_biet=None, anh=None):
    GOI_AI.append(tin)
    if "--no-ai" in sys.argv:
        raise RuntimeError("AI tắt")
    return _goc(client, tin, da_biet, anh)
bot.boc_tach = _dem

CASES = [
    # (mã, tin nhắn kiểu khách/My)
    ("LX200", "500 hộp lạp xưởng nắp gài 2 đầu có cửa sổ kiếng PVC, 11x3x19cm, Ivory 350, in 4 màu, cán bóng"),
    ("LX500", "1000 hộp nắp gài 2 đầu có cửa sổ 13x5x21 cm ivory 350 in 4 màu cán bóng"),
    ("LX1000", "hộp thực phẩm khô 1kg 15x7x24cm, 500 cái, ivory 350, cán mờ"),
    ("QXS-1", "300 hộp quai xách liền thân có cửa sổ 13x11x18 cm, ivory 350, in 4 màu cán mờ"),
    ("QXS-2", "300 hộp quai xách liền thân có cửa sổ loại 2 hũ 22x11x18cm ivory 350 cán mờ"),
    ("DST01", "200 hộp quà quai xách vát chóp có khay 4 ô, 28x20x18 cm, in 4 màu cán mờ ép kim"),
    ("DST02", "100 hộp cứng nắp bật nam châm 30x20x10 cm bồi giấy C150 cán mờ ép kim logo"),
    ("BC001", "200 hộp bánh chưng âm dương nắp chụp rời 25x25x8 cm, giấy ivory 350 in 4 màu cán mờ"),
    ("HOPQUA01", "hộp đựng hũ nhựa tròn 500ml, 300 cái"),
    ("ECO-S", "500 hộp eco nắp gập có dây giật 20x14x7 cm giấy kraft in 1 màu"),
    ("ECO-L", "300 hộp eco nắp gập có dây giật 32x22x11 kraft 1 màu"),
    ("MAILER-M", "500 hộp carton sóng E tự khóa 30x20x6 cm in 1 màu"),
    ("MAT01", "300 hộp đồ mát đông lạnh 26x18x12 cm"),
    ("GOI-S", "1000 hộp gối 9x6x2.8cm ivory 300 in 4 màu cán mờ"),
    ("GOI-L", "500 hộp gối 15x10x4 ivory 300 cán mờ"),
    ("TR001", "300 ống tròn giấy đường kính 9.5cm cao 13cm kèm tem hũ"),
    ("TT001", "200 hộp thời trang âm dương nắp rời 32x25x7 cm ivory 350 in 4 màu cán mờ"),
    ("TGT01-M", "500 túi giấy có quai ngang 32 hông 12 cao 26, ivory 250, in 4 màu cán mờ"),
    ("TGT01-L", "300 túi giấy có quai ngang 40 hông 15 cao 32 kraft 250 in 1 màu"),
    ("DAI", "2000 đai giấy quấn hộp 30x6cm couche 200 in 4 màu 1 mặt"),
    ("NHAN01", "2000 nhãn khiên decal giấy 7x7.8cm in 4 màu cán bóng bế demi"),
    ("TDL01", "5000 tem định lượng decal 3x6 cm cán bóng"),
    ("TQH01", "1000 tem quấn thân hũ decal 27x6cm cán mờ"),
    ("VCH01", "1000 vòng cổ hũ đường kính 8.8cm giấy couche 250"),
    ("PK-thiep", "300 thiệp Tết 10x15 C300 in 2 mặt cán mờ"),
    ("PK-hangtag", "1000 hangtag 5x9 giấy ivory 350 in 2 mặt cán mờ bế đục lỗ"),
    ("PK-sticker", "1000 tem decal tròn đường kính 5cm in logo cán bóng bế demi"),
    ("PK-ruybang", "5 cuộn ruy băng in logo bản 2cm"),
    # đơn thật
    ("PhuTran500", "3000 hộp lạp xưởng 16x28x4.5cm nắp gài 2 đầu, cửa sổ hoa mai dán kiếng PVC, ivory 350, in offset 4 màu, cán bóng"),
    ("KhanhBang", "50 hộp cứng nắp bật nam châm 35x25x15cm in 4 màu mặt ngoài cán mờ, mặt trong không in"),
    ("Uyen-1", "100 hộp cứng âm dương 30x25x5 cm bồi chipboard 2mm giấy C150 in 4 màu cán mờ ruột be trơn"),
    ("Uyen-2", "100 hộp cứng nắp kéo 35x12x7 cm chipboard bồi C150 in 4 màu cán mờ"),
    ("LongTuan", "90 hộp lạp xưởng 13x4x21 cm, Ivory 210, in KTS, cán mờ 1 mặt, bồi giấy Ivory 210, bế dán support cửa sổ, xỏ dây"),
    ("My-tui", "200 túi cao 30*25*8cm giấy I210gsm"),
    ("My-decal", "500 decal giấy 120x85mm cán bóng 1 mặt bế demi"),
    ("My-tam", "1600 tấm C100 ngang 30 cao 40 bế không in không cán màng"),
]

L = []
for ma, tin in CASES:
    n0 = len(GOI_AI); t0 = time.time()
    try:
        r = bot.tra_loi("sku" + ma, tin)
    except Exception as e:  # noqa: BLE001
        r = f"!!! EXCEPTION {type(e).__name__}: {e}"
    ai = "AI" if len(GOI_AI) > n0 else "quy tắc"
    gia = re.findall(r"giá bán ([\d.]+) đ/cái", r)
    loai = ("TÍNH" if gia else "HỎI LẠI" if "xin thêm" in r or "?" in r[:200] and not gia else "CHƯA CÓ GIÁ" if "chưa có bảng giá" in r else "TỪ CHỐI" if "vượt khổ" in r else "KHÁC")
    uoc = bool(re.search(r"Tạm tính|chờ My|ước tính|CHƯA gồm|em tính kết cấu|em tính kiểu", r))
    L.append(f"━━ {ma} [{ai} · {time.time()-t0:.1f}s] → {loai}{' (có ước tính)' if gia and uoc else ''}{' · ' + gia[0] + ' đ' if gia else ''}\n   TIN: {tin}\n{r}\n")
open(sys.argv[1], "w", encoding="utf-8").write("\n".join(L))
# giá bán một cái không được tăng khi số lượng tăng (quét dải rộng, không cần AI)
from goi import engine, parse_rules  # noqa: E402
tang = []
for ma, tin in CASES:
    sp, chac, _ = parse_rules.phan_tich(tin)
    if sp.get("dong_hang_khac") or parse_rules.thieu_cua(sp):
        continue
    sp["ket_cau_dac_biet"] = []
    don = engine.dung_don(sp)
    truoc = None
    for q in (50, 100, 200, 300, 500, 1000, 2000, 3000, 5000, 10000):
        r = engine.tinh(don, q)
        if r.get("vuot_kho"):
            break
        if truoc and r["gia_ban"] > truoc[1] * 1.001:
            tang.append(f"{ma}: {truoc[0]} cái {truoc[1]:,.0f} → {q} cái {r['gia_ban']:,.0f}")
        truoc = (q, r["gia_ban"])
print("Giá bán tăng theo số lượng:", tang or "không có")
co_gia = sum(1 for x in L if "giá bán" in x)
if tang and "--no-ai" in sys.argv:
    print("FAIL: đơn giá tăng theo số lượng"); sys.exit(1)
print(len(CASES), "tin;", co_gia, "ra giá;", len(GOI_AI), "lượt cần AI")
if "--no-ai" in sys.argv and co_gia < 32:
    print("FAIL: số đơn ra giá giảm còn", co_gia); sys.exit(1)

# hồi quy: kích thước vùng gia công gán đúng từ khoá gần nhất; giá My đã báo thật không lệch quá 12%
sp, _, _ = parse_rules.phan_tich("1000 hộp nắp gài 10x5x15 ivory 300 cán mờ, ép kim logo 5x3, UV 8x4, cửa sổ 6x10")
assert (sp["dai"], sp["rong"], sp["cao"]) == (10, 5, 15) and sp["ep_kim_kt"] == [5, 3] and sp["uv_kt"] == [8, 4] and sp["cua_so_kt"] == [6, 10], sp
GIA_MY = [("100 hộp cứng âm dương 30x12x7 cm bồi chipboard giấy C150 in 4 màu cán mờ", 100, 105000),
          ("100 hộp cứng nắp kéo 30x25x7 cm chipboard bồi C150 in 4 màu cán mờ", 100, 125000),
          ("90 hộp lạp xưởng 13x4x21 cm, Ivory 210, in KTS, cán mờ 1 mặt, bồi giấy Ivory 210, bế dán support cửa sổ, xỏ dây", 90, 42000),
          ("100 thiệp 8x12 cm couche 300 in 2 mặt", 100, 2500)]
for tin, sl, gia_my in GIA_MY:
    sp, _, _ = parse_rules.phan_tich(tin)
    sp["ket_cau_dac_biet"] = []
    gia = engine.tinh(engine.dung_don(sp), sl)["gia_ban_tron"]
    if abs(gia / gia_my - 1) > 0.12:
        print(f"FAIL: lệch giá My quá 12%: {tin[:50]} bot {gia:,.0f} vs My {gia_my:,}"); sys.exit(1)
print("Đối chiếu 4 giá My đã báo: trong ±12%")
