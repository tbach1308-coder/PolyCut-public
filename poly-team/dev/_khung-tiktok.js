/* ============================== KHUNG CANH LỀ (dùng chung trang chính + Sửa tay) ==============================
   Vẽ phác giao diện TikTok (không phải logo TikTok) đè lên khung 9:16 để canh chữ không bị che.
   Toạ độ theo khung 1080×1920. Vùng an toàn: trên 240, dưới 660, 2 bên 120, cột nút phải chiếm 180 từ y 840.
   kieu: 'an_toan' (chỉ khung vàng) | 'tiktok' (Dành cho bạn) | 'gio' (TikTok có link sản phẩm)
   o.cap = dòng caption, o.tag = dòng hashtag, o.sp = chữ trên link sản phẩm. */
const KHUNG_DS = [
  {v: '', ten: 'Không'},
  {v: 'an_toan', ten: 'Vùng an toàn'},
  {v: 'tiktok', ten: 'Giao diện TikTok'},
  {v: 'gio', ten: 'TikTok có link sản phẩm'}
];
function khungTT(kieu, o) {
  if (!kieu) return '';
  o = o || {};
  const e = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'})[c]);
  const vung = '<path d="M120 240H960V840H900V1260H120Z" fill="none" stroke="#FFD600" stroke-opacity=".85" stroke-width="4" stroke-dasharray="16 12"/>';
  if (kieu === 'an_toan') return `<svg class="tt" viewBox="0 0 1080 1920" preserveAspectRatio="none" aria-hidden="true">${vung}</svg>`;
  const cap = (o.cap || 'Caption khi đăng').slice(0, 34);
  const tag = o.tag || '#polystore #xuhuong';
  const nut = (y, ve, so) => `<g transform="translate(990 ${y})">${ve}</g><text x="990" y="${y + 74}" font-size="30" font-weight="700" text-anchor="middle">${so}</text>`;
  const gio = kieu === 'gio'
    ? `<rect x="48" y="1510" width="560" height="70" rx="12" fill="#000" fill-opacity=".45"/>
       <rect x="48" y="1510" width="70" height="70" rx="12" fill="#ff7a1a"/>
       <path d="M66 1532h6l6 26h24l6-18H76" fill="none" stroke="#fff" stroke-width="5" stroke-linejoin="round"/><circle cx="82" cy="1566" r="4"/><circle cx="100" cy="1566" r="4"/>
       <text x="136" y="1557" font-size="32" font-weight="700">${e((o.sp || 'Link sản phẩm').slice(0, 26))}</text>`
    : '';
  return `<svg class="tt" viewBox="0 0 1080 1920" preserveAspectRatio="none" aria-hidden="true">
    <defs><filter id="ttb" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity=".5"/></filter></defs>
    ${vung}
    <g fill="#fff" filter="url(#ttb)" font-family="Be Vietnam Pro,Segoe UI,sans-serif">
      <rect x="44" y="108" width="82" height="54" rx="10" fill="none" stroke="#fff" stroke-width="5"/>
      <text x="85" y="145" font-size="24" font-weight="800" text-anchor="middle">LIVE</text>
      <text x="500" y="150" font-size="38" font-weight="600" fill-opacity=".7" text-anchor="end">Đã follow</text>
      <text x="550" y="150" font-size="40" font-weight="800">Dành cho bạn</text>
      <rect x="640" y="172" width="80" height="6" rx="3"/>
      <circle cx="990" cy="134" r="22" fill="none" stroke="#fff" stroke-width="6"/><path d="M1006 150l18 18" stroke="#fff" stroke-width="7" stroke-linecap="round"/>
      <circle cx="990" cy="930" r="54" fill="#1f8f4e" stroke="#fff" stroke-width="5"/>
      <text x="990" y="950" font-size="52" font-weight="900" text-anchor="middle">P</text>
      <circle cx="990" cy="986" r="19" fill="#ff3b5c"/><path d="M980 986h20M990 976v20" stroke="#fff" stroke-width="5" stroke-linecap="round"/>
      ${nut(1080, '<path d="M0 38C-55 0-50-38-22-38C-9-38 0-29 0-21C0-29 9-38 22-38C50-38 55 0 0 38Z"/>', '12,4K')}
      ${nut(1236, '<ellipse cx="0" cy="-4" rx="38" ry="31"/><path d="M-22 18L-30 42L4 22Z"/>', '318')}
      ${nut(1392, '<path d="M-24-36H24V38L0 20L-24 38Z"/>', '1.204')}
      ${nut(1548, '<path d="M34 -4L-4 -38V-18C-36 -18 -52 4 -54 34C-40 16 -24 10 -4 10V30Z"/>', '256')}
      <circle cx="990" cy="1744" r="42" fill="#222" stroke="#3a3a3a" stroke-width="14"/><circle cx="990" cy="1744" r="13" fill="#1f8f4e"/>
      ${gio}
      <text x="48" y="1620" font-size="42" font-weight="800">@poly.store</text>
      <text x="48" y="1682" font-size="36" font-weight="500">${e(cap)}</text>
      <text x="48" y="1732" font-size="34" font-weight="600" fill-opacity=".85">${e(tag)}</text>
      <text x="48" y="1800" font-size="32" font-weight="500" fill-opacity=".9">♫ âm thanh gốc - Poly Store</text>
    </g></svg>`;
}
