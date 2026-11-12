#!/usr/bin/env python3
"""Đặt âm lượng TỪNG CLIP cho lượt a của Premiere (video tiếng nói thật, không giọng đọc).

Dùng:  python3 am_tung_clip.py <ke-hoach.json> <lenh-a.json> [--tran -1.7] [--dich -14] [--duoi 2] [--limiter] [--tung-clip]
Sửa lenh-a.json tại chỗ: thêm sau các bước am_luong sẵn có một lệnh am_luong cho mỗi clip
(thoi_diem = giữa clip trên timeline, thang "es"), rồi xem_sequence, rồi luu_project ở bước CUỐI (MCP chỉ tự chạy lại
lệnh có luu_project ở cuối). Ghi bảng đo ra <lenh-a>.am.json. Đo song song 4 luồng (mỗi clip 2 lần gọi ffmpeg).

Mỗi clip: I = độ lớn (ebur128) đoạn nguồn [vào, ra] theo khung; đỉnh = đỉnh mẫu nguồn trong [vào − 0,07; ra + 0,07]
(Premiere làm tròn vào/ra theo khung nên kéo vào ít tiếng clip bên cạnh). db = min(dich − I, tran − đỉnh),
kẹp [−6; +13]; <duoi> clip cuối (khung kết, không lời) ≤ +9; clip im lặng (I < −60) để +6.
Bản xuất ≈ −15,6 LUFS / −1,5 dBTP (trần đỉnh giữ mức tăng lại).

29/10 (anh: "âm thanh còn bị vấp"): một câu nói liền bị tách thành nhiều clip (đổi khung 2–4s, punch / zoom từng phần)
mà mỗi clip đo + đặt mức RIÊNG → ngay chỗ cắt tiếng nhảy 3–6 dB (mô phỏng tiếng nói 24s, nhịp nhanh). Nay: các clip
NỐI LIỀN nhau (cùng file, vào của clip sau = ra của clip trước, lệch ≤ 1 khung) gom thành 1 "đoạn liền", đo I + đỉnh trên cả
đoạn, MỌI clip trong đoạn cùng 1 mức → tiếng liền mạch như chưa cắt. Giữa 2 đoạn liền kề đều có tiếng nói (I > −45),
mức chênh ≤ CHENH_TOI_DA dB (hạ bên cao hơn — chỉ hạ nên không vượt trần đỉnh) để giọng không to nhỏ thất thường giữa cảnh.

--limiter (plugin ≥ 1.4.0, CHƯA KIỂM TRÊN PREMIERE THẬT): db = dich − I (bỏ trần đỉnh, kẹp [−6; +12]); mỗi clip thêm
Hard Limiter (trần −1,5 dB) với Input Boost = phần tăng, Level = phần giảm (Level chỉ hạ — Premiere xử lý Level sau
hiệu ứng, tăng bằng Level sẽ vượt trần). Limiter đặt TRƯỚC am_luong (limiter lỗi thì Level chưa đổi). Nhắm đúng −14.
"""
import json, math, re, subprocess, sys
from chung import FFMPEG
from concurrent.futures import ThreadPoolExecutor

import numpy as np

TRAN_LIMITER = -1.5   # giống lenh_premiere.LIMITER_TRAN
CHENH_TOI_DA = 3.0    # dB: mức chênh tối đa giữa 2 đoạn liền kề cùng có tiếng nói
TANG_LIMITER_MAX = 12.0


def nguon_local(plan, f):
    n = (plan.get("nguon") or {}).get(f) or {}
    return n.get("local") or f


def do_lon(p, a, b):
    r = subprocess.run([FFMPEG, "-v", "info", "-nostats", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", p, "-vn",
                        "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r)
    return float(m[-1]) if m else -70.0


def dinh(p, a, b):
    a = max(0.0, a)
    raw = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", p, "-vn", "-ac", "2",
                          "-f", "f32le", "-"], capture_output=True).stdout
    y = np.frombuffer(raw, np.float32)
    return 20 * math.log10(float(np.abs(y).max()) + 1e-9) if len(y) else -90.0


def clip_canh(buoc):
    """Các bước dat_clip của cảnh (V1/A1) trong lệnh a — không lấy clip giọng đọc (có track_hinh)."""
    return [b for b in buoc if b["lenh"] == "dat_clip" and "track_hinh" not in b]


def doan_lien(clips, fps=30.0):
    """Gom clip nối liền (cùng file, tu clip sau ≈ den clip trước, lệch ≤ 1 khung) -> [[chỉ số clip], ...] theo thứ tự."""
    nhom = []
    for i, b in enumerate(clips):
        if nhom and b["file"] == clips[i - 1]["file"] and abs(float(b["tu"]) - float(clips[i - 1]["den"])) <= 1.0 / fps + 1e-3:
            nhom[-1].append(i)
        else:
            nhom.append([i])
    return nhom


def do_clips(plan, clips, tran=-1.7, dich=-14.0, duoi=2, limiter=False, fps=30.0, gom=True):
    """Đo (song song 4 luồng) -> bảng [{file, tu, den, giua, I, dinh, db, doan}] theo đúng thứ tự clip.
    gom=True (mặc định 29/10): đo + đặt mức theo ĐOẠN LIỀN (doan_lien), mọi clip trong đoạn cùng mức; giới hạn chênh giữa
    2 đoạn có tiếng nói ≤ CHENH_TOI_DA. gom=False: từng clip riêng như trước 29/10 (gây nhảy tiếng giữa câu)."""
    khung = [(math.floor(b["tu"] * fps) / fps, math.floor(b["den"] * fps) / fps) for b in clips]
    nhom = doan_lien(clips, fps) if gom else [[i] for i in range(len(clips))]

    def do(ix):
        p = nguon_local(plan, clips[ix[0]]["file"])
        f0, f1 = khung[ix[0]][0], khung[ix[-1]][1]
        return do_lon(p, f0, f1), dinh(p, f0 - 0.07, f1 + 0.07)

    with ThreadPoolExecutor(4) as ex:
        do_duoc = list(ex.map(do, nhom))
    gs = []
    for j, (ix, (I, P)) in enumerate(zip(nhom, do_duoc)):
        if I < -60:
            g = 6.0
        elif limiter:
            g = dich - I
        else:
            g = min(dich - I, tran - P)
        if all(i >= len(clips) - duoi for i in ix):  # đoạn nằm trọn trong mấy clip cuối (khung kết, không lời)
            g = min(g, 9.0)
        gs.append(max(-6.0, min(TANG_LIMITER_MAX if limiter else 13.0, g)))
    noi = [I > -45 for I, _ in do_duoc]
    for _ in range(len(gs)):  # chênh giữa 2 đoạn có tiếng nói liền kề ≤ CHENH_TOI_DA: hạ bên cao (chỉ hạ, không vượt trần)
        doi = False
        for j in range(1, len(gs)):
            if noi[j] and noi[j - 1] and abs(gs[j] - gs[j - 1]) > CHENH_TOI_DA + 1e-6:
                k = j if gs[j] > gs[j - 1] else j - 1
                gs[k] = max(min(gs[j], gs[j - 1]) + CHENH_TOI_DA, -6.0)
                doi = True
        if not doi:
            break
    o, rows = 0.0, []
    for j, (ix, (I, P)) in enumerate(zip(nhom, do_duoc)):
        for i in ix:
            f0, f1 = khung[i]
            rows.append({"file": clips[i]["file"].split("/")[-1], "tu": clips[i]["tu"], "den": clips[i]["den"],
                         "giua": round(o + (f1 - f0) / 2, 3), "I": round(I, 1), "dinh": round(P, 1), "db": round(gs[j], 1),
                         "doan": j})
            o += f1 - f0
    return rows


def buoc_am(seq, rows, limiter=False, ca_muc_0=False):
    """Bước chỉnh âm từng clip theo rows[].db. limiter: Hard Limiter (Input Boost = phần tăng) TRƯỚC, rồi Level = phần
    giảm. ca_muc_0: ghi cả Level 0 (vòng chỉnh lại phải xóa mức cũ); lượt a thì bỏ (bước ca_track đã đặt 0)."""
    st = []
    if limiter:
        st += [{"lenh": "them_hieu_ung_am", "sequence": seq, "track_tieng": 0, "thoi_diem": r["giua"], "ten": "Hard Limiter",
                "limiter": {"tran_db": TRAN_LIMITER, "tang_db": round(max(r["db"], 0.0), 1)}} for r in rows]
        st += [{"lenh": "am_luong", "sequence": seq, "track_tieng": 0, "thoi_diem": r["giua"], "db": round(min(r["db"], 0.0), 1),
                "thang": "es"} for r in rows if ca_muc_0 or r["db"] < 0]
    else:
        st += [{"lenh": "am_luong", "sequence": seq, "track_tieng": 0, "thoi_diem": r["giua"], "db": r["db"], "thang": "es"}
               for r in rows]
    return st


def chen_vao_a(cmd, them):
    """Chèn bước âm vào cuối lệnh a: … + them + xem_sequence + luu_project (luu_project luôn là bước CUỐI)."""
    st = cmd["buoc"]
    if any(b["lenh"] in ("am_luong", "them_hieu_ung_am") and "thoi_diem" in b for b in st):
        raise SystemExit("Lệnh này đã có âm lượng từng clip.")
    duoi_st = [b for b in st if b["lenh"] == "xem_sequence"]
    st = [b for b in st if b["lenh"] not in ("xem_sequence", "luu_project")]
    cmd["buoc"] = st + them + duoi_st + [{"lenh": "luu_project"}]
    return cmd


def chinh_lai(rows, delta, limiter, tran=-1.7):
    """Vòng chỉnh âm sau khi đo bản xuất: mức mới từng clip = mức lượt a + delta. Không limiter: không vượt trần đỉnh của
    clip (tran − đỉnh; clip đã cao hơn trần thì giữ mức cũ khi tăng) và ≤ +13; có limiter: ≤ +12 (limiter chặn đỉnh)."""
    out = []
    for r in rows:
        g = r["db"] + delta
        if limiter:
            g = min(g, TANG_LIMITER_MAX)
        else:
            g = min(g, max(r["db"], tran - r["dinh"]), 13.0)
        out.append(dict(r, db=round(max(-20.0, g), 1)))
    return out


def main():
    plan_p, lenh_p = sys.argv[1], sys.argv[2]
    arg = lambda k, d: float(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    tran, dich, duoi = arg("--tran", -1.7), arg("--dich", -14.0), int(arg("--duoi", 2))
    lim = "--limiter" in sys.argv
    plan, cmd = json.load(open(plan_p, encoding="utf-8")), json.load(open(lenh_p, encoding="utf-8"))
    clips = clip_canh(cmd["buoc"])
    rows = do_clips(plan, clips, tran, dich, duoi, lim, gom="--tung-clip" not in sys.argv)
    chen_vao_a(cmd, buoc_am(clips[0]["sequence"], rows, lim))
    json.dump(cmd, open(lenh_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(rows, open(lenh_p.rsplit(".", 1)[0] + ".am.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(json.dumps({"so_clip": len(rows), "T": round(sum(r["den"] - r["tu"] for r in rows), 3), "so_buoc": len(cmd["buoc"]),
                      "limiter": lim, "db_min": min(r["db"] for r in rows), "db_max": max(r["db"] for r in rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
