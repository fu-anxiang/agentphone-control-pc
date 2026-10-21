#!/usr/bin/env python3
"""交互验证：打开记事本 → 点击窗口 → 打字 → Ctrl+A 全选 → 覆盖打字 → OCR 校验 → 关闭"""
import base64
import importlib.util
import subprocess
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

def sh(cmd):
    r = pcc.call("shell", cmd=cmd, timeout=120)
    return (r.get("out") or "").strip(), (r.get("err") or "").strip()[:200]

print("1) 启动记事本")
r = pcc.call("app", action="start", target="notepad.exe")
pid = r.get("pid")
print("   pid =", pid)
time.sleep(2.5)

print("2) 抢前台 + 窗口内点击（一次调用）")
r = pcc.call("input", action="click_window", match="记事本", fx=0.5, fy=0.6)
print("   ", (r.get("window") or {}).get("title"), "fg=", (r.get("window") or {}).get("foreground"))

print("3) 打字 AAA-111")
pcc.call("input", action="type", value="AAA-111")
time.sleep(0.6)

print("4) Ctrl+A 全选")
pcc.call("input", action="key", key="a", mods=["ctrl"])
time.sleep(0.4)

print("5) 覆盖打字 BBB-中文-222")
pcc.call("input", action="type", value="BBB-中文-222")
time.sleep(0.8)

print("6) 截图 + OCR")
shot = pcc.call("screenshot", quality=85, max_width=1600)
open("/workspace/shots/combo.jpg", "wb").write(base64.b64decode(shot["b64"]))
from PIL import Image, ImageOps
im = Image.open("/workspace/shots/combo.jpg")
sx, sy = im.size[0] / 3840.0, im.size[1] / 2160.0
# 记事本窗口先拿一下矩形
rect, _ = sh(r"""
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public struct RR { public int L,T,R,B; }
public class WG { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RR r); }
'@
$p = Get-Process notepad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if ($p) { $r = New-Object RR; [WG]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null; "$($r.L),$($r.T),$($r.R),$($r.B)" } else { 'NA' }
""")
print("   窗口矩形:", rect)
if rect and rect != "NA":
    L, T, R, B = [int(x) for x in rect.split(",")]
    box = (int(L * sx), int(T * sy), int(R * sx), min(int(B * sy), int((T + 700) * sy)))
    part = im.crop(box).convert("L")
    part = ImageOps.autocontrast(part)
    part = part.resize((part.width * 3, part.height * 3), Image.LANCZOS)
    part.save("/tmp/combo.png")
    subprocess.run(["tesseract", "/tmp/combo.png", "/tmp/combo", "-l", "chi_sim+eng",
                    "--psm", "6"], capture_output=True)
    txt = open("/tmp/combo.txt", encoding="utf-8", errors="replace").read()
    print("   OCR:", " | ".join([l.strip() for l in txt.splitlines() if l.strip()][:6]))
    print("   含 BBB:", "BBB" in txt, " 含 AAA:", "AAA" in txt)

print("7) 关闭记事本")
if pid:
    try:
        pcc.call("app", action="kill", pid=pid)
        print("   已结束 pid", pid)
    except SystemExit:
        print("   进程已退出")
