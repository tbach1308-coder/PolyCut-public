/* ============================== SỬA LỖI r29 (10/11, theo báo cáo soi sb33 /home/claude/sb33/BAO-CAO.md) ==============================
   L1  Timeline cuộn dọc: cuộn dọc chuyển từ .tlbody sang #tls (cả 2 chiều) -> thước thời gian ghim trên (CSS sticky), tên làn đi theo
       (translateY), vạch đỏ giữ mũi tên trên thước, thanh cuộn dọc mỏng thấy được, nút "↓ còn N làn" / "↑ Cảnh" khi có làn khuất,
       Shift + lăn chuột = cuộn dọc. (dev/_mod-quet.js, _mod-tach-am.js đổi theo: đọc scrollTop của #tls.)
   L4  2 cửa sổ: cứ 10 giây (và lúc cửa sổ được bấm vào) hỏi /api/sua-tay/moc; cửa sổ khác đã ghi bản mới hơn thì băng rôn vàng
       "Cửa sổ khác đã giữ bản của họ…" + Tải bản mới / Giữ bản ở đây, dòng lưu không còn "Đã lưu".
   L5  Thông báo nổi (toast) đặt ở đáy khung xem (trên thanh ▶), không đè hàng Xem trước / Khung / cảnh báo / ✕ mẫu.
   A12 Bấm 1 câu phụ đề trên timeline / "+ Câu, + Nhãn ở vạch đỏ" -> con trỏ vào ngay ô chữ.
   A13 Tên video có dấu: hiện tên đẹp (ten_dep từ máy chủ), thư mục vẫn slug.
   A14 Thu nhỏ hết cỡ: không nhỏ hơn mức "vừa khung" (khối không chồng nhau), khối cảnh hẹp nhất 8px.
   A16 Thẻ kết gõ 0 giây: báo "ít nhất 1,5 giây" thay vì lặng lẽ thành 3,6.
   N7  thanh chữ hẹp: không "t…". N8 / câu chữ: "Chữ động dựng sẵn (chỉ khi dựng bằng Premiere)",
       "Trộn chuyển cảnh", "Gõ việc cần Claude làm trước đã", ước giờ bản nháp theo độ dài video.
   Chỉ thêm file này + _mod-sua-r29.css (nạp sau _mod-r25-tl, trước _mod-tach-am): bọc hàm sẵn có, không thêm khoá kế hoạch. */
(function () {
  if (typeof veTimeline !== 'function' || !document.getElementById('tl')) return;
  const tl = $('#tl'), tls = $('#tls'), tlin = $('#tlin'), tnames = $('#tnames');
  const rulerH = () => ($('#ruler') || {}).offsetHeight || 22;

  /* ================= (L1) cuộn dọc trong #tls: tên làn đi theo, vạch đỏ giữ mũi tên, dấu còn làn khuất ================= */
  const nutDuoi = document.createElement('button'), nutTren = document.createElement('button');
  nutDuoi.type = nutTren.type = 'button'; nutDuoi.className = 'r29-lan duoi'; nutTren.className = 'r29-lan tren'; nutDuoi.hidden = nutTren.hidden = true;
  nutDuoi.dataset.tip = 'Còn làn phía dưới: bấm để cuộn xuống (hoặc Shift + lăn chuột trên timeline)'; nutTren.dataset.tip = 'Làn phía trên đang khuất: bấm để cuộn lên';
  tl.append(nutDuoi, nutTren);
  nutDuoi.addEventListener('click', () => { tls.scrollTop = tls.scrollHeight; });
  nutTren.addEventListener('click', () => { tls.scrollTop = 0; });
  function tenLan() {   // [{ten, top, bot}] theo tên làn đang hiện
    return $$('#tnames > span').filter(s => s.offsetParent !== null && s.textContent.trim()).map(s => ({ten: s.textContent.trim(), top: parseFloat(s.style.top) || 0, bot: (parseFloat(s.style.top) || 0) + (parseFloat(s.style.height) || s.offsetHeight || 0)}));
  }
  function veCuon() {
    const st = tls.scrollTop, H = tls.clientHeight;
    tnames.style.transform = st ? `translateY(${-st}px)` : '';
    const pl = $('#phl'); if (pl) pl.style.top = st + 'px';   // mũi tên đỏ luôn nằm trên thước
    const co = tls.scrollHeight > H + 2;
    if (!co) { nutDuoi.hidden = nutTren.hidden = true; return; }
    const ls = tenLan(), duoi = ls.filter(l => l.bot > st + H + 3).map(l => l.ten), tren = ls.filter(l => l.top < st + rulerH() - 3 && l.bot <= st + rulerH() + 6).map(l => l.ten);
    const gon = s => s.charAt(0) + s.slice(1).toLowerCase();
    nutDuoi.hidden = !duoi.length; if (duoi.length) nutDuoi.innerHTML = `↓ <b>còn ${duoi.length} làn</b> · ${esc(duoi.map(gon).join(', '))}`;
    nutTren.hidden = !tren.length; if (tren.length) nutTren.innerHTML = `↑ ${esc(tren.map(gon).join(', '))}`;
  }
  tls.addEventListener('scroll', veCuon, {passive: true});
  addEventListener('resize', veCuon);
  // Shift + lăn: cuộn dọc (lăn thường = cuộn ngang như cũ, Ctrl + lăn = phóng)
  tls.addEventListener('wheel', e => {
    if (!e.shiftKey || e.ctrlKey || e.metaKey) return;
    if (tls.scrollHeight <= tls.clientHeight + 2) return;
    e.preventDefault(); e.stopImmediatePropagation(); tls.scrollTop += (e.deltaY || e.deltaX);
  }, {passive: false, capture: true});
  (window.PHIM_TAT = window.PHIM_TAT || []).push({id: 'cuon-doc', nhom: 'Timeline', phim: ['Shift+Lăn chuột'], ten: 'Cuộn timeline lên / xuống (khi có nhiều làn)'});

  /* ================= (A14) thu nhỏ hết cỡ = vừa khung; (N7) thanh chữ hẹp ================= */
  function ppsVua() { const w = tls.clientWidth - 40, T = (S.view || {}).T || (S.plan ? tongT() : 0); return w > 50 && T > 0 ? w / T : 8; }
  const gocDatPps = datPps;
  datPps = function (p, neoT, neoX) { const m = Math.min(400, Math.max(ppsVua(), 2)); if (p < m) p = m; return gocDatPps.call(this, p, neoT, neoX); };
  const gocVua = vuaKhung;
  vuaKhung = function () { const r = gocVua.apply(this, arguments); try { veCuon(); } catch (e) {} return r; };
  const bZo = $('#bZo'); if (bZo) bZo.dataset.tip = 'Thu nhỏ timeline (Ctrl −) · nhỏ nhất = cả video vừa khung';
  function chuHep() {   // thanh < 40px: bỏ "…" vô nghĩa, có chỗ trống bên phải (cùng hàng) thì cho chữ tràn ra
    ['#tChu', '#tPd'].forEach(id => {
      const bars = $$(id + ' > .bar[data-k]'); if (!bars.length) return;
      const theoHang = {};
      bars.forEach(b => { b.classList.remove('r29-ngan', 'r29-tran'); (theoHang[b.style.top] = theoHang[b.style.top] || []).push(b); });
      Object.values(theoHang).forEach(ds => {
        ds.sort((a, b) => parseFloat(a.style.left) - parseFloat(b.style.left));
        ds.forEach((b, i) => {
          const w = parseFloat(b.style.width) || 0; if (w >= 40) return;
          b.classList.add('r29-ngan');
          const sau = ds[i + 1], l = parseFloat(b.style.left) || 0, trong = sau ? parseFloat(sau.style.left) - (l + w) : 1e9;
          const can = b.scrollWidth - b.clientWidth;
          if (can > 0 && trong > can + 10) b.classList.add('r29-tran');
        });
      });
    });
  }
  queueMicrotask(() => {   // sau lớp bọc của _mod-r25-tl (cũng queueMicrotask, nạp trước): làn gọn xếp xong mới đo
    const goc = veTimeline;
    veTimeline = function () { const r = goc.apply(this, arguments); try { chuHep(); veCuon(); } catch (e) { console.error(e); } return r; };
    if (S.plan) veTimeline();
  });

  /* ================= (L5) toast ở đáy khung xem ================= */
  const gocToast = toast;
  toast = function (m, err) {
    const r = gocToast.apply(this, arguments);
    try {
      const t = $('.toast'), st = $('#stage'), cot = st && st.closest('.pcol'); if (!t || !st || !cot || $('#edit').hidden) return r;
      const sr = st.getBoundingClientRect(), cr = cot.getBoundingClientRect(); if (sr.width < 120 || sr.height < 120) return r;
      t.classList.add('r29-stage');
      t.style.maxWidth = Math.max(160, cr.width - 24) + 'px';   // rộng theo cả cột khung xem (khung 9:16 ở 1366 chỉ ~220px), chữ xuống dòng
      const w = t.offsetWidth;
      t.style.left = Math.round(cr.left + (cr.width - w) / 2) + 'px';
      t.style.top = Math.round(sr.bottom - t.offsetHeight - 10) + 'px';
    } catch (e) {}
    return r;
  };

  /* ================= (L4) bên bị đè: hỏi mốc bản sửa dở trên đĩa ================= */
  let hoiMoc = 0;
  async function kiemMoc() {
    if (!S.plan || !S.v || S.xungDot || document.hidden || $('#edit').hidden) return;
    try {
      const r = await api('/api/sua-tay/moc?v=' + encodeURIComponent(S.v));
      if (!r || !S.plan || S.xungDot) return;
      if (r.phien && r.phien !== PHIEN && +r.luc > (+S.moc || 0) + 1e-6) { S.xungDot = true; S.r29BiDe = {luc: +r.luc}; veBanner(); if (typeof veLuu === 'function') veLuu(); }
    } catch (e) {}
  }
  setInterval(kiemMoc, 10000);
  addEventListener('focus', () => { if (Date.now() - hoiMoc > 2000) { hoiMoc = Date.now(); kiemMoc(); } });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) kiemMoc(); });
  const gocBanner = veBanner;
  veBanner = function () {
    const r = gocBanner.apply(this, arguments);
    try {
      if (!S.xungDot) S.r29BiDe = null;
      if (S.xungDot && S.r29BiDe && (S.banSua || 0) === (S.banLuu || 0)) {   // bên này chưa sửa gì thêm: nói đúng chuyện (bản ở đây cũ rồi), không nói "phần anh sửa chưa lưu"
        const b = $('#bn .banner.err:has(#bXdTai)') || $$('#bn .banner').find(x => x.querySelector('#bXdTai'));
        if (b) { b.className = 'banner r29-bide'; const gio = new Date(S.r29BiDe.luc * 1000).toLocaleTimeString('vi-VN', {hour: '2-digit', minute: '2-digit'});
          b.innerHTML = `Cửa sổ khác đã giữ bản của họ lúc ${esc(gio)}: bản đang mở ở đây <b>không còn là bản mới nhất</b>. <button class="btn small primary" id="bXdTai">Tải bản mới</button><button class="btn small" id="bXdGiu">Giữ bản ở đây (đè bên kia)</button>`;
          $('#bXdTai').onclick = () => { S.undo = []; S.xungDot = false; S.r29BiDe = null; moVideo(); };
          $('#bXdGiu').onclick = async () => { await luuNhap(true); if (!S.xungDot) { S.r29BiDe = null; toast('Đã lưu bản ở cửa sổ này'); } }; }
      }
    } catch (e) { console.error(e); }
    return r;
  };

  /* ================= (N5) ghi chú đầu tab Kiểu: câu đầu đủ (xuống dòng), phần dài sau dấu ":" vào tooltip đã có ================= */
  // dev/_mod-ben-phai.js làm dòng này bằng MutationObserver (sau veBen) -> cũng theo dõi #pane, chỉ sửa 1 lần mỗi lần vẽ (data-r29)
  new MutationObserver(() => {
    try {
      $$('#pane > p.note[data-bp="1dong"] > span').forEach(sp => {
        const t = sp.textContent; if (t.length <= 110 || sp.dataset.r29) return;
        const i = t.indexOf(': '); if (i < 20) return;
        sp.dataset.r29 = '1'; sp.textContent = t.slice(0, i) + ' (rê chuột để đọc thêm).';
      });
    } catch (e) {}
  }).observe($('#pane'), {childList: true, subtree: true});

  /* ================= (A12) con trỏ vào ô chữ khi bấm câu phụ đề trên timeline ================= */
  function focusO(k) {
    const o = $(`#pane .it[data-row="${CSS.escape(k)}"] textarea, #pane .it[data-row="${CSS.escape(k)}"] input`);
    if (o && document.activeElement !== o) { o.focus(); try { const n = o.value.length; o.setSelectionRange(n, n); } catch (e) {} }
  }
  $('#tPd').addEventListener('click', e => {
    const b = e.target.closest('.bar[data-k]'); if (!b || !b.dataset.k || e.ctrlKey || e.shiftKey || e.metaKey) return;
    if (window.TL25 && TL25.keo && TL25.keo()) return;
    const k = b.dataset.k; setTimeout(() => { if (S.sel.k === k && S.tab === 'pd') focusO(k); }, 60);
  });
  // "+ Câu / + Nhãn / + Thẻ giá ở vạch đỏ" trong bảng phải: bảng vẽ lại 2 lần (doi -> veBen, rồi bản xem về -> veBen(false) giữ ô đang gõ);
  // nếu ô chưa được focus (bảng vẽ lại muộn) thì thử lại 1 lần nữa
  const gocONhap = oNhap;
  oNhap = function (k, tab, chon) {
    const r = gocONhap.apply(this, arguments);
    setTimeout(() => { const ae = document.activeElement; if (!ae || !$('#pane').contains(ae) || !/INPUT|TEXTAREA/.test(ae.tagName)) { const o = $(chon || `#pane .it[data-row="${CSS.escape(k)}"] input, #pane .it[data-row="${CSS.escape(k)}"] textarea`); if (o) { o.focus(); o.select(); } } }, 220);
    return r;
  };

  /* ================= (A13) tên đẹp · (câu chữ) tên kiểu dễ hiểu ================= */
  const TEN_PR = {mov: 'Chữ động dựng sẵn', keyframe: 'Chữ động keyframe'};
  window.R29_TEN_PR = TEN_PR;
  const gocMoVideo = moVideo;
  moVideo = async function () {
    const r = await gocMoVideo.apply(this, arguments);
    try {
      const d = S.info || {};
      if (d.ten_dep && $('#ten')) { $('#ten').textContent = d.ten_dep; document.title = d.ten_dep + ' · Sửa tay'; baoCha('mo', {v: S.v, ten: d.ten_dep}); }
      (d.kieu_ds || []).forEach(m => (m.ds || []).forEach(x => { if (x.v === 'tron_poly') x.ten = 'Trộn chuyển cảnh (nhiều kiểu xen kẽ)'; }));
    } catch (e) {}
    return r;
  };

  /* ================= (A16) thẻ kết gõ số giây ngoài 1,5–6: báo ================= */
  $('#pane').addEventListener('change', e => {
    const o = e.target; if (!o || o.dataset.f !== 'ket_giay') return;
    const g = parseFloat(String(o.value).replace(',', '.'));
    if (!isFinite(g)) return;
    if (g < 1.5) toast('Thẻ kết hiện ít nhất 1,5 giây (đã đặt 1,5 giây)', true);
    else if (g > 6) toast('Thẻ kết hiện nhiều nhất 6 giây (đã đặt 6 giây)', true);
  }, true);

})();
