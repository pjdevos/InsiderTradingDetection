# RPC Rate Limiting - Quick Start Guide

## TL;DR

All blockchain RPC calls are now automatically rate-limited and protected. No code changes needed!

## What Changed?

### Before
```python
# Could make unlimited rapid RPC calls - risky!
client = BlockchainClient()
balance = client.get_wallet_balance(address)
```

### After
```python
# Same code, but now rate-limited automatically!
client = BlockchainClient()
balance = client.get_wallet_balance(address)
```

## Default Protection

- **Rate Limit:** 10 calls/second (safe for public RPCs)
- **Burst:** 20 immediate calls, then rate limited
- **Circuit Breaker:** Opens after 5 failures, recovers after 60s
- **Retry:** Up to 3 retries with exponential backoff

## Quick Config

### For Public RPCs (Default)
No configuration needed! Works out of the box.

### For Premium RPCs (Infura, Alchemy, etc.)
Add to `.env`:
```bash
RPC_RATE_LIMIT_CALLS_PER_SECOND=50.0
RPC_RATE_LIMIT_BURST_SIZE=50
```

### For Development (More Lenient)
```bash
RPC_RATE_LIMIT_CALLS_PER_SECOND=20.0
RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10
```

## Monitor Protection

```python
# Get statistics
client = BlockchainClient()
stats = client.get_protection_stats()

print(f"Total calls: {stats['rate_limiter']['total_calls']}")
print(f"Circuit state: {stats['circuit_breaker']['state']}")
```

## Common Scenarios

### Scenario 1: Normal Operation
Everything works as before, just slower (rate limited to 10/sec).

### Scenario 2: Rate Limit Hit
```
WARNING: Rate limit: waiting 2.5s (10.0 calls/sec limit)
```
**Action:** Normal - system is preventing rate limit violations.

### Scenario 3: Circuit Breaker Opens
```
ERROR: Circuit breaker: closed -> open (5 consecutive failures)
ERROR: Circuit breaker open, cannot get balance
```
**Action:** RPC endpoint is down. Wait 60s for automatic recovery, or fix RPC connectivity.

### Scenario 4: Temporary RPC Failures
```
WARNING: Attempt 1/4 failed: Connection timeout. Retrying in 1.0s...
```
**Action:** Normal - system is retrying automatically with backoff.

## Troubleshooting

### Problem: Operations are slow
**Cause:** Rate limiting (10 calls/sec)
**Solution:**
- Use premium RPC (increase `RPC_RATE_LIMIT_CALLS_PER_SECOND`)
- Reduce operation scope (scan fewer blocks)

### Problem: Circuit breaker keeps opening
**Cause:** RPC endpoint unreliable
**Solution:**
- Check RPC endpoint health
- Switch to more reliable endpoint
- Increase `RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD`

### Problem: Still getting 429 errors
**Cause:** Rate limit set too high for RPC tier
**Solution:** Decrease `RPC_RATE_LIMIT_CALLS_PER_SECOND`

## All Environment Variables

```bash
# Rate Limiting
RPC_RATE_LIMIT_CALLS_PER_SECOND=10.0      # Requests per second
RPC_RATE_LIMIT_BURST_SIZE=20               # Burst capacity

# Circuit Breaker
RPC_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5    # Failures to open
RPC_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60.0  # Seconds before retry
RPC_CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2    # Successes to close

# Retry
RPC_MAX_RETRIES=3                          # Max retries
RPC_RETRY_BASE_DELAY=1.0                   # Initial delay (seconds)
RPC_RETRY_MAX_DELAY=30.0                   # Max delay (seconds)
```

## Testing

```bash
# Run tests
pytest tests/test_rate_limiter.py -v

# Run demo
python examples/demo_rate_limiting.py
```

## More Info

- Full docs: `docs/RPC_RATE_LIMITING.md`
- Demo script: `examples/demo_rate_limiting.py`
- Changes: `RATE_LIMITING_CHANGES.md`

## Quick Reference

| RPC Tier | Calls/Sec | Config |
|----------|-----------|--------|
| Public | 10 | Default |
| Premium | 50-100 | Set `RPC_RATE_LIMIT_CALLS_PER_SECOND=50` |
| Enterprise | 200+ | Set `RPC_RATE_LIMIT_CALLS_PER_SECOND=200` |

## That's It!

Rate limiting is now automatic. Just use the blockchain client as before, and the system will handle all the protection for you!
