/* ============================== XEM CHUYỂN CẢNH TRONG KHUNG XEM NHANH (r27, 5/11/2026) ==============================
   Anh: "hiệu ứng chuyển cảnh chưa sài được". Kế hoạch + bản xuất đã có chuyển cảnh, nhưng khung Xem nhanh cắt thẳng ở chỗ chồng 2 cảnh
   (doanLuc lấy đoạn sau) -> bấm chọn, phát thử không thấy gì, chỉ Bản nháp / xuất mới thấy. Giờ khung xem vẽ gần giống bản xuất (cùng
   kiểu ffmpeg xfade của bộ dựng, so bằng ffmpeg trên ảnh màu: hướng trượt / lau, mép mềm, nháy đen / trắng, zoom…):
   - vạch đỏ vào chỗ chồng của đoạn d ([d.bd, d.bd + d.chuyen)): khung cảnh trước chụp vào canvas (#xcA) đè lên khung xem; cảnh sau
     (#vids + #ph, gói trong #xcB) phát như cũ bên dưới; hiệu ứng CSS (opacity / transform / clip-path / mask / lọc mờ / vỡ điểm) theo
     tiến độ p = (t - d.bd) / d.chuyen. Lúc phát: khung cảnh trước đứng yên (0,2–0,45s, không lộ), zoom / lia của nó vẫn chạy tiếp.
     Lúc đứng / kéo vạch đỏ: đúng khung bản xuất (tua thẻ video cảnh trước đang ẩn, hoặc 1 thẻ video phụ nếu 2 cảnh cùng 1 thẻ).
   - 2 cảnh cùng 1 clip (cùng 1 thẻ video): lúc phát chụp TRƯỚC khi veKhung tua thẻ sang cảnh sau -> không cần 2 thẻ phát cùng lúc.
   - kiểu: máy chủ gửi kèm d.chuyen_ten / d.chuyen_xfade (sua_tay_may.lenh_xem, kể cả "Trộn" kiểu Film Impact); bản cũ không có thì
     kiểu riêng cảnh -> kiểu chung (kieuDung). Khoá -> lớp xem thử của Thư viện (TV_XC, _thu-vien.js + _mod-thu-vien-them.js) -> hiệu ứng
     (XC_HU); không biết thì theo xfade; cuối cùng mờ chéo — có chỗ chồng là có hiệu ứng, không bao giờ cắt thẳng. Chỗ nối liền / cắt
     thẳng: máy chủ không cho chồng (d.chuyen = 0) -> không vẽ gì.
   - KHÔNG đổi: đồng hồ phát theo thẻ video đang hiện (clock-follow trong chay), thẻ chống rung (vidDoan), tiếng (tách âm / nhạc / giọng
     không đụng tới), chữ / phụ đề trên cùng (#xcW z-index 0 nằm trước #lops), video trống (không có đoạn -> tắt), bản nháp (S.mode).
   Móc: chỉ bọc veKhung (như _mod-tach-am.js), dời #vids + #ph vào #xcB lúc nạp trang (id giữ nguyên). Kiểm: dev/thu-sua-tay/thu_xem_chuyen.py */
(function () {
  const st = document.getElementById('stage'), vids = document.getElementById('vids'), ph = document.getElementById('ph');
  if (typeof veKhung !== 'function' || !st || !vids || !ph) return;
  const mk = (tag, id, cls) => { const e = document.createElement(tag); if (id) e.id = id; if (cls) e.className = cls; return e; };
  const W = mk('div', 'xcW', 'xc-w'), Bw = mk('div', 'xcB', 'xc-b'), Aw = mk('div', 'xcA', 'xc-a'), A2 = mk('div', 'xcA2', 'xc-a'), F = mk('div', 'xcF', 'xc-f');
  // cA: khung cảnh trước (chụp thẳng vào, cỡ vừa khung xem), cAp: bản vỡ điểm, cA2: nửa phải (cửa lùa), cB: cảnh sau vỡ điểm
  const cA = mk('canvas', '', 'xc-c'), cAp = mk('canvas', '', 'xc-c px'), cA2 = mk('canvas', '', 'xc-c'), cB = mk('canvas', 'xcBp', 'xc-bp');
  [cA, cAp, cA2, cB].forEach(c => { c.width = 2; c.height = 2; try { c.getContext('2d', {alpha: false}); } catch (e) {} });
  cAp.hidden = true;
  [Aw, A2, F].forEach(e => e.setAttribute('aria-hidden', 'true'));
  st.insertBefore(W, vids); Bw.append(vids, ph, cB); Aw.append(cA, cAp); A2.append(cA2); W.append(Bw, Aw, A2, F);
  // mờ ngang (mo_chuyen_dong = xfade hblur): lọc SVG chỉ làm mờ theo chiều ngang, mép không lộ nền đen
  document.body.insertAdjacentHTML('beforeend', '<svg class="tv-svg" width="0" height="0" aria-hidden="true" focusable="false" style="position:absolute">'
    + '<filter id="xcMo" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB"><feGaussianBlur id="xcMoB" stdDeviation="0 0" edgeMode="duplicate"/>'
    + '<feComponentTransfer><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer></filter></svg>');
  const moB = document.getElementById('xcMoB');

  /* ---------- hiệu ứng: p 0 -> 1 = cảnh trước -> cảnh sau. A / A2 = khung cảnh trước, B = cảnh sau, F = lớp màu (nháy) ---------- */
  const cl = (x, a, b) => Math.min(b, Math.max(a, x));
  const ss = (a, b, x) => { const u = cl((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u); };
  const eio = p => p < 0.5 ? 4 * p * p * p : 1 - 4 * Math.pow(1 - p, 3);   // nhanh dần rồi chậm dần (bản "mượt" của bộ dựng)
  const r4 = x => Math.round(x * 1e4) / 1e4;
  const mask = v => `-webkit-mask-image:${v};mask-image:${v};`;
  const g = (huong, f, n = 12) => { const s = []; for (let i = 0; i <= n; i++) s.push(`rgba(0,0,0,${r4(cl(f(i / n), 0, 1))}) ${r4(i / n * 100)}%`); return mask(`linear-gradient(${huong},${s.join(',')})`); };
  const gTron = f => { const s = []; for (let i = 0; i <= 12; i++) s.push(`rgba(0,0,0,${r4(cl(f(i / 12), 0, 1))}) ${r4(i / 12 * 100)}%`); return mask(`radial-gradient(circle farthest-corner at 50% 50%,${s.join(',')})`); };
  const tx = (x, y) => `transform:translate(${r4(x * 100)}%,${r4(y * 100)}%);`;
  const lau = (huong, p) => ({A: g(huong, s => 1 - ss(0, 1, 2 * p - s))});   // lau mép mềm (smooth*): huong = từ mép cảnh sau hiện ra
  const nhay = (p, mau) => {   // fadeblack / fadewhite của ffmpeg (phase 0,2): A -> màu -> B, đúng hệ số trộn
    const q = 1 - p, s1 = ss(0.8, 1, q), s2 = ss(0.2, 1, q), kA = q * s1, kF = q * (1 - s1) + (1 - q) * s2;
    return {A: `opacity:${r4(kF < 0.9999 ? kA / (1 - kF) : 0)};`, F: `background:${mau};opacity:${r4(kF)};`};
  };
  const HU = {
    fade: p => ({A: `opacity:${r4(1 - p)};`}),
    fadefast: p => ({A: `opacity:${r4(Math.pow(1 - p, 1.4))};`}),
    fadeblack: p => nhay(p, '#000'), fadewhite: p => nhay(p, '#fff'),
    slideleft: p => ({A: tx(-p, 0), B: tx(1 - p, 0)}), slideleft_e: p => HU.slideleft(eio(p)),
    slideright: p => ({A: tx(p, 0), B: tx(p - 1, 0)}), slideright_e: p => HU.slideright(eio(p)),
    slideup: p => ({A: tx(0, -p), B: tx(0, 1 - p)}), slideup_e: p => HU.slideup(eio(p)),
    coverleft: p => ({B: 'z-index:2;' + tx(1 - p, 0)}), coverleft_q: p => ({B: 'z-index:2;' + tx(Math.pow(1 - p, 4), 0)}),
    coverright: p => ({B: 'z-index:2;' + tx(p - 1, 0)}),
    coverup: p => ({B: 'z-index:2;' + tx(0, 1 - p)}), coverup_q: p => ({B: 'z-index:2;' + tx(0, Math.pow(1 - p, 4))}),
    revealleft: p => ({A: tx(-p, 0)}), revealup: p => ({A: tx(0, -p)}), revealup_e: p => HU.revealup(eio(p)),
    smoothleft: p => lau('to left', p), smoothright: p => lau('to right', p), smoothup: p => lau('to top', p), smoothdown: p => lau('to bottom', p),
    vertopen: p => ({A: g('to right', u => 1 - ss(0, 1, 2 * p - Math.abs(2 * u - 1)), 16)}),
    horzopen: p => ({A: g('to bottom', u => 1 - ss(0, 1, 2 * p - Math.abs(2 * u - 1)), 16)}),
    diagtl: p => ({A: g('to bottom right', v => 1 - ss(0, 1, v * v + 2 * p - 1))}),
    diagbr: p => ({A: g('to top left', v => 1 - ss(0, 1, v * v + 2 * p - 1))}),
    circleopen: p => ({A: gTron(r => ss(0, 1, r + (0.5 - p) * 3))}),
    wipeup: p => ({A: `clip-path:inset(0 0 ${r4(p * 100)}% 0);`}),
    hrslice: p => {   // 10 lát dọc, mỗi lát cảnh sau lấp dần từ mép trái lát, lát bên trái đi trước
      const s = [];
      for (let k = 0; k < 10; k++) { const u0 = k / 10, f = 1 - ss(-0.5, 0, u0 + 0.05 - 1.5 * p), m = r4((u0 + f / 10) * 100);
        s.push(`transparent ${r4(u0 * 100)}%`, `transparent ${m}%`, `#000 ${m}%`, `#000 ${r4((u0 + 0.1) * 100)}%`); }
      return {A: mask(`linear-gradient(to right,${s.join(',')})`)};
    },
    squeezeh: p => ({A: `transform:scaleY(${r4(Math.max(1 - p, 1e-4))});`}),
    zoomin: p => { const zf = ss(0.5, 1, 1 - p); return {A: `transform:scale(${r4(Math.min(40, 1 / Math.max(zf, 0.025)))});opacity:${r4(ss(0, 0.5, 1 - p))};`}; },
    zoom_ra: p => ({A: `transform:scale(${r4(1 + 0.25 * p * p)});opacity:${r4(1 - ss(0, 1, p))};`, B: `transform:scale(${r4(1 + 0.5 * (1 - p) * (1 - p))});`}),
    hblur: p => ({A: `opacity:${r4(1 - p)};filter:url(#xcMo);`, B: 'filter:url(#xcMo);', mo: p <= 0.5 ? 2 * p : 2 * (1 - p)}),
    pixelize: p => ({A: `opacity:${r4(1 - p)};`, px: 2 * (Math.ceil(Math.min(p, 1 - p) * 50) / 50) / 20}),   // px: cỡ ô / cạnh ngắn khung ra
    cua_lua: p => { const e = eio(p) * 50; return {A: `clip-path:inset(0 50% 0 0);transform:translateX(${r4(-e)}%);`, A2: `clip-path:inset(0 0 0 50%);transform:translateX(${r4(e)}%);`}; },
    lat_the: p => { const c = Math.abs(Math.cos(Math.PI * p)), sy = 1 + 0.06 * Math.sin(Math.PI * p), sc = `transform:scale(${r4(Math.max(c, 1e-3))},${r4(sy)});`;
      return p < 0.5 ? {A: sc, B: 'opacity:0;', nen: '#03231a'} : {A: 'opacity:0;', B: sc, nen: '#03231a'}; },
    lac_keo: p => { const sn = Math.sin(Math.PI * p), s = 1 + 0.25 * sn, dx = 0.09 * sn * Math.sin(6 * Math.PI * p), dy = 0.02 * sn * Math.cos(8 * Math.PI * p);
      const tf = `transform:translate(${r4(-dx * s * 100)}%,${r4(-dy * s * 100)}%) scale(${r4(s)});`; return {A: tf + `opacity:${r4(1 - cl((p - 0.42) / 0.16, 0, 1))};`, B: tf}; },
  };
  // lớp xem thử của Thư viện (TV_XC: khoá kiểu -> lớp) -> hiệu ứng khung xem. Bản "_e" = có gia tốc (custom của bộ dựng), "_q" = đè chậm dần
  const XC_HU = {cat: '', fade: 'fade', fadeDai: 'fade', fadeNhanh: 'fadefast', trang: 'fadewhite', den: 'fadeblack',
    ngang: 'slideleft', doc: 'slideup', ngangMuot: 'slideleft_e', docMuot: 'slideup_e', phaiMuot: 'slideright_e',
    deDoc: 'coverup_q', deNgang: 'coverleft_q', dePhai: 'coverright', keoLen: 'revealup_e', keoNgang: 'revealleft',
    lau: 'smoothleft', lauPhai: 'smoothright', lauDoc: 'smoothup', lauXuong: 'smoothdown', cheo: 'diagtl', cheoNguoc: 'diagbr', lauLen: 'wipeup', latDoc: 'hrslice',
    zoom: 'zoomin', zoomRa: 'zoom_ra', tron: 'circleopen', cua: 'vertopen', cuaNgang: 'horzopen', cuaLua: 'cua_lua', latThe: 'lat_the',
    nhoe: 'hblur', vo: 'pixelize', epNgang: 'squeezeh', lacKeo: 'lac_keo'};
  function kieuCua(d) {   // khoá kiểu chuyển cảnh ở chỗ nối này: máy chủ gửi (chuyen_ten) > kiểu riêng cảnh > kiểu chung
    if (d.chuyen_ten) return d.chuyen_ten;
    const ds = (S.plan || {}).canh || [], c = (d.id && ds.find(x => x._id === d.id)) || ds[d.canh] || {};   // id: máy chủ gộp 2 nửa chia liền -> chỉ số lệch
    return c.chuyen && c.chuyen !== 'tron_poly' && c.chuyen !== 'cat_cung' ? c.chuyen : kieuDung('chuyen_canh');
  }
  function hieuUng(d) {
    const k = kieuCua(d), lop = typeof TV_XC === 'object' && k !== 'tron_poly' ? TV_XC[k] : null;
    const moi = window.XC_MOI && XC_MOI.hu(k); if (moi) return moi;   // r35: kiểu chuyển cảnh mới (_mod-chuyen-moi.js, vẽ bằng cssChuyen)
    return (lop && XC_HU[lop]) || (d.chuyen_xfade && HU[d.chuyen_xfade] ? d.chuyen_xfade : '') || 'fade';   // không bao giờ cắt thẳng
  }

  /* ---------- trạng thái + chụp khung cảnh trước ---------- */
  const X = {bat: true, khoa: '', coA: false, last: null, cho: null, daVe: '', vua: null, verA: 0, verCA: -1, kA: -1, verA2: -1, nha: null, nhaHen: 0, anh: null,
    dem: {vao: 0, ra: 0, chup: 0, chupPhat: 0, chupDung: 0, chupAnh: 0}};
  const vid = x => typeof vidDoan === 'function' ? vidDoan(x) : VID[src(x.file)];
  const khungRa = () => { const k = (S.plan && S.plan.khung) || [1080, 1920]; return [+k[0] || 1080, +k[1] || 1920]; };
  function veA(n) {   // n: <video> / <img> đang có khung cảnh trước -> cA. Cỡ: vừa khung xem (x1,5 cho zoom, x tỉ lệ màn), không quá cỡ gốc
    const w0 = n.videoWidth || n.naturalWidth || 0, h0 = n.videoHeight || n.naturalHeight || 0; if (!w0 || !h0) return false;
    const k = Math.min(1, Math.ceil((st.clientWidth || 400) * (window.devicePixelRatio || 1) * 1.5) / w0), w = Math.max(2, Math.round(w0 * k)), h = Math.max(2, Math.round(h0 * k));
    try { if (cA.width !== w || cA.height !== h) { cA.width = w; cA.height = h; } cA.getContext('2d').drawImage(n, 0, 0, w, h); } catch (e) { return false; }
    X.coA = true; X.verA++; X.dem.chup++; return true;
  }
  function chupPhat(a, want) {   // đang phát, vừa vào chỗ chồng: thẻ / ảnh tạm còn đang hiện khung cảnh trước (veKhung chưa tua sang cảnh sau)
    if (X.vua !== a) return false;   // khung vừa vẽ không phải cảnh trước (vd. tua thẳng vào giữa chỗ chồng lúc phát): lấy ảnh máy chủ
    const ea = vid(a);
    if (ea && ea.classList.contains('on') && ea.readyState >= 2 && !ea.seeking && Math.abs(ea.currentTime - want) < 0.6 && veA(ea)) { X.dem.chupPhat++; return true; }
    if (ph.classList.contains('on') && ph.complete && ph.naturalWidth && veA(ph)) { X.dem.chupPhat++; return true; }
    return false;
  }
  function nha(el) {   // thẻ video phụ (không gắn vào trang, tắt tiếng) cùng nguồn: 2 cảnh liền dùng chung 1 thẻ, lúc đứng cần khung cảnh trước
    const u = el.currentSrc || el.getAttribute('src') || '';
    let h = X.nha;
    if (!h) { h = X.nha = document.createElement('video'); h.muted = true; h.preload = 'auto'; h.playsInline = true; }
    if (h.dataset.u !== u) { h.dataset.u = u; h.src = u; }
    return h;
  }
  function henNha() { clearTimeout(X.nhaHen); X.nhaHen = setTimeout(() => { if (!X.khoa && X.nha) { const h = X.nha; X.nha = null; h.removeAttribute('src'); try { h.load(); } catch (e) {} } }, 5000); }
  function chupTu(el, want) {   // đứng / kéo vạch đỏ: tua thẻ (đang ẩn) tới đúng khung cảnh trước của bản xuất rồi vẽ
    const tk = X.khoa + '@' + want.toFixed(3);
    if (X.daVe === tk) return;
    if (el.readyState >= 2 && !el.seeking && Math.abs(el.currentTime - want) < 0.015) { if (veA(el)) { X.daVe = tk; X.dem.chupDung++; } return; }
    X.cho = {el, want, tk};
    if (!el._xcNghe) { el._xcNghe = 1; const f = () => xongTua(el); el.addEventListener('seeked', f); el.addEventListener('loadeddata', f); }
    if (!el.seeking || Math.abs(el.currentTime - want) >= 0.015) { try { el.currentTime = want; } catch (e) {} }
  }
  function xongTua(el) {
    const c = X.cho; if (!c || c.el !== el || S.playing || el.seeking || el.readyState < 2) return;
    if (Math.abs(el.currentTime - c.want) >= 0.015) { try { el.currentTime = c.want; } catch (e) {} return; }
    X.cho = null;
    if (!X.last || c.tk.indexOf(X.khoa + '@') !== 0) return;
    if (veA(el)) { X.daVe = c.tk; X.dem.chupDung++; ap(); }
  }
  function chupAnh(a, want) {   // chưa có bản xem nhẹ của cảnh trước: ảnh khung từ máy chủ (như ảnh tạm #ph)
    const u = thumbUrl(src(a.file), want, 720), tk = X.khoa + '@anh' + u;
    if (X.daVe === tk || (X.anh && X.anh._tk === tk)) return;
    const im = new Image(); im._tk = tk; X.anh = im;
    im.onload = () => { if (X.anh !== im || tk.indexOf(X.khoa + '@') !== 0 || !X.last) return; if (veA(im)) { X.daVe = tk; X.dem.chupAnh++; ap(); } };
    im.src = u;
  }
  function chupDung(a, d, want) {
    const ea = vid(a), eb = vid(d);
    if (ea && (ea.currentSrc || ea.getAttribute('src')) && ea.readyState >= 1) return chupTu(ea !== eb ? ea : nha(ea), want);
    chupAnh(a, want);
  }

  /* ---------- vẽ 1 khung ---------- */
  function datCA(px, coA2) {   // khung cảnh trước: nét (cA) hoặc vỡ điểm (cAp nhỏ, phóng to pixelated; px = cỡ ô / cạnh ngắn khung ra)
    let kk = 0;
    if (px > 0) { const [w0, h0] = khungRa(), k = px * Math.min(w0, h0) * cA.width / w0; kk = k >= 1.5 ? Math.round(k * 10) / 10 : 0; }
    if (X.kA !== kk || X.verCA !== X.verA) {
      X.kA = kk; X.verCA = X.verA;
      if (kk) { const w = Math.max(1, Math.round(cA.width / kk)), h = Math.max(1, Math.round(cA.height / kk));
        if (cAp.width !== w || cAp.height !== h) { cAp.width = w; cAp.height = h; } cAp.getContext('2d').drawImage(cA, 0, 0, w, h); }
      cAp.hidden = !kk; cA.hidden = !!kk;
    }
    if (coA2 && X.verA2 !== X.verA) {
      X.verA2 = X.verA; if (cA2.width !== cA.width || cA2.height !== cA.height) { cA2.width = cA.width; cA2.height = cA.height; }
      cA2.getContext('2d').drawImage(cA, 0, 0);
    }
  }
  function hinhA(o, coA2) {   // zoom / lia / khung / màu của cảnh trước tại giờ này (như veKhung vẽ cảnh đó)
    const a = o.a, u = cl((o.t - a.bd) / Math.max(0.01, a.dur), 0, 1), e = ease(a.easing, u);
    const Z = a.z0 === a.z1 ? a.z0 : a.z0 * Math.pow(a.z1 / a.z0, e), Xx = a.x0 + (a.x1 - a.x0) * e, tt = ttDoan(a);
    hinhVideo(cA, Z, Xx, tt.kh, tt.mau, a.the_hoi);
    [cAp, coA2 ? cA2 : null].forEach(c => { if (c) ['transform', 'transformOrigin', 'objectPosition', 'filter'].forEach(k => { c.style[k] = cA.style[k]; }); });
  }
  function veBp(o, px) {   // vỡ điểm cảnh sau: thẻ đang hiện -> canvas nhỏ phóng to (pixelated), cùng khung / zoom / màu với thẻ
    const el = vid(o.d), n = el && el.classList.contains('on') && el.readyState >= 2 && !el.seeking ? el : (ph.classList.contains('on') && ph.complete && ph.naturalWidth ? ph : null);
    if (!n && el && !S.playing && !el._xcBp) { el._xcBp = 1; el.addEventListener('seeked', () => { el._xcBp = 0; if (X.last && !S.playing) ap(); }, {once: true}); }   // đứng: thẻ đang tua -> tua xong vẽ lại
    const w0 = n ? (n.videoWidth || n.naturalWidth) : 0, h0 = n ? (n.videoHeight || n.naturalHeight) : 0, [kw, kh] = khungRa(), k = px * Math.min(kw, kh) * w0 / kw;
    if (!n || !w0 || k < 1.5) { cB.classList.remove('on'); return; }
    const w = Math.max(1, Math.round(w0 / k)), h = Math.max(1, Math.round(h0 / k));
    if (cB.width !== w || cB.height !== h) { cB.width = w; cB.height = h; }
    try { cB.getContext('2d').drawImage(n, 0, 0, w, h); } catch (e) { cB.classList.remove('on'); return; }
    ['transform', 'transformOrigin', 'objectPosition', 'filter'].forEach(x => { cB.style[x] = n.style[x]; });
    cB.classList.add('on');
  }
  function ap() {
    const o = X.last; if (!o) return;
    const r = (HU[o.hu] ? HU[o.hu](o.p) : window.XC_MOI && XC_MOI.ap(o.hu, o.p, st.clientWidth || 400, khungRa())) || {}, coA2 = !!r.A2;   // r35: 'poly:<id>' = kiểu mới
    W.classList.add('xc-dang'); W.dataset.xc = o.hu; W.style.background = r.nen || '';
    if (X.coA) { datCA(r.px || 0, coA2); hinhA(o, coA2); }
    Aw.style.cssText = r.A || ''; Aw.classList.toggle('on', X.coA);
    A2.style.cssText = r.A2 || ''; A2.classList.toggle('on', X.coA && coA2);
    Bw.style.cssText = r.B || '';
    F.style.cssText = r.F || ''; F.classList.toggle('on', !!r.F);
    if (r.mo != null) { const [kw] = khungRa(), sw = st.clientWidth || 400; moB.setAttribute('stdDeviation', r4(0.29 * (1 + kw / 2 * r.mo) * sw / kw) + ' 0'); }
    if (r.px) veBp(o, r.px); else cB.classList.remove('on');
  }
  function tat() {
    if (!X.khoa) return null;
    X.khoa = ''; X.coA = false; X.last = null; X.cho = null; X.daVe = ''; X.anh = null; X.dem.ra++;
    W.classList.remove('xc-dang'); delete W.dataset.xc; W.style.background = '';
    Aw.classList.remove('on'); A2.classList.remove('on'); cB.classList.remove('on'); F.classList.remove('on');
    Aw.style.cssText = ''; A2.style.cssText = ''; Bw.style.cssText = ''; F.style.cssText = '';
    henNha();
    return null;
  }
  function truoc() {   // TRƯỚC veKhung gốc: còn chụp được khung cảnh trước từ thẻ đang hiện (2 cảnh cùng 1 thẻ)
    const v = S.view;
    if (!X.bat || !v || S.mode !== 'xem' || !(v.doan || []).length) return tat();
    const t = S.t, d = doanLuc(t);
    if (!d || !(d.chuyen > 0) || t < d.bd - 1e-6 || t >= d.bd + d.chuyen - 1e-6) return tat();
    const i = v.doan.indexOf(d), a = v.doan[i - 1]; if (!a) return tat();
    const ea = vid(a), khoa = [i, d.bd, d.chuyen, a.file, a.tu, a.den, d.file, ea && ea.dataset.od ? 'od' : ''].join('|');
    if (khoa !== X.khoa) { X.khoa = khoa; X.coA = false; X.daVe = ''; X.cho = null; X.anh = null; X.dem.vao++; clearTimeout(X.nhaHen); }
    X.last = {hu: hieuUng(d), p: cl((t - d.bd) / d.chuyen, 0, 1), a, d, t, i};
    const want = gioClip(a, Math.min(t, a.bd + a.dur - 0.001));
    if (S.playing) { if (!X.coA && !chupPhat(a, want)) chupAnh(a, want); }
    else chupDung(a, d, want);
    return X.last;
  }
  const gocKhung = veKhung;
  veKhung = function () {
    let o = null;
    try { o = truoc(); } catch (e) { console.error(e); try { tat(); } catch (e2) {} }
    const r = gocKhung.apply(this, arguments);
    try { if (o && X.last === o) ap(); } catch (e) { console.error(e); try { tat(); } catch (e2) {} }
    try { X.vua = S.view && (S.view.doan || []).length ? doanLuc(S.t) : null; } catch (e) { X.vua = null; }   // đoạn khung xem vừa vẽ
    return r;
  };
  // để kiểm thử / tắt nhanh: xemChuyen.bat = false -> khung xem cắt thẳng như cũ
  window.xemChuyen = {
    get bat() { return X.bat; }, set bat(v) { X.bat = !!v; if (!v) tat(); },
    hieuUng, kieuCua, HU: Object.keys(HU), XC_HU,
    trangThai: () => ({dang: !!X.khoa, khoa: X.khoa, hu: X.last ? X.last.hu : null, p: X.last ? X.last.p : null, coA: X.coA, cho: !!X.cho,
      A: Aw.classList.contains('on') ? Aw.style.cssText : null, A2: A2.classList.contains('on') ? A2.style.cssText : null, B: Bw.style.cssText,
      F: F.classList.contains('on') ? F.style.cssText : null, nen: W.style.background, px: cB.classList.contains('on'), kA: X.kA,
      canvas: [cA.width, cA.height], dem: Object.assign({}, X.dem)}),
  };
})();
