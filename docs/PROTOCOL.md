# 协议实测参考

> 这张表是**逐条发请求验证过**的结果，不是从文档抄的。
> 反推方法见 `dev/probe_api*.py`；接口再变时照着重跑一遍即可。

## 架构

```
手机 agent ──HTTPS POST──▶ pcrelay.pages.dev/api?room=<令牌A> ──WS──▶ 电脑 agent_bridge.py
手机浏览器 ──WSS /ws?role=phone&room=<令牌B>──▶ 同一中继 ──▶ 电脑（JPEG 画面 + 鼠标键盘事件）
```

- 中继：`https://pcrelay.pages.dev`（Cloudflare 边缘，Durable Object）——源码在 [`relay/`](../relay/README.md)
- Agent API：`POST .../api?room=<令牌A>`，body `{"m": 方法, "p": {...}}`
- 简写：`GET .../api?m=ping&room=<令牌A>` 也行（不带 `m` 默认 `info`；**GET 的 `p` 恒为空**）
- 健康检查：`GET .../health` → `{"ok":true,"relay":"pcrelay"}`（不需要令牌）
- 响应：`{"id":..,"ok":true,"r":{...}}` 或 `{"id":..,"ok":false,"e":"ValueError: ...","tb":"..."}`
- 投屏：`https://pcrelay.pages.dev/?room=<令牌B>`

### 中继错误码

| 返回 | 含义 |
|---|---|
| `{"ok":false,"e":"pc_offline"}` 503 | 电脑端没连上这个房间 |
| `{"ok":false,"e":"timeout","id":..}` 504 | 电脑端 55 秒内没回（中继 `RPC_TIMEOUT_MS`） |
| `{"ok":false,"e":"pc_disconnected"}` | 请求在路上时电脑端掉线（比等超时快） |
| `{"ok":false,"e":"missing_method"}` 400 | 没给 `m`（常见于 PowerShell 吞引号） |
| `{"ok":false,"e":"method_not_allowed"}` 405 | 用了 PUT/DELETE |

## 新版权令（2026-10 变更）

| 项 | 旧版 | 新版 |
|---|---|---|
| 令牌位数 | 24 位（`token_urlsafe(24)[:24]`，被截断） | **32 位**（`token_urlsafe(24)` 原始长度） |
| 房间关系 | 同一个码，API 走 `agent-<码>`，投屏走 `<码>` | **两个独立令牌**，互不派生 |
| 旧链接 | — | 全部失效 |

电脑端桥要**同时连两个房间**；同一出口 IP 并发 WS 握手会被中继排队，
两个连接要错开约 1.5 秒，否则第二个房间要等十几秒才上线。

Cloudflare 会按 UA 拦默认的 `Python-urllib`（返回 `403 error code: 1010`），
请求必须带正常 `User-Agent`。

## 方法表

| 方法 | 参数（**实测**） | 返回 |
|---|---|---|
| `ping` | – | `pong`, `room`, `calls` |
| `info` | – | `host`, `os`, `screen:{w,h}`, `cursor`, `uptime`, `pw_open`, `python`, `locked`, `idle` |
| `session` | – | `locked`, `idle`, `screen`, `keep_awake`, `jiggles`, `hint` |
| `keep_awake` | `on` | `on` |
| `shell` | `cmd`, `cwd?`, `timeout?` | `code`, `out`, `err` |
| `screenshot` | `quality?`(默认 60), `max_width?`(默认 1600), `force?` | `b64`(JPEG) 或 `{"e":"session_locked"}` |
| `input` | `action`：`move`(`x`,`y` **像素** / `dx`,`dy` 相对) / `abs`(0~1) / `click`(`button`,`count`) / `dblclick` / `rightclick` / `down` / `up` / `scroll`(`dy`) / **`type`(`value`)** / `key`(`key`,`mods`) / `click_window`(`match`,`fx`,`fy`) | `cursor` |
| `windows` | – | `windows:[{hwnd,title,pid}]` |
| `focus` | **`match`**（标题片段） | `window:{hwnd,title,foreground}` |
| `app` | `start`(`target`,`args?`) / `kill`(`pid` 或 `name`) | `pid` / `ok` |
| `fs` | `action`：`list` / `read`(`path`,`max_bytes?`,`encoding?`) / `write`(`path`,`content`,`append?`) / `mkdir` / `delete` | `items` / `text,truncated` / `bytes` |
| `clip` | 无参 = 读；**`set` = 写** | `text` / `chars` |
| `pw` | `action`：`goto`/`open`(`url`) · `url` · `click`(`selector` 或 `text`) · `fill`(`selector`,`value`) · `type` · `press`(`key`) · `text` · `html` · `attr` · `eval`(`js`) · `count` · `screenshot` · `back` · `reload` · `wait` · `newpage` · `pages` · `use` | 因动作而异 |
| `pwscript` | `code`（Python，作用域有 `page/context/browser`；`return x` 或 `result = x` 取值） | `result` |

### 参数名对照（最容易踩）

| 你以为是 | 实际是 |
|---|---|
| `input.type` 的 `text` | **`value`** |
| `focus` 的 `title` | **`match`** |
| `click` 的 `n` | **`count`** |
| `clip` 的 `action=set` + `text` | **`set`** |
| `fs.write` 的 `b64` | **`content`**（+`append`） |
| `fs` 的 `ls` / `cat` | **`list`** / **`read`** |
| `input` 的 `wheel` | **`scroll`** |

**参数名写错不会报错，只会静默无效果** —— 这是调试时最坑的地方。

## 四个必须知道的坑

1. **`shell` 会短暂抢走前台焦点**（它起了一个 PowerShell 控制台窗口）。
   "抢窗口前台 → 打字"要连着做，中间别插 `shell`。
2. **`pw` 默认是无头浏览器**，有自己的页面；SendInput 打的字进不去。
   往网页里填字用 `pw fill`，操作桌面可见窗口才用 `input type`。
3. **锁屏时**桌面截图与键鼠注入都不可用（返回 `session_locked`），
   但 `pw`/`shell`/`fs`/`clip` 照常。用 `keep_awake` 防锁屏。
4. **剪贴板**在 ctypes 里必须声明 `argtypes/restype`，否则 64 位 HANDLE 被当 `c_int` 截断，
   读出永远为空。

## 实测数据（2026-10-21，Win11 Pro / 3840×2160）

| 项 | 结果 |
|---|---|
| 只读接口（info/ping/session/shell/windows/fs list/clip） | 7/7 通过，1.0–7.3 s |
| 截图 1280 宽 | 70 KB，约 2 s |
| 文本写/读/追加 | 中英混排正确 |
| 二进制往返 | PNG 上传 → 电脑端解码 → 下载回，**md5 一致** |
| 键盘打字 | 记事本先打 `AAA-111`，Ctrl+A 全选，再打 `BBB-中文-222`；OCR 校验只剩后者 |
| 鼠标 | move / click / scroll / 窗口内相对点击均生效 |
| 剪贴板 | 写入后读回一致 |
| 保活 | `keep_awake` 开关正常，抖动计数递增 |

## 直接调接口（不经 pcc）

```python
import requests

B, R = "https://pcrelay.pages.dev/api", "<令牌A>"


def call(m, **p):
    return requests.post(B, params={"room": R}, json={"m": m, "p": p},
                         headers={"user-agent": "my-agent/1.0"}, timeout=90).json()


print(call("shell", cmd="hostname")["r"]["out"])
call("pw", action="goto", url="https://example.com")
print(call("pw", action="text", selector="h1")["r"]["text"])
```

不想发 body 的时候可以用 GET（`p` 恒为空，只适合 `info` / `ping` / `session` 这类无参方法）：

```sh
curl "https://pcrelay.pages.dev/api?room=<令牌A>&m=ping"
curl "https://pcrelay.pages.dev/api?room=<令牌A>"        # 不带 m 默认 info
curl "https://pcrelay.pages.dev/health"                  # 中继自身健康检查，不需要令牌
```

对应的 `pcc` 命令：`pcc get ping`、`pcc get`（=info）、`pcc health`。

多步有状态的浏览器自动化用 `pwscript`：

```python
call("pwscript", code='''
await page.goto("https://example.com", wait_until="domcontentloaded")
await page.click("a")
result = {"url": page.url, "h1": await page.locator("h1").all_inner_texts()}
''')
```

> PowerShell 里别内联写 JSON（会吞引号，报 `missing method`），
> 用 `--data-binary @req.json` 或改用 Python。
