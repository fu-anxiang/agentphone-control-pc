# 发布到 GitHub（一次性）

本地仓库已经建好，首次提交为 `feat: 手机控制 Windows 电脑（pcrelay 中继 + SSH 双通道）`。
只差推到远端。

## 方式 A：给我一个令牌，我全自动建库 + 推送

1. GitHub → 右上头像 → **Settings** → 左下 **Developer settings**
2. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
3. 设置：
   - **Repository access** → *All repositories*（首次建库需要）或先建空仓库再选 *Only select repositories*
   - **Permissions**：
     - `Administration` → **Read and write**（创建仓库）
     - `Contents` → **Read and write**（推送代码）
   - **Expiration**：7 天即可
4. 生成后复制 `github_pat_...`，发给我，我执行：

```sh
GITHUB_TOKEN=github_pat_xxx ./bin/push-github.sh phone-control-pc private
```

用完立刻到同一页面 **Revoke** 删掉这个令牌。

> 令牌只会作为环境变量传给这一次 `git push`，**不会写进 `.git/config`、
> 不会进任何文件、也不会出现在 `git remote -v`**（脚本用 `-c http.extraheader`
> 临时注入，并把 remote 设成不带凭据的 https 地址）。

## 方式 B：你自己推（令牌不经手我）

在你自己的终端里：

```sh
cd phone-control-pc

# 1. 在网页上先建一个空仓库（不要勾 README / .gitignore / license）
#    https://github.com/new

# 2. 关联并推送
git remote add origin https://github.com/<你的用户名>/phone-control-pc.git
git branch -M main
git push -u origin main
```

用 SSH 的话：

```sh
git remote add origin git@github.com:<你的用户名>/phone-control-pc.git
git push -u origin main
```

## 方式 C：只导出压缩包，稍后自己推

```sh
./bin/make-kit.py      # 生成 dist/pc-control-kit.zip
```

## 后续升级怎么拉取

仓库里已经带好：

- `CHANGELOG.md` —— 版本与变更（v0.1 → v0.3）
- `docs/PROTOCOL.md` —— 接口实测表，接口一变照着重跑 `dev/probe_api*.py`
- `dev/suite_real.py` / `dev/suite_ops.py` —— 回归套件，改完先跑这个

新机器上继续开发：

```sh
git clone https://github.com/<你>/phone-control-pc.git
cd phone-control-pc
install -m 0755 bin/pcc /usr/local/bin/pcc     # 装到手机端
pcc init "<电脑端打印的两行地址>"
pcc diag                                        # 10 项体检
```

## 提交前自检（重要）

```sh
git status --short
git grep -n "room=" -- '*.py' '*.md' | grep -v "<令牌"   # 别把真实令牌提交上去
```

`.gitignore` 已排除：`config.json`、`ROOM.txt`、`.pcc.env`、`logs/`、`dist/`、
`*.supervisor.*`、`qr*.png`、`shots/`。
