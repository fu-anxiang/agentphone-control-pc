#!/usr/bin/env python3
"""把手机截图/照片缩小，便于模型视觉读取；同时可切成上下两半提高字迹清晰度。"""
import sys, os
from PIL import Image

src = sys.argv[1]
out_dir = sys.argv[2] if len(sys.argv) > 2 else "/tmp/shots"
os.makedirs(out_dir, exist_ok=True)

im = Image.open(src)
im = im.convert("RGB")
w, h = im.size
print(f"original: {w}x{h}")

base = os.path.splitext(os.path.basename(src))[0]

# 整体缩略（长边 <= 1500）
scale = min(1.0, 1500 / max(w, h))
small = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
p = os.path.join(out_dir, base + "-full.jpg")
small.save(p, quality=82, optimize=True)
print("full:", p, os.path.getsize(p))

# 上下两半（各自长边 <= 1500）
if h > w:
    halves = [(0, 0, w, h // 2), (0, h // 2, w, h)]
    for i, box in enumerate(halves, 1):
        part = im.crop(box)
        pw, ph = part.size
        s = min(1.0, 1500 / max(pw, ph))
        part = part.resize((int(pw * s), int(ph * s)), Image.LANCZOS)
        pp = os.path.join(out_dir, f"{base}-part{i}.jpg")
        part.save(pp, quality=85, optimize=True)
        print(f"part{i}:", pp, os.path.getsize(pp))
