# -*- coding: utf-8 -*-
"""Phần "Sửa tay" của POLY Team chạy bằng Python của BỘ DỰNG (engine/.venv) — app (server.py, Python thường) gọi file này.

2 cách chạy:
  python sua_tay_may.py phuc-vu            mỗi dòng stdin 1 lệnh JSON {"id", "lenh", "data"} -> mỗi dòng stdout 1 kết quả
                                           (xem trước: dòng thời gian, vẽ chữ, gắn câu vào cảnh, lưu kế hoạch, tạo video mới)
  python sua_tay_may.py xuat <viec.json>   dựng video bằng ffmpeg (dung_may_chu.py) — in BUOC=… / LOI=… / XONG={…}

Nguyên tắc: không đổi bộ dựng. Mọi thứ đọc / ghi đúng file của đường dựng hiện có:
  <thư mục video>/lam/ke-hoach.json  (kế hoạch Claude viết, anh sửa tay ở đây)   ->  dong-thoi-gian / lop-chu  ->  mp4
Câu phụ đề, nhãn, thẻ giá được "neo" vào cảnh theo giờ của CLIP GỐC (_neo = {id cảnh, file, s0, s1, tu}): anh cắt / đổi chỗ
cảnh thì chữ đi theo đúng lời, không lệch. Video giọng AI: phụ đề theo giọng (giờ trên video), không neo.
Chuỗi bắt đầu bằng "_" (_id, _k, _neo) chỉ dùng khi đang sửa, ghi ke-hoach.json thì bỏ.
"""
import collections, contextlib, copy, datetime, hashlib, json, os, re, shutil, subprocess, sys, time, traceback, uuid

E = os.environ.get("POLY_ENGINE") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "poly-dung-video", "engine")
sys.path.insert(0, E)
import chung  # noqa: E402  (UTF-8, ffmpeg, font)
import ke_hoach as KH  # noqa: E402
import chon_kieu as CK  # noqa: E402
import chuyen_moi as CM  # noqa: E402  (r35: chuyển cảnh mới 'poly-chuyen-1', engine/chuyen-canh + Kho effect)

IS_WIN = os.name == "nt"
KW = {"creationflags": 0x08000000} if IS_WIN else {}
DUOI_VIDEO = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts")
TRUC_SUA = ("chu", "phu_de", "ket", "vi_tri_chu", "mo_dau", "chuyen_dong", "nhip", "chuyen_canh", "diem_nhan", "lop_phu",
            "thanh_tien_trinh", "bo_font", "mau", "hoat_hinh")   # hoat_hinh (4/11 tối): chữ hiện thẳng / chữ nảy


def doc(p, mac_dinh=None, chac=False):
    """Đọc JSON. Windows: file đang bị ghi đè (os.replace) thì thử lại. chac=True: file có mà đọc không được -> dừng (không ghi đè mất dữ liệu)."""
    for lan in range(12):
        try:
            with open(p, encoding="utf-8-sig") as f:
                return json.load(f)
        except FileNotFoundError:
            return mac_dinh
        except (PermissionError, ValueError):
            time.sleep(0.1)
        except OSError:
            break
    if chac and os.path.exists(p):
        raise SystemExit("Không đọc được %s (file đang mở ở chương trình khác?)" % os.path.basename(p))
    return mac_dinh


def ghi(p, o):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tam = p + ".%d.tmp" % os.getpid()
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
    for lan in range(20):
        try:
            os.replace(tam, p)
            return
        except PermissionError:  # Windows: file đích đang được đọc
            time.sleep(0.1)
    os.replace(tam, p)


def xuoi(p):
    return str(p).replace("\\", "/")


def ma():
    return uuid.uuid4().hex[:8]


# ------------------------------------------------------------------ clip
def do_clip(p):
    """ffprobe 1 clip -> {rong, cao (đã xoay), giay, hdr, hdr_trc, co_tieng, fps}."""
    r = subprocess.run([chung.FFPROBE, "-v", "error", "-show_entries",
                        "format=duration:stream=index,codec_type,width,height,r_frame_rate,color_transfer:stream_side_data=rotation",
                        "-of", "json", p], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, **KW)
    if r.returncode:
        raise SystemExit("Không đọc được clip %s: %s" % (os.path.basename(p), (r.stderr or "").strip()[-200:]))
    j = json.loads(r.stdout or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), None)
    if not v:
        raise SystemExit("File %s không có hình" % os.path.basename(p))
    w, h = v.get("width"), v.get("height")
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            try:
                rot = int(float(sd["rotation"]))
            except (TypeError, ValueError):
                pass
    if abs(rot) in (90, 270):
        w, h = h, w
    try:
        n, d = str(v.get("r_frame_rate") or "30/1").split("/")
        fps = round(float(n) / float(d), 3)
    except (ValueError, ZeroDivisionError):
        fps = 30.0
    trc = v.get("color_transfer")
    hdr = trc in ("arib-std-b67", "smpte2084")
    return {"rong": w, "cao": h, "giay": round(float((j.get("format") or {}).get("duration") or 0), 3), "fps": fps,
            "hdr": hdr, "hdr_trc": trc if hdr else None, "co_tieng": a is not None}


_GIAY = {}


def giay_clip(p):
    try:
        st = os.stat(p)
    except OSError:
        return None
    k = (p, st.st_size, int(st.st_mtime))
    if k not in _GIAY:
        try:
            _GIAY[k] = do_clip(p)["giay"]
        except SystemExit:
            _GIAY[k] = None
    return _GIAY[k]


# ------------------------------------------------------------------ dòng thời gian + neo
def danh_dau(plan):
    """Gắn _id cho cảnh, _k cho câu / nhãn / thẻ giá (giữ cái đã có); câu giọng AI giữ _tu_goc (giờ từng từ gốc)."""
    for c in plan.get("canh") or []:
        c.setdefault("_id", "c" + ma())
    for it in plan.get("phu_de") or []:
        it.setdefault("_k", "p" + ma())
        if it.get("tu") and "_tu_goc" not in it and "_neo" not in it:
            it["_tu_goc"] = it["tu"]
    chu = plan.setdefault("chu", {})
    for it in chu.get("nhan_chu") or []:
        it.setdefault("_k", "n" + ma())
    if isinstance(chu.get("the_gia"), dict):
        chu["the_gia"].setdefault("_k", "g" + ma())
    return plan


def _khong_rong(x):
    return isinstance(x, str) and x.strip() != ""


def sach(plan):
    """Bản kế hoạch không có trường đang sửa (_*) và không có chữ trống — để đưa bộ dựng / ghi file."""
    p = copy.deepcopy(plan)
    for c in p.get("canh") or []:
        for k in [k for k in c if k.startswith("_")]:
            c.pop(k)
    p["phu_de"] = [{k: v for k, v in it.items() if not k.startswith("_")} for it in p.get("phu_de") or []
                   if not it.get("_an") and _khong_rong(it.get("chu"))]
    chu = p.get("chu") or {}
    if chu.get("nhan_chu") is not None:
        chu["nhan_chu"] = [{k: v for k, v in it.items() if not k.startswith("_")} for it in chu["nhan_chu"]
                           if not it.get("_an") and _khong_rong(it.get("chu"))]
    tg = chu.get("the_gia")
    if isinstance(tg, dict):
        chu["the_gia"] = None if tg.get("_an") or not _khong_rong(tg.get("gia")) else {k: v for k, v in tg.items() if not k.startswith("_")}
    if isinstance(chu.get("hook"), list):
        chu["hook"] = [x for x in chu["hook"] if _khong_rong(x)]
    if isinstance(chu.get("ket"), list):  # thẻ kết tự viết mà để trống hết: về câu mặc định
        k = [x for x in chu["ket"] if _khong_rong(x)]
        if k:
            chu["ket"] = k
        else:
            chu.pop("ket")
    if "tieu_de" in chu and not _khong_rong(chu.get("tieu_de")):
        chu.pop("tieu_de")
    chep_chuyen_moi(p)
    return p


def chep_chuyen_moi(p):
    """r35: chép nguyên các kiểu chuyển cảnh mới đang dùng (canh[].chuyen, "Trộn chuyển cảnh mới") vào kế hoạch: plan.chuyen_moi
    = {id: kiểu}. Đã có bản chép đúng dạng thì giữ (Kho effect sửa kiểu sau này, video cũ dựng lại vẫn y hệt); kiểu bỏ dùng thì xoá.
    Kế hoạch không dùng kiểu mới: không có khoá này (như cũ)."""
    dung = {c.get("chuyen") for c in p.get("canh") or [] if isinstance(c, dict) and isinstance(c.get("chuyen"), str)}
    if (p.get("kieu") or {}).get("chuyen_canh") == "tron_moi":
        cfg = ((doc(os.path.join(E, "kieu_dung.json"), {}) or {}).get("chuyen_canh_ky_thuat") or {}).get("tron_moi") or {}
        dung |= {i for ds in (cfg.get("nhom") or {}).values() if isinstance(ds, list) for i in ds if isinstance(i, str)}
    cu = p.get("chuyen_moi") if isinstance(p.get("chuyen_moi"), dict) else {}
    moi = {}
    for i in sorted(dung):
        if CM.hop_le(cu.get(i), i):
            moi[i] = cu[i]
        else:
            sp = CM.tim(i)
            if sp:
                moi[i] = CM.ban_chep(sp)
    if moi:
        p["chuyen_moi"] = moi
    else:
        p.pop("chuyen_moi", None)


KHOA_RIENG = ("mau", "loc", "khung", "am_luong", "hieu_ung", "dong", "on_dinh", "easing", "tach_am")   # đặt riêng cảnh: 2 nửa giống nhau mới gộp được
# tach_am (4/11, "Tách âm thanh"): 1 nửa đã tách tiếng, nửa kia chưa -> không gộp (nửa chưa tách còn tiếng của nó)


def khoi_lien(ds):
    """Tiếng tách (4/11, plan.am_tach): các khối anh CHIA ra mà vẫn liền nhau (cùng clip, liền giờ clip, liền giờ video) gộp lại
    -> [(khối, tu, den, t)] để đặt câu phụ đề vắt qua chỗ chia khối không bị cắt."""
    out = []
    for k in sorted([k for k in ds or [] if isinstance(k, dict)], key=lambda k: (str(k.get("nguon")), float(k.get("t") or 0))):
        try:
            a, b, t = float(k["tu"]), float(k["den"]), float(k.get("t") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if b - a < 0.05:
            continue
        tr = out[-1] if out else None
        if tr and tr[0].get("nguon") == k.get("nguon") and abs(tr[2] - a) < 0.005 and abs(tr[3] + tr[2] - tr[1] - t) < 0.005:
            out[-1] = (tr[0], tr[1], b, tr[3])
        else:
            out.append((k, a, b, t))
    return out


def khoi_tai(kt, canh, i, t):
    """Khối tiếng tách đang phát ở giây t trên video (câu anh gõ / thêm ở chỗ đó neo theo khối) -> (khối, tu, den, t) | None.
    Chỉ khi cảnh dưới vạch là cảnh đã tách tiếng (hoặc không có cảnh): cảnh còn tiếng thì câu theo cảnh như cũ."""
    if not kt or (i is not None and 0 <= i < len(canh) and not canh[i].get("tach_am")):
        return None
    for x in kt:
        if x[3] - 0.01 <= t < x[3] + x[2] - x[1]:
            return x
    return None


def chuyen_tay(c, tr):
    """Anh tự đặt chuyển cảnh ở chỗ nối tr | c: c có chuyển cảnh vào, không phải "Cắt thẳng", khác chuyển cảnh vào của cảnh trước
    (giống cảnh trước = chép theo lúc chia / "Áp cho mọi cảnh", không tính)."""
    v = c.get("chuyen")
    return bool(v) and v != "cat_cung" and v != tr.get("chuyen")


def la_cho_chia(tr, c):
    """Chỗ nối tr | c là chỗ anh CHIA cảnh (c._tach hoặc noi_lien đã ghi), cùng clip, liền giờ clip."""
    if not tr or not (c.get("_tach") or c.get("noi_lien")) or c.get("file") != tr.get("file"):
        return False
    try:
        return abs(float(c["tu"]) - float(tr["den"])) < 0.005
    except (KeyError, TypeError, ValueError):
        return False


def gop_lien(p):
    """Cảnh anh vừa CHIA (_tach) mà 2 nửa vẫn nằm sát nhau, nối tiếp giờ clip -> gộp lại 1 cảnh khi dựng / lưu (không thêm
    chuyển cảnh, điểm nhấn giữa câu nói). Cảnh gộp nhớ các phần (_phan) để giao diện vẽ đúng từng khối.
    4/11 (anh duyệt "Chỗ chia luôn nối liền"): 2 nửa đặt riêng KHÁC nhau (màu, bộ lọc, khung, âm lượng, hiệu ứng, chuyển động…) thì không
    gộp (gộp là mất đặt riêng nửa sau) mà ghi noi_lien: bộ dựng (ke_hoach.noi_lien) cắt thẳng ở chỗ chia, không chuyển cảnh kiểu chung,
    không chớp trắng, zoom đi tiếp chiều. Chỉ khi anh tự chọn chuyển cảnh ở ◆ chỗ đó (chuyen_tay) mới là chỗ đổi cảnh thật."""
    out, truoc = [], None
    for c in p.get("canh") or []:
        tr = out[-1] if out else None
        chia = la_cho_chia(truoc, c) and not chuyen_tay(c, truoc)
        if chia and all(c.get(k) == truoc.get(k) for k in KHOA_RIENG):
            tr.setdefault("_phan", [[tr.get("_id"), float(tr["tu"]), float(tr["den"])]])
            tr["_phan"].append([c.get("_id"), float(c["tu"]), float(c["den"])])
            tr["den"] = c["den"]
            if c.get("mo_ta") and c.get("mo_ta") != tr.get("mo_ta"):
                tr["mo_ta"] = " / ".join(x for x in (tr.get("mo_ta"), c["mo_ta"]) if x)
        else:
            if chia:
                c["noi_lien"] = True
            else:
                c.pop("noi_lien", None)
            out.append(c)
        truoc = c
    p["canh"] = out
    return p


def tl_nhanh(plan, duong):
    """Dòng thời gian không đọc tiếng (nhanh; chỗ tách trong cảnh có thể lệch < 0,4s so với bản xuất, mốc cảnh không đổi)."""
    p = sach(plan)
    p["cat_cho_lang"] = False
    with contextlib.redirect_stdout(sys.stderr):
        return KH.build(p, duong)


def moc(tl):
    """{chỉ số cảnh: {dau: lúc cảnh hiện (kể cả chuyển cảnh), bd: lúc giây 'tu' của clip lên hình, kt: lúc hết}}."""
    pa = tl.get("duong") == "premiere"
    t, out = 0.0, {}
    for s in tl["shots"]:
        st = t if pa else t - float(s.get("chuyen") or 0.0)
        if s["canh"] >= 0:
            o = out.setdefault(s["canh"], {"dau": st, "bd": st + float(s.get("dong_bang") or 0.0)})
            o["kt"] = st + s["dur"]
        t = st + s["dur"]
    return out


def _canh_luc(m, t, goi_y=None):
    if isinstance(goi_y, int) and goi_y in m and m[goi_y]["dau"] <= t < m[goi_y]["kt"]:
        return goi_y
    chon = None
    for i in sorted(m, key=lambda i: m[i]["dau"]):
        if m[i]["dau"] - 0.05 <= t < m[i]["kt"]:
            chon = i  # chồng nhau lúc chuyển cảnh: lấy cảnh sau
    if chon is None and m:
        chon = min(m, key=lambda i: min(abs(t - m[i]["bd"]), abs(t - m[i]["kt"])))
    return chon


def _chon_canh(canh, m, neo):
    """Cảnh chứa đoạn neo: cùng clip, giờ clip chồng nhiều nhất (ưu tiên đúng cảnh cũ)."""
    best = None
    for i, c in enumerate(canh):
        if c.get("file") != neo.get("file") or i not in m:
            continue
        s1 = neo["s1"] if neo.get("cau", True) else min(neo["s1"], neo["s0"] + 0.5)
        ov = min(s1, float(c["den"])) - max(neo["s0"], float(c["tu"]))
        if ov <= 0.05:
            continue
        ids = [x[0] for x in c.get("_phan") or []] or [c.get("_id")]
        diem = ov + (100 if neo.get("id") and neo.get("id") in ids else 0)
        if best is None or diem > best[0]:
            best = (diem, i)
    return best[1] if best else None


def _dat_nhan(p, m, gio):
    """Nhãn / thẻ giá: neo chỗ bắt đầu vào cảnh, giữ nguyên độ dài. Trả True nếu giờ có đổi."""
    canh, doi = p.get("canh") or [], False
    chu = p.get("chu") or {}
    ds = list(chu.get("nhan_chu") or []) + ([chu["the_gia"]] if isinstance(chu.get("the_gia"), dict) else [])
    for it in ds:
        neo = it.get("_neo")
        it.pop("_an", None)
        if not neo:
            gio[it.get("_k")] = {"t0": it.get("t0"), "t1": it.get("t1")}
            continue
        i = _chon_canh(canh, m, neo)
        if i is None:
            it["_an"] = True
            gio[it.get("_k")] = {"an": True, "ly_do": "Cảnh chứa đoạn này đã bị cắt hoặc xoá"}
            continue
        c = canh[i]
        s0 = max(neo["s0"], float(c["tu"]))
        t0 = round(s0 + m[i]["bd"] - float(c["tu"]), 3)
        t1 = round(t0 + max(0.3, neo["s1"] - neo["s0"]), 3)
        if (it.get("t0"), it.get("t1")) != (t0, t1):
            doi = True
        it["t0"], it["t1"] = t0, t1
        gio[it.get("_k")] = {"t0": t0, "t1": t1, "cat": bool(s0 > neo["s0"] + 0.02)}
    return doi


def _tu_theo_chu(chu, tu):
    """Giờ từng từ + chữ hiện tại: cùng số từ thì thay chữ (sửa chữ nghe sai), khác số từ thì bỏ (chia đều)."""
    if not tu:
        return None
    ws = [w for w in re.sub(r"\|", " ", str(chu or "")).split() if w]
    if len(ws) != len(tu):
        return None
    return [[w, a, b] for w, (_, a, b) in zip(ws, tu)]


def on_dinh(plan, duong):
    """Bản sao kế hoạch (cảnh chia sát nhau đã gộp) + dòng thời gian + mốc cảnh, nhãn đã đặt theo neo.
    Chuyển cảnh trộn (tron_poly) chọn chỗ theo giờ nhãn, nhãn lại theo cảnh -> lặp tới khi giờ nhãn không đổi."""
    p = gop_lien(copy.deepcopy(plan))
    gio = {}
    for _ in range(5):
        tl = tl_nhanh(p, duong)
        m = moc(tl)
        if not _dat_nhan(p, m, gio):
            break
    return p, tl, m, gio


def gan_neo(plan, duong):
    """Câu / nhãn / thẻ giá chưa có _neo: đọc giờ (trên dòng thời gian của đường `duong`) -> neo vào giờ clip gốc.
    Tiếng tách (4/11): câu đặt ở chỗ đang phát khối tiếng tách (cảnh dưới đã tách tiếng) neo theo khối (_neo.am) -> dời khối, câu dời theo."""
    can = []
    if not plan.get("giong"):
        can += [(it, True) for it in plan.get("phu_de") or [] if "_neo" not in it]
    chu = plan.get("chu") or {}
    can += [(it, False) for it in chu.get("nhan_chu") or [] if "_neo" not in it]
    if isinstance(chu.get("the_gia"), dict) and "_neo" not in chu["the_gia"]:
        can.append((chu["the_gia"], False))
    if not can or not plan.get("canh"):
        return plan
    p, _, m, _ = on_dinh(plan, duong)
    canh = p["canh"]
    kt = khoi_lien(plan.get("am_tach")) if duong == "may_chu" and plan.get("am_tach") else []
    for it, la_cau in can:
        try:
            t0, t1 = float(it.get("t0", 0)), float(it.get("t1", 0))
        except (TypeError, ValueError):
            continue
        i = _canh_luc(m, t0, it.get("canh") if la_cau else None)
        x = khoi_tai(kt, canh, i, t0) if la_cau and kt else None
        if x:
            off = x[1] - x[3]
            neo = {"id": canh[i].get("_id") if i is not None and i < len(canh) else None, "file": x[0].get("nguon"),
                   "s0": round(t0 + off, 3), "s1": round(t1 + off, 3), "cau": True, "am": True}
            if it.get("tu"):
                try:
                    neo["tu"] = [[str(w), round(float(a) + off, 3), round(float(b) + off, 3)] for w, a, b in it["tu"]]
                except (TypeError, ValueError):
                    pass
            it["_neo"] = neo
            it.pop("canh", None)
            continue
        if i is None or i >= len(canh):
            continue
        off = float(canh[i]["tu"]) - m[i]["bd"]
        neo = {"id": canh[i].get("_id"), "file": canh[i]["file"], "s0": round(t0 + off, 3), "s1": round(t1 + off, 3), "cau": la_cau}
        if la_cau and it.get("tu"):
            try:
                neo["tu"] = [[str(w), round(float(a) + off, 3), round(float(b) + off, 3)] for w, a, b in it["tu"]]
            except (TypeError, ValueError):
                pass
        it["_neo"] = neo
        it.pop("canh", None)
    return plan


def _canh_sau(canh, i):
    """Cảnh ngay sau i nếu nối tiếp giờ clip (cùng clip, den = tu)."""
    if i + 1 < len(canh) and canh[i + 1].get("file") == canh[i].get("file") and abs(float(canh[i + 1]["tu"]) - float(canh[i]["den"])) < 0.005:
        return i + 1
    return None


def ap_neo(plan, duong):
    """Kế hoạch (cảnh chia sát nhau đã gộp) có giờ tính lại theo cảnh hiện tại trên đường `duong`
    + {_k: {t0, t1, an, ly_do, cat}} cho giao diện + mốc cảnh."""
    p, tl, m, gio = on_dinh(plan, duong)
    canh = p.get("canh") or []
    # tiếng tách (4/11): câu nghe từ lời (có giờ từng chữ) của cảnh đã tách tiếng, hoặc câu neo theo khối (_neo.am), đặt theo KHỐI
    # tiếng đang chứa đúng đoạn lời đó (anh dời khối = lời nghe ở chỗ khác -> phụ đề đi theo tiếng). Chỉ đường máy chủ (bản xuất
    # trong app có tiếng tách; ke-hoach.json đường Premiere giữ câu theo cảnh). Không có khối hợp: theo cảnh như cũ.
    kt = khoi_lien(p.get("am_tach")) if duong == "may_chu" and p.get("am_tach") else []

    def theo_khoi(it, neo):
        if not kt or not neo.get("cau", True):
            return False
        i = _chon_canh(canh, m, neo)
        if not neo.get("am") and not (neo.get("tu") and (i is None or canh[i].get("tach_am"))):
            return False
        best = None
        for x in kt:
            if x[0].get("nguon") != neo.get("file"):
                continue
            ov = min(neo["s1"], x[2]) - max(neo["s0"], x[1])
            if ov <= 0.05:
                continue
            diem = ov + (100 if i is not None and x[0].get("goc") and x[0].get("goc") == canh[i].get("tach_am") else 0)
            if best is None or diem > best[0]:
                best = (diem, x)
        if not best:
            return False
        k, a, b, t = best[1]
        s0, s1 = max(neo["s0"], a), min(neo["s1"], b)
        t0, t1 = round(t + s0 - a, 3), round(t + s1 - a, 3)
        if t1 - t0 < 0.2:
            return False
        it["t0"], it["t1"] = t0, t1
        it.pop("canh", None)
        tu = _tu_theo_chu(it.get("chu"), neo.get("tu"))
        if tu:
            tu = [[w, round(t + x_ - a, 3), round(t + y_ - a, 3)] for w, x_, y_ in tu if x_ >= s0 - 0.03 and y_ <= s1 + 0.03]
        if tu:
            it["tu"] = tu
        else:
            it.pop("tu", None)
        gio[it.get("_k")] = {"t0": t0, "t1": t1, "cat": bool(s0 > neo["s0"] + 0.02 or s1 < neo["s1"] - 0.02)}
        return True

    def ra_video(i, s):
        """Giờ clip s (thuộc cảnh i hoặc các cảnh nối tiếp sau i) -> giờ trên video."""
        while s > float(canh[i]["den"]) + 1e-6:
            j = _canh_sau(canh, i)
            if j is None or j not in m:
                break
            i = j
        s = min(max(s, float(canh[i]["tu"])), float(canh[i]["den"]))
        return round(m[i]["bd"] + s - float(canh[i]["tu"]), 3), i

    def dat_cau(it):
        neo = it.get("_neo")
        it.pop("_an", None)
        if not neo:  # giọng AI / chưa neo: giữ giờ trên video
            tu = _tu_theo_chu(it.get("chu"), it.get("_tu_goc"))
            if tu:
                it["tu"] = tu
            else:
                it.pop("tu", None)
            gio[it.get("_k")] = {"t0": it.get("t0"), "t1": it.get("t1")}
            return
        if kt and theo_khoi(it, neo):
            return
        i = _chon_canh(canh, m, neo)
        if i is None:
            it["_an"] = True
            gio[it.get("_k")] = {"an": True, "ly_do": "Cảnh chứa đoạn này đã bị cắt hoặc xoá"}
            return
        # dải cảnh nối tiếp chứa câu (anh chia cảnh mà không đổi chỗ: câu vắt qua chỗ chia không bị cắt)
        a = i
        while a - 1 >= 0 and _canh_sau(canh, a - 1) == a and a - 1 in m and neo["s0"] < float(canh[a]["tu"]):
            a -= 1
        z = a
        while _canh_sau(canh, z) is not None and _canh_sau(canh, z) in m and neo["s1"] > float(canh[z]["den"]):
            z = _canh_sau(canh, z)
        s0, s1 = max(neo["s0"], float(canh[a]["tu"])), min(neo["s1"], float(canh[z]["den"]))
        t0, ia = ra_video(a, s0)
        t1, _ = ra_video(a, s1)
        if t1 - t0 < 0.2:
            it["_an"] = True
            gio[it.get("_k")] = {"an": True, "ly_do": "Còn quá ngắn sau khi cắt cảnh"}
            return
        it["t0"], it["t1"], it["canh"] = t0, t1, ia
        tu = _tu_theo_chu(it.get("chu"), neo.get("tu"))
        if tu:
            tu = [[w, ra_video(a, x)[0], ra_video(a, y)[0]] for w, x, y in tu if x >= s0 - 0.03 and y <= s1 + 0.03]
        if tu:
            it["tu"] = tu
        else:
            it.pop("tu", None)
        gio[it.get("_k")] = {"t0": t0, "t1": t1, "cat": bool(s0 > neo["s0"] + 0.02 or s1 < neo["s1"] - 0.02)}

    pd = p.get("phu_de") or []
    for it in pd:
        dat_cau(it)
    hien = sorted([it for it in pd if not it.get("_an")], key=lambda x: float(x.get("t0") or 0))
    for a, b in zip(hien, hien[1:]):  # không chồng câu sau
        if float(a["t1"]) > float(b["t0"]):
            a["t1"] = b["t0"]
            if a.get("_k") in gio:
                gio[a["_k"]]["t1"] = b["t0"]
    p["phu_de"] = hien + [it for it in pd if it.get("_an")]
    return p, gio, tl, m


# ------------------------------------------------------------------ lệnh
def W_cua(v):
    return os.path.join(v, "lam")


def lenh_mo(d):
    """Mở 1 thư mục video: kế hoạch (bản đang sửa dở nếu mới hơn) đã gắn _id/_k/_neo + độ dài clip + danh sách kiểu."""
    v = d["v"]
    W = W_cua(v)
    kp = os.path.join(W, "ke-hoach.json")
    plan = doc(kp)
    if not isinstance(plan, dict) or not plan.get("canh"):
        raise SystemExit("Video này chưa có kế hoạch dựng (lam/ke-hoach.json) — chỉ sửa tay được video đã dựng xong hoặc tạo mới từ clip.")
    nhap = doc(os.path.join(W, "sua-tay", "dang-sua.json"))
    dung_nhap = False
    if isinstance(nhap, dict) and isinstance(nhap.get("plan"), dict) and not d.get("bo_nhap"):
        # bản sửa (nháp) dựa trên đúng ke-hoach.json đang có (chưa ai — vd Claude — ghi đè kế hoạch sau đó)
        dung_nhap = nhap.get("kp_mtime") is not None and abs(float(nhap["kp_mtime"]) - os.path.getmtime(kp)) < 0.001
    if dung_nhap:
        plan = nhap["plan"]
    else:
        danh_dau(plan)
        gan_neo(plan, (plan.get("kieu") or {}).get("duong") or "may_chu")
    danh_dau(plan)
    giay = {}
    for f, src in (plan.get("nguon") or {}).items():
        giay[f] = giay_clip(src.get("local") or f)
    sua_do = dung_nhap and not nhap.get("da_luu")
    return {"plan": plan, "giay": giay, "dang_sua": sua_do, "nhap_luc": nhap.get("luc") if sua_do else None,
            "nhap_moc": float(nhap.get("luc") or 0) if isinstance(nhap, dict) else 0,
            "kp_mtime": os.path.getmtime(kp),
            "kieu_ds": kieu_ds((plan.get("kieu") or {}).get("duong") or "may_chu"), "ket_mac_dinh": ket_mac_dinh(),
            **hieu_ung_rieng(), **bo_mau_app(),
            "nhap_mp4": xuoi(os.path.join(W, "sua-tay", "nhap", "ban-nhap.mp4")) if os.path.isfile(os.path.join(W, "sua-tay", "nhap", "ban-nhap.mp4")) else ""}


def kieu_ds(duong="may_chu"):
    """Giá trị kiểu cho chọn. Video đường Premiere (Claude dựng bằng Premiere): chỉ giá trị Premiere cũng làm được, để lần sau
    Claude "Sửa video" bằng Premiere không bị dừng (vd mở đầu đóng băng / câu hỏi chỉ ffmpeg làm)."""
    import don as DON
    deck = doc(os.path.join(E, "kieu_dung.json"), {})
    chi_pr = deck.get("chi_premiere") or {}
    pr = deck.get("premiere") or {}
    out = []
    for m in TRUC_SUA:
        vs = [x for x in (deck.get("muc") or {}).get(m, {}) if x not in (chi_pr.get(m) or [])]
        if duong == "premiere" and m in pr:
            vs = [x for x in vs if x in pr[m]]
        if m == "ket":
            vs = vs + ["khong"]
        them = {x: t for x, t in KIEU_THEM.get(m, {}).items() if duong == "may_chu" or m != "hoat_hinh"}
        if them:   # 4/11 tối: Đứng yên / mở đầu thường / chữ hiện thẳng (chỉ POLY Cut thêm, chon_kieu không bốc)
            vs = list(them) + [x for x in vs if x not in them]
        if vs:
            ten_may = TEN_MAY_CHU.get(m, {}) if duong == "may_chu" else {}
            out.append({"muc": m, "ten": DON.TEN_MUC.get(m, m),
                        "ds": [{"v": x, "ten": them.get(x) or ten_may.get(x) or DON.TEN_GIA_TRI.get(m, {}).get(x, x)} for x in vs]})
    return out


# 4/11 tối (anh: "khung hình vẫn rung"; 18:10 chốt "video cho mặc định từ đầu, hiệu ứng thêm sau"): giá trị kiểu thêm, KHÔNG có trong
# kieu_dung.json (chon_kieu không bốc cho video Claude dựng; kieu_dung.json + đường Claude giữ nguyên). ke_hoach.build: chuyen_dong lạ =
# không zoom / lia; mo_dau lạ = không hiệu ứng mở đầu (hook hiện ngay từ khung đầu, như mặc định 3,2s). hoat_hinh "khong" = chữ hiện thẳng,
# không nảy / mờ dần (dung_may_chu: chỉ đường máy chủ).
KIEU_THEM = {"chuyen_dong": {"dung_yen": "Đứng yên (không tự zoom / lia)"}, "mo_dau": {"thuong": "Thường (hình đứng yên, chữ hiện ngay)"},
             "chuyen_canh": {"tron_moi": "Trộn chuyển cảnh mới (nhiều kiểu xen kẽ)"},   # r35: trộn 15 kiểu mới (kieu_dung › tron_moi)
             "hoat_hinh": {"khong": "Chữ hiện thẳng (không nảy)"}}
TEN_MAY_CHU = {"hoat_hinh": {"keyframe": "Chữ nảy nhẹ khi hiện"}}   # tên dễ hiểu ở đường ffmpeg ("Keyframe Premiere" là tên đường Premiere)
DIEM_NHAN_DONG = ("rung_nhip", "zoom_dap")   # điểm nhấn làm hình tự rung / đập zoom ở chỗ đổi cảnh
# MẶC ĐỊNH TRƠN (anh chốt 4/11 18:10) cho video TẠO TAY: hiệu ứng nào anh chưa tự chọn (không có trong kieu._ghim) thì TẮT. Kiểu chữ /
# phụ đề / vị trí chữ / màu / thẻ kết / font / nhịp không phải hiệu ứng: giữ như cũ.
TRON = {"chuyen_dong": "dung_yen", "mo_dau": "thuong", "chuyen_canh": "cat_cung", "diem_nhan": "khong", "lop_phu": "khong",
        "am_nhan": "khong", "thanh_tien_trinh": "khong", "hoat_hinh": "khong"}


def hieu_ung_rieng():
    """Chuyển cảnh + hiệu ứng hình CHỈ gắn riêng từng cảnh (3/11, chủ tiệm chọn từ bộ sưu tầm): menu Hiệu ứng / Thư viện của trang."""
    deck = doc(os.path.join(E, "kieu_dung.json"), {}) or {}
    kt = deck.get("chuyen_canh_ky_thuat") or {}
    cr = [{"v": k, "ten": (kt.get(k) or {}).get("ten") or k, "cham": (kt.get(k) or {}).get("xfade") == "custom",
           "giay": (kt.get(k) or {}).get("giay")} for k in ((deck.get("chuyen_canh_rieng") or {}).get("ds") or []) if k in kt]
    hu = [{"v": k, "ten": x.get("ten") or k, "dau_canh": bool(x.get("dau_canh")), "nhom": x.get("nhom")}
          for k, x in (deck.get("hieu_ung_canh") or {}).items() if isinstance(x, dict)]
    # r20 (Thư viện thêm): mô tả + giây dựng thêm (tooltip) + nhóm chuyển cảnh (Cơ bản / Trượt / Lau / Zoom / Đặc biệt)
    for y in cr:
        y.update({"mo_ta": (kt.get(y["v"]) or {}).get("mo_ta") or "", "them_giay": (kt.get(y["v"]) or {}).get("them_giay_1080")})
    for y in hu:
        y["mo_ta"] = ((deck.get("hieu_ung_canh") or {}).get(y["v"]) or {}).get("mo_ta") or ""
        # 4/11 tối: chip / ô / menu đã gắn nhãn "đầu cảnh" theo dau_canh -> tên bỏ đuôi "đầu cảnh" (hết lặp "Zoom nảy đầu cảnh đầu cảnh")
        if y["dau_canh"]:
            y["ten"] = re.sub(r"\s+(ở\s+)?đầu cảnh$", "", y["ten"], flags=re.I) or y["ten"]
    nh = (deck.get("chuyen_canh_rieng") or {}).get("nhom") or {}
    cn = {v: g for g, ds in nh.items() if isinstance(ds, list) for v in ds}
    mt = {k: x.get("mo_ta") for k, x in kt.items() if isinstance(x, dict) and x.get("mo_ta")}
    # r35 (anh duyệt 11/11): 15 kiểu mới (engine/chuyen-canh + Kho effect) lên đầu, nhóm "Mới"; kiểu cũ trong chuyen_canh_rieng.an
    # ẩn khỏi Thư viện / danh sách chọn (vẫn có tên, video đang dùng vẫn thấy + đổi được: trang lọc theo "an")
    an = [x for x in ((deck.get("chuyen_canh_rieng") or {}).get("an") or []) if isinstance(x, str)]
    moi = {k: CM.ban_chep(v) for k, v in CM.tat_ca().items() if k not in kt}
    for y in cr:
        if y["v"] in an:
            y["an"] = True
    cr = [{"v": k, "ten": v.get("ten") or k, "cham": False, "giay": v.get("giay"), "moi": True, "mo_ta": v.get("mo_ta") or "",
           "them_giay": None} for k, v in moi.items()] + cr
    for k, v in moi.items():
        cn[k] = "moi"
        if v.get("mo_ta"):
            mt[k] = v["mo_ta"]
    tn = dict(nh.get("ten") or {}, moi="Mới · trend")
    return {"chuyen_rieng": cr, "hieu_ung_ds": hu, "chuyen_nhom": cn, "chuyen_ten_nhom": tn, "chuyen_mo_ta": mt,
            "chuyen_an": an, "chuyen_moi": moi}


def bo_mau_app():
    """r36 (11/11, anh duyệt "làm cả 3 bộ, cho anh chọn trong app"): bộ mẫu chữ + kiểu dựng cả video cho tab Kiểu (ảnh nhỏ nhúng sẵn).
    Bộ dựng cũ chưa có mau_chu_moi.py -> {} (trang ẩn 2 hàng này)."""
    try:
        import mau_chu_moi
        return mau_chu_moi.ds_app()
    except Exception:  # noqa  bộ dựng cũ / file bộ hỏng: app vẫn chạy như trước
        return {}


def ket_mac_dinh():
    gu = (doc(os.path.join(E, "kieu_dung.json"), {}) or {}).get("gu_kenh") or {}
    return {"the_comment": gu.get("ket_mac_dinh") or [], "dia_chi": gu.get("ket_dia_chi") or []}


MO_DAU_CAN_HOOK = ("hoi_truoc", "dong_bang")   # mở đầu sống nhờ chữ hook: không có hook thì giây đầu là hình mờ / đứng, không chữ


def _giong_thay_tieng(ps):
    """Giọng AI thay hẳn tiếng trong clip (4/11 anh: "giọng đọc ai tự thay thế tiếng trong clip được không"): plan.giong.thay_tieng
    -> lúc xem / dựng tắt tiếng mọi cảnh (canh.am_luong = 0, bản sao ps; kế hoạch anh sửa giữ nguyên). Không cờ = như cũ (hạ nhỏ làm nền).
    Khối tiếng tách (am_tach, 4/11) cũng là tiếng clip: im theo."""
    g = ps.get("giong")
    if isinstance(g, dict) and g.get("thay_tieng"):
        for c in ps.get("canh") or []:
            c["am_luong"] = 0
        if not ps.get("giong_de"):   # r32: giọng AI đọc lại đi theo khối tách -> giữ khối để đặt giờ (bộ dựng vẫn cho khối im)
            ps.pop("am_tach", None)


def kieu_tron(plan):
    """MẶC ĐỊNH TRƠN (4/11 18:xx, anh: "đoạn đầu bấm video chạy rất rung"; 18:10 chốt "video cho mặc định từ đầu, hiệu ứng thêm sau"):
    video TẠO TAY (_tao_boi "sua_tay"): mục hiệu ứng anh CHƯA tự chọn (không có trong kieu._ghim — máy bốc ngẫu nhiên lúc tạo) thì TẮT
    (TRON: Đứng yên, mở đầu thường, cắt thẳng, không điểm nhấn / lớp phủ / âm nhấn / thanh tiến trình, chữ hiện thẳng).
    Anh tự chọn (tab Kiểu, Thư viện, menu, script, Nhờ Claude) -> trang ghi vào _ghim -> dùng đúng giá trị đó như cũ. Video Claude dựng:
    không đổi. -> {mục: giá trị dùng} các mục bị thay (rỗng = không đổi). Không đổi kế hoạch anh lưu: chỉ bản đem xem trước / dựng."""
    k = plan.get("kieu") or {}
    if plan.get("_tao_boi") != "sua_tay":
        return {}
    g = set(k.get("_ghim") or [])
    return {m: v for m, v in TRON.items() if m not in g and k.get(m) != v}


kieu_dung_yen = kieu_tron   # tên cũ (bài thử)


def _mo_dau_an_toan(ps):
    """Video không có hook mà kiểu mở đầu cần hook (câu hỏi mở đầu / đóng băng) -> dựng như "punch_mo" (khung đầu đã chuyển động).
    Chỉ đổi bản đem dựng / xem trước, không đổi kế hoạch: anh gõ hook vào là mở đầu cũ quay lại.
    4/11 18:xx: video tạo tay -> hiệu ứng anh chưa tự chọn thì tắt (kieu_tron), trước _kieu_xem đã chạy nên giữ được "chữ hiện thẳng"."""
    dy = kieu_tron(ps)
    if dy:
        ps["kieu"] = dict(ps.get("kieu") or {}, **dy)
    k = ps.get("kieu") or {}
    if k.get("mo_dau") in MO_DAU_CAN_HOOK and not any(str(x or "").strip() for x in ((ps.get("chu") or {}).get("hook") or [])):
        ps["kieu"] = dict(k, mo_dau="punch_mo")
    # 3/11 (chủ tiệm: "chạy thử video thấy bị rung"): chuyển động liền mạch cả cảnh, không lia / zoom lại từ đầu mỗi phần ≤ 2,5s.
    # Gọi ở cả xem trước lẫn xuất (và mẫu kiểu) -> khung xem nhanh, bản nháp, bản xuất cùng 1 chuyển động. ke_hoach.lien_mach
    ps["dong_lien_canh"] = True
    return ps


def _kieu_xem(k):
    k = dict(k or {})
    # chữ động MOV / âm nhấn: chỉ đường Premiere — ffmpeg không dùng, khỏi vẽ cho nhanh. "khong" (4/11 tối) = chữ hiện thẳng: giữ
    k["hoat_hinh"] = "khong" if k.get("hoat_hinh") == "khong" else "keyframe"
    k["am_nhan"] = "khong"
    return k


# ------------------------------------------------------------------ xem trước: nhớ từng lớp chữ (3/11)
# Worker "phuc-vu" sống suốt lúc app mở -> nhớ từng lớp chữ đã vẽ: khoá = tên hàm vẽ + tham số + bộ font (+ thẻ bìa, màu,
# thư mục font). Cắt / xoá / đổi chỗ cảnh, Ctrl+Z chỉ tính lại giờ; sửa 1 câu chỉ vẽ 1–2 lớp. Ảnh ghi theo mã băm NỘI DUNG vào
# <video>/lam/sua-tay/xem/lop/<băm>.png (đã có thì không ghi lại) -> URL không đổi, trình duyệt dùng lại ảnh đã tải.
# Chỉ thay tạm hàm của ve_chu TRONG lúc lenh_xem gọi render (xong trả lại như cũ): xuat() / bộ dựng không bị ảnh hưởng.
_VE_TEN = ("block", "end_card", "brand", "price_card", "tieu_de_ghim", "nhan_gon", "the_ten_may", "nhan_to", "sticker", "sub_cum",
           "subtitle")
_NHO_LOP = collections.OrderedDict()  # mã khoá -> {"bam", "hop", "chu_nho", "p": file đã có gần nhất}
_NHO_LOP_TOI_DA = 6000
_NHO_BAN = collections.OrderedDict()  # (thư mục lop, mã cả bản chữ) -> kết quả vẽ cả bản
_CHI_MUC = {}  # thư mục lop -> {"d": {mã khoá: {bam, hop, chu_nho}}, "doi": bool} (lop/chi-muc.json: mở lại app vẫn nhớ)
_DON_LUC = {}  # thư mục xem -> lúc dọn gần nhất
LOP_GIU_TOI_DA = 400  # file lớp tối đa mỗi video (dọn file cũ nhất)
LOP_GIU_GIAY = 86400  # file không dùng quá 1 ngày thì dọn


class _AnhDaLuu:
    """Thay ảnh PIL mà hàm vẽ trả cho render() lúc xem trước: lớp đã nằm sẵn trong lop/<băm>.png. render() chỉ gọi .save(p)
    (kiểm màu đã tắt) -> ghi nhận p (đường render định ghi) -> file thật."""

    def __init__(self, p, ghi, chu_nho, ten_chu):
        self.p, self._ghi, self._chu_nho, self._ten_chu = p, ghi, chu_nho, ten_chu

    def save(self, p, *a, **k):
        self._ghi[p] = self.p
        for txt, _co in self._chu_nho:  # chữ bị thu nhỏ thuộc lớp nào (để cảnh báo ghi đúng tên)
            self._ten_chu.setdefault(txt, os.path.basename(p))


class _PhanDaLuu:
    """the_ten_may trả các phần; render ghép bằng ghep_phan -> trả thẳng ảnh đã ghép sẵn."""

    def __init__(self, anh):
        self.anh = anh


def _mac_dinh_json(o):
    if isinstance(o, (set, frozenset)):
        return sorted(str(x) for x in o)
    return str(o)


def _bam_anh(im):
    """Mã băm nội dung 1 lớp RGBA: hộp có nét + điểm ảnh trong hộp (ngoài hộp trong suốt hết)."""
    bb = im.getbbox()
    h = hashlib.md5(("%s|%s|%s" % (im.mode, im.size, bb)).encode("utf-8"))
    if bb:
        h.update(im.crop(bb).tobytes())
    return h.hexdigest()[:20]


_PHIEN = {}


def _phien_ve(VC):
    """Phiên bản ve_chu.py (cỡ + giờ sửa file): bộ dựng được cập nhật thì khoá đổi, không dùng lớp nhớ trên đĩa của bản cũ."""
    if "v" not in _PHIEN:
        try:
            st = os.stat(VC.__file__)
            _PHIEN["v"] = "%d-%d" % (st.st_size, int(st.st_mtime))
        except (OSError, TypeError):
            _PHIEN["v"] = "?"
    return _PHIEN["v"]


def _chi_muc(lop_dir):
    x = _CHI_MUC.get(lop_dir)
    if x is None:
        d = doc(os.path.join(lop_dir, "chi-muc.json"), {}) or {}
        x = _CHI_MUC[lop_dir] = {"d": d if isinstance(d, dict) else {}, "doi": False}
    return x


class _VeNho:
    """Thay tạm các hàm vẽ của ve_chu (chỉ lớp gọi thẳng từ render; hàm vẽ gọi lồng nhau chạy như cũ) + tắt phần chỉ
    Premiere cần (lop_rieng / *-giua.png, write_ass) + kiểm màu. Dùng: with _VeNho(VC, lop_dir) as v: VC.render(...)."""

    def __init__(self, VC, lop_dir):
        self.VC, self.lop_dir = VC, lop_dir
        self.ghi = {}  # đường PNG render định ghi -> file lớp thật
        self.ten_chu = {}  # chữ bị thu nhỏ -> tên lớp
        self.ve_moi = 0  # số lớp phải vẽ lại lần này
        self.sau = 0  # đang ở trong 1 hàm vẽ (gọi lồng: chạy hàm gốc)
        self.cu = {}
        self.cm = _chi_muc(lop_dir)

    def __enter__(self):
        VC = self.VC
        ten = list(_VE_TEN) + ["ghep_phan", "kiem_mau", "lop_rieng", "write_ass", "write_ass_cum"]
        self.cu = {t: getattr(VC, t) for t in ten}
        for t in _VE_TEN:
            setattr(VC, t, self._boc(t, self.cu[t]))
        gp = self.cu["ghep_phan"]
        VC.ghep_phan = lambda phan, *a, **k: phan.anh if isinstance(phan, _PhanDaLuu) else gp(phan, *a, **k)
        VC.kiem_mau = lambda *a, **k: []  # kiểm màu chậm (≈0,4s / lớp): để lúc xuất
        VC.lop_rieng = lambda *a, **k: ([], 1)  # lớp riêng track + *-giua.png: chỉ Premiere cần
        VC.write_ass = lambda *a, **k: None  # phụ đề ASS: chỉ lúc dựng ffmpeg (xem trước hiện bằng PNG)

        def ass_cum(tl, outdir, style, warn):  # không ghi phu-de.ass, chỉ giữ cảnh báo "bị thẻ kết cắt" của cac_cum
            VC.cac_cum(tl, warn)
            return None
        VC.write_ass_cum = ass_cum
        return self

    def __exit__(self, *exc):
        for t, f in self.cu.items():
            setattr(self.VC, t, f)
        return False

    def _khoa(self, ten, a, k):
        VC = self.VC
        them = [VC.BO.get("ten"), VC.FONT_DIR, VC.XANH, _phien_ve(VC)]
        if ten == "block":
            them.append(VC.THE_BIA.get("v"))
        if ten == "sticker":
            sp = os.path.join(VC.STICKER_DIR, "%s.png" % (a[0] if a else k.get("ten")))
            try:
                st = os.stat(sp)
                them += [sp, st.st_size, st.st_mtime]
            except OSError:
                them.append(sp)
        s = json.dumps([ten, a, k, them], ensure_ascii=False, sort_keys=True, default=_mac_dinh_json)
        return hashlib.md5(s.encode("utf-8")).hexdigest()[:24]

    def _co_san(self, kh):
        """Lớp đã nhớ và có file trong thư mục lop của video này (hoặc chép từ video khác) -> (file, mục nhớ) / None."""
        x = _NHO_LOP.get(kh) or self.cm["d"].get(kh)
        if not x:
            return None
        f = os.path.join(self.lop_dir, x["bam"] + ".png")
        try:
            st = os.stat(f)
            if time.time() - st.st_mtime > 3600:  # đánh dấu "còn dùng" (dọn theo giờ sửa file)
                os.utime(f)
        except OSError:
            nguon = x.get("p")
            if not nguon or not os.path.isfile(nguon):
                return None
            try:
                tam = f + ".%d.tmp" % os.getpid()
                shutil.copyfile(nguon, tam)
                os.replace(tam, f)
            except OSError:
                return None
        return f, x

    def _nho(self, kh, bam, hop, chu_nho, f):
        _NHO_LOP[kh] = {"bam": bam, "hop": hop, "chu_nho": chu_nho, "p": f}
        _NHO_LOP.move_to_end(kh)
        while len(_NHO_LOP) > _NHO_LOP_TOI_DA:
            _NHO_LOP.popitem(last=False)
        if (self.cm["d"].get(kh) or {}).get("bam") != bam:
            self.cm["d"][kh] = {"bam": bam, "hop": hop, "chu_nho": chu_nho}
            self.cm["doi"] = True

    def _boc(self, ten, goc):
        VC = self.VC

        def ve(*a, **k):
            if self.sau:
                return goc(*a, **k)
            kh = self._khoa(ten, a, k)
            co = self._co_san(kh)
            if co:
                f, x = co
                chu_nho = [tuple(c) for c in x.get("chu_nho") or []]
                hop = tuple(x["hop"]) if x.get("hop") is not None else None
                VC.CHU_NHO.extend(chu_nho)
                self._nho(kh, x["bam"], list(hop) if hop is not None else None, [list(c) for c in chu_nho], f)
            else:
                n0 = len(VC.CHU_NHO)
                self.sau += 1
                try:
                    im, hop = goc(*a, **k)
                    if ten == "the_ten_may":  # render: phan, hop = the_ten_may(...); im = ghep_phan(phan)
                        im = self.cu["ghep_phan"](im)
                finally:
                    self.sau -= 1
                chu_nho = [tuple(c) for c in VC.CHU_NHO[n0:]]
                bam = _bam_anh(im)
                f = os.path.join(self.lop_dir, bam + ".png")
                if not os.path.isfile(f):
                    tam = f + ".%d.tmp" % os.getpid()
                    im.save(tam, format="PNG", compress_level=1)  # nén nhẹ: ghi nhanh gấp ~4 lần, file lớn hơn ~15%
                    os.replace(tam, f)
                self.ve_moi += 1
                hop = tuple(hop) if hop is not None else None
                self._nho(kh, bam, list(hop) if hop is not None else None, [list(c) for c in chu_nho], f)
            anh = _AnhDaLuu(f, self.ghi, chu_nho, self.ten_chu)
            return (_PhanDaLuu(anh) if ten == "the_ten_may" else anh), hop
        ve.__name__ = ten
        return ve


def _ve_xem(VC, tl, goc, h):
    """Vẽ lớp chữ của dòng thời gian tl (nhớ từng lớp) -> {lop: [{png, t0, t1, ten, loai, hop}], warn, ten_chu, ve_moi}."""
    lop_dir = os.path.join(goc, "lop")
    kb = (os.path.normcase(os.path.abspath(lop_dir)), h)
    x = _NHO_BAN.get(kb)
    if x and all(os.path.isfile(l["png"]) for l in x["lop"]):
        _NHO_BAN.move_to_end(kb)
        return dict(x, ve_moi=0)
    os.makedirs(lop_dir, exist_ok=True)
    tam = os.path.join(goc, "_ve")  # render ghi lop-chu.json vào đây (không dùng tới)
    with _VeNho(VC, lop_dir) as v:
        with contextlib.redirect_stdout(sys.stderr):
            layers, warn = VC.render(json.loads(json.dumps(tl)), tam)
    lop = []
    for l in layers:
        f = v.ghi.get(l["png"])
        if not f:  # lớp không qua hàm vẽ đã bọc (không nên có): lấy file render ghi, chép vào lop/
            if not os.path.isfile(l["png"]):
                continue
            with open(l["png"], "rb") as fo:
                f = os.path.join(lop_dir, hashlib.md5(fo.read()).hexdigest()[:20] + ".png")
            if not os.path.isfile(f):
                shutil.copyfile(l["png"], f)
        lop.append({"png": f, "t0": l["t0"], "t1": l["t1"], "ten": l.get("ten"), "loai": l.get("loai"), "hop": l.get("hop"),
                    **({"mo_nen": l["mo_nen"]} if l.get("mo_nen") else {})})   # r36: lớp có kính (khung xem làm mờ bằng CSS)
    if v.cm["doi"]:
        try:
            ghi(os.path.join(lop_dir, "chi-muc.json"), v.cm["d"])
            v.cm["doi"] = False
        except OSError:
            pass
    kq = {"lop": lop, "warn": list(warn), "ten_chu": dict(v.ten_chu), "ve_moi": v.ve_moi}
    _NHO_BAN[kb] = kq
    while len(_NHO_BAN) > 24:
        _NHO_BAN.popitem(last=False)
    _don_lop(goc, lop_dir, {l["png"] for l in lop}, v.ve_moi)
    return kq


def _don_lop(goc, lop_dir, dang_dung, moi=0):
    """Dọn thư mục xem/: thư mục kiểu cũ (xem/<mã>/), file lớp không dùng quá 1 ngày, giữ tối đa LOP_GIU_TOI_DA file.
    Chạy tối đa 10 phút / lần mỗi video (hoặc khi vừa ghi nhiều lớp mới)."""
    now = time.time()
    x = _DON_LUC.get(goc) or {"luc": 0.0, "moi": 0}
    x["moi"] += moi
    _DON_LUC[goc] = x
    if now - x["luc"] < 600 and x["moi"] < 120:
        return
    x["luc"], x["moi"] = now, 0
    try:
        for n in os.listdir(goc):
            pn = os.path.join(goc, n)
            if n in ("lop", "_ve") or not os.path.isdir(pn):
                continue
            shutil.rmtree(pn, ignore_errors=True)  # xem/<mã>/ của bản trước 3/11, thư mục .tmp- dở
        ds = []
        for n in os.listdir(lop_dir):
            pn = os.path.join(lop_dir, n)
            try:
                mt = os.path.getmtime(pn)
            except OSError:
                continue
            if n.endswith(".tmp"):
                if now - mt > 3600:
                    os.remove(pn)
            elif n.endswith(".png"):
                ds.append((mt, pn))
    except OSError:
        return
    ds.sort()
    bo = [pn for mt, pn in ds if now - mt > LOP_GIU_GIAY and pn not in dang_dung]
    con = [pn for mt, pn in ds if pn not in bo]
    du = len(con) - LOP_GIU_TOI_DA
    if du > 0:
        bo += [pn for pn in con if pn not in dang_dung][:du]
    for pn in bo:
        try:
            os.remove(pn)
        except OSError:
            pass
    if bo:  # bỏ mục chỉ mục trỏ tới file đã xoá
        cm = _chi_muc(lop_dir)
        mat = {os.path.basename(pn)[:-4] for pn in bo}
        for kh in [kh for kh, e in cm["d"].items() if e.get("bam") in mat]:
            cm["d"].pop(kh, None)
        try:
            ghi(os.path.join(lop_dir, "chi-muc.json"), cm["d"])
            cm["doi"] = False
        except OSError:
            pass


# ------------------------------------------------------------------ cảnh báo dễ hiểu (3/11)
def _gio_txt(t):
    """0:10,4 (như đồng hồ của trang)."""
    t = max(0.0, float(t or 0))
    m = int(t // 60)
    return "%d:%s" % (m, ("%04.1f" % (t - 60 * m)).replace(".", ","))


def _giay_txt(t):
    """3,6 / 6 (số giây, dấu phẩy, bỏ ',0')."""
    s = "%.1f" % float(t)
    return (s[:-2] if s.endswith(".0") else s).replace(".", ",")


def _ngoac(s, n=32):
    s = re.sub(r"\s+", " ", str(s or "").replace("|", " ")).strip()
    return '"%s"' % (s if len(s) <= n else s[:n - 1].rstrip() + "…")


def _vi_lop(ten, tl, pd_k, nh_k, tg_k):
    """Tên lớp PNG -> (tên người dùng hiểu, loại, _k mục liên quan | None)."""
    chu = tl.get("chu") or {}
    ten = str(ten or "")
    if ten == "hook.png":
        return "Hook", "hook", None
    if ten == "ket.png":
        return "Thẻ kết", "ket", None
    if ten == "the-gia.png":
        return "Thẻ giá", "gia", tg_k
    if ten == "tieu-de.png":
        return "Tiêu đề ghim", "tieu_de", None
    if ten == "brand.png":
        return "Chữ POLY STORE", "brand", None
    m = re.match(r"^nhan-(\d+)\.png$", ten)
    if m:
        i = int(m.group(1)) - 1
        ds = chu.get("nhan_chu") or []
        return ("Nhãn " + _ngoac(ds[i].get("chu")) if i < len(ds) else "Nhãn %d" % (i + 1)), "nhan", nh_k[i] if i < len(nh_k) else None
    m = re.match(r"^sticker-(\d+)\.png$", ten)
    if m:
        i = int(m.group(1)) - 1
        ds = chu.get("sticker") or []
        return ("Sticker " + _ngoac(ds[i].get("ten")) if i < len(ds) else "Sticker %d" % (i + 1)), "sticker", None
    m = re.match(r"^phu-de-(\d+)(?:-\d+)?\.png$", ten)
    if m:
        i = int(m.group(1)) - 1
        ds = tl.get("phu_de") or []
        return ("Câu " + _ngoac(ds[i].get("chu")) if i < len(ds) else "Câu %d" % (i + 1)), "phu_de", pd_k[i] if i < len(pd_k) else None
    return ten, None, None


def _k_lop(ten, pd_k, nh_k, tg_k):
    """r31: tên lớp PNG -> mã chữ trang dùng để chọn / kéo (hook, ket, tieu_de, brand, st:<i>, _k nhãn / thẻ giá / câu) | None."""
    ten = str(ten or "")
    k = {"hook.png": "hook", "ket.png": "ket", "tieu-de.png": "tieu_de", "brand.png": "brand", "the-gia.png": tg_k}.get(ten)
    if k:
        return k
    m = re.match(r"^(nhan|sticker|phu-de)-(\d+)(?:-\d+)?\.png$", ten)
    if not m:
        return None
    i = int(m.group(2)) - 1
    if m.group(1) == "sticker":
        return "st:%d" % i
    ds = nh_k if m.group(1) == "nhan" else pd_k
    return ds[i] if 0 <= i < len(ds) else None


def _goi_y_doi(loai):
    if loai in ("nhan", "gia"):
        return "nút ⇥ Vạch đỏ ở tab Chữ"
    if loai == "phu_de":
        return "nút ⇥ ở tab Phụ đề"
    return None


def _cb_de_hieu(x, tl, lop, ten_chu, pd_k, nh_k, tg_k):
    """1 cảnh báo của bộ dựng -> (câu lời thường, giây trên video | None, _k | None). Không nhận ra thì giữ câu gốc."""
    chu = tl.get("chu") or {}
    theo_ten = {l["ten"]: l for l in lop}
    ket_t = tl.get("ket_t") or [tl.get("T"), tl.get("T")]
    m = re.match(r"^(\S+\.png) đè (\S+\.png) lúc ([\d.]+)–([\d.]+)s", x)
    if m:
        a, b = m.group(1), m.group(2)
        ta, la_, ka = _vi_lop(a, tl, pd_k, nh_k, tg_k)
        tb, lb, kb = _vi_lop(b, tl, pd_k, nh_k, tg_k)
        if a in theo_ten and b in theo_ten:
            t0 = max(theo_ten[a]["t0"], theo_ten[b]["t0"])
            t1 = min(theo_ten[a]["t1"], theo_ten[b]["t1"])
        else:
            t0, t1 = float(m.group(3)), float(m.group(4))
        gy = _goi_y_doi(la_) or _goi_y_doi(lb)
        k = ka if _goi_y_doi(la_) else kb
        if {la_, lb} == {"hook", "ket"}:
            loi = "video ngắn quá nên 2 thẻ hiện cùng lúc: thêm cảnh hoặc cho thẻ kết hiện ngắn lại (tab Chữ › Hiện cuối video)"
        else:
            loi = "dời giờ một bên" + (" (%s)" % gy if gy else "")
        return "%s đè lên %s lúc %s–%s: %s" % (ta, tb, _gio_txt(t0), _gio_txt(t1), loi), round(t0, 3), k
    m = re.match(r"^phụ đề (\d+): (\d+) từ cuối bị thẻ kết cắt", x)
    if m:
        i, n = int(m.group(1)) - 1, int(m.group(2))
        ds = tl.get("phu_de") or []
        s = ds[i] if i < len(ds) else {}
        k = pd_k[i] if i < len(pd_k) else None
        try:
            import ve_chu as VC
            tong = len(VC.gio_tung_tu(s)) if s else 0
        except (KeyError, TypeError, ValueError):
            tong = 0
        cau ="Câu " + _ngoac(s.get("chu")) if s else "Câu %d" % (i + 1)
        goi_y = "dời câu sớm hơn hoặc cho thẻ kết hiện ngắn lại (tab Chữ › Hiện cuối video)"
        if tong and n >= tong:
            return "%s bị thẻ kết che hết nên không hiện: %s" % (cau, goi_y), s.get("t0"), k
        return "%s: %d chữ cuối bị thẻ kết che: %s" % (cau, n, goi_y), s.get("t0"), k
    m = re.match(r"^chữ '(.*)' phải thu còn (\d+)px", x)
    if m:
        txt = m.group(1)
        ten = next((tn for t, tn in ten_chu.items() if t[:40] == txt), None)
        ten_vi, loai, k = _vi_lop(ten, tl, pd_k, nh_k, tg_k) if ten else ("Chữ " + _ngoac(txt), None, None)
        t = theo_ten[ten]["t0"] if ten in theo_ten else None
        if loai == "nhan":
            return "%s dài quá nên chữ bị thu nhỏ: nên ≤ 18 ký tự" % ten_vi, t, k
        if loai == "hook":
            hk = [str(h or "").strip().lower() for h in chu.get("hook") or []]
            dong = 2 if len(hk) > 1 and txt.lower() == hk[1][:40] else 1
            return ('Hook dòng %d %s dài quá nên chữ bị thu nhỏ: nên ≤ %d ký tự' % (dong, _ngoac(txt), 20 if dong == 1 else 22)), t, k
        if loai == "phu_de":
            return "%s dài quá nên chữ bị thu nhỏ: rút ngắn hoặc tách thành 2 câu" % ten_vi, t, k
        if loai in ("gia", "ket", "tieu_de"):
            return "%s %s dài quá nên chữ bị thu nhỏ: rút ngắn lại" % (ten_vi, _ngoac(txt)), t, k
        return "%s dài quá nên chữ bị thu nhỏ: rút ngắn lại" % ten_vi, t, k
    m = re.match(r"^nhãn (\d+) '(.*)': quá ngắn hoặc đè thẻ kết, bỏ", x)
    if m:
        i = int(m.group(1)) - 1
        ds = chu.get("nhan_chu") or []
        t = ds[i].get("t0") if i < len(ds) else None
        return ("Nhãn %s không hiện vì quá ngắn hoặc nằm lúc thẻ kết đang hiện: dời nhãn sớm hơn (nút ⇥ Vạch đỏ ở tab Chữ)"
                % _ngoac(m.group(2))), t, nh_k[i] if i < len(nh_k) else None
    m = re.match(r"^sticker (\d+) '(.*)': quá ngắn hoặc đè thẻ kết, bỏ", x)
    if m:
        i = int(m.group(1)) - 1
        ds = chu.get("sticker") or []
        return ("Sticker %s không hiện vì quá ngắn hoặc nằm lúc thẻ kết đang hiện" % _ngoac(m.group(2)),
                ds[i].get("t0") if i < len(ds) else None, None)
    m = re.match(r"^(\S+\.png): (.*)$", x)
    if m:
        ten_vi, loai, k = _vi_lop(m.group(1), tl, pd_k, nh_k, tg_k)
        t = theo_ten[m.group(1)]["t0"] if m.group(1) in theo_ten else None
        loi = m.group(2)
        if "lấn cột nút bên phải" in loi:
            return "%s lấn sang cột nút bên phải của TikTok (tim, bình luận): rút ngắn chữ" % ten_vi, t, k
        if "thấp hơn" in loi:
            return "%s nằm thấp quá, dễ bị dòng mô tả của TikTok che" % ten_vi, t, k
        if "sát mép trái" in loi:
            return "%s sát mép trái quá" % ten_vi, t, k
        return "%s: %s" % (ten_vi, loi), t, k
    m = re.match(r"^ket_giay ([\d.]+)s dài quá \(video ([\d.]+)s, hook tới ([\d.]+)s\) — rút còn ([\d.]+)s", x)
    if m:
        return ("Thẻ kết hiện %s giây là dài quá với video %s (hook tới %s): tạm rút còn %s giây — chỉnh ở tab Chữ › Hiện cuối video"
                % (_giay_txt(m.group(1)), _gio_txt(m.group(2)), _gio_txt(m.group(3)), _giay_txt(m.group(4)))), ket_t[0], None
    m = re.match(r"^ket_giay ([\d.]+)s quá dài cho thẻ kết, dùng 6s", x)
    if m:
        return ("Thẻ kết hiện %s giây là quá dài, chỉ dùng 6 giây (tab Chữ › Hiện cuối video)" % _giay_txt(m.group(1))), ket_t[0], None
    m = re.match(r"^thẻ kết chỉ ([\d.]+)s, khó đọc kịp", x)
    if m:
        return ("Thẻ kết chỉ hiện %s giây, khó đọc kịp: nên ≥ 2 giây (tab Chữ › Hiện cuối video)" % _giay_txt(m.group(1))), ket_t[0], None
    m = re.match(r"^cảnh (\d+): (đầu|cuối) cắt giữa tiếng nói", x)
    if m:
        return "Cảnh %s: %s cảnh cắt giữa lúc đang nói, nghe sẽ bị vấp" % (m.group(1), m.group(2)), None, None
    return x, None, None


def _an_vi_ket(tl, gio, pd_k):
    """Câu phụ đề bị thẻ kết che: hết chữ (như cac_cum) -> ẩn kèm lý do; mất vài chữ cuối -> cat. Trả cảnh báo thêm
    [(câu, giây, _k)] cho kiểu cả câu (cac_cum chỉ chạy ở kiểu cụm ngắn)."""
    import ve_chu as VC
    chu = tl.get("chu") or {}
    co_ket = bool(chu.get("ket"))
    het = tl["ket_t"][0] if co_ket else tl["T"]
    ket_giay = float(tl["ket_t"][1]) - float(tl["ket_t"][0]) if co_ket else 0.0
    cum = (tl.get("kieu") or {}).get("phu_de") == "cum_ngan"
    them = []
    for n, s in enumerate(tl.get("phu_de") or []):
        k = pd_k[n] if n < len(pd_k) else None
        if not k:
            continue
        try:
            tat_ca = VC.gio_tung_tu(s)
            t0 = float(s.get("t0") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        con = [w for w in tat_ca if w[1] < het - 0.05]
        mat = len(tat_ca) - len(con)
        an = not con or (not cum and co_ket and t0 >= het - 0.3)  # kiểu cả câu: render bỏ câu bắt đầu < 0,3s trước thẻ kết
        if an:
            ly = ("Bị thẻ kết che (thẻ kết hiện %s giây cuối)" % _giay_txt(ket_giay)) if co_ket else "Nằm sau cuối video"
            gio[k] = {"an": True, "ly_do": ly}
        elif mat:
            g = gio.setdefault(k, {"t0": s.get("t0"), "t1": s.get("t1")})
            g["cat"] = True
            g["ly_do_cat"] = ("%d chữ cuối bị thẻ kết che" % mat) if co_ket else ("%d chữ cuối nằm sau cuối video" % mat)
        if not cum and co_ket and (an or mat):
            goi_y = "dời câu sớm hơn hoặc cho thẻ kết hiện ngắn lại (tab Chữ › Hiện cuối video)"
            if an:
                them.append(("Câu %s bị thẻ kết che hết nên không hiện: %s" % (_ngoac(s.get("chu")), goi_y), s.get("t0"), k))
            else:
                them.append(("Câu %s: %d chữ cuối bị thẻ kết che: %s" % (_ngoac(s.get("chu")), mat, goi_y), s.get("t0"), k))
    return them


_GIAY_TEP = {}


def _giay_tep(p):
    """Độ dài (giây) file tiếng / hình bất kỳ (ffprobe format=duration), nhớ theo cỡ + giờ sửa file."""
    try:
        st = os.stat(p)
    except OSError:
        return None
    k = (p, st.st_size, int(st.st_mtime))
    if k not in _GIAY_TEP:
        try:
            r = subprocess.run([chung.FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", p],
                               capture_output=True, text=True, timeout=30, **KW)
            _GIAY_TEP[k] = round(float((r.stdout or "").strip().splitlines()[0]), 3)
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            _GIAY_TEP[k] = None
    return _GIAY_TEP[k]


def _xem_trong(plan):
    """Video 0 cảnh (4/11 18:14, anh: "có thể xóa hết video không cần chừa lại"): bản xem trống, KHÔNG gọi bộ dựng (KH.build cần
    ít nhất 1 cảnh). Chữ / phụ đề / thẻ giá vẫn giữ trong kế hoạch, đánh ẩn kèm lý do để bảng phải không treo "…"."""
    an = {"an": True, "ly_do": "Video chưa có cảnh nào: thêm clip là chữ hiện lại"}
    chu = plan.get("chu") or {}
    ds = [it for it in (plan.get("phu_de") or []) + (chu.get("nhan_chu") or []) + [chu.get("the_gia")] if isinstance(it, dict) and it.get("_k")]
    return {"T": 0.0, "hook_t": None, "ket_t": None, "doan": [], "canh": [], "gio": {it["_k"]: dict(an) for it in ds}, "lop": [],
            "khoa_chu": "", "canh_bao": [], "canh_bao_ct": [], "ve_lai": 0, "plan": plan, "trong": True}


def lenh_xem(d):
    """Kế hoạch đang sửa -> dữ liệu xem trước: đoạn phát (giờ clip / giờ video), mốc cảnh, giờ từng câu, lớp chữ PNG.
    Trả thêm (3/11): canh_bao_ct [{chu, t, k}] cùng thứ tự canh_bao (trang làm nút tua tới), ve_lai (số lớp vừa vẽ)."""
    import ve_chu as VC
    plan = d["plan"]
    W = W_cua(d["v"])
    danh_dau(plan)
    if not plan.get("canh"):
        return _xem_trong(plan)
    gan_neo(plan, "may_chu")  # đoạn mới thêm: giờ đang là giờ trên bản xem trước (đường ffmpeg)
    p, gio, _, _ = ap_neo(plan, "may_chu")
    ps = sach(p)
    ps["kieu"] = _kieu_xem(ps.get("kieu"))
    _mo_dau_an_toan(ps)
    _giong_thay_tieng(ps)
    ps["cat_cho_lang"] = False
    with contextlib.redirect_stdout(sys.stderr):
        tl = KH.build(ps, "may_chu")
    m = moc(tl)
    canh = p.get("canh") or []
    kc = (tl.get("kieu") or {}).get("chuyen_canh")
    doan, t = [], 0.0
    for s in tl["shots"]:
        st = t - float(s.get("chuyen") or 0.0)
        doan.append({"file": s["file"], "tu": s["tu"], "den": s["den"], "bd": round(st, 4), "dur": s["dur"],
                     "z0": s.get("z0", 1), "z1": s.get("z1", 1), "x0": s.get("x0", 0), "x1": s.get("x1", 0),
                     "easing": s.get("easing", "muot"), "the_hoi": s.get("the_hoi") or 0, "dong_bang": s.get("dong_bang") or 0,
                     "canh": s["canh"], "id": canh[s["canh"]].get("_id") if 0 <= s["canh"] < len(canh) else None,
                     "chuyen": s.get("chuyen") or 0,
                     # kiểu chuyển cảnh đúng như bộ dựng (r27, khung xem vẽ chuyển cảnh: dev/_mod-xem-chuyen.js): khoá kiểu riêng cảnh /
                     # kiểu chung, hoặc tên Film Impact của "Trộn" + bản xfade gần nhất
                     **({"chuyen_ten": s.get("chuyen_ten") or kc, "chuyen_xfade": s.get("chuyen_xfade")} if s.get("chuyen") else {}),
                     # khung tĩnh / màu / âm lượng riêng cảnh (3/11, kiểu CapCut): trang xem trước theo bằng CSS transform / filter, video.volume
                     **{k: s[k] for k in ("khung", "mau", "am_luong") if k in s}})
        t = st + s["dur"]
    # chữ: mã cả bản (giữ như cũ, trang có thể dùng) + vẽ theo từng lớp đã nhớ
    khoa = {k: tl.get(k) for k in ("chu", "phu_de", "T", "hook_t", "ket_t", "fps", "khung")}
    khoa["kieu"] = {k: v for k, v in (tl.get("kieu") or {}).items() if k in ("chu", "phu_de", "ket", "vi_tri_chu", "mo_dau", "bo_font",
                                                                          "diem_nhan", "lop_phu", "thanh_tien_trinh",
                                                                          "bo_mau", "kieu_phu_de")}   # r36: đổi bộ mẫu -> vẽ lại
    h = hashlib.md5(json.dumps(khoa, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:14]
    goc = os.path.join(W, "sua-tay", "xem")
    ve = _ve_xem(VC, tl, goc, h)
    lop = [{"png": xuoi(l["png"]), "t0": l["t0"], "t1": l["t1"], "ten": l.get("ten"), "loai": l.get("loai"), "hop": l.get("hop"),
            **({"mo": l["mo_nen"]} if l.get("mo_nen") else {})}   # r36: kính mờ -> trang làm mờ cảnh dưới lớp (backdrop-filter)
           for l in ve["lop"] if not str(l.get("ten", "")).startswith("fx-")]
    # _k của từng câu / nhãn theo thứ tự trên dòng thời gian (sach() bỏ mục ẩn / trống, giữ thứ tự)
    pd_k = [it.get("_k") for it in p.get("phu_de") or [] if not it.get("_an") and _khong_rong(it.get("chu"))]
    pchu = p.get("chu") or {}
    nh_k = [it.get("_k") for it in pchu.get("nhan_chu") or [] if not it.get("_an") and _khong_rong(it.get("chu"))]
    tg_k = pchu["the_gia"].get("_k") if isinstance(pchu.get("the_gia"), dict) else None
    if len(pd_k) != len(tl.get("phu_de") or []):
        pd_k = []
    if len(nh_k) != len(((tl.get("chu") or {}).get("nhan_chu") or [])):
        nh_k = []
    for l in lop:  # r31 (kéo chữ trên khung xem): lớp nào là chữ nào (hook / ket / tieu_de / brand / st:<i> / _k nhãn, giá, câu)
        k_ = _k_lop(l.get("ten"), pd_k, nh_k, tg_k)
        if k_:
            l["k"] = k_
    them = _an_vi_ket(tl, gio, pd_k)
    # nhãn nằm trong thẻ kết: ve_chu cắt t1 về đầu thẻ kết, còn < 0,2s thì bỏ -> đánh ẩn kèm lý do (trang hiện mờ + cách sửa)
    if (tl.get("chu") or {}).get("ket") and tl.get("ket_t"):
        k0 = float(tl["ket_t"][0])
        for n, it in enumerate((tl.get("chu") or {}).get("nhan_chu") or []):
            try:
                t0n = float(it.get("t0") or 0)
            except (TypeError, ValueError):
                continue
            if n < len(nh_k) and nh_k[n] and t0n > k0 - 0.2:
                gio[nh_k[n]] = {"an": True, "ly_do": "Bị thẻ kết che (thẻ kết hiện %s giây cuối): dời nhãn sớm hơn"
                                % _giay_txt(float(tl["ket_t"][1]) - k0)}
    goc_cb =[x for x in (tl.get("canh_bao") or []) + ve["warn"] if "phải thu còn" in x or "đè" in x or "cắt" in x
              or "ngắn" in x or "dài" in x or "lấn" in x or "thấp" in x]
    ct = []
    for x in goc_cb:
        try:
            chu_, tt, k = _cb_de_hieu(x, tl, ve["lop"], ve["ten_chu"], pd_k, nh_k, tg_k)
        except Exception:  # noqa  mẫu lạ: giữ câu gốc
            traceback.print_exc()
            chu_, tt, k = x, None, None
        ct.append((chu_, tt, k))
    ct += them
    gi = plan.get("giong")
    if gi and gi.get("local"):
        gg = _giay_tep(gi["local"])  # giay_clip (do_clip) cần có hình -> file giọng .wav/.mp3 luôn ra None, cảnh báo không bao giờ hiện
        if gg and gg > tl["T"] + 0.3:
            ct.append(("Video dài %s giây, ngắn hơn giọng đọc AI (%s giây): đoạn giọng cuối sẽ bị cắt — thêm cảnh hoặc kéo dài cảnh cuối"
                       % (_giay_txt(tl["T"]), _giay_txt(gg)), tl["T"], None))
    da, cb, cb_ct = set(), [], []
    for chu_, tt, k in ct:
        if chu_ in da:
            continue
        da.add(chu_)
        cb.append(chu_)
        cb_ct.append({"chu": chu_, "t": round(float(tt), 3) if isinstance(tt, (int, float)) else None, "k": k})
    vt = []  # vị trí từng khối cảnh trên video (cảnh đã gộp: chia lại theo từng phần anh thấy trên timeline)
    for i in sorted(m):
        c, x = canh[i], m[i]
        phan = c.get("_phan") or [[c.get("_id"), float(c["tu"]), float(c["den"])]]
        for j, (pid, a, b) in enumerate(phan):
            bd = x["bd"] + a - float(c["tu"])
            vt.append({"id": pid, "dau": round(x["dau"] if j == 0 else bd, 4), "bd": round(bd, 4),
                       "kt": round(x["kt"] if j == len(phan) - 1 else bd + b - a, 4)})
    return {"T": tl["T"], "hook_t": tl["hook_t"], "ket_t": tl["ket_t"] if (tl.get("chu") or {}).get("ket") else None,
            "doan": doan, "canh": vt,
            "gio": gio, "lop": lop, "khoa_chu": h, "canh_bao": cb[:12], "canh_bao_ct": cb_ct[:12], "ve_lai": ve["ve_moi"],
            "pd_y_goc": VC.pd_y_goc(tl.get("kieu")) if hasattr(VC, "pd_y_goc") else None,   # r31: chân chữ phụ đề mặc định (chu.vi_tri.phu_de)
            "plan": plan}


def don_xem(goc, giu=None, toi_da=4):
    try:
        ds = sorted((os.path.join(goc, n) for n in os.listdir(goc)), key=lambda x: -os.path.getmtime(x))
    except OSError:
        return
    for x in ds[toi_da:]:
        if x != giu and os.path.isdir(x):
            shutil.rmtree(x, ignore_errors=True)


def lenh_luu(d):
    """Ghi ke-hoach.json (giờ theo đường dựng của kế hoạch), bản cũ cất vào lam/sua-tay/lich-su/. Trả kế hoạch đã ghi."""
    v = d["v"]
    W = W_cua(v)
    plan = d["plan"]
    danh_dau(plan)
    gan_neo(plan, "may_chu")
    duong = (plan.get("kieu") or {}).get("duong") or "may_chu"
    p, _, _, _ = ap_neo(plan, duong)
    if d.get("ra"):
        p["ra"] = d["ra"]
        plan["ra"] = d["ra"]
    out = sach(p)
    kp = os.path.join(W, "ke-hoach.json")
    if os.path.isfile(kp):
        ls = os.path.join(W, "sua-tay", "lich-su")
        os.makedirs(ls, exist_ok=True)
        shutil.copy2(kp, os.path.join(ls, "ke-hoach-%s.json" % time.strftime("%Y%m%d-%H%M%S")))
        don_xem(ls, toi_da=30)
    ghi(kp, out)
    nh = os.path.join(W, "sua-tay", "dang-sua.json")
    cu = doc(nh) if d.get("dau_van_xuat") else None
    if isinstance(cu, dict) and isinstance(cu.get("plan"), dict) and _dau_van(cu["plan"]) != d["dau_van_xuat"]:
        # anh sửa tiếp TRONG LÚC đang xuất (kể cả đã F5 / mở video khác): giữ bản sửa dở đó, coi như dựa trên kế hoạch vừa ghi
        cu.update({"kp_mtime": os.path.getmtime(kp), "da_luu": False})
        ghi(nh, cu)
    else:
        # bản đang sửa giữ đủ neo, câu đang ẩn… để mở lại vẫn sửa tiếp được (dựa trên đúng ke-hoach.json vừa ghi)
        ghi(nh, {"luc": time.time(), "plan": plan, "kp_mtime": os.path.getmtime(kp), "da_luu": True, "phien": d.get("phien")})
    return {"ok": True, "ke_hoach": xuoi(kp), "kp_mtime": os.path.getmtime(kp)}


def _dau_van(plan):
    """Dấu vân nội dung kế hoạch (so bản sửa dở với bản đang xuất: khác = anh đã sửa thêm)."""
    p = plan if isinstance(plan, dict) else {}
    d = {k: p.get(k) for k in ("canh", "chu", "phu_de", "kieu", "ket_giay", "giong", "nguon", "nhac", "can_tieng")}
    for k in ("am_tach", "am_thanh", "giong_de"):   # tiếng tách (4/11) / âm thanh hiệu ứng (r20) / giọng AI đọc lại (r32): chỉ thêm khi có -> dấu vân kế hoạch cũ y hệt
        if p.get(k):
            d[k] = p[k]
    return json.dumps(d, sort_keys=True, ensure_ascii=False)


def lenh_nhap(d):
    """Lưu bản đang sửa. kp_mtime = mốc ke-hoach.json lúc trang mở (trang gửi lên): kế hoạch bị ghi lại sau đó (vd Claude sửa)
    thì lần mở sau dùng kế hoạch mới, không lấy bản nháp cũ đè lên.
    phien = mã cửa sổ, moc = "luc" bản sửa dở cửa sổ đó thấy lần cuối: cửa sổ KHÁC đã ghi sau mốc đó thì không ghi đè
    (2 cửa sổ cùng mở 1 video), trả xung_dot để trang hỏi anh; ep = anh chọn giữ bản của mình."""
    W = W_cua(d["v"])
    kp = os.path.join(W, "ke-hoach.json")
    nh = os.path.join(W, "sua-tay", "dang-sua.json")
    km = d.get("kp_mtime")
    if km is None:
        km = os.path.getmtime(kp) if os.path.isfile(kp) else None
    cu = doc(nh) if d.get("phien") and not d.get("ep") else None
    if isinstance(cu, dict) and cu.get("phien") and cu["phien"] != d["phien"] and float(cu.get("luc") or 0) > float(d.get("moc") or 0) + 1e-6:
        return {"ok": False, "xung_dot": True, "luc": cu.get("luc")}
    luc = time.time()
    ghi(nh, {"luc": luc, "plan": d["plan"], "kp_mtime": km, "phien": d.get("phien")})
    return {"ok": True, "luc": luc}


def lenh_do_clip(d):
    p = d["p"]
    x = do_clip(p)
    return dict(x, local=xuoi(p))


def lenh_moi(d):
    """Tạo video mới từ clip (không qua Claude): thư mục <ra>/<slug>/lam/ke-hoach.json, mỗi clip 1 cảnh, kiểu đúng gu kênh."""
    ra, slug, clips = d["ra"], d["slug"], d["clip"]
    v = os.path.join(ra, slug)
    W = W_cua(v)
    os.makedirs(W, exist_ok=True)
    nguon, canh = {}, []
    for c in clips:
        x = do_clip(c)
        f = xuoi(c)
        nguon[f] = {"local": f, "rong": x["rong"], "cao": x["cao"], "co_tieng": x["co_tieng"], "hdr": x["hdr"],
                    "hdr_trc": x["hdr_trc"], "am_thanh": "tieng_that" if x["co_tieng"] else None}
        if x["giay"] > 0.3:
            canh.append({"file": f, "tu": 0.0, "den": round(max(0.3, x["giay"] - 0.05), 3)})
    if not canh:
        raise SystemExit("Các clip đã chọn không đọc được hoặc quá ngắn")
    deck = CK.load(os.path.join(E, "kieu_dung.json"), None)
    # kiểu: "dung_gu" (mặc định) ghim gu kênh (chữ, thẻ kết, nhịp), cộng các mục anh tự chọn ở cột Video mới (chỉ nhận giá trị bộ dựng
    # ffmpeg làm được)
    ghim = dict(CK.DUNG_GU) if (d.get("che_do") or "dung_gu") == "dung_gu" else {}
    muc, chi_p = deck.get("muc") or {}, deck.get("chi_premiere") or {}
    for m, val in (d.get("kieu") or {}).items():
        if not isinstance(val, str) or val in ("", "tu_dong") or m not in muc:
            continue
        if (val in muc[m] or val in CK.GIA_TRI_THEM.get(m, []) or val in KIEU_THEM.get(m, {})) and val not in (chi_p.get(m) or []):
            ghim[m] = val
    # MẶC ĐỊNH TRƠN (anh chốt 4/11 18:10 "video cho mặc định từ đầu, hiệu ứng thêm sau"): KHÔNG bốc kiểu ngẫu nhiên nữa. Hiệu ứng = tắt
    # (TRON); chữ / thẻ kết / nhịp = gu kênh (DUNG_GU); màu trung tính; mục khác = giá trị kênh hay dùng nhất (trong_so, bằng nhau thì
    # giá trị đầu). Mục anh tự chọn ở cột Video mới (ghim) thắng tất cả.
    ts = deck.get("trong_so") or {}
    kieu = {}
    for m, vals in muc.items():
        ds_ = [v for v in vals if v not in (chi_p.get(m) or [])] or list(vals)
        if m in ghim:
            kieu[m] = ghim[m]
        elif m in TRON:
            kieu[m] = TRON[m]
        elif m in CK.DUNG_GU:
            kieu[m] = CK.DUNG_GU[m]
        elif m == "mau" and "trung_tinh" in vals:
            kieu[m] = "trung_tinh"
        else:
            kieu[m] = max(ds_, key=lambda v: (float((ts.get(m) or {}).get(v, 1)), -ds_.index(v)))
    kieu["duong"] = "may_chu"
    kieu["_ghim"] = sorted(ghim)
    # chữ điền sẵn từ cột Video mới: hook 2 dòng, thẻ giá, tên máy (kiểu chữ "Thẻ bìa máy")
    h = [str(x or "").strip()[:60] for x in (d.get("hook") or [])][:2]
    while h and not h[-1]:
        h.pop()
    chu = {"hook": h, "brand": True}
    tong = sum(c["den"] - c["tu"] for c in canh)
    gia = str(d.get("gia") or "").strip()[:30]
    if gia:
        t0 = round(max(0.0, min(8.0, max(1.0, tong * 0.4), tong - 1.0)), 2)
        chu["the_gia"] = {"t0": t0, "t1": round(min(tong, t0 + 3.0), 2), "gia": gia, "phu": ""}
    may = str(d.get("may") or "").strip()[:60]
    if may:
        chu["the_bia"] = {"ten": may}
    plan = {"ten": slug, "khung": [1080, 1920], "fps": 30, "nguon": nguon, "canh": canh,
            "chu": chu, "phu_de": [], "giong": None, "kieu": kieu, "ket_giay": 3.6,
            "ra": {"thu_muc": xuoi(os.path.join(v, "v1")), "ten_file": slug + "-v1.mp4"}, "_tao_boi": "sua_tay"}
    ghi(os.path.join(W, "ke-hoach.json"), plan)
    return {"v": xuoi(v)}


LENH = {"mo": lenh_mo, "xem": lenh_xem, "luu": lenh_luu, "nhap": lenh_nhap, "do_clip": lenh_do_clip, "moi": lenh_moi,
        "ping": lambda d: {"ok": True, "engine": xuoi(E)}}


def _xem_doc_lai(d):
    """r32 (giọng AI đọc lại khối tách, engine/doc_lai.py): xem trước như cũ + "giong_de" = các câu giọng đã đặt giờ trên video
    (trang vẽ làn Giọng, khung xem phát đúng chỗ) + báo câu giọng dài đè lên câu sau. Kế hoạch không có khoá: trả y hệt lenh_xem."""
    r = lenh_xem(d)
    plan = d.get("plan") or {}
    if not plan.get("giong_de") or not isinstance(r, dict) or r.get("trong"):
        return r
    import doc_lai
    x = doc_lai.dat(plan, r.get("T"))
    r["giong_de"] = x
    for c, d_ in doc_lai.tran(x["dat"]):
        m = "Câu giọng AI %s dài hơn chỗ trống %s giây: đè lên câu sau (sửa lời ngắn lại rồi tạo lại, hoặc dời khối tiếng)" % (
            _ngoac(c["chu"]), _giay_txt(d_))
        if m not in r["canh_bao"] and len(r["canh_bao"]) < 12:
            r["canh_bao"].append(m)
            r["canh_bao_ct"].append({"chu": m, "t": c["t"], "k": None})
    return r


LENH["xem"] = _xem_doc_lai


def phuc_vu():
    out = sys.stdout
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
        out.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    sys.stdout = sys.stderr  # bộ dựng in gì cũng sang stderr, stdout chỉ để trả lời app
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        rid = None
        try:
            req = json.loads(line)
            rid = req.get("id")
            kq = LENH[req["lenh"]](req.get("data") or {})
            res = {"id": rid, "ok": True, "kq": kq}
        except SystemExit as e:
            res = {"id": rid, "ok": False, "loi": str(e)}
        except Exception as e:  # noqa
            traceback.print_exc()
            res = {"id": rid, "ok": False, "loi": "Lỗi bộ dựng: %s" % e, "chi_tiet": traceback.format_exc()[-1500:]}
        out.write(json.dumps(res, ensure_ascii=False) + "\n")
        out.flush()


# ------------------------------------------------------------------ xuất video
def in_(s):
    print(s, flush=True)


def xuat(viec_p):
    """Dựng 1 bản: bản nháp (540x960, nhanh) vào lam/sua-tay/nhap/, bản đẹp vào <video>/v<n>/ + cập nhật ket-qua.json."""
    import ve_chu as VC
    viec = doc(viec_p)
    v = viec["v"]
    W = W_cua(v)
    nhap = bool(viec.get("nhap"))
    plan = viec["plan"]
    dv_xuat = _dau_van(plan)   # trước khi gắn neo: so với bản sửa dở lúc xong (anh sửa thêm trong lúc xuất thì giữ phần đó)
    dd = viec.get("dinh_dang") or {}   # định dạng xuất (3/11): chat_luong nhe|chuan|cao, fps, them [720p, hevc, mov]
    if not nhap and dd.get("fps") in (24, 25, 30, 50, 60):
        plan["fps"] = dd["fps"]
    danh_dau(plan)
    gan_neo(plan, "may_chu")
    in_("BUOC=Chuẩn bị")
    p, _, _, _ = ap_neo(plan, "may_chu")
    ps = sach(p)
    ps["kieu"] = _kieu_xem(ps.get("kieu"))
    _mo_dau_an_toan(ps)
    _giong_thay_tieng(ps)
    if nhap:
        M = os.path.join(W, "sua-tay", "nhap")
        if os.path.isdir(M):
            shutil.rmtree(M, ignore_errors=True)
        out = os.path.join(M, "ban-nhap.mp4")
    else:
        M = viec["thu_muc_may"]
        out = os.path.join(M, viec["ten_file"])
    os.makedirs(M, exist_ok=True)
    with contextlib.redirect_stdout(sys.stderr):
        tl = KH.build(ps, "may_chu")
    dtg = os.path.join(M, "dong-thoi-gian.json")
    ghi(dtg, tl)
    in_("BUOC=Vẽ chữ")
    chu_d = os.path.join(M, "chu")
    with contextlib.redirect_stdout(sys.stderr):
        _, warn = VC.render(tl, chu_d)
    lopj = doc(os.path.join(chu_d, "lop-chu.json"), {}) or {}
    cb = []
    for w in [w for w in warn if "màu" not in w][:10]:
        try:   # cùng cách nói với khung xem trước (3/11, soi lần 2 A11): không in "ket.png", "ket_giay"…
            cb.append(_cb_de_hieu(w, tl, lopj.get("lop") or [], {}, [], [], None)[0])
        except Exception:  # noqa  mẫu lạ: giữ câu gốc
            cb.append(w)
    cb = [re.sub(r"giảm ket_giay", "cho thẻ kết hiện ngắn lại (tab Chữ › Hiện cuối video)", x) for x in cb]
    in_("CANH_BAO=" + json.dumps(cb, ensure_ascii=False))
    in_("BUOC=Dựng video")
    t0 = time.time()
    r = subprocess.run([sys.executable, os.path.join(E, "dung_may_chu.py"), dtg, os.path.join(chu_d, "lop-chu.json"), out]
                       + (["--nhap"] if nhap else ["--chat-luong=" + (dd.get("chat_luong") if dd.get("chat_luong") in ("nhe", "chuan", "cao") else "chuan")]),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=E, **KW)
    if r.returncode or not os.path.isfile(out):
        in_("LOI=Dựng video lỗi: " + re.sub(r"\s+", " ", (r.stderr or r.stdout or "")[-600:]))
        sys.exit(1)
    kq = {}
    try:
        kq = json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        pass
    if isinstance(kq.get("tron"), dict) and kq["tron"].get("loi"):   # nhạc nền đọc không được (4/11): báo, video vẫn xuất không nhạc
        in_("CANH_BAO=" + json.dumps(cb + ["Nhạc nền: " + kq["tron"]["loi"]], ensure_ascii=False))
    khung = ""
    if not nhap:
        in_("BUOC=Hoàn tất")
        khung = os.path.join(M, "khung-dau.jpg")
        subprocess.run([chung.FFMPEG, "-v", "error", "-y", "-ss", "0.6", "-i", out, "-frames:v", "1", "-vf", "scale=540:-2", khung],
                       capture_output=True, **KW)
        khung = khung if os.path.isfile(khung) else ""
        them, them_loi = _xuat_them(out, dd)
        # dựng xong mới ghi kế hoạch (ra = bản này) + ket-qua.json: lỗi / dừng giữa chừng thì kế hoạch, thẻ video vẫn như cũ
        luu = lenh_luu({"v": v, "plan": plan, "ra": {"thu_muc": xuoi(M), "ten_file": viec["ten_file"]}, "dau_van_xuat": dv_xuat, "phien": viec.get("phien")})
        cap_nhat_ket_qua(v, out, khung, ps, kq)
        if plan.get("_tao_boi") == "sua_tay":
            ghi_lich_su(out, ps.get("kieu") or {})
    if nhap:
        them, them_loi = [], []
    tk_them = {}
    if "ma_hoa" in sys.modules:   # bản xuất thêm (720p / HEVC) vừa mã hoá trong tiến trình này (10/11: app ghi log card)
        x_ = sys.modules["ma_hoa"].thong_ke()
        tk_them = {"them_ma_hoa": x_["ma_hoa"], "them_lui": x_["ma_hoa_lui"]}
    in_("XONG=" + json.dumps(dict({"mp4": xuoi(out), "giay": kq.get("T"), "khung_dau": xuoi(khung) if khung else "", "them": them, "them_loi": them_loi,
                                   "nhap": nhap, "phut": round((time.time() - t0) / 60, 1),
                                   "kp_mtime": luu["kp_mtime"] if not nhap else None,
                                   "ma_hoa": kq.get("ma_hoa"), "card": kq.get("card"),
                                   **({"noi_moi": kq["noi_moi"]} if kq.get("noi_moi") else {})}, **tk_them), ensure_ascii=False))   # r35: chỗ nối kiểu mới


THEM_DD = {"720p": ("-720p.mp4", "720p nhẹ"), "hevc": ("-hevc.mp4", "HEVC (H.265)"), "mov": (".mov", "MOV")}


def _xuat_them(out, dd):
    """Bản xuất thêm từ bản chính (3/11): 720p nhẹ gửi Zalo, HEVC nhỏ hơn, MOV cho iMovie / Final Cut. -> ([đường], [lỗi])."""
    them, loi = [], []
    goc = os.path.splitext(out)[0]
    crf = {"nhe": 25, "cao": 18}.get(dd.get("chat_luong"), 21)
    for x in [y for y in (dd.get("them") or []) if y in THEM_DD]:
        ra = goc + THEM_DD[x][0]
        in_("BUOC=Xuất thêm bản " + THEM_DD[x][1])

        def lenh(v, x=x, ra=ra):   # v = tham số mã hoá hình (ma_hoa: card đồ hoạ nếu có, 3/11)
            if x == "mov":
                cmd = ["-c", "copy"]
            elif x == "720p":
                cmd = ["-vf", "scale=720:1280:flags=lanczos"] + v + ["-c:a", "aac", "-b:a", "128k"]
            else:
                cmd = v + ["-tag:v", "hvc1", "-c:a", "copy"]
            return [chung.FFMPEG, "-v", "error", "-y", "-i", out] + cmd + ["-movflags", "+faststart", ra]

        def chay1(cmd, ra=ra):
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **KW)
            if r.returncode or not os.path.isfile(ra) or os.path.getsize(ra) < 1000:
                raise SystemExit(re.sub(r"\s+", " ", r.stderr or "")[-160:])
        try:
            if x == "mov":
                chay1(lenh(None))
            else:
                import ma_hoa
                ma_hoa.chay(lenh, chay1, codec="h264" if x == "720p" else "hevc", crf=crf + (2 if x == "720p" else 3),
                            preset="medium" if x == "720p" else "fast")
            them.append(xuoi(ra))
        except SystemExit as e:
            loi.append("Không xuất được bản %s%s" % (THEM_DD[x][1], (": " + str(e)) if str(e) else ""))
            try:
                os.remove(ra)
            except OSError:
                pass
    return them, loi


def cap_nhat_ket_qua(v, mp4, khung, plan, kq):
    import don as DON
    p = os.path.join(v, "ket-qua.json")
    cu = doc(p, {}, chac=True) or {}
    k = dict(plan.get("kieu") or {}, duong="may_chu")
    ten = os.path.basename(os.path.dirname(mp4))
    out = dict(cu)
    out.update({"mp4": chung.duong(os.path.abspath(mp4)), "prproj": "", "kieu_ten": DON.kieu_ten(k),
                "giay": round(float(kq.get("T") or 0), 1) or DON.thoi_luong(mp4), "khung_dau": chung.duong(khung) if khung else "",
                "to_duyet": "", "duyet": "",
                "ghi_chu": "Sửa tay trong POLY Cut, bản %s (dựng bằng ffmpeg, %s)." % (ten, time.strftime("%H:%M %d/%m"))})
    ghi(p, out)


def ghi_lich_su(mp4, kieu):
    ls_p = os.path.join(E, "lich-su-kieu.json")
    ls = doc(ls_p, []) or []
    ten = os.path.splitext(os.path.basename(mp4))[0]
    if not any(h.get("ten") == ten for h in ls):
        ls.append({"ten": ten, "ngay": datetime.date.today().isoformat(),
                   "kieu": {m: v for m, v in kieu.items() if not m.startswith("_")}})
        ghi(ls_p, ls)


# ------------------------------------------------------------------ tự tạo phụ đề từ lời nói (3/11)
def _nghe_clip(rec, src, kho, khoa="greedy", bo_im=None):
    """Nghe cả clip 1 lần (máy nghe sherpa, cắt đoạn ở chỗ im như nghe.py) -> {do_dai, tu: [[từ, giây, hết, đoạn]]}, có cache.
    khoa = cách nghe (tu_dien.recognizer: "greedy" như cũ / "hw-…" ưu tiên từ của tiệm): đổi từ hay nói thì nghe lại.
    Cache giữ lời máy nghe THÔ; sửa theo từ điển làm sau (nghe_phu_de) nên anh sửa luật "sai => đúng" là có tác dụng ngay.
    bo_im = tu_dien.bo_im_dau (4/11): bỏ khoảng im đầu mỗi đoạn trước khi nghe — sherpa đặt chữ đầu ở giây 0 khi đầu đoạn im
    (clip thật: phụ đề "trên tay" / "với hiệu" hiện sớm 1–2 giây, câu đầu bị tách đôi); đoạn không có tiếng thì bỏ."""
    import tempfile
    import numpy as np
    import nghe as NG
    st = os.stat(src)
    k = hashlib.md5(("%s|%s|%s|nghe1%s%s" % (src, st.st_size, int(st.st_mtime), "" if khoa == "greedy" else "|" + khoa,
                                            "|im1" if bo_im else "")).encode("utf-8")).hexdigest()
    cp = os.path.join(kho, k + ".json")
    cu = doc(cp)
    if isinstance(cu, dict) and "tu" in cu:
        return cu
    out = {"do_dai": 0.0, "tu": []}
    with tempfile.TemporaryDirectory() as tmp:
        try:
            with contextlib.redirect_stdout(sys.stderr):
                a, w = NG.doc_wav(src, tmp)
        except Exception:  # noqa  clip không có tiếng
            # 4/11: chỉ nhớ "không có lời" khi clip THẬT SỰ không có tiếng. Lỗi lúc đọc (ổ rút ra, file đang chép dở, ffmpeg lỗi tạm)
            # trước đây cũng nhớ mãi -> bấm Tạo phụ đề lần sau vẫn "không nghe thấy lời nói" dù clip có tiếng
            try:
                khong_tieng = not do_clip(src).get("co_tieng")
            except BaseException:  # noqa  không đọc được clip: không nhớ
                khong_tieng = False
            if khong_tieng:
                ghi(cp, out)
            return out
        dur = len(a) / 16000.0
        out["do_dai"] = round(dur, 2)
        for n, (t0, t1) in enumerate(NG.cat_doan(dur, NG.cho_im(w, dur))):
            if bo_im:
                t0 = bo_im(a, t0, t1)
                if t0 is None:   # đoạn không có tiếng
                    continue
            s = rec.create_stream()
            s.accept_waveform(16000, a[int(t0 * 16000):int(t1 * 16000)].astype(np.float32))
            rec.decode_stream(s)
            r = s.result
            tu, cur = [], None
            for tok, ts in zip(r.tokens, r.timestamps):
                t = round(t0 + ts, 2)
                if tok.startswith(("▁", " ")) or cur is None:
                    if cur and cur[0]:
                        tu.append(cur)
                    cur = [tok.lstrip("▁ "), t, t + 0.2]
                else:
                    cur[0] += tok
                    cur[2] = t + 0.2
            if cur and cur[0]:
                tu.append(cur)
            tu = [[x[0].lower(), x[1], round(x[2], 2), n] for x in tu if x[0].strip()]
            for i in range(len(tu) - 1):
                tu[i][2] = round(min(tu[i][2] + 0.15, tu[i + 1][1]), 2)
            out["tu"] += tu
    ghi(cp, out)
    return out


def _chia_cau(ds, toi_da=6):
    """[[từ, giây, hết, đoạn]] (đã theo giờ) -> các câu 3–6 từ: ngắt ở chỗ nghỉ > 0,45s / đổi đoạn, câu dài chia đều."""
    chuoi, cur = [], []
    for w in ds:
        if cur and (w[1] - cur[-1][2] > 0.45 or w[3] != cur[-1][3]):
            chuoi.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chuoi.append(cur)
    cau = []
    for c in chuoi:
        n = len(c)
        if n <= toi_da + 1:
            cau.append(c)
            continue
        k = -(-n // 5)  # số câu, mỗi câu ~4–5 từ
        b = [round(i * n / k) for i in range(k + 1)]
        cau += [c[b[i]:b[i + 1]] for i in range(k) if b[i + 1] > b[i]]
    return cau


def nghe_phu_de(viec_p):
    """Lệnh "nghe": viec = {"canh": [{"id", "file", "src", "tu", "den"}], "kho": thư mục cache}. In BUOC= / XONG= / LOI=."""
    viec = doc(viec_p, {}, chac=True)
    md = chung.mo_hinh_hoac_none() if hasattr(chung, "mo_hinh_hoac_none") else chung.MO_HINH
    if not md or not os.path.isdir(md):
        in_("LOI=Chưa có máy nghe tiếng Việt (mô hình sherpa) trong bộ dựng: bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video")
        return
    try:
        import nghe as NG
        with contextlib.redirect_stdout(sys.stderr):
            try:   # 4/11: từ điển của tiệm (engine/tu_dien.py + tu-dien-tiem.txt): ưu tiên từ hay nói, sửa số / giá / tên máy
                import tu_dien as TD
                td = TD.doc()
                rec, khoa = TD.recognizer(md, td, kho=os.path.join(viec["kho"], "tu-dien"))
            except ImportError:   # bộ dựng chưa có tu_dien.py: nghe như trước
                TD, td, khoa = None, None, "greedy"
                rec = NG.recognizer(md)
    except Exception as e:  # noqa
        in_("LOI=Không mở được máy nghe: %s" % e)
        return
    kho = viec["kho"]
    os.makedirs(kho, exist_ok=True)
    canh = viec.get("canh") or []
    src_ds = []
    for c in canh:
        if c.get("src") and c["src"] not in src_ds:
            src_ds.append(c["src"])
    nghe = {}
    for i, s in enumerate(src_ds):
        in_("BUOC=Nghe lời nói clip %d/%d (%s)" % (i + 1, len(src_ds), os.path.basename(s)))
        try:
            nghe[s] = _nghe_clip(rec, s, kho, khoa, getattr(TD, "bo_im_dau", None) if TD else None)
            if TD:
                try:
                    nghe[s] = dict(nghe[s], tu=TD.sua_tu(nghe[s].get("tu") or [], td))
                except Exception:  # noqa  từ điển lỗi: dùng lời nghe thô
                    traceback.print_exc()
        except Exception as e:  # noqa
            traceback.print_exc()
            nghe[s] = {"tu": []}
            in_("CANH_BAO=" + json.dumps(["Không nghe được %s: %s" % (os.path.basename(s), str(e)[:120])], ensure_ascii=False))
    pd, so_tu = [], 0
    for c in canh:
        tu, den = float(c["tu"]), float(c["den"])
        ds = [w for w in (nghe.get(c.get("src")) or {}).get("tu") or [] if tu - 0.02 <= (w[1] + w[2]) / 2 <= den + 0.02]
        # 4/11: tu_dien.chia_cau không tách tên máy / game / từ ghép sang 2 câu ("Liên Quân Tốc | Chiến"); bộ dựng cũ: chia như trước
        for cau in (TD.chia_cau(ds, td) if TD and hasattr(TD, "chia_cau") else _chia_cau(ds)):
            so_tu += len(cau)
            s0, s1 = max(tu, cau[0][1]), min(den, cau[-1][2])
            if s1 - s0 < 0.2:
                continue
            pd.append({"_k": "p" + ma(), "chu": " ".join(w[0] for w in cau), "t0": round(s0, 3), "t1": round(s1, 3),
                       "_neo": dict({"id": c.get("id"), "file": c["file"], "s0": round(s0, 3), "s1": round(s1, 3), "cau": True,
                                     "tu": [[w[0], round(w[1], 3), round(w[2], 3)] for w in cau]},
                                    **({"am": True} if c.get("am") else {}))})   # đoạn của khối tiếng tách (4/11): câu theo khối
    in_("XONG=" + json.dumps({"phu_de": pd, "so_cau": len(pd), "so_tu": so_tu, "so_clip": len(src_ds)}, ensure_ascii=False))


# ------------------------------------------------------------------ ảnh cảnh cho "Nhờ Claude"
def _khung(src, t, out):
    """1 khung (cao 240) của clip ở giây t; có rồi thì dùng lại."""
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    tam = out + ".%d.jpg" % os.getpid()
    for ss in (["-ss", "%.2f" % max(0.0, t)], []):
        subprocess.run([chung.FFMPEG, "-v", "error", "-y"] + ss + ["-i", src, "-frames:v", "1", "-vf", "scale=-2:240", "-q:v", "6", tam],
                       capture_output=True, timeout=60, **({"creationflags": 0x08000000} if os.name == "nt" else {}))
        if os.path.isfile(tam) and os.path.getsize(tam) > 0:
            os.replace(tam, out)
            return out
    return None


def anh_canh(viec_p):
    """Ghép ảnh các cảnh thành trang canh-01.jpg, canh-02.jpg… (6 cảnh / trang, mỗi hàng: nhãn + khung đầu / giữa / cuối).
    viec = {"ra": thư mục, "kho": thư mục cache khung, "canh": [{"so", "id", "src", "tu", "den", "nhan"}]}. In ra danh sách trang."""
    from concurrent.futures import ThreadPoolExecutor
    from PIL import Image, ImageDraw, ImageFont
    viec = doc(viec_p, {}, chac=True)
    ra, kho, ds = viec["ra"], viec["kho"], viec.get("canh") or []
    os.makedirs(ra, exist_ok=True)
    os.makedirs(kho, exist_ok=True)

    def lay(c):
        tu, den = float(c["tu"]), float(c["den"])
        moc_t = [tu + min(0.15, (den - tu) / 4), (tu + den) / 2, den - min(0.15, (den - tu) / 4)]
        try:
            st = os.stat(c["src"])
            goc = "%s|%s|%s" % (c["src"], st.st_size, int(st.st_mtime))
        except OSError:
            goc = c["src"]
        out = []
        for t in moc_t:
            k = hashlib.md5(("%s|%.2f" % (goc, t)).encode("utf-8")).hexdigest()[:20]
            out.append(_khung(c["src"], t, os.path.join(kho, k + ".jpg")))
        return out
    with ThreadPoolExecutor(max_workers=4) as tp:
        khung = list(tp.map(lay, ds))
    try:
        f1 = ImageFont.truetype(os.path.join(chung.FONT_DIR, "BeVietnamPro-Bold.ttf"), 22)
        f2 = ImageFont.truetype(os.path.join(chung.FONT_DIR, "BeVietnamPro-Bold.ttf"), 17)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    H, NHAN, O = 240, 250, 150   # cao hàng, rộng cột nhãn, rộng ô khung
    trang = []
    for n0 in range(0, len(ds), 6):
        nhom = list(zip(ds[n0:n0 + 6], khung[n0:n0 + 6]))
        im = Image.new("RGB", (NHAN + 3 * (O + 6) + 6, len(nhom) * (H + 10) + 10), (24, 24, 24))
        d = ImageDraw.Draw(im)
        for i, (c, ks) in enumerate(nhom):
            y = 10 + i * (H + 10)
            d.text((12, y + 8), "CẢNH %s" % c["so"], font=f1, fill=(255, 214, 0))
            for j, dong in enumerate(str(c.get("nhan") or "").split("\n")[:7]):
                d.text((12, y + 44 + j * 26), dong[:24], font=f2, fill=(230, 230, 230))
            for j, k in enumerate(ks):
                x = NHAN + j * (O + 6)
                if k:
                    try:
                        t = Image.open(k).convert("RGB")
                        t.thumbnail((O, H))
                        im.paste(t, (x + (O - t.width) // 2, y + (H - t.height) // 2))
                    except OSError:
                        pass
                d.text((x + 4, y + H - 22), ("đầu", "giữa", "cuối")[j], font=f2, fill=(255, 255, 255))
        out = os.path.join(ra, "canh-%02d.jpg" % (n0 // 6 + 1))
        im.save(out, quality=82)
        trang.append(out)
    print(json.dumps({"trang": [xuoi(x) for x in trang]}, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "phuc-vu":
        phuc_vu()
    elif len(sys.argv) >= 3 and sys.argv[1] == "anh-canh":
        anh_canh(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "nghe":
        try:
            nghe_phu_de(sys.argv[2])
        except Exception as e:  # noqa
            traceback.print_exc()
            in_("LOI=" + ("%s" % e)[:400])
    elif len(sys.argv) >= 3 and sys.argv[1] == "xuat":
        try:
            xuat(sys.argv[2])
        except SystemExit:
            raise
        except Exception as e:  # noqa
            traceback.print_exc()
            in_("LOI=" + ("%s" % e)[:400])
            sys.exit(1)
    else:
        raise SystemExit(__doc__)
