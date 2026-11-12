#!/usr/bin/env python3
"""Canh giờ từng từ cho phụ đề theo lời nói thật (để chữ không trễ / sớm so với tiếng).

Dùng:  python3 canh_tu.py <ke-hoach.json> <thu_muc_mo_hinh> [--fps 30] [--bu 0.03] [--duong premiere|may_chu]
Ghi đè phu_de[].tu (và t0/t1, canh) trong ke-hoach.json. Mỗi câu phụ đề thuộc 1 cảnh gốc (canh[]):
  - câu đã có `canh` (số thứ tự trong canh[], 0 = cảnh đầu; canh_tu ghi lại sau mỗi lần chạy) -> dùng nó;
  - chưa có -> cảnh chứa t0 khi xếp các cảnh gốc nối nhau từ 0 (KHÔNG tính phần mở đầu montage / thẻ hỏi).
Giờ ghi ra theo dòng thời gian THẬT (ke_hoach.build): cảnh mở đầu montage / thẻ hỏi / đóng băng đứng trước được cộng vào
(28/10: bản cũ bắt đầu từ 0 nên mở đầu montage làm cả video phụ đề sớm 1,5s).
Nhớ kết quả nghe trong <thư mục kế hoạch>/cache-nghe.json (khóa: md5 file nguồn + vào/ra + mô hình): sửa chữ rồi chạy
lại không phải nghe lại.

Cách làm (theo từng CẢNH, không theo từng câu):
1. Nghe lại cả đoạn nguồn của cảnh bằng sherpa-onnx, mở rộng 1s trước / 0.3s sau để máy nghe có ngữ cảnh.
   Đã đo: mốc từ GIỮA dòng của sherpa sớm hơn tiếng thật ~0.05s, nhưng 1-2 từ ĐẦU của mỗi lần nghe bị dồn về đầu
   đoạn (sớm 0.3-1.3s) → các từ có mốc trước lúc tiếng bắt đầu thật (năng lượng 20ms vượt ngưỡng) được rải lại từ
   lúc đó; từ nào đứng sau khoảng lặng thì lấy lúc tiếng bắt đầu thật gần đó.
   (Đã thử đặt trước 1 đoạn tiếng khác cho máy "nóng" → máy nuốt mất từ đầu: bỏ.)
   (Bản cũ dời cả câu theo từ đầu → các từ sau bị trễ ~0.35s: sai.)
2. Chữ phụ đề (đã sửa chính tả, có "|", có số "12.9", "2020"...) ít khi khớp 1-1 với chữ máy nghe → so khớp
   chuỗi từ (difflib) lấy các từ trùng làm mốc chắc chắn, phần giữa các mốc nội suy theo vị trí ký tự.
3. Câu: t0 = giờ từ đầu, t1 = hết từ cuối + 0.15 (không chồng câu sau, không quá cuối cảnh).
Giờ trên timeline tính theo khung hình như Premiere (lenh_premiere đặt điểm vào/ra đúng khung).
"""
import json, os, re, subprocess, sys, bisect, difflib, hashlib, unicodedata
from chung import FFMPEG

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 16000


def moc_canh_that(plan, fps, duong="premiere"):
    """{chỉ số cảnh gốc: giờ bắt đầu nội dung cảnh đó trên timeline thật} — đặt nối tiếp theo khung như Premiere, gồm cả
    các cảnh mở đầu (canh < 0: montage, thẻ hỏi) và phần đóng băng đứng trước. None nếu không dựng được dòng thời gian.
    Bản máy tiệm: duong = "may_chu" (dựng ffmpeg) thì trừ phần chồng chuyển cảnh xfade như dung_may_chu (bản cũ luôn tính
    kiểu Premiere -> phụ đề bản ffmpeg trễ dần 0,16–0,35s mỗi chuyển cảnh)."""
    try:
        sys.path.insert(0, HERE)
        import ke_hoach
        shots = ke_hoach.build(plan, duong)["shots"]
    except Exception:
        return None
    out, k = {}, 0
    for s in shots:
        db = int(round((s.get("dong_bang") or 0.0) * fps))
        if s.get("the_hoi"):
            n = int(round(s["dur"] * fps))
        else:
            n = int(round(s["den"] * fps)) - int(round(s["tu"] * fps)) + db
        if duong != "premiere":
            k -= int(round((s.get("chuyen") or 0.0) * fps))  # xfade: cảnh sau bắt đầu chồng lên đuôi cảnh trước
        if s["canh"] >= 0 and s["canh"] not in out:
            out[s["canh"]] = (k + db) / fps
        k += n
    return out


def md5_file(p, _nho={}):
    if p not in _nho:
        h = hashlib.md5()
        with open(p, "rb") as f:
            for blk in iter(lambda: f.read(1 << 22), b""):
                h.update(blk)
        _nho[p] = h.hexdigest()
    return _nho[p]


def nguon_local(plan, f):
    n = (plan.get("nguon") or {}).get(f) or {}
    return n.get("local") or f


def doc_tieng(path, a, b):
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{max(0.0, a):.3f}", "-t", f"{b - max(0.0, a):.3f}", "-i", path,
                          "-ac", "1", "-ar", str(SR), "-af", "highpass=f=80", "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)


def nhan_dang(rec, x):
    """[[chữ, bắt đầu, hết], ...] giây tính từ đầu x. Hết = bắt đầu từ sau (từ cuối: +0.5s)."""
    z = lambda g: np.zeros(int(g * SR), np.float32)
    truoc = z(0.25)
    L = len(truoc) / SR
    s = rec.create_stream()
    s.accept_waveform(SR, np.concatenate([truoc, x, z(0.25)]))
    rec.decode_stream(s)
    r = s.result
    tu, cur = [], None
    for tok, ts in zip(r.tokens, r.timestamps):
        t = ts - L
        if tok.startswith(("▁", " ")) or cur is None:
            if cur and cur[0]:
                tu.append(cur)
            cur = [tok.lstrip("▁ "), t, t + 0.5]
        else:
            cur[0] += tok
    if cur and cur[0]:
        tu.append(cur)
    for i in range(len(tu) - 1):
        tu[i][2] = min(tu[i][2], tu[i + 1][1])
    return tu


def nang_luong(x):
    n = len(x) // 320
    if n == 0:
        return np.zeros(0)
    return 20 * np.log10(np.sqrt((x[:n * 320].reshape(n, 320) ** 2).mean(1)) + 1e-9)


def cac_luc_bat_dau(e, nguong_tuong_doi=26.0):
    """Các giây tiếng bắt đầu lại sau khoảng lặng (>= 40ms dưới ngưỡng)."""
    if len(e) == 0:
        return []
    ng = max(-42.0, e.max() - nguong_tuong_doi)
    on, duoi = [], 3
    for j, v in enumerate(e):
        if v > ng and duoi >= 2:
            on.append(j * 0.02)
        duoi = duoi + 1 if v <= ng else 0
    return on


def chuan(w):
    """So khớp không dấu (máy nghe hay sai dấu: "tóc" / "tốc")."""
    w = unicodedata.normalize("NFD", w.lower().replace("đ", "d"))
    w = "".join(ch for ch in w if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^\w]", "", w)


CHU_SO = ["không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "tám", "chín"]


def doc_so_nguyen(n):
    """Đọc số 0-999999 kiểu nói thường (12 -> mười hai, 120 -> một trăm hai mươi, 25 -> hai mươi lăm)."""
    n = int(n)
    if n >= 1000:
        ng, du = divmod(n, 1000)
        out = doc_so_nguyen(ng) + ["nghìn"]
        if du:
            out += (["không", "trăm"] if du < 100 else []) + doc_so_nguyen(du)
        return out
    if n >= 100:
        tr, du = divmod(n, 100)
        out = [CHU_SO[tr], "trăm"]
        if du:
            out += (["lẻ", CHU_SO[du]] if du < 10 else doc_so_nguyen(du))
        return out
    if n >= 20:
        c, d = divmod(n, 10)
        return [CHU_SO[c], "mươi"] + ([{1: "mốt", 5: "lăm"}.get(d, CHU_SO[d])] if d else [])
    if n >= 10:
        d = n - 10
        return ["mười"] + ([{5: "lăm"}.get(d, CHU_SO[d])] if d else [])
    return [CHU_SO[n]]


def doc_tu(w):
    """Chữ phụ đề -> các tiếng sẽ nghe được ("12.9" -> mười hai chấm chín, "12tr8" -> mười hai triệu tám trăm nghìn,
    "120Hz" -> một trăm hai mươi héc, "200K" -> hai trăm nghìn, "2020" -> hai không hai mươi). Không phải số: giữ nguyên."""
    g = w.rstrip("|").strip(",.!?:;…\"'()")
    m = re.match(r"^(\d+)tr(\d)?$", g, re.I)
    if m:
        return doc_so_nguyen(m.group(1)) + ["triệu"] + ([CHU_SO[int(m.group(2))], "trăm", "nghìn"] if m.group(2) else [])
    m = re.match(r"^(\d+)k$", g, re.I)
    if m:
        return doc_so_nguyen(m.group(1)) + ["nghìn"]
    m = re.match(r"^(\d+)hz$", g, re.I)
    if m:
        return doc_so_nguyen(m.group(1)) + ["héc"]
    m = re.match(r"^(\d+)[.,](\d+)$", g)
    if m:
        return doc_so_nguyen(m.group(1)) + ["chấm"] + [CHU_SO[int(c)] for c in m.group(2)] if len(m.group(2)) > 1 \
            else doc_so_nguyen(m.group(1)) + ["chấm"] + doc_so_nguyen(m.group(2))
    m = re.match(r"^(20)(\d\d)$", g)
    if m:  # năm: "hai không hai mươi"
        return ["hai", "không"] + doc_so_nguyen(int(m.group(2)))
    if g.isdigit():
        return doc_so_nguyen(g)
    return [w]


def main():
    plan_p, mdir = sys.argv[1], sys.argv[2]
    fps = float(sys.argv[sys.argv.index("--fps") + 1]) if "--fps" in sys.argv else 30.0
    bu = float(sys.argv[sys.argv.index("--bu") + 1]) if "--bu" in sys.argv else 0.05
    plan = json.load(open(plan_p, encoding="utf-8"))
    # bản máy tiệm: dòng thời gian theo đường dựng (--duong, không có thì kieu.duong của kế hoạch, mặc định premiere)
    duong = sys.argv[sys.argv.index("--duong") + 1] if "--duong" in sys.argv else ((plan.get("kieu") or {}).get("duong") or "premiere")
    rec_nho = []

    def rec():  # chỉ nạp máy nghe khi cache không có
        if not rec_nho:
            import sherpa_onnx
            f = lambda pat: next(os.path.join(mdir, x) for x in sorted(os.listdir(mdir)) if re.match(pat, x))
            rec_nho.append(sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=f(r"encoder.*\.onnx$"), decoder=f(r"decoder.*\.onnx$"), joiner=f(r"joiner.*\.onnx$"),
                tokens=os.path.join(mdir, "tokens.txt"), num_threads=2, decoding_method="greedy_search"))
        return rec_nho[0]
    cache_p = os.path.join(os.path.dirname(os.path.abspath(plan_p)), "cache-nghe.json")
    try:
        cache = json.load(open(cache_p, encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    dem = {"trung": 0, "nghe_moi": 0}
    fr = lambda t: int(round(t * fps)) / fps
    off0, t = [], 0.0  # các cảnh gốc nối nhau từ 0 (cách tính cũ) — chỉ để xếp câu CHƯA có `canh` vào cảnh
    for c in plan["canh"]:
        off0.append(t)
        t += fr(c["den"]) - fr(c["tu"])
    that = moc_canh_that(plan, fps, duong)
    bao = []
    if that is None or len(that) != len(plan["canh"]):
        bao.append("không dựng được dòng thời gian thật (ke_hoach) — giờ tính từ 0 như cũ, KHÔNG cộng phần mở đầu")
        off = list(off0)
    else:
        off = [that[i] for i in range(len(plan["canh"]))]
    lech_mo_dau = round(off[0] - off0[0], 3) if off else 0.0

    def canh_cua(x):
        for i, c in enumerate(plan["canh"]):
            if off0[i] - 1e-6 <= x < off0[i] + fr(c["den"]) - fr(c["tu"]) - 1e-6:
                return i
        return len(plan["canh"]) - 1

    pd = plan.get("phu_de") or []
    nhom = {}
    for n, p in enumerate(pd):
        ci = p.get("canh")
        if not (isinstance(ci, int) and 0 <= ci < len(plan["canh"])):
            ci = canh_cua(p["t0"] + 0.01)
        nhom.setdefault(ci, []).append(n)
    thong_ke = []
    mo_hinh = os.path.basename(os.path.normpath(mdir))
    for i, ds in sorted(nhom.items()):
        c = plan["canh"][i]
        a0, b0 = fr(c["tu"]), fr(c["den"])
        wa, wb = max(0.0, a0 - 1.0), b0 + 0.3
        src = nguon_local(plan, c["file"])
        khoa = f"{md5_file(src)}|{wa:.4f}|{wb:.4f}|{mo_hinh}"
        if khoa in cache:
            ons = [wa + o for o in cache[khoa]["ons"]]
            ws = [[w, wa + s0, wa + s1] for w, s0, s1 in cache[khoa]["ws"]]
            dem["trung"] += 1
        else:
            x = doc_tieng(src, wa, wb)
            ons_r = cac_luc_bat_dau(nang_luong(x))
            ws_r = nhan_dang(rec(), x)
            cache[khoa] = {"ons": [float(o) for o in ons_r], "ws": [[w, float(s0), float(s1)] for w, s0, s1 in ws_r]}  # json giữ đúng float
            ons = [wa + o for o in cache[khoa]["ons"]]
            ws = [[w, wa + s0, wa + s1] for w, s0, s1 in cache[khoa]["ws"]]
            dem["nghe_moi"] += 1
        # mấy từ đầu lần nghe bị dồn về trước lúc có tiếng -> rải lại từ lúc tiếng bắt đầu thật
        if ws and ons:
            n_d = 0
            while n_d < len(ws) and ws[n_d][1] < ons[0] - 0.05:
                n_d += 1
            if n_d:
                het = ws[n_d][1] if n_d < len(ws) else ons[0] + 0.25 * n_d
                buoc = max(0.0, het - ons[0]) / n_d
                for j in range(n_d):
                    ws[j][1] = ons[0] + j * buoc
                    ws[j][2] = ons[0] + (j + 1) * buoc if j + 1 < n_d else het
        # mốc giữa dòng của máy nghe sớm ~0.05s; từ đứng sau khoảng lặng -> lấy lúc tiếng bắt đầu thật gần đó
        for j, w in enumerate(ws):
            w[1] += bu
            w[2] += bu
            if j > 0 and w[1] - ws[j - 1][1] > 0.45:
                cand = [o for o in ons if w[1] - 0.12 <= o <= w[1] + 0.35]
                if cand:
                    w[1] = min(cand[0], w[2] - 0.05) if j + 1 < len(ws) else cand[0]
        nghe = [list(w) for w in ws if a0 - 0.25 <= w[1] < b0 - 0.05]
        on_dau = next((o for o in ons if o >= a0 - 0.1), None)
        hi_src = b0
        if not nghe:
            bao.append(f"cảnh {i + 1}: không nghe được chữ nào, giữ nguyên {len(ds)} câu (chỉ dời theo phần mở đầu)")
            thong_ke.append({"canh": i + 1, "cau": len(ds), "khop": 0, "tieng": 0, "nghe": 0})
            for n in ds:
                if not isinstance(pd[n].get("canh"), int):  # giờ cũ tính từ 0 -> dời sang dòng thời gian thật
                    dl = off[i] - off0[i]
                    pd[n]["t0"], pd[n]["t1"] = round(pd[n]["t0"] + dl, 3), round(pd[n]["t1"] + dl, 3)
                    for w in pd[n].get("tu") or []:
                        w[1], w[2] = round(w[1] + dl, 3), round(w[2] + dl, 3)
                pd[n]["canh"] = i
            continue
        for w in nghe:
            w[2] = min(w[2], hi_src)
        # chữ phụ đề của cả cảnh
        toks, cua = [], []
        for n in ds:
            tk = re.sub(r"\s*\|\s*", "| ", pd[n]["chu"].strip()).split()
            toks += tk
            cua += [n] * len(tk)
        # vị trí ký tự
        cs, pos = [], 0
        for w in toks:
            L = len(w.rstrip("|")) + 1
            cs.append((pos, pos + L - 1))
            pos += L
        tot = pos
        hs, pos = [], 0
        for w in nghe:
            L = len(w[0]) + 1
            hs.append((pos, pos + L - 1))
            pos += L
        htot = pos
        # mốc: từ khớp nhau (số đọc ra thành chữ: mỗi tiếng chiếm một phần vị trí ký tự của từ đó)
        sub, scs = [], []
        for w, (q0, q1) in zip(toks, cs):
            ds_ = doc_tu(w)
            L = (q1 - q0) / len(ds_)
            for k_, x_ in enumerate(ds_):
                sub.append(chuan(x_))
                scs.append((q0 + k_ * L, q0 + (k_ + 1) * L if k_ + 1 < len(ds_) else q1))
        sm = difflib.SequenceMatcher(None, sub, [chuan(w[0]) for w in nghe], autojunk=False)
        moc = []  # (vị trí ký tự chữ, giờ)
        so_khop = 0
        pa, pb = 0, 0
        for blk in sm.get_matching_blocks():
            # khoảng giữa hai chỗ khớp: chia theo vị trí ký tự của chữ máy nghe trong khoảng đó
            if blk.a > pa and blk.b > pb:
                T0, T1 = scs[pa][0], scs[blk.a - 1][1]
                hw = nghe[pb:blk.b]
                Ht = float(sum(len(w[0]) + 1 for w in hw))
                c = 0
                for w in hw:
                    L = len(w[0]) + 1
                    moc.append((T0 + c / Ht * (T1 - T0), w[1]))
                    moc.append((T0 + (c + L - 1) / Ht * (T1 - T0), w[2]))
                    c += L
            pa, pb = blk.a + blk.size, blk.b + blk.size
            for d in range(blk.size):
                ti, hj = blk.a + d, blk.b + d
                if not sub[ti]:
                    continue
                moc.append((scs[ti][0], nghe[hj][1]))
                moc.append((scs[ti][1], nghe[hj][2]))
                so_khop += 1
        # hai đầu
        moc.sort()
        if not moc or moc[0][0] > 0:
            t_dau = nghe[0][1] if on_dau is None else min(nghe[0][1], max(on_dau, a0))
            moc.insert(0, (0, t_dau))
        if moc[-1][0] < tot - 1:
            moc.append((tot - 1, nghe[-1][2]))
        # nếu không khớp từ nào: nội suy cả theo vị trí ký tự máy nghe
        if so_khop == 0:
            pts = []
            for (h0, h1), w in zip(hs, nghe):
                pts += [(h0 / htot * tot, w[1]), (h1 / htot * tot, w[2])]
            moc = pts
        moc.sort()
        # đơn điệu tăng
        m2 = []
        for q, tt in moc:
            if m2 and tt < m2[-1][1]:
                tt = m2[-1][1]
            if m2 and q == m2[-1][0]:
                m2[-1] = (q, max(m2[-1][1], tt))
            else:
                m2.append((q, tt))
        xs = [q for q, _ in m2]

        def tmap(q):
            k = max(0, min(bisect.bisect_right(xs, q) - 1, len(m2) - 2))
            if len(m2) == 1:
                return m2[0][1]
            (x0, y0), (x1, y1) = m2[k], m2[k + 1]
            if q <= x0:
                return y0
            if q >= x1:
                return y1
            return y0 + (y1 - y0) * (q - x0) / (x1 - x0)

        ra = lambda s: off[i] + s - a0
        lo, hi = off[i], off[i] + b0 - a0
        moi = {n: [] for n in ds}
        for w, (q0, q1), n in zip(toks, cs, cua):
            s0, s1 = tmap(q0), tmap(q1)
            s0 = round(min(max(ra(s0), lo), hi - 0.05), 3)
            s1 = round(min(max(ra(s1), s0 + 0.05), hi), 3)
            moi[n].append([w, s0, s1])
        for n in ds:
            tu = moi[n]
            for a, b in zip(tu, tu[1:]):  # không lùi
                if b[1] < a[1]:
                    b[1] = a[1]
            pd[n]["tu"] = tu
            pd[n]["t0"] = tu[0][1]
            pd[n]["t1"] = round(min(tu[-1][2] + 0.15, hi), 3)
            pd[n]["canh"] = i  # lần chạy sau xếp câu theo trường này (giờ đã là dòng thời gian thật)
        bao.append(f"cảnh {i + 1}: {len(ds)} câu, khớp {so_khop}/{len(sub)} tiếng (nghe {len(nghe)} từ)")
        thong_ke.append({"canh": i + 1, "cau": len(ds), "khop": so_khop, "tieng": len(sub), "nghe": len(nghe)})
    # không chồng nhau
    for a, b in zip(pd, pd[1:]):
        if a["t1"] > b["t0"] - 0.04:
            a["t1"] = round(max(a["t0"] + 0.2, b["t0"] - 0.04), 3)
            if a.get("tu"):
                for w in a["tu"]:
                    w[1] = min(w[1], a["t1"] - 0.05)
                    w[2] = min(w[2], a["t1"])
    json.dump(plan, open(plan_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if dem["nghe_moi"]:
        tam = cache_p + ".tmp"
        json.dump(cache, open(tam, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tam, cache_p)
    print(json.dumps({"so_cau": len(pd), "bao": bao, "canh": thong_ke, "mo_dau_giay": lech_mo_dau, "cache": dem},
                     ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
