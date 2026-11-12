# -*- coding: utf-8 -*-
"""Sửa tay video (trang /sua-tay của POLY Team) — phần máy chủ, chỉ thư viện chuẩn Python.

Anh mở 1 video đã dựng (hoặc tạo mới từ clip), xem trước 9:16, kéo cắt / đổi chỗ / chia cảnh, sửa hook, nhãn, phụ đề,
kiểu, rồi xuất bằng bộ dựng ffmpeg (không cần Premiere, không tốn lượt Claude). Đọc / ghi đúng <video>/lam/ke-hoach.json
mà Claude dùng, nên sau đó vẫn bấm "Sửa video" (Claude) trên thẻ được, Claude làm tiếp từ bản anh đã sửa.

Việc nặng (dòng thời gian, vẽ chữ, dựng) chạy bằng Python của bộ dựng: sua_tay_may.py (1 tiến trình "phuc-vu" chạy suốt
cho xem trước, mỗi lần xuất 1 tiến trình riêng). File tạm của trang này nằm trong <video>/lam/sua-tay/ và _cache/proxy/.
"""
import hashlib
import io
import json
import os
import queue
import re
import shutil
import signal
import subprocess
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

import tien_ich as TI  # noqa: E402  tiện ích / script (Nhờ Claude dùng được)
S = None  # module server.py (gán bằng gan())
APP = os.path.dirname(os.path.abspath(__file__))
IS_WIN = os.name == "nt"
NO_WIN = 0x08000000
VIDEO_EXT = (".mov", ".mp4", ".m4v", ".mts", ".mkv", ".avi")
XUAT_TOI_DA = 2          # cùng lúc dựng tối đa 2 bản (ffmpeg ăn CPU)
LOCK = threading.RLock()
NGUON_OK = set()          # clip được phép đọc (đã nằm trong kế hoạch trên đĩa, hoặc anh vừa chọn trong app)


def gan(server_module):
    global S
    S = server_module


def norm(p):
    return os.path.normcase(os.path.realpath(p))


def xuoi(p):
    return str(p).replace("\\", "/")


def ra_dir():
    return S.CFG.get("thu_muc_ra") or ""


# ---------------------------------------------------------------- tiến trình bộ dựng (xem trước)
class May:
    def __init__(self):
        self.p = None
        self.q = queue.Queue()
        self.lock = threading.Lock()
        self.n = 0

    def _env(self):
        e = S.engine()
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", POLY_ENGINE=e["dir"], POLY_FFMPEG_DIR=e["bin"],
                   POLY_FONT_DIR=e["font"], POLY_THU_MUC_RA=ra_dir())
        if e.get("mo_hinh"):
            env["POLY_MO_HINH"] = e["mo_hinh"]
        # 10/11 (anh: "app exe sẽ tự dò và sài card máy được cài"): mặc định Tự động = có card dùng được thì bộ dựng mã hoá + đọc clip
        # bằng card (card.py dò lúc mở app, bộ dựng tự lùi CPU khi card lỗi). config.json "ma_hoa": "cpu" = tắt (công tắc trong hộp Xuất);
        # "giai_ma" (không có trên trang) ép / tắt riêng phần đọc clip
        env["POLY_MA_HOA"] = str(S.CFG.get("ma_hoa") or "auto")
        if S.CFG.get("giai_ma"):
            env["POLY_GIAI_MA"] = str(S.CFG["giai_ma"])
        if S.CFG.get("kho_effect"):   # r35: Kho effect (Drive) — chuyển cảnh mới đọc thêm <kho>/chuyen-canh/*.json, chưa đặt = bản gói
            env["POLY_KHO_EFFECT"] = str(S.CFG["kho_effect"])
        env["PATH"] = os.pathsep.join([x for x in (e["scripts"], e["bin"]) if os.path.isdir(x)] + [env.get("PATH", "")])
        return env

    def _bat(self):
        e = S.engine()
        if not os.path.isfile(e["py"]):
            raise ValueError("Chưa cài bộ dựng (Python + ffmpeg): bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video")
        self.p = subprocess.Popen([e["py"], os.path.join(APP, "sua_tay_may.py"), "phuc-vu"], cwd=e["dir"], env=self._env(),
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  creationflags=NO_WIN if IS_WIN else 0)
        self.q = queue.Queue()
        p, q = self.p, self.q

        def doc_ra():
            for line in iter(p.stdout.readline, b""):
                q.put(line)
            q.put(None)

        def doc_loi():  # stderr: ghi gọn vào app-log (bộ dựng hay in cảnh báo)
            buf = []
            for line in iter(p.stderr.readline, b""):
                buf.append(line.decode("utf-8", "replace").rstrip())
                if len(buf) >= 40:
                    S.log("sua-tay may: " + " | ".join(buf)[-3000:])
                    buf = []
            if buf:
                S.log("sua-tay may: " + " | ".join(buf)[-3000:])

        threading.Thread(target=doc_ra, daemon=True).start()
        threading.Thread(target=doc_loi, daemon=True).start()

    def tat(self):
        if self.p and self.p.poll() is None:
            try:
                self.p.kill()
            except Exception:
                pass
        self.p = None

    def goi(self, lenh, data, timeout=120):
        with self.lock:
            for lan in range(2):
                if not self.p or self.p.poll() is not None:
                    self._bat()
                self.n += 1
                rid = self.n
                try:
                    self.p.stdin.write((json.dumps({"id": rid, "lenh": lenh, "data": data}, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.p.stdin.flush()
                except (OSError, ValueError):
                    self.tat()
                    if lan:
                        raise ValueError("Bộ dựng không chạy được (xem app-log.txt)")
                    continue
                han = time.time() + timeout
                while True:
                    try:
                        line = self.q.get(timeout=max(0.1, han - time.time()))
                    except queue.Empty:
                        self.tat()
                        raise ValueError("Bộ dựng xử lý quá lâu, thử lại")
                    if line is None:
                        self.tat()
                        break  # tiến trình chết: thử bật lại 1 lần
                    try:
                        res = json.loads(line.decode("utf-8", "replace"))
                    except ValueError:
                        continue
                    if res.get("id") != rid:
                        continue
                    if not res.get("ok"):
                        if res.get("chi_tiet"):
                            S.log("sua-tay %s: %s" % (lenh, res["chi_tiet"]))
                        raise ValueError(res.get("loi") or "Bộ dựng báo lỗi")
                    return res.get("kq")
            raise ValueError("Bộ dựng dừng đột ngột (xem app-log.txt)")


MAY = May()


# ---------------------------------------------------------------- kiểm đường dẫn
def thu_muc_video(v):
    """v phải là thư mục con trực tiếp của thư mục ra (E:\\Tool\\poly-edit\\<tên>)."""
    v = str(v or "").strip().strip('"')
    ra = ra_dir()
    if not v or not ra:
        raise ValueError("Thiếu thư mục video")
    rv = os.path.realpath(v)
    if norm(os.path.dirname(rv)) != norm(ra) or not os.path.isdir(rv):
        raise ValueError("Không mở được thư mục video này")
    return rv


def nguon_dia(v):
    """Các clip trong kế hoạch đang lưu trên đĩa (+ bản đang sửa: app chỉ ghi bản này sau khi đã kiểm clip) -> được phép đọc."""
    out = set()
    for f in (os.path.join(v, "lam", "ke-hoach.json"), os.path.join(v, "lam", "sua-tay", "dang-sua.json")):
        plan = S.read_json(f) or {}
        plan = plan.get("plan") if isinstance(plan.get("plan"), dict) else plan
        for k, src in ((plan or {}).get("nguon") or {}).items():
            p = (src or {}).get("local") or k if isinstance(src, dict) else k
            if p and isinstance(p, str) and os.path.isfile(p):
                out.add(norm(p))
    return out


def giong_dia(v):
    """Giọng AI của kế hoạch trên đĩa (trang không được tự đặt file giọng)."""
    plan = S.read_json(os.path.join(v, "lam", "ke-hoach.json")) or {}
    g = plan.get("giong")
    return g if isinstance(g, dict) and isinstance(g.get("local"), str) and os.path.isfile(g["local"]) else None


def cho_xem(rp):
    """Gọi từ allowed_path của server: clip của video đang sửa xem được (ảnh khung, bản xem nhẹ)."""
    with LOCK:
        return norm(rp) in NGUON_OK


def nguon_cua_video(v):
    """Mọi đường clip ghi trong kế hoạch / bản sửa dở của video (kể cả clip đã mất trên đĩa)."""
    out = set()
    for f in (os.path.join(v, "lam", "ke-hoach.json"), os.path.join(v, "lam", "sua-tay", "dang-sua.json")):
        plan = S.read_json(f) or {}
        plan = plan.get("plan") if isinstance(plan.get("plan"), dict) else plan
        for k, src in ((plan or {}).get("nguon") or {}).items():
            p = (src or {}).get("local") or k if isinstance(src, dict) else k
            if p and isinstance(p, str):
                out.add(norm(p))
    return out


def ten_clip_mat(plan):
    """Tên các clip cảnh còn dùng mà không thấy trên đĩa."""
    dung = {c.get("file") for c in plan.get("canh") or [] if isinstance(c, dict)}
    return [os.path.basename(str((src or {}).get("local") or f)) for f, src in (plan.get("nguon") or {}).items()
            if f in dung and not os.path.isfile(str((src or {}).get("local") or f))]


def kiem_ke_hoach(v, plan, can_file=True, cho_trong=False):
    """Kiểm kế hoạch trang gửi lên. Chỉ kiểm clip mà cảnh còn dùng (clip thừa / đã mất mà không cảnh nào dùng thì bỏ khỏi nguồn).
    can_file=False (xem trước, lưu bản sửa dở, Nhờ Claude): clip của chính video này mất trên đĩa (đổi tên / xoá / rút ổ) vẫn cho
    qua để anh còn sửa, lưu được; xuất / nghe thì báo rõ clip nào mất.
    cho_trong=True (xem trước, lưu bản sửa dở): video 0 cảnh vẫn cho qua (4/11 18:14, anh: "có thể xóa hết video không cần chừa lại");
    xuất / lưu / nghe / mẫu / Nhờ Claude thì báo "chưa có cảnh"."""
    if not isinstance(plan, dict) or not isinstance(plan.get("canh"), list) or not isinstance(plan.get("nguon"), dict):
        raise ValueError("Kế hoạch gửi lên sai dạng")
    if not plan["canh"] and not cho_trong:
        raise ValueError("Video chưa có cảnh nào, thêm clip trước")
    if len(plan["canh"]) > 300 or len(plan.get("phu_de") or []) > 800:
        raise ValueError("Kế hoạch quá lớn")
    ok = nguon_dia(v)
    with LOCK:
        ok |= NGUON_OK
    dung = {c.get("file") for c in plan["canh"] if isinstance(c, dict)}
    if isinstance(plan.get("am_tach"), list):   # tiếng tách (4/11): clip khối tiếng còn dùng (cảnh gốc đã xoá) cũng là clip đang dùng
        dung |= {k.get("nguon") for k in plan["am_tach"] if isinstance(k, dict) and isinstance(k.get("nguon"), str)}
    cua_video = None
    mat = []
    for f, src in list(plan["nguon"].items()):
        p = (src or {}).get("local") or f if isinstance(src, dict) else f
        hop_le = bool(p) and isinstance(p, str) and os.path.splitext(p)[1].lower() in VIDEO_EXT
        co = hop_le and os.path.isfile(p)
        if f not in dung:
            if not (co and norm(p) in ok):
                plan["nguon"].pop(f, None)   # clip thừa (không cảnh nào dùng) mà mất / lạ: bỏ, khỏi chặn cả video
            continue
        if co and norm(p) in ok:
            continue
        if hop_le and not co:
            if cua_video is None:
                cua_video = nguon_cua_video(v)
            if norm(p) in cua_video or norm(p) in ok:
                mat.append(os.path.basename(p))
                continue
        raise ValueError("Clip không hợp lệ: %s" % os.path.basename(str(p)))
    if mat and can_file:
        raise ValueError("Không thấy clip %s (đã đổi tên, xoá hoặc ổ đĩa chưa cắm?). Bấm \"Tìm lại clip…\" ở băng rôn đỏ trên cùng "
                         "(hoặc chuột phải vào cảnh sọc đỏ), hoặc xoá các cảnh dùng clip này rồi xuất lại." % ", ".join(mat))
    for c in plan["canh"]:
        if not isinstance(c, dict) or c.get("file") not in plan["nguon"]:
            raise ValueError("Cảnh trỏ tới clip không có trong kế hoạch")
        try:
            tu, den = float(c["tu"]), float(c["den"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Giờ cảnh sai dạng")
        if tu < 0 or den - tu < 0.2:
            raise ValueError("Có cảnh ngắn hơn 0,2 giây hoặc giờ âm")
    plan["giong"] = giong_hop(v, plan["giong"]) if "giong" in plan else giong_dia(v)   # giọng AI tạo trong Sửa tay (3/11) / bỏ giọng
    nhac_kiem(v, plan)   # nhạc nền + cân tiếng (4/11): chỉ file trong thư mục nhạc cho phép
    am_tach_kiem(plan)   # tiếng tách (4/11, dev/_mod-tach-am.js)
    if "giong_de" in plan:   # giọng AI đọc lại khối tách (r32, giong_de.py): chỉ file trong thư mục giọng của video
        import giong_de
        giong_de.kiem(v, plan)
    import am_thanh
    am_thanh.kiem(plan)   # âm thanh hiệu ứng ngắn (r20, am_thanh.py): chỉ file trong <app>/am-thanh
    # đường ra do máy chủ quyết, không lấy từ trang
    cu = S.read_json(os.path.join(v, "lam", "ke-hoach.json")) or {}
    if cu.get("ra"):
        plan["ra"] = cu["ra"]
    else:
        plan.pop("ra", None)
    return plan



def am_tach_kiem(plan):
    """Tiếng tách (4/11, "Tách âm thanh" kiểu CapCut): plan.am_tach = [{id, goc, nguon, tu, den, t, am_luong 0–2, vao, ra}] + cảnh đã tách
    có canh.tach_am = goc. Chỉ giữ khối đúng dạng, clip có trong nguon; không còn khối nào thì bỏ khoá (kế hoạch như chưa từng tách)."""
    for c in plan.get("canh") or []:
        if isinstance(c, dict) and "tach_am" in c and not (isinstance(c["tach_am"], str) and 0 < len(c["tach_am"]) <= 40):
            c.pop("tach_am")
    if "am_tach" not in plan:
        return
    out, ds = [], plan.get("am_tach")
    for k in ds if isinstance(ds, list) else []:
        if not isinstance(k, dict) or not isinstance(k.get("nguon"), str) or k["nguon"] not in plan["nguon"]:
            continue
        try:
            tu, den, t = float(k["tu"]), float(k["den"]), float(k.get("t") or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if not (tu >= 0 and den - tu >= 0.05 and -3600 < t < 36000):
            continue
        x = {"id": str(k.get("id") or "")[:40], "goc": str(k.get("goc") or "")[:40], "nguon": k["nguon"],
             "tu": round(tu, 3), "den": round(den, 3), "t": round(t, 3)}
        for kk, lo, hi in (("am_luong", 0.0, 2.0), ("vao", 0.0, 10.0), ("ra", 0.0, 10.0)):
            try:
                if kk in k:
                    x[kk] = round(max(lo, min(hi, float(k[kk]))), 3)
            except (TypeError, ValueError):
                pass
        out.append(x)
        if len(out) >= 300:
            break
    if out:
        plan["am_tach"] = out
    else:
        plan.pop("am_tach", None)


# ---------------------------------------------------------------- giọng đọc AI trong Sửa tay (3/11 17:49 anh: "add giọng nói ai cho sửa tay")
# Anh gõ lời đọc (mỗi dòng 1 câu), chọn giọng + tốc độ -> engine giong.py tạo giong-doc.wav + giong.json (mốc câu / chữ) trong
# <video>/lam/sua-tay/giong/<mã>/ (mã = băm lời + giọng + tốc độ: tạo lại y hệt thì dùng lại). Trang áp: plan.giong + phụ đề theo
# giọng thành 1 bước Ctrl+Z. Lúc xuất, bộ dựng trộn giọng và tự hạ tiếng clip khi có giọng (sidechain, đã có sẵn).
GIONG_VIEC = {}


def giong_thu_muc(v):
    return os.path.join(v, "lam", "sua-tay", "giong")


def _trong(p, d):
    try:
        return os.path.commonpath([norm(p), norm(d)]) == norm(d)
    except ValueError:
        return False


def giong_hop(v, g):
    """Giọng trang gửi lên: chỉ nhận giọng của kế hoạch trên đĩa hoặc file app tạo trong <video>/lam/sua-tay/giong/. None = bỏ giọng."""
    if g is None:
        return None
    dk = giong_dia(v)
    p = g.get("local") if isinstance(g, dict) else None
    if isinstance(p, str) and os.path.isfile(p):
        if dk and norm(dk["local"]) == norm(p):
            return _giong_thay(dk, g)
        if _trong(p, giong_thu_muc(v)) and os.path.splitext(p)[1].lower() in (".wav", ".mp3", ".m4a"):
            out = {"local": p, "file": p}
            for k in ("ten", "giong", "toc_do", "giay", "loi", "phong", "kieu_trend"):   # r39: + phong cách / kiểu trend (chỉ để nhớ)
                if k in g and isinstance(g[k], (str, int, float)):
                    out[k] = g[k] if not isinstance(g[k], str) else g[k][:4000]
            return _giong_thay(out, g)
    return dk


def _giong_thay(r, g):
    """Giữ cờ thay_tieng trang gửi (4/11: giọng AI thay hẳn tiếng trong clip -> lúc dựng tắt tiếng mọi cảnh)."""
    if r is None or not isinstance(g, dict) or "thay_tieng" not in g:
        return r
    return dict(r, thay_tieng=bool(g["thay_tieng"]))


def _giong_kq(d):
    """Kết quả 1 lần tạo giọng: wav + phụ đề theo giọng (mỗi câu 1 dòng phụ đề, mốc từng chữ nếu giọng có)."""
    j = S.read_json(os.path.join(d, "giong.json")) or {}
    wav = os.path.join(d, "giong-doc.wav")
    if not j or not os.path.isfile(wav):
        return None
    chu = j.get("chu") or []
    pd = []
    for i, c in enumerate(j.get("cau") or []):
        try:
            t0, t1 = round(float(c["tu"]), 3), round(float(c["den"]), 3)
        except (KeyError, TypeError, ValueError):
            continue
        tu = [x for x in chu if isinstance(x, dict) and x.get("cau") == i]
        it = {"chu": str(c.get("cau") or "").strip(), "t0": t0, "t1": max(t1, t0 + 0.2)}
        if tu:
            it["tu"] = [[str(x.get("chu")), round(float(x["t"]), 3),
                         round(float(tu[k + 1]["t"]) if k + 1 < len(tu) else t1, 3)] for k, x in enumerate(tu)]
        if it["chu"]:
            pd.append(it)
    return {"wav": wav, "giay": j.get("giay"), "giong": j.get("giong"), "toc_do": j.get("toc_do"), "phu_de": pd,
            "mt": int(os.path.getmtime(wav))}


def giong_ds_st():
    gd = S.giong_ds()
    return {"ds": gd["ds"], "mac_dinh": gd["mac_dinh"], "vieneu": gd.get("vieneu"),
            "toc": [{"v": k, "ten": t} for k, t in S.TOC_GIONG.items()], "trend": gd.get("trend") or [], "phong": gd.get("phong") or []}


def giong_tao(v, loi, giong, toc, phong=None, kieu=None):
    v = thu_muc_video(v)
    gd = S.giong_ds()
    if not S.giong_hop_le(giong):
        giong = gd["mac_dinh"]
    if toc not in S.TOC_GIONG:
        toc = "+10%"
    cau = [re.sub(r"\s+", " ", x).strip() for x in str(loi or "").replace("\r", "").split("\n")]
    cau = [x for x in cau if x and not x.startswith("#")]
    if not cau:
        raise ValueError("Chưa có lời đọc: gõ mỗi câu 1 dòng")
    if len(cau) > 80 or sum(len(x) for x in cau) > 4000:
        raise ValueError("Lời đọc dài quá (tối đa 80 câu, khoảng 4000 chữ)")
    phong = S.phong_hop_le(phong)   # r39: phong cách (giong.py --phong); không có thì mã / thư mục / lệnh như cũ
    kieu = S.kieu_hop_le(kieu) if phong or kieu else None
    ma = hashlib.sha1(json.dumps([cau, giong, toc] + ([phong] if phong else []), ensure_ascii=False).encode("utf-8")).hexdigest()[:12]
    d = os.path.join(giong_thu_muc(v), ma)
    ten = next((x["ten"] for x in gd["ds"] if x["id"] == giong), giong)
    with LOCK:
        x = GIONG_VIEC.get(ma)
        if x and x.get("dang"):
            return {"ma": ma}
        kq = _giong_kq(d)
        st = {"dang": not kq, "buoc": "Đang tạo giọng " + ten, "bat_dau": time.time(), "loi": "", "kq": kq, "v": v,
              "ten": ten, "giong": giong, "toc_do": toc, "loi_doc": "\n".join(cau), "so_cau": len(cau), "phong": phong, "kieu_trend": kieu}
        GIONG_VIEC[ma] = st
    if not kq:
        threading.Thread(target=_giong_chay, args=(st, d, cau, giong, toc, phong), daemon=True).start()
    return {"ma": ma}


def _giong_chay(st, d, cau, giong, toc, phong=None):
    try:
        os.makedirs(d, exist_ok=True)
        lp = os.path.join(d, "loi-doc.txt")
        with open(lp, "w", encoding="utf-8") as f:
            f.write("\n".join(cau) + "\n")
        e = S.engine()
        lenh = S.CFG.get("lenh_giong")   # máy thử: giọng giả (không có model / mạng)
        cmd = (list(lenh) if isinstance(lenh, list) and lenh else [e["py"], os.path.join(e["dir"], "giong.py")]) + [
            lp, d, "--giong", giong, "--toc-do", toc] + (["--phong", phong] if phong else [])
        if not lenh and not os.path.isfile(e["py"]):
            raise ValueError("Chưa cài bộ dựng: bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video")
        r = subprocess.run(cmd, cwd=e["dir"], env=MAY._env(), capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=1500, creationflags=NO_WIN if IS_WIN else 0)
        kq = _giong_kq(d)
        if r.returncode or not kq:
            ra = (r.stdout + "\n" + r.stderr).strip().splitlines()
            m = [x for x in ra if x.startswith("LOI=")]
            loi = m[-1][4:] if m else ""
            if not loi and any("edge_tts" in x or "aiohttp" in x or "ClientConnector" in x for x in ra):
                loi = "Giọng Microsoft cần mạng: kiểm mạng hoặc chọn giọng VieNeu (chạy trên máy)"
            if not loi and any("vieneu" in x.lower() or "onnx" in x.lower() for x in ra):
                loi = "Bộ dựng chưa có giọng VieNeu: chạy lại CAI-DAT.bat trong E:\\Tool\\poly-dung-video 1 lần (cần mạng)"
            raise ValueError(loi or "Không tạo được giọng: " + " ".join(ra[-3:])[:300])
        with LOCK:
            st.update(dang=False, kq=kq, buoc="Xong")
    except subprocess.TimeoutExpired:
        with LOCK:
            st.update(dang=False, loi="Tạo giọng quá 25 phút nên đã dừng: chia lời đọc ngắn lại rồi tạo lại")
    except Exception as x:  # noqa
        traceback.print_exc()
        with LOCK:
            st.update(dang=False, loi=str(x)[:400])


def giong_tao_tt(ma):
    with LOCK:
        st = GIONG_VIEC.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy lượt tạo giọng này (app vừa khởi động lại?): bấm Tạo giọng lại"}
        out = {k: st.get(k) for k in ("dang", "buoc", "loi", "kq", "ten", "giong", "toc_do", "loi_doc", "so_cau", "phong", "kieu_trend")}
        out["giay_da"] = round(time.time() - st["bat_dau"], 1)
        if out.get("kq"):
            out["kq"] = dict(out["kq"], url="/api/sua-tay/giong?v=%s&p=%s&t=%d" % (quote(st["v"]), quote(out["kq"]["wav"]), out["kq"]["mt"]))
        return out


# ---------------------------------------------------------------- nhạc nền (4/11, anh duyệt: "thêm nhạc từ file của tiệm hoặc nhạc
# miễn phí bản quyền; tự hạ nhạc khi có giọng đọc / người nói; chỉnh to nhỏ giữa nhạc, giọng, tiếng clip")
# plan.nhac {local, file, ten, tu, am_luong 0–2, ha_khi_noi, vao, ra, giay} · plan.can_tieng {giong 0–2, clip 0–2} (bộ dựng: dung_may_chu.tron_them).
# Thư mục nhạc được phép: config "thu_muc_nhac" (1 đường hoặc danh sách) + thư mục anh chọn trong app (_cache/nhac-thu-muc.json)
# + nhạc miễn phí kèm app (nhac-mien-phi/, CC0 tự tạo, NGUON.md). Máy chủ chỉ nhận / phát file nhạc trong các thư mục đó, hoặc đúng
# file nhạc kế hoạch trên đĩa đang dùng (anh đổi thư mục sau đó vẫn mở / xuất được video cũ). Nhạc là TUỲ CHỌN: kênh hay gắn nhạc
# trend ngay trong TikTok lúc đăng, video không có nhạc trừ khi anh thêm.
NHAC_EXT = (".mp3", ".m4a", ".aac", ".wav", ".ogg", ".opus", ".flac")
NHAC_MIME = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".wav": "audio/wav", ".ogg": "audio/ogg",
             ".opus": "audio/ogg", ".flac": "audio/flac"}
NHAC_MP = os.path.join(APP, "nhac-mien-phi")


def _nhac_chon_p():
    return os.path.join(S.CACHE, "nhac-thu-muc.json")


def nhac_thu_muc():
    """Thư mục nhạc được phép -> [(đường thật, nguồn "config" | "chon" | "mien_phi")]."""
    out, c = [], S.CFG.get("thu_muc_nhac")
    for p in ([c] if isinstance(c, str) else c if isinstance(c, list) else []):
        if isinstance(p, str) and p.strip() and os.path.isdir(p.strip()):
            out.append((os.path.realpath(p.strip()), "config"))
    ch = (S.read_json(_nhac_chon_p()) or {}).get("thu_muc")
    if isinstance(ch, str) and os.path.isdir(ch):
        out.append((os.path.realpath(ch), "chon"))
    if os.path.isdir(NHAC_MP):
        out.append((os.path.realpath(NHAC_MP), "mien_phi"))
    import kho   # r37: bản cache của Kho effect (Drive) — chỉ file đã chép về máy + kiểm sha256
    if os.path.isdir(kho.thu_muc_cache()):
        out.append((os.path.realpath(kho.thu_muc_cache()), "kho"))
    return out


def nhac_dia(v, ca_nhap=True):
    """Nhạc của kế hoạch (+ bản sửa dở nếu ca_nhap) trên đĩa, file còn -> [dict]. Kế hoạch trên đĩa đứng trước."""
    out = []
    for f in (os.path.join(v, "lam", "ke-hoach.json"),) + ((os.path.join(v, "lam", "sua-tay", "dang-sua.json"),) if ca_nhap else ()):
        p = S.read_json(f) or {}
        p = p.get("plan") if isinstance(p.get("plan"), dict) else p
        n = (p or {}).get("nhac")
        if isinstance(n, dict) and isinstance(n.get("local"), str) and os.path.isfile(n["local"]):
            out.append(n)
    return out


def nhac_cho_phep(p, v=None):
    """File nhạc p được dùng / phát không: đuôi nhạc, có thật, nằm trong thư mục nhạc cho phép (hoặc là nhạc video v đang dùng)."""
    if not (isinstance(p, str) and p and os.path.splitext(p)[1].lower() in NHAC_EXT and os.path.isfile(p)):
        return False
    if any(_trong(p, d) for d, _ in nhac_thu_muc()):
        return True
    return bool(v) and any(norm(n["local"]) == norm(p) for n in nhac_dia(v))


def _so_kep(x, lo, hi):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or x != x:
        return None
    return round(max(lo, min(hi, float(x))), 3)


def nhac_hop(v, n):
    """Nhạc trang gửi -> dict sạch | None (bỏ nhạc). File lạ / ngoài thư mục cho phép: giữ nhạc đang có trên đĩa (hoặc không nhạc)."""
    if n is None:
        return None
    p = n.get("local") if isinstance(n, dict) else None
    if not nhac_cho_phep(p, v):
        d = nhac_dia(v, False)
        return d[0] if d else None
    out = {"local": p, "file": p, "ten": str(n.get("ten") or os.path.splitext(os.path.basename(p))[0])[:200]}
    for k, lo, hi in (("tu", 0.0, 36000.0), ("am_luong", 0.0, 2.0), ("vao", 0.0, 5.0), ("ra", 0.0, 8.0), ("giay", 0.0, 36000.0)):
        x = _so_kep(n.get(k), lo, hi)
        if x is not None:
            out[k] = x
    out["ha_khi_noi"] = n.get("ha_khi_noi") is not False
    if n.get("mien_phi") is True:
        out["mien_phi"] = True
    return out


def nhac_kiem(v, plan):
    """Gọi trong kiem_ke_hoach: plan.nhac (trang không gửi khoá = giữ nhạc của ke-hoach.json; KHÔNG lấy bản sửa dở: Ctrl+Z về
    lúc chưa có nhạc thì trang gửi kế hoạch không khoá nhac) + plan.can_tieng (chỉ số 0–2, bỏ giá trị 1)."""
    if "nhac" in plan:
        plan["nhac"] = nhac_hop(v, plan["nhac"])
    else:
        d = nhac_dia(v, False)
        if d:
            plan["nhac"] = d[0]
    if "can_tieng" in plan:
        ct = plan["can_tieng"] if isinstance(plan["can_tieng"], dict) else {}
        ct = {k: _so_kep(ct.get(k), 0.0, 2.0) for k in ("giong", "clip")}
        ct = {k: x for k, x in ct.items() if x is not None and x != 1.0}
        if ct:
            plan["can_tieng"] = ct
        else:
            plan.pop("can_tieng")


_NHAC_DS = {}   # thư mục -> (dấu thời gian đọc, kết quả): khỏi quét lại liền nhau


def _nhac_quet(d, nguon):
    """Liệt kê file nhạc trong d (+ 1 tầng thư mục con, tối đa 300 file), kèm độ dài (ffprobe, nhớ theo file)."""
    ds = []
    try:
        for goc, con, tep in os.walk(d):
            con[:] = [] if goc != d else sorted(x for x in con if not x.startswith((".", "_", "$")))   # chỉ 1 tầng con
            for t in sorted(tep, key=lambda x: x.lower()):
                if t.startswith((".", "_")) or os.path.splitext(t)[1].lower() not in NHAC_EXT:
                    continue
                fp = os.path.join(goc, t)
                try:
                    st = os.stat(fp)
                except OSError:
                    continue
                if not _trong(fp, d):   # lối tắt trỏ ra ngoài thư mục: không liệt kê (máy chủ cũng không nhận)
                    continue
                nhom = "" if goc == d else os.path.relpath(goc, d).replace("\\", "/")
                ds.append({"p": fp, "ten": os.path.splitext(t)[0], "nhom": nhom, "kb": int(st.st_size / 1024), "mt": int(st.st_mtime)})
                if len(ds) >= 300:
                    break
            if len(ds) >= 300:
                break
    except OSError:
        pass
    for x, g in zip(ds, S._POOL.map(lambda x: S.clip_giay(x["p"]), ds)):
        x["giay"] = g
    ds = [x for x in ds if x["giay"]]   # file hỏng / không phải nhạc: bỏ
    return {"thu_muc": d, "nguon": nguon, "ds": ds}


def nhac_ds(lam_moi=False):
    """Tab Nhạc của Thư viện: thư mục nhạc của tiệm (anh chọn trong app > config) + nhạc miễn phí kèm app."""
    tm = nhac_thu_muc()
    tiem = next((x for x in tm if x[1] == "chon"), None) or next((x for x in tm if x[1] == "config"), None)
    out = {"tiem": None, "mien_phi": None, "config": S.CFG.get("thu_muc_nhac") or ""}
    for k, x in (("tiem", tiem), ("mien_phi", next((y for y in tm if y[1] == "mien_phi"), None))):
        if not x:
            continue
        cu = _NHAC_DS.get(x[0])
        if lam_moi or not cu or time.time() - cu[0] > 20:
            cu = (time.time(), _nhac_quet(x[0], x[1]))
            _NHAC_DS[x[0]] = cu
        out[k] = cu[1]
    if out["mien_phi"]:
        kk = S.read_json(os.path.join(NHAC_MP, "nhac.json")) or {}   # tên hiện + mô tả + giấy phép từng bài (file kê)
        for x in out["mien_phi"]["ds"]:
            m = kk.get(os.path.basename(x["p"])) or {}
            x.update({k: m[k] for k in ("ten", "mo_ta", "giay_phep", "bpm", "phong_cach") if k in m})   # phong_cach: nhóm trong Thư viện (r20)
    import kho
    return kho.them_nhac(out)   # r37: drop / nhịp đầu + bài chỉ có ở Kho effect (☁, tải về máy khi bấm)


def nhac_chon_thu_muc(p):
    p = str(p or "").strip().strip('"')
    if not p or not os.path.isdir(p):
        raise ValueError("Không thấy thư mục này trên máy")
    d = _nhac_quet(os.path.realpath(p), "chon")
    if not d["ds"]:
        raise ValueError("Thư mục này không có file nhạc (mp3, m4a, wav…). Chọn thư mục khác.")
    os.makedirs(S.CACHE, exist_ok=True)
    _ghi(_nhac_chon_p(), {"thu_muc": os.path.realpath(p), "luc": time.time()})
    _NHAC_DS[os.path.realpath(p)] = (time.time(), d)
    return nhac_ds()


def claude_dang_lam(v):
    """POLY Team có lượt Claude đang chạy / xếp hàng trên đúng video này?"""
    try:
        for jid in os.listdir(S.JOBS):
            j = S.read_json(os.path.join(S.JOBS, jid, "job.json")) or {}
            if j.get("status") in ("dang-chay", "cho") and S.thu_muc_video(j) and norm(S.thu_muc_video(j)) == norm(v):
                return (j.get("don") or {}).get("ten") or jid
    except OSError:
        pass
    return None


# ---------------------------------------------------------------- tên đẹp (r29, soi A13): tên có dấu anh gõ lúc tạo video, thư mục vẫn là slug
def ten_dep(v):
    p = os.path.join(v, "ten.txt")
    try:
        if os.path.isfile(p):
            with io.open(p, encoding="utf-8") as f:
                t = f.read().strip()
            return t[:60] if t and t != os.path.basename(v) else ""
    except Exception:
        pass
    return ""


def ghi_ten_dep(v, ten):
    ten = re.sub(r"\s+", " ", str(ten or "")).strip()[:60]
    if not ten or ten == os.path.basename(v):
        return
    try:
        with io.open(os.path.join(v, "ten.txt"), "w", encoding="utf-8") as f:
            f.write(ten)
    except Exception:
        S.log("sua-tay ten.txt: %s" % traceback.format_exc())


def moc_nhap(v):
    """Mốc bản sửa dở trên đĩa (r29, soi L4): cửa sổ hỏi mỗi 10 giây xem cửa sổ khác có ghi bản mới hơn không."""
    nh = os.path.join(v, "lam", "sua-tay", "dang-sua.json")
    d = S.read_json(nh) if os.path.isfile(nh) else None
    if not isinstance(d, dict):
        return {"luc": 0, "phien": None}
    return {"luc": float(d.get("luc") or 0), "phien": d.get("phien")}


# ---------------------------------------------------------------- danh sách video
def ds_video():
    ra = ra_dir()
    out = []
    if not ra or not os.path.isdir(ra):
        return {"ds": out, "thu_muc_ra": ra}
    for n in os.listdir(ra):
        v = os.path.join(ra, n)
        kp = os.path.join(v, "lam", "ke-hoach.json")
        if not os.path.isfile(kp):
            continue
        try:
            plan = S.read_json(kp) or {}
            kq = S.read_json(os.path.join(v, "ket-qua.json")) or {}
            nh = os.path.join(v, "lam", "sua-tay", "dang-sua.json")
            nh_luc = 0.0
            if os.path.isfile(nh):   # r29 (soi N11): giờ sửa gần nhất lấy "luc" ghi trong bản sửa dở (chép thư mục không làm mọi video cùng giờ)
                try:
                    nh_luc = float((S.read_json(nh) or {}).get("luc") or 0)
                except Exception:
                    nh_luc = 0.0
                nh_luc = nh_luc or os.path.getmtime(nh)
            mt = max(os.path.getmtime(kp), nh_luc)
            canh = plan.get("canh") or []
            giay = sum(max(0.0, float(c.get("den", 0)) - float(c.get("tu", 0))) for c in canh if isinstance(c, dict))
            anh = kq.get("khung_dau") if isinstance(kq.get("khung_dau"), str) and os.path.isfile(kq.get("khung_dau")) else ""
            dau = ""
            if canh and isinstance(canh[0], dict):
                src = (plan.get("nguon") or {}).get(canh[0].get("file")) or {}
                dau = src.get("local") or canh[0].get("file") or ""
            hook = ((plan.get("chu") or {}).get("hook") or [])
            out.append({"v": v, "ten": n, "ten_dep": ten_dep(v), "hook": " ".join(x for x in hook if isinstance(x, str)),
                        "so_canh": len(canh), "giay": round(giay, 1), "mt": mt,
                        "tay": plan.get("_tao_boi") == "sua_tay", "dang_sua": os.path.isfile(nh) and os.path.getmtime(nh) > os.path.getmtime(kp) + 1,
                        "anh": anh, "clip_dau": dau, "t_dau": float(canh[0].get("tu", 0)) + 0.5 if canh else 0,
                        "mp4": kq.get("mp4") if isinstance(kq.get("mp4"), str) and os.path.isfile(kq.get("mp4") or "") else ""})
            if dau and os.path.isfile(dau):
                with LOCK:
                    NGUON_OK.add(norm(dau))
        except Exception:
            S.log("sua-tay ds %s: %s" % (n, traceback.format_exc()))
    out.sort(key=lambda x: -x["mt"])
    return {"ds": out[:200], "thu_muc_ra": ra}


def phien_ban(v):
    ds = []
    for n in os.listdir(v):
        m = re.fullmatch(r"v(\d+)", n)
        d = os.path.join(v, n)
        if m and os.path.isdir(d):
            mp4 = [x for x in os.listdir(d) if x.lower().endswith(".mp4")]
            mp4.sort(key=lambda x: -os.path.getmtime(os.path.join(d, x)))
            kd = os.path.join(d, "khung-dau.jpg")
            ds.append({"so": int(m.group(1)), "ten": n, "mp4": os.path.join(d, mp4[0]) if mp4 else "",
                       "luc": os.path.getmtime(os.path.join(d, mp4[0])) if mp4 else os.path.getmtime(d),
                       "anh": kd if os.path.isfile(kd) else "", "tay": os.path.isfile(os.path.join(d, "dong-thoi-gian.json")) and not any(
                           x.lower().endswith(".prproj") for x in os.listdir(d))})
    ds.sort(key=lambda x: x["so"])
    return ds


def mo(v, bo_nhap=False):
    v = thu_muc_video(v)
    if bo_nhap:
        nh = os.path.join(v, "lam", "sua-tay", "dang-sua.json")
        if os.path.isfile(nh):
            os.replace(nh, nh + ".bo")
    with LOCK:
        NGUON_OK.update(nguon_dia(v))
    kq = MAY.goi("mo", {"v": v, "bo_nhap": bo_nhap})
    plan = kq["plan"]
    ng = plan.get("nguon") or {}
    # 4/11: clip CÓ trong cảnh làm bản xem nhẹ trước (theo thứ tự cảnh), clip thừa trong nguon làm sau — trước đây theo thứ tự nguon,
    # video-3 của anh: clip cảnh 2 xếp cuối sau 2 clip không dùng -> bấm phát cảnh 2 chỉ thấy ảnh tạm rất lâu
    # 4/11 tối (anh: "giật / khựng từng nhịp"): clip CHỈ có trong nguon (thư viện của video, không cảnh nào dùng) không làm ngay nữa —
    # xếp "để sau" (hang_nen: chỉ chạy khi không phát, sau mọi việc khác); video-3 có ~14 clip mà cảnh chỉ dùng vài clip
    trong_canh = [c.get("file") for c in plan.get("canh") or [] if isinstance(c, dict)]
    thu_tu = trong_canh + list(ng)
    for f in dict.fromkeys(x for x in thu_tu if x in ng):
        src = ng.get(f) or {}
        if os.path.isfile(src.get("local") or f):   # clip đã mất trên đĩa: khỏi xếp hàng làm bản xem nhẹ (treo "đang tạo" mãi)
            lam_proxy(src.get("local") or f, sau=f not in trong_canh)
    kq.update({"v": v, "ten": os.path.basename(v), "ten_dep": ten_dep(v), "ban": phien_ban(v), "xuat": trang_thai_xuat(v),
               "dang_lam": claude_dang_lam(v), "ket_qua": S.read_json(os.path.join(v, "ket-qua.json")) or {},
               "clip_mat": ten_clip_mat(plan)})
    return kq


def xem(v, plan):
    v = thu_muc_video(v)
    kiem_ke_hoach(v, plan, can_file=False, cho_trong=True)   # 0 cảnh: sua_tay_may trả bản xem trống, không gọi bộ dựng
    kq = MAY.goi("xem", {"v": v, "plan": plan}, timeout=90)
    for l in kq.get("lop") or []:
        l["url"] = "/file?p=" + quote(l.pop("png"))
    return kq


def nhap(v, plan, kp_mtime=None, phien=None, moc=None, ep=False):
    v = thu_muc_video(v)
    kiem_ke_hoach(v, plan, can_file=False, cho_trong=True)   # xoá hết cảnh vẫn tự lưu bản sửa dở (F5 mở lại vẫn trống)
    phien = str(phien)[:40] if isinstance(phien, str) and phien else None
    return MAY.goi("nhap", {"v": v, "plan": plan, "kp_mtime": kp_mtime if isinstance(kp_mtime, (int, float)) else None,
                            "phien": phien, "moc": moc if isinstance(moc, (int, float)) else 0, "ep": bool(ep)})


def luu(v, plan, ra=None):
    v = thu_muc_video(v)
    ai = claude_dang_lam(v)
    if ai:
        raise ValueError("Claude đang làm video này trong Hàng dựng (%s). Chờ xong hoặc bấm Dừng rồi lưu." % ai)
    kiem_ke_hoach(v, plan)
    return MAY.goi("luu", {"v": v, "plan": plan, "ra": ra})


def them_clip(p):
    p = str(p or "").strip().strip('"')
    if not p or not os.path.isfile(p) or os.path.splitext(p)[1].lower() not in VIDEO_EXT:
        raise ValueError("Không thấy clip này")
    if not S.allowed_path(p, video=True):
        raise ValueError("Clip phải nằm trong thư mục clip đã mở trong app")
    x = MAY.goi("do_clip", {"p": p})
    with LOCK:
        NGUON_OK.add(norm(p))
    lam_proxy(p)
    return x


def tao_moi(data):
    tm = str(data.get("thu_muc") or "").strip().strip('"')
    if not tm or not os.path.isdir(tm):
        raise ValueError("Không thấy thư mục clip")
    clips = data.get("clip") or []
    if not isinstance(clips, list) or not clips:
        raise ValueError("Chọn ít nhất 1 clip")
    co = {fn.lower(): fn for fn in os.listdir(tm)}
    ds = []
    for c in clips[:60]:
        fn = co.get(os.path.basename(str(c)).lower())
        if not fn or os.path.splitext(fn)[1].lower() not in VIDEO_EXT:
            raise ValueError("Không thấy clip %s trong thư mục" % c)
        p = os.path.join(tm, fn)
        if not S.allowed_path(p, video=True):
            raise ValueError("Mở thư mục clip trong app trước (bấm Chọn thư mục)")
        ds.append(p)
    ra = ra_dir()
    if not ra:
        raise ValueError("Chưa đặt thư mục lưu video")
    os.makedirs(ra, exist_ok=True)
    goc = S.slugify(data.get("ten") or os.path.basename(tm.rstrip("\\/"))) or "video"
    slug, i = goc, 2
    while os.path.exists(os.path.join(ra, slug)):
        slug, i = "%s-%d" % (goc, i), i + 1
    with LOCK:
        NGUON_OK.update(norm(p) for p in ds)
    them = {}  # bấm "Tự dựng tay" ở cột Video mới: mang theo hook, giá, máy, kiểu đã chọn
    hook = data.get("hook")
    if isinstance(hook, list):
        them["hook"] = [str(x or "")[:60] for x in hook[:2]]
    for k in ("gia", "may"):
        if isinstance(data.get(k), str):
            them[k] = data[k][:60]
    if data.get("che_do") in ("xoay_vong", "dung_gu", "tu_chon"):
        them["che_do"] = data["che_do"]
    if isinstance(data.get("kieu"), dict):
        them["kieu"] = {str(k)[:30]: str(v)[:30] for k, v in list(data["kieu"].items())[:30] if isinstance(v, str)}
    MAY.goi("moi", dict(them, ra=ra, slug=slug, clip=[xuoi(p) for p in ds]), timeout=180)
    ghi_ten_dep(os.path.join(ra, slug), data.get("ten"))   # r29 (A13): giữ tên có dấu để hiện, thư mục vẫn slug
    for p in ds:
        lam_proxy(p)
    return {"v": os.path.join(ra, slug)}


# ---------------------------------------------------------------- bản xem nhẹ (proxy) cho trình duyệt
PROXY = {}  # norm(clip) -> {"tt": cho|dang|xong|loi, "p": file}
_POOL = ThreadPoolExecutor(max_workers=2)


def _hdr(p):
    fpb = S.tim_ffmpeg("ffprobe")
    try:
        r = subprocess.run([fpb, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer", "-of",
                            "default=nw=1:nk=1", p], capture_output=True, timeout=30, creationflags=NO_WIN if IS_WIN else 0)
        t = (r.stdout or b"").decode("ascii", "ignore").strip()
        return t if t in ("arib-std-b67", "smpte2084") else None
    except Exception:
        return None


PROXY_BAN = "v2"   # 4/11 anh: "hiển thị video bị mờ quá" -> bản xem nhẹ 720×1280 CRF 23 (trước 540×960 CRF 30)


def _proxy_file(p, ban=PROXY_BAN):
    st = os.stat(p)
    k = hashlib.md5(("%s|%s|%s" % (norm(p), st.st_size, int(st.st_mtime)) + ("|" + ban if ban else "")).encode("utf-8")).hexdigest()
    return os.path.join(S.CACHE, "proxy", k + ".mp4")


def _proxy_cu(p):
    """Bản xem nhẹ kiểu cũ (540×960) nếu đã có: dùng tạm trong lúc làm bản nét hơn, khỏi phải chờ."""
    try:
        f = _proxy_file(p, "")
        return f if os.path.isfile(f) and os.path.getsize(f) > 1000 else None
    except OSError:
        return None


def _lam(p, out, uu=0):
    key = norm(p)
    try:
        ff = S.tim_ffmpeg("ffmpeg")
        if not ff:
            raise RuntimeError("Chưa cài bộ dựng (ffmpeg)")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        trc = _hdr(p)
        # thu nhỏ TRƯỚC rồi mới chuyển màu HDR (4/11): chuyển màu ở 4K chậm gấp nhiều lần; 720×1280 + CRF 23 nét hơn bản cũ (540×960, CRF 30)
        vf = "scale=w='if(gt(iw,ih),1280,-2)':h='if(gt(iw,ih),-2,1280)':flags=bicubic"
        if trc:  # HDR iPhone -> SDR như bản xuất (dung_may_chu.hdr_chain)
            vf += (f",setparams=color_primaries=bt2020:color_trc={trc}:colorspace=bt2020nc:range=tv,zscale=t=linear:npl=100,"
                   "format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
        vf += ",fps=30,format=yuv420p"
        tmp = out + ".%d.part.mp4" % os.getpid()
        # 4/11 (anh: "clip chạy bị rung"): làm bản xem nhẹ ở mức ưu tiên THẤP (Windows: BELOW_NORMAL) -> lúc anh bấm phát trong khi máy
        # còn làm bản xem nhẹ các clip khác, trình duyệt vẫn được ưu tiên giải mã video (đo: máy bận thì khung xem tua giật mỗi 0,25s)
        # 4/11 tối (anh: "giật / khựng từng nhịp vài giây"): qua hang_nen — lúc anh đang PHÁT chỉ 1 việc gấp nhất chạy, việc khác tạm dừng hẳn
        import hang_nen
        import card as CARD
        hw = CARD.giai_ma()   # 10/11: đọc clip gốc (HEVC 4K / 10-bit) bằng card nếu máy có; khung tải về CPU, chuỗi filter như cũ

        def lenh(vao):
            return [ff, "-v", "error", "-y"] + vao + ["-i", p, "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf, "-c:v", "libx264",
                                                     "-preset", "veryfast", "-crf", "23", "-g", "15", "-keyint_min", "15", "-sc_threshold", "0",
                                                     "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart", tmp]
        r = hang_nen.chay(lenh(["-hwaccel", hw] if hw else []), uu=uu, timeout=3600, ten=p)
        if hw and (r.returncode or not os.path.isfile(tmp) or os.path.getsize(tmp) < 1000):   # card lỗi: làm lại y lệnh bằng CPU
            r = hang_nen.chay(lenh([]), uu=uu, timeout=3600, ten=p)
            if not r.returncode and os.path.isfile(tmp) and os.path.getsize(tmp) >= 1000:
                CARD.bao_loi_gm(hw, "làm bản xem nhẹ " + os.path.basename(p))
        if r.returncode or not os.path.isfile(tmp) or os.path.getsize(tmp) < 1000:
            raise RuntimeError((r.stderr or b"").decode("utf-8", "replace")[-400:])
        os.replace(tmp, out)
        with LOCK:
            PROXY[key] = {"tt": "xong", "p": out}
    except Exception as e:
        S.log("sua-tay proxy %s: %s" % (p, e))
        with LOCK:
            PROXY[key] = {"tt": "loi", "p": out, "loi": str(e)[:200]}


_POOL_SAU = ThreadPoolExecutor(max_workers=1)   # 4/11 tối: clip chỉ có trong thư viện của video — 1 việc, sau cùng, khi máy rảnh


def _ban_proxy():
    """Còn bản xem nhẹ clip trong cảnh đang chờ / đang làm, hoặc việc nền gấp hơn đang chạy (hang_nen)."""
    import hang_nen
    with LOCK:
        if any(x.get("tt") in ("cho", "dang") and not x.get("sau") for x in PROXY.values()):
            return True
    return hang_nen.so_viec(2) > 0


def lam_proxy(p, sau=False):
    """sau=True (4/11 tối): clip chỉ có trong thư viện của video -> làm sau cùng, chỉ khi không phát và máy hết việc gấp.
    Clip đang "để sau" mà anh cần ngay (vừa thêm vào cảnh, bấm xem trong Thư viện) -> gọi lại không có sau = lên hàng thường."""
    if not p or not os.path.isfile(p):
        return
    key = norm(p)
    out = _proxy_file(p)
    with LOCK:
        cu = PROXY.get(key)
        if os.path.isfile(out):
            PROXY[key] = {"tt": "xong", "p": out}
            return
        if cu and cu.get("tt") in ("dang", "cho") and cu.get("p") == out:
            if not (cu.get("sau") and not sau and cu["tt"] == "cho"):
                return
            cu["sau"] = False   # lên hàng thường
        else:
            PROXY[key] = {"tt": "cho", "p": out, "sau": bool(sau)}

    def chay(la_sau):
        import hang_nen
        if la_sau:   # chờ máy rảnh: không phát ≥ 5s + hết việc gấp
            while True:
                with LOCK:
                    x = PROXY.get(key)
                    if not x or x.get("tt") != "cho" or not x.get("sau"):
                        return
                if hang_nen.ranh() and not _ban_proxy():
                    break
                time.sleep(1.0)
        with LOCK:
            x = PROXY.get(key)
            if not x or x.get("tt") != "cho" or x.get("p") != out or (la_sau and not x.get("sau")):
                return   # đã có hàng khác làm / đã xong
            x["tt"] = "dang"
            uu = 3 if x.get("sau") else 0
        _lam(p, out, uu)
    (_POOL_SAU if sau else _POOL).submit(chay, bool(sau))


def proxy_tt(ds):
    out = {}
    for f in ds or []:
        p = str(f or "")
        with LOCK:
            x = PROXY.get(norm(p)) if p else None
        if not x and p and os.path.isfile(p) and (cho_xem(os.path.realpath(p)) or (
                os.path.splitext(p)[1].lower() in VIDEO_EXT and S.allowed_path(p, video=True))):
            # clip của video đang sửa, hoặc clip anh vừa chọn ở trang chủ Sửa tay (trong thư mục clip đã mở): làm bản xem nhẹ trước
            with LOCK:
                NGUON_OK.add(norm(p))
            lam_proxy(p)
            with LOCK:
                x = PROXY.get(norm(p))
        elif x and x.get("sau") and x["tt"] == "cho":   # clip "để sau" mà trang hỏi tới (vừa thêm vào cảnh / bấm xem): làm ngay
            lam_proxy(p)
        cu = _proxy_cu(p) if x and x["tt"] in ("cho", "dang") and os.path.isfile(p) else None
        if not x:
            out[f] = {"tt": "khong"}
        elif x["tt"] == "xong":
            out[f] = {"tt": "xong", "url": "/file?p=" + quote(x["p"])}
        elif cu:   # đang làm bản nét hơn: phát tạm bản cũ, xong trang tự đổi
            out[f] = {"tt": "xong", "url": "/file?p=" + quote(cu), "tam": True}
        else:
            out[f] = {"tt": x["tt"], "loi": x.get("loi")}
    return out


# ---------------------------------------------------------------- xuất video
XUAT = {}  # norm(v) -> trạng thái


def trang_thai_xuat(v):
    with LOCK:
        x = XUAT.get(norm(v))
        if not x:
            return None
        y = {k: x.get(k) for k in ("nhap", "buoc", "bat_dau", "xong_luc", "uoc", "mp4", "loi", "canh_bao", "ban", "giay", "dang",
                                   "kp_mtime", "ma", "them", "them_loi", "dinh_dang", "card")}
    if y.get("mp4") and os.path.isfile(y["mp4"]):
        y["url"] = "/file?p=" + quote(y["mp4"]) + "&v=%d" % int(os.path.getmtime(y["mp4"]))
    y["giay_da"] = round((y.get("xong_luc") or time.time()) - (y.get("bat_dau") or time.time()))
    return y


def _so_ban(v):
    so = [int(m.group(1)) for n in os.listdir(v) for m in [re.fullmatch(r"v(\d+)", n)] if m and os.path.isdir(os.path.join(v, n))]
    return (max(so) + 1) if so else 1


def _dinh_dang(dd):
    """Định dạng xuất từ trang -> dict sạch (bỏ giá trị lạ)."""
    dd = dd if isinstance(dd, dict) else {}
    out = {"chat_luong": dd.get("chat_luong") if dd.get("chat_luong") in ("nhe", "chuan", "cao") else "chuan"}
    try:
        f = int(dd.get("fps") or 0)
    except (TypeError, ValueError):
        f = 0
    if f in (24, 25, 30, 50, 60):
        out["fps"] = f
    out["them"] = [x for x in ("720p", "hevc", "mov") if x in (dd.get("them") or [])]
    return out


def xuat(v, plan, la_nhap, kp_mtime=None, dinh_dang=None, phien=None):
    v = thu_muc_video(v)
    dd = _dinh_dang(dinh_dang)
    ai = claude_dang_lam(v)
    if ai and not la_nhap:
        raise ValueError("Claude đang làm video này trong Hàng dựng (%s). Chờ xong rồi xuất." % ai)
    kiem_ke_hoach(v, plan)
    giay = sum(max(0.0, float(c["den"]) - float(c["tu"])) for c in plan["canh"])
    st = {"dang": True, "nhap": bool(la_nhap), "buoc": "Bắt đầu", "bat_dau": time.time(), "ban": None, "giay": round(giay, 1),
          "uoc": round(max(20, giay * (2.2 if la_nhap else {"nhe": 3.0, "cao": 5.5}.get(dd["chat_luong"], 3.8)
                                       + (0 if la_nhap else 0.5 * ("720p" in dd["them"]) + 2.0 * ("hevc" in dd["them"]))))),
          "canh_bao": [], "mp4": "", "loi": "", "ma": "%x" % int(time.time() * 1000), "them": [], "them_loi": [],
          "dinh_dang": None if la_nhap else dd}
    with LOCK:  # giữ chỗ ngay trong khoá: bấm 2 lần không chạy 2 bản
        dang = [x for x in XUAT.values() if x.get("dang")]
        x = XUAT.get(norm(v))
        if x and x.get("dang"):
            raise ValueError("Video này đang dựng, chờ xong (hoặc bấm Dừng)")
        if len(dang) >= XUAT_TOI_DA:
            raise ValueError("Đang dựng %d bản cùng lúc, chờ 1 bản xong rồi bấm lại" % len(dang))
        XUAT[norm(v)] = st
        M = None
        phien = str(phien)[:40] if isinstance(phien, str) and phien else None
        viec = {"v": v, "nhap": bool(la_nhap), "plan": plan, "dinh_dang": None if la_nhap else dd, "phien": phien}
        if not la_nhap:
            n = _so_ban(v)
            slug = re.sub(r"-v\d+$", "", os.path.basename(v))
            M = os.path.join(v, "v%d" % n)
            os.makedirs(M, exist_ok=True)
            viec.update({"thu_muc_may": M, "ten_file": "%s-v%d.mp4" % (slug, n)})
            st["ban"] = "v%d" % n
    try:
        nhap(v, plan, kp_mtime, phien, ep=True)  # lưu bản đang sửa (anh bấm xuất = bản này thắng); kế hoạch chỉ ghi khi dựng xong bản đẹp
        d = os.path.join(v, "lam", "sua-tay")
        os.makedirs(d, exist_ok=True)
        vp = os.path.join(d, "viec-xuat.json")
        _ghi(vp, viec)
        e = S.engine()
        kw = {"creationflags": NO_WIN | 0x00000200} if IS_WIN else {"start_new_session": True}
        p = subprocess.Popen([e["py"], os.path.join(APP, "sua_tay_may.py"), "xuat", vp], cwd=e["dir"], env=MAY._env(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    except Exception:
        with LOCK:
            XUAT.pop(norm(v), None)
        _bo_thu_muc_loi(M)
        raise
    with LOCK:
        st["pid"] = p.pid

    def theo():
        loi_ds = []

        def doc_err():
            for line in iter(p.stderr.readline, b""):
                loi_ds.append(line.decode("utf-8", "replace").rstrip())
                del loi_ds[:-60]
        threading.Thread(target=doc_err, daemon=True).start()
        for raw in iter(p.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            with LOCK:
                if line.startswith("BUOC="):
                    st["buoc"] = line[5:]
                elif line.startswith("LOI="):
                    st["loi"] = line[4:]
                elif line.startswith("CANH_BAO="):
                    try:
                        st["canh_bao"] = json.loads(line[9:])
                    except ValueError:
                        pass
                elif line.startswith("XONG="):
                    try:
                        x = json.loads(line[5:])
                        st["mp4"] = x.get("mp4") or ""
                        st["kp_mtime"] = x.get("kp_mtime")
                        st["them"] = x.get("them") or []
                        st["them_loi"] = x.get("them_loi") or []
                        st["_xong"] = x
                        st["card"] = _card_xuat(x)   # 10/11: lần này mã hoá / đọc clip bằng gì (trang hiện dưới dòng Xong)
                    except ValueError:
                        pass
        rc = p.wait()
        with LOCK:
            st["dang"] = False
            st["xong_luc"] = time.time()
            if st.get("dung"):
                st["loi"] = "Đã dừng"
            elif rc and not st["loi"]:
                st["loi"] = "Dựng lỗi: " + " ".join(loi_ds[-6:])[-500:]
            if st["loi"]:
                S.log("sua-tay xuat %s: %s | %s" % (v, st["loi"], " | ".join(loi_ds[-20:])[-2000:]))
            hong = bool(st["loi"])
        _log_xuat(v, st, loi_ds)
        if hong:
            _bo_thu_muc_loi(M)
    threading.Thread(target=theo, daemon=True).start()
    return trang_thai_xuat(v)


def _card_xuat(x):
    try:
        import card as CARD
        mt = CARD.mo_ta_xuat(x)
        return {k: mt[k] for k in ("chu", "lui", "giai_ma")}
    except Exception:  # noqa
        return None


def _log_xuat(v, st, loi_ds):
    """10/11: mỗi lần xuất 1 dòng app-log: bộ mã hoá / giải mã đã dùng, video dài, mất bao lâu, có lùi CPU không (kiểm máy tiệm)."""
    try:
        import card as CARD
        x = st.get("_xong") or {}
        mt = CARD.mo_ta_xuat(x) if x else None
        dd = st.get("dinh_dang") or {}
        ban = "bản nháp 540p" if st.get("nhap") else "%s 1080p %s%s" % (st.get("ban") or "", dd.get("chat_luong") or "chuan",
                                                                          (" + " + ",".join(dd.get("them") or [])) if dd.get("them") else "")
        if st.get("loi"):
            kq = "LỖI: " + str(st["loi"])[:160]
        else:
            kq = "%s | mã hoá %s | giải mã %s%s | lùi CPU: %s" % (
                mt["chu"], "+".join(mt["ma_hoa"]) or "?", mt["giai_ma"] or "CPU",
                (" (card được %d / %d lệnh đọc clip)" % (mt["giai_ma_ok"], mt["giai_ma_lan"])) if mt["giai_ma_lan"] else "",
                ("có (mã hoá %d, giải mã %d)" % (mt["lui_ma_hoa"], mt["lui_giai_ma"])) if mt["lui"] else "không")
        lui = [l for l in loi_ds if "[ma_hoa]" in l][:4]
        S.log("xuat card | %s | %s | video %.1fs | mất %ds | %s%s" % (
            os.path.basename(v), ban, float(x.get("giay") or st.get("giay") or 0), round((st.get("xong_luc") or time.time()) - st["bat_dau"]),
            kq, (" | " + " · ".join(lui)) if lui else ""))
        if mt and mt["lui"]:   # có bước card lỗi: đọc lại nhớ (lỗi 2 lần thì thôi dùng loại đó) cho dòng trạng thái trong hộp Xuất
            CARD.lam_moi()
    except Exception as e:  # noqa  ghi log không được thì thôi, không ảnh hưởng bản xuất
        S.log("xuat card: không ghi được dòng log (%s)" % e)


def _bo_thu_muc_loi(M):
    """Bản đẹp dựng lỗi / bị dừng: đổi tên thư mục v<n> thành _loi-v<n>-<giờ> (không xoá; số bản sau không bị nhảy)."""
    if not M or not os.path.isdir(M):
        return
    try:
        if not os.listdir(M):
            os.rmdir(M)
            return
        dich = os.path.join(os.path.dirname(M), "_loi-%s-%s" % (os.path.basename(M), time.strftime("%H%M%S")))
        for _ in range(20):  # Windows: ffmpeg vừa bị tắt còn giữ file một chút
            try:
                os.replace(M, dich)
                return
            except PermissionError:
                time.sleep(0.5)
    except OSError as e:
        S.log("sua-tay bo thu muc loi %s: %s" % (M, e))


def _ghi(p, o):
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def dung_xuat(v):
    v = thu_muc_video(v)
    with LOCK:
        st = XUAT.get(norm(v))
        if not st or not st.get("dang"):
            return {"ok": True}
        st["dung"] = True
        pid = st.get("pid")
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, creationflags=NO_WIN)
        else:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        pass
    return {"ok": True}


# ---------------------------------------------------------------- tự tạo phụ đề từ lời nói (3/11)
# Mỗi lần 1 tiến trình riêng `sua_tay_may.py nghe viec.json` (máy nghe sherpa của bộ dựng; xem trước không bị chặn).
# Mỗi clip nghe 1 lần, cache ở _cache/nghe/. Trả các câu phụ đề đã neo vào cảnh (_neo), trang áp thành 1 bước Ctrl+Z.
NGHE = {}


def nghe(v, plan, chi=None):
    """chi = [id khối tiếng tách] (r32, giọng AI đọc lại: giong_de.py): chỉ nghe các khối này, video có giọng AI gõ lời vẫn nghe được."""
    v = thu_muc_video(v)
    kiem_ke_hoach(v, plan)
    if plan.get("giong") and chi is None:
        raise ValueError("Video dùng giọng đọc AI: phụ đề đi theo giọng, không nghe lời trong clip")
    nguon = plan.get("nguon") or {}
    ds = []
    for c in plan.get("canh") or []:
        if c.get("tach_am") or chi is not None:   # cảnh đã tách tiếng (4/11): cảnh im, lời nghe ở khối tiếng tách (dưới)
            continue
        local = ((nguon.get(c.get("file")) or {}).get("local")) or c.get("file")
        if local and os.path.isfile(local):
            ds.append({"id": c.get("_id"), "file": c.get("file"), "src": local, "tu": float(c["tu"]), "den": float(c["den"])})
    for k in plan.get("am_tach") or []:   # tiếng tách: nghe đúng đoạn tiếng đang phát (khối đã dời / cắt / kéo dài), câu đi theo khối
        if chi is not None and k.get("id") not in chi:
            continue
        local = ((nguon.get(k.get("nguon")) or {}).get("local")) or k.get("nguon")
        if local and os.path.isfile(local):
            g = next((c.get("_id") for c in plan.get("canh") or [] if c.get("tach_am") and c.get("tach_am") == k.get("goc")), None)
            ds.append({"id": g, "file": k.get("nguon"), "src": local, "tu": float(k["tu"]), "den": float(k["den"]), "am": True})
    if not ds:
        raise ValueError("Không thấy clip nào của video trên máy")
    with LOCK:
        for x in NGHE.values():
            if x.get("dang") and x["v"] == norm(v) and x.get("chi") == (sorted(chi) if chi is not None else None):
                return {"ma": x["ma"]}
        for k in sorted(NGHE)[:-20]:
            if not NGHE[k].get("dang"):
                NGHE.pop(k, None)
        ma = "%x" % int(time.time() * 1000)
        st = NGHE[ma] = {"ma": ma, "v": norm(v), "dang": True, "buoc": "Bắt đầu nghe", "bat_dau": time.time(), "kq": None, "loi": "", "canh_bao": []}
        if chi is not None:
            st["chi"] = sorted(chi)
    d = os.path.join(v, "lam", "sua-tay")
    os.makedirs(d, exist_ok=True)
    vp = os.path.join(d, "viec-nghe.json")
    _ghi(vp, {"canh": ds, "kho": os.path.join(S.CACHE, "nghe")})
    e = S.engine()
    kw = {"creationflags": NO_WIN | 0x00000200} if IS_WIN else {"start_new_session": True}
    try:
        p = subprocess.Popen([e["py"], os.path.join(APP, "sua_tay_may.py"), "nghe", vp], cwd=e["dir"], env=MAY._env(),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    except Exception as ex:
        with LOCK:
            st.update(dang=False, loi="Không chạy được máy nghe: %s" % ex)
        raise ValueError(st["loi"])
    st["pid"] = p.pid

    def theo():
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
                    st["buoc"] = line[5:]
                elif line.startswith("LOI="):
                    st["loi"] = line[4:]
                elif line.startswith("CANH_BAO="):
                    try:
                        st["canh_bao"] += json.loads(line[9:])
                    except ValueError:
                        pass
                elif line.startswith("XONG="):
                    try:
                        kq = json.loads(line[5:])
                    except ValueError:
                        pass
        code = p.wait()
        with LOCK:
            st["dang"] = False
            st["giay_da"] = round(time.time() - st["bat_dau"])
            if kq is not None:
                st["kq"] = kq
            elif not st["loi"]:
                st["loi"] = "Máy nghe dừng giữa chừng (mã %s)" % code
        if kq is None:
            S.log("sua-tay nghe loi %s: %s | %s" % (os.path.basename(v), st["loi"], " / ".join(loi_ds[-6:])))
    threading.Thread(target=theo, daemon=True).start()
    return {"ma": ma}


def nghe_tt(ma):
    with LOCK:
        st = NGHE.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy việc nghe này (app vừa khởi động lại?)"}
        out = {k: st.get(k) for k in ("ma", "dang", "buoc", "kq", "loi", "canh_bao")}
        out["giay_da"] = round(time.time() - st["bat_dau"])
        return out


# ---------------------------------------------------------------- Mẫu kiểu (3/11)
# Tab Kiểu: chọn chuyển cảnh / chuyển động / điểm nhấn / lớp phủ / màu… thì trang gửi 1 kế hoạch cắt ngắn (~3 giây, 2 cảnh quanh
# vạch đỏ, không chữ) -> dựng bản nháp 540p bằng đúng đường xuất (sua_tay_may.py xuat) vào thư mục riêng
# <video>/lam/sua-tay/mau/<băm>/ (giả làm "thư mục video" để không đụng bản nháp thật), trang phát trong khung xem.
# Cùng kế hoạch thì dùng lại file đã dựng. Mỗi video chỉ 1 mẫu đang dựng: bấm mẫu khác thì dừng mẫu cũ.
MAU_KIEU = {}


def mau_kieu(v, plan):
    v = thu_muc_video(v)
    kiem_ke_hoach(v, plan)
    if len(plan.get("canh") or []) > 3 or sum(float(c["den"]) - float(c["tu"]) for c in plan["canh"]) > 8.5:
        raise ValueError("Mẫu chỉ dựng đoạn ngắn (≤ 3 cảnh, ≤ 8 giây)")
    h = hashlib.md5(json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:14]
    goc = os.path.join(v, "lam", "sua-tay", "mau")
    d = os.path.join(goc, h)
    mp4 = os.path.join(d, "lam", "sua-tay", "nhap", "ban-nhap.mp4")
    if os.path.isfile(mp4):
        return {"ma": h, "dang": False, "mp4": xuoi(mp4)}
    cu = None
    with LOCK:
        st = MAU_KIEU.get(h)
        if st and st.get("dang"):
            return {"ma": h, "dang": True}
        for k, x in MAU_KIEU.items():
            if x.get("dang") and x["v"] == norm(v):
                x["dung"] = True
                cu = x.get("pid")
        for k in sorted(MAU_KIEU, key=lambda k: MAU_KIEU[k]["bat_dau"])[:-30]:
            if not MAU_KIEU[k].get("dang"):
                MAU_KIEU.pop(k, None)
        st = MAU_KIEU[h] = {"ma": h, "v": norm(v), "dang": True, "bat_dau": time.time(), "mp4": "", "loi": ""}
    _giet(cu)
    try:  # dọn mẫu cũ: giữ 40 thư mục mới nhất
        ds = sorted((os.path.join(goc, x) for x in os.listdir(goc) if x != h), key=os.path.getmtime)
        for x in ds[:-40]:
            shutil.rmtree(x, ignore_errors=True)
    except OSError:
        pass
    os.makedirs(d, exist_ok=True)
    vp = os.path.join(d, "viec-mau.json")
    _ghi(vp, {"v": d, "nhap": True, "plan": plan})
    e = S.engine()
    kw = {"creationflags": NO_WIN | 0x00000200} if IS_WIN else {"start_new_session": True}
    try:
        p = subprocess.Popen([e["py"], os.path.join(APP, "sua_tay_may.py"), "xuat", vp], cwd=e["dir"], env=MAY._env(),
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **kw)
    except Exception as ex:  # noqa
        with LOCK:
            st.update(dang=False, loi="Không chạy được bộ dựng: %s" % ex)
        return {"ma": h, "dang": False, "loi": st["loi"]}
    with LOCK:
        st["pid"] = p.pid

    def theo():
        loi = ""
        for raw in iter(p.stdout.readline, b""):
            line = raw.decode("utf-8", "replace").strip()
            if line.startswith("LOI="):
                loi = line[4:]
        p.wait()
        with LOCK:
            st["dang"] = False
            if st.get("dung"):
                st["loi"] = "Đã đổi sang mẫu khác"
            elif os.path.isfile(mp4):
                st["mp4"] = xuoi(mp4)
            else:
                st["loi"] = loi or "Dựng mẫu lỗi"
    threading.Thread(target=theo, daemon=True).start()
    return {"ma": h, "dang": True}


def mau_kieu_tt(ma):
    with LOCK:
        st = MAU_KIEU.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy mẫu này (app vừa khởi động lại?)"}
        out = {k: st.get(k) for k in ("ma", "dang", "mp4", "loi")}
        out["giay_da"] = round(time.time() - st["bat_dau"], 1)
        return out


# ---------------------------------------------------------------- Nhờ Claude (3/11)
# Anh gõ yêu cầu trong trình sửa -> Claude Code trên máy (tài khoản đang đăng nhập, không API) đọc kế hoạch gọn + ảnh các cảnh,
# trả danh sách thao tác (JSON). Trang hiện đề xuất, anh bấm Đồng ý mới áp (Ctrl+Z được). Claude chỉ có công cụ Read,
# chạy trong <video>/lam/sua-tay/claude/<mã>/, không sửa file nào.
NHO = {}            # mã -> trạng thái
NHO_GIAY = 300      # quá chừng này thì dừng


def _nho_dir(v, ma):
    return os.path.join(v, "lam", "sua-tay", "claude", ma)


def _don_nho(v):
    goc = os.path.join(v, "lam", "sua-tay", "claude")
    try:
        ds = sorted([d for d in os.listdir(goc) if d != "khung" and os.path.isdir(os.path.join(goc, d))])
    except OSError:
        return
    for d in ds[:-8]:
        shutil.rmtree(os.path.join(goc, d), ignore_errors=True)


def nho(v, plan, yeu_cau, gon, lich_su=None):
    v = thu_muc_video(v)
    yc = str(yeu_cau or "").strip()[:2000]
    if not yc:
        raise ValueError("Gõ việc cần Claude làm trước đã")
    if not isinstance(gon, dict) or not isinstance(gon.get("canh"), list):
        raise ValueError("Thiếu thông tin video, mở lại trang")
    kiem_ke_hoach(v, plan, can_file=False)
    cmd = list(S.CFG.get("lenh_claude_nho") or []) or S.resolve_claude()   # lenh_claude_nho: chỉ để thử (máy dev)
    if not cmd:
        raise ValueError("Không tìm thấy Claude Code trên máy")
    with LOCK:
        for x in NHO.values():
            if x.get("dang") and x["v"] == norm(v):
                raise ValueError("Claude đang làm 1 yêu cầu cho video này, chờ xong hoặc bấm Dừng")
        for k in sorted(NHO)[:-20]:
            if not NHO[k].get("dang"):
                NHO.pop(k, None)
        ma = "%x" % int(time.time() * 1000)
        NHO[ma] = {"ma": ma, "v": norm(v), "dang": True, "buoc": "Chuẩn bị ảnh các cảnh", "bat_dau": time.time(), "kq": None, "loi": ""}
    threading.Thread(target=_nho_chay, args=(ma, v, plan, yc, gon, lich_su or [], cmd), daemon=True).start()
    return {"ma": ma}


def nho_tt(ma):
    with LOCK:
        st = NHO.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy yêu cầu này (app vừa khởi động lại?)"}
        out = {k: st.get(k) for k in ("ma", "dang", "buoc", "kq", "loi")}
        out["giay_da"] = round(time.time() - st["bat_dau"])
        return out


def nho_dung(ma):
    with LOCK:
        st = NHO.get(str(ma or ""))
        if not st or not st.get("dang"):
            return {"ok": True}
        st["dung"] = True
        pid = st.get("pid")
    _giet(pid)
    return {"ok": True}


def _giet(pid):
    if not pid:
        return
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, creationflags=NO_WIN)
        else:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:
        pass


def _nho_set(ma, **kw):
    with LOCK:
        if ma in NHO:
            NHO[ma].update(kw)
            return not NHO[ma].get("dung")
    return False


def _anh_canh(v, W, plan, gon, ma=None):
    """Ảnh các cảnh (3 khung / cảnh, 6 cảnh / trang) bằng python bộ dựng. Lỗi thì trả [] (Claude làm không cần ảnh).
    ma: mã yêu cầu Nhờ Claude -> ghi pid để nút Dừng tắt được ngay cả lúc đang làm ảnh (4/11)."""
    nguon = plan.get("nguon") or {}
    ds = []
    for i, c in enumerate(plan.get("canh") or []):
        g = next((x for x in gon["canh"] if x.get("id") == c.get("_id")), {}) or {}
        local = ((nguon.get(c.get("file")) or {}).get("local")) or c.get("file")
        if not local or not os.path.isfile(local):
            continue
        with LOCK:
            px = PROXY.get(norm(local))
        src = px["p"] if px and px.get("tt") == "xong" and os.path.isfile(px["p"]) else local
        tv = g.get("tren_video") or []
        nhan = ["mã %s" % c.get("_id"), os.path.splitext(os.path.basename(str(c.get("file"))))[0],
                "clip giây %s–%s" % (("%.1f" % float(c["tu"])).replace(".", ","), ("%.1f" % float(c["den"])).replace(".", ","))]
        if len(tv) == 2:
            nhan.append("video %s–%s" % (("%.1f" % tv[0]).replace(".", ","), ("%.1f" % tv[1]).replace(".", ",")))
        if c.get("mo_ta"):
            mt = str(c["mo_ta"])
            nhan += [mt[:24], mt[24:48]] if len(mt) > 24 else [mt]
        ds.append({"so": i + 1, "id": c.get("_id"), "src": src, "tu": float(c["tu"]), "den": float(c["den"]), "nhan": "\n".join(nhan)})
    if not ds:
        return []
    vp = os.path.join(W, "viec-anh.json")
    _ghi(vp, {"ra": W, "kho": os.path.join(v, "lam", "sua-tay", "claude", "khung"), "canh": ds})
    e = S.engine()
    kw = {"creationflags": NO_WIN | 0x00000200} if IS_WIN else {"start_new_session": True}
    try:
        p = subprocess.Popen([e["py"], os.path.join(APP, "sua_tay_may.py"), "anh-canh", vp], cwd=e["dir"], env=MAY._env(),
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, **kw)
        if ma:
            with LOCK:
                if ma in NHO:
                    NHO[ma]["pid"] = p.pid
                    if NHO[ma].get("dung"):
                        _giet(p.pid)
        try:
            out, _ = p.communicate(timeout=240)
        except subprocess.TimeoutExpired:
            _giet(p.pid)
            out, _ = p.communicate()
        if ma:
            with LOCK:
                if ma in NHO and NHO[ma].get("pid") == p.pid:
                    NHO[ma]["pid"] = None   # tiến trình đã xong: khỏi giết nhầm pid cũ
        dong = [x for x in (out or b"").decode("utf-8", "replace").splitlines() if x.startswith("{")]
        return [os.path.basename(p) for p in json.loads(dong[-1])["trang"]] if dong else []
    except Exception as ex:  # noqa
        S.log("sua-tay nho anh-canh: %s" % ex)
        return []


def _lay_json(txt):
    txt = str(txt or "")
    m = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.S)
    for x in reversed(m):
        try:
            return json.loads(x)
        except ValueError:
            pass
    a, b = txt.find("{"), txt.rfind("}")
    if a >= 0 and b > a:
        try:
            return json.loads(txt[a:b + 1])
        except ValueError:
            pass
    return None


def _nho_tien_ich():
    """Phần prompt: tiện ích đang bật + hướng dẫn lệnh script (prompts/script-api.md)."""
    try:
        ds = TI.ds_bat()
    except Exception:  # noqa
        ds = []
    dong = []
    for x in ds:
        hoi = ", ".join("%s (%s%s)" % (h["ten"], "số" if h["kieu"] == "so" else "chữ",
                                        ", mặc định " + h["mac_dinh"] if h.get("mac_dinh") else "") for h in x.get("hoi") or [])
        dong.append("- `%s` — %s: %s%s" % (x["id"], x["ten"], x.get("mo_ta") or "", (" Ô hỏi (đưa vào \"vao\"): " + hoi) if hoi else ""))
    try:
        with open(TI.HUONG_DAN, encoding="utf-8") as f:
            hd = f.read().strip()
    except OSError:
        hd = ""
    return ("Tiện ích đang bật trên máy anh:\n" + ("\n".join(dong) if dong else "(chưa có tiện ích nào)") +
            "\n\n### Lệnh dùng trong script\n" + hd)


def _nho_chay(ma, v, plan, yc, gon, lich_su, cmd):
    W = _nho_dir(v, ma)
    try:
        os.makedirs(W, exist_ok=True)
        _don_nho(v)
        anh = _anh_canh(v, W, plan, gon, ma)
        if not _nho_set(ma, buoc="Claude đang đọc video"):
            # 4/11: anh bấm Dừng lúc đang "Chuẩn bị ảnh các cảnh": trước đây return mà không tắt "dang" -> yêu cầu treo mãi,
            # video đó không nhờ Claude được nữa tới khi khởi động lại app
            with LOCK:
                if ma in NHO:
                    NHO[ma].update(dang=False, loi="Đã dừng", pid=None)
            return
        _ghi(os.path.join(W, "video.json"), gon)
        with open(os.path.join(S.PROMPTS, "nho-claude.md"), encoding="utf-8") as f:
            mau = f.read()
        ls = ""
        for x in (lich_su or [])[-4:]:
            if isinstance(x, dict) and x.get("yeu_cau"):
                ls += "- Anh nhờ: %s\n  Bạn trả lời: %s%s\n" % (str(x["yeu_cau"])[:300], str(x.get("tra_loi") or "")[:300],
                                                             " (anh đã áp)" if x.get("da_ap") else " (anh chưa áp)" if x.get("da_ap") is False else "")
        prompt = (mau.replace("{{VIDEO_JSON}}", json.dumps(gon, ensure_ascii=False, indent=1))
                  .replace("{{TIEN_ICH}}", _nho_tien_ich())
                  .replace("{{ANH}}", ("Ảnh các cảnh (mở bằng Read khi cần nhìn): " + ", ".join(anh)) if anh else "(Không có ảnh cảnh.)")
                  .replace("{{LICH_SU}}", ("\n## Mấy lần nhờ trước (cùng video)\n" + ls) if ls else "")
                  .replace("{{YEU_CAU}}", yc))
        pp = os.path.join(W, "prompt.txt")
        with open(pp, "w", encoding="utf-8") as f:
            f.write(prompt)
        model = S.CFG.get("model_nho", "sonnet")
        kq, loi = None, ""
        for moi in (True, False):   # bản Claude Code cũ chưa có --tools ... thì chạy lại bằng cờ cũ
            args = cmd + ["-p", "--output-format", "stream-json", "--verbose"]
            if moi:
                args += ["--tools", "Read", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]
            else:
                args += ["--allowedTools", "Read", "--disallowedTools", "Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch"]
            if model:
                args += ["--model", model]
            env = dict(os.environ, PYTHONUTF8="1")
            kw = {"creationflags": NO_WIN | 0x00000200} if IS_WIN else {"start_new_session": True}
            with open(pp, "rb") as pin, open(os.path.join(W, "stderr.txt"), "wb") as er:
                p = subprocess.Popen(args, cwd=W, stdin=pin, stdout=subprocess.PIPE, stderr=er, env=env, **kw)
            with LOCK:
                NHO[ma]["pid"] = p.pid
                if NHO[ma].get("dung"):
                    _giet(p.pid)
            hen = threading.Timer(NHO_GIAY, lambda: (_nho_set(ma, het_gio=True), _giet(p.pid)))
            hen.start()
            ket = None
            with open(os.path.join(W, "stream.jsonl"), "wb") as luu:
                for raw in iter(p.stdout.readline, b""):
                    luu.write(raw)
                    try:
                        ev = json.loads(raw.decode("utf-8", "replace"))
                    except ValueError:
                        continue
                    if ev.get("type") == "assistant":
                        for c in ((ev.get("message") or {}).get("content") or []):
                            if c.get("type") == "tool_use" and c.get("name") == "Read":
                                _nho_set(ma, buoc="Claude đang xem ảnh %s" % os.path.basename(str((c.get("input") or {}).get("file_path") or "")))
                            elif c.get("type") == "text":
                                _nho_set(ma, buoc="Claude đang viết đề xuất")
                    elif ev.get("type") == "result":
                        ket = ev
            code = p.wait()
            hen.cancel()
            with LOCK:
                st = dict(NHO.get(ma) or {})
            if st.get("dung"):
                _nho_set(ma, dang=False, loi="Đã dừng")
                return
            if st.get("het_gio"):
                _nho_set(ma, dang=False, loi="Claude làm quá %d phút, đã dừng. Thử nhờ việc nhỏ hơn." % (NHO_GIAY // 60))
                return
            try:
                with open(os.path.join(W, "stderr.txt"), encoding="utf-8", errors="replace") as f:
                    err = f.read()[-2000:]
            except OSError:
                err = ""
            if ket is None and moi and re.search(r"unknown option|unrecognized|error: option", err, re.I):
                continue
            if ket is None:
                loi = S.explain_err(err) if err.strip() else "Claude dừng giữa chừng (mã %s)" % code
            elif ket.get("is_error"):
                loi = S.explain_err(str(ket.get("result") or ket.get("subtype") or err))
            else:
                kq = _lay_json(ket.get("result"))
                if not isinstance(kq, dict):
                    loi = "Claude trả lời không đúng mẫu, bấm Gửi lại"
            break
        if kq is not None:
            tl = str(kq.get("tra_loi") or "").strip()[:1200]
            td = [x for x in (kq.get("thay_doi") or []) if isinstance(x, dict) and isinstance(x.get("op"), str)
                  and (x["op"] != "script" or (isinstance(x.get("ma"), str) and 0 < len(x["ma"]) <= 20000))][:80]
            kh = [str(x).strip()[:300] for x in (kq.get("ke_hoach") or []) if isinstance(x, (str, int, float)) and str(x).strip()][:10] \
                if isinstance(kq.get("ke_hoach"), list) else []
            lt = None
            if isinstance(kq.get("luu_tien_ich"), dict):
                try:
                    meta, ma_ = TI.sach(dict(kq["luu_tien_ich"], loai="script", nguon="claude"), kq["luu_tien_ich"].get("ma") or "")
                    lt = dict(meta, ma=ma_)
                except ValueError:
                    lt = None
            kq = {"tra_loi": tl, "ke_hoach": kh, "thay_doi": td, "luu_tien_ich": lt, "giay": round(time.time() - NHO[ma]["bat_dau"]),
                  "chi_phi": (ket or {}).get("total_cost_usd")}
            _ghi(os.path.join(W, "ket-qua.json"), kq)
            _nho_set(ma, dang=False, kq=kq, buoc="Xong")
        else:
            _nho_set(ma, dang=False, loi=loi or "Lỗi không rõ")
        S.log("sua-tay nho %s %s: %s" % (ma, os.path.basename(v), "ok %d thay doi" % len(kq["thay_doi"]) if kq else loi))
    except Exception as ex:  # noqa
        S.log("sua-tay nho loi: %s" % traceback.format_exc()[-1500:])
        _nho_set(ma, dang=False, loi="Lỗi: %s" % ex)


# ---------------------------------------------------------------- HTTP (server.py gọi)
def get(h, u, q):
    """Trả True nếu đã xử lý."""
    if u.path.startswith("/api/sua-tay/hinh/"):  # tự chia cảnh / tự chỉnh màu / bộ lọc màu (hinh.py, 4/11)
        import hinh
        return hinh.get(h, u, q)
    if u.path.startswith("/api/sua-tay/chong-rung/"):  # chống rung: bản xem ổn định, đo độ rung, báo đang phát (chong_rung.py, 4/11)
        import chong_rung
        return chong_rung.get(h, u, q)
    if u.path.startswith("/api/sua-tay/giong-de/"):  # giọng AI đọc lại khối tách: trạng thái tạo giọng (giong_de.py, r32)
        import giong_de
        return giong_de.get(h, u, q)
    if u.path.startswith("/api/sua-tay/kieu-chu"):  # kiểu chữ có sẵn + font cho trang (kieu_chu.py, 4/11)
        import kieu_chu
        return kieu_chu.get(h, u, S)
    if u.path.startswith("/api/sua-tay/soat-pd"):  # Claude soát phụ đề tự động (soat_pd.py, 4/11)
        import soat_pd
        return soat_pd.get(h, u, q)
    if u.path.startswith("/api/sua-tay/am-thanh"):  # âm thanh hiệu ứng ngắn: danh sách + nghe thử (am_thanh.py, r20)
        import am_thanh
        return am_thanh.get(h, u, q)
    if u.path.startswith("/api/sua-tay/kho"):  # Kho effect trên Drive: trạng thái + chép 1 mục về máy (kho.py, r37)
        import kho
        return kho.get(h, u, q)
    if u.path == "/api/sua-tay/card":  # card đồ hoạ: đang dò / dùng card gì (card.py, 10/11)
        import card
        return card.get(h, u, q)
    if u.path == "/api/sua-tay/tha-file":  # thả clip từ máy vào Sửa tay: thư mục clip-tha của video (tha_file.py, r34)
        import tha_file
        return tha_file.get(h, u, q)
    if u.path.startswith("/api/sua-tay/tu-dung"):  # Dựng tự động: tiến độ, bộ kiểu, bảng tóm tắt (tu_dung.py, r38)
        import tu_dung
        return tu_dung.get(h, u, q)
    if u.path in ("/sua-tay", "/sua-tay/"):
        with open(os.path.join(S.UI, "sua-tay.html"), "rb") as f:
            h.send(200, f.read(), "text/html; charset=utf-8")
        return True
    if u.path == "/api/sua-tay/ds":
        h.send(200, ds_video())
        return True
    if u.path == "/api/sua-tay/moc":   # r29 (L4): mốc bản sửa dở trên đĩa, cửa sổ hỏi định kỳ để biết bị cửa sổ khác đè
        h.send(200, moc_nhap(thu_muc_video((q.get("v") or [""])[0])))
        return True
    if u.path == "/api/sua-tay/xuat":
        v = thu_muc_video((q.get("v") or [""])[0])
        h.send(200, {"xuat": trang_thai_xuat(v), "ban": phien_ban(v)})
        return True
    if u.path == "/api/sua-tay/nho":
        h.send(200, nho_tt((q.get("ma") or [""])[0]))
        return True
    if u.path == "/api/sua-tay/nghe":
        h.send(200, nghe_tt((q.get("ma") or [""])[0]))
        return True
    if u.path == "/api/sua-tay/mau-kieu":
        h.send(200, mau_kieu_tt((q.get("ma") or [""])[0]))
        return True
    if u.path == "/api/sua-tay/giong-ds":
        h.send(200, giong_ds_st())
        return True
    if u.path == "/api/sua-tay/giong-tao":
        h.send(200, giong_tao_tt((q.get("ma") or [""])[0]))
        return True
    if u.path == "/api/sua-tay/giong-mau":   # r39: mp3 nghe thử gói sẵn trong app (poly-team/giong-mau/), chỉ tên trend-* / vn-* .mp3
        f = (q.get("f") or [""])[0]
        if not S.giong_mau_url(f):
            h.send(404, {"err": "Không có mẫu nghe này"})
            return True
        h.send_file(os.path.join(S.GIONG_MAU, f), "audio/mpeg")
        return True
    if u.path == "/api/sua-tay/giong":  # giọng AI của video (file .wav nằm trong thư mục clip, hoặc giọng vừa tạo trong Sửa tay)
        v_ = thu_muc_video((q.get("v") or [""])[0])
        p_ = (q.get("p") or [""])[0]
        g = giong_hop(v_, {"local": p_}) if p_ else giong_dia(v_)
        if not g:
            h.send(404, {"err": "Video này không có giọng đọc AI"})
            return True
        ext = os.path.splitext(g["local"])[1].lower()
        h.send_file(g["local"], {".wav": "audio/wav", ".mp3": "audio/mpeg", ".m4a": "audio/mp4"}.get(ext, "application/octet-stream"))
        return True
    if u.path == "/api/sua-tay/nhac-ds":   # nhạc nền (4/11): thư mục nhạc của tiệm + nhạc miễn phí kèm app
        h.send(200, nhac_ds((q.get("moi") or [""])[0] == "1"))
        return True
    if u.path == "/api/sua-tay/nhac":   # phát 1 file nhạc (nghe thử / khung xem trước): chỉ file trong thư mục nhạc cho phép
        p_, v_ = (q.get("p") or [""])[0], (q.get("v") or [""])[0]
        v_ = thu_muc_video(v_) if v_ else None
        if not nhac_cho_phep(p_, v_):
            h.send(403, {"err": "Không phát được file nhạc này (chỉ nhạc trong thư mục nhạc của tiệm / nhạc miễn phí kèm app)"})
            return True
        h.send_file(p_, NHAC_MIME.get(os.path.splitext(p_)[1].lower(), "application/octet-stream"))
        return True
    return False


def post(h, u, data):
    p = u.path
    if not p.startswith("/api/sua-tay/"):
        return False
    a = p[len("/api/sua-tay/"):]
    if a.startswith("giong-de/"):  # giọng AI đọc lại khối tách: tạo giọng từng câu, nghe riêng các khối (giong_de.py, r32)
        import giong_de
        return giong_de.post(h, u, data)
    if a.startswith("hinh/"):  # tự chia cảnh / tự chỉnh màu (hinh.py, 4/11)
        import hinh
        return hinh.post(h, u, data)
    if a.startswith("chong-rung/"):  # chống rung (chong_rung.py, 4/11)
        import chong_rung
        return chong_rung.post(h, u, data)
    if a.startswith("soat-pd"):  # Claude soát phụ đề tự động (soat_pd.py, 4/11)
        import soat_pd
        return soat_pd.post(h, u, data)
    if a == "card":  # công tắc "Dùng card đồ hoạ" (Tự động / Tắt -> config.json "ma_hoa"), dò lại (card.py, 10/11)
        import card
        return card.post(h, u, data)
    if a.startswith("tha-file/"):  # thả clip từ máy: hỏi file có sẵn, huỷ (tha_file.py, r34; nhận file ở server.do_POST)
        import tha_file
        return tha_file.post(h, u, data)
    if a.startswith("tu-dung/"):  # Dựng tự động: chạy / huỷ (tu_dung.py, r38)
        import tu_dung
        return tu_dung.post(h, u, data)
    v = data.get("v")
    if a == "mo":
        r = mo(v, bool(data.get("bo_nhap")))
    elif a == "xem":
        r = xem(v, data.get("plan"))
    elif a == "nhap":
        r = nhap(v, data.get("plan"), data.get("kp_mtime"), data.get("phien"), data.get("moc"), bool(data.get("ep")))
    elif a == "luu":
        r = luu(v, data.get("plan"))
    elif a == "proxy":
        r = proxy_tt(data.get("ds") or [])
    elif a == "them-clip":
        r = them_clip(data.get("p"))
    elif a == "moi":
        r = tao_moi(data)
    elif a == "xuat":
        r = xuat(v, data.get("plan"), bool(data.get("nhap")), data.get("kp_mtime"), data.get("dinh_dang"), data.get("phien"))
    elif a == "giong-tao":
        r = giong_tao(v, data.get("loi"), data.get("giong"), data.get("toc_do"), data.get("phong"), data.get("kieu_trend"))
    elif a == "nhac-thu-muc":   # anh chọn thư mục nhạc của tiệm bằng bảng chọn thư mục (4/11)
        r = nhac_chon_thu_muc(data.get("p"))
    elif a == "xuat-dung":
        r = dung_xuat(v)
    elif a == "nho":
        r = nho(v, data.get("plan"), data.get("yeu_cau"), data.get("gon"), data.get("lich_su"))
    elif a == "nho-dung":
        r = nho_dung(data.get("ma"))
    elif a == "nghe":
        r = nghe(v, data.get("plan"))
    elif a == "mau-kieu":
        r = mau_kieu(v, data.get("plan"))
    elif a == "mo-thu-muc":
        vv = thu_muc_video(v)
        tm = data.get("p") or vv
        if os.path.isfile(tm):
            tm = os.path.dirname(tm)
        if not (os.path.isdir(tm) and S.trong(tm, vv)):
            raise ValueError("Không mở được thư mục này")
        if IS_WIN:
            os.startfile(tm)  # noqa
        r = {"ok": True}
    else:
        return False
    h.send(200, r if r is not None else {"ok": True})
    return True
