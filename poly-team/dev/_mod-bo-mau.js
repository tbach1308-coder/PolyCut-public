/* ============================== BỘ MẪU CHỮ + KIỂU DỰNG CẢ VIDEO (r36, 11/11/2026) ==============================
   Anh 11/11 10:54 "template còn xấu" -> 11:45 duyệt "làm cả 3 bộ, cho anh chọn trong app; kèm 6 kiểu dựng cả video".
   Tab Kiểu thêm 2 hàng ở đầu:
   - "Bộ mẫu chữ": Cũ · Lục bảo sang · Tối giản trắng–vàng · Thẻ kính mờ (ảnh nhỏ). Chọn = kieu.bo_mau (Cũ = bỏ khoá). Hook, nhãn, thẻ tên
     máy, thẻ giá, tiêu đề, thẻ kết, POLY STORE, phụ đề vẽ theo bộ (engine/mau_chu_moi.py). Có bộ thì hiện thêm hàng "Kiểu phụ đề của bộ"
     (kieu.kieu_phu_de + kieu.phu_de cụm / cả câu cho khớp).
   - "Kiểu dựng cả video": 6 kiểu có ảnh bìa (đầu / giữa / kết). Chọn = đặt bộ + kiểu phụ đề + các mục kiểu (chỉ giá trị video này dùng được),
     ghim như anh tự chọn. "So sánh 2 máy" chưa có bố cục chia đôi: hiện mờ, (i) ghi rõ.
   Mỗi lần bấm = 1 bước Ctrl+Z (doi()), khung xem vẽ lại ngay (sua_tay_may: khoá vẽ có bo_mau / kieu_phu_de).
   Kính mờ ở khung xem: lớp có `mo` (sigma, khung 1080) -> 1 lớp CSS backdrop-filter dưới ảnh chữ, mặt nạ = chính ảnh chữ
   (bản xuất: dung_may_chu làm mờ bằng ffmpeg). Lớp kính đi theo ảnh chữ (hiện / ẩn / kéo) qua MutationObserver.
   Video mới vẫn mặc định Cũ (anh dặn trơn); chọn bộ là tuỳ anh. Dữ liệu: S.info.bo_mau_ds / kieu_dung_ds (sua_tay_may.bo_mau_app). */
const BM = {
  bo: () => ((S.info || {}).bo_mau_ds) || [],
  kd: () => ((S.info || {}).kieu_dung_ds) || [],
};
function bmHienTai(p = S.plan) { const id = ((p || {}).kieu || {}).bo_mau || ''; return BM.bo().some(b => b.id === id) ? id : ''; }
function bmPd(bo, id, pdChung) {   // = mau_chu_moi.pd_kieu: kiểu phụ đề dùng (khớp loại cụm / cả câu)
  const b = BM.bo().find(x => x.id === bo); if (!b || !b.phu_de.length) return null;
  const loai = pdChung === 'ca_cau' ? 'cau' : pdChung === 'cum_ngan' ? 'cum' : null;
  const st = b.phu_de.find(x => x.id === id);
  if (st && (!loai || st.loai === loai)) return st;
  return b.phu_de.find(x => x.loai === loai) || b.phu_de[0];
}
function kdGiaTri(x) {   // các mục của kiểu dựng mà video này chọn được (đường Premiere / máy chủ khác nhau) -> [[mục, giá trị]]
  const ds = (S.info || {}).kieu_ds || [];
  return Object.entries(x.kieu || {}).filter(([m, v]) => { const d = ds.find(y => y.muc === m); return d && d.ds.some(y => y.v === v); });
}
function kdKhop(x) {
  if (!S.plan || bmHienTai() !== x.bo_mau) return false;
  const k = S.plan.kieu || {}, st = bmPd(x.bo_mau, x.phu_de, null);
  if (st && k.kieu_phu_de !== st.id) return false;
  return kdGiaTri(x).every(([m, v]) => m === 'ket' && (S.plan.chu || {}).ket === null ? true : kieuDung(m) === v);
}
function bmKhoi() {
  const bo = BM.bo(); if (!bo.length || !S.plan) return '';
  const cur = bmHienTai(), b = bo.find(x => x.id === cur);
  const st = cur ? bmPd(cur, (S.plan.kieu || {}).kieu_phu_de, (S.plan.kieu || {}).phu_de) : null;
  const o = x => `<button type="button" class="bm-o${x.id === cur ? ' on' : ''}" data-bm="${esc(x.id)}" aria-pressed="${x.id === cur}" data-tip="${esc(x.mo_ta)}">${x.anh ? `<img src="${x.anh}" alt="" loading="lazy">` : '<span class="bm-trong"></span>'}<span class="bm-t">${esc(x.ten)}</span></button>`;
  const pd = b && b.phu_de.length ? `<div class="bm-pd" role="group" aria-label="Kiểu phụ đề của bộ"><span class="lbl">Phụ đề</span><div class="bm-pd-ds">${b.phu_de.map(p => `<button type="button" class="chip${st && st.id === p.id ? ' on' : ''}" data-bmpd="${esc(p.id)}" aria-pressed="${!!(st && st.id === p.id)}">${esc(p.ten)}</button>`).join('')}</div></div>` : '';
  const kd = BM.kd();
  const k = x => `<button type="button" class="kd-o${kdKhop(x) ? ' on' : ''}${x.sap_co ? ' sap' : ''}" data-kd="${esc(x.id)}" aria-pressed="${kdKhop(x)}"${x.sap_co ? ' aria-disabled="true"' : ''} data-tip="${esc(x.mo_ta + (x.sap_co ? ' — ' + x.sap_co : ''))}">${x.anh ? `<img src="${x.anh}" alt="" loading="lazy">` : ''}<span class="kd-t">${esc(x.ten)}${x.sap_co ? '<small>sắp có</small>' : ''}</span></button>`;
  return `<div class="box bm-box"><h2 class="sec">Bộ mẫu chữ<button type="button" class="tt-i" data-tip="Chọn 1 bộ: hook, nhãn, thẻ tên máy, thẻ giá, tiêu đề, thẻ kết, chữ POLY STORE và phụ đề cả video vẽ theo bộ đó. Cũ = mẫu trước đây (theo ô Kiểu chữ / Phụ đề ở dưới). Chữ nào muốn khác bộ: chọn Mẫu chữ riêng cho chữ đó. Ctrl+Z để bỏ." aria-label="Giải thích bộ mẫu chữ">${icon('thongTin')}</button></h2>
    <div class="bm-ds" role="group" aria-label="Bộ mẫu chữ">${bo.map(o).join('')}</div>${pd}</div>`
    + (kd.length ? `<div class="box bm-box"><h2 class="sec">Kiểu dựng cả video<button type="button" class="tt-i" data-tip="1 bấm đặt cả bộ chữ, kiểu phụ đề, nhịp, chuyển cảnh, màu… theo loại video. Mục nào video này không dùng được (vd dựng bằng Premiere) thì giữ như cũ. Sau đó vẫn đổi từng mục ở dưới được. Ctrl+Z để bỏ." aria-label="Giải thích kiểu dựng">${icon('thongTin')}</button></h2>
    <div class="kd-ds" role="group" aria-label="Kiểu dựng cả video">${kd.map(k).join('')}</div></div>` : '');
}
function bmChon(id) {
  if (!S.plan || bmHienTai() === id) return;
  const b = BM.bo().find(x => x.id === id); if (!b) return;
  doi(p => {
    p.kieu = p.kieu || {};
    if (id) { p.kieu.bo_mau = id; const st = bmPd(id, p.kieu.kieu_phu_de, p.kieu.phu_de); if (st) p.kieu.kieu_phu_de = st.id; else delete p.kieu.kieu_phu_de; }
    else { delete p.kieu.bo_mau; delete p.kieu.kieu_phu_de; }
  });
  toast((id ? 'Đã dùng bộ ' + b.ten : 'Đã về mẫu chữ cũ') + ' · Ctrl+Z để bỏ');
}
function bmChonPd(id) {
  const cur = bmHienTai(); if (!cur) return;
  const st = BM.bo().find(x => x.id === cur).phu_de.find(x => x.id === id); if (!st) return;
  if ((S.plan.kieu || {}).kieu_phu_de === id && kieuDung('phu_de') === (st.loai === 'cau' ? 'ca_cau' : 'cum_ngan')) return;
  doi(p => { p.kieu.kieu_phu_de = id; p.kieu.phu_de = st.loai === 'cau' ? 'ca_cau' : 'cum_ngan'; ghimKieu(p, 'phu_de'); });
}
function kdChon(id) {
  const x = BM.kd().find(y => y.id === id); if (!x || !S.plan) return;
  if (x.sap_co) { toast(x.ten + ': ' + x.sap_co); return; }
  if (kdKhop(x)) return;
  const gt = kdGiaTri(x);
  doi(p => {
    p.kieu = p.kieu || {};
    gt.forEach(([m, v]) => { if (m === 'ket' && (p.chu || {}).ket === null) return; p.kieu[m] = v; ghimKieu(p, m); });
    p.kieu.bo_mau = x.bo_mau;
    const st = bmPd(x.bo_mau, x.phu_de, null);
    if (st) { p.kieu.kieu_phu_de = st.id; p.kieu.phu_de = st.loai === 'cau' ? 'ca_cau' : 'cum_ngan'; ghimKieu(p, 'phu_de'); }
  });
  toast('Đã đặt kiểu dựng ' + x.ten + ' · Ctrl+Z để bỏ');
}
(function () {
  const goc = benKieu;
  benKieu = function () { return bmKhoi() + goc.apply(this, arguments); };
  $('#pane').addEventListener('click', e => {
    const t = e.target.closest('[data-bm],[data-bmpd],[data-kd]'); if (!t || S.tab !== 'kieu') return;
    if (t.dataset.bm !== undefined) bmChon(t.dataset.bm);
    else if (t.dataset.bmpd) bmChonPd(t.dataset.bmpd);
    else if (t.dataset.kd) kdChon(t.dataset.kd);
  });
  /* ---------- kính mờ ở khung xem ---------- */
  const gocAp = apView;
  apView = function () {
    gocAp.apply(this, arguments);
    const v = S.view, box = $('#lops'); if (!v || !box) return;
    const k = (box.clientWidth || 360) / 1080;
    v.lop.forEach((l, i) => {
      const im = lopImgs[i]; if (!l.mo || !im) return;
      const d = document.createElement('div'); d.className = 'lopmo';
      const u = `url("${String(l.url).replace(/"/g, '%22')}")`;
      d.style.cssText = `--mo:${Math.max(1, l.mo * k).toFixed(1)}px;-webkit-mask-image:${u};mask-image:${u}`;
      box.insertBefore(d, im);
      const theo = () => { d.classList.toggle('on', im.classList.contains('on')); d.style.transform = im.style.transform; };
      theo();
      new MutationObserver(theo).observe(im, {attributes: true, attributeFilter: ['class', 'style']});
    });
  };
})();
