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
