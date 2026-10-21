# 手机控制电脑（Windows）—— pcrelay 中继 + SSH 双通道

用手机（Android + Coomi/ProotLinux）远程控制一台 Windows 电脑：
**跑命令、开软件、点鼠标、打字、截屏、传文件、剪贴板、浏览器自动化、看桌面**。

两条通道，优先用第一条 —— 不用公网 IP、不用改路由器、手机在 4G/5G 也能用：

| 通道 | 前提 | 能力 | 实测延迟 |
|---|---|---|---|
| **A. pcrelay 边缘中继**（推荐） | 电脑上跑 `agent_bridge.py` | 命令 / 软件 / 键鼠 / 截屏 / 文件 / 剪贴板 / 浏览器自动化 | info 1.8s、shell 1.5s、截图 2s |
| B. SSH + Tailscale（备用） | 电脑装 Tailscale + OpenSSH | 稳定命令行 / SFTP / RDP | 局域网毫秒级 |

> 已在真实环境跑通：手机 → 电脑 `FAX`（Windows 11 Pro / 3840×2160），
> 24 项接口测试 + 9 项运维命令全部通过，中文打字与二进制文件往返都验证过。

---

## 它解决什么问题

家里的 Windows 电脑没有公网 IP，手机在外网时：

- 想跑个命令 / 重启个服务 → `pcc sh '...'`
- 想拿电脑上的文件 → `pcc fs get`
- 想点一下某个窗口里的按钮 → `pcc win click`
- 想看看桌面现在什么样 → `pcc shot`
- 想让 AI Agent 自己去操作电脑 → 直接 `POST /api`，方法表见 [docs/PROTOCOL.md](docs/PROTOCOL.md)

中继走 Cloudflare 边缘（`pcrelay.pages.dev`），**两端都只做出站连接**，不开端口、不需要 DDNS。

---

## 快速开始

### 1. 电脑端（Windows）

把这三份文件放到电脑同一目录，管理员 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1
```

它会装依赖、生成两个 32 位令牌、用 `pythonw` 后台起、注册登录自启，最后打印两行地址：

```
Agent API : https://pcrelay.pages.dev/api?room=<令牌A>
触屏画面  : https://pcrelay.pages.dev/?room=<令牌B>
```

细节与参数见 [docs/WINDOWS.md](docs/WINDOWS.md)。

### 2. 手机端

```sh
pcc init "https://pcrelay.pages.dev/api?room=<令牌A> https://pcrelay.pages.dev/?room=<令牌B>"
pcc conf     # 核对解析出的两个令牌
pcc info     # 返回机器信息 = 通了
```

装法：

```sh
install -m 0755 bin/pcc /usr/local/bin/pcc
```

### 3. 开始用

```sh
pcc shot                                    # 截屏
pcc sh 'Get-Process | Sort CPU -Desc | Select -First 5'
pcc win list
pcc win click "记事本" 0.5 0.6                # 抢前台 + 窗口内落光标
pcc type "你好"                              # 中文可打
pcc fs ls 'C:/Users'
pcc diag                                     # 一键体检
```

---

## 命令速查

| 类别 | 命令 |
|---|---|
| 配置 | `pcc init` · `pcc conf` · `pcc link` · `pcc room` |
| 信息 | `pcc info` · `pcc ping` · `pcc session` · `pcc net` · `pcc diag` |
| 执行 | `pcc sh '<PowerShell>'` |
| 屏幕 | `pcc shot [文件] [宽]` · `pcc pw screenshot` |
| 鼠标 | `pcc move` · `pcc click` · `pcc dblclick` · `pcc scroll` · `pcc drag` |
| 键盘 | `pcc type` · `pcc key` |
| 窗口/程序 | `pcc win list\|focus\|click` · `pcc app start\|kill` |
| 文件 | `pcc fs ls\|read\|write\|mkdir\|rm\|get\|put` |
| 剪贴板 | `pcc clip get\|set` |
| 浏览器 | `pcc pw goto\|fill\|eval\|text\|screenshot` · `pcc pwscript` |
| 电脑运维 | `pcc svc` · `pcc logs` · `pcc view` · `pcc lan` · `pcc startup` · `pcc nolock` |

完整参数：[docs/OPS.md](docs/OPS.md)（运维） · [docs/PROTOCOL.md](docs/PROTOCOL.md)（接口）

---

## 目录结构

```
bin/pcc                 手机端客户端（单文件 Python，零依赖）
bin/pl                  在 ProotLinux 客户机里执行命令的启动器
bin/make-kit.py         打包成 zip
win/agent_bridge.py     电脑端桥（连中继、执行方法、推画面、注入键鼠）
win/install-bridge.ps1  一键安装（依赖 + 令牌 + 后台 + 自启）
win/run-bridge.bat      前台运行（看日志）
win/winctl              SSH 通道客户端（setup/ssh/files/get/put/sync/rdp）
setup-pc.ps1            备用通道：OpenSSH + 防火墙收紧 + RDP
tools/                  OCR / 分段下载 / 中继协议探针（探明接口时用的）
dev/                    mock 电脑端、回归套件、协议探针
dev/archive/            一次性调试脚本（保留作参考，不维护）
docs/                   协议实测表 / 运维手册 / Windows 安装 / SSH 通道
```

## 已知限制

- **锁屏时**桌面截图与键鼠注入不可用（Windows 安全桌面机制，RDP 同理）；
  `pw`/`shell`/`fs`/`clip` 照常。建议 `pcc awake on` 让电脑空闲时抖鼠标防锁屏。
- 投屏画面约 4 fps（`client_relay.py` 默认参数，可调 `--fps`）。
- 令牌即凭证：拿到 `room` 的人能看画面、操作键鼠。换令牌用 `install-bridge.ps1 -NewToken`。

## 开发

仓库：https://github.com/fu-anxiang/agentphone-control-pc

```sh
git clone git@github.com:fu-anxiang/agentphone-control-pc.git
cd agentphone-control-pc
install -m 0755 bin/pcc /usr/local/bin/pcc
```

改完代码跑回归：

```sh
cp bin/pcc /tmp/pccmod.py     # 套件从固定路径导入
python3 dev/suite_real.py     # 24 项接口（需电脑端在线）
python3 dev/suite_ops.py      # 9 项运维命令
```

没有电脑端时，用 mock 冒充：

```sh
python3 dev/mockpc.py mock-room 300      # 起一个假电脑
PCC_ROOM=mock-room python3 dev/selftest.sh
```

协议探针（`dev/probe_api*.py`）是当初反推接口用的脚本，保留下来方便以后
接口再变时快速重新摸一遍。发布与拉取细节见 [docs/PUBLISH.md](docs/PUBLISH.md)。


## 许可证

未指定。如需开源发布，建议补一个（MIT / Apache-2.0）。
