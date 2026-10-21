#!/usr/bin/env python3
"""验证修正后的 type 是否能真的打进输入框"""
import importlib.util
import json
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)


def pw(**p):
    return pcc.call("pw", timeout=120, **p)


print("1) 注入输入框")
print("  goto:", pw(action="goto", url="https://example.com").get("url"))
print("  eval:", pw(action="eval", js="document.body.innerHTML="
      "'<h1>PCC TEST</h1><input id=q style=\"font-size:48px;width:90%;height:120px\">';'ok'"))
print("  eval:", pw(action="eval", js="document.getElementById('q').focus();'focused'"))

print("2) 抢前台（用窗口标题片段 'Edge'）")
r = pcc.call("focus", match="Edge")
print("  ", r.get("window"))

print("3) 定位输入框并点击")
box = json.loads(pw(action="eval", js="JSON.stringify(document.getElementById('q')"
                    ".getBoundingClientRect())").get("result"))
vp = json.loads(pw(action="eval", js="JSON.stringify({w:innerWidth,h:innerHeight,"
                   "sx:window.screenX,sy:window.screenY,sy2:window.screenY})").get("result"))
print("   input:", box)
print("   viewport:", vp)
# client 区左上：用 screenY + (窗口高-视口高) 近似不可靠，直接按 screenY 试
cx = int(vp["sx"] + box["x"] + box["width"] / 2)
cy = int(vp["sy"] + box["y"] + box["height"] / 2)
print("   点击:", cx, cy)
pcc.call("input", action="move", x=cx, y=cy)
time.sleep(0.2)
pcc.call("input", action="click", button="left", count=1)
time.sleep(0.4)

print("4) 打字（value 参数）")
pcc.call("input", action="type", value="hello-phone-中文OK")
time.sleep(0.6)

print("5) 读回")
print("   value :", pw(action="eval", js="document.getElementById('q').value"))
print("   active:", pw(action="eval", js="document.activeElement && document.activeElement.id"))
