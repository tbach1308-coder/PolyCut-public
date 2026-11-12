# -*- coding: utf-8 -*-
"""POLY Cut — hàng việc nền nhường máy cho khung xem (4/11/2026, anh: "khung hình vẫn rung … giật / khựng từng nhịp vài giây").

Việc nền = ffmpeg làm bản xem nhẹ 720p (sua_tay._lam), bản xem đã chống rung + đo độ rung (chong_rung.py). Chạy ở mức ưu tiên THẤP
(Windows BELOW_NORMAL, Linux nice 10) như trước, và thêm:
  - Trang báo đang PHÁT (POST /api/sua-tay/chong-rung/phat, nhịp 1,5s): trong lúc khung xem đang phát VIDEO (bản xem nhẹ đã có) chỉ
    cho 1 việc quan trọng nhất chạy, các việc khác TẠM DỪNG HẲN (Windows NtSuspendProcess, Linux SIGSTOP) tới khi dừng phát. Đang phát
    mà khung xem chỉ hiện ẢNH TẠM (clip chưa có bản xem nhẹ, máy không giải mã video): các việc gấp chạy hết để có bản xem nhẹ sớm (đo
    4/11: chỉ 1 việc thì clip trong cảnh có bản xem nhẹ chậm hơn ~30%). Việc "để sau" (clip chỉ có trong thư viện của video, uu >= 3)
    không chạy lúc phát. Mất nhịp 6s (đóng trang, mạng) thì tự coi như đã dừng phát -> chạy tiếp.
  - Mức ưu tiên việc (uu, nhỏ = gấp): 0 bản xem nhẹ clip trong cảnh / clip anh bấm xem · 1 bản xem chống rung · 2 đo độ rung ·
    3 bản xem nhẹ clip chỉ có trong thư viện (làm sau cùng, khi máy rảnh).
Chỉ thư viện chuẩn. Tắt app: mọi việc đang tạm dừng được cho chạy lại (atexit) rồi mới thoát. App bị tắt ngang (/api/tat và
KHOI-DONG-LAI dùng os._exit — atexit không chạy; tắt máy chủ đột ngột): các pid đang tạm dừng đã ghi ở _cache/hang-nen-tam.txt, lần
mở app sau cho chạy lại (chỉ tiến trình ffmpeg / python) — không để ffmpeg nằm treo mãi.
"""
import atexit
import os
import shutil
import signal
import subprocess
import threading
import time

IS_WIN = os.name == "nt"
NO_WIN = 0x08000000
BELOW_NORMAL = 0x00004000
NHIP = 6.0          # giây: không nghe trang báo đang phát quá chừng này = đã dừng phát (máy bận: báo có thể trễ vài giây)
RANH_SAU = 5.0      # giây: dừng phát chừng này mới làm việc "để sau"

LOCK = threading.RLock()
VIEC = {}           # pid -> {"p": Popen, "uu": int, "luc": giờ bắt đầu, "dung": đang tạm dừng?}
_PHAT = {"luc": 0.0, "dang": False, "het": 0.0, "clip": "", "video": True}   # lần cuối trang báo đang phát / lúc dừng phát / clip
#                                                                               đang hiện / khung xem đang phát video (False = ảnh tạm)
DEM = {"tam_dung": 0, "chay_lai": 0}            # đếm (cho bài thử)
_THEO = None


def _tam(pid, dung):
    """Tạm dừng / cho chạy lại 1 tiến trình (cả cây không cần: ffmpeg không đẻ tiến trình con)."""
    try:
        if IS_WIN:
            import ctypes
            k32, nt = ctypes.windll.kernel32, ctypes.windll.ntdll
            h = k32.OpenProcess(0x0800, False, int(pid))   # PROCESS_SUSPEND_RESUME
            if not h:
                return False
            try:
                return (nt.NtSuspendProcess if dung else nt.NtResumeProcess)(h) == 0
            finally:
                k32.CloseHandle(h)
        os.kill(int(pid), signal.SIGSTOP if dung else signal.SIGCONT)
        return True
    except Exception:  # noqa  tiến trình vừa xong / không có quyền: bỏ qua
        return False


_TEP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_cache", "hang-nen-tam.txt")


def _luu():
    """Ghi pid các việc đang tạm dừng (gọi trong LOCK). Hết việc tạm dừng thì xoá file."""
    try:
        ds = [str(pid) for pid, x in VIEC.items() if x["dung"]]
        if ds:
            os.makedirs(os.path.dirname(_TEP), exist_ok=True)
            with open(_TEP, "w") as f:
                f.write("\n".join(ds))
        elif os.path.isfile(_TEP):
            os.remove(_TEP)
    except Exception:  # noqa
        pass


def _la_viec_nen(pid):   # ffmpeg (bản xem) hoặc python (chong_rung_may đo độ rung)
    try:
        if IS_WIN:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, int(pid))   # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            try:
                buf, n = ctypes.create_unicode_buffer(1024), wintypes.DWORD(1024)
                if not k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                    return False
                return os.path.basename(buf.value).lower().startswith(("ffmpeg", "python"))
            finally:
                k32.CloseHandle(h)
        with open("/proc/%d/cmdline" % int(pid), "rb") as f:   # "nice -n 10 ffmpeg …": nice exec thành ffmpeg, cùng pid
            ten = os.path.basename(f.read().split(b"\0")[0])
            return b"ffmpeg" in ten or b"python" in ten
    except Exception:  # noqa
        return False


def _don_cu():
    """Lần trước app bị tắt ngang lúc đang tạm dừng việc: cho các ffmpeg đó chạy lại (tự làm xong / tự thoát như trước khi có hàng này)."""
    try:
        with open(_TEP) as f:
            ds = f.read().split()
    except OSError:
        return
    for s in ds:
        if s.isdigit() and _la_viec_nen(s):
            _tam(s, False)
    try:
        os.remove(_TEP)
    except OSError:
        pass


def dang_phat():
    with LOCK:
        return _PHAT["dang"] and time.time() - _PHAT["luc"] < NHIP


_SO = {}   # trang (phiên) -> số thứ tự báo gần nhất: máy bận, báo đến trễ / lộn thứ tự thì bỏ báo cũ


def phat(dang, clip="", phien="", so=0, video=True):
    """Trang báo: dang=True mỗi 1,5s lúc phát (kèm clip đang hiện; video=False: khung xem đang hiện ảnh tạm, chưa có bản xem nhẹ),
    False khi dừng. phien + so: bỏ báo đến trễ (máy bận, yêu cầu lộn thứ tự: báo "đang phát" cũ tới sau báo "dừng")."""
    with LOCK:
        if phien and so:
            if so <= _SO.get(phien, 0):
                return {"dang": dang_phat(), "viec": so_viec(), "bo": True}
            _SO[phien] = so
            if len(_SO) > 50:
                _SO.pop(next(iter(_SO)))
        if dang:
            _PHAT["luc"] = time.time()
            _PHAT["clip"] = _chuan(clip)
            _PHAT["video"] = bool(video)
        elif _PHAT["dang"]:
            _PHAT["het"] = time.time()
        _PHAT["dang"] = bool(dang)
    _xep()
    _bat_theo()
    return {"dang": dang_phat(), "viec": so_viec()}


def ranh(giay=RANH_SAU):
    """Không phát (đã dừng ≥ giay) — để làm việc "để sau"."""
    with LOCK:
        if dang_phat():
            return False
        het = _PHAT["het"] if not _PHAT["dang"] else _PHAT["luc"] + NHIP
        return time.time() - het >= giay


def so_viec(uu_toi_da=99):
    with LOCK:
        return sum(1 for x in VIEC.values() if x["uu"] <= uu_toi_da)


def _chuan(p):
    return os.path.normcase(os.path.normpath(str(p or ""))) if p else ""


def _xep():
    """Đang phát video: chỉ việc gấp nhất chạy — việc của CLIP ĐANG HIỆN trên khung xem trước, rồi uu nhỏ, bắt đầu sớm; trừ việc
    "để sau". Đang phát mà khung xem chỉ hiện ảnh tạm: việc gấp chạy hết (trừ "để sau"). Không phát: chạy hết."""
    with LOCK:
        cl = _PHAT.get("clip") or ""
        ds = sorted(VIEC.items(), key=lambda kv: (0 if cl and kv[1].get("ten") == cl else 1, kv[1]["uu"], kv[1]["luc"]))
        phat_ = dang_phat()
        cho_chay = set()
        if phat_:
            gap = [pid for pid, x in ds if x["uu"] < 3]
            cho_chay = set(gap[:1] if _PHAT.get("video", True) else gap)
        else:
            cho_chay = {pid for pid, _ in ds}
        doi = False
        for pid, x in ds:
            muon_dung = pid not in cho_chay
            if muon_dung != x["dung"] and x["p"].poll() is None:
                if _tam(pid, muon_dung):
                    x["dung"] = muon_dung; doi = True
                    DEM["tam_dung" if muon_dung else "chay_lai"] += 1
        if doi:
            _luu()


def _bat_theo():
    global _THEO
    with LOCK:
        if _THEO and _THEO.is_alive():
            return

        def lap():
            while True:
                time.sleep(0.5)
                try:
                    _xep()
                except Exception:  # noqa
                    pass
        _THEO = threading.Thread(target=lap, daemon=True)
        _THEO.start()


@atexit.register
def _het():
    with LOCK:
        for pid, x in VIEC.items():
            if x["dung"]:
                _tam(pid, False); x["dung"] = False
        _luu()


class KetQua:
    def __init__(self, returncode, stdout, stderr):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def chay(cmd, uu=0, timeout=3600, ten="", **kw):
    """Chạy 1 lệnh nền ở mức ưu tiên thấp, có thể bị tạm dừng lúc anh đang phát. Việc uu >= 3 chờ máy rảnh mới bắt đầu.
    ten = clip của việc (lúc phát, việc của clip đang hiện được chạy trước).
    -> KetQua(returncode, stdout bytes, stderr bytes)."""
    _bat_theo()
    if uu >= 3:
        while not ranh() or so_viec(2) > 0:
            time.sleep(0.5)
    nice = [] if IS_WIN or not shutil.which("nice") else ["nice", "-n", "10"]
    if IS_WIN:
        kw.setdefault("creationflags", NO_WIN | BELOW_NORMAL)
    p = subprocess.Popen(nice + list(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    with LOCK:
        VIEC[p.pid] = {"p": p, "uu": int(uu), "luc": time.time(), "dung": False, "ten": _chuan(ten)}
    _xep()
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _tam(p.pid, False)
        p.kill()
        out, err = p.communicate()
    finally:
        with LOCK:
            if (VIEC.pop(p.pid, None) or {}).get("dung"):
                _luu()
    return KetQua(p.returncode, out, err)


_don_cu()


def trang_thai():
    with LOCK:
        return {"dang_phat": dang_phat(), "clip": _PHAT.get("clip"), "video": _PHAT.get("video", True), "viec": [{"pid": pid, "uu": x["uu"], "dung": x["dung"], "ten": x.get("ten")} for pid, x in VIEC.items()],
                "dem": dict(DEM)}
