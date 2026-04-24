import requests
import logging
import os
import time
from typing import List, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)

def fetch_ohlcv_bars(asset: str, interval: str = "5m", limit: int = 1000) -> List[Dict[str, Any]]:
    """Fetch OHLCV bars for a cryptocurrency asset."""
    try:
        symbol = f"{asset}USDT"
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        klines = response.json()
        
        bars = []
        for kline in klines:
            bar = {
                "timestamp": int(kline[0]),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5])
            }
            bars.append(bar)
        
        logger.info(f"Fetched {len(bars)} bars for {asset} from Binance")
        
        if len(bars) >= 100:
            return bars
        else:
            logger.warning(f"Binance returned only {len(bars)} bars")
            return bars
    
    except Exception as e:
        logger.error(f"Binance API failed: {e}")
        return []

def validate_bars(bars: List[Dict[str, Any]]) -> bool:
    """Validate OHLCV bars data."""
    if not bars or len(bars) < 100:
        logger.warning(f"Invalid bars: insufficient data ({len(bars) if bars else 0} bars)")
        return False
    
    required_keys = {"timestamp", "open", "high", "low", "close", "volume"}
    
    for i, bar in enumerate(bars):
        if not all(key in bar for key in required_keys):
            logger.warning(f"Invalid bar at index {i}: missing required keys")
            return False
        
        try:
            ts = bar["timestamp"]
            open_price = bar["open"]
            high_price = bar["high"]
            low_price = bar["low"]
            close_price = bar["close"]
            volume = bar["volume"]
            
            if not isinstance(ts, (int, float)) or ts <= 0:
                return False
            if not all(isinstance(x, (int, float)) and x >= 0 for x in [open_price, high_price, low_price, close_price, volume]):
                return False
            if high_price < low_price:
                return False
            if not (low_price <= open_price <= high_price):
                return False
            if not (low_price <= close_price <= high_price):
                return False
        except (ValueError, TypeError):
            return False
    
    return True