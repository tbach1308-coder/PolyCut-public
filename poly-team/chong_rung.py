# -*- coding: utf-8 -*-
"""POLY Cut — CHỐNG RUNG (4/11/2026 tối, anh: "khung hình vẫn rung", chọn cả 4 kiểu rung). Phần máy chủ, chỉ thư viện chuẩn.

  POST /api/sua-tay/chong-rung/xem  {ds: [clip]}  -> {clip: {tt: cho|dang|xong|loi|khong, url, loi}}
       Bản xem nhẹ ĐÃ CHỐNG RUNG của clip (cho khung xem: cảnh bật Chống rung thì anh thấy ngay hình đã ổn định, không phải chờ xuất).
       Làm từ bản xem nhẹ 720p đã có (sua_tay._lam): vidstab 2 lượt, cùng thông số bộ dựng (dung_may_chu OD_DO / OD_LAM: shakiness 6,
       accuracy 12, smoothing 12, optzoom 1) -> mức phóng che mép gần bằng bản xuất (optzoom tính theo % khung; bản xuất tính trên
       đoạn cảnh, bản xem trên cả clip). Cache riêng _cache/chong-rung/<băm>.mp4. Chưa có bản xem nhẹ thì chờ nó trước.
  POST /api/sua-tay/chong-rung/do   {ds: [clip]}  -> {clip: {tt, trung_vi, p90, muc: rung|vua|yen}}
       Đo độ rung tay của clip (chong_rung_may.py bằng Python của bộ dựng, trên bản xem nhẹ): cùng cách đo + mốc của bộ dựng
       (engine/phan_tich.py: > 0,25 = nên chống rung). Trang dùng để GỢI Ý "Clip này rung, bật Chống rung?" (không tự bật).
  POST /api/sua-tay/chong-rung/phat {dang: bool}  -> hang_nen.phat: lúc anh đang phát khung xem, việc nền chỉ 1 việc / tạm dừng.
  GET  /api/sua-tay/chong-rung/tt                 -> trạng thái hàng việc nền (để kiểm thử).
Việc nặng chạy qua hang_nen (ưu tiên thấp, tạm dừng được lúc phát): bản xem chống rung uu 1, đo độ rung uu 2.
"""
import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import hang_nen
import sua_tay as ST

APP = os.path.dirname(os.path.abspath(__file__))
BAN = "od1"
OD = {}       # norm(clip) -> {"tt": cho|dang|xong|loi, "p": file, "loi"}
DO = {}       # norm(clip) -> {"tt": cho|dang|xong|loi, "kq": {...}}
LOCK = threading.RLock()
_POOL = ThreadPoolExecutor(max_workers=1)   # 1 việc chống rung / đo cùng lúc (nhường máy)
NGUONG_RUNG, NGUONG_VUA = 0.25, 0.18       # % khung (trung vị phần giật): mốc của bộ dựng (phan_tich.py)


def _S():
    return ST.S


def _cache(ten):
    d = os.path.join(_S().CACHE, "chong-rung")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, ten)


def _khoa(p, them):
    st = os.stat(p)
    return hashlib.md5(("%s|%s|%s|%s" % (ST.norm(p), st.st_size, int(st.st_mtime), them)).encode("utf-8")).hexdigest()


def _duoc_xem(p):
    """Như sua_tay.proxy_tt: clip của video đang sửa / clip trong thư mục clip đã mở."""
    if not p or not os.path.isfile(p):
        return False
    return ST.cho_xem(os.path.realpath(p)) or (os.path.splitext(p)[1].lower() in ST.VIDEO_EXT and _S().allowed_path(p, video=True))


def _xem_nhe(p):
    """Bản xem nhẹ 720p đã xong của clip | '' (chưa có thì xếp làm, hàng thường)."""
    try:
        x = ST._proxy_file(p)
    except OSError:
        return ""
    if os.path.isfile(x) and os.path.getsize(x) > 1000:
        return x
    ST.lam_proxy(p)
    return ""


# ------------------------------------------------------------------ bản xem đã chống rung
def _lam_od(p, nguon, out):
    key = ST.norm(p)
    try:
        ff = _S().tim_ffmpeg("ffmpeg")
        if not ff:
            raise RuntimeError("Chưa cài bộ dựng (ffmpeg)")
        trf = out + ".trf"
        tam = out + ".%d.part.mp4" % os.getpid()
        # lượt 1: đo chuyển động · lượt 2: làm mượt + phóng che mép (thông số = dung_may_chu.OD_DO / OD_LAM)
        r = hang_nen.chay([ff, "-v", "error", "-y", "-i", nguon, "-an", "-vf",
                           "vidstabdetect=shakiness=6:accuracy=12:result=" + _loc(trf), "-f", "null", "-"], uu=1, ten=p)
        if r.returncode or not os.path.isfile(trf):
            raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-300:] or "đo chuyển động lỗi")
        r = hang_nen.chay([ff, "-v", "error", "-y", "-i", nguon, "-map", "0:v:0", "-map", "0:a:0?", "-vf",
                           "vidstabtransform=smoothing=12:optzoom=1:interpol=bicubic:input=" + _loc(trf) + ",format=yuv420p",
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
                           "-c:a", "copy", "-movflags", "+faststart", tam], uu=1, ten=p)
        if r.returncode or not os.path.isfile(tam) or os.path.getsize(tam) < 1000:
            raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-300:] or "chống rung lỗi")
        os.replace(tam, out)
        try:
            os.remove(trf)
        except OSError:
            pass
        with LOCK:
            OD[key] = {"tt": "xong", "p": out}
    except Exception as e:  # noqa
        _S().log("chong-rung xem %s: %s" % (p, e))
        with LOCK:
            OD[key] = {"tt": "loi", "p": out, "loi": str(e)[:200]}


def _loc(path):
    """Đường dẫn làm giá trị filter ffmpeg (ổ đĩa Windows 'E:' -> 'E\\:'), như engine/chung.loc."""
    s = path.replace("\\", "/").replace("'", r"'\''").replace(":", r"\:")
    return "'" + s + "'"


def xem(ds):
    out = {}
    for f in (ds or [])[:40]:
        p = str(f or "")
        if not _duoc_xem(p):
            out[f] = {"tt": "khong"}
            continue
        key = ST.norm(p)
        try:
            dich = _cache(_khoa(p, BAN) + ".mp4")
        except OSError:
            out[f] = {"tt": "khong"}
            continue
        with LOCK:
            x = OD.get(key)
            if os.path.isfile(dich):
                x = OD[key] = {"tt": "xong", "p": dich}
            elif x and x.get("p") != dich:
                x = None   # clip đã đổi (chép lại / sửa): làm lại
        if not x:
            nguon = _xem_nhe(p)
            if not nguon:
                out[f] = {"tt": "cho", "buoc": "chờ bản xem nhẹ"}
                continue
            with LOCK:
                x = OD.get(key)
                if not x or x.get("p") != dich:
                    x = OD[key] = {"tt": "cho", "p": dich}

                    def chay(p=p, nguon=nguon, dich=dich, key=key):
                        with LOCK:
                            OD[key]["tt"] = "dang"
                        _lam_od(p, nguon, dich)
                    _POOL.submit(chay)
        if x["tt"] == "xong":
            out[f] = {"tt": "xong", "url": "/file?p=" + quote(x["p"])}
        else:
            out[f] = {"tt": x["tt"], "loi": x.get("loi")}
    return out


# ------------------------------------------------------------------ đo độ rung
def _muc(kq):
    v = (kq or {}).get("trung_vi")
    if v is None:
        return "yen"
    return "rung" if v > NGUONG_RUNG else "vua" if v > NGUONG_VUA else "yen"


def _lam_do(p, nguon, dich):
    key = ST.norm(p)
    try:
        e = _S().engine()
        if not os.path.isfile(e["py"]):
            raise RuntimeError("Chưa cài bộ dựng")
        r = hang_nen.chay([e["py"], os.path.join(APP, "chong_rung_may.py"), "do", nguon, dich], uu=2, cwd=e["dir"], env=ST.MAY._env())
        kq = ST.S.read_json(dich) if os.path.isfile(dich) else None
        if r.returncode or not isinstance(kq, dict):
            raise RuntimeError((r.stdout or b"").decode("utf-8", "replace")[-200:] + (r.stderr or b"").decode("utf-8", "replace")[-200:])
        with LOCK:
            DO[key] = {"tt": "xong", "kq": kq, "p": dich}
    except Exception as ex:  # noqa
        _S().log("chong-rung do %s: %s" % (p, ex))
        with LOCK:
            DO[key] = {"tt": "loi", "loi": str(ex)[:200], "p": dich}


def do(ds):
    out = {}
    for f in (ds or [])[:60]:
        p = str(f or "")
        if not _duoc_xem(p):
            out[f] = {"tt": "khong"}
            continue
        key = ST.norm(p)
        try:
            dich = _cache(_khoa(p, "do1") + "-do.json")
        except OSError:
            out[f] = {"tt": "khong"}
            continue
        with LOCK:
            x = DO.get(key)
            if (not x or x.get("p") != dich) and os.path.isfile(dich):
                kq = ST.S.read_json(dich)
                if isinstance(kq, dict):
                    x = DO[key] = {"tt": "xong", "kq": kq, "p": dich}
        if not x or x.get("p") != dich:
            nguon = _xem_nhe(p)
            if not nguon:
                out[f] = {"tt": "cho"}
                continue
            with LOCK:
                x = DO.get(key)
                if not x or x.get("p") != dich:
                    x = DO[key] = {"tt": "cho", "p": dich}

                    def chay(p=p, nguon=nguon, dich=dich, key=key):
                        with LOCK:
                            DO[key]["tt"] = "dang"
                        _lam_do(p, nguon, dich)
                    _POOL.submit(chay)
        if x["tt"] == "xong":
            kq = x["kq"]
            out[f] = {"tt": "xong", "trung_vi": kq.get("trung_vi"), "p90": kq.get("p90"), "muc": _muc(kq)}
        else:
            out[f] = {"tt": x["tt"], "loi": x.get("loi")}
    return out


# ------------------------------------------------------------------ đường API
def get(h, u, q):
    if u.path == "/api/sua-tay/chong-rung/tt":
        with LOCK:
            od = {k: v.get("tt") for k, v in OD.items()}
            dd = {k: v.get("tt") for k, v in DO.items()}
        h.send(200, dict(hang_nen.trang_thai(), od=od, do=dd))
        return True
    return False


def post(h, u, data):
    a = u.path[len("/api/sua-tay/chong-rung/"):]
    if a == "xem":
        r = xem(data.get("ds") or [])
    elif a == "do":
        r = do(data.get("ds") or [])
    elif a == "phat":
        try:
            so = int(data.get("so") or 0)
        except (TypeError, ValueError):
            so = 0
        r = hang_nen.phat(bool(data.get("dang")), str(data.get("clip") or "")[:1000], str(data.get("phien") or "")[:40], so,
                          bool(data.get("video", True)))   # video=False: khung xem đang hiện ảnh tạm (chưa có bản xem nhẹ)
    else:
        return False
    h.send(200, r)
    return True
