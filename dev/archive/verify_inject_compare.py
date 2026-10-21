#!/usr/bin/env python3
"""对比两种注入方式：电脑端 bridge 的 SendInput vs PowerShell SendKeys，
   判断是「桥的实现问题」还是「整机会话不接受键鼠注入」"""
import importlib.util
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)


def pw(**p):
    return pcc.call("pw", timeout=120, **p)


def sh(cmd):
    r = pcc.call("shell", cmd=cmd, timeout=120)
    return r.get("code"), (r.get("out") or "").strip(), (r.get("err") or "").strip()[:300]


# 干净页面 + 输入框
pw(action="goto", url="https://example.com")
pw(action="eval", js="document.body.innerHTML="
   "'<h1>PCC TEST</h1><input id=q style=\"font-size:48px;width:90%;height:120px\">';'ok'")
print("focus:", pcc.call("focus", match="Edge").get("window", {}).get("foreground"))

SENDKEYS = r"""
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.SendKeys]::SendWait('from-sendkeys')
'ok'
"""
print("PowerShell SendKeys:", sh(SENDKEYS))
time.sleep(1.0)

print("--- 结果 ---")
print("bridge SendInput 打字前 value:", pw(action="eval", js="document.getElementById('q').value"))
print("前台窗口:", sh(r"""
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Runtime.InteropServices;
public class FG {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowTextW(IntPtr h, StringBuilder s, int n);
}
'@
$h = [FG]::GetForegroundWindow()
$sb = New-Object System.Text.StringBuilder 512
[FG]::GetWindowTextW($h, $sb, 512) | Out-Null
$sb.ToString()
""")[1])

print("再试 bridge 打字:")
pcc.call("input", action="type", value="via-bridge")
time.sleep(1.0)
print("value 最终:", pw(action="eval", js="document.getElementById('q').value"))
print("是否仍在输入框:", pw(action="eval", js="document.activeElement && document.activeElement.id"))
