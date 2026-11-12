Bạn soát lại PHỤ ĐỀ TỰ ĐỘNG cho 1 video TikTok của Poly Store (tiệm bán / sửa iPhone, iPad, MacBook ở Việt Nam).
Phụ đề do máy nghe tiếng Việt trên máy tạo ra từ lời người nói trong clip, nên hay nghe sai: tên máy (iPad, MacBook,
Magic Keyboard…), tên game, số, giá, từ tiếng Anh. Việc của bạn: SỬA CHỮ NGHE SAI theo ngữ cảnh, không làm gì khác.

## Luật (bắt buộc)
1. Chỉ sửa chữ nghe sai / viết sai. KHÔNG đổi ý, KHÔNG viết lại câu cho hay hơn, KHÔNG thêm câu, KHÔNG thêm ý người nói
   không nói, KHÔNG bỏ từ đệm người nói thật sự nói ("ha", "nha", "này", "thì", "là"…). Câu nào đã đúng thì bỏ qua.
2. Giữ đúng thứ tự từ. Mỗi câu chỉ sửa trong chính câu đó, không dời chữ sang câu khác, không gộp / tách câu.
3. Chữ vô nghĩa (máy nghe ra từ lạ như "combaldro", "ibe", "abardro") thì đoán theo cách phát âm + ngữ cảnh video
   (tên video, chữ trên video, từ của tiệm bên dưới). Không chắc thì GIỮ NGUYÊN, đừng bịa.
4. Viết số theo gu kênh: số bằng chữ số ("12.9 inch", "2020", "120Hz", "64GB", "98%", "M1", "iPhone 13");
   giá viết gọn kiểu tiệm: "mười ba triệu chín" -> "13TR9", "tám triệu rưỡi" -> "8TR5", "năm trăm nghìn" -> "500K".
   Chữ số lẻ dùng như mạo từ thì giữ chữ ("một chiếc", "bốn loa" giữ nguyên).
5. Tên máy / hãng / game viết đúng: iPad Pro, iPad Air, MacBook Air, iPhone 15 Pro Max, Apple Pencil, Magic Keyboard,
   Liên Quân, Tốc Chiến, PUBG… Không cần in hoa cả câu (máy dựng tự in hoa khi xuất).
6. Không tự nghĩ thông số / giá không có trong lời nói.

## Video
{{VIDEO}}

## Từ của tiệm (tên máy, từ hay nói)
{{TU_DIEN}}

## Các câu phụ đề (theo thứ tự thời gian; "k" là mã câu)
{{CAU}}

## Trả lời
CHỈ trả 1 khối JSON, không viết gì khác:
```json
{"sua": [{"k": "<mã câu>", "chu": "<cả câu sau khi sửa>", "ly_do": "<vài chữ: sửa gì>"}],
 "ghi_chu": "<1 câu tiếng Việt ngắn cho anh chủ tiệm, vd: Sửa 4 câu: tên máy iPad Pro, số 12.9 inch, game PUBG>"}
```
- Chỉ liệt kê câu CÓ sửa. Không có gì sửa thì "sua": [].
- "chu" là cả câu (không phải mỗi chữ sửa), viết thường như câu gốc, chỉ khác ở chữ sửa.
