#!/usr/bin/env python3
"""把 cf-edge-relay 的 5 个源文件拉下来，逐个打印（入仓前先审一遍有无密钥）"""
import importlib.util
import os

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

ROOT = "C:/Users/24335/Documents/for_phone/cf-edge-relay"
OUT = "/workspace/relay-src"
FILES = [
    "wrangler.toml",
    "functions/[[path]].js",
    "public/index.html",
    "do-worker/wrangler.toml",
    "do-worker/src/index.js",
]

for rel in FILES:
    p = f"{ROOT}/{rel}"
    try:
        r = pcc.call("fs", action="read", path=p, max_bytes=400000)
    except SystemExit:
        print(f"ERR  {rel}")
        continue
    body = r.get("text") or ""
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(body)
    print(f"OK   {rel:28} {len(body):>7} chars -> {dst}")
