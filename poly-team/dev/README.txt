POLY DỰNG VIDEO - bộ để sửa app (dành cho Claude / lead agent)
================================================================
Đọc PROJECT.md ở thư mục gốc app trước.

_index.src.html   nguồn giao diện (1 file HTML + CSS + JS thuần) kiểu Bảng dựng video: 3 cột Đơn dựng | phác 9:16 |
                  Hàng dựng (thẻ). CSS = CSS của bang-dung-video.html + phần thêm cho app. Sửa ở đây.
_sua-tay.src.html nguồn trang Sửa tay (/sua-tay, 31/10): xem trước 9:16, timeline cảnh, chữ, phụ đề, kiểu, xuất ffmpeg.
_thu-vien.js/.css Thư viện bên trái màn Sửa tay (3/11 tối, bố cục 4 khu: Thư viện | khung xem | bảng phải, timeline full ngang):
                  tab Clip / Chữ / Chuyển cảnh / Hiệu ứng / Tiện ích. build_ui.py chèn vào chỗ /*THU_VIEN_CSS*/ (cuối <style>) và
                  /*THU_VIEN_JS*/ (trước lúc mở video). Đường chia #keoTrai + tự co / tự thu hàng icon: hopCot() trong _sua-tay.src.html.
                  Bài thử: dev/thu-sua-tay/thu_thu_vien.py [cổng].
fonts.css         10 dòng @font-face Be Vietnam Pro (chèn vào chỗ /*FONTS*/).
build_ui.py       python dev/build_ui.py  -> ui/index.html + ui/sua-tay.html (kiểm cú pháp JS bằng node nếu có).
                  Trang app đang mở tự tải lại khi ui/index.html đổi (anh không đang gõ).
fake_claude.py    CLI giả để thử app không tốn lượt Claude. Trong ô Dặn thêm / Sửa video có chữ:
                    CHAM      bước "Dựng trong Premiere" chờ 15 phút  -> thử trang "đang dựng", xếp hàng, Dừng
                    KHONGTASK không gửi task list                      -> thử ô Tiến độ khi không có bước
                    LOI       chết giữa chừng "Not logged in"          -> thử trang lỗi + nút Đăng nhập
                    THUHOI    câu cuối có "Đã đổi so với đơn" + 2 dòng HOI_FEN -> thử ô Claude hỏi anh
                    KHONGPR   báo LOI=Mở Premiere…                     -> thử lỗi do Premiere chưa mở
                    NENSUA    ket-qua.json có duyet "NÊN SỬA: …"
                    HOIDUYET  kế hoạch chờ duyệt kèm 1 dòng HOI_FEN (trả lời đi kèm nút Dựng theo kế hoạch)
                    HOILAI    mọi lượt xong đều hỏi "Đổi nhạc nền?" (thử câu hỏi lượt sau khác lượt trước)
                    KHONGMP4  lượt đầu báo xong mà không có MP4= / ket-qua.json -> thẻ phải hiện lỗi + Chạy tiếp
                  Đơn có "Cho anh duyệt kế hoạch trước" -> lượt đầu dừng ở kế hoạch (CHO_DUYET=).
                  fake tự tạo mp4 thử 9:16 bằng ffmpeg (có ffmpeg trên PATH) + ket-qua.json đúng hợp đồng.
                  Ghi last-args.json / last-prompt.txt cạnh nó để xem app truyền cờ / prompt gì.

THỬ APP TRONG SANDBOX (máy Claude, không đụng app thật)
1. Chép server.py, ui/, prompts/, dev/fake_claude.py sang 1 thư mục trống.
   Giả bộ dựng + plugin: engine/.venv/bin/python (symlink python3), engine/san-sang.json {"ok": true},
   plugin/poly-video/.claude-plugin/plugin.json.
2. config.json trong đó: {"port": 8781, "lenh_claude": ["python3", "<thư mục>/dev/fake_claude.py"],
   "thu_muc_ra": "<thư mục>/ws/ra", "thu_muc_clip": "<thư mục>/ws/Video", "premiere_dir": "<thư mục>/ws/poly-premiere",
   "them_thu_muc": ["<thư mục>/ws/Video"], "hang_giay": 2}
   Clip thử: ffmpeg testsrc2 360x640 vài giây vào ws/Video/<thư mục>/IMG_51xx.MOV.
   Nhịp tim Premiere giả: ghi ws/poly-premiere/ket-qua/_trang-thai.json {"luc": "<giờ UTC ISO>Z", "dang_nghe": true, ...} mỗi 3 giây.
3. python3 server.py & ; mở http://127.0.0.1:8781/ bằng Playwright 1440x930, 1200x800, 900x800, sáng + tối; bắt pageerror.
   Kịch bản đi hết các trường hợp (bản 29/10): dev/thu_bang.py + dev/thu_sua.py (chép ra thư mục sandbox) (dựng + hỏi, sửa, duyệt trước, xếp hàng,
   Dừng, LOI, KHONGPR, Dùng lại cài đặt). Radio / công tắc trong form bị chữ đè: dùng pg.check(..., force=True).
   Giọng AI không cần mạng: chạy server với PYTHONPATH=<thư mục có edge_tts.py giả> (mẫu: tool Poly Video dev/fake_tts),
   chép engine/giong.py + chung.py vào engine/ của sandbox; POST /api/giong-thu trả mp3 bíp.
   Bộ dựng thật: engine/dev/thu_tron_bo.py + engine/dev/gia_plugin.py (Poly Bridge giả), xem engine/KIEM-THU.md.
   Tắt server bằng pid (kill $(cat srv.pid)). KHÔNG dùng pkill -f (giết luôn shell đang chạy lệnh).
   Trang Sửa tay: cần bộ dựng THẬT (engine của bản 1, chép từ máy / Project) vì sua_tay_may.py import ke_hoach / ve_chu /
   chon_kieu; engine/.venv/bin/python -> symlink python3 (có numpy, PIL), config.json "engine_dir" trỏ tới. Video mẫu:
   tạo thư mục <ra>/<slug>/lam/ke-hoach.json đúng hợp đồng (clip testsrc2 / smptehdbars HEVC xoay 90° + nhãn HLG để thử proxy HDR).
   Đi thử bằng Playwright: mở /sua-tay?rieng=1&v=<thư mục video> (không có rieng=1 thì trang tự chuyển về /#sua-tay=<v>, nằm
   trong iframe #stF của index: dùng frame_locator('#stF') / content_frame()), chờ window.ranh() (xem trước đã cập nhật), kéo mép .blk .h.l / .h.r,
   kéo thân .blk để đổi chỗ, #bChia, tab Chữ / Phụ đề, Ctrl+Z, #bNhap / #bXuat (chờ S.xuat.dang = false).
   Kịch bản đã dùng 31/10 (đường dẫn sandbox, sửa lại khi chạy): dev/thu-sua-tay/ (tao_mau.py tạo video mẫu đường Premiere).

PHÁT HÀNH LÊN MÁY SHOP (từ chat có liên kết máy)
- Hỏi anh trước. device_commit_files các file đã đổi vào E:\Tool\poly-dung-video\...
  CHÚ Ý: chép file đã sửa vào 1 thư mục outputs MỚI (vd /mnt/user-data/outputs/r3/) rồi mới commit. Commit lại từ đúng
  stagedPath cũ thì máy nhận bản CŨ (đã gặp 29/10). Commit xong kiểm size bằng device_list_dir.
- Tên file .lnk tạo bằng WScript.Shell phải không dấu ("Poly Dung Video.lnk"): WshShortcut.Save báo 8007007B với chữ có dấu.
- Chỉ đổi ui/ hoặc prompts/: không cần khởi động lại (mỗi lượt / mỗi lần tải trang đọc lại).
- Đổi server.py: video đang dựng không bị ảnh hưởng (claude.exe chạy riêng). Server mới chỉ chạy khi server cũ tắt:
  bấm đúp KHOI-DONG-LAI.vbs (POST /api/tat, chờ tắt, bật lại máy chủ; cửa sổ app đang mở tự tải lại). Explorer cho Claude
  bấm đúp được (computer use, mức "click").
- Đổi engine/ hay plugin/: lượt Claude sau tự dùng bản mới. Đổi thư viện Python thì sửa engine/requirements.txt
  và nhờ anh chạy lại CAI-DAT.bat.
