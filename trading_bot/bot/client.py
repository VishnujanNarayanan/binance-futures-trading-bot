import os
from dotenv import load_dotenv
from binance.client import Client

# Load environment variables from .env
load_dotenv()

def get_binance_client():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        raise ValueError("API credentials (BINANCE_API_KEY, BINANCE_API_SECRET) not found in .env")

    # Initialize client
    client = Client(api_key, api_secret, testnet=True)
    
    # Configure Futures endpoint explicitly as requested
    client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"
    
    return client

# Create a reusable client instance
client = get_binance_client()

def place_futures_order(**kwargs):
    """Reusable method to place futures orders."""
    # Ensure it hits the futures testnet endpoint
    return client.futures_create_order(**kwargs)
