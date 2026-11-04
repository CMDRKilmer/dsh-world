"""Measure the tonal level of every object in the approved v1 reference.

v1 (bedroom-anime-v1) is the painting the user approved as the standard look. Its layers are
cropped RGBA cut-outs positioned by layers/manifest.json, so masking the reference with each
layer (at its manifest offset) gives the luminance that object *should* have in the finished
room -- baked light and all.

That is the oracle for grading the v2 assets: they were generated in isolation, so each one
carries its own arbitrary exposure. Matching each asset's median to the reference's median
for the same object restores a single exposure basis without inventing a look.

Writes v1_targets.json.
"""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
V1 = os.path.join(os.path.dirname(ROOM), "bedroom-anime-v1")
REF = os.path.join(V1, "room-reference.png")
LAYERS = os.path.join(V1, "layers")
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def main():
    ref = np.asarray(Image.open(REF).convert("RGB")).astype(np.float32)
    H, W = ref.shape[:2]
    L = ref @ LUMA
    man = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
    out = {}
    for o in man["objects"]:
        path = os.path.join(LAYERS, o["file"])
        if not os.path.exists(path):
            continue
        a = np.asarray(Image.open(path).convert("RGBA"))
        m = a[..., 3] > 200
        if m.sum() < 400:
            continue
        x, y = int(o["x"]), int(o["y"])
        h, w = m.shape
        sub = np.zeros((H, W), bool)
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        sub[y0:y1, x0:x1] = m[y0 - y:y1 - y, x0 - x:x1 - x]
        v = L[sub]
        out[o["name"]] = dict(
            pixels=int(sub.sum()),
            p10=round(float(np.percentile(v, 10)), 1),
            median=round(float(np.median(v)), 1),
            p90=round(float(np.percentile(v, 90)), 1),
            mean=round(float(v.mean()), 1),
        )
    out["__room__"] = dict(pixels=int(L.size), p10=round(float(np.percentile(L, 10)), 1),
                           median=round(float(np.median(L)), 1),
                           p90=round(float(np.percentile(L, 90)), 1),
                           mean=round(float(L.mean()), 1))
    with open(os.path.join(ROOM, "v1_targets.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("%-20s %8s %6s %6s %6s" % ("v1 object", "px", "p10", "med", "p90"))
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["median"]):
        print("%-20s %8d %6.0f %6.0f %6.0f" % (k, v["pixels"], v["p10"], v["median"], v["p90"]))


if __name__ == "__main__":
    main()
