# -*- coding: utf-8 -*-
"""DỰNG TỰ ĐỘNG — phần TỰ GẮN (POLY Cut r38, 11/11/2026; anh chọn "Dựng trọn: thô + tự gắn chữ, nhạc, chuyển cảnh", làm 2 bước).

dung_tho.py (dựng thô: bỏ khoảng lặng, ừ / à, câu nói lại, zoom nhấn, phụ đề IN HOA) gọi file này khi có --bo-kieu. Chạy bằng Python
của BỘ DỰNG (như dung_tho.py), KHÔNG tốn lượt Claude: mọi thứ là luật trên lời đã nghe (máy nghe sherpa + từ điển tiệm):
  - hook 2 dòng: tên máy nghe được (+ đời máy: Pro / M1 / 2020 / 12.9…) / con số nổi bật nhất (giá > pin > GB > inch);
  - thẻ giá lúc nghe giá ("mười ba triệu chín" -> từ điển ra 13TR9), dòng phụ = pin / GB nghe được;
  - nhãn từ khoá (PIN 98%, 256GB, 12.9 INCH) đúng lúc nghe, không đè hook / thẻ giá / thẻ kết, cách nhau đủ xa;
  - phụ đề: tô vàng từ khoá (phu_de[].nhan, có sẵn của bộ vẽ chữ);
  - chuyển cảnh riêng cảnh (canh[].chuyen, có sẵn) ở chỗ ĐỔI CLIP: dời mép 2 cảnh vào khoảng lặng để phần trộn hình / tiếng không đè
    lên lời (không đủ lặng thì thử kiểu ngắn hơn, vẫn không đủ thì cắt thẳng);
  - nhạc nền (plan.nhac, có sẵn: bộ dựng tự hạ khi có người nói, bản cuối −14 LUFS) theo nhóm nhạc;
  - âm thanh hiệu ứng (plan.am_thanh, có sẵn) ở chuyển cảnh / thẻ giá (bộ mặc định r40: vút nhẹ + két tiền, 60%);
  - thẻ kết / kiểu cả video nếu bộ kiểu có ghi.
Không thêm khoá kế hoạch mới: chỉ dùng khoá bộ dựng đã có -> kế hoạch cũ dựng y hệt.

BỘ KIỂU (preset) = khung cho bước 2: <app>/dung-tu-dong/mac-dinh.json (đầy đủ) + <tên>.json (chỉ ghi mục muốn đổi) trong
<kho effect>/dung-tu-dong/ (config "kho_effect", thư mục Google Drive của tiệm) hoặc <app>/dung-tu-dong/. Duyệt mẫu chữ / chuyển cảnh /
âm thanh mới thì chỉ đổi mã trong bộ kiểu. Mã không có trong bảng của app -> dùng mặc định + ghi cảnh báo (bảng tóm tắt (i)).
r40 (11/11, bước 2 #93 — anh duyệt mẫu mới): bộ mặc định = bộ mẫu chữ Lục bảo sang (bo_mau -> kieu.bo_mau + kieu_phu_de, khoá có sẵn của
r36, như bấm ở tab Kiểu), chuyển cảnh MỚI r35 ở chỗ đổi clip (canh[].chuyen = mã engine/chuyen-canh), vút nhẹ + tiếng tiền, nhạc Sang trọng.
Ra thêm <video>/lam/tu-dung.json: tóm tắt cho trang (tom_tat), số đo, bản "trơn" (plan_tron = như Video mới từ clip) cho nút
Hoàn tác cả lượt, ghi chép từng thứ đã gắn.
"""
import copy
import hashlib
import json
import os
import re
import subprocess

APP = os.path.dirname(os.path.abspath(__file__))
BO_DIR = os.path.join(APP, "dung-tu-dong")
MAC_DINH = "mac-dinh"
PHIEN_BAN = 1
# bộ kiểu dự phòng khi thiếu file mac-dinh.json (giống file)
BO_DU_PHONG = {
    "ten": "Mặc định", "mo_ta": "", "bo_mau": {"ma": "luc_bao", "phu_de": "lb_cum_vien"}, "zoom": {"dong": "phong_sat"},
    "hook": {"bat": True, "mau_chu": None, "toi_da_ky_tu": 22},
    "the_gia": {"bat": True, "mau_chu": None, "giay": 3.0, "phu": "tu_khoa", "som": 0.1},
    "nhan": {"bat": True, "loai": ["pin", "gb", "inch"], "mau_chu": None, "giay": 2.2, "toi_da": 4, "cach_nhau": 2.5,
             "y": 700, "co": 92, "som": 0.1},
    "phu_de": {"to_tu_khoa": True},
    "chuyen": {"bat": True, "cho": "doi_clip", "ds": ["zoom_mo_vao", "lia_ngang", "hoa_tan_mo"]},
    "nhac": {"bat": True, "nhom": "Sang trọng", "file": None, "am_luong": 0.8, "ha_khi_noi": True, "vao": 0.3, "ra": 1.5},
    "am_thanh": {"bat": True, "chuyen": "vut-nhe.wav", "gia": "ket-tien.wav", "nhan": None, "am_luong": 0.6},
    "ket": {"kieu": None, "chu": None}, "kieu_video": {}}
CHUYEN_MARGIN = 0.03   # giây: phần trộn chuyển cảnh cách tiếng nói ít nhất chừng này
CHUYEN_IM_MAX = 0.46   # giây: khoảng không lời ở chỗ chuyển cảnh không dài quá chừng này (bài thử: không im > 0,5s)
GIA_VI_TRI_DUOI = [540, 1030]   # thẻ giá hiện lúc hook còn trên màn: dời xuống dưới hook (tâm hộp, khung 1080×1920)
SP = re.compile(r"(?i)^(ipad|iphone|macbook|imac|mac|airpods|watch|galaxy|surface|laptop|pencil|keyboard)$")
DOI = re.compile(r"(?i)^(pro|max|plus|mini|air|ultra|se|gen|m\d|a\d{2}|\d{1,4}(th)?|\d{1,2}[.,]\d|s\d{1,2}|book|inch)$")


# ------------------------------------------------------------------ bộ kiểu
def _doc(p):
    try:
        with open(p, encoding="utf-8-sig") as f:
            x = json.load(f)
        return x if isinstance(x, dict) else None
    except (OSError, ValueError):
        return None


def tron(a, b):
    """Gộp sâu b đè lên a (dict con gộp tiếp, giá trị khác thay hẳn). Khoá bắt đầu bằng "_" của b bỏ qua."""
    out = copy.deepcopy(a)
    for k, v in (b or {}).items():
        if str(k).startswith("_"):
            continue
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = tron(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def ma_hop(ma):
    return isinstance(ma, str) and bool(re.fullmatch(r"[\w][\w\- .]{0,59}", ma, re.U)) and ".." not in ma


def thu_muc_bo(kho=None):
    """[(thư mục, nguồn)]: kho effect trước (đè), app sau."""
    out = []
    if kho and os.path.isdir(os.path.join(kho, "dung-tu-dong")):
        out.append((os.path.join(kho, "dung-tu-dong"), "kho"))
    out.append((BO_DIR, "app"))
    return out


def ds_bo(kho=None):
    """Các bộ kiểu dùng được -> [{ma, ten, mo_ta, nguon}] (mac-dinh đầu tiên). Cùng mã: bản trong kho effect thắng."""
    da = {}
    for d, ng in thu_muc_bo(kho):
        try:
            ten_ds = sorted(os.listdir(d))
        except OSError:
            continue
        for f in ten_ds:
            ma = os.path.splitext(f)[0]
            if not f.lower().endswith(".json") or ma in da or not ma_hop(ma) or f.startswith(("_", ".")):
                continue
            x = _doc(os.path.join(d, f))
            if x is None:
                continue
            da[ma] = {"ma": ma, "ten": str(x.get("ten") or ma)[:40], "mo_ta": str(x.get("mo_ta") or "")[:160], "nguon": ng}
    if MAC_DINH not in da:
        da[MAC_DINH] = {"ma": MAC_DINH, "ten": "Mặc định", "mo_ta": "", "nguon": "app"}
    return [da[MAC_DINH]] + [da[k] for k in sorted(da) if k != MAC_DINH]


def doc_bo(ten=None, kho=None):
    """Bộ kiểu đầy đủ: mac-dinh.json của app (thiếu thì BO_DU_PHONG) gộp với bộ <ten> (kho effect trước, app sau) hoặc file .json."""
    goc = tron(BO_DU_PHONG, _doc(os.path.join(BO_DIR, MAC_DINH + ".json")) or {})
    if ten and str(ten).lower().endswith(".json") and os.path.isfile(str(ten)):
        x, p, ma = _doc(ten), str(ten), os.path.splitext(os.path.basename(str(ten)))[0]
    else:
        ma = ten if ma_hop(ten) else MAC_DINH
        x = p = None
        for d, _ in thu_muc_bo(kho):
            q = os.path.join(d, ma + ".json")
            if os.path.isfile(q):
                x, p = _doc(q), q
                break
    bo = tron(goc, x or {})
    bo["_ma"], bo["_nguon"] = ma, p or os.path.join(BO_DIR, MAC_DINH + ".json")
    if (ten and x is None) or (p and x is None):
        bo["_canh_bao"] = ["Không đọc được bộ kiểu \"%s\": dùng bộ Mặc định" % ten]
    return bo


def _so(x, md, lo, hi):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return md
    return md if x != x else max(lo, min(hi, x))


# ------------------------------------------------------------------ bảng của app (mẫu chữ, chuyển cảnh, nhạc, âm thanh)
def bang_mau_chu(E):
    return _doc(os.path.join(E, "kieu_chu.json")) or {}


def kieu_mau(E, mau_id, cb, ten):
    """Mã mẫu chữ -> kiểu đầy đủ ghi vào kế hoạch (như trang Sửa tay kcDu: mẫu đổi sau này thì chữ đã gắn không đổi theo)."""
    if not mau_id:
        return None
    b = bang_mau_chu(E)
    m = next((x for x in b.get("mau") or [] if isinstance(x, dict) and x.get("id") == mau_id), None)
    if not m:
        cb.append("%s: không có mẫu chữ \"%s\" trong bảng mẫu của app, dùng kiểu mặc định" % (ten, mau_id))
        return None
    md = b.get("mau_mac_dinh") or {}
    kv = {"mau_co_san": m["id"]}
    for x in md:
        v = m[x] if x in m else md[x]
        if v is not None or x in ("vien", "nen", "nen_vien", "bong"):
            kv[x] = v
    if not kv.get("mau2"):
        kv["mau2"] = "xanh" if kv.get("mau") == "xanh" else "vang" if kv.get("mau") == "trang" else "trang"
    return kv


def bang_chuyen(E):
    d = _doc(os.path.join(E, "kieu_dung.json")) or {}
    kt = d.get("chuyen_canh_ky_thuat") or {}
    out = {k: v for k, v in kt.items() if isinstance(v, dict) and k not in ("cat_cung", "tron_poly") and float(v.get("giay") or 0) >= 0.08}
    for k, v in bang_chuyen_moi(E).items():   # r40: + chuyển cảnh mới r35 (mã cũ trùng thì mã cũ thắng, như ke_hoach)
        out.setdefault(k, v)
    return out


def bang_chuyen_moi(E):
    """Chuyển cảnh mới r35: engine/chuyen-canh/*.json + <kho effect>/chuyen-canh (chuyen_moi.tat_ca, như Thư viện / bộ dựng) -> {mã: {ten, giay}}.
    canh[].chuyen = mã -> ke_hoach chép kiểu vào dòng thời gian (đoạn chuyển dựng riêng). Engine cũ chưa có chuyen_moi -> {}."""
    try:
        import chuyen_moi as CM
        ds = CM.tat_ca()
    except Exception:  # noqa
        return {}
    return {k: {"ten": v.get("ten") or k, "giay": float(v.get("giay") or 0), "moi": True} for k, v in ds.items()
            if isinstance(v, dict) and float(v.get("giay") or 0) >= 0.08}


def bang_bo_mau(E):
    """Bộ mẫu chữ mới r36 (engine/mau-chu/<mã>.json, mau_chu_moi.BO) -> {mã: {ten, phu_de: [{id, ten, loai}]}}. Engine cũ -> {}."""
    try:
        import mau_chu_moi as MCM
        bo = MCM.BO
    except Exception:  # noqa
        return {}
    return {k: {"ten": v.get("ten") or k, "phu_de": [p for p in v.get("phu_de") or [] if isinstance(p, dict) and p.get("id")]}
            for k, v in bo.items() if isinstance(v, dict)}


def bang_nhac():
    d = os.path.join(APP, "nhac-mien-phi")
    kk = _doc(os.path.join(d, "nhac.json")) or {}
    out = []
    for f, x in kk.items():
        p = os.path.join(d, f)
        if isinstance(x, dict) and os.path.isfile(p):
            out.append({"p": p, "f": f, "ten": x.get("ten") or os.path.splitext(f)[0], "nhom": x.get("phong_cach") or "", "giay": x.get("giay")})
    return out


def bang_am_thanh():
    d = os.path.join(APP, "am-thanh")
    kk = (_doc(os.path.join(d, "am-thanh.json")) or {}).get("ds") or {}
    out = {}
    for f, x in kk.items():
        if isinstance(x, dict) and os.path.isfile(os.path.join(d, f)):
            y = {"p": os.path.join(d, f), "f": f, "ten": x.get("ten") or f, "dinh": float(x.get("dinh") or 0), "giay": float(x.get("giay") or 0)}
            out[f] = y
            if x.get("khoa"):
                out[x["khoa"]] = y
    return out


# ------------------------------------------------------------------ từ khoá trong lời đã nghe (đã sửa theo từ điển tiệm)
def loai_tu(ws, i):
    """Chữ ws[i] (ws = chữ đã sửa theo từ điển, cùng câu) -> (loại, chữ hiện, số chữ dùng: 1 | 2 khi ghép với chữ trước) | None.
    Loại: gia, pin, gb, inch."""
    w = str(ws[i])
    lw = w.lower().strip(",.!?")
    truoc = str(ws[i - 1]).lower() if i else ""
    if re.fullmatch(r"\d+tr\d*", lw):
        return "gia", lw.upper(), 1
    if re.fullmatch(r"\d+k", lw):
        return "gia", lw.upper(), 1
    if lw == "k" and re.fullmatch(r"\d{2,4}", truoc):
        return "gia", truoc + "K", 2
    if lw in ("triệu", "củ") and re.fullmatch(r"\d{1,3}", truoc):
        return "gia", truoc + "TR", 2
    if re.fullmatch(r"\d{1,3}([.,]\d+)?%", lw):
        return "pin", "PIN " + lw.upper(), 1
    if re.fullmatch(r"\d+(gb|tb)", lw):
        return "gb", lw.upper(), 1
    if lw in ("gb", "tb") and re.fullmatch(r"\d{2,4}", truoc):
        return "gb", truoc + lw.upper(), 2
    if re.fullmatch(r"\d{1,2}[.,]\d", lw):
        try:
            x = float(lw.replace(",", "."))
        except ValueError:
            return None
        if 7 <= x < 18:
            return "inch", lw.replace(",", ".") + " INCH", 1
    if lw == "inch" and re.fullmatch(r"\d{1,2}", truoc) and 7 <= int(truoc) < 18:
        return "inch", truoc + " INCH", 2
    return None


def ten_may_cau(ws, ten_tu_dien):
    """Tên máy trong câu: tên của từ điển tiệm (>= 2 chữ) hoặc chữ sản phẩm (iPad, MacBook…) + đời máy theo sau (Pro, M1, 2020, 12.9)."""
    cau = " ".join(str(w) for w in ws)
    for ten in ten_tu_dien:
        m = re.search(r"(?i)(?<!\w)" + re.escape(ten) + r"(?!\w)", cau)
        if m:
            sau = cau[m.end():].split()
            them = []
            for x in sau[:3]:
                if DOI.match(x) and x.lower() != "inch":
                    them.append(x)
                else:
                    break
            return " ".join([ten] + them)
    for i, w in enumerate(ws):
        if SP.match(str(w)):
            out = [str(w)]
            for x in ws[i + 1:i + 4]:
                if DOI.match(str(x)) and str(x).lower() != "inch":
                    out.append(str(x))
                else:
                    break
            if len(out) >= 2 or str(w).lower() in ("ipad", "iphone", "macbook", "imac"):
                return " ".join(out)
    return None


def ngan_chu(s, n):
    s = " ".join(str(s or "").split())
    if len(s) <= n:
        return s
    cat = s[:n + 1].rsplit(" ", 1)[0]
    return cat if cat else s[:n]


# ------------------------------------------------------------------ gắn (trước khi neo / tính giờ trên video)
def _canh_cua(D, f, a):
    for ct in D.canh:
        if ct["file"] == f and ct["tu"] - 0.02 <= a < ct["den"]:
            return ct
    return None


def _chu_video(D, DT):
    """Mọi chữ đã giữ (đã sửa theo từ điển) theo thứ tự video: [{w, a, b, file, ci, cau (chữ cả câu), i (chỉ số trong câu)}]."""
    out = []
    for p in D.tat:
        c = D.clips[p["clip"]]
        for q in p.get("cau") or []:
            ws = [str(w[0]) for w in q]
            ts = [float(w[1]) for w in q]
            for i, w in enumerate(q):
                a = float(w[1])
                if _canh_cua(D, c["file"], a) is None:
                    continue
                out.append({"w": str(w[0]), "a": a, "b": float(w[2]), "file": c["file"], "ci": c["i"], "cau": ws, "i": i, "cau_a": ts})
    return out


def gan(D, plan, DT):
    """Gắn hook, thẻ giá, nhãn, tô từ khoá phụ đề, chuyển cảnh, nhạc, kiểu theo bộ kiểu D.bo. Sửa D.canh (mép cảnh chỗ chuyển cảnh),
    D.pd (nhan), plan (chu, nhac, kieu). Giờ thẻ giá / nhãn neo theo giờ CLIP (_neo) -> ap_neo tự tính giờ trên video."""
    bo, E = D.bo_kieu, os.environ.get("POLY_ENGINE") or ""
    cb = D.tu_dung_cb = list(bo.get("_canh_bao") or [])
    G = D.tu_dung = {"bo": {"ma": bo.get("_ma"), "ten": bo.get("ten"), "nguon": bo.get("_nguon")}, "hook": None, "gia": None,
                     "nhan": [], "nhan_bo": [], "chuyen": [], "chuyen_bo": [], "nhac": None, "am_thanh": [], "to_tu_khoa": 0, "bo_mau": None}
    VC = None
    try:
        import ve_chu as VC
    except Exception:  # noqa
        pass
    hoa = (lambda s: VC.in_hoa(s)) if VC else (lambda s: str(s).upper())
    chu = plan.setdefault("chu", {})
    W = _chu_video(D, DT)
    tu_k = []   # [(loại, chữ hiện, chữ gốc)]
    for x in W:
        k = loai_tu(x["cau"], x["i"])
        if k:   # chữ số + đơn vị đứng riêng ("11 INCH"): lúc nghe = lúc nói chữ số
            a = x["cau_a"][max(0, x["i"] - k[2] + 1)]
            if _canh_cua(D, x["file"], a) is not None:
                tu_k.append(dict(x, loai=k[0], hien=k[1], a=a))
    ten_td = DT.ten_may_tu_dien(D.td or {})
    # --- hook
    hb = bo.get("hook") or {}
    if hb.get("bat", True):
        n = int(_so(hb.get("toi_da_ky_tu"), 22, 10, 40))
        l1 = None
        da_cau = set()
        for x in W:
            if tuple(x["cau"]) in da_cau:
                continue
            da_cau.add(tuple(x["cau"]))
            t = ten_may_cau(x["cau"], ten_td)
            if t:
                l1 = t
                break
        gia = next((x for x in tu_k if x["loai"] == "gia"), None)
        so = gia or next((x for x in tu_k if x["loai"] in ("pin", "gb", "inch")
                          and not (l1 and x["hien"].split()[0].lower() in l1.lower())), None)
        l2 = so["hien"] if so else ""
        if not l1:
            l1 = " ".join(W[0]["cau"]) if W else ""
        l1, l2 = ngan_chu(hoa(l1), n), ngan_chu(hoa(l2), n)
        if l1 or l2:
            chu["hook"] = [x for x in (l1, l2) if x]
            kh = kieu_mau(E, hb.get("mau_chu"), cb, "Hook")
            if kh:
                chu["kieu_hook"] = kh
            G["hook"] = {"dong": chu["hook"], "so": so and {"loai": so["loai"], "hien": so["hien"]}, "mau_chu": hb.get("mau_chu") if kh else None}
    # --- thẻ giá: lần đầu nghe giá
    gb = bo.get("the_gia") or {}
    if gb.get("bat", True):
        gia = next((x for x in tu_k if x["loai"] == "gia"), None)
        if gia:
            ct = _canh_cua(D, gia["file"], gia["a"])
            som = _so(gb.get("som"), 0.1, 0.0, 0.5)
            giay = _so(gb.get("giay"), 3.0, 1.0, 8.0)
            phu = gb.get("phu")
            if phu == "tu_khoa":
                ds = []
                for lo in ("pin", "gb"):
                    y = next((x for x in tu_k if x["loai"] == lo), None)
                    if y and y["hien"] not in ds:
                        ds.append(y["hien"])
                phu = " · ".join(ds)
            phu = hoa(str(phu or ""))[:40]
            s0 = round(max(float(ct["tu"]), gia["a"] - som), 3)
            tg = {"gia": gia["hien"], "phu": phu, "t0": 0.0, "t1": giay,
                  "_neo": {"id": ct["_id"], "file": ct["file"], "s0": s0, "s1": round(s0 + giay, 3), "cau": False}}
            kg = kieu_mau(E, gb.get("mau_chu"), cb, "Thẻ giá")
            if kg:
                tg["kieu"] = kg
            chu["the_gia"] = tg
            G["gia"] = {"hien": gia["hien"], "phu": phu, "clip": os.path.basename(gia["file"]), "a": round(gia["a"], 3), "file": gia["file"],
                        "cau": hoa(" ".join(gia["cau"])), "som": som}
    # --- nhãn từ khoá (lọc lần cuối theo giờ trên video ở sau())
    nb = bo.get("nhan") or {}
    if nb.get("bat", True):
        loai = [x for x in (nb.get("loai") or []) if x in ("pin", "gb", "inch", "gia")]
        kn = kieu_mau(E, nb.get("mau_chu"), cb, "Nhãn")
        som = _so(nb.get("som"), 0.1, 0.0, 0.5)
        giay = _so(nb.get("giay"), 2.2, 0.8, 6.0)
        da, ds = set(), []
        gia_hien = (G["gia"] or {}).get("hien")
        for x in tu_k:
            if x["loai"] not in loai or x["hien"] in da or x["hien"] == gia_hien:
                continue
            da.add(x["hien"])
            ct = _canh_cua(D, x["file"], x["a"])
            s0 = round(max(float(ct["tu"]), x["a"] - som), 3)
            it = {"chu": x["hien"], "t0": 0.0, "t1": giay, "y": int(_so(nb.get("y"), 700, 300, 1500)), "co": int(_so(nb.get("co"), 92, 60, 140)),
                  "loai": "tu_khoa", "_neo": {"id": ct["_id"], "file": ct["file"], "s0": s0, "s1": round(s0 + giay, 3), "cau": False}}
            if kn:
                it["kieu"] = kn
            ds.append(it)
            G["nhan"].append({"chu": x["hien"], "loai": x["loai"], "clip": os.path.basename(x["file"]), "a": round(x["a"], 3), "file": x["file"],
                              "som": som})
        if ds:
            chu["nhan_chu"] = ds
    # --- tô từ khoá trong phụ đề
    if (bo.get("phu_de") or {}).get("to_tu_khoa", True):
        for it in D.pd:
            ws = it["chu"].split()
            nh = []
            for i in range(len(ws)):
                k = loai_tu(ws, i)
                if k:
                    for tok in ws[i - k[2] + 1:i + 1]:   # chữ số + đơn vị đứng riêng ("11 INCH", "500 K") tô cả 2
                        if tok not in nh:
                            nh.append(tok)
            if nh:
                it["nhan"] = nh
                G["to_tu_khoa"] += 1
    # --- chuyển cảnh ở chỗ đổi clip
    gan_chuyen(D, bo, E, cb)
    # --- nhạc nền
    nh = bo.get("nhac") or {}
    if nh.get("bat", True):
        ds = bang_nhac()
        chon = None
        f = nh.get("file")
        if f:
            p = f if os.path.isabs(str(f)) else None
            if not p:
                for d in ([os.path.join(D.kho_effect, "nhac"), D.kho_effect] if getattr(D, "kho_effect", None) else []) + [os.path.join(APP, "nhac-mien-phi")]:
                    if os.path.isfile(os.path.join(d, str(f))):
                        p = os.path.join(d, str(f))
                        break
            if p and os.path.isfile(p):
                chon = next((x for x in ds if os.path.normcase(x["p"]) == os.path.normcase(p)), None) or {"p": p, "ten": os.path.splitext(os.path.basename(p))[0], "giay": None}
            else:
                cb.append("Nhạc: không thấy file \"%s\", chọn theo nhóm" % f)
        if not chon:
            nhom = [x for x in ds if x["nhom"] == nh.get("nhom")]
            if not nhom and ds:
                if nh.get("nhom"):
                    cb.append("Nhạc: không có nhóm \"%s\", chọn trong cả kho nhạc miễn phí" % nh.get("nhom"))
                nhom = ds
            if nhom:   # cùng tên video -> cùng bài; video khác -> bài khác trong nhóm
                k = int(hashlib.md5(str(getattr(D, "slug", "") or D.args.ten or "").encode("utf-8")).hexdigest(), 16) % len(nhom)
                chon = sorted(nhom, key=lambda x: x["p"])[k]
        if chon:
            p = DT.xuoi(chon["p"])
            plan["nhac"] = {"local": p, "file": p, "ten": chon["ten"], "tu": 0, "am_luong": round(_so(nh.get("am_luong"), 0.8, 0.0, 2.0), 3),
                            "ha_khi_noi": nh.get("ha_khi_noi", True) is not False, "vao": round(_so(nh.get("vao"), 0.3, 0.0, 5.0), 3),
                            "ra": round(_so(nh.get("ra"), 1.5, 0.0, 8.0), 3)}
            if chon.get("giay"):
                plan["nhac"]["giay"] = chon["giay"]
            if os.path.normcase(os.path.dirname(chon["p"])) == os.path.normcase(os.path.join(APP, "nhac-mien-phi")):
                plan["nhac"]["mien_phi"] = True
            G["nhac"] = {"ten": chon["ten"], "nhom": chon.get("nhom"), "am_luong": plan["nhac"]["am_luong"], "ha_khi_noi": plan["nhac"]["ha_khi_noi"]}
    # --- thẻ kết + kiểu cả video
    k = plan.setdefault("kieu", {})
    # --- bộ mẫu chữ mới cả video (r40 bước 2: khoá r36 kieu.bo_mau + kieu_phu_de + phu_de cụm / cả câu + ghim, như bấm ở tab Kiểu)
    bmv = bo.get("bo_mau")
    ma_bm = (bmv.get("ma") if isinstance(bmv, dict) else bmv) or None
    if ma_bm:
        bb = bang_bo_mau(E)
        if ma_bm not in bb:
            cb.append("Bộ mẫu chữ: không có bộ \"%s\" trong app, dùng mẫu chữ cũ" % ma_bm)
        else:
            pds = bb[ma_bm]["phu_de"]
            ma_pd = bmv.get("phu_de") if isinstance(bmv, dict) else None
            st = next((x for x in pds if x.get("id") == ma_pd), None)
            if ma_pd and not st:
                cb.append("Bộ mẫu chữ %s: không có kiểu phụ đề \"%s\", dùng kiểu đầu của bộ" % (bb[ma_bm]["ten"], ma_pd))
            st = st or (pds[0] if pds else None)
            k["bo_mau"] = ma_bm
            if st:
                k["kieu_phu_de"] = st["id"]
                k["phu_de"] = "ca_cau" if st.get("loai") == "cau" else "cum_ngan"
                k["_ghim"] = sorted(set(k.get("_ghim") or []) | {"phu_de"})
            G["bo_mau"] = {"ma": ma_bm, "ten": bb[ma_bm]["ten"], "phu_de": st["id"] if st else None, "ten_phu_de": (st.get("ten") or st["id"]) if st else None}
    kb = bo.get("ket") or {}
    if kb.get("kieu"):
        k["ket"] = str(kb["kieu"])
    if isinstance(kb.get("chu"), list) and any(str(x).strip() for x in kb["chu"]):
        chu["ket"] = [str(x)[:60] for x in kb["chu"][:2]]
    kv = bo.get("kieu_video") or {}
    if isinstance(kv, dict) and kv:
        deck = _doc(os.path.join(E, "kieu_dung.json")) or {}
        muc = deck.get("muc") or {}
        ghim = set(k.get("_ghim") or [])
        for m, v in kv.items():
            if m in muc and (v in muc[m] or v in DT.M.KIEU_THEM.get(m, {})):
                k[m] = v
                ghim.add(m)
            else:
                cb.append("Kiểu cả video: %s = \"%s\" không có, bỏ qua" % (m, v))
        k["_ghim"] = sorted(ghim)
    return G


def gan_chuyen(D, bo, E, cb):
    G = D.tu_dung
    cv = bo.get("chuyen") or {}
    if not cv.get("bat", True) or len(D.canh) < 2:
        return
    bang = bang_chuyen(E)
    ds = []
    for x in cv.get("ds") or []:
        if x in bang:
            ds.append(x)
        else:
            cb.append("Chuyển cảnh: không có kiểu \"%s\" trong bảng chuyển cảnh của app, bỏ" % x)
    if not ds:
        ds = [x for x in ("hoa_tan_sang", "hoa_tan_nhanh") if x in bang]
    if not ds:
        return
    moi_cho = cv.get("cho") == "moi_cho_cat"
    k = 0
    for i in range(1, len(D.canh)):
        A, B = D.canh[i - 1], D.canh[i]
        if B.get("noi_lien") or (A["file"] == B["file"] and not moi_cho):
            continue
        ten = ds[k % len(ds)]
        thu = [ten] + sorted([x for x in ds if x != ten], key=lambda x: float(bang[x].get("giay") or 0))
        thu += [x for x in ("hoa_tan_sang", "hoa_tan_nhanh") if x in bang and x not in thu]
        dat = None
        for t in thu:
            d = float(bang[t].get("giay") or 0)
            r = _cho_chuyen(D, A, B, d)
            if r:
                dat = (t, d, r)
                break
        if not dat:
            G["chuyen_bo"].append({"canh": i + 1, "ly_do": "sát tiếng nói, không có khoảng lặng đủ cho chuyển cảnh: cắt thẳng"})
            continue
        t, d, (den_a, tu_b) = dat
        A["den"], B["tu"] = round(den_a, 3), round(tu_b, 3)
        B["chuyen"] = t
        k += 1
        G["chuyen"].append({"canh": i + 1, "ma": t, "ten": bang[t].get("ten") or t, "giay": d, "clip_truoc": os.path.basename(A["file"]),
                            "clip_sau": os.path.basename(B["file"])})


def _cho_chuyen(D, A, B, d):
    """Mép mới (den A, tu B) để phần trộn d giây của chuyển cảnh chỉ đè khoảng lặng của 2 cảnh | None (không đủ lặng).
    Phần trộn = d giây cuối A + d giây đầu B. Mép chỉ được nới vào chỗ KHÔNG có tiếng (khung dưới ngưỡng của clip)."""
    cA = next(c for c in D.clips if c["file"] == A["file"])
    cB = next(c for c in D.clips if c["file"] == B["file"])
    TA, TB = cA["T"], cB["T"]
    np = __import__("numpy")
    LOI = ("loi", "tieng_dem", "tu_dem")
    # lời (vùng có chữ / tiếng đệm) trong cảnh: phần trộn không được đè. Tiếng không lời (nhạc thử loa…) thì trộn được
    ea_s = max([min(v["b"], A["den"]) for v in cA["vung"] if v["loai"] in LOI and v["a"] < A["den"] and v["b"] > A["tu"]] or [A["tu"]])
    sb_s = min([max(v["a"], B["tu"]) for v in cB["vung"] if v["loai"] in LOI and v["a"] < B["den"] and v["b"] > B["tu"]] or [B["den"]])
    # nới mép chỉ vào chỗ KHÔNG có tiếng gì: tới khung có tiếng kế tiếp (A, về sau) / trước đó (B, về trước), không quá 2 đầu clip
    sau = np.flatnonzero(TA.co[TA.f(A["den"]):])
    lim_a = min(cA["dur"] - 0.05, (TA.f(A["den"]) + int(sau[0])) * 0.01 - CHUYEN_MARGIN if len(sau) else cA["dur"] - 0.05)
    truoc = np.flatnonzero(TB.co[:TB.f(B["tu"])])
    lim_b = max(0.0, (int(truoc[-1]) + 1) * 0.01 + CHUYEN_MARGIN if len(truoc) else 0.0)
    den_a, tu_b = max(A["den"], ea_s + d + CHUYEN_MARGIN), min(B["tu"], sb_s - d - CHUYEN_MARGIN)
    if den_a > max(A["den"], lim_a) + 1e-6 or tu_b < min(B["tu"], lim_b) - 1e-6:
        return None
    # khoảng không tiếng gì trên video ở chỗ chuyển (tiếng cuối A ... tiếng đầu B, trừ phần chồng d) không dài quá
    kA = TA.co[TA.f(A["tu"]):TA.f(den_a)]
    ea_c = (TA.f(A["tu"]) + int(np.flatnonzero(kA)[-1]) + 1) * 0.01 if kA.any() else A["tu"]
    kB = TB.co[TB.f(tu_b):TB.f(B["den"])]
    sb_c = (TB.f(tu_b) + int(np.flatnonzero(kB)[0])) * 0.01 if kB.any() else B["den"]
    if (den_a - ea_c) + (sb_c - tu_b) - d > CHUYEN_IM_MAX:
        return None
    if den_a - A["tu"] < 2.3 * d or B["den"] - tu_b < 2.3 * d:   # bộ dựng rút chuyển cảnh còn 0,45 × cảnh ngắn: tính như cũ cho chắc
        return None
    return den_a, tu_b


# ------------------------------------------------------------------ sau khi có giờ trên video (ap_neo)
def sau(D, plan, p, gio, tl, moc, DT):
    """Lọc nhãn đè hook / thẻ giá / thẻ kết / nhãn khác, dời thẻ giá xuống dưới hook khi trùng giờ, âm thanh hiệu ứng.
    -> True nếu kế hoạch đổi (tính lại giờ)."""
    bo, G = D.bo_kieu, D.tu_dung
    chu = plan.get("chu") or {}
    doi = False
    h1 = float(tl["hook_t"][1]) if chu.get("hook") else 0.0
    T = float(tl["T"])
    ket0 = float(tl["ket_t"][0]) if (tl.get("chu") or {}).get("ket") else T   # bộ dựng: không có câu kết = không thẻ kết
    # thẻ kết che câu phụ đề cuối (clip hết ngay sau lời, không đủ nền 3,6s): rút thẻ kết còn phần sau câu cuối (ít nhất 2s)
    if ket0 < T:
        t1_cuoi = max([float(x.get("t1") or 0) for x in p.get("phu_de") or [] if not x.get("_an")] or [0.0])
        if t1_cuoi > ket0 + 0.05:
            moi = round(max(2.0, T - t1_cuoi - 0.05), 2)
            if moi < T - ket0 - 0.05:
                plan["ket_giay"] = moi
                G["ket_giay"] = {"giay": moi, "cu": round(T - ket0, 2)}
                ket0 = T - moi
                doi = True
    tg = chu.get("the_gia") if isinstance(chu.get("the_gia"), dict) else None
    g_gia = gio.get(tg.get("_k")) if tg else None
    if tg and g_gia and not g_gia.get("an"):
        G["gia"]["luc"] = round(g_gia["t0"], 2)
        if g_gia["t0"] < h1 - 0.05 and not tg.get("vi_tri"):
            tg["vi_tri"] = list(GIA_VI_TRI_DUOI)   # hook còn trên màn: thẻ giá xuống dưới hook (không đè)
            G["gia"]["doi_xuong"] = True
            hk = chu.get("hook") or []
            if len(hk) > 1 and hk[1] == tg["gia"]:   # hook dòng 2 đang là giá, thẻ giá đã hiện ngay: dòng 2 lấy con số khác
                khac = next((x["chu"] for x in chu.get("nhan_chu") or [] if x["chu"] not in hk), None)
                chu["hook"] = [hk[0], khac] if khac else [hk[0]]
                G["hook"]["dong"] = chu["hook"]
        if g_gia["t1"] > ket0 - 0.1 and ket0 < T:
            con = ket0 - 0.1 - g_gia["t0"]
            if con >= 1.0:
                tg["_neo"]["s1"] = round(tg["_neo"]["s0"] + con, 3)
                doi = True
    elif tg:
        G["gia"]["luc"] = None
    # nhãn: theo giờ, giữ nhãn không đè gì, tối đa toi_da
    nb = bo.get("nhan") or {}
    toi_da = int(_so(nb.get("toi_da"), 4, 0, 12))
    cach = _so(nb.get("cach_nhau"), 2.5, 0.5, 10.0)
    ds = [it for it in chu.get("nhan_chu") or []]
    giu, bo_ = [], []
    for it in sorted(ds, key=lambda x: (gio.get(x.get("_k")) or {}).get("t0") or 0):
        g = gio.get(it.get("_k")) or {}
        ly = None
        if g.get("an") or g.get("t0") is None:
            ly = "cảnh chứa chữ này đã bị cắt"
        elif g["t0"] < h1 + 0.1:
            ly = "lúc hook còn trên màn"
        elif g_gia and not g_gia.get("an") and g["t0"] < g_gia["t1"] + 0.3 and g["t1"] > g_gia["t0"] - 0.3:
            ly = "trùng lúc thẻ giá"
        elif g["t0"] > ket0 - 1.0:
            ly = "sát thẻ kết"
        elif giu and g["t0"] - giu[-1][1]["t0"] < cach:
            ly = "gần nhãn trước quá"
        elif len(giu) >= toi_da:
            ly = "đủ %d nhãn" % toi_da
        if ly:
            bo_.append((it, ly))
            continue
        if g["t1"] > ket0 - 0.2:
            it["_neo"]["s1"] = round(it["_neo"]["s0"] + max(0.8, ket0 - 0.2 - g["t0"]), 3)
            doi = True
        giu.append((it, g))
    if bo_:
        chu["nhan_chu"] = [it for it, _ in giu]
        if not chu["nhan_chu"]:
            chu.pop("nhan_chu")
        doi = True
    G["nhan"] = [dict(x, luc=round((gio.get(it.get("_k")) or {}).get("t0") or 0, 2)) for it, _ in giu for x in G["nhan"] if x["chu"] == it["chu"]]
    G["nhan_bo"] = [{"chu": it["chu"], "ly_do": ly} for it, ly in bo_]
    # giờ chuyển cảnh trên video (tóm tắt)
    canh = p.get("canh") or []
    for x in G["chuyen"]:
        i = x["canh"] - 1
        if i in moc:
            x["luc"] = round(moc[i]["dau"], 2)
    # âm thanh hiệu ứng (giờ trên video, như Thư viện › Âm thanh)
    ab = bo.get("am_thanh") or {}
    if ab.get("bat"):
        bang = bang_am_thanh()
        al = round(_so(ab.get("am_luong"), 0.6, 0.0, 2.0), 3)
        out = []

        def them(ma, t, vi):
            x = bang.get(str(ma or ""))
            if not ma:
                return
            if not x:
                D.tu_dung_cb.append("Âm thanh: không có \"%s\" trong thư viện âm thanh của app" % ma)
                return
            t = round(max(0.0, min(T - 0.05, t - x["dinh"])), 3)
            y = {"local": DT.xuoi(x["p"]), "file": DT.xuoi(x["p"]), "ten": x["ten"], "t": t, "ma": "td" + hashlib.md5(("%s%s" % (ma, t)).encode()).hexdigest()[:8]}
            if al != 1.0:
                y["am_luong"] = al
            out.append(y)
            G["am_thanh"].append({"ten": x["ten"], "luc": t, "vi": vi})
        for x in G["chuyen"]:
            if x.get("luc") is not None:
                them(ab.get("chuyen"), x["luc"] + x["giay"] / 2.0, "chuyển cảnh")
        if g_gia and not g_gia.get("an"):
            them(ab.get("gia"), g_gia["t0"], "thẻ giá")
        if ab.get("nhan"):
            for it, g in giu:
                them(ab.get("nhan"), g["t0"], "nhãn " + it["chu"])
        G["am_thanh"] = sorted(G["am_thanh"], key=lambda z: z["luc"])
        if out:
            plan["am_thanh"] = sorted(out, key=lambda y: y["t"])
    del canh
    return doi


def plan_tron(M, plan):
    """Bản "trơn" (như Video mới từ clip: mỗi clip 1 cảnh, không chữ / nhạc) ở dạng trang Sửa tay dùng -> nút Hoàn tác cả lượt."""
    p = copy.deepcopy(plan)
    M.danh_dau(p)
    p["nhac"] = None   # trang gửi khoá nhac = null: bỏ nhạc (không gửi khoá thì máy chủ giữ nhạc của ke-hoach.json)
    return p


# ------------------------------------------------------------------ kiểm bản nháp (thêm vào dung_tho.kiem)
def lufs(ff, mp4):
    r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", mp4, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr or "")
    tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr or "")
    return (float(m[-1]) if m else None), (float(tp[-1]) if tp else None)


def _video_cua(dtg, f, s):
    """Giờ clip s của file f -> giờ trên bản nháp (dòng thời gian đường máy chủ: shot chồng nhau ở chuyển cảnh) | None."""
    t = 0.0
    for sh in dtg.get("shots") or []:
        st = t - float(sh.get("chuyen") or 0.0)
        if sh.get("file") == f and float(sh["tu"]) - 0.02 <= s <= float(sh["den"]) + 0.02 and sh.get("canh", 0) >= 0:
            return st + (s - float(sh["tu"]))
        t = st + float(sh["dur"])
    return None


def kiem_them(D, DT):
    """Số đo thêm của bản nháp dựng tự động: độ to (ebur128), khoảng không lời trên video (ghép lại từ tiếng từng clip theo dòng thời gian
    bản nháp: có nhạc nền thì đo im trên tiếng bản nháp không còn đúng), thẻ giá / nhãn đúng lúc nghe, chuyển cảnh không đè lời."""
    np = DT.np
    if not isinstance(getattr(D, "kq_kiem", None), dict):
        D.kq_kiem = {}
    K = D.kq_kiem.setdefault("tu_dung", {})
    I, tp = lufs(DT.CH.FFMPEG, D.mp4)
    K["lufs"], K["dinh_dbtp"] = I, tp
    dtg = D.dtg or {}
    shots = dtg.get("shots") or []
    T = float(dtg.get("T") or 0)
    n = int(T / 0.01) + 1
    co = np.zeros(n, dtype=bool)
    t = 0.0
    cl = {c["file"]: c for c in D.clips}
    for sh in shots:
        st = t - float(sh.get("chuyen") or 0.0)
        c = cl.get(sh.get("file"))
        if c is not None and float(sh.get("am_luong", 1) or 0) > 0:
            T0 = c["T"]
            a, b = T0.f(float(sh["tu"])), T0.f(float(sh["den"]))
            seg = T0.co[a:b]
            i0 = int(round(st / 0.01))
            j = min(n, i0 + len(seg))
            if j > i0 >= 0:
                co[i0:j] |= seg[:j - i0]
        t = st + float(sh["dur"])
    cuoi = T - 0.3 - (D.duoi["giay"] if D.duoi else 0.0)
    q = (~co).astype(np.int8)
    idx = np.flatnonzero(np.diff(np.concatenate([[0], q, [0]])))
    im = [(s * 0.01, e * 0.01) for s, e in zip(idx[0::2], idx[1::2]) if s * 0.01 < cuoi and s > 0]
    K["im_loi"] = [{"tu": round(x, 2), "den": round(min(y, cuoi), 2), "giay": round(min(y, cuoi) - x, 2)} for x, y in im if min(y, cuoi) - x > 0.5]
    K["im_loi_dai_nhat"] = round(max([0.0] + [min(y, cuoi) - x for x, y in im]), 2)
    # thẻ giá / nhãn: giờ hiện trên bản nháp (dòng thời gian bản nháp) so với lúc nghe chữ (giờ clip -> giờ bản nháp)
    chu = dtg.get("chu") or {}
    G = D.tu_dung
    if G.get("gia"):
        mong = _video_cua(dtg, G["gia"]["file"], G["gia"]["a"])
        tg = chu.get("the_gia") or {}
        K["the_gia"] = {"gia": G["gia"]["hien"], "luc_nghe": None if mong is None else round(mong, 2), "luc_hien": tg.get("t0"),
                        "lech": None if mong is None or tg.get("t0") is None else round(float(tg["t0"]) + G["gia"]["som"] - mong, 3)}
    K["nhan"] = []
    for x in G.get("nhan") or []:
        mong = _video_cua(dtg, x["file"], x["a"])
        it = next((y for y in chu.get("nhan_chu") or [] if y.get("chu") == x["chu"]), None)
        K["nhan"].append({"chu": x["chu"], "luc_nghe": None if mong is None else round(mong, 2), "luc_hien": it and it.get("t0"),
                          "lech": None if mong is None or not it else round(float(it["t0"]) + x["som"] - mong, 3)})
    # chuyển cảnh: phần trộn không đè LỜI của 2 cảnh (vùng có chữ / tiếng đệm; tiếng không lời như nhạc thử loa thì trộn được)
    LOI = ("loi", "tieng_dem", "tu_dem")

    def loi_trong(c, x, y):
        return round(sum(max(0.0, min(y, v["b"]) - max(x, v["a"])) for v in c["vung"] if v["loai"] in LOI), 3)
    de = []
    t = 0.0
    for k, sh in enumerate(shots):
        d = float(sh.get("chuyen") or 0.0)
        st = t - d
        if d > 0 and k:
            tr = shots[k - 1]
            for x, f, s0 in ((tr, tr["file"], float(tr["den"]) - d), (sh, sh["file"], float(sh["tu"]))):
                c = cl.get(f)
                if c is not None and loi_trong(c, s0, s0 + d) > 0:
                    de.append({"luc": round(st, 2), "clip": os.path.basename(f), "giay_loi": loi_trong(c, s0, s0 + d),
                               "khung_co_tieng": c["T"].so_khung_co(s0, s0 + d)})
        t = st + float(sh["dur"])
    K["chuyen"] = {"so": sum(1 for s in shots if float(s.get("chuyen") or 0) > 0), "de_loi": de}
    K["nhac"] = bool(dtg.get("nhac"))
    return K


# ------------------------------------------------------------------ tóm tắt cho trang + báo cáo
def tom_tat(D, DT):
    G, s = D.tu_dung, D.so_do
    gio = DT.gio
    out = []
    dem = sum(1 for b in D.bo if b["loai"] in ("tieng_dem", "tu_dem"))
    lap = sum(1 for b in D.bo if b["loai"] == "lap")
    im = D.khoang_im()
    ngung = len(im) + dem + lap
    out.append({"loai": "cat", "chu": "Đã bỏ %d chỗ ngập ngừng · %ss → %ss" % (ngung, DT.so_vn(s["dai_truoc"], 0), DT.so_vn(s["dai_sau"], 0)),
                "chi_tiet": "Khoảng lặng: %d chỗ (%ss); ừ / à / ờ: %d; lặp chữ: %d. Video %ss → %ss, %d chỗ cắt. Chỗ cắt luôn ở khoảng im, không cắt giữa chữ."
                % (len(im), DT.so_vn(sum(y - x for _, x, y in im)), dem, lap, DT.so_vn(s["dai_truoc"]), DT.so_vn(s["dai_sau"]), s["so_cho_cat"])})
    for r in D.noi_lai[:3]:
        out.append({"loai": "noi_lai", "chu": "Câu nói lại: giữ lần %d “%s”" % (r["lan_giu"], DT.ngan(D.in_hoa(r["giu"]["chu"]), 34)),
                    "chi_tiet": "Bỏ lần %d (%s %s–%s: %s). Giữ lần %d (%s %s–%s) vì %s." % (
                        3 - r["lan_giu"], r["bo"]["clip"], gio(r["bo"]["tu"]), gio(r["bo"]["den"]), r["loi_lan_bo"], r["lan_giu"],
                        r["giu"]["clip"], gio(r["giu"]["tu"]), gio(r["giu"]["den"]), r["ly_do"])})
    if G.get("bo_mau"):
        b = G["bo_mau"]
        out.append({"loai": "mau", "chu": "Mẫu chữ: bộ %s" % b["ten"],
                    "chi_tiet": "Hook, thẻ giá, nhãn, phụ đề%s vẽ theo bộ %s. Đổi bộ: tab Kiểu › Bộ mẫu chữ (Ctrl+Z về như cũ)."
                    % (" (" + b["ten_phu_de"] + ")" if b.get("ten_phu_de") else "", b["ten"])})
    if G.get("hook"):
        out.append({"loai": "hook", "chu": "Hook: " + " / ".join(G["hook"]["dong"]),
                    "chi_tiet": "Dòng 1: tên máy nghe được (không có thì câu đầu). Dòng 2: con số nổi bật nhất nghe được (giá > pin > GB > inch). "
                                "Hiện 3 giây đầu%s." % (", mẫu chữ " + G["hook"]["mau_chu"] if G["hook"].get("mau_chu") else "")})
    if G.get("gia"):
        g = G["gia"]
        out.append({"loai": "gia", "chu": "Thẻ giá %s lúc %s" % (g["hien"], gio(g["luc"]) if g.get("luc") is not None else "?"),
                    "chi_tiet": "Nghe giá trong câu “%s” (%s giây %s)%s%s." % (DT.ngan(g["cau"], 60), g["clip"], DT.so_vn(g["a"]),
                                                                             "; dòng phụ: " + g["phu"] if g.get("phu") else "",
                                                                             "; hook còn trên màn nên thẻ giá đặt dưới hook" if g.get("doi_xuong") else "")})
    else:
        out.append({"loai": "gia", "chu": "Không nghe thấy giá: chưa gắn thẻ giá", "chi_tiet": "Nói giá (vd “mười ba triệu chín”) thì tự gắn thẻ giá đúng lúc nói. Gắn tay: phím G."})
    if G.get("nhan") or G.get("nhan_bo"):
        out.append({"loai": "nhan", "chu": ("Nhãn: " + ", ".join("%s lúc %s" % (x["chu"], gio(x["luc"])) for x in G["nhan"][:4])) if G["nhan"] else "Không gắn nhãn",
                    "chi_tiet": ("Nhãn từ khoá đúng lúc nghe (pin, GB, inch), phụ đề tô vàng từ khoá ở %d câu." % G["to_tu_khoa"])
                    + ((" Không gắn: " + "; ".join("%s (%s)" % (x["chu"], x["ly_do"]) for x in G["nhan_bo"][:6]) + ".") if G["nhan_bo"] else "")})
    if s.get("so_zoom"):
        z = [x for x in D.dj["zoom"] if x["zoom"]] if getattr(D, "dj", None) else []
        out.append({"loai": "zoom", "chu": "Zoom nhấn %d chỗ" % s["so_zoom"],
                    "chi_tiet": "Phóng sát ở câu có giá / pin / GB / inch / tên máy: " + "; ".join("%s “%s”" % (gio(x["luc"]), DT.ngan(x["cau"], 30)) for x in z[:5])})
    if G.get("chuyen") or G.get("chuyen_bo"):
        out.append({"loai": "chuyen", "chu": "Chuyển cảnh %d chỗ giữa các clip" % len(G["chuyen"]),
                    "chi_tiet": "; ".join("%s %s (%s → %s)" % (gio(x.get("luc") or 0), x["ten"], x["clip_truoc"], x["clip_sau"]) for x in G["chuyen"])
                    + (". Mép cảnh dời vào khoảng lặng để phần chuyển không đè lời." if G["chuyen"] else "")
                    + ((" Cắt thẳng: " + "; ".join("cảnh %d (%s)" % (x["canh"], x["ly_do"]) for x in G["chuyen_bo"])) if G["chuyen_bo"] else "")})
    if G.get("nhac"):
        n = G["nhac"]
        out.append({"loai": "nhac", "chu": "Nhạc nền: %s" % n["ten"],
                    "chi_tiet": "Nhóm %s, mức %d%%%s. Bản xuất tự cân về −14 LUFS." % (n.get("nhom") or "?", round(n["am_luong"] * 100),
                                                                                  ", tự hạ khi có người nói" if n["ha_khi_noi"] else "")})
    if G.get("am_thanh"):
        out.append({"loai": "am_thanh", "chu": "Âm thanh hiệu ứng %d chỗ" % len(G["am_thanh"]),
                    "chi_tiet": "; ".join("%s %s (%s)" % (gio(x["luc"]), x["ten"], x["vi"]) for x in G["am_thanh"][:8])})
    kg = G.get("ket_giay")
    out.append({"loai": "pd", "chu": "Phụ đề %d câu IN HOA" % s["so_cau_phu_de"],
                "chi_tiet": "Theo lời nghe, sửa theo từ điển tiệm (13TR9, 98%, 256GB, iPad Pro…). Chữ nghe sai: sửa ở tab Phụ đề."
                + (" Thẻ kết rút còn %ss để không che câu cuối." % DT.so_vn(kg["giay"]) if kg else "")})
    cb = list(dict.fromkeys(D.tu_dung_cb))
    out.append({"loai": "bo", "chu": "Bộ kiểu: %s" % (G["bo"].get("ten") or G["bo"].get("ma")),
                "chi_tiet": "File: %s.%s" % (G["bo"].get("nguon"), (" Lưu ý: " + "; ".join(cb)) if cb else "")})
    return out


def ghi(D, DT):
    """lam/tu-dung.json (trang đọc: bảng tóm tắt + Hoàn tác cả lượt) + mục "Tự gắn" trong BAO-CAO.md."""
    tt = tom_tat(D, DT)
    pt = getattr(D, "plan_tron", None)
    bang = DT.doc_doi_duong(D.args.doi_duong)
    if pt and bang:
        pt = D._doi_duong_plan(pt, bang)
    o = {"phien_ban": PHIEN_BAN, "luc": D.dj.get("luc"), "slug": D.slug, "bo": D.tu_dung["bo"], "tom_tat": tt, "so_do": D.so_do,
         "gan": {k: v for k, v in D.tu_dung.items() if k != "bo"}, "canh_bao": list(dict.fromkeys(D.tu_dung_cb)),
         "kiem": (getattr(D, "kq_kiem", None) or {}).get("tu_dung"), "plan_tron": pt}
    DT.M.ghi(os.path.join(D.v, "lam", "tu-dung.json"), o)
    with open(os.path.join(D.v, "BAO-CAO.md"), "a", encoding="utf-8") as f:
        f.write("\n## Tự gắn (Dựng tự động, bộ kiểu %s)\n" % (D.tu_dung["bo"].get("ten") or D.tu_dung["bo"].get("ma")))
        for x in tt:
            f.write("- %s. %s\n" % (x["chu"], x["chi_tiet"]))
        K = o["kiem"]
        if K:
            f.write("- Kiểm: độ to %s LUFS (đỉnh %s dBTP); khoảng không lời > 0,5s: %d (dài nhất %ss); chuyển cảnh %d chỗ, đè lời %d; thẻ giá lệch %s s.\n" % (
                K.get("lufs"), K.get("dinh_dbtp"), len(K.get("im_loi") or []), K.get("im_loi_dai_nhat"), K["chuyen"]["so"], len(K["chuyen"]["de_loi"]),
                (K.get("the_gia") or {}).get("lech")))
    return o
