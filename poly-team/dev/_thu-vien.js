/* ============================== THƯ VIỆN (3/11 tối) ==============================
   Màn Sửa tay kiểu trình dựng 4 khu (anh: "clone giao diện này"): Thư viện | khung xem | bảng thuộc tính, timeline full ngang.
   Chỉ học cách sắp xếp khu, màu / icon / chữ là của POLY (xanh lục bảo --brand, vàng --gold, icon nét dev/_icon.js).
   Tab: Clip (bấm clip = thêm cảnh sau cảnh đang chọn) · Chữ (mẫu nhãn / thẻ giá / phụ đề / hook / thẻ kết + kiểu chữ cả video)
        · Chuyển cảnh (vào cảnh đang chọn; rê chuột vào ô thì chạy thử bằng CSS) · Hiệu ứng (chuyển động cảnh này + cả video)
        · Tiện ích (chạy như menu ⚡).
   veBen() gọi veTV(): so khoá (cảnh chọn + phần kế hoạch liên quan) để khỏi vẽ thừa; không vẽ lúc đang kéo (S.keo).
   Danh sách clip nhớ theo thư mục (S.tv.ds) để khỏi gọi /api/clip lại. Thu gọn: localStorage st-tv-thu (lớp .tv-thu trên #edit);
   bề ngang + tự co / tự thu thành hàng icon khi chật: hopCot() ở file chính (cùng chỗ đường chia #keoDoc / #keoNgang). */
const TV_TAB = [['clip', 'clip', 'Clip', 'Thêm cảnh từ thư mục clip'], ['chu', 'nhan', 'Chữ', 'Nhãn, thẻ giá, phụ đề, kiểu chữ'],
  ['chuyen', 'chuyenC', 'Chuyển cảnh', 'Kiểu nối vào cảnh đang chọn'], ['hieu', 'hieuUng', 'Hiệu ứng', 'Chuyển động, hiệu ứng hình, chớp, lớp phủ, màu'],
  ['giong', 'mic', 'Giọng AI', 'Lời đọc bằng giọng AI, như Text to speech'], ['nhac', 'nhac', 'Nhạc', 'Nhạc nền của tiệm hoặc nhạc miễn phí, cân tiếng nhạc / giọng / tiếng clip'],
  ['ti', 'ti', 'Tiện ích', 'Script chạy trên video này']];
const TV_THEM = {};   // tab thêm từ dev/_mod-*.js: {ve() -> html, sau(), khoa() -> chuỗi} (r20: Âm thanh, dev/_mod-thu-vien-them.js)
S.tv = {tab: 'clip', thu: false, noi: false, tm: '', ds: {}, khoa: '', cuon: {}, them: '', tiTai: false, tiDang: false, daVe: ''};
try { const t = localStorage.getItem('st-tv-tab'); if (TV_TAB.some(x => x[0] === t)) S.tv.tab = t; S.tv.thu = localStorage.getItem('st-tv-thu') === '1'; } catch (e) {}
const tvLuu = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} };
const chuanP = p => String(p || '').replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
const thuMucCua = p => String(p || '').replace(/[\\/][^\\/]*$/, '');
const tvRay = () => S.tv.thu || $('#edit').classList.contains('tv-tu-thu');

/* ---------- khung: tab, thu gọn, nổi (khi tự thu vì chật) ---------- */
function veTvTabs() {
  const ray = tvRay();
  $('#libTabs').innerHTML = (ray ? `<button type="button" class="tvt tv-mo" data-tv-mo aria-label="Mở thư viện" data-tip="Mở thư viện">${icon('moRong')}</button>` : '')
    + TV_TAB.map(([k, ic, ten, goi]) => `<button type="button" class="tvt${k === S.tv.tab ? ' on' : ''}" role="tab" aria-selected="${k === S.tv.tab}" data-tv="${k}" aria-label="${ten}" data-tip="${ten}: ${goi}">${icon(ic)}<span>${ten}</span></button>`).join('');   // tip luôn có tên tab: Thư viện hẹp chỉ hiện biểu tượng (_mod-nhac.css)
  const b = $('#bLib'); if (b) { const mo = !ray || S.tv.noi; b.innerHTML = icon(mo ? 'thuGon' : 'moRong'); b.dataset.tip = mo ? 'Thu gọn thư viện' : 'Mở thư viện'; b.setAttribute('aria-label', b.dataset.tip); b.setAttribute('aria-expanded', String(mo)); }
}
function datThu(thu) {   // anh bấm thu gọn / mở thư viện
  S.tv.thu = !!thu; S.tv.noi = false; tvLuu('st-tv-thu', thu ? '1' : null);
  const ed = $('#edit'); ed.classList.toggle('tv-thu', S.tv.thu); ed.classList.remove('tv-noi');
  hopCot();
  if (!S.tv.thu && ed.classList.contains('tv-tu-thu')) datNoi(true);   // anh muốn mở mà chỗ chật: mở dạng bảng nổi
  veTvTabs(); veTV(true); window.dispatchEvent(new Event('resize'));
}
function datNoi(noi) {   // thư viện tự thu (chật): bấm icon thì mở bảng nổi đè lên khung xem
  S.tv.noi = !!noi; $('#edit').classList.toggle('tv-noi', S.tv.noi); veTvTabs(); if (noi) veTV(true);
}
function moTab(k) {
  if (!TV_TAB.some(x => x[0] === k)) return;
  if (S.tv.tab !== k) { S.tv.cuon[S.tv.tab] = $('#libPane').scrollTop; S.tv.tab = k; tvLuu('st-tv-tab', k); }
  if (S.tv.thu) datThu(false);
  else if ($('#edit').classList.contains('tv-tu-thu')) datNoi(true);
  veTvTabs(); veTV(true); veTimeline();
}

/* ---------- vẽ ---------- */
function tmTV() {   // thư mục clip của Thư viện: anh chọn lần trước (theo video) hoặc thư mục clip của cảnh đầu
  if (!S.tv.tm) { let cu = ''; try { cu = localStorage.getItem('st-tv-tm|' + S.v) || ''; } catch (e) {} S.tv.tm = cu || thuMucCua(src((S.plan.canh[0] || {}).file || Object.keys(S.plan.nguon || {})[0])); }   // video trống (0 cảnh): thư mục clip của nguồn
  return S.tv.tm;
}
function khoaTV() {
  const p = S.plan, k = p.kieu || {}, chu = p.chu || {}; tmTV();
  if (TV_THEM[S.tv.tab]) return JSON.stringify([S.tv.tab, S.tv.thu, S.tv.noi, S.v, TV_THEM[S.tv.tab].khoa ? TV_THEM[S.tv.tab].khoa() : '']);   // tab thêm (r20)
  if (S.tv.tab === 'giong') return JSON.stringify(['giong', S.tv.thu, S.tv.noi, S.v, (p.giong || {}).local || '', (p.giong || {}).ten || '']);   // bảng giọng tự vẽ lại (veGA): khỏi xoá ô đang gõ
  if (S.tv.tab === 'nhac') return JSON.stringify(['nhac', S.tv.thu, S.tv.noi, S.v, typeof khoaNhacTV === 'function' ? khoaNhacTV() : '']);   // bảng Nhạc (veNhacTV, dev/_mod-nhac.js)
  return JSON.stringify([S.tv.tab, S.tv.thu, S.tv.noi, S.sel.canh, S.tv.tm, S.tv.them, Object.keys(S.tv.ds), S.tv.tiTai, S.tv.tiDang, (S.ng || {}).dang,
    p.canh.map(c => [c._id, c.file, Math.round(c.tu * 10), Math.round(c.den * 10), c.chuyen || '', c.dong || '', c.hieu_ung || '', JSON.stringify([c.loc || '', c.mau || ''])]), k, Object.keys(p.nguon || {}),
    (chu.hook || []).join('|'), ((chu.nhan_chu || [])[0] || {}).chu, chu.the_gia && [chu.the_gia.gia, chu.the_gia.phu], 'ket' in chu ? chu.ket : 'md',
    ((p.phu_de || [])[0] || {}).chu, !!p.giong, (S.info.kieu_ds || []).length, S.ti && S.ti.ds && S.ti.ds.map(x => x.id + x.bat).join()]);
}
function veTV(ep) {
  if (!S.plan || !S.info || S.keo) return;
  const pane = $('#libPane'); if (!pane) return;
  const i = S.plan.canh.findIndex(c => c._id === S.sel.canh);
  const pb = $('#pbCanh'); if (pb) pb.textContent = i >= 0 ? 'Đang chọn cảnh ' + (i + 1) + ' / ' + S.plan.canh.length : '';
  if (S.tv.daVe !== S.v) { S.tv.daVe = S.v; S.tv.tm = ''; S.tv.khoa = ''; veTvTabs(); hopCot(); veTvTabs(); }
  if (tvRay() && !S.tv.noi) { S.tv.khoa = ''; pane.innerHTML = ''; return; }
  const k = khoaTV(); if (!ep && k === S.tv.khoa) return;
  const cungTab = S.tv.khoa && JSON.parse(S.tv.khoa)[0] === S.tv.tab; S.tv.khoa = k;
  const sc = cungTab ? pane.scrollTop : (S.tv.cuon[S.tv.tab] || 0);
  const them = TV_THEM[S.tv.tab];   // tab thêm từ dev/_mod-*.js (r20: Âm thanh)
  pane.innerHTML = them ? them.ve() : ({clip: tvClip, chu: tvChu, chuyen: tvChuyen, hieu: tvHieu, giong: () => '<div id="tvGa"></div>', nhac: () => '<div id="tvNhac"></div>', ti: tvTi})[S.tv.tab]();
  if (S.tv.tab === 'giong') veGiongAI($('#tvGa'));   // bảng giọng đọc AI của dev/_giong-ai.js
  if (S.tv.tab === 'nhac' && typeof veNhacTV === 'function') veNhacTV($('#tvNhac'));   // nhạc nền (dev/_mod-nhac.js, 4/11)
  if (them && them.sau) them.sau();
  if (typeof tvSauVe === 'function') tvSauVe(S.tv.tab, pane);   // chia nhóm + ô tìm Chuyển cảnh / Hiệu ứng (dev/_mod-thu-vien-them.js, r20)
  pane.scrollTop = sc;
}
// 4/11 tối anh: "mấy phần chữ này bị chiếm chỗ nhiều quá" -> câu hướng dẫn không chiếm hàng nữa: dấu (i) nhỏ cạnh tiêu đề mục, rê chuột / Tab tới mới hiện (chữ thường, không thẻ HTML)
IC_P.thongTin = '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.5v.01"/>';   // giống dấu (i) khung phải (dev/_mod-ben-phai.js)
const tvI = tip => tip ? `<button type="button" class="tv-i" data-tip="${esc(tip)}" aria-label="${esc(tip)}">${icon('thongTin')}</button>` : '';
const tvTieuDe = (t, phu, tip) => `<div class="tv-h"><h3>${t}</h3>${tvI(tip)}${phu ? `<span>${phu}</span>` : ''}</div>`;
function canhChon() { const b = bocCanh(), i = b.findIndex(x => x.c._id === S.sel.canh); return i >= 0 ? b[i] : b[0]; }
function anhCanh(c, t) { return thumbUrl(src(c.file), t == null ? (c.tu + c.den) / 2 : clamp(t, c.tu, Math.max(c.tu, c.den - 0.05))); }
const tvBg = u => `background-image:url('${u}')`;

/* ---------- Clip ---------- */
async function taiClipTV(tm) {
  if (!tm || S.tv.ds[tm]) return;
  S.tv.ds[tm] = {dang: true};
  try { const d = await api('/api/clip?thu_muc=' + encodeURIComponent(tm)); S.tv.ds[tm] = d; if (d.thu_muc && d.thu_muc !== tm) S.tv.ds[d.thu_muc] = d; }
  catch (e) { S.tv.ds[tm] = {loi: e.message}; }
  if (S.tv.tab === 'clip') veTV(true);
}
function tvClip() {
  const tm = tmTV(), d = S.tv.ds[tm];
  if (!d) setTimeout(() => taiClipTV(tm), 0);
  const x = canhChon(), n = x ? x.i + 1 : 0;
  const dung = {}; S.plan.canh.forEach((c, j) => { const q = chuanP(src(c.file)); (dung[q] = dung[q] || []).push(j + 1); });
  const tmVideo = [...new Set(Object.keys(S.plan.nguon || {}).map(f => thuMucCua(src(f))))].filter(t => t && chuanP(t) !== chuanP(tm));
  const goi = 'Bấm 1 clip: ' + (n ? 'thêm thành cảnh mới ngay sau cảnh ' + n + ' (cảnh đang chọn)' : 'thêm thành cảnh 1 (video đang trống)') + '. Hoặc kéo clip xuống timeline để chèn đúng chỗ. Dấu ✓ = clip đã có trong video, bấm phải để xem clip.';
  let h = `<div class="tv-tm"><span class="tv-tmt" data-tip="${esc(tm || 'Chưa chọn thư mục')}">${icon('thuMuc')}<b>${esc(tenTm(tm) || 'Chưa chọn thư mục')}</b></span>${tvI(goi)}<button type="button" class="btn small" data-tva="doi-tm">Đổi thư mục</button></div>`;
  if (tmVideo.length) h += `<div class="tv-tmk"><span>Thư mục khác của video:</span>${tmVideo.slice(0, 4).map(t => `<button type="button" class="tvchip" data-tvtm="${esc(t)}" data-tip="${esc(t)}">${esc(tenTm(t))}</button>`).join('')}</div>`;
  if (!d || d.dang) return h + '<p class="tv-note tv-cho">Đang đọc thư mục…</p>';
  if (d.loi) return h + `<p class="tv-note err">${esc(d.loi)}</p>`;
  if (!d.clip.length) return h + '<p class="tv-note tv-trang">Thư mục này không có clip video.</p>';
  return h + `<div class="tv-grid tv-clip">${d.clip.map(c => { const so = dung[chuanP(c.path)] || [], dang = S.tv.them === c.path;
    const tip = c.ten + (c.giay ? ' · ' + gs(c.giay) : '') + (so.length ? ' · đang dùng ở cảnh ' + so.join(', ') : '') + (n ? ' · bấm + để thêm sau cảnh ' + n : ' · bấm + để thêm thành cảnh 1') + ', hoặc kéo xuống timeline';
    return `<button type="button" class="tvc${so.length ? ' dung' : ''}${dang ? ' dang' : ''}" data-tvclip="${esc(c.path)}" data-tip="${esc(tip)}" aria-label="${esc('Thêm clip ' + c.ten + ' sau cảnh ' + n)}">
      <span class="tvc-a"><img loading="lazy" alt="" draggable="false" src="${thumbUrl(c.path, 1)}"><span class="tvc-them">${dang ? '<span class="tv-xoay"></span>' : icon('them')}</span>
      ${c.giay ? `<span class="tvc-dai">${gs(c.giay)}</span>` : ''}${so.length ? `<span class="tvc-ok" aria-label="Đã có trong video">${icon('dauTick')}</span>` : ''}</span>
      <span class="tvc-ten">${esc(String(c.ten).replace(/\.[^.]+$/, ''))}</span></button>`; }).join('')}</div>`;
}
async function nguonClipTV(p) {   // clip -> {f: khoá nguồn, x: kết quả /them-clip (null nếu đã có trong video)} | null
  const key = Object.keys(S.plan.nguon || {}).find(f => chuanP(src(f)) === chuanP(p));
  if (key && S.giay[key]) return {f: key, x: null, giay: S.giay[key]};
  S.tv.them = p; veTV(true);
  let x = null; try { x = await api('/api/sua-tay/them-clip', {p}); } catch (e) { toast(e.message, true); }
  S.tv.them = ''; if (!x) { veTV(true); return null; }
  const f = key || x.local; S.giay[f] = x.giay;
  return {f, x: key ? null : x, giay: x.giay};
}
const nguonMoi = x => ({local: x.local, rong: x.rong, cao: x.cao, co_tieng: x.co_tieng, hdr: x.hdr, hdr_trc: x.hdr_trc, am_thanh: x.co_tieng ? 'tieng_that' : null});
async function themClipTV(p, o = {}) {   // o.viTri: chèn ở vị trí này (kéo thả); không có = ngay sau cảnh đang chọn
  if (!S.plan || S.tv.them) return;
  const n = await nguonClipTV(p); if (!n) return;
  const {f, x, giay} = n;
  dung();
  let moi = null;
  doi(pl => {   // nguồn đặt trong doi(): Ctrl+Z bỏ được cả nguồn
    if (x) pl.nguon[f] = nguonMoi(x);
    const i = o.viTri != null ? clamp(o.viTri, 0, pl.canh.length) : pl.canh.findIndex(c => c._id === S.sel.canh) + 1;
    moi = {_id: ma('c'), file: f, tu: 0, den: r3(Math.max(0.3, (giay || 5) - 0.05))};
    pl.canh.splice(i, 0, moi); S.sel.canh = moi._id; S.selLoai = 'canh';
  });
  theoProxy();
  const b = bocCanh().find(y => y.c._id === moi._id);
  if (b) { tua(b.bd + 0.02); giuVach(); }
  toast('Đã thêm cảnh ' + (b ? b.i + 1 : '') + ' (' + base(f).replace(/\.[^.]+$/, '') + '): kéo mép vàng để cắt · Ctrl+Z để bỏ');
}
async function thayClipTV(p, id) {   // đổi clip của cảnh (giữ chỗ, giữ độ dài; nhãn / thẻ giá neo theo cảnh đi theo) — như hộp "Thay clip"
  id = id || S.sel.canh; const c0 = S.plan.canh.find(c => c._id === id); if (!c0) return;
  const n = await nguonClipTV(p); if (!n) return;
  const {f, x, giay} = n, so = S.plan.canh.indexOf(c0) + 1, d0 = c0.den - c0.tu;
  dung();
  doi(pl => { if (x) pl.nguon[f] = nguonMoi(x);
    const c = pl.canh.find(y => y._id === id); if (!c) return;
    const cu = {file: c.file, tu: c.tu}, d = c.den - c.tu, het = Math.max(0.3, (giay || 5) - 0.05);
    c.file = f; c.tu = 0; c.den = r3(Math.min(d, het)); delete c._phan; delete c._tach; delete c.noi_lien;
    [...(pl.chu.nhan_chu || []), pl.chu.the_gia].forEach(it => { const ne = it && it._neo;
      if (ne && ne.id === c._id && ne.file === cu.file) { ne.file = f; ne.s0 = r3(c.tu + (ne.s0 - cu.tu)); ne.s1 = r3(c.tu + (ne.s1 - cu.tu)); } });
    S.sel.canh = c._id; });
  theoProxy();
  const c1 = S.plan.canh.find(y => y._id === id);
  toast('Đã thay clip cảnh ' + so + (c1 && c1.den - c1.tu < d0 - 0.01 ? ' (clip mới ngắn hơn nên cảnh ngắn lại)' : '') + ' · Ctrl+Z để lấy lại');
}
async function xemClipTV(p) {   // xem clip trước khi thêm (bản xem nhẹ; HEVC / HDR cần chờ tạo)
  const {m} = modal(`<h3>${esc(base(p))}</h3><div class="tv-xem"><p class="note tv-cho">Đang chuẩn bị bản xem…</p></div>
    <div class="acts"><button class="btn" data-dong>Đóng</button><button class="btn primary" data-tv-them>${icon('them')} Thêm vào video</button></div>`);
  $('[data-tv-them]', m).onclick = () => { $('[data-dong]', m).click(); themClipTV(p); };
  for (let k = 0; k < 150 && document.body.contains(m); k++) {
    const r = await api('/api/sua-tay/proxy', {ds: [p]}).catch(() => null), x = r && (r[p] || Object.values(r)[0]);
    if (x && x.tt === 'xong' && x.url) { $('.tv-xem', m).innerHTML = `<video controls autoplay playsinline src="${x.url}"></video>`; return; }
    if (x && x.tt === 'loi') { $('.tv-xem', m).innerHTML = `<p class="note err">${esc(x.loi || 'Không xem được clip này')}</p>`; return; }
    await new Promise(z => setTimeout(z, 1200));
  }
}
function datTm(tm) { if (!tm) return; S.tv.tm = tm; tvLuu('st-tv-tm|' + S.v, tm); veTV(true); }

/* ---------- Chữ ---------- */
function tvChu() {
  const chu = S.plan.chu || {}, k = S.plan.kieu || {}, x = canhChon(), bg = x ? tvBg(anhCanh(x.c)) : '';
  const hk = (chu.hook || []).filter(Boolean), g = chu.the_gia, kmd = S.info.ket_mac_dinh || {};
  const ketMd = (k.ket === 'the_comment' ? kmd.the_comment : kmd.dia_chi) || [], coKet = !(chu.ket === null || k.ket === 'khong');
  const ket = Array.isArray(chu.ket) && chu.ket.some(Boolean) ? chu.ket : ketMd;
  const nhan = ((chu.nhan_chu || [])[0] || {}).chu || 'Pin 98%', pd = ((S.plan.phu_de || [])[0] || {}).chu || 'Máy đẹp không tì vết';
  const pdT = String(pd).toUpperCase().split(/\s+/).slice(0, 4), giua = Math.min(1, pdT.length - 1);
  const o = (loai, ten, phim, ve, goi) => `<button type="button" class="tvx tvm" data-tvmau="${loai}" data-tip="${esc(goi)}"${phim ? ` data-phim="${phim}"` : ''}>
      <span class="xv mv" style="${bg}"><span class="mv-in">${ve}</span><span class="tv-cong" aria-hidden="true">${icon('them')}</span></span><span class="tvx-ten">${ten}${phim ? `<kbd>${phim}</kbd>` : ''}</span></button>`;
  let h = tvTieuDe('Thêm chữ', 'ở vạch đỏ')
    + `<div class="tv-grid tv-chu">`
    + o('nhan', 'Nhãn chữ', 'T', `<b class="m-nhan">${esc(nhan)}</b>`, 'Chữ vàng to giữa khung (tên máy, pin 98%…), thêm ở vạch đỏ rồi gõ chữ')
    + o('gia', g ? 'Dời thẻ giá' : 'Thẻ giá', 'G', `<span class="m-gia"><b>${esc((g && g.gia) || '13tr9')}</b><small>${esc((g && g.phu) || 'BH 6 tháng')}</small></span>`, g ? 'Video đã có thẻ giá: dời thẻ giá tới vạch đỏ' : 'Đặt thẻ giá ở vạch đỏ rồi gõ giá')
    + o('pd', 'Câu phụ đề', 'P', `<b class="m-pd">${pdT.map((w, j) => j === giua ? `<em>${esc(w)}</em>` : esc(w)).join(' ')}</b>`, 'Thêm 1 câu phụ đề ở vạch đỏ rồi gõ chữ')
    + o('hook', hk.length ? 'Sửa hook' : 'Hook 2 dòng', '', `<span class="m-hook"><b>${esc(hk[0] || 'iPad Pro M1')}</b><b>${esc(hk[1] || 'giá chỉ 13tr9?')}</b></span>`, 'Hook = 2 dòng chữ đầu video, dòng 2 màu vàng')
    + o('ket', coKet ? 'Sửa thẻ kết' : 'Bật thẻ kết', '', `<span class="m-ket"><b>${esc(ket[0] || 'Ghé Poly test máy nha')}</b><small>${esc(ket[1] || '')}</small></span>`, coKet ? 'Thẻ kết cuối video: sửa câu, số giây' : 'Video đang không có thẻ kết: bấm để bật câu mặc định')
    + `</div>`;
  if (!S.plan.giong) h += `<button type="button" class="btn tv-rong" data-tva="nghe" ${(S.ng || {}).dang ? 'disabled' : ''} data-tip="Máy nghe lời nói trong các cảnh (không cần Claude, không cần mạng) rồi chia thành câu 3–6 từ">${icon('mic')}${(S.ng || {}).dang ? 'Đang nghe lời nói…' : 'Tạo phụ đề từ lời nói'}</button>`;
  else h += '<p class="tv-note tv-trang">Video dùng giọng đọc AI: phụ đề đi theo giọng.</p>';
  return h + tvTieuDe('Kiểu chữ cả video', 'bấm là xem mẫu ngay') + ['chu', 'phu_de', 'ket'].map(tvChips).join('');
}
function tvChips(m) {
  const d = (S.info.kieu_ds || []).find(x => x.muc === m), v = (S.plan.kieu || {})[m];
  if (!d || d.ds.length < 2) return '';
  return `<div class="tv-k"><div class="tv-kt">${esc(d.ten)}</div><div class="tv-chips">${d.ds.map(x => `<button type="button" class="tvchip${v === x.v ? ' on' : ''}" data-tvkieu="${esc(m)}" data-v="${esc(x.v)}" aria-pressed="${v === x.v}">${v === x.v ? icon('dauTick') : ''}${esc(x.ten)}</button>`).join('')}</div></div>`;
}
function bamMau(loai) {
  dung();
  if (loai === 'nhan' || loai === 'gia' || loai === 'pd') return themChu(loai);
  const v = S.view || {};
  if (loai === 'hook') { if (v.hook_t && ((S.plan.chu || {}).hook || []).some(Boolean)) { tua(v.hook_t[0] + 0.4); giuVach(); } return oNhap('hook', 'chu', '#pane input[data-f="hook0"]'); }
  if (loai === 'ket') {
    const chu = S.plan.chu || {};
    if (chu.ket === null || (S.plan.kieu || {}).ket === 'khong') { doi(p => { delete p.chu.ket; if (p.kieu.ket === 'khong') p.kieu.ket = 'the_comment'; }); toast('Đã bật thẻ kết câu mặc định (Ctrl+Z để bỏ)'); }
    else if (v.ket_t) { tua(v.ket_t[0] + 0.5); giuVach(); }
    return oNhap('ket', 'chu', '#pane [data-r="ketmode"] button.on');
  }
}
function bamKieu(m, v) {
  if (kieuDung(m) === v) return xemMau(m);   // đang dùng đúng giá trị này (4/11: so với giá trị đang dùng, không phải giá trị máy bốc)
  sua('kieu:' + m, v, true); xemMau(m);
}

/* ---------- Chuyển cảnh ---------- */
// lớp CSS xem trước theo khoá chuyển cảnh (cùng bảng kieu_dung.json -> chuyen_canh_ky_thuat: khoá -> xfade)
const TV_XC = {cat_cung: 'cat', hoa_tan_nhanh: 'fade', nhay_trang: 'trang', truot_ngang: 'ngang', truot_doc: 'doc', zoom_xuyen: 'zoom',
  lau_mem: 'lau', mo_tron: 'tron', mo_chuyen_dong: 'nhoe', vo_diem: 'vo', tron_poly: 'fade',
  // 10 kiểu chỉ gắn riêng từng cảnh (S.info.chuyen_rieng)
  de_luot: 'deDoc', truot_ngang_muot: 'ngangMuot', truot_doc_muot: 'docMuot', keo_len: 'keoLen', de_ngang: 'deNgang',
  lau_mem_doc: 'lauDoc', mo_cua: 'cua', hoa_tan_sang: 'fadeNhanh', lau_cheo: 'cheo', nhay_den: 'den'};
function oXc(v, ten, a, b, o = {}) {
  return `<button type="button" class="tvx${o.on ? ' on' : ''}" data-tvchuyen="${esc(v)}"${o.tat ? ' disabled' : ''} data-tip="${esc(o.goi || ten)}">
    <span class="xv xc-${TV_XC[o.kieu || v] || 'fade'}" style="--a:url('${a}');--b:url('${b}')"><i class="xa"></i><i class="xb"></i><i class="xf"></i>${o.on ? `<span class="tick">${icon('dauTick')}</span>` : ''}${o.chung ? '<span class="tv-tag">Chung</span>' : ''}${o.cham ? '<span class="tv-tag cham">chậm</span>' : ''}<span class="tv-cong" aria-hidden="true">${icon('them')}</span></span>
    <span class="tvx-ten">${esc(ten)}</span></button>`;
}
function tvChuyen() {
  const b = bocCanh(), x = canhChon(); if (!x) return '';
  const i = x.i, c = x.c, k = S.plan.kieu || {}, truoc = b[i - 1];
  const A = truoc ? anhCanh(truoc.c, truoc.c.den - 0.15) : anhCanh(c, c.tu + 0.1), B = anhCanh(c, c.tu + 0.1);
  let h = '';
  if (b.length < 2) {   // r29 (soi L3): video 1 cảnh = chưa có chỗ nối -> chỉ đường Chia (S) ngay tại chỗ, không bày 36 ô mờ
    const chiaDuoc = !!canhLuc(S.t);
    h += `<div class="tv-tm tv-trong tv-1canh"><span class="tv-tmt"><span><b>Video mới có 1 cảnh</b> nên chưa có chỗ nối để đặt chuyển cảnh.</span></span>${tvI('Chuyển cảnh nằm ở chỗ nối giữa 2 cảnh. Đưa vạch đỏ tới chỗ muốn đổi cảnh rồi bấm ✂ Chia (phím S): cảnh 2 sẽ có ô Chuyển cảnh vào.')}</div>
      <div class="tv-hang tv-1canh-nut"><button type="button" class="btn small primary" data-tva="chia" ${chiaDuoc ? '' : 'disabled'} data-tip="Chia cảnh ở vạch đỏ (phím S), rồi chọn chuyển cảnh cho cảnh 2">${icon('chia')}Chia ở vạch đỏ <kbd>S</kbd></button><span class="note">Đưa vạch đỏ (${esc(tg(S.t))}) tới chỗ muốn đổi cảnh trước</span></div>`;
    return h + tvTieuDe('Kiểu chuyển cảnh cả video', 'cảnh không chọn riêng sẽ theo kiểu này') + tvChips('chuyen_canh');
  }
  if (i === 0) {
    h += `<div class="tv-tm tv-trong"><span class="tv-tmt"><span>Cảnh 1 không có chuyển cảnh vào</span></span>${tvI('Cảnh 1 là cảnh đầu video nên không có chuyển cảnh vào. Chọn cảnh khác: bấm cảnh trên timeline, hoặc bấm nút nối giữa 2 cảnh.')}${b.length > 1 ? `<button type="button" class="btn small" data-tva="canh2">Chọn cảnh 2</button>` : ''}</div>`;
  } else {
    h += `<div class="tv-ab"><span class="tv-ab-a" style="${tvBg(A)}"></span>${icon('chuyenC')}<span class="tv-ab-b" style="${tvBg(B)}"></span>
      <div><b>Vào cảnh ${i + 1}</b><small>từ cảnh ${i} · ${c.chuyen ? 'đang dùng: ' + esc(tenGiaTri('chuyen_canh', c.chuyen)) : 'đang theo kiểu chung: ' + esc(tenNgan('chuyen_canh'))}</small></div></div>`;
  }
  const tat = i === 0, chung = kieuDung('chuyen_canh');   // giá trị đang dùng (4/11: video tạo tay mặc định trơn = cắt thẳng)
  h += `<div class="tv-grid tv-xc${tat ? ' tat' : ''}">`
    + oXc('', 'Theo kiểu chung', A, B, {on: !tat && !c.chuyen, tat, kieu: chung, chung: true, goi: 'Theo kiểu chuyển cảnh cả video: ' + tenGiaTri('chuyen_canh', chung)})
    + dsChuyenCanh().map(y => oXc(y.v, y.ten, A, B, {on: !tat && c.chuyen === y.v, tat, cham: y.cham, goi: y.ten + ' · rê chuột để xem, bấm để dùng cho cảnh ' + (i + 1) + (y.cham ? '. ' + CHAM_GOI : '')})).join('') + `</div>`;
  if (!tat) h += `<div class="tv-hang"><button type="button" class="btn small" data-tvtat="chuyen" ${c.chuyen ? '' : 'disabled'} data-tip="${c.chuyen ? 'Dùng ' + esc(tenGiaTri('chuyen_canh', c.chuyen)) + ' cho mọi chỗ nối' : 'Chọn 1 kiểu cho cảnh này trước'}">${icon('lop')}Áp cho mọi cảnh</button>
    <button type="button" class="btn small ghost" data-tvbo="chuyen" ${S.plan.canh.some(y => y.chuyen) ? '' : 'disabled'} data-tip="Bỏ chuyển cảnh riêng của mọi cảnh, theo kiểu chung">${icon('boHet')}Bỏ hết</button></div>`;
  return h + tvTieuDe('Kiểu chuyển cảnh cả video', 'cảnh không chọn riêng sẽ theo kiểu này') + tvChips('chuyen_canh');
}

/* ---------- Hiệu ứng ---------- */
const TV_DONG = {dung_yen: 'yen', zoom_vao: 'zvao', zoom_ra: 'zra', phong_sat: 'sat', lia_phai: 'liap', lia_trai: 'liat',
  zoom_xen_ke: 'zxk', punch_nhip: 'punch', pan_ngang: 'liap'};
const TV_HINH = {lay_net_nhe: 'net', khu_nhieu_nhe: 'khuNhieu', mau_san_pham: 'mauSp', trang_sach: 'trang', zoom_nay: 'nay',
  lay_net_vao: 'netVao', vet_sang_quet: 'quet', mo_chuyen_dong: 'moCd'};
const TV_VIDEO = {diem_nhan: {khong: '', chop_trang: 'chop', rung_nhip: 'rung', glitch_rgb: 'glitch', zoom_dap: 'dap'},
  lop_phu: {khong: '', hat_film: 'hat', toi_vien: 'toi', loa_sang: 'loa'}, mau: {trung_tinh: '', am_nhe: 'am', tuong_phan: 'tp'},
  chuyen_dong: TV_DONG, nhip: {nhanh: 'nhanh', vua: 'vua'}};
function oHu(attr, v, ten, anh, lop, o = {}) {
  return `<button type="button" class="tvx${o.on ? ' on' : ''}" ${attr}="${esc(v)}"${o.v != null ? ` data-v="${esc(o.v)}"` : ''} data-tip="${esc(o.goi || ten)}">
    <span class="xv hu ${lop ? 'hu-' + lop : ''}" style="--b:url('${anh}')"><i class="xb"></i><i class="xf"></i>${o.on ? `<span class="tick">${icon('dauTick')}</span>` : ''}${o.chung ? '<span class="tv-tag">Chung</span>' : ''}${o.tag ? `<span class="tv-tag duoi">${esc(o.tag)}</span>` : ''}<span class="tv-cong" aria-hidden="true">${icon('them')}</span></span>
    <span class="tvx-ten">${esc(ten)}</span></button>`;
}
function tvHieu() {
  const x = canhChon(); if (!x) return '';
  const c = x.c, k = S.plan.kieu || {}, anh = anhCanh(c);
  let h = tvTieuDe('Chuyển động cảnh ' + (x.i + 1), c.dong ? tenGiaTri('chuyen_dong', c.dong) : 'theo kiểu chung: ' + tenNgan('chuyen_dong'))
    + `<div class="tv-grid tv-hu">` + oHu('data-tvdong', '', 'Theo kiểu chung', anh, TV_DONG[kieuDung('chuyen_dong')] || 'zxk', {on: !c.dong, chung: true, goi: 'Theo chuyển động cả video: ' + tenGiaTri('chuyen_dong', kieuDung('chuyen_dong'))})
    + dsDongCanh().map(([v, t]) => oHu('data-tvdong', v, t, anh, TV_DONG[v], {on: c.dong === v, goi: t + ' · bấm để dùng cho cảnh ' + (x.i + 1)})).join('') + `</div>`
    + `<div class="tv-hang"><button type="button" class="btn small" data-tvtat="dong" ${c.dong ? '' : 'disabled'} data-tip="${c.dong ? 'Dùng ' + esc(tenGiaTri('chuyen_dong', c.dong)) + ' cho mọi cảnh' : 'Chọn 1 kiểu cho cảnh này trước'}">${icon('lop')}Áp cho mọi cảnh</button>
      <button type="button" class="btn small ghost" data-tvbo="dong" ${S.plan.canh.some(y => y.dong) ? '' : 'disabled'} data-tip="Bỏ chuyển động riêng của mọi cảnh, theo kiểu chung">${icon('boHet')}Bỏ hết</button></div>`;
  const hh = dsHieuUngHinh();
  if (hh.length) h += tvTieuDe('Hiệu ứng hình cảnh ' + (x.i + 1), c.hieu_ung ? tenGiaTri('hieu_ung', c.hieu_ung) : 'không có')
    + `<div class="tv-grid tv-hu">` + oHu('data-tvhinh', '', 'Không', anh, '', {on: !c.hieu_ung, goi: 'Cảnh ' + (x.i + 1) + ' không có hiệu ứng hình'})
    + hh.map(y => oHu('data-tvhinh', y.v, y.ten, anh, TV_HINH[y.v] || '', {on: c.hieu_ung === y.v, tag: y.dau_canh ? 'đầu cảnh' : '', goi: y.ten + (y.dau_canh ? ' (chỉ chạy ở đầu cảnh)' : '') + ' · bấm để dùng cho cảnh ' + (x.i + 1)})).join('') + `</div>`
    + `<div class="tv-hang"><button type="button" class="btn small" data-tvtat="hieu_ung" ${c.hieu_ung ? '' : 'disabled'} data-tip="${c.hieu_ung ? 'Dùng ' + esc(tenGiaTri('hieu_ung', c.hieu_ung)) + ' cho mọi cảnh' : 'Chọn 1 hiệu ứng cho cảnh này trước'}">${icon('lop')}Áp cho mọi cảnh</button>
      <button type="button" class="btn small ghost" data-tvbo="hieu_ung" ${S.plan.canh.some(y => y.hieu_ung) ? '' : 'disabled'} data-tip="Bỏ hiệu ứng hình của mọi cảnh">${icon('boHet')}Bỏ hết</button></div>`;
  if (typeof tvHinhLoc === 'function') h += tvHinhLoc(x);   // nhóm "Bộ lọc" màu LUT (dev/_mod-hinh.js, 4/11)
  h += tvTieuDe('Cả video', 'bấm là xem mẫu ngay trong khung');
  ['diem_nhan', 'lop_phu', 'mau', 'chuyen_dong', 'nhip'].forEach(m => {
    const d = (S.info.kieu_ds || []).find(y => y.muc === m); if (!d || d.ds.length < 2) return;
    const kv = kieuDung(m);   // giá trị đang dùng (video tạo tay chưa tự chọn chuyển động: Đứng yên, 4/11)
    h += `<div class="tv-k"><div class="tv-kt">${esc(d.ten)}<span>${esc(tenGiaTri(m, kv))}</span></div><div class="tv-grid tv-hu nho">${d.ds.map(y => oHu('data-tvkieu', m, y.ten, anh, (TV_VIDEO[m] || {})[y.v] || '', {v: y.v, on: kv === y.v, goi: d.ten + ': ' + y.ten})).join('')}</div></div>`;
  });
  return h;
}

/* ---------- Tiện ích ---------- */
function tvTi() {
  if (!S.tv.tiTai) {
    if (!S.tv.tiDang) { S.tv.tiDang = true; taiTi(true).finally(() => { S.tv.tiDang = false; S.tv.tiTai = true; if (S.tv.tab === 'ti') veTV(true); }); }
    return '<p class="tv-note tv-cho">Đang tải tiện ích…</p>';
  }
  const T = S.ti || {ds: []}, bat = (T.ds || []).filter(x => x.bat && !x.loi);
  return tvTieuDe('Tiện ích đang bật', bat.length ? bat.length + ' tiện ích' : '', 'Script chạy trên video đang mở, xong vẫn Ctrl+Z được. Giống nút ⚡ Tiện ích trên đầu trang.')
    + (T.loi ? `<p class="tv-note err">${esc(T.loi)}</p>` : '')
    + (bat.length ? `<div class="tv-ti">${bat.map(x => `<div class="tvti"${x.mo_ta ? ` data-tip="${esc(x.mo_ta)}"` : ''}><div><b>${esc(x.ten)}</b>${x.mo_ta ? `<small>${esc(x.mo_ta)}</small>` : ''}</div>
        <button type="button" class="btn small primary" data-tvti="${esc(x.id)}" data-tip="${(x.hoi || []).length ? 'Hỏi vài ô rồi chạy' : 'Chạy ngay trên video này'}">${icon('play')}Chạy${(x.hoi || []).length ? '…' : ''}</button></div>`).join('')}</div>`
      : '<p class="tv-note tv-trang">Chưa có tiện ích nào đang bật.</p>')
    + `<div class="tv-hang"><button type="button" class="btn small" data-tva="ql-ti">${icon('caiDat')}Quản lý tiện ích…</button><button type="button" class="btn small ghost" data-tva="tai-ti">${icon('lamMoi')}Tải lại</button></div>`;
}

/* ---------- bấm ---------- */
$('#lib').addEventListener('click', async e => {
  const t = e.target.closest('button'); if (!t || t.disabled) return;
  if (t.dataset.tv) return moTab(t.dataset.tv);
  if (t.hasAttribute('data-tv-mo')) return S.tv.thu ? datThu(false) : datNoi(!S.tv.noi);
  if (t.dataset.tvclip) return themClipTV(t.dataset.tvclip);
  if (t.dataset.tvtm) return datTm(t.dataset.tvtm);
  if (t.dataset.tvmau) return bamMau(t.dataset.tvmau);
  const x = canhChon();
  if (t.dataset.tvchuyen != null && x) return datHieuUng(x.c._id, 'chuyen', t.dataset.tvchuyen || null);
  if (t.dataset.tvdong != null && x) return datHieuUng(x.c._id, 'dong', t.dataset.tvdong || null);
  if (t.dataset.tvhinh != null && x) return datHieuUng(x.c._id, 'hieu_ung', t.dataset.tvhinh || null);
  if (t.dataset.tvtat && x) return datHieuUng(x.c._id, t.dataset.tvtat, x.c[t.dataset.tvtat], true);
  if (t.dataset.tvbo && x) return datHieuUng(x.c._id, t.dataset.tvbo, null, true);
  if (t.dataset.tvkieu) return bamKieu(t.dataset.tvkieu, t.dataset.v);
  if (t.dataset.tvti) return chayTuMenu(t.dataset.tvti);
  const a = t.dataset.tva;
  if (a === 'doi-tm') { const tm = S.tv.tm; const p = await CTM(tm ? CTM.cha(tm) : '', tm); if (p) datTm(p); return; }
  if (a === 'nghe') return taoPhuDe(false);
  if (a === 'chia') { chiaCanh(); const b = bocCanh()[1]; if (b) { S.sel.canh = b.c._id; S.selLoai = 'canh'; veBen(true); veTimeline(); } return; }   // r29 (L3): chia xong chọn luôn cảnh 2 -> ô chuyển cảnh hiện ra
  if (a === 'canh2') { const b = bocCanh()[1]; if (b) { S.sel.canh = b.c._id; S.selLoai = 'canh'; dung(); tua(b.bd + 0.02); giuVach(); veBen(true); veTimeline(); } return; }
  if (a === 'ql-ti') return quanLyTi();
  if (a === 'tai-ti') { S.tv.tiTai = false; return veTV(true); }
});
$('#bLib').addEventListener('click', () => { if ($('#edit').classList.contains('tv-tu-thu') && !S.tv.thu) datNoi(!S.tv.noi); else datThu(!S.tv.thu); });
// bảng nổi: bấm ra ngoài / Esc thì đóng
addEventListener('pointerdown', e => { if (S.tv.noi && !e.target.closest('#lib, #bLib, .mbg, .ctm-bg, .cmenu, .tip, .toast')) datNoi(false); }, true);
addEventListener('keydown', e => { if (e.key === 'Escape' && S.tv.noi && !$('.mbg') && !$('.ctm-bg')) datNoi(false); });
// nút nối ◆ giữa 2 cảnh trên timeline: chọn cảnh sau + mở Thư viện › Chuyển cảnh
function moChuyenCanh(id) {
  const x = bocCanh().find(y => y.c._id === id); if (!x) return;
  dung(); S.sel.canh = id; S.selLoai = 'canh';
  tua(x.bd + 0.02); giuVach();
  if (S.tv.tab !== 'chuyen') { S.tv.cuon[S.tv.tab] = $('#libPane').scrollTop; S.tv.tab = 'chuyen'; tvLuu('st-tv-tab', 'chuyen'); }
  if (S.tv.thu) datThu(false); else if ($('#edit').classList.contains('tv-tu-thu')) datNoi(true);
  veTvTabs(); veBen(true); veTimeline(); veTV(true);
}
$('#tCanh').addEventListener('click', e => { const n = e.target.closest('.noi[data-noi]'); if (!n) return; e.stopPropagation(); moChuyenCanh(n.dataset.noi); });
// lúc tự thu / tự mở theo cỡ cửa sổ: vẽ lại tab (hàng icon <-> hàng chữ)
let tvRayCu = null;
addEventListener('resize', () => { const r = tvRay(); if (r !== tvRayCu) { tvRayCu = r; if (!r && S.tv.noi) datNoi(false); veTvTabs(); veTV(true); } });
// khởi đầu: lớp thu gọn, tab, biểu tượng làn trong cột tên làn, nút thư viện
$('#edit').classList.toggle('tv-thu', S.tv.thu);
veTvTabs(); tvRayCu = tvRay();
[['nmCanh', 'clip', 'Cảnh'], ['nmChu', 'nhan', 'Chữ'], ['nmPd', 'pd', 'Phụ đề'], ['nmGiong', 'mic', 'Giọng']].forEach(([id, ic, ten]) => { const el = document.getElementById(id); if (el) el.innerHTML = icon(ic) + `<b>${ten}</b>`; });
$('#pbTt').innerHTML = icon('dung9') + '<span>Xem trước</span>';
// lọc vỡ điểm ảnh cho ô xem trước "Vỡ điểm ảnh"
document.body.insertAdjacentHTML('beforeend', '<svg class="tv-svg" width="0" height="0" aria-hidden="true" focusable="false"><filter id="tvPx" x="0" y="0" width="1" height="1"><feFlood x="3" y="3" height="1" width="1"/><feComposite width="7" height="7"/><feTile result="a"/><feComposite in="SourceGraphic" in2="a" operator="in"/><feMorphology operator="dilate" radius="3"/></filter></svg>');

/* ---------- kéo thả từ Thư viện xuống timeline (như CapCut, 3/11 đêm) ----------
   clip -> chèn cảnh ở chỗ thả (vạch vàng) · chuyển cảnh -> thả lên nút nối ◆ hoặc khối cảnh · chuyển động / hiệu ứng hình -> khối cảnh
   · nhãn / thẻ giá / phụ đề -> làn Chữ / Phụ đề đúng giây thả. Kéo bằng chuột (pointer), < 6px = bấm như thường. */
const TV_KEO = '[data-tvclip], [data-tvmau="nhan"], [data-tvmau="gia"], [data-tvmau="pd"], [data-tvchuyen], [data-tvdong], [data-tvhinh]';
function loaiKeo(t) {
  if (t.dataset.tvclip) return {loai: 'clip', v: t.dataset.tvclip, ten: base(t.dataset.tvclip).replace(/\.[^.]+$/, ''), ic: 'clip'};
  if (t.dataset.tvmau) return {loai: 'chu', v: t.dataset.tvmau, ten: {nhan: 'Nhãn chữ', gia: 'Thẻ giá', pd: 'Câu phụ đề'}[t.dataset.tvmau], ic: {nhan: 'nhan', gia: 'gia', pd: 'pd'}[t.dataset.tvmau]};
  const ten = (t.querySelector('.tvx-ten') || {}).textContent || '';
  if (t.dataset.tvchuyen != null) return {loai: 'chuyen', v: t.dataset.tvchuyen || null, ten, ic: 'chuyenC'};
  if (t.dataset.tvdong != null) return {loai: 'dong', v: t.dataset.tvdong || null, ten, ic: 'dongK'};
  return {loai: 'hinh', v: t.dataset.tvhinh || null, ten, ic: 'hieuUng'};
}
function timDich(k, x, y) {   // chỗ sẽ thả dưới con trỏ -> {kieu, ...} | {sai: lý do} | null
  const el = document.elementFromPoint(x, y); if (!el || !el.closest('#tls')) return null;
  const T = (S.view || {}).T || tongT(), t = clamp(tTuX(x), 0, T), b = bocCanh();
  if (k.loai === 'clip') { let i = b.length; for (const y of b) if (t < (y.a + y.b) / 2) { i = y.i; break; } return {kieu: 'chen', i, x: (i < b.length ? b[i].a : b.length ? b[b.length - 1].b : 0) * S.pps}; }   // video trống: chèn ở đầu
  if (k.loai === 'chu') return {kieu: 'gio', t, lan: k.v === 'pd' ? '#tPd' : '#tChu'};
  const noi = el.closest('#tCanh .noi[data-noi]'), blk = el.closest('#tCanh .blk');
  const id = noi ? noi.dataset.noi : blk ? blk.dataset.id : (canhLuc(t) || {c: {}}).c._id;
  const i = b.findIndex(y => y.c._id === id); if (i < 0) return null;
  if (k.loai === 'chuyen' && i === 0) return {sai: 'Cảnh 1 là cảnh đầu: không có chuyển cảnh vào', id};
  return {kieu: 'canh', id, i, noi: !!noi};
}
function veDich(d) {
  $$('#tCanh .tha').forEach(x => x.classList.remove('tha', 'tha-sai')); const ins = $('#tvIns'); if (ins) ins.remove();
  if (!d) return;
  if (d.sai || d.kieu === 'canh') { const e = d.noi ? $(`#tCanh .noi[data-noi="${d.id}"]`) : $(`#tCanh .blk[data-id="${d.id}"]`); if (e) e.classList.add('tha', ...(d.sai ? ['tha-sai'] : [])); return; }
  const l = document.createElement('div'); l.id = 'tvIns'; l.className = 'tv-ins';
  if (d.kieu === 'chen') { l.style.left = (d.x - 2) + 'px'; l.style.top = '24px'; l.style.height = '78px'; }
  else { const ln = $(d.lan); l.classList.add('gio'); l.style.left = (d.t * S.pps - 1) + 'px'; l.style.top = ln.style.top; l.style.height = ln.style.height; }
  $('#tlin').append(l);
}
async function thaDich(k, d) {
  if (k.loai === 'clip') return themClipTV(k.v, {viTri: d.i});
  if (k.loai === 'chu') { dung(); tua(d.t); giuVach(); return themChu(k.v); }
  S.sel.canh = d.id; S.selLoai = 'canh'; veTimeline();
  datHieuUng(d.id, k.loai === 'chuyen' ? 'chuyen' : k.loai === 'dong' ? 'dong' : 'hieu_ung', k.v);
  veBen(true);
}
$('#libPane').addEventListener('pointerdown', e => {
  if (e.button !== 0 || !S.plan) return;
  const t = e.target.closest(TV_KEO); if (!t || t.disabled) return;
  const k = loaiKeo(t), x0 = e.clientX, y0 = e.clientY; let keo = false, dich = null, gh = null;
  const mv = ev => {
    if (!keo) { if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < 6) return;
      keo = true; S.tv.keoTha = true; dung(); document.body.classList.add('tv-dang-keo'); $$('.tip').forEach(x => x.classList.remove('on'));
      gh = document.createElement('div'); gh.className = 'tv-bong'; gh.innerHTML = icon(k.ic) + `<span>${esc(k.ten || '')}</span><small></small>`; document.body.append(gh); }
    gh.style.left = (ev.clientX + 12) + 'px'; gh.style.top = (ev.clientY + 10) + 'px';
    const tls = $('#tls'), r = tls.getBoundingClientRect();   // sát mép timeline: cuộn theo
    if (ev.clientY > r.top && ev.clientY < r.bottom) { if (ev.clientX < r.left + 40) tls.scrollLeft -= 14; else if (ev.clientX > r.right - 40) tls.scrollLeft += 14; }
    dich = timDich(k, ev.clientX, ev.clientY); veDich(dich);
    gh.classList.toggle('sai', !!(dich && dich.sai)); gh.classList.toggle('co', !!(dich && !dich.sai));
    $('small', gh).textContent = !dich ? (k.loai === 'clip' ? 'thả xuống timeline' : k.loai === 'chu' ? 'thả lên làn chữ' : 'thả lên 1 cảnh') : dich.sai || (
      dich.kieu === 'chen' ? 'chèn thành cảnh ' + (dich.i + 1) : dich.kieu === 'gio' ? 'thêm lúc ' + tg(dich.t) : (k.loai === 'chuyen' ? 'vào cảnh ' : 'cảnh ') + (dich.i + 1));
  };
  const xong = ev => {
    removeEventListener('pointermove', mv); removeEventListener('pointerup', xong); removeEventListener('pointercancel', xong);
    if (!keo) return;
    if (gh) gh.remove(); veDich(null); document.body.classList.remove('tv-dang-keo');
    S.tv.vuaKeo = true; setTimeout(() => { S.tv.vuaKeo = false; S.tv.keoTha = false; }, 0);
    if (ev.type === 'pointerup' && dich && !dich.sai) thaDich(k, dich);
    else if (dich && dich.sai) toast(dich.sai, true);
  };
  addEventListener('pointermove', mv); addEventListener('pointerup', xong); addEventListener('pointercancel', xong);
});
$('#lib').addEventListener('click', e => { if (S.tv.vuaKeo) { e.stopImmediatePropagation(); e.preventDefault(); } }, true);   // vừa kéo xong: không tính là bấm
$('#libPane').addEventListener('dragstart', e => e.preventDefault());

/* ---------- bấm phải vào ô Thư viện: menu riêng của ô ---------- */
function xemMauThu(m, sua, o = {}) { xemMau(m, Object.assign({sua}, o)); }
function menuTV(t) {
  const x = canhChon(), id = x && x.c._id, n = x ? x.i + 1 : 1, so = S.plan.canh.length;
  if (t.dataset.tvclip) { const p = t.dataset.tvclip, ten = base(p);
    return [{nhom: ten}, {t: 'Thêm sau cảnh ' + n + ' (cảnh đang chọn)', ic: 'them', f: () => themClipTV(p)},
      {t: 'Thêm ở đầu video', f: () => themClipTV(p, {viTri: 0})}, {t: 'Thêm ở cuối video', f: () => themClipTV(p, {viTri: so})},
      {t: 'Thay clip cảnh ' + n + ' bằng clip này', ic: 'thay', f: () => thayClipTV(p, id)}, '-', {t: 'Xem clip…', ic: 'play', f: () => xemClipTV(p)}]; }
  if (t.dataset.tvmau) { const l = t.dataset.tvmau, coGia = !!(S.plan.chu || {}).the_gia;
    const ten = {nhan: 'Nhãn chữ', gia: 'Thẻ giá', pd: 'Câu phụ đề', hook: 'Hook', ket: 'Thẻ kết'}[l];
    return [{nhom: ten}, {t: l === 'hook' ? 'Sửa hook' : l === 'ket' ? 'Sửa / bật thẻ kết' : l === 'gia' && coGia ? 'Dời thẻ giá tới vạch đỏ' : 'Thêm ở vạch đỏ (' + tg(S.t) + ')', ic: {nhan: 'nhan', gia: 'gia', pd: 'pd'}[l] || 'nhan', phim: {nhan: 'T', gia: 'G', pd: 'P'}[l], f: () => bamMau(l)}]; }
  if (t.dataset.tvchuyen != null) { const v = t.dataset.tvchuyen || null, ten = v ? tenGiaTri('chuyen_canh', v) : 'Theo kiểu chung', dau = x && x.i === 0;
    return [{nhom: 'Chuyển cảnh · ' + ten}, {t: 'Dùng cho cảnh ' + n + ' (vào cảnh ' + n + ')', ic: 'chuyenC', tat: dau, ly_do: dau ? 'Cảnh đầu không có chuyển cảnh vào' : '', f: () => datHieuUng(id, 'chuyen', v)},
      {t: v ? 'Áp cho mọi cảnh' : 'Bỏ hết, theo kiểu chung', ic: 'lop', f: () => datHieuUng(id, 'chuyen', v, true)},
      v && !dau && {t: 'Xem mẫu (chưa áp)…', ic: 'play', f: () => xemMauThu('chuyen_canh', p => { p.canh[x.i].chuyen = v; }, {i: x.i - 1, nhan: 'Thử: vào cảnh ' + n + ' · ' + ten + ' (chưa áp)'})}]; }
  if (t.dataset.tvdong != null || t.dataset.tvhinh != null) { const dg = t.dataset.tvdong != null, v = (dg ? t.dataset.tvdong : t.dataset.tvhinh) || null, khoa = dg ? 'dong' : 'hieu_ung';
    const ten = v ? tenGiaTri(dg ? 'chuyen_dong' : 'hieu_ung', v) : dg ? 'Theo kiểu chung' : 'Không', hu = dsHieuUngHinh().find(y => y.v === v) || {};
    return [{nhom: (dg ? 'Chuyển động · ' : 'Hiệu ứng hình · ') + ten}, {t: 'Dùng cho cảnh ' + n, ic: dg ? 'dongK' : 'hieuUng', f: () => datHieuUng(id, khoa, v)},
      {t: v ? 'Áp cho mọi cảnh' : 'Bỏ hết', ic: 'lop', f: () => datHieuUng(id, khoa, v, true)},
      v && {t: 'Xem mẫu (chưa áp)…', ic: 'play', f: () => xemMauThu(dg ? 'chuyen_dong' : 'hieu_ung', p => { p.canh[x.i][khoa] = v; },
        dg ? {i: x.i, nhan: 'Thử: cảnh ' + n + ' · ' + ten + ' (chưa áp)'} : hu.dau_canh ? {i: Math.max(0, x.i - 1), dau: x.i === 0, nhan: 'Thử: cảnh ' + n + ' · ' + ten + ' (chưa áp)'} : {i: x.i, nhan: 'Thử: cảnh ' + n + ' · ' + ten + ' (chưa áp)'})}]; }
  if (t.dataset.tvkieu) { const m = t.dataset.tvkieu, v = t.dataset.v, d = (S.info.kieu_ds || []).find(y => y.muc === m) || {}, ten = tenGiaTri(m, v), chu = KIEU_CHU.includes(m);
    return [{nhom: (d.ten || m) + ' · ' + ten}, {t: 'Dùng cho cả video', ic: 'lop', chon: (S.plan.kieu || {})[m] === v, f: () => bamKieu(m, v)},
      !chu && {t: 'Xem mẫu (chưa áp)…', ic: 'play', f: () => xemMauThu(m, p => { p.kieu[m] = v; }, {nhan: 'Thử: ' + (d.ten || m) + ' · ' + ten + ' (chưa áp)'})}]; }
  if (t.dataset.tvti) { const ti = tiTim(t.dataset.tvti) || {};
    return [{nhom: 'Tiện ích · ' + (ti.ten || '')}, {t: 'Chạy trên video này', ic: 'play', f: () => chayTuMenu(t.dataset.tvti)}, {t: 'Quản lý tiện ích…', ic: 'caiDat', f: quanLyTi}]; }
  return [];
}
$('#lib').addEventListener('contextmenu', e => {
  const t = e.target.closest('#libPane [data-tvclip], #libPane [data-tvmau], #libPane [data-tvchuyen], #libPane [data-tvdong], #libPane [data-tvhinh], #libPane [data-tvkieu], #libPane [data-tvti], #libPane .tvti');
  if (!t || !S.plan) return;
  e.preventDefault(); e.stopPropagation();
  const b = t.matches('.tvti') ? t.querySelector('[data-tvti]') : t;
  const ds = menuTV(b); if (ds.length) moMenu(e.clientX, e.clientY, ds);
});
