"""
Demo script showing rate limiting and circuit breaker in action

Run this script to see how the protection mechanisms work.
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import time
import logging
from blockchain.rate_limiter import RateLimiter, CircuitBreaker, RetryWithBackoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_rate_limiter():
    """Demonstrate rate limiter in action"""
    print("\n" + "="*70)
    print("DEMO 1: Rate Limiter")
    print("="*70)
    print("Creating rate limiter: 5 calls/second, burst size 3\n")

    limiter = RateLimiter(calls_per_second=5.0, burst_size=3)

    print("Making 10 rapid API calls...\n")
    start = time.time()

    for i in range(10):
        call_start = time.time()
        limiter.acquire()
        elapsed = time.time() - call_start

        if elapsed > 0.05:
            print(f"  Call {i+1:2d}: WAITED {elapsed:.3f}s (rate limited)")
        else:
            print(f"  Call {i+1:2d}: immediate (burst)")

    total_time = time.time() - start
    print(f"\nTotal time: {total_time:.2f}s")

    # Show statistics
    stats = limiter.get_stats()
    print(f"\nStatistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Total waits: {stats['total_waits']}")
    print(f"  Avg wait time: {stats['avg_wait_time']:.3f}s")


def demo_circuit_breaker():
    """Demonstrate circuit breaker states"""
    print("\n" + "="*70)
    print("DEMO 2: Circuit Breaker")
    print("="*70)
    print("Creating circuit breaker: 3 failures opens circuit, 1s recovery\n")

    breaker = CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=1.0,
        success_threshold=2
    )

    # Define functions
    call_count = [0]

    def failing_function():
        call_count[0] += 1
        if call_count[0] <= 5:
            raise Exception(f"Simulated RPC failure #{call_count[0]}")
        return "success"

    def success_function():
        return "success"

    # 1. Make successful calls
    print("1. Making successful calls (circuit stays CLOSED):")
    for i in range(3):
        result = breaker.call(success_function)
        print(f"  Call {i+1}: {result} - Circuit: {breaker.get_state().value}")

    # 2. Trigger failures to open circuit
    print("\n2. Triggering failures to OPEN circuit:")
    for i in range(3):
        try:
            breaker.call(failing_function)
        except Exception as e:
            state = breaker.get_state().value
            print(f"  Failure {i+1}: {e} - Circuit: {state}")

    # 3. Circuit is now open
    print("\n3. Circuit is OPEN - calls fail fast:")
    for i in range(2):
        try:
            breaker.call(failing_function)
        except Exception as e:
            print(f"  Call {i+1}: {type(e).__name__} - {e}")

    # 4. Wait for recovery
    print("\n4. Waiting for recovery timeout (1s)...")
    time.sleep(1.1)

    # 5. Recovery attempt
    print("\n5. Recovery attempt (HALF_OPEN state):")
    result = breaker.call(success_function)
    print(f"  Success: {result} - Circuit: {breaker.get_state().value}")

    result = breaker.call(success_function)
    print(f"  Success: {result} - Circuit: {breaker.get_state().value} (CLOSED!)")

    # Show statistics
    stats = breaker.get_stats()
    print(f"\nStatistics:")
    print(f"  Total calls: {stats['total_calls']}")
    print(f"  Successes: {stats['total_successes']}")
    print(f"  Failures: {stats['total_failures']}")
    print(f"  Times opened: {stats['times_opened']}")


def demo_retry_backoff():
    """Demonstrate exponential backoff"""
    print("\n" + "="*70)
    print("DEMO 3: Retry with Exponential Backoff")
    print("="*70)
    print("Creating retry handler: max 3 retries, 0.5s base delay\n")

    retry = RetryWithBackoff(max_retries=3, base_delay=0.5)

    # Function that fails twice then succeeds
    attempt_count = [0]

    def eventually_succeeds():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            print(f"  Attempt {attempt_count[0]}: FAILED (will retry)")
            raise Exception("Temporary failure")
        print(f"  Attempt {attempt_count[0]}: SUCCESS")
        return "finally worked!"

    print("Calling function that fails twice then succeeds:\n")
    start = time.time()

    result = retry.execute(eventually_succeeds)

    total_time = time.time() - start
    print(f"\nResult: {result}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Retries used: {attempt_count[0] - 1}")
    print("\nNote: Delays were ~0.5s, ~1.0s (exponential backoff)")


def demo_combined():
    """Demonstrate all protections working together"""
    print("\n" + "="*70)
    print("DEMO 4: Combined Protection (Real-world Simulation)")
    print("="*70)
    print("Simulating blockchain RPC calls with all protections\n")

    # Create protection layers
    limiter = RateLimiter(calls_per_second=5.0, burst_size=3)
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=2.0)
    retry = RetryWithBackoff(max_retries=2, base_delay=0.3)

    # Simulate RPC calls
    call_num = [0]

    def simulated_rpc_call():
        call_num[0] += 1

        # Simulate occasional failures
        if call_num[0] in [5, 6]:  # Failures on calls 5 and 6
            raise Exception("RPC timeout")

        return f"Block #{call_num[0] * 1000}"

    def protected_call():
        """Full protection stack"""
        # 1. Rate limiting
        limiter.acquire()

        # 2. Circuit breaker + retry
        def retry_wrapper():
            return breaker.call(simulated_rpc_call)

        return retry.execute(retry_wrapper)

    print("Making 8 protected RPC calls:\n")
    start = time.time()

    for i in range(8):
        try:
            result = protected_call()
            state = breaker.get_state().value
            print(f"  Call {i+1}: {result} - Circuit: {state}")
        except Exception as e:
            state = breaker.get_state().value
            print(f"  Call {i+1}: FAILED - {e} - Circuit: {state}")

        # Small delay for readability
        time.sleep(0.1)

    total_time = time.time() - start

    print(f"\nTotal time: {total_time:.2f}s")
    print(f"\nProtection Statistics:")
    print(f"  Rate Limiter: {limiter.get_stats()['total_calls']} calls, "
          f"{limiter.get_stats()['total_waits']} waits")
    print(f"  Circuit Breaker: {breaker.get_stats()['total_failures']} failures, "
          f"{breaker.get_stats()['times_opened']} times opened")


def main():
    """Run all demos"""
    print("\n")
    print("=" * 70)
    print("    RPC PROTECTION MECHANISMS DEMO")
    print("=" * 70)

    try:
        demo_rate_limiter()
        time.sleep(1)

        demo_circuit_breaker()
        time.sleep(1)

        demo_retry_backoff()
        time.sleep(1)

        demo_combined()

        print("\n" + "="*70)
        print("DEMO COMPLETE")
        print("="*70)
        print("\nThese protections are automatically applied to all blockchain")
        print("RPC calls in the InsiderTradingDetection system!")
        print()

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
