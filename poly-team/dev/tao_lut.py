# -*- coding: utf-8 -*-
"""Tạo BỘ LỌC MÀU (LUT .cube) của POLY Cut bằng ffmpeg (4/11 tối, r20 "thư viện còn ít"): ảnh Hald CLUT (haldclutsrc) đi qua 1 chuỗi
filter ffmpeg tự viết rồi ghi thành .cube 36³ — như 4 LUT Poly có sẵn (03/11). Không lấy LUT / preset của ai: chỉ là phép màu ffmpeg
-> Poly Store phát hành CC0 1.0. Làm ở 16 bit (rgb48) cho khỏi bậc thang 1/255. Chuỗi filter ghi ở dòng đầu mỗi file.
Gu kênh: lọc NHẸ, giữ màu máy thật (đo độ lệch màu bằng xem_lech()).
Dùng:  python dev/tao_lut.py <thư mục luts của bộ dựng>    (chỉ ghi các LUT trong LUT_MOI; LUT có sẵn không đụng)"""
import os, subprocess, sys
import numpy as np

N = 36   # LUT_3D_SIZE (haldclutsrc level 6 -> ảnh 216×216 = 36³ ô)
LUT_MOI = [
    ("poly_trong_treo", "Trong trẻo", "curves=m='0/0 0.08/0.066 0.5/0.52 0.92/0.95 1/1',vibrance=intensity=0.05",
     "Đen sâu hơn chút, sáng trong hơn: nhìn rõ, sạch, không đổi màu máy"),
    ("poly_tuoi_nhe", "Tươi nhẹ", "vibrance=intensity=0.16,eq=contrast=1.03:brightness=0.01",
     "Màu tươi hơn chút (màu nhạt tăng nhiều, màu đậm gần như giữ): cảnh mở hộp, phụ kiện"),
    ("poly_dien_anh", "Điện ảnh nhẹ", "colorbalance=rs=-0.015:bs=0.015:rh=0.012:gh=0.004:bh=-0.012,curves=m='0/0.016 0.25/0.228 0.75/0.772 1/0.986',eq=saturation=0.96",
     "Tối hơi xanh, sáng hơi ấm, đen hơi mờ: kể chuyện, giới thiệu tiệm"),
    ("poly_den_trang", "Đen trắng sang", "colorchannelmixer=rr=0.30:rg=0.59:rb=0.11:gr=0.30:gg=0.59:gb=0.11:br=0.30:bg=0.59:bb=0.11,curves=m='0/0 0.2/0.16 0.5/0.5 0.8/0.84 1/1'",
     "Đen trắng tương phản đẹp: so sánh trước / sau, cảnh hoài niệm (không dùng khi khoe màu máy)"),
    ("poly_ca_phe", "Ấm cà phê", "colortemperature=temperature=5400:mix=0.35,curves=m='0/0.012 0.5/0.5 1/0.976',eq=saturation=0.97",
     "Ấm nâu nhẹ, đen hơi mờ: góc tiệm, bàn gỗ, cảnh tư vấn"),
    ("poly_lanh_cong_nghe", "Lạnh công nghệ", "colortemperature=temperature=7600:mix=0.35,curves=m='0/0 0.25/0.236 0.75/0.764 1/1'",
     "Hơi xanh lạnh, nét tương phản: máy bạc / đen, laptop, cảnh công nghệ"),
    ("poly_sang_trong", "Sang trọng", "curves=m='0/0 0.2/0.168 0.5/0.49 0.85/0.87 1/1',colorbalance=rh=0.01:gh=0.006:bh=-0.01,eq=saturation=0.94",
     "Đen sâu, màu dịu, sáng hơi ánh vàng: máy cao cấp, hộp máy, cận viền kim loại"),
]


def tao(ra, ten, ten_hien, chuoi):
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "haldclutsrc=level=6,format=rgb48le", "-frames:v", "1",
                        "-vf", "format=rgb48le," + chuoi + ",format=rgb48le", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-"],
                       capture_output=True, check=True)
    a = np.frombuffer(r.stdout, "<u2").reshape(-1, 3).astype(np.float64) / 65535.0
    assert len(a) == N ** 3, len(a)
    dong = ["# %s — Poly Store, tự tạo bằng ffmpeg từ chuỗi: %s" % (ten_hien, chuoi),
            "# Giấy phép: CC0 1.0 (public domain) — dùng tự do, kể cả thương mại",
            'TITLE "%s"' % ten, "LUT_3D_SIZE %d" % N, "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    dong += ["%.6f %.6f %.6f" % tuple(x) for x in np.clip(a, 0, 1)]
    p = os.path.join(ra, ten + ".cube")
    with open(p + ".tmp", "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(dong) + "\n")
    os.replace(p + ".tmp", p)
    return p, a


# bảng màu máy hay gặp (sRGB 0–1) để đo LUT có "đổi màu máy" không
MAU_MAY = {"xám không gian": (0.36, 0.37, 0.39), "bạc": (0.84, 0.85, 0.86), "vàng champagne": (0.93, 0.86, 0.74), "xanh dương": (0.30, 0.45, 0.62),
           "tím": (0.66, 0.60, 0.78), "hồng": (0.93, 0.78, 0.78), "xanh lá": (0.42, 0.55, 0.47), "đen": (0.10, 0.10, 0.11),
           "trắng": (0.96, 0.96, 0.96), "da người": (0.85, 0.64, 0.52)}


def _hsv(c):
    import colorsys
    return colorsys.rgb_to_hsv(*c)


def xem_lech(a):
    """-> {màu: (lệch sắc độ °, đổi độ bão hoà, đổi độ sáng)} khi đi qua LUT (nội suy gần nhất ô lưới)."""
    out = {}
    for k, c in MAU_MAY.items():
        i = [int(round(v * (N - 1))) for v in c]
        o = a[i[0] + i[1] * N + i[2] * N * N]
        h0, s0, v0 = _hsv(tuple(x / (N - 1) for x in i)); h1, s1, v1 = _hsv(tuple(o))   # so với đúng ô lưới (khỏi tính sai số làm tròn)
        dh = (h1 - h0 + 0.5) % 1 - 0.5
        out[k] = (round(float(dh) * 360 if s0 > 0.12 else 0.0, 1), round(float(s1 - s0), 3), round(float(v1 - v0), 3))
    return out


if __name__ == "__main__":
    ra = sys.argv[1] if len(sys.argv) > 1 else "."
    for ten, ten_hien, chuoi, _ in LUT_MOI:
        p, a = tao(ra, ten, ten_hien, chuoi)
        print(p, xem_lech(a))
