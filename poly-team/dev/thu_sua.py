"""Kiểm lại các lỗi soi được (29/10): trả lời kèm duyệt, câu hỏi theo lượt, giữ chỗ gõ khi đổi thứ tự, nhật ký không lặp,
lý do sau Dừng, câu cuối trên thẻ xong, xong mà không có mp4."""
import json, os, time, datetime, threading, urllib.request
from playwright.sync_api import sync_playwright
T = os.path.dirname(os.path.abspath(__file__))
U = "http://127.0.0.1:8781/"
CLIP = os.path.join(T, "ws/Video/iPad Pro 12.9 M1")
SH = os.path.join(T, "shots-sua"); os.makedirs(SH, exist_ok=True)
errs, kq = [], []
def ok(ten, dk, them=""):
    kq.append(("ĐẠT " if dk else "HỎNG ") + ten + (" · " + str(them) if them else "")); print(kq[-1])
def nhip():
    while True:
        luc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        json.dump({"luc": luc.isoformat() + "Z", "dang_nghe": True, "dang_chay": None, "project": "", "plugin": "1.5.2", "premiere": "26.5.2"},
                  open(os.path.join(T, "ws/poly-premiere/ket-qua/_trang-thai.json"), "w"))
        time.sleep(2)
threading.Thread(target=nhip, daemon=True).start()
def api(path, body=None):
    rq = urllib.request.Request(U + path.lstrip("/"), data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json", "Origin": U.rstrip("/")})
    try:
        return json.load(urllib.request.urlopen(rq))
    except urllib.error.HTTPError as e:
        return dict(json.load(e), _ma=e.code)
def jobs(): return api("api/jobs")["jobs"]
def cho(jid, gd, s=90):
    gd = gd if isinstance(gd, (list, tuple)) else [gd]
    for _ in range(s * 4):
        j = next((x for x in jobs() if x["id"] == jid), None)
        if j and j["giai_doan"] in gd: return j
        time.sleep(0.25)
    raise SystemExit("hết giờ %s %s (đang %s)" % (jid, gd, j and j["giai_doan"]))
def don(ghi, duyet=False, ten=""):
    d = {"thu_muc": CLIP, "clip": [], "ten": ten, "loai": "ban_ipad", "may": "", "gia": "", "hook1": "", "hook2": "", "do_dai": "75-95",
         "kieu_che_do": "xoay_vong", "kieu": {}, "giong": "loi_that", "duong": "premiere", "ghi_chu": ghi, "duyet_truoc": duyet}
    r = api("api/run", d); assert r.get("id"), r; return r["id"]
def the(pg, jid): return pg.locator('.don[data-id="%s"]' % jid)
last_prompt = lambda: open(os.path.join(T, "app/dev/last-prompt.txt"), encoding="utf-8").read()

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1440, "height": 930})
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(800)
    pg.fill("#thu_muc", CLIP); pg.press("#thu_muc", "Enter"); pg.wait_for_timeout(1000)   # để server cho xem ảnh khung

    # 1) kế hoạch chờ duyệt có câu hỏi: không có nút Gửi trả lời riêng; trả lời + hook sửa đi kèm Dựng theo kế hoạch
    a = don("HOIDUYET", True, "Kế hoạch có hỏi"); cho(a, "cho_duyet"); pg.wait_for_timeout(4000)
    c = the(pg, a)
    ok("1a câu hỏi hiện trên thẻ chờ duyệt", c.locator(".hq").count() == 1)
    ok("1b không có nút Gửi trả lời riêng", c.locator('[data-a="hoi-gui"]').count() == 0)
    r = api("api/job/%s/tra-loi" % a, {"chon": {"0": "1"}})
    ok("1c server không cho trả lời riêng lúc chờ duyệt", r.get("_ma") == 400 or "err" in r, r.get("err"))
    c.locator(".ho button").nth(1).click()
    c.locator('input[data-f="hook1"]').fill("iPad M1 rẻ chưa")
    c.screenshot(path=SH + "/1-ke-hoach-co-hoi.png")
    c.locator('[data-a="duyet"]').click(); cho(a, "xong")
    lp = last_prompt()
    ok("1d prompt duyệt có hook sửa", "iPad M1 rẻ chưa" in lp)
    ok("1e prompt duyệt có câu trả lời", "Làm thẻ giá 9tr9" in lp)

    # 2) lựa chọn chưa gửi của lượt trước không dính sang câu hỏi lượt sau
    h = don("THUHOI", False, "Hỏi 2 lượt"); cho(h, "xong"); pg.wait_for_timeout(4000)
    c = the(pg, h)
    ok("6 thẻ xong hiện câu cuối (Đã đổi so với đơn)", "Đã đổi so với đơn" in c.inner_text())
    c.locator(".ho").nth(0).locator("button").nth(1).click()   # chọn nhưng không gửi
    c.locator('[data-a="sua"]').click(); pg.wait_for_timeout(300)
    c.locator('textarea[data-f="fix"]').fill("HOILAI đổi nhạc")
    c.locator('[data-a="sua-gui"]').click(); cho(h, "dang-chay", 10); cho(h, "xong"); pg.wait_for_timeout(4000)
    c = the(pg, h)
    on = c.locator(".ho button.on").all_inner_texts()
    ok("2 câu hỏi lượt mới bắt đầu ở 'đang làm'", len(on) == 1 and on[0].startswith("Giữ nhạc cũ"), on)

    # 3) đang gõ trong thẻ, thứ tự hàng đổi (video khác dừng) -> chữ không mất, vẫn gõ tiếp được
    k = don("", True, "Đang gõ"); cho(k, "cho_duyet"); pg.wait_for_timeout(3500)
    q = don("CHAM", False, "Video chậm"); cho(q, "dang-chay"); pg.wait_for_timeout(4000)
    inp = the(pg, k).locator('input[data-f="hook2"]')
    inp.click(); inp.press("End"); pg.keyboard.type("abc")
    api("api/job/%s/dung" % q, {}); pg.wait_for_timeout(4500)
    pg.keyboard.type("XYZ")
    v = the(pg, k).locator('input[data-f="hook2"]').input_value()
    ok("3 gõ không mất khi hàng đổi thứ tự", v.endswith("abcXYZ"), v)
    idx = pg.evaluate("[...document.querySelectorAll('#ds > .don')].map(e => e.dataset.id)")
    ok("3b thứ tự đúng sau khi dừng (chờ duyệt trước đã dừng)", idx.index(k) < idx.index(q), idx[:5])

    # 4) nhật ký không lặp
    c = the(pg, a)
    if not c.locator('details.menu').count(): c.locator('.dh').click(); pg.wait_for_timeout(400)
    c.locator('details.menu summary').click(); pg.wait_for_timeout(200); c.locator('.mlist [data-a="nk"]').click(); pg.wait_for_timeout(7000)
    n_ui = c.locator(".nk .ev").count()
    n_api = len(api("api/job/%s?since=0" % a)["events"])
    ok("4 nhật ký không lặp sự kiện", n_ui == min(n_api, 60), "%d / %d" % (n_ui, n_api))

    # 5) lỗi đăng nhập -> Chạy tiếp -> Dừng: lý do là của lượt cuối
    l = don("LOI", False, "Lỗi rồi dừng"); cho(l, "loi")
    api("api/job/%s/chay-lai" % l, {}); cho(l, "dang-chay", 10); api("api/job/%s/dung" % l, {}); cho(l, "dung")
    ly = api("api/job/%s?ev=0" % l)["ly_do"]
    ok("5 lý do sau Dừng không lấy lỗi lượt cũ", "đăng nhập" not in ly.lower(), ly)

    # 8) báo xong mà không có video -> Lỗi + Chạy tiếp
    m = don("KHONGMP4", False, "Không có mp4"); j = cho(m, ["xong", "loi"]); pg.wait_for_timeout(4000)
    ok("8a giai đoạn là lỗi", j["giai_doan"] == "loi", j["giai_doan"])
    ok("8b thẻ có Chạy tiếp", the(pg, m).locator('[data-a="tiep"]').count() == 1)
    the(pg, m).screenshot(path=SH + "/8-khong-mp4.png")
    the(pg, m).locator('[data-a="tiep"]').click(); cho(m, "xong")
    ok("8c Chạy tiếp ra video", bool(api("api/job/%s?ev=0" % m)["ket_qua"]))

    pg.screenshot(path=SH + "/9-tong.png")
    b.close()
print("\n".join(kq)); print("lỗi trang:", errs or "không")
