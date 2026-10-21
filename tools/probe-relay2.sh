#!/bin/bash
set -u
cd /tmp
[ -f relay.html ] || curl -sS -m 25 https://pcrelay.pages.dev/ -o relay.html
python3 - <<'PY'
import re
h = open('/tmp/relay.html', encoding='utf-8').read()
# 打印与协议相关的片段
for kw in ['WebSocket', '/ws', 'room', 'send(', 'onmessage', 'type', 'TEXT', 'BLOCK']:
    for m in re.finditer(re.escape(kw), h):
        s = max(0, m.start()-160); e = min(len(h), m.end()+200)
        print(f"--- {kw} @{m.start()} ---")
        print(h[s:e].replace('\n', ' '))
        break
PY
