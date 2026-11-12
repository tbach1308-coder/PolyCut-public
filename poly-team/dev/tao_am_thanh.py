# -*- coding: utf-8 -*-
"""Tạo bộ ÂM THANH HIỆU ỨNG ngắn của POLY Cut (4/11 tối, r20): 15 tiếng vút / bụp / ting / click / chụp ảnh / ting tiền… TỰ TỔNG HỢP
bằng numpy (sóng sin, tiếng ồn lọc, đường bao) — không mẫu âm thanh (sample) nào lấy từ ngoài, như engine/am_nhan.py.
Poly Store phát hành CC0 1.0. Hạt ngẫu nhiên cố định: chạy lại ra y hệt.
Ra: <app>/am-thanh/*.wav (48 kHz, 16 bit, stereo — WAV để khỏi lệch giờ như mp3) + am-thanh.json (tên hiện, nhóm, mô tả, giây, giấy phép).
Độ to: mỗi tiếng chỉnh về cùng độ to "tức thời" lớn nhất (ebur128 M max ≈ −16 LUFS), đỉnh ≤ −1 dBFS; bộ dựng trộn ở 70% (≈ −3 dB).
Dùng:  python dev/tao_am_thanh.py [thư mục ra]   (cần numpy, ffmpeg)"""
import json, os, re, subprocess, sys, tempfile, wave
import numpy as np

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
RA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "am-thanh")
M_DICH = -16.0   # LUFS tức thời lớn nhất của mỗi tiếng


def tt(n):
    return np.arange(n) / SR


def ns(giay):
    return int(round(giay * SR))


def env(n, a, d):
    """Lên tuyến tính a giây rồi tắt mũ (hằng số d giây)."""
    t = tt(n)
    return np.where(t < a, t / max(a, 1e-4), np.exp(-(t - a) / d))


def loc_dai(x, f_tam, rong, n_fft=1024, hop=256):
    """Lọc dải đổi theo thời gian (STFT): chuông Gauss quanh f_tam(t 0..1) Hz, rộng `rong` octave (như am_nhan._loc_dai)."""
    win = np.hanning(n_fft)
    pad = np.concatenate([np.zeros(n_fft), x, np.zeros(n_fft)])
    out, norm = np.zeros_like(pad), np.zeros_like(pad)
    f = np.fft.rfftfreq(n_fft, 1.0 / SR)
    for k in range((len(pad) - n_fft) // hop + 1):
        a = k * hop
        t = max(0.0, min(1.0, (a - n_fft) / max(1, len(x) - 1)))
        g = np.exp(-0.5 * (np.log2(np.maximum(f, 20.0) / float(f_tam(t))) / rong) ** 2)
        out[a:a + n_fft] += np.fft.irfft(np.fft.rfft(pad[a:a + n_fft] * win) * g, n_fft) * win
        norm[a:a + n_fft] += win ** 2
    return (out / np.maximum(norm, 1e-6))[n_fft:n_fft + len(x)]


def loc_thong(x, f0, f1):
    """Lọc thông dải tĩnh bằng FFT (đủ cho tiếng ngắn)."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1.0 / SR)
    X[(f < f0) | (f > f1)] = 0
    return np.fft.irfft(X, len(x))


def st(x, pan=0.0):
    """mono -> stereo, pan -1..1 (hằng công suất)."""
    return np.stack([x * np.cos((pan + 1) * np.pi / 4), x * np.sin((pan + 1) * np.pi / 4)], 1) * 1.414


def mo_cuoi(x, giay=0.01):
    n = len(x); k = max(1, ns(giay))
    e = np.ones(n); e[-k:] = np.linspace(1, 0, k)
    return x * (e[:, None] if x.ndim == 2 else e)


def chuong(f, giay, tat=0.25, hoa=((1.0, 1.0, 1.0), (2.76, 0.35, 0.45), (5.40, 0.15, 0.25))):
    n = ns(giay); t = tt(n); y = np.zeros(n)
    for k, (h, a, kt) in enumerate(hoa):
        y += a * np.sin(2 * np.pi * f * h * t + k) * np.exp(-t / (tat * kt))
    return y * np.minimum(1.0, t / 0.002)


# ------------------------------------------------------------------ 15 tiếng
def vut():          # whoosh ngang 0,45s: dải ồn quét 300 Hz -> 3 kHz -> 300 Hz, lia trái -> phải
    n = ns(0.45); x = loc_dai(np.random.default_rng(3).standard_normal(n), lambda t: 300 * 10 ** np.sin(np.pi * min(1, t / 0.9)), 0.55)
    x *= np.where(tt(n) < 0.27, tt(n) / 0.27, np.exp(-(tt(n) - 0.27) / 0.07))
    p = np.linspace(-0.8, 0.8, n)
    return mo_cuoi(np.stack([x * np.sqrt((1 - p) / 2), x * np.sqrt((1 + p) / 2)], 1) * 1.414)


def vut_len():      # whoosh đi lên 0,55s
    n = ns(0.55); t = tt(n)
    x = loc_dai(np.random.default_rng(7).standard_normal(n), lambda u: 250 * 16 ** u, 0.5)
    x *= np.where(t < 0.4, (t / 0.4) ** 1.5, np.exp(-(t - 0.4) / 0.05))
    return mo_cuoi(st(x))


def luot_nhanh():   # swoosh ngắn, sáng 0,25s
    n = ns(0.25); t = tt(n)
    x = loc_dai(np.random.default_rng(11).standard_normal(n), lambda u: 1500 * 4 ** np.sin(np.pi * u), 0.45)
    x *= np.where(t < 0.12, t / 0.12, np.exp(-(t - 0.12) / 0.035))
    p = np.linspace(0.6, -0.6, n)
    return mo_cuoi(np.stack([x * np.sqrt((1 - p) / 2), x * np.sqrt((1 + p) / 2)], 1) * 1.414)


def tang_dan():     # riser 1,2s: ồn + sin quét lên 200 -> 1600 Hz, to dần, dừng gọn
    n = ns(1.2); t = tt(n); u = t / 1.2
    nz = loc_dai(np.random.default_rng(13).standard_normal(n), lambda v: 400 * 12 ** v, 0.7)
    f = 200 * 8 ** u; sw = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.35 + np.sin(4 * np.pi * np.cumsum(f) / SR) * 0.12
    x = (nz * 0.8 + sw) * u ** 2.2
    return mo_cuoi(st(x), 0.03)


def bup():          # pop 0,12s: cao độ rơi 900 -> 180 Hz + tiếng tách
    n = ns(0.12); t = tt(n)
    f = 180 + 720 * np.exp(-t / 0.018)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.035)
    x += np.random.default_rng(5).standard_normal(n) * np.exp(-t / 0.0015) * 0.25
    return mo_cuoi(st(x))


def pop():          # bong bóng: cao độ vọt 380 -> 1400 Hz trong 40 ms
    n = ns(0.14); t = tt(n)
    f = 380 + 1020 * (1 - np.exp(-t / 0.012))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.03)
    x += 0.15 * np.sin(4 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.015)
    return mo_cuoi(st(x))


def dap():          # thump trầm 0,35s
    n = ns(0.35); t = tt(n)
    f = 48 + 90 * np.exp(-t / 0.04)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.003, 0.09)
    x += loc_dai(np.random.default_rng(11).standard_normal(n), lambda _u: 900.0, 0.8) * np.exp(-t / 0.02) * 0.6
    return mo_cuoi(st(x))


def click():        # click chuột: nhấn + nhả cách 55 ms
    n = ns(0.11); t = tt(n); x = np.zeros(n); rng = np.random.default_rng(17)
    for t0, a in ((0.0, 1.0), (0.055, 0.6)):
        i = ns(t0); m = ns(0.012)
        k = loc_thong(rng.standard_normal(m), 1800, 9000) * np.exp(-tt(m) / 0.0018)
        k += 0.4 * np.sin(2 * np.pi * 3200 * tt(m)) * np.exp(-tt(m) / 0.002)
        x[i:i + m] += k * a
    return mo_cuoi(st(x))


def chup_anh():     # máy ảnh: màn trập 2 tiếng tách + tiếng cơ khí ngắn
    n = ns(0.32); t = tt(n); x = np.zeros(n); rng = np.random.default_rng(19)
    for t0, a, f in ((0.0, 1.0, 2600), (0.105, 0.85, 2100)):
        i = ns(t0); m = ns(0.05)
        k = loc_thong(rng.standard_normal(m), 900, 7000) * np.exp(-tt(m) / 0.006)
        k += 0.5 * np.sin(2 * np.pi * f * tt(m)) * np.exp(-tt(m) / 0.004)
        x[i:i + m] += k * a
    i = ns(0.012); m = ns(0.09)
    x[i:i + m] += loc_thong(rng.standard_normal(m), 400, 2500) * np.exp(-tt(m) / 0.025) * 0.25   # cơ khí
    return mo_cuoi(st(x))


def ting():         # ting 0,7s (G6)
    return mo_cuoi(st(chuong(1568, 0.7, 0.22)))


def ting_tien():    # "ka-ching": tiếng ngăn kéo kim loại + 2 chuông cao
    n = ns(1.0); t = tt(n); rng = np.random.default_rng(23); x = np.zeros(n)
    m = ns(0.12); kl = loc_thong(rng.standard_normal(m), 1500, 9000) * np.exp(-tt(m) / 0.012)
    for f, a in ((2310, 0.5), (3120, 0.35), (4480, 0.2)):
        kl += a * np.sin(2 * np.pi * f * tt(m)) * np.exp(-tt(m) / 0.03)
    x[:m] += kl * 0.8
    for t0, f in ((0.07, 2093.0), (0.13, 2637.0)):
        i = ns(t0); c = chuong(f, 1.0 - t0, 0.28)
        x[i:i + len(c)] += c[: n - i] * 0.6
    return mo_cuoi(np.stack([x, np.roll(x, 40) * 0.97], 1))


def beep():         # báo tin 2 nốt A5 -> E6, sin mềm
    n = ns(0.34); x = np.zeros(n)
    for t0, f, d in ((0.0, 880.0, 0.1), (0.12, 1318.5, 0.2)):
        i = ns(t0); m = ns(d); u = tt(m)
        y = (np.sin(2 * np.pi * f * u) + 0.18 * np.sin(4 * np.pi * f * u)) * np.minimum(1, u / 0.006) * np.exp(-u / (d * 0.8))
        x[i:i + m] += y
    return mo_cuoi(st(x))


def dung():         # chuông "xong / đúng": rải 3 nốt C6 E6 G6 kiểu marimba
    n = ns(0.75); x = np.zeros(n)
    for k, f in enumerate((1046.5, 1318.5, 1568.0)):
        i = ns(0.075 * k); c = chuong(f, 0.75 - 0.075 * k, 0.12, ((1.0, 1.0, 1.0), (4.0, 0.25, 0.3), (10.0, 0.06, 0.1)))
        x[i:i + len(c)] += c * (0.8 + 0.1 * k)
    return mo_cuoi(st(x))


def go_phim():      # gõ phím 0,8s: 6 phím, khoảng cách lệch nhau
    n = ns(0.8); x = np.zeros(n); rng = np.random.default_rng(29)
    for t0 in (0.0, 0.11, 0.19, 0.33, 0.45, 0.6):
        i = ns(t0); m = ns(0.04)
        k = loc_thong(rng.standard_normal(m), 1200, 6000) * np.exp(-tt(m) / 0.004)
        k += 0.3 * np.sin(2 * np.pi * rng.uniform(380, 520) * tt(m)) * np.exp(-tt(m) / 0.008)   # thân phím
        x[i:i + m] += k * rng.uniform(0.6, 1.0)
    return mo_cuoi(st(x, 0.1))


def lap_lanh():     # lấp lánh 0,9s: chuỗi chuông cao 3–6 kHz nhỏ dần, lia rải
    n = ns(1.0); out = np.zeros((n, 2)); rng = np.random.default_rng(31)
    for k in range(9):
        t0 = 0.06 * k + rng.uniform(0, 0.02); i = ns(t0)
        c = chuong(rng.uniform(3000, 6200), 1.0 - t0, 0.09, ((1.0, 1.0, 1.0), (2.4, 0.2, 0.5)))
        out[i:i + len(c)] += st(c, rng.uniform(-0.7, 0.7)) * (1 - k / 11)
    return mo_cuoi(out)


# (khoá, tên file, tên hiện, nhóm, mô tả, giây "nghe thấy" tính từ đầu file, hàm)
AM = [
    ("vut", "vut.wav", "Vút", "chuyen", "Whoosh lướt ngang: đặt ngay trước chỗ chuyển cảnh", 0.27, vut),
    ("vut_len", "vut-len.wav", "Vút lên", "chuyen", "Whoosh đi lên: thẻ giá / thẻ kết hiện", 0.4, vut_len),
    ("luot_nhanh", "luot-nhanh.wav", "Lướt nhanh", "chuyen", "Swoosh ngắn, sáng: lướt qua thông số", 0.12, luot_nhanh),
    ("tang_dan", "tang-dan.wav", "Tăng dần", "chuyen", "Riser 1,2s dồn lên rồi dừng: trước khi lộ máy / lộ giá", 1.15, tang_dan),
    ("bup", "bup.wav", "Bụp", "nhan", "Pop gọn: chữ / nhãn bật lên", 0.0, bup),
    ("pop", "pop.wav", "Pop bong bóng", "nhan", "Tiếng bóng nổ vui: sticker, biểu tượng", 0.02, pop),
    ("dap", "dap.wav", "Đập trầm", "nhan", "Thump trầm: mở đầu, giá sốc", 0.0, dap),
    ("click", "click.wav", "Click chuột", "nhan", "Nhấn chuột: chọn, bấm nút trên màn hình", 0.0, click),
    ("ting", "ting.wav", "Ting", "thong_bao", "Chuông ting: thẻ giá hiện, điểm nhấn", 0.0, ting),
    ("beep", "beep.wav", "Beep thông báo", "thong_bao", "Báo tin 2 nốt: tin nhắn, thông báo", 0.0, beep),
    ("dung", "dung.wav", "Xong / đúng", "thong_bao", "Rải 3 nốt đi lên: test xong, máy đạt", 0.0, dung),
    ("chup_anh", "chup-anh.wav", "Chụp ảnh", "thong_bao", "Màn trập máy ảnh: khung đứng / chụp màn hình", 0.0, chup_anh),
    ("go_phim", "go-phim.wav", "Gõ phím", "thong_bao", "Gõ phím 0,8s: chữ hiện từng chữ, laptop", 0.0, go_phim),
    ("ting_tien", "ting-tien.wav", "Ting tiền", "vui", "Ka-ching: giá tốt, chốt đơn", 0.07, ting_tien),
    ("lap_lanh", "lap-lanh.wav", "Lấp lánh", "vui", "Chuông cao lấp lánh: máy đẹp như mới, mặt lưng bóng", 0.0, lap_lanh),
]
TEN_NHOM = {"chuyen": "Chuyển cảnh", "nhan": "Nhấn", "thong_bao": "Thông báo", "vui": "Vui"}


def ghi(p, x):
    a = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.tobytes())


def m_max(p):
    """LUFS tức thời lớn nhất (cửa sổ 400 ms) đo bằng ffmpeg ebur128 (tiếng ngắn: đệm 0,5s im cho đủ cửa sổ)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "apad=pad_dur=0.5,ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ms = [float(v) for v in re.findall(r"M:\s*(-?[\d.]+)", r.stderr)]
    return max(ms) if ms else None


def main():
    os.makedirs(RA, exist_ok=True)
    kk = {"_ghi_chu": "Âm thanh hiệu ứng kèm POLY Cut (r20, 4/11/2026): Poly Store TỰ TỔNG HỢP bằng dev/tao_am_thanh.py, CC0 1.0. "
                      "Thư viện › Âm thanh đọc file này (tên hiện, nhóm, mô tả).", "nhom": TEN_NHOM, "ds": {}}
    for k, f, ten, nhom, mo_ta, dinh, ham in AM:
        x = ham().astype(np.float64)
        x = x / max(1e-9, np.abs(x).max()) * 10 ** (-3 / 20)
        with tempfile.TemporaryDirectory() as tm:
            w = os.path.join(tm, "x.wav"); ghi(w, x); m = m_max(w)
        g = 10 ** ((M_DICH - m) / 20) if m is not None else 1.0
        g = min(g, 10 ** (-1 / 20) / max(1e-9, np.abs(x).max()))   # đỉnh ≤ −1 dBFS
        x = x * g
        p = os.path.join(RA, f); ghi(p, x)
        kk["ds"][f] = {"khoa": k, "ten": ten, "nhom": nhom, "mo_ta": mo_ta, "giay": round(len(x) / SR, 3), "dinh": dinh,
                       "giay_phep": "CC0 1.0 (Poly Store tự tạo bằng dev/tao_am_thanh.py)"}
        print("%-14s %5.2fs  M max %6.1f -> %6.1f LUFS  đỉnh %5.1f dBFS" % (f, len(x) / SR, m or -99, m_max(p) or -99, 20 * np.log10(np.abs(x).max())))
    json.dump(kk, open(os.path.join(RA, "am-thanh.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
