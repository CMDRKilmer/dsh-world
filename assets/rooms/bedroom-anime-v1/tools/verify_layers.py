"""Recompose the layered room from layers/ + manifest.json and compare to the reference.

Reads only the shipped PNGs, so it validates the deliverable rather than the generator.
"""
import json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM_DIR = os.path.abspath(os.path.join(HERE, ".."))
LAYERS = os.path.join(ROOM_DIR, "layers")
REF = os.path.join(ROOM_DIR, "room-reference.png")


def verify(layers_dir=LAYERS, ref=REF):
    man = json.load(open(os.path.join(layers_dir, "manifest.json"), encoding="utf-8"))
    W, H = man["canvas"]
    src = np.array(Image.open(ref).convert("RGB"))
    if src.shape[1] != W or src.shape[0] != H:
        raise SystemExit(f"reference is {src.shape[1]}x{src.shape[0]}, manifest says {W}x{H}")
    canvas = np.zeros((H, W, 3), np.uint8)
    covered = np.zeros((H, W), bool)
    room = np.array(Image.open(os.path.join(layers_dir, "room.png")))
    m = room[..., 3] > 0
    canvas[m] = room[..., :3][m]
    covered |= m
    for o in sorted(man["objects"], key=lambda e: -e["z"]):
        a = np.array(Image.open(os.path.join(layers_dir, o["file"])))
        if a.shape[0] != o["h"] or a.shape[1] != o["w"]:
            raise SystemExit(f"{o['file']}: size {a.shape[1]}x{a.shape[0]} != manifest {o['w']}x{o['h']}")
        sub = a[..., 3] > 0
        canvas[o["y"]:o["y"] + o["h"], o["x"]:o["x"] + o["w"]][sub] = a[..., :3][sub]
        covered[o["y"]:o["y"] + o["h"], o["x"]:o["x"] + o["w"]] |= sub
    diff = np.abs(canvas.astype(int) - src.astype(int))
    out = {
        "layers": len(man["objects"]) + 1,
        "coverage": float(covered.mean()),
        "exact": bool((canvas == src).all()),
        "max_abs_diff": int(diff.max()),
        "uncovered_pixels": int((~covered).sum()),
    }
    return out


if __name__ == "__main__":
    res = verify()
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["exact"] else 1)
