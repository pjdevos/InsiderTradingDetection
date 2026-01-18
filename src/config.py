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

        # Phase 5+: Alerts
        if phase >= 5:
            if not cls.TELEGRAM_BOT_TOKEN or not cls.TELEGRAM_CHAT_ID:
                warnings.append("Telegram configuration incomplete (needed for Phase 5)")

        if errors:
            raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

        if warnings:
            import logging
            logger = logging.getLogger(__name__)
            for warning in warnings:
                logger.warning(warning)

        return True


# Create config instance
config = Config()

# Ensure directories exist on import
config.ensure_directories()
