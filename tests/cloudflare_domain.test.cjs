const { test } = require("node:test"),
  assert = require("node:assert/strict");
const D = require("../static/free-pilot/domain.js");
const M = require("../static/free-pilot/market-data.js");
const day = "2026-10-08",
  option = {
    asset: "BBAS3",
    option_code: "BBASW270",
    option_type: "PUT",
    expiry: "2026-11-20",
    spot_price: 28.5,
    strike: 27,
    premium: 1.1,
    bid: 1,
    ask: 1.15,
    liquidity: 32000,
    timestamp: day,
  };
const profile = {
  assignment_eligible: true,
  long_term_suitable: true,
  quality_score: 0.88,
  data_confidence: 0.9,
};
test("PUT price, ROI, explicit costs and expiry limits", () => {
  const m = D.metrics(option, { asOf: day, quantity: 100, costs: 2 });
  assert.equal(m.net_price, 25.9);
  assert.ok(Math.abs(m.roi - 1.1 / 27) < 1e-10);
  assert.equal(m.dte, 43);
  assert.equal(m.capital, 2700);
  assert.equal(D.metrics({ ...option, spot_price: 0 }, { asOf: day }), null);
  assert.equal(
    D.metrics({ ...option, expiry: "2026-10-07" }, { asOf: day }),
    null,
  );
  assert.equal(
    D.metrics({ ...option, expiry: day }, { asOf: day }).annualized_roi,
    null,
  );
});
test("quality, liquidity and concentration override a high premium", () => {
  assert.equal(D.assess(option, profile, {}, day).status, "eligible");
  assert.equal(
    D.assess(
      { ...option, premium: 5 },
      { ...profile, assignment_eligible: false },
      {},
      day,
    ).score,
    null,
  );
  assert.equal(D.assess(option, {}, {}, day).status, "insufficient_data");
  assert.equal(
    D.assess(option, { ...profile, concentration_pct: 0.36 }, {}, day).status,
    "ineligible",
  );
  assert.equal(
    D.assess({ ...option, liquidity: 500 }, profile, {}, day).status,
    "ineligible",
  );
});
test("probability needs observed volatility and handles PUT/CALL consistently", () => {
  assert.equal(D.probability("PUT", 20, 21, 30, null), null);
  assert.equal(D.probability("PUT", 20, 21, 0, null), 1);
  const p = D.probability("PUT", 20, 21, 30, 0.3),
    c = D.probability("CALL", 20, 21, 30, 0.3);
  assert.ok(p > 0.5);
  assert.ok(Math.abs(p + c - 1) < 1e-12);
  assert.equal(D.historicalVolatility(Array(30).fill(20)), null);
  assert.equal(D.historicalVolatility([1, 2]), null);
});
test("CSV accepts Brazilian decimals, quotes and both option types; rejects expired rows", () => {
  const csv =
    'ativo;opcao;tipo;vencimento;cotacao;strike;premio;volume\nBBAS3;BBASW270;PUT;20/11/2026;"28,50";27;"1,10";32000\nBBAS3;BBASK300;CALL;20/11/2026;28,50;30;0,50;20000\nBBAS3;OLD123;PUT;01/01/2026;28;27;1;1';
  const r = D.csv(csv, day);
  assert.equal(r.opportunities.length, 2);
  assert.equal(r.opportunities[0].premium, 1.1);
  assert.equal(r.rejected_rows.length, 1);
  assert.throws(() => D.csv("ativo;premio\nBBAS3;1", day), /Coluna/);
  assert.equal(D.dateValue("2026-02-30"), null);
});
test("losses, IRRF and sub-R$10 DARF carry are separate from day trade", () => {
  const rows = D.taxProjection(
    [
      {
        Data_fechamento: "2026-08-05",
        Data_abertura: "2026-08-01",
        Resultado_realizado: -100,
      },
      {
        Data_fechamento: "2026-09-05",
        Data_abertura: "2026-09-01",
        Resultado_realizado: 140,
        IRRF: 1,
      },
      {
        Data_fechamento: "2026-10-01",
        Data_abertura: "2026-10-01",
        Resultado_realizado: 100,
        IRRF: 1,
      },
    ],
    [],
    day,
  );
  assert.equal(rows[1].common_loss_compensated, 100);
  assert.equal(rows[1].estimated_darf, 0);
  assert.equal(rows[2].estimated_darf, 24.35);
  assert.equal(rows[2].day_taxable_base, 101);
  assert.equal(rows[2].due_date, "2026-11-30");
});
test("PUT assignment defers result, unknown CALL basis requires review", () => {
  const rows = D.taxProjection(
    [
      {
        tipo: "PUT",
        closed_at: "2026-10-08",
        Observacoes: "Exercício de PUT",
        Resultado_final: 100,
      },
      {
        tipo: "CALL",
        closed_at: "2026-10-08",
        Observacoes: "Exercício de CALL",
        Resultado_final: 100,
      },
    ],
    [],
    day,
  );
  const r = rows.find((r) => r.competence === "2026-10");
  assert.equal(r.deferred_count, 1);
  assert.equal(r.review_count, 1);
  assert.equal(r.tax_calculated, 0);
  assert.equal(r.status, "Revisar exercício");
});
test("covered CALL scanner exposes existing coverage and never suggests below cost", () => {
  const calls = [{ ...option, option_type: "CALL", strike: 30, premium: 0.8 }];
  const rows = D.coveredCalls(
    calls,
    [{ asset: "BBAS3", quantity: 100, available_quantity: 0, average: 27 }],
    day,
  );
  assert.equal(rows.length, 1);
  assert.equal(rows[0].replacement_required, true);
  assert.equal(rows[0].contracts, 0);
  assert.equal(
    D.coveredCalls(
      calls,
      [{ asset: "BBAS3", quantity: 100, available_quantity: 100, average: 31 }],
      day,
    ).length,
    0,
  );
});
test("Jade uses actual quoted legs and rejects missing bid/ask", () => {
  const put = { ...option, bid: 2, liquidity: 2000, expiry: "2026-11-06" },
    short = {
      ...put,
      option_type: "CALL",
      option_code: "BBASK300",
      strike: 30,
      bid: 1,
      ask: 1.1,
    },
    long = {
      ...short,
      option_code: "BBASK310",
      strike: 31,
      bid: 0.4,
      ask: 0.5,
    };
  const rows = D.jade([put, short, long], day);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].credit, 2.5);
  assert.equal(D.jade([{ ...put, bid: null }, short, long], day).length, 0);
});
test("roll uses correct sign for closing debit and requires later expiration", () => {
  const rows = D.roll(
    {
      asset: "BBAS3",
      tipo: "PUT",
      ativo: "BBASV270",
      vencimento: "2026-10-16",
      strike: 27,
    },
    [option],
    0.6,
    100,
    day,
  );
  assert.equal(rows[0].net_credit, 40);
  assert.equal(rows[0].extra_days, 35);
  assert.equal(
    D.roll(
      {
        asset: "BBAS3",
        tipo: "PUT",
        ativo: option.option_code,
        vencimento: "2026-10-16",
      },
      [option],
      0.6,
      100,
      day,
    ).length,
    0,
  );
});
test("CVM never invents missing fundamentals and reproduces financial model", () => {
  const universe = [
    {
      asset: "TEST3",
      cnpj: "00.000.000/0001-00",
      model: "financial",
      assignment_eligible: true,
      long_term_suitable: true,
    },
  ];
  const lines = [
    "CNPJ_CIA;ORDEM_EXERC;CD_CONTA;VL_CONTA",
    "00.000.000/0001-00;ÚLTIMO;3.11;20",
    "00.000.000/0001-00;PENÚLTIMO;3.11;10",
    "00.000.000/0001-00;ÚLTIMO;2.08;100",
    "00.000.000/0001-00;PENÚLTIMO;2.08;90",
  ];
  const bytes = Uint8Array.from(Buffer.from(lines.join("\n"), "latin1"));
  assert.equal(
    M.cvm({ "DRE_con.csv": bytes }, universe, 2025)[0].quality_score,
    1,
  );
  assert.equal(M.cvm({}, universe, 2025)[0].quality_score, null);
});

test("reconciliation treats a negative brokerage debit as an outflow exactly once", () => {
  const { audit, compare } = require("../scripts/audit_cloudflare_backup.cjs");
  const b = {
    format: "faculdademaria-cloudflare-backup",
    version: 1,
    data: { notes: [{ key: "debit", cash_direction: "D", net_cash: -25 }] },
  };
  assert.equal(audit(b).notes_net_cash, -25);
  const after = structuredClone(b);
  after.data.notes[0].imported_at = "2026-10-08";
  assert.equal(compare(b, after).notes.changed.length, 0);
  after.data.notes[0].net_cash = -26;
  assert.equal(compare(b, after).notes.changed.length, 1);
});

test("source reconciliation preserves newer records and checks CALL deliveries", () => {
  const { reconcileSource } = require("../scripts/audit_cloudflare_backup.cjs");
  const original = {
    data: {
      equities: [
        {
          lot_id: "lot",
          asset: "PETR4",
          quantity: 100,
          available_quantity: 100,
          tax_cost_total: 4800,
        },
      ],
      closed: [],
      taxpayer: {},
    },
  };
  const destination = structuredClone(original);
  destination.data.equities[0].available_quantity = 0;
  destination.data.closed.push({
    closed_id: "new",
    ativo: "PETRJ500",
    tipo: "CALL",
    contratos: 1,
    Observacoes: "Exercício de CALL",
  });
  assert.deepEqual(reconcileSource(original, destination).issues, []);
  destination.data.closed = [];
  assert.ok(
    reconcileSource(original, destination).issues.some((x) =>
      x.includes("saldo não explicado"),
    ),
  );
  destination.data.equities = [];
  assert.ok(
    reconcileSource(original, destination).issues.some((x) =>
      x.includes("ausente lot"),
    ),
  );
});
