# -*- coding: utf-8 -*-
"""Tiện ích gắn thêm của POLY Team (3/11) — chỉ thư viện chuẩn Python.

Mỗi tiện ích là 1 thư mục trong tien-ich/ (config "thu_muc_tien_ich" để đổi chỗ):
    tien-ich/<id>/tien-ich.json   {"ten", "loai": "script", "mo_ta", "phien_ban", "thang", "tac_gia", "nguon", "hoi": [...]}
    tien-ich/<id>/script.js       mã JavaScript chạy trong trình Sửa tay (Web Worker, không mạng, tối đa vài giây)
Bỏ thư mục vào là app nhận; tắt / bật lưu ở tien-ich/.trang-thai.json; xoá = chuyển vào tien-ich/.thung-rac/.
Tiện ích gốc (app kèm sẵn) nằm ở tien-ich-goc/: chép sang tien-ich/ 1 lần (ghi nhớ ở .da-chep.json), anh sửa / xoá thoải mái,
lần cập nhật app sau không chép đè.
Hướng dẫn lệnh script (cho anh và cho Claude): prompts/script-api.md.
"""
import json
import os
import re
import shutil
import threading
import time
import unicodedata

APP = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.join(APP, "tien-ich-goc")
HUONG_DAN = os.path.join(APP, "prompts", "script-api.md")
LOCK = threading.Lock()
CFG = {}
LOAI = ("script",)
NGUON = ("goc", "tu_tao", "claude")
MA_TOI_DA = 64 * 1024
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,59}$")
TEN_HOI = re.compile(r"^[a-z_][a-z0-9_]{0,30}$")


def gan_cfg(cfg):
    global CFG
    CFG = cfg


def thu_muc():
    d = CFG.get("thu_muc_tien_ich") or os.path.join(APP, "tien-ich")
    os.makedirs(d, exist_ok=True)
    return d


def _doc(p, mac=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return mac


def _ghi(p, d):
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def _ghi_chu(p, s):
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8", newline="\n") as f:
        f.write(s)
    os.replace(tam, p)


def slug(s):
    s = str(s or "").replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50].strip("-")
    return s or "tien-ich"


def _chu(x, n):
    return re.sub(r"[\x00-\x08\x0b-\x1f]", "", str(x if x is not None else "")).strip()[:n]


def sach(meta, ma=None):
    """Kiểm + gọt tien-ich.json (và mã script). Sai thì ValueError (thông báo tiếng Việt)."""
    if not isinstance(meta, dict):
        raise ValueError("tien-ich.json phải là 1 đối tượng JSON")
    loai = meta.get("loai") or "script"
    if loai not in LOAI:
        raise ValueError("Loại tiện ích chưa hỗ trợ: %s (đang có: %s)" % (loai, ", ".join(LOAI)))
    ten = _chu(meta.get("ten"), 60)
    if not ten:
        raise ValueError("Tiện ích cần có tên")
    hoi = []
    for h in (meta.get("hoi") or [])[:8]:
        if not isinstance(h, dict):
            continue
        t = str(h.get("ten") or "").strip()
        if not TEN_HOI.match(t):
            raise ValueError("Ô hỏi '%s': tên chỉ gồm chữ thường không dấu, số, gạch dưới (vd gia, toi_da)" % t)
        if any(x["ten"] == t for x in hoi):
            raise ValueError("Ô hỏi '%s' bị trùng" % t)
        k = h.get("kieu") if h.get("kieu") in ("chu", "so") else "chu"
        hoi.append({"ten": t, "nhan": _chu(h.get("nhan"), 80) or t, "mac_dinh": _chu(h.get("mac_dinh"), 120), "kieu": k})
    out = {"ten": ten, "loai": loai, "mo_ta": _chu(meta.get("mo_ta"), 400), "phien_ban": _chu(meta.get("phien_ban"), 20) or "1.0",
           "thang": _chu(meta.get("thang"), 7), "tac_gia": _chu(meta.get("tac_gia"), 40),
           "nguon": meta.get("nguon") if meta.get("nguon") in NGUON else "tu_tao", "hoi": hoi}
    if ma is not None:
        ma = str(ma).replace("\r\n", "\n")
        if len(ma.encode("utf-8")) > MA_TOI_DA:
            raise ValueError("Script dài quá 64 KB")
        if not ma.strip():
            raise ValueError("Script đang trống")
    return out, ma


# dấu vân bản gốc đã phát (script.js + tien-ich.json): bản của anh còn y nguyên bản gốc cũ thì được thay bằng bản gốc mới
GOC_DA_PHAT = {
    "bo-canh-ngan": {"6b42a389f680cb8bc125f1e71366e11bd689af5e"},
    "cat-con-x-giay": {"677490770654c7b543a13a97cfc089f4aaf16d58"},
    "chia-canh-dai": {"e1c3c2e5933b81c03383300327018cf5bbe62749"},
    "nhan-theo-mo-ta": {"0eca0890841a0481bfd369692d906c33ea1913f0"},
    "the-gia-canh-cuoi": {"146f2f22d7317f5a3b77e21cb5a32cb5be1b95e2"},
}


def _van(d):
    import hashlib
    try:
        return hashlib.sha1(open(os.path.join(d, "script.js"), "rb").read() + b"\0"
                            + open(os.path.join(d, "tien-ich.json"), "rb").read()).hexdigest()
    except OSError:
        return None


def dong_bo_goc():
    """Chép tiện ích gốc chưa từng chép sang tien-ich/ (1 lần cho mỗi id). Bản gốc có bản sửa mới (3/11) mà bản của anh còn
    y nguyên bản gốc cũ (chưa sửa tay) thì thay bằng bản mới; anh đã sửa thì giữ của anh."""
    if not os.path.isdir(GOC):
        return
    D = thu_muc()
    pd = os.path.join(D, ".da-chep.json")
    da = _doc(pd, []) or []
    van = {}
    if isinstance(da, dict):   # dạng mới: {"da": [...], "van": {id: dấu vân lúc chép}}
        da, van = list(da.get("da") or []), dict(da.get("van") or {})
    moi = False
    for ten in sorted(os.listdir(GOC)):
        g = os.path.join(GOC, ten)
        if ten.startswith(".") or not os.path.isfile(os.path.join(g, "tien-ich.json")):
            continue
        dich = os.path.join(D, ten)
        if ten in da:
            vg, vd = _van(g), _van(dich)
            cu = set(GOC_DA_PHAT.get(ten) or ()) | ({van[ten]} if van.get(ten) else set())
            if vg and vd and vd != vg and vd in cu:
                try:
                    for f in ("script.js", "tien-ich.json"):
                        shutil.copy2(os.path.join(g, f), os.path.join(dich, f))
                    van[ten] = vg
                    moi = True
                except OSError:
                    pass
            continue
        if not os.path.exists(dich):
            shutil.copytree(g, dich)
            van[ten] = _van(dich)
        da.append(ten)
        moi = True
    if moi:
        _ghi(pd, {"da": da, "van": van})


def ds():
    with LOCK:
        dong_bo_goc()
        D = thu_muc()
        trang = _doc(os.path.join(D, ".trang-thai.json"), {}) or {}
        out = []
        for ten in sorted(os.listdir(D)):
            p = os.path.join(D, ten)
            if ten.startswith(".") or not os.path.isdir(p):
                continue
            pj = os.path.join(p, "tien-ich.json")
            if not os.path.isfile(pj):
                continue
            x = {"id": ten, "bat": trang.get(ten, True) is not False, "sua_luc": round(os.path.getmtime(pj))}
            try:
                meta, _ = sach(_doc(pj))
                x.update(meta)
                if meta["loai"] == "script":
                    with open(os.path.join(p, "script.js"), encoding="utf-8-sig") as f:
                        ma = f.read()
                    _, x["ma"] = sach(meta, ma)
                    x["sua_luc"] = round(max(x["sua_luc"], os.path.getmtime(os.path.join(p, "script.js"))))
            except (OSError, ValueError) as e:
                x.update({"ten": ten, "loi": str(e) if isinstance(e, ValueError) else "Thiếu file script.js", "bat": False})
            out.append(x)
        out.sort(key=lambda x: (x.get("loi") is not None, x.get("nguon") != "goc", x.get("ten", "").lower()))
        try:
            with open(HUONG_DAN, encoding="utf-8") as f:
                hd = f.read()
        except OSError:
            hd = ""
        return {"ds": out, "thu_muc": D, "huong_dan": hd}


def ds_bat():
    """Tiện ích đang bật, không lỗi (cho Nhờ Claude)."""
    return [x for x in ds()["ds"] if x.get("bat") and not x.get("loi")]


def luu(d):
    if not isinstance(d, dict):
        raise ValueError("Dữ liệu sai")
    meta, ma = sach(d, d.get("ma") or "")
    with LOCK:
        D = thu_muc()
        id_ = str(d.get("id") or "").strip()
        if id_:
            if not ID_RE.match(id_):
                raise ValueError("Mã tiện ích sai")
        else:
            base = slug(meta["ten"])
            id_, i = base, 2
            while os.path.exists(os.path.join(D, id_)):
                id_, i = "%s-%d" % (base, i), i + 1
        p = os.path.join(D, id_)
        os.makedirs(p, exist_ok=True)
        cu = _doc(os.path.join(p, "tien-ich.json"), {}) or {}
        if cu.get("nguon") == "goc" and d.get("nguon") in (None, "goc"):
            meta["nguon"] = "goc"   # sửa tiện ích gốc: vẫn ghi là gốc, đã chép nên lần cập nhật sau không đè
        if not meta["thang"]:
            meta["thang"] = time.strftime("%Y-%m")
        _ghi(os.path.join(p, "tien-ich.json"), meta)
        _ghi_chu(os.path.join(p, "script.js"), ma)
    return {"id": id_}


def xoa(id_):
    id_ = str(id_ or "")
    if not ID_RE.match(id_):
        raise ValueError("Mã tiện ích sai")
    with LOCK:
        D = thu_muc()
        p = os.path.join(D, id_)
        if not os.path.isdir(p):
            raise ValueError("Không thấy tiện ích này")
        rac = os.path.join(D, ".thung-rac")
        os.makedirs(rac, exist_ok=True)
        shutil.move(p, os.path.join(rac, "%s-%s" % (id_, time.strftime("%Y%m%d-%H%M%S"))))
    return {"ok": True}


def bat(id_, on):
    id_ = str(id_ or "")
    if not ID_RE.match(id_):
        raise ValueError("Mã tiện ích sai")
    with LOCK:
        pt = os.path.join(thu_muc(), ".trang-thai.json")
        t = _doc(pt, {}) or {}
        if on:
            t.pop(id_, None)
        else:
            t[id_] = False
        _ghi(pt, t)
    return {"ok": True}


def get(h, u, q):
    if u.path == "/api/tien-ich":
        h.send(200, ds())
        return True
    return False


def post(h, u, data):
    p = u.path
    if p == "/api/tien-ich/luu":
        h.send(200, luu(data))
    elif p == "/api/tien-ich/xoa":
        h.send(200, xoa(data.get("id")))
    elif p == "/api/tien-ich/bat":
        h.send(200, bat(data.get("id"), bool(data.get("bat"))))
    else:
        return False
    return True
