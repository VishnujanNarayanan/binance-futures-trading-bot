import json
from bot.client import place_futures_order, client
from bot.logging_config import logger

def get_open_positions():
    """Fetch all open positions from Binance Futures."""
    try:
        positions = client.futures_position_information()
        # Filter only positions with non-zero quantity
        open_positions = [pos for pos in positions if float(pos.get("positionAmt", 0)) != 0]
        return open_positions
    except Exception as e:
        logger.error(f"Error fetching positions: {str(e)}\n\n")
        raise

def close_position(symbol: str):
    """Closes an open position by placing a market order in the opposite direction."""
    try:
        positions = get_open_positions()
        pos = next((p for p in positions if p["symbol"] == symbol), None)
        
        if not pos:
            raise ValueError(f"No open position found for symbol {symbol}")
            
        amt = float(pos["positionAmt"])
        side = "SELL" if amt > 0 else "BUY"
        quantity = abs(amt)
        
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": quantity,
            "reduceOnly": "true" # Ensure we only close or reduce, not open a new position
        }
        
        logger.info(f"API Request (CLOSE POSITION - {symbol}): {json.dumps(params)}")
        response = place_futures_order(**params)
        logger.info(f"API Response (CLOSE POSITION - {symbol}): {json.dumps(response)}\n\n")
        return _format_response(response)
        
    except Exception as e:
        logger.error(f"Error closing position for {symbol}: {str(e)}\n\n")
        raise

def place_market_order(symbol: str, side: str, quantity: float):
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity
    }
    
    logger.info(f"API Request (MARKET): {json.dumps(params)}")
    try:
        response = place_futures_order(**params)
        logger.info(f"API Response (MARKET): {json.dumps(response)}\n\n")
        return _format_response(response)
    except Exception as e:
        logger.error(f"API Error (MARKET): {str(e)}\n\n")
        raise

def place_limit_order(symbol: str, side: str, quantity: float, price: float):
    params = {
        "symbol": symbol,
        "side": side,
        "type": "LIMIT",
        "quantity": quantity,
        "price": price,
        "timeInForce": "GTC"
    }
    
    logger.info(f"API Request (LIMIT): {json.dumps(params)}")
    try:
        response = place_futures_order(**params)
        logger.info(f"API Response (LIMIT): {json.dumps(response)}\n\n")
        return _format_response(response)
    except Exception as e:
        logger.error(f"API Error (LIMIT): {str(e)}\n\n")
        raise

def place_stop_limit_order(symbol: str, side: str, quantity: float, price: float, stop_price: float):
    params = {
        "symbol": symbol,
        "side": side,
        "type": "STOP",
        "quantity": quantity,
        "price": price,
        "stopPrice": stop_price,
        "timeInForce": "GTC"
    }
    
    logger.info(f"API Request (STOP_LIMIT): {json.dumps(params)}")
    try:
        response = place_futures_order(**params)
        logger.info(f"API Response (STOP_LIMIT): {json.dumps(response)}\n\n")
        return _format_response(response)
    except Exception as e:
        logger.error(f"API Error (STOP_LIMIT): {str(e)}\n\n")
        raise

def _format_response(response):
    qty = response.get("executedQty", "0")
    if float(qty) == 0:
        qty = response.get("origQty") or response.get("quantity", "0")

    return {
        "orderId": response.get("orderId") or response.get("algoId"),
        "status": response.get("status") or response.get("algoStatus"),
        "executedQty": qty,
        "avgPrice": response.get("avgPrice")
    }
