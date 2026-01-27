# Critical Security Fixes - January 26, 2026

**Status:** All 5 Critical Issues Fixed
**Tests:** 63/64 Passing (1 pre-existing failure unrelated to fixes)

---

## Summary

All 5 critical security vulnerabilities identified in the code review have been fixed:

1. SQL Injection Vulnerability Risk - Database validation layer added
2. Credential Exposure in Logs - Credential masking implemented
3. Missing Input Validation - API client validation enhanced
4. Race Condition in Trade Monitoring - Persistent checkpoints added
5. Unsafe Error Handling - SMTP error sanitization implemented

---

## Fix 1: SQL Injection Vulnerability Risk

**Files Modified:**
- `src/database/validators.py` (NEW)
- `src/database/repository.py`

**Changes:**
- Created comprehensive `DatabaseInputValidator` class with validation for:
  - Wallet addresses (format, length, hex validation)
  - Transaction hashes (format, length)
  - Market IDs (format, length, character validation)
  - Limits and hours (range validation)
  - Scores (0-100 range)
  - Timestamps (reasonable range)
  - Alert levels and statuses (enum validation)
  - Order by fields (whitelist validation)
  - Bet sizes (positive, reasonable max)
  - Generic strings (length limits)

- Updated all repository methods to validate inputs before queries:
  - `TradeRepository`: 7 methods updated
  - `MarketRepository`: 3 methods updated
  - `WalletRepository`: 4 methods updated
  - `AlertRepository`: 6 methods updated

**Example:**
```python
# Before
def get_trade_by_tx_hash(session: Session, tx_hash: str) -> Optional[Trade]:
    return session.query(Trade).filter(Trade.transaction_hash == tx_hash).first()

# After
def get_trade_by_tx_hash(session: Session, tx_hash: str) -> Optional[Trade]:
    tx_hash = DatabaseInputValidator.validate_transaction_hash(tx_hash)
    return session.query(Trade).filter(Trade.transaction_hash == tx_hash).first()
```

---

## Fix 2: Credential Exposure in Logs

**Files Modified:**
- `src/config.py`

**Changes:**
- Added `SecureString` class that:
  - Automatically masks values in `__str__` and `__repr__`
  - Detects placeholder patterns (e.g., "your_api_key_here")
  - Provides `masked()` method showing only last 4 characters

- Added `CredentialMaskingFilter` for logging:
  - Filters log messages for credential patterns
  - Masks API keys, Bearer tokens, passwords in URLs
  - Masks bot tokens and generic secrets

- Added `sanitize_error_message()` utility function

- Added `Config.__repr__()` method that masks sensitive fields:
  - `POLYMARKET_API_KEY`
  - `DATABASE_URL`
  - `POLYGON_RPC_URL`
  - `TELEGRAM_BOT_TOKEN`
  - `SMTP_PASSWORD`
  - `SMTP_USERNAME`

- Added `Config.get_safe_database_url()` method for logging

- Added `install_credential_masking()` function for global filter installation

**Example Output:**
```
Config(
  DATABASE_URL=*********************************************************************lway
  SMTP_PASSWORD=********************al34
  TELEGRAM_BOT_TOKEN=******************************************R_u8
)
```

---

## Fix 3: Comprehensive Input Validation in API Client

**Files Modified:**
- `src/api/client.py`

**Changes:**
- Added validation constants:
  - `MIN_VALID_TIMESTAMP` - 2020-01-01 (Polymarket didn't exist before)
  - `MAX_FUTURE_DAYS` - 365 days
  - `MAX_STRING_LENGTH` - 1000 characters
  - `MAX_MARKET_ID_LENGTH` - 100 characters

- Enhanced `_validate_market_id()`:
  - Added length validation
  - Added character validation (alphanumeric, underscore, hyphen)
  - Added hex format support for condition IDs

- Added `_validate_timestamp()`:
  - Ensures timezone-aware (adds UTC if naive)
  - Validates not before Polymarket existed
  - Validates not too far in future

- Added `_validate_optional_timestamp()`

- Added `_validate_string()` with max length validation

- Updated `get_trades()`:
  - Added timestamp validation for `start_time` and `end_time`
  - Added validation that `start_time` is before `end_time`

- Updated `get_order_fills()`:
  - Added limit validation
  - Added market validation

- Updated `get_markets()`:
  - Added tag validation with length limit

---

## Fix 4: Persistent Checkpoint Mechanism

**Files Modified:**
- `src/database/models.py`
- `src/database/repository.py`
- `src/api/monitor.py`

**New Database Models:**

### `MonitorCheckpoint`
```python
class MonitorCheckpoint(Base):
    __tablename__ = 'monitor_checkpoints'

    monitor_name = Column(String(100), primary_key=True)
    last_checkpoint_time = Column(DateTime(timezone=True), nullable=False)
    total_trades_processed = Column(Integer, default=0)
    total_failures = Column(Integer, default=0)
    last_failure_time = Column(DateTime(timezone=True))
    last_failure_reason = Column(Text)
```

### `FailedTrade` (Dead-Letter Queue)
```python
class FailedTrade(Base):
    __tablename__ = 'failed_trades'

    id = Column(Integer, primary_key=True)
    transaction_hash = Column(String(66), nullable=False)
    trade_data = Column(JSON, nullable=False)
    failure_reason = Column(Text, nullable=False)
    failure_count = Column(Integer, default=1)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=5)
    next_retry_at = Column(DateTime(timezone=True))
    status = Column(String(20), default='PENDING')  # PENDING, RETRYING, RESOLVED, ABANDONED
```

**New Repository Classes:**

### `CheckpointRepository`
- `get_checkpoint()` - Load checkpoint from database
- `save_checkpoint()` - Save checkpoint after successful processing
- `record_failure()` - Record failure without updating checkpoint

### `FailedTradeRepository`
- `add_failed_trade()` - Add to dead-letter queue
- `get_pending_retries()` - Get trades ready for retry
- `mark_resolved()` - Mark trade as successfully processed
- `increment_retry()` - Increment retry count with exponential backoff

**Monitor Updates:**
- Added `monitor_name` parameter for multi-monitor support
- Added `_load_checkpoint()` - Load from database on startup
- Added `_save_checkpoint()` - Save to database after successful batch
- Added `_record_failure()` - Record failures in database
- Added `_add_to_dead_letter_queue()` - Queue failed trades for retry
- Added `process_dead_letter_queue()` - Process queued trades with backoff

**Benefits:**
- Checkpoints survive restarts
- Failed trades are queued for retry
- Exponential backoff (5, 10, 20, 40, 80 minutes)
- Abandoned after 5 retries
- Multiple monitors can run independently

---

## Fix 5: Sanitized Error Handling in Email Alerts

**Files Modified:**
- `src/alerts/email_alerts.py`

**Changes:**

Added `_sanitize_smtp_error()` function:
- Removes password-like content
- Removes Base64 encoded strings
- Removes Python bytes literals
- Truncates long messages

Added specific exception handling for:
- `SMTPAuthenticationError` - Masks credentials in error
- `SMTPRecipientsRefused` - Lists refused addresses only
- `SMTPSenderRefused` - Shows sender and error code only
- `SMTPDataError` - Shows error code only
- `SMTPConnectError` - Shows server/port only
- `SMTPServerDisconnected` - Shows server only
- `SSLError` - Generic SSL message
- `socket.timeout` - Generic timeout message
- `socket.gaierror` - DNS resolution error
- `ConnectionRefusedError` - Connection refused message

**Example - Before:**
```python
except smtplib.SMTPAuthenticationError as e:
    logger.error(f"SMTP authentication failed: {e}")  # May contain password!
```

**Example - After:**
```python
except smtplib.SMTPAuthenticationError as e:
    sanitized_error = _sanitize_smtp_error(e)
    logger.error(
        f"SMTP authentication failed. Check SMTP_USERNAME and SMTP_PASSWORD. "
        f"Server: {self.smtp_server}. Error: {sanitized_error}"
    )
```

Updated methods:
- `send_alert()` - 12 specific exception handlers
- `send_test_email()` - Sanitized error handling
- `send_daily_summary()` - Sanitized error handling

---

## Test Results

```
63 passed, 1 failed (pre-existing), 1 warning
```

The failing test (`test_geopolitical_keywords_configured`) is pre-existing and unrelated to these fixes - it expects 'government' in the keywords list which was never added.

---

## Files Created/Modified

### New Files:
- `src/database/validators.py` - Input validation for database layer

### Modified Files:
- `src/config.py` - Credential masking, SecureString class
- `src/database/models.py` - MonitorCheckpoint, FailedTrade models
- `src/database/repository.py` - Input validation + checkpoint/failed trade repos
- `src/api/client.py` - Enhanced input validation
- `src/api/monitor.py` - Persistent checkpoints, dead-letter queue
- `src/alerts/email_alerts.py` - Sanitized error handling

---

## Migration Required

Run database migration to create new tables:

```sql
-- Monitor Checkpoints Table
CREATE TABLE monitor_checkpoints (
    monitor_name VARCHAR(100) PRIMARY KEY,
    last_checkpoint_time TIMESTAMP WITH TIME ZONE NOT NULL,
    total_trades_processed INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0,
    last_failure_time TIMESTAMP WITH TIME ZONE,
    last_failure_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Failed Trades Table (Dead-Letter Queue)
CREATE TABLE failed_trades (
    id SERIAL PRIMARY KEY,
    transaction_hash VARCHAR(66) NOT NULL,
    trade_data JSONB NOT NULL,
    failure_reason TEXT NOT NULL,
    failure_count INTEGER DEFAULT 1,
    first_failure_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_failure_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'PENDING',
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

CREATE INDEX idx_failed_trades_status ON failed_trades(status);
CREATE INDEX idx_failed_trades_next_retry ON failed_trades(next_retry_at);
CREATE INDEX idx_failed_trades_tx_hash ON failed_trades(transaction_hash);
```

---

---

## Database Critical Fixes (January 27, 2026)

4 critical database issues identified in the database-focused code review have been fixed.

### Fix 6: Missing CHECK Constraint and Index for `trade_result`

**File Modified:** `alembic/versions/add_suspicious_wins_tables.py`

**Changes:**
- Added `op.create_check_constraint('check_trade_result', 'trades', ...)` to enforce valid `trade_result` values (`WIN`, `LOSS`, `PENDING`, `VOID`, or `NULL`)
- Added `op.create_index('idx_trades_resolution_id', 'trades', ['resolution_id'])` for foreign key join performance
- Updated `downgrade()` to drop the constraint and index

**Impact:** Prevents invalid trade results from being stored. Improves JOIN performance on `resolution_id`.

---

### Fix 7: Missing Alembic Migration for MonitorCheckpoint and FailedTrade

**File Created:** `alembic/versions/add_monitor_checkpoint_tables.py`

**Changes:**
- New migration (revision `add_monitor_tables`, depends on `add_suspicious_wins`)
- Creates `monitor_checkpoints` table with all columns matching the model
- Creates `failed_trades` table (dead-letter queue) with all columns matching the model
- Creates indexes: `idx_failed_trades_status`, `idx_failed_trades_next_retry`, `idx_failed_trades_tx_hash`
- Proper `downgrade()` to drop tables and indexes

**Impact:** These tables are now managed by Alembic instead of relying on `Base.metadata.create_all()`, preventing schema drift between environments.

---

### Fix 8: Duplicate Pool Event Listener Registration

**File Modified:** `src/database/connection.py`

**Changes:**
- Added module-level `_pool_listeners_registered` flag
- Changed guard from `if attempt == 0` to `if not _pool_listeners_registered`
- Flag set to `True` before registering listeners, preventing re-registration across multiple `init_db()` calls

**Before:**
```python
if attempt == 0:  # Only guards within single init_db() call
    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn, connection_record): ...
```

**After:**
```python
global _pool_listeners_registered
if not _pool_listeners_registered:
    _pool_listeners_registered = True
    @event.listens_for(Pool, "connect")
    def receive_connect(dbapi_conn, connection_record): ...
```

**Impact:** Prevents duplicate log entries, memory leaks, and performance degradation from multiple listener registrations.

---

### Fix 9: Race Condition and Hardcoded Revision in Alembic Auto-Stamping

**File Modified:** `alembic/env.py`

**Changes:**
- Removed hardcoded `LATEST_REVISION = 'add_suspicious_wins'` constant
- Added `_get_head_revision()` helper that reads the head revision from `ScriptDirectory` dynamically
- Replaced string interpolation in SQL with parameterized query (`text(...), {"rev": head_revision}`)
- Added `ON CONFLICT (version_num) DO NOTHING` for atomicity (handles race if another process creates the row)
- Single `conn.commit()` after both CREATE TABLE and INSERT for transactional consistency
- Added `ScriptDirectory` import from `alembic.script`

**Before:**
```python
LATEST_REVISION = 'add_suspicious_wins'  # Must manually update!
# ...
conn.execute(text(f"INSERT INTO alembic_version (version_num) VALUES ('{LATEST_REVISION}')"))
conn.commit()  # Separate commits = race condition
```

**After:**
```python
head_revision = _get_head_revision()  # Auto-detected from migration scripts
# ...
conn.execute(
    text("INSERT INTO alembic_version (version_num) VALUES (:rev) ON CONFLICT (version_num) DO NOTHING"),
    {"rev": head_revision}
)
conn.commit()  # Single commit for atomicity
```

**Impact:** No more manual revision tracking. New migrations are automatically picked up. Race conditions between concurrent processes eliminated. SQL injection vector removed.

---

---

## Database Major Fixes (January 27, 2026)

6 major database issues from the database-focused code review have been fixed.

### Fix 10: Missing Index on `trades.resolution_id` Foreign Key

**Status:** Already resolved as part of Fix 6 (added `idx_trades_resolution_id` in the suspicious wins migration).

---

### Fix 11: Dashboard Hourly Stats Grouping Bug

**File Modified:** `dashboard.py`

**Problem:** The hourly activity chart grouped trades by `extract('hour', timestamp)` only, collapsing all days into a single 0-23 hour range. A trade at Monday 3pm and Tuesday 3pm would be counted in the same bucket.

**Fix:** Added `func.date(Trade.timestamp)` to both the SELECT and GROUP BY clauses, so each date+hour combination gets its own bucket. The x-axis now shows proper datetime values.

**Before:** `GROUP BY extract('hour', timestamp)` — loses date context
**After:** `GROUP BY func.date(timestamp), extract('hour', timestamp)` — preserves full timeline

---

### Fix 12: Wallet Metrics Tightly Coupled to Trade Storage

**File Modified:** `src/database/storage.py`

**Problem:** Every `store_trade()` call automatically ran `WalletRepository.update_wallet_metrics()`, which recalculates all metrics for that wallet. This slows down every individual insert and is especially wasteful during bulk operations.

**Fix:** Added `update_wallet_metrics` parameter (defaults to `False`). Callers that need metric updates can opt in explicitly; batch callers can update metrics once after all trades are stored.

```python
# Fast insert (default)
DataStorageService.store_trade(trade_data, market_data)

# With metric update when needed
DataStorageService.store_trade(trade_data, market_data, update_wallet_metrics=True)
```

---

### Fix 13: Inconsistent Retry Configuration

**File Modified:** `alembic/env.py`

**Problem:** `connection.py` uses `MAX_RETRIES=10, INITIAL_DELAY=2` while `alembic/env.py` used `MAX_RETRIES=5, RETRY_DELAY=3`. Different retry behavior makes connection issues harder to debug.

**Fix:** Aligned env.py to use `MAX_RETRIES=10, INITIAL_DELAY=2` matching connection.py. Updated the backoff calculation to use `INITIAL_DELAY`.

---

### Fix 14: Transaction Boundary Confusion in Storage Service

**File Modified:** `src/database/storage.py`

**Problem:** `store_market()` accepted an optional `session` parameter with unclear ownership semantics — when a session was passed in, it was unclear who commits/rolls back.

**Fix:** Extracted the core logic into `_store_market_in_session()` with explicit documentation that the caller owns the transaction. The public `store_market()` method delegates to it, clearly documenting behavior for both session-provided and standalone usage.

---

### Fix 15: Multiple Sessions Per Dashboard Page Load

**File Modified:** `dashboard.py`

**Problem:** The sidebar opened one session for stats, then each page function (`show_overview()`, `show_alerts()`, etc.) opened a second session. This means 2+ concurrent sessions per Streamlit re-run, increasing connection pool pressure.

**Fix:** Refactored `main()` to open a single session that is passed to all page functions. Functions that don't need the session (wallet analysis, network patterns, settings) still manage their own sessions or don't use one. The sidebar stats and main content now share the same session.

---

**Fixed By:** Claude Code Assistant
**Date:** January 26-27, 2026
**Status:** Complete
