#!/usr/bin/env python3
"""按行切图并放大 OCR（用于精确读取随机令牌/URL）"""
import sys, os, subprocess
from PIL import Image, ImageOps

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/lines"
lang = sys.argv[3] if len(sys.argv) > 3 else "eng"
os.makedirs(out, exist_ok=True)

im = Image.open(src).convert("L")
w, h = im.size
print(f"size {w}x{h}")
n = 12
step = h // n
for i in range(n):
    top = i * step
    bot = min(h, (i + 1) * step + int(step * 0.25))
    part = im.crop((0, top, w, bot))
    part = ImageOps.autocontrast(part)
    pw, ph = part.size
    s = max(1.0, 2000 / pw)
    part = part.resize((int(pw * s), int(ph * s)), Image.LANCZOS)
    p = os.path.join(out, f"l{i:02d}.png")
    part.save(p)
    subprocess.run(["tesseract", p, p[:-4], "-l", lang, "--psm", "6"], capture_output=True)
    txt = open(p[:-4] + ".txt", encoding="utf-8", errors="replace").read().strip()
    if txt:
        print(f"\n== [{i}] y={top}-{bot} ==")
        print(txt)
