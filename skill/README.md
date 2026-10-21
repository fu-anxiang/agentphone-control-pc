# Skill：controlling-windows-pc

把整套能力做成一个可复用的 Coomi Skill，下次开新会话时直接 `read_skill` 就能接着用。

## 安装（新设备/重装后一条命令）

```sh
cp -r skill/controlling-windows-pc ~/.coomi/skills/
```

或者用 Skill 工具装本地目录：

```
install_skill(source="/workspace/phone-control-pc/skill/controlling-windows-pc")
```

装完 `list_skills` 里应出现 `controlling-windows-pc`。

## 它记录了什么

- 两条通道怎么选（`pcc` 中继 vs `winctl` SSH）
- **每次开场固定动作**：`pcc conf` + `pcc diag`（10 项体检），别盲试
- 全部命令速查（执行/屏幕/键鼠/窗口/文件/剪贴板/浏览器/运维）
- **四个必踩的坑**：参数名静默失效、`shell` 抢焦点、`pw` 是无头、宽屏要降采样
- 锁屏的正确处理（不是绕过，是别让它锁）
- 凭据**位置**（不写内容）+ 泄露后的应急
- 故障 → 对应命令的排查表
- 改完代码的回归流程（33 项）

## 凭据怎么存

**不写进 SKILL.md**，而是单独放一个 600 权限文件：

```
~/.config/pcc/secrets.env
```

内容：`GITHUB_TOKEN`（coomi-use）、`GH_OWNER` / `GH_REPO` / `GH_REPO_URL`、
两把 SSH 私钥的路径。加载方式：

```sh
set -a; . ~/.config/pcc/secrets.env; set +a
```

为什么这么放：

| 方案 | 问题 |
|---|---|
| 写进 SKILL.md | skill 目录会被整包复制/打包/分享，令牌跟着走；仓库里也会被提交 |
| 写进 memory | memory 是引擎的私有目录，能读但排查时容易被顺手贴出来 |
| **单独 600 文件** | 只有本机 root 可读；skill/文档只引用路径；泄了只需删一个文件 |

同理，房间令牌在 `~/.pcc.env`，SSH 私钥在 `~/.ssh/`（600），skill 里只有路径。

## ⚠ 需要你处理的安全事项

`coomi-use` 这个 PAT **没有过期时间**，而且已经出现在聊天记录里了。
建议现在就做：

1. 需要它改仓库描述/Topics 时，先补 `Administration: Read and write`
   （https://github.com/settings/tokens?type=beta → coomi-use → Permissions）
2. 我跑 `GITHUB_TOKEN=... ./bin/set-repo-meta.sh` 把描述和 Topics 设好
3. 然后**立刻 Revoke 这个令牌**，用的时候再生成带 7 天过期的

Revoke 之后 `~/.config/pcc/secrets.env` 里的 `GITHUB_TOKEN` 会失效，
到时把 `secrets.env` 里那行删掉或换成新令牌即可（skill 不会因此失效）。

## 记忆里也存了一份

开发环境、电脑端路径、仓库地址、10 条踩坑结论同时写进了项目记忆
`pc-control-setup`，这样即使不加载 skill，问「那台电脑怎么连」也能答上来。
