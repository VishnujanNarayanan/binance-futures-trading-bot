import pytest

fastapi_testclient = pytest.importorskip(
    "fastapi.testclient", reason="REST interface deps not installed (requirements-api.txt)"
)

from api import app  # noqa: E402  -- imported after the skip guard

client = fastapi_testclient.TestClient(app)

API_KEY = "test-key-not-a-real-secret"
AUTH = {"X-API-Key": API_KEY}


@pytest.fixture(autouse=True)
def configured_api_key(monkeypatch):
    """Every test runs against a deployment that HAS a key configured.

    Tests covering the unconfigured case delete it themselves.
    """
    monkeypatch.setenv("TRADING_BOT_API_KEY", API_KEY)


def test_health_needs_no_credentials_and_no_exchange():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_placing_a_market_order_returns_the_formatted_response(fake_client):
    fake_client(order_response={
        "orderId": 42, "status": "FILLED", "executedQty": "0.01", "avgPrice": "84000.0",
    })

    response = client.post("/orders", headers=AUTH, json={
        "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01,
    })

    assert response.status_code == 200
    assert response.json()["orderId"] == 42


def test_the_api_uses_the_same_validator_as_the_cli(fake_client):
    stub = fake_client()

    # A LIMIT order with no price is rejected locally by validate_inputs, so the
    # request must never reach the exchange.
    response = client.post("/orders", headers=AUTH, json={
        "symbol": "BTCUSDT", "side": "SELL", "type": "LIMIT", "quantity": 0.01,
    })

    assert response.status_code == 422
    assert "Price is required" in response.json()["detail"]
    assert stub.calls == []


def test_a_lowercase_symbol_is_rejected_the_same_way_as_on_the_cli(fake_client):
    fake_client()
    response = client.post("/orders", headers=AUTH, json={
        "symbol": "btcusdt", "side": "BUY", "type": "MARKET", "quantity": 0.01,
    })
    assert response.status_code == 422
    assert "uppercase" in response.json()["detail"]


def test_a_non_positive_quantity_is_rejected_by_the_request_model(fake_client):
    fake_client()
    response = client.post("/orders", headers=AUTH, json={
        "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0,
    })
    # Caught by the Pydantic model's gt=0 before the handler runs.
    assert response.status_code == 422


def test_an_exchange_rejection_surfaces_as_502(fake_client):
    fake_client(raises=RuntimeError("APIError(code=-4002): Price greater than max price."))

    response = client.post("/orders", headers=AUTH, json={
        "symbol": "BTCUSDT", "side": "SELL", "type": "LIMIT", "quantity": 0.01, "price": 999999.0,
    })

    assert response.status_code == 502
    assert "code=-4002" in response.json()["detail"]


def test_positions_are_listed(fake_client):
    fake_client(positions=[
        {"symbol": "BTCUSDT", "positionAmt": "0.01"},
        {"symbol": "ETHUSDT", "positionAmt": "0"},
    ])

    response = client.get("/positions")

    assert response.status_code == 200
    assert [p["symbol"] for p in response.json()] == ["BTCUSDT"]


def test_closing_a_position_sends_a_reduce_only_order(fake_client):
    stub = fake_client(positions=[{"symbol": "BTCUSDT", "positionAmt": "0.01"}])

    response = client.post("/positions/BTCUSDT/close", headers=AUTH)

    assert response.status_code == 200
    assert stub.calls[0]["reduceOnly"] == "true"
    assert stub.calls[0]["side"] == "SELL"


def test_closing_a_symbol_with_no_position_is_a_404(fake_client):
    fake_client(positions=[])
    response = client.post("/positions/ETHUSDT/close", headers=AUTH)
    assert response.status_code == 404


def test_history_and_summary_read_back_what_was_placed(fake_client):
    fake_client(order_response={
        "orderId": 7, "status": "FILLED", "executedQty": "0.01", "avgPrice": "84000.0",
    })
    client.post("/orders", headers=AUTH, json={
        "symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01,
    })

    history = client.get("/orders/history").json()
    assert len(history) == 1
    assert history[0]["exchange_order_id"] == "7"

    summary = client.get("/orders/summary").json()
    assert summary[0]["symbol"] == "BTCUSDT"
    assert summary[0]["orders_placed"] == 1


def test_history_can_be_filtered_by_symbol(fake_client):
    fake_client()
    for symbol in ("BTCUSDT", "ETHUSDT"):
        client.post("/orders", headers=AUTH, json={
            "symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": 0.01,
        })

    filtered = client.get("/orders/history", params={"symbol": "ETHUSDT"}).json()
    assert [row["symbol"] for row in filtered] == ["ETHUSDT"]


def test_the_bare_url_redirects_to_the_docs():
    # The deployed hostname is what gets shared, and FastAPI has no root route by
    # default -- so without this the first thing a visitor sees is a 404.
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


# --- authentication -----------------------------------------------------------
# Reads stay open so the docs remain useful to a visitor. Anything that can move
# money requires X-API-Key.

ORDER = {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.01}


def test_placing_an_order_without_a_key_is_rejected(fake_client):
    stub = fake_client()

    response = client.post("/orders", json=ORDER)

    assert response.status_code == 401
    assert stub.calls == [], "an unauthenticated request must never reach the exchange"


def test_placing_an_order_with_the_wrong_key_is_rejected(fake_client):
    stub = fake_client()

    response = client.post("/orders", headers={"X-API-Key": "wrong"}, json=ORDER)

    assert response.status_code == 401
    assert stub.calls == []


def test_closing_a_position_without_a_key_is_rejected(fake_client):
    stub = fake_client(positions=[{"symbol": "BTCUSDT", "positionAmt": "0.01"}])

    response = client.post("/positions/BTCUSDT/close")

    assert response.status_code == 401
    assert stub.calls == []


def test_auth_runs_before_body_validation(fake_client):
    # An unauthenticated caller must not be able to probe the request schema by
    # watching which malformed bodies come back 422 instead of 401.
    fake_client()

    response = client.post("/orders", json={"symbol": "BTCUSDT"})  # missing required fields

    assert response.status_code == 401


def test_the_error_never_echoes_the_expected_key(fake_client):
    fake_client()
    response = client.post("/orders", headers={"X-API-Key": "wrong"}, json=ORDER)
    assert API_KEY not in response.text


def test_trading_is_disabled_when_no_key_is_configured(fake_client, monkeypatch):
    # Fail closed: a deployment that forgot to set the key must refuse to trade
    # rather than quietly accept anonymous orders.
    monkeypatch.delenv("TRADING_BOT_API_KEY", raising=False)
    stub = fake_client()

    response = client.post("/orders", headers=AUTH, json=ORDER)

    assert response.status_code == 503
    assert stub.calls == []


@pytest.mark.parametrize("path", ["/health", "/orders/history", "/orders/summary", "/positions"])
def test_read_endpoints_stay_open(path, fake_client):
    fake_client(positions=[])
    assert client.get(path).status_code == 200


def test_the_docs_advertise_the_api_key_scheme():
    # So the Swagger UI renders an Authorize button rather than leaving a visitor
    # guessing why every write returns 401.
    schema = client.get("/openapi.json").json()
    assert "APIKeyHeader" in schema["components"]["securitySchemes"]
    assert schema["components"]["securitySchemes"]["APIKeyHeader"]["name"] == "X-API-Key"
