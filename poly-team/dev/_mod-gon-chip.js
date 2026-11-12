/* ============================== GỌN CHIP (r28, 5/11/2026) ==============================
   Anh gửi ảnh khung phải tab Cảnh › Hình: "hiển thị nhiều quá, xấu chiếm chỗ" (Chuyển động 7 chip, Hiệu ứng hình 24 chip kín 8 hàng,
   nhãn "đầu cảnh" dính / lệch trong chip). Giờ MỌI nhóm chọn nhiều lựa chọn ở khung phải còn 1 HÀNG như bảng thuộc tính CapCut / FreeCut:
       nhãn · [giá trị đang chọn ▾] · ↺
   Bấm nút giá trị = danh sách nổi gọn (cùng màu lục bảo #074D3A + vàng #FFD600): nhóm con (Cả cảnh / Đầu cảnh / Màu; Cơ bản / Trượt /
   Lau / Zoom / Đặc biệt), ✓ ở mục đang dùng, nhãn nhỏ "chậm" / "đầu cảnh" một cột bên phải, ô tìm (bỏ dấu) khi > 12 mục, rê chuột / phím
   ↑ ↓ = xem trước ở cột trái (ảnh động có sẵn của Thư viện; bộ lọc màu: ảnh máy chủ dựng đúng bộ lọc + khung xem đổi màu gần đúng ngay),
   Enter chọn, Esc đóng, Home / End / PageUp / PageDown, gõ chữ cái nhảy tới mục (danh sách không có ô tìm). Chân danh sách:
   "Xem tất cả ở Thư viện ›" mở đúng tab (Hiệu ứng: lọc sẵn Chuyển động / Bộ lọc; Chuyển cảnh; Chữ).
   Nhóm đã làm gọn: tab Cảnh › Hình: Chuyển động, Hiệu ứng hình · › Màu: Bộ lọc màu · › Chuyển cảnh: kiểu chuyển cảnh vào ·
   tab Chữ (ô Kiểu chữ của chữ đang chọn): Mẫu chữ, Font. (Tab Kiểu vốn đã 1 hàng / mục bằng ô chọn; ô chọn chữ "kc-dich-ds" là chọn
   ĐỐI TƯỢNG, không phải kiểu: giữ nguyên.)
   CÁCH LÀM (không đổi dữ liệu / cách áp, sửa file chung 0 dòng): bảng vẫn vẽ chip / ô như cũ (_canh-tt.js, _mod-hinh.js, _mod-kieu-chu.js);
   mô-đun này (MutationObserver như _mod-ben-phai.js, chạy SAU bpGhiChu nên dấu (i) đã có) giấu nhóm chip (.gc-an) và chèn nút giá trị +
   ↺ vào hàng tiêu đề nhóm. Chọn 1 mục = BẤM ĐÚNG CHIP CŨ (đã giấu) -> cùng đường đi: datHieuUng / datLoc / kcApMau / kcApFont -> doi()
   -> 1 bước Ctrl+Z, tự lưu, xem mẫu. "Theo kiểu chung" / "Không" vẫn là mục đầu; ↺ = bấm chip mặc định (Mẫu chữ: Bỏ kiểu riêng).
   Cảnh 1 không có chuyển cảnh: bảng không vẽ chip -> không có nút. Menu nhóm (quét chọn) / menu chuột phải: không đụng.
   Kiểm: dev/thu-sua-tay/thu_gon_chip.py. Trình bày: dev/_mod-gon-chip.css. */
IC_P.gcMui = '<path d="m6 9 6 6 6-6"/>';
const GC = {mo: null, giu: null};   // giu: loại nút giá trị đang giữ con trỏ bàn phím
const GC_DONG_MO = {dung_yen: 'Khung đứng yên 100%, không tự zoom / lia (tay rung không bị phóng to theo)', zoom_vao: 'Phóng chậm 100% → 108% suốt cảnh',
  zoom_ra: 'Thu chậm 108% → 100% suốt cảnh', phong_sat: 'Phóng cố định 112% cho cận hơn, không chạy', lia_phai: 'Phóng 106%, lia chậm sang phải suốt cảnh',
  lia_trai: 'Phóng 106%, lia chậm sang trái suốt cảnh'};
/* mỗi loại nhóm: a = thuộc tính của chip cũ, nhan = nhãn hàng, ic = biểu tượng đầu nút, tv = tab Thư viện (+ mục lọc / phần cần cuộn tới) */
const GC_LOAI = [
  {k: 'dong', a: 'data-ttdong', nhan: 'Chuyển động', ic: 'dongK', tv: 'hieu', tvNhom: 'dong', md: '', laiTip: 'Về theo kiểu chung (tab Kiểu)'},
  {k: 'hinh', a: 'data-tthinh', nhan: 'Hiệu ứng hình', ic: 'hieuUng', tv: 'hieu', tvNhom: '', tvSec: 'hinh', md: '', laiTip: 'Bỏ hiệu ứng hình cảnh này'},
  {k: 'chuyen', a: 'data-ttchuyen', nhan: 'Chuyển cảnh', ic: 'chuyenC', tv: 'chuyen', md: '', laiTip: 'Về theo kiểu chung (tab Kiểu)'},
  {k: 'loc', a: 'data-hinh-loc', nhan: 'Bộ lọc màu', ic: 'locMau', tv: 'hieu', tvNhom: 'loc', md: '', laiTip: 'Bỏ bộ lọc cảnh này'},
  {k: 'mau', a: 'data-kcmau', nhan: 'Mẫu chữ', ic: 'nhan', tv: 'chu', md: null, laiTip: 'Bỏ mẫu + font riêng: chữ theo kiểu chữ cả video'},
  {k: 'font', a: 'data-kcfont', nhan: 'Font', ic: 'nhan', tv: 'chu', md: '', laiTip: 'Font theo kiểu chữ (bỏ font riêng)'}];
const gcLoai = k => GC_LOAI.find(L => L.k === k);
const gcChu = b => { const x = (b.querySelector('.tvx-ten') || b).cloneNode(true); x.querySelectorAll('.cm-tag, svg, .tick, .tv-tag, .tv-cong').forEach(e => e.remove()); return x.textContent.replace(/\s+/g, ' ').trim(); };
const gcBo = s => typeof boDau === 'function' ? boDau(s) : String(s || '').toLowerCase();

/* ---------- đọc các lựa chọn từ nhóm chip cũ (đang giấu) ---------- */
function gcMuc(L, g) {
  const b0 = bocCanh(), x = b0.find(y => y.c._id === S.sel.canh) || b0[0], c = x ? x.c : null;
  return [...g.querySelectorAll('[' + L.a + ']')].map(b => {
    const v = b.getAttribute(L.a) || '', m = {v, on: b.classList.contains('on') || b.getAttribute('aria-pressed') === 'true', tat: !!b.disabled, ten: gcChu(b), phu: '', tag: '', mo: '', mo2: '', nhom: ''};
    const tg = b.querySelector('.cm-tag'); if (tg) m.tag = tg.textContent.trim();
    if (L.k === 'dong') {
      if (!v) { m.ten = 'Theo kiểu chung'; m.phu = tenNgan('chuyen_dong'); m.chung = true; m.mo = 'Theo chuyển động cả video (tab Kiểu). Cảnh không chọn riêng đều theo kiểu này.'; }
      else m.mo = GC_DONG_MO[v] || '';
    } else if (L.k === 'hinh') {
      if (!v) { m.ten = 'Không'; m.mo = 'Cảnh này không có hiệu ứng hình'; }
      else { const y = dsHieuUngHinh().find(z => z.v === v) || {}; m.ten = y.ten || m.ten; m.mo = y.mo_ta || ''; m.tag = y.dau_canh ? 'đầu cảnh' : ''; if (y.dau_canh) m.mo2 = 'Chỉ chạy ở đầu cảnh'; m.nhom = nhomHu(y); }
    } else if (L.k === 'chuyen') {
      if (!v) { m.ten = 'Theo kiểu chung'; m.phu = tenNgan('chuyen_canh'); m.chung = true; m.mo = 'Theo kiểu chuyển cảnh cả video (tab Kiểu). Cảnh không chọn riêng đều theo kiểu này.'; }
      else { const y = dsChuyenCanh().find(z => z.v === v) || {}; m.ten = y.ten || m.ten; m.tag = y.cham ? 'chậm' : ''; m.mo = (S.info.chuyen_mo_ta || {})[v] || y.mo_ta || ''; if (y.cham) m.mo2 = CHAM_GOI; m.nhom = (S.info.chuyen_nhom || {})[v] || 'dac_biet'; }
    } else if (L.k === 'loc') {
      const y = HINH_LOC.find(z => z.v === v); m.ten = v ? (y ? y.ten : m.ten) : 'Không'; m.mo = v ? (y ? y.mo_ta : '') : 'Không dùng bộ lọc màu';
      if (c) m.anh = anhLoc(c, v, (c.tu + c.den) / 2);
    } else if (L.k === 'mau') {
      const y = kcMau(v) || {}; m.ten = y.ten || m.ten; m.mo = y.goi || ''; const ki = b.querySelector('.kc-in'); m.mau = ki ? ki.innerHTML : ''; if (b.querySelector('.tv-tag')) m.tag = 'hợp';
    } else if (L.k === 'font') {
      const y = v ? kcFont(v) : null; if (y) { m.ten = y.ten; m.mo = y.goi || ''; } else m.mo = b.dataset.tip || '';
      m.font = v; m.thieu = b.classList.contains('thieu'); if (m.thieu) m.mo2 = 'Máy thiếu file font (chép engine/fonts)';
    }
    return m;
  });
}
function gcNhomDs(L) {   // [[khoá, tên]] nhóm con theo thứ tự Thư viện
  if (L.k === 'hinh') return HU_NHOM;
  if (L.k === 'chuyen') { const t = S.info.chuyen_ten_nhom || {}; return XC_NHOM.map(([k, ten]) => [k, t[k] || ten]); }
  return null;
}

/* ---------- nút giá trị + ↺ ---------- */
function gcDau(L, m) {   // ảnh / biểu tượng đầu nút giá trị
  if (L.k === 'loc' && m && m.anh) return `<i class="gc-anh" style="background-image:url('${m.anh}')"></i>`;
  if (L.k === 'mau' && m && m.v && kcMau(m.v)) return `<span class="gc-sw">${kcMauHtml(kcDu(kcMau(m.v)), 'Aa')}</span>`;
  if (L.k === 'font') return `<span class="gc-aa${m && m.v ? ' kcf-' + esc(m.v) : ''}">Aa</span>`;
  return icon(L.ic);
}
function gcNut(L, ds) {
  const m = ds.find(x => x.on), rieng = !!(m && (L.md === null || m.v !== L.md));
  const ten = !m ? (L.k === 'mau' ? 'Theo kiểu video' : '—') : m.chung ? m.phu : m.ten;
  const nhan = !m ? ten : m.chung ? 'Theo kiểu chung: ' + m.phu : m.ten + (m.tag ? ' (' + m.tag + ')' : '');
  const lai = L.k === 'mau' ? !!document.querySelector('#kcBen [data-kcbo]') && rieng : rieng;
  return `<button type="button" class="gc-chon${rieng ? ' rieng' : ''}" data-gc-mo="${L.k}" aria-haspopup="listbox" aria-expanded="false" aria-label="${esc(L.nhan + ': ' + nhan + '. Bấm để chọn')}" data-tip="${esc(L.nhan + ': ' + nhan + ' · bấm để chọn')}">
      <span class="gc-dau" aria-hidden="true">${gcDau(L, m)}</span><span class="gc-gt">${m && m.chung ? '<span class="gc-chung">Chung</span>' : ''}<span class="gc-ten">${esc(ten)}</span>${m && m.tag && L.k !== 'mau' ? `<span class="gc-tag">${esc(m.tag)}</span>` : ''}</span><span class="gc-mui" aria-hidden="true">${icon('gcMui')}</span></button>
    <button type="button" class="gc-lai" data-gc-lai="${L.k}" ${lai ? '' : 'disabled'} aria-label="${esc(L.nhan + ': ' + L.laiTip)}" data-tip="${esc(L.laiTip)}">${icon('datLai')}</button>`;
}

/* ---------- làm gọn: mỗi lần bảng phải vẽ lại ---------- */
function gcGon() {
  const pane = $('#pane'); if (!pane || !S.plan || !S.info) return;
  pane.querySelectorAll('.tv-chips:not([data-gc]), .hinh-lo-grid:not([data-gc]), .kc-luoi:not([data-gc]), .kc-fonts:not([data-gc])').forEach(g => {
    const L = GC_LOAI.find(x => g.querySelector('[' + x.a + ']')); if (!L) return;   // nhóm khác: để nguyên
    let ds; try { ds = gcMuc(L, g); } catch (e) { console.warn('gọn chip', L.k, e); return; }
    g.dataset.gc = L.k; g.classList.add('gc-an');
    const box = g.closest('.tt-box, .kc-ben');
    if (L.k === 'mau' || L.k === 'font') {   // ô Kiểu chữ (tab Chữ): hàng riêng  nhãn · nút · ↺
      if (L.k === 'font') { const lb = g.previousElementSibling; if (lb && lb.classList.contains('lbl')) lb.classList.add('gc-an'); }
      g.insertAdjacentHTML('beforebegin', `<div class="gc-hang gc-tt" data-gc-hang="${L.k}"><span class="gc-nhan">${esc(L.nhan)}</span>${gcNut(L, ds)}</div>`);
      return;
    }
    const row = box && box.querySelector(':scope > .row:first-child'), h2 = row && row.querySelector(':scope > h2');
    if (!row || !h2) { g.insertAdjacentHTML('beforebegin', `<div class="gc-hang gc-tt" data-gc-hang="${L.k}"><span class="gc-nhan">${esc(L.nhan)}</span>${gcNut(L, ds)}</div>`); return; }
    // hàng tiêu đề nhóm thành hàng chọn: nhãn (tiêu đề cũ, dấu (i) đi theo) · nút giá trị · ↺
    box.classList.add('gc-box'); row.classList.add('gc-hang'); row.dataset.gcHang = L.k;
    const goc = h2.textContent.replace(/\s+/g, ' ').trim(), i = row.querySelector(':scope > .tt-i');
    h2.innerHTML = `<span class="gc-nt">${esc(L.k === 'chuyen' ? L.nhan : goc)}</span>`;
    if (L.k === 'chuyen' && goc !== L.nhan) { h2.dataset.tip = goc; h2.setAttribute('aria-label', goc); }
    if (i && L.k === 'chuyen') i.remove();   // "Xem trước từng kiểu: Thư viện › Chuyển cảnh": danh sách nổi đã có xem trước + nút Thư viện
    else if (i) h2.append(i);
    row.insertAdjacentHTML('beforeend', gcNut(L, ds));
  });
  // con trỏ đang ở nút giá trị (dùng phím) mà bảng vẽ lại làm mất: đưa về nút mới cùng loại
  if (GC.giu && (!document.activeElement || document.activeElement === document.body)) { const n = pane.querySelector(`[data-gc-mo="${GC.giu}"]`); if (n) n.focus({preventScroll: true}); }
  // danh sách đang mở mà bảng vừa vẽ lại (máy chủ cập nhật…): bám vào nút mới cùng loại, không thì đóng
  const M = GC.mo; if (!M) return;
  if (M.nut.isConnected) return;
  const n = pane.querySelector(`[data-gc-mo="${M.L.k}"]`), g = pane.querySelector(`[data-gc="${M.L.k}"]`);
  if (!n || !g) return gcDong();
  M.nut = n; M.g = g; n.setAttribute('aria-expanded', 'true'); n.classList.add('mo');
  try { const cu = M.ds[M.act] && M.ds[M.act].v; M.ds = gcMuc(M.L, g); const j = M.ds.findIndex(x => x.v === cu); if (j >= 0) M.act = j; } catch (e) {}
  gcVeDs(); gcDat();
}
new MutationObserver(() => gcGon()).observe($('#pane'), {childList: true, subtree: true});

/* ---------- danh sách nổi ---------- */
function gcMo(nut) {
  const L = gcLoai(nut.dataset.gcMo), g = L && $(`#pane [data-gc="${L.k}"]`); if (!g) return;
  if (GC.mo && GC.mo.nut === nut) return gcDong(true);
  gcDong();
  const ds = gcMuc(L, g), nhom = gcNhomDs(L), tim = ds.length - 1 > 12;
  const el = document.createElement('div'); el.className = 'gc-ds' + (L.k === 'mau' || L.k === 'font' ? ' rong' : ''); el.setAttribute('role', 'dialog');
  el.setAttribute('aria-label', 'Chọn ' + L.nhan.toLowerCase());
  el.innerHTML = `<div class="gc-xc" aria-hidden="true"></div><div class="gc-cot">`
    + (tim ? `<label class="gc-tim">${icon('tim')}<input type="search" class="inp" placeholder="Tìm ${esc(L.nhan.toLowerCase())}… (gõ không dấu được)" aria-label="Tìm ${esc(L.nhan.toLowerCase())}" aria-controls="gcList" autocomplete="off" spellcheck="false"></label>` : '')
    + `<div class="gc-list" id="gcList" role="listbox" tabindex="-1" aria-label="${esc(L.nhan)}"></div>`
    + `<div class="gc-chan"><span>${ds.filter(x => x.v || L.md !== '').length} ${L.k === 'font' ? 'font' : L.k === 'mau' ? 'mẫu' : 'kiểu'}</span><button type="button" class="gc-tv" data-tip="Thư viện bên trái: xem đủ kèm ảnh động, kéo / bấm để dùng">Xem tất cả ở Thư viện ›</button></div></div>`;
  document.body.append(el);
  const act = Math.max(0, ds.findIndex(x => x.on));
  GC.mo = {L, nut, g, el, ds, nhom, tim: '', coTim: tim, act, thu: [], phim: false, tam: false};
  nut.setAttribute('aria-expanded', 'true'); nut.classList.add('mo');
  $$('.tip').forEach(t => t.classList.remove('on'));
  if (L.k === 'loc') { const c = canhDangChon(); if (c) vaoCanh(c._id); }
  gcVeDs(); gcXem(); gcDat(true);
  const f = el.querySelector('.gc-tim input') || el.querySelector('.gc-list'); f.focus({preventScroll: true});
  const o = el.querySelector('.gc-o.act'); if (o) o.scrollIntoView({block: 'center'});
}
function gcDong(veNut) {   // veNut: trả con trỏ về nút giá trị (đóng bằng phím)
  const M = GC.mo; if (!M) return;
  GC.mo = null; M.el.remove(); M.nut.setAttribute('aria-expanded', 'false'); M.nut.classList.remove('mo');
  if (M.tam && S.tam && S.tam.khoa === 'loc') { S.tam = null; if (!S.playing) veKhung(true); }   // thôi xem thử bộ lọc: khung xem về như cũ
  if (veNut && M.nut.isConnected) { M.nut.focus({preventScroll: true}); GC.giu = M.L.k; }
}
function gcVeDs() {
  const M = GC.mo; if (!M) return;
  const q = gcBo(M.tim).trim(), hop = m => !q || gcBo([m.ten, m.phu, m.mo, m.tag].join(' ')).includes(q);
  const thu = [], L = M.L;
  const o = (m, i, nh) => { thu.push(i);
    const tag = m.tag && !(L.k === 'hinh' && nh === 'dau_canh') ? `<span class="gc-otag">${esc(m.tag)}</span>` : '';
    const anh = L.k === 'loc' && m.anh ? `<i class="gc-anh" style="background-image:url('${m.anh}')"></i>` : L.k === 'mau' ? `<span class="gc-sw lon">${m.mau ? m.mau : ''}</span>` : '';
    const ten = L.k === 'font' && m.v ? `<span class="gc-ot kcf-${esc(m.v)}">${esc(m.ten)}</span>` : `<span class="gc-ot">${esc(m.ten)}</span>`;
    return `<div class="gc-o${m.on ? ' on' : ''}${i === M.act ? ' act' : ''}${m.tat ? ' tat' : ''}${anh ? ' co-anh' : ''}${m.phu ? ' co-phu' : ''}${m.thieu ? ' thieu' : ''}" role="option" id="gcO${i}" data-i="${i}" data-v="${esc(m.v)}" aria-selected="${m.on}"${m.tat ? ' aria-disabled="true"' : ''}>`
      + `<span class="gc-ck" aria-hidden="true">${m.on ? icon('dauTick') : ''}</span>${anh}${ten}${m.phu ? `<span class="gc-phu">${esc(m.phu)}</span>` : ''}${tag}</div>`; };
  let h = '';
  const ds = M.ds.map((m, i) => [m, i]), dau = ds.filter(([m]) => !m.v && (m.chung || L.md === '')), con = ds.filter(x => !dau.includes(x));
  if (!q) h += dau.map(([m, i]) => o(m, i, '')).join('');
  if (M.nhom) M.nhom.forEach(([k, ten]) => { const bs = con.filter(([m]) => m.nhom === k && hop(m)); if (!bs.length) return;
    h += `<div class="gc-nh" role="presentation">${esc(ten)}<span>${bs.length}</span></div>` + bs.map(([m, i]) => o(m, i, k)).join(''); });
  else h += con.filter(([m]) => hop(m)).map(([m, i]) => o(m, i, '')).join('');
  if (q && M.nhom) { const le = con.filter(([m]) => !M.nhom.some(([k]) => k === m.nhom) && hop(m)); h += le.map(([m, i]) => o(m, i, '')).join(''); }
  if (!thu.length) h = `<p class="gc-rong">Không có mục nào khớp “${esc(M.tim.trim())}”. Xoá bớt chữ trong ô tìm.</p>`;
  M.thu = thu; if (!thu.includes(M.act)) M.act = thu.length ? thu[0] : -1;
  const ls = M.el.querySelector('.gc-list'); ls.innerHTML = h;
  $$('.gc-o', ls).forEach(e => e.classList.toggle('act', +e.dataset.i === M.act));
  gcAria();
}
function gcAria() {
  const M = GC.mo; if (!M) return;
  const id = M.act >= 0 ? 'gcO' + M.act : '';
  [M.el.querySelector('.gc-list'), M.el.querySelector('.gc-tim input')].forEach(e => { if (!e) return; if (id) e.setAttribute('aria-activedescendant', id); else e.removeAttribute('aria-activedescendant'); });
}
function gcAct(i, cuon) {
  const M = GC.mo; if (!M || i === M.act || i < 0) return;
  M.act = i; $$('.gc-o', M.el).forEach(e => e.classList.toggle('act', +e.dataset.i === i));
  if (cuon) { const e = M.el.querySelector('#gcO' + i); if (e) e.scrollIntoView({block: 'nearest'}); }
  gcAria(); gcXem();
}
/* xem trước mục đang trỏ: ảnh động có sẵn của Thư viện (TV_DONG / TV_HINH / TV_XC), bộ lọc = ảnh máy chủ + khung xem, mẫu chữ / font = chữ mẫu */
function gcXem() {
  const M = GC.mo; if (!M) return;
  const m = M.ds[M.act], xc = M.el.querySelector('.gc-xc'); if (!xc) return;
  if (!m) { xc.innerHTML = ''; return; }
  const b0 = bocCanh(), x = b0.find(y => y.c._id === S.sel.canh) || b0[0], c = x && x.c, L = M.L;
  let o = '';
  if (c && L.k === 'dong') { const k = m.v || kieuDung('chuyen_dong'); o = `<span class="tvx gc-xem"><span class="xv hu hu-${TV_DONG[k] || 'zxk'}" style="--b:url('${anhCanh(c)}')"><i class="xb"></i><i class="xf"></i></span></span>`; }
  else if (c && L.k === 'hinh') o = `<span class="tvx gc-xem"><span class="xv hu ${m.v && TV_HINH[m.v] ? 'hu-' + TV_HINH[m.v] : ''}" style="--b:url('${anhCanh(c)}')"><i class="xb"></i><i class="xf"></i></span></span>`;
  else if (c && L.k === 'chuyen') { const tr = b0[x.i - 1], A = tr ? anhCanh(tr.c, tr.c.den - 0.15) : anhCanh(c, c.tu + 0.1), B = anhCanh(c, c.tu + 0.1), k = m.v || kieuDung('chuyen_canh');
    o = `<span class="tvx gc-xem"><span class="xv xc-${TV_XC[k] || 'fade'}" style="--a:url('${A}');--b:url('${B}')"><i class="xa"></i><i class="xb"></i><i class="xf"></i></span></span>`; }
  else if (L.k === 'loc') o = `<span class="tvx gc-xem"><span class="xv"><i class="xb" style="background-image:url('${m.anh || ''}')"></i></span></span>`;
  else if (L.k === 'mau') o = `<span class="tvx kc-m gc-xem"><span class="xv kc-xv"${c ? ` style="background-image:url('${anhCanh(c)}')"` : ''}><span class="kc-in">${m.mau || ''}</span></span></span>`;
  else if (L.k === 'font') o = `<span class="tvx gc-xem"><span class="xv gc-fxv${m.v ? ' kcf-' + esc(m.v) : ''}"><b>Aa</b><small>Pin 98% · Máy đẹp</small></span></span>`;
  xc.innerHTML = o + `<b class="gc-xt">${esc(m.chung ? m.ten + ': ' + m.phu : m.ten)}</b>${m.mo ? `<small class="gc-xm">${esc(m.mo)}</small>` : ''}${m.mo2 ? `<small class="gc-xm vang">${esc(m.mo2)}</small>` : ''}`;
  // bộ lọc: khung xem đổi màu gần đúng ngay (S.tam như lúc kéo thanh); đóng mà không chọn thì trả lại
  if (L.k === 'loc' && c) { const cu = locC(c); S.tam = {id: c._id, khoa: 'loc', gt: m.v ? {ten: m.v, muc: cu ? cu.muc : 1} : null}; M.tam = true; if (!S.playing) veKhung(true); }
}
function gcDat(dau) {   // đặt danh sách dưới nút (không đủ chỗ thì lên trên), mép phải thẳng mép phải nút, không ra ngoài màn
  const M = GC.mo; if (!M) return;
  const el = M.el, r = M.nut.getBoundingClientRect(), ls = el.querySelector('.gc-list');
  el.classList.toggle('hep', innerWidth < 760);
  ls.style.maxHeight = '';
  const W = el.offsetWidth, cao = el.offsetHeight, duoi = innerHeight - r.bottom - 10, tren = r.top - 10;
  const len = duoi < Math.min(cao, 320) && tren > duoi, cho = Math.max(160, len ? tren : duoi);
  if (cao > cho) ls.style.maxHeight = Math.max(110, ls.offsetHeight - (cao - cho)) + 'px';
  const h = el.offsetHeight;
  el.style.left = Math.max(6, Math.min(innerWidth - W - 6, r.right - W)) + 'px';
  el.style.top = Math.max(6, len ? r.top - 4 - h : Math.min(r.bottom + 4, innerHeight - h - 6)) + 'px';
  el.classList.toggle('len', len);
}
function gcChon(i, phim) {
  const M = GC.mo; if (!M) return; const m = M.ds[i]; if (!m || m.tat) return;
  const L = M.L; gcDong(phim);
  if (m.on) return;
  gcBam(L, '[' + L.a + '="' + CSS.escape(m.v) + '"]', phim);
}
function gcBam(L, sel, phim) {   // bấm chip cũ (đã giấu) -> đúng đường đi cũ (doi() -> Ctrl+Z, tự lưu, xem mẫu)
  const g = $(`#pane [data-gc="${L.k}"]`), b = g && (sel.startsWith('#') ? $(sel) : g.querySelector(sel));
  if (!b || b.disabled) return;
  if (phim) GC.giu = L.k;   // chọn bằng phím: bảng vẽ lại (1 hay nhiều lần) xong thì con trỏ về nút giá trị mới (gcGon)
  b.click();
}
function gcTv() {   // "Xem tất cả ở Thư viện ›": mở đúng tab (lọc sẵn mục)
  const M = GC.mo; if (!M) return; const L = M.L; gcDong();
  try {
    if (L.tv === 'hieu' && typeof TVT !== 'undefined') { TVT.loc.hieu.tim = ''; TVT.loc.hieu.nhom = L.tvNhom || ''; }
    if (L.tv === 'chuyen' && typeof TVT !== 'undefined') { TVT.loc.chuyen.tim = ''; TVT.loc.chuyen.nhom = ''; }
  } catch (e) {}
  moTab(L.tv);
  if (L.tv === 'hieu' && typeof tvApLoc === 'function') tvApLoc('hieu');
  setTimeout(() => {
    const s = L.tvSec ? $(`#libPane [data-tvl-sec="${L.tvSec}"]`) : L.tv === 'chu' ? $('#kcTv') : L.tvNhom ? $(`#libPane [data-tvl-sec="${L.tvNhom}"]`) : null;
    if (s) s.scrollIntoView({block: 'start'});
    const on = $('#libPane .tvx.on, #libPane .tvchip.on'); if (on && !L.tvSec && L.tv !== 'chu') on.scrollIntoView({block: 'nearest'});
  }, 30);
}

/* ---------- bấm / phím ---------- */
$('#pane').addEventListener('click', e => {
  const n = e.target.closest('[data-gc-mo]'); if (n) { e.stopPropagation(); return gcMo(n); }
  const l = e.target.closest('[data-gc-lai]'); if (!l || l.disabled) return;
  e.stopPropagation(); const L = gcLoai(l.dataset.gcLai); gcDong();
  if (L.k === 'mau') gcBam(L, '#kcBen [data-kcbo]'); else gcBam(L, '[' + L.a + '=""]');
});
$('#pane').addEventListener('keydown', e => {   // nút giá trị: ↓ ↑ Enter phím cách mở danh sách (đừng để phím tắt timeline / phát ăn mất)
  const n = e.target.closest && e.target.closest('[data-gc-mo]'); if (!n || e.ctrlKey || e.metaKey || e.altKey) return;
  if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key)) { e.preventDefault(); e.stopPropagation(); if (!GC.mo || GC.mo.nut !== n) gcMo(n); }
});
/* phím trong danh sách: bắt ở pha capture của window (mô-đun này nạp trước _mod-quet / _mod-r25-tl / _mod-thu-vien-them) -> chặn hẳn
   phím tắt (Delete xoá nhóm, S chia cảnh, phím cách phát…); chữ gõ vào ô tìm vẫn vào ô (không chặn mặc định). */
addEventListener('keydown', e => {
  const M = GC.mo; if (!M || !M.el.contains(e.target)) return;
  const trongO = !!(e.target.matches && e.target.matches('.gc-tim input'));
  if (e.ctrlKey || e.metaKey) { if (/^[zy]$/i.test(e.key)) gcDong(true); else e.stopImmediatePropagation(); return; }   // Ctrl+Z / Y: đóng rồi hoàn tác như thường
  e.stopImmediatePropagation();
  const thu = M.thu, j = thu.indexOf(M.act), di = d => { e.preventDefault(); if (!thu.length) return; gcAct(thu[clamp((j < 0 ? (d > 0 ? -1 : thu.length) : j) + d, 0, thu.length - 1)], true); };
  if (e.key === 'ArrowDown') return di(1);
  if (e.key === 'ArrowUp') return di(-1);
  if (e.key === 'PageDown') return di(8);
  if (e.key === 'PageUp') return di(-8);
  if ((e.key === 'Home' || e.key === 'End') && !trongO) { e.preventDefault(); return gcAct(e.key === 'Home' ? thu[0] : thu[thu.length - 1], true); }
  if (e.key === 'Enter' || (e.key === ' ' && !trongO)) { e.preventDefault(); return gcChon(M.act, true); }
  if (e.key === 'Escape' || e.key === 'Tab') { e.preventDefault(); return gcDong(true); }
  if (!trongO && e.key.length === 1 && /\S/.test(e.key)) {   // không có ô tìm: gõ chữ cái nhảy tới mục bắt đầu bằng chữ đó
    e.preventDefault(); const k = gcBo(e.key), sau = thu.slice(j + 1).concat(thu.slice(0, j + 1)), t = sau.find(i => gcBo(M.ds[i].ten).startsWith(k));
    if (t != null) gcAct(t, true);
  }
}, true);
document.addEventListener('input', e => {
  const M = GC.mo; if (!M || !e.target.matches || !e.target.matches('.gc-tim input') || !M.el.contains(e.target)) return;
  M.tim = e.target.value; gcVeDs(); gcXem(); const ls = M.el.querySelector('.gc-list'); if (ls) ls.scrollTop = 0;
});
document.addEventListener('pointermove', e => {
  const M = GC.mo; if (!M) return; const o = e.target.closest && e.target.closest('.gc-ds .gc-o'); if (o && !o.classList.contains('tat')) gcAct(+o.dataset.i, false);
});
document.addEventListener('focusin', e => { const n = e.target.closest && e.target.closest('[data-gc-mo]');
  if (n) GC.giu = n.dataset.gcMo; else if (!(GC.mo && GC.mo.el.contains(e.target))) GC.giu = null; });
document.addEventListener('pointerdown', e => {
  GC.giu = null;   // dùng chuột: thôi giữ con trỏ ở nút (phím cách vẫn là phát / dừng)
  const M = GC.mo; if (!M) return;
  if (M.el.contains(e.target)) { if (e.target.closest('.gc-o, .gc-tv, .gc-xc, .gc-nh, .gc-chan')) e.preventDefault(); return; }   // giữ con trỏ trong ô tìm / danh sách
  if (!e.target.closest('[data-gc-mo]')) gcDong();   // bấm ra ngoài: đóng (bấm lại nút giá trị: nút tự đóng / mở)
}, true);
document.addEventListener('click', e => {
  const M = GC.mo; if (!M || !M.el.contains(e.target)) return;
  const o = e.target.closest('.gc-o'); if (o) return gcChon(+o.dataset.i, false);
  if (e.target.closest('.gc-tv')) return gcTv();
});
addEventListener('resize', () => gcDong()); addEventListener('blur', () => gcDong());
addEventListener('scroll', e => {   // cuộn bảng phải: danh sách đi theo nút; nút ra khỏi bảng thì đóng (cuộn timeline khi vạch đỏ nhảy vào cảnh: kệ)
  const M = GC.mo; if (!M || M.el.contains(e.target) || !(e.target === document || (e.target.contains && e.target.contains(M.nut)))) return;
  const r = M.nut.getBoundingClientRect(), p = $('#pane').getBoundingClientRect();
  if (r.bottom < p.top + 4 || r.top > p.bottom - 4) gcDong(); else gcDat();
}, true);
window.GON_CHIP = {mo: () => GC.mo, dong: gcDong, loai: GC_LOAI};   // cho bài kiểm
