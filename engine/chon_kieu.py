#!/usr/bin/env python3
"""Chọn kiểu dựng ngẫu nhiên có trọng số (kieu_dung.json "trong_so": kiểu đúng gu kênh hay ra hơn),
không trùng tổ hợp chính của N video gần nhất, không lặp kiểu chữ / hiệu ứng của video ngay trước.

Dùng:  python3 chon_kieu.py --lich-su lich-su-kieu.json --ten IMG_5123 [--duong premiere|may_chu] [--n 5] [--ghi]
In ra JSON kiểu đã chọn. --ghi: thêm vào lịch sử (chỉ ghi sau khi video đã giao).

Bản máy tiệm (thêm, không đổi cách bốc cũ):
  --ghim "chu=bong_bong,ket=khong"   giữ cứng các mục chủ shop đã chọn trong đơn (giá trị "tu_dong" / trống = bốc như cũ).
                                     ket=khong = video không có thẻ kết (kế hoạch ghi "ket": null).
                                     Mục ghim không bị luật "không trùng video trước" đổi; các mục còn lại vẫn bốc theo luật.
  --che-do xoay_vong|dung_gu|tu_chon xoay_vong = như cũ; dung_gu = "làm đúng gu kênh" (skill mục 5): chu bong_bong,
                                     ket the_comment, nhip nhanh (trừ mục đã ghim); tu_chon = chỉ dùng ghim
  --ra <file.json>                   ghi kiểu ra file (để kế hoạch đọc, khỏi chép JSON qua dòng lệnh)
  --ghi @<file.json>                 đọc kiểu từ file thay vì chuỗi JSON
"""
import argparse, json, os, random, datetime

import chung  # bản máy tiệm: import để có stdout UTF-8 trên Windows

HERE = chung.HERE
DUNG_GU = {"chu": "bong_bong", "ket": "the_comment", "nhip": "nhanh"}
GIA_TRI_THEM = {"ket": ["khong"]}  # giá trị ghim được dù không có trong muc (ket=khong: không thẻ kết)


def load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def doc_ghim(s, deck):
    """'a=b,c=d' -> ({mục: giá trị}, [cảnh báo]). Giá trị tu_dong / trống = không ghim. Mục / giá trị lạ -> dừng."""
    out, cb = {}, []
    for phan in [x.strip() for x in (s or "").split(",") if x.strip()]:
        if "=" not in phan:
            raise SystemExit(f"--ghim sai: '{phan}' (cần muc=gia_tri)")
        m, v = [x.strip() for x in phan.split("=", 1)]
        if v in ("", "tu_dong", "auto"):
            continue
        if m not in deck["muc"]:
            raise SystemExit(f"--ghim: mục lạ '{m}'. Có: {', '.join(deck['muc'])}")
        hop = list(deck["muc"][m].keys()) + GIA_TRI_THEM.get(m, [])
        if v not in hop:
            raise SystemExit(f"--ghim: {m}={v} không có. {m} nhận: {', '.join(hop)}")
        out[m] = v
    return out, cb


def chon(deck, lich_su, duong="may_chu", n=5, rng=None, ghim=None):
    rng = rng or random.Random()
    ghim = dict(ghim or {})
    muc = deck["muc"]
    chinh = deck["chinh"]
    allowed = {k: list(v.keys()) for k, v in muc.items()}
    if duong == "premiere":
        allowed = {k: list(deck["premiere"].get(k, allowed[k])) for k in allowed}
    else:  # giá trị chỉ Premiere làm được (vd. âm nhấn): máy chủ không bốc
        for m, vs in (deck.get("chi_premiere") or {}).items():
            if m in allowed and isinstance(vs, list):
                allowed[m] = [v for v in allowed[m] if v not in vs] or allowed[m]
    for m in deck.get("khong_boc", []):  # mục chọn theo hình (vd. vị trí chữ), không bốc ngẫu nhiên: lấy giá trị đầu
        if m in allowed:
            allowed[m] = allowed[m][:1]
    for m, v in ghim.items():  # mục ghim: chỉ 1 giá trị
        allowed[m] = [v]
    gan = [h["kieu"] for h in lich_su[-n:]] if lich_su else []
    sigs = {tuple(k.get(c) for c in chinh) for k in gan}
    chu_truoc = gan[-1].get("chu") if gan else None
    truoc = gan[-1] if gan else {}
    ts = deck.get("trong_so", {})
    g = lambda *ms: all(m in ghim for m in ms)  # luật chỉ dính mục ghim: bỏ qua (chủ shop đã chọn)

    def boc(m, vals):
        w = [max(0.0, float(ts.get(m, {}).get(v, 1))) for v in vals]
        if sum(w) <= 0:
            w = [1.0] * len(vals)
        return rng.choices(vals, weights=w, k=1)[0]

    def hop_le(k):
        if len(allowed["chu"]) > 1 and k["chu"] == chu_truoc:
            return False
        if not g(*chinh) and tuple(k[c] for c in chinh) in sigs:
            return False
        # bộ hiệu ứng: tối đa 2 hiệu ứng (chuyển cảnh + điểm nhấn HOẶC lớp phủ), không lặp hiệu ứng của video trước
        if not g("diem_nhan", "lop_phu") and k.get("diem_nhan", "khong") != "khong" and k.get("lop_phu", "khong") != "khong":
            return False
        if not g("chuyen_canh", "diem_nhan") and k.get("chuyen_canh") == "nhay_trang" and k.get("diem_nhan") == "chop_trang":
            return False
        if not g("mo_dau", "ket") and k.get("mo_dau") == "punch_mo" and k.get("ket") == "vong_lap":  # vòng lặp cần khung đầu 100%
            return False
        for m in ("chuyen_canh", "diem_nhan", "lop_phu"):
            if m not in ghim and k.get(m) not in (None, "khong", "cat_cung") and k.get(m) == truoc.get(m):
                return False
        return True

    best = None
    for _ in range(600):
        k = {m: boc(m, v) for m, v in allowed.items()}
        if hop_le(k):
            best = k
            break
    if best is None:  # hết tổ hợp mới: lấy tổ hợp ít trùng nhất
        best = {m: boc(m, v) for m, v in allowed.items()}
        if best.get("diem_nhan", "khong") != "khong" and "lop_phu" not in ghim:
            best["lop_phu"] = "khong"
    best["duong"] = duong
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lich-su", required=True)
    ap.add_argument("--ten", required=True)
    ap.add_argument("--duong", default="may_chu", choices=["premiere", "may_chu"])
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--ghi", help="ghi kiểu (JSON, hoặc @file.json) vào lịch sử thay vì chọn mới")
    ap.add_argument("--ghim", default="", help="giữ cứng các mục: muc=gia_tri,muc2=gia_tri2 (tu_dong = bốc)")
    ap.add_argument("--che-do", default="xoay_vong", choices=["xoay_vong", "dung_gu", "tu_chon"])
    ap.add_argument("--ra", help="ghi kiểu đã chọn ra file JSON")
    a = ap.parse_args()
    deck = load(os.path.join(HERE, "kieu_dung.json"), None)
    lich_su = load(a.lich_su, [])
    if a.ghi:
        if a.ghi.startswith("@"):
            with open(a.ghi[1:], encoding="utf-8") as f:
                k = json.load(f)
            k = k.get("kieu", k) if isinstance(k, dict) else k
        else:
            k = json.loads(a.ghi)
        lich_su.append({"ten": a.ten, "ngay": datetime.date.today().isoformat(), "kieu": k})
        with open(a.lich_su, "w", encoding="utf-8") as f:
            json.dump(lich_su, f, ensure_ascii=False, indent=1)
        print(json.dumps({"da_ghi": len(lich_su)}, ensure_ascii=False))
        return
    ghim, _ = doc_ghim(a.ghim, deck)
    if a.che_do == "dung_gu":
        for m, v in DUNG_GU.items():
            ghim.setdefault(m, v)
    canh_bao = []
    for m, v in ghim.items():
        if a.duong == "premiere" and m in deck["premiere"] and v not in deck["premiere"][m] + GIA_TRI_THEM.get(m, []):
            canh_bao.append(f"{m}={v} Premiere chưa làm được (bản Premiere sẽ không có hiệu ứng này) — giữ theo đơn")
        if a.duong == "may_chu" and v in ((deck.get("chi_premiere") or {}).get(m) or []):
            canh_bao.append(f"{m}={v} chỉ Premiere làm được — dựng máy này sẽ bỏ qua")
    k = chon(deck, lich_su, a.duong, a.n, ghim=ghim)
    if ghim:
        k["_ghim"] = sorted(ghim)
    if a.ra:
        with open(a.ra, "w", encoding="utf-8") as f:
            json.dump(k, f, ensure_ascii=False, indent=1)
    print(json.dumps(dict(k, **({"canh_bao": canh_bao} if canh_bao else {})), ensure_ascii=False))


if __name__ == "__main__":
    main()
