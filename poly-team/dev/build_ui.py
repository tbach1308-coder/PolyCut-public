# -*- coding: utf-8 -*-
"""Build giao dien app: dev/_index.src.html + dev/fonts.css (+ _chon-thu-muc.js/.css) -> ui/index.html
                       dev/_sua-tay.src.html + dev/fonts.css (+ _tien-ich.*, _thu-vien.*, _canh-tt.js) -> ui/sua-tay.html (trang Sua tay)
roi kiem cu phap JS bang node (neu co).

Dung:  python dev/build_ui.py            (chay o thu muc goc app, hoac goi tu bat ky dau)
Sua giao dien thi sua dev/_*.src.html, KHONG sua tay ui/*.html (lan build sau se de mat).
Trang dang mo tu tai lai khi ui/index.html doi (server tra "ui" = mtime trong /api/jobs).
"""
import io, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _mod(duoi):
    """Mô-đun thêm của trang Sửa tay (4/11): mọi file dev/_mod-<tên>.js / .css tự nối sau Thư viện, theo tên.
    Mỗi chức năng mới 1 file riêng -> nhiều người sửa song song không đụng nhau, không phải sửa file này."""
    import glob
    return "".join("\n/* ---- " + os.path.basename(f) + " ---- */\n" + io.open(f, encoding="utf-8").read()
                   for f in sorted(glob.glob(os.path.join(HERE, "_mod-*" + duoi))))

APP = os.path.dirname(HERE)
fonts = io.open(os.path.join(HERE, "fonts.css"), encoding="utf-8").read()
node = shutil.which("node")
if not node:
    print("(khong co node, bo qua kiem cu phap)")

for src_ten, dst_ten in (("_index.src.html", "index.html"), ("_sua-tay.src.html", "sua-tay.html")):
    src = io.open(os.path.join(HERE, src_ten), encoding="utf-8").read()
    if "/*FONTS*/" not in src:
        sys.exit("LOI: %s phai co dong /*FONTS*/ (cho chen @font-face)" % src_ten)
    out = src.replace("/*FONTS*/", fonts, 1)
    # bảng chọn thư mục dùng chung (dev/_chon-thu-muc.js / .css), trang nào có chỗ đánh dấu thì chèn
    out = out.replace("/*CHON_THU_MUC_CSS*/", io.open(os.path.join(HERE, "_chon-thu-muc.css"), encoding="utf-8").read(), 1)
    out = out.replace("/*CHON_THU_MUC_JS*/", io.open(os.path.join(HERE, "_chon-thu-muc.js"), encoding="utf-8").read(), 1)
    # khung canh lề (giao diện TikTok phác) dùng chung
    out = out.replace("/*KHUNG_TIKTOK_JS*/", io.open(os.path.join(HERE, "_khung-tiktok.js"), encoding="utf-8").read(), 1)
    out = out.replace("/*ICON_JS*/", io.open(os.path.join(HERE, "_icon.js"), encoding="utf-8").read(), 1)
    # tiện ích / script (chỉ trang Sửa tay)
    out = out.replace("/*TIEN_ICH_CSS*/", io.open(os.path.join(HERE, "_tien-ich.css"), encoding="utf-8").read(), 1)
    out = out.replace("/*TIEN_ICH_JS*/", io.open(os.path.join(HERE, "_tien-ich.js"), encoding="utf-8").read(), 1)
    # Thư viện bên trái màn Sửa tay (4 khu, 3/11 tối): CSS chèn cuối <style> (thắng các lớp cũ), JS chèn trước lúc mở video
    out = out.replace("/*THU_VIEN_CSS*/", io.open(os.path.join(HERE, "_thu-vien.css"), encoding="utf-8").read()
                      + "\n" + io.open(os.path.join(HERE, "_giong-ai.css"), encoding="utf-8").read() + _mod(".css"), 1)
    out = out.replace("/*THU_VIEN_JS*/", io.open(os.path.join(HERE, "_thu-vien.js"), encoding="utf-8").read()
                      + "\n" + io.open(os.path.join(HERE, "_giong-ai.js"), encoding="utf-8").read()   # giọng đọc AI (3/11): đi cùng Thư viện
                      + _mod(".js"), 1)
    # bảng thuộc tính cảnh đang chọn (tab Cảnh: Hình / Âm thanh / Màu / Chuyển cảnh vào) + khung / màu / âm lượng trong khung xem
    out = out.replace("/*CANH_TT_JS*/", io.open(os.path.join(HERE, "_canh-tt.js"), encoding="utf-8").read(), 1)
    # lớp "làm đẹp" (3/11 tối, anh: "làm lại các phần còn thô của giao diện"): CSS chèn trước </style> CUỐI của mỗi trang -> thắng mọi lớp cũ
    ld = os.path.join(HERE, "_lam-dep.css")
    if os.path.isfile(ld):
        i = out.rfind("</style>")
        out = out[:i] + "\n" + io.open(ld, encoding="utf-8").read() + "\n" + out[i:]
    js = "\n".join(re.findall(r"<script>(.*?)</script>", out, re.S))
    if node:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as t:
            t.write(js)
        r = subprocess.run([node, "--check", t.name], capture_output=True, text=True)
        os.unlink(t.name)
        if r.returncode:
            sys.exit("LOI cu phap JS trong %s, chua ghi ui/%s:\n%s" % (src_ten, dst_ten, r.stderr[-2000:]))
    dst = os.path.join(APP, "ui", dst_ten)
    io.open(dst, "w", encoding="utf-8", newline="\n").write(out)
    print("OK", dst, len(out), "byte")
