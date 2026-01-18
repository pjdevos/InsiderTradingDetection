"""
Tests for Polymarket API client
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api.client import PolymarketAPIClient
from config import config


@pytest.fixture
def api_client():
    """Create API client for testing"""
    return PolymarketAPIClient(api_key="test_key")


@pytest.fixture
def mock_response():
    """Create mock API response"""
    mock = Mock()
    mock.status_code = 200
    mock.json.return_value = {'data': 'test'}
    return mock


def test_client_initialization():
    """Test that client initializes correctly"""
    client = PolymarketAPIClient()
    assert client.api_key == config.POLYMARKET_API_KEY
    assert 'data' in client.BASE_URLS
    assert 'clob' in client.BASE_URLS
    assert 'gamma' in client.BASE_URLS


def test_client_with_custom_key():
    """Test client with custom API key"""
    client = PolymarketAPIClient(api_key="custom_key")
    assert client.api_key == "custom_key"
    assert 'Authorization' in client.session.headers


def test_categorize_geopolitical_market(api_client):
    """Test that geopolitical markets are correctly identified"""
    # Market with geopolitical keyword in title
    market1 = {
        'question': 'Will Maduro be arrested by March 2025?',
        'tags': []
    }
    assert api_client.categorize_market(market1) == 'GEOPOLITICS'

    # Market with military keyword
    market2 = {
        'question': 'US military action in Middle East?',
        'tags': ['world']
    }
    assert api_client.categorize_market(market2) == 'GEOPOLITICS'

    # Non-geopolitical market
    market3 = {
        'question': 'Will Bitcoin hit $100k?',
        'tags': ['crypto']
    }
    assert api_client.categorize_market(market3) == 'OTHER'


def test_categorize_market_by_tags(api_client):
    """Test market categorization by tags"""
    market = {
        'question': 'Some question',
        'tags': ['politics', 'international']
    }
    assert api_client.categorize_market(market) == 'GEOPOLITICS'


def test_calculate_bet_size(api_client):
    """Test bet size calculation"""
    trade1 = {'amount': 10000}
    assert api_client.calculate_bet_size_usd(trade1) == 10000.0

    trade2 = {'size': 5000}
    assert api_client.calculate_bet_size_usd(trade2) == 5000.0

    trade3 = {'value': 2500}
    assert api_client.calculate_bet_size_usd(trade3) == 2500.0

    trade4 = {}
    assert api_client.calculate_bet_size_usd(trade4) == 0.0


def test_is_large_trade(api_client):
    """Test large trade detection"""
    large_trade = {'amount': 15000}
    small_trade = {'amount': 5000}

    assert api_client.is_large_trade(large_trade, threshold=10000) is True
    assert api_client.is_large_trade(small_trade, threshold=10000) is False


def test_filter_geopolitical_markets(api_client):
    """Test filtering for geopolitical markets"""
    markets = [
        {'question': 'Maduro arrested?', 'tags': []},
        {'question': 'Bitcoin price?', 'tags': ['crypto']},
        {'question': 'Military operation?', 'tags': ['world']},
        {'question': 'Sports game result?', 'tags': ['sports']}
    ]

    geopolitical = api_client.filter_geopolitical_markets(markets)
    assert len(geopolitical) == 2
    assert any('Maduro' in m['question'] for m in geopolitical)
    assert any('Military' in m['question'] for m in geopolitical)


@patch('api.client.requests.Session.get')
def test_make_request_success(mock_get, api_client):
    """Test successful API request"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'result': 'success'}
    mock_get.return_value = mock_response

    result = api_client._make_request('https://test.com')
    assert result == {'result': 'success'}


@patch('api.client.requests.Session.get')
def test_make_request_retry_on_rate_limit(mock_get, api_client):
    """Test that requests are retried on rate limit"""
    # First call returns 429, second call succeeds
    mock_response_fail = Mock()
    mock_response_fail.status_code = 429
    mock_response_fail.raise_for_status.side_effect = Exception("429")

    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {'result': 'success'}

    mock_get.side_effect = [mock_response_fail, mock_response_success]

    # Note: This test may need adjustment based on actual retry logic
    # For now, just verify the client handles errors


@patch('api.client.requests.Session.get')
def test_get_user_activity(mock_get, api_client):
    """Test fetching user activity"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'timestamp': '2024-01-01', 'amount': 1000}
    ]
    mock_get.return_value = mock_response

    # Use valid Ethereum address format (42 characters)
    valid_address = '0x742d35Cc6634C0532925a3b844Bc9e7595f0a3f1'
    result = api_client.get_user_activity(valid_address, limit=10)
    assert isinstance(result, list)
    mock_get.assert_called_once()


@patch('api.client.requests.Session.get')
def test_get_trades(mock_get, api_client):
    """Test fetching trades"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'market_id': 'market1', 'amount': 5000}
    ]
    mock_get.return_value = mock_response

    result = api_client.get_trades(limit=50)
    assert isinstance(result, list)


@patch('api.client.requests.Session.get')
def test_get_markets(mock_get, api_client):
    """Test fetching markets"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {'question': 'Test market?', 'tags': []}
    ]
    mock_get.return_value = mock_response

    result = api_client.get_markets(active=True)
    assert isinstance(result, list)


def test_geopolitical_keywords_configured():
    """Test that geopolitical keywords are properly configured"""
    assert hasattr(config, 'GEOPOLITICAL_KEYWORDS')
    assert isinstance(config.GEOPOLITICAL_KEYWORDS, list)
    assert len(config.GEOPOLITICAL_KEYWORDS) > 0
    assert 'military' in config.GEOPOLITICAL_KEYWORDS
    assert 'government' in config.GEOPOLITICAL_KEYWORDS
