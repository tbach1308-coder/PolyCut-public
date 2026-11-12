#!/usr/bin/env python3
"""Dựng nhanh trong Premiere — BẢN MÁY TIỆM (Claude Code chạy ngay trên máy Windows có Premiere, không MCP, không stage,
không gói tar): từ ke-hoach.json sinh MỘT LẦN đủ mọi thứ — chữ PNG / MOV, âm nhấn, lệnh a, b (chia phần), c, d — và chép
thẳng chữ / âm / giọng vào <thu_muc_may>/chu/ (cùng ổ đĩa), file lệnh vào <thu_muc_may>/lenh-gui/. Gửi bằng gui_lenh.py.

Dùng (3 chế độ; cờ lạ / thừa tham số -> dừng):
  python dung_premiere.py <W> <thu_muc_may> [<thu_muc_font>] [--mo-hinh <sherpa>] [--preset <.epr>]
                          [--limiter] [--bo-qua-canh-bao] [--dung-lai] [--chu-ghep]
  python dung_premiere.py <W> --am <lufs đo được> [--limiter] [--ket-qua <ket-qua-a.json>…] [--preset …]
  python dung_premiere.py <W> --lai-d [--preset <.epr>]
  W              thư mục làm việc có W/ke-hoach.json (ra: W/dtg.json, W/chu/, W/lenh/, W/gui.json)
  thu_muc_may    thư mục phiên bản MỚI của video (vd. E:/Tool/poly-edit/ipad-pro-129/v2): project, chu/, lenh-gui/, mp4.
                 Script dừng nếu thư mục đã có .prproj / .mp4 (dựng chồng làm hỏng timeline), hoặc nằm trong thư mục Poly Bridge
  thu_muc_font   phải có BeVietnamPro-Black/ExtraBold/Bold.ttf; bỏ trống = env POLY_FONT_DIR / <engine>/fonts
  --mo-hinh      có lời nói thật + phụ đề: chạy canh_tu.py trước (giờ từng từ theo lời thật; nhớ kết quả nghe trong
                 W/cache-nghe.json). Bỏ trống = env POLY_MO_HINH / <engine>/mo-hinh nếu có. Phụ đề thiếu `tu`, không giọng AI
                 mà không có máy nghe -> dừng
  --limiter      (plugin ≥ 1.4.0, CHƯA KIỂM TRÊN PREMIERE THẬT; mặc định TẮT) lượt a đặt Hard Limiter từng clip, âm từng clip
                 nhắm −14 LUFS theo I, bỏ trần đỉnh -> không cần vòng chỉnh âm
  --dung-lai     cố ý dựng lại vào thư mục cũ (chỉ khi đã xóa project cũ trên máy; file chữ khác nội dung bị ghi đè)
  --am <lufs>    vòng chỉnh âm sau khi đo bản xuất: sinh cặp [am, d] với id mới (<goc>-am1, <goc>-d2; lần sau am2, d3…);
                 gui.json có tep_am -> gui_lenh.py W --bo am. Âm từng clip (có W/lenh/a.am.json): lấy lại mức lượt a + độ lệch
                 (cộng dồn trong W/am-da-chinh.json). Giọng AI: cần kết quả lượt a (tự đọc ket-qua/<id_do_thang>.json)
  --lai-d        chỉ sinh lại d với id mới (vd. d báo "Không thấy preset": thêm --preset <mẫu khác>); gui_lenh.py W --bo d
Mỗi file lệnh có `dung_neu_loi` cho gui_lenh: b = false (lỗi lẻ vẫn chạy c, d), các lệnh khác = true.

Vì sao sinh trước được: lot_a đặt vào/ra đúng khung nên vị trí từng cảnh trên timeline tính trước chính xác (Premiere
làm tròn xuống theo khung — đã đo khớp tới khung ở v7/v8); ke_hoach.py --duong premiere tính T không trừ chuyển cảnh
(Premiere đặt clip nối tiếp); canh_tu tính giờ phụ đề theo dòng thời gian thật (có cả phần mở đầu montage / thẻ hỏi) và
script kiểm mỗi câu phụ đề nằm trọn trong cảnh của nó; mẫu xuất H.264 của máy anh lưu ở may.json (cạnh file này), lần
đầu chưa có thì lượt c giữ tim_preset, không sinh d: chạy xong c rồi mới sinh d bằng lenh_premiere.py d (script báo).

Mỗi file lệnh ≤ 140 bước và kết bằng luu_project ở BƯỚC CUỐI (bước chỉ đọc như xem_sequence đứng trước) — gui_lenh chỉ tự
chạy lại lệnh như vậy khi Premiere văng. Lượt a dài quá thì chia a1, a2…; b chia b1, b2… (≥ 10 phần thì b01…).
c = cat_sau, vao_ra, luu_project (khung duyệt lấy từ mp4 bằng duyet.py). d = xuat_video ghi_de: true, luu_project.
PNG trùng nội dung (md5) gộp về 1 file đại diện TRƯỚC khi sinh lệnh: chỉ chép file khác nhau.

Gửi — W/gui.json: "tep" = các file lệnh <thu_muc_may>/lenh-gui/<id>.json đúng thứ tự chạy (a…, b…, c, d)
  -> python gui_lenh.py W   (gửi tuần tự vào <POLY_PREMIERE_DIR>/lenh, chờ ket-qua, dừng khi lỗi)
  -> python sau_xuat.py W <gui.mp4_may> --mo-hinh …   (đọc thẳng ket-qua trên máy)
"""
import glob, hashlib, json, os, re, shutil, subprocess, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lenh_premiere as LP  # noqa: E402
import am_tung_clip as ATC  # noqa: E402
import chung  # noqa: E402

TOI_DA_BUOC = 140           # mỗi file lệnh, KỂ CẢ luu_project cuối (Premiere 26.5.2 văng với 1 lệnh 532 bước)
TOI_DA_BUOC_B = 70          # lượt b (dán chữ + keyframe): 28/10 Premiere 26.5.2 + plugin 1.5.0 văng ~1/3 lượt b 140 bước,
                            # lượt 35 bước không văng lần nào -> chia nhỏ, văng thì chỉ chạy lại 1 đoạn ngắn
CHI_DOC = {"xem_sequence", "danh_sach"}  # bước chỉ đọc: dồn về trước luu_project cuối
CO_GIA_TRI = ("--mo-hinh", "--preset", "--am")
NHIEU_GIA_TRI = ("--ket-qua",)
CO_BAT_TAT = ("--bo-qua-canh-bao", "--dung-lai", "--limiter", "--lai-d", "--chu-ghep")  # --chu-ghep: chữ ghép tĩnh kiểu cũ (đường lui)
ID_HOP_LE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
FONT_CAN = ("Black", "ExtraBold", "Bold")  # ve_chu.py + sticker_poly.py dùng
KQ_MAY = chung.KQ_DIR  # kết quả lệnh Poly Bridge trên CHÍNH máy này (env POLY_PREMIERE_DIR\\ket-qua)
DELTA_MIN, DELTA_MAX, DELTA_MAX_LIMITER = -12.0, 6.0, 12.0


def run(args):
    r = subprocess.run([sys.executable] + args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"Lỗi khi chạy {' '.join(args[:2])}:\n{r.stdout[-1500:]}\n{r.stderr[-2500:]}")
    return r.stdout


def doc_doi_so(args):
    """-> (tham số vị trí, tùy chọn, chế độ dung | am | lai_d). Cờ lạ, thiếu / thừa tham số vị trí -> dừng."""
    vt, opt, i = [], {}, 0
    while i < len(args):
        a = args[i]
        if a in CO_GIA_TRI:
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                raise SystemExit(f"{a} thiếu giá trị")
            opt[a] = args[i + 1]
            i += 2
            continue
        if a in NHIEU_GIA_TRI:
            ds, i = [], i + 1
            while i < len(args) and not args[i].startswith("--") and args[i].lower().endswith(".json"):
                ds.append(args[i])
                i += 1
            if not ds:
                raise SystemExit(f"{a} cần ít nhất 1 file .json")
            opt[a] = ds
            continue
        if a in CO_BAT_TAT:
            opt[a] = True
        elif a.startswith("-") and not re.match(r"^-\d", a):
            raise SystemExit(f"Cờ lạ: {a}. Nhận: {', '.join(CO_GIA_TRI + NHIEU_GIA_TRI + CO_BAT_TAT)}")
        else:
            vt.append(a)
        i += 1
    if "--am" in opt and "--lai-d" in opt:
        raise SystemExit("Chọn --am HOẶC --lai-d.")
    che_do = "am" if "--am" in opt else "lai_d" if "--lai-d" in opt else "dung"
    if che_do == "am":
        try:
            float(opt["--am"])
        except ValueError:
            raise SystemExit(f"--am cần số LUFS đo được (vd. -15.6), nhận {opt['--am']}")
    if che_do == "dung" and len(vt) == 2:
        vt.append(chung.FONT_DIR)  # bản máy tiệm: thư mục font mặc định (env POLY_FONT_DIR / engine/fonts)
    can = 3 if che_do == "dung" else 1
    if len(vt) != can:
        raise SystemExit(f"Cần đúng {can} tham số vị trí ({'<W> <thu_muc_may> [<thu_muc_font>]' if can == 3 else '<W>'}), "
                         f"nhận {len(vt)}: {vt}\n\n" + __doc__.split("\n\n")[1])
    sai = [k for k in (("--ket-qua",) if che_do == "dung" else ("--mo-hinh", "--bo-qua-canh-bao", "--dung-lai", "--chu-ghep"))
           if k in opt]
    if che_do == "lai_d" and "--limiter" in opt:
        sai.append("--limiter")
    if sai:
        raise SystemExit(f"Cờ {', '.join(sai)} không dùng ở chế độ này.")
    return vt, opt, che_do


def id_sach(s, toi_da=70):
    """Phần tên trong id lệnh: không dấu, chỉ chữ / số / - . _ (giống cleanId của plugin, gui_lenh không phải đổi).
    ≤ 70 ký tự để id ≤ 92."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn").replace("đ", "d").replace("Đ", "D")
    s = re.sub(r"[^A-Za-z0-9._-]", "_", s)[:toi_da].strip("._")
    return s or "video"


def du_doan_a(tl):
    """Kết quả lượt a dự đoán: vị trí từng cảnh trên timeline theo khung (giống Premiere)."""
    fps = tl["fps"]
    out, o = [], 0.0
    for s in tl["shots"]:
        d = (int(round(s["den"] * fps)) - int(round(s["tu"] * fps))) / fps
        out.append({"lenh": "dat_clip", "ok": True,
                    "ket_qua": {"tu": s["tu"], "tren_timeline": {"track": "hinh", "bat_dau": round(o, 6), "ket_thuc": round(o + d, 6)}}})
        o += d
    return {"buoc": out}


def chia(buoc, toi_da=TOI_DA_BUOC):
    """Chia bước thành các phần ≤ toi_da bước; MỖI phần kết bằng luu_project ở bước cuối. luu_project giữa chừng bị bỏ
    (thay bằng luu cuối mỗi phần); bước chỉ đọc ở cuối lệnh gốc (xem_sequence) đứng ngay trước luu_project cuối."""
    than = [b for b in buoc if b["lenh"] != "luu_project"]
    duoi = []
    while than and than[-1]["lenh"] in CHI_DOC:
        duoi.insert(0, than.pop())
    n = toi_da - 1
    ds = than + duoi
    phan = [ds[i:i + n] for i in range(0, len(ds), n)] or [[]]
    if len(phan) > 1 and all(s["lenh"] in CHI_DOC for s in phan[-1]):  # phần cuối chỉ còn bước đọc: mượn 1 bước làm
        phan[-1] = phan[-2][-1:] + phan[-1]
        phan[-2] = phan[-2][:-1]
    return [p + [{"lenh": "luu_project"}] for p in phan]


def dat_ten_phan(goc, lot, cmd, noi="", dung_neu_loi=None):
    """1 phần -> '<goc>-a'; nhiều phần -> a1, a2… (≥ 10 phần: a01…) để thứ tự tên file đúng thứ tự chạy.
    noi: chuỗi chen giữa tên lượt và số phần (vd. 'am1' + '-' -> am1-1, am1-2)."""
    phan = chia(cmd["buoc"], TOI_DA_BUOC_B if lot == "b" else TOI_DA_BUOC)
    w = len(str(len(phan)))
    out = []
    for i, p in enumerate(phan, 1):
        x = {k: v for k, v in cmd.items() if k not in ("id", "buoc")}
        x["id"] = f"{goc}-{lot}" if len(phan) == 1 else f"{goc}-{lot}{noi}{i:0{w}d}"
        # MCP: b lỗi lẻ 1 bước chữ / keyframe vẫn gửi tiếp c, d (sửa riêng sau); lệnh khác lỗi thì dừng (plugin bỏ qua trường lạ)
        x["dung_neu_loi"] = (lot != "b") if dung_neu_loi is None else dung_neu_loi
        x["buoc"] = p
        out.append(x)
    return out


def kiem_lenh(cmds, theo_ten=True):
    for x in cmds:  # hợp đồng với MCP Poly Bridge
        if not ID_HOP_LE.match(x["id"]) or x["id"].endswith("."):
            raise SystemExit(f"id lệnh không hợp lệ: {x['id']}")
        if len(x["buoc"]) > TOI_DA_BUOC:
            raise SystemExit(f"{x['id']}: {len(x['buoc'])} bước > {TOI_DA_BUOC}")
        if x["buoc"][-1]["lenh"] != "luu_project" or any(s["lenh"] == "luu_project" for s in x["buoc"][:-1]):
            raise SystemExit(f"{x['id']}: luu_project phải là bước cuối và chỉ ở cuối")
        if not isinstance(x.get("dung_neu_loi"), bool):
            raise SystemExit(f"{x['id']}: thiếu dung_neu_loi")
    if theo_ten and [x["id"] for x in cmds] != sorted(x["id"] for x in cmds):
        raise SystemExit("Thứ tự tên file lệnh khác thứ tự chạy: " + ", ".join(x["id"] for x in cmds))


def gop_png(lopj, chu_d):
    """PNG trùng nội dung (md5) -> 1 file đại diện (tên nhỏ nhất theo thứ tự chữ). Đổi `ten` trong lop_premiere TRƯỚC
    khi sinh lệnh: lệnh dùng đúng hình đó, cùng giờ, chỉ khác tên file. Trả về {tên bỏ: tên đại diện}."""
    lp = LP.lop_premiere(lopj)
    dai_dien, doi = {}, {}
    for n in sorted({l["ten"] for l in lp}):
        h = hashlib.md5(open(os.path.join(chu_d, n), "rb").read()).hexdigest()
        if h in dai_dien:
            doi[n] = dai_dien[h]
        else:
            dai_dien[h] = n
    for l in lp:
        if l["ten"] in doi:
            l["ten"] = doi[l["ten"]]
            if l.get("png"):
                l["png"] = os.path.join(os.path.dirname(l["png"]), l["ten"])
    return doi


def kiem_giong(plan):
    """Giọng AI: Premiere nhập đúng giong.file. Bản máy tiệm: có giong.local khác giong.file thì chép sang giong.file;
    sau đó giong.file phải có thật. Trả về (local, file) khi cần chép, None khi không có giọng / đã nằm sẵn."""
    g = plan.get("giong")
    if not g:
        return None
    gf, loc = (g.get("file") or "").strip(), (g.get("local") or "").strip()
    if not gf:
        raise SystemExit("giong.file trống: cần đường dẫn file giọng trên máy (Premiere nhập file này).")
    if loc and os.path.isfile(loc) and os.path.abspath(loc) != os.path.abspath(gf):
        return loc, gf
    if not os.path.isfile(gf):
        raise SystemExit(f"Không thấy file giọng {gf}.")
    return None


def _thu_muc(p):
    s = re.sub(r"[\\/]+", "/", str(p or "")).rstrip("/")
    return s.lower() if chung.LA_WIN else s


def glob_kh(goc):
    return glob.glob(os.path.join(glob.escape(goc), "*", "ke-hoach.json")) + \
        glob.glob(os.path.join(glob.escape(goc), "*", "*", "ke-hoach.json"))


def kiem_thu_muc_moi(plan, W, mdir):
    """Mỗi lần dựng phải là thư mục phiên bản MỚI (dựng chồng làm hỏng timeline; gui_lenh từ chối tao_project vào
    .prproj đã có). Trả về (lỗi, cảnh báo)."""
    loi, cb = [], []
    m = _thu_muc(mdir)
    ten = plan.get("ten", "")
    # 1. thư mục máy (ngay trên máy này) đã có project / mp4 của lần dựng trước
    if os.path.isdir(mdir):
        cu = [n for n in os.listdir(mdir) if n.lower().endswith((".prproj", ".mp4"))]
        if cu:
            loi.append(f"{mdir} đã có bản dựng trước ({', '.join(sorted(cu)[:3])})")
    # 2. kế hoạch khác (cạnh W) đã dựng vào cùng thư mục
    W_abs = os.path.abspath(W)
    for p in sorted(set(glob_kh(os.path.dirname(W_abs)))):
        if os.path.dirname(os.path.abspath(p)) == W_abs:
            continue
        try:
            k = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if _thu_muc((k.get("ra") or {}).get("thu_muc")) == m and os.path.exists(os.path.join(os.path.dirname(p), "gui.json")):
            loi.append(f"kế hoạch {p} đã dựng vào {mdir}")
    # 3. lịch sử kiểu: tên video đã giao -> có thể quên đổi phiên bản (project = <thu_muc_may>/<ten>.prproj)
    try:
        ls = json.load(open(os.path.join(HERE, "lich-su-kieu.json"), encoding="utf-8"))
        if any(h.get("ten") == ten for h in ls):
            cb.append(f"tên '{ten}' đã có trong lich-su-kieu.json (video đã giao) — nhớ đổi phiên bản trong ten / ra.ten_file")
    except (OSError, ValueError):
        pass
    if _thu_muc((plan.get("ra") or {}).get("thu_muc")) not in ("", m):
        cb.append(f"ra.thu_muc trong kế hoạch ({plan['ra']['thu_muc']}) khác thu_muc_may ({mdir}) — lệnh dùng thu_muc_may")
    return loi, cb


def kiem_dau_vao(plan, mdir, font, mo_hinh):
    loi = []
    if not os.path.isabs(mdir):
        loi.append(f"thu_muc_may = {mdir}: phải là đường dẫn đầy đủ (vd. E:/Tool/poly-edit/<ten>/v1)")
    elif chung.trong(chung.PREMIERE_DIR, mdir):
        loi.append(f"thu_muc_may = {mdir}: không được nằm trong thư mục Poly Bridge ({chung.PREMIERE_DIR})")
    thieu = [f"BeVietnamPro-{w}.ttf" for w in FONT_CAN if not os.path.isfile(os.path.join(font, f"BeVietnamPro-{w}.ttf"))]
    if thieu:
        loi.append(f"thư mục font {font} thiếu {', '.join(thieu)} (chạy CAI-DAT.bat để tải font)")
    nguon = plan.get("nguon") or {}
    for c in plan.get("canh") or []:
        n = nguon.get(c.get("file")) or {}
        p = n.get("local") or c.get("file")
        if not p or not os.path.isfile(p):
            loi.append(f"không thấy clip {c.get('file')} (nguon.local = {n.get('local')})")
            break
    pd = plan.get("phu_de") or []
    thieu_tu = [i + 1 for i, p in enumerate(pd) if not p.get("tu")]
    if thieu_tu and not plan.get("giong") and not mo_hinh:
        loi.append(f"{len(thieu_tu)} câu phụ đề chưa có giờ từng từ `tu` (câu {thieu_tu[:8]}…) mà không có máy nghe: chữ sẽ "
                   "chia theo số ký tự, trễ 0,5–0,9s so với lời. Thêm --mo-hinh <thư mục sherpa> (hoặc chạy CAI-DAT.bat).")
    if loi:
        raise SystemExit("Dừng:\n- " + "\n- ".join(loi))


def khoang_canh(tl):
    """{chỉ số cảnh gốc: (bắt đầu, hết)} trên timeline thật (đặt nối tiếp theo khung như Premiere)."""
    fps, k, out = tl["fps"], 0, {}
    for s in tl["shots"]:
        db = int(round((s.get("dong_bang") or 0.0) * fps))
        n = int(round(s["dur"] * fps)) if s.get("the_hoi") else int(round(s["den"] * fps)) - int(round(s["tu"] * fps)) + db
        if s["canh"] >= 0:
            a = out.get(s["canh"], ((k + db) / fps, None))[0]
            out[s["canh"]] = (a, (k + n) / fps)
        k += n
    return out


def kiem_phu_de_trong_canh(tl):
    """Mỗi câu phụ đề (tiếng nói thật) phải nằm trọn trong cảnh của nó trên timeline thật. Trả về danh sách lỗi."""
    sp = khoang_canh(tl)
    tol = 0.5 / tl["fps"] + 1e-3
    loi = []
    for i, p in enumerate(tl.get("phu_de") or []):
        c = p.get("canh")
        if not (isinstance(c, int) and c in sp):
            c = next((x for x, (a, b) in sorted(sp.items()) if a - 1e-6 <= p["t0"] + 0.01 < b), None)
        chu = str(p.get("chu", ""))[:30]
        if c is None:
            loi.append(f"câu {i + 1} '{chu}' ({p['t0']}–{p['t1']}s) không nằm trong cảnh gốc nào (vùng mở đầu montage / thẻ hỏi)")
            continue
        a, b = sp[c]
        if p["t0"] < a - tol or p["t1"] > b + tol:
            loi.append(f"câu {i + 1} '{chu}' {p['t0']}–{p['t1']}s vượt cảnh {c + 1} ({a:.3f}–{b:.3f}s)")
    return loi


def tom_tat_canh_tu(out):
    """Một dòng cho mọi cảnh (khớp / tiếng), cảnh < 70%, phần mở đầu, cache. Trả (dòng, dữ liệu cho gui.json)."""
    try:
        j = json.loads(out)
    except ValueError:
        return "canh_tu: " + out.strip()[-300:], None
    ds = j.get("canh") or []
    k, t = sum(x["khop"] for x in ds), sum(x["tieng"] for x in ds)
    thap = [f"{x['canh']} ({x['khop']}/{x['tieng']})" for x in ds if x["tieng"] and x["khop"] / x["tieng"] < 0.7]
    thap += [f"{x['canh']} (không nghe được)" for x in ds if not x["tieng"]]
    dong = (f"canh_tu: {len(ds)} cảnh, khớp {k}/{t} tiếng ({round(100 * k / t) if t else 0}%), mở đầu +{j.get('mo_dau_giay', 0)}s, "
            f"cache {j.get('cache', {}).get('trung', 0)}/{len(ds)}; từng cảnh: "
            + " ".join(f"{x['canh']}:{x['khop']}/{x['tieng']}" for x in ds) + f"; dưới 70%: {', '.join(thap) or 'không'}")
    return dong, {"canh": ds, "khop": k, "tieng": t, "mo_dau_giay": j.get("mo_dau_giay"), "cache": j.get("cache"),
                  "duoi_70": thap, "bao": j.get("bao")}


def doi_ten_am_cu(W):
    """Lượt a mới ở mức gốc -> mức chỉnh âm của bản trước không còn đúng: đổi tên am-da-chinh.json (giữ lại để tra)."""
    p = os.path.join(W, "am-da-chinh.json")
    if not os.path.exists(p):
        return None
    goc_cu = None
    try:
        goc_cu = json.load(open(os.path.join(W, "gui.json"), encoding="utf-8")).get("goc_id")
    except (OSError, ValueError):
        pass
    goc_cu = goc_cu or time.strftime("%Y%m%d-%H%M%S", time.localtime(os.path.getmtime(p)))
    moi = os.path.join(W, f"am-da-chinh.{id_sach(goc_cu, 90)}.json")
    os.replace(p, moi)
    return moi


def _md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def chep_tai_san(ds, ghi_de=False):
    """Bản máy tiệm thay cho gói tar + MCP bung gói: chép thẳng [(nguồn, đích)] (chữ PNG / MOV, âm nhấn, giọng) vào thư mục
    video trên cùng máy. Đích đã có giống hệt -> bỏ qua; khác nội dung -> dừng (dựng vào phiên bản mới), trừ ghi_de
    (--dung-lai). Ghi tạm rồi đổi tên: Premiere không bao giờ đọc file chép dở."""
    moi = giong = 0
    mb = 0.0
    for src, dst in ds:
        mb += os.path.getsize(src) / 1e6
        if os.path.abspath(src) == os.path.abspath(dst):
            giong += 1
            continue
        if os.path.exists(dst):
            if os.path.getsize(dst) == os.path.getsize(src) and _md5(dst) == _md5(src):
                giong += 1
                continue
            if not ghi_de:
                raise SystemExit(f"{dst} đã có mà khác nội dung — dựng vào thư mục phiên bản mới (vd. v2), hoặc --dung-lai.")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        tam = dst + ".part"
        shutil.copyfile(src, tam)
        os.replace(tam, dst)
        moi += 1
    return {"so_file": len(ds), "chep_moi": moi, "giong_het_bo_qua": giong, "MB": round(mb, 2)}


gui_dir = lambda mdir, x: chung.xuoi(mdir + "/lenh-gui/" + x["id"] + ".json")  # gui_lenh.py đọc theo gui.tep
kq_dir = lambda x: chung.xuoi(os.path.join(KQ_MAY, x["id"] + ".json"))


def ghi_lenh(mdir, lenh_d, cmd, ten_w):
    """File lệnh -> <thu_muc_may>/lenh-gui/<id>.json (để gửi) + W/lenh/<tên ngắn>.json (để tra)."""
    p = gui_dir(mdir, cmd)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(cmd, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(cmd, open(os.path.join(lenh_d, ten_w + ".json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return p


def lot_d_moi(tl, mdir, goc, so, preset):
    res_c = {"buoc": [{"lenh": "tim_preset", "ok": True, "ket_qua": {"preset": [preset]}}]} if preset else {"buoc": []}
    d = LP.lot_d(tl, mdir, res_c)  # không có tim_preset -> mẫu xuất trong may.json
    d["buoc"][0]["ghi_de"] = True  # thư mục video luôn mới / xuất lại: chạy lại sau khi văng không lỗi "File đã có"
    d["buoc"].append({"lenh": "luu_project"})
    d["id"] = f"{goc}-d" if so == 1 else f"{goc}-d{so}"
    d["dung_neu_loi"] = True
    return d


# ---------------------------------------------------------------- dựng mới
def dung(vt, opt):
    W, font = vt[0], vt[2]
    mdir = chung.xuoi(os.path.abspath(vt[1])).rstrip("/")  # kiểu E:/Tool/... như lệnh Poly Bridge cần
    mo_hinh = opt.get("--mo-hinh")
    if mo_hinh and not chung.co_mo_hinh(mo_hinh):
        raise SystemExit(f"--mo-hinh {mo_hinh}: không thấy mô hình sherpa (tokens.txt, encoder*.onnx) — chạy CAI-DAT.bat.")
    mo_hinh = mo_hinh or chung.mo_hinh_hoac_none()  # bản máy tiệm: mặc định env POLY_MO_HINH / engine/mo-hinh
    lim = bool(opt.get("--limiter"))
    kh_p, dtg_p, chu_d = os.path.join(W, "ke-hoach.json"), os.path.join(W, "dtg.json"), os.path.join(W, "chu")
    lenh_d = os.path.join(W, "lenh")
    plan = json.load(open(kh_p, encoding="utf-8"))
    kiem_dau_vao(plan, mdir, font, mo_hinh)
    giong = kiem_giong(plan)
    loi_tm, bao = kiem_thu_muc_moi(plan, W, mdir)
    if loi_tm and "--dung-lai" not in opt:
        raise SystemExit("thu_muc_may phải là thư mục MỚI (gui_lenh từ chối tao_project vào .prproj đã có; dựng chồng làm "
                         "hỏng timeline):\n- " + "\n- ".join(loi_tm) + "\nĐổi sang thư mục phiên bản mới (vd. …/v2). Chỉ khi đã "
                         "xóa project cũ trên máy và cố ý dựng lại: thêm --dung-lai.")
    # 1. giờ từng từ theo lời thật (theo dòng thời gian thật, nhớ kết quả nghe)
    canh_tu = None
    if mo_hinh and plan.get("phu_de") and not plan.get("giong"):
        dong, canh_tu = tom_tat_canh_tu(run([os.path.join(HERE, "canh_tu.py"), kh_p, mo_hinh, "--duong", "premiere"]))
        bao.append(dong)
        plan = json.load(open(kh_p, encoding="utf-8"))
    # 2. kế hoạch (đường Premiere: chuyển cảnh không làm timeline ngắn lại) + kiểm phụ đề nằm trọn trong cảnh
    run([os.path.join(HERE, "ke_hoach.py"), kh_p, dtg_p, "--duong", "premiere"])
    tl = LP.load(dtg_p)
    if tl.get("phu_de") and not tl.get("giong"):
        loi_pd = kiem_phu_de_trong_canh(tl)
        if loi_pd:
            raise SystemExit("Phụ đề không nằm trọn trong cảnh của nó (chữ sẽ lệch lời):\n- " + "\n- ".join(loi_pd[:12])
                             + ("\n…" if len(loi_pd) > 12 else "") + "\nChạy lại với --mo-hinh (canh_tu tính theo dòng thời gian "
                             "thật), hoặc sửa t0/t1 / tách câu vắt qua chỗ cắt.")
    # 3. chữ ∥ đo âm từng clip (chỉ cần các bước dat_clip cảnh, không cần PNG)
    can_am = not tl.get("giong") and LP.co_tieng_goc(tl)
    clips = ATC.clip_canh(LP.lot_a(tl, {"lop_premiere": []}, mdir)["buoc"])
    with ThreadPoolExecutor(2) as ex:
        f_ve = ex.submit(run, [os.path.join(HERE, "ve_chu.py"), dtg_p, chu_d, font] + (["--chu-ghep"] if opt.get("--chu-ghep") else []))
        f_am = ex.submit(ATC.do_clips, plan, clips, -1.7, -14.0, 2, lim) if can_am else None
        v = json.loads(f_ve.result().strip().splitlines()[-1])
        rows = f_am.result() if f_am else None
    lop_p = os.path.join(chu_d, "lop-chu.json")
    lopj = LP.load(lop_p)
    canh_bao = (lopj.get("canh_bao") or []) + (v.get("canh_bao") or [])
    if canh_bao and "--bo-qua-canh-bao" not in opt:
        raise SystemExit("ve_chu cảnh báo (sửa rồi chạy lại, hoặc --bo-qua-canh-bao):\n" + "\n".join(map(str, canh_bao)))
    # 4. gộp PNG trùng nội dung — ghi lại lop-chu.json để lệnh sinh sau (lenh_premiere.py b/am…) cũng dùng tên đại diện
    so_png_goc = len({l["ten"] for l in LP.lop_premiere(lopj)})
    doi = gop_png(lopj, chu_d)
    lopj["gop_png"] = doi
    json.dump(lopj, open(lop_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # 5. lệnh — từ đây là bản dựng mới: dọn lệnh của lần sinh trước, cất mức chỉnh âm của bản trước (B6)
    os.makedirs(lenh_d, exist_ok=True)
    for n in os.listdir(lenh_d):  # tên phần có thể khác lần trước -> bỏ hết, tránh gửi nhầm
        if re.match(r"^([abcd]|am)[\d-]*(\.am)?\.json$", n):
            os.remove(os.path.join(lenh_d, n))
    cu = doi_ten_am_cu(W)
    if cu:
        bao.append(f"am-da-chinh.json của bản trước -> {os.path.basename(cu)} (lượt a mới ở mức gốc)")
    goc = LP.stamp() + "-" + id_sach(tl["ten"])
    a = LP.lot_a(tl, lopj, mdir)
    seq = LP.seq_name(tl)
    if rows:  # âm lượng từng clip (tiếng nói thật)
        ATC.chen_vao_a(a, ATC.buoc_am(seq, rows, lim))
        json.dump(rows, open(os.path.join(lenh_d, "a.am.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        bao.append(f"am: {len(rows)} clip, dB {min(r['db'] for r in rows):+.1f}…{max(r['db'] for r in rows):+.1f}"
                   + (" (limiter, nhắm −14)" if lim else " (trần đỉnh −1,7: bản xuất ≈ −15,6 LUFS; đúng −14 cần --limiter)"))
    elif lim and (LP.co_tieng_goc(tl) or tl.get("giong")):
        ATC.chen_vao_a(a, LP.limiter_steps(tl, 0.0))  # giọng AI: limiter cả track (trần), mức giữ như cũ
    if lim:
        json.dump({"delta": 0.0, "lufs_do": None, "delta_truoc": 0.0, "luc": LP.stamp(), "limiter": True, "tung_clip": bool(rows)},
                  open(os.path.join(W, "am-da-chinh.json"), "w", encoding="utf-8"))
    json.dump(a, open(os.path.join(lenh_d, "a.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)  # a ĐẦY ĐỦ
    res_a = du_doan_a(tl)
    T = res_a["buoc"][-1]["ket_qua"]["tren_timeline"]["ket_thuc"]
    if abs(T - tl["T"]) > 0.5 / tl["fps"]:
        raise SystemExit(f"T kế hoạch {tl['T']}s khác T trên timeline Premiere {T}s — thẻ kết / chữ cuối sẽ lệch. "
                         "Kiểm ke_hoach.py --duong premiere.")
    b = LP.lot_b(tl, lopj, mdir, res_a)
    am_nhan_ds = [x for x in b["buoc"] if x["lenh"] == "dat_clip" and str(x.get("file", "")).lower().endswith(".wav")]
    c = LP.lot_c(tl, res_a, mdir)
    may_p = os.path.join(HERE, "may.json")
    may = json.load(open(may_p, encoding="utf-8")) if os.path.exists(may_p) else {}
    if opt.get("--preset"):
        may["preset_h264"] = [opt["--preset"]]
    # khung duyệt lấy từ mp4 (duyet.py, phủ cả video) -> bỏ xuat_khung; mẫu xuất có trong may.json -> bỏ tim_preset
    giu = ("cat_sau", "vao_ra") if may.get("preset_h264") else ("cat_sau", "vao_ra", "tim_preset")
    c["buoc"] = [x for x in c["buoc"] if x["lenh"] in giu] + [{"lenh": "luu_project"}]
    c["id"] = goc + "-c"
    c["dung_neu_loi"] = True  # cắt / vào-ra lỗi thì gui_lenh không gửi d (xuất sai đoạn)
    d = lot_d_moi(tl, mdir, goc, 1, opt.get("--preset")) if may.get("preset_h264") else None
    if not d:
        bao.append("CHƯA có may.json (mẫu xuất): lượt c giữ tim_preset; chạy xong c thì `lenh_premiere.py d … <ket-qua-c>` "
                   "và lưu danh sách preset vào may.json.")
    bao.append(f"chữ: {lopj.get('che_do_premiere', 'ghep')}, {lopj.get('so_track_hinh', 3)} track hình"
               + (f", âm nhấn {len(am_nhan_ds)} lần" if am_nhan_ds else ""))
    phan_a = dat_ten_phan(goc, "a", a)
    phan_b = dat_ten_phan(goc, "b", b)
    sau = phan_b + [c] + ([d] if d else [])
    tat_ca = phan_a + sau
    kiem_lenh(tat_ca)
    do_thang = next((x["id"] for x in phan_a if any(s["lenh"] == "am_luong" and s.get("do_thang") for s in x["buoc"])), None)
    # 6. bản máy tiệm: chép thẳng chữ / âm nhấn / giọng vào thư mục video (cùng máy), ghi file lệnh vào lenh-gui/
    pngs = sorted({l["ten"] for l in LP.lop_premiere(lopj)})  # gồm cả .mov chữ động (hoat_hinh)
    am_nhan = sorted((lopj.get("am_nhan") or {}).values())  # âm nhấn tự tổng hợp (ve_chu -> am_nhan.py), cùng thư mục chu/
    ds_chep = [(os.path.join(chu_d, n), chung.duong(mdir + "/chu/" + n)) for n in pngs + am_nhan]
    if giong:
        ds_chep.append((giong[0], chung.duong(giong[1])))
        bao.append(f"giọng: chép {giong[0]} -> {giong[1]}")
    # chưa có project trong thư mục (chưa gửi lệnh nào) thì sửa chữ rồi sinh lại vào CÙNG thư mục được: chép đè chữ cũ
    chua_dung = not os.path.exists(chung.duong(LP.project_path(tl, mdir)))
    tai_san = chep_tai_san(ds_chep, ghi_de=bool(opt.get("--dung-lai")) or chua_dung)
    lg = chung.duong(mdir + "/lenh-gui")
    if os.path.isdir(lg):  # id có giờ -> file lệnh lần sinh trước (cùng thư mục, --dung-lai) không còn dùng: cất sang _cu/
        for n in os.listdir(lg):
            if n.endswith(".json"):
                os.makedirs(os.path.join(lg, "_cu"), exist_ok=True)
                os.replace(os.path.join(lg, n), os.path.join(lg, "_cu", n))
    tep = [ghi_lenh(mdir, lenh_d, x, x["id"].rsplit("-", 1)[1]) for x in tat_ca]
    mp4_may = chung.xuoi(d["buoc"][0]["dau_ra"]) if d else \
        ((tl.get("ra") or {}).get("ten_file") and chung.xuoi(mdir + "/" + tl["ra"]["ten_file"]))
    gui = {
        "ten": tl["ten"], "T": round(T, 3), "goc_id": goc, "thu_muc_may": mdir, "limiter": lim,
        "tep": tep,  # gửi bằng: python gui_lenh.py <W>   (tuần tự a…, b…, c, d)
        "tai_san": tai_san,
        "id_a": [x["id"] for x in phan_a], "id_b": [x["id"] for x in phan_b],
        "id_do_thang": do_thang,  # kết quả của lệnh này có thang âm lượng (cho lenh_premiere.py am / dung_premiere --am)
        "id_cuoi": sau[-1]["id"],
        "ket_qua_may": [kq_dir(x) for x in tat_ca],  # sau_xuat đọc thẳng (bước lỗi + so vị trí cảnh)
        "mp4_may": mp4_may,
        "prproj": chung.xuoi(LP.project_path(tl, mdir)),
        "khung_may": None,  # lượt c không còn xuất khung: khung duyệt lấy từ mp4 (sau_xuat.py -> duyet/khung-chu.jpg)
        "png_gop": doi, "canh_tu": canh_tu, "so_am": 0, "so_d": 1 if d else 0,
        "poly_bridge": chung.PREMIERE_DIR,
    }
    json.dump(gui, open(os.path.join(W, "gui.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"T": gui["T"], "png": len(pngs), "png_truoc_gop": so_png_goc, "tai_san": tai_san,
                      "a": [(x["id"].rsplit("-", 1)[1], len(x["buoc"])) for x in phan_a],
                      "sau": [(x["id"].rsplit("-", 1)[1], len(x["buoc"])) for x in sau], "gui": os.path.join(W, "gui.json"),
                      "mp4_may": mp4_may, "bao": bao}, ensure_ascii=False, indent=0))


# ---------------------------------------------------------------- chỉnh âm / xuất lại
def tim_ket_qua_a(gui, ds_file):
    """Kết quả lượt a có thang âm lượng: file --ket-qua, hoặc ket-qua/<id_do_thang>*.json trên máy này (kể cả -r2… / -lai1…)."""
    ung = list(ds_file or [])
    if not ung and gui.get("id_do_thang"):
        ung = sorted(glob.glob(os.path.join(glob.escape(KQ_MAY), gui["id_do_thang"] + "*.json")), key=os.path.getmtime, reverse=True)
    for p in ung:
        try:
            r = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if LP.thang_tu(r):
            return r, p
    return None, None


def tinh_delta(da_luu, lufs, lim):
    """Giống lenh_premiere.lot_am: cộng dồn độ lệch; chạy lại CÙNG số đo thì tính lại từ mức trước lần đó."""
    cu = da_luu.get("delta", 0.0)
    them = -14.0 - lufs
    if abs(them) < 1.0 and not (lim and not da_luu.get("limiter")):
        raise SystemExit(f"Độ lớn {lufs} LUFS đã trong khoảng -14 ±1, không cần chỉnh.")
    goc = cu
    try:
        if da_luu.get("lufs_do") not in (None, "-") and float(da_luu["lufs_do"]) == lufs and "delta_truoc" in da_luu:
            goc = da_luu["delta_truoc"]
    except (TypeError, ValueError):
        pass
    tran = DELTA_MAX_LIMITER if lim else DELTA_MAX
    return max(DELTA_MIN, min(tran, goc + them)), goc


def sinh_lai(vt, opt, che_do):
    W = vt[0]
    gp = os.path.join(W, "gui.json")
    try:
        gui = json.load(open(gp, encoding="utf-8"))
    except (OSError, ValueError):
        raise SystemExit(f"Không đọc được {gp}: chạy dung_premiere chế độ dựng trước.")
    if not gui.get("thu_muc_may") or not gui.get("goc_id"):
        raise SystemExit("gui.json của bản cũ (thiếu thu_muc_may / goc_id): chạy lại dung_premiere chế độ dựng.")
    mdir, goc = gui["thu_muc_may"], gui["goc_id"]
    dtg_p, lenh_d = os.path.join(W, "dtg.json"), os.path.join(W, "lenh")
    tl = LP.load(dtg_p)
    bao, cmds = [], []
    if che_do == "am":
        lufs = float(opt["--am"])
        k = gui.get("so_am", 0) + 1
        rows_p = os.path.join(lenh_d, "a.am.json")
        luu_p = os.path.join(W, "am-da-chinh.json")
        da_luu = json.load(open(luu_p, encoding="utf-8")) if os.path.exists(luu_p) else {}
        lim = bool(opt.get("--limiter")) or bool(da_luu.get("limiter"))
        if os.path.exists(rows_p) and not tl.get("giong"):
            rows = json.load(open(rows_p, encoding="utf-8"))
            kep, goc_d = tinh_delta(da_luu, lufs, lim)
            moi = ATC.chinh_lai(rows, kep, lim)
            json.dump({"delta": kep, "lufs_do": str(lufs), "delta_truoc": goc_d, "luc": LP.stamp(), "limiter": lim, "tung_clip": True},
                      open(luu_p, "w", encoding="utf-8"))
            am = {"project": LP.project_path(tl, mdir), "song_song": True,
                  "buoc": ATC.buoc_am(LP.seq_name(tl), moi, lim, ca_muc_0=True) + [{"lenh": "luu_project"}]}
            # ước độ lớn bản xuất mới: cộng năng lượng từng clip (độ dài × 10^((I + mức)/10)), bỏ clip im lặng
            w = [((r["den"] - r["tu"]) * 10 ** ((r["I"] + r["db"]) / 10), m["db"] - r["db"]) for r, m in zip(rows, moi) if r["I"] > -60]
            tang = 10 * __import__("math").log10(sum(a * 10 ** (x / 10) for a, x in w) / sum(a for a, _ in w)) if w else 0.0
            bi_giu = sum(1 for r, m in zip(rows, moi) if round(m["db"] - r["db"], 1) < round(kep, 1))
            bao.append(f"am: từng clip, lệch {kep:+.1f} dB (đo {lufs} LUFS){', limiter' if lim else ''}; "
                       f"dB {min(r['db'] for r in moi):+.1f}…{max(r['db'] for r in moi):+.1f}; ước bản xuất ≈ {lufs + tang:.1f} LUFS"
                       + (f"; {bi_giu}/{len(rows)} clip bị trần đỉnh giữ — muốn đúng −14 cần --limiter (plugin 1.4.0)"
                          if not lim and bi_giu else ""))
        else:  # giọng AI / lệnh cũ: mức cả track, cần thang từ kết quả lượt a
            res_a, p = tim_ket_qua_a(gui, opt.get("--ket-qua"))
            if not res_a:
                raise SystemExit("Cần kết quả lượt a có thang âm lượng: không thấy " + os.path.join(KQ_MAY, str(gui.get("id_do_thang"))) +
                                 ".json — truyền --ket-qua <file>.")
            am = LP.lot_am(tl, mdir, res_a, str(lufs), dtg_p)  # đọc --limiter từ dòng lệnh; ghi am-da-chinh.json
            bao.append(f"am: cả track theo kết quả {os.path.basename(p)}")
        am["dung_khi_loi"] = True
        cmds += dat_ten_phan(goc, f"am{k}", am, noi="-", dung_neu_loi=True)
        gui["so_am"] = k
    so_d = gui.get("so_d", 1) + 1
    d = lot_d_moi(tl, mdir, goc, so_d, opt.get("--preset"))
    cmds.append(d)
    gui["so_d"] = so_d
    kiem_lenh(cmds, theo_ten=False)
    tep = [ghi_lenh(mdir, lenh_d, x, x["id"][len(goc) + 1:]) for x in cmds]
    khoa = "am" if che_do == "am" else "d"
    gui[f"tep_{khoa}"] = tep  # gửi bằng: python gui_lenh.py <W> --bo am|d
    gui["ket_qua_may"] = list(dict.fromkeys((gui.get("ket_qua_may") or []) + [kq_dir(x) for x in cmds]))
    gui["mp4_may"] = chung.xuoi(d["buoc"][0]["dau_ra"])
    gui[f"id_cuoi_{khoa}"] = d["id"]  # id_cuoi giữ nguyên = lệnh cuối của bản dựng chính
    json.dump(gui, open(gp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"lenh": [(x["id"][len(goc) + 1:], len(x["buoc"])) for x in cmds], f"tep_{khoa}": tep,
                      "preset": d["buoc"][0]["preset"], "mp4_may": gui["mp4_may"], "bao": bao}, ensure_ascii=False, indent=0))


def main():
    vt, opt, che_do = doc_doi_so(sys.argv[1:])
    if che_do == "dung":
        dung(vt, opt)
    else:
        sinh_lai(vt, opt, che_do)


if __name__ == "__main__":
    main()
