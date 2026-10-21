#!/usr/bin/env python3
"""摸清电脑端当前运行状态：守护进程、两个通道、日志、自启项、电源设置"""
import importlib.util
import json

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

BASE = "C:/Users/24335/Documents/for_phone/pcremote"


def sh(cmd, timeout=60):
    r = pcc.call("shell", cmd=cmd, timeout=timeout)
    return r.get("code"), (r.get("out") or "").strip(), (r.get("err") or "").strip()


print("=== 1. pcremote 相关进程 ===")
c, o, e = sh(r"""Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Where-Object { $_.CommandLine -match 'pcremote' } |
  ForEach-Object { "$($_.ProcessId)`t$($_.CommandLine)" }""")
print(o or "(无)")

print("\n=== 2. 守护锁文件 ===")
c, o, e = sh(f"Get-Content -Raw '{BASE}/.supervisor.pid' -ErrorAction SilentlyContinue; "
             f"Get-Content -Raw '{BASE}/.supervisor.lock' -ErrorAction SilentlyContinue")
print(repr(o))

print("\n=== 3. logs 目录 ===")
r = pcc.call("fs", action="list", path=f"{BASE}/logs")
for it in r.get("items") or []:
    print(f"  {it.get('size'):>9}  {it.get('name')}")

print("\n=== 4. 自启项 ===")
c, o, e = sh(r"[Environment]::GetFolderPath('Startup')")
startup = o
print("  Startup 目录:", startup)
c, o, e = sh(f"Get-ChildItem -LiteralPath '{startup}' -Filter '*.lnk' | Select-Object -ExpandProperty Name")
print("  启动项:", o or "(无)")

print("\n=== 5. 电源/锁屏设置 ===")
c, o, e = sh(r"""powercfg /q SCHEME_CURRENT SUB_NONE CONSOLELOCK 2>$null | Select-String '当前|Current' | Select-Object -First 3
"--- timeout:"
powercfg /query SCHEME_CURRENT SUB_VIDEO VIDEOIDLE 2>$null | Select-String '当前交流|Current AC' | Select-Object -First 1
"ScreenSaveActive=" + (Get-ItemProperty 'HKCU:\Control Panel\Desktop' -Name ScreenSaveActive -ErrorAction SilentlyContinue).ScreenSaveActive""")
print(o or e[:300])

print("\n=== 6. 局域网 IP / 监听端口 ===")
c, o, e = sh(r"""(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notmatch '^(127\.|169\.254\.)' }).IPAddress -join ','
"--- 8765:"
(Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count""")
print(o)
