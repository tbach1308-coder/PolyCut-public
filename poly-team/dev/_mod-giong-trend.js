/* ============================== GIỌNG AI TREND (r39, 11/11 11:00 anh: "thêm giọng đọc AI trend"; 11:30 duyệt giữ cả 9 kiểu) ==============================
   Thay ô chọn giọng (Giọng AI gõ lời trong Thư viện + hộp "Đọc lại bằng giọng AI") bằng danh sách chia nhóm:
     Trend (9 kiểu = giọng + tốc độ + phong cách, có nhãn) · Phổ biến (8 giọng cũ, GIONG_PHO_BIEN) · Tất cả 25 giọng (gập, "Xem thêm").
   Mỗi mục 1 nút ▶ nghe mẫu: mp3 gói sẵn trong app (poly-team/giong-mau/, /api/sua-tay/giong-mau) — giọng chưa có mẫu (Microsoft)
   thì máy tạo như nút "Nghe thử". Chọn kiểu trend = đặt cùng lúc giọng + tốc độ + phong cách (giong.py --phong, phong_giong.py);
   chọn giọng thường = bỏ kiểu / phong cách (đọc như cũ). Đổi tốc độ sau đó vẫn giữ kiểu.
   Trạng thái: Giọng AI gõ lời = GA.chon / GA.toc / GA.phong / GA.kieu (_giong-ai.js); Đọc lại = GD.hop.giong / toc / phong / kieu
   (_mod-giong-de.js, nhớ lần trước trong localStorage). Kế hoạch chỉ THÊM khoá phong / kieu_trend vào plan.giong và câu plan.giong_de.
   Mô-đun bọc veGA / gdVe (giữ chỗ cuộn, gắn sự kiện) và dung (tắt tiếng mẫu đang phát). */
const GT = {mo: {}, cuon: {}, au: null, nghe: '', cho: ''};
const gtTrend = () => (GA.ds && GA.ds.vieneu && Array.isArray(GA.ds.trend)) ? GA.ds.trend : [];
const gtTocTen = v => { const x = GA.ds && (GA.ds.toc || []).find(t => t.v === v); return x ? x.ten : v; };
const gtPhongTen = id => { const x = GA.ds && (GA.ds.phong || []).find(p => p.id === id); return x ? x.ten : ''; };
function gtSt(ma) {
  if (ma === 'ga') return {g: GA.chon, toc: GA.toc, phong: GA.phong || null, kieu: GA.kieu || null};
  const H = GD.hop; return H ? {g: H.giong, toc: H.toc, phong: H.phong || null, kieu: H.kieu || null} : null;
}
function gtKieu(st) { return st && st.kieu ? gtTrend().find(k => k.id === st.kieu) || null : null; }
function gtTomTat(st) {   // "Loa thông báo · Mai Anh" / "Adam"
  const k = gtKieu(st), g = GA.ds.ds.find(x => x.id === st.g);
  if (k) return k.ten + ' · ' + (g ? g.ten : k.ten_giong);
  return (g ? g.ten : st.g) + (st.phong ? ' · ' + gtPhongTen(st.phong) : '');
}
function gtChip(ds) { return (ds || []).slice(0, 3).map(t => `<span class="gt-chip">${esc(t)}</span>`).join(''); }
function gtNut(key, ten) {
  const dang = GT.nghe === key && GT.au && !GT.au.paused, cho = GT.cho === key;
  return `<button type="button" class="gt-nghe${dang ? ' dang' : ''}${cho ? ' cho' : ''}" data-gt-nghe="${esc(key)}" aria-label="${dang ? 'Dừng' : 'Nghe mẫu'} ${esc(ten)}" data-tip="${dang ? 'Dừng' : 'Nghe mẫu'}">${icon(dang ? 'pause' : 'play')}</button>`;
}
function gtHangGiong(x, st, kOn) {
  const on = !kOn && st.g === x.id;
  const phu = [x.gioi, x.mien].filter(Boolean).join(' · ');
  const tip = x.nguon === 'microsoft' ? 'Giọng Microsoft: cần mạng khi tạo giọng' : (x.cach ? 'Giọng ' + x.cach + ', chạy trên máy' : '');
  return `<div class="gt-r${on ? ' on' : ''}">${gtNut('g:' + x.id, x.ten)}<button type="button" class="gt-chon" role="option" aria-selected="${on}" data-gt-g="${esc(x.id)}"${tip ? ` data-tip="${esc(tip)}"` : ''}>
    <span class="gt-ten">${esc(x.ten)}</span><span class="gt-phu">${esc(phu)}</span>${gtChip(x.nhan || (x.nguon === 'microsoft' ? ['cần mạng'] : []))}</button></div>`;
}
function gtVe(ma) {   // HTML hàng "Giọng" + danh sách (gọi trong veGA / gdVe)
  const st = gtSt(ma), d = GA.ds; if (!st || !d) return '';
  const tr = gtTrend(), kOn = gtKieu(st), ds = d.ds || [];
  const pb = GIONG_PHO_BIEN.map(id => ds.find(x => x.id === id)).filter(Boolean);
  const tat = d.vieneu ? ds.filter(x => x.nguon === 'vieneu') : [];
  if (GT.mo[ma] == null && !kOn && !GIONG_PHO_BIEN.includes(st.g) && tat.some(x => x.id === st.g)) GT.mo[ma] = true;   // giọng đang dùng nằm trong Tất cả
  const mo = !!GT.mo[ma];
  const thu = ma === 'ga' ? 'data-ga="thu"' : 'data-gd="thu"';
  return `<div class="gt" data-gt-ma="${ma}">
    <div class="gt-dau"><span class="lbl">Giọng</span><span class="gt-dang" title="${esc(gtTomTat(st))}">${esc(gtTomTat(st))}</span>
      <button type="button" class="btn small gt-thu" ${thu} data-tip="Nghe 1 câu mẫu bằng giọng + tốc độ${st.phong ? ' + phong cách' : ''} đang chọn">${icon('play')}Nghe thử</button></div>
    <div class="gt-ds" role="listbox" aria-label="Chọn giọng đọc">
      ${tr.length ? `<div class="gt-nhom">Trend${tvI('Kiểu giọng đang chạy trên TikTok: chọn 1 kiểu là đặt luôn giọng, tốc độ và phong cách xử lý (trầm, loa, robot…). Chỉ học kiểu giọng, không nhái giọng người thật.')}</div>
      ${tr.map(k => { const on = kOn && kOn.id === k.id;
        const tip = (k.hop ? k.hop + '. ' : '') + 'Giọng ' + k.ten_giong + ', tốc độ ' + gtTocTen(k.toc_do) + ', phong cách ' + gtPhongTen(k.phong) + '.';
        return `<div class="gt-r gt-tr${on ? ' on' : ''}">${gtNut('k:' + k.id, k.ten)}<button type="button" class="gt-chon" role="option" aria-selected="${!!on}" data-gt-k="${esc(k.id)}" data-tip="${esc(tip)}">
          <span class="gt-ten">${esc(k.ten)}</span><span class="gt-phu">${esc(k.ten_giong + ' · ' + gtTocTen(k.toc_do))}</span>${gtChip(k.nhan)}</button></div>`; }).join('')}` : ''}
      <div class="gt-nhom">Phổ biến</div>
      ${pb.map(x => gtHangGiong(x, st, kOn)).join('')}
      ${tat.length ? (mo ? `<div class="gt-nhom">Tất cả ${tat.length} giọng chạy trên máy</div>${tat.map(x => gtHangGiong(x, st, kOn)).join('')}
        <button type="button" class="gt-them" data-gt-mo="0">Thu gọn</button>`
        : `<button type="button" class="gt-them" data-gt-mo="1">Xem thêm ${tat.length} giọng</button>`) : ''}
    </div></div>`;
}
function gtDat(ma, v) {   // chọn 1 mục
  if (ma === 'ga') {
    const ta = GA.el && $('.ga-loi', GA.el); if (ta) GA.loi = ta.value;
    GA.chon = v.g; if (v.toc) GA.toc = v.toc; GA.phong = v.phong || null; GA.kieu = v.kieu || null;
    return veGA();
  }
  const H = GD.hop; if (!H) return;
  H.giong = v.g; if (v.toc) H.toc = v.toc; H.phong = v.phong || null; H.kieu = v.kieu || null; H.kq = null;
  gdGhi('gd-giong', H.giong); gdGhi('gd-toc', H.toc); gdGhi('gd-phong', H.phong || ''); gdGhi('gd-kieu', H.kieu || '');
  gdVe();
}
function gtDungNghe() {
  if (GT.au) { try { GT.au.pause(); } catch (e) {} }
  GT.au = null; GT.nghe = ''; gtVeNut();
}
function gtVeNut() {   // cập nhật nút ▶ / ■ đang hiện (không vẽ lại cả bảng)
  $$('.gt-nghe').forEach(b => { const key = b.dataset.gtNghe, dang = GT.nghe === key && GT.au && !GT.au.paused;
    b.classList.toggle('dang', !!dang); b.classList.toggle('cho', GT.cho === key); b.innerHTML = icon(dang ? 'pause' : 'play');
    b.dataset.tip = dang ? 'Dừng' : 'Nghe mẫu'; });
}
async function gtNghe(ma, key) {
  if (GT.nghe === key && GT.au && !GT.au.paused) return gtDungNghe();
  dung(); gtDungNghe();
  let url = '', body = null;
  if (key.startsWith('k:')) {
    const k = gtTrend().find(x => x.id === key.slice(2)); if (!k) return;
    url = k.mau || ''; body = {giong: k.giong, toc_do: k.toc_do, phong: k.phong};
  } else {
    const x = (GA.ds.ds || []).find(y => y.id === key.slice(2)); if (!x) return;
    url = x.mau || ''; body = {giong: x.id, toc_do: '+10%'};
  }
  if (!url) {   // chưa có mẫu gói sẵn (giọng Microsoft): máy tạo như nút Nghe thử
    GT.cho = key; gtVeNut();
    try { url = (await api('/api/giong-thu', body)).url; } catch (e) { GT.cho = ''; gtVeNut(); return toast(e.message, true); }
    GT.cho = ''; if (GT.au) return gtVeNut();   // bấm mẫu khác trong lúc chờ
  }
  const a = new Audio(url); GT.au = a; GT.nghe = key;
  a.onended = a.onerror = () => { if (GT.au === a) { GT.au = null; GT.nghe = ''; gtVeNut(); } };
  a.play().then(gtVeNut).catch(() => { if (GT.au === a) { GT.au = null; GT.nghe = ''; } gtVeNut(); });
  gtVeNut();
}
function gtBam(e) {
  const box = e.target.closest('.gt'); if (!box) return;
  const ma = box.dataset.gtMa, st = gtSt(ma); if (!st) return;
  const n = e.target.closest('[data-gt-nghe]'); if (n) { e.stopPropagation(); return gtNghe(ma, n.dataset.gtNghe); }
  const m = e.target.closest('[data-gt-mo]'); if (m) { GT.mo[ma] = m.dataset.gtMo === '1'; GT.cuon[ma] = $('.gt-ds', box).scrollTop; return gtDat(ma, st); }
  const k = e.target.closest('[data-gt-k]');
  if (k) { const x = gtTrend().find(y => y.id === k.dataset.gtK); if (x) gtDat(ma, {g: x.giong, toc: x.toc_do, phong: x.phong, kieu: x.id}); return; }
  const g = e.target.closest('[data-gt-g]'); if (g) gtDat(ma, {g: g.dataset.gtG, toc: null, phong: null, kieu: null});
}
function gtSau(el, ma) {   // sau khi vẽ: giữ chỗ cuộn, gắn sự kiện 1 lần
  if (!el || !el.isConnected) return;
  const ds = $('.gt-ds', el); if (!ds) return;
  if (!el.dataset.gtGan) { el.dataset.gtGan = '1'; el.addEventListener('click', gtBam, true); }
  if (GT.cuon[ma] != null) ds.scrollTop = GT.cuon[ma];   // mở lần đầu: từ đầu danh sách (giọng đang chọn ghi ở dòng tóm tắt trên)
  ds.addEventListener('scroll', () => { GT.cuon[ma] = ds.scrollTop; }, {passive: true});
}
{
  const gVe = veGA; veGA = function () { const r = gVe.apply(this, arguments); try { gtSau(GA.el, 'ga'); } catch (e) { console.error(e); } return r; };
  const gGd = gdVe; gdVe = function () { const r = gGd.apply(this, arguments); try { if (GD.hop) gtSau(GD.hop.el, 'gd'); } catch (e) { console.error(e); } return r; };
  const gMo = moDocLai; moDocLai = async function () { GT.cuon.gd = null; GT.mo.gd = null; return gMo.apply(this, arguments); };
  const gDung = dung; dung = function () { const r = gDung.apply(this, arguments); try { if (GT.au) gtDungNghe(); } catch (e) {} return r; };
}
