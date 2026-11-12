#!/usr/bin/env python3
"""Tự đo lỗi bản dựng trước khi đưa agent duyệt xem.

Dùng:  python3 duyet.py <video.mp4> <dong-thoi-gian.json> <thu_muc_ra> [lop-chu.json]
Ra:    <thu_muc_ra>/duyet.json + to-duyet.jpg (1 khung/giây có mốc giây) + khung-dau.jpg (0,0s · 0,5s · 1,0s · 1,5s)
       + khung-chu.jpg (nếu có lop-chu.json: tối đa 24 khung rải đều CẢ video — ưu tiên hook / nhãn / sticker / thẻ giá /
       thẻ kết, phần còn lại lấy câu phụ đề lấp chỗ trống; để soát chữ, vùng an toàn)
Âm: độ lớn -14 ±1 LUFS, đỉnh thật ≤ -1 dBTP, chỗ im lặng đo theo ngưỡng thích nghi (nền ồn của chính video).
29/10 (anh: "âm thanh còn bị vấp"): soát VẤP TIẾNG ở từng chỗ cắt khi video dùng tiếng nói thật (không giọng đọc) —
so độ lớn 150 ms trước / sau chỗ cắt của bản xuất với cùng chỗ trong file nguồn: 2 phần liền của cùng câu mà bản xuất
nhảy > 2 dB (nguồn không nhảy) = mức âm từng clip lệch nhau; chỗ cắt giữa 2 đoạn quay khác mà cả hai phía đang nói = cắt
giữa câu.

Giải mã MỘT lượt (28/10): hình 1 lần (blackdetect + freezedetect + tờ khung + khung đầu), tiếng 1 lần (volumedetect +
ebur128 + PCM để tự tìm chỗ im bằng numpy, đúng luật silencedetect: mọi kênh |mẫu| < ngưỡng liền ≥ 1,2s).
Khung chữ lấy bằng seek riêng từng mốc (nhanh, không giải mã cả video). Bản cũ giải mã hình 3 lần + tiếng 3 lần (60,6s
trên v8 80,5s) — số đo không đổi.
"""
import json, os, re, subprocess, sys
from chung import FFMPEG, FFPROBE, font_drawtext
from concurrent.futures import ThreadPoolExecutor

import numpy as np

TOI_DA_KHUNG_CHU = 24
IM_GIAY = 1.2


def ff(args):
    return subprocess.run([FFMPEG, "-hide_banner", "-nostats"] + args, capture_output=True, text=True, encoding="utf-8", errors="replace").stderr


def mot_luot(v, dur, outd, co_tieng):
    """Một lần giải mã cả file. Trả về (stderr của ffmpeg, PCM float32 [n, kênh] hoặc None, tần số mẫu)."""
    sheet, head = os.path.join(outd, "to-duyet.jpg"), os.path.join(outd, "khung-dau.jpg")
    cols = 8
    rows = max(1, -(-int(dur + 1) // cols))
    fc = ("[0:v]split=4[v1][v2][v3][v4];"
          "[v1]blackdetect=d=0.06:pix_th=0.08,nullsink;"
          "[v2]freezedetect=n=0.003:d=1.2,nullsink;"
          f"[v3]fps=1,scale=160:-2,drawtext={font_drawtext()}text='%{{eif\\:t\\:d}}s':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:"
          f"boxcolor=black@0.6,tile={cols}x{rows}[to];"
          "[v4]trim=end=2,fps=2,scale=270:-2,tile=4x1[dau]")
    out = ["-map", "[to]", "-frames:v", "1", "-y", sheet, "-map", "[dau]", "-frames:v", "1", "-y", head]
    ch = sr = None
    if co_tieng:
        ch, sr = co_tieng
        fc += ";[0:a]asplit=3[a1][a2][a3];[a1]volumedetect,anullsink;[a2]ebur128=framelog=quiet:peak=true,anullsink;[a3]anull[pcm]"
        out += ["-map", "[pcm]", "-c:a", "pcm_f32le", "-f", "f32le", "pipe:1"]
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", v, "-filter_complex", fc] + out, capture_output=True)
    e = r.stderr.decode("utf-8", "replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg (một lượt) lỗi:\n" + e[-1500:])
    pcm = np.frombuffer(r.stdout, np.float32).reshape(-1, ch) if co_tieng and r.stdout else None
    return e, pcm, sr


def _nguon_pcm(p, sr, _cache={}):
    if p not in _cache:
        r = subprocess.run([FFMPEG, "-v", "error", "-i", p, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                           capture_output=True)
        _cache[p] = np.frombuffer(r.stdout, np.float32).astype(np.float64) if r.returncode == 0 and r.stdout else None
    return _cache[p]


def vi_tri_canh(tl):
    """Giờ bắt đầu từng cảnh trên bản xuất: Premiere nối tiếp theo khung; máy chủ trừ phần chồng chuyển cảnh."""
    fps, o, out = float(tl.get("fps") or 30), 0.0, []
    for s in tl["shots"]:
        if tl.get("duong") == "premiere":
            out.append(o)
            o += (int(round(s["den"] * fps)) - int(round(s["tu"] * fps))) / fps
        else:
            o -= s.get("chuyen", 0.0)
            out.append(o)
            o += s["dur"]
    return out


def vap_tieng(pcm, sr, tl):
    """Soát vấp tiếng ở chỗ cắt (chỉ video tiếng nói thật, không giọng đọc đè). Trả [câu lưu ý]."""
    if pcm is None or tl.get("giong"):
        return []
    x = pcm.mean(1) if pcm.ndim == 2 else pcm
    fps = float(tl.get("fps") or 30)
    db = lambda a: 10 * np.log10(float(np.mean(a ** 2)) + 1e-12) if len(a) else -120.0
    w = lambda arr, a, b: arr[max(0, int(a * sr)):max(0, int(b * sr))]
    pos, shots, out = vi_tri_canh(tl), tl["shots"], []
    for i in range(1, len(shots)):
        s0, s1, c = shots[i - 1], shots[i], pos[i]
        if s1.get("chuyen") or s0.get("the_hoi") or s1.get("the_hoi") or s0.get("dong_bang"):
            continue
        p0 = ((tl.get("nguon") or {}).get(s0["file"]) or {}).get("local")
        p1 = ((tl.get("nguon") or {}).get(s1["file"]) or {}).get("local")
        y0, y1 = (_nguon_pcm(p0, sr) if p0 and os.path.exists(p0) else None), (_nguon_pcm(p1, sr) if p1 and os.path.exists(p1) else None)
        if y0 is None or y1 is None:
            continue
        nen = float(np.percentile(10 * np.log10(np.convolve(y0 ** 2, np.ones(4800) / 4800, "valid")[::480] + 1e-12), 10))
        lien = s0["file"] == s1["file"] and abs(s1["tu"] - s0["den"]) <= 1.0 / fps + 1e-3
        nb, na = db(w(y0, s0["den"] - 0.18, s0["den"] - 0.03)), db(w(y1, s1["tu"] + 0.03, s1["tu"] + 0.18))
        if lien:
            if nb < nen + 10 or na < nen + 10:
                continue
            xb, xa = db(w(x, c - 0.18, c - 0.03)), db(w(x, c + 0.03, c + 0.18))
            nhay = (xa - xb) - (na - nb)
            if abs(nhay) > 2.0:
                out.append(f"Vấp tiếng {c:.2f}s: giữa 1 câu nói (2 phần liền của cảnh {s1['canh'] + 1}) tiếng nhảy {nhay:+.1f} dB "
                           "— chỉnh âm theo đoạn liền (am_tung_clip.py mặc định từ 29/10)")
        elif nb > nen + 18 and na > nen + 18:
            out.append(f"Cắt giữa tiếng nói ở {c:.2f}s (cuối cảnh {s0['canh'] + 1} / đầu cảnh {s1['canh'] + 1} đều đang nói) "
                       "— dời tu / den vào khe lặng (ke_hoach.py có gợi ý)")
    return out


def tim_im(pcm, sr, nguong_db, d=IM_GIAY):
    """Giống silencedetect (mono=0): khung im khi MỌI kênh có |mẫu| < ngưỡng; im liền ≥ d giây. Trả [(bắt đầu, kết thúc)]."""
    if pcm is None or not len(pcm):
        return []
    im = np.all(np.abs(pcm) < 10 ** (nguong_db / 20.0), axis=1)
    dx = np.diff(np.concatenate(([0], im.astype(np.int8), [0])))
    st, en = np.flatnonzero(dx == 1), np.flatnonzero(dx == -1)
    can = int(round(d * sr))
    return [(a / sr, b / sr) for a, b in zip(st, en) if b - a >= can]


def chon_moc_chu(cands, dur, toi_da=TOI_DA_KHUNG_CHU):
    """cands: [(t, ten, uu_tien)]. Lấy hết mốc ưu tiên (hook, nhãn, sticker, thẻ giá, thẻ kết...; quá nhiều thì rải đều),
    chỗ còn lại lấy câu phụ đề xa các mốc đã chọn nhất (lấp chỗ trống) để khung phủ CẢ video. Bỏ mốc cách mốc khác < 0,3s."""
    uu = sorted(c for c in cands if c[2])
    con = sorted(c for c in cands if not c[2])
    if len(uu) > toi_da:
        uu = [uu[round(i * (len(uu) - 1) / (toi_da - 1))] for i in range(toi_da)] if toi_da > 1 else uu[:1]
    chon = []
    for c in uu:
        if not chon or c[0] - chon[-1][0] >= 0.3:
            chon.append(c)
        else:  # 2 lớp hiện gần nhau: lấy mốc SAU (lúc đó cả 2 lớp đã hiện), ghi cả 2 tên
            chon[-1] = (c[0], chon[-1][1] + " + " + c[1], True)
    while len(chon) < toi_da and con:
        moc = [0.0, dur] + [c[0] for c in chon]
        xa = lambda c: min(abs(c[0] - m) for m in moc)
        best = max(con, key=xa)
        con.remove(best)
        if xa(best) >= 0.3:
            chon.append(best)
    return sorted(chon)


def khung_chu(v, outd, moc):
    def mot(i_t):
        i, t = i_t
        f = os.path.join(outd, f"_c{i:02d}.jpg")
        subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", v, "-frames:v", "1", "-vf",
                        f"scale=270:-2,drawtext={font_drawtext()}text='{t:.1f}s':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6", f],
                       check=True)
        return f
    with ThreadPoolExecutor(3) as ex:
        parts = list(ex.map(mot, enumerate(t for t, _ in moc)))
    n = len(parts)
    cols = min(4, n) if n <= 16 else 6
    rows = -(-n // cols)
    cs = os.path.join(outd, "khung-chu.jpg")
    subprocess.run([FFMPEG, "-loglevel", "error", "-y", "-i", os.path.join(outd, "_c%02d.jpg"), "-vf",
                    f"tile={cols}x{rows}", "-frames:v", "1", cs], check=True)
    for f in parts:
        os.remove(f)
    return cs


def main():
    v, tlp, outd = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outd, exist_ok=True)
    tl = json.load(open(tlp, encoding="utf-8"))
    # đường Premiere: chuyển cảnh không làm timeline ngắn lại (clip nối tiếp) — xem ke_hoach.py
    chong = 0.0 if tl.get("duong") == "premiere" else 1.0
    pr = json.loads(subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                                    "format=duration:stream=codec_type,width,height,r_frame_rate,sample_rate,channels",
                                    "-of", "json", v], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout)
    vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
    au = next((s for s in pr["streams"] if s["codec_type"] == "audio"), None)
    dur = float(pr["format"]["duration"])
    n, d = vs["r_frame_rate"].split("/")
    res = {"file": v, "do_dai": round(dur, 2), "khung": [vs["width"], vs["height"]], "fps": round(float(n) / float(d), 2), "loi": [], "luu_y": []}
    if abs(dur - tl["T"]) > 0.3:
        res["loi"].append(f"Độ dài {dur:.2f}s khác dòng thời gian {tl['T']:.2f}s")
    gu = {}
    try:
        gu = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kieu_dung.json"), encoding="utf-8")).get("gu_kenh", {})
    except (OSError, ValueError):
        pass
    nen = gu.get("do_dai_nen", [20, 50])
    toi_da = gu.get("do_dai_toi_da", 60)
    if dur > toi_da:
        res["luu_y"].append(f"Độ dài {dur:.0f}s quá {toi_da}s (anh chốt 28/10: khoảng 1 phút 30) — cắt bớt")
    elif not (nen[0] - 5 <= dur <= nen[1] + 5):
        res["luu_y"].append(f"Độ dài {dur:.0f}s ngoài khoảng gu kênh {nen[0]}–{nen[1]}s")
    # một cảnh nguồn chạy liền quá lâu (gu kênh: video 1 góc máy cả phút đều thấp view)
    lien = gu.get("canh_lien_toi_da", 8.0)
    dai = {}
    for s in tl["shots"]:
        if s["canh"] >= 0:
            dai[s["canh"]] = dai.get(s["canh"], 0.0) + s["dur"] - chong * s.get("chuyen", 0.0)
    for c, d in sorted(dai.items()):
        if d > lien + 0.05:
            res["luu_y"].append(f"Cảnh {c + 1} chạy liền {d:.1f}s từ một đoạn quay (gu kênh ≤ {lien:.0f}s) — chèn cảnh khác hoặc cắt bớt")
    co_tieng = (int(au.get("channels") or 2), int(au.get("sample_rate") or 48000)) if au else None
    e, pcm, sr = mot_luot(v, dur, outd, co_tieng)
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", e)
    for a, b in blacks:
        res["loi"].append(f"Khung đen {a}–{b}s")
    allowed = []
    t = 0.0
    for s in tl["shots"]:
        if s.get("dong_bang") or s.get("the_hoi"):
            allowed.append((t - 0.1, t + (s.get("dong_bang") or s.get("the_hoi")) + 0.2))
        t += s["dur"] - chong * s.get("chuyen", 0)
    for st, en in re.findall(r"freeze_start: ([\d.]+).*?freeze_end: ([\d.]+)", e, re.S):
        st, en = float(st), float(en)
        if not any(a <= st and en <= b for a, b in allowed):
            res["luu_y"].append(f"Hình đứng yên {st:.1f}–{en:.1f}s")
    m = re.search(r"mean_volume: (-?[\d.]+) dB", e)
    nguong = max(-55.0, min(-30.0, float(m.group(1)) - 20)) if m else -45.0
    res["nguong_im_db"] = round(nguong, 1)
    for st, en in tim_im(pcm, sr, nguong):
        res["luu_y"].append(f"Im lặng {st:.1f}–{en:.1f}s (ngưỡng {nguong:.0f} dB)")
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", e)
    if m:
        res["loudness_lufs"] = float(m.group(1))
        if not (-17 <= res["loudness_lufs"] <= -11):
            res["loi"].append(f"Độ lớn {res['loudness_lufs']} LUFS, lệch xa −14 (chỉnh âm rồi xuất lại)")
        elif not (-15 <= res["loudness_lufs"] <= -13):
            res["luu_y"].append(f"Độ lớn {res['loudness_lufs']} LUFS (đích −14 ±1)")
    vap = vap_tieng(pcm, sr, tl) if pcm is not None else []
    res["vap_tieng"] = len(vap)
    res["luu_y"] += vap
    m = re.search(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf) dBFS", e)
    if m and m.group(1) != "-inf":
        res["dinh_that_dbtp"] = float(m.group(1))
        if res["dinh_that_dbtp"] > -1.0:
            res["luu_y"].append(f"Đỉnh thật {res['dinh_that_dbtp']} dBTP (nên ≤ −1, TikTok nén lại dễ rè)")
    W, H = tl["khung"]
    if [vs["width"], vs["height"]] != [W, H] and [vs["width"] * 2, vs["height"] * 2] != [W, H]:
        res["loi"].append(f"Khung {vs['width']}x{vs['height']} khác {W}x{H}")
    res["to_duyet"], res["khung_dau"] = os.path.join(outd, "to-duyet.jpg"), os.path.join(outd, "khung-dau.jpg")
    if len(sys.argv) > 4 and os.path.exists(sys.argv[4]):
        lopj = json.load(open(sys.argv[4], encoding="utf-8"))
        hook = [l for l in lopj.get("lop", []) if l["ten"] == "hook.png"]
        cham = gu.get("hook_hien_cham_nhat", 0.3)
        co_chu_dau = any(l["ten"] != "brand.png" and l["t0"] <= cham for l in lopj.get("lop", [])) or \
            any(sd["t0"] <= cham for sd in (tl.get("phu_de") or []))
        if not hook and not co_chu_dau:
            res["luu_y"].append(f"Không có chữ nào hiện trong {cham}s đầu (gu kênh: hook chữ từ khung đầu)")
        elif hook and hook[0]["t0"] > cham:
            res["loi"].append(f"Chữ hook hiện lúc {hook[0]['t0']}s, chậm hơn {cham}s (gu kênh: chữ có từ khung đầu)")
        cands = []
        for l in lopj.get("lop", []):
            if l["ten"] == "brand.png" or (lopj.get("ass") and l["ten"].startswith("phu-de-")):
                continue  # phụ đề ASS thay cho PNG phụ đề khi dựng máy chủ
            if l["t0"] >= dur - 0.05:
                res["loi"].append(f"Lớp {l['ten']} hiện lúc {l['t0']}s, sau khi video hết ({dur:.2f}s)")
                continue
            cands.append((min(dur - 0.05, l["t0"] + 0.15), l["ten"], not l["ten"].startswith("phu-de-")))
        if lopj.get("ass"):
            for i, sd in enumerate(tl.get("phu_de") or []):
                if sd["t0"] < dur - 0.05:
                    cands.append((min(dur - 0.05, sd["t0"] + 0.3), f"phụ đề {i + 1}", False))
        moc = [(t, ten) for t, ten, _ in chon_moc_chu(cands, dur)]
        if moc:
            res["khung_chu"] = khung_chu(v, outd, moc)
            res["khung_chu_moc"] = [[round(t, 2), ten] for t, ten in moc]
    res["dat"] = not res["loi"]
    json.dump(res, open(os.path.join(outd, "duyet.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
