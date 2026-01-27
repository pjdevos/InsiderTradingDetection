"""
Suspicion Scoring Algorithm for Geopolitical Insider Trading Detection

Implements a 7-factor scoring system to identify potentially suspicious trades:
1. Bet Size (30 points) - Larger bets indicate higher confidence/insider knowledge
2. Wallet History (40 points) - New wallets, unusual patterns, high accuracy
3. Market Category (15 points) - Geopolitical markets are higher risk
4. Timing Anomalies (15 points) - Off-hours, weekend trading
5. Price/Conviction (15 points) - Betting against market consensus
6. PizzINT Correlation (30 points) - NOT YET IMPLEMENTED (deferred to future phase)
7. Market Metadata (20 points) - New markets, low liquidity, high risk keywords

Total: 135 points currently implemented (normalized to 0-100 scale)
Note: Will be 165 points when PizzINT correlation is added

Phase 4 Enhancement: Blockchain verification integrated into wallet history scoring
Phase 3.5 Enhancement: Advanced pattern detection integrated (repeat offenders, temporal patterns)
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from database.storage import DataStorageService

logger = logging.getLogger(__name__)


class SuspicionScorer:
    """
    Calculates suspicion scores for trades based on multiple factors
    """

    # Scoring weights (max points per factor)
    WEIGHT_BET_SIZE = 30
    WEIGHT_WALLET_HISTORY = 40
    WEIGHT_MARKET_CATEGORY = 15
    WEIGHT_TIMING = 15
    WEIGHT_PRICE_CONVICTION = 15
    WEIGHT_PIZZINT = 30  # Deferred to later phase (not counted in MAX_SCORE until implemented)
    WEIGHT_MARKET_METADATA = 20

    # Total possible points (excluding PizzINT until implemented)
    MAX_SCORE = 135  # Will be 165 when PizzINT is added

    # Bet size thresholds (USD)
    BET_THRESHOLD_SMALL = 10000
    BET_THRESHOLD_MEDIUM = 50000
    BET_THRESHOLD_LARGE = 100000
    BET_THRESHOLD_HUGE = 250000

    # Wallet history thresholds
    NEW_WALLET_DAYS = 7
    YOUNG_WALLET_DAYS = 30
    HIGH_WIN_RATE_THRESHOLD = 0.70
    SUSPICIOUS_WIN_RATE_THRESHOLD = 0.80

    # Market metadata thresholds
    NEW_MARKET_HOURS = 48
    LOW_LIQUIDITY_THRESHOLD = 10000

    # Timing thresholds (business hours: 9am-9pm)
    BUSINESS_HOURS_START = 9
    BUSINESS_HOURS_END = 21

    @staticmethod
    def score_bet_size(bet_size_usd: float) -> Tuple[float, str]:
        """
        Factor 1: Bet Size (30 points max)

        Larger bets indicate higher confidence, potentially from insider knowledge.

        Scoring:
        - <$10k: 0 points (below threshold)
        - $10k-$50k: 10 points (moderate)
        - $50k-$100k: 20 points (large)
        - $100k-$250k: 25 points (very large)
        - >$250k: 30 points (huge)

        Args:
            bet_size_usd: Bet size in USD

        Returns:
            (score, reasoning)
        """
        if bet_size_usd < SuspicionScorer.BET_THRESHOLD_SMALL:
            return 0, f"Small bet (${bet_size_usd:,.0f})"
        elif bet_size_usd < SuspicionScorer.BET_THRESHOLD_MEDIUM:
            return 10, f"Moderate bet (${bet_size_usd:,.0f})"
        elif bet_size_usd < SuspicionScorer.BET_THRESHOLD_LARGE:
            return 20, f"Large bet (${bet_size_usd:,.0f})"
        elif bet_size_usd < SuspicionScorer.BET_THRESHOLD_HUGE:
            return 25, f"Very large bet (${bet_size_usd:,.0f})"
        else:
            return 30, f"Huge bet (${bet_size_usd:,.0f})"

    @staticmethod
    def score_wallet_history(wallet_address: str, use_blockchain: bool = False) -> Tuple[float, str]:
        """
        Factor 2: Wallet History (40 points max)

        Analyzes wallet trading patterns, history, and performance.

        Scoring factors:
        - New wallet (<7 days): +15 points
        - Young wallet (<30 days): +10 points
        - High win rate (>70%): +10 points
        - Suspicious win rate (>80%): +15 points
        - Off-hours trading (>50%): +5 points
        - Weekend trading (>50%): +5 points
        - Low trade count (<5 trades): +5 points
        - Mixer funded (blockchain verification): +15 points (Phase 4)

        Args:
            wallet_address: Ethereum wallet address
            use_blockchain: Whether to use blockchain verification (slower but more accurate)

        Returns:
            (score, reasoning)
        """
        if not wallet_address or not isinstance(wallet_address, str) or len(wallet_address.strip()) != 42:
            return 0, "Unknown wallet (no valid address)"

        try:
            metrics = DataStorageService.get_wallet_metrics(wallet_address)

            if not metrics:
                # No history - brand new wallet
                return 15, "Brand new wallet (no history)"

            score = 0
            reasons = []

            # Check wallet age (enhanced with blockchain if enabled)
            wallet_age_days = metrics.wallet_age_days

            if use_blockchain:
                try:
                    from blockchain.client import get_blockchain_client
                    blockchain = get_blockchain_client()

                    if blockchain.is_connected():
                        # Get actual wallet age from blockchain
                        age_result = blockchain.get_wallet_age(wallet_address)
                        if age_result:
                            blockchain_age_days, first_tx_date = age_result
                            wallet_age_days = blockchain_age_days
                            reasons.append(f"Blockchain verified age: {blockchain_age_days} days")

                        # Check for mixer funding
                        mixer_result = blockchain.detect_mixer_funding(wallet_address, depth=1)
                        if mixer_result and mixer_result['mixer_funded']:
                            score += 15
                            mixer_names = [m['mixer_name'] for m in mixer_result['mixers_detected']]
                            reasons.append(f"Mixer funded: {', '.join(mixer_names)}")

                except Exception as e:
                    logger.debug(f"Blockchain verification failed: {e}")

            if wallet_age_days is not None:
                if wallet_age_days < SuspicionScorer.NEW_WALLET_DAYS:
                    score += 15
                    reasons.append(f"New wallet ({wallet_age_days} days)")
                elif wallet_age_days < SuspicionScorer.YOUNG_WALLET_DAYS:
                    score += 10
                    reasons.append(f"Young wallet ({wallet_age_days} days)")

            # Check win rate
            if metrics.win_rate is not None:
                if metrics.win_rate >= SuspicionScorer.SUSPICIOUS_WIN_RATE_THRESHOLD:
                    score += 15
                    reasons.append(f"Suspicious win rate ({metrics.win_rate:.1%})")
                elif metrics.win_rate >= SuspicionScorer.HIGH_WIN_RATE_THRESHOLD:
                    score += 10
                    reasons.append(f"High win rate ({metrics.win_rate:.1%})")

            # Check timing patterns
            if metrics.total_trades > 0:
                off_hours_pct = (metrics.trades_outside_hours or 0) / metrics.total_trades
                weekend_pct = (metrics.weekend_trades or 0) / metrics.total_trades

                if off_hours_pct > 0.5:
                    score += 5
                    reasons.append(f"Frequent off-hours trading ({off_hours_pct:.0%})")

                if weekend_pct > 0.5:
                    score += 5
                    reasons.append(f"Frequent weekend trading ({weekend_pct:.0%})")

            # Check trade count
            if metrics.total_trades < 5:
                score += 5
                reasons.append(f"Low trade count ({metrics.total_trades})")

            # Advanced pattern detection (if wallet has enough history)
            if metrics.total_trades >= 5:
                try:
                    from analysis.patterns import WalletPatternAnalyzer
                    from database.connection import get_db_session

                    with get_db_session() as session:
                        # Detect temporal patterns
                        temporal_patterns = WalletPatternAnalyzer.detect_temporal_patterns(
                            session, wallet_address
                        )

                        for pattern in temporal_patterns:
                            if pattern.pattern_type == 'crisis_trader':
                                score += 8
                                reasons.append(f"Crisis trader pattern: {pattern.description}")
                            elif pattern.pattern_type == 'early_bird':
                                score += 6
                                reasons.append(f"Early bird pattern: {pattern.description}")
                            elif pattern.pattern_type == 'night_owl':
                                score += 3
                                reasons.append(f"Night owl pattern detected")

                        # Check if wallet is a repeat offender
                        repeat_offenders = WalletPatternAnalyzer.detect_repeat_offenders(
                            session,
                            min_suspicious_trades=2,
                            min_avg_score=60,
                            days=30
                        )

                        if any(w.wallet_address == wallet_address for w in repeat_offenders):
                            score += 10
                            reasons.append("Repeat offender (multiple suspicious trades)")

                except Exception as e:
                    logger.debug(f"Advanced pattern detection failed: {e}")

            reasoning = "; ".join(reasons) if reasons else "Established wallet with normal patterns"
            return min(score, SuspicionScorer.WEIGHT_WALLET_HISTORY), reasoning

        except Exception as e:
            logger.error(f"Error scoring wallet history: {e}")
            return 0, "Error analyzing wallet"

    @staticmethod
    def score_market_category(is_geopolitical: bool, category: str = None) -> Tuple[float, str]:
        """
        Factor 3: Market Category (15 points max)

        Geopolitical markets are the primary focus for insider trading detection.

        Scoring:
        - Geopolitical market: 15 points
        - Other categories: 0 points

        Args:
            is_geopolitical: Whether market is categorized as geopolitical
            category: Market category name

        Returns:
            (score, reasoning)
        """
        if is_geopolitical:
            return 15, f"Geopolitical market ({category or 'Politics'})"
        else:
            return 0, f"Non-geopolitical market ({category or 'Other'})"

    @staticmethod
    def score_timing_anomalies(timestamp: datetime) -> Tuple[float, str]:
        """
        Factor 4: Timing Anomalies (15 points max)

        Trades placed during off-hours or weekends may indicate insider activity.

        Scoring:
        - Weekend trade: +10 points
        - Off-hours (before 9am or after 9pm): +8 points
        - Normal hours: 0 points

        Args:
            timestamp: Trade timestamp (timezone-aware)

        Returns:
            (score, reasoning)
        """
        score = 0
        reasons = []

        # Check if weekend (Saturday=5, Sunday=6)
        weekday = timestamp.weekday()
        if weekday >= 5:
            score += 10
            day_name = "Saturday" if weekday == 5 else "Sunday"
            reasons.append(f"Weekend trade ({day_name})")

        # Check if off-hours
        hour = timestamp.hour
        if hour < SuspicionScorer.BUSINESS_HOURS_START or hour >= SuspicionScorer.BUSINESS_HOURS_END:
            score += 8
            reasons.append(f"Off-hours trade ({hour:02d}:00)")

        reasoning = "; ".join(reasons) if reasons else "Normal business hours"
        return min(score, SuspicionScorer.WEIGHT_TIMING), reasoning

    @staticmethod
    def score_price_conviction(bet_price: float, bet_direction: str) -> Tuple[float, str]:
        """
        Factor 5: Price/Conviction (15 points max)

        Betting against market consensus (at unfavorable odds) suggests strong conviction,
        potentially from insider knowledge.

        Price interpretation:
        - Price represents probability of YES outcome (0.0 to 1.0)
        - Buying YES at high price (>0.70) = betting against crowd
        - Buying NO at low price (<0.30) = betting against crowd

        Scoring:
        - Extreme contrarian (price >0.85 or <0.15): 15 points
        - Strong contrarian (price >0.75 or <0.25): 12 points
        - Moderate contrarian (price >0.65 or <0.35): 8 points
        - Mild contrarian (price >0.55 or <0.45): 4 points
        - Following consensus: 0 points

        Args:
            bet_price: Market price at time of bet (0.0 to 1.0)
            bet_direction: 'YES' or 'NO'

        Returns:
            (score, reasoning)
        """
        if bet_direction == 'YES':
            # Buying YES at high price = strong conviction against crowd
            if bet_price >= 0.85:
                return 15, f"Extreme conviction YES at {bet_price:.2f}"
            elif bet_price >= 0.75:
                return 12, f"Strong conviction YES at {bet_price:.2f}"
            elif bet_price >= 0.65:
                return 8, f"Moderate conviction YES at {bet_price:.2f}"
            elif bet_price >= 0.55:
                return 4, f"Mild conviction YES at {bet_price:.2f}"
            else:
                return 0, f"Following consensus YES at {bet_price:.2f}"
        else:  # NO
            # Buying NO at low price = strong conviction against crowd
            if bet_price <= 0.15:
                return 15, f"Extreme conviction NO at {bet_price:.2f}"
            elif bet_price <= 0.25:
                return 12, f"Strong conviction NO at {bet_price:.2f}"
            elif bet_price <= 0.35:
                return 8, f"Moderate conviction NO at {bet_price:.2f}"
            elif bet_price <= 0.45:
                return 4, f"Mild conviction NO at {bet_price:.2f}"
            else:
                return 0, f"Following consensus NO at {bet_price:.2f}"

    @staticmethod
    def score_pizzint_correlation(
        trade_timestamp: datetime,
        market_data: Dict = None
    ) -> Tuple[float, str]:
        """
        Factor 6: PizzINT Correlation (30 points max)

        Correlates trade timing with PizzINT operational intelligence spikes.

        NOTE: Deferred to later phase - requires PizzINT scraper implementation.

        Would score based on:
        - Trade placed <24h before PizzINT spike: 30 points
        - Trade placed <48h before spike: 20 points
        - Trade placed <72h before spike: 10 points
        - No correlation: 0 points

        Args:
            trade_timestamp: When trade was placed
            market_data: Optional market metadata

        Returns:
            (score, reasoning)
        """
        # TODO: Implement when PizzINT scraper is ready
        return 0, "PizzINT correlation not yet implemented"

    @staticmethod
    def score_market_metadata(market_data: Dict) -> Tuple[float, str]:
        """
        Factor 7: Market Metadata (20 points max)

        New markets with low liquidity and high-risk keywords are suspicious targets.

        Scoring:
        - New market (<48 hours old): +10 points
        - Low liquidity (<$10k): +8 points
        - High-risk keywords present: +5 points

        Args:
            market_data: Market metadata dict

        Returns:
            (score, reasoning)
        """
        score = 0
        reasons = []

        # Check market age
        created_at = market_data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None

            if created_at:
                age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                if age_hours < SuspicionScorer.NEW_MARKET_HOURS:
                    score += 10
                    reasons.append(f"New market ({age_hours:.1f} hours old)")

        # Check liquidity
        liquidity = market_data.get('liquidity_usd') or market_data.get('liquidity')
        if liquidity:
            liquidity = float(liquidity)
            if liquidity < SuspicionScorer.LOW_LIQUIDITY_THRESHOLD:
                score += 8
                reasons.append(f"Low liquidity (${liquidity:,.0f})")

        # Check for high-risk keywords
        risk_keywords = market_data.get('risk_keywords', [])
        if risk_keywords and len(risk_keywords) > 0:
            score += 5
            reasons.append(f"High-risk keywords: {', '.join(risk_keywords[:3])}")

        reasoning = "; ".join(reasons) if reasons else "Established market"
        return min(score, SuspicionScorer.WEIGHT_MARKET_METADATA), reasoning

    @classmethod
    def calculate_score(
        cls,
        trade_data: Dict,
        market_data: Dict = None,
        use_blockchain: bool = False
    ) -> Dict:
        """
        Calculate composite suspicion score from all factors

        Args:
            trade_data: Trade information dict
            market_data: Optional market metadata dict
            use_blockchain: Whether to use blockchain verification (Phase 4)

        Returns:
            Dict with:
            - total_score: 0-100 (normalized from 165 max)
            - raw_score: 0-165 (sum of all factors)
            - breakdown: Dict of individual factor scores
            - alert_level: WATCH/SUSPICIOUS/CRITICAL/None
            - blockchain_verified: Whether blockchain verification was used
        """
        # Extract trade fields
        bet_size_usd = trade_data.get('bet_size_usd', 0)
        wallet_address = trade_data.get('wallet_address', '')
        timestamp = trade_data.get('timestamp')
        bet_price = trade_data.get('bet_price', 0.5)
        bet_direction = trade_data.get('bet_direction', 'YES')

        # Convert timestamp if needed
        if isinstance(timestamp, (int, float)):
            # Unix timestamp - convert to datetime
            timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        if not timestamp:
            timestamp = datetime.now(timezone.utc)

        # Market fields
        is_geopolitical = False
        category = None
        if market_data:
            is_geopolitical = market_data.get('is_geopolitical', False)
            category = market_data.get('category')

        # Calculate individual factor scores
        score_1, reason_1 = cls.score_bet_size(bet_size_usd)
        score_2, reason_2 = cls.score_wallet_history(wallet_address, use_blockchain=use_blockchain)
        score_3, reason_3 = cls.score_market_category(is_geopolitical, category)
        score_4, reason_4 = cls.score_timing_anomalies(timestamp)
        score_5, reason_5 = cls.score_price_conviction(bet_price, bet_direction)
        score_6, reason_6 = cls.score_pizzint_correlation(timestamp, market_data)
        score_7, reason_7 = cls.score_market_metadata(market_data or {})

        # Calculate total
        raw_score = score_1 + score_2 + score_3 + score_4 + score_5 + score_6 + score_7
        normalized_score = int((raw_score / cls.MAX_SCORE) * 100)

        # Determine alert level
        from config import config
        if normalized_score >= config.SUSPICION_THRESHOLD_CRITICAL:
            alert_level = 'CRITICAL'
        elif normalized_score >= config.SUSPICION_THRESHOLD_SUSPICIOUS:
            alert_level = 'SUSPICIOUS'
        elif normalized_score >= config.SUSPICION_THRESHOLD_WATCH:
            alert_level = 'WATCH'
        else:
            alert_level = None

        return {
            'total_score': normalized_score,
            'raw_score': raw_score,
            'alert_level': alert_level,
            'blockchain_verified': use_blockchain,
            'breakdown': {
                'bet_size': {'score': score_1, 'max': cls.WEIGHT_BET_SIZE, 'reason': reason_1},
                'wallet_history': {'score': score_2, 'max': cls.WEIGHT_WALLET_HISTORY, 'reason': reason_2},
                'market_category': {'score': score_3, 'max': cls.WEIGHT_MARKET_CATEGORY, 'reason': reason_3},
                'timing': {'score': score_4, 'max': cls.WEIGHT_TIMING, 'reason': reason_4},
                'price_conviction': {'score': score_5, 'max': cls.WEIGHT_PRICE_CONVICTION, 'reason': reason_5},
                'pizzint': {'score': score_6, 'max': cls.WEIGHT_PIZZINT, 'reason': reason_6},
                'market_metadata': {'score': score_7, 'max': cls.WEIGHT_MARKET_METADATA, 'reason': reason_7},
            }
        }


def calculate_suspicion_score(trade_data: Dict, market_data: Dict = None) -> int:
    """
    Convenience function to calculate suspicion score

    Args:
        trade_data: Trade information
        market_data: Optional market metadata

    Returns:
        Suspicion score (0-100)
    """
    result = SuspicionScorer.calculate_score(trade_data, market_data)
    return result['total_score']
