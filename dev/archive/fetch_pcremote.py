#!/usr/bin/env python3
"""把电脑上 pcremote 关键文件逐个拉下来（只读，长超时）"""
import importlib.util
import os

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

BASE = "C:/Users/24335/Documents/for_phone/pcremote"
OUT = "/workspace/shots/pcremote"
os.makedirs(OUT, exist_ok=True)

names = [
    "config.json", "ROOM.txt", "pcconfig.py", "supervisor.py", "client_relay.py",
    "server.py", "agent_bridge.py", "install_startup.ps1", "never_lock_admin.ps1",
    "never_lock_admin.bat", "run_lan.ps1", "mkqr.py", "README.md",
    "after_restart.txt", "diag.txt", "api_test.txt", "e2e_test.txt", "final_test.txt",
]

for name in names:
    try:
        rr = pcc.call("fs", action="read", path=f"{BASE}/{name}", max_bytes=400000,
                      timeout=180)
        body = rr.get("text") or ""
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(body)
        print(f"OK   {name:22} {len(body):>7}  chars truncated={rr.get('truncated')}")
    except SystemExit:
        print(f"ERR  {name}")
