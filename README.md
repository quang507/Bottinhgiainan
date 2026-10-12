# Bot tính giá in ấn GÓI

Zalo Bot báo giá bao bì theo đúng công thức **Báo giá My.xlsx** (xưởng in NAHT).
Nhắn yêu cầu vào bot (hoặc @tag bot trong nhóm) → bot bóc tách quy cách, hỏi lại nếu thiếu, rồi báo giá 3 bậc số lượng.

## Cấu trúc
- `bot.py` – vòng lặp Zalo Bot API (`getUpdates` / `sendMessage`), nhớ thông số theo từng chat trong `state.json`.
- `goi/parse_rules.py` – đọc tin nhắn bằng bộ quy tắc (không cần AI). Tin rõ ràng đi đường này, trả lời tức thì.
- `goi/extract.py` – AI bóc tách (Gemini trước, Claude Haiku dự phòng) cho tin lộn xộn, nhiều sản phẩm, hoặc có ảnh. AI chỉ bóc tách, không tính tiền.
- `goi/engine.py` – cửa vào của phần tính giá, gom 5 module:
  - `bang_gia.py` bảng giá (`prices.json`) và đặc tính từng loại sản phẩm
  - `binh_bai.py` một tờ giấy xếp được mấy con
  - `san_pham.py` dựng đơn hàng từ thông số, mỗi loại sản phẩm một hàm
  - `tinh_gia.py` tính giá vốn và giá bán theo 6 bước
  - `soan_tin.py` soạn tin: bản nội bộ và bản gửi khách
- `goi/prices.json` – bảng giá xưởng, mỗi mục có ghi chú nguồn. Sửa file này rồi `systemctl restart goi-bot`.
- `tests/` – `smoke.py` chạy trước mỗi lần deploy: `e2e.py` (31 tin hội thoại), `sku21.py` (21 SKU GÓI + đơn thật, kiểm giá bán không tăng theo số lượng và không lệch quá 12% so với 4 giá My đã báo), đối chiếu Excel. `golden.py` chụp/so 1.400 đơn mẫu khi cần sửa cấu trúc code mà không đổi kết quả.
- `deploy.sh` – kiểm tra cú pháp, chạy test, đẩy lên VPS, commit.
- `index.html` – trang tính giá thủ công theo đúng Excel của My.

## Lệnh trong chat
`reset` – đơn mới · `giá` – xem bảng giá đang dùng · `help` – hướng dẫn.

## Chạy trên VPS (Ubuntu)
```bash
apt install -y python3-venv git
mkdir -p /opt/goi-bot && cd /opt/goi-bot   # copy code vào đây
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env && nano .env            # điền token
cp deploy/goi-bot.service /etc/systemd/system/ && systemctl daemon-reload
systemctl enable --now goi-bot && journalctl -u goi-bot -f
```

## Công thức (theo ô Excel)
| Khoản | Công thức |
| --- | --- |
| Giá tờ | Dài × Rộng (cm) × gsm × giá/gam ÷ 10.000 (giá/gam = giá tấn ÷ 1.000.000) |
| Số tờ | SL ÷ số con/tờ × 1,03 + tờ sửa bài; số con/tờ xếp trên 65×43 / 65×86 / 79×109 |
| Công in | < 3.000 lượt: số màu × 300.000; từ 3.000: số tờ × màu × mặt × đơn giá lượt (130/120/110/90/80/60) |
| CTP | số màu × số mặt × 110.000 |
| Giá bán | (vật tư × 1,05 vận chuyển) × (1 + lợi nhuận) ÷ SL, làm tròn lên 1.000 |

Các quy tắc My bổ sung ngoài Excel (hộp cứng, in nhanh, gia công, lãi theo loại) nằm trong `goi/prices.json`, mỗi mục có `_ghi_chu` nguồn. Khoản nào My chưa chốt thì tin trả lời ghi "Tạm tính" hoặc "chờ My".
