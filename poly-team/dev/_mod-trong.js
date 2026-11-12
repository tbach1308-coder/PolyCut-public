/* ============================== VIDEO TRỐNG (0 cảnh) — 4/11 18:14 ==============================
   Anh gửi ảnh timeline chỉ còn 1 cảnh: "có thể xóa hết video không cần chừa lại". Giờ xoá được cả cảnh cuối (Delete, menu, quét chọn,
   Nhờ Claude xoa_canh, script Tiện ích) — 1 bước Ctrl+Z như mọi lần xoá. Video 0 cảnh:
   - timeline: ô gợi ý "Kéo clip từ Thư viện vào đây (hoặc bấm clip)" ở chỗ làn Cảnh (bấm = mở Thư viện › Clip; kéo clip thả lên = thêm);
   - khung xem: chữ gợi ý thay cho khung hình cũ; vạch đỏ về 0 (máy chủ trả T = 0); phát / tua không lỗi;
   - tab Cảnh: "Chưa có cảnh"; chữ / phụ đề / thẻ kết vẫn giữ trong kế hoạch (bảng phải ghi ẩn vì chưa có cảnh);
   - tự lưu bản sửa dở được, F5 mở lại vẫn trống (máy chủ: sua_tay.kiem_ke_hoach(cho_trong) cho XEM / LƯU NHÁP, sua_tay_may._xem_trong
     trả bản xem trống, không gọi bộ dựng);
   - Xuất / Xuất bản nháp / mẫu kiểu: nút mờ + báo "Video chưa có cảnh nào, thêm clip trước" (máy chủ cũng chặn xuất 0 cảnh). */
(function () {
  if (typeof veTimeline !== 'function' || !document.getElementById('tCanh')) return;
  const BAO = 'Video chưa có cảnh nào, thêm clip trước';
  const trong = () => !!S.plan && Array.isArray(S.plan.canh) && !S.plan.canh.length;
  window.videoTrong = trong;
  const NUT = ['#bNhap', '#bXuat', '#bXuatDd'];
  function ve() {
    const t = trong();
    document.body.classList.toggle('vd-trong', t);
    // làn Cảnh: ô gợi ý (đặt trong #tlin, ngay chỗ làn Cảnh: veTimeline vẽ lại làn không xoá nó -> không chớp)
    const lan = $('#tlin'), tls = $('#tls');
    let g = $('#trGoiY');
    if (t && lan) {
      if (!g) { g = document.createElement('button'); g.type = 'button'; g.id = 'trGoiY'; g.className = 'tr-goi';
        g.dataset.tip = 'Mở Thư viện › Clip: bấm 1 clip để thêm, hoặc kéo clip thả xuống đây';
        g.innerHTML = icon('clip') + '<span><b>Kéo clip từ Thư viện vào đây</b> (hoặc bấm clip)</span>'; lan.append(g); }
      g.style.width = Math.max(160, tls.clientWidth - 26) + 'px';
    } else if (g) g.remove();
    // khung xem: chữ gợi ý
    const st = $('#stage'); let x = $('#trXem');
    if (t && st && !x) { x = document.createElement('div'); x.id = 'trXem'; x.className = 'tr-xem'; x.setAttribute('role', 'status');
      x.innerHTML = icon('clip') + '<b>Video chưa có cảnh nào</b><span>Bấm 1 clip trong Thư viện bên trái, hoặc kéo clip xuống timeline</span>'; st.append(x); }
    else if (!t && x) x.remove();
    // nút xuất: mờ + gợi ý (không đặt disabled: veXuat của trang tự bật / tắt theo lúc đang dựng)
    NUT.forEach(s => { const b = $(s); if (!b) return;
      if (t) { if (b.dataset.tipTrong == null) b.dataset.tipTrong = b.dataset.tip || ''; b.dataset.tip = BAO; b.classList.add('tr-mo'); b.setAttribute('aria-disabled', 'true'); }
      else if (b.dataset.tipTrong != null) { b.dataset.tip = b.dataset.tipTrong; delete b.dataset.tipTrong; b.classList.remove('tr-mo'); b.removeAttribute('aria-disabled'); } });
    if (t && S.t > 0 && S.view && !S.view.T) { S.t = 0; $('#phl').style.left = '0px'; }   // vạch đỏ về 0
  }
  const gocTl = veTimeline;
  veTimeline = function () { const r = gocTl.apply(this, arguments); try { ve(); } catch (e) {} return r; };
  addEventListener('resize', () => { if (trong()) ve(); });
  // bấm ô gợi ý: mở Thư viện › Clip
  $('#tlin').addEventListener('click', e => { if (!e.target.closest('#trGoiY')) return; e.stopPropagation(); if (typeof moTab === 'function') moTab('clip'); });
  // tab Cảnh khi chưa có cảnh
  if (typeof benCanh === 'function') {
    const gocBen = benCanh;
    benCanh = function () {
      if (!trong()) return gocBen.apply(this, arguments);
      return `<div class="tv-bao tr-ben"><b>Chưa có cảnh</b><span>Video đang trống. Bấm 1 clip trong Thư viện bên trái, hoặc kéo clip xuống timeline để thêm cảnh.
        Chữ, phụ đề vẫn giữ nguyên, thêm cảnh là hiện lại.</span><button type="button" class="btn small primary" data-tr="clip" data-tip="Mở Thư viện › Clip">${icon('clip')}Mở Thư viện › Clip</button>
        <button type="button" class="btn small" data-tr="them" data-tip="Chọn clip trong video hoặc thư mục khác">${icon('them')}Thêm cảnh…</button></div>`;
    };
  }
  $('#pane').addEventListener('click', e => { const b = e.target.closest('[data-tr]'); if (!b) return; e.stopPropagation();
    if (b.dataset.tr === 'clip' && typeof moTab === 'function') moTab('clip'); else if (b.dataset.tr === 'them') themCanh(); });
  // xuất / xuất bản nháp / hộp xuất: báo dễ hiểu thay vì gửi máy chủ
  const chan = f => function () { if (trong()) { toast(BAO, true); return; } return f.apply(this, arguments); };
  if (typeof xuat === 'function') xuat = chan(xuat);
  if (typeof moXuat === 'function') moXuat = chan(moXuat);
  if (typeof xuatNhanh === 'function') xuatNhanh = chan(xuatNhanh);
  // xem mẫu kiểu hình (chuyển cảnh, chuyển động…) cần cảnh để dựng mẫu
  if (typeof xemMau === 'function') { const gocMau = xemMau;
    xemMau = function (m) { if (trong() && !(typeof KIEU_CHU !== 'undefined' && KIEU_CHU.includes(m))) { toast(BAO, true); return; } return gocMau.apply(this, arguments); }; }
})();
