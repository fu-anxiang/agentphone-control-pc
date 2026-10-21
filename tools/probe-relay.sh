#!/bin/bash
# 抓取 relay 的前端页面，看看它用什么协议（WebSocket / SSE / 轮询）
set -u
cd /tmp
curl -sS -m 25 https://pcrelay.pages.dev/ -o relay.html || exit 1
echo "bytes: $(wc -c < relay.html)"
echo "--- script/link ---"
grep -oE '(src|href)="[^"]+"' relay.html | head -20
echo "--- websocket ---"
grep -oE 'new WebSocket\([^)]*\)' relay.html | head -5
grep -oE 'wss?://[A-Za-z0-9./_-]+' relay.html | head -5
echo "--- fetch/api paths ---"
grep -oE '"/[A-Za-z0-9?=_&.-]*"' relay.html | sort -u | head -20
echo "--- stream/event ---"
grep -oE '(EventSource|text/event-stream|/events|/ws|/api[^"]*)' relay.html | sort -u | head -20
