import json
from bot.client import place_futures_order
from bot.logging_config import logger

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
    return {
        "orderId": response.get("orderId") or response.get("algoId"),
        "status": response.get("status") or response.get("algoStatus"),
        "executedQty": response.get("executedQty", "0"),
        "avgPrice": response.get("avgPrice")
    }
