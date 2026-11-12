# -*- coding: utf-8 -*-
"""DỰNG TỰ ĐỘNG trong app (POLY Cut r38, 11/11/2026, anh: "chức năng edit video tự động" -> "Dựng trọn: thô + tự gắn chữ, nhạc,
chuyển cảnh", làm 2 bước; gói này = bước 1 + khung bộ kiểu cho bước 2). Phần máy chủ, chỉ thư viện chuẩn.

Hộp "Video mới từ clip…" (và Thư viện › Clip) có nút Dựng tự động: anh bấm clip cầm máy nói theo thứ tự -> máy chủ chạy dung_tho.py
(dựng thô: bỏ khoảng lặng, ừ / à, câu nói lại giữ lần tốt nhất, zoom nhấn, phụ đề IN HOA theo lời nghe + từ điển tiệm) với --bo-kieu
(tu_dung_gan.py: tự gắn hook, thẻ giá, nhãn, chuyển cảnh, nhạc theo BỘ KIỂU) bằng Python của bộ dựng, chạy nền như "Tạo phụ đề từ
lời nói" (KHÔNG tốn lượt Claude) -> ra 1 video Sửa tay, trang mở luôn + bảng tóm tắt + nút Hoàn tác cả lượt.
"Video mới từ clip" thường (Tạo và sửa) giữ nguyên: video trơn, hiệu ứng thêm sau.

API (sua_tay.py móc vào: get / post đường /api/sua-tay/tu-dung…):
  GET  /api/sua-tay/tu-dung/bo                -> {ds: [{ma, ten, mo_ta, nguon}], kho: bool}  các bộ kiểu (app + kho effect)
  POST /api/sua-tay/tu-dung/chay {thu_muc, clip: [tên file theo thứ tự], ten, bo} -> {ma}
  GET  /api/sua-tay/tu-dung?ma=               -> {dang, buoc (1 nghe lời · 2 cắt · 3 gắn chữ · 4 xong), chu, phan_tram, giay_da, loi, kq: {v}}
  POST /api/sua-tay/tu-dung/dung {ma}         -> dừng + xoá thư mục video đang làm dở (chỉ thư mục lượt này vừa tạo)
  GET  /api/sua-tay/tu-dung/ket-qua?v=        -> lam/tu-dung.json của video (tóm tắt, plan_tron) | {co: false}
Bộ kiểu: <app>/dung-tu-dong/<mã>.json + <kho effect>/dung-tu-dong/<mã>.json (config "kho_effect" = thư mục kho effect của tiệm,
vd G:\\My Drive\\Poly Store MKT\\Kho effect Poly Cut; trống = không dùng kho). Cùng mã: bản trong kho thắng.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time

import sua_tay as ST

APP = os.path.dirname(os.path.abspath(__file__))
BO_DIR = os.path.join(APP, "dung-tu-dong")
VIEC = {}
LOCK = threading.RLock()
TOI_DA_CLIP = 20
BUOC_TEN = {1: "Nghe lời", 2: "Cắt khoảng lặng, ừ / à, câu nói lại", 3: "Gắn chữ, nhạc, chuyển cảnh", 4: "Xong"}


def kho():
    """Thư mục kho effect (config "kho_effect") nếu có thật, không thì None."""
    k = ST.S.CFG.get("kho_effect")
    return k if isinstance(k, str) and k.strip() and os.path.isdir(k.strip()) else None


def ds_bo():
    """Danh sách bộ kiểu (không cần bộ dựng: chỉ đọc tên trong file)."""
    da = {}
    for d, ng in ([(os.path.join(kho(), "dung-tu-dong"), "kho")] if kho() else []) + [(BO_DIR, "app")]:
        try:
            ten = sorted(os.listdir(d))
        except OSError:
            continue
        for f in ten:
            ma = os.path.splitext(f)[0]
            if not f.lower().endswith(".json") or ma in da or f.startswith(("_", ".")) or not re.fullmatch(r"[\w][\w\- .]{0,59}", ma, re.U):
                continue
            x = ST.S.read_json(os.path.join(d, f))
            if isinstance(x, dict):
                da[ma] = {"ma": ma, "ten": str(x.get("ten") or ma)[:40], "mo_ta": str(x.get("mo_ta") or "")[:160], "nguon": ng}
    md = da.pop("mac-dinh", {"ma": "mac-dinh", "ten": "Mặc định", "mo_ta": "", "nguon": "app"})
    return {"ds": [md] + [da[k] for k in sorted(da)], "kho": bool(kho())}


def _chon_clip(data):
    tm = str(data.get("thu_muc") or "").strip().strip('"')
    if not tm or not os.path.isdir(tm):
        raise ValueError("Không thấy thư mục clip")
    clips = data.get("clip") or []
    if not isinstance(clips, list) or not clips:
        raise ValueError("Chọn ít nhất 1 clip")
    if len(clips) > TOI_DA_CLIP:
        raise ValueError("Dựng tự động tối đa %d clip mỗi lần" % TOI_DA_CLIP)
    co = {fn.lower(): fn for fn in os.listdir(tm)}
    ds = []
    for c in clips:
        fn = co.get(os.path.basename(str(c)).lower())
        if not fn or os.path.splitext(fn)[1].lower() not in ST.VIDEO_EXT:
            raise ValueError("Không thấy clip %s trong thư mục" % c)
        p = os.path.join(tm, fn)
        if not ST.S.allowed_path(p, video=True):
            raise ValueError("Mở thư mục clip trong app trước (bấm Chọn thư mục)")
        if p not in ds:
            ds.append(p)
    return tm, ds


def chay(data):
    tm, ds = _chon_clip(data)
    ra = ST.ra_dir()
    if not ra:
        raise ValueError("Chưa đặt thư mục lưu video")
    e = ST.S.engine()
    if not os.path.isfile(e["py"]):
        raise ValueError("Chưa cài bộ dựng (Python + ffmpeg): bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video")
    if not e.get("mo_hinh") or not os.path.isdir(e["mo_hinh"]):
        raise ValueError("Chưa có máy nghe tiếng Việt trong bộ dựng (mo-hinh): bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video")
    bo = str(data.get("bo") or "mac-dinh")
    if not any(x["ma"] == bo for x in ds_bo()["ds"]):
        bo = "mac-dinh"
    with LOCK:
        for x in VIEC.values():
            if x.get("dang"):
                raise ValueError("Đang dựng tự động video khác (%s), chờ xong hoặc bấm Huỷ" % x.get("ten_dep", ""))
        os.makedirs(ra, exist_ok=True)
        ten_dep = str(data.get("ten") or "").strip()[:60] or os.path.basename(tm.rstrip("\\/"))
        goc = ST.S.slugify(ten_dep) or "video"
        slug, i = goc, 2
        while os.path.exists(os.path.join(ra, slug)) or any(x.get("dang") and x.get("slug") == slug and x.get("ra") == ra for x in VIEC.values()):
            slug, i = "%s-%d" % (goc, i), i + 1
        for k in sorted(VIEC)[:-20]:
            VIEC.pop(k, None)
        ma = "%x" % int(time.time() * 1000)
        st = VIEC[ma] = {"ma": ma, "dang": True, "buoc": 1, "chu": "Bắt đầu nghe lời", "phan_tram": 2, "bat_dau": time.time(), "loi": "",
                         "kq": None, "slug": slug, "ra": ra, "v": os.path.join(ra, slug), "ten_dep": ten_dep, "so_clip": len(ds), "huy": False}
    with ST.LOCK:
        ST.NGUON_OK.update(ST.norm(p) for p in ds)
    try:   # độ dài từng clip: tiến độ bước nghe theo số giây đã nghe
        st["dai"] = [float(ST.S.clip_giay(p) or 1.0) for p in ds]
    except Exception:  # noqa
        st["dai"] = [1.0] * len(ds)
    cmd = [e["py"], os.path.join(APP, "dung_tho.py"), "--clip"] + ds + [
        "--ra", ra, "--ten", slug, "--ghi-de", "--engine", e["dir"], "--mo-hinh", e["mo_hinh"],
        "--kho", os.path.join(ST.S.CACHE, "nghe"), "--bo-kieu", bo, "--khong-khung"]
    if kho():
        cmd += ["--kho-effect", kho()]
    kw = {"creationflags": ST.NO_WIN | 0x00000200} if ST.IS_WIN else {"start_new_session": True}
    try:
        p = subprocess.Popen(cmd, cwd=e["dir"], env=ST.MAY._env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    except Exception as ex:
        with LOCK:
            st.update(dang=False, loi="Không chạy được bộ dựng: %s" % ex)
        raise ValueError(st["loi"])
    st["pid"], st["p"] = p.pid, p
    threading.Thread(target=_theo, args=(st, p, ds), daemon=True).start()
    return {"ma": ma, "v": st["v"]}


def _buoc(st, chu):
    """Dòng BUOC= của dung_tho.py -> bước + phần trăm."""
    m = re.match(r"Nghe clip (\d+)/(\d+)", chu)
    if m:
        i, n = int(m.group(1)), max(1, int(m.group(2)))
        dai = st.get("dai") if len(st.get("dai") or []) == n else [1.0] * n
        st.update(buoc=1, chu="Nghe lời clip %d/%d" % (i, n), phan_tram=int(3 + 60 * sum(dai[:i - 1]) / max(0.1, sum(dai))))
    elif chu.startswith("Cắt"):
        st.update(buoc=2, chu=BUOC_TEN[2], phan_tram=66)
    elif chu.startswith("Tạo kế hoạch"):
        st.update(buoc=2, chu="Ghép cảnh, phụ đề IN HOA", phan_tram=74)
    elif chu.startswith("Gắn"):
        st.update(buoc=3, chu=BUOC_TEN[3], phan_tram=82)
    else:
        st["chu"] = chu[:80]


def _theo(st, p, ds):
    loi_ds = []

    def doc_err():
        for line in iter(p.stderr.readline, b""):
            loi_ds.append(line.decode("utf-8", "replace").rstrip())
            del loi_ds[:-40]
    threading.Thread(target=doc_err, daemon=True).start()
    kq = None
    for raw in iter(p.stdout.readline, b""):
        line = raw.decode("utf-8", "replace").strip()
        with LOCK:
            if line.startswith("BUOC="):
                _buoc(st, line[5:])
            elif line.startswith("XONG="):
                try:
                    kq = json.loads(line[5:])
                except ValueError:
                    pass
    code = p.wait()
    time.sleep(0.05)
    with LOCK:
        st["giay_da"] = round(time.time() - st["bat_dau"], 1)
        st.pop("p", None)
        if st.get("huy"):
            st.update(dang=False, loi="Đã huỷ")
        elif kq is not None and code == 0:
            ST.ghi_ten_dep(st["v"], st["ten_dep"])
            st.update(dang=False, buoc=4, chu=BUOC_TEN[4], phan_tram=100, kq={"v": st["v"], "so_do": kq.get("so_do")})
        else:
            # lỗi của bộ dựng: dòng cuối có chữ (SystemExit in ra stderr)
            cuoi = next((x for x in reversed(loi_ds) if x.strip() and not x.startswith(("Traceback", "  "))), "")
            st.update(dang=False, loi=("Dựng tự động lỗi: " + cuoi[:300]) if cuoi else "Bộ dựng dừng giữa chừng (mã %s)" % code)
    if kq is None or st.get("huy"):
        _don(st)
        if not st.get("huy"):
            ST.S.log("tu-dung loi %s: %s" % (st["slug"], " | ".join(loi_ds[-8:])))
    else:
        for x in ds:   # bản xem nhẹ cho trình sửa (clip đã chọn trong hộp thì thường đã có)
            try:
                ST.lam_proxy(x)
            except Exception:  # noqa
                pass


def _don(st):
    """Xoá thư mục video lượt này đang làm dở (thư mục mới tạo, chưa từng có trước lượt này)."""
    v = st.get("v")
    if v and os.path.isdir(v) and os.path.dirname(os.path.abspath(v)) == os.path.abspath(st["ra"]):
        shutil.rmtree(v, ignore_errors=True)


def tt(ma):
    with LOCK:
        st = VIEC.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy lượt dựng này (app vừa khởi động lại?)"}
        out = {k: st.get(k) for k in ("ma", "dang", "buoc", "chu", "phan_tram", "loi", "kq", "so_clip")}
        out["giay_da"] = round(time.time() - st["bat_dau"]) if st.get("dang") else st.get("giay_da")
        out["buoc_ten"] = BUOC_TEN
        return out


def dung(ma):
    with LOCK:
        st = VIEC.get(str(ma or ""))
        if not st or not st.get("dang"):
            return {"ok": True}
        st["huy"] = True
        pid = st.get("pid")
    if pid:
        try:
            if ST.IS_WIN:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, creationflags=ST.NO_WIN)
            else:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:  # noqa  tiến trình vừa xong
            pass
    return {"ok": True}


def ket_qua(v):
    v = ST.thu_muc_video(v)
    o = ST.S.read_json(os.path.join(v, "lam", "tu-dung.json"))
    if not isinstance(o, dict) or not isinstance(o.get("tom_tat"), list):
        return {"co": False}
    return {"co": True, "tom_tat": o["tom_tat"], "bo": o.get("bo"), "so_do": o.get("so_do"), "luc": o.get("luc"),
            "plan_tron": o.get("plan_tron")}


def get(h, u, q):
    if u.path == "/api/sua-tay/tu-dung/bo":
        h.send(200, ds_bo())
        return True
    if u.path == "/api/sua-tay/tu-dung":
        h.send(200, tt((q.get("ma") or [""])[0]))
        return True
    if u.path == "/api/sua-tay/tu-dung/ket-qua":
        h.send(200, ket_qua((q.get("v") or [""])[0]))
        return True
    return False


def post(h, u, data):
    if u.path == "/api/sua-tay/tu-dung/chay":
        h.send(200, chay(data))
        return True
    if u.path == "/api/sua-tay/tu-dung/dung":
        h.send(200, dung(data.get("ma")))
        return True
    return False
