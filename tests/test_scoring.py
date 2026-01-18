"""
Unit tests for suspicion scoring algorithm
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import unittest
from datetime import datetime, timezone, timedelta
from analysis.scoring import SuspicionScorer


class TestBetSizeScoring(unittest.TestCase):
    """Test Factor 1: Bet Size scoring"""

    def test_small_bet_below_threshold(self):
        """Bets below $10k should score 0"""
        score, reason = SuspicionScorer.score_bet_size(5000)
        self.assertEqual(score, 0)
        self.assertIn("Small bet", reason)

    def test_moderate_bet(self):
        """Bets $10k-$50k should score 10"""
        score, _ = SuspicionScorer.score_bet_size(30000)
        self.assertEqual(score, 10)

    def test_large_bet(self):
        """Bets $50k-$100k should score 20"""
        score, _ = SuspicionScorer.score_bet_size(75000)
        self.assertEqual(score, 20)

    def test_very_large_bet(self):
        """Bets $100k-$250k should score 25"""
        score, _ = SuspicionScorer.score_bet_size(150000)
        self.assertEqual(score, 25)

    def test_huge_bet(self):
        """Bets >$250k should score 30 (max)"""
        score, _ = SuspicionScorer.score_bet_size(500000)
        self.assertEqual(score, 30)


class TestMarketCategoryScoring(unittest.TestCase):
    """Test Factor 3: Market Category scoring"""

    def test_geopolitical_market(self):
        """Geopolitical markets should score 15"""
        score, reason = SuspicionScorer.score_market_category(True, "Politics")
        self.assertEqual(score, 15)
        self.assertIn("Geopolitical", reason)

    def test_non_geopolitical_market(self):
        """Non-geopolitical markets should score 0"""
        score, _ = SuspicionScorer.score_market_category(False, "Sports")
        self.assertEqual(score, 0)


class TestTimingAnomaliesScoring(unittest.TestCase):
    """Test Factor 4: Timing Anomalies scoring"""

    def test_normal_weekday_hours(self):
        """Normal weekday hours should score 0"""
        # Tuesday at 2pm
        timestamp = datetime(2026, 1, 14, 14, 0, tzinfo=timezone.utc)
        score, reason = SuspicionScorer.score_timing_anomalies(timestamp)
        self.assertEqual(score, 0)
        self.assertIn("Normal business hours", reason)

    def test_weekend_trade(self):
        """Weekend trades should add 10 points"""
        # Saturday at 2pm
        timestamp = datetime(2026, 1, 18, 14, 0, tzinfo=timezone.utc)
        score, reason = SuspicionScorer.score_timing_anomalies(timestamp)
        self.assertGreaterEqual(score, 10)
        self.assertIn("Weekend", reason)

    def test_off_hours_trade(self):
        """Off-hours trades should add 8 points"""
        # Tuesday at 2am
        timestamp = datetime(2026, 1, 14, 2, 0, tzinfo=timezone.utc)
        score, reason = SuspicionScorer.score_timing_anomalies(timestamp)
        self.assertEqual(score, 8)
        self.assertIn("Off-hours", reason)

    def test_weekend_off_hours(self):
        """Weekend + off-hours should score high"""
        # Saturday at 3am (Jan 17, 2026 is Saturday)
        timestamp = datetime(2026, 1, 17, 3, 0, tzinfo=timezone.utc)
        score, reason = SuspicionScorer.score_timing_anomalies(timestamp)
        self.assertEqual(score, 15)  # Max for this factor (10 + 8 = 18, capped at 15)


class TestPriceConvictionScoring(unittest.TestCase):
    """Test Factor 5: Price/Conviction scoring"""

    def test_yes_extreme_contrarian(self):
        """YES bet at very high price (>0.85) should score 15"""
        score, reason = SuspicionScorer.score_price_conviction(0.90, 'YES')
        self.assertEqual(score, 15)
        self.assertIn("Extreme conviction", reason)

    def test_yes_following_consensus(self):
        """YES bet at low price (<0.55) should score 0"""
        score, reason = SuspicionScorer.score_price_conviction(0.30, 'YES')
        self.assertEqual(score, 0)
        self.assertIn("Following consensus", reason)

    def test_no_extreme_contrarian(self):
        """NO bet at very low price (<0.15) should score 15"""
        score, reason = SuspicionScorer.score_price_conviction(0.10, 'NO')
        self.assertEqual(score, 15)
        self.assertIn("Extreme conviction", reason)

    def test_no_following_consensus(self):
        """NO bet at high price (>0.45) should score 0"""
        score, reason = SuspicionScorer.score_price_conviction(0.70, 'NO')
        self.assertEqual(score, 0)
        self.assertIn("Following consensus", reason)


class TestMarketMetadataScoring(unittest.TestCase):
    """Test Factor 7: Market Metadata scoring"""

    def test_new_market_low_liquidity(self):
        """New market with low liquidity should score high"""
        market_data = {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'liquidity_usd': 5000,
            'risk_keywords': ['war', 'conflict']
        }
        score, reason = SuspicionScorer.score_market_metadata(market_data)
        self.assertGreaterEqual(score, 18)  # 10 + 8 + 0 (keywords don't stack beyond first)

    def test_established_market(self):
        """Old market with good liquidity should score 0"""
        old_time = datetime.now(timezone.utc) - timedelta(days=30)
        market_data = {
            'created_at': old_time.isoformat(),
            'liquidity_usd': 100000,
            'risk_keywords': []
        }
        score, reason = SuspicionScorer.score_market_metadata(market_data)
        self.assertEqual(score, 0)


class TestCompositeScoring(unittest.TestCase):
    """Test complete scoring calculation"""

    def test_highly_suspicious_trade(self):
        """Test a highly suspicious trade scenario"""
        trade_data = {
            'bet_size_usd': 200000,  # 25 points
            'wallet_address': '0x' + 'a' * 40,
            'timestamp': datetime(2026, 1, 17, 3, 0, tzinfo=timezone.utc),  # Weekend + off-hours: 15 points (Saturday)
            'bet_price': 0.90,  # Extreme contrarian: 15 points
            'bet_direction': 'YES'
        }

        market_data = {
            'is_geopolitical': True,  # 15 points
            'category': 'Politics',
            'created_at': datetime.now(timezone.utc).isoformat(),  # New: 10 points
            'liquidity_usd': 5000,  # Low: 8 points
            'risk_keywords': ['war', 'conflict']  # 5 points
        }

        result = SuspicionScorer.calculate_score(trade_data, market_data)

        # Should be suspicious (without wallet history, score ~50-60)
        # Note: Wallet history would add up to 40 more points if DB was initialized
        self.assertGreater(result['total_score'], 50)
        self.assertIn(result['alert_level'], ['WATCH', 'SUSPICIOUS', 'CRITICAL'])

        # Check all factors contributed
        breakdown = result['breakdown']
        self.assertGreater(breakdown['bet_size']['score'], 0)
        self.assertGreater(breakdown['market_category']['score'], 0)
        self.assertGreater(breakdown['timing']['score'], 0)
        self.assertGreater(breakdown['price_conviction']['score'], 0)
        self.assertGreater(breakdown['market_metadata']['score'], 0)

    def test_normal_trade(self):
        """Test a normal, non-suspicious trade"""
        trade_data = {
            'bet_size_usd': 5000,  # Below threshold: 0 points
            'wallet_address': '0x' + 'b' * 40,
            'timestamp': datetime(2026, 1, 14, 14, 0, tzinfo=timezone.utc),  # Normal hours: 0 points
            'bet_price': 0.45,  # Following consensus: 0 points
            'bet_direction': 'YES'
        }

        market_data = {
            'is_geopolitical': False,  # Non-geo: 0 points
            'category': 'Sports',
            'created_at': (datetime.now(timezone.utc) - timedelta(days=60)).isoformat(),
            'liquidity_usd': 100000,
            'risk_keywords': []
        }

        result = SuspicionScorer.calculate_score(trade_data, market_data)

        # Should be low suspicion
        self.assertLess(result['total_score'], 50)
        self.assertIsNone(result['alert_level'])

    def test_score_normalization(self):
        """Test that scores are properly normalized to 0-100"""
        # Create max scoring trade
        trade_data = {
            'bet_size_usd': 500000,  # Max: 30 points
            'wallet_address': '0x' + 'c' * 40,
            'timestamp': datetime(2026, 1, 18, 3, 0, tzinfo=timezone.utc),  # Max: 15 points
            'bet_price': 0.95,  # Max: 15 points
            'bet_direction': 'YES'
        }

        market_data = {
            'is_geopolitical': True,  # Max: 15 points
            'category': 'Politics',
            'created_at': datetime.now(timezone.utc).isoformat(),  # 10 points
            'liquidity_usd': 1000,  # 8 points
            'risk_keywords': ['war']  # 5 points
        }

        result = SuspicionScorer.calculate_score(trade_data, market_data)

        # Total should be between 0-100
        self.assertGreaterEqual(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)

        # Raw score should be higher (out of 165)
        self.assertGreater(result['raw_score'], result['total_score'])


if __name__ == '__main__':
    unittest.main()
