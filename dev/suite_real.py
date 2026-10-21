#!/usr/bin/env python3
"""pcc 全命令验证套件（对着真实电脑端跑）"""
import base64
import hashlib
import importlib.util
import json
import os
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

OK, FAIL = [], []


def check(name, fn):
    t0 = time.time()
    try:
        r = fn()
        ms = int((time.time() - t0) * 1000)
        OK.append((name, ms, r))
        print(f"[OK  ] {name:28} {ms:>6}ms  {str(r)[:90]}")
        return r
    except SystemExit as e:
        FAIL.append((name, "电脑端报错"))
        print(f"[FAIL] {name:28} 电脑端报错")
    except Exception as e:
        FAIL.append((name, f"{type(e).__name__}: {e}"))
        print(f"[FAIL] {name:28} {type(e).__name__}: {e}")


print("========== 只读类 ==========")
check("info", lambda: pcc.call("info").get("host"))
check("ping", lambda: pcc.call("ping").get("calls"))
check("session", lambda: pcc.call("session").get("locked"))
check("shell", lambda: pcc.call("shell", cmd="hostname").get("out", "").strip())
check("windows", lambda: len(pcc.call("windows").get("windows") or []))
check("fs list", lambda: len(pcc.call("fs", action="list", path="C:/Users/24335").get("items") or []))
check("clip get", lambda: len(pcc.call("clip").get("text") or ""))

print("========== 截图 ==========")
shot = check("screenshot", lambda: len(pcc.call("screenshot", quality=60, max_width=1280).get("b64") or ""))
if shot:
    data = base64.b64decode(pcc.call("screenshot", quality=60, max_width=1280)["b64"])
    open("/workspace/shots/suite-shot.jpg", "wb").write(data)
    print(f"       文件 {len(data)} 字节 → /workspace/shots/suite-shot.jpg")

print("========== 文件读写（文本 / 二进制） ==========")
tmp = "C:/Users/24335/pcc-suite.txt"
check("fs write", lambda: pcc.call("fs", action="write", path=tmp,
                                  content="第一行\n第二行中文\nthird\n").get("bytes"))
check("fs read", lambda: repr(pcc.call("fs", action="read", path=tmp).get("text"))[:60])
check("fs append", lambda: pcc.call("fs", action="write", path=tmp, content="appended\n",
                                    append=True).get("bytes"))
check("fs read2", lambda: pcc.call("fs", action="read", path=tmp).get("text").count("\n"))

# 二进制：上传本地生成的 PNG
local_png = "/tmp/suite-test.png"
from PIL import Image
Image.new("RGB", (64, 48), (30, 144, 255)).save(local_png)
data = open(local_png, "rb").read()
h_in = hashlib.md5(data).hexdigest()
b64 = base64.b64encode(data).decode()
remote_png = "C:/Users/24335/pcc-suite.png"
tmpb = remote_png + ".b64tmp"
check("fs put(b64)", lambda: pcc.call("fs", action="write", path=tmpb, content=b64).get("bytes"))
check("decode on pc", lambda: pcc.call("shell", cmd=(
    f"$b=Get-Content -Raw -LiteralPath '{tmpb}'; "
    f"[IO.File]::WriteAllBytes('{remote_png}',[Convert]::FromBase64String($b.Trim())); "
    f"(Get-Item -LiteralPath '{remote_png}').Length")).get("out", "").strip())
check("fs get(b64)", lambda: len(pcc.call("shell", cmd=(
    f"[Convert]::ToBase64String([IO.File]::ReadAllBytes('{remote_png}'))")).get("out", "").strip()))

# 下载回来校验 md5
back = pcc.call("shell", cmd=f"[Convert]::ToBase64String([IO.File]::ReadAllBytes('{remote_png}'))")
back_b64 = (back.get("out") or "").strip()
if back_b64:
    h_out = hashlib.md5(base64.b64decode(back_b64)).hexdigest()
    print(f"       md5 一致: {h_in == h_out}  ({h_in[:12]})")
    OK.append(("binary roundtrip md5", 0, h_in == h_out))

check("fs mkdir", lambda: pcc.call("fs", action="mkdir", path="C:/Users/24335/pcc-suite-dir").get("path"))
check("fs del dir", lambda: pcc.call("fs", action="delete", path="C:/Users/24335/pcc-suite-dir").get("path"))
check("fs del file", lambda: pcc.call("fs", action="delete", path=tmp).get("path"))
check("fs del png", lambda: pcc.call("fs", action="delete", path=remote_png).get("path"))

print("========== 剪贴板 ==========")
check("clip set", lambda: pcc.call("clip", set="剪贴板测试 abc-123") or "ok")
check("clip get", lambda: pcc.call("clip").get("text"))

print("========== 保活 ==========")
check("awake on", lambda: pcc.call("keep_awake", on=True).get("on"))
check("awake off/on", lambda: (pcc.call("keep_awake", on=False), pcc.call("keep_awake", on=True))[1].get("on"))

print("\n========== 汇总 ==========")
print(f"通过 {len(OK)} 项，失败 {len(FAIL)} 项")
for n, e in FAIL:
    print("  失败:", n, e)
