"""
Alert and notification system module
"""
from alerts.telegram_bot import (
    TelegramAlertBot,
    AlertRateLimiter,
    get_telegram_bot,
    get_rate_limiter,
    send_trade_alert
)
from alerts.email_alerts import (
    EmailAlertService,
    get_email_service,
    send_email_alert
)
from alerts.templates import (
    telegram_alert_message,
    telegram_welcome_message,
    telegram_status_message,
    telegram_help_message,
    email_alert_html
)

__all__ = [
    'TelegramAlertBot',
    'AlertRateLimiter',
    'get_telegram_bot',
    'get_rate_limiter',
    'send_trade_alert',
    'EmailAlertService',
    'get_email_service',
    'send_email_alert',
    'telegram_alert_message',
    'telegram_welcome_message',
    'telegram_status_message',
    'telegram_help_message',
    'email_alert_html'
]
