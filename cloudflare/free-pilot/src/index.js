const BASE = "/faculdademaria";
const encoder = new TextEncoder();

function json(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}

function unauthorized() {
  return json({ error: "unauthorized" }, 401);
}

function base64Url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlDecode(value) {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (value.length % 4)) % 4);
  return Uint8Array.from(atob(padded), (char) => char.charCodeAt(0));
}

async function signingKey(secret) {
  return crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
}

async function sessionCookie(env) {
  const payload = base64Url(encoder.encode(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 60 * 60 * 12 })));
  const signature = base64Url(new Uint8Array(await crypto.subtle.sign("HMAC", await signingKey(env.SESSION_SECRET), encoder.encode(payload))));
  return `${payload}.${signature}`;
}

async function isAuthenticated(request, env) {
  const token = request.headers.get("Cookie")?.match(/(?:^|;\s*)fm_session=([^;]+)/)?.[1];
  if (!token || !env.SESSION_SECRET) return false;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return false;
  const valid = await crypto.subtle.verify("HMAC", await signingKey(env.SESSION_SECRET), base64UrlDecode(signature), encoder.encode(payload));
  if (!valid) return false;
  try {
    return JSON.parse(new TextDecoder().decode(base64UrlDecode(payload))).exp > Math.floor(Date.now() / 1000);
  } catch {
    return false;
  }
}

function operationPayload(row) {
  return {
    data_abertura: String(row.data_abertura ?? ""), ativo: String(row.ativo ?? "").toUpperCase(),
    tipo: String(row.tipo ?? "PUT").toUpperCase(), estrategia: String(row.estrategia ?? "Venda"),
    status: String(row.status ?? "Aberta"), contratos: String(row.contratos ?? "1"),
    strike: String(row.strike ?? "0"), premio_opcao: String(row.premio_opcao ?? "0"),
    custos: String(row.custos ?? "0"), irrf: String(row.irrf ?? "0"),
    vencimento: String(row.vencimento ?? ""), cotacao_atual: String(row.cotacao_atual ?? "0"),
    resultado_realizado: String(row.resultado_realizado ?? "0"),
  };
}

async function api(request, env, path) {
  if (path === "/api/session" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    if (!env.ADMIN_PIN || String(body.pin ?? "") !== env.ADMIN_PIN) return unauthorized();
    const token = await sessionCookie(env);
    return json({ ok: true }, 200, { "set-cookie": `fm_session=${token}; HttpOnly; Secure; SameSite=Strict; Path=${BASE}; Max-Age=43200` });
  }
  if (path === "/api/session" && request.method === "DELETE") {
    return json({ ok: true }, 200, { "set-cookie": `fm_session=; HttpOnly; Secure; SameSite=Strict; Path=${BASE}; Max-Age=0` });
  }
  if (!await isAuthenticated(request, env)) return unauthorized();

  if (path === "/api/dashboard" && request.method === "GET") {
    const [operations, config, closed] = await Promise.all([
      env.DB.prepare("SELECT id, data_abertura, ativo, tipo, estrategia, status, contratos, strike, premio_opcao, custos, irrf, vencimento, cotacao_atual, resultado_realizado FROM operacoes ORDER BY id").all(),
      env.DB.prepare("SELECT parametro, valor FROM config ORDER BY parametro").all(),
      env.DB.prepare("SELECT closed_id, payload, closed_at FROM closed_operations ORDER BY closed_at DESC").all(),
    ]);
    return json({ operations: operations.results, config: config.results, closed: closed.results.map((row) => ({ ...JSON.parse(row.payload), closed_id: row.closed_id, closed_at: row.closed_at })) });
  }
  if (path === "/api/operations" && request.method === "POST") {
    const item = operationPayload(await request.json().catch(() => ({})));
    if (!item.ativo || !item.data_abertura) return json({ error: "ativo e data_abertura são obrigatórios" }, 400);
    const fields = Object.keys(item);
    const result = await env.DB.prepare(`INSERT INTO operacoes (${fields.join(", ")}) VALUES (${fields.map(() => "?").join(", ")})`).bind(...fields.map((field) => item[field])).run();
    return json({ id: result.meta.last_row_id }, 201);
  }
  const match = path.match(/^\/api\/operations\/(\d+)$/);
  if (match && request.method === "DELETE") {
    const result = await env.DB.prepare("DELETE FROM operacoes WHERE id = ?").bind(Number(match[1])).run();
    return result.meta.changes ? new Response(null, { status: 204 }) : json({ error: "not found" }, 404);
  }
  if (path === "/api/backup" && request.method === "GET") {
    const data = await api(new Request(request.url, { headers: request.headers }), env, "/api/dashboard");
    return new Response(data.body, { headers: { "content-type": "application/json; charset=utf-8", "content-disposition": "attachment; filename=faculdademaria-backup.json" } });
  }
  return json({ error: "not found" }, 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === BASE) return Response.redirect(`${url.origin}${BASE}/`, 302);
    if (!url.pathname.startsWith(`${BASE}/`)) return new Response("Not found", { status: 404 });
    const path = url.pathname.slice(BASE.length);
    if (path.startsWith("/api/")) return api(request, env, path);
    const assetUrl = new URL(request.url);
    assetUrl.pathname = path === "/" ? "/free-pilot/index.html" : path;
    return env.ASSETS.fetch(assetUrl);
  },
};
