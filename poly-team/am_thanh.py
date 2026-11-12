# -*- coding: utf-8 -*-
"""POLY Cut — ÂM THANH HIỆU ỨNG ngắn (4/11/2026 tối, r20, anh: "thư viện hiệu ứng nhạc chuyển cảnh còn ít quá"), phần máy chủ,
chỉ thư viện chuẩn.

  GET /api/sua-tay/am-thanh-ds          -> {ds: [{p, ten, nhom, mo_ta, giay, dinh}], nhom: {khoá: tên}}   Thư viện › Âm thanh
  GET /api/sua-tay/am-thanh?p=<file>    -> file WAV (nghe thử / khung xem trước). Chỉ file trong <app>/am-thanh/.

Kế hoạch: plan.am_thanh = [{ma, local, file, ten, t (giây trên video), am_luong 0–2}] (tùy chọn, tối đa 200). Bộ dựng (engine
ke_hoach.build chép khoá, dung_may_chu.build trộn đúng giây t) chỉ thêm filter khi kế hoạch có khoá -> kế hoạch cũ dựng y hệt.
15 tiếng do Poly Store tự tổng hợp (dev/tao_am_thanh.py, CC0) nằm ở <app>/am-thanh/ + am-thanh.json (tên hiện, nhóm, mô tả).
sua_tay.py chỉ thêm 3 dòng móc nối: get (đường /api/sua-tay/am-thanh…) + kiem_ke_hoach (kiem(plan)).
"""
import json
import os

APP = os.path.dirname(os.path.abspath(__file__))
AM_DIR = os.path.join(APP, "am-thanh")
DUOI = (".wav", ".mp3", ".m4a")
MIME = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4"}
TOI_DA = 200


def _norm(p):
    return os.path.normcase(os.path.realpath(p))


def cho_phep(p):
    """File âm thanh p được dùng / phát không: đuôi âm thanh, có thật, nằm ngay trong <app>/am-thanh/ (hoặc bản cache của Kho effect
    trên Drive, r37: kho.py chép về <app>/_cache/kho-effect sau khi kiểm sha256)."""
    if not (isinstance(p, str) and p and os.path.splitext(p)[1].lower() in DUOI and os.path.isfile(p)):
        return False
    try:
        if os.path.commonpath([_norm(p), _norm(AM_DIR)]) == _norm(AM_DIR):
            return True
    except ValueError:
        pass
    try:
        import kho
        return kho.cho_phep_cache(p, "am_thanh")
    except Exception:
        return False


def ds():
    try:
        with open(os.path.join(AM_DIR, "am-thanh.json"), encoding="utf-8-sig") as f:
            kk = json.load(f) or {}
    except (OSError, ValueError):
        kk = {}
    m = kk.get("ds") or {}
    out = []
    for f, x in m.items():
        p = os.path.join(AM_DIR, f)
        if not isinstance(x, dict) or not cho_phep(p):
            continue
        out.append({"p": p, "ten": str(x.get("ten") or f)[:60], "nhom": str(x.get("nhom") or ""), "mo_ta": str(x.get("mo_ta") or "")[:200],
                    "giay": x.get("giay"), "dinh": x.get("dinh") or 0})
    nhom = dict(kk.get("nhom") or {})
    try:   # r37: tiếng chỉ có ở Kho effect (Drive) — p = đường cache, may = đã chép về máy chưa (Thư viện hiện ☁)
        import kho
        them, nk = kho.ds_am_thanh()
        out += them
        for k, v in nk.items():
            nhom.setdefault(k, v)
    except Exception:
        pass
    return {"ds": out, "nhom": nhom}


def _so(x, lo, hi):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x:
        return None
    return round(max(lo, min(hi, float(x))), 3)


def kiem(plan):
    """Gọi trong sua_tay.kiem_ke_hoach: plan.am_thanh -> danh sách sạch (file lạ / ngoài <app>/am-thanh bị bỏ). Trang không gửi khoá
    thì không đụng (kế hoạch cũ không có khoá này)."""
    if "am_thanh" not in plan:
        return
    vao = plan.get("am_thanh") if isinstance(plan.get("am_thanh"), list) else []
    out = []
    for x in vao[:TOI_DA]:
        if not isinstance(x, dict) or not cho_phep(x.get("local")):
            continue
        t = _so(x.get("t"), 0.0, 36000.0)
        if t is None:
            continue
        y = {"local": x["local"], "file": x["local"], "ten": str(x.get("ten") or os.path.splitext(os.path.basename(x["local"]))[0])[:60], "t": t}
        al = _so(x.get("am_luong"), 0.0, 2.0)
        if al is not None and al != 1.0:
            y["am_luong"] = al
        if isinstance(x.get("ma"), str) and x["ma"][:24]:
            y["ma"] = x["ma"][:24]
        out.append(y)
    if out:
        plan["am_thanh"] = sorted(out, key=lambda y: y["t"])
    else:
        plan.pop("am_thanh", None)


def get(h, u, q):
    if u.path == "/api/sua-tay/am-thanh-ds":
        h.send(200, ds())
        return True
    if u.path == "/api/sua-tay/am-thanh":
        p = (q.get("p") or [""])[0]
        if not cho_phep(p):
            h.send(403, {"err": "Không phát được file này (chỉ âm thanh kèm app trong thư mục am-thanh)"})
            return True
        h.send_file(p, MIME.get(os.path.splitext(p)[1].lower(), "application/octet-stream"))
        return True
    return False
