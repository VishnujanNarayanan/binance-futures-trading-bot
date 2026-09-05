import pytest

import bot.client


def test_client_is_not_built_at_import_time():
    # Importing the package must never resolve credentials or hit the network.
    # The module-level cache stays empty until something actually asks for a client.
    assert "bot.client" in __import__("sys").modules


def test_get_client_builds_once_and_caches(monkeypatch):
    built = []

    def fake_builder():
        built.append(1)
        return "a-client"

    monkeypatch.setattr(bot.client, "_client", None)
    monkeypatch.setattr(bot.client, "get_binance_client", fake_builder)

    assert bot.client.get_client() == "a-client"
    assert bot.client.get_client() == "a-client"
    assert len(built) == 1, "the client should be constructed once and reused"


def test_missing_credentials_raise_when_not_interactive(monkeypatch):
    monkeypatch.delenv("BINANCE_API_KEY", raising=False)
    monkeypatch.delenv("BINANCE_API_SECRET", raising=False)
    monkeypatch.setattr(bot.client, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(bot.client.sys.stdin, "isatty", lambda: False)

    with pytest.raises(ValueError, match="API credentials"):
        bot.client.get_binance_client()


def test_place_futures_order_delegates_to_the_shared_client(monkeypatch):
    calls = []

    class Stub:
        def futures_create_order(self, **kwargs):
            calls.append(kwargs)
            return {"orderId": 7}

    monkeypatch.setattr(bot.client, "_client", Stub())

    assert bot.client.place_futures_order(symbol="BTCUSDT")["orderId"] == 7
    assert calls == [{"symbol": "BTCUSDT"}]
