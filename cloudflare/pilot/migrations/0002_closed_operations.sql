-- Registros fechados permanecem como payload JSON para preservar o formato
-- histórico enquanto as telas são migradas gradualmente para D1.

CREATE TABLE IF NOT EXISTS closed_operations (
  closed_id TEXT PRIMARY KEY,
  payload TEXT NOT NULL,
  closed_at TEXT,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_closed_operations_closed_at
  ON closed_operations(closed_at);
