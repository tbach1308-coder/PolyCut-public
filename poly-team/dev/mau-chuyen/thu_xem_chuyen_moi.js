// Kiểm xem trước chuyển cảnh mới (_mod-chuyen-moi.js): (1) đường cong JS == Python (chuyen_moi.gia_tri) trên mọi khoá của 15 kiểu, (2) CSS không có NaN.
// Dùng: node thu_xem_chuyen_moi.js <thư mục chuyen-canh>   (in JSON giá trị để so với Python: xem thu_xem_chuyen_moi.py)
const fs = require('fs'), path = require('path');
// cssChuyen nằm trong dev/_mod-chuyen-moi.js giữa 2 dấu /*CSS_CHUYEN_BAT*/ … /*CSS_CHUYEN_HET*/ (không cần trình duyệt)
const src = fs.readFileSync(path.join(__dirname, '..', '_mod-chuyen-moi.js'), 'utf8');
const doan = src.slice(src.indexOf('/*CSS_CHUYEN_BAT*/'), src.indexOf('/*CSS_CHUYEN_HET*/'));
const {cssChuyen, gt} = new Function(doan + '\nreturn CCM;')();
const dir = process.argv[2];
const out = {}, loi = [];
for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.json')).sort()) {
  const s = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')), id = s.id;
  const keys = [];
  for (const side of ['A', 'B']) for (const [k, tr] of Object.entries(s[side] || {})) if (typeof tr !== 'string' && k !== 'bong_lech') keys.push([side + '.' + k, tr]);
  (s.lop || []).forEach((l, i) => keys.push(['lop' + i + '.manh', l.manh]));
  if (s.nguong) keys.push(['nguong', s.nguong]);
  out[id] = {};
  for (const [k, tr] of keys) out[id][k] = Array.from({length: 41}, (_, i) => Math.round(gt(tr, i / 40, 0) * 1e6) / 1e6);
  for (let i = 0; i <= 20; i++) {
    const r = cssChuyen(s, i / 20, {sw: 400});
    const t = JSON.stringify(r);
    if (/NaN|Infinity|undefined/.test(t)) loi.push(id + ' p=' + i / 20 + ' ' + t);
  }
}
if (loi.length) { console.error('LỖI CSS:\n' + loi.join('\n')); process.exit(1); }
console.log(JSON.stringify(out));
