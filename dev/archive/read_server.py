#!/usr/bin/env python3
"""把电脑端 server.py 抓下来，看 type_text / send_combo / VK 的实现"""
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

p = "C:/Users/24335/Documents/for_phone/pcremote/server.py"
r = pcc.call("fs", action="read", path=p, max_bytes=400000)
body = r.get("text") or ""
open("/workspace/shots/pc_server_remote.py", "w", encoding="utf-8").write(body)
print("saved", len(body), "chars, truncated =", r.get("truncated"))
import re
for kw in ["def type_text", "def send_combo", "VK = ", "def move_px", "def move_abs", "def wheel"]:
    i = body.find(kw)
    print(f"\n----- {kw} @ {i} -----")
    if i >= 0:
        print(body[i:i + 700])
