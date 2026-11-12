---
name: dung-video
description: Dựng video TikTok Poly Store từ clip quay thật NGAY TRÊN MÁY SHOP (Windows) theo đơn của app Poly Dựng Video — phân tích clip, chọn cảnh, viết chữ theo gu kênh @poly.store, mỗi video một kiểu dựng không trùng, dựng trong Premiere qua Poly Bridge (gui_lenh.py) hoặc bằng ffmpeg trên máy, agent riêng duyệt, giao mp4 + ket-qua.json. Dùng cho mọi lượt app gửi: dựng mới, duyệt kế hoạch xong, sửa video, trả lời câu hỏi, chạy tiếp sau lỗi.
---

# Dựng video Poly Store — bản chạy trên máy shop

App "Poly Dựng Video" chạy `claude -p` ngay trên máy có Premiere. Anh (chủ shop) không xem chat, không trả lời được giữa chừng:
làm một mạch, tự quyết chỗ chưa rõ theo gu kênh, chỉ hỏi bằng dòng `HOI_FEN:` ở câu trả lời cuối. Không có MCP, không có
máy chủ, không chép file qua lại: clip đọc tại chỗ, mọi thứ ghi ra thư mục video.

## 0. Ký hiệu trong skill này (thay bằng đường dẫn THẬT, dấu `/`, trong ngoặc kép — không dùng biến shell)
- `<E>` = bộ dựng = dòng "Bộ dựng:" của lệnh lượt (thường `E:/Tool/poly-dung-video/engine`). Script: `python "<E>/<script>.py" …`
- `<V>` = thư mục video (dòng "Thư mục video:", vd `E:/Tool/poly-edit/ipad-pro-129`) · `<W>` = `<V>/lam` (làm việc)
- `<M>` = thư mục phiên bản đang dựng `<V>/v1`, `<V>/v2`… (project Premiere, chữ, lệnh, mp4) — lấy từ `thu_muc_may` mà
  `don.py chuan-bi` / `don.py phien-ban` in ra. Mỗi lần dựng / dựng lại = 1 thư mục v MỚI, không dựng chồng.
- `<MH>` = máy nghe sherpa (trường `mo_hinh` trong `<W>/chuan-bi.json`). `<P>` = thư mục Poly Bridge (dòng "Thư mục Poly Bridge").
Ví dụ 1 lệnh đúng: `python "E:/Tool/poly-dung-video/engine/don.py" chuan-bi "E:/Tool/poly-edit/ipad-pro-129/lam/don.json"`

## 1. Luật viết lệnh (chạy ngầm: lệnh bị chặn quyền = kẹt cả video)
- Mỗi lệnh Bash 1 việc. Đường dẫn đầy đủ, ngoặc kép, dấu `/`. Không `$BIEN`, `{a,b}`, `for`, `&&`, `|`, `;`, không `rm`.
- Chỉ dùng: `python "<E>/….py" …`, `mkdir -p "…"`, `cp "…" "…"`, `mv "…" "…"`, `ls "…"`, `ffmpeg …`, `ffprobe …` (+ Read / Write / Edit).
  Python dài hơn 3 dòng: Write ra `<W>/script/<ten>.py` rồi `python "<W>/script/<ten>.py"`. Không `python -c` nhiều dòng.
- Không ghi ra /tmp, %TEMP%. Không xóa: muốn bỏ thì `mv` vào `_to_delete/` cạnh đó.
- Lệnh lâu chạy TIỀN CẢNH với `timeout: 600000` (Bash tool): `phan_tich`, `nghe`, `dung_premiere`, `gui_lenh`, `sau_xuat`,
  `dung_may_chu`. Không chạy nền. Lệnh bị cắt giữa chừng thì chạy lại ĐÚNG lệnh đó: `phan_tich --them` làm tiếp clip còn lại,
  `gui_lenh` không gửi trùng (bỏ lệnh đã xong, chờ tiếp lệnh đang chạy).
- Không bao giờ: cài / gỡ / cập nhật gì (pip, winget, plugin) — thiếu thì `LOI=` bảo anh chạy CAI-DAT.bat; mở / tắt / lưu
  Premiere bằng tay; ghi file vào `<P>/lenh/` bằng cách nào khác `gui_lenh.py`; sửa clip gốc; đọc `.claude` của user.

## 2. Hợp đồng với app (in đúng dạng, mỗi dấu hiệu 1 dòng riêng trong câu trả lời)
- Tạo `<W>` xong là in ngay `THU_MUC_VIDEO=<V>` (đường dẫn Windows đầy đủ, như `don.py chuan-bi` in ra).
- Task list (TaskCreate / TaskUpdate), tên tiếng Việt đời thường ≤ 8 chữ, không tên file: "Xem clip, nghe lời", "Chọn cảnh,
  viết chữ", "Dựng trong Premiere" (hoặc "Dựng video trên máy"), "Kiểm bản dựng", "Giao video". Xong bước nào cập nhật ngay.
- Câu trả lời cuối: 1–3 câu tiếng Việt, rồi (tùy lượt) các dòng:
  - `Đã đổi so với đơn: <…>` (1 dòng, chỉ khi đổi chữ hook / số so với đơn)
  - tối đa 3 dòng `HOI_FEN: <câu hỏi> | <cách đang làm> | <cách khác>` (≤ 4 lựa chọn, mỗi lựa chọn ≤ 8 chữ) — chỉ việc
    anh mới quyết được: giá, khuyến mãi, cảnh có mặt khách, máy còn trong kho, chữ anh viết mà buộc phải đổi.
  - `LOI=<lý do ngắn, anh cần làm gì>` khi không dựng được. Premiere / bảng Poly Bridge không nhận lệnh (gui_lenh mã 2):
    đúng dòng `LOI=Mở Premiere + bảng Poly Bridge rồi bấm Chạy tiếp`.
  - Dừng chờ duyệt kế hoạch: dòng cuối `CHO_DUYET=<V>/ke-hoach-xem.json` (đường dẫn đầy đủ).
  - Xong video: 2 dòng cuối `MP4=<mp4>` rồi `THU_MUC_VIDEO=<V>` (`don.py giao` in sẵn 2 dòng này: chép nguyên văn).

## 3. Đọc trước (chỉ những file này)
- `<E>/quy-tac/gu-kenh-poly-store.md` — gu kênh. ĐỌC ĐẦU TIÊN; mục **"Anh chốt"** ở cuối thắng mọi luật khác.
- `<E>/quy-tac/so-tay-quay-dung-chung.md`; video bán máy thêm `so-tay-clip-ipad.md` hoặc `so-tay-clip-laptop.md`.
- Khi cần chi tiết: `<E>/quy-tac/README-poly-edit-goc.md` (mẫu ke-hoach.json, mọi trường chữ / kiểu — bản máy chủ cũ, phần
  "stage / MCP / device_*" không dùng ở đây), `<E>/quy-tac/LENH-poly-bridge.md` (lệnh Premiere, mục "đã biết khi chạy thật").

## 4. Nguyên tắc cứng
- Không bịa giá, % pin, bảo hành, thông số. Đơn không có `gia` thì KHÔNG làm thẻ giá. Thông số thẻ tên máy / thẻ bìa chỉ lấy
  từ đơn (`may`, `ghi_chu`) hoặc chữ anh viết. Không "nhất", "rẻ nhất", không so shop khác, không ghép logo Apple.
- Hook anh ghi (hook1 / hook2) dùng ĐÚNG chữ anh (chỉ sửa chính tả). Trống thì tự viết theo gu kênh.
- Mục kiểu trong đơn khác "tu_dong" là ghim: giữ đúng (chon_kieu đã giữ). Không tự đổi kiểu cho "đẹp hơn".
- Giọng AI: ghi "Giọng đọc AI" trong caption và nhắc bật nhãn nội dung AI. Không chèn nhân vật / nhạc / sticker có bản quyền.
- Không để lộ mặt khách / dữ liệu khách trên màn hình máy. Địa chỉ chỉ ở thẻ kết: `125/16/26 Bùi Đình Túy, Bình Thạnh`.

## A. DỰNG MỚI (lượt có `/poly-video:dung-video` + đơn JSON)
**A1. Thư mục + đơn.** `mkdir -p "<W>"` → in `THU_MUC_VIDEO=<V>` → Write `<W>/don.json` = đơn JSON nguyên văn trong lệnh →
TaskCreate các bước. `mkdir -p "<W>/script"` nếu cần viết script.

**A2. Chuẩn bị** (kiểm đơn, liệt kê clip, chọn phiên bản, bốc kiểu có ghim):
`python "<E>/don.py" chuan-bi "<W>/don.json"` → đọc JSON in ra (cũng ở `<W>/chuan-bi.json`): `clip`, `thu_muc_may` (= `<M>`),
`ten`, `ten_file`, `kieu` (cả object, chép nguyên vào kế hoạch), `kieu_ten`, `do_dai` [giây], `hook`, `gia`, `may`, `giong_ai`,
`mo_hinh`, `canh_bao`. Lỗi (không thấy clip / thư mục) → `LOI=`. `mo_hinh` null + có lời nói → `LOI=Thiếu máy nghe: anh chạy
CAI-DAT.bat`. Đơn `kieu_che_do` = dung_gu: script đã ghim chu bong_bong, ket the_comment, nhip nhanh (trừ mục anh ghim).

**A3. Xem clip, nghe lời** (task "Xem clip, nghe lời"):
1. `python "<E>/phan_tich.py" "<W>" --danh-sach "<W>/clip.txt" --them` (timeout 600000) → `<W>/phan-tich.json`; Read từng
   `<W>/to-khung-N.jpg` (mốc giây trên ảnh; ô cuối phải gần độ dài clip, lệch là mốc sai).
   Dùng: `hdr`(+`hdr_trc`) → `nguon.hdr`; `nen_on_dinh` → `nguon.on_dinh` (trung vị rung ~0,18 đã ổn định, 0,3–0,4 cầm tay đi bộ);
   `am_thanh.loai` → `nguon.am_thanh` (nhạc thì không khử ồn); `am_thanh.doan_im` = chỗ im để cắt; `doan_net` = đoạn nét.
2. Lời nói thật: `python "<E>/nghe.py" "<MH>" "<W>/nghe.json" --danh-sach "<W>/clip.txt"` (timeout 600000) → chữ + giờ từng
   từ (bản nháp: tên máy, số hay sai — sửa trước khi làm phụ đề). Giọng AI (`giong_ai` có wav): đọc `2-phu-de.srt` làm phụ đề.
   **Giọng AI tạo mới** (`giong_ai.tao` = true, anh chọn giọng trong app): xem clip xong thì Write `giong_ai.loi_doc` = lời đọc,
   mỗi dòng 1 câu văn nói 8–14 âm tiết, tổng ≈ `do_dai` (≈ 4 âm tiết/giây), hook = câu đầu, câu cuối kêu comment / ghé shop theo
   gu kênh; số viết bằng chữ ("mười ba triệu chín"), tên máy viết theo cách đọc ("ai pát pro em một"); không bịa giá / thông số.
   Rồi `python "<E>/giong.py" "<giong_ai.loi_doc>" "<giong_ai.thu_muc>" --giong <giong_ai.giong> --toc-do <giong_ai.toc_do>`
   (timeout 600000; giọng `vn-…` = VieNeu chạy trên máy, ~1–1,5 s cho mỗi giây tiếng, không cần mạng; `nu` / `nam` = Microsoft,
   cần mạng) → JSON {wav, srt, giay}; từ đây dùng như giọng AI có sẵn: wav = `giong_ai.wav`, phụ đề = `giong_ai.srt`,
   video dài theo `giay`, mỗi câu lời đọc phủ bằng cảnh hợp nội dung. Lỗi mạng (dòng `LOI=` từ giong.py) → chép đúng dòng đó.
   Duyệt trước: thêm lời đọc vào `ghi_chu_xem` của kế hoạch để anh đọc trước khi duyệt.
3. Cần xem kỹ 1 khung: `ffmpeg -v error -y -ss 1.5 -i "<clip>" -frames:v 1 -vf scale=540:-2 "<W>/khung-1.5.jpg"` rồi Read.
   Clip dưới 720p vẫn dựng, ghi vào `ghi_chu` của ket-qua "lần sau gửi file gốc".

**A4. Chọn cảnh, viết chữ** (theo gu kênh; tổng độ dài theo `do_dai` của đơn):
- Cảnh: máy thật, màn pin / cấu hình, thẻ giá, phản ứng người. Bỏ đoạn đi lại, mờ, tối, rung, im. Điểm cắt ở chỗ ít tiếng,
  không cắt giữa câu. Một đoạn quay chạy liền ≤ 8s. Khung đầu phải thấy máy hoặc người thật (không cảnh trống, không khung đen).
- Hook 2 dòng: dòng 1 ≤ 20 ký tự, dòng 2 là phần nhấn (vàng); có số hoặc câu hỏi. `vi_tri_chu` (tren / giua_tren / giua)
  chọn sao cho không che mặt, tay đang thao tác (xem khung 0,3 / 1,5 / 2,8s); ghi vào `kieu.vi_tri_chu`.
- `nhan_chu` ≤ 18 ký tự (Mẹo 1, tên máy, giá thật); `tieu_de` ghim cho video mẹo nhiều bước; `the_gia` CHỈ khi đơn có giá.
- `ket`: bỏ trống = câu mặc định theo kiểu kết; đơn `ket: khong` thì kế hoạch ghi `"ket": null`. Cảnh hay nhất ở cuối thì giảm
  `ket_giay` (mặc định 3,6, tối đa 6) để thẻ không che.
- Phụ đề `phu_de`: luôn IN HOA (máy tự làm); lời thật chép đúng lời, MỖI CÂU NẰM TRỌN TRONG 1 CẢNH, ghi `"canh": <số thứ tự
  cảnh, 0 = đầu>`; mỗi màn 3–6 từ (≤ 8), ≤ 2 dòng; `|` = chỗ ngắt dòng; kiểu `cum_ngan` thì dấu phẩy = chỗ ngắt cụm.
- Write `<W>/ke-hoach.json` (mẫu đầy đủ ở README-poly-edit-goc.md mục "Kế hoạch dựng"):
```json
{"ten": "<ten>", "khung": [1080, 1920], "fps": 30,
 "nguon": {"E:/Video/x/IMG_1.MOV": {"local": "E:/Video/x/IMG_1.MOV", "rong": 1080, "cao": 1920, "co_tieng": true,
           "hdr": true, "hdr_trc": "arib-std-b67", "on_dinh": false, "am_thanh": "tieng_that"}},
 "canh": [{"file": "E:/Video/x/IMG_1.MOV", "tu": 0.4, "den": 4.2, "mo_ta": "cầm máy, nói giá"}],
 "bo": ["IMG_2 0–6s: đi lại, rung"], "ghi_chu_xem": "",
 "chu": {"hook": ["Dòng 1", "Dòng 2"], "brand": true, "nhan_chu": [{"t0": 4, "t1": 6, "chu": "iPad Pro 12.9"}]},
 "phu_de": [{"canh": 0, "t0": 0.4, "t1": 3.9, "chu": "Câu nói thật, đúng lời"}],
 "giong": null, "ket_giay": 3.6, "kieu": {"…": "chép nguyên từ chuan-bi.json"},
 "ra": {"thu_muc": "<M>", "ten_file": "<ten_file>"}}
```
  `nguon` key = `local` = đường dẫn clip y như trong `clip.txt` (đọc tại chỗ). `mo_ta`, `bo`, `ghi_chu_xem` cho bản xem trước.

**A5. Duyệt trước?** Đơn `duyet_truoc: true` (lượt đầu): `python "<E>/don.py" xem "<W>"` → kiểm `canh_bao`, sửa kế hoạch nếu
cần → DỪNG (không dựng). Trả lời ngắn + dòng cuối `CHO_DUYET=<…ke-hoach-xem.json>` (script in sẵn). Không in MP4.

**A6. Dựng — Premiere** (`kieu.duong` = premiere; task "Dựng trong Premiere"):
1. `python "<E>/dung_premiere.py" "<W>" "<M>"` (timeout 600000): canh_tu (giờ từng từ theo lời thật) → ke_hoach → ve_chu ∥ âm
   từng clip → chép chữ / MOV / âm nhấn vào `<M>/chu/`, lệnh a, b1…bN, c, d vào `<M>/lenh-gui/`, `<W>/gui.json`. Đọc `bao`.
   Script DỪNG khi: ve_chu cảnh báo (chữ phải thu nhỏ, lớp đè nhau, từ bị thẻ kết cắt, ra ngoài vùng an toàn), phụ đề vượt cảnh,
   thư mục đã có bản dựng → sửa ke-hoach.json rồi chạy lại cùng lệnh (chưa gửi lệnh nào thì vẫn dùng `<M>` cũ).
   Chỉ cảnh báo màu / nhỏ mà chấp nhận được: thêm `--bo-qua-canh-bao` (ghi lý do vào ghi_chu).
2. `python "<E>/gui_lenh.py" "<W>"` (timeout 600000): gửi tuần tự vào `<P>/lenh/`, chờ `ket-qua/`, in tiến độ + 1 dòng JSON.
   Mã 0 xong · 1 có lệnh lỗi (đọc `buoc_loi`; b lỗi lẻ thì c, d vẫn chạy) · 2 Premiere / bảng không nhận → `LOI=Mở Premiere +
   bảng Poly Bridge rồi bấm Chạy tiếp`, dừng · 3 CHUA_XONG → chạy lại đúng lệnh này · 4 sai đầu vào.
   Premiere văng: gui_lenh tự mở lại project và chạy lại lệnh dở (`-lai1`) khi an toàn; không an toàn thì dừng, báo.
3. `python "<E>/sau_xuat.py" "<W>" "<mp4_may trong gui.json>"` (timeout 600000) → `<W>/ho-so.json` (duyệt máy, khớp chữ – lời,
   kết quả lệnh, vị trí cảnh, ảnh `to-duyet.jpg` / `khung-dau.jpg` / `khung-chu.jpg`). `dat=false` → đọc `ly_do_khong_dat`.
4. Độ lớn lệch −14 quá 1 LU: `python "<E>/dung_premiere.py" "<W>" --am <lufs đo được>` → `python "<E>/gui_lenh.py" "<W>" --bo am`
   → chạy lại sau_xuat. Xuất lỗi "Không thấy preset": `dung_premiere.py "<W>" --lai-d --preset "<.epr>"` → `gui_lenh.py "<W>" --bo d`.
5. Lỗi lẻ ở b (chữ / keyframe) mà khung-chu.jpg cho thấy thiếu chữ: sửa trong kế hoạch rồi dựng phiên bản mới (mục C), không vá tay.

**A6'. Dựng — trên máy bằng ffmpeg** (`kieu.duong` = may_chu; task "Dựng video trên máy"):
1. Có phụ đề lời thật: `python "<E>/canh_tu.py" "<W>/ke-hoach.json" "<MH>"`
2. `python "<E>/ke_hoach.py" "<W>/ke-hoach.json" "<W>/dtg.json"` → đọc `canh_bao` (dời `tu`/`den` vào khe lặng nếu có gợi ý).
3. `python "<E>/ve_chu.py" "<W>/dtg.json" "<W>/chu"` → phải 0 cảnh báo (sửa chữ / giờ / vị trí rồi chạy lại).
4. Nháp: `python "<E>/dung_may_chu.py" "<W>/dtg.json" "<W>/chu/lop-chu.json" "<W>/nhap.mp4" --nhap` (timeout 600000) →
   `python "<E>/duyet.py" "<W>/nhap.mp4" "<W>/dtg.json" "<W>/duyet" "<W>/chu/lop-chu.json"` → xem `khung-chu.jpg`, sửa nếu sai.
5. Bản đẹp: `mkdir -p "<M>"` → `python "<E>/dung_may_chu.py" "<W>/dtg.json" "<W>/chu/lop-chu.json" "<M>/<ten_file>"`
   (timeout 600000; ~1,5–3 phút) → `python "<E>/sau_xuat.py" "<W>" "<M>/<ten_file>"` (timeout 600000) → `<W>/ho-so.json`.
   Bản máy tự làm: HDR→SDR, chống rung khi `on_dinh`, khử ồn, âm −14 LUFS, phụ đề tô vàng từng từ. Âm nhấn / chữ MOV chỉ có
   ở Premiere (bỏ qua ở đây).

**A7. Duyệt độc lập** (task "Kiểm bản dựng"; BẮT BUỘC): gọi Agent `poly-video:duyet-video` với **model "opus"**, đưa đường dẫn
tuyệt đối: `<W>/ho-so.json`, 3 ảnh trong ho-so `anh`, `<W>/ke-hoach.json`, `<W>/chuan-bi.json` (kiểu + đơn), `<E>/quy-tac/`.
Dặn: không chạy lại ffmpeg / máy nghe, chỉ đọc. Nó trả ĐẠT / NÊN SỬA / CHƯA ĐẠT + danh sách sửa cụ thể.
Sửa hết "phải sửa" và "nên sửa" hợp lý → dựng lại vào phiên bản mới (`don.py phien-ban`, rồi A6 / A6' với `<M>` mới) → agent
duyệt MỚI. Tối đa 2 vòng; còn lỗi vẫn giao, ghi rõ ở `duyet` ("NÊN SỬA: …").

**A8. Giao** (task "Giao video"): Write `<W>/giao.json` =
`{"duyet": "ĐẠT" | "NÊN SỬA: <ngắn>", "caption": "<1 câu, giọng người bán>", "hashtag": "#polystore #… (3–4 cái)",
"ghi_chu": "<kiểu đã dùng, chỗ đã tự quyết, cảnh bỏ; nhắc gắn nhạc trong app + bật 'Thương hiệu của bạn' (+ nhãn AI nếu giọng AI)>"}`
→ `python "<E>/don.py" giao "<W>"` → ghi `<V>/ket-qua.json` {mp4, prproj, kieu_ten, giay, duyet, caption, hashtag, ghi_chu,
khung_dau, to_duyet} + lịch sử kiểu (để video sau không trùng). Câu trả lời cuối chép 2 dòng `MP4=` / `THU_MUC_VIDEO=` nó in.

## B. DUYỆT KẾ HOẠCH XONG → DỰNG TIẾP (lượt không có lệnh skill, anh đã duyệt + "Anh sửa / dặn thêm")
Không phân tích lại. Read `<W>/ke-hoach.json` + `<W>/chuan-bi.json`. Áp lời anh: hook anh sửa → `chu.hook` đúng chữ anh (chỉ
sửa chính tả); đổi cảnh / độ dài → sửa `canh` (+ `phu_de[].canh`, giờ). Rồi A6 hoặc A6' → A7 → A8. Không in CHO_DUYET nữa.

## C. SỬA VIDEO (lượt `/poly-video:dung-video sửa video` + "Anh ghi: …"; cũng dùng cho lượt "Anh đã trả lời câu hỏi")
1. Phiên mới không nhớ gì: Read `<V>/ket-qua.json`, `<W>/ke-hoach.json`, `<W>/chuan-bi.json`, `<W>/don.json` (+ `<W>/ho-so.json`).
2. Chỉ sửa caption / hashtag / ghi chú: sửa `<W>/giao.json` → `python "<E>/don.py" giao "<W>"` (không dựng lại). Xong.
3. Sửa hình / chữ / độ dài: `python "<E>/don.py" phien-ban "<W>"` → `<M>` mới (v<n+1>, đã ghi vào `ra` của kế hoạch). Sửa
   ke-hoach.json đúng chỗ anh nói:
   - đổi cảnh: sửa `canh[i].tu/den/file` (clip khác thì thêm vào `nguon`); câu phụ đề của cảnh đó: sửa `chu`, giữ `canh`
     (canh_tu tự canh giờ lại); cảnh mới không có câu thì bỏ câu đó.
   - sửa chữ / hook / nhãn / giá: `chu.*` (giá chỉ theo anh); cắt bớt: bỏ / rút `canh` + câu phụ đề tương ứng.
   - đổi kiểu: sửa `kieu.<mục>` (anh chọn = ghim). Đổi đường dựng: sửa `kieu.duong`.
   Rồi A6 / A6' với `<M>` mới → A7 (đổi chữ / giá theo đúng lựa chọn của anh thì khỏi gọi lại agent duyệt) → A8.
4. Anh chê / thích điều dùng được cho video sau (tên máy viết sao, kiểu chữ, độ dài…): Edit thêm 1 dòng cuối mục
   **"## Anh chốt"** của `<E>/quy-tac/gu-kenh-poly-store.md`: `- <ngày>: <luật ngắn>`.

## D. CHẠY TIẾP SAU LỖI (lượt "bị dừng hoặc lỗi giữa chừng")
1. Xem task list + file đã có: `chuan-bi.json`, `phan-tich.json`, `ke-hoach.json`, `gui.json`, `gui-ket-qua.json`, `ho-so.json`,
   `<V>/ket-qua.json`. Bước có kết quả rồi thì không làm lại (phan_tich dở: chạy lại với `--them`).
2. Premiere: chạy lại `python "<E>/gui_lenh.py" "<W>"` — lệnh đã xong được bỏ qua, lệnh đang chạy được chờ tiếp, lệnh mất kết
   quả được chạy lại an toàn (`-lai1`). Nó báo "không tự chạy lại" / project lạ → dựng phiên bản mới (C3 không đổi kế hoạch).
3. Gửi lại lệnh đã chạy (vd. sửa xong lỗi b, xuất lại): `python "<E>/gui_lenh.py" "<W>" --chi c,d --hau-to r2` (đuôi id sau tên
   gốc; kết quả `-r2` được sau_xuat dùng thay bản gốc). Lượt a lỗi giữa chừng mà Premiere không văng: KHÔNG gửi lại a (đặt trùng
   cảnh) — dựng phiên bản mới. Không chắc → phiên bản mới.
4. Muốn xem timeline thật trước khi gửi lại: Write `<W>/script/xem-timeline.json` =
   `{"id": "<goc_id trong gui.json>-xem1", "project": "<prproj trong gui.json>", "song_song": true, "buoc": [{"lenh": "xem_timeline", "sequence": "<ten>-doc"}]}`
   → `python "<E>/gui_lenh.py" --tep "<W>/script/xem-timeline.json" --ra "<W>/script/xem-tom-tat.json"` → Read file `ket_qua`
   nó in (id mới cho mỗi lần xem: -xem2, -xem3…). Chỉ lệnh đọc (`xem_timeline`, `xem_sequence`, `danh_sach`) — không tự soạn lệnh sửa.
5. Premiere chưa mở: gui_lenh tự mở Premiere (app đặt env `POLY_GUI_TU_MO_PREMIERE=1`, anh chốt 29/10 "tự mở Premiere khi
   cần"), mở kèm project gần nhất để bảng Poly Bridge tự lên, chờ nhịp tim ≤ 5 phút — bạn KHÔNG tự mở bằng cách khác. Premiere
   văng giữa lúc gửi lệnh: gui_lenh tự mở lại (tắt bằng `POLY_GUI_KHONG_MO_LAI=1`). Vẫn mã 2 (bảng không lên, đang tạm dừng,
   Premiere treo) → `LOI=Mở Premiere + bảng Poly Bridge rồi bấm Chạy tiếp`. Lệnh gui_lenh lần đầu có thể chạy lâu hơn vì chờ mở.

## E. Kinh nghiệm Premiere 26.5.2 + Poly Bridge 1.5.x (đã đo)
- Dựng + xuất ≈ 50s khi không văng; video 80s ≈ 3–4 phút từ lúc có kế hoạch. Lượt b chia ≤ 70 bước (140 bước văng ~1/3).
- Mọi file lệnh kết bằng `luu_project`; mỗi bản dựng 1 thư mục mới; `tao_project` vào project đã lưu bị từ chối.
- Kiểu mở đầu `dong_bang` / `hoi_truoc` chỉ dựng ffmpeg (chon_kieu --duong premiere không bốc). Âm nhấn, chữ MOV chỉ Premiere.
- Chữ là PNG / MOV alpha (không dùng .srt, Lumetri); khung duyệt lấy từ mp4 (khung-chu.jpg). Sticker Poly cần ảnh trong
  `<E>/sticker/` (chưa cài trên máy này → không dùng `chu.sticker`).
- Âm từng clip ≈ −15,6 LUFS (trần đỉnh); muốn đúng −14 dùng vòng `--am`. `--limiter` chưa kiểm trên máy thật: không dùng.
