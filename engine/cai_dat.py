#!/usr/bin/env python3
"""Cài 1 lần cho engine dựng video trên máy tiệm (Windows). Chạy bằng CAI-DAT.bat (hoặc: python engine\\cai_dat.py).

Làm (bỏ qua phần đã có, tải dở thì tải tiếp):
  1. venv engine\\.venv từ Python 3.12 (%LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe, không có thì py -3.12)
  2. pip install -r engine\\requirements.txt (numpy, Pillow, opencv-python-headless, sherpa-onnx, edge-tts — ghim phiên bản)
  3. ffmpeg + ffprobe bản win64 static của BtbN/FFmpeg-Builds (GitHub, có kiểm sha256) -> engine\\bin\\
  4. máy nghe tiếng Việt sherpa-onnx-zipformer-vi-int8-2025-04-20 (k2-fsa/sherpa-onnx, GitHub) -> engine\\mo-hinh\\
  5. font (google/fonts trên GitHub, đúng danh sách ve_chu.BO_FONT) -> engine\\fonts\\
  6. giọng AI VieNeu-TTS v3 Turbo (25 giọng chạy trên máy): requirements-vieneu.txt + vieneu --no-deps, model (Hugging Face,
     ~540 MB) -> engine\\giong-vieneu\\ — lỗi phần này chỉ là cảnh báo (vẫn dựng được, giọng Microsoft vẫn chạy)
  7. kiểm cuối: import thư viện, ffmpeg đủ bộ lọc, máy nghe nghe được câu mẫu, vẽ chữ + phụ đề ASS bằng ffmpeg với đường dẫn
     có ổ đĩa -> ghi engine\\san-sang.json {ok, python, ffmpeg, ffprobe, mo_hinh, font, luc, thieu:[…], …} cho app đọc.
Tùy chọn: --kiem (chỉ kiểm, không tải / cài) · --khong-tai-ffmpeg · --tai-ffmpeg-win (máy không phải Windows: vẫn tải bản
win64 để thử phần tải / giải nén) · --python <python.exe> (Python dùng tạo venv).
"""
import ast, datetime, hashlib, json, os, re, shutil, subprocess, sys, tarfile, time, zipfile
import urllib.error, urllib.parse, urllib.request

ENGINE = os.path.dirname(os.path.abspath(__file__))
LA_WIN = os.name == "nt"
VENV = os.path.join(ENGINE, ".venv")
VPY = os.path.join(VENV, "Scripts", "python.exe") if LA_WIN else os.path.join(VENV, "bin", "python")
BIN = os.path.join(ENGINE, "bin")
FONTS = os.path.join(ENGINE, "fonts")
MO_HINH_GOC = os.path.join(ENGINE, "mo-hinh")
TEN_MO_HINH = "sherpa-onnx-zipformer-vi-int8-2025-04-20"
TAI = os.path.join(ENGINE, "_tai")  # file tải dở (.part) — tải xong thì giữ zip/tar để khỏi tải lại khi cài lại
URL_FFMPEG = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
URL_MO_HINH = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{TEN_MO_HINH}.tar.bz2"
URL_FONT = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
URL_FFMPEG_DU_PHONG = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"  # khi GitHub hỏng (có .sha256)
BO_LOC_CAN = ("zscale", "tonemap", "vidstabdetect", "vidstabtransform", "ass", "drawtext", "xfade", "acrossfade", "loudnorm",
              "ebur128", "afftdn", "perspective", "gradients", "rgbashift", "freezedetect", "blackdetect", "volumedetect",
              "silencedetect", "sidechaincompress", "vignette", "noise", "setparams", "tpad", "apad")
MA_HOA_CAN = ("libx264", "png", "aac", "pcm_s16le")


def in_(s):
    print(s, flush=True)


def kich_thuoc(n):
    return f"{n / 1e6:.0f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


def tai(url, dich, sha256=None, ten=None):
    """Tải url -> dich (qua dich.part, tải tiếp bằng Range nếu dở). Có sha256 thì kiểm. Trả đường dẫn."""
    ten = ten or os.path.basename(dich)
    if os.path.isfile(dich) and (not sha256 or bam(dich) == sha256):
        in_(f"    {ten}: đã có, bỏ qua")
        return dich
    os.makedirs(os.path.dirname(dich), exist_ok=True)
    part = dich + ".part"
    for lan in range(1, 6):
        da = os.path.getsize(part) if os.path.exists(part) else 0
        req = urllib.request.Request(url, headers={"User-Agent": "poly-dung-video-cai-dat"})
        if da:
            req.add_header("Range", f"bytes={da}-")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                if da and r.status != 206:  # máy chủ không nhận tải tiếp: tải lại từ đầu
                    da = 0
                tong = int(r.headers.get("Content-Length") or 0) + da
                with open(part, "ab" if da else "wb") as f:
                    moc = da
                    while True:
                        blk = r.read(1 << 20)
                        if not blk:
                            break
                        f.write(blk)
                        da += len(blk)
                        if da - moc >= max(5 << 20, tong // 10) or (tong and da == tong):
                            moc = da
                            pt = f" ({100 * da // tong}%)" if tong else ""
                            in_(f"    {ten}: {kich_thuoc(da)}{('/' + kich_thuoc(tong)) if tong else ''}{pt}")
            break
        except (OSError, urllib.error.URLError) as e:
            in_(f"    {ten}: lỗi mạng lần {lan} ({e}) — thử tiếp sau 5 giây")
            time.sleep(5)
    else:
        raise RuntimeError(f"không tải được {url}")
    if sha256 and bam(part) != sha256:
        os.remove(part)
        raise RuntimeError(f"{ten}: sha256 không khớp — đã xóa bản tải, chạy lại để tải lại")
    os.replace(part, dich)
    return dich


def bam(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def doc_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "poly-dung-video-cai-dat"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def chay(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)


# ---------------------------------------------------------------- 1. Python + venv
def tim_python(chi_dinh=None):
    ung = []
    if chi_dinh:
        ung.append([chi_dinh])
    if LA_WIN:
        ung.append([os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python312", "python.exe")])
        ung.append(["py", "-3.12"])
        ung.append(["py", "-3"])
    else:
        ung += [["python3.12"], ["python3"]]
    ung.append([sys.executable])
    for c in ung:
        if len(c) == 1 and os.path.isabs(c[0]) and not os.path.isfile(c[0]):
            continue
        try:
            r = chay(c + ["-c", "import sys; print('%d.%d' % sys.version_info[:2]); print(sys.executable)"], timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0:
            ver, exe = r.stdout.split()[:2]
            if ver == "3.12" or (chi_dinh and c == [chi_dinh]):
                return exe, ver
    for c in ung:  # không có 3.12: nhận 3.10–3.13 (bánh xe đủ), báo
        try:
            r = chay(c + ["-c", "import sys; print('%d.%d' % sys.version_info[:2]); print(sys.executable)"], timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if r.returncode == 0:
            ver, exe = r.stdout.split()[:2]
            if ver in ("3.10", "3.11", "3.13"):
                return exe, ver
    return None, None


def buoc_venv(py, kiem):
    if os.path.isfile(VPY):
        r = chay([VPY, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], timeout=60)
        if r.returncode == 0:
            in_(f"    venv: đã có (Python {r.stdout.strip()})")
            return True
        in_("    venv hỏng: tạo lại")
        if not kiem:
            shutil.move(VENV, VENV + f".hong-{int(time.time())}")
    if kiem:
        return False
    r = chay([py, "-m", "venv", VENV], timeout=600)
    if r.returncode != 0:
        raise RuntimeError("không tạo được venv: " + (r.stderr or r.stdout)[-500:])
    in_(f"    venv: đã tạo {VENV}")
    return True


def buoc_pip(kiem):
    req = os.path.join(ENGINE, "requirements.txt")
    if kiem:
        return
    in_("    pip: cài thư viện (lần đầu ~2–4 phút, ~120 MB)…")
    r = chay([VPY, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-q", "-r", req], timeout=3600)
    if r.returncode != 0:
        raise RuntimeError("pip install lỗi:\n" + (r.stderr or r.stdout)[-1500:])
    in_("    pip: xong")


# ---------------------------------------------------------------- 3. ffmpeg
def chon_ban_ffmpeg():
    """Từ checksums.sha256 của bản 'latest' BtbN: bản ổn định mới nhất ffmpeg-n<X.Y>-latest-win64-gpl-<X.Y>.zip, không có
    thì master. Trả (tên file, sha256)."""
    ds = {}
    for dong in doc_url(URL_FFMPEG + "checksums.sha256").splitlines():
        p = dong.split()
        if len(p) == 2:
            ds[p[1].lstrip("*")] = p[0].lower()
    on_dinh = []
    for n in ds:
        m = re.fullmatch(r"ffmpeg-n(\d+)\.(\d+)-latest-win64-gpl-\1\.\2\.zip", n)
        if m:
            on_dinh.append(((int(m.group(1)), int(m.group(2))), n))
    if on_dinh:
        n = max(on_dinh)[1]
        return n, ds[n]
    n = "ffmpeg-master-latest-win64-gpl.zip"
    if n in ds:
        return n, ds[n]
    raise RuntimeError("checksums.sha256 của BtbN không có bản win64-gpl")


def giai_ffmpeg(zp):
    os.makedirs(BIN, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        da = []
        for m in z.infolist():
            b = os.path.basename(m.filename).lower()
            if b in ("ffmpeg.exe", "ffprobe.exe") and "/bin/" in "/" + m.filename.replace("\\", "/").lower():
                tam = os.path.join(BIN, b + ".part")
                with z.open(m) as s, open(tam, "wb") as d:
                    shutil.copyfileobj(s, d, 1 << 20)
                os.replace(tam, os.path.join(BIN, b))
                da.append(b)
    if sorted(da) != ["ffmpeg.exe", "ffprobe.exe"]:
        raise RuntimeError(f"zip {os.path.basename(zp)} không có đủ bin/ffmpeg.exe + bin/ffprobe.exe")


def buoc_ffmpeg(kiem, tai_win=False):
    exe = ".exe" if LA_WIN else ""
    ff, fp = os.path.join(BIN, "ffmpeg" + exe), os.path.join(BIN, "ffprobe" + exe)
    if os.path.isfile(ff) and os.path.isfile(fp) and chay([ff, "-version"], timeout=60).returncode == 0:
        in_("    ffmpeg: đã có " + chay([ff, "-version"], timeout=60).stdout.split("\n")[0][:80])
        return ff, fp
    if not LA_WIN and (kiem or not tai_win):
        w = shutil.which("ffmpeg"), shutil.which("ffprobe")
        in_(f"    ffmpeg: máy không phải Windows — dùng bản của hệ thống {w[0]}")
        return w
    if kiem:
        return None, None
    try:
        ten, sha = chon_ban_ffmpeg()
        in_(f"    ffmpeg: tải {ten} (BtbN/FFmpeg-Builds, ~200 MB)")
        zp = tai(URL_FFMPEG + ten, os.path.join(TAI, ten), sha)
    except (RuntimeError, OSError, urllib.error.URLError) as e:
        in_(f"    ffmpeg: GitHub lỗi ({e}) — thử bản dự phòng gyan.dev")
        sha = doc_url(URL_FFMPEG_DU_PHONG + ".sha256").split()[0].strip().lower()
        zp = tai(URL_FFMPEG_DU_PHONG, os.path.join(TAI, "ffmpeg-release-essentials.zip"), sha)
    giai_ffmpeg(zp)
    in_(f"    ffmpeg: đã giải nén vào {BIN}")
    if not LA_WIN:
        w = shutil.which("ffmpeg"), shutil.which("ffprobe")
        in_(f"    (máy không phải Windows: không chạy được .exe — kiểm tiếp bằng ffmpeg hệ thống {w[0]})")
        return w
    return ff, fp


def kiem_ffmpeg(ff):
    thieu = []
    if not ff:
        return ["ffmpeg"]
    loc = chay([ff, "-hide_banner", "-filters"], timeout=60).stdout
    co = {p[1] for p in (x.split() for x in loc.splitlines()) if len(p) >= 2}
    thieu += [f"bộ lọc ffmpeg {x}" for x in BO_LOC_CAN if x not in co]
    ma = chay([ff, "-hide_banner", "-encoders"], timeout=60).stdout
    co_ma = {p[1] for p in (x.split() for x in ma.splitlines()) if len(p) >= 2}
    thieu += [f"bộ mã ffmpeg {x}" for x in MA_HOA_CAN if x not in co_ma]
    return thieu


# ---------------------------------------------------------------- 4. máy nghe
def buoc_mo_hinh(kiem):
    d = os.path.join(MO_HINH_GOC, TEN_MO_HINH)
    can = ("tokens.txt",)
    if os.path.isdir(d) and all(os.path.isfile(os.path.join(d, x)) for x in can) and \
            sum(1 for x in os.listdir(d) if x.endswith(".onnx")) >= 3:
        in_(f"    máy nghe: đã có {d}")
        return d
    if kiem:
        return None
    tp = tai(URL_MO_HINH, os.path.join(TAI, TEN_MO_HINH + ".tar.bz2"), ten="máy nghe (~60 MB)")
    in_("    máy nghe: giải nén…")
    tam = os.path.join(MO_HINH_GOC, "_giai")
    shutil.rmtree(tam, ignore_errors=True)
    os.makedirs(tam, exist_ok=True)
    with tarfile.open(tp, "r:bz2") as tf:
        for m in tf.getmembers():
            if m.issym() or m.islnk() or m.name.startswith(("/", "\\")) or ".." in m.name.replace("\\", "/").split("/"):
                raise RuntimeError(f"gói máy nghe có mục lạ: {m.name}")
        try:
            tf.extractall(tam, filter="data")
        except TypeError:  # Python < 3.12
            tf.extractall(tam)
    if os.path.isdir(d):
        shutil.move(d, d + f".cu-{int(time.time())}")
    shutil.move(os.path.join(tam, TEN_MO_HINH), d)
    shutil.rmtree(tam, ignore_errors=True)
    in_(f"    máy nghe: xong {d}")
    return d


# ---------------------------------------------------------------- 5. font
def danh_sach_font():
    """Đọc BO_FONT trong ve_chu.py (không import: venv có thể chưa có Pillow) -> [(file, thư mục google/fonts)]."""
    with open(os.path.join(ENGINE, "ve_chu.py"), encoding="utf-8") as f:
        cay = ast.parse(f.read())
    bo = None
    for n in cay.body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BO_FONT" for t in n.targets):
            bo = ast.literal_eval(n.value)
    if not bo:
        raise RuntimeError("không đọc được BO_FONT trong ve_chu.py")
    out = {}
    for b in bo.values():
        dirs = b["thu_muc"].split("|")
        for vai in ("Black", "ExtraBold", "Bold"):
            fn = b[vai][0]
            goc = re.split(r"[-\[]", fn)[0].lower()
            d = goc if goc in dirs else dirs[0]
            out[fn] = d
    for fn in ("BeVietnamPro-Black.ttf", "BeVietnamPro-ExtraBold.ttf", "BeVietnamPro-Bold.ttf"):
        out.setdefault(fn, "bevietnampro")
    return sorted(out.items())


def buoc_font(kiem):
    os.makedirs(FONTS, exist_ok=True)
    thieu = []
    for fn, d in danh_sach_font():
        p = os.path.join(FONTS, fn)
        if os.path.isfile(p) and os.path.getsize(p) > 10000:
            continue
        if kiem:
            thieu.append(fn)
            continue
        url = URL_FONT + d + "/" + urllib.parse.quote(fn)
        try:
            tai(url, p, ten="font " + fn)
            with open(p, "rb") as f:
                dau = f.read(4)
            if dau not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
                os.remove(p)
                raise RuntimeError("không phải file font")
        except (RuntimeError, OSError) as e:
            in_(f"    font {fn}: lỗi {e}")
            thieu.append(fn)
    in_(f"    font: {len(danh_sach_font()) - len(thieu)}/{len(danh_sach_font())} file trong {FONTS}")
    return thieu


# ---------------------------------------------------------------- 6. giọng VieNeu
VIENEU_DIR = os.path.join(ENGINE, "giong-vieneu")
TAI_VIENEU_PY = r'''
import os, sys
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
from huggingface_hub import hf_hub_download
from vieneu._v3_turbo_engine import onnx_runtime_lite as m
goc = sys.argv[1]
for f in m._GRAPH_FILES:
    hf_hub_download(m._V3_REPO, f, subfolder="onnx_update", local_dir=os.path.join(goc, "v3"))
    print("    model: " + f, flush=True)
for f in m._CODEC_FILES:
    hf_hub_download(m._CODEC_REPO, f, local_dir=os.path.join(goc, "codec"))
    print("    codec: " + f, flush=True)
print("XONG")
'''
THU_VIENEU_PY = r'''
import os, sys
sys.path.insert(0, sys.argv[1])
os.environ["POLY_VIENEU_DIR"] = sys.argv[2]
import giong
w = giong.nap_vieneu().infer("Chào anh em.", voice="Adam")
print("OK %.1f" % (len(w) / 48000.0))
'''


def vieneu_co_model():
    return (os.path.isfile(os.path.join(VIENEU_DIR, "codec", "moss_audio_tokenizer_decode_full.onnx"))
            and os.path.isfile(os.path.join(VIENEU_DIR, "v3", "onnx_update", "vieneu_backbone_shared.data")))


def buoc_vieneu(kiem):
    """Thư viện (không kéo gradio / librosa) + model vào giong-vieneu\\ + đọc thử 1 câu. Trả True khi dùng được."""
    if not os.path.isfile(VPY):
        raise RuntimeError("chưa có venv")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", HF_HUB_DISABLE_TELEMETRY="1")
    if not kiem:
        r = chay([VPY, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-q", "-r",
                  os.path.join(ENGINE, "requirements-vieneu.txt")], timeout=3600)
        if r.returncode != 0:
            raise RuntimeError("pip (thư viện VieNeu) lỗi: " + (r.stderr or r.stdout)[-800:])
        r = chay([VPY, "-m", "pip", "install", "--disable-pip-version-check", "--no-input", "-q", "--no-deps", "vieneu==3.8.3"],
                 timeout=1200)
        if r.returncode != 0:
            raise RuntimeError("pip vieneu lỗi: " + (r.stderr or r.stdout)[-800:])
        in_("    thư viện VieNeu: xong")
        if not vieneu_co_model():
            in_("    tải model giọng (~540 MB, lần đầu vài phút)…")
        os.makedirs(TAI, exist_ok=True)
        kp = os.path.join(TAI, "tai_vieneu.py")
        with open(kp, "w", encoding="utf-8") as f:
            f.write(TAI_VIENEU_PY)
        r = chay([VPY, kp, VIENEU_DIR], timeout=7200, env=env)
        if r.returncode != 0 or "XONG" not in r.stdout:
            raise RuntimeError("tải model giọng lỗi (cần mạng tới huggingface.co): " + (r.stderr or r.stdout)[-800:])
    if not vieneu_co_model():
        return False
    kp = os.path.join(TAI, "thu_vieneu.py")
    os.makedirs(TAI, exist_ok=True)
    with open(kp, "w", encoding="utf-8") as f:
        f.write(THU_VIENEU_PY)
    r = chay([VPY, kp, ENGINE, VIENEU_DIR], timeout=600, env=dict(env, HF_HUB_OFFLINE="1"))
    dong = [x for x in r.stdout.strip().splitlines() if x.startswith("OK")]
    if r.returncode != 0 or not dong:
        raise RuntimeError("đọc thử giọng VieNeu lỗi: " + (r.stderr or r.stdout)[-800:])
    in_(f"    giọng VieNeu đọc thử: được ({dong[-1][3:]} giây tiếng)")
    return True


# ---------------------------------------------------------------- 7. kiểm cuối
KIEM_PY = r'''
import json, os, sys, wave
sys.path.insert(0, sys.argv[1])
out = {"thu_vien": {}, "loi": []}
for m in ("numpy", "PIL", "cv2", "sherpa_onnx", "edge_tts"):
    try:
        mod = __import__(m)
        out["thu_vien"][m] = getattr(mod, "__version__", "?")
    except Exception as e:
        out["loi"].append(f"import {m}: {e}")
try:
    from PIL import ImageFont
    f = ImageFont.truetype(os.path.join(sys.argv[3], "BeVietnamPro-Black.ttf"), 40)
    f.getbbox("Thử chữ Việt: ệ ợ ữ")
    v = ImageFont.truetype(os.path.join(sys.argv[3], "Montserrat[wght].ttf"), 40)
    v.set_variation_by_axes([900])
except Exception as e:
    out["loi"].append(f"vẽ chữ: {e}")
md = sys.argv[2]
try:
    import numpy as np, re, sherpa_onnx
    f = lambda pat: next(os.path.join(md, x) for x in sorted(os.listdir(md)) if re.match(pat, x))
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f(r"encoder.*\.onnx$"), decoder=f(r"decoder.*\.onnx$"),
        joiner=f(r"joiner.*\.onnx$"), tokens=os.path.join(md, "tokens.txt"), num_threads=2, decoding_method="greedy_search")
    w = os.path.join(md, "test_wavs", "0.wav")
    if os.path.isfile(w):
        with wave.open(w) as g:
            x = np.frombuffer(g.readframes(g.getnframes()), np.int16).astype(np.float32) / 32768
            sr = g.getframerate()
        s = rec.create_stream(); s.accept_waveform(sr, x); rec.decode_stream(s)
        out["nghe_thu"] = s.result.text[:80]
        if not s.result.text.strip():
            out["loi"].append("máy nghe không nghe ra chữ nào ở câu mẫu")
except Exception as e:
    out["loi"].append(f"máy nghe: {e}")
print(json.dumps(out, ensure_ascii=False))
'''


def kiem_ve_ffmpeg(ff):
    """Vẽ chữ (drawtext + fontfile) và phụ đề ASS (libass + fontsdir) bằng đúng cách thoát đường dẫn của engine (chung.loc),
    trên thư mục _tai\\thử chữ ổ đĩa (có dấu cách, chữ Việt). Lỗi thì trả câu báo."""
    sys.path.insert(0, ENGINE)
    import chung
    d = os.path.join(TAI, "thử ffmpeg")
    os.makedirs(d, exist_ok=True)
    ass = os.path.join(d, "phụ đề.ass")
    with open(ass, "w", encoding="utf-8") as f:
        f.write("[Script Info]\nScriptType: v4.00+\nPlayResX: 320\nPlayResY: 240\n\n[V4+ Styles]\nFormat: Name, Fontname, "
                "Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
                "Style: Pop,Be Vietnam Pro Black,40,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,0,0,1,4,0,2,10,10,"
                "20,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                "Dialogue: 0,0:00:00.00,0:00:01.00,Pop,,0,0,0,,THỬ PHỤ ĐỀ\n")
    ra = os.path.join(d, "khung.png")
    vf = (f"drawtext={chung.font_drawtext()}text='Thử':fontsize=30:fontcolor=yellow:x=10:y=10,"
          f"ass=filename={chung.loc(ass)}:fontsdir={chung.loc(chung.FONT_DIR)}")
    r = chay([ff, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=0.5",
              "-vf", vf, "-frames:v", "1", ra], timeout=120)
    if r.returncode != 0 or not os.path.isfile(ra):
        return "ffmpeg vẽ chữ / phụ đề lỗi: " + (r.stderr or "")[-400:]
    return None


def main():
    """thieu = tên ngắn tiếng Việt (app hiện cho anh); chi_tiet = lỗi đầy đủ."""
    a = sys.argv[1:]
    kiem = "--kiem" in a
    py_cd = a[a.index("--python") + 1] if "--python" in a else None
    t0 = time.time()
    in_("=== Cài engine dựng video Poly (" + ENGINE + ") ===")
    thieu, chi_tiet, canh_bao, kq = [], [], [], {}

    def hong(ten, ct=None):
        thieu.append(ten)
        if ct:
            chi_tiet.append(f"{ten}: {ct}")
            in_(f"    LỖI: {ct}")
    # 1
    in_("[1/7] Python 3.12 + venv")
    py, ver = tim_python(py_cd)
    if not py and not os.path.isfile(VPY):
        hong("Python 3.12", "không thấy Python 3.12 — anh cài Python 3.12 (python.org) rồi chạy lại")
    else:
        if ver and ver != "3.12":
            canh_bao.append(f"đang dùng Python {ver} (nên 3.12)")
        in_(f"    Python: {py} ({ver})")
        try:
            if not buoc_venv(py, kiem):
                hong("môi trường Python (venv)")
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            hong("môi trường Python (venv)", str(e))
    # 2
    in_("[2/7] Thư viện Python")
    if os.path.isfile(VPY):
        try:
            buoc_pip(kiem)
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            hong("thư viện Python", str(e))
    # 3
    in_("[3/7] ffmpeg + ffprobe")
    ff = fp = None
    try:
        if "--khong-tai-ffmpeg" in a:
            ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
        else:
            ff, fp = buoc_ffmpeg(kiem, "--tai-ffmpeg-win" in a)
    except (RuntimeError, OSError, urllib.error.URLError, zipfile.BadZipFile) as e:
        chi_tiet.append(f"ffmpeg: {e}")
        in_(f"    LỖI: {e}")
    if not ff or not fp:
        hong("ffmpeg")
    else:
        t = kiem_ffmpeg(ff)
        if t:
            hong("ffmpeg thiếu bộ lọc", ", ".join(t))
    # 4
    in_("[4/7] Máy nghe tiếng Việt (sherpa-onnx)")
    md = None
    try:
        md = buoc_mo_hinh(kiem)
    except (RuntimeError, OSError, tarfile.TarError, urllib.error.URLError) as e:
        chi_tiet.append(f"máy nghe: {e}")
        in_(f"    LỖI: {e}")
    if not md:
        hong("máy nghe tiếng Việt")
    # 5
    in_("[5/7] Font")
    try:
        tf = buoc_font(kiem)
    except (RuntimeError, OSError) as e:
        chi_tiet.append(f"font: {e}")
        tf = ["font"]
    if tf:
        hong("font chữ", ", ".join(tf))
    # 6
    in_("[6/7] Giọng AI VieNeu (25 giọng, lần đầu tải ~540 MB)")
    vieneu = False
    try:
        vieneu = buoc_vieneu(kiem)
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        canh_bao.append(f"giọng VieNeu chưa có: {e}")
        in_(f"    CHƯA ĐƯỢC (vẫn dựng được, giọng Microsoft vẫn chạy): {str(e)[-300:]}")
    in_("[7/7] Kiểm cuối")
    if os.path.isfile(VPY):
        os.makedirs(TAI, exist_ok=True)
        kp = os.path.join(TAI, "kiem_thu_vien.py")
        with open(kp, "w", encoding="utf-8") as f:
            f.write(KIEM_PY)
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        try:
            r = chay([VPY, kp, ENGINE, md or "", FONTS], timeout=600, env=env)
            kq = json.loads(r.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError, OSError, subprocess.SubprocessError) as e:
            kq = {"loi": [f"import: kiểm thư viện không chạy được ({e})"]}
        for x in kq.get("loi") or []:
            ten = "máy nghe tiếng Việt" if x.startswith("máy nghe") else "vẽ chữ (Pillow / font)" if x.startswith("vẽ chữ") \
                else "thư viện Python"
            hong(ten, x)
        if kq.get("thu_vien"):
            in_("    thư viện: " + ", ".join(f"{k} {v}" for k, v in kq["thu_vien"].items()))
        if kq.get("nghe_thu"):
            in_(f"    máy nghe thử: \"{kq['nghe_thu']}\"")
    else:
        hong("môi trường Python (venv)")
    if ff:
        try:
            loi = kiem_ve_ffmpeg(ff)
        except (OSError, subprocess.SubprocessError) as e:
            loi = str(e)
        if loi:
            hong("ffmpeg vẽ chữ / phụ đề", loi)
        else:
            in_("    ffmpeg vẽ chữ + phụ đề ASS: được")
    thieu = list(dict.fromkeys(thieu))
    ss = {
        "ok": not thieu, "python": VPY if os.path.isfile(VPY) else None, "ffmpeg": ff, "ffprobe": fp,
        "mo_hinh": md, "font": FONTS, "luc": datetime.datetime.now().isoformat(timespec="seconds"), "thieu": thieu,
        "chi_tiet": chi_tiet, "canh_bao": canh_bao, "thu_vien": kq.get("thu_vien"), "engine": ENGINE,
        "vieneu": {"ok": bool(vieneu), "thu_muc": VIENEU_DIR},
        "path_dau": [os.path.dirname(VPY), BIN],
        "env": {"POLY_ENGINE": ENGINE, "POLY_FFMPEG_DIR": os.path.dirname(ff) if ff else None, "POLY_MO_HINH": md,
                "POLY_FONT_DIR": FONTS, "PYTHONUTF8": "1"},
    }
    with open(os.path.join(ENGINE, "san-sang.json"), "w", encoding="utf-8") as f:
        json.dump(ss, f, ensure_ascii=False, indent=1)
    in_(f"=== {'SẴN SÀNG' if ss['ok'] else 'CHƯA XONG — thiếu: ' + ', '.join(thieu)} ({time.time() - t0:.0f}s) ===")
    in_("Ghi " + os.path.join(ENGINE, "san-sang.json"))
    sys.exit(0 if ss["ok"] else 1)


if __name__ == "__main__":
    main()
