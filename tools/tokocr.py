#!/usr/bin/env python3
"""令牌区域精读：裁剪 → 放大 → Otsu 二值化 → 指定字符白名单 OCR，多方案投票"""
import sys, subprocess
import numpy as np
from PIL import Image, ImageOps, ImageFilter

src, y0, y1, x0, x1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
WL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"

im = Image.open(src).convert("L")
base = im.crop((x0, y0, x1, y1))
base = ImageOps.autocontrast(base)


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


variants = []
for scale in (5, 7):
    for blur in (0, 1):
        v = base.resize((base.width * scale, base.height * scale), Image.LANCZOS)
        if blur:
            v = v.filter(ImageFilter.MedianFilter(3))
        arr = np.asarray(v)
        t = otsu(arr)
        bw = Image.fromarray(((arr > t) * 255).astype(np.uint8))
        variants.append((f"s{scale}b{blur}", bw))
        variants.append((f"s{scale}b{blur}inv", Image.fromarray(((arr <= t) * 255).astype(np.uint8))))

results = {}
for name, img in variants:
    p = f"/tmp/tok_{name}.png"
    img.save(p)
    for psm in ("7", "8", "13"):
        subprocess.run(["tesseract", p, p[:-4] + psm, "-l", "chi_sim",
                        "--psm", psm, "-c", "tessedit_char_whitelist=" + WL],
                       capture_output=True)
        try:
            txt = open(p[:-4] + psm + ".txt", encoding="utf-8", errors="replace").read()
        except FileNotFoundError:
            continue
        txt = "".join(ch for ch in txt if ch in WL)
        if txt:
            results.setdefault(txt, 0)
            results[txt] += 1

for txt, cnt in sorted(results.items(), key=lambda kv: -kv[1]):
    print(f"{cnt:2}x len={len(txt):2}  {txt}")
