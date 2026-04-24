install:
	./venv/bin/pip install -r requirements.txt

run:
	./venv/bin/python main.py

test:
	./venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from utils.logger import setup_logger, log_prediction, load_prediction_log
from utils.kelly import calculate_kelly, arbitrage_check, KellyResult
from utils.state import StateManager, PredictionCycle
from tools.polymarket_tool import get_crypto_markets as poly_markets
from tools.kalshi_tool import get_crypto_markets as kalshi_markets
from tools.apify_tool import fetch_ohlcv_bars, validate_bars
from tools.kronos_tool import predict_next_direction, multi_timeframe_check
from tools.arbitrage_engine import timeframe_arbitrage_check
from agents.market_search_agent import MarketSearchAgent
from agents.data_fetch_agent import DataFetchAgent
from agents.kronos_agent import KronosAgent
from agents.risk_agent import RiskAgent
from agents.feedback_agent import FeedbackAgent

print('Running all tests...')

# Test 1: All imports
try:
    from utils.logger import setup_logger, log_prediction, load_prediction_log, print_cycle_summary
    from utils.kelly import calculate_kelly, arbitrage_check, KellyResult
    from utils.state import StateManager, PredictionCycle
    from tools.polymarket_tool import get_crypto_markets as poly_markets
    from tools.kalshi_tool import get_crypto_markets as kalshi_markets
    from tools.apify_tool import fetch_ohlcv_bars, validate_bars
    from tools.kronos_tool import predict_next_direction, multi_timeframe_check
    from tools.arbitrage_engine import timeframe_arbitrage_check
    from agents.market_search_agent import MarketSearchAgent
    from agents.data_fetch_agent import DataFetchAgent
    from agents.kronos_agent import KronosAgent
    from agents.risk_agent import RiskAgent
    from agents.feedback_agent import FeedbackAgent
    print('✅ All imports successful')
except Exception as e:
    print(f'❌ Imports failed: {e}')
    sys.exit(1)

# Test 2: Kelly math
try:
    result = calculate_kelly(win_probability=0.60, market_yes_price=0.50, bankroll=1000.0)
    assert abs(result.kelly_fraction - 0.1) < 0.001
    assert result.is_favorable == True
    print('✅ Kelly math works')
except AssertionError:
    print('❌ Kelly math wrong values')
    sys.exit(1)
except Exception as e:
    print(f'❌ Kelly math failed: {e}')
    sys.exit(1)

print('✅ ALL TESTS PASSED')
"
