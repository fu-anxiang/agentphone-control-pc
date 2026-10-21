#!/usr/bin/env python3
"""定位电脑端桥脚本：找 python 进程命令行 + 常见目录"""
import importlib.util
import json

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

PS = r"""
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Select-Object ProcessId, @{n='cl';e={$_.CommandLine}} |
  ForEach-Object { "$($_.ProcessId)`t$($_.cl)" }
"""
r = pcc.call("shell", cmd=PS, timeout=60)
print("=== python 进程 ===")
print((r.get("out") or "").strip()[:2000] or (r.get("err") or "")[:500])
