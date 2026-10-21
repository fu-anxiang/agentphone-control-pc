#!/usr/bin/env python3
"""第三轮探测：input 其余动作、pw 动作集、fs 读写参数、pwscript 参数"""
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
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        return f"EXC {type(e).__name__}: {e}"
    j.pop("_ms", None)
    if j.get("ok") and isinstance(j.get("r"), dict):
        rr = j["r"]
        for k, v in list(rr.items()):
            if isinstance(v, str) and len(v) > 70:
                rr[k] = v[:40] + f"...({len(v)}B)"
        return json.dumps(rr, ensure_ascii=False)[:240]
    return f"ERR {j.get('e','?')[:110]}"


print("=== input 更多动作 ===")
for p in [
    {"action": "scroll", "dy": 120},
    {"action": "wheel", "delta": 120},
    {"action": "moveby", "dx": 10, "dy": 10},
    {"action": "move", "dx": 10, "dy": 10},
    {"action": "down", "button": "left"},
    {"action": "up", "button": "left"},
    {"action": "double_click"},
    {"action": "right_click"},
    {"action": "key", "key": "win"},
    {"action": "key", "keys": "ctrl+c"},
    {"action": "hotkey", "keys": ["ctrl", "c"]},
    {"action": "type", "text": ""},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:50]:52} -> {call('input', **p)}")

print("=== pw 更多动作 ===")
for p in [
    {"action": "click", "selector": "a"},
    {"action": "fill", "selector": "input", "value": "x"},
    {"action": "text", "selector": "h1"},
    {"action": "html"},
    {"action": "eval", "code": "document.title"},
    {"action": "count", "selector": "a"},
    {"action": "back"},
    {"action": "press", "key": "Enter"},
    {"action": "url"},
    {"action": "newpage"},
    {"action": "pages"},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:50]:52} -> {call('pw', **p)}")

print("=== fs 写/读 ===")
tmp = "C:/Users/24335/pcc-test.txt"
print("  write b64 ->", call("fs", action="write", path=tmp, b64="aGVsbG8gcGNj"))
print("  write text->", call("fs", action="write", path=tmp, text="hello text"))
print("  read      ->", call("fs", action="read", path=tmp))
print("  read b64  ->", call("fs", action="read", path=tmp, b64=True))
print("  rm        ->", call("fs", action="rm", path=tmp))
print("  unlink    ->", call("fs", action="delete", path=tmp))

print("=== pwscript ===")
print("  code kw   ->", call("pwscript", code="return 1+1"))
print("  1+1       ->", call("pwscript", js="1+1"))
print("  expr      ->", call("pwscript", expr="1+1"))
