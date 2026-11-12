/* ============================== NHẠC NỀN (4/11, anh duyệt mục "Nhạc nền" trong bài hướng dẫn CapCut) ==============================
   "Thêm nhạc từ file của tiệm hoặc nhạc miễn phí bản quyền; tự hạ nhạc khi có giọng đọc / người nói; chỉnh to nhỏ giữa nhạc, giọng, tiếng clip".
   Kế hoạch: plan.nhac {local, file, ten, tu (giây bắt đầu trong file), am_luong 0–2, ha_khi_noi, vao / ra (giây mờ dần), giay}
             plan.can_tieng {giong 0–2, clip 0–2} (chỉ ghi giá trị khác 1). Bỏ nhạc = plan.nhac null (không xoá khoá: máy chủ lấy
             nhạc của ke-hoach.json khi trang không gửi khoá). Bộ dựng: engine dung_may_chu.tron_them (sidechain thật, −14 LUFS).
   Thư viện › Nhạc (veNhacTV): thư mục nhạc của tiệm (config "thu_muc_nhac" / anh chọn bằng bảng chọn thư mục CTM) + nhạc miễn phí
   kèm app (tự tạo, CC0), nghe thử, bấm / kéo xuống timeline để thêm, cân tiếng nhạc / giọng / tiếng clip.
   Làn Nhạc dưới làn Giọng (veLanNhac, sóng âm giải mã bằng Web Audio), bấm phải: đổi nhạc, bắt đầu từ giây…, to / nhỏ, tự hạ, bỏ nhạc.
   Khung xem trước: thẻ #nhacXem phát theo vạch đỏ (nhacKhung, gọi từ veKhung), hạ nhạc gần đúng trong lúc có câu phụ đề / giọng AI.
   Mọi thao tác qua doi() -> Ctrl+Z, tự lưu như cũ. Nhạc là TUỲ CHỌN: kênh hay gắn nhạc trend ngay trong TikTok lúc đăng. */
IC_P.nhac = '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>';
const NH = {ds: null, dang: false, loi: '', nghe: '', a: null, song: {}, tam: null, el: null, tim: '', keo: false, hop: null};
const nhSo = (v, m) => (v == null || v === '' || !isFinite(+v)) ? m : +v;
const nhacUrl = p => '/api/sua-tay/nhac?p=' + encodeURIComponent(p) + (S.v ? '&v=' + encodeURIComponent(S.v) : '');
const nhPhut = t => { t = Math.max(0, Math.round(t || 0)); return Math.floor(t / 60) + ':' + String(t % 60).padStart(2, '0'); };
function nhacAm() { const n = S.plan && S.plan.nhac; if (!n) return 0; if (NH.tam && NH.tam.k === 'nhac') return NH.tam.v; return clamp(nhSo(n.am_luong, 1), 0, 2); }
function canTieng(k) { if (NH.tam && NH.tam.k === k) return NH.tam.v; return clamp(nhSo(((S.plan && S.plan.can_tieng) || {})[k], 1), 0, 2); }
function heSoClipXem() { return canTieng('clip'); }   // veKhung nhân âm lượng clip với hệ số này (cân tiếng)
function khoaNhacTV() { const p = S.plan || {}; return [p.nhac || null, p.can_tieng || null, (p.giong || {}).local || '', !!(p.giong || {}).thay_tieng, NH.dsVer || 0]; }
function nhacD(n) { const s = NH.song[n.local]; return nhSo(n.giay, 0) || (s && s.D) || 0; }

/* ---------- vị trí trong file nhạc ứng với giây t trên video: như bộ dựng (lặp từ đầu bài, nối mờ chéo min(1, D/4) giây) ---------- */
function viTriNhac(t, n, D) {
  const tu = clamp(nhSo(n.tu, 0), 0, Math.max(0, D - 1)), L0 = D - tu;
  if (!(D > 1) || t < L0) return tu + t;
  const xf = Math.min(1, D / 4), k = Math.floor((t - (L0 - xf)) / (D - xf));
  return t - (L0 - xf + k * (D - xf));
}
function diemLap(n, D, T) {   // giây trên video nhạc bắt đầu lặp lại
  const tu = clamp(nhSo(n.tu, 0), 0, Math.max(0, D - 1)), xf = Math.min(1, D / 4), out = [];
  if (!(D > 1)) return out;
  for (let t = D - tu - xf; t < T - 0.3 && out.length < 60; t += D - xf) out.push(t);
  return out;
}
/* ---------- hạ nhạc gần đúng ở khung xem: câu phụ đề (giọng AI đi theo phụ đề) = có người nói ---------- */
function khoangNoi() {
  const g = (S.view || {}).gio || {}, out = [];
  (S.plan.phu_de || []).forEach(p => { const x = g[p._k]; if (x && !x.an && x.t0 != null) out.push([x.t0, x.t1]); });
  if (S.plan.giong && !out.length) { const gg = nhSo(S.plan.giong.giay, 0); if (gg) out.push([0, gg]); }
  return out;
}
function heSoHa(t) {   // 1 = nhạc lúc không ai nói; trong câu: ~ −12 dB; hết câu nhạc lên lại trong ~0,4 giây (như bộ dựng)
  const n = S.plan.nhac; if (!n || n.ha_khi_noi === false) return 0.5;   // tắt tự hạ: nằm thấp cố định (bộ dựng: dưới tiếng nói 12 dB)
  let d = 9;
  for (const [a, b] of khoangNoi()) { if (t >= a - 0.05 && t <= b) { d = 0; break; } d = Math.min(d, t > b ? t - b : (a - t) * 8); }
  return 0.25 + 0.75 * clamp(d / 0.4, 0, 1);
}
function moNhac(t, n, T) { const vao = clamp(nhSo(n.vao, 0.3), 0, 5), ra = clamp(nhSo(n.ra, 1.5), 0, 8); return Math.min(vao > 0.01 ? clamp(t / vao, 0, 1) : 1, ra > 0.01 ? clamp((T - t) / ra, 0, 1) : 1); }

/* ---------- khung xem trước: phát nhạc theo vạch đỏ (gọi cuối veKhung, như thẻ #giong của giọng AI) ---------- */
function nhacKhung(t) {
  const g = $('#giong'); if (g) g.volume = clamp(canTieng('giong'), 0, 1);
  const n = S.plan && S.plan.nhac; let a = $('#nhacXem');
  if (!n || !n.local || S.mode !== 'xem') { if (a) { a.pause(); if (!n || !n.local) a.remove(); } return; }
  if (!a) { a = document.createElement('audio'); a.id = 'nhacXem'; a.preload = 'auto'; document.body.append(a); }
  if (a.dataset.p !== n.local) { a.src = nhacUrl(n.local); a.dataset.p = n.local; }
  if (!S.playing) { if (!a.paused) a.pause(); return; }
  const T = (S.view || {}).T || tongT(), D = nhacD(n) || a.duration || 0, want = viTriNhac(t, n, D);
  a.volume = clamp(0.5 * nhacAm() * heSoHa(t) * moNhac(t, n, T), 0, 1);
  if (Math.abs(a.currentTime - want) > 0.25) { try { a.currentTime = want; } catch (e) {} }
  if (a.paused) a.play().catch(() => {});
  if (NH.nghe) nhNgheDung();
}

/* ---------- sóng âm: giải mã 1 lần mỗi file (Web Audio, 8 kHz mono đủ vẽ), mức trung bình 20 lần / giây ---------- */
async function taiSong(p) {
  if (NH.song[p]) return; NH.song[p] = {dang: true};
  try {
    const r = await fetch(nhacUrl(p)); if (!r.ok) throw new Error(r.status);
    const ab = await new OfflineAudioContext(1, 1, 8000).decodeAudioData(await r.arrayBuffer());
    const x = ab.getChannelData(0), hz = 20, buoc = Math.max(1, Math.floor(ab.sampleRate / hz)), pk = new Float32Array(Math.ceil(x.length / buoc));
    let mx = 1e-6;
    for (let i = 0; i < pk.length; i++) { let s = 0; const a = i * buoc, b = Math.min(x.length, a + buoc); for (let j = a; j < b; j++) s += x[j] * x[j]; pk[i] = Math.sqrt(s / Math.max(1, b - a)); if (pk[i] > mx) mx = pk[i]; }
    for (let i = 0; i < pk.length; i++) pk[i] = Math.sqrt(pk[i] / mx);
    NH.song[p] = {pk, hz, D: ab.duration};
  } catch (e) { NH.song[p] = {loi: true}; }
  if (S.plan && S.plan.nhac && S.plan.nhac.local === p) veTimeline();
  if (NH.hop && NH.hop.p === p) NH.hop.ve();
}
function duongSong(ys) {   // ys 0..1 -> path đối xứng quanh giữa, khung 0..N × 0..100
  const N = ys.length; let d = 'M0 50';
  ys.forEach((y, i) => { d += ` L${i} ${(50 - y * 47).toFixed(1)}`; });
  for (let i = N - 1; i >= 0; i--) d += ` L${i} ${(50 + ys[i] * 47).toFixed(1)}`;
  return d + ' Z';
}
function songLan(n, T) {   // sóng âm đúng đoạn nhạc phát trên video (đã tính giây bắt đầu + lặp), cao theo âm lượng
  const s = NH.song[n.local]; if (!s || !s.pk) return '';
  const N = 360, ys = [], k = clamp(0.6 * nhacAm(), 0.08, 1), dt = T / N;
  for (let i = 0; i < N; i++) {
    const m0 = viTriNhac(i * dt, n, s.D), a = Math.floor(m0 * s.hz), b = Math.max(a + 1, Math.ceil((m0 + dt) * s.hz));
    let mx = 0; for (let j = a; j < b && j < s.pk.length; j++) mx = Math.max(mx, s.pk[j] || 0);
    ys.push(mx * k * moNhac(i * dt + dt / 2, n, T));
  }
  return `<svg class="nh-song" viewBox="0 0 ${N} 100" preserveAspectRatio="none" aria-hidden="true"><path d="${duongSong(ys)}"/></svg>`;
}

/* ---------- làn Nhạc trên timeline (gọi trong veTimeline, ngay dưới làn Giọng). Trả chiều cao làn ---------- */
function veLanNhac(top, T, pps) {
  const ln = $('#tNhac'), nm = $('#nmNhac'); if (!ln || !S.plan) return 0;
  const h = 27, n = S.plan.nhac;
  ln.style.top = top + 'px'; ln.style.height = h + 'px';
  const tn = $('#tnames'); if (tn) tn.style.minHeight = (top + h + 4) + 'px';   // cột tên làn cao bằng các làn (cuộn dọc cùng nhau)
  if (nm) { Object.assign(nm.style, {top: top + 'px', height: h + 'px'}); if (!nm.dataset.ve) { nm.dataset.ve = '1'; nm.innerHTML = icon('nhac') + '<b>Nhạc</b>'; } }
  if (!n || !n.local) {
    ln.innerHTML = `<div class="bar nhac trong" data-t="0" style="top:3px;left:0" data-tip="Thêm nhạc nền (không bắt buộc: kênh hay gắn nhạc trend lúc đăng TikTok)">${icon('them')}<span>Nhạc nền</span></div>`;
    return h;
  }
  if (!NH.song[n.local]) setTimeout(() => taiSong(n.local), 0);
  const D = nhacD(n), am = Math.round(nhacAm() * 100), lap = D ? diemLap(n, D, T) : [];
  const vao = clamp(nhSo(n.vao, 0.3), 0, 5), ra = clamp(nhSo(n.ra, 1.5), 0, 8);
  const chu = [esc(n.ten || base(n.local)), nhSo(n.tu, 0) > 0 ? 'từ ' + nhPhut(n.tu) : '', am !== 100 ? am + '%' : '', n.ha_khi_noi === false ? 'không tự hạ' : '', lap.length ? 'lặp ' + lap.length + ' lần' : ''].filter(Boolean).join(' · ');
  const tip = 'Nhạc nền: ' + (n.ten || base(n.local)) + (D ? ' (bài dài ' + nhPhut(D) + ')' : '') + ' · bấm để mở Thư viện › Nhạc, bấm phải để đổi nhạc, chỉnh giây bắt đầu, to / nhỏ, bỏ nhạc';
  ln.innerHTML = `<div class="bar nhac${S.tv && S.tv.tab === 'nhac' && !S.tv.thu ? ' sel' : ''}" data-t="0" style="top:3px;left:0;width:${Math.max(24, T * pps - 2)}px" title="${esc(tip)}">${songLan(n, T)}`
    + (vao > 0.01 ? `<i class="nh-mo dau" style="width:${vao * pps}px"></i>` : '') + (ra > 0.01 ? `<i class="nh-mo cuoi" style="width:${ra * pps}px"></i>` : '')
    + lap.map(t => `<i class="nh-lap" style="left:${t * pps}px"></i>`).join('')
    + `<span class="nh-nhan">${icon('nhac')}<span>${chu}</span></span></div>`;
  return h;
}
$('#tNhac').addEventListener('click', e => { if (S.keo) return; dung(); tua(tTuX(e.clientX)); if (e.target.closest('.bar')) moTab('nhac'); });
$('#tNhac').addEventListener('contextmenu', e => {
  if ($('#edit').hidden || !S.plan || $('.mbg')) return;
  e.preventDefault(); e.stopPropagation();
  moMenu(e.clientX, e.clientY, menuNhac());
});
function menuNhac() {
  const n = S.plan.nhac;
  if (!n || !n.local) return [{nhom: 'Nhạc nền'}, {t: 'Thêm nhạc nền…', ic: 'nhac', f: () => moTab('nhac')}, ...mucChung()];
  const am = Math.round(nhacAm() * 100), ha = n.ha_khi_noi !== false;
  return [{nhom: 'Nhạc nền · ' + (n.ten || base(n.local))},
    {t: 'Đổi nhạc…', ic: 'thay', f: () => moTab('nhac')},
    {t: 'Bắt đầu từ giây…', nhan: nhSo(n.tu, 0) > 0 ? 'đang ' + nhPhut(n.tu) : '', f: hopBatDau},
    {t: 'To / nhỏ', ic: 'loa', nhan: am + '%', sub: [[25, 'rất nhỏ'], [50, 'nhỏ'], [75, ''], [100, 'mặc định'], [125, ''], [150, 'to'], [200, 'rất to']]
      .map(([v, g]) => ({t: v + '%' + (g ? ' · ' + g : ''), chon: am === v, f: () => datNhac({am_luong: v / 100}, 'Nhạc ' + v + '%')}))},
    {t: 'Tự hạ nhạc khi có giọng / người nói', chon: ha, f: () => datNhac({ha_khi_noi: !ha}, ha ? 'Tắt tự hạ: nhạc nằm thấp cố định cả video' : 'Bật tự hạ nhạc khi có giọng / người nói')},
    {t: 'Cân tiếng nhạc / giọng / tiếng clip…', f: moCanTieng},
    '-', {t: 'Bỏ nhạc', ic: 'xoa', nguy: true, f: nhBo}, ...mucChung()];
}
function moCanTieng() { moTab('nhac'); setTimeout(() => { const b = $('#tvNhac .nh-can'); if (b) { b.scrollIntoView({block: 'nearest'}); b.classList.add('nhay'); setTimeout(() => b.classList.remove('nhay'), 900); } }, 60); }

/* ---------- sửa kế hoạch (mỗi lần = 1 bước Ctrl+Z) ---------- */
function datNhac(o, tb, key) {
  if (!S.plan.nhac) return;
  doi(p => { p.nhac = Object.assign({}, p.nhac, o); }, key);
  if (tb) toast(tb + ' (Ctrl+Z để bỏ)');
}
function nhThem(x) {
  if (!S.plan || !x) return;
  const cu = S.plan.nhac; nhNgheDung();
  if (cu && cu.local === x.p) return toast('Video đang dùng bài “' + x.ten + '”');
  dung();
  doi(p => { p.nhac = Object.assign({local: x.p, file: x.p, ten: x.ten, tu: 0, am_luong: cu ? clamp(nhSo(cu.am_luong, 1), 0, 2) : 1, ha_khi_noi: cu ? cu.ha_khi_noi !== false : true,
    vao: 0.3, ra: 1.5}, x.giay ? {giay: x.giay} : {}, x.mien_phi ? {mien_phi: true} : {}); });
  const T = (S.view || {}).T || tongT();
  toast((cu ? 'Đã đổi nhạc nền: “' : 'Đã thêm nhạc nền “') + x.ten + '”' + (x.giay && x.giay < T - 0.5 ? ' · bài ngắn hơn video, tự lặp lại' : '') + '. Tự hạ khi có giọng / người nói (Ctrl+Z để bỏ)');
}
function nhBo() {
  if (!S.plan.nhac) return;
  const ten = S.plan.nhac.ten; dung();
  doi(p => { p.nhac = null; });
  toast('Đã bỏ nhạc nền' + (ten ? ' “' + ten + '”' : '') + ' (Ctrl+Z để lấy lại)');
}
function datCan(k, v, key) {   // k: nhac | giong | clip; v 0–2
  v = Math.round(clamp(v, 0, 2) * 100) / 100; NH.tam = null;
  if (k === 'nhac') { if (!S.plan.nhac || nhSo(S.plan.nhac.am_luong, 1) === v) return veNH(); return datNhac({am_luong: v}, '', key); }
  if (canTieng(k) === v) return veNH();
  doi(p => { const c = Object.assign({}, p.can_tieng || {}); if (v === 1) delete c[k]; else c[k] = v; if (Object.keys(c).length) p.can_tieng = c; else delete p.can_tieng; }, key);
}

/* ---------- nghe thử trong Thư viện ---------- */
function nhNghe(p, tu) {
  if (NH.nghe === p && tu == null) return nhNgheDung();
  dung(); nhNgheDung();
  const a = NH.a = new Audio(nhacUrl(p)); NH.nghe = p; a.volume = 0.8;
  if (tu) a.addEventListener('loadedmetadata', () => { try { a.currentTime = tu; } catch (e) {} }, {once: true});
  a.addEventListener('ended', nhNgheDung); a.play().catch(() => nhNgheDung());
  if (tu != null) NH.hen = setTimeout(nhNgheDung, 6000);   // "nghe từ đây": 6 giây
  veNghe();
}
function nhNgheDung() { clearTimeout(NH.hen); if (NH.a) { NH.a.pause(); NH.a = null; } if (NH.nghe) { NH.nghe = ''; veNghe(); } }
function veNghe() { $$('#tvNhac [data-nh-nghe]').forEach(b => { const on = b.dataset.nhNghe === NH.nghe; b.classList.toggle('on', on); b.innerHTML = icon(on ? 'pause' : 'play'); b.setAttribute('aria-label', (on ? 'Dừng nghe ' : 'Nghe thử ') + (b.dataset.ten || '')); }); }

/* ---------- Thư viện › Nhạc ---------- */
async function taiNhacDs(moi) {
  NH.dang = true; NH.loi = ''; veNH();
  try { NH.ds = await api('/api/sua-tay/nhac-ds' + (moi ? '?moi=1' : '')); NH.dsVer = (NH.dsVer || 0) + 1; }
  catch (e) { NH.loi = e.message; }
  NH.dang = false; veNH();
}
function veNhacTV(el) { NH.el = el; if (!NH.ds && !NH.dang && !NH.loi) taiNhacDs(); veNH(); }
const tenTmNh = p => String(p || '').replace(/[\\/]+$/, '').split(/[\\/]/).pop() || p;
function thanhCan(k, ten, v, tat, goi) {
  const pct = Math.round(v * 100), id = 'nh-can-' + k;
  return `<div class="tt-h nh-ch${tat ? ' tat' : ''}"${goi ? ` data-tip="${esc(goi)}"` : ''}><label for="${id}">${ten}</label>
    <input type="range" id="${id}" class="tt-r" data-nh-can="${k}" min="0" max="200" step="5" value="${pct}"${tat ? ' disabled' : ''} style="--t0:0%;--t1:${pct / 2}%">
    <output data-nh-ra="${k}">${pct ? pct + '%' : 'Tắt'}</output>
    <button type="button" class="btn small icon ghost tt-lai" data-nh-lai="${k}" ${pct === 100 || tat ? 'disabled' : ''} aria-label="${ten}: về 100%" data-tip="Về 100%">${icon('datLai')}</button></div>`;
}
function dongBai(x, n) {
  const dang = n && n.local === x.p, on = NH.nghe === x.p;
  return `<div class="nh-bai${dang ? ' dang' : ''}" data-nh-p="${esc(x.p)}" role="button" tabindex="0" aria-label="${esc((dang ? 'Đang dùng: ' : 'Thêm nhạc ') + x.ten)}" data-tip="${esc(dang ? 'Video đang dùng bài này' : 'Bấm để thêm vào video (hoặc kéo xuống timeline)')}${x.mo_ta ? ' · ' + esc(x.mo_ta) : ''}">
    <button type="button" class="nh-nghe${on ? ' on' : ''}" data-nh-nghe="${esc(x.p)}" data-ten="${esc(x.ten)}" aria-label="${on ? 'Dừng nghe ' : 'Nghe thử '}${esc(x.ten)}" data-tip="${on ? 'Dừng nghe' : 'Nghe thử (không thêm vào video)'}">${icon(on ? 'pause' : 'play')}</button>
    <span class="nh-t"><b>${esc(x.ten)}</b><small>${[x.giay ? nhPhut(x.giay) : '', x.mo_ta || '', x.nhom || ''].filter(Boolean).map(esc).join(' · ')}</small></span>
    ${dang ? `<span class="nh-dung">${icon('dauTick')}Đang dùng</span>` : `<span class="nh-them" aria-hidden="true">${icon('them')}</span>`}</div>`;
}
function veNH() {
  const el = NH.el; if (!el || !el.isConnected || !S.plan) return;
  const n = S.plan.nhac, d = NH.ds, gi = S.plan.giong, k = NH.tim.trim().toLowerCase();
  const loc = ds => (ds || []).filter(x => !k || (x.ten + ' ' + (x.nhom || '') + ' ' + (x.mo_ta || '') + ' ' + (x.phong_cach || '')).toLowerCase().includes(k));
  let h = '<div class="nh">';
  if (n && n.local) {
    const D = nhacD(n);
    h += `<div class="nh-dang"><span>${icon('nhac')}<span>Video đang dùng nhạc <b>${esc(n.ten || base(n.local))}</b>${nhSo(n.tu, 0) > 0 ? ' · từ giây ' + gs(n.tu) : ''}${D ? ' · bài dài ' + nhPhut(D) : ''}</span></span>
      <span class="nh-dang-n"><button type="button" class="btn small" data-nh-a="tu" data-tip="Bỏ đoạn dạo đầu: video phát nhạc từ giây nào của bài">Bắt đầu từ…</button><button type="button" class="btn small danger" data-nh-a="bo" data-tip="Bỏ nhạc nền khỏi video (Ctrl+Z để lấy lại)">Bỏ nhạc</button></span>
      <label class="nh-ha"><input type="checkbox" data-nh-a="ha"${n.ha_khi_noi !== false ? ' checked' : ''}> Tự hạ nhạc khi có giọng AI / người nói trong clip</label></div>`;
  }
  // cân tiếng
  const thay = gi && gi.thay_tieng;
  h += `<div class="nh-can"><div class="nh-can-h"><b>Cân tiếng</b><span class="note" data-tip="App tự cân cả video về chuẩn TikTok (−14 LUFS): kéo là đổi độ chênh giữa nhạc, giọng, tiếng clip. Trên 100%: nghe thử tối đa 100%, bản xuất mới to hơn.">to / nhỏ giữa 3 tiếng</span></div>
    ${thanhCan('nhac', 'Nhạc', n ? nhacAm() : 1, !n, n ? '' : 'Chưa có nhạc nền')}
    ${(gd => thanhCan('giong', 'Giọng AI', canTieng('giong'), !gi && !gd, gi || gd ? '' : 'Video chưa có giọng đọc AI (Thư viện › Giọng AI)'))(typeof gdCau === 'function' && gdCau().length > 0)}
    ${thanhCan('clip', 'Tiếng clip', thay ? 0 : canTieng('clip'), !!thay, thay ? 'Giọng AI đang thay hẳn tiếng clip (đổi ở Thư viện › Giọng AI)' : '')}</div>`;
  if (!d) { h += NH.loi ? `<p class="tv-note err">${esc(NH.loi)}</p><div class="tv-hang"><button type="button" class="btn small" data-nh-a="tai" data-tip="Đọc lại thư mục nhạc">Thử lại</button></div>` : '<p class="tv-note tv-cho">Đang đọc thư mục nhạc…</p>'; el.innerHTML = h + '</div>'; return; }
  const tiem = d.tiem, mp = d.mien_phi, tong = ((tiem || {}).ds || []).length + ((mp || {}).ds || []).length;
  if (tong > 8) h += `<input type="search" class="inp nh-tim" placeholder="Tìm bài theo tên…" value="${esc(NH.tim)}" aria-label="Tìm bài nhạc">`;
  // nhạc của tiệm
  // 4/11 tối anh: "mấy phần chữ này bị chiếm chỗ nhiều quá" -> câu hướng dẫn vào dấu (i), chưa có thư mục = 1 hàng như thanh thư mục
  h += tvTieuDe('Nhạc của tiệm', tiem ? (tiem.ds.length + ' bài') : '', 'Nhạc nền không bắt buộc (kênh hay gắn nhạc trend lúc đăng TikTok). Bấm 1 bài để thêm hoặc kéo xuống timeline, ▶ nghe thử.');
  if (tiem) {
    h += `<div class="tv-tm"><span class="tv-tmt" data-tip="${esc(tiem.thu_muc)}">${icon('thuMuc')}<b>${esc(tenTmNh(tiem.thu_muc))}</b></span><button type="button" class="btn small" data-nh-a="doi-tm" data-tip="Chọn thư mục nhạc khác">Đổi thư mục</button><button type="button" class="btn small icon ghost" data-nh-a="moi" aria-label="Đọc lại thư mục nhạc" data-tip="Đọc lại (vừa chép thêm nhạc vào thư mục)">${icon('lamMoi')}</button></div>`;
    const ds = loc(tiem.ds);
    h += ds.length ? `<div class="nh-ds">${ds.map(x => dongBai(x, n)).join('')}</div>` : `<p class="tv-note tv-trang">${tiem.ds.length ? 'Không có bài khớp “' + esc(NH.tim) + '”.' : 'Thư mục chưa có file nhạc' + tvI('Chép nhạc của tiệm (mp3, m4a, wav…) vào thư mục này rồi bấm ↻ để đọc lại, hoặc bấm Đổi thư mục.')}</p>`;
  } else {
    h += `<div class="tv-tm tv-trong"><span class="tv-tmt" data-tip="Chọn thư mục đang để nhạc của tiệm (mp3, m4a, wav…) trên máy, app nhớ cho lần sau">${icon('thuMuc')}<span>Chưa chọn thư mục</span></span><button type="button" class="btn small primary" data-nh-a="doi-tm" data-tip="Mở bảng chọn thư mục: chọn thư mục đang để nhạc của tiệm (mp3, m4a, wav…), app nhớ cho lần sau">Chọn thư mục</button></div>`;
  }
  // nhạc miễn phí kèm app
  if (mp && mp.ds.length) {
    const ds = loc(mp.ds);
    h += tvTieuDe('Nhạc miễn phí', 'tự tạo · CC0, không bản quyền');
    // r20 (14 bài): chia nhóm theo phong cách (nhac.json › phong_cach), giữ thứ tự bài trong mỗi nhóm
    const pc = [...new Set(ds.map(x => x.phong_cach || ''))], dsH = a => `<div class="nh-ds">${a.map(x => dongBai(Object.assign({mien_phi: true}, x), n)).join('')}</div>`;
    h += !ds.length ? `<p class="tv-note">Không có bài khớp “${esc(NH.tim)}”.</p>` : pc.length < 2 ? dsH(ds)
      : pc.map(g => { const a = ds.filter(x => (x.phong_cach || '') === g); return `<div class="tvl-h">${esc(g || 'Khác')}<span>${a.length}</span></div>` + dsH(a); }).join('');
  }
  el.innerHTML = h + '</div>';
  const ti = $('.nh-tim', el); if (ti) ti.oninput = () => { NH.tim = ti.value; const c = ti.selectionStart; veNH(); const t2 = $('.nh-tim', NH.el); if (t2) { t2.focus(); t2.setSelectionRange(c, c); } };
}
function timBai(p) { const d = NH.ds || {}; return [...((d.tiem || {}).ds || []), ...((d.mien_phi || {}).ds || []).map(x => Object.assign({mien_phi: true}, x))].find(x => x.p === p); }
$('#libPane').addEventListener('click', e => {
  if (!e.target.closest('#tvNhac') || S.tv.vuaKeo) return;
  const nb = e.target.closest('[data-nh-nghe]'); if (nb) { e.stopPropagation(); return nhNghe(nb.dataset.nhNghe); }
  const lai = e.target.closest('[data-nh-lai]'); if (lai && !lai.disabled) return datCan(lai.dataset.nhLai, 1);
  const a = e.target.closest('[data-nh-a]');
  if (a && a.tagName === 'BUTTON') {
    const k = a.dataset.nhA;
    if (k === 'bo') return nhBo();
    if (k === 'tu') return hopBatDau();
    if (k === 'tai') return taiNhacDs();
    if (k === 'moi') return taiNhacDs(true);
    if (k === 'doi-tm') return doiThuMucNhac();
    return;
  }
  const b = e.target.closest('[data-nh-p]'); if (b) nhThem(timBai(b.dataset.nhP));
});
$('#libPane').addEventListener('change', e => {
  const c = e.target.closest('#tvNhac [data-nh-a="ha"]'); if (c) return datNhac({ha_khi_noi: c.checked}, c.checked ? 'Bật tự hạ nhạc khi có giọng / người nói' : 'Tắt tự hạ: nhạc nằm thấp cố định cả video');
  const r = e.target.closest('#tvNhac input[data-nh-can]'); if (!r) return;
  datCan(r.dataset.nhCan, +r.value / 100, NH.phim ? 'nhcan:' + r.dataset.nhCan : undefined);
});
$('#libPane').addEventListener('input', e => {   // kéo thanh: nghe ngay (khung xem đang phát), thả tay mới lưu = 1 bước Ctrl+Z
  const r = e.target.closest('#tvNhac input[data-nh-can]'); if (!r) return;
  const v = +r.value, o = $(`#tvNhac output[data-nh-ra="${r.dataset.nhCan}"]`); if (o) o.textContent = v ? v + '%' : 'Tắt';
  r.style.cssText = `--t0:0%;--t1:${v / 2}%`; NH.tam = {k: r.dataset.nhCan, v: v / 100};
});
$('#libPane').addEventListener('pointerdown', e => { if (e.target.closest('#tvNhac input[data-nh-can]')) NH.phim = false; });
$('#libPane').addEventListener('keydown', e => {
  const r = e.target.closest && e.target.closest('#tvNhac input[data-nh-can]');
  if (r && /^(Arrow|Page|Home|End)/.test(e.key)) { NH.phim = true; e.stopPropagation(); return; }
  const b = e.target.closest && e.target.closest('#tvNhac .nh-bai'); if (b && (e.key === 'Enter' || e.key === ' ') && e.target === b) { e.preventDefault(); nhThem(timBai(b.dataset.nhP)); }
});
$('#libPane').addEventListener('contextmenu', e => {
  const b = e.target.closest('#tvNhac .nh-bai'); if (!b || !S.plan) return;
  e.preventDefault(); e.stopPropagation();
  const x = timBai(b.dataset.nhP); if (!x) return;
  const dang = S.plan.nhac && S.plan.nhac.local === x.p;
  moMenu(e.clientX, e.clientY, [{nhom: x.ten + (x.giay ? ' · ' + nhPhut(x.giay) : '')},
    {t: dang ? 'Video đang dùng bài này' : S.plan.nhac ? 'Đổi nhạc thành bài này' : 'Thêm vào video', ic: 'nhac', tat: dang, f: () => nhThem(x)},
    {t: NH.nghe === x.p ? 'Dừng nghe' : 'Nghe thử', ic: NH.nghe === x.p ? 'pause' : 'play', f: () => nhNghe(x.p)}]);
});
/* kéo 1 bài từ Thư viện xuống timeline = thêm / đổi nhạc (như kéo clip) */
$('#libPane').addEventListener('pointerdown', e => {
  if (e.button !== 0 || !S.plan) return;
  const t = e.target.closest('#tvNhac .nh-bai'); if (!t || e.target.closest('[data-nh-nghe]')) return;
  const x = timBai(t.dataset.nhP); if (!x) return;
  const x0 = e.clientX, y0 = e.clientY; let keo = false, gh = null, trung = false;
  const mv = ev => {
    if (!keo) { if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < 6) return;
      keo = true; S.tv.keoTha = true; dung(); document.body.classList.add('tv-dang-keo'); $$('.tip').forEach(z => z.classList.remove('on'));
      gh = document.createElement('div'); gh.className = 'tv-bong'; gh.innerHTML = icon('nhac') + `<span>${esc(x.ten)}</span><small></small>`; document.body.append(gh); }
    gh.style.left = (ev.clientX + 12) + 'px'; gh.style.top = (ev.clientY + 10) + 'px';
    const el = document.elementFromPoint(ev.clientX, ev.clientY); trung = !!(el && el.closest('#tls'));
    $('#tNhac').classList.toggle('tha', trung); gh.classList.toggle('co', trung);
    $('small', gh).textContent = trung ? (S.plan.nhac ? 'thả để đổi nhạc nền' : 'thả để thêm nhạc nền') : 'thả xuống timeline';
  };
  const xong = ev => {
    removeEventListener('pointermove', mv); removeEventListener('pointerup', xong); removeEventListener('pointercancel', xong);
    if (!keo) return;
    if (gh) gh.remove(); $('#tNhac').classList.remove('tha'); document.body.classList.remove('tv-dang-keo');
    S.tv.vuaKeo = true; setTimeout(() => { S.tv.vuaKeo = false; S.tv.keoTha = false; }, 0);
    if (ev.type === 'pointerup' && trung) nhThem(x);
  };
  addEventListener('pointermove', mv); addEventListener('pointerup', xong); addEventListener('pointercancel', xong);
});

/* ---------- chọn thư mục nhạc: bảng chọn thư mục sẵn có (CTM) + nút "Dùng thư mục này làm thư mục nhạc" ---------- */
function chonThuMucNhac(batDau, dangChon) {
  return new Promise(xong => {
    const bg = document.createElement('div'); bg.className = 'ctm-bg nh-ctm-bg';
    const hop = document.createElement('div'); hop.setAttribute('role', 'dialog'); hop.setAttribute('aria-modal', 'true'); hop.setAttribute('aria-label', 'Chọn thư mục nhạc của tiệm');
    bg.append(hop); document.body.append(bg);
    const dong = p => { document.removeEventListener('keydown', phim, true); if (ob) ob.disconnect(); bg.remove(); xong(p || null); };
    const phim = ev => { if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); dong(); } };
    document.addEventListener('keydown', phim, true);
    bg.addEventListener('click', ev => { if (ev.target === bg) dong(); });
    const h = CTM.gan(hop, {batDau, dangChon, noi: true, onChon: dong, onDong: () => dong()});
    const td = hop.querySelector('.ctm-h b'); if (td) td.textContent = 'Chọn thư mục nhạc của tiệm';
    const f = hop.querySelector('.ctm-f'), nut = document.createElement('button');
    nut.type = 'button'; nut.className = 'ctm-b ctm-dung nh-ctm-dung'; nut.textContent = 'Dùng thư mục này làm thư mục nhạc'; f.append(nut);
    nut.onclick = () => { if (h.thuMuc) dong(h.thuMuc); };
    const vun = hop.querySelector('.ctm-vun'), ob = vun && new MutationObserver(() => { const t = h.thuMuc; nut.textContent = t ? 'Dùng “' + tenTmNh(t) + '” làm thư mục nhạc' : 'Dùng thư mục này làm thư mục nhạc'; });
    if (ob) ob.observe(vun, {childList: true, subtree: true});
  });
}
async function doiThuMucNhac() {
  const cu = ((NH.ds || {}).tiem || {}).thu_muc || '';
  const p = await chonThuMucNhac(cu ? CTM.cha(cu) : '', cu); if (!p) return;
  try { NH.ds = await api('/api/sua-tay/nhac-thu-muc', {p}); NH.dsVer = (NH.dsVer || 0) + 1; veNH(); toast('Đã chọn thư mục nhạc: ' + tenTmNh(p) + ' (' + ((NH.ds.tiem || {}).ds || []).length + ' bài)'); }
  catch (e) { toast(e.message, true); }
}

/* ---------- "Bắt đầu từ giây…": bỏ đoạn dạo đầu của bài ---------- */
function hopBatDau() {
  const n = S.plan.nhac; if (!n) return;
  const p = n.local, s0 = NH.song[p], D0 = nhacD(n) || (s0 && s0.D) || 0;
  const {m, dong} = modal(`<h3>Nhạc bắt đầu từ giây…</h3><p class="note">Bỏ đoạn dạo đầu của bài: video phát nhạc từ giây này của bài “${esc(n.ten || base(p))}”. Bấm lên sóng âm để chọn nhanh.</p>
    <div class="nh-tu-song" id="nhTuSong"></div>
    <div class="row nh-tu-hang"><input type="range" class="tt-r" id="nhTuR" min="0" step="0.1"><input type="number" class="inp" id="nhTuN" min="0" step="0.1" aria-label="Giây bắt đầu"><span class="note">giây</span></div>
    <div class="acts"><button class="btn" id="nhTuNghe" data-tip="Nghe 6 giây từ chỗ đang chọn">${icon('play')}Nghe từ đây</button><span class="grow"></span><button class="btn" data-dong>Huỷ</button><button class="btn primary" id="nhTuOk">Áp dụng</button></div>`);
  m.classList.add('nh-tu-hop');
  let x = clamp(nhSo(n.tu, 0), 0, Math.max(0, D0 - 1));
  const R = $('#nhTuR', m), N = $('#nhTuN', m);
  const ve = () => {
    const s = NH.song[p], D = nhacD(n) || (s && s.D) || 0, mx = Math.max(0, D - 1);
    R.max = N.max = mx.toFixed(1); x = clamp(x, 0, mx); R.value = N.value = x.toFixed(1); R.style.cssText = `--t0:0%;--t1:${mx ? x / mx * 100 : 0}%`;
    let svg = '';
    if (s && s.pk) { const C = 300, ys = []; for (let i = 0; i < C; i++) { const a = Math.floor(i / C * s.pk.length), b = Math.max(a + 1, Math.floor((i + 1) / C * s.pk.length)); let v = 0; for (let j = a; j < b; j++) v = Math.max(v, s.pk[j]); ys.push(v); }
      svg = `<svg viewBox="0 0 ${C} 100" preserveAspectRatio="none" aria-hidden="true"><path d="${duongSong(ys)}"/></svg>`; }
    $('#nhTuSong', m).innerHTML = (svg || '<span class="note">Đang đọc sóng âm…</span>') + (D ? `<i class="nh-tu-vach" style="left:${x / D * 100}%"></i><i class="nh-tu-bo" style="width:${x / D * 100}%"></i>` : '');
  };
  NH.hop = {p, ve}; ve(); if (!s0) taiSong(p);
  R.oninput = () => { x = +R.value; ve(); };
  N.onchange = () => { x = nhSo(N.value, 0); ve(); };
  $('#nhTuSong', m).onclick = ev => { const r = ev.currentTarget.getBoundingClientRect(), D = nhacD(n) || (NH.song[p] || {}).D || 0; if (!D) return; x = Math.round((ev.clientX - r.left) / r.width * D * 10) / 10; ve(); };
  $('#nhTuNghe', m).onclick = () => nhNghe(p, x);
  $('#nhTuOk', m).onclick = () => { const v = Math.round(x * 10) / 10; nhNgheDung(); dong(); NH.hop = null;
    if (v !== nhSo(n.tu, 0)) { datNhac({tu: v}, 'Nhạc bắt đầu từ giây ' + gs(v)); dung(); veKhung(true); } };
  const bg = m.closest('.mbg'); if (bg) new MutationObserver((_, o) => { if (!bg.isConnected) { o.disconnect(); NH.hop = null; nhNgheDung(); } }).observe(document.body, {childList: true});
}
veTvTabs();   // icon Nhạc vừa thêm vào bộ icon
