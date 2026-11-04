"""Check the composed room with SAM 3: does each placed object actually read as itself?

For every object in manifest.json we ask SAM 3 for its concept on the finished composite and
compare the best instance with the layer we placed. Two failures the layer files alone cannot
show:

  * the object is drawn but unrecognisable at this size or in this context (low score)
  * the object is drawn somewhere other than where the manifest says (centroid offset)

Reported per object: sam score, IoU with the placed mask, centroid offset in px.
"""
import json
import os
import sys

import numpy as np
import torch
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
MAN = os.path.join(ROOM, "manifest.json")

PHRASES = {
    "basket": ["wicker basket", "basket"],
    "bed": ["bed", "bedroom bed"],
    "bookshelf": ["bookshelf", "bookcase"],
    "cabinet": ["cabinet", "chest of drawers"],
    "cat": ["cat", "sleeping cat"],
    "controller": ["game controller", "gamepad"],
    "desk": ["desk", "writing desk"],
    "desk_lamp": ["desk lamp", "table lamp"],
    "easel": ["easel", "wooden easel"],
    "easel_painting": ["painting on an easel", "canvas painting"],
    "game_console": ["game console", "video game console"],
    "keyboard": ["computer keyboard", "keyboard"],
    "microphone": ["microphone", "condenser microphone"],
    "monitor": ["computer monitor", "computer screen"],
    "mouse": ["computer mouse", "mouse"],
    "mp3_player": ["mp3 player", "portable music player"],
    "mug": ["mug", "coffee mug"],
    "office_chair": ["office chair", "desk chair"],
    "phone": ["smartphone", "mobile phone"],
    "piano": ["electronic keyboard piano", "synthesizer keyboard"],
    "piano_bench": ["piano bench", "bench"],
    "plant_hanging": ["hanging plant", "hanging vine"],
    "plant_pot": ["potted plant", "houseplant"],
    "rice_cooker": ["rice cooker", "electric cooker"],
    "rug": ["rug", "carpet"],
    "side_table": ["side table", "small table"],
    "sketchbook": ["sketchbook", "open sketchbook"],
    "tv": ["television", "small tv"],
}


def load():
    from transformers import Sam3Model, Sam3Processor
    from huggingface_hub import snapshot_download
    path = snapshot_download("bodhicitta/sam3", cache_dir=r"C:\Users\kilsa\.cache\dsh-models\sam3")
    proc = Sam3Processor.from_pretrained(path)
    model = Sam3Model.from_pretrained(path, dtype=torch.float16).to("cuda").eval()
    return model, proc


def run_concept(model, proc, vision, phrase, H, W):
    ti = proc(text=phrase, return_tensors="pt")
    with torch.no_grad():
        out = model(vision_embeds=vision,
                    input_ids=ti["input_ids"].to("cuda"),
                    attention_mask=ti["attention_mask"].to("cuda"))
    res = proc.post_process_instance_segmentation(
        out, threshold=0.2, mask_threshold=0.5, target_sizes=[(H, W)])[0]
    masks = [m.detach().float().cpu().numpy() > 0.5 for m in res["masks"]]
    scores = [float(s) for s in res["scores"]]
    return masks, scores


def main():
    man = json.load(open(MAN, encoding="utf-8"))
    room = Image.open(os.path.join(ROOM, "room.png")).convert("RGB")
    W, H = man["canvas"]
    model, proc = load()
    print("model loaded", flush=True)

    pv = proc(images=room, return_tensors="pt")["pixel_values"].to("cuda", dtype=torch.float16)
    with torch.no_grad():
        vision = model.get_vision_features(pixel_values=pv)

    results = []
    for o in sorted(man["objects"], key=lambda o: (o["z"], o["order"])):
        name = o["name"]
        lay = np.asarray(Image.open(os.path.join(ROOM, "layers", o["file"])).convert("RGBA"))[..., 3] > 127
        ys, xs = np.where(lay)
        if len(ys) == 0:
            results.append(dict(name=name, ok=False, error="empty layer"))
            continue
        cx, cy = float(xs.mean()), float(ys.mean())
        # A concept with several phrases must be judged on its best phrase, not on whichever
        # instance happens to overlap the layer most: a tall bookcase that a piano cuts in half
        # yields one high-IoU fragment with a weak score and one confident whole with a lower
        # IoU, and picking by IoU alone reports the fragment. Acceptance is therefore "some
        # phrase recognises this object here" -- score >= 0.5 and IoU >= 0.35 on the same
        # instance -- while the reported row stays the strongest such instance.
        cands = []
        for phrase in PHRASES.get(name, [name.replace("_", " ")]):
            masks, scores = run_concept(model, proc, vision, phrase, H, W)
            for k, m in enumerate(masks):
                if m.sum() < 200:
                    continue
                iou = float((m & lay).sum() / max(1, (m | lay).sum()))
                my, mx = np.where(m)
                off = float(np.hypot(mx.mean() - cx, my.mean() - cy))
                cands.append(dict(phrase=phrase, score=round(float(scores[k]), 3),
                                  iou=round(iou, 3), offset=round(off, 1), area=int(m.sum())))
        if not cands:
            results.append(dict(name=name, ok=False, error="no instance above 200px"))
            print("%-15s NO INSTANCE" % name, flush=True)
            continue
        passed = [c for c in cands if c["iou"] >= 0.35 and c["score"] >= 0.5]
        best = max(passed or cands, key=lambda c: (c["score"], c["iou"]))
        best.update(name=name, layer_area=int(lay.sum()), cx=round(cx, 1), cy=round(cy, 1),
                    ok=bool(passed), n_phrases=len(cands))
        results.append(best)
        print("%-15s %-28s score %.2f iou %.2f off %5.1f area %6d/%6d %s" % (
            name, best["phrase"], best["score"], best["iou"], best["offset"],
            best["area"], best["layer_area"], "ok" if best["ok"] else "CHECK"), flush=True)

    ok = sum(1 for r in results if r.get("ok"))
    print("\n%d/%d objects found where placed" % (ok, len(results)))
    with open(os.path.join(ROOM, "verify_room.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)


if __name__ == "__main__":
    main()
