/* ============================== GIỌNG AI ĐỌC LẠI KHỐI TIẾNG TÁCH (r32, 10/11 17:07) ==============================
   Anh: "cho đè giọng đọc ai trên file âm thanh tách ra, không cần viết chữ".
   Chuột phải khối tiếng tách (hoặc cảnh đã tách, hoặc nhóm cảnh quét chọn) › "Đọc lại bằng giọng AI…" (bảng phải của khối cũng có nút):
   app lấy lời trong khối — câu phụ đề đã có (chữ anh đã sửa + giờ của câu), khối chưa có phụ đề thì máy nghe riêng khối đó (sherpa +
   từ điển tiệm, chia câu như "Tạo phụ đề từ lời nói") -> hộp nhỏ: giọng (giọng phổ biến, nhớ lần trước), tốc độ, "Giữ tiếng gốc làm nền",
   danh sách câu sửa được (không bắt buộc) -> Tạo giọng (máy chủ giong_de.py: mỗi câu 1 file, câu dài hơn chỗ trống tới câu sau thì
   tăng tốc giữ cao độ tối đa 1,25×, vẫn dài thì báo tràn) -> nghe thử -> Áp vào video = 1 bước Ctrl+Z.
   Kế hoạch: plan.giong_de = {cau: [{chu, nguon, goc, s0, s1, local, giay, toc, giong, ten, toc_do}], vung: [{nguon, goc, tu, den, nen}]}
   (engine/doc_lai.py): câu giọng bắt đầu đúng giờ câu gốc, ĐI THEO KHỐI tách (dời / cắt / xoá khối thì giọng theo, như phụ đề _neo.am);
   tiếng gốc trong vùng đọc lại tắt hẳn (nen 0) hoặc còn 15%. Phụ đề giữ chữ, giờ khớp giọng mới (câu chưa có phụ đề thì thêm).
   Làn Giọng: mỗi câu 1 thanh đúng giờ (đè câu sau thì mép đỏ). Khung xem phát giọng bằng Web Audio theo vạch đỏ (như khối tách).
   Giọng gõ lời cũ (plan.giong) vẫn chạy y nguyên; có cả 2 thì cả 2 cùng phát (giọng gõ lời liền từ đầu, giọng đọc lại đúng chỗ từng câu).
   Mô-đun bọc hàm sẵn có (menuKhoi, mucTachCanh, benKhoi, moMenu, veTimeline, veKhung, dung); 1 dòng trong _mod-tach-am.js (taKhung: gdNen). */
const GD = {buf: {}, au: {}, hop: null, dat: null, datKhoa: ''};
const GD_NEN = 0.15;   // "Giữ tiếng gốc làm nền": tiếng gốc còn ~15 %
const gdDoc = (k, md) => { try { const v = localStorage.getItem(k); return v == null ? md : v; } catch (e) { return md; } };
const gdGhi = (k, v) => { try { localStorage.setItem(k, v); } catch (e) {} };
const gdSo = (v, m) => (v == null || v === '' || !isFinite(+v)) ? m : +v;
function gdObj() { const g = S.plan && S.plan.giong_de; return g && typeof g === 'object' ? g : null; }
function gdCau() { const g = gdObj(); return g && Array.isArray(g.cau) ? g.cau : []; }
function gdVung() { const g = gdObj(); return g && Array.isArray(g.vung) ? g.vung : []; }
function gdKhoiDs(p) { return ((p || S.plan || {}).am_tach || []).filter(k => k && typeof k.nguon === 'string' && gdSo(k.tu, -1) >= 0 && gdSo(k.den, -1) - gdSo(k.tu, -1) >= 0.05); }

/* ---------- đặt câu giọng lên video (= engine/doc_lai.dat, để vẽ / phát ngay lúc kéo khối, không chờ máy chủ) ---------- */
function gdDatTu(cau, ks, T) {
  const out = [];
  cau.forEach((c, i) => {
    const s0 = gdSo(c.s0, -1), s1 = gdSo(c.s1, -1), giay = gdSo(c.giay, 0);
    if (!c.local || s0 < 0 || s1 <= s0 || giay < 0.1) return;
    let best = null;
    for (const k of ks) {
      if (k.nguon !== c.nguon || (c.goc && k.goc !== c.goc)) continue;
      const a = +k.tu, b = +k.den, ov = Math.min(s1, b) - Math.max(s0, a);
      let diem;
      if (a - 0.02 <= s0 && s0 < b - 0.05) diem = 1000 + ov; else if (ov >= Math.max(0.15, 0.4 * (s1 - s0))) diem = ov; else continue;
      if (!best || diem > best.diem) best = {diem, k, a, b, t: gdSo(k.t, 0)};
    }
    if (!best) return;
    const {k, a, b, t} = best;
    let tv = t + Math.max(s0, a) - a, dai = giay, off = 0, cat = false;
    if (b < s1 - 0.05 && t + b - a - tv < dai) { dai = t + b - a - tv; cat = true; }
    if (tv < 0) { off = -tv; dai += tv; tv = 0; }
    if (T) { if (tv >= T - 0.05) return; if (tv + dai > T) { dai = T - tv; cat = true; } }
    if (dai < 0.1) return;
    out.push({i, t: r3(tv), dai: r3(dai), off: r3(off), cat, chu: String(c.chu || ''), khoi: k.id, local: c.local});
  });
  out.sort((x, y) => x.t - y.t || x.i - y.i);
  out.forEach((x, j) => { const n = out[j + 1]; x.tran = n && x.t + x.dai - n.t > 0.05 ? r3(x.t + x.dai - n.t) : 0; });
  return out;
}
function gdDat() {   // nhớ theo nội dung (gọi mỗi khung lúc phát)
  if (!S.plan || !gdCau().length) return [];
  const T = (S.view || {}).T || tongT(), khoa = JSON.stringify([gdCau(), gdKhoiDs().map(k => [k.id, k.goc, k.nguon, k.tu, k.den, k.t]), Math.round(T * 100)]);
  if (khoa !== GD.datKhoa) { GD.datKhoa = khoa; GD.dat = gdDatTu(gdCau(), gdKhoiDs(), T); }
  return GD.dat;
}
window.gdDatXem = gdDat;   // (để kiểm thử)
function gdNen(k, s) {   // khối tách k đang phát giây s của clip: nằm trong vùng đọc lại -> mức tiếng gốc còn lại (gọi từ taKhung)
  for (const v of gdVung()) if (v.nguon === k.nguon && (!v.goc || v.goc === k.goc) && s >= +v.tu - 1e-3 && s < +v.den) return clamp(gdSo(v.nen, 0), 0, 1);
  return 1;
}
function gdCuaKhoi(k) {   // các câu giọng đang thuộc khối k
  return gdDat().filter(x => x.khoi === k.id);
}
function gdVungKhoi(k) { return gdVung().filter(v => v.nguon === k.nguon && (!v.goc || v.goc === k.goc) && Math.min(+v.den, +k.den) - Math.max(+v.tu, +k.tu) > 0.01); }
function gdCoKhoi(k) { return !!k && (gdCuaKhoi(k).length > 0 || gdVungKhoi(k).length > 0); }

/* ---------- khối đang chọn: nhóm quét chọn (QUET.nhom: các cảnh đã tách -> khối của chúng) + khối / cảnh bấm phải ---------- */
function gdKhoiCuaCanh(ids) {
  const gocs = new Set(S.plan.canh.filter(c => ids.includes(c._id) && c.tach_am).map(c => c.tach_am));
  return taDs().filter(k => gocs.has(k.goc)).map(k => k.id);
}
function gdNhom() { if (window.QUET && S.quet) { const n = QUET.nhom(); if (n.canh.length >= 1 && n.canh.length + n.k.length >= 2) return gdKhoiCuaCanh(n.canh); } return []; }
function gdChonKhoi(id) { const nh = gdNhom(); return nh.length && nh.includes(id) ? nh : [id]; }

/* ---------- lấy lời: câu phụ đề đã có trong khối, chưa có thì nghe khối ---------- */
function gdCauPhuDe(ks) {
  const gio = (S.view || {}).gio || {}, da = new Set(), out = [], trong = [];
  for (const k of ks) {
    const L = +k.den - +k.tu, ds = [];
    for (const it of S.plan.phu_de || []) {
      const n = it._neo; if (!n || da.has(it._k) || it._an || n.file !== k.nguon || !String(it.chu || '').trim()) continue;
      const s0 = +n.s0, s1 = +n.s1, ov = Math.min(s1, +k.den) - Math.max(s0, +k.tu);
      if (!(ov > 0.05 && ov >= 0.5 * (s1 - s0))) continue;
      const g = gio[it._k]; if (g && !g.an && g.t0 != null && (g.t0 < +k.t - 0.3 || g.t0 > +k.t + L + 0.3)) continue;   // câu đang hiện ở khối khác cùng clip
      da.add(it._k); ds.push({k: it._k, chu: String(it.chu).replace(/\|/g, ' ').replace(/\s+/g, ' ').trim(), nguon: k.nguon, goc: k.goc, khoi: k.id, s0: r3(s0), s1: r3(s1)});
    }
    if (ds.length) out.push(...ds); else trong.push(k);
  }
  return {cau: out, trong};
}
function gdT(c) { const k = taKhoi(c.khoi); return k ? +k.t + Math.max(c.s0, +k.tu) - +k.tu : 0; }
function gdCho(ds, ks) {   // chỗ trống của từng câu (giây trên video): tới câu sau (câu mới / câu giọng khác đang có), không quá cuối khối
  const khac = gdDat().filter(x => !ks.some(k => k.id === x.khoi)).map(x => x.t);
  const tt = ds.map(gdT), het = ds.map(c => { const k = taKhoi(c.khoi); return k ? +k.t + +k.den - +k.tu : Infinity; });
  return ds.map((c, i) => { let n = het[i]; tt.forEach((t, j) => { if (j !== i && t > tt[i] + 0.02) n = Math.min(n, t); }); khac.forEach(t => { if (t > tt[i] + 0.02) n = Math.min(n, t); });
    return r3(Math.max(0.2, n - tt[i])); });
}

/* ---------- hộp "Đọc lại bằng giọng AI" ---------- */
async function moDocLai(ids) {
  if (!S.plan || $('#edit').hidden) return;
  dung();
  const ks = [...new Set(ids)].map(taKhoi).filter(Boolean).sort((a, b) => a.t - b.t);
  if (!ks.length) return toast('Chọn 1 khối tiếng tách trước (chuột phải cảnh › Tách âm thanh)', true);
  if (typeof window.ranh === 'function' && !window.ranh() && typeof choRanh === 'function') await choRanh(6000);   // giờ câu phụ đề mới nhất
  const {m, dong} = modal('<div id="gdHop"></div>');
  m.classList.add('gde-hop');
  const H = GD.hop = {v: S.v, el: $('#gdHop', m), dong, ks: ks.map(k => k.id), cau: [], dang: 'lay', loi: '', kq: null, tt: null,
    giong: gdDoc('gd-giong', ''), toc: gdDoc('gd-toc', '+10%'), nen: false, phuDe: true, buoc: '', giay: 0,
    phong: gdDoc('gd-phong', '') || null, kieu: gdDoc('gd-kieu', '') || null};   // phong / kieu: kiểu trend (r39, _mod-giong-trend.js)
  m.addEventListener('click', gdBam); m.addEventListener('input', gdGo); m.addEventListener('change', gdDoi);
  try { await napGiongDs(); } catch (e) { H.loi = e.message; }
  if (!GA.ds) { H.el.innerHTML = `<h3>Đọc lại bằng giọng AI</h3><p class="note err giu">${esc(H.loi || 'Không tải được danh sách giọng')}</p><div class="acts"><button type="button" class="btn" data-dong>Đóng</button></div>`; GD.hop = null; return; }
  if (!H.giong || !GA.ds.ds.some(x => x.id === H.giong)) H.giong = GA.ds ? GA.ds.mac_dinh : 'vn-adam';
  if (!GA.ds.toc.some(x => x.v === H.toc)) H.toc = '+10%';
  if (H.phong && !(GA.ds.phong || []).some(x => x.id === H.phong)) H.phong = null;
  if (H.kieu && !(GA.ds.trend || []).some(x => x.id === H.kieu)) H.kieu = null;
  const {cau, trong} = gdCauPhuDe(ks);
  H.cau = cau; gdVe();
  if (trong.length) await gdNghe(H, trong); else { H.dang = ''; gdSapXep(H); gdVe(); }
}
function gdSapXep(H) { H.cau.sort((a, b) => gdT(a) - gdT(b)); const ks = H.ks.map(taKhoi).filter(Boolean); const cho = gdCho(H.cau, ks); H.cau.forEach((c, i) => { c.cho = cho[i]; }); }
async function gdNghe(H, trong) {
  H.dang = 'nghe'; H.buoc = 'Đang nghe lời trong ' + (trong.length > 1 ? trong.length + ' khối' : 'khối') + '…'; gdVe();
  try {
    const r = await api('/api/sua-tay/giong-de/nghe', {v: S.v, plan: S.plan, khoi: trong.map(k => k.id)});
    for (;;) {
      await new Promise(f => setTimeout(f, 900));
      if (GD.hop !== H) return;
      const s = await api('/api/sua-tay/nghe?ma=' + encodeURIComponent(r.ma));
      if (s.dang) { H.buoc = s.buoc || H.buoc; H.giay = s.giay_da || 0; gdVeTT(); continue; }
      if (!s.kq) throw new Error(s.loi || 'Máy nghe bị lỗi');
      for (const x of s.kq.phu_de || []) {
        const n = x._neo || {}, k = trong.find(k => k.nguon === n.file && +n.s0 >= +k.tu - 0.05 && +n.s0 < +k.den) || trong.find(k => k.nguon === n.file);
        if (k && String(x.chu || '').trim()) H.cau.push({k: null, chu: String(x.chu).trim(), nguon: k.nguon, goc: k.goc, khoi: k.id, s0: r3(+n.s0), s1: r3(+n.s1), id: n.id});
      }
      break;
    }
    H.dang = '';
    if (!H.cau.length) H.loi = 'Không nghe ra lời nói trong khối này (chỉ có tiếng ồn / nhạc?)';
  } catch (e) { if (GD.hop !== H) return; H.dang = ''; H.loi = e.message; }
  gdSapXep(H); gdVe();
}
function gdOpt(H) {
  const ds = GA.ds.ds, pb = x => GIONG_PHO_BIEN.indexOf(x.id) >= 0, hang = x => GIONG_PHO_BIEN.indexOf(x.id);
  const nhom = [['Đang chọn', x => x.id === H.giong && !pb(x)], ['Giọng nam · chạy trên máy', x => pb(x) && x.nguon === 'vieneu' && x.gioi === 'nam'],
    ['Giọng nữ · chạy trên máy', x => pb(x) && x.nguon === 'vieneu' && x.gioi !== 'nam'], ['Microsoft · cần mạng', x => pb(x) && x.nguon === 'microsoft']];
  const da = new Set();
  return nhom.map(([t, f]) => { const xs = ds.filter(x => !da.has(x.id) && f(x)).sort((a, b) => hang(a) - hang(b)); xs.forEach(x => da.add(x.id));
    return xs.length ? `<optgroup label="${esc(t)}">${xs.map(x => `<option value="${esc(x.id)}"${x.id === H.giong ? ' selected' : ''}>${esc(x.ten)} · ${esc([x.nguon === 'microsoft' ? x.gioi : '', x.mien].filter(Boolean).join(', '))}</option>`).join('')}</optgroup>` : ''; }).join('');
}
function gdTom(H) {
  const ks = H.ks.map(taKhoi).filter(Boolean);
  if (!ks.length) return '';
  const t0 = Math.min(...ks.map(k => +k.t)), t1 = Math.max(...ks.map(k => +k.t + +k.den - +k.tu));
  return (ks.length > 1 ? ks.length + ' khối tiếng tách' : 'Tiếng tách ' + taTen(ks[0])) + ' · ' + tg(t0) + ' – ' + tg(t1) + (H.cau.length ? ' · ' + H.cau.length + ' câu' : '');
}
function gdTT(c, kq) {   // trạng thái 1 câu sau khi tạo
  if (!kq) return '';
  if (kq.bo) return '<span class="gde-tt dim">bỏ</span>';
  if (kq.tran) return `<span class="gde-tt tran" data-tip="Giọng dài hơn chỗ trống tới câu sau ${gs(kq.tran)} dù đã nói nhanh ${String(kq.toc).replace('.', ',')}×: sẽ đè lên câu sau. Sửa chữ ngắn lại rồi Tạo lại">tràn ${gs(kq.tran)}</span>`;
  if (kq.toc > 1) return `<span class="gde-tt nhanh" data-tip="Giọng dài hơn chỗ trống tới câu sau: đã nói nhanh hơn ${String(kq.toc).replace('.', ',')} lần (giữ cao độ)">nhanh ×${String(kq.toc).replace('.', ',')}</span>`;
  return '<span class="gde-tt vua">vừa</span>';
}
function gdVe() {
  const H = GD.hop; if (!H || !H.el.isConnected) { GD.hop = null; return; }
  const kq = H.kq, dang = H.dang, n = H.cau.length, tran = kq ? kq.cau.filter(x => x.tran).length : 0, nhanh = kq ? kq.cau.filter(x => !x.tran && x.toc > 1).length : 0;
  const gi = S.plan.giong && S.plan.giong.local;
  H.el.innerHTML = `<h3>Đọc lại bằng giọng AI</h3>
    <p class="note gde-tom">${esc(gdTom(H))}${tvI('App lấy lời trong khối (câu phụ đề đã có, chưa có thì máy tự nghe), giọng AI đọc lại từng câu bắt đầu đúng giờ câu gốc, thay tiếng gốc. Dời / cắt / xoá khối thì giọng đi theo. Phụ đề giữ chữ, giờ theo giọng mới.')}</p>
    ${gi ? `<p class="note giu gde-canh">Video đang có giọng AI gõ lời (chạy liền từ đầu): 2 giọng sẽ cùng phát, chỗ trùng giờ nghe chồng.${tvI('Muốn chỉ giọng đọc lại: Thư viện › Giọng AI › Bỏ giọng AI.')}</p>` : ''}
    <div class="gde-cai">
      ${typeof gtVe === 'function' ? gtVe('gd') : `<span class="lbl">Giọng</span><span class="gde-g"><select class="inp gde-giong" aria-label="Giọng đọc">${gdOpt(H)}</select><button type="button" class="btn small" data-gd="thu" data-tip="Nghe 1 câu mẫu bằng giọng + tốc độ đang chọn">${icon('play')}Nghe thử</button></span>`}
      <span class="lbl">Tốc độ</span><span class="seg2 gde-toc">${GA.ds.toc.map(x => `<button type="button" data-toc="${esc(x.v)}" class="${x.v === H.toc ? 'on' : ''}">${esc(x.ten)}</button>`).join('')}</span>
      <span></span><span class="gde-chk"><label><input type="checkbox" data-gd="nen"${H.nen ? ' checked' : ''}> Giữ tiếng gốc làm nền</label>${tvI('Tắt (mặc định): tiếng gốc trong khối tắt hẳn, chỉ còn giọng AI. Bật: tiếng gốc còn khoảng 15 % làm nền (tiếng phòng, tiếng máy).')}
        <label><input type="checkbox" data-gd="pd"${H.phuDe ? ' checked' : ''}> Thêm phụ đề cho câu chưa có</label></span>
    </div>
    <div class="gde-ds" role="list">${dang === 'lay' ? '<p class="note">Đang lấy lời trong khối…</p>'
      : dang === 'nghe' && !n ? `<p class="note gde-cho"><span class="gde-quay"></span><span class="gde-buoc">${esc(H.buoc)}</span> <span class="gde-giay">${H.giay ? tg(H.giay, false) : ''}</span></p>`
      : !n ? `<p class="note ${H.loi ? 'err' : ''}">${esc(H.loi || 'Không có câu nào')}</p>`
      : H.cau.map((c, i) => { const x = kq && kq.cau[i]; return `<div class="gde-c${x && x.tran ? ' tran' : ''}" role="listitem" data-i="${i}">
        <span class="gde-so">${i + 1}</span><button type="button" class="gde-gio" data-gd="tua" data-i="${i}" data-tip="Tua tới câu này">${tg(gdT(c))}</button>
        <input class="inp gde-chu" data-i="${i}" value="${esc(c.chu)}" spellcheck="false" aria-label="Lời câu ${i + 1}">
        ${x && x.url ? `<button type="button" class="btn small icon ghost" data-gd="nghe1" data-i="${i}" aria-label="Nghe câu ${i + 1}" data-tip="Nghe câu này">${icon('play')}</button>` : '<span class="gde-tt-o"></span>'}${gdTT(c, x)}</div>`; }).join('')}</div>
    ${dang === 'nghe' && n ? `<p class="note gde-cho"><span class="gde-quay"></span><span class="gde-buoc">${esc(H.buoc)}</span> <span class="gde-giay"></span></p>` : ''}
    ${H.tt && H.tt.dang ? `<p class="note gde-cho"><span class="gde-quay"></span><span class="gde-buoc">${esc(H.tt.buoc || 'Đang tạo giọng…')}</span> <span class="gde-giay">${tg(H.tt.giay_da || 0, false)}</span>${tvI('Lần đầu giọng VieNeu nạp mất khoảng nửa phút. Vẫn sửa video được trong lúc chờ.')}</p>` : ''}
    ${H.loi && n ? `<p class="note err giu">${esc(H.loi)}</p>` : ''}
    ${kq ? `<p class="note gde-kq${tran ? ' warnt' : ''}">Giọng <b>${esc(kq.ten || '')}</b>: ${kq.cau.filter(x => x.local).length} câu${nhanh ? ' · ' + nhanh + ' câu nói nhanh hơn cho vừa chỗ' : ''}${tran ? ' · <b>' + tran + ' câu tràn</b> sang câu sau (đỏ bên trên)' : ' · vừa chỗ'}</p>` : ''}
    <div class="acts"><button type="button" class="btn" data-dong>Đóng</button>
      ${kq ? `<button type="button" class="btn" data-gd="nghe-het" data-tip="Nghe cả đoạn giọng mới theo đúng giờ từng câu">${icon('play')}Nghe cả đoạn</button>` : ''}
      <button type="button" class="btn${kq ? '' : ' primary'}" data-gd="tao"${!n || dang || (H.tt && H.tt.dang) ? ' disabled' : ''}>${kq ? 'Tạo lại' : 'Tạo giọng'}</button>
      <button type="button" class="btn primary" data-gd="ap"${kq ? '' : ' disabled'} data-tip="${kq ? 'Giọng AI thay tiếng gốc ở ' + (H.ks.length > 1 ? H.ks.length + ' khối' : 'khối') + ' này, phụ đề theo giọng mới. Ctrl+Z để bỏ' : 'Bấm Tạo giọng trước'}">Áp vào video</button></div>`;
}
function gdVeTT() {   // chỉ cập nhật dòng chờ (không vẽ lại ô gõ)
  const H = GD.hop; if (!H || !H.el.isConnected) return;
  const b = $('.gde-buoc', H.el), g = $('.gde-giay', H.el);
  if (b) b.textContent = (H.tt && H.tt.dang ? H.tt.buoc : H.buoc) || '';
  if (g) g.textContent = tg((H.tt && H.tt.dang ? H.tt.giay_da : H.giay) || 0, false);
}
function gdGo(e) {
  const H = GD.hop, o = e.target.closest && e.target.closest('input.gde-chu'); if (!H || !o) return;
  const c = H.cau[+o.dataset.i]; if (!c) return;
  c.chu = o.value;
  if (H.kq) { H.kq = null; gdVe(); const o2 = $(`input.gde-chu[data-i="${o.dataset.i}"]`, H.el); if (o2) { o2.focus(); o2.setSelectionRange(o2.value.length, o2.value.length); } }
}
function gdDoi(e) {
  const H = GD.hop; if (!H) return;
  if (e.target.matches('select.gde-giong')) { H.giong = e.target.value; H.phong = H.kieu = null; gdGhi('gd-giong', H.giong); if (H.kq) { H.kq = null; gdVe(); } }
  else if (e.target.matches('[data-gd="nen"]')) H.nen = e.target.checked;
  else if (e.target.matches('[data-gd="pd"]')) H.phuDe = e.target.checked;
}
function gdBam(e) {
  const H = GD.hop; if (!H) return;
  const tb = e.target.closest('[data-toc]'); if (tb) { H.toc = tb.dataset.toc; gdGhi('gd-toc', H.toc); H.kq = null; return gdVe(); }
  const b = e.target.closest('button[data-gd]'); if (!b || b.disabled) return;
  const a = b.dataset.gd, i = +b.dataset.i;
  if (a === 'thu') return gdThuGiong(b, H);
  if (a === 'tao') return gdTao(H);
  if (a === 'ap') return gdAp(H);
  if (a === 'tua') { const c = H.cau[i]; if (c) { tua(gdT(c)); giuVach(); } return; }
  if (a === 'nghe1') { const x = H.kq && H.kq.cau[i]; if (x && x.url) gdNgheDs([{url: x.url, sau: 0}]); return; }
  if (a === 'nghe-het') { const t0 = Math.min(...H.cau.map(gdT)); gdNgheDs(H.kq.cau.map((x, j) => x.url ? {url: x.url, sau: gdT(H.cau[j]) - t0} : null).filter(Boolean)); }
}
async function gdThuGiong(b, H) {
  const cu = b.innerHTML; b.disabled = true; b.textContent = 'Đang tạo mẫu…';
  try { const r = await api('/api/giong-thu', {giong: H.giong, toc_do: H.toc, phong: H.phong || undefined}); gdNgheDs([{url: r.url, sau: 0}]); }
  catch (e) { toast(e.message, true); }
  finally { b.disabled = false; b.innerHTML = cu; }
}
let gdNgheAu = [];
function gdNgheDs(ds) {   // nghe thử trong hộp: các file theo độ trễ (giây)
  gdNgheAu.forEach(x => { clearTimeout(x.h); x.a.pause(); }); gdNgheAu = [];
  dung();
  for (const d of ds) { const a = new Audio(d.url); a.preload = 'auto'; const x = {a, h: setTimeout(() => a.play().catch(() => {}), Math.max(0, d.sau * 1000))}; gdNgheAu.push(x); }
}
async function gdTao(H) {
  const cau = H.cau.map(c => ({chu: String(c.chu || '').trim(), cho: c.cho}));
  if (!cau.some(c => c.chu)) return toast('Chưa có lời nào để đọc', true);
  H.loi = ''; H.kq = null; H.tt = {dang: true, giay_da: 0, buoc: 'Đang tạo giọng…'}; gdVe();
  try {
    const r = await api('/api/sua-tay/giong-de/tao', {v: S.v, giong: H.giong, toc_do: H.toc, phong: H.phong || undefined, kieu_trend: H.kieu || undefined, cau});
    for (;;) {
      if (GD.hop !== H) return;
      const s = await api('/api/sua-tay/giong-de/tao?ma=' + encodeURIComponent(r.ma));
      H.tt = s;
      if (s.dang) { gdVeTT(); await new Promise(f => setTimeout(f, 800)); continue; }
      if (s.loi || !s.kq) throw new Error(s.loi || 'Không tạo được giọng');
      H.kq = s.kq; H.tt = null; break;
    }
  } catch (e) { if (GD.hop !== H) return; H.tt = null; H.loi = e.message; }
  gdVe();
}
function gdTu(chu, giay, tu) {   // mốc từng chữ của phụ đề theo giọng mới: giọng có mốc thì dùng, không thì chia đều
  const ws = String(chu || '').replace(/\|/g, ' ').split(/\s+/).filter(Boolean);
  if (tu && tu.length === ws.length) return tu.map(([w, a, b], j) => [ws[j], r3(a), r3(Math.max(b, a + 0.05))]);
  const d = giay / Math.max(1, ws.length);
  return ws.map((w, j) => [w, r3(j * d), r3((j + 1) * d)]);
}
function gdBoTrong(p, ks) {   // bỏ câu / vùng đọc lại cũ của các khối này (áp lại) + câu / vùng không còn khối nào (gọn kế hoạch)
  const g = p.giong_de; if (!g) return;
  const gocs = new Set((p.am_tach || []).map(k => k.goc).filter(Boolean));
  const trong = c => ks.some(k => c.nguon === k.nguon && (!c.goc || c.goc === k.goc) && +c.s0 >= +k.tu - 0.02 && +c.s0 < +k.den);
  g.cau = (g.cau || []).filter(c => !trong(c) && (!c.goc || gocs.has(c.goc)));
  let vs = (g.vung || []).filter(v => !v.goc || gocs.has(v.goc));
  for (const k of ks) {   // trừ đoạn của khối khỏi vùng cùng clip / goc
    const out = [];
    for (const v of vs) {
      if (v.nguon !== k.nguon || (v.goc && v.goc !== k.goc) || +v.den <= +k.tu || +v.tu >= +k.den) { out.push(v); continue; }
      if (+v.tu < +k.tu - 0.01) out.push(Object.assign({}, v, {den: r3(+k.tu)}));
      if (+v.den > +k.den + 0.01) out.push(Object.assign({}, v, {tu: r3(+k.den)}));
    }
    vs = out;
  }
  g.vung = vs;
}
function gdAp(H) {
  const kq = H.kq; if (!kq || S.v !== H.v) return;
  const ks0 = H.ks.map(taKhoi).filter(Boolean); if (!ks0.length) return toast('Khối tiếng tách đã bị xoá: đóng hộp rồi chọn lại', true);
  const nen = H.nen ? GD_NEN : 0, them = [], sua = [];
  dung();
  doi(p => {
    const ks = H.ks.map(id => (p.am_tach || []).find(k => k.id === id)).filter(Boolean);
    const g = p.giong_de = (p.giong_de && typeof p.giong_de === 'object') ? p.giong_de : {};
    g.cau = Array.isArray(g.cau) ? g.cau : []; g.vung = Array.isArray(g.vung) ? g.vung : [];
    gdBoTrong(p, ks);
    for (const k of ks) g.vung.push({nguon: k.nguon, goc: k.goc, tu: r3(+k.tu), den: r3(+k.den), nen});
    H.cau.forEach((c, i) => {
      const x = kq.cau[i]; if (!x || !x.local || !x.chu) return;
      g.cau.push(Object.assign({chu: x.chu, nguon: c.nguon, goc: c.goc, s0: c.s0, s1: c.s1, local: x.local, giay: x.giay, toc: x.toc, giong: kq.giong, ten: kq.ten, toc_do: kq.toc_do},
        kq.phong ? {phong: kq.phong} : {}, kq.kieu_trend ? {kieu_trend: kq.kieu_trend} : {}));   // r39: kiểu trend (chỉ THÊM khoá khi có)
      const s1 = r3(c.s0 + x.giay), tu = gdTu(x.chu, x.giay, x.tu).map(([w, a, b]) => [w, r3(c.s0 + a), r3(c.s0 + b)]);
      const it = c.k ? (p.phu_de || []).find(z => z._k === c.k) : null;
      if (it) {   // câu phụ đề đã có: giữ chữ (anh sửa trong hộp thì lấy chữ mới), giờ theo giọng mới
        if (String(it.chu || '').replace(/\|/g, ' ').replace(/\s+/g, ' ').trim() !== x.chu) it.chu = x.chu;
        it._neo = Object.assign({}, it._neo, {s0: c.s0, s1, tu, am: true, cau: true});
        delete it.tu; sua.push(it._k);
      } else if (H.phuDe) {
        const k = ks.find(z => z.id === c.khoi), sc = k && p.canh.find(z => z.tach_am && z.tach_am === k.goc);
        const t0 = k ? r3(+k.t + Math.max(c.s0, +k.tu) - +k.tu) : 0;
        p.phu_de = p.phu_de || [];
        p.phu_de.push({_k: ma('p'), chu: x.chu, t0, t1: r3(t0 + x.giay), _neo: {id: sc ? sc._id : null, file: c.nguon, s0: c.s0, s1, cau: true, am: true, tu}});
        them.push(1);
      }
    });
    if (!g.cau.length && !g.vung.length) delete p.giong_de;
  });
  const n = kq.cau.filter(x => x.local).length;
  H.dong(); GD.hop = null;
  toast('Đã đọc lại ' + n + ' câu bằng giọng ' + (kq.ten || 'AI') + (nen ? ' (tiếng gốc còn nền)' : ', tiếng gốc tắt') + (them.length ? ' · thêm ' + them.length + ' câu phụ đề' : '') + '. Ctrl+Z để bỏ');
}
function boDocLai(ids) {
  const ks = [...new Set(ids)].map(taKhoi).filter(gdCoKhoi); if (!ks.length) return;
  dung();
  doi(p => { const kk = ks.map(k => (p.am_tach || []).find(z => z.id === k.id)).filter(Boolean); gdBoTrong(p, kk); const g = p.giong_de; if (g && !(g.cau || []).length && !(g.vung || []).length) delete p.giong_de; });
  toast('Đã bỏ giọng AI đọc lại ' + (ks.length > 1 ? ks.length + ' khối' : 'khối này') + ': tiếng gốc trở lại (phụ đề giữ nguyên). Ctrl+Z để lấy lại');
}

/* ---------- menu chuột phải: khối tách, cảnh đã tách, nhóm quét chọn ---------- */
function gdMuc(ids) {
  const ks = ids.map(taKhoi).filter(Boolean), co = ks.filter(gdCoKhoi), n = ks.length;
  return [{t: 'Đọc lại' + (n > 1 ? ' ' + n + ' khối' : '') + ' bằng giọng AI…', ic: 'mic', ly_do: 'Lấy lời trong khối, giọng AI đọc lại đúng chỗ từng câu, thay tiếng gốc (không cần gõ lời)', f: () => moDocLai(ids)},
    co.length && {t: 'Bỏ giọng đọc lại' + (co.length > 1 ? ' (' + co.length + ' khối)' : ''), ic: 'boHet', ly_do: 'Tiếng gốc của khối trở lại như trước', f: () => boDocLai(co.map(k => k.id))}].filter(Boolean);
}
(function () {
  const gMenu = menuKhoi;
  menuKhoi = function (id, t) {
    const ds = gMenu.apply(this, arguments);
    try { const j = ds.findIndex(it => it && it.t === 'Chỉnh ở bảng bên phải'); ds.splice(j < 0 ? 1 : j + 1, 0, ...gdMuc(gdChonKhoi(id))); } catch (e) { console.error(e); }
    return ds;
  };
  const gTach = mucTachCanh;
  mucTachCanh = function (c) {
    const ds = gTach.apply(this, arguments);
    try { if (c && c.tach_am) { const nh = gdNhom(), mine = gdKhoiCuaCanh([c._id]); const ids = nh.length && mine.some(id => nh.includes(id)) ? nh : mine; if (ids.length) ds.push(...gdMuc(ids)); } } catch (e) { console.error(e); }
    return ds;
  };
  const gMo = moMenu;   // menu nhóm quét chọn (dev/_mod-quet.js menuNhom): thêm mục khi nhóm có cảnh đã tách
  moMenu = function (x, y, ds) {
    try { if (Array.isArray(ds) && ds[0] && typeof ds[0].nhom === 'string' && /^Đã chọn \d+ mục/.test(ds[0].nhom)) { const ids = gdNhom(); if (ids.length) { const j = ds.findIndex(it => it && it.t === 'Bỏ chọn'); ds.splice(j < 0 ? ds.length : Math.max(0, j - 1), 0, '-', {nhom: 'Giọng AI'}, ...gdMuc(ids)); } } }
    catch (e) { console.error(e); }
    return gMo.call(this, x, y, ds);
  };
})();

/* ---------- bảng phải của khối tách: nhóm "Giọng AI đọc lại" ---------- */
(function () {
  const gBen = benKhoi;
  benKhoi = function (k) {
    const h = gBen.apply(this, arguments);
    try {
      const ds = gdCuaKhoi(k), vs = gdVungKhoi(k), co = ds.length || vs.length, c0 = gdCau()[ds.length ? ds[0].i : -1] || {}, nen = vs.length ? gdSo(vs[0].nen, 0) : 0, tran = ds.filter(x => x.tran).length;
      const box = `<div class="box tt-box gde-box"><div class="row"><h2 class="sec grow">Giọng AI đọc lại</h2></div>
        ${co ? `<div class="gde-dang">${icon('mic')}<span><b>${ds.length} câu</b>${c0.ten ? ' · ' + esc(c0.ten) : ''} · tiếng gốc ${nen > 0 ? 'còn nền ' + Math.round(nen * 100) + '%' : 'tắt'}${tran ? ` · <b class="gde-do">${tran} câu tràn</b>` : ''}</span></div>` : ''}
        <div class="row gde-nut"><button type="button" class="btn small${co ? '' : ' primary'}" data-gde-a="mo" data-tip="Lấy lời trong khối, giọng AI đọc lại đúng chỗ từng câu, thay tiếng gốc">${icon('mic')}${co ? 'Đọc lại…' : 'Đọc lại bằng giọng AI'}</button>
          ${co ? `<button type="button" class="btn small" data-gde-a="bo" data-tip="Bỏ giọng AI của khối này, tiếng gốc trở lại">${icon('boHet')}Bỏ giọng đọc lại</button>` : ''}</div>
        <p class="note">Không cần gõ lời: app lấy lời trong khối (phụ đề đã có, chưa có thì tự nghe), giọng AI đọc lại từng câu bắt đầu đúng giờ câu gốc. Dời / cắt / xoá khối thì giọng đi theo.</p></div>`;
      const m = '<div class="box tt-box ta-box ta-cuoi">';
      return h.includes(m) ? h.replace(m, box + m) : h + box;
    } catch (e) { console.error(e); return h; }
  };
})();
$('#pane').addEventListener('click', e => {
  const b = e.target.closest('button[data-gde-a]'); if (!b || b.disabled || !S.plan) return;
  e.stopPropagation();
  const k = taKhoi(S.sel.am); if (!k) return;
  if (b.dataset.gdeA === 'mo') moDocLai(gdChonKhoi(k.id));
  else if (b.dataset.gdeA === 'bo') boDocLai([k.id]);
});

/* ---------- làn Giọng: mỗi câu 1 thanh đúng giờ; khối tách được đọc lại có dấu mic ---------- */
function gdVeLan() {
  const t3 = $('#tGiong'); if (!t3 || !S.plan) return;
  $$('.bar.gde', t3).forEach(b => b.remove());
  const ds = gdDat(), pps = S.pps, co = !!(S.plan.giong && S.plan.giong.local);
  const tr = $('.bar.giong.trong', t3); if (tr) tr.style.display = ds.length ? 'none' : '';   // ô "+ Giọng đọc AI" (chưa có giọng gõ lời) nhường chỗ cho các câu
  t3.insertAdjacentHTML('beforeend', ds.map(x => {
    const w = Math.max(6, x.dai * pps - 2), tip = 'Giọng AI đọc lại: “' + x.chu + '” · ' + tg(x.t) + ' – ' + tg(x.t + x.dai) + (x.tran ? ' · dài hơn chỗ trống ' + gs(x.tran) + ', đè lên câu sau' : '') + (x.cat ? ' · khối bị cắt nên giọng dừng sớm' : '') + ' · bấm phải để sửa';
    return `<div class="bar giong gde${x.tran ? ' tran' : ''}${co ? ' tren' : ''}" data-gde="${x.i}" data-t="${x.t}" style="top:2px;left:${x.t * pps}px;width:${w}px" title="${esc(tip)}"><span>${esc(x.chu)}</span></div>`;
  }).join(''));
  const vs = new Set(gdKhoiDs().filter(gdCoKhoi).map(k => k.id));
  $$('#tTach .bar.tach').forEach(b => { const on = vs.has(b.dataset.ta); b.classList.toggle('gde-co', on);
    const d = $('.gde-dau', b); if (on && !d) b.insertAdjacentHTML('beforeend', `<i class="gde-dau" title="Đã đọc lại bằng giọng AI">${icon('mic')}</i>`); else if (!on && d) d.remove(); });
}
setTimeout(() => {   // bọc NGOÀI CÙNG (sau mọi mô-đun): vẽ sau làn Tiếng tách / làn gọn
  const g = veTimeline;
  veTimeline = function () { const r = g.apply(this, arguments); try { gdVeLan(); } catch (e) { console.error(e); } return r; };
  if (S.plan) veTimeline();
}, 0);
$('#tGiong').addEventListener('click', e => {
  const b = e.target.closest('.bar.gde'); if (!b) return;
  e.stopPropagation();
  const x = gdDat().find(z => String(z.i) === b.dataset.gde); if (!x) return;
  dung(); tua(x.t + 0.001); giuVach();
  if (taKhoi(x.khoi)) chonKhoi(x.khoi);
}, true);
document.addEventListener('contextmenu', e => {
  if ($('#edit').hidden || !S.plan || $('.mbg')) return;
  const b = e.target.closest && e.target.closest('#tGiong .bar.gde'); if (!b) return;
  e.preventDefault(); e.stopImmediatePropagation();
  const x = gdDat().find(z => String(z.i) === b.dataset.gde); if (!x) return;
  const k = taKhoi(x.khoi);
  moMenu(e.clientX, e.clientY, [{nhom: 'Giọng AI đọc lại · ' + (x.chu.length > 28 ? x.chu.slice(0, 27) + '…' : x.chu)},
    {t: 'Nghe câu này', ic: 'play', f: taiT(x.t + 0.001, choi)},
    k && {t: 'Chọn khối tiếng tách', ic: 'tachAm', f: () => chonKhoi(k.id, true)},
    '-', ...(k ? gdMuc(gdChonKhoi(k.id)) : []), ...mucChung()].filter(Boolean));
}, true);

/* ---------- khung xem: phát câu giọng theo vạch đỏ (Web Audio, như khối tách) ---------- */
async function gdNap(local) {
  if (GD.buf[local]) return;
  GD.buf[local] = {dang: true};
  try {
    const r = await fetch(giongUrl({local})); if (!r.ok) throw new Error(r.status);
    const ab = await r.arrayBuffer(), ctx = taCtx();
    GD.buf[local] = {buf: await (ctx || new OfflineAudioContext(1, 1, 48000)).decodeAudioData(ab)};
  } catch (e) { GD.buf[local] = {loi: true}; }
}
function gdBoAu(key) { const n = GD.au[key]; if (!n) return; delete GD.au[key]; try { const c = n.src.context; n.g.gain.setTargetAtTime(0, c.currentTime, 0.006); n.src.stop(c.currentTime + 0.03); } catch (e) {} }
function gdKhung(t) {
  const ds = S.plan ? gdDat() : [], con = new Set(ds.map(x => x.i + '|' + x.t));
  for (const k of Object.keys(GD.au)) if (!con.has(k)) gdBoAu(k);
  if (!ds.length) return;
  ds.forEach(x => { if (!GD.buf[x.local]) gdNap(x.local); });   // nạp sẵn
  if (!(S.playing && S.mode === 'xem')) { Object.keys(GD.au).forEach(gdBoAu); return; }
  const ctx = taCtx(); if (!ctx) return;
  const now = ctx.currentTime, vol = clamp(typeof canTieng === 'function' ? canTieng('giong') : 1, 0, 1);
  const d = doanLuc(t), el = d && (typeof vidDoan === 'function' ? vidDoan(d) : VID[src(d.file)]), dongb = d && (d.the_hoi || t - d.bd < (d.dong_bang || 0));
  const von = !!(el && el.classList.contains('on') && !dongb), cho = von && (el.paused || el.seeking || el.readyState < 3);
  if (von && !cho) { const tv = d.bd + (d.dong_bang || 0) + (el.currentTime - d.tu); if (Math.abs(tv - t) < 0.6) t = tv; }
  for (const x of ds) {
    const key = x.i + '|' + x.t, u = t - x.t; let n = GD.au[key];
    if (u >= x.dai - 0.01 || u < -0.35) { if (n) gdBoAu(key); continue; }
    const b = GD.buf[x.local]; if (!b || !b.buf) continue;
    const want = x.off + Math.max(0, u);
    if (n && now >= n.bd && Math.abs(n.off + (now - n.bd) - want) > 0.12) { gdBoAu(key); n = null; }   // lệch (tua, máy kẹt): phát lại đúng chỗ
    if (!n && cho) continue;
    if (!n) {
      const sn = ctx.createBufferSource(), g = ctx.createGain(), tre = Math.max(0, -u), off = u < 0 ? x.off : want, dur = Math.max(0.01, x.off + x.dai - off);
      sn.buffer = b.buf; sn.connect(g); g.connect(ctx.destination); g.gain.value = 0;
      try { sn.start(now + tre, off, dur); } catch (e) { continue; }
      n = GD.au[key] = {src: sn, g, bd: now + tre, off};
      if (x.cat) g.gain.setTargetAtTime(0, now + tre + dur - 0.05, 0.012);
      sn.onended = () => { if (GD.au[key] === n) delete GD.au[key]; };
    }
    n.vol = vol;
    if (!x.cat || now < n.bd + (x.off + x.dai - n.off) - 0.06) n.g.gain.setTargetAtTime(vol, Math.max(now, n.bd), 0.01);
  }
}
window.gdXem = () => { const c = TA.ctx, now = c ? c.currentTime : 0;   // (để kiểm thử) câu đang phát
  return gdDat().map(x => { const n = GD.au[x.i + '|' + x.t]; return {i: x.i, t: x.t, dai: x.dai, chay: !!(n && now >= n.bd), pos: n && now >= n.bd ? n.off + now - n.bd : null, want: x.off + (S.t - x.t), vol: n ? n.vol : null, nap: !!(GD.buf[x.local] || {}).buf}; }); };
(function () {
  const gKhung = veKhung;
  veKhung = function () { const r = gKhung.apply(this, arguments); try { gdKhung(S.t); } catch (e) { console.error(e); } return r; };
  const gDung = dung;
  dung = function () { const r = gDung.apply(this, arguments); try { Object.keys(GD.au).forEach(gdBoAu); } catch (e) {} return r; };
})();
addEventListener('pointerdown', () => { if (gdCau().length) taCtx(); }, true);
