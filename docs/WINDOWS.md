# 电脑端（Windows）安装

两种跑法，任选：

- **A. 用你已有的官方客户端**（`pcremote` 目录里的 `agent_bridge.py` + `supervisor.py`）——
  功能最全，`pcc` 就是照它的实测协议写的。
- **B. 用本仓库自带的兼容桥** `win/agent_bridge.py` —— 同一套参数名，可以顶替。

## A. 官方客户端

```powershell
cd C:\Users\<你>\Documents\for_phone\pcremote
python pcconfig.py            # 首次生成两个 32 位令牌，写进 config.json
python supervisor.py          # 同时跑 agent API + 触屏画面两个通道
# 链接写在 ROOM.txt，二维码 qr_view.png
```

开机自启：`.\install_startup.ps1`（装到当前用户启动文件夹，`pythonw` 无窗口）。
停守护：`python supervisor.py --stop`。

手机端把 `ROOM.txt` 里那两行整段粘给 `pcc init` 即可。

## B. 本仓库的兼容桥

三份文件放电脑同一目录，管理员 PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\install-bridge.ps1
```

它做四件事：

1. 检查/安装 Python 依赖 `websockets`、`pillow`（可选 `qrcode` 生成二维码）
2. 生成或沿用**两个 32 位令牌**（存 `%USERPROFILE%\.pcremote\config.json`）
3. 用 `pythonw` 后台启动（无窗口），日志写同目录 `bridge.log`
4. 注册登录自启计划任务 `pcrelay-bridge`

```powershell
.\install-bridge.ps1 -NewToken                   # 换一对新令牌（旧地址立即失效）
.\install-bridge.ps1 -Room AAAA -ViewRoom BBBB   # 手工指定
.\install-bridge.ps1 -NoAuto                     # 不设自启
run-bridge.bat                                   # 前台跑，能看见实时日志
```

启动横幅会打印两行地址，并生成 `qrview.png` 供手机扫码。

### 桥支持的方法

与官方口实同名同参数（`value`/`match`/`count`/`set`/`content`…）：

| m | 参数 | 说明 |
|---|---|---|
| `info` / `session` | – | 机器信息 / 会话状态 |
| `keep_awake` | `on` | 记录保活开关 |
| `shell` | `cmd`, `timeout` | PowerShell 执行，返回 `code/out/err` |
| `screenshot` | `quality`, `max_width` | 整屏 JPEG(base64) |
| `input` | `action=move/abs/click/dblclick/rightclick/down/up/scroll/type/key` | SendInput 注入，Unicode 打字 |
| `windows` / `focus` | `match` | 枚举窗口 / 抢前台 |
| `app` | `start`(`target`) / `kill`(`pid` 或 `name`) | 启动 / 结束 |
| `fs` | `action=list/read/write/mkdir/delete` | 文件操作（`content`/`append`/`max_bytes`） |
| `clip` | 无参 = 读，`set` = 写 | 剪贴板 |
| `pw` / `pwscript` | 见 [PROTOCOL.md](PROTOCOL.md) | Playwright 持久会话 |

桥同时连**两个房间**：Agent 令牌房间收 API 请求，投屏令牌房间按 4 fps 推 JPEG 帧（带 ack 限流）。
两个握手错开 1.5 s，避免同一出口 IP 的并发 WS 被中继排队。

要求：Python 3.9+；`pip install websockets pillow`；`pcc pw …` 需 `pip install playwright`。
防火墙无需改动（全部是出站 HTTPS/WSS）。

## 排查

| 现象 | 处理 |
|---|---|
| `电脑离线：电脑端没连上` / `pc_disconnected` | 电脑端没在跑，或 **Agent 令牌**不一致（`pcc conf` 与电脑端打印的对一遍）。中继偶发断连会自动重试 3 次 |
| 旧地址完全没反应 | 新版令牌 32 位且与旧版不兼容，必须重新生成 |
| 投屏一片黑 | 用了 **Agent 令牌**去看画面；画面房间是另一个令牌（`?room=<令牌B>`） |
| `HTTP 403 error code: 1010` | Cloudflare 按 UA 拦；请求要带正常 `User-Agent`（`pcc` 已带） |
| 打字/点击"返回 ok 但没反应" | 参数名是 `value`/`match`/`count`；锁屏会被丢弃；`shell` 抢焦点后要重新 `pcc win click` |
| `session_locked` | 电脑锁屏了：键鼠与整屏截图不可用，用 `pw`/`shell`/`fs` 或 `pcc awake on` |
| 截图很慢 | 降 `max_width`（`pcc shot /tmp/x.jpg 1280`）或用 `pcc pw screenshot` 拍网页 |
| 重启后地址变了 | 令牌持久化在 `config.json`，重启沿用；只有 `-NewToken` 才换 |

## 编码铁律（踩过两次）

| 文件 | 必须 | 原因 |
|---|---|---|
| `.bat` | **纯 ASCII** | cmd.exe 按 OEM 代码页读，UTF-8 中文会被撕碎，命令被拆行 |
| `.ps1` | **UTF-8 with BOM** | PS 5.1 把无 BOM 的 UTF-8 当 GBK 解析，中文字符串报 "missing terminator" |
| `.vbs` | ANSI/GBK | cscript 按 ANSI 读 |

本仓库的 `bin/fix-win-files.sh` 会自动做这两件事（BOM + CRLF）。
