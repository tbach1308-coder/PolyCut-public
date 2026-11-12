/* ============================== BẢNG THUỘC TÍNH CẢNH (3/11 đêm, chủ tiệm: "mấy ô có chức năng giống capcut") ==============================
   Tab Cảnh bên phải = thuộc tính của cảnh đang chọn (như cột phải CapCut), tab con:
     Hình (thu phóng, vị trí ngang / dọc, chuyển động, hiệu ứng hình) · Âm thanh (âm lượng, tắt tiếng)
     · Màu (độ sáng, tương phản, độ đậm màu, nhiệt màu) · Chuyển cảnh vào.
   Khoá riêng cảnh (bộ dựng máy chủ dung_may_chu.shot_clip; Premiere bỏ qua):
     canh.khung {zoom 1–3, x −1..1, y −1..1} · canh.am_luong 0–2 (1 = giữ) · canh.mau {sang ±0,3, tuong_phan 0,5–1,5, bao_hoa 0–2, nhiet 3000–9000 K}.
   Kéo thanh: khung xem đổi NGAY (S.tam -> CSS transform / lọc màu SVG #stMau / video.volume); thả tay mới doi() = 1 bước Ctrl+Z.
   Khung xem đọc khung / màu / âm lượng theo id cảnh trong S.plan (đổi xong thấy ngay, khỏi chờ máy chủ).
   4/11 tối (anh: "khung này chưa tối ưu, nghiên cứu lại ui ux"): bảng gọn kiểu CapCut, trình bày ở dev/_mod-ben-phai.css / .js:
     nhóm phẳng (không hộp lồng hộp), mỗi thuộc tính 1 hàng: nhãn · thanh · ô số gõ được (.tt-so) · nút về mặc định;
     <p class="note"> trong nhóm tự thành dấu (i) cạnh tiêu đề (rê chuột xem), muốn giữ dòng chữ thì thêm class "giu";
     video 1 cảnh: ẩn ‹ ›, thẻ con Chuyển cảnh, danh sách cảnh (chỉ còn nút Thêm cảnh). */
const TT_TAB = [['hinh', 'catKhung', 'Hình'], ['am', 'loa', 'Âm thanh'], ['mau', 'giotMau', 'Màu'], ['chuyen', 'chuyenC', 'Chuyển cảnh']];
S.tabCanh = 'hinh'; S.tam = null; S.amCu = {}; S.dsMo = false;
try { const t = localStorage.getItem('st-tab-canh'); if (TT_TAB.some(x => x[0] === t)) S.tabCanh = t; S.dsMo = localStorage.getItem('st-ds-canh') === '1'; } catch (e) {}
const so_ = (v, m) => (v == null || v === '' || !isFinite(+v)) ? m : +v;
function khungC(c) { const k = (c && c.khung) || {}; return {zoom: clamp(so_(k.zoom, 1), 1, 3), x: clamp(so_(k.x, 0), -1, 1), y: clamp(so_(k.y, 0), -1, 1)}; }
function mauC(c) { const m = (c && c.mau) || {}; return {sang: clamp(so_(m.sang, 0), -0.3, 0.3), tuong_phan: clamp(so_(m.tuong_phan, 1), 0.5, 1.5), bao_hoa: clamp(so_(m.bao_hoa, 1), 0, 2), nhiet: clamp(so_(m.nhiet, 6500), 3000, 9000)}; }
function amC(c) { return clamp(so_(c && c.am_luong, 1), 0, 2); }
const khungMd = k => k.zoom === 1 && k.x === 0 && k.y === 0;
const mauMd = m => m.sang === 0 && m.tuong_phan === 1 && m.bao_hoa === 1 && m.nhiet === 6500;
const nhietUi = K => K <= 6500 ? Math.round((6500 - K) / 35) : -Math.round((K - 6500) / 25);   // + = ấm (K thấp), − = lạnh
const nhietK = v => Math.round(v >= 0 ? 6500 - v * 35 : 6500 - v * 25);
const dau = v => (v > 0 ? '+' : '') + v;
/* thanh kéo: giá trị trên thanh <-> giá trị trong kế hoạch */
const TT = {
  'khung.zoom': {ten: 'Thu phóng', min: 100, max: 300, ui: c => Math.round(khungC(c).zoom * 100), nhan: v => v + '%', ve: v => r3(v / 100)},
  'khung.x': {ten: 'Ngang', min: -100, max: 100, ui: c => Math.round(khungC(c).x * 100), nhan: v => !v ? 'Giữa' : v < 0 ? 'Trái ' + -v : 'Phải ' + v, ve: v => r3(v / 100)},
  'khung.y': {ten: 'Dọc', min: -100, max: 100, ui: c => Math.round(khungC(c).y * 100), nhan: v => !v ? 'Giữa' : v < 0 ? 'Trên ' + -v : 'Dưới ' + v, ve: v => r3(v / 100)},
  'am': {ten: 'Âm lượng', min: 0, max: 200, ui: c => Math.round(amC(c) * 100), nhan: v => v + '%', ve: v => r3(v / 100)},
  'mau.sang': {ten: 'Độ sáng', min: -100, max: 100, ui: c => Math.round(mauC(c).sang / 0.003), nhan: dau, ve: v => r3(v * 0.003)},
  'mau.tuong_phan': {ten: 'Tương phản', min: -100, max: 100, ui: c => Math.round((mauC(c).tuong_phan - 1) / 0.005), nhan: dau, ve: v => r3(1 + v * 0.005)},
  'mau.bao_hoa': {ten: 'Độ đậm màu', min: -100, max: 100, ui: c => Math.round((mauC(c).bao_hoa - 1) * 100), nhan: dau, ve: v => r3(1 + v / 100)},
  'mau.nhiet': {ten: 'Ấm / lạnh', min: -100, max: 100, ui: c => nhietUi(mauC(c).nhiet), nhan: v => v > 0 ? 'Ấm ' + v : v < 0 ? 'Lạnh ' + -v : 'Giữ', ve: nhietK}
};
function ttGiaTri(c, f, v) {   // -> {khoa, gt}: gt null = về mặc định (xoá khoá khỏi cảnh)
  const [a, b] = f.split('.'), x = TT[f].ve(v);
  if (a === 'khung') { const k = khungC(c); k[b] = x; return {khoa: 'khung', gt: khungMd(k) ? null : k}; }
  if (a === 'am') return {khoa: 'am_luong', gt: x === 1 ? null : x};
  const m = mauC(c); m[b] = x; return {khoa: 'mau', gt: mauMd(m) ? null : m};
}
function datTT(id, khoa, gt, key) {
  const c = S.plan.canh.find(x => x._id === id); if (!c) return;
  if (JSON.stringify(c[khoa] ?? null) === JSON.stringify(gt ?? null)) { S.tam = null; return; }
  S.tam = null;
  doi(p => { const y = p.canh.find(x => x._id === id); if (!y) return; if (gt == null) delete y[khoa]; else y[khoa] = gt; }, key);
}
/* chỗ thừa của clip so với khung 9:16 -> vị trí ngang / dọc có tác dụng không */
function thuaCanh(c, zoom) {
  const n = (S.plan.nguon || {})[c.file] || {}, W = +n.rong || 9, H = +n.cao || 16, ar = W / H, kh = 9 / 16;
  return {ngang: zoom > 1.001 || ar > kh * 1.01, doc: zoom > 1.001 || ar < kh * 0.99, quayNgang: ar > 1.01};
}
const ttDai = (d, v) => {   // vệt màu trên thanh: thanh 2 phía (− / +) tô từ giữa ra, thanh 1 phía tô từ đầu
  const p = (v - d.min) / (d.max - d.min) * 100, g = d.min < 0 ? 50 : 0;
  return `--t0:${Math.min(g, p).toFixed(1)}%;--t1:${Math.max(g, p).toFixed(1)}%`;
};
function thanhTT(c, f, tat, ly) {
  const d = TT[f], v = d.ui(c), md = f === 'khung.zoom' ? 100 : f === 'am' ? 100 : 0;
  return `<div class="tt-h${tat ? ' tat' : ''}"${ly ? ` data-tip="${esc(ly)}"` : ''}><label for="tt-${f.replace('.', '-')}">${d.ten}</label>
    <input type="range" id="tt-${f.replace('.', '-')}" class="tt-r" data-tt="${f}" min="${d.min}" max="${d.max}" step="1" value="${v}"${tat ? ' disabled' : ''} style="${ttDai(d, v)}">
    <input type="text" class="tt-so" data-tt-ra="${f}" data-tt-so="${f}" value="${esc(d.nhan(v))}" inputmode="decimal" autocomplete="off" spellcheck="false" aria-label="${d.ten}: gõ số rồi Enter"${tat ? ' disabled' : ''}>
    <button type="button" class="btn small icon ghost tt-lai" data-tt-lai="${f}" ${v === md || tat ? 'disabled' : ''} aria-label="${d.ten}: về mặc định" data-tip="Về mặc định">${icon('datLai')}</button></div>`;
}
const chipTT = (attr, v, ten, on, o = {}) => `<button type="button" class="tvchip${on ? ' on' : ''}" ${attr}="${esc(v)}" aria-pressed="${on}"${o.tat ? ' disabled' : ''}${o.goi ? ` data-tip="${esc(o.goi)}"` : ''}>${on ? icon('dauTick') : ''}${esc(ten)}${o.nhan ? `<span class="cm-tag">${esc(o.nhan)}</span>` : ''}</button>`;
function benCanh() {
  const b = bocCanh(), x = b.find(y => y.c._id === S.sel.canh) || b[0]; if (!x) return '';
  const c = x.c, i = x.i, n = b.length, k = S.plan.kieu || {};
  const tab = S.tabCanh;   // r29 (soi L3): video 1 cảnh vẫn có thẻ con Chuyển cảnh, trong đó chỉ đường Chia (S) (trước đây giấu thẻ -> ngõ cụt)
  // đầu cảnh: độ dài nói 1 lần; đoạn lấy trong clip (giây … đến …) để trong ô gợi ý
  let h = `<div class="tt-dau"><div class="th" style="background-image:url('${thumbUrl(src(c.file), (c.tu + c.den) / 2)}')"></div>
      <div class="tt-ten"><b>Cảnh ${i + 1}${n > 1 ? `<span class="count"> / ${n}</span>` : ''}<span class="tt-dai">${gs(c.den - c.tu)}</span></b><small data-tip="Lấy đoạn ${gs(c.tu)}–${gs(c.den)} của clip ${esc(base(c.file))}">${c.mo_ta ? esc(c.mo_ta) + ' · ' : ''}${esc(base(c.file))}</small></div>
      ${n > 1 ? `<span class="tt-nav"><button type="button" class="btn small icon" data-tt-nav="-1" ${i ? '' : 'disabled'} aria-label="Cảnh trước" data-tip="Cảnh trước">${icon('trai')}</button><button type="button" class="btn small icon" data-tt-nav="1" ${i < n - 1 ? '' : 'disabled'} aria-label="Cảnh sau" data-tip="Cảnh sau">${icon('phai')}</button></span>` : ''}</div>
    <nav class="tt-tabs" role="tablist">${TT_TAB.map(([t, ic, ten]) => `<button type="button" role="tab" aria-selected="${t === tab}" class="${t === tab ? 'on' : ''}" data-tttab="${t}">${icon(ic)}<span>${ten}</span></button>`).join('')}</nav>`;
  const pr = k.duong === 'premiere' ? `<p class="note dim tt-pr" tabindex="0" data-tip="Video này Claude dựng bằng Premiere: khung, âm lượng, màu riêng từng cảnh có ở bản xuất trong app (Xuất bản nháp / Xuất video); lần sau nhờ Claude dựng lại bằng Premiere thì bị bỏ qua.">${icon('thongTin')}<span>Video dựng bằng Premiere: chỉnh riêng cảnh chỉ có khi xuất trong app</span></p>` : '';
  if (tab === 'hinh') {
    const kh = khungC(c), th = thuaCanh(c, kh.zoom);
    if (typeof hinhDungYen === 'function') h += hinhDungYen(c);   // gợi ý "Hình tự zoom / lia? Bấm Đứng yên" (dev/_mod-dung-yen.js, 4/11)
    if (typeof hinhChongRung === 'function') h += hinhChongRung(c);   // Chống rung cảnh này / mọi cảnh (dev/_mod-chong-rung.js, 4/11)
    h += `<div class="box tt-box"><div class="row"><h2 class="sec grow">Vị trí và kích thước</h2>
        <button type="button" class="btn small" data-tt-a="giua" ${kh.x || kh.y ? '' : 'disabled'} data-tip="Đưa về giữa (giữ thu phóng)">${icon('giua')}Căn giữa</button>
        <button type="button" class="btn small ghost" data-tt-a="khung-lai" ${khungMd(kh) ? 'disabled' : ''} data-tip="Thu phóng 100%, về giữa">${icon('datLai')}Đặt lại</button></div>
      ${thanhTT(c, 'khung.zoom')}${thanhTT(c, 'khung.x', !th.ngang, th.ngang ? '' : 'Clip vừa khít khung 9:16 theo chiều ngang: tăng Thu phóng để dời được')}${thanhTT(c, 'khung.y', !th.doc, th.doc ? '' : 'Clip vừa khít khung 9:16 theo chiều dọc: tăng Thu phóng để dời được')}
      ${th.quayNgang ? '<p class="note giu"><b>Clip quay ngang</b>: kéo <b>Ngang</b> để chọn phần lấy (mặc định lấy giữa).</p>' : ''}<p class="note">${!th.ngang || !th.doc ? 'Clip vừa khung 9:16 theo ' + (!th.ngang && !th.doc ? 'cả 2 chiều' : !th.ngang ? 'chiều ngang' : 'chiều dọc') + ': tăng Thu phóng để dời được. ' : ''}Kéo thanh hoặc gõ số vào ô bên phải, khung xem đổi ngay.</p></div>
      <div class="box tt-box"><div class="row"><h2 class="sec grow">Chuyển động</h2><span class="note">${c.dong ? esc(tenGiaTri('chuyen_dong', c.dong)) : 'theo kiểu chung: ' + esc(tenNgan('chuyen_dong'))}</span></div>
        <div class="tv-chips">${chipTT('data-ttdong', '', 'Theo kiểu chung: ' + tenNgan('chuyen_dong'), !c.dong, {goi: 'Theo chuyển động cả video (tab Kiểu): ' + tenGiaTri('chuyen_dong', kieuDung('chuyen_dong'))})}${dsDongCanh().map(([v, t]) => chipTT('data-ttdong', v, t, c.dong === v)).join('')}</div></div>`
      + (dsHieuUngHinh().length ? `<div class="box tt-box"><div class="row"><h2 class="sec grow">Hiệu ứng hình</h2><span class="note">${c.hieu_ung ? esc(tenGiaTri('hieu_ung', c.hieu_ung)) : 'không có'}</span></div>
        <div class="tv-chips">${chipTT('data-tthinh', '', 'Không', !c.hieu_ung)}${dsHieuUngHinh().map(y => chipTT('data-tthinh', y.v, y.ten, c.hieu_ung === y.v, {nhan: y.dau_canh ? 'đầu cảnh' : ''})).join('')}</div></div>` : '');
  } else if (tab === 'am') {
    const ng = (S.plan.nguon || {})[c.file] || {}, am = amC(c), co = ng.co_tieng !== false;
    h += `<div class="box tt-box tt-am"><div class="row"><h2 class="sec grow">Tiếng clip</h2>
        <button type="button" class="btn small${am === 0 ? ' primary' : ''}" data-tt-a="tat-tieng" ${co ? '' : 'disabled'} aria-pressed="${am === 0}" data-tip="${am === 0 ? 'Bật lại tiếng gốc của cảnh này' : 'Tắt tiếng gốc của cảnh này'}">${icon(am === 0 ? 'tatLoa' : 'loa')}${am === 0 ? 'Bật tiếng lại' : 'Tắt tiếng'}</button></div>
      ${thanhTT(c, 'am', !co, co ? '' : 'Clip này không có tiếng')}
      ${!co ? '<p class="note giu">Clip này không có tiếng.</p>' : S.plan.giong ? '<p class="note giu">Video có giọng đọc AI: tiếng clip vốn được hạ còn 35%.</p>' : ''}
      <p class="note">Âm lượng tiếng gốc của clip, chỉ cảnh này. Thả tay là lưu (Ctrl+Z để bỏ). Trên 100%: nghe thử trong app tối đa 100%, bản xuất mới to hơn (app tự cân âm lượng cả video).</p></div>`;
  } else if (tab === 'mau') {
    const m = mauC(c);
    if (typeof hinhTuMau === 'function') h += hinhTuMau(c);   // Tự chỉnh màu (dev/_mod-hinh.js, 4/11)
    h += `<div class="box tt-box"><div class="row"><h2 class="sec grow">Chỉnh màu cảnh này</h2>
        <button type="button" class="btn small ghost" data-tt-a="mau-lai" ${mauMd(m) ? 'disabled' : ''} data-tip="Đặt lại màu cảnh này">${icon('datLai')}Đặt lại</button></div>
      ${thanhTT(c, 'mau.sang')}${thanhTT(c, 'mau.tuong_phan')}${thanhTT(c, 'mau.bao_hoa')}${thanhTT(c, 'mau.nhiet')}
      <p class="note">Màu máy thật: chỉnh nhẹ thôi kẻo khách thấy khác màu khi tới tiệm. Màu cả video ở tab Kiểu.</p></div>`;
    if (typeof hinhLocBox === 'function') h += hinhLocBox(c);   // Bộ lọc màu (dev/_mod-hinh.js, 4/11)
  } else {
    if (n < 2) h += `<div class="tt-trong tt-1canh">${icon('chuyenC')}<span><b>Video mới có 1 cảnh</b> nên chưa có chỗ nối. Đưa vạch đỏ tới chỗ muốn đổi cảnh rồi bấm Chia: cảnh 2 sẽ có ô chuyển cảnh vào.</span><button type="button" class="btn small primary" data-tt-a="chia" ${canhLuc(S.t) ? '' : 'disabled'} data-tip="Chia cảnh ở vạch đỏ (phím S)">${icon('chia')}Chia <kbd>S</kbd></button></div>`;   // r29 (soi L3)
    else if (i === 0) h += `<div class="tt-trong">${icon('chuyenC')}<span><b>Cảnh 1 mở đầu video</b>, không có chuyển cảnh vào.</span><button type="button" class="btn small" data-tt-nav="1">Cảnh 2${icon('phai')}</button></div>`;
    else h += `<div class="box tt-box"><div class="row"><h2 class="sec grow">Chuyển cảnh vào cảnh ${i + 1}</h2><span class="note">${c.chuyen ? esc(tenGiaTri('chuyen_canh', c.chuyen)) : 'theo kiểu chung: ' + esc(tenNgan('chuyen_canh'))}</span></div>
        <div class="tv-chips">${chipTT('data-ttchuyen', '', 'Theo kiểu chung: ' + tenNgan('chuyen_canh'), !c.chuyen, {goi: 'Theo kiểu cả video (tab Kiểu): ' + tenGiaTri('chuyen_canh', kieuDung('chuyen_canh'))})}${dsChuyenCanh().map(y => chipTT('data-ttchuyen', y.v, y.ten, c.chuyen === y.v, {nhan: y.cham ? 'chậm' : '', goi: y.cham ? CHAM_GOI : ''})).join('')}</div>
        <div class="row"><button type="button" class="btn small" data-tt-a="chuyen-het" ${c.chuyen ? '' : 'disabled'}>${icon('lop')}Áp cho mọi cảnh</button><span class="note grow">Xem trước từng kiểu: Thư viện › Chuyển cảnh (rê chuột vào ô).</span></div></div>`;
  }
  h += pr;
  // danh sách cảnh cũ: thu gọn bên dưới (timeline đã có đủ cảnh)
  const nThem = `<button type="button" class="btn small ghost ds-them" data-a="them" data-tip="Chọn clip làm cảnh mới, đặt ngay sau cảnh ${i + 1}">${icon('them')}<span>Thêm cảnh</span></button>`;
  if (n < 2) return h + `<div class="ds-canh ds-1">${nThem}</div>`;
  h += `<details class="ds-canh"${S.dsMo ? ' open' : ''}><summary><span class="ds-t">Tất cả cảnh <span class="count">${n}</span></span>${nThem}</summary><div class="ds-in">` + b.map(y => { const z = y.c, sel = z._id === S.sel.canh;
    return `<div class="sc${sel ? ' sel' : ''}" data-canh="${z._id}"><div class="th" style="background-image:url('${thumbUrl(src(z.file), (z.tu + z.den) / 2)}')"></div>
      <div class="sc-t" data-tip="Từ ${tg(y.a)} · ${esc(base(z.file))}"><b>Cảnh ${y.i + 1}</b><small>${esc(z.mo_ta || base(z.file))}</small></div><span class="sc-dai">${gs(z.den - z.tu)}</span>
      <div class="acts"><button type="button" class="btn small icon ghost" data-a="len" aria-label="Đưa cảnh ${y.i + 1} lên trước" data-tip="Đưa lên trước" ${y.i ? '' : 'disabled'}>${icon('len')}</button><button type="button" class="btn small icon ghost" data-a="xuong" aria-label="Đưa cảnh ${y.i + 1} xuống sau" data-tip="Đưa xuống sau" ${y.i < n - 1 ? '' : 'disabled'}>${icon('xuong')}</button></div></div>`; }).join('')
    + `</div></details>`;
  return h;
}
/* ---------- bấm / kéo trong bảng ---------- */
function canhDangChon() { return S.plan.canh.find(c => c._id === S.sel.canh) || S.plan.canh[0]; }
function vaoCanh(id) {   // vạch đỏ chưa nằm trong cảnh đang chỉnh: đưa vào để khung xem cho thấy ngay
  const x = bocCanh().find(y => y.c._id === id); if (!x) return;
  if (S.t < x.a || S.t >= x.b - 0.02) { dung(); tua(x.bd + Math.min(0.4, (x.b - x.bd) / 2)); giuVach(); }
}
$('#pane').addEventListener('click', e => {
  const t = e.target.closest('button'); if (!t || t.disabled || !S.plan) return;
  const c = canhDangChon(); if (!c) return;
  if (t.dataset.tttab) { S.tabCanh = t.dataset.tttab; try { localStorage.setItem('st-tab-canh', S.tabCanh); } catch (x) {} return veBen(true); }
  if (t.dataset.ttNav) { const b = bocCanh(), i = b.findIndex(y => y.c._id === c._id) + +t.dataset.ttNav, y = b[i]; if (!y) return; S.sel.canh = y.c._id; S.selLoai = 'canh'; dung(); tua(y.bd + 0.02); giuVach(); veBen(true); veTimeline(); return; }
  if (t.dataset.ttdong != null) return datHieuUng(c._id, 'dong', t.dataset.ttdong || null);
  if (t.dataset.tthinh != null) return datHieuUng(c._id, 'hieu_ung', t.dataset.tthinh || null);
  if (t.dataset.ttchuyen != null) return datHieuUng(c._id, 'chuyen', t.dataset.ttchuyen || null);
  if (t.dataset.ttLai) { const f = t.dataset.ttLai, md = f === 'khung.zoom' || f === 'am' ? 100 : 0, g = ttGiaTri(c, f, md); vaoCanh(c._id); return datTT(c._id, g.khoa, g.gt); }
  const a = t.dataset.ttA;
  if (a === 'giua') { const k = khungC(c); k.x = 0; k.y = 0; vaoCanh(c._id); return datTT(c._id, 'khung', khungMd(k) ? null : k); }
  if (a === 'khung-lai') { vaoCanh(c._id); return datTT(c._id, 'khung', null); }
  if (a === 'mau-lai') { vaoCanh(c._id); return datTT(c._id, 'mau', null); }
  if (a === 'tat-tieng') { const am = amC(c); if (am > 0) { S.amCu[c._id] = am; datTT(c._id, 'am_luong', 0); toast('Đã tắt tiếng cảnh ' + (S.plan.canh.indexOf(c) + 1) + ' (Ctrl+Z để bỏ)'); }
    else { const v = S.amCu[c._id] || 1; datTT(c._id, 'am_luong', v === 1 ? null : v); } return; }
  if (a === 'chuyen-het') return datHieuUng(c._id, 'chuyen', c.chuyen, true);
  if (a === 'chia') { chiaCanh(); const b = bocCanh()[1]; if (b) { S.sel.canh = b.c._id; S.selLoai = 'canh'; veBen(true); veTimeline(); } return; }   // r29 (L3): video 1 cảnh -> chia rồi chọn cảnh 2
});
$('#pane').addEventListener('toggle', e => { if (e.target.matches && e.target.matches('details.ds-canh')) { S.dsMo = e.target.open; try { localStorage.setItem('st-ds-canh', S.dsMo ? '1' : ''); } catch (x) {} } }, true);
let ttPhim = false;
$('#pane').addEventListener('pointerdown', e => { const r = e.target.closest('[data-tt]'); if (r && !r.disabled) { ttPhim = false; vaoCanh(canhDangChon()._id); } });
$('#pane').addEventListener('keydown', e => {   // phím mũi tên trên thanh kéo: chỉnh thanh, đừng để phím tắt timeline (← → tua) ăn mất
  const r = e.target.closest && e.target.closest('input[data-tt]'); if (!r) return;
  if (/^(Arrow|Page|Home|End)/.test(e.key)) { ttPhim = true; e.stopPropagation(); if (!e.repeat) vaoCanh(canhDangChon()._id); }
});
$('#pane').addEventListener('input', e => {
  const r = e.target.closest && e.target.closest('input[data-tt]'); if (!r) return;
  const c = canhDangChon(), f = r.dataset.tt, v = +r.value, d = TT[f]; if (!c || !d) return;
  const o = $(`#pane [data-tt-ra="${f}"]`); if (o) o.value = d.nhan(v);   // ô số (input) / output cũ đều có .value
  r.style.cssText = ttDai(d, v);
  const g = ttGiaTri(c, f, v); S.tam = {id: c._id, khoa: g.khoa, gt: g.gt};
  if (!S.playing) veKhung(true); else apAmLuongNgay();
});
$('#pane').addEventListener('change', e => {
  const r = e.target.closest && e.target.closest('input[data-tt]'); if (!r) return;
  const c = canhDangChon(), f = r.dataset.tt; if (!c || !TT[f]) return;
  const g = ttGiaTri(c, f, +r.value), kb = ttPhim;
  datTT(c._id, g.khoa, g.gt, kb ? 'tt:' + c._id + ':' + f : undefined);   // kéo chuột: mỗi lần thả = 1 bước Ctrl+Z; phím: gộp bước liền nhau
  if (kb) setTimeout(() => { const x = $(`#pane input[data-tt="${f}"]`); if (x && document.activeElement !== x) x.focus(); }, 0);
});
function apAmLuongNgay() { const d = doanLuc(S.t); if (!d) return; const el = typeof vidDoan === 'function' ? vidDoan(d) : VID[src(d.file)]; if (el && !el.paused) el.volume = clamp((S.plan.giong ? (S.plan.giong.thay_tieng ? 0 : 0.35) : 1) * ttDoan(d).am, 0, 1); }

/* ---------- khung xem: khung tĩnh + màu + âm lượng của đoạn đang phát ---------- */
function ttDoan(d) {   // S.tam (đang kéo) > kế hoạch (theo id cảnh) > máy chủ (đoạn mở đầu montage…)
  const c = d && d.id ? S.plan.canh.find(x => x._id === d.id) : null, g = c || d || {};
  let kh = khungC(g), mau = mauC(g), am = amC(g), loc = typeof locC === 'function' ? locC(g) : null;
  if (S.tam && d && d.id && S.tam.id === d.id) {
    if (S.tam.khoa === 'khung') kh = khungC({khung: S.tam.gt}); else if (S.tam.khoa === 'mau') mau = mauC({mau: S.tam.gt});
    else if (S.tam.khoa === 'loc') loc = locC({loc: S.tam.gt}); else am = amC({am_luong: S.tam.gt});
  }
  mau.loc = loc;   // bộ lọc màu LUT (dev/_mod-hinh.js, 4/11) đi cùng màu tới hinhVideo
  return {kh, mau, am};
}
function kRgb(k) {   // màu ánh sáng theo độ K (xấp xỉ Tanner Helland, cùng cách colortemperature của ffmpeg)
  const t = k / 100; let r, g, b;
  if (t <= 66) { r = 255; g = 99.4708025861 * Math.log(t) - 161.1195681661; b = t <= 19 ? 0 : 138.5177312231 * Math.log(t - 10) - 305.0447927307; }
  else { r = 329.698727446 * Math.pow(t - 60, -0.1332047592); g = 288.1221695283 * Math.pow(t - 60, -0.0755148492); b = 255; }
  return [r, g, b].map(x => clamp(x, 0, 255) / 255);
}
function matranMau(m) {   // eq (độ sáng / tương phản theo độ sáng điểm ảnh, độ đậm màu) rồi nhiệt màu -> 1 ma trận feColorMatrix
  const s = m.bao_hoa, c = m.tuong_phan, b = m.sang * 1.16, w = [0.299, 0.587, 0.114], t = kRgb(m.nhiet), t0 = kRgb(6500);
  const off = 0.5 - 0.5 * c + b;
  return [0, 1, 2].map(i => { const k = t[i] / t0[i]; return [0, 1, 2].map(j => (k * ((i === j ? s : 0) + (c - s) * w[j])).toFixed(4)).concat(['0', (k * off).toFixed(4)]).join(' '); }).join(' ') + ' 0 0 0 1 0';
}
let mauCu = '';
function locMau(m) { const v = matranMau(m); if (v !== mauCu) { mauCu = v; const x = $('#stMauM'); if (x) x.setAttribute('values', v); } return 'url(#stMau)'; }
function hinhVideo(el, Z, X, kh, mau, mo) {   // Z / X: chuyển động (zoom / lia) như cũ; kh: khung tĩnh (crop lệch) ÁP TRƯỚC chuyển động, như bộ dựng
  if (khungMd(kh)) { el.style.objectPosition = ''; el.style.transformOrigin = ''; el.style.transform = `scale(${Z}) translateX(${-X * 100}%)`; }
  else {
    const f = (0.5 + 0.5 * kh.x) * 100, g = (0.5 + 0.5 * kh.y) * 100;
    el.style.objectPosition = `${f}% ${g}%`; el.style.transformOrigin = '0 0';
    el.style.transform = `translate(50%,50%) scale(${Z}) translateX(${-X * 100}%) translate(-50%,-50%) translate(${f}%,${g}%) scale(${kh.zoom}) translate(${-f}%,${-g}%)`;
  }
  el.style.filter = [mo ? 'blur(14px) brightness(.85)' : '', mauMd(mau) ? '' : locMau(mau), mau.loc && typeof locLut === 'function' ? locLut(mau.loc) : ''].filter(Boolean).join(' ');
}
document.body.insertAdjacentHTML('beforeend', '<svg class="tv-svg" width="0" height="0" aria-hidden="true" focusable="false"><filter id="stMau" color-interpolation-filters="sRGB" x="0" y="0" width="1" height="1"><feColorMatrix id="stMauM" type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 1 0"/></filter></svg>');

/* ---------- dấu trên khối cảnh (timeline): hiệu ứng hình ✦, chuyển động, âm lượng, khung, màu ---------- */
function dauCanh(c) {
  const am = amC(c), coK = c.khung && !khungMd(khungC(c)), coM = (c.mau && !mauMd(mauC(c))) || !!(c.loc && c.loc.ten), d = [];   // + bộ lọc màu (4/11)
  if (am !== 1) d.push(`<span class="hu-a${am === 0 ? ' tat' : ''}" title="${am === 0 ? 'Đã tắt tiếng' : 'Âm lượng ' + Math.round(am * 100) + '%'}">${icon(am === 0 ? 'tatLoa' : 'loa')}</span>`);
  if (coK) d.push(`<span class="hu-k" title="Khung riêng: thu phóng ${Math.round(khungC(c).zoom * 100)}%">${icon('catKhung')}</span>`);
  if (coM) d.push(`<span class="hu-k" title="Màu riêng">${icon('giotMau')}</span>`);
  if (c.on_dinh) d.push(`<span class="hu-k hu-od" title="Chống rung">${icon('chongRung')}</span>`);   // 4/11 tối (dev/_mod-chong-rung.js)
  if (c.hieu_ung) d.push(`<span class="hu-h" title="Hiệu ứng hình: ${esc(tenGiaTri('hieu_ung', c.hieu_ung))}">✦</span>`);
  if (c.dong) d.push(`<span class="hu-d" title="Chuyển động: ${esc(tenGiaTri('chuyen_dong', c.dong))}">${c.dong === 'zoom_ra' ? '⤡' : c.dong === 'dung_yen' ? '■' : c.dong.startsWith('lia') ? '⇆' : '⤢'}</span>`);
  return d.length ? `<span class="hu-w">${d.join('')}</span>` : '';
}
