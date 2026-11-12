# -*- coding: utf-8 -*-
"""Giọng AI đọc lại lời trong khối tiếng tách (POLY Cut r32, 10/11 anh: "cho đè giọng đọc ai trên file âm thanh tách ra, không cần viết chữ").

Kế hoạch (tùy chọn, chỉ dựng máy chủ — ke_hoach.build chép khoá này CHỈ khi có, Premiere bỏ qua):
  "giong_de": {
    "cau":  [{"chu": "...", "nguon": "<khoá trong nguon>", "goc": "<goc khối tách>", "s0": 1.95, "s1": 2.63,   # giờ câu gốc trong clip
              "local": ".../lam/sua-tay/giong/de/cau-<mã>.wav", "giay": 0.72, "toc": 1.2,                    # file giọng (đã tăng tốc nếu cần)
              "giong": "vn-adam", "ten": "Adam", "toc_do": "+10%"}],
    "vung": [{"nguon": "<khoá>", "goc": "<goc>", "tu": 0.0, "den": 11.95, "nen": 0}]   # đoạn tiếng gốc được đọc lại: tiếng gốc ở đây
  }                                                                                       # nhân nen (0 = tắt hẳn, 0.15 = giữ làm nền)
Câu giọng đi theo KHỐI tiếng tách (plan.am_tach) như phụ đề neo theo khối (_neo.am): khối nào cùng clip + cùng goc chứa giờ bắt đầu câu
(hoặc chứa ≥ 40% câu) -> giọng bắt đầu ở t = khối.t + (s0 − khối.tu). Dời khối: giọng dời theo; cắt cuối khối vào giữa câu: giọng dừng ở
cuối khối; xoá khối / "Lấy lại tiếng gốc": câu không còn khối -> không phát. File không có -> bỏ câu đó.
Trộn (dung_may_chu): mỗi câu 1 đầu vào, dời tới giây t (adelay), gộp, chỉnh về −16 LUFS như giọng AI cũ (đo cả các câu 1 lần), theo thanh
"Giọng AI" ở Cân tiếng, làm tín hiệu hạ nhạc; khối tiếng tách bị đọc lại thì phần nằm trong "vung" nhân nen. Không có khoá: không gì đổi.
Hàm thuần Python (không ffmpeg) trừ gain(): sua_tay_may dùng chung dat() để vẽ / báo ở xem trước.
"""
import json, os, re, subprocess

TOI_THIEU = 0.1   # giây: phần giọng còn lại ngắn hơn thì bỏ


def _so(v, mac, lo, hi):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return mac
    return mac if v != v else max(lo, min(hi, v))


def _khoi(tl):
    """Khối tiếng tách dùng được -> [(khối, tu, den, t)]."""
    out = []
    for k in tl.get("am_tach") or []:
        if not isinstance(k, dict) or not isinstance(k.get("nguon"), str):
            continue
        tu, den, t = _so(k.get("tu"), -1.0, -1.0, 1e6), _so(k.get("den"), -1.0, -1.0, 1e6), _so(k.get("t"), 0.0, -1e6, 1e6)
        if tu < 0 or den - tu < 0.05:
            continue
        out.append((k, tu, den, t))
    return out


def dat(tl, T=None, can_file=True):
    """Đặt các câu giọng lên video -> {"dat": [{i, local, t, dai, off, cat, chu, khoi}], "an": [{i, ly_do}]} (theo giờ t).
    T = độ dài video (cắt phần giọng thò ra ngoài); can_file = bỏ câu mất file."""
    gd = tl.get("giong_de")
    out, an = [], []
    if not isinstance(gd, dict):
        return {"dat": out, "an": an}
    ks = _khoi(tl)
    for i, c in enumerate(gd.get("cau") or []):
        if not isinstance(c, dict):
            continue
        local = c.get("local")
        s0, s1, giay = _so(c.get("s0"), -1.0, -1.0, 1e6), _so(c.get("s1"), -1.0, -1.0, 1e6), _so(c.get("giay"), 0.0, 0.0, 120.0)
        if not isinstance(local, str) or s0 < 0 or s1 <= s0 or giay < TOI_THIEU:
            an.append({"i": i, "ly_do": "sai"})
            continue
        if can_file and not os.path.isfile(local):
            an.append({"i": i, "ly_do": "mat_file"})
            continue
        best = None
        for k, a, b, t in ks:
            if k.get("nguon") != c.get("nguon") or (c.get("goc") and k.get("goc") != c.get("goc")):
                continue
            ov = min(s1, b) - max(s0, a)
            if a - 0.02 <= s0 < b - 0.05:
                diem = 1000 + ov   # khối chứa giờ bắt đầu câu
            elif ov >= max(0.15, 0.4 * (s1 - s0)):
                diem = ov          # đầu khối bị cắt vào giữa câu: giọng bắt đầu ở đầu khối
            else:
                continue
            if best is None or diem > best[0]:
                best = (diem, k, a, b, t)
        if not best:
            an.append({"i": i, "ly_do": "khoi"})
            continue
        _, k, a, b, t = best
        bd = max(s0, a)
        tv, dai, off, cat = t + bd - a, giay, 0.0, False
        if b < s1 - 0.05 and t + b - a - tv < dai:   # cuối khối bị cắt vào giữa câu: giọng dừng ở cuối khối
            dai, cat = t + b - a - tv, True
        if tv < 0:   # khối thò ra trước đầu video
            off, dai, tv = -tv, dai + tv, 0.0
        if T is not None:
            if tv >= T - 0.05:
                an.append({"i": i, "ly_do": "ngoai"})
                continue
            if tv + dai > T:
                dai, cat = T - tv, True
        if dai < TOI_THIEU:
            an.append({"i": i, "ly_do": "ngan"})
            continue
        out.append({"i": i, "local": local, "t": round(tv, 4), "dai": round(dai, 4), "off": round(off, 4), "cat": cat,
                    "chu": str(c.get("chu") or ""), "khoi": k.get("id")})
    out.sort(key=lambda x: (x["t"], x["i"]))
    return {"dat": out, "an": an}


def tran(ds):
    """Câu giọng dài đè lên câu sau (giờ đã đặt) -> [(câu, giây đè)]."""
    out = []
    for a, b in zip(ds, ds[1:]):
        d = a["t"] + a["dai"] - b["t"]
        if d > 0.05:
            out.append((a, round(d, 2)))
    return out


def vung(tl):
    """Đoạn tiếng gốc được đọc lại -> [(nguon, goc, tu, den, nen)]."""
    gd = tl.get("giong_de")
    out = []
    for v in (gd.get("vung") or []) if isinstance(gd, dict) else []:
        if not isinstance(v, dict) or not isinstance(v.get("nguon"), str):
            continue
        a, b = _so(v.get("tu"), -1.0, -1.0, 1e6), _so(v.get("den"), -1.0, -1.0, 1e6)
        if a < 0 or b - a < 0.01:
            continue
        out.append((v["nguon"], v.get("goc"), a, b, _so(v.get("nen"), 0.0, 0.0, 1.0)))
    return out


def tat_khoi(vs, k, tu, dai):
    """Khối tiếng tách k phát đoạn [tu, tu + dai] của clip: phần nằm trong vùng đọc lại -> [(giây đầu, giây cuối, mức)] theo giờ của
    khối (0 = đầu khối); "het" = cả khối tắt hẳn (bỏ đầu vào); None = khối không bị đọc lại."""
    seg = []
    for ng, goc, a, b, nen in vs:
        if ng != k.get("nguon") or (goc and k.get("goc") != goc):
            continue
        x0, x1 = max(a, tu), min(b, tu + dai)
        if x1 - x0 > 0.01:
            seg.append((round(x0 - tu, 4), round(x1 - tu, 4), nen))
    if not seg:
        return None
    seg.sort()
    if all(n < 0.005 for _, _, n in seg):   # tắt hẳn: phủ kín cả khối thì bỏ khối
        phu, d = 0.0, 0.0
        for a, b, _ in seg:
            if a > phu + 0.02:
                break
            phu = max(phu, b)
        if phu >= dai - 0.02:
            return "het"
    return seg


def gain(ds, ffmpeg, muc=-16.0):
    """dB đưa các câu giọng (nối liền) về mức muc LUFS. Đo lỗi -> -2 dB (file giọng của engine/giong.py chuẩn −14 LUFS)."""
    fs = []
    for x in ds:
        if x["local"] not in fs:
            fs.append(x["local"])
    if not fs:
        return 0.0
    vao = []
    for f in fs[:80]:
        vao += ["-i", f]
    n = len(fs[:80])
    fc = "".join("[%d:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono[m%d];" % (i, i) for i in range(n)) \
        + "".join("[m%d]" % i for i in range(n)) + "concat=n=%d:v=0:a=1,loudnorm=print_format=json[o]" % n
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-nostats"] + vao + ["-filter_complex", fc, "-map", "[o]", "-f", "null", "-"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
        v = float(json.loads(m.group(0))["input_i"]) if m else None
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        v = None
    if v is None or not -70.0 < v < 10.0:
        return muc + 14.0
    return round(max(-20.0, min(20.0, muc - v)), 2)


def dau_vao(ds, T, mi, g_db, he=1.0, khoa=False):
    """Câu giọng đã đặt -> (đầu vào ffmpeg, dòng filter, nhãn trộn, nhãn tín hiệu hạ nhạc | None). Mỗi câu: đúng đoạn file
    (off, dai), mờ ra 0,05s nếu bị cắt, dời tới giây t; gộp amix (normalize=0), đủ dài T, chỉnh dB + hệ số Cân tiếng › Giọng AI."""
    vao, fc = [], []
    for j, x in enumerate(ds):
        vao += (["-ss", "%.4f" % x["off"]] if x["off"] > 0 else []) + ["-i", x["local"]]
        ch = (f"[{mi + j}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS,"
              f"atrim=0:{x['dai']:.4f}")
        if x["cat"]:
            ch += f",afade=t=out:st={max(0.0, x['dai'] - 0.05):.4f}:d=0.05"
        ms = int(round(x["t"] * 1000))
        if ms > 0:
            ch += f",adelay={ms}|{ms}"
        fc.append(ch + f"[gd{j}]")
    n = len(ds)
    g = "".join(f"[gd{j}]" for j in range(n)) + (f"amix=inputs={n}:duration=longest:normalize=0," if n > 1 else "anull,")
    g += f"apad=whole_dur={T:.4f},atrim=0:{T:.4f},volume={g_db:g}dB"
    if he != 1.0:
        g += f",volume={he:g}"
    fc.append(g + (",asplit=2[gde][gdk]" if khoa else "[gde]"))
    return vao, fc, "[gde]", "[gdk]" if khoa else None
