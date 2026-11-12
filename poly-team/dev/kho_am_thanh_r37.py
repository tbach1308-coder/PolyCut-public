# -*- coding: utf-8 -*-
"""NGUYÊN MẪU r37 (11/11/2026): dựng KHO EFFECT của POLY Cut (thư mục Drive "Kho effect Poly Cut") từ
  - tiếng hiệu ứng TẢI VỀ (CC0): SFX Kit của Wyzowl, gói Kenney (bản chép trên GitHub);
  - tiếng TỰ TẠO (dev/tao_am_thanh_r37.py) và nhạc TỰ TẠO (dev/tao_nhac_r37.py, có mẫu piano Meta CC0);
  - nhạc HoliznaCC0 (CC0, bản chép chuẩn hoá trong kho alvana-audio; bản gốc OpenGameArt / Free Music Archive).
Chuẩn hoá:  hiệu ứng -> WAV 48 kHz 16 bit stereo, cắt lặng đầu / cuối, ĐỈNH −3 dBFS (đỉnh thật ≤ −2 dBTP), độ to tức thời lớn nhất
            (BS.1770, cửa sổ 400 ms) không quá −14 LUFS;  nhạc -> MP3 192 kbps 44,1 kHz, −14 LUFS tích hợp, đỉnh thật ≤ −1,5 dBTP.
Ra (<kho>):  am-thanh/*.wav · nhac/*.mp3 · am-thanh.json · nhac.json (tên, nhóm, giây, BPM, drop, nguồn, tác giả, giấy phép, link, sha256)
            · GIAY-PHEP.md · SHA256SUMS ;  <nghe>/nghe-hieu-ung.mp3 · nghe-nhac.mp3 · thu-tu.json (giờ từng mục trong 2 file nghe).
Chỉ đọc file âm thanh bằng ffmpeg (dữ liệu, không chạy mã tải về).
Dùng:  python dev/kho_am_thanh_r37.py --tai <thư mục tải> --tu-tao <tiếng tự tạo> --nhac-tu-tao <nhạc tự tạo> --kho <kho> --nghe <thư mục nghe>"""
import argparse, hashlib, json, os, subprocess, wave
import numpy as np
from scipy import signal

SR = 48000
LUFS_NHAC = -14.0

NGUON = {
    "sfx-kit": {"ten": "SFX Kit 1.0.0 (Wyzowl)", "tac_gia": "Wyzowl (tự tổng hợp bằng code, không dùng bản ghi)", "giay_phep": "CC0 1.0",
                "link": "https://github.com/wyzowl/sfx-kit", "tai": "https://raw.githubusercontent.com/wyzowl/sfx-kit/main/"},
    "kenney-interface": {"ten": "Kenney · Interface Sounds 1.0", "tac_gia": "Kenney (kenney.nl)", "giay_phep": "CC0 1.0",
                         "link": "https://kenney.nl/assets/interface-sounds",
                         "tai": "https://raw.githubusercontent.com/Calinou/kenney-interface-sounds/master/addons/kenney_interface_sounds/"},
    "kenney-rpg": {"ten": "Kenney · RPG Audio", "tac_gia": "Kenney (kenney.nl)", "giay_phep": "CC0 1.0", "link": "https://kenney.nl/assets/rpg-audio",
                   "tai": "https://raw.githubusercontent.com/Boyquotes/kenney-rpg-audio-for-godot/main/addons/kenney%20rpg%20audio/"},
    "kenney-impact": {"ten": "Kenney · Impact Sounds", "tac_gia": "Kenney (kenney.nl)", "giay_phep": "CC0 1.0",
                      "link": "https://kenney.nl/assets/impact-sounds",
                      "tai": "https://raw.githubusercontent.com/Boyquotes/kenney-impact-sounds-for-godot/main/addons/kenney%20impact%20sounds/"},
    "tu-tao": {"ten": "Poly Store tự tạo (dev/tao_am_thanh_r37.py)", "tac_gia": "Poly Store", "giay_phep": "CC0 1.0", "link": "", "tai": ""},
    "tu-tao-nhac": {"ten": "Poly Store tự tạo (dev/tao_nhac_r37.py; mẫu piano: Meta Piano CC0)", "tac_gia": "Poly Store",
                    "giay_phep": "CC0 1.0", "link": "https://github.com/facebookincubator/Meta-open-sound", "tai": ""},
    "holizna": {"ten": "HoliznaCC0", "tac_gia": "HoliznaCC0 (Holizna)", "giay_phep": "CC0 1.0",
                "link": "https://opengameart.org/users/holizna", "tai": "https://raw.githubusercontent.com/seyedpouramir/alvana-audio/main/music/"},
}

NHOM = {"chuyen": "Chuyển cảnh", "dong": "Dồn / nổ", "nhan": "Nhấn / bật", "thong_bao": "Thông báo", "may": "Máy & đồ vật",
        "tien": "Giá & tiền", "vui": "Vui"}

# khoá file trong kho, nguồn, file gốc (sfx-kit: id), tên tiếng Việt, nhóm, mô tả (gợi ý chỗ dùng)
HIEU_UNG = [
    ("vut-manh", "sfx-kit", "whoosh-fast-hard", "Vút mạnh", "chuyen", "Whoosh nhanh, gắt: cắt cảnh nhanh, lia máy"),
    ("vut-vua", "sfx-kit", "whoosh-medium-medium", "Vút vừa", "chuyen", "Whoosh cân: chuyển cảnh thường"),
    ("vut-dai", "sfx-kit", "whoosh-slow-medium", "Vút dài", "chuyen", "Whoosh chậm 1 giây: chuyển cảnh chậm, mở đầu"),
    ("vut-nhe", "sfx-kit", "whoosh-fast-soft", "Vút nhẹ", "chuyen", "Whoosh nhẹ: dưới giọng đọc, video nhẹ nhàng"),
    ("vut-xoay", "tu-tao", "vut-xoay", "Vút xoáy", "chuyen", "Whoosh có tiếng xoáy, lia trái sang phải"),
    ("quat-gio", "sfx-kit", "swish-medium", "Quất gió", "chuyen", "Swish mảnh: chữ lướt vào, cắt nhanh"),
    ("zip-vao", "sfx-kit", "zip-in-medium", "Zip vào", "chuyen", "Zip dừng gọn: nhãn / ảnh trượt vào"),
    ("hut-vao", "sfx-kit", "reverse-whoosh-medium-strong", "Hút vào", "chuyen", "Whoosh ngược dừng phắt: đặt chỗ dừng ngay chỗ cắt"),
    ("zoom-toi", "sfx-kit", "move-zoom-in", "Zoom tới", "chuyen", "Lao tới gần: zoom vào máy, cận cảnh"),
    ("quet-man-hinh", "sfx-kit", "swipe-medium-firm", "Quẹt màn hình", "chuyen", "Ngón tay quẹt kính: lướt app, vuốt màn hình"),
    ("glitch-ngan", "sfx-kit", "digital-glitch-clear", "Glitch ngắn", "chuyen", "Giật số ngắn: chuyển cảnh công nghệ"),
    ("glitch-giat", "tu-tao", "glitch-giat", "Glitch giật", "chuyen", "Glitch cắt lát dài hơn: lỗi màn hình, đổi cảnh"),
    ("don-2-giay", "sfx-kit", "riser-2s-strong", "Dồn 2 giây", "dong", "Riser mạnh, đỉnh ở cuối: trước khi lộ máy"),
    ("don-4-giay", "sfx-kit", "riser-4s-soft", "Dồn 4 giây nhẹ", "dong", "Riser nhẹ dài: mở hộp chậm"),
    ("don-roi-no", "tu-tao", "don-roi-no", "Dồn rồi nổ", "dong", "Dồn 2 giây rồi nổ trầm: đặt chỗ nổ vào cắt cảnh"),
    ("trong-don", "tu-tao", "trong-don", "Trống dồn", "dong", "Trống dồn rồi chũm choẹ: công bố giá / quà"),
    ("dap-manh", "sfx-kit", "impact-heavy-hard", "Đập mạnh", "dong", "Cú đập gọn, chắc: chữ to đập xuống"),
    ("trong-dien-anh", "sfx-kit", "cinematic-drum-big", "Trống điện ảnh", "dong", "Trống lớn vang: mở đầu hoành tráng"),
    ("bum", "sfx-kit", "boom-hit-strong", "Bùm", "dong", "Tiếng bùm trầm đầy phòng: lộ máy"),
    ("bass-808", "sfx-kit", "bass-808-medium", "Bass 808", "dong", "Bass 808 ngân: nhấn nhịp, khoe máy"),
    ("sub-drop", "sfx-kit", "bass-sub-drop-medium", "Sub drop", "dong", "Trầm rơi sâu: sau riser, chỗ drop"),
    ("drop-phonk", "tu-tao", "drop-phonk", "Drop phonk", "dong", "Cowbell + 808 méo: khoe máy kiểu trend"),
    ("nhip-tim", "tu-tao", "nhip-tim", "Nhịp tim", "dong", "Thình thịch: hồi hộp trước khi lộ giá"),
    ("dem-nguoc", "sfx-kit", "time-countdown", "Đếm ngược 3-2-1", "dong", "3 bíp rồi bíp cao: đếm ngược, mở bán"),
    ("pop-bat", "sfx-kit", "pop-medium-in", "Pop bật", "nhan", "Pop tròn: chữ / sticker bật lên"),
    ("bloop", "sfx-kit", "pop-large-bubble", "Bloop", "nhan", "Bong bóng trầm: biểu tượng hiện"),
    ("cham-man-hinh", "sfx-kit", "click-tap-medium", "Chạm màn hình", "nhan", "Gõ nhẹ lên kính: bấm nút trên màn hình"),
    ("gat-cong-tac", "sfx-kit", "click-toggle-on-firm", "Gạt công tắc", "nhan", "Bật công tắc: bật tính năng, so sánh"),
    ("lat-the", "sfx-kit", "appear-flip-quick", "Lật thẻ", "nhan", "Lật thẻ nhanh: đổi thông số, đổi ảnh"),
    ("so-roi", "sfx-kit", "data-number-land", "Số rơi", "nhan", "Gõ gỗ + ping nhỏ: con số / giá hiện"),
    ("tin-nhan-den", "sfx-kit", "notification-message-in-clear", "Tin nhắn đến", "thong_bao", "Bong bóng + ping: tin nhắn khách"),
    ("thanh-cong", "sfx-kit", "notification-success-clear", "Thành công", "thong_bao", "3 nốt đi lên: xong, chốt đơn"),
    ("dung-roi", "sfx-kit", "notification-success-ding-ding", "Đúng rồi", "thong_bao", "Ding ding: đúng, máy chuẩn"),
    ("sai-roi", "sfx-kit", "notification-failure-knock", "Sai rồi (cốc cốc)", "thong_bao", "2 tiếng gõ đi xuống: không nên, máy dỏm"),
    ("buzzer-sai", "tu-tao", "buzzer-sai", "Buzzer sai", "thong_bao", "Còi sai kiểu game show: hiểu lầm"),
    ("ding-cao", "sfx-kit", "tone-ding-high", "Ding cao", "thong_bao", "Chuông nhỏ trong: điểm nhấn"),
    ("ting-thuy-tinh", "kenney-interface", "glass_001.wav", "Ting thủy tinh", "thong_bao", "Ting kính ngắn (ghi âm thật): điểm nhấn"),
    ("rung-dien-thoai", "sfx-kit", "phone-vibrate-table", "Rung điện thoại", "thong_bao", "Điện thoại rung trên bàn: có cuộc gọi, có khách"),
    ("chup-anh-dslr", "sfx-kit", "mechanical-shutter-heavy", "Chụp ảnh DSLR", "may", "Màn trập máy ảnh: ảnh chụp thử"),
    ("lay-net-chup", "tu-tao", "lay-net-chup", "Lấy nét + chụp", "may", "Bíp lấy nét rồi chụp: khoe camera"),
    ("go-phim-nhanh", "sfx-kit", "keyboard-typing-quick-medium", "Gõ phím nhanh", "may", "Gõ phím nhanh 1,7 giây: laptop, bàn phím iPad"),
    ("mo-hop", "sfx-kit", "props-box-open", "Mở hộp", "may", "Mở nắp hộp giấy: đập hộp"),
    ("boc-seal", "sfx-kit", "props-tape", "Bóc seal / băng keo", "may", "Xé băng keo nhanh: bóc seal, bóc màng"),
    ("tui-vai", "kenney-rpg", "cloth_2.ogg", "Sột soạt túi", "may", "Vải sột soạt (ghi âm thật): lấy máy khỏi túi"),
    ("lat-giay", "kenney-rpg", "book_flip_2.ogg", "Lật giấy", "may", "Lật trang (ghi âm thật): sách hướng dẫn, hoá đơn"),
    ("go-mat-kinh", "kenney-impact", "impact_glass_light_002.ogg", "Gõ mặt kính", "may", "Gõ nhẹ lên kính (ghi âm thật): ép kính, màn hình"),
    ("cam-sac", "tu-tao", "cam-sac", "Cắm sạc", "may", "Tiếng cắm + 2 nốt chuông: cắm sạc, thay pin xong"),
    ("bat-may", "sfx-kit", "digital-power-up", "Bật máy", "may", "Click, tiếng máy lên, ping: mở nguồn"),
    ("ket-tien", "sfx-kit", "money-register", "Két tiền ka-ching", "tien", "Phím, chuông két, ngăn kéo: giá, chốt đơn"),
    ("do-xu", "sfx-kit", "money-coins-pour", "Đổ xu", "tien", "Xu đổ ào: tiết kiệm, giảm giá"),
    ("xu-leng-keng", "kenney-rpg", "handle_coins.ogg", "Xu leng keng", "tien", "Xu trong tay (ghi âm thật): tiền, trả góp"),
    ("ting-gia", "tu-tao", "ting-gia", "Ting giá", "tien", "Chuông sáng lấp lánh: thẻ giá hiện"),
    ("lap-lanh-ngan", "sfx-kit", "shimmer-short-sparkle", "Lấp lánh ngắn", "vui", "Lấp lánh dày: máy đẹp keng, như mới"),
    ("vo-tay", "sfx-kit", "celebration-applause-small", "Vỗ tay", "vui", "Vài người vỗ tay: khách nhận máy"),
    ("phao-giay", "sfx-kit", "celebration-popper", "Pháo giấy", "vui", "Pháo giấy nổ: khai trương, ưu đãi"),
    ("logo-sang", "sfx-kit", "sting-bright-short", "Logo sáng", "vui", "Chuông + lấp lánh 1,5 giây: thẻ kết, logo tiệm"),
    ("dung-bang", "tu-tao", "dung-bang", "Dừng băng", "vui", "Nhạc chậm dần rồi tắt: khựng lại, câu chốt hài"),
    ("scratch-dia", "tu-tao", "scratch-dia", "Scratch đĩa", "vui", "Đĩa cào tới lui: khoan đã, đổi ý"),
    ("huyt-sao-len", "tu-tao", "huyt-sao-len", "Huýt sáo lên", "vui", "Huýt sáo trượt lên: bất ngờ"),
    ("huyt-sao-xuong", "tu-tao", "huyt-sao-xuong", "Huýt sáo xuống", "vui", "Huýt sáo trượt xuống: giá giảm, tụt mood"),
]

# nhạc HoliznaCC0: khoá, file trong kho alvana, tên hiện, nhóm, mô tả, album gốc (OpenGameArt)
NHAC_HOLIZNA = [
    ("hz-happy-dance", "upbeat/happy-dance", "Happy Dance", "Sôi động", "pop điện tử vui, nhanh · máy mới về", "Happy Pop Electronic"),
    ("hz-back-in-the-80s", "upbeat/back-in-the-80s", "Back In The 80s", "Sôi động", "synth pop thập niên 80 · khuyến mãi", "Happy Pop Electronic"),
    ("hz-love-love-love", "upbeat/love-love-love", "Love Love Love", "Vui tươi", "pop điện tử tươi · phụ kiện, quà", "Happy Pop Electronic"),
    ("hz-bouncing", "upbeat/bouncing", "Bouncing", "Vui tươi", "nảy tưng tưng · mẹo hay, ngắn", "Happy Pop Electronic"),
    ("hz-make-money", "funk/make-money", "Make Money", "Sôi động", "funk nhanh, bass chắc · chốt đơn, giá tốt", "Funk"),
    ("hz-morning-coffee", "lofi/morning-coffee", "Morning Coffee", "Chill / lofi", "lofi buổi sáng · kể chuyện, tư vấn", "Lo-Fi And Chill"),
    ("hz-blue-skies", "lofi/blue-skies", "Blue Skies", "Chill / lofi", "lofi vui nhẹ · review nhẹ nhàng", "Happy Lo-Fi"),
    ("hz-new-shoes", "lofi/new-shoes", "New Shoes", "Chill / lofi", "lofi đều, không drop · đọc thông số", "Happy Lo-Fi"),
    ("hz-poor-but-happy", "lofi/poor-but-happy", "Poor, But Happy", "Chill / lofi", "lofi vui, hơi hài · máy giá rẻ", "Happy Lo-Fi"),
    ("hz-machines-with-feelings", "synthwave/machines-with-feelings", "Machines With Feelings", "Công nghệ", "retro wave · review cấu hình", "Retro Wave"),
    ("hz-dear-mr-super-computer", "synthwave/dear-mr-super-computer", "Dear Mr Super Computer", "Công nghệ", "retro wave nhanh · laptop, game", "Retro Wave"),
    ("hz-cyber-anxiety", "synthwave/cyber-anxiety", "Cyber Anxiety", "Công nghệ", "synth tối, dồn · so sánh chip", "Retro Wave"),
    ("hz-credit-cards", "scifi/credit-cards", "Credit Cards", "Công nghệ", "sci-fi nhịp vừa · trả góp, thanh toán", "Sci-Fi"),
    ("hz-hard-mode", "hiphop/hard-mode", "Hard Mode", "Trend có drop", "beat game hip-hop · test game, khoe máy", "Gamer Beats"),
    ("hz-final-level", "hiphop/final-level", "Final Level", "Trend có drop", "beat game dồn mạnh · khoe máy, so sánh", "Gamer Beats"),
    ("hz-night-driving", "calm/night-driving", "Night Driving", "Sang trọng", "nhẹ, sang, đêm · máy cao cấp", "Relaxing Instrumentals"),
    ("hz-advertisements", "chill/advertisements", "Advertisements", "Sang trọng", "chillout quảng cáo · giới thiệu tiệm", "Chillout Instrumentals"),
    ("hz-somethings-out-there", "scifi/somethings-out-there", "Somethings Out There", "Hồi hộp", "sci-fi khám phá · mở hộp, bí ẩn", "Sci-Fi"),
    ("hz-anxiety", "scifi/anxiety", "Anxiety", "Hồi hộp", "sci-fi hồi hộp · đoán giá", "Sci-Fi"),
]


# ------------------------------------------------------------------ đo
def _k_loc(x, sr):
    """Lọc K (BS.1770) cho sr bất kỳ (thiết kế lại theo công thức của pyloudnorm / ITU)."""
    import math
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    K = math.tan(math.pi * fc / sr); Vh = 10 ** (G / 20); Vb = Vh ** 0.4996667741545416
    a0 = 1 + K / Q + K * K
    b1 = [(Vh + Vb * K / Q + K * K) / a0, 2 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0]
    a1 = [1, 2 * (K * K - 1) / a0, (1 - K / Q + K * K) / a0]
    Q2, fc2 = 0.5003270373238773, 38.13547087602444; K = math.tan(math.pi * fc2 / sr)
    a2 = [1, 2 * (K * K - 1) / (1 + K / Q2 + K * K), (1 - K / Q2 + K * K) / (1 + K / Q2 + K * K)]
    y = signal.lfilter(b1, a1, x, axis=0)
    return signal.lfilter([1, -2, 1], a2, y, axis=0)


def m_max(x, sr=SR):
    """Độ to tức thời lớn nhất (LUFS, cửa sổ 400 ms, bước 100 ms)."""
    y = _k_loc(x, sr); p = np.sum(y * y, axis=1)
    w, h = int(0.4 * sr), int(0.1 * sr)
    if len(p) < w:
        p = np.concatenate([p, np.zeros(w - len(p))])
    c = np.concatenate([[0], np.cumsum(p)])
    ms = (c[w::h] - c[:-w:h][: len(c[w::h])]) / w
    return float(-0.691 + 10 * np.log10(max(ms.max(), 1e-12)))


def dinh_that(x):
    up = signal.resample_poly(x, 4, 1, axis=0)
    return float(20 * np.log10(max(np.abs(up).max(), 1e-12)))


def doc(p, sr=SR):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-af", "aresample=resampler=soxr", "-f", "f32le", "-ac", "2", "-ar", str(sr), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype="<f4").reshape(-1, 2).astype(np.float64)


def ghi_wav16(p, x, seed=0):
    d = np.random.default_rng(seed).triangular(-1, 0, 1, x.shape) / 32768
    q = np.clip(np.round((x + d) * 32767), -32768, 32767).astype("<i2")
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(q.tobytes())


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ------------------------------------------------------------------ hiệu ứng
def chuan_hieu_ung(src, dich, dinh_goc=None, seed=0):
    x = doc(src); pk = np.abs(x).max(axis=1)
    top = pk.max(); nguong_dau, nguong_cuoi = top * 10 ** (-50 / 20), top * 10 ** (-60 / 20)
    i0 = int(np.argmax(pk > nguong_dau)); i1 = len(pk) - int(np.argmax(pk[::-1] > nguong_cuoi))
    a = max(0, i0 - int(0.003 * SR)); b = min(len(x), i1 + int(0.01 * SR))
    x = x[a:b].copy()
    if a > 0:
        k = min(len(x), int(0.002 * SR)); x[:k] *= np.linspace(0, 1, k)[:, None]
    k = min(len(x), int(0.015 * SR)); x[-k:] *= np.linspace(1, 0, k)[:, None]
    if dinh_goc is None:   # giây "chạm": đỉnh đường bao 10 ms
        e = np.convolve(np.abs(x).max(axis=1), np.ones(480) / 480, "same"); dinh = float(np.argmax(e) / SR)
    else:
        dinh = max(0.0, dinh_goc - a / SR)
    g = 10 ** (-3 / 20) / np.abs(x).max(); y = x * g
    mm = m_max(y)
    if mm > -14.0:
        y *= 10 ** ((-14.0 - mm) / 20)
    tp = dinh_that(y)
    if tp > -2.0:
        y *= 10 ** ((-2.0 - tp) / 20)
    ghi_wav16(dich, y, seed)
    return {"giay": round(len(y) / SR, 3), "dinh": round(dinh, 3), "dinh_dbfs": round(float(20 * np.log10(np.abs(y).max())), 2),
            "dinh_that_dbtp": round(dinh_that(y), 2), "m_max_lufs": round(m_max(y), 1)}


# ------------------------------------------------------------------ nhạc
def loudnorm_do(p):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", p, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    j = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    return float(j["input_i"]), float(j["input_tp"])


def chuan_nhac(src, dich, ten, tac_gia):
    i, tp = loudnorm_do(src); bu = 0.0
    for _ in range(3):
        af = "volume=%.2fdB,alimiter=limit=0.84:attack=3:release=80:level=false:latency=1,aresample=44100:resampler=soxr" % (LUFS_NHAC - i + bu)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af", af, "-map_metadata", "-1", "-map", "0:a", "-c:a", "libmp3lame", "-b:a", "192k",
                        "-metadata", "title=" + ten, "-metadata", "artist=" + tac_gia, "-metadata", "copyright=CC0 1.0", dich], check=True)
        i2, tp2 = loudnorm_do(dich)
        if abs(i2 - LUFS_NHAC) <= 0.4:
            break
        bu += LUFS_NHAC - i2
    return {"lufs": round(i2, 1), "dinh_that_dbtp": round(tp2, 1)}


def do_bpm(p):
    """BPM đo lại (đường bao onset 11 kHz + tự tương quan 70–180 BPM) để đối chiếu số trong bản đồ nhịp."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-t", "90", "-f", "f32le", "-ac", "1", "-ar", "11025", "-"], capture_output=True, check=True)
    x = np.frombuffer(r.stdout, dtype="<f4").astype(np.float64); h = 128
    f, t, Z = signal.stft(x, 11025, nperseg=1024, noverlap=1024 - h)
    S = np.log1p(np.abs(Z) * 100); fl = np.maximum(np.diff(S, axis=1), 0).sum(axis=0); fl -= np.convolve(fl, np.ones(16) / 16, "same")
    fl = np.maximum(fl, 0); ac = np.correlate(fl, fl, "full")[len(fl) - 1:]
    fps = 11025 / h; lags = np.arange(len(ac)); bpm = 60 * fps / np.maximum(lags, 1)
    m = (bpm >= 70) & (bpm <= 180); k = lags[m][np.argmax(ac[m])]
    return round(60 * fps / k, 1)


# ------------------------------------------------------------------ chính
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tai", required=True); ap.add_argument("--tu-tao", required=True); ap.add_argument("--nhac-tu-tao", required=True)
    ap.add_argument("--kho", required=True); ap.add_argument("--nghe", required=True); ap.add_argument("--chi", default="hieu,nhac,nghe")
    a = ap.parse_args(); chi = a.chi.split(",")
    os.makedirs(os.path.join(a.kho, "am-thanh"), exist_ok=True); os.makedirs(os.path.join(a.kho, "nhac"), exist_ok=True); os.makedirs(a.nghe, exist_ok=True)
    sk = {x["id"]: x for x in json.load(open(os.path.join(a.tai, "sounds.json")))["sounds"]}
    tu = {x["khoa"]: x for x in json.load(open(os.path.join(a.tu_tao, "tu-tao.json")))}
    pj = os.path.join(a.kho, "am-thanh.json")
    if "hieu" in chi:
        ds = {}
        for k, (khoa, ng, goc, ten, nhom, mt) in enumerate(HIEU_UNG):
            N = NGUON[ng]
            if ng == "sfx-kit":
                s = sk[goc]; src = os.path.join(a.tai, "sfx-kit", os.path.basename(s["file"])); dg = s["sync"]["at"]; bg = s["file"]; link = N["tai"] + s["file"]
            elif ng == "tu-tao":
                src = os.path.join(a.tu_tao, goc + ".wav"); dg = tu[goc]["dinh"]; bg = "dev/tao_am_thanh_r37.py › " + goc; link = ""
            else:
                src = os.path.join(a.tai, ng, goc); dg = None; bg = goc; link = N["tai"] + goc
            f = khoa + ".wav"; dich = os.path.join(a.kho, "am-thanh", f)
            do = chuan_hieu_ung(src, dich, dg, seed=k)
            ds[f] = {"khoa": khoa.replace("-", "_"), "ten": ten, "nhom": nhom, "mo_ta": mt, "giay": do["giay"], "dinh": do["dinh"],
                     "cach": "tự tạo" if ng == "tu-tao" else "tải về", "nguon": N["ten"], "tac_gia": N["tac_gia"], "giay_phep": N["giay_phep"],
                     "link": N["link"], "link_tai": link, "ban_goc": bg, "do": {k2: do[k2] for k2 in ("dinh_dbfs", "dinh_that_dbtp", "m_max_lufs")},
                     "bytes": os.path.getsize(dich), "sha256": sha(dich)}
            print("%-18s %5.2fs đỉnh %5.1f dBFS  M max %5.1f LUFS  %s" % (khoa, do["giay"], do["dinh_dbfs"], do["m_max_lufs"], ng), flush=True)
        json.dump({"_ghi_chu": "Kho effect POLY Cut r37 (nguyên mẫu, 11/11/2026): hiệu ứng chuẩn hoá WAV 48 kHz 16 bit, đỉnh −3 dBFS, M max ≤ −14 LUFS. "
                   "Mọi file CC0 1.0 (xem GIAY-PHEP.md). Trường như am-thanh/am-thanh.json của app + nguồn, giấy phép, link, sha256.",
                   "phien_ban": "r37-mau-1", "nhom": NHOM, "ds": ds}, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    nj = os.path.join(a.kho, "nhac.json")
    if "nhac" in chi:
        nh = {}
        tn = json.load(open(os.path.join(a.nhac_tu_tao, "nhac-tu-tao.json"), encoding="utf-8"))
        for khoa, x in tn.items():
            f = khoa + ".mp3"; dich = os.path.join(a.kho, "nhac", f)
            do = chuan_nhac(os.path.join(a.nhac_tu_tao, khoa + ".wav"), dich, x["ten"], "Poly Store (tự tạo)")
            N = NGUON["tu-tao-nhac"]
            nh[f] = {"ten": x["ten"], "phong_cach": x["nhom"], "mo_ta": x["mo_ta"] + " · %d BPM" % x["bpm"], "bpm": x["bpm"], "bpm_do_lai": do_bpm(dich),
                     "giay": x["giay"], "drop": x["drop"], "nhip_dau": x.get("nhip_dau", 0.0), "cach": "tự tạo", "nguon": N["ten"], "tac_gia": N["tac_gia"],
                     "giay_phep": "CC0 1.0 (Poly Store tự tạo bằng dev/tao_nhac_r37.py" + ("; piano: mẫu Meta Piano CC0" if "piano thật" in x["mo_ta"] else "") + ")",
                     "link": "", "lufs": do["lufs"], "dinh_that_dbtp": do["dinh_that_dbtp"], "bytes": os.path.getsize(dich), "sha256": sha(dich)}
            print("%-28s %s" % (f, json.dumps({k2: nh[f][k2] for k2 in ("bpm", "bpm_do_lai", "drop", "lufs")})), flush=True)
        for khoa, src, ten, nhom, mt, album in NHAC_HOLIZNA:
            f = khoa + ".mp3"; dich = os.path.join(a.kho, "nhac", f); sp = os.path.join(a.tai, "holizna", src.replace("/", "__") + ".mp3")
            cue = json.load(open(os.path.join(a.tai, "holizna-cue", src.replace("/", "__") + ".json")))
            do = chuan_nhac(sp, dich, ten, "HoliznaCC0")
            N = NGUON["holizna"]
            nh[f] = {"ten": ten, "phong_cach": nhom, "mo_ta": mt + " · %d BPM" % round(cue["bpm"]), "bpm": round(cue["bpm"], 1), "bpm_do_lai": do_bpm(dich),
                     "giay": round(cue["dur"], 2), "drop": [round(d, 2) for d in cue.get("drops", [])], "nhip_dau": round(cue["beats"][0], 3),
                     "cach": "tải về", "nguon": "HoliznaCC0 · album \"%s\" (OpenGameArt / Free Music Archive)" % album, "tac_gia": N["tac_gia"],
                     "giay_phep": "CC0 1.0", "link": N["link"], "link_tai": N["tai"] + src + ".mp3", "ban_tai_ve_sha256": sha(sp),
                     "ban_do_nhip": "alvana-audio music/%s.json (MIT)" % src, "lufs": do["lufs"], "dinh_that_dbtp": do["dinh_that_dbtp"],
                     "bytes": os.path.getsize(dich), "sha256": sha(dich)}
            print("%-34s %s" % (f, json.dumps({k2: nh[f][k2] for k2 in ("bpm", "bpm_do_lai", "drop", "lufs")})), flush=True)
        json.dump(nh, open(nj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # SHA256SUMS cho cả kho
    with open(os.path.join(a.kho, "SHA256SUMS"), "w") as fo:
        for thu in ("am-thanh", "nhac"):
            for f in sorted(os.listdir(os.path.join(a.kho, thu))):
                fo.write("%s  %s/%s\n" % (sha(os.path.join(a.kho, thu, f)), thu, f))
    if "nghe" in chi:
        nghe(a)


def nghe(a):
    """2 file nghe thử: hiệu ứng nối nhau (cách 0,6 s im), nhạc mỗi bài 15 s quanh chỗ drop đầu. Ghi giờ từng mục vào thu-tu.json."""
    hj = json.load(open(os.path.join(a.kho, "am-thanh.json"), encoding="utf-8"))["ds"]
    parts, t, tt_ = [np.zeros((int(0.5 * SR), 2))], 0.5, []
    for k, (f, x) in enumerate(hj.items()):
        y = doc(os.path.join(a.kho, "am-thanh", f)); tt_.append({"so": k + 1, "file": f, "ten": x["ten"], "bat_dau": round(t, 2)})
        parts += [y, np.zeros((int(0.6 * SR), 2))]; t += len(y) / SR + 0.6
    tmp = os.path.join(a.nghe, "_h.wav"); ghi_wav16(tmp, np.concatenate(parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-metadata", "title=POLY Cut r37 - nghe hieu ung",
                    os.path.join(a.nghe, "nghe-hieu-ung.mp3")], check=True); os.remove(tmp)
    nj = json.load(open(os.path.join(a.kho, "nhac.json"), encoding="utf-8"))
    parts, t, tn = [np.zeros((int(0.5 * SR), 2))], 0.5, []
    for k, (f, x) in enumerate(nj.items()):
        y = doc(os.path.join(a.kho, "nhac", f)); d = [v for v in x["drop"] if v >= 5.0]
        bd = (d[0] - 6.0) if d else min(20.0, x["giay"] / 4)
        bd = max(0.0, min(bd, len(y) / SR - 15)); s = y[int(bd * SR): int((bd + 15) * SR)].copy()
        fi, fo = int(0.25 * SR), int(1.0 * SR); s[:fi] *= np.linspace(0, 1, fi)[:, None]; s[-fo:] *= np.linspace(1, 0, fo)[:, None]
        tn.append({"so": k + 1, "file": f, "ten": x["ten"], "bat_dau": round(t, 2), "doan_trong_bai": [round(bd, 2), round(bd + 15, 2)],
                   "drop_trong_file_nghe": [round(t + v - bd, 2) for v in x["drop"] if bd <= v < bd + 15]})
        parts += [s, np.zeros((int(0.8 * SR), 2))]; t += 15 + 0.8
    tmp = os.path.join(a.nghe, "_n.wav"); ghi_wav16(tmp, np.concatenate(parts))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-metadata", "title=POLY Cut r37 - nghe nhac",
                    os.path.join(a.nghe, "nghe-nhac.mp3")], check=True); os.remove(tmp)
    json.dump({"hieu_ung": tt_, "nhac": tn}, open(os.path.join(a.nghe, "thu-tu.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("nghe-hieu-ung: %d mục, %.0f s · nghe-nhac: %d bài, %.0f s" % (len(tt_), tt_[-1]["bat_dau"] + 3, len(tn), t))


if __name__ == "__main__":
    main()
