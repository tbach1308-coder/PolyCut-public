/* ============================== HÌNH (4/11/2026): TỰ CHIA CẢNH · TỰ CHỈNH MÀU · BỘ LỌC MÀU ==============================
   Chủ tiệm duyệt 4/11 10:4x (bài "CapCut cho người mới"). Máy chủ: hinh.py (+ hinh_may.py chạy bằng Python của bộ dựng).
   1) TỰ CHIA CẢNH: nút "Tự chia" trên thanh timeline / chuột phải cảnh -> cảnh đang chọn hoặc cả video. Máy chủ tìm chỗ ngừng nói
      (khoảng lặng giữa 2 chữ, mép cắt chừa ≥ 0,12s, KHÔNG cắt giữa chữ) + chỗ đổi góc máy; mỗi cảnh con ≥ 0,8s. Trang hiện vạch trên
      làn cảnh (bấm vạch = bỏ / lấy lại) + thanh nổi "Chia" / "Thôi". Chia = các thao tác chia_canh sẵn có (apOps) trong 1 lần doi() =
      1 bước Ctrl+Z. Tuỳ chọn (mặc định bật): đoạn im lặng dài tách thành cảnh riêng, đánh dấu sọc xám "Im lặng" (canh._im, chỉ khi
      đang sửa) + nút "Xoá N đoạn im lặng" anh tự bấm. Không tự xoá.
   2) TỰ CHỈNH MÀU: tab Cảnh › Màu, "Cảnh này" / "Mọi cảnh" -> máy chủ đo 5 khung -> canh.mau (thanh kéo nhảy theo), 1 bước Ctrl+Z.
      "Mọi cảnh": các cảnh vừa chia liền nhau của cùng clip đo chung, nhận cùng 1 màu (bản xuất vẫn nối liền như 1 cảnh).
      Nút "Giữ để xem bản gốc": giữ chuột là khung xem bỏ màu riêng của cảnh, thả ra là hiện lại.
   3) BỘ LỌC MÀU: canh.loc {ten, muc 0–1} (bộ dựng: lut3d ngay sau màu riêng cảnh; muc < 1 = trộn với hình gốc). Chọn ở tab Cảnh › Màu
      hoặc Thư viện › Hiệu ứng (nhóm "Bộ lọc"). Ô chọn = ẢNH máy chủ dựng ĐÚNG bộ lọc trên khung của cảnh (GET /api/sua-tay/hinh/anh-loc).
      Khung xem = lọc SVG GẦN ĐÚNG: đường cong từng kênh (9 nút) + ma trận màu khớp từ LUT, lệch trung bình ~1/255 (p99 < 5/255) trên ảnh
      thử (dev/thu-sua-tay/xap_xi_lut.py tạo số HINH_LOC). "Xem mẫu thật" = dựng 3 giây đúng như bản xuất (xemMau).
   Móc nối ở file chung (vài dòng): _canh-tt.js (ttDoan / hinhVideo / bảng Màu / dấu khối cảnh), _thu-vien.js (tvHieu, khoaTV),
   _sua-tay.src.html (menuCanh). */
const HINH_LOC = [   // 4 LUT trong engine/luts (bo-loc.json), CC0 Poly tự tạo 3/11; bang/mt = xấp xỉ cho khung xem trình duyệt
  {v: 'poly_san_pham', ten: 'Sản phẩm', mo_ta: 'Tăng nhẹ tương phản và độ tươi, máy nổi khối hơn',
   bang: [[0.0273,0.1205,0.2355,0.3599,0.4935,0.6324,0.7622,0.8761,0.954],[0.0245,0.1225,0.2393,0.3643,0.499,0.6369,0.7658,0.8785,0.9711],[0.0254,0.1198,0.2378,0.3638,0.5006,0.6404,0.7697,0.8859,0.9626]],
   mt: '1.1630 -0.0856 -0.0261 0.0000 -0.0239 -0.0105 1.0836 -0.0260 0.0000 -0.0264 -0.0098 -0.0797 1.1305 0.0000 -0.0251 0.0000 0.0000 0.0000 1.0000 0.0000'},
  {v: 'poly_trang_sach', ten: 'Trắng sạch', mo_ta: 'Sáng hơn, hơi mát: nền trắng sạch, hợp máy màu bạc / trắng',
   bang: [[-0.0086,0.1248,0.2524,0.3773,0.5022,0.6279,0.7501,0.8794,0.9663],[-0.0086,0.1254,0.2516,0.3784,0.5014,0.6275,0.748,0.8801,0.9653],[-0.0051,0.1263,0.2506,0.3767,0.5017,0.6278,0.7492,0.8795,0.9713]],
   mt: '0.9824 0.0198 0.0049 0.0000 0.0170 0.0115 0.9878 0.0044 0.0000 0.0178 0.0133 0.0193 1.0013 0.0000 0.0211 0.0000 0.0000 0.0000 1.0000 0.0000'},
  {v: 'poly_am_ap', ten: 'Ấm áp', mo_ta: 'Hơi ấm, dịu mắt: hợp clip nói chuyện, mở hộp',
   bang: [[0.0083,0.1213,0.2497,0.374,0.4993,0.6251,0.7497,0.8765,1.0003],[0.0007,0.1243,0.2502,0.3751,0.5001,0.6251,0.7489,0.8758,1.0008],[0.0096,0.1186,0.2487,0.3739,0.4992,0.6261,0.7498,0.8796,1.0054]],
   mt: '1.0248 -0.0220 -0.0034 0.0000 -0.0107 -0.0129 0.9783 -0.0032 0.0000 0.0020 -0.0150 -0.0187 0.9544 0.0000 -0.0126 0.0000 0.0000 0.0000 1.0000 0.0000'},
  {v: 'poly_luc_bao', ten: 'Lục bảo Poly', mo_ta: 'Tối ngả xanh lục bảo, sáng hơi vàng: rất nhẹ, hợp màu kênh',
   bang: [[0.0184,0.1132,0.2427,0.3702,0.5042,0.6373,0.755,0.8671,0.968],[0.0197,0.1222,0.2356,0.3722,0.503,0.6353,0.7569,0.874,0.9794],[0.0174,0.1233,0.2411,0.3687,0.4949,0.6348,0.7628,0.8805,0.9925]],
   mt: '1.0500 0.0103 0.0112 0.0000 -0.0262 0.0017 1.0334 0.0006 0.0000 -0.0112 -0.0206 -0.0095 1.0193 0.0000 -0.0167 0.0000 0.0000 0.0000 1.0000 0.0000'}];
IC_P.tuChia = '<path d="M4 6h5M15 6h5M4 18h5M15 18h5"/><path d="M12 3v18" stroke-dasharray="2 2.6"/><path d="M8 10l-2 2 2 2M16 10l2 2-2 2"/>';
IC_P.tuMau = '<path d="M12 21a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5S12.5 4.5 12 2c-.5 2.5-2 4.9-4 6.5C6 10.1 5 12 5 14a7 7 0 0 0 7 7z"/><path d="M19.5 2.5l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z" fill="currentColor"/>';
IC_P.soGoc = '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17"/><path d="M12 3.5a8.5 8.5 0 0 1 0 17z" fill="currentColor" stroke="none"/>';
IC_P.locMau = '<circle cx="9" cy="9" r="5.5"/><circle cx="15" cy="9" r="5.5"/><circle cx="12" cy="15" r="5.5"/>';
S.hinh = {chia: null, dx: null, mau: null, tachIm: true, xongChia: false};
try { S.hinh.tachIm = localStorage.getItem('st-hinh-tach-im') !== '0'; } catch (e) {}
const hinhNgu = ms => new Promise(r => setTimeout(r, ms));
const hinhPct = m => Math.round(m * 100) + '%';
const hinhTen = v => (HINH_LOC.find(x => x.v === v) || {}).ten || v;

/* ---------- bộ lọc: đọc khoá, lọc SVG gần đúng cho khung xem ---------- */
function locC(c) {   // -> {ten, muc} | null
  const l = c && c.loc; if (!l || typeof l !== 'object' || !HINH_LOC.some(x => x.v === l.ten)) return null;
  return {ten: l.ten, muc: clamp(so_(l.muc, 1), 0, 1)};
}
document.body.insertAdjacentHTML('beforeend', '<svg class="tv-svg" width="0" height="0" aria-hidden="true" focusable="false">' + HINH_LOC.map(x =>
  `<filter id="stLoc-${x.v}" color-interpolation-filters="sRGB" x="0" y="0" width="1" height="1"><feComponentTransfer in="SourceGraphic" result="c">${['R', 'G', 'B'].map((k, i) =>
    `<feFunc${k} type="table" tableValues="${x.bang[i].join(' ')}"/>`).join('')}</feComponentTransfer><feColorMatrix in="c" type="matrix" values="${x.mt}" result="l"/>`
  + `<feComposite in="SourceGraphic" in2="l" operator="arithmetic" k1="0" k2="0" k3="1" k4="0"/></filter>`).join('') + '</svg>');
const locMuc = {};
function locLut(l) {   // hinhVideo (_canh-tt.js) gọi: chuỗi CSS filter của bộ lọc (gần đúng) ở cường độ l.muc
  if (!l) return '';
  const m = Math.round(l.muc * 100) / 100;
  if (locMuc[l.ten] !== m) { locMuc[l.ten] = m; const f = document.querySelector(`#stLoc-${l.ten} feComposite`); if (f) { f.setAttribute('k2', (1 - m).toFixed(2)); f.setAttribute('k3', m.toFixed(2)); } }
  return m > 0.005 ? `url(#stLoc-${l.ten})` : '';
}
function anhLoc(c, ten, t) {   // ảnh khung cảnh qua màu riêng + bộ lọc THẬT (máy chủ dựng bằng ffmpeg)
  const m = mauC(c), mau = mauMd(m) ? '' : [m.sang, m.tuong_phan, m.bao_hoa, m.nhiet].join(',');
  if (!ten && !mau) return thumbUrl(src(c.file), t);
  return '/api/sua-tay/hinh/anh-loc?p=' + encodeURIComponent(src(c.file)) + '&t=' + (Math.round((t ?? (c.tu + c.den) / 2) * 10) / 10) + (ten ? '&loc=' + ten : '') + (mau ? '&mau=' + mau : '');
}
function datLoc(id, ten, tatCa) {   // ten null = bỏ bộ lọc; giữ cường độ đang dùng khi đổi sang bộ lọc khác
  const i = S.plan.canh.findIndex(c => c._id === id); if (i < 0) return;
  const cu = locC(S.plan.canh[i]), gt = ten ? {ten, muc: cu ? r2(cu.muc) : 1} : null;
  S.tam = null;
  doi(p => p.canh.forEach(c => { if (tatCa || c._id === id) { if (gt) c.loc = {...gt}; else delete c.loc; } }));
  if (!tatCa) vaoCanh(id);
  toast('Bộ lọc ' + (tatCa ? 'mọi cảnh' : 'cảnh ' + (i + 1)) + ': ' + (ten ? hinhTen(ten) : 'không') + ' (Ctrl+Z để bỏ)');
}
function xemLocThat(id) {   // dựng 3 giây đúng như bản xuất (đường xem mẫu của tab Kiểu)
  const i = S.plan.canh.findIndex(c => c._id === id), l = locC(S.plan.canh[i]); if (i < 0) return;
  xemMau('loc', {i, dau: true, nhan: 'Cảnh ' + (i + 1) + ' · ' + (l ? hinhTen(l.ten) + ' ' + hinhPct(l.muc) : 'không bộ lọc') + ' · bản dựng thật'});
}

/* ---------- tab Cảnh › Màu: ô Tự chỉnh màu (trên) + ô Bộ lọc (dưới) — _canh-tt.js benCanh gọi ---------- */
function hinhTuMau(c) {
  const M = S.hinh.mau, n = S.plan.canh.length, coMau = c.mau && !mauMd(mauC(c));
  return `<div class="box tt-box hinh-tu"><div class="row"><h2 class="sec grow">${icon('tuMau')}Tự chỉnh màu</h2>
      ${coMau ? `<button type="button" class="btn small ghost" data-hinh-a="so-goc" aria-label="Giữ để xem bản gốc" data-tip="Giữ chuột để xem cảnh khi chưa chỉnh màu, thả ra là xem lại bản đã chỉnh">${icon('soGoc')}Giữ xem gốc</button>` : ''}</div>
    <p class="note">Máy đo màu clip rồi tự cân: đèn vàng về trắng hơn, cảnh tối sáng lên, giữ màu máy thật. Xong vẫn kéo thanh bên dưới được, Ctrl+Z để bỏ.</p>
    ${M && M.dang ? `<div class="ngtt"><span class="dot"></span><span class="ngtt-t">${esc(M.buoc || 'Đang đo màu…')}</span><button type="button" class="btn small ghost" data-hinh-a="mau-dung" data-tip="Thôi chờ (không đổi màu)">Thôi</button></div>`
      : `<div class="hinh-nut"><button type="button" class="btn small primary" data-hinh-a="mau-1" data-tip="Đo màu cảnh đang chọn rồi tự chỉnh (1 bước Ctrl+Z)">${icon('tuMau')}Cảnh này</button><button type="button" class="btn small" data-hinh-a="mau-het" ${n > 1 ? '' : 'disabled'} data-tip="Tự chỉnh từng cảnh của video; cảnh vừa chia liền nhau nhận chung 1 màu">${icon('lop')}Mọi cảnh (${n})</button></div>`}</div>`;
}
function hinhLocBox(c) {
  const l = locC(c), t = (c.tu + c.den) / 2;
  const o = (v, ten, goi) => `<button type="button" class="tvx hinh-lo${(l ? l.ten : '') === v ? ' on' : ''}" data-hinh-loc="${v}" data-tip="${esc(goi)}">
      <span class="xv"><i class="xb" style="background-image:url('${anhLoc(c, v, t)}')"></i>${(l ? l.ten : '') === v ? `<span class="tick">${icon('dauTick')}</span>` : ''}</span><span class="tvx-ten">${esc(ten)}</span></button>`;
  let h = `<div class="box tt-box hinh-loc-box"><div class="row"><h2 class="sec grow">${icon('locMau')}Bộ lọc màu</h2><span class="note">${l ? esc(hinhTen(l.ten)) + ' · ' + hinhPct(l.muc) : 'không có'}</span></div>
    <div class="tv-grid hinh-lo-grid">${o('', 'Không', 'Không dùng bộ lọc')}${HINH_LOC.map(x => o(x.v, x.ten, x.ten + ': ' + x.mo_ta)).join('')}</div>`;
  if (l) {
    const v = Math.round(l.muc * 100), d = {min: 0, max: 100};
    h += `<div class="tt-h"><label for="hinh-muc">Cường độ</label><input type="range" id="hinh-muc" class="tt-r" data-hinh-muc="1" min="0" max="100" step="1" value="${v}" style="${ttDai(d, v)}">
        <output id="hinhMucRa">${v}%</output><button type="button" class="btn small icon ghost tt-lai" data-hinh-a="muc-lai" ${v === 100 ? 'disabled' : ''} aria-label="Cường độ: về 100%" data-tip="Về 100%">${icon('datLai')}</button></div>
      <div class="hinh-nut"><button type="button" class="btn small" data-hinh-a="loc-het" data-tip="Dùng bộ lọc này, cùng cường độ, cho mọi cảnh">${icon('lop')}Áp cho mọi cảnh</button><button type="button" class="btn small" data-hinh-a="loc-that" data-tip="Dựng thử 3 giây đúng như bản xuất (khoảng 20–40 giây)">${icon('play')}Xem mẫu thật</button></div>`;
  }
  return h + `<p class="note">Ô ảnh và bản xuất: đúng bộ lọc. Khung xem bên trái: màu bộ lọc <b>gần đúng</b> (trình duyệt giả lập), muốn chắc thì bấm Xem mẫu thật.</p></div>`;
}
$('#pane').addEventListener('click', e => {
  const t = e.target.closest('button'); if (!t || t.disabled || !S.plan) return;
  const c = canhDangChon(); if (!c) return;
  if (t.dataset.hinhLoc != null) return datLoc(c._id, t.dataset.hinhLoc || null);
  const a = t.dataset.hinhA; if (!a) return;
  if (a === 'mau-1') return tuMau([c._id]);
  if (a === 'mau-het') return tuMau(null);
  if (a === 'mau-dung') { S.hinh.mau = null; return veBen(true); }
  if (a === 'loc-het') { const l = locC(c); if (l) { S.tam = null; doi(p => p.canh.forEach(y => { y.loc = {ten: l.ten, muc: r2(l.muc)}; })); toast('Bộ lọc mọi cảnh: ' + hinhTen(l.ten) + ' ' + hinhPct(l.muc) + ' (Ctrl+Z để bỏ)'); } return; }
  if (a === 'loc-that') return xemLocThat(c._id);
  if (a === 'muc-lai') { const l = locC(c); if (l) { vaoCanh(c._id); datTT(c._id, 'loc', {ten: l.ten, muc: 1}); } }
});
// thanh Cường độ: kéo = khung xem đổi ngay (S.tam), thả = 1 bước Ctrl+Z (datTT của _canh-tt.js)
$('#pane').addEventListener('pointerdown', e => { const r = e.target.closest('input[data-hinh-muc]'); if (r) vaoCanh(canhDangChon()._id); });
$('#pane').addEventListener('input', e => {
  const r = e.target.closest && e.target.closest('input[data-hinh-muc]'); if (!r) return;
  const c = canhDangChon(), l = locC(c); if (!l) return;
  const v = +r.value; r.style.cssText = ttDai({min: 0, max: 100}, v); const o = $('#hinhMucRa'); if (o) o.textContent = v + '%';
  S.tam = {id: c._id, khoa: 'loc', gt: {ten: l.ten, muc: r2(v / 100)}};
  if (!S.playing) veKhung(true);
});
$('#pane').addEventListener('change', e => {
  const r = e.target.closest && e.target.closest('input[data-hinh-muc]'); if (!r) return;
  const c = canhDangChon(), l = locC(c); if (!l) return;
  datTT(c._id, 'loc', {ten: l.ten, muc: r2(+r.value / 100)});
});
$('#pane').addEventListener('keydown', e => { if (e.target.closest && e.target.closest('input[data-hinh-muc]') && /^(Arrow|Page|Home|End)/.test(e.key)) e.stopPropagation(); });
// giữ để xem bản gốc (bỏ màu riêng cảnh trong lúc giữ)
$('#pane').addEventListener('pointerdown', e => {
  const b = e.target.closest('[data-hinh-a="so-goc"]'); if (!b) return;
  const c = canhDangChon(); vaoCanh(c._id); S.tam = {id: c._id, khoa: 'mau', gt: null}; b.classList.add('dang'); if (!S.playing) veKhung(true);
  const tha = () => { removeEventListener('pointerup', tha); removeEventListener('pointercancel', tha); b.classList.remove('dang');
    if (S.tam && S.tam.khoa === 'mau' && S.tam.gt === null) { S.tam = null; if (!S.playing) veKhung(true); } };
  addEventListener('pointerup', tha); addEventListener('pointercancel', tha);
});

/* ---------- Tự chỉnh màu ---------- */
function nhomMau(ids) {   // cảnh vừa chia (_tach) liền nhau của cùng clip -> 1 nhóm đo chung
  const out = [];
  S.plan.canh.forEach((c, i) => {
    if (ids && !ids.includes(c._id)) return;
    const tr = i ? S.plan.canh[i - 1] : null, g = out[out.length - 1];
    if (!ids && g && tr && c._tach && c.file === tr.file && Math.abs(c.tu - tr.den) < 0.005 && g.ids[g.ids.length - 1] === tr._id) g.ids.push(c._id);
    else out.push({ids: [c._id]});
  });
  return out;
}
async function tuMau(ids) {
  if (S.hinh.mau && S.hinh.mau.dang) return toast('Đang đo màu, chờ chút');
  const nhom = nhomMau(ids), M = S.hinh.mau = {dang: true, buoc: 'Đang đo màu…', ids};
  veBen(true);
  try {
    let r = await api('/api/sua-tay/hinh/mau', {v: S.v, plan: S.plan, nhom});
    const ma = M.ma = r.ma;
    while (r.dang) { await hinhNgu(500); if (S.hinh.mau !== M) return; r = await api('/api/sua-tay/hinh/mau?ma=' + ma);
      if (r.buoc && r.buoc !== M.buoc) { M.buoc = r.buoc; if (S.tab === 'canh' && S.tabCanh === 'mau') { const x = $('#pane .hinh-tu .ngtt-t'); if (x) x.textContent = r.buoc; } } }
    if (S.hinh.mau !== M) return;
    S.hinh.mau = null;
    if (r.loi || !r.kq) throw new Error(r.loi || 'Không đo được màu');
    const ds = r.kq.canh || [];
    let doiN = 0, onN = 0, loiN = 0;
    const gan = {};
    ds.forEach(x => (x.ids || [x.id]).forEach(id => { gan[id] = x; if (x.loi) loiN++; else if (x.mau) doiN++; else onN++; }));
    if (!doiN && !S.plan.canh.some(c => gan[c._id] && !gan[c._id].loi && c.mau)) { veBen(true); return toast(loiN ? 'Không đo được màu cảnh này' : 'Màu ' + (ids ? 'cảnh này' : 'các cảnh') + ' đã ổn, không cần chỉnh', !!loiN); }
    S.tam = null;
    doi(p => p.canh.forEach(c => { const x = gan[c._id]; if (!x || x.loi) return; if (x.mau) c.mau = {...x.mau}; else delete c.mau; }));
    if (ids && ids.length === 1) vaoCanh(ids[0]);
    toast('Đã tự chỉnh màu ' + doiN + ' cảnh' + (onN ? ', ' + onN + ' cảnh màu đã ổn giữ nguyên' : '') + (loiN ? ', ' + loiN + ' cảnh không đo được' : '') + ' (Ctrl+Z để bỏ)');
  } catch (e) { if (S.hinh.mau === M) S.hinh.mau = null; veBen(true); toast('Tự chỉnh màu lỗi: ' + e.message, true); }
}

/* ---------- Thư viện › Hiệu ứng: nhóm "Bộ lọc" (_thu-vien.js tvHieu gọi) ---------- */
function tvHinhLoc(x) {
  const c = x.c, l = locC(c), t = (c.tu + c.den) / 2, n = x.i + 1;
  const o = (v, ten, goi) => { const on = (l ? l.ten : '') === v;
    return `<button type="button" class="tvx hinh-lo${on ? ' on' : ''}" data-tvloc="${v}" data-tip="${esc(goi)}"><span class="xv"><i class="xb" style="background-image:url('${anhLoc(c, v, t)}')"></i>${on ? `<span class="tick">${icon('dauTick')}</span>` : ''}${on && l && l.muc < 0.995 ? `<span class="tv-tag duoi">${hinhPct(l.muc)}</span>` : ''}<span class="tv-cong" aria-hidden="true">${icon('them')}</span></span><span class="tvx-ten">${esc(ten)}</span></button>`; };
  return tvTieuDe('Bộ lọc cảnh ' + n, l ? hinhTen(l.ten) + ' · ' + hinhPct(l.muc) : 'không có', 'Ảnh ô = đúng bộ lọc trên khung cảnh ' + n + '. Cường độ: tab Cảnh › Màu.')   // 4/11 tối: câu hướng dẫn vào dấu (i)
    + `<div class="tv-grid tv-hu">${o('', 'Không', 'Cảnh ' + n + ' không dùng bộ lọc')}${HINH_LOC.map(y => o(y.v, y.ten, y.ten + ': ' + y.mo_ta + ' · bấm để dùng cho cảnh ' + n)).join('')}</div>`
    + `<div class="tv-hang"><button type="button" class="btn small" data-tvloc-het="1" ${l ? '' : 'disabled'} data-tip="${l ? 'Dùng ' + esc(hinhTen(l.ten)) + ' ' + hinhPct(l.muc) + ' cho mọi cảnh' : 'Chọn 1 bộ lọc cho cảnh này trước'}">${icon('lop')}Áp cho mọi cảnh</button>
      <button type="button" class="btn small ghost" data-tvloc-bo="1" ${S.plan.canh.some(y => y.loc) ? '' : 'disabled'} data-tip="Bỏ bộ lọc của mọi cảnh">${icon('boHet')}Bỏ hết</button></div>`;
}
$('#lib').addEventListener('click', e => {
  const t = e.target.closest('button'); if (!t || t.disabled || !S.plan || S.tv.vuaKeo) return;
  const x = canhChon(); if (!x) return;
  if (t.dataset.tvloc != null) return datLoc(x.c._id, t.dataset.tvloc || null);
  if (t.dataset.tvlocHet) { const l = locC(x.c); if (l) { doi(p => p.canh.forEach(y => { y.loc = {ten: l.ten, muc: r2(l.muc)}; })); toast('Bộ lọc mọi cảnh: ' + hinhTen(l.ten) + ' (Ctrl+Z để bỏ)'); } return; }
  if (t.dataset.tvlocBo) { doi(p => p.canh.forEach(y => { delete y.loc; })); toast('Đã bỏ bộ lọc mọi cảnh (Ctrl+Z để lấy lại)'); }
});
$('#lib').addEventListener('contextmenu', e => {
  const t = e.target.closest('#libPane [data-tvloc]'); if (!t || !S.plan) return;
  e.preventDefault(); e.stopPropagation();
  const x = canhChon(), v = t.dataset.tvloc || null, n = x.i + 1;
  moMenu(e.clientX, e.clientY, [{nhom: 'Bộ lọc · ' + (v ? hinhTen(v) : 'Không')}, {t: 'Dùng cho cảnh ' + n, ic: 'locMau', f: () => datLoc(x.c._id, v)},
    {t: v ? 'Áp cho mọi cảnh' : 'Bỏ hết', ic: 'lop', f: () => datLoc(x.c._id, v, true)},
    v && {t: 'Xem mẫu thật (chưa áp)…', ic: 'play', f: () => xemMau('loc', {i: x.i, dau: true, sua: p => { p.canh[x.i].loc = {ten: v, muc: 1}; }, nhan: 'Thử: cảnh ' + n + ' · ' + hinhTen(v) + ' (chưa áp)'})}]);
});

/* ---------- Tự chia cảnh ---------- */
(() => {
  // gộp r15: theo quy ước thanh timeline (_icon.js ic()): màn hẹp chỉ biểu tượng + ô gợi ý khi rê chuột, màn ≥ 1500px có chữ cạnh biểu tượng
  const b = document.createElement('button'); b.type = 'button'; b.className = 'btn small ico co-chu'; b.id = 'bTuChia';
  b.dataset.tip = 'Tự chia cảnh dài theo chỗ ngừng nói / đổi góc máy (cảnh đang chọn hoặc cả video). Hiện vạch đề xuất trước, bấm Chia mới chia';
  b.setAttribute('aria-label', 'Tự chia cảnh');
  b.innerHTML = icon('tuChia') + '<span class="nut-chu">Tự chia</span>';
  const ch = $('#bChia'); if (ch) ch.after(b);
  b.addEventListener('click', () => { if (!S.plan) return; const r = b.getBoundingClientRect(); moMenu(r.left, r.bottom + 4, mucTuChia()); });
  const bar = document.createElement('div'); bar.id = 'hinhBar'; bar.className = 'hinh-bar'; bar.hidden = true; bar.setAttribute('role', 'status');
  const tl = $('#tl'); if (tl) tl.append(bar);
})();
function mucTuChia(id) {
  const x = id ? bocCanh().find(y => y.c._id === id) : canhChon(); if (!x) return [];
  const dai = x.c.den - x.c.tu, n = S.plan.canh.length, dang = S.hinh.chia && S.hinh.chia.dang;
  return [{nhom: 'Tự chia cảnh theo chỗ ngừng nói / đổi góc máy'},
    {t: 'Cảnh ' + (x.i + 1) + ' (đang chọn, ' + gs(dai) + ')', ic: 'tuChia', tat: dai < 1.6 || dang, ly_do: dang ? 'Đang tìm chỗ chia' : dai < 1.6 ? 'Cảnh ngắn quá (dưới 1,6 giây)' : '', f: () => tuChia([x.c._id])},
    !id && {t: 'Cả video (' + n + ' cảnh)', ic: 'lop', tat: dang, ly_do: dang ? 'Đang tìm chỗ chia' : '', f: () => tuChia(null)},
    '-', {t: 'Tách riêng đoạn im lặng dài', chon: S.hinh.tachIm, f: () => { S.hinh.tachIm = !S.hinh.tachIm; try { localStorage.setItem('st-hinh-tach-im', S.hinh.tachIm ? '1' : '0'); } catch (e) {}
      toast(S.hinh.tachIm ? 'Lần sau: đoạn im lặng dài tách thành cảnh riêng (sọc xám) để anh xoá nhanh' : 'Lần sau: không tách riêng đoạn im lặng'); }}];
}
function mucHinhCanh(id, i) {   // chuột phải cảnh (_sua-tay.src.html menuCanh gọi)
  const c = S.plan.canh[i], soIm = S.plan.canh.filter(laIm).length;
  const ngan = c.den - c.tu < 1.6, dang = !!(S.hinh.chia && S.hinh.chia.dang);
  return ['-', {nhom: 'Tự động'}, {t: 'Tự chia cảnh này', ic: 'tuChia', tat: ngan || dang, ly_do: ngan ? 'Cảnh ngắn quá (dưới 1,6 giây)' : dang ? 'Đang tìm chỗ chia' : '', f: () => tuChia([id])},
    {t: 'Tự chỉnh màu cảnh này', ic: 'tuMau', f: () => { if (S.tab !== 'canh' || S.tabCanh !== 'mau') { S.tab = 'canh'; S.tabCanh = 'mau'; veTabs(); } S.sel.canh = id; tuMau([id]); }},
    soIm && {t: 'Xoá ' + soIm + ' đoạn im lặng đã đánh dấu', ic: 'xoa', nguy: true, f: xoaIm}];
}
async function tuChia(ids) {
  S.hinh.dx = null; S.hinh.xongChia = false;
  const C = S.hinh.chia = {dang: true, buoc: 'Bắt đầu…', t0: Date.now(), ids};
  veHinh();
  const tic = setInterval(() => { if (S.hinh.chia === C) veBar(); else clearInterval(tic); }, 1000);
  try {
    let r = await api('/api/sua-tay/hinh/chia', {v: S.v, plan: S.plan, ids, tach_im: S.hinh.tachIm});
    const ma = C.ma = r.ma;
    while (r.dang) { await hinhNgu(600); if (S.hinh.chia !== C) return; r = await api('/api/sua-tay/hinh/chia?ma=' + ma); if (r.buoc) C.buoc = r.buoc; veBar(); }
    if (S.hinh.chia !== C) return;
    S.hinh.chia = null;
    if (r.loi || !r.kq) throw new Error(r.loi || 'Không tìm được chỗ chia');
    const ds = (r.kq.canh || []).filter(e => S.plan.canh.some(c => c._id === e.id));
    const so = ds.reduce((a, e) => a + e.cat.length, 0);
    if (!so) { veHinh(); return toast('Không thấy chỗ nào nên chia' + ((r.canh_bao || []).length ? ': ' + r.canh_bao[0] : ' (không có chỗ ngừng nói ≥ 0,3s hay đổi góc máy)'), !!(r.canh_bao || []).length); }
    S.hinh.dx = {canh: ds, canh_bao: r.canh_bao || [], giay: r.giay_da};
    veHinh();
    const x = bocCanh().find(y => y.c._id === ds[0].id); if (x && ids && ids.length === 1) { const sc = $('#tls'); if (x.a * S.pps < sc.scrollLeft || x.b * S.pps > sc.scrollLeft + sc.clientWidth) sc.scrollLeft = Math.max(0, x.a * S.pps - 40); }
  } catch (e) { if (S.hinh.chia === C) S.hinh.chia = null; veHinh(); toast('Tự chia cảnh lỗi: ' + e.message, true); }
}
function dxDem() {   // đếm đề xuất đang bật
  const d = {so: 0, lang: 0, goc: 0, im: 0, canh: 0}, cap = new Set();
  ((S.hinh.dx || {}).canh || []).forEach((e, i) => { const on = e.cat.filter(k => !k.bo); if (on.length) d.canh++;
    on.forEach(k => { d.so++; if (k.loai === 'im') cap.add(i + ':' + (k.cap || k.t)); else d[k.loai === 'goc' ? 'goc' : 'lang']++; }); });
  d.im = cap.size;   // số ĐOẠN im lặng (1 đoạn giữa câu = 2 vạch)
  return d;
}
function laIm(c) { const m = c && c._im; return Array.isArray(m) && c.tu >= m[0] - 0.05 && c.den <= m[1] + 0.05; }
function veBar() {
  const bar = $('#hinhBar'); if (!bar) return;
  const C = S.hinh.chia, D = S.hinh.dx, soIm = S.plan ? S.plan.canh.filter(laIm).length : 0;
  if (C && C.dang) {
    bar.hidden = false; bar.className = 'hinh-bar dang';
    bar.innerHTML = `<span class="dot"></span><span class="hb-t"><b>Tự chia cảnh</b> · ${esc(C.buoc || 'Đang tìm chỗ chia…')}</span><span class="tg">${Math.round((Date.now() - C.t0) / 1000)}s</span><button type="button" class="btn small ghost" data-hb="dung" data-tip="Thôi chờ, không chia">Thôi</button>`;
  } else if (D) {
    const d = dxDem(), bao = D.canh_bao || [], ct = [d.lang && d.lang + ' chỗ ngừng nói', d.goc && d.goc + ' chỗ đổi góc máy', d.im && d.im + ' đoạn im lặng'].filter(Boolean).join(' · ');
    bar.hidden = false; bar.className = 'hinh-bar dx';
    bar.innerHTML = `<span class="hb-t"><b>Đề xuất chia ${d.so} chỗ</b>${ct ? ' · ' + ct : ''}<small>Vạch vàng trên làn cảnh · bấm vạch để bỏ / lấy lại</small></span>`
      + (bao.length ? `<span class="hb-bao" data-tip="${esc(bao.join('\n'))}">${bao.length} chỗ không chia</span>` : '')
      + `<button type="button" class="btn small primary" data-hb="chia" ${d.so ? '' : 'disabled'} data-tip="Chia ở các vạch vàng đang bật (1 bước Ctrl+Z)">${icon('chia')}Chia${d.so ? ' ' + d.so + ' chỗ' : ''}</button><button type="button" class="btn small" data-hb="thoi" data-tip="Bỏ đề xuất, không chia">Thôi</button>`;
  } else if (soIm) {
    bar.hidden = false; bar.className = 'hinh-bar im';
    bar.innerHTML = `<span class="hb-t"><b>${soIm} đoạn im lặng</b> (sọc xám trên làn cảnh)<small>Bấm để xem, xoá khi chắc là thừa</small></span><button type="button" class="btn small danger" data-hb="xoa-im" data-tip="Xoá các cảnh sọc xám (1 bước Ctrl+Z)">${icon('xoa')}Xoá ${soIm} đoạn im lặng</button><button type="button" class="btn small ghost" data-hb="bo-im" data-tip="Bỏ đánh dấu, giữ nguyên các cảnh">Bỏ đánh dấu</button>`;
  } else { bar.hidden = true; bar.innerHTML = ''; }
}
$('#tl').addEventListener('click', e => {
  const b = e.target.closest('#hinhBar [data-hb]'); if (b) {
    const a = b.dataset.hb;
    if (a === 'dung') { S.hinh.chia = null; return veHinh(); }
    if (a === 'thoi') { S.hinh.dx = null; return veHinh(); }
    if (a === 'chia') return apChia();
    if (a === 'xoa-im') return xoaIm();
    if (a === 'bo-im') { doi(p => p.canh.forEach(c => { delete c._im; })); return toast('Đã bỏ đánh dấu im lặng (Ctrl+Z để lấy lại)'); }
    return;
  }
  const v = e.target.closest('#hinhLop .hinh-vach'); if (v) {
    e.stopPropagation(); const [i, j] = v.dataset.hv.split(':').map(Number), e0 = S.hinh.dx && S.hinh.dx.canh[i], k = e0 && e0.cat[j]; if (!k) return;
    k.bo = !k.bo; if (k.loai === 'im') e0.cat.forEach(z => { if (z.loai === 'im' && z.cap === k.cap) z.bo = k.bo; });
    veHinh();
  }
}, true);
function apChia() {
  const D = S.hinh.dx; if (!D) return;
  const ops = [], im = [];
  D.canh.forEach(e => {
    const c = S.plan.canh.find(y => y._id === e.id); if (!c) return;
    const ts = e.cat.filter(k => !k.bo && k.t > c.tu + 0.3 && k.t < c.den - 0.3).map(k => k.t).sort((a, b) => b - a);   // cuối trước: cảnh gốc luôn là phần đầu
    ts.forEach(t => ops.push({op: 'chia_canh', canh: e.id, tai: t}));
    (e.im || []).forEach(([a, b, g]) => { const co = t => ts.some(x => Math.abs(x - t) < 0.002);
      if ((a <= c.tu + 0.002 || co(a)) && (b >= c.den - 0.002 || co(b))) im.push({file: c.file, a: Math.max(a, c.tu), b: Math.min(b, c.den), g}); });
  });
  if (!ops.length) return toast('Không còn chỗ chia nào (đã bỏ hết vạch)', true);
  const n0 = S.plan.canh.length; let kq = [];
  S.hinh.dx = null;
  doi(p => { kq = apOps(p, ops);
    im.forEach(m => { const z = p.canh.find(y => y.file === m.file && Math.abs(y.tu - m.a) < 0.004 && Math.abs(y.den - m.b) < 0.004); if (z) z._im = [r3(m.a), r3(m.b), r2(m.g)]; }); });
  const loi = kq.filter(x => x.loi).length, soIm = S.plan.canh.filter(laIm).length;
  veHinh();
  toast('Đã chia ' + (ops.length - loi) + ' chỗ: ' + n0 + ' → ' + S.plan.canh.length + ' cảnh' + (soIm ? ', ' + soIm + ' đoạn im lặng (sọc xám)' : '') + ' (Ctrl+Z để gộp lại)');
}
function xoaIm() {
  const ds = S.plan.canh.filter(laIm); if (!ds.length) return;   // 4/11 18:14: xoá hết cảnh cũng được (video trống)
  doi(p => { p.canh = p.canh.filter(c => !laIm(c)); giuChon(); });
  toast('Đã xoá ' + ds.length + ' đoạn im lặng (Ctrl+Z để lấy lại)');
}
function veVach() {   // vạch đề xuất + vùng im lặng trên làn cảnh; đánh dấu khối cảnh im lặng
  const tlin = $('#tlin'); if (!tlin || !S.plan) return;
  let lop = $('#hinhLop'); if (!lop) { lop = document.createElement('div'); lop.id = 'hinhLop'; lop.className = 'hinh-lop'; tlin.append(lop); }
  const D = S.hinh.dx, b = bocCanh(), pps = S.pps; let h = '';
  if (D) D.canh.forEach((e, i) => {
    const x = b.find(y => y.c._id === e.id); if (!x) return;
    const X = t => (x.bd + (t - x.c.tu)) * pps;
    (e.im || []).forEach(([a0, b0, g]) => { const a = Math.max(a0, x.c.tu), z = Math.min(b0, x.c.den); if (z - a < 0.3) return;
      const bo = e.cat.some(k => k.loai === 'im' && k.bo && (Math.abs(k.t - a0) < 0.002 || Math.abs(k.t - b0) < 0.002));
      h += `<div class="hinh-imv${bo ? ' bo' : ''}" style="left:${X(a)}px;width:${Math.max(4, (z - a) * pps)}px"><span>Im lặng ${gs(g)}</span></div>`; });
    e.cat.forEach((k, j) => { if (k.t <= x.c.tu + 0.3 || k.t >= x.c.den - 0.3) return;
      const tip = (k.bo ? 'ĐÃ BỎ · ' : '') + 'Chia ở giây ' + gs(k.t) + ' của clip · ' + k.ly_do + (k.sau ? ' · trước “' + k.sau + '…”' : '') + ' · bấm để ' + (k.bo ? 'lấy lại' : 'bỏ');
      h += `<button type="button" class="hinh-vach l-${k.loai}${k.bo ? ' bo' : ''}" data-hv="${i}:${j}" style="left:${X(k.t)}px" aria-label="${esc(tip)}" data-tip="${esc(tip)}"><i></i></button>`; });
  });
  lop.innerHTML = h;
  // khối cảnh im lặng (đã chia): sọc xám + nhãn
  $$('#tCanh .blk').forEach(el => { const c = S.plan.canh.find(y => y._id === el.dataset.id), im = laIm(c);
    el.classList.toggle('hinh-im', im); const cu = el.querySelector('.hinh-im-n');
    if (im && !cu) el.insertAdjacentHTML('afterbegin', `<span class="hinh-im-n">Im lặng</span>`); else if (!im && cu) cu.remove(); });
}
function veHinh() { veBar(); veVach(); }
// timeline vẽ lại (sửa, phóng to, Ctrl+Z…) -> vẽ lại vạch; đề xuất của cảnh đã đổi giờ / đã xoá thì bỏ chỗ không còn hợp
new MutationObserver(() => {
  const D = S.hinh.dx;
  if (D) { D.canh = D.canh.filter(e => { const c = S.plan.canh.find(y => y._id === e.id); if (!c) return false; e.cat = e.cat.filter(k => k.t > c.tu + 0.3 && k.t < c.den - 0.3); return e.cat.length; });
    if (!D.canh.length) S.hinh.dx = null; }
  veHinh();
}).observe($('#tCanh'), {childList: true});
