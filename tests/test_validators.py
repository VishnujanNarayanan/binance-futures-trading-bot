import pytest

from bot.validators import validate_inputs


def test_market_order_returns_normalised_tuple():
    result = validate_inputs("BTCUSDT", "buy", "market", 0.01)
    assert result == ("BTCUSDT", "BUY", "MARKET", 0.01, None, None)


def test_side_and_type_are_upper_cased_for_the_caller():
    _, side, order_type, _, _, _ = validate_inputs("BTCUSDT", "sell", "stop_limit", 1, 10, 9)
    assert side == "SELL"
    assert order_type == "STOP_LIMIT"


@pytest.mark.parametrize("symbol", ["", "btcusdt", "BtcUsdt", None])
def test_symbol_must_be_uppercase(symbol):
    with pytest.raises(ValueError, match="uppercase"):
        validate_inputs(symbol, "BUY", "MARKET", 0.01)


def test_side_must_be_buy_or_sell():
    with pytest.raises(ValueError, match="BUY"):
        validate_inputs("BTCUSDT", "HOLD", "MARKET", 0.01)


def test_order_type_must_be_supported():
    with pytest.raises(ValueError, match="Order type"):
        validate_inputs("BTCUSDT", "BUY", "OCO", 0.01)


@pytest.mark.parametrize("quantity", [0, -1, -0.001])
def test_quantity_must_be_positive(quantity):
    with pytest.raises(ValueError, match="Quantity"):
        validate_inputs("BTCUSDT", "BUY", "MARKET", quantity)


@pytest.mark.parametrize("order_type", ["LIMIT", "STOP_LIMIT"])
@pytest.mark.parametrize("price", [None, 0, -5])
def test_price_is_required_and_positive_for_priced_orders(order_type, price):
    with pytest.raises(ValueError, match="Price is required"):
        validate_inputs("BTCUSDT", "BUY", order_type, 0.01, price, 100)


def test_market_order_needs_no_price():
    assert validate_inputs("BTCUSDT", "BUY", "MARKET", 0.01, None, None)[4] is None


@pytest.mark.parametrize("stop_price", [None, 0, -5])
def test_stop_price_is_required_and_positive_for_stop_limit(stop_price):
    with pytest.raises(ValueError, match="Stop price"):
        validate_inputs("BTCUSDT", "BUY", "STOP_LIMIT", 0.01, 100, stop_price)


def test_limit_order_needs_no_stop_price():
    assert validate_inputs("BTCUSDT", "BUY", "LIMIT", 0.01, 100, None)[5] is None
