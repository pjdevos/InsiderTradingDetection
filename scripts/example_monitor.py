"""
Example script demonstrating real-time trade monitoring
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api.client import PolymarketAPIClient
from api.monitor import RealTimeTradeMonitor
from config import config


def on_large_trade_detected(trade):
    """
    Callback function called when a large trade is detected

    Args:
        trade: Trade dict with market data
    """
    market = trade.get('market', {})
    bet_size = trade.get('bet_size_usd', 0)
    wallet = trade.get('wallet_address', 'unknown')[:10]

    print("\n" + "=" * 70)
    print("LARGE TRADE DETECTED!")
    print("=" * 70)
    print(f"Market:    {market.get('question', 'Unknown')}")
    print(f"Bet Size:  ${bet_size:,.2f}")
    print(f"Wallet:    {wallet}...")
    print(f"Category:  {trade.get('category', 'Unknown')}")
    print(f"Time:      {trade.get('timestamp', 'Unknown')}")
    print("=" * 70)


def main():
    """Run the example monitor"""
    print("=" * 70)
    print("Polymarket Real-Time Trade Monitor - Example")
    print("=" * 70)
    print()
    print(f"Monitoring for trades >= ${config.MIN_BET_SIZE_USD:,.0f}")
    print(f"Polling interval: {config.POLL_INTERVAL_SECONDS} seconds")
    print(f"Focus: Geopolitical markets only")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()

    # Initialize client and monitor
    client = PolymarketAPIClient()
    monitor = RealTimeTradeMonitor(
        api_client=client,
        min_bet_size=config.MIN_BET_SIZE_USD,
        interval_seconds=config.POLL_INTERVAL_SECONDS
    )

    # Register callback
    monitor.register_callback(on_large_trade_detected)

    # Get recent large trades as a sample
    print("Fetching recent large trades (last 24 hours)...")
    recent = monitor.get_recent_large_trades(hours=24, geopolitical_only=True)
    if recent:
        print(f"Found {len(recent)} large geopolitical trades in last 24 hours:")
        for i, trade in enumerate(recent[:5], 1):
            market = trade.get('market', {})
            print(f"  {i}. ${trade.get('bet_size_usd', 0):,.0f} - {market.get('question', 'Unknown')[:50]}")
    else:
        print("No large geopolitical trades found in last 24 hours")
    print()

    # Start monitoring
    print("Starting live monitoring...")
    print()

    try:
        monitor.start()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        monitor.stop()


if __name__ == '__main__':
    main()
