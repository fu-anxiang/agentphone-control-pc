#!/usr/bin/env python3
"""协议探针 2：以 role=pc 连上 relay，收到请求后按指定格式回复，用来反推回复信封。"""
import asyncio, json, sys
import websockets

ROOM = sys.argv[1]
SHAPE = sys.argv[2] if len(sys.argv) > 2 else "r"
SECS = float(sys.argv[3]) if len(sys.argv) > 3 else 40
URL = f"wss://pcrelay.pages.dev/ws?role=pc&room={ROOM}"


def build(rid, out="PROBE_OUT"):
    r = {"out": out, "code": 0, "err": ""}
    if SHAPE == "r":
        return {"id": rid, "r": r}
    if SHAPE == "okr":
        return {"id": rid, "ok": True, "r": r}
    if SHAPE == "res":
        return {"id": rid, "res": r}
    if SHAPE == "flat":
        return {"id": rid, **r}
    return {"id": rid, "r": r}


async def main():
    async with websockets.connect(URL, ping_interval=20, max_size=None) as ws:
        print(f"connected shape={SHAPE}", flush=True)
        await ws.send(json.dumps({"t": "peer", "event": "join", "role": "pc"}))
        await ws.send(json.dumps({"t": "info", "w": 1080, "h": 1920}))

        async def serve():
            async for msg in ws:
                if isinstance(msg, bytes):
                    print(f"BIN {len(msg)}", flush=True)
                    continue
                print(f"REQ {msg}", flush=True)
                try:
                    j = json.loads(msg)
                except Exception:
                    continue
                if "id" in j and "m" in j:
                    reply = build(j["id"])
                    await ws.send(json.dumps(reply))
                    print(f"REPLY {json.dumps(reply)}", flush=True)

        t = asyncio.create_task(serve())
        await asyncio.sleep(SECS)
        t.cancel()


asyncio.run(main())
