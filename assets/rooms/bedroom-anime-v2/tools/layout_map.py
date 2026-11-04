"""Text map of the composite: which object owns each region of the frame.

Written because this session cannot display images. Each cell of a 96x36 grid is labelled
with the object drawn topmost there, so the arrangement can be read as text: what is where,
what is in front of what, whether anything floats or is buried.

Usage:  python layout_map.py [--cols 96]
"""
import argparse
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
CODE = {
    "rug": "ru", "plant_hanging": "ph", "bookshelf": "bs", "easel": "ea", "piano": "pi",
    "bed": "bd", "cabinet": "cb", "desk": "dk", "office_chair": "ch", "piano_bench": "pb",
    "plant_pot": "pp", "basket": "bk", "side_table": "st", "monitor": "mo", "microphone": "mc",
    "desk_lamp": "dl", "keyboard": "kb", "sketchbook": "sk", "mp3_player": "mp", "mouse": "ms",
    "mug": "mg", "phone": "pn", "tv": "tv", "game_console": "gc", "controller": "ct",
    "easel_painting": "ep", "cat": "ct2", "rice_cooker": "rc",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cols", type=int, default=96)
    args = ap.parse_args()

    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    W, H = man["canvas"]
    owner = np.full((H, W), "", dtype=object)
    owner[:] = "  "
    for o in sorted(man["objects"], key=lambda o: (o["z"], o["order"])):
        a = np.asarray(Image.open(os.path.join(ROOM, "layers", o["file"])).convert("RGBA"))[..., 3] > 127
        owner[a] = CODE.get(o["name"], o["name"][:2])

    rows = max(1, args.cols * H // W // 2)
    print("canvas %dx%d -> %d cols x %d rows (each row = 2 text rows)\n" % (W, H, args.cols, rows))
    for r in range(rows):
        y0, y1 = r * H // rows, (r + 1) * H // rows
        line = []
        for c in range(args.cols):
            x0, x1 = c * W // args.cols, (c + 1) * W // args.cols
            block = owner[y0:y1, x0:x1].ravel()
            vals, counts = np.unique(block, return_counts=True)
            k = int(np.argmax(counts))
            line.append(vals[k] if counts[k] >= 0.35 * len(block) else "..")
        print("%3d " % y0 + "".join(line))
    print()
    print("legend: " + "  ".join("%s=%s" % (v, k) for k, v in sorted(CODE.items(), key=lambda kv: kv[1])))


if __name__ == "__main__":
    main()
