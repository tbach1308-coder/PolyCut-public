# -*- coding: utf-8 -*-
"""Phong cách cho giọng đọc AI (POLY Cut r39, 11/11) = xử lý sau bằng ffmpeg, không đổi độ dài.

Anh 11/11: "thêm giọng đọc AI trend" (duyệt 11:30: giữ cả 9 kiểu). Kiểu trend (giong-trend.json) = 1 giọng có sẵn
(VieNeu / Microsoft) + tốc độ + 1 phong cách ở đây. giong.py --phong <id> gọi ap(..., giu_mau=True) lên giong-doc.wav sau khâu
chuẩn âm lượng: KHÔNG đổi độ dài (đổi cao độ bằng asetrate rồi atempo bù lại, cuối cùng cắt / đệm đúng số mẫu cũ) -> mốc câu,
mốc chữ, phụ đề đã canh theo giọng vẫn khớp. Tốc độ đọc vẫn là việc của giong.py (--toc-do), làm TRƯỚC khi canh phụ đề.
Không có --phong (hay "goc"): giong.py không gọi file này, giọng ra y hệt bản cũ.

Mỗi phong cách là 1 bộ THAM SỐ SỐ (không phải chuỗi lệnh ffmpeg thô): app tự dựng chuỗi lọc từ danh sách trắng và kẹp
mọi số trong khoảng an toàn. Nhờ vậy file phong-cach.json trong kho effect (Google Drive, đồng bộ mọi máy) chỉ chỉnh được
số, không chèn được bộ lọc đọc / ghi file (movie=, amovie=, ametadata=file...).

Tham số (bỏ trống = không dùng):
  cao_bc     đổi cao độ, bán cung (-6..+6). asetrate: giọng dày / mỏng theo (kiểu "trầm", "chipmunk").
  loc_thap   cắt trầm dưới Hz (20..1000)            loc_cao  cắt bổng trên Hz (1500..20000)
  eq         [[tần số Hz, dB (-12..12), độ rộng Q (0.3..5)], ...]  (tối đa 6 dải)
  tram_them  dB nâng dải trầm 150 Hz (bass shelf)   bong_them  dB nâng dải "air" 9 kHz (treble shelf)
  nen        nén tiếng: {"nguong": dB (-40..0), "ty_le": 1..20}
  bot_xi     giảm tiếng xì "s" (0..1)
  meo        làm méo loa (dB đẩy vào bộ cắt mềm, 0..18)
  robot      trộn tiếng robot (0..1)
  vang       tiếng vang: {"tre_ms": [..] (5..800), "giam": [..] (0..0.9)}  (tối đa 4 lần dội)
  luong      chuẩn âm lượng LUFS (-24..-10), mặc định -14 như giong.py

Dùng thử:
  python phong_giong.py --ds                               # in danh sách phong cách (JSON)
  python phong_giong.py --loc loa                          # in chuỗi lọc ffmpeg của 1 phong cách
  python phong_giong.py vao.wav ra.mp3 --phong loa [--kho "<kho>/giong/phong-cach.json"]
"""
import argparse
import json
import os
import re
import subprocess
import sys

try:
    import chung
    chung.dat_utf8()
    FFMPEG = chung.FFMPEG
except Exception:   # noqa: BLE001 - chạy rời ngoài engine
    FFMPEG = "ffmpeg"

SR = 48000

# Mặc định trong app (dự phòng khi kho chưa có / kho hỏng). Thứ tự = thứ tự hiện trong app.
PHONG = {
    "goc": {"ten": "Gốc", "mo_ta": "Giọng như máy đọc, chỉ chuẩn âm lượng"},
    "ro": {"ten": "Rõ · chốt sale", "mo_ta": "Rõ chữ, gọn, nổi trên nhạc: review nhanh, báo giá",
           "loc_thap": 90, "eq": [[220, -2, 1.0], [3500, 3, 1.2]], "nen": {"nguong": -22, "ty_le": 3}},
    "tram": {"ten": "Trầm ấm", "mo_ta": "Hạ 1,5 cung, dày tiếng, vang phòng nhẹ: kể chuyện, review phim",
             "cao_bc": -1.5, "tram_them": 3, "loc_cao": 9500, "nen": {"nguong": -24, "ty_le": 2.5},
             "vang": {"tre_ms": [35, 60, 95], "giam": [0.22, 0.14, 0.08]}},
    "ngot": {"ten": "Ngọt sáng", "mo_ta": "Nâng nhẹ cao độ, sáng tiếng, bớt xì: nữ nhẹ nhàng, đập hộp chill",
             "cao_bc": 0.7, "loc_thap": 120, "bong_them": 3, "bot_xi": 0.5, "nen": {"nguong": -24, "ty_le": 2},
             "vang": {"tre_ms": [25], "giam": [0.1]}},
    "genz": {"ten": "Trẻ trung", "mo_ta": "Cao hơn 1,5 cung, tươi, đậm: Gen Z, trend nhanh",
             "cao_bc": 1.5, "loc_thap": 110, "eq": [[4500, 3, 1.0]], "bong_them": 2, "nen": {"nguong": -20, "ty_le": 3.5}},
    "loa": {"ten": "Loa thông báo", "mo_ta": "Loa phát thanh ngoài trời: thông báo xả kho, flash sale",
            "loc_thap": 500, "loc_cao": 3000, "eq": [[1800, 6, 1.0]], "meo": 8,
            "vang": {"tre_ms": [180, 360], "giam": [0.35, 0.18]}},
    "radio": {"ten": "Bản tin radio", "mo_ta": "Tiếng radio / điện thoại: bản tin hot, tin giá",
              "loc_thap": 300, "loc_cao": 3600, "eq": [[1200, 3, 1.0]], "nen": {"nguong": -28, "ty_le": 6}, "meo": 3},
    "robot": {"ten": "Robot nhẹ", "mo_ta": "Pha tiếng máy, vẫn nghe rõ chữ: meme AI, công nghệ",
              "robot": 0.55, "loc_thap": 100, "nen": {"nguong": -22, "ty_le": 3}},
    "chipmunk": {"ten": "Chipmunk vui", "mo_ta": "Cao 5 cung kiểu hoạt hình: câu bựa, câu chốt hài",
                 "cao_bc": 5, "loc_thap": 150, "nen": {"nguong": -22, "ty_le": 3}},
}


def _so(v, lo, hi, md=None):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return md
    if v != v:   # NaN
        return md
    return max(lo, min(hi, v))


def _f(x):
    return ("%.4f" % x).rstrip("0").rstrip(".")


def chuoi(p, sr=SR, chuan=True):
    """Tham số phong cách -> chuỗi -af ffmpeg (1 vào 1 ra, giữ độ dài). Chỉ dùng bộ lọc trong danh sách trắng.
    chuan=False: bỏ khâu chuẩn âm lượng cuối (ap() đo 2 lượt cho đúng -14 LUFS cả với câu ngắn)."""
    p = p if isinstance(p, dict) else {}
    loc = []
    cao = _so(p.get("cao_bc"), -6, 6, 0)
    if abs(cao) >= 0.05:
        r = 2 ** (cao / 12.0)
        loc += ["asetrate=%d" % round(sr * r), "aresample=%d" % sr, "atempo=%s" % _f(1 / r)]
    v = _so(p.get("loc_thap"), 20, 1000)
    if v:
        loc.append("highpass=f=%d" % v)
    v = _so(p.get("loc_cao"), 1500, 20000)
    if v:
        loc.append("lowpass=f=%d" % v)
    for d in (p.get("eq") or [])[:6]:
        if isinstance(d, (list, tuple)) and len(d) >= 2:
            f, g, q = _so(d[0], 30, 18000), _so(d[1], -12, 12), _so(d[2] if len(d) > 2 else 1, 0.3, 5, 1)
            if f and g:
                loc.append("equalizer=f=%d:t=q:w=%s:g=%s" % (f, _f(q), _f(g)))
    v = _so(p.get("tram_them"), -12, 12)
    if v:
        loc.append("bass=g=%s:f=150" % _f(v))
    v = _so(p.get("bong_them"), -12, 12)
    if v:
        loc.append("treble=g=%s:f=9000" % _f(v))
    v = _so(p.get("bot_xi"), 0, 1)
    if v:
        loc.append("deesser=i=%s" % _f(v))
    n = p.get("nen")
    if isinstance(n, dict):
        th, ra = _so(n.get("nguong"), -40, 0, -20), _so(n.get("ty_le"), 1, 20, 3)
        loc.append("acompressor=threshold=%sdB:ratio=%s:attack=5:release=90:makeup=2" % (_f(th), _f(ra)))
    v = _so(p.get("robot"), 0, 1)
    if v:   # robot: bỏ pha từng khung FFT (giọng máy đều), trộn với tiếng gốc
        loc.append("asplit[k][r];[r]afftfilt=real='hypot(re,im)':imag='0':win_size=512:overlap=0.75[rb];"
                   "[k][rb]amix=inputs=2:weights='%s %s':normalize=1" % (_f(1 - v), _f(v)))
    v = _so(p.get("meo"), 0, 18)
    if v:
        loc += ["volume=%sdB" % _f(v), "asoftclip=type=atan", "volume=-%sdB" % _f(v * 0.6)]
    g = p.get("vang")
    if isinstance(g, dict):
        tre = [_so(x, 5, 800) for x in (g.get("tre_ms") or [])][:4]
        giam = [_so(x, 0, 0.9, 0) for x in (g.get("giam") or [])][:len(tre)]
        if tre and len(giam) == len(tre) and all(tre):
            loc.append("aecho=0.9:0.9:%s:%s" % ("|".join("%d" % x for x in tre), "|".join(_f(x) for x in giam)))
    if chuan:
        loc.append("loudnorm=I=%s:TP=-1.5:LRA=11" % _f(_so(p.get("luong"), -24, -10, -14)))
    return ",".join(loc) or "anull"


def doc_kho(duong):
    """Phong cách trong kho (giong/phong-cach.json: {"phong": {id: {...}}}) đè lên mặc định; kho hỏng thì dùng mặc định."""
    ds = {k: dict(v) for k, v in PHONG.items()}
    try:
        with open(duong, encoding="utf-8") as f:
            kho = json.load(f).get("phong") or {}
        for k, v in kho.items():
            if isinstance(k, str) and k.replace("-", "").isalnum() and len(k) <= 30 and isinstance(v, dict):
                ds[k] = dict(ds.get(k, {}), **v)
    except (OSError, ValueError, AttributeError):
        pass
    return ds


def co(phong):
    return isinstance(phong, str) and phong in PHONG


def ds_phong():
    return [dict(id=k, ten=v.get("ten", k), mo_ta=v.get("mo_ta", "")) for k, v in PHONG.items()]


def so_mau(p):
    """Số mẫu của file wav (None nếu không đọc được)."""
    import wave
    try:
        with wave.open(p, "rb") as w:
            return w.getnframes() if w.getframerate() == SR else None
    except (OSError, EOFError, wave.Error):
        return None


def ap(vao, ra, phong, ds=None, giu_mau=False):
    """Áp 1 phong cách lên file giọng (wav / mp3). Giữ 48 kHz mono; mp3 thì 160k.
    giu_mau: vào là wav 48 kHz -> ra đúng bằng số mẫu đó (vang dội ra ngoài thì cắt, đổi cao độ hụt vài ms thì đệm im).
    Chuẩn âm lượng bằng đo (câu ngắn vài giây loudnorm 1 lượt hụt 1–2 LU so với -14): đo -> tăng / giảm + chặn đỉnh
    -1.9 dBFS -> đo lại -> bù phần chặn đỉnh ăn mất. 3 lượt ffmpeg, giọng 30 giây mỗi lượt dưới 1 giây."""
    ds = ds or PHONG
    p = ds.get(phong) or ds["goc"]
    lu = _so(p.get("luong"), -24, -10, -14)
    goc = chuoi(p, chuan=False)
    chan = "alimiter=limit=0.8:attack=3:release=60:level=disabled"

    def do_i(af):
        r = subprocess.run([FFMPEG, "-nostdin", "-hide_banner", "-nostats", "-i", vao, "-af", af + ",ebur128", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr or "")
        v = _so(m[-1], -70, 10) if not r.returncode and m else None
        return v if v is not None and v > -69 else None   # None: không đo được / file im

    i0 = do_i(goc)
    if i0 is None:
        chuan = "loudnorm=I=%s:TP=-1.5:LRA=11" % _f(lu)   # như giong.py
    else:
        g = max(-30, min(30, lu - i0))
        i1 = do_i(goc + ",volume=%sdB,%s" % (_f(g), chan))
        if i1 is not None:
            g = max(-30, min(30, g + (lu - i1)))
        chuan = "volume=%sdB,%s" % (_f(g), chan)
    n = so_mau(vao) if giu_mau else None
    if n:
        chuan += ",apad=whole_len=%d,atrim=end_sample=%d" % (n, n)
    out = ["-c:a", "libmp3lame", "-b:a", "160k"] if ra.lower().endswith(".mp3") else ["-c:a", "pcm_s16le"]
    r = subprocess.run([FFMPEG, "-nostdin", "-v", "error", "-y", "-i", vao, "-af", goc + "," + chuan, "-ar", str(SR), "-ac", "1"] + out + [ra],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit("LOI=Không áp được phong cách giọng %s: %s" % (phong, r.stderr[-300:]))
    return ra


def main():
    ap_ = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap_.add_argument("vao", nargs="?")
    ap_.add_argument("ra", nargs="?")
    ap_.add_argument("--phong", default="goc")
    ap_.add_argument("--kho", help="giong/phong-cach.json trong kho effect")
    ap_.add_argument("--ds", action="store_true", help="in danh sách phong cách")
    ap_.add_argument("--loc", metavar="PHONG", help="in chuỗi lọc ffmpeg của 1 phong cách")
    a = ap_.parse_args()
    ds = doc_kho(a.kho) if a.kho else PHONG
    if a.ds:
        print(json.dumps([dict(id=k, ten=v.get("ten", k), mo_ta=v.get("mo_ta", "")) for k, v in ds.items()], ensure_ascii=False))
        return
    if a.loc:
        print(chuoi(ds.get(a.loc) or {}))
        return
    if not a.vao or not a.ra:
        ap_.error("cần file vào và file ra")
    print(json.dumps({"ra": ap(a.vao, a.ra, a.phong, ds), "phong": a.phong}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
