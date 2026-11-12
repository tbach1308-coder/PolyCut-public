# -*- coding: utf-8 -*-
"""Kiểu chữ có sẵn (POLY Cut 4/11) — phần máy chủ, chỉ thư viện chuẩn: sua_tay.get() chuyển 2 đường này sang đây.

GET /api/sua-tay/kieu-chu                 -> bảng mẫu chữ + font (đọc <engine>/kieu_chu.json, bộ dựng cũng vẽ theo đúng file này)
GET /api/sua-tay/kieu-chu/font/<tên file> -> file font (chỉ file có trong bảng, lấy ở <engine>/fonts) cho @font-face của trang
Trang (dev/_mod-kieu-chu.js) dùng để vẽ ô mẫu / tên font bằng đúng font mà ve_chu.py vẽ vào video.
"""
import json
import os
from urllib.parse import unquote

_NHO = {}


def _bang(S):
    e = S.engine()
    p = os.path.join(e["dir"], "kieu_chu.json")
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return None, e
    x = _NHO.get(p)
    if not x or x[0] != mt:
        try:
            with open(p, encoding="utf-8") as f:
                x = (mt, json.load(f))
        except (OSError, ValueError):
            return None, e
        _NHO[p] = x
    return x[1], e


def _file_font(b):
    ds = set()
    for f in b.get("font") or []:
        ds.update(f["file"].values() if isinstance(f["file"], dict) else [f["file"]])
    return ds


def get(h, u, S):
    """Trả True nếu đã xử lý."""
    b, e = _bang(S)
    if u.path == "/api/sua-tay/kieu-chu":
        if not b:
            h.send(404, {"err": "Bộ dựng chưa có bảng kiểu chữ (engine/kieu_chu.json) — cập nhật bộ dựng"})
            return True
        co = {f: os.path.isfile(os.path.join(e["font"], f)) for f in _file_font(b)}
        h.send(200, {"font": [dict(f, co_file=all(co.get(x) for x in (f["file"].values() if isinstance(f["file"], dict) else [f["file"]])))
                              for f in b["font"]],
                     "mau": b.get("mau") or [], "mau_mac_dinh": b.get("mau_mac_dinh") or {}})
        return True
    if u.path.startswith("/api/sua-tay/kieu-chu/font/"):
        ten = unquote(u.path[len("/api/sua-tay/kieu-chu/font/"):])
        p = os.path.join(e["font"], ten)
        if not b or ten not in _file_font(b) or not os.path.isfile(p):
            h.send(404, {"err": "không có font này"})
            return True
        with open(p, "rb") as f:
            h.send(200, f.read(), "font/ttf", {"Cache-Control": "max-age=86400"})
        return True
    return False
