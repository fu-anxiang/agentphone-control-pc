#!/usr/bin/env python3
"""干净验证：可见记事本 → 抢前台 + 窗口内点击 → 打字（含中文）→ 截图裁剪 OCR 验证"""
import base64
import importlib.util
import subprocess
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

NEEDLE = "记事本"

print("1) 抢前台 + 在窗口正中点击（一次调用完成，避免 PowerShell 抢焦点）")
r = pcc.call("input", action="click_window", match=NEEDLE, fx=0.5, fy=0.55)
win = r.get("window") or {}
print("   ", win.get("title"), "foreground=", win.get("foreground"))

print("2) 打字（含中文）")
pcc.call("input", action="type", value="手机输入测试 PCC-OK 123")
time.sleep(1.0)

print("3) 截图并用 UIA 读出记事本正文")
UIA = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::NameProperty, 'NEEDLE_TITLE')
$w = $root.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
if (-not $w) { 'NOWIN'; exit 0 }
$edit = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,
  [System.Windows.Automation.Condition]::TrueCondition)
foreach ($e in $edit) {
  if ($e.Current.ControlType.ProgrammaticName -match 'Document|Edit') {
    try {
      $tp = $e.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
      'TXT>[' + $tp.DocumentRange.GetText(-1) + ']'
    } catch {}
  }
}
"""
# 先用 windows 列表拿到记事本的准确标题
titles = [w["title"] for w in (pcc.call("windows").get("windows") or []) if NEEDLE in w["title"]]
print("   记事本标题:", titles)
if titles:
    out = pcc.call("shell", cmd=UIA.replace("NEEDLE_TITLE", titles[0]), timeout=90)
    print("   UIA:", (out.get("out") or "").strip()[:300])

# 裁剪截图给人工看
shot = pcc.call("screenshot", quality=80, max_width=1600)
data = base64.b64decode(shot["b64"])
open("/workspace/shots/pc-typed.jpg", "wb").write(data)
print("   截图:", len(data), "字节 → /workspace/shots/pc-typed.jpg")
