"""Measure the floor plane of any room plate, so layouts measured on one plate can be
transplanted onto another only when their perspective actually agrees.

For each column the script finds the last strong horizontal gradient (the wall/floor seam),
then reports the seam at the left edge, under the back wall, and at the right edge -- the same
four numbers compose_room.py carries for shell_wide.

Usage:  python measure_floor.py <image> [<image> ...]
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

LUMA = np.array([0.299, 0.587, 0.114], np.float32)


def seam(a):
    L = a @ LUMA
    g = np.abs(np.diff(ndimage.gaussian_filter(L, 2.0), axis=0))
    H, W = g.shape
    # the floor is below the seam: search the lower 70% of the frame
    band = g[int(H * 0.25):]
    rows = np.argmax(band, axis=0) + int(H * 0.25)
    return rows, L


def main():
    for path in sys.argv[1:]:
        a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
        rows, L = seam(a)
        H, W = a.shape[:2]
        print("%s  %dx%d" % (path.split("\\")[-1], a.shape[1], a.shape[0]))
        for x in (10, W // 8, W // 4, W // 2, 3 * W // 4, W - W // 8, W - 10):
            y = int(rows[x])
            print("    x=%4d  seam y=%3d   lum@seam-20 %5.0f  lum@seam+20 %5.0f"
                  % (x, y, L[max(0, y - 20), x], L[min(H - 1, y + 20), x]))
        # median seam under the middle third = back wall floor line
        mid = rows[W // 3:2 * W // 3]
        print("    back-wall floor line (median of middle third) y=%.0f" % np.median(mid))
        print()


if __name__ == "__main__":
    main()
