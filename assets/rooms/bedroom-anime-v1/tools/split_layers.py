"""Split assets/rooms/bedroom-anime-v1/room-reference.png into one RGBA layer per object.

Method
------
1. SAM 2.1 (hiera-large) box+point prompts produce a per-object mask. Large
   structural furniture (bed, bedside cabinet) is a union of several part
   prompts; desk and bookshelf use hand-drawn polygons because their visible
   area is a thin band / a flat rectangle against the wall.
2. Masks are cleaned: clamp to the prompt box (+14 px), 5x5 closing, hole
   fill, drop connected components below 2% of the largest one.
3. Forward z-claim: objects are processed front-to-back and every pixel goes to
   the first object that claims it. The remainder becomes room.png. This makes
   the decomposition a partition, so compositing back reproduces the source
   byte-exactly (verified in write_layers()).

Requires: transformers >= 5.17 (Sam2Processor/Sam2Model), torch+CUDA,
scipy, pillow, numpy. Weights: facebook/sam2.1-hiera-large (~1 GB, not gated).
Behind a proxy set HTTP_PROXY / HTTPS_PROXY before running.

Usage
-----
    python split_layers.py --src <room-reference.png> --out <layers dir>

Output: 00_<name>.png ... NN_<name>.png (z=0 = closest to camera), room.png,
manifest.json, preview.png.
"""
import argparse, hashlib, json, os, shutil
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

# ---------------------------------------------------------------- mask specs
# name: (box, positive points, negative points) for a single SAM prompt
SINGLE = {
    'cat':              ((1048, 606, 1226, 711), [(1130, 660)], []),
    'piano_bench':      ((1155, 712, 1402, 861), [(1280, 790)], []),
    'chair':            ((669, 410, 878, 651), [(770, 470), (760, 600)], []),
    'rug':              ((955, 612, 1300, 808), [(980, 780), (1250, 760)], []),
    'piano':            ((1240, 470, 1536, 805), [(1400, 600), (1300, 700)], []),
    'stool':            ((1040, 458, 1153, 625), [(1060, 590), (1120, 560)], []),
    'rice_cooker':      ((1050, 371, 1146, 472), [(1090, 420)], []),
    'plant_floor':      ((1150, 430, 1228, 552), [(1190, 500)], []),
    'microphone':       ((576, 221, 788, 366), [(700, 290), (760, 300)], []),
    'monitor':          ((841, 235, 1015, 370), [(930, 300)], []),
    'desk_lamp':        ((1025, 224, 1137, 363), [(1075, 260), (1100, 340)], []),
    'computer_keyboard':((830, 365, 946, 393), [(890, 378)], []),
    'sketchbook':       ((681, 373, 822, 412), [(750, 392)], []),
    'mp3_player':       ((592, 353, 669, 419), [(640, 385)], []),
    'phone':            ((828, 390, 876, 424), [(850, 406)], []),
    'phone_black':      ((486, 382, 572, 428), [(520, 400)], []),
    'mug':              ((961, 360, 999, 404), [(975, 385)], []),
    'plant_desk':       ((526, 258, 598, 346), [(560, 300)], []),
    'tv':               ((2, 379, 119, 628), [(60, 450)], []),
    'game_console':     ((2, 505, 225, 690), [(160, 540), (90, 600), (40, 640)], []),
    'easel':            ((301, 213, 457, 514), [(380, 300), (420, 450)], []),
    'plant_left':       ((159, 2, 417, 247), [(250, 80), (300, 150), (200, 200)], []),
    'plant_right':      ((1108, 2, 1226, 259), [(1160, 80), (1180, 200)], []),
}
# multi-part objects: union of several prompts
PARTS = {
    'bed': [((275, 478, 680, 560), [(400, 520), (620, 520)], []),
            ((295, 535, 670, 700), [(350, 590), (560, 600)], []),
            ((150, 660, 670, 864), [(300, 760), (500, 800)], [])],
    'bedside_cabinet': [((0, 470, 330, 700), [(60, 560), (200, 540)], [(300, 600)]),
                        ((0, 600, 320, 864), [(60, 700), (200, 780)], [])],
}
# hand polygons
POLYS = {
    'desk': [(455, 352), (1160, 348), (1160, 450), (455, 453)],
    'bookshelf': [(1228, 0), (1462, 0), (1462, 620), (1332, 620), (1332, 864), (1228, 864)],
}
# claim order, front (closest to camera) first
ORDER = ['cat', 'piano_bench', 'chair', 'rug', 'piano', 'stool', 'rice_cooker', 'bed',
         'plant_floor', 'microphone', 'monitor', 'desk_lamp', 'computer_keyboard',
         'sketchbook', 'mp3_player', 'phone', 'phone_black', 'mug', 'plant_desk',
         'tv', 'game_console', 'desk', 'bedside_cabinet', 'bookshelf', 'easel',
         'plant_left', 'plant_right']


def build_masks(im, device='cuda'):
    import torch
    from transformers import Sam2Processor, Sam2Model
    W, H = im.size
    proc = Sam2Processor.from_pretrained('facebook/sam2.1-hiera-large')
    model = Sam2Model.from_pretrained('facebook/sam2.1-hiera-large').to(device).eval()

    def prompt(box, pos, neg):
        pts = [list(p) for p in pos] + [list(p) for p in neg]
        labs = [1] * len(pos) + [0] * len(neg)
        inp = proc(images=im, input_boxes=[[list(box)]], input_points=[[pts]],
                   input_labels=[[labs]], return_tensors='pt').to(device)
        with torch.no_grad():
            out = model(**inp, multimask_output=True)
        ms = proc.post_process_masks(out.pred_masks.cpu(), inp['original_sizes'].cpu())[0]
        sc = out.iou_scores[0].cpu().numpy().reshape(-1, 3)[0]
        k = int(np.argmax(sc))
        return (ms[0][k] if ms.ndim == 4 else ms[k]).numpy() > 0.0, float(sc[k])

    def clean(m, box, pad=14, close=5, minfrac=0.02):
        m = m.astype(bool)
        x0, y0, x1, y1 = box
        allow = np.zeros_like(m)
        allow[max(0, y0 - pad):min(H, y1 + pad), max(0, x0 - pad):min(W, x1 + pad)] = True
        m &= allow
        m = ndi.binary_closing(m, structure=np.ones((close, close), bool))
        m = ndi.binary_fill_holes(m)
        lab, n = ndi.label(m)
        if n > 1:
            sz = ndi.sum(m, lab, range(1, n + 1))
            m = np.isin(lab, [i + 1 for i, s in enumerate(sz) if s >= sz.max() * minfrac])
        return m

    def poly(pts):
        p = Image.new('L', (W, H), 0)
        ImageDraw.Draw(p).polygon([tuple(map(int, q)) for q in pts], fill=255)
        return np.array(p) > 0

    masks, scores = {}, {}
    for name, (box, pos, neg) in SINGLE.items():
        m, s = prompt(box, pos, neg)
        masks[name], scores[name] = clean(m, box), [round(s, 3)]
    for name, parts in PARTS.items():
        acc, sc = np.zeros((H, W), bool), []
        for box, pos, neg in parts:
            m, s = prompt(box, pos, neg)
            acc |= clean(m, box)
            sc.append(round(s, 3))
        masks[name], scores[name] = acc, sc
    for name, pts in POLYS.items():
        masks[name], scores[name] = poly(pts), ['polygon']
    return masks, scores


def write_layers(im, masks, out):
    W, H = im.size
    arr = np.array(im)
    os.makedirs(out, exist_ok=True)
    claimed = np.zeros((H, W), bool)
    owned = {}
    for name in ORDER:
        owned[name] = masks[name] & ~claimed
        claimed |= owned[name]
    room = ~claimed

    entries, files = [], {}
    canvas = np.zeros((H, W, 3), np.uint8)
    cov = np.zeros((H, W), bool)

    def paint(mask, x0, y0, rgba):
        canvas[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]][mask] = rgba[mask]
        cov[y0:y0 + mask.shape[0], x0:x0 + mask.shape[1]] |= mask

    Image.fromarray(np.dstack([arr, (room * 255).astype(np.uint8)]), 'RGBA').save(
        os.path.join(out, 'room.png'))
    paint(room, 0, 0, arr)
    files['room.png'] = None
    for z, name in enumerate(ORDER):
        m = owned[name]
        ys, xs = np.where(m)
        x0, x1, y0, y1 = int(xs.min()), int(xs.max()) + 1, int(ys.min()), int(ys.max()) + 1
        fn = f'{z:02d}_{name}.png'
        rgba = np.dstack([arr, (m * 255).astype(np.uint8)])[y0:y1, x0:x1]
        Image.fromarray(rgba, 'RGBA').save(os.path.join(out, fn))
        paint(rgba[:, :, 3] > 0, x0, y0, rgba[:, :, :3])
        entries.append(dict(z=z, name=name, file=fn, x=x0, y=y0, w=x1 - x0, h=y1 - y0,
                            visible_pixels=int(m.sum()),
                            anchors=dict(bottom_center=[x0 + (x1 - x0) // 2, y1])))
        files[fn] = None
    exact = bool((canvas == arr).all())
    for fn in files:
        files[fn] = hashlib.sha256(open(os.path.join(out, fn), 'rb').read()).hexdigest()
    return entries, files, dict(coverage=float(cov.mean()), recomposite_exact=exact)


def preview(out, entries):
    cell, cols = 300, 6
    rows = (len(entries) + 1 + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cell, rows * cell + 34), (24, 24, 28))
    ImageDraw.Draw(sheet).text((10, 10), 'layers - 27 objects + room background (checkerboard = transparent)',
                               fill=(235, 235, 235))
    for i, o in enumerate([{'file': 'room.png'}] + entries):
        t = Image.open(os.path.join(out, o['file'])).convert('RGBA')
        s = min((cell - 14) / t.width, (cell - 34) / t.height, 1.0)
        t = t.resize((max(1, int(t.width * s)), max(1, int(t.height * s))), Image.LANCZOS)
        bg = Image.new('RGBA', (cell, cell), (44, 44, 50, 255))
        d = ImageDraw.Draw(bg)
        for yy in range(0, cell, 14):
            for xx in range(0, cell, 14):
                if ((xx // 14) + (yy // 14)) % 2 == 0:
                    d.rectangle([xx, yy, xx + 13, yy + 13], fill=(58, 58, 66, 255))
        bg.alpha_composite(t, ((cell - t.width) // 2, 26 + (cell - 34 - t.height) // 2))
        ImageDraw.Draw(bg).text((5, 6), o['file'].replace('.png', ''), fill=(255, 215, 0))
        sheet.paste(bg.convert('RGB'), ((i % cols) * cell, 34 + (i // cols) * cell))
    sheet.save(os.path.join(out, 'preview.png'))


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument('--src', default=os.path.join(here, 'room-reference.png'))
    ap.add_argument('--out', default=os.path.join(here, 'layers'))
    ap.add_argument('--device', default='cuda')
    a = ap.parse_args()

    im = Image.open(a.src).convert('RGB')
    W, H = im.size
    masks, scores = build_masks(im, a.device)
    entries, files, check = write_layers(im, masks, a.out)
    preview(a.out, entries)
    manifest = dict(
        asset=os.path.basename(os.path.dirname(os.path.abspath(a.src))),
        canvas=[W, H],
        source=dict(file=os.path.basename(a.src),
                    sha256=hashlib.sha256(open(a.src, 'rb').read()).hexdigest()),
        z_convention='z=0 is closest to the camera; composite by painting room first, then z descending',
        objects=entries, files=files,
        verification=dict(method='SAM2.1-hiera-large box+point prompts, part unions, hand polygons for desk/bookshelf, '
                                 'forward z-claim so every pixel belongs to exactly one layer',
                          prompt_iou={k: v for k, v in scores.items()}, **check))
    json.dump(manifest, open(os.path.join(a.out, 'manifest.json'), 'w', encoding='utf-8'),
              indent=2, ensure_ascii=False)
    print(json.dumps(check))


if __name__ == '__main__':
    main()
