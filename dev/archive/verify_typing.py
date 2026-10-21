#!/usr/bin/env python3
"""验证打字是否真的进了记事本：取窗口矩形 → 裁剪截图对应区域 → 放大 OCR"""
import base64
import importlib.util
import json

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

RECT_PS = r"""
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public struct RECT { public int Left, Top, Right, Bottom; }
public class WinR {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
}
'@
$p = Get-Process notepad -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { 'NOTFOUND' } else {
  $r = New-Object RECT
  [WinR]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
  "$($r.Left),$($r.Top),$($r.Right),$($r.Bottom)"
}
"""
r = pcc.call("shell", cmd=RECT_PS, timeout=60)
print("rect:", (r.get("out") or "").strip(), (r.get("err") or "")[:200])
out = (r.get("out") or "").strip()
if not out or out == "NOTFOUND":
    raise SystemExit("no notepad window")

L, T, R, B = [int(x) for x in out.split(",")]
shot = pcc.call("screenshot")
data = base64.b64decode(shot.get("b64") or "")
open("/workspace/shots/pc-notepad-full.jpg", "wb").write(data)

from PIL import Image, ImageOps
import subprocess
im = Image.open("/workspace/shots/pc-notepad-full.jpg")
W, H = im.size
print("shot:", W, H, "window:", L, T, R, B)
sx, sy = W / 3840.0, H / 2160.0
box = (int(L * sx), int(T * sy), int(R * sx), int(B * sy))
print("crop box:", box)
part = im.crop(box).convert("L")
part = ImageOps.autocontrast(part)
part = part.resize((part.width * 2, part.height * 2), Image.LANCZOS)
part.save("/workspace/shots/pc-notepad-crop.png")
subprocess.run(["tesseract", "/workspace/shots/pc-notepad-crop.png", "/tmp/np",
                "-l", "chi_sim", "--psm", "6"], capture_output=True)
txt = open("/tmp/np.txt", encoding="utf-8", errors="replace").read()
print("=== 记事本窗口 OCR ===")
print("\n".join([l for l in txt.splitlines() if l.strip()][:15]))
