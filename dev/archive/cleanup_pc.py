#!/usr/bin/env python3
"""清理我在电脑上留下的测试痕迹：
   1) 关掉 pw 打开的 example.com 标签页（恢复原页）
   2) 关掉测试用记事本（pid 27020，未保存内容丢弃）
   3) 删掉 pcc-test.txt 等临时文件
"""
import importlib.util

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

print("=== pw 页面列表 ===")
pages = pcc.call("pw", action="pages").get("pages") or []
for i, pg in enumerate(pages):
    print(f"  [{i}] {pg.get('title')!r}  {pg.get('url')}")

# 关掉 example.com 那个标签（用 script 直接 close 页面）
script = """
for pg in list(context.pages):
    if 'example.com' in pg.url:
        await pg.close()
result = [p.url for p in context.pages]
"""
r = pcc.call("pwscript", code=script, timeout=120)
print("清理后页面:", r.get("result"))

print("=== 关掉测试记事本 ===")
try:
    r = pcc.call("app", action="kill", pid=27020)
    print("  kill pid 27020:", r)
except SystemExit as e:
    print("  (进程可能已不存在)")

print("=== 清理临时文件 ===")
for p in ["C:/Users/24335/pcc-test.txt", "C:/Users/24335/pcc-focus.ps1"]:
    try:
        r = pcc.call("fs", action="delete", path=p)
        print("  deleted", r.get("path"))
    except SystemExit:
        print("  (不存在)", p)
