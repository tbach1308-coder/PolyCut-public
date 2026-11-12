# -*- coding: utf-8 -*-
"""POLY Cut — KHO EFFECT (r37, 11/11/2026; anh duyệt: kho âm thanh / nhạc dùng chung các máy trong tiệm trên Google Drive).

Kho = thư mục ở config khoá "kho_effect" (trống / không có khoá = không dùng kho, app chỉ dùng bản kèm app). Trong kho:
  kho.json                 {phien_ban, loai: {am_thanh: {thu_muc, ds}, nhac: {thu_muc, ds}}}
  am-thanh.json            {nhom, ds: {file: {ten, nhom, mo_ta, giay, dinh, sha256, bytes, nguon, giay_phep, link…}}}
  nhac.json                {file: {ten, mo_ta, bpm, giay, phong_cach, drop, nhip_dau, sha256, bytes, nguon, giay_phep…}}
  am-thanh/, nhac/         file âm thanh;  GIAY-PHEP.md, SHA256SUMS (cho người đọc)
Mỗi mục được kiểm: tên file trơn (không thư mục, không ".."), đuôi đúng loại, đường thật không thoát khỏi thư mục kho (lối tắt), sha256
đúng dạng, file có mặt. Mục hỏng bị bỏ qua + ghi app-log (1 lần mỗi khi danh sách đổi).
Drive có thể để file "chỉ trên mây": đọc lần đầu phải tải về, chậm / treo khi mất mạng -> KHÔNG đọc file kho lúc liệt kê, chỉ khi anh
nghe / thêm: chép về <app>/_cache/kho-effect/<sha256 16 ký tự>.<đuôi> ở luồng nền (1 file một lúc, có tiến độ), kiểm sha256 rồi mới
dùng. Kế hoạch (plan.am_thanh[].local, plan.nhac.local) luôn trỏ bản cache / bản kèm app -> bộ dựng ffmpeg không bao giờ đọc Drive.
Kho không có / chưa đồng bộ / mất mạng: danh sách chỉ còn bản kèm app (am-thanh/, nhac-mien-phi/), app không lỗi.
Mục trùng tên với bản kèm app: dùng bản kèm app (khỏi tải).

  GET /api/sua-tay/kho                       -> trạng thái kho (dùng / có / lỗi, số mục, mục hỏng, cache, đang chép)
  GET /api/sua-tay/kho/chep?loai=&f=         -> bắt đầu chép 1 mục về cache (nếu chưa) + trạng thái mục đó {tt, pt, p, loi}
Móc nối: am_thanh.ds() / cho_phep() và sua_tay.nhac_thu_muc() / nhac_ds() / get() (vài dòng, có try)."""
import hashlib, json, os, queue, re, threading, time, traceback

import sua_tay as ST

APP = os.path.dirname(os.path.abspath(__file__))
LOAI = {
    "am_thanh": {"duoi": (".wav", ".mp3", ".m4a"), "goi": os.path.join(APP, "am-thanh")},
    "nhac": {"duoi": (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus", ".flac"), "goi": os.path.join(APP, "nhac-mien-phi")},
}
NHOM_NHAC = ["Trend có drop", "Sôi động", "Vui tươi", "Nhẹ nhàng", "Công nghệ", "Sang trọng", "Hồi hộp"]   # thứ tự nhóm trong Thư viện › Nhạc
_TEN_OK = re.compile(r"^[^\\/:*?\"<>|\x00-\x1f]{1,120}$")
_SHA_OK = re.compile(r"^[0-9a-f]{64}$")
_KHOA = threading.Lock()
_NHO = {"k": None, "luc": 0.0, "kq": None}     # kết quả đọc kho gần nhất (đọc lại khi json đổi, hoặc sau 5 giây kiểm mtime)
_VIEC = {}                                     # (loai, file) -> {tt: cho|dang|xong|loi, da, tong, luc, loi}
_DA_KIEM = {}                                  # đường cache -> (mtime, size) đã kiểm sha256 trong phiên này
_HANG = queue.Queue()
_THO = {"t": None}
_LOG_CU = {"k": None}


def _log(s):
    try:
        ST.S.log("kho-effect: " + s)
    except Exception:
        pass


def duong():
    p = (ST.S.CFG.get("kho_effect") if ST.S else "") or ""
    return p.strip().strip('"') if isinstance(p, str) else ""


def thu_muc_cache():
    return os.path.join(ST.S.CACHE, "kho-effect")


def _real(p):
    return os.path.normcase(os.path.realpath(p))


def _trong(p, d):
    try:
        return os.path.commonpath([_real(p), _real(d)]) == _real(d)
    except ValueError:
        return False


def _doc_json(p):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _mt(p):
    try:
        return os.path.getmtime(p)
    except OSError:
        return None


def _sach(loai, tm, f, x, hong):
    """1 mục của danh sách -> dict sạch | None (ghi lý do vào hong)."""
    def bo(ly_do):
        hong.append({"loai": loai, "file": str(f)[:120], "ly_do": ly_do}); return None
    if not isinstance(f, str) or not _TEN_OK.match(f) or f.startswith(".") or ".." in f or f != f.strip():
        return bo("tên file không hợp lệ")
    if os.path.splitext(f)[1].lower() not in LOAI[loai]["duoi"]:
        return bo("đuôi file không đúng loại")
    if not isinstance(x, dict):
        return bo("mục không đúng dạng")
    sha = str(x.get("sha256") or "").lower()
    if not _SHA_OK.match(sha):
        return bo("thiếu / sai mã sha256")
    p = os.path.join(tm, f)
    if not _trong(p, tm):
        return bo("đường file thoát ra ngoài kho")
    if not os.path.exists(p):
        return bo("thiếu file (Drive chưa đồng bộ xong?)")
    y = dict(x); y["sha256"] = sha; y["_src"] = p
    b = x.get("bytes")
    y["bytes"] = int(b) if isinstance(b, int) and not isinstance(b, bool) and b > 0 else None
    return y


def doc():
    """Đọc kho (có nhớ) -> {dung, duong, co, loi, phien_ban, loai: {loai: {thu_muc, ds: {file: mục}}}, hong: [...]}."""
    d = duong()
    if not d:
        return {"dung": False, "duong": "", "co": False, "loi": "", "loai": {}, "hong": []}
    kj = os.path.join(d, "kho.json")
    now = time.time()
    with _KHOA:
        nho = _NHO["kq"]
        if nho and _NHO["k"] and _NHO["k"][0] == d and now - _NHO["luc"] < 5:
            return nho
    k = (d, _mt(kj))
    out = {"dung": True, "duong": d, "co": False, "loi": "", "loai": {}, "hong": [], "phien_ban": ""}
    try:
        if not os.path.isdir(d):
            out["loi"] = "Không thấy thư mục kho (Drive chưa đồng bộ / sai đường trong config)"
        else:
            kk = _doc_json(kj)
            if not isinstance(kk, dict) or not isinstance(kk.get("loai"), dict):
                out["loi"] = "Kho thiếu / hỏng kho.json"
            else:
                mts = []
                for loai, c in kk["loai"].items():
                    if loai not in LOAI or not isinstance(c, dict):
                        continue
                    tmr, dsr = str(c.get("thu_muc") or ""), str(c.get("ds") or "")
                    if not _TEN_OK.match(tmr) or ".." in tmr or not _TEN_OK.match(dsr) or ".." in dsr:
                        out["hong"].append({"loai": loai, "file": tmr or dsr, "ly_do": "kho.json ghi thư mục / danh sách không hợp lệ"}); continue
                    tm = os.path.join(d, tmr); pj = os.path.join(d, dsr); mts.append(_mt(pj))
                    if not _trong(tm, d) or not os.path.isdir(tm):
                        out["hong"].append({"loai": loai, "file": tmr, "ly_do": "thiếu thư mục"}); continue
                    j = _doc_json(pj)
                    m = (j.get("ds") if loai == "am_thanh" and isinstance(j, dict) and isinstance(j.get("ds"), dict) else j) if isinstance(j, dict) else None
                    if not isinstance(m, dict):
                        out["hong"].append({"loai": loai, "file": dsr, "ly_do": "thiếu / hỏng file danh sách"}); continue
                    ds = {}
                    for f, x in list(m.items())[:2000]:
                        if str(f).startswith("_"):
                            continue
                        y = _sach(loai, tm, f, x, out["hong"])
                        if y:
                            ds[f] = y
                    out["loai"][loai] = {"thu_muc": tm, "ds": ds, "nhom": (j.get("nhom") if loai == "am_thanh" and isinstance(j.get("nhom"), dict) else {})}
                k = k + tuple(mts)
                out["co"] = True
                out["phien_ban"] = str(kk.get("phien_ban") or "")[:40]
    except Exception:
        out["loi"] = "Đọc kho lỗi"; _log(traceback.format_exc())
    sig = (d, out["loi"], tuple((h["loai"], h["file"], h["ly_do"]) for h in out["hong"]))
    if sig != _LOG_CU["k"]:
        _LOG_CU["k"] = sig
        if out["loi"]:
            _log("%s — %s (dùng bản kèm app)" % (out["loi"], d))
        for h in out["hong"][:50]:
            _log("bỏ mục hỏng %s/%s: %s" % (h["loai"], h["file"], h["ly_do"]))
    with _KHOA:
        _NHO.update(k=k, luc=now, kq=out)
    return out


# ------------------------------------------------------------------ cache trên máy
def duong_cache(x, f):
    return os.path.join(thu_muc_cache(), x["sha256"][:16] + os.path.splitext(f)[1].lower())


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fo:
        for b in iter(lambda: fo.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _cache_ok(p, sha):
    try:
        st = os.stat(p)
    except OSError:
        return False
    k = (st.st_mtime, st.st_size)
    if _DA_KIEM.get(p) == k:
        return True
    if _sha_file(p) == sha:
        _DA_KIEM[p] = k
        return True
    return False


def cho_phep_cache(p, loai):
    """File p là bản cache của kho (đúng thư mục, đúng đuôi, có thật) -> được nghe / dùng trong kế hoạch."""
    if not (ST.S and isinstance(p, str) and p and os.path.splitext(p)[1].lower() in LOAI[loai]["duoi"] and os.path.isfile(p)):
        return False
    return _trong(p, thu_muc_cache())


def _chay():
    while True:
        loai, f, x = _HANG.get()
        k = (loai, f); v = _VIEC.get(k) or {}
        dich = duong_cache(x, f); tam = dich + ".tam"
        try:
            os.makedirs(thu_muc_cache(), exist_ok=True)
            if _cache_ok(dich, x["sha256"]):
                v.update(tt="xong", da=v.get("tong") or 0); continue
            v.update(tt="dang", luc=time.time(), da=0)
            h = hashlib.sha256()
            with open(x["_src"], "rb") as a, open(tam, "wb") as b:   # Drive "chỉ trên mây": lần đọc đầu có thể chờ tải
                for buf in iter(lambda: a.read(1 << 18), b""):
                    b.write(buf); h.update(buf); v["da"] = v.get("da", 0) + len(buf)
            if h.hexdigest() != x["sha256"]:
                os.remove(tam)
                _log("sai sha256 %s/%s (kho ghi %s…, file %s…): không dùng" % (loai, f, x["sha256"][:12], h.hexdigest()[:12]))
                v.update(tt="loi", loi="Sai mã kiểm: file trên Drive chưa đồng bộ xong hoặc đã bị sửa")
                continue
            os.replace(tam, dich); _DA_KIEM.pop(dich, None); _cache_ok(dich, x["sha256"])
            _log("đã chép %s/%s về máy (%.1f MB, %.1f giây)" % (loai, f, (v.get("da") or 0) / 1e6, time.time() - v["luc"]))
            v.update(tt="xong", da=v.get("tong") or v.get("da"))
        except Exception as e:
            try:
                if os.path.exists(tam):
                    os.remove(tam)
            except OSError:
                pass
            _log("chép %s/%s lỗi: %s" % (loai, f, e))
            v.update(tt="loi", loi="Không chép được từ kho (mất mạng / Drive chưa đồng bộ?)")
        finally:
            _HANG.task_done()


def chep(loai, f, lai=False):
    """Bắt đầu chép 1 mục kho về cache (nếu chưa có) -> trạng thái {tt: xong|dang|cho|loi|khong_co, pt, p, loi, giay}.
    Hỏi lại (trang hỏi tiến độ) không chép lại mục đang lỗi; lai=True (anh bấm lại) thì thử lại."""
    if loai not in LOAI:
        return {"tt": "khong_co", "loi": "Loại không hợp lệ"}
    m = ((doc().get("loai") or {}).get(loai) or {}).get("ds") or {}
    x = m.get(f)
    if not x:
        return {"tt": "khong_co", "loi": "Kho không có mục này (hoặc mục hỏng / kho chưa đồng bộ)"}
    dich = duong_cache(x, f); k = (loai, f)
    with _KHOA:
        v = _VIEC.get(k)
        if v and ((v["tt"] == "xong" and not os.path.isfile(dich)) or (v["tt"] == "loi" and lai)):
            v = None
        if not v:
            if os.path.isfile(dich) and _cache_ok(dich, x["sha256"]):
                v = _VIEC[k] = {"tt": "xong", "da": x.get("bytes") or os.path.getsize(dich), "tong": x.get("bytes") or os.path.getsize(dich)}
            else:
                tong = x.get("bytes")
                v = _VIEC[k] = {"tt": "cho", "da": 0, "tong": tong, "luc": time.time()}
                if not _THO["t"] or not _THO["t"].is_alive():
                    _THO["t"] = threading.Thread(target=_chay, name="kho-effect", daemon=True); _THO["t"].start()
                _HANG.put((loai, f, x))
    tong = v.get("tong") or 0
    out = {"tt": v["tt"], "p": dich, "pt": 100 if v["tt"] == "xong" else (int(100 * v.get("da", 0) / tong) if tong else 0)}
    if v.get("loi"):
        out["loi"] = v["loi"]
    if v["tt"] in ("cho", "dang"):
        out["giay"] = round(time.time() - (v.get("luc") or time.time()), 1)
    return out


# ------------------------------------------------------------------ gộp vào danh sách của Thư viện
def _goi_ten(loai):
    try:
        return {f for f in os.listdir(LOAI[loai]["goi"]) if os.path.splitext(f)[1].lower() in LOAI[loai]["duoi"]}
    except OSError:
        return set()


def ds_am_thanh():
    """Tiếng chỉ có ở kho (không trùng tên bản kèm app) theo dạng am_thanh.ds(): p = đường cache (cố định theo sha256)."""
    k = doc(); a = (k.get("loai") or {}).get("am_thanh")
    if not a:
        return [], {}
    goi, out = _goi_ten("am_thanh"), []
    for f, x in a["ds"].items():
        if f in goi:
            continue
        p = duong_cache(x, f)
        out.append({"p": p, "ten": str(x.get("ten") or os.path.splitext(f)[0])[:60], "nhom": str(x.get("nhom") or ""), "mo_ta": str(x.get("mo_ta") or "")[:200],
                    "giay": x.get("giay"), "dinh": x.get("dinh") or 0, "kho": f, "may": os.path.isfile(p)})
    return out, a.get("nhom") or {}


def them_nhac(out):
    """Gọi cuối sua_tay.nhac_ds(): thêm drop / nhịp đầu cho nhạc kèm app, thêm bài chỉ có ở kho vào "mien_phi" (☁ nếu chưa về máy),
    xếp theo nhóm. Lỗi kho không làm hỏng danh sách."""
    mp = out.get("mien_phi")
    if mp:   # nhac_ds giữ danh sách quét trong bộ nhớ 20 giây: không sửa thẳng vào đó (gọi lại sẽ thêm trùng)
        mp = out["mien_phi"] = dict(mp, ds=[dict(x) for x in mp.get("ds") or []])
    try:
        kk = _doc_json(os.path.join(LOAI["nhac"]["goi"], "nhac.json")) or {}
        for x in (mp or {}).get("ds") or []:
            m = kk.get(os.path.basename(x["p"])) or {}
            for kh in ("drop", "nhip_dau"):
                if kh in m:
                    x[kh] = m[kh]
        n = (doc().get("loai") or {}).get("nhac")
        if n:
            goi = {os.path.basename(x["p"]) for x in (mp or {}).get("ds") or []} | _goi_ten("nhac")
            them = []
            for f, x in n["ds"].items():
                if f in goi:
                    continue
                p = duong_cache(x, f)
                g = x.get("giay")
                them.append({"p": p, "ten": str(x.get("ten") or os.path.splitext(f)[0])[:200], "nhom": "", "kb": int((x.get("bytes") or 0) / 1024),
                             "giay": round(float(g), 2) if isinstance(g, (int, float)) and not isinstance(g, bool) else None,
                             "mo_ta": str(x.get("mo_ta") or "")[:200], "bpm": x.get("bpm"), "phong_cach": str(x.get("phong_cach") or ""),
                             "giay_phep": str(x.get("giay_phep") or "")[:200], "drop": x.get("drop") if isinstance(x.get("drop"), list) else [],
                             "nhip_dau": x.get("nhip_dau"), "kho": f, "may": os.path.isfile(p)})
            if them:
                if not mp:
                    mp = out["mien_phi"] = {"thu_muc": LOAI["nhac"]["goi"], "nguon": "mien_phi", "ds": []}
                mp["ds"] = mp["ds"] + them
        if mp and mp.get("ds"):
            thu = {g: i for i, g in enumerate(NHOM_NHAC)}
            mp["ds"] = sorted(mp["ds"], key=lambda x: thu.get(x.get("phong_cach") or "", len(thu)))
    except Exception:
        _log("gộp nhạc kho lỗi: " + traceback.format_exc()[-400:])
    return out


def trang_thai():
    k = doc()
    out = {"dung": k["dung"], "duong": k["duong"], "co": k["co"], "loi": k["loi"], "phien_ban": k.get("phien_ban", ""),
           "so": {l: len(v["ds"]) for l, v in (k.get("loai") or {}).items()}, "hong": len(k["hong"]), "hong_ds": k["hong"][:10]}
    out["chi_kho"] = {"am_thanh": len(ds_am_thanh()[0]) if k["co"] else 0}
    if k["co"] and (k.get("loai") or {}).get("nhac"):
        goi = _goi_ten("nhac"); n = k["loai"]["nhac"]["ds"]
        cn = [f for f in n if f not in goi]
        out["chi_kho"]["nhac"] = len(cn); out["tren_may"] = {"nhac": sum(1 for f in cn if os.path.isfile(duong_cache(n[f], f)))}
    try:
        fs = [os.path.join(thu_muc_cache(), f) for f in os.listdir(thu_muc_cache()) if not f.endswith(".tam")]
        out["cache"] = {"so": len(fs), "mb": round(sum(os.path.getsize(f) for f in fs) / 1e6, 1)}
    except OSError:
        out["cache"] = {"so": 0, "mb": 0}
    with _KHOA:
        out["dang_chep"] = [{"loai": l, "file": f, "tt": v["tt"], "pt": int(100 * v.get("da", 0) / v["tong"]) if v.get("tong") else 0}
                            for (l, f), v in _VIEC.items() if v.get("tt") in ("cho", "dang")]
    return out


def get(h, u, q):
    if u.path == "/api/sua-tay/kho":
        h.send(200, trang_thai())
        return True
    if u.path == "/api/sua-tay/kho/chep":
        h.send(200, chep((q.get("loai") or [""])[0], (q.get("f") or [""])[0], (q.get("lai") or [""])[0] == "1"))
        return True
    return False
