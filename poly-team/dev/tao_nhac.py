# -*- coding: utf-8 -*-
"""Tạo bộ NHẠC NỀN MIỄN PHÍ kèm POLY Cut (4/11): 4 bài nhạc nền TỰ TỔNG HỢP bằng numpy / scipy (không mẫu âm thanh, không vòng
nhạc lấy từ đâu cả) -> nhac-mien-phi/*.mp3 + nhac.json (tên hiện, mô tả, nhịp, giấy phép) + NGUON.md (file kê nguồn + giấy phép).
Giai điệu / hợp âm là vòng hợp âm phổ thông (không thuộc bản quyền ai), nhạc cụ là bộ tổng hợp tự viết: FM (đàn điện), cộng hoạ âm
(pad, pluck), Karplus-Strong (dây gảy kiểu ukulele), trống tổng hợp từ sóng sin + tiếng ồn. Phát hành CC0 1.0 (Poly Store tự tạo).
Hạt ngẫu nhiên cố định: chạy lại ra y hệt. Dùng:  python dev/tao_nhac.py [thư mục ra]   (mặc định <app>/nhac-mien-phi)
Cần numpy, scipy, ffmpeg (libmp3lame) — chỉ máy làm app cần, máy tiệm chỉ dùng file mp3 đã tạo."""
import json, os, subprocess, sys, tempfile, wave
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
RA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "nhac-mien-phi")


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


def tt(n):
    return np.arange(n) / SR


def env_ad(n, a, d, dinh=1.0):
    """Lên tuyến tính a giây rồi giảm mũ (hằng số d giây)."""
    t = tt(n)
    return np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) / d)) * dinh


def env_asr(n, a, r, giu):
    """Lên a giây, giữ tới giu giây, nhả r giây (cosine)."""
    t = tt(n)
    e = np.clip(t / max(a, 1e-4), 0, 1)
    e = np.where(t > giu, np.clip(1 - (t - giu) / max(r, 1e-4), 0, 1), e)
    return 0.5 - 0.5 * np.cos(np.pi * e)


def loc(x, f, kieu="low", bac=2):
    w = np.clip(np.asarray(f, dtype=float) / (SR / 2), 1e-4, 0.999)
    sos = butter(bac, w if w.size > 1 else float(w), btype=kieu, output="sos")
    return sosfilt(sos, x)


class Ban:
    """Bản trộn stereo: cộng tiếng vào đúng giây, có pan."""
    def __init__(self, giay):
        self.L = np.zeros(int(giay * SR) + SR * 4)
        self.R = np.zeros_like(self.L)

    def cong(self, x, t, vol=1.0, pan=0.0):
        i = int(round(t * SR))
        if i >= len(self.L):
            return
        x = x[: len(self.L) - i] * vol
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.L[i:i + len(x)] += x * gl * 1.414
        self.R[i:i + len(x)] += x * gr * 1.414


# ------------------------------------------------------------------ nhạc cụ
def dan_dien(m, dai, vel=1.0):
    """Đàn điện kiểu Rhodes: FM tỉ lệ 1:1, chỉ số điều chế giảm dần + tiếng 'tine' cao, tắt nhanh."""
    n = int((dai + 1.6) * SR); t = tt(n); f = hz(m)
    I = 0.15 + 1.6 * vel * np.exp(-t / 0.35)
    y = np.sin(2 * np.pi * f * t + I * np.sin(2 * np.pi * f * t))
    y += 0.12 * vel * np.sin(2 * np.pi * f * 14 * t) * np.exp(-t / 0.05)
    e = env_ad(n, 0.004, 1.4) * np.clip(1 - (t - dai) / 0.25, 0, 1)
    return y * e * (0.55 + 0.45 * vel)


def pad(m, dai, sang=0.6, rong=0.12):
    """Pad ấm: 3 sóng răng cưa lệch tông (cộng 14 hoạ âm, nghiêng dần), lên / nhả chậm. -> (trái, phải)."""
    n = int((dai + 0.9) * SR); t = tt(n); f = hz(m)
    out = []
    for lech in ((-rong, 0.0), (rong, 0.07)):
        y = np.zeros(n)
        for c, ph in ((1.0 + lech[0] / 100, 0.0), (1.0, 1.3), (1.0 - lech[0] / 100 * 0.7, 2.1 + lech[1])):
            for k in range(1, 15):
                y += np.sin(2 * np.pi * f * c * k * t + ph * k) / k ** (1.0 + 1.2 * (1 - sang))
        out.append(y * env_asr(n, 0.35, 0.8, dai) / 6.0)
    return out


def pluck(m, dai=0.5, sang=1.0, tat=1.0):
    """Gảy điện tử: hoạ âm cao tắt nhanh hơn hoạ âm thấp."""
    n = int((dai + 0.6) * SR); t = tt(n); f = hz(m); y = np.zeros(n)
    for k in range(1, 12):
        if f * k > 15000:
            break
        y += np.sin(2 * np.pi * f * k * t) / k ** 1.1 * np.exp(-t * (4 + 3.2 * k * sang) / tat)
    return y * env_ad(n, 0.002, 0.9 * tat) * 0.6


def bass(m, dai, cang=1.0):
    n = int((dai + 0.2) * SR); t = tt(n); f = hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t) * np.exp(-t / 0.15)
    y = np.tanh(1.6 * y) / np.tanh(1.6)
    return y * env_asr(n, 0.006, 0.06, dai) * (0.55 + 0.45 * np.exp(-t / (0.35 * cang)))


def day_gay(m, dai=1.2, sang=0.5, rng=None):
    """Dây gảy (ukulele / guitar nylon) Karplus-Strong: vòng trễ N mẫu + lọc trung bình 2 mẫu, chạy bằng lfilter."""
    f = hz(m); N = int(SR / f); n = int((dai + 0.3) * SR)
    rho = 0.996 ** (440.0 / f) if f > 440 else 0.996
    x = np.zeros(n); kich = (rng or np.random.default_rng(1)).uniform(-1, 1, N)
    kich = loc(kich, 1500 + 6000 * sang)
    x[:N] = kich
    a = np.zeros(N + 2); a[0] = 1; a[N] = -0.5 * rho; a[N + 1] = -0.5 * rho
    y = lfilter([1.0], a, x)
    y *= np.clip(1 - (tt(n) - dai) / 0.25, 0, 1)
    return loc(y, 80, "high") * 0.5


def chuong(m, dai=1.5):
    """Chuông (glockenspiel): sin + 2 hoạ âm không điều hoà, tắt dần."""
    n = int(dai * SR); t = tt(n); f = hz(m)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t / 0.25) + 0.18 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t / 0.08)
    return y * env_ad(n, 0.001, 0.55) * 0.5


def kick(manh=1.0):
    n = int(0.45 * SR); t = tt(n)
    f = 46 + 120 * np.exp(-t * 32)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7.5)
    y += 0.25 * np.random.default_rng(3).uniform(-1, 1, n) * np.exp(-t * 900)
    return np.tanh(1.4 * y) * manh


def snare(rng, manh=1.0, mem=False):
    n = int(0.3 * SR); t = tt(n)
    nz = loc(rng.uniform(-1, 1, n), [900, 7000] if not mem else [600, 4500], "band")
    y = nz * np.exp(-t * (24 if not mem else 30)) + 0.5 * np.sin(2 * np.pi * 185 * t) * np.exp(-t * 28)
    return y * manh * (0.8 if mem else 1.0)


def clap(rng, manh=1.0):
    n = int(0.35 * SR); t = tt(n)
    nz = loc(rng.uniform(-1, 1, n), [1000, 5000], "band")
    e = sum(np.where((t >= d) & (t < d + 0.008), 1.0, 0.0) * np.exp(-(t - d) * 300) for d in (0.0, 0.011, 0.022))
    e = e + np.where(t >= 0.03, np.exp(-(t - 0.03) * 18), 0)
    return nz * e * manh * 0.9


def hat(rng, mo=False, manh=1.0):
    n = int((0.25 if mo else 0.06) * SR); t = tt(n)
    nz = loc(rng.uniform(-1, 1, n), 7000, "high", 4)
    return nz * np.exp(-t * (14 if mo else 80)) * manh * 0.6


def shaker(rng, manh=1.0):
    n = int(0.09 * SR); t = tt(n)
    nz = loc(rng.uniform(-1, 1, n), [4000, 11000], "band")
    return nz * np.sin(np.pi * np.clip(t / 0.09, 0, 1)) ** 2 * manh * 0.5


def vang(L, R, phong=0.35, tron=0.18):
    """Tiếng vang Schroeder (4 comb + 2 allpass) mỗi kênh, lệch trễ trái / phải cho rộng."""
    def mot(x, lech):
        y = np.zeros_like(x)
        for d in (1557, 1617, 1491, 1422):
            D = d + lech
            a = np.zeros(D + 1); a[0] = 1; a[D] = -(0.70 + 0.25 * phong)
            y += lfilter([1.0], a, x)
        y /= 4
        for d, g in ((225, 0.5), (556, 0.5)):
            D = d + lech // 3
            b = np.zeros(D + 1); b[0] = -g; b[D] = 1
            a = np.zeros(D + 1); a[0] = 1; a[D] = -g
            y = lfilter(b, a, y)
        return loc(y, 5500)
    return L + tron * mot(L, 0), R + tron * mot(R, 23)


def tre(x, giay, phan=0.35, lan=4):
    """Tiếng dội (delay) lặp lại nhỏ dần."""
    y = x.copy(); d = int(giay * SR)
    for k in range(1, lan + 1):
        y[d * k:] += x[: len(x) - d * k] * phan ** k
    return y


def bom_nhip(n, nhip, giay_bat_dau=0.0, sau=0.55):
    """Nhún theo nhịp trống (kiểu sidechain nhạc EDM): hạ ở mỗi phách rồi lên lại."""
    t = tt(n) - giay_bat_dau
    p = np.mod(np.maximum(t, 0), nhip) / nhip
    return 1 - sau * np.exp(-p * 7)


# ------------------------------------------------------------------ 4 bài
def bai_nhe_nhang():
    bpm, so_o = 84, 24
    b = 60.0 / bpm; o = 4 * b; T = so_o * o
    rng = np.random.default_rng(84)
    ban, nen = Ban(T), Ban(T)
    hop = [(53, 57, 60, 64), (52, 55, 59, 62), (50, 53, 57, 60), (55, 59, 60, 64)]   # Fmaj7 Em7 Dm7 Cmaj7
    goc = [41, 40, 38, 36]
    for i in range(so_o):
        t0 = i * o; h = hop[i % 4]; vao = i >= 2
        for k, m in enumerate(h):   # hợp âm đàn điện: rải nhẹ
            ban.cong(dan_dien(m, 2.2 * b, 0.8), t0 + 0.012 * k, 0.30, pan=-0.3 + 0.2 * k)
        ban.cong(dan_dien(h[-1] + 12, 0.5 * b, 0.5), t0 + 2.5 * b, 0.10, pan=0.35)
        ban.cong(dan_dien(h[1] + 12, 0.5 * b, 0.45), t0 + 3.0 * b, 0.09, pan=-0.35)
        if vao:
            ban.cong(bass(goc[i % 4], 1.6 * b), t0, 0.28)
            ban.cong(bass(goc[i % 4] + 7, 0.8 * b), t0 + 2.5 * b, 0.20)
            for k, (p, v) in enumerate([(0, 1.0), (1.5, 0.7)]):
                ban.cong(kick(0.9), t0 + p * b, 0.38 * v)
            for p in (1, 3):
                ban.cong(snare(rng, 0.8, mem=True), t0 + p * b + 0.02, 0.30)
            for k in range(8):   # hat lệch nhịp (swing 58%)
                lech = (0.58 - 0.5) * b if k % 2 else 0.0
                ban.cong(hat(rng, manh=0.7 if k % 2 else 1.0), t0 + k * 0.5 * b + lech, 0.22, pan=0.25)
    L, R = vang(ban.L, ban.R, 0.45, 0.22)
    # tiếng lạo xạo đĩa than RẤT nhỏ (vài tiếng mỗi giây, lọc trầm) cho chất lofi
    cr = loc(rng.uniform(-1, 1, len(L)) * (rng.random(len(L)) > 0.99992) * 0.08, 3500) + loc(rng.uniform(-1, 1, len(L)), 2500) * 0.0015
    L, R = L + cr, R + np.roll(cr, 37)
    return loc(L, 12000), loc(R, 12000), T, bpm


def bai_soi_dong():
    bpm, so_o = 120, 32
    b = 60.0 / bpm; o = 4 * b; T = so_o * o
    rng = np.random.default_rng(120)
    ban, pd = Ban(T), Ban(T)
    hop = [(57, 60, 64), (57, 60, 65), (55, 60, 64), (55, 59, 62)]   # Am F C G
    goc = [45, 41, 48, 43]
    arp = [0, 1, 2, 1, 2, 3, 2, 1]
    for i in range(so_o):
        t0 = i * o; h = hop[i % 4]; nghi = 16 <= i < 20; dau = i < 2
        for m in h:
            l, r = pad(m, o, sang=0.55 if not nghi else 0.35)
            pd.cong(l, t0, 0.26, -0.6); pd.cong(r, t0, 0.26, 0.6)
        if not dau:
            ds = [h[0] + 12, h[1] + 12, h[2] + 12, h[0] + 24]
            for k in range(16):
                ban.cong(pluck(ds[arp[k % 8]], 0.18, 0.9), t0 + k * 0.25 * b, 0.20 * (0.8 if k % 4 else 1.0), pan=-0.4 if k % 2 else 0.4)
        if not nghi and not dau:
            for k in range(8):
                if k % 2:
                    ban.cong(bass(goc[i % 4], 0.42 * b, 0.6), t0 + k * 0.5 * b, 0.28)
            for p in range(4):
                ban.cong(kick(1.0), t0 + p * b, 0.40)
                ban.cong(hat(rng, mo=True, manh=0.9), t0 + p * b + 0.5 * b, 0.22, pan=0.2)
            for p in (1, 3):
                ban.cong(clap(rng), t0 + p * b, 0.36, pan=-0.1)
            for k in range(16):
                ban.cong(shaker(rng, 0.8 if k % 2 else 0.5), t0 + k * 0.25 * b, 0.15, pan=0.45)
        elif nghi and i == 19:
            for k in range(8):   # trống dồn trước khi vào lại
                ban.cong(snare(rng, 0.4 + 0.08 * k), t0 + 2 * b + k * 0.25 * b, 0.22)
    pl, pr = pd.L * bom_nhip(len(pd.L), b, 0.0, 0.5), pd.R * bom_nhip(len(pd.R), b, 0.0, 0.5)
    L, R = vang(ban.L + pl, ban.R + pr, 0.35, 0.16)
    return loc(L, 12000), loc(R, 12000), T, bpm


def bai_cong_nghe():
    bpm, so_o = 110, 32
    b = 60.0 / bpm; o = 4 * b; T = so_o * o
    rng = np.random.default_rng(110)
    ban, dl = Ban(T), Ban(T)
    hop = [(62, 65, 69), (62, 65, 70), (60, 65, 69), (60, 64, 67)]   # Dm Bb F C
    goc = [38, 34, 41, 36]
    mau = [0, 2, 1, 2, 0, 2, 1, 3, 0, 2, 1, 2, 0, 1, 2, 3]
    for i in range(so_o):
        t0 = i * o; h = hop[i % 4]; ds = [h[0], h[1], h[2], h[0] + 12]
        for m in h:
            l, r = pad(m - 12, o, sang=0.35, rong=0.08)
            ban.cong(l, t0, 0.11, -0.5); ban.cong(r, t0, 0.11, 0.5)
        for k in range(16):
            if k % 3 == 2 and i % 2:
                continue
            dl.cong(pluck(ds[mau[k]] + 12, 0.16, 0.8, 0.8), t0 + k * 0.25 * b, 0.16, pan=0.15 if k % 2 else -0.15)
        ban.cong(bass(goc[i % 4], 1.9 * b, 1.5), t0, 0.27)
        ban.cong(bass(goc[i % 4], 0.9 * b, 0.8), t0 + 2.5 * b, 0.20)
        if i >= 2:
            ban.cong(kick(0.8), t0, 0.36); ban.cong(kick(0.7), t0 + 2.5 * b, 0.30)
            if i >= 4:
                ban.cong(kick(0.8), t0 + 1.75 * b, 0.24)
            for p in (1, 3):
                ban.cong(snare(rng, 0.7, mem=True), t0 + p * b, 0.24)
            for k in range(16):
                ban.cong(hat(rng, manh=1.0 if k % 4 == 2 else 0.55), t0 + k * 0.25 * b, 0.17, pan=0.3)
    L = ban.L + tre(dl.L, 0.75 * b, 0.4, 5) + 0.6 * tre(dl.R, 0.5 * b, 0.3, 3)
    R = ban.R + tre(dl.R, 0.5 * b, 0.4, 5) + 0.6 * tre(dl.L, 0.75 * b, 0.3, 3)
    L, R = vang(L, R, 0.3, 0.14)
    return loc(L, 11000), loc(R, 11000), T, bpm


def bai_vui_tuoi():
    bpm, so_o = 112, 32
    b = 60.0 / bpm; o = 4 * b; T = so_o * o
    rng = np.random.default_rng(112)
    ban = Ban(T)
    uke = [(67, 60, 64, 72), (67, 62, 67, 71), (69, 60, 64, 69), (69, 60, 65, 69)]   # C G Am F (dây G C E A)
    goc = [48, 43, 45, 41]
    giai = [[76, 74, 72, 74, 76, 79, 76, 72], [74, 71, 74, 79, 74, 71, 67, 71], [72, 76, 81, 79, 76, 72, 69, 72], [72, 69, 72, 77, 76, 72, 69, 65]]
    quet = [(0, 1), (1, -1), (1.5, 1), (2.5, -1), (3, 1), (3.5, -1)]   # nhịp quạt chả: xuống / lên
    for i in range(so_o):
        t0 = i * o; h = uke[i % 4]
        for p, chieu in quet:
            for k, m in enumerate(h if chieu > 0 else h[::-1]):
                ban.cong(day_gay(m, 0.45 * b if p % 1 else 0.9 * b, 0.6 if chieu > 0 else 0.4, rng), t0 + p * b + 0.011 * k,
                         0.55 * (1.0 if chieu > 0 else 0.7), pan=-0.25)
        if i >= 2:
            ban.cong(bass(goc[i % 4], 1.4 * b), t0, 0.22); ban.cong(bass(goc[i % 4], 0.9 * b), t0 + 2 * b, 0.19)
            ban.cong(kick(0.8), t0, 0.32); ban.cong(kick(0.7), t0 + 2 * b, 0.27)
            for p in (1, 3):
                ban.cong(clap(rng, 0.9), t0 + p * b, 0.28, pan=0.1)
            for k in range(8):
                ban.cong(shaker(rng, 1.0 if k % 2 else 0.6), t0 + k * 0.5 * b, 0.17, pan=0.5)
        if 4 <= i < 12 or 20 <= i < 28:
            for k, m in enumerate(giai[i % 4]):
                if k in (3, 7) and i % 2:
                    continue
                ban.cong(chuong(m, 0.9), t0 + k * 0.5 * b, 0.17, pan=0.3)
    L, R = vang(ban.L, ban.R, 0.4, 0.18)
    return loc(L, 12000), loc(R, 12000), T, bpm


BAI = [
    ("poly-nhe-nhang.mp3", "Nhẹ nhàng", "đàn điện, trống nhẹ, kiểu lofi chill · 84 BPM", bai_nhe_nhang),
    ("poly-soi-dong.mp3", "Sôi động", "nhịp 4/4 dồn, pluck rải, kiểu pop / house · 120 BPM", bai_soi_dong),
    ("poly-cong-nghe.mp3", "Công nghệ", "pluck dội, bass sâu, kiểu review công nghệ · 110 BPM", bai_cong_nghe),
    ("poly-vui-tuoi.mp3", "Vui tươi", "dây gảy kiểu ukulele, vỗ tay, chuông · 112 BPM", bai_vui_tuoi),
]


def ghi_wav(p, L, R, T):
    n = int(T * SR)
    x = np.stack([L[:n], R[:n]], 1)
    x = loc(x.T, 28, "high").T   # bỏ tiếng ù siêu trầm
    x = np.tanh(x / max(1e-6, np.abs(x).max()) * 1.2) / np.tanh(1.2) * 0.89
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    os.makedirs(RA, exist_ok=True)
    kk = json.load(open(os.path.join(RA, "nhac.json"), encoding="utf-8")) if os.path.isfile(os.path.join(RA, "nhac.json")) else {}
    chi = os.environ.get("CHI_BAI", "")   # CHI_BAI=poly-nhe-nhang.mp3,… : chỉ tạo lại vài bài
    for ten_file, ten, mo_ta, ham in BAI:
        if chi and ten_file not in chi.split(","):
            continue
        L, R, T, bpm = ham()
        with tempfile.TemporaryDirectory() as tm:
            w = os.path.join(tm, "x.wav")
            ghi_wav(w, L, R, T)
            # chuẩn độ to −16 LUFS (2 lượt, tuyến tính), mp3 192 kbps, không thẻ / ảnh bìa
            r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", w, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                                "-f", "null", "-"], capture_output=True, text=True)
            j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
            af = ("loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true,"
                  "aresample=44100" % (j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", w, "-af", af, "-map_metadata", "-1", "-c:a", "libmp3lame", "-b:a", "192k",
                            "-metadata", "title=" + ten, "-metadata", "artist=Poly Store (tự tạo)", "-metadata", "copyright=CC0 1.0",
                            os.path.join(RA, ten_file)], check=True)
        kk[ten_file] = {"ten": ten, "mo_ta": mo_ta, "bpm": bpm, "giay": round(T, 2), "giay_phep": "CC0 1.0 (Poly Store tự tạo bằng dev/tao_nhac.py)"}
        print(ten_file, round(T, 1), "giây")
    json.dump(kk, open(os.path.join(RA, "nhac.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
