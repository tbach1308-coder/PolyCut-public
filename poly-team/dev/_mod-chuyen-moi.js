/* ============================== CHUYỂN CẢNH MỚI KIỂU TREND (r35, 11/11/2026) ==============================
   Anh (11/11 10:54): "hiệu ứng chuyển cảnh còn xấu quá" -> duyệt 15 kiểu mới (mẫu 11:55): ĐƯA HẾT vào app, ẨN kiểu cũ xấu / chậm / trùng.
   Kiểu mới = 1 file JSON 'poly-chuyen-1' (engine/chuyen-canh/<id>.json, sau này Kho effect): đường cong theo tiến độ p cho cảnh trước
   (A) / cảnh sau (B) + lớp phủ. Bộ dựng: engine/chuyen_moi.py. Trang nhận đủ đường cong qua S.info.chuyen_moi (sua_tay_may.hieu_ung_rieng)
   -> cssChuyen() vẽ lại bằng CSS (transform / filter / opacity / bo góc / bóng / lớp màu), cùng công thức đường cong với Python
   (dev/mau-chuyen/thu_xem_chuyen_moi.py so 41 điểm). Gần đúng: mép gương (CSS phóng to thêm để che), mờ toả tâm / mờ xoay (blur đều theo
   tốc độ), sọc lệch (bỏ), "Hòa theo sáng" (hoà tan thường).
   1) Thư viện › Chuyển cảnh: nhóm "Mới · trend" lên đầu (XC_NHOM), ô xem trước rê chuột chạy bằng cssChuyen trên chính 2 khung cảnh.
   2) Ẩn kiểu cũ (S.info.chuyen_an = kieu_dung › chuyen_canh_rieng.an) khỏi mọi danh sách chọn — trừ kiểu đang dùng ở video này
      (vẫn hiện, gắn "cũ", đổi được); tên vẫn đúng ở bảng phải / timeline (tenGiaTri tìm trong S.info.chuyen_rieng).
      Kiểu chung cả video: "Trộn chuyển cảnh mới" (tron_moi) thay "Trộn" cũ (tron_poly chỉ hiện khi video đang dùng, tên "Trộn kiểu cũ").
   3) Xem nhanh: _mod-xem-chuyen.js hỏi window.XC_MOI (hu: khoá kiểu -> 'poly:<id>', ap: vẽ 1 tiến độ) -> chỗ nối kiểu mới vẽ bằng cssChuyen.
   Móc: bọc dsChuyenCanh, tvChips, benKieu, mucHieuUngVideo, tvSauVe; 2 dòng trong _mod-xem-chuyen.js (hieuUng + ap). */

/*CSS_CHUYEN_BAT*/
const CCM = (function () {
  const cl = (x, a, b) => Math.min(b, Math.max(a, x));
  const r4 = x => Math.round(x * 1e4) / 1e4;
  function ease(ten, t) {
    t = cl(t, 0, 1);
    if (!ten || ten === 'lin') return t;
    if (ten.startsWith('outback')) { const s = parseFloat(ten.slice(7) || '1.4'), u = t - 1; return 1 + (s + 1) * u * u * u + s * u * u; }
    if (ten.endsWith('expo')) {
      const k = ten.slice(0, -4), fi = x => x <= 0 ? 0 : Math.pow(2, 10 * x - 10);
      return k === 'in' ? fi(t) : k === 'out' ? 1 - fi(1 - t) : t < 0.5 ? fi(2 * t) / 2 : 1 - fi(2 - 2 * t) / 2;
    }
    if (ten.endsWith('sine')) { const k = ten.slice(0, -4); return k === 'in' ? 1 - Math.cos(t * Math.PI / 2) : k === 'out' ? Math.sin(t * Math.PI / 2) : -(Math.cos(Math.PI * t) - 1) / 2; }
    const k = ten.slice(0, -1), n = +ten.slice(-1);
    return k === 'in' ? Math.pow(t, n) : k === 'out' ? 1 - Math.pow(1 - t, n) : t < 0.5 ? Math.pow(2, n - 1) * Math.pow(t, n) : 1 - Math.pow(-2 * t + 2, n) / 2;
  }
  function gt(tr, p, md) {   // y như gia_tri() của engine/chuyen_moi.py
    if (tr == null) return md;
    if (typeof tr === 'number') return tr;
    if (!Array.isArray(tr)) {
      let v = gt(tr.keys, p, md); const r = tr.rung;
      if (r && p >= (r.tu || 0)) { const u = (p - (r.tu || 0)) / Math.max(1e-6, (r.den == null ? 1 : r.den) - (r.tu || 0));
        if (u <= 1) v += r.bien_do * Math.exp(-(r.tat == null ? 4 : r.tat) * u) * Math.sin(2 * Math.PI * (r.so_lan == null ? 2 : r.so_lan) * u + (r.pha || 0)); }
      return v;
    }
    if (p <= tr[0][0]) return tr[0][1];
    for (let i = 1; i < tr.length; i++) if (p <= tr[i][0]) {
      const [p0, v0] = tr[i - 1], [p1, v1, e] = tr[i];
      return v0 + (v1 - v0) * ease(e || 'io2', (p - p0) / Math.max(1e-9, p1 - p0));
    }
    return tr[tr.length - 1][1];
  }
  // tâm + góc khung dời bao nhiêu trong màn trập -> mờ chuyển động gần đúng (dời: mờ 1 chiều; zoom / xoay: blur đều)
  function toc(b, p, h, kw, kh) {
    const pt = q => { const z = gt(b.zoom, q, 1), th = gt(b.xoay, q, 0) * Math.PI / 180, x = gt(b.x, q, 0) * kw, y = gt(b.y, q, 0) * kh;
      const cx = kw / 2 * z, cy = kh / 2 * z;
      return [x, y, x + cx * Math.cos(th) - cy * Math.sin(th), y + cx * Math.sin(th) + cy * Math.cos(th)]; };
    const a = pt(Math.max(0, p - h)), c = pt(Math.min(1, p + h));
    return {dx: c[0] - a[0], dy: c[1] - a[1], goc: Math.hypot(c[2] - a[2] - (c[0] - a[0]), c[3] - a[3] - (c[1] - a[1]))};
  }
  function ben(b, p, o, h, moId) {   // CSS 1 bên; moId: id lọc SVG mờ 1 chiều của bên này (người gọi đặt stdDeviation = moXY)
    const z = gt(b.zoom, p, 1), gx = gt(b.gian_x, p, 1), gy = gt(b.gian_y, p, 1), xo = gt(b.xoay, p, 0), ly = gt(b.lat_y, p, 0), lx = gt(b.lat_x, p, 0);
    const x = gt(b.x, p, 0), y = gt(b.y, p, 0), k = o.sw / o.kw;   // k: px khung xem / px khung ra (số đo px tính ở khung 1080 ngang)
    let bu = 1;   // mép gương: CSS không lát gương -> thu nhỏ / xoay thì phóng thêm để không lộ nền
    if ((b.vien || 'guong') !== 'trong') {
      const t = Math.abs(xo) * Math.PI / 180, r = o.kh / o.kw;
      bu = Math.max(1 / Math.max(z, 0.05), xo ? (Math.abs(Math.cos(t)) + r * Math.abs(Math.sin(t))) : 1);
    }
    const v = toc(b, p, h, o.kw, o.kh), moXY = [r4(Math.abs(v.dx) * 0.35 * k), r4(Math.abs(v.dy) * 0.35 * k)];
    // blur CSS làm mép lớp trong suốt (lộ nền tối): giới hạn bán kính + phóng thêm chút cho mép mờ nằm ngoài khung
    const mo = Math.min((gt(b.mo, p, 0) * o.kw / 1080 + 0.35 * v.goc) * k, 0.035 * o.sw);
    if ((b.vien || 'guong') !== 'trong' && mo > 0.3) bu *= 1 + 3 * mo / o.sw;
    const f = [];
    if (moId && (moXY[0] > 0.3 || moXY[1] > 0.3)) f.push(`url(#${moId})`);
    if (mo > 0.3) f.push(`blur(${r4(mo)}px)`);
    const tf = `transform:translate(${r4(x * 100)}%,${r4(y * 100)}%)` + (ly || lx ? ` perspective(${r4(2 * o.sw)}px) rotateY(${r4(ly)}deg) rotateX(${r4(lx)}deg)` : '')
      + ` rotate(${r4(xo)}deg) scale(${r4(z * gx * bu)},${r4(z * gy * bu)});`;
    const toi = gt(b.toi, p, 0), sang = gt(b.sang, p, 0);
    if (toi > 0 || sang > 0) f.push(`brightness(${r4((1 - toi) * (1 + 2.5 * sang))})`);
    if (o.tachId && o.tach > 0.3) f.push(`url(#${o.tachId})`);
    let css = tf + (f.length ? `filter:${f.join(' ')};` : '');
    const tr = gt(b.trong, p, 1); if (tr < 1) css += `opacity:${r4(tr)};`;
    const bo = gt(b.bo_goc, p, 0) * o.kw / 1080; if (bo > 0.5) css += `border-radius:${r4(bo * k)}px;overflow:hidden;`;
    const bg = gt(b.bong, p, 0); if (bg > 0) css += `box-shadow:0 ${r4(-0.012 * o.kh * k)}px ${r4(0.07 * o.kw * k)}px rgba(0,0,0,${r4(0.55 * bg)});`;
    return {css, moXY};
  }
  /* spec: kiểu 'poly-chuyen-1'; p 0 -> 1; o: {kw, kh: cỡ khung ra; sw: bề ngang khung vẽ (px); moA / moB / tachId: id lọc SVG}
     -> {A, B, F (CSS), nen, moA, moB ([x, y] px cho lọc mờ 1 chiều), tach (px lệch kênh)} — cùng dạng HU[...] của _mod-xem-chuyen.js */
  function cssChuyen(spec, p, o) {
    o = Object.assign({kw: 1080, kh: 1920, sw: 400}, o || {});
    o.dp = o.dp || 1 / Math.max(2, Math.round((spec.giay || 0.4) * 30));
    const h = (spec.mo_chuyen_dong == null ? 0.7 : spec.mo_chuyen_dong) * o.dp / 2, r = {};
    o.tach = 0;
    for (const l of spec.lop || []) if (l.kieu === 'tach_mau') o.tach = Math.max(o.tach, gt(l.manh, p, 0) * o.sw);
    const A = ben(spec.A || {}, p, o, h, o.moA), B = ben(spec.B || {}, p, o, h, o.moB), tron = spec.tron || 'cat';
    r.moA = A.moXY; r.moB = B.moXY; r.tach = r4(o.tach);
    if (tron === 'cat') {
      const cat = spec.cat_tai == null ? 0.5 : spec.cat_tai, a = p < cat;
      r.A = a ? A.css : 'opacity:0;'; r.B = a ? 'opacity:0;' : B.css;
    } else if (tron === 'sang') {   // gần đúng: hòa tan theo ngưỡng
      const e = gt(spec.nguong, p, p); r.A = A.css + `opacity:${r4(1 - e)};`; r.B = B.css;
    } else {   // phu: B đè lên A
      r.A = A.css; r.B = 'z-index:2;' + B.css;
    }
    if ((spec.nen || {}).kieu) r.nen = spec.nen.kieu === 'mau' ? spec.nen.mau : '#0d1512';
    const F = [];
    for (const l of spec.lop || []) {
      const s = gt(l.manh, p, 0); if (s <= 1e-4) continue;
      if (l.kieu === 'chop') F.push(`background:${l.mau || '#fff'};opacity:${r4(s)};`);
      else if (l.kieu === 'vet_sang') {
        const g = (l.goc == null ? 35 : l.goc), t = p * 1.3 - 0.15, cx = 50 + (t - 0.5) * Math.cos(g * Math.PI / 180) * 160, cy = 50 + (t - 0.5) * Math.sin(g * Math.PI / 180) * 160;
        const m = l.mau || ['#FFD86B', '#FFE9B8', '#FFB84D'];
        F.push(`mix-blend-mode:screen;opacity:${r4(s)};background:` + m.map((c, i) => `radial-gradient(ellipse ${r4(30 + 10 * i)}% ${r4(60 + 10 * i)}% at ${r4(cx + i * 6)}% ${r4(cy + i * 6)}%,${c},transparent 70%)`).join(',') + ';');
      } else if (l.kieu === 'rem') {
        const fe = (l.mem || 0.08) * 100, m = s * (50 + fe), g = `linear-gradient(to bottom,#000 ${r4(m - fe)}%,transparent ${r4(m)}%,transparent ${r4(100 - m)}%,#000 ${r4(100 - m + fe)}%)`;
        F.push(`background:${l.mau || '#000'};opacity:1;-webkit-mask-image:${g};mask-image:${g};`);
      }
    }
    if (F.length) r.F = F[F.length - 1];
    return r;
  }
  return {cssChuyen, gt, ease};
})();
/*CSS_CHUYEN_HET*/

(function () {
  if (typeof document === 'undefined') return;
  const SS = () => (typeof S !== 'undefined' ? S : {});   // S khai bằng const ở trang (không nằm trên window)
  const spec = id => ((SS().info || {}).chuyen_moi || {})[id];
  // lọc SVG: mờ 1 chiều cho cảnh trước / sau + tách kênh R / B (khung Xem nhanh và ô Thư viện dùng bộ riêng)
  const svgMo = id => `<filter id="${id}" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="0 0" edgeMode="duplicate"/><feComponentTransfer><feFuncA type="linear" slope="0" intercept="1"/></feComponentTransfer></filter>`;
  const svgTach = id => `<filter id="${id}" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">`
    + `<feColorMatrix in="SourceGraphic" type="matrix" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0" result="r"/><feOffset in="r" dx="0" result="ro"/>`
    + `<feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0" result="g"/>`
    + `<feColorMatrix in="SourceGraphic" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0" result="b"/><feOffset in="b" dx="0" result="bo"/>`
    + `<feComposite in="ro" in2="g" operator="arithmetic" k2="1" k3="1" result="rg"/><feComposite in="rg" in2="bo" operator="arithmetic" k2="1" k3="1"/></filter>`;
  document.body.insertAdjacentHTML('beforeend', '<svg class="tv-svg" width="0" height="0" aria-hidden="true" focusable="false" style="position:absolute">'
    + svgMo('ccmXA') + svgMo('ccmXB') + svgTach('ccmXT') + svgMo('ccmTA') + svgMo('ccmTB') + svgTach('ccmTT') + '</svg>');
  const datMo = (id, xy) => { const e = document.querySelector(`#${id} feGaussianBlur`); if (e) e.setAttribute('stdDeviation', (xy ? xy[0] + ' ' + xy[1] : '0 0')); };
  const datTach = (id, px) => { const f = document.getElementById(id); if (!f) return; const o = f.querySelectorAll('feOffset'); o[0].setAttribute('dx', String(-px)); o[1].setAttribute('dx', String(px)); };
  function ve(id, p, sw, khung, bo) {   // bo: [moA, moB, tach] id lọc
    const s = spec(id); if (!s) return null;
    const [kw, kh] = khung || [1080, 1920];
    const r = CCM.cssChuyen(s, p, {kw, kh, sw, moA: bo[0], moB: bo[1], tachId: bo[2]});
    datMo(bo[0], r.moA); datMo(bo[1], r.moB); datTach(bo[2], r.tach);
    return r;
  }

  /* ---------- Xem nhanh (_mod-xem-chuyen.js hỏi qua window.XC_MOI) ---------- */
  window.XC_MOI = {
    hu: k => (k && spec(k) ? 'poly:' + k : ''),
    ap: (hu, p, sw, khung) => (hu && hu.startsWith('poly:') ? ve(hu.slice(5), p, sw, khung, ['ccmXA', 'ccmXB', 'ccmXT']) : null),
    cssChuyen: CCM.cssChuyen,
  };

  /* ---------- danh sách chọn: kiểu mới lên đầu, kiểu cũ ẩn (trừ kiểu video này đang dùng) ---------- */
  const anSet = () => new Set((SS().info || {}).chuyen_an || []);
  const dangDung = () => new Set(((SS().plan || {}).canh || []).map(c => c.chuyen).filter(Boolean));
  function themTenAn() {   // kiểu chung bị ẩn vẫn có tên (tenGiaTri tìm trong chuyen_rieng)
    const d = (S.info.kieu_ds || []).find(x => x.muc === 'chuyen_canh'); if (!d || !S.info.chuyen_rieng) return;
    const an = anSet();
    d.ds.forEach(x => { if (an.has(x.v) && !S.info.chuyen_rieng.some(y => y.v === x.v)) S.info.chuyen_rieng.push({v: x.v, ten: x.ten, an: true}); });
  }
  if (typeof dsChuyenCanh === 'function') {
    const goc = dsChuyenCanh;
    dsChuyenCanh = function () {
      const ds = goc.apply(this, arguments);
      if (!S.info || !S.info.chuyen_moi) return ds;
      Object.keys(S.info.chuyen_moi).forEach(k => { if (typeof TV_XC === 'object' && !TV_XC[k]) TV_XC[k] = 'moi'; });
      const an = anSet(), dung = dangDung();
      const moi = ds.filter(x => x.moi), cu = ds.filter(x => !x.moi && x.v !== 'tron_moi' && (!(x.an || an.has(x.v)) || dung.has(x.v)))
        .map(x => (x.an || an.has(x.v)) ? Object.assign({}, x, {cu: true, cham: false}) : x);
      return moi.concat(cu);
    };
  }
  // kiểu chung cả video (chip Thư viện, tab Kiểu, menu Hiệu ứng cả video): ẩn kiểu cũ + "Trộn" cũ, trừ giá trị đang dùng
  function voiDsLoc(fn, ctx, args) {
    const d = S.info && (S.info.kieu_ds || []).find(x => x.muc === 'chuyen_canh');
    if (!d) return fn.apply(ctx, args);
    const goc = d.ds, v = typeof kieuDung === 'function' ? kieuDung('chuyen_canh') : (S.plan.kieu || {}).chuyen_canh, an = anSet();
    an.add('tron_poly');
    d.ds = goc.filter(x => !an.has(x.v) || x.v === v);
    try { return fn.apply(ctx, args); } finally { d.ds = goc; }
  }
  ['tvChips', 'benKieu', 'mucHieuUngVideo'].forEach(ten => {
    if (typeof window[ten] !== 'function') return;
    const goc = window[ten];
    window[ten] = function () { return (ten !== 'tvChips' || arguments[0] === 'chuyen_canh') ? voiDsLoc(goc, this, arguments) : goc.apply(this, arguments); };
  });
  // tên dễ hiểu: Trộn cũ / mới (sau _mod-sua-r29 đặt tên "Trộn chuyển cảnh (nhiều kiểu xen kẽ)" cho tron_poly)
  if (typeof moVideo === 'function') {
    const goc = moVideo;
    moVideo = async function () {
      const r = await goc.apply(this, arguments);
      try { themTenAn(); } catch (e) {}
      setTimeout(() => { try {
        // gộp r40: không ghi "Film Impact" trong tên (anh dặn r29 N8: tên kiểu không còn chữ Film Impact)
        (S.info.kieu_ds || []).forEach(m => (m.ds || []).forEach(x => { if (x.v === 'tron_poly') x.ten = 'Trộn kiểu cũ (nhiều kiểu xen kẽ)'; }));
        (S.info.chuyen_rieng || []).forEach(x => { if (x.v === 'tron_poly') x.ten = 'Trộn kiểu cũ (nhiều kiểu xen kẽ)'; });
      } catch (e) {} }, 0);
      return r;
    };
  }

  /* ---------- Thư viện › Chuyển cảnh: nhóm "Mới" lên đầu + ô xem trước chạy bằng cssChuyen ---------- */
  const NHOM_MOI = ['moi', 'Mới · trend'];
  queueMicrotask(() => {   // XC_NHOM / tvSauVe khai trong _mod-thu-vien-them.js (nối sau file này)
    try { if (typeof XC_NHOM !== 'undefined' && !XC_NHOM.some(x => x[0] === 'moi')) XC_NHOM.unshift(NHOM_MOI); } catch (e) {}
    if (typeof tvSauVe === 'function') {
      const goc = tvSauVe;
      tvSauVe = function (tab, pane) { const r = goc.apply(this, arguments); if (tab === 'chuyen') try { veOMoi(pane); } catch (e) { console.error(e); } return r; };
    }
  });
  const O = {el: null, raf: 0, t0: 0};
  function oCua(b) { const xv = b && b.querySelector('.xv.xc-moi'); return xv ? {b, xv, a: xv.querySelector('.xa'), bb: xv.querySelector('.xb'), f: xv.querySelector('.xf')} : null; }
  function veO(o, p) {
    const id = o.b.dataset.tvchuyen, r = ve(id, p, o.xv.clientWidth || 90, [1080, 1920], ['ccmTA', 'ccmTB', 'ccmTT']); if (!r) return;
    o.a.style.cssText = r.A || ''; o.bb.style.cssText = r.B || ''; o.f.style.cssText = r.F || ''; o.xv.style.backgroundColor = r.nen || '';
  }
  function veOMoi(pane) {   // ô kiểu mới: đứng yên ở giữa chuyển cảnh (p ≈ 0,42), nhãn "Mới"
    $$('.tvx[data-tvchuyen]', pane || document).forEach(b => {
      const o = oCua(b); if (!o) return;
      b.classList.add('tvx-moi');
      const x = (S.info.chuyen_rieng || []).find(y => y.v === b.dataset.tvchuyen);
      if (x && x.cu && !o.xv.querySelector('.tv-tag.cu')) o.xv.insertAdjacentHTML('beforeend', '<span class="tv-tag cu">cũ</span>');
      veO(o, 0.42);
    });
    $$('.tvx[data-tvchuyen]', pane || document).forEach(b => {   // kiểu cũ còn hiện vì video đang dùng
      const id = b.dataset.tvchuyen, xv = b.querySelector('.xv'); if (!id || !xv || xv.classList.contains('xc-moi')) return;
      if (anSet().has(id) && !xv.querySelector('.tv-tag.cu')) xv.insertAdjacentHTML('beforeend', '<span class="tv-tag cu">cũ</span>');
    });
  }
  function chay(o) {   // rê chuột: chạy lặp A -> B (giữ A 0,35s, chuyển theo đúng giây của kiểu x 2,2 cho dễ nhìn, giữ B 0,45s)
    dungChay();
    const s = spec(o.b.dataset.tvchuyen); if (!s) return;
    const g = Math.max(0.5, (s.giay || 0.4) * 2.2), vong = 0.35 + g + 0.45;
    O.el = o; O.t0 = performance.now();
    const buoc = now => {
      if (O.el !== o) return;
      const t = ((now - O.t0) / 1000) % vong, p = Math.min(1, Math.max(0, (t - 0.35) / g));
      veO(o, p); O.raf = requestAnimationFrame(buoc);
    };
    O.raf = requestAnimationFrame(buoc);
  }
  function dungChay() { if (O.raf) cancelAnimationFrame(O.raf); O.raf = 0; const o = O.el; O.el = null; if (o && o.b.isConnected) veO(o, 0.42); }
  const lib = document.getElementById('libPane');
  if (lib) {
    lib.addEventListener('pointerover', e => { const b = e.target.closest && e.target.closest('.tvx[data-tvchuyen]'); const o = oCua(b); if (o && !b.disabled && (!O.el || O.el.b !== b)) chay(o); });
    lib.addEventListener('pointerout', e => { const b = e.target.closest && e.target.closest('.tvx[data-tvchuyen]'); if (b && O.el && O.el.b === b && !b.contains(e.relatedTarget)) dungChay(); });
    lib.addEventListener('focusin', e => { const b = e.target.closest && e.target.closest('.tvx[data-tvchuyen]'); const o = oCua(b); if (o) chay(o); });
    lib.addEventListener('focusout', () => dungChay());
  }
  // để kiểm thử
  window.chuyenMoi = {cssChuyen: CCM.cssChuyen, gt: CCM.gt, veOMoi, dang: () => !!O.el, ds: () => Object.keys(((S.info || {}).chuyen_moi) || {})};
})();
