/* ============================== QUÉT CHỌN TRÊN TIMELINE (4/11 17:11) ==============================
   Anh gửi ảnh timeline (làn Cảnh, Chữ, Phụ đề, Giọng, Nhạc, dưới còn khoảng trống): "dưới này cho quét chọn".
   - Nhấn giữ chuột trái ở chỗ trống timeline (dưới các làn, hoặc chỗ trống trong làn) rồi kéo: khung chọn trong mờ, khối nào chạm khung
     thì được chọn (khối cảnh, thanh nhãn / giá / hook / thẻ kết, thanh phụ đề). Gần mép trái / phải: timeline tự cuộn. Ctrl / Shift + kéo:
     thêm vào nhóm đang chọn. Bấm 1 cái không kéo vào chỗ trống: như cũ (tua vạch đỏ) + bỏ chọn nhiều.
   - Ctrl / Shift + bấm 1 khối: thêm / bớt khối đó. Esc: bỏ chọn. Chọn ra đúng 1 mục = chọn như cũ (S.sel), không có nhóm.
   - Nhóm (≥ 2 mục, S.quet): Delete / Backspace xoá hết (chọn hết cảnh cũng xoá được: video trống, dev/_mod-trong.js); bấm phải lên nhóm = menu nhóm (Xoá N mục, Chuyển động ›,
     Hiệu ứng hình ›, Chuyển cảnh vào ›, Bộ lọc màu ›, Tự chỉnh màu, Tắt / bật tiếng, Kiểu chữ ›, Font chữ ›); kéo 1 thanh nhãn / giá / phụ đề
     trong nhóm = cả nhóm chữ dời giờ theo; bảng phải có dòng "Đã chọn N mục" + nút nhanh.
   - Mỗi thao tác nhóm = 1 bước Ctrl+Z: gop() chạy đúng các hàm áp sẵn có cho từng mục (datHieuUng, datTT, datLoc, tuMau, kcApMau, kcApFont,
     xoaCanh, xoaChu, xoaHookKet, datVachK) nhưng gộp các lần doi() lại thành 1 bước, 1 lần vẽ lại, 1 thông báo.
   Chỉ thêm file này + _mod-quet.css: bọc veTimeline / veBen, bắt sự kiện ở pha capture trên #tl. */
(function () {
  if (typeof veTimeline !== 'function' || !document.getElementById('tl')) return;
  const N = {canh: new Set(), k: new Set()};   // nhóm đang chọn nhiều
  S.quet = N;
  let P = null;          // đang quét / đang kéo nhóm chữ
  let chanClick = false; // vừa quét / Ctrl+bấm / kéo nhóm: bỏ cú click theo sau
  const chanClickSau = () => addEventListener('pointerup', () => { chanClick = true; setTimeout(() => { chanClick = false; }, 0); }, {capture: true, once: true});
  const so = () => N.canh.size + N.k.size;
  const coNhom = () => !!S.plan && so() >= 2;
  const tl = $('#tl'), tls = $('#tls');
  const laPd = k => (S.plan.phu_de || []).some(x => x._k === k);

  /* ---------- trạng thái nhóm ---------- */
  function conK(k) {   // thanh chữ này còn không (sau xoá, Ctrl+Z…)
    const chu = S.plan.chu || {}, v = S.view || {};
    if (k === 'hook') return (chu.hook || []).some(x => String(x || '').trim()) && !!v.hook_t;
    if (k === 'ket') return chu.ket !== null && !!v.ket_t;
    return !!timIt(k);
  }
  function don() {   // bỏ mục không còn; còn < 2 mục thì thôi nhóm
    if (!S.plan) { N.canh.clear(); N.k.clear(); return; }
    const ids = new Set(S.plan.canh.map(c => c._id));
    [...N.canh].forEach(id => { if (!ids.has(id)) N.canh.delete(id); });
    [...N.k].forEach(k => { if (!conK(k)) N.k.delete(k); });
    if (so() < 2) { N.canh.clear(); N.k.clear(); }
  }
  const idsNhom = () => S.plan.canh.filter(c => N.canh.has(c._id)).map(c => c._id);   // theo thứ tự cảnh
  const canhNhom = () => S.plan.canh.filter(c => N.canh.has(c._id));
  function hienTai() {   // nhóm đang có, hoặc mục đang chọn đơn (để Ctrl+bấm / Ctrl+quét thêm vào)
    if (coNhom()) return {canh: new Set(N.canh), k: new Set(N.k)};
    const o = {canh: new Set(), k: new Set()};
    if (S.selLoai === 'chu') { if (S.sel.k && $(`#tls .bar[data-k="${CSS.escape(S.sel.k)}"]`)) o.k.add(S.sel.k); }
    else if (S.sel.canh && $(`#tCanh .blk[data-id="${CSS.escape(S.sel.canh)}"]`)) o.canh.add(S.sel.canh);
    return o;
  }
  // tô viền sáng (cùng lớp .sel như chọn 1 mục) cho đúng nhóm; không có nhóm thì trả về như veTimeline gốc vẽ
  function apNhom(tam) {
    const c = tam ? tam.canh : coNhom() ? N.canh : null, k = tam ? tam.k : coNhom() ? N.k : null;
    $$('#tCanh .blk').forEach(el => { const on = c ? c.has(el.dataset.id) : el.dataset.id === S.sel.canh;
      el.classList.toggle('sel', on); el.classList.toggle('q-chon', !!c && on); });
    $$('#tChu .bar, #tPd .bar').forEach(el => { const kk = el.dataset.k; if (kk == null) return;
      const on = k ? !!kk && k.has(kk) : !!kk && kk === S.sel.k; el.classList.toggle('sel', on); el.classList.toggle('q-chon', !!k && on); });
    tl.classList.toggle('q-co', !!c);
    const bx = $('#bXoaCanh'); if (bx) { if (bx.dataset.tipGoc == null) bx.dataset.tipGoc = bx.dataset.tip || '';
      bx.dataset.tip = coNhom() ? 'Xoá ' + so() + ' mục đã chọn' : bx.dataset.tipGoc; }
  }
  function boNhom(veLai = true) {   // thôi chọn nhiều (giữ mục chọn đơn như cũ)
    if (!so()) return;
    N.canh.clear(); N.k.clear();
    if (veLai) { apNhom(); veBenNhom(); }
  }
  function datNhom(canh, ks) {   // ≥ 2 mục = nhóm; 1 mục = chọn như cũ; 0 = thôi nhóm
    N.canh = new Set(canh); N.k = new Set(ks); S.quet = N;
    const n = so();
    if (n === 1) {
      const id = [...N.canh][0], k = [...N.k][0]; N.canh.clear(); N.k.clear();
      if (id) { S.selLoai = 'canh'; S.sel.canh = id; if (S.tab !== 'canh') { S.tab = 'canh'; veTabs(); } veTimeline(); return veBen(true); }   // quét trúng 1 cảnh: như bấm cảnh đó
      chonChuMenu(k); return veBen(true);
    }
    if (!n) { apNhom(); return veBenNhom(); }
    if (N.canh.size && !N.canh.has(S.sel.canh)) S.sel.canh = idsNhom()[0];   // bảng phải / Thư viện: cảnh đầu của nhóm
    if (!['canh', 'chu', 'pd'].includes(S.tab)) { S.tab = N.canh.size ? 'canh' : [...N.k].every(laPd) ? 'pd' : 'chu'; veTabs(); }
    veTimeline(); veBen(true);
  }

  /* ---------- gộp nhiều lần áp (hàm sẵn có) thành 1 bước Ctrl+Z ---------- */
  function gop(fn, tb) {
    const snap = JSON.stringify(S.plan), cu = {doi, toast, xemMau, vaoCanh: typeof vaoCanh === 'function' ? vaoCanh : null, kcToi: typeof kcToi === 'function' ? kcToi : null};
    let co = false;
    doi = f => { co = true; f(S.plan); };
    toast = () => {}; xemMau = () => {};
    if (cu.vaoCanh) vaoCanh = () => {};
    if (cu.kcToi) kcToi = () => {};
    try { fn(); }
    finally { doi = cu.doi; toast = cu.toast; xemMau = cu.xemMau; if (cu.vaoCanh) vaoCanh = cu.vaoCanh; if (cu.kcToi) kcToi = cu.kcToi; }
    if (!co || JSON.stringify(S.plan) === snap) return false;
    S.undo.push(snap); if (S.undo.length > 100) S.undo.shift();
    S.redo = []; S.lastKey = ''; S.lastT = Date.now(); S.tam = null;
    sauDoi();
    if (tb) toast(tb);
    return true;
  }

  /* ---------- thao tác nhóm ---------- */
  function xoaNhom(daHoi) {
    don(); if (!coNhom()) return;
    const ids = idsNhom(), ks = [...N.k], n = ids.length + ks.length, het = ids.length && ids.length >= S.plan.canh.length;
    // r29 (soi sb33): quét từ chỗ trống hay dính luôn chữ / phụ đề -> nhóm có cả cảnh lẫn chữ thì hỏi 1 lần trước khi xoá
    if (!daHoi && ids.length && ks.length && !confirm('Xoá cả ' + demTxt() + '?\n(Chỉ muốn xoá cảnh: bấm Huỷ, rồi Ctrl + bấm từng thanh chữ để bỏ khỏi nhóm.)')) return;
    boNhom(false);   // 4/11 18:14 (anh: "có thể xóa hết video không cần chừa lại"): chọn hết cảnh vẫn xoá

    gop(() => { ks.forEach(k => k === 'hook' || k === 'ket' ? xoaHookKet(k) : xoaChu(k)); ids.forEach(id => xoaCanh(id)); },
      'Đã xoá ' + n + ' mục' + (het ? ', video đang trống' : '') + ' (Ctrl+Z để lấy lại)');
  }
  const TEN_KHOA = {chuyen: ['chuyen_canh', 'Chuyển cảnh vào'], dong: ['chuyen_dong', 'Chuyển động'], hieu_ung: ['hieu_ung', 'Hiệu ứng hình']};
  function hieuUngNhom(khoa, v) {
    const dau = (S.plan.canh[0] || {})._id, ids = idsNhom().filter(id => !(khoa === 'chuyen' && id === dau));
    if (!ids.length) return toast('Cảnh 1 là cảnh đầu: không có chuyển cảnh vào', true);
    const ten = v == null ? (khoa === 'hieu_ung' ? 'không' : 'theo kiểu cả video') : tenGiaTri(TEN_KHOA[khoa][0], v);
    if (!gop(() => ids.forEach(id => datHieuUng(id, khoa, v)), TEN_KHOA[khoa][1] + ' ' + ids.length + ' cảnh: ' + ten + ' (Ctrl+Z để bỏ)'))
      toast(TEN_KHOA[khoa][1] + ' ' + ids.length + ' cảnh đã là: ' + ten);
  }
  function locNhom(ten) {
    const ids = idsNhom(); if (!ids.length || typeof datLoc !== 'function') return;
    const tt = ten ? hinhTen(ten) : 'không';
    if (!gop(() => ids.forEach(id => datLoc(id, ten)), 'Bộ lọc ' + ids.length + ' cảnh: ' + tt + ' (Ctrl+Z để bỏ)')) toast('Bộ lọc ' + ids.length + ' cảnh đã là: ' + tt);
  }
  const coTieng = c => ((S.plan.nguon || {})[c.file] || {}).co_tieng !== false;
  function tiengNhom() {
    const ds = canhNhom().filter(coTieng);
    if (!ds.length) return toast('Các cảnh đã chọn không có tiếng clip', true);
    const tat = ds.some(c => amC(c) > 0);
    gop(() => ds.forEach(c => {   // như nút Tắt tiếng / Bật tiếng lại của tab Cảnh › Âm thanh, cho từng cảnh
      if (tat) { const am = amC(c); if (am > 0) { S.amCu[c._id] = am; datTT(c._id, 'am_luong', 0); } }
      else { const v = S.amCu[c._id] || 1; datTT(c._id, 'am_luong', v === 1 ? null : v); }
    }), (tat ? 'Đã tắt tiếng ' : 'Đã bật tiếng lại ') + ds.length + ' cảnh (Ctrl+Z để bỏ)');
  }
  function mauNhom() {
    const ids = idsNhom(); if (!ids.length || typeof tuMau !== 'function') return;
    if (S.tab !== 'canh' || S.tabCanh !== 'mau') { S.tab = 'canh'; S.tabCanh = 'mau'; veTabs(); }
    tuMau(ids);   // 1 lần đo, 1 bước Ctrl+Z (sẵn có trong _mod-hinh.js)
  }
  const ksKieu = () => [...N.k].filter(k => typeof kcLoai === 'function' && kcLoai(k));   // nhãn / thẻ giá / hook (phụ đề theo kiểu cả video)
  function kieuNhom(mid) { const m = kcMau(mid), ks = ksKieu(); if (!m || !ks.length) return;
    gop(() => ks.forEach(k => kcApMau(mid, k)), 'Đã áp mẫu “' + m.ten + '” cho ' + ks.length + ' chữ · Ctrl+Z để bỏ'); }
  function fontNhom(fid) { const ks = ksKieu(), f = fid ? kcFont(fid) : null; if (!ks.length) return;
    if (!gop(() => ks.forEach(k => kcApFont(fid, k)), (f ? 'Font ' + f.ten : 'Font theo kiểu') + ' cho ' + ks.length + ' chữ · Ctrl+Z để bỏ')) toast(ks.length + ' chữ đã dùng font này'); }
  function boKieuNhom() { const ks = ksKieu().filter(k => kcLay(S.plan, k)); if (!ks.length) return;
    gop(() => ks.forEach(k => kcBo(k)), 'Bỏ kiểu riêng của ' + ks.length + ' chữ: theo kiểu cả video · Ctrl+Z để lấy lại'); }

  /* ---------- menu chuột phải của nhóm ---------- */
  function menuNhom() {
    don(); if (!coNhom()) return [];
    const cs = canhNhom(), ks = [...N.k], nPd = ks.filter(laPd).length;
    const het = (f) => cs.length && cs.every(f), coC = cs.length > 0;
    const chiCanh1 = coC && cs.every(c => c._id === (S.plan.canh[0] || {})._id), coCanh1 = coC && cs.some(c => c._id === (S.plan.canh[0] || {})._id);
    const tieng = cs.filter(coTieng), tat = tieng.some(c => amC(c) > 0);
    const kk = ksKieu(), kv = kk.map(x => kcLay(S.plan, x) || {});
    const ds = [{nhom: 'Đã chọn ' + so() + ' mục · ' + demTxt()}];
    if (coC) ds.push('-', {nhom: cs.length + ' cảnh'},
      {t: 'Chuyển động', ic: 'dongK', sub: [{t: 'Theo kiểu cả video (' + tenGiaTri('chuyen_dong', dangDung('chuyen_dong')) + ')', chon: het(c => !c.dong), f: () => hieuUngNhom('dong', null)}, '-',
        ...dsDongCanh().map(([v, t]) => ({t, chon: het(c => c.dong === v), f: () => hieuUngNhom('dong', v)}))]},
      dsHieuUngHinh().length && {t: 'Hiệu ứng hình', ic: 'hieuUng', sub: [{t: 'Không', chon: het(c => !c.hieu_ung), f: () => hieuUngNhom('hieu_ung', null)}, '-',
        ...dsHieuUngHinh().map(x => ({t: x.ten, chon: het(c => c.hieu_ung === x.v), nhan: x.dau_canh ? 'đầu cảnh' : '', f: () => hieuUngNhom('hieu_ung', x.v)}))]},
      {t: 'Chuyển cảnh vào' + (coCanh1 && !chiCanh1 ? ' (trừ cảnh 1)' : ''), ic: 'chuyenC', tat: chiCanh1, ly_do: chiCanh1 ? 'Cảnh 1 là cảnh đầu: không có chuyển cảnh vào' : '',
        sub: [{t: 'Theo kiểu cả video (' + tenGiaTri('chuyen_canh', dangDung('chuyen_canh')) + ')', chon: het(c => !c.chuyen), f: () => hieuUngNhom('chuyen', null)}, '-',
          ...dsChuyenCanh().map(x => ({t: x.ten, chon: het(c => c.chuyen === x.v), nhan: x.cham ? 'chậm' : '', ly_do: x.cham ? CHAM_GOI : '', f: () => hieuUngNhom('chuyen', x.v)}))]},
      typeof HINH_LOC !== 'undefined' && typeof datLoc === 'function' && {t: 'Bộ lọc màu', ic: 'locMau', sub: [{t: 'Không', chon: het(c => !locC(c)), f: () => locNhom(null)}, '-',
        ...HINH_LOC.map(x => ({t: x.ten, chon: het(c => (locC(c) || {}).ten === x.v), f: () => locNhom(x.v)}))]},
      typeof tuMau === 'function' && (dangMau => ({t: 'Tự chỉnh màu ' + cs.length + ' cảnh', ic: 'tuMau', tat: dangMau, ly_do: dangMau ? 'Đang đo màu, chờ chút' : '', f: mauNhom}))(!!(S.hinh && S.hinh.mau && S.hinh.mau.dang)),
      {t: (tat || !tieng.length ? 'Tắt tiếng ' : 'Bật tiếng lại ') + (tieng.length || cs.length) + ' cảnh', ic: tat || !tieng.length ? 'tatLoa' : 'loa', tat: !tieng.length, ly_do: tieng.length ? '' : 'Clip của các cảnh này không có tiếng', f: tiengNhom},
      typeof tachAm === 'function' && (ids => ({t: 'Tách âm thanh ' + (ids.length || cs.length) + ' cảnh', phim: 'A', ic: 'tachAm', tat: !ids.length, ly_do: ids.length ? '' : 'Đã tách âm hoặc clip không có tiếng', f: () => tachAm(ids)}))(cs.filter(c => !c.tach_am && coTieng(c)).map(c => c._id)));   // gộp 5/11: tách âm cả nhóm (dev/_mod-tach-am.js)
    if (kk.length && typeof KC !== 'undefined') {
      const mau = KC.bang ? kv.map(x => x.mau_co_san) : [], font = KC.bang ? kv.map(x => x.font || '') : [];
      ds.push('-', {nhom: kk.length + ' chữ' + (nPd ? ' (trừ phụ đề)' : '')});
      if (!KC.bang) ds.push({t: 'Kiểu chữ', ic: 'nhan', tat: true, ly_do: KC.loi || 'Đang tải kiểu chữ…'});
      else ds.push({t: 'Kiểu chữ', ic: 'nhan', sub: [{nhom: 'Mẫu chữ cho ' + kk.length + ' chữ'}, ...(KC.bang.mau || []).map(x => ({t: x.ten, chon: mau.every(m => m === x.id), f: () => kieuNhom(x.id)}))]},
        {t: 'Font chữ', sub: [{t: 'Theo mẫu / kiểu video', chon: kv.every(x => !x.font || (kcMau(x.mau_co_san) || {}).font === x.font), f: () => fontNhom(null)}, '-',
          ...(KC.bang.font || []).map(f => ({t: f.ten, chon: font.every(x => x === f.id), f: () => fontNhom(f.id)}))]},
        kv.some(x => Object.keys(x).length) && {t: 'Bỏ kiểu riêng', ic: 'boHet', f: boKieuNhom});
    }
    ds.push('-', {t: 'Bỏ chọn', phim: 'Esc', f: () => boNhom()},
      {t: 'Xoá ' + so() + ' mục', phim: 'Delete', ic: 'xoa', nguy: true, f: xoaNhom},
      ...mucChung());
    return ds;
  }
  const dangDung = m => typeof kieuDung === 'function' ? kieuDung(m) : (S.plan.kieu || {})[m];   // giá trị cả video đang dùng (video tạo tay: mặc định trơn)
  function demTxt(nh) {
    nh = nh || N; const ks = [...nh.k], nPd = ks.filter(laPd).length, nChu = ks.length - nPd;
    return [nh.canh.size && nh.canh.size + ' cảnh', nChu && nChu + ' chữ', nPd && nPd + ' phụ đề'].filter(Boolean).join(', ');
  }

  /* ---------- bảng phải: dòng "Đã chọn N mục" + nút nhanh ---------- */
  let benCu = '';
  function veBenNhom() {
    const pane = $('#pane'); if (!pane) return;
    const cu = $('#qBen');
    don(); if (!coNhom()) { if (cu) cu.remove(); return; }
    const cs = canhNhom(), tieng = cs.filter(coTieng), tat = tieng.some(c => amC(c) > 0), dang = !!(S.hinh && S.hinh.mau && S.hinh.mau.dang);
    const i1 = S.plan.canh.findIndex(c => c._id === S.sel.canh);
    const nut = (q, ic, chu, tip, o = '', tat = false) => `<button type="button" class="btn small${o}" data-q="${q}" data-tip="${esc(tip)}"${tat ? ' disabled' : ''}>${icon(ic)}<span>${chu}</span></button>`;
    const html = `<div class="box q-ben" id="qBen" role="status">
      <div class="q-dau"><b data-tip="Ctrl / Shift + bấm 1 khối để thêm / bớt · kéo ở chỗ trống timeline để quét chọn">Đã chọn ${esc(demTxt().replace(/, /g, ' · '))}</b><span class="q-ct">(${so()} mục)</span>
        <button type="button" class="btn small ghost" data-q="bo" data-tip="Bỏ chọn nhiều (Esc)">Bỏ chọn</button></div>
      <div class="q-nut">${nut('xoa', 'xoa', 'Xoá', 'Xoá ' + so() + ' mục đã chọn (Delete) · Ctrl+Z để lấy lại', ' danger')}${cs.length ? (tieng.length
          ? nut('tieng', tat ? 'tatLoa' : 'loa', tat ? 'Tắt tiếng' : 'Bật tiếng', (tat ? 'Tắt tiếng gốc ' : 'Bật lại tiếng gốc ') + tieng.length + ' cảnh đã chọn')
          : '') + (typeof tuMau === 'function' ? nut('mau', 'tuMau', dang ? 'Đang đo màu…' : 'Tự chỉnh màu', 'Máy đo màu rồi tự cân màu ' + cs.length + ' cảnh đã chọn (1 bước Ctrl+Z)', '', dang) : '') : ''}</div>
      <p class="note">Bấm phải lên nhóm để áp chuyển động, bộ lọc, kiểu chữ…${S.tab === 'canh' && cs.length && i1 >= 0 ? ' Bảng dưới chỉ chỉnh cảnh ' + (i1 + 1) + '.' : ''}</p></div>`;
    if (cu && cu === pane.firstElementChild && html === benCu) return;   // không đổi gì: giữ nguyên (khỏi chớp ô gợi ý khi bản xem cập nhật)
    if (cu) cu.remove();
    pane.insertAdjacentHTML('afterbegin', html); benCu = html;
  }
  $('#pane').addEventListener('click', e => {
    const b = e.target.closest('#qBen [data-q]'); if (!b || b.disabled) return;
    e.stopPropagation();
    const q = b.dataset.q;
    if (q === 'bo') return boNhom();
    if (q === 'xoa') return xoaNhom();
    if (q === 'tieng') return tiengNhom();
    if (q === 'mau') return mauNhom();
  });

  /* ---------- bọc veTimeline / veBen ---------- */
  const gocTl = veTimeline;
  veTimeline = function () { const r = gocTl.apply(this, arguments); try { don(); apNhom(P && P.quet ? P.tam : null); if (P && P.keo) dichChu(); } catch (e) {} return r; };
  const gocBen = veBen;
  veBen = function () { const r = gocBen.apply(this, arguments); try { veBenNhom(); } catch (e) {} return r; };

  /* ---------- quét chọn ---------- */
  function oTrong(e) {   // chỗ trống của timeline: dưới các làn, khoảng giữa làn, chỗ trống trong làn (không trúng khối / thanh / nút)
    const t = e.target; if (!t || !t.closest || !tl.contains(t)) return false;
    if (t.closest('.tlbar, .keo, #hinhBar, .tnames, .ruler, .blk, .bar, .noi, button, input, select, textarea, a, label, .hinh-vach')) return false;
    if (t === tls) { const r = tls.getBoundingClientRect(); if (e.clientY >= r.top + tls.clientHeight || e.clientX >= r.left + tls.clientWidth) return false; }   // thanh cuộn ngang / dọc (r29: cuộn dọc nằm trong #tls)
    return true;
  }
  function khung() {   // khung chọn: toạ độ trong #tlin -> trên màn hình (chưa cắt)
    const r = $('#tlin').getBoundingClientRect(), x1 = P.cx - r.left, y1 = P.cy - r.top;
    return {l: r.left + Math.min(P.x0, x1), r: r.left + Math.max(P.x0, x1), t: r.top + Math.min(P.y0, y1), b: r.top + Math.max(P.y0, y1)};
  }
  const cham = (a, b) => a.left < b.r && a.right > b.l && a.top < b.b && a.bottom > b.t;
  function veQuet() {
    const k = khung(), tam = {canh: new Set(P.goc.canh), k: new Set(P.goc.k)};
    $$('#tCanh .blk[data-id]').forEach(el => { if (cham(el.getBoundingClientRect(), k)) tam.canh.add(el.dataset.id); });
    $$('#tChu .bar[data-k], #tPd .bar[data-k]').forEach(el => { if (el.dataset.k && cham(el.getBoundingClientRect(), k)) tam.k.add(el.dataset.k); });
    P.tam = tam; apNhom(tam);
    // vẽ khung (cắt theo phần timeline đang thấy)
    const tr = tl.getBoundingClientRect(), sr = tls.getBoundingClientRect();
    const L = Math.max(k.l, sr.left), R = Math.min(k.r, sr.left + tls.clientWidth), T = Math.max(k.t, sr.top + (($('#ruler') || {}).offsetHeight || 0)), B = Math.min(k.b, sr.top + tls.clientHeight);
    let el = $('#qKhung'); if (!el) { el = document.createElement('div'); el.id = 'qKhung'; el.className = 'q-khung'; el.innerHTML = '<span></span>'; tl.append(el); }
    el.hidden = !(R > L && B > T);
    Object.assign(el.style, {left: (L - tr.left) + 'px', top: (T - tr.top) + 'px', width: Math.max(0, R - L) + 'px', height: Math.max(0, B - T) + 'px'});
    const n = tam.canh.size + tam.k.size; el.firstChild.textContent = n ? demTxt(tam).replace(/, /g, ' · ') : ''; el.firstChild.hidden = !n;
  }
  function cuon() {   // gần mép trái / phải (và trên / dưới khi timeline cuộn dọc): tự cuộn
    if (!P) return;
    const sr = tls.getBoundingClientRect(), L = sr.left, R = sr.left + tls.clientWidth, M = 36;
    let dx = 0; if (P.cx < L + M) dx = -Math.min(36, Math.ceil((L + M - P.cx) / 2.5)); else if (P.cx > R - M) dx = Math.min(36, Math.ceil((P.cx - R + M) / 2.5));
    const bd = tls, brr = bd.getBoundingClientRect(); let dy = 0;   // r29: cuộn dọc nằm trong #tls
    if (P.quet && bd.scrollHeight > bd.clientHeight + 1) { if (P.cy < brr.top + 18) dy = -8; else if (P.cy > brr.top + bd.clientHeight - 18 && P.cy < brr.bottom + 60) dy = 8; }
    let doi_ = false;
    if (dx) { const s = tls.scrollLeft; tls.scrollLeft += dx; doi_ = tls.scrollLeft !== s; }
    if (dy) { const s = bd.scrollTop; bd.scrollTop += dy; doi_ = doi_ || bd.scrollTop !== s; }
    if (doi_) { if (P.quet) veQuet(); else if (P.keo) dichChu(); }
    P.raf = requestAnimationFrame(cuon);
  }
  function xong() {
    removeEventListener('pointermove', diChuot, true); removeEventListener('pointerup', thaChuot, true); removeEventListener('pointercancel', thaChuot, true);
    if (P && P.raf) cancelAnimationFrame(P.raf);
    const k = $('#qKhung'); if (k) k.remove();
    document.body.classList.remove('q-dang-quet', 'q-dang-keo');
  }
  function diChuot(ev) {
    if (!P) return;
    P.cx = ev.clientX; P.cy = ev.clientY;
    if (!P.quet && !P.keo2) {
      if (Math.hypot(P.cx - P.sx, P.cy - P.sy) < 5) return;
      if (P.keo) { P.keo2 = true; document.body.classList.add('q-dang-keo'); } else { P.quet = true; document.body.classList.add('q-dang-quet'); }
      $$('.tip').forEach(t => t.classList.remove('on'));
      try { tl.setPointerCapture(ev.pointerId); } catch (e) {}   // thả chuột ra ngoài khung (app nằm trong iframe) vẫn nhận được
      P.raf = requestAnimationFrame(cuon);
    }
    ev.preventDefault();
    if (P.quet) veQuet(); else dichChu();
  }
  function thaChuot(ev) {
    const p = P; xong(); P = null; if (!p) return;
    if (p.keo) return thaChu(p, ev.type === 'pointerup');
    if (!p.quet) {   // bấm 1 cái, không kéo: như cũ (tua vạch đỏ) + bỏ chọn nhiều
      boNhom();
      if (ev.type !== 'pointerup') return;
      const sr = tls.getBoundingClientRect();
      if (p.lan === 'canh') S.selLoai = 'canh';
      if (p.lan === 'canh' || (!p.lan && p.sx >= sr.left && p.sx <= sr.left + tls.clientWidth)) { dung(); tua(tTuX(p.sx)); }   // làn Chữ / Phụ đề / Giọng / Nhạc: cú click của làn tự tua
      return;
    }
    chanClick = true; setTimeout(() => { chanClick = false; }, 0);
    if (ev.type !== 'pointerup') { apNhom(); return; }   // huỷ giữa chừng: giữ nhóm cũ
    datNhom(p.tam ? p.tam.canh : [], p.tam ? p.tam.k : []);
    setSt('');
  }

  /* ---------- kéo 1 thanh chữ trong nhóm: cả nhóm chữ dời giờ ---------- */
  function batDauKeoChu(e, k) {
    const v = S.view || {}, gio = v.gio || {}, T = v.T || tongT();
    const ks = [...N.k].filter(x => timIt(x) && gio[x] && !gio[x].an && gio[x].t0 != null);   // nhãn / thẻ giá / phụ đề (hook, thẻ kết đứng yên)
    if (!ks.includes(k)) return false;
    const lo = Math.min(...ks.map(x => gio[x].t0)), hi = Math.max(...ks.map(x => gio[x].t1));
    P = {keo: true, k, ks, sx: e.clientX, sy: e.clientY, cx: e.clientX, cy: e.clientY, s0: tls.scrollLeft, dtMin: -lo, dtMax: Math.max(0, T - hi), dt: 0,
      g0: Object.fromEntries(ks.map(x => [x, {t0: gio[x].t0, t1: gio[x].t1}]))};
    return true;
  }
  function dichChu() {   // thanh đi theo chuột (chưa sửa kế hoạch: thả tay mới sửa, 1 bước Ctrl+Z)
    if (!P || !P.keo2) return;
    const px = (P.cx - P.sx) + (tls.scrollLeft - P.s0);
    P.dt = clamp(px / S.pps, P.dtMin, P.dtMax);
    P.ks.forEach(x => $$(`#tChu .bar[data-k="${CSS.escape(x)}"], #tPd .bar[data-k="${CSS.escape(x)}"]`).forEach(el => { el.style.transform = `translateX(${P.dt * S.pps}px)`; el.classList.add('q-keo'); }));
    setSt('Dời ' + P.ks.length + ' chữ ' + (P.dt >= 0 ? 'sau ' : 'trước ') + gs(Math.abs(P.dt)) + ' · thả tay để đặt');
  }
  function thaChu(p, ok) {
    $$('#tls .bar.q-keo').forEach(el => { el.style.transform = ''; el.classList.remove('q-keo'); });
    if (!p.keo2) { boNhom(); return; }   // bấm thanh, không kéo: cú click theo sau chọn 1 thanh như cũ
    chanClick = true; setTimeout(() => { chanClick = false; }, 0);
    setSt('');
    if (!ok || Math.abs(p.dt) < 0.01) return veTimeline();
    const dt = p.dt;
    gop(() => {
      p.ks.forEach(x => datVachK(x, Math.max(0, p.g0[x].t0 + dt)));
      // khung xem / làn chữ: giờ mới hiện ngay (máy chủ trả bản xem mới sẽ ghi đè)
      const gio = (S.view || {}).gio; if (gio) p.ks.forEach(x => { if (gio[x]) gio[x] = Object.assign({}, gio[x], {t0: r3(Math.max(0, p.g0[x].t0 + dt)), t1: r3(Math.max(0, p.g0[x].t0 + dt) + (p.g0[x].t1 - p.g0[x].t0))}); });
    }, 'Đã dời ' + p.ks.length + ' chữ ' + (dt >= 0 ? 'sau ' : 'trước ') + gs(Math.abs(dt)) + ' (Ctrl+Z để lấy lại)');
  }

  /* ---------- chuột: pha capture trên #tl (trước các bộ bắt sẵn có của làn) ---------- */
  tl.addEventListener('pointerdown', e => {
    if (P) { xong(); P = null; apNhom(); }   // lần kéo trước mất cú thả (hiếm): dọn
    if (e.button !== 0 || !S.plan || $('#edit').hidden || $('.mbg')) return;
    const blk = e.target.closest('#tCanh .blk[data-id]'), bar = e.target.closest('#tChu .bar[data-k], #tPd .bar[data-k]');
    const mod = e.ctrlKey || e.metaKey || e.shiftKey;
    if (!mod && coNhom() && e.target.closest('#tTach .bar, #tAm .bar, #tNhac .bar, #tGiong .bar')) { boNhom(); return; }   // gộp 5/11: bấm khối tiếng tách / âm thanh / nhạc / giọng thì bỏ nhóm (Delete sau đó chỉ xoá khối đó)
    if ((blk || bar) && !e.target.closest('.noi')) {
      if (mod) {   // Ctrl / Shift + bấm: thêm / bớt mục này
        if (bar && !bar.dataset.k) return;
        e.stopPropagation(); chanClickSau();
        const h = hienTai(), s = blk ? h.canh : h.k, v = blk ? blk.dataset.id : bar.dataset.k;
        if (s.has(v)) s.delete(v); else s.add(v);
        dung();
        return datNhom(h.canh, h.k);
      }
      if (coNhom() && bar && N.k.has(bar.dataset.k) && batDauKeoChu(e, bar.dataset.k)) {   // kéo nhóm chữ
        e.stopPropagation();
        addEventListener('pointermove', diChuot, true); addEventListener('pointerup', thaChuot, true); addEventListener('pointercancel', thaChuot, true);
        return;
      }
      boNhom(); return;   // bấm 1 khối / thanh không giữ Ctrl: chọn 1 mục như cũ (bộ bắt của làn lo)
    }
    if (!oTrong(e)) return;
    e.stopPropagation();   // làn Cảnh cũ: nhấn là tua ngay -> giờ chờ thả tay (không kéo mới tua)
    const r = $('#tlin').getBoundingClientRect(), lan = e.target.closest('#tCanh') ? 'canh' : e.target.closest('#tChu, #tPd, #tGiong, #tNhac') ? 'lan' : '';
    P = {sx: e.clientX, sy: e.clientY, cx: e.clientX, cy: e.clientY, x0: e.clientX - r.left, y0: e.clientY - r.top, lan,
      goc: mod ? hienTai() : {canh: new Set(), k: new Set()}, tam: null};
    addEventListener('pointermove', diChuot, true); addEventListener('pointerup', thaChuot, true); addEventListener('pointercancel', thaChuot, true);
  }, true);
  // cú click theo sau quét / Ctrl+bấm / kéo nhóm: bỏ (không chọn 1 thanh, không tua)
  addEventListener('click', e => { if (chanClick && tl.contains(e.target)) { e.stopPropagation(); e.preventDefault(); } }, true);
  // nút Xoá trên thanh timeline: đang chọn nhiều thì xoá cả nhóm
  tl.addEventListener('click', e => { if (coNhom() && e.target.closest('#bXoaCanh')) { e.stopPropagation(); e.preventDefault(); xoaNhom(); } }, true);
  // bấm phải: lên mục trong nhóm = menu nhóm; lên mục ngoài nhóm = thôi nhóm, menu 1 mục như cũ; chỗ trống = menu timeline như cũ
  tl.addEventListener('contextmenu', e => {
    if (!coNhom() || $('#edit').hidden || $('.mbg')) return;
    const blk = e.target.closest('#tCanh .blk[data-id]'), bar = e.target.closest('#tChu .bar[data-k], #tPd .bar[data-k]');
    if (!blk && !bar) return;
    if ((blk && N.canh.has(blk.dataset.id)) || (bar && N.k.has(bar.dataset.k))) {
      e.preventDefault(); e.stopPropagation();
      moMenu(e.clientX, e.clientY, menuNhom());
    } else boNhom();
  }, true);
  // phím: Esc bỏ chọn, Delete / Backspace xoá nhóm (sau menu chuột phải: menu mở thì phím đó chỉ đóng menu như cũ)
  addEventListener('keydown', e => {
    if (P && e.key === 'Escape') {   // Esc lúc đang quét / kéo: huỷ, giữ nhóm cũ
      e.preventDefault(); e.stopImmediatePropagation(); const p = P; xong(); P = null;
      if (p.keo) { $$('#tls .bar.q-keo').forEach(el => { el.style.transform = ''; el.classList.remove('q-keo'); }); setSt(''); }
      apNhom(); chanClickSau();
      return;
    }
    if (!coNhom() || $('#edit').hidden || $('.mbg') || (typeof MENU !== 'undefined' && MENU)) return;
    const ae = document.activeElement || {}, go = /TEXTAREA|SELECT/.test(ae.tagName || '') || (ae.tagName === 'INPUT' && !/^(checkbox|radio|button|range)$/.test(ae.type)) || ae.isContentEditable;
    if (go || e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.key === 'Escape') { boNhom(); return; }
    if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); e.stopImmediatePropagation(); xoaNhom(); }
  }, true);

  window.QUET = {nhom: () => ({canh: idsNhom(), k: [...N.k]}), dat: datNhom, bo: boNhom, xoa: xoaNhom, menu: menuNhom};
})();
