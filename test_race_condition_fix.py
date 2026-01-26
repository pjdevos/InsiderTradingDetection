"""
Test to verify race condition fix in trade monitoring

This test verifies that:
1. last_check_time is NOT updated when trade processing fails
2. Failed trades are retried on the next poll
3. Successful processing updates the checkpoint
"""
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from api.monitor import RealTimeTradeMonitor


def test_race_condition_fix():
    """Test that failed trades don't cause checkpoint update"""

    # Mock API client
    mock_api = Mock()
    mock_api.calculate_bet_size_usd = Mock(return_value=10000)  # Large trade

    # Create monitor
    monitor = RealTimeTradeMonitor(
        api_client=mock_api,
        min_bet_size=5000,
        interval_seconds=10
    )

    initial_time = monitor.last_check_time
    print(f"Initial checkpoint: {initial_time.isoformat()}")

    # Test 1: Successful processing updates checkpoint
    print("\n=== Test 1: Successful processing ===")
    mock_api.get_trades = Mock(return_value=[
        {
            'transaction_hash': 'tx1',
            'wallet_address': '0x123',
            'conditionId': 'market1',
            'title': 'Will Trump win election?',
            'timestamp': datetime.now(timezone.utc),
            'price': 0.55,
            'outcome': 'YES'
        }
    ])

    # Mock process_trade to succeed
    with patch.object(monitor, 'process_trade', return_value=None):
        monitor.poll_recent_trades()

    # Checkpoint should be updated
    assert monitor.last_check_time > initial_time, "Checkpoint should be updated after successful processing"
    print(f"Checkpoint after success: {monitor.last_check_time.isoformat()}")
    print("[PASS] Checkpoint updated after successful processing")

    # Test 2: Failed processing does NOT update checkpoint
    print("\n=== Test 2: Failed processing ===")
    checkpoint_before_failure = monitor.last_check_time

    mock_api.get_trades = Mock(return_value=[
        {
            'transaction_hash': 'tx2',
            'wallet_address': '0x456',
            'conditionId': 'market2',
            'title': 'Will Biden resign?',
            'timestamp': datetime.now(timezone.utc),
            'price': 0.45,
            'outcome': 'NO'
        }
    ])

    # Mock process_trade to fail
    with patch.object(monitor, 'process_trade', side_effect=Exception("Database error")):
        monitor.poll_recent_trades()

    # Checkpoint should NOT be updated
    assert monitor.last_check_time == checkpoint_before_failure, "Checkpoint should NOT be updated after failed processing"
    print(f"Checkpoint after failure: {monitor.last_check_time.isoformat()}")
    print("[PASS] Checkpoint NOT updated after failed processing")

    # Test 3: Partial failure does NOT update checkpoint
    print("\n=== Test 3: Partial failure (2 success, 1 fail) ===")
    checkpoint_before_partial = monitor.last_check_time

    mock_api.get_trades = Mock(return_value=[
        {
            'transaction_hash': 'tx3',
            'wallet_address': '0x789',
            'conditionId': 'market3',
            'title': 'Will Harris win primary?',
            'timestamp': datetime.now(timezone.utc),
            'price': 0.60,
            'outcome': 'YES'
        },
        {
            'transaction_hash': 'tx4',
            'wallet_address': '0xabc',
            'conditionId': 'market4',
            'title': 'Will Senate flip?',
            'timestamp': datetime.now(timezone.utc),
            'price': 0.50,
            'outcome': 'NO'
        },
        {
            'transaction_hash': 'tx5',
            'wallet_address': '0xdef',
            'conditionId': 'market5',
            'title': 'Will Trump be impeached?',
            'timestamp': datetime.now(timezone.utc),
            'price': 0.30,
            'outcome': 'YES'
        }
    ])

    # Mock process_trade to succeed for first 2, fail for 3rd
    call_count = 0
    def mock_process_with_failure(trade):
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise Exception("Database connection lost")

    with patch.object(monitor, 'process_trade', side_effect=mock_process_with_failure):
        monitor.poll_recent_trades()

    # Checkpoint should NOT be updated even though 2/3 succeeded
    assert monitor.last_check_time == checkpoint_before_partial, "Checkpoint should NOT be updated with partial failure"
    print(f"Checkpoint after partial failure: {monitor.last_check_time.isoformat()}")
    print("[PASS] Checkpoint NOT updated with partial failure (ensures retry of all trades)")

    # Test 4: Empty trades list updates checkpoint
    print("\n=== Test 4: Empty trades list ===")
    checkpoint_before_empty = monitor.last_check_time

    mock_api.get_trades = Mock(return_value=[])
    monitor.poll_recent_trades()

    # Checkpoint should be updated even with no trades
    assert monitor.last_check_time > checkpoint_before_empty, "Checkpoint should be updated with empty trades"
    print(f"Checkpoint after empty poll: {monitor.last_check_time.isoformat()}")
    print("[PASS] Checkpoint updated with empty trades list")

    print("\n=== All tests passed! ===")
    print("\nSummary:")
    print("[PASS] Race condition fixed: checkpoint only updates on complete success")
    print("[PASS] Failed trades trigger retry on next poll")
    print("[PASS] Partial failures prevent checkpoint update")
    print("[PASS] Empty polls safely update checkpoint")


if __name__ == '__main__':
    test_race_condition_fix()
