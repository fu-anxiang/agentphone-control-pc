// Pages Function: 全部路由交给 Durable Object (pcrelay-do)
//  /ws?role=phone|pc&room=xxx   -> WebSocket 中继（手机网页看画面/触屏）
//  /api?room=xxx  POST {m,p}    -> HTTP 隧道，转发给电脑端 agent_bridge 执行

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  if (url.pathname === "/ws" || url.pathname === "/api") {
    const room = url.searchParams.get("room") || request.headers.get("X-Room") || "default";
    const id = env.RELAY.idFromName(room);
    return env.RELAY.get(id).fetch(request);
  }

  if (url.pathname === "/health") {
    return new Response(JSON.stringify({ ok: true, relay: "pcrelay" }), {
      headers: { "content-type": "application/json" },
    });
  }

  return context.next();
}
