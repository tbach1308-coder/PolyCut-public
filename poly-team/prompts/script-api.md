Script tiện ích chạy trong trình Sửa tay, viết bằng JavaScript thường (không import, không async/await, không mạng). Script chạy trên BẢN SAO của video. Chạy xong thì app kiểm lại rồi áp thành 1 bước Ctrl+Z. Chạy quá 4 giây là app dừng.

Biến `ed` (mọi giờ tính bằng giây):

Đọc
- `ed.canh`: mảng cảnh theo thứ tự trên video. Mỗi cảnh có `c.tu` / `c.den` (giây trong CLIP GỐC), `c.file`, `c.mo_ta` (ghi chú cảnh, có thể trống). Hiệu ứng riêng cảnh (không ghi = theo kiểu cả video): `c.chuyen` = chuyển cảnh VÀO cảnh này (`cat_cung`, `hoa_tan_nhanh`, `truot_ngang`, `zoom_xuyen`, `mo_tron`; máy chủ thêm `nhay_trang`, `truot_doc`, `lau_mem`, `mo_chuyen_dong`, `vo_diem`), `c.dong` = chuyển động khung (`dung_yen`, `zoom_vao`, `zoom_ra`, `phong_sat`, `lia_phai`, `lia_trai`), `c.hieu_ung` = hiệu ứng hình (`lay_net_nhe`, `khu_nhieu_nhe`, `mau_san_pham`, `trang_sach`, `mo_chuyen_dong`; đầu cảnh: `zoom_nay`, `lay_net_vao`, `vet_sang_quet`). Chuyển cảnh riêng thêm (3/11): `de_luot`, `truot_ngang_muot`, `truot_doc_muot`, `keo_len`, `de_ngang` (đẹp nhưng dựng chậm, mỗi video 1–3 chỗ), `lau_mem_doc`, `mo_cua`, `hoa_tan_sang`, `lau_cheo`, `nhay_den`. Bỏ: `delete c.chuyen`.
- `ed.canhSo(n)`: cảnh thứ n, đếm từ 1 như trên màn hình.
- `ed.dai(c)`: độ dài cảnh. `ed.clip(c)`: tên clip. `ed.clipDai(c)`: độ dài clip gốc.
- `ed.batDau(c)`: cảnh bắt đầu ở giây nào trên video. Số này gần đúng, vì chưa trừ phần chuyển cảnh chồng lên nhau.
- `ed.tong()`: tổng độ dài các cảnh (chưa trừ chuyển cảnh chồng). `ed.thuc()`: độ dài video THẬT lúc xuất (đã trừ chuyển cảnh, cộng mở đầu); dùng số này khi cần video dài đúng X giây.
- `ed.vach`: chỗ vạch đỏ (giây trên video). `ed.canhVach`: cảnh đang dưới vạch đỏ. `ed.chon`: cảnh đang chọn (null nếu chưa chọn).
- `ed.vao`: giá trị các ô hỏi của tiện ích. Vd `ed.vao.gia`. Ô kiểu "so" đã là số.
- `ed.clipCoSan`: tên các clip dùng được cho `ed.themCanh`.
- `ed.nhanDs`, `ed.phuDe`: mảng nhãn / câu phụ đề, mỗi cái có `.chu`. Sửa thẳng `.chu` được.
- `ed.kieuDs`: các giá trị kiểu được phép, dạng { trục: [giá trị…] }.
- `ed.plan`: toàn bộ kế hoạch, dành cho script nâng cao. Hạn chế sửa thẳng.

Cảnh (mọi cảnh phải dài ≥ 0,3 giây)
- `ed.chia(c, sau)`: chia cảnh tại `sau` giây tính từ đầu cảnh. Trả về nửa sau (cảnh mới).
- `ed.catDau(c, giay)` / `ed.catCuoi(c, giay)`: bỏ bớt `giay` giây ở đầu / cuối cảnh.
- `ed.doan(c, tu, den)`: đặt lại đoạn lấy trong clip gốc.
- `ed.xoa(c)`: xoá cảnh (video luôn còn ít nhất 1 cảnh).
- `ed.nhanDoi(c)`: chép cảnh, bản chép nằm ngay sau. Trả về bản chép.
- `ed.doiCho(c, viTri)`: dời cảnh tới vị trí `viTri`, đếm từ 1.
- `ed.themCanh(clip, {tu, den, sau})`: thêm cảnh từ clip có sẵn. `sau` là một cảnh hoặc "dau"; bỏ trống thì thêm vào cuối. Trả về cảnh mới.
- `ed.thayClip(c, clip, tu)`: đổi cảnh sang clip khác, giữ độ dài.

Chữ (cách đặt chỗ `vt`)
- `{canh: c, sau: 0.3, dai: 2.5}`: dính vào cảnh, cắt hay dời cảnh thì chữ đi theo.
- `{luc: 5.2, dai: 2.5}`: đặt theo giây trên video.
- Bỏ trống `vt` thì đặt ở vạch đỏ.

- `ed.hook(dong1, dong2)`: hook 2 dòng (dòng 1 ≤ 20 ký tự, dòng 2 ≤ 22). `ed.hook()` = bỏ hook.
- `ed.nhan(chu, vt)`: thêm nhãn chữ to (≤ 18 ký tự). Trả về nhãn. `ed.xoaNhan(n)` để xoá.
- `ed.theGia(gia, phu, vt)`: đặt / thay thẻ giá. `ed.boTheGia()` để bỏ. Chỉ ghi giá thật.
- `ed.themPhuDe(chu, vt)`: thêm câu phụ đề. `ed.xoaPhuDe(x)` để xoá.
- `ed.ket(dong1, dong2)`: thẻ kết tự viết. `ed.ket("mac_dinh")` = câu mặc định, `ed.ket(null)` = không có thẻ kết. `ed.ketGiay(s)`: thẻ kết hiện bao lâu.
- `ed.tieuDe(chu)`: tiêu đề ghim trên cùng (`""` = bỏ). `ed.brand(true|false)`: chữ POLY STORE.
- `ed.kieu(truc, giaTri)`: đổi kiểu, vd `ed.kieu("chuyen_canh", "cat_cung")`. Giá trị phải có trong `ed.kieuDs`.

Khác
- `ed.bao("…")`: ghi 1 dòng báo cho anh xem sau khi chạy.
- `throw new Error("…")`: dừng script, không đổi gì.

Ví dụ: chia mọi cảnh dài hơn 4 giây
```js
for (const c of [...ed.canh]) {
  let x = c;
  while (ed.dai(x) > 4) x = ed.chia(x, 4);
}
```
Lặp qua `[...ed.canh]` (bản chép của mảng), vì chia, xoá hay thêm cảnh sẽ làm đổi chính mảng `ed.canh`.
