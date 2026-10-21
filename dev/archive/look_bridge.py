#!/usr/bin/env python3
"""读取电脑端的桥源码，弄清 type/key/input 的真实实现"""
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

base = "C:/Users/24335/Documents/for phone/pcremote"
r = pcc.call("fs", action="list", path=base)
print("=== 目录 ===", r.get("path"))
for it in (r.get("items") or []):
    print(f"  {'DIR ' if it.get('dir') else '    '}{it.get('size'):>9}  {it.get('name')}")
