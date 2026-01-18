"""
Data storage service for persisting API data to database
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Union

from database.connection import get_db_session
from database.models import Trade, Market, WalletMetrics, Alert
from database.repository import (
    TradeRepository,
    MarketRepository,
    WalletRepository,
    AlertRepository
)

logger = logging.getLogger(__name__)


def _parse_datetime(value: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Convert a datetime value to a Python datetime object

    Args:
        value: ISO string, datetime, or None

    Returns:
        datetime object or None
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            # Handle ISO format with Z or timezone
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{value}': {e}")
            return None
    return None


class DataStorageService:
    """
    Service for storing API data to database

    Handles conversion from API format to database models
    """

    @staticmethod
    def store_market(market_data: Dict, session=None) -> Optional[Market]:
        """
        Store or update market in database

        Args:
            market_data: Market data from Polymarket API
            session: Optional existing database session (for transaction consistency)

        Returns:
            Market object or None on error
        """
        def _store_market_impl(sess):
            # Convert API format to DB format
            db_market_data = {
                'market_id': market_data.get('id') or market_data.get('market_id'),
                'slug': market_data.get('slug'),
                'question': market_data.get('question'),
                'description': market_data.get('description'),
                'category': market_data.get('category'),
                'tags': market_data.get('tags', []),  # Store as JSON array
                'active': market_data.get('active', True),
                'closed': market_data.get('closed', False),
                'volume_usd': float(market_data.get('volume', 0) or 0),
                'liquidity_usd': float(market_data.get('liquidity', 0) or 0),
                'close_time': _parse_datetime(market_data.get('close_time')),
                'is_geopolitical': market_data.get('is_geopolitical', False),
                'risk_keywords': market_data.get('risk_keywords', []),
            }

            market = MarketRepository.create_or_update_market(sess, db_market_data)
            logger.info(f"Stored market: {market.market_id}")
            return market

        try:
            # Use existing session if provided (for transaction consistency)
            if session is not None:
                return _store_market_impl(session)
            else:
                # Create new session for standalone calls
                with get_db_session() as new_session:
                    return _store_market_impl(new_session)

        except Exception as e:
            logger.error(f"Error storing market: {e}", exc_info=True)
            return None

    @staticmethod
    def store_trade(
        trade_data: Dict,
        market_data: Dict = None,
        suspicion_score: int = None
    ) -> Optional[Trade]:
        """
        Store trade in database

        Args:
            trade_data: Trade data from Polymarket API
            market_data: Optional market data to cache
            suspicion_score: Optional suspicion score

        Returns:
            Trade object or None on error or duplicate
        """
        try:
            with get_db_session() as session:
                # Store market first if provided (in same transaction)
                # API uses conditionId for market identification
                market_id = (
                    trade_data.get('market_id') or
                    trade_data.get('asset_id') or
                    trade_data.get('conditionId')
                )

                if market_data:
                    # Pass session to ensure atomic transaction
                    DataStorageService.store_market(market_data, session=session)

                # Convert API format to DB format
                db_trade_data = {
                    'transaction_hash': (
                        trade_data.get('transaction_hash') or
                        trade_data.get('transactionHash') or  # API uses camelCase
                        trade_data.get('tx_hash')
                    ),
                    'block_number': trade_data.get('block_number'),
                    'timestamp': trade_data.get('timestamp'),
                    'wallet_address': (
                        trade_data.get('wallet_address') or
                        trade_data.get('proxyWallet') or  # API uses proxyWallet
                        trade_data.get('maker') or
                        trade_data.get('taker')
                    ),
                    'market_id': market_id,
                    'bet_size_usd': float(
                        trade_data.get('bet_size_usd') or
                        trade_data.get('size') or  # API uses size
                        trade_data.get('amount') or 0
                    ),
                    'bet_direction': DataStorageService._normalize_bet_direction(
                        trade_data.get('outcome') or trade_data.get('bet_direction')
                    ),
                    'bet_price': float(trade_data.get('price', 0) or 0),
                    'outcome': trade_data.get('outcome'),
                    # Cache market info
                    'market_title': market_data.get('question') if market_data else '',
                    'market_category': market_data.get('category') if market_data else None,
                    'market_slug': market_data.get('slug') if market_data else None,
                    'market_volume_usd': float(market_data.get('volume', 0) or 0) if market_data else None,
                    'market_liquidity_usd': float(market_data.get('liquidity', 0) or 0) if market_data else None,
                    'market_close_date': _parse_datetime(market_data.get('close_time')) if market_data else None,
                    # Analysis
                    'suspicion_score': suspicion_score,
                    'alert_level': DataStorageService._get_alert_level(suspicion_score) if suspicion_score else None,
                    # Source
                    'api_source': trade_data.get('api_source', 'data_api'),
                }

                # Convert timestamp to datetime if needed
                ts = db_trade_data['timestamp']
                if isinstance(ts, (int, float)):
                    # Unix timestamp - convert to datetime
                    db_trade_data['timestamp'] = datetime.fromtimestamp(ts, tz=timezone.utc)
                elif isinstance(ts, str):
                    db_trade_data['timestamp'] = datetime.fromisoformat(ts.replace('Z', '+00:00'))

                trade = TradeRepository.create_trade(session, db_trade_data)

                if trade:
                    logger.info(f"Stored trade: {trade.id} (${trade.bet_size_usd:,.2f})")

                    # Update wallet metrics asynchronously
                    try:
                        WalletRepository.update_wallet_metrics(session, trade.wallet_address)
                    except Exception as e:
                        logger.warning(f"Failed to update wallet metrics: {e}")

                return trade

        except Exception as e:
            logger.error(f"Error storing trade: {e}", exc_info=True)
            return None

    @staticmethod
    def _get_alert_level(score: int) -> str:
        """
        Determine alert level from suspicion score

        Args:
            score: Suspicion score (0-100)

        Returns:
            Alert level string
        """
        from config import config

        if score >= config.SUSPICION_THRESHOLD_CRITICAL:
            return 'CRITICAL'
        elif score >= config.SUSPICION_THRESHOLD_SUSPICIOUS:
            return 'SUSPICIOUS'
        elif score >= config.SUSPICION_THRESHOLD_WATCH:
            return 'WATCH'
        else:
            return None

    @staticmethod
    def _normalize_bet_direction(direction: str) -> str:
        """
        Normalize bet direction to YES/NO for database constraint.

        API returns various values: 'Yes', 'No', 'Up', 'Down', etc.
        Maps them to 'YES' or 'NO' for database storage.

        Args:
            direction: Raw direction from API

        Returns:
            'YES' or 'NO'
        """
        if not direction:
            return 'YES'

        direction_upper = direction.upper().strip()

        # Direct YES/NO mapping
        if direction_upper in ('YES', 'Y', 'TRUE', '1'):
            return 'YES'
        if direction_upper in ('NO', 'N', 'FALSE', '0'):
            return 'NO'

        # Directional mapping (Up/Down, Long/Short, Buy/Sell)
        if direction_upper in ('UP', 'LONG', 'BUY', 'OVER'):
            return 'YES'
        if direction_upper in ('DOWN', 'SHORT', 'SELL', 'UNDER'):
            return 'NO'

        # Default to YES for unknown values
        return 'YES'

    @staticmethod
    def store_trades_bulk(trades: List[Dict], market_data_map: Dict = None) -> int:
        """
        Store multiple trades efficiently in a single transaction

        Args:
            trades: List of trade data dicts
            market_data_map: Map of market_id -> market_data for caching

        Returns:
            Number of trades successfully stored
        """
        if not trades:
            return 0

        stored_count = 0
        stored_markets = set()  # Track already-stored markets to avoid duplicates

        try:
            with get_db_session() as session:
                for trade in trades:
                    try:
                        # API uses conditionId for market identification
                        market_id = (
                            trade.get('market_id') or
                            trade.get('asset_id') or
                            trade.get('conditionId')
                        )
                        market_data = market_data_map.get(market_id) if market_data_map else None

                        # Store market once per unique market_id (in same transaction)
                        if market_data and market_id and market_id not in stored_markets:
                            DataStorageService.store_market(market_data, session=session)
                            stored_markets.add(market_id)

                        # Build trade data
                        db_trade_data = {
                            'transaction_hash': (
                                trade.get('transaction_hash') or
                                trade.get('transactionHash') or  # API uses camelCase
                                trade.get('tx_hash')
                            ),
                            'block_number': trade.get('block_number'),
                            'timestamp': trade.get('timestamp'),
                            'wallet_address': (
                                trade.get('wallet_address') or
                                trade.get('proxyWallet') or  # API uses proxyWallet
                                trade.get('maker') or
                                trade.get('taker')
                            ),
                            'market_id': market_id,
                            'bet_size_usd': float(
                                trade.get('bet_size_usd') or
                                trade.get('size') or  # API uses size
                                trade.get('amount') or 0
                            ),
                            'bet_direction': DataStorageService._normalize_bet_direction(
                                trade.get('outcome') or trade.get('bet_direction')
                            ),
                            'bet_price': float(trade.get('price', 0) or 0),
                            'outcome': trade.get('outcome'),
                            'market_title': market_data.get('question') if market_data else '',
                            'market_category': market_data.get('category') if market_data else None,
                            'market_slug': market_data.get('slug') if market_data else None,
                            'market_volume_usd': float(market_data.get('volume', 0) or 0) if market_data else None,
                            'market_liquidity_usd': float(market_data.get('liquidity', 0) or 0) if market_data else None,
                            'market_close_date': _parse_datetime(market_data.get('close_time')) if market_data else None,
                            'api_source': trade.get('api_source', 'data_api'),
                        }

                        # Convert timestamp to datetime if needed
                        ts = db_trade_data['timestamp']
                        if isinstance(ts, (int, float)):
                            db_trade_data['timestamp'] = datetime.fromtimestamp(ts, tz=timezone.utc)
                        elif isinstance(ts, str):
                            db_trade_data['timestamp'] = datetime.fromisoformat(ts.replace('Z', '+00:00'))

                        result = TradeRepository.create_trade(session, db_trade_data)
                        if result:
                            stored_count += 1

                    except Exception as e:
                        # Log individual trade errors but continue processing
                        logger.warning(f"Error storing trade in bulk: {e}")
                        continue

                logger.info(f"Bulk stored {stored_count}/{len(trades)} trades in single transaction")

        except Exception as e:
            logger.error(f"Error in bulk trade storage: {e}", exc_info=True)

        return stored_count

    @staticmethod
    def get_recent_trade_stats(hours: int = 24) -> Dict:
        """Get statistics for recent trades"""
        with get_db_session() as session:
            return TradeRepository.get_trade_statistics(session, hours)

    @staticmethod
    def get_market_stats() -> Dict:
        """Get market statistics"""
        with get_db_session() as session:
            return MarketRepository.get_market_statistics(session)

    @staticmethod
    def store_alert(
        trade: Trade,
        scoring_result: Dict,
        telegram_sent: bool = False,
        email_sent: bool = False
    ) -> Optional[Alert]:
        """
        Create alert for suspicious trade

        Args:
            trade: Trade object
            scoring_result: Scoring algorithm results
            telegram_sent: Whether Telegram notification was sent
            email_sent: Whether email notification was sent

        Returns:
            Alert object or None on error
        """
        try:
            alert_level = scoring_result.get('alert_level')
            if not alert_level:
                return None

            with get_db_session() as session:
                # Generate alert content
                market_title = trade.market_title or 'Unknown Market'
                bet_size = trade.bet_size_usd
                wallet = trade.wallet_address

                title = f"{alert_level}: ${bet_size:,.0f} bet on {market_title[:80]}"

                # Build message with key factors
                breakdown = scoring_result.get('breakdown', {})
                message_parts = []
                for factor_name, factor_data in breakdown.items():
                    if factor_data['score'] > 0:
                        message_parts.append(
                            f"{factor_name}: {factor_data['score']}/{factor_data['max']} - {factor_data['reason']}"
                        )
                message = "\n".join(message_parts)

                # Store evidence as JSON
                import json
                evidence = json.dumps({
                    'scoring_result': scoring_result,
                    'trade_data': {
                        'transaction_hash': trade.transaction_hash,
                        'bet_size_usd': trade.bet_size_usd,
                        'bet_direction': trade.bet_direction,
                        'bet_price': trade.bet_price,
                        'timestamp': trade.timestamp.isoformat() if trade.timestamp else None
                    }
                })

                alert_data = {
                    'alert_level': alert_level,
                    'alert_type': 'HIGH_SCORE',
                    'trade_id': trade.id,
                    'wallet_address': wallet,
                    'market_id': trade.market_id,
                    'title': title,
                    'message': message,
                    'suspicion_score': scoring_result.get('total_score', 0),
                    'evidence': evidence,
                    'status': 'NEW',
                    'telegram_sent': telegram_sent,
                    'email_sent': email_sent
                }

                alert = AlertRepository.create_alert(session, alert_data)
                return alert

        except Exception as e:
            logger.error(f"Error storing alert: {e}", exc_info=True)
            return None

    @staticmethod
    def update_alert_notification_status(
        trade_id: int,
        telegram_sent: bool = None,
        email_sent: bool = None
    ) -> bool:
        """
        Update notification status for an alert

        Args:
            trade_id: Trade ID associated with alert
            telegram_sent: Whether Telegram was sent
            email_sent: Whether email was sent

        Returns:
            True if updated successfully
        """
        try:
            with get_db_session() as session:
                # Find alert by trade ID
                alert = AlertRepository.get_alert_by_trade_id(session, trade_id)
                if alert:
                    return AlertRepository.update_notification_status(
                        session,
                        alert.id,
                        telegram_sent=telegram_sent,
                        email_sent=email_sent
                    )
                return False
        except Exception as e:
            logger.error(f"Error updating alert notification status: {e}")
            return False

    @staticmethod
    def get_wallet_metrics(wallet_address: str) -> Optional[WalletMetrics]:
        """Get metrics for a specific wallet"""
        with get_db_session() as session:
            return WalletRepository.get_or_create_wallet_metrics(session, wallet_address)

    @staticmethod
    def update_wallet_metrics(wallet_address: str) -> WalletMetrics:
        """Update metrics for a wallet"""
        with get_db_session() as session:
            return WalletRepository.update_wallet_metrics(session, wallet_address)
