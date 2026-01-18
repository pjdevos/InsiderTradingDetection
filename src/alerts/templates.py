"""
Alert message templates for Telegram and email notifications
"""
from datetime import datetime
from typing import Dict


def format_currency(amount: float) -> str:
    """Format currency with commas"""
    return f"${amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format percentage"""
    return f"{value:.1%}"


def get_alert_emoji(alert_level: str) -> str:
    """Get emoji for alert level"""
    emojis = {
        'WATCH': '👀',
        'SUSPICIOUS': '⚠️',
        'CRITICAL': '🚨'
    }
    return emojis.get(alert_level, '📊')


def telegram_alert_message(trade_data: Dict, scoring_result: Dict) -> str:
    """
    Create Telegram alert message for suspicious trade

    Args:
        trade_data: Trade information
        scoring_result: Scoring algorithm results

    Returns:
        Formatted message string
    """
    alert_level = scoring_result.get('alert_level', 'WATCH')
    score = scoring_result.get('total_score', 0)
    breakdown = scoring_result.get('breakdown', {})

    emoji = get_alert_emoji(alert_level)

    # Extract trade details
    bet_size = trade_data.get('bet_size_usd', 0)
    wallet = trade_data.get('wallet_address', 'Unknown')
    market_title = trade_data.get('market_title', '')
    if not market_title and 'market' in trade_data:
        market_title = trade_data['market'].get('question', 'Unknown Market')

    bet_direction = trade_data.get('bet_direction', 'YES')
    bet_price = trade_data.get('bet_price', 0)
    timestamp = trade_data.get('timestamp', datetime.now())

    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    # Build message
    message = f"{emoji} *{alert_level} ALERT* {emoji}\n\n"
    message += f"*Suspicion Score:* {score}/100\n\n"

    message += f"*Trade Details:*\n"
    message += f"• Bet Size: {format_currency(bet_size)}\n"
    message += f"• Direction: {bet_direction} @ {bet_price:.2f}\n"
    message += f"• Wallet: `{wallet[:10]}...{wallet[-6:]}`\n"
    message += f"• Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

    message += f"*Market:*\n"
    message += f"{market_title[:200]}\n\n"

    # Add top scoring factors
    message += f"*Key Factors:*\n"
    top_factors = sorted(
        [(name, data) for name, data in breakdown.items() if data['score'] > 0],
        key=lambda x: x[1]['score'],
        reverse=True
    )[:3]

    for factor_name, factor_data in top_factors:
        score_val = factor_data['score']
        max_val = factor_data['max']
        reason = factor_data['reason']
        message += f"• {factor_name.replace('_', ' ').title()}: {score_val}/{max_val}\n"
        message += f"  _{reason}_\n"

    message += f"\n🔗 [View on Polymarket](https://polymarket.com)\n"

    return message


def telegram_summary_message(stats: Dict) -> str:
    """
    Create daily/hourly summary message

    Args:
        stats: Statistics dictionary

    Returns:
        Formatted summary message
    """
    message = "📊 *Trading Activity Summary*\n\n"

    total_trades = stats.get('total_trades', 0)
    high_suspicion = stats.get('high_suspicion_count', 0)
    total_volume = stats.get('total_volume_usd', 0)

    message += f"*Trades Monitored:* {total_trades}\n"
    message += f"*High Suspicion:* {high_suspicion}\n"
    message += f"*Total Volume:* {format_currency(total_volume)}\n\n"

    if 'top_wallets' in stats:
        message += "*Most Active Wallets:*\n"
        for wallet_data in stats['top_wallets'][:3]:
            wallet = wallet_data.get('wallet_address', '')
            count = wallet_data.get('trade_count', 0)
            message += f"• `{wallet[:10]}...` - {count} trades\n"

    return message


def telegram_welcome_message() -> str:
    """Welcome message when bot starts"""
    message = "🤖 *Geopolitical Insider Trading Detection Bot*\n\n"
    message += "I'm monitoring Polymarket for suspicious trading patterns.\n\n"
    message += "*Alert Levels:*\n"
    message += "👀 WATCH (50-69) - Noteworthy activity\n"
    message += "⚠️ SUSPICIOUS (70-84) - High probability insider trading\n"
    message += "🚨 CRITICAL (85-100) - Extremely suspicious activity\n\n"
    message += "*Commands:*\n"
    message += "/start - Show this message\n"
    message += "/status - System status\n"
    message += "/stats - Recent statistics\n"
    message += "/help - Get help\n\n"
    message += "✅ Bot is active and monitoring...\n"

    return message


def telegram_status_message(is_monitoring: bool, last_check: datetime = None) -> str:
    """
    System status message

    Args:
        is_monitoring: Whether monitoring is active
        last_check: Last check timestamp

    Returns:
        Formatted status message
    """
    status_emoji = "✅" if is_monitoring else "❌"
    status_text = "Active" if is_monitoring else "Inactive"

    message = f"🤖 *System Status*\n\n"
    message += f"*Monitoring:* {status_emoji} {status_text}\n"

    if last_check:
        if isinstance(last_check, str):
            last_check = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
        message += f"*Last Check:* {last_check.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"

    message += f"\n*Configuration:*\n"
    message += f"• Poll Interval: 60 seconds\n"
    message += f"• Min Bet Size: $10,000\n"
    message += f"• Alert Threshold: 50+\n"

    return message


def telegram_help_message() -> str:
    """Help message with command info"""
    message = "ℹ️ *Help - Available Commands*\n\n"
    message += "*Basic Commands:*\n"
    message += "/start - Welcome message and bot info\n"
    message += "/status - Check if monitoring is active\n"
    message += "/stats - View recent trading statistics\n"
    message += "/help - Show this help message\n\n"
    message += "*Alert System:*\n"
    message += "The bot automatically sends alerts when suspicious trades are detected.\n\n"
    message += "*Suspicion Factors:*\n"
    message += "• Bet size (larger = more suspicious)\n"
    message += "• Wallet history (new wallets = suspicious)\n"
    message += "• Market category (geopolitical focus)\n"
    message += "• Timing (off-hours, weekends)\n"
    message += "• Price/conviction (contrarian bets)\n"
    message += "• Market metadata (new, low liquidity)\n\n"
    message += "🔗 [GitHub](https://github.com) | [Documentation](https://docs.example.com)\n"

    return message


def email_alert_html(trade_data: Dict, scoring_result: Dict) -> str:
    """
    Create HTML email alert

    Args:
        trade_data: Trade information
        scoring_result: Scoring algorithm results

    Returns:
        HTML email content
    """
    alert_level = scoring_result.get('alert_level', 'WATCH')
    score = scoring_result.get('total_score', 0)
    breakdown = scoring_result.get('breakdown', {})

    # Alert level colors
    colors = {
        'WATCH': '#FFA500',
        'SUSPICIOUS': '#FF6B6B',
        'CRITICAL': '#DC143C'
    }
    alert_color = colors.get(alert_level, '#666666')

    bet_size = trade_data.get('bet_size_usd', 0)
    wallet = trade_data.get('wallet_address', 'Unknown')
    market_title = trade_data.get('market_title', '')
    if not market_title and 'market' in trade_data:
        market_title = trade_data['market'].get('question', 'Unknown Market')

    bet_direction = trade_data.get('bet_direction', 'YES')
    bet_price = trade_data.get('bet_price', 0)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: {alert_color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
            .score {{ font-size: 36px; font-weight: bold; text-align: center; margin: 20px 0; color: {alert_color}; }}
            .detail {{ margin: 10px 0; padding: 10px; background-color: white; border-left: 3px solid {alert_color}; }}
            .detail-label {{ font-weight: bold; color: #666; }}
            .factors {{ margin-top: 20px; }}
            .factor {{ margin: 10px 0; padding: 10px; background-color: #fff; }}
            .footer {{ text-align: center; margin-top: 20px; padding: 10px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{alert_level} ALERT</h1>
                <p>Suspicious Trading Activity Detected</p>
            </div>
            <div class="content">
                <div class="score">Suspicion Score: {score}/100</div>

                <h2>Trade Details</h2>
                <div class="detail">
                    <span class="detail-label">Bet Size:</span> {format_currency(bet_size)}
                </div>
                <div class="detail">
                    <span class="detail-label">Direction:</span> {bet_direction} @ {bet_price:.2f}
                </div>
                <div class="detail">
                    <span class="detail-label">Wallet:</span> <code>{wallet}</code>
                </div>

                <h2>Market</h2>
                <div class="detail">
                    {market_title}
                </div>

                <div class="factors">
                    <h2>Suspicion Factors</h2>
    """

    # Add scoring factors
    for factor_name, factor_data in breakdown.items():
        if factor_data['score'] > 0:
            html += f"""
                    <div class="factor">
                        <strong>{factor_name.replace('_', ' ').title()}:</strong>
                        {factor_data['score']}/{factor_data['max']}<br>
                        <em>{factor_data['reason']}</em>
                    </div>
            """

    html += """
                </div>
            </div>
            <div class="footer">
                <p>Geopolitical Insider Trading Detection System</p>
                <p>This is an automated alert. Do not reply to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return html
