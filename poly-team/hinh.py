# -*- coding: utf-8 -*-
"""POLY Cut — 2 chức năng HÌNH của trình sửa (4/11/2026, chủ tiệm duyệt từ bài "CapCut cho người mới"), phần máy chủ, chỉ thư viện chuẩn.

  POST /api/sua-tay/hinh/chia  {v, plan, ids|null, tach_im}  -> {ma}   Tự chia cảnh (đề xuất chỗ cắt, trang hiện vạch, anh bấm Chia)
  GET  /api/sua-tay/hinh/chia?ma=…                           -> {dang, buoc, kq, loi, canh_bao, giay_da}
  POST /api/sua-tay/hinh/mau   {v, plan, nhom: [{ids, tu, den, file}]} -> {ma}   Tự chỉnh màu (đo khung -> canh.mau)
  GET  /api/sua-tay/hinh/mau?ma=…
  GET  /api/sua-tay/hinh/loc-ds                              -> {ds: [{v, ten, mo_ta}]} bộ lọc LUT có trong bộ dựng (engine/luts)
  GET  /api/sua-tay/hinh/anh-loc?p=<clip>&t=<giây>&loc=<tên>[&mau=sang,tuong_phan,bao_hoa,nhiet]
                                                             -> ảnh JPEG khung clip qua ĐÚNG chuỗi màu + lut3d của bộ dựng (ô Thư viện)
Việc nặng chạy bằng Python của bộ dựng: hinh_may.py (numpy + máy nghe), mỗi việc 1 tiến trình riêng, in BUOC= / XONG= / LOI=.
sua_tay.py chỉ thêm 2 dòng móc nối (get / post: đường /api/sua-tay/hinh/…).
"""
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from urllib.parse import quote  # noqa: F401

import sua_tay as ST

APP = os.path.dirname(os.path.abspath(__file__))
VIEC = {}            # mã -> trạng thái việc (chia / mau)
LOCK = threading.RLock()
TEN_LOC = re.compile(r"[a-z0-9_]{1,40}")


def _S():
    return ST.S


def _cache(*p):
    d = os.path.join(_S().CACHE, "hinh", *p)
    os.makedirs(d, exist_ok=True)
    return d


def _proxy(p):
    """Bản xem nhẹ đã làm xong của clip (540×960, HDR -> SDR như bản xuất) | ''."""
    try:
        x = ST._proxy_file(p)
        return x if x and os.path.isfile(x) and os.path.getsize(x) > 1000 else ""
    except Exception:
        return ""


def _canh_ds(v, plan, ids):
    """Cảnh được chọn (ids None = mọi cảnh) -> [{id, so, src, xem, tu, den, co_tieng, hdr, hdr_trc}], [tên clip mất]."""
    ST.kiem_ke_hoach(v, plan, can_file=False)
    nguon = plan.get("nguon") or {}
    out, mat = [], []
    for i, c in enumerate(plan["canh"]):
        if ids is not None and c.get("_id") not in ids:
            continue
        n = nguon.get(c.get("file")) or {}
        local = n.get("local") or c.get("file")
        if not (local and os.path.isfile(local)):
            mat.append(os.path.basename(str(local)))
            continue
        out.append({"id": c.get("_id"), "so": i + 1, "src": local, "xem": _proxy(local), "tu": float(c["tu"]), "den": float(c["den"]),
                    "co_tieng": n.get("co_tieng", True) is not False, "hdr": bool(n.get("hdr")), "hdr_trc": n.get("hdr_trc")})
    return out, mat


def _chay(v, loai, viec, ten_viec):
    """Chạy hinh_may.py <loai> <viec.json> nền; trả {ma}. Mỗi video mỗi loại chỉ 1 việc cùng lúc."""
    S = _S()
    with LOCK:
        for x in VIEC.values():
            if x.get("dang") and x["v"] == ST.norm(v) and x["loai"] == loai:
                return {"ma": x["ma"], "dang": True}
        for k in sorted(VIEC, key=lambda k: VIEC[k]["bat_dau"])[:-30]:
            if not VIEC[k].get("dang"):
                VIEC.pop(k, None)
        ma = "%s%x" % (loai[0], int(time.time() * 1000))
        st = VIEC[ma] = {"ma": ma, "v": ST.norm(v), "loai": loai, "dang": True, "buoc": "Bắt đầu " + ten_viec, "bat_dau": time.time(),
                         "kq": None, "loi": "", "canh_bao": []}
    d = os.path.join(v, "lam", "sua-tay")
    os.makedirs(d, exist_ok=True)
    vp = os.path.join(d, "viec-hinh-%s.json" % loai)
    ST._ghi(vp, viec)
    e = S.engine()
    kw = {"creationflags": ST.NO_WIN | 0x00000200} if ST.IS_WIN else {"start_new_session": True}
    try:
        p = subprocess.Popen([e["py"], os.path.join(APP, "hinh_may.py"), loai, vp], cwd=e["dir"], env=ST.MAY._env(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    except Exception as ex:
        with LOCK:
            st.update(dang=False, loi="Không chạy được bộ dựng: %s" % ex)
        raise ValueError(st["loi"])
    st["pid"] = p.pid

    def theo():
        loi_ds = []

        def doc_err():
            for line in iter(p.stderr.readline, b""):
                loi_ds.append(line.decode("utf-8", "replace").rstrip())
                del loi_ds[:-40]
        threading.Thread(target=doc_err, daemon=True).start()
        kq = None
        for raw in iter(p.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            with LOCK:
                if line.startswith("BUOC="):
                    st["buoc"] = line[5:]
                elif line.startswith("LOI="):
                    st["loi"] = line[4:]
                elif line.startswith("CANH_BAO="):
                    try:
                        st["canh_bao"] += json.loads(line[9:])
                    except ValueError:
                        pass
                elif line.startswith("XONG="):
                    try:
                        kq = json.loads(line[5:])
                    except ValueError:
                        pass
        code = p.wait()
        with LOCK:
            st["dang"] = False
            st["giay_da"] = round(time.time() - st["bat_dau"], 1)
            if kq is not None:
                st["kq"] = kq
            elif not st["loi"]:
                st["loi"] = "Bộ dựng dừng giữa chừng (mã %s)" % code
        if kq is None:
            S.log("sua-tay hinh %s loi %s: %s | %s" % (loai, os.path.basename(v), st["loi"], " / ".join(loi_ds[-6:])))
    threading.Thread(target=theo, daemon=True).start()
    return {"ma": ma, "dang": True}


def trang_thai(ma):
    with LOCK:
        st = VIEC.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy việc này (app vừa khởi động lại?)"}
        out = {k: st.get(k) for k in ("ma", "dang", "buoc", "kq", "loi", "canh_bao")}
        out["giay_da"] = round(time.time() - st["bat_dau"], 1)
        return out


# ---------------------------------------------------------------- Tự chia cảnh
def chia(v, plan, ids, tach_im):
    v = ST.thu_muc_video(v)
    if ids is not None and (not isinstance(ids, list) or not all(isinstance(x, str) for x in ids)):
        raise ValueError("Danh sách cảnh sai dạng")
    ds, mat = _canh_ds(v, plan, ids)
    if not ds:
        raise ValueError("Không thấy clip của cảnh trên máy" + (" (%s)" % ", ".join(mat) if mat else ""))
    ds = [c for c in ds if c["den"] - c["tu"] >= 1.6]
    if not ds:
        raise ValueError("Cảnh ngắn quá (dưới 1,6 giây) nên không chia thêm được: mỗi cảnh con cần ít nhất 0,8 giây")
    with ST.LOCK:
        ST.NGUON_OK.update(ST.norm(c["src"]) for c in ds)
    return _chay(v, "chia", {"kho": _S().CACHE, "tach_im": tach_im is not False, "canh": ds}, "tự chia cảnh")


# ---------------------------------------------------------------- Tự chỉnh màu
def mau(v, plan, nhom):
    """nhom = [{ids: [...]}]: mỗi nhóm đo chung 1 lần (các cảnh vừa chia liền nhau của cùng clip -> cùng 1 màu, bản xuất vẫn nối liền)."""
    v = ST.thu_muc_video(v)
    if not isinstance(nhom, list) or not nhom or len(nhom) > 300:
        raise ValueError("Chưa chọn cảnh")
    ds, mat = _canh_ds(v, plan, None)
    theo_id = {c["id"]: c for c in ds}
    viec = []
    for g in nhom:
        ids = [x for x in (g.get("ids") or []) if x in theo_id] if isinstance(g, dict) else []
        if not ids:
            continue
        cs = [theo_id[x] for x in ids]
        c0 = dict(cs[0])
        if len({c["src"] for c in cs}) == 1:   # nhóm liền nhau cùng clip: đo cả đoạn
            c0["tu"], c0["den"] = min(c["tu"] for c in cs), max(c["den"] for c in cs)
        c0["ids"] = ids
        viec.append(c0)
    if not viec:
        raise ValueError("Không thấy clip của cảnh trên máy" + (" (%s)" % ", ".join(mat) if mat else ""))
    return _chay(v, "mau", {"kho": _S().CACHE, "canh": viec}, "đo màu")


# ---------------------------------------------------------------- Bộ lọc (LUT)
def _lut_dir():
    return os.path.join(_S().engine()["dir"], "luts")


def loc_ds():
    d = _lut_dir()
    try:
        with open(os.path.join(d, "bo-loc.json"), encoding="utf-8-sig") as f:
            ds = (json.load(f) or {}).get("ds") or []
    except (OSError, ValueError):
        ds = []
    co = [x for x in ds if isinstance(x, dict) and TEN_LOC.fullmatch(str(x.get("v") or "")) and os.path.isfile(os.path.join(d, x["v"] + ".cube"))]
    return {"ds": [{"v": x["v"], "ten": str(x.get("ten") or x["v"])[:40], "mo_ta": str(x.get("mo_ta") or "")[:200]} for x in co]}


def _so(x, mac, lo, hi):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return mac
    return mac if x != x else max(lo, min(hi, x))


def anh_loc(p, t, ten, mau_s):
    """Ảnh khung clip qua màu riêng cảnh (eq + colortemperature) + lut3d, đúng như bộ dựng (dung_may_chu.mau_canh / loc_canh)."""
    S = _S()
    if not S.allowed_path(p, video=True):
        raise PermissionError("không xem được clip này")
    goc = S.thumb(p, t)
    chuoi = []
    if mau_s:
        x = (str(mau_s).split(",") + ["", "", "", ""])[:4]
        sang, tp, bh, K = _so(x[0], 0.0, -0.3, 0.3), _so(x[1], 1.0, 0.5, 1.5), _so(x[2], 1.0, 0.0, 2.0), _so(x[3], 6500.0, 3000.0, 9000.0)
        if (sang, tp, bh) != (0.0, 1.0, 1.0):
            chuoi.append("eq=brightness=%g:contrast=%g:saturation=%g" % (sang, tp, bh))
        if K != 6500.0:
            chuoi.append("colortemperature=temperature=%d" % int(round(K)))
    if ten:
        if not TEN_LOC.fullmatch(str(ten)):
            raise ValueError("Bộ lọc lạ")
        f = os.path.join(_lut_dir(), ten + ".cube")
        if not os.path.isfile(f):
            raise ValueError("Bộ dựng chưa có bộ lọc này")
        chuoi.append("lut3d=file=%s:interp=tetrahedral" % _loc(f))
    if not chuoi:
        return goc
    k = hashlib.md5(("%s|%s|%s" % (goc, os.path.getmtime(goc), ",".join(chuoi))).encode("utf-8")).hexdigest()
    out = os.path.join(_cache("anh"), k + ".jpg")
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    ff = S.tim_ffmpeg("ffmpeg")
    tam = out + ".%d.tmp.jpg" % os.getpid()
    subprocess.run([ff, "-v", "error", "-y", "-i", goc, "-vf", ",".join(chuoi), "-q:v", "4", tam], capture_output=True, timeout=40,
                   creationflags=ST.NO_WIN if ST.IS_WIN else 0)
    if not os.path.isfile(tam) or os.path.getsize(tam) == 0:
        raise ValueError("Không dựng được ảnh bộ lọc")
    os.replace(tam, out)
    try:   # dọn: giữ 400 ảnh mới nhất
        d = os.path.dirname(out)
        ds = sorted((os.path.join(d, x) for x in os.listdir(d) if x.endswith(".jpg")), key=os.path.getmtime)
        for x in ds[:-400]:
            os.remove(x)
    except OSError:
        pass
    return out


def _loc(path):
    """Đường dẫn làm giá trị filter ffmpeg (như chung.loc của bộ dựng): ổ đĩa Windows 'E:' phải thoát ':'."""
    s = str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'\\''")
    return "'" + s + "'"


# ---------------------------------------------------------------- HTTP (sua_tay.get / post gọi)
def get(h, u, q):
    a = u.path[len("/api/sua-tay/hinh/"):]
    if a in ("chia", "mau"):
        h.send(200, trang_thai((q.get("ma") or [""])[0]))
        return True
    if a == "loc-ds":
        h.send(200, loc_ds())
        return True
    if a == "anh-loc":
        try:
            fp = anh_loc((q.get("p") or [""])[0], (q.get("t") or ["1"])[0], (q.get("loc") or [""])[0], (q.get("mau") or [""])[0])
        except PermissionError as e:
            h.send(403, {"err": str(e)})
            return True
        with open(fp, "rb") as f:
            h.send(200, f.read(), "image/jpeg", {"Cache-Control": "max-age=86400"})
        return True
    return False


def post(h, u, data):
    a = u.path[len("/api/sua-tay/hinh/"):]
    if a == "chia":
        r = chia(data.get("v"), data.get("plan"), data.get("ids"), data.get("tach_im"))
    elif a == "mau":
        r = mau(data.get("v"), data.get("plan"), data.get("nhom"))
    else:
        return False
    h.send(200, r)
    return True
