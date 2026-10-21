#!/usr/bin/env python3
"""调试 pcc view qr 的两步 PowerShell"""
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

PM = "C:/Users/24335/Documents/for_phone/pcremote"
import os
url = os.environ.get("PCC_VIEW_URL", "https://pcrelay.pages.dev/?room=<投屏令牌>")

r = pcc.call("shell", cmd=f"python '{PM}/mkqr.py' '{url}' '{PM}/qr_view.png'", timeout=90)
print("mkqr code:", r.get("code"), "out:", repr((r.get("out") or "")[:200]),
      "err:", repr((r.get("err") or "")[:300]))

r = pcc.call("shell", cmd=(
    f"$p='{PM}/qr_view.png'; if (Test-Path $p) {{ "
    "[Convert]::ToBase64String([IO.File]::ReadAllBytes($p)) }}"), timeout=90)
out = r.get("out") or ""
print("read code:", r.get("code"), "len:", len(out), "head:", repr(out[:80]))
print("err:", repr((r.get("err") or "")[:300]))
