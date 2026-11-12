#!/usr/bin/env python3
"""Kiểu chữ có sẵn + font riêng từng chữ (POLY Cut 4/11) — ve_chu.py gọi, bảng mẫu / font ở kieu_chu.json.

Kế hoạch (chỉ THÊM khoá, không có khoá = vẽ y hệt cũ):
  chu.nhan_chu[i].kieu, chu.the_gia.kieu, chu.kieu_hook, chu.kieu_tieu_de = {
    "mau_co_san": id mẫu (kieu_chu.json > mau) — khoá nào dưới đây thiếu thì lấy theo mẫu,
    "font": id font (kieu_chu.json > font), "mau": màu chữ dòng 1, "mau2": màu dòng 2 (vang | trang | xanh),
    "vien": den | trang | xanh_toi | null, "vien_day": px (ở cỡ 92), "nen": null | xanh | vang | trang | toi,
    "khung": bo | vien_thuoc, "nen_vien": trang | xanh_sang | null, "bong": mem | noi | dam | null,
    "co": 0.7–1.4 (nhân cỡ chữ), "in_hoa": true | false }
  Chỉ có "font" (không mẫu / màu / nền…) = giữ nguyên cách vẽ của kiểu video, chỉ đổi font (ve_chu.font đọc FONT_RIENG).
  r36: {"bo": id} hoặc mẫu có sẵn mang "bo" (kieu_chu.json) = vẽ chữ này theo bộ mẫu mới (ve_chu.render, mau_chu_moi.py).
Phụ đề không có kiểu riêng (theo kiểu cả video, luôn IN HOA). Màu chỉ trong bảng màu Poly (render() vẫn kiem_mau).
"""
import contextlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BANG = json.load(open(os.path.join(HERE, "kieu_chu.json"), encoding="utf-8"))
FONT = {f["id"]: f for f in BANG["font"]}
MAU = {m["id"]: m for m in BANG["mau"]}
MAC_DINH = BANG["mau_mac_dinh"]
VAI = ("Black", "ExtraBold", "Bold")
MAU_CHU = ("vang", "trang", "xanh")
MAU_VIEN = ("den", "trang", "xanh_toi")
MAU_NEN = ("xanh", "vang", "trang", "toi")
# cỡ chữ (dòng 1, dòng 2), bề ngang tối đa, cỡ nhỏ nhất đọc được theo loại chữ
LOAI = {"nhan": ((92, 57), 780), "gia": ((150, 36), 640), "hook": ((92, 74), 860), "tieu_de": ((50, 34), 760)}


def _mau(VC, ten, a=255):
    c = {"vang": VC.VANG, "trang": VC.TRANG, "xanh": VC.XANH, "xanh_toi": VC.XANH_TOI, "den": VC.DEN,
         "xanh_sang": VC.XANH_SANG}[ten]
    return tuple(c[:3]) + (a,)


def thu_muc_font(VC, ten_file):
    """Thư mục có file font: thư mục font đang dùng (tham số / env) rồi tới <engine>/fonts. Không có -> None."""
    import chung
    for d in (VC.FONT_DIR, chung.FONT_DIR, os.path.join(HERE, "fonts")):
        if d and os.path.isfile(os.path.join(d, ten_file)):
            return d
    return None


def bo_font(VC, fid):
    """Bộ font kiểu BO_FONT của ve_chu cho font id: {Black/ExtraBold/Bold: (đường file, trục | None), co}. Thiếu file -> None."""
    f = FONT.get(fid)
    if not f:
        return None
    out = {"co": float(f.get("co") or 1.0)}
    for i, vai in enumerate(VAI):
        ten = f["file"][vai] if isinstance(f["file"], dict) else f["file"]
        d = thu_muc_font(VC, ten)
        if not d:
            return None
        truc = None
        if f.get("truc"):
            v = [f["dam"][i] if t == "wght" else (f.get("them") or {})[t] for t in f["truc"]]
            truc = v[0] if len(v) == 1 else tuple(v)
        out[vai] = (os.path.join(d, ten), truc)
    return out


def kiem(kv, ten, warn, VC):
    """Khoá kiểu riêng trong kế hoạch -> {} (không có / sai hết: vẽ như cũ) | {"kieu": bản sạch}. Sai thì ghi cảnh báo."""
    if not kv:
        return {}
    if not isinstance(kv, dict):
        warn.append(f"{ten}: kiểu chữ riêng phải là {{...}}, bỏ")
        return {}
    out = {}
    if kv.get("bo") is not None:   # r36: chữ này vẽ theo bộ mẫu mới (mau_chu_moi.py, engine/mau-chu/<id>.json)
        import mau_chu_moi as MCM
        if kv["bo"] in MCM.BO:
            out["bo"] = kv["bo"]
        else:
            warn.append(f"{ten}: không có bộ mẫu '{kv['bo']}', bỏ")
    m = kv.get("mau_co_san")
    if m is not None:
        if m in MAU:
            out["mau_co_san"] = m
        else:
            warn.append(f"{ten}: không có mẫu chữ '{m}', bỏ")
    f = kv.get("font")
    if f is not None:
        if f not in FONT:
            warn.append(f"{ten}: không có font '{f}', dùng font của kiểu video")
        elif not bo_font(VC, f):
            warn.append(f"{ten}: thiếu file font {FONT[f]['ten']} trong {VC.FONT_DIR} — chép từ engine/fonts; tạm dùng font của kiểu video")
        else:
            out["font"] = f
    for k, ds in (("mau", MAU_CHU), ("mau2", MAU_CHU), ("vien", MAU_VIEN + (None,)), ("nen", MAU_NEN + (None,)),
                  ("khung", ("bo", "vien_thuoc")), ("nen_vien", ("trang", "xanh_sang", None)), ("bong", ("mem", "noi", "dam", None))):
        if k in kv:
            if kv[k] in ds:
                out[k] = kv[k]
            else:
                warn.append(f"{ten}: {k} '{kv[k]}' ngoài bảng màu / kiểu Poly, bỏ")
    for k, a, b in (("vien_day", 2, 14), ("co", 0.7, 1.4)):
        if k in kv:
            try:
                out[k] = round(min(b, max(a, float(kv[k]))), 2)
            except (TypeError, ValueError):
                warn.append(f"{ten}: {k} phải là số, bỏ")
    if "in_hoa" in kv:
        out["in_hoa"] = bool(kv["in_hoa"])
    return {"kieu": out} if out else {}


def co_mau(kv):
    """Có khoá ngoài 'font' (mẫu, màu, viền, nền…) -> vẽ theo mẫu; chỉ có font -> giữ cách vẽ cũ, đổi font."""
    return isinstance(kv, dict) and any(k != "font" for k in kv)


def giai(kv):
    """Kiểu đầy đủ: mặc định <- mẫu có sẵn <- khoá ghi riêng."""
    st = dict(MAC_DINH)
    m = MAU.get(kv.get("mau_co_san"))
    if m:
        st.update({k: v for k, v in m.items() if k in MAC_DINH})
    st.update({k: v for k, v in kv.items() if k in MAC_DINH})
    if not st.get("mau2"):
        st["mau2"] = "xanh" if st["mau"] == "xanh" else ("vang" if st["mau"] == "trang" else "trang")
    return st


@contextlib.contextmanager
def doi_font(VC, fid):
    """Trong khối with: ve_chu.font() (trừ font gốc POLY STORE / ASS) dùng font fid. fid None / thiếu file: không đổi."""
    b = bo_font(VC, fid) if fid else None
    cu = VC.FONT_RIENG["v"]
    if b:
        VC.FONT_RIENG["v"] = b
    try:
        yield
    finally:
        VC.FONT_RIENG["v"] = cu


def goi(VC, kv, loai, ham, args, dong, **vt):
    """Hàm vẽ của ve_chu nhận kieu: có mẫu -> vẽ theo mẫu (ve); chỉ font -> chạy hàm cũ ham(*args) với font đó."""
    if co_mau(kv):
        im, hop = ve(VC, kv, loai, dong, **vt)
        return ([(im, "chinh")], hop) if loai == "ten_may" else (im, hop)
    with doi_font(VC, kv.get("font")):
        return ham(*args)


def ve(VC, kv, loai, dong, y=700, cx=540, co=None, sizes=None, max_w=None):
    """Vẽ chữ theo mẫu (1–2 dòng; nhãn có '|' thì 2 dòng): font + cỡ + màu chữ + viền + nền / khung + bóng. Trả (ảnh, hộp)."""
    st = giai(kv)
    loai_ = "nhan" if loai == "ten_may" else loai
    (s1, s2), mw = LOAI.get(loai_, LOAI["nhan"])
    if sizes:
        s1, s2 = sizes[0], sizes[1] if len(sizes) > 1 else s2
    if co:
        s1, s2 = co, round(co * 0.62)
    mw = max_w or mw
    L = []
    for x in dong or []:
        L += [p.strip() for p in str(x or "").split("|")] if loai_ == "nhan" else [str(x or "").strip()]
    L = [x for x in L if x][:2] or [" "]
    if st["in_hoa"] or loai_ == "tieu_de":
        L = [VC.in_hoa(x) if (i or loai_ != "gia") else x for i, x in enumerate(L)]
    if loai_ == "gia" and len(L) > 1:
        L[1] = VC.in_hoa(L[1])
    k = float(st["co"])
    s1, s2 = int(round(s1 * k)), int(round(s2 * k))
    nen = st["nen"]
    pad_x, pad_y = (max(24, round(s1 * 0.36)), max(12, round(s1 * 0.22))) if nen else (0, 0)
    vien = st["vien"]
    sw1 = max(2, round(st["vien_day"] * s1 / 92)) if vien else 0
    sw2 = max(2, round(sw1 * 0.7)) if vien else 0
    with doi_font(VC, st["font"]):
        im, d = VC.new()
        rows = []
        kf = float((VC.FONT_RIENG["v"] or VC.BO_FONT.get(VC.BO["ten"]) or VC.BO_FONT["poly_goc"]).get("co") or 1.0)
        for i, txt in enumerate(L):
            sw = sw1 if i == 0 else sw2
            s = s1 if i == 0 else min(s2, int(rows[0][1].size / kf * 0.86))  # dòng 2 không to hơn dòng 1 (dòng 1 dài bị thu)
            f, bb = VC.fit(d, txt, "Black" if i == 0 else "ExtraBold", s, mw - 2 * pad_x, sw, nho_nhat=round(s * 0.6))
            rows.append((txt, f, bb, sw))
        gap = round(s1 * 0.14)
        tw = max(bb[2] - bb[0] for _, _, bb, _ in rows)
        th = sum(bb[3] - bb[1] for _, _, bb, _ in rows) + gap * (len(rows) - 1)
        x0, y0, x1, y1 = cx - tw // 2 - pad_x, y, cx + tw // 2 + pad_x, y + th + 2 * pad_y
        if nen:
            r = (y1 - y0) // 2 if st["khung"] == "vien_thuoc" else max(14, round(s1 * 0.3))
            nv = st["nen_vien"]
            vm = {"trang": (255, 255, 255, 120), "xanh_sang": _mau(VC, "xanh_sang", 190)}.get(nv, VC.TRANG)
            if nen == "xanh":
                VC.khoi(im, (x0, y0, x1, y1), r, None, a=246, vien=2.5 if nv else 0, vien_mau=vm)
            elif nen == "toi":
                VC.khoi(im, (x0, y0, x1, y1), r, VC.XANH_TOI, a=215, vien=2.5 if nv else 0, vien_mau=vm)
            else:
                VC.khoi(im, (x0, y0, x1, y1), r, _mau(VC, nen, 245 if nen == "trang" else 255), vien=2.5 if nv else 0, vien_mau=vm)
            d = VC.ImageDraw.Draw(im)
        yy = y + pad_y
        for i, (txt, f, bb, sw) in enumerate(rows):
            x = cx - (bb[2] - bb[0]) // 2 - bb[0]
            d.text((x, yy - bb[1]), txt, font=f, fill=_mau(VC, st["mau"] if i == 0 else st["mau2"]),
                   stroke_width=sw, stroke_fill=_mau(VC, vien) if vien else None)
            yy += bb[3] - bb[1] + gap
    bong = st["bong"]
    if bong == "noi":
        im = VC.bong_noi(im)
    elif bong == "mem":
        im = VC.bong_mem(im, 4, 8, 9, 110)
    elif bong == "dam":
        out, _ = VC.new()
        out.alpha_composite(VC.bong_dam(im, 10, 5, 255))
        out.alpha_composite(VC.bong_dam(im, 3, 2, 200))
        im = out
    return im, (int(x0), int(y0), int(x1), int(y1))
