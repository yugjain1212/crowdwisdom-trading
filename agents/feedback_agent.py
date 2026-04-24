import logging
from collections import Counter
from utils.logger import setup_logger

logger = setup_logger("FeedbackAgent")

class FeedbackAgent:
    """Feedback agent - analyzes past predictions for self-improvement."""
    
    def __init__(self, state_manager):
        self.state_manager = state_manager
    
    def analyze(self, prediction_log, asset: str):
        """Analyze past predictions and suggest adjustments."""
        if not prediction_log:
            return {
                "confidence_adjustment": 0.0,
                "kelly_cap_adjustment": 0.0,
                "dominant_bias": "BALANCED",
                "accuracy_estimate": 0.5,
                "suggested_threshold": self.state_manager.confidence_threshold,
                "feedback_summary": "No data available for analysis"
            }
        
        recent = prediction_log[-20:] if len(prediction_log) >= 20 else prediction_log
        total = len(recent)
        
        up_count = sum(1 for p in recent if p.get("kronos_prediction", {}).get("final_direction") == "UP")
        down_count = total - up_count
        
        confidences = [p.get("kronos_prediction", {}).get("final_confidence", 0.5) for p in recent]
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
        
        if up_count > down_count * 1.2:
            dominant_bias = "UP_BIAS"
        elif down_count > up_count * 1.2:
            dominant_bias = "DOWN_BIAS"
        else:
            dominant_bias = "BALANCED"
        
        win_rate = self.state_manager.get_win_rate(asset, last_n=total)
        
        conf_adjust = 0.0
        if win_rate < avg_conf - 0.1:
            conf_adjust = -0.05
        elif win_rate > avg_conf + 0.1:
            conf_adjust = 0.05
        
        suggested_threshold = max(0.5, min(0.8, self.state_manager.confidence_threshold + conf_adjust))
        
        if abs(suggested_threshold - self.state_manager.confidence_threshold) > 0.01:
            self.state_manager.update_confidence_threshold(suggested_threshold)
        
        summary = f"Analysis of {total} predictions: {dominant_bias.replace('_', ' ').lower()}, avg confidence {avg_conf:.1%}, win rate {win_rate:.1%}"
        
        return {
            "confidence_adjustment": conf_adjust,
            "kelly_cap_adjustment": 0.0,
            "dominant_bias": dominant_bias,
            "accuracy_estimate": win_rate,
            "suggested_threshold": suggested_threshold,
            "feedback_summary": summary
        }
    
    def quick_check(self, prediction):
        """Check if prediction meets confidence threshold."""
        confidence = prediction.get("final_confidence", 0.5)
        threshold = self.state_manager.confidence_threshold
        result = confidence >= threshold
        logger.info(f"FeedbackAgent: Signal {'ACCEPTED' if result else 'REJECTED'} (confidence {confidence:.1%} vs threshold {threshold:.1%})")
        return result