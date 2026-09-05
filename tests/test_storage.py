import sqlite3

import pytest

from bot import storage


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = str(tmp_path / "test.db")
    monkeypatch.setenv("TRADING_BOT_DB", path)
    return path


MARKET = {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01}
FILLED = {"orderId": 13096054981, "status": "FILLED", "executedQty": "0.01", "avgPrice": "84000.0"}


def test_schema_is_applied_on_connect(db):
    with storage.get_connection() as connection:
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        views = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='view'")}

    assert "orders" in tables
    assert "symbol_activity" in views


def test_connecting_twice_does_not_fail(db):
    storage.get_connection().close()
    storage.get_connection().close()  # schema statements must be idempotent


def test_record_order_stores_request_and_response(db):
    row_id = storage.record_order(MARKET, response=FILLED)
    assert row_id is not None

    row = storage.fetch_history()[0]
    assert row["symbol"] == "BTCUSDT"
    assert row["side"] == "BUY"
    assert row["order_type"] == "MARKET"
    assert row["quantity"] == 0.01
    assert row["exchange_order_id"] == "13096054981"
    assert row["status"] == "FILLED"
    assert row["executed_qty"] == 0.01
    assert row["avg_price"] == 84000.0
    assert row["error"] is None


def test_a_rejected_order_is_still_recorded(db):
    storage.record_order(MARKET, error="APIError(code=-4002): Price greater than max price.")

    row = storage.fetch_history()[0]
    assert row["error"].startswith("APIError")
    assert row["exchange_order_id"] is None
    assert row["status"] is None


def test_stop_limit_is_stored_under_the_bots_own_name(db):
    # Binance receives type STOP; the schema's CHECK constraint only accepts the
    # bot's three names, so the wire value has to be mapped back.
    storage.record_order(
        {"symbol": "BTCUSDT", "side": "BUY", "type": "STOP", "quantity": 0.01,
         "price": 86000.0, "stopPrice": 85000.0},
        response=FILLED,
    )

    row = storage.fetch_history()[0]
    assert row["order_type"] == "STOP_LIMIT"
    assert row["stop_price"] == 85000.0


def test_reduce_only_close_is_flagged(db):
    storage.record_order(
        {"symbol": "BTCUSDT", "side": "SELL", "type": "MARKET", "quantity": 0.01, "reduceOnly": "true"},
        response=FILLED,
    )
    assert storage.fetch_history()[0]["reduce_only"] == 1


def test_history_filters_by_symbol_and_respects_the_limit(db):
    for symbol in ("BTCUSDT", "ETHUSDT", "BTCUSDT"):
        storage.record_order({**MARKET, "symbol": symbol}, response=FILLED)

    assert len(storage.fetch_history()) == 3
    assert len(storage.fetch_history(symbol="BTCUSDT")) == 2
    assert len(storage.fetch_history(limit=1)) == 1
    assert {r["symbol"] for r in storage.fetch_history(symbol="ETHUSDT")} == {"ETHUSDT"}


def test_symbol_activity_view_aggregates_per_symbol(db):
    storage.record_order({**MARKET, "side": "BUY", "quantity": 2}, response=FILLED)
    storage.record_order({**MARKET, "side": "SELL", "quantity": 3}, response=FILLED)
    storage.record_order({**MARKET, "side": "BUY", "quantity": 1}, error="rejected")
    storage.record_order({**MARKET, "symbol": "ETHUSDT"}, response=FILLED)

    activity = {row["symbol"]: row for row in storage.fetch_symbol_activity()}

    btc = activity["BTCUSDT"]
    assert btc["orders_placed"] == 3
    assert btc["accepted"] == 2
    assert btc["rejected"] == 1
    assert btc["bought"] == 3      # 2 accepted + 1 rejected, both were BUY
    assert btc["sold"] == 3
    assert activity["ETHUSDT"]["orders_placed"] == 1


def test_schema_rejects_a_nonsense_side(db):
    with storage.get_connection() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO orders (symbol, side, order_type, quantity) VALUES ('BTCUSDT', 'HOLD', 'MARKET', 1)"
        )


def test_schema_rejects_a_non_positive_quantity(db):
    with storage.get_connection() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO orders (symbol, side, order_type, quantity) VALUES ('BTCUSDT', 'BUY', 'MARKET', 0)"
        )


def test_a_storage_failure_never_raises_at_the_caller(monkeypatch):
    # Bookkeeping must not be able to break order placement.
    monkeypatch.setattr(storage, "get_connection", lambda *a, **k: (_ for _ in ()).throw(sqlite3.OperationalError("disk full")))

    assert storage.record_order(MARKET, response=FILLED) is None
