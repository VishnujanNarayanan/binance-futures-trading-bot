import os
import sys
from dotenv import load_dotenv
from binance.client import Client

try:
    import questionary
except ImportError:
    pass

# Load environment variables from .env
load_dotenv()

def get_binance_client():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if not api_key or not api_secret:
        # Fallback to interactive prompts if no .env is found and we are in a terminal
        if 'questionary' in sys.modules and sys.stdin.isatty():
            print("\n[API Credentials Required]")
            print("No .env file detected. Please provide your Binance Futures Testnet credentials.")
            api_key = questionary.password("Enter your API Key:").ask()
            if not api_key: sys.exit(0)
            api_secret = questionary.password("Enter your API Secret:").ask()
            if not api_secret: sys.exit(0)
        else:
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
