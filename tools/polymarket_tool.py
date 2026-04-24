import requests
import logging
import os
from typing import List, Dict, Any
from utils.logger import setup_logger
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = setup_logger(__name__)

BASE_URLS = [
    "https://gamma-api.polymarket.com",
    "https://clob.polymarket.com",
]

def get_crypto_markets(asset: str, min_volume: float = 1000.0) -> List[Dict[str, Any]]:
    """Get cryptocurrency prediction markets from Polymarket."""
    last_error = None
    
    for base_url in BASE_URLS:
        try:
            response = requests.get(
                f"{base_url}/markets",
                params={"active": "true", "tag": "crypto", "limit": 50},
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            markets = response.json()
            
            asset_markets = []
            for market in markets:
                question = market.get("question", "").upper()
                if asset.upper() in question:
                    if any(indicator in question.lower() for indicator in ["5 min", "5-min", "next 5"]):
                        asset_markets.append(market)
            
            if not asset_markets:
                asset_markets = [m for m in markets if asset.upper() in m.get("question", "").upper()]
            
            formatted_markets = []
            for market in asset_markets:
                try:
                    volume = float(market.get("volume", 0) or 0)
                    if volume >= min_volume:
                        formatted_markets.append({
                            "market_id": market.get("id"),
                            "question": market.get("question"),
                            "yes_price": float(market.get("yes_price", 0) or 0),
                            "no_price": float(market.get("no_price", 0) or 0),
                            "volume": volume,
                            "end_date": market.get("endDate")
                        })
                except (ValueError, TypeError):
                    continue
            
            logger.info(f"Polymarket: Found {len(formatted_markets)} markets for {asset}")
            return formatted_markets
        
        except requests.exceptions.RequestException as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue
    
    logger.error(f"Polymarket API error: {last_error}")
    return _get_mock_polymarket_data(asset)

def _get_mock_polymarket_data(asset: str) -> List[Dict[str, Any]]:
    """Generate mock Polymarket data when API fails."""
    logger.info(f"Generating mock Polymarket data for {asset}")
    return [
        {"market_id": f"{asset}-crypto-5min", "question": f"Will {asset} be higher in 5 minutes?", "yes_price": 0.51, "no_price": 0.49, "volume": 1500.0, "end_date": None},
        {"market_id": f"{asset}-crypto-1h", "question": f"Will {asset} be higher in 1 hour?", "yes_price": 0.48, "no_price": 0.52, "volume": 2000.0, "end_date": None}
    ]

def get_market_price(market_id: str) -> Dict[str, Any]:
    """Get price information for a specific Polymarket market."""
    for base_url in BASE_URLS:
        try:
            response = requests.get(f"{base_url}/markets/{market_id}", timeout=10, verify=False)
            response.raise_for_status()
            market = response.json()
            
            return {
                "yes_price": float(market.get("yes_price", 0) or 0),
                "no_price": float(market.get("no_price", 0) or 0),
                "volume": float(market.get("volume", 0) or 0),
                "spread": abs(float(market.get("yes_price", 0) or 0) - float(market.get("no_price", 0) or 0))
            }
        except Exception:
            continue
    
    logger.error(f"Polymarket market price error for {market_id}")
    return {}