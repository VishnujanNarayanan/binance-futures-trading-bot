# Binance Futures Testnet Trading Bot

A minimal, production-quality Python trading bot for the Binance Futures Testnet (USDT-M).

## Setup Steps

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your `.env` file with your testnet credentials:
   ```env
   BINANCE_API_KEY=your_testnet_api_key_here
   BINANCE_API_SECRET=your_testnet_api_secret_here
   ```

## Usage Examples

Run the CLI from the `trading_bot` directory:

### Interactive Menu (New!)
To launch the interactive, prompt-based order menu, run the script without any arguments:
```bash
python cli.py
```

### Market Order
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit Order
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-Limit Order
```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.01 --price 65000 --stop_price 65500
```

## Logs
Logs for API requests and responses are saved in `trading.log` within the execution directory.
