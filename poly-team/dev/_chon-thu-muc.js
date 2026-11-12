/* Bảng chọn thư mục clip trong app (3/11, thay hộp cây thư mục của Windows). build_ui.py chèn vào cả 2 trang.
   CTM(batDau, dangChon) -> Promise<đường dẫn | null>: mở dạng hộp nổi.
   CTM.gan(phanTu, {batDau, dangChon, onChon}): vẽ thẳng vào 1 khung trên trang (trang chủ Sửa tay).
   Thẻ = thư mục con (ảnh bìa = clip mới nhất, số clip, ngày), mới nhất lên đầu. Bấm thẻ có clip = chọn luôn;
   thẻ chỉ có thư mục con = mở vào. */
const CTM = (() => {
  const e = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const q = (s, r) => r.querySelector(s);
  const ngay = t => { if (!t) return ''; const d = new Date(t * 1000), n = new Date(), h = new Date(n); h.setDate(n.getDate() - 1);
    if (d.toDateString() === n.toDateString()) return 'hôm nay ' + String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
    if (d.toDateString() === h.toDateString()) return 'hôm qua';
    return String(d.getDate()).padStart(2, '0') + '/' + String(d.getMonth() + 1).padStart(2, '0') + (d.getFullYear() !== n.getFullYear() ? '/' + d.getFullYear() : ''); };
  const sep = p => String(p).includes('\\') || /^[A-Za-z]:/.test(p) ? '\\' : '/';
  const kd = s => String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'D').toLowerCase();
  const chuan = p => String(p || '').replace(/[\\/]+$/, '').toLowerCase();
  function vun(p) {   // đường dẫn -> các bậc [{ten, p}]
    const s = sep(p), a = String(p).split(/[\\/]+/).filter(Boolean), out = [];
    let cur = /^[\\/]/.test(p) ? s : '';
    a.forEach((x, i) => { cur = i === 0 && /^[A-Za-z]:$/.test(x) ? x + s : (cur && !cur.endsWith(s) ? cur + s : cur) + x; out.push({ten: x, p: cur}); });
    return out;
  }
  const ganDay = () => { try { const x = JSON.parse(localStorage.getItem('ctm-gan-day') || '[]'); return Array.isArray(x) ? x.filter(p => typeof p === 'string') : []; } catch (er) { return []; } };
  const nhoGanDay = p => { try { localStorage.setItem('ctm-gan-day', JSON.stringify([p, ...ganDay().filter(x => chuan(x) !== chuan(p))].slice(0, 8))); } catch (er) {} };
  // vẽ bảng vào root; o = {batDau, dangChon, onChon(p), onDong(), noi: true (hộp nổi) | false (trên trang)}
  function gan(root, o) {
    root.classList.add('ctm');
    if (!o.noi) root.classList.add('ctm-in');
    root.innerHTML = (o.noi ? `<div class="ctm-h"><b>Chọn thư mục clip</b><span class="ctm-sp"></span><button type="button" class="ctm-x" data-x="dong" title="Đóng (Esc)">✕</button></div>` : '')
      + `<div class="ctm-bar"><button type="button" class="ctm-b" data-x="len" title="Lên thư mục cha (Backspace)">↑ Lên</button><div class="ctm-vun"></div>
          <input class="ctm-tim" type="search" placeholder="Tìm, hoặc dán đường dẫn rồi Enter" spellcheck="false" aria-label="Tìm thư mục hoặc dán đường dẫn"></div>
        <div class="ctm-mid"><nav class="ctm-side" aria-label="Lối tắt"></nav><div class="ctm-body"><p class="ctm-note">Đang đọc…</p></div></div>
        <div class="ctm-f"><span class="ctm-nay"></span><span class="ctm-sp"></span>
          <button type="button" class="ctm-b ctm-dung" data-x="dung">Dùng thư mục này</button></div>`;
    const tim = q('.ctm-tim', root), body = q('.ctm-body', root);
    let D = null, lan = 0, dang = o.dangChon || '';
    function ve() {
      const k = kd(tim.value.trim()), ds = D.con.filter(x => !k || kd(x.ten).includes(k)), da = chuan(dang);
      const v0 = vun(D.thu_muc), ten0 = v0.length ? v0[v0.length - 1].ten : D.thu_muc;
      const nay = D.so_clip && !k ? `<button type="button" class="ctm-c ctm-nay-c${chuan(D.thu_muc) === da ? ' on' : ''}" data-x="dung" title="${e(D.thu_muc)} · bấm để dùng">
          <span class="ctm-a">${D.bia ? `<img loading="lazy" alt="" src="/api/thumb?p=${encodeURIComponent(D.bia)}&t=1" onerror="this.remove()">` : ''}<span class="ctm-tag">clip ngay trong thư mục này</span><span class="ctm-go">Dùng</span></span>
          <span class="ctm-t">${e(ten0)}</span><span class="ctm-m">${D.so_clip} clip</span></button>` : '';
      body.innerHTML = ds.length || nay ? `<div class="ctm-grid">${nay}${ds.map(x => {
          const la = !x.so_thu_muc && x.so_clip;   // thư mục lá có clip: bấm = chọn
          const meta = [x.so_clip ? x.so_clip + ' clip' : '', x.so_thu_muc ? x.so_thu_muc + ' thư mục' : '', ngay(x.mt)].filter(Boolean).join(' · ');
          return `<button type="button" class="ctm-c${chuan(x.p) === da ? ' on' : ''}" data-i="${D.con.indexOf(x)}" title="${e(x.p)}${la ? ' · bấm để dùng' : ' · bấm để mở'}">
            <span class="ctm-a">${x.bia ? `<img loading="lazy" alt="" src="/api/thumb?p=${encodeURIComponent(x.bia)}&t=1" onerror="this.remove()">` : ''}<span class="ctm-ic">${x.so_clip ? '' : '📁'}</span>${x.so_thu_muc && x.so_clip ? '<span class="ctm-tag">có thư mục con</span>' : ''}${la ? '<span class="ctm-go">Dùng</span>' : x.so_thu_muc ? '<span class="ctm-go mo">Mở ›</span>' : ''}</span>
            <span class="ctm-t">${e(x.ten)}</span><span class="ctm-m">${e(meta) || 'trống'}</span></button>`; }).join('')}</div>` + (ds.length || !D.so_clip ? '' : `<p class="ctm-note">Thư mục này không có thư mục con.</p>`)
        : `<p class="ctm-note">${D.con.length ? 'Không có thư mục khớp “' + e(tim.value) + '”.' : 'Thư mục này không có thư mục con.'}${D.so_clip ? ' Có ' + D.so_clip + ' clip ngay trong thư mục này: bấm “Dùng thư mục này”.' : ''}</p>`;
      const v = vun(D.thu_muc);
      q('.ctm-vun', root).innerHTML = v.map((x, i) => `<button type="button" class="ctm-v" data-p="${e(x.p)}"${i === v.length - 1 ? ' aria-current="true"' : ''}>${e(x.ten)}</button>`).join('<span class="ctm-s">›</span>');
      q('[data-x=len]', root).disabled = !D.cha;
      q('.ctm-nay', root).innerHTML = D.so_clip ? `<b>${e(v.length ? v[v.length - 1].ten : D.thu_muc)}</b>: ${D.so_clip} clip` : `<span class="ctm-mo">Bấm 1 thư mục để chọn</span>`;
      const b = q('.ctm-dung', root); b.hidden = !D.so_clip; b.textContent = 'Dùng thư mục này (' + D.so_clip + ' clip)';
      const cur = chuan(D.thu_muc), mon = (p, ten, ic, tt) => `<button type="button" class="ctm-l${chuan(p) === cur ? ' on' : ''}" data-p="${e(p)}" title="${e(tt || p)}"><span>${ic}</span>${e(ten)}</button>`;
      const gd = ganDay().filter(p => chuan(p) !== cur).slice(0, 6);
      q('.ctm-side', root).innerHTML = `<h4>Lối tắt</h4>` + (D.nhanh || []).map((x, i) => mon(x.p, x.ten, i === 0 && D.goc && chuan(x.p) === chuan(D.goc) ? '⌂' : '📁')).join('')
        + ((D.o_dia || []).length ? `<h4>Ổ đĩa</h4>` + D.o_dia.map(d => mon(d, 'Ổ ' + d.replace(/[\\/]$/, ''), '💽')).join('') : '')
        + (gd.length ? `<h4>Gần đây</h4>` + gd.map(p => mon(p, (vun(p).pop() || {ten: p}).ten, '🕘', p)).join('') : '');
    }
    async function mo(p) {
      const n = ++lan; body.classList.add('cho');
      try {
        const r = await fetch('/api/thu-muc?p=' + encodeURIComponent(p || ''));
        const j = await r.json(); if (n !== lan) return;
        if (!r.ok) throw new Error(j.err || 'Lỗi ' + r.status);
        D = j; tim.value = ''; ve(); body.scrollTop = 0;
        const on = q('.ctm-c.on', body); if (on) on.scrollIntoView({block: 'nearest'});
      } catch (er) { if (n !== lan) return; if (!D) { D = {thu_muc: p || '', cha: '', con: [], so_clip: 0, o_dia: []}; ve(); } body.insertAdjacentHTML('afterbegin', `<p class="ctm-note ctm-loi">${e(er.message)}</p>`); }
      finally { if (n === lan) body.classList.remove('cho'); }
      if (o.noi) setTimeout(() => tim.focus(), 0);
    }
    const chon = p => { dang = p; nhoGanDay(p); if (D) ve(); o.onChon && o.onChon(p); };
    root.addEventListener('click', ev => {
      const x = ev.target.closest('[data-x]'); if (x) { if (x.dataset.x === 'dong') return o.onDong && o.onDong(); if (x.dataset.x === 'len' && D && D.cha) return mo(D.cha); if (x.dataset.x === 'dung' && D) return chon(D.thu_muc); }
      const v = ev.target.closest('[data-p]'); if (v) return mo(v.dataset.p);
      const c = ev.target.closest('.ctm-c'); if (c && D) { const it = D.con[+c.dataset.i]; if (!it) return; if (!it.so_thu_muc && it.so_clip) return chon(it.p); mo(it.p); }
    });
    tim.addEventListener('input', () => D && ve());
    tim.addEventListener('keydown', ev => { if (ev.key === 'Enter') { ev.preventDefault(); const t = tim.value.trim().replace(/^"+|"+$/g, '');
        if (/^([A-Za-z]:[\\/]?|[\\/]{1,2}[^\\/])/.test(t)) return mo(t);   // dán đường dẫn
        const c = q('.ctm-c', body); if (c) c.click(); }
      else if (ev.key === 'Backspace' && !tim.value && D && D.cha) { ev.preventDefault(); mo(D.cha); } });
    mo(o.batDau || '');
    return {mo, get thuMuc() { return D && D.thu_muc; }, datChon(p) { dang = p; if (D) ve(); }};
  }
  function chonThuMuc(batDau, dangChon) {
    return new Promise(xong => {
      const bg = document.createElement('div'); bg.className = 'ctm-bg';
      const hop = document.createElement('div'); hop.setAttribute('role', 'dialog'); hop.setAttribute('aria-modal', 'true'); hop.setAttribute('aria-label', 'Chọn thư mục clip');
      bg.append(hop); document.body.append(bg);
      const dong = p => { document.removeEventListener('keydown', phim, true); bg.remove(); xong(p || null); };
      const phim = ev => { if (ev.key === 'Escape') { ev.preventDefault(); ev.stopPropagation(); dong(); } };
      document.addEventListener('keydown', phim, true);
      bg.addEventListener('click', ev => { if (ev.target === bg) dong(); });
      gan(hop, {batDau, dangChon, noi: true, onChon: dong, onDong: () => dong()});
    });
  }
  chonThuMuc.gan = gan;
  chonThuMuc.cha = p => { const v = vun(p); return v.length > 1 ? v[v.length - 2].p : ''; };
  return chonThuMuc;
})();
