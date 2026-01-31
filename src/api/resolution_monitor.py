"""
Resolution Monitor - Tracks market outcomes and triggers win/loss calculation

This module polls Polymarket API for resolved markets and stores resolution data.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import time

from api.client import PolymarketAPIClient
from blockchain.client import BlockchainClient
from database.connection import get_db_session
from database.models import Market, Trade, MarketResolution
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class ResolutionMonitor:
    """
    Monitors Polymarket for resolved markets and stores resolution data.

    Uses price inference to determine market outcomes (winning outcome price -> ~1.0)
    """

    def __init__(
        self,
        api_client: PolymarketAPIClient = None,
        poll_interval_minutes: int = 30,
        resolution_threshold: float = 0.95
    ):
        """
        Initialize resolution monitor.

        Args:
            api_client: Polymarket API client (creates one if not provided)
            poll_interval_minutes: How often to check for new resolutions
            resolution_threshold: Price threshold to consider resolved (default 0.95)
        """
        self.api_client = api_client or PolymarketAPIClient()
        self.poll_interval = poll_interval_minutes * 60  # Convert to seconds
        self.resolution_threshold = resolution_threshold
        self._running = False

        logger.info(
            f"ResolutionMonitor initialized (poll_interval={poll_interval_minutes}min, "
            f"threshold={resolution_threshold})"
        )

    def poll_closed_markets(self, limit: int = 100) -> List[Dict]:
        """
        Fetch recently closed markets from Polymarket API.

        Args:
            limit: Maximum number of markets to fetch

        Returns:
            List of closed market data dicts
        """
        try:
            # Get closed markets from API
            markets = self.api_client.get_markets(closed=True, limit=limit)

            logger.info(f"Fetched {len(markets)} closed markets from API")
            return markets

        except Exception as e:
            logger.error(f"Error fetching closed markets: {e}")
            return []

    def check_blockchain_resolution(self, condition_id: str) -> Optional[Dict]:
        """
        Check market resolution directly from blockchain.

        Args:
            condition_id: The market's conditionId (bytes32 hex string)

        Returns:
            Resolution data dict or None if not resolved/error
        """
        if not condition_id:
            return None

        try:
            blockchain_client = BlockchainClient()
            result = blockchain_client.get_market_resolution(condition_id)

            if result and result.get('resolved'):
                return {
                    'winning_outcome': result['winning_outcome'],
                    'confidence': 1.0,  # Blockchain is authoritative
                    'resolution_source': 'blockchain',
                    'payout_numerators': result.get('payout_numerators', []),
                    'payout_denominator': result.get('payout_denominator', 0),
                }
            return None

        except Exception as e:
            logger.debug(f"Blockchain resolution check failed for {condition_id[:20]}...: {e}")
            return None

    def infer_resolution(self, market_data: Dict) -> Optional[Dict]:
        """
        Detect market resolution using blockchain first, then price inference.

        Args:
            market_data: Market data dict from API

        Returns:
            Resolution data dict or None if not resolvable
        """
        market_id = market_data.get('id') or market_data.get('conditionId')
        condition_id = market_data.get('conditionId')

        # Method 1: Check blockchain directly (authoritative)
        if condition_id:
            blockchain_result = self.check_blockchain_resolution(condition_id)
            if blockchain_result:
                logger.info(f"Blockchain resolution found for {market_id[:20] if market_id else 'unknown'}...")
                return {
                    'market_id': market_id,
                    'condition_id': condition_id,
                    'winning_outcome': blockchain_result['winning_outcome'],
                    'confidence': blockchain_result['confidence'],
                    'resolution_source': 'blockchain',
                    'payout_numerators': blockchain_result.get('payout_numerators'),
                    'payout_denominator': blockchain_result.get('payout_denominator'),
                    'resolved_at': datetime.now(timezone.utc),
                    'market_question': market_data.get('question', '')[:200]
                }

        # Method 2: Fall back to price inference
        outcome_prices = market_data.get('outcomePrices')
        if not outcome_prices:
            return None

        result = BlockchainClient.infer_resolution_from_prices(
            outcome_prices,
            threshold=self.resolution_threshold
        )

        if result and result.get('resolved'):
            return {
                'market_id': market_id,
                'condition_id': condition_id,
                'winning_outcome': result['winning_outcome'],
                'confidence': result['confidence'],
                'resolution_source': 'price_inference',
                'final_yes_price': float(outcome_prices[0]) if isinstance(outcome_prices, list) else None,
                'final_no_price': float(outcome_prices[1]) if isinstance(outcome_prices, list) else None,
                'resolved_at': datetime.now(timezone.utc),
                'market_question': market_data.get('question', '')[:200]
            }

        return None

    def store_resolution(self, resolution_data: Dict) -> Optional[MarketResolution]:
        """
        Store a market resolution in the database.

        Args:
            resolution_data: Resolution data dict

        Returns:
            MarketResolution object or None if already exists/failed
        """
        market_id = resolution_data.get('market_id')
        if not market_id:
            logger.warning("Cannot store resolution: no market_id")
            return None

        try:
            with get_db_session() as session:
                # Check if resolution already exists
                existing = session.query(MarketResolution).filter(
                    MarketResolution.market_id == market_id
                ).first()

                if existing:
                    logger.debug(f"Resolution already exists for market {market_id[:20]}...")
                    return existing

                # Create new resolution
                resolution = MarketResolution(
                    market_id=market_id,
                    condition_id=resolution_data.get('condition_id'),
                    winning_outcome=resolution_data['winning_outcome'],
                    confidence=resolution_data['confidence'],
                    resolution_source=resolution_data['resolution_source'],
                    final_yes_price=resolution_data.get('final_yes_price'),
                    final_no_price=resolution_data.get('final_no_price'),
                    resolved_at=resolution_data.get('resolved_at', datetime.now(timezone.utc)),
                    created_at=datetime.now(timezone.utc)
                )

                session.add(resolution)
                session.flush()

                logger.info(
                    f"Stored resolution: {market_id[:20]}... -> {resolution.winning_outcome} "
                    f"(confidence: {resolution.confidence:.2%})"
                )

                return resolution

        except Exception as e:
            logger.error(f"Error storing resolution for {market_id}: {e}")
            return None

    def get_unresolved_market_ids(self) -> List[str]:
        """
        Get market IDs that have trades but no resolution record.

        Returns:
            List of market IDs needing resolution check
        """
        try:
            with get_db_session() as session:
                # Find markets with trades but no resolution
                # Using a subquery to find markets that have trades
                markets_with_trades = session.query(Trade.market_id).distinct().subquery()

                # Find which of those don't have resolutions
                resolved_markets = session.query(MarketResolution.market_id).subquery()

                unresolved = session.query(markets_with_trades.c.market_id).filter(
                    ~markets_with_trades.c.market_id.in_(
                        session.query(resolved_markets.c.market_id)
                    )
                ).all()

                market_ids = [m[0] for m in unresolved if m[0]]
                logger.info(f"Found {len(market_ids)} markets with trades but no resolution")
                return market_ids

        except Exception as e:
            logger.error(f"Error getting unresolved market IDs: {e}")
            return []

    def get_markets_needing_resolution(self, limit: int = 50) -> List[str]:
        """
        Get market IDs that need resolution checking.

        Prioritizes:
        1. Markets with pending trades (trade_result is NULL or PENDING)
        2. Markets that haven't been checked recently

        Returns:
            List of market IDs to check
        """
        try:
            with get_db_session() as session:
                # Find markets with pending trades
                pending_markets = session.query(Trade.market_id).filter(
                    Trade.trade_result.is_(None) | (Trade.trade_result == 'PENDING')
                ).distinct().limit(limit).all()

                market_ids = [m[0] for m in pending_markets if m[0]]
                logger.debug(f"Found {len(market_ids)} markets with pending trades")
                return market_ids

        except Exception as e:
            logger.error(f"Error getting markets needing resolution: {e}")
            return []

    def process_new_resolutions(self) -> int:
        """
        Main method: find and process new market resolutions.

        Returns:
            Number of new resolutions processed
        """
        logger.info("Checking for new market resolutions...")

        resolutions_processed = 0

        try:
            # Step 1: Get closed markets from API
            closed_markets = self.poll_closed_markets(limit=100)

            if not closed_markets:
                logger.info("No closed markets found")
                return 0

            # Step 2: Try to infer resolution for each
            for market in closed_markets:
                market_id = market.get('id') or market.get('conditionId')
                if not market_id:
                    continue

                # Check if we already have this resolution
                with get_db_session() as session:
                    existing = session.query(MarketResolution).filter(
                        MarketResolution.market_id == market_id
                    ).first()

                    if existing:
                        continue

                # Try to infer resolution
                resolution_data = self.infer_resolution(market)

                if resolution_data:
                    stored = self.store_resolution(resolution_data)
                    if stored:
                        resolutions_processed += 1

            logger.info(f"Processed {resolutions_processed} new resolutions")
            return resolutions_processed

        except Exception as e:
            logger.error(f"Error processing resolutions: {e}")
            return resolutions_processed

    def check_specific_markets(self, market_ids: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Check resolution status for specific markets.

        Args:
            market_ids: List of market IDs to check

        Returns:
            Dict mapping market_id -> resolution data (or None if not resolved)
        """
        results = {}

        for market_id in market_ids:
            try:
                # Try to get market data from API
                market_data = self.api_client.get_market(market_id)

                if market_data and market_data.get('closed'):
                    resolution = self.infer_resolution(market_data)
                    if resolution:
                        stored = self.store_resolution(resolution)
                        results[market_id] = resolution
                    else:
                        results[market_id] = None
                else:
                    results[market_id] = None

            except Exception as e:
                logger.error(f"Error checking market {market_id}: {e}")
                results[market_id] = None

        return results

    def run_once(self) -> int:
        """
        Run a single resolution check cycle.

        Returns:
            Number of resolutions processed
        """
        return self.process_new_resolutions()

    def start(self):
        """
        Start continuous resolution monitoring loop.

        Runs until stop() is called.
        """
        self._running = True
        logger.info(f"Starting resolution monitor (interval: {self.poll_interval}s)")

        while self._running:
            try:
                processed = self.process_new_resolutions()
                logger.info(f"Resolution cycle complete: {processed} new resolutions")

            except Exception as e:
                logger.error(f"Error in resolution monitor loop: {e}")

            # Wait for next poll
            if self._running:
                time.sleep(self.poll_interval)

        logger.info("Resolution monitor stopped")

    def stop(self):
        """Stop the monitoring loop."""
        self._running = False
        logger.info("Resolution monitor stopping...")


def get_resolution_monitor() -> ResolutionMonitor:
    """
    Get singleton ResolutionMonitor instance.

    Returns:
        ResolutionMonitor instance
    """
    global _resolution_monitor

    if '_resolution_monitor' not in globals():
        _resolution_monitor = ResolutionMonitor()

    return _resolution_monitor
