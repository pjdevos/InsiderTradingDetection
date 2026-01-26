# RPC Rate Limiting and Circuit Breaker Implementation

## Overview

This document describes the rate limiting and circuit breaker protection implemented for blockchain RPC calls in the Insider Trading Detection System.

## Problem Statement

The previous implementation had unprotected blockchain RPC calls that could:
- Exhaust API quotas on public RPC endpoints
- Get IP addresses banned due to rate limiting violations
- Make up to 302,000 blocks worth of API calls during wallet age scanning
- Cause cascading failures when RPC endpoints become unavailable
- Fail blockchain verification operations

## Solution

We implemented a three-layer protection system:

1. **Rate Limiter**: Token bucket algorithm to limit requests per second
2. **Circuit Breaker**: Fail-fast pattern to prevent cascading failures
3. **Retry Handler**: Exponential backoff for transient failures

## Architecture

### Rate Limiter (`src/blockchain/rate_limiter.py`)

The `RateLimiter` class implements a token bucket algorithm:

```python
limiter = RateLimiter(
    calls_per_second=10.0,  # Max sustained rate
    burst_size=20           # Allow burst of 20 calls
)

limiter.acquire()  # Blocks until token available
```

**Features:**
- Thread-safe implementation using locks
- Configurable burst capacity for handling spikes
- Statistics tracking (total calls, waits, wait time)
- Timeout support to prevent indefinite blocking

**Default Configuration:**
- Public RPCs: 10 requests/second (default)
- Burst size: 20 requests (allows initial burst)
- Configurable via environment variables

### Circuit Breaker (`src/blockchain/rate_limiter.py`)

The `CircuitBreaker` class implements the circuit breaker pattern:

```python
breaker = CircuitBreaker(
    failure_threshold=5,      # Open after 5 failures
    recovery_timeout=60.0,    # Wait 60s before retry
    success_threshold=2       # Need 2 successes to close
)

result = breaker.call(risky_function)
```

**States:**
- **CLOSED**: Normal operation, all requests allowed
- **OPEN**: Too many failures, reject all requests immediately
- **HALF_OPEN**: Testing recovery, allow limited requests

**Default Configuration:**
- Failure threshold: 5 consecutive failures
- Recovery timeout: 60 seconds
- Success threshold: 2 consecutive successes

### Retry Handler (`src/blockchain/rate_limiter.py`)

The `RetryWithBackoff` class implements exponential backoff:

```python
retry = RetryWithBackoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0
)

result = retry.execute(function_that_might_fail)
```

**Features:**
- Exponential backoff: delays of 1s, 2s, 4s, 8s, etc.
- Maximum delay cap to prevent excessive waits
- Configurable retry attempts

## Integration with BlockchainClient

All RPC calls are protected using the `_protected_rpc_call()` wrapper:

```python
# Before (unprotected)
balance = self.w3.eth.get_balance(address)

# After (protected)
balance = self._protected_rpc_call(self.w3.eth.get_balance, address)
```

### Protected Methods

All blockchain RPC methods are now rate-limited:

- `verify_transaction()` - 3 RPC calls per transaction
- `get_wallet_age()` - Up to 20 RPC calls (limited by MAX_API_CALLS_PER_OPERATION)
- `detect_mixer_funding()` - Up to 20 RPC calls (limited)
- `get_wallet_balance()` - 1 RPC call
- `get_transaction_count()` - 1 RPC call
- `get_market_resolution()` - 2 RPC calls

### Statistics and Monitoring

Get protection statistics at runtime:

```python
client = BlockchainClient()
stats = client.get_protection_stats()

print(stats['rate_limiter'])
# {
#   'total_calls': 150,
#   'total_waits': 30,
#   'avg_wait_time': 0.15,
#   'calls_per_second': 10.0,
#   'current_tokens': 8.5
# }

print(stats['circuit_breaker'])
# {
#   'state': 'closed',
#   'total_failures': 2,
#   'total_successes': 148,
#   'times_opened': 0
# }
```

## Configuration

Configuration is managed via `config.py` and environment variables:

```python
# config.py
RPC_RATE_LIMIT_CALLS_PER_SECOND = float(os.getenv('RPC_RATE_LIMIT_CALLS_PER_SECOND', '10.0'))
RPC_RATE_LIMIT_BURST_SIZE = int(os.getenv('RPC_RATE_LIMIT_BURST_SIZE', '20'))

RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv('RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD', '5'))
RPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT = float(os.getenv('RPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT', '60.0'))
RPC_CIRCUIT_BREAKER_SUCCESS_THRESHOLD = int(os.getenv('RPC_CIRCUIT_BREAKER_SUCCESS_THRESHOLD', '2'))

RPC_MAX_RETRIES = int(os.getenv('RPC_MAX_RETRIES', '3'))
RPC_RETRY_BASE_DELAY = float(os.getenv('RPC_RETRY_BASE_DELAY', '1.0'))
RPC_RETRY_MAX_DELAY = float(os.getenv('RPC_RETRY_MAX_DELAY', '30.0'))
```

### Environment Variables

Add to `.env` file to customize:

```bash
# Rate Limiting
RPC_RATE_LIMIT_CALLS_PER_SECOND=20.0    # For premium RPCs
RPC_RATE_LIMIT_BURST_SIZE=30             # Allow larger bursts

# Circuit Breaker
RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10  # More tolerant
RPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30.0 # Faster recovery

# Retry
RPC_MAX_RETRIES=5                        # More retries
RPC_RETRY_BASE_DELAY=0.5                 # Faster initial retry
```

## Error Handling

### Circuit Breaker Open

When the circuit breaker opens, methods return `None` instead of raising:

```python
balance = client.get_wallet_balance(address)
if balance is None:
    # Circuit breaker is open or RPC is down
    logger.error("Cannot get balance - RPC unavailable")
```

### Rate Limit Timeout

If rate limiting would block too long, `RateLimitExceededError` is raised:

```python
try:
    limiter.acquire(timeout=5.0)  # Max 5 second wait
except RateLimitExceededError:
    logger.warning("Rate limit timeout - request skipped")
```

## Logging

The system logs important events:

```
INFO: Rate limiter initialized: 10.0 calls/sec, burst=20
INFO: Circuit breaker initialized: failure_threshold=5, recovery_timeout=60.0s

WARNING: Rate limit: waiting 2.5s (10.0 calls/sec limit)
WARNING: Circuit breaker: call failed (3/5) - Connection timeout

ERROR: Circuit breaker: closed -> open (5 consecutive failures)
WARNING: Circuit breaker: open -> half_open (recovery timeout elapsed)
INFO: Circuit breaker: half_open -> closed (2 consecutive successes)
```

## Testing

Comprehensive test suite included:

```bash
# Run rate limiter tests
pytest tests/test_rate_limiter.py -v

# Run blockchain integration tests
pytest tests/test_blockchain_integration.py -v

# Run all tests
pytest tests/test_rate_limiter.py tests/test_blockchain_integration.py -v
```

**Test Coverage:**
- Rate limiter: 6 tests (basic, enforcement, burst, timeout, stats, reset)
- Circuit breaker: 6 tests (states, failures, recovery, half-open, stats, reset)
- Retry handler: 4 tests (success, eventual success, all fail, backoff timing)
- Integration: 7 tests (initialization, protection, error handling)

**Total: 24 tests, all passing**

## Performance Impact

### Before Rate Limiting

- Wallet age scan: Could make 302k block checks in rapid succession
- No delay between calls: Limited only by network latency
- Risk: IP ban, quota exhaustion, cascade failures

### After Rate Limiting

- Maximum 10 calls/second (configurable)
- Burst capacity: 20 calls immediate, then rate limited
- Wallet age scan: Still limited to 20 API calls total
- Circuit breaker: Fails fast after 5 consecutive errors
- Automatic backoff: 1s, 2s, 4s retry delays

### Example Timeline

```
T+0.0s:  Calls 1-20   [BURST - immediate]
T+1.0s:  Call 21      [RATE LIMITED - 0.1s per call]
T+1.1s:  Call 22
T+1.2s:  Call 23
...
T+3.9s:  Call 40      [20 burst + 20 rate limited]
```

## Best Practices

### 1. Use Premium RPC for Production

```bash
# .env
POLYGON_RPC_URL=https://polygon-mainnet.infura.io/v3/YOUR_KEY
RPC_RATE_LIMIT_CALLS_PER_SECOND=50.0  # Premium tier allows more
```

### 2. Monitor Protection Statistics

```python
# Periodic monitoring
stats = client.get_protection_stats()
if stats['circuit_breaker']['state'] == 'open':
    alert_operations_team("RPC circuit breaker is open!")
```

### 3. Adjust Limits Based on RPC Tier

| RPC Tier | Calls/Second | Burst Size | Notes |
|----------|--------------|------------|-------|
| Public | 10 | 20 | Default, conservative |
| Premium | 50-100 | 50 | Paid tiers allow more |
| Enterprise | 200+ | 100 | Dedicated infrastructure |

### 4. Handle Circuit Breaker Gracefully

```python
# Don't just retry - handle degraded state
balance = client.get_wallet_balance(address)
if balance is None:
    # Use cached data or skip non-critical operations
    return use_cached_balance(address)
```

## Migration Guide

No code changes required for existing code! The protection is applied automatically to all RPC calls through the `BlockchainClient`.

### Before
```python
client = BlockchainClient()
balance = client.get_wallet_balance(address)
```

### After
```python
client = BlockchainClient()
balance = client.get_wallet_balance(address)  # Now rate-limited!
```

The only difference is in the configuration and monitoring.

## Troubleshooting

### Issue: Rate limiting too strict

**Solution:** Increase rate limit in `.env`:
```bash
RPC_RATE_LIMIT_CALLS_PER_SECOND=20.0
```

### Issue: Circuit breaker opens too quickly

**Solution:** Increase failure threshold:
```bash
RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10
```

### Issue: Long wait times during rate limiting

**Solution:** Either:
1. Reduce operation scope (fewer blocks to scan)
2. Use premium RPC with higher limits
3. Increase burst size for better burst handling

### Issue: Operations failing with CircuitBreakerOpenError

**Diagnosis:** Check logs for underlying RPC failures
**Solution:**
1. Fix RPC connectivity issues
2. Wait for recovery timeout (60s default)
3. Manually reset: `client.circuit_breaker.reset()`

## Future Enhancements

Potential improvements:

1. **Adaptive Rate Limiting**: Adjust rate based on RPC response times
2. **Multiple RPC Endpoints**: Failover to backup endpoints
3. **Request Prioritization**: Priority queue for critical operations
4. **Metrics Export**: Prometheus/Grafana integration
5. **Smart Retry**: Detect rate limit errors (429) and backoff accordingly

## References

- Token Bucket Algorithm: https://en.wikipedia.org/wiki/Token_bucket
- Circuit Breaker Pattern: https://martinfowler.com/bliki/CircuitBreaker.html
- Exponential Backoff: https://en.wikipedia.org/wiki/Exponential_backoff
- Polygon RPC Limits: https://docs.polygon.technology/

## Summary

This implementation provides:

✅ **Protection**: Rate limiting prevents API quota exhaustion
✅ **Resilience**: Circuit breaker prevents cascading failures
✅ **Reliability**: Exponential backoff handles transient errors
✅ **Observability**: Statistics tracking and detailed logging
✅ **Configurability**: Easy tuning via environment variables
✅ **Compatibility**: No code changes needed for existing features
✅ **Testing**: Comprehensive test suite (24 tests)

The blockchain client now safely handles public RPC endpoints without risking IP bans or quota exhaustion.
