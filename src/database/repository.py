"""
Data repository layer for database operations

All methods validate inputs before executing queries to prevent
potential security issues and ensure data integrity.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.models import Trade, Market, WalletMetrics, Alert, MonitorCheckpoint, FailedTrade
from database.connection import get_db_session
from database.validators import DatabaseInputValidator, ValidationError

logger = logging.getLogger(__name__)


class TradeRepository:
    """Repository for trade operations"""

    @staticmethod
    def create_trade(session: Session, trade_data: Dict) -> Optional[Trade]:
        """
        Create a new trade record

        Args:
            session: Database session
            trade_data: Dictionary with trade information

        Returns:
            Created Trade object or None if duplicate
        """
        try:
            # Validate required fields before constructing ORM object
            if trade_data.get('transaction_hash'):
                trade_data['transaction_hash'] = DatabaseInputValidator.validate_transaction_hash(
                    trade_data['transaction_hash']
                )
            if trade_data.get('wallet_address'):
                trade_data['wallet_address'] = DatabaseInputValidator.validate_wallet_address(
                    trade_data['wallet_address']
                )
            if trade_data.get('market_id'):
                trade_data['market_id'] = DatabaseInputValidator.validate_market_id(
                    trade_data['market_id']
                )

            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()  # Get the ID
            logger.debug(f"Created trade: {trade.id} (wallet: {(trade.wallet_address or 'unknown')[:10]}..., ${trade.bet_size_usd:,.2f})")
            return trade

        except ValidationError as e:
            logger.warning(f"Validation failed creating trade: {e}")
            return None

        except IntegrityError as e:
            session.rollback()
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            is_duplicate = (
                'UNIQUE constraint failed: trades.transaction_hash' in error_str or  # SQLite
                ('duplicate key value violates unique constraint' in error_str and
                 'transaction_hash' in error_str)  # PostgreSQL
            )
            if is_duplicate:
                logger.debug(f"Trade already exists: {trade_data.get('transaction_hash')}")
            else:
                # Log the full error for debugging other constraint violations
                logger.warning(f"IntegrityError creating trade: {error_str}")
            return None

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating trade: {e}", exc_info=True)
            return None

    @staticmethod
    def get_trade_by_tx_hash(session: Session, tx_hash: str) -> Optional[Trade]:
        """Get trade by transaction hash"""
        # Validate input
        tx_hash = DatabaseInputValidator.validate_transaction_hash(tx_hash)
        return session.query(Trade).filter(Trade.transaction_hash == tx_hash).first()

    @staticmethod
    def get_trades_by_wallet(
        session: Session,
        wallet_address: str,
        limit: int = 100
    ) -> List[Trade]:
        """Get all trades for a wallet"""
        # Validate inputs
        wallet_address = DatabaseInputValidator.validate_wallet_address(wallet_address)
        limit = DatabaseInputValidator.validate_limit(limit)

        return session.query(Trade)\
            .filter(Trade.wallet_address == wallet_address)\
            .order_by(Trade.timestamp.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def get_recent_trades(
        session: Session,
        hours: int = 24,
        min_bet_size: float = None,
        limit: int = 1000
    ) -> List[Trade]:
        """
        Get recent trades

        Args:
            session: Database session
            hours: Number of hours to look back
            min_bet_size: Minimum bet size filter
            limit: Maximum number of trades

        Returns:
            List of Trade objects
        """
        # Validate inputs
        hours = DatabaseInputValidator.validate_hours(hours)
        limit = DatabaseInputValidator.validate_limit(limit)
        min_bet_size = DatabaseInputValidator.validate_optional_bet_size(min_bet_size)

        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = session.query(Trade)\
            .filter(Trade.timestamp >= start_time)

        if min_bet_size:
            query = query.filter(Trade.bet_size_usd >= min_bet_size)

        return query.order_by(Trade.timestamp.desc()).limit(limit).all()

    @staticmethod
    def get_suspicious_trades(
        session: Session,
        min_score: int = 70,
        limit: int = 100
    ) -> List[Trade]:
        """Get trades with high suspicion scores"""
        # Validate inputs
        min_score = DatabaseInputValidator.validate_score(min_score)
        limit = DatabaseInputValidator.validate_limit(limit)

        return session.query(Trade)\
            .filter(Trade.suspicion_score >= min_score)\
            .order_by(Trade.suspicion_score.desc(), Trade.timestamp.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def update_suspicion_score(
        session: Session,
        trade_id: int,
        score: int,
        alert_level: str = None
    ) -> bool:
        """Update suspicion score for a trade"""
        try:
            # Validate inputs
            trade_id = DatabaseInputValidator.validate_positive_int(trade_id, "trade_id")
            score = DatabaseInputValidator.validate_score(score)
            alert_level = DatabaseInputValidator.validate_optional_alert_level(alert_level)

            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.suspicion_score = score
                if alert_level:
                    trade.alert_level = alert_level
                session.flush()
                logger.info(f"Updated suspicion score for trade {trade_id}: {score}")
                return True
            return False
        except ValidationError as e:
            logger.error(f"Validation error updating suspicion score: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating suspicion score: {e}")
            return False

    @staticmethod
    def get_trade_statistics(session: Session, hours: int = 24) -> Dict:
        """Get trade statistics for the last N hours"""
        # Validate inputs
        hours = DatabaseInputValidator.validate_hours(hours)

        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        total_trades = session.query(func.count(Trade.id))\
            .filter(Trade.timestamp >= start_time)\
            .scalar()

        total_volume = session.query(func.sum(Trade.bet_size_usd))\
            .filter(Trade.timestamp >= start_time)\
            .scalar() or 0.0

        avg_bet_size = session.query(func.avg(Trade.bet_size_usd))\
            .filter(Trade.timestamp >= start_time)\
            .scalar() or 0.0

        suspicious_count = session.query(func.count(Trade.id))\
            .filter(Trade.timestamp >= start_time, Trade.suspicion_score >= 70)\
            .scalar()

        return {
            'total_trades': total_trades,
            'total_volume_usd': float(total_volume),
            'avg_bet_size_usd': float(avg_bet_size),
            'suspicious_trades': suspicious_count,
            'time_period_hours': hours
        }


class MarketRepository:
    """Repository for market operations"""

    @staticmethod
    def create_or_update_market(session: Session, market_data: Dict) -> Market:
        """
        Create or update a market record

        Args:
            session: Database session
            market_data: Dictionary with market information

        Returns:
            Market object
        """
        market_id = market_data.get('market_id')

        # Try to get existing market
        market = session.query(Market).filter(Market.market_id == market_id).first()

        if market:
            # Update existing
            for key, value in market_data.items():
                if hasattr(market, key):
                    setattr(market, key, value)
            logger.debug(f"Updated market: {market_id}")
        else:
            # Create new
            market = Market(**market_data)
            session.add(market)
            logger.debug(f"Created market: {market_id}")

        session.flush()
        return market

    @staticmethod
    def get_market(session: Session, market_id: str) -> Optional[Market]:
        """Get market by ID"""
        # Validate input
        market_id = DatabaseInputValidator.validate_market_id(market_id)
        return session.query(Market).filter(Market.market_id == market_id).first()

    @staticmethod
    def get_geopolitical_markets(
        session: Session,
        active_only: bool = True,
        limit: int = 100
    ) -> List[Market]:
        """Get geopolitical markets"""
        # Validate inputs
        limit = DatabaseInputValidator.validate_limit(limit)

        query = session.query(Market)\
            .filter(Market.is_geopolitical == True)

        if active_only:
            query = query.filter(Market.active == True)

        return query.order_by(Market.volume_usd.desc()).limit(limit).all()

    @staticmethod
    def get_market_statistics(session: Session) -> Dict:
        """Get market statistics"""
        total_markets = session.query(func.count(Market.market_id)).scalar()
        active_markets = session.query(func.count(Market.market_id))\
            .filter(Market.active == True)\
            .scalar()
        geopolitical_markets = session.query(func.count(Market.market_id))\
            .filter(Market.is_geopolitical == True)\
            .scalar()

        return {
            'total_markets': total_markets,
            'active_markets': active_markets,
            'geopolitical_markets': geopolitical_markets
        }


class WalletRepository:
    """Repository for wallet metrics operations"""

    @staticmethod
    def get_or_create_wallet_metrics(
        session: Session,
        wallet_address: str
    ) -> WalletMetrics:
        """Get existing wallet metrics or create new"""
        # Validate input
        wallet_address = DatabaseInputValidator.validate_wallet_address(wallet_address)

        metrics = session.query(WalletMetrics)\
            .filter(WalletMetrics.wallet_address == wallet_address)\
            .first()

        if not metrics:
            metrics = WalletMetrics(wallet_address=wallet_address)
            session.add(metrics)
            session.flush()
            logger.debug(f"Created wallet metrics for {(wallet_address or 'unknown')[:10]}...")

        return metrics

    @staticmethod
    def update_wallet_metrics(session: Session, wallet_address: str) -> WalletMetrics:
        """
        Calculate and update wallet performance metrics

        Args:
            session: Database session
            wallet_address: Ethereum wallet address

        Returns:
            Updated WalletMetrics object
        """
        # Validate input (also validated in get_or_create_wallet_metrics)
        wallet_address = DatabaseInputValidator.validate_wallet_address(wallet_address)

        metrics = WalletRepository.get_or_create_wallet_metrics(session, wallet_address)

        # Get all trades for this wallet
        trades = session.query(Trade)\
            .filter(Trade.wallet_address == wallet_address)\
            .all()

        if not trades:
            return metrics

        # Calculate metrics
        metrics.total_trades = len(trades)
        metrics.total_volume_usd = sum(t.bet_size_usd for t in trades)
        metrics.avg_bet_size_usd = metrics.total_volume_usd / metrics.total_trades

        # Find largest bet
        metrics.largest_bet_usd = max(t.bet_size_usd for t in trades)

        # Calculate timing
        timestamps = [t.timestamp for t in trades]
        metrics.first_trade_at = min(timestamps)
        metrics.last_trade_at = max(timestamps)

        # Wallet age
        wallet_age = (datetime.now(timezone.utc) - metrics.first_trade_at).days
        metrics.wallet_age_days = wallet_age

        # Geopolitical focus
        geo_trades = [t for t in trades if t.market_category == 'GEOPOLITICS']
        metrics.geopolitical_trades = len(geo_trades)

        # Timing anomalies
        metrics.trades_outside_hours = sum(
            1 for t in trades
            if t.timestamp.hour < 9 or t.timestamp.hour > 21
        )

        metrics.weekend_trades = sum(
            1 for t in trades
            if t.timestamp.weekday() >= 5
        )

        # Update timestamp
        metrics.last_calculated = datetime.now(timezone.utc)

        session.flush()
        logger.debug(f"Updated wallet metrics for {(wallet_address or 'unknown')[:10]}... ({metrics.total_trades} trades)")

        return metrics

    @staticmethod
    def get_top_wallets(
        session: Session,
        order_by: str = 'volume',
        limit: int = 100
    ) -> List[WalletMetrics]:
        """
        Get top wallets by various metrics

        Args:
            session: Database session
            order_by: Sort field ('volume', 'trades', 'win_rate', 'suspicion')
            limit: Number of wallets to return

        Returns:
            List of WalletMetrics objects
        """
        # Validate inputs
        order_by = DatabaseInputValidator.validate_order_by(order_by)
        limit = DatabaseInputValidator.validate_limit(limit)

        query = session.query(WalletMetrics)

        if order_by == 'volume':
            query = query.order_by(WalletMetrics.total_volume_usd.desc())
        elif order_by == 'trades':
            query = query.order_by(WalletMetrics.total_trades.desc())
        elif order_by == 'win_rate':
            query = query.order_by(WalletMetrics.win_rate.desc())
        elif order_by == 'suspicion':
            query = query.order_by(WalletMetrics.suspicion_flags.desc())

        return query.limit(limit).all()

    @staticmethod
    def get_suspicious_wallets(
        session: Session,
        min_flags: int = 3,
        limit: int = 50
    ) -> List[WalletMetrics]:
        """Get wallets with suspicious patterns"""
        # Validate inputs
        min_flags = DatabaseInputValidator.validate_positive_int(min_flags, "min_flags", allow_zero=True)
        limit = DatabaseInputValidator.validate_limit(limit)

        return session.query(WalletMetrics)\
            .filter(WalletMetrics.suspicion_flags >= min_flags)\
            .order_by(WalletMetrics.suspicion_flags.desc())\
            .limit(limit)\
            .all()


class AlertRepository:
    """Repository for alert operations"""

    @staticmethod
    def create_alert(session: Session, alert_data: Dict) -> Alert:
        """Create a new alert"""
        alert = Alert(**alert_data)
        session.add(alert)
        session.flush()
        logger.info(f"Created alert: {alert.alert_level} - {alert.title}")
        return alert

    @staticmethod
    def get_recent_alerts(
        session: Session,
        hours: int = 24,
        level: str = None,
        limit: int = 100
    ) -> List[Alert]:
        """Get recent alerts"""
        # Validate inputs
        hours = DatabaseInputValidator.validate_hours(hours)
        level = DatabaseInputValidator.validate_optional_alert_level(level)
        limit = DatabaseInputValidator.validate_limit(limit)

        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = session.query(Alert)\
            .filter(Alert.created_at >= start_time)

        if level:
            query = query.filter(Alert.alert_level == level)

        return query.order_by(Alert.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unreviewed_alerts(session: Session, limit: int = 100) -> List[Alert]:
        """Get alerts that haven't been reviewed"""
        # Validate input
        limit = DatabaseInputValidator.validate_limit(limit)

        return session.query(Alert)\
            .filter(Alert.status == 'NEW')\
            .order_by(Alert.suspicion_score.desc(), Alert.created_at.desc())\
            .limit(limit)\
            .all()

    @staticmethod
    def mark_alert_reviewed(
        session: Session,
        alert_id: int,
        reviewed_by: str,
        notes: str = None
    ) -> bool:
        """Mark an alert as reviewed"""
        try:
            # Validate inputs
            alert_id = DatabaseInputValidator.validate_positive_int(alert_id, "alert_id")
            reviewed_by = DatabaseInputValidator.validate_string(reviewed_by, "reviewed_by", max_length=100)
            notes = DatabaseInputValidator.validate_optional_string(notes, "notes", max_length=5000)

            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.status = 'REVIEWED'
                alert.reviewed_at = datetime.now(timezone.utc)
                alert.reviewed_by = reviewed_by
                if notes:
                    alert.notes = notes
                session.flush()
                return True
            return False
        except ValidationError as e:
            logger.error(f"Validation error marking alert reviewed: {e}")
            return False
        except Exception as e:
            logger.error(f"Error marking alert reviewed: {e}")
            return False

    @staticmethod
    def update_notification_status(
        session: Session,
        alert_id: int,
        telegram_sent: bool = None,
        email_sent: bool = None
    ) -> bool:
        """
        Update notification delivery status for an alert

        Args:
            session: Database session
            alert_id: Alert ID
            telegram_sent: Whether Telegram notification was sent
            email_sent: Whether email notification was sent

        Returns:
            True if updated successfully
        """
        try:
            # Validate input
            alert_id = DatabaseInputValidator.validate_positive_int(alert_id, "alert_id")

            alert = session.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                if telegram_sent is not None:
                    alert.telegram_sent = telegram_sent
                if email_sent is not None:
                    alert.email_sent = email_sent
                session.flush()
                logger.debug(f"Updated notification status for alert {alert_id}")
                return True
            return False
        except ValidationError as e:
            logger.error(f"Validation error updating notification status: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating notification status: {e}")
            return False

    @staticmethod
    def get_alert_by_trade_id(session: Session, trade_id: int) -> Optional[Alert]:
        """
        Get alert associated with a trade

        Args:
            session: Database session
            trade_id: Trade ID

        Returns:
            Alert object or None
        """
        try:
            # Validate input
            trade_id = DatabaseInputValidator.validate_positive_int(trade_id, "trade_id")
            return session.query(Alert).filter(Alert.trade_id == trade_id).first()
        except ValidationError as e:
            logger.error(f"Validation error getting alert by trade ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting alert by trade ID: {e}")
            return None


class CheckpointRepository:
    """Repository for monitor checkpoint operations (race condition prevention)"""

    @staticmethod
    def get_checkpoint(
        session: Session,
        monitor_name: str = 'default'
    ) -> Optional[MonitorCheckpoint]:
        """
        Get the current checkpoint for a monitor.

        Args:
            session: Database session
            monitor_name: Name of the monitor

        Returns:
            MonitorCheckpoint object or None if not found
        """
        try:
            monitor_name = DatabaseInputValidator.validate_string(
                monitor_name, "monitor_name", max_length=100
            )
            return session.query(MonitorCheckpoint)\
                .filter(MonitorCheckpoint.monitor_name == monitor_name)\
                .first()
        except ValidationError as e:
            logger.error(f"Validation error getting checkpoint: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting checkpoint: {e}")
            return None

    @staticmethod
    def save_checkpoint(
        session: Session,
        checkpoint_time: datetime,
        monitor_name: str = 'default',
        trades_processed: int = 0
    ) -> Optional[MonitorCheckpoint]:
        """
        Save or update checkpoint after successful processing.

        Args:
            session: Database session
            checkpoint_time: Time to save as checkpoint
            monitor_name: Name of the monitor
            trades_processed: Number of trades processed in this batch

        Returns:
            Updated MonitorCheckpoint object or None on error
        """
        try:
            # Validate inputs
            monitor_name = DatabaseInputValidator.validate_string(
                monitor_name, "monitor_name", max_length=100
            )
            checkpoint_time = DatabaseInputValidator.validate_timestamp(checkpoint_time)
            trades_processed = DatabaseInputValidator.validate_positive_int(
                trades_processed, "trades_processed", allow_zero=True
            )

            # Get or create checkpoint
            checkpoint = session.query(MonitorCheckpoint)\
                .filter(MonitorCheckpoint.monitor_name == monitor_name)\
                .first()

            if checkpoint:
                # Update existing
                checkpoint.last_checkpoint_time = checkpoint_time
                checkpoint.total_trades_processed += trades_processed
            else:
                # Create new
                checkpoint = MonitorCheckpoint(
                    monitor_name=monitor_name,
                    last_checkpoint_time=checkpoint_time,
                    total_trades_processed=trades_processed
                )
                session.add(checkpoint)

            session.flush()
            logger.debug(
                f"Saved checkpoint for {monitor_name}: {checkpoint_time.isoformat()}"
            )
            return checkpoint

        except ValidationError as e:
            logger.error(f"Validation error saving checkpoint: {e}")
            return None
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            return None

    @staticmethod
    def record_failure(
        session: Session,
        monitor_name: str = 'default',
        reason: str = None
    ) -> bool:
        """
        Record a processing failure without updating the checkpoint time.

        Args:
            session: Database session
            monitor_name: Name of the monitor
            reason: Failure reason

        Returns:
            True if recorded successfully
        """
        try:
            monitor_name = DatabaseInputValidator.validate_string(
                monitor_name, "monitor_name", max_length=100
            )
            reason = DatabaseInputValidator.validate_optional_string(
                reason, "reason", max_length=5000
            )

            checkpoint = session.query(MonitorCheckpoint)\
                .filter(MonitorCheckpoint.monitor_name == monitor_name)\
                .first()

            if checkpoint:
                checkpoint.total_failures += 1
                checkpoint.last_failure_time = datetime.now(timezone.utc)
                checkpoint.last_failure_reason = reason
                session.flush()
                return True

            return False

        except Exception as e:
            logger.error(f"Error recording failure: {e}")
            return False


class FailedTradeRepository:
    """Repository for failed trade dead-letter queue operations"""

    @staticmethod
    def add_failed_trade(
        session: Session,
        tx_hash: str,
        trade_data: Dict,
        reason: str
    ) -> Optional[FailedTrade]:
        """
        Add a trade to the failed trades queue.

        Args:
            session: Database session
            tx_hash: Transaction hash
            trade_data: Original trade data
            reason: Failure reason

        Returns:
            FailedTrade object or None on error
        """
        try:
            # Validate inputs
            tx_hash = DatabaseInputValidator.validate_transaction_hash(tx_hash)
            reason = DatabaseInputValidator.validate_string(reason, "reason", max_length=5000)

            # Check if already exists
            existing = session.query(FailedTrade)\
                .filter(FailedTrade.transaction_hash == tx_hash)\
                .first()

            if existing:
                # Update existing
                existing.failure_count += 1
                existing.last_failure_at = datetime.now(timezone.utc)
                existing.failure_reason = reason
                session.flush()
                return existing

            # Create new
            failed_trade = FailedTrade(
                transaction_hash=tx_hash,
                trade_data=trade_data,
                failure_reason=reason
            )
            session.add(failed_trade)
            session.flush()

            logger.info(f"Added failed trade to queue: {tx_hash[:10]}...")
            return failed_trade

        except ValidationError as e:
            logger.error(f"Validation error adding failed trade: {e}")
            return None
        except Exception as e:
            logger.error(f"Error adding failed trade: {e}")
            return None

    @staticmethod
    def get_pending_retries(
        session: Session,
        limit: int = 100
    ) -> List[FailedTrade]:
        """
        Get trades ready for retry.

        Args:
            session: Database session
            limit: Maximum number to return

        Returns:
            List of FailedTrade objects ready for retry
        """
        try:
            limit = DatabaseInputValidator.validate_limit(limit)
            now = datetime.now(timezone.utc)

            return session.query(FailedTrade)\
                .filter(FailedTrade.status == 'PENDING')\
                .filter(FailedTrade.retry_count < FailedTrade.max_retries)\
                .filter(
                    (FailedTrade.next_retry_at == None) |
                    (FailedTrade.next_retry_at <= now)
                )\
                .order_by(FailedTrade.first_failure_at)\
                .limit(limit)\
                .all()

        except Exception as e:
            logger.error(f"Error getting pending retries: {e}")
            return []

    @staticmethod
    def mark_resolved(
        session: Session,
        failed_trade_id: int,
        notes: str = None
    ) -> bool:
        """
        Mark a failed trade as resolved.

        Args:
            session: Database session
            failed_trade_id: ID of the failed trade
            notes: Resolution notes

        Returns:
            True if marked successfully
        """
        try:
            failed_trade_id = DatabaseInputValidator.validate_positive_int(
                failed_trade_id, "failed_trade_id"
            )
            notes = DatabaseInputValidator.validate_optional_string(notes, "notes", max_length=5000)

            failed_trade = session.query(FailedTrade)\
                .filter(FailedTrade.id == failed_trade_id)\
                .first()

            if failed_trade:
                failed_trade.status = 'RESOLVED'
                failed_trade.resolved_at = datetime.now(timezone.utc)
                failed_trade.resolution_notes = notes
                session.flush()
                return True

            return False

        except Exception as e:
            logger.error(f"Error marking failed trade resolved: {e}")
            return False

    @staticmethod
    def increment_retry(
        session: Session,
        failed_trade_id: int,
        backoff_minutes: int = 5
    ) -> bool:
        """
        Increment retry count and schedule next retry.

        Args:
            session: Database session
            failed_trade_id: ID of the failed trade
            backoff_minutes: Base backoff time in minutes

        Returns:
            True if updated successfully
        """
        try:
            failed_trade_id = DatabaseInputValidator.validate_positive_int(
                failed_trade_id, "failed_trade_id"
            )

            failed_trade = session.query(FailedTrade)\
                .filter(FailedTrade.id == failed_trade_id)\
                .first()

            if failed_trade:
                failed_trade.retry_count += 1
                failed_trade.status = 'RETRYING'

                # Exponential backoff: 5, 10, 20, 40, 80 minutes...
                delay_minutes = backoff_minutes * (2 ** (failed_trade.retry_count - 1))
                failed_trade.next_retry_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)

                # If exceeded max retries, mark as abandoned
                if failed_trade.retry_count >= failed_trade.max_retries:
                    failed_trade.status = 'ABANDONED'
                    logger.warning(
                        f"Failed trade {failed_trade.transaction_hash[:10]}... "
                        f"abandoned after {failed_trade.retry_count} retries"
                    )

                session.flush()
                return True

            return False

        except Exception as e:
            logger.error(f"Error incrementing retry: {e}")
            return False
