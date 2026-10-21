#!/usr/bin/env python3
"""探测 input / pw / app / focus / fs 的真实参数名"""
import json, urllib.request, urllib.parse, time

BASE = "https://pcrelay.pages.dev/api"
import os
ROOM = os.environ.get("PCC_ROOM", "请填电脑端打印的 Agent 令牌")
H = {"content-type": "application/json",
     "user-agent": "Mozilla/5.0 (Linux; Android 14) pcc/1.0",
     "accept": "application/json"}


def call(m, **p):
    url = f"{BASE}?room={urllib.parse.quote(ROOM)}"
    req = urllib.request.Request(url, data=json.dumps({"m": m, "p": p}).encode(), headers=H)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        return f"EXC {type(e).__name__}: {e}"
    j.pop("_ms", None)
    for k, v in list(j.items()):
        if isinstance(v, str) and len(v) > 100:
            j[k] = v[:50] + f"...({len(v)}B)"
        if isinstance(v, dict):
            for k2, v2 in list(v.items()):
                if isinstance(v2, str) and len(v2) > 60:
                    v[k2] = v2[:30] + f"...({len(v2)}B)"
    return f"{int((time.time()-t0)*1000)}ms {json.dumps(j, ensure_ascii=False)[:260]}"


print("=== input 参数探测 ===")
for p in [
    {"action": "move", "x": 0.5, "y": 0.5},
    {"action": "move", "x": 960, "y": 540},
    {"action": "position"},
    {"action": "click", "button": "left"},
    {"action": "click", "x": 0.5, "y": 0.5},
    {"action": "wheel", "dy": 120},
    {"action": "type", "text": "hi"},
    {"action": "key", "key": "esc"},
    {"os": "move"},
    {"type": "move", "x": 0.5, "y": 0.5},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:52]:54} -> {call('input', **p)}")

print("=== pw 动作探测 ===")
for p in [
    {"action": "info"},
    {"action": "goto", "url": "https://example.com"},
    {"action": "title"},
    {"action": "screenshot"},
    {"action": "open", "url": "https://example.com"},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:52]:54} -> {call('pw', **p)}")

print("=== app 探测 ===")
for p in [
    {"action": "start", "target": "notepad.exe"},
    {"action": "list"},
    {"action": "start", "target": "https://example.com"},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:52]:54} -> {call('app', **p)}")

print("=== focus 探测 ===")
for p in [{"title": "记事本"}, {"title": "Edge"}]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:52]:54} -> {call('focus', **p)}")
