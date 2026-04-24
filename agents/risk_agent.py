import logging
from utils.kelly import calculate_kelly, arbitrage_check
from utils.logger import setup_logger

logger = setup_logger("RiskAgent")

class RiskAgent:
    """Risk agent - calculates position sizing using Kelly Criterion."""
    
    def __init__(self, bankroll: float = 1000.0):
        self.bankroll = bankroll
    
    def calculate(self, prediction, market_data, asset: str):
        """Calculate risk management recommendations."""
        try:
            win_probability = prediction.get("final_confidence", 0.5)
            
            poly_best = market_data.get("polymarket_best", {})
            kalshi_best = market_data.get("kalshi_best", {})
            
            poly_yes = poly_best.get("yes_price", 0.5)
            kalshi_yes = kalshi_best.get("yes_price", 0.5)
            
            market_yes_price = (poly_yes + kalshi_yes) / 2
            
            kelly_result = calculate_kelly(
                win_probability=win_probability,
                market_yes_price=market_yes_price,
                bankroll=self.bankroll
            )
            
            arb_check = arbitrage_check(poly_yes, kalshi_yes)
            
            logger.info(f"RiskAgent: {asset} → Kelly fraction={kelly_result.kelly_fraction:.3f}, bet=${kelly_result.recommended_bet_usd:.2f}")
            
            direction = prediction.get("final_direction", "UP")
            signal = prediction.get("signal_strength", "WEAK")
            
            if kelly_result.is_favorable and signal == "STRONG":
                final_rec = "STRONG_BUY" if direction == "UP" else "STRONG_SELL"
            elif kelly_result.is_favorable:
                final_rec = "BUY" if direction == "UP" else "SELL"
            else:
                final_rec = "HOLD"
            
            return {
                "final_recommendation": final_rec,
                "recommended_position_usd": kelly_result.recommended_bet_usd,
                "max_loss_usd": kelly_result.recommended_bet_usd,
                "has_arbitrage_opportunity": arb_check["has_arb"],
                "arb_details": arb_check.get("direction") if arb_check["has_arb"] else None,
                "risk_notes": f"Position sized according to Kelly criterion (edge: {kelly_result.edge:.1%})"
            }
        except Exception as e:
            logger.error(f"Error in RiskAgent.calculate: {e}")
            return {
                "final_recommendation": "HOLD",
                "recommended_position_usd": 0.0,
                "max_loss_usd": 0.0,
                "has_arbitrage_opportunity": False,
                "arb_details": None,
                "risk_notes": f"Error in risk calculation: {str(e)[:50]}"
            }