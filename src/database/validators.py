"""
Input validation for database operations.

This module provides validation functions to ensure data integrity
and prevent potential security issues like SQL injection if code
is ever refactored to use raw SQL.
"""
import re
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Union, List, Any

logger = logging.getLogger(__name__)


class ValidationError(ValueError):
    """Raised when input validation fails"""
    pass


class DatabaseInputValidator:
    """
    Validator for database input parameters.

    All validation methods either return the validated/normalized value
    or raise ValidationError with a descriptive message.
    """

    # Constants for validation
    WALLET_ADDRESS_LENGTH = 42
    WALLET_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')

    TX_HASH_LENGTH = 66
    TX_HASH_PATTERN = re.compile(r'^0x[a-fA-F0-9]{64}$')

    MARKET_ID_MAX_LENGTH = 100
    MARKET_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')

    # Valid alert levels and statuses
    VALID_ALERT_LEVELS = {'WATCH', 'SUSPICIOUS', 'CRITICAL'}
    VALID_ALERT_STATUSES = {'NEW', 'REVIEWED', 'DISMISSED', 'CONFIRMED'}
    VALID_BET_DIRECTIONS = {'YES', 'NO'}
    VALID_TRADE_RESULTS = {'WIN', 'LOSS', 'PENDING', 'VOID'}
    VALID_ORDER_BY_FIELDS = {'volume', 'trades', 'win_rate', 'suspicion'}

    # Limits
    MAX_LIMIT = 10000
    MAX_HOURS_LOOKBACK = 8760  # 1 year
    MIN_TIMESTAMP = datetime(2020, 1, 1, tzinfo=timezone.utc)  # Polymarket didn't exist before this
    MAX_TIMESTAMP_FUTURE = timedelta(days=365)  # Can't query more than 1 year in future

    @classmethod
    def validate_wallet_address(cls, address: Any, field_name: str = "wallet_address") -> str:
        """
        Validate Ethereum wallet address format.

        Args:
            address: Address to validate
            field_name: Name of field for error messages

        Returns:
            Lowercase normalized address

        Raises:
            ValidationError: If address format is invalid
        """
        if address is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(address, str):
            raise ValidationError(f"{field_name} must be string, got {type(address).__name__}")

        address = address.strip()

        if not address:
            raise ValidationError(f"{field_name} cannot be empty")

        if len(address) != cls.WALLET_ADDRESS_LENGTH:
            raise ValidationError(
                f"{field_name} must be {cls.WALLET_ADDRESS_LENGTH} characters, "
                f"got {len(address)}"
            )

        if not cls.WALLET_ADDRESS_PATTERN.match(address):
            raise ValidationError(
                f"{field_name} must be valid Ethereum address format (0x followed by 40 hex chars)"
            )

        return address.lower()

    @classmethod
    def validate_transaction_hash(cls, tx_hash: Any, field_name: str = "transaction_hash") -> str:
        """
        Validate Ethereum transaction hash format.

        Args:
            tx_hash: Transaction hash to validate
            field_name: Name of field for error messages

        Returns:
            Lowercase normalized transaction hash

        Raises:
            ValidationError: If hash format is invalid
        """
        if tx_hash is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(tx_hash, str):
            raise ValidationError(f"{field_name} must be string, got {type(tx_hash).__name__}")

        tx_hash = tx_hash.strip()

        if not tx_hash:
            raise ValidationError(f"{field_name} cannot be empty")

        if len(tx_hash) != cls.TX_HASH_LENGTH:
            raise ValidationError(
                f"{field_name} must be {cls.TX_HASH_LENGTH} characters, "
                f"got {len(tx_hash)}"
            )

        if not cls.TX_HASH_PATTERN.match(tx_hash):
            raise ValidationError(
                f"{field_name} must be valid transaction hash format (0x followed by 64 hex chars)"
            )

        return tx_hash.lower()

    @classmethod
    def validate_market_id(cls, market_id: Any, field_name: str = "market_id") -> str:
        """
        Validate market ID format.

        Args:
            market_id: Market ID to validate
            field_name: Name of field for error messages

        Returns:
            Validated market ID

        Raises:
            ValidationError: If market ID is invalid
        """
        if market_id is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(market_id, str):
            raise ValidationError(f"{field_name} must be string, got {type(market_id).__name__}")

        market_id = market_id.strip()

        if not market_id:
            raise ValidationError(f"{field_name} cannot be empty")

        if len(market_id) > cls.MARKET_ID_MAX_LENGTH:
            raise ValidationError(
                f"{field_name} exceeds maximum length of {cls.MARKET_ID_MAX_LENGTH}"
            )

        # Allow alphanumeric, underscore, hyphen (common market ID formats)
        # Also allow hex condition IDs that start with 0x
        if market_id.startswith('0x'):
            # Validate as hex string
            try:
                int(market_id, 16)
            except ValueError:
                raise ValidationError(f"{field_name} contains invalid hex characters")
        elif not cls.MARKET_ID_PATTERN.match(market_id):
            raise ValidationError(
                f"{field_name} contains invalid characters (allowed: alphanumeric, underscore, hyphen)"
            )

        return market_id

    @classmethod
    def validate_positive_int(
        cls,
        value: Any,
        field_name: str,
        max_value: int = None,
        allow_zero: bool = False
    ) -> int:
        """
        Validate positive integer.

        Args:
            value: Value to validate
            field_name: Name of field for error messages
            max_value: Optional maximum allowed value
            allow_zero: Whether to allow zero

        Returns:
            Validated integer

        Raises:
            ValidationError: If value is invalid
        """
        if value is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(f"{field_name} must be integer, got {type(value).__name__}")

        if allow_zero:
            if value < 0:
                raise ValidationError(f"{field_name} must be non-negative, got {value}")
        else:
            if value < 1:
                raise ValidationError(f"{field_name} must be positive, got {value}")

        if max_value is not None and value > max_value:
            raise ValidationError(f"{field_name} exceeds maximum of {max_value}, got {value}")

        return value

    @classmethod
    def validate_limit(cls, limit: Any, field_name: str = "limit") -> int:
        """
        Validate limit parameter for queries.

        Args:
            limit: Limit value to validate
            field_name: Name of field for error messages

        Returns:
            Validated limit (capped at MAX_LIMIT)

        Raises:
            ValidationError: If limit is invalid
        """
        limit = cls.validate_positive_int(limit, field_name)

        if limit > cls.MAX_LIMIT:
            logger.warning(f"{field_name} {limit} exceeds max {cls.MAX_LIMIT}, capping")
            return cls.MAX_LIMIT

        return limit

    @classmethod
    def validate_hours(cls, hours: Any, field_name: str = "hours") -> int:
        """
        Validate hours lookback parameter.

        Args:
            hours: Hours value to validate
            field_name: Name of field for error messages

        Returns:
            Validated hours value

        Raises:
            ValidationError: If hours is invalid
        """
        return cls.validate_positive_int(hours, field_name, max_value=cls.MAX_HOURS_LOOKBACK)

    @classmethod
    def validate_score(cls, score: Any, field_name: str = "score") -> int:
        """
        Validate suspicion score (0-100).

        Args:
            score: Score value to validate
            field_name: Name of field for error messages

        Returns:
            Validated score

        Raises:
            ValidationError: If score is invalid
        """
        score = cls.validate_positive_int(score, field_name, allow_zero=True)

        if score > 100:
            raise ValidationError(f"{field_name} must be 0-100, got {score}")

        return score

    @classmethod
    def validate_timestamp(
        cls,
        timestamp: Any,
        field_name: str = "timestamp",
        allow_future: bool = False
    ) -> datetime:
        """
        Validate timestamp.

        Args:
            timestamp: Timestamp to validate
            field_name: Name of field for error messages
            allow_future: Whether to allow future timestamps

        Returns:
            Validated timezone-aware datetime

        Raises:
            ValidationError: If timestamp is invalid
        """
        if timestamp is None:
            raise ValidationError(f"{field_name} cannot be None")

        if isinstance(timestamp, str):
            try:
                # Try ISO format
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                raise ValidationError(f"{field_name} is not valid ISO format")

        if not isinstance(timestamp, datetime):
            raise ValidationError(f"{field_name} must be datetime, got {type(timestamp).__name__}")

        # Ensure timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        # Validate reasonable range
        if timestamp < cls.MIN_TIMESTAMP:
            raise ValidationError(
                f"{field_name} is too far in the past (before Polymarket existed)"
            )

        max_allowed = datetime.now(timezone.utc) + cls.MAX_TIMESTAMP_FUTURE
        if not allow_future and timestamp > max_allowed:
            raise ValidationError(f"{field_name} is too far in the future")

        return timestamp

    @classmethod
    def validate_optional_timestamp(
        cls,
        timestamp: Any,
        field_name: str = "timestamp"
    ) -> Optional[datetime]:
        """
        Validate optional timestamp.

        Args:
            timestamp: Timestamp to validate (can be None)
            field_name: Name of field for error messages

        Returns:
            Validated datetime or None
        """
        if timestamp is None:
            return None
        return cls.validate_timestamp(timestamp, field_name)

    @classmethod
    def validate_alert_level(cls, level: Any, field_name: str = "alert_level") -> str:
        """
        Validate alert level.

        Args:
            level: Alert level to validate
            field_name: Name of field for error messages

        Returns:
            Validated uppercase alert level

        Raises:
            ValidationError: If level is invalid
        """
        if level is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(level, str):
            raise ValidationError(f"{field_name} must be string, got {type(level).__name__}")

        level = level.upper().strip()

        if level not in cls.VALID_ALERT_LEVELS:
            raise ValidationError(
                f"{field_name} must be one of {cls.VALID_ALERT_LEVELS}, got '{level}'"
            )

        return level

    @classmethod
    def validate_optional_alert_level(cls, level: Any, field_name: str = "alert_level") -> Optional[str]:
        """Validate optional alert level."""
        if level is None:
            return None
        return cls.validate_alert_level(level, field_name)

    @classmethod
    def validate_alert_status(cls, status: Any, field_name: str = "status") -> str:
        """
        Validate alert status.

        Args:
            status: Status to validate
            field_name: Name of field for error messages

        Returns:
            Validated uppercase status

        Raises:
            ValidationError: If status is invalid
        """
        if status is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(status, str):
            raise ValidationError(f"{field_name} must be string, got {type(status).__name__}")

        status = status.upper().strip()

        if status not in cls.VALID_ALERT_STATUSES:
            raise ValidationError(
                f"{field_name} must be one of {cls.VALID_ALERT_STATUSES}, got '{status}'"
            )

        return status

    @classmethod
    def validate_order_by(cls, order_by: Any, field_name: str = "order_by") -> str:
        """
        Validate order_by parameter for wallet queries.

        Args:
            order_by: Order by field to validate
            field_name: Name of field for error messages

        Returns:
            Validated lowercase order_by value

        Raises:
            ValidationError: If order_by is invalid
        """
        if order_by is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(order_by, str):
            raise ValidationError(f"{field_name} must be string, got {type(order_by).__name__}")

        order_by = order_by.lower().strip()

        if order_by not in cls.VALID_ORDER_BY_FIELDS:
            raise ValidationError(
                f"{field_name} must be one of {cls.VALID_ORDER_BY_FIELDS}, got '{order_by}'"
            )

        return order_by

    @classmethod
    def validate_bet_size(cls, bet_size: Any, field_name: str = "bet_size_usd") -> float:
        """
        Validate bet size.

        Args:
            bet_size: Bet size to validate
            field_name: Name of field for error messages

        Returns:
            Validated positive float

        Raises:
            ValidationError: If bet size is invalid
        """
        if bet_size is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(bet_size, (int, float)):
            raise ValidationError(f"{field_name} must be numeric, got {type(bet_size).__name__}")

        bet_size = float(bet_size)

        if bet_size <= 0:
            raise ValidationError(f"{field_name} must be positive, got {bet_size}")

        # Sanity check - no single bet should exceed $100M
        if bet_size > 100_000_000:
            raise ValidationError(f"{field_name} exceeds maximum reasonable value")

        return bet_size

    @classmethod
    def validate_optional_bet_size(cls, bet_size: Any, field_name: str = "bet_size_usd") -> Optional[float]:
        """Validate optional bet size."""
        if bet_size is None:
            return None
        return cls.validate_bet_size(bet_size, field_name)

    @classmethod
    def validate_string(
        cls,
        value: Any,
        field_name: str,
        max_length: int = 1000,
        allow_empty: bool = False
    ) -> str:
        """
        Validate string value.

        Args:
            value: String to validate
            field_name: Name of field for error messages
            max_length: Maximum allowed length
            allow_empty: Whether to allow empty strings

        Returns:
            Validated string

        Raises:
            ValidationError: If string is invalid
        """
        if value is None:
            raise ValidationError(f"{field_name} cannot be None")

        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be string, got {type(value).__name__}")

        if not allow_empty and not value.strip():
            raise ValidationError(f"{field_name} cannot be empty")

        if len(value) > max_length:
            raise ValidationError(f"{field_name} exceeds maximum length of {max_length}")

        return value

    @classmethod
    def validate_optional_string(
        cls,
        value: Any,
        field_name: str,
        max_length: int = 1000
    ) -> Optional[str]:
        """Validate optional string."""
        if value is None:
            return None
        return cls.validate_string(value, field_name, max_length, allow_empty=True)

    @classmethod
    def sanitize_for_logging(cls, value: Any, field_name: str = "value") -> str:
        """
        Sanitize a value for safe logging (mask sensitive data).

        Args:
            value: Value to sanitize
            field_name: Name of field (used to detect sensitive fields)

        Returns:
            Sanitized string safe for logging
        """
        sensitive_fields = {
            'password', 'secret', 'token', 'key', 'credential',
            'api_key', 'private_key', 'smtp_password'
        }

        field_lower = field_name.lower()

        # Mask sensitive fields
        if any(s in field_lower for s in sensitive_fields):
            return '***MASKED***'

        # Truncate long strings
        str_value = str(value)
        if len(str_value) > 100:
            return str_value[:100] + '...'

        return str_value
