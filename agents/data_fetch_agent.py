import logging
import time
from tools.apify_tool import fetch_ohlcv_bars, validate_bars
from utils.logger import setup_logger

logger = setup_logger("DataFetchAgent")

class DataFetchAgent:
    """Data fetch agent - retrieves OHLCV data for crypto assets."""
    
    def __init__(self):
        self.fetch_tool = fetch_ohlcv_bars
        self.validate_tool = validate_bars
    
    def fetch(self, asset: str, bars: int = 1000):
        """Fetch OHLCV bars for an asset."""
        try:
            result = self.fetch_tool(asset, limit=bars)
            is_valid = self.validate_tool(result)
            
            if not is_valid:
                logger.warning(f"Initial fetch produced invalid data for {asset}, retrying...")
                time.sleep(3)
                result = self.fetch_tool(asset, limit=bars)
                is_valid = self.validate_tool(result)
                if not is_valid:
                    logger.warning(f"Retry also failed for {asset}")
            
            logger.info(f"DataFetchAgent: Fetched {len(result)} bars for {asset}")
            return result
        except Exception as e:
            logger.error(f"Error in DataFetchAgent.fetch: {e}")
            return []
    
    def analyze_quality(self, bars, asset: str):
        """Analyze the quality of OHLCV bar data."""
        if not bars or len(bars) < 20:
            return {
                "quality_score": 0,
                "has_gaps": True,
                "is_sufficient": False,
                "last_price": 0.0,
                "price_range_24h": {"high": 0.0, "low": 0.0},
                "notes": "Insufficient data"
            }
        
        last_price = bars[-1].get("close", 0) if bars else 0
        high_prices = [b.get("high", 0) for b in bars if isinstance(b.get("high"), (int, float))]
        low_prices = [b.get("low", 0) for b in bars if isinstance(b.get("low"), (int, float))]
        
        return {
            "quality_score": 50 if len(bars) >= 100 else 30,
            "has_gaps": len(bars) < 100,
            "is_sufficient": len(bars) >= 100,
            "last_price": last_price,
            "price_range_24h": {
                "high": max(high_prices) if high_prices else 0.0,
                "low": min(low_prices) if low_prices else 0.0
            },
            "notes": "Analysis complete"
        }