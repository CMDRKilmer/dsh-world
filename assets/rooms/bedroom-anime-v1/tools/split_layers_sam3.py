"""SAM3 concept-prompt layer splitting for the bedroom reference image (v2).

Each object is described by one or more concept phrases plus a *hint box* that was
measured by eye on the reference art.  For every phrase SAM 3 (Promptable Concept
Segmentation) proposes instances; the instance that falls most completely inside the
hint box wins.  Masks are clipped to the hint box (+slack), reduced to their main
connected components, then a forward z-claim pass gives every pixel of the canvas to
exactly one layer (room plate included).

Usage:  python split_layers_sam3.py [--out DIR] [--dry-run] [--overlay PNG]
"""
import argparse
import json
import os
import re
import sys

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import Sam3Model, Sam3Processor

REF = r"C:\Users\kilsa\Desktop\code\dsh-world\assets\rooms\bedroom-anime-v1\room-reference.png"
MODEL_DIR = r"C:\Users\kilsa\.cache\dsh-models\sam3"
OUT_DEFAULT = r"C:\Users\kilsa\Desktop\code\dsh-world\assets\rooms\bedroom-anime-v1\layers"

# name, phrases, hint box (x1,y1,x2,y2), z (0 = front-most)
OBJECTS = [
    ("cat",              ["cat"],                                    (1025, 592, 1245, 722),   0),
    ("piano_bench",      ["bench", "stool", "piano bench"],          (1145, 700, 1415, 864),   1),
    ("chair",            ["office chair", "chair"],                  (650, 400, 895, 662),     2),
    ("rug",              ["carpet", "rug"],                          (945, 608, 1315, 818),    3),
    ("piano",            ["electronic keyboard", "keyboard"],        (1232, 468, 1536, 810),   4),
    ("stool",            ["stool"],                                  (1028, 448, 1162, 632),   5),
    ("rice_cooker",      ["rice cooker"],                            (1038, 362, 1162, 488),   6),
    ("bed",              ["bed"],                                    (0, 470, 890, 864),       7),
    ("plant_floor",      ["potted plant", "plant"],                  (1128, 418, 1242, 566),   8),
    ("microphone",       ["microphone"],                             (688, 212, 762, 332),     9),
    ("monitor",          ["monitor", "computer monitor"],            (826, 222, 1032, 392),   10),
    ("desk_lamp",        ["desk lamp", "lamp"],                      (1012, 212, 1152, 388),  11),
    ("computer_keyboard",["keyboard"],                               (818, 356, 958, 402),    12),
    ("sketchbook",       ["open book", "book", "sketchbook"],        (668, 366, 832, 428),    13),
    ("mp3_player",       ["smartphone", "mp3 player", "speaker"],    (602, 346, 668, 414),    14),
    ("phone",            ["smartphone", "phone"],                    (826, 390, 880, 428),    15),
    ("phone_black",      ["smartphone", "phone"],                    (498, 380, 572, 424),    16),
    ("mug",              ["mug", "cup"],                             (948, 350, 1014, 414),   17),
    ("plant_desk",       ["potted plant", "plant", "flower pot"],     (1012, 312, 1112, 394),  18),
    ("tv",               ["television", "tv"],                       (0, 368, 138, 644),      19),
    ("game_console",     ["game console", "game controller"],        (40, 500, 242, 662),     20),
    ("desk",             ["desk"],                                   (455, 342, 1185, 618),   21),
    ("bedside_cabinet",  ["bookcase", "cabinet", "dresser"],          (0, 466, 344, 864),      22),
    ("bookshelf",        ["bookcase", "bookshelf"],                  (1218, 0, 1536, 722),    23),
    ("easel",            ["easel"],                                  (288, 204, 472, 528),    24),
    ("easel_painting",   ["painting", "framed painting", "picture"],  (296, 216, 462, 508),    25),
    ("plant_left",       ["hanging plant", "potted plant"],          (108, 0, 322, 302),      26),
    ("plant_right",      ["hanging plant", "potted plant"],          (1100, 0, 1345, 340),    27),
]

SLACK = 24          # px the mask may exceed the hint box
MIN_SELF = 0.45     # fraction of an instance that must fall inside the hint box
PREFER_SELF = 0.85  # above this, prefer the biggest instance over the best-fitting one
KEEP_RATIO = 0.05   # connected components smaller than this share of the biggest are specks
CLOSE_MIN, CLOSE_MAX = 6, 40   # closing radius is derived from the hint box size
UNION_OBJECTS = {"game_console"}   # objects whose layer merges several instances
HULL_OBJECTS = {"bed", "rug"}      # flat objects whose silhouette should have no bites taken out


def load_model():
    kw = dict(local_files_only=True)
    try:
        model = Sam3Model.from_pretrained(MODEL_DIR, dtype=torch.float16, **kw)
    except TypeError:
        model = Sam3Model.from_pretrained(MODEL_DIR, torch_dtype=torch.float16, **kw)
    model = model.to("cuda").eval()
    processor = Sam3Processor.from_pretrained(MODEL_DIR, local_files_only=True)
    return model, processor


def clean(mask, box, slack=SLACK):
    """Clamp the mask to the hint box plus slack."""
    x1, y1, x2, y2 = box
    keep = np.zeros_like(mask)
    keep[max(0, int(y1) - slack):min(mask.shape[0], int(y2) + slack),
         max(0, int(x1) - slack):min(mask.shape[1], int(x2) + slack)] = True
    return mask & keep


def largest_components(m, keep_ratio=KEEP_RATIO):
    from scipy import ndimage
    lab, n = ndimage.label(m)
    if n <= 1:
        return m
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    top = float(sizes.max())
    out = np.zeros_like(m)
    for i, s in enumerate(sizes, start=1):
        if s >= max(top * keep_ratio, 60):
            out |= (lab == i)
    return out


def morph_close(m, radius):
    """Bridge sunlight stripes and thin gaps that break up large flat objects."""
    from scipy import ndimage
    if radius <= 0:
        return m
    yy, xx = np.ogrid[-radius:radius + 1, -radius:radius + 1]
    disk = (yy * yy + xx * xx) <= radius * radius
    return ndimage.binary_closing(m, structure=disk)


def fill_holes(m):
    from scipy import ndimage
    return ndimage.binary_fill_holes(m)


def convex_fill(m):
    """Rasterise the convex hull of a mask: closes concave bites a flat object should not have."""
    from scipy.spatial import ConvexHull
    ys, xs = np.nonzero(m)
    if len(xs) < 3:
        return m
    pts = np.column_stack([xs, ys]).astype(np.float64)
    try:
        hull = ConvexHull(pts)
    except Exception:
        return m
    poly = [tuple(p) for p in pts[hull.vertices]]
    img = Image.new("L", (m.shape[1], m.shape[0]), 0)
    ImageDraw.Draw(img).polygon(poly, fill=255)
    return np.array(img) > 0


def inside_ratio(mask, box):
    x1, y1, x2, y2 = [int(v) for v in box]
    sub = mask[max(0, y1):y2, max(0, x1):x2]
    total = float(mask.sum())
    return float(sub.sum()) / total if total else 0.0


def run_concept(model, processor, vision, phrase, H, W):
    ti = processor(text=phrase, return_tensors="pt")
    with torch.no_grad():
        out = model(vision_embeds=vision,
                    input_ids=ti["input_ids"].to("cuda"),
                    attention_mask=ti["attention_mask"].to("cuda"))
    res = processor.post_process_instance_segmentation(
        out, threshold=0.2, mask_threshold=0.5, target_sizes=[(H, W)])[0]
    masks = [m.detach().float().cpu().numpy() > 0.5 for m in res["masks"]]
    scores = [float(s) for s in res["scores"]]
    return masks, scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overlay", default="")
    args = ap.parse_args()

    img = Image.open(REF).convert("RGB")
    W, H = img.size
    model, processor = load_model()
    print("model loaded", file=sys.stderr)

    pixel_values = processor(images=img, return_tensors="pt")["pixel_values"].to("cuda", dtype=torch.float16)
    with torch.no_grad():
        vision = model.get_vision_features(pixel_values=pixel_values)

    results = []
    for name, phrases, box, z in OBJECTS:
        cands = []
        for phrase in phrases:
            masks, scores = run_concept(model, processor, vision, phrase, H, W)
            for k, m in enumerate(masks):
                if m.sum() < 200:
                    continue
                cands.append((inside_ratio(m, box), scores[k], phrase, m))
        if not cands:
            print("[MISS] %-18s no instance for %s" % (name, phrases), file=sys.stderr)
            results.append(dict(name=name, z=z, found=False, phrases=phrases))
            continue
        # among instances that sit essentially inside the hint box, take the biggest one;
        # otherwise fall back to the instance that fits the box best
        fitting = [c for c in cands if c[0] >= PREFER_SELF]
        if name in UNION_OBJECTS:
            loose = [c for c in cands if c[0] >= 0.90 and c[3].sum() >= 300]
            loose.sort(key=lambda c: -c[3].sum())
            merged = None
            for c in loose[:6]:
                merged = c[3] if merged is None else (merged | c[3])
            r, score, phrase = (1.0, max(c[1] for c in loose), "union") if loose else cands[0][:3]
            m = merged if merged is not None else cands[0][3]
        elif fitting:
            r, score, phrase, m = max(fitting, key=lambda c: (c[3].sum(), c[1]))
        else:
            r, score, phrase, m = max(cands, key=lambda c: (c[0], c[1]))
        area = max(1.0, float((box[2] - box[0]) * (box[3] - box[1])))
        radius = int(min(CLOSE_MAX, max(CLOSE_MIN, round(area ** 0.5 / 12.0))))
        m = morph_close(clean(m, box), radius)
        if name in HULL_OBJECTS:
            m = convex_fill(fill_holes(m))
        m = largest_components(fill_holes(m))
        ys, xs = np.nonzero(m)
        if len(xs) == 0:
            print("[EMPTY] %-18s after clip" % name, file=sys.stderr)
            results.append(dict(name=name, z=z, found=False, phrases=phrases))
            continue
        x0, y0 = int(xs.min()), int(ys.min())
        x1_, y1_ = int(xs.max()) + 1, int(ys.max()) + 1
        flag = "" if r >= MIN_SELF else "  <-- LOW CONFIDENCE"
        print("[%s] %-18s %-20s score=%.3f inside=%.2f r=%2d px=%d box=(%d,%d,%d,%d)%s" % (
            "OK" if r >= MIN_SELF else "??", name, phrase, score, r, radius, int(m.sum()), x0, y0, x1_, y1_, flag),
            file=sys.stderr)
        results.append(dict(name=name, z=z, found=True, phrase=phrase, score=score, inside=r,
                            mask=m, crop=[x0, y0, x1_, y1_]))

    found = [r for r in results if r.get("found")]
    print("\nfound %d/%d" % (len(found), len(results)), file=sys.stderr)

    # forward z-claim: front-most objects claim pixels first
    claimed = np.zeros((H, W), bool)
    for r in sorted(found, key=lambda r: r["z"]):
        owned = r["mask"] & ~claimed
        r["owned"] = owned
        claimed |= owned
    room_mask = ~claimed

    if args.overlay:
        ov = np.array(img).copy()
        lab_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lab_img)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        rng = np.random.default_rng(7)
        for r in sorted(found, key=lambda r: r["z"]):
            col = tuple(int(c) for c in rng.integers(40, 255, 3))
            m = r["owned"]
            ov[m] = (ov[m] * 0.35 + np.array(col) * 0.65).astype(np.uint8)
            ys, xs = np.nonzero(m)
            if len(xs) == 0:
                continue
            cx, cy = int(np.median(xs)), int(np.median(ys))
            tw = d.textlength(r["name"], font=font)
            d.rectangle([cx, cy - 8, cx + tw + 3, cy + 9], fill=(0, 0, 0, 200))
            d.text((cx + 1, cy - 7), r["name"], fill=(255, 255, 255, 255), font=font)
        base = Image.fromarray(ov).convert("RGBA")
        Image.alpha_composite(base, lab_img).convert("RGB").save(args.overlay)
        print("overlay ->", args.overlay, file=sys.stderr)

    if args.dry_run:
        print(json.dumps([{k: v for k, v in r.items() if k not in ("mask", "owned")} for r in results],
                         indent=1, default=str))
        return

    os.makedirs(args.out, exist_ok=True)
    src = np.array(img)
    room = np.zeros((H, W, 4), np.uint8)
    room[..., :3] = src
    room[..., 3] = np.where(room_mask, 255, 0).astype(np.uint8)
    Image.fromarray(room, "RGBA").save(os.path.join(args.out, "room.png"))

    manifest = {
        "canvas": [W, H],
        "method": "SAM 3 concept prompts (text + hint box instance selection); "
                  "forward z-claim gives every pixel to exactly one layer",
        "source": os.path.basename(REF),
        "objects": [],
    }
    for idx, r in enumerate(sorted(found, key=lambda r: r["z"])):
        x0, y0, x1_, y1_ = r["crop"]
        sub = r["owned"][y0:y1_, x0:x1_]
        crop = np.zeros((y1_ - y0, x1_ - x0, 4), np.uint8)
        crop[..., :3] = src[y0:y1_, x0:x1_]
        crop[..., 3] = np.where(sub, 255, 0).astype(np.uint8)
        fn = "%02d_%s.png" % (idx, r["name"])
        Image.fromarray(crop, "RGBA").save(os.path.join(args.out, fn))
        manifest["objects"].append(dict(
            z=r["z"], name=r["name"], file=fn, x=x0, y=y0, w=x1_ - x0, h=y1_ - y0,
            visible_pixels=int(sub.sum()), sam3_pixels=int(r["mask"].sum()),
            score=round(r["score"], 4), inside=round(r["inside"], 3), phrase=r["phrase"],
            anchors={"bottom_center": [x0 + (x1_ - x0) // 2, y1_]},
        ))
    written = {o["file"] for o in manifest["objects"]}
    for fn in sorted(os.listdir(args.out)):
        if re.match(r"^\d\d_.*\.png$", fn) and fn not in written:
            os.remove(os.path.join(args.out, fn))
            print("removed stale layer:", fn, file=sys.stderr)
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    print(json.dumps({"objects": len(manifest["objects"]),
                      "room_pixels": int(room_mask.sum()),
                      "coverage": float((claimed | room_mask).mean())}, indent=1))


if __name__ == "__main__":
    main()
