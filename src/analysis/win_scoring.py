"""
Suspicious Win Scorer - Detects wallets with abnormally profitable trading patterns

This module analyzes win/loss patterns to identify potential insider trading.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db_session
from database.models import WalletWinHistory, WalletMetrics, Trade

logger = logging.getLogger(__name__)


# Alert thresholds for suspicious win scores
WIN_ALERT_THRESHOLDS = {
    'WATCH_WIN': 50,       # Win rate >60% OR timing pattern detected
    'SUSPICIOUS_WIN': 70,  # Win rate >70% AND multiple factors
    'CRITICAL_WIN': 85     # Win rate >80% OR timing+geopolitical combo
}

# Minimum trades required before scoring (prevents false positives on small samples)
MIN_RESOLVED_TRADES = 5


class SuspiciousWinScorer:
    """
    Scores wallets based on suspicious win patterns.

    Factors analyzed:
    1. Win Rate Anomaly (30 points) - Significantly above 50% baseline
    2. Timing Pattern (25 points) - Bets placed close to resolution
    3. Geopolitical Accuracy (20 points) - High accuracy on insider-prone markets
    4. Profit Consistency (15 points) - Consistent profitability
    5. Low Volume Accuracy (10 points) - High accuracy with few bets
    """

    # Scoring weights (total = 100)
    WEIGHTS = {
        'win_rate_anomaly': 30,
        'timing_pattern': 25,
        'geopolitical_accuracy': 20,
        'profit_consistency': 15,
        'low_volume_accuracy': 10
    }

    def __init__(self):
        """Initialize the scorer."""
        logger.info("SuspiciousWinScorer initialized")

    def calculate_win_score(
        self,
        wallet_address: str,
        session: Session = None
    ) -> Optional[Dict]:
        """
        Calculate suspicious win score for a wallet.

        Args:
            wallet_address: Wallet address to analyze
            session: Optional database session

        Returns:
            Dict with:
            - total_score: int (0-100)
            - alert_level: 'WATCH_WIN', 'SUSPICIOUS_WIN', 'CRITICAL_WIN', or None
            - breakdown: Dict of factor scores with reasons
            - stats: Dict with trading statistics
        """
        def _calculate(sess: Session) -> Optional[Dict]:
            # Get win history for this wallet
            history = sess.query(WalletWinHistory).filter(
                WalletWinHistory.wallet_address == wallet_address
            ).all()

            if not history:
                logger.debug(f"No win history for {wallet_address[:10]}...")
                return None

            # Check minimum trades threshold
            resolved_count = len([h for h in history if h.trade_result in ('WIN', 'LOSS')])
            if resolved_count < MIN_RESOLVED_TRADES:
                logger.debug(
                    f"Wallet {wallet_address[:10]}... has only {resolved_count} resolved trades "
                    f"(min: {MIN_RESOLVED_TRADES})"
                )
                return {
                    'total_score': 0,
                    'alert_level': None,
                    'breakdown': {},
                    'stats': self._calculate_stats(history),
                    'reason': f'Insufficient trades ({resolved_count}/{MIN_RESOLVED_TRADES})'
                }

            # Calculate each factor
            breakdown = {}

            # Factor 1: Win Rate Anomaly
            breakdown['win_rate_anomaly'] = self._score_win_rate_anomaly(history)

            # Factor 2: Timing Pattern
            breakdown['timing_pattern'] = self._score_timing_pattern(history)

            # Factor 3: Geopolitical Accuracy
            breakdown['geopolitical_accuracy'] = self._score_geopolitical_accuracy(history)

            # Factor 4: Profit Consistency
            breakdown['profit_consistency'] = self._score_profit_consistency(history)

            # Factor 5: Low Volume Accuracy
            breakdown['low_volume_accuracy'] = self._score_low_volume_accuracy(history)

            # Calculate total score
            total_score = sum(factor['score'] for factor in breakdown.values())

            # Determine alert level
            alert_level = self._get_alert_level(total_score)

            # Calculate stats
            stats = self._calculate_stats(history)

            result = {
                'total_score': total_score,
                'alert_level': alert_level,
                'breakdown': breakdown,
                'stats': stats
            }

            # Update wallet metrics with score
            self._update_wallet_score(sess, wallet_address, total_score)

            if alert_level:
                logger.info(
                    f"Suspicious win pattern detected: {wallet_address[:10]}... "
                    f"score={total_score}, level={alert_level}"
                )

            return result

        if session:
            return _calculate(session)
        else:
            with get_db_session() as sess:
                return _calculate(sess)

    def _score_win_rate_anomaly(self, history: List[WalletWinHistory]) -> Dict:
        """
        Score based on win rate anomaly.

        Baseline is 50% (random guessing). Higher win rates are more suspicious.

        Scoring:
        - >80% win rate: 30 points
        - >70% win rate: 25 points
        - >60% win rate: 15 points
        - >55% win rate: 5 points
        - <=55%: 0 points
        """
        wins = len([h for h in history if h.trade_result == 'WIN'])
        losses = len([h for h in history if h.trade_result == 'LOSS'])
        total = wins + losses

        if total == 0:
            return {'score': 0, 'max': self.WEIGHTS['win_rate_anomaly'], 'reason': 'No resolved trades'}

        win_rate = wins / total

        if win_rate > 0.80:
            score = 30
            reason = f'Extremely high win rate: {win_rate:.1%} ({wins}/{total})'
        elif win_rate > 0.70:
            score = 25
            reason = f'Very high win rate: {win_rate:.1%} ({wins}/{total})'
        elif win_rate > 0.60:
            score = 15
            reason = f'Above average win rate: {win_rate:.1%} ({wins}/{total})'
        elif win_rate > 0.55:
            score = 5
            reason = f'Slightly elevated win rate: {win_rate:.1%} ({wins}/{total})'
        else:
            score = 0
            reason = f'Normal win rate: {win_rate:.1%} ({wins}/{total})'

        return {
            'score': score,
            'max': self.WEIGHTS['win_rate_anomaly'],
            'reason': reason,
            'win_rate': win_rate,
            'wins': wins,
            'losses': losses
        }

    def _score_timing_pattern(self, history: List[WalletWinHistory]) -> Dict:
        """
        Score based on timing pattern (bets placed close to resolution).

        Suspicious if many wins come from bets placed <48h before resolution.

        Scoring:
        - >70% of wins from <48h bets: 25 points
        - >50% of wins from <48h bets: 20 points
        - >30% of wins from <48h bets: 10 points
        - Otherwise: 0 points
        """
        wins = [h for h in history if h.trade_result == 'WIN']

        if not wins:
            return {'score': 0, 'max': self.WEIGHTS['timing_pattern'], 'reason': 'No wins to analyze'}

        # Count wins from bets placed <48h before resolution
        early_wins = [w for w in wins if w.hours_before_resolution and w.hours_before_resolution < 48]
        early_ratio = len(early_wins) / len(wins) if wins else 0

        if early_ratio > 0.70:
            score = 25
            reason = f'{early_ratio:.1%} of wins from bets <48h before resolution'
        elif early_ratio > 0.50:
            score = 20
            reason = f'{early_ratio:.1%} of wins from late bets'
        elif early_ratio > 0.30:
            score = 10
            reason = f'{early_ratio:.1%} of wins from late bets'
        else:
            score = 0
            reason = f'Normal timing pattern ({early_ratio:.1%} late bets)'

        return {
            'score': score,
            'max': self.WEIGHTS['timing_pattern'],
            'reason': reason,
            'early_win_ratio': early_ratio,
            'early_wins': len(early_wins),
            'total_wins': len(wins)
        }

    def _score_geopolitical_accuracy(self, history: List[WalletWinHistory]) -> Dict:
        """
        Score based on accuracy on geopolitical markets.

        High accuracy on geopolitical markets is more suspicious than other categories.

        Scoring:
        - >75% geo win rate on 3+ geo trades: 20 points
        - >65% geo win rate on 3+ geo trades: 15 points
        - >55% geo win rate on 3+ geo trades: 8 points
        - Otherwise: 0 points
        """
        geo_trades = [h for h in history if h.is_geopolitical and h.trade_result in ('WIN', 'LOSS')]

        if len(geo_trades) < 3:
            return {
                'score': 0,
                'max': self.WEIGHTS['geopolitical_accuracy'],
                'reason': f'Insufficient geopolitical trades ({len(geo_trades)})'
            }

        geo_wins = len([h for h in geo_trades if h.trade_result == 'WIN'])
        geo_win_rate = geo_wins / len(geo_trades)

        if geo_win_rate > 0.75:
            score = 20
            reason = f'Very high geopolitical accuracy: {geo_win_rate:.1%} ({geo_wins}/{len(geo_trades)})'
        elif geo_win_rate > 0.65:
            score = 15
            reason = f'High geopolitical accuracy: {geo_win_rate:.1%}'
        elif geo_win_rate > 0.55:
            score = 8
            reason = f'Above average geopolitical accuracy: {geo_win_rate:.1%}'
        else:
            score = 0
            reason = f'Normal geopolitical accuracy: {geo_win_rate:.1%}'

        return {
            'score': score,
            'max': self.WEIGHTS['geopolitical_accuracy'],
            'reason': reason,
            'geo_win_rate': geo_win_rate,
            'geo_wins': geo_wins,
            'geo_total': len(geo_trades)
        }

    def _score_profit_consistency(self, history: List[WalletWinHistory]) -> Dict:
        """
        Score based on profit consistency.

        Consistent profitability with high total profit is suspicious.

        Scoring:
        - >$50k profit AND >60% win rate: 15 points
        - >$10k profit AND >60% win rate: 12 points
        - >$5k profit AND >60% win rate: 8 points
        - Otherwise: 0 points
        """
        total_profit = sum(h.profit_loss_usd or 0 for h in history)

        wins = len([h for h in history if h.trade_result == 'WIN'])
        losses = len([h for h in history if h.trade_result == 'LOSS'])
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

        if total_profit > 50000 and win_rate > 0.60:
            score = 15
            reason = f'High profit (${total_profit:,.0f}) with {win_rate:.1%} win rate'
        elif total_profit > 10000 and win_rate > 0.60:
            score = 12
            reason = f'Good profit (${total_profit:,.0f}) with {win_rate:.1%} win rate'
        elif total_profit > 5000 and win_rate > 0.60:
            score = 8
            reason = f'Moderate profit (${total_profit:,.0f}) with {win_rate:.1%} win rate'
        else:
            score = 0
            reason = f'Profit: ${total_profit:,.0f}, win rate: {win_rate:.1%}'

        return {
            'score': score,
            'max': self.WEIGHTS['profit_consistency'],
            'reason': reason,
            'total_profit': total_profit,
            'win_rate': win_rate
        }

    def _score_low_volume_accuracy(self, history: List[WalletWinHistory]) -> Dict:
        """
        Score for high accuracy with low trade volume.

        High accuracy with few trades is harder to achieve by chance.

        Scoring:
        - >80% win rate on 5-15 trades: 10 points
        - >70% win rate on 5-15 trades: 6 points
        - Otherwise: 0 points
        """
        resolved = [h for h in history if h.trade_result in ('WIN', 'LOSS')]
        total = len(resolved)

        # Only applies to low volume (5-15 trades)
        if total < 5 or total > 15:
            return {
                'score': 0,
                'max': self.WEIGHTS['low_volume_accuracy'],
                'reason': f'Not applicable (trade count: {total})'
            }

        wins = len([h for h in resolved if h.trade_result == 'WIN'])
        win_rate = wins / total

        if win_rate > 0.80:
            score = 10
            reason = f'Very high accuracy on small sample: {win_rate:.1%} ({wins}/{total})'
        elif win_rate > 0.70:
            score = 6
            reason = f'High accuracy on small sample: {win_rate:.1%} ({wins}/{total})'
        else:
            score = 0
            reason = f'Normal accuracy on small sample: {win_rate:.1%}'

        return {
            'score': score,
            'max': self.WEIGHTS['low_volume_accuracy'],
            'reason': reason,
            'win_rate': win_rate,
            'trade_count': total
        }

    def _calculate_stats(self, history: List[WalletWinHistory]) -> Dict:
        """Calculate summary statistics from win history."""
        wins = [h for h in history if h.trade_result == 'WIN']
        losses = [h for h in history if h.trade_result == 'LOSS']
        geo = [h for h in history if h.is_geopolitical]
        geo_wins = [h for h in geo if h.trade_result == 'WIN']

        total_pnl = sum(h.profit_loss_usd or 0 for h in history)
        total_volume = sum(h.bet_size_usd or 0 for h in history)

        hours = [h.hours_before_resolution for h in history if h.hours_before_resolution]
        avg_hours = sum(hours) / len(hours) if hours else 0

        return {
            'total_resolved': len(wins) + len(losses),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': len(wins) / (len(wins) + len(losses)) if (wins or losses) else 0,
            'geo_trades': len(geo),
            'geo_wins': len(geo_wins),
            'geo_win_rate': len(geo_wins) / len(geo) if geo else 0,
            'total_profit_loss': total_pnl,
            'total_volume': total_volume,
            'avg_hours_before_resolution': avg_hours
        }

    def _get_alert_level(self, score: int) -> Optional[str]:
        """Map score to alert level."""
        if score >= WIN_ALERT_THRESHOLDS['CRITICAL_WIN']:
            return 'CRITICAL_WIN'
        elif score >= WIN_ALERT_THRESHOLDS['SUSPICIOUS_WIN']:
            return 'SUSPICIOUS_WIN'
        elif score >= WIN_ALERT_THRESHOLDS['WATCH_WIN']:
            return 'WATCH_WIN'
        return None

    def _update_wallet_score(
        self,
        session: Session,
        wallet_address: str,
        score: int
    ):
        """Update suspicious win score in wallet metrics."""
        try:
            metrics = session.query(WalletMetrics).filter(
                WalletMetrics.wallet_address == wallet_address
            ).first()

            if metrics:
                metrics.suspicious_win_score = score
                metrics.last_resolution_check = datetime.now(timezone.utc)

        except Exception as e:
            logger.error(f"Error updating wallet score: {e}")

    def score_all_wallets(
        self,
        min_trades: int = MIN_RESOLVED_TRADES
    ) -> List[Dict]:
        """
        Score all wallets that have sufficient resolved trades.

        Args:
            min_trades: Minimum resolved trades required

        Returns:
            List of scoring results, sorted by score descending
        """
        results = []

        try:
            with get_db_session() as session:
                # Find wallets with sufficient trades
                wallets = session.query(
                    WalletWinHistory.wallet_address,
                    func.count(WalletWinHistory.id).label('count')
                ).filter(
                    WalletWinHistory.trade_result.in_(['WIN', 'LOSS'])
                ).group_by(
                    WalletWinHistory.wallet_address
                ).having(
                    func.count(WalletWinHistory.id) >= min_trades
                ).all()

                logger.info(f"Scoring {len(wallets)} wallets with >={min_trades} resolved trades")

                for wallet_addr, count in wallets:
                    score_result = self.calculate_win_score(wallet_addr, session)
                    if score_result and score_result.get('total_score', 0) > 0:
                        score_result['wallet_address'] = wallet_addr
                        results.append(score_result)

                # Sort by score descending
                results.sort(key=lambda x: x.get('total_score', 0), reverse=True)

        except Exception as e:
            logger.error(f"Error scoring wallets: {e}")

        return results

    def get_suspicious_winners(
        self,
        min_score: int = WIN_ALERT_THRESHOLDS['WATCH_WIN'],
        limit: int = 50
    ) -> List[Dict]:
        """
        Get wallets with suspicious win patterns.

        Args:
            min_score: Minimum score threshold
            limit: Maximum results to return

        Returns:
            List of suspicious wallet data
        """
        try:
            with get_db_session() as session:
                # Query wallets with high suspicious win scores
                wallets = session.query(WalletMetrics).filter(
                    WalletMetrics.suspicious_win_score >= min_score
                ).order_by(
                    WalletMetrics.suspicious_win_score.desc()
                ).limit(limit).all()

                results = []
                for wallet in wallets:
                    results.append({
                        'wallet_address': wallet.wallet_address,
                        'suspicious_win_score': wallet.suspicious_win_score,
                        'win_rate': wallet.win_rate,
                        'winning_trades': wallet.winning_trades,
                        'losing_trades': wallet.losing_trades,
                        'total_profit_loss_usd': wallet.total_profit_loss_usd,
                        'geopolitical_accuracy': wallet.geopolitical_accuracy,
                        'last_resolution_check': wallet.last_resolution_check
                    })

                return results

        except Exception as e:
            logger.error(f"Error getting suspicious winners: {e}")
            return []


def get_suspicious_win_scorer() -> SuspiciousWinScorer:
    """
    Get singleton SuspiciousWinScorer instance.

    Returns:
        SuspiciousWinScorer instance
    """
    global _suspicious_win_scorer

    if '_suspicious_win_scorer' not in globals():
        _suspicious_win_scorer = SuspiciousWinScorer()

    return _suspicious_win_scorer
