# 手机控制电脑 —— 更新日志

## v0.5.0 · 2026-10-22

### 新增：可复用的 Coomi Skill（`skill/controlling-windows-pc`）

把整套操作知识封装成 Skill，下次开新会话直接加载，不用重新探协议：

- 两条通道怎么选（`pcc` 中继 / `winctl` SSH）
- **每场开场固定动作**：`pcc conf` + `pcc diag`（10 项），别盲试
- 命令速查（执行 / 屏幕 / 键鼠 / 窗口 / 文件 / 剪贴板 / 浏览器 / 运维）
- **四个参数名陷阱**（`value`/`match`/`count`/`set`/`content`/`scroll`）——写错不报错只静默失效
- 锁屏的正确处理（不是绕过，是别让它锁）
- 故障 → 命令 对照表
- 改完代码的回归流程（33 项）

安装：`cp -r skill/controlling-windows-pc ~/.coomi/skills/`

### 新增：凭据集中管理

`~/.config/pcc/secrets.env`（600）保存 `GITHUB_TOKEN`、仓库信息、两把 SSH 私钥路径。
**不写进 Skill 正文、不写进仓库** —— skill 只引用路径，泄了只需删一个文件。

房间令牌仍在 `~/.pcc.env`（`pcc init` 写入），SSH 私钥仍在 `~/.ssh/`（600）。

## v0.4.0 · 2026-10-22

### 新增：中继源码入仓（`relay/`）

整套系统现在**自包含**，不再依赖别人部署的中继：

- `relay/wrangler.toml` —— Pages 项目配置（DO 绑定走 `script_name`）
- `relay/functions/[[path]].js` —— Pages Function：`/ws`、`/api` 转发给 DO，`/health` 直接回 JSON
- `relay/public/index.html` —— 手机投屏网页（触屏→鼠标、软键盘、滚轮、全屏）
- `relay/do-worker/**` —— Durable Object：双端 WS 中继 + HTTP-over-WS 隧道（55s 超时、
  PC 掉线时让在途请求立即 `pc_disconnected`）
- `relay/README.md` —— 部署步骤、为什么要拆 Pages + Worker、错误码、自建方法

### 新增：两个命令

- `pcc health` —— 中继自身健康检查（`GET /health`，不需要令牌、不需要电脑在线）
- `pcc get [方法]` —— 用 `GET /api?m=…` 调无参方法（默认 `info`），不方便发 body 时用

### 协议补充（实测）

- `GET /api?m=ping&room=X` 是**可用**的，不带 `m` 时默认 `info`；GET 的 `p` 恒为空
- `GET /health` → `{"ok":true,"relay":"pcrelay"}`
- 错误码补全：`pc_offline`(503) / `timeout`(504) / `pc_disconnected` / `missing_method`(400) / `method_not_allowed`(405)

## v0.3.0 · 2026-10-21

### 新增：电脑端运维命令（对应 pcremote 的 17 项能力）

- `pcc svc status|start|stop|restart` —— 守护进程与两条通道
- `pcc logs [bridge|view|supervisor|all] -n N -g 关键字`
- `pcc view status|url|qr` —— 触屏画面通道
- `pcc room` —— 电脑端 `ROOM.txt` 与本机配置逐项比对
- `pcc lan status|start|stop` —— 局域网直连（`server.py:8765`）
- `pcc startup status|install|remove` —— 开机自启项
- `pcc nolock status|apply` —— 防锁屏硬化
- `pcc net` —— 网卡 IP / 公网出口 / 通道在线 / 中继往返
- `pcc diag` —— 一键体检（10 项）

### 修复

- **`svc stop/restart` 会把电脑弄失联**：`supervisor.py --stop` 用 `taskkill /T`
  杀整棵进程树，连正在执行命令的 PowerShell 一起杀，导致"重启"那一步永远执行不到。
  改为写 ASCII `pcc-svc.bat` + WMI `Win32_Process.Create` 脱管执行。
- PowerShell 里 `\"` 不是转义符，拼接 `cmd /c "…"` 直接语法错误 → 改走 .bat。
- 日志/`ROOM.txt` 读出乱码（UTF-8 无 BOM，PS 5.1 按 GBK 读）→ 显式 `-Encoding UTF8`。
- `pcc room` 把 View 令牌误判成 Agent（`/api?room=` 与 `/?room=` 混用同一正则）。
- `pcc fs put` 的 `*.b64tmp` 中转文件在失败时残留 → `finally` 里清理。
- `svc stop` 增加 `--yes` 门槛（停了就无法远程拉起）。

## v0.2.0 · 2026-10-21

### 按真实接口重写手机端（此前是猜的，参数名错会静默失效）

读到电脑端 `agent_bridge.py` / `server.py` 源码后修正：

| 项 | 原先 | 实际 |
|---|---|---|
| 打字 | `input.type` 的 `text` | `value` |
| 抢前台 | `focus` 的 `title` | `match` |
| 点击次数 | `click` 的 `n` | `count` |
| 写剪贴板 | `action=set` + `text` | `set` |
| 写文件 | `fs.write` 的 `b64` | `content`（+`append`） |
| 文件动作 | `ls` / `cat` | `list` / `read` |
| 滚轮 | `wheel` | `scroll` |

### 新增

- `pcc session` / `pcc awake on|off` —— 锁屏与空闲状态、防锁屏保活
- `pcc win click <标题> <fx> <fy>` —— 抢前台并在窗口内相对位置落光标（打字前的正确姿势）
- `pcc dblclick` / `pcc drag`
- `pcc fs mkdir|rm|get|put` 二进制走 base64（md5 校验一致）
- 中继偶发 `RemoteDisconnected` 自动重试 3 次 + 中文提示

### 验证

24 项接口测试全通过：只读接口、截图、文本写读追加、二进制往返、
中文打字 + Ctrl+A 组合键（OCR 校验）、鼠标、剪贴板、保活。

## v0.1.0 · 2026-10-21

### 新增

- 新版 32 位双令牌协议支持：Agent 房间与投屏房间互相独立
- `pcc init` 自动解析电脑端打印的两行地址；`pcc conf` 核对令牌位数
- 电脑端兼容桥 `win/agent_bridge.py`（双房间 + 配置持久化 + 二维码 + 握手错开 1.5s）
- `win/install-bridge.ps1` 一键安装（依赖 / 令牌 / 后台 / 自启）
- 备用通道：`setup-pc.ps1` + `win/winctl`（OpenSSH + Tailscale + RDP）
- 协议探针 `dev/probe_api*.py`、mock 电脑端 `dev/mockpc.py`、回归套件 `dev/suite_real.py`
