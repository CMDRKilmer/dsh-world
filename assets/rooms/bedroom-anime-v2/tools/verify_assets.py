"""Check every cut-out asset against SAM 3: does it depict what its filename claims?

Each asset is scored against its own phrase plus a few plausible distractors. An asset passes
when its own phrase scores >= 0.6 and beats every distractor.

Usage:  python verify_assets.py
"""
import json
import os

import numpy as np
import torch
from PIL import Image
from transformers import Sam3Model, Sam3Processor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
ASSETS = os.path.join(ROOM, "assets")
MODEL_DIR = r"C:\Users\kilsa\.cache\dsh-models\sam3"

EXPECT = {
    "bed": ["bed", "sofa", "table"],
    "desk": ["desk", "table", "bed"],
    "office_chair": ["office chair", "chair", "stool"],
    "monitor": ["monitor", "television", "window"],
    "keyboard": ["keyboard", "piano", "book"],
    "mouse": ["computer mouse", "phone", "stone"],
    "microphone": ["microphone", "lamp", "plant"],
    "mp3_player": ["mp3 player", "phone", "soap"],
    "phone": ["smartphone", "remote control", "notebook"],
    "mug": ["mug", "bowl", "pot"],
    "desk_lamp": ["desk lamp", "microphone", "plant"],
    "sketchbook": ["open book", "notebook", "tray"],
    "bookshelf": ["bookshelf", "cabinet", "door"],
    "piano": ["electronic keyboard", "piano", "desk"],
    "piano_bench": ["bench", "stool", "table"],
    "easel": ["easel", "tripod", "ladder"],
    "easel_painting": ["painting", "canvas", "poster"],
    "rice_cooker": ["rice cooker", "kettle", "pot"],
    "side_table": ["side table", "stool", "chair"],
    "game_console": ["game console", "router", "box"],
    "controller": ["game controller", "gamepad", "phone"],
    "tv": ["television", "monitor", "picture frame"],
    "cabinet": ["cabinet", "drawer", "box"],
    "rug": ["rug", "carpet", "mat"],
    "plant_pot": ["potted plant", "plant", "tree"],
    "plant_hanging": ["hanging plant", "plant", "vine"],
    "basket": ["basket", "bowl", "bag"],
    "cat": ["cat", "cushion", "bread"],
}


def load():
    kw = dict(local_files_only=True)
    try:
        m = Sam3Model.from_pretrained(MODEL_DIR, dtype=torch.float16, **kw)
    except TypeError:
        m = Sam3Model.from_pretrained(MODEL_DIR, torch_dtype=torch.float16, **kw)
    return m.to("cuda").eval(), Sam3Processor.from_pretrained(MODEL_DIR, **kw)


def main():
    model, proc = load()
    rows = []
    for name, phrases in EXPECT.items():
        p = os.path.join(ASSETS, name + ".png")
        if not os.path.exists(p):
            print("[missing] %s" % name)
            continue
        im = Image.open(p).convert("RGB")
        W, H = im.size
        pv = proc(images=im, return_tensors="pt")["pixel_values"].to("cuda", dtype=torch.float16)
        with torch.no_grad():
            vision = model.get_vision_features(pixel_values=pv)
        scores = {}
        for ph in phrases:
            ti = proc(text=ph, return_tensors="pt")
            with torch.no_grad():
                o = model(vision_embeds=vision, input_ids=ti["input_ids"].to("cuda"),
                          attention_mask=ti["attention_mask"].to("cuda"))
            res = proc.post_process_instance_segmentation(o, threshold=0.2, mask_threshold=0.5,
                                                         target_sizes=[(H, W)])[0]
            ms, sc = res["masks"], res["scores"]
            best = 0.0
            if ms is not None:
                for k, mk in enumerate(ms):
                    arr = mk.detach().float().cpu().numpy() > 0.5
                    if arr.sum() > 300:
                        best = max(best, float(sc[k]))
            scores[ph] = round(best, 3)
        own = scores[phrases[0]]
        others = max(scores[p] for p in phrases[1:])
        ok = own >= 0.6 and own > others
        rows.append(dict(name=name, own_phrase=phrases[0], scores=scores, pass_=bool(ok)))
        print("%-15s %-22s own=%.3f  others=%s  %s" % (
            name, phrases[0], own, {p: scores[p] for p in phrases[1:]}, "OK" if ok else "CHECK"))
    with open(os.path.join(HERE, "verify_assets.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    bad = [r["name"] for r in rows if not r["pass_"]]
    print("\n%d/%d pass; needs review: %s" % (len(rows) - len(bad), len(rows), bad))


if __name__ == "__main__":
    main()
