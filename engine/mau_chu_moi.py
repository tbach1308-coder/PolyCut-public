#!/usr/bin/env python3
"""Bộ mẫu chữ mới (POLY Cut r36, 11/11/2026; anh duyệt 11/11 ~11:45 "làm cả 3 bộ, cho anh chọn trong app").

ve_chu.py gọi khi kế hoạch có khoá kieu.bo_mau (hoặc 1 chữ có kiểu riêng {"bo": id} / mẫu có sẵn mang "bo"): KHÔNG có khoá = ve_chu
vẽ y hệt cũ (không gọi tới file này). Mỗi hàm trả (ảnh RGBA 1080×1920, hộp) như ve_chu; hộp = vùng đục (alpha > 128, bỏ bóng mờ).
Dữ liệu bộ: <engine>/mau-chu/<id>.json (cùng dạng sẽ để trong kho effect `mau-chu/<id>.json` sau này) — chỉ tham số (cỡ, màu theo TÊN
trong bảng màu Poly, độ bo, viền, đuôi bong bóng, kiểu phụ đề); CÁCH vẽ theo họ ("ho"): khoi (khối lục bảo, viền trắng, bong bóng) ·
but_da (không khối, chữ trắng bóng mềm, bút dạ vàng chữ xanh, căn trái x 90) · kinh (tấm kính lục bảo trong / đục).
Kính: che_do "mo" (dựng máy chủ: PNG phủ lục bảo trong ~58%, dung_may_chu làm mờ cảnh dưới thẻ bằng gblur theo mặt nạ = alpha lớp;
khung xem: CSS backdrop-filter) | "duc" (Premiere: phủ đục 84%, không làm mờ). render() đặt theo tl.duong.
Kiểu phụ đề (phu_de[].kieu): cum_vien · cum_the (nen xanh | kinh) · tu_khoa (2 tầng) · cum_trang · cum_but_da · cum_noi ·
cau_o (cả câu, ô vàng sau từ đang đọc) · cau_gach (gạch vàng) · cau_kinh. Loại "cau" vẽ 1 PNG mỗi từ (từ đang đọc khác nhau).
Vùng an toàn TikTok: chữ trong x 90–900, y 220–1380; khối rộng dịch trái vừa đủ (cx_cho). Nguyên mẫu + ảnh duyệt: dev/mau_moi.py.
"""
import base64
import glob
import hashlib
import json
import os
import re
import unicodedata

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
MAU_DIR = os.path.join(HERE, "mau-chu")
KIEU_DUNG_DIR = os.path.join(HERE, "kieu-dung")
V = None   # module ve_chu đang chạy (ve_chu gọi dat_vc lúc nạp: chạy ve_chu.py trực tiếp thì là __main__, không nạp bản thứ 2)

W, H = 1080, 1920
SS = 4
CX = 495                 # tâm ngang vùng an toàn (x 90–900)
LE_TRAI, LE_PHAI = 90, 900
Y_TREN, Y_DUOI = 220, 1380
Y_PD = 1290              # chân chữ phụ đề (dòng cuối) mặc định của bộ mới; hộp nền vẫn ≤ 1380
KINH = {"che_do": "mo"}  # mo | duc (render đặt theo đường dựng)
KINH_MAU = (5, 56, 42)   # lục bảo kính = trộn XANH / XANH_TOI 50% (dat_vc tính lại theo màu đang dùng)
MAU_CHU = ("vang", "trang", "xanh", "xanh_toi", "den", "xanh_sang")


def dat_vc(vc):
    """ve_chu gọi lúc nạp: dùng chung bảng màu, font, in_hoa, tên máy, CHU_NHO của đúng module đang chạy."""
    global V, KINH_MAU
    V = vc
    KINH_MAU = V._tron(V.XANH[:3], V.XANH_TOI[:3], 0.50)


def _doc_bo():
    out = {}
    for f in sorted(glob.glob(os.path.join(MAU_DIR, "*.json"))):
        try:
            with open(f, encoding="utf-8") as fo:
                b = json.load(fo)
        except (OSError, ValueError):
            continue
        if isinstance(b, dict) and b.get("id") and b.get("ho") in ("khoi", "but_da", "kinh") and isinstance(b.get("phu_de"), list):
            out[b["id"]] = b
    return dict(sorted(out.items(), key=lambda x: (x[1].get("thu_tu") or 99, x[0])))


BO = _doc_bo()


def _phien():
    h = hashlib.md5()
    for f in [os.path.abspath(__file__)] + sorted(glob.glob(os.path.join(MAU_DIR, "*.json"))):
        try:
            st = os.stat(f)
            h.update(("%s|%d|%d" % (os.path.basename(f), st.st_size, int(st.st_mtime))).encode())
        except OSError:
            pass
    return h.hexdigest()[:10]


PHIEN = _phien()   # đổi file bộ / file này -> khoá lớp nhớ xem trước đổi (ve_chu truyền _v=PHIEN)


def _ho(bo):
    return BO[bo]["ho"]


def bo_cua(k):
    """kieu (dict) -> id bộ hợp lệ | None."""
    b = (k or {}).get("bo_mau") if isinstance(k, dict) else None
    return b if isinstance(b, str) and b in BO else None


def pd_kieu(bo, kieu_pd=None, phu_de=None):
    """Kiểu phụ đề dùng: kieu_phu_de hợp lệ của bộ (khớp loại với kieu.phu_de nếu có) | kiểu đầu tiên của bộ đúng loại."""
    ds = BO[bo]["phu_de"]
    loai = "cau" if phu_de == "ca_cau" else ("cum" if phu_de == "cum_ngan" else None)
    st = next((p for p in ds if p.get("id") == kieu_pd), None)
    if st and (loai is None or st.get("loai") == loai):
        return st
    return next((p for p in ds if p.get("loai") == loai), None) or ds[0]


def la_kinh(bo, loai, pd=None):
    """Lớp này có tấm kính (cần làm mờ cảnh phía sau khi dựng máy chủ)?"""
    if not bo or bo not in BO or _ho(bo) != "kinh":
        return False
    if loai == "phu_de":
        return bool(pd) and (pd.get("nen") == "kinh" or pd.get("kieu") == "cau_kinh")
    return loai in ("hook", "nhan", "gia", "ket", "brand", "tieu_de")


def mo_cua(bo):
    return float(((BO.get(bo) or {}).get("kinh") or {}).get("mo") or 26)


def bao_hoa(bo):
    return float(((BO.get(bo) or {}).get("kinh") or {}).get("bao_hoa") or 0.35)


# ---------------------------------------------------------------- màu, font
def M(ten, a=255):
    c = {"xanh": V.XANH, "xanh_toi": V.XANH_TOI, "xanh_sang": V.XANH_SANG, "vang": V.VANG, "trang": V.TRANG,
         "den": V.DEN}[ten if ten in MAU_CHU else "trang"]
    return tuple(c[:3]) + (int(a),)


HO = {
    "be_vietnam": {"Black": ("BeVietnamPro-Black.ttf", None), "ExtraBold": ("BeVietnamPro-ExtraBold.ttf", None),
                   "Bold": ("BeVietnamPro-Bold.ttf", None)},
    "archivo_hep": {"Black": ("Archivo[wdth,wght].ttf", (900, 62)), "ExtraBold": ("Archivo[wdth,wght].ttf", (800, 62)),
                    "Bold": ("Archivo[wdth,wght].ttf", (700, 62))},
}
_FC = {}


def _thu_muc_font(f):
    for d in (getattr(V, "FONT_DIR", None), os.path.join(HERE, "fonts")):
        if d and os.path.isfile(os.path.join(d, f)):
            return d
    return os.path.join(HERE, "fonts")


def F(dam, co, ho="be_vietnam"):
    f, truc = HO[ho][dam]
    co = max(8, int(round(co)))
    d = _thu_muc_font(f)
    k = (d, f, truc, co)
    if k not in _FC:
        ft = ImageFont.truetype(os.path.join(d, f), co)
        if truc:
            ft.set_variation_by_axes(list(truc))
        _FC[k] = ft
    return _FC[k]


_D = ImageDraw.Draw(Image.new("L", (8, 8)))


def nfc(t):
    return unicodedata.normalize("NFC", str(t))


def bb(txt, f, sw=0):
    """Hộp chữ quanh điểm (0, chân chữ)."""
    return _D.textbbox((0, 0), nfc(txt), font=f, anchor="ls", stroke_width=sw)


def dai(txt, f):
    return _D.textlength(nfc(txt), font=f)


def cap(f):
    return -bb("H", f)[1]


def vua(txt, dam, co, max_w, ho="be_vietnam", sw=0, nho=30, nho_nhat=None):
    """Font cỡ lớn nhất ≤ co để txt vừa max_w (bước 2px). Cỡ cuối < nho_nhat (mặc định 62% cỡ đặt, tối thiểu 30) hoặc vẫn tràn
    -> ghi ve_chu.CHU_NHO (render báo "phải thu còn …px")."""
    c0 = co
    while co > nho and dai(txt, F(dam, co, ho)) + 2 * sw > max_w:
        co -= 2
    nn = nho_nhat if nho_nhat is not None else max(30, round(c0 * 0.62))
    if V is not None and (co < nn or dai(txt, F(dam, co, ho)) + 2 * sw > max_w):
        V.CHU_NHO.append((nfc(txt), co))
    return F(dam, co, ho)


def in_hoa(t):
    return V.in_hoa(nfc(t))


def lop():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


# ---------------------------------------------------------------- hình khối khử răng cưa
def _mask(w, h, ve):
    m = Image.new("L", (max(1, w) * SS, max(1, h) * SS), 0)
    ve(ImageDraw.Draw(m), SS)
    return m.resize((max(1, w), max(1, h)), Image.LANCZOS)


def _bez(a, c, b, n=20):
    return [((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u * u * b[0],
             (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u * u * b[1]) for u in (j / n for j in range(n + 1))]


def _duoi_pts(box, du, inset=0.0):
    """Đuôi bong bóng thoại: chân lấn vào đáy khối, mũi nhọn chĩa xuống ra ngoài; inset = co vào (viền)."""
    x0, y0, x1, y1 = box
    bw = x1 - x0
    d, rg, vt = float(du.get("dai", 62)), float(du.get("rong", 80)), float(du.get("vi_tri", 0.14))
    yb = y1 - 30
    ax = x0 + vt * bw
    bx = ax + rg
    tip = (ax - d * 0.42 + inset * 1.7, y1 + d - inset * 2.5)
    a, b = (ax + inset * 1.1, yb), (bx - inset * 1.9, yb)
    ca = (ax - d * 0.02 + inset * 0.6, y1 + d * 0.40)    # cạnh ngoài hơi phồng
    cb = (ax + rg * 0.30, y1 + d * 0.22)                 # cạnh trong khoét vào
    pts = _bez(a, ca, tip) + _bez(tip, cb, b)
    if du.get("ben", "trai") == "phai":
        pts = [(x0 + x1 - x, y) for x, y in pts]
    return pts


def _xanh_doi(w, h, ty0, ty1):
    """Lục bảo đổ dải dọc (sáng trên → đậm dưới) = dải khoi_xanh của engine (kiem_mau chấp nhận)."""
    yy = np.arange(h, dtype=np.float32)[:, None]
    t = np.clip((yy - ty0) / max(1.0, ty1 - ty0), 0, 1)
    tren, giua, duoi = (np.array(c, np.float32) for c in (V.XANH_TREN, V.XANH[:3], V.XANH_DUOI))
    col = np.where(t < 0.45, tren + (giua - tren) * (t / 0.45), giua + (duoi - giua) * ((t - 0.45) / 0.55))
    arr = np.empty((h, w, 4), np.uint8)
    arr[..., :3] = np.broadcast_to(col[:, None, :], (h, w, 3)).astype(np.uint8)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")


def _kinh(nen, X0, Y0, w, h, ty0, ty1, mo=26, phu=0.58, duc=0.84):
    """Tấm kính lục bảo + ánh sáng mờ nửa trên. Có nen (ảnh khung, chỉ ảnh duyệt dev): làm mờ thật cảnh phía sau.
    Không nen: KINH che_do "mo" -> lục bảo trong `phu` (dung_may_chu / khung xem làm mờ cảnh bên dưới) | "duc" -> đục `duc` (Premiere)."""
    yy = np.arange(h, dtype=np.float32)[:, None, None]
    g = np.clip(1 - (yy - ty0) / (0.65 * max(1.0, ty1 - ty0)), 0, 1) ** 2 * 0.09
    km = V._tron(V.XANH[:3], V.XANH_TOI[:3], 0.50) if V is not None else KINH_MAU
    if nen is None:
        c = np.array(km, np.float32)[None, None, :]
        out = np.broadcast_to(c + (255 - c) * g, (h, w, 3))
        a = np.full((h, w, 1), 255 * (phu if KINH["che_do"] == "mo" else duc), np.float32)
        return Image.fromarray(np.concatenate([np.clip(out, 0, 255), a], -1).astype(np.uint8), "RGBA")
    m = int(mo * 2)
    crop = nen.convert("RGB").crop((X0 - m, Y0 - m, X0 + w + m, Y0 + h + m)).filter(ImageFilter.GaussianBlur(mo))
    arr = np.asarray(crop.crop((m, m, m + w, m + h)), np.float32)
    arr = arr * 0.35 + arr.mean(-1, keepdims=True) * 0.65   # bớt màu cảnh (gỗ cam + xanh = ra màu rêu) -> kính vẫn lục bảo
    out = arr * (1 - phu) + np.array(km, np.float32) * phu
    out = out + (255 - out) * g
    a = np.full((h, w, 1), 255, np.float32)
    return Image.fromarray(np.concatenate([np.clip(out, 0, 255), a], -1).astype(np.uint8), "RGBA")


def to_khoi(im, box, r, nen_kieu="xanh", vien=0.0, vien_mau=None, duoi=None, khung=None, a=255, vet_sang=True):
    """Khối bo góc (± đuôi bong bóng) lên im. nen_kieu: 'xanh' (đổ dải) | 'kinh' (cần khung) | tên màu.
    vien: viền px (vien_mau RGBA). Trả hộp bao (kể cả đuôi)."""
    x0, y0, x1, y1 = (float(v) for v in box)
    pts = _duoi_pts((x0, y0, x1, y1), duoi) if duoi else []
    xs, ys = [x0, x1] + [p[0] for p in pts], [y0, y1] + [p[1] for p in pts]
    X0, Y0, X1, Y1 = int(min(xs)) - 3, int(min(ys)) - 3, int(max(xs)) + 4, int(max(ys)) + 4
    w, h = X1 - X0, Y1 - Y0

    def hinh(ins):
        def ve(d, k):
            d.rounded_rectangle([(x0 + ins - X0) * k, (y0 + ins - Y0) * k, (x1 - ins - X0) * k, (y1 - ins - Y0) * k],
                                radius=max(1.0, r - ins) * k, fill=255)
            if duoi:
                d.polygon([((x - X0) * k, (y - Y0) * k) for x, y in _duoi_pts((x0, y0, x1, y1), duoi, ins)], fill=255)
        return ve
    m = _mask(w, h, hinh(0))
    mi = _mask(w, h, hinh(vien)) if vien else m
    if nen_kieu == "xanh":
        core = _xanh_doi(w, h, y0 - Y0, y1 - Y0)
    elif nen_kieu == "kinh":
        core = _kinh(khung, X0, Y0, w, h, y0 - Y0, y1 - Y0)
    else:
        core = Image.new("RGBA", (w, h), M(nen_kieu))
    ca = core.split()[-1]
    core.putalpha(ImageChops.multiply(mi, ca).point(lambda v: v * a // 255))
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if vien:
        vm = vien_mau or M("trang")
        dac = vm[3] >= 250 and ca.getextrema()[0] >= 250 and a >= 250
        nen_v = m if dac else ImageChops.subtract(m, mi)   # viền đặc: tô cả hình rồi đặt lõi lên (không hở mép)
        rl = Image.new("RGBA", (w, h), tuple(vm[:3]) + (0,))
        rl.putalpha(nen_v.point(lambda v: v * vm[3] // 255))
        out.alpha_composite(rl)
    out.alpha_composite(core)
    if vet_sang and nen_kieu in ("xanh", "kinh"):   # vệt sáng mảnh mép trên trong lõi (men / kính)
        dich = Image.new("L", (w, h), 0)
        dich.paste(mi, (0, 3))
        vs = np.asarray(ImageChops.subtract(mi, dich), np.float32)
        vs[int(y0 - Y0 + (y1 - y0) * 0.4):, :] = 0
        vl = Image.new("RGBA", (w, h), (255, 255, 255, 0))
        vl.putalpha(Image.fromarray((vs * (0.30 if nen_kieu == "xanh" else 0.45)).astype(np.uint8), "L"))
        out.alpha_composite(vl)
    im.alpha_composite(out, (X0, Y0))
    return (X0, Y0, X1, Y1)


def _vung(im, le):
    """Hộp có nét của lớp toàn khung, nới `le` px (kẹp trong khung) | None."""
    bx = im.getbbox()
    if not bx:
        return None
    return (max(0, bx[0] - le), max(0, bx[1] - le), min(W, bx[2] + le), min(H, bx[3] + le))


def _trong():
    return KINH["che_do"] == "mo"


def bong(im, mo=14, dy=8, a=110, mau="xanh_toi", sat=(3, 2, 70), ngoai=False):
    """Bóng gọn: 1 lớp mềm ngắn + 1 lớp sát (thay bóng 2 lớp lan rộng 22px cũ — trên nền gỗ sáng trông bẩn).
    Làm trên vùng có nét (nới đủ bán kính mờ) cho nhanh, kết quả y như làm cả khung. ngoai=True (kính trong): bóng chỉ ở NGOÀI hình
    (dưới tấm kính trong không có bóng, kẻo kính đục / tối thêm)."""
    v = _vung(im, int(3 * max(mo, sat[0] if sat else 0)) + abs(int(dy)) + 4)
    if not v:
        return im
    c = im.crop(v)
    al = c.split()[-1]
    out_c = Image.new("RGBA", c.size, (0, 0, 0, 0))
    for mo_, dy_, a_ in ((mo, dy, a),) + ((sat,) if sat else ()):
        sh = Image.new("RGBA", c.size, M(mau, 0)[:3] + (0,))
        sh.putalpha(al.filter(ImageFilter.GaussianBlur(mo_)).point(lambda x, a_=a_: x * a_ // 255))
        out_c.alpha_composite(sh, (0, int(dy_)))
    if ngoai:
        ra = ImageChops.multiply(out_c.getchannel("A"), al.point(lambda x: 255 - x))
        out_c.putalpha(ra)
    out_c.alpha_composite(c)
    out = lop()
    out.paste(out_c, v[:2])
    return out


def bong_chu(im, mo=8, dy=4, a=200):
    """Bóng đậm sát chữ cho chữ KHÔNG viền (bộ tối giản): đọc được cả trên nền trắng."""
    return bong(im, mo, dy, a, "den", sat=(2, 1, 150))


def viet(im, x, yb, tu, f, sw=0, sf=None):
    """Viết các từ [(chữ, màu)] từ x, chân chữ yb. Trả x cuối."""
    d = ImageDraw.Draw(im)
    sp = d.textlength(" ", font=f)
    for i, (t, c) in enumerate(tu):
        t = nfc(t)
        d.text((x, yb), t, font=f, fill=c, anchor="ls", stroke_width=sw, stroke_fill=sf)
        x += d.textlength(t, font=f) + (sp if i < len(tu) - 1 else 0)
    return x


DAU_TREN = 0.54   # lề trên viên / hộp chữ IN HOA (× cỡ chữ, tính từ đỉnh chữ hoa): chừa dấu chồng cao nhất (Ổ, Ẫ ≈ 0,43)


def _la_vang(w, vang):
    t = nfc(w).lower()
    vg = {nfc(v).lower().strip(",.!?:;…") for v in vang}
    return t in vg or t.strip(",.!?:;…%") in vg


def to_tu(chu, vang, mau_thuong, mau_vang):
    """'MÀN HÌNH ĐẸP', {'đẹp'} -> [(từ, màu)]."""
    vg = {nfc(v).lower() for v in vang}
    return [(w, mau_vang if nfc(w).lower().strip(",.!?:;…%") in vg or nfc(w).lower() in vg else mau_thuong)
            for w in nfc(chu).split()]


def hop_bao(*hops):
    hs = [h for h in hops if h]
    return (min(h[0] for h in hs), min(h[1] for h in hs), max(h[2] for h in hs), max(h[3] for h in hs))


def xoay(im, goc, tam):
    return im.rotate(goc, resample=Image.BICUBIC, center=tam) if goc else im


def cx_cho(bw):
    """Tâm ngang của khối rộng bw: khối hẹp căn giữa khung (540), khối rộng dịch trái vừa đủ để mép phải ≤ x 900."""
    return min(540.0, LE_PHAI - bw / 2.0)


def man_toi(chu, a=105, mo=38, pad=(46, 30)):
    """Lớp tối rất mờ sau khối chữ không nền (bộ tối giản): đọc được trên màn iPad sáng / game; đen trung tính (pha xanh
    trông như vệt bẩn — ghi chú cũ ở ve_chu.tieu_de_toi_gian). Làm trên vùng quanh chữ cho nhanh."""
    b = chu.getbbox()
    out = lop()
    if not b:
        return out
    le = 3 * mo + max(pad)
    v = (max(0, b[0] - le), max(0, b[1] - le), min(W, b[2] + le), min(H, b[3] + le))
    m = Image.new("L", (v[2] - v[0], v[3] - v[1]), 0)
    ImageDraw.Draw(m).rounded_rectangle([b[0] - pad[0] - v[0], b[1] - pad[1] - v[1], b[2] + pad[0] - v[0], b[3] + pad[1] - v[1]],
                                        radius=60, fill=a)
    sh = Image.new("RGBA", m.size, (0, 0, 0, 0))
    sh.putalpha(m.filter(ImageFilter.GaussianBlur(mo)))
    out.paste(sh, v[:2])
    return out


def ghim_vung(hop):
    """Dời ngang để hộp nằm trong x 90–900 (nếu lọt ra)."""
    dx = 0
    if hop[2] > LE_PHAI:
        dx = LE_PHAI - hop[2]
    if hop[0] + dx < LE_TRAI:
        dx = LE_TRAI - hop[0]
    return int(dx)


def _xep_dong(dong, x_tam=None, x_trai=None, y_cap=0, gap=12):
    """dong = [(tu, f, sw)] -> [(x, chân chữ, rộng)] xếp dọc: dòng sau cách dòng trước theo hộp chữ THẬT (dấu tiếng Việt
    của dòng dưới không chạm đuôi chữ dòng trên). y_cap = mép trên chữ HOA dòng 1."""
    out, yb_truoc, day_truoc = [], None, 0
    for tu, f, sw in dong:
        s = " ".join(t for t, _ in tu)
        b = bb(s, f, sw)
        rong = dai(s, f) + 2 * sw
        c = cap(f)
        if yb_truoc is None:
            yb = y_cap + c
        else:
            tren = max(-b[1], c + 0.10 * f.size)   # dấu của dòng này
            yb = yb_truoc + max(day_truoc, 0.08 * f.size) + gap + tren
        x = (x_tam - rong / 2 + sw) if x_tam is not None else x_trai + sw
        out.append((x, yb, rong))
        yb_truoc, day_truoc = yb, max(b[3], 0)
    return out


# ---------------------------------------------------------------- thành phần chung
def _vien_trang(a=255):
    return M("trang", a)


def _nut(im, txt, cx, y, nen="trang", chu="xanh", co=40, tim=True, x_trai=None):
    """Nút viên thuốc (Poly hỗ trợ nha ♥). Trả hộp."""
    txt = nfc(txt).replace("️", "").rstrip()
    co_tim = tim and txt.endswith(("♥", "❤", "<3"))
    txt = txt.rstrip("♥❤").replace("<3", "").rstrip()
    f = F("Black", co)
    tw = dai(txt, f)
    w_tim = int(co * 1.05) if co_tim else 0
    px, ph = int(co * 0.9), int(cap(f) + co * 0.95)
    bw = tw + w_tim + 2 * px
    x0 = x_trai if x_trai is not None else cx - bw / 2
    box = (x0, y, x0 + bw, y + ph)
    to_khoi(im, box, ph / 2, nen, vet_sang=False)
    yb = y + ph / 2 + cap(f) / 2
    viet(im, x0 + px, yb, [(txt, M(chu))], f)
    if co_tim:
        V.tim(ImageDraw.Draw(im), x0 + px + tw + w_tim * 0.62, yb - cap(f) / 2 + 1, co * 0.36, M(chu))
    return box


def _pin(im, x, cy, h, mau):
    """Icon ghim bản đồ (vẽ tay, khử răng cưa). Trả bề rộng."""
    w = int(h * 0.78)

    def ve(d, k):
        r = w / 2
        d.ellipse([0, 0, w * k, w * k], fill=255)
        d.polygon([(w * 0.14 * k, r * 1.45 * k), (w * 0.86 * k, r * 1.45 * k), (r * k, h * k)], fill=255)
        d.ellipse([(r - r * 0.40) * k, (r - r * 0.40) * k, (r + r * 0.40) * k, (r + r * 0.40) * k], fill=0)
    m = _mask(w + 1, int(h) + 1, ve)
    l = Image.new("RGBA", m.size, tuple(mau[:3]) + (0,))
    l.putalpha(m)
    im.alpha_composite(l, (int(x), int(cy - h / 2)))
    return w


def _icon(im, kieu, x, cy, h, mau):
    ic = Image.new("RGBA", ((h + 8) * SS, h * SS), (0, 0, 0, 0))
    V._icon(ImageDraw.Draw(ic), kieu, 2 * SS, h * SS / 2, h * SS, mau)
    ic = ic.resize((h + 8, h), Image.LANCZOS)
    im.alpha_composite(ic, (int(x), int(cy - h / 2)))
    return h + 4


def _gia_tach(gia):
    """'13.990.000đ' -> ('13.990.000', 'đ'); '13TR9' -> ('13TR9', '')."""
    g = nfc(gia).strip()
    m = re.match(r"^(.*?\d)\s*(đ|₫|vnđ|VNĐ|k|K)$", g)
    return (m.group(1), "đ" if m.group(2) in ("₫", "vnđ", "VNĐ") else m.group(2)) if m else (g, "")


# ================================================================ HOOK
def _xuong_dong(dong, hk, max_w):
    """Hook: dòng phải thu < xuong_dong × cỡ đặt (dòng dài, vd 22 ký tự) thì tách làm 2 dòng cùng vai (tối đa 3 dòng) —
    chữ to đều thay vì 1 dòng tí hon. Trả [(chữ, vai 0|1)]."""
    out = []
    for i, t in enumerate(dong):
        dam, co = hk["dam"][min(i, 1)], hk["co"][min(i, 1)]
        f = vua(t, dam, co, max_w)
        if f.size < co * hk.get("xuong_dong", 0) and len(t.split()) >= 3 and len(dong) + len(out) - i < 3:
            for p in V.chia_dong(t, lambda s_: dai(s_, F(dam, co * 0.92)), max_w):
                out.append((p, min(i, 1)))
        else:
            out.append((t, min(i, 1)))
    return out[:3]


def hook(bo, dong, y=300, nen=None):
    b = BO[bo]
    hk = b["hook"]
    dong = [nfc(x) for x in dong if str(x).strip()][:2]
    im = lop()
    if _ho(bo) in ("khoi", "kinh"):
        pl, pt, pb = hk.get("pad", [54, 34, 40])
        max_txt = 810 - 2 * pl
        ds = _xuong_dong(dong, hk, max_txt)
        fs = [vua(t, hk["dam"][v], hk["co"][v], max_txt) for t, v in ds]
        for v in (0, 1):   # các dòng cùng vai: cùng cỡ (cỡ nhỏ nhất)
            c_ = [f.size for f, (_, vv) in zip(fs, ds) if vv == v]
            if c_:
                fs = [F(hk["dam"][vv], min(c_)) if vv == v else f for f, (_, vv) in zip(fs, ds)]
        rows = [([(t, M(hk["mau"][v]))], f, 0) for (t, v), f in zip(ds, fs)]
        tw = max(dai(t, f) for (t, _), f in zip(ds, fs))
        bw = max(tw + 2 * pl, 420)
        cx = cx_cho(bw)
        # dấu chồng dòng 1 (Ổ, Ẫ cao hơn chữ hoa ~0,43 cỡ): chữ lùi xuống để dấu nằm trong bong bóng, cách viền ≥ 8px
        them = max(0.0, (-bb(ds[0][0], fs[0])[1] - cap(fs[0])) - (pt - 8))
        xs = _xep_dong(rows, x_tam=cx, y_cap=y + pt + them, gap=12)
        bot = xs[-1][1] + max(bb(ds[-1][0], fs[-1])[3], 0.10 * fs[-1].size) + pb
        box = (cx - bw / 2, y, cx + bw / 2, bot)
        if _ho(bo) == "khoi":
            hop = to_khoi(im, box, b["bo_goc"], "xanh", vien=hk["vien"], vien_mau=_vien_trang(), duoi=hk["duoi"])
        else:
            hop = to_khoi(im, box, b["bo_goc"], "kinh", vien=hk["vien"], vien_mau=_vien_trang(150), duoi=hk["duoi"], khung=nen)
        for (tu, f, sw), (x, yb, _) in zip(rows, xs):
            viet(im, x, yb, tu, f)
        im = bong(im, 16, 10, 120) if _ho(bo) == "khoi" else bong(im, 18, 10, 90, ngoai=_trong())
        return im, hop
    # toi_gian: dòng 1 trắng Black to (bóng mềm) + dòng 2 chữ xanh trên bút dạ vàng, căn trái x 90
    ds = _xuong_dong(dong, hk, 790)
    chu, th = lop(), lop()
    hop, y_ = None, y
    for t, v in ds:
        if v == 0:
            f1 = vua(t, "Black", hk["co"][0], 800)
            yb1 = y_ + max(cap(f1), -bb(t, f1)[1] if hop else cap(f1))
            viet(chu, LE_TRAI, yb1, [(t, M("trang"))], f1)
            h_ = (LE_TRAI, y_, LE_TRAI + dai(t, f1), yb1 + max(bb(t, f1)[3], 0))
            hop = hop_bao(hop, h_) if hop else h_
            y_ = h_[3] + 0.16 * f1.size
        else:
            f2 = vua(t, "Black", hk["co"][1], 760)
            c2 = cap(f2)
            px, pt, pb = 22, max(-bb(t, f2)[1] - c2, 0.30 * f2.size) + 12, 0.32 * f2.size
            top2 = y_ + 14 + pt
            box = (LE_TRAI - 4, top2 - pt, LE_TRAI + dai(t, f2) + 2 * px - 4, top2 + c2 + pb)
            to_khoi(th, box, 10, "vang", vet_sang=False)
            viet(th, LE_TRAI - 4 + px, top2 + c2, [(t, M("xanh"))], f2)
            hop = hop_bao(hop, box) if hop else box
            y_ = box[3] - 4
    im.alpha_composite(man_toi(chu, 90))
    im.alpha_composite(bong_chu(chu, 9, 5, 190))
    im.alpha_composite(bong(th, 10, 6, 90, sat=None))
    return im, tuple(int(v) for v in hop)


# ================================================================ NHÃN TỪ KHOÁ
def nhan(bo, txt, y=600, nen=None):
    b = BO[bo]
    n = b["nhan"]
    txt = in_hoa(txt)
    im = lop()
    if _ho(bo) == "khoi":   # vàng, viền đen Poly mảnh, khối nổi lục bảo phía sau (đổ thẳng xuống), nghiêng nhẹ
        f = vua(txt, "Black", n["co"], 760, sw=n["vien"])
        w = dai(txt, f)
        CX = cx_cho(w + 40)
        x, yb = CX - w / 2, y + cap(f)
        khoi_ = lop()
        d = ImageDraw.Draw(khoi_)
        for k in range(n["noi"], 0, -1):
            d.text((x, yb + k), txt, font=f, fill=M("xanh"), anchor="ls", stroke_width=n["vien"], stroke_fill=M("xanh_toi"))
        viet(khoi_, x, yb, [(txt, M("vang"))], f, n["vien"], M("xanh_toi"))
        khoi_ = xoay(khoi_, n["goc"], (CX, yb - cap(f) / 2))
        im = bong(khoi_, 14, 10, 110)
        return im, im.getbbox()
    if _ho(bo) == "but_da":   # bút dạ vàng chữ xanh, căn trái, nghiêng −2°
        f = vua(txt, "Black", n["co"], 740)
        c = cap(f)
        pt, pb, px = max(-bb(txt, f)[1] - c, 0.28 * f.size) + 10, 0.30 * f.size, 26
        box = (LE_TRAI, y, LE_TRAI + dai(txt, f) + 2 * px, y + pt + c + pb)
        to_khoi(im, box, 10, "vang", vet_sang=False)
        viet(im, LE_TRAI + px, y + pt + c, [(txt, M("xanh"))], f)
        im = xoay(im, n["goc"], ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
        im = bong(im, 12, 8, 100, sat=None)
        return im, im.getbbox()
    # kinh: viên kính, chấm vàng + chữ vàng
    f = vua(txt, "Black", n["co"], 680)
    c = cap(f)
    pt, pb, px = max(-bb(txt, f)[1] - c, 0.30 * f.size) + 12, 0.34 * f.size + 4, 34
    dot = int(c * 0.42)
    bw = dai(txt, f) + 2 * px + dot + 18
    CX = cx_cho(bw)
    box = (CX - bw / 2, y, CX + bw / 2, y + pt + c + pb)
    to_khoi(im, box, (box[3] - box[1]) / 2, "kinh", vien=2, vien_mau=M("trang", 120), khung=nen)
    d = ImageDraw.Draw(im)
    yb = y + pt + c
    _cham(im, box[0] + px + dot / 2, yb - c / 2, dot / 2, M("vang"))
    viet(im, box[0] + px + dot + 18, yb, [(txt, M("vang"))], f)
    im = bong(im, 16, 8, 80, ngoai=_trong())
    return im, tuple(int(v) for v in box)


def _cham(im, cx, cy, r, mau):
    m = _mask(int(2 * r) + 2, int(2 * r) + 2, lambda d, k: d.ellipse([k, k, (2 * r + 1) * k, (2 * r + 1) * k], fill=255))
    l = Image.new("RGBA", m.size, tuple(mau[:3]) + (0,))
    l.putalpha(m)
    im.alpha_composite(l, (int(cx - r - 1), int(cy - r - 1)))


# ================================================================ THẺ GIÁ
def the_gia(bo, gia, gia_cu=None, ghi_chu=None, y=760, nen=None):
    b = BO[bo]
    g = b["gia"]
    so, dv = _gia_tach(gia)
    im = lop()
    if _ho(bo) == "but_da":   # không khối: giá cũ gạch, số hẹp cao trắng + đ vàng, ghi chú trên bút dạ vàng; căn trái
        chu = lop()
        y_ = y
        hop = [LE_TRAI, y, LE_TRAI, y]
        if gia_cu:
            fc = F("ExtraBold", 46)
            yb = y_ + cap(fc)
            x1 = viet(chu, LE_TRAI, yb, [(gia_cu, M("trang"))], fc)
            ImageDraw.Draw(chu).line([(LE_TRAI - 4, yb - cap(fc) * 0.40), (x1 + 4, yb - cap(fc) * 0.40)], fill=M("vang"), width=4)
            hop[2] = max(hop[2], x1)
            y_ = yb + 26
        fs = F("Black", g["co_gia"], "archivo_hep")
        fd = F("Black", g["co_gia"] * 0.40, "be_vietnam")
        while dai(so, fs) + (dai(dv, fd) + 6 if dv else 0) > 800 and fs.size > 90:
            fs = F("Black", fs.size - 4, "archivo_hep")
            fd = F("Black", fs.size * 0.40)
        yb = y_ + cap(fs)
        x1 = viet(chu, LE_TRAI, yb, [(so, M("trang"))], fs)
        if dv:
            x1 = viet(chu, x1 + 2, yb, [(dv, M(g["mau_don_vi"]))], fd)   # đ vàng đứng chân chữ, nhỏ
        hop[2] = max(hop[2], x1)
        hop[3] = yb + 6
        im.alpha_composite(man_toi(chu, 95))
        im.alpha_composite(bong_chu(chu, 10, 6, 200))
        if ghi_chu:
            fg = F("ExtraBold", 36)
            c = cap(fg)
            pt = max(-bb(ghi_chu, fg)[1] - c, 0.28 * fg.size) + 8
            box = (LE_TRAI, hop[3] + 20, LE_TRAI + dai(ghi_chu, fg) + 40, hop[3] + 20 + pt + c + 0.32 * fg.size)
            th = lop()
            to_khoi(th, box, 8, "vang", vet_sang=False)
            viet(th, LE_TRAI + 20, box[1] + pt + c, [(ghi_chu, M("xanh"))], fg)
            im.alpha_composite(bong(th, 10, 6, 80, sat=None))
            hop = hop_bao(hop, box)
        return im, tuple(int(v) for v in hop)
    # luc_bao / kinh: thẻ, căn trái trong thẻ: giá cũ gạch (trắng mờ, gạch vàng) · giá to vàng + đ nhỏ · ghi chú
    pad = 52
    fs = F("Black", g["co_gia"])
    fd = F("Black", g["co_gia"] * 0.48)
    while dai(so, fs) + (dai(dv, fd) + 8 if dv else 0) > 800 - 2 * pad and fs.size > 80:
        fs, fd = F("Black", fs.size - 4), F("Black", (fs.size - 4) * 0.48)
    fc = F("ExtraBold", 46)
    fg = F("ExtraBold" if _ho(bo) == "khoi" else "Bold", 36)
    w_gia = dai(so, fs) + (dai(dv, fd) + 8 if dv else 0)
    rong = max(w_gia, dai(gia_cu, fc) if gia_cu else 0, dai(ghi_chu, fg) if ghi_chu else 0)
    bw = rong + 2 * pad
    x0 = cx_cho(bw) - bw / 2
    yy = y + 42
    dong = []
    if gia_cu:
        dong.append(("cu", yy + cap(fc)))
        yy = yy + cap(fc) + 28
    dong.append(("gia", yy + cap(fs)))
    yy = yy + cap(fs) + 40
    y_dai = None
    if ghi_chu:
        if _ho(bo) == "khoi":   # dải vàng đáy thẻ (kiểu cuống vé), chữ xanh
            y_dai = yy
            yy += 22
            dong.append(("ghi", yy + cap(fg) + max(-bb(ghi_chu, fg)[1] - cap(fg), 0)))
            yy = dong[-1][1] + max(bb(ghi_chu, fg)[3], 8) + 22
        else:
            dong.append(("ghi", yy + cap(fg)))
            yy += cap(fg) + max(bb(ghi_chu, fg)[3], 0) + 40
    box = (x0, y, x0 + bw, yy)
    r = b["bo_goc"] - 6 if _ho(bo) == "khoi" else b["bo_goc"]
    if _ho(bo) == "khoi":
        to_khoi(im, box, r, "xanh", vien=g["vien"], vien_mau=_vien_trang())
        if y_dai is not None:   # dải vàng cắt theo đúng góc bo trong viền
            v = g["vien"]
            w_, h_ = int(bw), int(yy - y)
            mk = _mask(w_, h_, lambda d, k: d.rounded_rectangle([v * k, v * k, (w_ - v) * k, (h_ - v) * k], radius=(r - v) * k, fill=255))
            cut = Image.new("L", (w_, h_), 0)
            ImageDraw.Draw(cut).rectangle([0, int(y_dai - y), w_, h_], fill=255)
            dl = Image.new("RGBA", (w_, h_), M("vang"))
            dl.putalpha(ImageChops.multiply(mk, cut))
            im.alpha_composite(dl, (int(x0), int(y)))
    else:
        to_khoi(im, box, r, "kinh", vien=2, vien_mau=M("trang", 140), khung=nen)
    d = ImageDraw.Draw(im)
    xl = x0 + pad
    for loai, yb in dong:
        if loai == "cu":
            x1 = viet(im, xl, yb, [(gia_cu, M("trang", 225))], fc)
            d.line([(xl - 4, yb - cap(fc) * 0.40), (x1 + 4, yb - cap(fc) * 0.40)], fill=M("vang"), width=5)
        elif loai == "gia":
            x1 = viet(im, xl, yb, [(so, M(g["mau_gia"]))], fs)
            if dv:
                viet(im, x1 + 6, yb - cap(fs) + cap(fd), [(dv, M(g["mau_gia"]))], fd)
        else:
            viet(im, xl, yb, [(ghi_chu, M("xanh") if _ho(bo) == "khoi" else M("trang", 235))], fg)
    im = bong(im, 16, 10, 115) if _ho(bo) == "khoi" else bong(im, 18, 10, 85, ngoai=_trong())
    return im, tuple(int(v) for v in box)


# ================================================================ THẺ TÊN MÁY
def the_ten(bo, ten, tag=None, thong_so=None, y=840, nen=None):
    b = BO[bo]
    tm = b["ten_may"]
    ten = V.ten_dung(nfc(ten))
    trang_, vang_ = V.tach_doi(ten)
    ts = [V.ten_dung(x) if V.RE_TEN_MAY.search(str(x)) else nfc(x).strip() for x in (thong_so or []) if str(x).strip()][:4]
    im = lop()
    if _ho(bo) == "but_da":   # không khối, căn trái: tag bút dạ nhỏ · tên trắng to + đời vàng · gạch vàng ngắn · thông số trắng
        y_ = y
        hop = [LE_TRAI, y, LE_TRAI + 10, y + 10]
        if tag:
            ft = F("ExtraBold", 32)
            tg = in_hoa(tag)
            c = cap(ft)
            pt = max(-bb(tg, ft)[1] - c, 0.26 * ft.size) + 6
            box = (LE_TRAI, y_, LE_TRAI + dai(tg, ft) + 36, y_ + pt + c + 0.30 * ft.size)
            th = lop()
            to_khoi(th, box, 8, "vang", vet_sang=False)
            viet(th, LE_TRAI + 18, box[1] + pt + c, [(tg, M("xanh"))], ft)
            tag_l = bong(th, 8, 5, 80, sat=None)   # dán SAU lớp tối mờ của chữ (không làm tối vàng)
            hop = list(hop_bao(hop, box))
            y_ = box[3] + 18
        f = vua(ten, "ExtraBold", tm["co"], 800)
        chu = lop()
        yb = y_ + max(-bb(ten, f)[1], cap(f))
        x1 = viet(chu, LE_TRAI, yb, [(trang_, M("trang"))] + ([(vang_, M("vang"))] if vang_ else []), f)
        hop = list(hop_bao(hop, (LE_TRAI, y_, x1, yb + 8)))
        if ts:
            fs = F("Bold", 40)
            yb2 = yb + 36 + 12 + cap(fs)
            ImageDraw.Draw(chu).rounded_rectangle([LE_TRAI, yb + 26, LE_TRAI + 88, yb + 33], radius=3, fill=M("vang"))
            x = LE_TRAI
            for i, t in enumerate(ts):
                if i:
                    ImageDraw.Draw(chu).rounded_rectangle([x + 14, yb2 - cap(fs) * 0.62, x + 22, yb2 - cap(fs) * 0.38],
                                                          radius=2, fill=M("vang"))
                    x += 36
                x = viet(chu, x, yb2, [(t, M("trang"))], fs)
            hop = list(hop_bao(hop, (LE_TRAI, yb, x, yb2 + 8)))
        im.alpha_composite(man_toi(chu, 90))
        im.alpha_composite(bong_chu(chu, 10, 5, 200))
        if tag:
            im.alpha_composite(tag_l)
        return im, tuple(int(v) for v in hop)
    # luc_bao: thẻ lục bảo + tab vàng dính mép trên (như tab hồ sơ) · kinh: thẻ kính + tag vàng trong thẻ
    pad = 50
    f = vua(ten, "ExtraBold", tm["co"], 800 - 2 * pad)
    fs = F("Bold", 36)

    def rong_ts():
        return sum(int(cap(fs) * 1.15) + 14 + dai(t, fs) for t in ts) + 46 * max(0, len(ts) - 1)
    while ts and rong_ts() > 810 - 2 * pad:   # thu cỡ tới 30px; vẫn tràn thì bớt viên cuối (thẻ không vượt x 900)
        if fs.size > 30:
            fs = F("Bold", fs.size - 2)
        else:
            ts = ts[:-1]
    ih = int(cap(fs) * 1.15)
    w_ts = rong_ts() if ts else 0
    bw = min(810, max(dai(ten, f), w_ts) + 2 * pad)
    x0 = cx_cho(bw) - bw / 2
    ft = F("ExtraBold", 32)
    tg = in_hoa(tag) if tag else None
    c = cap(ft)
    tb = None
    yc = y + 42
    if tg and bo == "kinh":   # tag vàng trong thẻ kính, trên tên
        tb = (x0 + pad - 4, y + 28, x0 + pad - 4 + dai(tg, ft) + 40, y + 28 + c + 28)
        yc = tb[3] + 20
    yb = yc + max(-bb(ten, f)[1], cap(f))
    y_gach = yb + 32
    yb2 = y_gach + 32 + cap(fs)
    y1 = (yb2 + 42) if ts else (yb + 46)
    box = (x0, y, x0 + bw, y1)
    if _ho(bo) == "khoi":
        if tg:   # tab vàng dính mép trên thẻ (như tab hồ sơ): đáy chìm dưới thẻ
            ttw = dai(tg, ft) + 44
            tab = (x0 + 36, y - c - 30, x0 + 36 + ttw, y + 26)
            to_khoi(im, tab, 14, "vang", vet_sang=False)
        to_khoi(im, box, b["bo_goc"] - 6, "xanh", vien=tm["vien"], vien_mau=_vien_trang())
        if tg:
            viet(im, tab[0] + 22, y - 15, [(tg, M("xanh"))], ft)
    else:
        to_khoi(im, box, b["bo_goc"], "kinh", vien=2, vien_mau=M("trang", 140), khung=nen)
        if tb:
            to_khoi(im, tb, (tb[3] - tb[1]) / 2, "vang", vet_sang=False)
            viet(im, tb[0] + 20, tb[1] + 14 + c, [(tg, M("xanh"))], ft)
    xl = x0 + pad
    viet(im, xl, yb, [(trang_, M("trang"))] + ([(vang_, M("vang"))] if vang_ else []), f)
    d = ImageDraw.Draw(im)
    if ts:
        d.line([(xl, y_gach), (x0 + bw - pad, y_gach)], fill=M("trang", 55), width=2)
        x = xl
        for i, t in enumerate(ts):
            if i:
                d.line([(x + 22, yb2 - cap(fs) - 4), (x + 22, yb2 + 6)], fill=M("trang", 70), width=2)
                x += 46
            x += _icon(im, V.kieu_icon(t), x, yb2 - cap(fs) / 2, ih, M("vang")) + 10
            x = viet(im, x, yb2, [(t, M("trang"))], fs)
    im = bong(im, 16, 10, 115) if _ho(bo) == "khoi" else bong(im, 18, 10, 85, ngoai=_trong())
    return im, tuple(int(v) for v in hop_bao(box, im.getbbox()))


# ================================================================ THẺ KẾT
KET_COMMENT = ["Anh em cần hỏi gì", "để lại comment nha"]
NUT_COMMENT = "Poly hỗ trợ nha ♥"
KET_DIA_CHI = ["Ghé Poly test máy nha", "125/16/26 Bùi Đình Túy, Bình Thạnh"]


def the_ket(bo, loai="comment", dong=None, nen=None, y_day=1290):
    """Thẻ kết. loai "comment": dong = [câu kêu comment, chữ nút] (như card_comment cũ: dòng 2 = nút); "dia_chi": dong = [câu mời,
    địa chỉ]. Câu kêu comment tự ngắt ≤ 2 dòng cân bằng ('|' = chỗ ngắt)."""
    b = BO[bo]
    im = lop()
    dong = [nfc(x) for x in (dong or []) if str(x or "").strip()]
    if loai == "comment":
        cau = dong[0] if dong else " ".join(KET_COMMENT)
        nut = dong[1] if len(dong) > 1 else NUT_COMMENT
        bd = _ho(bo) == "but_da"
        fd = F("Black" if bd else "ExtraBold", 72 if bd else 62)
        L = V.chia_dong(cau, lambda t: dai(t, fd), 800 if bd else 692)[:2]
    else:
        L = (dong or KET_DIA_CHI)[:2]
        nut = None
    if _ho(bo) == "but_da":   # chữ trắng to căn trái + nút vàng / ghim vàng + địa chỉ
        chu = lop()
        f1 = vua(max(L[:2] if loai == "comment" else L[:1], key=len), "Black", 72, 800)
        rows = [([(t, M("trang"))], f1, 0) for t in (L[:2] if loai == "comment" else L[:1])]
        # đặt từ dưới lên: tính chiều cao trước
        xs = _xep_dong(rows, x_trai=LE_TRAI, y_cap=0, gap=10)
        h_chu = xs[-1][1] + 10
        h_nut = 0
        fa = F("Bold", 38)
        if loai == "comment":
            h_nut = cap(F("Black", 40)) + 40 * 0.95 + 30
        else:
            h_nut = (cap(fa) + 34) if len(L) > 1 else 0
        y0 = y_day - h_chu - h_nut
        xs = _xep_dong(rows, x_trai=LE_TRAI, y_cap=y0, gap=10)
        for (tu, f, sw), (x, yb, _) in zip(rows, xs):
            viet(chu, x, yb, tu, f)
        im.alpha_composite(man_toi(chu, 95))
        im.alpha_composite(bong_chu(chu, 10, 5, 200))
        yb_cuoi = xs[-1][1]
        if loai == "comment":
            th = lop()
            box = _nut(th, nut, 0, yb_cuoi + 34, "vang", "xanh", 40, x_trai=LE_TRAI)
            im.alpha_composite(bong(th, 10, 6, 90, sat=None))
        elif len(L) > 1:
            chu2 = lop()
            yb2 = yb_cuoi + 30 + cap(fa)
            w = _pin(chu2, LE_TRAI, yb2 - cap(fa) / 2, cap(fa) * 1.25, M("vang"))
            x1 = viet(chu2, LE_TRAI + w + 14, yb2, [(L[1], M("trang"))], vua(L[1], "Bold", 38, 800 - w - 14))
            im.alpha_composite(bong_chu(chu2, 8, 4, 200))
            box = (LE_TRAI, yb2 - cap(fa), x1, yb2 + 8)
        else:
            box = (LE_TRAI, y0, LE_TRAI + 10, yb_cuoi)
        return im, tuple(int(v) for v in hop_bao((LE_TRAI, y0, LE_TRAI + max(r for _, _, r in xs), yb_cuoi), box))
    # luc_bao: comment = bong bóng đuôi phải (đối xứng hook) + nút TRẮNG chữ xanh (thẻ kết kênh) · địa chỉ = thẻ xanh
    # kinh: thẻ kính + nút vàng
    pad = 54
    f1 = vua(max(L[:2] if loai == "comment" else L[:1], key=len), "ExtraBold", 62, 800 - 2 * pad)
    rows = [([(t, M("trang"))], f1, 0) for t in (L[:2] if loai == "comment" else L[:1])]
    xs = _xep_dong(rows, x_tam=540, y_cap=0, gap=8)
    fa = vua(L[1], "Bold", 38, 800 - 2 * pad - 50) if (loai != "comment" and len(L) > 1) else None
    fn = F("Black", 40)
    h_nut = cap(fn) + 40 * 0.95
    w_dc = (dai(L[1], fa) + cap(fa) * 1.25 * 0.78 + 14) if fa else 0
    h_chu = xs[-1][1] + max(bb(L[len(rows) - 1], f1)[3], 6)
    h_duoi = (30 + h_nut) if loai == "comment" else ((28 + cap(fa) + 10) if fa else 0)
    bw = max(max(r for _, _, r in xs), w_dc, (dai(nut.rstrip("♥ "), fn) + 42 + 72) if nut else 0) + 2 * pad
    bh = 44 + h_chu + h_duoi + 46
    du = {"ben": "phai", "vi_tri": 0.14, "dai": 56, "rong": 76} if (_ho(bo) == "khoi" and loai == "comment") else None
    CX = cx_cho(bw)
    y1 = y_day - (56 if du else 0)
    box = (CX - bw / 2, y1 - bh, CX + bw / 2, y1)
    if _ho(bo) == "khoi":
        hop = to_khoi(im, box, b["bo_goc"], "xanh", vien=5 if du else 3, vien_mau=_vien_trang(), duoi=du)
    else:
        hop = to_khoi(im, box, b["bo_goc"], "kinh", vien=2, vien_mau=M("trang", 140), khung=nen)
    xs = _xep_dong(rows, x_tam=CX, y_cap=box[1] + 44, gap=8)
    for (tu, f, sw), (x, yb, _) in zip(rows, xs):
        viet(im, x, yb, tu, f)
    yb_cuoi = xs[-1][1]
    if loai == "comment":
        _nut(im, nut, CX, yb_cuoi + 34, "trang" if _ho(bo) == "khoi" else "vang", "xanh", 40)
    elif fa:
        yb2 = yb_cuoi + 28 + cap(fa) + 6
        x = CX - w_dc / 2
        w = _pin(im, x, yb2 - cap(fa) / 2, cap(fa) * 1.25, M("vang"))
        viet(im, x + w + 14, yb2, [(L[1], M("trang", 235))], fa)
    im = bong(im, 16, 10, 115) if _ho(bo) == "khoi" else bong(im, 18, 10, 85, ngoai=_trong())
    return im, tuple(int(v) for v in hop)


# ================================================================ POLY STORE + TIÊU ĐỀ GHIM
def brand(bo, nen=None):
    """POLY STORE nhỏ góc trên trái, TRONG vùng an toàn (y ≥ 220; bản cũ ở y 150 bị thanh 'Đã follow | Dành cho bạn' che)."""
    im = lop()
    f = F("ExtraBold", 28)
    t = "POLY STORE"
    c = cap(f)
    if _ho(bo) == "but_da":
        chu = lop()
        viet(chu, LE_TRAI, 232 + c, [(t, M("trang"))], f)
        ImageDraw.Draw(chu).rounded_rectangle([LE_TRAI, 232 + c + 10, LE_TRAI + 40, 232 + c + 15], radius=2, fill=M("vang"))
        im.alpha_composite(bong_chu(chu, 6, 3, 190))
        return im, (LE_TRAI, 232, int(LE_TRAI + dai(t, f)), int(232 + c + 15))
    dot = 10
    box = (LE_TRAI, 226, LE_TRAI + dai(t, f) + 36 + dot + 12, 226 + c + 30)
    if _ho(bo) == "khoi":
        to_khoi(im, box, (box[3] - box[1]) / 2, "xanh", vien=2, vien_mau=M("trang", 200))
    else:
        to_khoi(im, box, (box[3] - box[1]) / 2, "kinh", vien=1.5, vien_mau=M("trang", 140), khung=nen)
    _cham(im, box[0] + 18 + dot / 2, box[1] + 15 + c / 2, dot / 2, M("vang"))
    viet(im, box[0] + 18 + dot + 12, box[1] + 15 + c, [(t, M("trang"))], f)
    return bong(im, 8, 4, 70, sat=None, ngoai=_ho(bo) == "kinh" and _trong()), tuple(int(v) for v in box)


def tieu_de(bo, txt, y=300, nen=None):
    """Tiêu đề ghim trên cùng (video mẹo nhiều bước): IN HOA, số tô vàng."""
    txt = in_hoa(txt)
    im = lop()
    tu = [(w, M("vang") if re.search(r"\d", w) else M("trang")) for w in txt.split()]
    if _ho(bo) == "but_da":
        f = vua(txt, "Black", 50, 770)
        c = cap(f)
        chu = lop()
        viet(chu, LE_TRAI + 26, y + c, tu, f)
        ImageDraw.Draw(chu).rounded_rectangle([LE_TRAI, y - 4, LE_TRAI + 9, y + c + 4], radius=4, fill=M("vang"))
        im.alpha_composite(bong_chu(chu, 8, 4, 200))
        return im, (LE_TRAI, y - 4, int(LE_TRAI + 26 + dai(txt, f)), int(y + c + 4))
    f = vua(txt, "Black", 46, 740)
    c = cap(f)
    pt = max(-bb(txt, f)[1] - c, 0.30 * f.size) + 12
    pb = 0.34 * f.size + 6
    bw = dai(txt, f) + 64
    CX = cx_cho(bw)
    box = (CX - bw / 2, y, CX + bw / 2, y + pt + c + pb)
    if _ho(bo) == "khoi":
        to_khoi(im, box, (box[3] - box[1]) / 2, "xanh", vien=3, vien_mau=_vien_trang())
    else:
        to_khoi(im, box, (box[3] - box[1]) / 2, "kinh", vien=2, vien_mau=M("trang", 140), khung=nen)
    viet(im, box[0] + 32, y + pt + c, tu, f)
    return bong(im, 12, 6, 90, ngoai=_ho(bo) == "kinh" and _trong()), tuple(int(v) for v in box)


# ================================================================ PHỤ ĐỀ (IN HOA)
Y_PD = 1290   # chân chữ phụ đề cụm (engine cũ 1272; cả hộp nền vẫn ≤ 1380)


def phu_de(bo, kieu, chu, tu_vang=(), dang_doc=None, nen=None, y_chan=Y_PD):
    """1 khung phụ đề. kieu = id trong BO[bo]['phu_de']. Loại 'cum': chu = cụm 1–3 từ; loại 'cau': chu = cả câu (≤ 2 dòng,
    '|' = chỗ ngắt), dang_doc = số thứ tự từ đang đọc (0…) -> tô theo kiểu."""
    st = kieu if isinstance(kieu, dict) else ({p["id"]: p for p in BO[bo]["phu_de"]}.get(kieu) or pd_kieu(bo, kieu))
    kd = st.get("kieu")
    chu = in_hoa(chu)
    im = lop()
    vg = M("vang")
    tr = M("trang")
    if kd == "cum_vien":
        f = vua(chu.replace("|", " "), "Black", st["co"], 790, sw=st["vien"])
        t = chu.replace("|", " ")
        x = cx_cho(dai(t, f)) - dai(t, f) / 2
        viet(im, x, y_chan, to_tu(t, tu_vang, tr, vg), f, st["vien"], M(st["vien_mau"]))
        return bong(im, 10, 6, 140), im.getbbox()
    if kd == "cum_the":
        t = chu.replace("|", " ")
        f = vua(t, "Black", st["co"], 740)
        c = cap(f)
        pt, pb, px = DAU_TREN * f.size, 0.36 * f.size, 32
        bw = dai(t, f) + 2 * px
        CX = cx_cho(bw)
        box = (CX - bw / 2, y_chan - c - pt, CX + bw / 2, y_chan + pb)
        if st.get("nen", "xanh") != "kinh":
            to_khoi(im, box, 20, "xanh", vien=2.5, vien_mau=M("trang", 150))
        else:
            to_khoi(im, box, (box[3] - box[1]) / 2, "kinh", vien=2, vien_mau=M("trang", 130), khung=nen)
        viet(im, CX - bw / 2 + px, y_chan, to_tu(t, tu_vang, tr, vg), f)
        return bong(im, 12, 7, 100, ngoai=st.get("nen") == "kinh" and _trong()), tuple(int(v) for v in box)
    if kd == "tu_khoa":   # tầng trên nhỏ trắng, tầng dưới từ khoá to vàng
        p = [x.strip() for x in chu.split("|")] if "|" in chu else [chu]
        if len(p) == 1:
            ws = p[0].split()
            p = [" ".join(ws[:-1]), ws[-1]] if len(ws) > 1 else ["", ws[0]]
        f1 = vua(p[0], "ExtraBold", st["co"][0], 760, sw=4)
        f2 = vua(p[1], "Black", st["co"][1], 800, sw=6)
        yb2 = y_chan
        yb1 = yb2 - cap(f2) - max(-bb(p[1], f2)[1] - cap(f2), 0.12 * f2.size) - 16 - max(bb(p[0], f1)[3], 4)
        CX = cx_cho(max(dai(p[0], f1), dai(p[1], f2)))
        if p[0]:
            viet(im, CX - dai(p[0], f1) / 2, yb1, [(p[0], tr)], f1, 4, M("xanh_toi"))
        viet(im, CX - dai(p[1], f2) / 2, yb2, [(p[1], vg)], f2, 6, M("xanh_toi"))
        return bong(im, 12, 7, 140), im.getbbox()
    if kd == "cau_o":   # cả câu, từ đang đọc: nền vàng bo, chữ xanh; còn lại trắng viền đen Poly
        dong, f = _chia_cau(chu, "ExtraBold", st["co"], 780, st["vien"])
        CX = cx_cho(max(dai(" ".join(d_), f) for d_ in dong) + 30)
        xs = _xep_dong([([(" ".join(d_), tr)], f, st["vien"]) for d_ in dong], x_tam=CX, y_cap=0, gap=14)
        dy = y_chan - xs[-1][1]
        k = 0
        chu_l = lop()
        for d_, (x, yb, _) in zip(dong, xs):
            x -= st["vien"]
            for w in d_:
                ww = dai(w, f)
                if k == dang_doc:
                    c = cap(f)
                    box = (x - 12, yb + dy - c - DAU_TREN * f.size + 4, x + ww + 12, yb + dy + 0.32 * f.size)
                    to_khoi(im, box, 12, "vang", vet_sang=False)
                    viet(chu_l, x, yb + dy, [(w, M("xanh"))], f)
                else:
                    col = vg if _la_vang(w, tu_vang) else tr
                    viet(chu_l, x, yb + dy, [(w, col)], f, st["vien"], M("xanh_toi"))
                x += ww + dai(" ", f)
                k += 1
        out = bong(chu_l, 9, 5, 120)   # bóng chữ nằm DƯỚI nền vàng (không làm bẩn vàng), rồi nền vàng, rồi chữ
        out.alpha_composite(bong(im, 10, 6, 90, sat=None))
        out.alpha_composite(chu_l)
        return out, out.getbbox()
    if kd == "cum_trang":
        t = chu.replace("|", " ")
        f = vua(t, "Black", st["co"], 800)
        viet(im, LE_TRAI, y_chan, to_tu(t, tu_vang, tr, vg), f)
        out = man_toi(im, 80)
        out.alpha_composite(bong_chu(im, 9, 5, 215))
        return out, im.getbbox()
    if kd == "cum_but_da":   # từ khoá trên bút dạ vàng chữ xanh (từ khoá liền nhau = 1 vệt), còn lại trắng bóng mềm; căn trái
        t = chu.replace("|", " ")
        f = vua(t, "Black", st["co"], 760)
        c = cap(f)
        sp = dai(" ", f)
        nhom = []   # [(là từ khoá, [từ…])]
        for w in t.split():
            v = _la_vang(w, tu_vang)
            if nhom and nhom[-1][0] == v:
                nhom[-1][1].append(w)
            else:
                nhom.append((v, [w]))
        x = LE_TRAI
        nen_l, chu_l = lop(), lop()
        for v, ws in nhom:
            cum = " ".join(ws)
            ww = dai(cum, f)
            if v:
                x += 14 if x > LE_TRAI else 0
                to_khoi(nen_l, (x - 14, y_chan - c - DAU_TREN * f.size + 4, x + ww + 14, y_chan + 0.32 * f.size), 10, "vang",
                        vet_sang=False)
                viet(nen_l, x, y_chan, [(cum, M("xanh"))], f)
                x += ww + 14 + sp
            else:
                viet(chu_l, x, y_chan, [(cum, tr)], f)
                x += ww + sp
        im.alpha_composite(man_toi(chu_l, 80))
        im.alpha_composite(bong(nen_l, 10, 6, 90, sat=None))
        im.alpha_composite(bong_chu(chu_l, 9, 5, 215))
        return im, im.getbbox()
    if kd == "cau_gach":   # cả câu trắng bóng mềm, từ đang đọc vàng + gạch vàng dưới; căn trái
        dong, f = _chia_cau(chu, "ExtraBold", st["co"], 800, 0)
        xs = _xep_dong([([(" ".join(d_), tr)], f, 0) for d_ in dong], x_trai=LE_TRAI, y_cap=0, gap=18)
        dy = y_chan - xs[-1][1]
        k = 0
        for d_, (x, yb, _) in zip(dong, xs):
            for w in d_:
                ww = dai(w, f)
                col = vg if (k == dang_doc or _la_vang(w, tu_vang)) else tr
                viet(im, x, yb + dy, [(w, col)], f)
                if k == dang_doc:
                    ImageDraw.Draw(im).rounded_rectangle([x, yb + dy + 0.20 * f.size, x + ww, yb + dy + 0.20 * f.size + 7],
                                                         radius=3, fill=vg)
                x += ww + dai(" ", f)
                k += 1
        out = man_toi(im, 85)
        out.alpha_composite(bong_chu(im, 9, 5, 215))
        return out, im.getbbox()
    if kd == "cau_kinh":   # cả câu trên tấm kính, từ đang đọc vàng
        dong, f = _chia_cau(chu, "ExtraBold", st["co"], 740, 0)
        CX = cx_cho(max(dai(" ".join(d_), f) for d_ in dong) + 72)
        xs = _xep_dong([([(" ".join(d_), tr)], f, 0) for d_ in dong], x_tam=CX, y_cap=0, gap=14)
        dy = y_chan - xs[-1][1]
        rong = max(r for _, _, r in xs)
        top = xs[0][1] + dy - cap(f) - DAU_TREN * f.size - 4
        box = (CX - rong / 2 - 36, top, CX + rong / 2 + 36, y_chan + 0.34 * f.size + 8)
        to_khoi(im, box, 26, "kinh", vien=2, vien_mau=M("trang", 130), khung=nen)
        k = 0
        for d_, (x, yb, _) in zip(dong, xs):
            for w in d_:
                col = vg if (k == dang_doc or _la_vang(w, tu_vang)) else tr
                viet(im, x, yb + dy, [(w, col)], f)
                x += dai(w, f) + dai(" ", f)
                k += 1
        return bong(im, 16, 8, 85, ngoai=_trong()), tuple(int(v) for v in box)
    if kd == "cum_noi":   # trắng, khối nổi lục bảo đổ chéo (dày `noi` px) + viền đen Poly mảnh
        t = chu.replace("|", " ")
        f = vua(t, "Black", st["co"], 780, sw=3)
        x = cx_cho(dai(t, f) + 10) - dai(t, f) / 2
        d = ImageDraw.Draw(im)
        for k in range(st["noi"], 0, -1):
            d.text((x + k * 0.5, y_chan + k), t, font=f, fill=M("xanh"), anchor="ls", stroke_width=3, stroke_fill=M("xanh_toi"))
        viet(im, x, y_chan, to_tu(t, tu_vang, tr, vg), f, 3, M("xanh_toi"))
        return bong(im, 12, 8, 120), im.getbbox()
    raise ValueError(kieu)


def _chia_cau(chu, dam, co, max_w, sw):
    """Câu IN HOA -> ([[từ…], [từ…]], font): '|' = chỗ ngắt; không có thì ngắt cân bằng (ve_chu.chia_dong), thu cỡ cho vừa."""
    while True:
        f = F(dam, co)
        dong = V.chia_dong(chu, lambda t: dai(t, f) + 2 * sw, max_w)
        if all(dai(d_, f) + 2 * sw <= max_w for d_ in dong) or co <= 48:
            return [d_.split() for d_ in dong], f
        co -= 2


# ---------------------------------------------------------------- hộp + hàm công khai
def _hop_dac(im):
    """Hộp vùng đục (alpha > 128): bỏ bóng mờ; hộp này dùng để kéo / hít / khung chọn và kiểm vùng an toàn."""
    a = im.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
    return tuple(int(v) for v in a) if a else (0, 0, 1, 1)


def _cong(f):
    def g(*a, **k):
        im, _ = f(*a, **k)
        return im, _hop_dac(im)
    g.__name__, g.__doc__ = f.__name__, f.__doc__
    return g


for _t in ("hook", "nhan", "the_gia", "the_ten", "the_ket", "brand", "tieu_de", "phu_de"):
    globals()[_t] = _cong(globals()[_t])


# ---------------------------------------------------------------- danh sách cho app (tab Kiểu)
def _anh(p):
    try:
        with open(p, "rb") as fo:
            return "data:image/jpeg;base64," + base64.b64encode(fo.read()).decode("ascii")
    except OSError:
        return ""


def ds_app():
    """{bo_mau_ds: [{id, ten, mo_ta, anh, phu_de: [{id, ten, loai}]}] (đầu tiên = "Cũ"), kieu_dung_ds: [{id, ten, mo_ta, anh, bo_mau,
    phu_de, kieu, sap_co}]} — ảnh nhỏ nhúng data URI (khỏi thêm đường tải)."""
    bo = [{"id": "", "ten": "Cũ", "mo_ta": "Mẫu chữ đang dùng trước đây (theo ô Kiểu chữ / Phụ đề bên dưới).",
           "anh": _anh(os.path.join(MAU_DIR, "cu.jpg")), "phu_de": []}]
    for b in BO.values():
        bo.append({"id": b["id"], "ten": b.get("ten") or b["id"], "mo_ta": b.get("mo_ta") or "",
                   "anh": _anh(os.path.join(MAU_DIR, b.get("anh") or (b["id"] + ".jpg"))),
                   "phu_de": [{"id": p["id"], "ten": p.get("ten") or p["id"], "loai": p.get("loai")} for p in b["phu_de"]]})
    kd = []
    for f in sorted(glob.glob(os.path.join(KIEU_DUNG_DIR, "*.json"))):
        try:
            with open(f, encoding="utf-8") as fo:
                x = json.load(fo)
        except (OSError, ValueError):
            continue
        if not isinstance(x, dict) or not x.get("id") or x.get("bo_mau") not in BO:
            continue
        kd.append(dict({k: x.get(k) for k in ("id", "ten", "mo_ta", "bo_mau", "phu_de", "kieu", "sap_co", "thu_tu")},
                       anh=_anh(os.path.join(KIEU_DUNG_DIR, x.get("anh_bia") or (x["id"] + ".jpg")))))
    kd.sort(key=lambda x: (x.get("thu_tu") or 99, x["id"]))
    return {"bo_mau_ds": bo, "kieu_dung_ds": kd}


# ---------------------------------------------------------------- mặt nạ kính (dựng máy chủ làm mờ cảnh dưới thẻ)
def mat_na(im, nguong=120):
    """Lớp chữ có kính -> (hộp, mặt nạ L đã cắt theo hộp): vùng alpha > nguong (thẻ / viên kính + viền + chữ; bỏ bóng mờ)."""
    m = im.getchannel("A").point(lambda v: 255 if v > nguong else 0)
    bx = m.getbbox()
    return (bx, m.crop(bx)) if bx else None


def ghi_mat_na(ds, outdir):
    """ds = [(t0, t1, (hộp, mặt nạ cắt))] -> các đoạn giờ không chồng nhau, mỗi đoạn 1 PNG mặt nạ toàn khung (gộp mọi lớp kính đang
    hiện) mo-NN.png -> [{png, t0, t1}] + hộp gộp. Đoạn không có lớp kính nào: bỏ (dung_may_chu lấp bằng mặt nạ trống)."""
    moc = sorted({round(float(t), 4) for a, b, _ in ds for t in (a, b)})
    out, hop = [], None
    for a, b in zip(moc, moc[1:]):
        dang = [x for t0, t1, x in ds if t0 < b - 1e-4 and t1 > a + 1e-4]
        if not dang or b - a < 1e-3:
            continue
        m = Image.new("L", (W, H), 0)
        for (bx, mk) in dang:
            m.paste(255, bx, mk)
            hop = bx if hop is None else (min(hop[0], bx[0]), min(hop[1], bx[1]), max(hop[2], bx[2]), max(hop[3], bx[3]))
        if out and abs(out[-1]["t1"] - a) < 1e-4 and out[-1]["_m"] == m.tobytes():   # đoạn liền nhau cùng mặt nạ: nối
            out[-1]["t1"] = b
            continue
        p = os.path.join(outdir, "mo-%02d.png" % (len(out) + 1))
        m.save(p)
        out.append({"png": p, "t0": a, "t1": b, "_m": m.tobytes()})
    for x in out:
        x.pop("_m")
    return out, (list(hop) if hop else None)

