#!/usr/bin/env python3
"""Việc quanh 1 ĐƠN DỰNG của app (bản máy tiệm): chuẩn bị thư mục + clip + kiểu, bản xem trước kế hoạch, phiên bản mới,
giao (ket-qua.json + lịch sử kiểu). Để agent khỏi tự ghép đường dẫn / JSON bằng tay trong lệnh Bash.

  python don.py chuan-bi <thu_muc_video>/lam/don.json [--chon-lai]
      kiểm đơn, liệt kê clip (thu_muc + clip, trống = mọi video trong thư mục) -> lam/clip.txt; chọn phiên bản v1 (hoặc
      phiên bản đang dở); chọn kiểu bằng chon_kieu (giữ mục đơn đã ghim, kieu_che_do, đường dựng) -> lam/kieu.json
      (đã có thì giữ, --chon-lai = bốc lại). In JSON tóm tắt + dòng THU_MUC_VIDEO=…
  python don.py xem <W>
      từ W/ke-hoach.json (+ canh[].mo_ta, "bo", "ghi_chu_xem" agent ghi thêm) -> <thu_muc_video>/ke-hoach-xem.json; in CHO_DUYET=…
  python don.py phien-ban <W>
      sửa video: tạo phiên bản mới v<n+1>, ghi vào ke-hoach.json (ra.thu_muc, ra.ten_file); in thư mục mới
  python don.py giao <W>
      đọc W/giao.json {duyet, caption, hashtag, ghi_chu} (agent ghi) + số đo thật -> <thu_muc_video>/ket-qua.json, ghi lịch sử
      kiểu (1 lần mỗi phiên bản); in MP4=… và THU_MUC_VIDEO=…
"""
import datetime, glob, json, os, re, subprocess, sys

import chung

HERE = os.path.dirname(os.path.abspath(__file__))
DUOI_VIDEO = (".mov", ".mp4", ".m4v", ".mkv", ".avi", ".mts", ".hevc")
LOAI = ("ban_ipad", "ban_laptop", "meo", "vui")
DO_DAI = {"30-45": [30, 45], "45-60": [45, 60], "75-95": [75, 95]}
CHE_DO = ("xoay_vong", "dung_gu", "tu_chon")
TRUC = ("mo_dau", "chuyen_dong", "nhip", "chuyen_canh", "diem_nhan", "lop_phu", "am_nhan", "thanh_tien_trinh", "bo_font",
        "hoat_hinh", "chu", "phu_de", "ket")
TEN_MUC = {"mo_dau": "Mở đầu", "chuyen_dong": "Chuyển động", "nhip": "Nhịp", "chuyen_canh": "Chuyển cảnh", "chu": "Kiểu chữ",
           "phu_de": "Phụ đề", "ket": "Kết", "diem_nhan": "Điểm nhấn", "lop_phu": "Lớp phủ", "am_nhan": "Âm nhấn",
           "thanh_tien_trinh": "Thanh tiến trình", "bo_font": "Font", "hoat_hinh": "Chữ động", "vi_tri_chu": "Vị trí chữ",
           "mau": "Màu"}
TEN_GIA_TRI = {
    "mo_dau": {"chu_zoom": "Zoom chậm, chữ hiện ngay", "dong_bang": "Đóng băng khung đầu", "montage": "Nháy nhanh 3 cảnh",
               "hoi_truoc": "Câu hỏi mở đầu", "punch_mo": "Bật zoom khung đầu"},
    "chuyen_dong": {"zoom_xen_ke": "Zoom vào / ra xen kẽ", "zoom_vao": "Zoom vào chậm", "punch_nhip": "Cắt cận theo nhịp",
                    "pan_ngang": "Lia ngang nhẹ"},
    "nhip": {"nhanh": "Nhanh (cảnh ≤ 2,5s)", "vua": "Vừa (cảnh ≤ 4s)"},
    "chuyen_canh": {"cat_cung": "Cắt thẳng", "hoa_tan_nhanh": "Hòa tan nhanh", "nhay_trang": "Chớp trắng", "truot_ngang": "Trượt ngang",
                    "truot_doc": "Trượt dọc", "zoom_xuyen": "Zoom xuyên", "lau_mem": "Lau mềm", "mo_tron": "Mở tròn",
                    "mo_chuyen_dong": "Nhòe lia nhanh", "vo_diem": "Vỡ điểm ảnh", "tron_poly": "Trộn chuyển cảnh Film Impact"},
    "chu": {"bong_bong": "Bong bóng thoại xanh", "vien_den": "Chữ trắng viền đen", "dai_trang": "Dải nền trắng",
            "nen_xanh": "Khối xanh Poly", "vang_tieu_de": "Tiêu đề vàng", "toi_gian": "Tối giản", "nhan_lon": "Nhãn lớn vàng",
            "hop_doi": "Hai hộp chồng", "vang_pill": "Chữ vàng + viên thuốc", "the_bia": "Thẻ bìa máy"},
    "phu_de": {"ca_cau": "Cả câu", "cum_ngan": "Cụm ngắn in hoa"},
    "ket": {"the_comment": "Thẻ kêu comment", "the_xanh": "Thẻ địa chỉ xanh", "the_den": "Thẻ địa chỉ tối",
            "vong_lap": "Kết vòng lặp", "khong": "Không thẻ kết"},
    "thanh_tien_trinh": {"co": "Có", "khong": "Không"},
    "diem_nhan": {"khong": "Không", "chop_trang": "Chớp trắng", "rung_nhip": "Rung nhẹ", "glitch_rgb": "Glitch màu",
                  "zoom_dap": "Đập zoom"},
    "lop_phu": {"khong": "Không", "hat_film": "Hạt film", "toi_vien": "Tối viền", "loa_sang": "Lóa vàng"},
    "am_nhan": {"co": "Có", "khong": "Không"},
    "bo_font": {"poly_goc": "Be Vietnam Pro", "tiktok_dam": "Montserrat", "cao_gon": "Anton + Barlow", "cong_nghe": "Kanit",
                "vui_tron": "Baloo 2 + Paytone"},
    "hoat_hinh": {"mov": "Chữ động dựng sẵn", "keyframe": "Keyframe Premiere"},
    "vi_tri_chu": {"tren": "Trên", "giua_tren": "Giữa trên", "giua": "Giữa"},
    "mau": {"trung_tinh": "Giữ màu gốc", "am_nhe": "Ấm nhẹ", "tuong_phan": "Tương phản"},
}
THU_TU_TEN = ("mo_dau", "chuyen_dong", "nhip", "chuyen_canh", "chu", "phu_de", "ket", "diem_nhan", "lop_phu", "am_nhan",
              "thanh_tien_trinh", "bo_font", "hoat_hinh", "vi_tri_chu")


def doc(p, mac_dinh=None):
    try:
        with open(p, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return mac_dinh


def ghi(p, o):
    tam = p + ".tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=1)
    os.replace(tam, p)


def kieu_ten(k):
    """Kiểu dựng -> các dòng tên tiếng Việt ('Kiểu chữ: Bong bóng thoại xanh')."""
    out = []
    chi_pr = ("am_nhan", "hoat_hinh") if (k or {}).get("duong") == "may_chu" else ()  # đường ffmpeg không có 2 mục này
    for m in THU_TU_TEN:
        v = (k or {}).get(m)
        if v is None or m in chi_pr:
            continue
        out.append(f"{TEN_MUC.get(m, m)}: {TEN_GIA_TRI.get(m, {}).get(v, v)}")
    if (k or {}).get("duong"):
        out.append("Đường dựng: " + ("Premiere" if k["duong"] == "premiere" else "ffmpeg trên máy này"))
    return out


def thu_muc_video(W):
    return os.path.dirname(os.path.abspath(W).rstrip("\\/"))


def cac_phien_ban(tm):
    ds = []
    for n in (os.listdir(tm) if os.path.isdir(tm) else []):
        m = re.fullmatch(r"v(\d+)", n)
        if m and os.path.isdir(os.path.join(tm, n)):
            ds.append(int(m.group(1)))
    return sorted(ds)


def da_dung(d):
    """Thư mục phiên bản đã có bản dựng (project / mp4 / lệnh đã gửi)?"""
    if not os.path.isdir(d):
        return False
    return any(n.lower().endswith((".prproj", ".mp4")) for n in os.listdir(d)) or os.path.isdir(os.path.join(d, "lenh-gui"))


def tim_clip(don):
    tm = str(don.get("thu_muc") or "").strip().strip('"')
    if not tm or not os.path.isdir(tm):
        raise SystemExit(f"Không thấy thư mục clip: {tm!r}")
    tat_ca = sorted(n for n in os.listdir(tm) if n.lower().endswith(DUOI_VIDEO) and not n.startswith((".", "~", "._")))
    ten = don.get("clip")
    if isinstance(ten, list):
        ten = ",".join(map(str, ten))
    ten = [x.strip().strip('"') for x in str(ten or "").split(",") if x.strip()]
    if not ten:
        chon = tat_ca
    else:
        chon, thieu = [], []
        theo = {n.lower(): n for n in tat_ca}
        theo_goc = {}
        for n in tat_ca:
            theo_goc.setdefault(os.path.splitext(n)[0].lower(), n)
        for x in ten:
            b = os.path.basename(x).lower()
            n = theo.get(b) or theo_goc.get(os.path.splitext(b)[0] if b.endswith(DUOI_VIDEO) else b)
            (chon.append(n) if n else thieu.append(x))
        if thieu:
            raise SystemExit(f"Không thấy clip trong {tm}: {', '.join(thieu)}. Có: {', '.join(tat_ca[:30])}")
    if not chon:
        raise SystemExit(f"Thư mục {tm} không có file video ({', '.join(DUOI_VIDEO)}).")
    return [chung.xuoi(os.path.abspath(os.path.join(tm, n))) for n in dict.fromkeys(chon)]


def tim_giong_ai(tm):
    """Giọng AI của tool Poly Video (giong-doc.wav + 2-phu-de.srt) trong thư mục clip hoặc 1 cấp con."""
    for d in [tm] + sorted(glob.glob(os.path.join(glob.escape(tm), "*"))):
        w, s = os.path.join(d, "giong-doc.wav"), os.path.join(d, "2-phu-de.srt")
        if os.path.isfile(w):
            return {"wav": chung.xuoi(os.path.abspath(w)), "srt": chung.xuoi(os.path.abspath(s)) if os.path.isfile(s) else None}
    return None


def chuan_bi(don_p, chon_lai=False):
    don = doc(don_p)
    if not isinstance(don, dict):
        raise SystemExit(f"Không đọc được đơn {don_p} (JSON).")
    W = os.path.dirname(os.path.abspath(don_p))
    tm = thu_muc_video(W)
    slug = str(don.get("slug") or "").strip()
    cb = []
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", slug):
        raise SystemExit(f"slug '{slug}' không hợp lệ (chỉ a-z 0-9 . _ -).")
    if os.path.basename(tm).lower() != slug.lower():
        cb.append(f"thư mục video {tm} khác slug {slug}")
    loai = don.get("loai") or "meo"
    if loai not in LOAI:
        raise SystemExit(f"loai '{loai}' lạ (nhận {', '.join(LOAI)}).")
    dd = DO_DAI.get(str(don.get("do_dai") or "").replace(" ", ""))
    if not dd:
        cb.append(f"do_dai '{don.get('do_dai')}' lạ — dùng 45-60")
        dd = DO_DAI["45-60"]
    duong = don.get("duong") or "premiere"
    if duong not in ("premiere", "may_chu"):
        raise SystemExit(f"duong '{duong}' lạ (premiere | may_chu).")
    che_do = don.get("kieu_che_do") or "xoay_vong"
    if che_do not in CHE_DO:
        cb.append(f"kieu_che_do '{che_do}' lạ — dùng xoay_vong")
        che_do = "xoay_vong"
    clips = tim_clip(don)
    with open(os.path.join(W, "clip.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(clips) + "\n")
    mb = round(sum(os.path.getsize(c) for c in clips) / 1e6, 1)
    # phiên bản: v đang dở (chưa dựng) thì dùng tiếp, không thì v mới
    ds = cac_phien_ban(tm)
    so = (ds[-1] if not da_dung(os.path.join(tm, f"v{ds[-1]}")) else ds[-1] + 1) if ds else 1
    tmm = os.path.join(tm, f"v{so}")
    # kiểu
    kieu_p = os.path.join(W, "kieu.json")
    kieu = doc(kieu_p) if not chon_lai else None
    ghim_ds = []
    for m, v in ((don.get("kieu") or {}).items()):
        if m in TRUC and v not in (None, "", "tu_dong"):
            ghim_ds.append(f"{m}={v}")
    if not isinstance(kieu, dict):
        sys.path.insert(0, HERE)
        import chon_kieu as CK
        deck = CK.load(os.path.join(HERE, "kieu_dung.json"), None)
        ghim, _ = CK.doc_ghim(",".join(ghim_ds), deck)
        if che_do == "dung_gu":
            for m, v in CK.DUNG_GU.items():
                ghim.setdefault(m, v)
        kieu = CK.chon(deck, CK.load(os.path.join(HERE, "lich-su-kieu.json"), []), duong, 5, ghim=ghim)
        if ghim:
            kieu["_ghim"] = sorted(ghim)
        for m, v in ghim.items():
            if duong == "premiere" and m in deck["premiere"] and v not in deck["premiere"][m] + CK.GIA_TRI_THEM.get(m, []):
                cb.append(f"{m}={v}: Premiere chưa làm được hiệu ứng này — giữ theo đơn, bản dựng sẽ không có")
            if duong == "may_chu" and v in ((deck.get("chi_premiere") or {}).get(m) or []):
                cb.append(f"{m}={v}: chỉ Premiere làm được — dựng bằng máy (ffmpeg) sẽ bỏ qua")
        ghi(kieu_p, kieu)
    elif kieu.get("duong") != duong:
        cb.append(f"kieu.json đang là đường {kieu.get('duong')}, đơn là {duong} — chạy lại với --chon-lai")
    giong = None
    if don.get("giong") == "giong_ai":
        giong = tim_giong_ai(str(don.get("thu_muc")))
        if giong:
            cb.append("dùng giong-doc.wav có sẵn trong thư mục clip (tool Poly Video), không tạo giọng mới")
        else:   # tạo giọng mới bằng giong.py (edge-tts): Claude viết <W>/loi-doc.txt rồi chạy giong.py
            gd = os.path.join(W, "giong")
            g = str(don.get("giong_ai_ten") or "")
            giong = {"tao": True, "giong": g if re.fullmatch(r"nu|nam|vn-[a-z0-9-]{2,40}", g) else "vn-adam",
                     "toc_do": str(don.get("giong_ai_toc") or "+10%"), "loi_doc": chung.xuoi(os.path.join(W, "loi-doc.txt")),
                     "thu_muc": chung.xuoi(gd), "wav": chung.xuoi(os.path.join(gd, "giong-doc.wav")),
                     "srt": chung.xuoi(os.path.join(gd, "2-phu-de.srt"))}
    mo_hinh = chung.mo_hinh_hoac_none()
    if not mo_hinh:
        cb.append("chưa có máy nghe sherpa (chạy CAI-DAT.bat): phụ đề lời thật sẽ không khớp giờ")
    out = {
        "thu_muc_video": chung.xuoi(tm), "W": chung.xuoi(W), "thu_muc_may": chung.xuoi(tmm), "phien_ban": f"v{so}",
        "ten": slug, "ten_file": f"{slug}-v{so}.mp4", "clip": clips, "so_clip": len(clips), "MB": mb,
        "kieu": kieu, "kieu_ten": kieu_ten(kieu), "do_dai": dd, "duong": duong, "loai": loai,
        "may": don.get("may"), "gia": don.get("gia"), "hook": [don.get("hook1") or "", don.get("hook2") or ""],
        "giong": don.get("giong") or "loi_that", "giong_ai": giong, "ghi_chu": don.get("ghi_chu") or "",
        "duyet_truoc": bool(don.get("duyet_truoc")), "mo_hinh": chung.xuoi(mo_hinh) if mo_hinh else None,
        "font": chung.xuoi(chung.FONT_DIR), "lich_su": chung.xuoi(os.path.join(HERE, "lich-su-kieu.json")), "canh_bao": cb,
    }
    ghi(os.path.join(W, "chuan-bi.json"), out)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("THU_MUC_VIDEO=" + chung.duong(tm))


def text_ket(plan):
    chu = plan.get("chu") or {}
    k = plan.get("kieu") or {}
    if k.get("ket") == "khong" or ("ket" in chu and not chu["ket"]):
        return "Không có thẻ kết"
    if chu.get("ket"):
        return " / ".join(chu["ket"])
    deck = doc(os.path.join(HERE, "kieu_dung.json"), {})
    gu = deck.get("gu_kenh") or {}
    ds = gu.get("ket_mac_dinh") if k.get("ket") == "the_comment" else gu.get("ket_dia_chi")
    return " / ".join(ds or [])


def xem(W):
    plan = doc(os.path.join(W, "ke-hoach.json"))
    if not isinstance(plan, dict):
        raise SystemExit(f"Chưa có {os.path.join(W, 'ke-hoach.json')}.")
    sys.path.insert(0, HERE)
    import ke_hoach as KH
    duong = (plan.get("kieu") or {}).get("duong") or "premiere"
    tl = KH.build(plan, duong)
    tm = thu_muc_video(W)
    chu = plan.get("chu") or {}
    out = {
        "tong_giay": round(tl["T"], 1), "kieu_ten": kieu_ten(plan.get("kieu")),
        "hook": list((chu.get("hook") or ["", ""]) + ["", ""])[:2], "ket": text_ket(plan),
        "canh": [{"clip": os.path.basename(str(c["file"]).replace("\\", "/")), "tu": round(float(c["tu"]), 2),
                  "den": round(float(c["den"]), 2), "mo_ta": c.get("mo_ta") or ""} for c in plan.get("canh") or []],
        "bo": [str(x) for x in plan.get("bo") or []], "ghi_chu": plan.get("ghi_chu_xem") or "",
        "canh_bao": tl.get("canh_bao") or [],
    }
    p = os.path.join(tm, "ke-hoach-xem.json")
    ghi(p, out)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("CHO_DUYET=" + chung.duong(p))


def phien_ban(W):
    kp = os.path.join(W, "ke-hoach.json")
    plan = doc(kp)
    if not isinstance(plan, dict):
        raise SystemExit(f"Chưa có {kp}.")
    tm = thu_muc_video(W)
    ds = cac_phien_ban(tm)
    so = (ds[-1] + 1) if ds else 1
    moi = os.path.join(tm, f"v{so}")
    os.makedirs(moi, exist_ok=True)
    slug = re.sub(r"-v\d+$", "", str(plan.get("ten") or os.path.basename(tm)))
    plan["ra"] = {"thu_muc": chung.xuoi(moi), "ten_file": f"{slug}-v{so}.mp4"}
    ghi(kp, plan)
    print(json.dumps({"phien_ban": f"v{so}", "thu_muc_may": chung.xuoi(moi), "ten_file": plan["ra"]["ten_file"]}, ensure_ascii=False))


def thoi_luong(mp4):
    try:
        r = subprocess.run([chung.FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp4],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        return round(float(r.stdout.strip()), 1)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def giao(W):
    tm = thu_muc_video(W)
    plan = doc(os.path.join(W, "ke-hoach.json")) or {}
    gui = doc(os.path.join(W, "gui.json")) or {}
    gj = doc(os.path.join(W, "giao.json")) or {}
    ra = plan.get("ra") or {}
    duong = (plan.get("kieu") or {}).get("duong") or "premiere"
    mp4 = gj.get("mp4") or (gui.get("mp4_may") if duong == "premiere" else None) or \
        (ra.get("thu_muc") and ra.get("ten_file") and os.path.join(ra["thu_muc"], ra["ten_file"]))
    if not mp4 or not os.path.isfile(mp4):
        raise SystemExit(f"Không thấy mp4 để giao: {mp4}")
    mp4 = chung.duong(os.path.abspath(mp4))
    prproj = gui.get("prproj") if duong == "premiere" and gui.get("prproj") and os.path.isfile(gui["prproj"]) else ""
    hs = doc(os.path.join(W, "ho-so.json")) or {}
    dy = hs.get("duyet") or doc(os.path.join(W, "duyet", "duyet.json")) or {}
    anh = lambda k: chung.duong(dy[k]) if dy.get(k) and os.path.isfile(dy[k]) else ""
    kieu = plan.get("kieu") or {}
    out = {
        "mp4": mp4, "prproj": chung.duong(prproj) if prproj else "", "kieu_ten": kieu_ten(kieu), "giay": thoi_luong(mp4),
        "duyet": gj.get("duyet") or "", "caption": gj.get("caption") or "", "hashtag": gj.get("hashtag") or "",
        "ghi_chu": gj.get("ghi_chu") or "", "khung_dau": anh("khung_dau"), "to_duyet": anh("to_duyet"),
    }
    ghi(os.path.join(tm, "ket-qua.json"), out)
    # lịch sử kiểu: 1 lần mỗi phiên bản (tên = <slug>-v<n>)
    ls_p = os.path.join(HERE, "lich-su-kieu.json")
    ls = doc(ls_p, [])
    ten = os.path.splitext(os.path.basename(mp4))[0]
    if not any(h.get("ten") == ten for h in ls):
        k = {m: v for m, v in kieu.items() if not m.startswith("_")}
        ls.append({"ten": ten, "ngay": datetime.date.today().isoformat(), "kieu": k})
        ghi(ls_p, ls)
    print(json.dumps(dict(out, lich_su=len(ls)), ensure_ascii=False, indent=1))
    print("MP4=" + mp4)
    print("THU_MUC_VIDEO=" + chung.duong(tm))


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] not in ("chuan-bi", "xem", "phien-ban", "giao"):
        raise SystemExit(__doc__)
    if a[0] == "chuan-bi":
        chuan_bi(a[1], "--chon-lai" in a)
    elif a[0] == "xem":
        xem(a[1])
    elif a[0] == "phien-ban":
        phien_ban(a[1])
    else:
        giao(a[1])


if __name__ == "__main__":
    main()
