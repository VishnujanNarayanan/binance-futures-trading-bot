import argparse
import sys
from binance.exceptions import BinanceAPIException
from bot.validators import validate_inputs
from bot.orders import (
    place_market_order, 
    place_limit_order, 
    place_stop_limit_order, 
    get_open_positions, 
    close_position
)
from bot.logging_config import logger

try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
except ImportError:
    print("Dependencies for enhanced CLI missing. Please run: pip install -r requirements.txt")
    sys.exit(1)

def display_positions():
    """Fetches and displays open positions in a table."""
    with console.status("[bold green]Fetching open positions...") as status:
        positions = get_open_positions()
    
    if not positions:
        console.print("[yellow]No open positions found.[/yellow]")
        return
    
    table = Table(title="Open Futures Positions")
    table.add_column("Symbol", style="cyan")
    table.add_column("Side", style="bold")
    table.add_column("Amount", justify="right")
    table.add_column("Entry Price", justify="right")
    table.add_column("Mark Price", justify="right")
    table.add_column("Unrealized PNL", justify="right")
    
    for pos in positions:
        amt = float(pos["positionAmt"])
        side = "[green]LONG[/green]" if amt > 0 else "[red]SHORT[/red]"
        pnl = float(pos["unRealizedProfit"])
        pnl_str = f"[{'green' if pnl >= 0 else 'red'}]{pnl:+.2f}[/]"
        
        table.add_row(
            pos["symbol"],
            side,
            str(abs(amt)),
            f"{float(pos['entryPrice']):.2f}",
            f"{float(pos['markPrice']):.2f}",
            pnl_str
        )
    
    console.print(table)

def handle_close_position_interactive():
    """Interactive flow to close an open position."""
    with console.status("[bold green]Fetching open positions...") as status:
        positions = get_open_positions()
    
    if not positions:
        console.print("[yellow]No open positions to close.[/yellow]")
        return
    
    choices = [pos["symbol"] for pos in positions]
    symbol = questionary.select(
        "Select position to close:",
        choices=choices
    ).ask()
    
    if not symbol: return
    
    confirm = questionary.confirm(f"Are you sure you want to market close {symbol}?").ask()
    if confirm:
        try:
            with console.status(f"[bold red]Closing position {symbol}...") as status:
                result = close_position(symbol)
            
            res_table = Table(show_header=False, box=None)
            res_table.add_column("Property", style="cyan", justify="right")
            res_table.add_column("Value", style="green")
            res_table.add_row("Order ID", str(result.get('orderId')))
            res_table.add_row("Status", str(result.get('status')))
            
            console.print(Panel(res_table, title="Close Response", border_style="green"))
            console.print(f"[bold green]Successfully closed {symbol}[/bold green]\n")
        except Exception as e:
            console.print(f"[bold red]Error closing position:[/bold red] {str(e)}")

def get_order_inputs_interactive():
    """Prompts for order details and returns a namespace."""
    symbol = questionary.text("Enter Trading Symbol (e.g., BTCUSDT):", default="BTCUSDT").ask()
    if symbol is None: return None
    symbol = symbol.strip().upper()
    
    side = questionary.select(
        "Select Order Side:",
        choices=["BUY", "SELL"]
    ).ask()
    if side is None: return None
    
    order_type = questionary.select(
        "Select Order Type:",
        choices=["MARKET", "LIMIT", "STOP_LIMIT"]
    ).ask()
    if order_type is None: return None
    
    quantity_str = questionary.text(
        "Enter Order Quantity:",
        validate=lambda text: True if text.replace('.','',1).isdigit() and float(text) > 0 else "Please enter a positive number"
    ).ask()
    if quantity_str is None: return None
    quantity = float(quantity_str)
    
    price = None
    if order_type in ["LIMIT", "STOP_LIMIT"]:
        price_str = questionary.text(
            "Enter Limit Price:",
            validate=lambda text: True if text.replace('.','',1).isdigit() and float(text) > 0 else "Please enter a positive number"
        ).ask()
        if price_str is None: return None
        price = float(price_str)
        
    stop_price = None
    if order_type == "STOP_LIMIT":
        stop_price_str = questionary.text(
            "Enter Stop Price:",
            validate=lambda text: True if text.replace('.','',1).isdigit() and float(text) > 0 else "Please enter a positive number"
        ).ask()
        if stop_price_str is None: return None
        stop_price = float(stop_price_str)
        
    return argparse.Namespace(
        symbol=symbol,
        side=side,
        type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price
    )

def print_summary(args):
    table = Table(title="Order Summary", show_header=False, box=None)
    table.add_column("Property", style="cyan", justify="right")
    table.add_column("Value", style="yellow")
    
    table.add_row("Symbol", args.symbol.upper())
    table.add_row("Side", args.side.upper())
    table.add_row("Type", args.type.upper())
    table.add_row("Quantity", str(args.quantity))
    if args.type.upper() in ["LIMIT", "STOP_LIMIT"] and args.price:
        table.add_row("Price", str(args.price))
    if args.type.upper() == "STOP_LIMIT" and args.stop_price:
        table.add_row("Stop Price", str(args.stop_price))
        
    console.print(Panel(table, border_style="blue"))

def main():
    parser = argparse.ArgumentParser(description="Binance Futures Testnet Trading Bot")
    parser.add_argument("--action", choices=["order", "positions", "close"], default="order", help="Action to perform (default: order)")
    parser.add_argument("--symbol", help="Trading symbol (e.g., BTCUSDT)")
    parser.add_argument("--side", choices=["BUY", "SELL", "buy", "sell"], help="Order side (BUY/SELL)")
    parser.add_argument("--type", choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"], help="Order type (MARKET/LIMIT/STOP_LIMIT)")
    parser.add_argument("--quantity", type=float, help="Order quantity")
    parser.add_argument("--price", type=float, help="Order price (required for LIMIT/STOP_LIMIT orders)")
    parser.add_argument("--stop_price", type=float, help="Stop price (required for STOP_LIMIT orders)")
    
    # Interactive Mode
    if len(sys.argv) == 1:
        console.print(Panel("[bold cyan]Binance Futures Bot[/bold cyan]", border_style="cyan"))
        
        while True:
            choice = questionary.select(
                "Main Menu:",
                choices=[
                    "Place New Order",
                    "View Open Positions",
                    "Close a Position",
                    "Exit"
                ]
            ).ask()
            
            if choice == "Place New Order":
                args = get_order_inputs_interactive()
                if args:
                    print_summary(args)
                    confirm = questionary.confirm("Proceed with this order?").ask()
                    if confirm:
                        execute_order(args)
                    else:
                        console.print("[bold red]Order cancelled.[/bold red]")
            elif choice == "View Open Positions":
                display_positions()
            elif choice == "Close a Position":
                handle_close_position_interactive()
            else:
                console.print("[bold cyan]Goodbye![/bold cyan]")
                sys.exit(0)
    
    # Headless Mode
    else:
        args = parser.parse_args()
        
        if args.action == "positions":
            display_positions()
        elif args.action == "close":
            if not args.symbol:
                parser.error("--symbol is required for close action")
            try:
                execute_close(args.symbol)
            except Exception as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                sys.exit(1)
        else:
            # Manual check for required args if running in CLI mode for orders
            required_args = ["symbol", "side", "type", "quantity"]
            missing_args = [arg for arg in required_args if not getattr(args, arg)]
            if missing_args:
                parser.error(f"the following arguments are required: {', '.join(['--'+a for a in missing_args])}")
            
            print_summary(args)
            execute_order(args)

def execute_order(args):
    """Core logic to validate and execute an order."""
    try:
        # Validate inputs
        symbol, side, order_type, quantity, price, stop_price = validate_inputs(
            args.symbol, args.side, args.type, args.quantity, args.price, args.stop_price
        )
        
        with console.status("[bold green]Connecting to Binance Testnet & Placing order...") as status:
            # Place order
            if order_type == "MARKET":
                result = place_market_order(symbol, side, quantity)
            elif order_type == "LIMIT":
                result = place_limit_order(symbol, side, quantity, price)
            elif order_type == "STOP_LIMIT":
                result = place_stop_limit_order(symbol, side, quantity, price, stop_price)
            
        res_table = Table(show_header=False, box=None)
        res_table.add_column("Property", style="cyan", justify="right")
        res_table.add_column("Value", style="green")
        
        res_table.add_row("Order ID", str(result.get('orderId')))
        res_table.add_row("Status", str(result.get('status')))
        res_table.add_row("Executed Qty", str(result.get('executedQty')))
        if result.get('avgPrice') and float(result.get('avgPrice')) > 0:
            res_table.add_row("Avg Price", str(result.get('avgPrice')))
            
        console.print(Panel(res_table, title="Response", border_style="green"))
        console.print("[bold green]FINAL STATUS: SUCCESS[/bold green]\n")

    except ValueError as ve:
        console.print(f"[bold red]Validation Error:[/bold red] {str(ve)}")
        console.print("[bold red]FINAL STATUS: FAILURE[/bold red]\n")
        logger.error(f"Validation Error: {str(ve)}\n\n")
        if len(sys.argv) > 1: sys.exit(1)
    except BinanceAPIException as bae:
        console.print(f"[bold red]Binance API Error:[/bold red] {bae.message} (Code: {bae.status_code})")
        console.print("[bold red]FINAL STATUS: FAILURE[/bold red]\n")
        if len(sys.argv) > 1: sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {str(e)}")
        console.print("[bold red]FINAL STATUS: FAILURE[/bold red]\n")
        logger.error(f"Unexpected Error: {str(e)}\n\n")
        if len(sys.argv) > 1: sys.exit(1)

def execute_close(symbol):
    """Core logic to execute a position close."""
    with console.status(f"[bold red]Closing position {symbol}...") as status:
        result = close_position(symbol)
    
    res_table = Table(show_header=False, box=None)
    res_table.add_column("Property", style="cyan", justify="right")
    res_table.add_column("Value", style="green")
    res_table.add_row("Order ID", str(result.get('orderId')))
    res_table.add_row("Status", str(result.get('status')))
    
    console.print(Panel(res_table, title="Close Response", border_style="green"))
    console.print(f"[bold green]Successfully closed {symbol}[/bold green]\n")

if __name__ == "__main__":
    main()
