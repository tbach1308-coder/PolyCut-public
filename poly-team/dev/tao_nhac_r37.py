# -*- coding: utf-8 -*-
"""NGUYÊN MẪU r37 (11/11/2026, anh: "âm thanh hạn chế quá"): 8 bài nhạc nền TỰ TẠO có CHỖ DROP rõ (để cắt cảnh đúng nhịp) —
drop điện tử, phonk, future bass, tropical house, trap, piano sang trọng, corporate tươi, hồi hộp khám phá.
Dùng lại nhạc cụ / trống / vang của dev/tao_nhac.py + dev/tao_nhac_them.py (tự tổng hợp), cộng thêm PIANO THẬT lấy mẫu từ
"Meta Piano" (facebookincubator/Meta-open-sound, CC0 1.0, 352 mẫu; ở đây dùng 48 mẫu Vel02/Vel03, mỗi quãng ba thứ, dịch ±1 nửa cung).
Hợp âm là vòng phổ thông, giai điệu tự đặt -> bài ra: CC0 1.0 (Poly Store), mẫu piano CC0 (Meta) không cần ghi công.
Ra: <thư mục>/<khoá>.wav (44,1 kHz, 16 bit, stereo, CHƯA chuẩn hoá) + nhac-tu-tao.json (tên, nhóm, BPM, giây, drop[] giây).
Dùng:  python dev/tao_nhac_r37.py <thư mục ra> <thư mục mẫu meta-piano>     CHI_BAI=khoa1,khoa2 để tạo lại vài bài."""
import json, os, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tao_nhac import SR, hz, tt, env_ad, env_asr, loc, Ban, kick, snare, clap, hat, shaker, bass, pluck, day_gay, chuong, vang, tre, bom_nhip
from tao_nhac_them import piano as piano_tong_hop, marimba, day_dan, supersaw, sub, rim, tom, hop_am, hoan_thien

RA = sys.argv[1] if len(sys.argv) > 1 else "nhac-tu-tao"
MAU = sys.argv[2] if len(sys.argv) > 2 else "meta-piano"
DUOI = 3.0


# ------------------------------------------------------------------ piano thật (mẫu Meta, CC0)
_PIANO = {}
_TEN = {0: "C", 3: "Ds", 6: "Fs", 9: "A"}


def _doc_mau(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").astype(np.float64)


def piano_that(m, dai, vel=0.7):
    """Nốt piano từ mẫu ghi âm thật gần nhất (cách ≤ 1 nửa cung), dịch cao độ bằng nội suy, nhả phím tắt trong 0,3s."""
    lop = 3 if vel >= 0.65 else 2
    goc = min((g for g in range(24, 94) if g % 12 in _TEN), key=lambda g: abs(g - m))
    k = (goc, lop)
    if k not in _PIANO:
        p = os.path.join(MAU, "INSPiano_Vel0%d_%s%d_01.ogg" % (lop, _TEN[goc % 12], goc // 12 - 1))
        _PIANO[k] = _doc_mau(p)
    x = _PIANO[k]; r = 2 ** ((m - goc) / 12)
    n = min(int((dai + 0.35) * SR), int(len(x) / r) - 1)
    y = np.interp(np.arange(n) * r, np.arange(len(x)), x)
    t = tt(n); y *= np.clip(1 - (t - dai) / 0.3, 0, 1)
    return y * (0.6 + 0.6 * vel)


# ------------------------------------------------------------------ đồ nghề dồn / drop
def roll(ban, rng, t0, dai, b, vol=0.3, pan=0.0):
    """Snare dồn: 8 -> 16 -> 32 nốt, to dần."""
    t = t0
    while t < t0 + dai - 1e-6:
        u = (t - t0) / dai; buoc = b / 2 if u < 0.5 else (b / 4 if u < 0.85 else b / 8)
        ban.cong(snare(rng, 0.5 + 0.5 * u), t, vol * (0.35 + 0.65 * u), pan)
        t += buoc


def riser(dai, rng, len_=8.0):
    """Tiếng ồn qua bộ lọc dải quét lên (biquad giữ trạng thái giữa các khối 256 mẫu -> không lách cách), to dần."""
    from scipy.signal import lfilter
    n = int(dai * SR); t = tt(n); u = t / dai
    x = rng.uniform(-1, 1, n); y = np.zeros(n); k = 256; zi = np.zeros(2)
    for a in range(0, n, k):
        f = min(400 * len_ ** u[a], SR * 0.42); w = 2 * np.pi * f / SR; al = np.sin(w) / (2 * 1.1)
        bb = np.array([al, 0, -al]) / (1 + al); aa = np.array([1, -2 * np.cos(w) / (1 + al), (1 - al) / (1 + al)])
        y[a:a + k], zi = lfilter(bb, aa, x[a:a + k], zi=zi)
    return y * u ** 2 * 2.0


def crash(rng, manh=1.0):
    n = int(2.2 * SR); t = tt(n)
    c = sum(np.sign(np.sin(2 * np.pi * f * t + rng.uniform(0, 6))) for f in (317, 461, 587, 811, 1023, 1471, 1913, 2617))
    c = loc(0.12 * c + rng.uniform(-1, 1, n), 3500, "high")
    return c * (0.7 * np.exp(-t / 1.0) + 0.3 * np.exp(-t / 0.08)) * manh * 0.5


def boom(manh=1.0):
    n = int(1.6 * SR); t = tt(n)
    f = 38 + 110 * np.exp(-t * 20)
    return np.tanh(1.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)) * manh


def cowbell(m, rng):
    n = int(0.45 * SR); t = tt(n); f = hz(m)
    x = np.sign(np.sin(2 * np.pi * f * t)) + np.sign(np.sin(2 * np.pi * f * 1.44 * t))
    return loc(x, [600, 3200], "band") * (0.75 * np.exp(-t / 0.035) + 0.25 * np.exp(-t / 0.22)) * 0.5


def b808(m, dai, truot=0.0, meo=2.5):
    n = int((dai + 0.1) * SR); t = tt(n); f = hz(m) * 2 ** (truot / 12 * np.clip((t - dai * 0.6) / (dai * 0.4 + 1e-6), 0, 1))
    y = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.8 * np.exp(-t * 40))) / SR)
    return np.tanh(meo * y) / np.tanh(meo) * env_asr(n, 0.004, 0.08, dai) * 0.8


def lead_saw(m, dai, sang=0.5):
    f = hz(m); n = int((dai + 0.3) * SR); t = tt(n); y = np.zeros(n)
    for c in (-0.12, 0.0, 0.11):
        ph = 2 * np.pi * f * (1 + c / 100) * t
        for k in range(1, 12):
            y += np.sin(k * ph) / k ** (1 + 1.2 * (1 - sang))
    return loc(y * env_asr(n, 0.01, 0.12, dai) / 4, 4500)


def nghi_loc(L, R, t0, t1, f0=500, f1=16000):
    """Mở dần bộ lọc thấp từ t0 tới t1 (đoạn dồn), trước t0 giữ ở f0."""
    out = []
    for X in (L, R):
        Y = X.copy(); k = 2048
        for a in range(0, int(t1 * SR), k):
            u = np.clip((a / SR - t0) / max(1e-6, t1 - t0), 0, 1); f = f0 * (f1 / f0) ** u
            Y[a:a + k] = loc(X[max(0, a - 1024):a + k], f)[-len(Y[a:a + k]):]
        out.append(Y)
    return out


# ------------------------------------------------------------------ 8 bài
def bai_drop_edm():      # 128 BPM, drop ô 8 và ô 24
    bpm = 128; b = 60 / bpm; o = 4 * b; so_o = 32; T = so_o * o; rng = np.random.default_rng(128)
    ban, ss = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(57, "min"), (53, "maj"), (60, "maj"), (55, "maj")]          # Am F C G
    drop = [8, 24]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)
        trong_drop = (8 <= i < 16) or (24 <= i < 32)
        if not trong_drop:   # intro / break: pad + piano rải
            for m in h:
                l, r = supersaw(m, o * 0.95, 0.3); ss.cong(l, t0, 0.05, -0.3); ss.cong(r, t0, 0.05, 0.3)
            for k in range(8):
                ban.cong(pluck(h[k % 3] + 12, 0.25, 0.6), t0 + k * b / 2, 0.12, 0.25 * (-1) ** k)
            if i in (6, 7, 22, 23):
                roll(ban, rng, t0, o, b, 0.22 if i % 2 == 0 else 0.3)
            if i >= 2 and i not in (7, 23):
                for k in range(4):
                    ban.cong(kick(0.5), t0 + k * b, 0.2)
        else:
            for k in range(4):
                ban.cong(kick(1.0), t0 + k * b, 0.36); ban.cong(hat(rng, mo=True, manh=0.8), t0 + k * b + b / 2, 0.13, 0.2)
            ban.cong(clap(rng), t0 + b, 0.28); ban.cong(clap(rng), t0 + 3 * b, 0.28)
            for p in (0, 0.75, 1.5, 2.5, 3.0):
                for m in h:
                    l, r = supersaw(m + 12, 0.45 * b, 0.65); ss.cong(l, t0 + p * b, 0.06, -0.3); ss.cong(r, t0 + p * b, 0.06, 0.3)
            mel = [h[2] + 12, h[1] + 12, h[2] + 12, h[0] + 24, h[2] + 12, h[1] + 12, h[0] + 12, h[1] + 12]
            for k, m in enumerate(mel):
                ban.cong(lead_saw(m, b * 0.45, 0.6), t0 + k * b / 2, 0.06, 0.1)
            ban.cong(sub(g - 24, o * 0.9), t0, 0.22)
        if i in drop:
            ban.cong(crash(rng), t0, 0.35); ban.cong(boom(), t0, 0.35)
        if i in (7, 23):
            r_ = riser(o, rng); ban.cong(r_, t0, 0.12, -0.2); ban.cong(r_, t0, 0.12, 0.2)
    sl = ss.L * bom_nhip(len(ss.L), b, 0, 0.6); sr = ss.R * bom_nhip(len(ss.R), b, 0, 0.6)
    L, R = vang(ban.L + sl, ban.R + sr, 0.4, 0.16)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_phonk():         # 130 BPM, cowbell + 808 méo, drop ô 4 và ô 20
    bpm = 130; b = 60 / bpm; o = 4 * b; so_o = 32; T = so_o * o; rng = np.random.default_rng(130)
    ban = Ban(T + DUOI)
    nen = [49, 49, 52, 47]                                              # C#, C#, E, B (C# thứ)
    cb = [73, 76, 73, 80, 78, 76, 73, 71, 73, 76, 73, 80, 81, 80, 78, 76]   # cowbell 16 nốt / ô (giai điệu tự đặt)
    drop = [4, 20]
    for i in range(so_o):
        t0 = i * o; g = nen[i % 4]; manh = (4 <= i < 16) or (20 <= i < 32)
        for k, m in enumerate(cb):
            if manh or k % 2 == 0:
                ban.cong(cowbell(m + (0 if i % 4 != 2 else 3), rng), t0 + k * b / 4, 0.13 if manh else 0.1, 0.15)
        if manh:
            ban.cong(b808(g - 12, 1.5 * b, -5 if i % 2 else 0), t0, 0.34); ban.cong(b808(g - 12, 1.2 * b), t0 + 2.5 * b, 0.28)
            ban.cong(kick(1.0), t0, 0.3); ban.cong(kick(0.8), t0 + 2.5 * b, 0.25)
            ban.cong(snare(rng, 0.9), t0 + 2 * b, 0.3); ban.cong(clap(rng), t0 + 2 * b, 0.2)
            for k in range(16 if i % 4 == 3 else 8):
                st_ = b / 4 if i % 4 == 3 else b / 2
                ban.cong(hat(rng, manh=0.7 + 0.3 * (k % 2)), t0 + k * st_, 0.1, 0.3)
        elif i in (3, 19):
            roll(ban, rng, t0, o, b, 0.25)
            r_ = riser(o, rng); ban.cong(r_, t0, 0.1)
        if i in drop:
            ban.cong(boom(1.0), t0, 0.4); ban.cong(crash(rng), t0, 0.25)
    L, R = vang(ban.L, ban.R, 0.45, 0.2)
    L, R = nghi_loc(L, R, 0, 4 * o, 900, 16000)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_future_bass():   # 150 BPM (cảm giác 75), drop ô 8 và ô 24
    bpm = 150; b = 60 / bpm; o = 4 * b; so_o = 32; T = so_o * o; rng = np.random.default_rng(150)
    ban, ss = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(53, "maj7"), (55, "add9"), (57, "m7"), (52, "m7")]          # Fmaj7 Gadd9 Am7 Em7
    drop = [8, 24]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)[:4]; trong = (8 <= i < 16) or (24 <= i < 32)
        if trong:
            for p in (0, 0.5, 1.5, 2.0, 2.75, 3.5):
                for m in h:
                    l, r = supersaw(m + 12, 0.42 * b, 0.6); ss.cong(l, t0 + p * b, 0.07, -0.35); ss.cong(r, t0 + p * b, 0.07, 0.35)
            ban.cong(kick(1.0), t0, 0.34); ban.cong(kick(0.8), t0 + 1.5 * b, 0.25)
            ban.cong(snare(rng, 1.0), t0 + 2 * b, 0.3); ban.cong(clap(rng), t0 + 2 * b, 0.22)
            for k in range(8):
                ban.cong(hat(rng, manh=0.5 + 0.4 * (k % 2)), t0 + k * b / 2, 0.1, 0.3)
            ban.cong(sub(g - 24, 1.8 * b), t0, 0.2); ban.cong(sub(g - 24, 1.8 * b), t0 + 2 * b, 0.18)
            for k, d in enumerate((0, 7, 12, 7, 16, 12, 7, 12)):
                ban.cong(chuong(h[0] + 24 + d, 0.4), t0 + k * b / 2, 0.035, 0.4 * (-1) ** k)
        else:
            for m in h:
                l, r = day_dan(m, o * 0.95, 0.4); ss.cong(l, t0, 0.07, -0.3); ss.cong(r, t0, 0.07, 0.3)
            for k in range(4):
                ban.cong(piano_tong_hop(h[k % 4] + 12, b * 0.9, 0.5), t0 + k * b, 0.12, 0.2)
            if i in (7, 23):
                roll(ban, rng, t0, o, b, 0.28); r_ = riser(o, rng); ban.cong(r_, t0, 0.12)
            elif i >= 4:
                ban.cong(kick(0.5), t0, 0.15); ban.cong(snare(rng, 0.5, True), t0 + 2 * b, 0.12)
        if i in drop:
            ban.cong(crash(rng), t0, 0.3); ban.cong(boom(0.8), t0, 0.3)
    sl = ss.L * bom_nhip(len(ss.L), b, 0, 0.7); sr = ss.R * bom_nhip(len(ss.R), b, 0, 0.7)
    L, R = vang(ban.L + sl, ban.R + sr, 0.45, 0.18)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_tropical():      # tropical house 105 BPM, drop ô 8 và ô 20
    bpm = 105; b = 60 / bpm; o = 4 * b; so_o = 28; T = so_o * o; rng = np.random.default_rng(105)
    ban = Ban(T + DUOI)
    vong = [(62, "m7"), (55, "maj7"), (60, "add9"), (57, "m7")]          # Dm7 Gmaj7 Cadd9 Am7
    giai = [74, 72, 69, 72, 74, 76, 74, 72]                              # marimba tự đặt
    drop = [8, 20]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu)[:4]; trong = (8 <= i < 16) or (20 <= i < 28)
        for k in range(4):          # hợp âm đánh lệch phách (pluck)
            for m in h:
                ban.cong(pluck(m, 0.2, 0.5), t0 + k * b + b / 2, 0.055 if trong else 0.04, 0.2)
        if trong or i >= 4:
            for k, m in enumerate(giai):
                ban.cong(marimba(m + (0 if i % 2 == 0 else -2), 0.9), t0 + k * b / 2 + (b / 4 if k % 3 == 2 else 0), 0.12 if trong else 0.07, -0.25)
        if trong:
            for k in range(4):
                ban.cong(kick(0.9), t0 + k * b, 0.3); ban.cong(shaker(rng), t0 + k * b + b / 2, 0.2, 0.4)
            ban.cong(clap(rng, 0.8), t0 + b, 0.2); ban.cong(clap(rng, 0.8), t0 + 3 * b, 0.2)
            ban.cong(bass(g - 24, 0.8 * b), t0, 0.24); ban.cong(bass(g - 24, 0.4 * b), t0 + 1.5 * b, 0.2); ban.cong(bass(g - 12, 0.4 * b), t0 + 3 * b, 0.18)
        elif i in (7, 19):
            roll(ban, rng, t0, o, b, 0.22); ban.cong(riser(o, rng, 6.0), t0, 0.08)
        elif i >= 4:
            ban.cong(rim(rng), t0 + b, 0.1); ban.cong(rim(rng), t0 + 3 * b, 0.1)
        if i in drop:
            ban.cong(crash(rng, 0.8), t0, 0.2)
    L, R = vang(ban.L, ban.R, 0.4, 0.2)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_trap():          # trap 140 BPM (cảm giác 70), chuông + 808, drop ô 4 và ô 16
    bpm = 140; b = 60 / bpm; o = 4 * b; so_o = 28; T = so_o * o; rng = np.random.default_rng(140)
    ban = Ban(T + DUOI)
    nen = [57, 53, 48, 52]                                               # Am F C E
    giai = [81, 84, 83, 79, 81, 76, 79, 77]
    drop = [4, 16]
    for i in range(so_o):
        t0 = i * o; g = nen[i % 4]; trong = (4 <= i < 12) or (16 <= i < 28)
        for k, m in enumerate(giai):
            ban.cong(chuong(m - (0 if i % 4 < 2 else 3), 0.6), t0 + k * b / 2, 0.07, 0.3 * (-1) ** k)
        for m in hop_am(g, "min" if g != 53 and g != 48 else "maj"):
            l, r = day_dan(m, o * 0.95, 0.3); ban.cong(l, t0, 0.04, -0.4); ban.cong(r, t0, 0.04, 0.4)
        if trong:
            ban.cong(b808(g - 24, 1.4 * b), t0, 0.36); ban.cong(b808(g - 24, 0.7 * b, 12 if i % 2 else 0), t0 + 2.75 * b, 0.3)
            ban.cong(kick(1.0), t0, 0.3); ban.cong(kick(0.8), t0 + 2.75 * b, 0.22)
            ban.cong(snare(rng, 1.0), t0 + 2 * b, 0.3); ban.cong(clap(rng), t0 + 2 * b, 0.2)
            t = 0.0
            while t < 4 - 1e-6:   # hi-hat có đoạn cuộn 1/16 -> 1/32
                cuon = (i % 2 == 1 and 3.0 <= t < 4.0)
                ban.cong(hat(rng, manh=0.6 + 0.4 * ((t * 2) % 1 == 0)), t0 + t * b, 0.09, 0.3)
                t += 0.125 if cuon else 0.5
        elif i in (3, 15):
            roll(ban, rng, t0, o, b, 0.2); ban.cong(riser(o, rng), t0, 0.1)
        if i in drop:
            ban.cong(boom(), t0, 0.35); ban.cong(crash(rng, 0.7), t0, 0.2)
    L, R = vang(ban.L, ban.R, 0.4, 0.18)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_piano_sang_trong():   # piano thật 84 BPM + dây, nhịp nhẹ vào ở ô 8 ("drop" mềm)
    bpm = 84; b = 60 / bpm; o = 4 * b; so_o = 22; T = so_o * o; rng = np.random.default_rng(84)
    ban, ds = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(50, "maj7"), (47, "m7"), (43, "maj7"), (45, "7")]            # Dmaj7 Bm7 Gmaj7 A7
    giai = [[78, 76, 74, 73], [74, 73, 71, 69], [71, 74, 78, 76], [76, 73, 69, 73]]
    drop = [8]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu); co_nhip = i >= 8
        ban.cong(piano_that(g - 12, o * 0.95, 0.55), t0, 0.32)
        for k, m in enumerate(h[1:] + [h[0] + 12]):
            ban.cong(piano_that(m + 12, o * 0.9 - k * b / 4, 0.45), t0 + k * b / 4 + b / 8, 0.22, 0.15)
        for k, m in enumerate(giai[i % 4]):
            if i >= 4:
                ban.cong(piano_that(m, b * 0.9, 0.7 if k == 0 else 0.6), t0 + k * b, 0.3, -0.1)
        for m in h[:3]:
            l, r = day_dan(m + 12, o * 0.98, 0.35); ds.cong(l, t0, 0.05 if i >= 4 else 0.03, -0.35); ds.cong(r, t0, 0.05 if i >= 4 else 0.03, 0.35)
        if co_nhip and i < so_o - 1:
            ban.cong(kick(0.7), t0, 0.2); ban.cong(kick(0.5), t0 + 2.5 * b, 0.14)
            ban.cong(snare(rng, 0.6, True), t0 + b, 0.1); ban.cong(snare(rng, 0.6, True), t0 + 3 * b, 0.1)
            for k in range(8):
                ban.cong(shaker(rng, 0.7), t0 + k * b / 2, 0.08, 0.3)
            ban.cong(sub(g - 24, o * 0.9), t0, 0.14)
        if i == 7:
            ban.cong(riser(o, rng, 5.0), t0, 0.05)
        if i in drop:
            ban.cong(crash(rng, 0.5), t0, 0.1)
    L, R = vang(ban.L + ds.L, ban.R + ds.R, 0.5, 0.22)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_corporate():     # corporate tươi 118 BPM: piano thật nhấn phách + ukulele + vỗ tay, lên ô 8
    bpm = 118; b = 60 / bpm; o = 4 * b; so_o = 28; T = so_o * o; rng = np.random.default_rng(118)
    ban = Ban(T + DUOI)
    vong = [(60, "maj"), (55, "maj"), (57, "min"), (53, "maj")]          # C G Am F
    drop = [8, 20]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu); len_ = (8 <= i < 16) or (20 <= i < 28)
        for k in range(8):
            if k % 2 == 1 or len_:
                for m in h:
                    ban.cong(piano_that(m, b * 0.35, 0.6 if k % 2 else 0.45), t0 + k * b / 2, 0.11, 0.1)
        for k, p in enumerate((0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5)):
            ban.cong(day_gay(h[k % 3] + 12, 0.3, 0.6, rng), t0 + p * b, 0.12 if i >= 4 else 0.08, -0.3)
        if i >= 4:
            ban.cong(bass(g - 24, b * 0.8), t0, 0.22); ban.cong(bass(g - 24, b * 0.4), t0 + 2 * b, 0.2); ban.cong(bass(g - 12, b * 0.4), t0 + 3.5 * b, 0.16)
            for k in range(4):
                ban.cong(kick(0.85 if len_ else 0.6), t0 + k * b, 0.26 if len_ else 0.18)
            ban.cong(clap(rng), t0 + b, 0.24 if len_ else 0.15); ban.cong(clap(rng), t0 + 3 * b, 0.24 if len_ else 0.15)
            for k in range(8):
                ban.cong(hat(rng, manh=0.6), t0 + k * b / 2 + b / 4, 0.08, 0.3)
        if len_:
            mel = [h[2] + 12, h[2] + 12, h[1] + 12, h[2] + 12, h[0] + 24, h[2] + 12, h[1] + 12, h[0] + 12]
            for k, m in enumerate(mel):
                ban.cong(chuong(m + 12, 0.5), t0 + k * b / 2, 0.035, 0.35)
        if i in (7, 19):
            roll(ban, rng, t0 + 2 * b, 2 * b, b, 0.2)
        if i in drop:
            ban.cong(crash(rng, 0.7), t0, 0.15)
    L, R = vang(ban.L, ban.R, 0.35, 0.15)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


def bai_hoi_hop():       # hồi hộp khám phá 100 BPM: dây nhấp nhịp + tích tắc, dồn -> NỔ ô 8 và ô 20
    bpm = 100; b = 60 / bpm; o = 4 * b; so_o = 28; T = so_o * o; rng = np.random.default_rng(100)
    ban, ds = Ban(T + DUOI), Ban(T + DUOI)
    vong = [(50, "min"), (46, "maj"), (48, "maj"), (45, "min")]          # Dm Bb C Am
    drop = [8, 20]
    for i in range(so_o):
        t0 = i * o; g, kieu = vong[i % 4]; h = hop_am(g, kieu); no = (8 <= i < 16) or (20 <= i < 28)
        for k in range(16):             # dây nhấp 1/16 (ostinato)
            m = (h[0] - 12, h[0], h[2] - 12, h[0])[k % 4]
            l, r = day_dan(m, b / 4 * 0.8, 0.55 if no else 0.4); ds.cong(l, t0 + k * b / 4, 0.05, -0.3); ds.cong(r, t0 + k * b / 4, 0.05, 0.3)
        for k in range(4):
            ban.cong(rim(rng), t0 + k * b + b / 2, 0.06, 0.5)
        if no:
            ban.cong(tom(g - 24, 1.0), t0, 0.3); ban.cong(tom(g - 24, 0.8), t0 + 0.75 * b, 0.22); ban.cong(tom(g - 21, 0.9), t0 + 2.5 * b, 0.25)
            ban.cong(kick(1.0), t0, 0.3); ban.cong(kick(0.9), t0 + 2 * b, 0.25); ban.cong(snare(rng, 1.0), t0 + 3 * b, 0.25)
            for m in h:
                ban.cong(piano_that(m + 12, o * 0.9, 0.7), t0, 0.12)
            ban.cong(sub(g - 24, o * 0.9), t0, 0.2)
        elif i >= 2:
            ban.cong(kick(0.6), t0, 0.16)
            if i in (7, 19):
                roll(ban, rng, t0, o, b, 0.26); ban.cong(riser(o, rng), t0, 0.12)
        if i in drop:
            ban.cong(boom(1.0), t0, 0.45); ban.cong(crash(rng), t0, 0.25)
    L, R = vang(ban.L + ds.L, ban.R + ds.R, 0.55, 0.22)
    return hoan_thien(L, R, T) + (T, bpm, [d * o for d in drop])


BAI = [
    ("poly-drop-dien-tu", "Drop điện tử", "Trend có drop", "EDM nhẹ, dồn trống rồi drop supersaw · lộ máy, mở hộp", bai_drop_edm),
    ("poly-phonk", "Phonk", "Trend có drop", "cowbell + 808 méo kiểu phonk · khoe máy, game, trend", bai_phonk),
    ("poly-future-bass", "Future bass", "Trend có drop", "hợp âm supersaw nhún, chuông · máy mới về, giá sốc", bai_future_bass),
    ("poly-trap", "Trap khoe máy", "Trend có drop", "chuông + 808, hi-hat cuộn · so sánh, khoe cấu hình", bai_trap),
    ("poly-tropical", "Tropical house", "Vui tươi", "marimba, pluck lệch phách, shaker · phụ kiện, mẹo hay", bai_tropical),
    ("poly-piano-sang-trong", "Piano sang trọng", "Sang trọng", "piano thật, dàn dây, nhịp nhẹ vào ô 9 · máy cao cấp", bai_piano_sang_trong),
    ("poly-corporate", "Tươi sáng", "Vui tươi", "piano thật nhấn phách, ukulele, vỗ tay · giới thiệu tiệm, ưu đãi", bai_corporate),
    ("poly-hoi-hop", "Hồi hộp khám phá", "Hồi hộp", "dây nhấp nhịp, tích tắc, trống tom nổ · mở hộp, lộ giá", bai_hoi_hop),
]


def ghi_wav(p, L, R):
    x = np.stack([L, R], 1)
    x = loc(x.T, 28, "high").T
    x = np.tanh(x / max(1e-6, np.abs(x).max()) * 1.15) / np.tanh(1.15) * 0.89
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def main():
    os.makedirs(RA, exist_ok=True)
    pj = os.path.join(RA, "nhac-tu-tao.json")
    kk = json.load(open(pj, encoding="utf-8")) if os.path.isfile(pj) else {}
    chi = [x for x in os.environ.get("CHI_BAI", "").split(",") if x]
    for khoa, ten, nhom, mo_ta, ham in BAI:
        if chi and khoa not in chi:
            continue
        L, R, T, bpm, drop = ham()
        ghi_wav(os.path.join(RA, khoa + ".wav"), L, R)
        kk[khoa] = {"ten": ten, "nhom": nhom, "mo_ta": mo_ta, "bpm": bpm, "giay": round(T, 2), "drop": [round(d, 2) for d in drop],
                    "nhip_dau": 0.0}
        print(khoa, round(T, 1), "giây, drop", kk[khoa]["drop"], flush=True)
        json.dump(kk, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
