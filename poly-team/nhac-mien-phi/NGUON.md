# Nhạc nền miễn phí kèm POLY Cut — nguồn và giấy phép

Ngày tạo: 04/11/2026 (4 bài đầu) · 04/11/2026 tối, r20 (thêm 10 bài, anh: "thư viện hiệu ứng nhạc chuyển cảnh còn ít quá").
Người tạo: Poly Store (Claude viết bộ tổng hợp cho tiệm). Tổng 14 bài, mỗi bài ≥ 60 giây, nối lặp được.

| File | Tên hiện trong app | Phong cách (nhóm) | Nguồn | Giấy phép |
|---|---|---|---|---|
| `poly-nhe-nhang.mp3` | Nhẹ nhàng (lofi chill, 84 BPM, 68,6 giây) | Nhẹ nhàng | TỰ TẠO bằng `dev/tao_nhac.py` | CC0 1.0 |
| `poly-soi-dong.mp3` | Sôi động (pop / house, 120 BPM, 64 giây) | Sôi động | TỰ TẠO bằng `dev/tao_nhac.py` | CC0 1.0 |
| `poly-cong-nghe.mp3` | Công nghệ (review công nghệ, 110 BPM, 69,8 giây) | Công nghệ | TỰ TẠO bằng `dev/tao_nhac.py` | CC0 1.0 |
| `poly-vui-tuoi.mp3` | Vui tươi (ukulele, vỗ tay, chuông, 112 BPM, 68,6 giây) | Vui tươi | TỰ TẠO bằng `dev/tao_nhac.py` | CC0 1.0 |
| `poly-sang-trong.mp3` | Sang trọng (piano, dàn dây, 88 BPM, 65,5 giây) | Sang trọng | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-kham-pha.mp3` | Khám phá (nhịp dồn kiểu phim, dàn dây, 100 BPM, 62,4 giây) | Sang trọng | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-toi-gian.mp3` | Tối giản (pluck dội, sub bass, 100 BPM, 62,4 giây) | Công nghệ | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-hiphop-nhe.mp3` | Hip-hop nhẹ (boom bap, đàn điện, 90 BPM, 64 giây) | Công nghệ | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-nang-dong.mp3` | Năng động (piano nhấn phách, vỗ tay, 124 BPM, 61,9 giây) | Sôi động | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-chill-house.mp3` | Chill house (hợp âm house, 118 BPM, 65,1 giây) | Sôi động | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-dien-tu-nhe.mp3` | Điện tử nhẹ (supersaw nhún nhịp, 140 BPM, 61,7 giây) | Sôi động | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-marimba.mp3` | Marimba vui (marimba, vỗ tay, 104 BPM, 64,6 giây) | Vui tươi | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-lofi-dem.mp3` | Lofi đêm (piano jazz, trống lệch, 76 BPM, 63,2 giây) | Nhẹ nhàng | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |
| `poly-acoustic.mp3` | Acoustic (guitar gảy ngón, 96 BPM, 65 giây) | Nhẹ nhàng | TỰ TẠO bằng `dev/tao_nhac_them.py` | CC0 1.0 |

## Cách tạo (để chắc chắn không dính bản quyền)

- Mọi âm thanh sinh ra từ phép toán trong `dev/tao_nhac.py` / `dev/tao_nhac_them.py` (numpy / scipy): sóng sin, cộng hoạ âm (piano có độ
  lệch dây, marimba, dàn dây, supersaw), FM (đàn điện), Karplus-Strong (dây gảy), tiếng ồn lọc (trống, hi-hat, vỗ tay), tiếng vang
  Schroeder tự viết. KHÔNG dùng file mẫu âm thanh (sample), vòng nhạc (loop), preset hay bản ghi nào lấy từ bên ngoài. Hạt ngẫu nhiên
  cố định: chạy lại ra y hệt.
- Hợp âm là các vòng hợp âm phổ thông (Dmaj7–Bm7–Gmaj7–A6, Am–F–C–G, Ebmaj7–Cm9–Fm7–Bb7…) — vòng hợp âm không có bản quyền.
  Giai điệu là các nốt trong hợp âm, tự đặt.
- 10 bài r20 có khâu hoàn thiện: nén nhẹ cả bài, mở rộng stereo phần cao, ĐUÔI VANG CUỘN VỀ ĐẦU BÀI (bài lặp liền mạch, không hụt
  tiếng vang ở chỗ nối), chuẩn −16 LUFS, mp3 192 kbps.
- Đã đo (không nghe được thì đo): độ to −16 LUFS, đỉnh ≤ −1,5 dBTP, cân trầm / trung / cao, không méo (không mẫu chạm 0 dBFS), không lặng
  dài > 1 giây — `python dev/tao_nhac_them.py --do`.

## Đã tìm nguồn nhạc CC0 / Public Domain ngoài (4/11 tối) — KHÔNG lấy

| Nguồn | Có gì | Lý do không lấy |
|---|---|---|
| github.com/SoundSafari/CC0-1.0-Music | ~9.300 file gom từ freemusicarchive.org, freesound.org, chosic.com, freepd.com, pixbay.com | Kho gom lại, không có giấy phép riêng từng bài; có cả nhạc Pixabay (giấy phép Pixabay, không phải CC0) và chosic (nhiều bài CC BY); README có mục "gỡ bài nếu sai giấy phép" -> không kiểm chắc được từng bài. Trang gốc (freepd.com, freesound.org, archive.org) bị chặn từ máy làm app nên không đối chiếu được. |
| huggingface.co/datasets/mrfakename/cc0-music-captioned | 9.015 bài không lời ("gom từ nhiều trang CC0", có FreePD) | Chỉ có âm thanh + mô tả, không ghi nguồn / tác giả / giấy phép từng bài. |
| huggingface.co/datasets/openmusic/cc0-1.0-music | bản chép kho SoundSafari ở trên | Bị khoá (phải đăng nhập), và cùng vấn đề giấy phép như trên. |

Vì luật "không chắc giấy phép thì không lấy", bộ nhạc kèm app vẫn chỉ gồm nhạc TỰ TẠO. Nhạc của tiệm thì anh tự để vào thư mục nhạc
(Thư viện › Nhạc › Đổi thư mục). KHÔNG lấy gì từ CapCut, TikTok, YouTube Audio Library, Epidemic, Artlist hay nhạc có bản quyền.

## Giấy phép

CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/): Poly Store từ bỏ mọi quyền với 14 file trên. Dùng trong
video thương mại, đăng TikTok / Facebook, sửa, cắt, phát lại thoải mái, không cần ghi nguồn.

Lưu ý: TikTok có thể vẫn gợi ý "nhạc trend" khi đăng; nhạc nền trong app là TUỲ CHỌN, video không có nhạc trừ khi anh thêm.

## Tạo lại

`python dev/tao_nhac.py` (4 bài đầu) và `python dev/tao_nhac_them.py` (10 bài r20; giữ 4 bài cũ, cập nhật `nhac.json`: tên hiện,
mô tả, nhịp, phong cách, giấy phép mà tab Nhạc đọc). `CHI_BAI=poly-sang-trong.mp3 python dev/tao_nhac_them.py` để tạo lại 1 bài.
Cần numpy, scipy, ffmpeg có libmp3lame.

## r37 (11/11/2026, anh duyệt "lấy hết"): thêm 4 bài tự tạo có chỗ DROP (gói sẵn) + 23 bài chỉ ở Kho effect trên Drive

Gói sẵn trong app (dự phòng khi kho Drive chưa đồng bộ / mất mạng), TỰ TẠO bằng `dev/tao_nhac_r37.py`, chuẩn −14 LUFS, MP3 192 kbps:

| File | Tên | Nhóm | BPM | Drop (giây) | Giấy phép |
|---|---|---|---:|---|---|
| `poly-drop-dien-tu.mp3` | Drop điện tử | Trend có drop | 128 | 15,0 · 45,0 | CC0 1.0 (Poly Store) |
| `poly-phonk.mp3` | Phonk | Trend có drop | 130 | 7,4 · 36,9 | CC0 1.0 (Poly Store) |
| `poly-piano-sang-trong.mp3` | Piano sang trọng | Sang trọng | 84 | 22,9 | CC0 1.0 (Poly Store; mẫu piano Meta Piano CC0, github.com/facebookincubator/Meta-open-sound) |
| `poly-corporate.mp3` | Tươi sáng | Vui tươi | 118 | 16,3 · 40,7 | CC0 1.0 (Poly Store; mẫu piano Meta Piano CC0) |

`nhac.json` thêm khoá `drop` (giây drop trong bài) và `nhip_dau` (giây phách đầu) — tab Nhạc dùng để vẽ vạch drop. Kho Drive có thêm 4 bài tự
tạo (future bass, trap, tropical, hồi hộp) + 19 bài **HoliznaCC0** (CC0 1.0, https://opengameart.org/users/holizna — bản chép chuẩn hoá
từ github.com/seyedpouramir/alvana-audio, ghi nguồn từng bài trong `nhac.json` của kho). App tải các bài đó về máy khi anh bấm.
