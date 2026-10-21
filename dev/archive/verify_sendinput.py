#!/usr/bin/env python3
"""判断 SendInput 是否生效：先标记页面，再发 F5，看页面有没有刷新"""
import importlib.util
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)


def pw(**p):
    return pcc.call("pw", timeout=120, **p)


print("mark:", pw(action="eval", js="window.__mark='MARK123'; window.__mark"))
print("focus:", pcc.call("focus", match="Edge").get("window", {}).get("foreground"))
print("send F5 ...")
pcc.call("input", action="key", key="f5")
time.sleep(2.5)
print("after F5 mark:", pw(action="eval", js="String(window.__mark)"))

print("--- 再试 ctrl+v 路径 ---")
pcc.call("clip", set="clipboard-路径中文测试")
pcc.call("focus", match="Edge")
pcc.call("input", action="key", key="a", mods=["ctrl"])
time.sleep(0.3)
pcc.call("input", action="key", key="v", mods=["ctrl"])
time.sleep(0.8)
print("input value:", pw(action="eval", js="document.getElementById('q') ? "
      "document.getElementById('q').value : '(no input)'"))
