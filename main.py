import asyncio
import json
import os
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List, Any

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import agents
from agents.market_search_agent import MarketSearchAgent
from agents.data_fetch_agent import DataFetchAgent
from agents.kronos_agent import KronosAgent
from agents.risk_agent import RiskAgent
from agents.feedback_agent import FeedbackAgent
from utils.logger import setup_logger, log_prediction, load_prediction_log, print_cycle_summary

# Import utilities
from utils.state import StateManager
from utils.kelly import arbitrage_check

# Import bonus features
from tools.arbitrage_engine import timeframe_arbitrage_check

# Import for FastAPI dashboard
from fastapi import FastAPI
import uvicorn

# Setup logging
logger = setup_logger("Main")

# Configuration
CONFIG = {
    "assets": ["BTC", "ETH"],           # Assets to monitor
    "loop_interval_seconds": 300,        # 5 minutes between cycles
    "feedback_every_n_cycles": 5,        # Run feedback loop every N cycles
    "bankroll_usd": 1000.0,             # Starting bankroll
    "enable_arbitrage_check": True,      # Check for arb between Polymarket/Kalshi
    "multi_asset_scale": True,           # Scale to more assets (see SCALING section)
    "extra_assets": ["SOL", "DOGE"],    # Extra assets if multi_asset_scale=True
}

# Global flag for graceful shutdown
shutdown_flag = False

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global shutdown_flag
    logger.info("Shutdown signal received, shutting down gracefully...")
    shutdown_flag = True

def create_fastapi_app(state_manager: StateManager) -> FastAPI:
    """Create FastAPI app for dashboard."""
    app = FastAPI(title="CrowdWisdom Trading Agent", version="1.0.0")
    
    @app.get("/health")
    async def health():
        return {
            "status": "ok", 
            "timestamp": datetime.now().isoformat(),
            "assets_monitored": CONFIG["assets"] + (CONFIG["extra_assets"] if CONFIG["multi_asset_scale"] else []),
            "total_cycles": len(state_manager.cycles)
        }
    
    @app.get("/predictions")
    async def get_predictions(limit: int = 20):
        """Get last N prediction cycles."""
        recent_cycles = state_manager.cycles[-limit:] if state_manager.cycles else []
        return [cycle.__dict__ for cycle in recent_cycles]
    
    @app.get("/predictions/{asset}")
    async def get_predictions_for_asset(asset: str, limit: int = 20):
        """Get last N prediction cycles for specific asset."""
        asset_cycles = state_manager.get_recent_cycles(asset.upper(), limit)
        return [cycle.__dict__ for cycle in asset_cycles]
    
    @app.get("/latest")
    async def get_latest_predictions():
        """Get latest prediction for each monitored asset."""
        assets = CONFIG["assets"] + (CONFIG["extra_assets"] if CONFIG["multi_asset_scale"] else [])
        latest = {}
        for asset in assets:
            cycles = state_manager.get_recent_cycles(asset, 1)
            if cycles:
                latest[asset] = cycles[0].__dict__
            else:
                latest[asset] = None
        return latest
    
    return app

def run_fastapi_app(state_manager: StateManager):
    """Run FastAPI app in a separate thread."""
    app = create_fastapi_app(state_manager)
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="warning")

async def run_pipeline():
    """Main orchestrator function that runs the agent pipeline."""
    global shutdown_flag
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check required environment variables
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    apify_token = os.getenv("APIFY_TOKEN")
    
    if not openrouter_key:
        logger.error("OPENROUTER_API_KEY not set in environment variables")
        sys.exit(1)
    
    if not apify_token:
        logger.warning("APIFY_TOKEN not set - will rely solely on Binance API")
    
    logger.info("🚀 CrowdWisdom Trading Agent STARTED")
    assets_list = CONFIG["assets"] + (CONFIG["extra_assets"] if CONFIG["multi_asset_scale"] else [])
    logger.info(f"Monitoring {len(assets_list)} assets: {', '.join(assets_list)}")
    logger.info(f"Loop interval: {CONFIG['loop_interval_seconds']} seconds")
    logger.info(f"Feedback every: {CONFIG['feedback_every_n_cycles']} cycles")
    logger.info(f"Bankroll: ${CONFIG['bankroll_usd']:.2f}")
    
    # Initialize agents and state manager
    try:
        state_manager = StateManager()
        market_search_agent = MarketSearchAgent()
        data_fetch_agent = DataFetchAgent()
        kronos_agent = KronosAgent()
        risk_agent = RiskAgent(bankroll=CONFIG["bankroll_usd"])
        feedback_agent = FeedbackAgent(state_manager)
        
        logger.info("All agents initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agents: {e}")
        sys.exit(1)
    
    # Start FastAPI dashboard in background thread
    fastapi_thread = threading.Thread(target=run_fastapi_app, args=(state_manager,), daemon=True)
    fastapi_thread.start()
    logger.info("FastAPI dashboard started on http://localhost:8080")
    
    # Initialize cycle counter
    cycle_count = 0
    
    # Main loop
    while not shutdown_flag:
        cycle_count += 1
        logger.info(f"=== Starting Cycle {cycle_count} ===")
        
        # Determine which assets to process in this cycle
        assets_to_process = CONFIG["assets"] + (CONFIG["extra_assets"] if CONFIG["multi_asset_scale"] else [])
        
        # Process each asset
        cycle_results = []
        
        for asset in assets_to_process:
            if shutdown_flag:
                break
                
            logger.info(f"--- Processing {asset} ---")
            
            try:
                # STEP 1 - Market Search
                logger.info("Step 1: Market Search")
                market_data = market_search_agent.search(asset)
                
                # STEP 2 - Data Fetch
                logger.info("Step 2: Data Fetch")
                ohlcv_bars = data_fetch_agent.fetch(asset, bars=1000)
                
                if not ohlcv_bars:
                    logger.warning(f"No OHLCV data retrieved for {asset}, skipping...")
                    continue
                
                # Validate bars
                if not data_fetch_agent.validate_tool(ohlcv_bars):
                    logger.warning(f"OHLCV data validation failed for {asset}, but continuing anyway...")
                
                # Analyze data quality
                quality = data_fetch_agent.analyze_quality(ohlcv_bars, asset)
                logger.info(f"Data quality score: {quality['quality_score']}/100")
                
                # Store market data in state
                cycle = state_manager.new_cycle(asset)
                cycle.polymarket_data = market_data
                cycle.kalshi_data = {}  # Will be populated below
                cycle.ohlcv_bars = ohlcv_bars
                
                # Extract best markets for easier access
                polymarket_best = market_data.get("polymarket_best", {})
                kalshi_best = market_data.get("kalshi_best", {})
                cycle.kalshi_data = {"kalshi_best": kalshi_best} if kalshi_best else {}
                
                # STEP 3 - Kronos Prediction
                logger.info("Step 3: Kronos Prediction")
                kronos_prediction = kronos_agent.predict(ohlcv_bars, asset)
                cycle.kronos_prediction = kronos_prediction
                
                # BONUS FEATURE 1 - Internal Arbitrage Engine
                logger.info("Step 3.5: Timeframe Arbitrage Check")
                timeframe_arb = timeframe_arbitrage_check(ohlcv_bars, asset)
                cycle.timeframe_arbitrage = timeframe_arb
                if timeframe_arb["arb_signal"] == "STRONG":
                    logger.info(f"⚡ TIMEFRAME ARB DETECTED: {timeframe_arb}")
                
                # STEP 4 - Feedback Gate
                logger.info("Step 4: Feedback Gate")
                is_valid = feedback_agent.quick_check(kronos_prediction)
                if not is_valid:
                    logger.info("Signal below threshold — skipping risk calculation")
                    cycle.final_recommendation = "HOLD"
                    cycle.kelly_result = {}
                    state_manager.save_cycle(cycle)
                    cycle_results.append({
                        "asset": asset,
                        "direction": kronos_prediction.get("final_direction", "N/A"),
                        "confidence": kronos_prediction.get("final_confidence", 0),
                        "recommendation": "HOLD",
                        "kelly_bet": 0,
                        "arb": False
                    })
                    continue
                
                # STEP 5 - Risk Management
                logger.info("Step 5: Risk Management")
                # Combine market data for risk agent
                combined_market_data = {
                    "polymarket_best": polymarket_best,
                    "kalshi_best": kalshi_best,
                    "average_yes_price": (
                        (polymarket_best.get("yes_price", 0.5) + kalshi_best.get("yes_price", 0.5)) / 2
                    )
                }
                
                risk_result = risk_agent.calculate(kronos_prediction, combined_market_data, asset)
                cycle.kelly_result = risk_result
                cycle.final_recommendation = risk_result["final_recommendation"]
                
                # STEP 6 - Arbitrage Check
                logger.info("Step 6: Arbitrage Check")
                arb_detected = False
                arb_details = None
                if CONFIG["enable_arbitrage_check"]:
                    poly_price = polymarket_best.get("yes_price", 0.5)
                    kalshi_price = kalshi_best.get("yes_price", 0.5)
                    arb_result = arbitrage_check(poly_price, kalshi_price)
                    if arb_result["has_arb"]:
                        arb_detected = True
                        arb_details = arb_result["direction"]
                        logger.info(f"⚡ ARB OPPORTUNITY DETECTED: {arb_result}")
                
                # Save cycle
                state_manager.save_cycle(cycle)
                
                # Add to results for display
                cycle_results.append({
                    "asset": asset,
                    "direction": kronos_prediction.get("final_direction", "N/A"),
                    "confidence": kronos_prediction.get("final_confidence", 0),
                    "recommendation": risk_result["final_recommendation"],
                    "kelly_bet": risk_result["recommended_position_usd"],
                    "arb": arb_detected
                })
                
                logger.info(f"--- Completed {asset} ---")
                
            except Exception as e:
                logger.error(f"Error processing {asset}: {e}")
                continue
        
        # Display summary table using rich
        if cycle_results:
            from utils.logger import print_cycle_summary
            print_cycle_summary(cycle_results)
            print_cycle_summary(cycle_results)
        # Display summary table using rich
        if cycle_results:
            from utils.logger import print_cycle_summary
            print_cycle_summary(cycle_results)
        
        # Feedback loop (every N cycles)
        if cycle_count % CONFIG["feedback_every_n_cycles"] == 0:
            logger.info("=== Running Feedback Loop ===")
            for asset in assets_to_process:
                try:
                    recent_cycles = state_manager.get_recent_cycles(asset, 20)
                    if recent_cycles:
                        # Convert to dict format for feedback agent
                        prediction_log = [cycle.__dict__ for cycle in recent_cycles]
                        adjustments = feedback_agent.analyze(prediction_log, asset)
                        logger.info(f"Feedback for {asset}: {adjustments['feedback_summary']}")
                except Exception as e:
                    logger.error(f"Error in feedback loop for {asset}: {e}")
        
        # Sleep until next cycle
        if not shutdown_flag:
            logger.info(f"Next cycle in {CONFIG['loop_interval_seconds']} seconds...")
            for _ in range(CONFIG["loop_interval_seconds"]):
                if shutdown_flag:
                    break
                time.sleep(1)
    
    logger.info("🚀 CrowdWisdom Trading Agent SHUTDOWN COMPLETE")

if __name__ == "__main__":
    try:
        asyncio.run(run_pipeline())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        sys.exit(1)
