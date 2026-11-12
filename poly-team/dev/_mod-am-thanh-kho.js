/* ============================== KHO EFFECT + ÂM THANH NHIỀU HƠN (r37, 11/11/2026) ==============================
   Anh (11/11 10:56): "âm thanh hạn chế quá" -> duyệt lấy hết 60 hiệu ứng + 27 nhạc (CC0), kho dùng chung trên Drive (kho.py).
   1) Âm thanh: 7 nhóm (Chuyển cảnh · Dồn / nổ · Nhấn / bật · Thông báo · Máy & đồ vật · Giá & tiền · Vui), ô tìm hiểu từ đồng nghĩa
      (whoosh -> vút, riser -> dồn, ka-ching -> két tiền…), hàng "Hay dùng" (5 tiếng anh thêm nhiều nhất, nhớ trên máy), nút
      "Tự gắn tiếng chuyển cảnh" (mỗi chỗ cắt 1 whoosh, 1 bước Ctrl+Z), kéo tiếng xuống timeline: "chạm" của tiếng (am-thanh.json › dinh)
      hít vào chỗ cắt cảnh gần nhất (giữ Alt khi thả = đặt tự do).
   2) Nhạc: bài chỉ có ở kho hiện ☁ — bấm nghe / thêm thì app tải về máy trước (có %), rồi mới dùng; vạch drop vàng trên làn Nhạc;
      bấm phải làn Nhạc / nút trong tab: "Đặt drop vào cảnh đang chọn" (đổi giây bắt đầu bài: khoá tu có sẵn).
   Mô-đun này nối TRƯỚC _mod-nhac / _mod-thu-vien-them (build nối theo tên) -> mọi chỗ bọc hàm chạy trong akKhoi() sau khi trang nạp xong.
   Chỉ dùng khoá kế hoạch có sẵn (am_thanh[], nhac.tu): kế hoạch cũ dựng y hệt. */
const AK = {kho: null, tai: {}, may: {}, keoX: null, alt: false, hay: null};
const AK_NHOM = [['chuyen', 'Chuyển cảnh'], ['dong', 'Dồn / nổ'], ['nhan', 'Nhấn / bật'], ['thong_bao', 'Thông báo'], ['may', 'Máy & đồ vật'], ['tien', 'Giá & tiền'], ['vui', 'Vui']];
// từ đồng nghĩa (không dấu) ghép vào chữ tìm của từng tiếng: tìm "whoosh" ra các tiếng Vút, "kaching" ra Két tiền… Nhóm chỉ thêm chữ chung
// của nhóm (tìm "chuyen canh" ra cả nhóm), còn đồng nghĩa gắn theo TÊN tiếng để tìm "seal" không ra cả nhóm Máy & đồ vật.
const AK_DN_NHOM = {chuyen: 'chuyen canh transition', dong: 'don no hoi hop', nhan: 'nhan bat', thong_bao: 'thong bao notification', may: 'may do vat', tien: 'gia tien money', vui: 'vui hai fun'};
const AK_DN_TEN = [[/\bvut\b|luot|quat gio|\bzip\b|hut vao/, 'whoosh swoosh swish'], [/quet/, 'swipe vuot'], [/zoom/, 'zoom phong to'], [/glitch|nhieu/, 'glitch loi man hinh'],
  [/\bdon\b|tang dan/, 'riser build up'], [/\bbum\b|\bdap\b|sub drop|808|trong dien anh|roi no/, 'impact boom bass drop'], [/dem nguoc/, 'countdown 321'],
  [/\bpop\b|\bbup\b|bloop/, 'pop bong bong'], [/click|cham man hinh|cong tac/, 'click tap bam'], [/\bting\b|\bding\b|chuong/, 'ding bell'],
  [/tin nhan|beep/, 'notification message'], [/dung roi|thanh cong|\bdung\b/, 'correct success'], [/\bsai\b|buzzer/, 'wrong error fail'],
  [/chup|lay net/, 'camera shutter'], [/go phim/, 'keyboard typing'], [/mo hop|seal|tui/, 'unbox unboxing khui hop'], [/cam sac/, 'charge charging pin sac'],
  [/ket tien|ting tien/, 'ka ching kaching cash'], [/\bxu\b/, 'coin tien'], [/ting gia/, 'price gia'], [/lap lanh/, 'sparkle'], [/vo tay/, 'applause clap'],
  [/dung bang/, 'tape stop'], [/huyt sao/, 'whistle'], [/logo/, 'logo intro'], [/nhip tim/, 'heartbeat'], [/rung dien thoai/, 'vibrate phone'], [/lat/, 'flip']];
const akHayP = 'st-am-hay';
function akHay() { if (AK.hay) return AK.hay; try { AK.hay = JSON.parse(localStorage.getItem(akHayP) || '{}') || {}; } catch (e) { AK.hay = {}; } return AK.hay; }
function akDem(p) { const h = akHay(); h[p] = (h[p] || 0) + 1; try { localStorage.setItem(akHayP, JSON.stringify(h)); } catch (e) {} }
const akChuaVe = x => !!(x && x.kho && !x.may && !AK.may[x.p]);   // mục ở kho chưa chép về máy (☁)

/* ---------- trạng thái kho (1 hàng gọn, chi tiết vào (i)) ---------- */
async function akTaiKho() { try { AK.kho = await api('/api/sua-tay/kho'); } catch (e) { AK.kho = null; } }
function akHangKho(loai) {
  const k = AK.kho; if (!k || !k.dung) return '';
  if (!k.co) return `<div class="ak-kho loi giu" data-tip="${esc((k.loi || 'Chưa thấy kho') + ' · ' + k.duong + ' · app đang dùng âm thanh / nhạc kèm app, vẫn làm bình thường')}">${icon('canhBao')}<span>Kho effect chưa đồng bộ · đang dùng bản kèm app</span></div>`;
  const n = loai === 'nhac' ? (k.chi_kho || {}).nhac || 0 : (k.so || {}).am_thanh || 0;
  const tip = 'Kho effect trên Drive (' + k.duong + ')' + (k.phien_ban ? ', bản ' + k.phien_ban : '') + ': ' + ((k.so || {}).am_thanh || 0) + ' tiếng, ' + ((k.so || {}).nhac || 0)
    + ' bài, CC0. Bài có ☁ chưa ở máy này: bấm là tải về (lần đầu chậm nếu Drive để "chỉ trên mây").' + (k.hong ? ' Có ' + k.hong + ' mục hỏng bị bỏ qua (xem app-log).' : '');
  return `<div class="ak-kho" data-tip="${esc(tip)}"><span class="ak-may">☁</span><span>${loai === 'nhac' ? n + ' bài ở kho Drive · bấm là tải về máy' : 'Kho Drive · ' + n + ' tiếng'}${k.hong ? ' · ' + k.hong + ' mục hỏng' : ''}</span></div>`;
}

/* ---------- tải 1 mục kho về máy (chạy nền ở máy chủ, trang hỏi tiến độ) ---------- */
function akTai(loai, x) {
  const f = x.kho; if (!f) return Promise.resolve(true);
  if (AK.tai[f]) return AK.tai[f].hua;
  const st = AK.tai[f] = {pt: 0, ten: x.ten};
  toast('Đang tải “' + x.ten + '” từ Kho effect về máy…');
  st.hua = (async () => {
    let lai = true;
    for (let i = 0; i < 2400; i++) {   // tối đa ~20 phút (Drive "chỉ trên mây", mạng chậm)
      let r; try { r = await api('/api/sua-tay/kho/chep?loai=' + loai + '&f=' + encodeURIComponent(f) + (lai ? '&lai=1' : '')); } catch (e) { r = {tt: 'loi', loi: e.message}; }
      lai = false; st.pt = r.pt || 0; akVeTai(f);
      if (r.tt === 'xong') { AK.may[x.p] = true; x.may = true; delete AK.tai[f]; akVeTai(f); toast('Đã tải “' + x.ten + '” về máy'); return true; }
      if (r.tt === 'loi' || r.tt === 'khong_co') { delete AK.tai[f]; akVeTai(f); toast('Không tải được “' + x.ten + '”: ' + (r.loi || 'lỗi') + '. Bấm lại để thử lại.', true); return false; }
      await new Promise(z => setTimeout(z, i < 10 ? 200 : 500));
    }
    delete AK.tai[f]; akVeTai(f); toast('Tải “' + x.ten + '” quá lâu: kiểm tra Drive / mạng rồi bấm lại', true); return false;
  })();
  akVeTai(f); return st.hua;
}
function akVeTai(f) {
  $$(`[data-ak-f="${CSS.escape(f)}"]`).forEach(b => { const st = AK.tai[f]; b.classList.toggle('dang', !!st); b.textContent = st ? st.pt + '%' : '☁';
    if (!st && AK.may[b.dataset.akP]) b.remove(); });
}
const akNhan = x => `<span class="ak-may" data-ak-f="${esc(x.kho)}" data-ak-p="${esc(x.p)}" data-tip="Ở Kho effect (Drive), chưa có trên máy này: bấm là tải về (${Math.max(1, Math.round((x.kb || 0) / 1024 * 10) / 10)} MB) rồi dùng">${AK.tai[x.kho] ? AK.tai[x.kho].pt + '%' : '☁'}</span>`;

/* ---------- chỗ cắt cảnh + hít "chạm" của tiếng vào chỗ cắt ---------- */
function akCat() { return S.plan ? bocCanh().slice(1).map(b => b.bd) : []; }
function akHit(x, t) {   // t = giây con trỏ (đầu tiếng nếu thả tự do) -> {c: chỗ cắt, t: giây đầu tiếng để "chạm" rơi đúng c} | null
  if (AK.alt || !x || t == null) return null;
  const d = +x.dinh || 0, thr = Math.max(0.25, 12 / (S.pps || 50)); let best = null;
  akCat().forEach(c => { const k = Math.min(Math.abs(t - c), Math.abs(t + d - c)); if (k <= thr && (!best || k < best.k)) best = {k, c}; });
  return best ? {c: best.c, t: r3(Math.max(0, best.c - d))} : null;
}
function akIns(ev) {   // đang kéo tiếng: vạch vàng đặt ở chỗ cắt sẽ hít vào (sau khi _mod-thu-vien-them vẽ vạch đầu tiếng)
  const v = $('#amIns'), gh = $('.tv-bong'); if (!AK.keoX) return;
  const T = (S.view || {}).T || tongT(), tt = clamp(tTuX(ev.clientX), 0, Math.max(0, T - 0.05)), h = v ? akHit(AK.keoX, tt) : null;
  if (v) v.classList.toggle('ak-hit', !!h);
  if (v && h) v.style.left = (h.c * S.pps - 1) + 'px';
  const sm = gh && $('small', gh); if (sm && v) sm.textContent = h ? 'chạm đúng chỗ cắt ' + tg(h.c) + ' · giữ Alt: thả tự do' : 'thả để thêm lúc ' + tg(tt);
}

/* ---------- Tự gắn tiếng chuyển cảnh: mỗi chỗ cắt chưa có tiếng -> 1 whoosh (đổi luân phiên), 1 bước Ctrl+Z ---------- */
function akTuGan() {
  if (!S.plan || !TVT.am) return;
  const cuts = akCat();
  if (!cuts.length) return toast('Video chỉ có 1 cảnh: chưa có chỗ cắt để gắn tiếng');
  const ds = TVT.am.ds, xoay = ['vut-vua.wav', 'quat-gio.wav', 'vut-manh.wav'].map(f => ds.find(x => base(x.p) === f)).filter(Boolean);
  if (!xoay.length) return toast('Không thấy tiếng vút kèm app', true);
  const coGiong = !!(S.plan.giong || (S.plan.phu_de || []).length), cu = amDs(), moi = [];
  cuts.forEach((c, i) => {
    if (cu.some(y => { const g = amTim(y.local); return Math.abs(y.t + ((g && +g.dinh) || 0) - c) < 0.2; })) return;   // chỗ cắt đã có tiếng
    const x = xoay[i % xoay.length], o = {ma: ma('a'), local: x.p, file: x.p, ten: x.ten, t: r3(Math.max(0, c - (+x.dinh || 0)))};
    if (coGiong) o.am_luong = 0.7;
    moi.push(o);
  });
  if (!moi.length) return toast('Mọi chỗ cắt đã có tiếng chuyển cảnh');
  doi(p => { p.am_thanh = (Array.isArray(p.am_thanh) ? p.am_thanh : []).concat(moi).sort((a, b) => a.t - b.t).slice(0, 200); });
  toast('Đã gắn ' + moi.length + ' tiếng chuyển cảnh vào ' + moi.length + ' chỗ cắt' + (coGiong ? ' (70% vì video có giọng)' : '') + ' · Ctrl+Z bỏ cả loạt');
  if (S.tv.tab === 'am') veTV(true);
}

/* ---------- vẽ thêm vào tab Âm thanh: 7 nhóm, đồng nghĩa, Hay dùng, Tự gắn, ☁ ---------- */
function akSauVeAm(el) {
  if (!el || !TVT.am) return;
  $$('.am-bai[data-am-p]', el).forEach(b => {
    const x = amTim(b.dataset.amP); if (!x) return;
    const ten = boDau(x.ten);
    b.dataset.tvlTen = boDau(x.ten + ' ' + x.mo_ta) + ' ' + (AK_DN_NHOM[x.nhom] || '') + ' ' + AK_DN_TEN.filter(([r]) => r.test(ten)).map(z => z[1]).join(' ');
    if (akChuaVe(x) && !$('.ak-may', b)) { const t = $('.am-t b', b), w = document.createElement('span'); w.className = 'ak-dong'; t.before(w); w.append(t); w.insertAdjacentHTML('beforeend', akNhan(x)); }
  });
  const NGAN = {chuyen: 'Chuyển', nhan: 'Nhấn', may: 'Máy', tien: 'Giá'};   // chip nhóm gọn (thư viện hẹp 1366): 2 hàng thay vì 3, tên đủ vào data-tip
  $$('.tvl[data-tvl="am"] [data-tvl-m]', el).forEach(c => { const k = c.dataset.tvlM, t = NGAN[k]; if (t && c.firstChild && c.firstChild.nodeType === 3) { c.dataset.tip = (AK_NHOM.find(z => z[0] === k) || [])[1] || ''; c.firstChild.textContent = t; } });
  const thanh = $('.tvl[data-tvl="am"]', el);
  if (thanh && !$('.ak-dau', el)) {
    const h = akHay(), top = Object.entries(h).filter(([p, n]) => n > 0 && amTim(p)).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([p]) => p);
    let s = `<div class="ak-dau"><button type="button" class="btn small" data-ak-a="tu-gan" data-tip="Mỗi chỗ cắt cảnh chưa có tiếng: thêm 1 tiếng vút (đổi luân phiên Vút vừa / Quất gió / Vút mạnh), chỗ 'chạm' đúng chỗ cắt. Video có giọng thì để 70%. Ctrl+Z bỏ cả loạt.">${icon('amThanh')}Tự gắn tiếng chuyển cảnh</button>${akHangKho('am')}</div>`;
    thanh.insertAdjacentHTML('beforebegin', s);
    if (top.length) {
      const o = $$('.tvl-sec .am-bai[data-am-p]', el).filter(b => top.includes(b.dataset.amP)).sort((a, b) => top.indexOf(a.dataset.amP) - top.indexOf(b.dataset.amP));
      const sec = document.createElement('div'); sec.className = 'tvl-sec ak-hay'; sec.dataset.tvlSec = 'hay';
      sec.innerHTML = `<div class="tvl-h">Hay dùng<span>${o.length}</span></div><div class="am-ds"></div>`;
      o.forEach(b => sec.lastChild.append(b.cloneNode(true)));
      const s1 = $('.tvl-sec', el); if (s1) s1.before(sec);
    }
  }
  tvApLoc('am', $('#libPane'));
}
$('#libPane').addEventListener('click', e => { const b = e.target.closest('[data-ak-a="tu-gan"]'); if (b) { e.stopPropagation(); akTuGan(); } });
$('#libPane').addEventListener('pointerdown', e => { const b = e.target.closest && e.target.closest('#tvAm .am-bai[data-am-p]'); AK.keoX = b && typeof amTim === 'function' ? amTim(b.dataset.amP) : null; }, true);
addEventListener('pointermove', e => { AK.alt = e.altKey; if (AK.keoX && document.body.classList.contains('tv-dang-keo')) requestAnimationFrame(() => akIns(e)); });
addEventListener('pointerup', e => { AK.alt = e.altKey; setTimeout(() => { AK.keoX = null; }, 0); });
addEventListener('keydown', e => { if (e.key === 'Alt') AK.alt = true; }, true);
addEventListener('keyup', e => { if (e.key === 'Alt') AK.alt = false; }, true);

/* ---------- nhạc: ☁ + vạch drop + đặt drop vào cảnh ---------- */
function akBaiDang() { const n = S.plan && S.plan.nhac; if (!n || !n.local || typeof timBai !== 'function') return null; return timBai(n.local) || null; }
function akDatDrop() {
  const n = S.plan && S.plan.nhac, x = akBaiDang(); if (!n || !x) return;
  const dr = (x.drop || []).filter(v => v > 0.5); if (!dr.length) return toast('Bài này không có chỗ drop rõ', true);
  const b = bocCanh(), c = b.find(z => z.c._id === S.sel.canh) || b.find(z => S.t >= z.bd && S.t < z.b) || b[0]; if (!c) return;
  const d = dr.find(v => v >= c.bd); if (d == null) return toast('Cảnh này muộn hơn mọi chỗ drop của bài: chọn cảnh sớm hơn', true);
  datNhac({tu: r3(d - c.bd)}, 'Drop của “' + (n.ten || x.ten) + '” rơi đúng đầu cảnh ' + (c.i + 1) + ' (' + tg(c.bd) + '), bài phát từ ' + tg(d - c.bd));
}
function akVeDrop(T, pps) {
  const bar = $('#tNhac .bar.nhac:not(.trong)'), n = S.plan && S.plan.nhac, x = akBaiDang(); if (!bar || !n || !x || !(x.drop || []).length) return;
  const tu = nhSo(n.tu, 0);
  bar.insertAdjacentHTML('beforeend', x.drop.map(d => d - tu).filter(t => t > 0.05 && t < T - 0.05).map(t => `<i class="ak-drop" style="left:${t * pps}px" title="Drop của bài lúc ${tg(t)}"></i>`).join(''));
}

/* ---------- bọc hàm của _mod-thu-vien-them / _mod-nhac (sau khi cả trang nạp xong) ---------- */
function akKhoi() {
  if (typeof AM_NHOM !== 'undefined') AM_NHOM.splice(0, AM_NHOM.length, ...AK_NHOM);
  if (typeof veAmTV === 'function') { const g = veAmTV; veAmTV = function (el) { g(el); akSauVeAm(el); }; }
  if (typeof themAm === 'function') {
    const g = themAm;
    themAm = function (x, t) {
      if (!x) return;
      const y = amTim(x.p) || x;
      if (akChuaVe(y)) { akTai('am_thanh', y).then(ok => { if (ok) themAm(x, t); }); return; }
      let h = null; if (t != null && S.tv.keoTha && AK.keoX) { h = akHit(y, t); if (h) t = h.t; }
      akDem(x.p); g(x, t);
      if (h) toast('Đã thêm “' + x.ten + '”: chỗ chạm rơi đúng chỗ cắt ' + tg(h.c) + ' (thả kèm Alt = đặt tự do · Ctrl+Z để bỏ)');
    };
  }
  if (typeof amNghe === 'function') { const g = amNghe; amNghe = function (p, vol) { const y = amTim(p); if (akChuaVe(y)) { akTai('am_thanh', y).then(ok => { if (ok) g(p, vol); }); return; } return g(p, vol); }; }
  if (typeof nhThem === 'function') { const g = nhThem; nhThem = function (x) { if (akChuaVe(x)) { akTai('nhac', x).then(ok => { if (ok) { g(Object.assign({}, x, {may: true})); veNH(); } }); return; } return g(x); }; }
  if (typeof nhNghe === 'function') { const g = nhNghe; nhNghe = function (p, tu) { const x = timBai(p); if (akChuaVe(x)) { akTai('nhac', x).then(ok => { if (ok) { veNH(); g(p, tu); } }); return; } return g(p, tu); }; }
  if (typeof dongBai === 'function') { const g = dongBai; dongBai = function (x, n) { const h = g(x, n); return akChuaVe(x) ? h.replace(/(<span class="nh-t">)(<b>[^<]*<\/b>)/, '$1<span class="ak-dong">$2' + akNhan(x) + '</span>') : h; }; }
  if (typeof veNH === 'function') {
    const g = veNH;
    veNH = function () {
      g(); const el = NH.el; if (!el || !el.isConnected) return;
      $$('.tv-h span', el).forEach(s => { if (s.textContent === 'tự tạo · CC0, không bản quyền') s.textContent = 'CC0, không bản quyền'; });
      const mp = $$('.tv-h', el).find(h => /Nhạc miễn phí/.test(h.textContent)); if (mp && !$('.ak-kho', el)) mp.insertAdjacentHTML('afterend', akHangKho('nhac'));
      const nd = $('.nh-dang-n', el), x = akBaiDang();
      if (nd && x && (x.drop || []).some(v => v > 0.5) && !$('[data-ak-a="drop"]', nd))
        nd.insertAdjacentHTML('afterbegin', `<button type="button" class="btn small" data-ak-a="drop" data-tip="Dời chỗ bắt đầu bài để chỗ drop (nhạc bùng lên) rơi đúng đầu cảnh đang chọn — cắt cảnh khớp nhạc">Drop vào cảnh</button>`);
    };
    $('#libPane').addEventListener('click', e => { const b = e.target.closest('[data-ak-a="drop"]'); if (b) { e.stopPropagation(); akDatDrop(); } }, true);
  }
  if (typeof menuNhac === 'function') {
    const g = menuNhac;
    menuNhac = function () { const m = g(), x = akBaiDang(); if (x && (x.drop || []).some(v => v > 0.5)) m.splice(2, 0, {t: 'Đặt drop vào cảnh đang chọn', ic: 'nhac', f: akDatDrop}); return m; };
  }
  if (typeof veLanNhac === 'function') { const g = veLanNhac; veLanNhac = function (top, T, pps) { const h = g(top, T, pps); try { akVeDrop(T, pps); } catch (e) {} return h; }; }
  akTaiKho().then(() => { if (S.tv && S.tv.tab === 'am' && typeof veTV === 'function') veTV(true); if (typeof veNH === 'function') veNH(); });
  setInterval(() => { if (!document.hidden && S.plan) akTaiKho(); }, 60000);
}
setTimeout(akKhoi, 0);
