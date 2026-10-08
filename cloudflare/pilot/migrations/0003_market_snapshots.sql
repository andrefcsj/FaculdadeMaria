-- Additive cache migration; operational tables and financial records stay intact.
CREATE TABLE IF NOT EXISTS market_snapshots (
  snapshot_kind TEXT NOT NULL,
  symbol TEXT NOT NULL,
  payload TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (snapshot_kind, symbol)
);
