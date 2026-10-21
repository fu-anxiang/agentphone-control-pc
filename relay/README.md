# cf-edge-relay —— 边缘中继源码

手机与电脑跨公网互联的中间件。跑在 Cloudflare 边缘：

- **Pages**（`pcrelay.pages.dev`）提供手机投屏网页 + 路由转发
- **Durable Object**（`pcrelay-do`）做双端 WebSocket 中继 + HTTP-over-WS 隧道

两端都只做出站连接，**不需要公网 IP、不用开端口、不用 DDNS**。

```
手机 agent ──HTTPS POST /api?room=X──▶ Pages Function ──▶ DO(Relay) ──WS──▶ 电脑 agent_bridge.py
手机浏览器 ──WSS /ws?role=phone&room=Y──▶ Pages Function ──▶ DO(Relay) ──WS──▶ 电脑 client_relay.py
```

## 结构

| 路径 | 作用 |
|---|---|
| `wrangler.toml` | Pages 项目配置；把 DO 类 `Relay` 通过 `script_name = "pcrelay-do"` 绑到 `env.RELAY` |
| `functions/[[path]].js` | Pages Function，捕获全部路由：`/ws`、`/api` 转给 DO，`/health` 直接回 JSON |
| `public/index.html` | 手机投屏网页（触屏→鼠标、软键盘、滚轮、全屏），连 `wss://…/ws?role=phone&room=` |
| `do-worker/wrangler.toml` | DO Worker 配置（含 `[[migrations]]`，只有独立 Worker 才支持） |
| `do-worker/src/index.js` | `Relay` 类：WS 广播转发、HTTP `POST /api` 的 RPC 等待与超时、PC 掉线时让在途请求立即失败 |

## 为什么要拆成 Pages + 独立 Worker

Pages 的 `wrangler.toml` **不支持 `[[migrations]]`**，而 Durable Object 类必须有 migration 才能创建。
所以 DO 放在独立的 Worker（`pcrelay-do`）里，Pages 通过 `script_name` 绑定调用它。
`pcrelay-do` 本身不需要任何对外路由（`workers.dev` 被封也不影响）。

## 部署

```sh
# 1) 先部署 DO Worker（改过 Relay 类或 migration 才需要重跑）
cd do-worker
wrangler deploy

# 2) 再部署 Pages
cd ..
wrangler pages deploy public --project-name pcrelay --commit-dirty=true
```

> **坑**：必须把 `public` 目录作为 deploy 目标传进去。
> 直接 `wrangler pages deploy .` 会把 `index.html` 放到 `/public/index.html`，根路径 404。

首次创建 Pages 项目：

```sh
wrangler pages project create pcrelay
```

## 接口

| 路径 | 说明 |
|---|---|
| `GET /health` | `{"ok":true,"relay":"pcrelay"}` |
| `WSS /ws?role=pc&room=X` | 电脑端接入（接收请求、推画面帧） |
| `WSS /ws?role=phone&room=Y` | 手机投屏页接入 |
| `POST /api?room=X`，body `{"m":..,"p":{..}}` | 调电脑端方法；`room` 也可用 `X-Room` 头 |
| `GET /api?m=ping&room=X` | **GET 也行**（不带 `m` 默认 `info`），适合不方便发 body 的客户端 |

响应：

```
{"id":"r...","ok":true,"r":{...}}          成功
{"id":"r...","ok":false,"e":"ValueError: ..."}  电脑端执行报错
{"ok":false,"e":"pc_offline"}  503          电脑端没连上
{"ok":false,"e":"timeout","id":"r..."}  504  电脑端 55s 内没回
{"ok":false,"e":"missing_method"}  400      没给 m
{"ok":false,"e":"pc_disconnected"}          电脑端中途掉线（比等 55s 超时友好）
```

## 房间名

房间名就是凭证，**不做任何前缀归一**：

- `agent-66151656` 与 `66151656` 是**两个房间**
- 新版（`pcconfig.py`）用 `secrets.token_urlsafe(24)[:32]` 生成 32 位令牌，Agent 房间与投屏房间**各一个、互不派生**

知道房间名的人可以看画面、操作键鼠。换令牌 = 换房间名，旧链接立即失效。

## 安全提醒

- 本目录**不含任何密钥**。`account_id`、API Token 等凭据放在
  `wrangler` 的全局配置（`~/.wrangler/config/`）或环境变量 `CLOUDFLARE_API_TOKEN` 里，不要提交。
- 中继本身不校验身份，**房间名就是唯一凭证**。生产使用建议：
  1. 令牌足够长（32 位，本仓库默认）
  2. 泄露后立刻换：电脑端 `install-bridge.ps1 -NewToken` 或官方 `pcconfig.py` 删除 `config.json` 后重启
  3. 中继域名对外公开没关系，房间名不公开即可

## 自建一套自己的中继

改 `wrangler.toml` 里的 `name`，然后：

```sh
wrangler pages project create <你的项目名>
cd do-worker && sed -i 's/pcrelay-do/<你的DO名>/g' wrangler.toml && wrangler deploy
cd .. && wrangler pages deploy public --project-name <你的项目名> --commit-dirty=true
```

手机端把地址换成你自己的域名即可：

```sh
pcc init "https://<你的域名>/api?room=AAAA https://<你的域名>/?room=BBBB"
```

> 为什么用 `*.pages.dev`：`ccwu.cc` 那类域名会**整域按 SNI 字符串被阻断**（实测任何子域都 reset），
> 而 `*.pages.dev` 在国内可直连。换域名时先确认手机网络能访问。

## 已知行为

- **同一出口 IP 并发 WS 握手会被排队**：两个房间同时连，第二个可能等十几秒才上线。
  所以电脑端两个连接要错开约 1.5 秒（`win/agent_bridge.py` 已处理）。
- 投屏帧是**二进制 JPEG**，靠链路层帧边界区分，不带长度头。
- `RPC_TIMEOUT_MS = 55000`：电脑端执行超 55 秒的请求会被中继判超时（`shell` 长任务请调小 `timeout`）。
- Durable Object 只用内存中的 `pending` Map，**实例重启会丢在途请求**（客户端会看到 `timeout`）。
