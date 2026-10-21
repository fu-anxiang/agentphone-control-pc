# 发布到 GitHub

目标仓库（你已在网页上建好，空仓库）：

```
https://github.com/fu-anxiang/agentphone-control-pc
```

本地分支 `main` 已提交，只剩推送。两种方式，任选其一。

## 方式 1（推荐）：deploy key —— 不用给任何令牌

已在本机生成好一对专用密钥：

```
私钥：~/.ssh/gh_agentphone_deploy          （留在手机里，不外传）
公钥：ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN6WcmjuEdSjmg2HPgSqCwCZ9YWVKrtF2AOcL01PIfHE coomi-deploy@agentphone-control-pc
```

1. 打开 https://github.com/fu-anxiang/agentphone-control-pc/settings/keys
2. **Add deploy key** → Title 随便填（如 `coomi-phone`）→ Key 粘贴上面那行公钥
3. ✅ 勾选 **Allow write access**（必须，否则只能读）
4. **Add key**

然后跟我说一声，我执行：

```sh
./bin/push-existing.sh
```

这把 key 只对这一个仓库有写权限，泄露影响面比 PAT 小，而且随时可在同一页面删除。

## 方式 2：给 PAT

GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate：

- Repository access → 选 *Only select repositories* → `agentphone-control-pc`
- `Contents` → **Read and write**

```sh
GITHUB_TOKEN=github_pat_xxx ./bin/push-existing.sh
```

令牌只作为环境变量传给这一次 `git push`（用 `-c http.extraheader`），
**不写进 `.git/config`、不进任何文件、不出现在 `git remote -v`**。用完在 GitHub 上 Revoke。

## 推送脚本做了什么

`bin/push-existing.sh`

- 有 `GITHUB_TOKEN` → 走 HTTPS + `http.extraheader`（令牌不落盘）
- 没有 → 走 SSH + `~/.ssh/gh_agentphone_deploy`
- 先测认证，未授权就打印公钥与添加链接，不会瞎重试
- 推送后打印仓库地址

## 推完以后

```sh
git clone https://github.com/fu-anxiang/agentphone-control-pc.git
cd agentphone-control-pc
install -m 0755 bin/pcc /usr/local/bin/pcc
pcc init "<电脑端打印的两行地址>"
pcc diag        # 10 项体检，全绿即可用
```

升级：`git pull origin main`。

改完代码先跑回归（需要电脑端在线）：

```sh
cp bin/pcc /tmp/pccmod.py
python3 dev/suite_real.py     # 24 项接口
python3 dev/suite_ops.py      # 9 项运维
```

## 提交前自检

```sh
git status --short
git grep -n "room=[A-Za-z0-9_-]\{20,\}" || echo "✓ 没有真实令牌"
```

`.gitignore` 已排除：`config.json`、`ROOM.txt`、`.pcc.env`、`logs/`、`dist/`、
`*.supervisor.*`、`qr*.png`、`shots/`、`__pycache__/`。

## 可选：仓库设置建议

推上去之后可以在网页上补：

- **About** → Description：`用手机控制 Windows 电脑：pcrelay 中继 + SSH 双通道`
- **Topics**：`windows` `remote-control` `android` `automation` `ssh` `tailscale`
- **Settings → General → Default branch**：确认是 `main`
