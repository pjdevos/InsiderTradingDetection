# Race Condition Fix for Trade Monitoring

## Problem

The trade polling system in `src/api/monitor.py` had a critical race condition where trades could be missed or data integrity could be compromised:

### Original Issue (Lines 84-107)

```python
# Line 84-87: last_check_time updated BEFORE processing completes
self.last_check_time = poll_start_time  # Too early!

# Lines 106-107: Processing happens AFTER timestamp update
for trade in large_trades:
    self.process_trade(trade)  # Could fail, leaving gap
```

### Impact

1. **Missed Trades**: If `process_trade()` failed after updating `last_check_time`, the next poll would skip those trades permanently
2. **Data Loss**: Database errors during trade processing would result in lost alerts for suspicious activity
3. **Silent Failures**: Error handling in `process_trade()` caught and swallowed exceptions without propagating them

## Solution

### Key Changes

#### 1. Checkpoint Update Only After Success (Lines 59-132)

```python
def poll_recent_trades(self):
    poll_start_time = datetime.now(timezone.utc)

    try:
        # Fetch trades
        trades = self.api.get_trades(...)

        # Process ALL trades, tracking success/failure
        processed_count = 0
        failed_count = 0

        for trade in large_trades:
            try:
                self.process_trade(trade)
                processed_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to process trade: {e}", exc_info=True)

        # Only update checkpoint if ALL trades succeeded
        if failed_count == 0:
            self.last_check_time = poll_start_time
            logger.info(f"Successfully processed {processed_count} trades, updating checkpoint")
        else:
            logger.warning(
                f"Processed {processed_count}/{len(large_trades)} trades, but {failed_count} failed. "
                f"Checkpoint NOT updated - failed trades will be retried on next poll."
            )

    except Exception as e:
        logger.error(f"Error in polling loop: {e}", exc_info=True)
```

#### 2. Proper Exception Propagation (Lines 251-268)

**Before:**
```python
try:
    stored_trade = DataStorageService.store_trade(...)
except Exception as e:
    logger.error(f"Failed to store trade: {e}")
    # Continue processing even if storage fails  # WRONG!
```

**After:**
```python
# NOTE: This raises exceptions on storage failures to trigger retry logic
stored_trade = DataStorageService.store_trade(...)

if stored_trade:
    logger.info(f"Stored trade in database: ID={stored_trade.id}")
else:
    # Trade not stored (likely duplicate) - this is OK, don't raise error
    logger.debug("Trade not stored (likely duplicate)")
```

#### 3. Enhanced Logging

Added detailed logging for retry scenarios:
- Success: "Successfully processed N trades, updating checkpoint to [timestamp]"
- Partial failure: "Processed N/M trades successfully, but X failed. Checkpoint NOT updated - failed trades will be retried on next poll."
- Total failure: "Error in polling loop: [error]" (checkpoint not updated)

### How It Works

1. **Overlap Buffer**: 5-second overlap ensures we don't miss trades due to clock skew
2. **Duplicate Handling**: Database unique constraint on `transaction_hash` safely ignores duplicates from overlap
3. **Atomic Checkpoint**: Timestamp only advances when all trades in a batch succeed
4. **Retry Logic**: Failed trades are automatically retried on next poll (with overlap buffer)

### Transaction Guarantees

While the current design processes each trade in a separate database transaction (via `DataStorageService.store_trade()`), the checkpoint logic ensures:

1. **No Lost Trades**: Failed trades trigger retry on next poll
2. **At-Least-Once Semantics**: Trades may be processed multiple times, but duplicates are safely ignored
3. **Eventual Consistency**: All trades will eventually be processed once the underlying issue is resolved

Note: Each trade creates its own session via `get_db_session()` context manager in `storage.py` line 124. This is acceptable because:
- Individual trade failures don't affect other trades
- The unique constraint on `transaction_hash` prevents duplicates
- The checkpoint logic ensures failed trades are retried

## Testing

Run the test suite to verify the fix:

```bash
python test_race_condition_fix.py
```

### Test Coverage

1. **Test 1**: Successful processing updates checkpoint
2. **Test 2**: Failed processing does NOT update checkpoint
3. **Test 3**: Partial failure (2/3 success) does NOT update checkpoint
4. **Test 4**: Empty trades list safely updates checkpoint

All tests pass, confirming the race condition is fixed.

## Migration Notes

No database schema changes required. The fix is purely in application logic.

## Monitoring

Watch for these log messages in production:

- **Success**: `Successfully processed N trades, updating checkpoint to [timestamp]`
- **Retry Required**: `Checkpoint NOT updated - failed trades will be retried on next poll`
- **Duplicate Trades**: `Trade not stored (likely duplicate)` (expected with overlap buffer)

## Performance Considerations

- **No Performance Impact**: The overlap buffer is only 5 seconds, minimal overhead
- **Retry Cost**: Failed batches are retried on next poll (configurable interval)
- **Database Load**: Each trade still creates separate session (no change from original)

## Future Improvements (Optional)

If you need true batch processing with a single transaction:

1. Create a new method in `DataStorageService`:
   ```python
   def store_trades_with_alerts_batch(trades, scoring_results, session):
       # Process all trades in single transaction
       pass
   ```

2. Update `poll_recent_trades()` to use batch method:
   ```python
   with get_db_session() as session:
       DataStorageService.store_trades_with_alerts_batch(trades, ..., session)
   session.commit()  # Atomic commit
   ```

However, this is not necessary for correctness - the current fix ensures data integrity.
