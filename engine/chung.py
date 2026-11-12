#!/usr/bin/env python3
"""Phần dùng chung của bản chạy TẠI MÁY tiệm (Windows, Claude Code chạy cục bộ) — mọi script trong engine import file này.

Tìm công cụ (theo thứ tự):
  ffmpeg / ffprobe   env POLY_FFMPEG_DIR  ->  <engine>/bin/  ->  PATH
  font               env POLY_FONT_DIR    ->  <engine>/fonts/
  máy nghe sherpa    env POLY_MO_HINH     ->  <engine>/mo-hinh/sherpa-onnx-zipformer-vi-int8-2025-04-20
  Poly Bridge        env POLY_PREMIERE_DIR ->  E:\\Tool\\poly-premiere   (lenh\\ + ket-qua\\)
  thư mục video      env POLY_THU_MUC_RA (app) / POLY_EDIT_DIR ->  E:\\Tool\\poly-edit
Lúc import: đặt stdout / stderr UTF-8 (Windows để mặc định cp1252 khi chạy qua ống của Claude Code -> lỗi chữ có dấu),
đưa thư mục ffmpeg lên đầu PATH, đặt FONTCONFIG_FILE (bản ffmpeg Windows không có fonts.conf -> drawtext / libass
không tìm được font mặc định).
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LA_WIN = os.name == "nt"
TEN_MO_HINH = "sherpa-onnx-zipformer-vi-int8-2025-04-20"


def dat_utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


dat_utf8()


def _env_dir(k, mac_dinh):
    v = (os.environ.get(k) or "").strip().strip('"')
    return os.path.abspath(v) if v else mac_dinh


def _tim_exe(ten):
    exe = ten + (".exe" if LA_WIN else "")
    for d in (os.environ.get("POLY_FFMPEG_DIR"), os.path.join(HERE, "bin")):
        if d:
            p = os.path.join(d.strip().strip('"'), exe)
            if os.path.isfile(p):
                return os.path.abspath(p)
    return shutil.which(ten) or ten


FFMPEG = _tim_exe("ffmpeg")
FFPROBE = _tim_exe("ffprobe")
FONT_DIR = _env_dir("POLY_FONT_DIR", os.path.join(HERE, "fonts"))
MO_HINH = _env_dir("POLY_MO_HINH", os.path.join(HERE, "mo-hinh", TEN_MO_HINH))
PREMIERE_DIR = _env_dir("POLY_PREMIERE_DIR", "E:\\Tool\\poly-premiere" if LA_WIN else os.path.join(HERE, "_premiere"))
EDIT_DIR = _env_dir("POLY_THU_MUC_RA", _env_dir("POLY_EDIT_DIR", "E:\\Tool\\poly-edit" if LA_WIN else os.path.join(HERE, "_poly-edit")))
KQ_DIR = os.path.join(PREMIERE_DIR, "ket-qua")
LENH_DIR = os.path.join(PREMIERE_DIR, "lenh")

if os.path.isabs(FFMPEG):  # lệnh con nào còn gọi "ffmpeg" trần cũng ra đúng bản này
    _d = os.path.dirname(FFMPEG)
    if _d not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")


def co_mo_hinh(d=None):
    d = d or MO_HINH
    try:
        ds = os.listdir(d)
    except OSError:
        return False
    return "tokens.txt" in ds and any(x.startswith("encoder") and x.endswith(".onnx") for x in ds)


def mo_hinh_hoac_none(d=None):
    """Thư mục máy nghe dùng được (tham số, rồi env / mặc định) hoặc None."""
    for x in ([d] if d else []) + [MO_HINH]:
        if x and co_mo_hinh(x):
            return x
    return None


def duong(p):
    """Đường dẫn chuẩn của máy đang chạy (Windows: dấu \\). Không đổi chữ hoa / thường."""
    return os.path.normpath(str(p)) if p else p


def xuoi(p):
    """Đường dẫn kiểu E:/Tool/... (dấu /) — dạng Poly Bridge / Premiere nhận (LENH.md)."""
    return str(p).replace("\\", "/") if p else p


def loc(p):
    """Đường dẫn làm GIÁ TRỊ tùy chọn trong chuỗi filter ffmpeg (vd. result=…, filename=…, fontfile=…), đã bọc nháy.
    2 tầng thoát của ffmpeg: tầng đồ thị bỏ nháy đơn (giữ nguyên \\ trong nháy), tầng tùy chọn tách ở ':' và hiểu \\ là thoát.
    -> 'E\\:/Tool/a b/x.ass': ổ đĩa Windows có ':' phải thoát; nháy đơn trong tên đóng nháy, thoát, mở lại."""
    s = str(p).replace("\\", "/")
    s = s.replace(":", "\\:").replace("'", "\\'\\''")
    return "'" + s + "'"


FONT_LOC = ("BeVietnamPro-Bold.ttf", "BeVietnamPro-Black.ttf", "BeVietnamPro-ExtraBold.ttf")


def font_drawtext():
    """'fontfile=…:' cho drawtext của ffmpeg (bản Windows không có font mặc định). Không có font -> '' (để như cũ)."""
    for f in FONT_LOC:
        p = os.path.join(FONT_DIR, f)
        if os.path.isfile(p):
            return "fontfile=" + loc(p) + ":"
    return ""


def _fontconfig():
    """ffmpeg bản Windows (BtbN) có fontconfig nhưng không kèm fonts.conf -> drawtext không fontfile / libass báo lỗi font.
    Ghi <engine>/_fc/fonts.conf (font của bộ + C:/Windows/Fonts) và đặt FONTCONFIG_FILE cho mọi lệnh ffmpeg con."""
    if os.environ.get("FONTCONFIG_FILE"):
        return
    d = os.path.join(HERE, "_fc")
    dirs = [FONT_DIR]
    if LA_WIN:
        dirs.append(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))
    xml = ('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
           + "".join(f"  <dir>{xuoi(x)}</dir>\n" for x in dirs if x)
           + f"  <cachedir>{xuoi(os.path.join(d, 'cache'))}</cachedir>\n</fontconfig>\n")
    p = os.path.join(d, "fonts.conf")
    try:
        os.makedirs(d, exist_ok=True)
        cu = None
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                cu = f.read()
        if cu != xml:
            with open(p, "w", encoding="utf-8") as f:
                f.write(xml)
        os.environ["FONTCONFIG_FILE"] = p
    except OSError:
        pass


_fontconfig()


def trong(goc, p):
    """p nằm trong (hoặc là) thư mục goc? So không phân biệt hoa / thường trên Windows."""
    a, b = os.path.abspath(goc), os.path.abspath(p)
    if LA_WIN:
        a, b = a.lower(), b.lower()
    try:
        return os.path.commonpath([a, b]) == a
    except ValueError:  # khác ổ đĩa
        return False
