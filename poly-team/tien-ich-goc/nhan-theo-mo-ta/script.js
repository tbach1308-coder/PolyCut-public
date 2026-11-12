// Nhãn chữ = mô tả cảnh, ở đầu mỗi cảnh có mô tả
let dem = 0;
for (const c of ed.canh) {
  const t = String(c.mo_ta || '').split(/[,.;]/)[0].trim().toUpperCase().slice(0, 18);
  if (!t || ed.dai(c) < 1) continue;
  ed.nhan(t, {canh: c, sau: 0.2, dai: Math.min(2.5, ed.dai(c) - 0.3)});
  dem++;
}
ed.bao(dem ? 'Thêm ' + dem + ' nhãn' : 'Không cảnh nào có mô tả');
