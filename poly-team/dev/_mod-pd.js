/* ============================== PHỤ ĐỀ TỰ ĐỘNG TRÊN LÀN PHỤ ĐỀ (4/11) ==============================
   Anh: "chưa có phụ đề tự động". Nút có sẵn (tab Phụ đề › "Tạo phụ đề từ lời nói", Thư viện › Chữ) nhưng khó thấy.
   Giờ làn Phụ đề trống (và video không dùng giọng AI) thì có ô "+ Phụ đề tự động" giống ô "+ Giọng đọc AI":
   bấm = máy nghe tiếng Việt trên máy nghe lời trong các cảnh rồi tạo phụ đề (taoPhuDe), Ctrl+Z được. */
(function () {
  if (typeof veTimeline !== 'function') return;
  const goc = veTimeline;
  veTimeline = function () { const r = goc.apply(this, arguments); try { nutPdTuDong(); } catch (e) {} return r; };
  function nutPdTuDong() {
    const t = document.getElementById('tPd'); if (!t || !S.plan || S.plan.giong || (S.plan.phu_de || []).length) return;
    const dang = !!(S.ng && S.ng.dang);
    t.insertAdjacentHTML('beforeend', `<div class="bar pd trong pd-tu-dong${dang ? ' dang' : ''}" data-t="0" style="top:2px;left:0" data-tip="${dang ? 'Đang nghe lời nói trong các cảnh…' : 'Tạo phụ đề tự động từ lời nói trong clip (máy nghe trên máy, không cần mạng). Ctrl+Z để bỏ'}">${icon('them')}<span>${dang ? 'Đang nghe lời nói…' : 'Phụ đề tự động'}</span></div>`);
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('#tPd .pd-tu-dong'); if (!b) return;
    e.stopPropagation(); e.preventDefault();
    if (S.ng && S.ng.dang) return;
    b.classList.add('dang'); const s = b.querySelector('span'); if (s) s.textContent = 'Đang nghe lời nói…';
    taoPhuDe(false);
  }, true);
})();

/* ============================== CLAUDE SOÁT PHỤ ĐỀ (4/11) ==============================
   Anh: "phụ đề tự động có tăng độ chính xác nghe giọng nói được không". Máy nghe trên máy hay sai tên máy / số / giá
   (từ điển của tiệm sửa được phần lớn số, giá, tên máy hay gặp). Nút "Claude soát phụ đề" (tab Phụ đề): gửi các câu +
   ngữ cảnh video cho Claude Code trên máy (như Nhờ Claude: claude.exe của tài khoản, không API) -> Claude chỉ sửa chữ
   nghe sai. Mỗi lần bấm = 1 lượt Claude. Giờ từng chữ giữ nguyên (máy chủ căn lại, soat_pd.py). Áp thành 1 bước Ctrl+Z;
   câu Claude sửa có dòng nhỏ "Claude sửa từ: …" để anh nghe kiểm. Công tắc "Tự soát sau khi nghe" (nhớ trên máy này). */
(function () {
  if (typeof benPd !== 'function' || typeof veBen !== 'function') return;
  S.sp = {dang: false};
  const KHOA = 'poly-pd-tu-soat';
  const tuSoat = () => { try { return localStorage.getItem(KHOA) === '1'; } catch (e) { return false; } };
  let spT;
  function khoiSoat() {
    if (!S.plan || S.plan.giong) return '';
    const n = (S.plan.phu_de || []).length, sp = S.sp || {}, ngDang = !!(S.ng && S.ng.dang);
    return `<div class="row soat-pd"><button class="btn small" data-a="soat-pd" ${!n || sp.dang || ngDang ? 'disabled' : ''} title="Claude Code trên máy đọc các câu phụ đề, sửa chữ máy nghe sai (tên máy, số, giá) theo ngữ cảnh video. Mỗi lần bấm = 1 lượt Claude. Ctrl+Z để bỏ">${icon('ai')}<span>Claude soát phụ đề</span></button>`
      + `<label class="chk" title="Nghe xong lời nói thì tự gọi Claude soát luôn (mỗi lần = 1 lượt Claude)"><input type="checkbox" data-soat-tu ${tuSoat() ? 'checked' : ''}> Tự soát sau khi nghe</label>`
      + `<button type="button" class="btn small" data-a="soat-pd-tu-dien" title="Mở file từ điển của tiệm (Notepad): thêm tên máy hay nói, hoặc dòng 'chữ nghe sai => chữ đúng'. Lưu file là lần nghe sau dùng ngay">Từ điển của tiệm…</button></div>`
      + (sp.dang ? `<div class="sptt"><span class="dot"></span><span class="sp-b">${esc(sp.buoc || 'Claude đang soát…')}</span><span class="sp"></span><span class="tg">${tg(sp.giay || 0, false)}</span><button type="button" class="btn small" data-a="soat-pd-dung">Dừng</button></div>`
        : sp.loi ? `<p class="note err">${esc(sp.loi)}</p>` : sp.ghi ? `<p class="note soat-ghi">${esc(sp.ghi)}</p>` : '');
  }
  function veSoat() {
    if (S.tab !== 'pd') return;
    const pane = document.getElementById('pane'); if (!pane) return;
    pane.querySelectorAll('.soat-pd, .sptt, .soat-ghi, .why.soat').forEach(x => x.remove());
    const h = khoiSoat(); if (!h) return;
    const dau = pane.querySelector('.row');
    let sau = dau; while (sau && sau.nextElementSibling && sau.nextElementSibling.matches('.ngtt, .note.err')) sau = sau.nextElementSibling;
    if (sau) sau.insertAdjacentHTML('afterend', h); else pane.insertAdjacentHTML('afterbegin', h);
    const doi_ = (S.sp || {}).doi || {};
    for (const k in doi_) {
      const it = (S.plan.phu_de || []).find(x => x._k === k), r = pane.querySelector(`[data-row="${k}"]`);
      if (it && r && String(it.chu || '').trim() !== doi_[k]) r.insertAdjacentHTML('beforeend', `<span class="why soat">Claude sửa từ: «${esc(doi_[k])}»</span>`);
    }
  }
  const gocBen = veBen;
  veBen = function (full) { const r = gocBen.apply(this, arguments); try { if (full !== false || !document.querySelector('#pane .soat-pd')) veSoat(); } catch (e) {} return r; };
  async function soatPd(tuDong) {
    if (!S.plan || S.plan.giong || (S.sp && S.sp.dang) || !(S.plan.phu_de || []).length) return;
    S.sp = {dang: true, buoc: 'Đang gửi cho Claude…', giay: 0, tuDong};
    if (S.tab !== 'pd') { S.tab = 'pd'; veTabs(); }
    veBen(true);
    try { const r = await api('/api/sua-tay/soat-pd', {v: S.v, plan: S.plan}); S.sp.ma = r.ma; theoSoat(); }
    catch (e) { S.sp = {dang: false, loi: e.message}; veBen(true); toast(e.message, true); }
  }
  async function theoSoat() {
    clearTimeout(spT);
    let r; try { r = await api('/api/sua-tay/soat-pd?ma=' + encodeURIComponent(S.sp.ma)); } catch (e) { spT = setTimeout(theoSoat, 1500); return; }
    if (r.dang) { S.sp.buoc = r.buoc; S.sp.giay = r.giay_da || 0;
      const el = document.querySelector('#pane .sptt'); if (el) { el.querySelector('.sp-b').textContent = r.buoc || ''; el.querySelector('.tg').textContent = tg(S.sp.giay, false); }
      spT = setTimeout(theoSoat, 1000); return; }
    if (!r.kq) { S.sp = {dang: false, loi: r.loi || 'Claude soát bị lỗi'}; veBen(true); return toast(S.sp.loi, true); }
    apSoat(r.kq);
  }
  function apSoat(kq) {
    const pd = S.plan.phu_de || [];
    // chỉ áp câu anh chưa sửa tay trong lúc Claude soát
    const sua = (kq.sua || []).filter(s => pd.some(p => p._k === s.k && String(p.chu || '').trim() === s.cu));
    const bo = (kq.sua || []).length - sua.length;
    if (!sua.length) {
      S.sp = {dang: false, ghi: (kq.sua || []).length ? 'Claude có đề xuất nhưng anh đã sửa tay các câu đó, không áp' : 'Claude soát xong: không thấy chữ nào nghe sai (' + (kq.so_cau || pd.length) + ' câu)'};
      veBen(true); return toast(S.sp.ghi);
    }
    S.sp = {dang: false, ghi: `Claude sửa ${sua.length}/${kq.so_cau || pd.length} câu${kq.ghi_chu ? ': ' + kq.ghi_chu : ''}${bo ? ` (bỏ ${bo} câu anh vừa sửa tay)` : ''}. Nghe lại kiểm, Ctrl+Z để bỏ.`,
      doi: Object.fromEntries(sua.map(s => [s.k, s.cu]))};
    doi(p => { for (const s of sua) { const it = (p.phu_de || []).find(x => x._k === s.k); if (!it) continue; it.chu = s.chu; if (it._neo && Array.isArray(s.tu) && s.tu.length) it._neo.tu = s.tu; } });
    toast('Claude sửa ' + sua.length + ' câu phụ đề (Ctrl+Z để bỏ)');
  }
  window.soatPd = soatPd;
  // nghe xong (tạo phụ đề thành công) + công tắc bật -> tự soát
  if (typeof theoNghe === 'function') {
    const gocTheo = theoNghe;
    theoNghe = async function () {
      const dang = !!(S.ng && S.ng.dang), pdTruoc = S.plan && S.plan.phu_de;
      const r = await gocTheo.apply(this, arguments);
      try { if (dang && S.ng && !S.ng.dang && !S.ng.loi && S.plan && S.plan.phu_de !== pdTruoc && (S.plan.phu_de || []).length) {
        if (S.sp) S.sp.doi = null;
        if (tuSoat()) setTimeout(() => soatPd(true), 300); else veBen(true);
      } } catch (e) {}
      return r;
    };
  }
  document.addEventListener('click', e => {
    const b = e.target.closest('#pane [data-a="soat-pd"], #pane [data-a="soat-pd-dung"], #pane [data-a="soat-pd-tu-dien"]'); if (!b) return;
    e.stopPropagation(); e.preventDefault();
    if (b.dataset.a === 'soat-pd') return soatPd(false);
    if (b.dataset.a === 'soat-pd-tu-dien') return api('/api/sua-tay/soat-pd-tu-dien', {}).then(r => toast('Từ điển của tiệm: ' + r.p + ' — thêm từ rồi lưu file, lần nghe sau dùng ngay')).catch(x => toast(x.message, true));
    if (S.sp && S.sp.ma) api('/api/sua-tay/soat-pd-dung', {ma: S.sp.ma}).catch(() => {});
  }, true);
  document.addEventListener('change', e => {
    const c = e.target.closest && e.target.closest('#pane [data-soat-tu]'); if (!c) return;
    e.stopPropagation();
    try { localStorage.setItem(KHOA, c.checked ? '1' : '0'); } catch (x) {}
    toast(c.checked ? 'Đã bật: nghe xong lời nói thì Claude tự soát phụ đề' : 'Đã tắt tự soát sau khi nghe');
  }, true);
})();
