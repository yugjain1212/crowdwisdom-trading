import logging
from tools.kronos_tool import predict_next_direction, multi_timeframe_check
from utils.logger import setup_logger

logger = setup_logger("KronosAgent")

class KronosAgent:
    """Kronos agent - generates price predictions using Kronos model."""
    
    def __init__(self):
        self.predict_tool = predict_next_direction
        self.multi_timeframe_tool = multi_timeframe_check
    
    def predict(self, bars, asset: str):
        """Generate price direction prediction for an asset."""
        try:
            kronos_result = self.predict_tool(bars)
            mtf_result = self.multi_timeframe_tool(bars)
            
            logger.info(f"KronosAgent: {asset} prediction = {kronos_result['direction']} ({kronos_result['confidence']:.1%})")
            
            conf = kronos_result["confidence"]
            agreement = mtf_result["agreement"]
            
            if conf >= 0.75 and agreement:
                signal_strength = "STRONG"
            elif conf >= 0.6:
                signal_strength = "MODERATE"
            else:
                signal_strength = "WEAK"
            
            return {
                "final_direction": kronos_result["direction"],
                "final_confidence": kronos_result["confidence"],
                "timeframe_agreement": mtf_result["agreement"],
                "reasoning": f"Technical analysis indicates {kronos_result['direction']} trend",
                "signal_strength": signal_strength
            }
        except Exception as e:
            logger.error(f"Error in KronosAgent.predict: {e}")
            return {
                "final_direction": "UP",
                "final_confidence": 0.5,
                "timeframe_agreement": False,
                "reasoning": "Error in prediction",
                "signal_strength": "WEAK"
            }