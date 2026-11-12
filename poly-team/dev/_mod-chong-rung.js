/* ============================== CHỐNG RUNG + NHƯỜNG MÁY KHI PHÁT (4/11/2026 tối, anh: "khung hình vẫn rung", chọn cả 4 kiểu rung) ==============================
   1) CHỐNG RUNG từng cảnh (khoá có sẵn canh.on_dinh, bộ dựng dung_may_chu: vidstab 2 lượt, các phần liền nhau của 1 cảnh làm chung 1 lượt):
      tab Cảnh › Hình: công tắc "Chống rung" cho cảnh đang chọn + nút "Bật cho mọi cảnh" (1 bước Ctrl+Z), dấu trên khối cảnh.
      KHUNG XEM thấy ngay hình đã chống rung: máy chủ làm bản xem nhẹ 720p đã ổn định (chong_rung.py, cache riêng, cùng thông số bộ dựng);
      trong lúc làm thì khung xem hiện bản thường. Thẻ <video> riêng VID[clip + '#od'], vidDoan(d) chọn thẻ cho từng đoạn (veKhung / chay).
   2) GỢI Ý (không tự bật): đo độ rung tay của clip trong cảnh (chong_rung_may.py, cách đo + mốc của bộ dựng phan_tich.py) -> cảnh có
      clip rung mà chưa bật thì hộp Chống rung ghi "Clip này quay tay bị rung… Bật Chống rung?" + 1 dòng nổi trong khung xem (tắt được).
   3) NHƯỜNG MÁY: đang phát thì báo máy chủ mỗi 1,5s (hang_nen: chỉ 1 việc nền chạy, còn lại tạm dừng hẳn; việc "để sau" không chạy).
      Rê chuột lên clip trong Thư viện ~0,8s (lúc không phát) thì xếp làm bản xem nhẹ clip đó.
   Móc ở file chung (vài dòng): _sua-tay.src.html (veKhung / chay / tua sẵn gọi vidDoan; theoProxy chỉ hỏi clip trong cảnh),
   _canh-tt.js (benCanh gọi hinhChongRung, dauCanh thêm dấu, apAmLuongNgay gọi vidDoan). */
IC_P.chongRung = '<rect x="7" y="5" width="10" height="14" rx="2"/><path d="M3.5 9v6M20.5 9v6"/><path d="M12 9.5v5M9.5 12h5"/>';
S.cr = {od: {}, do: {}, phat: false, lanXem: 0, lanDo: 0, xem: false, dangDo: false, an: false, nhip: 0};
try { S.cr.an = localStorage.getItem('st-cr-an|' + S.v) === '1'; } catch (e) {}
const crCanh = c => !!(c && c.on_dinh);
function crCanOD(d) {   // đoạn này dựng có chống rung? (cảnh bật, hoặc nguồn bật — như bộ dựng)
  if (!d || !S.plan) return false;
  const c = d.id ? S.plan.canh.find(x => x._id === d.id) : null;
  return !!(c && c.on_dinh) || !!(((S.plan.nguon || {})[d.file] || {}).on_dinh);
}
function vidDoan(d) {   // thẻ video cho 1 đoạn: bản đã chống rung (nếu cảnh bật + bản đó đã nạp xong) hay bản xem nhẹ thường
  const p = src(d.file), th = VID[p];
  if (!crCanOD(d)) return th;
  const e = VID[p + '#od'];
  return e && e.dataset.san === '1' && e.readyState >= 1 ? e : th;
}
function crClipBat() {
  const ng = S.plan.nguon || {};
  return [...new Set(S.plan.canh.filter(c => c.on_dinh || (ng[c.file] || {}).on_dinh).map(c => src(c.file)))].filter(p => !(S.matSrc || new Set()).has(p));
}
function crGan(p, url) {   // nạp thẻ video bản đã chống rung; đang phát thì chờ dừng mới đổi (không nhảy khung giữa lúc xem)
  const k = p + '#od'; let el = VID[k];
  if (el && el.getAttribute('src') === url) { if (!S.playing && el.readyState >= 1 && el.dataset.san !== '1') { el.dataset.san = '1'; veKhung(true); } return; }
  if (S.playing) return;
  if (el) { el.removeAttribute('src'); try { el.load(); } catch (e) {} el.remove(); }
  el = document.createElement('video'); el.className = 'v'; el.preload = 'auto'; el.playsInline = true; el.muted = true; el.dataset.od = '1';
  el.addEventListener('loadeddata', () => { if (!S.playing && VID[k] === el) { el.dataset.san = '1'; veKhung(true); } });
  el.src = url; $('#vids').append(el); VID[k] = el;
}
function crTxt(p) {
  const x = S.cr.od[p];
  if (!x) return 'Khung xem: đang chuẩn bị bản đã chống rung…';
  if (x.tt === 'xong') return (VID[p + '#od'] && VID[p + '#od'].dataset.san === '1') ? 'Khung xem đang hiện hình đã chống rung.' : 'Khung xem: đang nạp bản đã chống rung…';
  if (x.tt === 'loi') return 'Không làm được bản xem chống rung (' + (x.loi || 'lỗi') + '). Bản xuất vẫn chống rung.';
  return 'Khung xem: đang làm bản đã chống rung (tạm hiện hình thường)…';
}
function crVeTT() { const e = $('#crTT'); if (e) { const c = canhDangChon(); if (c) e.textContent = crTxt(src(c.file)); } crVeGoi(); }
const crPct = v => (Math.round(v * 100) / 100).toLocaleString('vi-VN') + '%';
function hinhChongRung(c) {
  const on = crCanh(c), n = S.plan.canh.length, nOn = S.plan.canh.filter(crCanh).length, p = src(c.file), dd = S.cr.do[p] || {};
  const rung = dd.muc === 'rung', pr = (S.plan.kieu || {}).duong === 'premiere';
  let note;
  // r29 (soi N6): ghi chú 1 dòng ngắn, câu đầy đủ vào (i) cạnh tên nhóm
  let tipI = 'Chống rung: máy làm mượt đường đi của máy quay, hình phóng nhẹ (~2–5%) để che mép. Cảnh nào bật thì khung xem cũng hiện hình đã chống rung. Xuất video 1080p lâu hơn khoảng 1,6 lần (bản nháp gần như không đổi).';
  if (on) note = 'Đang bật: hình phóng nhẹ (~2–5%) để che mép, xuất 1080p lâu hơn ~1,6 lần.';
  else if (rung) note = `<b>Clip này quay tay bị rung</b> (độ lắc ${crPct(dd.trung_vi)} khung). Bật Chống rung?`;
  else if (dd.muc === 'vua') note = 'Clip hơi lắc nhẹ. Bật nếu thấy hình rung.';
  else if (dd.tt === 'xong') note = 'Clip này khá đứng yên, thường không cần chống rung.';
  else note = 'Hình quay tay bị lắc thì bật để máy làm mượt.';
  return `<div class="box tt-box cr-box${rung && !on ? ' goi' : ''}"><div class="row co-i"><h2 class="sec grow">${icon('chongRung')}Chống rung</h2><button type="button" class="tt-i" data-tip="${esc(tipI)}" aria-label="Giải thích: ${esc(tipI)}">${icon('thongTin')}</button>
      <button type="button" class="cr-sw${on ? ' on' : ''}" role="switch" aria-checked="${on}" data-cr-a="bat" data-tip="${on ? 'Tắt' : 'Bật'} chống rung cảnh ${S.plan.canh.indexOf(c) + 1} (Ctrl+Z để bỏ)"><span class="cr-nut" aria-hidden="true"></span><span class="cr-ch">${on ? 'Bật' : 'Tắt'}</span></button></div>
    <p class="note giu">${note}</p>${on ? `<p class="note giu cr-tt" id="crTT" aria-live="polite">${esc(crTxt(p))}</p>` : ''}
    <div class="row"><button type="button" class="btn small" data-cr-a="het" ${n > 1 || !on ? '' : 'disabled'} data-tip="${nOn === n ? 'Tắt chống rung mọi cảnh' : 'Bật chống rung cho mọi cảnh của video'} (1 bước Ctrl+Z)">${icon('lop')}${nOn === n ? 'Tắt cho mọi cảnh' : 'Bật cho mọi cảnh (' + n + ')'}</button>
    ${pr ? '<span class="note grow">Chỉ có ở bản xuất trong app (Premiere bỏ qua).</span>' : ''}</div></div>`;
}
function crDat(ids, bat) {
  const s = new Set(ids);
  doi(p => { p.canh.forEach(c => { if (s.has(c._id)) { if (bat) c.on_dinh = true; else delete c.on_dinh; } }); });
  S.cr.lanXem = 0; crLap();
}
$('#pane').addEventListener('click', e => {
  const b = e.target.closest('[data-cr-a]'); if (!b || b.disabled || !S.plan) return;
  const c = canhDangChon(); if (!c) return;
  if (b.dataset.crA === 'bat') { const bat = !crCanh(c); crDat([c._id], bat); vaoCanh(c._id); toast((bat ? 'Đã bật' : 'Đã tắt') + ' chống rung cảnh ' + (S.plan.canh.findIndex(x => x._id === c._id) + 1) + ' (Ctrl+Z để bỏ)'); }
  if (b.dataset.crA === 'het') { const bat = S.plan.canh.some(x => !crCanh(x)); crDat(S.plan.canh.map(x => x._id), bat); toast((bat ? 'Đã bật' : 'Đã tắt') + ' chống rung mọi cảnh (Ctrl+Z để bỏ)'); }
});
/* dòng gợi ý nổi trong khung xem: cảnh dùng clip RUNG mà chưa bật */
function crCanhRung() { return S.plan ? S.plan.canh.filter(c => !crCanh(c) && (S.cr.do[src(c.file)] || {}).muc === 'rung') : []; }
function crVeGoi() {
  let el = $('#crGoi'); const ds = S.cr.an ? [] : crCanhRung();
  if (!ds.length) { if (el) el.remove(); return; }
  if (!el) { el = document.createElement('div'); el.id = 'crGoi'; el.className = 'cr-goi'; el.setAttribute('role', 'status'); $('#stage').append(el); }
  const h = `<span>${icon('chongRung')}${ds.length} cảnh quay tay bị rung</span><button type="button" class="btn small primary" data-crg="bat">Bật chống rung</button><button type="button" class="btn small icon ghost" data-crg="an" aria-label="Ẩn gợi ý" data-tip="Ẩn gợi ý này">✕</button>`;
  if (el.dataset.h !== h) { el.innerHTML = h; el.dataset.h = h; }
}
document.addEventListener('click', e => {
  const b = e.target.closest('#crGoi [data-crg]'); if (!b) return;
  if (b.dataset.crg === 'an') { S.cr.an = true; try { localStorage.setItem('st-cr-an|' + S.v, '1'); } catch (x) {} return crVeGoi(); }
  const ds = crCanhRung(); if (!ds.length) return;
  crDat(ds.map(c => c._id), true); toast('Đã bật chống rung ' + ds.length + ' cảnh (Ctrl+Z để bỏ)'); crVeGoi();
});
/* vòng 1,5s: báo đang phát (nhường máy), hỏi bản xem đã chống rung, đo độ rung clip trong cảnh */
async function crLap() {
  if (!S.plan || !S.view || ($('#edit') && $('#edit').hidden)) return;
  const ph = !!S.playing && S.mode === 'xem';
  if (ph || S.cr.phat !== ph) { S.cr.phat = ph; const d = ph ? doanLuc(S.t) : null;   // clip đang hiện: máy chủ cho việc nền của clip này chạy trước
    const el = d ? vidDoan(d) : null, video = !!(el && el.readyState >= 2);   // false: chưa có bản xem nhẹ, khung xem hiện ảnh tạm -> máy chủ không nhường
    S.cr.so = (S.cr.so || 0) + 1;   // số thứ tự: máy bận, báo đến trễ / lộn thứ tự thì máy chủ bỏ báo cũ
    api('/api/sua-tay/chong-rung/phat', {dang: ph, clip: d ? src(d.file) : '', video, phien: PHIEN, so: S.cr.so}).catch(() => {}); }
  const can = crClipBat(), now = Date.now();
  if (can.length && !S.cr.xem && now - S.cr.lanXem > 2500) {
    S.cr.xem = true; S.cr.lanXem = now;
    try { const r = await api('/api/sua-tay/chong-rung/xem', {ds: can}); for (const [p, x] of Object.entries(r || {})) { S.cr.od[p] = x; if (x.tt === 'xong' && x.url) crGan(p, x.url); } }
    catch (e) {} finally { S.cr.xem = false; }
  }
  // đo độ rung: chỉ lúc không phát, clip trong cảnh chưa có kết quả
  const chua = [...new Set(S.plan.canh.map(c => src(c.file)))].filter(p => !(S.matSrc || new Set()).has(p) && !['xong', 'loi', 'khong'].includes((S.cr.do[p] || {}).tt));
  if (!ph && chua.length && !S.cr.dangDo && now - S.cr.lanDo > 4000) {
    S.cr.dangDo = true; S.cr.lanDo = now;
    try { const r = await api('/api/sua-tay/chong-rung/do', {ds: chua}); let doi_ = false;
      for (const [p, x] of Object.entries(r || {})) { if ((S.cr.do[p] || {}).tt !== x.tt) doi_ = true; S.cr.do[p] = x; }
      if (doi_ && S.tab === 'canh' && S.tabCanh === 'hinh' && !S.tam && !(document.activeElement && document.activeElement.closest && document.activeElement.closest('#pane input, #pane textarea'))) {
        // gộp 5/11: chỉ thay hộp Chống rung, không vẽ lại cả bảng phải (bảng nhảy ngay lúc anh đang bấm)
        const bx = $('#pane .cr-box'), cc = (S.plan.canh || []).find(c => c._id === S.sel.canh);
        if (bx && cc) { const t = document.createElement('div'); t.innerHTML = hinhChongRung(cc); if (t.firstElementChild) bx.replaceWith(t.firstElementChild); } else if (!bx) veBen(true); } }
    catch (e) {} finally { S.cr.dangDo = false; }
  }
  crVeTT();
}
setInterval(crLap, 1500);
window.addEventListener('pagehide', () => { if (S.cr.phat) { S.cr.so = (S.cr.so || 0) + 1; api('/api/sua-tay/chong-rung/phat', {dang: false, phien: PHIEN, so: S.cr.so}, {keep: true}).catch(() => {}); } });
/* Thư viện: rê chuột lên clip ~0,8s (không phát) -> làm bản xem nhẹ clip đó (clip chưa dùng trong cảnh thì máy chủ để sau, rê vào là làm) */
let crRe = 0;
document.addEventListener('pointerover', e => {
  const t = e.target.closest && e.target.closest('#libPane [data-tvclip]'); if (!t) return;
  clearTimeout(crRe); const p = t.dataset.tvclip;
  crRe = setTimeout(() => { if (!S.playing && t.matches(':hover')) api('/api/sua-tay/proxy', {ds: [p]}).catch(() => {}); }, 800);
});
