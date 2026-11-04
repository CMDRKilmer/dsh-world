"""Assemble the layered bedroom PSD through PhotoCraft's MCP server (stdio)."""
import json, os, subprocess, sys, time

CLI = r"C:\Program Files\ArtCraft\PhotoCraft\photocraft-cli.exe"
LAYERS = r"C:\Users\kilsa\Desktop\code\dsh-world\assets\rooms\bedroom-anime-v1\layers"
WRITE_ROOT = r"C:\Users\kilsa\Desktop\code\dsh-world\assets"
PSD_REL = "rooms/bedroom-anime-v1/room-layered.psd"


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
                    raise RuntimeError(f"{method} failed: {msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(method)

    def tool(self, name, args, timeout=300):
        res = self.call("tools/call", {"name": name, "arguments": args}, timeout=timeout)
        content = res.get("content") or []
        text = next((c.get("text") for c in content if c.get("type") == "text"), None)
        if res.get("isError"):
            raise RuntimeError(f"{name} error: {text}")
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
    man = json.load(open(os.path.join(LAYERS, "manifest.json"), encoding="utf-8"))
    W, H = man["canvas"]
    m = Mcp(LAYERS, WRITE_ROOT)
    try:
        print("doc_new:", json.dumps(m.tool("doc_new", {"width": W, "height": H, "mode": "rgb",
                                                        "depth": 8, "background": "transparent",
                                                        "name": "bedroom-anime-v1"}))[:300])
        # room plate first (bottom), then objects back-to-front
        m.tool("doc_place", {"path": "room.png", "fit": False})
        m.tool("command_run", {"id": "layer.setProps", "params": {"name": "room"}})
        # a document may never drop below one layer, so the empty starter goes only after room.png exists
        state = m.tool("doc_inspect", {})
        for l in state.get("layers", []):
            if l.get("name") in ("Layer 1", "Background"):
                m.tool("command_run", {"id": "layer.delete", "params": {"layer": l["id"]}})
        placed = ["room"]
        for o in sorted(man["objects"], key=lambda o: -o["z"]):
            cx, cy = o["x"] + o["w"] / 2.0, o["y"] + o["h"] / 2.0
            m.tool("doc_place", {"path": o["file"], "fit": False, "center": [cx, cy]})
            m.tool("command_run", {"id": "layer.setProps", "params": {"name": o["name"]}})
            placed.append(o["name"])
        print("placed", len(placed), "layers")
        saved = m.tool("doc_save", {"path": PSD_REL}, timeout=600)
        print("doc_save:", json.dumps(saved)[:400])
        inspect = m.tool("doc_inspect", {})
        layers = inspect.get("layers", [])
        print("layers in saved doc:", len(layers))
        names = [l.get("name") for l in layers]
        print("top:", names[:4], "... bottom:", names[-3:])
        # flatten-export for verification
        flat = m.tool("doc_export", {"path": "rooms/bedroom-anime-v1/_verify_flat.png"}, timeout=600)
        print("export:", json.dumps(flat)[:200])
        print("placed order:", placed[:3], "...", placed[-3:])
    finally:
        m.close()


if __name__ == "__main__":
    main()
