import { handleMarket } from "./market.js";
const BASE = "/faculdademaria";
const encoder = new TextEncoder();

function json(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...headers },
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
  let valid;
  try { valid = await crypto.subtle.verify(
    "HMAC",
    await signingKey(env.SESSION_SECRET),
    base64UrlDecode(signature),
    encoder.encode(payload),
  ); } catch { return false; }
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

const B3_UNDERLYING = { BBAS: "BBAS3", BBDC: "BBDC4", CPLE: "CPLE3", GOAU: "GOAU4", ITSA: "ITSA4", ITUB: "ITUB4", PETR: "PETR4", VALE: "VALE3" };
function underlyingForOption(code, preferred = "") {
  const root = String(code || "").toUpperCase().match(/^[A-Z]{4}/)?.[0] || "";
  const saved = String(preferred || "").toUpperCase();
  return saved.startsWith(root) ? saved : (B3_UNDERLYING[root] || saved || root || "");
}

function money(value) {
  const normalized = String(value ?? "0")
    .replace(/R\$|\s/g, "")
    .replace(/\.(?=\d{3}(?:\D|$))/g, "")
    .replace(",", ".");
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : 0;
}

const businessDate = () => new Intl.DateTimeFormat("sv-SE", { timeZone: "America/Sao_Paulo" }).format(new Date());

function recordId() {
  return crypto.randomUUID().replace(/-/g, "");
}

async function dashboardData(env) {
  const [operations, config, closed, cash, notes, darfs, profile, equities, quotes, marketQuotes, preferences] =
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
      env.DB.prepare(
        "SELECT quote_kind, symbol, price, source, quoted_at FROM api_market_quotes ORDER BY quote_kind, symbol",
      ).all(),
      env.DB.prepare(
        "SELECT operation_id, exercise_interest, underlying_asset, updated_at FROM operation_preferences ORDER BY operation_id",
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
      created_at: JSON.parse(row.payload).created_at ?? row.created_at,
      id: row.event_id,
      date: row.event_date,
    })),
    notes: notes.results.map((row) => ({
      ...JSON.parse(row.payload),
      imported_at: JSON.parse(row.payload).imported_at ?? row.imported_at,
      key: row.note_key,
    })),
    darfs: darfs.results.map((row) => ({
      ...JSON.parse(row.payload),
      id: row.darf_id,
    })),
    taxpayer: profile ? JSON.parse(profile.payload) : {},
    equities: equities.results.map((row) => ({
      ...JSON.parse(row.payload),
      created_at: JSON.parse(row.payload).created_at ?? row.created_at,
      lot_id: row.lot_id,
    })),
    manual_option_quotes: quotes.results,
    api_market_quotes: marketQuotes.results,
    operation_preferences: preferences.results,
  };
}

async function backupData(env) {
  const [dashboard, preferences, quotes, marketQuotes, closureMetadata, snapshots] =
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
      env.DB.prepare("SELECT snapshot_kind, symbol, payload, updated_at FROM market_snapshots ORDER BY snapshot_kind, symbol").all(),
    ]);
  return {
    format: "faculdademaria-cloudflare-backup",
    version: 1,
    exported_at: new Date().toISOString(),
    data: {
      ...dashboard,
      market_snapshots: snapshots.results,
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
  if (backup?.format !== "faculdademaria-cloudflare-backup" || backup?.version !== 1 || !backup.data || typeof backup.data !== "object")
    throw new Error("Arquivo de backup inválido.");
  const data = backup.data;
  const tables = [
    ["operations", "operacoes", ["id", "data_abertura", "ativo", "tipo", "estrategia", "status", "contratos", "strike", "premio_opcao", "custos", "irrf", "vencimento", "cotacao_atual", "resultado_realizado"]],
    ["config", "config", ["parametro", "valor"]],
    ["closed", "closed_operations", ["closed_id", "payload", "closed_at"]],
    ["cash", "cash_ledger", ["event_id", "payload", "event_date", "created_at"]],
    ["notes", "brokerage_notes", ["note_key", "payload", "imported_at"]],
    ["darfs", "paid_darfs", ["darf_id", "payload", "competence", "payment_date"]],
    ["equities", "equity_lots", ["lot_id", "payload", "created_at"]],
    ["operation_preferences", "operation_preferences", ["operation_id", "exercise_interest", "underlying_asset", "updated_at"]],
    ["manual_option_quotes", "manual_option_quotes", ["option_code", "price", "quoted_at", "updated_at"]],
    ["api_market_quotes", "api_market_quotes", ["quote_kind", "symbol", "price", "source", "quoted_at"]],
    ["operation_closure_metadata", "operation_closure_metadata", ["operation_id", "payload", "updated_at"]],
  ];
  if (Array.isArray(data.market_snapshots)) tables.push(["market_snapshots", "market_snapshots", ["snapshot_kind", "symbol", "payload", "updated_at"]]);
  const timestamp = new Date().toISOString();
  let total = 0;
  const prepared = [];
  for (const [name, table, columns] of tables) {
    if (!Array.isArray(data[name])) throw new Error(`O backup não contém a coleção ${name}.`);
    const seen = new Set();
    const rows = data[name].map((original) => {
      if (!original || typeof original !== "object" || Array.isArray(original)) throw new Error(`Registro inválido em ${name}.`);
      const row = { ...original };
      if (name === "closed") { row.closed_id ||= recordId(); row.closed_at ||= row["Data fechamento"] || ""; row.payload = JSON.stringify(original); }
      if (name === "cash") { row.event_id = row.id || row.event_id; row.event_date = row.date || row.event_date || ""; row.created_at ||= timestamp; row.payload = JSON.stringify(original); }
      if (name === "notes") { row.note_key = row.key || row.note_key; row.imported_at ||= timestamp; row.payload = JSON.stringify(original); }
      if (name === "darfs") { row.darf_id = row.id || row.darf_id; row.payload = JSON.stringify(original); }
      if (name === "equities") { row.created_at ||= timestamp; row.payload = JSON.stringify(original); }
      if (name === "operation_closure_metadata") row.payload = JSON.stringify(original);
      const identifier = name === "api_market_quotes" ? `${row.quote_kind}:${row.symbol}` : name === "market_snapshots" ? `${row.snapshot_kind}:${row.symbol}` : row[columns[0]];
      if (identifier === undefined || identifier === null || identifier === "" || seen.has(String(identifier)))
        throw new Error(`Identificador ausente ou duplicado em ${name}.`);
      seen.add(String(identifier));
      if (name === "operations" && (!row.ativo || !row.data_abertura)) throw new Error("Operação incompleta no backup.");
      return row;
    });
    total += rows.length;
    // One JSON insert per table keeps the entire restore in one D1 transaction,
    // even when a backup contains thousands of cached quotes.
    const expressions = columns.map((column) => `json_extract(value, '$.${column}')`);
    prepared.push(env.DB.prepare(`DELETE FROM ${table}`));
    if (rows.length) prepared.push(env.DB.prepare(`INSERT INTO ${table} (${columns.join(", ")}) SELECT ${expressions.join(", ")} FROM json_each(?)`).bind(JSON.stringify(rows)));
  }
  if (total > 10000) throw new Error("O backup excede o limite de 10.000 registros.");
  if (JSON.stringify(backup).length > 8 * 1024 * 1024) throw new Error("O backup deve ter no máximo 8 MB.");
  if (!data.taxpayer || typeof data.taxpayer !== "object" || Array.isArray(data.taxpayer)) throw new Error("Dados do contribuinte ausentes ou inválidos.");
  prepared.push(env.DB.prepare("DELETE FROM taxpayer_profile"));
  prepared.push(env.DB.prepare("INSERT INTO taxpayer_profile (profile_id, payload) VALUES (1, ?)").bind(JSON.stringify(data.taxpayer)));
  await env.DB.batch(prepared);
  return total;
}

async function exercisePlan(env, operation, body) {
    const quantity = Math.floor(money(body.quantity));
    const exercisePrice = money(body.exercise_price || operation.strike);
    const closeDate = String(body.data_fechamento || businessDate());
    const type = String(operation.tipo).toUpperCase();
    if (!["PUT", "CALL"].includes(type) || /^compra$/i.test(operation.estrategia)) throw new Error("O fluxo automático de exercício atende opções vendidas PUT/CALL.");
    const contractConfig = await env.DB.prepare(
      "SELECT valor FROM config WHERE parametro = ?",
    ).bind("Tamanho contrato opcoes").first();
    const contractSize = Math.max(1, Math.floor(money(contractConfig?.valor) || 100));
    const expectedQuantity = Math.round(money(operation.contratos) * contractSize);
    if (quantity <= 0 || exercisePrice <= 0) throw new Error("Quantidade e preço de exercício são obrigatórios.");
    if (quantity !== expectedQuantity) throw new Error(`A nota informa ${quantity} ações, mas esta posição possui ${expectedQuantity}. Exercício parcial precisa ser conferido antes do encerramento.`);
    const premium = money(operation.premio_opcao) * money(operation.contratos) * contractSize - money(operation.custos) - money(operation.irrf);
    const payload = { ...operation, "Data fechamento": closeDate, Resultado_final: type === "PUT" ? premium : premium, Lucro_tributavel: premium, Observacoes: `Exercício de ${type} registrado pela nota` };
    const statements = [
      env.DB.prepare("INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES (?, ?, ?)").bind(recordId(), JSON.stringify(payload), closeDate),
      env.DB.prepare("DELETE FROM operacoes WHERE id = ?").bind(Number(operation.id)),
    ];
    if (type === "PUT") {
      const asset = underlyingForOption(operation.ativo, body.asset);
      const costs = money(body.costs);
      const total = exercisePrice * quantity + costs;
      const lot = { asset, quantity, available_quantity: quantity, acquisition_date: closeDate, exercise_price: String(exercisePrice), exercise_total: String(exercisePrice * quantity), exercise_costs: String(costs), cash_cost_total: String(total), option_premium_gross: String(premium), option_opening_costs: String(money(operation.custos) + money(operation.irrf)), tax_cost_total: String(total - premium), tax_cost_per_share: String((total - premium) / quantity), source: "Exercício de PUT vendida", source_operation_id: String(operation.id), source_option: operation.ativo, created_at: new Date().toISOString() };
      statements.push(env.DB.prepare("INSERT INTO equity_lots (lot_id, payload) VALUES (?, ?)").bind(`exercise:${operation.id}`, JSON.stringify(lot)));
    } else if (type === "CALL") {
      const asset = underlyingForOption(operation.ativo, body.asset);
      // A entrega da CALL reduz primeiro os lotes mais antigos da ação coberta.
      const lots = await env.DB.prepare("SELECT lot_id, payload FROM equity_lots WHERE json_extract(payload, '$.asset') = ? ORDER BY created_at").bind(asset).all();
      let remaining = quantity, deliveredTaxCost = 0;
      for (const row of lots.results) { if (!remaining) break; const lot = JSON.parse(row.payload); const available = Number(lot.available_quantity ?? lot.quantity ?? 0); const take = Math.min(available, remaining); deliveredTaxCost += money(lot.tax_cost_total ?? lot.cash_cost_total) * take / Math.max(1, Number(lot.quantity ?? available)); lot.available_quantity = available - take; statements.push(env.DB.prepare("UPDATE equity_lots SET payload = ? WHERE lot_id = ?").bind(JSON.stringify(lot), row.lot_id)); remaining -= take; }
      if (remaining) throw new Error("A carteira não possui ações suficientes para o exercício da CALL.");
      payload.exercise_tax_result = Math.round((premium + exercisePrice * quantity - money(body.costs) - deliveredTaxCost) * 100) / 100;
      payload.delivered_tax_cost = deliveredTaxCost;
      payload.exercise_quantity = quantity;
      payload.exercise_price = exercisePrice;
      // The first statement was built before the portfolio calculation.
      statements[0] = env.DB.prepare("INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES (?, ?, ?)").bind(recordId(), JSON.stringify(payload), closeDate);
    }
    return { statements, type };
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

  if (path.startsWith("/api/market/")) {
    try { const response = await handleMarket(request, env, path); if (response) return response; }
    catch (error) { return json({ error: error.message || "Fonte de mercado indisponível." }, 502); }
  }

  if (path === "/api/dashboard" && request.method === "GET") {
    return json(await dashboardData(env));
  }
  if (path === "/api/notes/import" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const key = String(body.key || "").trim().slice(0, 160), note = body.payload, action = body.action;
    if (!key || !note || !action || typeof note !== "object") return json({ error: "Importação incompleta." }, 400);
    const existingNote = await env.DB.prepare("SELECT note_key FROM brokerage_notes WHERE note_key = ?").bind(key).first();
    if (existingNote) return json({ ok: true, duplicate: true, imported: false });
    try {
      const statements = []; let operationId = action.operation_id;
      if (["exercise", "close"].includes(action.kind)) {
        const operation = await env.DB.prepare("SELECT * FROM operacoes WHERE id = ?").bind(Number(operationId)).first();
        if (!operation || operation.ativo !== note.trade?.option_code) throw new Error("A nota não corresponde à posição aberta.");
        if (action.kind === "exercise") {
          const plan = await exercisePlan(env, operation, action.values || {}); statements.push(...plan.statements);
        } else {
          const values = action.values || {}, total = money(operation.contratos), quantity = money(values.contratos_fechados), fraction = quantity / total;
          if (!(quantity > 0) || quantity > total) throw new Error("Quantidade de recompra incompatível com a posição.");
          const closeDate = String(values.data_fechamento || note.trade_date);
          const close = { ...operation, contratos: String(quantity), custos: String(money(operation.custos) * fraction + money(note.operational_costs)), irrf: String(money(operation.irrf) * fraction + money(note.irrf)), opening_costs: money(operation.custos) * fraction, opening_irrf: money(operation.irrf) * fraction, "Data fechamento": closeDate, Resultado_final: money(values.resultado_final), Lucro_tributavel: money(values.resultado_final), Observacoes: String(values.observacoes || "Recompra por nota") };
          statements.push(env.DB.prepare("INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES (?, ?, ?)").bind(recordId(), JSON.stringify(close), closeDate));
          statements.push(quantity === total ? env.DB.prepare("DELETE FROM operacoes WHERE id = ?").bind(Number(operationId)) : env.DB.prepare("UPDATE operacoes SET contratos = ?, custos = ?, irrf = ? WHERE id = ?").bind(total - quantity, money(operation.custos) * (1 - fraction), money(operation.irrf) * (1 - fraction), Number(operationId)));
        }
      } else if (action.kind === "opening") {
        const item = operationPayload(action.values || {});
        if (!item.ativo || item.ativo !== note.trade?.option_code || !(money(item.strike) > 0) || !(money(item.contratos) > 0) || !item.vencimento || !item.data_abertura) throw new Error("Confirme ativo, strike, quantidade e vencimento antes de importar.");
        const existing = await env.DB.prepare("SELECT * FROM operacoes WHERE ativo = ? AND status = 'Aberta' ORDER BY id LIMIT 1").bind(item.ativo).first();
        if (existing) {
          if (existing.tipo !== item.tipo || existing.vencimento !== item.vencimento || money(existing.strike) !== money(item.strike) || existing.estrategia !== item.estrategia) throw new Error("A negociação difere da posição existente. Confira os dados.");
          operationId = existing.id; const before = money(existing.contratos), added = money(item.contratos), total = before + added;
          statements.push(env.DB.prepare("UPDATE operacoes SET contratos = ?, premio_opcao = ?, custos = ?, irrf = ? WHERE id = ?").bind(total, (money(existing.premio_opcao) * before + money(item.premio_opcao) * added) / total, money(existing.custos) + money(item.custos), money(existing.irrf) + money(item.irrf), operationId));
        } else {
          const next = await env.DB.prepare("SELECT COALESCE(MAX(operation_id), 0) + 1 AS id FROM (SELECT id AS operation_id FROM operacoes UNION ALL SELECT CAST(json_extract(payload, '$.id') AS INTEGER) FROM closed_operations)").first();
          operationId = next.id; const fields = Object.keys(item);
          statements.push(env.DB.prepare(`INSERT INTO operacoes (id, ${fields.join(", ")}) VALUES (?, ${fields.map(() => "?").join(", ")})`).bind(operationId, ...fields.map(k => item[k])));
          statements.push(env.DB.prepare("INSERT INTO operation_preferences(operation_id,exercise_interest,underlying_asset,updated_at) VALUES(?,0,?,?) ON CONFLICT(operation_id) DO UPDATE SET underlying_asset=excluded.underlying_asset,updated_at=excluded.updated_at").bind(String(operationId), underlyingForOption(item.ativo, action.values?.underlying_asset), new Date().toISOString()));
        }
      } else if (action.kind !== "record") throw new Error("Ação de importação inválida.");
      const payload = { ...note, operation_id: operationId, apply_status: "applied" };
      statements.push(env.DB.prepare("INSERT INTO brokerage_notes(note_key,payload,imported_at) VALUES(?,?,?)").bind(key, JSON.stringify(payload), new Date().toISOString()));
      await env.DB.batch(statements);
      return json({ ok: true, imported: true, operation_id: operationId });
    } catch (error) { return json({ error: error.message || "Não foi possível importar a negociação." }, 400); }
  }
  if (path === "/api/notes" && request.method === "POST") {
    const body = await request.json().catch(() => ({}));
    const key = String(body.key || "").trim().slice(0, 160);
    const payload = body.payload;
    if (!key || !payload || typeof payload !== "object")
      return json({ error: "Lançamento de nota inválido." }, 400);
    const existing = await env.DB.prepare(
      "SELECT note_key FROM brokerage_notes WHERE note_key = ?",
    ).bind(key).first();
    if (existing) {
      await env.DB.prepare(
        "UPDATE brokerage_notes SET payload = ? WHERE note_key = ?",
      ).bind(JSON.stringify(payload), key).run();
      return json({ ok: true, imported: false, duplicate: true });
    }
    await env.DB.prepare(
      "INSERT INTO brokerage_notes (note_key, payload, imported_at) VALUES (?, ?, ?)",
    ).bind(key, JSON.stringify(payload), new Date().toISOString()).run();
    return json({ ok: true, imported: true, duplicate: false }, 201);
  }
  const noteMatch = path.match(/^\/api\/notes\/(.+)$/);
  if (noteMatch && request.method === "DELETE") {
    const result = await env.DB.prepare(
      "DELETE FROM brokerage_notes WHERE note_key = ?",
    )
      .bind(decodeURIComponent(noteMatch[1]))
      .run();
    return result.meta.changes
      ? new Response(null, { status: 204 })
      : json({ error: "not found" }, 404);
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
    const body = await request.json().catch(() => ({}));
    const item = operationPayload(body);
    if (!item.ativo || !item.data_abertura)
      return json({ error: "ativo e data_abertura são obrigatórios" }, 400);
    if (!["PUT", "CALL"].includes(item.tipo) || !(money(item.strike) > 0) || !(money(item.contratos) > 0) || money(item.premio_opcao) < 0 || !item.vencimento)
      return json({ error: "Confira tipo, strike, quantidade, prêmio e vencimento." }, 400);
    const fields = Object.keys(item);
    const next = await env.DB.prepare("SELECT COALESCE(MAX(operation_id), 0) + 1 AS id FROM (SELECT id AS operation_id FROM operacoes UNION ALL SELECT CAST(json_extract(payload, '$.id') AS INTEGER) FROM closed_operations)").first();
    const operationId = next.id;
    const underlying = underlyingForOption(item.ativo, body.underlying_asset);
    await env.DB.batch([
      env.DB.prepare(`INSERT INTO operacoes (id, ${fields.join(", ")}) VALUES (?, ${fields.map(() => "?").join(", ")})`).bind(operationId, ...fields.map((field) => item[field])),
      env.DB.prepare("INSERT INTO operation_preferences (operation_id, exercise_interest, underlying_asset, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(operation_id) DO UPDATE SET underlying_asset = excluded.underlying_asset, updated_at = excluded.updated_at")
        .bind(String(operationId), body.interesse_exercicio === "true" || body.interesse_exercicio === true ? 1 : 0, underlying, new Date().toISOString()),
    ]);
    return json({ id: operationId }, 201);
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
    const totalContracts = money(operation.contratos);
    const closedContracts = money(body.contratos_fechados || totalContracts);
    if (closedContracts <= 0 || closedContracts > totalContracts)
      return json({ error: "Quantidade de contratos para fechamento é inválida." }, 400);
    const result = money(body.resultado_final);
    const closedAt = String(
      body.data_fechamento || businessDate(),
    );
    const fraction = closedContracts / totalContracts;
    const payload = {
      ...operation,
      contratos: String(closedContracts),
      custos: String(money(operation.custos) * fraction),
      irrf: String(money(operation.irrf) * fraction),
      "Data fechamento": closedAt,
      Resultado_final: result,
      Lucro_tributavel: result,
      Observacoes: String(body.observacoes || "").slice(0, 300),
    };
    const statements = [
      env.DB.prepare(
        "INSERT INTO closed_operations (closed_id, payload, closed_at) VALUES (?, ?, ?)",
      ).bind(recordId(), JSON.stringify(payload), closedAt),
    ];
    if (closedContracts === totalContracts) {
      statements.push(env.DB.prepare("DELETE FROM operacoes WHERE id = ?").bind(Number(closeMatch[1])));
    } else {
      statements.push(
        env.DB.prepare("UPDATE operacoes SET contratos = ?, custos = ?, irrf = ? WHERE id = ?").bind(
          totalContracts - closedContracts,
          money(operation.custos) * (1 - fraction),
          money(operation.irrf) * (1 - fraction),
          Number(closeMatch[1]),
        ),
      );
    }
    await env.DB.batch(statements);
    return json({ ok: true, partial: closedContracts !== totalContracts });
  }
  const exerciseMatch = path.match(/^\/api\/operations\/(\d+)\/exercise$/);
  if (exerciseMatch && request.method === "POST") {
    const operation = await env.DB.prepare(
      "SELECT id, data_abertura, ativo, tipo, estrategia, status, contratos, strike, premio_opcao, custos, irrf, vencimento, cotacao_atual, resultado_realizado FROM operacoes WHERE id = ?",
    ).bind(Number(exerciseMatch[1])).first();
    if (!operation) return json({ error: "not found" }, 404);
    const body = await request.json().catch(() => ({}));
    try {
      const { statements, type } = await exercisePlan(env, operation, body);
      await env.DB.batch(statements);
      return json({ ok: true, exercised: type });
    } catch (error) { return json({ error: error.message }, 400); }
  }
  const reopenMatch = path.match(/^\/api\/closed\/(.+)\/reopen$/);
  if (reopenMatch && request.method === "POST") {
    const closed = await env.DB.prepare(
      "SELECT payload FROM closed_operations WHERE closed_id = ?",
    )
      .bind(reopenMatch[1])
      .first();
    if (!closed) return json({ error: "not found" }, 404);
    const original = JSON.parse(closed.payload);
    const item = operationPayload(original);
    const observation = String(original.Observacoes || original.observacoes || "");
    if (/Exercício de CALL/i.test(observation))
      return json({ error: "Esta CALL foi exercida e entregou ações da carteira. Reabra-a apenas após conferir a reversão da entrega." }, 400);
    const originalId = Number(original.id);
    const existing = Number.isInteger(originalId) ? await env.DB.prepare("SELECT * FROM operacoes WHERE id = ?").bind(originalId).first() : null;
    if (existing && (existing.ativo !== item.ativo || existing.tipo !== item.tipo || existing.vencimento !== item.vencimento || money(existing.strike) !== money(item.strike)))
      return json({ error: "A posição original foi alterada. Confira os dados antes de reabrir." }, 400);
    const exercisedPut = /Exercício de PUT/i.test(observation);
    if (exercisedPut) {
      const lot = await env.DB.prepare("SELECT payload FROM equity_lots WHERE lot_id = ?").bind(`exercise:${original.id}`).first();
      const position = lot && JSON.parse(lot.payload);
      if (!position || money(position.available_quantity ?? position.quantity) !== money(position.quantity))
        return json({ error: "As ações do exercício foram alteradas ou entregues. Confira a reversão antes de reabrir." }, 400);
      const coverage = await env.DB.prepare("SELECT id FROM operacoes WHERE tipo = 'CALL' AND status = 'Aberta' AND substr(ativo,1,4) = ?").bind(item.ativo.slice(0,4)).first();
      if (coverage) return json({ error: "As ações podem estar reservadas em uma CALL. Encerre a cobertura antes de desfazer o exercício." }, 400);
    }
    const fields = Object.keys(item), statements = [];
    if (existing) {
      const before = money(existing.contratos), added = money(item.contratos), total = before + added;
      statements.push(env.DB.prepare("UPDATE operacoes SET contratos = ?, premio_opcao = ?, custos = ?, irrf = ? WHERE id = ?").bind(total, (money(existing.premio_opcao)*before + money(item.premio_opcao)*added)/total, money(existing.custos)+money(original.opening_costs ?? item.custos), money(existing.irrf)+money(original.opening_irrf ?? item.irrf), originalId));
    } else {
      const next = await env.DB.prepare("SELECT COALESCE(MAX(operation_id),0)+1 AS id FROM (SELECT id AS operation_id FROM operacoes UNION ALL SELECT CAST(json_extract(payload,'$.id') AS INTEGER) FROM closed_operations)").first();
      const id = Number.isInteger(originalId) && originalId > 0 ? originalId : next.id;
      item.custos = String(money(original.opening_costs ?? item.custos)); item.irrf = String(money(original.opening_irrf ?? item.irrf));
      statements.push(env.DB.prepare(`INSERT INTO operacoes (id, ${fields.join(", ")}) VALUES (?, ${fields.map(() => "?").join(", ")})`).bind(id, ...fields.map(field=>item[field])));
    }
    statements.push(env.DB.prepare("DELETE FROM closed_operations WHERE closed_id = ?").bind(reopenMatch[1]));
    if (exercisedPut) statements.push(env.DB.prepare("DELETE FROM equity_lots WHERE lot_id = ?").bind(`exercise:${original.id}`));
    await env.DB.batch(statements);
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
      date: String(body.date || businessDate()),
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
        body.payment_date || businessDate(),
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
        body.acquisition_date || businessDate(),
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
        body.acquisition_date || businessDate(),
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
      date: String(body.sale_date || businessDate()),
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
    if (path.startsWith("/api/")) {
      try { return await api(request, env, path); }
      catch { return json({ error: "Não foi possível concluir a operação. Tente novamente." }, 500); }
    }
    const assetUrl = new URL(request.url);
    assetUrl.pathname = path === "/" ? "/free-pilot/index.html" : path;
    assetUrl.search = "";
    const response = await env.ASSETS.fetch(assetUrl);
    const headers = new Headers(response.headers);
    headers.set("Cache-Control", "no-store");
    return new Response(response.body, { status: response.status, headers });
  },
};
