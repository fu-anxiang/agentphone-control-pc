#!/usr/bin/env python3
"""把长截图切成带重叠的横向条带并放大，逐条 OCR，输出到指定目录。
用法: bands.py <图片> <输出txt目录> [条带数] [语言]
"""
import sys, os, subprocess
from PIL import Image, ImageOps, ImageEnhance

src = sys.argv[1]
out_dir = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
lang = sys.argv[4] if len(sys.argv) > 4 else "chi_sim+eng"
os.makedirs(out_dir, exist_ok=True)

im = Image.open(src).convert("L")
w, h = im.size
im = ImageOps.autocontrast(im)
overlap = int(h * 0.02)
step = h // n

for i in range(n):
    top = max(0, i * step - overlap)
    bot = min(h, (i + 1) * step + overlap)
    part = im.crop((0, top, w, bot))
    pw, ph = part.size
    scale = min(3.0, max(1.0, 1600 / pw))
    part = part.resize((int(pw * scale), int(ph * scale)), Image.LANCZOS)
    part = ImageEnhance.Sharpness(part).enhance(1.4)
    png = os.path.join(out_dir, f"band{i:02d}.png")
    part.save(png)
    txt = os.path.join(out_dir, f"band{i:02d}")
    subprocess.run(["tesseract", png, txt, "-l", lang, "--psm", "6"],
                   capture_output=True)
    with open(txt + ".txt", encoding="utf-8", errors="replace") as f:
        body = f.read().strip()
    print(f"\n===== BAND {i:02d} (y {top}-{bot}) =====")
    print(body)
