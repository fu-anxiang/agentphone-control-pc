#!/usr/bin/env python3
"""用 UI Automation 读取记事本里的真实文本，确认打字是否送达"""
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

UIA_PS = r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$procs = Get-Process notepad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 }
if (-not $procs) { 'NONOTEPAD'; exit 0 }
$p = $procs[0]
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $p.Id)
$win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if (-not $win) { 'NOWINDOW'; exit 0 }
$docCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Document)
$doc = $win.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $docCond)
if (-not $doc) { 'NODOC'; exit 0 }
$tp = $doc.GetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern)
'TEXT>>>' + $tp.DocumentRange.GetText(-1) + '<<<END'
"""

r = pcc.call("shell", cmd=UIA_PS, timeout=120)
print("code:", r.get("code"))
out = (r.get("out") or "").strip()
print("out:", out[:800])
err = (r.get("err") or "").strip()
if err:
    print("err:", err[:600])
