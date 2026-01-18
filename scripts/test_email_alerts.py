"""
Test script for Email alert system

Tests email configuration and delivery.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from datetime import datetime, timezone
from alerts import get_email_service, send_email_alert


def test_email_configuration():
    """Test email service configuration"""
    print("\n" + "="*70)
    print("EMAIL ALERT CONFIGURATION TEST")
    print("="*70)

    print("\n1. Testing email configuration...")

    service = get_email_service()

    if not service.is_configured():
        print("\n[WARN] Email service not configured")
        print("   Set the following in .env to enable email alerts:")
        print("\n   Required settings:")
        print("   - SMTP_SERVER=smtp.gmail.com (or your SMTP server)")
        print("   - SMTP_PORT=587 (587 for TLS, 465 for SSL)")
        print("   - SMTP_USERNAME=your_email@gmail.com")
        print("   - SMTP_PASSWORD=your_app_password")
        print("   - EMAIL_FROM=your_email@gmail.com")
        print("   - EMAIL_TO=recipient@example.com")
        print("\n   For Gmail:")
        print("   1. Enable 2-factor authentication")
        print("   2. Generate an App Password at https://myaccount.google.com/apppasswords")
        print("   3. Use the App Password (not your regular password)")
        print("\n   For multiple recipients:")
        print("   - EMAIL_TO=email1@example.com,email2@example.com")
        return False

    print("\n[OK] Email service configured")
    print(f"   SMTP Server: {service.smtp_server}:{service.smtp_port}")
    print(f"   From: {service.from_email}")
    print(f"   To: {service.to_email}")
    print(f"   Recipients: {len(service.get_recipients())}")

    return True


def test_email_formatting():
    """Test email message formatting"""
    print("\n2. Testing email formatting...")

    # Create mock trade data
    mock_trade = {
        'transaction_hash': '0x' + 'a' * 64,
        'wallet_address': '0x' + 'b' * 40,
        'bet_size_usd': 150000,
        'bet_direction': 'YES',
        'bet_price': 0.85,
        'timestamp': datetime.now(timezone.utc),
        'market_title': 'Will there be a military conflict with Iran in January 2026?',
        'market': {
            'question': 'Will there be a military conflict with Iran in January 2026?',
            'category': 'Politics'
        }
    }

    # Create mock scoring result
    mock_scoring = {
        'total_score': 87,
        'raw_score': 144,
        'alert_level': 'CRITICAL',
        'breakdown': {
            'bet_size': {
                'score': 25,
                'max': 30,
                'reason': 'Very large bet ($150,000)'
            },
            'wallet_history': {
                'score': 30,
                'max': 40,
                'reason': 'New wallet (0 days); Mixer funded'
            },
            'market_category': {
                'score': 15,
                'max': 15,
                'reason': 'Geopolitical market (Politics)'
            },
            'timing': {
                'score': 15,
                'max': 15,
                'reason': 'Weekend trade (Saturday); Off-hours trade (03:00)'
            },
            'price_conviction': {
                'score': 12,
                'max': 15,
                'reason': 'Strong conviction YES at 0.85'
            },
            'pizzint': {
                'score': 0,
                'max': 30,
                'reason': 'PizzINT correlation not yet implemented'
            },
            'market_metadata': {
                'score': 18,
                'max': 20,
                'reason': 'New market; Low liquidity'
            }
        }
    }

    from alerts.templates import email_alert_html

    html_content = email_alert_html(mock_trade, mock_scoring)

    print("\n[OK] Email formatted successfully")
    print(f"   HTML Length: {len(html_content)} characters")
    print(f"   Alert Level: {mock_scoring['alert_level']}")
    print(f"   Score: {mock_scoring['total_score']}/100")

    return html_content


def test_email_delivery():
    """Test sending actual email"""
    print("\n3. Testing email delivery...")

    service = get_email_service()

    if not service.is_configured():
        print("\n[SKIP] Email not configured, skipping delivery test")
        return False

    print("\n   Attempting to send test email...")
    print("   (Check your inbox/spam folder)")

    try:
        success = service.send_test_email()

        if success:
            print("\n[OK] Test email sent successfully!")
            print("   Check your email inbox (or spam folder)")
            print(f"   Recipient(s): {service.to_email}")
            return True
        else:
            print("\n[FAIL] Failed to send test email")
            print("   Common issues:")
            print("   - Wrong password (use App Password for Gmail)")
            print("   - 2FA not enabled (required for Gmail)")
            print("   - SMTP server/port incorrect")
            print("   - Firewall blocking SMTP port")
            return False

    except Exception as e:
        print(f"\n[ERROR] Exception while sending email: {e}")
        print("\n   Troubleshooting:")
        print("   - Verify SMTP credentials are correct")
        print("   - For Gmail, use App Password (not regular password)")
        print("   - Check SMTP server and port settings")
        print("   - Ensure network connection is working")
        import traceback
        traceback.print_exc()
        return False


def test_alert_email():
    """Test sending alert-style email"""
    print("\n4. Testing alert email delivery...")

    service = get_email_service()

    if not service.is_configured():
        print("\n[SKIP] Email not configured, skipping alert test")
        return False

    # Create test trade data
    test_trade = {
        'transaction_hash': '0x' + 'test' * 16,
        'wallet_address': '0x' + 'test' * 10,
        'bet_size_usd': 125000,
        'bet_direction': 'YES',
        'bet_price': 0.88,
        'timestamp': datetime.now(timezone.utc),
        'market_title': 'TEST: This is a test alert from the Geopolitical Insider Trading Detection System',
        'market': {
            'question': 'TEST: This is a test alert',
            'category': 'Test'
        }
    }

    test_scoring = {
        'total_score': 85,
        'alert_level': 'CRITICAL',
        'breakdown': {
            'bet_size': {
                'score': 25,
                'max': 30,
                'reason': 'Very large bet ($125,000)'
            },
            'wallet_history': {
                'score': 25,
                'max': 40,
                'reason': 'Test wallet'
            },
            'market_category': {
                'score': 15,
                'max': 15,
                'reason': 'Test market'
            },
            'timing': {
                'score': 10,
                'max': 15,
                'reason': 'Test timing'
            },
            'price_conviction': {
                'score': 10,
                'max': 15,
                'reason': 'Test conviction'
            },
            'pizzint': {
                'score': 0,
                'max': 30,
                'reason': 'Not implemented'
            },
            'market_metadata': {
                'score': 0,
                'max': 20,
                'reason': 'Normal market'
            }
        }
    }

    print("\n   Attempting to send test alert email...")
    print("   (Check your inbox/spam folder)")

    try:
        success = service.send_alert(test_trade, test_scoring)

        if success:
            print("\n[OK] Test alert email sent successfully!")
            print("   Check your email inbox for the formatted alert")
            return True
        else:
            print("\n[FAIL] Failed to send test alert email")
            return False

    except Exception as e:
        print(f"\n[ERROR] Exception while sending alert: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("EMAIL ALERT TEST SUITE")
    print("="*70)

    # Test 1: Configuration
    configured = test_email_configuration()

    # Test 2: Formatting (always run)
    test_email_formatting()

    # Test 3 & 4: Delivery (only if configured)
    if configured:
        print("\n" + "="*70)
        user_input = input("\nDo you want to send a test email? (yes/no): ").strip().lower()

        if user_input in ['yes', 'y']:
            # Send basic test email
            test_email_delivery()

            # Ask about alert email
            print("\n" + "="*70)
            user_input = input("\nDo you want to send a test alert email? (yes/no): ").strip().lower()

            if user_input in ['yes', 'y']:
                test_alert_email()
            else:
                print("\n[SKIP] Alert email test skipped by user")
        else:
            print("\n[SKIP] Email delivery tests skipped by user")

    print("\n" + "="*70)
    print("TEST SUITE COMPLETE")
    print("="*70)

    if not configured:
        print("\nTo enable email alerts:")
        print("1. Set SMTP credentials in .env")
        print("2. For Gmail, enable 2FA and create App Password")
        print("3. Run this test again to verify configuration")
    else:
        print("\n[SUCCESS] Email alert system is configured and ready!")
        print("\nThe system will automatically send emails when:")
        print("  - Suspicion score >= 70 (SUSPICIOUS)")
        print("  - Suspicion score >= 85 (CRITICAL)")
        print("\nTelegram alerts are sent for all levels >= 50 (WATCH)")


if __name__ == '__main__':
    main()
