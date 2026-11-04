"""Measure the colour of every object in the approved v1 reference, per channel.

Brightness alone does not make a set of props look like one room. Measured on the v2 assets
the mean red/blue ratio runs from 0.43 (the monitor, cool) to 9.22 (the desk, deep orange)
against a shell at 1.17, and mean saturation runs 0.03 to 0.90. Objects generated in
isolation drift in white point; that drift is what reads as a collage.

v1 is the approved painting, so its objects define the palette. This records each object's
mean RGB and its chromaticity normalised to unit luminance, which is what a grader can match
without also dragging the object's brightness around.

Writes v1_chroma.json.
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
ALIAS = {
    "chair": "office_chair",
    "stool": "piano_bench",
    "computer_keyboard": "keyboard",
    "bedside_cabinet": "cabinet",
    "plant_floor": "plant_pot",
    "plant_left": "plant_hanging",
    "phone_black": "phone",
}


def main():
    ref = np.asarray(Image.open(REF).convert("RGB")).astype(np.float32)
    H, W = ref.shape[:2]
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
        full = np.zeros((H, W), bool)
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        full[y0:y1, x0:x1] = m[y0 - y:y1 - y, x0 - x:x1 - x]
        px = ref[full]
        mean = px.mean(0)
        L = float(mean @ LUMA)
        out[ALIAS.get(o["name"], o["name"])] = dict(
            v1_name=o["name"],
            rgb=[round(float(c), 1) for c in mean],
            lum=round(L, 1),
            chroma=[round(float(c / max(L, 1.0)), 3) for c in mean],
            pixels=int(full.sum()))
    out["__room__"] = dict(v1_name="(room)",
                           rgb=[round(float(c), 1) for c in ref.reshape(-1, 3).mean(0)],
                           lum=round(float(ref.reshape(-1, 3).mean(0) @ LUMA), 1),
                           chroma=[round(float(c / max(float(ref.reshape(-1, 3).mean(0) @ LUMA), 1.0)), 3)
                                   for c in ref.reshape(-1, 3).mean(0)],
                           pixels=int(H * W))
    with open(os.path.join(ROOM, "v1_chroma.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("%-16s %-18s %6s %6s %6s %6s" % ("v2 name", "v1 layer", "R", "G", "B", "R/B"))
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["chroma"][0] / max(kv[1]["chroma"][2], 1e-3)):
        r, g, b = v["rgb"]
        print("%-16s %-18s %6.0f %6.0f %6.0f %6.2f" % (k, v["v1_name"], r, g, b, r / max(b, 1)))


if __name__ == "__main__":
    main()
