import json
import logging
from typing import Dict, Any

from tools.polymarket_tool import get_crypto_markets as poly_markets
from tools.kalshi_tool import get_crypto_markets as kalshi_markets
from utils.logger import setup_logger

logger = setup_logger("MarketSearchAgent")

class MarketSearchAgent:
    """Market search agent - analyzes prediction markets for crypto assets."""
    
    def __init__(self):
        self.polymarket_tool = poly_markets
        self.kalshi_tool = kalshi_markets
    
    def search(self, asset: str) -> Dict[str, Any]:
        """Search for prediction markets on Polymarket and Kalshi."""
        try:
            poly_data = self.polymarket_tool(asset)
            kalshi_data = self.kalshi_tool(asset)
            
            logger.info(f"MarketSearchAgent: Found {len(poly_data)} Polymarket and {len(kalshi_data)} Kalshi markets for {asset}")
            
            # Select best markets
            poly_best = poly_data[0] if poly_data else {}
            kalshi_best = kalshi_data[0] if kalshi_data else {}
            
            # Calculate average yes price
            prices = []
            if poly_best.get("yes_price"):
                prices.append(poly_best["yes_price"])
            if kalshi_best.get("yes_price"):
                prices.append(kalshi_best["yes_price"])
            avg_price = sum(prices) / len(prices) if prices else 0.5
            
            # Determine sentiment
            if avg_price > 0.55:
                sentiment = "BULLISH"
            elif avg_price < 0.45:
                sentiment = "BEARISH"
            else:
                sentiment = "NEUTRAL"
            
            return {
                "polymarket_best": {
                    "market_id": poly_best.get("market_id"),
                    "yes_price": poly_best.get("yes_price", 0.5),
                    "no_price": poly_best.get("no_price", 0.5),
                    "volume": poly_best.get("volume", 0),
                    "implied_probability": poly_best.get("yes_price", 0.5)
                },
                "kalshi_best": {
                    "market_id": kalshi_best.get("market_id"),
                    "yes_price": kalshi_best.get("yes_price", 0.5),
                    "no_price": kalshi_best.get("no_price", 0.5),
                    "volume": kalshi_best.get("volume", 0),
                    "implied_probability": kalshi_best.get("yes_price", 0.5)
                },
                "market_sentiment": sentiment,
                "average_yes_price": avg_price
            }
        except Exception as e:
            logger.error(f"Error in MarketSearchAgent.search: {e}")
            return {
                "polymarket_best": {},
                "kalshi_best": {},
                "market_sentiment": "NEUTRAL",
                "average_yes_price": 0.5
            }