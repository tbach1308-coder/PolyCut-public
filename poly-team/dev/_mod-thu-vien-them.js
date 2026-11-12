/* ============================== THƯ VIỆN THÊM (r20, 4/11/2026 tối) ==============================
   Anh (18:59): "thư viện hiệu ứng nhạc chuyển cảnh còn ít quá" -> thêm nhiều hơn rõ rệt nhưng chất, hợp gu kênh (gọn, sạch, sang;
   lục bảo + vàng; giữ màu máy thật). Chỉ THÊM khoá / giá trị: kế hoạch cũ dựng y hệt.
   1) CHUYỂN CẢNH: 20 -> 35 (15 kiểu thêm vào kieu_dung.json › chuyen_canh_rieng). Thư viện chia nhóm Cơ bản / Trượt / Lau / Zoom /
      Đặc biệt (S.info.chuyen_nhom từ máy chủ), ô tìm nhanh (bỏ dấu), xem trước rê chuột bằng CSS (TV_XC thêm lớp mới).
   2) HIỆU ỨNG HÌNH: 8 -> 23 (hieu_ung_canh), chia nhóm Cả cảnh / Đầu cảnh / Màu; BỘ LỌC MÀU: 4 -> 11 LUT (HINH_LOC thêm 7, lọc SVG
      gần đúng cho khung xem khớp bằng dev/thu-sua-tay/xap_xi_lut.py). Tab Hiệu ứng có thanh mục + ô tìm.
   3) ÂM THANH: tab mới "Âm thanh" (15 tiếng tự tổng hợp CC0, am-thanh/ + am_thanh.py). Bấm = thêm ở vạch đỏ, kéo xuống timeline = thêm
      đúng giây thả, ▶ nghe thử. Kế hoạch: plan.am_thanh [{ma, local, file, ten, t, am_luong}]. Làn "Âm thanh" mới dưới làn Nhạc
      (bọc veLanNhac): khối nhỏ, kéo ngang để dời, bấm phải: nghe / dời tới vạch đỏ / to nhỏ / xoá, Delete xoá. Khung xem phát tiếng
      khi vạch đỏ chạy qua (bọc nhacKhung). Bộ dựng: dung_may_chu.am_thanh_dau_vao. Mọi thao tác qua doi() -> Ctrl+Z.
   4) Đếm số trên tab ("Chuyển cảnh 35"), Thư viện hẹp 270–400px không tràn.
   Móc nối ở file chung: _thu-vien.js (veTV: TV_THEM + tvSauVe; khoaTV: TV_THEM), _mod-nhac.js (nhóm phong cách nhạc). */
IC_P.amThanh = '<path d="M4 9.5v5h3.5L12 18.5v-13L7.5 9.5z"/><path d="M15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11"/>';
IC_P.tim = '<circle cx="11" cy="11" r="6.5"/><path d="M20 20l-4.2-4.2"/>';
const TVT = {loc: {chuyen: {tim: '', nhom: ''}, hieu: {tim: '', nhom: ''}, am: {tim: '', nhom: ''}}, am: null, amDang: false, amLoi: '', amVer: 0,
  nghe: null, ngheP: '', amXem: {}, amT: null};
const boDau = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[đĐ]/g, 'd').toLowerCase();

/* ---------- xem trước CSS cho kiểu mới (lớp xc-* / hu-* trong _mod-thu-vien-them.css) ---------- */
Object.assign(TV_XC, {hoa_tan_dai: 'fadeDai', truot_phai_muot: 'phaiMuot', de_phai: 'dePhai', keo_ngang: 'keoNgang', lau_mem_xuong: 'lauXuong',
  lau_mem_phai: 'lauPhai', lau_cheo_nguoc: 'cheoNguoc', lau_len: 'lauLen', lat_doc: 'latDoc', zoom_ra: 'zoomRa', mo_cua_ngang: 'cuaNgang',
  cua_lua: 'cuaLua', lat_the: 'latThe', lac_keo: 'lacKeo', ep_ngang: 'epNgang'});
Object.assign(TV_HINH, {toi_vien_nhe: 'vienToi', hat_phim_nhe: 'hatPhim', lam_net_ro: 'netRo', lam_min: 'min', lay_net_giua: 'netGiua', glow_nhe: 'glow',
  thu_khung: 'thuKhung', mo_vao: 'moVao', chop_sang_mem: 'chopMem', nhay_sang: 'nhaySang', rung_nhe: 'rungNhe', zoom_lui_vao: 'zoomLui',
  den_trang: 'denTrang', tong_lanh: 'tongLanh', tong_am: 'tongAm'});

/* ---------- 7 bộ lọc màu thêm (engine/luts, dev/tao_lut.py, CC0): bang / mt = xấp xỉ cho khung xem (xap_xi_lut.py) ---------- */
const HINH_LOC_THEM = [
  {v: "poly_trong_treo", ten: "Trong trẻo", mo_ta: "Đen sâu hơn chút, sáng trong hơn: nhìn rõ, sạch, không đổi màu máy",
   bang: [[0.0247,0.1169,0.234,0.3632,0.4996,0.6369,0.7637,0.8717,0.935],[0.0242,0.1194,0.2367,0.3669,0.5036,0.6405,0.7666,0.8747,0.9456],[0.0242,0.1176,0.2363,0.3672,0.5054,0.6435,0.7704,0.8809,0.9413]],
   mt: "1.1584 -0.0573 -0.0170 0.0000 -0.0241 -0.0068 1.1061 -0.0169 0.0000 -0.0267 -0.0060 -0.0541 1.1364 0.0000 -0.0256 0.0000 0.0000 0.0000 1.0000 0.0000"},
  {v: "poly_tuoi_nhe", ten: "Tươi nhẹ", mo_ta: "Màu tươi hơn chút (màu nhạt tăng nhiều, màu đậm gần như giữ): mở hộp, phụ kiện",
   bang: [[0.0194,0.1178,0.2448,0.3702,0.4975,0.6259,0.7552,0.8841,0.96],[0.0117,0.1188,0.248,0.3734,0.5001,0.6267,0.7522,0.8834,0.9842],[0.015,0.1149,0.246,0.3731,0.5015,0.6293,0.7574,0.8899,0.9616]],
   mt: "1.1972 -0.1306 -0.0462 0.0000 -0.0128 -0.0083 1.0757 -0.0452 0.0000 -0.0157 -0.0112 -0.1199 1.1490 0.0000 -0.0153 0.0000 0.0000 0.0000 1.0000 0.0000"},
  {v: "poly_dien_anh", ten: "Điện ảnh nhẹ", mo_ta: "Tối hơi xanh, sáng hơi ấm, đen hơi mờ: kể chuyện, giới thiệu tiệm",
   bang: [[0.0275,0.1195,0.2314,0.3589,0.4988,0.6373,0.762,0.8679,0.9604],[0.0298,0.1243,0.2329,0.3625,0.501,0.6397,0.7673,0.8767,0.974],[0.0299,0.1243,0.2333,0.3599,0.4985,0.6426,0.7724,0.8847,0.9814]],
   mt: "1.0081 0.0285 0.0107 0.0000 -0.0198 0.0138 1.0102 0.0059 0.0000 -0.0120 0.0012 0.0198 0.9783 0.0000 -0.0133 0.0000 0.0000 0.0000 1.0000 0.0000"},
  {v: "poly_sang_trong", ten: "Sang trọng", mo_ta: "Đen sâu, màu dịu, sáng hơi ánh vàng: máy cao cấp, hộp máy, viền kim loại",
   bang: [[0.0351,0.1202,0.2319,0.3575,0.4933,0.6307,0.7609,0.8764,0.9724],[0.0296,0.1256,0.2339,0.3629,0.4982,0.6358,0.7656,0.8848,0.9822],[0.0325,0.1222,0.2333,0.3611,0.498,0.6374,0.7699,0.8906,0.9904]],
   mt: "1.0152 0.0404 0.0105 0.0000 -0.0398 0.0214 1.0240 0.0088 0.0000 -0.0277 0.0100 0.0346 0.9826 0.0000 -0.0375 0.0000 0.0000 0.0000 1.0000 0.0000"},
  {v: "poly_ca_phe", ten: "Ấm cà phê", mo_ta: "Ấm nâu nhẹ, đen hơi mờ: góc tiệm, bàn gỗ, cảnh tư vấn",
   bang: [[-0.0041,0.1244,0.2511,0.3774,0.5017,0.627,0.7497,0.8724,0.9965],[-0.0043,0.1253,0.2504,0.3768,0.5017,0.6259,0.7485,0.8718,0.9938],[-0.0013,0.1244,0.2506,0.3757,0.5007,0.6267,0.7495,0.8734,0.994]],
   mt: "0.9440 0.0163 0.0043 0.0000 0.0052 0.0089 0.9317 0.0043 0.0000 0.0181 0.0078 0.0170 0.8971 0.0000 0.0021 0.0000 0.0000 0.0000 1.0000 0.0000"},
  {v: "poly_lanh_cong_nghe", ten: "Lạnh công nghệ", mo_ta: "Hơi xanh lạnh, tương phản rõ: máy bạc / đen, laptop",
   bang: [[0.0143,0.1245,0.2409,0.3657,0.4967,0.6283,0.7557,0.8741,0.9875],[0.0145,0.1254,0.2425,0.3682,0.4995,0.6313,0.7574,0.8789,0.9911],[0.0128,0.1248,0.2421,0.3688,0.5009,0.633,0.7596,0.8776,0.9905]],
   mt: "0.9918 0.0004 0.0006 0.0000 -0.0149 -0.0007 0.9968 0.0005 0.0000 -0.0153 -0.0007 0.0007 1.0240 0.0000 -0.0145 0.0000 0.0000 0.0000 1.0000 0.0000"},
  {v: "poly_den_trang", ten: "Đen trắng sang", mo_ta: "Đen trắng tương phản đẹp: so sánh trước / sau (không dùng khi khoe màu máy)",
   bang: [[-0.1419,-0.0566,0.0396,0.1612,0.2856,0.4228,0.5632,0.7008,0.7757],[0.2098,0.285,0.3935,0.524,0.6633,0.7925,0.9074,1.0126,1.1164],[-0.2,-0.1438,-0.0347,0.044,0.1418,0.2613,0.3437,0.3972,0.4878]],
   mt: "0.3218 0.6908 0.1517 0.0000 -0.0733 0.3218 0.6908 0.1517 0.0000 -0.0733 0.3218 0.6908 0.1517 0.0000 -0.0733 0.0000 0.0000 0.0000 1.0000 0.0000"}
];
HINH_LOC_THEM.forEach(x => { if (!HINH_LOC.some(y => y.v === x.v)) HINH_LOC.push(x); });
document.body.insertAdjacentHTML('beforeend', '<svg class="tv-svg" width="0" height="0" aria-hidden="true" focusable="false">' + HINH_LOC_THEM.map(x =>
  `<filter id="stLoc-${x.v}" color-interpolation-filters="sRGB" x="0" y="0" width="1" height="1"><feComponentTransfer in="SourceGraphic" result="c">${['R', 'G', 'B'].map((k, i) =>
    `<feFunc${k} type="table" tableValues="${x.bang[i].join(' ')}"/>`).join('')}</feComponentTransfer><feColorMatrix in="c" type="matrix" values="${x.mt}" result="l"/>`
  + `<feComposite in="SourceGraphic" in2="l" operator="arithmetic" k1="0" k2="0" k3="1" k4="0"/></filter>`).join('') + '</svg>');

/* ---------- thanh tìm + mục (dùng chung cho tab Chuyển cảnh / Hiệu ứng / Âm thanh) ---------- */
function tvThanh(tab, muc, goiY) {   // muc: [[khoá, tên, số]]
  const L = TVT.loc[tab];
  return `<div class="tvl" data-tvl="${tab}"><label class="tvl-tim">${icon('tim')}<input type="search" class="inp" data-tvl-tim="${tab}" placeholder="${esc(goiY)}" value="${esc(L.tim)}" aria-label="${esc(goiY)}"></label>`
    + `<div class="tvl-muc" role="group" aria-label="Lọc theo nhóm">${muc.map(([k, ten, n]) => `<button type="button" class="tvl-m${L.nhom === k ? ' on' : ''}" data-tvl-m="${k}" aria-pressed="${L.nhom === k}">${esc(ten)}${n != null ? `<b>${n}</b>` : ''}</button>`).join('')}</div></div>`;
}
function tvApLoc(tab, pane) {   // ẩn ô / nhóm không khớp ô tìm + mục đang chọn (không vẽ lại: ô tìm giữ con trỏ)
  pane = pane || $('#libPane'); const L = TVT.loc[tab], k = boDau(L.tim).trim();
  $$('[data-tvl-sec]', pane).forEach(sec => {
    const hopNhom = !L.nhom || sec.dataset.tvlSec === L.nhom || (sec.dataset.tvlCha || '').split(' ').includes(L.nhom);
    let con = 0;
    $$('[data-tvl-ten]', sec).forEach(o => { const ok = hopNhom && (!k || o.dataset.tvlTen.includes(k)); o.classList.toggle('tvl-an', !ok); if (ok) con++; });
    const coMuc = $$('[data-tvl-ten]', sec).length;
    sec.classList.toggle('tvl-an', !hopNhom || (coMuc > 0 && !con) || (!!k && !coMuc && !sec.hasAttribute('data-tvl-giu')));
  });
  $$('[data-tvl-chung]', pane).forEach(o => o.classList.toggle('tvl-an', !!k || !!L.nhom));
  const rong = pane.querySelector('.tvl-rong'); const het = !$$('[data-tvl-sec]', pane).some(s => !s.classList.contains('tvl-an'));
  if (rong) rong.hidden = !het;
  $$('.tvl-m', pane).forEach(b => { const on = b.dataset.tvlM === L.nhom; b.classList.toggle('on', on); b.setAttribute('aria-pressed', on); });
}
$('#libPane').addEventListener('input', e => {
  const i = e.target.closest && e.target.closest('[data-tvl-tim]'); if (!i) return;
  TVT.loc[i.dataset.tvlTim].tim = i.value; tvApLoc(i.dataset.tvlTim);
});
$('#libPane').addEventListener('keydown', e => { if (e.target.closest && e.target.closest('[data-tvl-tim]')) e.stopPropagation(); });   // gõ chữ không thành phím tắt
$('#libPane').addEventListener('click', e => {
  const b = e.target.closest('[data-tvl-m]'); if (!b) return;
  const tab = b.closest('[data-tvl]').dataset.tvl, L = TVT.loc[tab];
  L.nhom = L.nhom === b.dataset.tvlM ? '' : b.dataset.tvlM; tvApLoc(tab);
  if (L.nhom) { const s = $(`#libPane [data-tvl-sec="${L.nhom}"], #libPane [data-tvl-cha~="${L.nhom}"]`); if (s) s.scrollIntoView({block: 'nearest'}); }
});
const tvTen = (el, them) => boDau(((el.querySelector('.tvx-ten, .am-t b') || el).textContent || '') + ' ' + (them || ''));

/* ---------- vẽ xong 1 tab (móc trong veTV của _thu-vien.js): chia nhóm + thanh tìm ---------- */
function tvSauVe(tab, pane) {
  if (tab === 'chuyen') return tvNhomChuyen(pane);
  if (tab === 'hieu') return tvNhomHieu(pane);
}
const XC_NHOM = [['co_ban', 'Cơ bản'], ['truot', 'Trượt'], ['lau', 'Lau'], ['zoom', 'Zoom'], ['dac_biet', 'Đặc biệt']];
function tvNhomChuyen(pane) {
  const g = pane.querySelector('.tv-xc'); if (!g) return;
  const map = S.info.chuyen_nhom || {}, tenN = S.info.chuyen_ten_nhom || {}, rieng = {};
  (S.info.chuyen_rieng || []).forEach(x => { rieng[x.v] = x; });
  const o = [...g.querySelectorAll('[data-tvchuyen]')], chung = o.find(b => !b.dataset.tvchuyen), ds = o.filter(b => b.dataset.tvchuyen);
  const nhom = XC_NHOM.map(([k, t]) => [k, tenN[k] || t, ds.filter(b => (map[b.dataset.tvchuyen] || 'dac_biet') === k)]).filter(x => x[2].length);
  ds.forEach(b => { const x = rieng[b.dataset.tvchuyen], mt = (S.info.chuyen_mo_ta || {})[b.dataset.tvchuyen] || (x && x.mo_ta);
    if (mt || (x && x.cham)) b.dataset.tip = (b.dataset.tip || '') + (mt ? ' · ' + mt : '') + (x && x.cham && x.them_giay ? ' · dựng lâu: thêm khoảng ' + Math.round(x.them_giay) + ' giây mỗi chỗ nối ở bản 1080p' : '');
    b.dataset.tvlTen = tvTen(b, mt); });
  const sec = nhom.map(([k, t, bs]) => { const d = document.createElement('div'); d.className = 'tvl-sec'; d.dataset.tvlSec = k;
    d.innerHTML = `<div class="tvl-h">${esc(t)}<span>${bs.length}</span></div><div class="tv-grid tv-xc${g.classList.contains('tat') ? ' tat' : ''}"></div>`;
    bs.forEach(b => d.lastChild.append(b)); return d; });
  const dau = document.createElement('div'); dau.innerHTML = tvThanh('chuyen', [['', 'Tất cả', ds.length], ...nhom.map(([k, t, bs]) => [k, t, bs.length])], 'Tìm chuyển cảnh… (vd: trượt, mở, zoom)');
  g.before(dau.firstChild);
  if (chung) { chung.dataset.tvlChung = '1'; g.classList.add('tvl-chung-g'); }
  g.after(...sec, Object.assign(document.createElement('p'), {className: 'tv-note tvl-rong', hidden: true, textContent: 'Không có kiểu nào khớp. Xoá chữ trong ô tìm.'}));
  if (!chung) g.remove();
  tvApLoc('chuyen', pane);
}
const HU_NHOM = [['ca_canh', 'Cả cảnh'], ['dau_canh', 'Đầu cảnh'], ['mau', 'Màu']];
function nhomHu(x) { return x.dau_canh ? 'dau_canh' : x.nhom === 'mau' ? 'mau' : 'ca_canh'; }
function tvNhomHieu(pane) {
  // tách tab thành các phần theo tiêu đề: chuyển động · hiệu ứng hình · bộ lọc · cả video
  const kids = [...pane.children]; let cur = null; const phan = [];
  kids.forEach(el => { if (el.classList.contains('tv-h') || !cur) { cur = document.createElement('div'); cur.className = 'tvl-sec'; phan.push(cur); el.before(cur); } cur.append(el); });
  phan.forEach(p => { p.dataset.tvlSec = p.querySelector('[data-tvdong]') ? 'dong' : p.querySelector('[data-tvhinh]') ? 'hinh' : p.querySelector('[data-tvloc]') ? 'loc' : 'video'; });
  const hh = dsHieuUngHinh(), hp = phan.find(p => p.dataset.tvlSec === 'hinh'), lp = phan.find(p => p.dataset.tvlSec === 'loc');
  if (hp) {   // hiệu ứng hình: 3 nhóm con Cả cảnh / Đầu cảnh / Màu
    const g = hp.querySelector('.tv-grid'), o = [...g.querySelectorAll('[data-tvhinh]')], khong = o.find(b => !b.dataset.tvhinh);
    if (khong) khong.dataset.tvlChung = '1';
    const theo = {}; hh.forEach(x => { theo[x.v] = x; });
    const con = HU_NHOM.map(([k, t]) => { const bs = o.filter(b => b.dataset.tvhinh && nhomHu(theo[b.dataset.tvhinh] || {}) === k); if (!bs.length) return null;
      const d = document.createElement('div'); d.className = 'tvl-sec tvl-con'; d.dataset.tvlSec = k; d.dataset.tvlCha = 'hinh';
      d.innerHTML = `<div class="tvl-h">${esc(t)}<span>${bs.length}</span></div><div class="tv-grid tv-hu"></div>`;
      bs.forEach(b => { const x = theo[b.dataset.tvhinh]; if (x && x.mo_ta) b.dataset.tip = x.ten + ': ' + x.mo_ta + (x.dau_canh ? ' (chỉ đầu cảnh)' : '') + ' · bấm để dùng cho cảnh đang chọn';
        b.dataset.tvlTen = tvTen(b, x && x.mo_ta); d.lastChild.append(b); }); return d; }).filter(Boolean);
    g.after(...con); hp.dataset.tvlCha = 'ca_canh dau_canh mau';
  }
  [...pane.querySelectorAll('[data-tvdong], [data-tvloc], [data-tvkieu]')].forEach(b => { const l = HINH_LOC.find(y => y.v === b.dataset.tvloc); b.dataset.tvlTen = tvTen(b, l && l.mo_ta); });
  if (lp) lp.querySelectorAll('[data-tvloc=""]').forEach(b => { b.dataset.tvlChung = '1'; });
  const dg = phan.find(p => p.dataset.tvlSec === 'dong'); if (dg) dg.querySelectorAll('[data-tvdong=""]').forEach(b => { b.dataset.tvlChung = '1'; });
  const n = k => hh.filter(x => nhomHu(x) === k).length;
  const dau = document.createElement('div');
  dau.innerHTML = tvThanh('hieu', [['', 'Tất cả', null], ['ca_canh', 'Cả cảnh', n('ca_canh')], ['dau_canh', 'Đầu cảnh', n('dau_canh')], ['mau', 'Màu', n('mau')],
    ['loc', 'Bộ lọc', HINH_LOC.length], ['dong', 'Chuyển động', dsDongCanh().length], ['video', 'Cả video', null]], 'Tìm hiệu ứng, bộ lọc… (vd: nét, ấm, rung)');
  pane.prepend(dau.firstChild);
  pane.append(Object.assign(document.createElement('p'), {className: 'tv-note tvl-rong', hidden: true, textContent: 'Không có hiệu ứng nào khớp. Xoá chữ trong ô tìm.'}));
  tvApLoc('hieu', pane);
}

/* ---------- đếm số trên tab ---------- */
function demTab(k) {
  if (k === 'chuyen') return typeof dsChuyenCanh === 'function' && S.info ? dsChuyenCanh().length : null;
  if (k === 'hieu') return S.info ? dsHieuUngHinh().length + HINH_LOC.length : null;
  if (k === 'am') return TVT.am ? TVT.am.ds.length : null;
  if (k === 'nhac') { const d = (typeof NH !== 'undefined' && NH.ds) || null; return d ? ((d.tiem || {}).ds || []).length + ((d.mien_phi || {}).ds || []).length : null; }
  if (k === 'clip') { const d = S.tv.ds[S.tv.tm]; return d && d.clip ? d.clip.length : null; }
  if (k === 'giong') return typeof GA !== 'undefined' && GA.ds && Array.isArray(GA.ds.ds) ? GA.ds.ds.length : null;
  if (k === 'ti') return S.ti && Array.isArray(S.ti.ds) ? S.ti.ds.filter(x => x.bat && !x.loi).length : null;
  return null;
}
const _veTvTabsGoc = veTvTabs;
veTvTabs = function () {
  _veTvTabsGoc();
  $$('#libTabs [data-tv]').forEach(b => { const n = demTab(b.dataset.tv); if (n == null) return;
    const s = b.querySelector('span'); if (s && !b.querySelector('.tv-dem')) s.insertAdjacentHTML('afterend', `<b class="tv-dem" aria-hidden="true">${n}</b>`);
    b.dataset.tip = b.dataset.tip.replace(/^([^:]+):/, '$1 (' + n + '):'); b.setAttribute('aria-label', b.getAttribute('aria-label') + ' (' + n + ')'); });
};
let demCu = '';
function capNhatDem() { const k = ['chuyen', 'hieu', 'am', 'nhac', 'clip', 'giong', 'ti'].map(demTab).join(','); if (k !== demCu) { demCu = k; veTvTabs(); } }
setInterval(() => { if (S.plan && S.info) capNhatDem(); }, 1500);

/* ============================== ÂM THANH (tab mới + làn timeline + phát khi xem) ============================== */
TV_TAB.splice(TV_TAB.findIndex(x => x[0] === 'nhac') + 1, 0, ['am', 'amThanh', 'Âm thanh', 'Tiếng hiệu ứng ngắn: vút, bụp, ting, chụp ảnh… thêm ở vạch đỏ']);
try { if (localStorage.getItem('st-tv-tab') === 'am') S.tv.tab = 'am'; } catch (e) {}
const amUrl = p => '/api/sua-tay/am-thanh?p=' + encodeURIComponent(p);
const amDs = () => (S.plan && Array.isArray(S.plan.am_thanh)) ? S.plan.am_thanh : [];
const AM_NHOM = [['chuyen', 'Chuyển cảnh'], ['nhan', 'Nhấn'], ['thong_bao', 'Thông báo'], ['vui', 'Vui']];
async function taiAm() {
  if (TVT.amDang) return; TVT.amDang = true; TVT.amLoi = '';
  try { TVT.am = await api('/api/sua-tay/am-thanh-ds'); TVT.amVer++; } catch (e) { TVT.amLoi = e.message; }
  TVT.amDang = false; if (S.tv.tab === 'am') veTV(true); capNhatDem(); veTimeline();
}
function amTim(p) { return ((TVT.am || {}).ds || []).find(x => x.p === p); }
function amGiay(x) { const y = amTim(x.local); return (y && +y.giay) || 0.5; }
TV_THEM.am = {
  khoa: () => JSON.stringify([amDs(), TVT.amVer, TVT.amLoi, S.tv.amChon || '']),
  ve: () => '<div id="tvAm" class="am"></div>',
  sau: () => veAmTV($('#tvAm')),
};
function veAmTV(el) {
  if (!el) return;
  if (!TVT.am) { if (!TVT.amDang && !TVT.amLoi) taiAm(); el.innerHTML = TVT.amLoi ? `<p class="tv-note err">${esc(TVT.amLoi)}</p><div class="tv-hang"><button type="button" class="btn small" data-am-a="tai">Thử lại</button></div>` : '<p class="tv-note tv-cho">Đang đọc âm thanh…</p>'; return; }
  const ds = TVT.am.ds, tenN = Object.assign({}, ...AM_NHOM.map(([k, t]) => ({[k]: t})), TVT.am.nhom || {}), trong = amDs();
  let h = '';   // 4/11 tối anh: "chữ chiếm chỗ nhiều quá" -> câu hướng dẫn vào dấu (i) cạnh tiêu đề
  if (trong.length) {
    h += tvTieuDe('Trong video', trong.length + ' tiếng');
    h += `<div class="am-ds am-trong">${trong.map(x => `<div class="am-dong${S.tv.amChon === x.ma ? ' on' : ''}" data-am-ma="${esc(x.ma || '')}">
      <button type="button" class="am-nghe" data-am-nghe="${esc(x.local)}" aria-label="Nghe ${esc(x.ten)}" data-tip="Nghe thử">${icon('play')}</button>
      <button type="button" class="am-toi" data-am-toi="${esc(x.ma || '')}" data-tip="Tới chỗ tiếng này trên timeline"><b>${esc(x.ten)}</b><small>lúc ${tg(x.t)}${x.am_luong != null && x.am_luong !== 1 ? ' · ' + Math.round(x.am_luong * 100) + '%' : ''}</small></button>
      <button type="button" class="btn small icon ghost" data-am-xoa="${esc(x.ma || '')}" aria-label="Xoá ${esc(x.ten)}" data-tip="Xoá tiếng này (Ctrl+Z để lấy lại)">${icon('xoa')}</button></div>`).join('')}</div>`;
  }
  const muc = AM_NHOM.map(([k]) => [k, tenN[k] || k, ds.filter(x => x.nhom === k).length]).filter(x => x[2]);
  h += tvTieuDe('Âm thanh có sẵn', ds.length + ' tiếng · CC0', 'Bấm 1 tiếng để thêm ở vạch đỏ, hoặc kéo xuống timeline đúng chỗ. ▶ nghe thử. Trên làn Âm thanh (dưới làn Nhạc): kéo ngang để dời, bấm phải để chỉnh. Tiếng Poly Store tự tổng hợp, CC0, không bản quyền.');
  h += tvThanh('am', [['', 'Tất cả', ds.length], ...muc], 'Tìm tiếng… (vd: vút, ting, chụp)');
  h += muc.map(([k, t, n]) => `<div class="tvl-sec" data-tvl-sec="${k}"><div class="tvl-h">${esc(t)}<span>${n}</span></div><div class="am-ds">${ds.filter(x => x.nhom === k).map(x => {
    const on = TVT.ngheP === x.p;
    return `<div class="am-bai" data-am-p="${esc(x.p)}" data-tvl-ten="${esc(boDau(x.ten + ' ' + x.mo_ta))}" role="button" tabindex="0" aria-label="${esc('Thêm tiếng ' + x.ten + ' ở vạch đỏ')}" data-tip="${esc(x.mo_ta + ' · bấm để thêm ở vạch đỏ, hoặc kéo xuống timeline')}">
      <button type="button" class="am-nghe${on ? ' on' : ''}" data-am-nghe="${esc(x.p)}" aria-label="Nghe thử ${esc(x.ten)}" data-tip="Nghe thử (không thêm vào video)">${icon(on ? 'pause' : 'play')}</button>
      <span class="am-t"><b>${esc(x.ten)}</b><small>${esc(gs(+x.giay || 0))} · ${esc(x.mo_ta)}</small></span><span class="am-them" aria-hidden="true">${icon('them')}</span></div>`; }).join('')}</div></div>`).join('');
  h += '<p class="tv-note tvl-rong" hidden>Không có tiếng nào khớp. Xoá chữ trong ô tìm.</p>';
  el.innerHTML = h;
  tvApLoc('am', $('#libPane'));
}
/* nghe thử */
function amNghe(p, vol) {
  if (TVT.ngheP === p && vol == null) return amNgheDung();
  amNgheDung(); dung();
  const a = TVT.nghe = new Audio(amUrl(p)); TVT.ngheP = p; a.volume = clamp(vol == null ? 0.85 : vol, 0, 1);
  a.addEventListener('ended', amNgheDung); a.play().catch(amNgheDung); veNgheAm();
}
function amNgheDung() { if (TVT.nghe) { TVT.nghe.pause(); TVT.nghe = null; } if (TVT.ngheP) { TVT.ngheP = ''; veNgheAm(); } }
function veNgheAm() { $$('#tvAm .am-bai [data-am-nghe]').forEach(b => { const on = b.dataset.amNghe === TVT.ngheP; b.classList.toggle('on', on); b.innerHTML = icon(on ? 'pause' : 'play'); }); }
/* thêm / dời / xoá (mỗi lần = 1 bước Ctrl+Z) */
function themAm(x, t) {
  if (!S.plan || !x) return;
  const T = (S.view || {}).T || tongT(); t = clamp(t == null ? S.t : t, 0, Math.max(0, T - 0.05));
  const moi = {ma: ma('a'), local: x.p, file: x.p, ten: x.ten, t: r3(t)};
  doi(p => { p.am_thanh = (Array.isArray(p.am_thanh) ? p.am_thanh : []).concat(moi).sort((a, b) => a.t - b.t); });
  S.tv.amChon = moi.ma; S.selLoai = 'amtv';
  amNghe(x.p, 0.7);
  const ln = $('#tAm'); if (ln) ln.scrollIntoView({block: 'nearest'});   // làn dưới cùng timeline: cuộn tới cho thấy khối vừa thêm
  toast('Đã thêm tiếng “' + x.ten + '” lúc ' + tg(t) + ' (Ctrl+Z để bỏ)');
  if (S.tv.tab === 'am') veTV(true);
}
function suaAm(ma_, f, tb) {
  const i = amDs().findIndex(y => y.ma === ma_); if (i < 0) return;
  doi(p => { const y = p.am_thanh[i]; f(y, p); p.am_thanh = p.am_thanh.filter(Boolean).sort((a, b) => a.t - b.t); if (!p.am_thanh.length) delete p.am_thanh; });
  if (tb) toast(tb + ' (Ctrl+Z để bỏ)');
}
function xoaAm(ma_) { const x = amDs().find(y => y.ma === ma_); if (!x) return; if (S.tv.amChon === ma_) S.tv.amChon = ''; suaAm(ma_, (y, p) => { p.am_thanh = p.am_thanh.filter(z => z.ma !== ma_); }, 'Đã xoá tiếng “' + x.ten + '”'); }
function toiAm(ma_) { const x = amDs().find(y => y.ma === ma_); if (!x) return; dung(); S.tv.amChon = ma_; S.selLoai = 'amtv'; tua(x.t); giuVach(); veTimeline(); if (S.tv.tab === 'am') veTV(true); }
$('#libPane').addEventListener('click', e => {
  if (!e.target.closest('#tvAm') || S.tv.vuaKeo) return;
  const n = e.target.closest('[data-am-nghe]'); if (n) { e.stopPropagation(); return amNghe(n.dataset.amNghe); }
  const xo = e.target.closest('[data-am-xoa]'); if (xo) return xoaAm(xo.dataset.amXoa);
  const to = e.target.closest('[data-am-toi]'); if (to) return toiAm(to.dataset.amToi);
  const a = e.target.closest('[data-am-a]'); if (a && a.dataset.amA === 'tai') { TVT.amLoi = ''; return taiAm(); }
  const b = e.target.closest('.am-bai[data-am-p]'); if (b) themAm(amTim(b.dataset.amP));
});
$('#libPane').addEventListener('keydown', e => { const b = e.target.closest && e.target.closest('#tvAm .am-bai'); if (b && e.target === b && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); themAm(amTim(b.dataset.amP)); } });
$('#libPane').addEventListener('contextmenu', e => {
  const b = e.target.closest('#tvAm .am-bai'); if (!b || !S.plan) return;
  e.preventDefault(); e.stopPropagation(); const x = amTim(b.dataset.amP); if (!x) return;
  moMenu(e.clientX, e.clientY, [{nhom: x.ten + ' · ' + gs(+x.giay || 0)}, {t: 'Thêm ở vạch đỏ (' + tg(S.t) + ')', ic: 'them', f: () => themAm(x)},
    {t: 'Thêm ở đầu video', f: () => themAm(x, 0)}, {t: TVT.ngheP === x.p ? 'Dừng nghe' : 'Nghe thử', ic: 'play', f: () => amNghe(x.p)}]);
});
/* kéo 1 tiếng từ Thư viện xuống timeline = thêm đúng giây thả */
$('#libPane').addEventListener('pointerdown', e => {
  if (e.button !== 0 || !S.plan) return;
  const t0 = e.target.closest('#tvAm .am-bai'); if (!t0 || e.target.closest('[data-am-nghe]')) return;
  const x = amTim(t0.dataset.amP); if (!x) return;
  const x0 = e.clientX, y0 = e.clientY; let keo = false, gh = null, tt = null;
  const mv = ev => {
    if (!keo) { if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < 6) return;
      keo = true; S.tv.keoTha = true; dung(); document.body.classList.add('tv-dang-keo'); $$('.tip').forEach(z => z.classList.remove('on'));
      gh = document.createElement('div'); gh.className = 'tv-bong'; gh.innerHTML = icon('amThanh') + `<span>${esc(x.ten)}</span><small></small>`; document.body.append(gh); }
    gh.style.left = (ev.clientX + 12) + 'px'; gh.style.top = (ev.clientY + 10) + 'px';
    const el = document.elementFromPoint(ev.clientX, ev.clientY), trung = !!(el && el.closest('#tls'));
    const T = (S.view || {}).T || tongT(); tt = trung ? clamp(tTuX(ev.clientX), 0, Math.max(0, T - 0.05)) : null;
    const ln = $('#tAm'); if (ln) ln.classList.toggle('tha', trung); gh.classList.toggle('co', trung);
    let v = $('#amIns'); if (trung) { if (!v) { v = document.createElement('div'); v.id = 'amIns'; v.className = 'tv-ins gio'; $('#tlin').append(v); }
      const l = $('#tAm'); v.style.left = (tt * S.pps - 1) + 'px'; v.style.top = l ? l.style.top : '0'; v.style.height = l ? l.style.height : '20px'; } else if (v) v.remove();
    $('small', gh).textContent = trung ? 'thả để thêm lúc ' + tg(tt) : 'thả xuống timeline';
  };
  const xong = ev => {
    removeEventListener('pointermove', mv); removeEventListener('pointerup', xong); removeEventListener('pointercancel', xong);
    if (!keo) return;
    if (gh) gh.remove(); const v = $('#amIns'); if (v) v.remove(); const ln = $('#tAm'); if (ln) ln.classList.remove('tha'); document.body.classList.remove('tv-dang-keo');
    S.tv.vuaKeo = true; setTimeout(() => { S.tv.vuaKeo = false; S.tv.keoTha = false; }, 0);
    if (ev.type === 'pointerup' && tt != null) themAm(x, tt);
  };
  addEventListener('pointermove', mv); addEventListener('pointerup', xong); addEventListener('pointercancel', xong);
});

/* ---------- làn Âm thanh dưới làn Nhạc (bọc veLanNhac của _mod-nhac.js) ---------- */
function veLanAm(top, T, pps) {
  let ln = $('#tAm'), nm = $('#nmAm');
  if (!ln) { ln = document.createElement('div'); ln.className = 'trk am'; ln.id = 'tAm'; const ph = $('#phl'); ph ? ph.before(ln) : $('#tlin').append(ln); }
  if (!nm) { nm = document.createElement('span'); nm.id = 'nmAm'; nm.innerHTML = '<b>Âm thanh</b>'; nm.dataset.tip = 'Làn Âm thanh: tiếng hiệu ứng ngắn (Thư viện › Âm thanh)'; $('#tnames').append(nm); }
  const h = 23; ln.style.top = top + 'px'; ln.style.height = h + 'px'; Object.assign(nm.style, {top: top + 'px', height: h + 'px'});
  const tn = $('#tnames'); if (tn) tn.style.minHeight = (top + h + 4) + 'px';
  const ds = amDs();
  if (!ds.length) { ln.innerHTML = `<div class="bar am trong" data-t="0" style="top:2px;left:0" data-tip="Thêm âm thanh hiệu ứng (vút, bụp, ting…): mở Thư viện › Âm thanh">${icon('them')}<span>Âm thanh</span></div>`; return h; }
  ln.innerHTML = ds.map(x => { const d = amGiay(x), w = Math.max(16, d * pps - 2), on = S.tv.amChon === x.ma;
    const tip = x.ten + ' · lúc ' + tg(x.t) + (x.am_luong != null && x.am_luong !== 1 ? ' · ' + Math.round(x.am_luong * 100) + '%' : '') + ' · kéo ngang để dời, bấm phải để chỉnh / xoá';
    return `<div class="bar am${on ? ' sel' : ''}" data-am="${esc(x.ma || '')}" data-t="${x.t}" style="top:2px;left:${x.t * pps}px;width:${w}px" title="${esc(tip)}">${icon('amThanh')}<span>${esc(x.ten)}</span></div>`; }).join('');
  return h;
}
if (typeof veLanNhac === 'function') {
  const _veLanNhacGoc = veLanNhac;
  veLanNhac = function (top, T, pps) { const h = _veLanNhacGoc(top, T, pps); return h + 2 + veLanAm(top + h + 2, T, pps); };
}
$('#tlin').addEventListener('pointerdown', e => {
  const b = e.target.closest('#tAm .bar.am[data-am]'); if (!b || e.button !== 0 || !S.plan) return;
  e.stopPropagation(); e.preventDefault();
  const id = b.dataset.am, x = amDs().find(y => y.ma === id); if (!x) return;
  const x0 = e.clientX, T = (S.view || {}).T || tongT(); let keo = false, t1 = x.t;
  const tuKhoi = S.selLoai === 'am';   // gộp 5/11: đang chọn khối tiếng tách -> bảng phải phải bỏ bảng khối
  S.tv.amChon = id; S.selLoai = 'amtv'; $$('#tAm .bar.am').forEach(z => z.classList.toggle('sel', z === b)); if (tuKhoi) veBen(true);
  const mv = ev => { const dx = ev.clientX - x0; if (!keo && Math.abs(dx) < 4) return; keo = true;
    t1 = clamp(x.t + dx / S.pps, 0, Math.max(0, T - 0.05)); b.style.left = (t1 * S.pps) + 'px'; b.dataset.tip = ''; b.title = 'Dời tới ' + tg(t1); };
  const up = () => { removeEventListener('pointermove', mv); removeEventListener('pointerup', up); removeEventListener('pointercancel', up);
    if (keo && Math.abs(t1 - x.t) > 0.005) suaAm(id, y => { y.t = r3(t1); }, 'Dời tiếng “' + x.ten + '” tới ' + tg(t1));
    else { dung(); tua(x.t); giuVach(); amNghe(x.local, clamp(0.9 * (x.am_luong ?? 1), 0, 1)); veTimeline(); if (S.tv.tab === 'am') veTV(true); } };
  addEventListener('pointermove', mv); addEventListener('pointerup', up); addEventListener('pointercancel', up);
}, true);
$('#tlin').addEventListener('click', e => {
  if (e.target.closest('#tAm .bar.am.trong')) { e.stopPropagation(); moTab('am'); return; }
  if (e.target.closest('#tAm') && !e.target.closest('.bar')) { dung(); tua(tTuX(e.clientX)); }
});
$('#tlin').addEventListener('contextmenu', e => {
  const ln = e.target.closest('#tAm'); if (!ln || !S.plan || $('.mbg')) return;
  e.preventDefault(); e.stopPropagation();
  const b = e.target.closest('.bar.am[data-am]'), x = b && amDs().find(y => y.ma === b.dataset.am);
  if (!x) return moMenu(e.clientX, e.clientY, [{nhom: 'Âm thanh'}, {t: 'Thêm âm thanh…', ic: 'amThanh', f: () => moTab('am')}]);
  const tuKhoi = S.selLoai === 'am';   // gộp 5/11: đang chọn khối tiếng tách -> bảng phải phải bỏ bảng khối
  S.tv.amChon = x.ma; S.selLoai = 'amtv'; $$('#tAm .bar.am').forEach(z => z.classList.toggle('sel', z === b)); if (tuKhoi) veBen(true);   // không vẽ lại timeline: cuộn làm menu tự đóng
  const al = Math.round((x.am_luong ?? 1) * 100);
  moMenu(e.clientX, e.clientY, [{nhom: 'Âm thanh · ' + x.ten + ' · ' + tg(x.t)}, {t: 'Nghe thử', ic: 'play', f: () => amNghe(x.local, clamp(0.9 * (x.am_luong ?? 1), 0, 1))},
    {t: 'Dời tới vạch đỏ (' + tg(S.t) + ')', ic: 'chuyenC', f: () => suaAm(x.ma, y => { y.t = r3(S.t); }, 'Dời tiếng “' + x.ten + '” tới ' + tg(S.t))},
    {t: 'Nhân đôi ở vạch đỏ', ic: 'nhanDoi', f: () => themAm({p: x.local, ten: x.ten}, S.t)},
    {t: 'To / nhỏ', ic: 'loa', nhan: al + '%', sub: [[25, 'rất nhỏ'], [50, 'nhỏ'], [75, ''], [100, 'mặc định'], [150, 'to'], [200, 'rất to']]
      .map(([v, g]) => ({t: v + '%' + (g ? ' · ' + g : ''), chon: al === v, f: () => suaAm(x.ma, y => { if (v === 100) delete y.am_luong; else y.am_luong = v / 100; }, 'Tiếng “' + x.ten + '” ' + v + '%')}))},
    '-', {t: 'Xoá tiếng này', ic: 'xoa', nguy: true, phim: 'Del', f: () => xoaAm(x.ma)}]);
});
// Delete / Backspace khi đang chọn 1 tiếng trên làn Âm thanh: xoá tiếng đó (chạy trước phím tắt chung, không xoá nhầm cảnh)
addEventListener('keydown', e => {
  if (!(e.key === 'Delete' || e.key === 'Backspace') || S.selLoai !== 'amtv' || !S.tv.amChon || !S.plan) return;
  const a = document.activeElement; if (a && (a.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName))) return;
  if ($('.mbg') || $('.ctm-bg')) return;
  e.preventDefault(); e.stopImmediatePropagation(); xoaAm(S.tv.amChon);
}, true);
addEventListener('pointerdown', e => { if (S.selLoai === 'amtv' && !e.target.closest('#tAm, #tvAm, .cmenu')) { S.tv.amChon = ''; S.selLoai = 'canh'; $$('#tAm .bar.am.sel').forEach(z => z.classList.remove('sel')); } }, true);

/* ---------- khung xem: phát tiếng khi vạch đỏ chạy qua (bọc nhacKhung) ---------- */
function amKhung(t) {
  const ds = amDs();
  if (!S.playing || S.mode !== 'xem' || !ds.length) { TVT.amT = null; return; }
  const t0 = TVT.amT; TVT.amT = t;
  if (t0 == null || t < t0 || t - t0 > 0.5) return;   // mới bấm phát / tua lùi / nhảy xa: không phát bù
  ds.forEach(x => { if (x.t > t0 && x.t <= t) {
    let a = TVT.amXem[x.local]; if (!a || !a.paused) { a = new Audio(amUrl(x.local)); if (!TVT.amXem[x.local]) TVT.amXem[x.local] = a; }
    a.volume = clamp(0.9 * (x.am_luong ?? 1) * (typeof canTieng === 'function' ? 1 : 1), 0, 1); try { a.currentTime = 0; } catch (er) {} a.play().catch(() => {}); } });
}
if (typeof nhacKhung === 'function') {
  const _nhacKhungGoc = nhacKhung;
  nhacKhung = function (t) { _nhacKhungGoc(t); amKhung(t); };
}
// nạp sẵn danh sách (đếm số trên tab, độ dài khối trên làn) khi đã mở video
setTimeout(() => { if (!TVT.am) taiAm(); }, 800);
veTvTabs();
