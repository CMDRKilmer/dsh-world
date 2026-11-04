"""Give the empty shell the palette the room is supposed to live in.

The shell was generated as a bright, pale beige interior: mean RGB 223/209/189, mean
saturation 0.16, red/blue 1.17. The approved v1 painting is a warm wooden room at 121/89/52,
saturation 0.59. Placing warm wooden furniture into a near-grey box is the other half of the
collage problem -- the props were graded toward the shell's *level*, but the shell itself is
too colourless to hold them together.

The gain is applied in HSV, on S alone, so V (and therefore every pixel's luminance
structure) is untouched: the room stays exactly as bright as it was, no light is invented,
and the objects graded against its median luminance keep their targets. Working directly on
RGB channels instead blew out 50% of the frame, because bright walls have no headroom above
their own value.

    python grade_shell.py [--sat 2.0] [--warm 0.04]

Writes shell_graded.png.
"""
import argparse
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
SHELL = r"D:\ComfyUI_windows_portable\ComfyUI\output\shell_wide_00001_.png"
OUT = os.path.join(ROOM, "shell_graded.png")
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def rgb_to_hsv(a):
    a = a / 255.0
    mx = a.max(-1)
    mn = a.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    idx = m & (mx == r)
    h[idx] = ((g[idx] - b[idx]) / d[idx]) % 6
    idx = m & (mx == g)
    h[idx] = (b[idx] - r[idx]) / d[idx] + 2
    idx = m & (mx == b)
    h[idx] = (r[idx] - g[idx]) / d[idx] + 4
    h = h * 60.0
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def hsv_to_rgb(h, s, v):
    h = (h % 360.0) / 60.0
    i = np.floor(h).astype(np.int32) % 6
    f = h - np.floor(h)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,), np.float32)
    for k, (rr, gg, bb) in enumerate([(v, t, p), (q, v, p), (p, v, t),
                                     (p, q, v), (t, p, v), (v, p, q)]):
        sel = i == k
        out[..., 0][sel] = rr[sel]
        out[..., 1][sel] = gg[sel]
        out[..., 2][sel] = bb[sel]
    return out * 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sat", type=float, default=2.0, help="HSV saturation gain")
    ap.add_argument("--warm", type=float, default=0.04,
                    help="hue rotation toward orange, in degrees")
    args = ap.parse_args()

    a = np.asarray(Image.open(SHELL).convert("RGB")).astype(np.float32)
    h, s, v = rgb_to_hsv(a)
    s2 = np.clip(s * args.sat, 0.0, 1.0)
    h2 = h - args.warm * 60.0  # warmer = hue index lower, toward red/orange
    out = np.clip(hsv_to_rgb(h2, s2, v), 0, 255)

    def sat(rgb):
        mx, mn = rgb.max(-1), rgb.min(-1)
        return ((mx - mn) / np.maximum(mx, 1e-3)).mean()

    print("%-8s %-24s %-8s %-8s %-8s %-8s" % ("", "mean rgb", "median", "mean", "sat", "R/B"))
    for tag, im in (("before", a), ("after", out)):
        L = im @ LUMA
        print("%-8s %-24s %-8.0f %-8.1f %-8.2f %-8.2f" % (
            tag, np.round(im.reshape(-1, 3).mean(0), 1), np.median(L), L.mean(),
            sat(im), im[..., 0].mean() / im[..., 2].mean()))
    print("clipped %.2f%%   luminance median shift %.1f"
          % (100 * float((out.max(-1) >= 254).mean()), np.median(out @ LUMA) - np.median(a @ LUMA)))

    Image.fromarray(out.astype(np.uint8), "RGB").save(OUT)
    print("wrote", os.path.basename(OUT))


if __name__ == "__main__":
    main()
