/* ============================== DỰNG TỰ ĐỘNG (r38, 11/11/2026) ==============================
   Anh 11/11 10:57: "chức năng edit video tự động" -> chọn "Dựng trọn: thô + tự gắn chữ, nhạc, chuyển cảnh" (làm 2 bước; đây là bước 1).
   Hộp "Video mới từ clip…": nút Dựng tự động cạnh "Tạo và sửa" (Thư viện › Clip có nút mở hộp này đúng thư mục). Bấm clip cầm máy nói
   theo thứ tự -> máy chủ (poly-team/tu_dung.py -> dung_tho.py --bo-kieu) tự: bỏ khoảng lặng, ừ / à, câu nói lại (giữ lần tốt nhất),
   phụ đề IN HOA theo lời nghe + từ điển tiệm, zoom nhấn; rồi tự gắn hook, thẻ giá lúc nghe giá, nhãn từ khoá, chuyển cảnh giữa các clip,
   nhạc nền (đã hạ dưới giọng), thẻ kết — theo BỘ KIỂU (dung-tu-dong/<mã>.json, kho effect). Không tốn lượt Claude.
   Tiến độ 4 bước (nghe lời -> cắt -> gắn chữ -> xong), Huỷ được. Xong: mở video trong trình sửa + bảng tóm tắt (câu dài vào (i)) + nút
   Hoàn tác cả lượt (= về bản trơn như "Tạo và sửa": mỗi clip 1 cảnh; 1 bước Ctrl+Z, Ctrl+Z lần nữa lấy lại bản dựng tự động).
   "Tạo và sửa" thường giữ nguyên mặc định trơn (anh 4/11: "video cho mặc định từ đầu, hiệu ứng thêm sau"). */
const TDG = {bo: null, ma: '', kq: null, hop: null};
const TD_BUOC = ['Nghe lời', 'Cắt', 'Gắn chữ, nhạc, chuyển cảnh', 'Xong'];
const TD_IC = {cat: 'catCuoi', noi_lai: 'thay', hook: 'nhan', gia: 'gia', nhan: 'nhan', zoom: 'vua', chuyen: 'chuyenC', nhac: 'loa', am_thanh: 'loa', pd: 'pd', bo: 'caiDat'};
const TD_GOI = 'Chọn clip cầm máy nói theo thứ tự rồi bấm. App tự: bỏ khoảng lặng, ừ / à, câu nói lại (giữ lần nói tốt nhất), phụ đề IN HOA theo lời nghe, zoom nhấn chỗ giá / pin / GB / tên máy; '
  + 'tự gắn hook, thẻ giá lúc nghe giá (“mười ba triệu chín” → 13TR9), nhãn PIN / GB, chuyển cảnh giữa các clip, nhạc nền hạ dưới giọng, thẻ kết. Chạy trên máy, không tốn lượt Claude. Xong mở luôn để sửa tiếp, có nút Hoàn tác cả lượt.';

/* ---------- nút trong hộp "Video mới từ clip" ---------- */
async function tdTaiBo() {
  if (TDG.bo) return;
  try { TDG.bo = await api('/api/sua-tay/tu-dung/bo'); } catch (e) { TDG.bo = {ds: []}; }
  tdNut();
}
function tdBoChon() { const s = $('#tdBo'); return s && !s.hidden ? s.value : (localStorageLay('st-td-bo') || 'mac-dinh'); }
function localStorageLay(k) { try { return localStorage.getItem(k) || ''; } catch (e) { return ''; } }
function tdNut() {
  const row = $('#buocClip .row.tao'); if (!row) return;
  let w = $('#tdNut');
  if (!w) {
    w = document.createElement('span'); w.id = 'tdNut'; w.className = 'td-nut';
    w.innerHTML = `<select id="tdBo" class="td-bo-chon" hidden aria-label="Bộ kiểu" data-tip="Bộ kiểu: chữ, chuyển cảnh, nhạc dùng để tự gắn"></select>`
      + `<button type="button" class="btn td-chay" id="bTuDung" disabled>${icon('hieuUng')}<span>Dựng tự động</span></button>${tvI(TD_GOI)}`;
    row.append(w);
    $('#bTuDung').onclick = tdChay;
    $('#tdBo').onchange = e => { try { localStorage.setItem('st-td-bo', e.target.value); } catch (x) {} };
  }
  const s = $('#tdBo'), ds = (TDG.bo && TDG.bo.ds) || [];
  if (ds.length > 1 && !s.options.length) {   // 1 bộ thì ẩn ô chọn (nút vô nghĩa thì ẩn)
    const cu = localStorageLay('st-td-bo');
    s.innerHTML = ds.map(x => `<option value="${esc(x.ma)}"${x.ma === cu ? ' selected' : ''} title="${esc(x.mo_ta || '')}">${esc(x.ten)}${x.nguon === 'kho' ? ' (kho)' : ''}</option>`).join('');
  }
  s.hidden = ds.length <= 1;
  $('#bTuDung').disabled = !H.chon.length || !!TDG.ma;
}
const tdVeClipGoc = veClip;
veClip = function () { const r = tdVeClipGoc.apply(this, arguments); try { tdNut(); tdTaiBo(); } catch (e) { console.error(e); } return r; };

/* ---------- chạy + tiến độ ---------- */
async function tdChay() {
  if (!H.chon.length || TDG.ma) return;
  const b = $('#bTuDung'); b.disabled = true; $('#moiErr').textContent = '';
  let r;
  try { r = await api('/api/sua-tay/tu-dung/chay', {thu_muc: H.tm, clip: H.chon, ten: $('#tenMoi').value.trim(), bo: tdBoChon()}); }
  catch (e) { $('#moiErr').textContent = e.message; b.disabled = false; return; }
  TDG.ma = r.ma; tdTienDo(r.ma);
}
function tdTienDo(ma) {
  const {m, dong} = modal(`<div class="td-h">${icon('hieuUng')}<h3>Dựng tự động</h3><span class="note td-gio"></span></div>
    <ol class="td-buoc">${TD_BUOC.map((t, i) => `<li data-b="${i + 1}"><span class="td-so">${i + 1}</span><span class="td-t">${t}</span></li>`).join('')}</ol>
    <div class="td-thanh" role="progressbar" aria-valuemin="0" aria-valuemax="100"><i></i></div>
    <p class="td-chu"></p><p class="note err td-loi" hidden></p>
    <div class="acts"><button type="button" class="btn" id="tdHuy">Huỷ</button></div>`);
  m.classList.add('td-hop'); TDG.hop = m;
  const bg = m.parentElement, mx = $('.mx', m); if (mx) mx.hidden = true;
  const chan = e => { if (TDG.ma && (e.target === bg || e.key === 'Escape')) { e.stopImmediatePropagation(); e.preventDefault(); } };
  bg.addEventListener('click', chan, true); document.addEventListener('keydown', chan, true);
  const xong = () => { document.removeEventListener('keydown', chan, true); TDG.ma = ''; TDG.hop = null; dong(); try { tdNut(); } catch (e) {} };
  $('#tdHuy', m).onclick = async () => {
    if (!TDG.ma) return xong();
    $('#tdHuy', m).disabled = true; $('.td-chu', m).textContent = 'Đang huỷ…';
    try { await api('/api/sua-tay/tu-dung/dung', {ma}); } catch (e) {}
  };
  const ve = x => {
    $$('.td-buoc li', m).forEach(li => { const b = +li.dataset.b; li.className = b < x.buoc || x.buoc === 4 ? 'xong' : b === x.buoc ? 'on' : ''; });
    const pt = clamp(+x.phan_tram || 0, 0, 100); $('.td-thanh i', m).style.width = pt + '%'; $('.td-thanh', m).setAttribute('aria-valuenow', pt);
    $('.td-chu', m).textContent = x.chu || ''; $('.td-gio', m).textContent = x.giay_da != null ? x.giay_da + ' giây' : '';
  };
  (async () => {
    for (;;) {
      if (!document.body.contains(m)) return;
      let x; try { x = await api('/api/sua-tay/tu-dung?ma=' + encodeURIComponent(ma)); } catch (e) { x = null; }
      if (x) {
        ve(x);
        if (!x.dang) {
          if (x.kq && x.kq.v) { $('.td-chu', m).textContent = 'Xong · đang mở video…'; TDG.ma = ''; location.href = '/sua-tay?v=' + encodeURIComponent(x.kq.v) + '&tu_dung=1'; return; }
          if (x.loi === 'Đã huỷ') { xong(); toast('Đã huỷ Dựng tự động (chưa tạo video nào)'); return; }
          TDG.ma = ''; $('.td-loi', m).hidden = false; $('.td-loi', m).textContent = x.loi || 'Dựng tự động dừng giữa chừng';
          $('#tdHuy', m).disabled = false; $('#tdHuy', m).textContent = 'Đóng'; if (mx) mx.hidden = false; return;
        }
      }
      await new Promise(z => setTimeout(z, 700));
    }
  })();
}

/* ---------- Thư viện › Clip: mở hộp đúng thư mục ---------- */
const tdTvClipGoc = tvClip;
tvClip = function () {
  const h = tdTvClipGoc.apply(this, arguments);
  const nut = `<button type="button" class="btn small td-tv" data-td-tv data-tip="${esc('Dựng tự động: chọn nhiều clip của thư mục này theo thứ tự → app tự cắt, gắn phụ đề, chữ, nhạc, chuyển cảnh thành 1 video mới')}">${icon('hieuUng')}<span>Dựng tự động…</span></button>`;
  return h.replace('<button type="button" class="btn small" data-tva="doi-tm">', nut + '<button type="button" class="btn small" data-tva="doi-tm">');
};
document.addEventListener('click', e => {
  if (!e.target.closest('[data-td-tv]')) return;
  const tm = tmTV(); moTaoMoi();
  if (tm) { H.chon = []; moThuMuc(tm).then(() => { const b = $('#bTuDung'); if (b) b.classList.add('td-goi'); }); }
});

/* ---------- trong trình sửa: chip + bảng tóm tắt + Hoàn tác cả lượt ---------- */
async function tdKetQua() {
  TDG.kq = null;
  if (S.plan && S.v) {
    try { const k = await api('/api/sua-tay/tu-dung/ket-qua?v=' + encodeURIComponent(S.v)); TDG.kq = k && k.co ? k : null; } catch (e) {}
  }
  tdChip();
  if (TDG.kq && Q.has('tu_dung')) {
    try { const u = new URL(location.href); u.searchParams.delete('tu_dung'); history.replaceState(null, '', u.pathname + u.search); } catch (e) {}
    Q.delete('tu_dung'); tdTomTat();
  }
}
function tdChip() {
  const c = $('#sdc'); if (!c) return;
  const cu = $('#tdChip'); if (cu) cu.remove();
  if (!TDG.kq) return;
  const b = document.createElement('button'); b.type = 'button'; b.id = 'tdChip'; b.className = 'chip td-chip';
  b.dataset.tip = 'Video này làm bằng Dựng tự động: bấm xem đã cắt / gắn gì, hoặc Hoàn tác cả lượt';
  b.innerHTML = icon('hieuUng') + '<span>Dựng tự động</span>'; b.onclick = tdTomTat; c.prepend(b);
}
function tdTomTat() {
  const k = TDG.kq; if (!k) return;
  const ds = k.tom_tat || [];
  const {m, dong: dongHop} = modal(`<div class="td-h">${icon('hieuUng')}<h3>Đã dựng tự động</h3><span class="note">${esc((k.bo && k.bo.ten) || '')}</span></div>
    <ul class="td-tt">${ds.map(x => `<li class="tdl-${esc(x.loai)}"><span class="td-ic">${icon(TD_IC[x.loai] || 'dauTick')}</span><span class="td-c">${esc(x.chu)}</span>${tvI(x.chi_tiet)}</li>`).join('')}</ul>
    <div class="acts"><button type="button" class="btn" id="tdHoan" data-tip="Về video trơn như “Tạo và sửa” (mỗi clip 1 cảnh, chưa cắt, chưa chữ / nhạc). Ctrl+Z để lấy lại bản dựng tự động"${k.plan_tron ? '' : ' hidden'}>${icon('undo')}<span>Hoàn tác cả lượt</span></button>
      <button type="button" class="btn primary" data-dong>Sửa tiếp</button></div>`);
  m.classList.add('td-hop', 'td-tom');
  const h = $('#tdHoan', m); if (h) h.onclick = () => { dongHop(); tdHoanTac(); };
}
function tdHoanTac() {
  const pt = TDG.kq && TDG.kq.plan_tron; if (!pt || !S.plan) return;
  try { dung(); } catch (e) {}
  doi(p => { Object.keys(p).forEach(x => delete p[x]); Object.assign(p, JSON.parse(JSON.stringify(pt))); S.sel.canh = (p.canh[0] || {})._id; S.sel.k = null; });
  toast('Đã hoàn tác cả lượt Dựng tự động: về video trơn (mỗi clip 1 cảnh) · Ctrl+Z để lấy lại bản dựng tự động');
}
const tdMoVideoGoc = moVideo;
moVideo = async function () { const r = await tdMoVideoGoc.apply(this, arguments); try { await tdKetQua(); } catch (e) { console.error(e); } return r; };
const tdVeBannerGoc = veBanner;
veBanner = function () { const r = tdVeBannerGoc.apply(this, arguments); try { tdChip(); } catch (e) {} return r; };

/* ---------- r41 (11/11 16:46, anh: "chưa có nút làm clip tự động"): nút Dựng tự động luôn thấy ----------
   Trước: nút nằm trong hộp "Video mới từ clip…" (phải mở menu tên video ▾) và Thư viện › Clip -> anh không thấy.
   Thêm: nút "Dựng tự động" ở thanh trên cùng (cạnh tên video, lúc nào cũng hiện), mục trong menu tên video ▾,
   nút ở màn "Chưa có video". Bấm = mở hộp Video mới từ clip ở chế độ dựng tự động: tiêu đề + 1 dòng hướng dẫn, nút Dựng tự động sáng. */
const TD_GHI_GOC = 'Không qua Claude: mỗi clip thành 1 cảnh để anh cắt, thêm chữ (hoặc bấm ✦ Nhờ Claude trong trình sửa).';
function tdCheDo(td) {   // đổi chữ đầu hộp theo chế độ (dựng tự động / video mới thường)
  const sec = $('.panel.moi'); if (!sec) return;
  const n = $('.phead .note', sec), b3 = $('#buoc li[data-b="3"]', sec), g = $('#tdGoi', sec), bt = $('#bTao');
  if (n) n.textContent = td ? 'App tự cắt chỗ lặng / ừ à / câu nói lại, gắn phụ đề, chữ, thẻ giá, nhạc, chuyển cảnh. Chạy trên máy, không tốn lượt Claude.' : TD_GHI_GOC;
  if (b3) b3.textContent = td ? 'Dựng tự động' : 'Tạo và sửa';
  if (g) g.hidden = !td;
  if (bt) bt.classList.toggle('td-phu', !!td);
}
const tdMoTaoMoiGoc = moTaoMoi;
moTaoMoi = function () { const r = tdMoTaoMoiGoc.apply(this, arguments); tdCheDo(false); const b = $('#bTuDung'); if (b) b.classList.remove('td-goi'); return r; };
function tdMoHop() {
  dongVd(); moTaoMoi();
  const sec = $('.panel.moi'); if (!sec) return;
  $('.h2', sec).textContent = 'Dựng tự động từ clip';
  let g = $('#tdGoi', sec);
  if (!g) { g = document.createElement('p'); g.id = 'tdGoi'; g.className = 'td-goi-dong'; $('.phead', sec).after(g); }
  g.innerHTML = icon('hieuUng') + '<span>Chọn thư mục, bấm các clip theo thứ tự quay, rồi bấm <b>Dựng tự động</b>.</span>';
  tdCheDo(true); TDG.cheDo = true;
  const b = $('#bTuDung'); if (b) b.classList.add('td-goi');
  const ob = new MutationObserver(() => { if (!document.body.contains($('#taoMoiM'))) { ob.disconnect(); TDG.cheDo = false; tdCheDo(false); } });
  ob.observe(document.body, {childList: true});
}
// chế độ dựng tự động: nút Dựng tự động (hiện khi đã chọn thư mục) sáng, "Tạo và sửa" thành nút phụ
const tdVeClipR41 = veClip;
veClip = function () { const r = tdVeClipR41.apply(this, arguments); if (TDG.cheDo) { const b = $('#bTuDung'); if (b) b.classList.add('td-goi'); tdCheDo(true); } return r; };
(function tdNutTren() {
  const vd = $('#bVd'); if (!vd || $('#bTuDungTren')) return;
  const b = document.createElement('button'); b.type = 'button'; b.id = 'bTuDungTren'; b.className = 'btn td-tren';
  b.dataset.tip = 'Chọn clip cầm máy nói → app tự cắt chỗ lặng / ừ à / câu nói lại, gắn phụ đề, chữ, thẻ giá, nhạc, chuyển cảnh thành 1 video mới. Không tốn lượt Claude.';
  b.innerHTML = icon('hieuUng') + '<span>Dựng tự động</span>';
  b.onclick = e => { e.stopPropagation(); tdMoHop(); };
  vd.after(b);
})();
new MutationObserver(() => {
  const m = $('#vdMenu .vd-moi[data-vd-moi]');
  if (m && !$('#vdMenu [data-td-moi]')) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'vd-moi td-vd'; b.dataset.tdMoi = '1';
    b.innerHTML = icon('hieuUng') + '<span><b>Dựng tự động từ clip…</b><small>Bấm clip theo thứ tự, app tự cắt, gắn phụ đề, chữ, nhạc, chuyển cảnh</small></span>';
    m.after(b);
  }
  const t = $('.trong-vd [data-vd-moi2]');
  if (t && !$('.trong-vd [data-td-moi]')) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'btn td-chay'; b.dataset.tdMoi = '1';
    b.innerHTML = icon('hieuUng') + '<span>Dựng tự động…</span>'; t.after(b);
  }
}).observe(document.body, {childList: true, subtree: true});
document.addEventListener('click', e => { if (e.target.closest('[data-td-moi]')) { e.stopPropagation(); tdMoHop(); } }, true);
