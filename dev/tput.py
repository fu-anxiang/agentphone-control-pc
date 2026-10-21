#!/usr/bin/env python3
"""中继二进制帧吞吐测试：role=pc 连续发送 N 帧 30KB，测量时间。"""
import asyncio, json, sys, time
import websockets

ROOM, N, SIZE = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
URL = f"wss://pcrelay.pages.dev/ws?role=pc&room={ROOM}"


async def main():
    async with websockets.connect(URL, ping_interval=20, max_size=None) as ws:
        await ws.send(json.dumps({"t": "peer", "event": "join", "role": "pc"}))
        await ws.send(json.dumps({"t": "info", "w": 1280, "h": 800}))
        await asyncio.sleep(1)
        payload = b"\xff\xd8" + b"\x00" * (SIZE - 4) + b"\xff\xd9"
        t0 = time.time()
        for i in range(N):
            await ws.send(payload)
        dt = time.time() - t0
        print(f"sent {N} frames x {SIZE}B in {dt:.2f}s -> {N/dt:.1f} fps")
        await asyncio.sleep(2)


asyncio.run(main())
