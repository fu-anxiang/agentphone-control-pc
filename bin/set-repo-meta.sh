#!/bin/bash
# =====================================================================
#  设置仓库描述与 Topics
#
#  需要 fine-grained PAT 带 **Administration: Read and write**（仅 Administration 不够
#  的是 Contents；改仓库元数据走的是 Administration）。
#  实测：只给 Contents 的令牌会返回 403 Resource not accessible by personal access token
#
#  用法：
#    GITHUB_TOKEN=github_pat_xxx ./bin/set-repo-meta.sh
#    GITHUB_TOKEN=... OWNER=fu-anxiang REPO=agentphone-control-pc ./bin/set-repo-meta.sh
# =====================================================================
set -uo pipefail

OWNER="${OWNER:-fu-anxiang}"
REPO="${REPO:-agentphone-control-pc}"
DESC="${DESC:-用手机控制 Windows 电脑：pcrelay 边缘中继 + SSH 双通道（命令/键鼠/截屏/文件/浏览器自动化）}"
TOPICS_JSON='{"names":["windows","remote-control","rpc","android","automation","ssh","tailscale","cloudflare-workers","durable-objects","powershell","python"]}'

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  cat <<'EOF' >&2
× 缺少令牌：GITHUB_TOKEN=github_pat_xxx ./bin/set-repo-meta.sh

令牌要有 **Administration: Read and write**（改描述/Topics 属于仓库管理权限）。
EOF
  exit 1
fi

API="https://api.github.com/repos/$OWNER/$REPO"

echo "[*] 设置 Description ..."
DESC_BODY=$(python3 -c 'import json,os;print(json.dumps({"description":os.environ["DESC"]}))' 2>/dev/null \
  || printf '{"description":"%s"}' "$DESC")
CODE=$(curl -sS -m 30 -o /tmp/meta1.json -w '%{http_code}' -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d "$DESC_BODY" "$API")
if [ "$CODE" = "200" ]; then
  echo "[+] Description 已更新"
else
  echo "[x] Description 失败 HTTP $CODE"; head -3 /tmp/meta1.json; DESC_OK=0
fi

echo "[*] 设置 Topics ..."
CODE=$(curl -sS -m 30 -o /tmp/meta2.json -w '%{http_code}' -X PUT \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d "$TOPICS_JSON" "$API/topics")
if [ "$CODE" = "200" ]; then
  echo "[+] Topics 已更新:"; python3 -c 'import json;print("   ", ", ".join(json.load(open("/tmp/meta2.json"))["names"]))' 2>/dev/null
else
  echo "[x] Topics 失败 HTTP $CODE"; head -3 /tmp/meta2.json
fi

rm -f /tmp/meta1.json /tmp/meta2.json

echo
echo "当前仓库状态："
curl -sS -m 20 -H "Authorization: Bearer $TOKEN" "$API" \
  | python3 -c '
import json,sys
d=json.load(sys.stdin)
print("  description:", d.get("description"))
print("  topics     :", ", ".join(d.get("topics") or []) or "(空)")
'
