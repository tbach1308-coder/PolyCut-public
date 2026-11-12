# Âm thanh hiệu ứng kèm POLY Cut — nguồn và giấy phép

Ngày tạo: 04/11/2026 (r20, anh: "thư viện hiệu ứng nhạc chuyển cảnh còn ít quá"). Người tạo: Poly Store (Claude viết bộ tổng hợp cho tiệm).

15 tiếng ngắn (WAV 48 kHz, 16 bit, stereo) TỰ TỔNG HỢP bằng `dev/tao_am_thanh.py` (numpy): sóng sin, tiếng ồn lọc dải, đường bao —
cùng cách với `engine/am_nhan.py`. KHÔNG dùng file mẫu (sample), không lấy từ CapCut / TikTok / thư viện âm thanh nào.
Hạt ngẫu nhiên cố định: chạy lại ra y hệt.

| File | Tên trong app | Nhóm | Mô tả |
|---|---|---|---|
| vut.wav | Vút | Chuyển cảnh | whoosh lướt ngang 0,45s |
| vut-len.wav | Vút lên | Chuyển cảnh | whoosh đi lên 0,55s |
| luot-nhanh.wav | Lướt nhanh | Chuyển cảnh | swoosh ngắn, sáng 0,25s |
| tang-dan.wav | Tăng dần | Chuyển cảnh | riser 1,2s dồn lên rồi dừng |
| bup.wav | Bụp | Nhấn | pop gọn 0,12s |
| pop.wav | Pop bong bóng | Nhấn | bóng nổ 0,14s |
| dap.wav | Đập trầm | Nhấn | thump trầm 0,35s |
| click.wav | Click chuột | Nhấn | nhấn + nhả chuột |
| ting.wav | Ting | Thông báo | chuông G6 0,7s |
| beep.wav | Beep thông báo | Thông báo | báo tin 2 nốt |
| dung.wav | Xong / đúng | Thông báo | rải 3 nốt đi lên |
| chup-anh.wav | Chụp ảnh | Thông báo | màn trập máy ảnh |
| go-phim.wav | Gõ phím | Thông báo | 6 phím gõ 0,8s |
| ting-tien.wav | Ting tiền | Vui | "ka-ching" |
| lap-lanh.wav | Lấp lánh | Vui | chuông cao lấp lánh 1s |

Độ to: mỗi tiếng chỉnh về cùng độ to tức thời lớn nhất (ebur128 M max ≈ −16 LUFS; click / chụp ảnh / gõ phím ngắn nên đo thấp hơn
nhưng đỉnh −1 dBFS), đỉnh ≤ −1 dBFS. Bộ dựng trộn ở 70% × âm lượng anh chọn, rồi cả video chuẩn −14 LUFS như cũ.

## Giấy phép

CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/): Poly Store từ bỏ mọi quyền với 15 file trên. Dùng trong
video thương mại, đăng TikTok / Facebook thoải mái, không cần ghi nguồn.

Tạo lại: `python dev/tao_am_thanh.py` (cần numpy, ffmpeg) -> ghi lại 15 file + `am-thanh.json` (tên, nhóm, mô tả mà tab Âm thanh đọc).

## r37 (11/11/2026, anh: "âm thanh hạn chế quá" — anh duyệt lấy hết): thêm 60 tiếng, tất cả CC0 1.0

Cùng bộ với **Kho effect POLY Cut** trên Drive (kho có thêm nguồn / link / sha256 từng file trong `am-thanh.json` của kho). Chuẩn hoá:
WAV 48 kHz 16 bit stereo, cắt lặng đầu / cuối, đỉnh −3 dBFS, độ to tức thời ≤ −14 LUFS, đỉnh thật ≤ −2 dBTP (`dev/kho_am_thanh_r37.py`).
`am-thanh.json` › `dinh` = giây "chạm" trong file (Thư viện hít chỗ này vào chỗ cắt cảnh). 7 nhóm: Chuyển cảnh · Dồn / nổ · Nhấn / bật ·
Thông báo · Máy & đồ vật · Giá & tiền · Vui (5 tiếng cũ đổi nhóm: tăng dần, đập trầm -> Dồn / nổ; chụp ảnh, gõ phím -> Máy & đồ vật;
ting tiền -> Giá & tiền; tên file không đổi nên kế hoạch cũ dựng y hệt).

| Nguồn | Số tiếng | Giấy phép | Link / cách kiểm |
|---|---:|---|---|
| SFX Kit 1.0.0 — Wyzowl (tổng hợp bằng code, không bản ghi) | 41 | CC0 1.0 | https://github.com/wyzowl/sfx-kit — LICENSE CC0 1.0, sounds.json "license": "CC0-1.0" |
| Kenney — Interface Sounds / RPG Audio / Impact Sounds (ghi âm thật): `ting-thuy-tinh`, `tui-vai`, `lat-giay`, `xu-leng-keng`, `go-mat-kinh` | 5 | CC0 1.0 | https://kenney.nl/assets/interface-sounds · /rpg-audio · /impact-sounds (trang ghi "Creative Commons CC0"; bản tải từ bản chép GitHub Calinou / Boyquotes, LICENSE CC0) |
| Poly Store tự tạo (`dev/tao_am_thanh_r37.py`, numpy / scipy, không mẫu ngoài) | 14 | CC0 1.0 | — |

Tên file, tên hiện, nguồn từng tiếng: `am-thanh.json` (trường `nguon`, `giay_phep`, `sha256`). Chi tiết kiểm giấy phép: NGUON.md của bộ mẫu r37.
