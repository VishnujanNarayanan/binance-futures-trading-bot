import pytest

from bot.orders import (
    _format_response,
    close_position,
    get_open_positions,
    place_limit_order,
    place_market_order,
    place_stop_limit_order,
)


def test_market_order_payload_carries_no_price_or_time_in_force(fake_client):
    client = fake_client()
    place_market_order("BTCUSDT", "BUY", 0.01)

    assert client.calls == [
        {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01}
    ]


def test_limit_order_payload_sets_gtc_and_price(fake_client):
    client = fake_client()
    place_limit_order("BTCUSDT", "SELL", 0.01, 85000.0)

    assert client.calls[0] == {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "LIMIT",
        "quantity": 0.01,
        "price": 85000.0,
        "timeInForce": "GTC",
    }


def test_stop_limit_order_is_submitted_as_binance_stop_type(fake_client):
    client = fake_client()
    place_stop_limit_order("BTCUSDT", "BUY", 0.01, 86000.0, 85000.0)

    payload = client.calls[0]
    # Binance's futures API calls this STOP, not STOP_LIMIT.
    assert payload["type"] == "STOP"
    assert payload["price"] == 86000.0
    assert payload["stopPrice"] == 85000.0
    assert payload["timeInForce"] == "GTC"


def test_order_errors_propagate_to_the_caller(fake_client):
    fake_client(raises=RuntimeError("exchange rejected"))

    with pytest.raises(RuntimeError, match="exchange rejected"):
        place_market_order("BTCUSDT", "BUY", 0.01)


def test_get_open_positions_filters_out_flat_symbols(fake_client):
    fake_client(positions=[
        {"symbol": "BTCUSDT", "positionAmt": "0.010"},
        {"symbol": "ETHUSDT", "positionAmt": "0.000"},
        {"symbol": "SOLUSDT", "positionAmt": "-2.5"},
    ])

    symbols = [p["symbol"] for p in get_open_positions()]
    assert symbols == ["BTCUSDT", "SOLUSDT"]


def test_closing_a_long_sells_the_absolute_quantity_reduce_only(fake_client):
    client = fake_client(positions=[{"symbol": "BTCUSDT", "positionAmt": "0.01"}])
    close_position("BTCUSDT")

    assert client.calls[0] == {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "MARKET",
        "quantity": 0.01,
        "reduceOnly": "true",
    }


def test_closing_a_short_buys_the_absolute_quantity(fake_client):
    client = fake_client(positions=[{"symbol": "SOLUSDT", "positionAmt": "-2.5"}])
    close_position("SOLUSDT")

    payload = client.calls[0]
    assert payload["side"] == "BUY"
    assert payload["quantity"] == 2.5
    assert payload["reduceOnly"] == "true"


def test_closing_a_symbol_with_no_position_raises_and_sends_nothing(fake_client):
    client = fake_client(positions=[{"symbol": "BTCUSDT", "positionAmt": "0.01"}])

    with pytest.raises(ValueError, match="No open position"):
        close_position("ETHUSDT")
    assert client.calls == []


def test_format_response_reads_a_standard_order():
    result = _format_response({
        "orderId": 13096054981,
        "status": "FILLED",
        "executedQty": "0.01",
        "avgPrice": "84000.0",
    })

    assert result == {
        "orderId": 13096054981,
        "status": "FILLED",
        "executedQty": "0.01",
        "avgPrice": "84000.0",
    }


def test_format_response_falls_back_to_conditional_algo_fields():
    # A STOP_LIMIT comes back as a conditional algo order: algoId/algoStatus, no orderId.
    result = _format_response({
        "algoId": 1000000062876129,
        "algoType": "CONDITIONAL",
        "algoStatus": "NEW",
        "origQty": "0.01",
    })

    assert result["orderId"] == 1000000062876129
    assert result["status"] == "NEW"


def test_format_response_falls_back_to_orig_qty_when_nothing_filled():
    result = _format_response({"orderId": 1, "status": "NEW", "executedQty": "0", "origQty": "0.05"})
    assert result["executedQty"] == "0.05"


# --- history recording -------------------------------------------------------
# Placing an order also writes a local record. These assert the wiring; the
# storage layer itself is covered in test_storage.py.

def test_a_placed_order_is_recorded_in_history(fake_client):
    fake_client(order_response={
        "orderId": 42, "status": "FILLED", "executedQty": "0.01", "avgPrice": "84000.0",
    })
    place_market_order("BTCUSDT", "BUY", 0.01)

    from bot.storage import fetch_history
    rows = fetch_history()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[0]["exchange_order_id"] == "42"
    assert rows[0]["error"] is None


def test_a_rejected_order_is_recorded_with_its_error(fake_client):
    fake_client(raises=RuntimeError("APIError(code=-4002): Price greater than max price."))

    with pytest.raises(RuntimeError):
        place_limit_order("BTCUSDT", "SELL", 0.01, 999999.0)

    from bot.storage import fetch_history
    rows = fetch_history()
    assert len(rows) == 1
    assert rows[0]["status"] is None
    assert "code=-4002" in rows[0]["error"]


def test_closing_a_position_is_recorded_as_reduce_only(fake_client):
    fake_client(positions=[{"symbol": "BTCUSDT", "positionAmt": "0.01"}])
    close_position("BTCUSDT")

    from bot.storage import fetch_history
    row = fetch_history()[0]
    assert row["reduce_only"] == 1
    assert row["side"] == "SELL"


def test_an_unwritable_history_database_does_not_break_the_order(fake_client, monkeypatch):
    # Bookkeeping is best-effort. If the history database cannot be opened at all,
    # the order still went to the exchange, so the caller must still get its result
    # rather than an exception about SQLite.
    monkeypatch.setenv("TRADING_BOT_DB", "/nonexistent-directory/history.db")
    fake_client(order_response={
        "orderId": 99, "status": "NEW", "executedQty": "0", "origQty": "0.01", "avgPrice": "0",
    })

    result = place_market_order("BTCUSDT", "BUY", 0.01)

    assert result["orderId"] == 99
