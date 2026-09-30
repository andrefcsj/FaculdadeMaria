-- Esquema vazio para homologação no D1. Nenhum dado de produção é inserido aqui.

CREATE TABLE IF NOT EXISTS operacoes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data_abertura TEXT,
  ativo TEXT,
  tipo TEXT,
  estrategia TEXT,
  status TEXT,
  contratos TEXT,
  strike TEXT,
  premio_opcao TEXT,
  custos TEXT,
  irrf TEXT,
  vencimento TEXT,
  cotacao_atual TEXT,
  resultado_realizado TEXT
);

CREATE TABLE IF NOT EXISTS config (
  parametro TEXT PRIMARY KEY,
  valor TEXT
);

CREATE TABLE IF NOT EXISTS brokerage_notes (
  note_key TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS manual_option_quotes (
  option_code TEXT PRIMARY KEY,
  price REAL NOT NULL,
  quoted_at TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cash_ledger (
  event_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  event_date TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operation_preferences (
  operation_id TEXT PRIMARY KEY,
  exercise_interest INTEGER NOT NULL DEFAULT 0,
  underlying_asset TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_market_quotes (
  quote_kind TEXT NOT NULL,
  symbol TEXT NOT NULL,
  price REAL NOT NULL,
  source TEXT NOT NULL,
  quoted_at TEXT NOT NULL,
  PRIMARY KEY (quote_kind, symbol)
);

CREATE TABLE IF NOT EXISTS operation_closure_metadata (
  operation_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS paid_darfs (
  darf_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  competence TEXT NOT NULL,
  payment_date TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS taxpayer_profile (
  profile_id INTEGER PRIMARY KEY CHECK (profile_id = 1),
  payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equity_lots (
  lot_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_operacoes_status ON operacoes(status);
CREATE INDEX IF NOT EXISTS idx_operacoes_vencimento ON operacoes(vencimento);
CREATE INDEX IF NOT EXISTS idx_cash_ledger_event_date ON cash_ledger(event_date);
CREATE INDEX IF NOT EXISTS idx_paid_darfs_competence ON paid_darfs(competence);
CREATE INDEX IF NOT EXISTS idx_brokerage_notes_imported_at ON brokerage_notes(imported_at);
