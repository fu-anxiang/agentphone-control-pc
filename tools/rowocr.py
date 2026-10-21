#!/usr/bin/env python3
"""按行分割 + 逐行放大 OCR：先做行投影找出文本行，再逐行识别（读令牌这类精确内容用）"""
import sys, os, subprocess
import numpy as np
from PIL import Image, ImageOps

src = sys.argv[1]
lang = sys.argv[3] if len(sys.argv) > 3 else "chi_sim"
mode = sys.argv[2] if len(sys.argv) > 2 else "lines"

im = Image.open(src).convert("L")
W, H = im.size
a = np.asarray(im).astype(np.float32)
# 行亮度方差（文字行比空白行“花”）
rows = a.std(axis=1)
thr = max(6.0, rows.mean() * 0.6)
mask = rows > thr
# 连通区间
segs, start = [], None
for y, m in enumerate(mask):
    if m and start is None:
        start = y
    elif not m and start is not None:
        if y - start >= 8:
            segs.append((start, y))
        start = None
if start is not None and H - start >= 8:
    segs.append((start, H))
print(f"size {W}x{H}, 找到 {len(segs)} 行", file=sys.stderr)

for i, (y0, y1) in enumerate(segs):
    pad = 6
    y0, y1 = max(0, y0 - pad), min(H, y1 + pad)
    part = im.crop((0, y0, W, y1))
    part = ImageOps.autocontrast(part)
    pw, ph = part.size
    s = max(1.0, 2400 / pw)
    part = part.resize((int(pw * s), int(ph * s)), Image.LANCZOS)
    p = f"/tmp/ln{i:02d}.png"
    part.save(p)
    subprocess.run(["tesseract", p, p[:-4], "-l", lang, "--psm", "7"],
                   capture_output=True)
    try:
        txt = open(p[:-4] + ".txt", encoding="utf-8", errors="replace").read().strip()
    except FileNotFoundError:
        txt = ""
    if txt:
        print(f"[{i:02d} y{y0}-{y1}] {txt}")
