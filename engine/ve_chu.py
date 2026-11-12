#!/usr/bin/env python3
"""Vẽ chữ trên video (PNG trong suốt 1080x1920) theo kiểu dựng. Font Be Vietnam Pro.

Dùng:  python3 ve_chu.py dong-thoi-gian.json <thu_muc_ra> [<thu_muc_font>]
Ra:    các PNG + <thu_muc_ra>/lop-chu.json: [{"png", "t0", "t1", "lop", "hop": [x0,y0,x1,y1]}]
Kiểm vùng an toàn của kênh: chữ không vượt x 950 trong khoảng y 620–1320, không thấp hơn y 1300 (trừ phụ đề ≤ 1380).
Phụ đề: vẽ PNG (Premiere dùng) + phu-de.ass tô từng từ (dựng máy chủ dùng, libass). Ngắt dòng cân bằng, tối đa 2 dòng;
muốn ngắt ở chỗ nhất định thì viết "|" trong câu (vd. "iPad Pro M4|chỉ còn [giá]"). Giờ từng từ: phu_de[].tu = [[từ, t0, t1], ...]
(lấy từ WordBoundary của edge-tts hoặc whisper); không có thì chia đều theo số ký tự.
Gu kênh @poly.store: hook "bong_bong" (bong bóng thoại xanh đậm), phụ đề "cum_ngan" (cụm 1–3 từ in hoa),
thẻ kết "the_comment"; tùy chọn chu.tieu_de (tiêu đề ghim trên cùng) và chu.nhan_chu (nhãn từ khoá vàng to).
Premiere (29/10, mặc định): lop_premiere = mỗi lớp 1 clip trên track riêng (lop_rieng), lớp có chuyển động dời về tâm khung
(*-giua.png, vi_tri = Position) + hieu_ung (HIEU_UNG_PR); lớp hiệu ứng fx-*.png (chớp trắng, tối viền, lóa sáng, thanh tiến
trình); kieu.am_nhan = co thì ghi âm nhấn am-*.wav (am_nhan.py). lop-chu.json có che_do_premiere, so_track_hinh, am_nhan.
--chu-ghep: cách cũ (ghép thành ghep-NN.png không chồng giờ, 3 track) — lệnh ra giống hệt bản 28/10.
Kiểu chữ riêng từng chữ (4/11, POLY Cut): chu.nhan_chu[i].kieu, chu.the_gia.kieu, chu.kieu_hook, chu.kieu_tieu_de = mẫu có sẵn
và / hoặc font riêng (chu_rieng.py, bảng kieu_chu.json, font OFL trong fonts/). Không có khoá = vẽ y hệt trước.
Chỗ anh kéo (10/11, POLY Cut r31): chu.vi_tri {hook, brand, tieu_de, ket: [x, y] tâm hộp chữ; phu_de: y chân chữ}, chu.nhan_chu[i].vi_tri,
chu.the_gia.vi_tri = [x, y] (khung 1080×1920) — lớp vẽ như cũ rồi dời cả lớp (_dat_cho). Không có khoá = vẽ y hệt trước.
"""
import json, os, re, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter

import chung
import chu_rieng  # kiểu chữ có sẵn + font riêng từng chữ (4/11, kieu_chu.json): không có khoá kieu = vẽ y hệt cũ
import mau_chu_moi as MCM  # bộ mẫu chữ mới (r36, 11/11: kieu.bo_mau / kiểu riêng {"bo"}): không có khoá = không gọi tới

W, H = 1080, 1920
# Bảng màu Poly Store (29/10, anh: "màu sắc tone màu của poly store") — mọi chữ / khối / thẻ / lớp hiệu ứng chỉ dùng các màu
# này (render() tự kiểm: kiem_mau). Gốc: bong bóng thoại + thẻ kết của kênh @poly.store, logo điện thoại xanh đậm viền trắng,
# sticker_poly.py. Cảnh quay giữ màu thật (khách xem màu máy) — tone Poly nằm ở lớp chữ / đồ họa, không phủ màu lên cảnh.
# Anh 29/10: "tone xanh lá màu sang hơn, đừng xanh lè" → xanh lục bảo sâu, ngả lam nhẹ, bớt gắt (không dùng xanh lá tươi
# kiểu #22C55E); khối xanh đổ dải nhẹ (sáng trên → đậm dưới) + vệt bóng mảnh mép trên (khoi_xanh) cho có chiều sâu như men / kính.
XANH_CU = (6, 78, 36)  # #064E24 xanh kênh dùng tới 28/10 (đo từ bong bóng thoại) — giữ để so
VANG = (255, 214, 0, 255)  # #FFD600 — nhấn: giá, từ khoá, dòng 2, tag, thanh tiến trình
TRANG = (255, 255, 255, 255)
DEN = (0, 0, 0, 255)  # chỉ viền chữ / bóng đổ (gu kênh: nhãn vàng viền đen)
BANG_MAU = {}


def _tron(a, b, k):
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def dat_mau_xanh(rgb):
    """Đặt cả họ xanh Poly từ 1 màu gốc: XANH (khối, chữ trên nền vàng / trắng), XANH_SANG (viền, mép sáng),
    XANH_TOI ("đen Poly": nền tối mờ, viền chữ vàng kiểu khối), XANH_TREN / XANH_DUOI (2 đầu dải của khoi_xanh)."""
    global XANH, XANH_SANG, XANH_TOI, XANH_TREN, XANH_DUOI
    XANH = tuple(rgb) + (255,)
    XANH_SANG = _tron(rgb, (255, 255, 255), 0.22) + (255,)
    XANH_TOI = _tron(rgb, (0, 0, 0), 0.55) + (255,)
    XANH_TREN = _tron(rgb, (255, 255, 255), 0.12)
    XANH_DUOI = _tron(rgb, (0, 0, 0), 0.32)
    BANG_MAU.update(xanh=XANH[:3], xanh_sang=XANH_SANG[:3], xanh_toi=XANH_TOI[:3], xanh_tren=XANH_TREN, xanh_duoi=XANH_DUOI,
                    vang=VANG[:3], trang=TRANG[:3], den=DEN[:3], vang_loa=(255, 226, 120))


XANH_POLY = (7, 77, 58)  # #074D3A xanh lục bảo sâu — màu chính từ 29/10
dat_mau_xanh(XANH_POLY)
FONT_DIR = chung.FONT_DIR  # bản máy tiệm: env POLY_FONT_DIR, không có thì <engine>/fonts (tham số thứ 3 vẫn thắng)
STICKER_DIR = os.environ.get("POLY_STICKER_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "sticker"))
HIEU_UNG = {"hook": "nay", "nhan": "nay", "sticker": "nay", "ket": "nay", "gia": "nay", "tieu_de": "mo"}  # cách hiện (dựng máy chủ)
# Premiere, chữ mỗi lớp 1 track (29/10, xu hướng 2026: chữ nào cũng có chuyển động khi hiện) — lenh_premiere.hieu_ung_chu
HIEU_UNG_PR = {"hook": "nay_dau", "nhan": "truot", "gia": "nay_manh", "ket": "len", "tieu_de": "mo", "sticker": "nay",
               "phu_de": "nay_nhe"}
CHU_GHEP = "--chu-ghep" in sys.argv  # cách cũ: ghép mọi lớp chữ thành đoạn tĩnh ghep-NN.png (V2) — đường lui khi them_track lỗi
ASS_K = 1.526  # libass: Fontsize N của Be Vietnam Pro hiện như cỡ N/1.526 px của PIL ((winAscent+winDescent)/unitsPerEm)
CHU_NHO = []  # [(chữ, cỡ px)] các dòng phải thu nhỏ dưới ngưỡng đọc được -> render() báo cảnh báo


# Bộ font (29/10, anh: "chọn một số font đẹp") — đã kiểm đủ dấu tiếng Việt (fontTools, 94 ký tự có dấu), Google Fonts OFL,
# tải từ https://raw.githubusercontent.com/google/fonts/main/ofl/<thư mục>/<file> (curl -g vì tên có [ ]). Vai trò theo độ đậm
# cũ của code: Black (dòng chính, phụ đề cụm, nhãn), ExtraBold (dòng phụ, thẻ), Bold (chữ thường kiểu tối giản). Mỗi vai trò =
# (file, độ đậm của font biến thiên | None). co = hệ số cỡ chữ (font hẹp như Anton cần to hơn mới cân). POLY STORE + phụ đề ASS
# (dựng máy chủ) luôn dùng Be Vietnam Pro.
BO_FONT = {
    "poly_goc": {"Black": ("BeVietnamPro-Black.ttf", None), "ExtraBold": ("BeVietnamPro-ExtraBold.ttf", None),
                 "Bold": ("BeVietnamPro-Bold.ttf", None), "co": 1.0, "thu_muc": "bevietnampro"},
    "tiktok_dam": {"Black": ("Montserrat[wght].ttf", 900), "ExtraBold": ("Montserrat[wght].ttf", 800),
                   "Bold": ("Montserrat[wght].ttf", 700), "co": 0.95, "thu_muc": "montserrat"},
    "cao_gon": {"Black": ("Anton-Regular.ttf", None), "ExtraBold": ("BarlowCondensed-Black.ttf", None),
                "Bold": ("BarlowCondensed-ExtraBoldItalic.ttf", None), "co": 1.16, "thu_muc": "anton|barlowcondensed"},
    "cong_nghe": {"Black": ("Kanit-Black.ttf", None), "ExtraBold": ("Kanit-ExtraBoldItalic.ttf", None),
                  "Bold": ("Kanit-Black.ttf", None), "co": 1.0, "thu_muc": "kanit"},
    "vui_tron": {"Black": ("Baloo2[wght].ttf", 800), "ExtraBold": ("PaytoneOne-Regular.ttf", None),
                 "Bold": ("Baloo2[wght].ttf", 700), "co": 1.06, "thu_muc": "baloo2|paytoneone"},
}
BO = {"ten": "poly_goc"}  # bộ đang dùng (render() đặt theo kieu.bo_font)
FONT_RIENG = {"v": None}  # font riêng của 1 chữ (chu_rieng.doi_font đặt tạm trong lúc vẽ chữ đó), dạng như BO_FONT[...]
THE_BIA = {"v": None}  # chu.the_bia của video đang vẽ (kiểu the_bia)
TEN_MAY = {}  # tên PNG nhãn -> tham số the_ten_may (dung_mov dựng lại các phần để làm MOV)
_FONT_CACHE = {}


def file_font_can(ten_bo):
    """Các file font bộ `ten_bo` cần (để dung_premiere kiểm trước khi chạy)."""
    b = BO_FONT.get(ten_bo) or BO_FONT["poly_goc"]
    return sorted({b[k][0] for k in ("Black", "ExtraBold", "Bold")} | {"BeVietnamPro-Bold.ttf", "BeVietnamPro-ExtraBold.ttf",
                                                                       "BeVietnamPro-Black.ttf"})


def font(w, s, goc=False):
    """Font vai trò w (Black / ExtraBold / Bold) cỡ s của bộ đang dùng; goc=True: luôn Be Vietnam Pro (POLY STORE, ASS)."""
    b = BO_FONT["poly_goc"] if goc else (FONT_RIENG["v"] or BO_FONT.get(BO["ten"]) or BO_FONT["poly_goc"])
    f, wght = b[w]
    co = max(8, int(round(s * (1.0 if goc else b["co"]))))
    key = (f, wght, co)
    if key not in _FONT_CACHE:
        ft = ImageFont.truetype(os.path.join(FONT_DIR, f), co)
        if wght:
            ft.set_variation_by_axes(list(wght) if isinstance(wght, tuple) else [wght])  # tuple: nhiều trục (Archivo hẹp: wght, wdth)
        _FONT_CACHE[key] = ft
    return _FONT_CACHE[key]


def fit(d, txt, weight, size, max_w, stroke=0, nho_nhat=0):
    """Thu cỡ chữ (bước 4px, tối thiểu 28) cho vừa max_w. Cỡ cuối < nho_nhat hoặc vẫn tràn -> ghi CHU_NHO."""
    while size > 28:
        f = font(weight, size)
        bb = d.textbbox((0, 0), txt, font=f, stroke_width=stroke)
        if bb[2] - bb[0] <= max_w:
            if size < nho_nhat:
                CHU_NHO.append((txt, size))
            return f, bb
        size -= 4
    f = font(weight, size)
    CHU_NHO.append((txt, size))
    return f, d.textbbox((0, 0), txt, font=f, stroke_width=stroke)


def new():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


# ---------- Dời chữ tới chỗ anh kéo (POLY Cut r31, 10/11, anh: "kéo thả các tag trong khung hình được") ----------
# Kế hoạch CHỈ THÊM khoá (không có khoá = vẽ y hệt cũ, từng byte). Toạ độ theo khung 1080×1920:
#   chu.vi_tri = {"hook": [x, y], "brand": [x, y], "tieu_de": [x, y], "ket": [x, y], "phu_de": y}   (mục nào không có = chỗ cũ)
#   chu.nhan_chu[i].vi_tri = [x, y] · chu.the_gia.vi_tri = [x, y] · sticker: x / y có sẵn (tâm sticker)
#   [x, y] = TÂM hộp chữ (hộp "hop" của lớp, như lop-chu.json); thẻ kết chỉ dùng y (luôn giữa ngang).
#   phu_de = y đường chân chữ phụ đề cả video (pd_y_goc: cụm 1272, cụm kiểu tối giản 1358, cả câu = đáy khối 1340).
# Cách vẽ: hàm vẽ chạy như cũ (chỗ mặc định) rồi dời cả lớp (ảnh toàn khung + hộp) để tâm hộp tới đúng chỗ, hộp kẹp trong khung
# (_dat_cho bọc các hàm vẽ: tham số tam / lech chỉ có khi kế hoạch có khoá -> lời gọi cũ y hệt, lớp nhớ xem trước cũng y hệt).
def lech_tam(hop, tam):
    """(dx, dy) nguyên để tâm hộp tới tam = [x | None, y | None] (None = giữ trục đó), hộp không ra ngoài khung."""
    def truc(a, b, v, M):
        if v is None:
            return 0
        d = int(round(float(v) - (a + b) / 2.0))
        lo, hi = -a, M - b
        if lo <= hi:
            d = max(int(-(-lo // 1)), min(int(hi // 1), d))
        return d
    x0, y0, x1, y1 = (float(v) for v in hop)
    return truc(x0, x1, tam[0], W), truc(y0, y1, tam[1], H)


def dich_anh(im, dx, dy):
    """Dời ảnh toàn khung (dx, dy) px, phần lọt ra ngoài khung bị cắt."""
    if not (dx or dy):
        return im
    out = Image.new(im.mode, im.size, (0, 0, 0, 0))
    out.paste(im, (int(dx), int(dy)))
    return out


def _dat_cho(ham):
    """Bọc hàm vẽ 1 lớp -> nhận thêm tam=[x, y] (tâm hộp mới) hoặc lech=[dx, dy]; không truyền = y hệt hàm cũ."""
    def boc(*a, tam=None, lech=None, **k):
        im, hop = ham(*a, **k)
        if (tam is None and lech is None) or hop is None:
            return im, hop
        if tam is not None:
            dx, dy = lech_tam(hop, tam)
        else:
            dx, dy = int(round(float(lech[0] or 0))), int(round(float(lech[1] or 0)))
        if not (dx or dy):
            return im, hop
        if isinstance(im, list):  # the_ten_may / khoi_tieu_de: các phần (lớp, vai)
            im = [(dich_anh(lp, dx, dy), v) for lp, v in im]
        else:
            im = dich_anh(im, dx, dy)
        return im, (hop[0] + dx, hop[1] + dy, hop[2] + dx, hop[3] + dy)
    boc.__name__, boc.__doc__, boc.__wrapped__ = ham.__name__, ham.__doc__, ham
    return boc


def _xy(v, chi_y=False):
    """Giá trị vị trí trong kế hoạch -> [x | None, y] (số trong khung) | None (không có / sai kiểu)."""
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            x, y = None, float(v)
        else:
            x, y = (None if v[0] is None else float(v[0])), float(v[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None
    if y != y or (x is not None and x != x):  # NaN
        return None
    x = None if chi_y or x is None else min(max(x, 0.0), float(W))
    return [x, min(max(y, 0.0), float(H))]


def dat_cho(v, chi_y=False):
    """Tham số thêm cho hàm vẽ từ 1 khoá vị trí: {"tam": [x, y]} | {} (không có khoá: lời gọi y hệt cũ)."""
    xy = _xy(v, chi_y) if v is not None else None
    return {"tam": xy} if xy else {}


def pd_y_goc(k):
    """Đường chân chữ phụ đề mặc định (khung 1080×1920) theo kiểu: cụm 1272 (sub_cum), cụm tối giản 1358, cả câu = đáy khối 1340."""
    if MCM.bo_cua(k):   # r36: bộ mẫu mới — chân chữ dòng cuối (cụm lẫn cả câu)
        return MCM.Y_PD
    if (k or {}).get("phu_de") == "cum_ngan":
        return 1358 if (k or {}).get("chu") == "toi_gian" else 1272
    return 1340


def pd_lech(tl):
    """dy (px) phụ đề cả video theo chu.vi_tri.phu_de (kẹp y 160–1880); không có khoá = 0."""
    v = ((tl.get("chu") or {}).get("vi_tri") or {}) if isinstance((tl.get("chu") or {}).get("vi_tri"), dict) else {}
    xy = _xy(v.get("phu_de"), True) if v.get("phu_de") is not None else None
    if not xy:
        return 0
    return int(round(min(max(xy[1], 160.0), 1880.0) - pd_y_goc(tl.get("kieu"))))


def nen_xanh(w, h, a=255):
    """Tấm xanh Poly kiểu sang (w×h): dải dọc XANH_TREN → XANH → XANH_DUOI (không phẳng màu), độ đục a."""
    t = np.linspace(0.0, 1.0, max(1, h), dtype=np.float32)[:, None]
    tren, giua, duoi = (np.array(c, np.float32) for c in (XANH_TREN, XANH[:3], XANH_DUOI))
    k1, k2 = np.clip(t / 0.45, 0, 1), np.clip((t - 0.45) / 0.55, 0, 1)
    mau = np.where(t < 0.45, tren + (giua - tren) * k1, giua + (duoi - giua) * k2)  # (h, 3)
    arr = np.empty((max(1, h), max(1, w), 4), np.uint8)
    arr[..., :3] = np.repeat(mau[:, None, :], max(1, w), axis=1).astype(np.uint8)
    arr[..., 3] = a
    return Image.fromarray(arr, "RGBA")


SS = 4  # vẽ hình ở 4× rồi thu nhỏ (LANCZOS) = khử răng cưa mép khối / đuôi bong bóng / viên (29/10: anh chê "thô")


def _mask_ss(w, h, ve):
    """Mặt nạ L (w×h) khử răng cưa: ve(draw, k) vẽ hình ở tỉ lệ k (toạ độ gốc × k), fill 255."""
    m = Image.new("L", (max(1, w) * SS, max(1, h) * SS), 0)
    ve(ImageDraw.Draw(m), SS)
    return m.resize((max(1, w), max(1, h)), Image.LANCZOS)


def _rr(x0, y0, x1, y1, r):
    """Hàm vẽ hình chữ nhật bo góc (toạ độ cục bộ) cho _mask_ss."""
    return lambda d, k: d.rounded_rectangle([x0 * k, y0 * k, x1 * k, y1 * k], radius=max(1, r * k), fill=255)


def khoi(im, box, radius, mau=None, a=255, vien=0, vien_mau=TRANG, bong_sang=True, them=None, them_hop=None):
    """Khối bo góc kiểu sang, khử răng cưa, vẽ lên im (tại chỗ).
    mau=None: xanh Poly đổ dải chéo (sáng góc trên trái → đậm góc dưới phải) + quầng sáng mềm nửa trên; có mau: màu phẳng.
    Viền: vien > 0 = viền MẢNH vien px (mặc định trắng mờ ~45%) thay viền trắng dày kiểu sticker. them(d, k, ox, oy):
    vẽ thêm vào hình (vd. đuôi bong bóng), toạ độ toàn khung; them_hop = hộp bao phần thêm (để khung vẽ đủ rộng)."""
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    le = int(vien) + 2
    X0, Y0, X1, Y1 = x0 - le, y0 - le, x1 + le, y1 + le
    if them_hop:
        X0, Y0 = min(X0, int(them_hop[0]) - le), min(Y0, int(them_hop[1]) - le)
        X1, Y1 = max(X1, int(them_hop[2]) + le), max(Y1, int(them_hop[3]) + le)
    w, h = X1 - X0 + 1, Y1 - Y0 + 1
    bx0, by0, bx1, by1 = x0 - X0, y0 - Y0, x1 - X0, y1 - Y0

    def hinh(inset):
        def ve(d, k):
            _rr(bx0 + inset, by0 + inset, bx1 - inset, by1 - inset, max(1, radius - inset))(d, k)
            if them:
                them(d, k, X0, Y0, inset)
        return ve
    m = _mask_ss(w, h, hinh(0))
    if mau is None:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        t = np.clip(0.78 * (yy - by0) / max(1, by1 - by0) + 0.22 * (xx - bx0) / max(1, bx1 - bx0), 0, 1)[..., None]
        tren, giua, duoi = (np.array(c, np.float32) for c in (XANH_TREN, XANH[:3], XANH_DUOI))
        mau_ = np.where(t < 0.42, tren + (giua - tren) * (t / 0.42), giua + (duoi - giua) * ((t - 0.42) / 0.58))
        if bong_sang:  # quầng sáng mềm nửa trên (như ánh đèn trên men), không vạch cứng
            g = np.clip(1 - (yy - by0) / (0.55 * max(1, by1 - by0)), 0, 1) ** 2 * 0.10
            mau_ = mau_ + (255 - mau_) * g[..., None]
        arr = np.empty((h, w, 4), np.uint8)
        arr[..., :3] = np.clip(mau_, 0, 255).astype(np.uint8)
        arr[..., 3] = 255
        tam = Image.fromarray(arr, "RGBA")
    else:
        tam = Image.new("RGBA", (w, h), tuple(mau[:3]) + (255,))
    tam.putalpha(m.point(lambda v: v * a // 255))
    if vien:  # viền mảnh = hình ngoài trừ hình thu vào `vien` px
        trong = _mask_ss(w, h, hinh(vien))
        vm = tuple(vien_mau[:3]), (vien_mau[3] if len(vien_mau) > 3 and vien_mau[3] < 255 else 115)
        ring = ImageChops.subtract(m, trong).point(lambda v: v * vm[1] // 255)
        lp = Image.new("RGBA", (w, h), vm[0] + (0,))
        lp.putalpha(ring)
        tam.alpha_composite(lp)
    im.alpha_composite(tam, (X0, Y0))


def khoi_xanh(im, box, radius, a=245, vien=0, vien_mau=TRANG, bong_sang=True):
    """Khối xanh Poly (tương thích tên cũ): khoi(mau=None). vien cũ (5–7 px trắng đặc) -> viền mảnh 2,5 px trắng mờ."""
    khoi(im, box, radius, None, a=a, vien=2.5 if vien else 0, vien_mau=(255, 255, 255, 120), bong_sang=bong_sang)


def bong_noi(im, dam=1.0):
    """Bóng đổ 2 lớp kiểu sang: bóng xa mềm (mờ 22, lệch 14) + bóng sát (mờ 4, lệch 3) — khối như nổi trên cảnh."""
    a = im.split()[-1]
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for mo, dy, d0 in ((22, 14, 95), (4, 3, 70)):
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", im.size, XANH_TOI[:3] + (int(d0 * dam),)), (0, dy), a.filter(ImageFilter.GaussianBlur(mo)))
        out.alpha_composite(sh)
    out.alpha_composite(im)
    return out


def _mau_hop_le():
    """Các màu được phép (RGB): bảng màu + dải xanh của khoi_xanh + dải đó pha vệt bóng trắng."""
    ds = [BANG_MAU[k] for k in ("xanh", "xanh_sang", "xanh_toi", "vang", "trang", "den")]
    tren, giua, duoi = (np.array(c, np.float32) for c in (XANH_TREN, XANH[:3], XANH_DUOI))
    for t in np.linspace(0, 1, 33):
        g = tren + (giua - tren) * min(1, t / 0.45) if t < 0.45 else giua + (duoi - giua) * (t - 0.45) / 0.55
        for k in (0, 0.1, 0.2, 0.3):
            ds.append(tuple(g + (255 - g) * k))
    return np.array(ds, np.float32)


def kiem_mau(im, ten, nguong=14, ti_le=0.02):
    """Soát lớp chữ có màu ngoài bảng màu Poly. Chỉ xét vùng màu PHẲNG (điểm đục mà 4 điểm kề cùng màu ±4: lòng chữ,
    thân hộp, khối xanh đổ dải) — bỏ viền chữ / mép (màu pha). Gom theo ô 4 mức, bỏ xám / trắng / đen; ô nào chiếm ≥ ti_le
    số điểm phẳng có màu mà cách màu hợp lệ gần nhất (_mau_hop_le) > nguong → báo. Trả danh sách cảnh báo."""
    a = np.asarray(im.convert("RGBA")).astype(np.int16)
    rgb, al = a[..., :3], a[..., 3]
    phang = al >= 200
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nb = np.roll(np.roll(a, dy, 0), dx, 1)
        phang &= (np.abs(nb[..., :3] - rgb).max(-1) <= 4) & (nb[..., 3] >= 200)
    px = rgb[phang].astype(np.int32)
    px = px[(px.max(1) - px.min(1)) >= 36] if len(px) else px
    if len(px) < 300:
        return []
    q = px // 4
    key = q[:, 0] * 4096 + q[:, 1] * 64 + q[:, 2]
    u, c = np.unique(key, return_counts=True)
    ref = _mau_hop_le()
    loi = []
    for k_, n in zip(u, c):
        if n / len(px) < ti_le:
            continue
        m = np.array([(k_ // 4096) * 4 + 2, (k_ // 64 % 64) * 4 + 2, (k_ % 64) * 4 + 2], np.float32)
        dmin = float(np.sqrt(((ref - m) ** 2).sum(1)).min())
        if dmin > nguong:
            loi.append((n / len(px), "#%02X%02X%02X" % tuple(int(v) for v in m), dmin))
    loi.sort(reverse=True)
    return [f"{ten}: màu {m} chiếm {p * 100:.0f}% vùng màu (lệch bảng màu Poly {d:.0f}) — dùng XANH / VANG / TRANG"
            for p, m, d in loi[:3]]


def bong_mem(im, dx=5, dy=9, mo=10, dam=120):
    """Thêm bóng đổ mềm dưới mọi nét đã vẽ (chữ, khối) cho chữ nổi khỏi nền, bớt cảm giác dán phẳng."""
    a = im.split()[-1]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", im.size, (0, 0, 0, dam)), (dx, dy), a.filter(ImageFilter.GaussianBlur(mo)))
    sh.alpha_composite(im)
    return sh


def block(lines, style, y0, max_w=820, cx=540, sizes=(92, 74), kieu=None, bo=None, _v=None):
    """Vẽ khối 1–2 dòng theo kiểu chữ. Trả (ảnh, hộp bao). kieu: kiểu riêng của hook (chu_rieng.py). bo: bộ mẫu mới (r36)."""
    if bo:
        return MCM.hook(bo, lines, max(int(y0), 296))   # dưới POLY STORE của bộ mới (y 226)
    if kieu:
        return chu_rieng.goi(sys.modules[__name__], kieu, "hook", block, (lines, style, y0, max_w, cx, sizes), lines,
                             y=y0, cx=cx, sizes=sizes)
    if style == "bong_bong":
        return bubble(lines, y0, min(max_w, 800), cx, sizes)
    if style == "vang_tieu_de":
        return tieu_de_vang(lines, y0, max_w, cx, sizes)
    if style == "toi_gian":
        return tieu_de_toi_gian(lines, y0, max_w, cx, sizes)
    if style in KIEU_KHOI:
        phan, hop = khoi_tieu_de(lines, style, y0, max(max_w, 860), cx, THE_BIA.get("v"))
        return ghep_phan(phan), hop
    im, d = new()
    boxes = []
    y = y0
    for i, txt in enumerate(lines):
        big = i == 0
        size = sizes[0] if big else sizes[1]
        if style == "vien_den":
            f, bb = fit(d, txt, "Black", size, max_w, 9)
            x = cx - (bb[2] - bb[0]) // 2 - bb[0]
            d.text((x, y - bb[1]), txt, font=f, fill=TRANG if big else VANG, stroke_width=9, stroke_fill=DEN)
            boxes.append((x + bb[0], y, x + bb[2], y + bb[3] - bb[1]))
            y += bb[3] - bb[1] + 26
        elif style in ("dai_trang", "nen_xanh"):
            f, bb = fit(d, txt, "Black" if big else "ExtraBold", size - 6, max_w - 60)
            tw, th = bb[2] - bb[0], bb[3] - bb[1]
            pad_x, pad_y = 30, 20
            bx0, by0 = cx - tw // 2 - pad_x, y
            bx1, by1 = cx + tw // 2 + pad_x, y + th + 2 * pad_y
            if style == "nen_xanh":
                khoi(im, (bx0, by0, bx1, by1), 24, None, a=245, vien=2.5, vien_mau=(255, 255, 255, 110))
            else:
                khoi(im, (bx0, by0, bx1, by1), 24, (255, 255, 255, 245) if big else VANG)
            d = ImageDraw.Draw(im)
            fg = XANH if style == "dai_trang" else TRANG  # nền trắng / vàng: chữ xanh đậm Poly (trước 29/10: đen)
            d.text((cx - tw // 2 - bb[0], y + pad_y - bb[1]), txt, font=f, fill=fg)
            boxes.append((bx0, by0, bx1, by1))
            y = by1 + 14
        else:  # vang_tieu_de
            f, bb = fit(d, txt, "Black" if big else "Bold", size + (8 if big else -10), max_w, 0)
            x = cx - (bb[2] - bb[0]) // 2 - bb[0]
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((x + 5, y - bb[1] + 6), txt, font=f, fill=(0, 0, 0, 200))
            sh = sh.filter(ImageFilter.GaussianBlur(6))
            im.alpha_composite(sh)
            d = ImageDraw.Draw(im)
            d.text((x, y - bb[1]), txt, font=f, fill=VANG if big else TRANG, stroke_width=2, stroke_fill=(0, 0, 0, 255))
            boxes.append((x + bb[0], y, x + bb[2], y + bb[3] - bb[1]))
            y += bb[3] - bb[1] + 22
    hop = (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))
    if style != "vang_tieu_de":  # vang_tieu_de đã có bóng riêng
        im = bong_mem(im, 4, 8, 9, 110)
    return im, hop


KIEU_KHOI = ("nhan_lon", "hop_doi", "vang_pill", "the_bia")  # 29/10: 4 kiểu khối theo mẫu anh gửi


def sao4(d, cx, cy, r, fill):
    """Ngôi sao 4 cánh lấp lánh (vẽ tay)."""
    k = r * 0.28
    d.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r), (cx - k, cy + k), (cx - r, cy),
               (cx - k, cy - k)], fill=fill)


def _hop_chu(txt, f, y, cx, pad_x, pad_y, bg, fg, radius, vien=0, vien_mau=TRANG, nghieng=0, stroke=0, stroke_mau=DEN):
    """1 hộp nền + chữ trên lớp riêng (khử răng cưa). nghieng: lệch ngang (px) cạnh trên so với cạnh dưới (hình bình
    hành). Hộp xanh Poly = đổ dải; màu khác = phẳng. Trả (lớp, hộp)."""
    im, d = new()
    bb = d.textbbox((0, 0), txt, font=f, stroke_width=stroke)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    x0, y0, x1, y1 = cx - tw // 2 - pad_x, y, cx + tw // 2 + pad_x, y + th + 2 * pad_y
    if nghieng:
        w_, h_ = x1 - x0 + 2 * abs(nghieng) + 4, y1 - y0 + 4
        ox, oy = x0 - abs(nghieng) - 2, y0 - 2
        m = _mask_ss(w_, h_, lambda dd, k: dd.polygon([((x0 + nghieng - ox) * k, (y0 - oy) * k), ((x1 + nghieng - ox) * k, (y0 - oy) * k),
                                                      ((x1 - nghieng - ox) * k, (y1 - oy) * k), ((x0 - nghieng - ox) * k, (y1 - oy) * k)], fill=255))
        lp = Image.new("RGBA", (w_, h_), tuple(bg[:3]) + (0,))
        lp.putalpha(m.point(lambda v: v * (bg[3] if len(bg) > 3 else 255) // 255))
        im.alpha_composite(lp, (ox, oy))
    else:
        xanh = tuple(bg[:3]) == XANH[:3]
        khoi(im, (x0, y0, x1, y1), radius, None if xanh else bg, a=bg[3] if len(bg) > 3 else 255,
             vien=2.5 if vien else 0, vien_mau=(255, 255, 255, 120) if vien else vien_mau)
    d = ImageDraw.Draw(im)
    d.text((cx - tw // 2 - bb[0], y + pad_y - bb[1]), txt, font=f, fill=fg, stroke_width=stroke, stroke_fill=stroke_mau)
    return im, (x0 - vien - abs(nghieng), y0 - vien, x1 + vien + abs(nghieng), y1 + vien)


def _chu_vien(txt, f, y, cx, fill, stroke, stroke_mau=DEN, ngoai=0, ngoai_mau=TRANG):
    """Chữ to viền dày (ngoai > 0: thêm viền ngoài màu khác, kiểu sticker). Trả (lớp, hộp)."""
    im, d = new()
    sw = stroke + ngoai
    bb = d.textbbox((0, 0), txt, font=f, stroke_width=sw)
    x = cx - (bb[2] - bb[0]) // 2 - bb[0]
    if ngoai:
        d.text((x, y - bb[1]), txt, font=f, fill=ngoai_mau, stroke_width=sw, stroke_fill=ngoai_mau)
    d.text((x, y - bb[1]), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_mau)
    return im, (x + bb[0], y, x + bb[2], y + bb[3] - bb[1])


def khoi_tieu_de(lines, style, y0, max_w=860, cx=540, the_bia=None):
    """4 kiểu khối tiêu đề theo mẫu anh gửi 29/10. Trả (các phần [(lớp RGBA toàn khung, vai)], hộp bao).
    vai: 'chinh' (dòng lớn, có vệt sáng), 'phu' (dòng / nhãn phụ), 'sao' (trang trí lấp lánh).
    - nhan_lon: dòng nhỏ chữ đen trên nhãn trắng bo tròn + dòng chính VÀNG IN HOA viền tối, 3 sao lấp lánh
    - hop_doi: dòng 1 chữ đen trên hộp vàng, dòng 2 chữ trắng trên hộp xanh đậm Poly viền trắng (font cao gọn của bộ)
    - vang_pill: dòng chính VÀNG IN HOA viền đen to + dòng 2 chữ đen IN HOA trên viên thuốc vàng
    - the_bia: tag vàng hình bình hành + hộp xanh đậm chữ trắng IN HOA rất to + thanh thông số '11 INCH | 256GB | 4G'
      (chu.the_bia = {tag, ten, thong_so[]} — thông số lấy từ kho, không bịa; thiếu thì lấy dòng hook)."""
    _, d = new()
    phan, hops = [], []
    L = [str(x) for x in lines if str(x).strip()]
    if style == "nhan_lon":
        nho, lon = (L[0], L[1]) if len(L) > 1 else (None, L[0])
        y = y0
        if nho:
            f = fit(d, nho, "ExtraBold", 50, max_w - 80, 0, nho_nhat=38)[0]
            im, h = _hop_chu(nho, f, y, cx, 30, 14, (255, 255, 255, 245), XANH, 40)
            phan.append((im, "phu")); hops.append(h); y = h[3] - 6
        f = fit(d, in_hoa(lon), "Black", 118, max_w, 10, nho_nhat=70)[0]
        im, h = _chu_vien(in_hoa(lon), f, y + 4, cx, VANG, 10, XANH_TOI, ngoai=5, ngoai_mau=(255, 255, 255, 230))
        phan.append((im, "chinh")); hops.append(h)
        sim, sd = new()
        x0, yy0, x1, yy1 = h
        for (sx, sy, r, c) in ((x0 - 34, yy0 + 18, 26, TRANG), (x1 + 26, yy0 - 10, 20, VANG), (x1 + 6, yy1 + 8, 16, TRANG)):
            sao4(sd, sx, sy, r, c)
        phan.append((sim, "sao"))
        hops.append((x0 - 62, yy0 - 32, x1 + 48, yy1 + 26))
    elif style == "hop_doi":
        L = [ten_dung(x) if la_ten_may(x) else x for x in L]  # "iPad mini 4", không "iPad Mini 4"
        y = y0
        if len(L) > 1:
            f = fit(d, L[0], "ExtraBold", 66, max_w - 80, 0, nho_nhat=44)[0]
            im, h = _hop_chu(L[0], f, y, cx, 26, 10, VANG, XANH, 8)
            phan.append((im, "phu")); hops.append(h); y = h[3] + 10
        f = fit(d, L[-1], "Black", 100, max_w - 90, 0, nho_nhat=60)[0]
        im, h = _hop_chu(L[-1], f, y, cx, 34, 16, XANH[:3] + (240,), TRANG, 10, vien=5)
        phan.append((im, "chinh")); hops.append(h)
    elif style == "vang_pill":
        f = fit(d, in_hoa(L[0]), "Black", 116, max_w, 9, nho_nhat=70)[0]
        im, h = _chu_vien(in_hoa(L[0]), f, y0, cx, VANG, 9)
        phan.append((im, "chinh")); hops.append(h)
        if len(L) > 1:
            f2 = fit(d, in_hoa(L[1]), "ExtraBold", 56, max_w - 100, 0, nho_nhat=40)[0]
            im2, h2 = _hop_chu(in_hoa(L[1]), f2, h[3] + 14, cx, 36, 12, VANG, XANH, 60)
            phan.append((im2, "phu")); hops.append(h2)
    elif style == "the_bia":  # 29/10: dùng thẻ tên máy (the_ten_may) — tên đúng kiểu hãng, phần đời vàng, viên thông số
        tb = the_bia or {}
        ten = str(tb.get("ten") or L[0])
        tag = tb.get("tag") or (L[1] if len(L) > 1 and not tb else None)
        ts = tb.get("thong_so") or []
        if not ts and len(L) > 1 and tb:
            ts = [x.strip() for x in re.split(r"[|·•]", L[1]) if x.strip()]
        return the_ten_may(ten, tag, ts, y0 + (24 if tag else 0), cx, max_w, 104)
    hop = (min(b[0] for b in hops), min(b[1] for b in hops), max(b[2] for b in hops), max(b[3] for b in hops))
    return phan, hop


# ---------- Thẻ tên máy (29/10, anh: "mấy đoạn có tên sản phẩm design sao cho đẹp tí") ----------
# Khối xanh lục bảo viền trắng (khoi_xanh) · tab vàng góc trên trái (tình trạng máy) · tên máy viết ĐÚNG kiểu hãng
# ("iPad Pro", "iPad mini", "MacBook Air" — không "IPAD PRO"), phần đời / chip / năm tô vàng · gạch vàng mảnh · hàng viên
# thông số trắng có icon (bộ nhớ, mạng, pin, màn, chip). Thông số CHỈ lấy từ kho (chu.the_bia / nhan_chu[].thong_so).
TEN_HANG = [("macbook", "MacBook"), ("airpods", "AirPods"), ("apple pencil", "Apple Pencil"), ("apple watch", "Apple Watch"),
            ("ipad", "iPad"), ("iphone", "iPhone"), ("imac", "iMac"), ("mac mini", "Mac mini"), ("thinkpad", "ThinkPad"),
            ("zenbook", "ZenBook"), ("vivobook", "VivoBook"), ("galaxy", "Galaxy"), ("surface", "Surface")]
TU_HANG = {"pro": "Pro", "air": "Air", "max": "Max", "plus": "Plus", "ultra": "Ultra", "mini": "mini", "gen": "Gen", "se": "SE",
           "inch": "inch", "tab": "Tab", "book": "Book"}
RE_TEN_MAY = re.compile(r"\b(ipad|iphone|macbook|imac|mac mini|airpods|apple pencil|apple watch|thinkpad|dell|hp|asus|lenovo|"
                        r"acer|msi|surface|galaxy|xiaomi|zenbook|vivobook|latitude|xps|elitebook|probook)\b", re.I)


def ten_dung(ten):
    """Viết tên máy đúng kiểu hãng: 'IPAD PRO 2018' -> 'iPad Pro 2018', 'ipad mini 6' -> 'iPad mini 6', 'M2' giữ nguyên."""
    out = str(ten).strip()
    for thuong, dung in TEN_HANG:
        out = re.sub(r"(?i)\b" + re.escape(thuong) + r"\b", dung, out)
    tu = []
    for w in out.split():
        lw = w.lower()
        if any(w == d for _, d in TEN_HANG) or re.match(r"^[A-Z]\d", w):  # tên hãng đã chuẩn / M2, A15…
            tu.append(w)
        elif lw in TU_HANG:
            tu.append(TU_HANG[lw])
        elif re.match(r"^m\d+$", lw):
            tu.append(w.upper())
        elif w.isupper() and len(w) > 2 and not re.search(r"\d", w):  # chữ thường bị in hoa: HÀNG -> Hàng
            tu.append(w.capitalize())
        else:
            tu.append(w)
    return " ".join(tu)


def tach_doi(ten):
    """'iPad Pro 2018' -> ('iPad Pro', '2018'); 'MacBook Air M2' -> ('MacBook Air', 'M2'); 'iPhone 15 Pro Max' ->
    ('iPhone 15', 'Pro Max'); không có phần nhấn -> (ten, '')."""
    m = re.match(r"^(.*?\S)\s+((?:\(?\d{4}\)?|M\d+(?:\s+(?:Pro|Max|Ultra))?|Gen\s*\d+|\d{1,2}(?:[.,]\d)?)(?:\s+\d{4})?)$", ten)
    if m and len(m.group(1)) >= 3:
        return m.group(1), m.group(2)
    m = re.match(r"^(.*?\S)\s+((?:Pro Max|Pro|Plus|Max|Ultra|mini|SE))$", ten)
    if m and re.search(r"\d", m.group(1)):
        return m.group(1), m.group(2)
    return ten, ""


def _icon(d, kieu, x, cy, h, mau):
    """Icon nhỏ (cao h) vẽ tay, căn giữa dọc tại cy, mép trái x. Trả bề rộng đã dùng."""
    w = int(h * 1.0)
    y0, y1 = cy - h / 2, cy + h / 2
    lw = max(3, int(h / 9))
    if kieu == "bo_nho":  # con chip có chân
        d.rounded_rectangle([x + h * .18, y0 + h * .18, x + h * .82, y1 - h * .18], radius=h * .1, outline=mau, width=lw)
        for k in range(3):
            yy = y0 + h * (.32 + .18 * k)
            d.line([(x, yy), (x + h * .18, yy)], fill=mau, width=lw)
            d.line([(x + h * .82, yy), (x + h, yy)], fill=mau, width=lw)
    elif kieu == "mang":  # 4 vạch sóng
        for k in range(4):
            bh = h * (.3 + .23 * k)
            d.rounded_rectangle([x + k * h * .26, y1 - bh, x + k * h * .26 + h * .17, y1], radius=2, fill=mau)
    elif kieu == "pin":
        d.rounded_rectangle([x, y0 + h * .2, x + h * .86, y1 - h * .2], radius=h * .12, outline=mau, width=lw)
        d.rectangle([x + h * .88, cy - h * .12, x + h, cy + h * .12], fill=mau)
        d.rectangle([x + lw + 3, y0 + h * .2 + lw + 3, x + h * .62, y1 - h * .2 - lw - 3], fill=mau)
    elif kieu == "man":  # màn hình + đường chéo
        d.rounded_rectangle([x, y0 + h * .1, x + h * .78, y1 - h * .1], radius=h * .1, outline=mau, width=lw)
        d.line([(x + h * .2, y1 - h * .3), (x + h * .58, y0 + h * .3)], fill=mau, width=lw)
    elif kieu == "chip":
        d.rounded_rectangle([x + h * .1, y0 + h * .1, x + h * .9, y1 - h * .1], radius=h * .18, fill=mau)
    else:  # chấm
        d.ellipse([x + h * .3, cy - h * .2, x + h * .7, cy + h * .2], fill=mau)
    return w


def kieu_icon(txt):
    t = txt.lower()
    if re.search(r"\d+\s*(gb|tb)\b", t):
        return "bo_nho"
    if re.search(r"\b(4g|5g|lte|wi-?fi|cellular|sim)\b", t):
        return "mang"
    if "pin" in t or re.search(r"\d+\s*%", t):
        return "pin"
    if re.search(r"inch|\"|\bin\b|hz", t):
        return "man"
    if re.search(r"\b(m\d|a\d+|chip|core|ryzen)\b", t):
        return "chip"
    return "cham"


def _vien_thong_so(txt, f, cx, y, h=62):
    """1 viên thông số trắng: icon + chữ xanh. Trả (lớp, hộp)."""
    im, d = new()
    bb = d.textbbox((0, 0), txt, font=f)
    tw = bb[2] - bb[0]
    ih = int(h * 0.5)
    w = 22 + ih + 12 + tw + 26
    x0 = int(cx - w / 2)
    khoi(im, (x0, y, x0 + w, y + h), h // 2, (255, 255, 255, 240))
    ic, di = Image.new("RGBA", (ih * SS + 8 * SS, h * SS), (0, 0, 0, 0)), None
    di = ImageDraw.Draw(ic)
    _icon(di, kieu_icon(txt), 2 * SS, h * SS / 2, ih * SS, XANH)
    ic = ic.resize((ih + 8, h), Image.LANCZOS)
    im.alpha_composite(ic, (x0 + 20, y))
    d = ImageDraw.Draw(im)
    d.text((x0 + 22 + ih + 12 - bb[0], y + (h - (bb[3] - bb[1])) / 2 - bb[1]), txt, font=f, fill=XANH)
    return im, (x0, y, x0 + w, y + h), w


def the_ten_may(ten, tag=None, thong_so=None, y0=700, cx=540, max_w=880, co=100, kieu=None):
    """Thẻ tên máy. Trả (phần [(lớp RGBA toàn khung, vai)], hộp). vai: 'the' (khối), 'ten' (tên trắng), 'nhan' (phần vàng),
    'gach' (gạch vàng), 'tag', 'chip0', 'chip1'… (viên thông số, theo thứ tự hiện). kieu: font riêng (chu_rieng.py)."""
    if kieu:
        return chu_rieng.goi(sys.modules[__name__], kieu, "ten_may", the_ten_may, (ten, tag, thong_so, y0, cx, max_w, co), [ten],
                             y=y0, co=co)
    _, d = new()
    ten = ten_dung(ten)
    trang_, vang_ = tach_doi(ten)
    ts = [ten_dung(x) if RE_TEN_MAY.search(str(x)) else str(x).strip() for x in (thong_so or []) if str(x).strip()][:4]
    pad_x, pad_top, pad_bot = 60, 50 if tag else 38, 38
    # tên: 1 dòng, trắng + vàng (cách 1 khoảng), thu cỡ cho vừa
    co_t = co
    while True:
        f = font("ExtraBold", co_t)
        w1 = d.textlength(trang_, font=f)
        w2 = d.textlength(" " + vang_, font=f) if vang_ else 0
        if w1 + w2 <= max_w - 2 * pad_x or co_t <= 64:
            break
        co_t -= 4
    if co_t < 72:
        CHU_NHO.append((ten, co_t))
    bb = d.textbbox((0, 0), trang_ + (" " + vang_ if vang_ else ""), font=f)
    th = bb[3] - bb[1]
    # viên thông số: cỡ chữ thu tới khi cả hàng vừa
    hang, co_c, h_c = [], 36, 60
    while ts:
        fc = font("Bold", co_c)
        rong = [22 + int(h_c * .5) + 12 + (d.textbbox((0, 0), x, font=fc)[2] - d.textbbox((0, 0), x, font=fc)[0]) + 26 for x in ts]
        if sum(rong) + 14 * (len(ts) - 1) <= max_w - 2 * pad_x + 20 or co_c <= 30:
            hang = list(zip(ts, rong))
            break
        co_c -= 2
        h_c = max(50, h_c - 2)
    gach_h, gap1, gap2 = 4, 20, 24
    noi_dung_w = max(w1 + w2, sum(r for _, r in hang) + 14 * max(0, len(hang) - 1))
    bw = int(min(max_w, noi_dung_w + 2 * pad_x))
    bh = int(pad_top + th + gap1 + gach_h + (gap2 + h_c if hang else 0) + pad_bot)
    x0, y1 = int(cx - bw / 2), int(y0 + bh)
    phan = []
    the, _ = new()
    khoi(the, (x0, y0, x0 + bw, y1), 36, None, a=246, vien=2.5, vien_mau=(255, 255, 255, 120))
    phan.append((the, "the"))
    yt = y0 + pad_top
    xt = cx - (w1 + w2) / 2
    lt, dt = new()
    dt.text((xt - bb[0], yt - bb[1]), trang_, font=f, fill=TRANG)
    phan.append((lt, "ten"))
    if vang_:
        lv, dv = new()
        dv.text((xt + w1 + d.textlength(" ", font=f) - bb[0], yt - bb[1]), vang_, font=f, fill=VANG)
        phan.append((lv, "nhan"))
    yg = yt + th + gap1
    lg, dg = new()
    dg.line([(x0 + 44, yg + gach_h // 2), (x0 + bw - 44, yg + gach_h // 2)], fill=(255, 255, 255, 60), width=2)
    phan.append((lg, "gach"))
    if hang:
        yc = yg + gach_h + gap2
        tong = sum(r for _, r in hang) + 14 * (len(hang) - 1)
        xc = cx - tong / 2
        fc = font("Bold", co_c)
        for i, (x, r) in enumerate(hang):
            lc, _, _ = _vien_thong_so(x, fc, xc + r / 2, yc, h_c)
            phan.append((lc, f"chip{i}"))
            xc += r + 14
    hop = [x0 - 4, y0 - 4, x0 + bw + 4, y1 + 4]
    if tag:
        tg = ten_dung(str(tag)).upper() if not re.search(r"[a-z]", str(tag)) else str(tag).upper()
        ft = font("ExtraBold", 30)
        sp = 2  # giãn chữ
        tb = d.textbbox((0, 0), tg, font=ft)
        tw_ = sum(d.textlength(c, font=ft) + sp for c in tg) - sp
        th_ = tb[3] - tb[1]
        lx0, ly0 = x0 + 40, y0 - th_ // 2 - 12
        ltag, _ = new()
        khoi(ltag, (lx0, ly0, lx0 + tw_ + 44, ly0 + th_ + 24), (th_ + 24) // 2, VANG)
        dtag = ImageDraw.Draw(ltag)
        xx = lx0 + 22
        for ch in tg:
            dtag.text((xx, ly0 + 12 - tb[1]), ch, font=ft, fill=XANH)
            xx += d.textlength(ch, font=ft) + sp
        phan.append((ltag, "tag"))
        hop[1] = min(hop[1], ly0)
    return phan, tuple(int(v) for v in hop)


def la_ten_may(txt):
    return bool(RE_TEN_MAY.search(str(txt)))


def ghep_phan(phan, bong=True):
    im, _ = new()
    for lp, _v in phan:
        im.alpha_composite(lp)
    return bong_noi(im) if bong else im


def tieu_de_vang(lines, y0, max_w=820, cx=540, sizes=(92, 74)):
    """Tiêu đề trên tấm xanh Poly (đổ dải, viền mảnh, khử răng cưa): dòng 1 vàng ExtraBold, dòng 2 trắng Bold — chữ
    trong khối không viền đen (29/10: bỏ kiểu viền dày cho đỡ thô), bóng nổi 2 lớp."""
    im, d = new()
    pad_x, pad_y, gap = 52, 30, 12
    rows = []
    for i, txt in enumerate(lines):
        big = i == 0
        size = sizes[0] + 4 if big else max(sizes[1] - 4, 64 if sizes[1] >= 70 else 0)
        f, bb = fit(d, txt, "ExtraBold" if big else "Bold", size, max_w - 2 * pad_x, 0, nho_nhat=60 if big else 52)
        rows.append((txt, f, bb, big))
    tw = max(bb[2] - bb[0] for _, _, bb, _ in rows)
    th = sum(bb[3] - bb[1] for _, _, bb, _ in rows) + gap * (len(rows) - 1)
    bx0, by0, bx1, by1 = cx - tw // 2 - pad_x, y0, cx + tw // 2 + pad_x, y0 + th + 2 * pad_y
    khoi(im, (bx0, by0, bx1, by1), 34, None, a=240, vien=2.5, vien_mau=(255, 255, 255, 110))
    d = ImageDraw.Draw(im)
    y = y0 + pad_y
    for txt, f, bb, big in rows:
        x = cx - (bb[2] - bb[0]) // 2 - bb[0]
        d.text((x, y - bb[1]), txt, font=f, fill=VANG if big else TRANG)
        y += bb[3] - bb[1] + gap
    return bong_noi(im), (bx0, by0, bx1, by1)


def bong_dam(im, blur=7, dy=4, dam=225):
    """Bóng mềm đậm sát chữ (kiểu tối giản: không viền, chỉ bóng) — đọc được cả trên nền sáng."""
    a = im.split()[-1].filter(ImageFilter.GaussianBlur(blur)).point(lambda v: min(255, int(v * dam / 255 * 1.6)))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(a)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, dy))
    out.alpha_composite(im)
    return out


def tieu_de_toi_gian(lines, y0, max_w=900, cx=540, sizes=(92, 74)):
    """Kiểu tối giản (anh chọn 28/10): không khung, dòng 1 trắng Black to, dòng 2 vàng Bold; bóng mềm đậm
    + lớp tối rất mờ phía sau để đọc được trên nền nhiều màu (poster, kệ máy)."""
    im, d = new()
    rows, y = [], y0
    for i, txt in enumerate(lines):
        big = i == 0
        f, bb = fit(d, txt, "Black" if big else "Bold", 96 if big else 74, max(max_w, 900), 0, nho_nhat=64 if big else 56)
        rows.append((txt, f, bb, big, y))
        y += bb[3] - bb[1] + (20 if big else 0)
    x0 = min(cx - (bb[2] - bb[0]) // 2 for _, _, bb, _, _ in rows)
    x1 = max(cx + (bb[2] - bb[0]) // 2 for _, _, bb, _, _ in rows)
    nen = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(nen).rounded_rectangle([x0 - 50, y0 - 36, x1 + 50, y + 40], radius=60, fill=(0, 0, 0, 95))  # bóng mờ trung tính (pha xanh trông như vệt bẩn)
    im.alpha_composite(nen.filter(ImageFilter.GaussianBlur(28)))
    chu, dc = new()
    for txt, f, bb, big, yy in rows:
        dc.text((cx - (bb[2] - bb[0]) // 2 - bb[0], yy - bb[1]), txt, font=f, fill=TRANG if big else VANG)
    im.alpha_composite(bong_dam(chu, 10, 5, 255))
    im.alpha_composite(bong_dam(chu, 3, 2, 200))  # bóng sát chữ: chữ trắng không lẫn vào nền trắng (lưng iPhone, tường)
    return im, (x0, y0, x1, y)


def nhan_gon(txt, y=258, x=62, kieu=None):
    """Nhãn kiểu tối giản: chữ trắng Bold 54 góc trên trái, gạch chân vàng; chỉ hiện lúc đổi ý (~2,5s). kieu: chu_rieng.py."""
    if kieu:
        return chu_rieng.goi(sys.modules[__name__], kieu, "nhan", nhan_gon, (txt, y, x), [txt], y=y)
    im, d = new()
    f, bb = fit(d, txt, "Bold", 54, 760, 0, nho_nhat=44)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text((x - bb[0], y - bb[1]), txt, font=f, fill=TRANG)
    d.rectangle([x, y + th + 14, x + tw, y + th + 22], fill=VANG)
    return bong_dam(im, 6, 3, 220), (x, y, x + tw, y + th + 22)


def bubble(lines, y0, max_w=800, cx=540, sizes=(92, 74), vien=7):
    """Bong bóng thoại kiểu kênh (làm lại 29/10 cho đỡ thô): khối xanh Poly đổ dải, viền trắng MẢNH, đuôi cong mượt góc
    dưới trái, khử răng cưa; dòng 1 trắng ExtraBold, dòng 2 vàng Bold; nhiều khoảng thở; bóng nổi 2 lớp."""
    im, d = new()
    pad_x, pad_y, gap = 58, 38, 10
    rows = []
    for i, txt in enumerate(lines):
        f, bb = fit(d, txt, "ExtraBold" if i == 0 else "Bold", (sizes[0] - 8) if i == 0 else (sizes[1] - 12),
                    max_w - 2 * pad_x - 8, nho_nhat=56 if i == 0 else 46)
        rows.append((txt, f, bb))
    tw = max(bb[2] - bb[0] for _, _, bb in rows)
    th = sum(bb[3] - bb[1] for _, _, bb in rows) + gap * (len(rows) - 1)
    bx0, by0 = cx - tw // 2 - pad_x, y0
    bx1, by1 = cx + tw // 2 + pad_x, y0 + th + 2 * pad_y

    def duoi(dd, k, ox, oy, inset):  # đuôi cong: 2 cạnh bezier bậc 2 từ đáy khối xuống mũi nhọn lệch trái
        a, b, tip = (bx0 + 62 + inset, by1 - 30), (bx0 + 150 - inset, by1 - 30), (bx0 + 36 + inset * .6, by1 + 54 - inset * 2.2)
        pts = []
        for j in range(17):
            u = j / 16
            c = (bx0 + 70, by1 + 10)
            pts.append(((1 - u) ** 2 * a[0] + 2 * (1 - u) * u * c[0] + u * u * tip[0], (1 - u) ** 2 * a[1] + 2 * (1 - u) * u * c[1] + u * u * tip[1]))
        for j in range(17):
            u = j / 16
            c = (bx0 + 100, by1 + 22)
            pts.append(((1 - u) ** 2 * tip[0] + 2 * (1 - u) * u * c[0] + u * u * b[0], (1 - u) ** 2 * tip[1] + 2 * (1 - u) * u * c[1] + u * u * b[1]))
        dd.polygon([((x - ox) * k, (y - oy) * k) for x, y in pts], fill=255)
    khoi(im, (bx0, by0, bx1, by1), 40, None, a=246, vien=3, vien_mau=(255, 255, 255, 200), them=duoi,
         them_hop=(bx0 + 30, by1 - 32, bx0 + 152, by1 + 56))
    d = ImageDraw.Draw(im)
    y = by0 + pad_y
    for i, (txt, f, bb) in enumerate(rows):
        d.text((cx - (bb[2] - bb[0]) // 2 - bb[0], y - bb[1]), txt, font=f, fill=TRANG if i == 0 else VANG)
        y += bb[3] - bb[1] + gap
    return bong_noi(im), (bx0 - 3, by0 - 3, bx1 + 3, by1 + 58)


def tim(d, cx, cy, r, fill):
    """Trái tim (font không có ♥) — khử răng cưa: vẽ trên lớp 4× rồi dán (d phải là ImageDraw của ảnh RGBA)."""
    im = d._image
    w = int(r * 2.4) + 4
    m = _mask_ss(w, w, lambda dd, k: (dd.ellipse([2 * k, (w / 2 - r * .9 - 2) * k, (w / 2) * k, (w / 2 + r * .1 + 2) * k], fill=255),
                                       dd.ellipse([(w / 2) * k, (w / 2 - r * .9 - 2) * k, (w - 2) * k, (w / 2 + r * .1 + 2) * k], fill=255),
                                       dd.polygon([(3 * k, (w / 2 - r * .25) * k), ((w - 3) * k, (w / 2 - r * .25) * k),
                                                   ((w / 2) * k, (w / 2 + r * 1.05) * k)], fill=255)))
    lp = Image.new("RGBA", (w, w), tuple(fill[:3]) + (0,))
    lp.putalpha(m)
    tmp = Image.new("RGBA", im.size, (0, 0, 0, 0))
    tmp.alpha_composite(lp, (int(cx - w / 2), int(cy - w / 2)))
    im.alpha_composite(tmp)


def card_comment(lines):
    """Thẻ kết của kênh (làm lại 29/10): khối xanh Poly đổ dải viền mảnh, câu kêu comment trắng ExtraBold, nút VÀNG gọn chữ
    xanh + tim; khử răng cưa, bóng nổi."""
    im, d = new()
    l1 = lines[0] if lines else "Anh em cần hỏi gì để lại comment"
    l2 = lines[1] if len(lines) > 1 else "Poly hỗ trợ nha ♥"
    co1 = 60
    while True:
        f1 = font("ExtraBold", co1)
        dong = chia_dong(l1, lambda t: d.textbbox((0, 0), t, font=f1)[2], 720)
        if all(d.textbbox((0, 0), t, font=f1)[2] <= 720 for t in dong) or co1 <= 40:
            break
        co1 -= 4
    if co1 < 48:
        CHU_NHO.append((l1, co1))
    l2 = l2.replace("\ufe0f", "").rstrip()
    co_tim = l2.endswith(("♥", "❤", "<3"))
    l2 = l2.rstrip("♥❤").replace("<3", "").rstrip()
    f2, b2 = fit(d, l2, "Bold", 44, 600, nho_nhat=36)
    bbs = [d.textbbox((0, 0), t, font=f1) for t in dong]
    w_tim = 50 if co_tim else 0
    pw = (b2[2] - b2[0]) + w_tim + 76
    ph = (b2[3] - b2[1]) + 40
    bw = max(max(b[2] - b[0] for b in bbs), pw) + 120
    h1 = sum(b[3] - b[1] for b in bbs) + 16 * (len(bbs) - 1)
    bh = 50 + h1 + 34 + ph + 46
    y1 = 1290
    y0 = y1 - bh
    x0 = 540 - bw // 2
    khoi(im, (x0, y0, x0 + bw, y1), 44, None, a=246, vien=2.5, vien_mau=(255, 255, 255, 120))
    d = ImageDraw.Draw(im)
    y = y0 + 50
    for t, b in zip(dong, bbs):
        d.text((540 - (b[2] - b[0]) // 2 - b[0], y - b[1]), t, font=f1, fill=TRANG)
        y += b[3] - b[1] + 16
    y += 18
    px0 = 540 - pw // 2
    khoi(im, (px0, y, px0 + pw, y + ph), ph // 2, VANG)
    d = ImageDraw.Draw(im)
    tx = px0 + 38
    d.text((tx - b2[0], y + 20 - b2[1]), l2, font=f2, fill=XANH)
    if co_tim:
        tim(d, tx + (b2[2] - b2[0]) + 30, y + ph / 2 - 1, 15, XANH)
    return bong_noi(im), (x0, y0, x0 + bw, y1)


def tieu_de_ghim(txt, kieu=None, bo=None, _v=None):
    """Tiêu đề ghim trên cùng suốt video (kiểu 'IOS 27 BETA - AI CAMERA' của kênh): vàng in hoa viền đen. kieu: chu_rieng.py."""
    if bo:   # r36: bộ mẫu mới (y 300, dưới POLY STORE)
        return MCM.tieu_de(bo, txt, 300)
    if kieu:
        return chu_rieng.goi(sys.modules[__name__], kieu, "tieu_de", tieu_de_ghim, (txt,), [txt], y=236)
    im, d = new()
    f, bb = fit(d, txt.upper(), "Black", 50, 760, 6, nho_nhat=36)
    x = 540 - (bb[2] - bb[0]) // 2 - bb[0]
    y = 236
    d.text((x, y - bb[1]), txt.upper(), font=f, fill=VANG, stroke_width=6, stroke_fill=DEN)
    return bong_mem(im, 3, 5, 6, 100), (x + bb[0], y, x + bb[2], y + bb[3] - bb[1])


def nhan_to(txt, y=700, co=92, nghieng=-3, kieu=None, bo=None, ten_may=None, _v=None):
    """Nhãn từ khoá to (kiểu chữ vàng viền đen của video top): viền 8px, bóng mềm, nghiêng nhẹ cho đỡ cứng;
    dài quá 780px thì tự thu nhỏ. kieu: kiểu riêng của nhãn (chu_rieng.py)."""
    if bo:   # r36: bộ mẫu mới — ten_may = {tag, thong_so} -> thẻ tên máy của bộ
        if ten_may is not None:
            return MCM.the_ten(bo, txt, ten_may.get("tag"), ten_may.get("thong_so"), y)
        return MCM.nhan(bo, txt, y)
    if kieu:
        return chu_rieng.goi(sys.modules[__name__], kieu, "nhan", nhan_to, (txt, y, co, nghieng), [txt], y=y, co=co)
    im, d = new()
    f, bb = fit(d, txt, "Black", co, 780, 8, nho_nhat=56)
    x = 540 - (bb[2] - bb[0]) // 2 - bb[0]
    d.text((x, y - bb[1]), txt, font=f, fill=VANG, stroke_width=8, stroke_fill=DEN)
    if nghieng:
        cy = y + (bb[3] - bb[1]) / 2
        im = im.rotate(-nghieng, resample=Image.BICUBIC, center=(540, cy))
    im = bong_mem(im, 4, 7, 8, 110)
    return im, im.getbbox()


def sticker(ten, x=800, y=1000, co=320):
    """Sticker Poly (sticker_poly.py) đặt tâm tại (x, y), rộng co px."""
    p = os.path.join(STICKER_DIR, f"{ten}.png")
    st = Image.open(p).convert("RGBA")
    k = co / st.width
    st = st.resize((max(1, round(st.width * k)), max(1, round(st.height * k))), Image.LANCZOS)
    im, _ = new()
    x0, y0 = int(x - st.width / 2), int(y - st.height / 2)
    im.alpha_composite(st, (max(0, x0), max(0, y0)), (max(0, -x0), max(0, -y0)))
    return im, (x0, y0, x0 + st.width, y0 + st.height)


def end_card(lines, kieu_ket, bo=None, _v=None):
    if bo:   # r36: bộ mẫu mới — the_comment = kêu comment (dòng 2 = nút), còn lại = câu mời + địa chỉ
        return MCM.the_ket(bo, "comment" if kieu_ket == "the_comment" else "dia_chi", lines)
    if kieu_ket == "the_comment":
        return card_comment(lines)
    im, d = new()
    f1, b1 = fit(d, lines[0], "ExtraBold", 62, 700)
    f2, b2 = fit(d, lines[1], "Bold", 42, 700) if len(lines) > 1 else (None, (0, 0, 0, 0))
    bw = max(b1[2] - b1[0], b2[2] - b2[0]) + 110
    bh = (b1[3] - b1[1]) + (b2[3] - b2[1]) + 120
    x0 = 540 - bw // 2
    y1 = 1290
    y0 = y1 - bh
    if kieu_ket == "the_xanh":
        khoi(im, (x0, y0, x0 + bw, y1), 40, None, a=246, vien=2.5, vien_mau=(255, 255, 255, 120))
    else:  # the_den / vong_lap: nền "đen Poly" mờ, viền mảnh xanh sáng (trước 29/10: đen mờ trơn)
        khoi(im, (x0, y0, x0 + bw, y1), 40, XANH_TOI, a=215, vien=2.5, vien_mau=XANH_SANG[:3] + (190,))
    d = ImageDraw.Draw(im)
    c1 = TRANG if kieu_ket == "the_xanh" else VANG
    d.text((540 - (b1[2] - b1[0]) // 2 - b1[0], y0 + 42 - b1[1]), lines[0], font=f1, fill=c1)
    if f2:
        d.text((540 - (b2[2] - b2[0]) // 2 - b2[0], y0 + 42 + (b1[3] - b1[1]) + 30 - b2[1]), lines[1], font=f2, fill=(255, 255, 255, 230))
    return bong_noi(im), (x0, y0, x0 + bw, y1)


def brand(style=None, bo=None, _v=None):
    if bo:   # r36: bộ mẫu mới, y 226 (trong vùng an toàn)
        return MCM.brand(bo)
    im, d = new()
    if style == "toi_gian":  # mảnh, không viền, chỉ bóng
        d.text((62, 150), "P O L Y   S T O R E", font=font("Bold", 30, goc=True), fill=(255, 255, 255, 240))
        return bong_dam(im, 5, 2, 200), (62, 150, 420, 186)
    d.text((70, 150), "P O L Y   S T O R E", font=font("ExtraBold", 34, goc=True), fill=(255, 255, 255, 235), stroke_width=4, stroke_fill=(0, 0, 0, 200))
    return im, (70, 150, 470, 190)


def price_card(gia, phu, style, kieu=None, bo=None, gia_cu=None, ghi_chu=None, _v=None):
    """Thẻ giá (làm lại 29/10 cho sang): khối xanh Poly, giá VÀNG ExtraBold rất to KHÔNG viền đen, gạch mảnh, dòng phụ
    nhỏ IN HOA giãn chữ trắng mờ (vd. GIÁ NGÀY 29/10). Kiểu dai_trang giữ dải trắng. kieu: chu_rieng.py."""
    if bo:   # r36: bộ mẫu mới — giá gạch (gia_cu) + ghi chú (ghi_chu, không có thì dòng phụ)
        return MCM.the_gia(bo, gia, gia_cu, ghi_chu if ghi_chu is not None else phu, 700)
    if kieu:
        return chu_rieng.goi(sys.modules[__name__], kieu, "gia", price_card, (gia, phu, style), [gia, phu], y=700)
    if style == "dai_trang":
        im, hop1 = block([gia], "dai_trang", 700, sizes=(120, 60))
        if phu:
            im2, hop2 = block([phu], "dai_trang", hop1[3] + 18, sizes=(52, 52))
            im.alpha_composite(im2)
            hop1 = (min(hop1[0], hop2[0]), hop1[1], max(hop1[2], hop2[2]), hop2[3])
        return im, hop1
    im, d = new()
    fg, bg_ = fit(d, gia, "ExtraBold", 150, 620, 0, nho_nhat=90)
    gw, gh = bg_[2] - bg_[0], bg_[3] - bg_[1]
    sub = in_hoa(phu) if phu else None
    fs = font("Bold", 34)
    sp = 3  # giãn chữ dòng phụ (px)
    sw = sum(d.textlength(c, font=fs) + sp for c in sub) - sp if sub else 0
    sbb = d.textbbox((0, 0), sub, font=fs) if sub else (0, 0, 0, 0)
    pad_x, pad_t, pad_b = 64, 34, 36
    bw = int(max(gw, sw) + 2 * pad_x)
    bh = int(pad_t + gh + (22 + 2 + 20 + (sbb[3] - sbb[1]) if sub else 0) + pad_b)
    x0, y0 = 540 - bw // 2, 700
    khoi(im, (x0, y0, x0 + bw, y0 + bh), 36, None, a=246, vien=2.5, vien_mau=(255, 255, 255, 120))
    d = ImageDraw.Draw(im)
    d.text((540 - gw // 2 - bg_[0], y0 + pad_t - bg_[1]), gia, font=fg, fill=VANG)
    if sub:
        yl = y0 + pad_t + gh + 22
        lp, dl = new()
        dl.line([(540 - min(bw / 2 - 40, 150), yl), (540 + min(bw / 2 - 40, 150), yl)], fill=(255, 255, 255, 70), width=2)
        im.alpha_composite(lp)
        d = ImageDraw.Draw(im)
        x = 540 - sw / 2
        for c in sub:
            d.text((x, yl + 22 - sbb[1]), c, font=fs, fill=(255, 255, 255, 225))
            x += d.textlength(c, font=fs) + sp
    return bong_noi(im), (x0, y0, x0 + bw, y0 + bh)


def chia_dong(txt, rong, max_w, max_dong=2):
    """Ngắt dòng cân bằng: theo "|" nếu có; vừa 1 dòng thì để 1 dòng; không thì chọn chỗ ngắt cho 2 dòng dài gần bằng nhau
    (tránh 1 từ mồ côi ở dòng dưới). rong(chuỗi) -> bề rộng px."""
    if "|" in txt:
        parts = [p.strip() for p in txt.split("|") if p.strip()]
        if len(parts) > max_dong:  # quá số dòng: gộp phần thừa vào dòng cuối (không bỏ chữ)
            parts = parts[:max_dong - 1] + [" ".join(parts[max_dong - 1:])]
        return parts
    words = txt.split()
    one = " ".join(words)
    if rong(one) <= max_w or len(words) < 2:
        return [one]
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        wa, wb = rong(a), rong(b)
        cost = max(wa, wb) + (10000 if max(wa, wb) > max_w else 0)
        if best is None or cost < best[0]:
            best = (cost, [a, b])
    return best[1]


ASS_HEAD = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
# màu ASS: &HAABBGGRR (AA = 00 đục, FF trong)
def ass_mau(rgb, a=0):
    """Màu ASS &HAABBGGRR (a: 0 đục … 255 trong)."""
    return "&H%02X%02X%02X%02X" % (a, rgb[2], rgb[1], rgb[0])


def ass_style(key, fs, dy=0):
    s = ASS_STYLE[key].replace("{fs}", str(fs)).replace("{xanh_ass}", ass_mau(XANH[:3], 0x18)).replace(
        "{toi_ass}", ass_mau(XANH_TOI[:3], 0x50))
    if dy:  # r31: phụ đề anh kéo lên / xuống (chu.vi_tri.phu_de): lề dưới MarginV trừ dy (Alignment 2 = canh đáy)
        p = s.split(",")
        p[-2] = str(max(0, int(p[-2]) - int(dy)))
        s = ",".join(p)
    return s


ASS_STYLE = {
    "vien": "Style: Pop,Be Vietnam Pro Black,{fs},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,8,3,2,130,130,580,1",
    "dai_trang": "Style: Pop,Be Vietnam Pro Black,{fs},&H00FFFFFF,&H00FFFFFF,{toi_ass},{toi_ass},0,0,0,0,100,100,0,0,3,14,0,2,130,130,580,1",
    "nen_xanh": "Style: Pop,Be Vietnam Pro Black,{fs},&H00FFFFFF,&H00FFFFFF,{xanh_ass},{xanh_ass},0,0,0,0,100,100,0,0,3,14,0,2,130,130,580,1",
}
ASS_VANG, ASS_TRANG = r"\c&H00D6FF&", r"\c&HFFFFFF&"


def ass_ts(t):
    cs = int(round(max(0.0, t) * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def gio_tung_tu(s):
    """[(từ, t0, t1)] — lấy phu_de.tu nếu có, không thì chia đều theo số ký tự."""
    if s.get("tu"):
        return [(str(w), float(a), float(b)) for w, a, b in s["tu"]]
    # "|" = chỗ ngắt cụm bắt buộc: dính vào cuối từ đứng trước ("và|"), chia_cum tách ở đó, không tính giờ
    ws = re.sub(r"\s*\|\s*", "| ", s["chu"].strip()).strip().lstrip("|").split()
    L = sum(len(w.rstrip("|")) + 1 for w in ws) or 1
    t, out = s["t0"], []
    for w in ws:
        d = (s["t1"] - s["t0"]) * (len(w.rstrip("|")) + 1) / L
        out.append((w, t, t + d))
        t += d
    return out


DAU_CAU = (",", ".", "!", "?", ":", ";", "…")
# cặp từ không tách sang 2 cụm (từ ghép, tên máy, số + đơn vị); chia_cum phạt khi cắt giữa cặp
KHONG_TACH = {("soạn", "thảo"), ("mượt", "mà"), ("học", "sinh"), ("sinh", "viên"), ("học", "tập"), ("làm", "việc"),
              ("văn", "bản"), ("màn", "hình"), ("bàn", "phím"), ("âm", "thanh"), ("tựa", "game"), ("giá", "bán"),
              ("bên", "mình"), ("thay", "thế"), ("đặc", "biệt"), ("đặc", "quyền"), ("hiệu", "năng"), ("mở", "khóa"),
              ("apple", "pencil"), ("pencil", "2"), ("magic", "keyboard"), ("face", "id"), ("ipad", "pro"),
              ("ipad", "air"), ("ipad", "mini"), ("ipad", "gen"), ("macbook", "air"), ("macbook", "pro"),
              ("tốc", "chiến"), ("liên", "quân"), ("hay", "không"), ("được", "không"), ("phiên", "bản"),
              ("thế", "này"), ("như", "thế")}
DON_VI = {"triệu", "nghìn", "ngàn", "trăm", "inch", "gb", "tb", "hz", "%", "tr", "k", "giờ", "tiếng"}


def _goc(w):
    return str(w).rstrip("|").strip(",.!?:;…\"'()").lower()


def khong_nen_tach(a, b):
    a, b = _goc(a), _goc(b)
    if (a, b) in KHONG_TACH:
        return True
    so = lambda x: x.replace(".", "").replace(",", "").isdigit()
    return (so(a) and b in DON_VI) or (a in ("triệu", "tr") and so(b))


def in_hoa(txt):
    """In hoa phụ đề cụm (IPAD PRO cho đồng bộ), chỉ giữ đơn vị Hz (120Hz)."""
    out = []
    for w in txt.split():
        if re.match(r"^\d+([.,]\d+)?Hz\W*$", w):
            out.append(w)
        else:
            out.append(w.upper())
    return " ".join(out)


def chia_cum(words, toi_da_tu=4, toi_da_ky_tu=16):
    """[(từ, t0, t1)] -> [[(từ, t0, t1), ...], ...]: tách ở dấu câu trước, rồi chia mỗi đoạn thành cụm 1–3 từ
    (quy hoạch động): tránh cụm quá ~16 ký tự, tránh cụm 1 từ khi đoạn có nhiều từ, ít cụm nhất có thể.
    Cụm 4 từ chỉ dùng khi chia 2+2 sẽ ra cụm hiện < 0,3s (bị gộp sai chỗ, vd "Apple Pencil 2, như thế" / "này đây").
    Một từ quá dài chỉ làm chính nó đứng riêng, không kéo cả câu thành từng từ."""
    doan, cur = [], []
    for w in words:
        cur.append(w)
        if str(w[0]).endswith("|") or str(w[0]).rstrip("|").endswith(DAU_CAU):  # "|" = chỗ ngắt viết tay
            doan.append(cur)
            cur = []
    if cur:
        doan.append(cur)
    out = []
    for d in doan:
        n = len(d)
        best = [0.0] + [float("inf")] * n
        cat = [0] * (n + 1)
        for j in range(1, n + 1):
            for k in range(1, min(toi_da_tu, j) + 1):
                c = d[j - k:j]
                dai = len(" ".join(str(x[0]).rstrip("|").rstrip(",.;:…") for x in c))  # đếm như chữ hiện ra
                cost = 1.0 + 100.0 * max(0, dai - toi_da_ky_tu) * (1 if k > 1 else 0.02)
                if k == 1 and n > 1:
                    cost += 6.0
                if j - k > 0 and khong_nen_tach(d[j - k - 1][0], d[j - k][0]):  # cắt giữa từ ghép / tên / số+đơn vị
                    cost += 7.0
                if k == 4:
                    cost += 2.5
                try:  # cụm hiện quá ngắn (sẽ bị gộp vào cụm bên cạnh, tách sai chỗ)
                    het = float(d[j][1]) if j < n else float(c[-1][2])
                    if n > 1 and het - float(c[0][1]) < 0.3:
                        cost += 8.0
                except (TypeError, ValueError, IndexError):
                    pass
                if best[j - k] + cost < best[j]:
                    best[j], cat[j] = best[j - k] + cost, k
        parts, j = [], n
        while j > 0:
            parts.append(d[j - cat[j]:j])
            j -= cat[j]
        out.extend(reversed(parts))
    return out


def cac_cum(tl, warn=None, kem_tu=False):
    """Mọi cụm phụ đề trên timeline: [(chữ in hoa, t0, t1, {từ vàng}, câu số)] — không chồng nhau, không đè thẻ kết.
    Cụm hiện < 0,25s gộp vào cụm trước (hoặc sau) để không mất chữ; cụm toàn dấu câu gộp luôn; giờ làm tròn theo khung."""
    items = tl.get("phu_de") or []
    chu = tl.get("chu") or {}
    het = tl["ket_t"][0] if chu.get("ket") else tl["T"]
    fr = 1.0 / float(tl.get("fps") or 30)
    q = lambda t: round(round(t / fr) * fr, 3)
    sach = lambda t: "".join(ch for ch in t if ch.isalnum())
    out = []
    for n, s in enumerate(items):
        tat_ca = gio_tung_tu(s)
        words = [w for w in tat_ca if w[1] < het - 0.05]
        if warn is not None and len(words) < len(tat_ca):
            warn.append(f"phụ đề {n + 1}: {len(tat_ca) - len(words)} từ cuối bị thẻ kết cắt ('" +
                        " ".join(str(w[0]) for w in tat_ca[len(words):]) + "') — dời câu sớm hơn hoặc giảm ket_giay")
        if not words:
            continue
        sau = items[n + 1]["t0"] if n + 1 < len(items) else het
        het_cau = min(het, sau, max(s["t1"], words[-1][2]))
        hl = set()
        for x in s.get("nhan") or []:
            hl.update(x.lower().split())
        cs = []
        for j, c in enumerate(chia_cum(words)):
            txt = " ".join(str(w[0]) for w in c).replace("|", " ")
            cs.append([txt, s["t0"] if j == 0 else c[0][1], [(str(w[0]).replace("|", ""), float(w[1])) for w in c]])
        moc = [c[1] for c in cs[1:]] + [het_cau]
        cs = [[t, a, b, ws] for (t, a, ws), b in zip(cs, moc)]
        gon = []
        for c in cs:  # gộp cụm toàn dấu câu / hiện quá ngắn vào cụm trước
            if gon and (not sach(c[0]) or c[2] - c[1] < 0.25):
                gon[-1][0] += " " + c[0]
                gon[-1][3] += c[3]
                gon[-1][2] = c[2]
            else:
                gon.append(c)
        if len(gon) > 1 and (not sach(gon[0][0]) or gon[0][2] - gon[0][1] < 0.25):  # cụm đầu quá ngắn: gộp vào cụm sau
            gon[1][0] = gon[0][0] + " " + gon[1][0]
            gon[1][3] = gon[0][3] + gon[1][3]
            gon[1][1] = gon[0][1]
            gon = gon[1:]
        for txt, a, b, ws in gon:
            txt = txt.strip().rstrip(",.;:…").strip()  # phụ đề cụm không in dấu phẩy, chấm cuối
            a, b = q(a), q(b)
            if not sach(txt) or b - a < fr / 2:
                continue
            row = (in_hoa(txt), a, b, set(hl), n)
            out.append(row + ([(in_hoa(w), max(a, q(t))) for w, t in ws],) if kem_tu else row)  # 28/10: phụ đề in hoa hết
    return out


def sub_cum(txt, hl, style, bo=None, pd=None, _v=None):
    """PNG 1 cụm phụ đề in hoa, 1 dòng, đường chân chữ cố định y 1272 (chữ có dấu nặng không làm cụm nhảy lên xuống);
    từ trong 'nhan' tô vàng."""
    if bo:   # r36: bộ mẫu mới — pd = id kiểu phụ đề của bộ
        return MCM.phu_de(bo, pd, txt, hl)
    im, d = new()
    if style == "toi_gian":  # chữ IN HOA (chủ shop 28/10), không viền, bóng mềm đậm, thấp xuống phần dưới (không đè tay/máy)
        f, _ = fit(d, txt, "Bold", 66, 860, 0, nho_nhat=54)
        yb = 1358  # chân chữ: phần thấp nhất (dấu nặng, g, y) vẫn trên mốc an toàn y 1380
        bb = d.textbbox((0, yb), txt, font=f, anchor="ls")
        tw = bb[2] - bb[0]
        x = 540 - tw // 2 - bb[0]
        for w_ in txt.split():
            col = VANG if w_.lower().strip(",.!?:;…") in hl else TRANG
            d.text((x, yb), w_, font=f, fill=col, anchor="ls")
            x += d.textlength(w_ + " ", font=f)
        return bong_dam(im, 6, 3, 235), (540 - tw // 2, bb[1], 540 + tw // 2, bb[3])
    f, _ = fit(d, txt, "Black", 80, 820, 8, nho_nhat=54)
    yb = 1272
    bb = d.textbbox((0, yb), txt, font=f, anchor="ls", stroke_width=8)
    tw = bb[2] - bb[0]
    x = 540 - tw // 2 - bb[0]
    if style in ("dai_trang", "nen_xanh"):
        hop_n = [540 - tw // 2 - 24, bb[1] - 14, 540 + tw // 2 + 24, bb[3] + 12]
        if style == "nen_xanh":
            khoi_xanh(im, hop_n, 18, a=232, bong_sang=False)
        else:
            d.rounded_rectangle(hop_n, radius=18, fill=XANH_TOI[:3] + (175,))
    vien = 0 if style in ("dai_trang", "nen_xanh") else 8
    for w_ in txt.split():
        col = VANG if w_.lower().strip(",.!?:;…") in hl else TRANG
        d.text((x, yb), w_, font=f, fill=col, anchor="ls", stroke_width=vien, stroke_fill=DEN)
        x += d.textlength(w_ + " ", font=f)
    return im, (540 - tw // 2, bb[1], 540 + tw // 2, bb[3])


def write_ass_cum(tl, outdir, style, warn):
    """phu-de.ass kiểu cụm ngắn: mỗi cụm 1–3 từ in hoa nảy 120%→100% trong 100ms; cỡ = cỡ PNG (80px, thu cho vừa
    820px) đổi sang đơn vị ASS (× ASS_K) để bản máy chủ và bản Premiere to bằng nhau."""
    cum = cac_cum(tl, warn)
    if not cum:
        return None
    _, d = new()
    ev = []
    clean = lambda w: w.replace("{", "").replace("}", "").replace("\\", "")
    dpd = pd_lech(tl)
    y_chan = pd_y_goc(tl.get("kieu")) + dpd   # r31: phụ đề anh đã kéo -> chân chữ ASS đúng y như PNG xem trước (từng cụm theo cỡ chữ)
    for txt, a, b, hl, _ in cum:
        f, _ = fit(d, txt, "Black", 80, 820, 8)
        parts = []
        for w in txt.split():
            w2 = clean(w)
            parts.append("{" + ASS_VANG + "}" + w2 + "{" + ASS_TRANG + "}" if w2.lower().strip(",.!?:;…") in hl else w2)
        # libass canh đáy (Alignment 2): đáy dòng = chân chữ + phần dưới chân chữ của font (descent) -> MarginV riêng từng cụm.
        # Không kéo (dpd = 0): MarginV 0 = theo Style (580) như cũ.
        mv = max(0, round(H - y_chan - f.getmetrics()[1])) if dpd else 0
        ev.append(f"Dialogue: 0,{ass_ts(a)},{ass_ts(b)},Pop,,0,0,{mv},," + r"{\fs%d\fscx120\fscy120\t(0,100,\fscx100\fscy100)}" % round(f.size * ASS_K)
                  + " ".join(parts))
    key = style if style in ASS_STYLE else "vien"
    path = os.path.join(outdir, "phu-de.ass")
    with open(path, "w", encoding="utf-8") as fo:
        fo.write(ASS_HEAD.replace("{style}", ass_style(key, round(80 * ASS_K), pd_lech(tl))) + "\n".join(ev) + "\n")
    return path


def write_ass(tl, outdir, style, warn):
    """phu-de.ass: cả câu hiện, từ đang đọc vàng + nảy 112% (90ms); từ trong 'nhan' vàng cả câu."""
    items = tl.get("phu_de") or []
    if not items:
        return None
    _, d = new()
    fs = 70  # cỡ px (PIL); ghi ra ASS thì nhân ASS_K
    fb = lambda size: font("Black", size)
    ev = []
    chu = tl.get("chu") or {}
    het = tl["ket_t"][0] if chu.get("ket") else tl["T"]  # phụ đề không đè thẻ kết
    for n, s in enumerate(items):
        words = [w for w in gio_tung_tu(s) if w[1] < het - 0.05]
        if not words:
            continue
        # 3/11: kiểu "cả câu, tô từ" cũng in hoa hết như phụ đề cụm (luật kênh 28/10); đo chiều ngang theo chữ in hoa
        words = [(in_hoa(str(w)) or str(w), a, b) for w, a, b in words]
        s = dict(s, chu=in_hoa(str(s.get("chu") or "")))
        sau = items[n + 1]["t0"] if n + 1 < len(items) else het
        het_cau = min(het, sau)  # không chồng câu sau (libass sẽ đẩy dòng lên)
        if len(words) > 8:
            warn.append(f"phụ đề {n + 1}: {len(words)} từ/màn (nên 3–6, tối đa 8)")
        size = fs
        while size > 54:
            f = fb(size)
            lines = chia_dong(s["chu"], lambda t: d.textbbox((0, 0), t, font=f, stroke_width=8)[2], 800)
            if all(d.textbbox((0, 0), ln, font=f, stroke_width=8)[2] <= 800 for ln in lines):
                break
            size -= 4
        f = fb(size)
        lines = chia_dong(s["chu"], lambda t: d.textbbox((0, 0), t, font=f, stroke_width=8)[2], 800)
        if len(" ".join(lines).split()) != len(words):
            # giờ từng từ không khớp số từ của câu: dùng chữ theo giờ, ngắt cân bằng lại
            lines = chia_dong(" ".join(w for w, _, _ in words), lambda t: d.textbbox((0, 0), t, font=f, stroke_width=8)[2], 800)
        per_line = [len(ln.split()) for ln in lines]
        hl = set()
        for x in s.get("nhan") or []:
            hl.update(x.lower().split())
        clean = lambda w: w.replace("{", "").replace("}", "").replace("\\", "")
        for k, (w, a, b) in enumerate(words):
            end = min(het_cau, words[k + 1][1] if k + 1 < len(words) else max(b, s["t1"]))
            if end <= (a if k else s["t0"]) + 0.01:
                continue
            parts, j = [], 0
            for li, cnt in enumerate(per_line):
                seg = []
                for _ in range(cnt):
                    if j >= len(words):
                        break
                    w2 = clean(words[j][0])
                    vang = w2.lower().strip(",.!?") in hl
                    if j == k:
                        seg.append("{" + ASS_VANG + r"\fscx112\fscy112\t(0,90,\fscx100\fscy100)}" + w2 +
                                   "{" + (ASS_VANG if vang else ASS_TRANG) + r"\fscx100\fscy100}")
                    elif vang:
                        seg.append("{" + ASS_VANG + "}" + w2 + "{" + ASS_TRANG + "}")
                    else:
                        seg.append(w2)
                    j += 1
                parts.append(" ".join(seg))
            txt = (r"{\fs%d}" % round(size * ASS_K) if size != fs else "") + r"\N".join(parts)
            ev.append(f"Dialogue: 0,{ass_ts(a if k else s['t0'])},{ass_ts(end)},Pop,,0,0,0,,{txt}")
    key = style if style in ASS_STYLE else "vien"
    path = os.path.join(outdir, "phu-de.ass")
    with open(path, "w", encoding="utf-8") as fo:
        fo.write(ASS_HEAD.replace("{style}", ass_style(key, round(fs * ASS_K), pd_lech(tl))) + "\n".join(ev) + "\n")
    return path


def subtitle(txt, nhan, style, bo=None, pd=None, dang_doc=None, _v=None):
    """Phụ đề 1–2 dòng, chân chữ ~y 1250–1350; từ trong 'nhan' tô vàng. bo (r36): cả câu kiểu bộ mới, dang_doc = từ đang đọc."""
    if bo:
        hl = set()
        for n in nhan or []:
            hl.update(str(n).lower().split())
        return MCM.phu_de(bo, pd, txt, hl, dang_doc)
    im, d = new()
    f = font("ExtraBold", 62)
    lines = chia_dong(txt, lambda t: d.textbbox((0, 0), t, font=f, stroke_width=7)[2], 800)
    hl = set()
    for n in nhan or []:
        hl.update(n.lower().split())
    lh = 80
    y = 1340 - lh * len(lines)
    boxes = []
    for ln in lines:
        tw = d.textbbox((0, 0), ln, font=f, stroke_width=7)[2]
        x = 540 - tw // 2
        if style in ("dai_trang", "nen_xanh"):
            if style == "nen_xanh":
                khoi_xanh(im, (x - 22, y - 8, x + tw + 22, y + lh - 6), 16, a=228, bong_sang=False)
            else:
                d.rounded_rectangle([x - 22, y - 8, x + tw + 22, y + lh - 6], radius=16, fill=XANH_TOI[:3] + (175,))
        for w_ in ln.split():
            col = VANG if w_.lower().strip(",.!?") in hl else TRANG
            d.text((x, y), w_, font=f, fill=col, stroke_width=0 if style in ("dai_trang", "nen_xanh") else 7, stroke_fill=DEN)
            x += d.textbbox((0, 0), w_ + " ", font=f)[2]
        boxes.append((540 - tw // 2, y, 540 + tw // 2, y + lh))
        y += lh
    return im, (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))


def check_safe(hop, kind):
    x0, y0, x1, y1 = hop
    bad = []
    if y1 > 620 and y0 < 1320 and x1 > 950:
        bad.append("chữ lấn cột nút bên phải (x>950)")
    if kind != "phu_de" and y1 > 1300:
        bad.append("chữ thấp hơn y 1300")
    if kind == "phu_de" and y1 > 1380:
        bad.append("phụ đề thấp hơn y 1380")
    if x0 < 60:
        bad.append("chữ sát mép trái")
    return bad


def phu_de_giua(l, outdir, track=1, hieu_ung="nay"):
    """Dời chữ của 1 PNG (phụ đề, hook, nhãn…) về tâm khung (540, 960) để Premiere phóng to/nhỏ quanh tâm chữ; trả vi_tri
    (0–1) = tâm chữ thật, dùng làm Position của clip."""
    im = Image.open(l["png"]).convert("RGBA")
    bb = im.getbbox()
    if not bb:
        return None
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    out.alpha_composite(im.crop(bb), (int(round(540 - (bb[2] - bb[0]) / 2)), int(round(960 - (bb[3] - bb[1]) / 2))))
    ten = l["ten"].replace(".png", "-giua.png")
    out.save(os.path.join(outdir, ten))
    return dict(png=os.path.join(outdir, ten), ten=ten, t0=l["t0"], t1=l["t1"], track=track,
                vi_tri=[round(cx / W, 4), round(cy / H, 4)], hieu_ung=hieu_ung)


def xep_track(ds, tu):
    """Xếp lớp (theo giờ bắt đầu) vào track thấp nhất từ `tu` mà lớp trước trên track đó đã hết — không chồng giờ trên
    cùng track (Premiere đặt đè sẽ cắt lớp cũ). Ghi l['track']; trả số track tiếp theo còn trống."""
    het = []  # giờ hết của lớp cuối trên track tu + i
    for l in sorted(ds, key=lambda x: (x["t0"], x["t1"])):
        for i, h in enumerate(het):
            if l["t0"] >= h - 1e-3:
                l["track"], het[i] = tu + i, l["t1"]
                break
        else:
            l["track"] = tu + len(het)
            het.append(l["t1"])
    return tu + len(het)


def anh_toan_khung(ten, outdir, ve):
    """PNG 1080×1920 vẽ bằng hàm ve(ImageDraw / Image) — lớp hiệu ứng (chớp trắng, tối viền, lóa sáng, thanh tiến trình)."""
    p = os.path.join(outdir, ten)
    im = ve()
    im.save(p)
    return p


def lop_hieu_ung(tl, outdir):
    """Lớp hiệu ứng hình cho Premiere (đường máy chủ tự làm bằng ffmpeg, không dùng các lớp này):
    - diem_nhan chop_trang: PNG trắng 4 khung ở chỗ đổi cảnh không có chuyển cảnh, Opacity 85 → 0;
    - lop_phu toi_vien: PNG tối viền cả video; loa_sang: PNG lóa ấm góc trên phải 1,2s đầu + 1s lúc vào thẻ kết;
    - thanh_tien_trinh co: thanh vàng mảnh trên cùng trượt từ trái sang hết video (keyframe Position).
    zoom_dap / rung_nhip là keyframe trên chính clip cảnh (lenh_premiere), không cần lớp."""
    import lenh_premiere as LP
    k, T, fps = tl["kieu"], tl["T"], float(tl.get("fps") or 30)
    ds = []
    if k.get("diem_nhan") == "chop_trang":
        p = anh_toan_khung("fx-chop.png", outdir, lambda: Image.new("RGBA", (W, H), (255, 255, 255, 255)))
        for t in LP.moc_nhan(tl):
            ds.append(dict(png=p, ten="fx-chop.png", t0=round(t, 3), t1=round(t + 4 / fps, 3), hieu_ung="chop", loai="fx"))
    lp = k.get("lop_phu")
    if lp == "toi_vien":
        def vien():
            y, x = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.sqrt(((x - W / 2) / (W * 0.62)) ** 2 + ((y - H / 2) / (H * 0.62)) ** 2)
            a = np.clip((r - 0.62) / 0.55, 0, 1) ** 1.6 * 150
            arr = np.zeros((H, W, 4), np.uint8)
            arr[..., 3] = a.astype(np.uint8)
            return Image.fromarray(arr, "RGBA")
        p = anh_toan_khung("fx-toi-vien.png", outdir, vien)
        ds.append(dict(png=p, ten="fx-toi-vien.png", t0=0.0, t1=T, hieu_ung=None, loai="fx"))
    elif lp == "loa_sang":
        def loa():
            y, x = np.mgrid[0:H, 0:W].astype(np.float32)
            r = np.sqrt((x - W * 1.05) ** 2 + (y + H * 0.05) ** 2) / (H * 0.75)
            a = np.clip(1 - r, 0, 1) ** 1.8 * 175
            arr = np.zeros((H, W, 4), np.uint8)
            arr[..., 0], arr[..., 1], arr[..., 2] = BANG_MAU["vang_loa"]  # lóa vàng Poly (trước: cam)
            arr[..., 3] = a.astype(np.uint8)
            return Image.fromarray(arr, "RGBA")
        p = anh_toan_khung("fx-loa-sang.png", outdir, loa)
        k0 = tl["ket_t"][0] if (tl.get("chu") or {}).get("ket") else max(0.0, T - 1.5)
        ds.append(dict(png=p, ten="fx-loa-sang.png", t0=0.0, t1=round(min(1.2, T), 3), hieu_ung="loe", loai="fx"))
        if k0 > 1.5:
            ds.append(dict(png=p, ten="fx-loa-sang.png", t0=round(k0, 3), t1=round(min(T, k0 + 1.0), 3), hieu_ung="loe", loai="fx"))
    thanh = None
    if k.get("thanh_tien_trinh") == "co":
        def ve_thanh():
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(im).rectangle([0, 0, W - 1, max(4, H // 192) - 1], fill=VANG)
            return im
        p = anh_toan_khung("fx-thanh.png", outdir, ve_thanh)
        thanh = dict(png=p, ten="fx-thanh.png", t0=0.0, t1=T, hieu_ung="chay", loai="thanh")
    return ds, thanh


MOV = {}  # ten PNG -> dict(ten mov, vi_tri) — chữ động dựng sẵn (hoat_hinh.py) cho đường Premiere


def dung_mov(tl, layers, outdir, warn):
    """kieu.hoat_hinh = mov: hook (khối tiêu đề có nảy / vệt sáng / sao), thẻ giá (đóng dấu), phụ đề cụm (karaoke từng từ)
    thành MOV alpha; ghi MOV[ten png] = {ten, vi_tri}. Lỗi 1 lớp -> cảnh báo, lớp đó giữ PNG + keyframe."""
    import hoat_hinh as HH
    MOV.clear()
    k, chu = tl["kieu"], tl.get("chu") or {}
    fps = float(tl.get("fps") or 30)
    y_hook = {"tren": 230 if k.get("chu") == "toi_gian" else 260, "giua": 900}.get(k.get("vi_tri_chu"), 600)
    for l in layers:
        try:
            if l.get("loai") == "hook":
                # hook có kiểu riêng / bộ mẫu mới (r36): dựng từ PNG đã vẽ
                if k["chu"] in KIEU_KHOI and not chu.get("kieu_hook") and not MCM.bo_cua(k):
                    phan, hop0 = khoi_tieu_de(chu["hook"], k["chu"], y_hook, 860, 540, THE_BIA.get("v"))
                    dc = dat_cho(((chu.get("vi_tri") if isinstance(chu.get("vi_tri"), dict) else {}) or {}).get("hook"))
                    if dc:  # r31: hook anh kéo chỗ khác -> các phần dời như PNG (block đã dời theo cùng hộp)
                        dx, dy = lech_tam(hop0, dc["tam"])
                        phan = [(dich_anh(lp, dx, dy), v) for lp, v in phan]
                else:
                    phan = [(Image.open(l["png"]).convert("RGBA"), "chinh")]
                ten = "hook.mov"
                if k["chu"] == "the_bia" and not chu.get("kieu_hook") and not MCM.bo_cua(k):  # thẻ tên máy làm bìa: khung 0 đủ thẻ, rồi viên thông số nảy + vệt sáng
                    _, vt, _ = HH.ten_may_mov(phan, l["t1"] - l["t0"], os.path.join(outdir, ten), fps, bia=True)
                else:
                    _, vt, _ = HH.hook_mov(phan, l["t1"] - l["t0"], os.path.join(outdir, ten), fps)
                MOV[l["ten"]] = {"ten": ten, "vi_tri": vt}
            elif l.get("loai") == "nhan" and l["ten"] in TEN_MAY:
                phan, _ = the_ten_may(**TEN_MAY[l["ten"]])
                ten = l["ten"].replace(".png", ".mov")
                _, vt, _ = HH.ten_may_mov(phan, l["t1"] - l["t0"], os.path.join(outdir, ten), fps)
                MOV[l["ten"]] = {"ten": ten, "vi_tri": vt}
            elif l.get("loai") == "gia":
                ten = "the-gia.mov"
                _, vt, _ = HH.gia_mov(Image.open(l["png"]).convert("RGBA"), l["t1"] - l["t0"], os.path.join(outdir, ten), fps)
                MOV[l["ten"]] = {"ten": ten, "vi_tri": vt}
        except Exception as e:  # noqa: BLE001
            warn.append(f"hoạt hình {l['ten']}: {e} — dùng PNG + keyframe")
    if k.get("phu_de") == "cum_ngan" and k["chu"] != "toi_gian" and not MCM.bo_cua(k):   # r36: bộ mới giữ PNG phụ đề của bộ
        dem = {}
        dpd = pd_lech(tl)
        for txt, a, b, hl, n, ws in cac_cum(tl, kem_tu=True):
            dem[n] = dem.get(n, 0) + 1
            ten_png = f"phu-de-{n + 1:02d}-{dem[n]}.png"
            if b - a < 0.2 or not ws:
                continue
            kw = lambda w: w.lower().strip(",.!?:;…") in hl or bool(re.search(r"\d", w))
            cum = [(w, t, kw(w)) for w, t in ws]
            try:
                ten = ten_png.replace(".png", ".mov")
                _, vt, _ = HH.karaoke_mov(cum, a, b, os.path.join(outdir, ten), lambda c: font("Black", c), fps=fps, xanh=XANH, vang=VANG,
                                          **({"y_tam": 1265 + dpd} if dpd else {}))  # r31: phụ đề anh kéo lên / xuống
                MOV[ten_png] = {"ten": ten, "vi_tri": vt}
            except Exception as e:  # noqa: BLE001
                warn.append(f"karaoke {ten_png}: {e} — dùng PNG + keyframe")


def lop_rieng(layers, outdir, tl):
    """Premiere ≥ 1.5.0 (them_track chạy thật 28/10): MỖI lớp chữ là 1 clip riêng, có chuyển động khi hiện.
    Thứ tự track từ dưới lên: V1 cảnh · lớp hiệu ứng · phụ đề · hook / nhãn / giá / tiêu đề / thẻ kết / sticker (xếp không
    chồng giờ) · POLY STORE · thanh tiến trình. Lớp có chuyển động được dời về tâm khung (`vi_tri` = Position thật) để phóng
    to quanh đúng chữ. Trả (lop_premiere, số track hình cần)."""
    fx, thanh = lop_hieu_ung(tl, outdir)
    tiep = xep_track(fx, 1) if fx else 1
    pd = [l for l in layers if l.get("loai") == "phu_de"]
    con = [l for l in layers if l.get("loai") not in ("phu_de", "brand")]
    brand = [l for l in layers if l.get("loai") == "brand"]
    out = list(fx)
    for nhom in (pd, con):
        if not nhom:
            continue
        tam = [dict(l) for l in nhom]
        tiep = xep_track(tam, tiep)
        for l in tam:
            hu = HIEU_UNG_PR.get(l.get("loai"))
            if l["ten"] in MOV:  # chữ động dựng sẵn: chuyển động nằm trong file, chỉ cần Position
                m = MOV[l["ten"]]
                out.append(dict(png=os.path.join(outdir, m["ten"]), ten=m["ten"], t0=l["t0"], t1=l["t1"], track=l["track"],
                                vi_tri=m["vi_tri"], hieu_ung="mov", loai=l.get("loai")))
                continue
            if hu and hu != "mo":
                g = phu_de_giua(l, outdir, l["track"], hu)
                if g:
                    g["loai"] = l["loai"]
                    out.append(g)
                    continue
            out.append(dict(png=l["png"], ten=l["ten"], t0=l["t0"], t1=l["t1"], track=l["track"], hieu_ung=hu, loai=l.get("loai")))
    for l in brand:
        out.append(dict(png=l["png"], ten=l["ten"], t0=l["t0"], t1=l["t1"], track=tiep, loai="brand"))
    if brand:
        tiep += 1
    if thanh:
        thanh["track"] = tiep
        out.append(thanh)
        tiep += 1
    return out, tiep


def ghep_cho_premiere(layers, outdir, tach_phu_de=False):
    if tach_phu_de:
        # Phụ đề cụm riêng V2 (mỗi cụm 1 clip, nảy lên bằng keyframe Scale/Opacity); mọi lớp còn lại kể cả
        # POLY STORE ghép thành đoạn tĩnh trên V3 (không chồng giờ).
        pd = [l for l in layers if l["ten"].startswith("phu-de-")]
        con = [l for l in layers if not l["ten"].startswith("phu-de-")]
        out = [x for x in (phu_de_giua(l, outdir) for l in sorted(pd, key=lambda l: l["t0"])) if x]
        moc = sorted({round(x, 3) for l in con for x in (l["t0"], l["t1"])})
        n = 0
        for a, b in zip(moc, moc[1:]):
            if b - a < 0.02:
                continue
            on = [l for l in con if l["t0"] <= a + 1e-3 and l["t1"] >= b - 1e-3]
            if not on:
                continue
            prev = out[-1] if out and out[-1]["track"] == 2 else None
            if prev and prev["nguon"] == [l["ten"] for l in on] and abs(prev["t1"] - a) < 1e-3:
                prev["t1"] = b
                continue
            n += 1
            ten = f"ghep-{n:02d}.png"
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            for l in on:
                im.alpha_composite(Image.open(l["png"]).convert("RGBA"))
            im.save(os.path.join(outdir, ten))
            out.append(dict(png=os.path.join(outdir, ten), ten=ten, t0=a, t1=b, track=2, nguon=[l["ten"] for l in on]))
        return out
    return ghep_mot_track(layers, outdir)


def ghep_mot_track(layers, outdir):
    """Premiere chỉ có 3 track hình (UXP không thêm track được) và đặt đè lên nhau dễ xóa mất lớp cũ:
    ghép các lớp chữ (trừ POLY STORE) thành từng đoạn không chồng giờ -> 1 track V2, POLY STORE riêng V3.
    Mỗi đoạn = các lớp đang hiện trong khoảng đó, chồng theo thứ tự vẽ."""
    chu = [l for l in layers if l["ten"] != "brand.png"]
    out = [dict(png=l["png"], ten=l["ten"], t0=l["t0"], t1=l["t1"], track=2) for l in layers if l["ten"] == "brand.png"]
    moc = sorted({round(x, 3) for l in chu for x in (l["t0"], l["t1"])})
    n = 0
    for a, b in zip(moc, moc[1:]):
        if b - a < 0.02:
            continue
        on = [l for l in chu if l["t0"] <= a + 1e-3 and l["t1"] >= b - 1e-3]
        if not on:
            continue
        prev = out[-1] if out and out[-1]["track"] == 1 else None
        if prev and prev["nguon"] == [l["ten"] for l in on] and abs(prev["t1"] - a) < 1e-3:
            prev["t1"] = b  # cùng bộ lớp: nối dài đoạn trước
            continue
        n += 1
        ten = f"ghep-{n:02d}.png"
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for l in on:
            im.alpha_composite(Image.open(l["png"]).convert("RGBA"))
        im.save(os.path.join(outdir, ten))
        out.append(dict(png=os.path.join(outdir, ten), ten=ten, t0=a, t1=b, track=1, nguon=[l["ten"] for l in on]))
    return out


for _t in ("block", "end_card", "brand", "price_card", "tieu_de_ghim", "nhan_gon", "the_ten_may", "nhan_to", "sub_cum", "subtitle"):
    globals()[_t] = _dat_cho(globals()[_t])  # r31: nhận thêm tam / lech (dời lớp tới chỗ anh kéo); không truyền = như cũ
MCM.dat_vc(sys.modules[__name__])  # r36: bộ mẫu mới dùng chung bảng màu / font / CHU_NHO của đúng module này (kể cả chạy trực tiếp)


def render(tl, outdir):
    os.makedirs(outdir, exist_ok=True)
    k = tl["kieu"]
    chu = tl.get("chu", {})
    vt = chu.get("vi_tri") if isinstance(chu.get("vi_tri"), dict) else {}  # r31: chỗ anh kéo (không có = chỗ cũ)
    dpd = pd_lech(tl)
    kpd = {"lech": [0, dpd]} if dpd else {}
    layers, warn = [], []
    CHU_NHO.clear()
    BO["ten"] = k.get("bo_font") or "poly_goc"
    if BO["ten"] not in BO_FONT:
        warn.append(f"bo_font '{BO['ten']}' không có, dùng poly_goc")
        BO["ten"] = "poly_goc"
    thieu = [f for f in file_font_can(BO["ten"]) if not os.path.isfile(os.path.join(FONT_DIR, f))]
    if thieu:
        warn.append(f"thiếu font {', '.join(thieu)} trong {FONT_DIR} (bộ {BO['ten']}) — tải từ github google/fonts ofl/"
                    f"{BO_FONT[BO['ten']]['thu_muc']}; tạm dùng poly_goc")
        BO["ten"] = "poly_goc"
    THE_BIA["v"] = chu.get("the_bia")
    TEN_MAY.clear()
    # r36 (11/11): bộ mẫu mới cả video (kieu.bo_mau) — không có khoá: bm None, mọi lời gọi / lớp / lop-chu.json y hệt cũ
    bm = MCM.bo_cua(k)
    if k.get("bo_mau") and not bm:
        warn.append(f"bộ mẫu '{k.get('bo_mau')}' không có trong bộ dựng, dùng kiểu chữ cũ")
    MCM.KINH["che_do"] = "duc" if tl.get("duong") == "premiere" else "mo"   # Premiere: kính đục (không làm mờ cảnh)
    mo_ds = []   # lớp có kính (dựng máy chủ): (t0, t1, mặt nạ)
    pd_st = MCM.pd_kieu(bm, k.get("kieu_phu_de"), k.get("phu_de")) if bm else None   # kiểu phụ đề của bộ mới

    def kb(bo):   # tham số bộ mới cho hàm vẽ (_v: khoá lớp nhớ xem trước đổi khi bộ / mau_chu_moi đổi)
        return {"bo": bo, "_v": MCM.PHIEN} if bo else {}

    def bo_chu(kh):   # kiểu riêng 1 chữ: {"bo": id} / mẫu có sẵn mang "bo" -> bộ đó; kiểu riêng khác -> kiểu cũ; không có -> bộ cả video
        kv = (kh or {}).get("kieu") or {}
        b = kv.get("bo") or (chu_rieng.MAU.get(kv.get("mau_co_san")) or {}).get("bo")
        if b in MCM.BO:
            return b, {}
        if kh and bm and not chu_rieng.co_mau(kv):   # chỉ đổi font (bộ mới dùng font của bộ): theo bộ cả video
            return bm, {}
        return (None, kh) if kh else (bm, {})

    def add(im, hop, name, t0, t1, lop, kind, mo=None):
        p = os.path.join(outdir, name)
        im.save(p)
        layers.append({"png": p, "ten": name, "t0": round(t0, 3), "t1": round(t1, 3), "lop": lop, "hop": list(hop),
                       "hieu_ung": HIEU_UNG.get(kind), "loai": kind})
        if mo and MCM.KINH["che_do"] == "mo":   # r36 kính: dung_may_chu làm mờ cảnh dưới thẻ (khung xem: CSS)
            layers[-1]["mo_nen"] = MCM.mo_cua(mo)
            if isinstance(im, Image.Image):
                mn = MCM.mat_na(im)
                if mn:
                    mo_ds.append((round(t0, 3), round(t1, 3), mn))
        for b in check_safe(hop, kind):
            warn.append(f"{name}: {b}")
        # r36: phụ đề bộ mới — mọi PNG cùng 1 kiểu, chỉ khác chữ: soát màu lớp phụ đề đầu tiên là đủ (kiem_mau ≈1s / lớp)
        if kind != "sticker" and not (pd_st and kind == "phu_de" and any(l["loai"] == "phu_de" for l in layers[:-1])):
            warn.extend(kiem_mau(im, name))  # sticker linh vật có má hồng; còn lại chỉ màu Poly

    y_hook = {"tren": 230 if k.get("chu") == "toi_gian" else 260, "giua": 900}.get(k.get("vi_tri_chu"), 600)
    kr = lambda kv, ten: chu_rieng.kiem(kv, ten, warn, sys.modules[__name__])  # kiểu riêng 1 chữ: {} = vẽ y hệt cũ
    if chu.get("hook"):
        bt, kh = bo_chu(kr(chu.get("kieu_hook"), "hook"))
        if k["mo_dau"] == "hoi_truoc":
            im, hop = block(chu["hook"], k["chu"], 760, sizes=(104, 84), **kh, **kb(bt), **dat_cho(vt.get("hook")))
        else:
            im, hop = block(chu["hook"], k["chu"], y_hook, **kh, **kb(bt), **dat_cho(vt.get("hook")))
        add(im, hop, "hook.png", tl["hook_t"][0], tl["hook_t"][1], 1, "hook", mo=bt if MCM.la_kinh(bt, "hook") else None)
    if chu.get("ket"):
        im, hop = end_card(chu["ket"], k["ket"], **kb(bm), **dat_cho(vt.get("ket"), chi_y=True))
        add(im, hop, "ket.png", tl["ket_t"][0], tl["ket_t"][1], 1, "ket", mo=bm if MCM.la_kinh(bm, "ket") else None)
    if chu.get("brand", True):
        im, hop = brand(k["chu"], **kb(bm), **dat_cho(vt.get("brand")))
        add(im, hop, "brand.png", 0, tl["T"], 2, "brand", mo=bm if MCM.la_kinh(bm, "brand") else None)
    tg = chu.get("the_gia")
    if tg:
        bt, kh = bo_chu(kr(tg.get("kieu"), "thẻ giá"))
        them = {x: tg[x] for x in ("gia_cu", "ghi_chu") if bt and tg.get(x) not in (None, "")}   # r36: chỉ bộ mới dùng
        im, hop = price_card(tg["gia"], tg.get("phu"), k["chu"], **kh, **kb(bt), **them, **dat_cho(tg.get("vi_tri")))
        add(im, hop, "the-gia.png", tg["t0"], tg["t1"], 1, "gia", mo=bt if MCM.la_kinh(bt, "gia") else None)
    ket_t0 = tl["ket_t"][0] if chu.get("ket") else None
    if chu.get("tieu_de"):  # tiêu đề ghim: từ lúc hook tắt tới thẻ kết
        a = tl["hook_t"][1] if chu.get("hook") else 0.0
        b = ket_t0 if ket_t0 is not None else tl["T"]
        if b - a > 0.5:
            bt, kh = bo_chu(kr(chu.get("kieu_tieu_de"), "tiêu đề"))
            im, hop = tieu_de_ghim(chu["tieu_de"], **kh, **kb(bt), **dat_cho(vt.get("tieu_de")))
            add(im, hop, "tieu-de.png", a, b, 1, "tieu_de", mo=bt if MCM.la_kinh(bt, "tieu_de") else None)
    for i, n in enumerate(chu.get("nhan_chu") or []):  # nhãn từ khoá to giữa khung
        t0, t1 = float(n["t0"]), float(n["t1"])
        if ket_t0 is not None:
            t1 = min(t1, ket_t0)
        if t1 - t0 < 0.2:
            warn.append(f"nhãn {i + 1} '{n['chu']}': quá ngắn hoặc đè thẻ kết, bỏ")
            continue
        bt, kn = bo_chu(kr(n.get("kieu"), f"nhãn {i + 1}"))
        dc = dat_cho(n.get("vi_tri"))  # r31: chỗ anh kéo
        if bt:   # r36: bộ mẫu mới — nhãn của bộ, tên máy -> thẻ tên máy của bộ (tag / thông số chỉ lấy từ kế hoạch = kho)
            la_ten = n.get("loai") == "ten_may" or (n.get("loai") is None and la_ten_may(n["chu"]))
            tm = {"ten_may": {"tag": n.get("tag"), "thong_so": n.get("thong_so")}} if la_ten else {}
            im, hop = nhan_to(n["chu"], int(n.get("y", 700)), int(n.get("co", 92)), **kb(bt), **tm, **dc)
            add(im, hop, f"nhan-{i + 1:02d}.png", t0, t1, 1, "nhan", mo=bt if MCM.la_kinh(bt, "nhan") else None)
            continue
        if chu_rieng.co_mau(kn.get("kieu")):  # có mẫu chữ (màu / viền / nền…): vẽ theo mẫu, mọi loại nhãn
            if k["chu"] == "toi_gian":
                t1 = min(t1, t0 + float(n.get("giay", 2.5)))
            im, hop = nhan_to(n["chu"], int(n.get("y", 700)), int(n.get("co", 92)), **kn, **dc)
        elif k["chu"] == "toi_gian":  # nhãn gọn góc trên trái, chỉ hiện lúc đổi ý
            t1 = min(t1, t0 + float(n.get("giay", 2.5)))
            im, hop = nhan_gon(n["chu"], int(n.get("y", 258)), **kn, **dc)
        elif n.get("loai") == "ten_may" or (n.get("loai") is None and la_ten_may(n["chu"])):
            # 29/10: nhãn là tên máy -> thẻ tên máy (thông số / tag chỉ lấy từ kế hoạch = kho, không tự thêm). Lệch trái
            # 20px + rộng ≤ 820 để mép phải không lấn cột nút (x ≤ 950).
            arg = dict(ten=n["chu"], tag=n.get("tag"), thong_so=n.get("thong_so"), y0=int(n.get("y", 700)), cx=520, max_w=820,
                       co=int(n.get("co", 92)), **kn, **dc)
            phan, hop = the_ten_may(**arg)
            im = ghep_phan(phan)
            TEN_MAY[f"nhan-{i + 1:02d}.png"] = arg
        else:
            im, hop = nhan_to(n["chu"], int(n.get("y", 700)), int(n.get("co", 92)), **kn, **dc)
        add(im, hop, f"nhan-{i + 1:02d}.png", t0, t1, 1, "nhan")
    for i, st in enumerate(chu.get("sticker") or []):  # sticker Poly (sticker_poly.py)
        t0, t1 = float(st["t0"]), float(st["t1"])
        if ket_t0 is not None:
            t1 = min(t1, ket_t0)
        if t1 - t0 < 0.3:
            warn.append(f"sticker {i + 1} '{st['ten']}': quá ngắn hoặc đè thẻ kết, bỏ")
            continue
        if not os.path.exists(os.path.join(STICKER_DIR, f"{st['ten']}.png")):
            warn.append(f"sticker '{st['ten']}' không có trong {STICKER_DIR} — chạy sticker_poly.py trước")
            continue
        im, hop = sticker(st["ten"], int(st.get("x", 800)), int(st.get("y", 1000)), int(st.get("co", 320)))
        add(im, hop, f"sticker-{i + 1:02d}.png", t0, t1, 1, "sticker")
    cum_ngan = (pd_st.get("loai") == "cum") if pd_st else (k.get("phu_de") == "cum_ngan")
    cau_moi = bool(pd_st) and not cum_ngan
    mo_pd = bm if (pd_st and MCM.la_kinh(bm, "phu_de", pd_st)) else None
    if cum_ngan:
        dem = {}
        for txt, a, b, hl, n in (cac_cum(tl, warn) if pd_st else cac_cum(tl)):
            dem[n] = dem.get(n, 0) + 1
            im, hop = sub_cum(txt, hl, k["chu"], **kpd, **({"bo": bm, "pd": pd_st["id"], "_v": MCM.PHIEN} if pd_st else {}))
            add(im, hop, f"phu-de-{n + 1:02d}-{dem[n]}.png", a, b, 1, "phu_de", mo=mo_pd)
    if cau_moi:   # r36: cả câu kiểu bộ mới — 1 PNG mỗi từ (từ đang đọc khác nhau), giờ như phụ đề ASS cả câu cũ (write_ass)
        items = tl.get("phu_de") or []
        het = tl["ket_t"][0] if chu.get("ket") else tl["T"]
        for n, s in enumerate(items):
            words = [w for w in gio_tung_tu(s) if w[1] < het - 0.05]
            if not words:
                continue
            ws = [in_hoa(str(w)).replace("|", "") for w, _, _ in words]
            cau = in_hoa(str(s.get("chu") or ""))
            if len(cau.replace("|", " ").split()) != len(ws):
                cau = " ".join(ws)
            if len(words) > 8:
                warn.append(f"phụ đề {n + 1}: {len(words)} từ/màn (nên 3–6, tối đa 8)")
            sau = items[n + 1]["t0"] if n + 1 < len(items) else het
            het_cau = min(het, sau)
            for j, (w, a, b) in enumerate(words):
                t0_ = a if j else s["t0"]
                t1_ = min(het_cau, words[j + 1][1] if j + 1 < len(words) else max(b, s["t1"]))
                if t1_ <= t0_ + 0.01:
                    continue
                im, hop = subtitle(cau, s.get("nhan"), k["chu"], **kpd, bo=bm, pd=pd_st["id"], dang_doc=j, _v=MCM.PHIEN)
                add(im, hop, f"phu-de-{n + 1:02d}-{j + 1}.png", t0_, t1_, 1, "phu_de", mo=mo_pd)
    for i, s in enumerate([] if (cum_ngan or cau_moi) else (tl.get("phu_de") or [])):
        if s["chu"].count("|") >= 2:
            warn.append(f"phụ đề {i + 1}: hơn 2 dòng ('|'), đã gộp vào dòng 2 — nên tách thành 2 câu")
        t0, t1 = s["t0"], s["t1"]
        if ket_t0 is not None and t1 > ket_t0:  # phụ đề không đè thẻ kết
            if t0 >= ket_t0 - 0.3:
                continue
            t1 = ket_t0
        im, hop = subtitle(s["chu"], s.get("nhan"), k["chu"], **kpd)
        add(im, hop, f"phu-de-{i + 1:02d}.png", t0, t1, 1, "phu_de")
    bo_dang = BO["ten"]
    BO["ten"] = "poly_goc"  # phụ đề ASS (dựng máy chủ) hiện bằng Be Vietnam Pro: đo cỡ bằng đúng font đó
    try:
        # r36: bộ mẫu mới -> phụ đề là PNG cả 2 đường (khung xem = bản xuất), không ghi ASS
        ass = None if pd_st else (write_ass_cum if cum_ngan else write_ass)(tl, outdir, k["chu"], warn)
    finally:
        BO["ten"] = bo_dang
    for txt, co in dict.fromkeys(CHU_NHO):
        warn.append(f"chữ '{txt[:40]}' phải thu còn {co}px (quá dài) — rút ngắn hoặc tách dòng")
    # lớp chữ đè nhau (cùng lúc + chồng vị trí), trừ POLY STORE
    ds = [l for l in layers if l["ten"] != "brand.png"]
    for i, a in enumerate(ds):
        for b in ds[i + 1:]:
            if a["ten"].startswith("phu-de-") and b["ten"].startswith("phu-de-"):
                continue
            cung_luc = min(a["t1"], b["t1"]) - max(a["t0"], b["t0"]) > 0.05
            ha, hb = a["hop"], b["hop"]
            chong = min(ha[2], hb[2]) - max(ha[0], hb[0]) > 4 and min(ha[3], hb[3]) - max(ha[1], hb[1]) > 4
            if cung_luc and chong:
                warn.append(f"{a['ten']} đè {b['ten']} lúc {max(a['t0'], b['t0']):.1f}–{min(a['t1'], b['t1']):.1f}s — dời y hoặc giờ")
    if CHU_GHEP:
        ghep, so_track, che_do = ghep_cho_premiere(layers, outdir, tach_phu_de=(k["chu"] == "toi_gian" and cum_ngan)), 3, "ghep"
        bo = [m for m, v in (("diem_nhan", "chop_trang"), ("lop_phu", "toi_vien"), ("lop_phu", "loa_sang"), ("thanh_tien_trinh", "co"),
                             ("hoat_hinh", "mov")) if k.get(m) == v]
        if bo:
            warn.append("--chu-ghep: không làm được " + ", ".join(bo) + " (cần lớp riêng track) — ghi kiểu vào lịch sử nhớ bỏ các mục này")
    else:
        MOV.clear()
        if k.get("hoat_hinh") == "mov":
            dung_mov(tl, layers, outdir, warn)
        (ghep, so_track), che_do = lop_rieng(layers, outdir, tl), "lop_rieng"
    am = None
    if k.get("am_nhan") == "co":  # âm nhấn tự tổng hợp (am_nhan.py), chép cùng thư mục chữ, lenh_premiere đặt lên A3
        import am_nhan
        am = am_nhan.tao(outdir)
    them = {}   # r36: chỉ có khi dùng bộ mẫu mới (kế hoạch cũ: lop-chu.json y hệt)
    if pd_st:   # dung_may_chu: mọi lớp phụ đề PNG thành 1 đầu vào (chuỗi ảnh, chỗ trống = ảnh trong suốt), nhẹ hơn mỗi cụm 1 đầu vào
        trong = os.path.join(outdir, "pd-trong.png")
        Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(trong)
        them["pd_chuoi"] = {"trong": trong}
    if mo_ds:   # kính (dựng máy chủ): mặt nạ theo đoạn giờ -> dung_may_chu làm mờ cảnh dưới thẻ
        ds_mo, hop_mo = MCM.ghi_mat_na(mo_ds, outdir)
        if ds_mo:
            trong = os.path.join(outdir, "mo-trong.png")
            Image.new("L", (W, H), 0).save(trong)
            them["mo_nen"] = {"sigma": max(l["mo_nen"] for l in layers if l.get("mo_nen")), "bao_hoa": MCM.bao_hoa(bm),
                              "ds": ds_mo, "hop": hop_mo, "trong": trong}
    json.dump({"lop": layers, "lop_premiere": ghep, "che_do_premiere": che_do, "so_track_hinh": max(3, so_track),
               "am_nhan": am, "canh_bao": warn, "ass": ass,
               "font_dir": os.path.abspath(FONT_DIR) if FONT_DIR else None, **them},
              open(os.path.join(outdir, "lop-chu.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return layers, warn


def main():
    global FONT_DIR
    argv = [a for a in sys.argv if not a.startswith("--")]  # --chu-ghep: đọc ở CHU_GHEP
    tl = json.load(open(argv[1], encoding="utf-8"))
    if len(argv) > 3:
        FONT_DIR = argv[3]
    layers, warn = render(tl, argv[2])
    print(json.dumps({"so_lop": len(layers), "canh_bao": warn}, ensure_ascii=False))


if __name__ == "__main__":
    main()
