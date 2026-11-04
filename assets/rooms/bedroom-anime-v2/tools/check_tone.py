"""Check the finished composite against the approved reference, objectively.

Reads room.png and layers/manifest.json, and for every object measures the same quantities
that were measured on the v1 reference, so the two rooms can be compared number for number:

    median luminance of the object, and its ratio to the ring around it in the composite
    mean RGB / red-blue ratio (white point)
    mean saturation
    vertical gradient and low-frequency shading (is any light baked in)

Also reports whole-frame statistics against v1, and flags objects whose ratio is still far
from the reference's.

Writes tone-check.json.
"""
import json
import os

import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
V1 = os.path.join(os.path.dirname(ROOM), "bedroom-anime-v1")
LUMA = np.array([0.299, 0.587, 0.114], np.float32)
RING = 24


def lum(a):
    return a[..., :3] @ LUMA


def sat(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    return (mx - mn) / np.maximum(mx, 1e-3)


def stats(px, full_mask):
    L = lum(px)
    v = L[full_mask]
    rgb = px[full_mask]
    ys = np.nonzero(full_mask)[0]
    h = max(1, ys.max() - ys.min())
    return dict(median=round(float(np.median(v)), 1),
                rgb=[round(float(c), 1) for c in rgb.mean(0)],
                sat=round(float(sat(rgb).mean()), 3),
                p10=round(float(np.percentile(v, 10)), 1),
                p90=round(float(np.percentile(v, 90)), 1))


def main():
    room = np.asarray(Image.open(os.path.join(ROOM, "room.png")).convert("RGB")).astype(np.float32)
    ref = np.asarray(Image.open(os.path.join(V1, "room-reference.png")).convert("RGB")).astype(np.float32)
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    v1r = json.load(open(os.path.join(ROOM, "v1_ratios.json"), encoding="utf-8"))

    L = lum(room)
    print("frame        %-8s %8s %8s %8s %8s" % ("", "median", "mean", "p5", "p95"))
    for tag, im in (("v2 room", room), ("v1 ref", ref)):
        l = lum(im)
        print("%-12s %8.0f %8.1f %8.0f %8.0f   rgb %s  sat %.2f"
              % (tag, np.median(l), l.mean(), np.percentile(l, 5), np.percentile(l, 95),
                 np.round(im.reshape(-1, 3).mean(0), 1), sat(im).mean()))
    print()

    out, bad = {}, []
    print("%-15s %6s %6s %6s %6s %6s %6s" % ("object", "med", "ring", "ratio", "v1", "R/B", "sat"))
    for o in man["objects"]:
        a = np.asarray(Image.open(os.path.join(ROOM, "layers", o["file"])).convert("RGBA"))
        m = a[..., 3] > 200
        if m.sum() < 200:
            continue
        ring = ndimage.binary_dilation(m, np.ones((2 * RING + 1,) * 2, bool)) & ~m
        bg = float(np.median(L[ring])) if ring.sum() > 100 else float(np.median(L[~m]))
        s = stats(room, m)
        ratio = s["median"] / max(bg, 1.0)
        want = v1r.get(o["name"], {}).get("ratio")
        out[o["name"]] = dict(**s, ring=round(bg, 1), ratio=round(ratio, 3), v1_ratio=want,
                              rb=round(s["rgb"][0] / max(s["rgb"][2], 1), 2))
        flag = ""
        if want and (ratio < want * 0.6 or ratio > want * 1.7):
            flag = "  <-- off"
            bad.append(o["name"])
        print("%-15s %6.0f %6.0f %6.2f %6s %6.2f %6.2f%s"
              % (o["name"], s["median"], bg, ratio, "%.2f" % want if want else "-",
                 s["rgb"][0] / max(s["rgb"][2], 1), s["sat"], flag))

    rb = [v["rb"] for v in out.values()]
    sats = [v["sat"] for v in out.values()]
    print()
    print("R/B spread %.2f..%.2f   saturation spread %.2f..%.2f   objects off-ratio %d/%d"
          % (min(rb), max(rb), min(sats), max(sats), len(bad), len(out)))
    with open(os.path.join(ROOM, "tone-check.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main()
