"""
Test script for Suspicious Wins Detection System

Tests the new Phase 7 components:
1. Market Resolution detection
2. Win/Loss calculation
3. Suspicious Win scoring
"""
import sys
import io
from pathlib import Path

# Fix Windows console encoding for UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import logging
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_price_inference():
    """Test price inference from outcome prices"""
    print("\n" + "="*60)
    print("TEST 1: Price Inference")
    print("="*60 + "\n")

    from blockchain.client import BlockchainClient

    # Test cases
    test_cases = [
        # (outcome_prices, expected_outcome, description)
        ('["0.99", "0.01"]', 'YES', 'YES wins clearly'),
        ('["0.01", "0.99"]', 'NO', 'NO wins clearly'),
        ('["0.50", "0.50"]', None, 'Undetermined (50/50)'),
        ('["0.97", "0.03"]', 'YES', 'YES wins with 97%'),
        ('[\"0.001\", \"0.999\"]', 'NO', 'NO wins with 99.9%'),
    ]

    passed = 0
    for prices, expected, description in test_cases:
        result = BlockchainClient.infer_resolution_from_prices(prices)

        if result:
            actual = result.get('winning_outcome') if result.get('resolved') else None
        else:
            actual = None

        status = "✅ PASS" if actual == expected else "❌ FAIL"
        if actual == expected:
            passed += 1

        print(f"{status}: {description}")
        print(f"  Input: {prices}")
        print(f"  Expected: {expected}, Got: {actual}")
        if result:
            print(f"  Confidence: {result.get('confidence', 0):.4f}")
        print()

    print(f"Result: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_profit_calculation():
    """Test profit/loss calculation"""
    print("\n" + "="*60)
    print("TEST 2: Profit/Loss Calculation")
    print("="*60 + "\n")

    from analysis.win_calculator import WinLossCalculator

    calc = WinLossCalculator()

    # Test cases: (bet_size, bet_price, expected_profit)
    test_cases = [
        (1000, 0.30, 2333.33, "Bet $1000 at 0.30, win -> ~$2333 profit"),
        (1000, 0.50, 1000.00, "Bet $1000 at 0.50, win -> $1000 profit"),
        (1000, 0.80, 250.00, "Bet $1000 at 0.80, win -> $250 profit"),
        (500, 0.10, 4500.00, "Bet $500 at 0.10, win -> $4500 profit"),
    ]

    passed = 0
    for bet_size, bet_price, expected, description in test_cases:
        actual = calc.calculate_profit(bet_size, bet_price)
        diff = abs(actual - expected)

        status = "✅ PASS" if diff < 1 else "❌ FAIL"
        if diff < 1:
            passed += 1

        print(f"{status}: {description}")
        print(f"  Expected: ${expected:,.2f}, Got: ${actual:,.2f}")
        print()

    print(f"Result: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_win_scoring():
    """Test suspicious win scoring logic"""
    print("\n" + "="*60)
    print("TEST 3: Suspicious Win Scoring")
    print("="*60 + "\n")

    from analysis.win_scoring import SuspiciousWinScorer

    scorer = SuspiciousWinScorer()

    # Test scoring thresholds
    print("Scoring weights:")
    for factor, weight in scorer.WEIGHTS.items():
        print(f"  {factor}: {weight} points")
    print()

    # Test alert thresholds
    print("Alert thresholds:")
    from analysis.win_scoring import WIN_ALERT_THRESHOLDS
    for level, threshold in WIN_ALERT_THRESHOLDS.items():
        print(f"  {level}: {threshold}+ points")
    print()

    # Test alert level mapping
    test_scores = [45, 55, 72, 88]
    print("Alert level mapping:")
    for score in test_scores:
        level = scorer._get_alert_level(score)
        print(f"  Score {score} -> {level or 'None'}")

    print("\n✅ Win scoring module loaded successfully")
    return True


def test_models():
    """Test database models"""
    print("\n" + "="*60)
    print("TEST 4: Database Models")
    print("="*60 + "\n")

    try:
        from database.models import MarketResolution, WalletWinHistory, Trade, WalletMetrics

        print("✅ MarketResolution model imported")
        print("✅ WalletWinHistory model imported")
        print("✅ Trade model (with new fields) imported")
        print("✅ WalletMetrics model (with new fields) imported")

        # Check new Trade fields
        assert hasattr(Trade, 'trade_result'), "Trade missing trade_result field"
        assert hasattr(Trade, 'profit_loss_usd'), "Trade missing profit_loss_usd field"
        assert hasattr(Trade, 'hours_before_resolution'), "Trade missing hours_before_resolution field"
        print("✅ Trade model has new win tracking fields")

        # Check new WalletMetrics fields
        assert hasattr(WalletMetrics, 'geopolitical_wins'), "WalletMetrics missing geopolitical_wins"
        assert hasattr(WalletMetrics, 'suspicious_win_score'), "WalletMetrics missing suspicious_win_score"
        print("✅ WalletMetrics model has new win tracking fields")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_resolution_monitor():
    """Test resolution monitor initialization"""
    print("\n" + "="*60)
    print("TEST 5: Resolution Monitor")
    print("="*60 + "\n")

    try:
        from api.resolution_monitor import ResolutionMonitor, get_resolution_monitor

        # Test initialization
        monitor = ResolutionMonitor(poll_interval_minutes=30)
        print(f"✅ ResolutionMonitor initialized")
        print(f"  Poll interval: {monitor.poll_interval}s")
        print(f"  Resolution threshold: {monitor.resolution_threshold}")

        # Test singleton
        singleton = get_resolution_monitor()
        print("✅ Singleton accessor works")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alert_templates():
    """Test alert message templates"""
    print("\n" + "="*60)
    print("TEST 6: Alert Templates")
    print("="*60 + "\n")

    try:
        from alerts.templates import telegram_win_alert_message, email_win_alert_html

        # Mock scoring result
        mock_result = {
            'total_score': 75,
            'alert_level': 'SUSPICIOUS_WIN',
            'breakdown': {
                'win_rate_anomaly': {'score': 25, 'max': 30, 'reason': 'Very high win rate: 75%'},
                'timing_pattern': {'score': 20, 'max': 25, 'reason': '60% late bets'},
                'geopolitical_accuracy': {'score': 15, 'max': 20, 'reason': '80% geo accuracy'},
            },
            'stats': {
                'wins': 15,
                'losses': 5,
                'win_rate': 0.75,
                'geo_win_rate': 0.80,
                'total_profit_loss': 25000,
                'avg_hours_before_resolution': 36
            }
        }

        # Test Telegram message
        telegram_msg = telegram_win_alert_message(
            "0x1234567890abcdef1234567890abcdef12345678",
            mock_result
        )
        print("✅ Telegram win alert message generated")
        print(f"  Length: {len(telegram_msg)} chars")

        # Test HTML email
        html_msg = email_win_alert_html(
            "0x1234567890abcdef1234567890abcdef12345678",
            mock_result
        )
        print("✅ HTML win alert email generated")
        print(f"  Length: {len(html_msg)} chars")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SUSPICIOUS WINS DETECTION - COMPONENT TESTS")
    print("="*60)

    results = []

    results.append(("Price Inference", test_price_inference()))
    results.append(("Profit Calculation", test_profit_calculation()))
    results.append(("Win Scoring", test_win_scoring()))
    results.append(("Database Models", test_models()))
    results.append(("Resolution Monitor", test_resolution_monitor()))
    results.append(("Alert Templates", test_alert_templates()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60 + "\n")

    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        if result:
            passed += 1
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n🎉 All tests passed! Suspicious wins detection is ready.")
        return True
    else:
        print("\n⚠️ Some tests failed. Check the output above.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
