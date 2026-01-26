"""
Configuration management for Geopolitical Insider Trading Detection System
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Main configuration class"""

    # Polymarket API
    POLYMARKET_API_KEY = os.getenv('POLYMARKET_API_KEY')
    POLYMARKET_DATA_API = 'https://data-api.polymarket.com'
    POLYMARKET_CLOB_API = 'https://clob.polymarket.com'
    POLYMARKET_GAMMA_API = 'https://gamma-api.polymarket.com'

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/geoint')

    # Blockchain
    POLYGON_RPC_URL = os.getenv('POLYGON_RPC_URL')

    # Polymarket Contract Addresses on Polygon
    CONTRACTS = {
        'CTF_EXCHANGE': '0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E',
        'CONDITIONAL_TOKENS': '0x4D97DCd97eC945f40cF65F87097ACe5EA0476045',
        'NEG_RISK_CTF_EXCHANGE': '0xC5d563A36AE78145C45a50134d48A1215220f80a'
    }

    # Blockchain RPC Rate Limiting
    # Public RPCs typically allow 10-30 RPS, premium endpoints allow more
    RPC_RATE_LIMIT_CALLS_PER_SECOND = float(os.getenv('RPC_RATE_LIMIT_CALLS_PER_SECOND', '10.0'))
    RPC_RATE_LIMIT_BURST_SIZE = int(os.getenv('RPC_RATE_LIMIT_BURST_SIZE', '20'))

    # Circuit Breaker Configuration
    RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv('RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD', '5'))
    RPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = float(os.getenv('RPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT', '60.0'))
    RPC_CIRCUIT_BREAKER_SUCCESS_THRESHOLD = int(os.getenv('RPC_CIRCUIT_BREAKER_SUCCESS_THRESHOLD', '2'))

    # Retry Configuration
    RPC_MAX_RETRIES = int(os.getenv('RPC_MAX_RETRIES', '3'))
    RPC_RETRY_BASE_DELAY = float(os.getenv('RPC_RETRY_BASE_DELAY', '1.0'))
    RPC_RETRY_MAX_DELAY = float(os.getenv('RPC_RETRY_MAX_DELAY', '30.0'))

    # Monitoring Thresholds
    MIN_BET_SIZE_USD = float(os.getenv('MIN_BET_SIZE_USD', '10000'))
    SUSPICION_THRESHOLD_WATCH = int(os.getenv('SUSPICION_THRESHOLD_WATCH', '50'))
    SUSPICION_THRESHOLD_SUSPICIOUS = int(os.getenv('SUSPICION_THRESHOLD_SUSPICIOUS', '70'))
    SUSPICION_THRESHOLD_CRITICAL = int(os.getenv('SUSPICION_THRESHOLD_CRITICAL', '85'))

    # API Polling
    POLL_INTERVAL_SECONDS = int(os.getenv('POLL_INTERVAL_SECONDS', '60'))

    # PizzINT
    PIZZINT_URL = os.getenv('PIZZINT_URL', 'https://pizzint.io')
    SCRAPE_INTERVAL_MINUTES = int(os.getenv('SCRAPE_INTERVAL_MINUTES', '30'))

    # Alerts - Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Alerts - Email
    EMAIL_FROM = os.getenv('EMAIL_FROM')
    EMAIL_TO = os.getenv('EMAIL_TO')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

    # Alert System Configuration
    # When True, system will fail at startup if alert credentials are invalid/missing
    # When False, system will run without alerts (for development/testing only)
    ALERTS_REQUIRED = os.getenv('ALERTS_REQUIRED', 'true').lower() in ('true', '1', 'yes')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = BASE_DIR / os.getenv('LOG_FILE', 'logs/geoint_detector.log')

    # Data directories
    DATA_DIR = BASE_DIR / 'data'
    LOGS_DIR = BASE_DIR / 'logs'

    # Geopolitical & US Politics keywords for market categorization
    GEOPOLITICAL_KEYWORDS = [
        # International Geopolitics
        'arrest', 'military', 'war', 'invasion', 'sanctions',
        'minister', 'treaty', 'raid', 'operation', 'strike', 'conflict',
        'diplomat', 'embassy', 'ambassador', 'coup', 'referendum',
        'nuclear', 'missile', 'defense', 'intelligence', 'spy',

        # US & General Politics
        'president', 'presidential', 'vice president', 'vp',
        'senate', 'senator', 'house', 'congress', 'congressional',
        'speaker', 'majority leader', 'minority leader',
        'election', 'primary', 'caucus', 'midterm', 'ballot',
        'republican', 'democrat', 'gop', 'dnc', 'rnc',
        'governor', 'legislature', 'supreme court', 'justice',
        'cabinet', 'secretary', 'confirmation', 'nominee',
        'impeachment', 'impeach', 'resignation', 'resign',
        'fbi', 'cia', 'doj', 'attorney general', 'indictment',
        'bill', 'legislation', 'amendment', 'veto', 'executive order',
        'white house', 'biden', 'trump', 'harris', 'pence',
        'pelosi', 'mcconnell', 'schumer', 'mccarthy',

        # US Economic/Financial Politics
        'fed', 'federal reserve', 'treasury', 'tariff', 'trade war',
        'debt ceiling', 'shutdown', 'budget'
    ]

    # High-risk keywords for enhanced scoring
    HIGH_RISK_KEYWORDS = [
        'arrest', 'military', 'raid', 'operation', 'strike',
        'invasion', 'war', 'coup', 'assassination'
    ]

    # API request settings
    API_TIMEOUT_SECONDS = 10
    API_MAX_RETRIES = 3
    API_RETRY_DELAY_SECONDS = 5

    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls, phase: int = 1):
        """
        Validate critical configuration values

        Args:
            phase: Development phase (1=API only, 2=Database, etc.)
        """
        errors = []
        warnings = []

        # Phase 1: API Integration - require API key
        if not cls.POLYMARKET_API_KEY:
            errors.append("POLYMARKET_API_KEY is not set (required for Phase 1)")

        # Phase 2+: Database
        if phase >= 2:
            if not cls.DATABASE_URL or 'localhost' in cls.DATABASE_URL:
                warnings.append("DATABASE_URL not configured (needed for Phase 2)")

        # Phase 4+: Blockchain
        if phase >= 4:
            if not cls.POLYGON_RPC_URL:
                warnings.append("POLYGON_RPC_URL not configured (needed for Phase 4)")

        # Phase 5+: Alerts - Use strict validation
        if phase >= 5:
            cls.validate_alert_credentials()

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(warning)

        return True

    @classmethod
    def validate_alert_credentials(cls):
        """
        Validate alert system credentials with fail-fast behavior.

        When ALERTS_REQUIRED=true (default), this method will raise an error
        if credentials are missing or contain placeholder values.

        When ALERTS_REQUIRED=false, it will log prominent warnings but allow
        the system to run without alerts (for development/testing only).

        Raises:
            ValueError: When ALERTS_REQUIRED=true and credentials are invalid
        """
        from alerts.credential_validator import CredentialValidator, CredentialValidationError

        import logging
        logger = logging.getLogger(__name__)

        # Validate Telegram credentials
        telegram_valid, telegram_errors = CredentialValidator.validate_telegram_credentials(
            bot_token=cls.TELEGRAM_BOT_TOKEN,
            chat_id=cls.TELEGRAM_CHAT_ID,
            required=cls.ALERTS_REQUIRED
        )

        # Validate Email credentials
        email_valid, email_errors = CredentialValidator.validate_email_credentials(
            smtp_server=cls.SMTP_SERVER,
            smtp_port=cls.SMTP_PORT,
            smtp_username=cls.SMTP_USERNAME,
            smtp_password=cls.SMTP_PASSWORD,
            from_email=cls.EMAIL_FROM,
            to_email=cls.EMAIL_TO,
            required=cls.ALERTS_REQUIRED
        )

        # Determine overall alert status
        any_alerts_configured = telegram_valid or email_valid
        all_alerts_configured = telegram_valid and email_valid

        # Handle based on ALERTS_REQUIRED setting
        if cls.ALERTS_REQUIRED:
            # In production mode, at least one alert method must be configured
            if not any_alerts_configured:
                all_errors = telegram_errors + email_errors
                error_msg = (
                    "ALERTS_REQUIRED=true but no alert systems are properly configured!\n\n"
                    "Alert Configuration Errors:\n"
                )
                for error in all_errors:
                    error_msg += f"  - {error}\n"

                error_msg += (
                    "\nTo fix this, either:\n"
                    "  1. Configure at least one alert system (Telegram OR Email) in your .env file\n"
                    "  2. Set ALERTS_REQUIRED=false to run without alerts (NOT recommended for production)\n"
                )

                raise CredentialValidationError(error_msg)

            # Warn about partially configured alerts
            if not all_alerts_configured:
                if not telegram_valid:
                    logger.warning("Telegram alerts not configured - only Email alerts will be sent")
                    CredentialValidator.log_disabled_alert_warning("Telegram")
                if not email_valid:
                    logger.warning("Email alerts not configured - only Telegram alerts will be sent")
                    CredentialValidator.log_disabled_alert_warning("Email")

            logger.info("Alert system validation passed - alerts are properly configured")

        else:
            # Development/testing mode - alerts are optional
            if not any_alerts_configured:
                CredentialValidator.log_disabled_alert_warning("ALL")
                logger.warning(
                    "Running in ALERTS_REQUIRED=false mode - this should ONLY be used for "
                    "development and testing. NEVER run in production without alerts!"
                )
            else:
                logger.info("Alert credentials partially configured (ALERTS_REQUIRED=false mode)")
                if not telegram_valid:
                    CredentialValidator.log_disabled_alert_warning("Telegram")
                if not email_valid:
                    CredentialValidator.log_disabled_alert_warning("Email")


# Create config instance
config = Config()

# Ensure directories exist on import
config.ensure_directories()
