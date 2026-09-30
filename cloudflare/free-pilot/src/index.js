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
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function base64UrlDecode(value) {
  const padded =
    value.replace(/-/g, "+").replace(/_/g, "/") +
    "=".repeat((4 - (value.length % 4)) % 4);
  return Uint8Array.from(atob(padded), (char) => char.charCodeAt(0));
}

async function signingKey(secret) {
  return crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"],
  );
}

async function sessionCookie(env) {
  const payload = base64Url(
    encoder.encode(
      JSON.stringify({ exp: Math.floor(Date.now() / 1000) + 60 * 60 * 12 }),
    ),
  );
  const signature = base64Url(
    new Uint8Array(
      await crypto.subtle.sign(
        "HMAC",
        await signingKey(env.SESSION_SECRET),
        encoder.encode(payload),
      ),
    ),
  );
  return `${payload}.${signature}`;
}

async function isAuthenticated(request, env) {
  const token =
    request.headers.get("Authorization")?.replace(/^Bearer\s+/i, "") ||
    request.headers.get("Cookie")?.match(/(?:^|;\s*)fm_session=([^;]+)/)?.[1];
  if (!token || !env.SESSION_SECRET) return false;
  const [payload, signature] = token.split(".");
  if (!payload || !signature) return false;
  const valid = await crypto.subtle.verify(
    "HMAC",
    await signingKey(env.SESSION_SECRET),
    base64UrlDecode(signature),
    encoder.encode(payload),
  );
  if (!valid) return false;
  try {
    return (
      JSON.parse(new TextDecoder().decode(base64UrlDecode(payload))).exp >
      Math.floor(Date.now() / 1000)
    );
  } catch {
    return false;
  }
}

function operationPayload(row) {
  return {
    data_abertura: String(row.data_abertura ?? ""),
    ativo: String(row.ativo ?? "").toUpperCase(),
    tipo: String(row.tipo ?? "PUT").toUpperCase(),
    estrategia: String(row.estrategia ?? "Venda"),
    status: String(row.status ?? "Aberta"),
    contratos: String(row.contratos ?? "1"),
    strike: String(row.strike ?? "0"),
    premio_opcao: String(row.premio_opcao ?? "0"),
    custos: String(row.custos ?? "0"),
    irrf: String(row.irrf ?? "0"),
    vencimento: String(row.vencimento ?? ""),
    cotacao_atual: String(row.cotacao_atual ?? "0"),
    resultado_realizado: String(row.resultado_realizado ?? "0"),
  };
}

function money(value) {
  const normalized = String(value ?? "0")
    .replace(/R\$|\s/g, "")
    .replace(/\.(?=\d{3}(?:\D|$))/g, "")
    .replace(",", ".");
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : 0;
}

function recordId() {
  return crypto.randomUUID().replace(/-/g, "");
}

async function dashboardData(env) {
  const [operations, config, closed, cash, notes, darfs, profile, equities] =
    await Promise.all([
      env.DB.prepare(
        "SELECT id, data_abertura, ativo, tipo, estrategia, status, contratos, strike, premio_opcao, custos, irrf, vencimento, cotacao_atual, resultado_realizado FROM operacoes ORDER BY id",
      ).all(),
      env.DB.prepare(
        "SELECT parametro, valor FROM config ORDER BY parametro",
      ).all(),
      env.DB.prepare(
        "SELECT closed_id, payload, closed_at FROM closed_operations ORDER BY closed_at DESC",
      ).all(),
      env.DB.prepare(
        "SELECT event_id, payload, event_date, created_at FROM cash_ledger ORDER BY event_date DESC, created_at DESC",
      ).all(),
      env.DB.prepare(
        "SELECT note_key, payload, imported_at FROM brokerage_notes ORDER BY imported_at DESC",
      ).all(),
      env.DB.prepare(
        "SELECT darf_id, payload, competence, payment_date FROM paid_darfs ORDER BY payment_date DESC",
      ).all(),
      env.DB.prepare(
        "SELECT payload FROM taxpayer_profile WHERE profile_id = 1",
      ).first(),
      env.DB.prepare(
        "SELECT lot_id, payload, created_at FROM equity_lots ORDER BY created_at",
      ).all(),
    ]);
  return {
    operations: operations.results,
    config: config.results,
    closed: closed.results.map((row) => ({
      ...JSON.parse(row.payload),
      closed_id: row.closed_id,
      closed_at: row.closed_at,
    })),
    cash: cash.results.map((row) => ({
      ...JSON.parse(row.payload),
      id: row.event_id,
      date: row.event_date,
    })),
    notes: notes.results.map((row) => ({
      ...JSON.parse(row.payload),
      key: row.note_key,
    })),
    darfs: darfs.results.map((row) => ({
      ...JSON.parse(row.payload),
      id: row.darf_id,
    })),
    taxpayer: profile ? JSON.parse(profile.payload) : {},
    equities: equities.results.map((row) => ({
      ...JSON.parse(row.payload),
      lot_id: row.lot_id,
    })),
  };
}

async function api(request, env, path) {
  if (path === "/api/session" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    if (!env.ADMIN_PIN || String(body.pin ?? "") !== env.ADMIN_PIN)
      return unauthorized();
    const token = await sessionCookie(env);
    return json({ ok: true, token }, 200, {
      "set-cookie": `fm_session=${token}; HttpOnly; Secure; SameSite=Strict; Path=${BASE}; Max-Age=43200`,
    });
  }
  if (path === "/api/session" && request.method === "DELETE") {
    return json({ ok: true }, 200, {
      "set-cookie": `fm_session=; HttpOnly; Secure; SameSite=Strict; Path=${BASE}; Max-Age=0`,
    });
  }
  if (!(await isAuthenticated(request, env))) return unauthorized();

  if (path === "/api/dashboard" && request.method === "GET") {
    return json(await dashboardData(env));
  }
  if (path === "/api/operations" && request.method === "POST") {
    const item = operationPayload(await request.json().catch(() => ({})));
    if (!item.ativo || !item.data_abertura)
      return json({ error: "ativo e data_abertura são obrigatórios" }, 400);
    const fields = Object.keys(item);
    const result = await env.DB.prepare(
      `INSERT INTO operacoes (${fields.join(", ")}) VALUES (${fields.map(() => "?").join(", ")})`,
    )
      .bind(...fields.map((field) => item[field]))
      .run();
    return json({ id: result.meta.last_row_id }, 201);
  }
  const match = path.match(/^\/api\/operations\/(\d+)$/);
  if (match && request.method === "DELETE") {
    const result = await env.DB.prepare("DELETE FROM operacoes WHERE id = ?")
      .bind(Number(match[1]))
      .run();
    return result.meta.changes
      ? new Response(null, { status: 204 })
      : json({ error: "not found" }, 404);
  }
  if (match && request.method === "PUT") {
    const item = operationPayload(await request.json().catch(() => ({})));
    if (!item.ativo || !item.data_abertura)
      return json({ error: "ativo e data_abertura são obrigatórios" }, 400);
    const fields = Object.keys(item);
    const result = await env.DB.prepare(
      `UPDATE operacoes SET ${fields.map((field) => `${field} = ?`).join(", ")} WHERE id = ?`,
    )
      .bind(...fields.map((field) => item[field]), Number(match[1]))
      .run();
    return result.meta.changes
      ? json({ ok: true })
      : json({ error: "not found" }, 404);
  }
  const closeMatch = path.match(/^\/api\/operations\/(\d+)\/close$/);
  if (closeMatch && request.method === "POST") {
    const operation = await env.DB.prepare(
      "SELECT id, data_abertura, ativo, tipo, estrategia, status, contratos, strike, premio_opcao, custos, irrf, vencimento, cotacao_atual, resultado_realizado FROM operacoes WHERE id = ?",
    )
      .bind(Number(closeMatch[1]))
      .first();
    if (!operation) return json({ error: "not found" }, 404);
    const body = await request.json().catch(() => ({}));
    const result = money(body.resultado_final);
    const closedAt = String(
      body.data_fechamento || new Date().toISOString().slice(0, 10),
    );
    const payload = {
      ...operation,
      "Data fechamento": closedAt,
      Resultado_final: result,
      Lucro_tributavel: result,
      Observacoes: String(body.observacoes || "").slice(0, 300),
    };
    await env.DB.batch([
      env.DB.prepare(
        "INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES (?, ?, ?)",
      ).bind(recordId(), JSON.stringify(payload), closedAt),
      env.DB.prepare("DELETE FROM operacoes WHERE id = ?").bind(
        Number(closeMatch[1]),
      ),
    ]);
    return json({ ok: true });
  }
  const reopenMatch = path.match(/^\/api\/closed\/(.+)\/reopen$/);
  if (reopenMatch && request.method === "POST") {
    const closed = await env.DB.prepare(
      "SELECT payload FROM closed_operations WHERE closed_id = ?",
    )
      .bind(reopenMatch[1])
      .first();
    if (!closed) return json({ error: "not found" }, 404);
    const item = operationPayload(JSON.parse(closed.payload));
    const fields = Object.keys(item);
    await env.DB.batch([
      env.DB.prepare(
        `INSERT INTO operacoes (${fields.join(", ")}) VALUES (${fields.map(() => "?").join(", ")})`,
      ).bind(...fields.map((field) => item[field])),
      env.DB.prepare("DELETE FROM closed_operations WHERE closed_id = ?").bind(
        reopenMatch[1],
      ),
    ]);
    return json({ ok: true });
  }
  if (path === "/api/cash" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const kind = String(body.kind || "aporte");
    const amount = money(body.amount);
    if (
      !new Set(["aporte", "retirada", "ajuste_credito", "ajuste_debito"]).has(
        kind,
      ) ||
      amount <= 0
    )
      return json(
        { error: "Informe uma movimentação e um valor maior que zero." },
        400,
      );
    const record = {
      kind,
      amount: String(amount),
      date: String(body.date || new Date().toISOString().slice(0, 10)),
      description: String(body.description || "")
        .trim()
        .slice(0, 180),
      created_at: new Date().toISOString(),
    };
    const id = recordId();
    await env.DB.prepare(
      "INSERT INTO cash_ledger (event_id, payload, event_date) VALUES (?, ?, ?)",
    )
      .bind(id, JSON.stringify(record), record.date)
      .run();
    return json({ ok: true, id }, 201);
  }
  const cashMatch = path.match(/^\/api\/cash\/(.+)$/);
  if (cashMatch && request.method === "DELETE") {
    const result = await env.DB.prepare(
      "DELETE FROM cash_ledger WHERE event_id = ?",
    )
      .bind(cashMatch[1])
      .run();
    return result.meta.changes
      ? new Response(null, { status: 204 })
      : json({ error: "not found" }, 404);
  }
  if (path === "/api/config" && request.method === "PUT") {
    const body = await request.json().catch(() => ({}));
    const values = Array.isArray(body.values) ? body.values : [];
    if (
      !values.length ||
      values.some((row) => !String(row.parametro || "").trim())
    )
      return json({ error: "Configuração inválida." }, 400);
    await env.DB.batch(
      values.map((row) =>
        env.DB.prepare(
          "INSERT INTO config (parametro, valor) VALUES (?, ?) ON CONFLICT(parametro) DO UPDATE SET valor = excluded.valor",
        ).bind(
          String(row.parametro).trim().slice(0, 120),
          String(row.valor ?? "")
            .trim()
            .slice(0, 120),
        ),
      ),
    );
    return json({ ok: true });
  }
  if (path === "/api/darfs" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const amount = money(body.amount);
    const competence = String(body.competence || "");
    if (!/^\d{4}-\d{2}$/.test(competence) || amount <= 0)
      return json({ error: "Informe competência e valor válidos." }, 400);
    const record = {
      competence,
      payment_date: String(
        body.payment_date || new Date().toISOString().slice(0, 10),
      ),
      due_date: String(body.due_date || ""),
      revenue_code: "6015",
      amount: String(amount),
      description: String(body.description || "")
        .trim()
        .slice(0, 180),
    };
    const id = recordId();
    await env.DB.prepare(
      "INSERT INTO paid_darfs (darf_id, payload, competence, payment_date) VALUES (?, ?, ?, ?)",
    )
      .bind(id, JSON.stringify(record), record.competence, record.payment_date)
      .run();
    return json({ ok: true, id }, 201);
  }
  if (path === "/api/equities" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const asset = String(body.asset || "")
      .trim()
      .toUpperCase();
    const quantity = Math.floor(money(body.quantity));
    const average = money(body.average_price);
    if (!/^[A-Z0-9]{4,12}$/.test(asset) || quantity <= 0 || average <= 0)
      return json(
        { error: "Informe ativo, quantidade e preço médio válidos." },
        400,
      );
    const record = {
      asset,
      quantity,
      available_quantity: quantity,
      acquisition_date: String(
        body.acquisition_date || new Date().toISOString().slice(0, 10),
      ),
      exercise_price: String(average),
      exercise_total: String(average * quantity),
      exercise_costs: "0",
      cash_cost_total: String(average * quantity),
      option_premium_gross: "0",
      option_opening_costs: "0",
      tax_cost_total: String(average * quantity),
      tax_cost_per_share: String(average),
      source: "Inclusão manual",
      created_at: new Date().toISOString(),
    };
    const id = "manual:" + recordId();
    await env.DB.prepare(
      "INSERT INTO equity_lots (lot_id, payload) VALUES (?, ?)",
    )
      .bind(id, JSON.stringify(record))
      .run();
    return json({ ok: true, id }, 201);
  }
  const equityMatch = path.match(/^\/api\/equities\/([A-Z0-9]+)$/);
  if (equityMatch && request.method === "PUT") {
    const body = await request.json().catch(() => ({}));
    const quantity = Math.floor(money(body.quantity));
    const average = money(body.average_price);
    if (quantity <= 0 || average <= 0)
      return json(
        { error: "Quantidade e preço médio devem ser maiores que zero." },
        400,
      );
    const current = await env.DB.prepare(
      "SELECT lot_id FROM equity_lots WHERE json_extract(payload, '$.asset') = ?",
    )
      .bind(equityMatch[1])
      .all();
    if (!current.results.length)
      return json({ error: "Ação não encontrada." }, 404);
    const record = {
      asset: equityMatch[1],
      quantity,
      available_quantity: quantity,
      acquisition_date: String(
        body.acquisition_date || new Date().toISOString().slice(0, 10),
      ),
      exercise_price: String(average),
      exercise_total: String(average * quantity),
      exercise_costs: "0",
      cash_cost_total: String(average * quantity),
      option_premium_gross: "0",
      option_opening_costs: "0",
      tax_cost_total: String(average * quantity),
      tax_cost_per_share: String(average),
      source: "Posição consolidada por edição manual",
      updated_at: new Date().toISOString(),
    };
    await env.DB.batch([
      env.DB.prepare(
        "DELETE FROM equity_lots WHERE json_extract(payload, '$.asset') = ?",
      ).bind(equityMatch[1]),
      env.DB.prepare(
        "INSERT INTO equity_lots (lot_id, payload) VALUES (?, ?)",
      ).bind("manual:" + recordId(), JSON.stringify(record)),
    ]);
    return json({ ok: true });
  }
  if (equityMatch && request.method === "DELETE") {
    const result = await env.DB.prepare(
      "DELETE FROM equity_lots WHERE json_extract(payload, '$.asset') = ?",
    )
      .bind(equityMatch[1])
      .run();
    return result.meta.changes
      ? new Response(null, { status: 204 })
      : json({ error: "not found" }, 404);
  }
  const equitySellMatch = path.match(/^\/api\/equities\/([A-Z0-9]+)\/sell$/);
  if (equitySellMatch && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const quantity = Math.floor(money(body.quantity)),
      price = money(body.sale_price);
    const lots = await env.DB.prepare(
      "SELECT lot_id, payload FROM equity_lots WHERE json_extract(payload, '$.asset') = ? ORDER BY created_at",
    )
      .bind(equitySellMatch[1])
      .all();
    let remaining = quantity;
    if (
      quantity <= 0 ||
      price <= 0 ||
      lots.results.reduce(
        (sum, row) =>
          sum +
          Number(
            JSON.parse(row.payload).available_quantity ??
              JSON.parse(row.payload).quantity ??
              0,
          ),
        0,
      ) < quantity
    )
      return json({ error: "Quantidade indisponível para venda." }, 400);
    const statements = [];
    for (const row of lots.results) {
      if (!remaining) break;
      const record = JSON.parse(row.payload),
        available = Number(record.available_quantity ?? record.quantity ?? 0),
        take = Math.min(available, remaining);
      const oldQuantity = Number(record.quantity ?? available);
      record.quantity = Math.max(0, oldQuantity - take);
      record.available_quantity = available - take;
      record.cash_cost_total = String(
        money(record.cash_cost_total) *
          (record.quantity / Math.max(1, oldQuantity)),
      );
      record.tax_cost_total = String(
        money(record.tax_cost_total) *
          (record.quantity / Math.max(1, oldQuantity)),
      );
      statements.push(
        record.quantity
          ? env.DB.prepare(
              "UPDATE equity_lots SET payload = ? WHERE lot_id = ?",
            ).bind(JSON.stringify(record), row.lot_id)
          : env.DB.prepare("DELETE FROM equity_lots WHERE lot_id = ?").bind(
              row.lot_id,
            ),
      );
      remaining -= take;
    }
    const cash = {
      kind: "venda_acoes",
      amount: String(price * quantity),
      date: String(body.sale_date || new Date().toISOString().slice(0, 10)),
      description: "Venda de " + quantity + " ações " + equitySellMatch[1],
      created_at: new Date().toISOString(),
    };
    statements.push(
      env.DB.prepare(
        "INSERT INTO cash_ledger (event_id, payload, event_date) VALUES (?, ?, ?)",
      ).bind(recordId(), JSON.stringify(cash), cash.date),
    );
    await env.DB.batch(statements);
    return json({ ok: true });
  }
  const darfMatch = path.match(/^\/api\/darfs\/(.+)$/);
  if (darfMatch && request.method === "DELETE") {
    const result = await env.DB.prepare(
      "DELETE FROM paid_darfs WHERE darf_id = ?",
    )
      .bind(darfMatch[1])
      .run();
    return result.meta.changes
      ? new Response(null, { status: 204 })
      : json({ error: "not found" }, 404);
  }
  if (path === "/api/backup" && request.method === "GET") {
    const data = await api(
      new Request(request.url, { headers: request.headers }),
      env,
      "/api/dashboard",
    );
    return new Response(data.body, {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "content-disposition":
          "attachment; filename=faculdademaria-backup.json",
      },
    });
  }
  return json({ error: "not found" }, 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === BASE)
      return Response.redirect(`${url.origin}${BASE}/`, 302);
    if (!url.pathname.startsWith(`${BASE}/`))
      return new Response("Not found", { status: 404 });
    const path = url.pathname.slice(BASE.length);
    if (path.startsWith("/api/")) return api(request, env, path);
    const assetUrl = new URL(request.url);
    assetUrl.pathname = path === "/" ? "/free-pilot/index.html" : path;
    assetUrl.search = "";
    const response = await env.ASSETS.fetch(assetUrl);
    const headers = new Headers(response.headers);
    headers.set("Cache-Control", "no-store");
    return new Response(response.body, { status: response.status, headers });
  },
};
