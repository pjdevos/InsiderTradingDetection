"""
Integration test script to verify Polymarket API connection
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api.client import PolymarketAPIClient
from config import config


def test_api_connection():
    """Test connection to Polymarket APIs"""
    print("=" * 60)
    print("Polymarket API Connection Test")
    print("=" * 60)
    print()

    # Initialize client
    print("Initializing API client...")
    client = PolymarketAPIClient()
    print(f"  API Key: {client.api_key[:10]}..." if client.api_key else "  No API key configured")
    print()

    # Test 1: Fetch markets
    print("[1/4] Testing get_markets()...")
    try:
        markets = client.get_markets(active=True, limit=10)
        if markets:
            print(f"  [+] SUCCESS: Fetched {len(markets)} markets")
            if len(markets) > 0:
                print(f"  Sample: {markets[0].get('question', 'N/A')[:60]}...")
        else:
            print("  [-] No markets returned")
    except Exception as e:
        print(f"  [X] ERROR: {e}")
    print()

    # Test 2: Find geopolitical markets
    print("[2/4] Testing geopolitical market filtering...")
    try:
        geo_markets = client.get_geopolitical_markets(limit=20)
        print(f"  [+] Found {len(geo_markets)} geopolitical markets")
        if geo_markets:
            for i, market in enumerate(geo_markets[:3], 1):
                print(f"    {i}. {market.get('question', 'Unknown')[:70]}")
    except Exception as e:
        print(f"  [X] ERROR: {e}")
    print()

    # Test 3: Fetch recent trades
    print("[3/4] Testing get_trades()...")
    try:
        trades = client.get_trades(limit=20)
        if trades:
            print(f"  [+] SUCCESS: Fetched {len(trades)} recent trades")
            # Try to find large trades
            large_trades = [t for t in trades if client.calculate_bet_size_usd(t) >= 1000]
            if large_trades:
                print(f"  [+] Found {len(large_trades)} trades over $1,000")
        else:
            print("  [-] No trades returned")
    except Exception as e:
        print(f"  [X] ERROR: {e}")
    print()

    # Test 4: Test market categorization
    print("[4/4] Testing market categorization...")
    try:
        test_markets = [
            {'question': 'Will Maduro be arrested?', 'tags': []},
            {'question': 'Bitcoin to $100k?', 'tags': ['crypto']},
            {'question': 'Military operation in Iran?', 'tags': ['world']},
        ]

        for market in test_markets:
            category = client.categorize_market(market)
            question = market['question'][:50]
            print(f"  {question:<52} -> {category}")
    except Exception as e:
        print(f"  [X] ERROR: {e}")
    print()

    print("=" * 60)
    print("Test Complete!")
    print("=" * 60)


if __name__ == '__main__':
    test_api_connection()
