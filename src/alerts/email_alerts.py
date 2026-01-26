"""
Email alert system for sending suspicious trade notifications
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
from datetime import datetime, timezone

from config import config
from alerts.credential_validator import CredentialValidator, CredentialValidationError
from alerts.templates import email_alert_html

logger = logging.getLogger(__name__)


class EmailAlertService:
    """
    Email alert service for sending trade alerts via SMTP
    """

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        smtp_username: str = None,
        smtp_password: str = None,
        from_email: str = None,
        to_email: str = None
    ):
        """
        Initialize email alert service with strict credential validation.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port (587 for TLS)
            smtp_username: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            to_email: Recipient email address (or comma-separated list)

        Raises:
            CredentialValidationError: If ALERTS_REQUIRED=true and credentials are invalid
        """
        self.smtp_server = smtp_server or config.SMTP_SERVER
        self.smtp_port = smtp_port or config.SMTP_PORT
        self.smtp_username = smtp_username or config.SMTP_USERNAME
        self.smtp_password = smtp_password or config.SMTP_PASSWORD
        self.from_email = from_email or config.EMAIL_FROM
        self.to_email = to_email or config.EMAIL_TO

        # Validate credentials based on ALERTS_REQUIRED setting
        is_valid, errors = CredentialValidator.validate_email_credentials(
            smtp_server=self.smtp_server,
            smtp_port=self.smtp_port,
            smtp_username=self.smtp_username,
            smtp_password=self.smtp_password,
            from_email=self.from_email,
            to_email=self.to_email,
            required=config.ALERTS_REQUIRED
        )

        if not is_valid:
            if config.ALERTS_REQUIRED:
                # Fail fast when alerts are required
                error_msg = "Email/SMTP credentials validation failed:\n"
                for error in errors:
                    error_msg += f"  - {error}\n"
                raise CredentialValidationError(error_msg)
            else:
                # Allow running without email when alerts not required
                CredentialValidator.log_disabled_alert_warning("Email")

    def is_configured(self) -> bool:
        """
        Check if email service is properly configured

        Returns:
            True if all required settings are present and valid
        """
        # Use the credential validator for consistent validation
        is_valid, _ = CredentialValidator.validate_email_credentials(
            smtp_server=self.smtp_server,
            smtp_port=self.smtp_port,
            smtp_username=self.smtp_username,
            smtp_password=self.smtp_password,
            from_email=self.from_email,
            to_email=self.to_email,
            required=False  # Don't raise errors in this method, just return bool
        )

        return is_valid

    def get_recipients(self) -> List[str]:
        """
        Parse recipient email addresses

        Returns:
            List of email addresses
        """
        if not self.to_email:
            return []

        # Split by comma and strip whitespace
        return [email.strip() for email in self.to_email.split(',')]

    def send_alert(
        self,
        trade_data: Dict,
        scoring_result: Dict,
        recipients: List[str] = None
    ) -> bool:
        """
        Send email alert for suspicious trade

        Args:
            trade_data: Trade information
            scoring_result: Scoring algorithm results
            recipients: Optional list of recipient emails (overrides default)

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            logger.warning("Email service not configured, cannot send alert")
            return False

        target_recipients = recipients or self.get_recipients()

        if not target_recipients:
            logger.warning("No recipient email addresses configured")
            return False

        try:
            # Generate email content
            alert_level = scoring_result.get('alert_level', 'WATCH')
            score = scoring_result.get('total_score', 0)

            market_title = trade_data.get('market_title', '')
            if not market_title and 'market' in trade_data:
                market_title = trade_data['market'].get('question', 'Unknown Market')

            # Create email message
            message = MIMEMultipart('alternative')
            message['Subject'] = f"{alert_level} ALERT: Suspicious Trade ({score}/100) - {market_title[:60]}"
            message['From'] = self.from_email
            message['To'] = ', '.join(target_recipients)
            message['Date'] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Generate HTML body
            html_body = email_alert_html(trade_data, scoring_result)

            # Generate plain text fallback
            text_body = self._generate_text_fallback(trade_data, scoring_result)

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')

            message.attach(part1)
            message.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                # Enable TLS encryption
                server.starttls()

                # Login to SMTP server
                server.login(self.smtp_username, self.smtp_password)

                # Send email
                server.send_message(message)

            logger.info(
                f"Sent {alert_level} email alert to {len(target_recipients)} recipient(s)"
            )
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False

    def _generate_text_fallback(self, trade_data: Dict, scoring_result: Dict) -> str:
        """
        Generate plain text version of email for clients that don't support HTML

        Args:
            trade_data: Trade information
            scoring_result: Scoring algorithm results

        Returns:
            Plain text email body
        """
        alert_level = scoring_result.get('alert_level', 'WATCH')
        score = scoring_result.get('total_score', 0)
        breakdown = scoring_result.get('breakdown', {})

        # Extract trade details
        bet_size = trade_data.get('bet_size_usd', 0)
        wallet = trade_data.get('wallet_address', 'Unknown')
        market_title = trade_data.get('market_title', '')
        if not market_title and 'market' in trade_data:
            market_title = trade_data['market'].get('question', 'Unknown Market')

        bet_direction = trade_data.get('bet_direction', 'YES')
        bet_price = trade_data.get('bet_price', 0)
        timestamp = trade_data.get('timestamp', datetime.now(timezone.utc))

        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        # Build plain text message
        text = f"{alert_level} ALERT - Suspicious Trading Activity Detected\n"
        text += "=" * 70 + "\n\n"

        text += f"SUSPICION SCORE: {score}/100\n\n"

        text += "TRADE DETAILS:\n"
        text += f"  Bet Size: ${bet_size:,.2f}\n"
        text += f"  Direction: {bet_direction} @ {bet_price:.2f}\n"
        text += f"  Wallet: {wallet}\n"
        text += f"  Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

        text += "MARKET:\n"
        text += f"  {market_title}\n\n"

        text += "SUSPICION FACTORS:\n"
        for factor_name, factor_data in breakdown.items():
            if factor_data['score'] > 0:
                text += f"  - {factor_name.replace('_', ' ').title()}: "
                text += f"{factor_data['score']}/{factor_data['max']}\n"
                text += f"    {factor_data['reason']}\n"

        text += "\n" + "=" * 70 + "\n"
        text += "Geopolitical Insider Trading Detection System\n"
        text += "This is an automated alert. Do not reply to this email.\n"

        return text

    def send_test_email(self, to_email: str = None) -> bool:
        """
        Send test email to verify configuration

        Args:
            to_email: Optional recipient email (uses default if not provided)

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            logger.error("Email service not configured")
            return False

        recipient = to_email or self.to_email

        try:
            # Create simple test message
            message = MIMEMultipart('alternative')
            message['Subject'] = "TEST: Geopolitical Insider Trading Detection - Email Alert Test"
            message['From'] = self.from_email
            message['To'] = recipient
            message['Date'] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Plain text body
            text_body = """
TEST EMAIL - Geopolitical Insider Trading Detection System
============================================================

This is a test email to verify that the email alert system is configured correctly.

If you received this message, your email alerts are working properly!

Configuration:
- SMTP Server: {}
- SMTP Port: {}
- From: {}
- To: {}

System Status: Operational
Alert System: Active

This is an automated test message.
""".format(self.smtp_server, self.smtp_port, self.from_email, recipient)

            # HTML body
            html_body = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
        .detail {{ margin: 10px 0; padding: 10px; background-color: white; border-left: 3px solid #4CAF50; }}
        .footer {{ text-align: center; margin-top: 20px; padding: 10px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ TEST EMAIL</h1>
            <p>Geopolitical Insider Trading Detection System</p>
        </div>
        <div class="content">
            <p><strong>This is a test email to verify that the email alert system is configured correctly.</strong></p>
            <p>If you received this message, your email alerts are working properly!</p>

            <h2>Configuration</h2>
            <div class="detail">
                <strong>SMTP Server:</strong> {}<br>
                <strong>SMTP Port:</strong> {}<br>
                <strong>From:</strong> {}<br>
                <strong>To:</strong> {}
            </div>

            <div class="detail">
                <strong>System Status:</strong> Operational<br>
                <strong>Alert System:</strong> Active
            </div>
        </div>
        <div class="footer">
            <p>Geopolitical Insider Trading Detection System</p>
            <p>This is an automated test message.</p>
        </div>
    </div>
</body>
</html>
""".format(self.smtp_server, self.smtp_port, self.from_email, recipient)

            # Attach both versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')

            message.attach(part1)
            message.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)

            logger.info(f"Sent test email to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Error sending test email: {e}")
            return False

    def send_daily_summary(self, stats: Dict, to_email: str = None) -> bool:
        """
        Send daily summary email with statistics

        Args:
            stats: Statistics dictionary
            to_email: Optional recipient email

        Returns:
            True if sent successfully
        """
        if not self.is_configured():
            logger.warning("Email service not configured")
            return False

        recipient = to_email or self.to_email

        try:
            # Create summary message
            message = MIMEMultipart('alternative')
            message['Subject'] = f"Daily Summary: {stats.get('total_trades', 0)} Trades Monitored"
            message['From'] = self.from_email
            message['To'] = recipient
            message['Date'] = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')

            # Generate bodies
            text_body = self._generate_summary_text(stats)
            html_body = self._generate_summary_html(stats)

            # Attach both versions
            part1 = MIMEText(text_body, 'plain')
            part2 = MIMEText(html_body, 'html')

            message.attach(part1)
            message.attach(part2)

            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)

            logger.info(f"Sent daily summary email to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Error sending summary email: {e}")
            return False

    def _generate_summary_text(self, stats: Dict) -> str:
        """Generate plain text summary"""
        text = "Daily Trading Activity Summary\n"
        text += "=" * 70 + "\n\n"

        total_trades = stats.get('total_trades', 0)
        high_suspicion = stats.get('high_suspicion_count', 0)
        total_volume = stats.get('total_volume_usd', 0)

        text += f"Trades Monitored: {total_trades}\n"
        text += f"High Suspicion Trades: {high_suspicion}\n"
        text += f"Total Volume: ${total_volume:,.2f}\n\n"

        if 'top_wallets' in stats:
            text += "Most Active Wallets:\n"
            for wallet_data in stats['top_wallets'][:5]:
                wallet = wallet_data.get('wallet_address', '')
                count = wallet_data.get('trade_count', 0)
                text += f"  - {wallet[:10]}...{wallet[-6:]}: {count} trades\n"

        return text

    def _generate_summary_html(self, stats: Dict) -> str:
        """Generate HTML summary"""
        total_trades = stats.get('total_trades', 0)
        high_suspicion = stats.get('high_suspicion_count', 0)
        total_volume = stats.get('total_volume_usd', 0)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
        .stat {{ margin: 10px 0; padding: 15px; background-color: white; border-left: 3px solid #2196F3; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        .footer {{ text-align: center; margin-top: 20px; padding: 10px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Daily Summary</h1>
            <p>Geopolitical Insider Trading Detection System</p>
        </div>
        <div class="content">
            <div class="stat">
                <div>Trades Monitored</div>
                <div class="stat-value">{total_trades}</div>
            </div>
            <div class="stat">
                <div>High Suspicion Trades</div>
                <div class="stat-value">{high_suspicion}</div>
            </div>
            <div class="stat">
                <div>Total Volume</div>
                <div class="stat-value">${total_volume:,.2f}</div>
            </div>
        </div>
        <div class="footer">
            <p>Geopolitical Insider Trading Detection System</p>
        </div>
    </div>
</body>
</html>
"""
        return html


# Singleton instance
_email_service = None


def get_email_service() -> EmailAlertService:
    """
    Get singleton email service instance

    Returns:
        EmailAlertService instance
    """
    global _email_service

    if _email_service is None:
        _email_service = EmailAlertService()

    return _email_service


def send_email_alert(
    trade_data: Dict,
    scoring_result: Dict
) -> bool:
    """
    Convenience function to send email alert

    Args:
        trade_data: Trade information
        scoring_result: Scoring algorithm results

    Returns:
        True if sent successfully
    """
    alert_level = scoring_result.get('alert_level')

    if not alert_level:
        return False

    # Only send emails for SUSPICIOUS and CRITICAL alerts
    if alert_level not in ['SUSPICIOUS', 'CRITICAL']:
        logger.debug(f"Skipping email for {alert_level} level (only SUSPICIOUS/CRITICAL)")
        return False

    service = get_email_service()
    return service.send_alert(trade_data, scoring_result)
