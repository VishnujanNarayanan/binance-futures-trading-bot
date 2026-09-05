-- Order history for the Binance Futures bot.
--
-- Applied on every connection with executescript(), so every statement here must
-- be idempotent -- hence IF NOT EXISTS throughout.

CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),

    -- What was requested.
    symbol              TEXT    NOT NULL,
    side                TEXT    NOT NULL CHECK (side IN ('BUY', 'SELL')),
    order_type          TEXT    NOT NULL CHECK (order_type IN ('MARKET', 'LIMIT', 'STOP_LIMIT')),
    quantity            REAL    NOT NULL CHECK (quantity > 0),
    price               REAL,
    stop_price          REAL,
    reduce_only         INTEGER NOT NULL DEFAULT 0 CHECK (reduce_only IN (0, 1)),

    -- What the exchange said. Nullable: a rejected order has a row but no id.
    exchange_order_id   TEXT,
    status              TEXT,
    executed_qty        REAL,
    avg_price           REAL,
    error               TEXT
);

-- The history view is always read newest-first and usually filtered by symbol.
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_symbol_created_at ON orders (symbol, created_at DESC);

-- Per-symbol trading activity, for the --summary command.
CREATE VIEW IF NOT EXISTS symbol_activity AS
SELECT
    symbol,
    COUNT(*)                                          AS orders_placed,
    SUM(CASE WHEN error IS NULL THEN 1 ELSE 0 END)    AS accepted,
    SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS rejected,
    SUM(CASE WHEN side = 'BUY'  THEN quantity ELSE 0 END) AS bought,
    SUM(CASE WHEN side = 'SELL' THEN quantity ELSE 0 END) AS sold,
    MAX(created_at)                                   AS last_order_at
FROM orders
GROUP BY symbol;
