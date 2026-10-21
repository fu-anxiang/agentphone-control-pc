# 发布与拉取

## 仓库

```
https://github.com/fu-anxiang/agentphone-control-pc    （public，默认分支 main）
```

**已推送成功**，远端 HEAD 与本地一致。已验证：全新克隆 → `bin/pcc` 语法通过、
脚本语法通过、用已有 `~/.pcc.env` 能直连电脑 `FAX`。

## 为什么不需要令牌

手机上的 `~/.ssh/config` 里已有：

```
Host github.com
  IdentityFile /root/.ssh/id_ed25519
  IdentitiesOnly yes
```

这把钥匙 GitHub 已认（`ssh -T git@github.com` → `Hi fu-anxiang!`），
所以直接用 SSH 推送即可，无需 PAT：

```sh
git remote add origin git@github.com:fu-anxiang/agentphone-control-pc.git
git push -u origin main
```

`bin/push-existing.sh` 会优先用这把钥匙；只有它失效时才需要 deploy key 或 PAT。

<details>
<summary>备用：deploy key / PAT（本机已有可用钥匙，一般用不上）</summary>

**deploy key**：`~/.ssh/gh_agentphone_deploy.pub` 已生成，加到
Settings → Deploy keys → ✅ Allow write access 即可。
它只对这一个仓库有写权限，影响面比 PAT 小。

**PAT**：Fine-grained token，`Contents: Read and write`，只选这一个仓库：

```sh
GITHUB_TOKEN=github_pat_xxx ./bin/push-existing.sh
```

令牌只作为环境变量传给这一次 `git push`（`-c http.extraheader`），
不写进 `.git/config`、不进任何文件、不出现在 `git remote -v`。用完 Revoke。

</details>

## 在另一台机器上拉取并继续

```sh
git clone git@github.com:fu-anxiang/agentphone-control-pc.git   # 或 https://
cd agentphone-control-pc

install -m 0755 bin/pcc /usr/local/bin/pcc      # 装手机端客户端
pcc init "<电脑端打印的两行地址>"                 # 两个 32 位令牌
pcc diag                                        # 10 项体检，全绿即可用
```

升级已有环境：

```sh
git pull origin main
install -m 0755 bin/pcc /usr/local/bin/pcc      # bin/pcc 是主程序，改了就重装
```

## 改完代码怎么验

```sh
cp bin/pcc /tmp/pccmod.py        # 套件从固定路径导入
python3 dev/suite_real.py        # 24 项接口（需电脑端在线）
python3 dev/suite_ops.py         # 9 项运维命令
python3 -m py_compile bin/pcc win/agent_bridge.py
bash -n bin/*.sh
```

没有电脑端时用 mock：

```sh
python3 dev/mockpc.py mock-room 300          # 起一个假电脑
PCC_ROOM=mock-room python3 dev/selftest.sh
```

## 提交前自检

```sh
git status --short
git grep -n "room=[A-Za-z0-9_-]\{20,\}" || echo "✓ 没有真实令牌"
```

`.gitignore` 已排除：`config.json`、`ROOM.txt`、`.pcc.env`、`logs/`、`dist/`、
`*.supervisor.*`、`qr*.png`、`shots/`、`__pycache__/`。

## 建议在网页上补的仓库信息

- **About → Description**：`用手机控制 Windows 电脑：pcrelay 中继 + SSH 双通道`
- **Topics**：`windows` `remote-control` `android` `automation` `ssh` `tailscale`
- 这些设置需要浏览器操作（或带 token 的 API 调用）
