/* ============================== KIỂU CHỮ CÓ SẴN + FONT RIÊNG TỪNG CHỮ (4/11) ==============================
   Anh duyệt 4/11 10:4x: "bộ mẫu chữ bấm là dùng (font, màu, viền, nền) cho nhãn / giá / tiêu đề, chọn font riêng từng chữ".
   Bảng mẫu + font: <engine>/kieu_chu.json (bộ dựng ve_chu.py / chu_rieng.py vẽ theo đúng bảng này), lấy qua
   GET /api/sua-tay/kieu-chu (kieu_chu.py); file font lấy ở /api/sua-tay/kieu-chu/font/<file> -> @font-face 'PK-<id>'.
   Kế hoạch (chỉ thêm khoá): chu.nhan_chu[i].kieu · chu.the_gia.kieu · chu.kieu_hook · chu.kieu_tieu_de =
     {mau_co_san, font, mau, mau2, vien, vien_day, nen, khung, nen_vien, bong, co, in_hoa}  (chỉ {font} = giữ kiểu video, đổi font)
   Nơi chọn: Thư viện › Chữ (nhóm "Kiểu chữ" + "Font chữ"), menu chuột phải của chữ, bảng phải (tab Chữ, ô "Kiểu chữ").
   Mỗi lần bấm = 1 bước Ctrl+Z (doi()), tự lưu như mọi sửa khác. Phụ đề theo kiểu cả video (không có kiểu riêng). */
const KC = {bang: null, dang: false, loi: ''};
const KC_MAU = {vang: '#FFD600', trang: '#FFFFFF', xanh: '#074D3A', xanh_toi: '#03231A', den: '#000000', xanh_sang: '#3D7465'};
const KC_LOAI = {nhan: 'Nhãn', gia: 'Thẻ giá', hook: 'Hook', tieu_de: 'Tiêu đề'};
const kcUrlFont = f => '/api/sua-tay/kieu-chu/font/' + encodeURIComponent(f);
function kcMau(id) { return ((KC.bang || {}).mau || []).find(m => m.id === id); }
function kcFont(id) { return ((KC.bang || {}).font || []).find(f => f.id === id); }
async function kcTai() {
  if (KC.dang || KC.bang) return; KC.dang = true;
  try {
    const b = await api('/api/sua-tay/kieu-chu');
    KC.bang = b; KC.loi = '';
    const css = [];
    b.font.forEach(f => {
      const ho = `'PK-${f.id}'`;
      if (typeof f.file === 'object') [['Black', 900], ['ExtraBold', 800], ['Bold', 700]].forEach(([v, w]) => css.push(`@font-face{font-family:${ho};src:url(${kcUrlFont(f.file[v])}) format('truetype');font-weight:${w};font-display:swap}`));
      else css.push(`@font-face{font-family:${ho};src:url(${kcUrlFont(f.file)}) format('truetype');font-weight:1 1000;font-stretch:50% 200%;font-display:swap}`);
      const them = Object.entries(f.them || {}).map(([k, v]) => `'${k}' ${v}`).join(',');
      css.push(`.kcf-${f.id}{font-family:${ho},var(--f);font-synthesis:none${them ? ';font-variation-settings:' + them : ''}}`);
    });
    let st = document.getElementById('kcFonts'); if (!st) { st = document.createElement('style'); st.id = 'kcFonts'; document.head.append(st); }
    st.textContent = css.join('\n');
  } catch (e) { KC.loi = e.message; }
  KC.dang = false;
  if (S.plan) { veTV(true); veBen(true); }
}
const kcDam = (f, i) => !f ? 900 : f.dam ? f.dam[i] : [900, 800, 700][i];   // độ đậm vai Black / ExtraBold (CSS = trục wght PIL)

/* ---------- chữ nhận kiểu: k = 'hook' | 'tieu_de' | _k nhãn | _k thẻ giá ---------- */
function kcLoai(k, p = S.plan) {
  if (!k || !p) return null; const chu = p.chu || {};
  if (k === 'hook') return (chu.hook || []).some(x => String(x || '').trim()) ? 'hook' : null;
  if (k === 'tieu_de') return String(chu.tieu_de || '').trim() ? 'tieu_de' : null;
  if (chu.the_gia && chu.the_gia._k === k) return 'gia';
  return (chu.nhan_chu || []).some(n => n._k === k) ? 'nhan' : null;
}
function kcLay(p, k) {
  const chu = p.chu || {};
  if (k === 'hook') return chu.kieu_hook || null;
  if (k === 'tieu_de') return chu.kieu_tieu_de || null;
  if (chu.the_gia && chu.the_gia._k === k) return chu.the_gia.kieu || null;
  const n = (chu.nhan_chu || []).find(x => x._k === k); return n ? n.kieu || null : null;
}
function kcDat(p, k, kv) {
  const chu = p.chu = p.chu || {}, bo = !kv || !Object.keys(kv).length;
  const dat = (o, khoa) => { if (bo) delete o[khoa]; else o[khoa] = kv; };
  if (k === 'hook') return dat(chu, 'kieu_hook');
  if (k === 'tieu_de') return dat(chu, 'kieu_tieu_de');
  if (chu.the_gia && chu.the_gia._k === k) return dat(chu.the_gia, 'kieu');
  const n = (chu.nhan_chu || []).find(x => x._k === k); if (n) dat(n, 'kieu');
}
function kcTen(k, du) {   // du: không rút gọn (cho data-tip)
  const l = kcLoai(k), chu = S.plan.chu || {}; if (!l) return '';
  const cat = s => { s = String(s || '').replace(/\|/g, ' ').trim(); return !du && s.length > 22 ? s.slice(0, 21) + '…' : s; };
  if (l === 'nhan') { const n = chu.nhan_chu.find(x => x._k === k); return 'Nhãn “' + cat(n.chu) + '”'; }
  if (l === 'gia') return 'Thẻ giá' + (chu.the_gia.gia ? ' “' + cat(chu.the_gia.gia) + '”' : '');
  if (l === 'hook') return 'Hook “' + cat((chu.hook || []).filter(Boolean).join(' / ')) + '”';
  return 'Tiêu đề “' + cat(chu.tieu_de) + '”';
}
function kcLucVach() {   // chữ đang hiện ở vạch đỏ (nhãn / thẻ giá trước, rồi hook)
  const v = S.view || {}, gio = v.gio || {}, chu = S.plan.chu || {}, t = S.t;
  const trong = k => { const g = gio[k]; return g && !g.an && g.t0 != null && t >= g.t0 - 0.02 && t < g.t1; };
  const n = (chu.nhan_chu || []).find(x => trong(x._k)); if (n) return n._k;
  if (chu.the_gia && trong(chu.the_gia._k)) return chu.the_gia._k;
  if (v.hook_t && t >= v.hook_t[0] && t < v.hook_t[1] && kcLoai('hook')) return 'hook';
  return null;
}
function kcDich() { return S.selLoai === 'chu' && kcLoai(S.sel.k) ? S.sel.k : null; }
function kcDichBam() {   // bấm mẫu / font mà chưa chọn chữ: lấy chữ ở vạch đỏ; không có thì nhắc
  const k = kcDich(); if (k) return k;
  if (S.selLoai === 'chu' && String(S.sel.k || '').startsWith('p')) { toast('Phụ đề đi theo kiểu chữ cả video (tab Kiểu). Kiểu riêng dùng cho nhãn, thẻ giá, hook, tiêu đề', true); return null; }
  const v = kcLucVach(); if (v) { S.sel.k = v; S.selLoai = 'chu'; return v; }
  toast('Chọn 1 nhãn, thẻ giá hoặc hook trước: bấm thanh chữ trên timeline (hoặc đưa vạch đỏ tới chữ đó)', true); return null;
}
function kcChon(k) { S.sel.k = k; S.selLoai = 'chu'; if (S.tab !== 'chu') { S.tab = 'chu'; veTabs(); } veBen(true); veTimeline(); }
function kcToi(k) {   // vạch đỏ tới chữ (khung xem cho thấy ngay kiểu mới)
  const v = S.view || {}, g = (v.gio || {})[k], tt = k === 'hook' ? v.hook_t : k === 'tieu_de' ? (v.hook_t ? [v.hook_t[1], v.T] : null) : g && !g.an ? [g.t0, g.t1] : null;
  if (tt && !(S.t >= tt[0] && S.t < tt[1])) { dung(); tua(tt[0] + (k === 'tieu_de' ? 0.3 : 0.05)); giuVach(); }
}

/* ---------- áp ---------- */
function kcDu(m) {   // mẫu -> kiểu đầy đủ ghi vào kế hoạch (mẫu đổi sau này thì chữ đã áp không đổi theo)
  const md = KC.bang.mau_mac_dinh || {}, kv = {mau_co_san: m.id};
  Object.keys(md).forEach(x => { const v = x in m ? m[x] : md[x]; if (v != null || ['vien', 'nen', 'nen_vien', 'bong'].includes(x)) kv[x] = v; });
  if (!kv.mau2) kv.mau2 = kv.mau === 'xanh' ? 'xanh' : kv.mau === 'trang' ? 'vang' : 'trang';
  return kv;
}
function kcApMau(id, k) {
  const m = kcMau(id); if (!m) return; k = k || kcDichBam(); if (!k) return;
  const ten = kcTen(k); dung();
  doi(p => kcDat(p, k, kcDu(m)));
  kcToi(k); toast('Đã áp mẫu “' + m.ten + '” cho ' + ten + ' · Ctrl+Z để bỏ');
}
function kcApFont(fid, k) {
  k = k || kcDichBam(); if (!k) return;
  const cu = kcLay(S.plan, k) || {}, m = kcMau(cu.mau_co_san), kv = Object.assign({}, cu);
  if (fid) kv.font = fid; else if (m) kv.font = m.font; else delete kv.font;
  if (JSON.stringify(kv) === JSON.stringify(cu)) return;
  const ten = kcTen(k), f = kcFont(kv.font); dung();
  doi(p => kcDat(p, k, kv));
  kcToi(k); toast((f ? 'Font ' + f.ten : 'Font theo kiểu video') + ' cho ' + ten + ' · Ctrl+Z để bỏ');
}
function kcCo(k, d) {
  const cu = kcLay(S.plan, k); if (!cu || !Object.keys(cu).some(x => x !== 'font')) return;
  const co = clamp(Math.round(((+cu.co || 1) + d) * 100) / 100, 0.7, 1.4); if (co === (+cu.co || 1)) return;
  doi(p => kcDat(p, k, Object.assign({}, cu, {co}))); kcToi(k);
}
function kcBo(k) {
  if (!kcLay(S.plan, k)) return; const ten = kcTen(k); dung();
  doi(p => kcDat(p, k, null)); kcToi(k); toast('Bỏ kiểu riêng của ' + ten + ': chữ theo kiểu cả video · Ctrl+Z để lấy lại');
}

/* ---------- vẽ ô mẫu bằng CSS (cùng font, màu, viền, nền như bộ dựng vẽ) ---------- */
function kcCss(kv, dong2) {   // kiểu -> style chữ mẫu, cỡ theo em (1em = cỡ ô mẫu, ô co theo bề ngang: .kc-in dùng cqi)
  const f = kcFont(kv.font), k = (f ? +f.co || 1 : 1) * (+kv.co || 1) * (dong2 ? 0.62 : 1);
  const st = [`font-size:${k.toFixed(3)}em`, `font-weight:${kcDam(f, dong2 ? 1 : 0)}`, `color:${KC_MAU[dong2 ? kv.mau2 || 'trang' : kv.mau] || KC_MAU.vang}`];
  if (kv.vien) st.push(`-webkit-text-stroke:${(2 * (kv.vien_day || 8) / 92 * (dong2 ? 0.7 : 1)).toFixed(3)}em ${KC_MAU[kv.vien]}`, 'paint-order:stroke fill');
  if (kv.in_hoa !== false) st.push('text-transform:uppercase');
  if (kv.bong === 'dam') st.push('text-shadow:0 .12em .3em rgba(0,0,0,.95),0 .06em .12em rgba(0,0,0,.8)');
  return st.join(';');
}
function kcNenCss(kv) {
  if (!kv.nen) return '';
  const nen = {xanh: 'linear-gradient(165deg,#256252 0%,#074D3A 42%,#053427 100%)', vang: KC_MAU.vang, trang: 'rgba(255,255,255,.96)', toi: 'rgba(3,35,26,.84)'}[kv.nen];
  const vien = kv.nen_vien === 'trang' ? 'inset 0 0 0 1px rgba(255,255,255,.5)' : kv.nen_vien === 'xanh_sang' ? 'inset 0 0 0 1px rgba(61,116,101,.85)' : '';
  return `background:${nen};padding:.2em .38em;border-radius:${kv.khung === 'vien_thuoc' ? '999px' : '.3em'}${vien ? ';box-shadow:' + vien : ''}`;
}
function kcMauHtml(kv, txt, txt2) {
  const f = kcFont(kv.font), bong = kv.bong === 'noi' ? ' kc-noi' : kv.bong === 'mem' ? ' kc-mem' : '';
  return `<span class="kc-o${bong}${f ? ' kcf-' + f.id : ''}" style="${kcNenCss(kv)}"><b style="${kcCss(kv)}">${esc(txt)}</b>${txt2 ? `<small style="${kcCss(kv, true)}">${esc(txt2)}</small>` : ''}</span>`;
}
function kcLuoi(dich, nho) {   // lưới ô mẫu: mẫu hợp loại chữ đang chọn xếp trước
  const l = dich ? kcLoai(dich) : null, cu = dich ? kcLay(S.plan, dich) || {} : {}, x = typeof canhChon === 'function' ? canhChon() : null;
  const bg = x && typeof anhCanh === 'function' ? `background-image:url('${anhCanh(x.c)}')` : '';
  const ds = KC.bang.mau || [];   // thứ tự cố định (dễ nhớ chỗ); mẫu hợp loại chữ có nhãn "Hợp" (khi chỉ vài mẫu hợp: giá, hook, tiêu đề)
  const nHop = l ? ds.filter(m => m.hop.includes(l)).length : 0;
  return `<div class="tv-grid kc-luoi${nho ? ' nho' : ''}">${ds.map(m => { const on = cu.mau_co_san === m.id, hop = l && nHop <= 5 && m.hop.includes(l);
    return `<button type="button" class="tvx kc-m${on ? ' on' : ''}" data-kcmau="${esc(m.id)}" data-tip="${esc(m.ten + ': ' + m.goi + (dich ? ' · bấm để áp cho ' + kcTen(dich) : ' · chọn 1 chữ rồi bấm'))}" aria-pressed="${on}">
      <span class="xv kc-xv" style="${bg}"><span class="kc-in">${kcMauHtml(kcDu(m), m.vi_du || 'PIN 98%')}</span>${on ? `<span class="tick">${icon('dauTick')}</span>` : ''}${hop ? '<span class="tv-tag">Hợp</span>' : ''}</span>
      <span class="tvx-ten">${esc(m.ten)}</span></button>`; }).join('')}</div>`;
}
function kcFonts(dich) {
  const cu = dich ? kcLay(S.plan, dich) || {} : {}, m = kcMau(cu.mau_co_san), dang = cu.font || null;
  const goc = m ? 'Font của mẫu' : 'Theo kiểu video', onGoc = m ? dang === m.font : !dang;
  return `<div class="kc-fonts"><button type="button" class="tvchip${onGoc ? ' on' : ''}" data-kcfont="" aria-pressed="${onGoc}" data-tip="${esc(m ? 'Dùng font của mẫu “' + m.ten + '”: ' + ((kcFont(m.font) || {}).ten || '') : 'Font theo kiểu chữ cả video (tab Kiểu › Bộ font)')}">${onGoc ? icon('dauTick') : ''}${goc}</button>`
    + (KC.bang.font || []).map(f => { const on = dang === f.id && !(m && m.font === f.id && onGoc);
      return `<button type="button" class="tvchip kc-f kcf-${esc(f.id)}${on ? ' on' : ''}${f.co_file === false ? ' thieu' : ''}" data-kcfont="${esc(f.id)}" aria-pressed="${on}" style="font-weight:${kcDam(f, 0)}" data-tip="${esc(f.ten + ': ' + f.goi + (f.co_file === false ? ' · máy thiếu file font, chép engine/fonts' : ''))}">${on ? icon('dauTick') : ''}${esc(f.ten)}</button>`; }).join('') + `</div>`;
}
function kcDsDich() {   // các chữ có thể nhận kiểu (để bấm chọn nhanh)
  const chu = S.plan.chu || {}, ds = [];
  if (kcLoai('hook')) ds.push('hook');
  if (chu.the_gia && String(chu.the_gia.gia || '').trim()) ds.push(chu.the_gia._k);
  (chu.nhan_chu || []).forEach(n => { if (String(n.chu || '').trim()) ds.push(n._k); });
  if (kcLoai('tieu_de')) ds.push('tieu_de');
  return ds;
}
function kcChips(dich) {
  return `<div class="kc-dich-ds">${kcDsDich().map(k => `<button type="button" class="tvchip${k === dich ? ' on' : ''}${kcLay(S.plan, k) ? ' co' : ''}" data-kcchon="${esc(k)}" data-tip="${esc(kcTen(k, true) + (kcLay(S.plan, k) ? ' · đang có kiểu riêng (chấm vàng)' : ' · bấm để chọn'))}">${esc(kcTen(k))}</button>`).join('') || '<span class="note">Video chưa có nhãn, thẻ giá hay hook.</span>'}</div>`;
}

/* ---------- Thư viện › Chữ: nhóm "Kiểu chữ" + "Font chữ" ---------- */
function kcTv() {
  if (!KC.bang) { if (!KC.dang && !KC.loi) setTimeout(kcTai, 0); return tvTieuDe('Kiểu chữ', '') + `<p class="tv-note${KC.loi ? ' err' : ' tv-cho'}">${esc(KC.loi || 'Đang tải kiểu chữ…')}</p>`; }
  const d = kcDich(), cu = d ? kcLay(S.plan, d) : null;
  return `<div id="kcTv">` + tvTieuDe('Kiểu chữ', d ? 'áp cho ' + kcTen(d) : 'chọn 1 chữ trước', 'Bấm thanh nhãn / thẻ giá / hook trên timeline (hoặc chữ dưới đây) rồi bấm mẫu. Chưa chọn thì mẫu áp cho chữ đang hiện ở vạch đỏ.')   // 4/11 tối: câu hướng dẫn vào dấu (i)
    + kcChips(d)
    + kcLuoi(d) + tvTieuDe('Font chữ', d ? (cu && cu.font ? (kcFont(cu.font) || {}).ten : 'theo kiểu video') : 'font riêng cho 1 chữ') + kcFonts(d)
    + (d && cu ? `<div class="tv-hang"><button type="button" class="btn small ghost" data-kcbo="${esc(d)}" data-tip="Bỏ mẫu + font riêng: ${esc(kcTen(d))} theo kiểu chữ cả video">${icon('boHet')}Bỏ kiểu riêng</button></div>` : '') + `</div>`;
}
const kcTvChuGoc = tvChu;
tvChu = function () {   // chèn nhóm Kiểu chữ trước "Kiểu chữ cả video"
  const h = kcTvChuGoc(), moc = h.indexOf('<div class="tv-h"><h3>Kiểu chữ cả video');
  return moc < 0 ? h + kcTv() : h.slice(0, moc) + kcTv() + h.slice(moc);
};
const kcKhoaTvGoc = khoaTV;
khoaTV = function () {
  if (S.tv.tab !== 'chu' || !S.plan) return kcKhoaTvGoc();
  const d = kcDich(), g = kcKhoaTvGoc();   // khoá gốc là mảng JSON (veTV đọc lại phần tử 0): nối thêm 1 phần tử
  return g.slice(0, -1) + ',' + JSON.stringify(['kc', !!KC.bang, KC.loi, d, d && kcLay(S.plan, d), kcDsDich().map(k => [k, kcTen(k), !!kcLay(S.plan, k)])]) + ']';
};

/* ---------- bảng phải (tab Chữ): ô "Kiểu chữ" của chữ đang chọn ---------- */
function kcBen() {
  if (!KC.bang) { if (!KC.dang && !KC.loi) setTimeout(kcTai, 0); return ''; }
  const d = kcDich(), cu = d ? kcLay(S.plan, d) : null, coMau = cu && Object.keys(cu).some(x => x !== 'font');
  let h = `<div class="box kc-ben" id="kcBen"><h2 class="sec">Kiểu chữ</h2>`;   // chữ đang chọn = chip sáng ngay dưới (bảng hẹp: không nhồi vào dòng tiêu đề)
  h += kcChips(d);
  if (!d) return h + `<p class="note">Chọn 1 chữ ở trên (hoặc bấm thanh chữ trên timeline) để chọn mẫu chữ và font riêng cho chữ đó.</p></div>`;
  h += kcLuoi(d, true) + `<div class="lbl">Font</div>` + kcFonts(d);
  h += `<div class="row kc-hang">${coMau ? `<span class="lbl">Cỡ</span><button type="button" class="btn small icon" data-kcco="-0.1" data-tip="Nhỏ hơn" ${(+cu.co || 1) <= 0.7 ? 'disabled' : ''}>−</button><b class="kc-co">${Math.round((+cu.co || 1) * 100)}%</b><button type="button" class="btn small icon" data-kcco="0.1" data-tip="To hơn" ${(+cu.co || 1) >= 1.4 ? 'disabled' : ''}>+</button>` : `<span class="note grow">${cu ? 'Chỉ đổi font, giữ kiểu chữ của video.' : 'Đang theo kiểu chữ cả video.'}</span>`}<span class="sp"></span>${cu ? `<button type="button" class="btn small ghost" data-kcbo="${esc(d)}" data-tip="Bỏ mẫu + font riêng: ${esc(kcTen(d))} theo kiểu chữ cả video">Bỏ kiểu riêng</button>` : ''}</div>`;
  return h + '</div>';
}
const kcBenChuGoc = benChu;
benChu = function () { return kcBen() + kcBenChuGoc(); };
function kcVeBen() {   // chỉ vẽ lại ô Kiểu chữ (đang gõ ở ô khác: giữ con trỏ)
  const o = document.getElementById('kcBen'); if (!o || S.tab !== 'chu') return;
  const t = document.createElement('div'); t.innerHTML = kcBen(); if (t.firstElementChild) o.replaceWith(t.firstElementChild);
  $$('#pane .it[data-row]').forEach(x => x.classList.toggle('sel', x.dataset.row === S.sel.k));
}
$('#pane').addEventListener('focusin', e => {   // bấm vào ô gõ của 1 chữ = chọn chữ đó (ô Kiểu chữ đổi theo)
  const f = (e.target.dataset || {}).f || ''; if (!S.plan) return;
  const k = /^hook[01]$/.test(f) ? 'hook' : f === 'tieu_de' ? 'tieu_de' : (f === 'gia' || f === 'phu') ? ((S.plan.chu || {}).the_gia || {})._k : f.startsWith('nhan:') ? f.slice(5) : null;
  if (!k || (S.sel.k === k && S.selLoai === 'chu')) return;
  S.sel.k = k; S.selLoai = 'chu'; kcVeBen(); veTimeline(); veTV();
});
let kcGoT = 0;
$('#pane').addEventListener('input', e => {   // đang gõ chữ (vd tiêu đề mới gõ): ô Kiểu chữ + Thư viện theo kịp (không đụng ô đang gõ)
  if (!/^(hook[01]|tieu_de|gia|phu|nhan:)/.test((e.target.dataset || {}).f || '')) return;
  clearTimeout(kcGoT); kcGoT = setTimeout(() => { kcVeBen(); veTV(); }, 250);
});

/* ---------- bấm ---------- */
function kcBam(e) {
  const t = e.target.closest('button'); if (!t || t.disabled || !S.plan) return;
  if (t.dataset.kcmau) { e.stopPropagation(); return kcApMau(t.dataset.kcmau); }
  if (t.dataset.kcfont != null) { e.stopPropagation(); return kcApFont(t.dataset.kcfont || null); }
  if (t.dataset.kcchon) { e.stopPropagation(); const k = t.dataset.kcchon; kcChon(k); kcToi(k); return; }
  if (t.dataset.kcbo) { e.stopPropagation(); return kcBo(t.dataset.kcbo); }
  if (t.dataset.kcco) { e.stopPropagation(); const k = kcDich(); if (k) kcCo(k, +t.dataset.kcco); }
}
$('#lib').addEventListener('click', kcBam);
$('#pane').addEventListener('click', kcBam, true);
// bấm phải vào ô mẫu / font trong Thư viện: chọn chữ nhận kiểu
$('#lib').addEventListener('contextmenu', e => {
  const t = e.target.closest('#libPane [data-kcmau], #libPane [data-kcfont]'); if (!t || !S.plan || !KC.bang) return;
  e.preventDefault(); e.stopPropagation();
  const mau = t.dataset.kcmau, fid = t.dataset.kcfont, ten = mau ? (kcMau(mau) || {}).ten : fid ? (kcFont(fid) || {}).ten : 'Font theo kiểu video';
  moMenu(e.clientX, e.clientY, [{nhom: (mau ? 'Mẫu chữ · ' : 'Font · ') + ten}, ...kcDsDich().map(k => ({t: 'Áp cho ' + kcTen(k), ic: 'nhan', chon: mau ? (kcLay(S.plan, k) || {}).mau_co_san === mau : false, f: () => { kcChon(k); mau ? kcApMau(mau, k) : kcApFont(fid || null, k); }}))]);
});

/* ---------- menu chuột phải của chữ (timeline / bảng phải): Kiểu chữ › · Font chữ › · Bỏ kiểu riêng ---------- */
function kcMenu(k) {
  if (!KC.bang || !kcLoai(k)) return [];
  const cu = kcLay(S.plan, k) || {}, m = kcMau(cu.mau_co_san), l = kcLoai(k);
  const ds = KC.bang.mau || [];
  return [{t: 'Kiểu chữ' + (m ? ': ' + m.ten : ''), ic: 'nhan', sub: [{nhom: 'Mẫu chữ cho ' + KC_LOAI[l].toLowerCase()}, ...ds.map(x => ({t: x.ten, chon: cu.mau_co_san === x.id, nhan: x.hop.includes(l) ? 'hợp' : '', f: () => kcApMau(x.id, k)}))]},
    {t: 'Font chữ' + (cu.font ? ': ' + ((kcFont(cu.font) || {}).ten || cu.font) : ''), sub: [{t: m ? 'Font của mẫu' : 'Theo kiểu video', chon: m ? cu.font === m.font : !cu.font, f: () => kcApFont(null, k)},
      '-', ...(KC.bang.font || []).map(f => ({t: f.ten, chon: cu.font === f.id && !(m && m.font === f.id), f: () => kcApFont(f.id, k)}))]},
    Object.keys(cu).length && {t: 'Bỏ kiểu riêng', ic: 'boHet', f: () => kcBo(k)}];
}
const kcMenuChuGoc = menuChu;
menuChu = function (k, t, o) {
  const ds = kcMenuChuGoc(k, t, o), them = kcMenu(k); if (!them.length) return ds;
  const i = ds.lastIndexOf('-');   // trước "Xoá …"
  ds.splice(i < 0 ? ds.length : i, 0, '-', ...them); return ds;
};

kcTai();
