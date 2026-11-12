/* ============================== MENU GỌN (r43, 11/11/2026) ==============================
   Anh 11/11 18:15 "ui ux menu này chưa ổn" (thanh tab bảng phải), 18:26 "ui ux lại menu" (thanh tab Thư viện + tab Chữ có lưới chip),
   18:28 "agent riêng làm ui ux chức năng nhỏ menu", "check lại bỏ các phần không cần thiết".
   Chỉ đổi TRÌNH BÀY + LỐI VÀO trên giao diện: không đổi khoá kế hoạch, không bỏ tính năng, phím tắt vẫn chạy.
   1. Hai thanh tab (bảng phải #tabs, Thư viện #libTabs) cùng 1 kiểu: tab đều nhau, tab đang chọn nổi rõ (nền lục bảo + gạch vàng),
      số đếm thành huy hiệu nhỏ, không bị cắt khi bảng hẹp, ✦ Claude tách khỏi hàng tab (nút tròn riêng ở cuối).
      Phương án B (để anh chọn): thanh dạng "viên thuốc" (tab đang chọn tô kín). Bật: ?pa=b (nhớ trong máy), về A: ?pa=a.
   2. Thư viện › Chữ: nhóm thu gọn / mở được (nhớ trong máy), lưới chip -> ô xem trước 2–3 cột (_mod-menu-gon: mgChu*).
   3. Menu nhỏ: thứ tự hay dùng, nhãn rõ, câu dài vào (i) / data-tip.
   4. Bỏ / gộp / ẩn phần thừa: mỗi nhóm 1 CỜ (MG_CO) = 1 lớp body.mg-<cờ>; bỏ 1 cờ khỏi MG_CO là trả nhóm đó về như cũ.
   Trình bày: dev/_mod-menu-gon.css. Kiểm: dev/thu-sua-tay/thu_menu_gon.py. */
const MG_CO = [
  'tab',            // 2 thanh tab mới (bảng phải + Thư viện)
  'chu',            // Thư viện › Chữ: nhóm thu gọn + ô xem trước
  // --- menu nhỏ: thứ tự hay dùng, nhãn rõ, câu dài vào (i) ---
  'menu-vd',        // menu tên video ▾: "Video mới" + "Dựng tự động" lên đầu, video gần đây ở dưới
  'menu-canh',      // chuột phải cảnh: Sửa cảnh (chia / cắt / nhân đôi / thay…) lên trước, hiệu ứng cảnh xuống sau
  // 'goi-y-i',     // câu dài thành dấu (i) — anh KHÔNG chọn (12/11), giữ câu như cũ
  'nhan-ro',        // tab Kiểu: "Font" -> "Font cả video", "Kết" -> "Thẻ kết"
  'tip',            // ô gợi ý cùng 1 kiểu: title (ô vàng nhạt của Windows, hiện chậm) -> data-tip của app (thanh trên, bảng phải, hàng nút phát)
  // --- bỏ / gộp / ẩn (mỗi cờ 1 dòng trong bảng PHẦN BỎ / GỘP / ẨN của BAO-CAO) ---
  'pd-them',        // tab Phụ đề: Claude soát / Tự soát / Từ điển / Giọng đọc AI gộp vào nút "Thêm ▾"
  // Anh KHÔNG chọn (12/11), giữ như cũ: 'an-nghe-tv' (nút Tạo phụ đề ở Thư viện › Chữ),
  // 'gop-ti' (tab Thư viện › Tiện ích), 'gop-claude' (nút ✦ Nhờ Claude thanh trên).
  'an-1-lua-chon',  // tab Kiểu: ẩn hàng chọn chỉ có 1 lựa chọn (vd Màu: "Giữ màu gốc")
];
const MG = {pa: 'a'};
(function () {
  let pa = '';
  try {
    const q = new URLSearchParams(location.search).get('pa') || (window.top !== window ? new URLSearchParams(window.top.location.search).get('pa') : '');
    if (q === 'a' || q === 'b') localStorage.setItem('st-pa', q);
    pa = localStorage.getItem('st-pa') || '';
  } catch (e) {}
  MG.pa = pa === 'b' ? 'b' : 'a';
  document.body.classList.add('mg', 'mg-' + MG.pa);
  MG_CO.forEach(k => document.body.classList.add('mg-' + k));
})();

/* ---------- 1. thanh tab bảng phải: chữ tab vào <span> (co chữ được), ✦ Claude thành nút tròn riêng ---------- */
(function () {
  if (!MG_CO.includes('tab')) return;
  const tabs = document.getElementById('tabs'); if (!tabs) return;
  tabs.setAttribute('role', 'tablist'); tabs.setAttribute('aria-label', 'Bảng chỉnh');
  $$('#tabs > button[data-t]').forEach(b => {
    const t = [...b.childNodes].find(n => n.nodeType === 3 && n.textContent.trim());
    if (t) { const s = document.createElement('span'); s.className = 'mg-t'; s.textContent = t.textContent.replace('✦', '').trim(); t.replaceWith(s); }
    b.setAttribute('role', 'tab');
    if (b.dataset.t === 'ai') {
      b.insertAdjacentHTML('afterbegin', `<span class="mg-ai-ic" aria-hidden="true">${icon('ai')}</span>`);
      b.dataset.tip = 'Nhờ Claude: gõ việc cần sửa, Claude đề xuất, anh bấm Đồng ý mới áp'; b.setAttribute('aria-label', 'Nhờ Claude');
    }
  });
  const goc = veTabs;
  veTabs = function () { goc.apply(this, arguments); $$('#tabs > button[data-t]').forEach(b => b.setAttribute('aria-selected', String(b.classList.contains('on')))); };
  veTabs();
})();

/* ---------- 2. Thư viện › Chữ: nhóm thu gọn / mở được + lưới chip -> ô xem trước ----------
   Nhóm (nhớ trong máy, localStorage st-mg-nh): Thêm chữ · Kiểu chữ cả video · Kiểu phụ đề · Thẻ kết · Mẫu chữ riêng (1 chữ) · Font riêng (1 chữ).
   Ô kiểu cả video vẽ bằng CSS theo đúng cách bộ dựng vẽ (khối / viền / màu lục bảo + vàng, chữ của video) -> nhìn là biết kiểu trông ra sao;
   bấm ô = đúng đường cũ (data-tvkieu -> bamKieu: đổi cả video + khung xem nhảy tới chỗ có chữ). Ô font: chữ mẫu viết bằng chính font đó
   (data-kcfont -> kcApFont như cũ). Không đổi khoá kế hoạch. */
const MG_NH = {};
try { Object.assign(MG_NH, JSON.parse(localStorage.getItem('st-mg-nh') || '{}')); } catch (e) {}
const mgNhMo = (id, md) => id in MG_NH ? !!MG_NH[id] : md;
function mgNhom(id, ten, phu, than, o = {}) {
  const mo = mgNhMo(id, o.md !== false);
  return `<section class="mg-nh${mo ? ' mo' : ''}" data-mgnh="${id}"${o.id ? ` id="${o.id}"` : ''}><div class="mg-nh-h"><button type="button" class="mg-nh-b" aria-expanded="${mo}" data-mgnh-bat="${id}">`
    + `<span class="mg-nh-mui" aria-hidden="true">${icon('phai')}</span><span class="mg-nh-t">${ten}</span>${phu ? `<span class="mg-nh-phu">${phu}</span>` : ''}</button>`
    + `${o.i ? tvI(o.i) : ''}${o.nut || ''}</div><div class="mg-nh-than">${than}</div></section>`;
}
document.addEventListener('click', e => {
  const b = e.target.closest('[data-mgnh-bat]'); if (!b) return;
  const sec = b.closest('.mg-nh'), mo = !sec.classList.contains('mo');
  sec.classList.toggle('mo', mo); b.setAttribute('aria-expanded', String(mo));
  MG_NH[b.dataset.mgnhBat] = mo ? 1 : 0; try { localStorage.setItem('st-mg-nh', JSON.stringify(MG_NH)); } catch (x) {}
});
const mgCat = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); return s.length > n ? s.slice(0, n - 1).trim() + '…' : s; };
const mgCatTu = (s, n) => { s = String(s || '').replace(/\s+/g, ' ').trim(); if (s.length <= n) return s; const i = s.lastIndexOf(' ', n); return i > n / 2 ? s.slice(0, i) : s.slice(0, n); };   // cắt ở khoảng trắng (chữ mẫu trong ô nhỏ)
function mgXemChu(v, l1, l2) {   // kiểu chữ cả video (hook 2 dòng) -> HTML mẫu
  const a = `<b class="l1">${esc(l1)}</b>`, b = `<b class="l2">${esc(l2)}</b>`;
  if (v === 'the_bia') return `<span class="mgc mgc-the_bia">${b}<span class="mgc-hop">${a}<i class="mgc-ke"></i></span></span>`;
  if (v === 'nhan_lon') return `<span class="mgc mgc-nhan_lon"><i class="mgc-sao s1">✦</i>${a}${b}<i class="mgc-sao s2">✦</i></span>`;
  return `<span class="mgc mgc-${esc(v)}">${a}${b}</span>`;
}
function mgXemPd(v, cau) {
  const w = String(cau || 'Máy này pin còn ngon lắm').toUpperCase().split(/\s+/).filter(Boolean);
  if (v === 'cum_ngan') { const c = w.slice(0, 3); return `<span class="mgp mgp-cum">${c.map((x, i) => i === Math.min(1, c.length - 1) ? `<em>${esc(x)}</em>` : esc(x)).join(' ')}</span>`; }
  const c = w.slice(0, 6), g = Math.ceil(c.length / 2);
  return `<span class="mgp mgp-cau"><b>${c.slice(0, g).map((x, i) => i === Math.min(2, g - 1) ? `<em>${esc(x)}</em>` : esc(x)).join(' ')}</b><b>${esc(c.slice(g).join(' '))}</b></span>`;
}
function mgXemKet(v) {
  const kmd = S.info.ket_mac_dinh || {}, chu = S.plan.chu || {}, rieng = Array.isArray(chu.ket) && chu.ket.some(Boolean) ? chu.ket : null;
  if (v === 'khong') return `<span class="mgk mgk-khong">${icon('boHet')}<small>Không có thẻ kết</small></span>`;
  const t = rieng || (v === 'the_comment' ? kmd.the_comment : kmd.dia_chi) || [];
  if (v === 'the_comment') return `<span class="mgk mgk-the_comment"><b>${esc(mgCat(t[0] || 'Anh em cần hỏi gì để lại comment', 40))}</b><small>${esc(mgCat(t[1] || 'Poly hỗ trợ nha ♥', 26))}</small></span>`;
  return `<span class="mgk mgk-${esc(v)}"><b>${esc(mgCat(t[0] || 'Ghé Poly test máy nha', 30))}</b><small>${esc(mgCat(t[1] || '', 36))}</small>${v === 'vong_lap' ? `<i class="mgk-lap">${icon('lamMoi')}</i>` : ''}</span>`;
}
function mgLuoiKieu(m, ve) {   // ô xem trước cho 1 mục kiểu cả video (chu / phu_de / ket)
  const d = (S.info.kieu_ds || []).find(x => x.muc === m); if (!d || !d.ds.length) return '';
  const dang = kieuDung(m), x = canhChon(), bg = x ? tvBg(anhCanh(x.c)) : '';
  return `<div class="tv-grid mg-luoi mg-luoi-${m}">${d.ds.map(y => { const on = dang === y.v;
    return `<button type="button" class="tvx mg-o${on ? ' on' : ''}" data-tvkieu="${esc(m)}" data-v="${esc(y.v)}" aria-pressed="${on}" data-tip="${esc(d.ten + ': ' + y.ten + (on ? ' (đang dùng)' : ' · bấm để dùng cho cả video, khung xem cho thấy ngay'))}">
      <span class="xv mg-xv" style="${bg}"><span class="mg-in mg-in-${m}">${ve(y.v)}</span>${on ? `<span class="tick">${icon('dauTick')}</span>` : ''}</span><span class="tvx-ten">${esc(y.ten)}</span></button>`; }).join('')}</div>`;
}
function mgFonts(htmlFonts) {   // nhóm chip font (kcFonts) -> ô: "Aa" + chữ mẫu viết bằng chính font đó
  const t = document.createElement('template'); t.innerHTML = htmlFonts;
  return `<div class="tv-grid mg-luoi mg-fonts">${[...t.content.querySelectorAll('[data-kcfont]')].map(b => {
    const f = b.dataset.kcfont, ff = f ? kcFont(f) : null, on = b.classList.contains('on'), ten = ff ? ff.ten : b.textContent.trim();
    return `<button type="button" class="tvx mg-o mg-f${on ? ' on' : ''}${b.classList.contains('thieu') ? ' thieu' : ''}" data-kcfont="${esc(f)}" aria-pressed="${on}" data-tip="${esc(b.dataset.tip || ten)}">
      <span class="xv mg-xv mg-fv"><span class="mg-in"><span class="mg-fm${ff ? ' kcf-' + esc(ff.id) : ''}" style="font-weight:${kcDam(ff, 0)}"><b>Aa</b><small>Máy 13tr9</small></span></span>${on ? `<span class="tick">${icon('dauTick')}</span>` : ''}</span>
      <span class="tvx-ten${ff ? ' kcf-' + esc(ff.id) : ''}">${esc(ten)}</span></button>`; }).join('')}</div>`;
}
const mgTvChuCu = tvChu;   // = bản đã có nhóm Kiểu chữ (dev/_mod-kieu-chu.js)
tvChu = function () {
  if (!MG_CO.includes('chu') || typeof kcTvChuGoc !== 'function' || typeof kcTv !== 'function') return mgTvChuCu.apply(this, arguments);
  const t = document.createElement('template'); t.innerHTML = kcTvChuGoc();
  const c = t.content, them = c.querySelector('.tv-grid.tv-chu'), nghe = c.querySelector('[data-tva="nghe"]') || c.querySelector('.tv-note.tv-trang');
  const hk = ((S.plan.chu || {}).hook || []).filter(Boolean), l1 = mgCatTu(hk[0] || 'iPad Pro M1', 14), l2 = mgCatTu(hk[1] || '13tr9 có đáng mua?', 17);
  const pd = ((S.plan.phu_de || [])[0] || {}).chu, bo = typeof bmHienTai === 'function' ? bmHienTai() : '';
  const boTen = bo ? ((BM.bo().find(x => x.id === bo) || {}).ten || bo) : '';
  const ghiBo = bo ? `<p class="tv-note mg-bo">${icon('lop')}<span>Đang dùng bộ <b>${esc(boTen)}</b> (tab Kiểu): chữ vẽ theo bộ, ô dưới đây dùng khi về bộ Cũ.</span></p>` : '';
  const tenK = m => esc(tenGiaTri(m, kieuDung(m)));
  let h = mgNhom('them', 'Thêm chữ', 'ở vạch đỏ', (them ? them.outerHTML : '') + (nghe && !MG_CO.includes('an-nghe-tv') ? nghe.outerHTML : ''));
  h += mgNhom('video-chu', 'Kiểu chữ cả video', tenK('chu'), ghiBo + mgLuoiKieu('chu', v => mgXemChu(v, l1, l2)), {i: 'Hook, nhãn, tiêu đề của cả video vẽ theo kiểu này. Bấm 1 ô là đổi ngay, khung xem nhảy tới chỗ có chữ. Ctrl+Z để bỏ.'});
  h += mgNhom('video-pd', 'Kiểu phụ đề', tenK('phu_de'), (bo ? ghiBo : '') + mgLuoiKieu('phu_de', v => mgXemPd(v, pd)), {i: 'Phụ đề luôn in hoa khi dựng. Cả câu: 1–2 dòng, chữ đang đọc màu vàng. Cụm ngắn: 1–3 chữ to nảy theo nhịp nói.'});
  h += mgNhom('video-ket', 'Thẻ kết', tenK('ket'), mgLuoiKieu('ket', mgXemKet), {i: 'Thẻ hiện mấy giây cuối video. Sửa câu, số giây: bảng phải › tab Chữ › Thẻ kết.'});
  // mẫu chữ + font riêng cho 1 chữ (dev/_mod-kieu-chu.js): giữ nguyên ô chọn chữ + lưới mẫu, font thành ô xem trước
  const k = document.createElement('template'); k.innerHTML = kcTv();
  const kt = k.content.querySelector('#kcTv'), d = kcDich(), coRieng = !!d;
  if (kt) {
    const chips = kt.querySelector('.kc-dich-ds'), luoi = kt.querySelector('.kc-luoi'), fonts = kt.querySelector('.kc-fonts'), bo2 = kt.querySelector('.tv-hang');
    const iTip = (kt.querySelector('.tv-h .tv-i') || {}).dataset;
    h += mgNhom('rieng', 'Mẫu chữ cho 1 chữ', d ? 'áp cho ' + esc(kcTen(d)) : (KC.bang.mau || []).length + ' mẫu', (chips ? chips.outerHTML : '') + (luoi ? luoi.outerHTML : '') + (bo2 ? bo2.outerHTML : ''),
      {md: coRieng, i: iTip ? iTip.tip : '', id: 'kcTv'});   // id cũ: "Xem tất cả ở Thư viện ›" của ô Mẫu chữ (dev/_mod-gon-chip.js) cuộn tới đây
    const cu = d ? kcLay(S.plan, d) : null;
    h += mgNhom('font', 'Font cho 1 chữ', d ? (cu && cu.font ? esc((kcFont(cu.font) || {}).ten || '') : 'theo kiểu video') : (KC.bang.font || []).length + ' font', fonts ? mgFonts(fonts.outerHTML) : '',
      {md: coRieng, i: 'Đổi font riêng cho nhãn / thẻ giá / hook đang chọn (giữ màu, khung của kiểu). Font cả video: tab Kiểu › Font.'});
  } else h += mgNhom('rieng', 'Mẫu chữ cho 1 chữ', '', k.innerHTML, {md: false, id: 'kcTv'});
  return `<div class="mg-chu">${h}</div>`;
};
// bảng phải › Mẫu chữ / Font ▾ › "Xem tất cả ở Thư viện ›": mở đúng nhóm (kể cả khi anh đã thu nó lại), cuộn tới nhóm Font nếu bấm từ ô Font
if (typeof gcTv === 'function') {
  const gcTvGoc = gcTv;
  gcTv = function () {
    const L = (typeof GC !== 'undefined' && GC.mo && GC.mo.L) || {}, font = L.k === 'font';
    if (L.tv === 'chu' && MG_CO.includes('chu')) MG_NH[font ? 'font' : 'rieng'] = 1;
    const r = gcTvGoc.apply(this, arguments);
    if (font) setTimeout(() => { const s = document.querySelector('#libPane [data-mgnh=font]'); if (s) s.scrollIntoView({block: 'start'}); }, 60);
    return r;
  };
}

/* ---------- 3. menu nhỏ ---------- */
// 3a. chuột phải cảnh: các lệnh sửa cảnh (hay dùng nhất) lên trước, hiệu ứng / tự động / chép kiểu xuống sau; không bỏ mục nào
queueMicrotask(() => {   // sau mọi mô-đun khác (tách âm, chép / dán kiểu… chèn mục theo nhóm "Sửa cảnh") -> sắp lại sau cùng
  if (!MG_CO.includes('menu-canh')) return;
  const goc = menuCanh;
  menuCanh = function () {
    const ds = goc.apply(this, arguments); if (!Array.isArray(ds) || !ds.length) return ds;
    const iSua = ds.findIndex(x => x && x.nhom === 'Sửa cảnh'), iHu = ds.findIndex(x => x && x.nhom && /^Hiệu ứng cảnh/.test(x.nhom));
    if (iSua < 0 || iHu < 0 || iHu > iSua) return ds;
    let iCuoi = ds.length; for (let j = ds.length - 1; j > iSua; j--) if (ds[j] === '-') { iCuoi = j; break; }   // trước "Xoá cảnh"
    const dau = ds.slice(0, iHu), hu = ds.slice(iHu, iSua), sua = ds.slice(iSua + 1, iCuoi), cuoi = ds.slice(iCuoi);
    while (hu.length && hu[hu.length - 1] === '-') hu.pop();
    return [...dau, ds[iSua], ...sua, '-', ...hu, ...cuoi];   // giữ tiêu đề nhóm "Sửa cảnh" (mục tách âm, chép kiểu… bám theo nó)
  };
});

// 3b. gợi ý dài -> (i): giữ nguyên chữ trong trang (đọc màn hình / bài thử vẫn thấy), chỉ ẩn khỏi mắt; rê (i) để đọc
function mgGoiY(root) {
  if (!MG_CO.includes('goi-y-i')) return;
  (root || document).querySelectorAll('.dy-goi .dy-t:not([data-mg])').forEach(t => {
    const s = t.querySelector(':scope > span'), b = s && s.querySelector('b'); if (!s || !b) return;
    t.dataset.mg = '1'; const tip = s.textContent.replace(/\s+/g, ' ').trim();
    const an = document.createElement('span'); an.className = 'mg-sr'; an.textContent = tip.slice(b.textContent.length).trim();
    [...s.childNodes].filter(n => n !== b).forEach(n => n.remove()); s.append(an);
    b.insertAdjacentHTML('afterend', tvI(tip));
  });
  const n = document.querySelector('.tlbar > .note:not([data-mg])');
  if (n && n.textContent.trim()) { n.dataset.mg = '1'; const tip = n.textContent.trim(); n.classList.add('mg-tl-i'); n.innerHTML = `<span class="mg-sr">${esc(tip)}</span>` + tvI('Timeline: ' + tip); }
}

// 3c. tab Kiểu: nhãn rõ hơn + ẩn hàng chỉ có 1 lựa chọn
const MG_NHAN = {'kieu:bo_font': 'Font cả video', 'kieu:ket': 'Thẻ kết'};
function mgKieu(pane) {
  if (S.tab !== 'kieu') return;
  pane.querySelectorAll('.kgrid select[data-f]:not([data-mg])').forEach(sl => {
    sl.dataset.mg = '1'; const lb = sl.previousElementSibling, nut = sl.nextElementSibling;
    if (MG_CO.includes('nhan-ro') && lb && MG_NHAN[sl.dataset.f]) lb.textContent = MG_NHAN[sl.dataset.f];
    if (MG_CO.includes('an-1-lua-chon') && sl.options.length < 2) [lb, sl, nut].forEach(x => x && x.classList.add('mg-an'));
  });
}

// 3d. tab Phụ đề: hàng đầu chỉ còn việc hay làm (Tạo phụ đề từ lời nói, + Câu ở vạch đỏ); việc ít dùng vào "Thêm ▾" (bấm mở / đóng, nhớ trong máy)
let mgPdMo = false; try { mgPdMo = localStorage.getItem('st-mg-pd-them') === '1'; } catch (e) {}
function mgPd(pane) {
  if (S.tab !== 'pd' || !MG_CO.includes('pd-them')) return;
  const dau = pane.querySelector(':scope > .row'); if (!dau) return;
  const giong = dau.querySelector('[data-a="sua-giong"]'), soat = pane.querySelector('.soat-pd');
  if (!dau.querySelector('[data-mg-pd]')) dau.insertAdjacentHTML('beforeend', `<button type="button" class="btn small mg-pd-them" data-mg-pd aria-expanded="${mgPdMo}" data-tip="Claude soát phụ đề, tự soát sau khi nghe, từ điển của tiệm, giọng đọc AI">Thêm<span class="mg-mui" aria-hidden="true">▾</span></button>`);
  let hang = pane.querySelector('.mg-pd-hang');
  if (!hang) { hang = document.createElement('div'); hang.className = 'row mg-pd-hang'; (soat || dau).after(hang); }
  if (soat && soat.nextElementSibling !== hang) soat.after(hang);
  if (soat && soat.children.length) {   // hàng soát vừa vẽ lại (veSoat): thay bộ nút cũ trong hàng Thêm bằng bộ mới (không nhân đôi)
    hang.querySelectorAll(':scope > :not([data-a="sua-giong"])').forEach(x => x.remove());
    [...soat.children].forEach(x => hang.append(x));
  }
  if (!soat) hang.querySelectorAll(':scope > :not([data-a="sua-giong"])').forEach(x => x.remove());   // video chuyển sang giọng AI: không còn hàng soát
  if (giong && !S.plan.giong) hang.append(giong);   // video có giọng AI: nút "Sửa lời đọc / giọng" giữ trên hàng đầu
  if (soat) soat.classList.add('mg-an');
  hang.hidden = !mgPdMo || !hang.children.length;
  const b = dau.querySelector('[data-mg-pd]'); b.hidden = !hang.children.length; b.setAttribute('aria-expanded', String(mgPdMo)); b.classList.toggle('on', mgPdMo);
}
document.addEventListener('click', e => {
  const b = e.target.closest('#pane [data-mg-pd]'); if (!b) return;
  mgPdMo = !mgPdMo; try { localStorage.setItem('st-mg-pd-them', mgPdMo ? '1' : '0'); } catch (x) {}
  mgPd(document.getElementById('pane'));
});

// 3e. title -> data-tip (cùng kiểu ô gợi ý của app: hiện nhanh, có phím tắt); không đụng menu chuột phải (title = lý do mục bị tắt)
function mgTip(root) {
  if (!MG_CO.includes('tip')) return;
  root.querySelectorAll('button[title], label[title], select[title], a.btn[title]').forEach(e => {
    if (e.closest('.cmenu, .vdmenu, .timenu')) return;
    if (!e.dataset.tip) e.dataset.tip = e.title;
    if (!e.getAttribute('aria-label') && !e.textContent.trim()) e.setAttribute('aria-label', e.title);
    e.removeAttribute('title');
  });
}
queueMicrotask(() => ['#edBtns', '.ctl', '.pbar', '.tlbar'].forEach(s => { const r = document.querySelector(s); if (r) mgTip(r); }));

// bảng phải vẽ lại (nhiều mô-đun tự chèn khối sau veBen) -> làm gọn sau cùng, 1 lần mỗi lượt
(function () {
  const pane = document.getElementById('pane'); if (!pane) return;
  let hen = false;
  const lam = () => { hen = false; try { mgGoiY(pane); mgKieu(pane); mgPd(pane); mgTip(pane); } catch (e) { console.warn('menu gọn', e); } };
  new MutationObserver(() => { if (!hen) { hen = true; queueMicrotask(lam); } }).observe(pane, {childList: true, subtree: true});
  queueMicrotask(() => { mgGoiY(document); lam(); });
})();

/* ---------- 4. bỏ / gộp / ẩn lối vào trùng (tính năng + phím tắt giữ nguyên) ---------- */
// 4a. Thư viện › Tiện ích = nút ⚡ Tiện ích trên thanh trên (cùng danh sách, cùng Chạy / Quản lý) -> bỏ tab trùng, Thư viện còn 7 tab
(function () {
  if (!MG_CO.includes('gop-ti')) return;
  const i = TV_TAB.findIndex(x => x[0] === 'ti'); if (i >= 0) TV_TAB.splice(i, 1);
  if (S.tv.tab === 'ti') S.tv.tab = 'clip';
})();
