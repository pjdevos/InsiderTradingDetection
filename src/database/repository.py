"""
Data repository layer for database operations
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.models import Trade, Market, WalletMetrics, Alert
from database.connection import get_db_session

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
            trade = Trade(**trade_data)
            session.add(trade)
            session.flush()  # Get the ID
            logger.debug(f"Created trade: {trade.id} (wallet: {trade.wallet_address[:10]}..., ${trade.bet_size_usd:,.2f})")
            return trade

        except IntegrityError as e:
            session.rollback()
            error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
            if 'UNIQUE constraint failed: trades.transaction_hash' in error_str:
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
        return session.query(Trade).filter(Trade.transaction_hash == tx_hash).first()

    @staticmethod
    def get_trades_by_wallet(
        session: Session,
        wallet_address: str,
        limit: int = 100
    ) -> List[Trade]:
        """Get all trades for a wallet"""
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
            trade = session.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.suspicion_score = score
                if alert_level:
                    trade.alert_level = alert_level
                session.flush()
                logger.info(f"Updated suspicion score for trade {trade_id}: {score}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating suspicion score: {e}")
            return False

    @staticmethod
    def get_trade_statistics(session: Session, hours: int = 24) -> Dict:
        """Get trade statistics for the last N hours"""
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
        return session.query(Market).filter(Market.market_id == market_id).first()

    @staticmethod
    def get_geopolitical_markets(
        session: Session,
        active_only: bool = True,
        limit: int = 100
    ) -> List[Market]:
        """Get geopolitical markets"""
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
        metrics = session.query(WalletMetrics)\
            .filter(WalletMetrics.wallet_address == wallet_address)\
            .first()

        if not metrics:
            metrics = WalletMetrics(wallet_address=wallet_address)
            session.add(metrics)
            session.flush()
            logger.debug(f"Created wallet metrics for {wallet_address[:10]}...")

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
        logger.debug(f"Updated wallet metrics for {wallet_address[:10]}... ({metrics.total_trades} trades)")

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
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        query = session.query(Alert)\
            .filter(Alert.created_at >= start_time)

        if level:
            query = query.filter(Alert.alert_level == level)

        return query.order_by(Alert.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unreviewed_alerts(session: Session, limit: int = 100) -> List[Alert]:
        """Get alerts that haven't been reviewed"""
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
            return session.query(Alert).filter(Alert.trade_id == trade_id).first()
        except Exception as e:
            logger.error(f"Error getting alert by trade ID: {e}")
            return None
