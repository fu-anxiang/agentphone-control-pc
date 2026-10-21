#!/usr/bin/env python3
"""真实电脑端联调测试（直接在 Python 里调用接口，避开 shell 引号问题）"""
import importlib.util
import json
import os
import sys
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

FOCUS_PS = r"""
$ErrorActionPreference = 'Stop'
$sig = @'
using System;
using System.Runtime.InteropServices;
public class WinAct {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  public static void Activate(IntPtr h) {
    if (IsIconic(h)) ShowWindow(h, 9);
    SetForegroundWindow(h);
  }
}
'@
Add-Type -TypeDefinition $sig
$needle = 'TITLEPLACEHOLDER'
$hit = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$needle*" } | Select-Object -First 1
if (-not $hit) { Write-Output 'NOTFOUND' } else {
  [WinAct]::Activate($hit.MainWindowHandle) | Out-Null
  Write-Output ('FOCUSED: ' + $hit.MainWindowTitle)
}
"""


def shell(cmd):
    r = pcc.call("shell", cmd=cmd, timeout=120)
    return r.get("code"), (r.get("out") or "").strip(), (r.get("err") or "").strip()


def step(name, fn):
    t0 = time.time()
    try:
        r = fn()
        print(f"[OK  ] {name}  ({int((time.time()-t0)*1000)}ms)  {r}")
        return r
    except SystemExit:
        print(f"[DIE ] {name}")
        return None
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}: {e}")
        return None


print("=== 1. 窗口焦点（PowerShell Win32） ===")
code, o, e = shell(FOCUS_PS.replace("TITLEPLACEHOLDER", "记事本"))
print(f"  code={code} out={o!r} err={e[:200]!r}")

print("=== 2. 打字 + 截图验证 ===")
pcc.call("input", action="type", text="hello from phone 中文输入测试")
print("  typed ok")
r = pcc.call("screenshot")
b64 = r.get("b64") or ""
open("/workspace/shots/pc-after-type.jpg", "wb").write(
    __import__("base64").b64decode(b64))
print(f"  shot saved {os.path.getsize('/workspace/shots/pc-after-type.jpg')} bytes")

print("=== 3. 鼠标 move/click/scroll ===")
print("  move:", pcc.call("input", action="move", x=800, y=400).get("cursor"))
print("  click:", pcc.call("input", action="click", button="left", x=800, y=400).get("cursor"))
print("  scroll:", pcc.call("input", action="scroll", dy=-120).get("cursor"))

print("=== 4. 文件读写（fs 真实参数） ===")
tmp = "C:/Users/24335/pcc-test.txt"
print("  write:", pcc.call("fs", action="write", path=tmp, content="line1\nline2 中文\n"))
print("  read :", repr(pcc.call("fs", action="read", path=tmp).get("text")))
print("  list :", len(pcc.call("fs", action="list", path="C:/Users/24335").get("items") or []), "项")
print("  del  :", pcc.call("fs", action="delete", path=tmp))
