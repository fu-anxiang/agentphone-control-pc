#!/usr/bin/env python3
"""第四轮：fs 写入参数名、click 按钮/次数、key 组合键、pw eval 参数名"""
import base64, json, urllib.request, urllib.parse

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
    if j.get("ok") and isinstance(j.get("r"), dict):
        rr = j["r"]
        for k, v in list(rr.items()):
            if isinstance(v, str) and len(v) > 60:
                rr[k] = v[:30] + f"...({len(v)}B)"
        return json.dumps(rr, ensure_ascii=False)[:220]
    return f"ERR {str(j.get('e'))[:100]}"


tmp = "C:/Users/24335/pcc-test.txt"
b64 = base64.b64encode(b"hello-from-pcc").decode()
print("=== fs write 参数名 ===")
for kw in [{"content": "aaa"}, {"data": "bbb"}, {"text": "ccc"}, {"b64": b64},
           {"base64": b64}, {"content_b64": b64}, {"bytes": b64}]:
    p = dict(action="write", path=tmp)
    p.update(kw)
    r = call("fs", **p)
    rd = call("fs", action="read", path=tmp)
    print(f"  {list(kw)[0]:12} write->{r[:90]:92} read->{rd[:80]}")

print("=== click 变体 ===")
for p in [
    {"action": "click", "button": "right"},
    {"action": "click", "button": "middle"},
    {"action": "click", "clicks": 2},
    {"action": "click", "n": 2},
    {"action": "click", "double": True},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:46]:48} -> {call('input', **p)}")

print("=== key 变体 ===")
for p in [
    {"action": "key", "key": "esc"},
    {"action": "key", "key": "ctrl+c"},
    {"action": "key", "key": "c", "mods": ["ctrl"]},
    {"action": "key", "key": "ctrl", "with": "c"},
    {"action": "key", "key": "enter"},
]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:46]:48} -> {call('input', **p)}")

print("=== pw eval 参数 ===")
for p in [{"action": "eval", "js": "document.title"},
          {"action": "eval", "expression": "1+1"},
          {"action": "eval", "code": "1+1", "js": "document.title"}]:
    print(f"  {json.dumps(p, ensure_ascii=False)[:50]:52} -> {call('pw', **p)}")
