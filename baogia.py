# Tái hiện công thức sheet "Đơn SLL" / "Đơn số ít" trong "Báo giá My.xlsx"
def tinh(sl, trai_d, trai_r, trai_day, so_tay, kt_d, kt_r, so_con, so_mau, so_mat, sua_bai, he_so,
         loai_giay, dinh_luong, gia_gram, gia_cong, khuon_k, proof_ti_le, ctp,
         pct_ql=0, pct_vc=0.05, pct_khac=0, pct_ln=0, pct_hh_nvkd=0, pct_thue_nvkd=0, pct_hh_kh=0, pct_thue_kh=0,
         gia_kem=110000, gia_in_1_kem=300000, gia_met=3500, sheet='SLL'):
    gia_to = kt_d*kt_r*dinh_luong*gia_gram/10000 + (kt_d*kt_r*gia_met/10000 if loai_giay=='Met' else 0)
    so_to = sl/so_con*1.03 + sua_bai                     # B53
    so_to_tay = so_to*so_tay                             # B54
    tien_giay = so_to_tay*gia_to                         # B68
    # B74 công in theo bậc
    luot = so_to*so_mat
    if luot < 3000: cong_in = so_tay*so_mau*gia_in_1_kem*he_so
    else:
        rate = 130 if luot<4000 else 120 if luot<5000 else 110 if luot<6000 else 90 if luot<10000 else 80 if luot<15000 else (60 if sheet=='SLL' else 70)
        cong_in = so_tay*so_to*rate*so_mau*so_mat*he_so
    # B66 proof, B67 CTP
    proof = 0
    if proof_ti_le:
        p = trai_d*trai_r*trai_day*proof_ti_le*100
        proof = max(150000, p) if sheet=='SLL' else p
    tien_ctp = so_mau*so_tay*gia_kem if ctp=='ctp' else 0
    gc = {k: sl*v for k,v in gia_cong.items()}          # B82..B85
    khuon = khuon_k*1000                                 # B86
    vat_tu = tien_giay + cong_in + sum(gc.values()) + khuon + tien_ctp + proof   # B87
    ql = vat_tu*pct_ql; vc = vat_tu*pct_vc; khac = vat_tu*pct_khac
    chi_phi = vat_tu+ql+vc+khac                          # B91 / B46
    loi_nhuan = vat_tu*pct_ln                            # B92 (tính trên vật tư!)  B51 = B46*E34 (tính trên chi phí)
    ln_B51 = chi_phi*pct_ln
    don_gia_cp = chi_phi/sl
    hh_nvkd = don_gia_cp*sl*pct_hh_nvkd; thue_nvkd = hh_nvkd*pct_thue_nvkd
    don_gia_ban = (chi_phi+hh_nvkd+thue_nvkd+ln_B51)/(1-pct_hh_kh-pct_hh_kh*pct_thue_kh)/sl   # B41
    return dict(gia_to=gia_to, so_to=so_to, tien_giay=tien_giay, cong_in=cong_in, proof=proof, ctp=tien_ctp,
                gia_cong=gc, khuon=khuon, vat_tu=vat_tu, van_chuyen=vc, chi_phi=chi_phi,
                loi_nhuan_B92=loi_nhuan, loi_nhuan_B51=ln_B51, don_gia_ban=don_gia_ban, thanh_tien=don_gia_ban*sl)

if __name__=='__main__':
    # Sheet Đơn SLL – kỳ vọng: giá tờ 1509.3, số tờ 1330, giấy 2,007,369, in 1,200,000, proof 150,000, ctp 440,000, vật tư 9,262,369, VC 463,118.45, đơn giá 9,725.48745
    r = tinh(sl=1000, trai_d=26, trai_r=17, trai_day=8, so_tay=1, kt_d=65, kt_r=43, so_con=1, so_mau=4, so_mat=1, sua_bai=300, he_so=1,
             loai_giay='Ivory', dinh_luong=300, gia_gram=18,
             gia_cong={'Bế':1401,'Dán dây':1500,'Ép kim':720,'Dập nổi':1344}, khuon_k=500, proof_ti_le=0.1, ctp='ctp', pct_ln=0, sheet='SLL')
    for k,v in r.items(): print(f'{k:16}', v)
    print()
    # Sheet Đơn số ít – kỳ vọng: số tờ 409, giấy 617,303.7, in 600,000, bế 225,000, màng 369,000, dán 90,000, vật tư 2,401,303.7, VC 120,065.185, đơn giá 11,598.296871, LN(B51) 958,120.1763
    r = tinh(sl=300, trai_d=0, trai_r=20, trai_day=0, so_tay=1, kt_d=43, kt_r=65, so_con=1, so_mau=2, so_mat=1, sua_bai=100, he_so=1,
             loai_giay='Kraft', dinh_luong=300, gia_gram=18,
             gia_cong={'Bế':750,'Cán mờ':1230,'Dán':300}, khuon_k=500, proof_ti_le=0.1, ctp='ctp', pct_ln=0.38, sheet='it')
    for k,v in r.items(): print(f'{k:16}', v)
