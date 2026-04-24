import logging
import json
import os
from datetime import datetime
from rich.logging import RichHandler
from rich.table import Table
from rich.console import Console

def setup_logger(name: str) -> logging.Logger:
    """Set up a structured logger with Rich handler and file output."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler with Rich
    console_handler = RichHandler(show_path=False)
    console_handler.setLevel(logging.INFO)
    
    # File handler
    os.makedirs('logs', exist_ok=True)
    file_handler = logging.FileHandler('logs/app.log')
    file_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def log_prediction(data: dict) -> None:
    """Append prediction data as JSON line to logs/predictions.jsonl."""
    try:
        # Add timestamp if not present
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Append JSON line
        with open('logs/predictions.jsonl', 'a') as f:
            f.write(json.dumps(data) + '\n')
    except Exception as e:
        # Log error but don't crash
        logging.error(f"Failed to write prediction to log: {e}")

def load_prediction_log(last_n: int = 50) -> list[dict]:
    """Load the last N prediction entries from logs/predictions.jsonl."""
    try:
        if not os.path.exists('logs/predictions.jsonl'):
            return []
        
        with open('logs/predictions.jsonl', 'r') as f:
            lines = f.readlines()
        
        # Get last N lines and parse JSON
        entries = []
        for line in lines[-last_n:]:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue  # Skip malformed lines
        
        return entries
    except Exception as e:
        logging.error(f"Failed to load prediction log: {e}")
        return []

def print_cycle_summary(cycles: list[dict]) -> None:
    """
    Print a rich table summary of cycle results.
    
    Args:
        cycles: List of cycle dictionaries
    """
    console = Console()
    
    table = Table(title="CrowdWisdom Trading Agent - Cycle Summary")
    
    table.add_column("Asset", style="cyan", no_wrap=True)
    table.add_column("Direction", style="magenta")
    table.add_column("Confidence", style="green")
    table.add_column("Signal", style="yellow")
    table.add_column("Kelly Bet", style="blue")
    table.add_column("Recommendation", style="red")
    table.add_column("Arb", style="white")
    
    for cycle in cycles:
        # Extract data with defaults
        asset = cycle.get("asset", "UNKNOWN")
        direction = cycle.get("direction", "N/A")
        confidence = f"{cycle.get('confidence', 0):.1%}"
        
        # Get signal strength from kronos prediction if available
        kronos_pred = cycle.get("kronos_prediction", {})
        signal_strength = kronos_pred.get("signal_strength", "WEAK")
        
        kelly_bet = f"${cycle.get('kelly_bet', 0):.2f}"
        recommendation = cycle.get("recommendation", "HOLD")
        arb = "YES" if cycle.get("arb", False) else "no"
        
        # Color code direction
        if direction == "UP":
            direction_colored = f"[green]{direction}[/green]"
        elif direction == "DOWN":
            direction_colored = f"[red]{direction}[/red]"
        else:
            direction_colored = direction
        
        # Color code recommendation
        rec_colors = {
            "STRONG_BUY": "bold green",
            "BUY": "green",
            "HOLD": "yellow",
            "SELL": "red",
            "STRONG_SELL": "bold red"
        }
        rec_color = rec_colors.get(recommendation, "white")
        recommendation_colored = f"[{rec_color}]{recommendation}[/{rec_color}]"
        
        table.add_row(
            asset,
            direction_colored,
            confidence,
            signal_strength,
            kelly_bet,
            recommendation_colored,
            arb
        )
    
    console.print(table)