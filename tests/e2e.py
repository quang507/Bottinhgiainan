"""Chạy thử bot end-to-end qua tra_loi(), không gửi Zalo.\nDùng: python tests/e2e.py <repo> <out.txt> --no-ai   (không tốn lượt AI; bỏ --no-ai để gọi AI thật)"""
import sys, time, re, base64, pathlib, tempfile, traceback
repo, out = sys.argv[1], sys.argv[2]
imgs = sys.argv[3:]
sys.path.insert(0, repo)
import os
os.chdir(repo)
import bot                                   # noqa: E402  (không chạy main)
bot.STATE_FILE = pathlib.Path(tempfile.mkdtemp()) / "state.json"
bot.state.clear()
CAN_AI = []
if "--no-ai" in sys.argv:
    def _chan(client, tin, da_biet=None, anh=None):
        CAN_AI.append(tin); raise RuntimeError("AI tắt trong test")
    bot.boc_tach = _chan
imgs = [i for i in imgs if not i.startswith("--")]

CASES = [
    # (chat, tin, ghi chú kỳ vọng)
    ("a", "xin chào", "chào → hướng dẫn"),
    ("a", "e cần báo giá hộp giấy", "thiếu → hỏi"),
    ("a", "kt 20x15x8, 500 cái nha", "ghép thông số → ra giá"),
    ("a", "giấy ivory 350, cán mờ, thêm ép kim logo 5x3cm", "cập nhật giấy + gia công"),
    ("a", "tóm lại giá bao nhiêu 1 cái", "tóm tắt 1 dòng"),
    ("a", "đổi sang 2000 cái", "tính lại theo SL"),
    ("a", "báo cả 3 mức 1000, 3000, 5000 luôn", "3 mức đúng như hỏi"),
    ("a", "reset", "xoá"),
    ("b", "e cần 300 hộp đựng trà kt 10x10x15 giấy kraft in 1 màu k cán màng", "tin lộn xộn, kraft, 1 màu"),
    ("c", "hộp 120x80x40mm 1000c ivory 350 cán bóng nắp gài", "đơn vị mm → cm"),
    ("d", "túi giấy ngang 25 hông 10 cao 32, kraft 250, in 1 màu, 1000 cái, quai dây dù 800đ/cặp", "túi có nhãn + giá quai"),
    ("e", "200 hộp cứng nắp kéo có ruy băng 20x20x8, bồi giấy C150 cán mờ ép kim logo", "hộp cứng nắp kéo +15k"),
    ("f", "100 thiệp cảm ơn 8x12 C300 in 2 mặt cán mờ 2 mặt", "thiệp KTS A4"),
    ("g", "500 tem decal giấy 5x5cm cán bóng bế demi", "decal nhỏ"),
    ("g2", "15000 tem decal giấy 6x6 cán bóng", "decal theo bảng giá My"),
    ("h", "3000 thẻ bài 5x9cm giấy I350 in 2 mặt cán mờ bế đục lỗ xỏ dây", "thẻ bài, chưa gồm dây"),
    ("i", "báo giá 5000 nhãn dệt 2x5cm 3 màu", "dòng hàng chưa có giá"),
    ("i2", "10 cuộn ruy băng satin bản 2.5cm in logo vàng", "ruy băng chưa có giá"),
    ("j", "Số lượng 100 cái hộp + thiệp: Hộp hcn 30x25x5cm, hộp dài 12x35x7cm, thiệp 8x12cm, in theo thiết kế", "nhiều sản phẩm 1 tin"),
    ("k", "1000 hộp giấy nắp gài 22.5x17x12 cm, Ivory 300 giá 18tr/tấn, in offset 4 màu 1 mặt, khổ in 65x43 1 con/tờ, sửa bài 300 tờ, bế 1401đ/cái, dán dây 1500đ/cái, ép kim 720đ/cái, dập nổi 1344đ/cái, khuôn 500k, lợi nhuận 0", "khớp Excel 9.725.487"),
    ("l", "50 hộp nắp gài 8x8x12 ivory 300 cán mờ", "lô rất nhỏ → KTS"),
    ("l", "in offset đi", "ép offset"),
    ("l", "lợi nhuận 40%", "đổi lãi"),
    ("m", "2000 hộp 60x40x30 ivory 300", "hộp quá khổ giấy"),
    ("n", "giá", "lệnh giá"),
    ("n", "chính sách", "lệnh chính sách"),
    ("n", "help", "lệnh help"),
    ("o", "bao nhiêu tiền", "không ngữ cảnh"),
    ("p", "1000 hộp gối 15x10x4 ivory 300 cán mờ, khách in lại đã có khuôn", "khuôn có sẵn"),
    ("q", "tính giúp 1600 tấm C100 ngang 30 cao 40 bế không in", "tấm phẳng không in"),
    ("r", "hộp âm dương 25x25x10 chipboard bồi C150 cán mờ, 300 cái, dập nổi âm dương logo 8x4", "hộp cứng + dập nổi âm dương"),
]

L = []
def log(s=""):
    L.append(s)

van_de = []
for chat, tin, ky_vong in CASES:
    t0 = time.time()
    try:
        r = bot.tra_loi(chat, tin)
    except Exception as e:
        r = f"!!! EXCEPTION {type(e).__name__}: {e}\n{traceback.format_exc()[-600:]}"
        van_de.append((tin, "exception"))
    dt = time.time() - t0
    log(f"━━ [{chat}] {tin}\n   (kỳ vọng: {ky_vong} · {dt:.1f}s · {len(r)} ký tự)")
    log(r); log()
    if len(r) > 2000: van_de.append((tin, f"quá dài {len(r)}"))
    for bad in ("None", "nan", "{", "Traceback"):
        if bad in r: van_de.append((tin, f"chứa '{bad}'"))
    gia = [int(x.replace(".", "")) for x in re.findall(r"giá bán ([\d.]+) đ/cái", r)]
    sl = [int(x.replace(".", "")) for x in re.findall(r"🔹 ([\d.]+) cái", r)]
    if len(gia) >= 2 and sl == sorted(sl) and any(b > a for a, b in zip(gia, gia[1:])):
        van_de.append((tin, f"đơn giá tăng theo số lượng: {gia}"))
    time.sleep(0 if '--no-ai' in sys.argv else 1.5)

for img in imgs:
    b64 = base64.b64encode(open(img, "rb").read()).decode()
    mt = "image/png" if img.lower().endswith("png") else "image/webp" if img.lower().endswith("webp") else "image/jpeg"
    for cap in ("báo giá hộp này 200 cái", ""):
        t0 = time.time()
        try:
            r = bot.tra_loi("img" + pathlib.Path(img).stem + str(len(cap)), cap, (mt, b64))
        except Exception as e:
            r = f"!!! EXCEPTION {type(e).__name__}: {e}"; van_de.append((img, "exception"))
        log(f"━━ [ảnh {pathlib.Path(img).name}] caption={cap!r} ({time.time()-t0:.1f}s · {len(r)} ký tự)"); log(r); log()
        time.sleep(1.5)

log("════ VẤN ĐỀ TỰ PHÁT HIỆN ════")
for v in van_de: log(f"- {v[1]} ← {v[0][:70]}")
log("════ TIN PHẢI NHỜ AI (bộ quy tắc không đủ chắc) ════")
for c in CAN_AI: log("- " + c[:90])
log(f"Tổng: {len(CASES)} tin, {len(van_de)} vấn đề tự phát hiện, {len(CAN_AI)} tin cần AI")
open(out, "w", encoding="utf-8").write("\n".join(L))
print(L[-1])
# các kỳ vọng cứng
txt = "\n".join(L)
assert "vốn 9.725" in txt, "bài Excel không còn khớp 9.725"
assert "vượt khổ giấy lớn nhất" in txt, "hộp quá khổ phải bị từ chối"
assert "Hộp cứng nắp kéo" in txt, "hộp cứng nắp kéo có ruy băng bị hiểu sai"
assert "Nhãn dệt: xưởng có làm" in txt and "Dây ruy băng in: xưởng có làm" in txt
sys.exit(1 if van_de else 0)
