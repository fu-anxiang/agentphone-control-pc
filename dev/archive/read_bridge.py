#!/usr/bin/env python3
"""读取电脑端 agent_bridge.py 源码，弄清 input.type / key / scroll 的真实实现"""
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

base = "C:/Users/24335/Documents/for_phone/pcremote"
r = pcc.call("fs", action="list", path=base)
print("=== 目录 ===", r.get("path"))
for it in (r.get("items") or []):
    print(f"  {'DIR ' if it.get('dir') else '    '}{str(it.get('size')):>9}  {it.get('name')}")

target = base + "/agent_bridge.py"
try:
    t = pcc.call("fs", action="read", path=target)
    body = t.get("text") or ""
    print(f"\n=== agent_bridge.py ({len(body)} 字符, truncated={t.get('truncated')}) ===")
    open("/workspace/shots/pc_bridge_remote.py", "w", encoding="utf-8").write(body)
    print("已保存 /workspace/shots/pc_bridge_remote.py")
except SystemExit:
    print("读取失败")
