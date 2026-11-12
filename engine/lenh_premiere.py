#!/usr/bin/env python3
"""Sinh lệnh Poly Bridge (Premiere) từ dong-thoi-gian.json + lop-chu.json. Chạy theo lượt, lượt sau đọc kết quả lượt trước.

  a: python3 lenh_premiere.py a <dtg.json> <lop-chu.json> <thu_muc_may> <ra.json>
     tạo project, nhập file, sequence trống, khung dọc + fps, đặt các cảnh nối tiếp (+ giọng đọc), đo thang âm lượng, đặt âm lượng,
     xem_sequence, luu_project (bước CUỐI — MCP chỉ tự chạy lại lệnh như vậy)
  b: python3 lenh_premiere.py b <dtg.json> <lop-chu.json> <thu_muc_may> <ket-qua-a.json> <ra.json>
     zoom (Scale keyframe, vào/ra êm) từng cảnh + điểm nhấn (zoom_dap / rung_nhip), chuyển cảnh, âm nhấn (A3), từng lớp chữ
     trên track của nó + chuyển động (hieu_ung_chu), ten_track. Chữ ghép cũ (ve_chu --chu-ghep): đoạn ghép V2 + POLY STORE V3.
     Lượt a thêm them_track khi lop-chu.json cần > 3 track hình.
  c: python3 lenh_premiere.py c <dtg.json> <lop-chu.json> <thu_muc_may> <ket-qua-a.json> <ra.json>
     cắt phần thừa sau cảnh cuối, đặt vào/ra, lưu, tìm mẫu xuất H.264, xuất ảnh khung để duyệt (thư mục khung/)
  d: python3 lenh_premiere.py d <dtg.json> <lop-chu.json> <thu_muc_may> <ket-qua-c.json> <ra.json> [--ghi-de]
     xuất mp4 bằng mẫu xuất tìm được (--ghi-de: xuất lại đè bản cũ sau khi sửa). Kết quả c không có tim_preset (lượt c
     luồng nhanh) -> lấy mẫu xuất trong may.json (cạnh file này)
  am: python3 lenh_premiere.py am <dtg.json> <lop-chu.json> <thu_muc_may> <ket-qua-a.json> <lufs_do_duoc | -> <ra.json>
     chỉnh lại âm lượng theo độ lớn đo ở bản xuất (đích -14 LUFS), cộng dồn với lần chỉnh trước (lưu ở am-da-chinh.json
     cạnh dtg.json); "-" = đặt lại mức đang lưu. Sau đó chạy lại lượt d --ghi-de.
     Lượt a lỗi ở bước âm lượng: chạy lượt am "-" — KHÔNG chạy lại lượt a (sẽ nối thêm cả bộ cảnh lần nữa).
     --limiter (plugin >= 1.4.0): thêm Hard Limiter (trần -1,5 dB) vào TỪNG clip A1/A2; phần tăng (+dB) đưa vào Input Boost
       của limiter thay vì Level (Level chỉ hạ, không tăng) nên đỉnh TỪNG CLIP luôn bị chặn dù Premiere xử lý Volume trước hay
       sau limiter; cho tăng tới +12 dB. Premiere không có limiter cho track / Master → tổng A1 + A2 (2 track kêu cùng lúc) vẫn
       có thể vượt trần: luôn đo true peak bản xuất (ffmpeg ebur128=peak=true), vượt -1 dBTP thì hạ mức / dựng âm máy chủ.
       Bước limiter chạy trước am_luong (limiter lỗi thì Level chưa đổi). Đã dùng 1 lần thì các lượt am sau tự giữ
       (lưu trong am-da-chinh.json, ghi lúc sinh lệnh). --bo-limiter: gỡ limiter, về cách cũ.
       LỆNH CỨU khi limiter lỗi trên Premiere: lenh_premiere.py am <dtg> <lop> <may> <kq-a> - <ra> --bo-limiter
       ("-" = dùng lại mức đã lưu, không cộng thêm). Chạy lại với CÙNG số LUFS vừa đo cũng không bị cộng hai lần
       (tính lại từ mức trước lần đó — delta_truoc trong am-da-chinh.json). Không có cờ nào = luồng cũ, không đổi gì.

Plugin Poly Bridge >= 1.3.0. Với 1.2.x: thêm --plugin-cu (tắt tiếng gốc thay vì né giọng, không xuất khung, không chạy song song).
Mỗi file lệnh mang "project" + "song_song": plugin làm đúng project của video này dù anh đang mở project khác phía trước.

<thu_muc_may>: thư mục trên máy anh chứa project + thư mục chu/ (vd. E:/Tool/poly-edit/IMG_5123).
Tên file lệnh = id; id có giờ để không trùng.
"""
import json, os, sys, datetime

H264 = "4e49434b_48323634"
CU = "--plugin-cu" in sys.argv  # plugin 1.2.x
# Âm lượng (dB) — tiếng gốc làm nền, hạ xuống khi có giọng đọc (giống bản dựng máy chủ).
AM = {"nen_co_giong": -6.0, "ne_giong": -20.0, "mem": 0.2, "goc_khong_giong": 0.0, "giong": 0.0}
DELTA_MIN, DELTA_MAX = -12.0, 6.0
# --limiter (plugin 1.4.0 them_hieu_ung_am): trần mẫu -1,5 dBFS chừa ~0,5 dB cho đỉnh giữa mẫu → mỗi clip <= -1 dBTP.
# Chỉ chặn từng clip: tổng A1 + A2 có thể vượt → đo true peak bản xuất.
LIMITER_TRAN = -1.5
DELTA_MAX_LIMITER = 12.0


def stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def load(p):
    return json.load(open(p, encoding="utf-8"))


def seq_name(tl):
    return tl["ten"] + "-doc"


def project_path(tl, mdir):
    return mdir.rstrip("/") + "/" + tl["ten"] + ".prproj"


def wrap(tl, mdir, lot, buoc, dung_khi_loi=True):
    cmd = {"id": stamp() + "-" + tl["ten"] + "-" + lot, "buoc": buoc}
    if not CU:
        cmd.update({"project": project_path(tl, mdir), "song_song": True})
    if not dung_khi_loi:
        cmd["dung_khi_loi"] = False
    return cmd


def fill_pct(tl, src):
    W, H = tl["khung"]
    s = tl["nguon"][src]
    return max(W / s["rong"], H / s["cao"]) * 100.0


def png_on_machine(mdir, ten):
    return mdir.rstrip("/") + "/chu/" + ten


def lop_premiere(lopj):
    """Đoạn chữ đã ghép (track 1 = V2, không chồng giờ) + POLY STORE (track 2 = V3)."""
    lp = lopj.get("lop_premiere")
    if lp is None:
        raise SystemExit("lop-chu.json chưa có lop_premiere — chạy lại ve_chu.py bản mới.")
    return lp


def co_tieng_goc(tl):
    return any(tl["nguon"][s["file"]].get("co_tieng", True) for s in tl["shots"])


def am_steps(tl, delta, thang=None):
    """Lệnh âm lượng: tiếng gốc (A1) nền + né giọng; giọng đọc (A2). delta: dB cộng thêm vào mức chuẩn."""
    sq = seq_name(tl)
    r = lambda x: round(x + delta, 1)
    extra = {"thang": thang} if thang else {}
    st = []
    if co_tieng_goc(tl):
        if tl.get("giong"):
            st.append(dict({"lenh": "am_luong", "sequence": sq, "track_tieng": 0, "ca_track": True, "db": r(AM["nen_co_giong"]),
                            "ne_giong": {"track_tieng": 1, "db_ne": r(AM["ne_giong"]), "mem": AM["mem"]}}, **extra))
        else:
            st.append(dict({"lenh": "am_luong", "sequence": sq, "track_tieng": 0, "ca_track": True, "db": r(AM["goc_khong_giong"])}, **extra))
    if tl.get("giong"):
        st.append(dict({"lenh": "am_luong", "sequence": sq, "track_tieng": 1, "ca_track": True, "db": r(AM["giong"])}, **extra))
    return st


def limiter_steps(tl, tang, go=False):
    """Hard Limiter trên mọi clip tiếng gốc (A1) + giọng (A2): trần LIMITER_TRAN, tang = Input Boost (dB, >= 0).
    Plugin chỉnh limiter đang có (không thêm chồng). go=True: gỡ limiter."""
    sq = seq_name(tl)
    tracks = ([0] if co_tieng_goc(tl) else []) + ([1] if tl.get("giong") else [])
    st = []
    for t in tracks:
        step = {"lenh": "them_hieu_ung_am", "sequence": sq, "track_tieng": t, "ca_track": True, "ten": "Hard Limiter"}
        if go:
            step["go"] = True
        else:
            step["limiter"] = {"tran_db": LIMITER_TRAN, "tang_db": round(tang, 1)}
        st.append(step)
    return st


def them_track_steps(sq, lopj, mdir):
    """Chữ mỗi lớp 1 track (ve_chu lop_rieng): thêm track hình cho đủ so_track_hinh (sequence mới có 3). Clip tạm = 1 PNG
    của chính video (plugin đặt ở cuối timeline rồi gỡ). Kiểu ghép cũ (--chu-ghep) không cần."""
    can = int(lopj.get("so_track_hinh") or 3)
    if lopj.get("che_do_premiere") != "lop_rieng" or can <= 3:
        return []
    png = next((l["ten"] for l in lop_premiere(lopj) if l["ten"].lower().endswith(".png")), None)
    st, con = [], can - 3
    while con > 0:
        b = {"lenh": "them_track", "sequence": sq, "loai": "hinh", "so": min(5, con)}
        if png:
            b["file"] = png_on_machine(mdir, png)
        st.append(b)
        con -= b["so"]
    return st


def vi_tri_du_doan(tl):
    """Vị trí từng cảnh trên timeline Premiere (đặt nối tiếp, vào/ra theo khung) — giống dung_premiere.du_doan_a."""
    fps, o, out = tl["fps"], 0.0, []
    for s in tl["shots"]:
        d = (int(round(s["den"] * fps)) - int(round(s["tu"] * fps))) / fps
        out.append({"bat_dau": round(o, 6), "ket_thuc": round(o + d, 6)})
        o += d
    return out


def canh_nhan(tl, pos=None):
    """Chỗ đặt điểm nhấn (diem_nhan): chỗ cắt KHÔNG có chuyển cảnh (chuyển cảnh đã là nhấn), trước thẻ kết, ngoài phần
    montage mở đầu. Ưu tiên đầu cảnh gốc mới (cách nhau ≥ 2s); kiểu chuyển cảnh đều (mọi chỗ đổi cảnh đều có chuyển cảnh)
    thì lấy thêm chỗ cắt giữa các phần của một cảnh dài, cách mọi điểm nhấn khác ≥ 4s (nhấn liên tục thành rối).
    -> [(chỉ số cảnh, giây)] tăng dần."""
    pos = pos or vi_tri_du_doan(tl)
    ket0 = tl["ket_t"][0] if (tl.get("chu") or {}).get("ket") else tl["T"]
    ung = []
    for i, (s, p) in enumerate(zip(tl["shots"], pos)):
        if i == 0 or s["canh"] < 0 or tl["shots"][i - 1]["canh"] < 0 or s.get("chuyen") or p["bat_dau"] >= ket0 - 0.3:
            continue
        ung.append((i, round(p["bat_dau"], 3), bool(s.get("dau_canh"))))
    chon = []
    for i, t, dau in ung:
        if dau and all(abs(t - t2) >= 2.0 for _, t2 in chon):
            chon.append((i, t))
    deu = any(s.get("chuyen") for s in tl["shots"]) and not any(d for _, _, d in ung)  # mọi chỗ đổi cảnh đều có chuyển cảnh
    if deu and tl["kieu"].get("chuyen_dong") != "punch_nhip":  # punch_nhip đã nhấn bằng cận 112% ở chính chỗ cắt đó
        for i, t, dau in ung:
            if not dau and all(abs(t - t2) >= 4.0 for _, t2 in chon):
                chon.append((i, t))
    return sorted(chon, key=lambda x: x[1])


def moc_nhan(tl):
    return [t for _, t in canh_nhan(tl)]


def lot_a(tl, lopj, mdir):
    sq = seq_name(tl)
    files = sorted({s["file"] for s in tl["shots"]})
    if CU:
        pngs = [png_on_machine(mdir, l["ten"]) for l in lopj["lop"]]
    else:  # nhiều đoạn có thể dùng chung 1 PNG (dung_premiere gộp file trùng nội dung) -> nhập mỗi file 1 lần
        pngs = [png_on_machine(mdir, n) for n in dict.fromkeys(l["ten"] for l in lop_premiere(lopj))]
        pngs += [png_on_machine(mdir, n) for n in (lopj.get("am_nhan") or {}).values()]  # âm nhấn (wav) cùng thư mục chu/
    st = [
        {"lenh": "tao_project", "duong_dan": project_path(tl, mdir)},
        {"lenh": "nhap_file", "files": files + pngs + ([tl["giong"]["file"]] if tl.get("giong") else []), "bin": "Nguyen lieu"},
        {"lenh": "tao_sequence", "ten": sq},
        {"lenh": "khung_sequence", "sequence": sq, "rong": tl["khung"][0], "cao": tl["khung"][1], "fps": tl["fps"]},
    ]
    if not CU:  # lớp chữ riêng track: thêm V4, V5… NGAY SAU khi có sequence (lỗi ở đây thì chưa đặt cảnh nào, chạy lại không mất gì)
        st += them_track_steps(sq, lopj, mdir)
    for i, s in enumerate(tl["shots"]):
        if s.get("dong_bang") or s.get("the_hoi"):
            raise SystemExit("Kiểu mở đầu này chỉ dựng được trên máy chủ (đổi kiểu bằng chon_kieu.py --duong premiere).")
        # Premiere làm tròn XUỐNG điểm vào/ra theo khung: 9.8333 (=295/30 làm tròn 4 số) thành khung 294 -> lệch dần
        # 0,03s mỗi cảnh. Đưa về đúng khung + 0,0005s để làm tròn xuống ra đúng khung định (canh_tu.py tính như vậy).
        kh = lambda x: round(int(round(x * tl["fps"])) / tl["fps"] + 0.0005, 4)
        st.append({"lenh": "dat_clip", "file": s["file"], "sequence": sq, "bat_dau": 0 if i == 0 else "noi",
                   "tu": kh(s["tu"]), "den": kh(s["den"])})
    if tl.get("giong"):
        st.append({"lenh": "dat_clip", "file": tl["giong"]["file"], "sequence": sq, "bat_dau": 0, "track_hinh": 3, "track_tieng": 1})
        if CU:
            st.append({"lenh": "tat_tieng", "sequence": sq, "track": 0})
    if not CU and (co_tieng_goc(tl) or tl.get("giong")):
        # đo thang Level trên clip vừa đặt (chưa chỉnh) — clip đầu tiên của track, không phụ thuộc giây 0 có tiếng hay không
        st.append({"lenh": "am_luong", "sequence": sq, "track_tieng": 0 if co_tieng_goc(tl) else 1, "ca_track": True, "do_thang": True})
        st += am_steps(tl, 0.0)
    st.append({"lenh": "xem_sequence", "ten": sq})
    # luu_project ở bước CUỐI: MCP chỉ tự chạy lại lệnh như vậy; văng ở lượt sau cũng không mất lượt a
    # (am_tung_clip.py chèn âm lượng từng clip trước xem_sequence, giữ luu_project cuối)
    st.append({"lenh": "luu_project"})
    return wrap(tl, mdir, "a", st)


def placed(res_a):
    """Vị trí thật của từng cảnh trên timeline (theo thứ tự đặt)."""
    out = []
    for b in res_a["buoc"]:
        if b.get("lenh") == "dat_clip" and b.get("ok") and b.get("ket_qua", {}).get("tren_timeline"):
            k = b["ket_qua"]
            if k["tren_timeline"]["track"] == "hinh" and k.get("tu") is not None:
                out.append(k["tren_timeline"])
    return out


def thang_tu(res_a):
    for b in res_a["buoc"]:
        if b.get("lenh") == "am_luong" and b.get("ok") and (b.get("ket_qua") or {}).get("thang_dang_dung"):
            return b["ket_qua"]["thang_dang_dung"]
    return None


def lot_b(tl, lopj, mdir, res_a):
    sq = seq_name(tl)
    pos = placed(res_a)
    if len(pos) < len(tl["shots"]):
        raise SystemExit(f"Lượt a mới đặt được {len(pos)}/{len(tl['shots'])} cảnh — xem lại kết quả lượt a.")
    pos = pos[:len(tl["shots"])]
    fps = float(tl.get("fps") or 30)
    k = tl["kieu"]
    dn = "khong" if CU else k.get("diem_nhan", "khong")
    nhan = dict(canh_nhan(tl, pos)) if dn in ("zoom_dap", "rung_nhip") else {}
    st = []
    for i, (s, p) in enumerate(zip(tl["shots"], pos)):
        f = fill_pct(tl, s["file"])
        dur = p["ket_thuc"] - p["bat_dau"]
        mid = round((p["bat_dau"] + p["ket_thuc"]) / 2, 3)
        a, b = round(f * s["z0"], 2), round(f * s["z1"], 2)
        rung = dn == "rung_nhip" and i in nhan
        if rung:  # rung cần dư mép: phóng thêm 4% (≈ 38px mỗi bên dọc) cho khỏi lộ viền đen
            a, b = round(a * 1.04, 2), round(b * 1.04, 2)
        base = {"lenh": "dat_thong_so", "sequence": sq, "track_hinh": 0, "thoi_diem": mid, "thong_so": "Scale"}
        kf = None
        if s.get("kf") and not CU:  # mở đầu punch_mo: keyframe riêng [giây, hệ số], None = cuối cảnh
            het = round(max(0.1, dur - 0.05), 3)
            kf, t_truoc = [], -1.0
            for x, z in s["kf"]:
                t = het if x is None else round(min(float(x), het), 3)
                if t > t_truoc + 1e-3:
                    kf.append({"t": t, "v": round(f * z * (1.04 if rung else 1.0), 2)})
                    t_truoc = t
        elif dn == "zoom_dap" and i in nhan:  # đập zoom 110% -> mức thường trong 0,25s đầu cảnh mới, rồi zoom như cũ
            t1 = round(min(0.25, dur * 0.4), 3)
            kf = [{"t": 0, "v": round(a * 1.10, 2)}, {"t": t1, "v": round(a + (b - a) * t1 / max(dur, 1e-3), 2)}]
            if dur - 0.05 > t1 + 0.05:
                kf.append({"t": round(dur - 0.05, 3), "v": b})
        if kf:
            st.append(dict(base, keyframes=kf, noi_suy="muot"))
        elif abs(a - b) < 0.01:
            st.append(dict(base, gia_tri=a))
        else:
            step = dict(base, keyframes=[{"t": 0, "v": a}, {"t": round(max(0.1, dur - 0.05), 3), "v": b}])
            if not CU:
                step["noi_suy"] = "deu" if s.get("easing") == "deu" else "muot"  # vào/ra êm, không giật đầu/cuối cảnh
            st.append(step)
        if rung:  # rung máy nhẹ 0,35s đầu cảnh mới (ngang ±1,2%, dọc ±0,4%), tắt dần
            lech = [(0.012, -0.004), (-0.010, 0.004), (0.007, -0.003), (-0.004, 0.002), (0.002, -0.001), (0.0, 0.0)]
            kp = [{"t": round(j * 0.07, 3), "v": [round(0.5 + dx, 4), round(0.5 + dy, 4)]} for j, (dx, dy) in enumerate(lech)
                  if j * 0.07 < dur - 0.04]
            st.append(dict(base, thong_so="Position", keyframes=kp, noi_suy="deu"))
    kt = load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kieu_dung.json"))["chuyen_canh_ky_thuat"]
    kieu_pr = kt.get(k.get("chuyen_canh"), {}).get("premiere") or "cross dissolve"
    for s, p in zip(tl["shots"], pos):
        if s.get("chuyen", 0) > 0:
            b = {"lenh": "chuyen_canh", "sequence": sq, "track_hinh": 0, "thoi_diem": round(p["bat_dau"] + 0.05, 3),
                 "vi_tri": "dau", "do_dai": s["chuyen"]}
            if s.get("chuyen_match"):
                b["match_name"] = s["chuyen_match"]  # bộ trộn (tron_poly): Film Impact theo đúng tên máy
            else:
                b["kieu"] = s.get("chuyen_pr") or kieu_pr   # chuyển cảnh đặt riêng cảnh này (POLY Team 3/11)
            st.append(b)
    T = pos[-1]["ket_thuc"]
    T_plan = tl["T"]
    if CU:
        layers = []
        for l in lopj["lop"]:
            track = 2 if l["lop"] == 2 else (3 if l.get("lop_phu") else 1)
            layers.append(dict(ten=l["ten"], t0=l["t0"], t1=l["t1"], track=track))
    else:
        layers = [dict(ten=l["ten"], t0=l["t0"], t1=l["t1"], track=l["track"], vi_tri=l.get("vi_tri"),
                       hieu_ung=l.get("hieu_ung"), loai=l.get("loai")) for l in lop_premiere(lopj)]
        st += am_nhan_steps(tl, lopj, mdir, pos, dn)
    # đặt theo giờ tăng dần trên từng track: lệnh đè (overwrite) của ảnh tĩnh chỉ đè vào phần phía sau còn trống
    for l in sorted(layers, key=lambda x: (x["track"], x["t0"])):
        t0, t1 = l["t0"], l["t1"]
        if l["ten"] == "brand.png" or t1 >= T_plan - 0.05:
            t1 = T  # lớp kéo tới cuối: theo độ dài thật trên timeline
        if t0 >= T - 0.05:
            continue
        t1 = min(t1, T)
        st.append({"lenh": "dat_clip", "file": png_on_machine(mdir, l["ten"]), "sequence": sq, "bat_dau": round(t0, 3),
                   "track_hinh": l["track"], "track_tieng": 3, "do_dai": round(t1 - t0, 3)})
        if l.get("hieu_ung") == "mov":  # chữ động dựng sẵn (hoat_hinh.py): chỉ đặt Position = tâm dải
            if l.get("vi_tri"):
                st.append({"lenh": "dat_thong_so", "sequence": sq, "track_hinh": l["track"], "thoi_diem": round((t0 + t1) / 2, 3),
                           "thong_so": "Position", "gia_tri": list(l["vi_tri"])})
        elif not CU:
            st += hieu_ung_chu(sq, l["track"], t0, t1, l.get("vi_tri"), l.get("hieu_ung"), fps)
    if not CU and lopj.get("che_do_premiere") == "lop_rieng":
        st.append(ten_track_step(sq, tl, lopj, layers))
    st.append({"lenh": "xem_sequence", "ten": sq})
    return wrap(tl, mdir, "b", st, dung_khi_loi=False)


# âm nhấn theo loại lớp chữ (giây lúc âm "nghe thấy" = giờ lớp hiện + độ trễ của chuyển động)
AM_LOP = {"nhan": ("bup", 0.05), "gia": ("ting", 0.1), "ket": ("vut_len", 0.12), "sticker": ("bup", 0.03)}


def am_nhan_steps(tl, lopj, mdir, pos, dn):
    """Âm nhấn (kieu.am_nhan = co, file do ve_chu/am_nhan.py tạo trong chu/): vút ở chuyển cảnh, bụp ở điểm nhấn và lúc
    nhãn / sticker hiện, ting ở thẻ giá, vút lên ở thẻ kết, thump (punch_mo) hoặc bụp ở hook khung đầu. Đặt trên A3
    (track_tieng 2), theo giờ tăng dần, cách nhau ≥ 0,35s (am_nhan.lich)."""
    am = lopj.get("am_nhan") or {}
    if not am:
        return []
    import am_nhan
    sq, T = seq_name(tl), pos[-1]["ket_thuc"]
    ev = []
    for s, p in zip(tl["shots"], pos):
        if s.get("chuyen", 0) > 0:
            ev.append(("vut", p["bat_dau"] + s["chuyen"] / 2))
    if dn != "khong":
        ev += [("bup", t) for _, t in canh_nhan(tl, pos)]
    for l in lopj.get("lop") or []:  # lớp gốc (có loai, giờ hiện) — dùng được cả khi chữ ghép (--chu-ghep)
        lo = l.get("loai") or {"hook.png": "hook", "the-gia.png": "gia", "ket.png": "ket"}.get(l["ten"])
        if lo == "hook":
            ev.append(("dap" if tl["kieu"].get("mo_dau") == "punch_mo" else "bup", l["t0"]))
        elif lo in AM_LOP:
            ten, tre = AM_LOP[lo]
            ev.append((ten, l["t0"] + tre))
    st = []
    for ten, bd in am_nhan.lich([(x, t) for x, t in ev if x in am], T):
        st.append({"lenh": "dat_clip", "file": png_on_machine(mdir, am[ten]), "sequence": sq, "bat_dau": bd, "track_tieng": 2})
    return st


def ten_track_step(sq, tl, lopj, layers):
    """Tên track cho anh dễ nhìn trong Premiere (cần 26.3+; lượt b không dừng nếu lỗi)."""
    ten = {0: "Cảnh"}
    for l in layers:
        lo = l.get("loai")
        ten.setdefault(l["track"], {"fx": "Hiệu ứng", "phu_de": "Phụ đề", "brand": "Logo", "thanh": "Tiến trình"}.get(lo, "Chữ"))
    ds = [{"track_hinh": t, "ten": n} for t, n in sorted(ten.items())][:17]
    ds.append({"track_tieng": 0, "ten": "Tiếng gốc"})
    if tl.get("giong"):
        ds.append({"track_tieng": 1, "ten": "Giọng"})
    if lopj.get("am_nhan"):
        ds.append({"track_tieng": 2, "ten": "Âm nhấn"})
    return {"lenh": "ten_track", "sequence": sq, "ds": ds}


def hieu_ung_chu(sq, track, t0, t1, vi_tri, hieu_ung, fps=30.0):
    """Chuyển động khi lớp hiện (keyframe tính từ đầu clip). Lớp đã dời về tâm khung (ve_chu.phu_de_giua): Position =
    tâm chữ thật. nay = nảy (Scale 72→106→100) + hiện dần; nay_nhe = chỉ nảy (phụ đề cụm); nay_dau = hook, khung đầu đã thấy chữ 90%; nay_manh = nảy mạnh (50→115→100, thẻ giá); truot = trượt từ
    trái vào 0,22s (nhãn); len = trồi lên 0,25s (thẻ kết); mo = hiện dần 0,2s (tiêu đề ghim); chop = chớp trắng tắt dần;
    loe = lóa sáng lên rồi tắt; chay = thanh tiến trình chạy hết clip. Clip ngắn hơn hiệu ứng: co thời gian keyframe lại."""
    mid = round((t0 + t1) / 2, 3)
    dur = t1 - t0
    het = max(1.0 / fps, dur - 1.0 / fps)  # keyframe cuối phải nằm trong clip
    base = {"lenh": "dat_thong_so", "sequence": sq, "track_hinh": track, "thoi_diem": mid}

    def nen(kfs):
        last = kfs[-1]["t"]
        if last > het + 1e-9:
            kfs = [dict(x, t=round(x["t"] * het / last, 3)) for x in kfs]
        return kfs

    def mo(d, v0=0, v1=100):
        return dict(base, hieu_ung="opacity", thong_so="Opacity", keyframes=nen([{"t": 0, "v": v0}, {"t": d, "v": v1}]),
                    noi_suy="deu")

    st = []
    tam = vi_tri and hieu_ung in ("nay", "nay_nhe", "nay_dau", "nay_manh")
    if vi_tri and (tam or hieu_ung not in ("truot", "len")):
        st.append(dict(base, thong_so="Position", gia_tri=list(vi_tri)))
    if hieu_ung in ("nay", "nay_nhe"):
        kf = [{"t": 0, "v": 72}, {"t": 0.1, "v": 106}, {"t": 0.18, "v": 100}] if dur >= 0.35 else \
            [{"t": 0, "v": 88}, {"t": 0.08, "v": 100}]
        st.append(dict(base, thong_so="Scale", keyframes=nen(kf), noi_suy="muot"))
        if hieu_ung == "nay":  # nay_nhe (phụ đề cụm, lớp riêng): bỏ hiện dần 2 khung — bớt ~1/4 số bước lượt b
            st.append(mo(0.067))
    elif hieu_ung == "nay_dau":  # hook: khung đầu đã thấy chữ (90%) — khung đầu thường là ảnh bìa — rồi nảy 106% về 100%
        st.append(dict(base, thong_so="Scale", keyframes=nen([{"t": 0, "v": 90}, {"t": 0.1, "v": 106}, {"t": 0.2, "v": 100}]),
                       noi_suy="muot"))
    elif hieu_ung == "nay_manh":
        st.append(dict(base, thong_so="Scale", keyframes=nen([{"t": 0, "v": 50}, {"t": 0.12, "v": 115}, {"t": 0.22, "v": 100}]),
                       noi_suy="muot"))
        st.append(mo(0.067))
    elif hieu_ung in ("truot", "len") and vi_tri:
        vx, vy = vi_tri
        dau = [round(vx - 0.3, 4), vy] if hieu_ung == "truot" else [vx, round(vy + 0.05, 4)]
        d = 0.22 if hieu_ung == "truot" else 0.25
        st.append(dict(base, thong_so="Position", keyframes=nen([{"t": 0, "v": dau}, {"t": d, "v": list(vi_tri)}]), noi_suy="muot"))
        st.append(mo(0.1 if hieu_ung == "truot" else 0.12))
    elif hieu_ung == "mo":
        st.append(mo(0.2))
    elif hieu_ung == "chop":
        st.append(mo(round(het, 3), 85, 0))
    elif hieu_ung == "loe":
        st.append(dict(base, hieu_ung="opacity", thong_so="Opacity",
                       keyframes=[{"t": 0, "v": 0}, {"t": round(min(0.3, het / 2), 3), "v": 100}, {"t": round(het, 3), "v": 0}],
                       noi_suy="muot"))
    elif hieu_ung == "chay":
        st.append(dict(base, thong_so="Position", keyframes=[{"t": 0, "v": [-0.5, 0.5]}, {"t": round(het, 3), "v": [0.5, 0.5]}],
                       noi_suy="deu"))
    return st


def nay_chu(sq, track, t0, t1, vi_tri, hieu_ung="nay"):
    """Giữ cho lệnh cũ / script khác gọi: = hieu_ung_chu (Position + nảy lên + hiện dần)."""
    return hieu_ung_chu(sq, track, t0, t1, vi_tri, hieu_ung)


def moc_duyet(tl, pos):
    """Các mốc giây để xuất khung duyệt: hook, giữa từng cảnh (tối đa 8), thẻ kết."""
    T = pos[-1]["ket_thuc"]
    ts = [0.4, min(T - 0.1, tl["hook_t"][1] - 0.3)]
    mids = [(p["bat_dau"] + p["ket_thuc"]) / 2 for p in pos]
    if len(mids) > 8:
        step = len(mids) / 8.0
        mids = [mids[int(i * step)] for i in range(8)]
    ts += mids + [max(0.0, T - 1.0)]
    out = []
    for t in sorted(round(x, 2) for x in ts if 0 <= x < T):
        if not out or t - out[-1] > 0.3:
            out.append(t)
    return out


def lot_c(tl, res_a, mdir):
    sq = seq_name(tl)
    pos = placed(res_a)[:len(tl["shots"])]
    T = pos[-1]["ket_thuc"]
    st = [
        {"lenh": "cat_sau", "sequence": sq, "sau": round(T, 4)},
        {"lenh": "vao_ra", "sequence": sq, "vao": 0, "ra": round(T, 4)},
        {"lenh": "luu_project"},
        {"lenh": "tim_preset", "loc": H264},
    ]
    if not CU:
        st.append({"lenh": "xuat_khung", "sequence": sq, "thoi_diem": moc_duyet(tl, pos), "thu_muc": mdir.rstrip("/") + "/khung",
                   "rong": 540, "tien_to": tl["ten"]})
    st.append({"lenh": "xem_sequence", "ten": sq})
    return wrap(tl, mdir, "c", st, dung_khi_loi=False)


def lot_am(tl, mdir, res_a, lufs, dtg_path):
    """Chỉnh lại âm lượng: cộng dồn độ lệch với lần trước (am-da-chinh.json), mang theo thang đã đo ở lượt a."""
    luu = os.path.join(os.path.dirname(os.path.abspath(dtg_path)), "am-da-chinh.json")
    da_luu = load(luu) if os.path.exists(luu) else {}
    cu = da_luu.get("delta", 0.0)
    bo_lim = "--bo-limiter" in sys.argv
    if bo_lim and "--limiter" in sys.argv:
        raise SystemExit("Chọn --limiter HOẶC --bo-limiter.")
    lim = not bo_lim and ("--limiter" in sys.argv or bool(da_luu.get("limiter")))
    # Mức lưu được ghi lúc SINH lệnh (trước khi lượt chạy). Chạy lại với CÙNG số đo (vd. lượt trước lỗi) thì tính lại từ mức
    # trước lần đó (delta_truoc), không cộng số đo đó thêm lần nữa.
    if lufs == "-":
        moi = cu
        goc = da_luu.get("delta_truoc", cu)
        lufs_luu = da_luu.get("lufs_do")
    else:
        them = -14.0 - float(lufs)
        if abs(them) < 1.0 and not bo_lim and not (lim and not da_luu.get("limiter")):
            raise SystemExit(f"Độ lớn {lufs} LUFS đã trong khoảng -14 ±1, không cần chỉnh.")
        goc = cu
        try:
            cung_so_do = da_luu.get("lufs_do") not in (None, "-") and float(da_luu["lufs_do"]) == float(lufs)
        except (TypeError, ValueError):
            cung_so_do = False
        if cung_so_do and "delta_truoc" in da_luu:
            goc = da_luu["delta_truoc"]
            print(json.dumps({"ghi_chu": f"Cùng số đo {lufs} LUFS với lần trước → tính lại từ mức {goc:+.1f} dB, không cộng dồn lần nữa."},
                             ensure_ascii=False), file=sys.stderr)
        elif cung_so_do:
            # am-da-chinh.json kiểu cũ (chưa có delta_truoc): coi như lần trước đã cộng đúng `them` → trừ ra rồi tính lại
            goc = cu - them
            kep_bien = cu in (DELTA_MIN, DELTA_MAX, DELTA_MAX_LIMITER)
            print(json.dumps({"canh_bao": f"am-da-chinh.json kiểu cũ (chưa có delta_truoc), cùng số đo {lufs} LUFS với lần trước → "
                                          f"coi như lần trước đã cộng {them:+.1f} dB, tính lại từ {goc:+.1f} dB (không cộng hai lần)."
                                          + (" Mức lưu đang ở biên kẹp → mức gốc có thể khác: kiểm lại bằng cách đo bản xuất." if kep_bien else "")},
                             ensure_ascii=False), file=sys.stderr)
        moi = goc + them
        lufs_luu = lufs
    tran = DELTA_MAX_LIMITER if lim else DELTA_MAX
    kep = max(DELTA_MIN, min(tran, moi))
    if kep != moi:
        ly_do = "dù đã có limiter" if lim else "(chưa bật limiter: thêm --limiter để tăng tới +12 dB)"
        print(json.dumps({"canh_bao": f"Cần chỉnh {moi:+.1f} dB nhưng chỉ cho phép {DELTA_MIN:+.0f}…{tran:+.0f} dB {ly_do} "
                                      f"— dùng {kep:+.1f} dB; nếu vẫn nhỏ thì dựng máy chủ."},
                         ensure_ascii=False), file=sys.stderr)
    thang = thang_tu(res_a)
    if not thang:
        raise SystemExit("Kết quả lượt a không có thang âm lượng (bước am_luong do_thang) — chạy am_luong do_thang trước.")
    # Ghi trước khi biết lượt chạy được hay không (lệnh chạy sau trên máy anh). Limiter lỗi → lệnh cứu: am ... - ... --bo-limiter.
    luu_moi = {"delta": kep, "lufs_do": lufs_luu, "delta_truoc": goc, "luc": stamp()}
    if lim:
        luu_moi["limiter"] = True
    json.dump(luu_moi, open(luu, "w", encoding="utf-8"))
    # Limiter (thêm / gỡ) chạy TRƯỚC am_luong: lượt dừng ở bước lỗi đầu tiên → limiter lỗi thì Level chưa bị đổi.
    if lim:
        # Level chỉ hạ (<= mức chuẩn), phần tăng vào Input Boost của limiter → đỉnh không vượt trần dù thứ tự xử lý thế nào
        return wrap(tl, mdir, "am", limiter_steps(tl, max(kep, 0.0)) + am_steps(tl, min(kep, 0.0), thang) + [{"lenh": "luu_project"}])
    st = limiter_steps(tl, 0.0, go=True) if bo_lim else []
    return wrap(tl, mdir, "am", st + am_steps(tl, kep, thang) + [{"lenh": "luu_project"}])


def pick_preset(paths):
    def score(p):
        n = os.path.basename(p).lower()
        s = 0
        if "match source" in n:
            s += 10
        if "high" in n:
            s += 3
        if "adaptive" in n:
            s += 1
        if "4k" in n or "2160" in n:
            s -= 5
        # cùng tên mẫu: ưu tiên bản trong thư mục Premiere (plugin chạy được = Premiere chắc chắn có; Media Encoder thì không)
        if "/adobe premiere pro" in p.replace("\\", "/").lower():
            s += 0.5
        return s
    return sorted(paths, key=score, reverse=True)[0] if paths else None


def lot_d(tl, mdir, res_c):
    sq = seq_name(tl)
    presets = []
    for b in res_c["buoc"]:
        if b.get("lenh") == "tim_preset" and b.get("ok"):
            presets = b["ket_qua"]["preset"]
    if not presets:  # lượt c luồng nhanh không còn tim_preset -> dùng mẫu xuất đã lưu của máy anh (may.json)
        may_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "may.json")
        if os.path.exists(may_p):
            presets = load(may_p).get("preset_h264") or []
    p = pick_preset(presets)
    if not p:
        raise SystemExit("Không tìm thấy mẫu xuất H.264 — xuất tay trong Premiere hoặc dựng trên máy chủ.")
    ten_file = (tl.get("ra") or {}).get("ten_file") or (tl["ten"] + "-premiere.mp4")
    step = {"lenh": "xuat_video", "sequence": sq, "dau_ra": mdir.rstrip("/") + "/" + ten_file, "preset": p, "chi_vao_ra": True}
    if "--ghi-de" in sys.argv:
        step["ghi_de"] = True
    return wrap(tl, mdir, "d", [step])


def main():
    import chung  # bản máy tiệm: stdout UTF-8 trên Windows
    chung.dat_utf8()
    argv = [x for x in sys.argv if not x.startswith("--")]
    lot = argv[1]
    tl, lopj = load(argv[2]), load(argv[3])
    mdir = argv[4]
    if lot == "a":
        cmd, out = lot_a(tl, lopj, mdir), argv[5]
    elif lot == "b":
        cmd, out = lot_b(tl, lopj, mdir, load(argv[5])), argv[6]
    elif lot == "c":
        cmd, out = lot_c(tl, load(argv[5]), mdir), argv[6]
    elif lot == "d":
        cmd, out = lot_d(tl, mdir, load(argv[5])), argv[6]
    elif lot == "am":
        if CU:
            raise SystemExit("Lượt am cần plugin >= 1.3.0.")
        cmd, out = lot_am(tl, mdir, load(argv[5]), argv[6], argv[2]), argv[7]
    else:
        raise SystemExit("lượt phải là a, b, c, d hoặc am")
    if os.path.isdir(out):
        out = os.path.join(out, cmd["id"] + ".json")
    json.dump(cmd, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"id": cmd["id"], "so_buoc": len(cmd["buoc"]), "file": out}, ensure_ascii=False))


if __name__ == "__main__":
    main()
