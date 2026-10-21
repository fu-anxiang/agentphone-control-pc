#!/usr/bin/env python3
"""精确读取 GitHub 新建仓库页上的仓库地址与命令（多尺度 + 白名单）"""
import subprocess
import sys

import numpy as np
from PIL import Image, ImageOps, ImageFilter

SRC = "/workspace/inbox/IMG_20261022_011941.jpg"
# 页面上 "Quick setup" 那段区域（含 HTTPS/SSH 与仓库地址）
REGIONS = [
    ("url_row", 1500, 1750, 700, 3072),
    ("quick", 1450, 1620, 100, 1400),
    ("repo_title", 300, 480, 100, 2000),
    ("commands", 2350, 3000, 100, 1800),
]

im = Image.open(SRC).convert("L")
W, H = im.size
print("size", W, H)


def otsu(arr):
    hist, _ = np.histogram(arr, bins=256, range=(0, 256))
    total = arr.size
    sum_all = np.dot(np.arange(256), hist)
    sumB = wB = 0.0
    best, thr = -1, 128
    for t in range(256):
        wB += hist[t]
        if wB == 0:
            continue
        wF = total - wB
        if wF == 0:
            break
        sumB += t * hist[t]
        mB, mF = sumB / wB, (sum_all - sumB) / wF
        v = wB * wF * (mB - mF) ** 2
        if v > best:
            best, thr = v, t
    return thr


for name, y0, y1, x0, x1 in REGIONS:
    part = im.crop((max(0, x0), max(0, y0), min(W, x1), min(H, y1)))
    part = ImageOps.autocontrast(part)
    print(f"\n===== {name} ({part.width}x{part.height}) =====")
    for scale in (2, 4):
        img = part.resize((part.width * scale, part.height * scale), Image.LANCZOS)
        img = img.filter(ImageFilter.MedianFilter(3))
        arr = np.asarray(img)
        t = otsu(arr)
        bw = Image.fromarray(((arr > t) * 255).astype(np.uint8))
        p = f"/tmp/gh_{name}_{scale}.png"
        bw.save(p)
        subprocess.run(["tesseract", p, p[:-4], "-l", "chi_sim+eng",
                        "--psm", "7"], capture_output=True)
        try:
            txt = open(p[:-4] + ".txt", encoding="utf-8", errors="replace").read().strip()
        except FileNotFoundError:
            txt = ""
        print(f"  [s{scale}] {txt[:400]}")
