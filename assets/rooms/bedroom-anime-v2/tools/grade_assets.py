"""Grade the cut-out assets so the assembled room reads as one exposure and one palette.

Each asset was generated alone under neutral studio light, so every one carries its own
arbitrary exposure and white point. Measured against the room shell before grading:

    luminance spread   0.09x (the TV) .. 1.03x (handheld console) of the surface behind it
    red/blue spread    0.43 (monitor) .. 9.22 (desk)  against a shell at 1.17
    saturation spread  0.03 .. 0.90

An 11x brightness range inside one interior is what makes the composite read as a collage.

Brightness
----------
Targets come from the approved v1 painting, but not as raw ratios: v1 is an evening interior
whose walls are dark, so "object is 1.34x its surroundings" cannot be transplanted onto a
daytime shell (it asks for a 288-luminance desk on a 216 wall and clips). What transfers is
the *ordering and spacing of material values*, so v1's per-object median is normalised by
the brightest object in that painting (the sketchbook, 210) and mapped onto a band anchored
to the shell's own median:

    target_i = shell_median * (0.40 + 0.60 * v1_median_i / 210)

A black TV therefore lands near 100 rather than 13, the wooden desk near 140, paper near the
wall's own value. Furniture stays darker than the walls, which is what a bright room looks
like, and nothing clips.

Colour
------
Saturation is compressed halfway toward the median of the asset set (an over-saturated orange
desk and a washed-out grey console both move toward the middle), and a small warm shift pulls
the whole set toward the shell's tint. Hue is preserved, so a blue monitor stays blue.

Each object is graded with one monotone tone curve, solved by bisection:

    L' = 255 * (L / 255) ** gamma

so material relationships inside an object survive and no shadow, highlight or direction term
is invented -- global illumination can still be added later.

    python grade_assets.py [--warm 0.03] [--sat-pull 0.5]

The gamma search runs to 24 because a flat, near-white asset (the handheld console at 234)
has to come down to about 120, which needs an exponent near 9 -- the first version capped at
6 and left three objects 30% too bright.

Writes assets_graded/<name>.png and grade.json. assets/ is left untouched.
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
# the plate the room is actually built on; grade_shell.py writes it, and grading against the
# graded plate keeps the objects' targets consistent with the wall they end up against
SHELL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shell_graded.png")
LUMA = np.array([0.299, 0.587, 0.114], np.float32)

# v1 layer name -> v2 asset name, where the two differ
ALIAS = {
    "office_chair": "chair",
    "piano_bench": "stool",
    "keyboard": "computer_keyboard",
    "cabinet": "bedside_cabinet",
    "plant_pot": "plant_floor",
    "plant_hanging": "plant_left",
    "phone": "phone_black",
}
# no counterpart in the v1 painting: use the median v1 object value as a neutral placeholder
NO_COUNTERPART = {"mouse", "controller", "basket", "side_table"}
BAND_FLOOR, BAND_TOP = 0.40, 1.00


def lum(a):
    return a[..., :3] @ LUMA


def saturation(rgb):
    mx, mn = rgb.max(-1), rgb.min(-1)
    return (mx - mn) / np.maximum(mx, 1e-3)


def solve_gamma(v, target, lo=0.15, hi=24.0):
    """Bisect the tone-curve exponent so the median of v lands on target."""
    for _ in range(64):
        mid = 0.5 * (lo + hi)
        if float(np.median(255.0 * (v / 255.0) ** mid)) > target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--warm", type=float, default=0.03,
                    help="fractional warm shift toward the shell's tint (0 disables)")
    ap.add_argument("--sat-pull", type=float, default=0.5,
                    help="0 leaves saturation alone, 1 pulls every asset to the set median")
    args = ap.parse_args()

    targets = json.load(open(os.path.join(ROOM, "v1_targets.json"), encoding="utf-8"))
    shell = np.asarray(Image.open(SHELL).convert("RGB")).astype(np.float32)
    shell_med = float(np.median(lum(shell)))

    names = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith(".png") and not f.startswith("_"))
    imgs, stats = {}, {}
    for n in names:
        a = np.asarray(Image.open(os.path.join(SRC, n + ".png")).convert("RGBA")).astype(np.float32)
        imgs[n] = a
        m = a[..., 3] > 200
        stats[n] = dict(m=m, med=float(np.median(lum(a)[m])), sat=float(saturation(a[..., :3])[m].mean()))

    # v1 reference value per asset: its counterpart's median, or the median object value
    v1_med = {k: v["median"] for k, v in targets.items() if k != "__room__"}
    top = max(v1_med.values())
    mid = float(np.median(list(v1_med.values())))
    ref = {}
    for n in names:
        key = ALIAS.get(n, n)
        ref[n] = mid if n in NO_COUNTERPART or key not in v1_med else v1_med[key]

    sat_med = float(np.median([stats[n]["sat"] for n in names]))
    os.makedirs(DST, exist_ok=True)
    rows = []
    for n in names:
        a = imgs[n].copy()
        m = stats[n]["m"]
        target = shell_med * (BAND_FLOOR + (BAND_TOP - BAND_FLOOR) * min(ref[n] / top, 1.0))

        g = solve_gamma(lum(a)[m], target)
        a[..., :3] = np.clip(255.0 * (np.clip(a[..., :3], 0, 255) / 255.0) ** g, 0, 255)

        # saturation: move halfway toward the set's median saturation, hue untouched
        rgb = a[..., :3]
        s = saturation(rgb)
        want = sat_med + (s - sat_med) * (1.0 - args.sat_pull)
        gain = np.where(s > 1e-3, want / np.maximum(s, 1e-3), 1.0)
        L = rgb @ LUMA
        rgb = L[..., None] + (rgb - L[..., None]) * gain[..., None]
        a[..., :3] = np.clip(rgb, 0, 255)

        if args.warm:
            a[..., 0] = np.clip(a[..., 0] * (1 + args.warm), 0, 255)
            a[..., 2] = np.clip(a[..., 2] * (1 - args.warm), 0, 255)

        out = np.clip(a, 0, 255).astype(np.uint8)
        Image.fromarray(out, "RGBA").save(os.path.join(DST, n + ".png"))
        L2 = lum(out[..., :3].astype(np.float32))
        rows.append(dict(name=n, v1_ref=round(ref[n], 1), target=round(target, 1),
                         before=round(stats[n]["med"], 1),
                         after=round(float(np.median(L2[m])), 1),
                         gamma=round(g, 3),
                         sat_before=round(stats[n]["sat"], 3),
                         sat_after=round(float(saturation(out[..., :3].astype(np.float32))[m].mean()), 3),
                         clipped=round(float((L2[m] > 253).mean()), 3)))

    with open(os.path.join(DST, "grade.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(shell_median=round(shell_med, 1), warm=args.warm, sat_pull=args.sat_pull,
                       band=[BAND_FLOOR, BAND_TOP], objects=rows), fh, indent=1)

    print("shell median %.0f   targets band %.0f..%.0f" % (shell_med, shell_med * BAND_FLOOR, shell_med * BAND_TOP))
    print("%-15s %6s %6s %6s %6s %6s %6s" % ("object", "v1", "target", "before", "after", "g", "sat"))
    for r in rows:
        flag = "  <-- clipped" if r["clipped"] > 0.03 else ""
        print("%-15s %6.0f %6.0f %6.0f %6.0f %6.2f %5.2f->%.2f%s"
              % (r["name"], r["v1_ref"], r["target"], r["before"], r["after"], r["gamma"],
                 r["sat_before"], r["sat_after"], flag))
    err = [abs(r["after"] - r["target"]) / max(r["target"], 1) for r in rows]
    print("\nmedian error vs target %.1f%%, worst %.1f%%" % (100 * float(np.median(err)), 100 * max(err)))
    print("clipped objects: %d" % sum(1 for r in rows if r["clipped"] > 0.03))


if __name__ == "__main__":
    main()
