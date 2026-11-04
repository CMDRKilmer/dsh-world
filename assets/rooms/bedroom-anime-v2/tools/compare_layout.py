"""Compare the composite's layout against the approved reference, region by region.

Numbers so far only checked per-object tone. They say nothing about whether the room *reads*
like the reference: the reference has furniture packed across the back wall and both side
walls, and a composite can hit every tone target while still looking like a showroom.

This rasterises both rooms' object coverage onto a coarse grid (12 x 6 cells) and reports the
fraction of each cell covered, plus a text map. Where the composite is much emptier than the
reference is where furniture still needs to be added or enlarged.

Usage:  python compare_layout.py
"""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
V1 = os.path.join(os.path.dirname(ROOM), "bedroom-anime-v1")
COLS, ROWS = 12, 6


def v1_coverage(W, H):
    man = json.load(open(os.path.join(V1, "layers", "manifest.json"), encoding="utf-8"))
    cov = np.zeros((H, W), bool)
    for o in man["objects"]:
        p = os.path.join(V1, "layers", o["file"])
        if not os.path.exists(p):
            continue
        a = np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 200
        x, y = int(o["x"]), int(o["y"])
        h, w = a.shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        cov[y0:y1, x0:x1] |= a[y0 - y:y1 - y, x0 - x:x1 - x]
    return cov


def v2_coverage(W, H):
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    cov = np.zeros((H, W), bool)
    for o in man["objects"]:
        a = np.asarray(Image.open(os.path.join(ROOM, "layers", o["file"])).convert("RGBA"))[..., 3] > 200
        cov |= a
    return cov


def grid(cov):
    H, W = cov.shape
    g = np.zeros((ROWS, COLS))
    for r in range(ROWS):
        for c in range(COLS):
            cell = cov[r * H // ROWS:(r + 1) * H // ROWS, c * W // COLS:(c + 1) * W // COLS]
            g[r, c] = cell.mean()
    return g


def main():
    W, H = 1536, 864
    a, b = v1_coverage(W, H), v2_coverage(W, H)
    print("overall object coverage   v1 %.1f%%   v2 %.1f%%" % (100 * a.mean(), 100 * b.mean()))
    ga, gb = grid(a), grid(b)
    chars = " .:-=+*#%@"
    for tag, g in (("v1 reference", ga), ("v2 composite", gb)):
        print("\n%s" % tag)
        for r in range(ROWS):
            print("  " + " ".join(chars[min(9, int(v * 10))] for v in g[r]))
    print("\ndelta (v2 - v1), in coverage points; negative = emptier than the reference")
    for r in range(ROWS):
        print("  " + " ".join("%+4.0f" % (100 * (gb[r, c] - ga[r, c])) for c in range(COLS)))
    deficit = [(r, c, 100 * (ga[r, c] - gb[r, c])) for r in range(ROWS) for c in range(COLS)]
    deficit.sort(key=lambda t: -t[2])
    print("\nemptiest cells vs reference:")
    for r, c, d in deficit[:6]:
        y0, y1 = r * H // ROWS, (r + 1) * H // ROWS
        x0, x1 = c * W // COLS, (c + 1) * W // COLS
        print("  cell r%d c%d  x %4d-%4d  y %3d-%3d   v1 %4.0f%%  v2 %4.0f%%  deficit %4.0f pts"
              % (r, c, x0, x1, y0, y1, 100 * ga[r, c], 100 * gb[r, c], d))
    print("\nmean absolute cell difference %.1f points" % (100 * np.abs(ga - gb).mean()))


if __name__ == "__main__":
    main()
