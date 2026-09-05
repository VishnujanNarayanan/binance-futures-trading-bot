"""Local order history, stored in SQLite.

The exchange is the source of truth for live state; this is a local record of what
this bot asked for and what came back, so a trader can answer "what did I send, and
what happened to it" without reading the log file.

Recording is deliberately best-effort: a storage failure must never turn a
successfully placed order into an exception on the caller's side.
"""
import os
import sqlite3
from pathlib import Path

from bot.logging_config import logger

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_DB_PATH = "trading_bot.db"


def get_db_path():
    return os.getenv("TRADING_BOT_DB", DEFAULT_DB_PATH)


def get_connection(db_path=None):
    """Open a connection with the schema applied and rows returned as mappings."""
    path = db_path or get_db_path()
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.executescript(SCHEMA_PATH.read_text())
    return connection


def record_order(params, response=None, error=None, db_path=None):
    """Write one attempted order. Returns the new row id, or None if storage failed.

    `params` is the payload sent to Binance, so this works for plain orders and for
    reduce-only closes alike. `response` is the formatted response; `error` is the
    exchange or validation message when the order did not go through.
    """
    try:
        with get_connection(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO orders (
                    symbol, side, order_type, quantity, price, stop_price, reduce_only,
                    exchange_order_id, status, executed_qty, avg_price, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    params.get("symbol"),
                    params.get("side"),
                    _order_type_of(params),
                    params.get("quantity"),
                    params.get("price"),
                    params.get("stopPrice"),
                    1 if params.get("reduceOnly") else 0,
                    str(response.get("orderId")) if response and response.get("orderId") is not None else None,
                    response.get("status") if response else None,
                    _as_float(response.get("executedQty")) if response else None,
                    _as_float(response.get("avgPrice")) if response else None,
                    error,
                ),
            )
            return cursor.lastrowid
    except Exception as exc:
        # Never let bookkeeping break order placement.
        logger.error(f"Failed to record order in history: {exc!s}\n\n")
        return None


def fetch_history(symbol=None, limit=20, db_path=None):
    """Most recent orders first, optionally filtered to one symbol."""
    query = """
        SELECT created_at, symbol, side, order_type, quantity, price, stop_price,
               reduce_only, exchange_order_id, status, executed_qty, avg_price, error
        FROM orders
    """
    parameters = []
    if symbol:
        query += " WHERE symbol = ?"
        parameters.append(symbol)
    query += " ORDER BY created_at DESC, id DESC LIMIT ?"
    parameters.append(limit)

    with get_connection(db_path) as connection:
        return [dict(row) for row in connection.execute(query, parameters)]


def fetch_symbol_activity(db_path=None):
    """Per-symbol totals, read from the symbol_activity view."""
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT * FROM symbol_activity ORDER BY last_order_at DESC"
        )
        return [dict(row) for row in rows]


def _order_type_of(params):
    """Map Binance's wire type back to the bot's own vocabulary.

    A STOP_LIMIT is submitted as type STOP with a stopPrice, so the wire value alone
    cannot be stored -- the schema's CHECK constraint only accepts the bot's three.
    """
    wire_type = params.get("type")
    if wire_type == "STOP":
        return "STOP_LIMIT"
    return wire_type


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
