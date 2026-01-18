"""
Tests for configuration module
"""
import pytest
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config


def test_config_has_required_attributes():
    """Test that Config has all required attributes"""
    required_attrs = [
        'POLYMARKET_API_KEY',
        'DATABASE_URL',
        'POLYGON_RPC_URL',
        'MIN_BET_SIZE_USD',
        'SUSPICION_THRESHOLD_CRITICAL',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]

    for attr in required_attrs:
        assert hasattr(Config, attr), f"Config missing attribute: {attr}"


def test_min_bet_size_is_numeric():
    """Test that MIN_BET_SIZE_USD is a valid number"""
    assert isinstance(Config.MIN_BET_SIZE_USD, (int, float))
    assert Config.MIN_BET_SIZE_USD > 0


def test_suspicion_thresholds_are_valid():
    """Test that suspicion thresholds are valid integers"""
    assert isinstance(Config.SUSPICION_THRESHOLD_WATCH, int)
    assert isinstance(Config.SUSPICION_THRESHOLD_SUSPICIOUS, int)
    assert isinstance(Config.SUSPICION_THRESHOLD_CRITICAL, int)

    # Check they're in logical order
    assert Config.SUSPICION_THRESHOLD_WATCH < Config.SUSPICION_THRESHOLD_SUSPICIOUS
    assert Config.SUSPICION_THRESHOLD_SUSPICIOUS < Config.SUSPICION_THRESHOLD_CRITICAL


def test_geopolitical_keywords_exist():
    """Test that geopolitical keywords are defined"""
    assert hasattr(Config, 'GEOPOLITICAL_KEYWORDS')
    assert isinstance(Config.GEOPOLITICAL_KEYWORDS, list)
    assert len(Config.GEOPOLITICAL_KEYWORDS) > 0


def test_api_urls_are_valid():
    """Test that API URLs are properly formatted"""
    assert Config.POLYMARKET_DATA_API.startswith('https://')
    assert Config.POLYMARKET_CLOB_API.startswith('https://')
    assert Config.POLYMARKET_GAMMA_API.startswith('https://')


def test_ensure_directories():
    """Test that ensure_directories creates required directories"""
    Config.ensure_directories()
    assert Config.DATA_DIR.exists()
    assert Config.LOGS_DIR.exists()


def test_contract_addresses_defined():
    """Test that Polymarket contract addresses are defined"""
    assert hasattr(Config, 'CONTRACTS')
    assert 'CTF_EXCHANGE' in Config.CONTRACTS
    assert 'CONDITIONAL_TOKENS' in Config.CONTRACTS
    assert 'NEG_RISK_CTF_EXCHANGE' in Config.CONTRACTS
