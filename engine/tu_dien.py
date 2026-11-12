#!/usr/bin/env python3
"""Từ điển của tiệm cho PHỤ ĐỀ TỰ ĐỘNG (POLY Cut, 4/11).

Anh hỏi "phụ đề tự động có tăng độ chính xác nghe giọng nói được không". File này làm 2 việc, không cài thêm gì:
1. Máy nghe ưu tiên từ hay nói của tiệm (sherpa-onnx `modified_beam_search` + hotwords): từ trong mục "TỪ HAY NÓI"
   của tu-dien-tiem.txt (bỏ từ có chữ số) -> in hoa -> file hotwords. Bảng mã bpe.vocab sherpa cần để mã hoá hotwords
   đọc thẳng từ bpe.model của mô hình (đọc protobuf bằng Python thuần, không cần sentencepiece).
   Mức ưu tiên: dòng `@uu_tien 1.0` trong từ điển (0 = tắt, nghe như cũ greedy_search).
2. Sửa chữ sau khi nghe (sua_tu): luật "sai => đúng" của anh, viết đúng tên máy (ipad pro -> iPad Pro, mac book -> MacBook),
   số / giá / đơn vị theo gu kênh: "mười ba triệu chín" -> 13TR9, "mười hai chấm chín in" -> 12.9 inch,
   "hai không hai mươi" -> 2020, "sáu tư gb" -> 64GB, "một trăm hai mươi héc" -> 120Hz, "chín mươi tám phần trăm" -> 98%,
   "m một" -> M1, "iphone mười ba" -> iPhone 13. Chữ số lẻ ("một chiếc", "bốn loa", "không khác gì") GIỮ chữ.
   Nhiều từ gộp thành 1 thì giờ = từ đầu tới từ cuối; 1 từ tách thành nhiều thì chia đều giờ theo độ dài chữ.

Chỉ phần "Phụ đề tự động" của POLY Cut dùng (sua_tay_may.py). nghe.py / canh_tu.py (Claude dựng, bản 1) KHÔNG dùng file này:
canh_tu so chữ phụ đề với lời nghe từng tiếng, gộp số sẽ làm lệch.

Thử: python3 tu_dien.py "mười ba triệu chín" "trên tay mình đây là ai pát pro mười hai chấm chín in hai không hai mươi"
"""
import hashlib
import os
import re
import struct
import sys
import unicodedata

DIR = os.path.dirname(os.path.abspath(__file__))
TEP = os.path.join(DIR, "tu-dien-tiem.txt")
UU_TIEN_MAC_DINH = 1.0


# ------------------------------------------------------------------ đọc từ điển
def _nfc(s):
    return unicodedata.normalize("NFC", str(s or ""))


def doc(p=None):
    """-> {"tu": ["iPad Pro", ...], "sua": [(("ai", "pát"), "iPad"), ...], "uu_tien": 1.0, "khoa": băm nội dung}.
    Không có file / đọc lỗi: từ điển rỗng (máy nghe chạy như cũ)."""
    p = p or os.environ.get("POLY_TU_DIEN") or TEP
    out = {"tu": [], "sua": [], "uu_tien": UU_TIEN_MAC_DINH, "khoa": "", "tep": p}
    try:
        with open(p, encoding="utf-8-sig") as f:
            raw = f.read()
    except OSError:
        return out
    out["khoa"] = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
    for dong in _nfc(raw).splitlines():
        d = dong.split("#", 1)[0].strip() if not dong.lstrip().startswith("#") else ""
        if not d:
            continue
        if d.startswith("@"):
            m = re.match(r"@uu_tien\s*[:=]?\s*([\d.,]+)", d, re.I)
            if m:
                try:
                    out["uu_tien"] = max(0.0, min(5.0, float(m.group(1).replace(",", "."))))
                except ValueError:
                    pass
            continue
        if "=>" in d or "->" in d:
            a, b = re.split(r"=>|->", d, maxsplit=1)
            a, b = " ".join(a.lower().split()), " ".join(b.split())
            if a and b:
                out["sua"].append((tuple(a.split()), b))
            continue
        out["tu"].append(" ".join(d.split()))
    out["sua"].sort(key=lambda x: -len(x[0]))  # cụm dài khớp trước
    return out


# ------------------------------------------------------------------ máy nghe ưu tiên từ của tiệm
def _bpe_vocab(bpe_model, ra):
    """bpe.model (protobuf sentencepiece) -> file "mảnh<TAB>điểm" như export_bpe_vocab.py của sherpa. Python thuần."""
    with open(bpe_model, "rb") as f:
        buf = f.read()

    def varint(b, i):
        n = s = 0
        while True:
            c = b[i]
            i += 1
            n |= (c & 0x7F) << s
            s += 7
            if c < 0x80:
                return n, i

    def fields(b):
        i = 0
        while i < len(b):
            k, i = varint(b, i)
            no, ty = k >> 3, k & 7
            if ty == 0:
                v, i = varint(b, i)
            elif ty == 1:
                v, i = b[i:i + 8], i + 8
            elif ty == 2:
                ln, i = varint(b, i)
                v, i = b[i:i + ln], i + ln
            elif ty == 5:
                v, i = b[i:i + 4], i + 4
            else:
                raise ValueError("bpe.model lạ")
            yield no, ty, v

    dong = []
    for no, ty, v in fields(buf):
        if no == 1 and ty == 2:  # SentencePiece {1: piece, 2: score}
            piece, score = "", 0.0
            for n2, t2, v2 in fields(v):
                if n2 == 1:
                    piece = v2.decode("utf-8")
                elif n2 == 2 and t2 == 5:
                    score = struct.unpack("<f", v2)[0]
            dong.append("%s\t%s\n" % (piece, score))
    if not dong:
        raise ValueError("bpe.model không có mảnh nào")
    with open(ra, "w", encoding="utf-8") as f:
        f.writelines(dong)
    return ra


def _co_so(s):
    return bool(re.search(r"\d", s))


def hotwords(td):
    """Từ hay nói -> dòng hotwords (IN HOA, chỉ chữ cái). Từ có chữ số (M1, 64GB) bỏ: máy nghe viết số bằng chữ."""
    out = []
    for t in list(td.get("tu") or []) + [b for _, b in td.get("sua") or []]:
        if _co_so(t) or len(re.sub(r"\W", "", t)) <= 3:   # bỏ từ có số (M1) và từ ngắn (Pro, Air, Pin, GB): dễ chèn nhầm
            continue
        w = " ".join(re.sub(r"[^\w\s]", " ", t).split()).upper()
        if w and w not in out:
            out.append(w)
    return out


def recognizer(mdir, td=None, threads=2, kho=None):
    """Máy nghe sherpa. Có từ hay nói + @uu_tien > 0 + mô hình có bpe.model -> modified_beam_search + hotwords;
    không thì greedy_search như nghe.py. -> (rec, khoa_cache) — khoa đổi khi cách nghe đổi (cache lời nghe theo khoá này)."""
    import sherpa_onnx
    td = td if td is not None else doc()
    f = lambda pat: next(os.path.join(mdir, x) for x in sorted(os.listdir(mdir)) if re.match(pat, x))
    kw = dict(encoder=f(r"encoder.*\.onnx$"), decoder=f(r"decoder.*\.onnx$"), joiner=f(r"joiner.*\.onnx$"),
              tokens=os.path.join(mdir, "tokens.txt"), num_threads=threads)
    hw = hotwords(td)
    diem = float(td.get("uu_tien") or 0)
    bpe = os.path.join(mdir, "bpe.model")
    if hw and diem > 0 and os.path.isfile(bpe):
        try:
            kho = kho or os.path.join(DIR, "_cache", "tu-dien")
            os.makedirs(kho, exist_ok=True)
            st = os.stat(bpe)
            voc = os.path.join(kho, "bpe-%s.vocab" % hashlib.md5(("%s|%s|%s" % (bpe, st.st_size, int(st.st_mtime))).encode()).hexdigest()[:10])
            if not os.path.isfile(voc):
                _bpe_vocab(bpe, voc + ".tam")
                os.replace(voc + ".tam", voc)
            noi = "\n".join(hw) + "\n"
            k = hashlib.md5(noi.encode("utf-8")).hexdigest()[:10]
            hp = os.path.join(kho, "hotwords-%s.txt" % k)
            if not os.path.isfile(hp):
                with open(hp + ".tam", "w", encoding="utf-8") as fo:
                    fo.write(noi)
                os.replace(hp + ".tam", hp)
            rec = sherpa_onnx.OfflineRecognizer.from_transducer(
                decoding_method="modified_beam_search", max_active_paths=4, hotwords_file=hp, hotwords_score=diem,
                modeling_unit="bpe", bpe_vocab=voc, **kw)
            return rec, "hw-%s-%s" % (k, diem)
        except Exception as e:  # noqa  bản sherpa / mô hình không hỗ trợ: nghe như cũ
            print("tu_dien: không bật được ưu tiên từ (%s), nghe như cũ" % e, file=sys.stderr)
    return sherpa_onnx.OfflineRecognizer.from_transducer(decoding_method="greedy_search", **kw), "greedy"


# ------------------------------------------------------------------ bỏ khoảng im đầu đoạn
def bo_im_dau(a, t0, t1, sr=16000, nguong_db=-35.0, dem=0.25):
    """Giờ bắt đầu có tiếng trong đoạn [t0, t1] của tiếng a (mảng float −1..1). Máy nghe sherpa hay đặt 1–2 chữ đầu ở giây 0
    khi đầu đoạn im lặng (clip thật 4/11: "trên tay" ở 0,04s, người nói từ 1,2s; "với hiệu" ở 0,04s, nói từ 1,7s) -> phụ đề hiện
    sớm 1–2 giây và câu đầu bị tách đôi. Trả t0 mới = 0,25s trước khung 20ms đầu tiên to hơn −35 dB (giống silencedetect của
    nghe.py) nếu khoảng im đầu đoạn > 0,3s; đoạn không có tiếng nào > −45 dB -> None (bỏ, đỡ chữ "ừ" ma); còn lại trả t0."""
    import numpy as np
    x = np.asarray(a[int(t0 * sr):int(t1 * sr)], dtype=np.float32)
    n = int(0.02 * sr)
    k = len(x) // n
    if k < 5:
        return t0
    db = 10 * np.log10(np.mean(x[:k * n].reshape(k, n) ** 2, axis=1) + 1e-12)
    if float(db.max()) < -45.0:
        return None
    on = np.nonzero(db > nguong_db)[0]
    if not len(on):
        return t0
    s = t0 + on[0] * 0.02 - dem
    return round(s, 3) if s - t0 > 0.3 else t0


# ------------------------------------------------------------------ chia câu phụ đề
# từ ghép / cụm hay gặp trong video của tiệm: không tách sang 2 câu phụ đề (giống ve_chu.KHONG_TACH + thêm từ ghép thường)
TU_GHEP = {("có", "thể"), ("thoải", "mái"), ("giống", "như"), ("như", "là"), ("giải", "trí"), ("cảm", "giác"), ("sử", "dụng"),
           ("âm", "thanh"), ("bàn", "phím"), ("làm", "việc"), ("hiệu", "năng"), ("thời", "gian"), ("phiên", "bản"), ("màn", "hình"),
           ("thiết", "kế"), ("mượt", "mà"), ("tấm", "nền"), ("tựa", "game"), ("các", "thứ"), ("kèm", "theo"), ("kèm", "với"),
           ("trên", "tay"), ("rất", "là"), ("cơ", "bản"), ("đó", "là"), ("sẽ", "là"), ("soạn", "thảo"), ("học", "sinh"), ("sinh", "viên"), ("học", "tập"),
           ("văn", "bản"), ("giá", "bán"), ("bên", "mình"), ("thay", "thế"), ("đặc", "biệt"), ("mở", "khóa"), ("hay", "không"),
           ("được", "không"), ("thế", "này"), ("như", "thế"), ("chơi", "game"), ("xem", "phim"), ("bảo", "hành"), ("dung", "lượng"),
           ("cấu", "hình"), ("điện", "thoại"), ("máy", "tính"), ("sạc", "pin"), ("chính", "hãng"), ("ngoại", "hình"), ("trải", "nghiệm")}
CUOI_CAU = {"ha", "nha", "nhé", "nhá", "luôn", "ạ", "á", "nè", "đó", "rồi"}          # tiếng đệm cuối: dính câu trước
DAU_CUM = {"của", "là", "những", "các", "chiếc", "cái", "một", "với", "và", "để", "cho", "như", "rất", "có", "đến", "con", "mấy"}
DON_VI_SAU = {"inch", "gb", "tb", "hz", "%", "tr", "triệu", "k", "nghìn", "ngàn", "giờ", "tiếng", "loa"}


def _khong_tach(a, b, cum):
    a, b = _nfc(a).lower().strip(",.!?"), _nfc(b).lower().strip(",.!?")
    if (a, b) in TU_GHEP or (a + " " + b) in cum:
        return True
    so = a.replace(".", "").replace(",", "").isdigit()
    return so and b in DON_VI_SAU


def chia_cau(ds, td=None, toi_da=6):
    """[[từ, giây, hết, đoạn]] -> câu phụ đề 2–6 chữ (thay sua_tay_may._chia_cau, 4/11). Vẫn ngắt ở chỗ nghỉ > 0,45s / đổi đoạn;
    chuỗi dài thì chọn chỗ ngắt tốt nhất (quy hoạch động): câu ~4–5 chữ, ngắt ở chỗ ngừng nói lâu hơn, KHÔNG tách tên máy / game
    ("Liên Quân", "Tốc Chiến", "iPad Pro"), từ ghép ("có thể", "thoải mái"), số + đơn vị ("12.9 inch"); tiếng đệm "ha / nha / luôn"
    dính câu trước; không ngắt ngay sau "của / là / những / chiếc…". Bản cũ chia đều theo số chữ: "Liên Quân Tốc | Chiến"."""
    td = td if td is not None else doc()
    cum = set()
    for t in list(td.get("tu") or []) + [b for _, b in td.get("sua") or []]:
        w = _nfc(t).lower().split()
        cum.update(" ".join(w[i:i + 2]) for i in range(len(w) - 1))
    chuoi, cur = [], []
    for w in ds:
        if cur and (float(w[1]) - float(cur[-1][2]) > 0.45 or (len(w) > 3 and len(cur[-1]) > 3 and w[3] != cur[-1][3])):
            chuoi.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chuoi.append(cur)
    GIA_DAI = {1: 6.0, 2: 1.5, 3: 0.3, 4: 0.0, 5: 0.0, 6: 0.6}
    out = []
    for c in chuoi:
        n = len(c)
        if n <= toi_da + 1:
            out.append(c)
            continue

        def gia_cat(i):   # cắt giữa c[i-1] | c[i]
            a, b = str(c[i - 1][0]), str(c[i][0])
            g = 0.0
            if _khong_tach(a, b, cum):
                g += 5.0
            if _nfc(b).lower().strip(",.!?") in CUOI_CAU:
                g += 3.0
            if _nfc(a).lower().strip(",.!?") in DAU_CUM:
                g += 2.0
            g -= min(0.4, max(0.0, float(c[i][1]) - float(c[i - 1][2]))) * 6
            return g

        best = [0.0] + [1e9] * n
        tr = [0] * (n + 1)
        for j in range(1, n + 1):
            for L in range(1, toi_da + 1):
                i = j - L
                if i < 0:
                    break
                g = best[i] + GIA_DAI[L] + (gia_cat(i) if i > 0 else 0.0)
                g += 1.0 if len(" ".join(str(x[0]) for x in c[i:j])) > 26 else 0.0
                if g < best[j]:
                    best[j], tr[j] = g, i
        cat, j = [], n
        while j > 0:
            cat.append((tr[j], j))
            j = tr[j]
        out += [c[a:b] for a, b in reversed(cat)]
    return out


# ------------------------------------------------------------------ đọc số tiếng Việt
SO = {"không": 0, "một": 1, "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4, "năm": 5, "lăm": 5, "sáu": 6, "bảy": 7, "bẩy": 7,
      "tám": 8, "chín": 9}
SO_DON = {"không", "một", "hai", "ba", "bốn", "năm", "sáu", "bảy", "bẩy", "tám", "chín"}   # chữ số đứng đầu được
SO_SAU = {"mốt", "tư", "lăm"}                                                             # chỉ đứng sau (21, 24, 25)
NHAN = {"mười", "mươi", "trăm", "nghìn", "ngàn", "triệu"}
TU_SO = set(SO) | NHAN | {"linh", "lẻ", "chấm", "phẩy", "rưỡi"}
# đứng trước chữ số lẻ thì đọc thành số (iphone mười một, m một, gen chín, pin tám tám)
MOI_SO = {"iphone", "ipad", "gen", "air", "mini", "series", "ios", "watch", "đời", "pin", "ram", "s", "se", "plus", "số"}
DV_GB = {("gb",): "GB", ("gi", "bi"): "GB", ("ghi", "ga"): "GB", ("gi",): "GB", ("tb",): "TB", ("tê", "bê"): "TB",
         ("tê", "ra"): "TB"}
DV_HZ = {("hz",), ("héc",), ("hét",), ("hẹc",), ("hec",), ("hertz",)}
DV_INCH = {("inch",), ("in",), ("inh",), ("ins",), ("ing",), ("inches",)}
DV_PT = {("phần", "trăm"), ("%",)}


def _khop(ws, i, bang):
    for k in sorted(bang, key=len, reverse=True):
        if tuple(x.lower() for x in ws[i:i + len(k)]) == k:
            return len(k)
    return 0


def _duoi_99(ws, i, sau_tram=False):
    """Đọc 0–99 từ ws[i:] -> (giá trị, số từ) | None. "mười hai", "hai mươi lăm", "ba mốt"; sau trăm: "linh năm", "hai mốt"."""
    n = len(ws)
    if i >= n:
        return None
    w = ws[i]
    if w in ("linh", "lẻ") and sau_tram and i + 1 < n and ws[i + 1] in SO_DON - {"không"}:
        return SO[ws[i + 1]], 2
    if w == "mười":
        if i + 1 < n and ws[i + 1] in SO and ws[i + 1] not in ("không", "năm", "mốt", "tư"):
            return 10 + SO[ws[i + 1]], 2
        return 10, 1
    if w in SO_DON:
        if i + 1 < n and ws[i + 1] == "mươi":
            if i + 2 < n and ws[i + 2] in SO and ws[i + 2] not in ("không", "năm"):
                return SO[w] * 10 + SO[ws[i + 2]], 3
            return SO[w] * 10, 2
        if sau_tram and w != "không" and i + 1 < n and ws[i + 1] in (SO_DON | SO_SAU) - {"không", "năm"}:
            return SO[w] * 10 + SO[ws[i + 1]], 2   # "một trăm hai mốt" = 121
        return SO[w], 1
    return None


def _duoi_1000(ws, i):
    """0–999 -> (giá trị, số từ, có_nhân) | None."""
    n = len(ws)
    if i < n and ws[i] in SO_DON and i + 1 < n and ws[i + 1] == "trăm":
        v, k = SO[ws[i]] * 100, 2
        r = _duoi_99(ws, i + 2, sau_tram=True)
        if r:
            v, k = v + r[0], k + r[1]
        return v, k, True
    r = _duoi_99(ws, i)
    if not r:
        return None
    return r[0], r[1], r[1] > 1 or ws[i] == "mười"


def _so_nguyen(ws, i):
    """Số nguyên kèm nghìn / ngàn (không gồm triệu) -> (giá trị, số từ, có_nhân, đuôi_k)."""
    r = _duoi_1000(ws, i)
    if not r:
        return None
    v, k, nhan = r
    if i + k < len(ws) and ws[i + k] in ("nghìn", "ngàn"):
        k += 1
        r2 = _duoi_1000(ws, i + k)
        if r2 and (r2[2] or ws[i + k] not in ("năm", "một")):
            return v * 1000 + r2[0] * (1 if r2[2] else 100), k + r2[1], True, False
        return v * 1000, k, True, True
    return v, k, nhan, False


def _chuoi_chu_so(ws, i, toi_da=4):
    """"sáu tư" -> "64", "một hai tám" -> "128", "chín chín" -> "99": đọc từng chữ số (chỉ dùng khi có đơn vị / từ mồi)."""
    s, k = "", 0
    while i + k < len(ws) and k < toi_da and ws[i + k] in SO and (k > 0 or ws[i + k] not in SO_SAU):
        s += str(SO[ws[i + k]])
        k += 1
    return (s, k) if s else None


def _nam(ws, i):
    """Năm "hai không hai mươi" / "hai không hai ba" / "hai nghìn không trăm hai mươi" -> ("2020", số từ)."""
    if ws[i:i + 2] == ["hai", "không"]:
        r = _duoi_99(ws, i + 2)
        if r and (r[1] > 1 or ws[i + 2] == "mười"):
            return "20%02d" % r[0], 2 + r[1]
        c = _chuoi_chu_so(ws, i + 2, 2)
        if c and c[1] == 2:
            return "20" + c[0], 4
    if ws[i:i + 5] == ["hai", "nghìn", "không", "trăm", "hai"] or ws[i:i + 5] == ["hai", "ngàn", "không", "trăm", "hai"]:
        r = _duoi_99(ws, i + 4)
        if r and 10 <= r[0] <= 39:
            return "20%02d" % r[0], 4 + r[1]
    return None


def _gia(ws, i):
    """"mười ba triệu chín" -> "13TR9", "mười ba triệu chín trăm năm mươi" -> "13TR95", "tám triệu rưỡi" -> "8TR5",
    "mười hai triệu" -> "12TR". -> (chữ, số từ) | None."""
    r = _duoi_1000(ws, i)
    if not r or i + r[1] >= len(ws) or ws[i + r[1]] != "triệu":
        return None
    v, k = r[0], r[1] + 1
    j = i + k
    if j < len(ws) and ws[j] == "rưỡi":
        return "%dTR5" % v, k + 1
    r2 = _duoi_1000(ws, j)
    if r2 and r2[0] > 0:
        le, k2 = r2[0], r2[1]
        if r2[2] and j + k2 < len(ws) and ws[j + k2] in ("nghìn", "ngàn"):
            k2 += 1
        elif not r2[2] and k2 == 1:
            le *= 100     # "triệu chín" = 900 nghìn
        if le < 1000:
            return "%dTR%s" % (v, ("%03d" % le).rstrip("0") or "0"), k + k2
    return "%dTR" % v, k


def _so_tai(ws, i, truoc):
    """Đọc 1 số bắt đầu ở ws[i] -> (chữ ra, số từ đã ăn) | None. Bảo thủ: chữ số lẻ không đơn vị / từ mồi thì bỏ qua."""
    w = ws[i]
    if w not in SO_DON and w != "mười":
        return None
    n = _nam(ws, i)
    if n:
        return n
    g = _gia(ws, i)
    if g:
        return g
    r = _so_nguyen(ws, i)
    moi = truoc in MOI_SO
    if r and i + r[1] + 1 < len(ws) and ws[i + r[1]] in ("chấm", "phẩy") and not r[3]:   # số thập phân: 12.9, 7.9, 13.6
        j = i + r[1] + 1
        r2 = _duoi_99(ws, j)
        c2 = _chuoi_chu_so(ws, j, 2) if ws[j] != "mười" else None
        if r2 and r2[1] > 1:
            return "%d.%d" % (r[0], r2[0]), r[1] + 1 + r2[1]
        if c2:
            return "%d.%s" % (r[0], c2[0]), r[1] + 1 + c2[1]
    # chữ số lẻ / đọc từng chữ số: chỉ khi có đơn vị phía sau hoặc từ mồi phía trước
    c = _chuoi_chu_so(ws, i)
    if c and (not r or not r[2]):
        j = i + c[1]
        if _khop(ws, j, DV_GB) or _khop(ws, j, DV_HZ) or _khop(ws, j, DV_PT) or moi:
            if c[1] == 1 or moi or _khop(ws, j, DV_GB):
                return c
        if c[1] >= 1 and _khop(ws, j, DV_INCH) and r and 7 <= r[0] <= 17:
            return str(r[0]), r[1]
        return None
    if not r:
        return None
    v, k, _, duoi_k = r
    if duoi_k and 10 * 1000 <= v < 1000 * 1000 and v % 1000 == 0:   # 500K, 50K (giá lẻ); "hai nghìn" -> 2000
        return "%dK" % (v // 1000), k
    return str(v), k


def _don_vi(ws, j, so):
    """Đơn vị ngay sau số -> (chữ gộp | None, chữ riêng | None, số từ)."""
    k = _khop(ws, j, DV_GB)
    if k:
        return so + DV_GB[tuple(ws[j:j + k])], None, k
    k = _khop(ws, j, DV_HZ)
    if k:
        return so + "Hz", None, k
    k = _khop(ws, j, DV_PT)
    if k:
        return so + "%", None, k
    k = _khop(ws, j, DV_INCH)
    if k:
        try:
            ok = 7 <= float(so) <= 17
        except ValueError:
            ok = False
        if ok:
            return None, "inch", k
    return None, None, 0


# ------------------------------------------------------------------ sửa chữ sau khi nghe
TIENG_DEM_LE = {"ừ", "ờ", "ừm", "ờm", "ưm", "hừ", "hử", "ơ", "à", "ạ", "hả"}


def _ghep(words, a, b, chu_moi):
    """words[a:b] -> các từ chu_moi (list). Giờ: 1 từ thì từ đầu tới cuối; nhiều từ thì chia theo độ dài chữ."""
    t0, t1 = float(words[a][1]), float(words[b - 1][2])
    du = list(words[a][3:])
    if len(chu_moi) == b - a:
        return [[c, words[a + i][1], words[a + i][2]] + list(words[a + i][3:]) for i, c in enumerate(chu_moi)]
    tong = sum(max(1, len(c)) for c in chu_moi)
    out, t = [], t0
    for c in chu_moi:
        d = (t1 - t0) * max(1, len(c)) / tong
        out.append([c, round(t, 3), round(t + d, 3)] + du)
        t += d
    out[-1][2] = round(t1, 3)
    return out


def _cum_tu(td):
    """Từ hay nói -> {khoá viết liền thường: [các từ đúng]} để viết đúng tên máy ("ipad pro" / "i pad pro" -> iPad Pro)."""
    out = {}
    for t in td.get("tu") or []:
        k = re.sub(r"\s+", "", t.lower())
        if k:
            out[k] = t.split()
    return out


def sua_tu(words, td=None):
    """[[từ, t0, t1, …]] (chữ thường máy nghe) -> danh sách mới đã sửa theo từ điển. Không đổi thứ tự / không bỏ lời.
    Từ khác đoạn nghe (cột 4) không gộp với nhau."""
    td = td if td is not None else doc()
    if not words:
        return []
    ws = [list(w) for w in words]
    # 0) tiếng "ừ / ờ" đứng lẻ loi (cách lời nói khác ≥ 0,8s): thường là tiếng thở / tiếng động máy nghe nhầm -> bỏ
    ws = [w for i, w in enumerate(ws) if not (_nfc(w[0]).lower() in TIENG_DEM_LE
          and (i == 0 or float(w[1]) - float(ws[i - 1][2]) >= 0.8) and (i == len(ws) - 1 or float(ws[i + 1][1]) - float(w[2]) >= 0.8))]
    # 1) luật "sai => đúng" của anh (cụm dài trước). Khớp theo chữ viết liền ("mark kibo" = "markibo" = "mark ki bo");
    #    chữ dài ≥ 7 ký tự được lệch 1 ký tự (máy nghe ra "markibo" / "mart kibo" thay vì "mark kibo")
    luat = [("".join(src), dst) for src, dst in td.get("sua") or []]
    out, i = [], 0
    while i < len(ws):
        for src_key, dst in luat:
            k = _khop_luat(ws, i, src_key)
            if k:
                out += _ghep(ws, i, i + k, dst.split())
                i += k
                break
        else:
            out.append(ws[i])
            i += 1
    ws = out
    # 2) viết đúng tên máy / từ của tiệm (gộp 1–3 từ viết liền)
    cum = _cum_tu(td)
    out, i = [], 0
    while i < len(ws):
        for k in (3, 2, 1):
            if i + k > len(ws) or not _cung_doan(ws, i, k):
                continue
            key = "".join(re.sub(r"\s+", "", str(x[0]).lower()) for x in ws[i:i + k])
            if key in cum and (k > 1 or True):
                out += _ghep(ws, i, i + k, cum[key])
                i += k
                break
        else:
            out.append(ws[i])
            i += 1
    ws = out
    # 3) số, giá, đơn vị, chip M
    out, i = [], 0
    low = [_nfc(x[0]).lower() for x in ws]
    while i < len(ws):
        truoc = low[i - 1] if i else ""
        if low[i] == "m" and i + 1 < len(ws) and low[i + 1] in ("một", "hai", "ba", "bốn", "năm") and _cung_doan(ws, i, 2):
            out += _ghep(ws, i, i + 2, ["M%d" % SO[low[i + 1]]])
            i += 2
            continue
        r = _so_tai(low, i, truoc)
        if r and _cung_doan(ws, i, r[1]):
            chu, k = r
            gop, rieng, kd = _don_vi(low, i + k, chu) if "TR" not in chu and not chu.endswith("K") else (None, None, 0)
            if kd and not _cung_doan(ws, i, k + kd):
                gop, rieng, kd = None, None, 0
            if gop:
                out += _ghep(ws, i, i + k + kd, [gop])
            elif rieng:
                out += _ghep(ws, i, i + k, [chu]) + _ghep(ws, i + k, i + k + kd, [rieng])
            else:
                out += _ghep(ws, i, i + k, [chu])
            i += k + kd
            continue
        out.append(ws[i])
        i += 1
    return out


def _lech(a, b, toi_da=1):
    """Khoảng cách sửa chữ (Levenshtein) a–b, dừng sớm khi > toi_da."""
    if abs(len(a) - len(b)) > toi_da:
        return toi_da + 1
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (ca != cb))
        if min(d) > toi_da:
            return toi_da + 1
    return d[-1]


def _khop_luat(ws, i, key):
    """Số từ (1–4) bắt đầu ở ws[i] mà viết liền khớp `key` của luật "sai => đúng" (0 = không khớp)."""
    s = ""
    for k in range(1, 5):
        if i + k > len(ws) or not _cung_doan(ws, i, k):
            return 0
        s += re.sub(r"\s+", "", _nfc(ws[i + k - 1][0]).lower())
        if s == key or (len(key) >= 7 and len(s) >= 7 and _lech(s, key) <= 1):
            return k
        if len(s) > len(key) + 1:
            return 0
    return 0


def _cung_doan(ws, i, k):
    """Các từ ws[i:i+k] cùng 1 đoạn nghe (cột 4 nếu có)."""
    if i + k > len(ws):
        return False
    d = [x[3] for x in ws[i:i + k] if len(x) > 3]
    return len(set(d)) <= 1


def sua_chu(chu, td=None):
    """Tiện cho thử / prompt: câu chữ -> câu đã sửa."""
    ws = [[w, i, i + 1] for i, w in enumerate(str(chu).split())]
    return " ".join(w[0] for w in sua_tu(ws, td))


def tu_cho_claude(td=None, toi_da=120):
    """Danh sách từ của tiệm (để Claude soát phụ đề biết tên máy hay nói)."""
    td = td if td is not None else doc()
    ds = list(dict.fromkeys(list(td.get("tu") or []) + [b for _, b in td.get("sua") or [] if len(b.split()) <= 2]))
    return ", ".join(ds[:toi_da])


if __name__ == "__main__":
    t = doc()
    for c in sys.argv[1:] or ["mười ba triệu chín"]:
        print(c, "->", sua_chu(c, t))
