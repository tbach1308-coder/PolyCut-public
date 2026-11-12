/* ============================== TÁCH ÂM THANH (4/11, anh: "chưa có chức năng tách âm thanh clip ở dưới time line") ==============================
   Như CapCut "Tách âm thanh / Extract audio": chuột phải cảnh › Sửa cảnh › Tách âm thanh (phím A, nút ở thanh dưới khung xem) -> tiếng
   của cảnh thành 1 khối riêng trên làn "Tiếng tách" cuối timeline, nằm đúng chỗ cảnh, có sóng âm; cảnh gốc im (dấu loa vàng trên khối cảnh).
   Chọn nhiều cảnh (khi timeline chọn được nhiều: khối .sel / S.sel.nhieu…) thì tách từng cảnh, 1 bước Ctrl+Z.
   Kế hoạch: plan.am_tach = [{id, goc, nguon, tu, den, t, am_luong 0–2, vao, ra}] (tu / den: giây trong clip gốc; t: giây trên video bản
             máy chủ; vao / ra: giây mờ dần) + canh.tach_am = goc (cảnh đã tách; chia cảnh thì 2 nửa cùng goc). Không có khoá: y hệt trước.
   Khối ĐỘC LẬP với hình (J/L cut): kéo dời sớm / trễ hơn hình, kéo 2 mép cắt ngắn / dài (trong clip gốc), chia ở vạch đỏ, to / nhỏ 0–200 %,
   mờ vào / ra (menu, bảng phải, hoặc kéo 2 nút tròn ở góc trên khối), xoá = bỏ hẳn tiếng đoạn đó. Xoá / chia / đổi chỗ / thay clip cảnh
   không đụng khối. "Lấy lại tiếng gốc": bỏ các khối của cảnh, cảnh có tiếng lại như trước.
   Khung xem: tiếng clip giải mã 1 lần (Web Audio) -> mỗi khối 1 nguồn phát bám vạch đỏ — đồng hồ khung xem đi theo thẻ video (như
   nhạc nền), lệch nhỏ chỉnh tốc độ ±4 %, lệch > 0,1s mới phát lại đúng chỗ; khối sắp tới hẹn giờ trước nên vào đúng lúc, không vấp.
   Bộ dựng: engine dung_may_chu.am_tach_ds (trộn vào tiếng clip: theo thanh "Tiếng clip" ở Cân tiếng, tự hạ khi có giọng AI,
   giọng "thay hẳn tiếng clip" thì im, −14 LUFS như cũ).
   Phụ đề nghe từ lời của cảnh đã tách đi theo khối (sua_tay_may.ap_neo). Mọi thao tác qua doi() -> Ctrl+Z / Ctrl+Y, tự lưu như cũ.
   Viết thành mô-đun bọc hàm có sẵn (veTimeline, benCanh, veBen, ttDoan, veKhung, dung, menuCanh, chiaCanh, catVach, xoaCanh, nhanDoi,
   dauCanh): không sửa _sua-tay.src.html / _canh-tt.js. */
IC_P.tachAm = '<path d="M3 9v6M6.5 6.5v11M10 9.5v5"/><path d="M17.5 3.5v9m-3.2-3.2 3.2 3.2 3.2-3.2"/><path d="M14 19.5h7"/>';
const TA = {song: {}, au: {}, tam: null, chonLuc: null, hen: 0, phim: false, day: 0};
const taSo = (v, m) => (v == null || v === '' || !isFinite(+v)) ? m : +v;
function taDs() { return (S.plan && Array.isArray(S.plan.am_tach)) ? S.plan.am_tach : []; }
function taKhoi(id) { return id ? taDs().find(k => k.id === id) || null : null; }
const taDai = k => Math.max(0, taSo(k.den, 0) - taSo(k.tu, 0));
function taGt(k, khoa, md, lo, hi) { if (TA.tam && TA.tam.id === k.id && TA.tam.khoa === khoa) return TA.tam.v; return clamp(taSo(k[khoa], md), lo, hi); }
const taAm = k => taGt(k, 'am_luong', 1, 0, 2), taVao = k => taGt(k, 'vao', 0, 0, 10), taRa = k => taGt(k, 'ra', 0, 0, 10);
const taGiayClip = f => S.giay[f] || S.giay[src(f)] || 0;
const taSs = t => (t > 0 ? '+' : t < 0 ? '−' : '') + gs(Math.abs(t));
function taCanhGoc(k) {   // phần cảnh (bocCanh) đã tách ra khối này: cùng goc, cùng clip, chứa nhiều đoạn của khối nhất
  let best = null;
  for (const x of bocCanh()) {
    const c = x.c; if (!c.tach_am || c.tach_am !== k.goc) continue;
    const ov = Math.min(+c.den, +k.den) - Math.max(+c.tu, +k.tu) + (c.file === k.nguon ? 0 : -1000);
    if (!best || ov > best.ov) best = {x, ov};
  }
  return best ? best.x : null;
}
function taLech(k) {   // giây tiếng lệch so với hình của cảnh gốc (+ = tiếng trễ hơn hình); null = không còn cảnh gốc cùng clip
  const x = taCanhGoc(k); if (!x || x.c.file !== k.nguon) return null;
  return r3(k.t - (x.bd + (+k.tu - +x.c.tu)));
}
function taTen(k) { const x = taCanhGoc(k); return x ? 'cảnh ' + (x.i + 1) : base(src(k.nguon)).replace(/\.[^.]+$/, ''); }

/* ---------- các cảnh đang chọn: timeline chọn được nhiều cảnh (khối .sel / .chon, S.sel.nhieu / ds / canhs) thì lấy cả nhóm ---------- */
function taChonHienTai() {
  if (window.QUET && S.quet) { const n = QUET.nhom().canh.filter(id => S.plan.canh.some(c => c._id === id)); if (n.length) return n; }   // gộp 5/11: nhóm quét chọn (dev/_mod-quet.js)
  for (const k of ['nhieu', 'ds', 'canhs']) if (Array.isArray(S.sel[k]) && S.sel[k].length) return S.sel[k].filter(id => S.plan.canh.some(c => c._id === id));
  const dom = $$('#tCanh .blk.sel[data-id], #tCanh .blk.chon[data-id]').map(b => b.dataset.id);
  return dom.length ? [...new Set(dom)] : S.sel.canh ? [S.sel.canh] : [];
}
function taChonNhieu(id) {   // bấm phải vào 1 cảnh: cảnh đó nằm trong nhóm đang chọn thì tách cả nhóm, không thì chỉ cảnh đó (như CapCut)
  const snap = TA.chonLuc && Date.now() - TA.chonLuc.luc < 2000 ? TA.chonLuc.ids : null;
  const ds = snap && snap.length ? snap : taChonHienTai();
  return ds.includes(id) ? ds : [id];
}

/* ---------- tách / lấy lại ---------- */
async function tachAm(ids) {
  if (!S.plan || $('#edit').hidden) return;
  ids = [...new Set((ids || []).filter(Boolean))];
  if (!ids.length) return toast('Chọn 1 cảnh trước rồi bấm Tách âm thanh', true);
  if (typeof window.ranh === 'function' && !window.ranh() && typeof choRanh === 'function') await choRanh(6000);   // chờ mốc cảnh của xem trước (có chuyển cảnh)
  const b = bocCanh(), ok = [], da = [], cam = [];
  for (const x of b) {
    if (!ids.includes(x.c._id)) continue;
    const ng = (S.plan.nguon || {})[x.c.file] || {};
    if (x.c.tach_am) da.push(x.i + 1); else if (ng.co_tieng === false) cam.push(x.i + 1); else ok.push(x);
  }
  if (!ok.length) return toast(da.length ? 'Cảnh ' + da.join(', ') + ' đã tách âm thanh rồi (chuột phải › Lấy lại tiếng gốc để gộp lại)' : 'Clip của cảnh ' + cam.join(', ') + ' không có tiếng để tách', true);
  dung();
  let cuoi = null;
  doi(p => {
    const ds = p.am_tach = Array.isArray(p.am_tach) ? p.am_tach : [];
    for (const x of ok) {
      const c = p.canh.find(z => z._id === x.c._id); if (!c) continue;
      const g = ma('g'), am = amC(c), k = {id: ma('a'), goc: g, nguon: c.file, tu: r3(+c.tu), den: r3(+c.den), t: r3(Math.max(0, x.bd))};
      if (am > 0 && am !== 1) k.am_luong = am;   // âm lượng riêng của cảnh (tab Âm thanh) đi theo khối; cảnh đang tắt tiếng: khối 100%
      c.tach_am = g; ds.push(k); cuoi = k;
    }
    if (cuoi) { S.selLoai = 'am'; S.sel.am = cuoi.id; S.tab = 'canh'; }
  });
  veTabs(); taHienLan();
  const so = ok.map(x => x.i + 1);
  toast((so.length > 1 ? 'Đã tách âm thanh ' + so.length + ' cảnh (' + so.join(', ') + ')' : 'Đã tách âm thanh cảnh ' + so[0])
    + ' ra làn Tiếng tách: kéo khối để dời tiếng, kéo mép để cắt' + (cam.length ? ' · cảnh ' + cam.join(', ') + ' không có tiếng' : '')
    + (da.length ? ' · cảnh ' + da.join(', ') + ' đã tách từ trước' : '')
    + (S.plan.giong && S.plan.giong.thay_tieng ? '. Giọng AI đang thay hẳn tiếng clip nên khối sẽ im' : '') + ' (Ctrl+Z để bỏ)');
}
function layLaiTieng(id) {
  const c = S.plan.canh.find(z => z._id === id); if (!c || !c.tach_am) return;
  const g = c.tach_am, nK = taDs().filter(k => k.goc === g).length, i = S.plan.canh.indexOf(c);
  dung();
  doi(p => {
    if (Array.isArray(p.am_tach)) { p.am_tach = p.am_tach.filter(k => k.goc !== g); if (!p.am_tach.length) delete p.am_tach; }
    p.canh.forEach(z => { if (z.tach_am === g) delete z.tach_am; });
    if (S.selLoai === 'am' && !taKhoi(S.sel.am)) { S.selLoai = 'canh'; S.sel.canh = id; }
  });
  toast('Đã lấy lại tiếng gốc cảnh ' + (i + 1) + (nK ? ' (bỏ ' + (nK > 1 ? nK + ' khối' : 'khối') + ' tiếng tách)' : '') + '. Ctrl+Z để bỏ');
}

/* ---------- sửa khối (mỗi lần = 1 bước Ctrl+Z) ---------- */
function datKhoi(id, o, key, tb) {
  if (!taKhoi(id)) return; TA.tam = null;
  doi(p => { const y = (p.am_tach || []).find(z => z.id === id); if (!y) return; for (const [a, v] of Object.entries(o)) { if (v == null) delete y[a]; else y[a] = v; } }, key);
  if (tb) toast(tb + ' (Ctrl+Z để bỏ)');
}
function xoaKhoi(id) {
  const k = taKhoi(id); if (!k) return; const ten = taTen(k);
  dung();
  doi(p => { p.am_tach = (p.am_tach || []).filter(z => z.id !== id); if (!p.am_tach.length) delete p.am_tach; if (S.sel.am === id) { S.selLoai = 'canh'; S.sel.am = null; } });
  toast('Đã xoá tiếng đoạn này (' + ten + ' vẫn im). Ctrl+Z để lấy lại');
}
function taTrong(k, t) { return t > k.t + 0.05 && t < k.t + taDai(k) - 0.05; }
function chiaKhoi(id, t) {
  const k = taKhoi(id); if (!k) return;
  if (!taTrong(k, t)) return toast('Đưa vạch đỏ vào trong khối tiếng rồi bấm Chia', true);
  const s = r3(+k.tu + (t - k.t));
  if (s - k.tu < 0.1 || k.den - s < 0.1) return toast('Vạch đỏ sát mép khối quá (mỗi phần cần ≥ 0,1s)', true);
  dung();
  doi(p => {
    const ds = p.am_tach, i = ds.findIndex(z => z.id === id), y = ds[i];
    const m = Object.assign(JSON.parse(JSON.stringify(y)), {id: ma('a'), tu: s, t: r3(t)});
    y.den = s; delete m.vao; if (y.ra != null) delete y.ra;   // mờ vào giữ ở nửa đầu, mờ ra ở nửa sau
    ds.splice(i + 1, 0, m); S.selLoai = 'am'; S.sel.am = m.id;
  });
  toast('Đã chia khối tiếng làm 2 (Ctrl+Z để lấy lại)');
}
function catKhoi(id, dau, t) {
  const k = taKhoi(id); if (!k) return;
  if (!taTrong(k, t)) return toast('Đưa vạch đỏ vào trong khối tiếng trước', true);
  const s = r3(+k.tu + (t - k.t));
  if (dau ? k.den - s < 0.1 : s - k.tu < 0.1) return toast('Phần còn lại của khối phải dài ít nhất 0,1s', true);
  dung();
  datKhoi(id, dau ? {tu: s, t: r3(t)} : {den: s});
  toast((dau ? 'Đã cắt bỏ phần tiếng trước' : 'Đã cắt bỏ phần tiếng sau') + ' vạch đỏ (Ctrl+Z để lấy lại)');
}
function khopHinh(id) {
  const k = taKhoi(id), x = k && taCanhGoc(k); if (!x || x.c.file !== k.nguon) return;
  const t = r3(Math.max(0, x.bd + (+k.tu - +x.c.tu)));
  if (Math.abs(t - k.t) < 0.001) return;
  datKhoi(id, {t}, null, 'Tiếng đã khớp lại với hình cảnh ' + (x.i + 1));
}
function chonKhoi(id, hien) {
  if (!taKhoi(id)) return;
  S.selLoai = 'am'; S.sel.am = id; if (S.tab !== 'canh') { S.tab = 'canh'; veTabs(); }
  veBen(true); veTimeline(); if (hien) taHienLan();
}
function taHienLan() {   // làn Tiếng tách nằm cuối timeline: cuộn timeline xuống cho thấy (màn 1366 timeline thấp)
  const bd = $('#tls'), ln = $('#tTach'); if (!bd || !ln || ln.hidden) return;   // r29: cuộn dọc nằm trong #tls, thước ghim trên nên cuộn không mất thước
  const k = taKhoi(S.sel.am), bar = k && $(`#tTach .bar[data-ta="${k.id}"]`), r = (bar || ln).getBoundingClientRect(), rb = bd.getBoundingClientRect(), tr = (($('#ruler') || {}).offsetHeight || 0);
  const day = rb.top + bd.clientHeight;
  if (r.bottom > day - 2) bd.scrollTop += r.bottom - day + 8; else if (r.top < rb.top + tr) bd.scrollTop -= rb.top + tr - r.top + 8;
  if (k) { const sc = $('#tls'), x0 = k.t * S.pps, x1 = (k.t + taDai(k)) * S.pps; if (x1 < sc.scrollLeft || x0 > sc.scrollLeft + sc.clientWidth - 40) sc.scrollLeft = Math.max(0, x0 - sc.clientWidth * 0.3); }
}

/* ---------- tiếng của clip: giải mã bản xem nhẹ 1 lần (Web Audio, 22 kHz mono) -> vừa vẽ sóng âm (40 mức / giây) vừa phát ở khung xem ---------- */
const TA_SR = 22050;
function taUrl(k) { const x = S.proxy[src(k.nguon)]; return x && x.tt === 'xong' && x.url ? x.url : ''; }
async function taiSongClip(k) {
  const p = src(k.nguon); if (TA.song[p]) return;
  const url = taUrl(k);
  if (!url) { clearTimeout(TA.hen); TA.hen = setTimeout(() => { if (taDs().some(z => !TA.song[src(z.nguon)])) veTimeline(); }, 2500); return; }
  TA.song[p] = {dang: true};
  try {
    const r = await fetch(url); if (!r.ok) throw new Error(r.status);
    const raw = await new OfflineAudioContext(1, 1, TA_SR).decodeAudioData(await r.arrayBuffer());
    const n = raw.length, nc = raw.numberOfChannels, x = new Float32Array(n);
    for (let c = 0; c < nc; c++) { const y = raw.getChannelData(c); for (let i = 0; i < n; i++) x[i] += y[i] / nc; }
    const buf = new AudioBuffer({length: Math.max(1, n), numberOfChannels: 1, sampleRate: raw.sampleRate}); if (n) buf.copyToChannel(x, 0);
    const hz = 40, buoc = Math.max(1, Math.floor(raw.sampleRate / hz)), pk = new Float32Array(Math.ceil(n / buoc));
    let mx = 1e-6;
    for (let i = 0; i < pk.length; i++) { let s = 0; const a = i * buoc, b = Math.min(n, a + buoc); for (let j = a; j < b; j++) s += x[j] * x[j]; pk[i] = Math.sqrt(s / Math.max(1, b - a)); if (pk[i] > mx) mx = pk[i]; }
    for (let i = 0; i < pk.length; i++) pk[i] = Math.sqrt(pk[i] / mx);
    TA.song[p] = {pk, hz, D: raw.duration, buf};
  } catch (e) { TA.song[p] = {loi: true}; }
  if (taDs().some(z => src(z.nguon) === p)) { veTimeline(); if (S.playing) taKhung(S.t); }
}
function taDuong(ys) { const N = ys.length; let d = 'M0 50'; ys.forEach((y, i) => { d += ` L${i} ${(50 - y * 46).toFixed(1)}`; }); for (let i = N - 1; i >= 0; i--) d += ` L${i} ${(50 + ys[i] * 46).toFixed(1)}`; return d + ' Z'; }
function songKhoi(k, w) {
  const s = TA.song[src(k.nguon)];
  if (!s) { setTimeout(() => taiSongClip(k), 0); return '<i class="ta-cho"></i>'; }
  if (!s.pk) return s.loi ? '' : '<i class="ta-cho"></i>';
  const L = taDai(k), N = clamp(Math.round(w / 3), 6, 300), dt = L / N, he = clamp(0.8 * taAm(k), 0.08, 1), vao = taVao(k), ra = taRa(k), ys = [];
  for (let i = 0; i < N; i++) {
    const s0 = +k.tu + i * dt, a = Math.floor(s0 * s.hz), b = Math.max(a + 1, Math.ceil((s0 + dt) * s.hz));
    let mx = 0; for (let j = a; j < b && j < s.pk.length; j++) mx = Math.max(mx, s.pk[j] || 0);
    const u = (i + 0.5) * dt, mo = Math.min(vao > 0.01 ? clamp(u / vao, 0, 1) : 1, ra > 0.01 ? clamp((L - u) / ra, 0, 1) : 1);
    ys.push(mx * he * mo);
  }
  return `<svg class="ta-song" viewBox="0 0 ${N - 1} 100" preserveAspectRatio="none" aria-hidden="true"><path d="${taDuong(ys)}"/></svg>`;
}

/* ---------- làn "Tiếng tách" cuối timeline (bọc veTimeline: chỉ hiện khi có khối; khối chồng giờ nhau xuống hàng dưới) ---------- */
function veLanTach() {
  const tlin = $('#tlin'); if (!tlin) return;
  let ln = $('#tTach'), nm = $('#nmTach');
  if (!ln) { ln = document.createElement('div'); ln.className = 'trk tach'; ln.id = 'tTach'; ln.hidden = true; tlin.insertBefore(ln, $('#phl')); ganLan(ln); }
  if (!nm) { nm = document.createElement('span'); nm.id = 'nmTach'; nm.hidden = true; nm.innerHTML = icon('tachAm') + '<b>Tách</b>'; nm.title = 'Tiếng tách: tiếng đã tách khỏi cảnh (chuột phải cảnh › Tách âm thanh)'; $('#tnames').append(nm); }
  const ds = taDs();
  if (!S.plan || !ds.length) { ln.hidden = nm.hidden = true; ln.innerHTML = ''; return; }
  const day = (parseFloat(tlin.style.height) || tlin.offsetHeight) - 4, top = day + 2, pps = S.pps;
  const hang = [], xep = ds.map((k, i) => ({k, i})).sort((a, b) => a.k.t - b.k.t || a.i - b.i);
  for (const o of xep) { let r = hang.findIndex(z => z <= o.k.t + 0.01); if (r < 0) { r = hang.length; hang.push(0); } hang[r] = o.k.t + taDai(o.k); o.r = r; }
  const h = Math.max(1, hang.length) * 24 + 4;
  ln.hidden = nm.hidden = false;
  Object.assign(ln.style, {top: top + 'px', height: h + 'px'}); Object.assign(nm.style, {top: top + 'px', height: h + 'px'});
  tlin.style.height = (top + h + 4) + 'px';
  const tn = $('#tnames'); if (tn) tn.style.minHeight = (top + h + 4) + 'px';
  ln.innerHTML = xep.map(({k, r}) => {
    const L = taDai(k), w = Math.max(8, L * pps - 2), sel = S.selLoai === 'am' && S.sel.am === k.id, lech = taLech(k), am = Math.round(taAm(k) * 100);
    const vao = taVao(k), ra = taRa(k);
    const chu = [taTen(k).replace(/^c/, 'C'), gs(L), am !== 100 ? am + '%' : '', lech != null && Math.abs(lech) >= 0.02 ? (lech > 0 ? 'trễ ' : 'sớm ') + gs(Math.abs(lech)) : ''].filter(Boolean).join(' · ');
    const tip = 'Tiếng tách của ' + taTen(k) + ' (' + base(src(k.nguon)) + ' giây ' + gs(+k.tu) + '–' + gs(+k.den) + ')' + (lech != null && Math.abs(lech) >= 0.02 ? ', ' + (lech > 0 ? 'trễ ' : 'sớm ') + gs(Math.abs(lech)) + ' so với hình' : '') + ' · kéo để dời, kéo mép để cắt, bấm phải để chỉnh';
    return `<div class="bar tach${sel ? ' sel' : ''}${am === 0 ? ' tat' : ''}" data-ta="${k.id}" data-t="${k.t}" style="top:${r * 24 + 3}px;left:${k.t * pps}px;width:${w}px" title="${esc(tip)}">`
      + songKhoi(k, w)
      + (vao > 0.01 ? `<i class="ta-mo dau" style="width:${Math.min(w, vao * pps)}px"></i>` : '') + (ra > 0.01 ? `<i class="ta-mo cuoi" style="width:${Math.min(w, ra * pps)}px"></i>` : '')
      + `<span class="ta-nhan">${icon(am === 0 ? 'tatLoa' : 'tachAm')}<span>${esc(chu)}</span></span>`
      + (w >= 40 ? `<span class="ta-fh dau" data-fh="vao" style="left:${clamp(vao * pps, 0, w - 10)}px" title="Kéo để mờ vào"></span><span class="ta-fh cuoi" data-fh="ra" style="right:${clamp(ra * pps, 0, w - 10)}px" title="Kéo để mờ ra"></span>` : '')
      + `<span class="h l" data-h="l"></span><span class="h r" data-h="r"></span></div>`;
  }).join('');
  if (S.selLoai === 'am') $$('#tCanh .blk.sel').forEach(x => x.classList.remove('sel'));   // đang chọn khối tiếng: cảnh không sáng viền
}
(function () {
  const goc = veTimeline;
  veTimeline = function () { const r = goc.apply(this, arguments); try { veLanTach(); } catch (e) { console.error(e); } return r; };
})();
function taMoc(id) {   // chỗ hút (nam châm 7px) khi kéo: mép cảnh, vạch đỏ, mép khối khác, chỗ khớp hình của chính khối
  const out = [0, S.t];
  for (const x of bocCanh()) out.push(x.bd, x.b);
  for (const k of taDs()) if (k.id !== id) out.push(k.t, k.t + taDai(k));
  const k = taKhoi(id), x = k && taCanhGoc(k); if (x && x.c.file === k.nguon) out.push(x.bd + (+k.tu - +x.c.tu));
  return out;
}
function hutMoc(t, moc, d) { let b = null; for (const m of moc) if (Math.abs(m - t) <= d && (b == null || Math.abs(m - t) < Math.abs(b - t))) b = m; return b; }
function taTrangThai(k) {
  const L = taDai(k), lech = taLech(k);
  return 'Tiếng tách ' + taTen(k) + ': ' + tg(k.t) + ' – ' + tg(k.t + L) + ' (dài ' + gs(L) + ')' + (lech == null ? '' : Math.abs(lech) < 0.02 ? ' · khớp với hình' : ' · ' + (lech > 0 ? 'trễ ' : 'sớm ') + gs(Math.abs(lech)) + ' so với hình');
}
function ganLan(ln) {
  ln.addEventListener('pointerdown', e => {
    if (e.button !== 0 || !S.plan) return;
    const bar = e.target.closest('.bar.tach');
    if (!bar) { dung(); tua(tTuX(e.clientX)); return; }
    e.preventDefault(); e.stopPropagation(); dung();
    const id = bar.dataset.ta, k = taKhoi(id); if (!k) return;
    const h = e.target.dataset.h, fh = e.target.dataset.fh, x0 = e.clientX, goc = JSON.stringify(S.plan), k0 = {tu: +k.tu, den: +k.den, t: +k.t, vao: taVao(k), ra: taRa(k)};
    const lim = taGiayClip(k.nguon) || (k0.den + 600), T = tongT(), L0 = k0.den - k0.tu;
    if (S.selLoai !== 'am' || S.sel.am !== id) chonKhoi(id);
    const moc = taMoc(id);
    let moved = false;
    const mv = ev => {
      const dx = ev.clientX - x0; if (!moved && Math.abs(dx) < 4) return; moved = true;
      const dt = dx / S.pps, hut = 7 / S.pps;
      if (fh === 'vao') { const v = Math.round(clamp(k0.vao + dt, 0, Math.min(5, L0 / 2)) * 10) / 10; if (v) k.vao = v; else delete k.vao; }
      else if (fh === 'ra') { const v = Math.round(clamp(k0.ra - dt, 0, Math.min(5, L0 / 2)) * 10) / 10; if (v) k.ra = v; else delete k.ra; }
      else if (h === 'l') {
        let tu = clamp(k0.tu + dt, Math.max(0, k0.tu - k0.t), k0.den - 0.2); const sn = hutMoc(k0.t + (tu - k0.tu), moc, hut);
        if (sn != null) tu = clamp(k0.tu + (sn - k0.t), Math.max(0, k0.tu - k0.t), k0.den - 0.2);
        k.tu = r3(tu); k.t = r3(k0.t + (tu - k0.tu));
      } else if (h === 'r') {
        let den = clamp(k0.den + dt, k0.tu + 0.2, lim); const sn = hutMoc(k0.t + den - k0.tu, moc, hut);
        if (sn != null) den = clamp(sn - k0.t + k0.tu, k0.tu + 0.2, lim);
        k.den = r3(den);
      } else {
        let t = k0.t + dt; const s1 = hutMoc(t, moc, hut), s2 = hutMoc(t + L0, moc, hut);
        if (s1 != null) t = s1; else if (s2 != null) t = s2 - L0;
        k.t = r3(clamp(t, 0, Math.max(0, T - 0.1)));
      }
      veTimeline(); setSt(fh ? (fh === 'vao' ? 'Mờ vào ' : 'Mờ ra ') + gs(fh === 'vao' ? taVao(k) : taRa(k)) : taTrangThai(k));
    };
    const up = () => {
      removeEventListener('pointermove', mv); removeEventListener('pointerup', up); removeEventListener('pointercancel', up); setSt('');
      if (!moved) { tua(clamp(tTuX(x0), 0, T)); veTimeline(); return; }
      if (+k.tu !== k0.tu || +k.den !== k0.den || +k.t !== k0.t || taVao(k) !== k0.vao || taRa(k) !== k0.ra) {
        S.undo.push(goc); if (S.undo.length > 100) S.undo.shift(); S.redo = []; S.lastKey = ''; sauDoi();
      } else veTimeline();
    };
    addEventListener('pointermove', mv); addEventListener('pointerup', up); addEventListener('pointercancel', up);
  });
}

/* ---------- menu chuột phải: khối tiếng + mục "Tách âm thanh" trong menu cảnh (nhóm Sửa cảnh, sau "Thay clip…") ---------- */
function menuKhoi(id, t) {
  const k = taKhoi(id); if (!k) return [];
  const L = taDai(k), trong = taTrong(k, t), x = taCanhGoc(k), lech = taLech(k), am = Math.round(taAm(k) * 100);
  const vi = trong ? '' : 'Bấm phải vào đúng chỗ muốn chia / cắt trong khối';
  const mo = (khoa, ten) => { const v = khoa === 'vao' ? taVao(k) : taRa(k);
    return {t: ten, nhan: v > 0.01 ? gs(v) : 'không', sub: [0, 0.3, 0.5, 1, 2, 3].filter(z => !z || z <= L / 2 + 1e-6).map(z => ({t: z ? gs(z) : 'Không', chon: Math.abs(v - z) < 0.01,
      f: () => datKhoi(id, {[khoa]: z || null}, null, ten + ' ' + (z ? gs(z) : 'không'))}))}; };
  return [{nhom: 'Tiếng tách · ' + taTen(k) + ' · ' + gs(L)},
    {t: 'Phát từ ' + (trong ? 'chỗ này' : 'đầu khối'), ic: 'play', f: taiT(trong ? t : k.t + 0.001, choi)},
    {t: 'Chỉnh ở bảng bên phải', ic: 'caiDat', f: () => chonKhoi(id, true)},
    '-', {nhom: 'Sửa tiếng'},
    {t: 'Chia ở chỗ này', phim: 'S', ic: 'chia', tat: !trong, ly_do: vi, f: taiT(t, () => chiaKhoi(id, t))},
    {t: 'Cắt bỏ phần trước chỗ này', phim: 'Q', ic: 'catDau', tat: !trong, ly_do: vi, f: taiT(t, () => catKhoi(id, true, t))},
    {t: 'Cắt bỏ phần sau chỗ này', phim: 'W', ic: 'catCuoi', tat: !trong, ly_do: vi, f: taiT(t, () => catKhoi(id, false, t))},
    {t: 'To / nhỏ', ic: 'loa', nhan: am + '%', sub: [[0, 'tắt'], [25, 'rất nhỏ'], [50, 'nhỏ'], [75, ''], [100, 'như gốc'], [125, ''], [150, 'to'], [200, 'rất to']]
      .map(([v, g]) => ({t: v + '%' + (g ? ' · ' + g : ''), chon: am === v, f: () => datKhoi(id, {am_luong: v === 100 ? null : v / 100}, null, 'Tiếng tách ' + v + '%')}))},
    mo('vao', 'Mờ vào'), mo('ra', 'Mờ ra'),
    {t: 'Dời đầu khối tới vạch đỏ', ic: 'catCuoi', tat: Math.abs(S.t - k.t) < 0.01, f: () => datKhoi(id, {t: r3(S.t)}, null, 'Đã dời khối tiếng tới vạch đỏ')},
    {t: 'Khớp lại với hình', tat: !(x && lech), ly_do: !x ? 'Cảnh gốc đã xoá' : !lech ? 'Tiếng đang khớp với hình' : 'Đưa tiếng về đúng chỗ hình cảnh ' + (x.i + 1) + ' (' + taSs(-lech) + ')', f: () => khopHinh(id)},
    '-', {t: 'Lấy lại tiếng gốc', ic: 'loa', tat: !x, ly_do: x ? 'Bỏ khối tiếng tách, cảnh ' + (x.i + 1) + ' có tiếng lại như trước' : 'Cảnh gốc đã xoá', f: () => layLaiTieng(x.c._id)},
    {t: 'Xoá tiếng đoạn này', phim: 'Delete', ic: 'xoa', nguy: true, ly_do: 'Bỏ hẳn tiếng đoạn này (cảnh vẫn im)', f: () => xoaKhoi(id)}, ...mucChung()];
}
function mucTachCanh(c) {
  const ng = (S.plan.nguon || {})[c.file] || {};
  if (c.tach_am) {
    const ks = taDs().filter(k => k.goc === c.tach_am);
    return [ks.length && {t: 'Chọn khối tiếng tách', ic: 'tachAm', f: () => chonKhoi(ks[0].id, true)},
      {t: 'Lấy lại tiếng gốc', ic: 'loa', nhan: ks.length ? '' : 'đã xoá tiếng', ly_do: 'Bỏ khối tiếng tách của cảnh này, cảnh có tiếng lại như trước', f: () => layLaiTieng(c._id)}];
  }
  const ids = taChonNhieu(c._id), n = ids.length, cam = ng.co_tieng === false;
  return [{t: n > 1 ? 'Tách âm thanh ' + n + ' cảnh' : 'Tách âm thanh', phim: 'A', ic: 'tachAm', tat: cam && n === 1, ly_do: cam && n === 1 ? 'Clip này không có tiếng' : 'Tiếng của cảnh thành khối riêng ở làn Tiếng tách: dời sớm / trễ, cắt, chỉnh to nhỏ riêng', f: () => tachAm(ids)}];
}
(function () {
  const goc = menuCanh;
  menuCanh = function (id) {
    const ds = goc.apply(this, arguments);
    try { const c = S.plan.canh.find(z => z._id === id); if (c && ds.length) { let j = ds.findIndex(it => it && it.t === 'Thay clip…'); if (j < 0) j = ds.findIndex(it => it && it.nhom === 'Sửa cảnh'); ds.splice(j < 0 ? ds.length : j + 1, 0, ...mucTachCanh(c)); } }
    catch (e) { console.error(e); }
    return ds;
  };
})();
document.addEventListener('contextmenu', e => {   // pha bắt (trước menu chung của trang): khối tiếng -> menu riêng; khối cảnh -> nhớ nhóm đang chọn
  if ($('#edit').hidden || !S.plan || $('.mbg')) return;
  if (e.target.closest && e.target.closest('#tCanh .blk')) { TA.chonLuc = {ids: taChonHienTai(), luc: Date.now()}; return; }
  const bar = e.target.closest && e.target.closest('#tTach .bar.tach'); if (!bar) return;
  e.preventDefault(); e.stopImmediatePropagation();
  const id = bar.dataset.ta, T = (S.view || {}).T || tongT(), t = clamp(tTuX(e.clientX), 0, T);
  if (S.selLoai !== 'am' || S.sel.am !== id) chonKhoi(id);
  moMenu(e.clientX, e.clientY, menuKhoi(id, t));
}, true);

/* ---------- phím A = tách âm thanh cảnh đang chọn. Khối tiếng đang chọn: S / Ctrl+B chia, Q / W cắt, Delete xoá (bọc hàm có sẵn) ---------- */
document.addEventListener('keydown', e => {
  if ($('#edit').hidden || $('.mbg') || !S.plan || e.ctrlKey || e.altKey || e.metaKey || e.repeat) return;
  const ae = document.activeElement || {}, go = /TEXTAREA|SELECT/.test(ae.tagName || '') || (ae.tagName === 'INPUT' && !/^(checkbox|radio|button|range)$/.test(ae.type)) || ae.isContentEditable;
  if (go || (e.key !== 'a' && e.key !== 'A')) return;
  e.preventDefault(); e.stopPropagation();
  if (S.selLoai === 'am' && taKhoi(S.sel.am)) return toast('Đang chọn khối tiếng tách. Chọn 1 cảnh trên timeline rồi bấm A để tách âm thanh cảnh đó');
  const ds = taChonHienTai();
  if (ds.length === 1) { const c = S.plan.canh.find(z => z._id === ds[0]); if (c && c.tach_am) return toast('Cảnh ' + (S.plan.canh.indexOf(c) + 1) + ' đã tách âm thanh rồi. Muốn gộp lại: chuột phải cảnh › Lấy lại tiếng gốc'); }
  tachAm(ds);
}, true);
(function () {
  const khoiChon = () => S.selLoai === 'am' ? taKhoi(S.sel.am) : null;
  const gChia = chiaCanh, gCat = catVach, gXoa = xoaCanh, gNhan = nhanDoi;
  chiaCanh = function () { const k = khoiChon(); if (!k) return gChia.apply(this, arguments); chiaKhoi(k.id, S.t); };
  catVach = function (dau) { const k = khoiChon(); if (!k) return gCat.apply(this, arguments); catKhoi(k.id, dau, S.t); };
  xoaCanh = function (id) { const k = khoiChon(); if (!k || id) return gXoa.apply(this, arguments); xoaKhoi(k.id); };
  nhanDoi = function () {   // bản sao của cảnh đã tách: im như bản gốc nhưng là nhóm riêng ("Lấy lại tiếng gốc" ở bản sao không bỏ khối của bản gốc)
    const k = khoiChon(); if (k && !arguments[0]) return toast('Đang chọn khối tiếng tách: chọn 1 cảnh rồi mới nhân đôi', true);
    const r = gNhan.apply(this, arguments);
    try { const m = S.plan.canh.find(c => c._id === S.sel.canh); if (m && m.tach_am && S.plan.canh.some(c => c !== m && c.tach_am === m.tach_am)) { m.tach_am = ma('g'); veTimeline(); } } catch (e) {}
    return r;
  };
})();

/* ---------- dấu trên khối cảnh đã tách: loa vàng (cảnh im, âm lượng riêng của cảnh không còn tác dụng) ---------- */
(function () {
  const goc = dauCanh;
  dauCanh = function (c) {
    if (!c || !c.tach_am) return goc.apply(this, arguments);
    const h = goc(Object.assign({}, c, {am_luong: 1})), d = `<span class="hu-a tach" title="Đã tách âm thanh ra làn Tiếng tách: cảnh này im">${icon('tachAm')}</span>`;
    return h ? h.replace('<span class="hu-w">', '<span class="hu-w">' + d) : `<span class="hu-w">${d}</span>`;
  };
})();

/* ---------- khung xem: cảnh đã tách im; khối tiếng phát theo vạch đỏ ---------- */
(function () {
  const gocTt = ttDoan;
  ttDoan = function (d) { const r = gocTt.apply(this, arguments); try { const c = d && d.id ? S.plan.canh.find(x => x._id === d.id) : null; if (c && c.tach_am) r.am = 0; } catch (e) {} return r; };
  const gocKhung = veKhung;
  veKhung = function () { const r = gocKhung.apply(this, arguments); try { taKhung(S.t); } catch (e) { console.error(e); } return r; };
  const gocDung = dung;
  dung = function () { const r = gocDung.apply(this, arguments); try { Object.keys(TA.au).forEach(taBoAu); } catch (e) {} return r; };
})();
function taCtx() {
  if (TA.ctx === undefined) { try { TA.ctx = new (window.AudioContext || window.webkitAudioContext)({latencyHint: 'interactive'}); } catch (e) { TA.ctx = null; } }
  if (TA.ctx && TA.ctx.state === 'suspended') TA.ctx.resume().catch(() => {});
  return TA.ctx;
}
addEventListener('pointerdown', () => { if (taDs().length) taCtx(); }, true);   // trình duyệt chỉ cho mở tiếng sau 1 lần bấm của anh
function taBoAu(id) { const n = TA.au[id]; if (!n) return; delete TA.au[id]; try { const c = n.src.context; n.g.gain.setTargetAtTime(0, c.currentTime, 0.006); n.src.stop(c.currentTime + 0.03); } catch (e) {} }
function taKhung(t) {   // gọi sau mỗi lần vẽ khung xem (đồng hồ đi theo thẻ video): mỗi khối 1 nguồn phát Web Audio, bám vị trí vạch đỏ
  const ds = taDs(), con = new Set(ds.map(k => k.id));
  for (const id of Object.keys(TA.au)) if (!con.has(id)) taBoAu(id);
  if (!ds.length || !S.view) return;
  if (!(S.playing && S.mode === 'xem')) { Object.keys(TA.au).forEach(taBoAu); return; }
  const ctx = taCtx(); if (!ctx) return;
  const now = ctx.currentTime, he = (S.plan.giong ? (S.plan.giong.thay_tieng ? 0 : 0.35) : 1) * (typeof heSoClipXem === 'function' ? heSoClipXem() : 1);   // như tiếng clip (veKhung)
  // đồng hồ = thẻ video đang phát (khung xem đi theo nó): đọc thẳng giờ thẻ video cho khỏi trễ 1 khung; thẻ video còn đang nạp / tua
  // (vừa bấm phát, sang cảnh mới) thì chưa cho khối mới bắt đầu, kẻo tiếng đi trước hình
  const d = doanLuc(t), el = d && (typeof vidDoan === 'function' ? vidDoan(d) : VID[src(d.file)]), dong = d && (d.the_hoi || t - d.bd < (d.dong_bang || 0));
  const von = !!(el && el.classList.contains('on') && !dong), cho = von && (el.paused || el.seeking || el.readyState < 3);
  if (von && !cho) { const tv = d.bd + (d.dong_bang || 0) + (el.currentTime - d.tu); if (Math.abs(tv - t) < 0.6) t = tv; }
  for (const k of ds) {
    const s = TA.song[src(k.nguon)];
    if (!s) { taiSongClip(k); continue; }   // chưa giải mã: nạp (xong là phát tiếp)
    if (!s.buf) continue;
    const L = taDai(k), u = t - k.t, khoa = k.tu + '|' + k.den + '|' + k.t;
    let n = TA.au[k.id];
    if (n && n.khoa !== khoa) { taBoAu(k.id); n = null; }
    if (u >= L - 0.01 || u < -0.35) { if (n) taBoAu(k.id); continue; }
    const want = +k.tu + u;   // giây trong clip đúng lúc này
    if (n) {   // vị trí đang phát (cộng dồn theo tốc độ phát)
      if (now > n.luc) { n.pos += (now - Math.max(n.luc, n.bd)) * (now > n.bd ? n.toc : 0); n.luc = now; }
      const lech = (now >= n.bd ? n.pos : n.off - (n.bd - now)) - want;
      if (Math.abs(lech) > 0.1) { taBoAu(k.id); n = null; }   // lệch nhiều (tua, máy kẹt): phát lại đúng chỗ
      else if (now >= n.bd) { const toc = Math.abs(lech) > 0.025 ? clamp(1 - lech * 0.8, 0.96, 1.04) : 1; if (toc !== n.toc) { n.toc = toc; n.src.playbackRate.setValueAtTime(toc, now); } }
    }
    if (!n && cho) continue;
    if (!n) {   // bắt đầu đúng giờ: khối sắp tới thì hẹn trước theo đồng hồ tiếng (không trễ 1 khung hình)
      const sn = ctx.createBufferSource(), g = ctx.createGain(), tre = Math.max(0, -u), off = u < 0 ? +k.tu : want;
      sn.buffer = s.buf; sn.connect(g); g.connect(ctx.destination); g.gain.value = 0;
      try { sn.start(now + tre, off, Math.max(0.01, +k.den - off)); } catch (e) { continue; }
      n = TA.au[k.id] = {src: sn, g, bd: now + tre, off, pos: off, luc: now, toc: 1, khoa};
      sn.onended = () => { if (TA.au[k.id] === n) delete TA.au[k.id]; };
    }
    const uu = Math.max(0, u), vao = taVao(k), ra = taRa(k);
    const mo = Math.min(vao > 0.01 ? clamp(uu / vao, 0, 1) : 1, ra > 0.01 ? clamp((L - uu) / ra, 0, 1) : 1);
    n.vol = clamp(taAm(k) * mo * he * (typeof gdNen === 'function' ? gdNen(k, +k.tu + uu) : 1), 0, 1);   // nghe thử tối đa 100% như tiếng clip / nhạc · r32: đoạn giọng AI đọc lại -> tiếng gốc tắt / còn nền
    n.g.gain.setTargetAtTime(n.vol, Math.max(now, n.bd), 0.012);
  }
}
window.taXem = () => { const c = TA.ctx, now = c ? c.currentTime : 0;   // (để kiểm thử) vị trí đang phát từng khối
  return taDs().map(k => { const n = TA.au[k.id], want = +k.tu + (S.t - k.t);
    const pos = n ? (now >= n.bd ? n.pos + (now - Math.max(n.luc, n.bd)) * n.toc : null) : null;
    return {id: k.id, t: k.t, tu: +k.tu, den: +k.den, chay: !!(n && now >= n.bd), pos, want, lech: pos == null ? null : pos - want, vol: n ? n.vol : null, toc: n ? n.toc : null, ctx: c ? c.state : ''}; }); };

/* ---------- bảng bên phải: chọn khối tiếng -> tab Cảnh hiện bảng của khối (cùng kiểu bảng gọn dev/_mod-ben-phai: nhóm phẳng,
   hàng nhãn · thanh · ô số gõ được · ↺, ghi chú thành dấu (i)); cảnh đã tách -> nhóm Tiếng clip báo "đã tách" + nút ---------- */
function taThanh(k, khoa) {
  const d = TA_R[khoa], v = d.ui(k), max = taMax(k, khoa), p = max > d.min ? (v - d.min) / (max - d.min) * 100 : 0;
  return `<div class="tt-h${khoa === 'am_luong' && v > 100 ? ' qua' : ''}"><label for="ta-${khoa}">${d.ten}</label>
    <input type="range" id="ta-${khoa}" class="tt-r" data-ta-r="${khoa}" min="${d.min}" max="${max}" step="${d.step}" value="${v}" style="--t0:0%;--t1:${p.toFixed(1)}%">
    <input type="text" class="tt-so" data-ta-ra="${khoa}" data-ta-so="${khoa}" value="${esc(d.nhan(v))}" inputmode="decimal" autocomplete="off" spellcheck="false" aria-label="${d.ten}: gõ số rồi Enter">
    <button type="button" class="btn small icon ghost tt-lai" data-ta-lai="${khoa}" ${v === d.md ? 'disabled' : ''} aria-label="${d.ten}: về mặc định" data-tip="Về mặc định">${icon('datLai')}</button></div>`;
}
const taGiay = v => (Math.round(v) / 10).toString().replace('.', ',') + 's';
const TA_R = {   // thanh kéo / ô số <-> giá trị trong kế hoạch
  am_luong: {ten: 'Âm lượng', min: 0, step: 1, buoc: 1, ui: k => Math.round(taAm(k) * 100), ve: v => v / 100, md: 100, nhan: v => v + '%',
    doc: s => { const m = s.match(/-?\d+(\.\d+)?/); if (!m) return /tắt|không/.test(s) ? 0 : null; let v = parseFloat(m[0]); if (m[1] && v <= 2) v *= 100; return Math.round(v); }},
  vao: {ten: 'Mờ vào', min: 0, step: 1, buoc: 1, ui: k => Math.round(taVao(k) * 10), ve: v => v / 10, md: 0, nhan: taGiay,
    doc: s => { const m = s.match(/\d+(\.\d+)?/); if (!m) return /không|tắt/.test(s) ? 0 : null; return Math.round(parseFloat(m[0]) * (/ms/.test(s) ? 0.01 : 10)); }},
  ra: {ten: 'Mờ ra', min: 0, step: 1, buoc: 1, md: 0, nhan: taGiay, ui: k => Math.round(taRa(k) * 10), ve: v => v / 10}
};
TA_R.ra.doc = TA_R.vao.doc;
const taMax = (k, khoa) => khoa === 'am_luong' ? 200 : Math.max(1, Math.round(Math.min(5, taDai(k) / 2) * 10));
function benKhoi(k) {
  const x = taCanhGoc(k), lech = taLech(k), L = taDai(k), p = src(k.nguon), lim = taGiayClip(k.nguon);
  const thay = S.plan.giong && S.plan.giong.thay_tieng, ct = typeof canTieng === 'function' ? canTieng('clip') : 1, trong = taTrong(k, S.t);
  const vi = lech == null ? '' : Math.abs(lech) < 0.02 ? ' · <span class="ta-khop">khớp hình</span>' : ' · <span class="ta-lech">' + (lech > 0 ? 'trễ ' : 'sớm ') + gs(Math.abs(lech)) + ' so với hình</span>';
  return `<div class="tt-dau ta-dau"><div class="th" style="background-image:url('${thumbUrl(p, (+k.tu + +k.den) / 2)}')"><span class="ta-th">${icon('tachAm')}</span></div>
      <div class="tt-ten"><b>Tiếng tách<span class="count">${esc(x ? 'cảnh ' + (x.i + 1) : 'cảnh gốc đã xoá')}</span><span class="tt-dai">${gs(L)}</span></b>
        <small data-tip="Đoạn ${gs(+k.tu)}–${gs(+k.den)} của clip ${esc(base(p))}, đặt ở ${tg(k.t)} – ${tg(k.t + L)} trên video">Từ ${tg(k.t)}${vi}</small></div>
      ${x ? `<span class="tt-nav"><button type="button" class="btn small icon" data-ta-a="ve-canh" aria-label="Chọn cảnh ${x.i + 1}" data-tip="Chọn cảnh gốc (cảnh ${x.i + 1})">${icon('trai')}</button></span>` : ''}</div>`
    + `<div class="box tt-box ta-box"><div class="row"><h2 class="sec grow">Âm thanh</h2></div>${taThanh(k, 'am_luong')}${taThanh(k, 'vao')}${taThanh(k, 'ra')}
        ${thay ? '<p class="note giu ta-bao-do"><b>Giọng AI đang thay hẳn tiếng clip</b>: khối này im khi xem và khi xuất (đổi ở Thư viện › Giọng AI).</p>' : ''}
        <p class="note">Vẫn là tiếng clip: theo thanh Tiếng clip ở Cân tiếng${ct !== 1 ? ' (đang ' + Math.round(ct * 100) + '%)' : ''}, tự hạ khi có giọng AI, app tự cân cả video về chuẩn TikTok. Trên 100%: nghe thử tối đa 100%, bản xuất mới to hơn. Mờ vào / ra: tiếng to dần ở đầu khối, nhỏ dần ở cuối khối (hoặc kéo 2 nút tròn ở góc trên khối trên timeline).</p></div>
      <div class="box tt-box ta-box"><div class="row"><h2 class="sec grow">Vị trí</h2></div>
        <div class="row ta-nut"><button type="button" class="btn small" data-ta-a="vach" ${Math.abs(S.t - k.t) < 0.01 ? 'disabled' : ''} data-tip="Dời đầu khối tiếng tới vạch đỏ">${icon('catCuoi')}Tới vạch đỏ</button>
          <button type="button" class="btn small" data-ta-a="khop" ${x && lech ? '' : 'disabled'} data-tip="${x ? 'Đưa tiếng về đúng chỗ hình cảnh ' + (x.i + 1) : 'Cảnh gốc đã xoá'}">${icon('giua')}Khớp hình</button>
          <button type="button" class="btn small" data-ta-a="chia" ${trong ? '' : 'disabled'} data-tip="${trong ? 'Chia khối ở vạch đỏ' : 'Đưa vạch đỏ vào trong khối trước'}" data-phim="S">${icon('chia')}Chia</button></div>
        <p class="note">Kéo khối trên timeline cho tiếng vào sớm / trễ hơn hình (J/L cut), kéo 2 mép để cắt ngắn / dài${lim ? ' (tối đa hết clip, ' + gs(lim) + ')' : ''}. Xoá / chia / đổi chỗ cảnh không đụng khối này.</p></div>
      <div class="box tt-box ta-box ta-cuoi"><div class="row"><button type="button" class="btn small" data-ta-a="lay-lai" ${x ? '' : 'disabled'} data-tip="${x ? 'Bỏ khối tiếng tách, cảnh ' + (x.i + 1) + ' có tiếng lại như trước' : 'Cảnh gốc đã xoá'}">${icon('loa')}Lấy lại tiếng gốc</button>
        <span class="grow"></span><button type="button" class="btn small danger" data-ta-a="xoa" data-tip="Bỏ hẳn tiếng đoạn này (cảnh vẫn im)" data-phim="Delete">${icon('xoa')}Xoá tiếng này</button></div></div>`
    + ((S.plan.kieu || {}).duong === 'premiere' ? `<p class="note dim tt-pr" tabindex="0" data-tip="Video này Claude dựng bằng Premiere: tiếng tách có ở bản xuất trong app (Xuất bản nháp / Xuất video); lần sau nhờ Claude dựng lại bằng Premiere thì tiếng về như cũ (theo cảnh).">${icon('thongTin')}<span>Video dựng bằng Premiere: tiếng tách chỉ có khi xuất trong app</span></p>` : '');
}
(function () {
  const gocBen = benCanh;
  benCanh = function () { if (S.selLoai === 'am') { const k = taKhoi(S.sel.am); if (k) return benKhoi(k); S.selLoai = 'canh'; } return gocBen.apply(this, arguments); };
  const gocVe = veBen;
  veBen = function () {
    if (S.plan && S.selLoai === 'am' && !taKhoi(S.sel.am)) S.selLoai = 'canh';
    const r = gocVe.apply(this, arguments);
    try { taBaoCanh(); } catch (e) { console.error(e); }
    return r;
  };
})();
function taBaoCanh() {   // tab Cảnh › Âm thanh của cảnh đã tách: dòng báo + nút trong nhóm Tiếng clip, khoá thanh âm lượng (cảnh đang im)
  if (!S.plan || S.tab !== 'canh' || S.selLoai === 'am') return;
  const pane = $('#pane'), c = S.plan.canh.find(z => z._id === S.sel.canh) || S.plan.canh[0]; if (!pane || !c || !c.tach_am || $('.ta-bao', pane)) return;
  const r = $('input[data-tt="am"]', pane), box = r && r.closest('.tt-box'); if (!box) return;
  const ks = taDs().filter(k => k.goc === c.tach_am), h = r.closest('.tt-h');
  h.insertAdjacentHTML('beforebegin', `<div class="ta-bao">${icon('tachAm')}<span><b>Đã tách âm thanh</b> ra làn Tiếng tách${ks.length ? '' : ' (khối đã xoá)'}: cảnh này im, chỉnh tiếng ở khối tách.</span></div>
    <div class="row ta-bao-n">${ks.length ? `<button type="button" class="btn small" data-ta-a="chon" data-ta-id="${ks[0].id}">${icon('tachAm')}Chọn khối tiếng</button>` : ''}<button type="button" class="btn small" data-ta-a="lay-lai-canh" data-ta-id="${c._id}">${icon('loa')}Lấy lại tiếng gốc</button></div>`);
  h.classList.add('tat'); h.dataset.tip = 'Cảnh đã tách âm thanh: âm lượng chỉnh ở khối tiếng tách';
  $$('input[data-tt="am"], input[data-tt-so="am"], [data-tt-lai="am"]', box).forEach(x => { x.disabled = true; });
  const t = $('[data-tt-a="tat-tieng"]', box); if (t) t.hidden = true;
}
$('#pane').addEventListener('click', e => {
  const b = e.target.closest('button[data-ta-a], button[data-ta-lai]'); if (!b || b.disabled || !S.plan) return;
  e.stopPropagation();
  const a = b.dataset.taA;
  if (a === 'chon') return chonKhoi(b.dataset.taId, true);
  if (a === 'lay-lai-canh') return layLaiTieng(b.dataset.taId);
  const k = taKhoi(S.sel.am); if (!k) return;
  if (b.dataset.taLai) { const d = TA_R[b.dataset.taLai]; return datKhoi(k.id, {[b.dataset.taLai]: null}, null, d.ten + ': về mặc định'); }
  if (a === 've-canh') { const x = taCanhGoc(k); if (!x) return; S.selLoai = 'canh'; S.sel.canh = x.c._id; dung(); tua(x.bd + 0.02); giuVach(); veBen(true); veTimeline(); return; }
  if (a === 'vach') return datKhoi(k.id, {t: r3(S.t)}, null, 'Đã dời khối tiếng tới vạch đỏ');
  if (a === 'khop') return khopHinh(k.id);
  if (a === 'chia') return chiaKhoi(k.id, S.t);
  if (a === 'lay-lai') { const x = taCanhGoc(k); if (x) layLaiTieng(x.c._id); return; }
  if (a === 'xoa') return xoaKhoi(k.id);
});
function taDongBo(k, khoa, giuO) {   // sau khi ghi (bảng không vẽ lại lúc đang gõ): thanh, ô số, nút ↺ của hàng
  const d = TA_R[khoa], v = d.ui(k), r = $(`#pane input[data-ta-r="${khoa}"]`), o = $(`#pane input[data-ta-so="${khoa}"]`), l = $(`#pane [data-ta-lai="${khoa}"]`);
  if (r) { r.value = v; r.style.cssText = `--t0:0%;--t1:${(+r.max > 0 ? v / +r.max * 100 : 0).toFixed(1)}%`; const h = r.closest('.tt-h'); if (h && khoa === 'am_luong') h.classList.toggle('qua', v > 100); }
  if (o && !giuO) o.value = d.nhan(v);
  if (l) l.disabled = v === d.md;
}
function taGhi(k, khoa, v, key) {   // v = số trên thanh
  const d = TA_R[khoa]; v = clamp(Math.round(v), d.min, taMax(k, khoa));
  const x = d.ve(v), cu = khoa === 'am_luong' ? clamp(taSo(k.am_luong, 1), 0, 2) : clamp(taSo(k[khoa], 0), 0, 10);
  TA.tam = null;
  if (Math.abs(x - cu) > 1e-6) datKhoi(k.id, {[khoa]: x === (khoa === 'am_luong' ? 1 : 0) ? null : x}, key);
}
$('#pane').addEventListener('pointerdown', e => { if (e.target.closest('input[data-ta-r]')) TA.phim = false; });
$('#pane').addEventListener('keydown', e => {
  const r = e.target.closest && e.target.closest('input[data-ta-r]');
  if (r && /^(Arrow|Page|Home|End)/.test(e.key)) { TA.phim = true; e.stopPropagation(); return; }
  const o = e.target.closest && e.target.closest('input[data-ta-so]'); if (!o) return;
  const k = taKhoi(S.sel.am), khoa = o.dataset.taSo, d = TA_R[khoa]; if (!k || !d) return;
  if (e.key === 'Enter') { e.preventDefault(); o.value = d.nhan(d.ui(taKhoi(k.id))); o.select(); return; }
  if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); const v = d.doc(String(TA.oCu || '').toLowerCase().replace(/,/g, '.')); if (v != null) taGhi(k, khoa, v, 'taso:' + k.id + ':' + khoa); o.value = TA.oCu || d.nhan(d.ui(k)); o.blur(); return; }
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault(); e.stopPropagation();
    taGhi(k, khoa, d.ui(k) + (e.key === 'ArrowUp' ? 1 : -1) * (e.shiftKey ? 10 : d.buoc), 'taso:' + k.id + ':' + khoa);
    const k2 = taKhoi(k.id); if (k2) { taDongBo(k2, khoa); o.select(); }
  }
});
$('#pane').addEventListener('focusin', e => { const o = e.target.closest && e.target.closest('input[data-ta-so]'); if (!o) return; TA.oCu = o.value; setTimeout(() => { if (document.activeElement === o) o.select(); }, 0); });
$('#pane').addEventListener('focusout', e => {   // rời ô: hiện lại chữ chuẩn (gõ sai thì về số đang dùng)
  const o = e.target.closest && e.target.closest('input[data-ta-so]'); if (!o) return;
  const k = taKhoi(S.sel.am), d = TA_R[o.dataset.taSo]; if (k && d) o.value = d.nhan(d.ui(k));
  TA.oCu = null;
});
$('#pane').addEventListener('input', e => {
  const o = e.target.closest && e.target.closest('input[data-ta-so]');
  if (o) {   // gõ số: nghe / thấy ngay, các lần gõ liền nhau gộp 1 bước Ctrl+Z
    const k = taKhoi(S.sel.am), khoa = o.dataset.taSo, d = TA_R[khoa]; if (!k || !d) return;
    const v = d.doc(String(o.value).normalize('NFC').toLowerCase().replace(/−/g, '-').replace(/,/g, '.').trim());
    if (v == null) return;
    taGhi(k, khoa, v, 'taso:' + k.id + ':' + khoa); const k2 = taKhoi(k.id); if (k2) taDongBo(k2, khoa, true);
    return;
  }
  const r = e.target.closest && e.target.closest('input[data-ta-r]'); if (!r) return;   // kéo thanh: nghe ngay (đang phát), thả tay mới lưu = 1 bước Ctrl+Z
  const k = taKhoi(S.sel.am), d = TA_R[r.dataset.taR]; if (!k || !d) return;
  const v = +r.value, so = $(`#pane input[data-ta-so="${r.dataset.taR}"]`); if (so) so.value = d.nhan(v);
  r.style.cssText = `--t0:0%;--t1:${(+r.max > 0 ? v / +r.max * 100 : 0).toFixed(1)}%`;
  const h = r.closest('.tt-h'); if (h && r.dataset.taR === 'am_luong') h.classList.toggle('qua', v > 100);
  TA.tam = {id: k.id, khoa: r.dataset.taR, v: d.ve(v)};
});
$('#pane').addEventListener('change', e => {
  const r = e.target.closest && e.target.closest('input[data-ta-r]'); if (!r) return;
  const k = taKhoi(S.sel.am), khoa = r.dataset.taR; if (!k || !TA_R[khoa]) return;
  const kb = TA.phim;
  taGhi(k, khoa, +r.value, kb ? 'ta:' + k.id + ':' + khoa : undefined);
  if (kb) setTimeout(() => { const x = $(`#pane input[data-ta-r="${khoa}"]`); if (x && document.activeElement !== x) x.focus(); }, 0);
});

/* ---------- nút "Tách âm" ở thanh dưới khung xem (cạnh Thay clip) ---------- */
(function () {
  const thay = $('#bThay'); if (!thay || $('#bTachAm')) return;
  const b = document.createElement('button'); b.type = 'button'; b.id = 'bTachAm'; b.className = 'btn small ico co-chu';
  b.innerHTML = icon('tachAm') + '<span class="nut-chu">Tách âm</span>'; b.setAttribute('aria-label', 'Tách âm thanh cảnh đang chọn (A)');
  b.dataset.tip = 'Tách âm thanh cảnh đang chọn ra làn riêng'; b.dataset.phim = 'A';
  b.onclick = () => { if (S.selLoai === 'am') return toast('Đang chọn khối tiếng tách: chọn 1 cảnh trước'); const ds = taChonHienTai(); if (ds.length === 1) { const c = S.plan.canh.find(z => z._id === ds[0]); if (c && c.tach_am) return layLaiTieng(c._id); } tachAm(ds); };
  thay.after(b);
  const ve = () => { const c = S.plan && S.plan.canh.find(z => z._id === S.sel.canh), da = !!(c && c.tach_am && S.selLoai !== 'am');
    b.classList.toggle('on', da); b.innerHTML = icon(da ? 'loa' : 'tachAm') + `<span class="nut-chu">${da ? 'Lấy lại tiếng' : 'Tách âm'}</span>`;
    b.dataset.tip = da ? 'Cảnh này đã tách âm thanh: bấm để lấy lại tiếng gốc (bỏ khối tách)' : 'Tách âm thanh cảnh đang chọn ra làn riêng'; b.dataset.phim = da ? '' : 'A'; };
  const goc = veTimeline;
  veTimeline = function () { const r = goc.apply(this, arguments); try { ve(); } catch (e) {} return r; };
})();

/* gộp 5/11: vừa tách âm (đang chọn khối tiếng) mà bấm lại đúng cảnh đó: bảng phải phải về bảng cảnh (veBen chỉ chạy khi S.sel.canh đổi) */
addEventListener('pointerdown', e => {
  if (e.button !== 0 || S.selLoai !== 'am' || !e.target.closest || !e.target.closest('#tCanh .blk[data-id]')) return;
  setTimeout(() => { if (S.selLoai === 'am') return; if (S.tab !== 'canh') { S.tab = 'canh'; veTabs(); } veBen(true); veTimeline(); }, 0);
}, true);
