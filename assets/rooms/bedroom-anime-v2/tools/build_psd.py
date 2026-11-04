"""Assemble the layered bedroom PSD through PhotoCraft's MCP server (stdio).

Same transport as v1 (newline-delimited JSON-RPC over the CLI's stdin/stdout), but the layer
stack is built from manifest.json's z order so the file always matches the composite.
"""
import json
import os
import shutil
import subprocess
import sys
import time

CLI = r"C:\Program Files\ArtCraft\PhotoCraft\photocraft-cli.exe"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOM = os.path.dirname(HERE)
ASSETS_ROOT = os.path.dirname(os.path.dirname(ROOM))       # assets/
SHELL = os.path.join(ROOM, "shell_graded.png")
PSD_REL = "rooms/bedroom-anime-v2/room-layered.psd"
FLAT_REL = "rooms/bedroom-anime-v2/_verify_flat.png"


class Mcp:
    def __init__(self, read_root, write_root):
        self.p = subprocess.Popen(
            [CLI, "mcp", "--automation-read-root", read_root, "--automation-write-root", write_root],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, encoding="utf-8")
        self.id = 0
        self.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                 "clientInfo": {"name": "dsh-layer-builder", "version": "1.0"}})
        self.notify("notifications/initialized", {})

    def _send(self, obj):
        self.p.stdin.write(json.dumps(obj) + "\n")
        self.p.stdin.flush()

    def notify(self, method, params):
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def call(self, method, params, timeout=300):
        self.id += 1
        mid = self.id
        self._send({"jsonrpc": "2.0", "id": mid, "method": method, "params": params})
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("mcp server closed stdout")
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s failed: %s" % (method, msg["error"]))
                return msg.get("result", {})
        raise TimeoutError(method)

    def tool(self, name, args, timeout=300):
        res = self.call("tools/call", {"name": name, "arguments": args}, timeout=timeout)
        content = res.get("content") or []
        text = next((c.get("text") for c in content if c.get("type") == "text"), None)
        if res.get("isError"):
            raise RuntimeError("%s error: %s" % (name, text))
        try:
            return json.loads(text)
        except Exception:
            return text

    def close(self):
        self.p.terminate()
        try:
            self.p.wait(10)
        except Exception:
            self.p.kill()


def main():
    man = json.load(open(os.path.join(ROOM, "manifest.json"), encoding="utf-8"))
    W, H = man["canvas"]

    # PhotoCraft only reads inside its read-root, so the shell comes in as a local copy.
    # manifest.json records which plate was composed on, and the PSD must use the same one.
    shell_local = os.path.join(ROOM, "shell.png")
    shutil.copyfile(os.path.join(ROOM, man.get("shell", "shell.png")), shell_local)

    m = Mcp(ROOM, ASSETS_ROOT)
    try:
        print("doc_new:", json.dumps(m.tool("doc_new", {
            "width": W, "height": H, "mode": "rgb", "depth": 8,
            "background": "transparent", "name": "bedroom-anime-v2"}))[:200])

        # bottom plate: the empty room shell
        m.tool("doc_place", {"path": "shell.png", "fit": False})
        m.tool("command_run", {"id": "layer.setProps", "params": {"name": "room"}})
        state = m.tool("doc_inspect", {})
        for l in state.get("layers", []):
            if l.get("name") in ("Layer 1", "Background"):
                m.tool("command_run", {"id": "layer.delete", "params": {"layer": l["id"]}})

        # Objects back to front: the last one placed must end up topmost.
        # The layer files are already canvas-sized, so they go in with no offset at all --
        # passing a center would move the whole 1536x864 plate, not the object inside it.
        order = sorted(man["objects"], key=lambda o: (o["z"], o["order"]))
        for o in order:
            m.tool("doc_place", {"path": "layers/" + o["file"], "fit": False})
            m.tool("command_run", {"id": "layer.setProps", "params": {"name": o["name"]}})

        saved = m.tool("doc_save", {"path": PSD_REL}, timeout=900)
        print("doc_save:", json.dumps(saved)[:300])

        inspect = m.tool("doc_inspect", {})
        layers = inspect.get("layers", [])
        names = [l.get("name") for l in layers]
        print("layers in saved doc:", len(layers))
        print("top 5:", names[:5])
        print("bottom 3:", names[-3:])

        flat = m.tool("doc_export", {"path": FLAT_REL}, timeout=900)
        print("export:", json.dumps(flat)[:200])
    finally:
        m.close()

    # flatten must equal the composite we made with PIL
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(os.path.join(ROOM, "room.png")).convert("RGB")).astype(np.int16)
    b = np.asarray(Image.open(os.path.join(ASSETS_ROOT, FLAT_REL)).convert("RGB")).astype(np.int16)
    if a.shape != b.shape:
        print("SHAPE MISMATCH", a.shape, b.shape)
    else:
        d = np.abs(a - b)
        print("flatten vs room.png: max_abs_diff=%d  differing_px=%d" % (
            d.max(), int((d.max(axis=2) > 2).sum())))


if __name__ == "__main__":
    main()
