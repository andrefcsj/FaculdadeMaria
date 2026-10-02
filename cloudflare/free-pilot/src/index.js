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
  const [operations, config, closed, cash, notes, darfs, profile, equities, quotes] =
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
      env.DB.prepare(
        "SELECT option_code, price, quoted_at, updated_at FROM manual_option_quotes ORDER BY option_code",
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
    manual_option_quotes: quotes.results,
  };
}

async function backupData(env) {
  const [dashboard, preferences, quotes, marketQuotes, closureMetadata] =
    await Promise.all([
      dashboardData(env),
      env.DB.prepare(
        "SELECT operation_id, exercise_interest, underlying_asset, updated_at FROM operation_preferences ORDER BY operation_id",
      ).all(),
      env.DB.prepare(
        "SELECT option_code, price, quoted_at, updated_at FROM manual_option_quotes ORDER BY option_code",
      ).all(),
      env.DB.prepare(
        "SELECT quote_kind, symbol, price, source, quoted_at FROM api_market_quotes ORDER BY quote_kind, symbol",
      ).all(),
      env.DB.prepare(
        "SELECT operation_id, payload, updated_at FROM operation_closure_metadata ORDER BY operation_id",
      ).all(),
    ]);
  return {
    format: "faculdademaria-cloudflare-backup",
    version: 1,
    exported_at: new Date().toISOString(),
    data: {
      ...dashboard,
      operation_preferences: preferences.results,
      manual_option_quotes: quotes.results,
      api_market_quotes: marketQuotes.results,
      operation_closure_metadata: closureMetadata.results.map((row) => ({
        ...JSON.parse(row.payload),
        operation_id: row.operation_id,
        updated_at: row.updated_at,
      })),
    },
  };
}

async function restoreBackup(env, backup) {
  if (
    backup?.format !== "faculdademaria-cloudflare-backup" ||
    backup?.version !== 1 ||
    !backup?.data ||
    typeof backup.data !== "object"
  )
    throw new Error("Arquivo de backup inválido.");
  const data = backup.data,
    list = (name) => (Array.isArray(data[name]) ? data[name] : []);
  const total = [
    "operations",
    "config",
    "closed",
    "cash",
    "notes",
    "darfs",
    "equities",
    "operation_preferences",
    "manual_option_quotes",
    "api_market_quotes",
    "operation_closure_metadata",
  ].reduce((sum, name) => sum + list(name).length, 0);
  if (total > 5000)
    throw new Error("O backup excede o limite seguro de 5.000 registros.");
  const statements = [
    "operacoes",
    "config",
    "closed_operations",
    "cash_ledger",
    "brokerage_notes",
    "paid_darfs",
    "equity_lots",
    "operation_preferences",
    "manual_option_quotes",
    "api_market_quotes",
    "operation_closure_metadata",
    "taxpayer_profile",
  ].map((table) => env.DB.prepare(`DELETE FROM ${table}`));
  for (const row of list("operations"))
    statements.push(
      env.DB.prepare(
        "INSERT INTO operacoes (id, data_abertura, ativo, tipo, estrategia, status, contratos, strike, premio_opcao, custos, irrf, vencimento, cotacao_atual, resultado_realizado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
      ).bind(
        row.id,
        row.data_abertura,
        row.ativo,
        row.tipo,
        row.estrategia,
        row.status,
        row.contratos,
        row.strike,
        row.premio_opcao,
        row.custos,
        row.irrf,
        row.vencimento,
        row.cotacao_atual,
        row.resultado_realizado,
      ),
    );
  for (const row of list("config"))
    statements.push(
      env.DB.prepare(
        "INSERT INTO config (parametro, valor) VALUES (?, ?)",
      ).bind(row.parametro, row.valor),
    );
  for (const row of list("closed")) {
    const { closed_id, closed_at, ...payload } = row;
    statements.push(
      env.DB.prepare(
        "INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES (?, ?, ?)",
      ).bind(
        closed_id || recordId(),
        JSON.stringify(payload),
        closed_at || payload["Data fechamento"] || "",
      ),
    );
  }
  for (const row of list("cash")) {
    const { id, date, ...payload } = row;
    statements.push(
      env.DB.prepare(
        "INSERT INTO cash_ledger (event_id, payload, event_date) VALUES (?, ?, ?)",
      ).bind(
        id || recordId(),
        JSON.stringify(payload),
        date || payload.date || "",
      ),
    );
  }
  for (const row of list("notes")) {
    const { key, ...payload } = row;
    statements.push(
      env.DB.prepare(
        "INSERT INTO brokerage_notes (note_key, payload) VALUES (?, ?)",
      ).bind(key || recordId(), JSON.stringify(payload)),
    );
  }
  for (const row of list("darfs")) {
    const { id, ...payload } = row;
    statements.push(
      env.DB.prepare(
        "INSERT INTO paid_darfs (darf_id, payload, competence, payment_date) VALUES (?, ?, ?, ?)",
      ).bind(
        id || recordId(),
        JSON.stringify(payload),
        payload.competence || "",
        payload.payment_date || "",
      ),
    );
  }
  for (const row of list("equities")) {
    const { lot_id, ...payload } = row;
    statements.push(
      env.DB.prepare(
        "INSERT INTO equity_lots (lot_id, payload) VALUES (?, ?)",
      ).bind(lot_id || "manual:" + recordId(), JSON.stringify(payload)),
    );
  }
  for (const row of list("operation_preferences"))
    statements.push(
      env.DB.prepare(
        "INSERT INTO operation_preferences (operation_id, exercise_interest, underlying_asset, updated_at) VALUES (?, ?, ?, ?)",
      ).bind(
        row.operation_id,
        row.exercise_interest,
        row.underlying_asset,
        row.updated_at,
      ),
    );
  for (const row of list("manual_option_quotes"))
    statements.push(
      env.DB.prepare(
        "INSERT INTO manual_option_quotes (option_code, price, quoted_at, updated_at) VALUES (?, ?, ?, ?)",
      ).bind(row.option_code, row.price, row.quoted_at, row.updated_at),
    );
  for (const row of list("api_market_quotes"))
    statements.push(
      env.DB.prepare(
        "INSERT INTO api_market_quotes (quote_kind, symbol, price, source, quoted_at) VALUES (?, ?, ?, ?, ?)",
      ).bind(row.quote_kind, row.symbol, row.price, row.source, row.quoted_at),
    );
  for (const row of list("operation_closure_metadata")) {
    const { operation_id, updated_at, ...payload } = row;
    statements.push(
      env.DB.prepare(
        "INSERT INTO operation_closure_metadata (operation_id, payload, updated_at) VALUES (?, ?, ?)",
      ).bind(operation_id, JSON.stringify(payload), updated_at),
    );
  }
  if (data.taxpayer && Object.keys(data.taxpayer).length)
    statements.push(
      env.DB.prepare(
        "INSERT INTO taxpayer_profile (profile_id, payload) VALUES (1, ?)",
      ).bind(JSON.stringify(data.taxpayer)),
    );
  for (let index = 0; index < statements.length; index += 100)
    await env.DB.batch(statements.slice(index, index + 100));
  return total;
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
  if (path === "/api/notes" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const key = String(body.key || "").trim().slice(0, 160);
    const payload = body.payload;
    if (!key || !payload || typeof payload !== "object")
      return json({ error: "Lançamento de nota inválido." }, 400);
    const result = await env.DB.prepare(
      "INSERT INTO brokerage_notes (note_key, payload, imported_at) VALUES (?, ?, ?) ON CONFLICT(note_key) DO NOTHING",
    )
      .bind(key, JSON.stringify(payload), new Date().toISOString())
      .run();
    return json({ ok: true, imported: result.meta.changes > 0 }, 201);
  }
  if (path === "/api/quotes" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const optionCode = String(body.option_code || "").trim().toUpperCase();
    const price = money(body.price);
    if (!/^[A-Z0-9]{4,16}$/.test(optionCode) || price < 0)
      return json({ error: "Informe código e cotação válidos." }, 400);
    const quotedAt = String(body.quoted_at || new Date().toISOString().slice(0, 16));
    await env.DB.prepare(
      "INSERT INTO manual_option_quotes (option_code, price, quoted_at, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(option_code) DO UPDATE SET price = excluded.price, quoted_at = excluded.quoted_at, updated_at = excluded.updated_at",
    )
      .bind(optionCode, price, quotedAt, new Date().toISOString())
      .run();
    return json({ ok: true }, 201);
  }
  const quoteMatch = path.match(/^\/api\/quotes\/([A-Z0-9]{4,16})$/);
  if (quoteMatch && request.method === "DELETE") {
    const result = await env.DB.prepare(
      "DELETE FROM manual_option_quotes WHERE option_code = ?",
    )
      .bind(quoteMatch[1])
      .run();
    return result.meta.changes
      ? new Response(null, { status: 204 })
      : json({ error: "not found" }, 404);
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
    return new Response(JSON.stringify(await backupData(env)), {
      headers: {
        "content-type": "application/json; charset=utf-8",
        "content-disposition":
          "attachment; filename=faculdademaria-backup.json",
      },
    });
  }
  if (path === "/api/restore" && request.method === "POST") {
    try {
      return json({
        ok: true,
        restored: await restoreBackup(env, await request.json()),
      });
    } catch (error) {
      return json(
        { error: error.message || "Não foi possível restaurar o backup." },
        400,
      );
    }
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
