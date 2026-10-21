#!/usr/bin/env python3
"""决定性验证 SendInput 打字：在浏览器页面里注入输入框 → 点它 → 打字 → 读回 value"""
import importlib.util
import json
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

FOCUS_PS = r"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class WinAct2 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  public static void Activate(IntPtr h) { if (IsIconic(h)) ShowWindow(h, 9); SetForegroundWindow(h); }
}
'@
$needle = 'NEEDLE'
$hit = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like "*$needle*" } | Select-Object -First 1
if (-not $hit) { 'NOTFOUND' } else { [WinAct2]::Activate($hit.MainWindowHandle) | Out-Null; 'FOCUSED: ' + $hit.MainWindowTitle }
"""


def sh(cmd):
    r = pcc.call("shell", cmd=cmd, timeout=120)
    return r.get("code"), (r.get("out") or "").strip(), (r.get("err") or "").strip()


def pw(**p):
    return pcc.call("pw", timeout=120, **p)


print("1) 聚焦 Edge")
print("  ", sh(FOCUS_PS.replace("NEEDLE", "Edge"))[1])

print("2) 打开测试页并注入输入框")
print("  goto:", pw(action="goto", url="https://example.com"))
print("  eval:", pw(action="eval", js="document.body.innerHTML="
      "'<h1 id=h>PCC TEST</h1><input id=q style=\"font-size:48px;width:90%;height:120px\">'"
      ";'injected'"))
print("  eval:", pw(action="eval", js="document.getElementById('q').focus();'focused'"))

print("3) 计算输入框在屏幕上的位置（用 getBoundingClientRect + 窗口坐标）")
RECT_PS = r"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public struct RECT2 { public int Left, Top, Right, Bottom; }
public class WinR2 { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT2 r); }
'@
$p = Get-Process | Where-Object { $_.MainWindowTitle -like "*Edge*" -and $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$r = New-Object RECT2
[WinR2]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
"$($r.Left),$($r.Top),$($r.Right),$($r.Bottom)"
"""
code, rect, err = sh(RECT_PS)
print("   Edge rect:", rect)
box = pw(action="eval", js="JSON.stringify(document.getElementById('q').getBoundingClientRect())")
print("   input rect:", box.get("result"))
try:
    L, T, R, B = [int(x) for x in rect.split(",")]
    br = json.loads(box.get("result") or "{}")
    # 页面在窗口内：算 client 区偏移（标题栏 ~ 0，Edge 有 tab 栏）
    vp = pw(action="eval", js="JSON.stringify({w:innerWidth,h:innerHeight,"
            "ox:window.screenX,oy:window.screenY})")
    print("   viewport:", vp.get("result"))
    vs = json.loads(vp.get("result") or "{}")
    cand_x = R + (br["x"] + br["width"] / 2) - vs["w"]
    cand_y = B + (br["y"] + br["height"] / 2) - vs["h"]
    print(f"   估算坐标: ({int(cand_x)}, {int(cand_y)})")
    pcc.call("input", action="click", x=int(cand_x), y=int(cand_y))
    time.sleep(0.3)
except Exception as e:
    print("   坐标估算失败:", e)

print("4) 打字（含中文）")
print("  ", pcc.call("input", action="type", text="hello-phone-123 中文测试"))

print("5) 读回输入框 value")
print("  value:", pw(action="eval", js="document.getElementById('q').value"))
print("  active:", pw(action="eval", js="document.activeElement && document.activeElement.id"))
