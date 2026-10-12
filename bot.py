"""Zalo Bot báo giá GÓI - long-polling getUpdates. Chạy: python bot.py (đọc .env)."""
import json
import logging
import os
import sys
import time
from pathlib import Path

import anthropic
import httpx

sys.path.insert(0, str(Path(__file__).parent))
from goi import engine                      # noqa: E402
from goi.extract import boc_tach            # noqa: E402

ROOT = Path(__file__).parent
for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if (ROOT / ".env").exists() else []:
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

TOKEN = os.environ["ZALO_BOT_TOKEN"]
BASE = f"https://bot-api.zaloplatforms.com/bot{TOKEN}"
STATE_FILE = ROOT / "state.json"
CHO_HOI_LAI = {"loai", "dai", "rong", "so_luong"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("goi-bot")
logging.getLogger("httpx").setLevel(logging.WARNING)   # không ghi URL chứa token vào log
client = anthropic.Anthropic()
http = httpx.Client(timeout=60)

state: dict = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
da_xu_ly: list = []


def luu_state():
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


def api(method, **params):
    r = http.post(f"{BASE}/{method}", json=params)
    data = r.json()
    if not data.get("ok") and data.get("error_code") != 408:   # 408 = hết thời gian chờ long-polling, bình thường
        log.warning("API %s lỗi: %s", method, data)
    return data


def gui(chat_id, text):
    for i in range(0, len(text), 1990):
        api("sendMessage", chat_id=chat_id, text=text[i:i + 1990])


def bac_so_luong(sl: list) -> list:
    mac_dinh = engine.P["bac_so_luong_mac_dinh"]
    out = list(dict.fromkeys([q for q in sl if q > 0] + mac_dinh))
    return sorted(out)[:4] if len(sl) != 1 else [sl[0]] + [q for q in mac_dinh if q > sl[0]][:2]


def tra_loi(chat_id: str, text: str) -> str:
    t = text.strip()
    lower = t.lower()
    if lower in ("reset", "đơn mới", "don moi", "/reset"):
        state.pop(chat_id, None); luu_state()
        return "Đã xoá thông số cũ. Gửi yêu cầu mới (loại hộp, kích thước, số lượng, giấy, gia công)."
    if lower in ("giá", "gia", "/gia", "bảng giá"):
        p = engine.P
        giay = ", ".join(f"{k} {v}tr/tấn" for k, v in p["giay_tr_tan"].items())
        return (f"Bảng giá đang dùng:\n• Giấy: {giay}\n• Chipboard {p['chipboard_gia_to_65x86']:,} đ/tờ 65×86\n"
                f"• Kẽm {p['gia_kem']:,} đ/bản, công in tối thiểu {p['cong_in_toi_thieu_1_kem']:,} đ/kẽm, khuôn bế {p['khuon_be']:,} đ\n"
                f"• Vận chuyển {int(p['pct_van_chuyen']*100)}%, lợi nhuận {int(p['pct_loi_nhuan']*100)}%").replace(",", ".")
    if lower in ("chính sách", "chinh sach", "điều khoản", "/chinhsach"):
        return "
".join("📎 " + d for d in engine.P.get("chinh_sach", {}).get("dong", []))
    if lower in ("help", "/help", "hướng dẫn", "?"):
        return ("Gửi yêu cầu một tin, ví dụ:\n'100 hộp âm dương 30x25x5, Ivory 300, in 4 màu, cán mờ, ép kim logo'\n"
                "Bot sẽ hỏi lại nếu thiếu, rồi báo giá 3 bậc số lượng. Gõ 'chính sách' xem điều khoản, 'reset' làm đơn mới, 'giá' xem bảng giá.")

    da_biet = state.get(chat_id, {}).get("spec")
    s = boc_tach(client, t, da_biet)
    state[chat_id] = {"spec": s, "luc": time.time()}
    luu_state()
    thieu = [x for x in s["thieu"]] or [k for k in ("loai", "dai", "rong") if not s.get(k)] or ([] if s["so_luong"] else ["số lượng"])
    if s["loai"] in ("hop_gap", "hop_cung", "tui_giay") and not s.get("cao"):
        thieu.append("chiều cao")
    if thieu:
        return s["cau_hoi"] or ("Cho em xin thêm: " + ", ".join(thieu) + " ạ.")
    don = engine.dung_don(s)
    ket_qua = [engine.tinh(don, q) for q in bac_so_luong(s["so_luong"])]
    return engine.soan_tin(s, don, ket_qua)


def xu_ly(update: dict):
    msg = update.get("message") or {}
    if update.get("event_name") not in (None, "message.text.received"):
        return
    mid = msg.get("message_id")
    if not msg.get("text") or mid in da_xu_ly or (msg.get("from") or {}).get("is_bot"):
        return
    da_xu_ly.append(mid)
    del da_xu_ly[:-500]
    chat_id = msg["chat"]["id"]
    text = msg["text"]
    log.info("[%s] %s: %s", chat_id, (msg.get("from") or {}).get("display_name"), text[:120])
    try:
        reply = tra_loi(chat_id, text)
    except Exception as e:  # noqa: BLE001
        log.exception("Lỗi xử lý tin: %s", text[:200])
        reply = f"Bot gặp lỗi khi tính ({type(e).__name__}: {str(e)[:150]}). Anh Quang sẽ sửa, gửi lại sau hoặc gõ 'reset' giúp em."
    gui(chat_id, reply)


def main():
    me = api("getMe")
    log.info("Bot: %s", me.get("result"))
    while True:
        try:
            data = api("getUpdates", timeout=30)
            res = data.get("result")
            items = res if isinstance(res, list) else ([res] if res else [])
            for u in items:
                xu_ly(u)
        except KeyboardInterrupt:
            break
        except Exception:  # noqa: BLE001
            log.exception("Lỗi vòng lặp, thử lại sau 5s")
            time.sleep(5)


if __name__ == "__main__":
    main()
