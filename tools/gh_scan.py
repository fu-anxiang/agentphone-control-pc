#!/usr/bin/env python3
"""在截图里扫出包含 github / https / git@ 的行（逐条横带，多尺度）"""
import re
import subprocess

import numpy as np
from PIL import Image, ImageOps

SRC = "/workspace/inbox/IMG_20261022_011941.jpg"
im = Image.open(SRC).convert("L")
W, H = im.size
PAT = re.compile(r"(github|git@|https?://|agentphone|control-pc|origin)", re.I)

step = 90
hits = []
for y0 in range(0, H, step):
    y1 = min(H, y0 + step * 2)
    part = im.crop((0, y0, W, y1))
    part = ImageOps.autocontrast(part)
    img = part.resize((part.width * 2, part.height * 2), Image.LANCZOS)
    p = "/tmp/scan.png"
    img.save(p)
    subprocess.run(["tesseract", p, "/tmp/scan", "-l", "eng", "--psm", "6"],
                   capture_output=True)
    try:
        txt = open("/tmp/scan.txt", encoding="utf-8", errors="replace").read()
    except FileNotFoundError:
        continue
    for line in txt.splitlines():
        s = line.strip()
        if s and PAT.search(s):
            hits.append((y0, s))
            print(f"[y{y0:>5}] {s}")
