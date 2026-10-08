#!/usr/bin/env node
// Read-only reconciliation. Does not alter application data or contact a service.
const fs = require("node:fs");
const crypto = require("node:crypto");
const number = (v) => {
  const s = String(v ?? "").replace(/R\$|\s/g, "");
  return (
    Number(s.includes(",") ? s.replace(/\./g, "").replace(",", ".") : s) || 0
  );
};
const round = (v) => Math.round(v * 100) / 100;
function audit(backup) {
  if (
    backup.format !== "faculdademaria-cloudflare-backup" ||
    backup.version !== 1 ||
    !backup.data
  )
    throw Error("Backup inválido");
  const d = backup.data,
    issues = [],
    warnings = [];
  const size =
    number(
      (d.config || []).find((x) => x.parametro === "Tamanho contrato opcoes")
        ?.valor,
    ) || 100;
  const ids = {
    operations: "id",
    closed: "closed_id",
    notes: "key",
    equities: "lot_id",
    cash: "id",
    darfs: "id",
  };
  for (const [table, key] of Object.entries(ids)) {
    const seen = new Set();
    for (const row of d[table] || []) {
      if (!row[key] || seen.has(String(row[key])))
        issues.push(`${table}: identificador ausente/duplicado ${row[key]}`);
      seen.add(String(row[key]));
    }
  }
  for (const lot of d.equities || []) {
    const q = number(lot.quantity),
      a = number(lot.available_quantity ?? lot.quantity);
    if (a < 0 || a > q) issues.push(`Lote ${lot.lot_id}: saldo incompatível`);
  }
  const available = {};
  for (const lot of d.equities || [])
    available[lot.asset] =
      (available[lot.asset] || 0) +
      number(lot.available_quantity ?? lot.quantity);
  const covered = {};
  for (const op of d.operations || []) {
    if (
      String(op.tipo).toUpperCase() === "CALL" &&
      /venda|coberta/i.test(op.estrategia)
    ) {
      const pref = (d.operation_preferences || []).find(
        (x) => String(x.operation_id) === String(op.id),
      );
      const asset = pref?.underlying_asset || op.ativo.slice(0, 4);
      covered[asset] = (covered[asset] || 0) + number(op.contratos) * size;
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(op.data_abertura || ""))
      issues.push(`Operação ${op.id}: data ausente/inválida`);
  }
  for (const [asset, q] of Object.entries(covered))
    if (q > (available[asset] || 0))
      warnings.push(
        `CALL ${asset}: cobertura solicitada ${q}, disponível ${available[asset] || 0}`,
      );
  const notes = d.notes || [];
  const noteCash = round(
    notes.reduce(
      (s, n) =>
        s + (n.cash_direction === "D" ? -1 : 1) * Math.abs(number(n.net_cash)),
      0,
    ),
  );
  const snapshot = {
    counts: Object.fromEntries(
      Object.entries(d)
        .filter(([, v]) => Array.isArray(v))
        .map(([k, v]) => [k, v.length]),
    ),
    available_equities: available,
    notes_net_cash: noteCash,
    issues,
    warnings,
  };
  return snapshot;
}
function compare(before, after) {
  const out = {};
  for (const table of [
    "operations",
    "closed",
    "cash",
    "notes",
    "darfs",
    "equities",
    "config",
    "operation_preferences",
    "manual_option_quotes",
    "api_market_quotes",
    "operation_closure_metadata",
  ]) {
    const key = {
      operations: "id",
      closed: "closed_id",
      cash: "id",
      notes: "key",
      darfs: "id",
      equities: "lot_id",
      config: "parametro",
      operation_preferences: "operation_id",
      manual_option_quotes: "option_code",
      api_market_quotes: "symbol",
      operation_closure_metadata: "operation_id",
    }[table];
    const hash = (row) =>
      crypto
        .createHash("sha256")
        .update(
          JSON.stringify(
            Object.fromEntries(
              Object.entries(row).sort(([a], [b]) => a.localeCompare(b)),
            ),
          ),
        )
        .digest("hex");
    const a = new Map(
        (before.data[table] || []).map((x) => [
          String(
            table === "api_market_quotes"
              ? x.quote_kind + ":" + x.symbol
              : x[key],
          ),
          x,
        ]),
      ),
      b = new Map(
        (after.data[table] || []).map((x) => [
          String(
            table === "api_market_quotes"
              ? x.quote_kind + ":" + x.symbol
              : x[key],
          ),
          x,
        ]),
      );
    const metadata = ["created_at", "imported_at"];
    const comparable = (row, reference) =>
      Object.fromEntries(
        Object.entries(row).filter(
          ([field]) =>
            !metadata.includes(field) || Object.hasOwn(reference, field),
        ),
      );
    out[table] = {
      missing: [...a.keys()].filter((k) => !b.has(k)),
      added: [...b.keys()].filter((k) => !a.has(k)),
      changed: [...a.keys()].filter(
        (k) =>
          b.has(k) && hash(a.get(k)) !== hash(comparable(b.get(k), a.get(k))),
      ),
      metadata_added: [...a.keys()].filter(
        (k) =>
          b.has(k) &&
          metadata.some(
            (field) =>
              !Object.hasOwn(a.get(k), field) && Object.hasOwn(b.get(k), field),
          ),
      ).length,
    };
  }
  return out;
}
function reconcileSource(source, destination) {
  const a = source.data,
    b = destination.data,
    issues = [],
    inventory = {};
  const tables = {
    operations: "id",
    closed: "closed_id",
    notes: "key",
    cash: "id",
    darfs: "id",
    equities: "lot_id",
    config: "parametro",
    operation_preferences: "operation_id",
    manual_option_quotes: "option_code",
    operation_closure_metadata: "operation_id",
  };
  const ignored = new Set([
    "created_at",
    "imported_at",
    "updated_at",
    "event_id",
    "note_key",
  ]);
  for (const [table, key] of Object.entries(tables)) {
    const original = new Map((a[table] || []).map((r) => [String(r[key]), r])),
      current = new Map((b[table] || []).map((r) => [String(r[key]), r]));
    const missing = [...original.keys()].filter((id) => !current.has(id));
    missing.forEach((id) => issues.push(`${table}: ausente ${id}`));
    const changed = [];
    for (const [id, row] of original) {
      const target = current.get(id);
      if (!target) continue;
      const differences = Object.keys(row).filter(
        (field) =>
          !ignored.has(field) &&
          !(table === "equities" && field === "available_quantity") &&
          String(row[field] ?? "") !== String(target[field] ?? ""),
      );
      if (table === "operation_preferences")
        differences.splice(
          differences.indexOf("exercise_interest"),
          differences.includes("exercise_interest") &&
            Number(Boolean(row.exercise_interest)) ===
              Number(target.exercise_interest)
            ? 1
            : 0,
        );
      if (differences.length) {
        changed.push({ id, fields: differences });
        if (!["manual_option_quotes", "operation_preferences"].includes(table))
          issues.push(
            `${table}: divergência ${id} (${differences.join(", ")})`,
          );
      }
    }
    inventory[table] = {
      source: original.size,
      destination: current.size,
      missing,
      added: [...current.keys()].filter((id) => !original.has(id)).length,
      updated: changed,
    };
  }
  const originalClose = new Set((a.closed || []).map((r) => r.closed_id)),
    newClosed = (b.closed || []).filter((r) => !originalClose.has(r.closed_id));
  const roots = {
    BBAS: "BBAS3",
    BBDC: "BBDC4",
    CPLE: "CPLE3",
    PETR: "PETR4",
    VALE: "VALE3",
    ITUB: "ITUB4",
    ITSA: "ITSA4",
  };
  const size =
    number(
      (b.config || []).find((x) => x.parametro === "Tamanho contrato opcoes")
        ?.valor,
    ) || 100;
  const delivery = {};
  for (const row of newClosed)
    if (row.tipo === "CALL" && /exerc/i.test(row.Observacoes || "")) {
      const asset = roots[row.ativo.slice(0, 4)] || row.ativo.slice(0, 4);
      delivery[asset] = (delivery[asset] || 0) + number(row.contratos) * size;
    }
  const holdings = (a.equities || []).map((row) => {
    const target = (b.equities || []).find((r) => r.lot_id === row.lot_id);
    return {
      asset: row.asset,
      source_available: number(row.available_quantity ?? row.quantity),
      destination_available: number(
        target?.available_quantity ?? target?.quantity,
      ),
    };
  });
  for (const asset of new Set(holdings.map((r) => r.asset))) {
    const reduction = holdings
      .filter((r) => r.asset === asset)
      .reduce(
        (sum, r) => sum + r.source_available - r.destination_available,
        0,
      );
    if (reduction !== (delivery[asset] || 0))
      issues.push(
        `Carteira ${asset}: saldo não explicado pelos exercícios posteriores.`,
      );
  }
  if (JSON.stringify(a.taxpayer) !== JSON.stringify(b.taxpayer))
    issues.push("Perfil fiscal divergente.");
  return {
    inventory,
    holdings,
    delivery_from_new_closed_calls: delivery,
    issues,
    policy:
      "Preserva as cotações e preferências mais recentes do Cloudflare e verifica a entrega de ações pelas CALLs novas.",
  };
}
module.exports = { audit, compare, reconcileSource };
if (require.main === module) {
  const [input, other, mode] = process.argv.slice(2);
  if (!input)
    throw Error(
      "Uso: node scripts/audit_cloudflare_backup.cjs <backup.json> [outro.json]",
    );
  const first = JSON.parse(fs.readFileSync(input));
  const report = audit(first);
  if (other)
    report.comparison = (mode === "--source" ? reconcileSource : compare)(
      first,
      JSON.parse(fs.readFileSync(other)),
    );
  console.log(JSON.stringify(report, null, 2));
  if (report.issues.length || report.comparison?.issues?.length)
    process.exitCode = 1;
}
