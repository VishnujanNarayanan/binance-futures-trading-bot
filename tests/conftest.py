import os
import sys
import tempfile

import pytest

# The bot's modules import each other as a top-level `bot` package (cli.py is run from
# the project root, which puts trading_bot/ on sys.path). Mirror that for the tests.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trading_bot"))

# Point the logger and the history database at throwaway paths so a test run never
# touches the real trading.log or trading_bot.db in the project root.
os.environ.setdefault("TRADING_BOT_LOG", os.path.join(tempfile.gettempdir(), "trading_bot_tests.log"))
os.environ.setdefault("TRADING_BOT_DB", os.path.join(tempfile.gettempdir(), "trading_bot_tests.db"))


class FakeClient:
    """Stands in for binance.client.Client.

    Records the parameters it was called with and replays canned responses, so the
    order-building and position logic can be tested without a network call or an API key.
    """

    def __init__(self, order_response=None, positions=None, raises=None):
        self.order_response = order_response if order_response is not None else {
            "orderId": 1, "status": "NEW", "executedQty": "0", "origQty": "0.01", "avgPrice": "0",
        }
        self.positions = positions if positions is not None else []
        self.raises = raises
        self.calls = []

    def futures_create_order(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises:
            raise self.raises
        return self.order_response

    def futures_position_information(self):
        if self.raises:
            raise self.raises
        return self.positions


@pytest.fixture
def fake_client(monkeypatch):
    """Install a FakeClient behind both entry points orders.py uses."""
    import bot.client
    import bot.orders

    holder = {}

    def install(**kwargs):
        client = FakeClient(**kwargs)
        holder["client"] = client
        monkeypatch.setattr(bot.client, "_client", client)
        monkeypatch.setattr(bot.orders, "get_client", lambda: client)
        monkeypatch.setattr(
            bot.orders, "place_futures_order", lambda **kw: client.futures_create_order(**kw)
        )
        return client

    install.holder = holder
    return install


@pytest.fixture(autouse=True)
def isolated_history_db(tmp_path, monkeypatch):
    """Give every test its own empty history database.

    Without this the session-wide default path is shared, and tests that place
    orders would see each other's rows.
    """
    monkeypatch.setenv("TRADING_BOT_DB", str(tmp_path / "history.db"))
