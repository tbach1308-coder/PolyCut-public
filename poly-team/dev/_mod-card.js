/* ============================== CARD ĐỒ HOẠ (10/11, anh: "poly sẽ chạy bằng card trên máy để mượt" / "app exe sẽ tự dò và sài card máy được cài")
   Máy nào cài app cũng tự dò card (NVIDIA / Intel / AMD) lúc mở app (máy chủ card.py, luồng nền) và dùng luôn để đọc clip + xuất video;
   không có / card lỗi thì CPU, bản xuất không mất. Trang chỉ HIỆN + cho tắt:
   - hộp Xuất video: ở hàng nút cuối (bên trái Huỷ / Xuất video, KHÔNG thêm hàng: hộp vẫn vừa màn 1366×768) 1 dòng trạng thái
     ("Xuất bằng card NVIDIA GeForce …" / "Xuất bằng CPU (máy không có card dùng được)" / "Đang dò card…") + (i) giải thích ngắn + máy này
     dùng gì + công tắc "Dùng card đồ hoạ" Tự động / Tắt (ghi config.json "ma_hoa");
   - tab Bản xuất: cùng dòng trạng thái dưới hàng nút Xuất; lần xuất xong thêm 1 dòng nhỏ "Lần này: mã hoá bằng card …, đọc clip bằng …".
   GET /api/sua-tay/card (đang dò thì hỏi lại mỗi 2s tới khi xong), POST {che_do}. Chỉ thêm file này + _mod-card.css: bọc moXuat / benBan. */
(function () {
  if (typeof moXuat !== 'function' || typeof benBan !== 'function') return;
  const C = {tt: null, hen: 0, gui: false};
  const TIP = 'Máy có card đồ hoạ (NVIDIA, Intel, AMD) thì app tự dùng card để đọc clip và xuất video: nhanh hơn, máy đỡ đơ. '
    + 'Card lỗi giữa chừng thì tự làm lại bằng CPU, video vẫn ra đủ. Tắt = luôn dùng CPU như trước. App tự dò lại khi đổi card / cập nhật driver.';
  const lop = t => !t ? 'dang' : t.tt === 'dang_do' ? 'dang' : t.tt === 'card' ? 'card' : t.tt === 'tat' ? 'tat' : 'cpu';
  const tip = t => TIP + (t && t.chi_tiet ? ' ' + t.chi_tiet : '');
  function dongHtml(t) {
    const x = t || {dong: 'Đang dò card…'};
    return `<span class="cd-tt ${lop(t)}" role="status" aria-live="polite"><i class="cd-cham" aria-hidden="true"></i><span class="cd-chu">${esc(x.dong)}</span></span>`
      + `<button type="button" class="tt-i cd-i" data-tip="${esc(tip(t))}" aria-label="Giải thích: ${esc(tip(t))}">${icon('thongTin')}</button>`;
  }
  function swHtml(t) {
    const cd = (t && t.che_do) || 'auto';
    return `<span class="seg2 cd-sw" role="group" aria-label="Dùng card đồ hoạ">`
      + `<button type="button" data-cd="auto" class="${cd === 'auto' ? 'on' : ''}" aria-pressed="${cd === 'auto'}" data-tip="Dùng card đồ hoạ: Tự động — có card dùng được thì dùng (mặc định)">Tự động</button>`
      + `<button type="button" data-cd="cpu" class="${cd === 'cpu' ? 'on' : ''}" aria-pressed="${cd === 'cpu'}" data-tip="Dùng card đồ hoạ: Tắt — luôn đọc clip và xuất bằng CPU">Tắt</button></span>`;
  }
  function veLai() {   // vẽ lại mọi chỗ đang hiện (hộp Xuất, tab Bản xuất)
    $$('.cd-dong').forEach(el => { const h = dongHtml(C.tt); if (el._h !== h) { el.innerHTML = h; el._h = h; } });
    $$('.cd-sw-o').forEach(el => { const h = swHtml(C.tt); if (el._h !== h) { el.innerHTML = h; el._h = h; } });
  }
  async function lay() {
    clearTimeout(C.hen);
    try { C.tt = await api('/api/sua-tay/card'); } catch (e) { if (!C.tt) C.tt = {tt: 'loi', dong: 'Xuất bằng CPU (chưa dò được card)', che_do: 'auto', chi_tiet: ''}; }
    veLai();
    if (C.tt && C.tt.dang_do && C.tt.che_do !== 'cpu') C.hen = setTimeout(lay, 2000);
  }
  async function doi(cd) {
    if (C.gui || (C.tt && C.tt.che_do === cd)) return;
    C.gui = true;
    try { C.tt = await api('/api/sua-tay/card', {che_do: cd}); veLai();
      toast(cd === 'cpu' ? 'Đã tắt card đồ hoạ: lần xuất sau dùng CPU' : 'Đã bật Tự động: có card dùng được thì xuất bằng card');
      if (C.tt.dang_do) { clearTimeout(C.hen); C.hen = setTimeout(lay, 2000); } }
    catch (e) { toast('Chưa đổi được: ' + e.message, true); }
    finally { C.gui = false; }
  }
  document.addEventListener('click', e => { const b = e.target.closest && e.target.closest('.cd-sw [data-cd]'); if (!b) return; e.stopPropagation(); doi(b.dataset.cd); });
  window.cardTt = () => C.tt;   // cho bài thử

  // hộp Xuất video: đầu hàng nút cuối (bên trái Huỷ / Xuất video) — không thêm hàng, hộp không cao thêm
  const goc = moXuat;
  moXuat = function () {
    const n0 = $$('.mbg').length, r = goc.apply(this, arguments);
    try {
      const bg = $$('.mbg').pop(), m = bg && $$('.mbg').length > n0 ? bg.querySelector('.mbox') : null, ok = m && m.querySelector('#xOk'),
        acts = ok && ok.closest('.acts');
      if (acts) {
        acts.insertAdjacentHTML('afterbegin', `<div class="cd-hang" id="cdHang"><span class="cd-dong">${dongHtml(C.tt)}</span><span class="cd-sw-o">${swHtml(C.tt)}</span></div>`);
        veLai(); lay();
      }
    } catch (e) { console.error(e); }
    return r;
  };
  // tab Bản xuất: dòng trạng thái dưới hàng nút + "Lần này: …" khi vừa xuất xong
  const gocBan = benBan;
  benBan = function () {
    let h = gocBan.apply(this, arguments);
    try {
      const x = S.xuat, lan = x && !x.dang && !x.loi && x.card && x.card.chu
        ? `<p class="note cd-lan${x.card.lui ? ' lui' : ''}">Lần này: ${esc(x.card.chu)}</p>` : '';
      const j = h.indexOf('data-a="xuat-dd"'), k = j >= 0 ? h.indexOf('</div>', j) : -1;   // ngay sau hàng nút Xuất bản nháp / Xuất video / Định dạng…
      if (k >= 0) {
        h = h.slice(0, k + 6) + `<div class="cd-ban"><span class="cd-dong">${dongHtml(C.tt)}</span></div>` + h.slice(k + 6);
        const x1 = lan ? h.indexOf('class="note okt"', k) : -1, x2 = x1 >= 0 ? h.indexOf('</p>', x1) : -1;   // "Lần này" ngay dưới dòng "Xong …"
        if (x2 >= 0) h = h.slice(0, x2 + 4) + lan + h.slice(x2 + 4);
      }
      setTimeout(() => { veLai(); if (!C.tt) lay(); }, 0);
    } catch (e) { console.error(e); }
    return h;
  };
  setTimeout(lay, 400);   // mở trang: hỏi 1 lần (máy chủ dò nền từ lúc mở app); đang dò thì hỏi tiếp mỗi 2s
})();
