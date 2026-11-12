# -*- coding: utf-8 -*-
"""DỰNG THÔ TỪ CLIP NÓI (POLY Cut, 5/11/2026; anh duyệt ý "Dựng thô từ clip nói").

Clip cầm máy nói về máy (15–60s, hay vấp, nói lại câu) -> 1 video Sửa tay của POLY Cut (lam/ke-hoach.json, _tao_boi "sua_tay")
để anh mở trong app chỉnh tiếp. Không đổi file nào của app / bộ dựng: chỉ GỌI lại hàm có sẵn
(sua_tay_may._nghe_clip + tu_dien = máy nghe của "Tạo phụ đề từ lời nói", sua_tay_may.lenh_moi = "Video mới từ clip",
gan_neo / ap_neo / sach = cách trang Sửa tay lưu kế hoạch, sua_tay_may.py xuat = Xuất bản nháp).

Chạy bằng Python của BỘ DỰNG (engine/.venv có numpy, sherpa-onnx 2.0.1, Pillow), như sua_tay_may.py:
  python dung_tho.py --clip <clip>... --ra <thư mục ra> --ten <tên>
                     [--doi-duong "<thư mục trên máy này>=E:\\...\\<thư mục trên máy tiệm>"]...   (đổi đường dẫn trong kế hoạch)
                     [--nhap] [--kiem] [--mo-ta mo-ta.json] [--bo CLIP:giây-giây]... [--giu CLIP:giây-giây]...
                     [--zoom phong_sat|zoom_vao|...|khong] [--ghi-de] [--engine <engine>] [--mo-hinh <thư mục mô hình>] [--kho <cache>]
                     [--bo-kieu <mã | file.json> [--kho-effect <thư mục kho effect>]]   (DỰNG TỰ ĐỘNG r38: tự gắn hook, thẻ giá,
                     nhãn, chuyển cảnh, nhạc theo bộ kiểu — tu_dung_gan.py; không có --bo-kieu = dựng thô y như trước)
Ra <ra>/<slug>/:
  lam/ke-hoach.json        kế hoạch Sửa tay (mở được trong POLY Cut); đường clip đổi sang máy tiệm khi có --doi-duong
  lam/dung-tho.json        số đo, lời nghe từng clip, danh sách cắt + lý do, câu nói lại, zoom, gợi ý chèn, kết quả kiểm
  lam/dung-tho/khung/      ảnh khung mỗi clip (6 khung, có giờ) để Claude xem rồi viết mo-ta.json (gợi ý cảnh chèn)
  BAO-CAO.md               báo cáo ngắn tiếng Việt cho chủ tiệm
  nhap-dung-tho.mp4        (--nhap) bản nháp 540x960 dựng bằng bộ dựng ffmpeg (như nút Xuất bản nháp)
--kiem (cần --nhap): nghe lại bản nháp, so với lời gốc (mất chữ, cụt chữ ở chỗ cắt), dò khoảng im > 0,5s, tiếng bụp ở chỗ nối.

Cách cắt (mọi giờ là giờ CLIP GỐC):
 1. Năng lượng tiếng mỗi 10 ms -> vùng có tiếng. Chữ máy nghe ra mà chỗ đó im = nghe nhầm (bỏ). Vùng có lời cách nhau
    <= NGHI_GIU giữ liền (nghỉ tự nhiên); xa hơn = khoảng chết, cắt, mỗi đoạn chừa lề LE_TRUOC trước / LE_SAU sau (không
    lấn sang vùng tiếng bị bỏ). Đoạn quá ngắn bỏ. Chỗ cắt luôn ở khung im (không cắt giữa chữ); bộ dựng tự fade 30/50 ms.
 2. Vùng chỉ có "ừ / à / ờ / ơ…" (hoặc từ đệm "thì / mà / kiểu…" đứng riêng, có nghỉ 2 bên) -> bỏ. Lặp chữ liền ("nó nó")
    / nói lại liền không nghỉ ("với thiết kế với thiết kế chiếc…") -> bỏ lần đầu nếu có chỗ ngắt tiếng rõ.
 3. Câu nói lại (đoạn sau lặp lại phần lớn đoạn trước, cùng cách mở đầu, gần nhau hoặc clip kế tiếp) -> giữ lần tốt nhất
    (đủ câu, ít vấp; bằng nhau thì lần sau cùng), bỏ lần hỏng, ghi lý do.
 4. Zoom nhấn: câu có giá / pin % / GB / inch / tên máy (từ điển tiệm) -> tách câu đó thành cảnh nối liền (noi_lien) đặt
    chuyển động riêng cảnh "phong_sat" (Phóng sát, giá trị có sẵn trong menu Hiệu ứng của Sửa tay).
 5. Gợi ý cảnh chèn: CHỈ ghi trong báo cáo (không chèn) — khớp lời với mô tả clip (mo-ta.json Claude viết sau khi xem khung).
 6. Phụ đề: lời đã nghe (sửa theo từ điển tiệm), IN HOA, neo theo cảnh như "Tạo phụ đề từ lời nói" -> giờ khớp các đoạn đã cắt.
 7. Kiểu cả video: y như "Video mới từ clip" (MẶC ĐỊNH TRƠN, sua_tay_may.lenh_moi / TRON / kieu_tron), không thêm hiệu ứng.
"""
import argparse
import contextlib
import copy
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import uuid

APP = os.path.dirname(os.path.abspath(__file__))
IS_WIN = os.name == "nt"
KW = {"creationflags": 0x08000000} if IS_WIN else {}
PHIEN_BAN = 1

# ------------------------------------------------------------------ tham số (giây)
KHUNG = 0.01          # năng lượng tiếng tính mỗi 10 ms
NOI_VUNG = 0.12       # khung có tiếng cách nhau < chừng này = cùng 1 vùng
VUNG_MIN = 0.05       # vùng có tiếng ngắn hơn chừng này: bỏ qua (tiếng lách cách)
NGHI_GIU = 0.42       # nghỉ giữa 2 vùng có lời <= chừng này: giữ nguyên (nghỉ tự nhiên, không cắt)
LE_TRUOC = 0.12       # lề trước mỗi đoạn nói (không cụt đầu chữ)
LE_SAU = 0.18         # lề sau mỗi đoạn nói (không cụt cuối chữ)
CACH_VUNG_BO = 0.03   # lề không lấn sang vùng tiếng bị bỏ (ừ / à, câu hỏng) gần hơn chừng này
LO_NHO = 0.06         # lỗ hổng < chừng này giữa 2 phần giữ: lấp lại
DOAN_MIN = 0.40       # đoạn giữ ngắn hơn chừng này: bỏ
DOAN_1_TU = 0.60      # đoạn chỉ 1 chữ ngắn hơn chừng này: bỏ
KHONG_LOI_DAI = 1.2   # vùng có tiếng mà không có lời dài từ chừng này = nhạc / tiếng loa / tiếng máy
DUOI_THUA = 0.8       # vùng có lời mà tiếng kéo dài quá chữ cuối chừng này (nhạc nối sau lời): tách phần đuôi
THU_LOA_GIU = 4.0     # thử loa ngay sau câu nói về loa / âm thanh: giữ tối đa chừng này
CACH_THU_LOA = 2.0
GAN_NOI_LAI = 20.0    # câu nói lại: cách câu trước tối đa chừng này (cùng clip)
GAN_NOI_LAI_CLIP = 25.0   # ... hoặc ở clip kế tiếp (cuối clip trước + đầu clip sau)
NGUNG_VAP = 0.8       # ngừng giữa câu lâu hơn chừng này = 1 lần vấp
ZOOM_CACH = 2.5       # 2 chỗ zoom nhấn cách nhau ít nhất chừng này (giây trên video)
ZOOM_PHAN_MIN = 0.5   # phần cảnh trước / sau câu zoom ngắn hơn chừng này thì gộp vào câu zoom
DONG_NHAN = "phong_sat"   # chuyển động riêng cảnh có sẵn (ke_hoach.DONG_CANH, menu Hiệu ứng › Chuyển động của Sửa tay)

TIENG_DEM = {"ừ", "ờ", "ừm", "ờm", "ưm", "hừm", "hửm", "ơ", "à", "ầm", "ừa", "ậm", "hmm", "um", "uh", "ah", "ơi"}
TU_DEM = {"thì", "mà", "là", "kiểu", "kiểu như", "nói chung", "nói chung là", "thì là", "kiểu kiểu", "à thì", "ờ thì"}
LAP_DUOC = {"rất", "lắm", "quá", "nhiều", "từng", "đi", "thật", "mãi", "nhanh", "chậm", "xa", "gần", "cao", "to", "nhỏ"}
STOP = {"là", "thì", "của", "này", "mình", "có", "cho", "như", "và", "với", "đó", "cái", "một", "những", "các", "rất", "nó",
        "mà", "để", "sẽ", "đây", "ha", "nha", "luôn", "rồi", "ạ", "á", "nè", "thể", "được", "hết", "đều", "ra", "vô", "vào",
        "giống", "thấy", "nhé", "nhá", "anh", "em", "chị", "bạn", "ở", "trong", "trên", "lại", "cũng", "đã", "đang", "thế",
        "vậy", "nhìn", "chiếc", "con", "kia", "ấy", "mấy", "khi", "nên", "nếu", "về", "từ", "tới", "đến", "bị", "theo"}
LOA_TU = ("loa", "am thanh", "nghe", "nhac", "bass", "tieng", "am luong")
SAN_PHAM = re.compile(r"(?i)\b(ipad|iphone|macbook|imac|mac mini|apple pencil|magic keyboard|airpods|apple watch|galaxy)\b")


# ------------------------------------------------------------------ tiện ích chung (không cần bộ dựng)
def bo_dau(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def slugify(s):
    """Như server.slugify (tên thư mục video của app)."""
    s = re.sub(r"[^a-z0-9]+", "-", bo_dau(s).lower()).strip("-")
    return s[:48].strip("-")


def chuan(w):
    """Chữ để so câu nói lại: chữ thường, bỏ dấu câu, GIỮ dấu thanh (bỏ dấu thì "máy" = "mấy", "còn" = "con": lẫn với chữ đệm)."""
    return re.sub(r"[^\w%.]", "", unicodedata.normalize("NFC", str(w or "")).lower())


def xuoi(p):
    return str(p).replace("\\", "/")


def gio(t):
    """Giây -> "0:45" (hoặc "1:02")."""
    t = max(0.0, float(t))
    return "%d:%02d" % (int(t // 60), int(round(t % 60)) if round(t % 60) < 60 else 59)


def so(x, n=1):
    """1,5 kiểu Việt."""
    return ("%." + str(n) + "f") % x if n else "%d" % round(x)


def so_vn(x, n=1):
    return so(x, n).replace(".", ",")


def ngan(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def doc_doi_duong(ds):
    """["A=B", ...] -> [(A chuẩn, B)] dài trước. A: thư mục trên máy này; B: thư mục trên máy tiệm (E:\\..., dấu cách, chữ Việt được).
    Tách ở dấu "=" cuối cùng đứng trước 1 đường dẫn (ổ đĩa "X:", "\\\\máy" hoặc "/")."""
    out = []
    for s in ds or []:
        m = re.match(r"^(.*)=([A-Za-z]:[\\/].*|[A-Za-z]:$|\\\\.*|/.*)$", str(s).strip().strip('"'))
        if not m or not m.group(1).strip():
            raise SystemExit('--doi-duong sai dạng: %s (đúng: "<thư mục máy này>=E:\\...\\<thư mục máy tiệm>")' % s)
        a = xuoi(os.path.abspath(m.group(1).strip().strip('"'))).rstrip("/")
        b = m.group(2).strip().strip('"').rstrip("\\/")
        out.append((a, b))
    out.sort(key=lambda x: -len(x[0]))
    return out


def doi_duong(p, bang):
    """Đường dẫn trên máy này -> đường dẫn máy tiệm theo bảng (dạng app ghi: E:/Video/x y/IMG.MOV). Không khớp: giữ nguyên."""
    if not bang or not p:
        return p
    x = xuoi(os.path.abspath(p)) if not re.match(r"^[A-Za-z]:", str(p)) or IS_WIN else xuoi(p)
    so_sanh = (lambda s: s.lower()) if IS_WIN else (lambda s: s)
    for a, b in bang:
        if so_sanh(x) == so_sanh(a) or so_sanh(x).startswith(so_sanh(a) + "/"):
            con = x[len(a):].lstrip("/")
            return xuoi(b) + ("/" + con if con else "")
    return p


def lcs(a, b):
    """Dãy con chung dài nhất -> (độ dài, [(i, j)])."""
    n, m = len(a), len(b)
    L = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if a[i] == b[j] else max(L[i + 1][j], L[i][j + 1])
    cap, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            cap.append((i, j))
            i, j = i + 1, j + 1
        elif L[i + 1][j] >= L[i][j + 1]:
            i += 1
        else:
            j += 1
    return L[0][0], cap


# ------------------------------------------------------------------ nhận ra câu nói lại (thuần, thử được không cần tiếng)
def la_noi_lai(A, B, cach):
    """A = chữ (đã chuẩn) lần trước, B = lần sau, cach = giây giữa 2 lần. -> (có phải nói lại, số chữ trùng, cặp khớp)."""
    if len(A) < 2 or len(B) < 2:
        return False, 0, []
    L, cap = lcs(A, B)
    if not cap or cap[0][0] > 2 or cap[0][1] > 4:   # lần sau mở đầu giống lần trước (cho thêm vài chữ dẫn: "máy này thì …")
        return False, L, cap
    nd = sum(1 for i, _ in cap if A[i] not in STOP_C)
    if len(A) <= 4 and L == len(A) and cap[0] == (0, 0) and cach <= 3.0 and nd >= 1:   # bắt đầu hỏng: "với thiết kế | với thiết kế chiếc…"
        return True, L, cap
    return (L >= 4 and nd >= 3 and L / float(len(A)) >= 0.5), L, cap


STOP_C = {chuan(x) for x in STOP}


def chon_lan(A, B):
    """A, B: {"n": số chữ, "ngung": số lần ngừng > NGUNG_VAP, "dem": tiếng đệm, "lap": lặp chữ / nói lại liền}.
    -> ("B" | "A", lý do). Mặc định giữ lần sau (thường là lần tốt nhất); lần sau thiếu câu hoặc vấp hơn rõ thì giữ lần trước."""
    vA, vB = A["ngung"] + A["dem"] + A["lap"], B["ngung"] + B["dem"] + B["lap"]
    nmax = max(A["n"], B["n"], 1)
    duA, duB = A["n"] >= 0.6 * nmax, B["n"] >= 0.6 * nmax
    if duB and vB <= vA + 1:
        return "B", "đủ câu, %s, là lần sau cùng" % ("ít vấp hơn" if vB < vA else "không vấp hơn" if vB == vA else "vấp ngang nhau")
    if duA and not duB:
        return "A", "lần sau chưa hết câu (%d chữ so với %d)" % (B["n"], A["n"])
    if vA < vB:
        return "A", "lần trước ít vấp hơn rõ (%d so với %d chỗ vấp)" % (vA, vB)
    return "B", "đủ câu, là lần sau cùng"


def tim_noi_lai(doan, gan):
    """doan: [{"chu": [chữ chuẩn], "vap": {...}, ...}] theo thứ tự video; gan(i, j, toi_da=None) -> giây từ cuối đoạn i tới đầu
    đoạn j hoặc None (xa quá). -> [{"A": [i..], "B": [j..], "giu": "A"|"B", "ly_do", "trung"}]. Đoạn đã bỏ không xét lại."""
    out, bo = [], set()
    j = 1
    while j < len(doan):
        tot = None
        cach = gan(j - 1, j)
        for i in range(j - 1, max(-1, j - 6), -1):
            if cach is None or i in bo or doan[i].get("clip") != doan[j - 1].get("clip"):
                break
            if gan(i, j, 1.75) is None:   # lần trước bắt đầu xa quá
                break
            A = [w for x in range(i, j) for w in doan[x]["chu"]]
            for k in range(j, min(len(doan), j + 5)):
                if doan[k].get("clip") != doan[j].get("clip"):
                    break
                B = [w for x in range(j, k + 1) for w in doan[x]["chu"]]
                ok, L, cap = la_noi_lai(A, B, cach)
                if ok and (tot is None or L > tot["trung"] or (L == tot["trung"] and k - j < tot["k"] - j)):
                    tot = {"i": i, "k": k, "trung": L, "cap": cap, "nA": len(A), "nB": len(B)}
        if not tot:
            j += 1
            continue
        Ai, Bi = list(range(tot["i"], j)), list(range(j, tot["k"] + 1))

        def vap(ids):
            v = {"n": 0, "ngung": 0, "dem": 0, "lap": 0}
            for x in ids:
                for kk in ("n", "ngung", "dem", "lap"):
                    v[kk] += doan[x]["vap"].get(kk, 0)
            v["ngung"] += sum(1 for a, b in zip(ids, ids[1:]) if (gan(a, b) or 0) > NGUNG_VAP)
            return v
        giu, ly = chon_lan(vap(Ai), vap(Bi))
        out.append({"A": Ai, "B": Bi, "giu": giu, "ly_do": ly, "trung": tot["trung"], "vapA": vap(Ai), "vapB": vap(Bi)})
        bo.update(Ai if giu == "B" else Bi)
        j = tot["k"] + 1
    return out


# ------------------------------------------------------------------ từ khoá zoom nhấn (thuần)
def tu_khoa_cau(chu_ds, ten_may):
    """chu_ds = chữ của 1 câu (đã sửa theo từ điển: 13TR9, 98%, 64GB, 12.9, inch, iPad Pro). ten_may = [tên máy của từ điển].
    -> [(loại, chữ, ưu tiên)]: gia 3, pin 3, gb 2, inch 2, ten_may 1."""
    out = []
    low = [str(w).lower() for w in chu_ds]
    for i, w in enumerate(chu_ds):
        lw = low[i]
        if re.fullmatch(r"\d+tr\d*", lw) or re.fullmatch(r"\d+k", lw) or (lw in ("triệu", "tr", "củ") and i and re.match(r"^\d", low[i - 1])):
            out.append(("gia", w if lw not in ("triệu", "tr", "củ") else chu_ds[i - 1] + " " + w, 3))
        elif re.fullmatch(r"\d+([.,]\d+)?%", lw):
            out.append(("pin", w, 3))
        elif re.fullmatch(r"\d+(gb|tb)", lw) or (lw in ("gb", "tb") and i and re.match(r"^\d+$", low[i - 1])):
            out.append(("gb", w, 2))
        elif lw == "inch" or (re.fullmatch(r"\d{1,2}[.,]\d", lw) and 7 <= float(lw.replace(",", ".")) < 18
                              and not (i + 1 < len(low) and low[i + 1] == "inch")):
            out.append(("inch", (chu_ds[i - 1] + " " + w) if lw == "inch" and i and re.match(r"^\d", low[i - 1]) else w, 2))
    cau = " ".join(chu_ds)
    for ten in ten_may:
        if re.search(r"(?i)(?<!\w)" + re.escape(ten) + r"(?!\w)", cau):
            out.append(("ten_may", ten, 1))
    return out


def ten_may_tu_dien(td):
    """Tên máy trong từ điển tiệm: mục "từ hay nói" / chữ đúng của luật sửa có tên sản phẩm (iPad Pro, MacBook Air, Magic
    Keyboard…) và >= 2 chữ (1 chữ "iPad" nói câu nào cũng có, zoom hết thì loạn)."""
    ds = []
    for t in list(td.get("tu") or []) + [b for _, b in td.get("sua") or []]:
        t = " ".join(str(t).split())
        m = SAN_PHAM.search(t)
        if m and len(t.split()) >= 2 and t not in ds:
            ds.append(re.sub(r"(?i)^combo\s+", "", t))
    return sorted(set(ds), key=lambda x: -len(x))


# ------------------------------------------------------------------ nạp bộ dựng
M = CH = TD = NG = KH = np = None


def tim_engine(arg=None):
    for d in (arg, os.environ.get("POLY_ENGINE"), os.path.join(os.path.dirname(APP), "engine"),
              os.path.join(os.path.dirname(APP), "poly-dung-video", "engine")):
        if d and os.path.isfile(os.path.join(d, "ke_hoach.py")):
            return os.path.abspath(d)
    raise SystemExit("Không thấy bộ dựng (thư mục engine có ke_hoach.py): ghi --engine <thư mục engine>")


def tim_mo_hinh(d):
    """Thư mục mô hình sherpa (có tokens.txt + encoder*.onnx), cho cả thư mục cha (mo-hinh/)."""
    if not d:
        return None
    goc = os.path.abspath(d)
    for root, dirs, files in os.walk(goc):
        if "tokens.txt" in files and any(f.startswith("encoder") and f.endswith(".onnx") for f in files):
            return root
        if root[len(goc):].count(os.sep) >= 3:
            dirs[:] = []
    return None


def nap(engine=None, mo_hinh=None):
    global M, CH, TD, NG, KH, np
    E = tim_engine(engine)
    os.environ["POLY_ENGINE"] = E
    if mo_hinh:
        md = tim_mo_hinh(mo_hinh)
        if not md:
            raise SystemExit("Không thấy mô hình máy nghe (tokens.txt + encoder*.onnx) trong %s" % mo_hinh)
        os.environ["POLY_MO_HINH"] = md
    for p in (E, APP):
        if p not in sys.path:
            sys.path.insert(0, p)
    import numpy as _np
    import chung as _ch
    import ke_hoach as _kh
    import nghe as _ng
    import sua_tay_may as _m
    try:
        import tu_dien as _td
    except ImportError:
        _td = None
    M, CH, TD, NG, KH, np = _m, _ch, _td, _ng, _kh, _np
    return E


def in_(s):
    print(s, flush=True)


# ------------------------------------------------------------------ tiếng 1 clip
class Tieng:
    """Tiếng 1 clip: 16 kHz mono (như máy nghe) + năng lượng mỗi 10 ms (dB) + ngưỡng có tiếng tự đo theo clip."""

    def __init__(self, src, tmp):
        self.src, self.co_tieng = src, True
        try:
            with contextlib.redirect_stdout(sys.stderr):
                a, _ = NG.doc_wav(src, tmp)
        except Exception:  # noqa  clip không có tiếng
            a = np.zeros(0, dtype=np.float32)
            self.co_tieng = False
        self.a = a
        self.dur = len(a) / 16000.0
        n = 160
        k = len(a) // n
        if k < 10:
            self.co_tieng = False
            self.db = np.full(max(k, 1), -100.0)
        else:
            p = (a[:k * n].reshape(k, n).astype(np.float64) ** 2).mean(1)
            p = np.convolve(p, np.ones(3) / 3, mode="same")
            self.db = 10 * np.log10(p + 1e-12)
        self.nen = float(np.percentile(self.db, 5))
        self.noi = float(np.percentile(self.db, 95))
        thr = self.nen + 0.45 * (self.noi - self.nen)
        thr = min(thr, -35.0, self.noi - 12.0)
        self.nguong = max(thr, self.nen + 6.0)
        self.co = self.db > self.nguong

    def f(self, t):
        return int(min(max(round(t / KHUNG), 0), len(self.db)))

    def so_khung_co(self, a, b):
        return int(self.co[self.f(a):self.f(b)].sum())

    def vung(self):
        """Các vùng có tiếng [(a, b)] (giây): khung có tiếng cách nhau < NOI_VUNG gộp, ngắn < VUNG_MIN bỏ."""
        c = self.co.astype(np.int8)
        idx = np.flatnonzero(np.diff(np.concatenate([[0], c, [0]])))
        runs = [[int(s), int(e)] for s, e in zip(idx[0::2], idx[1::2])]
        gop = []
        for s, e in runs:
            if gop and s - gop[-1][1] < round(NOI_VUNG / KHUNG):
                gop[-1][1] = e
            else:
                gop.append([s, e])
        return [(s * KHUNG, e * KHUNG) for s, e in gop if (e - s) * KHUNG >= VUNG_MIN]

    def cho_ngat(self, lo, hi, cho_trung=False):
        """Chỗ ngắt tiếng trong [lo, hi]: giữa khoảng im dài nhất (>= 30 ms dưới ngưỡng) -> giây | None.
        cho_trung=True (chỉ chỗ tách cảnh nối liền để zoom, tiếng vẫn liền): không có khoảng im thì lấy chỗ trũng nhỏ nhất nếu thấp
        hơn hẳn tiếng nói quanh đó (>= 18 dB) — chỗ ngắt giữa 2 chữ nói liền. Cắt BỎ tiếng (lặp chữ, nói lại liền) chỉ ở khoảng im
        thật: 5/11 thử "nó nó" cắt ở chỗ trũng -56 dB thì nghe lại mất luôn chữ "thì" đứng trước."""
        i0, i1 = self.f(lo), self.f(hi)
        if i1 - i0 < 2:
            return None
        seg = self.db[i0:i1]
        q = seg <= self.nguong
        if q.any():
            idx = np.flatnonzero(np.diff(np.concatenate([[0], q.astype(np.int8), [0]])))
            runs = sorted(zip(idx[0::2], idx[1::2]), key=lambda r: -(r[1] - r[0]))
            s, e = runs[0]
            if e - s >= 3:
                return (i0 + (s + e) / 2.0) * KHUNG
        if not cho_trung:
            return None
        j = int(np.argmin(seg))
        quanh = self.db[max(0, i0 - 25):min(len(self.db), i1 + 25)]
        if float(np.percentile(quanh, 80)) - float(seg[j]) < 18.0:
            return None
        return (i0 + j + 0.5) * KHUNG

    def nho_nhat(self, lo, hi):
        """Khung nhỏ tiếng nhất trong [lo, hi] (chỗ tách cảnh nối liền khi zoom)."""
        i0, i1 = self.f(lo), self.f(hi)
        if i1 - i0 < 1:
            return (lo + hi) / 2.0
        return (i0 + int(np.argmin(self.db[i0:i1])) + 0.5) * KHUNG


# ------------------------------------------------------------------ phân tích 1 clip
def phan_tich_clip(ci, clip, T, words, ghi_bo):
    """-> {"vung", "tu", "doan" (đoạn nói), "khong_loi"}; ghi_bo(loai, a, b, chu, ly_do) ghi chỗ bỏ."""
    vung = [{"a": a, "b": b, "tu": [], "loai": None} for a, b in T.vung()]
    tu = []
    for k, w in enumerate(words):
        a = float(w[1])
        x = {"w": str(w[0]), "a": a, "a0": a, "b": float(w[2]), "d": w[3] if len(w) > 3 else 0, "k": k, "clip": ci, "bo": None, "v": None}
        tu.append(x)
        # Máy nghe (sherpa) đặt chữ đầu mỗi đoạn nghe ở giây 0 của đoạn = sớm ~0,25s so với tiếng thật (tu_dien.bo_im_dau chừa 0,25s
        # im trước tiếng), chữ sau chỗ nghỉ cũng hay sớm 0,1–0,3s -> chữ rơi vào chỗ im: dời tới khung có tiếng đầu tiên trong 0,45s
        # sau. Không có tiếng nào quanh đó = máy nghe nhầm (tiếng thở, tiếng động).
        lo, hi = a - 0.08, a + 0.45
        if T.so_khung_co(a, hi) < 4 and T.so_khung_co(lo, a + 0.1) < 4:
            x["bo"] = "nghe_nham"
            ghi_bo("nghe_nham", x["a"], x["b"], x["w"], "máy nghe ra chữ ở chỗ không có tiếng nói (nghe nhầm)")
            continue
        k0 = T.f(a)
        if k0 < len(T.co) and not T.co[k0]:
            nx = np.flatnonzero(T.co[k0:T.f(hi)])
            if len(nx) and T.so_khung_co(a, hi) >= 4:
                x["a"] = round((k0 + int(nx[0])) * KHUNG, 3)
        lo, hi = x["a"] - 0.08, x["a"] + 0.30
        best = None
        for vi, v in enumerate(vung):
            ov = min(hi, v["b"]) - max(lo, v["a"])
            if ov > 0 and (best is None or ov > best[0]):
                best = (ov, vi)
        if best is None:
            x["bo"] = "nghe_nham"
            continue
        x["v"] = best[1]
        vung[best[1]]["tu"].append(x)
    # giờ chữ sau khi dời: giữ thứ tự, mỗi chữ >= 0,08s; hết chữ >= đầu chữ + 0,1s, không quá đầu chữ sau
    that = [x for x in tu if not x["bo"]]
    for p, q in zip(that, that[1:]):
        if q["a"] < p["a"] + 0.08 and q["v"] == p["v"]:
            q["a"] = round(p["a"] + 0.08, 3)
    for i, x in enumerate(that):
        x["b"] = max(x["b"], x["a"] + 0.1)
        if i + 1 < len(that) and that[i + 1]["a"] > x["a"]:
            x["b"] = round(min(x["b"], max(that[i + 1]["a"], x["a"] + 0.08)), 3)
    # vùng có lời mà tiếng kéo dài xa quá chữ cuối / trước chữ đầu (vd nhạc mở loa nối liền câu): tách phần đuôi / đầu không lời
    them = []
    for v in vung:
        that = [x for x in v["tu"] if not x["bo"]]
        if not that:
            continue
        cuoi = max(x["a"] for x in that) + 0.45
        dau = min(x["a"] for x in that)
        if v["b"] - cuoi > DUOI_THUA + 0.3:
            them.append({"a": cuoi, "b": v["b"], "tu": [], "loai": None, "tach": True})
            v["b"] = cuoi
        if dau - v["a"] > DUOI_THUA + 0.3:
            them.append({"a": v["a"], "b": dau - 0.05, "tu": [], "loai": None, "tach": True})
            v["a"] = dau - 0.05
    vung = sorted(vung + them, key=lambda v: v["a"])
    # vùng chỉ có tiếng đệm (ừ / à / ờ) hoặc từ đệm đứng riêng
    for vi, v in enumerate(vung):
        that = [x for x in v["tu"] if not x["bo"]]
        if not that:
            if v["b"] - v["a"] >= KHONG_LOI_DAI and float(np.mean(T.db[T.f(v["a"]):T.f(v["b"])])) >= T.nguong + 6:
                v["loai"] = "khong_loi"
            else:
                v["loai"] = "tieng_nho"
            continue
        chu = " ".join(x["w"].lower() for x in that)
        truoc = v["a"] - vung[vi - 1]["b"] if vi else 9.0
        sau = vung[vi + 1]["a"] - v["b"] if vi + 1 < len(vung) else 9.0
        if all(x["w"].lower() in TIENG_DEM for x in that):
            v["loai"] = "tieng_dem"
        elif chu in TU_DEM and v["b"] - v["a"] <= 0.9 and truoc >= 0.3 and sau >= 0.3:
            v["loai"] = "tu_dem"
        else:
            v["loai"] = "loi"
            continue
        for x in that:
            x["bo"] = v["loai"]
        ghi_bo(v["loai"], v["a"], v["b"], chu, "tiếng đệm đứng riêng" if v["loai"] == "tieng_dem" else "từ đệm đứng riêng (có nghỉ 2 bên)")
    # đoạn nói = các vùng có lời cách nhau <= NGHI_GIU (vùng tiếng nhỏ không lời nằm giữa giữ theo)
    doan, cur = [], None
    for vi, v in enumerate(vung):
        if v["loai"] != "loi":
            continue
        if cur and v["a"] - cur["b"] <= NGHI_GIU and not any(
                vung[x]["loai"] in ("tieng_dem", "tu_dem", "khong_loi") for x in range(cur["vi"][-1] + 1, vi)):
            cur["b"] = v["b"]
            cur["vi"].append(vi)
        else:
            cur = {"clip": ci, "a": v["a"], "b": v["b"], "vi": [vi]}
            doan.append(cur)
    for d in doan:
        d["tu"] = [x for vi in range(d["vi"][0], d["vi"][-1] + 1) for x in vung[vi]["tu"] if not x["bo"]]
        d["tu"].sort(key=lambda x: x["a"])
    return {"vung": vung, "tu": tu, "doan": doan}


def lap_trong_doan(d, T, ghi_bo):
    """Lặp chữ liền ("nó nó") / nói lại liền không nghỉ ("với thiết kế với thiết kế chiếc…") trong 1 đoạn: bỏ lần đầu nếu có chỗ
    ngắt tiếng rõ ở 2 đầu. -> [(x, y)] khoảng bỏ (giờ clip). Không có chỗ ngắt sạch: để nguyên, ghi "chua_cat"."""
    out, ds = [], d["tu"]
    W = [chuan(x["w"]) for x in ds]
    i = 0
    while i < len(ds) - 1:
        tim = None
        for m in (4, 3, 2):   # cụm 2–4 chữ lặp lại ngay sau (trong 8 chữ)
            for j in range(i + m, min(len(ds) - m + 1, i + 9)):
                if W[i:i + m] == W[j:j + m] and any(w not in STOP_C for w in W[i:i + m]):
                    tim = (j, m)
                    break
            if tim:
                break
        if not tim and W[i] == W[i + 1] and W[i] not in {chuan(x) for x in LAP_DUOC} and ds[i + 1]["a"] - ds[i]["a"] <= 0.5:
            tim = (i + 1, 1)
        if not tim:
            i += 1
            continue
        j, m = tim
        x = d["a"] - LE_TRUOC - 0.02 if i == 0 else T.cho_ngat(ds[i]["a"] - 0.12, ds[i]["a"] + 0.20)
        y = T.cho_ngat(ds[j]["a"] - 0.12, ds[j]["a"] + 0.20)
        chu = " ".join(z["w"] for z in ds[i:j])
        if x is None or y is None or y - x < 0.08:
            ghi_bo("chua_cat", ds[i]["a"], ds[j]["a"], chu, "lặp / nói lại liền không ngắt tiếng — chưa cắt (cắt dễ vấp)")
            d["vap_lap"] = d.get("vap_lap", 0) + 1   # vẫn là 1 chỗ vấp khi chọn lần nói tốt nhất
            i = j
            continue
        for z in ds[i:j]:
            z["bo"] = "lap"
        if ds[j]["a"] < y + 0.02:   # máy nghe đặt chữ giữ lại sớm hơn chỗ ngắt (tiếng thật của nó ở sau chỗ ngắt)
            ds[j]["a"] = round(y + 0.02, 3)
        out.append((x, y))
        ghi_bo("lap", x, y, chu, "lặp chữ" if m == 1 and j == i + 1 else "nói lại liền (bỏ lần đầu, giữ lần sau)")
        d["vap_lap"] = d.get("vap_lap", 0) + 1
        i = j
    d["tu"] = [z for z in ds if not z["bo"]]
    return out


# ------------------------------------------------------------------ dựng thô
class DungTho:
    def __init__(self, args):
        self.args = args
        self.bo = []        # [{"clip", "file", "loai", "tu", "den", "chu", "ly_do"}]
        self.noi_lai = []
        self.zoom = []
        self.goi_y = []
        self.canh_bao = []
        self.bo_kieu = None   # bộ kiểu Dựng tự động (r38, tu_dung_gan.doc_bo); None = dựng thô như trước

    # ---------------- 1. nghe + năng lượng
    def nghe(self):
        a = self.args
        md = CH.mo_hinh_hoac_none() if hasattr(CH, "mo_hinh_hoac_none") else CH.MO_HINH
        if not md or not os.path.isdir(md):
            raise SystemExit("Chưa có máy nghe tiếng Việt (mô hình sherpa): ghi --mo-hinh <thư mục mo-hinh>")
        kho = a.kho or self._kho_mac_dinh()
        os.makedirs(kho, exist_ok=True)
        self.kho = kho
        with contextlib.redirect_stdout(sys.stderr):
            if TD:
                self.td = TD.doc()
                self.rec, self.khoa = TD.recognizer(md, self.td, kho=os.path.join(kho, "tu-dien"))
            else:
                self.td, self.khoa = {"tu": [], "sua": []}, "greedy"
                self.rec = NG.recognizer(md)
        self.clips = []
        self.tmp = tempfile.mkdtemp(prefix="dung-tho-")
        for ci, p in enumerate(a.clip):
            in_("BUOC=Nghe clip %d/%d (%s)" % (ci + 1, len(a.clip), os.path.basename(p)))
            info = M.do_clip(p)
            T = Tieng(p, self.tmp)
            r = {"tu": []}
            if T.co_tieng and info.get("co_tieng"):
                r = M._nghe_clip(self.rec, p, kho, self.khoa, getattr(TD, "bo_im_dau", None) if TD else None)
            self.clips.append({"i": ci, "p": p, "file": xuoi(p), "ten": os.path.basename(p), "info": info, "T": T,
                               "raw": r.get("tu") or [], "dur": float(info.get("giay") or T.dur)})

    def _kho_mac_dinh(self):
        d = os.path.join(APP, "_cache")
        if os.path.isdir(d):   # máy có app POLY Cut: dùng chung cache nghe của "Tạo phụ đề từ lời nói"
            return os.path.join(d, "nghe")
        return os.path.join(tempfile.gettempdir(), "poly-dung-tho", "nghe")

    def ghi_bo(self, ci):
        def f(loai, a, b, chu, ly_do):
            self.bo.append({"clip": self.clips[ci]["ten"], "ci": ci, "loai": loai, "tu": round(max(0.0, a), 2), "den": round(b, 2),
                            "chu": chu, "ly_do": ly_do})
        return f

    # ---------------- 2. cắt từng clip + câu nói lại
    def phan_tich(self):
        self.doan = []
        for c in self.clips:
            pt = phan_tich_clip(c["i"], c, c["T"], c["raw"], self.ghi_bo(c["i"]))
            c.update(pt)
            c["xoa"] = []
            for d in c["doan"]:
                c["xoa"] += lap_trong_doan(d, c["T"], self.ghi_bo(c["i"]))
            for d in c["doan"]:
                if not d["tu"]:
                    continue
                ws = [x for x in d["tu"]]
                gap = [b["a"] - a["a"] for a, b in zip(ws, ws[1:])]
                d["chu"] = [chuan(w[0]) for w in self.sua([[x["w"], x["a"], x["b"], x["d"]] for x in ws])]
                d["vap"] = {"n": len(ws), "ngung": sum(1 for g in gap if g > NGUNG_VAP + 0.3), "lap": d.get("vap_lap", 0),
                            "dem": sum(1 for b in self.bo if b["ci"] == c["i"] and b["loai"] in ("tieng_dem", "tu_dem")
                                       and d["a"] - 0.5 <= b["tu"] <= d["b"] + 0.5)}
                self.doan.append(d)
        # câu nói lại: theo thứ tự video (clip theo thứ tự anh đưa, trong clip theo giờ)
        dd = self.doan

        def gan(i, j, he_so=1.0):
            a, b = dd[i], dd[j]
            if a["clip"] == b["clip"]:
                g = b["a"] - a["b"]
                return g if 0 <= g <= GAN_NOI_LAI * he_so else None
            if b["clip"] == a["clip"] + 1:
                g = (self.clips[a["clip"]]["dur"] - a["b"]) + b["a"]
                return g if g <= GAN_NOI_LAI_CLIP * he_so else None
            return None
        for r in tim_noi_lai(dd, gan):
            bo_ids = r["A"] if r["giu"] == "B" else r["B"]
            giu_ids = r["B"] if r["giu"] == "B" else r["A"]

            def mo(ids):
                c = self.clips[dd[ids[0]]["clip"]]
                return {"clip": c["ten"], "tu": round(dd[ids[0]]["a"], 2), "den": round(dd[ids[-1]]["b"], 2),
                        "chu": " ".join(self.chu_doan(dd[x]) for x in ids)}
            vap_bo = r["vapA"] if r["giu"] == "B" else r["vapB"]
            loi = []
            if vap_bo["ngung"]:
                loi.append("ngừng %d lần giữa câu" % vap_bo["ngung"])
            if vap_bo["lap"]:
                loi.append("lặp / nói lại liền %d chỗ" % vap_bo["lap"])
            if vap_bo["dem"]:
                loi.append("%d tiếng đệm" % vap_bo["dem"])
            ghi = {"giu": mo(giu_ids), "bo": mo(bo_ids), "lan_giu": 2 if r["giu"] == "B" else 1, "ly_do": r["ly_do"],
                   "loi_lan_bo": ", ".join(loi) or ("thiếu câu" if r["giu"] == "A" else "nói lại câu này ngay sau đó"),
                   "chu_trung": r["trung"]}
            self.noi_lai.append(ghi)
            for x in bo_ids:
                d = dd[x]
                d["bo"] = "noi_lai"
                for w in d["tu"]:
                    w["bo"] = "noi_lai"
                self.bo.append({"clip": self.clips[d["clip"]]["ten"], "ci": d["clip"], "loai": "noi_lai", "tu": round(d["a"], 2),
                                "den": round(d["b"], 2), "chu": self.chu_doan(d),
                                "ly_do": "câu nói lại: bỏ lần %d, giữ lần %d (%s)" % (3 - ghi["lan_giu"], ghi["lan_giu"], r["ly_do"])})

    def sua(self, ws):
        if not TD or not ws:
            return ws
        try:
            return TD.sua_tu(ws, self.td)
        except Exception:  # noqa  từ điển lỗi: lời thô
            return ws

    def chu_doan(self, d):
        return " ".join(w[0] for w in self.sua([[x["w"], x["a"], x["b"], x["d"]] for x in d["tu"]]))

    # ---------------- 3. phần giữ của từng clip (mặt nạ 10 ms)
    def phan_giu(self):
        a = self.args
        bo_tay, giu_tay = self._khoang_tay(a.bo), self._khoang_tay(a.giu)
        for c in self.clips:
            T, dur = c["T"], c["dur"]
            n = int(dur / KHUNG) + 2
            mask = np.zeros(n, dtype=np.int8)
            f = lambda t: int(min(max(round(t / KHUNG), 0), n))
            for d in c["doan"]:
                if d.get("bo") or not d["tu"]:
                    continue
                mask[f(d["a"] - LE_TRUOC):f(d["b"] + LE_SAU)] = 1
            # nhạc / tiếng loa không lời ngay sau câu nói về loa, âm thanh -> giữ ít giây (thử loa); còn lại bỏ
            for vi, v in enumerate(c["vung"]):
                if v["loai"] != "khong_loi":
                    continue
                truoc = [d for d in c["doan"] if not d.get("bo") and d["tu"] and d["b"] <= v["a"] + 0.05]
                chu = bo_dau(" ".join(x["w"] for x in truoc[-1]["tu"][-15:])).lower() if truoc else ""
                if truoc and v["a"] - truoc[-1]["b"] <= CACH_THU_LOA and any(k in chu for k in LOA_TU):
                    het = min(v["b"], T.nho_nhat(v["a"] + THU_LOA_GIU - 1.0, v["a"] + THU_LOA_GIU + 0.5))
                    # cách câu trước ngắn (<= nghỉ giữ + lề sau): nối liền, khỏi 1 chỗ cắt chỉ bỏ 0,1s
                    dau_ = truoc[-1]["b"] if v["a"] - truoc[-1]["b"] <= NGHI_GIU + LE_SAU else v["a"] - LE_TRUOC
                    mask[f(dau_):f(het)] = 1
                    v["giu"] = (v["a"], het)
                    self.bo.append({"clip": c["ten"], "ci": c["i"], "loai": "thu_loa", "tu": round(het, 2), "den": round(v["b"], 2),
                                    "chu": "", "ly_do": "tiếng không lời (thử loa) dài %ss: giữ %ss đầu sau câu \"%s\", bỏ phần còn lại"
                                    % (so_vn(v["b"] - v["a"]), so_vn(het - v["a"]), " ".join(x["w"] for x in truoc[-1]["tu"][-6:]))})
                else:
                    self.bo.append({"clip": c["ten"], "ci": c["i"], "loai": "khong_loi", "tu": round(v["a"], 2), "den": round(v["b"], 2),
                                    "chu": "", "ly_do": "tiếng không có lời dài %ss (nhạc / tiếng máy / ồn?)" % so_vn(v["b"] - v["a"])})
            # vùng tiếng bị bỏ (ừ / à, câu hỏng, tiếng không lời ngoài phần thử loa): lề đoạn bên cạnh không lấn vào
            for d in c["doan"]:
                if d.get("bo"):
                    mask[f(d["a"] - CACH_VUNG_BO):f(d["b"] + CACH_VUNG_BO)] = 0
            for v in c["vung"]:
                if v["loai"] in ("tieng_dem", "tu_dem"):
                    mask[f(v["a"] - CACH_VUNG_BO):f(v["b"] + CACH_VUNG_BO)] = 0
                elif v["loai"] in ("khong_loi", "tieng_nho") and not v.get("giu"):
                    if not any(not d.get("bo") and d["a"] <= v["a"] and v["b"] <= d["b"] for d in c["doan"]):
                        mask[f(v["a"] - CACH_VUNG_BO):f(v["b"] + CACH_VUNG_BO)] = 0
                elif v.get("giu"):
                    mask[f(v["giu"][1]):f(v["b"] + CACH_VUNG_BO)] = 0
            for x, y in c["xoa"]:
                mask[f(x):f(y)] = 0
            for ten, x, y in bo_tay:
                if ten == c["ten"].lower():
                    mask[f(x):f(y)] = 0
                    ws = [z for z in c["tu"] if not z["bo"] and x <= z["a"] < y]
                    for z in ws:
                        z["bo"] = "tay"
                    self.bo.append({"clip": c["ten"], "ci": c["i"], "loai": "tay", "tu": x, "den": y, "chu": " ".join(z["w"] for z in ws),
                                    "ly_do": "chọn bỏ (--bo)"})
            for ten, x, y in giu_tay:
                if ten == c["ten"].lower():
                    mask[f(x):f(y)] = 1
            mask[f(dur - 0.02):] = 0
            # lấp lỗ nhỏ, ra các phần giữ
            idx = np.flatnonzero(np.diff(np.concatenate([[0], mask, [0]])))
            runs = [[int(s), int(e)] for s, e in zip(idx[0::2], idx[1::2])]
            gop = []
            for s, e in runs:
                if gop and (s - gop[-1][1]) * KHUNG < LO_NHO:
                    gop[-1][1] = e
                else:
                    gop.append([s, e])
            phan = []
            for s, e in gop:
                tu, den = s * KHUNG, e * KHUNG
                ws = [x for x in c["tu"] if not x["bo"] and tu - 0.02 <= x["a"] <= den]
                tay = any(t == c["ten"].lower() and x <= tu + 0.05 and den - 0.05 <= y for t, x, y in giu_tay)
                thu_loa = any(v.get("giu") and tu <= v["giu"][0] <= den for v in c["vung"])
                if not tay and not thu_loa and (den - tu < DOAN_MIN or (len(ws) <= 1 and den - tu < DOAN_1_TU)):
                    for x in ws:
                        x["bo"] = "ngan"
                    self.bo.append({"clip": c["ten"], "ci": c["i"], "loai": "ngan", "tu": round(tu, 2), "den": round(den, 2),
                                    "chu": " ".join(x["w"] for x in ws), "ly_do": "đoạn quá ngắn (%ss)" % so_vn(den - tu, 2)})
                    continue
                phan.append({"clip": c["i"], "tu": round(tu, 3), "den": round(den, 3), "tu_ds": ws})
            # chữ (chưa bỏ) mà không nằm trong phần nào: máy nghe đặt sớm ngay trước 1 phần giữ (chỗ đó đã cắt = im) -> thuộc phần đó;
            # còn lại ghi bỏ (không để mất chữ mà không biết)
            for x in c["tu"]:
                if x["bo"] or any(p["tu"] - 0.02 <= x["a"] <= p["den"] for p in phan):
                    continue
                sau = [p for p in phan if 0 < p["tu"] - x["a"] <= 0.25]
                if sau and not any(z is not x and not z["bo"] and x["a"] < z["a"] < sau[0]["tu"] for z in c["tu"]):
                    x["a"] = round(sau[0]["tu"] + 0.01, 3)
                    x["b"] = max(x["b"], x["a"] + 0.1)
                    sau[0]["tu_ds"] = sorted(sau[0]["tu_ds"] + [x], key=lambda z: z["a"])
                    continue
                x["bo"] = "ngoai"
                self.bo.append({"clip": c["ten"], "ci": c["i"], "loai": "ngoai", "tu": x["a"], "den": x["b"], "chu": x["w"],
                                "ly_do": "chữ nằm ngoài các đoạn giữ (bị bỏ theo đoạn quanh nó)"})
            c["phan"] = phan
            # khoảng im đã cắt (giữa các phần giữ và 2 đầu clip) -> ghi bỏ "im"
            moc = [0.0] + [x for p in phan for x in (p["tu"], p["den"])] + [dur]
            for x, y in zip(moc[0::2], moc[1::2]):
                if y - x >= 0.05:
                    self.bo.append({"clip": c["ten"], "ci": c["i"], "loai": "cat", "tu": round(x, 2), "den": round(y, 2), "chu": "",
                                    "ly_do": "phần bị cắt"})

    def _khoang_tay(self, ds):
        out = []
        for s in ds or []:
            m = re.match(r"^(.+):\s*([\d.,]+)\s*-\s*([\d.,]+)\s*$", str(s))
            if not m:
                raise SystemExit("--bo / --giu sai dạng: %s (đúng: IMG_4409.MOV:29.6-30.4)" % s)
            out.append((os.path.basename(m.group(1)).lower(), float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", "."))))
        return out

    # ---------------- 4. cảnh + phụ đề + zoom nhấn
    def canh_phu_de(self):
        a = self.args
        ten_may = ten_may_tu_dien(self.td or {})
        dong = a.zoom if a.zoom else DONG_NHAN
        if dong != "khong" and dong not in getattr(KH, "DONG_CANH", {}):
            raise SystemExit("--zoom phải là 1 chuyển động riêng cảnh có sẵn: %s hoặc khong" % ", ".join(sorted(KH.DONG_CANH)))
        # câu phụ đề từng phần giữ (chữ đã sửa theo từ điển, chia câu như "Tạo phụ đề từ lời nói")
        tat = []
        t_video = 0.0
        for c in self.clips:
            for p in c["phan"]:
                ws = [[x["w"], x["a"], x["b"], x["d"]] for x in p["tu_ds"]]
                sw = self.sua(ws)
                cau = (TD.chia_cau(sw, self.td) if TD and hasattr(TD, "chia_cau") else M._chia_cau(sw)) if sw else []
                p["cau"] = [x for x in cau if x]
                p["t_video"] = t_video
                t_video += p["den"] - p["tu"]
                tat.append(p)
        # zoom nhấn: câu có từ khoá; 2 chỗ zoom cách nhau >= ZOOM_CACH giây video, ưu tiên giá / pin rồi tới câu sớm hơn.
        # Tên máy / inch / GB đã zoom 1 lần thì nhắc lại không zoom nữa (giá, pin nhắc lại vẫn zoom)
        ung = []
        for p in tat:
            for qi, q in enumerate(p["cau"]):
                kh = tu_khoa_cau([w[0] for w in q], ten_may)
                if kh:
                    t0 = p["t_video"] + max(0.0, float(q[0][1]) - p["tu"])
                    khoa = {(l, re.sub(r"\s*inch$", "", c.lower()).replace(",", ".")) for l, c, _ in kh if l in ("ten_may", "inch", "gb")}
                    ung.append({"p": p, "qi": qi, "kh": kh, "ut": max(x[2] for x in kh), "t": t0, "khoa": khoa,
                                "lap_lai": len(khoa) == len(kh)})
        chon, da = [], set()
        if dong != "khong":
            for u in sorted(ung, key=lambda u: (-u["ut"], u["t"])):
                if u["lap_lai"] and u["khoa"] <= da:
                    u["ly_do_bo"] = "đã zoom chỗ nhắc trước"
                    continue
                if all(abs(u["t"] - v["t"]) >= ZOOM_CACH for v in chon):
                    chon.append(u)
                    da |= u["khoa"]
                else:
                    u["ly_do_bo"] = "gần chỗ zoom khác quá"
        chon_set = {(id(u["p"]), u["qi"]) for u in chon}
        for u in ung:
            if (id(u["p"]), u["qi"]) not in chon_set:
                u["bo_qua"] = True
        # tách phần giữ thành cảnh: câu zoom -> cảnh riêng nối liền (noi_lien) có dong
        canh = []
        for p in tat:
            c = self.clips[p["clip"]]
            T = c["T"]
            cat = []   # [(x, y, zoom_u)]
            zs = sorted([u for u in chon if u["p"] is p], key=lambda u: u["qi"])
            phang = [w for q in p["cau"] for w in q]   # chữ cả phần (đã sửa), theo giờ

            def tach(i0, buoc):
                """Chỗ tách cảnh ngay trước chữ phang[i0] (lùi / tiến tối đa 3 chữ tìm chỗ ngắt tiếng rõ) | None = không tách."""
                for k in range(4):
                    i = i0 + buoc * k
                    if i <= 0 or i >= len(phang):
                        return None
                    t = float(phang[i][1])
                    x_ = T.cho_ngat(t - 0.15, t + 0.25, cho_trung=True)
                    if x_ is not None and p["tu"] < x_ < p["den"]:
                        return x_
                return None
            for u in zs:
                q = p["cau"][u["qi"]]
                i_dau = sum(len(z) for z in p["cau"][:u["qi"]])
                i_sau = i_dau + len(q)
                x = tach(i_dau, -1) if i_dau > 0 else None
                y = tach(i_sau, +1) if i_sau < len(phang) else None
                x = p["tu"] if x is None else x
                y = p["den"] if y is None else y
                if x - p["tu"] < ZOOM_PHAN_MIN:
                    x = p["tu"]
                if p["den"] - y < ZOOM_PHAN_MIN:
                    y = p["den"]
                if cat and x < cat[-1][1] + ZOOM_PHAN_MIN:
                    x = cat[-1][1]
                if y - x < 0.3:
                    u["bo_qua"] = True
                    u["ly_do_bo"] = "câu ngắn quá, không tách được cảnh riêng"
                    continue
                cat.append((round(x, 3), round(y, 3), u))
            moc, t = [], p["tu"]
            for x, y, u in cat:
                if x > t:
                    moc.append((t, x, None))
                moc.append((x, y, u))
                t = y
            if t < p["den"]:
                moc.append((t, p["den"], None))
            for k, (x, y, u) in enumerate(moc):
                ws = [w for w in p["tu_ds"] if x - 0.02 <= w["a"] < y]
                ct = {"_id": "c" + uuid.uuid4().hex[:8], "file": c["file"], "tu": round(x, 3), "den": round(y, 3),
                      "mo_ta": self._mo_ta(ws, c["ten"])}
                if u is not None:
                    ct["dong"] = dong
                    u["canh"] = ct
                if k > 0:
                    ct["noi_lien"] = True   # nửa cảnh tách ra để zoom: cắt thẳng, tiếng liền (ke_hoach.noi_lien)
                canh.append((ct, p))
        # phụ đề: neo theo giờ clip (như sua_tay_may.nghe_phu_de) -> app tính giờ trên video theo cảnh
        pd = []
        for p in tat:
            c = self.clips[p["clip"]]
            for q in p["cau"]:
                s0, s1 = max(p["tu"], float(q[0][1])), min(p["den"], float(q[-1][2]))
                if s1 - s0 < 0.2:
                    continue
                cid = next((ct["_id"] for ct, pp in canh if pp is p and ct["tu"] - 0.02 <= s0 < ct["den"]), canh[0][0]["_id"])
                chu = self.in_hoa(" ".join(str(w[0]) for w in q))
                pd.append({"_k": "p" + uuid.uuid4().hex[:8], "chu": chu, "t0": round(s0, 3), "t1": round(s1, 3),
                           "_neo": {"id": cid, "file": c["file"], "s0": round(s0, 3), "s1": round(s1, 3), "cau": True,
                                    # giờ từng chữ kẹp trong [s0, s1]: chữ lố ra ngoài bị ap_neo bỏ -> mất tô chữ cả câu
                                    "tu": [[self.in_hoa(str(w[0])), round(min(max(float(w[1]), s0), s1 - 0.05), 3),
                                            round(max(min(float(w[2]), s1), min(max(float(w[1]), s0), s1 - 0.05) + 0.05), 3)] for w in q]}})
        self.canh = [ct for ct, _ in canh]
        self.pd = pd
        self.ung_zoom = ung
        self.tat = tat

    def _mo_ta(self, ws, ten):
        chu = " ".join(x["w"] for x in ws[:8])
        if not ws:
            return "%s: tiếng không lời (thử loa)" % os.path.splitext(ten)[0]
        return ("%s: \"%s%s\"" % (os.path.splitext(ten)[0], chu, "…" if len(ws) > 8 else ""))[:90]

    def in_hoa(self, s):
        try:
            import ve_chu as VC
            return VC.in_hoa(s)
        except Exception:  # noqa
            return str(s).upper()

    # ---------------- 5. kế hoạch Sửa tay
    def ke_hoach(self):
        a = self.args
        ra = os.path.abspath(a.ra)
        os.makedirs(ra, exist_ok=True)
        goc = slugify(a.ten or os.path.splitext(self.clips[0]["ten"])[0]) or "dung-tho"
        slug, i = goc, 2
        if not a.ghi_de:
            while os.path.exists(os.path.join(ra, slug)):
                slug, i = "%s-%d" % (goc, i), i + 1
        v = os.path.join(ra, slug)
        if a.ghi_de and os.path.isdir(v):
            for x in ("lam", "BAO-CAO.md", "nhap-dung-tho.mp4"):
                q = os.path.join(v, x)
                if os.path.isdir(q):
                    shutil.rmtree(q, ignore_errors=True)
                elif os.path.isfile(q):
                    os.remove(q)
        self.v, self.slug = v, slug
        dung = [c for c in self.clips if c["phan"]]
        if not dung:
            raise SystemExit("Không nghe thấy lời nói nào trong các clip (clip không có tiếng hoặc chỉ có tiếng ồn)")
        in_("BUOC=Tạo kế hoạch")
        with contextlib.redirect_stdout(sys.stderr):
            # nguồn + kiểu mặc định trơn như "Video mới từ clip". Mọi clip anh đưa đều vào nguồn (clip không còn cảnh nào, vd lần nói
            # hỏng, vẫn nằm trong thư viện clip của video để anh thêm lại nếu muốn)
            M.lenh_moi({"ra": ra, "slug": slug, "clip": [c["file"] for c in self.clips]})
        W = os.path.join(v, "lam")
        kp = os.path.join(W, "ke-hoach.json")
        plan = M.doc(kp, chac=True)
        G = _gan() if self.bo_kieu else None
        if G:
            self.plan_tron = G.plan_tron(M, plan)   # bản như Video mới từ clip: nút Hoàn tác cả lượt
        self._duoi_the_ket(plan)
        if G:
            in_("BUOC=Gắn chữ, nhạc, chuyển cảnh")
            G.gan(self, plan, _ns())
        plan["canh"] = copy.deepcopy(self.canh)
        plan["phu_de"] = copy.deepcopy(self.pd)
        plan["bo"] = self._bo_ngan()[:40]
        M.danh_dau(plan)
        M.gan_neo(plan, "may_chu")
        p, gio_, tl, moc = M.ap_neo(plan, "may_chu")
        if G and G.sau(self, plan, p, gio_, tl, moc, _ns()):   # nhãn đè hook / thẻ giá…: bỏ rồi tính lại giờ
            p, gio_, tl, moc = M.ap_neo(plan, "may_chu")
        self.plan_sua = plan                 # bản đang sửa (có _id / _neo), đường dẫn máy này: dựng nháp
        self.moc = moc
        self.tl = tl
        self.T_video = float(tl["T"])
        out = M.sach(p)
        self.plan_may = copy.deepcopy(out)   # đường dẫn máy này
        bang = doc_doi_duong(a.doi_duong)
        if bang:
            out = self._doi_duong_plan(out, bang)
        M.ghi(kp, out)
        self.plan_ghi = out
        self.kp = kp
        # giờ trên video từng cảnh (báo cáo, gợi ý chèn, kiểm)
        for i, ct in enumerate(self.canh):
            if i in moc:
                ct["_bd"] = moc[i]["bd"]

    def _duoi_the_ket(self, plan):
        """Thẻ kết (mặc định của video tạo tay: hiện ket_giay = 3,6s cuối, che phụ đề) -> nối thêm tới ket_giay giây hình cuối clip
        KHÔNG có lời ngay sau cảnh cuối (dừng trước lời / tiếng đệm kế tiếp) làm nền cho thẻ kết, để câu cuối còn phụ đề.
        Clip hết ngay sau lời (còn < 1s): để nguyên, báo cáo nhắc."""
        self.duoi = None
        k = plan.get("kieu") or {}
        if k.get("ket") == "khong" or not self.canh:
            return
        try:
            kg = float(plan.get("ket_giay") or 3.6)
        except (TypeError, ValueError):
            kg = 3.6
        ct = self.canh[-1]
        c = next(x for x in self.clips if x["file"] == ct["file"])
        het = c["dur"] - 0.05
        for x in c["tu"]:
            if x["bo"] != "nghe_nham" and x["a"] > ct["den"]:
                het = min(het, x["a"] - 0.15)
        for v in c["vung"]:
            if v["a"] >= ct["den"] - 0.01 and v["loai"] in ("loi", "tieng_dem", "tu_dem"):
                het = min(het, v["a"] - 0.05)
        them = round(min(kg, het - ct["den"]), 3)
        if them < 1.0:
            return
        T = c["T"]
        if T.co[min(T.f(ct["den"] + them), len(T.co) - 1)]:   # hết đuôi giữa tiếng (nhạc, tiếng máy): lùi về chỗ nhỏ tiếng nhất gần đó
            them = round(T.nho_nhat(ct["den"] + max(1.0, them - 0.6), ct["den"] + them) - ct["den"], 3)
        self.duoi = {"clip": c["ten"], "tu": ct["den"], "den": round(ct["den"] + them, 3), "giay": them}
        ct["den"] = round(ct["den"] + them, 3)
        for p in self.tat:   # phần giữ của clip cũng dài ra (gợi ý chèn tính chỗ đã dùng)
            if p["clip"] == c["i"] and abs(p["den"] - self.duoi["tu"]) < 1e-6:
                p["den"] = ct["den"]
        for b in self.bo:   # khoảng bị cắt sau cảnh cuối ngắn lại
            if b["loai"] == "cat" and b["ci"] == c["i"] and abs(b["tu"] - round(self.duoi["tu"], 2)) < 0.011:
                b["tu"] = round(ct["den"], 2)
        self.bo = [b for b in self.bo if not (b["loai"] == "cat" and b["den"] - b["tu"] < 0.05)]

    def _doi_duong_plan(self, plan, bang):
        p = copy.deepcopy(plan)
        ng = {}
        for k, src in (p.get("nguon") or {}).items():
            k2 = doi_duong(k, bang)
            src = dict(src or {})
            if src.get("local"):
                src["local"] = doi_duong(src["local"], bang)
            ng[k2] = src
        p["nguon"] = ng
        for c in p.get("canh") or []:
            c["file"] = doi_duong(c["file"], bang)
        if isinstance(p.get("ra"), dict) and p["ra"].get("thu_muc"):
            p["ra"]["thu_muc"] = doi_duong(p["ra"]["thu_muc"], bang)
        for x in ([p["nhac"]] if isinstance(p.get("nhac"), dict) else []) + [y for y in p.get("am_thanh") or [] if isinstance(y, dict)]:
            for k in ("local", "file"):   # nhạc / âm thanh Dựng tự động gắn (r38): file trong thư mục app
                if x.get(k):
                    x[k] = doi_duong(x[k], bang)
        if p.get("ra") and p["ra"]["thu_muc"] == plan["ra"]["thu_muc"] and not re.match(r"^[A-Za-z]:", str(plan["ra"]["thu_muc"])):
            self.canh_bao.append("Thư mục ra chưa đổi sang máy tiệm (thêm --doi-duong \"%s=E:\\Tool\\poly-edit\"): app tự tính lại khi xuất"
                                 % xuoi(os.path.dirname(self.v)))
        chua = [k for k in ng if not re.match(r"^[A-Za-z]:|^//|^\\\\", k)]
        if chua:
            self.canh_bao.append("Đường clip chưa đổi sang máy tiệm: " + ", ".join(os.path.basename(x) for x in chua))
        return p

    def _bo_ngan(self):
        out = []
        for b in self.bo:
            if b["loai"] in ("cat", "nghe_nham"):
                continue
            out.append("%s %s–%ss: %s%s" % (os.path.splitext(b["clip"])[0], so_vn(b["tu"]), so_vn(b["den"]), b["ly_do"],
                                            (" \"%s\"" % b["chu"][:40]) if b["chu"] else ""))
        return out

    # ---------------- 6. gợi ý cảnh chèn (chỉ ghi báo cáo)
    def goi_y_chen(self):
        a = self.args
        self.khung = {} if getattr(a, "khong_khung", False) else self._lam_khung()   # trong app (Dựng tự động): không cần ảnh khung
        mt = {}
        if a.mo_ta:
            raw = M.doc(a.mo_ta, {}) or {}
            raw = raw.get("clip") if isinstance(raw.get("clip"), dict) else raw
            for k, ds in (raw or {}).items():
                if isinstance(ds, dict):
                    ds = [ds]
                mt[os.path.basename(str(k)).lower()] = [x for x in ds or [] if isinstance(x, dict)]
        self.mo_ta = mt
        if not mt:
            return
        dung = {}   # clip -> [(tu, den)] đã nằm trong video
        for ct in self.canh:
            dung.setdefault(os.path.basename(ct["file"]).lower(), []).append((ct["tu"], ct["den"]))
        lan, gan_nhat = {}, {}
        for p in self.tat:
            c = self.clips[p["clip"]]
            for q in p["cau"]:
                chu = " " + re.sub(r"\s+", " ", bo_dau(" ".join(str(w[0]) for w in q)).lower()) + " "
                t_clip = float(q[0][1])
                rieng = " ".join(bo_dau(" ".join([x.get("mo_ta") or ""] + list(x.get("tu_khoa") or []))).lower()
                                 for x in mt.get(c["ten"].lower(), []) if float(x.get("tu", 0)) - 0.5 <= t_clip <= float(x.get("den", 1e9)) + 0.5)
                tot = None
                for ten, ds in mt.items():
                    for ri, R in enumerate(ds):
                        for k in sorted([str(x) for x in R.get("tu_khoa") or [] if str(x).strip()], key=lambda x: -len(x)):
                            kb = " " + bo_dau(k).lower().strip() + " "
                            if kb not in chu or kb.strip() in rieng:
                                continue
                            r0, r1 = float(R.get("tu", 0)), float(R.get("den", 0) or 0)
                            ranh = self._con_trong(r0, r1, dung.get(ten, []))
                            if not ranh or lan.get((ten, ri), 0) >= 2:
                                continue
                            if tot is None or len(k) > len(tot["vi"]):
                                tot = {"clip_chen": next((x["ten"] for x in self.clips if x["ten"].lower() == ten), ten), "tu": round(ranh[0], 1),
                                       "den": round(ranh[1], 1), "mo_ta": R.get("mo_ta") or "", "vi": k, "_ri": (ten, ri)}
                            break
                if tot:
                    tv = p["t_video"] + max(0.0, float(q[0][1]) - p["tu"])
                    luc = round(self._gio_video(p, float(q[0][1]), tv), 1)
                    ri = tot.pop("_ri")
                    if luc - gan_nhat.get(ri, -99) < 15.0:   # cùng cảnh chèn vừa gợi ý trong 15s trước: 1 lần thôi
                        continue
                    gan_nhat[ri] = luc
                    lan[ri] = lan.get(ri, 0) + 1
                    tot.update({"luc": luc, "cau": self.in_hoa(" ".join(str(w[0]) for w in q)), "clip_noi": c["ten"]})
                    self.goi_y.append(tot)

    def _con_trong(self, r0, r1, dung):
        """Khoảng [r0, r1] trừ các đoạn đã dùng trong video -> khoảng trống dài nhất (>= 1s) | None."""
        ds = [(r0, r1)]
        for x, y in dung:
            moi = []
            for a, b in ds:
                if y <= a or x >= b:
                    moi.append((a, b))
                    continue
                if x > a:
                    moi.append((a, x))
                if y < b:
                    moi.append((y, b))
            ds = moi
        ds = [d for d in ds if d[1] - d[0] >= 1.0]
        return max(ds, key=lambda d: d[1] - d[0]) if ds else None

    def _gio_video(self, p, t_clip, mac_dinh):
        for i, ct in enumerate(self.canh):
            if ct["file"] == self.clips[p["clip"]]["file"] and ct["tu"] - 0.02 <= t_clip < ct["den"] and "_bd" in ct:
                return ct["_bd"] + t_clip - ct["tu"]
        return mac_dinh

    def _lam_khung(self):
        """6 khung mỗi clip (có giờ) -> lam/dung-tho/khung/<clip>.jpg để Claude xem, viết mo-ta.json."""
        from PIL import Image, ImageDraw, ImageFont
        d = os.path.join(self.v, "lam", "dung-tho", "khung")
        os.makedirs(d, exist_ok=True)
        try:
            f = ImageFont.truetype(os.path.join(CH.FONT_DIR, "BeVietnamPro-Bold.ttf"), 20)
        except OSError:
            f = ImageFont.load_default()
        out = {}
        for c in self.clips:
            n = 6
            ts = [round((k + 0.5) * c["dur"] / n, 1) for k in range(n)]
            ims = []
            for k, t in enumerate(ts):
                x = M._khung(c["p"], t, os.path.join(self.tmp, "k%d-%d.jpg" % (c["i"], k)))
                ims.append(Image.open(x).convert("RGB") if x else None)
            w = max([im.width for im in ims if im] or [135])
            h = 240
            sheet = Image.new("RGB", (n * (w + 6) + 6, h + 40), (24, 24, 24))
            dr = ImageDraw.Draw(sheet)
            for k, (im, t) in enumerate(zip(ims, ts)):
                x = 6 + k * (w + 6)
                if im:
                    sheet.paste(im, (x, 34))
                dr.text((x + 2, 6), "%ss" % so_vn(t), font=f, fill=(255, 214, 0))
            p = os.path.join(d, os.path.splitext(c["ten"])[0] + ".jpg")
            sheet.save(p, quality=82)
            out[c["ten"]] = xuoi(p)
        return out

    # ---------------- 7. bản nháp (bộ dựng ffmpeg, như nút Xuất bản nháp)
    def nhap(self):
        in_("BUOC=Dựng bản nháp")
        viec = os.path.join(self.tmp, "viec-nhap.json")
        M.ghi(viec, {"v": self.v, "nhap": True, "plan": copy.deepcopy(self.plan_sua)})
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(APP, "sua_tay_may.py"), "xuat", viec], cwd=os.environ["POLY_ENGINE"], env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace", **KW)
        xong = next((l[5:] for l in (r.stdout or "").splitlines() if l.startswith("XONG=")), None)
        loi = next((l[4:] for l in (r.stdout or "").splitlines() if l.startswith("LOI=")), None)
        if r.returncode or not xong:
            raise SystemExit("Dựng bản nháp lỗi: %s" % (loi or (r.stderr or "")[-600:]))
        kq = json.loads(xong)
        cb = [json.loads(l[9:]) for l in (r.stdout or "").splitlines() if l.startswith("CANH_BAO=")]
        for x in (cb[-1] if cb else []):
            self.canh_bao.append("Bản nháp: " + str(x))
        out = os.path.join(self.v, "nhap-dung-tho.mp4")
        M_dir = os.path.join(self.v, "lam", "sua-tay", "nhap")
        self.dtg = M.doc(os.path.join(M_dir, "dong-thoi-gian.json"), {}) or {}
        shutil.move(kq["mp4"], out)
        shutil.rmtree(M_dir, ignore_errors=True)
        st = os.path.join(self.v, "lam", "sua-tay")
        if os.path.isdir(st) and not os.listdir(st):
            os.rmdir(st)
        self.mp4 = out
        self.nhap_giay = round(time.time() - t0, 1)
        self.nhap_T = kq.get("giay")

    # ---------------- 8. kiểm bản nháp
    def kiem(self):
        in_("BUOC=Nghe lại bản nháp")
        K = {}
        # chữ mong đợi (giờ trên video) = chữ giữ của từng cảnh
        mong = []
        cho_noi = []
        for i, ct in enumerate(self.canh):
            bd = ct.get("_bd")
            if bd is None:
                continue
            if i > 0 and not ct.get("noi_lien"):
                cho_noi.append(bd)
            c = next(x for x in self.clips if x["file"] == ct["file"])
            for x in c["tu"]:
                if not x["bo"] and ct["tu"] - 0.02 <= x["a"] < ct["den"]:
                    mong.append({"w": x["w"], "t": bd + x["a"] - ct["tu"], "clip": c["ten"], "s": x["a"]})
        T = Tieng(self.mp4, self.tmp)
        r = M._nghe_clip(self.rec, self.mp4, self.kho, self.khoa, getattr(TD, "bo_im_dau", None) if TD else None)
        # so theo chữ đã sửa từ điển (máy nghe nghe cùng 1 tiếng ra "markibo" / "maryt kibo" -> Magic Keyboard), tách lại từng tiếng
        def tach_tu(ds):
            out = []   # cột 5 = chỉ số chữ gốc (cột 4 là "đoạn nghe": sua_tu chỉ gộp chữ cùng đoạn)
            for w in self.sua([[x["w"], x["t"], x["t"] + 0.2, 0, i] for i, x in enumerate(ds)]):
                for z in str(w[0]).split():
                    out.append(dict(ds[w[4]] if len(w) > 4 else {}, w=z, t=float(w[1])))
            return out
        nghe = tach_tu([{"w": w[0], "t": float(w[1])} for w in r.get("tu") or []])
        mong = tach_tu(mong)
        A = [chuan(x["w"]) for x in mong]
        B = [chuan(x["w"]) for x in nghe]
        L, cap = lcs(A, B)
        khop_a = {i for i, _ in cap}
        khop_b = {j for _, j in cap}
        moi_noi = [ct["_bd"] for i, ct in enumerate(self.canh) if i > 0 and ct.get("_bd") is not None]   # cả chỗ tách zoom
        mat = [dict(mong[i], gan_cho_cat=any(abs(mong[i]["t"] - x) < 0.4 for x in moi_noi)) for i in range(len(A)) if i not in khop_a]
        thua = [dict(nghe[j], gan_cho_cat=any(abs(nghe[j]["t"] - x) < 0.4 for x in cho_noi)) for j in range(len(B)) if j not in khop_b]
        # chữ mất gần chỗ nối: nghe riêng đúng đoạn GIỮ của clip gốc và đoạn rộng hơn 0,6s 2 đầu. Đoạn rộng có chữ mà đoạn giữ không
        # có = chỗ cắt làm mất chữ (lỗi thật); cả 2 cùng thiếu = máy nghe nghe khác (cùng tiếng, cách chia đoạn khác)
        for x in mat:
            if x["gan_cho_cat"]:
                x["do_cat"] = self._mat_do_cat(x)
        K["nghe_lai"] = {"chu_mong": len(A), "chu_nghe": len(B), "khop": L, "ty_le": round(L / max(1, len(A)), 3),
                         "mat": [{"chu": x["w"], "luc": round(x["t"], 2), "clip": x["clip"], "giay_clip": round(x["s"], 2),
                                  "gan_cho_cat": x["gan_cho_cat"], "do_cat": x.get("do_cat")} for x in mat],
                         "mat_do_cat": [{"chu": x["w"], "luc": round(x["t"], 2), "clip": x["clip"], "giay_clip": round(x["s"], 2)}
                                        for x in mat if x.get("do_cat")],
                         "thua": [{"chu": x["w"], "luc": round(x["t"], 2), "gan_cho_cat": x["gan_cho_cat"]} for x in thua]}
        # mốc chữ so với chỗ cắt (giờ CLIP GỐC): mỗi chỗ cắt thật (không tính chỗ tách zoom nối liền) -> lề tới khung có tiếng gần
        # nhất phía giữ, độ to ngay chỗ cắt so với ngưỡng (cắt trong im = không cụt chữ), cách chữ đầu / cuối máy nghe đặt
        le = []
        for i, ct in enumerate(self.canh):
            c = next(x for x in self.clips if x["file"] == ct["file"])
            T0 = c["T"]
            ws = [x for x in c["tu"] if not x["bo"] and ct["tu"] - 0.02 <= x["a"] < ct["den"]]
            nxt = self.canh[i + 1] if i + 1 < len(self.canh) else None
            ngat = [round(x, 2) for xy in c["xoa"] for x in xy]   # chỗ cắt ở chỗ ngắt giữa 2 chữ nói liền (lặp chữ)
            for dau, t in (("dau", ct["tu"]), ("cuoi", ct["den"])):
                if (dau == "dau" and ct.get("noi_lien")) or (dau == "cuoi" and nxt is not None and nxt.get("noi_lien")):
                    continue
                k = T0.f(t)
                if dau == "dau":
                    co = np.flatnonzero(T0.co[k:k + 100])
                    l_ = round(float(co[0]) * KHUNG, 3) if len(co) else None
                    cach_chu = round(ws[0]["a"] - t, 3) if ws else None
                else:
                    co = np.flatnonzero(T0.co[max(0, k - 100):k])
                    l_ = round((min(k, 100) - 1 - float(co[-1])) * KHUNG, 3) if len(co) else None
                    cach_chu = round(t - ws[-1]["a"], 3) if ws else None
                db = float(T0.db[min(max(k - (1 if dau == "cuoi" else 0), 0), len(T0.db) - 1)])
                # cắt trong tiếng KHÔNG lời (bớt nhạc thử loa, đuôi nền thẻ kết): không phải cắt giữa tiếng nói
                nhac = any(v["loai"] in ("khong_loi", "tieng_nho") and v["a"] - 0.02 <= t <= v["b"] + 0.02 for v in c["vung"])
                le.append({"canh": i + 1, "clip": c["ten"], "dau_cuoi": dau, "luc_clip": round(t, 3), "le": l_, "db": round(db, 1),
                           "nguong": round(T0.nguong, 1), "trong_im": db <= T0.nguong, "cho_ngat": any(abs(t - x) < 0.02 for x in ngat),
                           "cat_thu_loa": nhac, "chu": (ws[0]["w"] if dau == "dau" else ws[-1]["w"]) if ws else "", "cach_moc_chu": cach_chu})
        K["le"] = le
        lt = [x["le"] for x in le if x["dau_cuoi"] == "dau" and x["le"] is not None and x["trong_im"]]
        ls = [x["le"] for x in le if x["dau_cuoi"] == "cuoi" and x["le"] is not None and x["trong_im"]]
        K["le_tom"] = {"truoc_min": min(lt) if lt else None, "sau_min": min(ls) if ls else None,
                       "truoc_tb": round(sum(lt) / len(lt), 3) if lt else None, "sau_tb": round(sum(ls) / len(ls), 3) if ls else None,
                       "cat_giua_tieng": [x for x in le if not x["trong_im"] and not x["cho_ngat"] and not x["cat_thu_loa"]],
                       "cat_thu_loa": [x for x in le if x["cat_thu_loa"]],
                       "cat_cho_ngat": [x for x in le if x["cho_ngat"]]}
        # khoảng im > 0,5s còn sót trong bản nháp (bỏ 0,3s cuối)
        q = (~T.co).astype(np.int8)
        idx = np.flatnonzero(np.diff(np.concatenate([[0], q, [0]])))
        cuoi = T.dur - 0.3 - (self.duoi["giay"] if self.duoi else 0.0)   # đuôi nền thẻ kết (cố ý không lời): không tính
        im = [(s * KHUNG, e * KHUNG) for s, e in zip(idx[0::2], idx[1::2]) if s * KHUNG < cuoi]
        K["im_sot"] = [{"tu": round(x, 2), "den": round(y, 2), "giay": round(y - x, 2)} for x, y in im if y - x > 0.5]
        K["im_dai_nhat"] = round(max([0.0] + [y - x for x, y in im]), 2)
        K["nguong_nhap_db"] = round(T.nguong, 1)
        # tiếng bụp ở chỗ nối (cả chỗ cắt lẫn chỗ tách zoom): bước nhảy mẫu 48 kHz quanh chỗ nối so với cả bài
        moi_noi = [ct["_bd"] for i, ct in enumerate(self.canh) if i > 0 and ct.get("_bd") is not None]
        K["cho_noi"] = self._kiem_bup(self.mp4, moi_noi)
        K["dai_nhap"] = round(T.dur, 2)
        self.kq_kiem = K
        return K

    def _nghe_doan(self, T, a, b):
        """Máy nghe trên đoạn [a, b] của tiếng 1 clip -> chữ đã sửa từ điển, chuẩn hoá."""
        seg = T.a[max(0, int(a * 16000)):int(b * 16000)].astype(np.float32)
        if len(seg) < 1600:
            return []
        st = self.rec.create_stream()
        st.accept_waveform(16000, seg)
        self.rec.decode_stream(st)
        ws, cur = [], None
        for tok in st.result.tokens:
            if tok.startswith(("▁", " ")) or cur is None:
                if cur:
                    ws.append(cur)
                cur = tok.lstrip("▁ ")
            else:
                cur += tok
        if cur:
            ws.append(cur)
        return [chuan(z) for w in self.sua([[w.lower(), 0, 0.2, 0] for w in ws if w]) for z in str(w[0]).split()]

    def _mat_do_cat(self, x):
        """Chữ x (mất khi nghe lại bản nháp, gần chỗ nối) có phải do chỗ cắt không (xem kiem)."""
        c = next((k for k in self.clips if k["ten"] == x.get("clip")), None)
        if not c:
            return None
        ds = [i for i, ct in enumerate(self.canh) if ct["file"] == c["file"] and ct["tu"] - 0.05 <= x["s"] <= ct["den"] + 0.05]
        if not ds:
            return None
        i0 = i1 = ds[0]
        while i0 > 0 and self.canh[i0].get("noi_lien"):
            i0 -= 1
        while i1 + 1 < len(self.canh) and self.canh[i1 + 1].get("noi_lien"):
            i1 += 1
        a, b = self.canh[i0]["tu"], self.canh[i1]["den"]
        w = chuan(x["w"])
        return (w in self._nghe_doan(c["T"], a - 0.6, b + 0.6)) and (w not in self._nghe_doan(c["T"], a, b))

    def _kiem_bup(self, mp4, cho_noi):
        r = subprocess.run([CH.FFMPEG, "-v", "error", "-i", mp4, "-vn", "-ac", "1", "-ar", "48000", "-f", "f32le", "-"],
                           capture_output=True, **KW)
        x = np.frombuffer(r.stdout, np.float32).astype(np.float64)
        if len(x) < 4800:
            return {"so": 0}
        dx = np.abs(np.diff(x))
        nen = float(np.percentile(dx, 99.9)) + 1e-9
        rms_all = float(np.sqrt(np.mean(x ** 2))) + 1e-9
        out = []
        for t in cho_noi:
            i = int(t * 48000)
            w = dx[max(0, i - 240):i + 240]   # ±5 ms
            v = x[max(0, i - 960):i + 960]    # ±20 ms
            if not len(w):
                continue
            out.append({"luc": round(t, 3), "buoc_nhay": round(float(w.max()) / nen, 2),
                        "db_quanh": round(20 * np.log10(float(np.sqrt(np.mean(v ** 2))) / rms_all + 1e-9), 1)})
        bup = [o for o in out if o["buoc_nhay"] > 3.0]
        return {"so": len(out), "bup": bup, "buoc_nhay_max": max([o["buoc_nhay"] for o in out] or [0]),
                "db_quanh_max": max([o["db_quanh"] for o in out] or [-99]), "chi_tiet": out}

    # ---------------- 9. ghi số đo + báo cáo
    def tong_ket(self):
        dai_truoc = sum(c["dur"] for c in self.clips)
        so_cho_cat = sum(1 for i, ct in enumerate(self.canh) if i > 0 and not ct.get("noi_lien"))
        cat = [b for b in self.bo if b["loai"] == "cat"]
        so_do = {"dai_truoc": round(dai_truoc, 2), "dai_sau": round(self.T_video, 2), "bo_giay": round(dai_truoc - self.T_video, 2),
                 "so_cho_cat": so_cho_cat, "so_doan_bo": len(cat), "so_canh": len(self.canh),
                 "so_zoom": sum(1 for ct in self.canh if ct.get("dong")), "so_cau_phu_de": len(self.plan_ghi.get("phu_de") or []),
                 "khoang_im": len(self.khoang_im()), "khoang_im_giay": round(sum(y - x for _, x, y in self.khoang_im()), 2),
                 "so_noi_lai": len(self.noi_lai), "so_tieng_dem": sum(1 for b in self.bo if b["loai"] in ("tieng_dem", "tu_dem")),
                 "so_lap": sum(1 for b in self.bo if b["loai"] == "lap")}
        self.so_do = so_do
        dj = {"phien_ban": PHIEN_BAN, "luc": datetime.datetime.now().isoformat(timespec="seconds"), "ten": self.args.ten, "slug": self.slug,
              "thu_muc_video": xuoi(self.v), "ke_hoach": xuoi(self.kp), "so_do": so_do,
              "tham_so": {"le_truoc": LE_TRUOC, "le_sau": LE_SAU, "nghi_giu": NGHI_GIU, "doan_min": DOAN_MIN, "zoom": self.args.zoom or DONG_NHAN,
                          "khoa_may_nghe": self.khoa},
              "duoi_the_ket": self.duoi,
              "clip": [{"ten": c["ten"], "file": c["file"], "giay": round(c["dur"], 2), "co_tieng": c["T"].co_tieng,
                        "nguong_db": round(c["T"].nguong, 1), "nen_db": round(c["T"].nen, 1), "noi_db": round(c["T"].noi, 1),
                        "loi_nghe": " ".join(x["w"] for x in c["tu"] if x["bo"] != "nghe_nham"),
                        "giu": [[p["tu"], p["den"]] for p in c["phan"]], "khung": self.khung.get(c["ten"])} for c in self.clips],
              "canh": [{"so": i + 1, "clip": os.path.basename(ct["file"]), "tu": ct["tu"], "den": ct["den"], "luc": round(ct.get("_bd", 0), 2),
                        "dong": ct.get("dong"), "noi_lien": bool(ct.get("noi_lien")), "mo_ta": ct.get("mo_ta")} for i, ct in enumerate(self.canh)],
              "bo": [{k: v for k, v in b.items() if k != "ci"} for b in self.bo],
              "noi_lai": self.noi_lai,
              "zoom": [{"luc": round(self._gio_video(u["p"], float(u["p"]["cau"][u["qi"]][0][1]), u["t"]), 1),
                        "cau": self.in_hoa(" ".join(str(w[0]) for w in u["p"]["cau"][u["qi"]])),
                        "tu_khoa": [x[1] for x in u["kh"]], "loai": [x[0] for x in u["kh"]], "zoom": not u.get("bo_qua"), "ly_do_bo": u.get("ly_do_bo", ""),
                        "clip": self.clips[u["p"]["clip"]]["ten"], "giay_clip": round(float(u["p"]["cau"][u["qi"]][0][1]), 2)}
                       for u in sorted(self.ung_zoom, key=lambda u: u["t"])],
              "goi_y_chen": self.goi_y, "mo_ta_clip": self.mo_ta, "canh_bao": self.canh_bao,
              "nhap": xuoi(self.mp4) if getattr(self, "mp4", None) else None, "kiem": getattr(self, "kq_kiem", None)}
        self.dj = dj
        M.ghi(os.path.join(self.v, "lam", "dung-tho.json"), dj)
        with open(os.path.join(self.v, "BAO-CAO.md"), "w", encoding="utf-8") as f:
            f.write(self.bao_cao())

    def khoang_im(self):
        """Phần bị cắt mà không thuộc chỗ bỏ có lý do khác (câu nói lại, tiếng đệm, nhạc…) = khoảng im thật -> [(clip, tu, den)]."""
        khac = [b for b in self.bo if b["loai"] not in ("cat", "nghe_nham", "ngoai", "chua_cat")]
        out = []
        for b in self.bo:
            if b["loai"] != "cat":
                continue
            ds = [(b["tu"], b["den"])]
            for o in khac:
                if o["ci"] != b["ci"]:
                    continue
                moi = []
                for x, y in ds:
                    if o["den"] <= x or o["tu"] >= y:
                        moi.append((x, y))
                        continue
                    if o["tu"] > x:
                        moi.append((x, o["tu"]))
                    if o["den"] < y:
                        moi.append((o["den"], y))
                ds = moi
            out += [(b["clip"], x, y) for x, y in ds if y - x >= 0.1]
        return out

    def bao_cao(self):
        s, dj = self.so_do, self.dj
        L = ["# Dựng thô: %s" % (self.args.ten or self.slug), ""]
        L.append("- Clip: " + ", ".join("%s (%ss)" % (c["ten"], so_vn(c["dur"])) for c in self.clips))
        L.append("- **Dài %ss → %ss** (bỏ %ss), %d chỗ cắt, %d cảnh (%d cảnh zoom nhấn), %d câu phụ đề IN HOA."
                 % (so_vn(s["dai_truoc"]), so_vn(s["dai_sau"]), so_vn(s["bo_giay"]), s["so_cho_cat"], s["so_canh"], s["so_zoom"],
                    s["so_cau_phu_de"]))
        L.append("- Mở trong POLY Cut: Sửa tay › video **%s** (kế hoạch `lam/ke-hoach.json`). Kiểu cả video: mặc định trơn như Video mới từ clip."
                 % self.slug)
        L += ["", "## Đã bỏ"]
        im = self.khoang_im()
        if im:
            dai = max(im, key=lambda b: b[2] - b[1])
            L.append("- Khoảng im (khoảng chết): %d chỗ, tổng %ss (dài nhất %ss ở %s %s–%s)." % (
                len(im), so_vn(sum(y - x for _, x, y in im)), so_vn(dai[2] - dai[1]), dai[0], gio(dai[1]), gio(dai[2])))
        for loai, ten in (("tieng_dem", "Tiếng đệm (ừ / à / ờ…)"), ("tu_dem", "Từ đệm đứng riêng"), ("lap", "Lặp chữ / nói lại liền"),
                          ("ngan", "Đoạn quá ngắn"), ("khong_loi", "Tiếng không có lời"), ("thu_loa", "Thử loa (cắt bớt)"),
                          ("tay", "Chọn bỏ tay"), ("chua_cat", "Lặp chữ chưa cắt được (nói liền, cắt dễ vấp)")):
            ds = [b for b in self.bo if b["loai"] == loai]
            if ds:
                L.append("- %s: %s." % (ten, "; ".join("%s %s%s" % (os.path.splitext(b["clip"])[0], gio(b["tu"]),
                                                                    (" \"%s\"" % b["chu"]) if b["chu"] else (" (%s)" % b["ly_do"]))
                                                       for b in ds[:8]) + (" …" if len(ds) > 8 else "")))
        nn = [b for b in self.bo if b["loai"] == "nghe_nham"]
        if nn:
            L.append("- Máy nghe ra %d chữ ở chỗ không có tiếng (nghe nhầm): không tính." % len(nn))
        if self.duoi:
            L.append("- Giữ thêm %ss cuối %s (%s–%s, không lời) làm nền cho thẻ kết, để thẻ kết không che phụ đề câu cuối."
                     % (so_vn(self.duoi["giay"]), self.duoi["clip"], gio(self.duoi["tu"]), gio(self.duoi["den"])))
        L += ["", "## Câu nói lại"]
        if not self.noi_lai:
            L.append("- Không thấy câu nào nói lại.")
        for r in self.noi_lai:
            L.append("- Đã bỏ lần %d: %s %s–%s \"%s\" (%s)." % (3 - r["lan_giu"], r["bo"]["clip"], gio(r["bo"]["tu"]), gio(r["bo"]["den"]),
                                                               ngan(r["bo"]["chu"], 160), r["loi_lan_bo"]))
            L.append("  Giữ lần %d: %s %s–%s \"%s\" — %s." % (r["lan_giu"], r["giu"]["clip"], gio(r["giu"]["tu"]), gio(r["giu"]["den"]),
                                                             ngan(r["giu"]["chu"], 160), r["ly_do"]))
        L += ["", "## Zoom nhấn (%s)" % ("Phóng sát" if (self.args.zoom or DONG_NHAN) == "phong_sat" else (self.args.zoom or DONG_NHAN))]
        z = [x for x in dj["zoom"] if x["zoom"]]
        if not z:
            L.append("- Không có câu nào nói giá / pin % / GB / inch / tên máy.")
        for x in z:
            L.append("- %s \"%s\" (%s)" % (gio(x["luc"]), x["cau"], ", ".join(x["tu_khoa"])))
        bq = [x for x in dj["zoom"] if not x["zoom"]]
        if bq:
            L.append("- Không zoom: " + "; ".join("%s \"%s\" (%s)" % (gio(x["luc"]), x["cau"], x["ly_do_bo"]) for x in bq[:6]))
        L += ["", "## Gợi ý cảnh chèn (chưa chèn, anh tự chọn)"]
        if not self.mo_ta:
            L.append("- Chưa có mô tả clip (mo-ta.json): Claude xem ảnh khung `lam/dung-tho/khung/` rồi chạy lại với --mo-ta.")
        elif not self.goi_y:
            L.append("- Không có lời nào nhắc tới thứ có trong clip khác.")
        for g in self.goi_y:
            L.append("- %s \"%s\" → chèn %s %s–%s (%s)" % (gio(g["luc"]), g["cau"], g["clip_chen"], gio(g["tu"]), gio(g["den"]), g["mo_ta"]))
        K = dj.get("kiem")
        if K:
            nl = K["nghe_lai"]
            L += ["", "## Kiểm bản nháp"]
            L.append("- Nghe lại bản nháp: khớp %d/%d chữ (%d%%); không khớp %d chữ, %d chữ mất do chỗ cắt%s." % (
                nl["khop"], nl["chu_mong"], round(100 * nl["ty_le"]), len(nl["mat"]), len(nl["mat_do_cat"]),
                (": " + ", ".join("%s %s" % (x["chu"], gio(x["luc"])) for x in nl["mat_do_cat"])) if nl["mat_do_cat"] else
                " (chữ không khớp là máy nghe nghe khác, tiếng vẫn còn)" if nl["mat"] else ""))
            lt = K["le_tom"]
            L.append("- Chỗ cắt: lề trước ít nhất %ss, lề sau ít nhất %ss; cắt giữa tiếng nói: %d chỗ%s." % (
                so_vn(lt["truoc_min"] or 0, 2), so_vn(lt["sau_min"] or 0, 2), len(lt["cat_giua_tieng"]),
                ("; %d chỗ cắt ở chỗ ngắt giữa 2 chữ (bỏ lặp chữ)" % len(lt["cat_cho_ngat"])) if lt["cat_cho_ngat"] else ""))
            L.append("- Khoảng im > 0,5s còn sót: %d (dài nhất %ss)." % (len(K["im_sot"]), so_vn(K["im_dai_nhat"], 2)))
            L.append("- Chỗ nối: %d, tiếng bụp: %d (bước nhảy lớn nhất %s lần mức thường)." % (
                K["cho_noi"]["so"], len(K["cho_noi"].get("bup") or []), so_vn(K["cho_noi"].get("buoc_nhay_max") or 0, 2)))
        if getattr(self, "mp4", None):
            L += ["", "Bản nháp xem nhanh: `nhap-dung-tho.mp4` (540x960, dựng bằng ffmpeg)."]
        if self.canh_bao:
            L += ["", "## Lưu ý"] + ["- " + x for x in self.canh_bao[:10]]
        return "\n".join(L) + "\n"


def _ns():
    """Tên của file này (M, KH, CH, np, gio, so_vn…) cho tu_dung_gan.py (bài thử nạp file bằng importlib: không có trong sys.modules)."""
    import types
    return types.SimpleNamespace(**globals())


def _gan():
    """Phần tự gắn của Dựng tự động (tu_dung_gan.py cạnh file này)."""
    if APP not in sys.path:
        sys.path.insert(0, APP)
    import tu_dung_gan
    return tu_dung_gan


def kiem_may(a):
    """In 1 dòng JSON: bộ dựng, ffmpeg / ffprobe, mô hình máy nghe, sherpa-onnx (cần 2.0.1), numpy, Pillow, từ điển tiệm. Thoát 1 nếu thiếu."""
    out, thieu = {}, []
    try:
        out["engine"] = nap(a.engine or None, a.mo_hinh or None)
    except SystemExit as e:
        print(json.dumps({"ok": False, "thieu": [str(e)]}, ensure_ascii=False))
        sys.exit(1)
    except ImportError as e:
        print(json.dumps({"ok": False, "thieu": ["thư viện Python: %s (pip install sherpa-onnx==2.0.1 numpy Pillow)" % e]}, ensure_ascii=False))
        sys.exit(1)
    for ten in ("FFMPEG", "FFPROBE"):
        exe = getattr(CH, ten)
        try:
            r = subprocess.run([exe, "-version"], capture_output=True, text=True, errors="replace", timeout=30, **KW)
            out[ten.lower()] = (r.stdout or "").splitlines()[0][:60] if r.returncode == 0 else None
        except OSError:
            out[ten.lower()] = None
        if not out[ten.lower()]:
            thieu.append(ten.lower())
    md = CH.mo_hinh_hoac_none() if hasattr(CH, "mo_hinh_hoac_none") else None
    out["mo_hinh"] = xuoi(md) if md else None
    if not md:
        thieu.append("mô hình máy nghe (--mo-hinh)")
    elif not os.path.isfile(os.path.join(md, "bpe.model")):
        out["canh_bao"] = "mô hình thiếu bpe.model: nghe không ưu tiên được từ của tiệm"
    import sherpa_onnx
    import PIL
    out["sherpa_onnx"] = getattr(sherpa_onnx, "__version__", "?")
    if out["sherpa_onnx"] != "2.0.1":
        thieu.append("sherpa-onnx phải đúng 2.0.1 (đang %s)" % out["sherpa_onnx"])
    out["numpy"], out["pillow"] = np.__version__, PIL.__version__
    out["tu_dien"] = xuoi(TD.TEP) if TD else None
    out["so_tu_dien"] = len((TD.doc() or {}).get("tu") or []) if TD else 0
    out["ok"] = not thieu
    out["thieu"] = thieu
    print(json.dumps(out, ensure_ascii=False))
    if thieu:
        sys.exit(1)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Dựng thô từ clip nói -> video Sửa tay của POLY Cut")
    ap.add_argument("--clip", nargs="+", default=[], help="clip theo thứ tự trong video")
    ap.add_argument("--ra", default="", help="thư mục ra (thư mục video của app, vd E:\\Tool\\poly-edit)")
    ap.add_argument("--ten", default="", help="tên video (thư mục = tên không dấu)")
    ap.add_argument("--doi-duong", action="append", default=[], help='"<thư mục máy này>=E:\\...\\<thư mục máy tiệm>" (lặp được)')
    ap.add_argument("--nhap", action="store_true", help="dựng thêm bản nháp mp4 540x960")
    ap.add_argument("--kiem", action="store_true", help="(cần --nhap) nghe lại bản nháp, dò im / bụp / cụt chữ")
    ap.add_argument("--mo-ta", default="", help="mo-ta.json: mô tả từng clip (Claude viết sau khi xem khung) để gợi ý cảnh chèn")
    ap.add_argument("--bo", action="append", default=[], help="CLIP:giây-giây bắt bỏ")
    ap.add_argument("--giu", action="append", default=[], help="CLIP:giây-giây bắt giữ")
    ap.add_argument("--zoom", default="", help="chuyển động zoom nhấn (mặc định phong_sat; khong = không zoom)")
    ap.add_argument("--ghi-de", action="store_true", help="ghi đè thư mục video cùng tên (chạy lại)")
    ap.add_argument("--engine", default="", help="thư mục bộ dựng (engine)")
    ap.add_argument("--mo-hinh", default="", help="thư mục mô hình máy nghe sherpa")
    ap.add_argument("--kho", default="", help="thư mục cache lời nghe")
    ap.add_argument("--kiem-may", action="store_true", help="chỉ kiểm máy đủ đồ chưa (bộ dựng, ffmpeg, mô hình, thư viện) rồi thoát")
    ap.add_argument("--bo-kieu", default="", help="Dựng tự động (r38): mã bộ kiểu (dung-tu-dong/<mã>.json) hoặc file .json -> tự gắn")
    ap.add_argument("--khong-khung", action="store_true", help="không làm ảnh khung từng clip (app Dựng tự động: nhanh hơn)")
    ap.add_argument("--kho-effect", default="", help="thư mục kho effect (bộ kiểu ở <kho>/dung-tu-dong/<mã>.json đè bộ của app)")
    a = ap.parse_args(argv)
    if a.kiem_may:
        return kiem_may(a)
    if not a.clip or not a.ra:
        ap.error("cần --clip và --ra")
    a.clip = [os.path.abspath(p) for p in a.clip]
    for p in a.clip:
        if not os.path.isfile(p):
            raise SystemExit("Không thấy clip %s" % p)
    if len(set(os.path.basename(p).lower() for p in a.clip)) < len(a.clip):
        raise SystemExit("Có 2 clip trùng tên file: đổi tên 1 clip rồi chạy lại")
    doc_doi_duong(a.doi_duong)   # kiểm sớm
    nap(a.engine or None, a.mo_hinh or None)
    t0 = time.time()
    D = DungTho(a)
    if a.bo_kieu:
        D.kho_effect = a.kho_effect if a.kho_effect and os.path.isdir(a.kho_effect) else None
        D.bo_kieu = _gan().doc_bo(a.bo_kieu, D.kho_effect)
        if not a.zoom:
            a.zoom = str((D.bo_kieu.get("zoom") or {}).get("dong") or DONG_NHAN)
            if a.zoom != "khong" and a.zoom not in getattr(KH, "DONG_CANH", {}):
                D.bo_kieu.setdefault("_canh_bao", []).append("Zoom nhấn: không có chuyển động \"%s\", dùng Phóng sát" % a.zoom)
                a.zoom = DONG_NHAN
    try:
        D.nghe()
        in_("BUOC=Cắt khoảng chết, tiếng đệm, câu nói lại")
        D.phan_tich()
        D.phan_giu()
        D.canh_phu_de()
        D.ke_hoach()
        D.goi_y_chen()
        if a.nhap:
            D.nhap()
            if a.kiem:
                D.kiem()
                if D.bo_kieu:
                    _gan().kiem_them(D, _ns())
        D.tong_ket()
        if D.bo_kieu:
            _gan().ghi(D, _ns())
    finally:
        if getattr(D, "tmp", None):
            shutil.rmtree(D.tmp, ignore_errors=True)
    in_("XONG=" + json.dumps({"v": xuoi(D.v), "ke_hoach": xuoi(D.kp), "bao_cao": xuoi(os.path.join(D.v, "BAO-CAO.md")),
                              "nhap": xuoi(D.mp4) if getattr(D, "mp4", None) else None, "so_do": D.so_do,
                              "giay_chay": round(time.time() - t0, 1)}, ensure_ascii=False))
    return D


if __name__ == "__main__":
    main()
