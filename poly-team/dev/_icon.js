/* ============================== BỘ ICON NÉT (3/11) ==============================
   1 bộ SVG nét kiểu Lucide (24×24, nét 1.8, theo màu chữ) thay cho ký tự lẫn kiểu ✂ ⇤ ⇥ ⧉ ⇄ ₫ ≡ ↶ ↷ ⏮ ▶ ⏭
   (trên Windows mấy ký tự đó hay ra emoji màu). icon(ten) -> chuỗi <svg>. */
const IC_P = {
  chuyenC: '<rect x="3" y="6" width="8" height="12" rx="1.5"/><rect x="13" y="6" width="8" height="12" rx="1.5"/><path d="M9 12h6m-2-2 2 2-2 2"/>',
  dongK: '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"/>',
  chia: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
  catDau: '<path d="M4 5v14M20 12H9m4-5-5 5 5 5"/>',
  catCuoi: '<path d="M20 5v14M4 12h11m-4-5 5 5-5 5"/>',
  nhanDoi: '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M4 16V5a1 1 0 0 1 1-1h11"/>',
  thay: '<path d="M8 3 4 7l4 4M4 7h16M16 21l4-4-4-4M20 17H4"/>',
  them: '<path d="M12 5v14M5 12h14"/>',
  xoa: '<path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>',
  nhan: '<path d="M4 7V4h16v3M9 20h6M12 4v16"/>',
  gia: '<path d="M3 12V4h8l9.5 9.5a1.5 1.5 0 0 1 0 2.1l-5.9 5.9a1.5 1.5 0 0 1-2.1 0z"/><circle cx="7.5" cy="7.5" r="1.2"/>',
  pd: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 15h4M14 15h3M7 11h3M13 11h4"/>',
  undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
  redo: '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
  lui: '<path d="M19 20 9 12l10-8z"/><path d="M5 19V5"/>',
  toi: '<path d="m5 4 10 8-10 8z"/><path d="M19 5v14"/>',
  play: '<path d="M7 4.5v15l12-7.5z" fill="currentColor"/>',
  pause: '<rect x="6" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="14" y="5" width="4" height="14" rx="1" fill="currentColor"/>',
  nho: '<path d="M5 12h14"/>', to: '<path d="M12 5v14M5 12h14"/>',
  vua: '<path d="M8 3H5a2 2 0 0 0-2 2v3M21 8V5a2 2 0 0 0-2-2h-3M3 16v3a2 2 0 0 0 2 2h3M16 21h3a2 2 0 0 0 2-2v-3"/>',
  ai: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>',
  ti: '<path d="M13 2 3 14h9l-1 8 10-12h-9z"/>',
  // Thư viện 4 khu (3/11 tối)
  clip: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 7.5h4M3 12h18M3 16.5h4M17 7.5h4M17 16.5h4"/>',
  hieuUng: '<path d="m21.6 3.6-1.2-1.2a1.2 1.2 0 0 0-1.7 0L2.4 18.7a1.2 1.2 0 0 0 0 1.7l1.2 1.2a1.2 1.2 0 0 0 1.7 0L21.6 5.3a1.2 1.2 0 0 0 0-1.7"/><path d="m14 7 3 3M5 6v4M19 14v4M10 2v2M7 8H3M21 16h-4M11 3H9"/>',
  thuMuc: '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2z"/>',
  thuGon: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M16 15l-3-3 3-3"/>',
  moRong: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18M14 9l3 3-3 3"/>',
  dung9: '<rect x="6" y="2" width="12" height="20" rx="2.5"/><path d="M11 18h2"/>',
  mic: '<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0M12 17v5"/>',
  lop: '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5M2 12l10 5 10-5"/>',
  boHet: '<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6M9 9l6 6"/>',
  caiDat: '<path d="M20 7h-9M14 17H5"/><circle cx="17" cy="17" r="3"/><circle cx="7" cy="7" r="3"/>',
  lamMoi: '<path d="M21 12a9 9 0 1 1-2.6-6.4L21 8"/><path d="M21 3v5h-5"/>',
  dauTick: '<path d="M20 6 9 17l-5-5"/>',
  // bảng thuộc tính cảnh + dấu trên timeline (3/11 đêm)
  loa: '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13"/>',
  tatLoa: '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="m22 9-6 6M16 9l6 6"/>',
  catKhung: '<path d="M6 2v14a2 2 0 0 0 2 2h14"/><path d="M18 22V8a2 2 0 0 0-2-2H2"/>',
  giotMau: '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
  giua: '<circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>',
  datLai: '<path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5"/>',
  trai: '<path d="m15 18-6-6 6-6"/>', phai: '<path d="m9 18 6-6-6-6"/>'
};
const icon = k => `<svg class="ic" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC_P[k] || ''}</svg>`;
(() => {
  const dat = (id, k, chu) => { const b = document.getElementById(id); if (!b) return; const kbd = b.querySelector('kbd');
    if (!chu && !b.getAttribute('aria-label')) b.setAttribute('aria-label', b.title || k);
    b.innerHTML = icon(k) + (chu ? `<span>${chu}</span>` : '') + (kbd ? kbd.outerHTML : ''); };
  // công cụ chỉ còn icon (anh 3/11: "thu gọn chỉ còn icon, rê chuột vô hiện ra đó là cái gì"): tên + phím tắt hiện ở ô gợi ý
  // chu = chữ ngắn cạnh icon (3/11 khuya, anh: "cải thiện mấy nút cho thân thiện"): chỉ hiện ở màn ≥ 1500px, màn hẹp vẫn chỉ icon
  const ic = (id, k, ten, phim, chu) => { const b = document.getElementById(id); if (!b) return;
    b.innerHTML = icon(k) + (chu ? `<span class="nut-chu">${chu}</span>` : ''); b.classList.add('ico'); if (chu) b.classList.add('co-chu'); b.removeAttribute('title'); b.setAttribute('aria-label', ten + (phim ? ' (' + phim + ')' : ''));
    b.dataset.tip = ten; if (phim) b.dataset.phim = phim; };
  ic('bChia', 'chia', 'Chia cảnh ở vạch đỏ', 'S', 'Chia'); ic('bCatDau', 'catDau', 'Cắt đầu: bỏ phần trước vạch đỏ', 'Q', 'Cắt đầu'); ic('bCatCuoi', 'catCuoi', 'Cắt cuối: bỏ phần sau vạch đỏ', 'W', 'Cắt cuối');
  ic('bNhanDoi', 'nhanDoi', 'Nhân đôi cảnh', 'Ctrl+D', 'Nhân đôi'); ic('bThay', 'thay', 'Thay clip (giữ chỗ và độ dài)', '', 'Thay'); ic('bThem', 'them', 'Thêm cảnh', '', 'Thêm');
  ic('bXoaCanh', 'xoa', 'Xoá cảnh / mục đang chọn', 'Delete', 'Xoá'); ic('bTNhan', 'nhan', 'Thêm nhãn chữ ở vạch đỏ', 'T', 'Nhãn'); ic('bTGia', 'gia', 'Thẻ giá ở vạch đỏ', 'G', 'Giá');
  ic('bTPd', 'pd', 'Thêm câu phụ đề ở vạch đỏ', 'P', 'Phụ đề'); ic('bVua', 'vua', 'Vừa khung: cả video vừa timeline', 'Ctrl+0');
  ic('bZo', 'nho', 'Thu nhỏ timeline', 'Ctrl −'); ic('bZi', 'to', 'Phóng to timeline', 'Ctrl +');
  ic('bUndo', 'undo', 'Hoàn tác', 'Ctrl+Z'); ic('bRedo', 'redo', 'Làm lại', 'Ctrl+Y'); ic('bLui', 'lui', 'Lùi 1 khung', '←'); ic('bToi', 'toi', 'Tới 1 khung', '→');
  ic('bPlay', 'play', 'Phát / dừng', 'Phím cách');
  dat('bAi', 'ai', 'Nhờ Claude'); dat('bTi', 'ti', 'Tiện ích');
  const zr = document.getElementById('zoomR'); if (zr) { zr.dataset.tip = 'Kéo để phóng to / thu nhỏ timeline'; zr.dataset.phim = 'Ctrl + lăn chuột'; const w = zr.closest('[title]'); if (w) w.removeAttribute('title'); }
})();
/* ô gợi ý khi rê chuột / focus vào nút có data-tip (thay title: hiện nhanh, có phím tắt) */
(() => {
  const T = document.createElement('div'); T.className = 'tip'; T.setAttribute('role', 'tooltip'); document.body.append(T);
  let hen = null, dang = null;
  const e_ = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'})[c]);
  const hien = b => { if (!b.isConnected) return;   // nút vừa bị vẽ lại trong lúc chờ (vd timeline cập nhật): khỏi hiện ô gợi ý ở góc trái trên
    dang = b; T.innerHTML = e_(b.dataset.tip) + (b.dataset.phim ? `<kbd>${e_(b.dataset.phim)}</kbd>` : ''); T.classList.add('on');
    const r = b.getBoundingClientRect(), w = T.offsetWidth, h = T.offsetHeight;
    const x = Math.max(6, Math.min(innerWidth - w - 6, r.left + r.width / 2 - w / 2)); let y = r.top - h - 8; if (y < 6) y = r.bottom + 8;
    T.style.left = x + 'px'; T.style.top = y + 'px'; };
  const an = () => { clearTimeout(hen); dang = null; T.classList.remove('on'); };
  document.addEventListener('mouseover', e => { const b = e.target.closest && e.target.closest('[data-tip]'); if (!b || b === dang) return; clearTimeout(hen); hen = setTimeout(() => hien(b), dang ? 0 : 220); });
  document.addEventListener('mouseout', e => { const b = e.target.closest && e.target.closest('[data-tip]'); if (b && !b.contains(e.relatedTarget)) an(); });
  document.addEventListener('focusin', e => { const b = e.target.closest && e.target.closest('[data-tip]'); if (b && b.matches(':focus-visible')) hien(b); });
  document.addEventListener('focusout', an); document.addEventListener('pointerdown', an, true); addEventListener('scroll', an, true); addEventListener('blur', an);
})();
