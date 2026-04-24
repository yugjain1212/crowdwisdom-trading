import numpy as np
import logging
from typing import List, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)

def predict_next_direction(bars: List[Dict[str, Any]], prediction_steps: int = 1) -> Dict[str, Any]:
    """
    Predict next price direction using Kronos model or technical indicator fallback.
    
    Args:
        bars: List of OHLCV bar dictionaries
        prediction_steps: Number of steps to predict ahead (default: 1)
    
    Returns:
        Dictionary with prediction results
    """
    if not bars or len(bars) < 10:
        logger.warning("Insufficient bars for prediction")
        return {
            "direction": "UP",
            "confidence": 0.5,
            "method": "error_fallback",
            "indicators": {},
            "predicted_price": 0.0,
            "current_price": 0.0
        }
    
    # Extract close prices
    close_prices = np.array([bar["close"] for bar in bars])
    current_price = close_prices[-1]
    
    # Try Kronos model first
    try:
        import torch
        
        # Normalize the series: (x - mean) / std
        mean = np.mean(close_prices)
        std = np.std(close_prices)
        if std == 0:
            std = 1e-8  # Avoid division by zero
        normalized_prices = (close_prices - mean) / std
        
        # Create input tensor of shape (1, min(200, len(bars)), 1)
        seq_len = min(200, len(normalized_prices))
        input_tensor = torch.FloatTensor(normalized_prices[-seq_len:]).unsqueeze(0).unsqueeze(-1)
        
        # Try to import and use Kronos
        try:
            from kronos import KronosModel
            model = KronosModel.from_pretrained("shiyu-coder/Kronos-small")
            
            # Get forecast
            with torch.no_grad():
                forecast = model.predict(input_tensor, prediction_steps=prediction_steps)
            
            # Denormalize forecast
            forecast_denorm = forecast.numpy().flatten() * std + mean
            
            # Compare to last close
            predicted_price = forecast_denorm[-1] if len(forecast_denorm) > 0 else current_price
            price_change = (predicted_price - current_price) / current_price
            
            # Determine direction and confidence
            if price_change > 0:
                direction = "UP"
                # Confidence based on magnitude of change (capped)
                confidence = min(0.5 + abs(price_change) * 10, 0.95)
            else:
                direction = "DOWN"
                confidence = min(0.5 + abs(price_change) * 10, 0.95)
            
            # Ensure confidence is at least 0.5
            confidence = max(0.5, confidence)
            
            logger.info(f"Kronos prediction: {direction} with {confidence:.2%} confidence")
            
            return {
                "direction": direction,
                "confidence": float(confidence),
                "method": "kronos",
                "indicators": {
                    "predicted_price": float(predicted_price),
                    "price_change_pct": float(price_change * 100)
                },
                "predicted_price": float(predicted_price),
                "current_price": float(current_price)
            }
            
        except ImportError:
            logger.info("Kronos not available, using technical indicator fallback")
        except Exception as e:
            logger.warning(f"Kronos prediction failed: {e}, using technical indicator fallback")
    
    except ImportError:
        logger.info("Torch not available, using technical indicator fallback")
    except Exception as e:
        logger.warning(f"Error in Kronos prediction setup: {e}, using technical indicator fallback")
    
    # Fallback to technical indicators
    return _technical_fallback_prediction(close_prices, current_price)

def _technical_fallback_prediction(close_prices: np.ndarray, current_price: float) -> Dict[str, Any]:
    """
    Fallback prediction using technical indicators.
    
    Args:
        close_prices: Array of close prices
        current_price: Current close price
    
    Returns:
        Dictionary with prediction results
    """
    if len(close_prices) < 20:
        logger.warning("Insufficient data for technical indicators")
        return {
            "direction": "UP" if len(close_prices) >= 2 and close_prices[-1] > close_prices[-2] else "DOWN",
            "confidence": 0.52,
            "method": "technical_fallback",
            "indicators": {},
            "predicted_price": current_price,
            "current_price": current_price
        }
    
    # Calculate technical indicators from the last 50 bars
    lookback = min(50, len(close_prices))
    recent_closes = close_prices[-lookback:]
    
    # SMA_10: simple moving average of last 10 closes
    sma_10 = np.mean(recent_closes[-10:]) if len(recent_closes) >= 10 else np.mean(recent_closes)
    
    # SMA_20: simple moving average of last 20 closes
    sma_20 = np.mean(recent_closes[-20:]) if len(recent_closes) >= 20 else np.mean(recent_closes)
    
    # RSI: 14-period RSI
    def calculate_rsi(prices, period=14):
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        if down == 0:
            return 100.0
        rs = up / down
        rsi = 100.0 - (100.0 / (1.0 + rs))
        for i in range(len(prices) - period - 1):
            delta = deltas[i + period]
            if delta > 0:
                upval = delta
                downval = 0.0
            else:
                upval = 0.0
                downval = -delta
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            if down == 0:
                rsi = 100.0
            else:
                rs = up / down
                rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi
    
    rsi = calculate_rsi(recent_closes)
    
    # momentum: (close[-1] - close[-5]) / close[-5] * 100
    momentum = 0.0
    if len(recent_closes) >= 5:
        momentum = (recent_closes[-1] - recent_closes[-5]) / recent_closes[-5] * 100
    
    # volatility: std of last 20 returns
    volatility = 0.0
    if len(recent_closes) >= 20:
        returns = np.diff(recent_closes[-20:]) / recent_closes[-20:-1]
        volatility = np.std(returns) * 100  # As percentage
    
    # Direction logic
    if sma_10 > sma_20 and momentum > 0 and rsi < 70:
        direction = "UP"
        confidence = 0.60
    elif sma_10 < sma_20 and momentum < 0 and rsi > 30:
        direction = "DOWN"
        confidence = 0.60
    else:
        direction = "UP" if momentum > 0 else "DOWN"
        confidence = 0.52
    
    # Adjust confidence based on indicator strength
    # Stronger signals increase confidence
    sma_diff = abs(sma_10 - sma_20) / sma_20 if sma_20 != 0 else 0
    momentum_strength = min(abs(momentum) / 5, 0.2)  # Cap momentum contribution
    rsi_extreme = 0.0
    if rsi > 70 or rsi < 30:
        rsi_extreme = 0.1  # Extreme RSI reduces confidence in continuation
    else:
        rsi_extreme = -0.05  # Neutral RSI increases confidence
    
    confidence = 0.5 + sma_diff * 2 + momentum_strength + rsi_extreme
    confidence = max(0.5, min(0.95, confidence))  # Clamp between 0.5 and 0.95
    
    # Simple price prediction: assume small move in direction of momentum
    predicted_price = current_price * (1 + momentum / 100 * 0.1)  # 10% of momentum as price change
    
    logger.info(f"Technical fallback prediction: {direction} with {confidence:.2%} confidence")
    
    return {
        "direction": direction,
        "confidence": float(confidence),
        "method": "technical_fallback",
        "indicators": {
            "sma_10": float(sma_10),
            "sma_20": float(sma_20),
            "rsi": float(rsi),
            "momentum": float(momentum),
            "volatility": float(volatility)
        },
        "predicted_price": float(predicted_price),
        "current_price": float(current_price)
    }

def multi_timeframe_check(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run predictions on multiple timeframes to check for agreement.
    
    Args:
        bars: List of OHLCV bar dictionaries
    
    Returns:
        Dictionary with multi-timeframe analysis results
    """
    if not bars or len(bars) < 50:
        logger.warning("Insufficient bars for multi-timeframe check")
        return {
            "agreement": False,
            "direction": "UP",
            "avg_confidence": 0.5
        }
    
    # Define timeframe windows: last 50, 100, 200 bars (or as many as available)
    windows = [50, 100, 200]
    predictions = []
    
    for window in windows:
        if len(bars) >= window:
            window_bars = bars[-window:]
            pred = predict_next_direction(window_bars)
            predictions.append(pred)
        else:
            # Use all available bars if window is too large
            pred = predict_next_direction(bars)
            predictions.append(pred)
            break  # Don't repeat the same prediction
    
    if not predictions:
        return {
            "agreement": False,
            "direction": "UP",
            "avg_confidence": 0.5
        }
    
    # Check agreement on direction
    directions = [p["direction"] for p in predictions]
    agreement = all(d == directions[0] for d in directions)
    
    # Average confidence
    avg_confidence = np.mean([p["confidence"] for p in predictions])
    
    # Overall direction is the agreed direction or the most common one
    if agreement:
        direction = directions[0]
    else:
        # Count occurrences
        from collections import Counter
        direction_counts = Counter(directions)
        direction = direction_counts.most_common(1)[0][0]
    
    logger.info(f"Multi-timeframe check: agreement={agreement}, direction={direction}, avg_confidence={avg_confidence:.2%}")
    
    return {
        "agreement": agreement,
        "direction": direction,
        "avg_confidence": float(avg_confidence)
    }