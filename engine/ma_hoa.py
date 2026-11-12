#!/usr/bin/env python3
"""Chọn bộ mã hoá hình (POLY Cut, 3/11; ý học từ trình sửa Concat, code tự viết) + giải mã clip bằng card (10/11).

Có card đồ hoạ thì mã hoá bằng card: NVIDIA (nvenc) -> Intel (qsv) -> AMD (amf). Không có / lỗi thì libx264 / libx265 như cũ.
- Dò 1 lần: ffmpeg -encoders + mã hoá thử 8 khung 1080x1920 đúng tham số sẽ dùng; nhớ ở _cache/ma-hoa.json
  theo đường dẫn + ngày sửa + cỡ file ffmpeg (đổi ffmpeg / cập nhật driver làm hỏng thì dò lại sau 7 ngày).
- Đang dựng mà bước mã hoá bằng card lỗi: làm lại bước đó bằng CPU (ve_cpu), các bước sau dùng CPU luôn;
  lỗi 2 lần thì tắt card cho các lần xuất sau (ghi vào cache, dò lại sau 7 ngày).
- Ép: biến môi trường POLY_MA_HOA = cpu | auto | h264_nvenc | h264_qsv | h264_amf. Trống = cpu (bản 1 Poly Dựng Video, Claude dựng:
  lệnh ffmpeg y như trước). POLY Cut (sua_tay) đặt "auto" từ 10/11 (config.json "ma_hoa": "cpu" để tắt).
- CRF 0 (lưu không mất của chất lượng "cao") luôn dùng libx264: card không làm được không mất gọn.

Giải mã bằng card (10/11, anh: "app exe sẽ tự dò và sài card máy được cài"; chỗ nặng nhất là clip iPhone HEVC 4K 10-bit):
- Dò cùng lúc với bộ mã hoá, nhớ chung _cache/ma-hoa.json (khoá "giai_ma"): giải mã THẬT 2 clip mẫu (H.264 8-bit + HEVC 10-bit,
  tạo 1 lần bằng CPU) bằng từng loại -hwaccel theo thứ tự Windows: d3d11va -> cuda -> qsv -> dxva2 (máy khác: cuda -> vaapi -> qsv).
  Ưu tiên loại giải mã được cả HEVC 10-bit; ffmpeg báo "Failed setup for format" (card không hỗ trợ, tự lùi CPU) = coi như không được.
- Chỉ đặt -hwaccel trước -i của CLIP video (vao()); khung tải về CPU (không -hwaccel_output_format) nên chuỗi filter cũ chạy y nguyên.
- Lệnh có -hwaccel lỗi: chạy lại y lệnh đó bỏ -hwaccel (chay_gm); CPU được thì ghi card giải mã hỏng (lượt này thôi dùng; lỗi 2 lần
  trong 7 ngày thì tắt như mã hoá).
- Bật khi POLY_GIAI_MA = auto | d3d11va | cuda | qsv | dxva2 | vaapi, hoặc POLY_GIAI_MA trống mà POLY_MA_HOA bật (khác cpu / trống).
  POLY_GIAI_MA = cpu: tắt riêng phần giải mã.
- App gửi tên + phiên bản driver card (--card): khác lần dò trước (đổi card / cập nhật driver) thì dò lại ngay.
- Nhiều tiến trình cùng cần dò: chỉ 1 tiến trình dò (khoá _cache/ma-hoa.dang-do), tiến trình khác dùng CPU cho lần đó, không chờ.

Dùng:  python ma_hoa.py            in bộ mã hoá / giải mã đang chọn
       python ma_hoa.py --do-lai   bỏ nhớ cũ, dò lại
       python ma_hoa.py --json [--card=<json [{ten, driver}]>] [--do-lai]   (app gọi lúc mở: 1 dòng JSON cuối)
"""
import json, os, re, subprocess, sys, tempfile, time
from chung import FFMPEG

KW = {"creationflags": 0x08000000} if os.name == "nt" else {}   # Windows: không bật cửa sổ đen
UU_TIEN = {"h264": ["h264_nvenc", "h264_qsv", "h264_amf"], "hevc": ["hevc_nvenc", "hevc_qsv", "hevc_amf"]}
CPU = {"h264": "libx264", "hevc": "libx265"}
TEN = {"nvenc": "card NVIDIA", "qsv": "card Intel", "amf": "card AMD", "libx264": "CPU", "libx265": "CPU"}
HAN_DO = 7 * 86400
_hong = set()   # bộ mã hoá lỗi trong lượt chạy này
TAT = ("cpu", "khong", "0", "off", "tat", "false")
GIAI_MA = ["d3d11va", "cuda", "qsv", "dxva2"] if os.name == "nt" else ["cuda", "vaapi", "qsv"]
GIAI_MA_MOI = ("d3d11va", "cuda", "qsv", "dxva2", "vaapi", "videotoolbox")   # tên ép được qua POLY_GIAI_MA
_hong_gm = set()   # loại giải mã bằng card lỗi trong lượt chạy này
DA = {"ma_hoa": [], "ma_hoa_lui": 0, "giai_ma": None, "giai_ma_lan": 0, "giai_ma_ok": 0, "giai_ma_lui": 0}   # lượt chạy này (app ghi log mỗi lần xuất)
KHOA_HAN = 300   # giây: khoá "đang dò" cũ hơn chừng này = tiến trình dò đã chết


def _cache_path():
    for d in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cache"), os.path.join(tempfile.gettempdir(), "poly-cut")):
        try:
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, "ma-hoa.json")
            with open(p, "a"):
                pass
            return p
        except OSError:
            continue
    return None


def _dau_ffmpeg():
    try:
        st = os.stat(FFMPEG)
        return "%s|%d|%d" % (FFMPEG, int(st.st_mtime), st.st_size)
    except OSError:
        return FFMPEG


def _doc_tho():
    """File nhớ, không xét hạn (giữ tên card / dấu driver qua các lần dò lại)."""
    try:
        d = json.load(open(_cache_path(), encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _doc():
    p = _cache_path()
    try:
        d = json.load(open(p, encoding="utf-8"))
        if d.get("ffmpeg") == _dau_ffmpeg() and time.time() - d.get("luc", 0) < HAN_DO:
            return d
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def _ghi(d):
    p = _cache_path()
    if not p:
        return
    try:
        tmp = p + ".%d.tmp" % os.getpid()
        json.dump(d, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(tmp, p)
    except OSError:
        pass


def tham_so(enc, crf, preset="veryfast"):
    """Tham số -c:v … cho 1 bộ mã hoá, chất lượng tương đương libx264 -crf <crf>. preset: veryfast | fast | medium."""
    crf = int(crf)
    cham = preset in ("medium", "slow")
    if enc.endswith("_nvenc"):
        return ["-c:v", enc, "-preset", "p6" if cham else "p4", "-tune", "hq", "-rc", "vbr", "-cq", str(max(1, crf - 1)), "-b:v", "0",
                "-spatial-aq", "1", "-pix_fmt", "yuv420p"] + (["-profile:v", "high"] if enc.startswith("h264") else [])
    if enc.endswith("_qsv"):
        return ["-c:v", enc, "-preset", "medium" if cham else "veryfast", "-global_quality", str(max(1, crf)), "-pix_fmt", "nv12"]
    if enc.endswith("_amf"):
        q = str(max(1, crf + 1))
        return ["-c:v", enc, "-quality", "quality" if cham else "balanced", "-rc", "cqp", "-qp_i", q, "-qp_p", q] + \
               (["-qp_b", q] if enc.startswith("h264") else []) + ["-pix_fmt", "nv12"]
    if enc == "libx265":
        return ["-c:v", "libx265", "-preset", "medium" if cham else "fast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-x265-params", "log-level=error"]
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p"]


def _thu(enc):
    """Mã hoá thử 8 khung 1080x1920 bằng đúng tham số sẽ dùng. -> (được?, lỗi ngắn)."""
    try:
        r = subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1080x1920:r=30", "-frames:v", "8"]
                           + tham_so(enc, 19) + ["-f", "null", "-"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=40, **KW)
        return r.returncode == 0, (r.stderr or "").strip()[-200:]
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)[:200]


# ------------------------------------------------------------------ giải mã bằng card (10/11)
def _mau_giai_ma():
    """Clip mẫu để giải mã thử (tạo 1 lần bằng CPU, để cạnh file nhớ): {"h264": 8-bit, "hevc10": HEVC 10-bit như iPhone HDR}."""
    p = _cache_path()
    d = os.path.dirname(p) if p else tempfile.gettempdir()
    out = {}
    for ten, ma in (("h264", ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p"]),
                    ("hevc10", ["-c:v", "libx265", "-preset", "ultrafast", "-pix_fmt", "yuv420p10le", "-x265-params", "log-level=error"])):
        f = os.path.join(d, "mau-giai-ma-%s.mp4" % ten)
        if not (os.path.isfile(f) and os.path.getsize(f) > 1000):
            tam = f + ".%d.mp4" % os.getpid()
            try:
                subprocess.run([FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30", "-frames:v", "8"] + ma + [tam],
                               capture_output=True, timeout=90, **KW)
                if os.path.isfile(tam) and os.path.getsize(tam) > 1000:
                    os.replace(tam, f)
            except (OSError, subprocess.SubprocessError):
                pass
            if os.path.isfile(tam):
                try:
                    os.remove(tam)
                except OSError:
                    pass
        if os.path.isfile(f) and os.path.getsize(f) > 1000:
            out[ten] = f
    return out


def _thu_giai_ma(hw, f):
    """Giải mã thật 8 khung của clip mẫu bằng -hwaccel hw (khung tải về CPU như lúc dựng). -> (được?, lỗi ngắn)."""
    try:
        r = subprocess.run([FFMPEG, "-v", "warning", "-hwaccel", hw, "-i", f, "-frames:v", "8", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40, **KW)
        loi = (r.stderr or "").strip()
        if r.returncode:
            return False, loi[-200:] or "lỗi"
        if re.search(r"Failed setup for format|hwaccel initiali[sz]ation returned error|Device creation failed", loi, re.I):
            return False, loi[-200:]   # card không giải mã được loại này: ffmpeg tự lùi CPU (không phải lỗi) -> coi như không được
        return True, ""
    except (OSError, subprocess.SubprocessError) as e:
        return False, str(e)[:200]


def _do_giai_ma():
    """-> {"hw": loại dùng | None, "h264": loại | None, "hevc10": loại | None, "thu": {"loại:codec": lỗi | ""}}."""
    kq = {"hw": None, "h264": None, "hevc10": None, "thu": {}}
    try:
        ds = subprocess.run([FFMPEG, "-hide_banner", "-hwaccels"], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", timeout=20, **KW).stdout
    except (OSError, subprocess.SubprocessError):
        ds = ""
    co = {w.strip() for w in ds.splitlines()[1:] if w.strip()}
    if not any(hw in co for hw in GIAI_MA):
        return kq
    mau = _mau_giai_ma()
    if "h264" not in mau:
        return kq
    du_phong = None
    for hw in GIAI_MA:
        if hw not in co:
            continue
        ok, loi = _thu_giai_ma(hw, mau["h264"])
        kq["thu"][hw + ":h264"] = "" if ok else loi
        if not ok:
            continue
        kq["h264"] = kq["h264"] or hw
        if "hevc10" not in mau:
            kq["hw"] = hw
            break
        ok, loi = _thu_giai_ma(hw, mau["hevc10"])
        kq["thu"][hw + ":hevc10"] = "" if ok else loi
        if ok:
            kq["hevc10"] = kq["hw"] = hw
            break
        du_phong = du_phong or hw   # giải mã được H.264 mà không được HEVC 10-bit: dùng nếu không có loại nào tốt hơn
    kq["hw"] = kq["hw"] or du_phong
    return kq


def _dau_card(card):
    return "|".join(sorted("%s=%s" % (str(c.get("ten") or ""), str(c.get("driver") or "")) for c in card or [] if isinstance(c, dict)))


def _khoa():
    """Giữ quyền dò (1 tiến trình). -> đường dẫn khoá | None (tiến trình khác đang dò)."""
    p = _cache_path()
    if not p:
        return ""
    k = os.path.splitext(p)[0] + ".dang-do"
    for _ in range(2):
        try:
            os.close(os.open(k, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return k
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(k) < KHOA_HAN:
                    return None
                os.remove(k)   # khoá cũ của tiến trình đã chết
            except OSError:
                return None
        except OSError:
            return ""
    return None


def do(ep=False, card=None):
    """Dò bộ mã hoá + giải mã dùng được. -> {"h264": tên, "hevc": tên, "thu": {tên: lỗi|""}, "giai_ma": {…}, …} (nhớ 7 ngày).
    card = [{ten, driver}] của máy (app gửi): khác lần dò trước thì dò lại."""
    tho = _doc_tho()
    dau = _dau_card(card) if card else None
    if dau is not None and tho.get("card_dau") != dau:
        ep = True   # đổi card / cập nhật driver
    d = None if ep else _doc()
    if d and "h264" in d and isinstance(d.get("giai_ma"), dict):
        return d
    k = _khoa()
    if k is None:   # tiến trình khác (app lúc mở) đang dò: lần này dùng CPU, không chờ, không ghi nhớ
        return {"h264": CPU["h264"], "hevc": CPU["hevc"], "thu": {}, "giai_ma": {"hw": None}, "loi_dung": {}, "tam": True}
    try:
        if d and "h264" in d:   # nhớ của bản trước 10/11 (chưa dò giải mã): dò thêm phần giải mã
            kq = d
        else:
            try:
                ds = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=20, **KW).stdout
            except (OSError, subprocess.SubprocessError):
                ds = ""
            co = {w.split()[1] for w in ds.splitlines() if len(w.split()) > 1}
            kq = {"ffmpeg": _dau_ffmpeg(), "luc": time.time(), "thu": {}, "loi_dung": (d or {}).get("loi_dung", {})}
            for codec, ds_enc in UU_TIEN.items():
                kq[codec] = CPU[codec]
                for enc in ds_enc:
                    if enc not in co:
                        continue
                    ok, loi = _thu(enc)
                    kq["thu"][enc] = "" if ok else (loi or "lỗi")
                    if ok:
                        kq[codec] = enc
                        break
        kq["giai_ma"] = _do_giai_ma()
        if dau is not None:
            kq["card"], kq["card_dau"] = card, dau
        elif tho.get("card_dau") is not None:
            kq.setdefault("card", tho.get("card"))
            kq.setdefault("card_dau", tho.get("card_dau"))
        _ghi(kq)
        return kq
    finally:
        if k:
            try:
                os.remove(k)
            except OSError:
                pass


def _ep_ma_hoa():
    return (os.environ.get("POLY_MA_HOA") or "cpu").strip().lower()   # trống = cpu: bản 1 / Claude dựng y như trước


def chon(codec="h264", crf=19):
    """Tên bộ mã hoá cho 1 bước. CRF 0 = không mất -> CPU."""
    ep = _ep_ma_hoa()
    if ep in TAT or int(crf) == 0:
        return CPU[codec]
    if ep in UU_TIEN.get(codec, []):
        return ep if ep not in _hong else CPU[codec]
    return _chon_tu_dong(do(), codec)


def _chon_tu_dong(d, codec):
    enc = d.get(codec, CPU[codec])
    if enc in _hong or (d.get("loi_dung") or {}).get(enc, 0) >= 2:
        return CPU[codec]
    return enc


def bao_loi(enc):
    """Bước mã hoá bằng card vừa lỗi: lượt này thôi dùng; lỗi 2 lần (cộng dồn trong 7 ngày) thì tắt hẳn."""
    if enc in CPU.values():
        return
    _hong.add(enc)
    d = _doc() or do()
    if d.get("tam"):
        return
    ld = d.setdefault("loi_dung", {})
    ld[enc] = ld.get(enc, 0) + 1
    _ghi(d)


def ten_de_hieu(enc):
    for k, v in TEN.items():
        if k in enc:
            return v
    return enc


def chay(dung_lenh, chay_fn, codec="h264", crf=19, preset="veryfast"):
    """Chạy 1 bước có mã hoá: dung_lenh(tham_so_ma_hoa) -> cmd; chay_fn(cmd) ném lỗi nếu ffmpeg lỗi.
    Bằng card lỗi thì làm lại bằng CPU. -> tên bộ mã hoá đã dùng."""
    enc = chon(codec, crf)
    try:
        chay_fn(dung_lenh(tham_so(enc, crf, preset)))
        _ghi_da(enc)
        return enc
    except (SystemExit, Exception):
        if enc == CPU[codec]:
            raise
        sys.stderr.write("[ma_hoa] %s lỗi, làm lại bằng CPU\n" % enc)
        chay_fn(dung_lenh(tham_so(CPU[codec], crf, preset)))   # CPU cũng lỗi = lỗi khác, không phải tại card: ném lỗi, không ghi card hỏng
        bao_loi(enc)
        DA["ma_hoa_lui"] += 1
        _ghi_da(CPU[codec])
        return CPU[codec]


def _ghi_da(enc):
    if enc not in DA["ma_hoa"]:
        DA["ma_hoa"].append(enc)


# ------------------------------------------------------------------ giải mã: dùng lúc dựng
def _ep_giai_ma():
    gm = (os.environ.get("POLY_GIAI_MA") or "").strip().lower()
    if gm:
        return gm
    return "cpu" if _ep_ma_hoa() in TAT else "auto"


def bat():
    """Đường card (mã hoá hoặc giải mã) đang bật trong tiến trình này? Tắt (bản 1, POLY_MA_HOA trống / cpu) = lệnh y như trước."""
    return _ep_ma_hoa() not in TAT or _ep_giai_ma() not in TAT


def giai_ma():
    """Loại -hwaccel giải mã clip cho lệnh dựng, None = CPU (như cũ)."""
    gm = _ep_giai_ma()
    if gm in TAT:
        return None
    if gm != "auto":
        return None if gm in _hong_gm else gm
    return _giai_ma_tu_dong(do())


def _giai_ma_tu_dong(d):
    hw = (d.get("giai_ma") or {}).get("hw")
    if not hw or hw in _hong_gm or (d.get("loi_dung") or {}).get("gm:" + hw, 0) >= 2:
        return None
    return hw


def vao():
    """Tham số đặt ngay TRƯỚC -i của 1 clip video: ["-hwaccel", loại] khi giải mã bằng card, [] = như cũ."""
    hw = giai_ma()
    return ["-hwaccel", hw] if hw else []


def _hw_cua(cmd):
    for i in range(len(cmd) - 1):
        if cmd[i] == "-hwaccel":
            return cmd[i + 1]
    return None


def bo_hw(cmd):
    """Y lệnh đó, bỏ mọi cặp -hwaccel <loại> (giải mã bằng CPU)."""
    out, i = [], 0
    while i < len(cmd):
        if cmd[i] == "-hwaccel" and i + 1 < len(cmd):
            i += 2
            continue
        out.append(cmd[i])
        i += 1
    return out


def bao_loi_gm(hw):
    """Giải mã bằng card vừa lỗi (CPU thì được): lượt này thôi dùng; lỗi 2 lần (cộng dồn trong 7 ngày) thì tắt hẳn."""
    if not hw:
        return
    _hong_gm.add(hw)
    d = _doc() or do()
    if d.get("tam"):
        return
    ld = d.setdefault("loi_dung", {})
    ld["gm:" + hw] = ld.get("gm:" + hw, 0) + 1
    _ghi(d)


def chay_gm(cmd, chay_fn):
    """Chạy 1 lệnh; có -hwaccel mà lỗi thì chạy lại y lệnh đó bỏ -hwaccel (CPU). CPU cũng lỗi = lỗi khác: ném, không ghi card hỏng."""
    hw = _hw_cua(cmd)
    if not hw:
        return chay_fn(cmd)
    DA["giai_ma"] = hw
    DA["giai_ma_lan"] += 1
    try:
        r = chay_fn(cmd)
        DA["giai_ma_ok"] += 1
        return r
    except (SystemExit, Exception):
        sys.stderr.write("[ma_hoa] giải mã bằng card (%s) lỗi, làm lại bằng CPU\n" % hw)
        r = chay_fn(bo_hw(cmd))
        bao_loi_gm(hw)
        DA["giai_ma_lui"] += 1
        return r


def thong_ke():
    """Lượt dựng này dùng gì (app ghi log): {ma_hoa: [..], ma_hoa_lui, giai_ma, giai_ma_lan (lệnh thử card), giai_ma_ok (được), giai_ma_lui}."""
    return {"ma_hoa": list(DA["ma_hoa"]), "ma_hoa_lui": DA["ma_hoa_lui"], "giai_ma": DA["giai_ma"],
            "giai_ma_lan": DA["giai_ma_lan"], "giai_ma_ok": DA["giai_ma_ok"], "giai_ma_lui": DA["giai_ma_lui"]}


if __name__ == "__main__":
    card = None
    for a in sys.argv[1:]:
        if a.startswith("--card="):
            try:
                card = [c for c in json.loads(a[7:]) if isinstance(c, dict)]
            except ValueError:
                card = None
    d = do(ep="--do-lai" in sys.argv, card=card)
    out = {"h264": d.get("h264"), "hevc": d.get("hevc"), "thu": d.get("thu", {}), "loi_dung": d.get("loi_dung", {}),
           "giai_ma": d.get("giai_ma") or {}, "card": d.get("card") or [], "tam": bool(d.get("tam")), "luc": d.get("luc"),
           # dùng thật khi POLY Cut để Tự động (đã trừ loại lỗi 2 lần)
           "tu_dong": {"h264": _chon_tu_dong(d, "h264"), "hevc": _chon_tu_dong(d, "hevc"), "giai_ma": _giai_ma_tu_dong(d)},
           "dang_dung": chon("h264")}
    if "--json" in sys.argv:
        print(json.dumps(out, ensure_ascii=False))
    else:
        print(json.dumps(out, ensure_ascii=False, indent=1))
