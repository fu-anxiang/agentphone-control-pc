#!/usr/bin/env python3
"""协议探针：以 role=pc 连上 relay，打印它发来的每一条消息（用于反推 /api 的请求信封）。"""
import asyncio, json, sys, time
import websockets

ROOM = sys.argv[1] if len(sys.argv) > 1 else "probe-test"
URL = f"wss://pcrelay.pages.dev/ws?role=pc&room={ROOM}"
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 40


async def main():
    print(f"connecting {URL}", flush=True)
    async with websockets.connect(URL, ping_interval=20, max_size=None) as ws:
        print("connected", flush=True)
        # 先自报身份，模仿前端看到的 peer/join 与 info
        await ws.send(json.dumps({"t": "peer", "event": "join", "role": "pc"}))
        await ws.send(json.dumps({"t": "info", "w": 1080, "h": 1920}))

        async def drain():
            try:
                async for msg in ws:
                    if isinstance(msg, bytes):
                        print(f"[{time.strftime('%H:%M:%S')}] BIN {len(msg)} bytes", flush=True)
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] TXT {msg}", flush=True)
            except Exception as e:
                print("drain end:", e, flush=True)

        task = asyncio.create_task(drain())
        await asyncio.sleep(SECS)
        task.cancel()


asyncio.run(main())
