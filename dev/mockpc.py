#!/usr/bin/env python3
"""
mockpc.py —— 测试用的“电脑端 agent_bridge”
在手机(或任意机器)上冒充电脑连上中继，用来验证 pcc 客户端与协议。

    python3 mockpc.py <room> [秒数]
"""
import asyncio, base64, io, json, os, platform, socket, subprocess, sys, time
import websockets
from PIL import Image, ImageDraw

ROOM = sys.argv[1] if len(sys.argv) > 1 else "mock-room"
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 60
URL = f"wss://pcrelay.pages.dev/ws?role=pc&room={ROOM}"

W, H = 1280, 800


def shot_jpeg():
    im = Image.new("RGB", (W, H), (24, 32, 44))
    d = ImageDraw.Draw(im)
    d.rectangle([40, 40, W - 40, H - 40], outline=(60, 120, 200), width=3)
    d.text((70, 80), "MOCK PC SCREEN", fill=(230, 240, 250))
    d.text((70, 120), time.strftime("%Y-%m-%d %H:%M:%S"), fill=(150, 200, 255))
    d.text((70, 160), f"room={ROOM}", fill=(150, 200, 255))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=70)
    return buf.getvalue()


def handle(m, p):
    if m == "info":
        return {"host": socket.gethostname(), "os": platform.platform(),
                "user": os.environ.get("USER", "?"), "w": W, "h": H, "mock": True}
    if m == "ping":
        return {"pong": time.time()}
    if m == "shell":
        cmd = p.get("cmd", "")
        r = subprocess.run(["/bin/bash", "-lc", cmd], capture_output=True, text=True, timeout=60)
        return {"code": r.returncode, "out": r.stdout, "err": r.stderr}
    if m == "screenshot":
        return {"b64": base64.b64encode(shot_jpeg()).decode(), "w": W, "h": H}
    if m == "input":
        return {"ok": True, "echo": p}
    if m == "windows":
        return {"items": [{"title": "Mock Window", "pid": 1}]}
    if m == "fs":
        act = p.get("action")
        path = p.get("path", ".")
        if act == "ls":
            return {"items": [{"name": n, "size": os.path.getsize(os.path.join(path, n)) if os.path.isfile(os.path.join(path, n)) else 0}
                              for n in os.listdir(path)]}
        if act == "read":
            data = open(path, "rb").read()
            if p.get("b64"):
                return {"b64": base64.b64encode(data).decode(), "size": len(data)}
            return {"text": data.decode("utf-8", "replace")}
    if m == "clip":
        return {"text": "(mock clipboard)"}
    return {"err": f"mock: 未知方法 {m}", "code": -1}


async def main():
    async with websockets.connect(URL, ping_interval=20, max_size=None) as ws:
        print(f"mock connected room={ROOM}", flush=True)
        await ws.send(json.dumps({"t": "peer", "event": "join", "role": "pc"}))
        await ws.send(json.dumps({"t": "info", "w": W, "h": H}))

        async def pump():
            async for msg in ws:
                if isinstance(msg, bytes):
                    continue
                try:
                    j = json.loads(msg)
                except Exception:
                    continue
                if "m" in j and "id" in j:
                    t0 = time.time()
                    try:
                        r = handle(j["m"], j.get("p") or {})
                    except Exception as e:
                        r = {"err": f"{type(e).__name__}: {e}", "code": -1}
                    r["_ms"] = int((time.time() - t0) * 1000)
                    await ws.send(json.dumps({"id": j["id"], "r": r}))
                    print(f"REQ {j['m']} {json.dumps(j.get('p'))[:120]} -> {int(r['_ms'])}ms", flush=True)
                elif j.get("t") == "ack":
                    continue
                else:
                    print(f"EVT {msg[:120]}", flush=True)

        t = asyncio.create_task(pump())
        await asyncio.sleep(SECS)
        t.cancel()


asyncio.run(main())
