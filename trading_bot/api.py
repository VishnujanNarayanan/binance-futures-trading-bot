"""HTTP interface to the same execution core the CLI uses.

This is a third entry point alongside the interactive menu and the argparse flags.
It deliberately reuses bot.validators and bot.orders rather than reimplementing
anything, so an order placed over HTTP is validated, logged and recorded exactly
as one placed from the terminal.

Run locally:
    uvicorn api:app --reload        # from inside trading_bot/
"""
import os
import secrets
from typing import Optional

from binance.exceptions import BinanceAPIException
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from bot.orders import (
    close_position,
    get_open_positions,
    place_limit_order,
    place_market_order,
    place_stop_limit_order,
)
from bot.storage import fetch_history, fetch_symbol_activity
from bot.validators import validate_inputs

app = FastAPI(
    title="Binance Futures Testnet Trading Bot",
    description=(
        "REST interface over the same validated execution path as the CLI.\n\n"
        "Reads are open. Anything that moves money -- placing an order, closing a "
        "position -- requires an `X-API-Key` header. Use the **Authorize** button."
    ),
    version="1.1.0",
)

# auto_error=False so a missing header reaches require_api_key and gets the same 401
# as a wrong one. Letting FastAPI raise its own 403 first would tell an attacker
# whether the header name was right.
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(provided: Optional[str] = Security(_api_key_header)):
    """Gate the endpoints that can move money.

    Read endpoints are deliberately left open so the docs stay useful to a visitor.
    """
    expected = os.getenv("TRADING_BOT_API_KEY")

    # Fail CLOSED. A deployment with no key configured refuses to trade rather than
    # silently accepting anonymous orders -- the failure mode that would matter.
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Trading is disabled: this deployment has no TRADING_BOT_API_KEY set.",
        )

    # Compared in constant time so the response time cannot be used to guess the key
    # one character at a time. Encoded because compare_digest rejects non-ASCII str.
    if not provided or not secrets.compare_digest(provided.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key.")


class OrderRequest(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    side: str = Field(..., examples=["BUY"])
    type: str = Field(..., examples=["MARKET"], description="MARKET, LIMIT or STOP_LIMIT")
    quantity: float = Field(..., gt=0, examples=[0.01])
    price: Optional[float] = None
    stop_price: Optional[float] = None


@app.get("/", include_in_schema=False)
def root():
    """Send the bare URL to the docs.

    Without this, opening the deployed hostname returns a bare 404, which is the
    first thing anyone visiting the service sees.
    """
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["meta"])
def health():
    """Liveness check. Deliberately does not touch the exchange, so it stays green
    without credentials and can be used as a container health probe."""
    return {"status": "ok"}


@app.post("/orders", tags=["orders"], dependencies=[Depends(require_api_key)])
def create_order(order: OrderRequest):
    """Validate and place an order. Requires X-API-Key.

    401 without a valid key, 422 on bad input, 502 if the exchange rejects it.
    """
    try:
        symbol, side, order_type, quantity, price, stop_price = validate_inputs(
            order.symbol, order.side, order.type, order.quantity, order.price, order.stop_price
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        if order_type == "MARKET":
            return place_market_order(symbol, side, quantity)
        if order_type == "LIMIT":
            return place_limit_order(symbol, side, quantity, price)
        return place_stop_limit_order(symbol, side, quantity, price, stop_price)
    except BinanceAPIException as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/positions", tags=["positions"])
def list_positions():
    """Open positions, straight from the exchange."""
    try:
        return get_open_positions()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/positions/{symbol}/close", tags=["positions"], dependencies=[Depends(require_api_key)])
def close(symbol: str):
    """Close one position with a reduce-only market order. Requires X-API-Key."""
    try:
        return close_position(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/orders/history", tags=["orders"])
def order_history(symbol: Optional[str] = None, limit: int = 20):
    """Locally recorded order history, newest first."""
    return fetch_history(symbol=symbol, limit=limit)


@app.get("/orders/summary", tags=["orders"])
def order_summary():
    """Per-symbol activity totals, from the symbol_activity SQL view."""
    return fetch_symbol_activity()
