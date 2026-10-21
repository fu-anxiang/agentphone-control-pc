// Durable Object: 双端 WebSocket 中继 + HTTP-over-WS 隧道
//  - WS: role=phone / role=pc 互相转发（手机网页看画面用）
//  - HTTP: POST /api {m,p}  ->  转发给 role=pc 连接，等它回 {id,ok,r}
//    这样手机上的 agent 直接用 curl/fetch 调电脑，无需装任何客户端

const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const RPC_TIMEOUT_MS = 55000;

function jres(obj, status = 200) {
  return new Response(JSON.stringify(obj), { status, headers: JSON_HEADERS });
}

function roleOf(ws) {
  try {
    const a = ws.deserializeAttachment();
    return (a && a.role) || "peer";
  } catch (e) {
    return "peer";
  }
}

export class Relay {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.pending = new Map(); // id -> resolve(Response)
  }

  async fetch(request) {
    const url = new URL(request.url);
    const isWs = request.headers.get("Upgrade") === "websocket";

    if (isWs) {
      const role = url.searchParams.get("role") || "peer";
      const pair = new WebSocketPair();
      const client = pair[0];
      const server = pair[1];
      this.state.acceptWebSocket(server);
      try { server.serializeAttachment({ role }); } catch (e) {}
      this.broadcast(server, JSON.stringify({ t: "peer", event: "join", role }));
      return new Response(null, { status: 101, webSocket: client });
    }

    // ---- HTTP -> PC 的 RPC 隧道
    if (request.method !== "POST" && request.method !== "GET") {
      return jres({ ok: false, e: "method_not_allowed" }, 405);
    }
    const pcs = this.state.getWebSockets().filter((w) => roleOf(w) === "pc");
    if (!pcs.length) {
      return jres({ ok: false, e: "pc_offline", hint: "电脑端 agent_bridge.py 没连上" }, 503);
    }
    let payload = {};
    if (request.method === "POST") {
      try { payload = await request.json(); } catch (e) { payload = {}; }
    } else {
      payload = { m: url.searchParams.get("m") || "info", p: {} };
    }
    if (!payload.m) return jres({ ok: false, e: "missing_method" }, 400);

    const id = "r" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    const msg = JSON.stringify({ id, m: payload.m, p: payload.p || {} });

    const resp = await new Promise((resolve) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        resolve(jres({ ok: false, e: "timeout", id }, 504));
      }, RPC_TIMEOUT_MS);
      this.pending.set(id, (data) => {
        clearTimeout(timer);
        this.pending.delete(id);
        resolve(jres(data, 200));
      });
      const target = pcs[0];
      try {
        target.send(msg);
      } catch (e) {
        clearTimeout(timer);
        this.pending.delete(id);
        resolve(jres({ ok: false, e: "send_failed" }, 500));
      }
    });
    return resp;
  }

  peers(ws) {
    const out = [];
    for (const w of this.state.getWebSockets()) {
      if (w !== ws) out.push(w);
    }
    return out;
  }

  broadcast(from, data) {
    for (const w of this.peers(from)) {
      try { w.send(data); } catch (e) {}
    }
  }

  async webSocketMessage(ws, msg) {
    if (typeof msg === "string") {
      try {
        const o = JSON.parse(msg);
        if (o && o.id && this.pending.has(o.id)) {
          this.pending.get(o.id)(o);
          return;
        }
      } catch (e) {}
    }
    this.broadcast(ws, msg);
  }

  async webSocketClose(ws, code, reason) {
    // 有 PC 掉线时，把等在路上的 RPC 立刻失败掉，别让手机上等到 504
    if (roleOf(ws) === "pc") {
      for (const [id, resolve] of this.pending.entries()) {
        resolve({ ok: false, e: "pc_disconnected", id });
      }
      this.pending.clear();
    }
    this.broadcast(ws, JSON.stringify({ t: "peer", event: "leave", role: roleOf(ws) }));
    try { ws.close(code || 1000, reason || ""); } catch (e) {}
  }

  async webSocketError(ws) {
    this.broadcast(ws, JSON.stringify({ t: "peer", event: "error" }));
  }
}

export default {
  async fetch() {
    return new Response("relay worker: no public routes", { status: 404 });
  },
};
