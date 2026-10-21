#!/bin/bash
# =====================================================================
#  推送到已存在的 GitHub 仓库（仓库你已经在网页上建好）
#
#  方式 1（推荐，不用给令牌）：先把 deploy key 加到仓库
#     GitHub → 仓库 → Settings → Deploy keys → Add deploy key
#     粘贴：~/.ssh/gh_agentphone_deploy.pub 的内容
#     ✅ 勾选 "Allow write access"
#     然后运行： ./bin/push-existing.sh
#
#  方式 2（给 PAT）：GITHUB_TOKEN=ghp_xxx ./bin/push-existing.sh
# =====================================================================
set -uo pipefail

OWNER="${1:-fu-anxiang}"
REPO="${2:-agentphone-control-pc}"
KEY="$HOME/.ssh/gh_agentphone_deploy"

cd "$(dirname "$0")/.." || exit 1
git rev-parse --git-dir >/dev/null 2>&1 || { echo "× 这里不是 git 仓库" >&2; exit 1; }

BRANCH=$(git branch --show-current)
[ -z "$BRANCH" ] && BRANCH=main

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"

if [ -n "$TOKEN" ]; then
  # ---- HTTPS + 令牌（令牌只在这次命令里，不落盘） ----
  echo "[*] 使用令牌推送（HTTPS）"
  git remote remove origin 2>/dev/null
  git remote add origin "https://github.com/$OWNER/$REPO.git"
  git -c "http.https://github.com/.extraheader=Authorization: Bearer $TOKEN" \
      push -u origin "$BRANCH" && {
    echo "[+] 完成: https://github.com/$OWNER/$REPO"
    exit 0
  }
  echo "× 推送失败（检查令牌是否有 Contents:write）" >&2
  exit 1
fi

# ---- SSH + deploy key ----
if [ ! -f "$KEY" ]; then
  echo "× 没有 deploy key，也没有 GITHUB_TOKEN。" >&2
  echo "  生成密钥: ssh-keygen -t ed25519 -N '' -f $KEY" >&2
  exit 1
fi

echo "[*] 使用 SSH deploy key：$KEY"
export GIT_SSH_COMMAND="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
echo "[*] 测试 GitHub SSH 认证 ..."
if ! ssh -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
        -T git@github.com 2>&1 | grep -qiE "successfully authenticated|Hi "; then
  echo "[!] GitHub 还没认这把 key。请先加 deploy key（见下面说明），再重跑本脚本："
  echo
  echo "    1) 打开 https://github.com/$OWNER/$REPO/settings/keys"
  echo "    2) Add deploy key → 粘贴下面这行 → ✅ 勾 Allow write access → Add key"
  echo
  cat "$KEY.pub"
  echo
  exit 1
fi

git remote remove origin 2>/dev/null
git remote add origin "git@github.com:$OWNER/$REPO.git"
git push -u origin "$BRANCH" && {
  echo "[+] 完成: https://github.com/$OWNER/$REPO"
}
