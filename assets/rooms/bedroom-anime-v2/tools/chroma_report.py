"""Colour-temperature and lineart report for the cut-out assets.

Two things make a set of separately generated props read as a collage even when their
brightness is fine: a different white point (warm interior vs neutral studio) and a
different lineart/rendering habit. Both are measurable.

Usage:  python chroma_report.py
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


def main():
    sh = np.asarray(Image.open(SHELL).convert("RGB")).astype(np.float32)
    print("shell mean rgb %s  R/B %.2f" % (np.round(sh.reshape(-1, 3).mean(0), 1), sh[..., 0].mean() / sh[..., 2].mean()))
    print()
    print("%-15s %6s %6s %6s %6s %6s %6s %6s" % ("asset", "R", "G", "B", "R/B", "sat", "line%", "stroke"))
    rows = []
    for f in sorted(os.listdir(ASSETS)):
        if not f.endswith(".png") or f.startswith("_"):
            continue
        a = np.asarray(Image.open(os.path.join(ASSETS, f)).convert("RGBA")).astype(np.float32)
        m = a[..., 3] > 200
        if m.sum() < 500:
            continue
        rgb = a[..., :3]
        mean = rgb[m].mean(0)
        mx, mn = rgb.max(2), rgb.min(2)
        sat = float(((mx - mn) / np.maximum(mx, 1))[m].mean())
        L = rgb @ LUMA
        # lineart: dark thin strokes = pixels well below the local median of the silhouette
        med = ndimage.median_filter(np.where(m, L, np.nan), size=9)
        med = np.nan_to_num(med, nan=0.0)
        dark = m & (L < med - 45)
        line = float(dark.sum() / max(m.sum(), 1))
        # stroke width estimate: dark-pixel count / length of their skeleton proxy
        if dark.sum() > 200:
            er = ndimage.binary_erosion(dark, np.ones((3, 3), bool))
            stroke = float(dark.sum() / max(er.sum(), 1))
        else:
            stroke = 0.0
        rows.append((f[:-4], mean, mean[0] / max(mean[2], 1), sat, line, stroke))
    for n, mean, rb, sat, line, stroke in sorted(rows, key=lambda r: r[3]):
        print("%-15s %6.0f %6.0f %6.0f %6.2f %6.2f %6.1f %6.1f" % (n, mean[0], mean[1], mean[2], rb, sat, 100 * line, stroke))
    print()
    sats = np.array([r[3] for r in rows])
    lines = np.array([r[4] for r in rows])
    print("saturation  mean %.2f  sd %.2f  min %.2f  max %.2f" % (sats.mean(), sats.std(), sats.min(), sats.max()))
    print("lineart     mean %.1f%%  sd %.1f  min %.1f  max %.1f" % (100 * lines.mean(), 100 * lines.std(), 100 * lines.min(), 100 * lines.max()))


if __name__ == "__main__":
    main()
