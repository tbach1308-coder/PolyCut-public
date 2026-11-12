#!/usr/bin/env python3
"""So đường cong JS (dev/_mod-chuyen-moi.js › cssChuyen) với Python (engine/chuyen_moi.py) trên 41 điểm p của mọi khoá, 15 kiểu. In ĐẠT / HỎNG."""
import json, os, subprocess, sys
D = os.path.dirname(os.path.abspath(__file__))
G = os.path.abspath(os.path.join(D, "..", "..", ".."))
sys.path.insert(0, os.path.join(G, "engine"))
import chuyen_moi as CM  # noqa: E402
kho = os.path.join(G, "engine", "chuyen-canh")
js = json.loads(subprocess.run(["node", os.path.join(D, "thu_xem_chuyen_moi.js"), kho], capture_output=True, text=True, check=True).stdout)
sai = 0
for id_, ks in js.items():
    s = CM.doc_spec(id_)
    for k, vals in ks.items():
        if k == "nguong":
            tr = s["nguong"]
        elif k.startswith("lop"):
            tr = s["lop"][int(k[3:k.index(".")])]["manh"]
        else:
            side, kk = k.split(".")
            tr = s[side][kk]
        for i, v in enumerate(vals):
            py = CM.gia_tri(tr, i / 40, 0.0)
            if abs(py - v) > 1e-5:
                sai += 1
                print("lệch", id_, k, i / 40, py, v)
print("ĐẠT" if not sai else f"HỎNG {sai}", f"({len(js)} kiểu, {sum(len(v) for v in js.values())} đường cong x 41 điểm)")
