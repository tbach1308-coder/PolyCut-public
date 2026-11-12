#!/usr/bin/env python3
"""Chuyển cảnh MỚI kiểu trend 'poly-chuyen-1' (r35, 11/11/2026; anh duyệt 11/11: đưa cả 15 kiểu vào app).

Mỗi kiểu là 1 file JSON (engine/chuyen-canh/<id>.json gói sẵn; sau này thêm Kho effect trên Drive) mô tả bằng "đường cong theo
tiến độ p" (0 = còn cảnh trước, 1 = đã sang cảnh sau) cho từng bên A (cảnh trước) / B (cảnh sau): zoom, xoay, lật 3D, dời, kéo
giãn, mờ, tối, sáng, trong suốt, bo góc, bóng; cộng lớp phủ tự vẽ: chớp sáng, vệt sáng, tách màu, sọc nhiễu, chớp mắt. Bộ đọc này
dựng mọi kiểu -> thêm kiểu = thêm file JSON. Khung xem của app vẽ lại cùng đường cong bằng CSS (poly-team/dev/_mod-chuyen-moi.js).

Nguồn kiểu (tim): 1) bản chép trong kế hoạch (plan["chuyen_moi"][id], app chép lúc lưu -> kho sửa sau vẫn dựng y hệt),
2) Kho effect: thư mục POLY_KHO_EFFECT/chuyen-canh/*.json (đè bản gói theo id), 3) bản gói sẵn engine/chuyen-canh/*.json.
File hỏng / "loai" lạ / thiếu khoá: bỏ qua (ghi stderr), không làm hỏng lần dựng.

Dựng 1 chỗ nối (dung_cho_noi, dung_may_chu.build gọi): d giây cuối file cảnh trước + d giây đầu file cảnh sau (như xfade: 2 cảnh
chồng d giây) -> numpy + OpenCV (có trong engine/.venv) vẽ từng khung -> mã hoá qua ma_hoa (card nếu bật, lỗi thì CPU); đọc file
cảnh có -hwaccel (ma_hoa.vao, lỗi thì CPU). Mờ chuyển động thật: nhiều mẫu tiến độ trong "màn trập", trộn với bản nét theo tốc độ
từng vùng (zoom / xoay: tâm nét, mép mờ toả / mờ xoay; lia: mờ đều theo hướng). Số đo px (mo, bo_goc) tính ở khung 1080 ngang,
bản nháp (540) tự quy đổi.
Phần đường cong / tìm kiểu không cần numpy (ke_hoach, app import nhẹ); numpy + OpenCV chỉ nạp khi dựng (_nap).

Dùng (thử 1 chỗ nối):
  python chuyen_moi.py <id | file.json> <A.mkv> <giây A kết thúc> <B.mkv> <giây B bắt đầu> <ra.mkv> [--d 0.4] [--w 1080 --h 1920 --fps 30]
  python chuyen_moi.py --ds        in danh sách kiểu đang có (id, giây, nguồn, tên)
Mã Poly tự viết (CC0). Không dùng tài nguyên ngoài: màu / hình đều tự vẽ bằng mã.
"""
import copy, json, math, os, subprocess, sys, threading, time

E = os.path.dirname(os.path.abspath(__file__))
GOI = os.path.join(E, "chuyen-canh")   # kiểu gói sẵn trong engine
LOAI = "poly-chuyen-1"
TRON = ("cat", "phu", "sang")
np = cv2 = None   # nạp khi dựng (_nap)


def _nap():
    global np, cv2
    if np is None:
        import numpy as _np
        import cv2 as _cv2
        _cv2.setNumThreads(max(1, min(4, os.cpu_count() or 2)))
        np, cv2 = _np, _cv2


# ------------------------------------------------------------------ kiểu: đọc / kiểm / tìm
def hop_le(s, id_=None):
    """Kiểu dựng được bằng bộ đọc này? (loai đúng, giây là số, tron biết, A / B là dict, lop là list, đường cong đọc được)."""
    if not isinstance(s, dict) or s.get("loai") != LOAI or not isinstance(s.get("id"), str):
        return False
    if id_ is not None and s["id"] != id_:
        return False
    try:
        g = float(s.get("giay"))
    except (TypeError, ValueError):
        return False
    if not 0.05 <= g <= 3.0 or s.get("tron", "cat") not in TRON:
        return False
    if not all(isinstance(s.get(k, {}), dict) for k in ("A", "B")) or not isinstance(s.get("lop", []), list):
        return False
    try:
        for b in (s.get("A") or {}, s.get("B") or {}):
            for k, tr in b.items():
                if k not in ("vien", "bong_lech"):
                    for p in (0.0, 0.5, 1.0):
                        float(gia_tri(tr, p))
        for l in s.get("lop") or []:
            if not isinstance(l, dict) or not isinstance(l.get("kieu"), str):
                return False
            float(gia_tri(l.get("manh"), 0.5))
    except Exception:  # noqa: BLE001  đường cong hỏng
        return False
    return True


def _doc_thu_muc(d, nguon):
    out = {}
    try:
        ten = sorted(f for f in os.listdir(d) if f.endswith(".json") and not f.startswith(("_", ".")))
    except OSError:
        return out
    for f in ten:
        try:
            s = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except (OSError, ValueError) as e:
            sys.stderr.write("[chuyen_moi] bỏ qua %s: %s\n" % (f, str(e)[:120]))
            continue
        if hop_le(s, f[:-5]):
            s["_nguon"] = nguon
            out[s["id"]] = s
        else:
            sys.stderr.write("[chuyen_moi] bỏ qua %s: không đúng dạng %s\n" % (f, LOAI))
    return out


def thu_muc_kho():
    """Kho effect (Drive): POLY_KHO_EFFECT/chuyen-canh. Chưa đặt / không có thư mục -> None (chỉ dùng bản gói)."""
    k = (os.environ.get("POLY_KHO_EFFECT") or "").strip()
    d = os.path.join(k, "chuyen-canh") if k else ""
    return d if d and os.path.isdir(d) else None


_DS = {"khoa": None, "ds": {}}


def tat_ca():
    """{id: kiểu} = bản gói + Kho effect đè theo id (đọc lại khi thư mục đổi)."""
    kho = thu_muc_kho()
    khoa = []
    for d in (GOI, kho):
        try:
            khoa.append((d, os.path.getmtime(d), len(os.listdir(d))) if d else None)
        except OSError:
            khoa.append(None)
    if _DS["khoa"] != khoa:
        ds = _doc_thu_muc(GOI, "goi")
        if kho:
            ds.update(_doc_thu_muc(kho, "kho"))
        _DS.update(khoa=khoa, ds=ds)
    return _DS["ds"]


def tim(id_, plan=None):
    """Kiểu theo id: bản chép trong kế hoạch (nếu đúng dạng) > kho > gói. Không có -> None. Trả bản sao."""
    if not isinstance(id_, str) or not id_:
        return None
    chep = ((plan or {}).get("chuyen_moi") or {}).get(id_) if isinstance(plan, dict) and isinstance(plan.get("chuyen_moi"), dict) else None
    if hop_le(chep, id_):
        return copy.deepcopy(chep)
    s = tat_ca().get(id_)
    return copy.deepcopy(s) if s else None


def la_moi(id_):
    return isinstance(id_, str) and id_ in tat_ca()


def ban_chep(s):
    """Bản chép vào kế hoạch: bỏ khoá nội bộ (_nguon...)."""
    return {k: v for k, v in s.items() if not k.startswith("_")}


# ------------------------------------------------------------------ easing + đường cong (không cần numpy)
def _ease(ten, t):
    t = min(1.0, max(0.0, t))
    if ten in (None, "", "lin"):
        return t
    if ten == "outback" or ten.startswith("outback"):
        s = float(ten[7:] or 1.4)
        u = t - 1
        return 1 + (s + 1) * u ** 3 + s * u ** 2
    if ten.endswith("expo"):
        k = ten[:-4]
        f_in = lambda x: 0.0 if x <= 0 else 2 ** (10 * x - 10)
        if k == "in":
            return f_in(t)
        if k == "out":
            return 1 - f_in(1 - t)
        return f_in(2 * t) / 2 if t < 0.5 else 1 - f_in(2 - 2 * t) / 2
    if ten.endswith("sine"):
        k = ten[:-4]
        if k == "in":
            return 1 - math.cos(t * math.pi / 2)
        if k == "out":
            return math.sin(t * math.pi / 2)
        return -(math.cos(math.pi * t) - 1) / 2
    k, n = ten[:-1], int(ten[-1])  # in3 / out3 / io3 ...
    if k == "in":
        return t ** n
    if k == "out":
        return 1 - (1 - t) ** n
    return (2 ** (n - 1)) * t ** n if t < 0.5 else 1 - ((-2 * t + 2) ** n) / 2


def gia_tri(tr, p, mac_dinh=0.0):
    """Đường cong: số | [[p, v], [p, v, "easing"], ...] | {"keys": [...], "rung": {...}}. Ngoài khoảng: giữ đầu / cuối."""
    if tr is None:
        return mac_dinh
    if isinstance(tr, (int, float)):
        return float(tr)
    if isinstance(tr, dict):
        v = gia_tri(tr.get("keys"), p, mac_dinh)
        r = tr.get("rung")
        if r and p >= r.get("tu", 0):
            u = (p - r.get("tu", 0)) / max(1e-6, r.get("den", 1) - r.get("tu", 0))
            if u <= 1:
                v += r["bien_do"] * math.exp(-r.get("tat", 4) * u) * math.sin(2 * math.pi * r.get("so_lan", 2) * u + r.get("pha", 0))
        return v
    if p <= tr[0][0]:
        return float(tr[0][1])
    for i in range(1, len(tr)):
        if p <= tr[i][0]:
            p0, v0 = tr[i - 1][0], tr[i - 1][1]
            p1, v1 = tr[i][0], tr[i][1]
            e = tr[i][2] if len(tr[i]) > 2 else "io2"
            return v0 + (v1 - v0) * _ease(e, (p - p0) / max(1e-9, p1 - p0))
    return float(tr[-1][1])



# ------------------------------------------------------------------ dựng (numpy + OpenCV, nạp bằng _nap)
def hex_bgr(h):
    h = h.lstrip("#")
    return np.array([int(h[4:6], 16), int(h[2:4], 16), int(h[0:2], 16)], np.float32)


# ------------------------------------------------------------------ biến hình 1 bên
def ma_tran(b, p, W, H):
    """Ma trận 3x3 (toạ độ khung ra, px) cho bên b (dict đường cong) ở tiến độ p."""
    z = gia_tri(b.get("zoom"), p, 1.0)
    gx, gy = gia_tri(b.get("gian_x"), p, 1.0), gia_tri(b.get("gian_y"), p, 1.0)
    th = math.radians(gia_tri(b.get("xoay"), p, 0.0))
    fy, fx = math.radians(gia_tri(b.get("lat_y"), p, 0.0)), math.radians(gia_tri(b.get("lat_x"), p, 0.0))
    x, y = gia_tri(b.get("x"), p, 0.0) * W, gia_tri(b.get("y"), p, 0.0) * H
    cx, cy = W / 2, H / 2
    T1 = np.array([[1, 0, -cx], [0, 1, -cy], [0, 0, 1]], np.float64)
    S = np.diag([z * gx, z * gy, 1.0])
    c, s = math.cos(th), math.sin(th)
    R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float64)
    f = 2.0 * W  # tiêu cự lật 3D
    P = np.eye(3)
    if fy:
        P = np.array([[math.cos(fy), 0, 0], [0, 1, 0], [math.sin(fy) / f, 0, 1]]) @ P
    if fx:
        P = np.array([[1, 0, 0], [0, math.cos(fx), 0], [0, math.sin(fx) / f, 1]]) @ P
    T2 = np.array([[1, 0, cx + x], [0, 1, cy + y], [0, 0, 1]], np.float64)
    return T2 @ P @ R @ S @ T1


def _diem(M, W, H):
    pts = np.array([[0, 0, 1], [W, 0, 1], [0, H, 1], [W, H, 1], [W / 2, H / 2, 1]], np.float64).T
    q = M @ pts
    w = np.where(np.abs(q[2]) < 1e-6, 1e-6, q[2])
    return (q[:2] / w).T


def _vien(ten):
    return {"guong": cv2.BORDER_REFLECT_101, "keo": cv2.BORDER_REPLICATE}.get(ten, cv2.BORDER_CONSTANT)


class Ben:
    """1 bên (A hoặc B) của 1 khung: ảnh gốc + bản thu nhỏ (cache) + mặt nạ bo góc."""

    def __init__(self, img, spec_ben):
        self.img, self.b = img, spec_ben or {}
        self.vien = self.b.get("vien", "guong")
        self.cache = {}
        self.memo = {}
        self.q_co_dinh = None  # bên gần như đứng yên trong màn trập: vẽ 1 lần ở tiến độ này, các mẫu dùng lại

    def nho_bo(self, k, r):
        """Ảnh gốc cỡ k có alpha, bo góc bán kính r (px ở cỡ k), màu đã nhân alpha. Cache theo (k, r)."""
        key = ("bo", k, r)
        if key not in self.cache:
            src = self.nho(k).copy()
            h, w = src.shape[:2]
            m = np.zeros((h, w), np.uint8)
            cv2.rectangle(m, (r, 0), (w - 1 - r, h - 1), 255, -1)
            cv2.rectangle(m, (0, r), (w - 1, h - 1 - r), 255, -1)
            for cx_, cy_ in ((r, r), (w - 1 - r, r), (r, h - 1 - r), (w - 1 - r, h - 1 - r)):
                cv2.circle(m, (cx_, cy_), r, 255, -1, lineType=cv2.LINE_AA)
            src[..., 3] = m
            src[..., :3] = cv2.multiply(src[..., :3], cv2.merge([m, m, m]), scale=1 / 255.0)
            self.cache[key] = src
        return self.cache[key]

    def nen(self, spec, k, W, H):
        key = ("nen", k)
        if key not in self.cache:
            self.cache[key] = _nen(spec, self.img, k, W, H)
        return self.cache[key]

    def nho(self, k):
        if k not in self.cache:
            H, W = self.img.shape[:2]
            im = self.img if k == 1 else cv2.resize(self.img, (round(W * k), round(H * k)), interpolation=cv2.INTER_AREA)
            if self.vien == "trong":  # thêm kênh alpha (để biết chỗ trống sau khi biến hình)
                im = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
            self.cache[k] = im
        return self.cache[k]

    def ve(self, p, k, W, H):
        """-> (màu float32 đã nhân alpha, alpha float32 hoặc None, M) ở cỡ (W*k, H*k). Nhớ theo (tiến độ, k)."""
        if self.q_co_dinh is not None:
            p = self.q_co_dinh
        key = (round(p, 5), k)
        if key not in self.memo:
            self.memo[key] = self._ve(p, k, W, H)
        return self.memo[key]

    def _ve(self, p, k, W, H):
        b = self.b
        M = ma_tran(b, p, W, H)
        Sk = np.diag([k, k, 1.0])
        Mk = Sk @ M @ np.linalg.inv(Sk)
        src = self.nho(k)
        bo = int(gia_tri(b.get("bo_goc"), p, 0.0) * k * W / 1080.0)   # px ở khung 1080 ngang
        if bo >= 1 and src.shape[2] == 4:
            src = self.nho_bo(k, bo)
        dsz = (round(W * k), round(H * k))
        flags = cv2.INTER_LINEAR
        bm = _vien(self.vien)
        if abs(Mk[2, 0]) > 1e-12 or abs(Mk[2, 1]) > 1e-12:
            out = cv2.warpPerspective(src, Mk, dsz, flags=flags, borderMode=bm, borderValue=(0, 0, 0, 0))
        else:
            out = cv2.warpAffine(src, Mk[:2], dsz, flags=flags, borderMode=bm, borderValue=(0, 0, 0, 0))
        out = out.astype(np.float32)
        if out.shape[2] == 4:
            a = out[..., 3] / 255.0
            col = out[..., :3]  # mép đã trộn với nền 0 -> coi như đã nhân alpha
        else:
            a, col = None, out
        # mờ / tối / sáng của riêng bên này
        mo = gia_tri(b.get("mo"), p, 0.0) * k * W / 1080.0   # px ở khung 1080 ngang
        if mo > 0.3:
            col = _mo(col, mo)
            if a is not None:
                a = _mo(a, mo)
        toi = gia_tri(b.get("toi"), p, 0.0)
        if toi > 0:
            col = col * (1 - toi)
        sang = gia_tri(b.get("sang"), p, 0.0)
        if sang > 0:
            col = col + ((255.0 if a is None else a[..., None] * 255.0) - col) * sang
        tr = gia_tri(b.get("trong"), p, 1.0)
        if tr < 1:
            col = col * tr
            a = (np.full(col.shape[:2], tr, np.float32) if a is None else a * tr)
        return col, a, M


def _mo(x, sigma):
    """Mờ Gauss nhanh: sigma lớn thì thu nhỏ -> mờ -> phóng lại."""
    if sigma < 6:
        return cv2.GaussianBlur(x, (0, 0), sigma)
    f = max(1, int(sigma // 3))
    h, w = x.shape[:2]
    s = cv2.resize(x, (max(1, w // f), max(1, h // f)), interpolation=cv2.INTER_AREA)
    s = cv2.GaussianBlur(s, (0, 0), sigma / f)
    return cv2.resize(s, (w, h), interpolation=cv2.INTER_LINEAR)


# ------------------------------------------------------------------ ghép 1 mẫu (1 tiến độ)
def _nen(spec, img, k, W, H):
    n = spec.get("nen") or {}
    w, h = round(W * k), round(H * k)
    if n.get("kieu") == "mau":
        return np.broadcast_to(hex_bgr(n.get("mau", "#074D3A")), (h, w, 3)).astype(np.float32)
    s = cv2.resize(img, (max(1, W // 16), max(1, H // 16)), interpolation=cv2.INTER_AREA).astype(np.float32)
    s = cv2.GaussianBlur(s, (0, 0), 3)
    return cv2.resize(s, (w, h), interpolation=cv2.INTER_LINEAR) * (1 - n.get("toi", 0.45))


def _bong(a, p, b, k):
    """Bóng mềm của bên B (theo alpha), lệch về phía sau hướng chuyển động."""
    st = gia_tri(b.get("bong"), p, 0.0)
    if st <= 0 or a is None:
        return None
    h, w = a.shape
    sig = max(2.0, 0.035 * w)
    dx, dy = b.get("bong_lech", [0, -0.012])
    m = cv2.warpAffine(a, np.float32([[1, 0, dx * w], [0, 1, dy * h]]), (w, h), borderMode=cv2.BORDER_CONSTANT)
    return _mo(m, sig) * st * 0.75


def ghep_mau(spec, A, B, p, k, W, H):
    """1 khung ở tiến độ p, cỡ k (chưa có lớp phủ). A, B: Ben."""
    tron = spec.get("tron", "cat")
    if tron == "cat":
        cat = spec.get("cat_tai", 0.5)
        ben = A if p < cat else B
        col, a, _ = ben.ve(p, k, W, H)
        if a is not None:
            col = col + ben.nen(spec, k, W, H) * (1 - a[..., None])
        return col
    colA, aA, _ = A.ve(p, k, W, H)
    if aA is not None:
        colA = colA + A.nen(spec, k, W, H) * (1 - aA[..., None])
    if tron == "sang":  # B hiện dần từ chỗ SÁNG nhất (luma fade)
        mem = spec.get("mem", 0.25)
        e = gia_tri(spec.get("nguong"), p, p)
        th = 1 + mem - e * (1 + 2 * mem)
        colB, _, _ = B.ve(p, k, W, H)
        L = cv2.cvtColor(np.clip(colB, 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        L = cv2.GaussianBlur(cv2.resize(L, (L.shape[1] // 4, L.shape[0] // 4), interpolation=cv2.INTER_AREA), (0, 0), 2)
        L = cv2.resize(L, (colB.shape[1], colB.shape[0])).astype(np.float32) / 255.0
        u = np.clip((L - (th - mem)) / (2 * mem), 0, 1)
        a = u * u * (3 - 2 * u)
        return colB * a[..., None] + colA * (1 - a[..., None])
    # "phu": B đè lên A theo alpha của B (trong suốt / chỗ trống sau biến hình)
    colB, aB, _ = B.ve(p, k, W, H)
    if aB is None:
        return colB
    kb = ("bong", k)  # bóng không cần mờ chuyển động: tính 1 lần mỗi khung (mẫu đầu), các mẫu sau dùng lại
    if kb not in B.cache:
        B.cache[kb] = _bong(aB, p, B.b, k)
    sh = B.cache[kb]
    if sh is not None:
        colA = colA * (1 - sh[..., None])
    return colB + colA * (1 - aB[..., None])


# ------------------------------------------------------------------ lớp phủ (cỡ thật)
def _lop(spec, f, p, W, H, rng):
    for l in spec.get("lop", []):
        kieu = l["kieu"]
        s = gia_tri(l.get("manh"), p, 0.0)
        if s <= 1e-4:
            continue
        if kieu == "chop":  # chớp sáng: đẩy sáng + loé (bloom)
            c = hex_bgr(l.get("mau", "#FFFFFF"))
            loe = l.get("loe", 0.0)
            if loe:
                bl = _mo(f, 0.03 * W)
                f = 255 - (255 - f) * (1 - np.clip(bl / 255.0 * loe * s, 0, 1))
            f = f + (c - f) * s
        elif kieu == "vet_sang":  # vệt sáng tự vẽ: vài đốm Gauss màu ấm trôi chéo, trộn kiểu screen
            f = _vet_sang(f, p, s, l, W, H)
        elif kieu == "tach_mau":  # tách kênh R / B ngược chiều
            a = s * W
            b_, g_, r_ = cv2.split(f)
            r_ = cv2.warpAffine(r_, np.float32([[1, 0, -a], [0, 1, 0]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
            b_ = cv2.warpAffine(b_, np.float32([[1, 0, a], [0, 1, a * 0.25]]), (W, H), borderMode=cv2.BORDER_REPLICATE)
            f = cv2.merge([b_, g_, r_])
        elif kieu == "soc":  # vài dải ngang lệch (glitch nhẹ), cố định theo hạt giống
            n = l.get("so_dai", 5)
            r2 = np.random.default_rng(l.get("hat", 7) + int(p * 6))
            f = f.copy()
            for _ in range(n):
                y0 = int(r2.uniform(0.05, 0.9) * H)
                h = int(r2.uniform(0.01, 0.06) * H)
                dx = int(r2.uniform(-1, 1) * s * l.get("lech", 0.06) * W)
                if dx > 0:  # dời dải, mép lấp bằng cột biên (không cuộn vòng)
                    f[y0:y0 + h, dx:] = f[y0:y0 + h, :-dx].copy()
                    f[y0:y0 + h, :dx] = f[y0:y0 + h, dx:dx + 1]
                elif dx < 0:
                    f[y0:y0 + h, :dx] = f[y0:y0 + h, -dx:].copy()
                    f[y0:y0 + h, dx:] = f[y0:y0 + h, dx - 1:dx]
        elif kieu == "rem":  # chớp mắt: 2 mép đen khép từ trên / dưới, mép mềm
            fe = l.get("mem", 0.08) * H
            y = np.arange(H, dtype=np.float32)
            d = np.minimum(y, H - 1 - y)  # khoảng cách tới mép gần nhất
            mep = s * (H / 2 + fe)
            m = np.clip((mep - d) / fe, 0, 1)
            m = m * m * (3 - 2 * m)
            f = f * (1 - m)[:, None, None] + hex_bgr(l.get("mau", "#000000")) * m[:, None, None]
    return f


def _vet_sang(f, p, s, l, W, H):
    w, h = 90, 160
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xx /= w
    yy /= h
    acc = np.zeros((h, w, 3), np.float32)
    mau = l.get("mau", ["#FFD27A", "#FFF1CC", "#FFB547"])
    goc = math.radians(l.get("goc", 35))
    ux, uy = math.cos(goc), math.sin(goc)
    for i, m in enumerate(mau):
        t = p * 1.3 - 0.15 + i * 0.12
        cx, cy = 0.5 + (t - 0.5) * ux * 1.6, 0.5 + (t - 0.5) * uy * 1.6
        rx, ry = l.get("rong", 0.16) + 0.06 * i, l.get("dai", 0.55) + 0.1 * i  # dải sáng: hẹp theo hướng trôi, dài vuông góc
        # đốm elip kéo dài theo hướng trôi
        dx, dy = xx - cx, (yy - cy) * (H / W)
        u = dx * ux + dy * uy
        v = -dx * uy + dy * ux
        g = np.exp(-(u * u) / (2 * rx * rx) - (v * v) / (2 * ry * ry))
        acc += g[..., None] * (hex_bgr(m) / 255.0)[None, None, :] * (0.9 - 0.15 * i)
    acc = np.clip(acc * s, 0, 1)
    L = cv2.resize(acc, (W, H), interpolation=cv2.INTER_CUBIC)
    return 255 - (255 - f) * (1 - L)  # screen


# ------------------------------------------------------------------ 1 khung ra (có mờ chuyển động)
GW, GH = 12, 21  # lưới đo tốc độ từng vùng


def _dich(b, p, h, W, H):
    """Quãng dời (px, cỡ thật) trong màn trập [p-h, p+h] của nội dung đang nằm ở từng ô lưới khung ra (GH x GW)."""
    gx, gy = np.meshgrid((np.arange(GW) + 0.5) * W / GW, (np.arange(GH) + 0.5) * H / GH)
    u = np.stack([gx.ravel(), gy.ravel(), np.ones(GW * GH)])
    try:
        s = np.linalg.inv(ma_tran(b, p, W, H)) @ u
    except np.linalg.LinAlgError:
        return np.zeros((GH, GW))
    q = []
    for t in (max(0.0, p - h), min(1.0, p + h)):
        x = ma_tran(b, t, W, H) @ s
        w = np.where(np.abs(x[2]) < 1e-6, 1e-6, x[2])
        q.append(x[:2] / w)
    return np.hypot(*(q[1] - q[0])).reshape(GH, GW)


def _alpha_nho(B, p, W, H):
    """Độ phủ của bên B ở lưới đo (GH x GW): B vẽ đè lên A bao nhiêu."""
    tr = gia_tri(B.b.get("trong"), p, 1.0)
    if B.vien != "trong":
        return np.full((GH, GW), tr)
    m = np.full((GH * 4, GW * 4), 255, np.uint8)
    k = GW * 4 / W
    Sk = np.diag([k, k, 1.0])
    Mk = Sk @ ma_tran(B.b, p, W, H) @ np.linalg.inv(Sk)
    o = cv2.warpPerspective(m, Mk, (GW * 4, GH * 4), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return cv2.resize(o, (GW, GH), interpolation=cv2.INTER_AREA) / 255.0 * tr


def ban_do_toc_do(spec, A, B, p, h, W, H):
    """Bản đồ quãng dời (GH x GW, px) của khung ghép: theo bên đang hiện ở từng vùng."""
    tron = spec.get("tron", "cat")
    if tron == "cat":
        cat = spec.get("cat_tai", 0.5)
        ds = []
        if p - h < cat:
            ds.append(_dich(A.b, min(p, cat - 1e-4), h, W, H))
        if p + h >= cat:
            ds.append(_dich(B.b, max(p, cat), h, W, H))
        return np.maximum.reduce(ds) if len(ds) > 1 else ds[0]
    dA, dB = _dich(A.b, p, h, W, H), _dich(B.b, p, h, W, H)
    if tron == "sang":
        return np.maximum(dA, dB)
    a = _alpha_nho(B, p, W, H)
    return dB * a + dA * (1 - a)


def khung(spec, imA, imB, p, dp, W, H, rng=None, dem=None):
    """1 khung ra. Mờ chuyển động: n mẫu tiến độ trong màn trập, ghép ở cỡ nhỏ (k) rồi phóng lại; trộn với bản nét theo
    tốc độ TỪNG VÙNG (zoom / xoay: tâm gần như đứng yên nên vẫn nét, mép mờ toả / mờ xoay; lia: mờ đều cả khung)."""
    A, B = Ben(imA, spec.get("A")), Ben(imB, spec.get("B"))
    mcd = spec.get("mo_chuyen_dong", 0.7)  # màn trập (phần của 1 khung)
    n, dmap = 1, None
    if mcd > 0:
        h = mcd * dp / 2
        dmap = ban_do_toc_do(spec, A, B, p, h, W, H)
        n = int(min(16, max(1, math.ceil(float(dmap.max()) * 1080.0 / W / 12.0))))   # ngưỡng tính ở khung 1080
        if n > 2:
            for ben in (A, B):  # bên gần như đứng yên (< 3 px trong màn trập): vẽ 1 lần cho mọi mẫu
                if float(_dich(ben.b, p, h, W, H).max()) < 3.0:
                    ben.q_co_dinh = p
    if n <= 2:
        f = ghep_mau(spec, A, B, p, 1, W, H)
    else:
        k = 0.5 if n <= 5 else 0.375 if n <= 10 else 0.25
        acc = None
        for j in range(n):
            q = min(1.0, max(0.0, p + (j / (n - 1) - 0.5) * mcd * dp))
            x = ghep_mau(spec, A, B, q, k, W, H)
            acc = x if acc is None else acc + x
        acc /= n
        buoc = float(dmap.max()) / (n - 1) * k  # khoảng giữa 2 mẫu (px ở cỡ k): làm mềm vệt bậc thang
        if buoc > 2:
            acc = cv2.GaussianBlur(acc, (0, 0), buoc * 0.35)
        mo = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
        if float(dmap.min()) >= 16:  # cả khung chạy nhanh: không cần bản nét
            f = mo
        else:
            u = np.clip((dmap - 3.0) / 13.0, 0, 1)
            w = cv2.resize((u * u * (3 - 2 * u)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
            w = np.clip(w, 0, 1)[..., None]
            net = ghep_mau(spec, A, B, p, 1, W, H)
            f = net + (mo - net) * w
    if dem is not None:
        dem.append(n)
    f = _lop(spec, f, p, W, H, rng)
    return np.clip(f, 0, 255).astype(np.uint8)


# ------------------------------------------------------------------ đọc / ghi khung bằng ffmpeg (qua ma_hoa: card -> lỗi thì CPU)
def _ff():
    try:
        from chung import FFMPEG
        return FFMPEG
    except Exception:  # noqa: BLE001  chạy rời (dev): ffmpeg trong PATH
        return os.environ.get("POLY_FFMPEG", "ffmpeg")


def _ma_hoa():
    try:
        import ma_hoa
        return ma_hoa
    except Exception:  # noqa: BLE001
        return None


def _chay_ra(cmd):
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **({"creationflags": 0x08000000} if os.name == "nt" else {}))
    if r.returncode:
        raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-400:])
    return r.stdout


def doc_khung(path, t0, n, W, H, fps):
    """n khung W×H (bgr24) của file từ giây t0. Giải mã bằng card nếu ma_hoa bật (lỗi thì chạy lại bằng CPU)."""
    _nap()
    MH = _ma_hoa()
    vao = MH.vao() if MH else []
    cmd = [_ff(), "-v", "error", "-ss", f"{max(0.0, t0):.4f}"] + vao + [
        "-i", path, "-frames:v", str(n), "-an", "-vf", f"fps={fps},scale={W}:{H}:flags=bicubic,setsar=1",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = MH.chay_gm(cmd, _chay_ra) if MH and vao else _chay_ra(cmd)
    sz = W * H * 3
    ks = [np.frombuffer(raw[i * sz:(i + 1) * sz], np.uint8).reshape(H, W, 3) for i in range(len(raw) // sz)]
    if not ks:
        raise RuntimeError("không đọc được khung " + os.path.basename(path))
    while len(ks) < n:  # file ngắn hơn: giữ khung cuối
        ks.append(ks[-1])
    return ks[:n]


def so_khung(d, fps):
    """Số khung của đoạn chuyển d giây (ke_hoach đã làm tròn d theo khung)."""
    return max(2, int(round(d * fps)))


def dung_cho_noi(spec, a_path, a_het, b_path, b_dau, out, d=None, W=1080, H=1920, fps=30, crf=16, tmp=None, preset="ultrafast"):
    """Đoạn chuyển d giây = d giây cuối A (kết thúc ở a_het) + d giây đầu B (từ b_dau) -> file hình (không tiếng) W×H, fps.
    Mã hoá qua ma_hoa.chay (card nếu bật, lỗi thì CPU; crf như file cảnh, CPU preset ultrafast: đoạn tạm, bản cuối nén lại). Khung vẽ ghi tạm ra đĩa (<ra>.raw) để làm lại
    được bằng CPU, xong xoá. Trả dict số đo."""
    _nap()
    spec = doc_spec(spec)
    d = float(d or spec.get("giay", 0.4))
    n = so_khung(d, fps)
    t0 = time.time()
    kq = {}

    def doc_b():
        try:
            kq["b"] = doc_khung(b_path, b_dau, n, W, H, fps)
        except Exception as e:  # noqa: BLE001
            kq["loi"] = e
    th = threading.Thread(target=doc_b)
    th.start()
    try:
        KA = doc_khung(a_path, a_het - n / fps, n, W, H, fps)
    finally:
        th.join()
    if "b" not in kq:
        raise RuntimeError("không đọc được cảnh sau: %s" % kq.get("loi"))
    KB = kq.pop("b")
    t1 = time.time()
    dem = []
    raw = os.path.join(tmp or os.path.dirname(os.path.abspath(out)), os.path.basename(out) + ".raw")
    try:
        with open(raw, "wb") as fo:
            for i in range(n):
                fo.write(khung(spec, KA[i], KB[i], (i + 0.5) / n, 1.0 / n, W, H, None, dem).tobytes())
        del KA, KB
        t2 = time.time()
        vao = [_ff(), "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", raw]
        MH = _ma_hoa()
        if MH:
            enc = MH.chay(lambda v: vao + v + ["-an", out], _chay_ra, crf=crf, preset=preset)
        else:
            _chay_ra(vao + ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-an", out])
            enc = "libx264"
    finally:
        try:
            os.remove(raw)
        except OSError:
            pass
    t3 = time.time()
    return {"id": spec.get("id"), "d": d, "khung": n, "giay": round(t3 - t0, 2), "giay_doc": round(t1 - t0, 2),
            "giay_ve": round(t2 - t1, 2), "giay_ma_hoa": round(t3 - t2, 2), "ma_hoa": enc,
            "mau_toi_da": max(dem), "mau_tb": round(sum(dem) / len(dem), 1)}


def doc_spec(x):
    if isinstance(x, dict):
        return x
    if x.endswith(".json"):
        return json.load(open(x, encoding="utf-8"))
    s = tim(x)
    if not s:
        raise SystemExit("không có kiểu chuyển cảnh " + x)
    return s


def main():
    if "--ds" in sys.argv:
        for k, s in sorted(tat_ca().items()):
            print(f"{k:16s} {s.get('giay'):5} {s.get('_nguon')}  {s.get('ten')}")
        return
    a = [x for i, x in enumerate(sys.argv[1:], 1) if not x.startswith("--") and not sys.argv[i - 1].startswith("--")]
    opt = lambda k, dv: type(dv)(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else dv
    spec, A, ta, B, tb, out = a[0], a[1], float(a[2]), a[3], float(a[4]), a[5]
    r = dung_cho_noi(spec, A, ta, B, tb, out, d=opt("--d", 0.0) or None, W=opt("--w", 1080), H=opt("--h", 1920), fps=opt("--fps", 30))
    print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
