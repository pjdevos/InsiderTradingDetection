"""
Real-time trade monitoring system for Polymarket
"""
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Callable

from api.client import PolymarketAPIClient
from config import config
from database.storage import DataStorageService
from database.connection import init_db, get_db_session
from database.repository import CheckpointRepository, FailedTradeRepository
from analysis.scoring import SuspicionScorer
from alerts import send_trade_alert, send_email_alert


logger = logging.getLogger(__name__)


class RealTimeTradeMonitor:
    """
    Continuously monitor Polymarket for large trades on geopolitical markets.

    Uses database-backed checkpoints to prevent race conditions and ensure
    no trades are missed across restarts or failures.
    """

    def __init__(self,
                 api_client: PolymarketAPIClient,
                 min_bet_size: float = None,
                 interval_seconds: int = None,
                 monitor_name: str = 'default'):
        """
        Initialize trade monitor

        Args:
            api_client: Polymarket API client instance
            min_bet_size: Minimum bet size to track (USD)
            interval_seconds: Polling interval
            monitor_name: Name for checkpoint persistence (allows multiple monitors)
        """
        self.api = api_client
        self.min_bet_size = min_bet_size or config.MIN_BET_SIZE_USD
        self.interval_seconds = interval_seconds or config.POLL_INTERVAL_SECONDS
        self.monitor_name = monitor_name
        self.last_check_time = datetime.now(timezone.utc)
        self.running = False
        self.trade_callbacks = []

        # Try to load checkpoint from database
        self._load_checkpoint()

        logger.info(
            f"RealTimeTradeMonitor initialized: "
            f"min_bet=${self.min_bet_size}, interval={self.interval_seconds}s, "
            f"monitor={self.monitor_name}, checkpoint={self.last_check_time.isoformat()}"
        )

    def _load_checkpoint(self):
        """Load checkpoint from database if available"""
        try:
            with get_db_session() as session:
                checkpoint = CheckpointRepository.get_checkpoint(
                    session, self.monitor_name
                )
                if checkpoint:
                    self.last_check_time = checkpoint.last_checkpoint_time
                    logger.info(
                        f"Loaded checkpoint for {self.monitor_name}: "
                        f"{checkpoint.last_checkpoint_time.isoformat()}, "
                        f"total processed: {checkpoint.total_trades_processed}"
                    )
                else:
                    logger.info(
                        f"No checkpoint found for {self.monitor_name}, "
                        f"starting from now"
                    )
        except Exception as e:
            logger.warning(
                f"Could not load checkpoint, starting from now: {e}"
            )

    def _save_checkpoint(self, checkpoint_time: datetime, trades_processed: int = 0):
        """Save checkpoint to database"""
        try:
            with get_db_session() as session:
                CheckpointRepository.save_checkpoint(
                    session,
                    checkpoint_time=checkpoint_time,
                    monitor_name=self.monitor_name,
                    trades_processed=trades_processed
                )
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _record_failure(self, reason: str):
        """Record processing failure in database"""
        try:
            with get_db_session() as session:
                CheckpointRepository.record_failure(
                    session,
                    monitor_name=self.monitor_name,
                    reason=reason
                )
                session.commit()
        except Exception as e:
            logger.error(f"Failed to record failure: {e}")

    def _add_to_dead_letter_queue(self, trade: Dict, reason: str):
        """Add a failed trade to the dead-letter queue"""
        try:
            tx_hash = trade.get('transaction_hash') or trade.get('hash') or 'unknown'
            if tx_hash == 'unknown':
                logger.warning("Cannot add trade to dead-letter queue: no transaction hash")
                return

            with get_db_session() as session:
                FailedTradeRepository.add_failed_trade(
                    session,
                    tx_hash=tx_hash,
                    trade_data=trade,
                    reason=reason
                )
                session.commit()
        except Exception as e:
            logger.error(f"Failed to add trade to dead-letter queue: {e}")

    def process_dead_letter_queue(self, limit: int = 10) -> int:
        """
        Process trades from the dead-letter queue.

        Args:
            limit: Maximum number of trades to process

        Returns:
            Number of trades successfully processed
        """
        processed = 0
        try:
            with get_db_session() as session:
                failed_trades = FailedTradeRepository.get_pending_retries(session, limit)

                if not failed_trades:
                    return 0

                logger.info(f"Processing {len(failed_trades)} trades from dead-letter queue")

                for failed_trade in failed_trades:
                    try:
                        # Retry processing the trade
                        trade_data = failed_trade.trade_data
                        self.process_trade(trade_data)

                        # If successful, mark as resolved
                        FailedTradeRepository.mark_resolved(
                            session,
                            failed_trade.id,
                            notes="Successfully processed on retry"
                        )
                        processed += 1
                        logger.info(
                            f"Successfully processed failed trade {failed_trade.transaction_hash[:10]}..."
                        )

                    except Exception as e:
                        # Increment retry count and schedule next retry
                        FailedTradeRepository.increment_retry(session, failed_trade.id)
                        logger.warning(
                            f"Retry failed for trade {failed_trade.transaction_hash[:10]}...: {e}"
                        )

                session.commit()

        except Exception as e:
            logger.error(f"Error processing dead-letter queue: {e}")

        return processed

    def register_callback(self, callback: Callable[[Dict], None]):
        """
        Register a callback function to be called when large trade is detected

        Args:
            callback: Function that takes a trade dict as parameter
        """
        self.trade_callbacks.append(callback)
        logger.info(f"Registered callback: {callback.__name__}")

    def poll_recent_trades(self):
        """
        Poll API for new trades since last check.

        Race condition prevention:
        - Capture poll_start_time BEFORE fetching to ensure no trades are missed
        - Use a small overlap buffer to handle clock skew and API delays
        - Only update last_check_time AFTER all trades are successfully processed
        - Process trades in batch to ensure atomicity
        """
        # Capture the current time BEFORE fetching - this prevents race conditions
        # where trades arrive during our fetch/process cycle
        poll_start_time = datetime.now(timezone.utc)

        # Small overlap buffer (5 seconds) to handle clock skew between our system
        # and the API server, and any propagation delays
        overlap_buffer = timedelta(seconds=5)

        try:
            # Get trades since last check (with overlap to catch edge cases)
            fetch_from = self.last_check_time - overlap_buffer
            trades = self.api.get_trades(
                start_time=fetch_from,
                limit=1000
            )

            if not trades:
                logger.debug("No new trades found")
                # Safe to update timestamp even with no trades
                self.last_check_time = poll_start_time
                return

            logger.info(f"Found {len(trades)} new trades")

            # Filter for large bets
            large_trades = [
                t for t in trades
                if self.api.calculate_bet_size_usd(t) >= self.min_bet_size
            ]

            if large_trades:
                logger.info(f"Found {len(large_trades)} large trades (>=${self.min_bet_size})")

            # Process all large trades
            # Note: Due to overlap buffer, some trades may be processed multiple times.
            # Duplicates are safely ignored by the database (unique constraint on transaction_hash)
            processed_count = 0
            failed_count = 0

            for trade in large_trades:
                try:
                    self.process_trade(trade)
                    processed_count += 1
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to process trade: {e}", exc_info=True)
                    # Continue processing other trades, but don't update timestamp
                    # This ensures failed trades will be retried on next poll

            # Only update checkpoint if ALL trades were processed successfully
            # This ensures failed trades are retried on the next poll (with overlap buffer)
            if failed_count == 0:
                self.last_check_time = poll_start_time
                # Save checkpoint to database for persistence across restarts
                self._save_checkpoint(poll_start_time, processed_count)
                if large_trades:
                    logger.info(f"Successfully processed {processed_count} trades, checkpoint saved: {poll_start_time.isoformat()}")
            else:
                logger.warning(
                    f"Processed {processed_count}/{len(large_trades)} trades successfully, but {failed_count} failed. "
                    f"Checkpoint NOT updated - failed trades will be retried on next poll."
                )
                # Record failure in database
                self._record_failure(f"Failed to process {failed_count} trades")

        except Exception as e:
            # Don't update last_check_time on failure - trades will be refetched
            logger.error(f"Error in polling loop: {e}", exc_info=True)
            self._record_failure(str(e))

    def process_trade(self, trade: Dict):
        """
        Process a large trade:
        1. Get market metadata
        2. Check if geopolitical
        3. Store in database
        4. Call registered callbacks
        5. Log the trade

        Args:
            trade: Trade object from API
        """
        try:
            # Support multiple field names from different API endpoints
            market_id = trade.get('market_id') or trade.get('asset_id') or trade.get('conditionId')
            bet_size = self.api.calculate_bet_size_usd(trade)
            wallet = trade.get('wallet_address') or trade.get('maker') or trade.get('proxyWallet')

            logger.info(
                f"Processing large trade: ${bet_size:,.2f} "
                f"by {wallet[:10] if wallet else 'unknown'}..."
            )

            # Get market metadata - try API first (skip hex IDs), then fall back to title
            import re
            market = None
            category = None

            # Only try API lookup for numeric market IDs (not hex conditionIds)
            if market_id and not str(market_id).startswith('0x'):
                market = self.api.get_market(str(market_id))

            if market:
                category = self.api.categorize_market(market)
            elif trade.get('title'):
                # Use title field directly for categorization (no API call needed)
                title = trade.get('title', '').lower()

                # Blacklist for false positives (sports, esports, entertainment)
                # Note: Removed 'vs.', 'vs ', ' map ', 'winner', 'loser' - can appear in political markets
                FALSE_POSITIVE_PATTERNS = [
                    'counter-strike', 'counter strike', 'csgo', 'cs2', 'cs:',
                    'dota', 'league of legends', 'valorant', 'overwatch',
                    'nba', 'nfl', 'mlb', 'nhl', 'mls',
                    'lakers', 'celtics', 'warriors', 'bulls', 'heat',
                    'yankees', 'dodgers', 'red sox', 'cubs', 'mets',
                    'patriots', 'cowboys', 'packers', 'chiefs', 'eagles',
                    'rangers', 'bruins', 'penguins', 'capitals', 'senators',
                    'manchester', 'liverpool', 'chelsea', 'arsenal', 'barcelona',
                    'real madrid', 'bayern', 'juventus', 'psg',
                    'super bowl', 'world series', 'stanley cup', 'finals',
                    'playoff', 'championship', 'tournament', 'esport',
                ]

                # Check blacklist first
                is_blacklisted = any(bp in title for bp in FALSE_POSITIVE_PATTERNS)

                is_political = False
                if not is_blacklisted:
                    for kw in config.GEOPOLITICAL_KEYWORDS:
                        # Word boundary for short keywords to avoid false positives
                        if len(kw) <= 4:
                            if re.search(r'\b' + re.escape(kw) + r'\b', title):
                                is_political = True
                                break
                        elif kw in title:
                            is_political = True
                            break

                if is_political:
                    category = 'GEOPOLITICS'
                    # Include market_id from conditionId for database storage
                    market = {
                        'id': market_id or trade.get('conditionId', 'unknown'),
                        'question': trade.get('title') or 'Unknown'
                    }
                else:
                    category = 'OTHER'

            # Only process geopolitical markets
            if category != 'GEOPOLITICS':
                logger.debug(f"Skipping non-geopolitical market: {category}")
                return

            # Enhance trade with market data
            trade['market'] = market
            trade['category'] = category
            trade['bet_size_usd'] = bet_size

            logger.info(
                f"Geopolitical trade detected: {market.get('question', 'Unknown')[:60]}"
            )

            # Calculate suspicion score
            try:
                scoring_result = SuspicionScorer.calculate_score(trade, market)
                suspicion_score = scoring_result['total_score']
                alert_level = scoring_result['alert_level']

                logger.info(
                    f"Suspicion score: {suspicion_score}/100 "
                    f"({alert_level or 'NORMAL'})"
                )

                # Log score breakdown for high-suspicion trades
                if suspicion_score >= config.SUSPICION_THRESHOLD_WATCH:
                    breakdown = scoring_result['breakdown']
                    logger.info("Score breakdown:")
                    for factor, data in breakdown.items():
                        if data['score'] > 0:
                            logger.info(f"  - {factor}: {data['score']}/{data['max']} - {data['reason']}")

            except Exception as e:
                logger.error(f"Error calculating suspicion score: {e}")
                suspicion_score = None
                alert_level = None

            # Store in database
            # NOTE: store_trade() returns None for duplicates, raises for real errors
            stored_trade = None
            try:
                stored_trade = DataStorageService.store_trade(
                    trade_data=trade,
                    market_data=market,
                    suspicion_score=suspicion_score
                )
            except Exception as e:
                logger.error(f"Failed to store trade: {e}")
                stored_trade = None

            if stored_trade:
                logger.info(
                    f"Stored trade in database: ID={stored_trade.id}, "
                    f"Score={stored_trade.suspicion_score or 0}/100, "
                    f"Alert={stored_trade.alert_level or 'NONE'}"
                )
            else:
                logger.debug("Trade not stored (duplicate or skipped)")

            # Store alert in database if trade was stored and alert_level exists
            stored_alert = None
            if stored_trade and alert_level:
                try:
                    stored_alert = DataStorageService.store_alert(
                        trade=stored_trade,
                        scoring_result=scoring_result
                    )
                    if stored_alert:
                        logger.info(f"Stored alert in database: ID={stored_alert.id}")
                except Exception as e:
                    logger.error(f"Failed to store alert: {e}", exc_info=True)

            # Send Telegram alert if needed
            telegram_sent = False
            if alert_level and suspicion_score >= config.SUSPICION_THRESHOLD_WATCH:
                try:
                    telegram_sent = send_trade_alert(trade, scoring_result)
                    if telegram_sent:
                        logger.info(f"Telegram alert sent: {alert_level}")
                    else:
                        logger.debug(f"Telegram alert not sent (rate limited or not configured)")
                except Exception as e:
                    logger.error(f"Failed to send Telegram alert: {e}")

            # Send Email alert for SUSPICIOUS and CRITICAL
            email_sent = False
            if alert_level in ['SUSPICIOUS', 'CRITICAL']:
                try:
                    email_sent = send_email_alert(trade, scoring_result)
                    if email_sent:
                        logger.info(f"Email alert sent: {alert_level}")
                    else:
                        logger.debug(f"Email alert not sent (not configured)")
                except Exception as e:
                    logger.error(f"Failed to send Email alert: {e}")

            # Update alert notification status in database
            if stored_trade and (telegram_sent or email_sent):
                try:
                    DataStorageService.update_alert_notification_status(
                        trade_id=stored_trade.id,
                        telegram_sent=telegram_sent,
                        email_sent=email_sent
                    )
                    logger.debug("Updated alert notification status")
                except Exception as e:
                    logger.error(f"Failed to update alert notification status: {e}")

            # Call all registered callbacks
            for callback in self.trade_callbacks:
                try:
                    callback(trade)
                except Exception as e:
                    logger.error(f"Error in callback {callback.__name__}: {e}")

        except Exception as e:
            logger.error(f"Error processing trade: {e}", exc_info=True)
            # Add to dead-letter queue for later retry
            self._add_to_dead_letter_queue(trade, str(e))
            # Re-raise to signal failure to poll_recent_trades
            raise

    def start(self):
        """
        Start the monitoring loop
        """
        logger.info("Starting real-time trade monitoring...")

        # Initialize database connection
        try:
            init_db()
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            raise

        self.running = True
        self.last_check_time = datetime.now(timezone.utc)

        try:
            while self.running:
                self.poll_recent_trades()
                time.sleep(self.interval_seconds)

        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
            self.running = False
        except Exception as e:
            logger.error(f"Fatal error in monitoring loop: {e}", exc_info=True)
            self.running = False

    def stop(self):
        """
        Stop the monitoring loop
        """
        logger.info("Stopping trade monitor...")
        self.running = False

    def get_recent_large_trades(self,
                                hours: int = 24,
                                geopolitical_only: bool = True) -> List[Dict]:
        """
        Get large trades from the last N hours

        Args:
            hours: Number of hours to look back
            geopolitical_only: Only return geopolitical market trades

        Returns:
            List of large trades
        """
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        logger.info(f"Fetching large trades from last {hours} hours")

        trades = self.api.get_trades(
            start_time=start_time,
            limit=1000
        )

        # Filter for large bets
        large_trades = [
            t for t in trades
            if self.api.calculate_bet_size_usd(t) >= self.min_bet_size
        ]

        if not geopolitical_only:
            return large_trades

        # Filter for geopolitical markets
        import re
        geopolitical_trades = []

        # Blacklist for false positives (sports, esports, entertainment)
        # Note: Removed 'vs.', 'vs ', ' map ', 'winner', 'loser' - can appear in political markets
        FALSE_POSITIVE_PATTERNS = [
            'counter-strike', 'counter strike', 'csgo', 'cs2', 'cs:',
            'dota', 'league of legends', 'valorant', 'overwatch',
            'nba', 'nfl', 'mlb', 'nhl', 'mls',
            'lakers', 'celtics', 'warriors', 'bulls', 'heat',
            'yankees', 'dodgers', 'red sox', 'cubs', 'mets',
            'patriots', 'cowboys', 'packers', 'chiefs', 'eagles',
            'rangers', 'bruins', 'penguins', 'capitals', 'senators',
            'manchester', 'liverpool', 'chelsea', 'arsenal', 'barcelona',
            'real madrid', 'bayern', 'juventus', 'psg',
            'super bowl', 'world series', 'stanley cup', 'finals',
            'playoff', 'championship', 'tournament', 'esport',
        ]

        for trade in large_trades:
            # Quick check using title field if available (faster, no API call)
            title = trade.get('title', '').lower()
            if title:
                # Check blacklist first
                is_blacklisted = any(bp in title for bp in FALSE_POSITIVE_PATTERNS)

                is_political = False
                if not is_blacklisted:
                    for kw in config.GEOPOLITICAL_KEYWORDS:
                        # Use word boundary for short keywords to avoid false positives
                        if len(kw) <= 4:
                            if re.search(r'\b' + re.escape(kw) + r'\b', title):
                                is_political = True
                                break
                        elif kw in title:
                            is_political = True
                            break

                if is_political:
                    trade['market'] = {
                        'id': trade.get('conditionId', 'unknown'),
                        'question': trade.get('title') or 'Unknown'
                    }
                    trade['category'] = 'GEOPOLITICS'
                    trade['bet_size_usd'] = self.api.calculate_bet_size_usd(trade)
                    geopolitical_trades.append(trade)
                    continue

            # Fall back to market lookup (skip hex conditionIds - they don't work with API)
            market_id = trade.get('market_id') or trade.get('asset_id')
            if market_id and not str(market_id).startswith('0x'):
                market = self.api.get_market(str(market_id))
                if market and self.api.categorize_market(market) == 'GEOPOLITICS':
                    trade['market'] = market
                    trade['bet_size_usd'] = self.api.calculate_bet_size_usd(trade)
                    geopolitical_trades.append(trade)

        logger.info(
            f"Found {len(geopolitical_trades)} large geopolitical trades "
            f"from {len(large_trades)} total large trades"
        )

        return geopolitical_trades

    def get_market_summary(self, market_id: str) -> Dict:
        """
        Get summary of trading activity for a specific market

        Args:
            market_id: Market identifier

        Returns:
            Summary dict with stats
        """
        market = self.api.get_market(market_id)
        if not market:
            return {}

        # Get recent trades for this market
        trades = self.api.get_trades(market_id=market_id, limit=500)

        # Calculate stats
        total_volume = sum(self.api.calculate_bet_size_usd(t) for t in trades)
        large_trades = [t for t in trades if self.api.calculate_bet_size_usd(t) >= self.min_bet_size]
        avg_bet_size = total_volume / len(trades) if trades else 0

        return {
            'market': market,
            'total_trades': len(trades),
            'total_volume_usd': total_volume,
            'large_trades': len(large_trades),
            'avg_bet_size_usd': avg_bet_size,
            'category': self.api.categorize_market(market)
        }
