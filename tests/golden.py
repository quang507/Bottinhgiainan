"""Chụp / so kết quả engine trên lưới đơn mẫu ngẫu nhiên (seed cố định) để refactor không đổi một con số nào.
  python tests/golden.py save <file.json>     chụp
  python tests/golden.py check <file.json>    so với bản đã chụp"""
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from goi import engine as e  # noqa: E402

rnd = random.Random(20261012)
KT = {
    "hop_gap": [(20, 15, 8), (10, 5, 15), (13, 4, 21), (30, 25, 5), (35, 12, 7), (8, 8, 12), (60, 40, 30), (22.5, 17, 12), (15, 10, 4), (45, 35, 10), (12, 8, 4)],
    "hop_cung": [(30, 12, 7), (30, 25, 7), (20, 20, 8), (35, 25, 15), (25, 25, 10), (15, 10, 5), (60, 50, 20)],
    "tui_giay": [(25, 10, 32), (20, 8, 15), (32, 12, 26), (40, 15, 50), (25, 8, 30), (15, 6, 20)],
    "thiep": [(8, 12, None), (10, 15, None), (5, 9, None), (30, 40, None), (30, 6, None), (8.8, 8.8, None), (21, 29.7, None)],
    "tem_decal": [(5, 5, None), (12, 8.5, None), (6, 6, None), (3, 6, None), (27, 6, None), (10, 15, None)],
}
KIEU = {"hop_gap": ["", "nắp gài", "âm dương", "bao diêm", "đáy khóa", "hộp gối", "nắp rời"], "hop_cung": ["âm dương", "nắp kéo", "nam châm", ""],
        "tui_giay": [""], "thiep": ["", "thẻ bài"], "tem_decal": [""]}
TEN = {"thiep": ["", "Thẻ bài", "Tấm giấy", "Đai giấy", "Vòng cổ hũ", "Thiệp cảm ơn"], "hop_gap": ["", "Hộp lạp xưởng", "Hộp nắp gài"], "hop_cung": ["", "Hộp cứng nắp kéo"],
       "tui_giay": ["", "Túi giấy"], "tem_decal": ["", "Tem decal tròn"]}
GIAY = [(None, None), ("Ivory", 300), ("Ivory", 250), ("Ivory", 350), ("Ivory", 210), ("Couche", 150), ("Couche", 300), ("Couche", 100), ("Kraft", 250), ("Bristol", 250), ("Duplex", 300)]
GC = ["can_mo", "can_bong", "ep_kim", "dap_noi", "uv_dinh_vi", "be", "dan_may", "dan_tay", "boi_giay", "cua_so", "xo_day"]
SLS = [30, 50, 90, 100, 200, 300, 500, 1000, 1600, 3000, 5000, 15000, 20000]


def spec_ngau_nhien():
    loai = rnd.choice(list(KT))
    D, R, C = rnd.choice(KT[loai])
    giay, gsm = rnd.choice(GIAY)
    s = {"san_pham": rnd.choice(TEN[loai]), "loai": loai, "kieu_hop": rnd.choice(KIEU[loai]) or None, "dai": D, "rong": R, "cao": C,
         "so_luong": [], "giay": "Decal" if loai == "tem_decal" else giay, "dinh_luong": gsm,
         "so_mau": rnd.choice([None, None, 4, 4, 1, 0, 2]), "so_mat": rnd.choice([None, None, 1, 2]),
         "gia_cong": rnd.sample(GC, rnd.choice([0, 0, 1, 1, 2, 3, 5])), "thieu": [], "cau_hoi": "",
         "gia_giay_tr_tan": rnd.choice([None] * 6 + [18, 21]), "tu_sua_bai": rnd.choice([None] * 6 + [300, 50]),
         "kho_giay": None, "so_con_to": None, "pct_loi_nhuan": rnd.choice([None] * 5 + [0, 0.4]),
         "khuon_be_nghin": rnd.choice([None] * 6 + [500, 0]), "khong_proof": rnd.random() < 0.1, "khuon_co_san": rnd.random() < 0.1,
         "gia_cong_tuy_chinh": [], "ep_kim_kt": rnd.choice([None, None, [5, 3], [20, 12]]), "dap_noi_kt": rnd.choice([None, None, [8, 4]]),
         "dap_noi_am_duong": rnd.random() < 0.2, "so_mep_dan": rnd.choice([None, None, 1, 3]), "tui_2_manh": rnd.random() < 0.15,
         "gia_quai": rnd.choice([None, None, 800]), "can_mang_2_mat": rnd.random() < 0.2,
         "kieu_in_2_mat": rnd.choice([None] * 5 + ["AB", "tu_tro", "tro_nhip"]), "in_kts": rnd.choice([None] * 4 + [True, False]),
         "ket_cau_dac_biet": rnd.choice([[]] * 4 + [["cửa sổ"], ["quai xách liền thân", "khay/ngăn bên trong"]])}
    if rnd.random() < 0.1:
        s["kho_giay"], s["so_con_to"] = rnd.choice(["65x43", "65x86", "79x109"]), rnd.choice([1, 2, 4])
    if rnd.random() < 0.1:
        s["gia_cong_tuy_chinh"] = rnd.sample([{"ten": "Bế", "gia_moi_cai": 1401.0}, {"ten": "Dán dây", "gia_moi_cai": 1500.0}, {"ten": "Ép kim", "gia_moi_cai": 720.0}, {"ten": "Dập nổi", "gia_moi_cai": 1344.0}], 2)
    return s


def chay():
    out = []
    for i in range(1400):
        s = spec_ngau_nhien()
        sls = rnd.sample(SLS, 3)
        rec = {"i": i, "spec": json.dumps(s, ensure_ascii=False, sort_keys=True)}
        try:
            don = e.dung_don(json.loads(rec["spec"]))
            kq = [e.tinh(don, q) for q in sorted(sls)]
            rec["kq"] = [json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, ensure_ascii=False, sort_keys=True, default=str) for r in kq]
            rec["tin"] = e.thong_bao_vuot_kho(json.loads(rec["spec"]), don, kq[0]) if kq[0].get("vuot_kho") else e.soan_tin(json.loads(rec["spec"]), don, kq)
            rec["khach"] = "" if kq[0].get("vuot_kho") else e.soan_tin_khach(json.loads(rec["spec"]), don, kq)
            rec["ep"] = [json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in e.tinh(don, sorted(sls)[0], kts=m).items()}, ensure_ascii=False, sort_keys=True, default=str) for m in (True, False)]
        except Exception as ex:  # noqa: BLE001
            rec["loi"] = f"{type(ex).__name__}: {ex}"
        out.append(rec)
    return out


if __name__ == "__main__":
    che_do, f = sys.argv[1], Path(sys.argv[2])
    kq = chay()
    if che_do == "save":
        f.write_text(json.dumps(kq, ensure_ascii=False), encoding="utf-8")
        print("đã chụp", len(kq), "đơn;", sum(1 for r in kq if "loi" in r), "đơn lỗi;", sum(1 for r in kq if "vượt khổ" in r.get("tin", "")), "vượt khổ")
    else:
        cu = json.loads(f.read_text(encoding="utf-8"))
        lech = [(a["i"], k) for a, b in zip(cu, kq) for k in ("kq", "tin", "khach", "ep", "loi") if a.get(k) != b.get(k)]
        print("so", len(kq), "đơn:", "GIỐNG HỆT" if not lech and len(cu) == len(kq) else f"LỆCH {len(lech)} chỗ, ví dụ {lech[:5]}")
        if lech:
            i, k = lech[0]
            a, b = cu[i].get(k), kq[i].get(k)
            print("spec:", cu[i]["spec"][:400])
            print("CŨ :", (a if isinstance(a, str) else json.dumps(a, ensure_ascii=False))[:900])
            print("MỚI:", (b if isinstance(b, str) else json.dumps(b, ensure_ascii=False))[:900])
            sys.exit(1)
