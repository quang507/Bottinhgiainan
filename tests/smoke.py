"""Kiểm tra nhanh trước khi deploy: engine khớp Excel + 4 tin thật qua Claude. Chạy: python tests/smoke.py"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import anthropic  # noqa: E402
from goi import engine  # noqa: E402
from goi.extract import boc_tach  # noqa: E402

TIN = [
    ("tính giá hộp 13*4*21", "hỏi lại"),
    ("100 hộp âm dương 30x25x5 cm, chipboard 2mm bồi giấy C150, in 4 màu, cán mờ, ruột màu be", "offset"),
    ("200 túi cao 30*25*8cm giấy I210gsm", "túi"),
    ("1000 hộp giấy nắp gài 22.5x17x12 cm, Ivory 300 giá 18tr/tấn, in offset 4 màu 1 mặt, khổ in 65x43 1 con/tờ, sửa bài 300 tờ, "
     "bế 1401đ/cái, dán dây 1500đ/cái, ép kim 720đ/cái, dập nổi 1344đ/cái, khuôn 500k, lợi nhuận 0", "excel 9.725.487"),
]

c = anthropic.Anthropic()
loi = 0
for tin, ky_vong in TIN:
    d = None
    try:
        d = boc_tach(c, tin)
        thieu = d["thieu"] or [k for k in ("loai", "dai", "rong") if not d.get(k)] or ([] if d["so_luong"] else ["số lượng"])
        if thieu:
            print(f"OK  hỏi lại ({ky_vong}): {d['cau_hoi'][:80]}")
            continue
        don = engine.dung_don(d)
        kq = [engine.tinh(don, q) for q in (d["so_luong"] or [100])]
        msg = engine.soan_tin(d, don, kq)
        assert len(msg) <= 2000, "tin quá 2000 ký tự"
        if "excel" in ky_vong:
            assert abs(kq[0]["chi_phi"] - 9725487.45) < 1, f"lệch Excel: {kq[0]['chi_phi']}"
        print(f"OK  {ky_vong}: {don.ten} → {kq[0]['gia_ban_tron']:,} đ/cái ({len(msg)} ký tự)")
    except Exception as e:  # noqa: BLE001
        loi += 1
        import traceback
        print(f"FAIL {ky_vong}: {type(e).__name__}: {str(e)[:300]}")
        print("     spec:", d)
        traceback.print_exc()
print("SMOKE", "FAIL" if loi else "PASS")
sys.exit(1 if loi else 0)
