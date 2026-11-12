# -*- coding: utf-8 -*-
"""VÍ DỤ r37: video 1080x1920 ~16 s ghép clip máy thật (không mặt người), cắt đúng nhịp nhạc "Drop điện tử" (128 BPM, drop ở cảnh game),
gắn hiệu ứng mới của kho ở chỗ cắt / chữ hiện; góc dưới hiện tên tiếng đang kêu để anh nghe trong ngữ cảnh. Chỉ để duyệt, không vào app.
Dùng: python dev/vi_du_am_thanh_r37.py <kho> <thư mục clip> <file ra.mp4> <thư mục tạm>"""
import json, os, subprocess, sys, wave
import numpy as np

KHO, CLIP, RA, TAM = sys.argv[1:5]
FONT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "engine", "fonts", "BeVietnamPro-ExtraBold.ttf")
SR = 48000; B = 60 / 128.0; FPS = 30
XANH, VANG = "0x074D3A", "0xFFD600"
HDR = ("setparams=color_primaries=bt2020:color_trc=arib-std-b67:colorspace=bt2020nc:range=tv,zscale=t=linear:npl=100,format=gbrpf32le,"
       "zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")

# cảnh: (file clip, giây bắt đầu trong clip, số phách)  — 1 phách = 0,46875 s
CANH = [("IMG_4409.MOV", 0.3, 4), ("IMG_4409.MOV", 13.6, 4), ("IMG_4409.MOV", 30.2, 4), ("IMG_4409.MOV", 21.4, 2),
        ("IMG_4413.MOV", 8.5, 4), ("IMG_4414.MOV", 2.5, 4), ("IMG_4409.MOV", 8.0, 4), ("IMG_4409.MOV", 25.6, 4)]
KET = 4 * B   # thẻ kết
# tiếng: (giây trên video = chỗ "chạm", file trong kho, nhãn hiện)
TIENG = [(0.30, "pop-bat.wav"), (4 * B, "vut-manh.wav"), (8 * B, "quat-gio.wav"), (8 * B + 0.25, "go-phim-nhanh.wav"),
         (14 * B, "hut-vao.wav"), (14 * B, "bum.wav"), (18 * B, "glitch-ngan.wav"), (22 * B, "zoom-toi.wav"), (22 * B + 0.55, "ting-gia.wav"),
         (26 * B + 0.35, "cham-man-hinh.wav"), (26 * B + 0.9, "ket-tien.wav"), (30 * B, "logo-sang.wav")]
CHU = [(0.30, 4 * B - 0.1, "ÂM THANH MỚI\nPOLY CUT"), (8 * B + 0.25, 12 * B, "GÕ PHÍM ÊM"), (14 * B, 18 * B, "TEST GAME"),
       (22 * B + 0.55, 26 * B, "NHẮN TIN HỎI GIÁ"), (26 * B + 0.9, 30 * B, "CHỐT ĐƠN")]
NHAC, NHAC_TU = "poly-drop-dien-tu.mp3", 15.0 - 14 * B   # drop của bài (15,0 s) rơi đúng phách 14 = cảnh game


def doc(p, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").reshape(-1, 2).astype(np.float64)


def esc(p):
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def main():
    os.makedirs(TAM, exist_ok=True)
    meta = json.load(open(os.path.join(KHO, "am-thanh.json"), encoding="utf-8"))["ds"]
    T = sum(c[2] for c in CANH) * B + KET
    # ---- tiếng: nhạc −7 dB, hiệu ứng 70% (như bộ dựng), đặt "dinh" của mỗi tiếng vào đúng giây
    n = int((T + 0.5) * SR); mix = np.zeros((n, 2))
    m = doc(os.path.join(KHO, "nhac", NHAC))[int(NHAC_TU * SR):][:n]
    e = np.ones(len(m)); k = int(1.5 * SR); e[-k:] = np.linspace(1, 0, k); mix[:len(m)] += m * e[:, None] * 10 ** (-7 / 20)
    nhan = []
    for t, f in TIENG:
        x = doc(os.path.join(KHO, "am-thanh", f)); a = int(round((t - meta[f]["dinh"]) * SR))
        if a < 0:
            x = x[-a:]; a = 0
        b = min(n, a + len(x)); mix[a:b] += x[: b - a] * 0.7
        nhan.append((t, meta[f]["ten"]))
    w = os.path.join(TAM, "tron.wav")
    with wave.open(w, "wb") as fo:
        fo.setnchannels(2); fo.setsampwidth(2); fo.setframerate(SR)
        fo.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", w, "-af", "loudnorm=I=-14:TP=-1.5:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    I = float(json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])["input_i"])
    # ---- hình: mỗi cảnh HDR -> SDR, 1080x1920, 30 hình/s; nối; chữ + nhãn tiếng
    vao, f_ = [], []
    for i, (c, s, ph) in enumerate(CANH):
        vao += ["-ss", "%.3f" % s, "-t", "%.3f" % (ph * B + 0.1), "-i", os.path.join(CLIP, c)]
        f_.append(f"[{i}:v]{HDR},scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps={FPS},setsar=1,"
                  f"trim=duration={ph * B:.5f},setpts=PTS-STARTPTS[c{i}]")
    k = len(CANH)
    f_.append(f"color=c={XANH}:s=1080x1920:r={FPS}:d={KET:.5f},format=yuv420p,setsar=1[c{k}]")
    f_.append("".join(f"[c{i}]" for i in range(k + 1)) + f"concat=n={k + 1}:v=1:a=0[v0]")
    ve, j = [], 0
    for a, b, txt in CHU:
        p = os.path.join(TAM, f"chu{j}.txt"); open(p, "w", encoding="utf-8").write(txt); j += 1
        ve.append(f"drawtext=fontfile='{esc(FONT)}':textfile='{esc(p)}':fontsize=84:fontcolor={VANG}:line_spacing=14:box=1:boxcolor={XANH}@0.92:"
                  f"boxborderw=34:x=(w-text_w)/2:y=300:enable='between(t,{a:.3f},{b:.3f})'")
    hang = []   # nhãn trùng giờ thì xếp hàng trên nhau, không đè chữ
    for t, ten in sorted(nhan):
        a, b = max(0, t - 0.15), t + 0.95
        r = next(r for r in range(9) if all(not (a < b2 and a2 < b) for a2, b2, r2 in hang if r2 == r)); hang.append((a, b, r))
        p = os.path.join(TAM, f"chu{j}.txt"); open(p, "w", encoding="utf-8").write("ÂM: " + ten.upper()); j += 1
        ve.append(f"drawtext=fontfile='{esc(FONT)}':textfile='{esc(p)}':fontsize=44:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=18:"
                  f"x=60:y=h-330-{r * 92}:enable='between(t,{a:.3f},{b:.3f})'")
    p = os.path.join(TAM, f"chu{j}.txt"); open(p, "w", encoding="utf-8").write("POLY STORE")
    ve.append(f"drawtext=fontfile='{esc(FONT)}':textfile='{esc(p)}':fontsize=130:fontcolor={VANG}:x=(w-text_w)/2:y=(h-text_h)/2:"
              f"enable='gte(t,{T - KET:.3f})'")
    f_.append("[v0]" + ",".join(ve) + ",format=yuv420p[v]")
    af = f"volume={-14 - I:.2f}dB,alimiter=limit=0.84:level=false:latency=1,aresample=48000"
    cmd = ["ffmpeg", "-v", "error", "-y"] + vao + ["-i", w, "-filter_complex", ";".join(f_), "-map", "[v]", "-map", f"{k}:a", "-af", af,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-colorspace", "bt709", "-c:a", "aac", "-b:a", "192k", "-t", f"{T:.3f}", "-movflags", "+faststart", RA]
    subprocess.run(cmd, check=True)
    print(RA, round(T, 2), "giây;", len(nhan), "tiếng")


if __name__ == "__main__":
    main()
