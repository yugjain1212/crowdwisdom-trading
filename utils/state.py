from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from utils.logger import log_prediction
import logging

logger = logging.getLogger(__name__)

@dataclass
class PredictionCycle:
    """Represents a single prediction cycle."""
    cycle_id: str
    timestamp: str
    asset: str
    polymarket_data: Dict[str, Any]
    kalshi_data: Dict[str, Any]
    ohlcv_bars: List[Dict[str, Any]]
    kronos_prediction: Dict[str, Any]
    kelly_result: Dict[str, Any]
    feedback_adjustments: Dict[str, Any]
    final_recommendation: str  # One of: "STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"

class StateManager:
    """Manages shared state across prediction cycles."""
    
    def __init__(self):
        self.cycles: List[PredictionCycle] = []
        self.confidence_threshold = 0.50  # Adjustable by feedback agent
    
    def new_cycle(self, asset: str) -> PredictionCycle:
        """Create a new prediction cycle."""
        cycle = PredictionCycle(
            cycle_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            asset=asset,
            polymarket_data={},
            kalshi_data={},
            ohlcv_bars=[],
            kronos_prediction={},
            kelly_result={},
            feedback_adjustments={},
            final_recommendation="HOLD"
        )
        return cycle
    
    def save_cycle(self, cycle: PredictionCycle) -> None:
        """Save a cycle to internal state and log it."""
        self.cycles.append(cycle)
        log_prediction(asdict(cycle))
    
    def get_recent_cycles(self, asset: str, n: int = 20) -> List[PredictionCycle]:
        """Get the last N cycles for a specific asset."""
        asset_cycles = [c for c in self.cycles if c.asset == asset]
        return asset_cycles[-n:] if asset_cycles else []
    
    def update_confidence_threshold(self, new_threshold: float) -> None:
        """Update the confidence threshold (used by feedback agent)."""
        old_threshold = self.confidence_threshold
        self.confidence_threshold = max(0.5, min(0.95, new_threshold))  # Clamp between 0.5 and 0.95
        logger.info(f"Confidence threshold updated from {old_threshold:.2f} to {self.confidence_threshold:.2f}")
    
    def get_win_rate(self, asset: str, last_n: int = 20) -> float:
        """
        Calculate win rate from last N cycles.
        Stub implementation - returns 0.5 if no outcome data yet.
        In a real system, this would compare predictions with actual outcomes.
        """
        # For now, return 0.5 as placeholder
        # In future, this would check actual outcomes vs predictions
        return 0.5