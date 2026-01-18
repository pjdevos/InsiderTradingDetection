"""
Advanced wallet pattern analysis and detection

Analyzes trading patterns to identify sophisticated insider trading behaviors:
- Network analysis (coordinated trading)
- Repeat offenders
- Win rate anomalies
- Temporal patterns
- Behavior clustering
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from database.models import Trade, WalletMetrics
from database.connection import get_db_session

logger = logging.getLogger(__name__)


@dataclass
class WalletProfile:
    """Profile of a wallet's trading behavior"""
    wallet_address: str
    total_trades: int
    suspicious_trades: int
    avg_suspicion_score: float
    win_rate: float
    avg_bet_size: float
    off_hours_ratio: float
    weekend_ratio: float
    early_trade_ratio: float  # Trades before significant price movement
    markets_traded: int
    first_trade_date: datetime
    last_trade_date: datetime
    wallet_age_days: int


@dataclass
class NetworkPattern:
    """Coordinated trading pattern between wallets"""
    wallets: List[str]
    market_id: str
    market_title: str
    time_window_minutes: int
    trade_count: int
    total_volume: float
    avg_suspicion_score: float
    pattern_type: str  # 'coordinated', 'copycat', 'sybil'


@dataclass
class TemporalPattern:
    """Temporal trading pattern for a wallet"""
    wallet_address: str
    pattern_type: str  # 'early_bird', 'night_owl', 'weekend_warrior', 'crisis_trader'
    description: str
    confidence_score: float
    supporting_trades: int


class WalletPatternAnalyzer:
    """
    Analyzes wallet trading patterns for insider trading detection
    """

    @staticmethod
    def get_wallet_profile(session: Session, wallet_address: str) -> Optional[WalletProfile]:
        """
        Build comprehensive profile of a wallet's trading behavior

        Args:
            session: Database session
            wallet_address: Wallet address to analyze

        Returns:
            WalletProfile or None
        """
        try:
            # Get all trades for this wallet
            trades = session.query(Trade)\
                .filter(Trade.wallet_address == wallet_address)\
                .order_by(Trade.timestamp)\
                .all()

            if not trades:
                return None

            # Calculate metrics
            total_trades = len(trades)
            suspicious_trades = len([t for t in trades if (t.suspicion_score or 0) >= 50])

            scores = [t.suspicion_score for t in trades if t.suspicion_score is not None]
            avg_suspicion_score = sum(scores) / len(scores) if scores else 0

            # Win rate calculation (simplified - would need outcome data)
            # For now, use high suspicion trades as proxy for "knowing" trades
            win_rate = suspicious_trades / total_trades if total_trades > 0 else 0

            avg_bet_size = sum(t.bet_size_usd for t in trades) / total_trades

            # Off-hours and weekend ratios
            off_hours_count = sum(1 for t in trades if t.timestamp and (
                t.timestamp.hour < 9 or t.timestamp.hour >= 21
            ))
            off_hours_ratio = off_hours_count / total_trades if total_trades > 0 else 0

            weekend_count = sum(1 for t in trades if t.timestamp and t.timestamp.weekday() >= 5)
            weekend_ratio = weekend_count / total_trades if total_trades > 0 else 0

            # Markets traded
            markets_traded = len(set(t.market_id for t in trades if t.market_id))

            # Dates
            first_trade = trades[0].timestamp
            last_trade = trades[-1].timestamp

            # Calculate wallet age (handle timezone-aware and naive datetimes)
            if first_trade:
                if first_trade.tzinfo is None:
                    first_trade = first_trade.replace(tzinfo=timezone.utc)
                wallet_age_days = (datetime.now(timezone.utc) - first_trade).days
            else:
                wallet_age_days = 0

            # Early trade detection (simplified)
            # Would need price history to properly detect
            early_trade_ratio = 0.0  # Placeholder

            return WalletProfile(
                wallet_address=wallet_address,
                total_trades=total_trades,
                suspicious_trades=suspicious_trades,
                avg_suspicion_score=avg_suspicion_score,
                win_rate=win_rate,
                avg_bet_size=avg_bet_size,
                off_hours_ratio=off_hours_ratio,
                weekend_ratio=weekend_ratio,
                early_trade_ratio=early_trade_ratio,
                markets_traded=markets_traded,
                first_trade_date=first_trade,
                last_trade_date=last_trade,
                wallet_age_days=wallet_age_days
            )

        except Exception as e:
            logger.error(f"Error building wallet profile: {e}")
            return None

    @staticmethod
    def detect_repeat_offenders(
        session: Session,
        min_suspicious_trades: int = 3,
        min_avg_score: float = 60,
        days: int = 30
    ) -> List[WalletProfile]:
        """
        Detect wallets with repeated suspicious trading behavior

        Args:
            session: Database session
            min_suspicious_trades: Minimum number of suspicious trades
            min_avg_score: Minimum average suspicion score
            days: Time window to analyze

        Returns:
            List of suspicious wallet profiles
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get wallets with multiple suspicious trades
            wallet_query = session.query(Trade.wallet_address)\
                .filter(
                    Trade.timestamp >= cutoff_date,
                    Trade.suspicion_score >= 50
                )\
                .group_by(Trade.wallet_address)\
                .having(func.count(Trade.id) >= min_suspicious_trades)

            suspicious_wallets = [row[0] for row in wallet_query.all()]

            # Build profiles for these wallets
            profiles = []
            for wallet in suspicious_wallets:
                profile = WalletPatternAnalyzer.get_wallet_profile(session, wallet)
                if profile and profile.avg_suspicion_score >= min_avg_score:
                    profiles.append(profile)

            # Sort by average suspicion score
            profiles.sort(key=lambda p: p.avg_suspicion_score, reverse=True)

            logger.info(f"Found {len(profiles)} repeat offenders")
            return profiles

        except Exception as e:
            logger.error(f"Error detecting repeat offenders: {e}")
            return []

    @staticmethod
    def detect_network_patterns(
        session: Session,
        time_window_minutes: int = 60,
        min_wallets: int = 2,
        days: int = 7
    ) -> List[NetworkPattern]:
        """
        Detect coordinated trading patterns across multiple wallets

        Args:
            session: Database session
            time_window_minutes: Time window for coordination detection
            min_wallets: Minimum wallets to constitute a pattern
            days: Time window to analyze

        Returns:
            List of detected network patterns
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get all trades in time window
            trades = session.query(Trade)\
                .filter(Trade.timestamp >= cutoff_date)\
                .order_by(Trade.market_id, Trade.timestamp)\
                .all()

            # Group trades by market
            market_trades = defaultdict(list)
            for trade in trades:
                if trade.market_id:
                    market_trades[trade.market_id].append(trade)

            patterns = []

            # Analyze each market for coordinated activity
            for market_id, market_trade_list in market_trades.items():
                if len(market_trade_list) < min_wallets:
                    continue

                # Find clusters of trades within time window
                for i, base_trade in enumerate(market_trade_list):
                    cluster = [base_trade]
                    cluster_wallets = {base_trade.wallet_address}

                    # Find other trades within time window
                    for other_trade in market_trade_list[i+1:]:
                        if not other_trade.timestamp or not base_trade.timestamp:
                            continue

                        time_diff = (other_trade.timestamp - base_trade.timestamp).total_seconds() / 60

                        if time_diff <= time_window_minutes:
                            if other_trade.wallet_address not in cluster_wallets:
                                cluster.append(other_trade)
                                cluster_wallets.add(other_trade.wallet_address)
                        else:
                            break  # Trades are sorted by time

                    # If cluster is significant, record pattern
                    if len(cluster_wallets) >= min_wallets:
                        total_volume = sum(t.bet_size_usd for t in cluster)
                        scores = [t.suspicion_score for t in cluster if t.suspicion_score]
                        avg_score = sum(scores) / len(scores) if scores else 0

                        market_title = cluster[0].market_title or "Unknown Market"

                        pattern = NetworkPattern(
                            wallets=list(cluster_wallets),
                            market_id=market_id,
                            market_title=market_title,
                            time_window_minutes=int(time_diff) if time_diff else time_window_minutes,
                            trade_count=len(cluster),
                            total_volume=total_volume,
                            avg_suspicion_score=avg_score,
                            pattern_type='coordinated'
                        )
                        patterns.append(pattern)

            logger.info(f"Found {len(patterns)} network patterns")
            return patterns

        except Exception as e:
            logger.error(f"Error detecting network patterns: {e}")
            return []

    @staticmethod
    def detect_temporal_patterns(
        session: Session,
        wallet_address: str
    ) -> List[TemporalPattern]:
        """
        Detect temporal trading patterns for a specific wallet

        Args:
            session: Database session
            wallet_address: Wallet to analyze

        Returns:
            List of detected temporal patterns
        """
        try:
            trades = session.query(Trade)\
                .filter(Trade.wallet_address == wallet_address)\
                .order_by(Trade.timestamp)\
                .all()

            if len(trades) < 5:
                return []  # Need sufficient data

            patterns = []

            # Analyze timing patterns
            total_trades = len(trades)

            # Night owl pattern (> 50% trades between 9pm - 6am)
            night_trades = sum(1 for t in trades if t.timestamp and (
                t.timestamp.hour >= 21 or t.timestamp.hour < 6
            ))
            if night_trades / total_trades > 0.5:
                patterns.append(TemporalPattern(
                    wallet_address=wallet_address,
                    pattern_type='night_owl',
                    description=f'{night_trades}/{total_trades} trades during night hours (9pm-6am)',
                    confidence_score=night_trades / total_trades,
                    supporting_trades=night_trades
                ))

            # Weekend warrior (> 40% trades on weekends)
            weekend_trades = sum(1 for t in trades if t.timestamp and t.timestamp.weekday() >= 5)
            if weekend_trades / total_trades > 0.4:
                patterns.append(TemporalPattern(
                    wallet_address=wallet_address,
                    pattern_type='weekend_warrior',
                    description=f'{weekend_trades}/{total_trades} trades on weekends',
                    confidence_score=weekend_trades / total_trades,
                    supporting_trades=weekend_trades
                ))

            # Early bird pattern (trades with high suspicion scores)
            high_suspicion = [t for t in trades if (t.suspicion_score or 0) >= 70]
            if len(high_suspicion) >= 3:
                patterns.append(TemporalPattern(
                    wallet_address=wallet_address,
                    pattern_type='early_bird',
                    description=f'{len(high_suspicion)} high-suspicion trades (score >= 70)',
                    confidence_score=len(high_suspicion) / total_trades,
                    supporting_trades=len(high_suspicion)
                ))

            # Crisis trader (trades on geopolitical markets with suspicious timing)
            geopolitical_trades = [t for t in trades if t.market_category == 'GEOPOLITICS']
            suspicious_geo = [t for t in geopolitical_trades if (t.suspicion_score or 0) >= 60]
            if len(suspicious_geo) >= 2 and len(geopolitical_trades) > 0:
                ratio = len(suspicious_geo) / len(geopolitical_trades)
                if ratio > 0.5:
                    patterns.append(TemporalPattern(
                        wallet_address=wallet_address,
                        pattern_type='crisis_trader',
                        description=f'{len(suspicious_geo)}/{len(geopolitical_trades)} suspicious geopolitical trades',
                        confidence_score=ratio,
                        supporting_trades=len(suspicious_geo)
                    ))

            return patterns

        except Exception as e:
            logger.error(f"Error detecting temporal patterns: {e}")
            return []

    @staticmethod
    def calculate_win_rate_anomaly(
        session: Session,
        wallet_address: str,
        baseline_win_rate: float = 0.50
    ) -> Optional[Dict]:
        """
        Detect statistically unusual win rates

        Args:
            session: Database session
            wallet_address: Wallet to analyze
            baseline_win_rate: Expected baseline win rate (50% for binary markets)

        Returns:
            Anomaly details or None
        """
        try:
            # Get wallet metrics
            metrics = session.query(WalletMetrics)\
                .filter(WalletMetrics.wallet_address == wallet_address)\
                .first()

            if not metrics or metrics.total_trades < 10:
                return None  # Need sufficient data

            # Calculate win rate (if we have the data)
            # For now, use high-suspicion trades as proxy
            trades = session.query(Trade)\
                .filter(Trade.wallet_address == wallet_address)\
                .all()

            if not trades:
                return None

            # Simplified: count trades that likely won (high suspicion = early knowledge)
            likely_wins = sum(1 for t in trades if (t.suspicion_score or 0) >= 70)
            observed_win_rate = likely_wins / len(trades)

            # Statistical significance (simplified chi-square test)
            # Would need actual outcomes for proper calculation
            deviation = abs(observed_win_rate - baseline_win_rate)

            # Flag if win rate is significantly above baseline
            if deviation > 0.20 and observed_win_rate > baseline_win_rate:
                return {
                    'wallet_address': wallet_address,
                    'observed_win_rate': observed_win_rate,
                    'baseline_win_rate': baseline_win_rate,
                    'deviation': deviation,
                    'total_trades': len(trades),
                    'likely_wins': likely_wins,
                    'anomaly_score': min(deviation * 100, 100),
                    'is_anomalous': True
                }

            return None

        except Exception as e:
            logger.error(f"Error calculating win rate anomaly: {e}")
            return None

    @staticmethod
    def get_wallet_similarity(
        session: Session,
        wallet1: str,
        wallet2: str
    ) -> float:
        """
        Calculate similarity score between two wallets

        Args:
            session: Database session
            wallet1: First wallet address
            wallet2: Second wallet address

        Returns:
            Similarity score (0-1)
        """
        try:
            # Get trades for both wallets
            trades1 = session.query(Trade)\
                .filter(Trade.wallet_address == wallet1)\
                .all()

            trades2 = session.query(Trade)\
                .filter(Trade.wallet_address == wallet2)\
                .all()

            if not trades1 or not trades2:
                return 0.0

            # Calculate similarity based on:
            # 1. Shared markets
            markets1 = set(t.market_id for t in trades1 if t.market_id)
            markets2 = set(t.market_id for t in trades2 if t.market_id)
            market_overlap = len(markets1 & markets2) / max(len(markets1 | markets2), 1)

            # 2. Similar timing patterns
            hours1 = [t.timestamp.hour for t in trades1 if t.timestamp]
            hours2 = [t.timestamp.hour for t in trades2 if t.timestamp]

            if hours1 and hours2:
                avg_hour1 = sum(hours1) / len(hours1)
                avg_hour2 = sum(hours2) / len(hours2)
                hour_similarity = 1 - (abs(avg_hour1 - avg_hour2) / 24)
            else:
                hour_similarity = 0

            # 3. Similar suspicion scores
            scores1 = [t.suspicion_score for t in trades1 if t.suspicion_score]
            scores2 = [t.suspicion_score for t in trades2 if t.suspicion_score]

            if scores1 and scores2:
                avg_score1 = sum(scores1) / len(scores1)
                avg_score2 = sum(scores2) / len(scores2)
                score_similarity = 1 - (abs(avg_score1 - avg_score2) / 100)
            else:
                score_similarity = 0

            # Combined similarity (weighted average)
            similarity = (
                market_overlap * 0.5 +
                hour_similarity * 0.25 +
                score_similarity * 0.25
            )

            return similarity

        except Exception as e:
            logger.error(f"Error calculating wallet similarity: {e}")
            return 0.0


# Convenience functions

def analyze_wallet(wallet_address: str) -> Dict:
    """
    Comprehensive analysis of a wallet

    Args:
        wallet_address: Wallet to analyze

    Returns:
        Analysis results
    """
    with get_db_session() as session:
        profile = WalletPatternAnalyzer.get_wallet_profile(session, wallet_address)
        temporal_patterns = WalletPatternAnalyzer.detect_temporal_patterns(session, wallet_address)
        win_rate_anomaly = WalletPatternAnalyzer.calculate_win_rate_anomaly(session, wallet_address)

        return {
            'profile': profile,
            'temporal_patterns': temporal_patterns,
            'win_rate_anomaly': win_rate_anomaly
        }


def find_suspicious_networks(days: int = 7) -> List[NetworkPattern]:
    """
    Find coordinated trading networks

    Args:
        days: Days to analyze

    Returns:
        List of network patterns
    """
    with get_db_session() as session:
        return WalletPatternAnalyzer.detect_network_patterns(session, days=days)


def find_repeat_offenders(days: int = 30) -> List[WalletProfile]:
    """
    Find wallets with repeated suspicious activity

    Args:
        days: Days to analyze

    Returns:
        List of suspicious wallet profiles
    """
    with get_db_session() as session:
        return WalletPatternAnalyzer.detect_repeat_offenders(session, days=days)
