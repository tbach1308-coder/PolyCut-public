#!/usr/bin/env python3
"""Biến kế hoạch dựng (ke-hoach.json) + kiểu dựng thành dòng thời gian chi tiết (dong-thoi-gian.json).

Dùng:  python3 ke_hoach.py ke-hoach.json [ra.json]

ke-hoach.json:
{
  "ten": "IMG_5123", "khung": [1080, 1920], "fps": 30,
  "nguon": {"E:/Video/IMG_5123.MP4": {"local": "/mnt/.../IMG_5123.MP4", "rong": 624, "cao": 832}},
  "canh": [{"file": "E:/Video/IMG_5123.MP4", "tu": 0, "den": 4.5}, ...],     # theo thứ tự xuất hiện
  "chu": {"hook": ["Dòng 1", "Dòng 2"], "ket": ["Ghé Poly test máy nha", "125/16/26 Bùi Đình Túy, Bình Thạnh"],
          "brand": true, "the_gia": null | {"t0": 8, "t1": 11, "gia": "15tr9", "phu": "Pin 98% · BH 6 tháng"},
          "tieu_de": "MẸO IPAD" (tùy chọn, ghim trên cùng),
          "nhan_chu": [{"t0": 4, "t1": 6, "chu": "Mẹo 1", "y": 700}] (tùy chọn, nhãn vàng to)},
          kiểu ket "the_comment" mà không ghi "ket" -> dùng câu mặc định của kênh (gu_kenh.ket_mac_dinh)
  "phu_de": [{"t0": 0.2, "t1": 2.4, "chu": "Có 15 triệu mua gì", "nhan": ["15 triệu"]}],   # tùy chọn
  "giong": null | {"local": ".../giong-doc.wav", "file": "E:/.../giong-doc.wav"},
  "nhac": {"local": ".../nhac.mp3", "ten": "…", "tu": 0, "am_luong": 1, "ha_khi_noi": true, "vao": 0.3, "ra": 1.5},  # tùy chọn (4/11)
  "can_tieng": {"giong": 1, "clip": 1},   # tùy chọn (4/11): cân to nhỏ giọng AI / tiếng clip lúc trộn (0–2)
  "am_tach": [{"id": "a1", "goc": "g1", "nguon": "E:/Video/IMG_5123.MP4", "tu": 2.2, "den": 3.6, "t": 0.5,
               "am_luong": 1, "vao": 0, "ra": 0}],   # tùy chọn (4/11, POLY Cut "Tách âm thanh"): tiếng clip đặt riêng trên video
  # (giờ t trên video đường máy chủ), cảnh có "tach_am": "g1" thì im (tiếng đã tách ra khối). Chỉ dựng máy chủ (dung_may_chu).
  "giong_de": {"cau": [{"chu", "nguon", "goc", "s0", "s1", "local", "giay", "toc"}], "vung": [{"nguon", "goc", "tu", "den", "nen"}]},
  # tùy chọn (r32, POLY Cut "Đọc lại bằng giọng AI"): giọng AI đọc lại lời trong khối tiếng tách, mỗi câu bắt đầu đúng giờ câu gốc,
  # đi theo khối (doc_lai.py). Chỉ dựng máy chủ.
  "kieu": {... từ chon_kieu.py ...},
  "ra": {"thu_muc": "E:/Tool/poly-edit/IMG_5123", "ten_file": "IMG_5123-v1.mp4"},
  "ket_giay": 3.6   # tùy chọn: thẻ kết hiện bao lâu cuối video (để cảnh hay nhất không bị thẻ che)
}
"""
import json, math, os, subprocess, sys
from chung import FFMPEG
import chuyen_moi as CM   # r35: chuyển cảnh mới 'poly-chuyen-1' (phần tìm kiểu không nạp numpy)

MAX_SHOT = {"nhanh": 2.5, "vua": 4.0}
LECH_CAT = 0.4  # giây: chỗ tách phần được dời tối đa chừng này để rơi vào khe lặng giữa 2 từ
PHAN_MIN = 1.0  # giây: phần ngắn nhất sau khi dời
_ENV = {}


# chuyển động đặt riêng từng cảnh (plan.canh[].dong): (z0, z1, x0, x1) — x > 0 = khung nhìn lệch phải
DONG_CANH = {
    "dung_yen": (1.0, 1.0, 0.0, 0.0),
    "zoom_vao": (1.0, 1.08, 0.0, 0.0),
    "zoom_ra": (1.08, 1.0, 0.0, 0.0),
    "lia_phai": (1.06, 1.06, -0.025, 0.025),
    "lia_trai": (1.06, 1.06, 0.025, -0.025),
    "phong_sat": (1.12, 1.12, 0.0, 0.0),
}

def bao_bien(local):
    """Năng lượng tiếng của file nguồn: mảng dB mỗi 10 ms (trung bình trượt 50 ms) hoặc None (không có tiếng / không đọc
    được — vd. máy chủ chưa có file). Đọc 1 lần mỗi file."""
    if not local:
        return None
    if local not in _ENV:
        env = None
        try:
            import numpy as np
            r = subprocess.run([FFMPEG, "-v", "error", "-i", local, "-vn", "-ac", "1", "-ar", "8000", "-f", "f32le", "-"],
                               capture_output=True, timeout=180)
            x = np.frombuffer(r.stdout, np.float32).astype(np.float64)
            n = len(x) // 80
            if r.returncode == 0 and n >= 50:
                p = (x[:n * 80].reshape(n, 80) ** 2).mean(1)
                p = np.convolve(p, np.ones(5) / 5, mode="same")
                env = 10 * np.log10(p + 1e-12)
        except Exception:
            env = None
        _ENV[local] = env
    return _ENV[local]


def _db(env, t):
    i = int(round(t * 100))
    return float(env[min(max(i, 0), len(env) - 1)])


def cho_lang(env, t, lo, hi):
    """Giây trong [lo, hi] mà tiếng nhỏ nhất (ưu tiên gần t: phạt 6 dB mỗi LECH_CAT giây lệch)."""
    import numpy as np
    a, b = max(0, int(lo * 100)), min(len(env) - 1, int(hi * 100))
    if b <= a:
        return t
    idx = np.arange(a, b + 1)
    diem = env[a:b + 1] + 6.0 * np.abs(idx / 100.0 - t) / LECH_CAT
    return float(idx[int(np.argmin(diem))]) / 100.0


def muc_noi(env):
    """(nền ồn, mức nói) của file: phân vị 10 và 90 của năng lượng."""
    import numpy as np
    return float(np.percentile(env, 10)), float(np.percentile(env, 90))


def tach_o_cho_lang(tu, den, parts, env):
    """Dời chỗ tách giữa các phần của 1 cảnh tới khe lặng gần nhất (±LECH_CAT, mỗi phần ≥ PHAN_MIN). Phần vẫn nối liền
    nhau (ra phần trước = vào phần sau) nên tổng độ dài không đổi; chỉ đổi chỗ cắt. 29/10: cắt giữa từ + Premiere làm
    tròn khung = tiếng vấp."""
    if env is None or len(parts) < 2:
        return parts
    nen, noi = muc_noi(env)
    cat, t = [], tu
    for j, d in enumerate(parts[:-1]):
        y = t + d
        lo = max((cat[-1] if cat else tu) + PHAN_MIN, y - LECH_CAT)
        hi = min(y + LECH_CAT, den - PHAN_MIN * (len(parts) - 1 - j))
        if _db(env, y) > nen + 0.35 * (noi - nen) and hi > lo:  # đang có tiếng: tìm khe lặng
            y = cho_lang(env, y, lo, hi)
        cat.append(y)
        t = t + d
    moc = [tu] + cat + [den]
    return [moc[i + 1] - moc[i] for i in range(len(moc) - 1)]


def canh_cat_giua_tieng(ci, c, env, out):
    """Đầu / cuối cảnh rơi giữa tiếng nói -> cảnh báo kèm chỗ lặng gần nhất (±0,5s) để agent dời tu / den."""
    if env is None:
        return
    nen, noi = muc_noi(env)
    if noi - nen < 12:  # cả file gần như cùng mức (nhạc / ồn đều): không xét
        return
    for ten, t in (("tu", c["tu"]), ("den", c["den"])):
        if _db(env, t) > nen + 0.6 * (noi - nen):
            g = cho_lang(env, t, max(0.0, t - 0.5), t + 0.5)
            if _db(env, g) < nen + 0.35 * (noi - nen) and abs(g - t) > 0.03:
                out.append(f"cảnh {ci + 1}: {'đầu' if ten == 'tu' else 'cuối'} cắt giữa tiếng nói ({t:.2f}s) — dời {ten} về "
                           f"{g:.2f}s (khe lặng) cho khỏi vấp")
            else:
                out.append(f"cảnh {ci + 1}: {'đầu' if ten == 'tu' else 'cuối'} cắt giữa tiếng nói ({t:.2f}s), ±0,5s không có "
                           "khe lặng — chọn chỗ khác hoặc để giọng đọc đè")


def split_len(d, mx):
    n = 1
    while d / n > mx:
        n += 1
    return [d / n] * n


def chon_tron(shots, plan, cfg, hook_t1, fps, noi=frozenset()):
    """Bộ chuyển cảnh trộn (tron_poly): {chỉ số cảnh: (giây, tên, match_name, xfade)} cho một phần các chỗ đổi cảnh gốc.
    Ngân sách ≈ ty_le_nhanh × số chỗ đổi cảnh: luôn có vao_bai (chỗ nối đầu sau hook) + ket (vào cảnh cuối), cách 1 lấy 1 chỗ
    có nhãn mục mới (doi_y), còn lại rải nhanh (dac_biet ≤ 1). Mỗi kiểu ≤ toi_da_moi_kieu lần, không lặp liền nhau.
    Hạt ngẫu nhiên theo tên video (dựng lại ra y hệt)."""
    import random, zlib
    if not cfg:
        return {}
    rng = random.Random(zlib.crc32(str(plan.get("ten", "")).encode()))
    nhom = cfg["nhom"]
    nhan = [float(x.get("t0", -9)) for x in ((plan.get("chu") or {}).get("nhan_chu") or [])]
    t, bd = 0.0, []
    for i, s in enumerate(shots):  # giờ bắt đầu từng cảnh (nối tiếp, như đường Premiere)
        if i > 0 and s["canh"] != shots[i - 1]["canh"] and s["canh"] >= 0 and shots[i - 1]["canh"] >= 0 and s["canh"] not in noi:
            bd.append((i, t))
        t += s.get("the_hoi") or (s["den"] - s["tu"]) + s.get("dong_bang", 0.0)
    if not bd:
        return {}
    ngan_sach = max(2, round(len(bd) * float(cfg.get("ty_le_nhanh", 0.4))))
    loai = {}
    loai[bd[-1][0]] = "ket"
    vao = next((i for i, t0 in bd if t0 >= hook_t1 - 0.2 and i != bd[-1][0]), None)
    if vao is not None:
        loai[vao] = "vao_bai"
    co_nhan = [i for i, t0 in bd if i not in loai and any(abs(t0 - x) <= 0.5 for x in nhan)]
    for i in co_nhan[1::2]:
        if len(loai) >= ngan_sach:
            break
        loai[i] = "doi_y"
    con = [i for i, _ in bd if i not in loai]
    rng.shuffle(con)
    for i in con[:max(0, ngan_sach - len(loai))]:
        loai[i] = "nhanh"
    dac = [i for i in loai if loai[i] == "nhanh"]
    if dac and rng.random() < 0.5:
        loai[rng.choice(dac)] = "dac_biet"
    out, truoc, dem = {}, None, {}
    toi_da = int(cfg.get("toi_da_moi_kieu", 3))
    for i, _ in bd:
        if i not in loai:
            continue
        ds = [x for x in nhom[loai[i]] if x["ten"] != truoc and dem.get(x["ten"], 0) < toi_da]
        ds = ds or [x for x in nhom["nhanh"] if x["ten"] != truoc and dem.get(x["ten"], 0) < toi_da] or nhom[loai[i]]
        x = rng.choice(ds)
        dem[x["ten"]] = dem.get(x["ten"], 0) + 1
        truoc = x["ten"]
        out[i] = (round(round(float(x["giay"]) * fps) / fps, 4), x["ten"], x["match"], x["xfade"])
    return out


def tron_moi_cfg(cfg, plan):
    """Cấu hình "Trộn chuyển cảnh mới" (tron_moi, r35) -> dạng chon_tron hiểu: mỗi mục {ten: id kiểu mới, giay, match, xfade}.
    Kiểu không tìm thấy (kho thiếu) thì bỏ khỏi nhóm."""
    if not cfg:
        return None
    nhom = {}
    for g, ds in (cfg.get("nhom") or {}).items():
        xs = []
        for i in ds if isinstance(ds, list) else []:
            sp = CM.tim(i, plan)
            if sp:
                xs.append({"ten": i, "giay": sp["giay"], "match": sp.get("premiere_match"), "xfade": sp.get("xfade_du_phong") or "fade"})
        nhom[g] = xs
    if not nhom.get("nhanh"):
        return None
    for g in ("vao_bai", "dac_biet", "doi_y", "ket"):
        nhom[g] = nhom.get(g) or nhom["nhanh"]
    return dict(cfg, nhom=nhom)


def dat_chuyen_moi(s, truoc, id_, sp, fps):
    """Gắn kiểu chuyển cảnh mới (r35) vào cảnh s (chỗ nối truoc -> s): giây làm tròn theo khung, không dài quá 45% cảnh ngắn;
    chép nguyên kiểu vào dòng thời gian (dung_may_chu dựng từ đây, kho đổi sau không ảnh hưởng). Bản dự phòng: xfade (máy chủ, khi
    dựng chỗ nối lỗi) + Film Impact / kiểu Premiere (đường Premiere)."""
    lim = min(s["dur"], truoc["dur"]) * 0.45
    nf = int(round(float(sp.get("giay") or 0.4) * fps))
    if nf / fps > lim:
        nf = int(math.floor(lim * fps + 1e-6))
    if nf < 3:
        return False
    s["chuyen"] = round(nf / fps, 4)
    s["chuyen_ten"], s["chuyen_moi"] = id_, CM.ban_chep(sp)
    s["chuyen_xfade"] = sp.get("xfade_du_phong") or "fade"
    if sp.get("premiere_match"):
        s["chuyen_match"] = sp["premiere_match"]
    else:
        s["chuyen_pr"] = sp.get("premiere") or "cross dissolve"
    return True


def _muot(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def lien_mach(shots, plan, k, lien, goc=None):
    """Chuyển động liền mạch cả cảnh (POLY Cut 3/11, chủ tiệm: "chạy thử video thấy bị rung"). Cảnh dài bị chia nhiều phần ≤ 2,5s;
    trước đây mỗi phần tự lia / zoom lại từ đầu (pan_ngang lia trái-phải-trái mỗi 2,3s, canh.dong zoom_vao giật về 1.0 đầu mỗi phần).
    Giờ: lấy khởi đầu của phần đầu + kết thúc của phần cuối (Z0 → Z1, X0 → X1), trải đều cả cảnh theo smoothstep; phần ứng với [a, b]
    của cảnh nhận z0 = Z(a), z1 = Z(b), easing "deu" -> nối liền, không giật. Luôn làm với cảnh có canh.dong riêng; kiểu chung
    (pan_ngang / zoom_xen_ke / zoom_vao) chỉ khi kế hoạch có dong_lien_canh. Bỏ qua: cảnh 1 phần, phần có kf / easing "bat"
    (punch_mo mở đầu), punch_nhip (cố ý theo nhịp), cảnh mở đầu montage / câu hỏi.
    goc (4/11): {chỉ số cảnh: cảnh gốc} — cảnh nối liền (noi_lien, cùng chuyển động riêng) trải chung 1 lượt với cảnh gốc."""
    goc = goc or {}
    nhom = {}
    for s in shots:
        if s.get("canh", -1) >= 0 and not s.get("montage") and not s.get("the_hoi"):
            nhom.setdefault(goc.get(s["canh"], s["canh"]), []).append(s)
    for ci, ps in nhom.items():
        if len(ps) < 2:
            continue
        c = plan["canh"][ci] if isinstance(plan["canh"][ci], dict) else {}
        if not (c.get("dong") in DONG_CANH or (lien and k.get("chuyen_dong") in ("pan_ngang", "zoom_xen_ke", "zoom_vao"))):
            continue
        # 4/11 (anh: "clip chạy bị rung như đang căn frame hình vào giữa"): trước đây cảnh có phần punch_mo / kf thì bỏ qua CẢ cảnh
        # -> các phần sau punch vẫn zoom 1.0→1.08 rồi giật về 1.0 mỗi 2,4s. Giờ: giữ nguyên phần kf / "bat", trải liền mạch từng
        # dãy phần thường liên tiếp (vd sau punch_mo mở đầu).
        day, cur = [], []
        for p in ps:
            if p.get("kf") or p.get("easing") == "bat":
                day.append(cur); cur = []
            else:
                cur.append(p)
        day.append(cur)
        for ds in day:
            if len(ds) < 2:
                continue
            Z0, Z1, X0, X1 = ds[0]["z0"], ds[-1]["z1"], ds[0]["x0"], ds[-1]["x1"]
            tong = sum(p["den"] - p["tu"] for p in ds)
            if tong <= 0:
                continue
            a = 0.0
            for p in ds:
                b = a + (p["den"] - p["tu"])
                ga, gb = _muot(a / tong), _muot(b / tong)
                p["z0"], p["z1"] = round(Z0 + (Z1 - Z0) * ga, 5), round(Z0 + (Z1 - Z0) * gb, 5)
                p["x0"], p["x1"] = round(X0 + (X1 - X0) * ga, 5), round(X0 + (X1 - X0) * gb, 5)
                p["easing"] = "deu"
                a = b


def noi_lien(plan):
    """Cảnh nối liền cảnh ngay trước (POLY Cut 4/11, anh: "chỗ chia luôn nối liền"): canh[i].noi_lien + cùng clip + tu = den cảnh trước
    (nửa sau của cảnh vừa chia mà 2 nửa đặt khác nhau). Chỗ nối đó: cắt thẳng (bỏ chuyển cảnh kiểu chung / chuyển cảnh riêng của cảnh),
    không điểm nhấn, chuyển động đi tiếp chiều cảnh trước. Kế hoạch không có khoá: tập rỗng -> dựng y hệt trước. -> set chỉ số cảnh."""
    cs, out = plan.get("canh") or [], set()
    for ci in range(1, len(cs)):
        c, tr = cs[ci], cs[ci - 1]
        if not (isinstance(c, dict) and isinstance(tr, dict) and c.get("noi_lien") and c.get("file") == tr.get("file")):
            continue
        try:
            if abs(float(c["tu"]) - float(tr["den"])) < 0.005:
                out.add(ci)
        except (KeyError, TypeError, ValueError):
            pass
    return out


def build(plan, duong=None):
    k = plan["kieu"]
    fps = plan.get("fps", 30)
    fr = 1.0 / fps
    q = lambda t: round(round(t / fr) * fr, 4)  # làm tròn theo khung hình
    shots = []
    zoom_flip = False
    canh_bao_cat = []
    # dong_lien_canh (POLY Cut 3/11, trang Sửa tay bật): chuyển động kiểu chung đổi chiều theo CẢNH (không theo phần ≤ 2,5s), rồi trải
    # liền mạch cả cảnh ở bước dưới. Kế hoạch không có cờ: y hệt trước (Claude dựng bản 1).
    lien = bool(plan.get("dong_lien_canh"))
    noi = noi_lien(plan)
    goc, flip_truoc, phan_sau = {}, None, 0   # cảnh gốc của chuỗi nối liền (cùng chuyển động riêng) / chiều zoom cảnh trước / phần kế tiếp
    for ci, c in enumerate(plan["canh"]):
        d = c["den"] - c["tu"]
        mx = MAX_SHOT[k.get("nhip", "vua")]
        if k["chuyen_dong"] == "punch_nhip" and d > 2.4:
            parts = [d / 2, d / 2] if d / 2 <= mx else split_len(d, mx / 1.0)
        else:
            parts = split_len(d, mx)
        ng = (plan.get("nguon") or {}).get(c["file"]) or {}
        env = bao_bien(ng.get("local")) if ng.get("co_tieng", True) and plan.get("cat_cho_lang", True) else None
        parts = tach_o_cho_lang(c["tu"], c["den"], parts, env)
        canh_cat_giua_tieng(ci, c, env, canh_bao_cat)
        t = c["tu"]
        tr = plan["canh"][ci - 1] if ci in noi else None
        flip_canh = flip_truoc if tr is not None and flip_truoc is not None else zoom_flip   # nối liền: zoom / lia đi tiếp chiều cảnh trước
        goc[ci] = goc[ci - 1] if tr is not None and c.get("dong") == tr.get("dong") else ci
        # nối liền mà hiệu ứng hình giống cảnh trước: đếm phần tiếp -> hiệu ứng "đầu cảnh" không chạy lại ở chỗ chia
        p0 = phan_sau if tr is not None and c.get("hieu_ung") == tr.get("hieu_ung") else 0
        for pi, pdur in enumerate(parts):
            s = {"file": c["file"], "tu": q(t), "den": q(t + pdur), "canh": ci, "phan": p0 + pi, "z0": 1.0, "z1": 1.0, "x0": 0.0, "x1": 0.0}
            # đặt riêng từng cảnh: chống rung, kiểu chuyển động, hiệu ứng hình; khung tĩnh / âm lượng / màu (POLY Cut 3/11, chỉ máy chủ)
            # + bộ lọc màu LUT `loc` (4/11, chỉ máy chủ)
            for key in ("on_dinh", "easing", "hieu_ung", "khung", "am_luong", "mau", "loc"):
                if key in c:
                    s[key] = c[key]
            if c.get("tach_am"):   # tách âm thanh (POLY Cut 4/11): tiếng cảnh đã thành khối riêng (plan.am_tach) -> cảnh im
                s["am_luong"] = 0
            cd = k["chuyen_dong"]
            if cd == "zoom_xen_ke":
                s["z0"], s["z1"] = (1.08, 1.0) if (flip_canh if lien else zoom_flip) else (1.0, 1.08)
                if not lien:
                    zoom_flip = not zoom_flip
            elif cd == "zoom_vao":
                s["z0"], s["z1"] = 1.0, 1.06
            elif cd == "punch_nhip":
                z = 1.12 if pi % 2 == 1 else 1.0
                s["z0"] = s["z1"] = z
            elif cd == "pan_ngang":
                s["z0"] = s["z1"] = 1.06
                s["x0"], s["x1"] = (0.025, -0.025) if (flip_canh if lien else zoom_flip) else (-0.025, 0.025)
                if not lien:
                    zoom_flip = not zoom_flip
            shots.append(s)
            t += pdur
        flip_truoc, phan_sau = flip_canh, p0 + len(parts)
        if lien and k["chuyen_dong"] in ("zoom_xen_ke", "pan_ngang") and ci not in noi:
            zoom_flip = not zoom_flip
    # mở đầu
    md = k["mo_dau"]
    pre = []
    hook_t1 = 3.2
    if md == "montage" and len(plan["canh"]) >= 3:
        picks = [c for c in plan["canh"][1:]]
        picks = sorted(picks, key=lambda c: -(c["den"] - c["tu"]))[:3]
        for c in picks:
            mid = (c["tu"] + c["den"]) / 2
            pre.append({"file": c["file"], "tu": q(mid - 0.25), "den": q(mid + 0.25), "canh": -1, "phan": 0,
                        "z0": 1.1, "z1": 1.1, "x0": 0.0, "x1": 0.0, "montage": True,
                        **{key: c[key] for key in ("khung", "mau", "loc") if key in c},   # khung / màu / bộ lọc riêng cảnh theo luôn
                        **({"am_luong": 0} if c.get("tach_am") else {})})   # cảnh đã tách âm thanh: mẩu mở đầu cũng im (4/11)
        hook_t1 = 1.5 + 2.7
    elif md == "dong_bang":
        shots[0]["dong_bang"] = 0.5
        hook_t1 = 0.5 + 2.7
    elif md == "hoi_truoc":
        c0 = plan["canh"][0]
        pre.append({"file": c0["file"], "tu": q(c0["tu"]), "den": q(c0["tu"] + fr), "canh": -1, "phan": 0,
                    "z0": 1.0, "z1": 1.0, "x0": 0.0, "x1": 0.0, "the_hoi": 1.2, **({"khung": c0["khung"]} if "khung" in c0 else {})})
        hook_t1 = 1.2
    elif md == "chu_zoom":
        shots[0]["z0"], shots[0]["z1"] = 1.0, 1.08
    elif md == "punch_mo":
        # xu hướng 2026: khung đầu đã có chuyển động — cảnh đầu đang cận 125% bật lùi về 104% trong 0,4s rồi trôi chậm về
        # 100% (Premiere: keyframe `kf` [giây, hệ số zoom], None = cuối cảnh; máy chủ: z0 -> z1 easing "bat" gần giống)
        shots[0]["z0"], shots[0]["z1"], shots[0]["easing"] = 1.25, 1.0, "bat"
        shots[0]["kf"] = [[0.0, 1.25], [0.4, 1.04], [None, 1.0]]
    if k["ket"] == "vong_lap" and len(shots) > 1:
        shots[-1]["z0"], shots[-1]["z1"] = 1.08, 1.0
        shots[0]["z0"] = 1.0
        shots[0].pop("kf", None)  # vòng lặp: khung đầu phải khớp khung cuối (100%) -> bỏ punch_mo
    shots = pre + shots
    # chuyển động đặt riêng từng cảnh (POLY Team 3/11, menu chuột phải "Hiệu ứng"): canh[].dong đè kiểu chung + mở đầu
    for s in shots:
        c = plan["canh"][s["canh"]] if 0 <= s.get("canh", -1) < len(plan["canh"]) else None
        dg = c.get("dong") if isinstance(c, dict) else None
        if dg in DONG_CANH:
            s["z0"], s["z1"], s["x0"], s["x1"] = DONG_CANH[dg]
            s.pop("kf", None)
            if s.get("easing") == "bat" and "easing" not in c:
                s.pop("easing", None)
    lien_mach(shots, plan, k, lien, goc)
    # độ dài từng cảnh trên timeline
    deck = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kieu_dung.json"), encoding="utf-8"))
    td = deck["chuyen_canh_ky_thuat"][k["chuyen_canh"]]["giay"]
    tron = chon_tron(shots, plan, deck["chuyen_canh_ky_thuat"].get("tron_poly"), hook_t1, fps, noi) if k["chuyen_canh"] == "tron_poly" else {}
    if k["chuyen_canh"] == "tron_moi":   # r35: trộn kiểu mới (chỉ POLY Cut chọn)
        tron = chon_tron(shots, plan, tron_moi_cfg(deck["chuyen_canh_ky_thuat"].get("tron_moi"), plan), hook_t1, fps, noi)
    chu = dict(plan.get("chu", {}))
    if k.get("ket") == "khong":  # bản máy tiệm: đơn chọn "không thẻ kết" (chon_kieu --ghim ket=khong)
        chu["ket"] = None
    if "ket" not in chu:  # không ghi câu kết -> câu mặc định theo kiểu kết (null / [] = cố ý không có thẻ kết)
        gu = deck.get("gu_kenh", {})
        if k.get("ket") == "the_comment":
            chu["ket"] = list(gu.get("ket_mac_dinh") or ["Anh em cần hỏi gì để lại comment", "Poly hỗ trợ nha ♥"])
        else:
            chu["ket"] = list(gu.get("ket_dia_chi") or ["Ghé Poly test máy nha", "125/16/26 Bùi Đình Túy, Bình Thạnh"])
    # Đường Premiere: clip đặt NỐI TIẾP (lot_a "noi"), chuyển cảnh dùng phần thừa của clip, timeline KHÔNG ngắn lại
    # -> T = tổng độ dài (tính theo khung, khớp du_doan_a của dung_premiere). Đường máy chủ (xfade chồng) trừ `chuyen`.
    duong = duong or k.get("duong") or "may_chu"
    T = 0.0
    so_khung = 0
    for i, s in enumerate(shots):
        s["dur"] = round(s.get("the_hoi") or (s["den"] - s["tu"]) + s.get("dong_bang", 0.0), 4)
        # chuyển cảnh chỉ đặt ở ranh giới giữa 2 cảnh gốc khác nhau (không giữa phần tách ra)
        s["chuyen"] = 0.0
        doi_canh = i > 0 and s["canh"] != shots[i - 1]["canh"] and s["canh"] >= 0 and shots[i - 1]["canh"] >= 0
        doi_canh = doi_canh and s["canh"] not in noi   # nối liền (4/11): cắt thẳng, không chuyển cảnh, không điểm nhấn
        s["dau_canh"] = bool(doi_canh)  # chỗ đặt điểm nhấn (chớp, rung, glitch, đập zoom)
        ov = plan["canh"][s["canh"]].get("chuyen") if doi_canh and isinstance(plan["canh"][s["canh"]], dict) else None
        # r35: kiểu mới đặt riêng cảnh (khoá không có trong bảng cũ; kế hoạch cũ không có khoá này -> nhánh cũ y hệt)
        sp_moi = CM.tim(ov, plan) if isinstance(ov, str) and ov not in deck["chuyen_canh_ky_thuat"] else None
        if ov in deck["chuyen_canh_ky_thuat"] and ov != "tron_poly":   # chuyển cảnh đặt riêng cảnh này (POLY Team 3/11)
            kt = deck["chuyen_canh_ky_thuat"][ov]
            g = float(kt.get("giay") or 0.0)
            g = round(min(g, s["dur"] * 0.45, shots[i - 1]["dur"] * 0.45), 3) if g > 0 else 0.0   # không dài quá nửa cảnh ngắn
            s["chuyen"] = g if g >= 0.08 else 0.0
            if s["chuyen"] > 0:
                s["chuyen_xfade"] = kt.get("xfade") or "fade"
                if s["chuyen_xfade"] == "custom":   # chuyển cảnh viết bằng biểu thức (tai-nguyen 3/11)
                    s["chuyen_expr"] = kt.get("expr") or ""
                    if not s["chuyen_expr"]:
                        s["chuyen_xfade"] = kt.get("xfade_du_phong") or "fade"
                s["chuyen_ten"], s["chuyen_pr"] = ov, kt.get("premiere")
        elif sp_moi:
            dat_chuyen_moi(s, shots[i - 1], ov, sp_moi, fps)
        elif doi_canh and i in tron and k["chuyen_canh"] == "tron_moi":
            sp = CM.tim(tron[i][1], plan)
            if sp:
                dat_chuyen_moi(s, shots[i - 1], tron[i][1], sp, fps)
        elif doi_canh and i in tron:
            s["chuyen"], s["chuyen_ten"], s["chuyen_match"], s["chuyen_xfade"] = tron[i]
        elif doi_canh and td > 0 and k["chuyen_canh"] != "tron_poly":
            s["chuyen"] = td
        T += s["dur"] - s["chuyen"]
        if s.get("the_hoi") or s.get("dong_bang"):  # chỉ dựng máy chủ (lot_a từ chối) — vẫn tính cho đủ
            so_khung += int(round(s["dur"] * fps))
        else:
            so_khung += int(round(s["den"] * fps)) - int(round(s["tu"] * fps))
    T = round(so_khung / fps, 4) if duong == "premiere" else round(T, 4)
    canh_bao = list(canh_bao_cat)
    hook_t1 = min(hook_t1, T)
    try:
        ket_giay = float(plan.get("ket_giay") or 3.6)
    except (TypeError, ValueError):
        ket_giay = 3.6
        canh_bao.append("ket_giay không phải số, dùng 3,6s")
    if ket_giay > 6.0:
        canh_bao.append(f"ket_giay {ket_giay}s quá dài cho thẻ kết, dùng 6s")
        ket_giay = 6.0
    ket_max = T - hook_t1 - 0.5  # thẻ kết bắt đầu sau khi hook tắt ít nhất 0,5s
    if ket_giay > ket_max:
        canh_bao.append(f"ket_giay {ket_giay}s dài quá (video {T}s, hook tới {hook_t1}s) — rút còn {max(1.0, ket_max):.1f}s")
        ket_giay = max(1.0, ket_max)
    if ket_giay < 1.5:
        canh_bao.append(f"thẻ kết chỉ {ket_giay:.1f}s, khó đọc kịp (nên ≥ 2s)")
    tl = {
        "ten": plan["ten"], "khung": plan.get("khung", [1080, 1920]), "fps": fps, "kieu": k,
        "nguon": plan["nguon"], "shots": shots, "T": T, "chu": chu,
        "phu_de": plan.get("phu_de", []), "giong": plan.get("giong"), "ra": plan.get("ra", {}),
        "hook_t": [0.0, hook_t1], "ket_t": [round(max(0.0, T - ket_giay), 3), T], "canh_bao": canh_bao,
        "duong": duong,  # premiere: chuyển cảnh không làm timeline ngắn lại (duyet.py đọc trường này)
    }
    # nhạc nền + cân tiếng (4/11) + tiếng tách (4/11) + âm thanh hiệu ứng ngắn (r20: [{local, t, am_luong}]) + giọng AI đọc lại khối tách
    # (r32, doc_lai.py), POLY Cut, chỉ dựng máy chủ: chỉ chép khi có -> kế hoạch cũ y hệt
    for kk in ("nhac", "can_tieng", "am_tach", "am_thanh", "giong_de"):
        if plan.get(kk):
            tl[kk] = plan[kk]
    return tl


def main():
    # --duong premiere|may_chu: ghi đè kieu.duong (dung_premiere.py luôn truyền --duong premiere)
    duong = sys.argv[sys.argv.index("--duong") + 1] if "--duong" in sys.argv else None
    argv = [a for i, a in enumerate(sys.argv) if not a.startswith("--") and not (i > 0 and sys.argv[i - 1] == "--duong")]
    plan = json.load(open(argv[1], encoding="utf-8"))
    tl = build(plan, duong)
    out = argv[2] if len(argv) > 2 else argv[1].replace("ke-hoach", "dong-thoi-gian")
    json.dump(tl, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"so_canh": len(tl["shots"]), "T": tl["T"], "hook": tl["hook_t"], "ket": tl["ket_t"], "canh_bao": tl["canh_bao"],
                      "ra": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
