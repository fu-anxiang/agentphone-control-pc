#!/usr/bin/env python3
"""先验证 WMI 脱管启动机制（不起停服务，只 echo 一个文件），确认引号拼接没写错"""
import importlib.util
import time

spec = importlib.util.spec_from_file_location("pccmod", "/tmp/pccmod.py")
pcc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pcc)

PM = "C:/Users/24335/Documents/for_phone/pcremote"
OUT = "C:/Users/24335/pcc-wmi-test.txt"

ps = (
    "$sup='" + PM + "/supervisor.py'; "
    "$py=(Get-Command python).Source; "
    "$c=\"cmd.exe /c timeout /t 1 /nobreak >nul & echo \" + $py + \" \" + $sup + \" > " + OUT + "\"; "
    "Invoke-CimMethod -ClassName Win32_Process -MethodName Create "
    "-Arguments @{CommandLine=$c; CurrentDirectory='" + PM + "'} "
    "| Select-Object -ExpandProperty ProcessId"
)
r = pcc.call("shell", cmd=ps, timeout=90)
print("code:", r.get("code"), "out:", (r.get("out") or "").strip(), "err:", (r.get("err") or "")[:300])
time.sleep(4)
r = pcc.call("fs", action="read", path=OUT)
print("写到文件的内容:", repr(r.get("text")))
pcc.call("fs", action="delete", path=OUT)
print("已删除测试文件")
