#!/usr/bin/env python3
"""探测真实电脑端支持的 method / action 与参数（打印每个尝试的结果摘要）"""
import json, sys, urllib.request, urllib.parse, time

BASE = "https://pcrelay.pages.dev/api"
import os
ROOM = os.environ.get("PCC_ROOM", "请填电脑端打印的 Agent 令牌")
H = {"content-type": "application/json",
     "user-agent": "Mozilla/5.0 (Linux; Android 14) pcc/1.0",
     "accept": "application/json"}


def call(m, **p):
    url = f"{BASE}?room={urllib.parse.quote(ROOM)}"
    body = json.dumps({"m": m, "p": p}).encode()
    req = urllib.request.Request(url, data=body, headers=H)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            j = json.loads(r.read().decode())
    except Exception as e:
        return f"EXC {type(e).__name__}: {e}"
    j.pop("_ms", None)
    # 截断长字段
    for k, v in list(j.items()):
        if isinstance(v, str) and len(v) > 120:
            j[k] = v[:60] + f"...({len(v)}B)"
    return f"{int((time.time()-t0)*1000)}ms {json.dumps(j, ensure_ascii=False)[:300]}"


tests = []
for act in ["list", "read", "write", "cat", "get", "put", "mkdir", "stat", "ls_dir", "dir"]:
    tests.append(("fs", {"action": act, "path": "C:/Users/24335"}))
for m in ["windows", "list_windows", "focus", "app", "apps", "processes", "pw", "pwscript",
          "screenshot", "screen", "input", "mouse", "keyboard", "clip", "shell", "info", "help"]:
    tests.append((m, {}))

for m, p in tests:
    print(f"{m:14} {json.dumps(p, ensure_ascii=False)[:40]:42} -> {call(m, **p)}")
