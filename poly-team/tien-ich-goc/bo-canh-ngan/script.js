// Xoá cảnh ngắn hơn X giây
const duoi = Math.max(0.3, ed.vao.duoi || 0.6);
let dem = 0;
for (const c of [...ed.canh]) {
  if (ed.canh.length > 1 && ed.dai(c) < duoi) { ed.xoa(c); dem++; }
}
ed.bao(dem ? 'Đã xoá ' + dem + ' cảnh ngắn hơn ' + duoi + 's' : 'Không có cảnh nào ngắn hơn ' + duoi + 's');
