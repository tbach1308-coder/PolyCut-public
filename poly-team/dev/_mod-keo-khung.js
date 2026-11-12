/* ============================== KÉO CHỮ TRÊN KHUNG XEM (r31, 10/11/2026) ==============================
   Anh (10/11 15:39, ảnh khung xem Sửa tay: logo POLY STORE nằm ngay dưới nút LIVE): "kéo thả các tag trong khung hình được". Như CapCut:
   - BẤM 1 chữ đang hiện ở giờ vạch đỏ trên khung xem (hook, nhãn, thẻ giá, tiêu đề ghim, sticker, chữ POLY STORE, thẻ kết, phụ đề)
     -> khung chọn vàng + chọn đúng thanh trên timeline + bảng 1 chữ bên phải. 2 chiều: chọn thanh / dòng ở bảng thì khung xem cũng
     hiện khung chọn (chữ đó đang hiện). Rê chuột: viền mảnh + con trỏ "move". Lớp giao diện TikTok / khung vàng không nuốt chuột
     (bắt sự kiện ở #stage). Bấm chỗ trống trên khung: bỏ chọn chữ. Bấm đúp chữ: tới ô gõ chữ đó ở bảng phải.
   - KÉO để dời: chữ dời ngay trên màn (CSS transform lớp PNG đang có, không chờ máy chủ), tự hít (8px màn hình) vào giữa ngang / giữa
     dọc khung và mép vùng an toàn (x 120 / 960, cột nút x 900, y 240 / 1260): đường hít vàng mảnh. Giữ Alt = tắt hít tạm; nút nam châm
     (phím N) của timeline tắt hít cả ở đây. Ra ngoài vùng an toàn (luật check_safe của bộ dựng + thanh trên y < 228): khung đỏ +
     1 dòng báo. Esc lúc kéo = huỷ. Thả: 1 bước Ctrl+Z (doi), máy chủ vẽ lại -> đúng hệt bản xuất. Phụ đề: chỉ lên / xuống, 1 vị trí
     cho cả video. Thẻ kết: chỉ lên / xuống. Hộp chữ luôn nằm trong khung 1080×1920 (như bộ dựng kẹp).
   - KÉO GÓC khung chọn = to / nhỏ: nhãn (co = cỡ chữ px, 40–220), sticker (co = bề ngang px). Thẻ giá: chưa (để sau).
   - Mũi tên ← ↑ → ↓ dời 1px (Shift 10px) khi vừa bấm chữ trên khung (không gõ trong ô); bấm ra ngoài khung xem: phím như cũ.
   - Bảng 1 chữ: dòng "Vị trí" (Chỗ mặc định / Đã dời + Về chỗ cũ). Chữ POLY STORE / sticker: bảng nhỏ riêng. Bấm "Trên / Giữa trên /
     Giữa" của hook đang bị dời: về vị trí đó (bỏ chỗ kéo) trong 1 bước.
   Kế hoạch (chỉ THÊM khoá, engine/ve_chu.py): chu.vi_tri = {hook, brand, tieu_de, ket: [x, y] tâm hộp chữ, phu_de: y chân chữ},
   chu.nhan_chu[i].vi_tri, chu.the_gia.vi_tri = [x, y] tâm hộp; sticker: x, y, co có sẵn. Toạ độ khung 1080×1920.
   Máy chủ (sua_tay_may.lenh_xem) gửi kèm từng lớp: k (chữ nào), hop (hộp chữ), và pd_y_goc (chân chữ phụ đề mặc định).
   Chỉ thêm file này + _mod-keo-khung.css: bọc veKhung / veTimeline / veBen / benChu, bắt sự kiện ở #stage. Kiểm: thu_keo_khung.py */
IC_P.kkVe = '<path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/>';
IC_P.kkLogo = '<rect x="3" y="8" width="18" height="8" rx="2"/><path d="M7 12h10"/>';
(function () {
  const st = document.getElementById('stage');
  if (!st || typeof veKhung !== 'function') return;
  const W = 1080, H = 1920, HUT = 8;   // khung bộ dựng · tầm hít (px màn hình, như timeline r25)
  const O = document.createElement('div'); O.id = 'kkO'; O.className = 'kk-o'; O.setAttribute('aria-hidden', 'true');
  O.innerHTML = '<div class="kk-re" hidden></div><div class="kk-doc" hidden></div><div class="kk-ngang" hidden></div>'
    + '<div class="kk-chon" hidden><i class="kk-g" data-g="tl"></i><i class="kk-g" data-g="tr"></i><i class="kk-g" data-g="bl"></i><i class="kk-g" data-g="br"></i></div>'
    + '<div class="kk-nhan" hidden></div><div class="kk-bao" hidden></div>';
  st.append(O);
  const q = s => O.querySelector(s);
  const K = {khung: false, keo: null, chan: false};   // khung: vừa bấm chữ trên khung (phím mũi tên dời chữ) · keo: đang kéo
  const r1 = x => Math.round(x * 10) / 10;
  const go = () => { const ae = document.activeElement || {}; return /TEXTAREA|SELECT/.test(ae.tagName || '') || (ae.tagName === 'INPUT' && !/^(checkbox|radio|button|range)$/.test(ae.type)) || !!ae.isContentEditable; };
  const pc = (e, h) => { e.style.left = h[0] / W * 100 + '%'; e.style.top = h[1] / H * 100 + '%'; e.style.width = Math.max(0, h[2] - h[0]) / W * 100 + '%'; e.style.height = Math.max(0, h[3] - h[1]) / H * 100 + '%'; };

  /* ---------- lớp chữ của bản xem trước: {l, i, lo} ---------- */
  const LOAI_CO_DINH = ['hook', 'ket', 'tieu_de', 'brand'];
  function loaiCua(l) { const k = String(l.k || ''); if (LOAI_CO_DINH.includes(k)) return k; if (k.startsWith('st:')) return 'st'; return l.loai === 'phu_de' ? 'pd' : l.loai === 'gia' ? 'gia' : 'nhan'; }
  const chiY = lo => lo === 'pd' || lo === 'ket';
  const tat = () => !S.plan || !S.view || S.mode === 'nhap' || $('#edit').hidden || !!S.view.trong || !!document.getElementById('mauK');
  function hien() {   // lớp chữ đang hiện ở giờ vạch đỏ (như veKhung: t0 ≤ t < t1)
    if (tat()) return [];
    const t = S.t, out = [];
    (S.view.lop || []).forEach((l, i) => { if (l.k && Array.isArray(l.hop) && l.hop.length === 4 && t >= +l.t0 && t < +l.t1) out.push({l, i, lo: loaiCua(l)}); });
    return out;
  }
  function diem(ev) { const r = st.getBoundingClientRect(); return [(ev.clientX - r.left) / r.width * W, (ev.clientY - r.top) / r.height * H]; }
  function trung(x, y) {   // chữ dưới chuột: hộp chứa điểm (lề 5px màn hình: chữ POLY STORE ở 1366 chỉ cao ~8px), nhiều hộp thì hộp nhỏ nhất
    let b = null; const le = Math.max(4, 5 * W / (st.clientWidth || W));
    for (const o of hien()) { const [a0, b0, a1, b1] = o.l.hop;
      if (x >= a0 - le && x <= a1 + le && y >= b0 - le && y <= b1 + le) { const s = (a1 - a0) * (b1 - b0); if (!b || s < b.s) b = {o, s}; } }
    return b ? b.o : null;
  }
  function nhomLop(k, lo) { const out = []; ((S.view || {}).lop || []).forEach((l, i) => { if (lo === 'pd' ? l.loai === 'phu_de' : l.k === k) out.push(i); }); return out; }
  const anh = idx => idx.map(i => lopImgs[i]).filter(Boolean);
  const coNhom = () => { try { return !!(S.quet && S.quet.canh && S.quet.k && S.quet.canh.size + S.quet.k.size >= 2); } catch (e) { return false; } };
  function chonK() { return !tat() && S.selLoai === 'chu' && S.sel.k && !coNhom() ? S.sel.k : null; }
  function oChon() { const k = chonK(); return k ? hien().find(o => o.l.k === k) || null : null; }

  /* ---------- kế hoạch: đọc / ghi chỗ ---------- */
  const KHOA = {hook: 'hook', ket: 'ket', tieu_de: 'tieu_de', brand: 'brand', pd: 'phu_de'};
  const vtChu = p => { const c = (p || {}).chu || {}; return c.vi_tri && typeof c.vi_tri === 'object' && !Array.isArray(c.vi_tri) ? c.vi_tri : null; };
  function itCua(p, k, lo) {
    const chu = (p || {}).chu || {};
    if (lo === 'nhan') return (chu.nhan_chu || []).find(x => x && x._k === k) || null;
    if (lo === 'gia') return chu.the_gia && chu.the_gia._k === k ? chu.the_gia : null;
    if (lo === 'st') return (chu.sticker || [])[+String(k).slice(3)] || null;
    return null;
  }
  function daDoi(k, lo) {
    if (lo === 'st') return false;
    if (lo === 'nhan' || lo === 'gia') { const it = itCua(S.plan, k, lo); return !!(it && it.vi_tri); }
    const v = vtChu(S.plan); return !!(v && v[KHOA[lo]] != null);
  }
  function pdY() { const v = vtChu(S.plan), y = v ? +v.phu_de : NaN; return v && v.phu_de != null && isFinite(y) ? clamp(y, 160, 1880) : (+(S.view || {}).pd_y_goc || 1272); }
  function ghiViTri(p, k, lo, dx, dy, tam) {   // tam = tâm hộp chữ mới (khung 1080×1920)
    p.chu = p.chu || {};
    if (lo === 'st') { const s = itCua(p, k, lo); if (!s) return; s.x = Math.round((s.x != null ? +s.x : 800) + dx); s.y = Math.round((s.y != null ? +s.y : 1000) + dy); return; }
    if (lo === 'nhan' || lo === 'gia') { const it = itCua(p, k, lo); if (it) it.vi_tri = [r1(tam[0]), r1(tam[1])]; return; }
    const vt = vtChu(p) || (p.chu.vi_tri = {});
    if (lo === 'pd') vt.phu_de = Math.round(clamp(pdY() + dy, 160, 1880));
    else vt[KHOA[lo]] = [r1(tam[0]), r1(tam[1])];
  }
  function boViTri(p, k, lo) {
    if (lo === 'nhan' || lo === 'gia') { const it = itCua(p, k, lo); if (it) delete it.vi_tri; return; }
    const vt = vtChu(p); if (!vt) return;
    delete vt[KHOA[lo]]; if (!Object.keys(vt).length) delete p.chu.vi_tri;
  }
  function coGian(o) {   // kéo góc để to / nhỏ: nhãn (cỡ chữ, trừ nhãn gọn kiểu tối giản không có mẫu), sticker
    if (o.lo === 'st') return true;
    if (o.lo !== 'nhan') return false;
    const it = itCua(S.plan, o.l.k, 'nhan') || {}, kv = it.kieu && typeof it.kieu === 'object' ? it.kieu : null;
    return (S.plan.kieu || {}).chu !== 'toi_gian' || !!(kv && Object.keys(kv).some(x => x !== 'font'));
  }
  const CO = {nhan: [92, 40, 220], st: [320, 60, 1080]};   // cỡ mặc định, nhỏ nhất, to nhất
  function coCu(o) { const it = itCua(S.plan, o.l.k, o.lo) || {}, c = CO[o.lo]; return +it.co > 0 ? +it.co : c[0]; }
  function ghiCo(p, k, lo, co, tam) {
    const it = itCua(p, k, lo); if (!it) return;
    it.co = co;
    if (lo === 'nhan') it.vi_tri = [r1(tam[0]), r1(tam[1])];   // giữ tâm chữ đứng yên khi to / nhỏ
  }

  /* ---------- tên + vùng an toàn ---------- */
  const TEN = {hook: 'Hook', ket: 'Thẻ kết', tieu_de: 'Tiêu đề ghim', brand: 'Chữ POLY STORE', pd: 'Phụ đề', nhan: 'Nhãn', gia: 'Thẻ giá', st: 'Sticker'};
  function tenChu(k, lo) {
    if (['nhan', 'gia', 'pd'].includes(lo) && typeof r25TenNgan === 'function') { try { return r25TenNgan(k, lo); } catch (e) {} }
    if (lo === 'st') { const s = itCua(S.plan, k, 'st'); return 'Sticker' + (s && s.ten ? ' “' + s.ten + '”' : ''); }
    return TEN[lo] || 'Chữ';
  }
  // ngoài vùng an toàn: như check_safe của ve_chu (cột nút phải x > 950 trong y 620–1320, thấp hơn y 1300 / phụ đề 1380, sát mép trái
  // x < 60) + thanh trên của TikTok (LIVE / Dành cho bạn, khung vàng y 240; lề 12 cho tiêu đề ghim / hook kiểu tối giản mặc định)
  const LY = {tren: 'thanh LIVE / Dành cho bạn', phai: 'cột tim, bình luận', duoi: 'tên kênh, mô tả', trai: 'sát mép trái'};
  function ngoai(h, lo) {
    const [x0, y0, x1, y1] = h, out = [];
    if (y0 < 228) out.push('tren');
    if (x1 > 950 && y1 > 620 && y0 < 1320) out.push('phai');
    if (y1 > (lo === 'pd' ? 1380 : 1300)) out.push('duoi');
    if (x0 < 60) out.push('trai');
    return out;
  }
  const BAO = 'Ra ngoài vùng an toàn (bị nút TikTok che)';
  const baoNgoai = ng => BAO + ': ' + ng.map(x => LY[x]).join(', ');

  /* ---------- vẽ: khung chọn, viền rê chuột, đường hít, dòng báo ---------- */
  function veChon(o, h, P) {
    const c = q('.kk-chon'), b = q('.kk-bao');
    if (!o) { c.hidden = true; b.hidden = true; return; }
    pc(c, h); c.hidden = false;
    const ng = ngoai(h, o.lo);
    c.classList.toggle('do', ng.length > 0); c.classList.toggle('co-co', coGian(o)); c.classList.toggle('dang', !!P);
    c.dataset.k = o.l.k; c.dataset.lo = o.lo;
    if (ng.length) {
      b.innerHTML = icon('canhBao') + '<span>' + BAO + '</span>'; b.dataset.tip = baoNgoai(ng); b.hidden = false;
      const duoi = h[3] < H - 260;   // dòng báo dưới khung chọn; chữ sát đáy thì để trên
      b.style.top = duoi ? 'calc(' + h[3] / H * 100 + '% + 6px)' : ''; b.style.bottom = duoi ? '' : 'calc(' + (100 - h[1] / H * 100) + '% + 6px)';
    } else b.hidden = true;
  }
  function veKK() {
    if (K.keo && K.keo.dang) return;
    const o = oChon();
    veChon(o, o ? o.l.hop : null, null);
    if (!o) K.khung = false;
    if (tat()) { q('.kk-re').hidden = true; st.classList.remove('kk-tay'); }
  }
  window.veKK = veKK;
  let hen = 0;
  const veSau = () => { if (!hen) hen = requestAnimationFrame(() => { hen = 0; try { veKK(); } catch (e) { console.error(e); } }); };
  function veRe(o) {
    const r = q('.kk-re');
    st.classList.toggle('kk-tay', !!o);
    if (!o || (oChon() && oChon().i === o.i)) { r.hidden = true; return; }
    pc(r, o.l.hop); r.hidden = false;
  }

  /* ---------- chọn chữ (đồng bộ timeline + bảng phải) ---------- */
  function chon(o) {
    const k = o.l.k;
    try { if (coNhom() && window.QUET) QUET.bo(); } catch (e) {}
    if (S.selLoai === 'chu' && S.sel.k === k) { veSau(); return; }
    if (o.lo === 'brand' || o.lo === 'st') {
      if (typeof r25MoMot === 'function') r25MoMot();
      S.selLoai = 'chu'; S.sel.k = k; if (S.tab !== 'chu') { S.tab = 'chu'; veTabs(); }
      veBen(true); veTimeline(); return;
    }
    chonChuMenu(k);   // như chuột phải thanh chữ: tab Chữ / Phụ đề, bảng 1 chữ, thanh timeline sáng
  }
  function boChon() {
    if (S.selLoai !== 'chu' || !S.sel.k) return;
    S.sel.k = null; veTimeline(); veBen(true);
  }

  /* ---------- kéo / kéo góc ---------- */
  function hopMoi(P) {
    const h = P.hop0;
    if (P.mode === 'co') { const cx = (h[0] + h[2]) / 2, cy = (h[1] + h[3]) / 2, w = (h[2] - h[0]) * P.s / 2, hh = (h[3] - h[1]) * P.s / 2; return [cx - w, cy - hh, cx + w, cy + hh]; }
    return [h[0] + P.dx, h[1] + P.dy, h[2] + P.dx, h[3] + P.dy];
  }
  function tinh(P) {
    const r = st.getBoundingClientRect(), kx = W / r.width, ky = H / r.height, h = P.hop0;
    P.gx = P.gy = null; P.hit = [];
    if (P.mode === 'co') {
      const cx = r.left + (h[0] + h[2]) / 2 / kx, cy = r.top + (h[1] + h[3]) / 2 / ky;
      const d0 = Math.hypot(P.x0 - cx, P.y0 - cy) || 1, d1 = Math.hypot(P.cx - cx, P.cy - cy);
      const c = CO[P.lo], co0 = P.co0;
      let co = Math.round(co0 * d1 / d0);
      co = clamp(co, c[1], c[2]); P.co = co; P.s = co / co0;
      return;
    }
    let dx = (P.cx - P.x0) * kx, dy = (P.cy - P.y0) * ky;
    if (chiY(P.lo)) dx = 0;
    const hit = (window.TL25 && typeof TL25.hit === 'function' ? TL25.hit() : true) && !P.alt, d = HUT * kx;
    if (hit) {
      const tim = ds => { let b = null; for (const [v, dich, ten] of ds) { const x = Math.abs(dich - v); if (x <= d && (!b || x < b.x)) b = {x, dd: dich - v, dich, ten}; } return b; };
      if (!chiY(P.lo)) {
        const ds = [[(h[0] + h[2]) / 2 + dx, 540, 'giữa ngang'], [h[0] + dx, 120, 'mép trái vùng an toàn'], [h[2] + dx, 960, 'mép phải vùng an toàn']];
        if (h[3] + dy > 840) ds.push([h[2] + dx, 900, 'mép cột nút']);
        const b = tim(ds); if (b) { dx += b.dd; P.gx = b.dich; P.hit.push(b.ten); }
      }
      const b = tim([[(h[1] + h[3]) / 2 + dy, 960, 'giữa dọc'], [h[1] + dy, 240, 'mép trên vùng an toàn'], [h[3] + dy, 1260, 'mép dưới vùng an toàn']]);
      if (b) { dy += b.dd; P.gy = b.dich; P.hit.push(b.ten); }
    }
    let x = Math.round(dx), y = Math.round(dy);
    // hộp chữ trong khung (bộ dựng kẹp y như vậy: ve_chu.lech_tam); phụ đề: chân chữ trong y 160–1880 (ve_chu.pd_lech)
    const kx0 = Math.ceil(-h[0]), kx1 = Math.floor(W - h[2]), ky0 = Math.ceil(-h[1]), ky1 = Math.floor(H - h[3]);
    if (kx0 <= kx1) x = clamp(x, kx0, kx1);
    if (ky0 <= ky1) y = clamp(y, ky0, ky1);
    if (P.lo === 'pd') { const cur = pdY(); y = clamp(y, Math.ceil(160 - cur), Math.floor(1880 - cur)); }
    if (P.gx != null && Math.abs(x - Math.round(dx)) > 0) { P.gx = null; P.hit = P.hit.filter(t => !/ngang|trái|phải|cột/.test(t)); }
    if (P.gy != null && Math.abs(y - Math.round(dy)) > 0) { P.gy = null; P.hit = P.hit.filter(t => !/dọc|trên|dưới/.test(t)); }
    P.dx = x; P.dy = y;
  }
  function datAnh(ims, dx, dy, s, h0) {   // dời / phóng lớp PNG đang có (không chờ máy chủ)
    const r = st.getBoundingClientRect(), sx = r.width / W, sy = r.height / H;
    ims.forEach(im => {
      const o = im._kk || [0, 0];
      const tx = (o[0] + dx) * sx, ty = (o[1] + dy) * sy;
      if (s && Math.abs(s - 1) > 1e-3) { im.style.transformOrigin = ((h0[0] + h0[2]) / 2 / W * 100) + '% ' + ((h0[1] + h0[3]) / 2 / H * 100) + '%'; im.style.transform = `translate(${tx}px,${ty}px) scale(${s})`; }
      else { im.style.transform = tx || ty ? `translate(${tx}px,${ty}px)` : ''; }
    });
  }
  function ap(P) {
    const h = hopMoi(P);
    datAnh(anh(P.idx), P.mode === 'doi' ? P.dx : 0, P.mode === 'doi' ? P.dy : 0, P.mode === 'co' ? P.s : 1, P.hop0);
    veChon(P.o, h, P);
    const gd = q('.kk-doc'), gn = q('.kk-ngang');
    gd.hidden = P.gx == null; if (P.gx != null) gd.style.left = P.gx / W * 100 + '%';
    gn.hidden = P.gy == null; if (P.gy != null) gn.style.top = P.gy / H * 100 + '%';
    const n = q('.kk-nhan');
    const vt = P.mode === 'co' ? 'cỡ ' + P.co + (P.lo === 'nhan' ? 'px chữ' : 'px ngang')
      : P.lo === 'pd' ? 'chân chữ y ' + Math.round(pdY() + P.dy) : 'x ' + Math.round((h[0] + h[2]) / 2) + ' · y ' + Math.round((h[1] + h[3]) / 2);
    n.innerHTML = `<span>${esc(P.ten)}</span> · ${vt}${P.hit && P.hit.length ? ` <b>hít ${esc(P.hit.join(', '))}</b>` : P.alt ? ' <i>tắt hít (Alt)</i>' : ''}`;
    n.hidden = false;
    const tren = h[1] > 150;   // khung báo trên khung chọn; chữ sát đỉnh thì để dưới
    n.style.top = tren ? '' : 'calc(' + h[3] / H * 100 + '% + 6px)'; n.style.bottom = tren ? 'calc(' + (100 - h[1] / H * 100) + '% + 6px)' : '';
    q('.kk-re').hidden = true;
  }
  function batDau(P) {
    P.dang = true; document.body.classList.add('kk-dang-keo'); if (P.mode === 'co') document.body.classList.add('kk-keo-goc');
    $$('.tip').forEach(t => t.classList.remove('on'));
    try { st.setPointerCapture(P.pid); } catch (e) {}
  }
  function diChuot(ev) {
    const P = K.keo; if (!P) return;
    P.cx = ev.clientX; P.cy = ev.clientY; P.alt = ev.altKey;
    if (!P.dang) { if (Math.abs(ev.clientX - P.x0) < 3 && Math.abs(ev.clientY - P.y0) < 3) return; batDau(P); }
    ev.preventDefault(); tinh(P); ap(P);
  }
  function thaChuot(ev) { xong(ev.type !== 'pointerup'); }
  function phimKeo(e) {
    const P = K.keo; if (!P) return;
    if (e.key === 'Escape' && e.type === 'keydown') { e.preventDefault(); e.stopImmediatePropagation(); xong(true); return; }
    if (e.key === 'Alt') { e.preventDefault(); P.alt = e.type === 'keydown'; if (P.dang) { tinh(P); ap(P); } }
  }
  function don() {
    removeEventListener('pointermove', diChuot, true); removeEventListener('pointerup', thaChuot, true); removeEventListener('pointercancel', thaChuot, true);
    removeEventListener('keydown', phimKeo, true); removeEventListener('keyup', phimKeo, true);
    document.body.classList.remove('kk-dang-keo', 'kk-keo-goc');
    ['.kk-doc', '.kk-ngang', '.kk-nhan'].forEach(s => { q(s).hidden = true; });
  }
  function dichHop(idx, dx, dy, s) {   // hộp chữ của bản xem đang có đi theo ngay (máy chủ trả bản mới sẽ ghi đè)
    const v = S.view || {};
    idx.forEach(i => { const l = (v.lop || [])[i]; if (!l || !l.hop) return; const h = l.hop;
      if (s) { const cx = (h[0] + h[2]) / 2, cy = (h[1] + h[3]) / 2, w = (h[2] - h[0]) * s / 2, hh = (h[3] - h[1]) * s / 2; l.hop = [cx - w, cy - hh, cx + w, cy + hh].map(Math.round); }
      else l.hop = [h[0] + dx, h[1] + dy, h[2] + dx, h[3] + dy]; });
  }
  function xong(huy) {
    const P = K.keo; K.keo = null; don();
    if (!P) return;
    if (!P.dang) { veKK(); return; }
    K.chan = true; setTimeout(() => { K.chan = false; }, 0);
    const doiGi = P.mode === 'co' ? P.co !== P.co0 : (P.dx || P.dy);
    if (huy || !doiGi) { datAnh(anh(P.idx), 0, 0, 1, P.hop0); veKK(); return; }
    const h0 = P.hop0, c0 = [(h0[0] + h0[2]) / 2, (h0[1] + h0[3]) / 2], h = hopMoi(P);
    if (P.mode === 'co') {
      doi(p => ghiCo(p, P.k, P.lo, P.co, c0));
      anh(P.idx).forEach(im => { im._kk = im._kk || [0, 0]; });
      dichHop(P.idx, 0, 0, P.s);
      toast((P.co > P.co0 ? 'Phóng to ' : 'Thu nhỏ ') + P.ten + ' (cỡ ' + P.co0 + ' → ' + P.co + ') · Ctrl+Z để lấy lại');
    } else {
      doi(p => ghiViTri(p, P.k, P.lo, P.dx, P.dy, [c0[0] + P.dx, c0[1] + P.dy]));
      anh(P.idx).forEach(im => { const o = im._kk || [0, 0]; im._kk = [o[0] + P.dx, o[1] + P.dy]; });
      dichHop(P.idx, P.dx, P.dy);
      const ng = ngoai(h, P.lo);
      toast('Dời ' + (P.lo === 'pd' ? 'phụ đề (cả video)' : P.ten) + (P.hit && P.hit.length ? ', hít ' + P.hit.join(', ') : '') + (ng.length ? ' · ' + baoNgoai(ng) : '') + ' · Ctrl+Z để lấy lại', !!ng.length);
    }
    K.khung = true; veKK();
  }

  /* ---------- chuột trên khung xem ---------- */
  const BO_QUA = 'button, a, input, select, textarea, label, video.nhap, .mauk, .cr-goi, .cho.on';
  st.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.ctrlKey || e.metaKey || tat() || $('.mbg') || K.keo) return;
    if (e.target.closest(BO_QUA) && !e.target.closest('.kk-o')) return;
    const g = e.target.closest('.kk-g'), [x, y] = diem(e);
    let o = null, mode = 'doi';
    if (g) { o = oChon(); if (!o || !coGian(o)) return; mode = 'co'; }
    else o = trung(x, y);
    if (!o) { K.khung = false; boChon(); veKK(); return; }
    e.preventDefault();
    if (go() && document.activeElement && document.activeElement.blur) document.activeElement.blur();   // đang gõ ô bảng phải: rời ô (mũi tên dời chữ)
    dung(); chon(o); K.khung = true;
    const ten = o.lo === 'pd' ? 'Phụ đề (cả video)' : tenChu(o.l.k, o.lo);
    K.keo = {o, k: o.l.k, lo: o.lo, mode, pid: e.pointerId, x0: e.clientX, y0: e.clientY, cx: e.clientX, cy: e.clientY, hop0: o.l.hop.slice(),
      idx: nhomLop(o.l.k, o.lo), dx: 0, dy: 0, s: 1, co0: mode === 'co' ? coCu(o) : 0, co: 0, alt: e.altKey, dang: false, ten, hit: []};
    if (mode === 'co') K.keo.co = K.keo.co0;
    addEventListener('pointermove', diChuot, true); addEventListener('pointerup', thaChuot, true); addEventListener('pointercancel', thaChuot, true);
    addEventListener('keydown', phimKeo, true); addEventListener('keyup', phimKeo, true);
    veKK();
  });
  st.addEventListener('pointermove', e => { if (K.keo || e.buttons || tat()) return; const [x, y] = diem(e); veRe(trung(x, y)); });
  st.addEventListener('pointerleave', () => { if (!K.keo) veRe(null); });
  st.addEventListener('click', e => { if (K.chan) { e.stopPropagation(); e.preventDefault(); } }, true);
  st.addEventListener('dblclick', e => {   // bấm đúp chữ: tới ô gõ chữ đó (bảng phải)
    if (tat()) return; const [x, y] = diem(e), o = trung(x, y); if (!o) return;
    const ip = $('#pane .r25-g .inp, #pane .kk-ben input'); if (ip) { ip.focus(); if (ip.select) ip.select(); }
  });
  addEventListener('pointerdown', e => { if (!st.contains(e.target)) K.khung = false; }, true);

  /* ---------- phím mũi tên: dời 1px (Shift 10px) chữ vừa bấm trên khung ---------- */
  document.addEventListener('keydown', e => {
    if (!K.khung || K.keo || e.ctrlKey || e.metaKey || e.altKey || !/^Arrow(Left|Right|Up|Down)$/.test(e.key)) return;
    if ($('#edit').hidden || $('.mbg') || go()) return;
    const o = oChon(); if (!o) { K.khung = false; return; }
    e.preventDefault(); e.stopImmediatePropagation();
    const b = e.shiftKey ? 10 : 1, h = o.l.hop;
    let dx = e.key === 'ArrowLeft' ? -b : e.key === 'ArrowRight' ? b : 0, dy = e.key === 'ArrowUp' ? -b : e.key === 'ArrowDown' ? b : 0;
    if (chiY(o.lo)) dx = 0;
    dx = clamp(dx, Math.ceil(-h[0]), Math.max(Math.ceil(-h[0]), Math.floor(W - h[2]))); dy = clamp(dy, Math.ceil(-h[1]), Math.max(Math.ceil(-h[1]), Math.floor(H - h[3])));
    if (o.lo === 'pd') { const cur = pdY(); dy = clamp(dy, Math.ceil(160 - cur), Math.floor(1880 - cur)); }
    if (!dx && !dy) return;
    const c0 = [(h[0] + h[2]) / 2, (h[1] + h[3]) / 2], idx = nhomLop(o.l.k, o.lo);
    doi(p => ghiViTri(p, o.l.k, o.lo, dx, dy, [c0[0] + dx, c0[1] + dy]), 'kk-mui:' + o.l.k);   // bấm liền tay = 1 bước Ctrl+Z
    anh(idx).forEach(im => { const x = im._kk || [0, 0]; im._kk = [x[0] + dx, x[1] + dy]; });
    datAnh(anh(idx), 0, 0, 1, h);
    dichHop(idx, dx, dy); veKK();
  }, true);

  /* ---------- bảng phải: dòng Vị trí (bảng 1 chữ), bảng nhỏ cho chữ POLY STORE / sticker ---------- */
  function hangViTri(k, lo) {
    const da = daDoi(k, lo), cua = lo === 'pd' ? 'phụ đề (cả video)' : lo === 'ket' ? 'thẻ kết' : 'chữ này';
    const tip = (chiY(lo) ? 'Kéo ' + cua + ' lên / xuống trên khung xem' : 'Kéo ' + cua + ' trên khung xem để dời') + ' (tự hít giữa khung, mép vùng an toàn; giữ Alt: tắt hít). Bấm chữ trên khung rồi bấm phím mũi tên: dời 1px, giữ Shift: 10px'
      + (lo === 'nhan' || lo === 'st' ? '. Kéo góc khung chọn: to / nhỏ' : '');
    return `<div class="kk-vt" data-kk-vt="${esc(k)}"><span class="lbl">Vị trí</span><span class="kk-vt-tx${da ? ' da' : ''}">${da ? 'Đã dời trên khung xem' : lo === 'st' ? 'Theo chỗ đặt sticker' : 'Chỗ mặc định'}</span>`
      + `<button type="button" class="kk-i" data-tip="${esc(tip)}" aria-label="Cách dời chữ">${icon('thongTin')}</button><span class="sp"></span>`
      + (da ? `<button type="button" class="btn small ghost" data-kk="ve-cu" data-k="${esc(k)}" data-lo="${lo}" data-tip="Bỏ chỗ đã kéo, ${esc(cua)} về chỗ mặc định (Ctrl+Z để lấy lại)">${icon('kkVe')}<span>Về chỗ cũ</span></button>` : '') + '</div>';
  }
  function loaiChon(k) {
    if (!k || !S.plan) return null;
    if (LOAI_CO_DINH.includes(k)) return k;
    if (String(k).startsWith('st:')) return 'st';
    const l = typeof r25Loai === 'function' ? r25Loai(k) : null;
    return l === 'pd' || l === 'nhan' || l === 'gia' ? l : null;
  }
  function benRieng(lo) {   // chữ POLY STORE / sticker: không có thanh timeline, không có bảng 1 chữ -> bảng nhỏ
    const k = S.sel.k, chu = S.plan.chu || {};
    let h = `<button type="button" class="r25-ve" data-kk="tat-ca" data-tip="Về danh sách mọi chữ của video">${icon('trai')}<span>Tất cả chữ</span></button>`;
    h += `<div class="tt-dau r25-dau kk-dau"><span class="r25-o" aria-hidden="true">${icon(lo === 'brand' ? 'kkLogo' : 'nhan')}</span><div class="tt-ten"><b>${esc(tenChu(k, lo))}</b><small>${lo === 'brand' ? 'suốt video · góc trên' : 'sticker Poly'}</small></div></div>`;
    h += `<div class="box tt-box r25-g kk-ben"><div class="row"><h2 class="sec grow">${lo === 'brand' ? 'Chữ POLY STORE' : 'Sticker'}</h2></div>`
      + (lo === 'brand' ? `<label class="chk"><input type="checkbox" data-f="brand" ${chu.brand !== false ? 'checked' : ''}> Hiện chữ POLY STORE</label>` : '')
      + hangViTri(k, lo) + '</div>';
    return h;
  }
  queueMicrotask(() => {   // bọc SAU mọi mô-đun khác (r25 bảng 1 chữ, quét chọn, timeline r25…)
    const vk = veKhung; veKhung = function () { const r = vk.apply(this, arguments); try { veKK(); } catch (e) { console.error(e); } return r; };
    const vt = veTimeline; veTimeline = function () { const r = vt.apply(this, arguments); veSau(); return r; };
    const bc = benChu; benChu = function () {
      const lo = S.selLoai === 'chu' && !coNhom() ? loaiChon(S.sel.k) : null;
      if ((lo === 'brand' || lo === 'st') && (lo !== 'st' || itCua(S.plan, S.sel.k, 'st'))) return benRieng(lo);
      return bc.apply(this, arguments);
    };
    const vb = veBen; veBen = function () {
      const r = vb.apply(this, arguments);
      try {
        const p = $('#pane'), dau = p && p.querySelector(':scope > .r25-dau:not(.kk-dau)'), lo = dau ? loaiChon(S.sel.k) : null;
        if (dau && lo && !p.querySelector('.kk-vt')) dau.insertAdjacentHTML('afterend', hangViTri(S.sel.k, lo));
      } catch (e) { console.error(e); }
      veSau();
      return r;
    };
    if (S.plan) veKK();
  });
  $('#pane').addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('[data-kk]');
    if (b) {
      e.preventDefault();
      if (b.dataset.kk === 'tat-ca') { S.sel.k = null; return veBen(true); }
      if (b.dataset.kk === 've-cu') {
        const k = b.dataset.k, lo = b.dataset.lo, ten = tenChu(k, lo);
        doi(p => boViTri(p, k, lo));
        nhomLop(k, lo).forEach(i => { const im = lopImgs[i]; if (im) { im._kk = null; im.style.transform = ''; } });
        return toast(ten + ' về chỗ mặc định · Ctrl+Z để lấy lại');
      }
    }
    // hook đang bị kéo chỗ khác mà anh bấm Trên / Giữa trên / Giữa: về đúng vị trí đó (bỏ chỗ kéo), 1 bước Ctrl+Z
    const r = e.target.closest && e.target.closest('.radio[data-r="vi_tri_chu"] button[data-v]');
    if (r && daDoi('hook', 'hook')) {
      e.stopPropagation(); e.preventDefault();
      const v = r.dataset.v;
      doi(p => { p.kieu = p.kieu || {}; p.kieu.vi_tri_chu = v; boViTri(p, 'hook', 'hook'); });
      return;
    }
  }, true);

  // bảng phím tắt (dev/_mod-r25-bang.js đọc window.PHIM_TAT)
  (window.PHIM_TAT = window.PHIM_TAT || []).push(
    {id: 'kk-mui', nhom: 'Chữ', phim: ['←', '↑', '→', '↓'], ten: 'Chữ vừa bấm trên khung xem: dời 1px', ghi: 'giữ Shift: 10px · bấm ra ngoài khung xem: phím về như cũ'},
    {id: 'kk-alt', nhom: 'Chữ', phim: ['Alt'], ten: 'Giữ khi kéo chữ trên khung xem: tắt hít'},
    {id: 'kk-esc', nhom: 'Chữ', phim: ['Esc'], ten: 'Đang kéo chữ trên khung xem: huỷ kéo'});
  window.KK = {hien, trung, chon: () => oChon(), keo: () => K.keo, khung: () => K.khung, ngoai, pdY, ve: veKK};
})();
