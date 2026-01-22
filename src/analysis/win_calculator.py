"""
Win/Loss Calculator - Computes trade outcomes after market resolution

This module matches trades to resolutions and calculates profit/loss.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple

from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.models import Trade, MarketResolution, WalletWinHistory, WalletMetrics, Market

logger = logging.getLogger(__name__)


class WinLossCalculator:
    """
    Calculates trade outcomes (WIN/LOSS) after market resolution.

    Matches trades to resolutions and computes profit/loss in USD.
    """

    def __init__(self):
        """Initialize the calculator."""
        logger.info("WinLossCalculator initialized")

    def calculate_trade_result(
        self,
        trade: Trade,
        resolution: MarketResolution
    ) -> Dict:
        """
        Determine trade outcome based on market resolution.

        Args:
            trade: Trade object
            resolution: MarketResolution object

        Returns:
            Dict with:
            - result: 'WIN', 'LOSS', or 'VOID'
            - profit_loss_usd: float
            - hours_before_resolution: float
        """
        # Handle VOID case
        if resolution.winning_outcome == 'VOID':
            return {
                'result': 'VOID',
                'profit_loss_usd': 0.0,
                'hours_before_resolution': self._calculate_hours_before(
                    trade.timestamp, resolution.resolved_at
                )
            }

        # Determine if trade won
        bet_direction = trade.bet_direction.upper() if trade.bet_direction else ''
        winning_outcome = resolution.winning_outcome.upper() if resolution.winning_outcome else ''

        if bet_direction == winning_outcome:
            # WIN: Calculate profit
            profit = self.calculate_profit(
                bet_size=trade.bet_size_usd,
                bet_price=trade.bet_price
            )
            result = 'WIN'
        else:
            # LOSS: Lose entire bet
            profit = -trade.bet_size_usd
            result = 'LOSS'

        hours_before = self._calculate_hours_before(trade.timestamp, resolution.resolved_at)

        return {
            'result': result,
            'profit_loss_usd': profit,
            'hours_before_resolution': hours_before
        }

    def calculate_profit(self, bet_size: float, bet_price: float) -> float:
        """
        Calculate profit for a winning trade.

        Formula: profit = bet_size * (1 - bet_price) / bet_price

        Example:
        - Bet $1000 at 0.30 (30 cents per share)
        - Shares = $1000 / $0.30 = 3,333 shares
        - Payout = 3,333 * $1.00 = $3,333
        - Profit = $3,333 - $1,000 = $2,333

        Args:
            bet_size: Amount bet in USD
            bet_price: Entry price (0.0 to 1.0)

        Returns:
            Profit in USD
        """
        if bet_price <= 0 or bet_price >= 1:
            # Edge case: price at boundaries
            if bet_price <= 0:
                return bet_size * 100  # Massive win (unlikely)
            return 0  # Price at 1.0, no profit possible

        # Shares bought = bet_size / bet_price
        # Payout per share = $1.00
        # Profit = (1 - bet_price) / bet_price * bet_size
        return bet_size * (1 - bet_price) / bet_price

    def _calculate_hours_before(
        self,
        trade_time: datetime,
        resolution_time: datetime
    ) -> float:
        """
        Calculate hours between trade and resolution.

        Args:
            trade_time: When trade was placed
            resolution_time: When market resolved

        Returns:
            Hours before resolution (negative if after)
        """
        if not trade_time or not resolution_time:
            return 0.0

        # Ensure both are timezone-aware
        if trade_time.tzinfo is None:
            trade_time = trade_time.replace(tzinfo=timezone.utc)
        if resolution_time.tzinfo is None:
            resolution_time = resolution_time.replace(tzinfo=timezone.utc)

        delta = resolution_time - trade_time
        return delta.total_seconds() / 3600  # Convert to hours

    def process_market_resolution(
        self,
        resolution: MarketResolution,
        session: Session = None
    ) -> int:
        """
        Process all trades for a resolved market.

        Args:
            resolution: MarketResolution object
            session: Optional database session (creates one if not provided)

        Returns:
            Number of trades processed
        """
        trades_processed = 0

        def _process(sess: Session):
            nonlocal trades_processed

            # Find all trades for this market that haven't been resolved
            trades = sess.query(Trade).filter(
                Trade.market_id == resolution.market_id,
                Trade.trade_result.is_(None) | (Trade.trade_result == 'PENDING')
            ).all()

            if not trades:
                logger.debug(f"No pending trades for market {resolution.market_id[:20]}...")
                return

            logger.info(f"Processing {len(trades)} trades for market {resolution.market_id[:20]}...")

            # Get market info for context
            market = sess.query(Market).filter(
                Market.market_id == resolution.market_id
            ).first()

            is_geopolitical = market.is_geopolitical if market else False
            market_title = market.question[:200] if market and market.question else ''

            for trade in trades:
                try:
                    # Calculate result
                    result = self.calculate_trade_result(trade, resolution)

                    # Update trade
                    trade.trade_result = result['result']
                    trade.profit_loss_usd = result['profit_loss_usd']
                    trade.hours_before_resolution = result['hours_before_resolution']
                    trade.resolution_id = resolution.id

                    # Create win history entry
                    history = WalletWinHistory(
                        wallet_address=trade.wallet_address,
                        market_id=resolution.market_id,
                        trade_id=trade.id,
                        resolution_id=resolution.id,
                        bet_direction=trade.bet_direction,
                        bet_size_usd=trade.bet_size_usd,
                        bet_price=trade.bet_price,
                        winning_outcome=resolution.winning_outcome,
                        trade_result=result['result'],
                        profit_loss_usd=result['profit_loss_usd'],
                        hours_before_resolution=result['hours_before_resolution'],
                        is_geopolitical=is_geopolitical,
                        suspicion_score_at_bet=trade.suspicion_score,
                        market_title=market_title,
                        created_at=datetime.now(timezone.utc)
                    )
                    sess.add(history)

                    trades_processed += 1

                    logger.debug(
                        f"Trade {trade.id}: {result['result']} "
                        f"(P&L: ${result['profit_loss_usd']:,.2f}, "
                        f"{result['hours_before_resolution']:.1f}h before)"
                    )

                except Exception as e:
                    logger.error(f"Error processing trade {trade.id}: {e}")
                    continue

            sess.flush()

        # Use provided session or create new one
        if session:
            _process(session)
        else:
            with get_db_session() as sess:
                _process(sess)

        if trades_processed > 0:
            logger.info(
                f"Processed {trades_processed} trades for market {resolution.market_id[:20]}... "
                f"-> {resolution.winning_outcome}"
            )

        return trades_processed

    def update_wallet_metrics(
        self,
        wallet_address: str,
        session: Session = None
    ) -> Optional[WalletMetrics]:
        """
        Recalculate wallet win metrics after new resolutions.

        Args:
            wallet_address: Wallet to update
            session: Optional database session

        Returns:
            Updated WalletMetrics or None
        """
        def _update(sess: Session) -> Optional[WalletMetrics]:
            # Get or create wallet metrics
            metrics = sess.query(WalletMetrics).filter(
                WalletMetrics.wallet_address == wallet_address
            ).first()

            if not metrics:
                metrics = WalletMetrics(wallet_address=wallet_address)
                sess.add(metrics)

            # Get win history for this wallet
            history = sess.query(WalletWinHistory).filter(
                WalletWinHistory.wallet_address == wallet_address
            ).all()

            if not history:
                return metrics

            # Calculate stats
            wins = [h for h in history if h.trade_result == 'WIN']
            losses = [h for h in history if h.trade_result == 'LOSS']
            geo_wins = [h for h in wins if h.is_geopolitical]
            geo_losses = [h for h in losses if h.is_geopolitical]

            # Update metrics
            metrics.winning_trades = len(wins)
            metrics.losing_trades = len(losses)

            if wins or losses:
                metrics.win_rate = len(wins) / (len(wins) + len(losses))
            else:
                metrics.win_rate = None

            # Geopolitical stats
            metrics.geopolitical_wins = len(geo_wins)
            metrics.geopolitical_losses = len(geo_losses)

            if geo_wins or geo_losses:
                metrics.geopolitical_accuracy = len(geo_wins) / (len(geo_wins) + len(geo_losses))
            else:
                metrics.geopolitical_accuracy = None

            # Profit/loss
            total_pnl = sum(h.profit_loss_usd or 0 for h in history)
            metrics.total_profit_loss_usd = total_pnl

            # Early wins (bets placed <48h before resolution)
            early_wins = [w for w in wins if w.hours_before_resolution and w.hours_before_resolution < 48]
            metrics.early_win_count = len(early_wins)

            # Win streaks
            current_streak, max_streak = self._calculate_win_streaks(history)
            metrics.win_streak_current = current_streak
            metrics.win_streak_max = max_streak

            # Timing
            if history:
                hours = [h.hours_before_resolution for h in history if h.hours_before_resolution]
                if hours:
                    metrics.avg_hours_before_resolution = sum(hours) / len(hours)

            metrics.last_resolution_check = datetime.now(timezone.utc)
            sess.flush()

            logger.info(
                f"Updated metrics for {wallet_address[:10]}...: "
                f"wins={metrics.winning_trades}, losses={metrics.losing_trades}, "
                f"win_rate={metrics.win_rate:.1%}" if metrics.win_rate else ""
            )

            return metrics

        if session:
            return _update(session)
        else:
            with get_db_session() as sess:
                return _update(sess)

    def _calculate_win_streaks(
        self,
        history: List[WalletWinHistory]
    ) -> Tuple[int, int]:
        """
        Calculate current and max win streaks.

        Args:
            history: List of win history entries (should be sorted by time)

        Returns:
            Tuple of (current_streak, max_streak)
        """
        if not history:
            return 0, 0

        # Sort by created_at
        sorted_history = sorted(history, key=lambda h: h.created_at or datetime.min)

        current_streak = 0
        max_streak = 0
        streak = 0

        for entry in sorted_history:
            if entry.trade_result == 'WIN':
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0

        # Current streak is the streak at the end
        current_streak = streak

        return current_streak, max_streak

    def process_all_pending_resolutions(self) -> Dict[str, int]:
        """
        Process all markets that have resolutions but pending trades.

        Returns:
            Dict with processing stats
        """
        stats = {
            'resolutions_checked': 0,
            'trades_processed': 0,
            'wallets_updated': 0
        }

        try:
            with get_db_session() as session:
                # Find resolutions that have pending trades
                pending_trades = session.query(Trade.market_id).filter(
                    Trade.trade_result.is_(None) | (Trade.trade_result == 'PENDING')
                ).distinct().all()

                pending_market_ids = [t[0] for t in pending_trades]

                if not pending_market_ids:
                    logger.info("No pending trades to process")
                    return stats

                # Get resolutions for these markets
                resolutions = session.query(MarketResolution).filter(
                    MarketResolution.market_id.in_(pending_market_ids)
                ).all()

                stats['resolutions_checked'] = len(resolutions)

                wallets_to_update = set()

                for resolution in resolutions:
                    # Get wallet addresses before processing
                    trades = session.query(Trade.wallet_address).filter(
                        Trade.market_id == resolution.market_id,
                        Trade.trade_result.is_(None) | (Trade.trade_result == 'PENDING')
                    ).distinct().all()

                    for t in trades:
                        wallets_to_update.add(t[0])

                    # Process trades
                    processed = self.process_market_resolution(resolution, session)
                    stats['trades_processed'] += processed

                # Update wallet metrics
                for wallet in wallets_to_update:
                    self.update_wallet_metrics(wallet, session)
                    stats['wallets_updated'] += 1

            logger.info(
                f"Processed {stats['trades_processed']} trades from "
                f"{stats['resolutions_checked']} resolutions, "
                f"updated {stats['wallets_updated']} wallets"
            )

        except Exception as e:
            logger.error(f"Error processing pending resolutions: {e}")

        return stats


def get_win_loss_calculator() -> WinLossCalculator:
    """
    Get singleton WinLossCalculator instance.

    Returns:
        WinLossCalculator instance
    """
    global _win_loss_calculator

    if '_win_loss_calculator' not in globals():
        _win_loss_calculator = WinLossCalculator()

    return _win_loss_calculator
