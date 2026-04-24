import requests
import logging
import os
from typing import List, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)

BASE_URL = "https://trading-api.kalshi.com/trade-api/v2"

def get_crypto_markets(asset: str) -> List[Dict[str, Any]]:
    """Get cryptocurrency prediction markets from Kalshi."""
    api_key = os.getenv("KALSHI_API_KEY")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.get(
            f"{BASE_URL}/markets",
            params={"status": "open", "limit": 100},
            headers=headers,
            timeout=10,
            verify=False
        )
        
        if response.status_code == 401:
            logger.warning("Kalshi auth not configured - returning mock data")
            return _get_mock_kalshi_data(asset)
        
        response.raise_for_status()
        data = response.json()
        markets = data.get("markets", [])
        
        asset_markets = []
        for market in markets:
            title = market.get("title", "").upper()
            ticker = market.get("ticker", "").upper()
            if asset.upper() in title or asset.upper() in ticker:
                if any(keyword in title.lower() for keyword in ["above", "below", "higher", "lower"]):
                    asset_markets.append(market)
        
        formatted_markets = []
        for market in asset_markets:
            try:
                yes_price_cents = float(market.get("yes_price", 0) or 0)
                no_price_cents = float(market.get("no_price", 0) or 0)
                yes_price = yes_price_cents / 100.0
                no_price = no_price_cents / 100.0
                
                formatted_markets.append({
                    "market_id": market.get("ticker"),
                    "title": market.get("title"),
                    "yes_price": yes_price,
                    "no_price": no_price,
                    "volume": float(market.get("volume", 0) or 0)
                })
            except (ValueError, TypeError):
                continue
        
        logger.info(f"Kalshi: Found {len(formatted_markets)} markets for {asset}")
        return formatted_markets
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Kalshi API error: {e}")
        return _get_mock_kalshi_data(asset)
    except Exception as e:
        logger.error(f"Unexpected error in Kalshi tool: {e}")
        return _get_mock_kalshi_data(asset)

def get_market_price(ticker: str) -> Dict[str, Any]:
    """Get price information for a specific Kalshi market."""
    api_key = os.getenv("KALSHI_API_KEY")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        response = requests.get(f"{BASE_URL}/markets/{ticker}", headers=headers, timeout=2)
        
        if response.status_code == 401:
            logger.warning("Kalshi auth not configured - returning mock data")
            return _get_mock_market_price(ticker)
        
        response.raise_for_status()
        market = response.json()
        
        yes_price_cents = float(market.get("yes_price", 0) or 0)
        no_price_cents = float(market.get("no_price", 0) or 0)
        
        return {
            "yes_price": yes_price_cents / 100.0,
            "no_price": no_price_cents / 100.0,
            "volume": float(market.get("volume", 0) or 0)
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Kalshi market price error for {ticker}: {e}")
        return _get_mock_market_price(ticker)
    except Exception as e:
        logger.error(f"Unexpected error getting Kalshi market price: {e}")
        return _get_mock_market_price(ticker)

def _get_mock_kalshi_data(asset: str) -> List[Dict[str, Any]]:
    """Generate mock Kalshi data for testing."""
    logger.info(f"Generating mock Kalshi data for {asset}")
    return [
        {"market_id": f"{asset}_HIGHER_24H", "title": f"Will {asset} be higher in 24 hours?", "yes_price": 0.52, "no_price": 0.48, "volume": 1000.0},
        {"market_id": f"{asset}_LOWER_7D", "title": f"Will {asset} be lower in 7 days?", "yes_price": 0.48, "no_price": 0.52, "volume": 750.0}
    ]

def _get_mock_market_price(ticker: str) -> Dict[str, Any]:
    """Generate mock market price for a specific ticker."""
    asset = "BTC"
    if "_" in ticker:
        asset = ticker.split("_")[0]
    import hashlib
    hash_val = int(hashlib.md5(ticker.encode()).hexdigest(), 16)
    yes_price = 0.4 + (hash_val % 20) / 100.0
    return {"yes_price": yes_price, "no_price": 1.0 - yes_price, "volume": 500.0}