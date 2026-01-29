"""
Resolution Monitor - Tracks market outcomes for win/loss calculation

This script runs the resolution monitor which:
1. Polls Polymarket API for resolved (closed) markets
2. Infers winning outcomes from final prices
3. Stores resolutions in the database
4. Enables the Suspicious Winners feature

Press Ctrl+C to stop monitoring.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import logging
from database.connection import init_db
from api.resolution_monitor import ResolutionMonitor
from analysis.win_calculator import WinLossCalculator
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResolutionService:
    """
    Combined resolution and win/loss calculation service.
    """

    def __init__(self, poll_interval_minutes: int = 30):
        """Initialize the resolution service."""
        logger.info("Initializing Resolution Monitor Service...")

        # Initialize database
        init_db()
        logger.info("Database initialized")

        # Initialize resolution monitor
        self.resolution_monitor = ResolutionMonitor(
            poll_interval_minutes=poll_interval_minutes
        )
        logger.info("Resolution monitor ready")

        # Initialize win/loss calculator
        self.win_calculator = WinLossCalculator()
        logger.info("Win/loss calculator ready")

        self.stats = {
            'resolutions_found': 0,
            'wins_calculated': 0,
            'cycles': 0,
        }

    def run_cycle(self):
        """Run one cycle: check resolutions, then calculate wins."""
        self.stats['cycles'] += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"RESOLUTION CYCLE #{self.stats['cycles']}")
        logger.info(f"{'='*60}")

        # Step 1: Check for new resolutions
        try:
            new_resolutions = self.resolution_monitor.process_new_resolutions()
            self.stats['resolutions_found'] += new_resolutions
            logger.info(f"Found {new_resolutions} new market resolutions")
        except Exception as e:
            logger.error(f"Error checking resolutions: {e}")

        # Step 2: Calculate win/loss for pending trades
        try:
            result = self.win_calculator.process_all_pending_resolutions()
            trades_processed = result.get('trades_processed', 0)
            self.stats['wins_calculated'] += trades_processed
            logger.info(f"Calculated outcomes for {trades_processed} trades")
            if result.get('wallets_updated'):
                logger.info(f"Updated {result['wallets_updated']} wallet metrics")
        except Exception as e:
            logger.error(f"Error calculating wins: {e}")

        logger.info(f"\nStats: {self.stats['resolutions_found']} total resolutions, "
                    f"{self.stats['wins_calculated']} trade outcomes calculated")

    def start(self):
        """Start the resolution monitoring loop."""
        import time

        logger.info(f"\n{'='*60}")
        logger.info("RESOLUTION MONITOR SERVICE")
        logger.info(f"{'='*60}")
        logger.info(f"Poll interval: {self.resolution_monitor.poll_interval}s")
        logger.info(f"Resolution threshold: {self.resolution_monitor.resolution_threshold}")
        logger.info(f"\nPress Ctrl+C to stop")
        logger.info(f"{'='*60}\n")

        try:
            while True:
                self.run_cycle()
                logger.info(f"\nSleeping for {self.resolution_monitor.poll_interval}s...")
                time.sleep(self.resolution_monitor.poll_interval)

        except KeyboardInterrupt:
            logger.info("\n\nResolution monitor stopped by user")
            logger.info(f"Final stats: {self.stats}")


def main():
    """Main entry point."""
    try:
        # Poll every 30 minutes by default
        poll_interval = getattr(config, 'RESOLUTION_POLL_INTERVAL_MINUTES', 30)
        service = ResolutionService(poll_interval_minutes=poll_interval)
        service.start()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
