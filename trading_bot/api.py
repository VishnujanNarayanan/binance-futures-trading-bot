"""HTTP interface to the same execution core the CLI uses.

This is a third entry point alongside the interactive menu and the argparse flags.
It deliberately reuses bot.validators and bot.orders rather than reimplementing
anything, so an order placed over HTTP is validated, logged and recorded exactly
as one placed from the terminal.

Run locally:
    uvicorn api:app --reload        # from inside trading_bot/
"""
from typing import Optional

from binance.exceptions import BinanceAPIException
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
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
    description="REST interface over the same validated execution path as the CLI.",
    version="1.0.0",
)


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


@app.post("/orders", tags=["orders"])
def create_order(order: OrderRequest):
    """Validate and place an order. 422 on bad input, 502 if the exchange rejects it."""
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


@app.post("/positions/{symbol}/close", tags=["positions"])
def close(symbol: str):
    """Close one position with a reduce-only market order."""
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
