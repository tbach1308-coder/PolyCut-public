"""Claude soát phụ đề tự động (POLY Cut, 4/11).

Anh: "phụ đề tự động có tăng độ chính xác nghe giọng nói được không" -> sau khi máy nghe tạo phụ đề, anh bấm
"Claude soát phụ đề" (hoặc bật "tự soát sau khi nghe"): gửi các câu phụ đề + ngữ cảnh video (tên, chữ trên video, mô tả
cảnh, từ của tiệm) cho Claude Code CỦA TÀI KHOẢN TRÊN MÁY (claude.exe, cách giống Nhờ Claude: không API, không lưu đăng
nhập, không công cụ nào, không lưu phiên). Claude chỉ sửa chữ nghe sai, trả JSON. Mỗi lần bấm = 1 lượt Claude.

Giờ từng chữ (tô từ / phụ đề cụm nảy theo nhịp nói) giữ được: câu cũ có giờ từng chữ (_neo.tu, giờ trong clip) ->
căn dòng chữ cũ / mới bằng difflib: chữ giữ nguyên giữ giờ; đoạn chữ thay (vd "mười hai chấm chín" -> "12.9") nhận đúng
khoảng giờ của đoạn cũ, chia theo độ dài chữ; chữ thêm mới chưa có giờ thì chia đều trong khoảng giữa 2 chữ cũ kề nó
(khoảng hẹp quá thì chia chung khoảng của chữ cũ đứng trước).

Trang (dev/_mod-pd.js) nhận danh sách câu sửa {k, chu, tu, cu} và áp thành 1 bước Ctrl+Z (chỉ áp câu anh chưa sửa tay từ lúc gửi).
API: POST /api/sua-tay/soat-pd {v, plan} -> {ma} · GET /api/sua-tay/soat-pd?ma= -> {dang, buoc, kq, loi}
     POST /api/sua-tay/soat-pd-dung {ma}.
"""
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import threading
import time
import traceback
import unicodedata

import sua_tay as ST

VIEC = {}
LOCK = threading.RLock()
GIAY = 240          # quá chừng này thì dừng
TOI_DA_CAU = 120


def _S():
    return ST.S


# ------------------------------------------------------------------ căn giờ từng chữ
def _khong_dau(w):
    """So khớp bỏ dấu thanh (Claude sửa "tóc" -> "tốc" vẫn giữ giờ của chữ cũ)."""
    w = unicodedata.normalize("NFD", _goc(w)).replace("đ", "d")
    return "".join(c for c in w if not unicodedata.combining(c))


def _goc(w):
    w = unicodedata.normalize("NFC", str(w)).lower()
    return re.sub(r"[^\w%.]", "", w).strip(".")


CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def _doc_so(n):
    """0–999999 -> tiếng đọc (120 -> một trăm hai mươi, 25 -> hai mươi lăm)."""
    n = int(n)
    if n >= 1000:
        ng, du = divmod(n, 1000)
        return _doc_so(ng) + ["nghìn"] + ((["không", "trăm"] if du < 100 else []) + _doc_so(du) if du else [])
    if n >= 100:
        tr, du = divmod(n, 100)
        return [CHU_SO[tr], "trăm"] + ((["linh", CHU_SO[du]] if du < 10 else _doc_so(du)) if du else [])
    if n >= 20:
        c, d = divmod(n, 10)
        return [CHU_SO[c], "mươi"] + ([{1: "mốt", 4: "tư", 5: "lăm"}.get(d, CHU_SO[d])] if d else [])
    if n >= 10:
        return ["mười"] + ([{5: "lăm"}.get(n - 10, CHU_SO[n - 10])] if n > 10 else [])
    return [CHU_SO[n]]


def doc_lai(w):
    """Chữ phụ đề -> các tiếng máy nghe sẽ ra (để căn giờ chữ số): 12.9 -> mười hai chấm chín, 13TR9 -> mười ba triệu chín,
    2020 -> hai không hai mươi, 120Hz -> một trăm hai mươi héc, 64GB -> sáu mươi tư gb, 98% -> … phần trăm, M1 -> m một."""
    g = _goc(w)
    try:
        m = re.match(r"^(\d+)tr(\d*)$", g)
        if m:
            return _doc_so(m.group(1)) + ["triệu"] + ([CHU_SO[int(c)] for c in m.group(2)] if m.group(2) else [])
        m = re.match(r"^(\d+)k$", g)
        if m:
            return _doc_so(m.group(1)) + ["nghìn"]
        m = re.match(r"^(\d+)(hz|gb|tb|%)$", g)
        if m:
            return _doc_so(m.group(1)) + {"hz": ["héc"], "gb": ["gb"], "tb": ["tb"], "%": ["phần", "trăm"]}[m.group(2)]
        m = re.match(r"^m(\d)$", g)
        if m:
            return ["m", CHU_SO[int(m.group(1))]]
        m = re.match(r"^(\d+)[.,](\d+)$", g)
        if m:
            return _doc_so(m.group(1)) + ["chấm"] + (_doc_so(m.group(2)) if len(m.group(2)) == 1 else [CHU_SO[int(c)] for c in m.group(2)])
        m = re.match(r"^(20)(\d\d)$", g)
        if m:
            return ["hai", "không"] + _doc_so(int(m.group(2)))
        if g.isdigit() and len(g) <= 6:
            return _doc_so(g)
    except (ValueError, IndexError):
        pass
    return [g]


def can_tu(cu, chu_moi, s0=None, s1=None):
    """cu = [[chữ, t0, t1], ...] (giờ trong clip, cùng số chữ với câu cũ); chu_moi = câu mới.
    -> [[chữ mới, t0, t1], ...] đúng số chữ của câu mới (tách theo dấu cách, "|" coi như dấu cách).
    Căn theo TIẾNG: chữ mới đọc ra tiếng (12.9 -> mười hai chấm chín) rồi căn với chữ cũ, nên chữ số / giá nhận đúng giờ
    của đoạn đọc số; chữ thay khác hẳn nhận khoảng giờ đoạn cũ; chữ thêm chia đều khoảng trống giữa 2 chữ cũ kề nó."""
    moi = [w for w in re.sub(r"\|", " ", str(chu_moi or "")).split() if w]
    if not moi:
        return []
    cu = [[str(w), float(a), float(b)] for w, a, b in (cu or [])]
    if not cu:
        a, b = float(s0 or 0), float(s1 if s1 is not None else (s0 or 0) + 0.4 * len(moi))
        return [[w, round(x, 3), round(y, 3)] for w, x, y in _chia(moi, a, b)]
    s0 = cu[0][1] if s0 is None else min(float(s0), cu[0][1])
    s1 = cu[-1][2] if s1 is None else max(float(s1), cu[-1][2])
    tieng = [(t, j) for j, w in enumerate(moi) for t in (doc_lai(w) or [_goc(w)])]
    gio = [None] * len(tieng)
    sm = difflib.SequenceMatcher(None, [_khong_dau(w[0]) for w in cu], [_khong_dau(t) for t, _ in tieng], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for d in range(j2 - j1):
                gio[j1 + d] = (cu[i1 + d][1], cu[i1 + d][2])
        elif op == "replace":   # đoạn thay: chia khoảng giờ đoạn cũ theo độ dài tiếng
            for d, x in enumerate(_chia([t for t, _ in tieng[j1:j2]], cu[i1][1], cu[i2 - 1][2])):
                gio[j1 + d] = (x[1], x[2])
    out = [None] * len(moi)
    for (t, j), g in zip(tieng, gio):
        if g:
            out[j] = [moi[j], g[0], g[1]] if out[j] is None else [moi[j], min(out[j][1], g[0]), max(out[j][2], g[1])]
    j = 0
    while j < len(moi):   # chữ thêm mới (chưa có giờ): chia đều khoảng giữa 2 chữ đã có giờ
        if out[j]:
            j += 1
            continue
        k = j
        while k < len(moi) and not out[k]:
            k += 1
        a = out[j - 1][2] if j > 0 else s0
        b = out[k][1] if k < len(moi) else s1
        if b - a >= 0.08 * (k - j):
            for d, x in enumerate(_chia(moi[j:k], a, b)):
                out[j + d] = x
        elif j > 0:   # khoảng hẹp: chia chung khoảng của chữ đứng trước
            p = out[j - 1]
            ds = _chia([p[0]] + moi[j:k], p[1], max(p[2], b))
            out[j - 1] = ds[0]
            for d, x in enumerate(ds[1:]):
                out[j + d] = x
        else:   # đầu câu, không có khoảng trống: chia chung khoảng của chữ đứng sau
            q = out[k]
            ds = _chia(moi[j:k] + [q[0]], min(a, q[1]), q[2])
            for d, x in enumerate(ds[:-1]):
                out[j + d] = x
            out[k] = ds[-1]
        j = k
    for i in range(1, len(out)):   # không chồng / lùi giờ
        if out[i][1] < out[i - 1][1]:
            out[i][1] = out[i - 1][1]
        if out[i - 1][2] > out[i][1]:
            out[i - 1][2] = out[i][1]
        if out[i][2] < out[i][1]:
            out[i][2] = out[i][1]
    return [[w, round(a, 3), round(b, 3)] for w, a, b in out]


def _chia(ws, a, b):
    """Chia khoảng [a, b] cho các chữ theo độ dài chữ."""
    tong = sum(max(1, len(w)) for w in ws) or 1
    out, t = [], a
    for w in ws:
        d = (b - a) * max(1, len(w)) / tong
        out.append([w, t, t + d])
        t += d
    if out:
        out[-1][2] = b
    return out


# ------------------------------------------------------------------ từ điển của tiệm (engine/tu_dien.py)
def _tu_dien_chu():
    try:
        p = os.path.join(_S().engine()["dir"], "tu_dien.py")
        spec = importlib.util.spec_from_file_location("tu_dien_poly", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m.tu_cho_claude(m.doc(os.path.join(os.path.dirname(p), "tu-dien-tiem.txt")))
    except Exception:  # noqa
        return "iPad, iPad Pro, iPad Air, iPad Mini, iPhone, MacBook, MacBook Air, MacBook Pro, Apple Pencil, Magic Keyboard"


# ------------------------------------------------------------------ câu + ngữ cảnh gửi Claude
def _cau_ds(plan):
    ds = []
    for it in plan.get("phu_de") or []:
        chu = str(it.get("chu") or "").strip()
        if not chu or not it.get("_k"):
            continue
        neo = it.get("_neo") or {}
        ds.append({"k": str(it["_k"]), "chu": chu, "t": float(neo.get("s0", it.get("t0") or 0)),
                   "f": str(neo.get("file") or ""), "neo": neo, "it": it})
    # thứ tự: theo cảnh rồi theo giờ trong clip (câu chưa neo theo giờ trên video)
    thu_tu = {}
    for i, c in enumerate(plan.get("canh") or []):
        thu_tu.setdefault(c.get("_id"), i)
    ds.sort(key=lambda x: (thu_tu.get((x["neo"] or {}).get("id"), 1e9), x["t"]))
    return ds[:TOI_DA_CAU]


def _video_txt(v, plan):
    chu = plan.get("chu") or {}
    dong = ["- Tên video: %s" % (plan.get("ten") or os.path.basename(v))]
    hook = [x for x in (chu.get("hook") or []) if x]
    if hook:
        dong.append("- Hook (chữ to đầu video, anh viết tay — tin được): %s" % " / ".join(map(str, hook)))
    nhan = [str(x.get("chu")) for x in chu.get("nhan_chu") or [] if x.get("chu")]
    if nhan:
        dong.append("- Nhãn chữ trên video (anh viết tay): %s" % ", ".join(nhan))
    g = chu.get("the_gia")
    if isinstance(g, dict) and (g.get("gia") or g.get("phu")):
        dong.append("- Thẻ giá: %s %s" % (g.get("gia") or "", g.get("phu") or ""))
    if chu.get("tieu_de"):
        dong.append("- Tiêu đề ghim: %s" % chu["tieu_de"])
    mt = [str(c.get("mo_ta")) for c in plan.get("canh") or [] if c.get("mo_ta")]
    if mt:
        dong.append("- Mô tả cảnh: %s" % " | ".join(mt[:20]))
    clip = []
    for c in plan.get("canh") or []:
        b = os.path.splitext(os.path.basename(str(c.get("file") or "")))[0]
        if b and b not in clip:
            clip.append(b)
    if clip:
        dong.append("- Tên clip / thư mục: %s (%s)" % (", ".join(clip[:12]), os.path.basename(os.path.dirname(str((plan.get("canh") or [{}])[0].get("file") or "")))))
    return "\n".join(dong)


def _lay_json(txt):
    txt = str(txt or "")
    for x in reversed(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", txt, re.S)):
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


def ap_ket_qua(ds, kq):
    """Kết quả Claude -> danh sách câu sửa hợp lệ [{k, cu, chu, tu, ly_do}] (tu = giờ trong clip, đúng số chữ câu mới)."""
    theo_k = {x["k"]: x for x in ds}
    out = []
    for s in (kq or {}).get("sua") or []:
        if not isinstance(s, dict):
            continue
        x = theo_k.get(str(s.get("k") or ""))
        chu = " ".join(str(s.get("chu") or "").replace("|", " ").split())
        if not x or not chu or len(chu) > 240 or any(o["k"] == x["k"] for o in out):
            continue
        cu = x["chu"]
        if chu == " ".join(cu.replace("|", " ").split()):
            continue
        n_cu, n_moi = len(cu.split()), len(chu.split())
        if n_moi > n_cu + 4 or len(chu) > len(cu) * 1.6 + 12:   # viết thêm ý / thêm câu: bỏ
            continue
        neo = x["neo"] or {}
        tu_cu = neo.get("tu") or []
        if len(tu_cu) != len([w for w in cu.replace("|", " ").split() if w]):
            tu_cu = []   # anh đã sửa tay khác số chữ: chia đều trong câu
        tu = can_tu(tu_cu, chu, neo.get("s0"), neo.get("s1")) if neo else None
        out.append({"k": x["k"], "cu": cu, "chu": chu, "tu": tu, "ly_do": str(s.get("ly_do") or "")[:120]})
    return out


# ------------------------------------------------------------------ chạy Claude Code trên máy
def _set(ma, **kw):
    with LOCK:
        if ma in VIEC:
            VIEC[ma].update(kw)
            return not VIEC[ma].get("dung")
    return False


def bat_dau(v, plan):
    S = _S()
    v = ST.thu_muc_video(v)
    ST.kiem_ke_hoach(v, plan, can_file=False)
    if plan.get("giong"):
        raise ValueError("Video dùng giọng đọc AI: phụ đề là lời anh viết, không cần soát")
    ds = _cau_ds(plan)
    if not ds:
        raise ValueError("Video chưa có phụ đề để soát. Bấm Phụ đề tự động trước")
    cmd = list(S.CFG.get("lenh_claude_nho") or []) or S.resolve_claude()   # lenh_claude_nho: chỉ để thử (máy dev)
    if not cmd:
        raise ValueError("Không tìm thấy Claude Code trên máy")
    with LOCK:
        for x in VIEC.values():
            if x.get("dang") and x["v"] == ST.norm(v):
                return {"ma": x["ma"]}
        for k in sorted(VIEC)[:-20]:
            if not VIEC[k].get("dang"):
                VIEC.pop(k, None)
        ma = "%x" % int(time.time() * 1000)
        VIEC[ma] = {"ma": ma, "v": ST.norm(v), "dang": True, "buoc": "Chuẩn bị", "bat_dau": time.time(), "kq": None, "loi": ""}
    threading.Thread(target=_chay, args=(ma, v, plan, ds, cmd), daemon=True).start()
    return {"ma": ma}


def trang_thai(ma):
    with LOCK:
        st = VIEC.get(str(ma or ""))
        if not st:
            return {"dang": False, "loi": "Không thấy lượt soát này (app vừa khởi động lại?)"}
        out = {k: st.get(k) for k in ("ma", "dang", "buoc", "kq", "loi")}
        out["giay_da"] = round(time.time() - st["bat_dau"])
        return out


def dung(ma):
    with LOCK:
        st = VIEC.get(str(ma or ""))
        if not st or not st.get("dang"):
            return {"ok": True}
        st["dung"] = True
        pid = st.get("pid")
    ST._giet(pid)
    return {"ok": True}


def _chay(ma, v, plan, ds, cmd):
    S = _S()
    W = os.path.join(v, "lam", "sua-tay", "claude-soat", ma)
    try:
        os.makedirs(W, exist_ok=True)
        goc = os.path.dirname(W)
        for d in sorted(x for x in os.listdir(goc) if os.path.isdir(os.path.join(goc, x)))[:-6]:
            shutil.rmtree(os.path.join(goc, d), ignore_errors=True)
        with open(os.path.join(S.PROMPTS, "soat-phu-de.md"), encoding="utf-8") as f:
            mau = f.read()
        cau = "\n".join(json.dumps({"k": x["k"], "chu": x["chu"]}, ensure_ascii=False) for x in ds)
        prompt = (mau.replace("{{VIDEO}}", _video_txt(v, plan)).replace("{{TU_DIEN}}", _tu_dien_chu()).replace("{{CAU}}", cau))
        pp = os.path.join(W, "prompt.txt")
        with open(pp, "w", encoding="utf-8") as f:
            f.write(prompt)
        model = S.CFG.get("model_soat", S.CFG.get("model_nho", "sonnet"))
        if not _set(ma, buoc="Claude đang đọc %d câu phụ đề" % len(ds)):
            _set(ma, dang=False, loi="Đã dừng")
            return
        kq, loi, ket = None, "", None
        for moi in (True, False):   # bản Claude Code cũ chưa có --tools ... thì chạy lại bằng cờ cũ
            args = cmd + ["-p", "--output-format", "stream-json", "--verbose"]
            if moi:
                args += ["--tools", "", "--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"]
            else:
                args += ["--disallowedTools", "Bash", "Edit", "Write", "Read", "NotebookEdit", "WebFetch", "WebSearch"]
            if model:
                args += ["--model", model]
            env = dict(os.environ, PYTHONUTF8="1")
            kw = {"creationflags": ST.NO_WIN | 0x00000200} if ST.IS_WIN else {"start_new_session": True}
            with open(pp, "rb") as pin, open(os.path.join(W, "stderr.txt"), "wb") as er:
                p = subprocess.Popen(args, cwd=W, stdin=pin, stdout=subprocess.PIPE, stderr=er, env=env, **kw)
            with LOCK:
                VIEC[ma]["pid"] = p.pid
                if VIEC[ma].get("dung"):
                    ST._giet(p.pid)
            hen = threading.Timer(GIAY, lambda: (_set(ma, het_gio=True), ST._giet(p.pid)))
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
                        _set(ma, buoc="Claude đang sửa chữ nghe sai")
                    elif ev.get("type") == "result":
                        ket = ev
            code = p.wait()
            hen.cancel()
            with LOCK:
                st = dict(VIEC.get(ma) or {})
            if st.get("dung"):
                _set(ma, dang=False, loi="Đã dừng")
                return
            if st.get("het_gio"):
                _set(ma, dang=False, loi="Claude soát quá %d phút, đã dừng. Bấm soát lại." % (GIAY // 60))
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
                    loi = "Claude trả lời không đúng mẫu, bấm soát lại"
            break
        if kq is not None:
            sua = ap_ket_qua(ds, kq)
            out = {"sua": sua, "ghi_chu": str(kq.get("ghi_chu") or "").strip()[:300], "so_cau": len(ds),
                   "giay": round(time.time() - VIEC[ma]["bat_dau"]), "chi_phi": (ket or {}).get("total_cost_usd")}
            ST._ghi(os.path.join(W, "ket-qua.json"), out)
            _set(ma, dang=False, kq=out, buoc="Xong")
        else:
            _set(ma, dang=False, loi=loi or "Lỗi không rõ")
        S.log("sua-tay soat-pd %s %s: %s" % (ma, os.path.basename(v), ("ok sua %d/%d cau" % (len(out["sua"]), len(ds))) if kq is not None else loi))
    except Exception as ex:  # noqa
        S.log("sua-tay soat-pd loi: %s" % traceback.format_exc()[-1500:])
        _set(ma, dang=False, loi="Lỗi: %s" % ex)


def mo_tu_dien():
    p = os.path.join(_S().engine()["dir"], "tu-dien-tiem.txt")
    if not os.path.isfile(p):
        raise ValueError("Bộ dựng chưa có từ điển của tiệm (tu-dien-tiem.txt)")
    if ST.IS_WIN:
        subprocess.Popen(["notepad.exe", p], creationflags=ST.NO_WIN)
    return {"ok": True, "p": p}


# ------------------------------------------------------------------ HTTP (sua_tay.get / post gọi)
def get(h, u, q):
    if u.path == "/api/sua-tay/soat-pd":
        h.send(200, trang_thai((q.get("ma") or [""])[0]))
        return True
    return False


def post(h, u, data):
    if u.path == "/api/sua-tay/soat-pd":
        r = bat_dau(data.get("v"), data.get("plan"))
    elif u.path == "/api/sua-tay/soat-pd-dung":
        r = dung(data.get("ma"))
    elif u.path == "/api/sua-tay/soat-pd-tu-dien":   # mở từ điển của tiệm (engine/tu-dien-tiem.txt) bằng Notepad để anh thêm từ
        r = mo_tu_dien()
    else:
        return False
    h.send(200, r)
    return True
