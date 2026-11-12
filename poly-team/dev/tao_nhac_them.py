# -*- coding: utf-8 -*-
"""Thêm 10 bài NHẠC NỀN MIỄN PHÍ cho POLY Cut (4/11 tối, r20 "thư viện nhạc còn ít"): tự tổng hợp như dev/tao_nhac.py (dùng lại bộ
nhạc cụ trong đó) + nhạc cụ mới (piano cộng hoạ âm có độ lệch dây, marimba, dàn dây, supersaw, hợp âm house) và khâu hoàn thiện mới:
nén nhẹ cả bài, mở rộng stereo phần cao, ĐUÔI VANG CUỘN VỀ ĐẦU BÀI (bài lặp lại liền mạch, không hụt tiếng vang ở chỗ nối).
Không mẫu âm thanh / vòng nhạc / preset lấy từ ngoài; hợp âm là vòng phổ thông; giai điệu tự đặt từ nốt trong hợp âm -> CC0 1.0.
Dùng:  python dev/tao_nhac_them.py [thư mục ra]          (ghi mp3 + cập nhật nhac.json, giữ 4 bài cũ)
       python dev/tao_nhac_them.py --do [thư mục]        (chỉ đo: LUFS, đỉnh, cân trầm / trung / cao, méo, lặng dài, chỗ nối lặp)
       CHI_BAI=poly-sang-trong.mp3,... để tạo lại vài bài."""
import json, os, subprocess, sys, tempfile, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tao_nhac as N   # nhạc cụ + trống + vang của bộ 4 bài đầu
from tao_nhac import SR, hz, tt, env_ad, env_asr, loc, Ban, kick, snare, clap, hat, shaker, bass, pluck, dan_dien, day_gay, chuong, vang, tre, bom_nhip

HERE = os.path.dirname(os.path.abspath(__file__))
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
RA = _args[0] if _args else os.path.join(os.path.dirname(HERE), "nhac-mien-phi")
DUOI = 4.0   # giây đuôi vang cuộn về đầu bài


# ------------------------------------------------------------------ nhạc cụ mới
def piano(m, dai, vel=0.8, sang=1.0):
    """Piano cộng hoạ âm: 10 hoạ âm lệch dây (inharmonic B), hoạ âm cao tắt nhanh, tiếng búa ngắn; nhả phím thì tắt trong 0,18s."""
    f = hz(m); n = int((dai + 1.2) * SR); t = tt(n); y = np.zeros(n)
    B = 0.00035 * (1 + max(0, m - 60) / 24)
    tat = 2.6 * (2 ** (-(m - 60) / 24))
    for k in range(1, 11):
        fk = f * k * np.sqrt(1 + B * k * k)
        if fk > 14000:
            break
        y += np.sin(2 * np.pi * fk * t + 0.3 * k) * (vel ** (0.5 + 0.12 * k * sang)) / k ** 1.25 * np.exp(-t * (1 + 0.55 * k) / tat)
    y += np.random.default_rng(int(m)).uniform(-1, 1, n) * np.exp(-t / 0.004) * 0.06 * vel
    y *= np.minimum(1, t / 0.003) * np.clip(1 - (t - dai) / 0.18, 0, 1)
    return y * 0.5


def marimba(m, vel=0.9):
    f = hz(m); n = int(1.1 * SR); t = tt(n)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.42) + 0.32 * np.sin(2 * np.pi * f * 3.93 * t) * np.exp(-t / 0.07) \
        + 0.08 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / 0.02)
    return y * np.minimum(1, t / 0.0015) * vel * 0.55


def day_dan(m, dai, sang=0.5):
    """Dàn dây: 3 răng cưa lệch (8 hoạ âm), lên chậm 0,45s, rung nhẹ 5,2 Hz -> (trái, phải)."""
    f = hz(m); n = int((dai + 1.0) * SR); t = tt(n)
    rung = 1 + 0.0025 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.6, 0, 1)
    out = []
    for lech in ((-0.11, 0.0, 0.07), (0.09, -0.05, 0.13)):
        y = np.zeros(n)
        for c in lech:
            ph = 2 * np.pi * np.cumsum(f * (1 + c / 100) * rung) / SR
            for k in range(1, 9):
                y += np.sin(k * ph) / k ** (1.0 + 1.4 * (1 - sang))
        out.append(y * env_asr(n, 0.45, 0.9, dai) / 7.0)
    return out


def supersaw(m, dai, sang=0.6):
    """Hợp âm kiểu future bass nhẹ: 5 răng cưa lệch nhau (10 hoạ âm), lên nhanh, nhả 0,3s -> (trái, phải)."""
    f = hz(m); n = int((dai + 0.4) * SR); t = tt(n); L = np.zeros(n); R = np.zeros(n)
    for j, c in enumerate((-0.18, -0.08, 0.0, 0.09, 0.17)):
        y = np.zeros(n); ph = 2 * np.pi * f * (1 + c / 100) * t + j
        for k in range(1, 11):
            y += np.sin(k * ph) / k ** (1.0 + 1.0 * (1 - sang))
        p = (j - 2) / 2.5
        L += y * np.cos((p + 1) * np.pi / 4); R += y * np.sin((p + 1) * np.pi / 4)
    e = env_asr(n, 0.01, 0.3, dai) / 6.0
    return loc(L * e, 5200), loc(R * e, 5200)


def hop_house(m, sang=0.6):
    """Hợp âm house (organ / stab) ngắn 0,28s."""
    f = hz(m); n = int(0.4 * SR); t = tt(n); y = np.zeros(n)
    for k, a in ((1, 1.0), (2, 0.55), (3, 0.3), (4, 0.22), (6, 0.12), (8, 0.07)):
        y += a * np.sin(2 * np.pi * f * k * t + k)
    return loc(y * env_ad(n, 0.004, 0.11), 2600 + 2500 * sang) * 0.4


def sub(m, dai):
    f = hz(m); n = int((dai + 0.1) * SR); t = tt(n)
    y = np.sin(2 * np.pi * f * t) + 0.12 * np.sin(4 * np.pi * f * t)
    return y * env_asr(n, 0.008, 0.06, dai) * 0.9


def rim(rng):
    n = int(0.06 * SR); t = tt(n)
    return (np.sin(2 * np.pi * 1700 * t) * 0.6 + loc(rng.uniform(-1, 1, n), [2000, 8000], "band")) * np.exp(-t * 90) * 0.7


def tom(m, manh=1.0):
    n = int(0.5 * SR); t = tt(n); f = hz(m) * (1 + 0.6 * np.exp(-t * 18))
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6) * manh


def dia_than(rng, n):   # tiếng lạo xạo đĩa than rất nhỏ
    return loc(rng.uniform(-1, 1, n) * (rng.random(n) > 0.99993) * 0.07, 3200) + loc(rng.uniform(-1, 1, n), 2400) * 0.0012


def hop_am(goc, kieu):
    """Nốt hợp âm (MIDI) từ nốt gốc: maj, min, maj7, m7, 7, add9, m9, 6."""
    b = {"maj": (0, 4, 7), "min": (0, 3, 7), "maj7": (0, 4, 7, 11), "m7": (0, 3, 7, 10), "7": (0, 4, 7, 10), "add9": (0, 4, 7, 14),
         "m9": (0, 3, 7, 10, 14), "6": (0, 4, 7, 9)}[kieu]
    return [goc + x for x in b]


def hoan_thien(L, R, T, rong=0.18):
    """Cuộn đuôi về đầu (lặp liền mạch), nén nhẹ cả bài (RMS 50 ms, ngưỡng tương đối), mở rộng stereo phần > 2 kHz."""
    n = int(T * SR); d = len(L) - n
    L, R = L.copy(), R.copy()
    if d > 0:
        L[:d] += L[n:n + d]; R[:d] += R[n:n + d]
    L, R = L[:n], R[:n]
    L, R = can_pho(L, R)
    M, S = (L + R) / 2, (L - R) / 2
    S = S + rong * loc(S, 2000, "high")
    L, R = M + S, M - S
    # nén nhẹ: đưa đoạn to sát đoạn nhỏ hơn chút (tỉ lệ 2:1 trên ngưỡng = RMS trung bình bài)
    w = int(0.05 * SR); e = np.sqrt(np.convolve((L * L + R * R) / 2, np.ones(w) / w, "same") + 1e-12)
    nguong = np.sqrt(np.mean((L * L + R * R) / 2)) * 1.1
    g = np.where(e > nguong, (nguong / e) ** 0.5, 1.0)
    g = np.convolve(g, np.ones(w) / w, "same")
    return L * g, R * g


def can_pho(L, R, tram_toi_da=0.74, cao_muc_tieu=0.003):
    """Cân trầm / trung / cao (loa điện thoại không phát được trầm sâu), như 4 bài đầu (trầm 66–78% công suất, cao ~0–1%):
    1) kệ thấp (< 160 Hz) hạ dần tới khi phần trầm (28–250 Hz) ≤ 74% (tối đa −9 dB); 2) kệ cao (> 3,5 kHz) nâng dần tới khi phần
    cao (≥ 4 kHz) ≥ 0,3% (tối đa +4 dB). Lọc trên FFT cả bài, đường cong mềm (không méo pha theo thời gian kiểu IIR)."""
    n = len(L); f = np.fft.rfftfreq(n, 1 / SR)
    XL, XR = np.fft.rfft(L), np.fft.rfft(R)
    P = (np.abs(XL) ** 2 + np.abs(XR) ** 2); P[f < 28] = 0
    lf = np.log2(np.maximum(f, 1.0))
    ke_thap = 1 / (1 + np.exp((lf - np.log2(160)) * 4))     # 1 dưới 160 Hz, 0 trên
    ke_cao = 1 / (1 + np.exp(-(lf - np.log2(3500)) * 4))    # 0 dưới 3,5 kHz, 1 trên
    def thu(gl, gh):
        g = 10 ** ((gl * ke_thap + gh * ke_cao) / 20); q = P * g * g; t = q.sum()
        return g, q[(f >= 28) & (f < 250)].sum() / t, q[f >= 4000].sum() / t
    gl = 0.0
    while gl > -9.0 and thu(gl, 0.0)[1] > tram_toi_da:
        gl -= 0.5
    gh = 0.0
    while gh < 4.0 and thu(gl, gh)[2] < cao_muc_tieu:
        gh += 0.5
    g, tr, ca = thu(gl, gh)
    print("   cân phổ: trầm %+.1f dB, cao %+.1f dB -> trầm %.0f%%, cao %.2f%%" % (gl, gh, tr * 100, ca * 100), flush=True)
    return np.fft.irfft(XL * g, n), np.fft.irfft(XR * g, n)


def lap(n_o, o):
    return n_o * o


# ------------------------------------------------------------------ 10 bài
def bai_sang_trong():   # piano + dàn dây, 88 BPM
    bpm, so_o = 88, 24; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(88)
    ban, day = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(50, "maj7"), (47, "m7"), (43, "maj7"), (45, "6")]   # Dmaj7 Bm7 Gmaj7 A6
    giai = [[78, 76, 74, 76], [74, 73, 71, 73], [71, 74, 78, 76], [76, 73, 69, 73]]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g + 12, kieu)
        for k, m in enumerate(h):
            ban.cong(piano(m, 1.9 * b, 0.55), t0 + 0.015 * k, 0.24, pan=-0.25 + 0.15 * k)
            ban.cong(piano(m, 1.4 * b, 0.42), t0 + 2.5 * b + 0.012 * k, 0.17, pan=-0.2 + 0.13 * k)
        ban.cong(piano(g, 3.6 * b, 0.6), t0, 0.26); ban.cong(piano(g + 7, 1.5 * b, 0.4), t0 + 2 * b, 0.16)
        if 4 <= i < 20:
            for k, m in enumerate(giai[i % 4]):
                if i % 8 >= 4 and k == 3:
                    continue
                ban.cong(piano(m, 0.9 * b, 0.62, 1.2), t0 + k * b + (0.5 * b if k % 2 else 0), 0.20, pan=0.15)
        for m in h[:3]:
            l, r = day_dan(m - 12, o * 0.98, 0.45)
            day.cong(l, t0, 0.13, -0.5); day.cong(r, t0, 0.13, 0.5)
        if i >= 2:
            ban.cong(kick(0.7), t0, 0.26); ban.cong(kick(0.6), t0 + 2.5 * b, 0.2)
            for k in range(8):
                ban.cong(shaker(rng, 0.8 if k % 2 else 0.5), t0 + k * 0.5 * b, 0.09, pan=0.4)
            ban.cong(rim(rng), t0 + 3 * b, 0.12, pan=-0.2)
    L, R = vang(ban.L + day.L, ban.R + day.R, 0.55, 0.26)
    return hoan_thien(loc(L, 13000), loc(R, 13000), T) + (T, bpm)


def pluck_sin(m):
    """pluck mềm + sin tròn (kiểu chuông điện tử) cho bài Tối giản."""
    y = pluck(m, 0.12, 0.5, 0.6) * 0.8; n = int(0.3 * SR)
    y[:n] += 0.25 * np.sin(2 * np.pi * hz(m) * tt(n)) * np.exp(-tt(n) / 0.08)
    return y


def bai_toi_gian():     # minimal tech, 100 BPM
    bpm, so_o = 100, 26; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(100)
    ban, dl = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(57, "min"), (53, "maj"), (48, "maj"), (55, "maj")]
    mau = [0, 2, 1, 2, 0, 3, 1, 2]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu) + [g + 12]
        for k in range(8):
            if k == 5 and i % 2:
                continue
            m = h[mau[k]] + 12
            dl.cong(pluck_sin(m), t0 + k * 0.5 * b, 0.17, pan=-0.2 if k % 2 else 0.2)
        ban.cong(sub(g - 24 if g - 24 >= 28 else g - 12, 1.8 * b), t0, 0.32); ban.cong(sub(g - 24 if g - 24 >= 28 else g - 12, 0.8 * b), t0 + 2.5 * b, 0.22)
        if not (12 <= i < 14):
            ban.cong(kick(0.75), t0, 0.32); ban.cong(kick(0.65), t0 + 2 * b, 0.28)
            for k in range(16):
                ban.cong(hat(rng, manh=1.0 if k % 4 == 2 else 0.4), t0 + k * 0.25 * b, 0.11, pan=0.35)
            ban.cong(rim(rng), t0 + b, 0.13); ban.cong(rim(rng), t0 + 3 * b, 0.13)
    L = ban.L + tre(dl.L, 0.75 * b, 0.38, 5); R = ban.R + tre(dl.R, 0.5 * b, 0.38, 5)
    L, R = vang(L, R, 0.3, 0.12)
    return hoan_thien(loc(L, 12000), loc(R, 12000), T, 0.25) + (T, bpm)


def bai_nang_dong():    # corporate pop, 124 BPM
    bpm, so_o = 124, 32; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(124)
    ban = Ban(T + DUOI)
    vong = [(60, "maj"), (55, "maj"), (57, "min"), (53, "maj")]
    goc = [36, 43, 45, 41]
    giai = [[76, 79, 76, 74, 72, 74, 76, 79], [74, 79, 74, 71, 74, 76, 74, 71], [72, 76, 81, 76, 72, 76, 79, 76], [72, 77, 81, 77, 76, 74, 72, 74]]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)
        for p in (0.5, 1.5, 2.5, 3.5):   # piano nhấn phách lệch
            for k, m in enumerate(h):
                ban.cong(piano(m, 0.35 * b, 0.7), t0 + p * b + 0.006 * k, 0.15, pan=-0.2 + 0.2 * k)
        nghi = 16 <= i < 18
        for k in range(8):
            ban.cong(bass(goc[i % 4] + (12 if k % 2 else 0), 0.45 * b, 0.6), t0 + k * 0.5 * b, 0.22 if not nghi else 0.1)
        if not nghi:
            for p in range(4):
                ban.cong(kick(0.9), t0 + p * b, 0.34)
                ban.cong(hat(rng, mo=True, manh=0.7), t0 + p * b + 0.5 * b, 0.13, pan=0.25)
            for p in (1, 3):
                ban.cong(clap(rng, 0.9), t0 + p * b, 0.3)
        if 8 <= i < 16 or 20 <= i < 30:
            for k, m in enumerate(giai[i % 4]):
                ban.cong(pluck(m, 0.2, 0.7, 0.9), t0 + k * 0.5 * b, 0.14, pan=0.3)
                ban.cong(chuong(m + 12, 0.5), t0 + k * 0.5 * b, 0.04, pan=-0.3)
    L, R = vang(ban.L, ban.R, 0.35, 0.15)
    return hoan_thien(loc(L, 13000), loc(R, 13000), T) + (T, bpm)


def bai_chill_house():  # deep house 118 BPM
    bpm, so_o = 118, 32; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(118)
    ban, hop = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(57, "m7"), (52, "m7"), (53, "maj7"), (55, "6")]
    goc = [45, 40, 41, 43]
    nhip = [0.5, 1.75, 2.5, 3.25]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)
        for p in nhip:
            for m in h:
                hop.cong(hop_house(m, 0.5 + 0.3 * (i % 8 == 7)), t0 + p * b, 0.2, pan=0.0)
        for p in (0, 1.5, 2.5, 3.5):
            ban.cong(bass(goc[i % 4], 0.4 * b, 0.5), t0 + p * b, 0.26)
        mong = 12 <= i < 16
        for p in range(4):
            ban.cong(kick(0.95 if not mong else 0.5), t0 + p * b, 0.36)
            ban.cong(hat(rng, mo=True, manh=0.8), t0 + p * b + 0.5 * b, 0.15, pan=0.2)
        if not mong:
            for p in (1, 3):
                ban.cong(clap(rng, 0.7), t0 + p * b, 0.22, pan=-0.1)
        for k in range(16):
            ban.cong(shaker(rng, 0.8 if k % 2 else 0.5), t0 + k * 0.25 * b, 0.1, pan=0.45)
    hl, hr = tre(hop.L, 0.75 * b, 0.3, 3), tre(hop.R, 0.5 * b, 0.3, 3)
    hl, hr = hl * bom_nhip(len(hl), b, 0.0, 0.4), hr * bom_nhip(len(hr), b, 0.0, 0.4)
    L, R = vang(ban.L + hl, ban.R + hr, 0.4, 0.15)
    return hoan_thien(loc(L, 12500), loc(R, 12500), T) + (T, bpm)


def bai_marimba():      # marimba vui 104 BPM
    bpm, so_o = 104, 28; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(104)
    ban = Ban(T + DUOI)
    vong = [(53, "maj"), (48, "maj"), (50, "min"), (46, "maj")]   # F C Dm Bb
    giai = [[77, 81, 84, 81, 79, 77, 76, 77], [76, 79, 84, 79, 76, 72, 74, 76], [74, 77, 81, 77, 74, 72, 74, 77], [74, 77, 82, 81, 79, 77, 74, 72]]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)
        for k, m in enumerate(giai[i % 4]):
            if i % 4 == 3 and k == 7:
                continue
            ban.cong(marimba(m, 0.9 if k % 2 == 0 else 0.7), t0 + k * 0.5 * b, 0.3, pan=0.2)
        for p, m in ((0, h[0]), (1, h[1]), (2, h[2]), (3, h[1])):
            ban.cong(marimba(m - 12, 0.6), t0 + p * b + 0.5 * b, 0.18, pan=-0.3)
        ban.cong(bass(g - 24, 1.4 * b), t0, 0.22); ban.cong(bass(g - 17, 0.8 * b), t0 + 2 * b, 0.18)
        ban.cong(kick(0.75), t0, 0.28); ban.cong(kick(0.65), t0 + 2 * b, 0.24)
        for p in (1, 3):
            ban.cong(clap(rng, 0.8), t0 + p * b, 0.24, pan=0.1)
        for k in range(8):
            ban.cong(shaker(rng, 1.0 if k % 2 else 0.6), t0 + k * 0.5 * b, 0.13, pan=0.5)
    L, R = vang(ban.L, ban.R, 0.4, 0.18)
    return hoan_thien(loc(L, 12500), loc(R, 12500), T) + (T, bpm)


def bai_lofi_dem():     # lofi hip-hop 76 BPM, hợp âm jazz
    bpm, so_o = 76, 20; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(76)
    ban = Ban(T + DUOI)
    vong = [(51, "maj7"), (48, "m9"), (53, "m7"), (46, "7")]   # Ebmaj7 Cm9 Fm7 Bb7
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)
        for k, m in enumerate(h):
            ban.cong(piano(m, 2.6 * b, 0.45, 0.6), t0 + 0.02 * k, 0.2, pan=-0.3 + 0.15 * k)
        ban.cong(piano(h[-1] + 12, 0.6 * b, 0.4, 0.6), t0 + 2.75 * b, 0.1, pan=0.35)
        ban.cong(bass(g - 12, 1.7 * b, 1.2), t0, 0.3); ban.cong(bass(g - 12 + 7, 0.7 * b, 0.8), t0 + 2.5 * b, 0.2)
        sw = 0.6 * b * 0.5 * 0.33   # swing
        ban.cong(kick(0.85), t0, 0.36); ban.cong(kick(0.7), t0 + 1.5 * b + sw, 0.28); ban.cong(kick(0.75), t0 + 2.5 * b, 0.3)
        for p in (1, 3):
            ban.cong(snare(rng, 0.75, mem=True), t0 + p * b + 0.015, 0.3)
        for k in range(8):
            ban.cong(hat(rng, manh=0.75 if k % 2 else 1.0), t0 + k * 0.5 * b + (sw if k % 2 else 0), 0.17, pan=0.25)
    L, R = vang(ban.L, ban.R, 0.5, 0.22)
    cr = dia_than(rng, len(L)); L, R = L + cr, R + np.roll(cr, 41)
    return hoan_thien(loc(L, 9500), loc(R, 9500), T) + (T, bpm)


def bai_dien_tu_nhe():  # future bass nhẹ, 140 BPM nửa nhịp
    bpm, so_o = 140, 36; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(140)
    ban, ss = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(58, "maj7"), (60, "m7"), (62, "m7"), (53, "add9")]   # Bbmaj7 Cm7 Dm7 Fadd9
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)[:4]
        nhip = [0, 1.5, 2.5, 3.0] if i % 2 == 0 else [0, 1.5, 2.0, 3.0]
        for p in nhip:
            for m in h:
                l, r = supersaw(m, 0.4 * b, 0.55)
                ss.cong(l, t0 + p * b, 0.07, -0.2); ss.cong(r, t0 + p * b, 0.07, 0.2)
        # sub + kick nhỏ hơn bản đầu (đo: trầm 92% dù kệ thấp −9 dB, loa điện thoại nghe đục) -> trầm ~75%
        ban.cong(sub(g - 24, 1.4 * b), t0, 0.15); ban.cong(sub(g - 24, 1.4 * b), t0 + 2 * b, 0.13)
        mong = 16 <= i < 18
        ban.cong(kick(0.9 if not mong else 0.4), t0, 0.27); ban.cong(kick(0.7 if not mong else 0.3), t0 + 1.5 * b, 0.2)
        if not mong:
            ban.cong(clap(rng, 0.9), t0 + 2 * b, 0.3); ban.cong(snare(rng, 0.6), t0 + 2 * b, 0.16)
        for k in range(8):
            ban.cong(hat(rng, manh=0.9 if k % 2 else 0.5), t0 + k * 0.5 * b, 0.12, pan=0.3)
        if i % 4 == 3:
            for k in range(6):
                ban.cong(chuong(84 + (0, 3, 7, 10, 12, 15)[k], 0.4), t0 + 2 * b + k * 0.25 * b, 0.05, pan=0.4)
    sl, sr = ss.L * bom_nhip(len(ss.L), b, 0.0, 0.6), ss.R * bom_nhip(len(ss.R), b, 0.0, 0.6)
    L, R = vang(ban.L + sl, ban.R + sr, 0.35, 0.16)
    return hoan_thien(loc(L, 12500), loc(R, 12500), T) + (T, bpm)


def bai_acoustic():     # guitar gảy ngón 96 BPM
    bpm, so_o = 96, 26; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(96)
    ban = Ban(T + DUOI)
    vong = [(43, (55, 59, 62, 67)), (38, (54, 57, 62, 66)), (40, (55, 59, 64, 67)), (36, (55, 60, 64, 67))]   # G D Em C
    mau = [(0, 0), (0.5, 2), (1, 1), (1.5, 3), (2, 0), (2.5, 2), (3, 1), (3.5, 2)]
    for i in range(so_o):
        t0 = i * o; goc, h = vong[i % 4]
        ban.cong(day_gay(goc, 1.8 * b, 0.4, rng), t0, 0.5, pan=-0.15)
        ban.cong(day_gay(goc + 7, 1.2 * b, 0.4, rng), t0 + 2 * b, 0.4, pan=-0.15)
        for p, k in mau:
            ban.cong(day_gay(h[k], 0.9 * b, 0.5, rng), t0 + p * b + rng.uniform(0, 0.008), 0.42 * (1 if p % 1 == 0 else 0.8), pan=0.2)
        if i >= 2 and not (14 <= i < 16):
            ban.cong(kick(0.6), t0, 0.24); ban.cong(kick(0.5), t0 + 2.5 * b, 0.2)
            ban.cong(snare(rng, 0.5, mem=True), t0 + b, 0.14); ban.cong(snare(rng, 0.5, mem=True), t0 + 3 * b, 0.14)
            for k in range(8):
                ban.cong(shaker(rng, 1.0 if k % 2 else 0.6), t0 + k * 0.5 * b, 0.12, pan=0.45)
        ban.cong(bass(goc, 1.8 * b, 1.2), t0, 0.16)
    L, R = vang(ban.L, ban.R, 0.45, 0.2)
    return hoan_thien(loc(L, 12000), loc(R, 12000), T, 0.22) + (T, bpm)


def bai_hiphop_nhe():   # boom bap 90 BPM + đàn điện
    bpm, so_o = 90, 24; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(90)
    ban = Ban(T + DUOI)
    vong = [(50, "m9"), (43, "7"), (48, "maj7"), (45, "m7")]   # Dm9 G7 Cmaj7 Am7
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)[:4]
        for k, m in enumerate(h):
            ban.cong(dan_dien(m + 12, 1.6 * b, 0.6), t0 + 0.01 * k, 0.17, pan=-0.3 + 0.2 * k)
            ban.cong(dan_dien(m + 12, 0.8 * b, 0.45), t0 + 2.5 * b + 0.01 * k, 0.11, pan=-0.3 + 0.2 * k)
        ban.cong(sub(g - 12 if g - 12 >= 33 else g, 1.6 * b), t0, 0.34); ban.cong(sub(g - 12 if g - 12 >= 33 else g, 0.6 * b), t0 + 2.75 * b, 0.24)
        ban.cong(kick(1.0), t0, 0.4); ban.cong(kick(0.8), t0 + 0.75 * b, 0.3); ban.cong(kick(0.85), t0 + 2.5 * b, 0.34)
        for p in (1, 3):
            ban.cong(snare(rng, 0.95), t0 + p * b, 0.3); ban.cong(clap(rng, 0.5), t0 + p * b + 0.01, 0.12)
        for k in range(8):
            ban.cong(hat(rng, manh=1.0 if k % 2 == 0 else 0.6), t0 + k * 0.5 * b + (0.04 if k % 2 else 0), 0.16, pan=0.25)
    L, R = vang(ban.L, ban.R, 0.4, 0.16)
    return hoan_thien(loc(L, 11500), loc(R, 11500), T) + (T, bpm)


def bai_kham_pha():     # nhịp dồn kiểu phim, mở hộp 100 BPM
    bpm, so_o = 100, 26; b = 60 / bpm; o = 4 * b; T = so_o * o; rng = np.random.default_rng(101)
    ban, day = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(52, "min"), (48, "maj"), (55, "maj"), (50, "maj")]   # Em C G D
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)
        for k in range(8):   # bass móc 8 nốt
            ban.cong(pluck(g - 24 + (12 if k % 4 == 3 else 0), 0.4 * b, 0.4, 0.8) + 0.0, t0 + k * 0.5 * b, 0.26)
        for m in h:
            l, r = day_dan(m, o * 0.98, 0.55)
            day.cong(l, t0, 0.12, -0.6); day.cong(r, t0, 0.12, 0.6)
        ban.cong(kick(0.8), t0, 0.3); ban.cong(kick(0.7), t0 + 2 * b, 0.26)
        if i % 2 == 1:
            ban.cong(tom(45, 0.7), t0 + 3 * b, 0.24); ban.cong(tom(40, 0.7), t0 + 3.5 * b, 0.24)
        for k in range(16):
            ban.cong(hat(rng, manh=0.9 if k % 2 else 0.4), t0 + k * 0.25 * b, 0.08, pan=0.35)
        ban.cong(snare(rng, 0.7, mem=True), t0 + b, 0.18); ban.cong(snare(rng, 0.7, mem=True), t0 + 3 * b, 0.18)
        if i % 4 == 0:
            ban.cong(piano(g + 24, 2 * b, 0.5), t0, 0.12, pan=0.3)
    L, R = vang(ban.L + day.L, ban.R + day.R, 0.5, 0.2)
    return hoan_thien(loc(L, 12500), loc(R, 12500), T) + (T, bpm)


# (file, tên hiện, nhóm phong cách, mô tả, hàm)
BAI = [
    ("poly-sang-trong.mp3", "Sang trọng", "Sang trọng", "piano, dàn dây, nhịp nhẹ · máy cao cấp, mở hộp", bai_sang_trong),
    ("poly-toi-gian.mp3", "Tối giản", "Công nghệ", "pluck dội, sub bass, gõ nhẹ · review gọn", bai_toi_gian),
    ("poly-nang-dong.mp3", "Năng động", "Sôi động", "piano nhấn phách, vỗ tay, 4/4 · khuyến mãi, chốt đơn", bai_nang_dong),
    ("poly-chill-house.mp3", "Chill house", "Sôi động", "hợp âm house, hi-hat lệch nhịp · lướt máy, đổi cảnh nhanh", bai_chill_house),
    ("poly-marimba.mp3", "Marimba vui", "Vui tươi", "marimba, vỗ tay, lắc · mẹo hay, phụ kiện", bai_marimba),
    ("poly-lofi-dem.mp3", "Lofi đêm", "Nhẹ nhàng", "piano jazz, trống lệch, đĩa than · kể chuyện, tư vấn", bai_lofi_dem),
    ("poly-dien-tu-nhe.mp3", "Điện tử nhẹ", "Sôi động", "hợp âm supersaw nhún nhịp · máy mới về, giá sốc", bai_dien_tu_nhe),
    ("poly-acoustic.mp3", "Acoustic", "Nhẹ nhàng", "guitar gảy ngón, lắc nhẹ · tiệm, khách, cảm ơn", bai_acoustic),
    ("poly-hiphop-nhe.mp3", "Hip-hop nhẹ", "Công nghệ", "boom bap, đàn điện · so sánh máy, thông số", bai_hiphop_nhe),
    ("poly-kham-pha.mp3", "Khám phá", "Sang trọng", "nhịp dồn kiểu phim, dàn dây · mở hộp, lộ máy", bai_kham_pha),
]
PHONG_CACH_CU = {"poly-nhe-nhang.mp3": "Nhẹ nhàng", "poly-soi-dong.mp3": "Sôi động", "poly-cong-nghe.mp3": "Công nghệ", "poly-vui-tuoi.mp3": "Vui tươi"}


def ghi_wav(p, L, R):
    x = np.stack([L, R], 1)
    x = loc(x.T, 28, "high").T
    x = np.tanh(x / max(1e-6, np.abs(x).max()) * 1.15) / np.tanh(1.15) * 0.89
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def tao():
    os.makedirs(RA, exist_ok=True)
    pj = os.path.join(RA, "nhac.json")
    kk = json.load(open(pj, encoding="utf-8")) if os.path.isfile(pj) else {}
    for f, pc in PHONG_CACH_CU.items():
        if f in kk:
            kk[f].setdefault("phong_cach", pc)
    chi = os.environ.get("CHI_BAI", "")
    for ten_file, ten, pc, mo_ta, ham in BAI:
        if chi and ten_file not in chi.split(","):
            continue
        L, R, T, bpm = ham()
        with tempfile.TemporaryDirectory() as tm:
            w = os.path.join(tm, "x.wav"); ghi_wav(w, L, R)
            r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", w, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                                "-f", "null", "-"], capture_output=True, text=True)
            j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
            # 1 hệ số cho cả bài + chặn đỉnh (alimiter bù trễ, không đổi độ dài) — không dùng loudnorm để ghi: chế độ động của nó làm
            # nhỏ dần 0,6s cuối bài -> hụt tiếng ở chỗ lặp
            af = "volume=%.2fdB,alimiter=limit=0.8:attack=5:release=60:level=false:latency=1,aresample=44100" % (-16.0 - float(j["input_i"]))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", w, "-af", af, "-map_metadata", "-1", "-c:a", "libmp3lame", "-b:a", "192k",
                            "-metadata", "title=" + ten, "-metadata", "artist=Poly Store (tự tạo)", "-metadata", "copyright=CC0 1.0",
                            os.path.join(RA, ten_file)], check=True)
        kk[ten_file] = {"ten": ten, "mo_ta": mo_ta + " · %d BPM" % bpm, "bpm": bpm, "giay": round(T, 2), "phong_cach": pc,
                        "giay_phep": "CC0 1.0 (Poly Store tự tạo bằng dev/tao_nhac_them.py)"}
        print(ten_file, round(T, 1), "giây", flush=True)
        json.dump(kk, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(kk, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ đo (không nghe được thì đo)
def do(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "2", "-ar", "44100", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, "<f4").reshape(-1, 2).astype(np.float64); m = x.mean(1); n = len(m)
    r2 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True)
    j = json.loads(r2.stderr[r2.stderr.rindex("{"):r2.stderr.rindex("}") + 1])
    X = np.abs(np.fft.rfft(m[: min(n, 44100 * 60)])) ** 2; f = np.fft.rfftfreq(min(n, 44100 * 60), 1 / 44100)
    tong = X[f > 20].sum()
    tram, trung, cao = X[(f > 20) & (f < 250)].sum() / tong, X[(f >= 250) & (f < 4000)].sum() / tong, X[f >= 4000].sum() / tong
    w = 22050; rms = np.array([np.sqrt(np.mean(m[i:i + w] ** 2)) for i in range(0, n - w, w)])
    lang = 20 * np.log10(rms + 1e-9) < -45
    dai_lang = max((len(s) for s in "".join("1" if v else "0" for v in lang).split("0")), default=0) * 0.5
    meo = int((np.abs(x) > 0.995).sum())
    # chỗ nối lặp: so mức 0,5s cuối với 0,5s đầu (dB) + bước nhảy biên độ ở mẫu nối
    a, z = np.sqrt(np.mean(m[:w] ** 2)), np.sqrt(np.mean(m[-w:] ** 2))
    noi_db = 20 * np.log10((z + 1e-9) / (a + 1e-9)); buoc = float(np.abs(x[0] - x[-1]).max())
    return {"giay": round(n / 44100, 1), "lufs": float(j["input_i"]), "dinh_dbtp": float(j["input_tp"]), "tram": round(tram * 100), "trung": round(trung * 100),
            "cao": round(cao * 100, 2), "lang_dai_nhat_s": dai_lang, "mau_meo": meo, "noi_lap_lech_db": round(float(noi_db), 1), "noi_lap_buoc": round(buoc, 3)}


if __name__ == "__main__":
    if "--do" in sys.argv:
        for f in sorted(os.listdir(RA)):
            if f.endswith(".mp3"):
                print(f, json.dumps(do(os.path.join(RA, f)), ensure_ascii=False), flush=True)
    else:
        tao()
