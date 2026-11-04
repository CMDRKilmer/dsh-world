"""Generate the bedroom furniture set one object at a time on a chroma-green backdrop.

Plan A (asset-first): every object is generated on its own, fully visible, with no cast
shadow and no baked lighting, so that global illumination can be added later in engine.
The green backdrop is a keying aid only; it is removed by cutout_assets.py.

Usage:  python gen_assets.py [--only name,name] [--seed N] [--size 1024]
"""
import argparse
import json
import os
import sys
import time
import urllib.request

SERVER = "http://127.0.0.1:8188"
OUT = r"D:\ComfyUI_windows_portable\ComfyUI\output"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)

STYLE = ("Modern Japanese anime background art style, clean confident lineart with slightly "
         "varied line weight, flat cel-shaded colour fills with a single flat tone per material "
         "plus at most one flat shadow tone, painterly detail in the material, rich but slightly "
         "desaturated palette, high production value theatrical anime film background.")

LIGHT = ("The object is lit by perfectly even neutral studio light coming from no particular "
         "direction: it casts no shadow on the background, no contact shadow, no ambient "
         "occlusion darkening, no rim light, no specular highlight, no colour bounce.")

GREEN = ("The object is photographed against a completely flat, uniform, fully saturated "
         "chroma-key green backdrop, pure RGB 0,255,0, the green fills every empty area of the "
         "frame edge to edge with no gradient, no shadow and no texture.")

NEG = ("nsfw, worst quality, watermark, text, signature, photorealistic, 3d render, pixel art, "
       "low resolution, blurry, oversaturated, chromatic aberration, distorted perspective, "
       "fisheye, cast shadow, drop shadow, contact shadow, shadow on the ground, ambient "
       "occlusion, rim light, backlight, glow, vignette, gradient background, floor, wall, "
       "room, scenery, furniture set, multiple objects, duplicate, cropped, cut off, out of "
       "frame, cluttered, green tint on the object, green reflection")

# name, description, view hint
OBJECTS = [
    ("bed",            "a low single bed with a light wooden frame, a thick mattress, a rumpled quilt and two mismatched pillows", "three-quarter front view"),
    ("desk",           "a long wooden writing desk with a wide flat rectangular top, a row of three drawers under the right side, straight tapered legs", "front view"),
    ("office_chair",   "an office chair with a cushioned seat, a curved backrest, a five-star swivel base with castors and a gas lift", "three-quarter front view"),
    ("monitor",        "a computer monitor with a thin dark bezel, a rectangular screen showing a calm desktop, and a small stand with a flat foot", "front view"),
    ("keyboard",       "a compact computer keyboard with rows of light keycaps and a slim dark case", "three-quarter top view"),
    ("mouse",          "a small rounded computer mouse with a scroll wheel and a thin cable", "three-quarter top view"),
    ("microphone",     "a studio condenser microphone in a shock mount on a black articulated boom arm with a desk clamp", "three-quarter front view"),
    ("mp3_player",     "a small rectangular MP3 player with a screen and a click wheel, with coiled white wired earbuds beside it", "three-quarter top view"),
    ("phone",          "a modern smartphone lying flat with a dark screen and rounded corners", "three-quarter top view"),
    ("mug",            "a ceramic mug with a handle, seen slightly from above", "three-quarter front view"),
    ("desk_lamp",      "an articulated desk lamp with a brass shade, a thin arm and a round weighted base", "three-quarter front view"),
    ("sketchbook",     "an open sketchbook with a spiral binding, blank cream pages and a pencil lying across it", "three-quarter top view"),
    ("bookshelf",      "a tall wooden bookshelf with five shelves packed with colourful book spines and a few small boxes", "front view"),
    ("piano",          "a black electronic keyboard piano on a folding metal stand, with a row of white and black keys and a small control panel", "three-quarter front view"),
    ("piano_bench",    "a small wooden piano bench with a padded top and four straight legs", "three-quarter front view"),
    ("easel",          "a wooden artist easel with three legs, an adjustable ledge and a top clamp, empty", "three-quarter front view"),
    ("easel_painting", "a half-finished landscape painting on a stretched canvas, warm hills and a pale sky, visible brush strokes", "front view"),
    ("rice_cooker",    "a white rice cooker with a rounded lid, a small control panel and a carrying handle", "three-quarter front view"),
    ("side_table",     "a small round wooden side table with three splayed legs", "three-quarter front view"),
    ("game_console",   "a small white game console, a flat rectangular box with a slot and a few ports", "three-quarter front view"),
    ("controller",     "a white game controller with two thumbsticks, a d-pad and four face buttons", "three-quarter front view"),
    ("tv",             "a small flat-screen television with a thin bezel on a short pedestal stand, dark screen", "front view"),
    ("cabinet",        "a low wooden cabinet with two doors, small round knobs and short legs", "front view"),
    ("rug",            "a woven oval rug with a simple geometric border pattern, seen from a low angle so it reads as a flat oval", "near-top view, flattened perspective"),
    ("plant_pot",      "a potted houseplant with broad green leaves in a terracotta pot", "three-quarter front view"),
    ("plant_hanging",  "a hanging planter with trailing vines cascading downward from a small pot and a hook", "front view"),
    ("basket",         "a woven wicker basket with a folded blanket inside", "three-quarter front view"),
    ("cat",            "a sleeping cat curled into a round ball with its tail wrapped around its body and its head tucked in", "three-quarter front view"),
]


def build_workflow(text, seed, size, prefix):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "moss_image_sft_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3.5_9b_w4a8_gptq.safetensors", "type": "moss_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae_small.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["2", 0]}},
        "6": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": size, "height": size, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["10", 0], "positive": ["4", 0], "negative": ["5", 0],
                                                  "latent_image": ["6", 0], "seed": seed, "steps": 25, "cfg": 2.5,
                                                  "sampler_name": "er_sde", "scheduler": "simple", "denoise": 1}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": prefix}},
        "10": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": "moss-anime-seinen.safetensors", "strength_model": 1}},
    }


def post(path, payload):
    req = urllib.request.Request(SERVER + path, data=json.dumps(payload).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get(path):
    try:
        with urllib.request.urlopen(SERVER + path, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--seed", type=int, default=20261104)
    ap.add_argument("--size", type=int, default=1024)
    args = ap.parse_args()

    todo = OBJECTS
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        todo = [o for o in OBJECTS if o[0] in want]

    log = open(os.path.join(HERE, "gen_assets.log"), "a", encoding="utf-8")
    def say(msg):
        print(msg, flush=True)
        log.write(msg + "\n"); log.flush()

    say("=== %s  %d objects ===" % (time.strftime("%Y-%m-%d %H:%M:%S"), len(todo)))
    ids = {}
    for i, (name, desc, view) in enumerate(todo):
        text = ("A single isolated %s, shown on its own as a standalone asset for a 2D game "
                "background. %s, camera at eye level, the whole object fully visible with "
                "generous empty margin on every side, centred in the frame, nothing else in the "
                "image. %s %s %s" % (desc, view.capitalize(), LIGHT, GREEN, STYLE))
        seed = args.seed + i * 7919
        try:
            res = post("/prompt", {"prompt": build_workflow(text, seed, args.size, "aset_" + name),
                                   "client_id": "gen-" + name})
            ids[name] = res["prompt_id"]
            say("[queued] %-15s seed=%d" % (name, seed))
        except Exception as e:
            say("[FAIL]   %-15s %s" % (name, e))

    pending = dict(ids)
    t0 = time.time()
    done = {}
    while pending and time.time() - t0 < 7200:
        time.sleep(6)
        for name, pid in list(pending.items()):
            h = get("/history/" + pid)
            if pid in h:
                imgs = h[pid].get("outputs", {}).get("9", {}).get("images", [])
                if imgs:
                    done[name] = imgs[0]["filename"]
                    say("[done]   %-15s %s" % (name, imgs[0]["filename"]))
                else:
                    say("[EMPTY]  %-15s no image" % name)
                del pending[name]
        if pending:
            say("  ... %d pending, %.0fs elapsed" % (len(pending), time.time() - t0))

    with open(os.path.join(HERE, "gen_assets.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": args.seed, "size": args.size, "files": done}, f, indent=1)
    say("=== finished %d/%d in %.0fs ===" % (len(done), len(todo), time.time() - t0))


if __name__ == "__main__":
    main()
