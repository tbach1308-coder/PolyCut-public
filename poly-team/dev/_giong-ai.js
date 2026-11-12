/* ============================== GIỌNG ĐỌC AI TRONG SỬA TAY (3/11) ==============================
   Anh gõ lời đọc (mỗi dòng 1 câu), chọn giọng + tốc độ -> "Tạo giọng" (máy chủ chạy engine giong.py: 25 giọng VieNeu chạy trên
   máy + 2 giọng Microsoft cần mạng) -> nghe lại -> "Áp vào video": plan.giong + phụ đề theo giọng thành 1 bước Ctrl+Z.
   Lúc xuất, bộ dựng trộn giọng và tự hạ tiếng trong clip khi có giọng. "Bỏ giọng AI": plan.giong = null.
   Dùng: veGiongAI(phanTu) vẽ bảng vào 1 khung (tab Thư viện), moGiongAI() mở hộp nổi. */
const GA = {ds: null, chon: null, toc: '+10%', loi: null, v: null, tt: null, hen: null, el: null, thay: true, phong: null, kieu: null};   // thay: giọng thay hẳn tiếng clip (4/11); phong / kieu: kiểu trend (r39, _mod-giong-trend.js)
const gaThay = () => S.plan && S.plan.giong ? !!S.plan.giong.thay_tieng : GA.thay;
// 4/11 anh: "giọng đọc ai chỉ lấy giọng phổ biến" -> ô chọn chỉ hiện các giọng này (theo thứ tự); giọng khác video đang dùng vẫn hiện ở nhóm "Đang dùng"
const GIONG_PHO_BIEN = ['vn-adam', 'vn-adam-bua', 'vn-hai-dang', 'vn-truc-ly', 'vn-mai-anh', 'vn-thuy-dung', 'nu', 'nam'];
async function napGiongDs() {
  if (!GA.ds) { GA.ds = await api('/api/sua-tay/giong-ds'); }
  if (!GA.chon) gaChonTuPlan();
  return GA.ds;
}
function gaChonTuPlan() {   // giọng + kiểu trend (r39) của video đang mở
  const g = S.plan && S.plan.giong;
  GA.chon = (g && g.giong) || GA.ds.mac_dinh; GA.phong = (g && g.phong) || null; GA.kieu = (g && g.kieu_trend) || null;
}
function giongUrl(g) { g = g || (S.plan || {}).giong; return g && g.local ? '/api/sua-tay/giong?v=' + encodeURIComponent(S.v) + '&p=' + encodeURIComponent(g.local) : ''; }
function gaLoiMacDinh() {
  const g = S.plan.giong; if (g && g.loi) return g.loi;
  return (S.plan.phu_de || []).map(x => String(x.chu || '').replace(/\|/g, '').trim()).filter(Boolean).join('\n');
}
function gaUoc(t) {   // ước độ dài giọng: ~4,2 từ/giây ở tốc độ vừa + nghỉ giữa câu
  const dong = String(t || '').split('\n').filter(x => x.trim()), tu = dong.join(' ').split(/\s+/).filter(Boolean).length;
  return tu / ({'-5%': 3.6, '+10%': 4.2, '+20%': 4.7}[GA.toc] || 4.2) + 0.25 * dong.length;
}
function veGiongAI(el) {
  GA.el = el;
  if (GA.v !== S.v) { GA.v = S.v; GA.loi = null; GA.tt = null; GA.chon = null; }
  if (!GA.ds) { el.innerHTML = '<p class="note">Đang tải danh sách giọng…</p>'; napGiongDs().then(() => veGA()).catch(e => { el.innerHTML = `<p class="note err">${esc(e.message)}</p>`; }); return; }
  if (!GA.chon) gaChonTuPlan();
  veGA();
}
function gaTomUoc() {
  const T = (S.view || {}).T || 0, u = gaUoc(GA.loi);
  return `khoảng ${gs(u)}${T ? ' · video ' + gs(T) : ''}` + (T && u > T + 0.5 ? ` · <b class="ga-warn">dài hơn video ${gs(u - T)}</b>` : '');
}
function veGA() {
  const el = GA.el; if (!el || !el.isConnected || !S.plan) return;
  if (GA.loi == null) GA.loi = gaLoiMacDinh();
  const g = S.plan.giong, ds = GA.ds.ds, T = (S.view || {}).T || 0, tt = GA.tt;
  const pb = x => GIONG_PHO_BIEN.indexOf(x.id) >= 0, hang = x => GIONG_PHO_BIEN.indexOf(x.id);
  const nhom = [['Đang dùng', x => x.id === GA.chon && !pb(x)], ['Giọng nam · chạy trên máy', x => pb(x) && x.nguon === 'vieneu' && x.gioi === 'nam'],
    ['Giọng nữ · chạy trên máy', x => pb(x) && x.nguon === 'vieneu' && x.gioi !== 'nam'], ['Microsoft · cần mạng', x => pb(x) && x.nguon === 'microsoft']];
  const da = new Set(), opt = nhom.map(([t, f]) => { const xs = ds.filter(x => !da.has(x.id) && f(x)).sort((a, b) => hang(a) - hang(b)); xs.forEach(x => da.add(x.id));
    return xs.length ? `<optgroup label="${esc(t)}">${xs.map(x => `<option value="${esc(x.id)}"${x.id === GA.chon ? ' selected' : ''}>${esc(x.ten)} · ${esc([x.nguon === 'microsoft' || !pb(x) ? x.gioi : '', x.mien, x.nguon === 'microsoft' ? '' : x.cach].filter(Boolean).join(', '))}</option>`).join('')}</optgroup>` : ''; }).join('');
  el.innerHTML = `<div class="ga">
    ${g ? `<div class="ga-dang"><span>🔊 Video đang dùng giọng AI${g.ten ? ' <b>' + esc(g.ten) + '</b>' : ''}${g.giay ? ' · ' + gs(g.giay) : ''} · tiếng clip ${g.thay_tieng ? 'tắt' : 'nhỏ làm nền'}</span><button type="button" class="btn small danger" data-ga="bo">Bỏ giọng AI</button></div>` : ''}
    <div class="ga-h"><b>Lời đọc</b><span class="note">mỗi dòng 1 câu · <span class="ga-uoc">${gaTomUoc()}</span></span></div>
    <textarea class="inp ga-loi" rows="7" spellcheck="false" placeholder="Vd:&#10;Anh em ơi, iPad Pro M1 12.9 về rồi nè&#10;Máy đẹp keng, pin 98%, bao test 7 ngày&#10;Giá chỉ 13 triệu 9, ghé Poly test máy nha">${esc(GA.loi)}</textarea>
    ${typeof gtVe === 'function' ? gtVe('ga') : `<div class="ga-hang"><span class="lbl">Giọng</span><select class="inp ga-giong">${opt}</select><button type="button" class="btn small" data-ga="thu" title="Nghe 1 câu mẫu bằng giọng + tốc độ đang chọn">▶ Nghe thử</button></div>`}
    <div class="ga-hang"><span class="lbl" title="Tiếng gốc quay trong clip khi video có giọng AI">Tiếng clip</span><span class="seg2 ga-thay"><button type="button" data-thay="1" class="${gaThay() ? 'on' : ''}" title="Giọng AI thay hẳn tiếng gốc trong clip (tắt tiếng mọi cảnh)">Tắt, giọng thay hẳn</button><button type="button" data-thay="0" class="${gaThay() ? '' : 'on'}" title="Giữ tiếng gốc nhỏ làm nền, tự hạ khi giọng đọc">Giữ nhỏ làm nền</button></span></div>
    <div class="ga-hang"><span class="lbl">Tốc độ</span><span class="seg2 ga-toc">${GA.ds.toc.map(x => `<button type="button" data-toc="${esc(x.v)}" class="${x.v === GA.toc ? 'on' : ''}">${esc(x.ten)}</button>`).join('')}</span></div>
    ${GA.ds.vieneu ? '' : '<p class="note tv-canh">Máy chưa cài giọng VieNeu (chạy trên máy): hiện chỉ dùng được giọng Microsoft, cần mạng.</p>'}
    <div class="ga-hang"><button type="button" class="btn primary" data-ga="tao"${tt && tt.dang ? ' disabled' : ''}>${tt && tt.dang ? 'Đang tạo giọng… ' + Math.round(tt.giay_da || 0) + 's' : (tt && tt.kq ? 'Tạo lại' : 'Tạo giọng')}</button>
      ${tt && tt.dang ? '<span class="note">Lần đầu giọng VieNeu nạp mất khoảng nửa phút. Vẫn sửa video được trong lúc chờ.</span>' : ''}</div>
    ${tt && tt.loi ? `<p class="note err">${esc(tt.loi)}</p>` : ''}
    ${tt && tt.kq ? `<div class="ga-kq"><audio controls preload="auto" src="${esc(tt.kq.url)}"></audio>
      <p class="note">Giọng <b>${esc(tt.ten || '')}</b> dài ${gs(tt.kq.giay || 0)} · ${tt.kq.phu_de.length} câu phụ đề${T && tt.kq.giay > T + 0.3 ? ` · <b class="ga-warn">dài hơn video ${gs(tt.kq.giay - T)}: đoạn cuối sẽ bị cắt</b>` : ''}</p>
      <div class="ga-hang"><button type="button" class="btn primary" data-ga="ap" data-tip="Phụ đề đổi theo giọng, ${gaThay() ? 'tiếng gốc trong clip tắt hẳn' : 'tiếng trong clip nhỏ lại làm nền'}. Ctrl+Z để bỏ.">Áp vào video</button></div></div>` : ''}
  </div>`;
  const ta = $('.ga-loi', el);
  ta.oninput = () => { GA.loi = ta.value; const u = $('.ga-uoc', el); if (u) u.innerHTML = gaTomUoc(); };
  const sel = $('.ga-giong', el); if (sel) sel.onchange = e => { GA.chon = e.target.value; GA.phong = GA.kieu = null; };
  el.onclick = e => {
    const tb = e.target.closest('[data-toc]'); if (tb) { GA.toc = tb.dataset.toc; GA.loi = ta.value; return veGA(); }
    const th = e.target.closest('[data-thay]'); if (th) { GA.loi = ta.value; return gaDatThay(th.dataset.thay === '1'); }
    const b = e.target.closest('[data-ga]'); if (!b || b.disabled) return;
    GA.loi = ta.value;
    ({thu: gaThu, tao: gaTao, ap: gaAp, bo: gaBo})[b.dataset.ga](b);
  };
}
async function gaThu(b) {
  const cu = b.textContent; b.disabled = true; b.textContent = 'Đang tạo mẫu…';
  try { const r = await api('/api/giong-thu', {giong: GA.chon, toc_do: GA.toc, phong: GA.phong || undefined}); const a = new Audio(r.url); dung(); await a.play(); }
  catch (e) { toast(e.message, true); }
  finally { b.disabled = false; b.textContent = cu; }
}
async function gaTao() {
  if (!GA.loi.trim()) return toast('Gõ lời đọc trước: mỗi dòng 1 câu', true);
  try {
    const r = await api('/api/sua-tay/giong-tao', {v: S.v, loi: GA.loi, giong: GA.chon, toc_do: GA.toc, phong: GA.phong || undefined, kieu_trend: GA.kieu || undefined});
    GA.tt = {dang: true, giay_da: 0}; veGA(); clearTimeout(GA.hen);
    const v = S.v, theo = async () => {
      if (S.v !== v) return;
      try { GA.tt = await api('/api/sua-tay/giong-tao?ma=' + r.ma); } catch (e) { GA.tt = {dang: false, loi: e.message}; }
      veGA();
      if (GA.tt.dang) GA.hen = setTimeout(theo, 1000);
      else if (GA.tt.kq) toast('Đã tạo xong giọng ' + (GA.tt.ten || '') + ': nghe thử rồi bấm Áp vào video');
    };
    theo();
  } catch (e) { toast(e.message, true); }
}
function gaApAudio() {   // khung xem trước phát đúng file giọng đang dùng (giọng mới tạo chưa xuất cũng phát được)
  const a = $('#giong'), u = giongUrl();
  if (!u) { if (a) { a.pause(); a.remove(); } return; }
  if (a && a.dataset.p !== S.plan.giong.local) { a.src = u; a.dataset.p = S.plan.giong.local; }
}
function gaAp() {
  const tt = GA.tt; if (!tt || !tt.kq) return;
  const kq = tt.kq, thay = gaThay();   // 4/11: tạo lại giọng giữ đúng lựa chọn Tiếng clip đang hiện (trước: lấy GA.thay mặc định -> video đang "nhỏ làm nền" bị đổi sang tắt hẳn)
  doi(p => {
    p.giong = {local: kq.wav, file: kq.wav, ten: tt.ten, giong: tt.giong, toc_do: tt.toc_do, giay: kq.giay, loi: tt.loi_doc, thay_tieng: thay};
    if (tt.phong) p.giong.phong = tt.phong;   // r39: kiểu trend (chỉ THÊM khoá khi có)
    if (tt.kieu_trend) p.giong.kieu_trend = tt.kieu_trend;
    p.phu_de = kq.phu_de.map(x => Object.assign({_k: ma('p')}, JSON.parse(JSON.stringify(x))));
  });
  gaApAudio(); veGA();
  toast('Đã áp giọng ' + (tt.ten || 'AI') + ' (' + kq.phu_de.length + ' câu phụ đề). Ctrl+Z để bỏ');
}
function gaDatThay(thay) {   // 4/11 anh: "giọng đọc ai tự thay thế tiếng trong clip được không"
  GA.thay = thay;
  if (S.plan.giong && !!S.plan.giong.thay_tieng !== thay) {
    doi(p => { p.giong.thay_tieng = thay; });
    toast(thay ? 'Giọng AI thay hẳn tiếng trong clip: tắt tiếng gốc mọi cảnh (Ctrl+Z để bỏ)' : 'Giữ tiếng gốc trong clip nhỏ làm nền dưới giọng AI (Ctrl+Z để bỏ)');
  }
  veGA();
}
function gaBo() {
  if (!S.plan.giong) return;
  doi(p => { p.giong = null; });
  gaApAudio(); veGA();
  toast('Đã bỏ giọng AI: tiếng trong clip về như cũ. Phụ đề giữ nguyên (Ctrl+Z để lấy lại giọng)');
}
function moGiongAI() {
  const {m} = modal('<h3>Giọng đọc AI</h3><div id="gaM"></div><div class="acts"><button class="btn" data-dong>Đóng</button></div>');
  m.classList.add('ga-hop'); veGiongAI($('#gaM', m));
}
