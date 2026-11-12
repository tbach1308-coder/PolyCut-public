# -*- coding: utf-8 -*-
"""NGUYÊN MẪU r37 (11/11/2026, anh: "âm thanh hạn chế quá"): 14 tiếng hiệu ứng TỰ TỔNG HỢP bằng numpy / scipy cho video bán máy —
những tiếng các kho CC0 tải về (SFX Kit Wyzowl, Kenney) chưa có hoặc cần kiểu TikTok: dừng băng, scratch đĩa, dồn rồi nổ, cắm sạc,
nhịp tim, glitch giật, ting giá, drop phonk, vút xoáy, lấy nét + chụp, buzzer sai, huýt sáo lên / xuống, trống dồn + chũm choẹ.
Không dùng mẫu âm thanh (sample) nào lấy từ ngoài: sóng sin / răng cưa / vuông, tiếng ồn lọc, FM, đường bao, vang (IR tổng hợp).
Poly Store phát hành CC0 1.0. Hạt ngẫu nhiên cố định: chạy lại ra y hệt.
Ra: <thư mục>/<khoá>.wav (48 kHz, float32, stereo, CHƯA chuẩn hoá — dev/kho_am_thanh_r37.py chuẩn hoá đỉnh −3 dBFS) + tu-tao.json
(khoá, tên, nhóm, mô tả, giây, dinh = giây "chạm" để đặt đúng chỗ cắt cảnh).
Dùng:  python dev/tao_am_thanh_r37.py <thư mục ra>     (cần numpy, scipy)"""
import json, os, sys, wave
import numpy as np
from scipy import signal

SR = 48000


def ns(g):
    return int(round(g * SR))


def tt(n):
    return np.arange(n) / SR


def rng(k):
    return np.random.default_rng(1000 + k)


def sos(kieu, f, bac=2):
    return signal.butter(bac, f, btype=kieu, fs=SR, output="sos")


def loc(x, kieu, f, bac=2):
    return signal.sosfilt(sos(kieu, f, bac), x)


def loc_quet(x, f_tam, q=1.2, khoi=256):
    """Lọc thông dải quét theo thời gian: f_tam(t 0..1) Hz, giữ trạng thái giữa các khối (không lách cách)."""
    out = np.zeros_like(x); zi = np.zeros((1, 2)); n = len(x)
    for a in range(0, n, khoi):
        f = float(np.clip(f_tam(a / max(1, n - 1)), 40, SR * 0.45))
        b, aa = _bp(f, q)
        seg = x[a:a + khoi]
        y, zi1 = signal.lfilter(b, aa, seg, zi=zi[0]); zi[0] = zi1; out[a:a + khoi] = y
    return out


def _bp(f, q):
    """Biquad thông dải (RBJ, đỉnh 0 dB)."""
    w = 2 * np.pi * f / SR; al = np.sin(w) / (2 * q)
    b = np.array([al, 0, -al]); a = np.array([1 + al, -2 * np.cos(w), 1 - al])
    return b / a[0], a / a[0]


def vang(x, dai=1.2, tron=0.2, sang=6000, tre=0.012, k=0):
    """Vang phòng: IR = tiếng ồn tắt mũ (mỗi kênh một hạt -> rộng), lọc thấp. x mono hoặc stereo -> stereo."""
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    x = mo(x, 0.0, 0.03)   # tắt êm phần khô trước khi vang (khỏi "tạch" ở chỗ hết tiếng khô)
    n = ns(dai); t = tt(n); out = []
    for c in range(2):
        ir = rng(900 + k * 2 + c).standard_normal(n) * np.exp(-6.9 * t / dai)
        ir = loc(ir, "low", sang); ir[: ns(tre)] = 0; ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        out.append(signal.fftconvolve(x[:, c], ir)[: len(x) + n])
    w = np.stack(out, 1)
    d = np.zeros_like(w); d[: len(x)] = x
    return d * (1 - tron * 0.5) + w * tron


def st(x, pan=0.0):
    if np.isscalar(pan):
        pan = np.full(len(x), pan)
    return np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414


def mo(x, vao=0.002, ra=0.02):
    n = len(x); e = np.ones(n)
    a, b = max(1, ns(vao)), max(1, ns(ra))
    e[:a] = np.linspace(0, 1, a); e[-b:] = np.minimum(e[-b:], np.linspace(1, 0, b))
    return x * (e[:, None] if x.ndim == 2 else e)


def dat(buf, x, t):
    a = ns(t); b = min(len(buf), a + len(x)); buf[a:b] += x[: b - a]


def sin_f(f, n, pha=0.0):
    """Sóng sin tần số đổi theo thời gian (mảng f hoặc số)."""
    f = np.full(n, f) if np.isscalar(f) else f
    return np.sin(2 * np.pi * np.cumsum(f) / SR + pha)


def saw_f(f, n):
    f = np.full(n, f) if np.isscalar(f) else f
    ph = np.cumsum(f) / SR
    return 2 * (ph - np.floor(ph + 0.5))


def vuong_f(f, n):
    return np.sign(sin_f(f, n) + 1e-9)


def kick(dai=0.6, f0=150, f1=45, tat=0.35):
    n = ns(dai); t = tt(n)
    f = f1 + (f0 - f1) * np.exp(-t / 0.04)
    return np.tanh(1.6 * sin_f(f, n) * np.exp(-t / tat))


# ------------------------------------------------------------------ 14 tiếng
def vut_xoay():          # whoosh + phaser quét + tiếng huýt mờ, lia trái -> phải
    n = ns(0.95); t = tt(n); x = rng(1).standard_normal(n)
    x = loc_quet(x, lambda u: 350 * 12 ** np.sin(np.pi * min(1.0, u / 0.95)), q=0.9)
    d = (0.0004 + 0.0026 * (0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * t))) * SR   # flanger 0,4–3 ms
    idx = np.clip(np.arange(n) - d, 0, n - 1); x = x + 0.8 * np.interp(idx, np.arange(n), x)
    wh = 0.08 * sin_f(900 * 1.6 ** np.sin(np.pi * t / 0.95), n)
    e = np.where(t < 0.52, (t / 0.52) ** 2, np.exp(-(t - 0.52) / 0.12))
    y = (x / (np.abs(x).max() + 1e-9) + wh) * e
    return mo(vang(st(y, np.linspace(-0.85, 0.85, n)), 0.8, 0.15, k=1), 0.001, 0.05), 0.52


def dung_bang():         # tape stop: 1 ô nhạc (hợp âm + kick + hat) chạy chậm dần tới dừng
    m = ns(1.6); src = np.zeros(m); tm = tt(m)
    for f in (130.8, 164.8, 196.0, 246.9, 329.6):
        src += 0.18 * saw_f(f * (1 + 0.002 * rng(2).standard_normal()), m)
    src = loc(src, "low", 2200) * (0.6 + 0.4 * (np.sin(2 * np.pi * 2 * tm) > 0))
    for b in (0.0, 0.5, 1.0):
        dat(src, 0.9 * kick(0.4), b)
    for b in np.arange(0.25, 1.5, 0.5):
        dat(src, 0.25 * loc(rng(3).standard_normal(ns(0.05)), "high", 7000) * np.exp(-tt(ns(0.05)) / 0.015), b)
    n = ns(1.15); t = tt(n); T = 0.95
    r = np.clip(1 - t / T, 0, 1) ** 1.7
    pos = np.cumsum(r) + ns(0.25)
    y = np.interp(pos, np.arange(m), src)
    y = loc_quet(y, lambda u: 2500 * max(0.08, 1 - u) + 120, q=0.5) * 1.6
    return mo(vang(st(y), 0.5, 0.08, k=2), 0.003, 0.06), 0.0


def scratch():           # scratch đĩa: nguồn giàu hoạ âm, đọc tới / lui 2 lần
    m = ns(0.3); tm = tt(m)
    src = 0.5 * saw_f(220 * (1 + 0.3 * tm), m) + 0.35 * saw_f(331, m) + 0.4 * rng(4).standard_normal(m)
    src = loc(src, "band", [300, 5000])
    n = ns(0.5); t = tt(n)
    pos = 0.085 * SR * (1 - np.cos(2 * np.pi * t / 0.24)) / 2 + 200
    y = np.interp(pos, np.arange(m), src)
    sp = np.abs(np.gradient(pos)); y *= np.clip(sp / sp.max(), 0, 1) ** 0.6       # đứng tay = lặng
    y += 0.03 * (rng(5).random(n) < 0.002) * rng(5).standard_normal(n)              # lạo xạo đĩa
    return mo(st(y), 0.002, 0.03), 0.0


def don_roi_no():        # riser 2 giây -> cắt -> nổ (kick + sub + nứt) + vang
    n = ns(3.6); t = tt(n); y = np.zeros(n); T = 2.0
    m = ns(T); u = tt(m) / T
    no = loc_quet(rng(6).standard_normal(m), lambda v: 300 * 27 ** v, q=1.4)
    ton = sum(saw_f(130.8 * 4 ** u * k, m) * a for k, a in ((1, 0.5), (1.005, 0.5), (2, 0.25)))
    ton = loc_quet(ton, lambda v: 400 * 15 ** v, q=0.7)
    ri = (0.7 * no / (np.abs(no).max() + 1e-9) + 0.35 * ton) * (u ** 2.2)
    y[:m] += ri * mo(np.ones(m), 0.01, 0.004)
    k = ns(1.6); tk = tt(k)
    hit = 1.1 * kick(1.6, 170, 42, 0.45) + 0.5 * np.sin(2 * np.pi * 42 * tk) * np.exp(-tk / 0.9)
    hit += 0.6 * loc(rng(7).standard_normal(k), "high", 1800) * np.exp(-tk / 0.06)
    dat(y, hit, T)
    return mo(vang(st(y), 1.8, 0.22, sang=5000, k=3), 0.001, 0.2), T


def cam_sac():           # cắm sạc: tiếng cắm (click) + 2 nốt chuông mềm đi lên (kiểu chung, không theo máy nào)
    n = ns(1.2); y = np.zeros(n)
    c = ns(0.03); tc = tt(c)
    dat(y, 0.8 * loc(rng(8).standard_normal(c), "high", 2500) * np.exp(-tc / 0.004), 0.0)
    dat(y, 0.5 * loc(rng(9).standard_normal(c), "band", [1500, 6000]) * np.exp(-tc / 0.003), 0.018)
    for t0, f in ((0.12, 1318.5), (0.24, 1975.5)):
        m = ns(0.8); tm = tt(m)
        note = (np.sin(2 * np.pi * f * tm) + 0.25 * np.sin(2 * np.pi * 2 * f * tm) * np.exp(-tm / 0.08)) * np.exp(-tm / 0.28)
        dat(y, 0.45 * note * np.minimum(1, tm / 0.004), t0)
    return mo(vang(st(y), 1.0, 0.22, k=4), 0.001, 0.08), 0.0


def nhip_tim():          # lub-dub x2, có hoạ âm để loa điện thoại vẫn nghe
    n = ns(1.9); y = np.zeros(n)
    def dap(f0, a):
        m = ns(0.3); tm = tt(m)
        x = np.sin(2 * np.pi * np.cumsum(f0 * (0.7 + 0.3 * np.exp(-tm / 0.03))) / SR) * np.exp(-tm / 0.07)
        x += 0.3 * loc(rng(10).standard_normal(m), "low", 300) * np.exp(-tm / 0.02)
        return a * np.tanh(2.2 * x)
    for b in (0.0, 0.95):
        dat(y, dap(62, 1.0), b); dat(y, dap(75, 0.7), b + 0.27)
    return mo(vang(st(loc(y, "low", 900)), 0.6, 0.1, k=5), 0.001, 0.1), 0.0


def glitch_giat():       # cắt lát + lặp + đổi cao độ + giảm bit
    g = rng(11); n = ns(0.75); y = np.zeros(n)
    m = ns(0.5); tm = tt(m)
    src = (np.sin(2 * np.pi * 440 * tm + 3 * np.sin(2 * np.pi * 660 * tm)) + 0.5 * saw_f(220, m) + 0.3 * g.standard_normal(m)) * 0.5
    t = 0.0; k = 0; pan = np.zeros(n)
    while t < 0.68:
        L = float(g.choice([0.018, 0.03, 0.045, 0.06])); rep = int(g.choice([1, 1, 2, 3]))
        a = int(g.integers(0, m - ns(0.08))); sl = src[a:a + ns(L)]
        sh = float(g.choice([0.5, 1, 1, 1.5, 2])); sl = np.interp(np.arange(0, len(sl), sh), np.arange(len(sl)), sl)
        bits = int(g.choice([3, 4, 6, 8])); sl = np.round(sl * 2 ** bits) / 2 ** bits
        hold = int(g.choice([1, 2, 4, 8])); sl = np.repeat(sl[::hold], hold)[: len(sl)]
        for _ in range(rep):
            if t >= 0.68: break
            dat(y, mo(sl, 0.0005, 0.001), t); p0 = ns(t); pan[p0:p0 + len(sl)] = g.uniform(-0.7, 0.7); t += len(sl) / SR
        if g.random() < 0.3: t += 0.02
        k += 1
    return mo(st(loc(y, "high", 120), pan), 0.001, 0.02), 0.0


def ting_gia():          # chuông FM sáng + lấp lánh + vang
    n = ns(1.8); t = tt(n); f = 2093.0
    idx = 2.5 * np.exp(-t / 0.15)
    y = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t / 0.45)
    y += 0.35 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.2)
    g = rng(12)
    for k in range(7):
        t0 = 0.02 + 0.05 * k + g.uniform(0, 0.02); m = ns(0.3); tm = tt(m)
        dat(y, 0.12 * np.sin(2 * np.pi * g.uniform(5500, 9500) * tm) * np.exp(-tm / 0.05), t0)
    y *= np.minimum(1, t / 0.001)
    return mo(vang(st(y), 1.6, 0.3, sang=9000, k=6), 0.0, 0.1), 0.0


def drop_phonk():        # cowbell phonk + 808 méo trượt xuống
    n = ns(1.8); y = np.zeros(n)
    def cowbell(f1, f2, a):
        m = ns(0.5); tm = tt(m)
        x = (vuong_f(f1, m) + vuong_f(f2, m)) * (0.75 * np.exp(-tm / 0.03) + 0.25 * np.exp(-tm / 0.2))
        return a * loc(x, "band", [700, 3000], 2)
    m = ns(1.5); tm = tt(m)
    f = 98 * np.where(tm < 0.55, 1.0, 2 ** (-(np.minimum(tm, 0.9) - 0.55) / 0.35 * 7 / 12))
    b8 = np.tanh(3.5 * sin_f(f, m) * np.exp(-tm / 0.7)) * mo(np.ones(m), 0.002, 0.2)
    dat(y, 0.8 * loc(b8, "low", 3500), 0.0)
    dat(y, 0.9 * kick(0.3, 180, 60, 0.08), 0.0)
    cb = np.zeros(n)
    for t0, (f1, f2), a in ((0.0, (587, 845), 0.6), (0.375, (659, 949), 0.5), (0.75, (587, 845), 0.45)):
        dat(cb, cowbell(f1, f2, a), t0)
    w = vang(st(cb), 0.9, 0.3, k=7)[: n]
    return mo(st(y) + w, 0.001, 0.15), 0.0


def lay_net_chup():      # 2 bíp lấy nét + màn trập 2 lần (gương lên / xuống)
    n = ns(0.85); y = np.zeros(n)
    for t0 in (0.0, 0.11):
        m = ns(0.055); tm = tt(m)
        dat(y, 0.35 * np.sin(2 * np.pi * 2793 * tm) * mo(np.ones(m), 0.002, 0.01), t0)
    def tach(a, sang):
        m = ns(0.06); tm = tt(m)
        x = loc(rng(13).standard_normal(m), "band", [sang, 9000]) * np.exp(-tm / 0.008)
        x += 0.5 * np.sin(2 * np.pi * 180 * tm) * np.exp(-tm / 0.015)
        return a * x
    dat(y, tach(0.9, 1200), 0.34); dat(y, tach(0.7, 2000), 0.43)
    return mo(vang(st(y), 0.4, 0.08, k=8), 0.001, 0.05), 0.34


def buzzer_sai():        # buzzer "sai rồi" kiểu game show
    n = ns(0.75); t = tt(n)
    f = 1 - 0.06 * np.clip((t - 0.45) / 0.3, 0, 1)
    y = 0.45 * saw_f(110 * f, n) + 0.45 * saw_f(116.5 * f, n) + 0.3 * vuong_f(55 * f, n)
    y = loc(np.tanh(1.8 * y), "low", 1800) * mo(np.ones(n), 0.005, 0.12)
    return mo(vang(st(y), 0.4, 0.06, k=9), 0.0, 0.03), 0.0


def huyt_sao(len_=True):  # huýt sáo trượt (slide whistle) lên / xuống
    n = ns(0.75); t = tt(n); u = np.clip(t / 0.62, 0, 1)
    f = (520 * (1600 / 520) ** u) if len_ else (1600 * (520 / 1600) ** u)
    f = f * (1 + 0.012 * np.sin(2 * np.pi * 6 * t))
    y = sin_f(f, n) + 0.08 * sin_f(2 * f, n)
    br = loc_quet(rng(14).standard_normal(n), lambda v: float(np.interp(v, [0, 1], [f[0], f[-1]])), q=4) * 0.15
    e = np.minimum(1, t / 0.03) * np.where(t > 0.62, np.exp(-(t - 0.62) / 0.04), 1)
    return mo(vang(st((y + br) * e), 0.5, 0.12, k=10), 0.0, 0.03), 0.0


def trong_don():         # trống dồn nhanh dần 2,3 giây -> chũm choẹ + kick
    n = ns(4.4); y = np.zeros(n); g = rng(15); T = 2.3
    t = 0.0
    while t < T - 0.03:
        u = t / T; v = 0.25 + 0.75 * u ** 1.4
        m = ns(0.12); tm = tt(m)
        sn = loc(g.standard_normal(m), "band", [900, 7000]) * np.exp(-tm / 0.045) + 0.6 * np.sin(2 * np.pi * 190 * tm) * np.exp(-tm / 0.03)
        dat(y, v * sn * g.uniform(0.85, 1.0), t)
        t += 1.0 / (8 + 18 * u ** 1.2)
    m = ns(2.0); tm = tt(m)
    cr = sum(np.sign(np.sin(2 * np.pi * f * tm + g.uniform(0, 6))) for f in (317, 461, 587, 811, 1023, 1471, 1913, 2617))
    cr = loc(0.15 * cr + g.standard_normal(m), "high", 3000) * (0.7 * np.exp(-tm / 0.9) + 0.3 * np.exp(-tm / 0.08))
    dat(y, 0.55 * cr, T); dat(y, 1.0 * kick(1.2, 160, 45, 0.4), T)
    return mo(vang(st(y), 1.6, 0.2, k=11), 0.0, 0.3), T


TIENG = [
    # khoá, hàm, tên tiếng Việt, nhóm, mô tả
    ("vut-xoay", vut_xoay, "Vút xoáy", "chuyen", "Whoosh có tiếng xoáy, lia trái sang phải: chuyển cảnh nhanh"),
    ("dung-bang", dung_bang, "Dừng băng", "vui", "Nhạc chậm dần rồi tắt (tape stop): khựng lại, câu chốt hài"),
    ("scratch-dia", scratch, "Scratch đĩa", "vui", "Đĩa than cào tới lui: \"khoan đã\", đổi ý, ngắt nhịp"),
    ("don-roi-no", don_roi_no, "Dồn rồi nổ", "dong", "Dồn 2 giây rồi nổ trầm đúng giây 2: lộ máy, lộ giá (đặt chỗ nổ vào cắt cảnh)"),
    ("cam-sac", cam_sac, "Cắm sạc", "may", "Tiếng cắm + 2 nốt chuông mềm: cắm sạc, máy nhận sạc"),
    ("nhip-tim", nhip_tim, "Nhịp tim", "dong", "Thình thịch 2 lần: hồi hộp trước khi lộ giá"),
    ("glitch-giat", glitch_giat, "Glitch giật", "chuyen", "Tiếng số giật cắt lát: chuyển cảnh kiểu công nghệ, lỗi màn hình"),
    ("ting-gia", ting_gia, "Ting giá", "thong_bao", "Chuông sáng lấp lánh: thẻ giá hiện"),
    ("drop-phonk", drop_phonk, "Drop phonk", "dong", "Cowbell + bass 808 méo trượt xuống: khoe máy kiểu trend"),
    ("lay-net-chup", lay_net_chup, "Lấy nét + chụp", "may", "Bíp bíp lấy nét rồi bấm chụp: khoe camera, ảnh chụp thử"),
    ("buzzer-sai", buzzer_sai, "Buzzer sai", "thong_bao", "Còi sai kiểu game show: hiểu lầm, \"sai rồi\""),
    ("huyt-sao-len", lambda: huyt_sao(True), "Huýt sáo lên", "vui", "Huýt sáo trượt lên: bất ngờ, hài"),
    ("huyt-sao-xuong", lambda: huyt_sao(False), "Huýt sáo xuống", "vui", "Huýt sáo trượt xuống: tụt mood, giá giảm"),
    ("trong-don", trong_don, "Trống dồn", "dong", "Trống dồn nhanh dần rồi chũm choẹ ở giây 2,3: công bố giá / quà"),
]


def ghi_wav_f32(p, x):
    """WAV float32 (định dạng 3) — để bước chuẩn hoá không mất độ phân giải."""
    x = np.ascontiguousarray(x, dtype="<f4")
    data = x.tobytes(); ch = x.shape[1]
    with open(p, "wb") as f:
        f.write(b"RIFF"); f.write((36 + len(data)).to_bytes(4, "little")); f.write(b"WAVEfmt ")
        f.write((16).to_bytes(4, "little")); f.write((3).to_bytes(2, "little")); f.write(ch.to_bytes(2, "little"))
        f.write(SR.to_bytes(4, "little")); f.write((SR * ch * 4).to_bytes(4, "little")); f.write((ch * 4).to_bytes(2, "little"))
        f.write((32).to_bytes(2, "little")); f.write(b"data"); f.write(len(data).to_bytes(4, "little")); f.write(data)


def main():
    ra = sys.argv[1] if len(sys.argv) > 1 else "tu-tao"
    os.makedirs(ra, exist_ok=True); out = []
    for k, fn, ten, nhom, mt in TIENG:
        x, dinh = fn()
        x = x / (np.abs(x).max() + 1e-9) * 0.7
        ghi_wav_f32(os.path.join(ra, k + ".wav"), x)
        out.append({"khoa": k, "ten": ten, "nhom": nhom, "mo_ta": mt, "giay": round(len(x) / SR, 2), "dinh": round(dinh, 3)})
        print(k, round(len(x) / SR, 2), "s")
    json.dump(out, open(os.path.join(ra, "tu-tao.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
