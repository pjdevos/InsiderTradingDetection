"""
Integration tests for blockchain client with rate limiting
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from unittest.mock import Mock, patch, MagicMock
from blockchain.client import BlockchainClient
from blockchain.rate_limiter import CircuitBreakerOpenError


class TestBlockchainClientIntegration:
    """Integration tests for blockchain client with rate limiting"""

    @patch('blockchain.client.Web3')
    def test_client_initializes_with_rate_limiting(self, mock_web3):
        """Test blockchain client initializes rate limiter and circuit breaker"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137
        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        # Create client
        client = BlockchainClient()

        # Verify rate limiter and circuit breaker exist
        assert hasattr(client, 'rate_limiter')
        assert hasattr(client, 'circuit_breaker')
        assert hasattr(client, 'retry_handler')

        # Verify rate limiter is configured
        stats = client.rate_limiter.get_stats()
        assert stats['calls_per_second'] == 10.0  # default config

    @patch('blockchain.client.Web3')
    def test_protected_rpc_call_applies_rate_limiting(self, mock_web3):
        """Test that RPC calls are rate limited"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137
        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        client = BlockchainClient()

        # Mock function
        mock_func = Mock(return_value="result")

        # Make protected call
        result = client._protected_rpc_call(mock_func)

        assert result == "result"
        assert mock_func.call_count == 1

        # Verify rate limiter tracked the call
        stats = client.rate_limiter.get_stats()
        assert stats['total_calls'] > 0

    @patch('blockchain.client.Web3')
    def test_circuit_breaker_opens_on_failures(self, mock_web3):
        """Test circuit breaker opens after repeated failures"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137
        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        client = BlockchainClient()

        # Reset circuit breaker to known state
        client.circuit_breaker.reset()

        # Function that always fails
        def failing_func():
            raise Exception("RPC Error")

        # Try multiple times to trip circuit breaker
        threshold = client.circuit_breaker.failure_threshold

        for i in range(threshold):
            with pytest.raises(Exception):
                client._protected_rpc_call(failing_func)

        # Circuit should now be open
        stats = client.circuit_breaker.get_stats()
        assert stats['state'] == 'open'

        # Next call should fail fast with CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            client._protected_rpc_call(failing_func)

    @patch('blockchain.client.Web3')
    def test_get_protection_stats(self, mock_web3):
        """Test getting protection statistics"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137
        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        client = BlockchainClient()

        # Get stats
        stats = client.get_protection_stats()

        assert 'rate_limiter' in stats
        assert 'circuit_breaker' in stats
        assert 'total_calls' in stats['rate_limiter']
        assert 'state' in stats['circuit_breaker']

    @patch('blockchain.client.Web3')
    def test_verify_transaction_uses_rate_limiting(self, mock_web3):
        """Test that verify_transaction uses protected RPC calls"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137

        # Mock transaction data
        mock_tx = {
            'hash': MagicMock(hex=lambda: '0x123'),
            'from': '0xAddress1',
            'to': '0xAddress2',
            'value': 1000000000000000000,
            'gas': 21000,
            'gasPrice': 20000000000,
            'blockNumber': 12345
        }
        mock_receipt = {'status': 1}
        mock_block = {'timestamp': 1640000000}

        mock_instance.eth.get_transaction.return_value = mock_tx
        mock_instance.eth.get_transaction_receipt.return_value = mock_receipt
        mock_instance.eth.get_block.return_value = mock_block
        mock_instance.from_wei.return_value = 1.0

        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        client = BlockchainClient()

        # Reset stats
        before_calls = client.rate_limiter.get_stats()['total_calls']

        # Verify transaction - use valid 66 char tx hash
        result = client.verify_transaction('0x' + '1' * 64)

        # Should have made at least 3 RPC calls (get_transaction, get_receipt, get_block)
        # Plus initialization calls
        after_calls = client.rate_limiter.get_stats()['total_calls']
        assert after_calls > before_calls

    @patch('blockchain.client.Web3')
    def test_get_wallet_balance_uses_rate_limiting(self, mock_web3):
        """Test that get_wallet_balance uses protected RPC calls"""
        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137
        mock_instance.eth.get_balance.return_value = 1000000000000000000
        mock_instance.from_wei.return_value = 1.0
        mock_instance.to_checksum_address = lambda x: x

        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        client = BlockchainClient()

        # Get stats before
        before_calls = client.rate_limiter.get_stats()['total_calls']

        # Get balance - use valid 42 char address
        result = client.get_wallet_balance('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')

        assert result is not None
        assert 'balance_matic' in result

        # Verify rate limiter was used
        after_calls = client.rate_limiter.get_stats()['total_calls']
        assert after_calls > before_calls

    @patch('blockchain.client.Web3')
    def test_circuit_breaker_error_handling(self, mock_web3):
        """Test that circuit breaker errors are handled gracefully"""
        import time

        # Setup mock
        mock_instance = MagicMock()
        mock_instance.is_connected.return_value = True
        mock_instance.eth.chain_id = 137
        mock_instance.to_checksum_address = lambda x: x

        mock_web3.return_value = mock_instance
        mock_web3.HTTPProvider = MagicMock()

        client = BlockchainClient()

        # Force circuit breaker open and update last_failure_time to now
        # to prevent immediate transition to half-open
        client.circuit_breaker.force_open()
        client.circuit_breaker.last_failure_time = time.time()

        # Try to get balance - should return None instead of raising
        result = client.get_wallet_balance('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEbB')
        assert result is None

        # Try to verify transaction - should return None
        result = client.verify_transaction('0x' + '1' * 64)
        assert result is None
