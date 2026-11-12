#!/usr/bin/env python3
"""Dựng video trên máy chủ Claude (ffmpeg) từ dong-thoi-gian.json + lop-chu.json.

Dùng:  python3 dung_may_chu.py dong-thoi-gian.json lop-chu.json <file_ra.mp4> [--nhap] [--phu-de-png]
--nhap:       bản xem nhanh 540x960, CRF 26 (để duyệt trước khi dựng bản đẹp).
--phu-de-png: dùng phụ đề PNG (như Premiere) thay vì phụ đề ASS tô từng từ.

Hình: zoom/lia dưới điểm ảnh (perspective, nội suy cubic) có easing — không giật như zoompan;
      nguồn HDR (HLG/PQ của iPhone) được tone-map về SDR; nguồn/cảnh có "on_dinh": true thì chống rung (vidstab 2 lượt).
Tiếng: khử ồn nhẹ tiếng phòng (highpass + afftdn, bỏ qua nếu nguồn là nhạc), nền nhún theo giọng đọc (sidechain),
       nén nhẹ + loudnorm 2 lượt về -14 LUFS, đỉnh -1,5 dBTP.
       Nhạc nền (tl["nhac"], 4/11): lặp nếu ngắn, mờ đầu / cuối, tự hạ khi có giọng AI / người nói (tron_them, nhac_dau_vao).
       Tiếng tách (tl["am_tach"], 4/11): khối tiếng clip đặt riêng trên video (J/L cut), trộn vào tiếng clip (am_tach_ds).
Chữ:  lớp PNG 1 khung (overlay tự giữ khung cuối) + phụ đề ASS (libass) nếu lop-chu.json có "ass".
"""
import json, os, re, shutil, subprocess, sys, tempfile
from chung import FFMPEG, FFPROBE, loc
import ma_hoa   # 3/11: mã hoá bằng card đồ hoạ nếu có, lỗi thì tự làm lại bằng CPU (POLY_MA_HOA=cpu để tắt)

MAU = {"trung_tinh": None, "am_nhe": "eq=saturation=1.08:contrast=1.03", "tuong_phan": "eq=contrast=1.08:brightness=-0.02"}
def hdr_chain(src):
    """HDR (HLG / PQ của iPhone) -> SDR bt709. Ghi rõ nhãn màu vào (clip thiếu nhãn thì zscale báo 'no path')."""
    tin = src.get("hdr_trc") if src.get("hdr_trc") in ("arib-std-b67", "smpte2084") else "arib-std-b67"
    return (f"setparams=color_primaries=bt2020:color_trc={tin}:colorspace=bt2020nc:range=tv,"
            "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")


def q(path):
    """Đường dẫn trong chuỗi filter ffmpeg: bọc nháy đơn + thoát ':' (ổ đĩa Windows E:) và nháy đơn — chung.loc.
    (Bản máy chủ cũ chỉ bọc nháy: đủ trên Linux, nhưng 'E:/…' bị tầng tùy chọn của ffmpeg tách ở dấu ':'.)"""
    return loc(path)


def co_tieng_that(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return bool(r.stdout.strip())


def loai_am(src):
    a = src.get("am_thanh")
    return a.get("loai") if isinstance(a, dict) else a
KHU_ON = "highpass=f=90,afftdn=nr=12:nf=-30:tn=1"
LUFS, TP, LRA = -14.0, -1.5, 11.0


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg lỗi:\n" + " ".join(cmd)[:600] + "\n" + r.stderr[-1500:])
    return r


def easing(kieu, U):
    """U: biểu thức 0→1. muot = vào/ra êm (smoothstep), bat = bật nhanh rồi chậm dần, deu = tuyến tính."""
    if kieu == "deu":
        return U
    if kieu == "bat":
        return f"(1-pow(1-{U},3))"
    return f"({U}*{U}*(3-2*{U}))"


def pre_chain(src, fps):
    return f"fps={fps}" + ("," + hdr_chain(src) if src.get("hdr") else "")


def audio_src(src, tmp, cache):
    """Tiếng nguồn đã khử ồn (làm 1 lần cho cả clip để mức ồn ổn định giữa các cảnh)."""
    key = src["local"]
    if key in cache:
        return cache[key]
    path = src["local"]
    if src.get("co_tieng", True) and src.get("khu_on", True) and loai_am(src) != "nhac":
        out = os.path.join(tmp, f"tieng-{len(cache):02d}.wav")
        run([FFMPEG, "-loglevel", "error", "-y", "-i", src["local"], "-vn", "-af", KHU_ON + ",aresample=48000",
             "-ac", "2", "-c:a", "pcm_s16le", out])
        path = out
    cache[key] = path
    return path


def stab_file(s, src, fps, tmp, idx):
    """Lượt 1 chống rung: đo chuyển động của đúng đoạn cảnh."""
    trf = os.path.join(tmp, f"rung-{idx:02d}.trf")
    d = s["den"] - s["tu"]
    ma_hoa.chay_gm([FFMPEG, "-loglevel", "error", "-y", "-ss", str(s["tu"]), "-t", f"{d:.4f}"] + ma_hoa.vao() + ["-i", src["local"], "-vf",
                    pre_chain(src, fps) + f",vidstabdetect=shakiness=6:accuracy=12:result={q(trf)}", "-f", "null", "-"], run)
    return trf


# ------------------------------------------------------------------ chống rung theo nhóm (4/11, POLY Cut "Chống rung")
# Trước: mỗi phần ≤ 2,5s của 1 cảnh tự chống rung riêng (đo + làm mượt + tự phóng optzoom riêng) -> ở chỗ nối 2 phần hình nhảy
# (đo clip lắc tay 10s, nhịp nhanh: nhảy 17,7 px + đổi cỡ 0,3% ở giây 7,43, các khung khác ~1 px). Giờ: các phần LIỀN NHAU của cùng
# clip (cùng cảnh, nửa chia nối liền…) cùng bật chống rung = 1 nhóm, đo 1 lượt và làm mượt 1 lượt cho cả nhóm, ghi 1 file trung gian
# đã ổn định (đã đổi fps, HDR -> SDR, thu nhỏ vừa đủ cho khung ra); từng phần đọc file đó -> không nhảy ở chỗ nối, 1 mức phóng.
# Đo chuyển động trên hình CHƯA chuyển màu HDR (chỉ cần độ sáng) -> bỏ được 1 lượt chuyển màu 32-bit tốn nhất.
OD_DO = "vidstabdetect=shakiness=6:accuracy=12"
OD_LAM = "vidstabtransform=smoothing=12:optzoom=1:interpol=bicubic"


def nhom_on_dinh(shots, nguon, fps):
    """[[chỉ số phần], …]: phần bật chống rung (canh / nguồn on_dinh), liền nhau, cùng clip, giờ nối tiếp (lệch < nửa khung)."""
    out, cur = [], []
    for i, s in enumerate(shots):
        if not ((s.get("on_dinh") or nguon[s["file"]].get("on_dinh")) and not s.get("the_hoi")):
            cur = []
            continue
        t = shots[cur[-1]] if cur else None
        if t is not None and t["file"] == s["file"] and abs(s["tu"] - t["den"]) < 0.5 / fps and not s.get("montage") and not t.get("montage"):
            cur.append(i)
        else:
            cur = [i]
            out.append(cur)
    return out


def _nhan_trf(trf, kx, ky):
    """Số đo vidstabdetect ở ảnh nhỏ -> cỡ ảnh làm: mỗi (LM v.x v.y f.x f.y f.size contrast match) nhân v / f theo kx, ky (số nguyên)."""
    def lm(m):
        v = m.group(1).split()
        if len(v) < 7:
            return m.group(0)
        a = [int(round(int(v[0]) * kx)), int(round(int(v[1]) * ky)), int(round(int(v[2]) * kx)), int(round(int(v[3]) * ky)),
             int(round(int(v[4]) * kx))]
        return "(LM " + " ".join(str(x) for x in a + v[5:7]) + ")"
    s = open(trf, encoding="utf-8", errors="replace").read()
    tam = trf + ".tmp"
    with open(tam, "w", encoding="utf-8") as fh:
        fh.write(re.sub(r"\(LM ([^()]*)\)", lm, s))
    os.replace(tam, trf)


def lam_on_dinh(shots, g, src, W, H, fps, tmp, idx, crf):
    """Nhóm g -> file trung gian đã ổn định; gắn shots[i]["_od"] = {local, tu0, rong, cao}. Thu nhỏ trước khi chống rung xuống đúng
    cỡ phần dựng cần (bản nháp 540p / clip 4K: ít điểm ảnh hơn nhiều; optzoom tính theo % khung nên mức phóng như bản đủ cỡ)."""
    sw, sh = src["rong"], src["cao"]
    f = min(1.0, max(max(W / sw, H / sh) * khung_canh(shots[i])[0] for i in g))
    rw, rh = (sw, sh) if f >= 0.999 else (max(2, int(round(sw * f / 2)) * 2), max(2, int(round(sh * f / 2)) * 2))
    nho = "" if (rw, rh) == (sw, sh) else f",scale={rw}:{rh}:flags=lanczos"
    A, B = shots[g[0]]["tu"], shots[g[-1]]["den"]
    vao = ["-ss", f"{A:.4f}", "-t", f"{B - A + 0.2:.4f}"] + ma_hoa.vao() + ["-i", src["local"]]   # vao(): giải mã bằng card (10/11), tắt = []
    trf = os.path.join(tmp, f"od-{idx:02d}.trf")
    out = os.path.join(tmp, f"od-{idx:02d}.mkv")
    # đo chuyển động trên ảnh ~540px cạnh ngắn (đo ở 1080 tốn gấp ~3 lần), rồi nhân số đo về cỡ làm (_nhan_trf)
    k = max(1, int(round(min(rw, rh) / 540.0)))
    dw, dh = (rw, rh) if k == 1 else (max(2, rw // k // 2 * 2), max(2, rh // k // 2 * 2))
    do_nho = f",scale={dw}:{dh}:flags=bilinear" if (dw, dh) != (sw, sh) else ""
    ma_hoa.chay_gm([FFMPEG, "-loglevel", "error", "-y"] + vao + ["-an", "-vf", f"fps={fps}{do_nho},format=yuv420p,{OD_DO}:result={q(trf)}", "-f", "null", "-"], run)
    if (dw, dh) != (rw, rh):
        _nhan_trf(trf, rw / dw, rh / dh)
    mau = ("," + hdr_chain(src)) if src.get("hdr") else ""
    enc = ["-qp", "0"] if crf <= 0 else ["-crf", str(max(0, int(crf) - 4))]
    vao = ma_hoa.bo_hw(vao) if "-hwaccel" in vao and ma_hoa.giai_ma() is None else vao   # lượt đo vừa lùi CPU: lượt làm cũng CPU
    ma_hoa.chay_gm([FFMPEG, "-loglevel", "error", "-y"] + vao + ["-an", "-vf", f"fps={fps}{nho}{mau},format=yuv420p,{OD_LAM}:input={q(trf)}",
                    "-c:v", "libx264", "-preset", "ultrafast"] + enc + ["-g", "15", "-pix_fmt", "yuv420p", out], run)
    for i in g:
        shots[i]["_od"] = {"local": out, "tu0": A, "rong": rw, "cao": rh}


def deck():
    return json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kieu_dung.json"), encoding="utf-8"))


def _so(v, mac, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return mac
    return mac if v != v else max(lo, min(hi, v))


def khung_canh(s):
    """canh[].khung (POLY Cut 3/11, "Vị trí & kích thước" kiểu CapCut): {zoom 1–3, x −1..1, y −1..1} -> (zoom, x, y).
    x / y = lệch trong phần thừa sau khi phủ khung (−1 = sát trái / trên, 1 = sát phải / dưới): chọn phần lấy của clip quay ngang."""
    k = s.get("khung") if isinstance(s.get("khung"), dict) else {}
    return _so(k.get("zoom"), 1.0, 1.0, 3.0), _so(k.get("x"), 0.0, -1.0, 1.0), _so(k.get("y"), 0.0, -1.0, 1.0)


def crop_khung(W, H, x, y):
    """crop W×H; không lệch thì giữ đúng chuỗi cũ (kế hoạch cũ dựng y hệt)."""
    if x == 0 and y == 0:
        return f"crop={W}:{H}"
    return f"crop={W}:{H}:x='(iw-ow)*(0.5+0.5*({x:g}))':y='(ih-oh)*(0.5+0.5*({y:g}))'"


def mau_canh(s):
    """canh[].mau {sang −0.3..0.3, tuong_phan 0.5..1.5, bao_hoa 0..2, nhiet 3000..9000 (6500 = giữ)} -> chuỗi filter ('' = không đổi)."""
    m = s.get("mau") if isinstance(s.get("mau"), dict) else {}
    sang, tp, bh = _so(m.get("sang"), 0.0, -0.3, 0.3), _so(m.get("tuong_phan"), 1.0, 0.5, 1.5), _so(m.get("bao_hoa"), 1.0, 0.0, 2.0)
    nhiet = _so(m.get("nhiet"), 6500.0, 3000.0, 9000.0)
    f = []
    if (sang, tp, bh) != (0.0, 1.0, 1.0):
        f.append(f"eq=brightness={sang:g}:contrast={tp:g}:saturation={bh:g}")
    if nhiet != 6500.0:
        f.append(f"colortemperature=temperature={int(round(nhiet))}")
    return ",".join(f)


def am_luong_canh(s):
    """canh[].am_luong 0–2 (1 = giữ, 0 = tắt tiếng)."""
    return _so(s.get("am_luong"), 1.0, 0.0, 2.0)


# bộ lọc màu LUT riêng cảnh (POLY Cut 4/11): engine/luts/<ten>.cube (danh sách + tên hiện: luts/bo-loc.json)
LUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "luts")


def _tron_lut(goc, muc, ra):
    """LUT trộn với LUT "không đổi" theo mức muc: ra(x) = (1−muc)·x + muc·LUT(x). Nội suy lut3d tuyến tính theo nút nên đúng
    bằng trộn 2 hình (lut3d không có tuỳ chọn mix)."""
    n, dau, so = 0, [], []
    for dong in open(goc, encoding="utf-8"):
        s = dong.strip()
        if not s or s[0] == "#":
            continue
        if s[0].isalpha():
            dau.append(s)
            if s.startswith("LUT_3D_SIZE"):
                n = int(s.split()[1])
            continue
        so.append(s.split()[:3])
    if n < 2 or len(so) != n ** 3:
        raise SystemExit("LUT hỏng: %s" % os.path.basename(goc))
    out = ["# tron %.2f tu %s" % (muc, os.path.basename(goc))] + [d for d in dau if not d.startswith("TITLE")]
    for i, v in enumerate(so):
        x = (i % n / (n - 1), i // n % n / (n - 1), i // (n * n) / (n - 1))
        out.append(" ".join("%.6f" % ((1 - muc) * x[c] + muc * float(v[c])) for c in range(3)))
    tam = ra + ".%d.tmp" % os.getpid()
    with open(tam, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.replace(tam, ra)


def loc_canh(s, tmp):
    """canh[].loc {ten: tên LUT trong engine/luts (a-z 0-9 _), muc 0–1 (1 = đủ)} -> 'lut3d=…' ('' = không lọc / không thấy LUT)."""
    l = s.get("loc") if isinstance(s.get("loc"), dict) else {}
    ten = str(l.get("ten") or "")
    muc = round(_so(l.get("muc"), 1.0, 0.0, 1.0), 2)
    goc = os.path.join(LUT_DIR, ten + ".cube")
    if not re.fullmatch(r"[a-z0-9_]{1,40}", ten) or muc < 0.01:
        return ""
    if not os.path.isfile(goc):
        print("bỏ qua bộ lọc %s: không thấy %s" % (ten, goc), file=sys.stderr)
        return ""
    f = goc
    if muc < 1.0:
        f = os.path.join(tmp, "loc-%s-%03d.cube" % (ten, round(muc * 100)))
        if not os.path.isfile(f):
            _tron_lut(goc, muc, f)
    return f"lut3d=file={q(f)}:interp=tetrahedral"


def shot_clip(s, src, W, H, fps, out, crf, tmp, idx, acache, dn="khong", kf_lui=None):
    """1 cảnh -> file mp4 W×H đúng số khung, kèm tiếng (có fade ngắn).
    kf_lui (r35, chỉ cảnh đứng trước chỗ nối chuyển cảnh mới): đặt keyframe cách cuối cảnh chừng đó giây -> bộ dựng chỗ nối tua
    tới đuôi cảnh khỏi giải mã lại cả cảnh. Không có (mọi kế hoạch cũ) = lệnh y như trước."""
    od = s.get("_od")   # chống rung theo nhóm (4/11): hình lấy từ file trung gian đã ổn định (lam_on_dinh), tiếng vẫn lấy clip gốc
    sw, sh = (od["rong"], od["cao"]) if od else (src["rong"], src["cao"])
    cover = max(W / sw, H / sh)
    kz, kx, ky = khung_canh(s)   # khung tĩnh riêng cảnh: phóng thêm rồi cắt lệch (kế hoạch cũ: 1, 0, 0 -> y hệt trước)
    cw, ch = int(round(sw * cover * kz / 2) * 2), int(round(sh * cover * kz / 2) * 2)
    crop = crop_khung(W, H, kx, ky)
    if s.get("the_hoi"):
        d = s["the_hoi"]
        n = int(round(d * fps))
        ma_hoa.chay_gm([FFMPEG, "-loglevel", "error", "-y", "-ss", str(s["tu"])] + ma_hoa.vao() + ["-i", src["local"], "-frames:v", "1",
                        "-vf", (hdr_chain(src) + "," if src.get("hdr") else "") + "scale=iw:ih", "-f", "image2", out + ".png"], run)
        run([FFMPEG, "-loglevel", "error", "-y", "-loop", "1", "-i", out + ".png", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
             "-vf", f"scale={cw}:{ch}:flags=lanczos,{crop},boxblur=24:2,eq=brightness=-0.12,fps={fps},setsar=1",
             "-t", f"{n / fps:.4f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-c:a", "pcm_s16le", "-ar", "48000", "-shortest", out])
        return n / fps
    d = s["den"] - s["tu"]
    n = int(round(d * fps))
    z0, z1, x0, x1 = s["z0"], s["z1"], s["x0"], s["x1"]
    U = f"min(1,max(0,(on-1)/{max(1, n - 1)}))"  # biến on của perspective đếm từ 1
    E = easing(s.get("easing", "muot"), U)
    vf = pre_chain(src, fps)
    vin = ["-ss", str(s["tu"]), "-t", f"{d:.4f}"] + ma_hoa.vao() + ["-i", src["local"]]   # vao(): giải mã bằng card (10/11), tắt = []
    if od:   # đã đổi fps + HDR -> SDR + ổn định trong file trung gian
        vf = f"fps={fps}"
        vin = ["-ss", f"{s['tu'] - od['tu0']:.4f}", "-t", f"{d:.4f}", "-i", od["local"]]
    elif s.get("on_dinh") or src.get("on_dinh"):
        trf = stab_file(s, src, fps, tmp, idx)
        vf += f",vidstabtransform=input={q(trf)}:smoothing=12:optzoom=1:interpol=bicubic"
    vf += f",scale={cw}:{ch}:flags=lanczos,{crop}"
    dap = dn == "zoom_dap" and s.get("dau_canh")
    if not (z0 == z1 == 1.0 and x0 == x1 == 0) or dap:
        # zoom theo cảm nhận (z0·(z1/z0)^e) + lia; perspective nội suy dưới điểm ảnh nên không giật
        Z = f"({z0}*pow({z1}/{z0},{E}))" if z0 != z1 else f"({z0})"
        if dap:  # điểm nhấn: đập zoom 110% -> 100% trong 0,25s đầu cảnh mới
            F = max(2, round(0.25 * fps))
            Z = f"({Z}*(1+0.10*pow(max(0,1-(on-1)/{F}),2)))"
        X = f"({x0}+({x1}-{x0})*{E})" if x0 != x1 else f"({x0})"
        L = f"max(0,min(W-W/{Z},(W-W/{Z})/2+{X}*W))"
        T = f"((H-H/{Z})/2)"
        R, B = f"({L}+W/{Z})", f"({T}+H/{Z})"
        vf += f",perspective=x0='{L}':y0='{T}':x1='{R}':y1='{T}':x2='{L}':y2='{B}':x3='{R}':y3='{B}':interpolation=cubic:eval=frame"
    if dn == "rung_nhip" and s.get("dau_canh"):  # điểm nhấn: rung máy nhẹ 0,35s đầu cảnh mới
        A, F = round(W * 0.012, 1), max(2, round(0.35 * fps))
        vf += (f",scale=trunc(iw*1.06/2)*2:-2,crop={W}:{H}:x='(iw-ow)/2+{A}*sin(n*2.3)*max(0,1-n/{F})'"
               f":y='(ih-oh)/2+{A}*cos(n*1.9)*max(0,1-n/{F})'")
    mc = mau_canh(s)
    if mc:  # màu riêng cảnh (3/11): sau zoom / lia, trước hiệu ứng hình
        vf += "," + mc
    lc = loc_canh(s, tmp)
    if lc:  # bộ lọc màu LUT riêng cảnh (4/11): ngay sau màu riêng cảnh
        vf += "," + lc
    hu = (deck().get("hieu_ung_canh") or {}).get(s.get("hieu_ung") or "")
    if isinstance(hu, dict) and hu.get("filter") and not (hu.get("dau_canh") and s.get("phan", 0)):
        # hiệu ứng hình riêng cảnh (3/11): sau zoom / lia, trước chữ; "đầu cảnh" chỉ ở phần đầu của cảnh
        vf += "," + hu["filter"].replace("(on-1)/30)", "(on-1)/%s)" % fps)
    vf += ",setsar=1"
    fb = s.get("dong_bang", 0.0)
    if fb:
        vf += f",tpad=start_duration={fb}:start_mode=clone"
    al = am_luong_canh(s)
    af = "aresample=48000" + (f",volume={al:g}" if al != 1.0 else "") + f",afade=t=in:st=0:d=0.03,afade=t=out:st={max(0, d - 0.05):.3f}:d=0.05"
    if fb:
        af += f",adelay={int(fb * 1000)}|{int(fb * 1000)}"
    total = d + fb
    cmd = [FFMPEG, "-loglevel", "error", "-y"] + vin
    if src.get("co_tieng", True):  # main() đã dò lại bằng ffprobe
        cmd += ["-ss", str(s["tu"]), "-t", f"{d:.4f}", "-i", audio_src(src, tmp, acache),
                "-vf", vf, "-af", af + f",apad=whole_dur={total:.4f}", "-map", "0:v", "-map", "1:a"]
    else:
        cmd += ["-f", "lavfi", "-t", f"{total:.4f}", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-map", "0:v", "-map", "1:a"]
    # tiếng PCM trong file trung gian: AAC làm tròn 1024 mẫu -> lệch hình-tiếng cộng dồn qua nhiều cảnh
    cmd += ["-frames:v", str(int(round(total * fps)))]
    kf = []
    if kf_lui:   # keyframe gần đuôi (card NVIDIA: khung I phải là IDR mới tua tới được)
        kf = ["-force_key_frames", f"{max(0.0, total - kf_lui):.4f}"]
    ma_hoa.chay(lambda v: cmd + v + (kf + (["-forced-idr", "1"] if kf and any(str(x).endswith("_nvenc") for x in v) else []))
                + ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", out], lambda c: ma_hoa.chay_gm(c, run), crf=crf)
    return total


def loudnorm_2(src, out):
    """Lượt 1 đo, lượt 2 chỉnh tuyến tính về -14 LUFS; hình chép nguyên."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", src, "-vn", "-af",
                        f"loudnorm=I={LUFS}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    j = json.loads(m.group(0)) if m else {}

    def so(k):
        try:
            v = float(j.get(k))
            return v if v == v and abs(v) != float("inf") else None
        except (TypeError, ValueError):
            return None
    vals = {k: so(k) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")}
    if vals["input_i"] is None or vals["input_i"] < -70:
        af = "aresample=48000"  # tiếng im (hoặc gần như im): không chuẩn hóa được, giữ nguyên
    elif all(v is not None for v in vals.values()):
        af = (f"loudnorm=I={LUFS}:TP={TP}:LRA={LRA}:measured_I={vals['input_i']}:measured_TP={vals['input_tp']}:"
              f"measured_LRA={vals['input_lra']}:measured_thresh={vals['input_thresh']}:offset={vals['target_offset']}:linear=true,"
              "aresample=48000")
    else:
        af = f"loudnorm=I={LUFS}:TP={TP}:LRA={LRA},aresample=48000"
    run([FFMPEG, "-loglevel", "error", "-y", "-i", src, "-c:v", "copy", "-af", af,
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    return vals["input_i"]


# ------------------------------------------------------------------ nhạc nền + cân tiếng (4/11, POLY Cut)
# tl["nhac"] = {local, ten, tu (giây bắt đầu trong file), am_luong 0–2, ha_khi_noi, vao / ra (giây mờ dần đầu / cuối)}
# tl["can_tieng"] = {giong 0–2, clip 0–2}. ke_hoach.build chép 2 khoá này CHỈ khi kế hoạch có -> kế hoạch cũ: lệnh trộn y hệt trước.
# Mức nhạc tính theo tiếng nói của chính video (giọng AI −16 LUFS, không có thì tiếng clip đo được): lúc không ai nói nhạc thấp hơn
# tiếng nói ~6 dB, có giọng AI / người nói trong clip thì tự hạ thêm ~10–12 dB (sidechain theo giọng + tiếng clip, dải tiếng nói
# 200–4000 Hz). Bản cuối vẫn qua acompressor + loudnorm 2 lượt về −14 LUFS như cũ. Premiere (lenh_premiere) bỏ qua 2 khoá này.
GIONG_LUFS = -16.0      # giọng AI chuẩn hoá trước khi trộn (loudnorm I=-16 ở dưới)
NHAC_DUOI_NOI = 6.0     # dB: nhạc lúc không ai nói nằm dưới mức tiếng nói chừng này
NHAC_KHONG_HA = 12.0    # dB: tắt "tự hạ khi có người nói" thì nhạc nằm luôn dưới tiếng nói chừng này
NHAC_HA = "threshold=0.01:ratio=20:attack=15:release=400:knee=2.8:mix=0.75"   # mix 0.75: hạ sâu nhất ~12 dB, không câm hẳn


def _lufs(args):
    """Độ to tích hợp (LUFS) đo bằng loudnorm lượt 1 (args = đầu vào + -af / -filter_complex có loudnorm print_format=json).
    None = im lặng / không đọc được."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-nostats"] + args + ["-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
    try:
        v = float(json.loads(m.group(0))["input_i"]) if m else None
    except (ValueError, KeyError, TypeError):
        return None
    return v if v is not None and -70.0 < v < 10.0 else None


def _giay_tep(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", p],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        g = float((r.stdout or "").strip().splitlines()[0])
        return g if g == g and g > 0 else None
    except (ValueError, IndexError):
        return None


def tron_them(tl, T, files, them=None):
    """Thông số trộn thêm: {"clip": hệ số, "giong": hệ số, "nhac": {...} | None, "loi": ""} hoặc None (kế hoạch không có nhạc /
    cân tiếng). Hệ số 1 + không nhạc = không thêm filter nào (lệnh y hệt trước).
    them = [(file tiếng, giây đầu, dài, âm lượng)] các khối tiếng tách (4/11): đo mức tiếng nói gồm cả các khối (cảnh đã tách thì im)."""
    import math
    lg = math.log10
    n, ct = tl.get("nhac"), tl.get("can_tieng")
    co_nhac = isinstance(n, dict) and isinstance(n.get("local"), str) and n.get("local")
    if not co_nhac and not isinstance(ct, dict):
        return None
    ct = ct if isinstance(ct, dict) else {}
    out = {"clip": _so(ct.get("clip"), 1.0, 0.0, 2.0), "giong": _so(ct.get("giong"), 1.0, 0.0, 2.0), "nhac": None, "loi": ""}
    if not co_nhac:
        return out
    p, am = n["local"], _so(n.get("am_luong"), 1.0, 0.0, 2.0)
    if am < 0.01:
        return out   # kéo nhạc về 0%: như không có nhạc
    D = _giay_tep(p) if os.path.isfile(p) else None
    if not D or D < 1.0:
        out["loi"] = "không đọc được file nhạc %s: dựng không có nhạc" % os.path.basename(p)
        return out
    tu = _so(n.get("tu"), 0.0, 0.0, max(0.0, D - 1.0))
    ha = n.get("ha_khi_noi", True) is not False
    vao, ra = min(_so(n.get("vao"), 0.3, 0.0, 5.0), T / 3), min(_so(n.get("ra"), 1.5, 0.0, 8.0), T / 3)
    # mức tiếng nói của video: giọng AI (đã chuẩn hoá) hoặc tiếng clip (đo cả các cảnh, đã gồm âm lượng riêng cảnh)
    l_clip = None
    if files and out["clip"] > 0:
        vao_ = []
        for f in files:
            vao_ += ["-vn", "-i", f]
        if them:   # tiếng tách (4/11): nối thêm các khối (đúng đoạn, đúng âm lượng) rồi mới đo
            for p_, tu_, dai_, am_ in them:
                vao_ += ["-ss", "%.4f" % tu_, "-t", "%.4f" % dai_, "-vn", "-i", p_]
            n_ = len(files) + len(them)
            l_clip = _lufs(vao_ + ["-filter_complex", "".join(
                "[%d:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo%s[m%d];"
                % (i, ",volume=%g" % them[i - len(files)][3] if i >= len(files) and them[i - len(files)][3] != 1.0 else "", i)
                for i in range(n_)) + "".join("[m%d]" % i for i in range(n_))
                + "concat=n=%d:v=0:a=1,loudnorm=print_format=json[o]" % n_, "-map", "[o]"])
        else:
            l_clip = _lufs(vao_ + ["-filter_complex", "".join("[%d:a]" % i for i in range(len(files)))
                                   + "concat=n=%d:v=0:a=1,loudnorm=print_format=json[o]" % len(files), "-map", "[o]"])
        if l_clip is not None:
            l_clip += 20 * lg(out["clip"])
        if l_clip is not None and l_clip < -45:
            l_clip = None   # chỉ có tiếng ồn rất nhỏ: không tính là người nói
    g = tl.get("giong")
    co_giong = isinstance(g, dict) and isinstance(g.get("local"), str) and os.path.isfile(g["local"]) and out["giong"] > 0
    if not co_giong and tl.get("giong_de") and out["giong"] > 0:   # r32: giọng AI đọc lại khối tách (chỉ khi kế hoạch có)
        import doc_lai
        co_giong = bool(doc_lai.dat(tl, T)["dat"])
    l_ref = GIONG_LUFS + 20 * lg(out["giong"]) if co_giong else l_clip if l_clip is not None else -20.0
    l_nhac = _lufs(["-ss", "%.3f" % tu, "-t", "%.3f" % min(D - tu, max(T, 10.0), 120.0), "-i", p, "-vn",
                    "-af", "loudnorm=print_format=json"])
    if l_nhac is None:
        out["loi"] = "file nhạc %s im lặng: dựng không có nhạc" % os.path.basename(p)
        return out
    muc = l_ref - (NHAC_DUOI_NOI if ha else NHAC_KHONG_HA) + 20 * lg(am)
    out["nhac"] = {"p": p, "D": D, "tu": tu, "ha": ha and (co_giong or l_clip is not None), "vao": vao, "ra": ra,
                   "gain": round(max(-40.0, min(24.0, muc - l_nhac)), 2), "l_ref": round(l_ref, 1), "l_nhac": round(l_nhac, 1),
                   "khoa_clip": None if l_clip is None else round(max(-10.0, min(6.0, -20.0 - l_clip)), 2), "co_giong": co_giong}
    return out


def nhac_dau_vao(nh, T, mi):
    """Nhạc -> (đầu vào ffmpeg, dòng filter, nhãn ra) dài đúng T. Nhạc ngắn hơn video thì lặp lại từ đầu bài, nối mờ chéo
    (acrossfade) cho khỏi giật; mờ dần đầu / cuối; chỉnh độ to (gain dB)."""
    D, tu = nh["D"], nh["tu"]
    xf = round(min(1.0, D / 4), 3)
    doan = [(tu, min(D - tu, T + 0.2))]
    tong = doan[0][1]
    while tong < T + 0.05 and len(doan) < 60:
        doan.append((0.0, D))
        tong += D - xf
    vao, fc = [], []
    for k, (a, d) in enumerate(doan):
        vao += (["-ss", "%.3f" % a] if a > 0 else []) + ["-t", "%.3f" % d, "-i", nh["p"]]
        fc.append(f"[{mi + k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[nh{k}]")
    cur = "[nh0]"
    for k in range(1, len(doan)):
        fc.append(f"{cur}[nh{k}]acrossfade=d={xf}:c1=qsin:c2=qsin[nx{k}]")
        cur = f"[nx{k}]"
    ch = f"{cur}atrim=0:{T:.4f},apad=whole_dur={T:.4f},volume={nh['gain']}dB"
    if nh["vao"] > 0.01:
        ch += f",afade=t=in:st=0:d={nh['vao']:.3f}"
    if nh["ra"] > 0.01:
        ch += f",afade=t=out:st={max(0.0, T - nh['ra']):.4f}:d={nh['ra']:.3f}"
    fc.append(ch + "[nhac]")
    return vao, fc, "[nhac]"


# ------------------------------------------------------------------ tiếng tách (4/11, POLY Cut "Tách âm thanh" kiểu CapCut)
# tl["am_tach"] = [{id, goc, nguon (khoá trong nguon), tu, den (giây trong clip), t (giây trên video), am_luong 0–2, vao / ra (giây mờ)}]
# Cảnh đã tách (canh.tach_am) thì im (ke_hoach.build đặt am_luong 0); tiếng của cảnh thành khối riêng đặt ở giờ t, dời / cắt / chia
# độc lập với hình (J/L cut). Khối là TIẾNG CLIP: trộn vào tiếng các cảnh TRƯỚC bước cân tiếng -> theo thanh "Tiếng clip"
# (can_tieng.clip), tự hạ dưới giọng AI, làm tín hiệu hạ nhạc, rồi acompressor + loudnorm 2 lượt −14 LUFS như cũ.
# Giọng AI "thay hẳn tiếng clip" (giong.thay_tieng) thì khối cũng im. Không có khoá -> không thêm đầu vào / filter nào (lệnh y hệt trước).
def am_tach_ds(tl, T):
    """-> [(khoá nguồn, giây đầu trong clip, dài, giây trên video, âm lượng, mờ vào, mờ ra)] các khối dùng được."""
    ds, out = tl.get("am_tach"), []
    g = tl.get("giong")
    if not isinstance(ds, list) or (isinstance(g, dict) and g.get("thay_tieng")):
        return out
    vs = None
    if tl.get("giong_de"):   # r32: giọng AI đọc lại khối (doc_lai.py) -> phần tiếng gốc được đọc lại tắt / còn nền
        import doc_lai
        vs = doc_lai.vung(tl)
    for k in ds[:300]:
        if not isinstance(k, dict):
            continue
        src = (tl.get("nguon") or {}).get(k.get("nguon"))
        if not isinstance(src, dict) or not src.get("local") or not src.get("co_tieng", True):
            continue
        tu, den, t = _so(k.get("tu"), -1.0, 0.0, 1e6), _so(k.get("den"), -1.0, 0.0, 1e6), _so(k.get("t"), 0.0, -1e6, 1e6)
        if tu < 0 or den <= tu:
            continue
        if t < 0:   # khối thò ra trước đầu video: bỏ phần thò
            tu, t = tu - t, 0.0
        dai = min(den - tu, T - t)
        am = _so(k.get("am_luong"), 1.0, 0.0, 2.0)
        if dai < 0.05 or am < 0.005:
            continue
        vao, ra = min(_so(k.get("vao"), 0.0, 0.0, 10.0), dai / 2), min(_so(k.get("ra"), 0.0, 0.0, 10.0), dai / 2)
        x = (k["nguon"], round(tu, 4), round(dai, 4), round(t, 4), am, vao, ra)
        if vs:   # r32: thêm phần thứ 8 = [(giây đầu, giây cuối, mức)] chỉ khi khối bị đọc lại; tắt hẳn cả khối thì bỏ khối
            tat = doc_lai.tat_khoi(vs, k, tu, dai)
            if tat == "het":
                continue
            if tat:
                x += (tat,)
        out.append(x)
    return out


def am_tach_dau_vao(ds, T, mi, nguon, tmp, acache):
    """Khối tiếng tách -> (đầu vào ffmpeg, dòng filter, nhãn ra từng khối): đúng đoạn clip (tiếng đã khử ồn như các cảnh), âm lượng,
    mờ vào / ra (tối thiểu 0,03 / 0,05s như mép cảnh cho khỏi lụp bụp), dời tới giây t, đệm im cho đủ dài video."""
    vao, fc, nhan = [], [], []
    for j, x in enumerate(ds):
        key, tu, dai, t, am, fi, fo = x[:7]
        vao += ["-ss", "%.4f" % tu, "-t", "%.4f" % dai, "-i", audio_src(nguon[key], tmp, acache)]
        fi, fo = max(fi, 0.03), max(fo, 0.05)
        ch = f"[{mi + j}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS"
        if am != 1.0:
            ch += f",volume={am:g}"
        for a_, b_, n_ in (x[7] if len(x) > 7 else ()):   # r32: đoạn được giọng AI đọc lại -> tiếng gốc tắt / còn nền
            ch += f",volume={n_:g}:enable='between(t,{a_:.4f},{b_:.4f})'"
        ch += f",afade=t=in:st=0:d={fi:.3f},afade=t=out:st={max(0.0, dai - fo):.4f}:d={fo:.3f}"
        ms = int(round(t * 1000))
        if ms > 0:
            ch += f",adelay={ms}|{ms}"
        fc.append(ch + f",apad=whole_dur={T:.4f},atrim=0:{T:.4f}[at{j}]")
        nhan.append(f"[at{j}]")
    return vao, fc, nhan
# ------------------------------------------------------------------ âm thanh hiệu ứng ngắn (r20, POLY Cut Thư viện › Âm thanh)
# tl["am_thanh"] = [{local, t (giây trên video), am_luong 0–2}] — ke_hoach.build chép khoá CHỈ khi kế hoạch có -> kế hoạch cũ y hệt.
# File kèm app (poly-team/am-thanh, tự tổng hợp CC0, M max ≈ −16 LUFS) trộn ở AM_THANH_MUC, sau nhạc nền (nhạc không nhún theo
# tiếng hiệu ứng), trước nén + chuẩn −14 LUFS như mọi tiếng khác. Premiere (lenh_premiere) bỏ qua khoá này.
AM_THANH_MUC = 1.0   # đo trên clip có lời nói (r20): tiếng ở 100% thấp hơn lời nói ~6 dB — nghe rõ, không lấn lời


def am_thanh_dau_vao(ds, T, mi):
    """-> (đầu vào ffmpeg, dòng filter, "[sfx]") | None. Mỗi tiếng dời tới giây t (adelay), chỉnh âm lượng; tiếng bắt đầu ngoài
    [0, T) / file mất / âm lượng 0 thì bỏ. Nhiều tiếng gộp bằng amix (normalize=0, dài theo tiếng kết thúc muộn nhất)."""
    if not isinstance(ds, list):
        return None
    vao, fc = [], []
    for x in ds[:200]:
        if not isinstance(x, dict) or not isinstance(x.get("local"), str) or not os.path.isfile(x["local"]):
            continue
        t, al = _so(x.get("t"), -1.0, -1.0, 36000.0), _so(x.get("am_luong"), 1.0, 0.0, 2.0)
        if t < 0 or t >= T - 0.02 or al < 0.01:
            continue
        k, ms = len(fc), int(round(t * 1000))
        vao += ["-i", x["local"]]
        fc.append(f"[{mi + k}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,"
                  f"volume={AM_THANH_MUC * al:.3f},adelay={ms}|{ms}[sx{k}]")
    if not fc:
        return None
    n = len(fc)
    fc.append("".join(f"[sx{k}]" for k in range(n)) + (f"amix=inputs={n}:duration=longest:normalize=0[sfx]" if n > 1 else "anull[sfx]"))
    return vao, fc, "[sfx]"


NOI_DO = []   # r35: số đo các chỗ nối kiểu mới của lần dựng này (trả trong kết quả, app ghi log)


def dung_noi_moi(tl, files, durs, trans, W, H, fps, crf, tmp):
    """r35: dựng các đoạn chuyển kiểu mới ('poly-chuyen-1', engine/chuyen_moi.py) -> {chỉ số cảnh: file đoạn chuyển}.
    Mỗi đoạn = d giây cuối file cảnh trước + d giây đầu file cảnh sau, mã hoá qua ma_hoa (card / CPU như file cảnh).
    Chạy song song min(3, số nhân // 4) đoạn (POLY_NOI_SONG_SONG ép). Đoạn lỗi: bỏ (chỗ đó dùng xfade dự phòng), ghi stderr."""
    ds = [i for i in range(1, len(files)) if trans[i] > 0 and isinstance(tl["shots"][i].get("chuyen_moi"), dict)]
    if not ds:
        return {}
    import chuyen_moi as CM
    from concurrent.futures import ThreadPoolExecutor
    try:
        ss = int(os.environ.get("POLY_NOI_SONG_SONG") or 0)
    except ValueError:
        ss = 0
    ss = max(1, min(len(ds), ss or min(3, (os.cpu_count() or 2) // 4)))

    def mot(i):
        out = os.path.join(tmp, f"t{i:02d}.mkv")
        try:
            r = CM.dung_cho_noi(tl["shots"][i]["chuyen_moi"], files[i - 1], durs[i - 1], files[i], 0.0, out, d=trans[i],
                                W=W, H=H, fps=fps, crf=crf, tmp=tmp)
            sys.stderr.write("[chuyen_moi] chỗ nối %d %s: %.1fs (%d khung)\n" % (i, r["id"], r["giay"], r["khung"]))
            NOI_DO.append({"i": i, "id": r["id"], "giay": r["giay"], "khung": r["khung"], "ma_hoa": r.get("ma_hoa")})
            return i, out
        except (Exception, SystemExit) as e:  # noqa: BLE001  lỗi: lùi xfade dự phòng, video vẫn ra
            sys.stderr.write("[chuyen_moi] chỗ nối %d dựng lỗi, dùng xfade %s: %s\n" % (i, tl["shots"][i].get("chuyen_xfade"), str(e)[-300:]))
            NOI_DO.append({"i": i, "id": tl["shots"][i]["chuyen_moi"].get("id"), "loi": str(e)[-200:], "lui": tl["shots"][i].get("chuyen_xfade")})
            return i, None
    if ss == 1:
        kq = [mot(i) for i in ds]
    else:
        with ThreadPoolExecutor(ss) as ex:
            kq = list(ex.map(mot, ds))
    giu = os.environ.get("POLY_GIU_NOI")   # bài thử (thu_chuyen_moi.py): giữ bản đoạn chuyển để so khung với video ra
    if giu:
        os.makedirs(giu, exist_ok=True)
        for i, f in kq:
            if f:
                shutil.copy(f, os.path.join(giu, os.path.basename(f)))
    return {i: f for i, f in kq if f}


def main():
    argv = [a for a in sys.argv if not a.startswith("--")]
    tl = json.load(open(argv[1], encoding="utf-8"))
    lopj = json.load(open(argv[2], encoding="utf-8"))
    out = argv[3]
    tmp = tempfile.mkdtemp(prefix=".poly-dung-", dir=os.path.dirname(os.path.abspath(out)))  # thư mục tạm cạnh file ra
    try:
        ket = build(tl, lopj, out, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)  # xóa cả khi lỗi
    print(json.dumps(ket, ensure_ascii=False))


def chuoi_anh(ds, trong, tmp, ten):
    """r36 (bộ mẫu mới): các ảnh hiện nối tiếp [{png, t0, t1}] -> 1 đầu vào ffmpeg (concat demuxer, mỗi ảnh 1 khung giữ tới ảnh sau;
    chỗ trống / trước ảnh đầu = `trong`). Giờ chồng nhau: ảnh sau thắng. Trả đường file danh sách."""
    def dong(p, d):
        return "file '%s'\nduration %.6f\n" % (os.path.abspath(p).replace("'", "'\\''"), max(0.0, d))
    ds = sorted(ds, key=lambda x: (float(x["t0"]), float(x["t1"])))
    s, t = "ffconcat version 1.0\n", 0.0
    for i, x in enumerate(ds):
        a = max(float(x["t0"]), t)
        b = float(ds[i + 1]["t0"]) if i + 1 < len(ds) and float(ds[i + 1]["t0"]) < float(x["t1"]) else float(x["t1"])
        if b - a < 1e-3:
            continue
        if a - t > 1e-4:
            s += dong(trong, a - t)
        s += dong(x["png"], b - a)
        t = b
    s += dong(trong, 1.0) + "file '%s'\n" % os.path.abspath(trong).replace("'", "'\\''")   # ảnh cuối lặp lại: concat bỏ duration ảnh cuối
    p = os.path.join(tmp, ten + ".ffconcat")
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)
    return p


def build(tl, lopj, out, tmp):
    NOI_DO.clear()   # r40: số đo chỗ nối chỉ của lần dựng này (gọi build nhiều lần trong 1 tiến trình)
    lop = lopj["lop"]
    nhap = "--nhap" in sys.argv
    ass = None if "--phu-de-png" in sys.argv else lopj.get("ass")
    if ass and not os.path.exists(ass):
        ass = None
    if ass:
        lop = [l for l in lop if not l["ten"].startswith("phu-de-")]
    pd_seq = []   # r36: bộ mẫu mới -> phụ đề PNG thành 1 chuỗi ảnh (1 đầu vào). Kế hoạch cũ: không có khoá, như cũ
    if lopj.get("pd_chuoi") and not ass:
        pd_seq = [l for l in lop if l["ten"].startswith("phu-de-")]
        lop = [l for l in lop if not l["ten"].startswith("phu-de-")]
    for src in tl["nguon"].values():  # kế hoạch có thể ghi sai / thiếu co_tieng: dò lại
        src["co_tieng"] = co_tieng_that(src["local"])
    W, H = tl["khung"]
    if nhap:
        W, H = W // 2, H // 2
    fps = tl["fps"]
    k = tl["kieu"]
    # --chat-luong=nhe|chuan|cao (POLY Team, 3/11): CRF từng cảnh / bản cuối + preset bản cuối. Không ghi = chuan (như cũ).
    # cao: từng cảnh lưu KHÔNG MẤT (CRF 0, file tạm to) -> cả video chỉ nén mất 1 lần ở bản cuối (CRF 16, preset medium)
    cl = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--chat-luong=")), "chuan")
    crf_shot, crf_cuoi, preset_cuoi = {"nhe": (20, "23", "veryfast"), "cao": (0, "16", "medium")}.get(cl, (16, "19", "veryfast"))
    if nhap:
        crf_shot, crf_cuoi, preset_cuoi = 26, "26", "veryfast"
    dn, lp = k.get("diem_nhan", "khong"), k.get("lop_phu", "khong")
    files, durs, trans, acache = [], [], [], {}
    # chống rung theo nhóm phần liền nhau (4/11): làm file trung gian lúc tới phần đầu nhóm, xoá ngay sau phần cuối (file lớn)
    nhom_od = {g[0]: g for g in nhom_on_dinh(tl["shots"], tl["nguon"], fps)}
    cuoi_od = {g[-1] for g in nhom_od.values()}
    for i, s in enumerate(tl["shots"]):
        src = tl["nguon"][s["file"]]
        if i in nhom_od:
            lam_on_dinh(tl["shots"], nhom_od[i], src, W, H, fps, tmp, i, crf_shot)
        f = os.path.join(tmp, f"s{i:02d}.mkv")
        sau = tl["shots"][i + 1] if i + 1 < len(tl["shots"]) else {}
        kf_lui = (sau.get("chuyen") or 0) + 2.0 / fps if sau.get("chuyen_moi") and (sau.get("chuyen") or 0) > 0 else None
        durs.append(shot_clip(s, src, W, H, fps, f, crf_shot, tmp, i, acache, dn, **({"kf_lui": kf_lui} if kf_lui else {})))
        if i in cuoi_od and s.get("_od"):
            try:
                os.remove(s["_od"]["local"])
            except OSError:
                pass
        files.append(f)
        trans.append(s.get("chuyen", 0.0))
    # ghép: cắt cứng hoặc xfade ở ranh giới có 'chuyen' (kiểu theo bảng chuyen_canh_ky_thuat)
    kind = deck()["chuyen_canh_ky_thuat"].get(k["chuyen_canh"], {}).get("xfade") or "fade"
    moc_doi = []  # giây trên video ra: lúc cảnh mới hiện hẳn (cho điểm nhấn)
    inputs = []
    for f in files:
        inputs += ["-i", f]
    # r35: chỗ nối chuyển cảnh mới (shots[i].chuyen_moi) -> đoạn chuyển dựng riêng (chuyen_moi.py), thay xfade bằng trim + concat.
    # Kế hoạch cũ không có khoá này: không có đoạn nào, lệnh ffmpeg y hệt. Đoạn nào dựng lỗi: chỗ đó lùi về xfade dự phòng.
    noi_moi = dung_noi_moi(tl, files, durs, trans, W, H, fps, crf_shot, tmp)
    for i in sorted(noi_moi):   # đoạn ngắn: giải mã 1 luồng (đỡ bộ nhớ khung của bộ giải mã đa luồng khi video nhiều chỗ nối)
        inputs += ["-threads", "1", "-i", noi_moi[i]]
    fc = []
    for i in range(len(files)):  # thống nhất đơn vị thời gian để ghép cắt cứng + xfade
        fc.append(f"[{i}:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p[iv{i}]")
        fc.append(f"[{i}:a]aresample=48000,asettb=AVTB,asetpts=PTS-STARTPTS[ia{i}]")
    cur_v, cur_a, cur_len = "[iv0]", "[ia0]", durs[0]
    for i in range(1, len(files)):
        d = trans[i]
        nv, na = f"[v{i}]", f"[a{i}]"
        if tl["shots"][i].get("dau_canh"):
            moc_doi.append(round(cur_len, 4))  # cắt cứng: cảnh mới bắt đầu; xfade: lúc chuyển xong
        if d > 0 and i in noi_moi:   # r35: [cảnh trước bỏ d giây cuối][đoạn chuyển][cảnh sau bỏ d giây đầu]
            j = len(files) + sorted(noi_moi).index(i)
            e = 0.25 / fps   # lệch 1/4 khung: trim không ăn nhầm khung ở mép (giờ khung = k/fps)
            fc.append(f"{cur_v}trim=end={cur_len - d - e:.4f},setpts=PTS-STARTPTS[na{i}]")
            fc.append(f"[{j}:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS,format=yuv420p,setsar=1[nt{i}]")
            fc.append(f"[iv{i}]trim=start={d - e:.4f},setpts=PTS-STARTPTS[nb{i}]")
            fc.append(f"[na{i}][nt{i}][nb{i}]concat=n=3:v=1:a=0,settb=AVTB{nv}")
            fc.append(f"{cur_a}[ia{i}]acrossfade=d={d}{na}")
            cur_len += durs[i] - d
        elif d > 0:
            kd = tl["shots"][i].get("chuyen_xfade") or kind  # bộ trộn: mỗi chỗ nối một kiểu
            if kd == "custom":  # chuyển cảnh bằng biểu thức (3/11, riêng từng cảnh): biểu thức không có ':' / nháy đơn
                kd = "custom:expr='%s'" % tl["shots"][i].get("chuyen_expr", "")
            fc.append(f"{cur_v}[iv{i}]xfade=transition={kd}:duration={d}:offset={cur_len - d:.4f},settb=AVTB{nv}")
            fc.append(f"{cur_a}[ia{i}]acrossfade=d={d}{na}")
            cur_len += durs[i] - d
        else:
            fc.append(f"{cur_v}{cur_a}[iv{i}][ia{i}]concat=n=2:v=1:a=1[cv{i}]{na}")
            fc.append(f"[cv{i}]settb=AVTB{nv}")
            cur_len += durs[i]
        cur_v, cur_a = nv, na
    T = cur_len
    n_in = len(files) + len(noi_moi)
    vlabel = cur_v
    fx = []
    if MAU.get(k.get("mau")):
        fx.append(MAU[k["mau"]])
    # điểm nhấn theo mốc đổi cảnh + lớp phủ: làm trên hình TRƯỚC khi đặt chữ (chữ luôn nét, không bị chớp/tách màu)
    if dn == "chop_trang" and moc_doi:
        e1 = "+".join(f"between(t,{c:.3f},{c + 2 / fps:.3f})" for c in moc_doi)
        e2 = "+".join(f"between(t,{c + 2 / fps:.3f},{c + 4 / fps:.3f})" for c in moc_doi)
        fx.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.8:t=fill:enable='{e1}'")
        fx.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.35:t=fill:enable='{e2}'")
    if dn == "glitch_rgb" and moc_doi:
        a = max(4, W // 80)
        e = "+".join(f"between(t,{max(0.0, c - 0.04):.3f},{c + 0.12:.3f})" for c in moc_doi)
        fx.append(f"rgbashift=rh=-{a}:bh={a}:edge=smear:enable='{e}'")
    if lp == "hat_film":
        fx.append("noise=alls=7:allf=t+u")
    if lp == "toi_vien":
        fx.append("vignette=angle=PI/5")
    if fx:
        fc.append(f"{cur_v}{','.join(fx)}[vp]")
        vlabel = "[vp]"
    if lp == "loa_sang":  # lóa vàng Poly (29/10, trước: cam) đầu video và lúc vào thẻ kết
        k0 = tl["ket_t"][0] if (tl.get("chu") or {}).get("ket") else max(0.0, T - 1.5)
        inputs += ["-f", "lavfi", "-i", f"gradients=s={W}x{H}:c0=0xFFE278:c1=0xFFD600:c2=0x000000:nb_colors=3:speed=0.02:"
                                       f"rate={fps}:duration={T:.4f}:type=radial"]
        fc.append(f"{vlabel}format=gbrp[lka];[{n_in}:v]format=gbrp[lkb];[lka][lkb]blend=all_mode=screen:all_opacity=0.45:"
                  f"enable='between(t,0,1.2)+between(t,{k0:.3f},{k0 + 1.0:.3f})',format=yuv420p[vlk]")
        vlabel = "[vlk]"
        n_in += 1
    if k.get("thanh_tien_trinh") == "co":
        # thanh vàng chạy theo thời gian: dải màu trượt từ ngoài khung vào (overlay tính x từng khung)
        hb = max(4, H // 192)
        inputs += ["-f", "lavfi", "-i", f"color=c=0xFFD600:s={W}x{hb}:r={fps}:d={T:.4f}"]
        fc.append(f"{vlabel}[{n_in}:v]overlay=x='-w+w*t/{T:.4f}':y=0:eof_action=pass[vbar]")
        vlabel = "[vbar]"
        n_in += 1
    mo = lopj.get("mo_nen")
    if mo and mo.get("ds") and mo.get("hop"):
        # r36 kính mờ: làm mờ + bớt màu cảnh, chỉ trong mặt nạ (thẻ / viên kính đang hiện), TRƯỚC khi đặt chữ (PNG phủ lục bảo trong)
        f = W / 1080.0
        hx0, hy0, hx1, hy1 = mo["hop"]
        x0, y0 = max(0, int((hx0 - 4) * f)) // 2 * 2, max(0, int((hy0 - 4) * f)) // 2 * 2
        x1, y1 = min(W, int((hx1 + 6) * f)), min(H, int((hy1 + 6) * f))
        cw, ch = max(2, (x1 - x0) // 2 * 2), max(2, (y1 - y0) // 2 * 2)
        inputs += ["-f", "concat", "-safe", "0", "-i", chuoi_anh(mo["ds"], mo["trong"], tmp, "mo-nen")]
        fc.append(f"{vlabel}split=2[moa][mob]")
        fc.append(f"[mob]crop={cw}:{ch}:{x0}:{y0},gblur=sigma={float(mo.get('sigma') or 26) * f:.2f},"
                  f"hue=s={float(mo.get('bao_hoa') or 0.35):g}[mobl]")
        fc.append(f"[{n_in}:v]scale={W}:{H},crop={cw}:{ch}:{x0}:{y0},format=gray[momk]")
        fc.append("[mobl][momk]alphamerge[mobm]")
        fc.append(f"[moa][mobm]overlay={x0}:{y0}:eof_action=pass[vmo]")
        vlabel = "[vmo]"
        n_in += 1
    for j, l in enumerate(sorted(lop, key=lambda x: x["lop"])):
        nl = f"[o{j}]"
        hu = l.get("hieu_ung")
        if k.get("hoat_hinh") == "khong" and hu in ("nay", "mo"):   # 4/11 tối (POLY Cut "mặc định trơn"): chữ hiện thẳng, không nảy / mờ
            hu = None
        dur = round(l["t1"] - l["t0"], 3)
        if hu in ("nay", "mo") and dur >= 0.4 and l.get("hop"):
            # chữ / sticker hiện có chuyển động: cắt riêng vùng lớp, mờ dần vào-ra 0,12–0,15s; "nay" = nảy 55%→108%→100%
            # (easeOutBack 0,28s) quanh tâm vùng. Lớp là ảnh lặp -loop 1 dài đúng dur, dời giờ tới t0 bằng setpts.
            f = W / 1080.0
            x0, y0, x1, y1 = l["hop"]
            x0, y0 = max(0, int((x0 - 24) * f)), max(0, int((y0 - 24) * f))
            x1, y1 = min(W, int((x1 + 30) * f)), min(H, int((y1 + 36) * f))
            cw, ch = max(2, x1 - x0), max(2, y1 - y0)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{dur:.3f}", "-i", l["png"]]
            ch_ = (f"[{n_in + j}:v]scale={W}:{H},crop={cw}:{ch}:{x0}:{y0},format=rgba,"
                   f"fade=t=in:st=0:d=0.12:alpha=1,fade=t=out:st={max(0.0, dur - 0.15):.3f}:d=0.15:alpha=1")
            if hu == "nay":
                p_ = "min(1,t/0.28)"
                sc = f"(0.55+0.45*(1+2.70158*pow({p_}-1,3)+1.70158*pow({p_}-1,2)))"
                ch_ += f",scale=w='max(2,trunc(iw*{sc}))':h='max(2,trunc(ih*{sc}))':eval=frame"
            ch_ += f",setpts=PTS+{l['t0']:.3f}/TB[pg{j}]"
            fc.append(ch_)
            fc.append(f"{vlabel}[pg{j}]overlay=x='{cx:.1f}-overlay_w/2':y='{cy:.1f}-overlay_h/2':eval=frame:eof_action=pass{nl}")
        else:
            inputs += ["-i", l["png"]]  # 1 khung: overlay tự giữ khung cuối (nhanh gấp ~3 lần -loop 1)
            fc.append(f"[{n_in + j}:v]scale={W}:{H}[pg{j}]")
            # [t0, t1): 2 lớp nối tiếp (cụm phụ đề) không cùng hiện ở khung giáp ranh
            fc.append(f"{vlabel}[pg{j}]overlay=0:0:enable='gte(t,{l['t0']})*lt(t,{l['t1']})'{nl}")
        vlabel = nl
    if pd_seq:   # r36: chuỗi ảnh phụ đề (bộ mẫu mới), trên các lớp chữ khác như phụ đề ASS
        gi_pd = inputs.count("-i")
        inputs += ["-f", "concat", "-safe", "0", "-i", chuoi_anh(pd_seq, lopj["pd_chuoi"]["trong"], tmp, "phu-de")]
        fc.append(f"[{gi_pd}:v]scale={W}:{H},format=rgba[pdq]")
        fc.append(f"{vlabel}[pdq]overlay=0:0:eof_action=pass[vpd]")
        vlabel = "[vpd]"
    if ass:
        fd = lopj.get("font_dir") or ""
        fc.append(f"{vlabel}ass=filename={q(ass)}" + (f":fontsdir={q(fd)}" if fd else "") + "[vass]")
        vlabel = "[vass]"
    # tiếng tách (4/11): các khối trộn vào tiếng clip trước cân tiếng / hạ nhạc / giọng. Không có khối: không thêm gì
    at = am_tach_ds(tl, T)
    if at:
        av, af_, an = am_tach_dau_vao(at, T, inputs.count("-i"), tl["nguon"], tmp, acache)
        inputs += av
        fc += af_
        fc.append(f"{cur_a}{''.join(an)}amix=inputs={len(an) + 1}:duration=first:normalize=0[atc]")
        cur_a = "[atc]"
    alabel = cur_a
    # nhạc nền + cân tiếng (4/11): tn None / hệ số 1 / không nhạc -> không thêm filter nào, các dòng cũ giữ nguyên từng ký tự
    tn = tron_them(tl, T, files, [(audio_src(tl["nguon"][x[0]], tmp, acache), x[1], x[2], x[4]) for x in at] if at else None)
    nh = tn and tn["nhac"]
    khoa = None   # tín hiệu "có người nói" để hạ nhạc (tiếng clip + giọng AI)
    if tn and tn["clip"] != 1.0:
        fc.append(f"{cur_a}volume={tn['clip']:g}[acl]")
        cur_a = alabel = "[acl]"
    if nh and nh["ha"] and nh["khoa_clip"] is not None:
        fc.append(f"{cur_a}asplit=2[abed][akc0]")
        fc.append(f"[akc0]volume={nh['khoa_clip']:g}dB[akc]")
        cur_a = alabel = "[abed]"
        khoa = "[akc]"
    if tl.get("giong"):
        gi = inputs.count("-i")   # = n_in + len(lop) như trước; có khối tiếng tách thì đầu vào giọng đứng sau các khối (4/11)
        inputs += ["-i", tl["giong"]["local"]]
        kg = bool(nh and nh["ha"] and nh["co_giong"])   # giọng cũng là tín hiệu hạ nhạc
        # giọng chuẩn hóa trước để ngưỡng nhún ổn định; nền chỉ hạ khi có giọng, chỗ không giọng giữ tiếng phòng thật
        # giọng ngắn hơn video thì đệm im cho đủ T (sidechain hết sớm sẽ làm treo / cụt tiếng nền)
        fc.append(f"[{gi}:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-2:LRA=7,"
                  f"atrim=0:{T:.4f},apad=whole_dur={T:.4f}," + ("asplit=3[vsc][vmx][vkc]" if kg else "asplit=2[vsc][vmx]"))
        fc.append(f"{cur_a}[vsc]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=300:knee=4:makeup=1[bed]")
        vmx = "[vmx]"
        if tn and tn["giong"] != 1.0:
            fc.append(f"[vmx]volume={tn['giong']:g}[vmg]")
            vmx = "[vmg]"
        fc.append(f"[bed]{vmx}amix=inputs=2:duration=first:normalize=0[amx]")
        alabel = "[amx]"
        if kg:
            if khoa:
                fc.append(f"{khoa}[vkc]amix=inputs=2:duration=first:normalize=0[akv]")
                khoa = "[akv]"
            else:
                khoa = "[vkc]"
    gde = None
    if tl.get("giong_de"):   # r32: giọng AI đọc lại khối tách (doc_lai.py) — không có khoá: không thêm đầu vào / filter nào
        import doc_lai
        gde = doc_lai.dat(tl, T)["dat"]
    if gde:
        vg, fg, lg_, kg_ = doc_lai.dau_vao(gde, T, inputs.count("-i"), doc_lai.gain(gde, FFMPEG, GIONG_LUFS),
                                           tn["giong"] if tn else 1.0, bool(nh and nh["ha"]))
        inputs += vg
        fc += fg
        fc.append(f"{alabel}{lg_}amix=inputs=2:duration=first:normalize=0[agde]")
        alabel = "[agde]"
        if kg_:   # giọng đọc lại cũng là tín hiệu hạ nhạc
            if khoa:
                fc.append(f"{khoa}{kg_}amix=inputs=2:duration=first:normalize=0[akgd]")
                khoa = "[akgd]"
            else:
                khoa = kg_
    if nh:
        vn, fn, ln = nhac_dau_vao(nh, T, inputs.count("-i"))
        inputs += vn
        fc += fn
        if khoa:   # hạ nhạc khi có người nói: bắt theo dải tiếng nói để tiếng ồn trầm / xì không làm nhạc nhún
            fc.append(f"{khoa}highpass=f=200,lowpass=f=4000[khoa]")
            fc.append(f"{ln}[khoa]sidechaincompress={NHAC_HA}[nhh]")
            ln = "[nhh]"
        fc.append(f"{alabel}{ln}amix=inputs=2:duration=first:normalize=0[anh]")
        alabel = "[anh]"
    sfx = am_thanh_dau_vao(tl.get("am_thanh"), T, inputs.count("-i"))   # âm thanh hiệu ứng ngắn (r20): không có khoá -> None, lệnh y hệt
    if sfx:
        inputs += sfx[0]
        fc += sfx[1]
        fc.append(f"{alabel}[sfx]amix=inputs=2:duration=first:normalize=0[asfx]")
        alabel = "[asfx]"
    fc.append(f"{alabel}acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,aresample=48000[aout]")
    fc.append(f"{vlabel}null[vout]")
    mid = os.path.join(tmp, "truoc-loudnorm.mkv")
    cmd = [FFMPEG, "-loglevel", "error", "-y"] + inputs + ["-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]",
           "-t", f"{T:.4f}", "-r", str(fps)]
    enc_cuoi = ma_hoa.chay(lambda v: cmd + v + ["-c:a", "pcm_s16le", "-ar", "48000", mid], run, crf=crf_cuoi, preset=preset_cuoi)
    lufs_vao = loudnorm_2(mid, out)
    ket = {"ra": out, "T": round(T, 3), "so_canh": len(files), "nhap": nhap, "phu_de": "ass" if ass else "png",
           "chuyen_canh": k["chuyen_canh"], "diem_nhan": dn, "lop_phu": lp, "moc_doi_canh": moc_doi,
           "lufs_truoc_chuan": lufs_vao, "ma_hoa": enc_cuoi,
           "on_dinh": sum(1 for s in tl["shots"] if s.get("on_dinh") or tl["nguon"][s["file"]].get("on_dinh")),
           "hdr": any(v.get("hdr") for v in tl["nguon"].values())}
    if at:   # tiếng tách (4/11): số khối đã trộn
        ket["am_tach"] = len(at)
    if gde:   # r32: số câu giọng AI đọc lại đã trộn
        ket["giong_de"] = len(gde)
    if tn:   # nhạc nền / cân tiếng (4/11): chỉ thêm khoá khi kế hoạch có
        ket["tron"] = {"clip": tn["clip"], "giong": tn["giong"], "loi": tn["loi"],
                       "nhac": nh and {k_: nh[k_] for k_ in ("tu", "ha", "gain", "l_ref", "l_nhac")}}
    if sfx:   # r20: chỉ thêm khoá khi kế hoạch có âm thanh hiệu ứng
        ket["am_thanh"] = len(sfx[0]) // 2
    if ma_hoa.bat():   # 10/11: đường card bật (POLY Cut) -> mã hoá / giải mã đã dùng, số lần lùi CPU (app ghi log). Tắt: không thêm khoá
        ket["card"] = ma_hoa.thong_ke()
    if NOI_DO:   # r35: chỉ khi có chỗ nối kiểu mới — [{i, id, giay, khung}] + chỗ lùi xfade (kế hoạch cũ: không có khoá này)
        ket["noi_moi"] = list(NOI_DO)
    return ket


if __name__ == "__main__":
    main()
