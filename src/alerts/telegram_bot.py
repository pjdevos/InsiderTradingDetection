"""
Telegram bot for sending alerts about suspicious trades
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from telegram.error import TelegramError

from config import config
from alerts.templates import (
    telegram_alert_message,
    telegram_welcome_message,
    telegram_status_message,
    telegram_help_message,
    telegram_summary_message
)
from database.storage import DataStorageService

logger = logging.getLogger(__name__)


class TelegramAlertBot:
    """
    Telegram bot for sending trade alerts
    """

    def __init__(
        self,
        bot_token: str = None,
        chat_id: str = None
    ):
        """
        Initialize Telegram bot

        Args:
            bot_token: Telegram bot token
            chat_id: Default chat ID for alerts
        """
        self.bot_token = bot_token or config.TELEGRAM_BOT_TOKEN
        self.chat_id = chat_id or config.TELEGRAM_CHAT_ID

        if not self.bot_token or 'your' in self.bot_token.lower():
            logger.warning("No valid Telegram bot token configured")
            self.bot = None
            self.application = None
            return

        try:
            # Create bot instance
            self.bot = Bot(token=self.bot_token)

            # Create application for handling commands
            self.application = Application.builder().token(self.bot_token).build()

            # Register command handlers
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))

            logger.info("Telegram bot initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.bot = None
            self.application = None

    def is_configured(self) -> bool:
        """Check if bot is properly configured"""
        return self.bot is not None

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            message = telegram_welcome_message()
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent welcome message to chat {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"Error handling /start command: {e}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        try:
            message = telegram_help_message()
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info(f"Sent help message to chat {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"Error handling /help command: {e}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Get monitoring status (simplified - would check actual monitor state)
            is_monitoring = True
            last_check = datetime.now(timezone.utc)

            message = telegram_status_message(is_monitoring, last_check)
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent status message to chat {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"Error handling /status command: {e}")

    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        try:
            # Get recent statistics
            stats = DataStorageService.get_recent_trade_stats(hours=24)

            message = telegram_summary_message(stats)
            await update.message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"Sent statistics to chat {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"Error handling /stats command: {e}")
            await update.message.reply_text(
                "❌ Error fetching statistics. Please try again later."
            )

    async def send_alert(
        self,
        trade_data: Dict,
        scoring_result: Dict,
        chat_id: str = None
    ) -> bool:
        """
        Send alert message for suspicious trade

        Args:
            trade_data: Trade information
            scoring_result: Scoring algorithm results
            chat_id: Optional chat ID (uses default if not provided)

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            logger.warning("Telegram bot not configured, cannot send alert")
            return False

        target_chat_id = chat_id or self.chat_id

        if not target_chat_id or 'your' in target_chat_id.lower():
            logger.warning("No valid chat ID configured")
            return False

        try:
            # Generate alert message
            message = telegram_alert_message(trade_data, scoring_result)

            # Send message
            await self.bot.send_message(
                chat_id=target_chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )

            logger.info(
                f"Sent {scoring_result.get('alert_level', 'UNKNOWN')} alert to chat {target_chat_id}"
            )
            return True

        except TelegramError as e:
            logger.error(f"Telegram error sending alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False

    def send_alert_sync(
        self,
        trade_data: Dict,
        scoring_result: Dict,
        chat_id: str = None
    ) -> bool:
        """
        Synchronous wrapper for send_alert

        Args:
            trade_data: Trade information
            scoring_result: Scoring algorithm results
            chat_id: Optional chat ID

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            return False

        try:
            import asyncio

            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run async function
            return loop.run_until_complete(
                self.send_alert(trade_data, scoring_result, chat_id)
            )

        except Exception as e:
            logger.error(f"Error in send_alert_sync: {e}")
            return False

    async def send_summary(
        self,
        stats: Dict,
        chat_id: str = None
    ) -> bool:
        """
        Send summary message

        Args:
            stats: Statistics dictionary
            chat_id: Optional chat ID

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            return False

        target_chat_id = chat_id or self.chat_id

        try:
            message = telegram_summary_message(stats)

            await self.bot.send_message(
                chat_id=target_chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )

            logger.info(f"Sent summary to chat {target_chat_id}")
            return True

        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            return False

    def run_bot(self):
        """
        Run bot in polling mode (for testing/interactive use)
        """
        if not self.is_configured():
            logger.error("Cannot run bot - not configured")
            return

        logger.info("Starting Telegram bot in polling mode...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)


# Rate limiting for alerts
class AlertRateLimiter:
    """
    Rate limiter to prevent alert spam
    """

    def __init__(
        self,
        max_alerts_per_hour: int = 10,
        min_seconds_between: int = 60
    ):
        """
        Initialize rate limiter

        Args:
            max_alerts_per_hour: Maximum alerts per hour
            min_seconds_between: Minimum seconds between alerts
        """
        self.max_alerts_per_hour = max_alerts_per_hour
        self.min_seconds_between = min_seconds_between
        self.alert_history = []
        self.last_alert_time = None

    def should_send_alert(self, alert_level: str) -> bool:
        """
        Check if alert should be sent based on rate limits

        Args:
            alert_level: Alert level (WATCH, SUSPICIOUS, CRITICAL)

        Returns:
            True if alert should be sent
        """
        now = datetime.now(timezone.utc)

        # CRITICAL alerts always go through
        if alert_level == 'CRITICAL':
            return True

        # Check minimum time between alerts
        if self.last_alert_time:
            seconds_since_last = (now - self.last_alert_time).total_seconds()
            if seconds_since_last < self.min_seconds_between:
                logger.info(f"Rate limit: Only {seconds_since_last}s since last alert")
                return False

        # Check hourly limit
        one_hour_ago = now - timedelta(hours=1)
        recent_alerts = [t for t in self.alert_history if t > one_hour_ago]

        if len(recent_alerts) >= self.max_alerts_per_hour:
            logger.warning(f"Rate limit: {len(recent_alerts)} alerts in last hour")
            return False

        return True

    def record_alert(self):
        """Record that an alert was sent"""
        now = datetime.now(timezone.utc)
        self.alert_history.append(now)
        self.last_alert_time = now

        # Clean up old history (keep last 24 hours)
        cutoff = now - timedelta(hours=24)
        self.alert_history = [t for t in self.alert_history if t > cutoff]


# Singleton instances
_telegram_bot = None
_rate_limiter = None


def get_telegram_bot() -> TelegramAlertBot:
    """
    Get singleton Telegram bot instance

    Returns:
        TelegramAlertBot instance
    """
    global _telegram_bot

    if _telegram_bot is None:
        _telegram_bot = TelegramAlertBot()

    return _telegram_bot


def get_rate_limiter() -> AlertRateLimiter:
    """
    Get singleton rate limiter instance

    Returns:
        AlertRateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = AlertRateLimiter()

    return _rate_limiter


def send_trade_alert(
    trade_data: Dict,
    scoring_result: Dict,
    respect_rate_limit: bool = True
) -> bool:
    """
    Convenience function to send trade alert

    Args:
        trade_data: Trade information
        scoring_result: Scoring algorithm results
        respect_rate_limit: Whether to respect rate limits

    Returns:
        True if sent successfully
    """
    alert_level = scoring_result.get('alert_level')

    if not alert_level:
        return False

    # Get rate limiter
    rate_limiter = get_rate_limiter()

    # Check rate limit
    if respect_rate_limit:
        if not rate_limiter.should_send_alert(alert_level):
            logger.info(f"Alert suppressed due to rate limit: {alert_level}")
            return False

    # Send alert
    bot = get_telegram_bot()
    success = bot.send_alert_sync(trade_data, scoring_result)

    # Record alert if sent successfully and respecting rate limits
    if success and respect_rate_limit:
        rate_limiter.record_alert()

    return success
