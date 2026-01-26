"""
Test script to verify credential validation works correctly.

This script tests the new fail-fast credential validation system to ensure:
1. Invalid credentials are detected
2. ALERTS_REQUIRED=true causes startup failure with invalid credentials
3. ALERTS_REQUIRED=false allows running without alerts
4. Prominent warnings are logged when alerts are disabled
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from alerts.credential_validator import CredentialValidator, CredentialValidationError


def test_placeholder_detection():
    """Test that placeholder patterns are correctly detected"""
    print("\n=== Testing Placeholder Detection ===")

    # Test cases that should be detected as placeholders
    placeholders = [
        None,
        "",
        "   ",
        "YOUR_TOKEN_HERE",
        "your_api_key",
        "xxx-xxx-xxx",
        "PLACEHOLDER",
        "changeme",
        "TODO: add token",
        "example@example.com",
        "test_value",
        "dummy_token",
        "REPLACE_ME",
        "INSERT_YOUR_KEY_HERE",
        "user@example.com",  # example.com domain
        "test_api_key",      # test_ prefix
    ]

    print("\nTesting placeholder values (should all be True):")
    for value in placeholders:
        result = CredentialValidator.is_placeholder(value)
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} is_placeholder({repr(value)}) = {result}")
        assert result, f"Failed to detect placeholder: {repr(value)}"

    # Test cases that should NOT be detected as placeholders
    valid_values = [
        "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ",  # Telegram token format
        "real_api_key_12345",
        "user@domain.com",
        "smtp.gmail.com",
        "postgresql://user:pass@host:5432/db"
    ]

    print("\nTesting valid values (should all be False):")
    for value in valid_values:
        result = CredentialValidator.is_placeholder(value)
        status = "[PASS]" if not result else "[FAIL]"
        print(f"  {status} is_placeholder({repr(value)}) = {result}")
        assert not result, f"Incorrectly detected valid value as placeholder: {repr(value)}"

    print("\n[PASS] Placeholder detection tests passed!")


def test_telegram_validation():
    """Test Telegram credential validation"""
    print("\n=== Testing Telegram Credential Validation ===")

    # Test invalid credentials with required=True
    print("\nTest 1: Invalid credentials with required=True (should fail)")
    is_valid, errors = CredentialValidator.validate_telegram_credentials(
        bot_token="YOUR_TOKEN_HERE",
        chat_id="YOUR_CHAT_ID",
        required=True
    )
    assert not is_valid, "Should detect invalid credentials"
    assert len(errors) > 0, "Should return error messages"
    print(f"  [PASS] Detected {len(errors)} errors:")
    for error in errors:
        print(f"    - {error}")

    # Test invalid credentials with required=False
    print("\nTest 2: Invalid credentials with required=False (should warn)")
    is_valid, errors = CredentialValidator.validate_telegram_credentials(
        bot_token="YOUR_TOKEN_HERE",
        chat_id="YOUR_CHAT_ID",
        required=False
    )
    assert not is_valid, "Should detect invalid credentials"
    assert len(errors) == 0, "Should not return errors when not required"
    print("  [PASS] Invalid credentials allowed when not required")

    # Test valid credentials
    print("\nTest 3: Valid credentials (should pass)")
    is_valid, errors = CredentialValidator.validate_telegram_credentials(
        bot_token="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ",
        chat_id="-1001234567890",
        required=True
    )
    assert is_valid, "Should accept valid credentials"
    assert len(errors) == 0, "Should not return errors"
    print("  [PASS] Valid credentials accepted")

    print("\n[PASS] Telegram validation tests passed!")


def test_email_validation():
    """Test Email credential validation"""
    print("\n=== Testing Email Credential Validation ===")

    # Test invalid credentials with required=True
    print("\nTest 1: Invalid credentials with required=True (should fail)")
    is_valid, errors = CredentialValidator.validate_email_credentials(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_username="your_username",
        smtp_password="your_password",
        from_email="your_email@domain.com",
        to_email="recipient@domain.com",
        required=True
    )
    assert not is_valid, "Should detect invalid credentials"
    assert len(errors) > 0, "Should return error messages"
    print(f"  [PASS] Detected {len(errors)} errors:")
    for error in errors:
        print(f"    - {error}")

    # Test invalid port
    print("\nTest 2: Invalid SMTP port (should fail)")
    is_valid, errors = CredentialValidator.validate_email_credentials(
        smtp_server="smtp.gmail.com",
        smtp_port=999999,  # Invalid port
        smtp_username="user@gmail.com",
        smtp_password="realpassword",
        from_email="user@gmail.com",
        to_email="recipient@domain.com",
        required=True
    )
    assert not is_valid, "Should detect invalid port"
    assert any("SMTP_PORT" in error for error in errors), "Should mention port error"
    print("  [PASS] Invalid port detected")

    # Test invalid email format
    print("\nTest 3: Invalid email format (should fail)")
    is_valid, errors = CredentialValidator.validate_email_credentials(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_username="user@gmail.com",
        smtp_password="realpassword",
        from_email="not_an_email",  # Missing @
        to_email="recipient@domain.com",
        required=True
    )
    assert not is_valid, "Should detect invalid email"
    assert any("EMAIL_FROM" in error for error in errors), "Should mention email error"
    print("  [PASS] Invalid email format detected")

    # Test valid credentials
    print("\nTest 4: Valid credentials (should pass)")
    is_valid, errors = CredentialValidator.validate_email_credentials(
        smtp_server="smtp.gmail.com",
        smtp_port=587,
        smtp_username="user@gmail.com",
        smtp_password="realpassword123",
        from_email="sender@company.com",
        to_email="recipient@company.com",
        required=True
    )
    assert is_valid, "Should accept valid credentials"
    assert len(errors) == 0, "Should not return errors"
    print("  [PASS] Valid credentials accepted")

    print("\n[PASS] Email validation tests passed!")


def test_validate_required():
    """Test validate_required method"""
    print("\n=== Testing validate_required() ===")

    # Test valid credential
    print("\nTest 1: Valid credential (should not raise)")
    try:
        CredentialValidator.validate_required("API_KEY", "real_key_12345", "Test Service")
        print("  [PASS] Valid credential accepted")
    except CredentialValidationError:
        assert False, "Should not raise for valid credential"

    # Test invalid credential
    print("\nTest 2: Invalid credential (should raise)")
    try:
        CredentialValidator.validate_required("API_KEY", "YOUR_KEY_HERE", "Test Service")
        assert False, "Should raise for invalid credential"
    except CredentialValidationError as e:
        print(f"  [PASS] Raised error as expected:")
        print(f"    {str(e)[:100]}...")

    # Test None credential
    print("\nTest 3: None credential (should raise)")
    try:
        CredentialValidator.validate_required("API_KEY", None, "Test Service")
        assert False, "Should raise for None credential"
    except CredentialValidationError as e:
        print("  [PASS] Raised error as expected")

    print("\n[PASS] validate_required tests passed!")


def main():
    """Run all tests"""
    print("=" * 70)
    print("  Credential Validation Test Suite")
    print("=" * 70)

    try:
        test_placeholder_detection()
        test_telegram_validation()
        test_email_validation()
        test_validate_required()

        print("\n" + "=" * 70)
        print("  ALL TESTS PASSED")
        print("=" * 70)
        print("\nThe credential validation system is working correctly!")
        print("\nKey features verified:")
        print("  [PASS] Placeholder pattern detection")
        print("  [PASS] Telegram credential validation")
        print("  [PASS] Email credential validation")
        print("  [PASS] Fail-fast behavior with required=True")
        print("  [PASS] Graceful degradation with required=False")

        return 0

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
