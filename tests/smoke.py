"""Kiểm tra trước khi deploy. Chạy: python tests/smoke.py
1) Bộ 31 tin end-to-end KHÔNG dùng AI (phải qua hết).
2) Một lượt gọi AI thật để chắc schema còn hợp lệ; hết hạn mức (429/402/503) chỉ cảnh báo, lỗi 400 thì fail."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
out = Path(tempfile.mkdtemp()) / "e2e.txt"
r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tests" / "e2e.py"), str(ROOT), str(out), "--no-ai"], capture_output=True, text=True, encoding="utf-8")
tail = (r.stdout.strip().splitlines() or [""])[-1]
print("E2E offline:", tail)
if r.returncode != 0:
    print(r.stdout[-1500:], r.stderr[-1500:])
    print("SMOKE FAIL"); sys.exit(1)

r2 = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tests" / "sku21.py"), str(out.parent / "sku21.txt"), "--no-ai"], capture_output=True, text=True, encoding="utf-8")
print("21 SKU + đơn thật:", (r2.stdout.strip().splitlines() or [""])[-1])
if r2.returncode != 0:
    print(r2.stdout[-800:], r2.stderr[-800:]); print("SMOKE FAIL"); sys.exit(1)

sys.path.insert(0, str(ROOT))
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
if os.environ.get("SKIP_AI"):
    print("AI: bỏ qua (SKIP_AI)"); print("SMOKE PASS"); sys.exit(0)
from goi.extract import boc_tach  # noqa: E402
try:
    d = boc_tach(None, "200 hộp nắp gài 10x5x15 ivory 300 cán mờ")
    ok = d.get("loai") == "hop_gap" and d.get("so_luong") == [200]
    print("AI:", "OK" if ok else f"đọc lệch: {d.get('loai')} {d.get('so_luong')}")
    print("SMOKE", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
except Exception as e:  # noqa: BLE001
    msg = str(e)
    if any(c in msg for c in ("429", "402", "503", "hạn mức", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "Chưa cấu hình")):
        print("AI: CẢNH BÁO hết hạn mức/quá tải, bot sẽ chạy bằng bộ quy tắc:", msg[:140]); print("SMOKE PASS"); sys.exit(0)
    print("AI: LỖI", msg[:300]); print("SMOKE FAIL"); sys.exit(1)
