#!/usr/bin/env python3
"""Âm nhấn (sound effect) TỰ TỔNG HỢP bằng numpy — không lấy từ thư viện / CapCut, không bản quyền.

Dùng:  python3 am_nhan.py <thu_muc_ra>          (ghi am-vut.wav, am-vut-len.wav, am-bup.wav, am-ting.wav, am-dap.wav)
Trong code: am_nhan.tao(thu_muc) -> {ten_ngan: ten_file}; am_nhan.lich(...) -> [(ten_file, giây)].

WAV 48 kHz 16-bit stereo. Đỉnh từng file thấp (−20…−21 dBFS) để cộng với tiếng nói (đỉnh ≈ −1,7 dBFS) vẫn khó vượt
−1 dBTP; độ lớn bản xuất vẫn do tiếng nói quyết định (âm nhấn ngắn, ít năng lượng). Sau khi xuất luôn đo đỉnh thật.
  vut      whoosh 0,45s — chỗ chuyển cảnh (đỉnh ở 0,27s, đặt sao cho đỉnh rơi vào giữa chuyển cảnh)
  vut_len  swoosh đi lên 0,5s — lúc thẻ kết hiện
  bup      pop 0,12s — chữ nhãn / sticker / hook hiện, điểm nhấn đổi cảnh
  ting     ting 0,7s — thẻ giá hiện
  dap      thump trầm 0,35s — khung đầu khi mở đầu punch_mo
Hạt ngẫu nhiên cố định: chạy lại ra y hệt từng mẫu (md5 không đổi -> gói chép không đổi).
"""
import json, os, sys, wave

import numpy as np

SR = 48000
DINH_DB = {"vut": -20.0, "vut_len": -20.0, "bup": -21.0, "ting": -21.0, "dap": -20.0}  # 29/10 hạ bup/dap 3 dB: cộng tiếng nói −1,5 vẫn ≤ −1 dBTP
TEN_FILE = {k: "am-" + k.replace("_", "-") + ".wav" for k in DINH_DB}
DINH_GIAY = {"vut": 0.27, "vut_len": 0.36, "bup": 0.0, "ting": 0.0, "dap": 0.0}  # chỗ "nghe thấy" của âm, tính từ đầu file
UU_TIEN = {"ting": 5, "dap": 4, "vut_len": 3, "vut": 2, "bup": 1}
CACH_TOI_THIEU = 0.35  # hai âm nhấn gần hơn thế: giữ âm ưu tiên cao


def _loc_dai(x, f_tam, rong, n_fft=1024, hop=256):
    """Lọc dải thay đổi theo thời gian (STFT): mỗi khung nhân phổ với chuông Gauss quanh f_tam[k] (Hz), rộng `rong` (oct)."""
    win = np.hanning(n_fft)
    pad = np.concatenate([np.zeros(n_fft), x, np.zeros(n_fft)])
    out = np.zeros_like(pad)
    norm = np.zeros_like(pad)
    f = np.fft.rfftfreq(n_fft, 1.0 / SR)
    so_khung = (len(pad) - n_fft) // hop + 1
    for k in range(so_khung):
        a = k * hop
        t = max(0.0, min(1.0, (a - n_fft) / max(1, len(x) - 1)))
        fc = float(f_tam(t))
        oct_ = np.log2(np.maximum(f, 20.0) / fc)
        g = np.exp(-0.5 * (oct_ / rong) ** 2)
        seg = np.fft.irfft(np.fft.rfft(pad[a:a + n_fft] * win) * g, n_fft) * win
        out[a:a + n_fft] += seg
        norm[a:a + n_fft] += win ** 2
    out = out / np.maximum(norm, 1e-6)
    return out[n_fft:n_fft + len(x)]


def _chuan(st, dinh_db):
    m = float(np.abs(st).max()) or 1.0
    return st * (10 ** (dinh_db / 20.0) / m)


def _env(n, tan_cong, giam, dinh=None):
    """Bao biên: lên tuyến tính trong tan_cong giây (hoặc tới `dinh` 0–1 của độ dài), rồi giảm mũ (hằng số giam giây)."""
    t = np.arange(n) / SR
    d0 = dinh * n / SR if dinh is not None else tan_cong
    e = np.where(t < d0, t / max(d0, 1e-4), np.exp(-(t - d0) / giam))
    return e


def vut(len_=False):
    dur = 0.5 if len_ else 0.45
    n = int(SR * dur)
    rng = np.random.default_rng(7 if len_ else 3)
    no = rng.standard_normal(n)
    if len_:
        f_tam = lambda t: 250 * (14.0 ** t)  # 250 Hz -> 3,5 kHz đi lên
        env = _env(n, 0, 0.06, dinh=0.72)
    else:
        f_tam = lambda t: 300 * (10.0 ** (np.sin(np.pi * min(1.0, t / 0.9)) * 1.0))  # 300 -> 3 kHz -> 300
        env = _env(n, 0, 0.07, dinh=0.6)
    x = _loc_dai(no, f_tam, 0.55) * env
    # lia trái -> phải: cảm giác vật bay ngang qua
    p = np.linspace(-0.8, 0.8, n)
    L, R = x * np.sqrt((1 - p) / 2), x * np.sqrt((1 + p) / 2)
    st = np.stack([L, R], 1)
    fade = np.minimum(1.0, (n - np.arange(n)) / (0.01 * SR))[:, None]
    return _chuan(st * fade, DINH_DB["vut_len" if len_ else "vut"])


def bup():
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    f = 180 + 720 * np.exp(-t / 0.018)  # cao độ rơi nhanh 900 -> 180 Hz
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * _env(n, 0.002, 0.035)
    rng = np.random.default_rng(5)
    clk = rng.standard_normal(n) * np.exp(-t / 0.0015) * 0.25  # tiếng tách ngắn đầu âm
    x = x + clk
    return _chuan(np.stack([x, x], 1), DINH_DB["bup"])


def ting():
    n = int(SR * 0.7)
    t = np.arange(n) / SR
    x = np.zeros(n)
    for k, (h, a, tau) in enumerate([(1.0, 1.0, 0.22), (2.76, 0.35, 0.12), (5.40, 0.15, 0.06)]):
        x += a * np.sin(2 * np.pi * 1568 * h * t + k) * np.exp(-t / tau)
    x *= np.minimum(1.0, t / 0.003)
    return _chuan(np.stack([x, x * 0.96], 1), DINH_DB["ting"])


def dap():
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    f = 48 + 90 * np.exp(-t / 0.04)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.003, 0.09)
    rng = np.random.default_rng(11)
    no = _loc_dai(rng.standard_normal(n), lambda _t: 900.0, 0.8) * np.exp(-t / 0.02) * 0.6
    x = x + no
    return _chuan(np.stack([x, x], 1), DINH_DB["dap"])


TAO = {"vut": lambda: vut(False), "vut_len": lambda: vut(True), "bup": bup, "ting": ting, "dap": dap}


def ghi_wav(p, st):
    a = np.clip(np.round(st * 32767), -32768, 32767).astype("<i2")
    with wave.open(p, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(a.tobytes())


def tao(thu_muc, chi=None):
    """Ghi các file âm nhấn vào thu_muc (chỉ các âm trong `chi` nếu có). Trả {tên ngắn: tên file}."""
    os.makedirs(thu_muc, exist_ok=True)
    out = {}
    for k, f in TAO.items():
        if chi is not None and k not in chi:
            continue
        ghi_wav(os.path.join(thu_muc, TEN_FILE[k]), f())
        out[k] = TEN_FILE[k]
    return out


def do_dai(k):
    return {"vut": 0.45, "vut_len": 0.5, "bup": 0.12, "ting": 0.7, "dap": 0.35}[k]


def lich(su_kien, T, het=None):
    """su_kien: [(tên ngắn, giây lúc âm cần 'nghe thấy')] -> [(tên ngắn, giây bắt đầu file)] tăng dần, không chồng nhau:
    hai âm gần nhau < CACH_TOI_THIEU thì giữ âm ưu tiên cao (ting > dap > vut_len > vut > bup); âm bắt đầu phải ≥ 0 và kết
    thúc trước `het` (mặc định T). Âm sau đè đuôi âm trước (đặt theo giờ tăng dần trên 1 track: đè = cắt đuôi tự nhiên)."""
    het = T if het is None else het
    ds = []
    for k, t in su_kien:
        b = round(max(0.0, t - DINH_GIAY[k]), 3)
        if b + min(do_dai(k), 0.2) > het:
            continue
        ds.append((k, b, t))
    ds.sort(key=lambda x: (-UU_TIEN[x[0]], x[2]))
    chon = []
    for k, b, t in ds:
        e = b + do_dai(k)
        ok = True
        for k2, b2, t2 in chon:
            e2 = b2 + do_dai(k2)
            if abs(t - t2) < CACH_TOI_THIEU:
                ok = False
            elif b < e2 and b2 < e:  # chồng file: âm sau đè đuôi âm trước (hoặc bị âm trước đè) -> chỉ cho khi phần còn lại ≥ 0,4s
                truoc, sau = (k2, b2) if b2 <= b else (k, b)
                if min(b, b2) + 0.4 > max(b, b2):
                    ok = False
            if not ok:
                break
        if ok:
            chon.append((k, b, t))
    return [(k, b) for k, b, _ in sorted(chon, key=lambda x: x[1])]


def main():
    out = tao(sys.argv[1])
    print(json.dumps({"am_nhan": out, "thu_muc": sys.argv[1]}, ensure_ascii=False))


if __name__ == "__main__":
    import chung  # bản máy tiệm: stdout UTF-8 trên Windows
    chung.dat_utf8()
    main()
