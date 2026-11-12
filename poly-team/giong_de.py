# -*- coding: utf-8 -*-
"""Giọng AI ĐỌC LẠI khối tiếng tách (r32, 10/11 17:07 anh: "cho đè giọng đọc ai trên file âm thanh tách ra, không cần viết chữ").

Trang (dev/_mod-giong-de.js): chuột phải khối tiếng tách (hoặc nhóm cảnh đã tách) › "Đọc lại bằng giọng AI…" -> lấy lời trong khối
(câu phụ đề đã có, chưa có thì máy nghe sherpa nghe riêng các khối: sua_tay.nghe(chi=…)) -> anh xem / sửa danh sách câu -> Tạo:
máy chủ tạo giọng từng câu bằng engine/giong.py (VieNeu trên máy / Microsoft cần mạng; máy thử: config "lenh_giong"), cắt ra mỗi câu
1 file, câu dài hơn chỗ trống tới câu sau thì tăng tốc (atempo giữ cao độ, tối đa 1,25×), vẫn dài thì báo tràn -> Áp: plan.giong_de
(engine/doc_lai.py đặt giờ theo khối, bộ dựng trộn).
File: <video>/lam/sua-tay/giong/de/cau-<mã>.wav (mã = băm chữ + giọng + tốc độ [+ phong cách, r39]: câu đã tạo thì dùng lại, sửa 1 câu
      chỉ tạo lại câu đó)
      + cau-<mã>-t<tốc×100>.wav (bản tăng tốc). Nằm trong thư mục giọng của video nên /api/sua-tay/giong?v=&p= phát được như giọng cũ.
API: POST /api/sua-tay/giong-de/tao {v, giong, toc_do, [phong, kieu_trend], cau: [{chu, cho}]} -> {ma};  GET /api/sua-tay/giong-de/tao?ma= -> trạng thái
     POST /api/sua-tay/giong-de/nghe {v, plan, khoi: [id khối]} -> {ma} (theo dõi bằng GET /api/sua-tay/nghe?ma= như Phụ đề tự động)
Kế hoạch: kiem(v, plan) gọi trong sua_tay.kiem_ke_hoach — chỉ nhận file trong thư mục giọng của video, số trong khoảng hợp lệ.
"""
import hashlib, json, os, re, shutil, subprocess, threading, time, traceback, unicodedata, wave

import sua_tay as ST

TANG_TOI_DA = 1.25   # tăng tốc tối đa (anh: "tối đa ~1,25×, giữ cao độ")
DEM = 0.04           # giây chừa trước câu sau
VIEC = {}


def thu_muc(v):
    return os.path.join(ST.giong_thu_muc(v), "de")


def _ma(chu, giong, toc, phong=None):
    """phong (r39): chỉ thêm vào băm khi có -> câu không phong cách giữ đúng tên file cũ."""
    return hashlib.sha1(json.dumps([chu, giong, toc] + ([phong] if phong else []), ensure_ascii=False).encode("utf-8")).hexdigest()[:14]


def _sach_chu(x):
    x = unicodedata.normalize("NFC", str(x or "")).replace("|", " ").replace("\r", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", x).strip()[:300]


def _giay_wav(p):
    try:
        with wave.open(p, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        return None


def _cat_wav(goc, out, tu, den):
    """Cắt đoạn [tu, den] giây của file wav (giong-doc.wav của engine: 48 kHz mono 16 bit) ra file riêng (không qua ffmpeg)."""
    with wave.open(goc, "rb") as r:
        sr, n = r.getframerate(), r.getnframes()
        a, b = max(0, int(round(tu * sr))), min(n, int(round(den * sr)))
        r.setpos(a)
        data = r.readframes(max(0, b - a))
        tam = out + ".tam.wav"
        with wave.open(tam, "wb") as w:
            w.setnchannels(r.getnchannels())
            w.setsampwidth(r.getsampwidth())
            w.setframerate(sr)
            w.writeframes(data)
    os.replace(tam, out)


def _tang_toc(goc, toc):
    """Bản tăng tốc (giữ cao độ: atempo) của 1 câu -> đường file (có rồi thì dùng lại)."""
    out = goc[:-4] + "-t%d.wav" % int(round(toc * 100))
    if os.path.isfile(out) and os.path.getsize(out) > 100:
        return out
    ff = ST.S.tim_ffmpeg()
    if not ff:
        raise ValueError("Không thấy ffmpeg của bộ dựng")
    tam = out + ".tam.wav"
    r = subprocess.run([ff, "-v", "error", "-y", "-i", goc, "-af", "atempo=%.3f" % toc, "-ar", "48000", "-ac", "1", tam],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
                       creationflags=ST.NO_WIN if ST.IS_WIN else 0)
    if r.returncode or not os.path.isfile(tam):
        raise ValueError("Không tăng tốc được câu giọng: " + (r.stderr or "")[-200:])
    os.replace(tam, out)
    return out


# ---------------------------------------------------------------- tạo giọng từng câu
def tao(v, giong, toc, cau, phong=None, kieu=None):
    v = ST.thu_muc_video(v)
    phong = ST.S.phong_hop_le(phong)   # r39: kiểu trend / phong cách (giong.py --phong); không có thì như cũ
    kieu = ST.S.kieu_hop_le(kieu) if phong or kieu else None
    gd = ST.S.giong_ds()
    if not ST.S.giong_hop_le(giong):
        giong = gd["mac_dinh"]
    if toc not in ST.S.TOC_GIONG:
        toc = "+10%"
    ds = []
    for c in cau if isinstance(cau, list) else []:
        if not isinstance(c, dict):
            continue
        chu = _sach_chu(c.get("chu"))
        try:
            cho = float(c.get("cho")) if c.get("cho") is not None else None
        except (TypeError, ValueError):
            cho = None
        ds.append({"chu": chu, "cho": cho if cho is None or cho == cho else None})
    if not ds or not any(x["chu"] for x in ds):
        raise ValueError("Chưa có câu nào để đọc: khối này không nghe ra lời")
    if len(ds) > 150 or sum(len(x["chu"]) for x in ds) > 8000:
        raise ValueError("Nhiều lời quá (tối đa 150 câu): chọn ít khối hơn rồi làm từng phần")
    ten = next((x["ten"] for x in gd["ds"] if x["id"] == giong), giong)
    ma = _ma([[x["chu"], None if x["cho"] is None else round(x["cho"], 2)] for x in ds], giong, toc + "|" + v, phong)
    with ST.LOCK:
        x = VIEC.get(ma)
        if x and (x.get("dang") or x.get("kq")):
            return {"ma": ma}
        for k in [k for k, y in VIEC.items() if not y.get("dang")][:-20]:
            VIEC.pop(k, None)
        st = VIEC[ma] = {"ma": ma, "v": v, "dang": True, "bat_dau": time.time(), "loi": "", "kq": None, "ten": ten, "giong": giong,
                         "toc_do": toc, "buoc": "Đang tạo giọng " + ten, "so_cau": sum(1 for x in ds if x["chu"]), "phong": phong, "kieu_trend": kieu}
    threading.Thread(target=_chay, args=(st, v, giong, toc, ten, ds, phong, kieu), daemon=True).start()
    return {"ma": ma}


def _chay(st, v, giong, toc, ten, ds, phong=None, kieu=None):
    try:
        d = thu_muc(v)
        os.makedirs(d, exist_ok=True)
        thieu = []   # câu chưa có file: tạo 1 lượt engine cho tất cả
        for x in ds:
            if x["chu"]:
                x["f0"] = os.path.join(d, "cau-%s.wav" % _ma(x["chu"], giong, toc, phong))
                if not (os.path.isfile(x["f0"]) and os.path.isfile(x["f0"][:-4] + ".json")) and x["chu"] not in thieu:
                    thieu.append(x["chu"])
        if thieu:
            with ST.LOCK:
                st["buoc"] = "Đang tạo giọng %s cho %d câu" % (ten, len(thieu))
            _engine(d, thieu, giong, toc, phong)
        out = []
        for i, x in enumerate(ds):
            if not x["chu"]:
                out.append({"i": i, "chu": "", "bo": True})
                continue
            meta = ST.S.read_json(x["f0"][:-4] + ".json", {}) or {}
            g0 = _giay_wav(x["f0"]) or 0.0
            toc_ = 1.0
            if x["cho"] is not None and g0 > x["cho"] - DEM and x["cho"] > 0.15:
                toc_ = min(TANG_TOI_DA, g0 / max(0.15, x["cho"] - DEM))
                toc_ = 1.0 if toc_ < 1.02 else round(toc_, 2)
            p = _tang_toc(x["f0"], toc_) if toc_ > 1.0 else x["f0"]
            g = _giay_wav(p) or g0 / toc_
            it = {"i": i, "chu": x["chu"], "local": p, "giay": round(g, 3), "goc_giay": round(g0, 3), "toc": toc_,
                  "tran": round(g - x["cho"], 2) if x["cho"] is not None and g > x["cho"] + 0.05 else 0}
            if meta.get("tu"):
                it["tu"] = [[w, round(a / toc_, 3), round(b / toc_, 3)] for w, a, b in meta["tu"]]
            out.append(it)
        with ST.LOCK:
            kq = {"cau": out, "giong": giong, "ten": ten, "toc_do": toc}
            if phong or kieu:
                kq.update({k: x for k, x in (("phong", phong), ("kieu_trend", kieu)) if x})
            st.update(dang=False, kq=kq, buoc="Xong")
    except subprocess.TimeoutExpired:
        with ST.LOCK:
            st.update(dang=False, loi="Tạo giọng quá 25 phút nên đã dừng: chọn ít khối hơn rồi làm từng phần")
    except Exception as x:  # noqa
        traceback.print_exc()
        with ST.LOCK:
            st.update(dang=False, loi=str(x)[:400])


def _engine(d, cau, giong, toc, phong=None):
    """Chạy engine/giong.py 1 lượt cho các câu (mỗi câu 1 dòng) rồi cắt giong-doc.wav theo mốc câu trong giong.json."""
    lam = os.path.join(d, "lam-%x" % int(time.time() * 1000))
    os.makedirs(lam, exist_ok=True)
    try:
        lp = os.path.join(lam, "loi-doc.txt")
        with open(lp, "w", encoding="utf-8") as f:
            f.write("\n".join(cau) + "\n")
        e = ST.S.engine()
        lenh = ST.S.CFG.get("lenh_giong")   # máy thử: giọng giả (không có model / mạng)
        cmd = (list(lenh) if isinstance(lenh, list) and lenh else [e["py"], os.path.join(e["dir"], "giong.py")]) + [
            lp, lam, "--giong", giong, "--toc-do", toc] + (["--phong", phong] if phong else [])
        if not lenh and not os.path.isfile(e["py"]):
            raise ValueError("Chưa cài bộ dựng: bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video")
        r = subprocess.run(cmd, cwd=e["dir"], env=ST.MAY._env(), capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=1500, creationflags=ST.NO_WIN if ST.IS_WIN else 0)
        j = ST.S.read_json(os.path.join(lam, "giong.json"), {}) or {}
        wav = os.path.join(lam, "giong-doc.wav")
        mc = j.get("cau") or []
        if r.returncode or not os.path.isfile(wav) or len(mc) != len(cau):
            ra = (r.stdout + "\n" + r.stderr).strip().splitlines()
            m = [x for x in ra if x.startswith("LOI=")]
            loi = m[-1][4:] if m else ""
            if not loi and any("edge_tts" in x or "aiohttp" in x or "ClientConnector" in x for x in ra):
                loi = "Giọng Microsoft cần mạng: kiểm mạng hoặc chọn giọng VieNeu (chạy trên máy)"
            if not loi and any("vieneu" in x.lower() or "onnx" in x.lower() for x in ra):
                loi = "Bộ dựng chưa có giọng VieNeu: chạy lại CAI-DAT.bat trong E:\\Tool\\poly-dung-video 1 lần (cần mạng)"
            raise ValueError(loi or "Không tạo được giọng: " + " ".join(ra[-3:])[:300])
        chu = j.get("chu") or []
        for i, (c, m) in enumerate(zip(cau, mc)):
            tu, den = float(m["tu"]), float(m["den"])
            p = os.path.join(d, "cau-%s.wav" % _ma(c, giong, toc, phong))
            _cat_wav(wav, p, tu, den)
            w = [x for x in chu if isinstance(x, dict) and x.get("cau") == i]
            tu_ = [[str(x.get("chu")), round(max(0.0, float(x["t"]) - tu), 3),
                    round((float(w[k + 1]["t"]) if k + 1 < len(w) else den) - tu, 3)] for k, x in enumerate(w)]
            ST._ghi(p[:-4] + ".json", dict({"chu": c, "giong": giong, "toc_do": toc, "giay": round(den - tu, 3), "tu": tu_}, **({"phong": phong} if phong else {})))
    finally:
        shutil.rmtree(lam, ignore_errors=True)


def tao_tt(ma):
    with ST.LOCK:
        st = VIEC.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy lượt tạo giọng này (app vừa khởi động lại?): bấm Tạo lại"}
        out = {k: st.get(k) for k in ("dang", "buoc", "loi", "kq", "ten", "giong", "toc_do", "so_cau", "phong", "kieu_trend")}
        out["giay_da"] = round(time.time() - st["bat_dau"], 1)
        if out.get("kq"):
            kq = dict(out["kq"])
            kq["cau"] = [dict(x, url="/api/sua-tay/giong?v=%s&p=%s&t=%d" % (ST.quote(st["v"]), ST.quote(x["local"]), int(os.path.getmtime(x["local"]))))
                         if x.get("local") and os.path.isfile(x["local"]) else x for x in kq["cau"]]
            out["kq"] = kq
        return out


# ---------------------------------------------------------------- kiểm khoá kế hoạch
def _so(v, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return v if v == v and lo <= v <= hi else None


def kiem(v, plan):
    """plan.giong_de từ trang -> bản sạch (file giọng chỉ trong <video>/lam/sua-tay/giong/, nguồn có trong kế hoạch); rỗng thì bỏ khoá."""
    if "giong_de" not in plan:
        return
    g = plan.get("giong_de")
    nguon = plan.get("nguon") or {}
    goc_d = ST.giong_thu_muc(v)
    # câu / vùng của khối không còn (xoá khối, "Lấy lại tiếng gốc"): bỏ cho gọn (trang vẫn giữ trong bản đang sửa để Ctrl+Z)
    khoi = {(k.get("nguon"), k.get("goc") or "") for k in plan.get("am_tach") or [] if isinstance(k, dict)}
    con = lambda x: (x.get("nguon"), str(x.get("goc") or "")) in khoi or (not x.get("goc") and any(n == x.get("nguon") for n, _ in khoi))
    cau, vung = [], []
    for c in (g.get("cau") or []) if isinstance(g, dict) else []:
        if not isinstance(c, dict) or c.get("nguon") not in nguon or not isinstance(c.get("local"), str) or not con(c):
            continue
        p = c["local"]
        if not (ST._trong(p, goc_d) and os.path.splitext(p)[1].lower() in (".wav", ".mp3", ".m4a")):
            continue
        s0, s1, giay = _so(c.get("s0"), 0, 1e6), _so(c.get("s1"), 0, 1e6), _so(c.get("giay"), 0.05, 120)
        if s0 is None or s1 is None or giay is None or s1 <= s0:
            continue
        x = {"chu": _sach_chu(c.get("chu")), "nguon": c["nguon"], "goc": str(c.get("goc") or "")[:40], "s0": round(s0, 3), "s1": round(s1, 3),
             "local": p, "giay": round(giay, 3), "toc": round(_so(c.get("toc"), 1, 2) or 1.0, 3)}
        for k in ("giong", "ten", "toc_do", "phong", "kieu_trend"):   # r39: + phong cách / kiểu trend (chỉ để nhớ)
            if isinstance(c.get(k), str):
                x[k] = c[k][:60]
        cau.append(x)
        if len(cau) >= 400:
            break
    for z in (g.get("vung") or []) if isinstance(g, dict) else []:
        if not isinstance(z, dict) or z.get("nguon") not in nguon or not con(z):
            continue
        a, b, n = _so(z.get("tu"), 0, 1e6), _so(z.get("den"), 0, 1e6), _so(z.get("nen"), 0, 1)
        if a is None or b is None or b - a < 0.01:
            continue
        vung.append({"nguon": z["nguon"], "goc": str(z.get("goc") or "")[:40], "tu": round(a, 3), "den": round(b, 3), "nen": round(n or 0.0, 3)})
        if len(vung) >= 300:
            break
    if cau or vung:
        plan["giong_de"] = {"cau": cau, "vung": vung}
    else:
        plan.pop("giong_de", None)


# ---------------------------------------------------------------- API
def get(h, u, q):
    if u.path == "/api/sua-tay/giong-de/tao":
        h.send(200, tao_tt((q.get("ma") or [""])[0]))
        return True
    return False


def post(h, u, data):
    a = u.path
    if a == "/api/sua-tay/giong-de/tao":
        r = tao(data.get("v"), data.get("giong"), data.get("toc_do"), data.get("cau"), data.get("phong"), data.get("kieu_trend"))
    elif a == "/api/sua-tay/giong-de/nghe":   # chỉ nghe các khối tiếng tách được chọn (video có giọng AI gõ lời vẫn nghe được)
        ids = [str(x) for x in (data.get("khoi") or []) if isinstance(x, str)][:300]
        if not ids:
            raise ValueError("Chưa chọn khối tiếng tách nào")
        r = ST.nghe(data.get("v"), data.get("plan"), chi=ids)
    else:
        return False
    h.send(200, r)
    return True
