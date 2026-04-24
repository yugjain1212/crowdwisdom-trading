from typing import List, Dict, Any
from tools.kronos_tool import predict_next_direction
from utils.logger import setup_logger

logger = setup_logger(__name__)

def timeframe_arbitrage_check(bars: List[Dict[str, Any]], asset: str) -> Dict[str, Any]:
    """Check for internal arbitrage between different timeframes."""
    if not bars or len(bars) < 150:
        return {
            "five_min_predictions": [],
            "fifteen_min_prediction": {},
            "all_agree": False,
            "agreement_rate": 0.0,
            "arb_signal": "CONFLICTED",
            "recommended_action": "INSUFFICIENT_DATA"
        }
    
    five_min_windows = [50, 100, 150]
    five_min_predictions = []
    
    for window in five_min_windows:
        if len(bars) >= window:
            pred = predict_next_direction(bars[-window:])
            five_min_predictions.append(pred)
    
    fifteen_min_prediction = predict_next_direction(bars[-200:]) if len(bars) >= 200 else predict_next_direction(bars)
    
    if len(five_min_predictions) >= 3:
        directions = [p["direction"] for p in five_min_predictions[:3]]
        from collections import Counter
        counts = Counter(directions)
        majority = counts.most_common(1)[0][0]
        agreement_rate = counts[majority] / len(directions)
        all_agree = agreement_rate == 1.0
    else:
        agreement_rate = 0.0
        all_agree = False
        majority = "UNKNOWN"
    
    fifteen_dir = fifteen_min_prediction["direction"]
    overall_agree = all_agree and fifteen_dir == majority
    
    if overall_agree:
        arb_signal = "STRONG"
        action = f"FOLLOW_{fifteen_dir}_SIGNAL"
    elif agreement_rate >= 0.67:
        arb_signal = "MODERATE"
        action = f"CONSIDER_{majority}_WITH_CAUTION"
    else:
        arb_signal = "CONFLICTED"
        action = "AVOID_TRADING"
    
    return {
        "five_min_predictions": five_min_predictions[:3],
        "fifteen_min_prediction": fifteen_min_prediction,
        "all_agree": overall_agree,
        "agreement_rate": agreement_rate,
        "arb_signal": arb_signal,
        "recommended_action": action
    }