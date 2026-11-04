"""Assemble the cut-out assets onto the empty room shell.

Plan A: every object was generated on its own with no baked lighting, so the room is
composed by placing those assets rather than by slicing a finished painting.

Sizes are set in screen space, not metres, and that is deliberate: the shell is not
metrically self-consistent. Its back wall spans 528 px, and by the time the floor reaches
the front of the frame at y=711 it spans the full 1536 px -- a 2.9x change over 180 px of
depth. Forcing a single pixels-per-metre figure onto that makes a 2 m bed 878 px wide and
clips it off the canvas. So each object declares its width in pixels as read off the room,
and the depth scaling below is the gentler one the shell actually draws.

Placement is hierarchical, because "where does this thing sit" is the whole problem:

  floor  - bottom-centre anchor on the floor plane; size shrinks with depth
  on     - a child of another object: positioned in the parent's own rect (u across, v down)
           and sized relative to it, so it inherits the parent's perspective instead of
           being scaled by a floor plane it never touches
  abs    - explicit canvas rect, for things that hang in the air

Outputs:
  room.png                  flattened composite
  layers/NN_<name>.png      one RGBA layer per object, already at canvas size
  manifest.json             placement data + provenance, same shape as v1
  compose-report.json       numeric checks run after composing
"""
import argparse
import json
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
ASSETS = os.path.join(ROOM, "assets")  # replaced by --assets, see main()
LAYERS = os.path.join(ROOM, "layers")
SHELL = r"D:\ComfyUI_windows_portable\ComfyUI\output\shell_wide_00001_.png"
CANVAS = (1536, 864)

# --- floor plane measured from shell_wide_00001_.png -----------------------------------
BACK_Y = 531.0
BACK_X0, BACK_X1 = 480.0, 1008.0
LEFT_EDGE_Y = 711.0
RIGHT_EDGE_Y = 707.0
FRONT_Y = 864.0
SCALE_FAR, SCALE_NEAR = 0.58, 1.00

# The band of a support's own image where its usable top surface lives, as a fraction of
# the support's placed height. Measured from each asset's silhouette.
SURFACE = {
    "desk": (0.01, 0.31),
    "cabinet": (0.01, 0.26),
    "side_table": (0.02, 0.30),
    "easel": (0.08, 0.42),
    "bed": (0.30, 0.95),
}

# name, mode, params, z
#   floor: (x, y, width_px, squash)
#   on:    (parent, u, v, rel_w, squash)
#   abs:   (x, y, width_px, scale)
#
# z is the drawing order, and for anything standing on the floor it is simply the anchor's y:
# the lower an object's feet sit in the frame, the closer it is to the camera, the later it is
# drawn. Leaving that to be hand-assigned was a mistake -- the bedside cabinet was given a z
# in front of the bed while standing half a metre behind it, so it painted itself onto the
# mattress. Children in "on" mode inherit parent_z + 0.5, which keeps a TV above the cabinet
# it stands on while still letting a chair in front of that cabinet cover it.
#
# Two objects opt out: the rug lies flat and must be under everything, and the hanging plant
# is on the wall, so both carry an explicit z.
LAYOUT = [
    ("rug",             "floor", (830, 828, 480, 0.80),    2),
    ("plant_hanging",   "abs",   (250, 40, 120, 1.0),      6),

    # --- against the back wall: the desk under the window, the bookcase on the right ---
    ("bookshelf",       "floor", (1230, 660, 390, 1.0), None),
    ("desk",            "floor", (790, 612, 610, 1.0),  None),

    # --- right side: the upright piano, its bench, and a plant in front of it ---
    ("piano",           "floor", (1260, 764, 500, 1.0), None),
    ("piano_bench",     "floor", (1230, 840, 190, 1.0), None),
    ("plant_pot",       "floor", (1462, 856, 140, 1.0), None),

    # --- left side: the easel tucked against the back wall, the bed in front of it, and
    # the TV cabinet in the near-left corner at the foot of the bed, the way the approved
    # reference has it: the cabinet is largely behind the bed, the TV rises above it. ---
    # The easel stands on the floor behind the bed, so the bed hides its legs and nothing
    # else -- putting its feet lower in the frame buried half of it.
    ("easel",           "floor", (430, 566, 150, 1.0),  None),
    ("bed",             "floor", (400, 812, 700, 1.0),  None),
    # the cabinet stands at the near-left corner, in front of the foot of the bed, so it
    # takes an explicit z above the bed's: sorting by foot position alone would put it
    # behind, because its feet are higher up the frame than the bed's.
    ("cabinet",         "floor", (115, 812, 225, 1.0),  900),

    # --- middle floor ---
    ("office_chair",    "floor", (870, 772, 235, 1.0),  None),
    ("side_table",      "floor", (1020, 832, 180, 1.0), None),
    ("basket",          "floor", (700, 838, 140, 1.0),  None),

    # --- on the desk, back row then front row ---
    # v is where the object's bottom sits as a fraction of the desk's height: props at the
    # back of the desk use small v, props near the front edge use large v. squash flattens
    # objects that lie flat on the surface, since they are seen at a shallow angle.
    ("monitor",         "on", ("desk", 0.51, 0.05, 0.50, 1.00), None),
    ("microphone",      "on", ("desk", 0.05, 0.06, 0.16, 1.00), None),
    ("desk_lamp",       "on", ("desk", 0.93, 0.06, 0.26, 1.00), None),
    ("mp3_player",      "on", ("desk", 0.30, 0.09, 0.12, 0.70), None),
    ("sketchbook",      "on", ("desk", 0.13, 0.22, 0.24, 0.60), None),
    ("keyboard",        "on", ("desk", 0.45, 0.25, 0.32, 0.45), None),
    ("mouse",           "on", ("desk", 0.66, 0.27, 0.10, 0.70), None),
    ("mug",             "on", ("desk", 0.80, 0.17, 0.11, 1.00), None),
    ("phone",           "on", ("desk", 0.90, 0.30, 0.12, 0.60), None),

    # --- on the cabinet, the easel, the bed, the side table ---
    ("tv",              "on", ("cabinet", 0.50, 0.02, 0.86, 1.00), None),
    ("game_console",    "on", ("cabinet", 0.50, 0.14, 0.70, 1.00), None),
    ("controller",      "on", ("cabinet", 0.24, 0.21, 0.40, 0.75), None),
    ("easel_painting",  "on", ("easel", 0.52, 0.20, 1.00, 1.00), None),
    ("cat",             "on", ("bed", 0.70, 0.45, 0.34, 1.00), None),
    ("rice_cooker",     "on", ("side_table", 0.48, 0.06, 0.73, 1.00), None),
]


def floor_top(x):
    if x < BACK_X0:
        return BACK_Y + (BACK_X0 - x) / BACK_X0 * (LEFT_EDGE_Y - BACK_Y)
    if x > BACK_X1:
        return BACK_Y + (x - BACK_X1) / (CANVAS[0] - BACK_X1) * (RIGHT_EDGE_Y - BACK_Y)
    return BACK_Y


def depth_scale(y):
    t = min(1.0, max(0.0, (y - BACK_Y) / (FRONT_Y - BACK_Y)))
    return SCALE_FAR + (SCALE_NEAR - SCALE_FAR) * t


def open_asset(name):
    return Image.open(os.path.join(ASSETS, name + ".png")).convert("RGBA")


def resize(im, w, squash=1.0):
    w = max(1, int(round(w)))
    h = max(1, int(round(im.height * w / im.width * squash)))
    return im.resize((w, h), Image.LANCZOS)


def main():
    global ASSETS
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="assets",
                    help="cut-out directory to place: assets (as generated) or assets_graded "
                         "(tone and palette matched to the shell by grade_assets.py)")
    ap.add_argument("--shell", default=None,
                    help="room plate to compose onto; defaults to the raw shell_wide, pass "
                         "shell_graded.png for the palette-matched plate")
    args = ap.parse_args()
    ASSETS = os.path.join(ROOM, args.assets)
    shell_path = os.path.join(ROOM, args.shell) if args.shell else SHELL

    os.makedirs(LAYERS, exist_ok=True)
    for f in os.listdir(LAYERS):
        if f.endswith(".png"):
            os.remove(os.path.join(LAYERS, f))

    shell = Image.open(shell_path).convert("RGB")
    if shell.size != CANVAS:
        shell = shell.resize(CANVAS, Image.LANCZOS)
    canvas = shell.convert("RGBA")

    placed, warnings = {}, []
    for idx, (name, mode, prm, fixed_z) in enumerate(LAYOUT):
        src_img = open_asset(name)
        if mode == "floor":
            ax, ay, width, squash = prm
            sc = depth_scale(ay)
            img = resize(src_img, width * sc, squash)
            x = int(round(ax - img.width / 2.0))
            y = int(round(ay - img.height))
            ft = floor_top(ax)
            if ay < ft - 2:
                warnings.append("%s floats: anchor y=%d above floor line %.0f" % (name, ay, ft))
            z = ay if fixed_z is None else fixed_z
            placed[name] = dict(x=x, y=y, w=img.width, h=img.height, scale=round(sc, 3),
                                anchors={"bottom_center": [ax, ay]})
        elif mode == "on":
            parent, u, v, rel, squash = prm
            par = placed[parent]
            img = resize(src_img, par["w"] * rel, squash)
            x = int(round(par["x"] + u * par["w"] - img.width / 2.0))
            y = int(round(par["y"] + v * par["h"] - img.height))
            lo, hi = SURFACE.get(parent, (0.0, 1.0))
            if not lo <= v <= hi:
                warnings.append("%s sits at v=%.2f, outside %s's surface band %.2f-%.2f"
                                % (name, v, parent, lo, hi))
            z = par["z"] + 0.5 if fixed_z is None else fixed_z
            placed[name] = dict(x=x, y=y, w=img.width, h=img.height, scale=par["scale"],
                                anchors={"on": parent, "u": u, "v": v, "rel_w": rel,
                                         "squash": squash})
        else:
            ax, ay, width, sc = prm
            img = resize(src_img, width * sc)
            x, y = int(ax), int(ay)
            z = ay if fixed_z is None else fixed_z
            placed[name] = dict(x=x, y=y, w=img.width, h=img.height, scale=sc, anchors={})

        if x < 0 or y < 0 or x + img.width > CANVAS[0] or y + img.height > CANVAS[1]:
            warnings.append("%s is clipped by the canvas" % name)
        layer = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
        layer.alpha_composite(img, (max(0, x), max(0, y)))
        fn = "%02d_%s.png" % (idx, name)
        layer.save(os.path.join(LAYERS, fn))
        placed[name].update(file=fn, z=round(float(z), 2), order=idx,
                            source="%s/%s.png" % (args.assets, name))

    for name in sorted(placed, key=lambda n: (placed[n]["z"], placed[n]["order"])):
        canvas.alpha_composite(Image.open(os.path.join(LAYERS, placed[name]["file"])).convert("RGBA"))
    canvas.convert("RGB").save(os.path.join(ROOM, "room.png"))

    # ---- checks -----------------------------------------------------------------------
    owner = np.zeros((CANVAS[1], CANVAS[0]), np.int32) - 1
    for name in sorted(placed, key=lambda n: (placed[n]["z"], placed[n]["order"])):
        a = np.asarray(Image.open(os.path.join(LAYERS, placed[name]["file"])).convert("RGBA"))[..., 3] > 127
        owner[a] = placed[name]["order"]
    visible = {}
    for name, p in placed.items():
        lay = np.asarray(Image.open(os.path.join(LAYERS, p["file"])).convert("RGBA"))[..., 3] > 127
        tot = int(lay.sum())
        vis = int((owner[lay] == p["order"]).sum())
        visible[name] = round(vis / tot, 3) if tot else 0.0
        if tot and vis / tot < 0.55:
            warnings.append("%s is %.0f%% hidden by objects in front of it" % (name, 100 * (1 - vis / tot)))

    covered = float((owner >= 0).mean())
    report = dict(canvas=list(CANVAS), objects=len(placed),
                  covered_fraction=round(covered, 4), visible=visible, warnings=warnings)
    with open(os.path.join(ROOM, "compose-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)

    manifest = dict(
        canvas=list(CANVAS),
        method="asset-first composition: each object generated alone on a chroma-key backdrop "
               "with no cast shadow or baked lighting, cut out, then placed on the measured "
               "floor plane in screen space; props inherit their support's perspective",
        shell=os.path.basename(shell_path),
        asset_set=args.assets,
        floor=dict(back_y=BACK_Y, back_x=[BACK_X0, BACK_X1], left_edge_y=LEFT_EDGE_Y,
                   right_edge_y=RIGHT_EDGE_Y, scale_far=SCALE_FAR, scale_near=SCALE_NEAR),
        surface_bands=SURFACE,
        objects=[dict(name=n, **{k: v for k, v in p.items() if k != "order"}, order=p["order"])
                 for n, p in sorted(placed.items(), key=lambda kv: kv[1]["order"])],
    )
    with open(os.path.join(ROOM, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    print("composed %d objects, covered %.1f%% of the canvas" % (len(placed), 100 * covered))
    for n, p in sorted(placed.items(), key=lambda kv: kv[1]["z"]):
        print("  z%-3d %-15s %4dx%-4d at (%4d,%4d) scale %.2f visible %.2f"
              % (p["z"], n, p["w"], p["h"], p["x"], p["y"], p["scale"], visible[n]))
    print("\nwarnings:")
    for w in warnings:
        print("  -", w)


if __name__ == "__main__":
    main()