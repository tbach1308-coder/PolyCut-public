/* ============================== TIỆN ÍCH / SCRIPT (3/11) ==============================
   Tiện ích = thư mục tien-ich/<id>/ (tien-ich.json + script.js) — máy chủ: tien_ich.py, hướng dẫn lệnh: prompts/script-api.md.
   Script chạy trong Web Worker trên BẢN SAO kế hoạch (tắt mạng, quá 4 giây thì dừng) với biến `ed`; xong thì kiemPlan()
   gọt lại (không cho đổi nguồn clip, khung, giọng…), tomTat() liệt kê thay đổi, áp thành 1 bước Ctrl+Z.
   Nhờ Claude dùng chung: thao tác {"op":"tien_ich"} / {"op":"script"} chạy qua chayOps(). */
function wkTienIch() {   // thân Worker: KHÔNG dùng biến ngoài (chuyển thành chuỗi)
  const CAM = ['fetch', 'XMLHttpRequest', 'WebSocket', 'EventSource', 'importScripts', 'indexedDB', 'caches', 'BroadcastChannel', 'Worker', 'SharedWorker'];
  self.onmessage = e => {
    const d = e.data, P = d.plan, bao = [];
    const r3 = x => Math.round(x * 1000) / 1000;
    const so = (x, ten) => { const v = +x; if (x === null || x === '' || !isFinite(v)) throw new Error(ten + ' phải là số'); return v; };
    let dem = 0;
    const ma = p => p + (Date.now() % 1e6).toString(36) + (dem++).toString(36) + Math.random().toString(36).slice(2, 6);
    const ten = f => String(f || '').replace(/\\/g, '/').split('/').pop();
    const dl = f => d.giay[f] || d.giay[((P.nguon || {})[f] || {}).local] || 1e9;
    P.chu = P.chu || {}; P.phu_de = P.phu_de || []; P.kieu = P.kieu || {};
    const C = (c, ham) => {
      const x = c && typeof c === 'object' ? P.canh.find(y => y === c || (c._id && y._id === c._id)) : typeof c === 'string' ? P.canh.find(y => y._id === c) : null;
      if (!x) throw new Error(ham + ': không thấy cảnh (truyền 1 cảnh lấy từ ed.canh)');
      return x;
    };
    const dai = c => r3(c.den - c.tu);
    const batDau = c => { let t = 0; for (const y of P.canh) { if (y === c) return r3(t); t += y.den - y.tu; } return null; };
    const tong = () => r3(P.canh.reduce((s, y) => s + y.den - y.tu, 0));
    const lech = typeof d.T === 'number' && d.T > 0 ? d.T - tong() : 0;   // chuyển cảnh chồng + mở đầu… lúc bắt đầu chạy (3/11)
    const thuc = () => r3(Math.max(0, tong() + lech));
    const kiemDai = (tu, den) => { if (den - tu < 0.3 - 1e-6) throw new Error('Cảnh phải dài ít nhất 0,3 giây'); };
    const vt = (o, cau, macDai) => {
      o = o || {};
      const len = o.dai != null ? so(o.dai, 'dai') : macDai;
      if (!(len >= 0.3)) throw new Error('dai phải ≥ 0,3 giây');
      if (o.canh) {
        const c = C(o.canh, 'vị trí canh'), sau = Math.max(0, o.sau != null ? so(o.sau, 'sau') : 0);
        const s0 = r3(c.tu + sau), t0 = r3(batDau(c) + sau);
        return {t0, t1: r3(t0 + len), _neo: {id: c._id, file: c.file, s0, s1: r3(s0 + len), cau: !!cau}};
      }
      const t0 = r3(Math.max(0, o.luc != null ? so(o.luc, 'luc') : d.vach));
      return {t0, t1: r3(t0 + len)};
    };
    const timClip = clip => {
      const f = Object.keys(P.nguon || {}).find(k => k === clip || ten(k) === clip || ten(k).replace(/\.[^.]+$/, '') === clip);
      if (!f) throw new Error('Không có clip "' + clip + '" (xem ed.clipCoSan)');
      return f;
    };
    const ed = {
      get canh() { return P.canh; },
      canhSo: n => P.canh[so(n, 'n') - 1] || null,
      dai: c => dai(C(c, 'dai')),
      clip: c => ten(C(c, 'clip').file),
      clipDai: c => { const x = dl(C(c, 'clipDai').file); return x >= 1e9 ? null : x; },
      batDau: c => batDau(C(c, 'batDau')),
      tong, thuc,
      vach: d.vach,
      get canhVach() { return P.canh.find(y => y._id === d.canhVach) || null; },
      get chon() { return P.canh.find(y => y._id === d.chon) || null; },
      vao: d.vao || {},
      clipCoSan: Object.keys(P.nguon || {}).map(ten),
      get nhanDs() { return (P.chu.nhan_chu = P.chu.nhan_chu || []); },
      get phuDe() { return P.phu_de; },
      kieuDs: d.kieuDs || {},
      plan: P,
      chia(c, sau) {
        c = C(c, 'chia'); sau = so(sau, 'sau'); const t = r3(c.tu + sau);
        if (sau < 0.3 - 1e-6 || c.den - t < 0.3 - 1e-6) throw new Error('chia: mỗi phần phải ≥ 0,3 giây (cảnh dài ' + dai(c) + 's, chia tại ' + r3(sau) + 's)');
        const m = JSON.parse(JSON.stringify(c)); m._id = ma('c'); m._tach = true; delete m._phan; delete m.chuyen; m.tu = t; c.den = t;   // nửa sau nối liền: không chuyển cảnh riêng
        P.canh.splice(P.canh.indexOf(c) + 1, 0, m); return m;
      },
      catDau(c, g) { c = C(c, 'catDau'); g = so(g, 'giay'); if (g <= 0) return c; kiemDai(c.tu + g, c.den); c.tu = r3(c.tu + g); return c; },
      catCuoi(c, g) { c = C(c, 'catCuoi'); g = so(g, 'giay'); if (g <= 0) return c; kiemDai(c.tu, c.den - g); c.den = r3(c.den - g); return c; },
      doan(c, tu, den) { c = C(c, 'doan'); tu = Math.max(0, so(tu, 'tu')); den = Math.min(dl(c.file), so(den, 'den')); kiemDai(tu, den); c.tu = r3(tu); c.den = r3(den); return c; },
      xoa(c) { c = C(c, 'xoa'); P.canh.splice(P.canh.indexOf(c), 1); },   // 4/11 18:14: xoá được cả cảnh cuối (video trống)
      nhanDoi(c) { c = C(c, 'nhanDoi'); const m = JSON.parse(JSON.stringify(c)); m._id = ma('c'); delete m._phan; P.canh.splice(P.canh.indexOf(c) + 1, 0, m); return m; },
      doiCho(c, viTri) { c = C(c, 'doiCho'); const i = Math.max(0, Math.min(P.canh.length - 1, Math.round(so(viTri, 'viTri')) - 1)); P.canh.splice(P.canh.indexOf(c), 1); P.canh.splice(i, 0, c); return c; },
      themCanh(clip, o) {
        o = o || {}; const f = timClip(clip), L = dl(f);
        const tu = Math.max(0, o.tu != null ? so(o.tu, 'tu') : 0), den = Math.min(L, o.den != null ? so(o.den, 'den') : Math.min(L, tu + 3)); kiemDai(tu, den);
        const m = {_id: ma('c'), file: f, tu: r3(tu), den: r3(den)}; let i = P.canh.length;
        if (o.sau === 'dau') i = 0; else if (o.sau) i = P.canh.indexOf(C(o.sau, 'themCanh sau')) + 1;
        P.canh.splice(i, 0, m); return m;
      },
      thayClip(c, clip, tu) {
        c = C(c, 'thayClip'); const f = timClip(clip), L = dl(f), len = dai(c);
        const a = Math.max(0, tu != null ? so(tu, 'tu') : 0), b = Math.min(L, a + len); kiemDai(a, b);
        c.file = f; c.tu = r3(a); c.den = r3(b); delete c._phan; delete c._tach; delete c.noi_lien; return c;
      },
      hook(d1, d2) { const h = [d1, d2].map(x => String(x ?? '').trim()); while (h.length && !h[h.length - 1]) h.pop(); P.chu.hook = h; },
      nhan(chu, o) { const t = String(chu ?? '').trim(); if (!t) throw new Error('nhan: chữ trống'); const n = {_k: ma('n'), chu: t, ...vt(o, false, 2.5)}; (P.chu.nhan_chu = P.chu.nhan_chu || []).push(n); return n; },
      xoaNhan(n) { P.chu.nhan_chu = (P.chu.nhan_chu || []).filter(x => x !== n && !(n && n._k && x._k === n._k)); },
      theGia(gia, phu, o) {
        const g = String(gia ?? '').trim(); if (!g) throw new Error('theGia: thiếu giá'); const cu = P.chu.the_gia;
        P.chu.the_gia = {_k: (cu && cu._k) || ma('g'), gia: g, phu: String(phu ?? '').trim(), ...vt(o, false, 3)}; return P.chu.the_gia;
      },
      boTheGia() { P.chu.the_gia = null; },
      themPhuDe(chu, o) { const t = String(chu ?? '').trim(); if (!t) throw new Error('themPhuDe: câu trống'); const n = {_k: ma('p'), chu: t, ...vt(o, true, 2.2)}; P.phu_de.push(n); return n; },
      xoaPhuDe(x) { P.phu_de = P.phu_de.filter(y => y !== x && !(x && x._k && y._k === x._k)); },
      ket(d1, d2) {
        if (d1 === 'mac_dinh') { delete P.chu.ket; if (P.kieu.ket === 'khong') P.kieu.ket = 'the_comment'; }
        else if (d1 === null || d1 === false) P.chu.ket = null;
        else { P.chu.ket = [String(d1 ?? '').trim(), String(d2 ?? '').trim()]; if (P.kieu.ket === 'khong') P.kieu.ket = 'the_comment'; }
      },
      ketGiay(s) { P.ket_giay = Math.max(1.5, Math.min(6, so(s, 'giay'))); },
      tieuDe(t) { t = String(t ?? '').trim(); if (t) P.chu.tieu_de = t; else delete P.chu.tieu_de; },
      brand(b) { P.chu.brand = !!b; },
      kieu(truc, v) {
        const ds = (d.kieuDs || {})[truc]; if (!ds) throw new Error('kieu: không có trục "' + truc + '"');
        if (!ds.includes(v)) throw new Error('kieu: ' + truc + ' không có "' + v + '" (có: ' + ds.join(', ') + ')');
        const cu = P.kieu[truc]; P.kieu[truc] = v; ghimKieu(P, truc);   // tự chọn -> ghim (4/11: video tạo tay)
        if (truc === 'ket') { if (v === 'khong') P.chu.ket = null; else if (P.chu.ket === null) delete P.chu.ket; }
        return cu;
      },
      bao(m) { if (bao.length < 30) bao.push(String(m).slice(0, 300)); }
    };
    for (const k of CAM) { try { self[k] = undefined; } catch (x) {} }
    try {
      const f = new Function('ed', '"use strict";\n' + d.ma + '\n;');
      const kq = f(ed);
      if (kq && typeof kq.then === 'function') throw new Error('Script không được dùng async / await');
      postMessage({ok: true, plan: P, bao});
    } catch (x) {
      const m = /<anonymous>:(\d+):\d+/.exec(String((x && x.stack) || ''));
      postMessage({ok: false, loi: String((x && x.message) || x), dong: m ? Math.max(1, +m[1] - 3) : null, bao});
    }
  };
}
const TI_WK = URL.createObjectURL(new Blob(['(' + wkTienIch.toString() + ')()'], {type: 'text/javascript'}));
const kieuChoPhep = () => Object.fromEntries(((S.info || {}).kieu_ds || []).map(m => [m.muc, m.ds.map(x => x.v)]));
function chayScript(ma_, plan, vao) {   // -> {ok, plan, bao} | {ok:false, loi, dong}
  return new Promise(res => {
    let w;
    try { w = new Worker(TI_WK); } catch (e) { return res({ok: false, loi: 'Máy không chạy được script: ' + e.message, bao: []}); }
    const het = setTimeout(() => { w.terminate(); res({ok: false, loi: 'Script chạy quá 4 giây nên app đã dừng (có vòng lặp không dừng?)', bao: []}); }, 4000);
    w.onmessage = e => { clearTimeout(het); w.terminate(); res(e.data); };
    w.onerror = e => { e.preventDefault(); clearTimeout(het); w.terminate(); res({ok: false, loi: 'Script lỗi: ' + (e.message || ''), bao: []}); };
    const x0 = canhLuc(S.t);
    w.postMessage({ma: String(ma_ || ''), plan: JSON.parse(JSON.stringify(plan)), vao: vao || {}, vach: r3(S.t), canhVach: x0 ? x0.c._id : null,
      chon: S.sel.canh, giay: S.giay, kieuDs: kieuChoPhep(), T: S.view && S.viewIds === S.plan.canh.map(c => c._id).join() ? S.view.T : null});
  });
}
function kiemPlan(cu, moi) {   // gọt kế hoạch script trả về: chỉ cho đổi cảnh, chữ, phụ đề, kiểu, thẻ kết. Sai -> Error
  if (!moi || !Array.isArray(moi.canh)) throw new Error('Script trả kế hoạch sai dạng (thiếu danh sách cảnh)');   // 0 cảnh: được (video trống)
  const p = JSON.parse(JSON.stringify(cu)), cb = [], ids = new Set();
  const str = (x, n) => String(x ?? '').replace(/[\u0000-\u0008\u000b-\u001f]/g, '').slice(0, n);
  p.canh = moi.canh.map((c, i) => {
    if (!c || typeof c !== 'object') throw new Error('Cảnh ' + (i + 1) + ' sai dạng');
    if (!(c.file in (cu.nguon || {}))) throw new Error('Cảnh ' + (i + 1) + ': clip không có trong video này');
    let tu = +c.tu, den = +c.den;
    if (!isFinite(tu) || !isFinite(den)) throw new Error('Cảnh ' + (i + 1) + ': giờ không phải số');
    const L = S.giay[c.file] || S.giay[src(c.file)] || 1e9; tu = clamp(tu, 0, L); den = clamp(den, 0, L);
    if (den - tu < 0.29) throw new Error('Cảnh ' + (i + 1) + ' ngắn hơn 0,3 giây');
    const x = JSON.parse(JSON.stringify(c)); x.tu = r3(tu); x.den = r3(den); if (x.mo_ta != null) x.mo_ta = str(x.mo_ta, 200);
    if (!x._id || ids.has(x._id)) x._id = ma('c'); ids.add(x._id);
    return x;
  });
  const ch = moi.chu && typeof moi.chu === 'object' ? moi.chu : {};
  const it = (x, k, n) => {
    if (!x || typeof x !== 'object') return null;
    const y = JSON.parse(JSON.stringify(x)); y.chu = str(y.chu, n).trim(); if (!y.chu) return null; if (!y._k) y._k = ma(k);
    if (!y._neo && !(isFinite(+y.t0) && isFinite(+y.t1) && +y.t1 - +y.t0 >= 0.2)) return null;
    return y;
  };
  p.chu = JSON.parse(JSON.stringify(cu.chu || {}));
  p.chu.hook = Array.isArray(ch.hook) ? ch.hook.slice(0, 2).map(x => str(x, 60)) : [];
  p.chu.nhan_chu = (Array.isArray(ch.nhan_chu) ? ch.nhan_chu : []).map(x => it(x, 'n', 60)).filter(Boolean);
  if (ch.the_gia && typeof ch.the_gia === 'object' && str(ch.the_gia.gia, 30).trim()) {
    const g = JSON.parse(JSON.stringify(ch.the_gia)); g.gia = str(g.gia, 30).trim(); g.phu = str(g.phu, 60).trim(); if (!g._k) g._k = ma('g'); p.chu.the_gia = g;
  } else p.chu.the_gia = null;
  if (!('ket' in ch)) delete p.chu.ket; else if (ch.ket === null) p.chu.ket = null; else if (Array.isArray(ch.ket)) p.chu.ket = ch.ket.slice(0, 2).map(x => str(x, 60)); else delete p.chu.ket;
  if (str(ch.tieu_de, 30).trim()) p.chu.tieu_de = str(ch.tieu_de, 30).trim(); else delete p.chu.tieu_de;
  p.chu.brand = ch.brand !== false;
  p.phu_de = (Array.isArray(moi.phu_de) ? moi.phu_de : []).map(x => it(x, 'p', 200)).filter(Boolean);
  const ok = kieuChoPhep();
  p.kieu = JSON.parse(JSON.stringify(cu.kieu || {}));
  for (const [m, v] of Object.entries(moi.kieu || {})) {
    if (v === (cu.kieu || {})[m]) continue;
    if (ok[m] && ok[m].includes(v)) { p.kieu[m] = v; ghimKieu(p, m); } else cb.push('Bỏ đổi kiểu ' + m + ' = ' + v + ' (bản ffmpeg không có)');
  }
  if (moi.ket_giay != null && isFinite(+moi.ket_giay)) p.ket_giay = clamp(+moi.ket_giay, 1.5, 6);
  return {plan: p, cb};
}
function tomTat(a, b) {   // các dòng (HTML) mô tả khác nhau giữa 2 kế hoạch
  const out = [], q = s => `<span class="q">“${esc(s)}”</span>`, dai = p => p.canh.reduce((s, c) => s + c.den - c.tu, 0);
  const ia = Object.fromEntries(a.canh.map((c, i) => [c._id, i + 1])), ib = new Set(b.canh.map(c => c._id));
  const xoa = a.canh.filter(c => !ib.has(c._id)).map(c => ia[c._id]);
  const them = b.canh.filter(c => !(c._id in ia)).length;
  const sua = b.canh.filter(c => c._id in ia).filter(c => { const o = a.canh.find(x => x._id === c._id); return o.file !== c.file || Math.abs(o.tu - c.tu) > 0.004 || Math.abs(o.den - c.den) > 0.004; }).map(c => ia[c._id]);
  const chungB = b.canh.filter(c => c._id in ia).map(c => c._id).join(), chungA = a.canh.filter(c => ib.has(c._id)).map(c => c._id).join();
  if (xoa.length) out.push(`<b>Xoá cảnh</b> ${xoa.join(', ')}`);
  if (them) out.push(`<b>Thêm ${them} cảnh</b> (chia / nhân đôi / thêm mới)`);
  if (sua.length) out.push(`<b>Đổi đoạn cảnh</b> ${sua.join(', ')}`);
  if (chungA !== chungB) out.push('<b>Đổi thứ tự cảnh</b>');
  const da = dai(a), db = dai(b); if (Math.abs(da - db) > 0.05) out.push(`Tổng cảnh ${gs(da)} → ${gs(db)}`);
  const ca = a.chu || {}, cb = b.chu || {};
  if (JSON.stringify(ca.hook || []) !== JSON.stringify(cb.hook || [])) out.push((cb.hook || []).filter(Boolean).length ? '<b>Hook</b>: ' + cb.hook.filter(Boolean).map(q).join(' / ') : '<b>Bỏ hook</b>');
  const ds = (x, y, ten) => {
    const ma_ = Object.fromEntries((x || []).map(n => [n._k, n])), mb = Object.fromEntries((y || []).map(n => [n._k, n]));
    const moi = (y || []).filter(n => !ma_[n._k]), mat = (x || []).filter(n => !mb[n._k]);
    const doi = (y || []).filter(n => ma_[n._k] && (ma_[n._k].chu !== n.chu || JSON.stringify(ma_[n._k]._neo) !== JSON.stringify(n._neo) || ma_[n._k].t0 !== n.t0));
    const lk = ds => ds.slice(0, 3).map(n => q(n.chu)).join(', ') + (ds.length > 3 ? '…' : '');
    if (moi.length) out.push(`<b>Thêm ${moi.length} ${ten}</b> ${lk(moi)}`);
    if (mat.length) out.push(`<b>Xoá ${mat.length} ${ten}</b> ${lk(mat)}`);
    if (doi.length) out.push(`<b>Sửa ${doi.length} ${ten}</b> ${lk(doi)}`);
  };
  ds(ca.nhan_chu, cb.nhan_chu, 'nhãn'); ds(a.phu_de, b.phu_de, 'câu phụ đề');
  if (JSON.stringify(ca.the_gia || null) !== JSON.stringify(cb.the_gia || null)) out.push(cb.the_gia ? `<b>${ca.the_gia ? 'Sửa' : 'Thêm'} thẻ giá</b> ${q(cb.the_gia.gia)}${cb.the_gia.phu ? ' · ' + q(cb.the_gia.phu) : ''}` : '<b>Bỏ thẻ giá</b>');
  if (JSON.stringify(ca.ket) !== JSON.stringify(cb.ket)) out.push(cb.ket === null ? '<b>Bỏ thẻ kết</b>' : cb.ket === undefined ? '<b>Thẻ kết</b>: câu mặc định' : '<b>Thẻ kết</b>: ' + cb.ket.filter(Boolean).map(q).join(' / '));
  if ((a.ket_giay || 3.6) !== (b.ket_giay || 3.6)) out.push(`<b>Thẻ kết</b> hiện ${gs(b.ket_giay)}`);
  if ((ca.tieu_de || '') !== (cb.tieu_de || '')) out.push(cb.tieu_de ? '<b>Tiêu đề ghim</b> ' + q(cb.tieu_de) : '<b>Bỏ tiêu đề ghim</b>');
  if ((ca.brand !== false) !== (cb.brand !== false)) out.push('<b>Chữ POLY STORE</b>: ' + (cb.brand !== false ? 'hiện' : 'ẩn'));
  for (const m of (S.info.kieu_ds || [])) {
    const x = (a.kieu || {})[m.muc], y = (b.kieu || {})[m.muc];
    if (x !== y) { const t = v => (m.ds.find(z => z.v === v) || {}).ten || v || '—'; out.push(`<b>${esc(m.ten)}</b>: ${esc(t(x))} → ${esc(t(y))}`); }
  }
  return out;
}
const boThe = s => String(s).replace(/<[^>]+>/g, '');

/* ---------- danh sách tiện ích ---------- */
S.ti = null;
async function taiTi(lai) {
  if (S.ti && !lai) return S.ti;
  try { S.ti = await api('/api/tien-ich'); } catch (e) { S.ti = S.ti || {ds: [], huong_dan: '', thu_muc: '', loi: e.message}; }
  return S.ti;
}
const tiTim = id => ((S.ti || {}).ds || []).find(x => x.id === id);
function vaoMacDinh(ti, vao) {   // ghép giá trị ô hỏi: mặc định <- vao; ô số -> số
  const o = {};
  for (const h of ti.hoi || []) {
    let v = vao && h.ten in vao ? vao[h.ten] : h.mac_dinh;
    if (h.kieu === 'so') { v = +String(v ?? '').replace(',', '.'); if (!isFinite(v)) v = +String(h.mac_dinh).replace(',', '.') || 0; }
    o[h.ten] = v;
  }
  for (const [k, v] of Object.entries(vao || {})) if (!(k in o)) o[k] = v;
  return o;
}
function hoiVao(ti) {   // ô hỏi trước khi chạy -> Promise(vao | null)
  if (!(ti.hoi || []).length) return Promise.resolve({});
  return new Promise(res => {
    let xong = false;
    const {m, dong} = modal(`<h3>${esc(ti.ten)}</h3>${ti.mo_ta ? `<p class="note">${esc(ti.mo_ta)}</p>` : ''}
      <form id="tiF" class="tiform">${ti.hoi.map((h, i) => `<label>${esc(h.nhan)}<input class="inp" name="${esc(h.ten)}" value="${esc(h.mac_dinh)}" ${h.kieu === 'so' ? 'inputmode="decimal"' : ''} ${i === 0 ? 'autofocus' : ''}></label>`).join('')}
      <div class="acts"><button type="button" class="btn" data-dong>Huỷ</button><button class="btn primary">▶ Chạy</button></div></form>`);
    const f = $('#tiF', m);
    f.onsubmit = e => { e.preventDefault(); xong = true; const o = {}; for (const h of ti.hoi) o[h.ten] = f.elements[h.ten].value; dong(); res(vaoMacDinh(ti, o)); };
    const ob = new MutationObserver(() => { if (!document.body.contains(m)) { ob.disconnect(); if (!xong) res(null); } });
    ob.observe(document.body, {childList: true});
    const x0 = f.querySelector('input'); if (x0) { x0.focus(); x0.select(); }
  });
}
async function chayTi(ti, vao) {   // chạy 1 tiện ích trên video đang mở, áp ngay (Ctrl+Z được) -> {tt, bao, cb} | {loi}
  if (!S.plan) return {loi: 'Chưa mở video'};
  dung();
  try { clearTimeout(S.nhapHen); await luuNhap(); } catch (e) {}   // script lỗi làm treo / sập trang thì phần sửa vẫn còn (soi lần 2 A7)
  const r = await chayScript(ti.ma, S.plan, vao);
  if (!r.ok) return {loi: r.loi + (r.dong ? ' (dòng ' + r.dong + ')' : ''), bao: r.bao || []};
  let k; try { k = kiemPlan(S.plan, r.plan); } catch (e) { return {loi: e.message, bao: r.bao}; }
  const tt = tomTat(S.plan, k.plan);
  if (tt.length) doi(() => { S.plan = k.plan; giuChon(); });
  return {tt, bao: r.bao || [], cb: k.cb};
}
async function chayTuMenu(id) {
  dongTiMenu();
  const ti = tiTim(id); if (!ti) return;
  const vao = await hoiVao(ti); if (vao === null) return;
  const kq = await chayTi(ti, vao);
  if (kq.loi) return baoKq(ti.ten, kq);
  toast(ti.ten + ': ' + ([...kq.bao, ...kq.tt.map(boThe)].slice(0, 3).join(' · ') || 'chạy xong') + (kq.tt.length ? ' (Ctrl+Z để bỏ)' : ' — không đổi gì'));
}
function baoKq(ten, kq) {
  modal(`<h3>${esc(ten)}</h3>${kq.loi ? `<p class="note err">Không chạy được: ${esc(kq.loi)}</p><p class="note">Video chưa bị đổi gì.</p>` : ''}
    ${(kq.bao || []).length ? `<ul class="tt">${kq.bao.map(x => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}<div class="acts"><button class="btn" data-dong>Đóng</button></div>`);
}

/* ---------- menu ⚡ Tiện ích ---------- */
function dongTiMenu() { const x = $('#tiMenu'); if (x) x.remove(); }
async function moTiMenu() {
  if ($('#tiMenu')) return dongTiMenu();
  const b = $('#bTi'), r = b.getBoundingClientRect();
  const el = document.createElement('div'); el.id = 'tiMenu'; el.className = 'timenu'; el.innerHTML = '<p class="note" style="padding:8px">Đang tải…</p>';
  el.style.top = (r.bottom + 6) + 'px'; el.style.right = Math.max(8, innerWidth - r.right) + 'px';
  document.body.append(el);
  const T = await taiTi(true);
  if (!$('#tiMenu')) return;
  const bat = T.ds.filter(x => x.bat && !x.loi);
  el.innerHTML = (bat.length ? bat.map(x => `<button type="button" class="ti-it" data-ti="${esc(x.id)}"><b>${esc(x.ten)}${(x.hoi || []).length ? ' …' : ''}</b>${x.mo_ta ? `<small>${esc(x.mo_ta)}</small>` : ''}</button>`).join('')
    : '<p class="note" style="padding:8px 10px">Chưa có tiện ích nào đang bật.</p>')
    + `<button type="button" class="ti-it ti-ql" data-ti-ql><b>Quản lý tiện ích…</b><small>Bật / tắt, sửa, viết script mới</small></button>`;
}
$('#bTi').onclick = e => { e.stopPropagation(); moTiMenu(); };
document.addEventListener('click', e => {
  const m = $('#tiMenu'); if (!m) return;
  const it = e.target.closest('#tiMenu [data-ti]'); if (it) return chayTuMenu(it.dataset.ti);
  if (e.target.closest('#tiMenu [data-ti-ql]')) { dongTiMenu(); return quanLyTi(); }
  if (!m.contains(e.target)) dongTiMenu();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') dongTiMenu(); });

/* ---------- quản lý + sửa script ---------- */
const NGUON_TEN = {goc: 'Có sẵn', tu_tao: 'Tự tạo', claude: 'Claude viết'};
async function quanLyTi() {
  const T = await taiTi(true);
  const {m, dong} = modal(`<h3>Tiện ích</h3><p class="note">Mỗi tiện ích là 1 thư mục trong <code>${esc(T.thu_muc || 'tien-ich')}</code>. Script chạy trên video đang mở, chạy xong vẫn Ctrl+Z được.</p>
    <div class="tids" id="tids"></div><div class="acts"><button class="btn" data-x="moi">+ Script mới</button><button class="btn" data-dong>Đóng</button></div>`);
  m.classList.add('rong');
  const ve = () => { $('#tids', m).innerHTML = S.ti.ds.length ? S.ti.ds.map(x => `<div class="tid${x.bat ? '' : ' tat'}" data-id="${esc(x.id)}">
      <label class="sw" title="${x.bat ? 'Đang bật' : 'Đang tắt'}"><input type="checkbox" data-x="bat" ${x.bat ? 'checked' : ''} ${x.loi ? 'disabled' : ''}></label>
      <div><b>${esc(x.ten)}</b> <span class="tag2">${esc(NGUON_TEN[x.nguon] || 'Tự tạo')}</span>${x.thang ? ` <span class="tag2">${esc(x.thang)}</span>` : ''}
        <small>${x.loi ? `<span class="err">Lỗi: ${esc(x.loi)}</span>` : esc(x.mo_ta || '')}</small></div>
      <div class="row"><button class="btn small" data-x="chay" ${x.loi ? 'disabled' : ''}>▶ Chạy</button><button class="btn small" data-x="sua">Sửa</button><button class="btn small danger" data-x="xoa">Xoá</button></div></div>`).join('')
    : '<p class="note">Chưa có tiện ích nào.</p>'; };
  ve();
  m.addEventListener('click', async e => {
    const b = e.target.closest('[data-x]'); if (!b) return;
    const x = b.dataset.x, id = (b.closest('[data-id]') || {}).dataset && b.closest('[data-id]').dataset.id, ti = id && tiTim(id);
    if (x === 'moi') { dong(); return suaTi(null); }
    if (x === 'sua' && ti) { dong(); return suaTi(ti); }
    if (x === 'chay' && ti) { dong(); return chayTuMenu(id); }
    if (x === 'xoa' && ti) { if (!confirm('Xoá tiện ích "' + ti.ten + '"? (chuyển vào thư mục .thung-rac, lấy lại được)')) return;
      try { await api('/api/tien-ich/xoa', {id}); await taiTi(true); ve(); toast('Đã xoá ' + ti.ten); } catch (er) { toast(er.message, true); } }
  });
  m.addEventListener('change', async e => {
    const c = e.target.closest('input[data-x="bat"]'); if (!c) return; const id = c.closest('[data-id]').dataset.id;
    try { await api('/api/tien-ich/bat', {id, bat: c.checked}); await taiTi(true); ve(); } catch (er) { toast(er.message, true); c.checked = !c.checked; }
  });
}
const hoiThanhChu = hoi => (hoi || []).map(h => [h.ten, h.nhan, h.mac_dinh].join(' | ') + (h.kieu === 'so' ? ' | so' : '')).join('\n');
function chuThanhHoi(s) {
  return String(s || '').split('\n').map(x => x.trim()).filter(Boolean).map(x => {
    const p = x.split('|').map(y => y.trim());
    return {ten: p[0], nhan: p[1] || p[0], mac_dinh: p[2] || '', kieu: (p[3] || '').toLowerCase() === 'so' ? 'so' : 'chu'};
  });
}
async function suaTi(ti, moi) {   // moi: {ten, mo_ta, hoi, ma, nguon} (script Claude viết, chưa lưu)
  const T = await taiTi();
  const x = ti || moi || {ten: '', mo_ta: '', hoi: [], ma: '// Viết script ở đây. Bảng bên phải có các lệnh dùng được.\nfor (const c of ed.canh) {\n  // vd: if (ed.dai(c) > 4) ed.chia(c, ed.dai(c) / 2);\n}\n', nguon: 'tu_tao'};
  const {m, dong} = modal(`<h3>${ti ? 'Sửa tiện ích' : 'Tiện ích mới'}</h3>
    <div class="tied"><div class="tied-l">
      <label>Tên<input class="inp" id="tiTen" value="${esc(x.ten || '')}" maxlength="60" placeholder="vd Chia cảnh dài"></label>
      <label>Mô tả (ghi rõ làm gì, Claude đọc để biết khi nào dùng)<textarea class="inp" id="tiMoTa" rows="2" maxlength="400">${esc(x.mo_ta || '')}</textarea></label>
      <label>Ô hỏi trước khi chạy <small>mỗi dòng: tên | câu hỏi | mặc định | so (nếu là số). Trong script đọc bằng ed.vao.tên</small><textarea class="inp mono" id="tiHoi" rows="2" spellcheck="false" placeholder="gia | Giá (vd 13tr9) |">${esc(hoiThanhChu(x.hoi))}</textarea></label>
      <label>Script (JavaScript)<textarea class="inp mono" id="tiMa" rows="15" spellcheck="false">${esc(x.ma || '')}</textarea></label>
      <div id="tiKq" class="tikq"></div>
    </div><div class="tied-r"><div class="lbl">Lệnh dùng được</div><pre>${esc(T.huong_dan || '(chưa có hướng dẫn)')}</pre></div></div>
    <div class="acts"><span class="note grow">Chạy thử: áp lên video đang mở, Ctrl+Z để bỏ.</span><button class="btn" id="tiThu">▶ Chạy thử</button><button class="btn" data-dong>Đóng</button><button class="btn primary" id="tiLuu">Lưu tiện ích</button></div>`);
  m.classList.add('rong');
  const ma_ = $('#tiMa', m);
  ma_.addEventListener('keydown', e => { if (e.key === 'Tab' && !e.shiftKey) { e.preventDefault(); const a = ma_.selectionStart, b = ma_.selectionEnd; ma_.setRangeText('  ', a, b, 'end'); } });
  const lay = () => ({id: ti ? ti.id : undefined, ten: $('#tiTen', m).value.trim(), mo_ta: $('#tiMoTa', m).value.trim(), hoi: chuThanhHoi($('#tiHoi', m).value),
    ma: ma_.value, nguon: ti ? ti.nguon : (x.nguon || 'tu_tao')});
  $('#tiThu', m).onclick = async e => {
    const b = e.currentTarget; if (b.disabled) return; b.disabled = true;
    try {
    const t = lay(); const vao = await hoiVao({...t, ten: t.ten || 'Chạy thử'}); if (vao === null) return;
    const kq = await chayTi(t, vao);
    $('#tiKq', m).innerHTML = kq.loi ? `<p class="note err">Lỗi: ${esc(kq.loi)}</p>`
      : `<p class="note ok">Đã chạy${kq.tt.length ? ' và áp lên video (Ctrl+Z để bỏ)' : ', không đổi gì'}:</p><ul class="tt">${[...kq.bao.map(esc), ...kq.tt, ...(kq.cb || []).map(esc)].map(y => `<li>${y}</li>`).join('')}</ul>`;
    } finally { b.disabled = false; }
  };
  $('#tiLuu', m).onclick = async () => {
    const t = lay(); if (!t.ten) { toast('Đặt tên cho tiện ích', true); return $('#tiTen', m).focus(); }
    try { const r = await api('/api/tien-ich/luu', t); await taiTi(true); dong(); toast('Đã lưu tiện ích ' + t.ten + ' — chạy ở nút ⚡ Tiện ích'); if (moi && moi.khiLuu) moi.khiLuu(r.id); }
    catch (er) { toast(er.message, true); }
  };
  setTimeout(() => (x.ten ? ma_ : $('#tiTen', m)).focus(), 30);
}

/* ---------- dùng trong Nhờ Claude: thao tác thường + tiện ích + script, theo thứ tự ---------- */
async function chayOps(p, ops) {   // áp lên p (sửa tại chỗ), trả [{txt, loi, ly_do}]
  const ctx = {alias: {}, goc: Object.fromEntries(p.canh.map((c, i) => [c._id, i + 1]))}, out = [];
  if (ops.some(o => o && (o.op === 'tien_ich' || o.op === 'script'))) await taiTi();
  for (const o of ops) {
    if (!o || (o.op !== 'tien_ich' && o.op !== 'script')) { out.push(...apOps(p, [o], ctx)); continue; }
    const ti = o.op === 'tien_ich' ? tiTim(o.id) : null;
    const ten = o.op === 'script' ? 'Script' : 'Tiện ích ' + (ti ? '“' + esc(ti.ten) + '”' : esc(o.id || '?'));
    let txt = `<b>${ten}</b>${o.mo_ta ? ': ' + esc(o.mo_ta) : ''}`, loi = '';
    try {
      if (o.op === 'tien_ich' && (!ti || !ti.bat || ti.loi)) throw 'tiện ích không có hoặc đang tắt';
      const r = await chayScript(ti ? ti.ma : o.ma, p, ti ? vaoMacDinh(ti, o.vao) : (o.vao || {}));
      if (!r.ok) throw r.loi + (r.dong ? ' (dòng ' + r.dong + ')' : '');
      const k = kiemPlan(p, r.plan), tt = tomTat(p, k.plan);
      for (const key of Object.keys(p)) delete p[key];
      Object.assign(p, k.plan);
      txt += `<ul class="tt">${[...(r.bao || []).map(esc), ...tt, ...k.cb.map(esc)].map(y => `<li>${y}</li>`).join('') || '<li>không đổi gì</li>'}</ul>`;
    } catch (e) { loi = typeof e === 'string' ? e : (e && e.message) || 'lỗi'; }
    out.push({txt, loi, ly_do: o.ly_do ? String(o.ly_do) : ''});
  }
  return out;
}
