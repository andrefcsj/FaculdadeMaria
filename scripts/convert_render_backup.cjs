#!/usr/bin/env node
// Converts the portable Render ZIP to the Cloudflare pilot backup format.
// It is deliberately offline: this script never contacts Render or Cloudflare.
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  throw new Error('Uso: node scripts/convert_render_backup.cjs <backup.zip> <saida.json>');
}
const readZip = (entry) =>
  execFileSync('unzip', ['-p', input, entry], { encoding: 'utf8', maxBuffer: 20 * 1024 * 1024 });
const table = (name) => JSON.parse(readZip(`database/${name}.json`)).rows || [];
const asPayload = (rows, key, extra = {}) =>
  rows.map((row) => ({ ...(row.payload || {}), [key]: row[key], ...extra }));
const metadata = new Map(
  table('operation_closure_metadata').map((row) => [String(row.operation_id), row.payload || {}]),
);
const operations = table('operacoes');
const open = operations
  .filter((row) => String(row.status).toLowerCase() === 'aberta')
  .map((row) => ({ ...row, status: 'Aberta' }));
const closed = operations
  .filter((row) => String(row.status).toLowerCase() !== 'aberta')
  .map((row) => {
    const close = metadata.get(String(row.id)) || {};
    const result = String(close.result ?? row.resultado_realizado ?? '0');
    const closedAt = String(close.close_date || row.vencimento || row.data_abertura);
    return {
      ...row,
      status: 'Encerrada',
      closed_id: `render-${row.id}`,
      closed_at: closedAt,
      'Data fechamento': closedAt,
      Resultado_final: result,
      Lucro_tributavel: result,
      Observacoes: String(close.method || 'Migração do Render'),
    };
  });
const csvLines = readZip('files/data/config.csv').trim().split(/\r?\n/).slice(1);
const config = csvLines
  .map((line) => line.split(','))
  .filter(([parametro]) => parametro)
  .map(([parametro, valor]) => ({ parametro, valor: String(valor ?? '') }));
const taxpayerRows = table('taxpayer_profile');
const backup = {
  format: 'faculdademaria-cloudflare-backup',
  version: 1,
  exported_at: new Date().toISOString(),
  data: {
    operations: open,
    config,
    closed,
    cash: asPayload(table('cash_ledger'), 'event_id').map((row) => ({ ...row, id: row.event_id })),
    notes: asPayload(table('brokerage_notes'), 'note_key').map((row) => ({ ...row, key: row.note_key })),
    darfs: asPayload(table('paid_darfs'), 'darf_id').map((row) => ({ ...row, id: row.darf_id })),
    equities: asPayload(table('equity_lots'), 'lot_id'),
    taxpayer: taxpayerRows[0]?.payload || {},
    operation_preferences: table('operation_preferences'),
    manual_option_quotes: table('manual_option_quotes'),
    api_market_quotes: table('api_market_quotes'),
    operation_closure_metadata: table('operation_closure_metadata').map((row) => ({
      ...(row.payload || {}), operation_id: row.operation_id, updated_at: row.updated_at,
    })),
  },
};
fs.writeFileSync(path.resolve(output), JSON.stringify(backup, null, 2));
const counts = Object.fromEntries(Object.entries(backup.data).filter(([, value]) => Array.isArray(value)).map(([key, value]) => [key, value.length]));
console.log(JSON.stringify(counts, null, 2));
