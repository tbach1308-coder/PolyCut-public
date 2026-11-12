/* ============================== BẢNG / HỘP (r25, 5/11) ==============================
   Anh duyệt 5/11 (học OpenReel / FreeCut, sb27/DE-XUAT.md mục 3, 4, 6, 8). Trình bày: dev/_mod-r25-bang.css. Không đụng timeline.
   (3) SOÁT NHANH TRƯỚC KHI XUẤT: khối "Trước khi xuất" trong hộp Xuất video (▾) + tab Bản xuất (cạnh Xuất bản nháp).
       Chỉ đọc dữ liệu app đã tính sẵn (bản xem trước của máy chủ: canh_bao_ct = "N chỗ chữ bị đè" dưới khung xem, gio[k].an / cat,
       matSet() clip mất lúc mở video, S.view.T) -> không tự đoán, không báo nhầm. CHỈ NHẮC: nút Xuất luôn bấm được.
       Mục cần xem có nút "Xem" nhảy tới đúng chỗ (tua vạch đỏ + chọn chữ / cảnh + mở danh sách cảnh báo dưới khung xem).
       Nút ▾ cạnh Xuất video có chấm vàng khi có chỗ nên xem; bấm Xuất video nhanh (không qua hộp) thì thông báo kèm số chỗ.
   (4) BẤM 1 CHỮ -> BẢNG PHẢI CHỈ HIỆN CHỮ ĐÓ (tab Chữ: nhãn, thẻ giá, hook, thẻ kết, tiêu đề; tab Phụ đề: câu phụ đề):
       đầu bảng "Nhãn 2 / 3 · 2,0s" + ‹ › (như thẻ Cảnh), ô chữ, giờ từ → đến (gõ được, ↑ ↓ ±0,1s), Tới vạch đỏ, Xoá, kiểu chữ riêng
       chữ đó (ô #kcBen của dev/_mod-kieu-chu.js, chỉ chữ đang chọn). "‹ Tất cả chữ (N)" = danh sách cũ (giữ tới khi anh bấm chữ khác).
       Ô gõ dùng lại data-f cũ (nhan:k, gia, phu, hook0/1, ket0/1, ket_giay, tieu_de, pd:k) -> sửa / gộp bước Ctrl+Z / tự lưu như cũ.
   (6) BẢNG PHÍM TẮT: phím ? (Shift + /) hoặc nút ⌨ đầu thanh trên. Nhóm Phát / Sửa cảnh / Chữ / Timeline / Khác, ô tìm (gõ không dấu
       cũng được). Danh sách đọc từ window.PHIM_TAT lúc mở bảng. Không đổi phím nào.
       ĐĂNG KÝ PHÍM MỚI (mô-đun khác, không sửa file này, nạp trước hay sau file này đều được):
         (window.PHIM_TAT = window.PHIM_TAT || []).push({id: 'nam-cham', nhom: 'Timeline', phim: ['N'], ten: 'Bật / tắt nam châm (hít mép cảnh)'});
         - nhom: 'Phát' | 'Sửa cảnh' | 'Chữ' | 'Timeline' | 'Khác' (lạ -> Khác); phim: mảng các cách bấm, phím trong 1 cách nối bằng '+'
           ('Ctrl+Alt+C', 'Shift+←', 'Phím cách', 'Ctrl+Lăn chuột'); ghi: chú thích nhỏ (tuỳ chọn); an: true = giấu mục có sẵn.
         - trùng id: mục đăng ký sau thay hẳn mục trước, giữ chỗ cũ (đổi tên / phím của mục có sẵn). id mục có sẵn: xem PT_GOC dưới đây.
         - bài dev/thu-sua-tay/thu_r25_bang.py bấm thử TỪNG phím trong bảng: thêm phím thì thêm 1 bước kiểm vào KIEM_PHIM ở đó.
   (8) BÁO TỰ LƯU: dòng chữ mờ cạnh tên video: "Đang lưu…" (có sửa chưa lưu / đang gửi) · "Đã lưu 15:45" · lưu lỗi: đỏ + Thử lại
       (tự thử lại sau 15 giây) · cửa sổ khác vừa sửa (S.xungDot, băng rôn đỏ): vàng. Bọc luuNhap / sauDoi / moVideo, không đổi cách lưu. */
IC_P.banPhim = '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>';
IC_P.timR25 = '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>';
IC_P.canhBao = '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>';
IC_P.r25Hook = '<path d="M4 6h16M4 11h16M4 16h9"/>';
IC_P.r25Ket = '<path d="M5 21V4h12l-2.5 4L17 12H5"/>';
IC_P.r25Ghim = '<path d="M12 17v5M9 3h6l-1 6 3 3H7l3-3z"/>';
IC_P.r25Loi = '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6M9 9l6 6"/>';
IC_P.r25Tin = '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>';

const R25 = {ds: {chu: false, pd: false}, kVe: null, cuonVe: null, tuHop: false, ban: []};
const r25Go = () => { const ae = document.activeElement || {}; return /TEXTAREA|SELECT/.test(ae.tagName || '') || (ae.tagName === 'INPUT' && !/^(checkbox|radio|button|range)$/.test(ae.type)) || !!ae.isContentEditable; };
const r25Giay = t => String(Math.round((+t || 0) * 10) / 10).replace('.', ',') + ' giây';

/* ============================== (6) BẢNG PHÍM TẮT ============================== */
const PT_NHOM = ['Phát', 'Sửa cảnh', 'Chữ', 'Timeline', 'Khác'];
const PT_GOC = [   // chỉ phím có thật (đã soát _sua-tay.src.html + các _mod-*.js, 5/11); thu_r25_bang.py bấm thử từng mục
  {id: 'phat', nhom: 'Phát', phim: ['Phím cách'], ten: 'Phát / dừng'},
  {id: 'lui-khung', nhom: 'Phát', phim: ['←'], ten: 'Lùi 1 khung hình'},
  {id: 'toi-khung', nhom: 'Phát', phim: ['→'], ten: 'Tới 1 khung hình'},
  {id: 'lui-giay', nhom: 'Phát', phim: ['Shift+←'], ten: 'Lùi 1 giây'},
  {id: 'toi-giay', nhom: 'Phát', phim: ['Shift+→'], ten: 'Tới 1 giây'},
  {id: 'moc-truoc', nhom: 'Phát', phim: ['↑'], ten: 'Về mép cảnh trước'},
  {id: 'moc-sau', nhom: 'Phát', phim: ['↓'], ten: 'Tới mép cảnh sau'},
  {id: 've-dau', nhom: 'Phát', phim: ['Home'], ten: 'Về đầu video'},
  {id: 've-cuoi', nhom: 'Phát', phim: ['End'], ten: 'Tới cuối video'},
  {id: 'chia', nhom: 'Sửa cảnh', phim: ['S', 'Ctrl+B'], ten: 'Chia cảnh ở vạch đỏ', ghi: 'đang chọn khối tiếng tách: chia khối tiếng'},
  {id: 'cat-dau', nhom: 'Sửa cảnh', phim: ['Q'], ten: 'Cắt bỏ phần trước vạch đỏ'},
  {id: 'cat-cuoi', nhom: 'Sửa cảnh', phim: ['W'], ten: 'Cắt bỏ phần sau vạch đỏ'},
  {id: 'nhan-doi', nhom: 'Sửa cảnh', phim: ['Ctrl+D'], ten: 'Nhân đôi cảnh đang chọn'},
  {id: 'xoa', nhom: 'Sửa cảnh', phim: ['Delete', 'Backspace'], ten: 'Xoá cảnh / chữ / mục đang chọn'},
  {id: 'tach-am', nhom: 'Sửa cảnh', phim: ['A'], ten: 'Tách âm thanh cảnh đang chọn ra làn riêng'},
  {id: 'them-nhan', nhom: 'Chữ', phim: ['T'], ten: 'Thêm nhãn chữ ở vạch đỏ'},
  {id: 'the-gia', nhom: 'Chữ', phim: ['G'], ten: 'Thẻ giá ở vạch đỏ', ghi: 'đã có thẻ giá: dời tới vạch đỏ'},
  {id: 'them-pd', nhom: 'Chữ', phim: ['P'], ten: 'Thêm câu phụ đề ở vạch đỏ'},
  {id: 'thoat-o', nhom: 'Chữ', phim: ['Esc'], ten: 'Ra khỏi ô đang gõ (phím tắt chạy lại)'},
  {id: 'phong-to', nhom: 'Timeline', phim: ['Ctrl+='], ten: 'Phóng to timeline'},
  {id: 'thu-nho', nhom: 'Timeline', phim: ['Ctrl+-'], ten: 'Thu nhỏ timeline'},
  {id: 'vua-khung', nhom: 'Timeline', phim: ['Ctrl+0'], ten: 'Vừa khung: cả video gọn trong timeline'},
  {id: 'zoom-chuot', nhom: 'Timeline', phim: ['Ctrl+Lăn chuột'], ten: 'Phóng to / thu nhỏ quanh chỗ chuột'},
  {id: 'cuon', nhom: 'Timeline', phim: ['Lăn chuột'], ten: 'Cuộn timeline sang ngang'},
  {id: 'chon-them', nhom: 'Timeline', phim: ['Ctrl+Bấm', 'Shift+Bấm'], ten: 'Thêm / bớt 1 khối vào nhóm chọn'},
  {id: 'quet', nhom: 'Timeline', phim: ['Kéo chỗ trống'], ten: 'Quét chọn nhiều khối'},
  {id: 'bo-chon', nhom: 'Timeline', phim: ['Esc'], ten: 'Bỏ chọn nhiều'},
  {id: 'hoan-tac', nhom: 'Khác', phim: ['Ctrl+Z'], ten: 'Hoàn tác'},
  {id: 'lam-lai', nhom: 'Khác', phim: ['Ctrl+Y', 'Ctrl+Shift+Z'], ten: 'Làm lại'},
  {id: 'menu', nhom: 'Khác', phim: ['Chuột phải'], ten: 'Menu lệnh đúng chỗ (cảnh, chữ, timeline, khung xem)'},
  {id: 'o-so', nhom: 'Khác', phim: ['↑', '↓'], ten: 'Ô số ở bảng phải: tăng / giảm 1', ghi: 'giữ Shift: 10 · Esc: trả số cũ'},
  {id: 'gui-claude', nhom: 'Khác', phim: ['Ctrl+Enter'], ten: 'Gửi việc cho Claude (ô Nhờ Claude)'},
  {id: 'dong', nhom: 'Khác', phim: ['Esc'], ten: 'Đóng hộp / menu đang mở'},
  {id: 'bang-phim', nhom: 'Khác', phim: ['?'], ten: 'Mở / đóng bảng phím tắt này'}
];
window.PHIM_TAT = window.PHIM_TAT || [];
window.PHIM_TAT.unshift(...PT_GOC);   // mô-đun nạp trước đã đăng ký: mục của nó nằm sau -> thắng khi trùng id
window.dangKyPhim = function () { (window.PHIM_TAT = window.PHIM_TAT || []).push(...arguments); };
function phimTatDs() {   // gộp trùng id (mục sau thay hẳn mục trước, giữ chỗ cũ), bỏ mục an
  const m = new Map();
  (window.PHIM_TAT || []).forEach(x => { if (!x || !x.ten || !x.phim) return; const id = String(x.id || x.ten); m.set(id, Object.assign({}, x, {id})); });
  return [...m.values()].filter(x => !x.an).map(x => Object.assign(x, {phim: [].concat(x.phim).map(String), nhom: PT_NHOM.includes(x.nhom) ? x.nhom : 'Khác'}));
}
window.phimTatDs = phimTatDs;
const ptBo = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();
function ptPhim(ds) {   // ['S', 'Ctrl+B'] -> <kbd>S</kbd> / <kbd>Ctrl</kbd>+<kbd>B</kbd>
  return ds.map(c => `<span class="pt-c">${(c === '+' ? ['+'] : c.split(/\+(?=.)/)).map(k => `<kbd>${esc(k === '-' ? '−' : k)}</kbd>`).join('<i>+</i>')}</span>`).join('<span class="pt-hoac">/</span>');
}
function ptVe(m, q) {
  const tu = ptBo(q).split(/\s+/).filter(Boolean), ds = phimTatDs().filter(x => { const s = ptBo([x.ten, x.ghi || '', x.nhom, ...x.phim].join(' ')); return tu.every(t => s.includes(t)); });
  const el = $('#ptDs', m);
  el.innerHTML = ds.length ? PT_NHOM.map(n => { const h = ds.filter(x => x.nhom === n); return h.length ? `<section class="pt-nhom"><h4>${n}</h4>${h.map(x =>
    `<div class="pt-h" data-pt="${esc(x.id)}"><span class="pt-ten">${esc(x.ten)}${x.ghi ? `<small>${esc(x.ghi)}</small>` : ''}</span><span class="pt-k">${ptPhim(x.phim)}</span></div>`).join('')}</section>` : ''; }).join('')
    : `<p class="pt-trong">Không thấy phím nào khớp “${esc(q)}”.</p>`;
  $('#ptDem', m).textContent = q.trim() ? ds.length + ' phím khớp' : ds.length + ' phím tắt';
}
function moPhimTat() {
  const cu = $('.mbg .r25-pt'); if (cu) { cu.querySelector('[data-dong]').click(); return; }
  if ($('.mbg')) return;
  dongMenu && dongMenu();
  const {m} = modal(`<h3>Phím tắt</h3>
    <div class="pt-dau"><label class="pt-tim">${icon('timR25')}<input class="inp" id="ptTim" type="search" placeholder="Tìm phím hoặc việc: chia, xoá, Ctrl…" autocomplete="off" spellcheck="false" aria-label="Tìm phím tắt"></label><span class="pt-dem" id="ptDem"></span></div>
    <div class="pt-ds" id="ptDs"></div>
    <p class="pt-cuoi">Phím tắt không chạy khi đang gõ trong ô chữ: bấm Esc để ra khỏi ô. Bấm <kbd>?</kbd> để mở / đóng bảng này.</p>`);
  m.classList.add('r25-pt'); m.setAttribute('aria-label', 'Bảng phím tắt');
  const o = $('#ptTim', m);
  ptVe(m, ''); o.addEventListener('input', () => ptVe(m, o.value));
  o.addEventListener('keydown', e => { if (e.key === 'Escape' && o.value) { e.preventDefault(); e.stopPropagation(); o.value = ''; ptVe(m, ''); } });
  setTimeout(() => o.focus(), 20);
}
document.addEventListener('keydown', e => {
  const hoi = e.key === '?' || (e.code === 'Slash' && e.shiftKey);
  if (!hoi || e.ctrlKey || e.altKey || e.metaKey || e.repeat || r25Go()) return;
  if ($('#edit').hidden) return;
  if ($('.mbg') && !$('.mbg .r25-pt')) return;   // hộp khác đang mở
  e.preventDefault(); e.stopPropagation(); moPhimTat();
});
$('#edBtns').insertAdjacentHTML('afterbegin', `<button type="button" class="btn icon ghost" id="bPhim" aria-label="Bảng phím tắt (?)" data-tip="Bảng phím tắt" data-phim="?">${icon('banPhim')}</button>`);
$('#bPhim').addEventListener('click', () => moPhimTat());

/* ============================== (8) BÁO TỰ LƯU ============================== */
const LUU = {dang: false, luc: 0, hen: 0};
$('#bVd').insertAdjacentHTML('afterend', '<span class="luu-tt" id="luuTt" role="status" aria-live="polite" hidden></span>');   // lúc nạp trang: POLY Cut (khung ngoài) theo dõi cỡ các mục thanh đầu
function gioLuu(ms) { const d = new Date(ms), p = n => String(n).padStart(2, '0'), h = p(d.getHours()) + ':' + p(d.getMinutes());
  return d.toDateString() === new Date().toDateString() ? h : h + ' · ' + d.getDate() + '/' + (d.getMonth() + 1); }
function veLuu() {
  const el = $('#luuTt'); if (!el) return;
  if (!S.plan || $('#edit').hidden) { el.hidden = true; return; }
  let cls = '', txt = '', tip = '', nut = '';
  if (S.xungDot) { cls = 'xd'; txt = 'Chưa lưu · cửa sổ khác vừa sửa'; tip = 'Video này vừa được sửa ở cửa sổ khác (mở 2 lần?). Phần sửa ở đây chưa tự lưu để khỏi đè bên kia: chọn ở băng báo đỏ phía dưới (tải bản mới hoặc giữ bản ở đây)'; }
  else if (S.loiLuu) { cls = 'loi'; txt = 'Chưa lưu được'; tip = 'Tự lưu bị lỗi: ' + S.loiLuu + '. App tự thử lại sau ít giây (hoặc bấm Thử lại). Đừng tắt app tới khi thấy "Đã lưu"'; nut = '<button type="button" class="luu-lai" data-luu-lai>Thử lại</button>'; }
  else if (LUU.dang || (S.banSua || 0) !== (S.banLuu || 0)) { cls = 'dang'; txt = 'Đang lưu…'; tip = 'Đang tự lưu bản sửa dở'; }
  else { const ms = LUU.luc || (S.info && S.info.dang_sua && S.info.nhap_luc ? S.info.nhap_luc * 1000 : 0);
    if (ms) { txt = 'Đã lưu ' + gioLuu(ms); tip = 'Bản sửa dở tự lưu lúc ' + gioLuu(ms) + ': tắt app, mở lại vẫn còn. Bấm Xuất video để thành phiên bản mới'; } }
  el.hidden = !txt; el.className = 'luu-tt' + (cls ? ' ' + cls : '');
  if (tip) el.dataset.tip = tip; else delete el.dataset.tip;
  const h = `<span class="luu-t">${esc(txt)}</span>${nut}`; if (el.innerHTML !== h) el.innerHTML = h;
}
window.veLuu = veLuu;
const r25LuuGoc = luuNhap;
luuNhap = async function (ep) {
  const co = !!S.plan && !(S.xungDot && !ep), moc0 = S.moc;
  if (co) { LUU.dang = true; clearTimeout(LUU.hen); veLuu(); }
  try { return await r25LuuGoc.apply(this, arguments); }
  finally {
    if (co) {
      LUU.dang = false;
      if (!S.loiLuu && !S.xungDot && S.moc !== moc0) LUU.luc = Date.now();
      if (S.loiLuu && !S.xungDot) { clearTimeout(LUU.hen); LUU.hen = setTimeout(() => { if (S.loiLuu && S.plan && !S.xungDot) luuNhap(); }, 15000); }   // lỗi: tự thử lại
      veLuu();
    }
  }
};
const r25SauDoiGoc = sauDoi;
sauDoi = function () { const r = r25SauDoiGoc.apply(this, arguments); try { veLuu(); } catch (e) {} return r; };
const r25MoVideoGoc = moVideo;
moVideo = async function () {
  LUU.luc = 0; LUU.dang = false; clearTimeout(LUU.hen); R25.ds.chu = R25.ds.pd = false;
  const r = await r25MoVideoGoc.apply(this, arguments);
  try { veLuu(); r25Cham(); } catch (e) {}
  return r;
};
document.addEventListener('click', e => { if (e.target.closest && e.target.closest('#luuTt [data-luu-lai]')) { clearTimeout(S.nhapHen); luuNhap(); } });

/* ============================== (4) BẤM 1 CHỮ -> BẢNG PHẢI CHỈ HIỆN CHỮ ĐÓ ============================== */
const R25_TEN = {hook: 'Hook', nhan: 'Nhãn', gia: 'Thẻ giá', ket: 'Thẻ kết', tieu_de: 'Tiêu đề ghim', pd: 'Câu'};
const R25_IC = {hook: 'r25Hook', nhan: 'nhan', gia: 'gia', ket: 'r25Ket', tieu_de: 'r25Ghim', pd: 'pd'};
const R25_CUA = {hook: 'hook', nhan: 'nhãn này', gia: 'thẻ giá này', tieu_de: 'tiêu đề'};
function r25Loai(k) {
  if (!k || !S.plan) return null;
  if (k === 'hook' || k === 'ket' || k === 'tieu_de') return k;
  const chu = S.plan.chu || {};
  if (chu.the_gia && chu.the_gia._k === k) return 'gia';
  if ((chu.nhan_chu || []).some(n => n._k === k)) return 'nhan';
  if ((S.plan.phu_de || []).some(p => p._k === k)) return 'pd';
  return null;
}
const r25Nhom = () => { const q = S.quet; return !!(q && q.canh && q.k && q.canh.size + q.k.size >= 2); };
function r25Mot(tab) {   // bảng 1 chữ của tab này? -> loại chữ đang chọn | null (= danh sách cũ)
  if (!S.plan || S.selLoai !== 'chu' || R25.ds[tab] || r25Nhom()) return null;
  const l = r25Loai(S.sel.k); if (!l) return null;
  return (tab === 'pd') === (l === 'pd') ? l : null;
}
function r25Gio(k, l) {   // giờ trên video theo bản xem trước: {t0, t1} | {an, ly} | {}
  const v = S.view || {};
  if (l === 'hook') return v.hook_t && ((S.plan.chu || {}).hook || []).some(x => String(x || '').trim()) ? {t0: v.hook_t[0], t1: v.hook_t[1]} : {};
  if (l === 'ket') return v.ket_t ? {t0: v.ket_t[0], t1: v.ket_t[1]} : {};
  if (l === 'tieu_de') return String((S.plan.chu || {}).tieu_de || '').trim() && v.T ? {t0: v.hook_t ? v.hook_t[1] : 0, t1: v.T} : {};
  const g = (v.gio || {})[k];
  if (!g) return {};
  return g.an ? {an: true, ly: g.ly_do || ''} : {t0: g.t0, t1: g.t1, cat: !!g.cat, lyCat: g.ly_do_cat || ''};
}
function r25GioO(k, l) {   // giờ đặt vào 2 ô từ / đến: theo bản xem, chữ đang ẩn thì theo kế hoạch
  const g = r25Gio(k, l); if (g.t0 != null) return g;
  const it = timIt(k) || {}, a = +it.t0 || 0; return {t0: a, t1: +it.t1 > a ? +it.t1 : a + 2};
}
function r25Ds(tab) {   // chữ của tab theo giờ: [{k, l, co}] (co = đang có trong video; chữ đang chọn luôn có mặt để ‹ › biết chỗ)
  const v = S.view || {}, chu = S.plan.chu || {}, ds = [];
  const them = (k, l, co) => { if (!co && S.sel.k !== k) return; const g = r25Gio(k, l), it = l === 'nhan' || l === 'gia' || l === 'pd' ? timIt(k) || {} : {};
    ds.push({k, l, co, t: g.t0 != null ? g.t0 : it.t0 != null ? +it.t0 : 1e9, i: ds.length}); };
  if (tab === 'pd') (S.plan.phu_de || []).forEach(p => them(p._k, 'pd', true));
  else {
    them('hook', 'hook', (chu.hook || []).some(x => String(x || '').trim()));
    (chu.nhan_chu || []).forEach(n => them(n._k, 'nhan', true));
    if (chu.the_gia) them(chu.the_gia._k, 'gia', true);
    them('tieu_de', 'tieu_de', !!String(chu.tieu_de || '').trim());
    them('ket', 'ket', v.ket_t ? true : S.view ? false : chu.ket !== null);
  }
  return ds.sort((a, b) => a.t - b.t || a.i - b.i);
}
function r25TenNgan(k, l) {
  const it = timIt(k) || {}, cat = s => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > 22 ? s.slice(0, 21) + '…' : s; };
  if (l === 'nhan') return 'Nhãn “' + cat(it.chu) + '”';
  if (l === 'gia') return 'Thẻ giá' + (it.gia ? ' “' + cat(it.gia) + '”' : '');
  if (l === 'pd') return 'Câu “' + cat(it.chu) + '”';
  return R25_TEN[l];
}
function r25KieuHtml(k, l) {   // ô #kcBen chỉ cho chữ đang chọn (không có hàng chip chọn chữ khác)
  const ten = R25_CUA[l];
  const dau = x => `<div class="box tt-box kc-ben r25-kc" id="kcBen"><div class="row"><h2 class="sec grow">Kiểu chữ của ${ten}</h2>${x || ''}</div>`;
  if (!KC.bang) { if (!KC.dang && !KC.loi) setTimeout(kcTai, 0); return dau() + `<p class="note giu${KC.loi ? ' err' : ''}">${esc(KC.loi || 'Đang tải kiểu chữ…')}</p></div>`; }
  const cu = kcLay(S.plan, k), coMau = cu && Object.keys(cu).some(x => x !== 'font'), co = +((cu || {}).co) || 1;
  return dau(cu ? `<button type="button" class="btn small ghost" data-kcbo="${esc(k)}" data-tip="Bỏ mẫu + font riêng: ${esc(R25_TEN[l].toLowerCase())} theo kiểu chữ cả video">${icon('boHet')}Bỏ kiểu riêng</button>` : '')
    + (kcLoai(k) ? kcLuoi(k, true) + `<div class="lbl">Font</div>` + kcFonts(k)
      + `<div class="r25-kc-h">${coMau ? `<span class="lbl">Cỡ</span><button type="button" class="btn small icon" data-kcco="-0.1" data-tip="Nhỏ hơn" ${co <= 0.7 ? 'disabled' : ''}>−</button><b class="kc-co">${Math.round(co * 100)}%</b><button type="button" class="btn small icon" data-kcco="0.1" data-tip="To hơn" ${co >= 1.4 ? 'disabled' : ''}>+</button>`
        : `<span class="r25-ghi">${cu ? 'Chỉ đổi font, giữ kiểu chữ của video.' : 'Đang theo kiểu chữ cả video: bấm 1 mẫu để đổi riêng ' + ten + '.'}</span>`}</div>`
      : `<p class="note giu">Gõ chữ trước rồi chọn mẫu chữ.</p>`) + '</div>';
}
const r25KcGoc = kcBen;
kcBen = function () { const l = r25Mot('chu'); return l && R25_CUA[l] ? r25KieuHtml(S.sel.k, l) : r25KcGoc.apply(this, arguments); };
function r25GioHtml(k, l) {   // nhãn / thẻ giá / câu: 2 ô giờ + Tới vạch đỏ + Xoá
  const o = r25GioO(k, l), g = r25Gio(k, l), ten = R25_TEN[l].toLowerCase();
  const why = g.an ? `<p class="note giu r25-why">${icon('canhBao')}<span>${esc(g.ly || 'Đang ẩn')}: sửa giờ hoặc bấm Tới vạch đỏ để hiện lại</span></p>`
    : g.cat ? `<p class="note giu r25-why">${icon('canhBao')}<span>${esc(g.lyCat || 'Bị cắt bớt theo cảnh')}</span></p>` : '';
  return `<div class="lbl r25-lbl">Hiện từ … đến</div>
    <div class="r25-gio-h"><input class="inp r25-gio" data-r25-gio="t0" data-k="${esc(k)}" value="${tg(o.t0)}" inputmode="decimal" autocomplete="off" spellcheck="false" aria-label="Hiện từ (giờ trên video)">
      <span class="r25-mui" aria-hidden="true">→</span><input class="inp r25-gio" data-r25-gio="t1" data-k="${esc(k)}" value="${tg(o.t1)}" inputmode="decimal" autocomplete="off" spellcheck="false" aria-label="Hiện đến (giờ trên video)">
      <button type="button" class="btn small r25-toi" data-r25="toi-vach" data-tip="Dời ${esc(ten)} tới vạch đỏ, giữ độ dài">${icon('catCuoi')}<span>Tới vạch đỏ</span></button>
      <span class="sp"></span><button type="button" class="btn small icon danger r25-xoa" data-r25="xoa" aria-label="Xoá ${esc(ten)}" data-tip="Xoá ${esc(ten)}" data-phim="Delete">${icon('xoa')}</button></div>${why}
    <p class="note">Giờ trên video: gõ 0:02,5 hoặc 2,5 rồi Enter (↑ ↓ ±0,1 giây, giữ Shift ±1 giây). Đổi “từ” thì giữ “đến”.</p>`;
}
function r25CoDinh(l, chu) {   // hook / thẻ kết / tiêu đề: giờ cố định + nút bỏ
  const g = r25Gio(null, l), bo = {hook: 'Bỏ hook', ket: 'Bỏ thẻ kết', tieu_de: 'Bỏ tiêu đề'}[l];
  return `<div class="r25-gio-h r25-cd"><span class="r25-gio-tx">${g.t0 != null ? tg(g.t0) + ' → ' + tg(g.t1) : '—'}</span><span class="r25-ghi">${{hook: 'cố định đầu video', ket: 'cố định cuối video', tieu_de: 'từ sau hook tới hết video'}[l]}</span>${chu || ''}
    <span class="sp"></span><button type="button" class="btn small danger r25-bo" data-r25="xoa" data-tip="${bo} (Ctrl+Z để lấy lại)">${icon('xoa')}<span>${bo}</span></button></div>`;
}
function r25BenMot(l) {
  const k = S.sel.k, tab = l === 'pd' ? 'pd' : 'chu', chu = S.plan.chu || {};
  const ds = r25Ds(tab), i = ds.findIndex(x => x.k === k), cung = ds.filter(x => x.l === l), j = cung.findIndex(x => x.k === k);
  const g = r25Gio(k, l), n = ds.filter(x => x.co).length, truoc = i > 0 ? ds[i - 1] : null, sau = i >= 0 ? ds[i + 1] : null, loai = tab === 'pd' ? 'câu' : 'chữ';
  let h = `<button type="button" class="r25-ve" data-r25="tat-ca" data-tip="Về danh sách mọi ${tab === 'pd' ? 'câu phụ đề' : 'chữ'} của video">${icon('trai')}<span>Tất cả ${loai} (${n})</span></button>`;
  const so = cung.length > 1 && j >= 0, dai = g.t0 != null && g.t1 != null ? `<span class="tt-dai">${gs(g.t1 - g.t0)}</span>` : '';
  let phu;
  if (g.an) phu = `<span class="r25-an">Đang ẩn</span> · ${esc(g.ly)}`;
  else if (l === 'hook' || l === 'ket' || l === 'tieu_de') phu = (g.t0 != null ? tg(g.t0) + '–' + tg(g.t1) + ' · ' : '') + {hook: 'đầu video', ket: 'cuối video', tieu_de: 'ghim trên cùng'}[l];
  else { const x = g.t0 != null ? canhLuc(g.t0 + 0.01) : null; phu = `<span data-gio="${esc(k)}">${gioTxt(k)}</span>${x ? ' · nằm trên cảnh ' + (x.i + 1) : ''}`; }
  const nut = (x, d) => `<button type="button" class="btn small icon" data-r25-nav="${d}" ${x ? '' : 'disabled'} aria-label="${d < 0 ? 'Chữ trước' : 'Chữ sau'}" data-tip="${x ? esc((d < 0 ? 'Trước: ' : 'Sau: ') + r25TenNgan(x.k, x.l)) : d < 0 ? 'Đang là ' + loai + ' đầu' : 'Đang là ' + loai + ' cuối'}">${icon(d < 0 ? 'trai' : 'phai')}</button>`;
  h += `<div class="tt-dau r25-dau"><span class="r25-o" aria-hidden="true">${icon(R25_IC[l])}</span>
    <div class="tt-ten"><b>${R25_TEN[l]}${so ? ' ' + (j + 1) + `<span class="count"> / ${cung.length}</span>` : ''}${dai}</b><small>${phu}</small></div>
    ${ds.length > 1 ? `<span class="tt-nav">${nut(truoc, -1)}${nut(sau, 1)}</span>` : ''}</div>`;
  const nhom = (tieu, ben, cls = '') => `<div class="box tt-box r25-g${cls}"><div class="row"><h2 class="sec grow">${tieu}</h2></div>${ben}</div>`;
  if (l === 'nhan') { const it = timIt(k);
    h += nhom('Chữ', `<div class="it r25-it" data-row="${esc(k)}"><span class="inpw"><input class="inp" data-f="nhan:${esc(k)}" value="${esc(it.chu || '')}" maxlength="24" aria-label="Chữ của nhãn">${dem(it.chu, 18, 'nhan:' + k)}</span></div>
      <p class="note">Nhãn = chữ vàng to giữa khung (tên máy, Mẹo 1, pin 98%…), nên ≤ 18 ký tự.</p>${r25GioHtml(k, l)}`); }
  else if (l === 'gia') { const it = chu.the_gia;
    h += nhom('Giá', `<div class="two"><div><div class="lbl">Giá</div><input class="inp" data-f="gia" value="${esc(it.gia || '')}" placeholder="13tr9" aria-label="Giá"></div><div><div class="lbl">Dòng phụ</div><input class="inp" data-f="phu" value="${esc(it.phu || '')}" placeholder="Pin 98% · BH 6 tháng" aria-label="Dòng phụ"></div></div>
      <p class="note">Chỉ ghi giá thật trong kho.</p>${r25GioHtml(k, l)}`); }
  else if (l === 'pd') { const it = timIt(k);
    h += nhom('Câu phụ đề', `<div class="it r25-it" data-row="${esc(k)}"><textarea class="inp" rows="2" data-f="pd:${esc(k)}" aria-label="Chữ của câu phụ đề">${esc(it.chu || '')}</textarea></div>
      <p class="note">Sửa chữ nghe sai ngay trong ô (phụ đề luôn in hoa khi dựng).</p>${r25GioHtml(k, l)}`);
    h += `<p class="r25-ghi-kieu">${icon('thongTin')}<span>Phụ đề theo kiểu chữ cả video</span><button type="button" class="lnk" data-r25="tab-kieu">Đổi ở tab Kiểu</button></p>`; }
  else if (l === 'hook') { const hk = chu.hook || [], vt = (S.plan.kieu || {}).vi_tri_chu || 'tren';
    h += nhom('Hook (2 dòng đầu video)', `<div class="lbl">Dòng 1 ${dem(hk[0], 20)}</div><input class="inp" data-f="hook0" value="${esc(hk[0] || '')}" placeholder="Vd: iPad Pro M1 12.9" aria-label="Hook dòng 1">
      <div class="lbl">Dòng 2, chữ vàng ${dem(hk[1], 22)}</div><input class="inp" data-f="hook1" value="${esc(hk[1] || '')}" placeholder="Vd: giá chỉ 13tr9?" aria-label="Hook dòng 2">
      <div class="r25-vt"><span class="lbl">Vị trí</span><span class="radio" data-r="vi_tri_chu">${[['tren', 'Trên'], ['giua_tren', 'Giữa trên'], ['giua', 'Giữa']].map(([v, t]) => `<button type="button" data-v="${v}" class="${vt === v ? 'on' : ''}">${t}</button>`).join('')}</span></div>
      <p class="note">Để trống cả 2 dòng = không có hook.</p><div class="lbl r25-lbl">Hiện lúc</div>${r25CoDinh('hook')}`); }
  else if (l === 'ket') { const k2 = S.plan.kieu || {}, kmd = S.info.ket_mac_dinh || {}, ketMode = !('ket' in chu) ? 'md' : chu.ket ? 'tv' : 'khong';
    const md = (k2.ket === 'the_comment' ? kmd.the_comment : kmd.dia_chi) || [], ket = chu.ket || md;
    h += nhom('Thẻ kết', `<span class="radio" data-r="ketmode">${[['md', 'Câu mặc định'], ['tv', 'Tự viết'], ['khong', 'Không có thẻ kết']].map(([v, t]) => `<button type="button" data-v="${v}" class="${ketMode === v ? 'on' : ''}">${t}</button>`).join('')}</span>
      ${ketMode === 'tv' ? `<input class="inp" data-f="ket0" value="${esc(ket[0] || '')}" aria-label="Thẻ kết dòng 1"><input class="inp" data-f="ket1" value="${esc(ket[1] || '')}" aria-label="Thẻ kết dòng 2">` : ketMode === 'md' ? `<p class="note giu">${esc(md.join(' / '))}</p>` : ''}
      ${ketMode !== 'khong' ? `<div class="lbl r25-lbl">Hiện cuối video</div>${r25CoDinh('ket', `<span class="r25-kg"><input class="inp num" type="number" step="0.5" min="1.5" max="6" data-f="ket_giay" value="${S.plan.ket_giay || 3.6}" aria-label="Số giây thẻ kết hiện"><span class="r25-ghi">giây</span></span>`)}` : ''}`);
    h += `<p class="r25-ghi-kieu">${icon('thongTin')}<span>Thẻ kết theo kiểu cả video</span><button type="button" class="lnk" data-r25="tab-kieu">Đổi ở tab Kiểu</button></p>`; }
  else if (l === 'tieu_de') {
    h += nhom('Tiêu đề ghim', `<input class="inp" data-f="tieu_de" value="${esc(chu.tieu_de || '')}" maxlength="30" placeholder="Vd: 3 mẹo dùng iPad" aria-label="Tiêu đề ghim">
      <p class="note">Tiêu đề ghim trên cùng cho video mẹo nhiều bước. Để trống = không có.</p>${r25CoDinh('tieu_de')}`); }
  if (R25_CUA[l]) h += kcBen();
  return h;
}
const r25BenChuGoc = benChu;
benChu = function () { const l = r25Mot('chu'); return l ? r25BenMot(l) : r25BenChuGoc.apply(this, arguments); };
const r25BenPdGoc = benPd;
benPd = function () { const l = r25Mot('pd'); return l ? r25BenMot(l) : r25BenPdGoc.apply(this, arguments); };
const r25VeBenGoc = veBen;
veBen = function () {
  const r = r25VeBenGoc.apply(this, arguments);
  try {
    const p = $('#pane'), mot = p && p.querySelector(':scope > .r25-dau') ? S.sel.k : null;
    if (mot && mot !== R25.kVe) p.scrollTop = 0;   // sang chữ khác: lên đầu bảng
    if (!mot && R25.cuonVe) { const row = p.querySelector(`.it[data-row="${CSS.escape(R25.cuonVe)}"]`); if (row) row.scrollIntoView({block: 'center'}); }
    R25.kVe = mot; R25.cuonVe = null;
  } catch (e) {}
  return r;
};
/* chọn 1 chữ (bấm thanh chữ, menu chuột phải, Sửa chữ, thêm chữ, chip Kiểu chữ, dòng cảnh báo, quét trúng 1 chữ) = mở bảng 1 chữ */
function r25MoMot() { R25.ds.chu = R25.ds.pd = false; }
const r25ChonGoc = chonChuMenu; chonChuMenu = function () { r25MoMot(); return r25ChonGoc.apply(this, arguments); };
const r25ONhapGoc = oNhap; oNhap = function () { r25MoMot(); return r25ONhapGoc.apply(this, arguments); };
const r25KcChonGoc = kcChon; kcChon = function () { r25MoMot(); return r25KcChonGoc.apply(this, arguments); };
document.addEventListener('click', e => { if (e.target.closest && e.target.closest('#tChu .bar[data-k], #tPd .bar[data-k], #cb .cbi')) r25MoMot(); }, true);
function r25Toi(k) {   // chọn chữ k (bảng 1 chữ), vạch đỏ tới đầu chữ đó
  const l = r25Loai(k); if (!l) return;
  r25MoMot(); S.sel.k = k; S.selLoai = 'chu';
  const tab = l === 'pd' ? 'pd' : 'chu'; if (S.tab !== tab) { S.tab = tab; veTabs(); }
  const g = r25Gio(k, l); if (g.t0 != null) { dung(); tua(g.t0 + (l === 'tieu_de' ? 0.3 : 0.05)); giuVach(); }
  veTimeline(); veBen(true);
}
window.r25Toi = r25Toi;
function r25DocGio(s) {   // "0:02,5" | "2,5" | "2.5s" | "1:05" -> giây (null = không hiểu)
  s = String(s || '').trim().replace(/,/g, '.').replace(/\s+/g, '').replace(/(giây|s)$/i, '');
  let m = s.match(/^(\d+):(\d+(?:\.\d+)?)$/); if (m) return +m[1] * 60 + +m[2];
  return /^\d+(?:\.\d+)?$/.test(s) ? +s : null;
}
function r25DatGio(k, a, b, key) {   // đặt giờ trên video (như ⇥ Vạch đỏ: bỏ neo cảnh, máy chủ neo lại)
  const T = (S.view || {}).T || tongT();
  a = clamp(a, 0, Math.max(0, T - 0.3)); b = clamp(b, a + 0.3, Math.max(a + 0.3, T));
  doi(() => { const it = timIt(k); if (!it) return; delete it._neo; delete it.tu; delete it._tu_goc; delete it.canh; it.t0 = r3(a); it.t1 = r3(b); S.sel.k = k; }, key);
  const gio = (S.view || {}).gio; if (gio) gio[k] = {t0: r3(a), t1: r3(b)};   // bảng / làn chữ thấy ngay, bản xem mới của máy chủ sẽ ghi đè
  return [a, b];
}
function r25GhiGio(o, giu) {
  const k = o.dataset.k, l = r25Loai(k); if (!['nhan', 'gia', 'pd'].includes(l)) return;
  const f = o.dataset.r25Gio, cu = r25GioO(k, l), v = r25DocGio(o.value);
  if (v == null) { o.value = tg(cu[f]); return toast('Gõ giờ trên video kiểu 0:02,5 hoặc 2,5', true); }
  let a = cu.t0, b = cu.t1;
  if (f === 't0') { a = v; if (b - a < 0.3) b = a + (cu.t1 - cu.t0); }
  else { if (v - a < 0.3) { o.value = tg(cu.t1); return toast('Giờ "đến" phải sau giờ "từ" ít nhất 0,3 giây', true); } b = v; }
  if (Math.abs(a - cu.t0) < 0.0005 && Math.abs(b - cu.t1) < 0.0005 && !r25Gio(k, l).an) { o.value = tg(cu[f]); return; }
  const [x, y] = r25DatGio(k, a, b, giu ? 'r25gio:' + k + ':' + f : undefined);
  if (giu) { o.value = tg(f === 't0' ? x : y); const kia = $(`#pane input[data-r25-gio="${f === 't0' ? 't1' : 't0'}"]`); if (kia) kia.value = tg(f === 't0' ? y : x); }
}
$('#pane').addEventListener('change', e => {   // Enter / rời ô: áp; đang Tab sang ô giờ kia thì bảng vẽ lại xong vẫn đứng ở ô đó
  const o = e.target.closest && e.target.closest('input[data-r25-gio]'); if (!o) return;
  setTimeout(() => {
    const f = (document.activeElement && document.activeElement.dataset || {}).r25Gio;
    r25GhiGio(o);
    if (f) { const x = $(`#pane input[data-r25-gio="${f}"]`); if (x && x !== document.activeElement) { x.focus(); x.select(); } }
  }, 0);
});
$('#pane').addEventListener('keydown', e => {
  const o = e.target.closest && e.target.closest('input[data-r25-gio]'); if (!o) return;
  if (e.key === 'Enter') { e.preventDefault(); o.blur(); return; }
  if (e.key === 'Escape') { o.value = o.dataset.v0 != null ? o.dataset.v0 : o.value; return; }   // trang tự rời ô; số cũ -> không đổi gì
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault(); e.stopPropagation();
    const v = r25DocGio(o.value); if (v == null) return;
    o.value = tg(Math.max(0, v + (e.key === 'ArrowUp' ? 1 : -1) * (e.shiftKey ? 1 : 0.1))); r25GhiGio(o, true);
  }
});
const r25XoaHkGoc = xoaHookKet;   // bỏ hook / thẻ kết (nút, phím Delete): S.sel.k về null SAU lần vẽ của doi() -> vẽ lại cho về danh sách
xoaHookKet = function () { const r = r25XoaHkGoc.apply(this, arguments); try { if (!S.sel.k && $('#pane > .r25-dau')) veBen(true); } catch (e) {} return r; };
function r25Xoa(k, l) {
  if (l === 'hook' || l === 'ket') return xoaHookKet(l);
  if (l === 'tieu_de') { if (!String((S.plan.chu || {}).tieu_de || '').trim()) { S.sel.k = null; return veBen(true); } doi(p => { delete p.chu.tieu_de; }); S.sel.k = null; veBen(true); return toast('Đã bỏ tiêu đề ghim (Ctrl+Z để lấy lại)'); }
  xoaChu(k); veBen(true);
}
$('#pane').addEventListener('click', e => {
  const b = e.target.closest('[data-r25], [data-r25-nav]'); if (!b || b.disabled || !S.plan) return;
  const k = S.sel.k, l = r25Loai(k), a = b.dataset.r25;
  if (b.dataset.r25Nav) { const ds = r25Ds(l === 'pd' ? 'pd' : 'chu'), i = ds.findIndex(x => x.k === k), x = ds[i + +b.dataset.r25Nav]; if (x) r25Toi(x.k); return; }
  if (a === 'tat-ca') { R25.ds[l === 'pd' ? 'pd' : 'chu'] = true; R25.cuonVe = k; return veBen(true); }
  if (a === 'tab-kieu') { S.tab = 'kieu'; veTabs(); return veBen(true); }
  if (!l) return;
  if (a === 'toi-vach') { if (!['nhan', 'gia', 'pd'].includes(l)) return; const o = r25GioO(k, l), d = Math.max(0.6, o.t1 - o.t0); r25DatGio(k, S.t, S.t + d); return; }
  if (a === 'xoa') return r25Xoa(k, l);
});

/* ============================== (3) SOÁT NHANH TRƯỚC KHI XUẤT ============================== */
function r25LoaiCb(s) {   // 1 cảnh báo của bản xem trước -> nhóm dòng soát
  s = String(s || '');
  if (/bị thẻ kết che/.test(s)) return 'ket';
  if (/cắt giữa lúc đang nói/.test(s)) return 'noi';
  if (/giọng đọc AI/.test(s)) return 'giong';
  return 'chu';
}
function r25KieuChu(s) {
  if (/đè lên/.test(s)) return 'chữ chồng chữ';
  if (/TikTok/.test(s)) return 'nút / chữ TikTok che';
  if (/sát mép/.test(s)) return 'sát mép khung';
  if (/thu nhỏ/.test(s)) return 'chữ dài bị thu nhỏ';
  if (/không hiện/.test(s)) return 'chữ không hiện';
  if (/^Thẻ kết/.test(s)) return 'thẻ kết hiện ngắn / dài quá';
  return 'chữ cần xem';
}
function r25XemCb(x) {   // như bấm 1 dòng cảnh báo dưới khung xem + mở danh sách cảnh báo
  const g = x.k && ((S.view || {}).gio || {})[x.k], t = x.t != null ? x.t : g && !g.an ? g.t0 : null;
  dung(); if (t != null) { tua(t + 0.05); giuVach(); }
  S.cbMo = true; if (S.view) veCB(S.view);
  if (x.k && r25Loai(x.k)) { r25MoMot(); S.sel.k = x.k; S.selLoai = 'chu'; S.tab = r25Loai(x.k) === 'pd' ? 'pd' : 'chu'; veTabs(); veBen(true); }
  veTimeline();
}
function r25XemCanh(id, cuoi) {
  const x = bocCanh().find(y => y.c._id === id); if (!x) return;
  S.sel.canh = id; S.selLoai = 'canh'; if (S.tab !== 'canh') { S.tab = 'canh'; veTabs(); }
  dung(); tua(cuoi ? Math.max(x.bd, x.b - 0.3) : x.bd + 0.02); giuVach(); veBen(true); veTimeline();
}
function r25TachCb(s) {   // "Câu “a” đè lên câu “b” lúc 0:19,8–0:20,5: dời giờ một bên (nút ⇥…)" -> ["Câu “a” đè lên câu “b” lúc 0:19,8–0:20,5", "dời giờ một bên (nút ⇥…)"]
  s = String(s || ''); const i = s.lastIndexOf(': ');
  if (i < 0) return [s, ''];
  return [s.slice(0, i), s.slice(i + 2)];
}
function r25SoatDs() {   // -> {dang, ds: [{muc: 'loi'|'nhac'|'tin'|'ok', con (dòng con), ten (HTML), ct, nut, xem}]}
  const ds = []; if (!S.plan) return {dang: false, ds};
  const canh = S.plan.canh || [];
  if (!canh.length) { ds.push({muc: 'loi', ten: 'Video chưa có cảnh nào', ct: 'thêm clip trước, máy không xuất video trống'}); return {dang: false, ds}; }
  if (!S.view || !(typeof window.ranh === 'function' && window.ranh())) return {dang: true, ds};
  const v = S.view, gio = v.gio || {}, chu = S.plan.chu || {};
  const ct = v.canh_bao_ct || (v.canh_bao || []).map(x => ({chu: x}));
  const nh = {chu: [], ket: [], noi: [], giong: []}; ct.forEach(x => nh[r25LoaiCb(x.chu)].push(x));
  if (nh.chu.length) { const kieu = [...new Set(nh.chu.map(x => r25KieuChu(x.chu)))];
    ds.push({muc: 'nhac', ten: `<b>${nh.chu.length} chỗ chữ bị đè / bị che</b>`, ct: '(' + kieu.join(', ') + ')', xem: () => r25XemCb(nh.chu[0])});
    // r29 (soi N9): liệt kê từng chỗ (chữ nào, lúc nào, nút Xem riêng) thay vì chỉ 1 dòng tổng
    const TOI_DA = 8;
    nh.chu.slice(0, TOI_DA).forEach(x => { const [ten, goi] = r25TachCb(x.chu); ds.push({muc: 'nhac', con: true, ten: esc(ten), ct: goi, xem: () => r25XemCb(x)}); });
    if (nh.chu.length > TOI_DA) ds.push({muc: 'nhac', con: true, ten: '… còn ' + (nh.chu.length - TOI_DA) + ' chỗ nữa', ct: 'xem hết ở cảnh báo dưới khung xem', xem: () => r25XemCb(nh.chu[TOI_DA])}); }
  if (nh.ket.length) { const m = String(nh.ket[0].chu).match(/^Câu (".*?"|“.*?”)/);
    ds.push({muc: 'nhac', ten: `<b>${nh.ket.length} câu phụ đề</b> bị thẻ kết che`, ct: (m ? 'câu ' + m[1] + (nh.ket.length > 1 ? '…' : '') + ' · ' : '') + 'dời câu sớm hơn hoặc cho thẻ kết hiện ngắn lại', xem: () => r25XemCb(nh.ket[0])}); }
  if (nh.noi.length) { const m = String(nh.noi[0].chu).match(/^Cảnh (\d+): (đầu|cuối)/), c = m && canh[+m[1] - 1];
    ds.push({muc: 'nhac', ten: `<b>${nh.noi.length} chỗ</b> cắt giữa lúc đang nói`, ct: 'nghe sẽ bị vấp', xem: c ? () => r25XemCanh(c._id, m[2] === 'cuối') : () => r25XemCb(nh.noi[0])}); }
  // thẻ giá
  const tgia = chu.the_gia;
  if (!tgia) ds.push({muc: 'tin', ten: 'Chưa có thẻ giá', ct: 'video bán máy nên có giá (phím G)', nut: 'Thêm', xem: () => { dung(); themChu('gia'); }});
  else { const g = gio[tgia._k], gia = String(tgia.gia || '').trim(), xem = () => r25Toi(tgia._k);
    if (!gia) ds.push({muc: 'nhac', ten: '<b>Thẻ giá chưa ghi giá</b>', ct: 'thẻ đang trống', xem});
    else if (g && g.an) ds.push({muc: 'nhac', ten: `<b>Thẻ giá ${esc(gia)}</b> đang ẩn`, ct: g.ly_do || 'không có trong bản xuất', xem});
    else if (g && g.t0 != null) { const x = canhLuc(g.t0 + 0.01); ds.push({muc: 'ok', ten: `Có thẻ giá <b>${esc(gia)}</b>`, ct: (x ? 'cảnh ' + (x.i + 1) + ', ' : '') + 'lúc ' + tg(g.t0)}); } }
  // nhãn đang ẩn (chưa nằm trong cảnh báo trên)
  const daCb = new Set(ct.map(x => x.k).filter(Boolean)), an = (chu.nhan_chu || []).filter(n => String(n.chu || '').trim() && gio[n._k] && gio[n._k].an && !daCb.has(n._k));
  if (an.length) ds.push({muc: 'nhac', ten: `<b>${an.length} nhãn</b> đang ẩn`, ct: (gio[an[0]._k].ly_do || '') + ' · không có trong bản xuất', xem: () => r25Toi(an[0]._k)});
  // clip
  const mat = [...matSet()];
  if (mat.length) { const so = canh.map((c, i) => mat.includes(c.file) ? i + 1 : 0).filter(Boolean), dau = canh.find(c => mat.includes(c.file));
    ds.push({muc: 'loi', ten: mat.length === 1 ? `<b>Thiếu file clip ${esc(base(src(mat[0])))}</b>` : `<b>Thiếu ${mat.length} file clip</b>`, ct: 'cảnh ' + so.join(', ') + ' · tìm lại clip (băng báo đỏ) hoặc xoá các cảnh đó', xem: () => r25XemCanh(dau._id)}); }
  else ds.push({muc: 'ok', ten: `Đủ clip cho ${canh.length} cảnh`, ct: 'không thiếu file'});
  // độ dài
  if (nh.giong.length) ds.push({muc: 'nhac', ten: `<b>Dài ${r25Giay(v.T)}</b>, ngắn hơn giọng đọc AI`, ct: 'đoạn giọng cuối sẽ bị cắt: thêm cảnh hoặc kéo dài cảnh cuối', xem: () => r25XemCanh(canh[canh.length - 1]._id, true)});
  else ds.push({muc: 'ok', ten: `Dài ${r25Giay(v.T)}`, ct: canh.length + ' cảnh'});
  const thu = {loi: 0, nhac: 1, tin: 2, ok: 3};
  return {dang: false, ds: ds.map((x, i) => Object.assign(x, {i})).sort((a, b) => thu[a.muc] - thu[b.muc] || a.i - b.i)};   // dòng con nằm ngay sau dòng tổng (cùng mức, cùng thứ tự)
}
window.r25SoatDs = r25SoatDs;
const r25SoN = s => s.ds.filter(x => (x.muc === 'loi' || x.muc === 'nhac') && !x.con).length;
function r25SoatHtml(s, gonCon) {   // gonCon (hộp Xuất, màn 768 chật): các dòng con "từng chỗ đè" gói trong <details> đóng sẵn; tab Bản xuất: mở sẵn
  const IC = {loi: 'r25Loi', nhac: 'canhBao', tin: 'r25Tin', ok: 'dauTick'};
  if (s.dang) return `<div class="sn-dau"><b>Soát nhanh</b><span>đang soát lại theo bản sửa mới…</span></div>`;
  const n = r25SoN(s), loi = s.ds.some(x => x.muc === 'loi' && /clip/.test(x.ten));
  const dong = (x, i) => `<div class="sn-h ${x.muc}${x.con ? ' sn-con' : ''}" data-sn-muc="${x.muc}"><span class="sn-ic">${x.con ? '' : icon(IC[x.muc])}</span><span class="sn-t">${x.ten}${x.ct ? ` <small>${/^\(/.test(x.ct) ? '' : '· '}${esc(x.ct)}</small>` : ''}</span>${x.xem ? `<button type="button" class="btn small sn-xem" data-sn="${i}" data-tip="${x.nut ? 'Thêm thẻ giá ở vạch đỏ' : 'Tới chỗ này (đóng hộp xuất)'}">${x.nut || 'Xem'}</button>` : ''}</div>`;
  let h = `<div class="sn-dau${n ? '' : ' sach'}"><b>Soát nhanh</b><span>${n ? n + ' chỗ nên xem · ' + (loi ? 'thiếu clip thì máy chưa xuất được' : 'vẫn xuất được') : 'không thấy chỗ nào cần sửa'}</span></div>`;
  let con = [];
  const xaCon = () => { if (!con.length) return ''; const r = `<details class="sn-con-hop"${gonCon ? '' : ' open'}><summary>${gonCon ? 'Xem từng chỗ' : 'Từng chỗ'} (${con.length})</summary>${con.join('')}</details>`; con = []; return r; };
  s.ds.forEach((x, i) => { if (x.con) { con.push(dong(x, i)); return; } h += xaCon() + dong(x, i); });
  return h + xaCon();
}
function r25VeSoat(el, dong) {   // khối trong hộp Xuất video: vẽ lại khi bản xem đang cập nhật xong
  const s = r25SoatDs(), h = r25SoatHtml(s, true);
  el._ds = s.ds; el._dong = dong; el.classList.toggle('dang', s.dang);
  if (el.innerHTML !== h) el.innerHTML = h;
  return s;
}
document.addEventListener('click', e => {
  const b = e.target.closest && e.target.closest('.r25-soat [data-sn]'); if (!b) return;
  const el = b.closest('.r25-soat'), ds = el._ds || (el.closest('#pane') ? R25.ban : null), x = ds && ds[+b.dataset.sn]; if (!x || !x.xem) return;
  e.stopPropagation();
  if (el._dong) el._dong();
  x.xem();
});
const r25MoXuatGoc = moXuat;
moXuat = function () {
  const n0 = $$('.mbg').length, r = r25MoXuatGoc.apply(this, arguments);
  try {
    const bg = $$('.mbg').pop(), m = bg && $$('.mbg').length > n0 ? bg.querySelector('.mbox') : null, u = m && m.querySelector('#xUoc');
    if (u) {
      u.insertAdjacentHTML('beforebegin', '<div class="lbl r25-sl">Trước khi xuất</div><div class="r25-soat" id="r25Soat" role="status" aria-live="polite"></div>');
      const el = m.querySelector('#r25Soat'), dong = () => { const x = bg.querySelector('[data-dong]'); if (x) x.click(); };
      r25VeSoat(el, dong);
      const hen = setInterval(() => { if (!document.body.contains(bg)) return clearInterval(hen); if (el.classList.contains('dang')) r25VeSoat(el, dong); }, 400);
      m.querySelector('#xOk').addEventListener('click', () => { R25.tuHop = true; }, true);
    }
  } catch (e) { console.error(e); }
  return r;
};
// tab Bản xuất: khối "Trước khi xuất" (cùng nội dung) trên hộp Xuất
const r25BenBanGoc = benBan;
benBan = function () {
  const s = r25SoatDs(); R25.ban = s.ds;
  return `<div class="box r25-ban"><h2 class="sec">Trước khi xuất</h2><div class="r25-soat${s.dang ? ' dang' : ''}" role="status">${r25SoatHtml(s)}</div></div>` + r25BenBanGoc.apply(this, arguments);
};
// chấm vàng trên ▾ cạnh Xuất video (rê chuột: "N chỗ nên xem") + thông báo khi bấm Xuất video nhanh (không qua hộp)
function r25Cham() {
  const b = $('#bXuatDd'); if (!b || !S.plan) return;
  const s = r25SoatDs(); if (s.dang) return;
  const n = S.plan.canh.length ? r25SoN(s) : 0;
  b.classList.toggle('r25-co', n > 0);
  if (n) b.dataset.phim = n + ' chỗ nên xem'; else delete b.dataset.phim;
}
const r25ApViewGoc = apView;
apView = function () {   // apView chạy giữa lúc capNhat còn bận (ranh() = false): chờ capNhat xong mới soát (còn bản mới hơn đang tới thì thôi)
  const r = r25ApViewGoc.apply(this, arguments);
  setTimeout(() => { try { if (!window.ranh()) return; r25Cham(); if (S.tab === 'ban' && !r25Go()) veBen(true); } catch (e) {} }, 0);
  return r;
};
const r25XuatGoc = xuat;
xuat = async function (nhap) {
  const tuHop = R25.tuHop; R25.tuHop = false;
  const r = await r25XuatGoc.apply(this, arguments);
  try { if (!nhap && !tuHop && S.xuat && S.xuat.dang) { const s = r25SoatDs(), n = s.dang ? 0 : r25SoN(s);
    if (n) toast('Đang dựng ' + (S.xuat.ban || 'bản mới') + '… · Soát nhanh: ' + n + ' chỗ nên xem (bấm ▾ cạnh Xuất video để xem)'); } } catch (e) {}
  return r;
};
