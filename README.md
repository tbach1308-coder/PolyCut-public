# POLY Cut

Trình dựng video TikTok bán hàng của **POLY Store** (máy Windows của tiệm, mở trong trình duyệt, cổng 8790).
Đây là bản **công khai để xem mã nguồn**, chụp 1 lần ngày 12/11/2026 (không cập nhật thêm); nơi làm việc chính là repo riêng.

## Gồm gì
- `poly-team/`: app (máy chủ Python chỉ dùng thư viện chuẩn: `server.py`, `sua_tay.py`…).
  Giao diện viết trong `poly-team/dev/` (`_*.src.html`, `_mod-*.js/.css`), gộp ra `poly-team/ui/*.html` bằng `python3 dev/build_ui.py`.
- `engine/`: bộ dựng dùng chung (ffmpeg, chữ, chuyển cảnh, màu).
- Cách cài / dùng: `poly-team/HUONG-DAN.txt`. Cấu hình mẫu: `poly-team/config.mau.json` (chép thành `config.json`).

## Tài nguyên đi kèm
- Font: giấy phép SIL OFL (xem file giấy phép trong `engine/fonts/`).
- Hiệu ứng âm thanh, nhạc nền: CC0 hoặc tự làm (`poly-team/am-thanh/`, `poly-team/nhac-mien-phi/`).
- `engine/giay-phep/`: giấy phép mã bên ngoài (xfade-easing, MIT).
- Không có tài nguyên của CapCut / TikTok. Không chứa khoá, mật khẩu hay đăng nhập Claude (app dùng Claude qua `claude.exe` của chính máy).

## Bản quyền
Chưa gắn giấy phép mã nguồn mở: mọi quyền thuộc POLY Store. Muốn dùng lại mã, liên hệ chủ repo.
