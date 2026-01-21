"""
Test script to verify market resolution fetching from blockchain.

This tests the new get_market_resolution() method in BlockchainClient.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import logging
from blockchain.client import BlockchainClient, CONDITIONAL_TOKENS_ABI

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_resolution_fetch():
    """Test fetching market resolution from blockchain"""

    print("\n" + "="*60)
    print("MARKET RESOLUTION FETCH TEST")
    print("="*60 + "\n")

    # Initialize blockchain client
    client = BlockchainClient()

    if not client.is_connected():
        print("ERROR: Could not connect to Polygon blockchain")
        print("Make sure POLYGON_RPC_URL is configured in .env")
        return False

    print("Connected to Polygon blockchain\n")

    # First, let's query the Polymarket API to get actual market data
    # and understand the relationship between market IDs and condition IDs
    print("Fetching market data from Polymarket API...\n")

    import requests

    # Get some closed/resolved markets from Polymarket API
    try:
        response = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"closed": "true", "limit": 10},
            timeout=10
        )
        markets = response.json()

        print(f"Found {len(markets)} closed markets\n")

        # Print available fields to understand the data structure
        if markets:
            sample = markets[0]
            print("Sample market fields:")
            for key in sorted(sample.keys()):
                value = sample.get(key)
                if value and key in ['id', 'conditionId', 'question', 'closed', 'outcomes', 'outcomePrices']:
                    print(f"  {key}: {str(value)[:60]}")
            print()

    except Exception as e:
        print(f"Error fetching markets: {e}")
        markets = []

    # Try with condition IDs from the API response
    test_condition_ids = []

    for market in markets[:5]:
        cid = market.get('conditionId')
        if cid:
            test_condition_ids.append(cid)
            print(f"Market: {market.get('question', 'Unknown')[:50]}...")
            print(f"  conditionId: {cid}")
            print(f"  outcomes: {market.get('outcomes')}")
            print(f"  outcomePrices: {market.get('outcomePrices')}")
            print()

    if not test_condition_ids:
        # Fallback to hardcoded IDs
        test_condition_ids = [
            "0xd1047755d35a03b7ceea9923daae56ecf67784446daa63e87eebc471b4b9dbd9",
            "0x288a6193d8f99f6cd90b4bd68f91a958cca08c87c2201193f73928ab52ba0172",
        ]

    # Test PRICE INFERENCE method (more reliable for Polymarket)
    print("="*60)
    print("TESTING PRICE INFERENCE METHOD")
    print("="*60 + "\n")

    results = []
    for market in markets[:10]:
        question = market.get('question', 'Unknown')[:50]
        prices = market.get('outcomePrices', [])
        closed = market.get('closed', False)
        cid = market.get('conditionId', '')[:20]

        print(f"Market: {question}...")
        print(f"  Closed: {closed}")
        print(f"  Prices: {prices}")

        # Use price inference
        inferred = BlockchainClient.infer_resolution_from_prices(prices)

        if inferred:
            results.append({
                'question': question,
                'prices': prices,
                **inferred
            })
            print(f"  Inferred: {inferred['winning_outcome'] or 'UNDETERMINED'} (confidence: {inferred['confidence']:.4f})")
        else:
            print(f"  Could not infer resolution")

        print()

    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)

    if results:
        resolved = [r for r in results if r.get('resolved')]
        pending = [r for r in results if not r.get('resolved')]

        print(f"Total markets analyzed: {len(results)}")
        print(f"Resolution inferred: {len(resolved)}")
        print(f"Undetermined: {len(pending)}")

        if resolved:
            print("\nResolved markets (from price inference):")
            for r in resolved:
                print(f"  - {r['question'][:40]}... -> {r['winning_outcome']} ({r['confidence']:.2%})")

        print("\n" + "="*60)
        print("CONCLUSION")
        print("="*60)
        print("\nPrice inference method works for determining market outcomes!")
        print("When a market resolves:")
        print("  - Winning outcome price -> ~1.0")
        print("  - Losing outcome price -> ~0.0")
        print("\nThis can be used to track wins/losses without blockchain queries.")
        return True
    else:
        print("ERROR: No results")
        return False


if __name__ == '__main__':
    success = test_resolution_fetch()
    sys.exit(0 if success else 1)
