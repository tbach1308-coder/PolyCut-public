// Bớt đuôi cảnh dài nhất cho tới khi video còn X giây
const muon = Math.max(5, ed.vao.giay || 45);
const truoc = ed.thuc();   // độ dài THẬT (đã trừ chuyển cảnh chồng nhau)
let thua = truoc - muon;
if (thua <= 0) { ed.bao('Video đang ' + truoc.toFixed(1) + 's, đã ngắn hơn ' + muon + 's'); }
else {
  while (thua > 0.05) {
    const ds = ed.canh.filter(c => ed.dai(c) > 1.5).sort((a, b) => ed.dai(b) - ed.dai(a));
    if (!ds.length) break;
    const c = ds[0];
    const ke = ds[1] ? ed.dai(ds[1]) : 1.5;
    const bot = Math.min(thua, Math.max(0.1, ed.dai(c) - Math.max(ke, 1.5)), ed.dai(c) - 1.5);
    if (bot <= 0) break;
    ed.catCuoi(c, bot); thua -= bot;
  }
  ed.bao('Từ ' + truoc.toFixed(1) + 's còn khoảng ' + ed.thuc().toFixed(1) + 's' + (thua > 0.05 ? ' (không bớt thêm được, các cảnh đã ≤ 1,5s)' : ''));
}
