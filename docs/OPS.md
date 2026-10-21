# 电脑端运维命令

对应电脑上 `pcremote` 目录里的守护进程、日志、投屏通道、局域网模式、自启、防锁屏。
全部在真机上跑通过（见 `dev/suite_ops.py`）。

```sh
pcc svc status                  # 守护进程 + 两条通道 + 局域网模式：谁在跑、什么参数
pcc svc restart                 # 脱管重启（停 → 3s → 起），不需要在电脑旁
pcc svc start                   # 守护没在跑时拉起（单实例锁，重复调用安全）
pcc svc start --only view       # 只拉起投屏通道
pcc svc stop --yes              # ⚠ 会把 Agent API 通道一起停，之后只能到电脑前手动启动

pcc logs                        # bridge / view / supervisor 三个日志尾部
pcc logs bridge -n 50           # 指定条数
pcc logs all -g "失败|error"     # 关键字过滤

pcc view status                 # 触屏画面通道状态 + 启动参数 + 日志尾
pcc view url                    # 手机投屏地址
pcc view qr [本地路径]           # 取/生成 qr_view.png 二维码

pcc room                        # 读电脑端 ROOM.txt，与手机配置逐项比对
pcc lan status                  # 局域网直连（server.py:8765）状态、防火墙、本机 IP
pcc lan start                   # 起局域网直连，打印 http://192.168.x.x:8765/?t=<token>
pcc lan stop                    # 停局域网直连

pcc startup status              # 开机自启项是否已装、目标与参数
pcc startup install / remove    # 装/卸（当前用户启动文件夹，免管理员）

pcc nolock status               # 屏保 / 不活动锁定 / NoLockScreen / 显示器超时
pcc nolock apply                # 跑 never_lock_admin.ps1（电脑上会弹 UAC，需点「是」）

pcc net                         # 网卡 IP、公网出口、两通道在线、中继往返
pcc diag                        # 一键体检（10 项）
```

## 这些命令背后的坑

| 坑 | 说明 |
|---|---|
| **`svc stop/restart` 必须"脱管"** | `supervisor.py --stop` 用 `taskkill /T` 杀整棵进程树，连正在执行命令的 PowerShell 一起杀。直接调用的话"重启"那一步永远执行不到，**电脑就失联了**。解决办法：先往电脑写一个 ASCII 的 `pcc-svc.bat`，再用 WMI `Win32_Process.Create` 起进程（父进程是 `WmiPrvSE`，不在被杀树里） |
| `svc stop` 要 `--yes` | 停了就没通道把自己拉回来，必须人在电脑前 |
| PowerShell 里 `\"` 不是转义符 | 拼接 `cmd /c "...bat"` 用 PS 单引号字符串或直接写 .bat，别用反斜杠转义（实测报 `表达式或语句中包含意外的标记`） |
| 日志读出来乱码 | 日志是 UTF-8 无 BOM，PS 5.1 默认按 GBK 读 → 必须 `Get-Content -Encoding UTF8` |
| 两个令牌别用同一个正则抓 | API 是 `/api?room=`，投屏是 `/?room=`；混用会把 View 误判成 Agent（`pcc room` 曾因此报"不一致"） |
| 局域网 token | `server.py` 不传 `--token` 就随机 6 字节、抓不到；`pcc lan start` 自己生成并打印完整链接 |
| 二进制上传中转文件 | `fs put` 二进制走 `*.b64tmp` 中转，无论成败都在 `finally` 里删掉，避免在电脑上留垃圾 |

## 电脑端目录（pcremote 参考）

| 文件 | 作用 |
|---|---|
| `server.py` | 截图 / 键鼠注入底层（`agent_bridge` 会 import，不能删） |
| `agent_bridge.py` | 手机 agent 的 HTTP API 执行器 |
| `client_relay.py` | 触屏画面通道（推 JPEG 帧） |
| `supervisor.py` | 守护：崩溃重启 + 单实例锁 + 日志轮转 |
| `pcconfig.py` | 32 位令牌生成/持久化 |
| `config.json` | 当前 `agent_room` / `view_room`（**不要提交到仓库**） |
| `ROOM.txt` | 两条链接的可读副本 |
| `qr_view.png` | 触屏画面二维码 |
| `install_startup.ps1` | 装/卸开机自启 |
| `never_lock_admin.bat` / `.ps1` | 防锁屏硬化（需管理员） |
| `run_lan.ps1` | 局域网直连模式（独立） |
| `mkqr.py` | 生成二维码 |
| `logs/` | `bridge.log` / `view.log` / `supervisor.log`（轮转 2 MB） |
| `.supervisor.pid` / `.supervisor.lock` | 单实例锁 |

## 锁屏时还能做什么

| 方法 | 锁屏时 | 原因 |
|---|---|---|
| `shell` / `app` / `fs` / `clip(set)` | ✅ | 不依赖桌面 |
| `pw`（含 `pw screenshot`） | ✅ | CDP 截的是**页面**，不是屏幕 |
| `pwscript` | ✅ | 同上 |
| `screenshot`（整屏） | ❌ `session_locked` | 安全桌面拿不到像素 |
| `input`（键鼠） | ❌ `session_locked` | SendInput 被丢 |
| `windows` / `focus` / `click_window` | ⚠️ 列表能读，前台操作无效 | 前台不是你那个会话 |

这是 Windows 的安全设计（防偷屏/注键），**RDP 也一样**。
正确思路是"别让它锁"：`pcc awake on`（20s 一次 `SetThreadExecutionState`，
空闲 ≥45s 抖 1px 鼠标），加上 `pcc nolock apply` 关掉屏保/不活动锁定。
