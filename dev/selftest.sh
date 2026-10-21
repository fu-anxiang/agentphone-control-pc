#!/bin/bash
# pcc 客户端端到端自测
#   不带参数：用 ~/.pcc.env 里已配置的电脑
#   带参数：  临时指定 Agent 房间（如 dev/mockpc.py 起的 mock 房间）
set -u
if [ $# -ge 1 ]; then
    export PCC_ROOM="$1"
    [ $# -ge 2 ] && export PCC_VIEW_ROOM="$2"
fi
PCC=/workspace/phone-control-pc/bin/pcc
python3 "$PCC" link
echo "=== info ==="; python3 "$PCC" info
echo "=== sh ==="; python3 "$PCC" sh 'uname -s; echo hello-from-pc'
echo "=== shot ==="; python3 "$PCC" shot /tmp/pcc-test.jpg
echo "=== fs ls ==="; python3 "$PCC" fs ls /etc | head -12
echo "=== input ==="; python3 "$PCC" click left 1
echo "=== raw ==="; python3 "$PCC" raw '{"m":"ping","p":{}}'
