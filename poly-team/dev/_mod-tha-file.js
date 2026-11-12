/* ============================== THẢ CLIP TỪ MÁY VÀO SỬA TAY (r34, 11/11/2026) ==============================
   Anh (11/11 10:53): "kéo thả clip vào time line" -> chọn "Từ thư mục máy tính (Windows)": kéo file .MOV / .MP4 từ File Explorer
   thả thẳng vào cửa sổ như CapCut.
   - Đang kéo file vào cửa sổ: lớp phủ nhẹ "Thả để thêm vào video" + khung vàng quanh chỗ sẽ thả + vạch vàng chỗ chèn trên timeline
     (dùng lại timDich / veDich của kéo từ Thư viện, _thu-vien.js).
   - Thả xuống timeline: chèn cảnh đúng chỗ thả; nhiều file chèn liền nhau theo tên file; video trống thì thành cảnh 1. Thả vào Thư
     viện (cột trái): chỉ thêm vào Thư viện (mở thư mục chứa clip, nháy viền vàng clip mới). Thả lên khung xem / chỗ khác: thêm vào
     cuối video. Ảnh / nhạc / thư mục: báo rõ, không gửi. Trang ngoài (index) thả lệch lên đầu trang thì chuyển vào đây (cuối video).
   - Chrome không cho biết đường dẫn thật -> trang hỏi máy chủ trước (POST /api/sua-tay/tha-file/hoi): file cùng tên + cỡ + giờ sửa đã
     có (thư mục Thư viện đang mở, thư mục clip của video, clip-tha) thì DÙNG LẠI, không gửi; không thì gửi nội dung file (XHR, có %,
     Huỷ) -> máy chủ ghi <video>/clip-tha/ (tha_file.py). Mỗi lượt gửi lần lượt từng file (đỡ nghẽn ổ).
   - Mỗi file 1 dòng tiến độ ở góc dưới Thư viện (% + MB, Huỷ). File xong: /them-clip (đo clip, bản xem nhẹ, ảnh khung như clip thường,
     card đồ hoạ nếu bật) rồi chèn cảnh (như themClipTV). Cả lượt thả = 1 bước Ctrl+Z: file sau gộp vào bước của file đầu nếu anh chưa
     sửa gì khác giữa chừng. Huỷ / lỗi: không chèn gì, file dở bị máy chủ xoá.
   - Tab Clip của Thư viện có chip "Clip đã thả (N)" (mở thư mục clip-tha) khi video có clip thả vào.
   Chỉ thêm file này + _mod-tha-file.css; bọc tvSauVe (vẽ xong tab Thư viện). Kiểm: dev/thu-sua-tay/thu_tha_file.py */
IC_P.tfTai = '<path d="M12 15V4"/><path d="M7.5 8.5 12 4l4.5 4.5"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>';
IC_P.tfX = '<path d="M6.5 6.5l11 11"/><path d="M17.5 6.5l-11 11"/>';
const TF = {hang: Promise.resolve(), lan: 0, thuMuc: '', so: 0, infoV: '', moi: [], moiHet: 0, trong: false, hen: 0};
(function () {
  const DUOI = ['mov', 'mp4', 'm4v', 'mkv'];
  const ANH = ['jpg', 'jpeg', 'png', 'heic', 'heif', 'webp', 'gif', 'bmp', 'tif', 'tiff'];
  const NHAC = ['mp3', 'm4a', 'wav', 'aac', 'flac', 'ogg', 'wma', 'opus'];
  const duoi = n => ((String(n || '').match(/\.([^.\\/]+)$/) || [])[1] || '').toLowerCase();
  const loaiSai = n => { const d = duoi(n); return DUOI.includes(d) ? '' : ANH.includes(d) ? 'anh' : NHAC.includes(d) ? 'nhac' : 'khac'; };
  const coFile = dt => !!dt && [...(dt.types || [])].includes('Files');
  const soVN = (x, l = 1) => x.toFixed(l).replace('.', ',');
  const gb = x => soVN(x / 1073741824) + ' GB', mbs = x => Math.round(x / 1048576) + ' MB';
  const coMB = (a, b) => b < 1073741824 ? Math.round(a / 1048576) + ' / ' + Math.max(1, Math.round(b / 1048576)) + ' MB' : (a < 1073741824 ? mbs(a) : soVN(a / 1073741824)) + ' / ' + gb(b);
  const tenNgan = n => String(n || '').replace(/\.[^.]+$/, '');

  /* ---------- chỗ sẽ thả ---------- */
  function cuoiVideo() { const b = bocCanh(); return {kieu: 'chen', i: S.plan.canh.length, x: (b.length ? b[b.length - 1].b : 0) * S.pps, cuoi: true}; }
  function dichTha(x, y) {
    if (!S.plan || $('#edit').hidden) return {kieu: 'khong', ly: 'Mở 1 video rồi thả clip vào'};
    if ($('.mbg, .ctm-bg')) return {kieu: 'khong', ly: 'Đóng hộp đang mở rồi thả lại'};
    const el = document.elementFromPoint(x, y), lib = $('#lib'), tl = $('#tl');
    if (el && lib && (lib.contains(el) || (el.closest('#tfKhay') && TF.khayLib))) return {kieu: 'tv', vung: lib};   // dòng tiến độ nằm trong góc Thư viện
    if (el && tl && tl.contains(el)) {
      const d = timDich({loai: 'clip'}, x, y);   // cùng cách chọn chỗ chèn với kéo clip từ Thư viện
      return Object.assign(d && d.kieu === 'chen' ? {kieu: 'chen', i: d.i, x: d.x, cuoi: d.i >= S.plan.canh.length} : cuoiVideo(), {vung: tl});
    }
    return Object.assign(cuoiVideo(), {vung: (el && el.closest('.pcol')) || $('#edit')});
  }
  function demKeo(dt) {   // lúc đang kéo chỉ biết số file + loại (MIME), chưa biết tên
    const it = [...((dt && dt.items) || [])].filter(i => i.kind === 'file');
    const sai = it.filter(i => /^(image|audio)\//.test(i.type || '')).length;
    return {n: it.length || ((dt && dt.files) || []).length || 1, sai, het: it.length > 0 && sai === it.length};
  }

  /* ---------- lớp phủ lúc kéo ---------- */
  let phu = null;
  function moPhu() {
    if (phu) return phu;
    phu = document.createElement('div'); phu.id = 'tfPhu'; phu.className = 'tf-phu'; phu.setAttribute('aria-hidden', 'true');
    phu.innerHTML = `<div class="tf-vung"></div><div class="tf-nhan">${icon('tfTai')}<span><b></b><small></small></span></div>`;
    document.body.append(phu); document.body.classList.add('tf-keo'); $$('.tip').forEach(x => x.classList.remove('on'));
    return phu;
  }
  function dongPhu() { clearTimeout(TF.hen); if (!phu) return; phu.remove(); phu = null; document.body.classList.remove('tf-keo'); veDich(null); }
  function veVung(d, dem) {
    const p = moPhu(), r = (d.vung || $('#edit') || document.body).getBoundingClientRect(), v = $('.tf-vung', p), nh = $('.tf-nhan', p);
    Object.assign(v.style, {left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px'});
    const sai = d.kieu === 'khong' || dem.het, n = dem.n - dem.sai, so = n > 1 ? n + ' clip' : 'clip';
    p.classList.toggle('sai', sai); p.dataset.kieu = d.kieu;
    $('b', nh).textContent = sai ? 'Chưa thả được ở đây' : d.kieu === 'tv' ? 'Thả để thêm vào Thư viện' : 'Thả để thêm vào video';
    $('small', nh).textContent = d.kieu === 'khong' ? d.ly : dem.het ? 'Chưa nhận ảnh / nhạc ở đây, chỉ clip .mov .mp4' : d.kieu === 'tv' ? so + ' · chưa chèn vào video'
      : (d.cuoi ? (d.i ? 'Thêm ' + so + ' vào cuối video (cảnh ' + (d.i + 1) + ')' : 'Thành cảnh 1') : 'Chèn ' + so + ' thành cảnh ' + (d.i + 1)) + (dem.sai ? ' · bỏ qua ảnh / nhạc' : '');
    const w = nh.offsetWidth || 260, h = nh.offsetHeight || 52;
    let x = r.left + r.width / 2, y = d.vung === $('#tl') ? r.top - h - 12 : d.kieu === 'tv' ? r.top + 56 : r.top + Math.min(r.height * 0.42, 220);
    x = clamp(x, w / 2 + 8, innerWidth - w / 2 - 8); y = clamp(y, 8, innerHeight - h - 8);
    nh.style.left = x + 'px'; nh.style.top = y + 'px';
    if (!sai && d.kieu === 'chen') { veDich({kieu: 'chen', i: d.i, x: d.x}); const l = $('#tvIns'); if (l) l.classList.add('tf'); } else veDich(null);
  }
  function keo(e) {
    if (TF.trong || !coFile(e.dataTransfer)) return;
    e.preventDefault();   // cho phép thả + Chrome không tự mở file thay trang
    const d = dichTha(e.clientX, e.clientY), dem = demKeo(e.dataTransfer);
    e.dataTransfer.dropEffect = TF.de = d.kieu === 'khong' || dem.het ? 'none' : 'copy';   // TF.de: để bài thử đọc (DataTransfer giả lập bỏ qua dropEffect)
    if (S.playing) dung();
    const tls = $('#tls'); if (tls && d.vung === $('#tl')) { const r = tls.getBoundingClientRect();   // sát mép timeline: cuộn theo
      if (e.clientY > r.top && e.clientY < r.bottom) { if (e.clientX < r.left + 40) tls.scrollLeft -= 14; else if (e.clientX > r.right - 40) tls.scrollLeft += 14; } }
    veVung(d, dem);
    clearTimeout(TF.hen); TF.hen = setTimeout(dongPhu, 700);   // kéo ra ngoài cửa sổ / bấm Esc: không còn dragover thì tắt lớp phủ
  }
  addEventListener('dragstart', () => { TF.trong = true; }, true);   // kéo thứ có sẵn trong trang (ảnh, chữ chọn): không phải file từ máy
  addEventListener('dragend', () => { TF.trong = false; }, true);
  addEventListener('dragenter', keo, true);
  addEventListener('dragover', keo, true);
  addEventListener('dragleave', e => { if (coFile(e.dataTransfer) && !e.relatedTarget) { clearTimeout(TF.hen); TF.hen = setTimeout(dongPhu, 120); } }, true);
  addEventListener('drop', e => {
    if (!coFile(e.dataTransfer)) return;
    e.preventDefault(); e.stopPropagation();
    if (TF.trong) { TF.trong = false; dongPhu(); return; }
    const d = dichTha(e.clientX, e.clientY); dongPhu();
    nhanFile(layFile(e.dataTransfer), d);
  }, true);
  function layFile(dt) {   // phải lấy ngay trong lúc thả (sau đó DataTransfer bị khoá)
    const it = [...(dt.items || [])].filter(i => i.kind === 'file'), out = [];
    if (it.length) it.forEach(i => { let en = null; try { en = i.webkitGetAsEntry && i.webkitGetAsEntry(); } catch (x) {} const f = i.getAsFile(); if (f) out.push({f, thuMuc: !!(en && en.isDirectory)}); });
    else [...(dt.files || [])].forEach(f => out.push({f, thuMuc: false}));
    return out;
  }
  // trang ngoài (index, chế độ Sửa tay) thả lệch lên đầu trang: thêm vào cuối video
  window.thaFileRe = () => { if (!S.plan) return; veVung(Object.assign(cuoiVideo(), {vung: $('#edit')}), {n: 1, sai: 0, het: false}); clearTimeout(TF.hen); TF.hen = setTimeout(dongPhu, 700); };
  window.thaFileTuNgoai = ds => { dongPhu(); nhanFile(ds || [], S.plan && !$('#edit').hidden ? cuoiVideo() : {kieu: 'khong', ly: 'Mở 1 video rồi thả clip vào'}); };

  /* ---------- nhận 1 lượt thả ---------- */
  function cacTm() {   // thư mục để dò file có sẵn: Thư viện đang mở + thư mục clip của video
    const ds = [S.tv.tm || (typeof tmTV === 'function' ? tmTV() : ''), ...Object.keys(S.plan.nguon || {}).map(f => thuMucCua(src(f)))].filter(Boolean);
    return [...new Map(ds.map(t => [chuanP(t), t])).values()].slice(0, 8);
  }
  function nhanFile(ds, d) {
    if (!d || d.kieu === 'khong') { if (ds.length) toast((d && d.ly) || 'Chưa thả được ở đây', true); return; }
    const ok = [], sai = {anh: [], nhac: [], khac: []}, tm = [];
    ds.forEach(x => { if (x.thuMuc) tm.push(x.f.name); else { const l = loaiSai(x.f.name); if (l) sai[l].push(x.f.name); else ok.push(x.f); } });
    const bao = [], ke = a => a.slice(0, 3).join(', ') + (a.length > 3 ? '…' : '');
    if (sai.anh.length || sai.nhac.length) bao.push('Chưa nhận ' + [sai.anh.length && 'ảnh', sai.nhac.length && 'nhạc'].filter(Boolean).join(' / ') + ' ở đây (' + ke([...sai.anh, ...sai.nhac]) + ')');
    if (sai.khac.length) bao.push('Không phải clip video (' + ke(sai.khac) + ')');
    if (tm.length) bao.push('Chưa nhận cả thư mục (' + ke(tm) + '): mở thư mục, chọn các clip rồi kéo vào');
    if (bao.length) toast(bao.join(' · ') + '. Chỉ nhận clip .mov .mp4 .m4v .mkv', true);
    if (!ok.length) return;
    ok.sort((a, b) => a.name.localeCompare(b.name, 'vi', {numeric: true, sensitivity: 'base'}));
    const lot = {id: ++TF.lan, v: S.v, tv: d.kieu === 'tv', viTri: d.i, truoc: d.kieu === 'chen' && !d.cuoi ? (S.plan.canh[d.i] || {})._id || null : null,
      da: 0, undoLen: -1, undoTop: null, dau: null, cuoiId: null, so: [], xong: []};
    lot.dong = ok.map(f => themDong(f, lot));
    TF.hang = TF.hang.then(() => chayLot(lot)).catch(e => { console.error(e); lot.dong.forEach(r => { if (!r.het) datDong(r, 'loi', e.message || 'Lỗi'); }); });
  }
  async function chayLot(lot) {
    const con = lot.dong.filter(r => !r.huy);
    if (!con.length) return;
    if (lot.v !== S.v) { con.forEach(r => datDong(r, 'loi', 'Đã đổi video khác, không thêm')); return; }
    con.forEach(r => datDong(r, 'kiem'));
    let hoi;
    try { hoi = await api('/api/sua-tay/tha-file/hoi', {v: lot.v, tm: cacTm(), ds: lot.dong.map(r => ({ten: r.f.name, co: r.f.size, luc: r.f.lastModified || null}))}); }
    catch (e) { con.forEach(r => datDong(r, 'loi', e.message)); return; }
    TF.thuMuc = hoi.thu_muc; TF.infoV = lot.v;
    lot.dong.forEach(r => { if (r.tt === 'kiem') datDong(r, 'cho'); });   // kiểm xong: file sau chờ tới lượt gửi
    for (let k = 0; k < lot.dong.length; k++) {
      const r = lot.dong[k], h = hoi.ds[k] || {};
      if (r.huy) { datDong(r, 'huy'); continue; }
      if (h.loi) { datDong(r, 'loi', h.loi); continue; }
      try {
        let p = h.co_san;
        if (p) datDong(r, 'san'); else p = (await guiFile(r, lot.v)).p;
        if (r.huy) throw huyLoi();
        if (lot.v !== S.v) throw new Error('Đã đổi video khác: clip vẫn lưu trong thư mục video cũ');
        if (lot.tv) { lot.xong.push(p); datDong(r, 'xong', h.co_san ? 'Có sẵn trong Thư viện' : 'Đã vào Thư viện'); continue; }
        datDong(r, 'doc');
        const n = await nguonTha(p);
        if (r.huy) throw huyLoi();
        if (lot.v !== S.v || !S.plan) throw new Error('Đã đổi video khác: clip vẫn lưu trong thư mục video cũ');
        const so = chenCanh(lot, n); lot.xong.push(p);
        datDong(r, 'xong', 'Cảnh ' + so);
      } catch (e) { datDong(r, e.huy ? 'huy' : 'loi', e.message); }
    }
    ketThuc(lot);
  }
  const huyLoi = () => Object.assign(new Error('Đã huỷ'), {huy: true});
  function guiFile(r, v) {   // gửi nội dung file (đĩa -> mạng trong máy, trình duyệt không nạp cả file vào bộ nhớ)
    return new Promise((ok, loi) => {
      const x = new XMLHttpRequest(), m = Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
      x.open('POST', '/api/sua-tay/tha-file/nhan?' + new URLSearchParams({v, ten: r.f.name, co: r.f.size, luc: r.f.lastModified || '', ma: m}));
      x.setRequestHeader('Content-Type', 'application/octet-stream');
      x.upload.onprogress = e => { if (!r.huy) datDong(r, e.loaded >= r.f.size ? 'luu' : 'gui', '', e.loaded); };
      x.onload = () => { let j = null; try { j = JSON.parse(x.responseText); } catch (e) {} if (x.status === 200 && j && j.p) ok(j); else if (j && j.huy) loi(huyLoi()); else loi(new Error((j && j.err) || 'Lỗi ' + x.status)); };
      x.onerror = () => loi(r.huy ? huyLoi() : new Error('Không gửi được file (mất kết nối với app, hoặc file đã bị xoá / đổi tên trên máy)'));
      x.onabort = () => loi(huyLoi());
      r.dung = () => { try { x.abort(); } catch (e) {} api('/api/sua-tay/tha-file/huy', {ma: m}).catch(() => {}); };
      datDong(r, 'gui', '', 0);
      x.send(r.f);
    });
  }
  async function nguonTha(p) {   // như nguonClipTV (_thu-vien.js) nhưng trả lỗi cho dòng tiến độ thay vì toast
    for (let k = 0; k < 100 && S.tv.them; k++) await new Promise(z => setTimeout(z, 100));   // anh đang bấm thêm 1 clip Thư viện: chờ xong
    const key = Object.keys(S.plan.nguon || {}).find(f => chuanP(src(f)) === chuanP(p));
    if (key && S.giay[key]) return {f: key, x: null, giay: S.giay[key]};
    const x = await api('/api/sua-tay/them-clip', {p});
    const f = key || x.local; S.giay[f] = x.giay;
    return {f, x: key ? null : x, giay: x.giay};
  }
  function chenCanh(lot, n) {   // chèn 1 cảnh (như themClipTV); file sau của cùng lượt gộp vào bước Ctrl+Z của file đầu
    const {f, x, giay} = n; let moi = null;
    const fn = pl => {
      if (x && !pl.nguon[f]) pl.nguon[f] = nguonMoi(x);
      let i = lot.truoc ? pl.canh.findIndex(c => c._id === lot.truoc) : -1;
      if (i < 0 && lot.cuoiId) { const j = pl.canh.findIndex(c => c._id === lot.cuoiId); if (j >= 0) i = j + 1; }
      if (i < 0) i = lot.truoc ? clamp(lot.viTri, 0, pl.canh.length) : pl.canh.length;
      moi = {_id: ma('c'), file: f, tu: 0, den: r3(Math.max(0.3, (giay || 5) - 0.05))};
      pl.canh.splice(i, 0, moi);
      if (!lot.dau) { S.sel.canh = moi._id; S.selLoai = 'canh'; }
    };
    const gop = lot.da > 0 && S.undo.length === lot.undoLen && S.undo[S.undo.length - 1] === lot.undoTop;   // chưa ai sửa gì xen giữa
    if (gop) { S.redo = []; S.lastKey = ''; fn(S.plan); sauDoi(true); }
    else { dung(); doi(fn); }
    lot.undoLen = S.undo.length; lot.undoTop = S.undo[S.undo.length - 1]; lot.da++; lot.cuoiId = moi._id;
    theoProxy();
    const b = bocCanh().find(y => y.c._id === moi._id);
    if (!lot.dau) { lot.dau = moi._id; if (b) { tua(b.bd + 0.02); giuVach(); } }
    const so = (b ? b.i : S.plan.canh.findIndex(c => c._id === moi._id)) + 1; lot.so.push(so);
    return so;
  }
  function ketThuc(lot) {
    if (!lot.xong.length) return;
    Object.keys(S.tv.ds).forEach(k => { if (lot.xong.some(p => chuanP(thuMucCua(p)) === chuanP(k))) delete S.tv.ds[k]; });   // Thư viện đọc lại thư mục có clip mới
    TF.moi = lot.xong.map(chuanP); TF.moiHet = Date.now() + 4000;
    layInfo(true);
    if (lot.tv) {
      const tm = thuMucCua(lot.xong[lot.xong.length - 1]);
      if (S.tv.tab !== 'clip') moTab('clip'); else if (S.tv.thu) datThu(false); else if ($('#edit').classList.contains('tv-tu-thu')) datNoi(true);
      if (chuanP(tm) !== chuanP(S.tv.tm)) datTm(tm); else veTV(true);
      toast(lot.xong.length > 1 ? 'Đã thêm ' + lot.xong.length + ' clip vào Thư viện' : 'Đã thêm ' + tenNgan(base(lot.xong[0])) + ' vào Thư viện');
      return;
    }
    veTV(true);
    const ds = [...lot.so].sort((a, b) => a - b);
    toast(ds.length > 1 ? 'Đã thêm ' + ds.length + ' cảnh (cảnh ' + ds[0] + '–' + ds[ds.length - 1] + ') · Ctrl+Z để bỏ cả lượt' : 'Đã thêm cảnh ' + ds[0] + ' (' + tenNgan(base(lot.xong[0])) + ') · Ctrl+Z để bỏ');
  }

  /* ---------- dòng tiến độ (góc dưới Thư viện) ---------- */
  function khay() {
    let k = $('#tfKhay');
    if (!k) { k = document.createElement('div'); k.id = 'tfKhay'; k.className = 'tf-khay'; k.setAttribute('role', 'status'); k.setAttribute('aria-live', 'polite'); document.body.append(k);
      k.addEventListener('click', e => { const b = e.target.closest('[data-tf]'); if (!b) return; const r = (TF.dong || []).find(x => x.id === b.closest('.tf-dong').dataset.id); if (!r) return;
        if (b.dataset.tf === 'huy') { r.huy = true; if (r.dung) r.dung(); datDong(r, 'huy'); } else boDong(r); }); }
    datKhay(k); return k;
  }
  function datKhay(k) {   // nằm trong góc dưới cột Thư viện; Thư viện thu gọn / hẹp thì góc dưới khung xem
    k = k || $('#tfKhay'); if (!k) return;
    const lib = $('#lib'), rl = lib && !$('#edit').hidden ? lib.getBoundingClientRect() : null, vua = rl && rl.width >= 220;
    const r = vua ? rl : ($('.pcol') && !$('#edit').hidden ? $('.pcol').getBoundingClientRect() : {left: 8, bottom: innerHeight - 8, width: 340}); TF.khayLib = !!vua;
    k.style.left = (r.left + 8) + 'px'; k.style.width = Math.min(360, Math.max(240, r.width - 16)) + 'px'; k.style.bottom = Math.max(8, innerHeight - r.bottom + 8) + 'px';
  }
  addEventListener('resize', () => datKhay());
  TF.dong = [];
  function themDong(f, lot) {
    const r = {id: 'tf' + Math.random().toString(36).slice(2, 9), f, lot, tt: 'cho'}; TF.dong.push(r);
    const el = document.createElement('div'); el.className = 'tf-dong'; el.dataset.id = r.id; r.el = el;
    el.innerHTML = `<span class="tf-ten" title="${esc(f.name)}">${esc(f.name)}</span><span class="tf-tt"></span><span class="tf-nut"></span><i class="tf-thanh"><b></b></i>`;
    khay().append(el); datDong(r, 'cho'); return r;
  }
  function boDong(r) { r.het = true; if (r.el) r.el.remove(); TF.dong = TF.dong.filter(x => x !== r); const k = $('#tfKhay'); if (k && !k.children.length) k.remove(); }
  function datDong(r, tt, ct, gui) {
    if (r.het) return;
    r.tt = tt; const el = r.el; el.dataset.tt = tt;
    const pc = gui != null ? Math.min(100, Math.floor(gui / Math.max(1, r.f.size) * 100)) : null;
    const chu = {cho: 'Chờ…', kiem: 'Đang kiểm…', san: 'Có sẵn trên máy · không cần gửi lại', gui: pc != null ? pc + '% · ' + coMB(gui, r.f.size) : 'Đang gửi…',
      luu: 'Đang lưu… ' + coMB(r.f.size, r.f.size), doc: 'Đang đọc clip…', xong: (ct || 'Xong'), huy: 'Đã huỷ', loi: ct || 'Lỗi'}[tt];
    $('.tf-tt', el).innerHTML = (tt === 'xong' ? icon('dauTick') : '') + esc(chu);
    $('.tf-tt', el).title = tt === 'loi' ? chu : '';
    $('.tf-thanh b', el).style.width = (tt === 'gui' ? (pc || 0) : tt === 'luu' || tt === 'doc' || tt === 'xong' ? 100 : 0) + '%';
    const dangChay = ['cho', 'kiem', 'san', 'gui', 'luu', 'doc'].includes(tt);
    $('.tf-nut', el).innerHTML = dangChay ? `<button type="button" class="tf-b" data-tf="huy" aria-label="Huỷ ${esc(r.f.name)}">Huỷ</button>`
      : `<button type="button" class="tf-b tf-bx" data-tf="dong" aria-label="Ẩn dòng này" data-tip="Ẩn">${icon('tfX')}</button>`;
    if (tt === 'xong' || tt === 'huy') setTimeout(() => boDong(r), tt === 'xong' ? 5000 : 2500);
    datKhay();
  }

  /* ---------- Thư viện: chip "Clip đã thả", nháy viền clip mới ---------- */
  function layInfo(ep) {
    if (!S.plan || !S.v) return;
    if (!ep && TF.infoV === S.v && TF.daHoi) return;
    const v = S.v; TF.infoV = v; TF.daHoi = true;
    api('/api/sua-tay/tha-file?v=' + encodeURIComponent(v)).then(r => { if (S.v !== v) return; const doi = r.so !== TF.so || r.thu_muc !== TF.thuMuc; TF.thuMuc = r.thu_muc; TF.so = r.so; if (doi && S.tv.tab === 'clip') veTV(true); }).catch(() => {});
  }
  function chipTha(pane) {
    if (TF.infoV !== S.v) { TF.so = 0; TF.thuMuc = ''; TF.daHoi = false; }
    layInfo(false);
    const dangO = TF.thuMuc && chuanP(TF.thuMuc) === chuanP(S.tv.tm);
    if (dangO) { const b = $('.tv-tmt b', pane); if (b) b.textContent = 'Clip đã thả vào'; }
    if (TF.so && TF.thuMuc && !dangO) {
      let row = $('.tv-tmk', pane);
      if (!row) { const tm = $('.tv-tm', pane); if (!tm) return; row = document.createElement('div'); row.className = 'tv-tmk'; row.innerHTML = '<span>Thư mục khác của video:</span>'; tm.after(row); }
      let b = [...row.querySelectorAll('[data-tvtm]')].find(x => chuanP(x.dataset.tvtm) === chuanP(TF.thuMuc));
      if (!b) { b = document.createElement('button'); b.type = 'button'; b.className = 'tvchip'; b.dataset.tvtm = TF.thuMuc; row.querySelector('span').after(b); }
      b.classList.add('tf-chip'); b.dataset.tip = 'Clip anh kéo từ máy vào video này (lưu trong thư mục video, không đụng thư mục clip gốc)';
      b.innerHTML = icon('tfTai') + 'Clip đã thả (' + TF.so + ')';
    }
    if (Date.now() < TF.moiHet) { let dau = null;
      $$('[data-tvclip]', pane).forEach(t => { if (TF.moi.includes(chuanP(t.dataset.tvclip))) { t.classList.add('tf-moi'); dau = dau || t; } });
      if (dau) dau.scrollIntoView({block: 'nearest'}); }
  }
  const sauVeGoc = typeof tvSauVe === 'function' ? tvSauVe : null;
  tvSauVe = function (tab, pane) { const r = sauVeGoc ? sauVeGoc(tab, pane) : undefined; if (tab === 'clip' && S.plan) chipTha(pane); return r; };   // eslint-disable-line no-func-assign
})();
