"""Derive, from the approved v1 painting, how bright each object should be relative to the
surface behind it -- then use that as the grading target for the v2 assets.

v2's assets were each generated alone under studio light, so every one carries its own
arbitrary exposure: a bookshelf lands at 0.44x the luminance of the wall behind it while a
rice cooker lands at 1.19x. That spread is what makes the assembled room read as a collage.

v1 (bedroom-anime-v1) is the painting the user approved, so its objects already sit at
believable levels against their surroundings. For each v1 object this script measures

    ratio = median luminance of the object / median luminance of the ring around it

where the ring is the object's bounding box dilated by 40 px with the object itself masked
out -- i.e. the wall, floor or neighbouring surface it is actually seen against. The ratio
is what carries over between the two rooms, not the absolute level, because v1 is an
evening interior and v2's shell is a bright daytime one.

Writes v1_ratios.json.
"""
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
V1 = os.path.join(os.path.dirname(ROOM), "bedroom-anime-v1")
REF = os.path.join(V1, "room-reference.png")
LAYERS = os.path.join(V1, "layers")
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
RING_PX = 40

# v1 layer name -> v2 asset name, where they differ
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
        full = np.zeros((H, W), bool)
        x0, y0, x1, y1 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
        full[y0:y1, x0:x1] = m[y0 - y:y1 - y, x0 - x:x1 - x]
        ring = ndimage.binary_dilation(full, np.ones((2 * RING_PX + 1, 2 * RING_PX + 1), bool)) & ~ndimage.binary_dilation(full, np.ones((3, 3), bool))
        ring &= ~full
        if ring.sum() < 200:
            continue
        obj = float(np.median(L[full]))
        bg = float(np.median(L[ring]))
        out[ALIAS.get(o["name"], o["name"])] = dict(
            v1_name=o["name"], obj=round(obj, 1), bg=round(bg, 1),
            ratio=round(obj / max(bg, 1.0), 3), pixels=int(full.sum()))
    with open(os.path.join(ROOM, "v1_ratios.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print("%-16s %-18s %6s %6s %6s" % ("v2 name", "v1 layer", "obj", "bg", "ratio"))
    for k, v in sorted(out.items(), key=lambda kv: kv[1]["ratio"]):
        print("%-16s %-18s %6.0f %6.0f %6.2f" % (k, v["v1_name"], v["obj"], v["bg"], v["ratio"]))
    print("\n%d objects, ratio spread %.2f .. %.2f"
          % (len(out), min(v["ratio"] for v in out.values()), max(v["ratio"] for v in out.values())))


if __name__ == "__main__":
    main()
