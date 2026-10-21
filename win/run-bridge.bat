@echo off
chcp 65001 >nul
cd /d "%~dp0"
title pcrelay bridge
echo ============================================================
echo   电脑端中继桥（新版 32 位双令牌）
echo   启动后会把两行地址打印出来，粘给手机端 pcc init
echo ============================================================
python agent_bridge.py %*
echo.
echo 进程已退出，按任意键关闭窗口
pause >nul
