import logging
import os


def setup_logger():
    logger = logging.getLogger("trading_bot")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File handler
        log_path = os.getenv("TRADING_BOT_LOG", "trading.log")
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        
        # Formatter - Clean, compact format
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    return logger

logger = setup_logger()
