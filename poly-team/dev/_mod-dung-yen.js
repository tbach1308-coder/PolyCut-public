/* ============================== ĐỨNG YÊN (4/11/2026 18:xx, anh: "khung hình vẫn rung" / "đoạn đầu bấm video chạy rất rung") ==============================
   Kiểu rung "hình tự zoom vào / ra, trôi qua lại": chuyển động TỰ ĐỘNG của kiểu chung (zoom_xen_ke, zoom_vao, pan_ngang, punch_nhip) +
   mở đầu đập zoom (punch_mo 125% -> 100%, chu_zoom). Tay rung trong clip lại bị phóng to theo -> anh thấy như rung.
   1) Video TẠO TAY (_tao_boi sua_tay): mục Chuyển động / Mở đầu anh chưa tự chọn (không có trong kieu._ghim) -> Đứng yên / mở đầu Thường,
      cả khung xem lẫn bản nháp / xuất (luật ở kieuDungYen() trong _sua-tay.src.html + sua_tay_may.kieu_dung_yen). Tab Kiểu ghi rõ đang dùng gì.
      Anh tự chọn zoom ở bất cứ đâu -> ghimKieu -> dùng như cũ. Video tạo MỚI: lưu sẵn Đứng yên / Thường (sua_tay_may.lenh_moi).
   2) Video Claude dựng (dữ liệu không đổi): kiểu đang tự zoom / lia thì hiện 1 dòng gợi ý ở tab Kiểu và tab Cảnh › Hình:
      "Hình tự zoom / lia? Bấm Đứng yên" -> 1 bấm: Chuyển động = Đứng yên + mở đầu đập zoom -> Thường (ghim cả 2), 1 bước Ctrl+Z.
   Móc ở file chung: _sua-tay.src.html (benKieu gọi goiYDungYen), _canh-tt.js (benCanh gọi hinhDungYen). */
IC_P.dungYen = '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M9 9.5v5M15 9.5v5"/>';
const DY_DONG = ['zoom_xen_ke', 'zoom_vao', 'pan_ngang', 'punch_nhip'], DY_MO = ['punch_mo', 'chu_zoom'];
function dyTuDong() {   // -> danh sách tên các thứ đang làm hình tự chuyển động ([] = đứng yên)
  if (!S.plan) return [];
  const o = [], cd = kieuDung('chuyen_dong'), md = kieuDung('mo_dau');
  if (DY_DONG.includes(cd)) o.push(tenGiaTri('chuyen_dong', cd).toLowerCase());
  if (DY_MO.includes(md)) o.push('mở đầu ' + tenGiaTri('mo_dau', md).toLowerCase());
  return o;
}
function goiYDungYen(noi) {
  const o = dyTuDong(); if (!o.length) return '';
  return `<div class="dy-goi${noi === 'canh' ? ' canh' : ''}" role="note"><span class="dy-t">${icon('dungYen')}<span><b>Hình tự zoom / lia?</b> Kiểu đang ${esc(o.join(' + '))}: tay rung trong clip cũng bị phóng to theo.</span></span>
    <button type="button" class="btn small primary" data-dy-a="dung-yen" data-tip="Chuyển động cả video = Đứng yên, mở đầu không đập zoom (Ctrl+Z để bỏ). Cảnh đặt chuyển động riêng giữ nguyên.">${icon('dungYen')}Đứng yên</button></div>`;
}
function hinhDungYen(c) { return goiYDungYen('canh'); }
function datDungYen() {
  if (!S.plan) return;
  const md = kieuDung('mo_dau');
  doi(p => { p.kieu.chuyen_dong = 'dung_yen'; ghimKieu(p, 'chuyen_dong'); if (DY_MO.includes(md)) { p.kieu.mo_dau = 'thuong'; ghimKieu(p, 'mo_dau'); } });
  const rieng = S.plan.canh.filter(c => c.dong && c.dong !== 'dung_yen').length;
  toast('Đã đặt Đứng yên' + (DY_MO.includes(md) ? ' + mở đầu thường' : '') + (rieng ? ' (' + rieng + ' cảnh có chuyển động riêng vẫn giữ)' : '') + ' · Ctrl+Z để bỏ');
}
$('#pane').addEventListener('click', e => { const b = e.target.closest('[data-dy-a]'); if (b && !b.disabled && b.dataset.dyA === 'dung-yen') datDungYen(); });
