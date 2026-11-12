# -*- coding: utf-8 -*-
"""POLY Cut — 2 chức năng HÌNH (4/11/2026) chạy bằng Python của BỘ DỰNG (engine/.venv: numpy + máy nghe sherpa). App gọi qua hinh.py:

  python hinh_may.py chia <viec.json>   TỰ CHIA CẢNH: tìm chỗ cắt trong các cảnh đã chọn
      - chỗ ngừng nói: năng lượng tiếng mỗi 10 ms (ke_hoach.bao_bien) + mốc từng chữ của máy nghe (sua_tay_may._nghe_clip, cùng
        bộ nhớ đệm với "Tạo phụ đề từ lời nói" nên clip đã nghe rồi thì không nghe lại);
      - chỗ đổi góc máy: điểm "scene" của ffmpeg trên bản xem nhẹ (proxy) — đang nói thì dời về khoảng lặng gần nhất (±0,8s),
        không có thì KHÔNG chia (báo lại);
      - luật (học từ video-use, MIT, mục Hard Rules): không bao giờ cắt giữa chữ, mép cắt chừa ≥ 0,12s (0,12–0,2s) tới tiếng nói,
        ưu tiên khoảng lặng dài; mỗi cảnh con ≥ 0,8s;
      - tuỳ chọn tach_im: đoạn im lặng dài (≥ 1,2s giữa 2 câu, ≥ 1s đầu / cuối cảnh) tách thành cảnh riêng + đánh dấu để anh xoá
        nhanh (KHÔNG tự xoá).
  python hinh_may.py mau <viec.json>    TỰ CHỈNH MÀU: đo 5 khung mỗi cảnh (bản xem nhẹ, đã chuyển HDR -> SDR như bản xuất) ->
      canh.mau {sang, tuong_phan, bao_hoa, nhiet} (khoá đã có, dung_may_chu.mau_canh): đèn vàng về gần trung tính (giữ ~1/4 độ ấm),
      tối thì sáng lên (giữ điểm đen), không tăng độ đậm màu quá 12%. Ước rồi DỰNG THỬ đúng chuỗi eq + colortemperature của bộ dựng
      trên các khung đó, đo lại, chỉnh độ sáng thêm 1 lượt (khỏi lệch vì eq làm trên YUV còn nhiệt màu làm trên RGB).

In ra: BUOC=<chữ> (tiến độ) · CANH_BAO=[…] · XONG={json} · LOI=<chữ>.
"""
import contextlib, hashlib, json, math, os, re, subprocess, sys, traceback
from concurrent.futures import ThreadPoolExecutor

APP = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP)
import sua_tay_may as M  # noqa: E402  (đưa engine vào sys.path: chung, ke_hoach, nghe)
import chung  # noqa: E402
import ke_hoach as KH  # noqa: E402
import numpy as np  # noqa: E402

KW = {"creationflags": 0x08000000} if os.name == "nt" else {}
FPS = 30.0

# ------------------------------------------------------------------ chung
def in_(s):
    print(s, flush=True)


def doc(p, mac=None):
    return M.doc(p, mac)


def ghi(p, o):
    M.ghi(p, o)


def khoa_tep(p, them=""):
    st = os.stat(p)
    return hashlib.md5(("%s|%s|%s|%s" % (p, st.st_size, int(st.st_mtime), them)).encode("utf-8")).hexdigest()


# ================================================================== TỰ CHIA CẢNH
PAD = 0.12          # mép cắt chừa tối thiểu tới tiếng nói (giây)
PAD_MAX = 0.20      # chừa tối đa trước câu tiếp theo
LANG_MIN = 0.30     # khoảng lặng ngắn nhất để chia
IM_DAI = 1.2        # im lặng dài giữa 2 câu -> tách riêng (tuỳ chọn)
IM_DAU = 1.0        # im lặng đầu / cuối cảnh -> tách riêng (tuỳ chọn)
CANH_MIN = 0.8      # cảnh con ngắn nhất
GOC_NGUONG = 0.30   # điểm đổi cảnh ffmpeg (0..1)
GOC_TIM = 0.8       # đổi góc máy lúc đang nói: tìm khoảng lặng trong ±0,8s


class _Nghe:
    """Máy nghe chỉ mở khi clip chưa có trong bộ nhớ đệm (mở mất vài giây)."""
    def __init__(self, md):
        self.md, self.r = md, None

    def _r(self):
        if self.r is None:
            import nghe as NG
            with contextlib.redirect_stdout(sys.stderr):
                self.r = NG.recognizer(self.md)
        return self.r

    def create_stream(self):
        return self._r().create_stream()

    def decode_stream(self, s):
        return self._r().decode_stream(s)


def tu_cua_clip(src, kho_nghe, may):
    """[[từ, giây, hết, đoạn]] của cả clip (máy nghe sherpa, có bộ nhớ đệm chung với phụ đề) | None nếu không nghe được."""
    if may is None:
        return None
    try:
        return (M._nghe_clip(may, src, kho_nghe) or {}).get("tu") or []
    except Exception as e:  # noqa  clip không có tiếng / máy nghe đổi cách gọi: chỉ dùng năng lượng tiếng
        print("nghe %s: %s" % (src, e), file=sys.stderr)
        return None


def lang_cua(env, nen, noi):
    """Các khoảng lặng [(a, b)] (giây) của cả clip theo năng lượng tiếng: dưới nền + 30% (nói − nền); lỗ < 60 ms trong khoảng lặng
    (tiếng lách cách, hơi thở nhẹ) bỏ qua. Trả cả khoảng ngắn (≥ 0,15s) để dời chỗ đổi góc máy."""
    q = env < nen + 0.3 * (noi - nen)
    runs, i, n = [], 0, len(q)
    while i < n:
        if q[i]:
            j = i
            while j < n and q[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    gop = []
    for a, b in runs:
        if gop and a - gop[-1][1] <= 6:
            gop[-1][1] = b
        else:
            gop.append([a, b])
    return [(a / 100.0, b / 100.0) for a, b in gop if b - a >= 15]


def diem_goc(src, xem, kho):
    """[(giây, điểm)] chỗ đổi góc máy của cả clip (ffmpeg scene trên bản xem nhẹ nếu có), có bộ nhớ đệm."""
    f = xem if xem and os.path.isfile(xem) else src
    cp = os.path.join(kho, "goc-" + khoa_tep(f, "goc2") + ".json")
    cu = doc(cp)
    if isinstance(cu, list):
        return [tuple(x) for x in cu]
    r = subprocess.run([chung.FFMPEG, "-hide_banner", "-nostats", "-i", f, "-an", "-vf",
                        "scale=128:-2,select='gte(scene\\,0)',metadata=print:key=lavfi.scene_score:file=-", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800, **KW)
    ds, t = [], None
    for dong in r.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", dong)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"lavfi\.scene_score=([\d.]+)", dong)
        if m and t is not None:
            ds.append((round(t, 3), float(m.group(1))))
    # đỉnh: ≥ ngưỡng, cao nhất trong ±0,25s, gấp ≥ 3 lần trung vị ±1s (lia máy chậm / rung tay không tính)
    out = []
    if ds:
        tt = np.array([x[0] for x in ds]); sc = np.array([x[1] for x in ds])
        for i in np.where(sc >= GOC_NGUONG)[0]:
            g = (tt >= tt[i] - 0.25) & (tt <= tt[i] + 0.25)
            v = (tt >= tt[i] - 1) & (tt <= tt[i] + 1)
            if sc[i] >= sc[g].max() - 1e-9 and sc[i] >= 3 * max(0.02, float(np.median(sc[v]))):
                out.append((float(tt[i]), round(float(sc[i]), 3)))
    try:
        ghi(cp, out)
    except OSError:
        pass
    return out


def _tg(t):
    m = int(t // 60)
    return "%d:%04.1f" % (m, t - 60 * m)


def chia_mot(c, words, env, goc, tach_im):
    """Chỗ cắt cho 1 cảnh [tu, den] (giờ clip). -> ({"cat": [...], "im": [...]}, [cảnh báo])."""
    tu, den = float(c["tu"]), float(c["den"])
    bao = []
    if den - tu < 2 * CANH_MIN:
        return {"cat": [], "im": []}, bao
    ws = [w for w in (words or []) if tu - 0.05 <= (w[1] + w[2]) / 2 <= den + 0.05]
    env_ok = env is not None and len(env) > 50
    nen = noi = None
    if env_ok:
        nen, noi = KH.muc_noi(env)
        env_ok = noi - nen >= 12.0          # cả clip gần như cùng mức (nhạc / ồn đều): không dựa vào năng lượng
    lang = []
    if env_ok:
        for a, b in lang_cua(env, nen, noi):
            a, b = max(a, tu), min(b, den)
            if b - a < 0.15:
                continue
            # chữ nằm gọn trong khoảng "lặng" mà có tiếng (nói nhỏ dưới ngưỡng): không phải khoảng lặng
            nho = False
            for w in ws:
                if w[1] >= a + 0.05 and w[2] <= b - 0.05:
                    i0, i1 = int(w[1] * 100), max(int(w[1] * 100) + 1, int(w[2] * 100))
                    if float(env[i0:i1].max()) >= nen + 0.18 * (noi - nen):
                        nho = True
                        break
            if not nho:
                lang.append((a, b))
    elif ws:   # không tin được năng lượng: khe giữa 2 chữ của máy nghe (mốc "hết" đã nới ~0,35s sau âm cuối)
        for x, y in zip(ws, ws[1:]):
            if y[1] - x[2] >= 0.2:
                lang.append((x[2], y[1]))
        if ws[0][1] - tu >= 0.3:
            lang.append((tu, ws[0][1]))
        if den - ws[-1][2] >= 0.3:
            lang.append((ws[-1][2], den))
    if env_ok:      # có tiếng nói = năng lượng có đoạn vượt hẳn nền (máy nghe hay "nghe ra chữ" trong tiếng ồn: không tin riêng chữ)
        co_loi = any(float(env[min(len(env) - 1, int(t * 100))]) > nen + 0.5 * (noi - nen) for t in np.arange(tu, den, 0.05))
    else:           # không đọc được tiếng: tin chữ khi có ≥ 3 chữ; tiếng đều đều (ồn / nhạc, không thấy người nói): coi như không nói
        co_loi = env is None and len(ws) >= 3

    def dien(t):   # năng lượng (dB) tại giây t
        return float(env[min(len(env) - 1, max(0, int(round(t * 100))))]) if env_ok else 0.0

    def em_nhat(a, b, uu):   # chỗ êm nhất trong [a, b], gần `uu` (phạt 3 dB / 0,1s lệch)
        if not env_ok or b - a < 0.02:
            return min(max(uu, a), b)
        ts = np.arange(a, b + 1e-6, 0.01)
        diem = np.array([dien(t) for t in ts]) + 30.0 * np.abs(ts - uu)
        return float(ts[int(np.argmin(diem))])

    def sau(t):   # vài chữ ngay sau chỗ cắt (để anh nhận ra chỗ)
        x = [w[0] for w in ws if w[1] >= t - 0.05][:4]
        return " ".join(x)

    def trong_loi(t):   # t có rơi vào tiếng nói không (theo năng lượng; không có thì theo chữ)
        for a, b in lang:
            if a + PAD - 1e-6 <= t <= b - PAD + 1e-6:
                return False
        if lang or env_ok:
            return co_loi
        return any(w[1] - PAD < t < w[2] for w in ws)

    ung = []   # ứng viên: {t, loai, uu, ly_do, cap}
    dau_lang = cuoi_lang = None
    for a, b in lang:
        if a <= tu + 0.1:
            dau_lang = (a, b)
        if b >= den - 0.1:
            cuoi_lang = (a, b)
    # 1) ngừng nói (khoảng lặng nằm giữa 2 đoạn có tiếng)
    if co_loi:
        for a, b in lang:
            if a <= tu + 0.1 or b >= den - 0.1:
                continue
            L = b - a
            if L < LANG_MIN:
                continue
            if tach_im and L >= IM_DAI:
                t1, t2 = a + 0.15, b - 0.18
                ung.append({"t": t1, "loai": "im", "uu": 2 + L / 100, "ly_do": "đầu đoạn im lặng %s" % ("%.1fs" % L).replace(".", ","), "cap": (t1, t2)})
                ung.append({"t": t2, "loai": "im", "uu": 2 + L / 100, "ly_do": "hết đoạn im lặng, bắt đầu nói", "cap": (t1, t2)})
                continue
            padd = min(PAD_MAX, max(PAD, 0.35 * L))
            t = em_nhat(max(a + PAD, b - padd - 0.04), min(b - PAD, b - padd + 0.04), b - padd)
            ung.append({"t": t, "loai": "lang", "uu": 1 + L / 100, "ly_do": "ngừng nói %s" % ("%.1fs" % L).replace(".", ",")})
        # im lặng dài đầu / cuối cảnh
        if tach_im and dau_lang and dau_lang[1] - tu >= IM_DAU and dau_lang[1] < den - 0.3:
            t = dau_lang[1] - 0.18
            ung.append({"t": t, "loai": "im", "uu": 2, "ly_do": "hết đoạn im lặng đầu cảnh", "cap": (tu, t)})
        if tach_im and cuoi_lang and den - cuoi_lang[0] >= IM_DAU and cuoi_lang[0] > tu + 0.3:
            t = cuoi_lang[0] + 0.15
            ung.append({"t": t, "loai": "im", "uu": 2, "ly_do": "đoạn im lặng cuối cảnh", "cap": (t, den)})
    # 2) đổi góc máy
    for g, diem in goc:
        if not (tu + CANH_MIN <= g <= den - CANH_MIN):
            continue
        cap = next((u for u in ung if u.get("cap") and u["cap"][0] - 0.2 <= g <= u["cap"][1] + 0.2), None)
        if cap:   # đổi góc máy giữa đoạn im lặng sẽ tách riêng: 2 mép đoạn im đã là chỗ cắt
            for u in ung:
                if u.get("cap") == cap["cap"] and "đổi góc máy" not in u["ly_do"]:
                    u["ly_do"] += " (có đổi góc máy)"
            continue
        t = g
        if co_loi and trong_loi(g):
            tot = None
            for a, b in lang:
                if b - a < 2 * PAD + 0.02:
                    continue
                x = min(max(g, a + PAD), b - PAD)
                if abs(x - g) <= GOC_TIM and (tot is None or abs(x - g) < abs(tot - g)):
                    tot = x
            if tot is None:
                bao.append("đổi góc máy lúc giây %s của clip nhưng đang nói, không có chỗ lặng gần đó: không chia (chia sẽ cắt giữa chữ)"
                           % _tg(g))
                continue
            t = tot
        ung.append({"t": t, "loai": "goc", "uu": 3 + diem, "ly_do": "đổi góc máy" + ("" if abs(t - g) < 0.05 else " (dời %s về chỗ lặng)"
                                                                                     % ("%.1fs" % abs(t - g)).replace(".", ","))})
    # chỗ đổi góc máy rơi vào cùng khoảng lặng với chỗ ngừng nói: giữ 1 chỗ (đổi góc máy), ghi cả 2 lý do
    for u in [x for x in ung if x["loai"] == "goc"]:
        for v in [x for x in ung if x["loai"] == "lang"]:
            if any(a - 1e-6 <= u["t"] <= b + 1e-6 and a - 1e-6 <= v["t"] <= b + 1e-6 for a, b in lang):
                u["ly_do"] = "đổi góc máy + " + v["ly_do"]
                ung.remove(v)
    # 3) gom: ưu tiên cao trước, mỗi cảnh con ≥ CANH_MIN; cặp im lặng nhận cả 2 hoặc bỏ cả 2
    nhan = []

    def vua(t):
        return t - tu >= CANH_MIN - 1e-6 and den - t >= CANH_MIN - 1e-6 and all(abs(t - x["t"]) >= CANH_MIN - 1e-6 for x in nhan)
    xong_cap = set()
    for u in sorted(ung, key=lambda x: -x["uu"]):
        if u.get("cap") and u["cap"][0] > tu + 1e-6 and u["cap"][1] < den - 1e-6:   # cặp 2 mép giữa cảnh
            if u["cap"] in xong_cap:
                continue
            xong_cap.add(u["cap"])
            hai = [x for x in ung if x.get("cap") == u["cap"]]
            if len(hai) == 2 and vua(hai[0]["t"]) and vua(hai[1]["t"]) and abs(hai[0]["t"] - hai[1]["t"]) >= CANH_MIN - 1e-6:
                nhan += hai
            continue
        if vua(u["t"]):
            nhan.append(u)
    nhan.sort(key=lambda x: x["t"])
    cat, im = [], []
    for u in nhan:
        t = round(round(u["t"] * FPS) / FPS, 3)   # đúng mép khung hình (bộ dựng cũng làm tròn theo khung)
        dau_im = bool(u.get("cap")) and abs(u["cap"][0] - u["t"]) < 1e-6   # sau mép này là đoạn im lặng
        cat.append({"t": t, "loai": u["loai"], "ly_do": u["ly_do"], "sau": "" if dau_im else sau(t),
                    **({"cap": "%.3f-%.3f" % u["cap"]} if u.get("cap") else {})})
    for u in nhan:
        if u.get("cap"):
            a, b = u["cap"]
            a = tu if a <= tu + 1e-6 else round(round(a * FPS) / FPS, 3)
            b = den if b >= den - 1e-6 else round(round(b * FPS) / FPS, 3)
            if [a, b] not in [x[:2] for x in im]:
                im.append([a, b, round(b - a, 2)])
    return {"cat": cat, "im": im, "co_loi": bool(co_loi), "so_chu": len(ws)}, bao


def lenh_chia(viec_p):
    viec = doc(viec_p, {})
    kho = viec["kho"]
    kho_nghe, kho_hinh = os.path.join(kho, "nghe"), os.path.join(kho, "hinh")
    os.makedirs(kho_nghe, exist_ok=True)
    os.makedirs(kho_hinh, exist_ok=True)
    canh = viec.get("canh") or []
    tach_im = viec.get("tach_im", True) is not False
    md = chung.mo_hinh_hoac_none() if hasattr(chung, "mo_hinh_hoac_none") else getattr(chung, "MO_HINH", None)
    may = _Nghe(md) if md and os.path.isdir(md) else None
    bao = []
    if may is None:
        bao.append("Chưa có máy nghe tiếng Việt: chỉ dựa vào độ to nhỏ của tiếng để tìm chỗ ngừng nói")
    src_ds = []
    for c in canh:
        if c["src"] not in [x["src"] for x in src_ds]:
            src_ds.append(c)
    du = {}
    for i, c in enumerate(src_ds):
        s, ten = c["src"], os.path.basename(c["src"])
        x = {"env": None, "tu": None, "goc": []}
        if c.get("co_tieng", True):
            in_("BUOC=Nghe lời nói clip %d/%d (%s)" % (i + 1, len(src_ds), ten))
            x["tu"] = tu_cua_clip(s, kho_nghe, may)
            in_("BUOC=Đo chỗ ngừng nói clip %d/%d (%s)" % (i + 1, len(src_ds), ten))
            with contextlib.redirect_stdout(sys.stderr):
                x["env"] = KH.bao_bien(s)
        in_("BUOC=Tìm chỗ đổi góc máy clip %d/%d (%s)" % (i + 1, len(src_ds), ten))
        try:
            x["goc"] = diem_goc(s, c.get("xem"), kho_hinh)
        except Exception as e:  # noqa
            bao.append("Không dò được chỗ đổi góc máy của %s: %s" % (ten, str(e)[:100]))
        du[s] = x
    out, so = [], 0
    for n, c in enumerate(canh):
        x = du[c["src"]]
        kq, b = chia_mot(c, x["tu"], x["env"], x["goc"], tach_im)
        bao += ["Cảnh %s: %s" % (c.get("so") or n + 1, y) for y in b]
        so += len(kq["cat"])
        out.append(dict(kq, id=c.get("id")))
    in_("CANH_BAO=" + json.dumps(bao, ensure_ascii=False))
    in_("XONG=" + json.dumps({"canh": out, "so_cho": so, "tach_im": tach_im}, ensure_ascii=False))


# ================================================================== TỰ CHỈNH MÀU
SO_KHUNG = 5
RONG = 96            # khung đo nhỏ (đủ cho thống kê màu, rất nhanh)
GIU_AM = 0.25        # giữ lại chừng này độ ấm của đèn (không trắng toát như phòng chụp)
DICH_SANG = 0.44     # trung vị độ sáng mong muốn cho cảnh tối
KEO_SANG = 0.7       # kéo trung vị về DICH_SANG chừng này phần


def kelvin_rgb(K):
    """Hệ số R, G, B mà colortemperature của ffmpeg nhân vào (vf_colortemperature.c, không chuẩn hoá)."""
    k = K / 100.0
    if k <= 66.0:
        r, g = 1.0, 0.39008157876901960784 * math.log(k) - 0.63184144378862745098
    else:
        t = max(k - 60.0, 0.0)
        r, g = 1.29293618606274509804 * t ** -0.1332047592, 1.12989086089529411765 * t ** -0.0755148492
    b = 1.0 if k >= 66.0 else 0.0 if k <= 19.0 else 0.54320678911019607843 * math.log(k - 10.0) - 1.19625408914
    return np.clip([r, g, b], 0, 1)


# giá trị thanh kéo của tab Cảnh › Màu (dev/_canh-tt.js TT): làm tròn đúng nấc để thanh hiện đúng số
def _nac_K(K):
    v = round((6500 - K) / 35) if K <= 6500 else -round((K - 6500) / 25)
    v = max(-100, min(100, v))
    return int(round(6500 - v * 35 if v >= 0 else 6500 - v * 25))


def _nac(x, buoc, goc, lo, hi):
    v = max(lo, min(hi, round((x - goc) / buoc)))
    return round(goc + v * buoc, 3)


def khung_raw(c, ra_dir):
    """SO_KHUNG khung (yuv420p, rộng RONG) của cảnh -> (tệp .yuv nhiều khung, rộng, cao). Lấy từ bản xem nhẹ (đã HDR -> SDR) nếu có."""
    tu, den = float(c["tu"]), float(c["den"])
    xem = c.get("xem") if c.get("xem") and os.path.isfile(c["xem"]) else None
    f = xem or c["src"]
    vf = ""
    if not xem and c.get("hdr"):
        import dung_may_chu as DM
        vf = DM.hdr_chain({"hdr_trc": c.get("hdr_trc")}) + ","
    ts = [tu + (den - tu) * (i + 0.5) / SO_KHUNG for i in range(SO_KHUNG)]
    # khung dọc 9:16: cắt giữa như bộ dựng (phủ khung) để đo đúng phần sẽ lên hình
    vf += "scale=%d:-2,crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=%d:%d,format=yuv420p" % (RONG * 4, RONG, int(RONG * 16 / 9) // 2 * 2)

    def mot(t):
        r = subprocess.run([chung.FFMPEG, "-v", "error", "-ss", "%.3f" % t, "-i", f, "-frames:v", "1", "-vf", vf,
                            "-f", "rawvideo", "-"], capture_output=True, timeout=120, **KW)
        return r.stdout
    with ThreadPoolExecutor(max_workers=3) as tp:
        ds = [x for x in tp.map(mot, ts) if x]
    if not ds:
        raise ValueError("không lấy được khung nào")
    w, h = RONG, int(RONG * 16 / 9) // 2 * 2
    n = w * h * 3 // 2
    ds = [x[:n] for x in ds if len(x) >= n]
    p = os.path.join(ra_dir, "khung-%s.yuv" % hashlib.md5(json.dumps(c, sort_keys=True).encode()).hexdigest()[:10])
    with open(p, "wb") as fo:
        fo.write(b"".join(ds))
    return p, w, h, len(ds)


def dung_thu(p, w, h, chuoi):
    """Các khung đi qua chuỗi filter (đúng như bộ dựng) -> mảng RGB (N, 3) 0..1."""
    r = subprocess.run([chung.FFMPEG, "-v", "error", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", "%dx%d" % (w, h), "-i", p,
                        "-vf", (chuoi + "," if chuoi else "") + "format=rgb24", "-f", "rawvideo", "-"], capture_output=True, timeout=120, **KW)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, 3).astype(np.float64) / 255.0


def do_mau(rgb):
    """Thống kê: độ sáng (phân vị 2 / 50 / 98), ánh đèn (trung bình các điểm gần xám, ln R/B), độ đậm màu."""
    Y = rgb @ np.array([0.299, 0.587, 0.114])
    mx, mn = rgb.max(1), rgb.min(1)
    s = (mx - mn) / (mx + 1e-6)
    ok = (Y > 0.06) & (mx < 0.97)
    ok2 = ok & (Y > 0.12) & (Y < 0.9)
    if ok2.sum() < 50:
        ok2 = ok
    if ok2.sum() < 20:
        return {"p2": float(np.percentile(Y, 2)), "p50": float(np.median(Y)), "p98": float(np.percentile(Y, 98)), "rb": 0.0, "gb": 0.0,
                "sat": float(s.mean()), "xam_sat": 1.0, "tin": 0.0, "sac": float((mx - mn).mean())}
    nguong = np.percentile(s[ok2], 30)
    xam = rgb[ok2 & (s <= nguong)]
    e = xam.mean(0) + 1e-4
    # ánh đèn đo 2 cách: điểm gần xám (30% ít màu nhất) và điểm sáng nhất (5%, chưa cháy: tường trắng, máy bạc, đèn hắt).
    # Đèn vàng thật thì cả 2 cùng ấm; cảnh vốn ấm (bàn gỗ, đồ cam) thì điểm sáng nhất (cốc trắng…) gần trung tính -> lấy số NHỎ hơn,
    # khác chiều nhau thì coi như không lệch màu (giữ màu thật)
    t = np.percentile(Y[ok], 95)
    es = rgb[ok & (Y >= t)].mean(0) + 1e-4
    rb_x, rb_s = math.log(e[0] / e[2]), math.log(es[0] / es[2])
    rb = min(rb_x, rb_s) if rb_x > 0 and rb_s > 0 else max(rb_x, rb_s) if rb_x < 0 and rb_s < 0 else 0.0
    return {"p2": float(np.percentile(Y, 2)), "p50": float(np.median(Y)), "p98": float(np.percentile(Y, 98)),
            "rb": float(rb), "rb_xam": float(rb_x), "rb_sang": float(rb_s), "gb": float(math.log(e[1] / e[2])), "sat": float(s[ok].mean()),
            "xam_sat": float(s[ok2 & (s <= nguong)].mean()), "tin": float(ok2.mean()), "sac": float((mx - mn)[ok].mean())}


def chuoi_mau(m):
    """Đúng chuỗi filter của dung_may_chu.mau_canh."""
    f = []
    if (m["sang"], m["tuong_phan"], m["bao_hoa"]) != (0.0, 1.0, 1.0):
        f.append("eq=brightness=%g:contrast=%g:saturation=%g" % (m["sang"], m["tuong_phan"], m["bao_hoa"]))
    if m["nhiet"] != 6500:
        f.append("colortemperature=temperature=%d" % m["nhiet"])
    return ",".join(f)


def uoc_mau(d):
    """Thống kê khung gốc -> {sang, tuong_phan, bao_hoa, nhiet} (chưa làm tròn nấc)."""
    # 1) nhiệt màu: đưa ánh đèn (ln R/B của điểm gần xám) về GIU_AM phần cũ; ấm quá 0,08 mới sửa; hơi xanh thì ấm lại nhẹ (một nửa)
    rb = d["rb"]
    K = 6500
    tin = max(0.5, min(1.0, (0.6 - d["xam_sat"]) / 0.3))   # điểm "xám" vẫn đậm màu (cảnh toàn đồ màu): bớt tay
    if rb > 0.08:
        dich = rb - (1 - GIU_AM) * tin * rb
    elif rb < -0.08:
        dich = rb - 0.5 * tin * rb
    else:
        dich = None
    if dich is not None:
        tot, K = abs(rb - dich), 6500
        for v in range(-100, 101):
            k = 6500 - v * 35 if v >= 0 else 6500 - v * 25
            if not (5300 <= k <= 9000):
                continue
            m = kelvin_rgb(k) if k != 6500 else np.ones(3)
            sai = abs(rb + math.log(m[0] / m[2]) - dich)
            if sai < tot - 1e-9:
                tot, K = sai, k
    mK = kelvin_rgb(K) if K != 6500 else np.ones(3)
    hs = float(np.dot([0.299, 0.587, 0.114], mK))   # nhiệt màu làm tối đi chừng này
    p2, p50, p98 = d["p2"] * hs, d["p50"] * hs, d["p98"] * hs
    # 2) độ sáng / tương phản: y' = a·y + c (y = độ sáng 0..1). Tối: kéo trung vị về gần DICH_SANG nhưng GIỮ ĐIỂM ĐEN (p2 chỉ nhích
    #    +0,02: nền đen không bạc), phần sáng nhất không quá 1,02; sáng quá: hạ nhẹ; nhạt (bệt): tăng tương phản nhẹ quanh trung vị.
    a, cc, muon = 1.0, 0.0, None
    if p50 < 0.40:
        T50 = p50 + KEO_SANG * (DICH_SANG - p50)
        L = p2 + 0.02
        a = (T50 - L) / max(0.05, p50 - p2)
        a = max(1.0, min(a, (1.02 - L) / max(0.05, p98 - p2), 1.5))
        # tương phản chạm trần (1,5) mà chưa tới đích: nhấc thêm cả điểm đen, tối đa +0,08 (hơi bạc nhẹ còn hơn tối)
        cc = max(L - a * p2, min(T50 - a * p50, p2 + 0.08 - a * p2, 1.02 - a * p98))
        muon = a * p50 + cc
    elif p50 > 0.62:
        muon = p50 - 0.5 * (p50 - 0.62)
        cc = muon - p50
    elif p98 - p2 < 0.55:          # bệt, thiếu tương phản
        a = min(1.15, 0.65 / max(0.2, p98 - p2))
        cc = p50 - a * p50
    # eq của ffmpeg làm trên Y dải hẹp (16–235): Y' = a(Y − 0,5) + 0,5 + sang  ->  sang = c·219/255 + (a − 1)(0,5 − 16/255)
    sang = cc * 219.0 / 255.0 + (a - 1.0) * (0.5 - 16.0 / 255.0)
    # 3) độ đậm màu: sáng / tương phản lên thì màu nhạt đi tương đối -> bù một nửa, tối đa +12%, cảnh đã đậm thì giữ
    bh = 1.0
    if (a > 1.0 or sang > 0.02) and d["sac"] < 0.3:
        bh = min(1.12, 1.0 + 0.5 * ((a - 1.0) + max(0.0, cc)))
    return {"sang": sang, "tuong_phan": a, "bao_hoa": bh, "nhiet": K}, muon


def lam_tron(m):
    return {"sang": _nac(m["sang"], 0.003, 0.0, -100, 100), "tuong_phan": _nac(m["tuong_phan"], 0.005, 1.0, -100, 100),
            "bao_hoa": _nac(m["bao_hoa"], 0.01, 1.0, -100, 100), "nhiet": _nac_K(m["nhiet"])}


def la_mac_dinh(m):
    return abs(m["sang"]) < 0.012 and abs(m["tuong_phan"] - 1) < 0.02 and abs(m["bao_hoa"] - 1) < 0.02 and abs(m["nhiet"] - 6500) < 150


def mau_mot(c, tam):
    p, w, h, n = khung_raw(c, tam)
    try:
        d0 = do_mau(dung_thu(p, w, h, ""))
        m, muon = uoc_mau(d0)
        m = lam_tron(m)
        # dựng thử đúng chuỗi của bộ dựng, đo lại: chỉnh độ sáng cho trúng đích (eq làm trên YUV, nhiệt màu trên RGB: ước lệch chút)
        if not la_mac_dinh(m):
            d1 = do_mau(dung_thu(p, w, h, chuoi_mau(m)))
            if muon is not None and abs(d1["p50"] - muon) > 0.015:
                m["sang"] = max(-0.3, min(0.3, m["sang"] + (muon - d1["p50"]) * 0.9))
                m = lam_tron(m)
                d1 = do_mau(dung_thu(p, w, h, chuoi_mau(m)))
        else:
            d1 = d0
        kq = None if la_mac_dinh(m) else m
        return {"id": c.get("id"), "ids": c.get("ids") or [c.get("id")], "mau": kq, "truoc": _gon(d0), "sau": _gon(d1)}
    finally:
        try:
            os.remove(p)
        except OSError:
            pass


def _gon(d):
    return {"sang": round(d["p50"], 3), "den": round(d["p2"], 3), "am": round(d["rb"], 3), "dam": round(d["sac"], 3)}


def lenh_mau(viec_p):
    viec = doc(viec_p, {})
    tam = os.path.join(viec["kho"], "hinh", "mau-tam")
    os.makedirs(tam, exist_ok=True)
    canh = viec.get("canh") or []
    out, bao = [], []
    for i, c in enumerate(canh):
        in_("BUOC=Đo màu cảnh %d/%d" % (i + 1, len(canh)))
        try:
            out.append(mau_mot(c, tam))
        except Exception as e:  # noqa
            traceback.print_exc()
            bao.append("Cảnh %s: không đo được màu (%s)" % (c.get("so") or i + 1, str(e)[:100]))
            out.append({"id": c.get("id"), "ids": c.get("ids") or [c.get("id")], "mau": None, "loi": True})
    in_("CANH_BAO=" + json.dumps(bao, ensure_ascii=False))
    in_("XONG=" + json.dumps({"canh": out}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        if len(sys.argv) >= 3 and sys.argv[1] == "chia":
            lenh_chia(sys.argv[2])
        elif len(sys.argv) >= 3 and sys.argv[1] == "mau":
            lenh_mau(sys.argv[2])
        else:
            in_("LOI=Lệnh lạ")
    except SystemExit as e:
        in_("LOI=" + str(e)[:400])
    except Exception as e:  # noqa
        traceback.print_exc()
        in_("LOI=" + ("%s" % e)[:400])
