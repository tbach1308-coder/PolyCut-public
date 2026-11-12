#!/usr/bin/env python3
"""Chữ động dựng sẵn thành video nền trong suốt (MOV, mã PNG có alpha) để đặt thẳng lên Premiere.

29/10 — anh: "sáng tạo lên, đừng làm mấy cái basic". Chạy thật trên Premiere 26.5.2: MOV alpha (qtrle / png) nhập và xuất
đúng nền trong suốt. Mỗi lớp động = 1 clip (đặt + Position), ít bước hơn keyframe từng thông số, chuyển động tự do hơn.
Khung luôn rộng 1080 (đúng bề ngang sequence: Premiere có đặt "scale to frame size" cũng không đổi cỡ), cao = dải chứa chữ;
Position = tâm dải.

  hook_mov   khối tiêu đề (mọi kiểu chữ): khung 0 đã đủ chữ (làm ảnh bìa) → nảy nhẹ từng phần lệch nhịp, vệt sáng quét qua
             dòng chính, sao lấp lánh, "thở" rất nhẹ khi đứng yên
  gia_mov    thẻ giá "đóng dấu": đập từ 230% xuống, nghiêng −6°, rung tắt dần, tia bụi bung ra, vệt sáng
  ten_may    thẻ tên máy (ve_chu.the_ten_may): thẻ nảy, tên lộ dần, phần vàng bật, viên thông số bật lần lượt, vệt sáng
  karaoke    phụ đề từng từ: cụm 2–4 từ IN HOA, từ hiện đúng lúc nói (nảy), từ đang nói nằm trên viên thuốc xanh đậm Poly
             chữ trắng, từ khoá (số, giá, tên máy, `nhan`) vàng; mỗi câu 1 file
Không dùng tài nguyên ngoài: chữ vẽ bằng font của bộ (ve_chu.font), mọi hình vẽ bằng PIL.
"""
import math, os, shutil, subprocess, tempfile
from chung import FFMPEG
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageChops, ImageDraw, ImageFilter

W, H, FPS = 1080, 1920, 30


def ma_hoa(thu_muc_khung, ra, fps=FPS):
    """PNG khung -> MOV mã PNG (rgba; nhẹ hơn qtrle ~2,5 lần khi có bóng mờ): có alpha, Premiere đọc được, vùng trong suốt nén rất gọn."""
    r = subprocess.run([FFMPEG, "-v", "error", "-y", "-framerate", str(fps), "-i", os.path.join(thu_muc_khung, "%05d.png"),
                        "-c:v", "png", "-pix_fmt", "rgba", ra], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg (MOV alpha) lỗi: " + r.stderr[-800:])
    return ra


def _vung(layers, le=70):
    """Dải y chứa mọi lớp (+ lề cho nảy / bóng). Chiều cao chẵn."""
    bb = [l.getbbox() for l in layers if l.getbbox()]
    y0 = max(0, min(b[1] for b in bb) - le)
    y1 = min(H, max(b[3] for b in bb) + le)
    if (y1 - y0) % 2:
        y1 = min(H, y1 + 1) if y1 < H else y1 - 1
    return y0, y1


def _co_gian(lp, s, cx, cy, goc=0.0):
    """Phóng lp (RGBA) quanh (cx, cy) theo s (+ xoay goc độ), giữ nguyên khổ."""
    if abs(s - 1) < 1e-3 and not goc:
        return lp
    bb = lp.getbbox()
    if not bb:
        return lp
    crop = lp.crop(bb)
    if goc:
        crop = crop.rotate(goc, resample=Image.BICUBIC, expand=True)
    nw, nh = max(1, int(crop.width * s)), max(1, int(crop.height * s))
    crop = crop.resize((nw, nh), Image.BICUBIC)
    ocx, ocy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    # giữ tâm phần tử, dời theo tâm nhóm
    ncx, ncy = cx + (ocx - cx) * s, cy + (ocy - cy) * s
    out = Image.new("RGBA", lp.size, (0, 0, 0, 0))
    out.paste(crop, (int(round(ncx - nw / 2)), int(round(ncy - nh / 2))), crop)  # paste cắt được phần lọt ra ngoài khung
    return out


def _vet_sang(lp, p, rong=110, manh=190):
    """Vệt sáng chéo đi qua lớp lp tại tiến độ p (0..1), chỉ phủ trên phần có chữ / hộp (theo alpha của lp)."""
    bb = lp.getbbox()
    if not bb or not (0 <= p <= 1):
        return lp
    x0, y0, x1, y1 = bb
    span = (x1 - x0) + (y1 - y0) + 2 * rong
    cx = x0 - rong - (y1 - y0) + p * span
    band = Image.new("L", lp.size, 0)
    d = ImageDraw.Draw(band)
    d.polygon([(cx, y0), (cx + rong, y0), (cx + rong + (y1 - y0) * 0.6, y1), (cx + (y1 - y0) * 0.6, y1)], fill=manh)
    band = band.filter(ImageFilter.GaussianBlur(rong / 4))
    band = ImageChops.multiply(band, lp.split()[-1])
    trang = Image.new("RGBA", lp.size, (255, 255, 255, 0))
    trang.putalpha(band)
    out = lp.copy()
    out.alpha_composite(trang)
    return out


def _bong(im, dx=4, dy=8, mo=9, dam=115):
    a = im.split()[-1]
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", im.size, (0, 0, 0, dam)), (dx, dy), a.filter(ImageFilter.GaussianBlur(mo)))
    sh.alpha_composite(im)
    return sh


def _nay(x, bien=0.09):
    """Nảy tắt dần: 0 ở x ≤ 0, đỉnh ~bien ở x≈0.25, về 0 ở x ≥ 1."""
    if x <= 0 or x >= 1:
        return 0.0
    return bien * math.sin(math.pi * x * 1.6) * (1 - x) ** 1.5 * 2.2


def hook_mov(phan, dur, ra, fps=FPS, bong=True):
    """phan: [(lớp RGBA toàn khung, vai)] (ve_chu.khoi_tieu_de / bubble…). Trả (đường dẫn mov, vi_tri [x, y] 0–1, số khung)."""
    layers = [l for l, _ in phan]
    y0, y1 = _vung(layers)
    phan = [(l.crop((0, y0, W, y1)), v) for l, v in phan]
    allbb = [l.getbbox() for l, _ in phan if l.getbbox()]
    gcx = (min(b[0] for b in allbb) + max(b[2] for b in allbb)) / 2
    gcy = (min(b[1] for b in allbb) + max(b[3] for b in allbb)) / 2
    n = max(1, int(round(dur * fps)))
    tre = {"chinh": 0.0, "phu": 0.08, "sao": 0.0}
    sang = [0.45] + ([dur - 1.1] if dur > 2.8 else [])
    tmp = tempfile.mkdtemp(prefix="hh-")
    try:
        def khung(i):
            t = i / fps
            s_nhom = 1 + _nay((t - 0.03) / 0.5, 0.06)  # 29/10: bỏ "thở" sau 0,7s — phóng lại từng khung làm chữ nhoè
            out = Image.new("RGBA", (W, y1 - y0), (0, 0, 0, 0))
            for lp, vai in phan:
                if vai == "sao":
                    pha = (t * 1.7 + (hash(id(lp)) % 7) / 7.0) % 1.0
                    s = 0.75 + 0.35 * abs(math.sin(math.pi * pha))
                    lp2 = _co_gian(lp, s * s_nhom, gcx, gcy)
                else:
                    s = s_nhom + _nay((t - tre[vai] - 0.03) / 0.45, 0.07 if vai == "phu" else 0.0)
                    lp2 = _co_gian(lp, s, gcx, gcy)
                    if vai == "chinh":
                        for a in sang:
                            if a <= t <= a + 0.45:
                                lp2 = _vet_sang(lp2, (t - a) / 0.45)
                out.alpha_composite(lp2)
            if bong:
                out = _bong(out)
            out.save(os.path.join(tmp, f"{i:05d}.png"))
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(khung, range(n)))
        ma_hoa(tmp, ra, fps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ra, [0.5, round((y0 + y1) / 2 / H, 4)], n


def gia_mov(lop, dur, ra, fps=FPS):
    """Thẻ giá đóng dấu: lop = ảnh thẻ giá toàn khung (ve_chu.price_card). Khung 0 chưa có thẻ (thẻ đập xuống trong 0,16s)."""
    y0, y1 = _vung([lop], le=170)
    lp = lop.crop((0, y0, W, y1))
    bb = lp.getbbox()
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    n = max(1, int(round(dur * fps)))
    tmp = tempfile.mkdtemp(prefix="hh-")
    try:
        def khung(i):
            t = i / fps
            if t < 0.16:
                u = t / 0.16
                s, goc, op = 2.3 - 1.36 * (u * u), -6 * u, min(1.0, u * 2.5)
            elif t < 0.34:
                u = (t - 0.16) / 0.18
                s, goc, op = 0.94 + 0.06 * math.sin(math.pi * u * 0.5) + 0.03 * math.sin(math.pi * u), -6, 1.0
            else:
                s, goc, op = 1.0 + (0.01 * math.sin(2 * math.pi * (t - 0.34) / 1.6)), -6, 1.0
            lp2 = _co_gian(lp, s, cx, cy, goc)
            if 0.16 <= t < 0.5:  # rung tắt dần sau cú đập
                k = (0.5 - t) / 0.34
                dx, dy = int(10 * k * math.sin(t * 90)), int(6 * k * math.cos(t * 70))
                lp3 = Image.new("RGBA", lp2.size, (0, 0, 0, 0))
                lp3.alpha_composite(lp2, (max(0, dx), max(0, dy)), (max(0, -dx), max(0, -dy)))
                lp2 = lp3
            if op < 1:
                a = lp2.split()[-1].point(lambda v: int(v * op))
                lp2.putalpha(a)
            if 0.62 <= t <= 1.1:
                lp2 = _vet_sang(lp2, (t - 0.62) / 0.48)
            out = Image.new("RGBA", lp.size, (0, 0, 0, 0))
            if 0.14 <= t < 0.5:  # tia bụi bung quanh thẻ
                u = (t - 0.14) / 0.36
                d = ImageDraw.Draw(out)
                rx, ry = (bb[2] - bb[0]) / 2, (bb[3] - bb[1]) / 2
                for j in range(10):
                    g = 2 * math.pi * j / 10 + 0.3
                    r0, r1 = 1.0 + 0.25 * u, 1.15 + 0.45 * u
                    a = int(230 * (1 - u))
                    d.line([(cx + math.cos(g) * rx * r0, cy + math.sin(g) * ry * r0),
                            (cx + math.cos(g) * rx * r1, cy + math.sin(g) * ry * r1)], fill=(255, 255, 255, a), width=7)
            out.alpha_composite(lp2)
            _bong(out).save(os.path.join(tmp, f"{i:05d}.png"))
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(khung, range(n)))
        ma_hoa(tmp, ra, fps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ra, [0.5, round((y0 + y1) / 2 / H, 4)], n


def _back(x):
    c1 = 1.70158
    x = min(1.0, max(0.0, x))
    return 1 + (c1 + 1) * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _mo(lp, op):
    if op >= 0.999:
        return lp
    out = lp.copy()
    out.putalpha(lp.split()[-1].point(lambda v: int(v * max(0.0, op))))
    return out


def _lo_trai_phai(lp, p):
    """Lộ dần từ trái sang phải (p 0..1) theo hộp chữ, mép mềm 40px."""
    bb = lp.getbbox()
    if not bb or p >= 1:
        return lp
    x = bb[0] + (bb[2] - bb[0] + 40) * max(0.0, p)
    m = Image.new("L", lp.size, 0)
    ImageDraw.Draw(m).rectangle([0, 0, int(x), lp.size[1]], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(14))
    out = lp.copy()
    out.putalpha(ImageChops.multiply(lp.split()[-1], m))
    return out


def ten_may_mov(phan, dur, ra, fps=FPS, bia=False):
    """Thẻ tên máy (ve_chu.the_ten_may). phan vai: the, ten, nhan, gach, tag, chip0…
    Hiện (bia=False): thẻ nảy lên 0,28s (92%→100%, back) · tag trượt từ trái · tên lộ trái→phải · phần vàng bật 135%→100% ·
    viên thông số bật lần lượt cách 0,07s · vệt sáng quét qua thẻ ở 0,8s · sau đó đứng yên, sắc nét.
    bia=True (hook làm ảnh bìa): khung 0 đã đủ thẻ; chỉ viên thông số nảy nhẹ lần lượt + vệt sáng. Trả (mov, vi_tri, số khung)."""
    layers = [l for l, _ in phan]
    y0, y1 = _vung(layers, le=90)
    phan = [(l.crop((0, y0, W, y1)), v) for l, v in phan]
    the = next((l for l, v in phan if v == "the"), phan[0][0])
    bb = the.getbbox()
    gcx, gcy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    chips = sorted([(int(v[4:]), l) for l, v in phan if v.startswith("chip")])
    n = max(1, int(round(dur * fps)))
    sang = [0.8] + ([dur - 1.0] if dur > 3.0 else [])
    tmp = tempfile.mkdtemp(prefix="hh-")
    try:
        def khung(i):
            t = i / fps
            # không "thở" (co giãn liên tục) sau khi hiện: phóng lại từng khung làm chữ / đường kẻ mảnh nhoè
            if bia:
                s_nhom, op_nhom = 1.0, 1.0
            else:
                u = min(1.0, t / 0.28)
                s_nhom = 0.92 + 0.08 * _back(u)
                op_nhom = min(1.0, t / 0.12)
            out = Image.new("RGBA", (W, y1 - y0), (0, 0, 0, 0))
            for lp, vai in phan:
                if vai.startswith("chip"):
                    continue
                lp2 = lp
                if not bia:
                    if vai == "ten":
                        lp2 = _lo_trai_phai(lp, (t - 0.10) / 0.30)
                    elif vai == "nhan":
                        u = (t - 0.32) / 0.2
                        if u <= 0:
                            continue
                        lp2 = _mo(_co_gian(lp, 1.35 - 0.35 * _back(min(1.0, u)), *_tam(lp)), min(1.0, u * 2.5))
                    elif vai == "gach":
                        lp2 = _lo_giua(lp, (t - 0.38) / 0.18)
                    elif vai == "tag":
                        u = (t - 0.12) / 0.2
                        if u <= 0:
                            continue
                        dx = int(-40 * (1 - _back(min(1.0, u))))
                        lp3 = Image.new("RGBA", lp.size, (0, 0, 0, 0))
                        lp3.alpha_composite(lp, (max(0, dx), 0), (max(0, -dx), 0))
                        lp2 = _mo(lp3, min(1.0, u * 2))
                if vai == "the":
                    for a in sang:
                        if a <= t <= a + 0.5:
                            lp2 = _vet_sang(lp2, (t - a) / 0.5, rong=140, manh=120)
                out.alpha_composite(_co_gian(lp2, s_nhom, gcx, gcy))
            for j, lp in chips:
                bat = (0.25 if bia else 0.48) + 0.07 * j
                u = (t - bat) / 0.22
                if u <= 0 and not bia:
                    continue
                if bia:
                    s = 1.0 + (0.08 * math.sin(math.pi * min(1.0, u)) if 0 < u < 1 else 0.0)
                    op = 1.0
                else:
                    s, op = 0.6 + 0.4 * _back(min(1.0, u)), min(1.0, u * 3)
                cx_, cy_ = _tam(lp)
                out.alpha_composite(_co_gian(_mo(_co_gian(lp, s, cx_, cy_), op), s_nhom, gcx, gcy))
            if op_nhom < 1:
                out = _mo(out, op_nhom)
            _bong_noi(out).save(os.path.join(tmp, f"{i:05d}.png"))
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(khung, range(n)))
        ma_hoa(tmp, ra, fps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ra, [0.5, round((y0 + y1) / 2 / H, 4)], n


def _tam(lp):
    bb = lp.getbbox() or (0, 0, lp.size[0], lp.size[1])
    return (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2


def _lo_giua(lp, p):
    """Lộ từ giữa ra 2 bên (đường kẻ)."""
    bb = lp.getbbox()
    if not bb or p >= 1:
        return lp
    if p <= 0:
        return Image.new("RGBA", lp.size, (0, 0, 0, 0))
    cx, nua = (bb[0] + bb[2]) / 2, (bb[2] - bb[0]) / 2 * p
    m = Image.new("L", lp.size, 0)
    ImageDraw.Draw(m).rectangle([int(cx - nua), 0, int(cx + nua), lp.size[1]], fill=255)
    out = lp.copy()
    out.putalpha(ImageChops.multiply(lp.split()[-1], m))
    return out


def _bong_noi(im):
    """Bóng nổi 2 lớp giống ve_chu.bong_noi (xanh đen Poly)."""
    a = im.split()[-1]
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    for mo, dy, d0 in ((22, 14, 95), (4, 3, 70)):
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.paste(Image.new("RGBA", im.size, (3, 35, 26, d0)), (0, dy), a.filter(ImageFilter.GaussianBlur(mo)))
        out.alpha_composite(sh)
    out.alpha_composite(im)
    return out


def karaoke_mov(cum, t0, t1, ra, font_fn, y_tam=1265, fps=FPS, xanh=(7, 77, 58, 255), vang=(255, 214, 0, 255)):
    """1 cụm phụ đề karaoke: cum = [(từ IN HOA, giờ bắt đầu nói, là_từ_khoá)], hiện từ t0 tới t1 (giây trên timeline).
    font_fn(cỡ) -> font. Trả (mov, vi_tri, số khung)."""
    co = 84
    d0 = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    while co > 52:
        f = font_fn(co)
        rong = [d0.textlength(w, font=f) for w, _, _ in cum]
        if sum(rong) + 30 * (len(cum) - 1) <= 900:
            break
        co -= 4
    f = font_fn(co)
    rong = [d0.textlength(w, font=f) for w, _, _ in cum]
    gap = 30
    tong = sum(rong) + gap * (len(rong) - 1)
    hb = 260
    asc = f.getbbox("ÂỲ")[1]
    n = max(1, int(round((t1 - t0) * fps)))
    tmp = tempfile.mkdtemp(prefix="hh-")
    try:
        def khung(i):
            t = t0 + i / fps
            im = Image.new("RGBA", (W, hb), (0, 0, 0, 0))
            x = (W - tong) / 2
            dang = max([k for k, (_, a, _) in enumerate(cum) if a <= t + 1e-3] or [0])
            for k, ((w, a, kh), rw) in enumerate(zip(cum, rong)):
                hien = k == 0 or a <= t + 1e-3
                if not hien:
                    x += rw + gap
                    continue
                p = (t - max(a, t0)) / 0.18
                s = 0.55 + 0.45 * _back(p) if k > 0 or t > t0 + 1e-3 else 1.0
                if k == 0 and i == 0:
                    s = 1.0
                lp = Image.new("RGBA", (int(rw) + 80, hb), (0, 0, 0, 0))
                dl = ImageDraw.Draw(lp)
                ty = hb / 2 - (f.getbbox(w)[1] + f.getbbox(w)[3]) / 2
                if k == dang:
                    bb = dl.textbbox((40, ty), w, font=f)
                    dl.rounded_rectangle([bb[0] - 18, hb / 2 - co * 0.62, bb[2] + 18, hb / 2 + co * 0.62], radius=int(co * 0.3), fill=xanh)
                    dl.text((40, ty), w, font=f, fill=(255, 255, 255, 255))
                else:
                    dl.text((40, ty), w, font=f, fill=vang if kh else (255, 255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))
                if abs(s - 1) > 1e-3:
                    nw, nh = max(1, int(lp.width * s)), max(1, int(lp.height * s))
                    lp = lp.resize((nw, nh), Image.BICUBIC)
                cx = x + rw / 2
                im.alpha_composite(lp, (int(round(cx - lp.width / 2)), int(round(hb / 2 - lp.height / 2))))
                x += rw + gap
            _bong(im, 3, 6, 7, 120).save(os.path.join(tmp, f"{i:05d}.png"))
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(khung, range(n)))
        ma_hoa(tmp, ra, fps)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return ra, [0.5, round(y_tam / H, 4)], n
