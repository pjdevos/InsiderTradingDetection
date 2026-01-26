"""
Test script to simulate system startup with various credential scenarios.

This demonstrates the fail-fast behavior when ALERTS_REQUIRED=true
and graceful degradation when ALERTS_REQUIRED=false.
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def test_scenario(scenario_name, env_vars, should_fail=True):
    """Test a specific credential scenario"""
    print(f"\n{'=' * 70}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'=' * 70}")

    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = str(value) if value is not None else ""

    # Reload config to pick up new env vars
    import importlib
    if 'config' in sys.modules:
        importlib.reload(sys.modules['config'])
    if 'alerts.credential_validator' in sys.modules:
        importlib.reload(sys.modules['alerts.credential_validator'])

    from config import config
    from alerts.credential_validator import CredentialValidationError

    try:
        print(f"\nALERTS_REQUIRED: {config.ALERTS_REQUIRED}")
        print("\nAttempting to validate alert credentials...")

        config.validate_alert_credentials()

        print("\n[SUCCESS] Validation passed!")
        if should_fail:
            print("\n[UNEXPECTED] This scenario should have failed!")
            return False
        else:
            print("\n[EXPECTED] This scenario passed as expected.")
            return True

    except CredentialValidationError as e:
        print(f"\n[FAILED] Validation failed with error:")
        print(f"\n{str(e)}")
        if should_fail:
            print("\n[EXPECTED] This scenario failed as expected.")
            return True
        else:
            print("\n[UNEXPECTED] This scenario should have passed!")
            return False

    finally:
        # Clean up environment
        for key in env_vars.keys():
            os.environ.pop(key, None)


def main():
    """Run all test scenarios"""
    print("=" * 70)
    print("  System Startup Credential Validation Tests")
    print("=" * 70)
    print("\nThis demonstrates fail-fast behavior vs graceful degradation")

    results = []

    # Scenario 1: ALERTS_REQUIRED=true with invalid credentials (should FAIL)
    results.append(test_scenario(
        "Production mode with placeholder credentials",
        {
            'ALERTS_REQUIRED': 'true',
            'TELEGRAM_BOT_TOKEN': 'YOUR_TOKEN_HERE',
            'TELEGRAM_CHAT_ID': 'YOUR_CHAT_ID',
            'EMAIL_FROM': 'your_email@example.com',
            'EMAIL_TO': 'recipient@example.com',
            'SMTP_USERNAME': 'your_username',
            'SMTP_PASSWORD': 'your_password',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        },
        should_fail=True
    ))

    # Scenario 2: ALERTS_REQUIRED=false with invalid credentials (should PASS with warnings)
    results.append(test_scenario(
        "Development mode with placeholder credentials",
        {
            'ALERTS_REQUIRED': 'false',
            'TELEGRAM_BOT_TOKEN': 'YOUR_TOKEN_HERE',
            'TELEGRAM_CHAT_ID': 'YOUR_CHAT_ID',
            'EMAIL_FROM': 'your_email@example.com',
            'EMAIL_TO': 'recipient@example.com',
            'SMTP_USERNAME': 'your_username',
            'SMTP_PASSWORD': 'your_password',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        },
        should_fail=False
    ))

    # Scenario 3: ALERTS_REQUIRED=true with valid Telegram only (should PASS)
    results.append(test_scenario(
        "Production mode with valid Telegram credentials only",
        {
            'ALERTS_REQUIRED': 'true',
            'TELEGRAM_BOT_TOKEN': '1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ',
            'TELEGRAM_CHAT_ID': '-1001234567890',
            'EMAIL_FROM': 'your_email@example.com',
            'EMAIL_TO': 'recipient@example.com',
            'SMTP_USERNAME': 'your_username',
            'SMTP_PASSWORD': 'your_password',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        },
        should_fail=False
    ))

    # Scenario 4: ALERTS_REQUIRED=true with valid Email only (should PASS)
    results.append(test_scenario(
        "Production mode with valid Email credentials only",
        {
            'ALERTS_REQUIRED': 'true',
            'TELEGRAM_BOT_TOKEN': 'YOUR_TOKEN_HERE',
            'TELEGRAM_CHAT_ID': 'YOUR_CHAT_ID',
            'EMAIL_FROM': 'sender@company.com',
            'EMAIL_TO': 'recipient@company.com',
            'SMTP_USERNAME': 'user@gmail.com',
            'SMTP_PASSWORD': 'realpassword123',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        },
        should_fail=False
    ))

    # Scenario 5: ALERTS_REQUIRED=true with both systems valid (should PASS)
    results.append(test_scenario(
        "Production mode with all credentials valid",
        {
            'ALERTS_REQUIRED': 'true',
            'TELEGRAM_BOT_TOKEN': '1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ',
            'TELEGRAM_CHAT_ID': '-1001234567890',
            'EMAIL_FROM': 'sender@company.com',
            'EMAIL_TO': 'recipient@company.com',
            'SMTP_USERNAME': 'user@gmail.com',
            'SMTP_PASSWORD': 'realpassword123',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        },
        should_fail=False
    ))

    # Scenario 6: Empty credentials with ALERTS_REQUIRED=true (should FAIL)
    results.append(test_scenario(
        "Production mode with no credentials",
        {
            'ALERTS_REQUIRED': 'true',
            'TELEGRAM_BOT_TOKEN': '',
            'TELEGRAM_CHAT_ID': '',
            'EMAIL_FROM': '',
            'EMAIL_TO': '',
            'SMTP_USERNAME': '',
            'SMTP_PASSWORD': '',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        },
        should_fail=True
    ))

    # Print summary
    print("\n" + "=" * 70)
    print("  TEST SUMMARY")
    print("=" * 70)

    all_passed = all(results)
    passed_count = sum(results)
    total_count = len(results)

    print(f"\nTests Passed: {passed_count}/{total_count}")

    if all_passed:
        print("\n[SUCCESS] All scenarios behaved as expected!")
        print("\nKey Behaviors Verified:")
        print("  [PASS] ALERTS_REQUIRED=true fails with invalid credentials")
        print("  [PASS] ALERTS_REQUIRED=false allows invalid credentials")
        print("  [PASS] At least one alert system must be valid in production")
        print("  [PASS] Both alert systems can be individually valid")
        print("  [PASS] Both alert systems can be valid together")
        print("  [PASS] Empty credentials are rejected in production")
        return 0
    else:
        print("\n[FAIL] Some scenarios did not behave as expected!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
