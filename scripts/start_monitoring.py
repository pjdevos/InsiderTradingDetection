"""
Production Monitoring Script for Geopolitical Insider Trading Detection

This script runs the full monitoring pipeline:
1. Connects to Polymarket API
2. Monitors geopolitical markets for large trades
3. Scores each trade using the 6-factor suspicion algorithm
4. Stores trades and scores in database
5. Sends Telegram alerts for suspicious trades (WATCH/SUSPICIOUS/CRITICAL)
6. Builds historical data for pattern detection

Press Ctrl+C to stop monitoring.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import logging
from datetime import datetime, timezone
from typing import Dict
from api.client import PolymarketAPIClient
from api.monitor import RealTimeTradeMonitor
from analysis.scoring import SuspicionScorer
from database.connection import init_db
from database.storage import DataStorageService
from alerts.telegram_bot import send_trade_alert
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InsiderTradingMonitor:
    """
    Full production monitoring system for insider trading detection
    """

    def __init__(self):
        """Initialize the monitoring system"""
        logger.info("Initializing Insider Trading Detection System...")

        # Initialize database
        init_db()
        logger.info("✓ Database initialized")

        # Initialize API client
        self.api_client = PolymarketAPIClient()
        logger.info("✓ Polymarket API client ready")

        # Initialize trade monitor
        self.monitor = RealTimeTradeMonitor(
            api_client=self.api_client,
            min_bet_size=config.MIN_BET_SIZE_USD,
            interval_seconds=config.POLL_INTERVAL_SECONDS
        )
        logger.info("✓ Trade monitor ready")

        # Statistics
        self.stats = {
            'trades_processed': 0,
            'trades_scored': 0,
            'alerts_sent': 0,
            'watch_alerts': 0,
            'suspicious_alerts': 0,
            'critical_alerts': 0,
            'errors': 0
        }

        logger.info("✓ System ready!")

    def process_trade(self, trade_data: Dict):
        """
        Process a detected trade through the full pipeline.

        NOTE: The RealTimeTradeMonitor already stores trades in the database.
        This callback is for additional processing (scoring display, alerts).

        Args:
            trade_data: Trade information dict (already stored by monitor)
        """
        # Generate correlation ID from transaction hash for log tracing
        tx_hash = (
            trade_data.get('transaction_hash') or
            trade_data.get('transactionHash') or
            trade_data.get('tx_hash') or
            'unknown'
        )
        tx_short = tx_hash[:10] if tx_hash != 'unknown' else 'unknown'

        try:
            self.stats['trades_processed'] += 1

            # Extract trade info (monitor.py normalizes these fields)
            wallet = trade_data.get('wallet_address') or trade_data.get('maker') or 'unknown'
            bet_size = trade_data.get('bet_size_usd', 0)
            market = trade_data.get('market', {})
            market_title = trade_data.get('market_title') or market.get('question', 'Unknown market')
            bet_direction = trade_data.get('bet_direction') or trade_data.get('outcome') or 'Unknown'
            bet_price = trade_data.get('bet_price') or trade_data.get('price') or 0

            logger.info(f"\n{'='*70}")
            logger.info(f"[{tx_short}] TRADE #{self.stats['trades_processed']}")
            logger.info(f"{'='*70}")
            logger.info(f"[{tx_short}] Market:    {market_title[:60]}")
            logger.info(f"[{tx_short}] Wallet:    {wallet[:10]}...{wallet[-6:] if len(wallet) > 6 else ''}")
            logger.info(f"[{tx_short}] Bet Size:  ${bet_size:,.2f}")
            logger.info(f"[{tx_short}] Direction: {bet_direction}")
            logger.info(f"[{tx_short}] Price:     {float(bet_price):.2f}")

            # Calculate suspicion score (blockchain verification disabled for speed)
            scoring_result = SuspicionScorer.calculate_score(
                trade_data=trade_data,
                market_data=market,
                use_blockchain=False  # Can enable for enhanced verification (slower)
            )

            self.stats['trades_scored'] += 1

            score = scoring_result['total_score']
            alert_level = scoring_result['alert_level']

            logger.info(f"[{tx_short}] --- SUSPICION SCORE ---")
            logger.info(f"[{tx_short}] Total Score: {score}/100")
            logger.info(f"[{tx_short}] Alert Level: {alert_level or 'NONE'}")
            logger.info(f"[{tx_short}] Breakdown:")
            for factor, data in scoring_result['breakdown'].items():
                logger.info(f"[{tx_short}]   {factor:20s}: {data['score']:2.0f}/{data['max']:2.0f} - {data['reason']}")

            # NOTE: Trade is already stored by RealTimeTradeMonitor.process_trade()
            # We just log the status here based on what the monitor reported
            logger.info(f"[{tx_short}] ✓ Trade processed (stored by monitor)")

            # Send alert if suspicious
            if alert_level:
                logger.info(f"\n🚨 ALERT: {alert_level} level trade detected!")

                try:
                    success = send_trade_alert(trade_data, scoring_result)

                    if success:
                        self.stats['alerts_sent'] += 1

                        if alert_level == 'WATCH':
                            self.stats['watch_alerts'] += 1
                        elif alert_level == 'SUSPICIOUS':
                            self.stats['suspicious_alerts'] += 1
                        elif alert_level == 'CRITICAL':
                            self.stats['critical_alerts'] += 1

                        logger.info(f"✓ Telegram alert sent")
                    else:
                        logger.warning(f"✗ Telegram alert not sent (rate limited or failed)")

                except Exception as e:
                    logger.error(f"✗ Alert failed: {e}")
                    self.stats['errors'] += 1
            else:
                logger.info(f"\n✓ Normal trade (score below threshold)")

            logger.info(f"{'='*70}\n")

        except Exception as e:
            logger.error(f"Error processing trade: {e}", exc_info=True)
            self.stats['errors'] += 1

    def print_stats(self):
        """Print current monitoring statistics"""
        logger.info(f"\n{'='*70}")
        logger.info(f"MONITORING STATISTICS")
        logger.info(f"{'='*70}")
        logger.info(f"Trades Processed:    {self.stats['trades_processed']}")
        logger.info(f"Trades Scored:       {self.stats['trades_scored']}")
        logger.info(f"Alerts Sent:         {self.stats['alerts_sent']}")
        logger.info(f"  - WATCH:           {self.stats['watch_alerts']}")
        logger.info(f"  - SUSPICIOUS:      {self.stats['suspicious_alerts']}")
        logger.info(f"  - CRITICAL:        {self.stats['critical_alerts']}")
        logger.info(f"Errors:              {self.stats['errors']}")
        logger.info(f"{'='*70}\n")

    def start(self):
        """Start the monitoring system"""
        logger.info(f"\n{'='*70}")
        logger.info(f"GEOPOLITICAL INSIDER TRADING DETECTION SYSTEM")
        logger.info(f"{'='*70}")
        logger.info(f"")
        logger.info(f"Configuration:")
        logger.info(f"  Min Bet Size:         ${config.MIN_BET_SIZE_USD:,.0f}")
        logger.info(f"  Poll Interval:        {config.POLL_INTERVAL_SECONDS}s")
        logger.info(f"  Geopolitical Only:    Yes")
        logger.info(f"  Blockchain Verify:    Disabled (for speed)")
        logger.info(f"")
        logger.info(f"Alert Thresholds:")
        logger.info(f"  WATCH:                {config.SUSPICION_THRESHOLD_WATCH}+")
        logger.info(f"  SUSPICIOUS:           {config.SUSPICION_THRESHOLD_SUSPICIOUS}+")
        logger.info(f"  CRITICAL:             {config.SUSPICION_THRESHOLD_CRITICAL}+")
        logger.info(f"")
        logger.info(f"Telegram alerts configured for your chat ID")
        logger.info(f"")
        logger.info(f"Press Ctrl+C to stop monitoring")
        logger.info(f"{'='*70}\n")

        # Register callback
        self.monitor.register_callback(self.process_trade)

        # Get recent trades as initial sample
        logger.info("Fetching recent large trades (last 24 hours)...")
        try:
            recent = self.monitor.get_recent_large_trades(hours=24, geopolitical_only=True)
            if recent:
                logger.info(f"Found {len(recent)} large geopolitical trades in last 24 hours")
                logger.info("Processing them to build initial database...")

                for i, trade in enumerate(recent[:10], 1):  # Process up to 10 recent trades
                    logger.info(f"\nProcessing recent trade {i}/{min(len(recent), 10)}...")
                    self.process_trade(trade)

                self.print_stats()
            else:
                logger.info("No large geopolitical trades found in last 24 hours")
        except Exception as e:
            logger.error(f"Error fetching recent trades: {e}")

        logger.info("\n" + "="*70)
        logger.info("STARTING LIVE MONITORING")
        logger.info("="*70 + "\n")

        # Start live monitoring
        try:
            self.monitor.start()
        except KeyboardInterrupt:
            logger.info("\n\nMonitoring stopped by user")
            self.monitor.stop()
            self.print_stats()
            logger.info("\nShutdown complete. Database preserved.")


def main():
    """Main entry point"""
    try:
        monitor = InsiderTradingMonitor()
        monitor.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
