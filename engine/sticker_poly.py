#!/usr/bin/env python3
"""Bộ sticker riêng của Poly Store: linh vật "bé Poly" (điện thoại xanh lục bảo viền trắng như logo, mặt trên màn hình)
với các biểu cảm hay dùng trên kênh. Thay cho sticker nhân vật có bản quyền (minion, mèo meme).

Dùng:  python3 sticker_poly.py <thu_muc_ra> [<thu_muc_font>]
Ra:    <thu_muc_ra>/<ten>.png (nền trong suốt, viền trắng kiểu sticker, cạnh dài 600px) + bang-sticker.jpg (xem nhanh)
Cần:   Playwright + Chromium (có sẵn trên máy chủ Claude) để vẽ SVG; Pillow; font Be Vietnam Pro Black.
Dùng trong video: ke-hoach.json -> chu.sticker = [{"ten": "omg", "t0": 4.0, "t1": 5.5, "x": 800, "y": 1000, "co": 340}]
"""
import base64, os, sys
from PIL import Image, ImageFilter

import chung

XANH = "#074D3A"  # xanh lục bảo Poly (29/10, anh: "tone xanh sang hơn, đừng xanh lè"; tới 28/10: #064E24) — cùng ve_chu.XANH_POLY
XANH_SANG = "#13684F"  # đầu sáng của dải thân (tới 28/10: #0B6B35)
VANG = "#FFD600"
HONG = "#FF8FA3"
TRANG = "#FFFFFF"
W, H = 720, 720  # nội dung vẽ trong khung 600 rộng, dời vào giữa 60px để tay vẫy / bong bóng không bị cắt

# ten: (mắt, miệng, tay, chữ, phụ kiện)
BO = {
    "omg": ("ngac", "o", "ma", "OMG!", None),
    "he-he": ("gian", "nhech", "xuong", "HẸ HẸ", None),
    "mua": ("sao", "ha", "gio", "MUA!", None),
    "luu-lien": ("nhay", "cuoi", "chi", "LƯU LIỀN!", "bookmark"),
    "chot-don": ("cong", "cuoi_to", "like", "CHỐT ĐƠN", None),
    "xin-xo": ("tim", "cuoi_to", "gio", "XỊN XÒ", None),
    "hoi-poly": ("tron", "cuoi", "vay", "HỎI POLY NHA", "bong"),
    "cam-on": ("cong", "cuoi", "vay", "CẢM ƠN ĐÃ XEM", "tim_bay"),
}


def mat(kieu, cx, cy, ben):
    """1 con mắt tại (cx, cy); ben = -1 trái / 1 phải."""
    g = XANH
    if kieu == "tron":
        return (f'<ellipse cx="{cx}" cy="{cy}" rx="17" ry="23" fill="{g}"/>'
                f'<circle cx="{cx + 6}" cy="{cy - 8}" r="6" fill="{TRANG}"/>')
    if kieu == "ngac":
        return (f'<circle cx="{cx}" cy="{cy}" r="26" fill="{TRANG}" stroke="{g}" stroke-width="7"/>'
                f'<circle cx="{cx}" cy="{cy + 2}" r="9" fill="{g}"/>')
    if kieu == "cong":
        return f'<path d="M{cx - 20},{cy + 8} Q{cx},{cy - 18} {cx + 20},{cy + 8}" fill="none" stroke="{g}" stroke-width="9" stroke-linecap="round"/>'
    if kieu == "gian":
        return (f'<path d="M{cx - 19},{cy} A19,17 0 0 0 {cx + 19},{cy} Z" fill="{g}"/>'
                f'<line x1="{cx - 24}" y1="{cy - 2}" x2="{cx + 24}" y2="{cy - 2 + ben * 4}" stroke="{g}" stroke-width="8" stroke-linecap="round"/>')
    if kieu == "nhay":
        if ben < 0:
            return mat("tron", cx, cy, ben)
        return f'<path d="M{cx - 20},{cy + 2} Q{cx},{cy - 14} {cx + 20},{cy + 2}" fill="none" stroke="{g}" stroke-width="9" stroke-linecap="round"/>'
    if kieu == "sao":
        import math
        pts = []
        for i in range(10):
            r = 28 if i % 2 == 0 else 12
            a = -math.pi / 2 + i * math.pi / 5
            pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
        return f'<polygon points="{" ".join(pts)}" fill="{VANG}" stroke="{g}" stroke-width="5" stroke-linejoin="round"/>'
    if kieu == "tim":
        return (f'<path d="M{cx},{cy + 22} C{cx - 34},{cy} {cx - 26},{cy - 26} {cx},{cy - 12} '
                f'C{cx + 26},{cy - 26} {cx + 34},{cy} {cx},{cy + 22} Z" fill="#FF3B5C" stroke="{g}" stroke-width="5" stroke-linejoin="round"/>')
    return ""


def mieng(kieu, cx, cy):
    g = XANH
    if kieu == "cuoi":
        return f'<path d="M{cx - 30},{cy - 4} Q{cx},{cy + 26} {cx + 30},{cy - 4}" fill="none" stroke="{g}" stroke-width="9" stroke-linecap="round"/>'
    if kieu == "cuoi_to":
        return (f'<path d="M{cx - 36},{cy - 8} Q{cx},{cy + 50} {cx + 36},{cy - 8} Z" fill="{g}" stroke="{g}" stroke-width="6" stroke-linejoin="round"/>'
                f'<path d="M{cx - 16},{cy + 18} Q{cx},{cy + 8} {cx + 16},{cy + 18} Q{cx},{cy + 32} {cx - 16},{cy + 18} Z" fill="{HONG}"/>')
    if kieu == "ha":
        return (f'<ellipse cx="{cx}" cy="{cy + 10}" rx="38" ry="30" fill="{g}"/>'
                f'<ellipse cx="{cx}" cy="{cy + 26}" rx="20" ry="11" fill="{HONG}"/>')
    if kieu == "o":
        return f'<ellipse cx="{cx}" cy="{cy + 12}" rx="17" ry="22" fill="{g}"/>'
    if kieu == "nhech":
        return f'<path d="M{cx - 28},{cy + 6} Q{cx + 6},{cy + 22} {cx + 32},{cy - 10}" fill="none" stroke="{g}" stroke-width="9" stroke-linecap="round"/>'
    return ""


def tay(path, ngon_cai=False, vay=False):
    """Cánh tay = đường xanh đậm có viền trắng + bàn tay tròn ở cuối."""
    end = path.split()[-1].split(",")
    ex, ey = float(end[0]), float(end[1])
    s = (f'<path d="{path}" fill="none" stroke="{TRANG}" stroke-width="40" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<path d="{path}" fill="none" stroke="{XANH}" stroke-width="24" stroke-linecap="round" stroke-linejoin="round"/>'
         f'<circle cx="{ex}" cy="{ey}" r="25" fill="{XANH}" stroke="{TRANG}" stroke-width="8"/>')
    if ngon_cai:
        s += (f'<rect x="{ex - 9}" y="{ey - 52}" width="18" height="40" rx="9" fill="{XANH}" stroke="{TRANG}" stroke-width="7"/>'
              f'<circle cx="{ex}" cy="{ey}" r="21" fill="{XANH}"/>')
    if vay:
        s += "".join(f'<path d="M{ex + 34 + 10 * i},{ey - 30 + 2 * i} q12,22 0,44" fill="none" stroke="{TRANG}" stroke-width="7" stroke-linecap="round" opacity="0.95"/>'
                     for i in range(2))
    return s


def tay_kieu(kieu):
    L, R = (178, 330), (422, 330)
    if kieu == "xuong":
        return tay(f"M{L[0]},{L[1]} Q140,380 150,430") + tay(f"M{R[0]},{R[1]} Q460,380 450,430")
    if kieu == "gio":
        return tay(f"M{L[0]},{L[1]} Q120,260 110,190") + tay(f"M{R[0]},{R[1]} Q480,260 490,190")
    if kieu == "ma":  # hai tay áp má
        return tay(f"M{L[0]},{L[1] + 40} Q140,330 214,292") + tay(f"M{R[0]},{R[1] + 40} Q460,330 386,292")
    if kieu == "chi":
        return tay(f"M{L[0]},{L[1]} Q140,380 150,430") + tay(f"M{R[0]},{R[1]} Q470,280 505,210")
    if kieu == "like":
        return tay(f"M{L[0]},{L[1]} Q140,380 150,430") + tay(f"M{R[0]},{R[1]} Q480,320 480,260", ngon_cai=True)
    if kieu == "vay":
        return tay(f"M{L[0]},{L[1]} Q140,380 150,430") + tay(f"M{R[0]},{R[1]} Q480,280 470,200", vay=True)
    return ""


def phu_kien(k):
    if k == "bookmark":
        return (f'<path d="M500,90 h62 v92 l-31,-22 l-31,22 Z" fill="{VANG}" stroke="#111" stroke-width="7" stroke-linejoin="round"/>')
    if k == "bong":
        return (f'<path d="M470,60 h110 a22,22 0 0 1 22,22 v46 a22,22 0 0 1 -22,22 h-70 l-26,26 v-26 h-14 a22,22 0 0 1 -22,-22 v-46 a22,22 0 0 1 22,-22 Z" '
                f'fill="{TRANG}" stroke="{XANH}" stroke-width="7"/>'
                f'<circle cx="503" cy="105" r="8" fill="{XANH}"/><circle cx="527" cy="105" r="8" fill="{XANH}"/><circle cx="551" cy="105" r="8" fill="{XANH}"/>')
    if k == "tim_bay":
        return "".join(f'<path transform="translate({x},{y}) scale({s})" d="M0,18 C-28,0 -21,-21 0,-10 C21,-21 28,0 0,18 Z" fill="#FF3B5C" stroke="{TRANG}" stroke-width="4"/>'
                       for x, y, s in ((90, 150, 1.0), (520, 110, 1.3), (470, 60, 0.8)))
    return ""


def svg(ten, font_b64):
    m, mi, t, chu, pk = BO[ten]
    co = 74 if len(chu) <= 9 else (60 if len(chu) <= 13 else 52)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<style>@font-face {{ font-family: BVP; src: url(data:font/ttf;base64,{font_b64}); }}</style>
<linearGradient id="than" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{XANH_SANG}"/><stop offset="1" stop-color="{XANH}"/></linearGradient>
</defs>
<g transform="translate(60,0)">
<!-- chân -->
<g stroke-linecap="round">
<line x1="255" y1="520" x2="250" y2="575" stroke="{TRANG}" stroke-width="40"/><line x1="255" y1="520" x2="250" y2="575" stroke="{XANH}" stroke-width="24"/>
<line x1="345" y1="520" x2="350" y2="575" stroke="{TRANG}" stroke-width="40"/><line x1="345" y1="520" x2="350" y2="575" stroke="{XANH}" stroke-width="24"/>
<ellipse cx="240" cy="582" rx="34" ry="17" fill="{XANH}" stroke="{TRANG}" stroke-width="7"/>
<ellipse cx="360" cy="582" rx="34" ry="17" fill="{XANH}" stroke="{TRANG}" stroke-width="7"/>
</g>
{"" if t == "ma" else tay_kieu(t)}
<!-- thân điện thoại -->
<rect x="180" y="110" width="240" height="420" rx="58" fill="url(#than)" stroke="{TRANG}" stroke-width="16"/>
<rect x="272" y="128" width="56" height="12" rx="6" fill="{TRANG}" opacity="0.9"/>
<rect x="204" y="156" width="192" height="270" rx="38" fill="#F3FBF5"/>
{mat(m, 262, 250, -1)}{mat(m, 338, 250, 1)}
<ellipse cx="236" cy="300" rx="16" ry="9" fill="{HONG}" opacity="0.75"/><ellipse cx="364" cy="300" rx="16" ry="9" fill="{HONG}" opacity="0.75"/>
{mieng(mi, 300, 318)}
{tay_kieu(t) if t == "ma" else ""}
<!-- chữ p của logo -->
<circle cx="300" cy="470" r="20" fill="none" stroke="{TRANG}" stroke-width="9"/>
<path d="M280,470 v34" stroke="{TRANG}" stroke-width="9" stroke-linecap="round"/>
{phu_kien(pk)}
<text x="300" y="672" text-anchor="middle" font-family="BVP" font-size="{co}" fill="{VANG}" stroke="#111" stroke-width="14"
 stroke-linejoin="round" paint-order="stroke" transform="rotate(-5 300 650)">{chu}</text>
</g>
</svg>'''


def vien_trang(im, d=11):
    """Viền trắng + bóng mờ kiểu sticker quanh phần không trong suốt; cắt sát, cạnh dài 600px."""
    a = im.split()[-1]
    to = a.filter(ImageFilter.MaxFilter(2 * d + 1))
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    bong = Image.new("RGBA", im.size, (0, 0, 0, 90))
    out.paste(bong, (5, 8), to.filter(ImageFilter.GaussianBlur(7)))
    out.paste(Image.new("RGBA", im.size, (255, 255, 255, 255)), (0, 0), to)
    out.alpha_composite(im)
    bb = out.getbbox()
    out = out.crop((max(0, bb[0] - 6), max(0, bb[1] - 6), min(im.width, bb[2] + 8), min(im.height, bb[3] + 10)))
    k = 600 / max(out.size)
    return out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)


def main():
    ra = sys.argv[1]
    fdir = sys.argv[2] if len(sys.argv) > 2 else chung.FONT_DIR
    os.makedirs(ra, exist_ok=True)
    font_b64 = base64.b64encode(open(os.path.join(fdir, "BeVietnamPro-Black.ttf"), "rb").read()).decode()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        for ten in BO:
            pg.set_content(f'<html><body style="margin:0;background:transparent">{svg(ten, font_b64)}</body></html>')
            pg.wait_for_timeout(150)
            tmp = os.path.join(ra, f"_{ten}.png")
            pg.locator("svg").screenshot(path=tmp, omit_background=True)
            im = Image.open(tmp).convert("RGBA")
            os.remove(tmp)
            vien_trang(im, 22).save(os.path.join(ra, f"{ten}.png"))
        b.close()
    # bảng xem nhanh trên nền xám carô
    o = 300
    sheet = Image.new("RGB", (o * 4, o * 2), (200, 200, 200))
    for i, ten in enumerate(BO):
        im = Image.open(os.path.join(ra, f"{ten}.png"))
        im.thumbnail((o - 20, o - 20))
        x, y = (i % 4) * o, (i // 4) * o
        nen = Image.new("RGB", (o, o), (120, 120, 120) if (i // 4 + i) % 2 else (90, 90, 90))
        sheet.paste(nen, (x, y))
        sheet.paste(im, (x + (o - im.width) // 2, y + (o - im.height) // 2), im)
    sheet.save(os.path.join(ra, "bang-sticker.jpg"), quality=90)
    print({"so_sticker": len(BO), "ra": ra, "ten": list(BO)})


if __name__ == "__main__":
    main()
