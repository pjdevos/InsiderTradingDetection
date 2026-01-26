"""
Polymarket API Client for fetching trade data and market information
"""
import requests
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
from web3 import Web3

from config import config


logger = logging.getLogger(__name__)


class PolymarketAPIClient:
    """
    Primary interface to Polymarket official APIs

    Provides access to:
    - Data API: User activity and trades
    - CLOB API: Orderbook and order fills
    - Gamma API: Market metadata
    """

    BASE_URLS = {
        'data': config.POLYMARKET_DATA_API,
        'clob': config.POLYMARKET_CLOB_API,
        'gamma': config.POLYMARKET_GAMMA_API
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Polymarket API client

        Args:
            api_key: Optional API key for authenticated endpoints
        """
        self.api_key = api_key or config.POLYMARKET_API_KEY
        self.session = requests.Session()

        # Validate API key
        if not self.api_key:
            logger.warning(
                "No API key configured. Some endpoints may require authentication. "
                "Set POLYMARKET_API_KEY in .env file."
            )
        elif self.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_key}'
            })
            logger.info("PolymarketAPIClient initialized with API key")
        else:
            logger.info("PolymarketAPIClient initialized without API key")

    def _validate_wallet_address(self, address: str) -> str:
        """
        Validate Ethereum wallet address format with EIP-55 checksum validation

        Args:
            address: Ethereum address to validate

        Returns:
            Checksummed address (normalized format)

        Raises:
            ValueError: If address format is invalid
        """
        if not address:
            raise ValueError("Wallet address cannot be empty")

        if not isinstance(address, str):
            raise ValueError(f"Wallet address must be string, got {type(address)}")

        if len(address) != 42:
            raise ValueError(f"Invalid wallet address length: {len(address)} (expected 42)")

        if not address.startswith('0x'):
            raise ValueError(f"Wallet address must start with '0x'")

        # Validate hex characters
        try:
            int(address, 16)
        except ValueError:
            raise ValueError(f"Wallet address contains invalid hex characters")

        # Validate and convert to checksum address using Web3 (EIP-55)
        # This accepts both checksummed and non-checksummed addresses
        # and returns the properly checksummed version
        try:
            return Web3.to_checksum_address(address)
        except ValueError as e:
            raise ValueError(f"Invalid Ethereum address: {address}") from e

    def _validate_limit(self, limit: int, max_limit: int = 1000) -> int:
        """
        Validate and cap limit parameter

        Args:
            limit: Requested limit
            max_limit: Maximum allowed limit

        Returns:
            Validated limit (capped at max_limit)

        Raises:
            ValueError: If limit is invalid
        """
        if not isinstance(limit, int):
            raise ValueError(f"Limit must be integer, got {type(limit)}")

        if limit < 1:
            raise ValueError(f"Limit must be positive, got {limit}")

        if limit > max_limit:
            logger.warning(f"Limit {limit} exceeds maximum {max_limit}, capping to {max_limit}")
            return max_limit

        return limit

    def _validate_market_id(self, market_id: str) -> str:
        """
        Validate market ID format

        Args:
            market_id: Market identifier

        Returns:
            Validated market ID

        Raises:
            ValueError: If market_id is invalid
        """
        if not market_id:
            raise ValueError("Market ID cannot be empty")

        if not isinstance(market_id, str):
            raise ValueError(f"Market ID must be string, got {type(market_id)}")

        return market_id

    def _make_request(self, url: str, params: Dict = None, api_type: str = 'data') -> Optional[Dict]:
        """
        Make HTTP request with error handling and retries

        Args:
            url: Full URL to request
            params: Query parameters
            api_type: Type of API (for logging)

        Returns:
            JSON response or None on error
        """
        response = None

        for attempt in range(config.API_MAX_RETRIES):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=config.API_TIMEOUT_SECONDS
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                if response and response.status_code == 429:  # Rate limited
                    wait_time = config.API_RETRY_DELAY_SECONDS * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Rate limited on {api_type} API, "
                        f"waiting {wait_time}s before retry {attempt + 1}/{config.API_MAX_RETRIES}"
                    )
                    time.sleep(wait_time)
                    continue
                elif response and 400 <= response.status_code < 500:
                    # Client error - don't retry (except 429 handled above)
                    logger.error(f"Client error on {api_type} API: {e} (status: {response.status_code})")
                    return None
                else:
                    # Server error or unknown - retry
                    logger.error(f"HTTP error on {api_type} API: {e}")
                    if attempt < config.API_MAX_RETRIES - 1:
                        time.sleep(config.API_RETRY_DELAY_SECONDS)
                        continue
                    return None

            except requests.exceptions.Timeout:
                logger.warning(
                    f"Timeout on {api_type} API "
                    f"(attempt {attempt + 1}/{config.API_MAX_RETRIES})"
                )
                if attempt < config.API_MAX_RETRIES - 1:
                    time.sleep(config.API_RETRY_DELAY_SECONDS)
                    continue
                return None

            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on {api_type} API: {e}")
                if attempt < config.API_MAX_RETRIES - 1:
                    time.sleep(config.API_RETRY_DELAY_SECONDS)
                    continue
                return None

        logger.error(f"All {config.API_MAX_RETRIES} retry attempts failed for {url}")
        return None

    def get_user_activity(self,
                         wallet_address: str,
                         limit: int = 100,
                         offset: int = 0) -> List[Dict]:
        """
        Fetch trading history for a specific wallet

        Args:
            wallet_address: Ethereum wallet address
            limit: Maximum number of trades to return
            offset: Pagination offset

        Returns:
            List of trades with:
            - timestamp
            - market_id
            - amount (bet size in USD)
            - price
            - outcome (YES/NO)
            - transaction_hash (for blockchain verification)
        """
        # Validate inputs
        wallet_address = self._validate_wallet_address(wallet_address)
        limit = self._validate_limit(limit)

        url = f"{self.BASE_URLS['data']}/user-activity"
        params = {
            'address': wallet_address,
            'limit': limit,
            'offset': offset
        }

        logger.info(f"Fetching user activity for wallet {wallet_address[:10]}...")
        result = self._make_request(url, params, 'data')
        return result if result else []

    def get_trades(self,
                   market_id: Optional[str] = None,
                   user_address: Optional[str] = None,
                   start_time: Optional[datetime] = None,
                   end_time: Optional[datetime] = None,
                   limit: int = 100) -> List[Dict]:
        """
        Fetch historical trades across markets or filtered

        Use for: Monitoring all large trades in real-time

        Args:
            market_id: Filter by specific market
            user_address: Filter by specific user
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of trades

        Returns:
            List of trade objects
        """
        # Validate inputs
        limit = self._validate_limit(limit)
        if user_address:
            user_address = self._validate_wallet_address(user_address)
        if market_id:
            market_id = self._validate_market_id(market_id)

        url = f"{self.BASE_URLS['data']}/trades"
        params = {'limit': limit}

        if market_id:
            params['market'] = market_id
        if user_address:
            params['user'] = user_address
        if start_time:
            params['start_time'] = start_time.isoformat()
        if end_time:
            params['end_time'] = end_time.isoformat()

        active_filters = [k for k in params.keys() if k != 'limit']
        logger.info(f"Fetching trades (limit={limit}, filters={active_filters})")
        result = self._make_request(url, params, 'data')
        return result if result else []

    def get_order_fills(self,
                       market: Optional[str] = None,
                       maker: Optional[str] = None,
                       taker: Optional[str] = None,
                       limit: int = 100) -> List[Dict]:
        """
        Get trade fills from CLOB orderbook

        Returns:
            - maker/taker addresses
            - fill prices
            - sizes
            - timestamps

        Use for: Real-time trade monitoring

        Args:
            market: Filter by market
            maker: Filter by maker address
            taker: Filter by taker address
            limit: Maximum number of fills
        """
        # Validate inputs
        if maker:
            maker = self._validate_wallet_address(maker)
        if taker:
            taker = self._validate_wallet_address(taker)

        url = f"{self.BASE_URLS['clob']}/order-fills"
        params = {'limit': limit}

        if market:
            params['market'] = market
        if maker:
            params['maker'] = maker
        if taker:
            params['taker'] = taker

        logger.info(f"Fetching order fills (limit={limit})")
        result = self._make_request(url, params, 'clob')
        return result if result else []

    def get_markets(self,
                   active: bool = True,
                   closed: bool = False,
                   tag: Optional[str] = None,
                   limit: int = 100) -> List[Dict]:
        """
        Discover markets with metadata

        Returns:
            - market_id
            - title/question
            - category/tags
            - close_time
            - volume

        Use for: Categorizing markets as geopolitical

        Args:
            active: Include active markets
            closed: Include closed markets
            tag: Filter by tag
            limit: Maximum number of markets
        """
        # Validate inputs
        limit = self._validate_limit(limit)

        url = f"{self.BASE_URLS['gamma']}/markets"
        params = {
            'active': str(active).lower(),
            'closed': str(closed).lower(),
            'limit': limit
        }

        if tag:
            params['tag'] = tag

        logger.info(f"Fetching markets (active={active}, closed={closed})")
        result = self._make_request(url, params, 'gamma')
        return result if result else []

    def get_market(self, market_id: str) -> Optional[Dict]:
        """
        Get detailed information for a specific market

        Args:
            market_id: Market identifier

        Returns:
            Market details or None
        """
        # Validate input
        market_id = self._validate_market_id(market_id)

        url = f"{self.BASE_URLS['gamma']}/markets/{market_id}"

        logger.info(f"Fetching market details for {market_id}")
        return self._make_request(url, api_type='gamma')

    def categorize_market(self, market: Dict) -> str:
        """
        Determine if market is geopolitical/government action

        Categories:
            - GEOPOLITICS
            - GOVERNMENT_ACTION
            - MILITARY
            - ELECTIONS
            - OTHER

        Args:
            market: Market object with 'question' and 'tags' fields

        Returns:
            Category string
        """
        title = market.get('question', '').lower()
        tags = [t.lower() for t in market.get('tags', [])]

        # Blacklist for false positives (sports, esports, entertainment)
        # Note: Removed 'vs.', 'vs ', ' map ', 'winner', 'loser' - can appear in political markets
        FALSE_POSITIVE_PATTERNS = [
            'counter-strike', 'counter strike', 'csgo', 'cs2', 'cs:',
            'dota', 'league of legends', 'valorant', 'overwatch',
            'nba', 'nfl', 'mlb', 'nhl', 'mls',
            'lakers', 'celtics', 'warriors', 'bulls', 'heat',
            'yankees', 'dodgers', 'red sox', 'cubs', 'mets',
            'patriots', 'cowboys', 'packers', 'chiefs', 'eagles',
            'rangers', 'bruins', 'penguins', 'capitals', 'senators',
            'manchester', 'liverpool', 'chelsea', 'arsenal', 'barcelona',
            'real madrid', 'bayern', 'juventus', 'psg',
            'super bowl', 'world series', 'stanley cup', 'finals',
            'playoff', 'championship', 'tournament', 'esport',
        ]

        # Check blacklist first - skip sports/esports
        if any(bp in title for bp in FALSE_POSITIVE_PATTERNS):
            return 'OTHER'

        # Check for geopolitical keywords in title (whole word match)
        import re
        for kw in config.GEOPOLITICAL_KEYWORDS:
            # Use word boundary for short keywords to avoid false positives (e.g., "cia" in "Valencia")
            if len(kw) <= 4:
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, title):
                    return 'GEOPOLITICS'
            elif kw in title:
                return 'GEOPOLITICS'

        # Check for geopolitical tags
        geopolitical_tags = ['politics', 'world', 'international', 'military', 'government']
        if any(tag in tags for tag in geopolitical_tags):
            return 'GEOPOLITICS'

        return 'OTHER'

    def calculate_bet_size_usd(self, trade: Dict) -> float:
        """
        Calculate bet size in USD from trade data

        Polymarket uses USDC, so amount should be in USD already

        Args:
            trade: Trade object

        Returns:
            Bet size in USD
        """
        # Adjust based on actual API response structure
        amount = trade.get('amount', 0)

        # Handle different possible field names
        if amount == 0:
            amount = trade.get('size', 0)
        if amount == 0:
            amount = trade.get('value', 0)

        return float(amount)

    def is_large_trade(self, trade: Dict, threshold: float = None) -> bool:
        """
        Check if trade meets large trade threshold

        Args:
            trade: Trade object
            threshold: USD threshold (defaults to config value)

        Returns:
            True if trade is above threshold
        """
        threshold = threshold or config.MIN_BET_SIZE_USD
        bet_size = self.calculate_bet_size_usd(trade)
        return bet_size >= threshold

    def filter_geopolitical_markets(self, markets: List[Dict]) -> List[Dict]:
        """
        Filter markets to only geopolitical ones

        Args:
            markets: List of market objects

        Returns:
            Filtered list of geopolitical markets
        """
        geopolitical = []
        for market in markets:
            if self.categorize_market(market) == 'GEOPOLITICS':
                geopolitical.append(market)

        logger.info(f"Filtered {len(geopolitical)} geopolitical markets from {len(markets)} total")
        return geopolitical

    def get_geopolitical_markets(self, limit: int = 100) -> List[Dict]:
        """
        Get all active geopolitical markets

        Args:
            limit: Maximum markets to fetch

        Returns:
            List of geopolitical markets
        """
        all_markets = self.get_markets(active=True, limit=limit)
        return self.filter_geopolitical_markets(all_markets)

    def close(self):
        """
        Close the session and cleanup resources

        Call this when done using the client to prevent resource leaks
        """
        if self.session:
            self.session.close()
            logger.info("PolymarketAPIClient session closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.close()
        return False
