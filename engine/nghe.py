#!/usr/bin/env python3
"""Nghe lời nói tiếng Việt trong clip -> chữ + giờ từng từ (để làm phụ đề, chọn cảnh theo lời).

Dùng:  python3 nghe.py <thu_muc_mo_hinh> <ra.json> <clip...>
       python  nghe.py <thu_muc_mo_hinh> <ra.json> --danh-sach <W>/clip.txt   (bản máy tiệm)
Mô hình: sherpa-onnx zipformer tiếng Việt (GitHub k2-fsa/sherpa-onnx, release "asr-models",
         sherpa-onnx-zipformer-vi-int8-2025-04-20.tar.bz2, ~60MB) + `pip install sherpa-onnx`.
Ra:    {clip: {"do_dai": s, "cau": [{"t0", "t1", "chu", "tu": [[từ, t0, t1], ...]}]}}
Cắt đoạn theo chỗ im (silencedetect) để mỗi đoạn ≤ 20s; máy 2 nhân nghe khoảng 0,2–0,4 lần thời lượng clip.
Kết quả là bản nháp: tên máy, số, tiếng lóng hay sai — agent phải đọc lại, sửa trước khi dùng làm phụ đề.
"""
import json, os, re, subprocess, sys, tempfile, wave
from chung import FFMPEG

import numpy as np
import sherpa_onnx


def recognizer(mdir):
    f = lambda pat: next(os.path.join(mdir, x) for x in sorted(os.listdir(mdir)) if re.match(pat, x))
    return sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f(r"encoder.*\.onnx$"), decoder=f(r"decoder.*\.onnx$"), joiner=f(r"joiner.*\.onnx$"),
        tokens=os.path.join(mdir, "tokens.txt"), num_threads=2, decoding_method="greedy_search")


def doc_wav(clip, tmp):
    w = os.path.join(tmp, "a.wav")
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", clip, "-vn", "-ac", "1", "-ar", "16000",
                    "-af", "highpass=f=80", "-c:a", "pcm_s16le", w], check=True)
    with wave.open(w) as f:
        a = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return a, w


def cho_im(w, dur):
    e = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", w, "-af", "silencedetect=n=-35dB:d=0.35", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", e)]
    en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", e)]
    return [((a + b) / 2) for a, b in zip(st, en)]


def cat_doan(dur, moc, toi_da=20.0):
    out, a = [], 0.0
    while a < dur - 0.05:
        cand = [m for m in moc if a + 3 < m <= a + toi_da]
        b = cand[-1] if cand else min(dur, a + toi_da)
        out.append((a, b))
        a = b
    return out


def main():
    args = sys.argv[1:]
    them = []
    if "--danh-sach" in args:  # bản máy tiệm: danh sách clip (mỗi dòng 1 đường dẫn) do don.py chuan-bi ghi ra
        i = args.index("--danh-sach")
        with open(args[i + 1], encoding="utf-8-sig") as f:
            them = [x.strip() for x in f if x.strip()]
        args = args[:i] + args[i + 2:]
    mdir, ra, clips = args[0], args[1], args[2:] + them
    rec = recognizer(mdir)
    kq = {}
    for clip in clips:
        with tempfile.TemporaryDirectory() as tmp:
            a, w = doc_wav(clip, tmp)
            dur = len(a) / 16000
            cau = []
            for t0, t1 in cat_doan(dur, cho_im(w, dur)):
                s = rec.create_stream()
                s.accept_waveform(16000, a[int(t0 * 16000):int(t1 * 16000)])
                rec.decode_stream(s)
                r = s.result
                tu, cur = [], None
                for tok, ts in zip(r.tokens, r.timestamps):
                    t = round(t0 + ts, 2)
                    if tok.startswith(("▁", " ")) or cur is None:  # sherpa trả "▁" hoặc dấu cách đầu từ
                        if cur:
                            tu.append(cur)
                        cur = [tok.lstrip("▁ "), t, t + 0.2]
                    else:
                        cur[0] += tok
                        cur[2] = t + 0.2
                if cur and cur[0]:
                    tu.append(cur)
                tu = [[x[0].lower(), x[1], round(x[2], 2)] for x in tu if x[0]]
                for i in range(len(tu) - 1):  # từ kết thúc khi từ sau bắt đầu (nếu sát nhau)
                    tu[i][2] = round(min(tu[i][2] + 0.15, tu[i + 1][1]), 2)
                if tu:
                    cau.append({"t0": tu[0][1], "t1": tu[-1][2], "chu": " ".join(x[0] for x in tu), "tu": tu})
            kq[os.path.basename(clip)] = {"do_dai": round(dur, 2), "cau": cau}
            print(os.path.basename(clip), round(dur, 1), "s:", " / ".join(c["chu"] for c in cau)[:300], flush=True)
    json.dump(kq, open(ra, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
