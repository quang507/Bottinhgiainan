"""Bình bài: một tờ giấy W×H xếp được bao nhiêu con w×h."""
import math

from .bang_gia import P

CAT_TAI = (0.5, 1.0, 1.5)   # các mức bớt tai dán (cm) được phép thử


def _luoi_va_dai_du(W, H, w, h):
    """Lưới chính w×h, phần dư bên phải hoặc bên dưới xếp thêm con xoay 90°."""
    cot, hang = math.floor(W / w), math.floor(H / h)
    if cot == 0 or hang == 0:
        return 0
    phai = math.floor((W - cot * w) / h) * math.floor(H / w)
    duoi = math.floor(W / h) * math.floor((H - hang * h) / w)
    return cot * hang + max(phai, duoi)


def ups(W, H, w, h, bu_xen=None, le=None):
    """Số con/tờ: trừ lề kẹp nhíp một cạnh, cộng bù xén quanh mỗi con, thử cả hai chiều tờ và hai chiều con."""
    if not w or not h:
        return 0
    cau_hinh = P.get("binh_bai", {})
    le = cau_hinh.get("le_nhip_cm", 0) if le is None else le
    bu_xen = cau_hinh.get("bu_xen_cm", {}).get("hop_gap", 0) if bu_xen is None else bu_xen
    W2, H2, w2, h2 = W, H - le, w + bu_xen, h + bu_xen
    return max(_luoi_va_dai_du(W2, H2, w2, h2), _luoi_va_dai_du(W2, H2, h2, w2),
               _luoi_va_dai_du(H2, W2, w2, h2), _luoi_va_dai_du(H2, W2, h2, w2))


def ups_bot_tai(W, H, w, h, cho_phep=True, le=None):
    """Trả về (số con, cm đã bớt). Chỉ bớt tai dán khi nhờ đó xếp thêm được con."""
    tot = (ups(W, H, w, h, le=le), 0)
    if not cho_phep:
        return tot
    for t in CAT_TAI:
        u = max(ups(W, H, w - t, h, le=le), ups(W, H, w, h - t, le=le), ups(W, H, w - t, h - t, le=le))
        if u > tot[0]:
            tot = (u, t)
    return tot


def lot_kho_giay(w, h) -> bool:
    """Khổ trải w×h có lọt ít nhất một khổ giấy công nghiệp không."""
    return any(ups(W, H, w, h) for W, H in P["kho_giay"])
