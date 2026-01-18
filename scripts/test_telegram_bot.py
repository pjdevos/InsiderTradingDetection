"""
Test script for Telegram bot

Tests alert message formatting and delivery (if configured).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime, timezone
from alerts import get_telegram_bot, send_trade_alert
from alerts.templates import telegram_alert_message


def test_message_formatting():
    """Test alert message formatting"""
    print("\n" + "="*70)
    print("TELEGRAM BOT MESSAGE FORMATTING TEST")
    print("="*70)

    # Create mock trade data
    mock_trade = {
        'transaction_hash': '0x' + 'a' * 64,
        'wallet_address': '0x' + 'b' * 40,
        'bet_size_usd': 150000,
        'bet_direction': 'YES',
        'bet_price': 0.85,
        'timestamp': datetime.now(timezone.utc),
        'market_title': 'Will there be a military conflict with Iran in January 2026?',
        'market': {
            'question': 'Will there be a military conflict with Iran in January 2026?',
            'category': 'Politics'
        }
    }

    # Create mock scoring result
    mock_scoring = {
        'total_score': 72,
        'raw_score': 119,
        'alert_level': 'SUSPICIOUS',
        'breakdown': {
            'bet_size': {
                'score': 25,
                'max': 30,
                'reason': 'Very large bet ($150,000)'
            },
            'wallet_history': {
                'score': 15,
                'max': 40,
                'reason': 'New wallet (0 days)'
            },
            'market_category': {
                'score': 15,
                'max': 15,
                'reason': 'Geopolitical market (Politics)'
            },
            'timing': {
                'score': 15,
                'max': 15,
                'reason': 'Weekend trade (Saturday); Off-hours trade (03:00)'
            },
            'price_conviction': {
                'score': 12,
                'max': 15,
                'reason': 'Strong conviction YES at 0.85'
            },
            'pizzint': {
                'score': 0,
                'max': 30,
                'reason': 'PizzINT correlation not yet implemented'
            },
            'market_metadata': {
                'score': 18,
                'max': 20,
                'reason': 'New market; Low liquidity'
            }
        }
    }

    print("\n1. Testing message formatting...")
    message = telegram_alert_message(mock_trade, mock_scoring)

    print("\n" + "-"*70)
    print("FORMATTED MESSAGE:")
    print("-"*70)
    print(message)
    print("-"*70)

    print("\n[OK] Message formatted successfully")
    print(f"   Length: {len(message)} characters")
    print(f"   Alert Level: {mock_scoring['alert_level']}")
    print(f"   Score: {mock_scoring['total_score']}/100")

    return message


def test_bot_connection():
    """Test bot connection and configuration"""
    print("\n2. Testing bot configuration...")

    bot = get_telegram_bot()

    if not bot.is_configured():
        print("\n[WARN] Telegram bot not configured")
        print("   Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env to enable")
        print("\n   To get a bot token:")
        print("   1. Talk to @BotFather on Telegram")
        print("   2. Send /newbot and follow instructions")
        print("   3. Copy the token to .env")
        print("\n   To get your chat ID:")
        print("   1. Start a chat with your bot")
        print("   2. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("   3. Look for 'chat':{'id': YOUR_CHAT_ID}")
        return False

    print("\n[OK] Telegram bot configured")
    print(f"   Token: {bot.bot_token[:20]}...")
    print(f"   Chat ID: {bot.chat_id}")

    return True


def test_alert_sending():
    """Test sending a test alert (requires configuration)"""
    print("\n3. Testing alert delivery...")

    bot = get_telegram_bot()

    if not bot.is_configured():
        print("\n[SKIP] Bot not configured, skipping delivery test")
        return False

    # Create test trade
    test_trade = {
        'transaction_hash': '0x' + 'test' * 16,
        'wallet_address': '0x' + 'test' * 10,
        'bet_size_usd': 75000,
        'bet_direction': 'YES',
        'bet_price': 0.70,
        'timestamp': datetime.now(timezone.utc),
        'market_title': 'TEST: This is a test alert from the Geopolitical Insider Trading Detection System',
        'market': {
            'question': 'TEST: This is a test alert',
            'category': 'Test'
        }
    }

    test_scoring = {
        'total_score': 60,
        'alert_level': 'WATCH',
        'breakdown': {
            'bet_size': {
                'score': 20,
                'max': 30,
                'reason': 'Large bet ($75,000)'
            },
            'wallet_history': {
                'score': 15,
                'max': 40,
                'reason': 'Test wallet'
            },
            'market_category': {
                'score': 15,
                'max': 15,
                'reason': 'Test market'
            },
            'timing': {
                'score': 10,
                'max': 15,
                'reason': 'Test timing'
            },
            'price_conviction': {
                'score': 0,
                'max': 15,
                'reason': 'Following consensus'
            },
            'pizzint': {
                'score': 0,
                'max': 30,
                'reason': 'Not implemented'
            },
            'market_metadata': {
                'score': 0,
                'max': 20,
                'reason': 'Normal market'
            }
        }
    }

    print("\n   Attempting to send test alert...")
    print("   (Check your Telegram for the message)")

    try:
        success = send_trade_alert(
            test_trade,
            test_scoring,
            respect_rate_limit=False  # Ignore rate limits for test
        )

        if success:
            print("\n[OK] Test alert sent successfully!")
            print("   Check your Telegram app for the message")
            return True
        else:
            print("\n[FAIL] Failed to send test alert")
            print("   Check logs for details")
            return False

    except Exception as e:
        print(f"\n[ERROR] Exception while sending alert: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("TELEGRAM BOT TEST SUITE")
    print("="*70)

    # Test 1: Message formatting
    test_message_formatting()

    # Test 2: Bot configuration
    bot_configured = test_bot_connection()

    # Test 3: Alert sending (only if configured)
    if bot_configured:
        print("\n" + "="*70)
        user_input = input("\nDo you want to send a test alert? (yes/no): ").strip().lower()

        if user_input in ['yes', 'y']:
            test_alert_sending()
        else:
            print("\n[SKIP] Alert sending test skipped by user")

    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)

    if not bot_configured:
        print("\nTo enable Telegram alerts:")
        print("1. Set TELEGRAM_BOT_TOKEN in .env (get from @BotFather)")
        print("2. Set TELEGRAM_CHAT_ID in .env (your chat ID)")
        print("3. Run this test again to verify configuration")
    else:
        print("\n[SUCCESS] Telegram bot is configured and ready!")
        print("\nThe bot will now automatically send alerts when:")
        print("  - Suspicion score >= 50 (WATCH)")
        print("  - Suspicion score >= 70 (SUSPICIOUS)")
        print("  - Suspicion score >= 85 (CRITICAL)")


if __name__ == '__main__':
    main()
