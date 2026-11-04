"""Cut every generated asset out of its chroma-green backdrop.

Green screen -> alpha matte -> despill -> tight crop -> assets/<name>.png
Also writes assets/_contact-sheet.png (all cutouts on a checkerboard) for eyeballing.

Keying is global (any strongly green-dominant pixel is backdrop) and then reduced to the
largest connected object, so real see-through gaps inside an object stay transparent while
green that happens to be enclosed by the object does not survive as a green blob.

Usage:  python cutout_assets.py [--only name,name]
"""
import argparse
import json
import os
import re

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
OUT = r"D:\ComfyUI_windows_portable\ComfyUI\output"
DEST = os.path.join(ROOM, "assets")

GREEN_DOM = 24      # G - max(R,B) above this is backdrop
SOFT_LO, SOFT_HI = 8, 34   # soft matte ramp on the dominance value


def key_green(a):
    """Return (alpha 0..1, despilled rgb)."""
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    dom = G - np.maximum(R, B)
    alpha = np.clip((SOFT_HI - dom) / (SOFT_HI - SOFT_LO), 0.0, 1.0)
    # despill: pull the green channel back to the level of the other two
    excess = np.clip(G - np.maximum(R, B), 0, None)
    rgb = a.copy()
    rgb[..., 1] = np.clip(G - excess, 0, 255)
    return alpha, rgb


def object_mask(alpha):
    """Everything the green key left behind, minus keying specks.

    Thin parts of an object (a boom arm, coiled earbud wire) are separate connected
    components from its bulk, so the threshold has to be small: only specks go.
    """
    m = alpha > 0.5
    m = ndimage.binary_opening(m, np.ones((2, 2), bool))
    lab, n = ndimage.label(m)
    if n == 0:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    top = float(sizes.max())
    keep = np.zeros_like(m)
    for i, s in enumerate(sizes, start=1):
        if s >= max(top * 0.002, 250):
            keep |= (lab == i)
    return keep


def process(name):
    src = os.path.join(OUT, "aset_%s_00001_.png" % name)
    if not os.path.exists(src):
        return None
    im = Image.open(src).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    alpha, rgb = key_green(a)
    obj = object_mask(alpha)
    if not obj.any():
        return None
    alpha = np.where(obj, np.maximum(alpha, 1.0), 0.0)
    ys, xs = np.nonzero(obj)
    pad = 2
    x0, y0 = max(0, int(xs.min()) - pad), max(0, int(ys.min()) - pad)
    x1, y1 = min(a.shape[1], int(xs.max()) + 1 + pad), min(a.shape[0], int(ys.max()) + 1 + pad)
    rgba = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)[y0:y1, x0:x1]
    os.makedirs(DEST, exist_ok=True)
    dst = os.path.join(DEST, "%s.png" % name)
    Image.fromarray(rgba, "RGBA").save(dst)
    op = rgba[..., 3] > 128
    g = rgba[..., 1].astype(np.int16)
    other = np.maximum(rgba[..., 0], rgba[..., 2]).astype(np.int16)
    fringe = float(((g - other) > 12)[op].mean()) if op.any() else 0.0
    return dict(name=name, file=os.path.basename(dst), size=[int(x1 - x0), int(y1 - y0)],
                source_crop=[int(x0), int(y0), int(x1), int(y1)],
                visible=int(op.sum()), fill=round(float(op.mean()), 3),
                green_fringe=round(fringe, 4), bytes=os.path.getsize(dst))


def contact_sheet(entries, path):
    cell = 220
    cols = 6
    rows = max(1, (len(entries) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    for i, e in enumerate(entries):
        im = Image.open(os.path.join(DEST, e["file"])).convert("RGBA")
        im.thumbnail((cell - 24, cell - 40), Image.LANCZOS)
        cx, cy = (i % cols) * cell, (i // cols) * cell
        for yy in range(cy + 4, cy + cell - 22, 10):
            for xx in range(cx + 4, cx + cell - 4, 10):
                if ((xx // 10) + (yy // 10)) % 2 == 0:
                    d.rectangle([xx, yy, xx + 9, yy + 9], fill=(58, 58, 64))
        sheet.paste(im, (cx + (cell - im.width) // 2, cy + (cell - 22 - im.height) // 2), im)
        d.text((cx + 6, cy + cell - 18), e["name"], fill=(220, 220, 220))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    if args.only:
        names = [s.strip() for s in args.only.split(",") if s.strip()]
    else:
        # aset_<name>_v2_00001_.png is a regeneration of an object that was already accepted
        # into assets/ under its plain name; re-cutting it would add a duplicate asset.
        names = sorted(n for n in (f[len("aset_"):-len("_00001_.png")] for f in os.listdir(OUT)
                                   if f.startswith("aset_") and f.endswith("_00001_.png"))
                       if not re.search(r"_v\d+$", n))
    entries = []
    for n in names:
        e = process(n)
        if e is None:
            print("[skip] %s" % n)
            continue
        entries.append(e)
        print("[ok] %-15s %4dx%-4d visible=%7d fill=%.2f fringe=%.4f %6.0f KB" % (
            n, e["size"][0], e["size"][1], e["visible"], e["fill"], e["green_fringe"], e["bytes"] / 1024))
    with open(os.path.join(DEST, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"assets": entries}, f, indent=1)
    if entries:
        contact_sheet(entries, os.path.join(DEST, "_contact-sheet.png"))
    print("wrote %d assets" % len(entries))


if __name__ == "__main__":
    main()
