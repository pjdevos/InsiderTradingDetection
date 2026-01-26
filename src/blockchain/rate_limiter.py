"""
Rate limiting and circuit breaker implementation for blockchain RPC calls

Provides protection against API rate limits and cascading failures.
"""
import time
import logging
from threading import Lock
from enum import Enum
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"           # Normal operation, requests allowed
    OPEN = "open"              # Failing state, reject all requests
    HALF_OPEN = "half_open"    # Testing recovery, allow limited requests


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls"""
    pass


class RateLimitExceededError(Exception):
    """Raised when rate limit would be exceeded"""
    pass


class RateLimiter:
    """
    Token bucket rate limiter for RPC calls.

    Implements a token bucket algorithm to limit requests per second.
    Thread-safe implementation using locks.
    """

    def __init__(self, calls_per_second: float = 10.0, burst_size: Optional[int] = None):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum sustained requests per second
            burst_size: Maximum burst of requests (defaults to calls_per_second)
        """
        if calls_per_second <= 0:
            raise ValueError("calls_per_second must be positive")

        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.burst_size = burst_size or int(calls_per_second)

        # Token bucket state
        self.tokens = float(self.burst_size)
        self.max_tokens = float(self.burst_size)
        self.last_update = time.time()

        # Thread safety
        self.lock = Lock()

        # Statistics
        self.total_calls = 0
        self.total_waits = 0
        self.total_wait_time = 0.0

        logger.info(
            f"Rate limiter initialized: {calls_per_second} calls/sec, "
            f"burst={self.burst_size}, interval={self.min_interval:.3f}s"
        )

    def _refill_tokens(self):
        """Refill tokens based on elapsed time (called with lock held)"""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on time elapsed
        new_tokens = elapsed * self.calls_per_second
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_update = now

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to make an RPC call.

        Blocks until a token is available or timeout is reached.

        Args:
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            True if token acquired, False if timeout

        Raises:
            RateLimitExceededError: If timeout is reached
        """
        start_time = time.time()

        with self.lock:
            self._refill_tokens()

            # If tokens available, consume one immediately
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                self.total_calls += 1
                return True

            # Calculate wait time needed
            tokens_needed = 1.0 - self.tokens
            wait_time = tokens_needed / self.calls_per_second

            # Check timeout
            if timeout is not None and wait_time > timeout:
                raise RateLimitExceededError(
                    f"Rate limit would require {wait_time:.2f}s wait (timeout={timeout:.2f}s)"
                )

            # Log if significant wait required
            if wait_time > 1.0:
                logger.warning(
                    f"Rate limit: waiting {wait_time:.2f}s "
                    f"({self.calls_per_second} calls/sec limit)"
                )

            self.total_waits += 1
            self.total_wait_time += wait_time

        # Wait outside of lock to allow other threads
        time.sleep(wait_time)

        # Acquire token after wait
        with self.lock:
            self._refill_tokens()
            self.tokens -= 1.0
            self.total_calls += 1
            return True

    def try_acquire(self) -> bool:
        """
        Try to acquire a token without blocking.

        Returns:
            True if token acquired, False if no tokens available
        """
        with self.lock:
            self._refill_tokens()

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                self.total_calls += 1
                return True

            return False

    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        with self.lock:
            return {
                'total_calls': self.total_calls,
                'total_waits': self.total_waits,
                'total_wait_time': self.total_wait_time,
                'avg_wait_time': self.total_wait_time / max(1, self.total_waits),
                'calls_per_second': self.calls_per_second,
                'current_tokens': self.tokens,
                'max_tokens': self.max_tokens
            }

    def reset(self):
        """Reset rate limiter state"""
        with self.lock:
            self.tokens = self.max_tokens
            self.last_update = time.time()
            self.total_calls = 0
            self.total_waits = 0
            self.total_wait_time = 0.0
            logger.info("Rate limiter reset")


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for RPC resilience.

    Prevents cascading failures by failing fast when error rate is high.
    Automatically attempts recovery after timeout period.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of consecutive failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            success_threshold: Consecutive successes needed to close circuit from half-open
        """
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be positive")
        if success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.last_state_change = time.time()

        # Statistics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.times_opened = 0

        # Thread safety
        self.lock = Lock()

        logger.info(
            f"Circuit breaker initialized: failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s, success_threshold={success_threshold}"
        )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery (called with lock held)"""
        if self.state != CircuitState.OPEN:
            return False

        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    def _transition_to(self, new_state: CircuitState, reason: str = ""):
        """Transition to new state and log (called with lock held)"""
        if new_state == self.state:
            return

        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()

        log_msg = f"Circuit breaker: {old_state.value} -> {new_state.value}"
        if reason:
            log_msg += f" ({reason})"

        if new_state == CircuitState.OPEN:
            self.times_opened += 1
            logger.error(log_msg)
        elif new_state == CircuitState.CLOSED:
            logger.info(log_msg)
        else:
            logger.warning(log_msg)

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from function if call fails
        """
        with self.lock:
            self.total_calls += 1

            # Check if we should attempt recovery
            if self._should_attempt_reset():
                self._transition_to(
                    CircuitState.HALF_OPEN,
                    f"recovery timeout elapsed ({self.recovery_timeout}s)"
                )

            # Reject calls if circuit is open
            if self.state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN (failed {self.failure_count} times, "
                    f"last failure {time.time() - self.last_failure_time:.0f}s ago)"
                )

            # Track state for recovery logic
            current_state = self.state

        # Execute function outside of lock
        try:
            result = func(*args, **kwargs)
            self._on_success(current_state)
            return result

        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self, state_at_call: CircuitState):
        """Handle successful call"""
        with self.lock:
            self.total_successes += 1
            self.failure_count = 0

            if state_at_call == CircuitState.HALF_OPEN:
                self.success_count += 1

                if self.success_count >= self.success_threshold:
                    self._transition_to(
                        CircuitState.CLOSED,
                        f"{self.success_threshold} consecutive successes"
                    )
                    self.success_count = 0

    def _on_failure(self, error: Exception):
        """Handle failed call"""
        with self.lock:
            self.total_failures += 1
            self.failure_count += 1
            self.success_count = 0
            self.last_failure_time = time.time()

            # Log the error
            logger.warning(
                f"Circuit breaker: call failed ({self.failure_count}/{self.failure_threshold}) - {error}"
            )

            # Open circuit if threshold reached
            if self.state == CircuitState.HALF_OPEN:
                # Fail immediately in half-open state
                self._transition_to(
                    CircuitState.OPEN,
                    "failure during recovery attempt"
                )
            elif self.failure_count >= self.failure_threshold:
                self._transition_to(
                    CircuitState.OPEN,
                    f"{self.failure_count} consecutive failures"
                )

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state"""
        with self.lock:
            return self.state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics"""
        with self.lock:
            return {
                'state': self.state.value,
                'total_calls': self.total_calls,
                'total_successes': self.total_successes,
                'total_failures': self.total_failures,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'times_opened': self.times_opened,
                'last_failure_time': self.last_failure_time,
                'last_state_change': self.last_state_change,
                'time_in_current_state': time.time() - self.last_state_change
            }

    def reset(self):
        """Reset circuit breaker to closed state"""
        with self.lock:
            old_state = self.state
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_state_change = time.time()
            logger.info(f"Circuit breaker manually reset from {old_state.value}")

    def force_open(self):
        """Manually open circuit breaker"""
        with self.lock:
            self._transition_to(CircuitState.OPEN, "manual override")


def rate_limited(rate_limiter: RateLimiter):
    """
    Decorator to apply rate limiting to a function.

    Args:
        rate_limiter: RateLimiter instance to use

    Example:
        @rate_limited(my_limiter)
        def make_api_call():
            return requests.get("...")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            rate_limiter.acquire()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def circuit_protected(circuit_breaker: CircuitBreaker):
    """
    Decorator to apply circuit breaker protection to a function.

    Args:
        circuit_breaker: CircuitBreaker instance to use

    Example:
        @circuit_protected(my_breaker)
        def make_api_call():
            return requests.get("...")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


class RetryWithBackoff:
    """
    Exponential backoff retry logic for transient failures.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with exponential backoff retry.

        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    # Calculate delay with exponential backoff
                    delay = min(
                        self.base_delay * (self.exponential_base ** attempt),
                        self.max_delay
                    )

                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_retries + 1} attempts failed. "
                        f"Last error: {e}"
                    )

        raise last_exception
