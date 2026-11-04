"""Contact sheet of the split layers: one labelled cell per object on a checkerboard."""
import json, os
from PIL import Image, ImageDraw, ImageFont

LAYERS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "layers")
CELL, PAD, COLS = 176, 8, 8


def checker(w, h, step=12):
    im = Image.new("RGB", (w, h), (58, 58, 58))
    d = ImageDraw.Draw(im)
    for y in range(0, h, step):
        for x in range(0, w, step):
            if (x // step + y // step) % 2 == 0:
                d.rectangle([x, y, x + step - 1, y + step - 1], fill=(74, 74, 74))
    return im


def main():
    man = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
    objs = sorted(man["objects"], key=lambda o: -o["z"])       # back to front
    try:
        font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
    rows = (len(objs) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (CELL + PAD) + PAD, rows * (CELL + 26 + PAD) + PAD), (30, 30, 30))
    d = ImageDraw.Draw(sheet)
    for i, o in enumerate(objs):
        cx = PAD + (i % COLS) * (CELL + PAD)
        cy = PAD + (i // COLS) * (CELL + 26 + PAD)
        cell = checker(CELL, CELL)
        im = Image.open(os.path.join(LAYERS, o["file"])).convert("RGBA")
        k = min(CELL / max(1, im.width), CELL / max(1, im.height), 1.0)
        im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
        cell.paste(im, ((CELL - im.width) // 2, (CELL - im.height) // 2), im)
        sheet.paste(cell, (cx, cy))
        d.text((cx + 2, cy + CELL + 4), "%02d %s" % (o["z"], o["name"]), fill=(235, 235, 235), font=font)
        d.text((cx + 2, cy + CELL + 17), "%d px" % o["visible_pixels"], fill=(150, 150, 150), font=font)
    out = os.path.join(LAYERS, "preview.png")
    sheet.save(out)
    print("preview ->", out, sheet.size, "objects:", len(objs))


if __name__ == "__main__":
    main()
