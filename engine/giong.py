# -*- coding: utf-8 -*-
"""Giọng đọc AI tiếng Việt cho video dựng bằng app Poly Dựng Video. 2 nguồn giọng (danh sách: giong-ds.json):
  - VieNeu-TTS v3 Turbo: 25 giọng (Adam, Adam bựa, Hải Đăng, Mai Anh…), chạy NGAY TRÊN MÁY (CPU, ONNX), không cần mạng sau
    khi CAI-DAT.bat tải model vào engine/giong-vieneu (~540 MB). Dùng thương mại được (Apache-2.0). KHÔNG có watermark: VieNeu
    chỉ gắn watermark khi cài gói resemble-perth (kéo theo PyTorch), máy tiệm không cài (r39, 11/11).
    id "vn-<tên không dấu>", vd vn-adam. Không có mốc từng chữ -> phụ đề chia đều theo chữ trong câu.
  - Microsoft (edge-tts, cần mạng): nu = Hoài My, nam = Nam Minh (giống tool Poly Video), có mốc từng chữ.

Tạo giọng cho cả video (mỗi dòng trong file lời đọc = 1 câu):
  python giong.py "<W>/loi-doc.txt" "<W>/giong" --giong vn-adam --toc-do +10% [--phong loa]
  -> <W>/giong/giong-doc.wav (48 kHz mono, -14 LUFS), 2-phu-de.srt (cụm 1–4 chữ), giong.json
     In ra 1 dòng JSON: {"wav", "srt", "giay", "so_cau", "giong"} (+ "phong" khi có --phong)
Nghe thử (app gọi khi anh bấm "Nghe thử"):
  python giong.py --thu "<câu>" "<file.mp3>" --giong vn-adam --toc-do +10% [--phong loa]
--phong (r39, 11/11 "giọng đọc AI trend"): phong cách xử lý sau (phong_giong.py: ro, tram, ngot, genz, loa, radio, robot,
chipmunk) áp lên cả giọng SAU khâu chuẩn âm lượng, giữ đúng số mẫu -> mốc câu / chữ / phụ đề không đổi. Không có --phong hoặc
"goc": không gọi phong_giong, ra y hệt bản cũ.

Cắt im đầu/cuối câu, nghỉ 0,25 s giữa câu (như tool Poly Video). Không ghi gì vào thư mục clip của anh.
"""
import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
import wave

import chung

chung.dat_utf8()

GIONG = {"nu": "vi-VN-HoaiMyNeural", "nam": "vi-VN-NamMinhNeural"}
HERE = os.path.dirname(os.path.abspath(__file__))
VIENEU_DIR = os.environ.get("POLY_VIENEU_DIR") or os.path.join(HERE, "giong-vieneu")


def ds_vieneu():
    try:
        with open(os.path.join(HERE, "giong-ds.json"), encoding="utf-8") as f:
            return {x["id"]: x["ten"] for x in json.load(f).get("vieneu", [])}
    except (OSError, ValueError, KeyError):
        return {}


_TTS = {}


def nap_vieneu():
    """VieNeu v3 Turbo từ thư mục model thường (onnxruntime chặn đọc dữ liệu ngoài qua symlink cache HF), không lên mạng."""
    if "v" in _TTS:
        return _TTS["v"]
    v3, codec = os.path.join(VIENEU_DIR, "v3", "onnx_update"), os.path.join(VIENEU_DIR, "codec")
    if not os.path.isfile(os.path.join(codec, "moss_audio_tokenizer_decode_full.onnx")) or not os.path.isfile(os.path.join(v3, "tokenizer.json")):
        raise SystemExit("LOI=Chưa có giọng VieNeu trên máy: anh chạy lại CAI-DAT.bat (cần mạng, tải ~540 MB 1 lần)")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    try:
        try:
            import onnxruntime
            onnxruntime.disable_telemetry_events()
        except Exception:   # noqa: BLE001 - bản không có hàm này
            pass
        from vieneu._v3_turbo_engine import onnx_runtime_lite as m
        goc_init = m.OnnxV3LiteEngine.__init__

        def init(self, *a, **kw):   # thư viện không chuyển codec_dir xuống engine -> chèn vào
            kw.setdefault("codec_dir", codec)
            kw["onnx_dir"] = kw.get("onnx_dir") or v3
            goc_init(self, *a, **kw)
        m.OnnxV3LiteEngine.__init__ = init
        from vieneu import Vieneu
        _TTS["v"] = Vieneu(onnx_dir=v3, threads=0)
    except ImportError as e:
        raise SystemExit("LOI=Bộ dựng chưa có thư viện giọng VieNeu: anh chạy lại CAI-DAT.bat (%s)" % e)
    return _TTS["v"]


def doc_cau_vieneu(text, ten, out_wav):
    import numpy as np
    w = nap_vieneu().infer(text, voice=ten)
    if not len(w):
        raise SystemExit("LOI=Giọng VieNeu không đọc được câu: " + text[:60])
    a = (np.clip(np.asarray(w, dtype=np.float32), -1, 1) * 32767).astype(np.int16)
    ghi_wav(out_wav, a)
    return []   # không có mốc từng chữ
SR = 48000
NGHI_GIUA_CAU = 0.25
DUOI_VIDEO = 0.8
CHU_MOI_CUM = 4


def toc_do(r):
    """'+10%', '10', '-5 %' -> '+10%' / '-5%' (edge-tts chỉ nhận số nguyên, -50..+100)."""
    m = re.fullmatch(r"([+-]?)(\d{1,3}(?:[.,]\d+)?)%?", (r or "+0%").strip().replace(" ", ""))
    if not m:
        return "+0%"
    v = max(-50, min(100, int(round(float(m.group(2).replace(",", "."))))))
    return ("-" if m.group(1) == "-" and v else "+") + str(v) + "%"


async def _doc(text, voice, rate, out):
    import edge_tts
    try:
        com = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    except TypeError:   # edge-tts cũ
        com = edge_tts.Communicate(text, voice, rate=rate)
    tu = []
    with open(out, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                tu.append([ch["offset"] / 1e7, ch["text"]])
    return tu


def doc_cau(text, voice, rate, out):
    """1 câu -> mp3 + mốc từng chữ. Lỗi mạng thử 3 lần."""
    loi = None
    for lan in range(3):
        try:
            tu = asyncio.run(_doc(text, voice, rate, out))
            if os.path.getsize(out) < 500:
                raise RuntimeError("âm thanh rỗng")
            return tu
        except ValueError as e:   # edge-tts từ chối giọng / tốc độ
            raise SystemExit("LOI=Giọng đọc không nhận cài đặt %s %s: %s" % (voice, rate, e))
        except Exception as e:   # noqa: BLE001 - mạng chập chờn
            loi = e
            time.sleep(2 * (lan + 1))
    raise SystemExit("LOI=Không tạo được giọng đọc AI (cần mạng tới dịch vụ giọng Microsoft): %s" % loi)


def giai_ma(p, tempo=None):
    import numpy as np
    af = ["-af", "atempo=%.3f" % tempo] if tempo and abs(tempo - 1) > 0.005 else []
    r = subprocess.run([chung.FFMPEG, "-v", "error", "-i", p] + af + ["-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        raise SystemExit("LOI=Không đọc được file giọng vừa tạo: " + os.path.basename(p))
    return np.frombuffer(r.stdout, np.int16).copy()


def cat_im(a):
    """Cắt im đầu/cuối câu, chừa phụ âm nhẹ; trả (âm, giây đã cắt ở đầu)."""
    import numpy as np
    x = np.abs(a.astype(np.int32))
    if not len(x):
        return a, 0.0
    nguong = max(150, int(x.max() * 0.01))
    idx = np.where(x > nguong)[0]
    if not len(idx):
        return a, 0.0
    s = max(0, idx[0] - int(0.06 * SR))
    e = min(len(a), idx[-1] + int(0.12 * SR))
    out = a[s:e].astype(np.float32)
    f = min(len(out) // 4, int(0.005 * SR))
    if f > 1:
        ramp = np.linspace(0, 1, f, dtype=np.float32)
        out[:f] *= ramp
        out[-f:] *= ramp[::-1]
    return out.astype(np.int16), s / SR


def ghi_wav(p, a):
    with wave.open(p, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(a.tobytes())


def gio_srt(t):
    ms = int(round(max(0.0, t) * 1000))
    return "%02d:%02d:%02d,%03d" % (ms // 3600000, ms // 60000 % 60, ms // 1000 % 60, ms % 1000)


def doc_loi(p):
    with open(p, "rb") as f:
        b = f.read()
    t = b.decode("utf-16") if b[:2] in (b"\xff\xfe", b"\xfe\xff") else b.decode("utf-8-sig", errors="replace")
    import unicodedata
    cau = [unicodedata.normalize("NFC", x).strip() for x in t.splitlines()]
    return [x for x in cau if x and not x.startswith("#")]


def ap_phong(wav, phong):
    """Áp phong cách lên file wav tại chỗ, giữ đúng số mẫu (phong_giong.py). phong rỗng / "goc": không làm gì."""
    if not phong or phong == "goc":
        return
    import phong_giong
    tam = wav[:-4] + "-phong.wav"
    phong_giong.ap(wav, tam, phong, giu_mau=True)
    os.replace(tam, wav)


def tao(loi_p, ra, giong, rate, phong=None):
    import numpy as np
    cau = doc_loi(loi_p)
    if not cau:
        raise SystemExit("LOI=File lời đọc trống: " + loi_p)
    vn = ds_vieneu()
    voice = vn.get(giong) or GIONG.get(giong, giong)
    la_vn = giong in vn
    tempo = 1 + int(rate.rstrip("%")) / 100 if la_vn else None   # VieNeu không có tốc độ: kéo nhanh / chậm bằng atempo
    os.makedirs(ra, exist_ok=True)
    tam = os.path.join(ra, "_cau")
    os.makedirs(tam, exist_ok=True)
    phan, tu_all, t, ds = [], [], 0.0, []
    for i, c in enumerate(cau):
        if la_vn:
            mp3 = os.path.join(tam, "cau-%02d.wav" % (i + 1))
            tu = doc_cau_vieneu(c, voice, mp3)
        else:
            mp3 = os.path.join(tam, "cau-%02d.mp3" % (i + 1))
            tu = doc_cau(c, voice, rate, mp3)
        a, dau = cat_im(giai_ma(mp3, tempo))
        dai = len(a) / SR
        for t0, w in tu:
            if t0 - dau > -0.05:
                tu_all.append([round(t + max(0.0, t0 - dau), 3), w, i])
        nghi = DUOI_VIDEO if i == len(cau) - 1 else NGHI_GIUA_CAU
        ds.append({"cau": c, "tu": round(t, 3), "den": round(t + dai, 3)})
        phan += [a, np.zeros(int(round(nghi * SR)), np.int16)]
        t += dai + nghi
    tho = os.path.join(tam, "giong-tho.wav")
    ghi_wav(tho, np.concatenate(phan))
    wav = os.path.join(ra, "giong-doc.wav")
    r = subprocess.run([chung.FFMPEG, "-v", "error", "-y", "-i", tho, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                        "-ar", str(SR), "-ac", "1", wav], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit("LOI=Không chuẩn âm lượng giọng được: " + r.stderr[-300:])
    ap_phong(wav, phong)
    # phụ đề: cụm 1–4 chữ trong cùng 1 câu, hết cụm ở dấu câu; câu không có mốc chữ thì chia đều
    cum = []
    for i, d in enumerate(ds):
        tu = [x for x in tu_all if x[2] == i]
        if not tu:
            w = d["cau"].split()
            buoc = (d["den"] - d["tu"]) / max(1, len(w))
            tu = [[d["tu"] + k * buoc, x, i] for k, x in enumerate(w)]
        cur = []
        for k, x in enumerate(tu):
            cur.append(x)
            if len(cur) >= CHU_MOI_CUM or re.search(r"[,.;:!?…]$", x[1]) or k == len(tu) - 1:
                het = tu[k + 1][0] if k + 1 < len(tu) else d["den"]
                cum.append({"tu": cur[0][0], "den": round(het, 3), "chu": " ".join(y[1] for y in cur)})
                cur = []
    srt = os.path.join(ra, "2-phu-de.srt")
    with open(srt, "w", encoding="utf-8") as f:
        for n, c in enumerate(cum):
            f.write("%d\n%s --> %s\n%s\n\n" % (n + 1, gio_srt(c["tu"]), gio_srt(c["den"]), c["chu"]))
    kq = {"wav": chung.xuoi(wav), "srt": chung.xuoi(srt), "giay": round(t, 2), "so_cau": len(cau), "giong": voice, "toc_do": rate}
    if phong and phong != "goc":
        kq["phong"] = phong
    with open(os.path.join(ra, "giong.json"), "w", encoding="utf-8") as f:
        json.dump(dict(kq, cau=ds, chu=[{"t": x[0], "chu": x[1], "cau": x[2]} for x in tu_all]), f, ensure_ascii=False, indent=1)
    return kq


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vao", nargs="?", help="file lời đọc (1 câu 1 dòng)")
    ap.add_argument("ra", nargs="?", help="thư mục ra")
    ap.add_argument("--giong", default="vn-adam", help="vn-<tên> (VieNeu, xem giong-ds.json) | nu | nam | tên giọng Microsoft")
    ap.add_argument("--toc-do", default="+10%")
    ap.add_argument("--thu", nargs=2, metavar=("CAU", "MP3"), help="nghe thử 1 câu")
    ap.add_argument("--phong", help="phong cách xử lý sau (phong_giong.py), vd loa; bỏ trống / goc = như cũ")
    av, i = [], 1   # r39: "--toc-do -5%" (nút Chậm) bị argparse hiểu "-5%" là 1 tuỳ chọn -> lỗi; gộp thành "--toc-do=-5%"
    while i < len(sys.argv):
        if sys.argv[i] == "--toc-do" and i + 1 < len(sys.argv) and sys.argv[i + 1].startswith("-"):
            av.append("--toc-do=" + sys.argv[i + 1])
            i += 2
        else:
            av.append(sys.argv[i])
            i += 1
    a = ap.parse_args(av)
    rate = toc_do(a.toc_do)
    phong = a.phong if a.phong and a.phong != "goc" else None
    if phong:
        import phong_giong
        if not phong_giong.co(phong):
            raise SystemExit("LOI=Không có phong cách giọng: " + phong)
    if a.thu:
        vn = ds_vieneu()
        if a.giong in vn:
            voice = vn[a.giong]
            tam = a.thu[1] + ".wav"
            doc_cau_vieneu(a.thu[0], voice, tam)
            tempo = 1 + int(rate.rstrip("%")) / 100
            ra_thu = tam[:-4] + "-toc.wav" if phong else a.thu[1]
            r = subprocess.run([chung.FFMPEG, "-v", "error", "-y", "-i", tam] + (["-af", "atempo=%.3f" % tempo] if abs(tempo - 1) > 0.005 else [])
                               + ["-ac", "1"] + (["-ar", str(SR)] if phong else ["-b:a", "160k"]) + [ra_thu], capture_output=True)
            try:
                os.remove(tam)
            except OSError:
                pass
            if r.returncode:
                raise SystemExit("LOI=Không ghi được file nghe thử")
        else:
            voice = GIONG.get(a.giong, a.giong)
            ra_thu = a.thu[1] + ".goc.mp3" if phong else a.thu[1]
            doc_cau(a.thu[0], voice, rate, ra_thu)
        if phong:   # nghe thử có phong cách: áp lên bản đã đổi tốc độ rồi ghi mp3
            import phong_giong
            try:
                phong_giong.ap(ra_thu, a.thu[1], phong)
            finally:
                try:
                    os.remove(ra_thu)
                except OSError:
                    pass
        out = {"mp3": chung.xuoi(a.thu[1]), "giong": voice, "toc_do": rate}
        if phong:
            out["phong"] = phong
        print(json.dumps(out, ensure_ascii=False))
        return
    if not a.vao or not a.ra:
        ap.error("cần file lời đọc và thư mục ra")
    print(json.dumps(tao(a.vao, a.ra, a.giong, rate, phong), ensure_ascii=False))


if __name__ == "__main__":
    main()
