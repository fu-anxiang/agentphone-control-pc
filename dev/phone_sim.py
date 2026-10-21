#!/usr/bin/env python3
"""phone_sim.py —— 模拟手机投屏端：连 role=phone，打印收到的消息，统计画面帧。"""
import asyncio, json, sys, time
import websockets

ROOM = sys.argv[1]
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 15
SEND_INPUT = len(sys.argv) > 3 and sys.argv[3] == "input"
URL = f"wss://pcrelay.pages.dev/ws?role=phone&room={ROOM}"


async def main():
    frames = 0
    async with websockets.connect(URL, ping_interval=20, max_size=None) as ws:
        print(f"phone connected room={ROOM}", flush=True)

        async def pump():
            nonlocal frames
            async for msg in ws:
                if isinstance(msg, bytes):
                    frames += 1
                    if frames <= 2:
                        print(f"FRAME {len(msg)} bytes", flush=True)
                    await ws.send(json.dumps({"t": "ack"}))
                else:
                    print(f"TXT {msg[:200]}", flush=True)

        t = asyncio.create_task(pump())
        await asyncio.sleep(3)
        if SEND_INPUT:
            for ev in [{"t": "abs", "x": 0.5, "y": 0.5},
                       {"t": "click", "b": "left", "n": 1},
                       {"t": "text", "s": "你好"},
                       {"t": "key", "k": "enter"}]:
                await ws.send(json.dumps(ev))
                print(f"SENT {ev}", flush=True)
        await asyncio.sleep(max(0, SECS - 3))
        t.cancel()
    print(f"total frames={frames}", flush=True)


asyncio.run(main())
