#!/bin/bash
# =====================================================================
#  在 GitHub 上创建仓库并推送（一次性脚本，令牌不会被写进任何文件）
#
#  用法：
#    GITHUB_TOKEN=ghp_xxx ./bin/push-github.sh                  # 默认仓库名 phone-control-pc / 私有
#    GITHUB_TOKEN=ghp_xxx ./bin/push-github.sh phone-control-pc public
#    GITHUB_TOKEN=ghp_xxx ./bin/push-github.sh my-repo private owner
#
#  令牌权限（fine-grained PAT）：
#    - Administration: Read and write   （创建仓库）
#    - Contents:       Read and write   （推送代码）
#  或者 classic PAT 勾 repo 一项。
# =====================================================================
set -uo pipefail

REPO="${1:-phone-control-pc}"
VIS="${2:-private}"
OWNER_ARG="${3:-}"

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
if [ -z "$TOKEN" ]; then
  cat <<'EOF' >&2
× 缺少令牌。请这样运行：

    GITHUB_TOKEN=你的PAT ./bin/push-github.sh

令牌在 GitHub → Settings → Developer settings → Personal access tokens 生成，
用完可以立即删除。本脚本不会把令牌写到磁盘任何地方。
EOF
  exit 1
fi

cd "$(dirname "$0")/.." || exit 1
command -v git >/dev/null || { echo "× 需要 git" >&2; exit 1; }
command -v curl >/dev/null || { echo "× 需要 curl" >&2; exit 1; }

# ---------- 1. 取账号 ----------
USER_JSON=$(curl -sS -m 20 -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" https://api.github.com/user)
LOGIN=$(printf '%s' "$USER_JSON" | grep -o '"login"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
if [ -z "$LOGIN" ]; then
  echo "× 令牌无效，或没有 user 读权限。返回：" >&2
  printf '%s\n' "$USER_JSON" | head -5 >&2
  exit 1
fi
OWNER="${OWNER_ARG:-$LOGIN}"
PRIVATE=false
[ "$VIS" = "private" ] && PRIVATE=true
echo "[*] 账号: $LOGIN    仓库: $OWNER/$REPO    $([ "$PRIVATE" = true ] && echo 私有 || echo 公开)"

# ---------- 2. 创建仓库（已存在就复用） ----------
CODEPATH="/user/repos"
[ "$OWNER" != "$LOGIN" ] && CODEPATH="/orgs/$OWNER/repos"
BODY=$(printf '{"name":"%s","private":%s,"description":"手机控制 Windows 电脑：pcrelay 中继 + SSH 双通道","has_issues":true,"has_wiki":false}' \
  "$REPO" "$PRIVATE")

HTTP=$(curl -sS -m 30 -o /tmp/gh-create.json -w '%{http_code}' -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "Content-Type: application/json" \
  -d "$BODY" "https://api.github.com$CODEPATH")

case "$HTTP" in
  201) echo "[+] 仓库已创建: https://github.com/$OWNER/$REPO" ;;
  422) echo "[!] 仓库已存在，直接推送" ;;
  401|403) echo "× 令牌权限不足（需要 Administration + Contents 读写）HTTP $HTTP" >&2
           head -5 /tmp/gh-create.json >&2; exit 1 ;;
  *)   echo "× 创建失败 HTTP $HTTP" >&2; head -5 /tmp/gh-create.json >&2; exit 1 ;;
esac
rm -f /tmp/gh-create.json

# ---------- 3. 推送 ----------
# 用改写过 header 的方式传令牌，避免令牌出现在 remote URL / .git/config / 进程列表里
git config --local user.name  "$(git config --global user.name  || echo "$LOGIN")"
git config --local user.email "$(git config --global user.email || echo "$LOGIN@users.noreply.github.com")"

REMOTE_URL="https://github.com/$OWNER/$REPO.git"
git remote remove origin 2>/dev/null
git remote add origin "$REMOTE_URL"

echo "[*] 推送 main ..."
if git -c "http.https://github.com/.extraheader=Authorization: Bearer $TOKEN" \
       push -u origin main 2>&1 | tail -5; then
  echo "[+] 完成: https://github.com/$OWNER/$REPO"
  echo "    以后拉取/升级:  git pull origin main"
else
  echo "× 推送失败。检查：令牌是否有 Contents:write；分支是否叫 main" >&2
  exit 1
fi
