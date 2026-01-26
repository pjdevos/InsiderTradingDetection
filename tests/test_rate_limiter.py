"""
Tests for rate limiter and circuit breaker functionality
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import time
import pytest
from blockchain.rate_limiter import (
    RateLimiter,
    CircuitBreaker,
    RetryWithBackoff,
    CircuitBreakerOpenError,
    RateLimitExceededError,
    CircuitState
)


class TestRateLimiter:
    """Test rate limiter functionality"""

    def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        limiter = RateLimiter(calls_per_second=10.0)

        # First call should be immediate
        start = time.time()
        limiter.acquire()
        elapsed = time.time() - start

        assert elapsed < 0.1, "First call should be immediate"

    def test_rate_limiter_enforces_limit(self):
        """Test that rate limiter enforces the specified rate"""
        # Use burst_size=1 to ensure rate limiting kicks in immediately
        limiter = RateLimiter(calls_per_second=5.0, burst_size=1)  # 5 calls/sec = 0.2s interval

        # Make 3 calls
        start = time.time()
        for _ in range(3):
            limiter.acquire()
        elapsed = time.time() - start

        # Should take at least 2 intervals (calls 2 and 3 each wait)
        expected_min = 2 * 0.2  # 0.4 seconds
        assert elapsed >= expected_min * 0.9, f"Rate limiting not enforced: {elapsed}s < {expected_min}s"

    def test_rate_limiter_burst(self):
        """Test burst capacity"""
        limiter = RateLimiter(calls_per_second=10.0, burst_size=5)

        # Should allow burst of 5 calls immediately
        start = time.time()
        for _ in range(5):
            assert limiter.try_acquire(), "Burst should allow immediate calls"
        elapsed = time.time() - start

        assert elapsed < 0.1, "Burst should be immediate"

        # 6th call should fail
        assert not limiter.try_acquire(), "Burst exceeded should fail"

    def test_rate_limiter_timeout(self):
        """Test timeout behavior"""
        limiter = RateLimiter(calls_per_second=1.0)  # Very slow

        # First call is immediate
        limiter.acquire()

        # Second call would wait 1 second, but timeout after 0.1s
        with pytest.raises(RateLimitExceededError):
            limiter.acquire(timeout=0.1)

    def test_rate_limiter_stats(self):
        """Test statistics tracking"""
        limiter = RateLimiter(calls_per_second=10.0)

        for _ in range(5):
            limiter.acquire()

        stats = limiter.get_stats()
        assert stats['total_calls'] == 5
        assert stats['calls_per_second'] == 10.0
        assert 'total_waits' in stats
        assert 'avg_wait_time' in stats

    def test_rate_limiter_reset(self):
        """Test reset functionality"""
        limiter = RateLimiter(calls_per_second=10.0)

        # Make some calls
        for _ in range(3):
            limiter.acquire()

        limiter.reset()
        stats = limiter.get_stats()

        assert stats['total_calls'] == 0
        assert stats['total_waits'] == 0


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    def test_circuit_breaker_closed_state(self):
        """Test normal operation in closed state"""
        breaker = CircuitBreaker(failure_threshold=3)

        def success_func():
            return "success"

        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit opens after threshold failures"""
        breaker = CircuitBreaker(failure_threshold=3)

        def failing_func():
            raise ValueError("Test error")

        # First 3 failures should go through
        for i in range(3):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Circuit should now be open
        assert breaker.get_state() == CircuitState.OPEN

        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(failing_func)

    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.5,  # 0.5 second recovery
            success_threshold=2
        )

        def failing_func():
            raise ValueError("Test error")

        def success_func():
            return "success"

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.get_state() == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.6)

        # Should transition to half-open on next call
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.get_state() == CircuitState.HALF_OPEN

        # Need another success to close
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.get_state() == CircuitState.CLOSED

    def test_circuit_breaker_half_open_failure(self):
        """Test circuit re-opens if half-open call fails"""
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.3
        )

        def failing_func():
            raise ValueError("Test error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        # Wait for recovery
        time.sleep(0.4)

        # Call should put it in half-open, but fail
        with pytest.raises(ValueError):
            breaker.call(failing_func)

        # Should be back to open
        assert breaker.get_state() == CircuitState.OPEN

    def test_circuit_breaker_stats(self):
        """Test statistics tracking"""
        breaker = CircuitBreaker(failure_threshold=3)

        def success_func():
            return "ok"

        def fail_func():
            raise ValueError("error")

        # Some successes
        for _ in range(5):
            breaker.call(success_func)

        # Some failures
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(fail_func)

        stats = breaker.get_stats()
        assert stats['total_calls'] == 7
        assert stats['total_successes'] == 5
        assert stats['total_failures'] == 2
        assert stats['state'] == CircuitState.CLOSED.value

    def test_circuit_breaker_reset(self):
        """Test manual reset"""
        breaker = CircuitBreaker(failure_threshold=2)

        def failing_func():
            raise ValueError("error")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ValueError):
                breaker.call(failing_func)

        assert breaker.get_state() == CircuitState.OPEN

        # Manual reset
        breaker.reset()
        assert breaker.get_state() == CircuitState.CLOSED


class TestRetryWithBackoff:
    """Test retry with exponential backoff"""

    def test_retry_success_first_attempt(self):
        """Test successful call on first attempt"""
        retry = RetryWithBackoff(max_retries=3)

        def success_func():
            return "success"

        result = retry.execute(success_func)
        assert result == "success"

    def test_retry_eventual_success(self):
        """Test eventual success after retries"""
        retry = RetryWithBackoff(max_retries=3, base_delay=0.1)

        call_count = [0]

        def eventually_succeeds():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not yet")
            return "success"

        result = retry.execute(eventually_succeeds)
        assert result == "success"
        assert call_count[0] == 3

    def test_retry_all_fail(self):
        """Test all retries exhausted"""
        retry = RetryWithBackoff(max_retries=2, base_delay=0.05)

        call_count = [0]

        def always_fails():
            call_count[0] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            retry.execute(always_fails)

        # Should have tried 3 times (initial + 2 retries)
        assert call_count[0] == 3

    def test_retry_exponential_backoff(self):
        """Test exponential backoff timing"""
        retry = RetryWithBackoff(
            max_retries=2,
            base_delay=0.1,
            exponential_base=2.0
        )

        call_times = []

        def failing_func():
            call_times.append(time.time())
            raise ValueError("Fail")

        start = time.time()
        with pytest.raises(ValueError):
            retry.execute(failing_func)

        # Check delays between calls
        # First retry after ~0.1s, second after ~0.2s
        if len(call_times) >= 3:
            delay1 = call_times[1] - call_times[0]
            delay2 = call_times[2] - call_times[1]

            assert 0.08 <= delay1 <= 0.15, f"First delay {delay1} not ~0.1s"
            assert 0.15 <= delay2 <= 0.30, f"Second delay {delay2} not ~0.2s"


class TestIntegration:
    """Integration tests combining rate limiter and circuit breaker"""

    def test_rate_limited_with_circuit_breaker(self):
        """Test rate limiter and circuit breaker working together"""
        limiter = RateLimiter(calls_per_second=10.0)
        breaker = CircuitBreaker(failure_threshold=3)

        def protected_call():
            limiter.acquire()
            return breaker.call(lambda: "success")

        # Should work normally
        for _ in range(5):
            result = protected_call()
            assert result == "success"

        # Check both have statistics
        limiter_stats = limiter.get_stats()
        breaker_stats = breaker.get_stats()

        assert limiter_stats['total_calls'] == 5
        assert breaker_stats['total_successes'] == 5
