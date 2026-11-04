"""Diagnostic: how does each asset's tonal range compare with the room it sits in?

Reports, per asset: luminance percentiles, the vertical shading gradient (is there baked
form shading despite the prompt asking for none), and how much of the silhouette falls
below the room's own dark end.

Usage:  python tone_report.py
"""
import os
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
ASSETS = os.path.join(ROOM, "assets")
SHELL = r"D:\ComfyUI_windows_portable\ComfyUI\output\shell_wide_00001_.png"
LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def lum(a):
    return a[..., :3] @ LUMA


def main():
    shell = np.asarray(Image.open(SHELL).convert("RGB")).astype(np.float32)
    sl = lum(shell)
    pct = list(np.percentile(sl, [1, 5, 50, 95, 99])) + [sl.mean()]
    print("shell  p1 %.0f  p5 %.0f  p50 %.0f  p95 %.0f  p99 %.0f  mean %.1f" % tuple(pct))
    print()
    print("%-15s %5s %5s %5s %5s %5s %6s %6s %6s" % (
        "asset", "p2", "p25", "p50", "p75", "p98", "top-bot", "shade", "below5%"))
    rows = []
    for f in sorted(os.listdir(ASSETS)):
        if not f.endswith(".png") or f.startswith("_"):
            continue
        a = np.asarray(Image.open(os.path.join(ASSETS, f)).convert("RGBA")).astype(np.float32)
        m = a[..., 3] > 200
        if m.sum() < 500:
            continue
        L = lum(a)
        v = L[m]
        ys, xs = np.nonzero(m)
        # vertical gradient: mean luminance of the top third vs the bottom third
        y0, y1 = ys.min(), ys.max()
        h = max(1, y1 - y0)
        band = np.zeros_like(m)
        band[y0:y0 + int(h / 3)] = True
        top = L[m & band].mean()
        band[:] = False
        band[y1 - int(h / 3):y1 + 1] = True
        bot = L[m & band].mean()
        # low-frequency shading amplitude: std of a heavily blurred copy, over the silhouette
        sig = max(6.0, max(a.shape[:2]) / 10.0)
        blur = ndimage.gaussian_filter(L * m, sig) / np.maximum(ndimage.gaussian_filter(m.astype(np.float32), sig), 1e-3)
        shade = float(np.std(blur[m]))
        p = np.percentile(v, [2, 25, 50, 75, 98])
        below = float((v < 5).mean())
        rows.append((f[:-4], p, top - bot, shade, below))
    for name, p, d, s, b in sorted(rows, key=lambda r: r[1][2]):
        print("%-15s %5.0f %5.0f %5.0f %5.0f %5.0f %6.1f %6.1f %6.2f"
              % (name, p[0], p[1], p[2], p[3], p[4], d, s, b))
    print()
    med = np.array([r[1][2] for r in rows])
    print("median-of-medians %.0f   range %.0f..%.0f" % (np.median(med), med.min(), med.max()))
    print("vertical gradient mean %.1f, max %.1f" % (np.mean([r[2] for r in rows]), max(abs(r[2]) for r in rows)))
    print("low-frequency shading mean %.1f" % np.mean([r[3] for r in rows]))


if __name__ == "__main__":
    main()
