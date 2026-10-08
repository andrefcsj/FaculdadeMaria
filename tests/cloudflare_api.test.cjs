const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { DatabaseSync } = require("node:sqlite");
const { pathToFileURL } = require("node:url");
const { database, setup, op } = require("./helpers/cloudflare-fixture.cjs");
test("authentication, malformed token and path prefix", async () => {
  const { call, worker, env } = await setup();
  assert.equal((await call("/dashboard", null, "GET", false)).status, 401);
  assert.equal(
    (
      await worker.fetch(
        new Request("https://test.invalid/faculdademaria/api/dashboard", {
          headers: { Authorization: "Bearer !!!!.!!!" },
        }),
        env,
      )
    ).status,
    401,
  );
  assert.equal(
    (
      await worker.fetch(
        new Request("https://test.invalid/faculdademaria"),
        env,
      )
    ).status,
    302,
  );
  assert.equal(
    (await worker.fetch(new Request("https://test.invalid/outside"), env))
      .status,
    404,
  );
});
test("restore >100 records is atomic and preserves dates", async () => {
  const { call, backup } = await setup();
  backup.data.api_market_quotes = Array.from({ length: 4050 }, (_, i) => ({
    quote_kind: "option",
    symbol: "TEST" + i,
    price: 1,
    source: "fixture",
    quoted_at: "2026-10-08T12:00:00Z",
  }));
  backup.data.cash = [
    {
      id: "one",
      date: "2026-10-01",
      amount: "100",
      kind: "aporte",
      created_at: "2026-10-01T12:00:00Z",
    },
  ];
  assert.equal((await call("/restore", backup)).status, 200);
  const saved = await (await call("/backup")).json();
  assert.equal(saved.data.api_market_quotes.length, 4050);
  assert.equal(saved.data.cash[0].created_at, backup.data.cash[0].created_at);
  // Force a SQL constraint failure at the end, after other tables would be cleared.
  const bad = structuredClone(backup);
  bad.data.api_market_quotes[0].price = null;
  bad.data.cash = [];
  assert.equal((await call("/restore", bad)).status, 400);
  const after = await (await call("/backup")).json();
  assert.equal(after.data.cash.length, 1);
  assert.equal(after.data.api_market_quotes.length, 4050);
  const missing = structuredClone(backup);
  delete missing.data.cash;
  assert.equal((await call("/restore", missing)).status, 400);
  assert.equal((await (await call("/backup")).json()).data.cash.length, 1);
});
test("partial repurchase conserves premium, contracts and opening costs", async () => {
  const { call } = await setup();
  const { id } = await (
    await call("/operations", op({ contratos: "2", custos: "4", irrf: ".10" }))
  ).json();
  assert.equal(
    (
      await call(`/operations/${id}/close`, {
        contratos_fechados: 1,
        resultado_final: 47.95,
        data_fechamento: "2026-10-08",
        observacoes: "Recompra",
      })
    ).status,
    200,
  );
  const d = await (await call("/dashboard")).json();
  assert.equal(Number(d.operations[0].contratos), 1);
  assert.equal(Number(d.operations[0].custos), 2);
  assert.equal(Number(d.closed[0].custos), 2);
  assert.equal(d.closed.length, 1);
});
test("PUT exercise acquires shares once and closes option", async () => {
  const { call } = await setup();
  const { id } = await (await call("/operations", op())).json();
  const exercise = {
    quantity: 100,
    asset: "PETR4",
    exercise_price: 48,
    costs: 1,
    data_fechamento: "2026-10-08",
  };
  assert.equal(
    (await call(`/operations/${id}/exercise`, exercise)).status,
    200,
  );
  const d = await (await call("/dashboard")).json();
  assert.equal(d.operations.length, 0);
  assert.equal(d.closed.length, 1);
  assert.equal(d.equities[0].available_quantity, 100);
  assert.equal(Number(d.equities[0].tax_cost_total), 4703.05);
  assert.equal(
    (await call(`/operations/${id}/exercise`, exercise)).status,
    404,
  );
});
test("CALL assignment verifies coverage and delivers available shares", async () => {
  const { call } = await setup();
  const { id } = await (
    await call(
      "/operations",
      op({
        tipo: "CALL",
        ativo: "PETRJ500",
        strike: "50",
        underlying_asset: "PETR4",
      }),
    )
  ).json();
  const e = {
    quantity: 100,
    asset: "PETR4",
    exercise_price: 50,
    data_fechamento: "2026-10-08",
  };
  assert.equal((await call(`/operations/${id}/exercise`, e)).status, 400);
  assert.equal((await (await call("/dashboard")).json()).operations.length, 1);
  await call("/equities", {
    asset: "PETR4",
    quantity: 100,
    average_price: 48,
    acquisition_date: "2026-09-10",
  });
  assert.equal((await call(`/operations/${id}/exercise`, e)).status, 200);
  const d = await (await call("/dashboard")).json();
  assert.equal(d.equities[0].available_quantity, 0);
  assert.equal(d.closed.length, 1);
});
test("invalid exercise quantity leaves all records intact", async () => {
  const { call } = await setup();
  const { id } = await (await call("/operations", op())).json();
  assert.equal(
    (
      await call(`/operations/${id}/exercise`, {
        quantity: 200,
        asset: "PETR4",
      })
    ).status,
    400,
  );
  const d = await (await call("/dashboard")).json();
  assert.equal(d.operations.length, 1);
  assert.equal(d.closed.length, 0);
  assert.equal(d.equities.length, 0);
});
test("atomic note import can be retried after failure without a phantom note", async () => {
  const { call } = await setup();
  const { id } = await (
    await call(
      "/operations",
      op({ tipo: "CALL", ativo: "PETRJ500", strike: "50" }),
    )
  ).json();
  const body = {
    key: "fixture-exercise",
    payload: {
      trade_date: "2026-10-08",
      trade: {
        option_code: "PETRJ500",
        event_type: "exercise",
        quantity: 100,
        side: "Venda",
      },
      net_cash: "5000",
      cash_direction: "C",
    },
    action: {
      kind: "exercise",
      operation_id: id,
      values: { quantity: 100, asset: "PETR4", exercise_price: 50 },
    },
  };
  assert.equal((await call("/notes/import", body)).status, 400);
  assert.equal((await (await call("/dashboard")).json()).notes.length, 0);
  await call("/equities", { asset: "PETR4", quantity: 100, average_price: 48 });
  assert.equal((await call("/notes/import", body)).status, 200);
  assert.equal(
    (await (await call("/notes/import", body)).json()).duplicate,
    true,
  );
  const d = await (await call("/dashboard")).json();
  assert.equal(d.closed.length, 1);
  assert.equal(d.notes.length, 1);
  assert.equal(d.equities[0].available_quantity, 0);
  assert.equal(d.closed[0].exercise_tax_result, 297.95);
});
test("second sale adds contracts and weighted premium once", async () => {
  const { call } = await setup();
  const importSale = (key, premium) => ({
    key,
    payload: {
      trade_date: "2026-10-01",
      trade: { option_code: "PETRV480", side: "Venda", quantity: 100 },
      cash_direction: "C",
      net_cash: String(premium * 100),
    },
    action: { kind: "opening", values: op({ premio_opcao: String(premium) }) },
  });
  assert.equal(
    (await call("/notes/import", importSale("first", 1))).status,
    200,
  );
  assert.equal(
    (await call("/notes/import", importSale("second", 2))).status,
    200,
  );
  const d = await (await call("/dashboard")).json();
  assert.equal(d.operations.length, 1);
  assert.equal(Number(d.operations[0].contratos), 2);
  assert.equal(Number(d.operations[0].premio_opcao), 1.5);
  assert.equal(d.notes.length, 2);
  await call("/notes/import", importSale("second", 2));
  assert.equal((await (await call("/dashboard")).json()).notes.length, 2);
});
test("new operations never reuse a closed operation identifier after restore", async () => {
  const { call, backup } = await setup();
  backup.data.closed = [
    { id: 50, ativo: "OLD", closed_id: "old", closed_at: "2026-09-01" },
  ];
  await call("/restore", backup);
  const r = await (await call("/operations", op())).json();
  assert.equal(r.id, 51);
});
test("market cache validates import and survives backup roundtrip", async () => {
  const { call } = await setup();
  const o = {
    asset: "PETR4",
    option_code: "PETRV480",
    option_type: "PUT",
    expiry: "2026-10-16",
    spot_price: 49,
    strike: 48,
    premium: 1,
  };
  assert.equal(
    (await call("/market/import", { opportunities: [o], source: "fixture" }))
      .status,
    200,
  );
  assert.equal(
    (await call("/market/import", { opportunities: [{ ...o, strike: 0 }] }))
      .status,
    400,
  );
  const backup = await (await call("/backup")).json();
  assert.equal(backup.data.market_snapshots.length, 1);
  assert.equal((await call("/restore", backup)).status, 200);
  assert.equal(
    (await (await call("/market/chains")).json()).chains[0].opportunities
      .length,
    1,
  );
  assert.equal((await call("/market/chain/PETR4")).status, 503);
});

test("partial close reopens into the original position without changing its identifier", async () => {
  const { call } = await setup();
  const { id } = await (
    await call("/operations", op({ contratos: "2", custos: "4", irrf: ".10" }))
  ).json();
  await call(`/operations/${id}/close`, {
    contratos_fechados: 1,
    resultado_final: 50,
    data_fechamento: "2026-10-08",
  });
  const d = await (await call("/dashboard")).json();
  assert.equal(
    (await call(`/closed/${d.closed[0].closed_id}/reopen`, {})).status,
    200,
  );
  const reopened = await (await call("/dashboard")).json();
  assert.equal(reopened.operations.length, 1);
  assert.equal(reopened.operations[0].id, id);
  assert.equal(Number(reopened.operations[0].contratos), 2);
  assert.equal(Number(reopened.operations[0].custos), 4);
  assert.equal(reopened.closed.length, 0);
});
test("PUT exercise reversal preserves identity and refuses altered share lots", async () => {
  const { call, env } = await setup();
  const { id } = await (await call("/operations", op())).json();
  await call(`/operations/${id}/exercise`, {
    quantity: 100,
    asset: "PETR4",
    exercise_price: 48,
  });
  let d = await (await call("/dashboard")).json();
  const key = d.closed[0].closed_id;
  const lot = d.equities[0];
  await env.DB.prepare("UPDATE equity_lots SET payload=? WHERE lot_id=?")
    .bind(JSON.stringify({ ...lot, available_quantity: 0 }), lot.lot_id)
    .run();
  assert.equal((await call(`/closed/${key}/reopen`, {})).status, 400);
  await env.DB.prepare("UPDATE equity_lots SET payload=? WHERE lot_id=?")
    .bind(JSON.stringify(lot), lot.lot_id)
    .run();
  assert.equal((await call(`/closed/${key}/reopen`, {})).status, 200);
  d = await (await call("/dashboard")).json();
  assert.equal(d.equities.length, 0);
  assert.equal(d.operations[0].id, id);
});
