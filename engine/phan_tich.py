#!/usr/bin/env python3
"""Phân tích clip cho agent dựng Poly Store.

Dùng:  python3 phan_tich.py <thu_muc_ra> <clip1> [clip2 ...]
       python  phan_tich.py <thu_muc_ra> --danh-sach <W>/clip.txt --them   (bản máy tiệm: danh sách do don.py chuan-bi
               ghi; --them = giữ clip đã phân tích, làm tiếp clip còn lại — ghi phan-tich.json sau mỗi clip)
Ra:    <thu_muc_ra>/phan-tich.json + to-khung-<n>.jpg (tờ khung hình có mốc giây, 1 khung/1,5s)

Mỗi clip: thông số (rộng, cao, fps, độ dài, HDR), đường độ nét/độ chuyển động mỗi 0,5s,
các đoạn nét gợi ý (đủ nét, không rung mạnh, dài ≥ 1,2s), và âm thanh là nhạc hay tiếng thật.
28/10: đọc khung qua ffmpeg 1 lần giải mã (160px xám để đo rung, 480px xám mỗi 0,5s để đo nét) thay cv2 giải mã nguyên cỡ
1 luồng; tờ khung chỉ giải mã khung khóa; 2 clip chạy song song.
"""
import json, os, subprocess, sys
from chung import FFMPEG, FFPROBE, font_drawtext
import numpy as np
import cv2


def ffprobe(p):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries",
         "format=duration:stream=index,codec_type,width,height,r_frame_rate,color_transfer:stream_side_data=rotation",
         "-of", "json", p], capture_output=True, text=True, encoding="utf-8", errors="replace", check=True).stdout
    j = json.loads(out)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v or {}).get("r_frame_rate", "30/1").split("/")
    w, h = (v or {}).get("width"), (v or {}).get("height")
    rot = 0
    for sd in (v or {}).get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    return {
        "rong": w, "cao": h, "fps": round(float(num) / float(den), 3),
        "do_dai": float(j["format"]["duration"]),
        "hdr": (v or {}).get("color_transfer") in ("arib-std-b67", "smpte2084"),
        "hdr_trc": (v or {}).get("color_transfer") if (v or {}).get("color_transfer") in ("arib-std-b67", "smpte2084") else None,
        "co_tieng": a is not None,
    }


LOC_THU_NHO = "fast_bilinear"  # gần cv2 INTER_LINEAR nhất (đã so 3 clip với bản cv2 cũ: rung tay, đoạn nét)


def thang_cv2(p, g0):
    """Thang xám của ffmpeg (6.x hệ thống) -> thang của bản cv2 cũ (cv2 5 dùng FFmpeg 8 riêng: clip HDR sáng hơn ~16).
    Các ngưỡng cũ (sáng 25–235, chuyển động 55, nét ≥ 60) đặt theo thang cv2 -> đọc ĐÚNG 1 khung bằng cv2, khớp tuyến
    tính từng điểm ảnh với khung đầu (g0, xám 480px) -> (a, b): xám_cv2 ≈ a·x + b. Không tin được thì (1, 0)."""
    cap = cv2.VideoCapture(p)
    ok, f = cap.read()
    cap.release()
    if not ok:
        return 1.0, 0.0
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    best = None
    for k in range(4):  # cv2 có thể không xoay khung như ffmpeg
        r = np.rot90(g, k)
        if r.shape[0] * g0.shape[1] != r.shape[1] * g0.shape[0]:
            continue
        r = cv2.resize(np.ascontiguousarray(r), (g0.shape[1], g0.shape[0]), interpolation=cv2.INTER_AREA).astype(float)
        c = np.corrcoef(r.ravel(), g0.ravel().astype(float))[0, 1]
        if best is None or c > best[0]:
            best = (c, r)
    if best is None or not best[0] > 0.9:
        return 1.0, 0.0
    a, b = np.polyfit(g0.ravel().astype(float), best[1].ravel(), 1)
    return (float(a), float(b)) if 0.7 < a < 1.4 and -40 < b < 40 else (1.0, 0.0)


def fps_that(p):
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "json", p],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    try:
        n, d = json.loads(out)["streams"][0]["r_frame_rate"].split("/")
        return float(n) / float(d)
    except (ValueError, KeyError, IndexError, ZeroDivisionError):
        return None


def doc_khung_xam(p, rong, cao, fps, step=0.5, loc=None):
    """MỘT lần giải mã bằng ffmpeg (đa luồng, tự xoay như cv2): (a) mọi khung 160px xám — đo rung; (b) khung thứ n chia hết
    cho round(fps·0,5) (đúng khung bản cv2 cũ lấy), cạnh dài 480px, xám — đo nét / chuyển động / sáng.
    Trả về (mảng [n, h, 160] uint8, mảng [m, h2, w2] uint8, every). Bản cũ: cv2 giải mã nguyên cỡ 1 luồng (68,9s / clip 11s)."""
    import tempfile
    loc = loc or LOC_THU_NHO
    every = max(1, int(round(fps * step)))
    w1, h1 = 160, max(16, int(cao * 160 / rong))
    sc = 480.0 / max(rong, cao)
    w2, h2 = (int(rong * sc), int(cao * sc)) if sc < 1 else (rong, cao)
    fc = (f"[0:v]split=2[a][b];[a]scale={w1}:{h1}:flags={loc},format=gray[s];"
          f"[b]select='not(mod(n\\,{every}))',scale={w2}:{h2}:flags={loc},format=gray[g]")
    with tempfile.TemporaryDirectory() as td:
        g_p = os.path.join(td, "g.raw")
        r = subprocess.run([FFMPEG, "-v", "error", "-i", p, "-filter_complex", fc,
                            "-map", "[s]", "-fps_mode", "passthrough", "-f", "rawvideo", "pipe:1",
                            "-map", "[g]", "-fps_mode", "passthrough", "-f", "rawvideo", g_p], capture_output=True)
        if r.returncode != 0:
            raise RuntimeError("ffmpeg đọc khung lỗi: " + r.stderr.decode("utf-8", "replace")[-500:])
        nho = np.frombuffer(r.stdout, np.uint8)
        g = np.fromfile(g_p, np.uint8)
    return nho[: len(nho) // (w1 * h1) * w1 * h1].reshape(-1, h1, w1), g[: len(g) // (w2 * h2) * w2 * h2].reshape(-1, h2, w2), every


def curves(p, step=0.5, info=None):
    """Mỗi 0,5s: độ nét, độ chuyển động, độ sáng. Kèm độ rung tay: đo dịch khung từng khung (phase correlation, ảnh 160px),
    trừ đường đi đã làm mượt ~0,27s → phần giật còn lại (% bề rộng khung). Lia/đi bộ chủ ý không tính là rung."""
    info = info or ffprobe(p)
    fps = fps_that(p) or info["fps"] or 30  # phân số đầy đủ (59,94005994…) như cv2, để mốc giây trùng bản cũ
    nho, lon, every = doc_khung_xam(p, info["rong"], info["cao"], fps, step)
    win, tr, traj, small_prev = None, [0.0, 0.0], [], None
    for f in nho:
        g160 = f.astype(np.float32)
        if win is None:
            win = cv2.createHanningWindow(g160.shape[::-1], cv2.CV_32F)
        if small_prev is not None:
            (dx, dy), _ = cv2.phaseCorrelate(small_prev, g160, win)
            tr[0] += dx
            tr[1] += dy
        traj.append((tr[0], tr[1]))
        small_prev = g160
    a, b = thang_cv2(p, lon[0]) if len(lon) else (1.0, 0.0)  # giữ thang của các ngưỡng cũ
    prev, rows = None, []
    for k, g in enumerate(lon):
        sharp = float(cv2.Laplacian(g, cv2.CV_64F).var()) * a * a
        motion = 0.0 if prev is None else float(np.mean(cv2.absdiff(g, prev))) * a
        rows.append({"t": round(k * every / fps, 2), "net": round(sharp), "rung": round(motion, 1),
                     "sang": round(a * float(np.mean(g)) + b)})
        prev = g
    shake = None
    if len(traj) > 20:
        a = np.array(traj)
        k = max(2, int(round(fps * 0.13)))
        sm = np.stack([np.convolve(np.pad(a[:, j], k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid") for j in (0, 1)], 1)
        res = np.hypot(*(a - sm).T) / 160 * 100
        shake = {"trung_vi": round(float(np.median(res)), 3), "p90": round(float(np.percentile(res, 90)), 3)}
    return rows, shake


def good_segments(rows, dur, step=0.5, min_len=1.2):
    if not rows:
        return []
    nets = np.array([r["net"] for r in rows], dtype=float)
    thr = max(60.0, float(np.percentile(nets, 35)))
    segs, start = [], None
    for k, r in enumerate(rows):
        ok = r["net"] >= thr and r["rung"] < 55 and 25 < r["sang"] < 235
        if ok and start is None:
            start = r["t"]
        if (not ok or k == len(rows) - 1) and start is not None:
            end = r["t"] if not ok else min(dur, r["t"] + step)
            if end - start >= min_len:
                seg = [x for x in rows if start <= x["t"] < end]
                segs.append({"tu": round(start, 2), "den": round(end, 2),
                             "net_tb": round(float(np.mean([x["net"] for x in seg]))) if seg else 0})
            start = None
    return segs


def audio_kind(p):
    raw = subprocess.run([FFMPEG, "-loglevel", "error", "-i", p, "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True).stdout
    if len(raw) < 32000:
        return {"loai": "khong_co"}
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    hop = 800
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x) - hop, hop)])
    db = 20 * np.log10(rms + 1e-6)
    env = np.maximum(0, np.diff(rms)); env = env - env.mean()
    ac = np.correlate(env, env, "full")[len(env) - 1:]
    lags = np.arange(len(ac)) * 0.05
    m = (lags > 0.3) & (lags < 1.5)
    beat = float(ac[m].max() / ac[0]) if ac[0] > 0 and m.any() else 0.0
    std = float(np.std(db))
    loai = "nhac" if (beat > 0.3 and std < 6) else "tieng_that"
    # đoạn im (ngưỡng thích nghi theo nền ồn của chính clip, không dùng -45 dB cố định): ≥ 0,8s
    p10, p90 = np.percentile(db, 10), np.percentile(db, 90)
    thr = p10 + 0.3 * (p90 - p10)
    im, start = [], None
    for i, v in enumerate(db):
        q = v < thr
        if q and start is None:
            start = i
        if (not q or i == len(db) - 1) and start is not None:
            a, b = start * 0.05, (i if not q else i + 1) * 0.05
            if b - a >= 0.8:
                im.append([round(a, 2), round(b, 2)])
            start = None
    return {"loai": loai, "do_lon_tb_db": round(float(np.mean(db)), 1), "dao_dong_db": round(std, 1), "nhip": round(beat, 2),
            "nguong_im_db": round(float(thr), 1), "doan_im": im}


def contact_sheet(p, out, dur):
    n = int(dur // 1.5) + 1
    cols = 8
    rows = max(1, -(-n // cols))
    # chỉ giải mã khung khóa (-skip_frame nokey, iPhone ~0,93s/khung khóa: nhanh ~10 lần); ghi giây TRƯỚC fps=1/1.5 nên
    # mốc trên ảnh là giây thật của khung khóa đó (lệch lưới 1,5s tối đa ~0,5s)
    vf = (f"scale=180:-2,drawtext={font_drawtext()}text='%{{eif\\:t\\:d}}.%{{eif\\:mod(t*10\\,10)\\:d}}s':x=4:y=4:fontsize=18:"
          f"fontcolor=yellow:box=1:boxcolor=black@0.6,fps=1/1.5,tile={cols}x{rows}")
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-skip_frame", "nokey", "-i", p, "-vf", vf, "-frames:v", "1", out], check=True)
    if not os.path.isfile(out):  # bản máy tiệm: clip ít khung khóa (GOP dài, HEVC xuất lại…) -> nokey không ra khung nào: giải mã đủ
        subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", p, "-vf", vf, "-frames:v", "1", out], check=True)


def mot_clip(k, p, outdir):
    info = ffprobe(p)
    rows, shake = curves(p, info=info)
    info.update({
        "file": p,
        # rung tay (% khung, trung vị): ~0,18 đã ổn định, ~0,32 cầm tay đi bộ; > 0,25 nên bật on_dinh khi dựng máy chủ
        "rung_tay": shake,
        "nen_on_dinh": bool(shake) and shake["trung_vi"] > 0.25,
        "doan_net": good_segments(rows, info["do_dai"]),
        "am_thanh": audio_kind(p) if info["co_tieng"] else {"loai": "khong_co"},
        "duong_cong": rows,
        "to_khung": os.path.join(outdir, f"to-khung-{k}.jpg"),
    })
    contact_sheet(p, info["to_khung"], info["do_dai"])
    return info


def main():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    args = sys.argv[1:]
    clips = []
    them = "--them" in args  # bản máy tiệm: giữ kết quả cũ, chỉ phân tích clip chưa có (chạy lại sau khi bị ngắt)
    args = [a for a in args if a != "--them"]
    if "--danh-sach" in args:  # bản máy tiệm: danh sách clip (mỗi dòng 1 đường dẫn) do don.py chuan-bi ghi ra
        i = args.index("--danh-sach")
        with open(args[i + 1], encoding="utf-8-sig") as f:
            clips += [x.strip() for x in f if x.strip()]
        args = args[:i] + args[i + 2:]
    outdir, clips = args[0], args[1:] + clips
    thieu = [c for c in clips if not os.path.isfile(c)]
    if not clips or thieu:
        raise SystemExit("Không có clip nào." if not clips else "Không thấy clip: " + "; ".join(thieu))
    os.makedirs(outdir, exist_ok=True)
    ra = os.path.join(outdir, "phan-tich.json")
    res = []
    if them and os.path.exists(ra):
        with open(ra, encoding="utf-8") as f:
            res = [x for x in json.load(f) if x.get("file") in clips and os.path.exists(x.get("to_khung") or "")]
    xong = {x["file"] for x in res}
    so = [int(x["to_khung"].rsplit("-", 1)[-1].split(".")[0]) for x in res if x.get("to_khung")]
    viec = [c for c in dict.fromkeys(clips) if c not in xong]
    thu_tu = {c: i for i, c in enumerate(clips)}

    def ghi():  # ghi sau MỖI clip: bị ngắt giữa chừng thì chạy lại với --them làm tiếp
        res.sort(key=lambda x: thu_tu.get(x["file"], -1))
        tam = ra + ".tmp"
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        os.replace(tam, ra)

    with ThreadPoolExecutor(2) as ex:  # 2 clip song song (ffmpeg giải mã đa luồng + numpy/cv2 nhả GIL)
        fs = [ex.submit(mot_clip, max(so or [0]) + i + 1, c, outdir) for i, c in enumerate(viec)]
        for fu in as_completed(fs):
            r = fu.result()
            res.append(r)
            ghi()
            print(json.dumps({k: r[k] for k in ("file", "rong", "cao", "fps", "do_dai", "hdr", "rung_tay", "nen_on_dinh", "am_thanh",
                                                "doan_net", "to_khung")}, ensure_ascii=False), flush=True)
    ghi()
    if xong:
        print(json.dumps({"giu_tu_lan_truoc": len(xong), "phan_tich_moi": len(viec)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
