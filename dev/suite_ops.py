#!/usr/bin/env python3
"""新运维命令的回归测试（只跑只读/安全的，restart 已验证过就不再打断）"""
import importlib.util
import io
import contextlib

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

CASES = [
    ("svc status", ["status"]),
    ("view status", ["status"]),
    ("view url", ["url"]),
    ("room", []),
    ("lan status", ["status"]),
    ("startup status", ["status"]),
    ("nolock status", ["status"]),
    ("net", []),
    ("logs bridge -n 3", ["bridge", "-n", "3"]),
]

FN = {
    "svc": pcc.cmd_svc, "view": pcc.cmd_view, "room": pcc.cmd_room,
    "lan": pcc.cmd_lan, "startup": pcc.cmd_startup, "nolock": pcc.cmd_nolock,
    "net": pcc.cmd_net, "logs": pcc.cmd_logs,
}

ok = fail = 0
for name, args in CASES:
    key = name.split()[0]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = FN[key](args)
        body = buf.getvalue().strip()
        if not body:
            raise RuntimeError("无输出")
        ok += 1
        first = body.splitlines()[0][:60]
        print(f"[OK  ] {name:20} {first}")
    except SystemExit as e:
        fail += 1
        print(f"[FAIL] {name:20} 退出码 {e.code}")
    except Exception as e:
        fail += 1
        print(f"[FAIL] {name:20} {type(e).__name__}: {e}")

print(f"\n通过 {ok}，失败 {fail}")
