"""How much of the frame does each object occupy, here versus in the approved reference?

A per-object tone match can still leave a room that reads as a showroom: every object the
right brightness, all of them too small. v1's layer manifest records, for each object it
split, the number of visible pixels it occupies in the approved painting -- that is a
measurable target for how much of the frame an object of that kind should take.

Prints, per object, v1's visible pixel count, v2's, and the width multiplier that would close
the gap. Used to set TARGET_PX in compose_room.py.

Usage:  python size_report.py
"""
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
V1 = os.path.join(os.path.dirname(ROOM), "bedroom-anime-v1", "layers")
ALIAS = {
    "office_chair": "chair",
    "piano_bench": "stool",
    "keyboard": "computer_keyboard",
    "cabinet": "bedside_cabinet",
    "plant_pot": "plant_floor",
    "plant_hanging": "plant_left",
    "phone": "phone_black",
}


def main():
    v1 = {o["name"]: o for o in json.load(open(os.path.join(V1, "manifest.json"), encoding="utf-8"))["objects"]}
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    print("%-15s %10s %10s %8s %8s" % ("object", "v1 px", "v2 px", "ratio", "x-width"))
    total1 = total2 = 0
    rows = []
    for o in man["objects"]:
        a = np.asarray(Image.open(os.path.join(ROOM, "layers", o["file"])).convert("RGBA"))[..., 3] > 200
        px = int(a.sum())
        src = v1.get(ALIAS.get(o["name"], o["name"]))
        p1 = src["visible_pixels"] if src else None
        total2 += px
        if p1:
            total1 += p1
            k = (p1 / max(px, 1)) ** 0.5
            rows.append((o["name"], p1, px, k))
            print("%-15s %10d %10d %8.2f %8.2f" % (o["name"], p1, px, p1 / max(px, 1), k))
        else:
            print("%-15s %10s %10d %8s %8s" % (o["name"], "-", px, "-", "-"))
    print("\nobjects with a reference counterpart: %d   v1 total %d px   v2 total %d px   %.1f%%"
          % (len(rows), total1, total2, 100.0 * total2 / max(total1, 1)))
    print("median width multiplier needed %.2f" % float(np.median([r[3] for r in rows])))


if __name__ == "__main__":
    main()
