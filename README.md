# Tính giá GÓI

Công cụ báo giá in offset / bao bì theo đúng công thức file **Báo giá My.xlsx** (xưởng in NAHT).

- `index.html` – trang tính giá, chạy offline, không cần server. Mở trực tiếp bằng trình duyệt.
  Bản online: https://claude.ai/artifact/3ye8uhcsRhLdE7KvYbWFA4
- `baogia.py` – engine Python cùng công thức, dùng cho Zalo bot / API. Chạy `python baogia.py` để đối chiếu với Excel.

## Công thức (theo ô Excel)

| Khoản | Công thức |
| --- | --- |
| Giá tờ | Dài × Rộng (cm) × gsm × giá/gam ÷ 10.000 (giá/gam = giá tấn ÷ 1.000.000) |
| Số tờ | SL ÷ số con/tờ × 1,03 + tờ sửa bài |
| Công in | < 3.000 lượt: số tay × số màu × 300.000; từ 3.000: số tờ × màu × mặt × đơn giá lượt (130/120/110/90/80/60-70) |
| CTP | số màu × số tay × 110.000 |
| Đơn giá bán | (Chi phí + HH + Lợi nhuận) ÷ (1 − HH KH − HH KH × thuế) ÷ SL, lợi nhuận tính trên tổng chi phí |

Kiểm chứng: preset "Nạp mẫu Excel" (Đơn SLL, 1.000 hộp Ivory 300) phải ra **9.725,49 đ/cái**.

## Chưa có trong Excel
Hộp cứng bồi chipboard: chipboard đ/tờ, công bồi tay đ/hộp, in KTS lô nhỏ – chờ My chốt.

## Kế hoạch
Zalo OA bot: webhook → Claude bóc tách quy cách (JSON) → `baogia.py` tính → trả 3 bậc số lượng hoặc hỏi lại thông số thiếu.
