#!/usr/bin/env python3
"""Sau khi Premiere xuất xong: chạy SONG SONG duyet.py (giải mã 1 lượt) và đo độ khớp chữ – lời trên bản xuất, ghi hết
ra W/ho-so.json cho người duyệt độc lập đọc (không phải đo lại). Bản nhẹ chỉ làm khi có --nhe (sau khi duyệt xong).

Dùng:  python3 sau_xuat.py <W> <mp4> [--mo-hinh <sherpa>] [--ket-qua <ket-qua/<id>.json>…] [--nhe [<ra.mp4>]]
  W: thư mục làm việc (dtg.json, chu/lop-chu.json, ke-hoach.json, gui.json). Ra: W/duyet/ (duyet.json + ảnh), W/ho-so.json.
  --ket-qua: file kết quả lệnh Premiere (a…, b…, c, d). Không ghi thì tự đọc thẳng thư mục kết quả của Poly Bridge trên
     máy này (env POLY_PREMIERE_DIR + /ket-qua, theo gui.ket_qua_may, kể cả bản gửi lại -r2… / -lai1…). Ghi vào ho-so: bước
     lỗi từng lệnh, so vị trí cảnh lượt a (thật) với dự đoán.
  --nhe: làm thêm bản nhẹ 720p (mặc định <mp4 không đuôi>-xem.mp4 cạnh mp4).
  Đường Premiere KHÔNG cần bản nhẹ: mp4 đã nằm sẵn trên máy anh.
  In một dòng JSON: kết quả duyệt + lệch chữ (trung vị, chậm nhất, các cụm lệch > 0,2s) + đường dẫn ho-so.json.
  Chạy bằng Bash với run_in_background hoặc timeout 300000 (v8 80,5s: khoảng 30–40s).
  ho-so.dat = false khi: duyệt máy có lỗi, còn bước lỗi trong kết quả lệnh, |trung vị lệch chữ| > 0,15s, đo được < 70% số
  cụm phụ đề, hoặc vị trí cảnh thật lệch dự đoán ≥ 0,5 khung. Lý do ghi ở ho-so.ly_do_khong_dat.

Đo khớp: nghe lại bản xuất từng đoạn 10s (sherpa, bỏ 0,6s đầu mỗi đoạn vì máy nghe dồn mốc từ đầu), mỗi cụm phụ đề
tìm tiếng của từ đầu cụm (so không dấu, số đọc thành chữ) gần nhất trong ±1,2s; lệch = giờ hiện chữ − giờ nghe.
Mốc máy nghe sớm ~0,05s nên lệch trung vị +0,03…+0,06 là khớp.
"""
import datetime, glob, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from chung import FFMPEG, FFPROBE, KQ_DIR  # noqa: E402

GUI_LAI = re.compile(r"(-(?:r|lai)\d+)+$")  # bản gửi lại: -r2 (hau_to) / -lai1 (gui_lenh tự chạy lại sau khi Premiere văng)


def ban_nhe(mp4, ra):
    os.makedirs(os.path.dirname(ra), exist_ok=True)
    # 720p đủ xem trên điện thoại, mã hóa nhanh hơn ~2,5 lần bản 1080p
    r = subprocess.run([FFMPEG, "-v", "error", "-y", "-i", mp4, "-vf", "scale=720:-2", "-c:v", "libx264", "-preset", "veryfast",
                        "-b:v", "2.2M", "-maxrate", "6M", "-bufsize", "9M", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", ra],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"nhe": ra, "ok": r.returncode == 0, "loi": r.stderr[-300:] if r.returncode else None,
            "MB": round(os.path.getsize(ra) / 1e6, 1) if os.path.exists(ra) else None}


def duyet(W, mp4):
    """Chạy duyet.py, trả về TOÀN BỘ duyet.json (có khung_chu_moc, đường dẫn ảnh)."""
    r = subprocess.run([sys.executable, os.path.join(HERE, "duyet.py"), mp4, os.path.join(W, "dtg.json"),
                        os.path.join(W, "duyet"), os.path.join(W, "chu", "lop-chu.json")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"dat": False, "loi": ["duyet.py không chạy: " + (r.stderr or r.stdout)[-500:]]}


def kiem_khop(W, mp4, mdir):
    import canh_tu as ct
    import sherpa_onnx
    f = lambda pat: next(os.path.join(mdir, x) for x in sorted(os.listdir(mdir)) if re.match(pat, x))
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f(r"encoder.*\.onnx$"), decoder=f(r"decoder.*\.onnx$"), joiner=f(r"joiner.*\.onnx$"),
        tokens=os.path.join(mdir, "tokens.txt"), num_threads=2, decoding_method="greedy_search")
    T = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                             capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip())
    nghe = []
    for a in np.arange(0, T, 10):
        wa, wb = max(0.0, a - 1.5), min(T, a + 10.5)
        for w, s, _ in ct.nhan_dang(rec, ct.doc_tieng(mp4, wa, wb)):
            t = wa + s
            if a <= t < a + 10 and (t - wa > 0.6 or wa == 0):
                nghe.append((ct.chuan(w), t))
    k = json.load(open(os.path.join(W, "ke-hoach.json"), encoding="utf-8"))
    lop = json.load(open(os.path.join(W, "chu", "lop-chu.json"), encoding="utf-8"))
    tu = [(w[0], w[1]) for p in k.get("phu_de") or [] for w in p.get("tu") or []]
    if not tu:
        return {"khop": "không có giờ từng từ (chưa chạy canh_tu)"}
    cum = sorted(l["t0"] for l in lop["lop"] if l["ten"].startswith("phu-de"))
    res = []
    for t0 in cum:
        w = min(tu, key=lambda z: abs(z[1] - t0))
        c0 = ct.chuan(ct.doc_tu(w[0])[0])
        cand = [h for h in nghe if h[0] == c0 and abs(h[1] - t0) < 1.2]
        if cand:
            h = min(cand, key=lambda z: abs(z[1] - t0))
            res.append((round(t0, 2), w[0].rstrip("|"), round(t0 - h[1], 2)))
    if not res:
        return {"khop": "không đo được"}
    d = [r[2] for r in res]
    return {"khop": {"so_cum": len(cum), "do_duoc": len(res), "trung_vi": round(float(np.median(d)), 3),
                     "cham_nhat": max(d), "som_nhat": min(d), "lech_hon_02": [r for r in res if abs(r[2]) > 0.2]}}


def doc_doi_so(args):
    """W, mp4 vị trí (đúng 2); --mo-hinh <dir>; --nhe [<ra.mp4>] (đường dẫn chỉ nhận khi đã đủ 2 tham số vị trí và kết thúc
    .mp4); --ket-qua <file.json>… Cờ lạ / thiếu giá trị / thừa tham số -> dừng."""
    vt, mo_hinh, nhe, ra, kq = [], None, False, None, None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--mo-hinh":
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                raise SystemExit("--mo-hinh thiếu thư mục mô hình")
            mo_hinh = args[i + 1]
            i += 2
            continue
        if a == "--nhe":
            nhe = True
            if len(vt) >= 2 and i + 1 < len(args) and not args[i + 1].startswith("--") and args[i + 1].lower().endswith(".mp4"):
                ra = args[i + 1]
                i += 1
            i += 1
            continue
        if a == "--ket-qua":
            kq, i = [], i + 1
            while i < len(args) and not args[i].startswith("--") and args[i].lower().endswith(".json"):
                kq.append(args[i])
                i += 1
            if not kq:
                raise SystemExit("--ket-qua cần ít nhất 1 file .json")
            continue
        if a.startswith("-"):
            raise SystemExit(f"Cờ lạ: {a}. Nhận: --mo-hinh <dir>, --nhe [ra.mp4], --ket-qua <file.json>…")
        vt.append(a)
        i += 1
    if len(vt) != 2:
        raise SystemExit(f"Cần đúng 2 tham số vị trí <W> <mp4>, nhận {len(vt)}: {vt}\n\n" + __doc__)
    return vt[0], vt[1], mo_hinh, nhe, ra, kq


def doc_ket_qua(files, W):
    """Kết quả lệnh Premiere (ket-qua/<id>.json) -> {id: {ok, so_buoc, can, buoc_loi}}; lệnh gửi lại (-r2…) thay lệnh gốc."""
    can = {}
    for p in glob.glob(os.path.join(W, "lenh", "*.json")):
        try:
            c = json.load(open(p, encoding="utf-8"))
            if isinstance(c, dict) and c.get("id"):
                can[c["id"]] = len(c.get("buoc") or [])
        except (OSError, ValueError):
            pass
    ds = {}
    for p in files:
        try:
            r = json.load(open(p, encoding="utf-8"))
        except (OSError, ValueError) as e:
            ds[os.path.basename(p)] = {"file": p, "ok": False, "buoc_loi": [{"loi": f"không đọc được: {e}"}]}
            continue
        i = r.get("id") or os.path.splitext(os.path.basename(p))[0]
        buoc = r.get("buoc") if isinstance(r.get("buoc"), list) else []
        loi = [{"buoc": k + 1, "lenh": b.get("lenh"), "loi": b.get("loi")} for k, b in enumerate(buoc) if not b.get("ok")]
        goc = GUI_LAI.sub("", i)
        x = {"file": p, "ok": bool(r.get("ok", not loi)) and not loi, "so_buoc": len(buoc), "can": can.get(goc), "buoc_loi": loi,
             "xong": r.get("xong")}
        if x["can"] and x["so_buoc"] < x["can"]:
            x["ok"] = False
            x["chua_het"] = f"chạy {x['so_buoc']}/{x['can']} bước"
        ds[i] = x
    con = {}
    for i in sorted(ds, key=lambda z: (GUI_LAI.sub("", z), str(ds[z].get("xong") or ""), len(z))):
        con[GUI_LAI.sub("", i)] = i  # bản gửi lại sau cùng (xong muộn nhất) thắng
    loi_con = {g: ds[i] for g, i in con.items() if not ds[i]["ok"]}
    return ds, loi_con


def so_vi_tri(tl, ds, id_a):
    """So vị trí từng cảnh trong kết quả lượt a (các phần a, theo thứ tự) với vị trí dự đoán (lệch theo khung)."""
    import dung_premiere as DP
    import lenh_premiere as LP
    buoc = []
    for g in id_a or []:
        cand = [i for i in ds if GUI_LAI.sub("", i) == g]
        if not cand:
            return {"khop": None, "ghi_chu": f"thiếu kết quả {g}"}
        r = json.load(open(ds[max(cand, key=lambda z: (str(ds[z].get("xong") or ""), len(z)))]["file"], encoding="utf-8"))
        buoc += r.get("buoc") or []
    if not buoc:
        return {"khop": None, "ghi_chu": "không có kết quả lượt a"}
    du = [b["ket_qua"]["tren_timeline"] for b in DP.du_doan_a(tl)["buoc"]]
    that = LP.placed({"buoc": buoc})[:len(du)]
    fps = tl["fps"]
    lech = [round(max(abs(a["bat_dau"] - b["bat_dau"]), abs(a["ket_thuc"] - b["ket_thuc"])) * fps, 2) for a, b in zip(du, that)]
    return {"so_canh": len(du), "dat_duoc": len(that), "lech_toi_da_khung": max(lech) if lech else None,
            "canh_lech": [k + 1 for k, x in enumerate(lech) if x >= 0.5], "khop": len(that) == len(du) and (max(lech) if lech else 0) < 0.5}


def main():
    W, mp4, mo_hinh, nhe, ra, kq_files = doc_doi_so(sys.argv[1:])
    import chung
    mo_hinh = chung.mo_hinh_hoac_none(mo_hinh)  # bản máy tiệm: thiếu --mo-hinh thì dùng env POLY_MO_HINH / engine/mo-hinh
    W, mp4 = os.path.abspath(W), os.path.abspath(mp4)  # ho-so.json ghi đường dẫn đầy đủ cho người duyệt
    if not os.path.isfile(mp4):
        raise SystemExit(f"Không thấy mp4: {mp4}")
    dtg_p, kh_p, lop_p = os.path.join(W, "dtg.json"), os.path.join(W, "ke-hoach.json"), os.path.join(W, "chu", "lop-chu.json")
    tl = json.load(open(dtg_p, encoding="utf-8"))
    ten = tl["ten"]
    try:
        gui = json.load(open(os.path.join(W, "gui.json"), encoding="utf-8"))
    except (OSError, ValueError):
        gui = {}
    try:
        lopj = json.load(open(lop_p, encoding="utf-8"))
    except (OSError, ValueError):
        lopj = {}
    # kết quả lệnh: --ket-qua, hoặc bản đã stage của gui.ket_qua_may (kể cả gửi lại -r2…)
    thieu_kq = []
    if kq_files is None:  # bản máy tiệm: kết quả nằm sẵn trong thư mục ket-qua của Poly Bridge trên máy này
        kq_files = []
        for d in gui.get("ket_qua_may") or []:
            p = os.path.join(KQ_DIR, os.path.basename(str(d).replace("\\", "/")))
            co = [p] if os.path.isfile(p) else []
            goc_p = glob.escape(os.path.splitext(p)[0])
            co += sorted(glob.glob(goc_p + "-r*.json") + glob.glob(goc_p + "-lai*.json"))
            kq_files += co
            if not co:
                thieu_kq.append(d)
    ds_kq, loi_con = doc_ket_qua(kq_files, W) if kq_files else ({}, {})
    gio, t0 = {}, time.time()

    def do(ten_viec, f, *a):
        s = time.time()
        try:
            return f(*a)
        finally:
            gio[ten_viec] = round(time.time() - s, 1)

    # duyệt (ffmpeg, 1 lượt giải mã) ∥ khớp chữ (sherpa) — không làm bản nhẹ trên đường găng
    with ThreadPoolExecutor(2) as ex:
        f_duyet = ex.submit(do, "duyet", duyet, W, mp4)
        f_khop = ex.submit(do, "kiem_khop", kiem_khop, W, mp4, mo_hinh) if mo_hinh else None
        dy = f_duyet.result()
        try:
            khop = f_khop.result() if f_khop else {"khop": "không đo (thiếu --mo-hinh)"}
        except Exception as e:  # máy nghe lỗi không được làm mất kết quả duyệt
            khop = {"khop": f"lỗi khi đo khớp: {e}"}
    vi_tri = so_vi_tri(tl, ds_kq, gui.get("id_a")) if ds_kq else {"khop": None, "ghi_chu": "không có kết quả lệnh"}
    ly_do = []
    if not dy.get("dat"):
        ly_do.append("duyệt máy có lỗi: " + "; ".join(map(str, dy.get("loi") or [])))
    for g, x in loi_con.items():
        ly_do.append(f"lệnh {g} còn lỗi: " + (x.get("chua_het") or "") + "; ".join(
            f"bước {b.get('buoc')} {b.get('lenh')}: {b.get('loi')}" for b in x["buoc_loi"][:5]))
    k = khop.get("khop")
    if isinstance(k, dict):
        if abs(k["trung_vi"]) > 0.15:
            ly_do.append(f"chữ lệch lời: trung vị {k['trung_vi']:+.3f}s (> 0,15s)")
        if k["do_duoc"] < 0.7 * k["so_cum"]:
            ly_do.append(f"chỉ đo được {k['do_duoc']}/{k['so_cum']} cụm phụ đề (< 70%)")
    if vi_tri.get("khop") is False:
        ly_do.append(f"vị trí cảnh thật lệch dự đoán {vi_tri.get('lech_toi_da_khung')} khung (cảnh {vi_tri.get('canh_lech')[:10]})")
    nhe_kq = None
    if nhe:
        ra = ra or os.path.splitext(mp4)[0] + "-xem.mp4"
        nhe_kq = do("ban_nhe", ban_nhe, mp4, ra)
    gio["tong"] = round(time.time() - t0, 1)
    luu_y = []
    if not isinstance(k, dict):
        luu_y.append("chưa đo khớp chữ – lời: " + str(k))
    if not ds_kq and gui:  # đường ffmpeg (không gui.json): không có lệnh Premiere nào
        luu_y.append("chưa có kết quả lệnh Premiere (không thấy trong " + KQ_DIR + "; hoặc truyền --ket-qua)")
    if thieu_kq:
        luu_y.append(f"thiếu {len(thieu_kq)} file kết quả: " + ", ".join(x.rsplit(chr(92), 1)[-1] for x in thieu_kq))
    ho_so = {
        "ten": ten, "mp4": mp4, "mp4_may": gui.get("mp4_may"), "luc": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "MB": round(os.path.getsize(mp4) / 1e6, 1),
        "dat": not ly_do, "ly_do_khong_dat": ly_do, "luu_y": luu_y,
        "duyet": dy, **khop, "lenh": ds_kq, "vi_tri_canh": vi_tri, "nhe": nhe_kq,
        "anh": [p for p in (dy.get("to_duyet"), dy.get("khung_dau"), dy.get("khung_chu")) if p],
        # cho người duyệt vòng 1 (chữ, cảnh, hook): đọc thẳng, không phải hỏi lại
        "duong_dan": {"W": W, "ke_hoach": kh_p, "dtg": dtg_p, "lop_chu": lop_p, "chu": os.path.join(W, "chu"),
                      "gui": os.path.join(W, "gui.json") if gui else None},
        "kieu": tl.get("kieu"), "T": tl.get("T"),
        "canh_bao": {"ke_hoach": tl.get("canh_bao") or [], "ve_chu": lopj.get("canh_bao") or []},
        "canh_tu": gui.get("canh_tu"),
        "gio_giay": gio,
        "ghi_chu": "Số đo đã đủ (duyệt máy + khớp chữ + kết quả lệnh + vị trí cảnh). Người duyệt KHÔNG chạy lại ffmpeg / máy "
                   "nghe: đọc file này và xem ảnh trong `anh` (khung-chu phủ cả video, khung_chu_moc ghi giây từng khung).",
    }
    hp = os.path.join(W, "ho-so.json")
    json.dump(ho_so, open(hp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    gon = {k2: dy.get(k2) for k2 in ("dat", "loi", "luu_y", "do_dai", "loudness_lufs", "dinh_that_dbtp", "to_duyet", "khung_chu")}
    print(json.dumps({"dat": ho_so["dat"], "ly_do_khong_dat": ly_do, "duyet": gon, **khop,
                      "lenh": {i: x["ok"] for i, x in ds_kq.items()}, "vi_tri_canh": vi_tri.get("khop"), **(nhe_kq or {}),
                      "ho_so": hp, "gio_giay": gio}, ensure_ascii=False))


if __name__ == "__main__":
    main()
