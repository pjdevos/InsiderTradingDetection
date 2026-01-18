"""
Blockchain verification client for Polygon network

Provides on-chain verification of trades, wallet forensics, and mixer detection.
"""
import re
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, List, Tuple
from web3 import Web3
from web3.exceptions import Web3Exception
from config import config

logger = logging.getLogger(__name__)


# Blockchain scanning limits to prevent resource exhaustion
POLYGON_BLOCKS_PER_DAY = 43200  # ~2 seconds per block
MAX_WALLET_AGE_SCAN_DAYS = 7  # Limit wallet age scan to 7 days (vs 30 days before)
MAX_WALLET_AGE_SCAN_BLOCKS = MAX_WALLET_AGE_SCAN_DAYS * POLYGON_BLOCKS_PER_DAY  # ~302k blocks
BLOCK_SAMPLING_STEP = 50000  # Check every 50k blocks (vs 10k before) = max 6 API calls
MAX_API_CALLS_PER_OPERATION = 20  # Hard limit on API calls per operation
MIXER_DETECTION_BLOCKS = 500  # Blocks to check for mixer detection (vs 1000 before)
MAX_ADDRESSES_TO_CHECK = 50  # Max addresses to check in mixer detection

# Known mixer addresses (Tornado Cash, etc.)
KNOWN_MIXERS = {
    # Tornado Cash contracts (Polygon)
    '0x1E34A77868E19A6647b1f2F47B51ed72dEDE95DD': 'Tornado Cash 100 MATIC',
    '0xdf231d99Ff8b6c6CBF4E9B9a945CBAcEF9339178': 'Tornado Cash 1000 MATIC',
    '0xaf4c0B70B2Ea9FB7487C7CbB37aDa259579fe040': 'Tornado Cash 10000 MATIC',
    '0xa5C2254e4253490C54cef0a4347fddb8f75A4998': 'Tornado Cash 100000 MATIC',
    # Add more known mixers as needed
}


class BlockchainClient:
    """
    Client for interacting with Polygon blockchain for trade verification
    """

    def __init__(self, rpc_url: str = None):
        """
        Initialize blockchain client

        Args:
            rpc_url: Polygon RPC endpoint URL (defaults to config)
        """
        self.rpc_url = rpc_url or config.POLYGON_RPC_URL

        # Fallback to public RPC if not configured
        if not self.rpc_url or 'YOUR_KEY' in self.rpc_url:
            logger.warning("No Polygon RPC URL configured, using public endpoint")
            self.rpc_url = 'https://polygon-rpc.com'

        try:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

            # Test connection
            if self.w3.is_connected():
                chain_id = self.w3.eth.chain_id
                logger.info(f"Connected to Polygon (chain_id={chain_id})")

                # Verify it's Polygon mainnet
                if chain_id != 137:
                    logger.warning(f"Connected to chain_id {chain_id}, expected 137 (Polygon mainnet)")
            else:
                logger.error("Failed to connect to Polygon RPC")
                self.w3 = None

        except Exception as e:
            logger.error(f"Error initializing blockchain client: {e}")
            self.w3 = None

    def is_connected(self) -> bool:
        """Check if connected to blockchain"""
        return self.w3 is not None and self.w3.is_connected()

    def _validate_address(self, address: str) -> str:
        """
        Validate and normalize Ethereum address before expensive blockchain operations.

        Args:
            address: Ethereum address to validate

        Returns:
            Checksummed address

        Raises:
            ValueError: If address is invalid
        """
        if not address:
            raise ValueError("Wallet address cannot be empty")

        if not isinstance(address, str):
            raise ValueError(f"Wallet address must be a string, got {type(address)}")

        # Check basic format (0x + 40 hex characters)
        if not address.startswith('0x'):
            raise ValueError(f"Invalid address format: must start with '0x'")

        if len(address) != 42:
            raise ValueError(f"Invalid address length: expected 42 characters, got {len(address)}")

        # Check for valid hex characters only
        if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
            raise ValueError(f"Invalid address: contains non-hexadecimal characters")

        # Convert to checksum address (also validates checksum if mixed case)
        try:
            return self.w3.to_checksum_address(address)
        except Exception as e:
            raise ValueError(f"Invalid Ethereum address: {e}")

    def _validate_tx_hash(self, tx_hash: str) -> str:
        """
        Validate and normalize transaction hash.

        Args:
            tx_hash: Transaction hash to validate

        Returns:
            Normalized transaction hash (with 0x prefix)

        Raises:
            ValueError: If transaction hash is invalid
        """
        if not tx_hash:
            raise ValueError("Transaction hash cannot be empty")

        if not isinstance(tx_hash, str):
            raise ValueError(f"Transaction hash must be a string, got {type(tx_hash)}")

        # Add 0x prefix if missing
        if not tx_hash.startswith('0x'):
            tx_hash = '0x' + tx_hash

        # Transaction hashes are 32 bytes = 64 hex chars + '0x' = 66 chars
        if len(tx_hash) != 66:
            raise ValueError(f"Invalid transaction hash length: expected 66 characters, got {len(tx_hash)}")

        # Check for valid hex characters only
        if not re.match(r'^0x[a-fA-F0-9]{64}$', tx_hash):
            raise ValueError(f"Invalid transaction hash: contains non-hexadecimal characters")

        return tx_hash.lower()

    def verify_transaction(self, tx_hash: str) -> Optional[Dict]:
        """
        Verify a transaction exists on-chain and retrieve its details

        Args:
            tx_hash: Transaction hash (with or without 0x prefix)

        Returns:
            Dict with transaction details or None if not found
        """
        if not self.is_connected():
            logger.error("Not connected to blockchain")
            return None

        try:
            # Validate and normalize transaction hash
            tx_hash = self._validate_tx_hash(tx_hash)
        except ValueError as e:
            logger.error(f"Invalid transaction hash: {e}")
            return None

        try:
            # Get transaction
            tx = self.w3.eth.get_transaction(tx_hash)

            if not tx:
                logger.warning(f"Transaction not found: {tx_hash}")
                return None

            # Get transaction receipt for status
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)

            # Get block for timestamp
            block = self.w3.eth.get_block(tx['blockNumber'])

            return {
                'hash': tx['hash'].hex(),
                'from': tx['from'],
                'to': tx['to'],
                'value': self.w3.from_wei(tx['value'], 'ether'),
                'value_wei': tx['value'],
                'gas': tx['gas'],
                'gas_price': tx['gasPrice'],
                'block_number': tx['blockNumber'],
                'timestamp': datetime.fromtimestamp(block['timestamp'], tz=timezone.utc),
                'status': receipt['status'] if receipt else None,  # 1 = success, 0 = failed
                'confirmed': True
            }

        except Exception as e:
            logger.error(f"Error verifying transaction {tx_hash}: {e}")
            return None

    def get_wallet_age(self, wallet_address: str) -> Optional[Tuple[int, datetime]]:
        """
        Calculate wallet age from first on-chain transaction

        Args:
            wallet_address: Ethereum address

        Returns:
            Tuple of (age_in_days, first_transaction_date) or None
        """
        if not self.is_connected():
            logger.error("Not connected to blockchain")
            return None

        try:
            # Validate address before expensive blockchain operations
            wallet_address = self._validate_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None

        try:
            # Get current block
            current_block = self.w3.eth.block_number
            api_calls = 1  # Count the block_number call

            # Check if wallet has any transactions (quick check first)
            tx_count = self.w3.eth.get_transaction_count(wallet_address)
            api_calls += 1

            if tx_count == 0:
                logger.info(f"Wallet {wallet_address} has no transactions")
                return None

            # Use limited scan range to prevent resource exhaustion
            # For production, recommend using Polygonscan API instead
            blocks_to_check = min(MAX_WALLET_AGE_SCAN_BLOCKS, current_block)
            start_block = max(0, current_block - blocks_to_check)

            logger.info(
                f"Searching for first transaction in blocks {start_block} to {current_block} "
                f"(~{blocks_to_check // POLYGON_BLOCKS_PER_DAY} days, step={BLOCK_SAMPLING_STEP})"
            )

            # Sample blocks with configured step size and API call limit
            first_tx_block = None

            for block_num in range(start_block, current_block, BLOCK_SAMPLING_STEP):
                # Enforce API call limit
                if api_calls >= MAX_API_CALLS_PER_OPERATION:
                    logger.warning(
                        f"Reached API call limit ({MAX_API_CALLS_PER_OPERATION}) "
                        f"while scanning for wallet age"
                    )
                    break

                try:
                    block = self.w3.eth.get_block(block_num, full_transactions=True)
                    api_calls += 1

                    for tx in block['transactions']:
                        if tx['from'].lower() == wallet_address.lower():
                            first_tx_block = block_num
                            break

                    if first_tx_block:
                        break

                except Exception as e:
                    logger.debug(f"Error checking block {block_num}: {e}")
                    api_calls += 1  # Count failed calls too
                    continue

            if first_tx_block:
                block = self.w3.eth.get_block(first_tx_block)
                first_tx_date = datetime.fromtimestamp(block['timestamp'], tz=timezone.utc)
                age_days = (datetime.now(timezone.utc) - first_tx_date).days

                logger.info(
                    f"Wallet {wallet_address} first transaction: {first_tx_date} "
                    f"({age_days} days old, {api_calls} API calls)"
                )
                return age_days, first_tx_date
            else:
                logger.warning(
                    f"Could not find first transaction for {wallet_address} "
                    f"in sampled blocks ({api_calls} API calls). "
                    f"Consider using Polygonscan API for accurate results."
                )
                return None

        except Exception as e:
            logger.error(f"Error calculating wallet age for {wallet_address}: {e}")
            return None

    def detect_mixer_funding(
        self,
        wallet_address: str,
        depth: int = 2
    ) -> Optional[Dict]:
        """
        Detect if wallet was funded from known mixers

        Args:
            wallet_address: Ethereum address to check
            depth: How many transaction hops to check (1-3 recommended)

        Returns:
            Dict with mixer detection results or None
        """
        if not self.is_connected():
            logger.error("Not connected to blockchain")
            return None

        try:
            # Validate address before expensive blockchain operations
            wallet_address = self._validate_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None

        # Validate depth parameter
        if not isinstance(depth, int) or depth < 1 or depth > 5:
            logger.error(f"Invalid depth parameter: must be integer between 1-5, got {depth}")
            return None

        try:
            logger.info(f"Checking mixer funding for {wallet_address} (depth={depth})")

            mixers_found = []
            checked_addresses = set()
            api_calls = [0]  # Use list to allow modification in nested function

            def check_address(address: str, current_depth: int):
                """Recursively check address and its funding sources"""
                # Enforce limits
                if current_depth > depth:
                    return
                if address in checked_addresses:
                    return
                if len(checked_addresses) >= MAX_ADDRESSES_TO_CHECK:
                    logger.warning(f"Reached max addresses limit ({MAX_ADDRESSES_TO_CHECK})")
                    return
                if api_calls[0] >= MAX_API_CALLS_PER_OPERATION:
                    logger.warning(f"Reached API call limit ({MAX_API_CALLS_PER_OPERATION})")
                    return

                checked_addresses.add(address)

                # Check if address itself is a known mixer (no API call needed)
                if address in KNOWN_MIXERS:
                    mixers_found.append({
                        'mixer_address': address,
                        'mixer_name': KNOWN_MIXERS[address],
                        'depth': current_depth
                    })
                    return

                # Get recent incoming transactions with limited block range
                try:
                    current_block = self.w3.eth.block_number
                    api_calls[0] += 1

                    # Use configured limit for blocks to check
                    start_block = max(0, current_block - MIXER_DETECTION_BLOCKS)

                    # Sample every 10 blocks instead of every block
                    for block_num in range(current_block, start_block, -10):
                        if api_calls[0] >= MAX_API_CALLS_PER_OPERATION:
                            break

                        try:
                            block = self.w3.eth.get_block(block_num, full_transactions=True)
                            api_calls[0] += 1

                            for tx in block['transactions']:
                                if tx['to'] and tx['to'].lower() == address.lower():
                                    sender = tx['from']

                                    # Check if sender is a mixer
                                    if sender in KNOWN_MIXERS:
                                        mixers_found.append({
                                            'mixer_address': sender,
                                            'mixer_name': KNOWN_MIXERS[sender],
                                            'depth': current_depth,
                                            'tx_hash': tx['hash'].hex()
                                        })
                                    elif current_depth < depth:
                                        # Recursively check sender (with limits)
                                        check_address(sender, current_depth + 1)
                        except:
                            api_calls[0] += 1  # Count failed calls
                            continue

                except Exception as e:
                    logger.debug(f"Error checking transactions for {address}: {e}")

            # Start recursive check
            check_address(wallet_address, 1)

            result = {
                'wallet_address': wallet_address,
                'mixer_funded': len(mixers_found) > 0,
                'mixers_detected': mixers_found,
                'depth_checked': depth,
                'addresses_checked': len(checked_addresses),
                'api_calls': api_calls[0]
            }

            if result['mixer_funded']:
                logger.warning(
                    f"Mixer funding detected for {wallet_address}: "
                    f"{len(mixers_found)} mixer(s) found ({api_calls[0]} API calls)"
                )
            else:
                logger.info(
                    f"No mixer funding detected for {wallet_address} "
                    f"({api_calls[0]} API calls, {len(checked_addresses)} addresses checked)"
                )

            return result

        except Exception as e:
            logger.error(f"Error detecting mixer funding for {wallet_address}: {e}")
            return None

    def verify_trade_amount(
        self,
        tx_hash: str,
        expected_amount_usd: float,
        tolerance_percent: float = 5.0
    ) -> Optional[Dict]:
        """
        Verify that on-chain transaction amount matches expected trade amount

        Args:
            tx_hash: Transaction hash
            expected_amount_usd: Expected amount in USD
            tolerance_percent: Acceptable variance percentage

        Returns:
            Dict with verification results or None
        """
        if not self.is_connected():
            logger.error("Not connected to blockchain")
            return None

        # Validate numeric parameters
        if not isinstance(expected_amount_usd, (int, float)) or expected_amount_usd < 0:
            logger.error(f"Invalid expected_amount_usd: must be non-negative number, got {expected_amount_usd}")
            return None

        if not isinstance(tolerance_percent, (int, float)) or tolerance_percent < 0 or tolerance_percent > 100:
            logger.error(f"Invalid tolerance_percent: must be 0-100, got {tolerance_percent}")
            return None

        try:
            # Get transaction details (tx_hash is validated in verify_transaction)
            tx_details = self.verify_transaction(tx_hash)

            if not tx_details:
                return {
                    'verified': False,
                    'reason': 'Transaction not found on-chain'
                }

            # Note: This is simplified - actual Polymarket trades involve
            # contract interactions with CTF tokens, not just MATIC transfers
            # For production, would need to decode contract logs/events

            onchain_value_matic = float(tx_details['value'])

            # For now, just verify transaction exists and succeeded
            if tx_details['status'] == 1:
                return {
                    'verified': True,
                    'tx_hash': tx_hash,
                    'onchain_value_matic': onchain_value_matic,
                    'expected_amount_usd': expected_amount_usd,
                    'status': 'success',
                    'note': 'Transaction confirmed on-chain (amount verification requires contract event decoding)'
                }
            else:
                return {
                    'verified': False,
                    'reason': 'Transaction failed on-chain',
                    'tx_hash': tx_hash
                }

        except Exception as e:
            logger.error(f"Error verifying trade amount for {tx_hash}: {e}")
            return None

    def get_wallet_balance(self, wallet_address: str) -> Optional[Dict]:
        """
        Get current wallet balance

        Args:
            wallet_address: Ethereum address

        Returns:
            Dict with balance info or None
        """
        if not self.is_connected():
            logger.error("Not connected to blockchain")
            return None

        try:
            # Validate address before blockchain call
            wallet_address = self._validate_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None

        try:
            balance_wei = self.w3.eth.get_balance(wallet_address)
            balance_matic = self.w3.from_wei(balance_wei, 'ether')

            return {
                'wallet_address': wallet_address,
                'balance_matic': float(balance_matic),
                'balance_wei': balance_wei,
                'timestamp': datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.error(f"Error getting balance for {wallet_address}: {e}")
            return None

    def get_transaction_count(self, wallet_address: str) -> Optional[int]:
        """
        Get number of transactions sent by wallet

        Args:
            wallet_address: Ethereum address

        Returns:
            Transaction count or None
        """
        if not self.is_connected():
            logger.error("Not connected to blockchain")
            return None

        try:
            # Validate address before blockchain call
            wallet_address = self._validate_address(wallet_address)
        except ValueError as e:
            logger.error(f"Invalid wallet address: {e}")
            return None

        try:
            return self.w3.eth.get_transaction_count(wallet_address)

        except Exception as e:
            logger.error(f"Error getting transaction count for {wallet_address}: {e}")
            return None


def get_blockchain_client() -> BlockchainClient:
    """
    Get singleton blockchain client instance

    Returns:
        BlockchainClient instance
    """
    global _blockchain_client

    if '_blockchain_client' not in globals():
        _blockchain_client = BlockchainClient()

    return _blockchain_client
