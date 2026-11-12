/* ============================== BẢNG PHẢI GỌN (4/11 tối, anh: "khung này chưa tối ưu, nghiên cứu lại ui ux") ==============================
   Tab Cảnh bên phải xếp như cột thuộc tính CapCut: nhóm phẳng có tiêu đề nhỏ, mỗi thuộc tính 1 hàng
   (nhãn · thanh kéo · ô số gõ được · nút về mặc định), ghi chú dài vào dấu (i), điều khiển vô nghĩa thì ẩn.
   Trình bày: dev/_mod-ben-phai.css. Dữ liệu / bước Ctrl+Z vẫn đi qua _canh-tt.js (TT, ttGiaTri, datTT, vaoCanh).
   1) ghi chú -> (i): mỗi lần bảng vẽ lại, <p class="note"> trong .tt-box (kể cả của mô-đun khác: Tự chỉnh màu, Bộ lọc màu…)
      và .note.grow ở hàng dưới thành 1 nút (i) cạnh tiêu đề nhóm; rê chuột / Tab tới là hiện chữ. Giữ dòng chữ: class "giu".
   2) ô số .tt-so: gõ 150, -30, "trái 30", "ấm 20"… là khung xem đổi ngay (gộp 1 bước Ctrl+Z); ↑ ↓ tăng giảm 1 (Shift: 10);
      Enter giữ ô, Esc trả lại số cũ. Thanh kéo đổi thì ô đi theo (_canh-tt.js).
   3) âm lượng trên 100%: ô số màu vàng (bản xuất to hơn nghe thử).
   4) nút Thêm cảnh nằm trên dòng "Tất cả cảnh": bấm không đóng / mở danh sách.
   5) tab Chữ / Phụ đề / Kiểu / Bản xuất: chỉ câu hướng dẫn -> (i), trạng thái trống 1 dòng (bpTabKhac). */
IC_P.thongTin = '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><path d="M12 7.5v.01"/>';
IC_P.len = '<path d="M12 19V5"/><path d="m6 11 6-6 6 6"/>';
IC_P.xuong = '<path d="M12 5v14"/><path d="m18 13-6 6-6-6"/>';

/* ---------- 1) ghi chú -> dấu (i) ---------- */
function bpGhiChu() {
  const pane = $('#pane'); if (!pane) return;
  pane.querySelectorAll('.tt-box').forEach(bx => {
    const ds = [...bx.querySelectorAll(':scope > p.note:not(.giu), :scope > .row:not(:first-child) > .note.grow')];
    if (!ds.length) return;
    const txt = ds.map(p => p.textContent.replace(/\s+/g, ' ').trim()).filter(Boolean).join(' ');
    ds.forEach(p => p.remove());
    const h2 = bx.querySelector(':scope > .row:first-child > h2, :scope > h2'); if (!txt || !h2) return;
    const cu = h2.nextElementSibling && h2.nextElementSibling.classList.contains('tt-i') ? h2.nextElementSibling : null;
    if (cu) { cu.dataset.tip += ' ' + txt; cu.setAttribute('aria-label', 'Giải thích: ' + cu.dataset.tip); return; }
    h2.insertAdjacentHTML('afterend', `<button type="button" class="tt-i" data-tip="${esc(txt)}" aria-label="Giải thích: ${esc(txt)}">${icon('thongTin')}</button>`);
    if (h2.parentElement.classList.contains('row')) h2.parentElement.classList.add('co-i');
  });
  // gợi ý "Hình tự zoom / lia?" (dev/_mod-dung-yen.js): khung còn 1 dòng, câu giải thích đầy đủ vào ô gợi ý
  pane.querySelectorAll('.dy-goi.canh .dy-t').forEach(t => { if (!t.dataset.tip) t.dataset.tip = t.textContent.replace(/\s+/g, ' ').trim(); });
  bpTabKhac(pane);
  bpQua();
}
/* các tab khác (Chữ, Phụ đề, Kiểu, Bản xuất), 4/11 tối anh: "mấy phần chữ này bị chiếm chỗ nhiều quá": chỉ đổi câu hướng dẫn sang (i),
   không đổi bố cục. Giữ nguyên: lỗi / cảnh báo / trạng thái (class err, warnt, okt, giu, kieu-dy, soat-ghi, dim…), dòng có giờ / ô gõ / nút,
   dòng là nội dung (ngay sau ô chọn .radio / nhãn .lbl, vd câu thẻ kết mặc định). Trạng thái trống ("Chưa có…", "Không có…"): giữ câu đầu, phần giải thích vào (i). */
const BP_TRONG = /^(Chưa có|Không có|Video chưa có)[^.]*\./;
function bpHD(p) {   // <p class="note"> thường = câu hướng dẫn?
  if (p.getAttribute('class') !== 'note' || p.dataset.bp || /^(Đang|Xong|Lỗi)/.test(p.textContent.trim())) return false;   // "note " (đang dựng…) = trạng thái
  if (p.querySelector('[data-gio], input, button, select, textarea, a')) return false;
  const tr = p.previousElementSibling; return !(tr && tr.matches('.radio, .lbl, .inp, select'));
}
function bpNutI(txt) { return `<button type="button" class="tt-i" data-tip="${esc(txt)}" aria-label="Giải thích: ${esc(txt)}">${icon('thongTin')}</button>`; }
function bpTrong(p) {   // "Chưa có nhãn. Nhãn = …" -> "Chưa có nhãn." + (i)
  const t = p.textContent.replace(/\s+/g, ' ').trim(), m = t.match(BP_TRONG); if (!m) return false;
  const con = t.slice(m[0].length).trim(); p.dataset.bp = 'trong';
  if (con) p.innerHTML = esc(m[0]) + ' ' + bpNutI(con);
  return true;
}
function bpTabKhac(pane) {
  if (!S.plan || S.tab === 'canh' || S.tab === 'ai') return;
  pane.querySelectorAll('.box').forEach(bx => {
    const h2 = bx.querySelector(':scope > h2.sec, :scope > .row:first-child > h2.sec'); if (!h2) return;
    const ds = [...bx.querySelectorAll(':scope > p.note')].filter(bpHD).filter(p => !bpTrong(p));
    if (!ds.length) return;
    const txt = ds.map(p => p.textContent.replace(/\s+/g, ' ').trim()).filter(Boolean).join(' '); ds.forEach(p => p.remove());
    if (txt) h2.insertAdjacentHTML('beforeend', bpNutI(txt));
  });
  // ghi chú đứng riêng đầu / cuối tab (Kiểu): 1 dòng, rê chuột đọc đủ
  pane.querySelectorAll(':scope > p.note').forEach(p => {
    if (!bpHD(p) || bpTrong(p)) return;
    const t = p.textContent.replace(/\s+/g, ' ').trim(); p.dataset.bp = '1dong'; p.dataset.tip = t; p.tabIndex = 0;
    p.innerHTML = icon('thongTin') + `<span>${esc(t)}</span>`;
  });
  // Phụ đề: câu giới thiệu đầu hàng nút -> (i) đầu hàng
  pane.querySelectorAll(':scope > .row > p.note.grow:first-child').forEach(p => {
    const t = p.textContent.replace(/\s+/g, ' ').trim(); if (t) p.insertAdjacentHTML('beforebegin', bpNutI(t)); p.remove();
  });
}
new MutationObserver(() => bpGhiChu()).observe($('#pane'), {childList: true, subtree: true});

/* ---------- 3) âm lượng > 100%: ô số vàng ---------- */
function bpQua() {
  const r = $('#pane input[data-tt="am"]'); if (!r) return;
  const h = r.closest('.tt-h'); if (h) h.classList.toggle('qua', +r.value > 100);
}
$('#pane').addEventListener('input', e => { if (e.target.matches && e.target.matches('input[data-tt="am"]')) bpQua(); });

/* ---------- 2) ô số gõ được ---------- */
function bpDoc(f, s) {   // chữ anh gõ -> số trên thanh (null = không hiểu)
  const d = TT[f]; if (!d) return null;
  s = String(s || '').normalize('NFC').toLowerCase().replace(/−/g, '-').replace(/,/g, '.').trim();
  const m = s.match(/-?\d+(\.\d+)?/);
  let v = m ? parseFloat(m[0]) : /giữa|giữ|tắt|không/.test(s) ? (f === 'khung.zoom' ? 100 : 0) : NaN;
  if (!isFinite(v)) return null;
  if (f === 'khung.zoom' && v > 0 && v <= 3) v *= 100;   // gõ 1,5 = 150%
  if (/trái|trên|lạnh/.test(s) && v > 0) v = -v;
  return clamp(Math.round(v), d.min, d.max);
}
function bpDongBo(f, giuO) {   // sau khi ghi: thanh, ô số, nút về mặc định của hàng (bảng không vẽ lại lúc đang gõ)
  const c = canhDangChon(), d = TT[f]; if (!c || !d) return;
  const v = d.ui(c), md = f === 'khung.zoom' || f === 'am' ? 100 : 0;
  const r = $(`#pane input[data-tt="${f}"]`); if (r) { r.value = v; r.style.cssText = ttDai(d, v); }
  const o = $(`#pane input[data-tt-so="${f}"]`); if (o && !giuO) o.value = d.nhan(v);
  const l = $(`#pane [data-tt-lai="${f}"]`); if (l) l.disabled = v === md;
  bpNhom(c); bpQua();
}
function bpNhom(c) {   // trạng thái phụ thuộc trong nhóm: Ngang / Dọc mở khi thu phóng > 100%, Căn giữa / Đặt lại, nút Tắt tiếng
  const kh = khungC(c), th = thuaCanh(c, kh.zoom);
  [['khung.x', th.ngang, 'chiều ngang'], ['khung.y', th.doc, 'chiều dọc']].forEach(([f, mo, chieu]) => {
    const r = $(`#pane input[data-tt="${f}"]`), h = r && r.closest('.tt-h'); if (!h) return;
    h.classList.toggle('tat', !mo); r.disabled = !mo;
    const o = h.querySelector('.tt-so'); if (o) o.disabled = !mo;
    const l = h.querySelector('.tt-lai'); if (l) l.disabled = !mo || TT[f].ui(c) === 0;
    if (mo) delete h.dataset.tip; else h.dataset.tip = 'Clip vừa khít khung 9:16 theo ' + chieu + ': tăng Thu phóng để dời được';
  });
  const g = $('#pane [data-tt-a="giua"]'); if (g) g.disabled = !(kh.x || kh.y);
  const kl = $('#pane [data-tt-a="khung-lai"]'); if (kl) kl.disabled = khungMd(kh);
  const ml = $('#pane [data-tt-a="mau-lai"]'); if (ml) ml.disabled = mauMd(mauC(c));
  const t = $('#pane [data-tt-a="tat-tieng"]');
  if (t && !t.disabled) { const tat = amC(c) === 0; t.classList.toggle('primary', tat); t.setAttribute('aria-pressed', String(tat));
    t.dataset.tip = tat ? 'Bật lại tiếng gốc của cảnh này' : 'Tắt tiếng gốc của cảnh này'; t.innerHTML = icon(tat ? 'tatLoa' : 'loa') + (tat ? 'Bật tiếng lại' : 'Tắt tiếng'); }
}
const BP = {cu: null, vao: false, go: false};
function bpGhi(o, v) {   // v = số trên thanh; gộp các lần gõ liền nhau thành 1 bước Ctrl+Z
  const f = o.dataset.ttSo, c = canhDangChon(); if (!c || !TT[f] || v == null) return;
  if (v === TT[f].ui(c)) return bpDongBo(f, true);
  if (!BP.vao) { BP.vao = true; vaoCanh(c._id); }
  const g = ttGiaTri(c, f, v);
  datTT(c._id, g.khoa, g.gt, 'tt:' + c._id + ':' + f);
  bpDongBo(f, true);
}
$('#pane').addEventListener('focusin', e => {
  const o = e.target.closest && e.target.closest('input[data-tt-so]'); if (!o) return;
  BP.cu = o.value; BP.vao = false; BP.go = false;
  setTimeout(() => { if (document.activeElement === o && !BP.go) o.select(); }, 0);   // máy chậm: đừng chọn đè chữ anh vừa gõ
});
$('#pane').addEventListener('input', e => {
  const o = e.target.closest && e.target.closest('input[data-tt-so]'); if (!o) return;
  BP.go = true; bpGhi(o, bpDoc(o.dataset.ttSo, o.value));
});
$('#pane').addEventListener('keydown', e => {
  const o = e.target.closest && e.target.closest('input[data-tt-so]'); if (!o) return;
  const f = o.dataset.ttSo, d = TT[f], c = canhDangChon(); if (!d || !c) return;
  if (e.key === 'Enter') { e.preventDefault(); o.value = d.nhan(d.ui(c)); o.select(); return; }
  if (e.key === 'Escape') {   // trả lại số lúc bấm vào ô
    e.preventDefault(); e.stopPropagation();
    const v = bpDoc(f, BP.cu); if (v != null) bpGhi(o, v);
    o.value = BP.cu != null ? BP.cu : d.nhan(d.ui(c)); o.blur(); return;
  }
  if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
    e.preventDefault(); e.stopPropagation();
    const v = clamp(d.ui(c) + (e.key === 'ArrowUp' ? 1 : -1) * (e.shiftKey ? 10 : 1), d.min, d.max);
    bpGhi(o, v); o.value = d.nhan(d.ui(canhDangChon())); o.select();
  }
});
$('#pane').addEventListener('focusout', e => {   // rời ô: hiện lại chữ chuẩn (gõ sai thì về số đang dùng)
  const o = e.target.closest && e.target.closest('input[data-tt-so]'); if (!o) return;
  const f = o.dataset.ttSo, c = canhDangChon(); if (c && TT[f]) o.value = TT[f].nhan(TT[f].ui(c));
  // đã đổi gì + rời hẳn bảng: vẽ lại cho đủ (sang nút / thanh khác trong bảng thì thôi, kẻo nút đang bấm bị thay mất)
  if (BP.vao && !(e.relatedTarget && $('#pane').contains(e.relatedTarget))) setTimeout(() => { if (!$('#pane').contains(document.activeElement)) veBen(true); }, 0);
  BP.cu = null; BP.vao = false;
});

/* ---------- 4) Thêm cảnh trên dòng "Tất cả cảnh": không bật / tắt danh sách ---------- */
$('#pane').addEventListener('click', e => { if (e.target.closest && e.target.closest('summary [data-a]')) e.preventDefault(); }, true);
