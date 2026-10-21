#!/usr/bin/env python3
"""看清当前桌面：窗口列表 + 前台窗口 + 截图"""
import base64
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

for w in pcc.call("windows").get("windows") or []:
    print(f"  {w['hwnd']:>9} pid={w['pid']:<7} {w['title']}")

PS = r"""
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class FgWin {
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@
$h = [FgWin]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 512
[FgWin]::GetWindowTextW($h, $sb, 512) | Out-Null
$pid = 0
[FgWin]::GetWindowThreadProcessId($h, [ref]$pid) | Out-Null
$p = Get-Process -Id $pid -ErrorAction SilentlyContinue
"hwnd=$h title=$($sb.ToString()) pid=$pid name=$($p.ProcessName)"
"""
r = pcc.call("shell", cmd=PS, timeout=60)
print("前台:", (r.get("out") or "").strip(), (r.get("err") or "")[:200])

shot = pcc.call("screenshot", quality=70, max_width=1600)
open("/workspace/shots/pc-now.jpg", "wb").write(base64.b64decode(shot["b64"]))
print("截图已存 /workspace/shots/pc-now.jpg")
