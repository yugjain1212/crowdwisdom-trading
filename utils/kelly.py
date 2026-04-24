from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class KellyResult:
    """Result of Kelly Criterion calculation."""
    kelly_fraction: float
    recommended_bet_usd: float
    edge: float
    is_favorable: bool
    reasoning: str

def calculate_kelly(win_probability: float, market_yes_price: float, bankroll: float = 1000.0, max_kelly_fraction: float = 0.25) -> KellyResult:
    """
    Calculate Kelly Criterion for optimal bet sizing.
    
    Args:
        win_probability: Probability of winning (0-1)
        market_yes_price: Market price for YES outcome (0.01-0.99)
        bankroll: Total bankroll in USD (default: 1000.0)
        max_kelly_fraction: Maximum fraction of bankroll to bet (default: 0.25 for half-Kelly safety)
    
    Returns:
        KellyResult with calculation details
    """
    # Input validation
    if not 0 <= win_probability <= 1:
        raise ValueError("win_probability must be between 0 and 1")
    if not 0.01 <= market_yes_price <= 0.99:
        raise ValueError("market_yes_price must be between 0.01 and 0.99")
    
    # Calculate implied odds: b = p / (1 - p) where p is market probability
    b = market_yes_price / (1 - market_yes_price)
    
    # Kelly formula: f* = (bp - q) / b where p = win_probability, q = 1 - p
    p = win_probability
    q = 1 - p
    f_star = (b * p - q) / b
    
    # Only calculate if positive edge
    if f_star <= 0:
        return KellyResult(
            kelly_fraction=0.0,
            recommended_bet_usd=0.0,
            edge=f_star,
            is_favorable=False,
            reasoning=f"Negative edge ({f_star:.3f}) - no bet"
        )
    
    # Apply half-Kelly for safety (multiply by 0.5)
    f_star_half = f_star * 0.5
    
    # Clamp between 0 and max_kelly_fraction
    kelly_fraction = max(0.0, min(f_star_half, max_kelly_fraction))
    
    # Calculate recommended bet in USD
    recommended_bet_usd = kelly_fraction * bankroll
    
    # Calculate edge: expected value minus 1
    edge = (b * p - q) / b  # This is the same as the full Kelly before halving
    
    # Determine if favorable (minimum 2% edge required and positive kelly)
    is_favorable = edge > 0.02 and kelly_fraction > 0
    
    # Generate reasoning string
    reasoning_parts = []
    reasoning_parts.append(f"Win probability: {p:.1%}")
    reasoning_parts.append(f"Market YES price: {market_yes_price:.3f}")
    reasoning_parts.append(f"Implied odds (b): {b:.3f}")
    reasoning_parts.append(f"Full Kelly: {f_star:.3f}")
    reasoning_parts.append(f"Half-Kelly: {f_star_half:.3f}")
    reasoning_parts.append(f"Clamped Kelly: {kelly_fraction:.3f}")
    reasoning_parts.append(f"Edge: {edge:.3f}")
    reasoning_parts.append(f"Favorable (>2% edge): {is_favorable}")
    
    reasoning = " | ".join(reasoning_parts)
    
    return KellyResult(
        kelly_fraction=kelly_fraction,
        recommended_bet_usd=recommended_bet_usd,
        edge=edge,
        is_favorable=is_favorable,
        reasoning=reasoning
    )

def arbitrage_check(polymarket_yes: float, kalshi_yes: float, threshold: float = 0.03) -> dict:
    """
    Check for arbitrage opportunity between Polymarket and Kalshi.
    
    Args:
        polymarket_yes: Polymarket YES price (0-1 float)
        kalshi_yes: Kalshi YES price (0-1 float)
        threshold: Minimum percentage difference for arbitrage (default: 0.03 = 3%)
    
    Returns:
        Dictionary with arbitrage details
    """
    # Calculate percentage difference
    diff = abs(polymarket_yes - kalshi_yes)
    avg_price = (polymarket_yes + kalshi_yes) / 2
    arb_percentage = diff / avg_price if avg_price > 0 else 0
    
    has_arb = arb_percentage > threshold
    
    # Determine direction
    if polymarket_yes > kalshi_yes:
        direction = "BUY_POLY_SELL_KALSHI"  # Buy low on Kalshi, sell high on Polymarket
    else:
        direction = "BUY_KALSHI_SELL_POLY"  # Buy low on Polymarket, sell high on Kalshi
    
    return {
        "has_arb": has_arb,
        "arb_percentage": arb_percentage,
        "direction": direction if has_arb else None
    }