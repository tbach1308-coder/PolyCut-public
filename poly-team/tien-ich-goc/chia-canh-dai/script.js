// Chia đều mọi cảnh dài hơn toi_da giây
const toiDa = Math.max(1, ed.vao.toi_da || 4);
let dem = 0;
for (const c of [...ed.canh]) {
  const n = Math.ceil(ed.dai(c) / toiDa - 1e-6);
  if (n < 2) continue;
  const phan = ed.dai(c) / n;
  let x = c;
  for (let i = 1; i < n; i++) { x = ed.chia(x, phan); dem++; }
}
ed.bao(dem ? `Đã chia thêm ${dem} chỗ, mỗi đoạn ≤ ${toiDa}s` : `Không có cảnh nào dài hơn ${toiDa}s`);
