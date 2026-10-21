#!/bin/sh
# 在 ProotLinux 客户机内生成并保管 SSH 密钥
set -e
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [ ! -f "$HOME/.ssh/coomi_win_ed25519" ]; then
  ssh-keygen -t ed25519 -N '' -C 'coomi-android@phone' -f "$HOME/.ssh/coomi_win_ed25519" >/dev/null
fi
chmod 600 "$HOME/.ssh/coomi_win_ed25519"
chmod 644 "$HOME/.ssh/coomi_win_ed25519.pub"
echo "PRIBKEY=$HOME/.ssh/coomi_win_ed25519"
cat "$HOME/.ssh/coomi_win_ed25519.pub"
