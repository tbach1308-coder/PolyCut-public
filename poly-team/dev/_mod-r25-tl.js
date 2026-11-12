/* ============================== TIMELINE r25 (5/11, anh duyệt đề xuất học từ OpenReel / FreeCut, mục 1 · 2 · 5 · 9) ==============================
   (1) KÉO THANH CHỮ: thanh nhãn / thẻ giá / câu phụ đề trên timeline kéo thân để dời, kéo 2 mép (tay nắm vàng) để dài / ngắn.
       Tự hít (nam châm 8px) vào mép cảnh, vạch đỏ, đầu / cuối video, mép chữ khác; vạch hít vàng đứt + khung báo
       "Pin 98% · 0:03,4 → 0:05,4 (2,0s) hít mép cảnh 3" + bóng chỗ cũ. Nút nam châm trên thanh timeline (phím N, nhớ trên máy),
       giữ Alt lúc kéo = tắt hít tạm. Esc lúc kéo = huỷ. Mỗi lần kéo = 1 bước Ctrl+Z (doi), tự lưu như cũ.
       Hook / thẻ kết có giờ cố định: không kéo. Đang có nhóm quét chọn mà kéo 1 thanh trong nhóm: cả nhóm dời như cũ (dev/_mod-quet.js).
       Câu phụ đề có giờ từng chữ (tô chữ): giờ từng chữ đi theo câu (dời / co giãn đều), máy chủ neo lại vào cảnh mới (gan_neo).
   (2) LÀN GỌN: nút "Làn gọn" trên thanh timeline: khối cảnh 74 -> 44px, hàng chữ 19 -> 13px, làn Giọng / Nhạc / Âm thanh / Tách thấp lại
       -> màn 1366×768 thấy đủ các làn không phải cuộn. Màn thấp (< 900px) tự bật khi anh chưa chọn; anh bấm thì nhớ trên máy (st-tl-gon).
       Làm sau cùng mọi lớp bọc veTimeline (xếp lại toạ độ các làn: style.top / height, tên làn, chiều cao #tlin) nên quét chọn, thả clip,
       kéo khối tách, làn Nhạc / Âm thanh vẫn đúng (đều đọc style.top / getBoundingClientRect).
   (5) CHÉP / DÁN KIỂU CẢNH: chuột phải cảnh › Chép kiểu cảnh này (Ctrl+Alt+C) / Dán kiểu vào cảnh (Ctrl+Alt+V); có nhóm quét chọn thì
       dán vào mọi cảnh của nhóm. Chỉ các khoá kiểu có sẵn của cảnh: chuyển động, hiệu ứng hình, chuyển cảnh vào, màu, bộ lọc, khung,
       âm lượng, chống rung (không đụng clip / giờ). Cảnh 1 và chỗ chia giữ chuyển cảnh vào của nó. 1 bước Ctrl+Z.
   (9) MÀU KHỐI THEO LOẠI: thẻ giá vàng #FFD600 chữ tối (nổi nhất), nhãn nâu, hook / thẻ kết lục bảo #074D3A, phụ đề xám. Chú thích ở tên làn.
   Chỉ thêm file này + _mod-r25-tl.css: bọc veTimeline / menuCanh / moMenu, bắt sự kiện riêng. Không thêm khoá kế hoạch. */
IC_P.namCham = '<path d="M5 3h4v8a3 3 0 0 0 6 0V3h4v8a7 7 0 0 1-14 0z"/><path d="M5 7h4M15 7h4"/>';
IC_P.lanGon = '<path d="M4 9.5h16M4 14.5h16"/><path d="m9 3 3 3 3-3M9 21l3-3 3 3"/>';
IC_P.chepKieu = '<path d="M18.4 2.6 14 7l-1.6-1.6a2 2 0 0 0-2.8 0L8 7l9 9 1.6-1.6a2 2 0 0 0 0-2.8L17 10l4.4-4.4a2.1 2.1 0 1 0-3-3z"/><path d="M9 8c-2 3-4 3.5-7 4l8 10c2-1 6-5 6-7"/>';
IC_P.danKieu = '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>';
(function () {
  if (typeof veTimeline !== 'function' || !document.getElementById('tl')) return;
  const tl = $('#tl'), tls = $('#tls');
  const doc = k => { try { return localStorage.getItem(k); } catch (e) { return null; } };
  const ghi = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) {} };
  const R = {hit: doc('st-tl-hit') !== '0', gon: false, gonTu: doc('st-tl-gon') == null, keo: null, kieu: null, chanClick: false};
  try { const k = JSON.parse(doc('st-kieu-canh') || 'null'); if (k && k.k && typeof k.k === 'object') R.kieu = k; } catch (e) {}
  const MAN_THAP = 900;   // cửa sổ thấp hơn (máy 1366×768, 1440×900 có thanh tác vụ): tự bật Làn gọn khi anh chưa chọn
  R.gon = R.gonTu ? innerHeight < MAN_THAP : doc('st-tl-gon') === '1';
  const go = () => { const ae = document.activeElement || {}; return /TEXTAREA|SELECT/.test(ae.tagName || '') || (ae.tagName === 'INPUT' && !/^(checkbox|radio|button|range)$/.test(ae.type)) || !!ae.isContentEditable; };
  const ngan = s => { s = String(s || '').trim(); return s.length > 22 ? s.slice(0, 21) + '…' : s; };
  const gs1 = t => (Math.round((t || 0) * 10) / 10).toFixed(1).replace('.', ',') + 's';   // "2,0s" (độ dài trong khung báo, luôn 1 số lẻ)

  /* ================= nút trên thanh timeline: Làn gọn + nam châm (trước nút Vừa khung) ================= */
  const vua = $('#bVua');
  const nutGon = document.createElement('button'); nutGon.type = 'button'; nutGon.id = 'bLanGon'; nutGon.className = 'btn ico r25-nut r25-gon-nut';
  nutGon.innerHTML = icon('lanGon') + '<span class="r25-chu">Làn gọn</span>';
  nutGon.dataset.tip = 'Làn gọn: thu thấp các làn để màn nhỏ (1366×768) thấy đủ Cảnh, Chữ, Phụ đề, Giọng, Nhạc. Bấm lần nữa để về cỡ thường (nhớ trên máy này)';
  const nutHit = document.createElement('button'); nutHit.type = 'button'; nutHit.id = 'bHit'; nutHit.className = 'btn ico r25-nut';
  nutHit.innerHTML = icon('namCham');
  nutHit.dataset.tip = 'Tự hít: kéo thanh chữ tới gần mép cảnh, vạch đỏ hay mép chữ khác thì tự hít vào. Giữ Alt lúc kéo để tắt tạm'; nutHit.dataset.phim = 'N';
  if (vua) { vua.before(nutGon); vua.before(nutHit); }
  const ghiChu = $('.tlbar > .note'); if (ghiChu) ghiChu.textContent = 'Kéo thân để dời · kéo mép vàng để cắt / đổi dài · giữ Alt: tắt hít';
  function veNutTl() {
    nutGon.classList.toggle('on', R.gon); nutGon.setAttribute('aria-pressed', String(R.gon));
    nutGon.setAttribute('aria-label', 'Làn gọn: ' + (R.gon ? 'đang bật' : 'đang tắt'));
    nutHit.classList.toggle('on', R.hit); nutHit.setAttribute('aria-pressed', String(R.hit));
    nutHit.setAttribute('aria-label', 'Tự hít: ' + (R.hit ? 'đang bật' : 'đang tắt') + ' (N)');
  }
  function datHit(v, bao) { R.hit = !!v; ghi('st-tl-hit', R.hit ? null : '0'); veNutTl(); if (bao) toast(R.hit ? 'Tự hít: bật (kéo thanh chữ gần mép cảnh / vạch đỏ là hít vào)' : 'Tự hít: tắt (bấm N hoặc nút nam châm để bật lại)'); }
  function datGon(v, nho = true) {
    if (nho) { R.gonTu = false; ghi('st-tl-gon', v ? '1' : '0'); }
    if (R.gon === !!v) { veNutTl(); return; }
    R.gon = !!v; veNutTl();
    if (S.plan) veTimeline(); else gonLai();
    if (nho) window.dispatchEvent(new Event('resize'));   // timeline thấp / cao lại -> khung xem, cột tự canh lại
  }
  nutGon.addEventListener('click', () => datGon(!R.gon));
  nutHit.addEventListener('click', () => datHit(!R.hit, true));
  addEventListener('resize', () => { if (R.gonTu) datGon(innerHeight < MAN_THAP, false); });
  veNutTl();

  /* chú thích màu khối (9) ở tên làn */
  const nmChu = $('#nmChu'), nmPd = $('#nmPd');
  if (nmChu) nmChu.dataset.tip = 'Màu thanh: vàng = thẻ giá · nâu = nhãn · lục bảo = hook / thẻ kết. Kéo thân thanh để dời, kéo 2 mép vàng để dài / ngắn';
  if (nmPd) nmPd.dataset.tip = 'Thanh xám = câu phụ đề. Kéo thân để dời, kéo 2 mép vàng để dài / ngắn (giờ từng chữ đi theo)';

  /* ================= (2) LÀN GỌN: xếp lại toạ độ các làn sau khi mọi lớp bọc vẽ xong ================= */
  // khe: chỗ trống giữa làn Cảnh và làn Chữ (bắt đầu quét chọn được); .tls vẫn chừa 30px trống dưới làn cuối để quét (_mod-quet.css)
  // r29 (soi N10): khối Tiếng tách 13 -> 18px cho dễ bấm (hàng làn Tách 18); bù lại khe 4 -> 2, làn đơn 15 -> 14 để 7 làn vẫn vừa 1366×768
  const GON = {canhTop: 20, canhH: 44, khe: 2, hang: 13, hangTach: 18, don: 14, ke: 1};
  const LAN = [['tChu', 'nmChu', 19, 2], ['tPd', 'nmPd', 19, 2], ['tGiong', 'nmGiong'], ['tNhac', 'nmNhac'], ['tAm', 'nmAm'], ['tTach', 'nmTach', 24, 3]];
  function gonLai() {
    tl.classList.toggle('tl-gon', R.gon);
    const nm = $('#nmCanh'); if (nm) Object.assign(nm.style, R.gon ? {top: GON.canhTop + 'px', height: GON.canhH + 'px'} : {top: '26px', height: '74px'});
    if (!R.gon || !S.plan) return;
    let y = GON.canhTop + GON.canhH + GON.khe;
    for (const [id, nid, buoc, dem] of LAN) {
      const ln = document.getElementById(id); if (!ln || ln.hidden) continue;
      let h = GON.don;
      if (buoc) {   // làn nhiều hàng: hàng cũ (top = hàng × bước + lề) -> hàng gọn; nhớ số hàng trên thanh để vẽ lại nhiều lần vẫn đúng
        let n = 1; const hang = id === 'tTach' ? GON.hangTach : GON.hang;
        ln.querySelectorAll(':scope > .bar').forEach(b => {
          let r = b.dataset.r25h; if (r == null) { r = Math.max(0, Math.round((parseFloat(b.style.top) - dem) / buoc) || 0); b.dataset.r25h = r; }
          r = +r; b.style.top = (r * hang + 1) + 'px'; n = Math.max(n, r + 1); });
        h = n * hang + 3;
      }
      ln.style.top = y + 'px'; ln.style.height = h + 'px';
      const n2 = document.getElementById(nid); if (n2) { n2.style.top = y + 'px'; n2.style.height = h + 'px'; }
      y += h + GON.ke;
    }
    const H = y - GON.ke + 4;
    $('#tlin').style.height = H + 'px'; const tn = $('#tnames'); if (tn) tn.style.minHeight = H + 'px';
  }

  /* ================= (1) KÉO THANH CHỮ ================= */
  const MIN = 0.3, HUT = 8;   // độ dài ít nhất (giây) · tầm hít (px trên màn hình)
  const gioV = () => (S.view || {}).gio || {};
  const laPd = k => (S.plan.phu_de || []).some(x => x._k === k);
  const laGia = k => !!((S.plan.chu || {}).the_gia && S.plan.chu.the_gia._k === k);
  const keoDuoc = k => !!k && k !== 'hook' && k !== 'ket' && !!timIt(k) && !!gioV()[k] && !gioV()[k].an && gioV()[k].t0 != null;
  const tenThanh = k => k === 'hook' ? 'hook' : k === 'ket' ? 'thẻ kết' : laGia(k) ? 'thẻ giá' : laPd(k) ? 'phụ đề' : 'nhãn';
  const chuThanh = k => { const it = timIt(k); if (!it) return ''; return laGia(k) ? 'Giá ' + (it.gia || '') : ngan(it.chu); };
  function ganMep() {   // tay nắm 2 mép cho thanh kéo được (vẽ lại sau mỗi lần veTimeline)
    if (!S.plan) return;
    $$('#tChu .bar[data-k], #tPd .bar[data-k]').forEach(b => {
      const k = b.dataset.k; if (!k) return;
      if (k === 'hook' || k === 'ket') { b.classList.add('r25-co-dinh'); return; }
      if (!keoDuoc(k)) return;
      // r29 (soi L2): thanh < 40px tay nắm 4px, < 20px không có tay nắm (kéo thân thôi; muốn đổi dài thì phóng to timeline) -> thân luôn nắm được
      const w = parseFloat(b.style.width) || b.offsetWidth; b.classList.toggle('r25-ngan', w < 40); b.classList.toggle('r25-rat-ngan', w < 20);
      if (b.querySelector('.r25-m')) return;
      b.classList.add('r25-keo'); b.insertAdjacentHTML('beforeend', '<i class="r25-m l" data-m="l"></i><i class="r25-m r" data-m="r"></i>');
    });
  }
  function deNhau(k, t0, t1) {   // r29 (soi L2): thanh k ở giờ t0–t1 đè lên thanh nào cùng làn (phụ đề ↔ phụ đề; nhãn / giá / hook / kết với nhau)
    const g = gioV(), v = S.view || {}, chu = S.plan.chu || {}, pd = laPd(k), out = [];
    const xet = (kk, a, z, ten) => { if (kk === k || a == null || z == null) return; if (Math.min(t1, z) - Math.max(t0, a) > 0.02) out.push({k: kk, ten}); };
    if (pd) (S.plan.phu_de || []).forEach(it => { const x = g[it._k]; if (x && !x.an) xet(it._k, x.t0, x.t1, 'câu “' + ngan(it.chu) + '”'); });
    else {
      if (v.hook_t && (chu.hook || []).some(Boolean)) xet('hook', v.hook_t[0], v.hook_t[1], 'hook');
      if (v.ket_t) xet('ket', v.ket_t[0], v.ket_t[1], 'thẻ kết');
      [...(chu.nhan_chu || []), chu.the_gia].forEach(it => { if (!it) return; const x = g[it._k]; if (x && !x.an) xet(it._k, x.t0, x.t1, (laGia(it._k) ? 'thẻ giá “' + ngan(it.gia) : 'nhãn “' + ngan(it.chu)) + '”'); });
    }
    return out;
  }
  function mocHit(k) {   // chỗ hít: vạch đỏ, đầu / cuối video, mép cảnh, mép chữ khác
    const T = tongT(), out = [{t: S.t, ten: 'vạch đỏ', uu: 0}, {t: 0, ten: 'đầu video', uu: 1}, {t: T, ten: 'cuối video', uu: 1}];
    const b = bocCanh();
    b.forEach((x, j) => { if (j > 0) out.push({t: x.bd, ten: 'mép cảnh ' + (x.i + 1), uu: 1});
      if (j < b.length - 1 && Math.abs(x.b - b[j + 1].bd) > 0.02) out.push({t: x.b, ten: 'cuối cảnh ' + (x.i + 1), uu: 1}); });
    const v = S.view || {}, g = gioV(), chu = S.plan.chu || {};
    const them = (a, z, ten) => { if (a == null || z == null) return; out.push({t: a, ten, uu: 2}, {t: z, ten, uu: 2}); };
    if (v.hook_t && (chu.hook || []).some(Boolean)) them(v.hook_t[0], v.hook_t[1], 'mép hook');
    if (v.ket_t) them(v.ket_t[0], v.ket_t[1], 'mép thẻ kết');
    [...(chu.nhan_chu || []), chu.the_gia, ...(S.plan.phu_de || [])].forEach(it => {
      if (!it || it._k === k || !g[it._k] || g[it._k].an || g[it._k].t0 == null) return;
      them(g[it._k].t0, g[it._k].t1, 'mép ' + tenThanh(it._k) + (laPd(it._k) ? '' : ' “' + ngan(laGia(it._k) ? it.gia : it.chu) + '”'));
    });
    return out;
  }
  function hut(t, moc, d) { let b = null; for (const m of moc) { const x = Math.abs(m.t - t); if (x <= d && (!b || x < b.x - 1e-6 || (Math.abs(x - b.x) <= 1e-6 && m.uu < b.m.uu))) b = {m, x}; } return b; }
  function tinh(ev) {   // giờ mới theo chuột (+ hít)
    const P = R.keo, T = tongT(), d0 = P.g0.t1 - P.g0.t0;
    const dt = ((ev ? ev.clientX : P.cx) - P.x0 + (tls.scrollLeft - P.s0)) / S.pps;
    const tat = !R.hit || P.alt, dh = HUT / S.pps;
    let t0 = P.g0.t0, t1 = P.g0.t1, h = null;
    if (P.mode === 'doi') {
      t0 = clamp(P.g0.t0 + dt, 0, Math.max(0, T - d0));
      if (!tat) { const a = hut(t0, P.moc, dh), z = hut(t0 + d0, P.moc, dh);
        if (a && (!z || a.x <= z.x)) { h = a.m; t0 = a.m.t; } else if (z) { h = z.m; t0 = z.m.t - d0; }
        if (h && (t0 < -1e-6 || t0 + d0 > T + 1e-6)) { h = null; t0 = clamp(P.g0.t0 + dt, 0, Math.max(0, T - d0)); } }
      t1 = t0 + d0;
    } else if (P.mode === 'l') {
      t0 = clamp(P.g0.t0 + dt, 0, P.g0.t1 - MIN);
      if (!tat) { const a = hut(t0, P.moc, dh); if (a && a.m.t >= 0 && a.m.t <= P.g0.t1 - MIN) { h = a.m; t0 = a.m.t; } }
    } else {
      t1 = clamp(P.g0.t1 + dt, P.g0.t0 + MIN, Math.max(P.g0.t0 + MIN, T));
      if (!tat) { const a = hut(t1, P.moc, dh); if (a && a.m.t >= P.g0.t0 + MIN && a.m.t <= T + 1e-6) { h = a.m; t1 = a.m.t; } }
    }
    P.t0 = r3(t0); P.t1 = r3(t1); P.h = h; P.de = deNhau(P.k, P.t0, P.t1);
  }
  function apKeo() {   // vẽ thanh đang kéo (+ bóng chỗ cũ, vạch hít, khung báo giờ); gọi lại được sau mỗi lần timeline vẽ lại
    const P = R.keo; if (!P || !P.dang) return;
    const sel = `#tChu .bar[data-k="${CSS.escape(P.k)}"], #tPd .bar[data-k="${CSS.escape(P.k)}"]`, b = $(sel); if (!b) return;
    const pps = S.pps;
    b.style.left = (P.t0 * pps) + 'px'; b.style.width = Math.max(6, (P.t1 - P.t0) * pps - 2) + 'px'; b.classList.add('r25-dang'); b.classList.toggle('r25-de', !!(P.de && P.de.length));
    let bo = $('#r25Bong'); if (!bo || bo.parentNode !== b.parentNode) { if (bo) bo.remove(); bo = document.createElement('div'); bo.id = 'r25Bong'; bo.className = 'r25-bong'; b.parentNode.insertBefore(bo, b); }
    Object.assign(bo.style, {top: b.style.top, left: (P.g0.t0 * pps) + 'px', width: Math.max(6, (P.g0.t1 - P.g0.t0) * pps - 2) + 'px'});
    let v = $('#r25Vach'); if (!v) { v = document.createElement('div'); v.id = 'r25Vach'; v.className = 'r25-vach'; $('#tlin').append(v); }
    v.hidden = !P.h; if (P.h) v.style.left = (P.h.t * pps) + 'px';
    let k = $('#r25Hop'); if (!k) { k = document.createElement('div'); k.id = 'r25Hop'; k.className = 'r25-hop'; k.setAttribute('role', 'status'); document.body.append(k); }
    const de = P.de && P.de.length ? ` <b class="de">⚠ đè ${esc(P.de.map(x => x.ten).join(', '))}</b>` : '';
    k.innerHTML = `<span>${esc(P.ten)}</span> · ${tg(P.t0)} → ${tg(P.t1)} <small>(${gs1(P.t1 - P.t0)})</small>${P.h ? ` <b>hít ${esc(P.h.ten)}</b>` : P.alt && R.hit ? ' <i>tắt hít (Alt)</i>' : ''}${de}`;
    k.classList.toggle('de', !!de);
    const r = b.getBoundingClientRect(), w = k.offsetWidth, hh = k.offsetHeight;
    let y = r.top - hh - 7; if (y < 4) y = r.bottom + 7;
    k.style.left = Math.max(6, Math.min(innerWidth - w - 6, r.left)) + 'px'; k.style.top = y + 'px';
  }
  function donKeo() {
    ['#r25Bong', '#r25Vach', '#r25Hop'].forEach(s => { const e = $(s); if (e) e.remove(); });
    $$('#tls .bar.r25-dang').forEach(e => e.classList.remove('r25-dang', 'r25-de'));
    document.body.classList.remove('r25-dang-keo', 'r25-keo-mep');
  }
  function cuon() {   // gần mép trái / phải timeline: tự cuộn theo
    const P = R.keo; if (!P || !P.dang) return;
    const sr = tls.getBoundingClientRect(), L = sr.left, Rr = sr.left + tls.clientWidth, M = 36;
    let dx = 0; if (P.cx < L + M) dx = -Math.min(30, Math.ceil((L + M - P.cx) / 2.5)); else if (P.cx > Rr - M) dx = Math.min(30, Math.ceil((P.cx - Rr + M) / 2.5));
    if (dx) { const s = tls.scrollLeft; tls.scrollLeft += dx; if (tls.scrollLeft !== s) { tinh(); apKeo(); } }
    P.raf = requestAnimationFrame(cuon);
  }
  function chanClickSau() { R.chanClick = true; setTimeout(() => { R.chanClick = false; }, 0); }
  addEventListener('click', e => { if (R.chanClick && tl.contains(e.target)) { e.stopPropagation(); e.preventDefault(); } }, true);
  function giuChu(it, g, t0, t1) {   // giờ từng chữ (tô chữ) của câu phụ đề: lấy giờ đang dùng trên video, co giãn theo khoảng mới
    let ds = null; const n = it._neo;
    if (n && Array.isArray(n.tu) && n.tu.length) {
      const x = bocCanh().find(y => y.c._id === n.id && y.c.file === n.file);
      if (x) ds = n.tu.map(([w, a, b]) => [w, x.bd + (+a - x.c.tu), x.bd + (+b - x.c.tu)]);
    } else if (!n && Array.isArray(it._tu_goc) && it._tu_goc.length) ds = it._tu_goc.map(([w, a, b]) => [w, +a, +b]);
    if (!ds || ds.some(([, a, b]) => !(a >= g.t0 - 0.05 && b <= g.t1 + 0.05))) return null;   // chữ nằm ngoài khoảng đang hiện (câu bị cắt): không đoán
    const k = (t1 - t0) / Math.max(0.01, g.t1 - g.t0), f = x => r3(t0 + (x - g.t0) * k);
    return ds.map(([w, a, b]) => [w, f(a), f(b)]);
  }
  function datGio(k, t0, t1, g) {   // ghi giờ mới cho nhãn / thẻ giá / câu (1 bước Ctrl+Z), như "⇥ Vạch đỏ" nhưng giữ được độ dài anh kéo
    const pd = laPd(k);
    doi(() => {
      const it = timIt(k); if (!it) return;
      const tu = pd ? giuChu(it, g, t0, t1) : null;
      delete it._neo; delete it.canh;
      if (pd && tu) { it.tu = tu; if (S.plan.giong) it._tu_goc = tu; else delete it._tu_goc; }
      else { delete it.tu; delete it._tu_goc; }
      it.t0 = r3(t0); it.t1 = r3(t1);
      S.sel.k = k; S.selLoai = 'chu';
      const gv = gioV(); if (gv[k]) gv[k] = Object.assign({}, gv[k], {t0: r3(t0), t1: r3(t1), cat: false});   // thanh đứng ngay chỗ mới (máy chủ trả bản xem mới sẽ ghi đè)
    });
  }
  function batDau(P, ev) {   // vừa kéo quá 4px: chọn thanh, hiện bóng / khung báo
    P.dang = true; dung();
    try { tl.setPointerCapture(ev.pointerId); } catch (e) {}
    document.body.classList.add('r25-dang-keo'); if (P.mode !== 'doi') document.body.classList.add('r25-keo-mep');
    $$('.tip').forEach(t => t.classList.remove('on'));
    P.moc = mocHit(P.k);
    if (S.sel.k !== P.k || S.selLoai !== 'chu') { S.sel.k = P.k; S.selLoai = 'chu'; const tab = laPd(P.k) ? 'pd' : 'chu'; if (S.tab !== tab) { S.tab = tab; veTabs(); } veBen(true); veTimeline(); }
    P.raf = requestAnimationFrame(cuon);
  }
  function xongKeo(huy) {
    const P = R.keo; R.keo = null; if (!P) return;
    removeEventListener('pointermove', diChuot, true); removeEventListener('pointerup', thaChuot, true); removeEventListener('pointercancel', thaChuot, true);
    removeEventListener('keydown', phimKeo, true); removeEventListener('keyup', phimKeo, true);
    if (P.raf) cancelAnimationFrame(P.raf);
    donKeo();
    if (!P.dang) return;
    chanClickSau();
    if (huy || (Math.abs(P.t0 - P.g0.t0) < 0.005 && Math.abs(P.t1 - P.g0.t1) < 0.005)) { veTimeline(); return; }
    datGio(P.k, P.t0, P.t1, P.g0);
    const ten = tenThanh(P.k), dai = P.mode !== 'doi';
    const de = P.de && P.de.length ? ' · đang đè ' + P.de.map(x => x.ten).join(', ') + ' (2 chữ hiện cùng lúc)' : '';
    toast((dai ? 'Đổi ' + ten + ' thành ' + gs1(P.t1 - P.t0) + ' (' + tg(P.t0) + ' → ' + tg(P.t1) + ')' : 'Dời ' + ten + ' tới ' + tg(P.t0)) + (P.h ? ', hít ' + P.h.ten : '') + de + ' · Ctrl+Z để lấy lại', !!de);
  }
  function diChuot(ev) {
    const P = R.keo; if (!P) return;
    P.cx = ev.clientX; P.alt = ev.altKey;
    if (!P.dang) { if (Math.abs(ev.clientX - P.x0) < 4 && Math.abs(ev.clientY - P.y0) < 4) return; batDau(P, ev); }
    ev.preventDefault();
    tinh(ev); apKeo();
  }
  function thaChuot(ev) { xongKeo(ev.type !== 'pointerup'); }
  function phimKeo(e) {   // Esc: huỷ · Alt: tắt hít tạm (cập nhật ngay, không chờ rê chuột)
    const P = R.keo; if (!P) return;
    if (e.key === 'Escape' && e.type === 'keydown') { e.preventDefault(); e.stopImmediatePropagation(); const d = P.dang; xongKeo(true);
      if (d) addEventListener('pointerup', chanClickSau, {capture: true, once: true});   // chuột còn đang giữ: thả ra không tính là bấm (không tua / chọn lại)
      return; }
    if (e.key === 'Alt') { e.preventDefault(); P.alt = e.type === 'keydown'; if (P.dang) { tinh(); apKeo(); } }
  }
  ['#tChu', '#tPd'].forEach(id => $(id).addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || !S.plan || $('.mbg') || R.keo) return;
    const b = e.target.closest('.bar[data-k]'); if (!b || !b.dataset.k) return;
    const k = b.dataset.k;
    if (k === 'hook' || k === 'ket') {   // giờ cố định: kéo thì nhắc 1 lần, bấm vẫn chọn như cũ
      const x0 = e.clientX, mv = ev => { if (Math.abs(ev.clientX - x0) < 6) return; removeEventListener('pointermove', mv, true);
        toast(k === 'hook' ? 'Hook luôn hiện ở đầu video: không dời được (sửa chữ ở tab Chữ)' : 'Thẻ kết luôn hiện ở cuối video: đổi số giây hiện ở tab Chữ › Thẻ kết'); };
      addEventListener('pointermove', mv, true); addEventListener('pointerup', () => removeEventListener('pointermove', mv, true), {capture: true, once: true});
      return;
    }
    if (!keoDuoc(k)) return;
    e.preventDefault();
    const g = gioV()[k], m = e.target.closest('.r25-m');
    let mode = m ? m.dataset.m : 'doi';
    if (!m) { const r = b.getBoundingClientRect(), z = r.width >= 40 ? 5 : 3; if (r.width >= 20) { if (e.clientX < r.left + z) mode = 'l'; else if (e.clientX > r.right - z) mode = 'r'; } }   // r29: thanh < 20px chỉ kéo thân
    R.keo = {k, mode, x0: e.clientX, y0: e.clientY, cx: e.clientX, s0: tls.scrollLeft, g0: {t0: +g.t0, t1: +g.t1}, t0: +g.t0, t1: +g.t1, h: null, alt: e.altKey, dang: false, ten: chuThanh(k)};
    addEventListener('pointermove', diChuot, true); addEventListener('pointerup', thaChuot, true); addEventListener('pointercancel', thaChuot, true);
    addEventListener('keydown', phimKeo, true); addEventListener('keyup', phimKeo, true);
  }));

  /* ================= (5) CHÉP / DÁN KIỂU CẢNH ================= */
  const KHOA = ['dong', 'hieu_ung', 'chuyen', 'mau', 'loc', 'khung', 'am_luong', 'on_dinh'];
  const sao = v => JSON.parse(JSON.stringify(v));
  function tomTat(k) {   // "Zoom vào chậm · bộ lọc Ấm · âm lượng 80%"
    const o = [];
    if (k.chuyen) o.push('vào: ' + tenGiaTri('chuyen_canh', k.chuyen));
    if (k.dong) o.push(tenGiaTri('chuyen_dong', k.dong));
    if (k.hieu_ung) o.push(tenGiaTri('hieu_ung', k.hieu_ung));
    if (k.loc && k.loc.ten) o.push('bộ lọc ' + (typeof hinhTen === 'function' ? hinhTen(k.loc.ten) : k.loc.ten));
    if (k.mau) o.push('màu riêng');
    if (k.khung) o.push('khung ' + Math.round(khungC({khung: k.khung}).zoom * 100) + '%');
    if (k.am_luong != null) o.push(k.am_luong === 0 ? 'tắt tiếng' : 'âm lượng ' + Math.round(k.am_luong * 100) + '%');
    if (k.on_dinh) o.push('chống rung');
    return o.length ? o.join(' · ') : 'kiểu trơn (không hiệu ứng)';
  }
  function chepKieu(id) {
    id = id || S.sel.canh; const i = S.plan.canh.findIndex(c => c._id === id); if (i < 0) return toast('Chọn 1 cảnh trước rồi chép kiểu', true);
    const c = S.plan.canh[i], k = {}; KHOA.forEach(x => { if (c[x] != null) k[x] = sao(c[x]); });
    R.kieu = {tu: 'cảnh ' + (i + 1), id, k}; ghi('st-kieu-canh', JSON.stringify(R.kieu));
    toast('Đã chép kiểu cảnh ' + (i + 1) + ': ' + tomTat(k) + ' · bấm phải cảnh khác › Dán kiểu (Ctrl+Alt+V)');
  }
  function apKieu(p, ids, k, giu) {   // dán kiểu k vào các cảnh ids của kế hoạch p; giu: số cảnh giữ chuyển cảnh vào
    p.canh.forEach((c, j) => {
      if (!ids.includes(c._id)) return;
      KHOA.forEach(x => {
        if (x === 'chuyen' && (j === 0 || laChoChia(p.canh[j - 1], c))) { if (giu && (k.chuyen || null) !== (c.chuyen || null)) giu.add(j + 1); return; }   // cảnh đầu / chỗ chia: giữ chuyển cảnh vào
        if (k[x] == null) delete c[x]; else c[x] = sao(k[x]);
      });
    });
  }
  function danKieu(ids) {
    if (!R.kieu) return toast('Chưa chép kiểu: bấm phải 1 cảnh › Chép kiểu cảnh này (Ctrl+Alt+C)', true);
    ids = (ids || []).filter(id => S.plan.canh.some(c => c._id === id)); if (!ids.length) return toast('Chọn 1 cảnh (hoặc quét chọn nhiều cảnh) rồi dán kiểu', true);
    const k = R.kieu.k, so = ids.map(id => S.plan.canh.findIndex(c => c._id === id) + 1).sort((a, b) => a - b);
    const thu = sao(S.plan); apKieu(thu, ids, k, null);
    if (JSON.stringify(thu) === JSON.stringify(S.plan)) return toast((so.length > 1 ? so.length + ' cảnh' : 'Cảnh ' + so[0]) + ' đã cùng kiểu với ' + R.kieu.tu);
    const giu = new Set();
    doi(p => apKieu(p, ids, k, giu));   // 1 bước Ctrl+Z cho cả nhóm
    R.dan = new Set(ids); apDan(); clearTimeout(R.danHen); R.danHen = setTimeout(() => { R.dan = null; apDan(); }, 1100);   // khối vừa dán sáng viền vàng chốc lát
    toast('Đã dán kiểu ' + R.kieu.tu + ' vào ' + (so.length > 1 ? so.length + ' cảnh' : 'cảnh ' + so[0]) + (giu.size ? ' (cảnh ' + [...giu].join(', ') + ' giữ chuyển cảnh vào: cảnh đầu / chỗ chia)' : '') + ' · Ctrl+Z để bỏ');
  }
  function apDan() { $$('#tCanh .blk[data-id]').forEach(el => el.classList.toggle('r25-dan', !!(R.dan && R.dan.has(el.dataset.id)))); }
  const nhomCanh = () => { try { const n = window.QUET && S.quet ? QUET.nhom() : null; const c = n ? n.canh : []; return c.length && (c.length + n.k.length) >= 2 ? c : null; } catch (e) { return null; } };
  function mucKieu(id) {
    const i = S.plan.canh.findIndex(c => c._id === id), cung = R.kieu && R.kieu.id === id;
    return [{t: 'Chép kiểu cảnh này', ic: 'chepKieu', phim: 'Ctrl+Alt+C', ly_do: 'Chép chuyển động, hiệu ứng, chuyển cảnh vào, màu, bộ lọc, khung, âm lượng, chống rung (không chép clip / giờ)', f: () => chepKieu(id)},
      {t: 'Dán kiểu vào cảnh này', ic: 'danKieu', phim: 'Ctrl+Alt+V', tat: !R.kieu, nhan: R.kieu ? (cung && i >= 0 ? 'cảnh này' : R.kieu.tu) : '',
        ly_do: R.kieu ? 'Dán kiểu ' + R.kieu.tu + ': ' + tomTat(R.kieu.k) : 'Chưa chép kiểu: bấm phải 1 cảnh › Chép kiểu cảnh này', f: () => danKieu([id])}];
  }
  const gocMenuCanh = menuCanh;
  menuCanh = function (id) {
    const ds = gocMenuCanh.apply(this, arguments);
    try { if (ds.length) { let j = ds.findIndex(it => it && it.nhom === 'Sửa cảnh'); if (j > 0 && ds[j - 1] === '-') j--; ds.splice(j < 0 ? ds.length : j, 0, '-', ...mucKieu(id)); } }
    catch (e) { console.error(e); }
    return ds;
  };
  // menu nhóm quét chọn (dev/_mod-quet.js): bấm phải lên nhóm -> thêm "Dán kiểu vào N cảnh"
  let menuNhomLuc = 0;
  document.addEventListener('contextmenu', e => { if (e.target.closest && e.target.closest('#tCanh .blk[data-id], #tChu .bar[data-k], #tPd .bar[data-k]') && nhomCanh()) menuNhomLuc = performance.now(); }, true);
  const gocMoMenu = moMenu;
  moMenu = function (x, y, ds) {
    try {
      const c = performance.now() - menuNhomLuc < 300 && Array.isArray(ds) && ds[0] && ds[0].nhom && /^Đã chọn/.test(ds[0].nhom) ? nhomCanh() : null;
      if (c) { menuNhomLuc = 0; let j = ds.findIndex(it => it && it.t === 'Bỏ chọn'); if (j > 0 && ds[j - 1] === '-') j--;
        ds = ds.slice(); ds.splice(j < 0 ? ds.length : j, 0, '-', {t: 'Dán kiểu vào ' + c.length + ' cảnh', ic: 'danKieu', phim: 'Ctrl+Alt+V', tat: !R.kieu, nhan: R.kieu ? R.kieu.tu : '',
          ly_do: R.kieu ? 'Dán kiểu ' + R.kieu.tu + ': ' + tomTat(R.kieu.k) : 'Chưa chép kiểu: bấm phải 1 cảnh › Chép kiểu cảnh này', f: () => danKieu(c)}); }
    } catch (er) { console.error(er); }
    return gocMoMenu.call(this, x, y, ds);
  };

  /* ================= phím: N = bật / tắt hít · Ctrl+Alt+C / V = chép / dán kiểu cảnh ================= */
  document.addEventListener('keydown', e => {
    if ($('#edit').hidden || $('.mbg') || !S.plan || go() || R.keo) return;
    if ((e.ctrlKey || e.metaKey) && e.altKey && !e.shiftKey && (e.code === 'KeyC' || e.code === 'KeyV')) {
      e.preventDefault(); e.stopPropagation();
      const laCanh = !S.selLoai || S.selLoai === 'canh';   // đang chọn thanh chữ ('chu'), khối tiếng tách ('am'), tiếng hiệu ứng ('amtv'): không phải cảnh
      if (e.code === 'KeyC') { if (!laCanh) return toast('Bấm chọn 1 cảnh rồi Ctrl+Alt+C để chép kiểu cảnh', true); return chepKieu(S.sel.canh); }
      const n = nhomCanh(); if (n) return danKieu(n);
      if (!laCanh) return toast('Bấm chọn 1 cảnh (hoặc quét chọn nhiều cảnh) rồi Ctrl+Alt+V để dán kiểu', true);
      return danKieu([S.sel.canh]);
    }
    if (e.ctrlKey || e.metaKey || e.altKey || e.repeat) return;
    if (e.key === 'n' || e.key === 'N') { e.preventDefault(); datHit(!R.hit, true); }
  });

  /* ================= bọc veTimeline SAU CÙNG (sau mọi mô-đun khác: tách âm, video trống…): làn gọn, tay nắm, thanh đang kéo ================= */
  queueMicrotask(() => {
    const goc = veTimeline;
    veTimeline = function () { const r = goc.apply(this, arguments); try { ganMep(); gonLai(); apKeo(); if (R.dan) apDan(); } catch (e) { console.error(e); } return r; };
    if (S.plan) veTimeline(); else gonLai();
  });
  // bảng phím tắt (dev/_mod-r25-bang.js đọc window.PHIM_TAT; mục trùng id thì mục sau thay mục trước)
  (window.PHIM_TAT = window.PHIM_TAT || []).push(
    {id: 'nam-cham', nhom: 'Timeline', phim: ['N'], ten: 'Bật / tắt tự hít (nam châm)'},
    {id: 'keo-chu-alt', nhom: 'Timeline', phim: ['Alt'], ten: 'Giữ khi kéo chữ: tắt hít tạm'},
    {id: 'keo-chu-huy', nhom: 'Timeline', phim: ['Esc'], ten: 'Đang kéo chữ: huỷ kéo'},
    {id: 'chep-kieu-canh', nhom: 'Sửa cảnh', phim: ['Ctrl+Alt+C'], ten: 'Chép kiểu cảnh'},
    {id: 'dan-kieu-canh', nhom: 'Sửa cảnh', phim: ['Ctrl+Alt+V'], ten: 'Dán kiểu vào cảnh / nhóm'});
  window.TL25 = {gon: () => R.gon, datGon, hit: () => R.hit, datHit, kieu: () => R.kieu, chep: chepKieu, dan: danKieu, keo: () => R.keo};
})();
