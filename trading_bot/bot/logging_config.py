import logging
import sys

def setup_logger():
    logger = logging.getLogger("trading_bot")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler("trading.log")
        file_handler.setLevel(logging.INFO)
        
        # Formatter - Clean, compact format
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    return logger

logger = setup_logger()
