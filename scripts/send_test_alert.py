"""
Send a test alert to Telegram with mock trade data
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime, timezone
from alerts import send_trade_alert

def send_test_alert():
    """Send a test alert to verify Telegram delivery"""

    # Create realistic mock trade data
    mock_trade = {
        'transaction_hash': '0x' + 'a' * 64,
        'wallet_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f0a3f1',
        'bet_size_usd': 125000,
        'bet_direction': 'YES',
        'bet_price': 0.88,
        'timestamp': datetime.now(timezone.utc),
        'market_title': 'Will there be a military conflict with Iran in January 2026?',
        'market': {
            'question': 'Will there be a military conflict with Iran in January 2026?',
            'category': 'Politics'
        }
    }

    # Create mock scoring result - CRITICAL level
    mock_scoring = {
        'total_score': 87,
        'raw_score': 144,
        'alert_level': 'CRITICAL',
        'breakdown': {
            'bet_size': {
                'score': 25,
                'max': 30,
                'reason': 'Very large bet ($125,000)'
            },
            'wallet_history': {
                'score': 30,
                'max': 40,
                'reason': 'New wallet (0 days); Mixer funded from Tornado Cash'
            },
            'market_category': {
                'score': 15,
                'max': 15,
                'reason': 'Geopolitical market (Politics)'
            },
            'timing': {
                'score': 15,
                'max': 15,
                'reason': 'Weekend trade (Saturday); Off-hours trade (03:15 AM)'
            },
            'price_conviction': {
                'score': 12,
                'max': 15,
                'reason': 'Strong conviction YES at 0.88'
            },
            'pizzint': {
                'score': 0,
                'max': 30,
                'reason': 'PizzINT correlation not yet implemented'
            },
            'market_metadata': {
                'score': 18,
                'max': 20,
                'reason': 'New market (created 6 hours ago); Low liquidity ($8.5K)'
            }
        }
    }

    print("Sending test CRITICAL alert to your Telegram...")
    print(f"Alert Level: {mock_scoring['alert_level']}")
    print(f"Suspicion Score: {mock_scoring['total_score']}/100")
    print(f"Bet Size: ${mock_trade['bet_size_usd']:,.0f}")
    print(f"Market: {mock_trade['market_title'][:60]}...")
    print()

    try:
        # Send the alert (bypassing rate limits for test)
        success = send_trade_alert(
            mock_trade,
            mock_scoring,
            respect_rate_limit=False  # Bypass rate limits for testing
        )

        if success:
            print("=" * 70)
            print("SUCCESS! Test alert sent to your Telegram!")
            print("=" * 70)
            print()
            print("Check your Telegram app (@pjdevos) - you should see:")
            print("  - A message with CRITICAL ALERT emoji (red siren)")
            print("  - Suspicion score: 87/100")
            print("  - Trade details (bet size, direction, wallet)")
            print("  - Market information")
            print("  - Top scoring factors breakdown")
            print()
            print("If you received the message, your Telegram bot is working perfectly!")
            return True
        else:
            print("=" * 70)
            print("FAILED - Alert not sent")
            print("=" * 70)
            print()
            print("Possible issues:")
            print("  - Bot token invalid")
            print("  - Chat ID incorrect")
            print("  - Network connectivity")
            print("  - Telegram API down")
            return False

    except Exception as e:
        print("=" * 70)
        print(f"ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print()
    print("=" * 70)
    print("TELEGRAM BOT - MOCK ALERT TEST")
    print("=" * 70)
    print()
    print("This will send a test CRITICAL alert to your Telegram.")
    print("The alert contains realistic mock data to verify formatting.")
    print()

    send_test_alert()

    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
