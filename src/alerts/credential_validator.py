"""
Credential validation system to ensure alerts are properly configured or explicitly disabled.

This module prevents the dangerous scenario where the system appears operational but
critical alerts are silently disabled due to missing or placeholder credentials.
"""
import logging
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


class CredentialValidationError(Exception):
    """Raised when required credentials are missing or invalid"""
    pass


class CredentialValidator:
    """
    Validates credentials and configuration to prevent silent failures.

    This validator checks for common placeholder patterns and ensures that
    when alerts are required, they are properly configured. When alerts are
    not required, it logs prominent warnings to make the disabled state visible.
    """

    # Common placeholder patterns that indicate invalid credentials
    PLACEHOLDER_PATTERNS = [
        'your',           # "YOUR_TOKEN_HERE"
        'xxx',            # "XXXXXXXXXX"
        'placeholder',    # "PLACEHOLDER_VALUE"
        'changeme',       # "CHANGEME"
        'todo',           # "TODO"
        'example.com',    # "example@example.com"
        'test_',          # "test_token" (with underscore to avoid false positives)
        'dummy',          # "dummy_value"
        'replace',        # "REPLACE_ME"
        'insert',         # "INSERT_HERE"
    ]

    @staticmethod
    def is_placeholder(value: Optional[str]) -> bool:
        """
        Check if a credential value appears to be a placeholder.

        Args:
            value: The credential value to check

        Returns:
            True if the value is None, empty, or contains placeholder patterns

        Examples:
            >>> CredentialValidator.is_placeholder(None)
            True
            >>> CredentialValidator.is_placeholder("")
            True
            >>> CredentialValidator.is_placeholder("YOUR_TOKEN_HERE")
            True
            >>> CredentialValidator.is_placeholder("actual_valid_token_123")
            False
        """
        # None or empty string
        if not value or not value.strip():
            return True

        # Check for placeholder patterns (case-insensitive)
        value_lower = value.lower()
        return any(pattern in value_lower for pattern in CredentialValidator.PLACEHOLDER_PATTERNS)

    @staticmethod
    def validate_required(name: str, value: Optional[str], context: str = "") -> None:
        """
        Validate that a required credential is present and not a placeholder.

        This method enforces strict validation and raises an error if the
        credential is missing or appears to be a placeholder value.

        Args:
            name: The name of the credential (for error messages)
            value: The credential value to validate
            context: Additional context for the error message (e.g., "Telegram", "Email")

        Raises:
            CredentialValidationError: If the credential is invalid or missing

        Examples:
            >>> CredentialValidator.validate_required("API_KEY", "actual_key")
            # No error

            >>> CredentialValidator.validate_required("API_KEY", "YOUR_KEY_HERE")
            # Raises CredentialValidationError
        """
        if CredentialValidator.is_placeholder(value):
            context_msg = f" for {context}" if context else ""

            # Provide helpful error message
            error_msg = (
                f"Invalid credential: {name}{context_msg}\n"
                f"  Current value: {repr(value)}\n"
                f"  The credential is missing or appears to be a placeholder.\n"
                f"  \n"
                f"  To fix this:\n"
                f"  1. Set a valid value in your .env file\n"
                f"  2. OR set ALERTS_REQUIRED=false to explicitly disable alerts\n"
            )

            raise CredentialValidationError(error_msg)

    @staticmethod
    def validate_optional(name: str, value: Optional[str]) -> bool:
        """
        Validate an optional credential and return whether it's properly configured.

        Unlike validate_required(), this method does not raise an error for
        invalid credentials - it just returns False and logs a warning.

        Args:
            name: The name of the credential (for logging)
            value: The credential value to validate

        Returns:
            True if the credential is valid, False otherwise
        """
        is_valid = not CredentialValidator.is_placeholder(value)

        if not is_valid:
            logger.warning(f"Optional credential {name} is not configured or contains placeholder value")

        return is_valid

    @staticmethod
    def validate_telegram_credentials(
        bot_token: Optional[str],
        chat_id: Optional[str],
        required: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate Telegram credentials.

        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID
            required: Whether these credentials are required

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check bot token
        if CredentialValidator.is_placeholder(bot_token):
            errors.append("TELEGRAM_BOT_TOKEN is missing or contains placeholder value")

        # Check chat ID
        if CredentialValidator.is_placeholder(chat_id):
            errors.append("TELEGRAM_CHAT_ID is missing or contains placeholder value")

        is_valid = len(errors) == 0

        if required and not is_valid:
            # When required, these are critical errors
            return False, errors
        elif not required and not is_valid:
            # When not required, just log warnings
            for error in errors:
                logger.warning(f"Telegram not configured: {error}")
            return False, []

        return True, []

    @staticmethod
    def validate_email_credentials(
        smtp_server: Optional[str],
        smtp_port: Optional[int],
        smtp_username: Optional[str],
        smtp_password: Optional[str],
        from_email: Optional[str],
        to_email: Optional[str],
        required: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Validate email/SMTP credentials.

        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP port
            smtp_username: SMTP username
            smtp_password: SMTP password
            from_email: Sender email address
            to_email: Recipient email address
            required: Whether these credentials are required

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check SMTP server
        if CredentialValidator.is_placeholder(smtp_server):
            errors.append("SMTP_SERVER is missing or contains placeholder value")

        # Check SMTP port (validate it's a reasonable port number)
        if not smtp_port or smtp_port <= 0 or smtp_port > 65535:
            errors.append(f"SMTP_PORT is invalid: {smtp_port}")

        # Check SMTP username
        if CredentialValidator.is_placeholder(smtp_username):
            errors.append("SMTP_USERNAME is missing or contains placeholder value")

        # Check SMTP password
        if CredentialValidator.is_placeholder(smtp_password):
            errors.append("SMTP_PASSWORD is missing or contains placeholder value")

        # Check from email
        if CredentialValidator.is_placeholder(from_email):
            errors.append("EMAIL_FROM is missing or contains placeholder value")
        elif '@' not in str(from_email):
            errors.append(f"EMAIL_FROM appears to be invalid (no @ symbol): {from_email}")

        # Check to email
        if CredentialValidator.is_placeholder(to_email):
            errors.append("EMAIL_TO is missing or contains placeholder value")
        elif '@' not in str(to_email):
            errors.append(f"EMAIL_TO appears to be invalid (no @ symbol): {to_email}")

        is_valid = len(errors) == 0

        if required and not is_valid:
            # When required, these are critical errors
            return False, errors
        elif not required and not is_valid:
            # When not required, just log warnings
            for error in errors:
                logger.warning(f"Email not configured: {error}")
            return False, []

        return True, []

    @staticmethod
    def log_disabled_alert_warning(alert_type: str) -> None:
        """
        Log a prominent warning that alerts are disabled.

        This ensures that the disabled state is visible in logs, not silent.

        Args:
            alert_type: Type of alert that's disabled (e.g., "Telegram", "Email", "All")
        """
        logger.warning("=" * 70)
        logger.warning(f"  {alert_type} ALERTS ARE DISABLED")
        logger.warning("  The system is running WITHOUT alert notifications!")
        logger.warning("  This is acceptable for development/testing only.")
        logger.warning("  Set ALERTS_REQUIRED=true in production to enforce alerts.")
        logger.warning("=" * 70)
