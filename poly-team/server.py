# -*- coding: utf-8 -*-
"""
POLY TEAM (Poly Dung Video 2.0) - app dat cach dung video TikTok, bam Chay, Claude Code (plugin poly-video) tu dung tren may nay.

Chay: pythonw server.py  (hoac bam icon "POLY Cut" ngoai Desktop)
Mo:   http://127.0.0.1:8790  (8779 la Poly Dung Video ban 1, 8777 la Poly Dung Bai, 8765 la tool dang bai: khong dung chung)
Ban 2.0 (30/10/2026) ten app POLY Team, nam rieng o E:/Tool/poly-team, dung chung bo dung engine/ cua ban 1 (E:/Tool/poly-dung-video/engine).

Chi dung thu vien co san cua Python 3.12. Phan dung video (ffmpeg, may nghe tieng Viet...) nam o engine/ cua ban 1 (CAI-DAT.bat ben ban 1).
Moi video = 1 thu muc jobs/<id>/ : job.json, don.json, prompt-N.txt, stream-N.jsonl (log Claude), stderr-N.txt.
Trang thai luon doc lai tu file log, nen tat app giua chung roi mo lai van xem tiep duoc.
Lam tu server.py cua Poly Dung Bai (28-29/10/2026): phan chay Claude + doc log giu nguyen cach lam.
"""
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

APP = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.join(APP, "jobs")
UI = os.path.join(APP, "ui")
PROMPTS = os.path.join(APP, "prompts")
CACHE = os.path.join(APP, "_cache")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/quicktime", ".mov")
IS_WIN = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
VIDEO_EXT = (".mov", ".mp4", ".m4v", ".mts", ".mkv", ".avi")
APP_TEN = "POLY Cut"   # 3/11 chủ tiệm đổi tên app (trước: POLY Team); thư mục / mã app giữ poly-team
APP_MA = "poly-team"
import sua_tay as ST  # noqa: E402  trang Sửa tay (/sua-tay): sửa video bằng tay, xuất bằng ffmpeg
import tien_ich as TI  # noqa: E402  tiện ích gắn thêm (tien-ich/<id>/: script chạy trong Sửa tay)

def _engine_mac_dinh():
    """Bản 2.0 dùng chung bộ dựng của bản 1 (Python, ffmpeg, máy nghe, giọng AI ~1 GB) khi thư mục mình chưa có engine riêng."""
    rieng = os.path.join(APP, "engine")
    chung = os.path.join(os.path.dirname(APP), "poly-dung-video", "engine")
    if not os.path.isfile(os.path.join(rieng, "san-sang.json")) and os.path.isdir(chung):
        return chung
    return rieng


DEFAULT_CFG = {
    "port": 8790,
    # nơi ra video (mỗi video 1 thư mục <slug>), nơi hay để clip, thư mục plugin Premiere Poly Bridge
    "thu_muc_ra": "E:\\Tool\\poly-edit",
    "thu_muc_clip": "E:\\Video",
    "premiere_dir": "E:\\Tool\\poly-premiere",
    "them_thu_muc": ["E:\\Video", "E:\\Tool\\poly-edit", "E:\\Tool\\poly-premiere"],
    "che_do_quyen": "acceptEdits",
    # lệnh được chạy không hỏi (chạy ngầm không ai bấm cho phép được); không có lệnh xoá
    "cho_phep_them": [
        "Bash(python *)", "Bash(python3 *)", "Bash(py *)", "Bash(ffmpeg *)", "Bash(ffprobe *)",
        "Bash(ls *)", "Bash(mkdir *)", "Bash(cp *)", "Bash(mv *)", "Bash(cat *)", "Bash(head *)", "Bash(tail *)",
        "Bash(wc *)", "Bash(find *)", "Bash(grep *)", "Bash(cd *)", "Bash(echo *)", "Bash(sleep *)",
        "Bash(stat *)", "Bash(du *)", "Bash(file *)", "Bash(sort *)", "Bash(diff *)",
        "PowerShell(python *)", "PowerShell(py *)", "PowerShell(Get-ChildItem *)", "PowerShell(Copy-Item *)",
        "PowerShell(Move-Item *)", "PowerShell(New-Item *)", "PowerShell(Test-Path *)",
        "PowerShell(Get-Content *)", "PowerShell(Start-Sleep *)",
        # Read / Write / Edit để chế độ acceptEdits lo (chỉ trong thư mục được --add-dir), không mở ra cả máy
        "TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "TodoWrite", "Agent", "Skill",
    ],
    "model": "",
    "lenh_claude": [],
    # tài khoản Claude nào đăng nhập cũng làm được: mỗi lượt app tự nạp plugin poly-video + luật chung
    "plugin_dir": os.path.join(APP, "plugin", "poly-video"),
    "engine_dir": _engine_mac_dinh(),
    "mo_hinh": "sherpa-onnx-zipformer-vi-int8-2025-04-20",
    # Premiere chỉ dựng 1 video 1 lúc: video bấm Chạy khi đang có video khác dựng thì xếp hàng
    "dang_chay_toi_da": 1,
    # Premiere văng giữa lúc gui_lenh.py đang gửi lệnh: tự mở lại đúng project (như MCP Poly Bridge cũ). false = chỉ dừng + báo
    "premiere_tu_mo_lai": True,
    # tới bước dựng mà Premiere chưa mở: gui_lenh.py tự mở Premiere (kèm project gần nhất) rồi chờ bảng Poly Bridge. false = dừng báo anh
    "premiere_tu_mo": True,
    "telegram_token": "",
    "telegram_chat": "",
}

LOCK = threading.RLock()
STATE = {}  # job_id -> parsed state cache
LISTED = set()  # thư mục clip anh vừa mở trong app (cho xem ảnh khung clip trong đó)


# ---------------------------------------------------------------- tien ich
def log(s):
    try:
        with open(os.path.join(APP, "app-log.txt"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + str(s) + "\n")
    except Exception:
        pass


def load_cfg():
    cfg = json.loads(json.dumps(DEFAULT_CFG))
    p = os.path.join(APP, "config.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                user = json.load(f)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception as e:  # config hong thi dung mac dinh
            log("config.json loi: %s" % e)
    return cfg


CFG = load_cfg()
TI.gan_cfg(CFG)


def now():
    return time.time()


def read_json(p, default=None):
    for k in range(5):
        try:
            with open(p, "r", encoding="utf-8-sig") as f:  # -sig: file sửa bằng Notepad có BOM vẫn đọc được
                return json.load(f)
        except PermissionError:  # Windows: file đang bị ghi đè (os.replace) -> thử lại
            time.sleep(0.05)
        except Exception:
            return default
    return default


def write_json(p, data):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    for k in range(20):  # Windows: luồng khác đang mở đọc file -> os.replace lỗi quyền, chờ chút thử lại
        try:
            os.replace(tmp, p)
            return
        except PermissionError:
            time.sleep(0.05)
    os.replace(tmp, p)


def read_text(p):
    try:
        with open(p, "rb") as f:
            return f.read().decode("utf-8", "replace")
    except Exception:
        return ""


def job_dir(jid):
    if not re.fullmatch(r"[0-9a-zA-Z_-]{6,64}", jid or ""):
        raise ValueError("id sai")
    return os.path.join(JOBS, jid)


def load_job(jid):
    return read_json(os.path.join(job_dir(jid), "job.json"))


def save_job(job):
    write_json(os.path.join(job_dir(job["id"]), "job.json"), job)


def short(s, n=110):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def base(p):
    return os.path.basename(str(p).replace("\\", "/").rstrip("/")) or str(p)


def norm(p):
    return os.path.normcase(os.path.realpath(p))


def trong(p, root):
    """p nằm trong (hoặc là) thư mục root."""
    if not root:
        return False
    a, b = norm(p), norm(root)
    return a == b or a.startswith(b.rstrip("\\/") + os.sep)


def bo_dau(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.replace("đ", "d").replace("Đ", "D")


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", bo_dau(s).lower()).strip("-")
    return s[:48].strip("-")


def proc_start(pid):
    """Gio (epoch) tien trinh pid duoc tao, None neu khong doc duoc."""
    try:
        if IS_WIN:
            import ctypes

            k = ctypes.windll.kernel32
            h = k.OpenProcess(0x1000, False, int(pid))
            if not h:
                return None

            class FT(ctypes.Structure):
                _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]

            c, e, kk, u = FT(), FT(), FT(), FT()
            ok = k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kk), ctypes.byref(u))
            k.CloseHandle(h)
            if not ok:
                return None
            return ((c.hi << 32) | c.lo) / 1e7 - 11644473600
        with open("/proc/%d/stat" % int(pid)) as f:
            ticks = int(f.read().rsplit(")", 1)[1].split()[19])
        with open("/proc/stat") as f:
            btime = next(int(l.split()[1]) for l in f if l.startswith("btime"))
        return btime + ticks / os.sysconf("SC_CLK_TCK")
    except Exception:
        return None


def pid_alive(pid, started=None):
    """started = gio app bat luot chay. PID con song nhung tao luc khac (lech > 60 giay) = tien trinh khac
    (Windows cap lai PID sau khi tat may) -> coi nhu luot da ket thuc."""
    if not pid:
        return False
    if started:
        t = proc_start(pid)
        if t and abs(t - started) > 60:
            return False
    if IS_WIN:
        import ctypes

        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        code = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(code))
        k.CloseHandle(h)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    try:  # zombie (linux, khi chay thu) coi nhu da xong
        with open("/proc/%d/stat" % int(pid)) as f:
            if f.read().split(")")[-1].split()[0] == "Z":
                return False
    except Exception:
        pass
    return True


def kill_tree(pid):
    if not pid:
        return
    if IS_WIN:
        subprocess.call(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
    else:
        try:
            os.killpg(int(pid), 15)
        except Exception:
            try:
                os.kill(int(pid), 15)
            except Exception:
                pass


# ---------------------------------------------------------------- tim Claude Code (giong Poly Dung Bai)
_CLAUDE = {"cmd": None, "version": None, "err": None, "t": 0}


def resolve_claude():
    """Tra ve lenh goi Claude Code (list). Khong di qua cmd.exe neu tranh duoc."""
    if CFG.get("lenh_claude"):
        return list(CFG["lenh_claude"])
    home = os.path.expanduser("~")
    cands = []
    if IS_WIN:
        cands += [
            os.path.join(home, ".local", "bin", "claude.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "claude", "claude.exe"),
        ]
    for c in cands:
        if c and os.path.isfile(c):
            return [c]
    exe = shutil.which("claude.exe") if IS_WIN else None
    if exe:
        return [exe]
    roots = []
    if IS_WIN and os.environ.get("APPDATA"):
        roots.append(os.path.join(os.environ["APPDATA"], "npm", "node_modules"))
    try:
        npm_root = subprocess.run(["npm.cmd" if IS_WIN else "npm", "root", "-g"], capture_output=True, text=True,
                                  timeout=20, creationflags=CREATE_NO_WINDOW if IS_WIN else 0).stdout.strip()
        if npm_root:
            roots.append(npm_root)
    except Exception:
        pass
    node = shutil.which("node")
    for r in roots:
        pkg = os.path.join(r, "@anthropic-ai", "claude-code")
        pj = read_json(os.path.join(pkg, "package.json"), {}) or {}
        b = pj.get("bin")
        if isinstance(b, dict):
            b = b.get("claude") or next(iter(b.values()), None)
        cand = [b] if b else []
        cand += ["cli.js", "bin/claude.exe", "bin/claude"]
        for rel in cand:
            fp = os.path.normpath(os.path.join(pkg, rel))
            if not os.path.isfile(fp):
                continue
            if fp.lower().endswith((".js", ".mjs", ".cjs")):
                if node:
                    return [node, fp]
            elif fp.lower().endswith(".exe") or not IS_WIN:
                return [fp]
    c = shutil.which("claude")
    if c:
        if IS_WIN and c.lower().endswith((".cmd", ".bat")):
            return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", c]
        return [c]
    return None


def claude_info(force=False):
    if not force and _CLAUDE["t"] and now() - _CLAUDE["t"] < (300 if _CLAUDE.get("login") else 20):
        return _CLAUDE
    cmd = resolve_claude()
    _CLAUDE.update(cmd=cmd, version=None, err=None, t=now())
    if not cmd:
        _CLAUDE["err"] = "Không tìm thấy Claude Code trên máy (lệnh claude)."
        return _CLAUDE
    try:
        out = subprocess.run(cmd + ["--version"], capture_output=True, timeout=60,
                             creationflags=CREATE_NO_WINDOW if IS_WIN else 0)
        v = (out.stdout or b"").decode("utf-8", "replace").strip() or (out.stderr or b"").decode("utf-8", "replace").strip()
        _CLAUDE["version"] = v.splitlines()[0] if v else "?"
    except Exception as e:
        _CLAUDE["err"] = "Gọi Claude Code lỗi: %s" % e
    _CLAUDE["login"] = None
    _CLAUDE["tk"] = {}
    try:
        out = subprocess.run(cmd + ["auth", "status"], capture_output=True, timeout=60,
                             creationflags=CREATE_NO_WINDOW if IS_WIN else 0)
        txt = (out.stdout or b"").decode("utf-8", "replace")
        m = re.search(r"\{.*\}", txt, re.S)
        if m:
            st = json.loads(m.group(0))
            _CLAUDE["login"] = bool(st.get("loggedIn"))
            _CLAUDE["tk"] = {k: st.get(k2) for k, k2 in (("email", "email"), ("goi", "subscriptionType"), ("to_chuc", "orgName"), ("kieu", "authMethod"))
                             if st.get(k2)} if _CLAUDE["login"] else {}
        else:
            _CLAUDE["login"] = out.returncode == 0
    except Exception:
        pass
    return _CLAUDE


# ---------------------------------------------------------------- engine (bo dung tren may nay)
def engine():
    e = CFG.get("engine_dir") or os.path.join(APP, "engine")
    sc = "Scripts" if IS_WIN else "bin"
    return {
        "dir": e,
        "py": os.path.join(e, ".venv", sc, "python.exe" if IS_WIN else "python"),
        "scripts": os.path.join(e, ".venv", sc),
        "bin": os.path.join(e, "bin"),
        "mo_hinh": os.path.join(e, "mo-hinh", CFG.get("mo_hinh") or ""),
        "font": os.path.join(e, "fonts"),
        "san_sang": os.path.join(e, "san-sang.json"),
    }


def tim_ffmpeg(ten="ffmpeg"):
    e = engine()
    for p in (os.path.join(e["bin"], ten + (".exe" if IS_WIN else "")),):
        if os.path.isfile(p):
            return p
    return shutil.which(ten)


def premiere_nhip():
    """Nhịp tim plugin Poly Bridge: {song, tuoi, project, premiere, dang_nghe, dang_chay}."""
    p = os.path.join(CFG.get("premiere_dir") or "", "ket-qua", "_trang-thai.json")
    d = read_json(p)
    if not d or not d.get("luc"):
        return {"song": False, "co": False}
    try:
        from datetime import datetime
        t = datetime.fromisoformat(str(d["luc"]).replace("Z", "+00:00")).timestamp()
    except Exception:
        try:
            t = os.path.getmtime(p)
        except OSError:
            return {"song": False, "co": False}
    tuoi = now() - t
    return {"song": tuoi < 20, "co": True, "tuoi": round(tuoi), "project": d.get("project"), "premiere": d.get("premiere"),
            "plugin": d.get("plugin"), "dang_nghe": d.get("dang_nghe"), "dang_chay": bool(d.get("dang_chay"))}


def plugin_dir():
    d = CFG.get("plugin_dir") or ""
    return d if d and os.path.isfile(os.path.join(d, ".claude-plugin", "plugin.json")) else ""


def san_sang():
    """Kiểm máy có đủ đồ để dựng (hiện ở ô Kiểm máy). can=True: thiếu thì chặn nút Chạy."""
    ds = []
    pd = plugin_dir()
    pj = read_json(os.path.join(pd, ".claude-plugin", "plugin.json"), {}) if pd else {}
    ds.append({"ma": "plugin", "ten": "Bộ quy tắc dựng video (plugin poly-video)", "ok": bool(pd), "can": True,
               "ghi": ("bản %s" % pj.get("version")) if pd and pj.get("version") else ("" if pd else "thiếu thư mục plugin\\poly-video")})
    e = engine()
    ss = read_json(e["san_sang"], {}) or {}
    ok = bool(ss.get("ok")) and os.path.isfile(e["py"])
    ghi = "đã cài" if ok else ("chưa cài: chạy CAI-DAT.bat trong E:\\Tool\\poly-dung-video (bộ dựng dùng chung với bản 1)" if not ss else "thiếu " + ", ".join(ss.get("thieu") or ["?"]))
    ds.append({"ma": "engine", "ten": "Bộ dựng (ffmpeg, máy nghe tiếng Việt, font)", "ok": ok, "can": True, "ghi": ghi})
    lc = os.path.isfile(os.path.join(PROMPTS, "luat-chung.md"))
    ds.append({"ma": "luat", "ten": "Luật chung của shop", "ok": lc, "can": False, "ghi": "" if lc else "thiếu prompts\\luat-chung.md"})
    nt = premiere_nhip()
    if nt.get("song"):
        g = "đang mở" + (" · " + nt["project"] if nt.get("project") else "") + ("" if nt.get("dang_nghe") is not False else " · bảng Poly Bridge đang tạm dừng")
    else:
        g = ("chưa mở (tới bước dựng app tự mở Premiere)" if CFG.get("premiere_tu_mo") is not False
             else "chưa mở (mở Premiere + bảng Poly Bridge trước bước dựng)")
    ds.append({"ma": "premiere", "ten": "Premiere + bảng Poly Bridge", "ok": bool(nt.get("song")) and nt.get("dang_nghe") is not False,
               "can": False, "ghi": g})
    ra = CFG.get("thu_muc_ra") or ""
    ds.append({"ma": "ra", "ten": "Thư mục lưu video", "ok": os.path.isdir(ra), "can": False, "ghi": ra if os.path.isdir(ra) else "chưa có " + ra + " (Claude tự tạo)"})
    return ds


def doi_tai_khoan():
    """Mở cửa sổ đăng xuất tài khoản Claude cũ rồi đăng nhập tài khoản khác."""
    with LOCK:
        for jid in (os.listdir(JOBS) if os.path.isdir(JOBS) else []):
            if (read_json(os.path.join(JOBS, jid, "job.json")) or {}).get("status") == "dang-chay":
                raise ValueError("Đang có video dựng, chờ xong rồi đổi tài khoản.")
    cmd = resolve_claude()
    if not cmd:
        raise ValueError("Không tìm thấy Claude Code")
    c = cmd[-1] if len(cmd) > 1 and cmd[0].lower().endswith("cmd.exe") else None
    lenh = ('call "%s"' % c) if c else " ".join('"%s"' % x for x in cmd)
    bat = os.path.join(APP, "doi-tai-khoan.bat")
    with open(bat, "w", encoding="utf-8", newline="") as f:
        f.write("@echo off\r\nchcp 65001 >nul\r\n"
                "echo Dang xuat tai khoan Claude cu...\r\n%s auth logout\r\n"
                "echo.\r\necho Dang nhap tai khoan moi: trinh duyet tu mo, chon tai khoan Claude can dung.\r\n%s auth login\r\n"
                "echo.\r\necho Xong. Dong cua so nay, quay lai app POLY Cut.\r\npause\r\n" % (lenh, lenh))
    if IS_WIN:
        comspec = os.environ.get("COMSPEC", "cmd.exe")
        subprocess.Popen([comspec, "/c", "start", "Doi tai khoan Claude", comspec, "/c", bat], creationflags=CREATE_NO_WINDOW)
    _CLAUDE["t"] = 0
    return {"ok": True}


# ---------------------------------------------------------------- clip: liệt kê, độ dài, ảnh khung
_GIAY = {}
_POOL = ThreadPoolExecutor(max_workers=4)


def clip_giay(fp):
    try:
        st = os.stat(fp)
    except OSError:
        return None
    k = (norm(fp), st.st_size, int(st.st_mtime))
    if k in _GIAY:
        return _GIAY[k]
    fpb = tim_ffmpeg("ffprobe")
    if not fpb:
        return None
    try:
        out = subprocess.run([fpb, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", fp],
                             capture_output=True, timeout=20, creationflags=CREATE_NO_WINDOW if IS_WIN else 0)
        g = float((out.stdout or b"0").decode("ascii", "ignore").strip() or 0)
        _GIAY[k] = round(g, 1) if g > 0 else None
    except Exception:
        _GIAY[k] = None
    return _GIAY[k]


def list_clips(folder):
    folder = (folder or "").strip().strip('"')
    if not folder or not os.path.isdir(folder):
        raise ValueError("Không thấy thư mục này trên máy")
    out = []
    for fn in sorted(os.listdir(folder), key=lambda x: x.lower()):
        fp = os.path.join(folder, fn)
        if fn.startswith((".", "_")) or os.path.splitext(fn)[1].lower() not in VIDEO_EXT or not os.path.isfile(fp):
            continue
        st = os.stat(fp)
        out.append({"ten": fn, "path": fp, "mb": round(st.st_size / 1048576, 1), "mt": st.st_mtime})
    with LOCK:
        LISTED.add(norm(folder))
    gi = list(_POOL.map(lambda c: clip_giay(c["path"]), out[:120]))
    for c, g in zip(out, gi):
        c["giay"] = g
    sub = []
    try:
        for fn in sorted(os.listdir(folder), key=lambda x: x.lower()):
            if os.path.isdir(os.path.join(folder, fn)) and not fn.startswith((".", "_", "$")):
                sub.append(fn)
    except OSError:
        pass
    return {"thu_muc": folder, "clip": out, "thu_muc_con": sub[:60], "ffprobe": bool(tim_ffmpeg("ffprobe"))}


_THUMB_SEM = threading.Semaphore(2)  # tối đa 2 ffmpeg cắt ảnh khung cùng lúc (kéo mép cảnh / mở trang chọn clip không làm nghẽn máy)


_HDR_NHO = {}


def clip_hdr(p, st):
    """'arib-std-b67' / 'smpte2084' nếu clip HDR (nhớ theo file + cỡ + giờ sửa), không thì None."""
    k = (norm(p), st.st_size, int(st.st_mtime))
    if k not in _HDR_NHO:
        try:
            _HDR_NHO[k] = ST._hdr(p)
        except Exception:
            _HDR_NHO[k] = None
        if len(_HDR_NHO) > 3000:
            _HDR_NHO.clear()
    return _HDR_NHO[k]


def thumb(p, t=1.0, cao=360):
    if os.path.splitext(p)[1].lower() not in VIDEO_EXT or not os.path.isfile(p):
        raise ValueError("Không có clip này")
    st = os.stat(p)
    t = max(0.0, min(float(t or 0), 36000))
    cao = 720 if str(cao) == "720" else 360   # 720: ảnh tạm trong khung xem (4/11: "video bị mờ"), 360: ô nhỏ / timeline
    hdr = clip_hdr(p, st)   # 4/11: clip HDR iPhone cắt ảnh từ file gốc thì chuyển màu SDR như bản xem nhẹ (trước: ảnh bạc màu, đổi ảnh -> video nhảy màu)
    key = hashlib.md5((("%s|%s|%s|%.2f" % (norm(p), st.st_size, int(st.st_mtime), t)) + ("|720" if cao == 720 else "")
                       + ("|sdr" if hdr else "")).encode("utf-8")).hexdigest()
    d = os.path.join(CACHE, "khung")
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, key + ".jpg")
    if os.path.isfile(out) and os.path.getsize(out) > 0:
        return out
    ff = tim_ffmpeg("ffmpeg")
    if not ff:
        raise ValueError("Chưa cài bộ dựng (ffmpeg)")
    # clip đã có bản xem nhẹ (540×960, Sửa tay) thì cắt ảnh từ bản đó: nhanh gấp ~5 lần clip gốc 4K / HEVC, màu HDR đã chuyển như xem trước
    nguon = [p]
    try:
        px = ST._proxy_file(p)
        if px and os.path.isfile(px) and os.path.getsize(px) > 1000:
            nguon.insert(0, px)
        elif cao == 360 and ST._proxy_cu(p):
            nguon.insert(0, ST._proxy_cu(p))
    except Exception:
        pass
    tmp = "%s.%d-%s.tmp.jpg" % (out, os.getpid(), uuid.uuid4().hex[:8])
    with _THUMB_SEM:
        if os.path.isfile(out) and os.path.getsize(out) > 0:  # yêu cầu khác vừa cắt xong cùng ảnh trong lúc chờ
            return out
        import card as CARD
        for src in nguon:
            vf = "scale=-2:%d" % cao
            if hdr and src == p:   # cùng chuỗi chuyển màu của bản xem nhẹ (sua_tay._lam) / bản xuất
                vf += (",setparams=color_primaries=bt2020:color_trc=%s:colorspace=bt2020nc:range=tv,zscale=t=linear:npl=100,"
                       "format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p" % hdr)
            hw = CARD.giai_ma() if src == p else None   # 10/11: cắt ảnh từ clip gốc (4K / HEVC 10-bit) thì đọc bằng card nếu máy có
            if hw:
                subprocess.run([ff, "-v", "error", "-y", "-ss", "%.2f" % t, "-hwaccel", hw, "-i", src, "-frames:v", "1", "-vf", vf,
                                "-q:v", "5" if cao == 360 else "3", tmp], capture_output=True, timeout=40, creationflags=CREATE_NO_WINDOW if IS_WIN else 0)
                if os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
                    break
            subprocess.run([ff, "-v", "error", "-y", "-ss", "%.2f" % t, "-i", src, "-frames:v", "1", "-vf", vf, "-q:v", "5" if cao == 360 else "3", tmp],
                           capture_output=True, timeout=40, creationflags=CREATE_NO_WINDOW if IS_WIN else 0)
            if hw and os.path.isfile(tmp) and os.path.getsize(tmp) > 0:   # card không ra ảnh mà CPU ra: card đọc clip hỏng
                CARD.bao_loi_gm(hw, "cắt ảnh khung " + os.path.basename(p))
            if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:  # clip ngắn hơn t: lấy khung đầu
                subprocess.run([ff, "-v", "error", "-y", "-i", src, "-frames:v", "1", "-vf", vf, "-q:v", "5" if cao == 360 else "3", tmp],
                               capture_output=True, timeout=40, creationflags=CREATE_NO_WINDOW if IS_WIN else 0)
            if os.path.isfile(tmp) and os.path.getsize(tmp) > 0:
                break
    if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
        try:
            os.remove(tmp)
        except OSError:
            pass
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
        raise ValueError("Không lấy được ảnh khung")
    try:
        os.replace(tmp, out)
    except OSError:   # Windows: yêu cầu khác vừa ghi xong cùng ảnh và file đang mở
        try:
            os.remove(tmp)
        except OSError:
            pass
        if not os.path.isfile(out):
            raise
    return out


def duyet_thu_muc(p):
    """Bảng chọn thư mục trong app (3/11, anh: hộp chọn thư mục Windows "chưa ô kê"): thư mục con của p dạng thẻ (số clip,
    ngày clip mới nhất, ảnh bìa = clip mới nhất), mới nhất lên đầu. p trống = thư mục clip mặc định (E:\\Video)."""
    goc = CFG.get("thu_muc_clip") or ""
    p = (p or "").strip().strip('"') or goc
    if IS_WIN and re.fullmatch(r"[A-Za-z]:", p):
        p += "\\"
    if not p or not os.path.isdir(p):
        raise ValueError("Không thấy thư mục này trên máy")
    p = os.path.abspath(p)

    def quet(d, sau=True):
        so, moi, bia, con = 0, 0.0, None, 0
        try:
            with os.scandir(d) as it:
                for e in it:
                    n = e.name
                    if n.startswith((".", "_", "$")):
                        continue
                    try:
                        if e.is_dir(follow_symlinks=False):
                            con += 1
                            if sau:
                                moi = max(moi, e.stat().st_mtime)
                        elif os.path.splitext(n)[1].lower() in VIDEO_EXT and e.is_file():
                            so += 1
                            mt = e.stat().st_mtime
                            if mt >= moi:
                                moi, bia = mt, e.path
                    except OSError:
                        pass
        except OSError:
            return None
        return {"so_clip": so, "so_thu_muc": con, "mt": moi or (os.path.getmtime(d) if os.path.isdir(d) else 0), "bia": bia}
    con = []
    try:
        ten = [e.name for e in os.scandir(p) if not e.name.startswith((".", "_", "$")) and e.is_dir(follow_symlinks=False)]
    except OSError as ex:
        raise ValueError("Không mở được thư mục: %s" % ex)
    for n in ten[:400]:
        d = os.path.join(p, n)
        x = quet(d)
        if x is None:
            continue
        x.update({"ten": n, "p": d})
        con.append(x)
        if x["bia"]:
            with LOCK:
                LISTED.add(norm(d))
    con.sort(key=lambda x: (not (x["so_clip"] or x["so_thu_muc"]), -(x["mt"] or 0), x["ten"].lower()))   # thư mục trống xuống cuối
    nay = quet(p, sau=False) or {"so_clip": 0, "so_thu_muc": 0, "mt": 0, "bia": None}
    if nay["bia"]:
        with LOCK:
            LISTED.add(norm(p))
    cha = os.path.dirname(p.rstrip("\\/")) or ""
    if cha and IS_WIN and re.fullmatch(r"[A-Za-z]:", cha):
        cha += "\\"
    if cha and (norm(cha) == norm(p) or not os.path.isdir(cha)):   # gốc ổ đĩa (E:\\) / gốc "/": không lên nữa
        cha = ""
    o_dia = []
    if IS_WIN:
        import string
        o_dia = [c + ":\\" for c in string.ascii_uppercase if os.path.isdir(c + ":\\")]
    nhanh, home = [], os.path.expanduser("~")
    ung = [(goc, "Thư mục clip")] if goc else []
    for ten_tm, nhan in (("Desktop", "Màn hình"), ("Downloads", "Tải về"), ("Videos", "Video (Windows)"), ("Pictures", "Ảnh"),
                         ("Documents", "Tài liệu"), (os.path.join("OneDrive", "Desktop"), "OneDrive · Màn hình")):
        ung.append((os.path.join(home, ten_tm), nhan))
    seen = set()
    for d, nhan in ung:
        if d and os.path.isdir(d) and norm(d) not in seen:
            seen.add(norm(d))
            nhanh.append({"ten": nhan, "p": d})
    return {"thu_muc": p, "cha": cha, "goc": goc, "con": con, "so_clip": nay["so_clip"], "bia": nay["bia"], "o_dia": o_dia,
            "nhanh": nhanh}


def chon_thu_muc(start):
    """BỎ hộp chọn thư mục kiểu Windows (PowerShell FolderBrowserDialog), 4/11: hộp hay mở SAU cửa sổ app nên anh không thấy,
    app treo chờ 900 giây rồi TimeoutExpired (nhật ký máy tiệm 31/10, 3/11). Giao diện đã dùng bảng chọn thư mục trong trang
    (dev/_chon-thu-muc.js + /api/thu-muc); trang cũ còn gọi thì báo ngay, không mở hộp, không treo."""
    raise ValueError("Bấm nút Chọn thư mục để mở bảng chọn thư mục trong app (tải lại trang bằng F5 nếu chưa thấy)")


# ---------------------------------------------------------------- đơn dựng
TRUC = ["mo_dau", "chuyen_dong", "nhip", "chuyen_canh", "diem_nhan", "lop_phu", "am_nhan", "thanh_tien_trinh",
        "bo_font", "hoat_hinh", "chu", "phu_de", "ket"]
LOAI = {"ban_ipad": "Bán iPad", "ban_laptop": "Bán laptop", "meo": "Mẹo / review", "vui": "Vui trong tiệm"}
DUONG = {"premiere": "Premiere", "may_chu": "Dựng bằng ffmpeg"}


TOC_GIONG = {"-5%": "chậm", "+10%": "vừa", "+20%": "nhanh"}


GIONG_MAU = os.path.join(APP, "giong-mau")   # r39: mp3 nghe thử gói sẵn (trend-<kiểu>.mp3, vn-<giọng>.mp3), cùng dạng để trong kho effect
_PHONG = {}


def phong_ds():
    """Phong cách giọng (engine/phong_giong.py, r39): [{id, ten, mo_ta}]. Nạp file của engine (chỉ thư viện chuẩn) theo mtime;
    engine cũ chưa có file -> [] (app ẩn kiểu trend, giọng thường chạy như cũ)."""
    p = os.path.join(engine()["dir"], "phong_giong.py")
    try:
        mt = os.path.getmtime(p)
    except OSError:
        return []
    if _PHONG.get("mt") != mt:
        try:
            import importlib.util
            sp = importlib.util.spec_from_file_location("poly_phong_giong", p)
            m = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(m)
            _PHONG.update(mt=mt, ds=[x for x in m.ds_phong() if isinstance(x, dict) and re.fullmatch(r"[a-z0-9-]{1,30}", str(x.get("id")))])
        except Exception:   # noqa: BLE001 - file engine hỏng: coi như chưa có phong cách
            traceback.print_exc()
            _PHONG.update(mt=mt, ds=[])
    return _PHONG.get("ds") or []


def giong_mau_url(f):
    return "/api/sua-tay/giong-mau?f=" + quote(f) if isinstance(f, str) and re.fullmatch(r"[a-z0-9-]{1,60}\.mp3", f) \
        and os.path.isfile(os.path.join(GIONG_MAU, f)) else None


def giong_ds():
    """Danh sách giọng AI từ engine/giong-ds.json: 25 giọng VieNeu (chạy trên máy) + 2 giọng Microsoft (cần mạng).
    r39: + "trend" (engine/giong-trend.json: 9 kiểu = giọng + tốc độ + phong cách, chỉ kiểu có giọng / tốc độ / phong cách hợp lệ),
    "phong" (phong cách), mỗi giọng thêm "nhan" (nhãn kiểu) và "mau" (url mp3 nghe thử gói sẵn, nếu có)."""
    d = read_json(os.path.join(engine()["dir"], "giong-ds.json"), {}) or {}
    ds = [dict(x, nguon="vieneu") for x in d.get("vieneu") or [] if isinstance(x, dict) and x.get("id")]
    ds += [dict(x, nguon="microsoft") for x in d.get("microsoft") or [] if isinstance(x, dict) and x.get("id")]
    if not ds:
        ds = [{"id": "nu", "ten": "Hoài My", "gioi": "nữ", "mien": "miền Bắc", "cach": "Microsoft", "nguon": "microsoft"},
              {"id": "nam", "ten": "Nam Minh", "gioi": "nam", "mien": "miền Bắc", "cach": "Microsoft", "nguon": "microsoft"}]
    ss = read_json(engine()["san_sang"], {}) or {}
    vn = bool((ss.get("vieneu") or {}).get("ok"))
    md = d.get("mac_dinh") if vn and any(x["id"] == d.get("mac_dinh") for x in ds) else "nu"
    tr = read_json(os.path.join(engine()["dir"], "giong-trend.json"), {}) or {}
    ng = tr.get("nhan_giong") if isinstance(tr.get("nhan_giong"), dict) else {}
    for x in ds:
        n = (ng.get(x["id"]) or {}).get("nhan") if isinstance(ng.get(x["id"]), dict) else None
        if isinstance(n, list):
            x["nhan"] = [str(y)[:24] for y in n if isinstance(y, str)][:4]
        u = giong_mau_url(str(x["id"]) + ".mp3")
        if u:
            x["mau"] = u
    ph = phong_ds()
    ids, pids = {x["id"]: x for x in ds}, {x["id"] for x in ph}
    trend = []
    for k in tr.get("kieu") or [] if ph else []:
        if not isinstance(k, dict) or not re.fullmatch(r"[a-z0-9-]{1,40}", str(k.get("id"))) or k.get("giong") not in ids \
                or k.get("toc_do") not in TOC_GIONG or k.get("phong") not in pids:
            continue
        g = ids[k["giong"]]
        if g["nguon"] == "vieneu" and not vn:
            continue   # máy chưa cài VieNeu: kiểu dùng giọng VieNeu không chạy được
        trend.append({"id": k["id"], "ten": str(k.get("ten") or k["id"])[:40], "nhan": [str(y)[:24] for y in k.get("nhan") or [] if isinstance(y, str)][:4],
                      "hop": str(k.get("hop") or "")[:120], "giong": k["giong"], "ten_giong": g["ten"], "toc_do": k["toc_do"], "phong": k["phong"],
                      "mau": giong_mau_url(k.get("mau"))})
    return {"ds": ds, "mac_dinh": md, "vieneu": vn, "trend": trend, "phong": ph}


def phong_hop_le(p):
    """Phong cách trang gửi lên: id có trong engine (bỏ trống / "goc" = không phong cách) -> id hoặc None."""
    return p if isinstance(p, str) and p != "goc" and any(x["id"] == p for x in phong_ds()) else None


def kieu_hop_le(k):
    return k if isinstance(k, str) and re.fullmatch(r"[a-z0-9-]{1,40}", k) else None


def giong_hop_le(g):
    return any(x["id"] == g for x in giong_ds()["ds"])


CAU_THU = "Chào anh em, hôm nay Poly lên con iPad Pro M1 màn mười hai chấm chín, máy đẹp, pin còn ngon."


def giong_thu(data):
    """Nghe thử giọng AI: engine giong.py --thu -> mp3 trong _cache/giong (có rồi thì dùng lại). Cần mạng + edge-tts."""
    gd = giong_ds()
    g = data.get("giong") if giong_hop_le(data.get("giong")) else gd["mac_dinh"]
    ten = next((x["ten"] for x in gd["ds"] if x["id"] == g), g)
    toc = data.get("toc_do") if data.get("toc_do") in TOC_GIONG else "+10%"
    ph = phong_hop_le(data.get("phong"))   # r39: nghe thử có phong cách (không có: lệnh / file như cũ)
    e = engine()
    if not os.path.isfile(e["py"]) or not os.path.isfile(os.path.join(e["dir"], "giong.py")):
        raise ValueError("Chưa cài bộ dựng (bấm đúp CAI-DAT.bat trong E:\\Tool\\poly-dung-video)")
    d = os.path.join(CACHE, "giong")
    os.makedirs(d, exist_ok=True)
    mp3 = os.path.join(d, "thu-%s-%s%s.mp3" % (re.sub(r"[^a-z0-9-]", "", g), toc.replace("%", "").replace("+", "p").replace("-", "m"),
                                                "-" + ph if ph else ""))
    if not (os.path.isfile(mp3) and os.path.getsize(mp3) > 500):
        env = dict(os.environ, PYTHONUTF8="1", POLY_FFMPEG_DIR=e["bin"])
        kw = {"creationflags": CREATE_NO_WINDOW} if IS_WIN else {}
        try:
            r = subprocess.run([e["py"], os.path.join(e["dir"], "giong.py"), "--thu", CAU_THU, mp3, "--giong", g, "--toc-do", toc]
                               + (["--phong", ph] if ph else []),
                               cwd=e["dir"], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240, **kw)
        except subprocess.TimeoutExpired:
            raise ValueError("Tạo giọng thử quá lâu (lần đầu giọng VieNeu nạp model khoảng nửa phút), bấm lại thử")
        if r.returncode or not os.path.isfile(mp3):
            loi = (r.stdout + r.stderr).strip().splitlines()
            m = [x for x in loi if x.startswith("LOI=")]
            if any("edge_tts" in x or "vieneu" in x for x in loi) and not m:
                raise ValueError("Bộ dựng chưa có giọng AI: chạy lại CAI-DAT.bat trong E:\\Tool\\poly-dung-video 1 lần (cần mạng)")
            raise ValueError((m[-1][4:] if m else "Không tạo được giọng thử") [:300])
    out = {"url": "/file?p=" + quote(mp3) + "&v=%d" % int(os.path.getmtime(mp3)), "giong": ten, "toc_do": TOC_GIONG[toc]}
    if ph:
        out["phong"] = ph
    return out


def chuan_hoa_don(data):
    if not isinstance(data, dict):
        raise ValueError("Đơn dựng sai dạng")
    if not isinstance(data.get("kieu") or {}, dict):
        raise ValueError("Kiểu dựng sai dạng")
    def s(k, n=300):
        return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(data.get(k) or "")).strip()[:n]
    tm = s("thu_muc", 400).strip('"')
    if not tm or not os.path.isdir(tm):
        raise ValueError("Không thấy thư mục clip: " + (tm or "(trống)"))
    clips = data.get("clip") or []
    if isinstance(clips, str):
        clips = [x.strip() for x in re.split(r"[,;\n]+", clips) if x.strip()]
    co = {fn.lower(): fn for fn in os.listdir(tm)}
    chon = []
    for c in clips[:200]:
        c = base(str(c))
        if c.lower() in co:
            chon.append(co[c.lower()])
        else:  # gõ tên không có đuôi: IMG_5123
            m = [v for k, v in co.items() if os.path.splitext(k)[0] == c.lower() and os.path.splitext(k)[1] in VIDEO_EXT]
            if m:
                chon.append(m[0])
            else:
                raise ValueError("Không thấy clip %s trong thư mục" % c)
    if not chon and not any(os.path.splitext(k)[1] in VIDEO_EXT for k in co):
        raise ValueError("Thư mục này chưa có clip video nào")
    loai = s("loai") if s("loai") in LOAI else "ban_ipad"
    kieu = {}
    for k in TRUC:
        v = str((data.get("kieu") or {}).get(k) or "tu_dong")
        kieu[k] = v if re.fullmatch(r"[a-z_]{2,30}", v) else "tu_dong"
    ten = s("ten", 120)
    goc = ten or base(tm.rstrip("\\/")) or LOAI[loai]
    sl = slugify(goc) or "video"
    if not re.search(r"(20\d\d|\d{4})$", sl):
        sl += "-" + time.strftime("%d%m")
    ra = CFG.get("thu_muc_ra") or ""
    dung = set()
    for jid in (os.listdir(JOBS) if os.path.isdir(JOBS) else []):
        dung.add(((read_json(os.path.join(JOBS, jid, "job.json")) or {}).get("don") or {}).get("slug"))
    goc_sl, i = sl, 2
    while sl in dung or (ra and os.path.exists(os.path.join(ra, sl))):
        sl = "%s-%d" % (goc_sl, i)
        i += 1
    don = {
        "ten": ten or base(tm.rstrip("\\/")), "slug": sl, "thu_muc": tm, "clip": chon,
        "loai": loai, "may": s("may", 120) if loai.startswith("ban_") else "", "gia": s("gia", 60) if loai.startswith("ban_") else "",
        "hook1": s("hook1", 60), "hook2": s("hook2", 60),
        "do_dai": s("do_dai") if s("do_dai") in ("30-45", "45-60", "75-95") else "75-95",
        "kieu_che_do": s("kieu_che_do") if s("kieu_che_do") in ("xoay_vong", "dung_gu", "tu_chon") else "xoay_vong",
        "kieu": kieu, "giong": "giong_ai" if s("giong") == "giong_ai" else "loi_that",
        "giong_ai_ten": s("giong_ai_ten") if giong_hop_le(s("giong_ai_ten")) else giong_ds()["mac_dinh"],
        "giong_ai_toc": s("giong_ai_toc") if s("giong_ai_toc") in TOC_GIONG else "+10%",
        "duong": "may_chu" if s("duong") == "may_chu" else "premiere",
        "ghi_chu": s("ghi_chu", 2000), "duyet_truoc": bool(data.get("duyet_truoc")),
    }
    return don


def _nhan_thu_muc(job, p):
    """Dòng THU_MUC_VIDEO= Claude in: chỉ nhận khi đúng thư mục app giao, hoặc thư mục con có thật trong thư mục ra."""
    ra = CFG.get("thu_muc_ra") or ""
    try:
        return norm(p) == norm(thu_muc_video(job)) or (trong(p, ra) and norm(p) != norm(ra) and os.path.isdir(p))
    except (OSError, ValueError):
        return False


def thu_muc_video(job):
    return job.get("thu_muc_video") or os.path.join(CFG.get("thu_muc_ra") or "", (job.get("don") or {}).get("slug") or "")


# ---------------------------------------------------------------- prompt
def read_prompt(name):
    with open(os.path.join(PROMPTS, name), "r", encoding="utf-8") as f:
        return f.read()


def fill(tpl, data):
    def rep(m):
        return str(data.get(m.group(1), ""))
    return re.sub(r"\{([a-z_]+)\}", rep, tpl)


def _du_lieu(job):
    don = job["don"]
    e = engine()
    return {
        "don_json": json.dumps(don, ensure_ascii=False, indent=1),
        "ten": don.get("ten"), "slug": don.get("slug"),
        "thu_muc_video": thu_muc_video(job), "thu_muc_clip": don.get("thu_muc"),
        "clip_list": ", ".join(don.get("clip") or []) or "(cả thư mục)",
        "loai": LOAI.get(don.get("loai"), don.get("loai")), "duong": DUONG.get(don.get("duong"), don.get("duong")),
        "engine": e["dir"], "premiere_dir": CFG.get("premiere_dir"), "job_dir": job_dir(job["id"]),
        "home": os.path.expanduser("~"),
        "duyet_truoc": ("ĐÃ DUYỆT: anh đã duyệt kế hoạch, dựng tới mp4, không dừng chờ duyệt nữa" if job.get("duyet")
                        else "CÓ: làm tới kế hoạch thì dừng chờ anh duyệt") if don.get("duyet_truoc") else "KHÔNG: dựng luôn tới mp4",
    }


def build_prompt_dung(job):
    return fill(read_prompt("dung-video.txt"), _du_lieu(job))


def build_prompt_duyet(job, sua):
    d = _du_lieu(job)
    dong = []
    if sua.get("hook1") is not None or sua.get("hook2") is not None:
        dong.append("- Hook: \"%s\" / \"%s\"" % (sua.get("hook1") or "", sua.get("hook2") or ""))
    if sua.get("ghi_chu"):
        dong.append("- Anh dặn thêm: " + sua["ghi_chu"])
    for q, c in sua.get("tra_loi") or []:
        dong.append("- Câu hỏi \"%s\": anh chọn \"%s\"" % (q, c))
    d["sua_duyet"] = "\n".join(dong) or "- (anh không sửa gì, dựng đúng kế hoạch)"
    return fill(read_prompt("duyet-ke-hoach.txt"), d)


HOI_RE = re.compile(r"^[\s*_`-]*(?:\d+[.)]\s*)?[*_`]*HOI_FEN[*_`]*\s*:\s*(.+?)\s*$", re.M)


def tach_hoi(text):
    """Dòng HOI_FEN: câu hỏi | lựa chọn đang dùng | lựa chọn khác [| ...] -> [{q, opts}] (tối đa 3 câu, 4 lựa chọn)."""
    hoi = []
    for m in HOI_RE.finditer(text or ""):
        parts = [x.strip(" *_`") for x in m.group(1).split("|")]
        parts = [x for x in parts if x]
        if len(parts) >= 3 and len(hoi) < 3:
            hoi.append({"q": parts[0], "opts": parts[1:5]})
    return hoi, HOI_RE.sub("", text or "").strip()


def build_prompt_tra_loi(job, hoi, chon):
    dong = []
    for i, h in enumerate(hoi):
        c = chon.get(str(i))
        if c is None:
            continue
        o = h["opts"][int(c)] if str(c).isdigit() and int(c) < len(h["opts"]) else str(c)
        dong.append("- %s → %s%s" % (h["q"], o, " (giữ như đang làm)" if str(c) == "0" else ""))
    d = _du_lieu(job)
    d["tra_loi"] = "\n".join(dong)
    return fill(read_prompt("tra-loi.txt"), d)


def build_prompt_sua(job, text, resumed):
    d = _du_lieu(job)
    d["yeu_cau"] = text.strip()
    return fill(read_prompt("sua-video.txt" if resumed else "sua-video-moi.txt"), d)


# ---------------------------------------------------------------- doc log Claude (giữ cách đọc của Poly Dựng Bài)
TOOL_VI = {
    "Read": "Đọc", "Write": "Ghi", "Edit": "Sửa", "MultiEdit": "Sửa", "NotebookEdit": "Sửa",
    "Glob": "Tìm file", "Grep": "Tìm trong file", "WebSearch": "Tìm trên mạng",
    "WebFetch": "Mở trang", "Skill": "Dùng skill", "ToolSearch": "Nạp công cụ",
}


def humanize(name, inp):
    inp = inp or {}
    if name in ("Agent", "Task"):
        t = inp.get("subagent_type")
        return "agent", "Giao việc: %s" % (inp.get("description") or (t or "agent").split(":")[-1])
    if name == "Bash" or name == "PowerShell":
        return "tool", "Chạy lệnh: " + short(inp.get("description") or inp.get("command"), 90)
    if name in ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit"):
        return "tool", "%s %s" % (TOOL_VI[name], base(inp.get("file_path") or inp.get("notebook_path") or ""))
    if name in ("Glob", "Grep"):
        return "tool", "%s: %s" % (TOOL_VI[name], short(inp.get("pattern"), 60))
    if name == "WebSearch":
        return "tool", "Tìm trên mạng: " + short(inp.get("query"), 80)
    if name == "WebFetch":
        u = urlparse(str(inp.get("url", "")))
        return "tool", "Mở trang: " + (u.netloc or short(inp.get("url"), 60))
    if name == "Skill":
        return "tool", "Dùng skill " + str(inp.get("skill") or inp.get("command") or "")
    if name.startswith("mcp__"):
        return "tool", "Công cụ: " + name.split("__")[-1]
    if name in ("TaskOutput", "TaskGet", "TaskList", "ToolSearch"):
        return None, None
    return "tool", TOOL_VI.get(name, name)


SUB_VI = {
    "error_max_turns": "Claude làm quá nhiều bước nên tự dừng. Bấm Chạy tiếp để làm nốt.",
    "error_during_execution": "Claude gặp lỗi giữa chừng. Bấm Chạy tiếp để làm nốt.",
    "error_max_budget_usd": "Hết hạn mức của lượt này. Bấm Chạy tiếp để làm nốt.",
}

MARK_RE = re.compile(r"^[\s*_`>-]*(THU_MUC_VIDEO|MP4|CHO_DUYET|LOI)[*_`\s]*=[*_`'\"\s]*([^\r\n]*)$", re.M)


def _sach_duong(s):
    p = re.split(r"[`*'\"]| \(| [-–] ", (s or "").strip())[0].strip().rstrip(".,;:)\\/ ")
    return p if re.match(r"([A-Za-z]:|/)", p) else ""


def doc_dau(text):
    """Các dòng dấu Claude in ra: THU_MUC_VIDEO=, MP4=, CHO_DUYET=, LOI=."""
    out = {}
    for m in MARK_RE.finditer(text or ""):
        k, v = m.group(1), m.group(2)
        out[k] = v.strip(" *_`'\"") if k == "LOI" else _sach_duong(v)
    return out


def bo_dau_dong(text):
    return MARK_RE.sub("", text or "").strip()


def new_state():
    return {
        "events": [], "tasks": {}, "task_order": [], "pending_tasks": {},
        "session_id": None, "results": [], "folder": None, "offsets": {},
        "agents": {}, "model": None, "last_new": now(), "gen": "%x" % int(time.time() * 1000), "cost": 0.0,
    }


def add_event(st, kind, text, run, sub=False, t=None):
    st["events"].append({"i": len(st["events"]), "k": kind, "x": text, "r": run, "s": bool(sub), "t": t or now()})
    st["last_new"] = now()


def note_folder(st, s):
    d = doc_dau(s)
    if d.get("THU_MUC_VIDEO"):
        st["folder"] = d["THU_MUC_VIDEO"]


def handle_line(st, obj, run):
    typ = obj.get("type")
    sub = bool(obj.get("parent_tool_use_id"))
    if typ in ("assistant", "user") and not sub:
        st.setdefault("sau_kq", {})[run] = True  # còn làm sau result -> result đó chưa phải câu cuối
    if typ == "system":
        if obj.get("subtype") == "init":
            st["session_id"] = obj.get("session_id") or st["session_id"]
            st["model"] = obj.get("model") or st["model"]
            if run not in st.setdefault("init_luot", set()):
                st["init_luot"].add(run)
                add_event(st, "info", "Claude bắt đầu làm", run)
        elif obj.get("subtype") in ("api_retry", "api_error"):
            add_event(st, "warn", "Mạng / API lỗi, Claude thử lại…", run)
        elif obj.get("subtype") == "compact_boundary":
            add_event(st, "info", "Claude gọn lại bộ nhớ hội thoại", run)
        return
    if typ == "assistant":
        msg = obj.get("message") or {}
        for b in msg.get("content") or []:
            bt = b.get("type")
            if bt == "text":
                txt = b.get("text") or ""
                if not sub:
                    note_folder(st, txt)
                show = bo_dau_dong(txt)
                if show and not sub:
                    add_event(st, "text", show, run)
            elif bt == "tool_use":
                name = b.get("name") or ""
                inp = b.get("input") or {}
                if name in ("TodoWrite", "TaskCreate") and not sub and st.get("task_run") != run:
                    st["tasks"], st["task_order"], st["task_run"] = {}, [], run
                if name == "TodoWrite" and not sub:
                    st["tasks"], st["task_order"] = {}, []
                    for i, td in enumerate(inp.get("todos") or []):
                        k = "td%d" % i
                        st["tasks"][k] = {"x": td.get("content") or td.get("activeForm") or "", "st": td.get("status", "pending")}
                        st["task_order"].append(k)
                    continue
                if name == "TaskCreate" and not sub:
                    st["pending_tasks"][b.get("id")] = inp.get("subject") or ""
                    continue
                if name == "TaskUpdate" and not sub:
                    tid = str(inp.get("taskId", ""))
                    if st.get("task_run") != run and tid in st["tasks"]:
                        st["task_run"] = run   # lượt tiếp (duyệt, chạy tiếp) cập nhật danh sách bước cũ -> hiện lại danh sách đó
                    t = st["tasks"].get(tid)
                    if t is None:
                        t = st["tasks"][tid] = {"x": inp.get("subject") or ("Việc " + tid), "st": "pending"}
                        if tid not in st["task_order"]:
                            st["task_order"].append(tid)
                    if inp.get("status"):
                        t["st"] = inp["status"]
                    if inp.get("subject"):
                        t["x"] = inp["subject"]
                    continue
                kind, text = humanize(name, inp)
                if kind:
                    if kind == "agent":
                        st["agents"][b.get("id")] = text
                    add_event(st, kind, text, run, sub)
        return
    if typ == "user":
        msg = obj.get("message") or {}
        content = msg.get("content")
        if not isinstance(content, list):
            return
        for b in content:
            if b.get("type") != "tool_result":
                continue
            tuid = b.get("tool_use_id")
            res = b.get("content")
            if isinstance(res, list):
                res = " ".join(x.get("text", "") for x in res if isinstance(x, dict))
            res = str(res or "")
            if tuid in st["pending_tasks"]:
                subj = st["pending_tasks"].pop(tuid)
                m = re.search(r"#(\d+)", res)
                tid = m.group(1) if m else "p%d" % len(st["tasks"])
                st["tasks"][tid] = {"x": subj, "st": "pending"}
                if tid not in st["task_order"]:
                    st["task_order"].append(tid)
            elif tuid in st["agents"] and not sub:
                add_event(st, "agentdone", "Xong: " + st["agents"][tuid].replace("Giao việc: ", ""), run)
            if b.get("is_error") and not sub:
                add_event(st, "info", "Công cụ báo lỗi, Claude tự xử lý: " + short(res, 140), run)
        return
    if typ == "result":
        r = {
            "run": run, "ok": not obj.get("is_error") and obj.get("subtype") == "success",
            "subtype": obj.get("subtype"), "text": obj.get("result") or "",
            "ms": obj.get("duration_ms"), "turns": obj.get("num_turns"),
            "session_id": obj.get("session_id"), "cost": obj.get("total_cost_usd"),
        }
        st["session_id"] = obj.get("session_id") or st["session_id"]
        note_folder(st, r["text"])
        den = obj.get("permission_denials") or []
        if den:
            names = []
            for x in den:
                nm = x.get("tool_name") or x.get("name") or "?"
                cmdx = (x.get("tool_input") or {}).get("command")
                names.append(nm + (": " + short(cmdx, 60) if cmdx else ""))
            add_event(st, "info", "Claude bị chặn %d lệnh (thường không ảnh hưởng video): %s" % (len(den), "; ".join(names[:3])), run)
        st["results"].append(r)
        st.setdefault("sau_kq", {})[run] = False
        if not r["ok"]:
            add_event(st, "error", SUB_VI.get(r["subtype"]) or ("Claude dừng vì lỗi: " + short(explain_err(r["text"] or r["subtype"] or ""), 200)), run)


def _luot_xong(st, run):
    """Lượt đã kết thúc có tính là XONG không: result cuối ok, sau result đó Claude không làm gì thêm,
    mã thoát 0 nếu biết, anh không bấm Dừng."""
    n = run["n"]
    res = [r for r in st["results"] if r["run"] == n]
    if not res or not res[-1]["ok"] or st.setdefault("sau_kq", {}).get(n):
        return False
    if run.get("exit") not in (None, 0) or run.get("ket_qua") == "dung":
        return False
    return True


def _danh_dau_ket(st, run):
    n = run["n"]
    dm = st.setdefault("ket_luot", set())
    if n in dm:
        return
    kq = run.get("ket_qua") or ("xong" if _luot_xong(st, run) else None)
    if kq == "xong":
        add_event(st, "done", "Xong lượt này", n)
    elif kq == "dung":
        add_event(st, "warn", "Anh đã dừng video này", n)
    elif kq == "loi" and run.get("ly_do"):
        add_event(st, "error", run["ly_do"], n)
    else:
        return
    dm.add(n)


def _doc_luot(st, p, n):
    if not os.path.exists(p):
        return
    off = st["offsets"].get(n, 0)
    size = os.path.getsize(p)
    if size <= off:
        return
    with open(p, "rb") as f:
        f.seek(off)
        chunk = f.read()
    last_nl = chunk.rfind(b"\n")
    if last_nl < 0:
        return
    body = chunk[: last_nl + 1]
    st["offsets"][n] = off + len(body)
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", "replace"))
        except Exception:
            continue
        try:
            handle_line(st, obj, n)
        except Exception:
            log("parse loi: " + traceback.format_exc())


def parse_tail(jid, st, job):
    for run in job.get("runs", []):
        n = run["n"]
        p = os.path.join(job_dir(jid), "stream-%d.jsonl" % n)
        if not os.path.exists(p):
            continue
        off = st["offsets"].get(n, 0)
        with open(p, "rb") as f:
            f.seek(off)
            rest = f.read()
        st["offsets"][n] = off + len(rest)
        for line in rest.splitlines():
            try:
                handle_line(st, json.loads(line.decode("utf-8", "replace")), n)
            except Exception:
                pass


def parse_job(jid):
    """Doc tiep phan log moi cua moi luot chay, cap nhat cache. Doc job.json TRONG LOCK."""
    with LOCK:
        job = load_job(jid)
        if not job:
            return None, None
        st = STATE.get(jid)
        if st is None:
            st = STATE[jid] = new_state()
        for run in job.get("runs", []):
            n = run["n"]
            _doc_luot(st, os.path.join(job_dir(jid), "stream-%d.jsonl" % n), n)
            if run.get("ended"):
                _danh_dau_ket(st, run)
        changed = False
        if st["folder"] and job.get("thu_muc_video") != st["folder"] and _nhan_thu_muc(job, st["folder"]):
            job["thu_muc_video"] = st["folder"]
            changed = True
        if st["session_id"] and job.get("session_id") != st["session_id"]:
            job["session_id"] = st["session_id"]
            changed = True
        runs = job.get("runs", [])
        if runs and job.get("status") == "dang-chay":
            last = runs[-1]
            if not pid_alive(last.get("pid"), last.get("started")):
                time.sleep(0.2)
                parse_tail(jid, st, job)
                res = [r for r in st["results"] if r["run"] == last["n"]]
                last["ended"] = last.get("ended") or now()
                if job.get("stop_req"):
                    job["status"] = last["ket_qua"] = "dung"
                elif _luot_xong(st, last):
                    dau = doc_dau(res[-1].get("text") or "") if res else {}
                    if dau.get("LOI"):   # Claude làm hết lượt nhưng báo không dựng được (vd Premiere chưa mở)
                        job["status"] = last["ket_qua"] = "loi"
                        last["ly_do"] = short(dau["LOI"], 300)
                        job["loi_luot"], job["loi_ly_do"] = last["n"], last["ly_do"]
                    else:
                        job["status"] = last["ket_qua"] = "xong"
                    if dau.get("MP4"):
                        job["mp4_luot"] = last["n"]
                    if dau.get("CHO_DUYET"):
                        job["cho_duyet_luot"] = last["n"]   # danh sách bên trái hiện "Chờ duyệt" kể cả khi anh chưa mở video
                else:
                    job["status"] = last["ket_qua"] = "loi"
                    if not res or res[-1]["ok"]:
                        err = read_text(os.path.join(job_dir(jid), "stderr-%d.txt" % last["n"]))[-800:]
                        last["ly_do"] = "Claude dừng giữa chừng. " + short(explain_err(err), 300)
                _danh_dau_ket(st, last)
                job.pop("stop_req", None)
                changed = True
        if changed:
            save_job(job)
        return job, st


def explain_err(err):
    e = err or ""
    low = e.lower()
    if "not logged in" in low or "/login" in low or "api key" in low or "authenticat" in low or "401" in low:
        return "Claude Code trên máy chưa đăng nhập. Bấm Đăng nhập, chọn tài khoản Claude 1 lần là xong."
    if "rate limit" in low or "usage limit" in low or "limit reached" in low:
        return "Hết lượt dùng Claude tạm thời, chờ một lúc rồi bấm Chạy tiếp."
    if "plugin" in low and ("not found" in low or "invalid" in low):
        return "Không nạp được bộ quy tắc dựng video (plugin poly-video). Bấm chip Claude ở góc trên để kiểm máy."
    return e.strip() or "Không có thông báo lỗi."


# ---------------------------------------------------------------- chay Claude
def start_run(job, prompt, kind, resume=None, label=None):
    cmd = resolve_claude()
    if not cmd:
        raise RuntimeError("Không tìm thấy Claude Code trên máy.")
    n = len(job.get("runs", [])) + 1
    d = job_dir(job["id"])
    with open(os.path.join(d, "prompt-%d.txt" % n), "w", encoding="utf-8") as f:
        f.write(prompt)
    args = cmd + ["-p", "--output-format", "stream-json", "--verbose"]
    mode = CFG.get("che_do_quyen") or ""
    if mode:
        args += ["--permission-mode", mode]
    model = job.get("model") or CFG.get("model")
    if model:
        args += ["--model", model]
    if CFG.get("cho_phep_them"):
        args += ["--allowedTools"] + list(CFG["cho_phep_them"])
    if resume:
        args += ["--resume", resume]
    pd = plugin_dir()
    if pd:
        args += ["--plugin-dir", pd]
    lc = os.path.join(PROMPTS, "luat-chung.md")
    if os.path.isfile(lc):
        args += ["--append-system-prompt-file", lc]
    e = engine()
    don = job.get("don") or {}
    ra = CFG.get("thu_muc_ra") or ""
    if ra and not os.path.isdir(ra):
        try:
            os.makedirs(ra, exist_ok=True)
        except OSError:
            pass
    dirs = [x for x in (CFG.get("them_thu_muc") or []) + [ra, e["dir"], CFG.get("premiere_dir") or "", don.get("thu_muc") or ""]
            if x and os.path.isdir(x)]
    seen, uniq = set(), []
    for x in dirs + [d]:
        if norm(x) not in seen:
            seen.add(norm(x))
            uniq.append(x)
    args += ["--add-dir"] + uniq   # --add-dir nhận nhiều thư mục: để cuối (prompt đi qua stdin)
    cwd = ra if ra and os.path.isdir(ra) else APP
    out = open(os.path.join(d, "stream-%d.jsonl" % n), "ab")
    err = open(os.path.join(d, "stderr-%d.txt" % n), "ab")
    env = dict(os.environ)
    env["POLY_APP"] = "video"
    env["CLAUDE_CODE_ENABLE_TODO_TOOLS"] = "1"   # chạy ngầm có task list -> app hiện tiến độ từng bước
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS", "8")
    # bộ dựng: python của engine đứng đầu PATH (lệnh "python ..." = python có đủ thư viện), ffmpeg trong engine\bin
    env["PATH"] = os.pathsep.join([x for x in (e["scripts"], e["bin"]) if os.path.isdir(x)] + [env.get("PATH", "")])
    env["POLY_ENGINE"] = e["dir"]
    env["POLY_FFMPEG_DIR"] = e["bin"]
    env["POLY_MO_HINH"] = e["mo_hinh"]
    env["POLY_FONT_DIR"] = e["font"]
    env["POLY_PREMIERE_DIR"] = CFG.get("premiere_dir") or ""
    env["POLY_THU_MUC_RA"] = ra
    if CFG.get("premiere_tu_mo_lai") is False:
        env["POLY_GUI_KHONG_MO_LAI"] = "1"
    if CFG.get("premiere_tu_mo") is not False:
        env["POLY_GUI_TU_MO_PREMIERE"] = "1"
    kw = {}
    if IS_WIN:
        kw["creationflags"] = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    else:
        kw["start_new_session"] = True
    pin = open(os.path.join(d, "prompt-%d.txt" % n), "rb")
    try:
        p = subprocess.Popen(args, cwd=cwd, stdin=pin, stdout=out, stderr=err, env=env, **kw)
    finally:
        pin.close()
        out.close()
        err.close()
    job.setdefault("runs", []).append({"n": n, "kind": kind, "label": label or {"dung": "Dựng video", "sua": "Sửa video", "tiep": "Chạy tiếp", "duyet": "Dựng theo kế hoạch"}.get(kind, kind),
                                       "pid": p.pid, "started": now(), "resume": resume})
    job["status"] = "dang-chay"
    save_job(job)
    log("chay %s %s luot %d pid %d" % (kind, job["id"], n, p.pid))
    threading.Thread(target=_reap, args=(p, job["id"]), daemon=True).start()
    return n


def _reap(p, jid):
    try:
        code = p.wait()
    except Exception:
        code = None
    time.sleep(0.5)
    try:
        with LOCK:
            job = load_job(jid)
            for r in (job or {}).get("runs", []):
                if r.get("pid") == p.pid and "exit" not in r:
                    r["exit"] = code
                    save_job(job)
    except Exception:
        log(traceback.format_exc())
    try:
        parse_job(jid)
    except Exception:
        log(traceback.format_exc())
    try:
        _chay_hang()   # video xong thì chạy luôn video đang xếp hàng
    except Exception:
        log(traceback.format_exc())


def so_dang_chay():
    n = 0
    for jid in (os.listdir(JOBS) if os.path.isdir(JOBS) else []):
        j = read_json(os.path.join(JOBS, jid, "job.json"))
        if j and j.get("status") == "dang-chay":
            try:
                j, _ = parse_job(jid)
            except Exception:
                pass
            if j and j.get("status") == "dang-chay":
                n += 1
    return n


def co_hang_cho():
    for jid in (os.listdir(JOBS) if os.path.isdir(JOBS) else []):
        if (read_json(os.path.join(JOBS, jid, "job.json")) or {}).get("status") == "cho":
            return True
    return False


VIEC = {"dung": "dựng video", "duyet": "dựng theo kế hoạch", "sua": "sửa video", "tiep": "chạy tiếp", "tra_loi": "trả lời câu hỏi"}


def xep_hang(job, kind, prompt=None, resume=None, label=None):
    """Premiere đang dựng video khác: đưa việc vào hàng. kind "dung" = video mới (dựng từ đầu); việc anh bấm
    (duyet, sua, tra_loi, tiep) mang sẵn prompt + phiên để chạy đúng việc đó, và chạy TRƯỚC video mới."""
    truoc = job.get("status") if job.get("status") != "cho" else (job.get("cho_lam") or {}).get("truoc")
    job["cho_lam"] = {"kind": kind, "prompt": prompt, "resume": resume, "label": label, "truoc": truoc}
    job["status"] = "cho"
    job["cho_luc"] = now()
    save_job(job)
    log("xep hang %s %s" % (job["id"], kind))
    threading.Thread(target=_chay_hang_an_toan, daemon=True).start()


def hang_tam_dung():
    """Lượt Premiere kết thúc gần nhất báo LOI vì Premiere / Poly Bridge, và giờ vẫn chưa có nhịp tim -> không tự chạy
    video Premiere tiếp (mỗi video sẽ lại dừng ở bước dựng, tốn lượt Claude). Trả lý do hoặc None."""
    moi = None
    for jid in (os.listdir(JOBS) if os.path.isdir(JOBS) else []):
        j = read_json(os.path.join(JOBS, jid, "job.json")) or {}
        r = (j.get("runs") or [None])[-1]
        if r and r.get("ended") and (moi is None or r["ended"] > moi[0]):
            moi = (r["ended"], j, r)
    if not moi:
        return None
    _, j, r = moi
    ly = j.get("loi_ly_do") if j.get("loi_luot") == r.get("n") else ""
    if ly and re.search(r"premiere|poly bridge", ly, re.I) and not premiere_nhip().get("song"):
        return ly
    return None


def create_job(data):
    don = chuan_hoa_don(data)
    if not resolve_claude():
        raise ValueError("Không tìm thấy Claude Code trên máy. Bấm chip Claude ở góc trên để kiểm lại.")
    jid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
    d = job_dir(jid)
    os.makedirs(d, exist_ok=True)
    job = {"id": jid, "don": don, "created": now(), "status": "moi", "runs": [], "model": CFG.get("model") or "",
           "thu_muc_video": os.path.join(CFG.get("thu_muc_ra") or "", don["slug"])}
    write_json(os.path.join(d, "don.json"), don)
    with LOCK:
        if so_dang_chay() >= int(CFG.get("dang_chay_toi_da") or 1) or co_hang_cho():
            xep_hang(job, "dung")   # xếp hàng (sau các video đang chờ): video đang dựng xong thì tự chạy
            return job
        save_job(job)
        try:
            start_run(job, build_prompt_dung(job), "dung")
        except Exception as e:
            job["status"], job["loi_chay"] = "loi", str(e)
            save_job(job)
            log("khong bat duoc Claude: %s" % e)
            raise ValueError(str(e))
    return job


def _uu_tien(j):
    cl = j.get("cho_lam") or {}
    return (0 if cl.get("kind") not in (None, "dung") else 1, j.get("cho_luc") or j.get("created") or 0)


def _chay_hang():
    if not co_hang_cho():
        return
    info = claude_info()   # gọi Claude kiểm đăng nhập NGOÀI khoá (có thể mất vài giây)
    if not resolve_claude() or info.get("login") is False:
        return
    with LOCK:
        cho = []
        for jid in sorted(os.listdir(JOBS)) if os.path.isdir(JOBS) else []:
            j = read_json(os.path.join(JOBS, jid, "job.json"))
            if j and j.get("status") == "cho":
                cho.append(j)
        if not cho or so_dang_chay() >= int(CFG.get("dang_chay_toi_da") or 1):
            return
        dung_pr = hang_tam_dung()
        for j in sorted(cho, key=_uu_tien):
            if dung_pr and (j.get("don") or {}).get("duong") == "premiere":
                continue   # Premiere chưa mở: video Premiere chờ tới khi có nhịp tim
            jj = load_job(j["id"])
            if not jj or jj.get("status") != "cho":
                continue
            cl = jj.pop("cho_lam", None) or {}
            kind = cl.get("kind") or "dung"
            try:
                if kind == "dung" or not cl.get("prompt"):
                    start_run(jj, build_prompt_dung(jj), "dung", None, "Dựng video (xếp hàng)")
                else:
                    start_run(jj, cl["prompt"], "sua" if kind == "tra_loi" else kind, cl.get("resume"),
                              (cl.get("label") or VIEC.get(kind, kind)) + " (xếp hàng)")
                log("hang: bat dau %s %s" % (jj["id"], kind))
            except Exception as e:
                jj["status"], jj["loi_chay"] = "loi", str(e)
                save_job(jj)
                log("hang: khong chay duoc %s: %s" % (jj["id"], e))
            return


def _chay_hang_an_toan():
    try:
        _chay_hang()
    except Exception:
        log(traceback.format_exc())


def hang_doi():
    while True:
        time.sleep(CFG.get("hang_giay") or 10)
        try:
            _chay_hang()
        except Exception:
            log(traceback.format_exc())


def _can_job(jid, cho_chay=False):
    job, st = parse_job(jid)
    if not job:
        raise ValueError("Không thấy video này")
    if job.get("status") == "dang-chay":
        raise ValueError("Video đang chạy, chờ xong hoặc bấm Dừng trước")
    if job.get("status") == "cho" and not cho_chay:
        raise ValueError("Video đang xếp hàng")
    return job, st


def ban():
    return so_dang_chay() >= int(CFG.get("dang_chay_toi_da") or 1)


def duyet_job(jid, data):
    """Anh duyệt kế hoạch (có thể sửa hook / dặn thêm) -> chạy tiếp phiên cũ, dựng tới mp4."""
    with LOCK:
        job, st = _can_job(jid)
        sid = job.get("session_id")
        if not sid:
            raise ValueError("Không còn phiên làm kế hoạch, bấm Chạy lại từ đầu")
        sua = {"hook1": str(data.get("hook1") or "").strip()[:60] if data.get("hook1") is not None else None,
               "hook2": str(data.get("hook2") or "").strip()[:60] if data.get("hook2") is not None else None,
               "ghi_chu": str(data.get("ghi_chu") or "").strip()[:2000]}
        v = job_view(jid, ev_on=False) or {}
        chon = data.get("chon") if isinstance(data.get("chon"), dict) else {}
        tl = []
        for i, q in enumerate(v.get("hoi") or []):   # câu Claude hỏi lúc làm kế hoạch: trả lời đi kèm lúc duyệt
            k = str(chon.get(str(i), "0"))
            if k.isdigit() and 0 < int(k) < len(q["opts"]):
                tl.append((q["q"], q["opts"][int(k)]))
        if v.get("hoi"):
            job.setdefault("da_tra_loi", {})[str(v.get("hoi_luot"))] = {str(a): str(b) for a, b in chon.items()}
        sua["tra_loi"] = tl
        job.setdefault("duyet", []).append(dict(sua, t=now()))
        prompt = build_prompt_duyet(job, sua)
        if ban():
            xep_hang(job, "duyet", prompt, sid, "Dựng theo kế hoạch")
            return {"ok": True, "cho": True}
        start_run(job, prompt, "duyet", sid)
        return {"ok": True}


def fix_job(jid, data):
    with LOCK:
        job, st = _can_job(jid)
        text = str(data.get("text") or "").strip()[:4000]
        if not text:
            raise ValueError("Chưa ghi cần sửa gì")
        sid = job.get("session_id")
        resumed = bool(sid) and data.get("moi") is not True
        job.setdefault("sua", []).append({"t": now(), "text": text})
        prompt, label = build_prompt_sua(job, text, resumed), "Sửa: " + short(text, 50)
        if ban():
            xep_hang(job, "sua", prompt, sid if resumed else None, label)
            return {"ok": True, "cho": True}
        start_run(job, prompt, "sua", sid if resumed else None, label)
        return {"ok": True}


def tra_loi_job(jid, data):
    with LOCK:
        v = job_view(jid)
        if not v:
            raise ValueError("Không thấy video này")
        job, hoi = load_job(jid), v.get("hoi") or []
        if job.get("status") in ("dang-chay", "cho"):
            raise ValueError("Video đang chạy / xếp hàng, chờ xong rồi trả lời")
        if not hoi:
            raise ValueError("Không còn câu hỏi nào")
        if v.get("giai_doan") == "cho_duyet":
            raise ValueError("Kế hoạch đang chờ duyệt: chọn câu trả lời rồi bấm Dựng theo kế hoạch")
        chon = data.get("chon") if isinstance(data.get("chon"), dict) else {}
        chon = {str(k): str(x) for k, x in chon.items()}
        job.setdefault("da_tra_loi", {})[str(v.get("hoi_luot"))] = chon
        if not any(c != "0" for c in chon.values()):
            save_job(job)
            return {"ok": True, "chay": False}
        prompt = build_prompt_tra_loi(job, hoi, chon)
        if ban():
            xep_hang(job, "tra_loi", prompt, job.get("session_id"), "Anh trả lời câu hỏi")
            return {"ok": True, "chay": True, "cho": True}
        start_run(job, prompt, "sua", job.get("session_id"), "Anh trả lời câu hỏi")
        return {"ok": True, "chay": True}


def chay_lai(jid, data):
    with LOCK:
        job, st = _can_job(jid, cho_chay=True)
        STATE.pop(jid, None)
        job.pop("loi_chay", None)
        sid = job.get("session_id")
        if sid and job.get("runs"):
            err = read_text(os.path.join(job_dir(jid), "stderr-%d.txt" % job["runs"][-1]["n"]))[-2000:]
            if "No conversation found" in err:   # phiên cũ mất (đổi tài khoản / xoá lịch sử): làm lại từ đầu
                sid = None
                job.pop("session_id", None)
        tiep = bool(sid) and data.get("tiep") is not False and bool(job.get("runs"))
        prompt = fill(read_prompt("chay-tiep.txt"), _du_lieu(job)) if tiep else None
        if ban():
            xep_hang(job, "tiep" if tiep else "dung", prompt, sid if tiep else None, "Chạy tiếp" if tiep else None)
            return {"ok": True, "cho": True}
        job.pop("cho_lam", None)
        if tiep:
            start_run(job, prompt, "tiep", sid)
        else:
            start_run(job, build_prompt_dung(job), "dung")
        return {"ok": True}


def stop_job(jid):
    with LOCK:
        job = load_job(jid)
        if not job:
            return job
        if job.get("status") == "cho":   # đang xếp hàng: bỏ khỏi hàng, video về trạng thái trước khi xếp
            truoc = (job.pop("cho_lam", None) or {}).get("truoc")
            job["status"] = truoc if truoc in ("xong", "loi", "dung") else "dung"
            job.pop("cho_luc", None)
            save_job(job)
            return job
        if job.get("status") != "dang-chay":
            return job
        job["stop_req"] = True
        save_job(job)
        last = job["runs"][-1]
    if pid_alive(last.get("pid"), last.get("started")):
        kill_tree(last.get("pid"))
    time.sleep(0.8)
    parse_job(jid)
    return load_job(jid)


# ---------------------------------------------------------------- xem video
def _final(st):
    for r in reversed(st["results"]):
        if r["ok"] and r["text"].strip():
            return r
    return None


def _chuoi(v, n=4000):
    """Giá trị Claude ghi (có thể là chuỗi, danh sách, số, null) -> chuỗi."""
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        v = " ".join(_chuoi(x) for x in v if x is not None)
    elif isinstance(v, dict):
        v = " · ".join("%s: %s" % (k, _chuoi(x)) for k, x in v.items())
    return str(v)[:n]


def _so(v):
    try:
        x = float(v)
        return x if x == x and abs(x) < 1e7 else None
    except (TypeError, ValueError):
        return None


def _file_co(v):
    return v if isinstance(v, str) and v and os.path.isfile(v) else ""


def ket_qua(job):
    """ket-qua.json Claude ghi -> dạng chắc chắn cho UI (sai kiểu thì bỏ trường đó, không làm hỏng app)."""
    f = thu_muc_video(job)
    raw = read_json(os.path.join(f, "ket-qua.json")) if f else None
    if not isinstance(raw, dict):
        return None
    kt = raw.get("kieu_ten")
    kq = {"mp4": raw.get("mp4") if isinstance(raw.get("mp4"), str) else "",
          "prproj": _file_co(raw.get("prproj")), "khung_dau": _file_co(raw.get("khung_dau")), "to_duyet": _file_co(raw.get("to_duyet")),
          "kieu_ten": kt if isinstance(kt, (str, list, dict)) else "", "giay": _so(raw.get("giay")),
          "duyet": _chuoi(raw.get("duyet"), 600), "caption": _chuoi(raw.get("caption"), 2000),
          "hashtag": _chuoi(raw.get("hashtag"), 600), "ghi_chu": _chuoi(raw.get("ghi_chu"), 2000)}
    kq["co_mp4"] = bool(kq["mp4"]) and os.path.isfile(kq["mp4"])
    kq["sua_tay"] = os.path.isfile(os.path.join(f, "lam", "ke-hoach.json"))
    try:
        kq["mt"] = os.path.getmtime(os.path.join(f, "ket-qua.json"))
    except OSError:
        pass
    return kq


def chuan_ke_hoach(k):
    """ke-hoach-xem.json -> dạng chắc chắn cho UI."""
    if not isinstance(k, dict):
        return None
    hk = k.get("hook")
    hk = [hk, ""] if isinstance(hk, str) else hk if isinstance(hk, list) else []
    hk = [_chuoi(x, 120) for x in hk[:2]] + [""] * (2 - len(hk[:2]))
    canh = []
    for c in (k.get("canh") if isinstance(k.get("canh"), list) else [])[:80]:
        if isinstance(c, dict):
            canh.append({"clip": _chuoi(c.get("clip"), 400), "tu": _so(c.get("tu")), "den": _so(c.get("den")), "mo_ta": _chuoi(c.get("mo_ta"), 300)})
    bo = k.get("bo")
    bo = [bo] if isinstance(bo, str) else bo if isinstance(bo, list) else []
    kt = k.get("kieu_ten")
    return {"tong_giay": _so(k.get("tong_giay")), "kieu_ten": kt if isinstance(kt, (str, list, dict)) else "", "hook": hk,
            "ket": _chuoi(k.get("ket"), 400), "canh": canh, "bo": [_chuoi(x, 300) for x in bo[:40]], "ghi_chu": _chuoi(k.get("ghi_chu"), 2000)}


def giai_doan(job):
    """Trạng thái hiện cho anh (danh sách + trang video dùng chung): cho | dang-chay | cho_duyet | xong | loi | dung | moi."""
    s = job.get("status")
    last = (job.get("runs") or [{}])[-1].get("n")
    if s == "xong" and last and job.get("cho_duyet_luot") == last:
        return "cho_duyet"
    if s == "xong" and last and not job.get("mp4_luot") and not (ket_qua(job) or {}).get("mp4"):
        return "loi"   # Claude báo xong mà chưa có video nào: cho anh Chạy tiếp
    return s


def job_view(jid, since=0, ev_on=True):
    job, st = parse_job(jid)
    if not job:
        return None
    with LOCK:
        n_ev = len(st["events"])
        ev = st["events"][since:] if ev_on else []
        live = ""
        if job.get("status") == "dang-chay":
            for e in reversed(st["events"][-80:]):
                if e.get("k") == "text" and not e.get("s"):
                    live = short(e.get("x") or "", 400)
                    break
        tasks = [dict(id=k, **st["tasks"][k]) for k in st["task_order"] if k in st["tasks"]]
        last_n = (job.get("runs") or [{}])[-1].get("n")
        if st.get("task_run") is not None and st.get("task_run") != last_n:
            tasks = []
        fr = _final(st)
        cost = sum((r.get("cost") or 0) for r in st["results"])
    final_raw = fr["text"] if fr else ""
    dau = doc_dau(final_raw)
    run_hoi = fr["run"] if fr else None
    hoi, final = tach_hoi(bo_dau_dong(final_raw))
    if hoi and (job.get("da_tra_loi") or {}).get(str(run_hoi)):
        hoi = []
    run = job["runs"][-1] if job.get("runs") else None
    # kế hoạch chờ duyệt: chỉ khi câu cuối của LƯỢT CUỐI có CHO_DUYET=
    gd = giai_doan(job)
    ke_hoach = None
    if job.get("status") == "xong" and run and run_hoi == run["n"] and dau.get("CHO_DUYET"):
        gd = "cho_duyet"
        p = dau["CHO_DUYET"] if allowed_path(dau["CHO_DUYET"]) else ""
        ke_hoach = chuan_ke_hoach((read_json(p) if p else None) or read_json(os.path.join(thu_muc_video(job), "ke-hoach-xem.json")))
        with LOCK:
            jj = load_job(jid)
            if jj and jj.get("cho_duyet_luot") != run["n"]:
                jj["cho_duyet_luot"] = run["n"]
                save_job(jj)
    kq = ket_qua(job)
    if gd == "xong" and dau.get("MP4") and (not kq or not kq.get("mp4")):
        kq = dict(kq or {}, mp4=dau["MP4"], co_mp4=os.path.isfile(dau["MP4"]))
        kq["mt"] = kq.get("mt") or (run or {}).get("ended")
    ly_do = ""
    if job.get("status") in ("loi", "dung"):
        with LOCK:
            for e in reversed(st["events"]):
                if e["k"] == "error" and (not run or e.get("r") == run["n"]):
                    ly_do = re.sub(r"^Claude dừng giữa chừng\.\s*", "", e["x"]) or e["x"]
                    break
        if not ly_do and job.get("status") == "loi" and run:
            err = read_text(os.path.join(job_dir(jid), "stderr-%d.txt" % run["n"]))[-800:]
            if err.strip():
                ly_do = short(explain_err(err), 300)
        if not ly_do and job.get("loi_chay"):
            ly_do = job["loi_chay"]
    if gd == "loi" and job.get("status") == "xong" and not ly_do:
        ly_do = "Claude báo xong mà chưa có video. Bấm Chạy tiếp để Claude làm nốt."
    if dau.get("LOI") and job.get("status") == "xong" and run and run_hoi == run["n"]:   # lượt cũ (trước bản sửa server)
        gd, ly_do = "loi", dau["LOI"]
    cl = job.get("cho_lam") or {}
    return {
        "ly_do": ly_do, "giai_doan": gd,
        "job": dict({k: job.get(k) for k in ("id", "don", "status", "created", "thu_muc_video", "session_id", "sua", "duyet", "model", "cho_luc")},
                    cho_viec={"kind": cl.get("kind"), "ten": VIEC.get(cl.get("kind"), "")} if job.get("status") == "cho" else None),
        "run": run and {"n": run["n"], "kind": run["kind"], "started": run["started"], "ended": run.get("ended"), "label": run.get("label")},
        "runs": len(job.get("runs", [])),
        "run_list": [{"n": r["n"], "kind": r["kind"], "label": r.get("label") or r["kind"], "started": r["started"], "ended": r.get("ended"),
                      "ket_qua": r.get("ket_qua")} for r in job.get("runs", [])],
        "idle": round(now() - st.get("last_new", now())),
        "events": ev, "next": since + len(ev) if ev_on else n_ev, "tasks": tasks, "gen": st.get("gen"),
        "final_live": live, "final": final, "hoi": hoi, "hoi_luot": run_hoi, "ke_hoach": ke_hoach, "ket_qua": kq,
        "chi_phi": round(cost, 2), "now": now(),
    }


def list_jobs():
    out = []
    if not os.path.isdir(JOBS):
        return out
    for jid in sorted(os.listdir(JOBS), reverse=True)[:200]:
        try:
            job = read_json(os.path.join(JOBS, jid, "job.json"))
            if not isinstance(job, dict) or not job.get("id"):
                continue
            if job.get("status") == "dang-chay":
                try:
                    job, _ = parse_job(jid)
                except Exception:
                    pass
            don = job.get("don") or {}
            lr = (job.get("runs") or [{}])[-1]
            gd = giai_doan(job)
            kq = ket_qua(job) if gd in ("xong", "loi", "dung", "cho") else None   # video đã có bản dựng (kể cả đang sửa)
            out.append({
                "id": jid, "ten": don.get("ten") or don.get("slug") or "Video", "loai": don.get("loai"), "duong": don.get("duong"),
                "do_dai": don.get("do_dai"), "status": job.get("status"), "giai_doan": gd, "created": job.get("created"),
                "started": lr.get("started"), "ended": lr.get("ended"), "xem": job.get("da_xem"), "cho_luc": job.get("cho_luc"),
                "viec": VIEC.get((job.get("cho_lam") or {}).get("kind"), "") if gd == "cho" else "",
                "anh": (kq or {}).get("khung_dau") or "", "n_luot": len(job.get("runs") or []),
            })
        except Exception:
            log("list_jobs %s: %s" % (jid, traceback.format_exc()))
    return out


def danh_dau_xem(jid):
    with LOCK:
        job = load_job(jid)
        if job and not job.get("da_xem") and job.get("status") in ("xong", "loi", "dung"):
            job["da_xem"] = now()
            save_job(job)
    return {"ok": True}


def allowed_path(p, video=False):
    try:
        rp = os.path.realpath(p)
    except Exception:
        return False
    roots = [JOBS, CACHE, CFG.get("thu_muc_ra") or ""]
    if video:
        roots.append(CFG.get("thu_muc_clip") or "")
    for r in roots:
        if r and os.path.isdir(r) and trong(rp, r):
            return True
    if video:
        with LOCK:
            if norm(os.path.dirname(rp)) in LISTED:
                return True
        for jid in (os.listdir(JOBS) if os.path.isdir(JOBS) else []):
            tm = ((read_json(os.path.join(JOBS, jid, "job.json")) or {}).get("don") or {}).get("thu_muc")
            if tm and trong(rp, tm):
                return True
        if ST.cho_xem(rp):
            return True
    return False


# ---------------------------------------------------------------- báo Telegram khi xong (chỉ khi config có token + chat)
BAT_DAU = time.time()


def tg_gui(text, anh=None):
    tok, chat = CFG.get("telegram_token"), CFG.get("telegram_chat")
    if not (tok and chat):
        return False
    import urllib.request
    try:
        if anh and os.path.isfile(anh) and os.path.getsize(anh) < 9.5e6:
            bd = "----poly" + uuid.uuid4().hex
            parts = []
            for k, v in (("chat_id", str(chat)), ("caption", short(text, 1000))):
                parts.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (bd, k, v)).encode("utf-8"))
            with open(anh, "rb") as f:
                parts.append(("--%s\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"anh.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n" % bd).encode("utf-8") + f.read() + b"\r\n")
            parts.append(("--%s--\r\n" % bd).encode("utf-8"))
            req = urllib.request.Request("https://api.telegram.org/bot%s/sendPhoto" % tok, data=b"".join(parts),
                                         headers={"Content-Type": "multipart/form-data; boundary=" + bd})
        else:
            req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % tok,
                                         data=json.dumps({"chat_id": chat, "text": text}).encode("utf-8"),
                                         headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=60).read()
        return True
    except Exception as e:
        log("bao telegram loi: %s" % e)
        return False


def theo_doi():
    while True:
        time.sleep(30)
        if not (CFG.get("telegram_token") and CFG.get("telegram_chat")):
            continue
        try:
            for jid in sorted(os.listdir(JOBS), reverse=True)[:20]:
                job = read_json(os.path.join(JOBS, jid, "job.json"))
                if not job or not job.get("runs") or job.get("status") not in ("xong", "loi"):
                    continue
                run = job["runs"][-1]
                if run.get("da_bao") or (run.get("ended") or 0) < BAT_DAU - 120:
                    continue
                with LOCK:
                    j = load_job(jid)
                    j["runs"][-1]["da_bao"] = now()
                    save_job(j)
                v = job_view(jid) or {}
                ten = (job.get("don") or {}).get("ten") or "video"
                phut = max(1, round(((run.get("ended") or now()) - run.get("started", now())) / 60))
                if v.get("giai_doan") == "cho_duyet":
                    tg_gui("📝 %s: kế hoạch xong sau %d phút, chờ anh duyệt trong app POLY Cut." % (ten, phut))
                elif v.get("giai_doan") == "xong":
                    kq = v.get("ket_qua") or {}
                    tg_gui("✅ Xong video: %s (%d phút)%s" % (ten, phut, ("\nDuyệt: " + kq["duyet"]) if kq.get("duyet") else ""), kq.get("khung_dau"))
                else:
                    tg_gui("⚠️ %s dừng giữa chừng sau %d phút: %s" % (ten, phut, short(v.get("ly_do") or "không rõ lý do", 300)))
        except Exception:
            log(traceback.format_exc())


# ---------------------------------------------------------------- HTTP
# /file chỉ trả các loại này (không html / svg: không chạy được trang lạ trong app)
FILE_XEM = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif",
            ".mp4": "video/mp4", ".m4v": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
            ".mp3": "audio/mpeg", ".wav": "audio/wav", ".json": "application/json; charset=utf-8", ".txt": "text/plain; charset=utf-8", ".log": "text/plain; charset=utf-8"}


class H(BaseHTTPRequestHandler):
    server_version = "PolyDungVideo/1.0"

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        try:
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # 4/11: trình duyệt bỏ yêu cầu giữa chừng (F5, ảnh cảnh cuộn qua, đổi video): không phải lỗi app -> không ghi
            # traceback "WinError 10053" vào app-log.txt (nhật ký máy tiệm đầy dòng này, che lỗi thật)
            self.close_connection = True

    def send_file(self, p, ctype):
        """Gửi file có hỗ trợ Range (thẻ <video> tua được)."""
        size = os.path.getsize(p)
        rng = self.headers.get("Range")
        a, b = 0, size - 1
        code = 200
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    a = int(m.group(1))
                    b = int(m.group(2)) if m.group(2) else size - 1
                elif m.group(2):
                    a = max(0, size - int(m.group(2)))
                b = min(b, size - 1)
                if a > b or a >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % size)
                    self.end_headers()
                    return
                code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(b - a + 1))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "sandbox")
        if code == 206:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (a, b, size))
        self.end_headers()
        with open(p, "rb") as f:
            f.seek(a)
            left = b - a + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    return
                left -= len(chunk)

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > 20 * 1024 * 1024:
            raise ValueError("Gửi quá lớn")
        raw = self.rfile.read(n) if n else b"{}"
        try:
            d = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            raise ValueError("Dữ liệu gửi lên sai dạng")
        if not isinstance(d, dict):
            raise ValueError("Dữ liệu gửi lên sai dạng")
        return d

    def local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self.send(403, {"err": "chỉ mở trên máy này"})
            return False
        origin = self.headers.get("Origin")
        if origin and not re.match(r"^http://(127\.0\.0\.1|localhost):%d$" % int(CFG["port"]), origin):
            self.send(403, {"err": "origin lạ"})
            return False
        return True

    def do_GET(self):
        if not self.local_only():
            return
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if ST.get(self, u, q) or TI.get(self, u, q):
                return
            if u.path in ("/", "/index.html"):
                with open(os.path.join(UI, "index.html"), "rb") as f:
                    return self.send(200, f.read(), "text/html; charset=utf-8")
            if u.path.startswith("/ui/"):
                fp = os.path.normpath(os.path.join(UI, unquote(u.path[4:])))
                if not fp.startswith(UI) or not os.path.isfile(fp):
                    return self.send(404, {"err": "không có"})
                with open(fp, "rb") as f:
                    return self.send(200, f.read(), mimetypes.guess_type(fp)[0] or "application/octet-stream", {"Cache-Control": "max-age=3600"})
            if u.path == "/api/ping":
                return self.send(200, {"ok": True, "app": APP_MA, "ten": APP_TEN})
            if u.path == "/api/health":
                ci = claude_info(force=q.get("force") == ["1"])
                return self.send(200, {
                    "claude": ci.get("cmd") and " ".join(ci["cmd"]), "version": ci.get("version"),
                    "err": ci.get("err"), "login": ci.get("login"), "tk": ci.get("tk") or {},
                    "san_sang": san_sang(), "premiere": premiere_nhip(),
                    "thu_muc_clip": CFG.get("thu_muc_clip"), "thu_muc_ra": CFG.get("thu_muc_ra"), "win": IS_WIN,
                    "giong": giong_ds(),
                })
            if u.path == "/api/premiere":
                return self.send(200, premiere_nhip())
            if u.path == "/api/jobs":
                try:
                    uiv = int(os.path.getmtime(os.path.join(UI, "index.html")))
                except OSError:
                    uiv = 0
                hd = hang_tam_dung() if co_hang_cho() else None
                return self.send(200, {"jobs": list_jobs(), "ui": uiv, "premiere": premiere_nhip(), "hang_dung": hd})
            if u.path == "/api/clip":
                return self.send(200, list_clips((q.get("thu_muc") or [""])[0]))
            if u.path == "/api/thu-muc":
                return self.send(200, duyet_thu_muc((q.get("p") or [""])[0]))
            if u.path == "/api/thumb":
                p = (q.get("p") or [""])[0]
                if not allowed_path(p, video=True):
                    return self.send(403, {"err": "không xem được clip này"})
                fp = thumb(p, (q.get("t") or ["1"])[0], (q.get("h") or ["360"])[0])
                with open(fp, "rb") as f:
                    return self.send(200, f.read(), "image/jpeg", {"Cache-Control": "max-age=86400"})
            m = re.fullmatch(r"/api/job/([\w-]+)", u.path)
            if m:
                try:
                    since = max(0, int((q.get("since") or ["0"])[0]))
                except ValueError:
                    since = 0
                v = job_view(m.group(1), since, (q.get("ev") or ["1"])[0] != "0")
                return self.send(200 if v else 404, v or {"err": "không thấy video này"})
            if u.path == "/file":
                p = (q.get("p") or [""])[0]
                ext = os.path.splitext(p)[1].lower()
                ctype = FILE_XEM.get(ext)
                if not ctype:
                    return self.send(403, {"err": "loại file không cho xem"})
                if not allowed_path(p, video=ctype.startswith("video/")) or not os.path.isfile(p):
                    return self.send(404, {"err": "không mở được file"})
                return self.send_file(p, ctype)
            m = re.fullmatch(r"/api/job/([\w-]+)/log", u.path)
            if m:
                d = job_dir(m.group(1))
                if not os.path.isdir(d):
                    return self.send(404, {"err": "không thấy video này"})
                parts = []
                for fn in sorted(os.listdir(d)):
                    if fn.startswith(("stderr-", "prompt-")):
                        parts.append("===== %s =====\n%s" % (fn, read_text(os.path.join(d, fn))[-20000:]))
                return self.send(200, "\n\n".join(parts) or "(trống)", "text/plain; charset=utf-8")
            return self.send(404, {"err": "không có"})
        except ValueError as e:
            return self.send(400, {"err": str(e)})
        except Exception:
            log(traceback.format_exc())
            return self.send(500, {"err": "Có lỗi trong app, chi tiết đã ghi vào app-log.txt. Thử lại, vẫn lỗi thì chụp màn hình gửi Claude."})

    def do_POST(self):
        if not self.local_only():
            return
        u = urlparse(self.path)
        try:
            if u.path == "/api/sua-tay/tha-file/nhan":   # r34: thả clip từ máy vào Sửa tay, thân = nội dung file -> ghi thẳng xuống đĩa từng khúc (tha_file.py)
                import tha_file
                return tha_file.nhan(self, u)
            data = self.body()
            if ST.post(self, u, data) or TI.post(self, u, data):
                return
            if u.path == "/api/tat":
                self.send(200, {"ok": True})
                threading.Timer(0.3, lambda: os._exit(0)).start()
                return
            if u.path == "/api/login" and data.get("doi"):
                return self.send(200, doi_tai_khoan())
            if u.path == "/api/login":
                cmd = resolve_claude()
                if not cmd:
                    raise ValueError("Không tìm thấy Claude Code")
                if IS_WIN:
                    comspec = os.environ.get("COMSPEC", "cmd.exe")
                    subprocess.Popen([comspec, "/c", "start", "Dang nhap Claude Code", comspec, "/k"] + cmd + ["auth", "login"],
                                     creationflags=CREATE_NO_WINDOW)
                _CLAUDE["t"] = 0
                return self.send(200, {"ok": True})
            if u.path == "/api/chon-thu-muc":
                return self.send(200, chon_thu_muc(data.get("tu") or ""))
            if u.path == "/api/giong-thu":
                return self.send(200, giong_thu(data))
            if u.path == "/api/run":
                job = create_job(data)
                return self.send(200, {"id": job["id"], "cho": job.get("status") == "cho"})
            m = re.fullmatch(r"/api/job/([\w-]+)/(duyet|sua|tra-loi|dung|chay-lai|mo|mo-premiere|xoa|xem)", u.path)
            if m:
                jid, act = m.groups()
                if act == "duyet":
                    return self.send(200, duyet_job(jid, data))
                if act == "sua":
                    return self.send(200, fix_job(jid, data))
                if act == "tra-loi":
                    return self.send(200, tra_loi_job(jid, data))
                if act == "dung":
                    stop_job(jid)
                    return self.send(200, {"ok": True})
                if act == "chay-lai":
                    return self.send(200, chay_lai(jid, data))
                if act == "xem":
                    return self.send(200, danh_dau_xem(jid))
                if act in ("mo", "mo-premiere"):
                    job = load_job(jid)
                    if not job:
                        raise ValueError("Không thấy video này")
                    if act == "mo-premiere":
                        kq = ket_qua(job) or {}
                        p = kq.get("prproj") or ""
                        if not p or not os.path.isfile(p):
                            raise ValueError("Video này chưa có project Premiere")
                    else:
                        p = data.get("p") or thu_muc_video(job)
                        if p and os.path.isfile(p):
                            p = os.path.dirname(p)
                        if (not p or not os.path.isdir(p)) and not data.get("clip"):
                            p = thu_muc_video(job)
                        if not p or not os.path.isdir(p):
                            p = (job.get("don") or {}).get("thu_muc") if data.get("clip") else job_dir(jid)
                    if not (allowed_path(p) or trong(p, (job.get("don") or {}).get("thu_muc") or "")):
                        raise ValueError("Không mở được thư mục này")
                    if IS_WIN:
                        os.startfile(p)  # noqa
                    return self.send(200, {"ok": True})
                if act == "xoa":
                    job = load_job(jid)
                    if not job:
                        raise ValueError("Không thấy video này")
                    if job.get("status") == "dang-chay":
                        raise ValueError("Video đang chạy, bấm Dừng trước")
                    dst = os.path.join(APP, "_to_delete")
                    os.makedirs(dst, exist_ok=True)
                    shutil.move(job_dir(jid), os.path.join(dst, jid))   # chỉ bỏ khỏi danh sách, video vẫn còn trong thư mục
                    with LOCK:
                        STATE.pop(jid, None)
                    return self.send(200, {"ok": True})
            return self.send(404, {"err": "không có"})
        except ValueError as e:
            return self.send(400, {"err": str(e)})
        except Exception:
            log(traceback.format_exc())
            return self.send(500, {"err": "Có lỗi trong app, chi tiết đã ghi vào app-log.txt. Thử lại, vẫn lỗi thì chụp màn hình gửi Claude."})


class Srv(ThreadingHTTPServer):
    # Windows: SO_REUSEADDR cho nhieu ban cung nghe 1 cong -> chi cho 1 ban duy nhat
    allow_reuse_address = not IS_WIN

    def server_bind(self):
        if IS_WIN:
            import socket
            self.socket.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_EXCLUSIVEADDRUSE", -5), 1)
        super().server_bind()


def main():
    ST.gan(sys.modules[__name__])
    os.makedirs(JOBS, exist_ok=True)
    port = int(CFG.get("port") or 8790)
    try:
        srv = Srv(("127.0.0.1", port), H)
    except OSError:
        print("App da chay san o cong %d" % port)
        return
    srv.daemon_threads = True
    log("mo app cong %d" % port)
    print("POLY Cut: http://127.0.0.1:%d" % port)
    threading.Thread(target=claude_info, daemon=True).start()
    threading.Thread(target=hang_doi, daemon=True).start()
    threading.Thread(target=theo_doi, daemon=True).start()
    import card as CARD   # 10/11: dò card đồ hoạ của máy ở luồng nền (mở app không chờ), xem card.py
    CARD.bat_dau()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
