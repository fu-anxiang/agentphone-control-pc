#!/usr/bin/env python3
"""打包手机控制电脑工具包（手机端 pcc + Windows 端桥 + 文档 + 实测工具）"""
import os, zipfile

ROOT = "/workspace/phone-control-pc"
OUT_DIR = os.path.join(ROOT, "dist")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "pc-control-kit.zip")

files = [
    "README.md",
    "setup-pc.ps1",
    "win/agent_bridge.py",
    "win/install-bridge.ps1",
    "win/run-bridge.bat",
    "win/winctl",
    "bin/pcc",
    "bin/pl",
    "dev/mockpc.py",
    "dev/phone_sim.py",
    "dev/selftest.sh",
    "dev/suite_real.py",
    "dev/probe_api.py",
    "dev/probe_api2.py",
    "dev/probe_api3.py",
    "dev/probe_api4.py",
    "dev/suite_ops.py",
    "dev/fetch_pcremote.py",
]

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in files:
        p = os.path.join(ROOT, rel)
        if os.path.exists(p):
            z.write(p, rel)
        else:
            print("缺文件:", rel)

print(out, os.path.getsize(out), "bytes")
with zipfile.ZipFile(out) as z:
    for i in z.infolist():
        print(f"  {i.filename:32} {i.file_size:7} B")
