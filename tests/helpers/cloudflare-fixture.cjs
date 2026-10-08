const fs = require("node:fs"),
  path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const { pathToFileURL } = require("node:url");
function database() {
  const db = new DatabaseSync(":memory:");
  for (const name of [
    "0001_initial_schema.sql",
    "0002_closed_operations.sql",
    "0003_market_snapshots.sql",
  ])
    db.exec(
      fs.readFileSync(
        path.join(__dirname, "../../cloudflare/pilot/migrations", name),
        "utf8",
      ),
    );
  const wrap = (sql, args = []) => ({
    sql,
    args,
    bind(...values) {
      return wrap(sql, values);
    },
    async first() {
      return db.prepare(sql).get(...args) || null;
    },
    async all() {
      return { results: db.prepare(sql).all(...args) };
    },
    async run() {
      const r = db.prepare(sql).run(...args);
      return {
        meta: {
          changes: Number(r.changes),
          last_row_id: Number(r.lastInsertRowid),
        },
      };
    },
  });
  return {
    db,
    prepare: (sql) => wrap(sql),
    async batch(statements) {
      db.exec("BEGIN");
      try {
        const results = [];
        for (const s of statements) results.push(await s.run());
        db.exec("COMMIT");
        return results;
      } catch (e) {
        db.exec("ROLLBACK");
        throw e;
      }
    },
  };
}
async function setup() {
  const worker = (
    await import(
      pathToFileURL(
        path.join(__dirname, "../../cloudflare/free-pilot/src/index.js"),
      )
    )
  ).default;
  const env = {
    DB: database(),
    ADMIN_PIN: "test-fixture-only",
    SESSION_SECRET: "test-fixture-session-secret",
    ASSETS: { fetch: async () => new Response("asset") },
  };
  const call = async (
    route,
    body,
    method = body ? "POST" : "GET",
    auth = true,
  ) => {
    const r = await worker.fetch(
      new Request("https://test.invalid/faculdademaria/api" + route, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(auth && token ? { Authorization: "Bearer " + token } : {}),
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      }),
      env,
    );
    return r;
  };
  let token;
  token = (
    await (await call("/session", { pin: env.ADMIN_PIN }, "POST", false)).json()
  ).token;
  const backup = {
    format: "faculdademaria-cloudflare-backup",
    version: 1,
    data: Object.fromEntries(
      [
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
      ].map((k) => [k, []]),
    ),
  };
  backup.data.taxpayer = {};
  backup.data.config = [{ parametro: "Tamanho contrato opcoes", valor: "100" }];
  await call("/restore", backup);
  return { env, call, backup, worker };
}
const op = (overrides = {}) => ({
  data_abertura: "2026-10-01",
  ativo: "PETRV480",
  tipo: "PUT",
  estrategia: "Venda",
  contratos: "1",
  strike: "48",
  premio_opcao: "1",
  custos: "2",
  irrf: ".05",
  vencimento: "2026-10-16",
  ...overrides,
});

module.exports = { database, setup, op };
