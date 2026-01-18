"""
Demo script for Advanced Wallet Pattern Analysis

Demonstrates the pattern detection capabilities:
- Wallet profiling
- Repeat offender detection
- Network pattern analysis
- Temporal pattern detection
- Win rate anomaly detection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from database.connection import init_db
from analysis.patterns import (
    analyze_wallet,
    find_repeat_offenders,
    find_suspicious_networks,
    WalletPatternAnalyzer
)


def demo_wallet_profile(wallet_address: str):
    """Demonstrate wallet profiling"""
    print("\n" + "="*70)
    print(f"WALLET PROFILE ANALYSIS: {wallet_address[:10]}...{wallet_address[-6:]}")
    print("="*70)

    analysis = analyze_wallet(wallet_address)

    if not analysis['profile']:
        print("No trading history found for this wallet.")
        return

    profile = analysis['profile']

    print(f"\nTrading Activity:")
    print(f"  Total Trades: {profile.total_trades}")
    print(f"  Suspicious Trades: {profile.suspicious_trades}")
    print(f"  Average Suspicion Score: {profile.avg_suspicion_score:.1f}/100")
    print(f"  Markets Traded: {profile.markets_traded}")

    print(f"\nPerformance Metrics:")
    print(f"  Win Rate (Proxy): {profile.win_rate:.1%}")
    print(f"  Average Bet Size: ${profile.avg_bet_size:,.2f}")

    print(f"\nTiming Patterns:")
    print(f"  Off-Hours Trading: {profile.off_hours_ratio:.1%}")
    print(f"  Weekend Trading: {profile.weekend_ratio:.1%}")

    print(f"\nWallet Age:")
    print(f"  Age: {profile.wallet_age_days} days")
    print(f"  First Trade: {profile.first_trade_date.strftime('%Y-%m-%d')}")
    print(f"  Last Trade: {profile.last_trade_date.strftime('%Y-%m-%d')}")

    # Temporal patterns
    if analysis['temporal_patterns']:
        print(f"\nTemporal Patterns Detected:")
        for pattern in analysis['temporal_patterns']:
            print(f"  - {pattern.pattern_type}: {pattern.description}")
            print(f"    Confidence: {pattern.confidence_score:.1%}")
    else:
        print(f"\nNo significant temporal patterns detected.")

    # Win rate anomaly
    if analysis['win_rate_anomaly']:
        anomaly = analysis['win_rate_anomaly']
        print(f"\nWin Rate Anomaly Detected!")
        print(f"  Observed: {anomaly['observed_win_rate']:.1%}")
        print(f"  Expected: {anomaly['baseline_win_rate']:.1%}")
        print(f"  Deviation: {anomaly['deviation']:.1%}")
        print(f"  Anomaly Score: {anomaly['anomaly_score']:.1f}/100")
    else:
        print(f"\nNo win rate anomalies detected.")


def demo_repeat_offenders(days: int = 30):
    """Demonstrate repeat offender detection"""
    print("\n" + "="*70)
    print(f"REPEAT OFFENDER DETECTION (Last {days} days)")
    print("="*70)

    offenders = find_repeat_offenders(days=days)

    if not offenders:
        print(f"\nNo repeat offenders found in the last {days} days.")
        print("This is actually good news - no wallets with multiple suspicious trades!")
        return

    print(f"\nFound {len(offenders)} repeat offenders:\n")

    for i, profile in enumerate(offenders[:10], 1):  # Show top 10
        print(f"{i}. Wallet: {profile.wallet_address[:10]}...{profile.wallet_address[-6:]}")
        print(f"   Suspicious Trades: {profile.suspicious_trades}/{profile.total_trades}")
        print(f"   Avg Suspicion Score: {profile.avg_suspicion_score:.1f}/100")
        print(f"   Total Volume: ${profile.avg_bet_size * profile.total_trades:,.2f}")
        print(f"   Wallet Age: {profile.wallet_age_days} days")
        print()


def demo_network_patterns(days: int = 7):
    """Demonstrate network pattern detection"""
    print("\n" + "="*70)
    print(f"NETWORK PATTERN DETECTION (Last {days} days)")
    print("="*70)

    patterns = find_suspicious_networks(days=days)

    if not patterns:
        print(f"\nNo coordinated trading networks found in the last {days} days.")
        print("No evidence of collusion or coordinated activity detected.")
        return

    print(f"\nFound {len(patterns)} suspicious networks:\n")

    for i, pattern in enumerate(patterns[:10], 1):  # Show top 10
        print(f"{i}. Market: {pattern.market_title[:60]}")
        print(f"   Wallets Involved: {len(pattern.wallets)}")
        print(f"   Time Window: {pattern.time_window_minutes} minutes")
        print(f"   Total Trades: {pattern.trade_count}")
        print(f"   Combined Volume: ${pattern.total_volume:,.2f}")
        print(f"   Avg Suspicion Score: {pattern.avg_suspicion_score:.1f}/100")
        print(f"   Pattern Type: {pattern.pattern_type}")
        print(f"   Wallets: {', '.join(w[:10] + '...' for w in pattern.wallets[:3])}")
        print()


def demo_comprehensive_analysis():
    """Run comprehensive pattern analysis"""
    print("\n" + "="*70)
    print("ADVANCED WALLET PATTERN ANALYSIS - COMPREHENSIVE DEMO")
    print("="*70)

    print("\nThis demo showcases the advanced pattern detection features:")
    print("1. Wallet profiling (trading behavior analysis)")
    print("2. Repeat offender detection (multiple suspicious trades)")
    print("3. Network pattern detection (coordinated trading)")
    print("4. Temporal pattern recognition (timing anomalies)")
    print("5. Win rate anomaly detection (statistical outliers)")

    # Demo 1: Repeat offenders
    demo_repeat_offenders(days=30)

    # Demo 2: Network patterns
    demo_network_patterns(days=7)

    # Demo 3: If there are any wallets in the database, analyze them
    from database.storage import DataStorageService
    from database.connection import get_db_session

    with get_db_session() as session:
        from database.models import Trade
        from sqlalchemy import func

        # Get top wallets by trade count
        top_wallets = session.query(
            Trade.wallet_address,
            func.count(Trade.id).label('trade_count')
        ).group_by(Trade.wallet_address)\
         .order_by(func.count(Trade.id).desc())\
         .limit(3)\
         .all()

        if top_wallets:
            print("\n" + "="*70)
            print("SAMPLE WALLET ANALYSES")
            print("="*70)

            for wallet_address, trade_count in top_wallets:
                if trade_count >= 2:  # Only analyze wallets with some activity
                    demo_wallet_profile(wallet_address)
        else:
            print("\n" + "="*70)
            print("NO WALLETS IN DATABASE YET")
            print("="*70)
            print("\nStart monitoring Polymarket to collect trading data,")
            print("then run this demo again to see pattern analysis in action!")

    print("\n" + "="*70)
    print("DEMO COMPLETE")
    print("="*70)
    print("\nWhat These Features Enable:")
    print("  - Identify wallets with repeated suspicious behavior")
    print("  - Detect coordinated trading (potential collusion)")
    print("  - Recognize timing patterns (crisis trading, early birds)")
    print("  - Flag statistical anomalies (impossibly high win rates)")
    print("  - Build behavioral profiles for investigation")
    print("\nThese patterns are now integrated into the scoring algorithm,")
    print("boosting suspicion scores for wallets with concerning patterns!")


if __name__ == '__main__':
    # Initialize database
    init_db()

    # Run comprehensive demo
    demo_comprehensive_analysis()
