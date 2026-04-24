# CrowdWisdom Trading Agent

A multi-agent AI crypto prediction system that searches prediction markets, fetches OHLCV data from Binance, predicts price moves using technical indicators, calculates Kelly Criterion position sizing, and implements a feedback loop for continuous improvement.

## Features

- **MarketSearchAgent**: Searches Polymarket and Kalshi APIs for crypto prediction markets
- **DataFetchAgent**: Fetches OHLCV price data from Binance
- **KronosAgent**: Predicts next UP/DOWN price movement using technical indicators
- **RiskAgent**: Calculates Kelly Criterion optimal position sizing
- **FeedbackAgent**: Auto-adjusts confidence thresholds based on performance
- **Arbitrage Detection**: Detects cross-exchange arbitrage opportunities
- **FastAPI Dashboard**: Web interface on port 8080

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file and add your API keys
cp .env.example .env
# Edit .env with your API keys:
# - OPENROUTER_API_KEY (from openrouter.ai)
# - APIFY_TOKEN (from apify.com)
```

## Usage

```bash
# Run the agent
python main.py

# Access dashboard
curl http://localhost:8080/health
```

## Configuration

Edit `main.py` to adjust:
- Assets to monitor: `["BTC", "ETH"]`
- Loop interval: 300 seconds
- Confidence threshold: 50%

## Project Structure

```
.
├── main.py              # Main orchestrator
├── agents/             # Agent implementations
│   ├── market_search_agent.py
│   ├── data_fetch_agent.py
│   ├── kronos_agent.py
│   ├── risk_agent.py
│   └── feedback_agent.py
├── tools/              # API tool wrappers
│   ├── polymarket_tool.py
│   ├── kalshi_tool.py
│   ├── apify_tool.py
│   └── kronos_tool.py
├── utils/              # Utilities
│   ├── logger.py
│   ├── kelly.py
│   └── state.py
└── logs/               # Prediction logs
    └── predictions.jsonl
```

## API Keys Required

- **OPENROUTER_API_KEY**: For LLM access (hermes-agent fallback)
- **APIFY_TOKEN**: For Apify data fetching

## Notes

- Polymarket/Kalshi APIs may be blocked in certain regions (India government block)
- The system falls back to mock data when APIs are unavailable
- Binance data always works for price predictions