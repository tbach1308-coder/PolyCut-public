// Thẻ giá ở cảnh cuối (trước thẻ kết, để thẻ kết không che)
const gia = String(ed.vao.gia || '').trim();
if (!gia) throw new Error('Chưa nhập giá');
const P = ed.plan, chu = P.chu || {};
const coKet = chu.ket !== null && (P.kieu || {}).ket !== 'khong';
const ketDai = coKet ? (+P.ket_giay || 3.6) : 0;
const T = ed.thuc(), k = ed.tong() > 0 ? T / ed.tong() : 1;   // giờ trên video thật ≈ giờ cộng dồn × k
const het = T - ketDai;                                           // thẻ kết bắt đầu lúc này
let c = null, sau = 0, dai = 0;
for (let i = ed.canh.length - 1; i >= 0; i--) {
  const x = ed.canh[i], a = ed.batDau(x) * k, b = a + ed.dai(x) * k;
  const con = Math.min(b, het) - a;                               // phần cảnh còn thấy trước thẻ kết
  if (con >= 1.5) { c = x; sau = Math.min(0.5, con / 4); dai = Math.max(1, Math.min(3, con - sau - 0.1)); break; }
}
if (!c) { c = ed.canh[ed.canh.length - 1]; sau = Math.min(0.5, ed.dai(c) / 4); dai = Math.max(1, Math.min(3, ed.dai(c) - sau)); ed.bao('Video ngắn quá: thẻ giá có thể bị thẻ kết che, nên cho thẻ kết hiện ngắn lại (tab Chữ)'); }
ed.theGia(gia, ed.vao.phu || '', {canh: c, sau: sau / k, dai: dai / k});
const so = ed.canh.indexOf(c) + 1;
ed.bao('Thẻ giá ' + gia + ' ở cảnh ' + so + (so < ed.canh.length ? ' (cảnh cuối nằm dưới thẻ kết nên đặt sớm hơn)' : '') + ', hiện khoảng ' + dai.toFixed(1) + 's');
