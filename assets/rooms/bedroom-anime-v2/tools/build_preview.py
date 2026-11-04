"""Build the review artefacts: a contact sheet of the assets and a labelled preview."""
import json
import os

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
ASSETS = os.path.join(ROOM, "assets")


def contact_sheet():
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    names = [o["name"] for o in sorted(man["objects"], key=lambda o: o["order"])]
    cols, cell = 7, 200
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (32, 32, 36))
    d = ImageDraw.Draw(sheet)
    for i, n in enumerate(names):
        im = Image.open(os.path.join(ASSETS, n + ".png")).convert("RGBA")
        im.thumbnail((cell - 16, cell - 30), Image.LANCZOS)
        cx, cy = (i % cols) * cell, (i // cols) * cell
        sheet.paste(im, (cx + (cell - im.width) // 2, cy + (cell - 24 - im.height) // 2 + 6), im)
        d.text((cx + 6, cy + cell - 16), "%s %dx%d" % (n, im.width, im.height), fill=(220, 220, 220))
    sheet.save(os.path.join(ROOM, "_contact-sheet.png"))


def labelled_preview():
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    im = Image.open(os.path.join(ROOM, "room.png")).convert("RGB")
    d = ImageDraw.Draw(im)
    for o in man["objects"]:
        x, y, w, h = o["x"], o["y"], o["w"], o["h"]
        d.rectangle([x, y, x + w, y + h], outline=(255, 40, 40))
        d.text((x + 2, max(0, y - 10)), o["name"], fill=(255, 255, 0))
    im.save(os.path.join(ROOM, "_preview-labelled.png"))


if __name__ == "__main__":
    contact_sheet()
    labelled_preview()
    print("wrote _contact-sheet.png and _preview-labelled.png")
