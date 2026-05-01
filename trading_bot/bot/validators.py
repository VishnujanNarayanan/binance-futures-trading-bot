def validate_inputs(symbol: str, side: str, order_type: str, quantity: float, price: float = None, stop_price: float = None):
    if not symbol or not symbol.isupper():
        raise ValueError("Symbol must be an uppercase string (e.g., BTCUSDT).")
    
    side_upper = side.upper()
    if side_upper not in ["BUY", "SELL"]:
        raise ValueError("Side must be either 'BUY' or 'SELL'.")
        
    type_upper = order_type.upper()
    if type_upper not in ["MARKET", "LIMIT", "STOP_LIMIT"]:
        raise ValueError("Order type must be 'MARKET', 'LIMIT', or 'STOP_LIMIT'.")
        
    if quantity <= 0:
        raise ValueError("Quantity must be greater than 0.")
        
    if type_upper in ["LIMIT", "STOP_LIMIT"]:
        if price is None or price <= 0:
            raise ValueError(f"Price is required and must be greater than 0 for {type_upper} orders.")
            
    if type_upper == "STOP_LIMIT":
        if stop_price is None or stop_price <= 0:
            raise ValueError("Stop price is required and must be greater than 0 for STOP_LIMIT orders.")
            
    return symbol, side_upper, type_upper, quantity, price, stop_price
