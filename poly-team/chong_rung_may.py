# -*- coding: utf-8 -*-
"""POLY Cut — đo độ RUNG TAY của 1 clip (4/11/2026, Chống rung). Chạy bằng Python của BỘ DỰNG (engine/.venv: numpy + opencv), app gọi
qua chong_rung.py, trên BẢN XEM NHẸ 720p của clip (đã có sẵn, giải mã nhanh, ảnh 160px xám).

  python chong_rung_may.py do <video> <ra.json>

Cách đo = cách của bộ dựng (engine/phan_tich.py, "rung_tay"): dịch khung từng khung bằng phase correlation trên ảnh 160px, cộng thành
đường đi máy quay, trừ đường đi đã làm mượt ~0,27s -> phần GIẬT còn lại (% bề rộng khung, trung vị). Lia / đi bộ chủ ý (đi đều, chậm)
không tính là rung. Mốc của bộ dựng (đo trên clip iPhone thật): ~0,18 = đã ổn định, ~0,32 = cầm tay đi bộ, > 0,25 nên chống rung.
Ghi {"trung_vi", "p90", "khung", "giay"}; in XONG=<json> hoặc LOI=<chữ>.
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

APP = os.path.dirname(os.path.abspath(__file__))
KW = {"creationflags": 0x08000000} if os.name == "nt" else {}
RONG = 160


def ffmpeg():
    try:
        sys.path.insert(0, os.getcwd())
        import chung   # engine/chung.py (cwd = engine): ffmpeg của bộ dựng
        return chung.FFMPEG
    except Exception:  # noqa
        return "ffmpeg"


def doc_khung(p, toi_da=1800):
    """Mọi khung (tối đa 60s đầu) -> mảng [n, h, 160] float32 xám, 30 khung/giây."""
    # khung PGM nối nhau: đầu mỗi khung ghi cỡ ảnh (clip xoay / ngang / dọc đều đúng, khỏi dò cỡ riêng)
    r = subprocess.run([ffmpeg(), "-v", "error", "-i", p, "-t", str(toi_da / 30.0), "-an", "-vf",
                        "fps=30,scale=%d:-2:flags=area,format=gray" % RONG, "-f", "image2pipe", "-c:v", "pgm", "pipe:1"], capture_output=True, **KW)
    if r.returncode:
        raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-300:])
    b = r.stdout
    dau = b[:40].split(b"\n")
    if len(dau) < 3 or dau[0] != b"P5":
        raise RuntimeError("không đọc được khung")
    w, h = [int(x) for x in dau[1].split()]
    n0 = len(dau[0]) + len(dau[1]) + len(dau[2]) + 3
    buoc = n0 + w * h
    n = len(b) // buoc
    a = np.frombuffer(b[: n * buoc], np.uint8).reshape(n, buoc)[:, n0:].reshape(n, h, w)
    return a.astype(np.float32)


def dich(a, b, win):
    """Dịch (dx, dy) từ ảnh a sang b, dưới điểm ảnh."""
    try:
        import cv2
        (dx, dy), _ = cv2.phaseCorrelate(a, b, win)
        return dx, dy
    except ImportError:
        A, B = np.fft.fft2(a * win), np.fft.fft2(b * win)
        R = A.conj() * B
        R /= np.abs(R) + 1e-9
        c = np.fft.ifft2(R).real
        y, x = np.unravel_index(np.argmax(c), c.shape)
        h, w = c.shape
        return (x - w if x > w // 2 else x), (y - h if y > h // 2 else y)


def do(p):
    t0 = time.time()
    f = doc_khung(p)
    if len(f) < 25:
        return {"trung_vi": None, "p90": None, "khung": int(len(f)), "giay": round(time.time() - t0, 1)}
    win = np.outer(np.hanning(f.shape[1]), np.hanning(f.shape[2])).astype(np.float32)
    tr, traj = [0.0, 0.0], [(0.0, 0.0)]
    for a, b in zip(f, f[1:]):
        dx, dy = dich(a, b, win)
        tr[0] += dx
        tr[1] += dy
        traj.append((tr[0], tr[1]))
    a = np.array(traj)
    k = max(2, int(round(30 * 0.13)))
    sm = np.stack([np.convolve(np.pad(a[:, j], k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid") for j in (0, 1)], 1)
    res = np.hypot(*(a - sm).T) / RONG * 100
    return {"trung_vi": round(float(np.median(res)), 3), "p90": round(float(np.percentile(res, 90)), 3), "khung": int(len(f)),
            "giay": round(time.time() - t0, 1)}


def main():
    if len(sys.argv) < 4 or sys.argv[1] != "do":
        print("LOI=Dùng: chong_rung_may.py do <video> <ra.json>", flush=True)
        sys.exit(2)
    try:
        kq = do(sys.argv[2])
        tam = sys.argv[3] + ".tmp"
        with open(tam, "w", encoding="utf-8") as fh:
            json.dump(kq, fh)
        os.replace(tam, sys.argv[3])
        print("XONG=" + json.dumps(kq), flush=True)
    except Exception as e:  # noqa
        print("LOI=" + str(e)[:300], flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
