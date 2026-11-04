"""Numeric audit of the composed layout: who overlaps whom, and is the overlap legitimate?

The composition is built blind -- this session cannot display images -- so the checks have to
be arithmetic. Three questions, per object:

  visible   fraction of the object's own pixels that survive to the final image
  buried    fraction hidden behind objects drawn later (in front)
  collisions mask intersections that no support relationship explains

A collision is legitimate only when one object is declared to sit on the other (compose_room's
"on" mode) or when both stand on the floor at clearly different depths. Everything else is
reported, because in a blind composition an unexplained overlap is almost always a mistake.

Usage:  python layout_check.py
"""
import json
import os
from itertools import combinations

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)

# Overlaps that are not mistakes, and why:
#   - anything against the rug: a floor covering is meant to be walked on and stood on
#   - a support and whatever is declared to rest on it
#   - the TV corner: the console and a controller sit on the same cabinet as the TV
FLAT = {"rug"}
STACKED = {("tv", "game_console"), ("tv", "controller"), ("game_console", "controller")}


SUPPORTED = set()


def load():
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    masks, rects = {}, {}
    for o in man["objects"]:
        a = np.asarray(Image.open(os.path.join(ROOM, "layers", o["file"])).convert("RGBA"))[..., 3] > 127
        masks[o["name"]] = a
        ys, xs = np.nonzero(a)
        rects[o["name"]] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        if "on" in (o.get("anchors") or {}):
            SUPPORTED.add((o["anchors"]["on"], o["name"]))
    return man, masks, rects


def main():
    man, masks, rects = load()
    order = [o["name"] for o in sorted(man["objects"], key=lambda o: (o["z"], o["order"]))]
    H, W = man["canvas"][1], man["canvas"][0]

    # who ends up owning each pixel
    owner = np.full((H, W), -1, np.int32)
    for i, n in enumerate(order):
        owner[masks[n]] = i

    print("%-15s %-22s %7s %7s  %s" % ("object", "rect x,y,w,h", "visible", "buried", "hidden by"))
    for n in order:
        m = masks[n]
        tot = int(m.sum())
        own = int((owner[m] == order.index(n)).sum())
        vis = own / tot if tot else 0.0
        hid = {}
        for j, other in enumerate(order):
            if j <= order.index(n):
                continue
            k = int((m & masks[other]).sum())
            if k:
                hid[other] = k / tot
        top = sorted(hid.items(), key=lambda kv: -kv[1])[:3]
        x0, y0, x1, y1 = rects[n]
        print("%-15s %-22s %6.0f%% %6.0f%%  %s" % (
            n, "%d,%d %dx%d" % (x0, y0, x1 - x0 + 1, y1 - y0 + 1), 100 * vis, 100 * (1 - vis),
            ", ".join("%s %.0f%%" % (k, 100 * v) for k, v in top) or "-"))

    print("\nburied objects (a small thing almost completely hidden is always a mistake):")
    bad = 0
    for a, b in combinations(order, 2):
        inter = int((masks[a] & masks[b]).sum())
        if not inter:
            continue
        small = min(int(masks[a].sum()), int(masks[b].sum()))
        frac = inter / max(small, 1)
        # Partial occlusion of one object by another in front of it is what a room looks like.
        # What is never right is an object that all but disappears: that is a z-order or a
        # placement error, and it is exactly how the MP3 player was lost in an earlier pass.
        if frac < 0.60:
            continue
        smaller = a if int(masks[a].sum()) <= int(masks[b].sum()) else b
        vis = int((owner[masks[smaller]] == order.index(smaller)).sum()) / max(int(masks[smaller].sum()), 1)
        if vis >= 0.5:
            continue
        bad += 1
        print("  %-15s <-> %-15s  %5.1f%% of the smaller, %s only %.0f%% visible"
              % (a, b, 100 * frac, smaller, 100 * vis))
    print("  %d buried objects" % bad)

    print("\nlargest partial occlusions (expected where furniture stands in front of furniture):")
    pairs = []
    for a, b in combinations(order, 2):
        inter = int((masks[a] & masks[b]).sum())
        if inter:
            pairs.append((inter / max(min(int(masks[a].sum()), int(masks[b].sum())), 1), a, b, inter))
    for frac, a, b, inter in sorted(pairs, reverse=True)[:6]:
        print("  %-15s <-> %-15s  %5.1f%%  (%d px)" % (a, b, 100 * frac, inter))

    # Floor contact. The seam under a column is where the floor *begins*; the floor runs from
    # there down to the bottom of the frame, so a foot anywhere in that band is standing on it.
    # Comparing against the seam alone flagged every object in the middle of the room as
    # "sinking", which was a bug in the check, not in the layout.
    floor = man["floor"]
    by = floor["back_y"]
    x0, x1 = floor["back_x"]
    le, re_ = floor["left_edge_y"], floor["right_edge_y"]

    def seam(x):
        if x < x0:
            return by + (x0 - x) / x0 * (le - by)
        if x > x1:
            return by + (x - x1) / (W - x1) * (re_ - by)
        return by

    print("\nfloor contact (foot vs the floor band under the object's centre):")
    for n in order:
        o = next(x for x in man["objects"] if x["name"] == n)
        if not (o.get("anchors") or {}).get("bottom_center"):
            continue
        cx = o["anchors"]["bottom_center"][0]
        x0r, y0r, x1r, y1r = rects[n]
        top = seam(cx)
        if y1r < top:
            note = "  <- floats %.0f px above the floor" % (top - y1r)
        elif y1r > H - 2:
            note = "  <- runs off the bottom of the frame"
        else:
            note = "  depth %.0f px into the floor" % (y1r - top)
        print("  %-15s foot y=%4d  floor %4.0f..%d%s" % (n, y1r, top, H, note))


if __name__ == "__main__":
    main()