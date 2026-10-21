#!/usr/bin/env python3
"""对截图的指定纵向区间做 4x 放大 OCR，只打印含 URL / room / 代码特征的行，用于精确取出地址与房间号。"""
import sys, os, re, subprocess
from PIL import Image, ImageOps

src = sys.argv[1]
y0 = int(sys.argv[2]); y1 = int(sys.argv[3])
psm = sys.argv[4] if len(sys.argv) > 4 else "6"
lang = os.environ.get("OCR_LANG", "chi_sim")

im = Image.open(src).convert("L")
w, h = im.size
y1 = min(y1, h)
part = im.crop((0, y0, w, y1))
part = ImageOps.autocontrast(part)
pw, ph = part.size
part = part.resize((pw * 4, ph * 4), Image.LANCZOS)
p = "/tmp/crop.png"
part.save(p)
subprocess.run(["tesseract", p, "/tmp/crop", "-l", lang, "--psm", psm], capture_output=True)
txt = open("/tmp/crop.txt", encoding="utf-8", errors="replace").read()
pat = re.compile(r"(https?://\S+|agent-\d+|\b\d{6,12}\b|room\s*=\s*\S+|def call|requests\.post|\"m\"|'m')", re.I)
for line in txt.splitlines():
    s = line.strip()
    if s and pat.search(s):
        print(f"[{y0}-{y1}] {s}")
