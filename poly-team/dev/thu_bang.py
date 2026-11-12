"""Đi thử giao diện kiểu Bảng dựng video với CLI giả. Đặt file này ở thư mục sandbox (cạnh app/ và ws/ như bước 1-2) rồi: python3 thu_bang.py"""
import json, os, sys, time, datetime, threading, urllib.request
from playwright.sync_api import sync_playwright
T = os.path.dirname(os.path.abspath(__file__))
U = "http://127.0.0.1:8781/"
SH = os.path.join(T, "shots-bang"); os.makedirs(SH, exist_ok=True)
CLIP = os.path.join(T, "ws/Video/iPad Pro 12.9 M1")
errs = []
SONG = {"v": False}
def nhip():
    while True:
        luc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        if not SONG["v"]: luc -= datetime.timedelta(minutes=10)
        json.dump({"luc": luc.isoformat() + "Z", "dang_nghe": True, "dang_chay": None,
                   "project": "E:\\Tool\\poly-edit\\ipad-pro\\v1\\ipad-pro.prproj", "plugin": "1.5.2", "premiere": "26.5.2"},
                  open(os.path.join(T, "ws/poly-premiere/ket-qua/_trang-thai.json"), "w"))
        time.sleep(2)
threading.Thread(target=nhip, daemon=True).start()
def jobs(): return json.load(urllib.request.urlopen(U + "api/jobs"))["jobs"]
def moi_nhat(): return sorted(jobs(), key=lambda j: j["created"] or 0)[-1]
def cho(jid, gd, s=90):
    gd = gd if isinstance(gd, (list, tuple)) else [gd]
    for _ in range(s * 2):
        j = next((x for x in jobs() if x["id"] == jid), None)
        if j and (j["giai_doan"] in gd): return j
        time.sleep(0.5)
    raise SystemExit("hết giờ chờ %s %s, đang %s" % (jid, gd, j and j["giai_doan"]))
def the(pg, jid): return pg.locator('.don[data-id="%s"]' % jid)
def shot(pg, ten, **kw): pg.screenshot(path=os.path.join(SH, ten + ".png"), **kw); print("ảnh", ten)
def mo_thu_muc(pg):
    pg.fill("#thu_muc", CLIP); pg.press("#thu_muc", "Enter"); pg.wait_for_timeout(1800)
def chay(pg, ghi="", duyet=False, cho_clip=True):
    if pg.locator("#clips .ct").count() == 0: mo_thu_muc(pg)
    pg.fill("#ghi_chu", ghi)
    pg.eval_on_selector("#duyet_truoc", "(e, v) => { if (e.checked !== v) { e.checked = v; e.dispatchEvent(new Event('change', {bubbles: true})); } }", duyet)
    truoc = {j["id"] for j in jobs()}
    pg.click("#chay")
    for _ in range(40):
        moi = [j for j in jobs() if j["id"] not in truoc]
        if moi: return moi[0]["id"]
        time.sleep(0.25)
    raise SystemExit("không tạo được video: " + pg.inner_text("#runmsg"))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 930})
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)))
    pg.on("console", lambda m: errs.append("console: " + m.text) if m.type == "error" else None)
    pg.goto(U); pg.wait_for_timeout(1500)
    shot(pg, "01-trong")
    mo_thu_muc(pg)
    cts = pg.locator("#clips .ct"); print("số clip", cts.count())
    cts.nth(2).click(); cts.nth(0).click(); cts.nth(4).click()
    pg.fill("#may", "iPad Pro 12.9 M1 256GB Wifi"); pg.fill("#gia", "13tr9")
    pg.fill("#hook1", "iPad Pro 12.9 M1"); pg.fill("#hook2", "giá mềm hơn Air M2?")
    pg.select_option("#p_chu", "nhan_lon"); pg.eval_on_selector('input[name=giong_chon][value=ai]', "e => { e.checked = true; e.dispatchEvent(new Event('change', {bubbles: true})); }"); pg.wait_for_timeout(900)
    shot(pg, "02-don-co-clip")
    pg.click("#tab_cuoi"); pg.wait_for_timeout(500); pg.locator(".prev").screenshot(path=SH + "/03-phac-cuoi.png"); pg.click("#tab_dau")
    pg.eval_on_selector('input[name=kieu_che_do][value=tu_chon]', "e => { e.checked = true; e.dispatchEvent(new Event('change', {bubbles: true})); }"); pg.wait_for_timeout(300)
    pg.locator("#f").screenshot(path=SH + "/04-form-tu-chon.png")
    # 1) dựng + Claude hỏi
    SONG["v"] = True; time.sleep(2.5)
    a = chay(pg, "THUHOI"); pg.wait_for_timeout(2500)
    shot(pg, "05-dang-dung")
    cho(a, "xong"); pg.wait_for_timeout(4000)
    shot(pg, "06-xong-co-hoi")
    the(pg, a).screenshot(path=SH + "/06b-the-xong.png")
    print("câu hỏi", the(pg, a).locator(".hq").count())
    the(pg, a).locator(".ho").nth(0).locator("button").nth(1).click()
    the(pg, a).locator('[data-a="hoi-gui"]').click(); pg.wait_for_timeout(1500)
    cho(a, "xong"); pg.wait_for_timeout(3500)
    # 2) sửa video
    the(pg, a).locator('[data-a="sua"]').click(); pg.wait_for_timeout(300)
    the(pg, a).locator(".quick button").nth(0).click()
    the(pg, a).screenshot(path=SH + "/07-o-sua.png")
    the(pg, a).locator('[data-a="sua-gui"]').click(); pg.wait_for_timeout(2500)
    the(pg, a).screenshot(path=SH + "/08-dang-sua.png")
    cho(a, "xong"); pg.wait_for_timeout(3500)
    # xem video
    the(pg, a).locator(".vthumb").click(); pg.wait_for_timeout(1200); shot(pg, "09-xem-video"); pg.keyboard.press("Escape")
    # 3) duyệt kế hoạch trước
    c = chay(pg, "", duyet=True); cho(c, "cho_duyet"); pg.wait_for_timeout(4000)
    the(pg, c).scroll_into_view_if_needed(); the(pg, c).screenshot(path=SH + "/10-ke-hoach.png")
    the(pg, c).locator('input[data-f="hook1"]').fill("iPad Pro M1 rẻ chưa?")
    pg.wait_for_timeout(3500)   # gõ dở không bị vẽ lại mất chữ
    print("hook giữ:", the(pg, c).locator('input[data-f="hook1"]').input_value())
    the(pg, c).locator('[data-a="duyet"]').click(); cho(c, "xong"); pg.wait_for_timeout(3500)
    # 4) xếp hàng + dừng
    d = chay(pg, "CHAM"); pg.wait_for_timeout(1500)
    e = chay(pg, "NENSUA"); pg.wait_for_timeout(4000)
    shot(pg, "11-xep-hang")
    the(pg, d).locator('[data-a="dung"]').click(); pg.wait_for_timeout(300)
    the(pg, d).screenshot(path=SH + "/12-nut-dung-hai-lan.png")
    the(pg, d).locator('[data-a="dung"]').click()
    cho(d, "dung"); cho(e, "xong"); pg.wait_for_timeout(3500)
    the(pg, d).screenshot(path=SH + "/13-da-dung.png")
    the(pg, e).screenshot(path=SH + "/14-nen-sua.png")
    # 5) lỗi đăng nhập + lỗi Premiere
    f = chay(pg, "LOI"); cho(f, "loi"); pg.wait_for_timeout(3500)
    the(pg, f).screenshot(path=SH + "/15-loi-dang-nhap.png")
    SONG["v"] = False
    g = chay(pg, "KHONGPR"); cho(g, "loi"); pg.wait_for_timeout(3500)
    the(pg, g).screenshot(path=SH + "/16-loi-premiere.png")
    shot(pg, "17-hang-day-du")
    # 6) dùng lại cài đặt
    if not the(pg, a).locator('details.menu').count(): the(pg, a).locator('.dh').click(); pg.wait_for_timeout(300)
    the(pg, a).locator('details.menu summary').click(); pg.wait_for_timeout(200)
    the(pg, a).locator('.mlist [data-a="dunglai"]').click(); pg.wait_for_timeout(1500)
    print("dùng lại: hook1=%r may=%r clip chọn=%d" % (pg.input_value("#hook1"), pg.input_value("#may"), pg.locator("#clips .ct.on").count()))
    pg.evaluate("window.scrollTo(0,0)"); shot(pg, "18-dung-lai")
    # nhật ký
    the(pg, a).locator('details.menu summary').click(); pg.wait_for_timeout(200)
    the(pg, a).locator('.mlist [data-a="nk"]').click(); pg.wait_for_timeout(1500)
    the(pg, a).screenshot(path=SH + "/19-nhat-ky.png")
    # khổ màn hình + tối
    for w, h in [(1200, 800), (900, 800)]:
        pg.set_viewport_size({"width": w, "height": h}); pg.wait_for_timeout(600); shot(pg, "20-%d" % w, full_page=True)
        sw = pg.evaluate("document.documentElement.scrollWidth"); print("rộng", w, "scrollWidth", sw)
    pg.set_viewport_size({"width": 1440, "height": 930})
    pg.emulate_media(color_scheme="dark"); pg.wait_for_timeout(600); pg.evaluate("window.scrollTo(0,0)"); shot(pg, "21-toi")
    pg.click("#hc"); pg.wait_for_timeout(1200); shot(pg, "22-kiem-may"); pg.keyboard.press("Escape")
    b.close()
print("LỖI TRANG:" if errs else "không lỗi trang", *errs[:20], sep="\n")
