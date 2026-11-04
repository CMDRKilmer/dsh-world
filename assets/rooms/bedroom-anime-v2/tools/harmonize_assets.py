"""Grade the cut-out assets so their exposure matches the room they are placed in.

The assets were generated in isolation under neutral studio light, the room shell was
generated as a bright beige interior. Placed as-is, a desk reads at 0.40x the luminance of
the wall behind it, a bookshelf at 0.44x, an office chair at 0.37x -- the furniture looks
like it was photographed in a different, much darker room.

This is a grading step, not a lighting step: a single monotonic curve is applied to every
asset's RGB so dark materials lift toward the room's exposure while light materials are
left almost untouched. Relative material differences inside an object survive (a black
piano stays the darkest thing in the room), and no shadow, highlight or directional term is
introduced, so global illumination can still be added later.

    L' = 255 * (L / 255) ** GAMMA

Writes assets_graded/<name>.png; assets/ keeps the untouched cut-outs.

Usage:  python harmonize_assets.py [--gamma 0.8]
"""
import argparse
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
SRC = os.path.join(ROOM, "assets")
DST = os.path.join(ROOM, "assets_graded")
SHELL = r"D:\ComfyUI_windows_portable\ComfyUI\output\shell_wide_00001_.png"
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def grade(rgb, gamma):
    return np.clip(255.0 * (np.clip(rgb, 0, 255) / 255.0) ** gamma, 0, 255)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gamma", type=float, default=0.8)
    args = ap.parse_args()

    os.makedirs(DST, exist_ok=True)
    shell = np.asarray(Image.open(SHELL).convert("RGB")).astype(np.float32)
    room_lum = float((shell @ LUMA).mean())

    rows = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".png") or f.startswith("_"):
            continue
        im = Image.open(os.path.join(SRC, f)).convert("RGBA")
        a = np.asarray(im).astype(np.float32)
        op = a[..., 3] > 128
        if not op.any():
            continue
        before = float((a[..., :3][op] @ LUMA).mean())
        a[..., :3] = grade(a[..., :3], args.gamma)
        after = float((a[..., :3][op] @ LUMA).mean())
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(DST, f))
        rows.append(dict(name=f[:-4], lum_before=round(before, 1), lum_after=round(after, 1),
                         ratio_before=round(before / room_lum, 3),
                         ratio_after=round(after / room_lum, 3)))

    rows.sort(key=lambda r: r["ratio_before"])
    print("room mean luminance %.1f, gamma %.2f" % (room_lum, args.gamma))
    for r in rows:
        print("  %-15s %6.1f -> %6.1f   ratio %.2f -> %.2f" % (
            r["name"], r["lum_before"], r["lum_after"], r["ratio_before"], r["ratio_after"]))
    spread_before = max(r["ratio_before"] for r in rows) - min(r["ratio_before"] for r in rows)
    spread_after = max(r["ratio_after"] for r in rows) - min(r["ratio_after"] for r in rows)
    print("\nspread of object/room luminance ratio: %.2f -> %.2f" % (spread_before, spread_after))
    with open(os.path.join(DST, "grade.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(gamma=args.gamma, room_lum=round(room_lum, 1), assets=rows), fh, indent=1)


if __name__ == "__main__":
    main()
