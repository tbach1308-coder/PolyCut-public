# -*- coding: utf-8 -*-
"""POLY Cut — dùng card đồ hoạ của máy để đọc clip và xuất video (10/11/2026, anh: "poly sẽ chạy bằng card trên máy để mượt",
"app exe sẽ tự dò và sài card máy được cài").

- Mở app: luồng nền dò (không chặn mở app): tên + driver card (Windows: PowerShell Win32_VideoController, không bật cửa sổ, tối đa
  10s, lỗi thì bỏ qua), rồi engine/ma_hoa.py --json (mã hoá thử + giải mã thử THẬT, nhớ engine/_cache/ma-hoa.json 7 ngày; đổi
  driver / ffmpeg thì dò lại). Máy nào cài app cũng tự dò, không giả định máy tiệm.
- Mặc định Tự động: xuất (sua_tay_may -> dung_may_chu) chạy với POLY_MA_HOA=auto; bản xem nhẹ + ảnh khung giải mã clip bằng card.
  config.json "ma_hoa": "cpu" = Tắt (công tắc "Dùng card đồ hoạ" trong hộp Xuất video ghi khoá này).
- Card lỗi giữa chừng: làm lại y lệnh đó bằng CPU (bản xuất / bản xem không mất); lỗi 2 lần trong 7 ngày thì thôi dùng loại đó
  (ghi chung ma-hoa.json với bộ dựng).
- GET /api/sua-tay/card -> trạng thái + dòng chữ cho hộp Xuất; POST {che_do: auto|cpu} ghi config.json; POST {do_lai: 1} dò lại.
Chỉ thư viện chuẩn.
"""
import json
import os
import re
import shutil
import subprocess
import threading
import time

import sua_tay as ST

IS_WIN = os.name == "nt"
NO_WIN = 0x08000000
TAT = ("cpu", "khong", "0", "off", "tat", "false")
CPU_ENC = ("libx264", "libx265")
LOCK = threading.RLock()
TT = {"tt": "chua", "card": []}   # tt: chua | dang_do | xong | loi (che_do cpu: không dò ffmpeg, trang_thai báo "tat")
_HONG = set()                     # loại giải mã bằng card lỗi trong lượt chạy app này (bản xem nhẹ / ảnh khung)
_DANG = {"t": None}
AO = re.compile(r"basic display|basic render|virtual|remote|mirror|parsec|\bidd\b|spacedesk|dummy|sunshine|citrix|vmware|hyper-v|displaylink",
                re.I)   # card ảo (màn hình ảo, điều khiển từ xa): không phải card để dựng
HANG = (("nvenc", "NVIDIA", r"nvidia"), ("cuda", "NVIDIA", r"nvidia"), ("qsv", "Intel", r"intel"), ("amf", "AMD", r"amd|radeon"))
TEN_GM = {"d3d11va": "D3D11", "dxva2": "DXVA2", "cuda": "NVDEC", "qsv": "Intel Quick Sync", "vaapi": "VA-API"}
TEN_MH = {"nvenc": "NVENC", "qsv": "Quick Sync", "amf": "AMF"}


def _S():
    return ST.S


def che_do():
    """auto (mặc định: có card dùng được thì dùng) | cpu (anh tắt)."""
    v = str((_S().CFG.get("ma_hoa") if _S() else "") or "auto").strip().lower()
    return "cpu" if v in TAT else "auto"


def _powershell():
    if IS_WIN:
        p = os.path.join(os.environ.get("SystemRoot") or "C:\\Windows", "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
        return shutil.which("powershell") or (p if os.path.isfile(p) else None)
    return shutil.which("powershell")   # máy khác thường không có -> không có tên card


def ds_card():
    """[{ten, driver}] card đồ hoạ của máy (Windows: Win32_VideoController). Lỗi / không có PowerShell / quá 10s: []."""
    ps = _powershell()
    if not ps:
        return []
    try:
        r = subprocess.run([ps, "-NoProfile", "-NonInteractive", "-Command",
                            "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
                            "Get-CimInstance Win32_VideoController | Select Name,DriverVersion | ConvertTo-Json"],
                           capture_output=True, timeout=10, creationflags=NO_WIN if IS_WIN else 0)
        txt = (r.stdout or b"").decode("utf-8", "replace").strip().lstrip("\ufeff")
        d = json.loads(txt) if txt else []
    except Exception:  # noqa  không có quyền WMI, PowerShell bị chặn, quá giờ: bỏ qua
        return []
    if isinstance(d, dict):
        d = [d]
    out = []
    for x in d if isinstance(d, list) else []:
        if isinstance(x, dict) and str(x.get("Name") or "").strip():
            out.append({"ten": str(x.get("Name")).strip()[:80], "driver": str(x.get("DriverVersion") or "").strip()[:40]})
    return out[:6]


def _la_that(ten):
    return not AO.search(ten or "")


def _tom_tat(d):
    """1 dòng log kết quả dò."""
    gm = d.get("giai_ma") or {}
    td = d.get("tu_dong") or {}
    loi = [k for k, v in sorted((d.get("thu") or {}).items()) if v] + [k for k, v in sorted((gm.get("thu") or {}).items()) if v]
    return "mã hoá %s / %s · giải mã %s (HEVC 10-bit: %s)%s" % (td.get("h264"), td.get("hevc"), td.get("giai_ma") or "CPU",
                                                              gm.get("hevc10") or "không", (" · thử không được: " + ", ".join(loi)) if loi else "")


def _do(ep=False, doc_lai=False):
    """doc_lai: chỉ đọc lại nhớ của bộ dựng (sau lần xuất có card lỗi: loại lỗi 2 lần đã tắt), không hỏi tên card, không dò lại."""
    try:
        card = [] if doc_lai else ds_card()
        with LOCK:
            if card:
                TT["card"] = card
        if che_do() == "cpu":   # anh đã tắt (có thể vì card trục trặc): không chạy thử card
            with LOCK:
                TT.update(tt="chua")
            _S().log("card: đang tắt (config.json \"ma_hoa\": \"cpu\") · card máy: %s" % (", ".join(c["ten"] for c in card) or "không đọc được"))
            return
        e = _S().engine()
        if not os.path.isfile(e["py"]) or not os.path.isfile(os.path.join(e["dir"], "ma_hoa.py")):
            raise RuntimeError("chưa cài bộ dựng")
        cmd = [e["py"], os.path.join(e["dir"], "ma_hoa.py"), "--json"] + (["--do-lai"] if ep and not doc_lai else []) \
            + (["--card=" + json.dumps(card, ensure_ascii=True)] if card else [])
        d = None
        for _ in range(60):   # bộ dựng của 1 lần xuất đang dò (khoá): chờ nó xong rồi đọc nhớ
            r = subprocess.run(cmd, cwd=e["dir"], env=ST.MAY._env(), capture_output=True, timeout=600,
                               creationflags=NO_WIN if IS_WIN else 0)
            dong = [x for x in (r.stdout or b"").decode("utf-8", "replace").splitlines() if x.strip().startswith("{")]
            if r.returncode or not dong:
                raise RuntimeError(((r.stderr or b"").decode("utf-8", "replace") or "không đọc được kết quả")[-300:])
            d = json.loads(dong[-1])
            if not d.get("tam"):
                break
            cmd = [x for x in cmd if x != "--do-lai"]
            time.sleep(3)
        td = d.get("tu_dong") or {}
        with LOCK:
            TT.update(tt="xong", ma_hoa=td.get("h264"), hevc=td.get("hevc"), giai_ma=td.get("giai_ma"),
                      co_mh=d.get("h264"), co_gm=(d.get("giai_ma") or {}).get("hw"),   # dò thấy (trước khi trừ loại lỗi 2 lần)
                      hevc10=(d.get("giai_ma") or {}).get("hevc10"), card=d.get("card") or card or TT.get("card") or [], luc=time.time(),
                      loi="")
        _S().log("card: %s%s · %s" % ("đọc lại sau lần xuất có card lỗi · " if doc_lai else "",
                                     ", ".join("%s (%s)" % (c.get("ten"), c.get("driver")) for c in TT["card"]) or "không đọc được tên card",
                                     _tom_tat(d)))
    except Exception as ex:  # noqa
        if doc_lai:   # đọc lại không được: giữ trạng thái cũ
            return
        with LOCK:
            TT.update(tt="loi", loi=str(ex)[:200])
        try:
            _S().log("card: dò lỗi (xuất bằng CPU): %s" % ex)
        except Exception:  # noqa
            pass
    finally:
        with LOCK:
            _DANG["t"] = None


def bat_dau(ep=False):
    """Dò card ở luồng nền (mở app không phải chờ). Đang dò thì thôi."""
    with LOCK:
        if _DANG["t"]:
            return
        TT["tt"] = "dang_do"
        t = threading.Thread(target=_do, args=(bool(ep),), daemon=True, name="do-card")
        _DANG["t"] = t
    t.start()


def lam_moi():
    """Lần xuất vừa có bước card lỗi (đã làm lại bằng CPU): đọc lại nhớ của bộ dựng ở nền để dòng trạng thái đúng."""
    with LOCK:
        if _DANG["t"] or TT.get("tt") != "xong" or che_do() == "cpu":
            return
        t = threading.Thread(target=_do, kwargs={"doc_lai": True}, daemon=True, name="doc-lai-card")
        _DANG["t"] = t
    t.start()


def giai_ma():
    """Loại -hwaccel cho bản xem nhẹ / ảnh khung (đọc clip gốc), None = CPU. Chưa dò xong / đang tắt / vừa lỗi: CPU."""
    if not _S() or che_do() == "cpu" or str(_S().CFG.get("giai_ma") or "").strip().lower() in TAT:
        return None
    with LOCK:
        hw = TT.get("giai_ma") if TT.get("tt") == "xong" else None
    return hw if hw and hw not in _HONG else None


def vao():
    hw = giai_ma()
    return ["-hwaccel", hw] if hw else []


def bao_loi_gm(hw, viec=""):
    """Đọc clip bằng card lỗi (CPU thì được): lượt chạy app này thôi dùng; ghi chung ma-hoa.json (lỗi 2 lần / 7 ngày: tắt hẳn)."""
    if not hw:
        return
    with LOCK:
        _HONG.add(hw)
    try:
        _S().log("card: đọc clip bằng card (%s) lỗi%s -> đã làm lại bằng CPU" % (hw, (" khi " + viec) if viec else ""))
        import tempfile   # cùng chỗ nhớ với ma_hoa._cache_path(): <engine>/_cache, thư mục engine không ghi được thì %TEMP%/poly-cut
        p = next((x for x in (os.path.join(_S().engine()["dir"], "_cache", "ma-hoa.json"), os.path.join(tempfile.gettempdir(), "poly-cut", "ma-hoa.json"))
                  if os.path.isfile(x) and os.path.getsize(x) > 0), None)
        if not p:
            return
        d = json.load(open(p, encoding="utf-8"))
        ld = d.setdefault("loi_dung", {})
        ld["gm:" + hw] = ld.get("gm:" + hw, 0) + 1
        tam = p + ".%d.tmp" % os.getpid()
        json.dump(d, open(tam, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.replace(tam, p)
    except Exception:  # noqa  không có file nhớ / đang bị giữ: lượt này vẫn thôi dùng
        pass


def _hang(ma):
    for k, ten, mau in HANG:
        if k in (ma or ""):
            return ten, mau
    return None, None


def _ten_card(ma, ds):
    """Tên card cho 1 bộ mã hoá / giải mã: theo hãng (nvenc -> tên có NVIDIA…); d3d11va / dxva2 / vaapi: card duy nhất của máy."""
    ten, mau = _hang(ma)
    if mau:
        for x in ds:
            if re.search(mau, x, re.I):
                return "card " + x
        return "card " + ten
    if len(ds) == 1:
        return "card " + ds[0]
    return "card đồ hoạ"


def trang_thai():
    with LOCK:
        t = dict(TT)
        hong = set(_HONG)
    cd = che_do()
    card = [c for c in t.get("card") or [] if isinstance(c, dict)]
    that = [c["ten"] for c in card if _la_that(c.get("ten"))] or [c["ten"] for c in card]
    enc, hevc, hw = t.get("ma_hoa"), t.get("hevc"), t.get("giai_ma")
    if hw in hong:
        hw = None
    dung_mh = bool(enc and enc not in CPU_ENC)
    if cd == "cpu":
        tt, dong = "tat", "Xuất bằng CPU (đang tắt card đồ hoạ)"
    elif t.get("tt") in ("chua", "dang_do"):
        tt, dong = "dang_do", "Đang dò card…"
    elif t.get("tt") == "loi":
        tt, dong = "loi", "Xuất bằng CPU (chưa dò được card)"
    elif dung_mh:
        tt, dong = "card", "Xuất bằng " + _ten_card(enc, that)
    elif hw:
        tt, dong = "card", "Xuất bằng CPU, đọc clip bằng " + _ten_card(hw, that)
    else:
        tt, dong = "cpu", "Xuất bằng CPU (máy không có card dùng được)"
    ct = []
    hien = [c for c in card if _la_that(c.get("ten"))] or card   # card ảo (màn hình ảo, điều khiển từ xa) không kể
    if hien:
        ct.append("Máy này: " + ", ".join(c["ten"] + ((" (driver " + c["driver"] + ")") if c.get("driver") else "") for c in hien) + ".")
    if tt == "card":
        hm = _hang(enc)[0] if dung_mh else None
        ct.append("Mã hoá video: " + ((TEN_MH.get(next((k for k in TEN_MH if k in enc), ""), enc) + (" (card %s)" % hm if hm else ""))
                                       if dung_mh else "CPU") + ".")
        ct.append("Đọc clip: " + (TEN_GM.get(hw, hw) + (", đọc được clip HEVC 10-bit của iPhone" if t.get("hevc10") == hw else "")
                                   if hw else "CPU") + ".")
    if tt in ("card", "cpu") and ((t.get("co_mh") not in (None,) + CPU_ENC and not dung_mh) or (t.get("co_gm") and not hw)):
        ct.append("Card lỗi lúc xuất gần đây nên phần đó tạm dùng CPU; app tự thử lại card trong vòng 7 ngày, hoặc ngay khi cập nhật driver.")
    elif tt == "cpu":
        ct.append("Đã thử mã hoá và đọc clip bằng card: không dùng được, app dùng CPU.")
    elif tt == "loi":
        ct.append("Lỗi: " + str(t.get("loi") or "") + ".")
    return {"che_do": cd, "tt": tt, "dong": dong, "chi_tiet": " ".join(ct), "card": card, "ma_hoa": enc, "hevc": hevc,
            "giai_ma": hw, "hevc10": t.get("hevc10"), "dang_do": t.get("tt") == "dang_do", "luc": t.get("luc")}


def ghi_che_do(v):
    """Công tắc "Dùng card đồ hoạ": auto (Tự động) | cpu (Tắt) -> config.json "ma_hoa" (giữ mọi khoá khác). Lần xuất sau có hiệu lực."""
    v = "cpu" if str(v or "").strip().lower() in TAT else "auto"
    S = _S()
    p = os.path.join(S.APP, "config.json")
    raw = {}
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8-sig") as f:
                raw = json.load(f)
        except ValueError:
            raise ValueError("config.json đang lỗi nên chưa ghi được lựa chọn này (mở file sửa lại, hoặc báo người cài app)")
        if not isinstance(raw, dict):
            raise ValueError("config.json không đúng dạng, chưa ghi được lựa chọn này")
    raw["ma_hoa"] = v
    tam = p + ".%d.tmp" % os.getpid()
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)
    S.CFG["ma_hoa"] = v
    S.log("card: anh chọn %s (config.json \"ma_hoa\": \"%s\")" % ("Tự động" if v == "auto" else "Tắt", v))
    with LOCK:
        can_do = v == "auto" and TT.get("tt") not in ("xong", "dang_do")
    if can_do:
        bat_dau()
    return trang_thai()


def mo_ta_xuat(x):
    """Kết quả 1 lần xuất (dòng XONG của sua_tay_may) -> {ma_hoa, giai_ma, lui, chu} cho log + trang."""
    x = x or {}
    tk = x.get("card") if isinstance(x.get("card"), dict) else None
    enc = x.get("ma_hoa") or ""
    ds_enc = []
    for e in ((tk or {}).get("ma_hoa") or ([enc] if enc else [])) + [e for e in (x.get("them_ma_hoa") or []) if e]:
        if e not in ds_enc:
            ds_enc.append(e)
    mh_card = [e for e in ds_enc if e not in CPU_ENC]
    gm = (tk or {}).get("giai_ma")
    gm_ok = int((tk or {}).get("giai_ma_ok") or 0)
    lui_mh = int((tk or {}).get("ma_hoa_lui") or 0) + int(x.get("them_lui") or 0)
    lui_gm = int((tk or {}).get("giai_ma_lui") or 0)
    if tk is None and not mh_card and not lui_mh:
        chu = "bằng CPU" + (" (card đang tắt)" if che_do() == "cpu" else "")
    else:
        with LOCK:
            ds = [c["ten"] for c in TT.get("card") or [] if isinstance(c, dict) and _la_that(c.get("ten"))]
        chu = ("mã hoá bằng " + _ten_card(mh_card[0], ds)) if mh_card else "mã hoá bằng CPU"
        chu += ", đọc clip bằng card" if gm and gm_ok else ", đọc clip bằng CPU"
        if lui_mh or lui_gm:
            chu += " · card lỗi %d lần, đã tự làm lại bằng CPU" % (lui_mh + lui_gm)
    return {"ma_hoa": ds_enc, "giai_ma": gm if gm_ok else None, "giai_ma_lan": int((tk or {}).get("giai_ma_lan") or 0), "giai_ma_ok": gm_ok,
            "lui_ma_hoa": lui_mh, "lui_giai_ma": lui_gm, "lui": bool(lui_mh or lui_gm), "chu": chu}


def get(h, u, q):
    if u.path == "/api/sua-tay/card":
        h.send(200, trang_thai())
        return True
    return False


def post(h, u, data):
    if u.path != "/api/sua-tay/card":
        return False
    if data.get("do_lai"):
        if che_do() == "cpu":
            raise ValueError("Đang tắt card đồ hoạ: bật Tự động trước")
        bat_dau(ep=True)
        r = trang_thai()
    elif "che_do" in data:
        r = ghi_che_do(data.get("che_do"))
    else:
        r = trang_thai()
    h.send(200, r)
    return True
