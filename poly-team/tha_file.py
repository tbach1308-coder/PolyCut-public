# -*- coding: utf-8 -*-
"""POLY Cut — thả clip từ máy (File Explorer) vào Sửa tay (r34, 11/11/2026; anh: "kéo thả clip vào time line",
chọn "Từ thư mục máy tính (Windows)").

Chrome không cho trang biết đường dẫn thật của file thả vào, nên trang gửi NỘI DUNG file lên máy chủ (cùng máy, 127.0.0.1) và máy
chủ lưu thành file trên ổ:
- Nơi lưu: <thư mục video>/clip-tha/ (trong thư mục ra, KHÔNG ghi vào thư mục clip gốc của anh). Thư mục ra vốn được phép đọc
  (allowed_path) nên clip lưu xong là dùng như clip thường: /them-clip (đo clip), bản xem nhẹ, ảnh khung, card đồ hoạ.
- Trước khi gửi, trang hỏi (POST /api/sua-tay/tha-file/hoi): file cùng tên + cùng cỡ (+ cùng giờ sửa ±2 s nếu trình duyệt cho)
  đã có trong thư mục clip Thư viện đang mở / thư mục clip của video / clip-tha thì DÙNG LẠI file đó, không gửi lại (anh hay kéo
  từ đúng thư mục clip đang mở). Trùng tên khác cỡ thì lưu thêm hậu tố "-2", "-3"…
- Nhận (POST /api/sua-tay/tha-file/nhan?v=&ten=&co=&luc=&ma=, thân = nội dung file, gọi từ server.do_POST TRƯỚC khi đọc JSON):
  kiểm Content-Length = co, đuôi (.mov .mp4 .m4v .mkv; ảnh / nhạc báo "chưa nhận ảnh / nhạc ở đây"), tên làm sạch (không "..",
  không ký tự cấm Windows, giữ chữ Việt), ổ còn đủ chỗ; ghi THẲNG xuống đĩa từng khúc 1 MB vào file tạm ".tha-<mã>.part" (không đọc
  cả file vào bộ nhớ: máy tiệm 8 GB, clip iPhone 4K 100 MB–2 GB+), đủ thì đặt giờ sửa = giờ file gốc rồi đổi tên. Lỗi / huỷ / mất
  kết nối / 60 s không có dữ liệu: xoá file dở. Huỷ: trang ngắt XHR + POST /tha-file/huy {ma}.
- GET /api/sua-tay/tha-file?v= -> {thu_muc, so}: thư mục clip-tha của video + số clip trong đó (Thư viện hiện chip "Clip đã thả").
Chỉ thư viện chuẩn.
"""
import errno
import os
import re
import shutil
import threading
import time
import unicodedata
import uuid
from urllib.parse import parse_qs

import sua_tay as ST

DUOI = (".mov", ".mp4", ".m4v", ".mkv")
ANH = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tif", ".tiff")
NHAC = (".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".wma", ".opus")
THU_MUC = "clip-tha"
KHUC = 1 << 20                 # ghi từng khúc 1 MB
CHUA = 256 * 1024 * 1024       # chừa lại trên ổ sau khi nhận (bản xem nhẹ, bản xuất…)
TOI_DA = 64 * 1024 ** 3        # 64 GB / file
CHO_DU_LIEU = 60               # giây không nhận được byte nào thì bỏ
CAM = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')
TEN_CAM = {"CON", "PRN", "AUX", "NUL", *("COM%d" % i for i in range(1, 10)), *("LPT%d" % i for i in range(1, 10))}
KHOA = threading.Lock()
DANG = {}                      # mã -> {"huy": bool, "nhan": byte, "co": byte, "p": file tạm}


class Huy(Exception):
    pass


def _S():
    return ST.S


def thu_muc(v):
    return os.path.join(v, THU_MUC)


def loai_sai(ten):
    """Lý do không nhận (đuôi) hoặc None."""
    e = os.path.splitext(str(ten or ""))[1].lower()
    if e in DUOI:
        return None
    if e in ANH:
        return "Chưa nhận ảnh ở đây (chỉ clip .mov .mp4 .m4v .mkv)"
    if e in NHAC:
        return "Chưa nhận nhạc ở đây (nhạc nền: tab Nhạc)"
    return "Không phải clip video (chỉ nhận .mov .mp4 .m4v .mkv)"


def lam_sach(ten):
    """Tên file an toàn trên Windows, giữ chữ Việt (NFC) + dấu cách: bỏ phần thư mục, ký tự cấm, '..', tên dành riêng (CON, NUL…)."""
    t = unicodedata.normalize("NFC", str(ten or "")).replace("\\", "/").split("/")[-1]
    t = CAM.sub("_", t).strip()
    goc, duoi = os.path.splitext(t)
    duoi = CAM.sub("", duoi)[:10]
    goc = re.sub(r"\.{2,}", ".", goc).strip(" .")
    goc = goc.lstrip("_").strip(" .") or "clip"          # tên bắt đầu "." / "_" thì Thư viện ẩn (list_clips) -> bỏ
    if goc.split(".")[0].upper() in TEN_CAM:
        goc = "clip " + goc
    goc = goc[:120].rstrip(" .") or "clip"
    return goc + duoi


def _mtime_khop(st, luc):
    return luc is None or abs(st.st_mtime - luc) <= 2.0


def _so(x, kieu=int):
    try:
        return kieu(x)
    except (TypeError, ValueError):
        return None


def _luc(x):
    """Giờ sửa file trình duyệt gửi (ms từ 1970) -> giây, hoặc None."""
    v = _so(x, float)
    if v is None or v <= 0:
        return None
    v = v / 1000.0 if v > 1e11 else v
    return v if 3e8 < v < 5e9 else None


def _cung_ten(d, ten):
    """File trong d trùng tên (không phân biệt hoa thường, như Windows) -> đường dẫn | None."""
    try:
        ds = os.listdir(d)
    except OSError:
        return None
    tl = unicodedata.normalize("NFC", ten).lower()
    for fn in ds:
        if unicodedata.normalize("NFC", fn).lower() == tl:
            p = os.path.join(d, fn)
            if os.path.isfile(p):
                return p
    return None


def _ho_ten(d, ten):
    """Các file trong clip-tha cùng 'họ' với ten: ten, ten-2, ten-3… (cùng đuôi)."""
    goc, duoi = os.path.splitext(ten)
    m = re.compile(re.escape(unicodedata.normalize("NFC", goc).lower()) + r"(?:-(\d+))?" + re.escape(duoi.lower()) + r"$")
    out = []
    try:
        for fn in os.listdir(d):
            if m.match(unicodedata.normalize("NFC", fn).lower()) and os.path.isfile(os.path.join(d, fn)):
                out.append(os.path.join(d, fn))
    except OSError:
        pass
    return out


def tim_co_san(v, cac_tm, ten, co, luc):
    """File đã có trên ổ (cùng tên + cỡ + giờ sửa) để dùng lại thay vì gửi lại -> đường dẫn | None.
    Xét thư mục clip-tha của video trước, rồi các thư mục clip trang gửi (Thư viện đang mở, thư mục clip của video) — chỉ file app
    vốn được phép đọc (allowed_path video)."""
    d = thu_muc(v)
    for p in _ho_ten(d, lam_sach(ten)):
        st = os.stat(p)
        if st.st_size == co and _mtime_khop(st, luc):
            return p
    S = _S()
    for tm in cac_tm[:8]:
        if not isinstance(tm, str) or not tm.strip():
            continue
        tm = tm.strip().strip('"')
        if not os.path.isdir(tm):
            continue
        p = _cung_ten(tm, os.path.basename(str(ten).replace("\\", "/")))
        if not p or os.path.splitext(p)[1].lower() not in DUOI or not S.allowed_path(p, video=True):
            continue
        st = os.stat(p)
        if st.st_size == co and _mtime_khop(st, luc):
            return p
    return None


def _don_tam(d):
    """File tạm bỏ dở (app tắt giữa chừng) quá 1 giờ, không còn ai đang ghi: xoá."""
    try:
        ds = os.listdir(d)
    except OSError:
        return
    dang = {os.path.normcase(x.get("p") or "") for x in list(DANG.values())}
    for fn in ds:
        if fn.startswith(".tha-") and fn.endswith(".part"):
            p = os.path.join(d, fn)
            try:
                if os.path.normcase(p) not in dang and time.time() - os.path.getmtime(p) > 3600:
                    os.remove(p)
            except OSError:
                pass


def _gb(b):
    return ("%.1f" % (b / 1024 ** 3)).replace(".", ",") + " GB"


def _o_trong(d):
    x = d
    while x and not os.path.isdir(x):
        x2 = os.path.dirname(x)
        if x2 == x:
            break
        x = x2
    try:
        return shutil.disk_usage(x).free
    except OSError:
        return None


def info(v):
    v = ST.thu_muc_video(v)
    d = thu_muc(v)
    so = 0
    if os.path.isdir(d):
        so = sum(1 for fn in os.listdir(d) if os.path.splitext(fn)[1].lower() in DUOI and not fn.startswith((".", "_"))
                 and os.path.isfile(os.path.join(d, fn)))
    return {"thu_muc": d, "so": so}


def hoi(data):
    """Trang hỏi trước khi gửi: file nào đã có sẵn (dùng lại), file nào sai loại, ổ có đủ chỗ."""
    v = ST.thu_muc_video(data.get("v"))
    d = thu_muc(v)
    _don_tam(d)
    cac_tm = data.get("tm") if isinstance(data.get("tm"), list) else []
    ds = data.get("ds") if isinstance(data.get("ds"), list) else []
    trong = _o_trong(d)
    can = 0
    out = []
    for x in ds[:60]:
        x = x if isinstance(x, dict) else {}
        ten = str(x.get("ten") or "")[:300]
        co = _so(x.get("co"))
        r = {"ten": ten, "co_san": None, "loi": None, "ten_luu": lam_sach(ten)}
        r["loi"] = loai_sai(ten) or ("File rỗng" if not co or co <= 0 else "File quá lớn" if co > TOI_DA else None)
        if not r["loi"]:
            r["co_san"] = tim_co_san(v, cac_tm, ten, co, _luc(x.get("luc")))
            if not r["co_san"]:
                can += co
                if trong is not None and can + CHUA > trong:
                    r["loi"] = "Ổ đĩa không đủ chỗ: còn %s, cần thêm %s" % (_gb(trong), _gb(can + CHUA - trong))
                    can -= co
        out.append(r)
    return {"thu_muc": d, "ds": out}


def huy(data):
    x = DANG.get(str(data.get("ma") or ""))
    if x:
        x["huy"] = True
    return {"ok": bool(x)}


def _dat_ten(d, ten, co, luc):
    """Tên cuối trong clip-tha (gọi trong KHOA): đã có file cùng họ + cùng cỡ (+ giờ) -> (p, True: dùng lại);
    trùng tên khác cỡ -> thêm hậu tố."""
    for p in _ho_ten(d, ten):
        st = os.stat(p)
        if st.st_size == co and _mtime_khop(st, luc):
            return p, True
    goc, duoi = os.path.splitext(ten)
    p, i = os.path.join(d, ten), 2
    while os.path.exists(p) or _cung_ten(d, os.path.basename(p)):
        p, i = os.path.join(d, "%s-%d%s" % (goc, i, duoi)), i + 1
    return p, False


def nhan(h, u):
    """POST thân = nội dung file. Gọi từ server.do_POST trước self.body() (không đọc JSON). Trả True (đã trả lời)."""
    q = parse_qs(u.query)
    g = lambda k: (q.get(k) or [""])[0]
    tam = None
    ma = g("ma")
    try:
        n = _so(h.headers.get("Content-Length"))
        v = ST.thu_muc_video(g("v"))
        ten_goc = g("ten")
        loi = loai_sai(ten_goc)
        if loi:
            raise ValueError(loi)
        co = _so(g("co"))
        if n is None or n < 0:
            raise ValueError("Thiếu cỡ file (Content-Length)")
        if co is None or co != n:
            raise ValueError("Cỡ file gửi lên không khớp")
        if co <= 0:
            raise ValueError("File rỗng")
        if co > TOI_DA:
            raise ValueError("File quá lớn")
        if not re.fullmatch(r"[a-z0-9]{6,32}", ma or ""):
            ma = uuid.uuid4().hex[:16]
        ten = lam_sach(ten_goc)
        luc = _luc(g("luc"))
        d = thu_muc(v)
        os.makedirs(d, exist_ok=True)
        trong = _o_trong(d)
        if trong is not None and co + CHUA > trong:
            raise ValueError("Ổ đĩa không đủ chỗ: còn %s, file cần %s" % (_gb(trong), _gb(co + CHUA)))
        tam = os.path.join(d, ".tha-%s.part" % ma)
        tt = DANG[ma] = {"huy": False, "nhan": 0, "co": co, "p": tam}
        try:
            h.connection.settimeout(CHO_DU_LIEU)
        except Exception:
            pass
        with open(tam, "wb") as f:
            con = co
            while con > 0:
                if tt["huy"]:
                    raise Huy()
                b = h.rfile.read(min(KHUC, con))
                if not b:
                    raise ValueError("Mất kết nối giữa chừng (nhận %d / %d MB)" % (tt["nhan"] >> 20, co >> 20))
                f.write(b)
                con -= len(b)
                tt["nhan"] += len(b)
        if tt["huy"]:
            raise Huy()
        if luc:
            try:
                os.utime(tam, (luc, luc))
            except OSError:
                pass
        with KHOA:
            p, dung_lai = _dat_ten(d, ten, co, luc)
            if dung_lai:
                os.remove(tam)
            else:
                os.replace(tam, p)
            tam = None
        _S().log("tha-file: %s %s (%d MB)" % ("dùng lại" if dung_lai else "nhận", p, co >> 20))
        h.send(200, {"p": p, "ten": os.path.basename(p), "dung_lai": dung_lai, "thu_muc": d})
    except Huy:
        h.close_connection = True
        h.send(409, {"err": "Đã huỷ", "huy": True})
    except ValueError as e:
        h.close_connection = True   # chưa đọc hết thân: không dùng lại kết nối này
        h.send(400, {"err": str(e)})
    except OSError as e:   # mất kết nối, hết giờ chờ (socket.timeout), ổ đầy giữa chừng…
        h.close_connection = True
        ly_do = ("quá %d giây không nhận được dữ liệu" % CHO_DU_LIEU if isinstance(e, TimeoutError)
                 else "ổ đĩa đầy" if e.errno == errno.ENOSPC else "mất kết nối giữa chừng" if isinstance(e, ConnectionError)
                 else (e.strerror or e.__class__.__name__))
        h.send(400, {"err": "Không nhận được file: " + ly_do})
    finally:
        DANG.pop(ma, None)
        if tam:
            try:
                os.remove(tam)
            except OSError:
                pass
        try:
            h.connection.settimeout(None)
        except Exception:
            pass
    return True


def get(h, u, q):
    if u.path == "/api/sua-tay/tha-file":
        h.send(200, info((q.get("v") or [""])[0]))
        return True
    return False


def post(h, u, data):
    a = u.path[len("/api/sua-tay/tha-file/"):] if u.path.startswith("/api/sua-tay/tha-file/") else None
    if a == "hoi":
        r = hoi(data)
    elif a == "huy":
        r = huy(data)
    else:
        return False
    h.send(200, r)
    return True
