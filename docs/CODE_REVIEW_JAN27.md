# Post-Incident Code Review Report

**Date:** January 27, 2026
**Status:** 9/9 Issues FIXED
**Incident Context:** Two production failures on Railway deployment

---

## Executive Summary

Following two production incidents on Railway, a comprehensive post-incident code review was performed to identify similar vulnerabilities across the codebase. The incidents revealed systemic issues with database migration handling, null safety, and validation patterns.

**Key Findings:**
- 3 Critical issues (data loss bug, migration stamp design flaw, NULL market_title)
- 3 Major issues (missing null guards, validators bypassed on write path, PostgreSQL duplicate detection)
- 3 Minor issues (migration idempotency, __repr__ crashes, silent failure masking)

All findings have been documented with specific locations, severity assessments, and recommended fixes.

---

## Incident Timeline

### Incident 1: Database Schema Mismatch
**Date:** January 27, 2026
**Error:** `ERROR: column "trade_result" of relation "trades" does not exist`

**Root Cause:** The `check_and_stamp_if_needed()` function in `alembic/env.py` stamped the database at revision `add_suspicious_wins` without executing its upgrade() function. This resulted in the `trades` table missing four columns that should have been added:
- `trade_result`
- `profit_loss_usd`
- `hours_before_resolution`
- `resolution_id`

**Resolution:** Created backfill migration `fix_missing_suspicious_wins_columns.py` to idempotently add the missing schema elements.

### Incident 2: Pipeline Crash on Missing Wallet Address
**Date:** January 27, 2026
**Error:** `ValidationError: wallet_address cannot be empty`

**Root Cause:** The Polymarket API can return trades without usable wallet addresses (no `wallet_address`, `maker`, `proxyWallet`, or `taker` field). This invalid value flowed unchecked into the wallet metrics and scoring systems, where strict validators raised ValidationError.

**Resolution:** Added null guards in `scoring.py` (line 96) and `storage.py` (lines 205, 489) to gracefully handle missing/invalid wallet addresses.

### Incident 3: Dashboard 502 - Application Failed to Respond
**Date:** January 28, 2026
**Error:** `502 Bad Gateway - Application failed to respond`

**Root Cause (multi-layered):**
1. **Blocking startup:** The Railway start command ran `alembic upgrade head && streamlit run ...` sequentially. If alembic hung on DB connection (up to 210s with exponential backoff), Streamlit never started and Railway killed the container.
2. **Module-level `init_db()`:** `dashboard.py` called `init_db()` at module scope (line 39), blocking Streamlit from binding its port until DB connected.
3. **Port mismatch:** Railway networking was configured to route traffic to port 8501, but no `PORT` environment variable was set. Streamlit received Railway's default internal port (8080), creating a mismatch.

**Resolution:**
- Created `scripts/start_web.py` — runs migrations with a 30s timeout, then starts Streamlit regardless via `os.execvp`
- Moved `init_db()` into `@st.cache_resource` wrapper with `max_retries=3` and graceful error page on failure
- Added `PORT=8501` environment variable in Railway web service settings
- Updated Railway start command to `python scripts/start_web.py`

---

## Migration Chain Analysis

The project uses Alembic for database schema versioning. The current migration chain:

```
d3080b390a2a (initial_schema)
    ↓
add_suspicious_wins
    ↓
add_monitor_tables
    ↓
fix_missing_columns (backfill)
```

### Migration Details

#### 1. `d3080b390a2a_initial_schema.py`
- Creates base tables: `markets`, `trades`, `wallet_metrics`, `alerts`, `pizzint_data`
- Establishes primary keys, foreign keys, and basic indexes
- **Issue:** No idempotency guards (will crash if re-run)

#### 2. `add_suspicious_wins_tables.py`
- Creates `market_resolutions` and `wallet_win_history` tables
- Adds 4 columns to `trades`: `trade_result`, `profit_loss_usd`, `hours_before_resolution`, `resolution_id`
- Adds 8 columns to `wallet_metrics` for win/loss tracking
- **Issue:** This migration was skipped when DB was stamped at HEAD
- **Issue:** No idempotency guards (will crash if re-run)

#### 3. `add_monitor_checkpoint_tables.py`
- Creates `monitor_checkpoints` and `failed_trades` tables for race condition prevention
- **Correct:** Uses idempotency guards (`inspect()` checks)

#### 4. `fix_missing_suspicious_wins_columns.py`
- Backfills all schema changes from `add_suspicious_wins` that were skipped
- **Correct:** Fully idempotent with existence checks for tables, columns, indexes, and constraints

### Migration Backfill Completeness Verification

The backfill migration `fix_missing_columns` correctly covers all elements from `add_suspicious_wins`:

**trades table:**
- ✅ Column: `trade_result`
- ✅ Column: `profit_loss_usd`
- ✅ Column: `hours_before_resolution`
- ✅ Column: `resolution_id`
- ✅ Foreign Key: `fk_trades_resolution`
- ✅ Check Constraint: `check_trade_result`
- ✅ Indexes: `idx_trades_result`, `idx_trades_hours_before`, `idx_trades_resolution_id`

**wallet_metrics table:**
- ✅ Column: `geopolitical_wins`
- ✅ Column: `geopolitical_losses`
- ✅ Column: `total_profit_loss_usd`
- ✅ Column: `early_win_count`
- ✅ Column: `win_streak_max`
- ✅ Column: `win_streak_current`
- ✅ Column: `suspicious_win_score`
- ✅ Column: `last_resolution_check`
- ✅ Indexes: `idx_wallet_metrics_suspicious_win`, `idx_wallet_metrics_profit`

**New tables:**
- ✅ Table: `market_resolutions` (with all indexes and constraints)
- ✅ Table: `wallet_win_history` (with all indexes and constraints)

**Conclusion:** The backfill is complete and comprehensive.

---

## What Was Already Fixed (January 27, 2026)

Before the code review, two fixes were implemented to resolve the immediate production issues:

### 1. Wallet Address Guards
**Files Modified:** `src/analysis/scoring.py`, `src/database/storage.py`

**scoring.py (line 119):**
```python
if not wallet_address or not isinstance(wallet_address, str) or len(wallet_address.strip()) != 42:
    return 0, "Unknown wallet (no valid address)"
```

**storage.py (line 205):**
```python
if update_wallet_metrics and trade.wallet_address and len(trade.wallet_address) == 42:
    try:
        WalletRepository.update_wallet_metrics(session, trade.wallet_address)
```

**storage.py (line 491):**
```python
if not wallet_address or not isinstance(wallet_address, str) or len(wallet_address.strip()) != 42:
    logger.debug(f"Skipping wallet metrics: invalid address '{wallet_address}'")
    return None
```

### 2. Backfill Migration
**File Created:** `alembic/versions/fix_missing_suspicious_wins_columns.py`

This idempotent migration adds all columns, tables, indexes, and constraints that were skipped when the database was stamped at `add_suspicious_wins` without running its upgrade function.

---

## Code Review Findings

### Critical 1: Data Loss Bug in repository.py:40

**Severity:** CRITICAL
**File:** `src/database/repository.py`
**Line:** 40
**Impact:** Trade data successfully inserted into database is rolled back and lost

**Problem:**
```python
def create_trade(session: Session, trade_data: Dict) -> Optional[Trade]:
    try:
        trade = Trade(**trade_data)
        session.add(trade)
        session.flush()  # Get the ID - trade IS NOW IN DB
        logger.debug(f"Created trade: {trade.id} (wallet: {trade.wallet_address[:10]}..., ${trade.bet_size_usd:,.2f})")
        #                                                    ^^^^^^^ CRASH if wallet_address is None
        return trade

    except IntegrityError as e:
        session.rollback()  # This rollback removes the successfully flushed trade!
```

**Explanation:**
1. Line 37-39: Trade is created and flushed to the database successfully
2. Line 40: If `wallet_address` is None, `[:10]` raises TypeError
3. Line 43-44: The except block catches ANY exception, calls `session.rollback()`
4. Result: The successfully flushed trade is rolled back and lost from the database

This is a data loss bug because the trade was valid and successfully inserted, but the logging code causes it to be deleted.

**Recommended Fix:**
```python
logger.debug(f"Created trade: {trade.id} (wallet: {(trade.wallet_address or 'unknown')[:10]}..., ${trade.bet_size_usd:,.2f})")
```

**Additional Context:**
The same pattern appears on line 294:
```python
logger.debug(f"Created wallet metrics for {wallet_address[:10]}...")
```
And line 359:
```python
logger.debug(f"Updated wallet metrics for {wallet_address[:10]}... ({metrics.total_trades} trades)")
```

These should also use null guards, though they're less critical because they occur in methods that already validate wallet_address.

---

### Critical 2: Stamp Logic Still Skips Migrations

**Severity:** CRITICAL
**File:** `alembic/env.py`
**Lines:** 166-251
**Impact:** Future migrations will be silently skipped if DB is stamped without running migrations

**Problem:**
```python
def check_and_stamp_if_needed() -> bool:
    """
    Check if core tables exist but alembic_version is missing/empty.
    If so, stamp the database with the current head revision to avoid
    DuplicateTable errors.

    Returns True if migrations should be skipped (already stamped).
    """
    # ... existence checks ...

    # Tables exist but no alembic_version - need to stamp
    head_revision = _get_head_revision()  # Gets HEAD revision

    # Stamp at HEAD
    conn.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:rev) ON CONFLICT (version_num) DO NOTHING"),
        {"rev": head_revision}
    )
    conn.commit()

    logger.info(f"Database stamped with revision: {head_revision}")
    return True  # SKIP ALL MIGRATIONS

# Lines 248-251
if not check_and_stamp_if_needed():
    run_migrations_online()
else:
    logger.info("Skipping migrations - database already stamped")
    # ^ This branch was taken during Incident 1
```

**Explanation:**
The incident occurred because:
1. Railway database had tables from initial_schema but no `alembic_version` table
2. `check_and_stamp_if_needed()` detected this and stamped at `add_suspicious_wins` (HEAD at that time)
3. Function returned `True`, causing line 248 to skip `run_migrations_online()`
4. Result: The `add_suspicious_wins` migration's upgrade() was never executed
5. Database had `alembic_version = 'add_suspicious_wins'` but was missing all columns/tables from that migration

**The Root Cause:**
Stamping a database at a particular revision means "this database has all changes up to and including this revision." But if you stamp without running migrations, that's a lie. The database doesn't actually have those changes.

**Why This Will Happen Again:**
If a future migration `add_new_feature` adds columns to an existing table, and the database gets stamped at `add_new_feature` without running it, the same schema mismatch will occur.

**Recommended Fix (Option 1 - Preferred):**
Stamp at the INITIAL revision, then let Alembic run all migrations forward:

```python
def check_and_stamp_if_needed() -> bool:
    # ... existence checks ...

    # Tables exist but no alembic_version - stamp at INITIAL revision
    initial_revision = 'd3080b390a2a'  # The first migration

    conn.execute(
        text("INSERT INTO alembic_version (version_num) VALUES (:rev) ON CONFLICT (version_num) DO NOTHING"),
        {"rev": initial_revision}
    )
    conn.commit()

    logger.info(f"Database stamped at initial revision: {initial_revision}")
    return False  # Let migrations run forward from here

# Then migrations will run:
# - add_suspicious_wins (if needed)
# - add_monitor_tables (if needed)
# - fix_missing_columns (if needed)
```

**Recommended Fix (Option 2 - Alternative):**
Always call `run_migrations_online()` - Alembic will detect if DB is current and do nothing:

```python
if context.is_offline_mode():
    run_migrations_offline()
else:
    # Always run migrations - Alembic will detect if up-to-date
    check_and_stamp_if_needed()  # Just stamps, doesn't return skip signal
    run_migrations_online()
```

**Why Option 1 is Better:**
- Option 1 explicitly models the truth: "tables exist from initial_schema, so stamp at initial_schema, then apply remaining migrations"
- Option 2 relies on Alembic's internal logic to detect the stamp and skip migrations

---

### Major 3: Missing Null Guards in storage.py for NOT NULL Fields

**Severity:** MAJOR
**File:** `src/database/storage.py`
**Lines:** 118-216
**Impact:** Database constraint violations when API returns incomplete data

**Problem:**
The `store_trade()` method builds a `db_trade_data` dictionary from API data without validating that required fields are present. Several fields can be None despite having `nullable=False` in the database schema:

**Issue 1: transaction_hash (lines 154-158)**
```python
'transaction_hash': (
    trade_data.get('transaction_hash') or
    trade_data.get('transactionHash') or  # API uses camelCase
    trade_data.get('tx_hash')
),
```
If all three API fields are missing, this resolves to `None`. But the database column is `nullable=False`.

**Issue 2: wallet_address (lines 161-166)**
```python
'wallet_address': (
    trade_data.get('wallet_address') or
    trade_data.get('proxyWallet') or  # API uses proxyWallet
    trade_data.get('maker') or
    trade_data.get('taker')
),
```
If all alternatives are missing, this resolves to `None`. Database column is `nullable=False`. This was the cause of Incident 2 (though now guarded downstream).

**Issue 3: market_id (line 167)**
```python
'market_id': market_id,
```
The `market_id` is extracted from trade_data on lines 142-146, but if all alternatives are missing, it's `None`. Database column is `nullable=False`.

**Issue 4: timestamp (line 160)**
```python
'timestamp': trade_data.get('timestamp'),
```
Can be `None`. Lines 193-198 only handle int/str conversion - if None, neither branch fires. Database column is `nullable=False`.

**Issue 5: bet_size_usd (lines 168-172)**
```python
'bet_size_usd': float(
    trade_data.get('bet_size_usd') or
    trade_data.get('size') or  # API uses size
    trade_data.get('amount') or 0
),
```
Falls back to `0`, but the database has a CHECK constraint `bet_size_usd > 0`, so this raises a constraint violation.

**Current Behavior:**
- These issues cause database constraint violations with cryptic error messages
- The trade is silently dropped (logged as an error but not handled)
- No visibility into which field was missing

**Recommended Fix:**
Add explicit null checks at the top of `store_trade()`:

```python
@staticmethod
def store_trade(
    trade_data: Dict,
    market_data: Dict = None,
    suspicion_score: int = None,
    update_wallet_metrics: bool = False
) -> Optional[Trade]:
    """
    Store trade in database

    Args:
        trade_data: Trade data from Polymarket API
        market_data: Optional market data to cache
        suspicion_score: Optional suspicion score
        update_wallet_metrics: Whether to recalculate wallet metrics

    Returns:
        Trade object or None on error or duplicate
    """
    try:
        # Extract required fields
        transaction_hash = (
            trade_data.get('transaction_hash') or
            trade_data.get('transactionHash') or
            trade_data.get('tx_hash')
        )

        wallet_address = (
            trade_data.get('wallet_address') or
            trade_data.get('proxyWallet') or
            trade_data.get('maker') or
            trade_data.get('taker')
        )

        market_id = (
            trade_data.get('market_id') or
            trade_data.get('asset_id') or
            trade_data.get('conditionId')
        )

        timestamp = trade_data.get('timestamp')

        bet_size_usd = float(
            trade_data.get('bet_size_usd') or
            trade_data.get('size') or
            trade_data.get('amount') or 0
        )

        # Validate required fields BEFORE building db_trade_data
        if not transaction_hash:
            logger.warning("Skipping trade: missing transaction_hash")
            return None

        if not wallet_address or len(wallet_address.strip()) != 42:
            logger.warning("Skipping trade: missing or invalid wallet_address")
            return None

        if not market_id:
            logger.warning("Skipping trade: missing market_id")
            return None

        if not timestamp:
            logger.warning("Skipping trade: missing timestamp")
            return None

        if bet_size_usd <= 0:
            logger.warning("Skipping trade: invalid bet_size_usd")
            return None

        # NOW safe to proceed with database insertion
        with get_db_session() as session:
            # ... rest of existing code ...
```

**Alternative Fix:**
Add these checks in `TradeRepository.create_trade()` before line 37, but the storage layer is the better place since it's the API boundary.

---

### Major 4: Write Path Bypasses Validators

**Severity:** MAJOR
**File:** `src/database/repository.py`, `src/database/validators.py`
**Lines:** repository.py:37, validators.py (entire module)
**Impact:** Invalid data can be written to database; validators only catch issues on reads

**Problem:**

**Part 1: create_trade() doesn't validate:**
```python
# repository.py:25-56
@staticmethod
def create_trade(session: Session, trade_data: Dict) -> Optional[Trade]:
    """Create a new trade record"""
    try:
        trade = Trade(**trade_data)  # No validation!
        session.add(trade)
        session.flush()
        # ...
```

The `create_trade()` method constructs a Trade ORM object directly from `trade_data` without any validation. The strict validators from `validators.py` are never called.

**Part 2: Validators are only used on READ paths:**

Looking at `repository.py`, validators are used in query methods:
- Line 62: `validate_transaction_hash()` in `get_trade_by_tx_hash()`
- Line 73: `validate_wallet_address()` in `get_trades_by_wallet()`
- Line 235: `validate_market_id()` in `get_market()`
- Line 284: `validate_wallet_address()` in `get_or_create_wallet_metrics()`

But NOT in write methods:
- `create_trade()` - no validation
- `create_or_update_market()` - no validation
- `create_alert()` - no validation

**Part 3: Read validators have no null guards:**

The validators in `validators.py` raise ValidationError if passed None:

```python
# validators.py:53-89
@classmethod
def validate_wallet_address(cls, address: Any, field_name: str = "wallet_address") -> str:
    if address is None:
        raise ValidationError(f"{field_name} cannot be None")
    # ...
```

But callers don't always guard against None:
```python
# repository.py:73
wallet_address = DatabaseInputValidator.validate_wallet_address(wallet_address)
```

If `get_trades_by_wallet()` is called with `wallet_address=None`, this raises uncaught ValidationError.

**Current Behavior:**
- Invalid data can be written to the database
- Database constraints catch some issues but give poor error messages
- Validators only help on read operations
- ValidationError can propagate uncaught if None is passed to read methods

**Recommended Fix:**

**Option A: Validate in storage.py (recommended):**
Add validation in `storage.py:store_trade()` before calling `create_trade()`. This was partially addressed in Finding #3, but should explicitly use validators:

```python
# In storage.py before calling TradeRepository.create_trade()
from database.validators import DatabaseInputValidator, ValidationError

try:
    # Validate using strict validators
    transaction_hash = DatabaseInputValidator.validate_transaction_hash(transaction_hash)
    wallet_address = DatabaseInputValidator.validate_wallet_address(wallet_address)
    market_id = DatabaseInputValidator.validate_market_id(market_id)
    timestamp = DatabaseInputValidator.validate_timestamp(timestamp)
    bet_size_usd = DatabaseInputValidator.validate_bet_size(bet_size_usd)

except ValidationError as e:
    logger.warning(f"Skipping trade: {e}")
    return None
```

**Option B: Validate in repository.py:**
Add validation in `create_trade()`:

```python
@staticmethod
def create_trade(session: Session, trade_data: Dict) -> Optional[Trade]:
    """Create a new trade record"""
    try:
        # Validate required fields
        if 'transaction_hash' in trade_data:
            trade_data['transaction_hash'] = DatabaseInputValidator.validate_transaction_hash(
                trade_data['transaction_hash']
            )
        if 'wallet_address' in trade_data:
            trade_data['wallet_address'] = DatabaseInputValidator.validate_wallet_address(
                trade_data['wallet_address']
            )
        # ... etc for other fields

        trade = Trade(**trade_data)
        session.add(trade)
        session.flush()
        # ...
```

**Option C: Add null guards in read methods:**
Wrap validator calls in read methods:

```python
@staticmethod
def get_trades_by_wallet(session: Session, wallet_address: str, limit: int = 100) -> List[Trade]:
    """Get all trades for a wallet"""
    try:
        wallet_address = DatabaseInputValidator.validate_wallet_address(wallet_address)
        limit = DatabaseInputValidator.validate_limit(limit)
    except ValidationError as e:
        logger.error(f"Invalid parameters: {e}")
        return []  # Or raise, depending on desired behavior

    return session.query(Trade)...
```

**Recommendation:** Use Option A (validate in storage.py) for writes, and add try/except in read methods (Option C) for robustness.

---

### Minor 5: Older Migrations Lack Idempotency Guards

**Severity:** MINOR
**File:** `alembic/versions/d3080b390a2a_initial_schema.py`, `alembic/versions/add_suspicious_wins_tables.py`
**Impact:** Migrations will crash if re-run (possible if Alembic bookkeeping is broken)

**Problem:**

The older migrations don't use existence checks:

```python
# d3080b390a2a_initial_schema.py
def upgrade() -> None:
    op.create_table('markets', ...)  # Will crash if table exists
    op.create_table('trades', ...)
    # etc.
```

```python
# add_suspicious_wins_tables.py
def upgrade() -> None:
    op.create_table('market_resolutions', ...)  # Will crash if table exists
    op.add_column('trades', sa.Column('trade_result', ...))  # Will crash if column exists
```

The newer migrations correctly use idempotency guards:

```python
# add_monitor_checkpoint_tables.py
def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'monitor_checkpoints' not in existing_tables:
        op.create_table('monitor_checkpoints', ...)
```

```python
# fix_missing_suspicious_wins_columns.py
def _column_exists(bind, table, column):
    """Check if a column exists in a table."""
    cols = [c['name'] for c in inspect(bind).get_columns(table)]
    return column in cols

def upgrade() -> None:
    bind = op.get_bind()

    if not _column_exists(bind, 'trades', 'trade_result'):
        op.add_column('trades', ...)
```

**Why This Matters:**
The stamp bug (Finding #2) makes it possible for Alembic bookkeeping to become desynchronized with actual schema state. If this happens, an operator might try to manually run migrations, and non-idempotent migrations will crash.

**Recommended Fix:**

**For d3080b390a2a_initial_schema.py:**
```python
def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'markets' not in existing_tables:
        op.create_table('markets', ...)

    if 'trades' not in existing_tables:
        op.create_table('trades', ...)

    # etc. for all tables
```

**For add_suspicious_wins_tables.py:**
```python
def _column_exists(bind, table, column):
    cols = [c['name'] for c in inspect(bind).get_columns(table)]
    return column in cols

def _table_exists(bind, table):
    return table in inspect(bind).get_table_names()

def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, 'market_resolutions'):
        op.create_table('market_resolutions', ...)

    if not _column_exists(bind, 'trades', 'trade_result'):
        op.add_column('trades', sa.Column('trade_result', ...))

    # etc. for all schema changes
```

**Note:** Since the backfill migration `fix_missing_columns` already handles the `add_suspicious_wins` idempotency, this is lower priority. However, `d3080b390a2a` should be updated.

---

### Minor 6: __repr__ Methods Crash on None wallet_address

**Severity:** MINOR
**File:** `src/database/models.py`
**Lines:** 138, 206
**Impact:** Crashes when printing Trade or WalletMetrics objects with None wallet_address

**Problem:**

**Trade.__repr__ (line 138):**
```python
def __repr__(self):
    return f"<Trade(id={self.id}, wallet={self.wallet_address[:10]}..., size=${self.bet_size_usd})>"
    #                                      ^^^^^^^ TypeError if wallet_address is None
```

**WalletMetrics.__repr__ (line 206):**
```python
def __repr__(self):
    return f"<WalletMetrics(wallet={self.wallet_address[:10]}..., trades={self.total_trades}, win_rate={self.win_rate})>"
    #                                  ^^^^^^^ TypeError if wallet_address is None
```

**When This Occurs:**
- During debugging when inspecting objects in a debugger
- When logging objects that get converted to strings
- In error messages that include the object repr

While wallet_address should never be None in a properly functioning system, defensive programming suggests __repr__ should never crash.

**Recommended Fix:**

**Trade.__repr__:**
```python
def __repr__(self):
    wallet_display = (self.wallet_address or 'unknown')[:10]
    return f"<Trade(id={self.id}, wallet={wallet_display}..., size=${self.bet_size_usd})>"
```

**WalletMetrics.__repr__:**
```python
def __repr__(self):
    wallet_display = (self.wallet_address or 'unknown')[:10]
    return f"<WalletMetrics(wallet={wallet_display}..., trades={self.total_trades}, win_rate={self.win_rate})>"
```

**Additional Occurrences:**
The same pattern appears in `repository.py`:
- Line 40: `logger.debug(f"Created trade: {trade.id} (wallet: {trade.wallet_address[:10]}...")`
- Line 294: `logger.debug(f"Created wallet metrics for {wallet_address[:10]}...")`
- Line 359: `logger.debug(f"Updated wallet metrics for {wallet_address[:10]}...")`

These should also be fixed (covered in Finding #1).

---

### Critical 7: NULL market_title Causes IntegrityError — Trades Not Persisted

**Severity:** CRITICAL
**Files:** `src/database/storage.py:179`, `src/api/monitor.py:345`
**Impact:** Every trade where the API payload has `title: null` fails to insert. The monitor logs "Trade not stored (likely duplicate)" — masking a real data error. Trades are permanently lost.

**Problem:**

Two code paths produce `market_title = None`:

**Path A — `monitor.py:345` (title-based fallback):**
```python
market = {
    'id': market_id or trade.get('conditionId', 'unknown'),
    'question': trade.get('title', 'Unknown')
}
```
Python's `.get('title', 'Unknown')` only returns `'Unknown'` when the key is **absent**. If the key **exists** with value `None`, it returns `None`. So `market['question']` = `None`.

**Path B — `storage.py:179` (API-fetched market without 'question'):**
```python
'market_title': market_data.get('question') if market_data else '',
```
When `market_data` is present but has no `'question'` key (or the key is `None`), this evaluates to `None`. The `trades.market_title` column is `NOT NULL` (`models.py:87`), so PostgreSQL rejects the insert.

**The Cascade:**
1. `market_title` = `None` → IntegrityError on INSERT
2. `storage.py:213-215` catches the exception, returns `None`
3. `monitor.py:403-405` logs "Trade not stored (likely duplicate)" — **wrong diagnosis**
4. Monitor advances its checkpoint — trade is **permanently lost**
5. On retry (via overlap buffer), the same trade is attempted again → duplicate key error on `transaction_hash`

**Evidence from Railway logs:**
```
IntegrityError creating trade: null value in column "market_title" of relation "trades" violates not-null constraint
```

**Recommended Fix:**

**storage.py:179** — coalesce to empty string:
```python
# Before (broken):
'market_title': market_data.get('question') if market_data else '',

# After (fixed):
'market_title': (market_data.get('question') or '') if market_data else '',
```

**monitor.py:345** — use `or` instead of default parameter:
```python
# Before (broken):
'question': trade.get('title', 'Unknown')

# After (fixed):
'question': trade.get('title') or 'Unknown'
```

---

### Major 8: PostgreSQL Duplicate Key Detection Broken

**Severity:** MAJOR
**File:** `src/database/repository.py:46`
**Impact:** Duplicate trade inserts on PostgreSQL are logged as warnings instead of being silently deduplicated. Log noise and misleading error messages.

**Problem:**

The IntegrityError handler only checks for the **SQLite** error string:

```python
# repository.py:43-51
except IntegrityError as e:
    session.rollback()
    error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
    if 'UNIQUE constraint failed: trades.transaction_hash' in error_str:
        logger.debug(f"Trade already exists: {trade_data.get('transaction_hash')}")
    else:
        # Log the full error for debugging other constraint violations
        logger.warning(f"IntegrityError creating trade: {error_str}")
```

PostgreSQL produces a **different** error message:
```
duplicate key value violates unique constraint "ix_trades_transaction_hash"
```

This means on Railway (PostgreSQL):
- Legitimate duplicates (from overlap buffer / retries) are logged as `WARNING` instead of `DEBUG`
- The NULL `market_title` IntegrityError is also caught here and logged as a warning, but the actual constraint name is different — it all gets lumped together

**Recommended Fix:**

```python
except IntegrityError as e:
    session.rollback()
    error_str = str(e.orig) if hasattr(e, 'orig') else str(e)
    is_duplicate = (
        'UNIQUE constraint failed: trades.transaction_hash' in error_str or  # SQLite
        ('duplicate key value violates unique constraint' in error_str and
         'transaction_hash' in error_str)  # PostgreSQL
    )
    if is_duplicate:
        logger.debug(f"Trade already exists: {trade_data.get('transaction_hash')}")
    else:
        logger.warning(f"IntegrityError creating trade: {error_str}")
```

---

### Minor 9: Silent Failure Masking — store_trade() Swallows All Exceptions

**Severity:** MINOR
**Files:** `src/database/storage.py:213-215`, `src/api/monitor.py:397-405`
**Impact:** Real data errors (like NULL market_title) are silently swallowed and misreported as "likely duplicate". Trades are permanently lost without retry.

**Problem:**

**storage.py:213-215** catches ALL exceptions and returns None:
```python
except Exception as e:
    logger.error(f"Error storing trade: {e}", exc_info=True)
    return None
```

**monitor.py:397-405** treats any None return as a benign duplicate:
```python
if stored_trade:
    logger.info(
        f"Stored trade in database: ID={stored_trade.id}, "
        f"Score={stored_trade.suspicion_score or 0}/100, "
        f"Alert={stored_trade.alert_level or 'NONE'}"
    )
else:
    # Trade not stored (likely duplicate) - this is OK, don't raise error
    logger.debug("Trade not stored (likely duplicate)")
```

This means:
- A real data error (NULL market_title, constraint violation) returns `None`
- The monitor treats it as a harmless duplicate
- The checkpoint advances — the trade is **never retried**
- The trade is permanently lost from the database

**Recommended Fix (Option A — distinguish error from duplicate):**

In `storage.py`, re-raise non-duplicate errors:
```python
except Exception as e:
    logger.error(f"Error storing trade: {e}", exc_info=True)
    # Don't swallow real errors — let the monitor handle them
    raise
```

In `monitor.py`, handle the re-raised exception:
```python
try:
    stored_trade = DataStorageService.store_trade(
        trade_data=trade,
        market_data=market,
        suspicion_score=suspicion_score
    )
except Exception as e:
    logger.error(f"Failed to store trade: {e}")
    stored_trade = None
    # Optionally add to dead-letter queue here
```

**Recommended Fix (Option B — return sentinel):**

In `storage.py`, return distinct values:
```python
# Return None for duplicates, raise for real errors
except IntegrityError as e:
    # Duplicate — this is fine
    return None
except Exception as e:
    logger.error(f"Error storing trade: {e}", exc_info=True)
    raise  # Real error — let caller decide
```

---

## Summary Table

| ID | Severity | Component | Issue | Impact | Status |
|----|----------|-----------|-------|--------|--------|
| 1 | CRITICAL | repository.py:40 | Data loss: successful trade rolled back on logging error | Lost trade data | ✅ FIXED |
| 2 | CRITICAL | alembic/env.py:248 | Stamp logic skips migrations | Future schema mismatches | ✅ FIXED |
| 3 | MAJOR | storage.py:153-190 | Missing null guards for NOT NULL fields | DB constraint violations | ✅ FIXED |
| 4 | MAJOR | repository.py:37 | Write path bypasses validators | Invalid data in DB | ✅ FIXED |
| 5 | MINOR | alembic/versions/*.py | Older migrations not idempotent | Manual recovery issues | ✅ FIXED |
| 6 | MINOR | models.py:138,206 | __repr__ crashes on None wallet | Debugging crashes | ✅ FIXED |
| 7 | CRITICAL | storage.py:179, monitor.py:345 | NULL market_title — trades not persisted | Permanent trade data loss | ✅ FIXED |
| 8 | MAJOR | repository.py:46 | PostgreSQL duplicate detection broken | Log noise, misdiagnosed errors | ✅ FIXED |
| 9 | MINOR | storage.py:213-215, monitor.py:397-405 | Silent failure masking — errors reported as duplicates | Lost trades, no retry | ✅ FIXED |

---

## Recommended Fix Priority Order

### Priority 1: Critical Fixes (Immediate)

**7. Fix NULL market_title — Trades Not Persisted (Critical 7)**
- Files: `src/database/storage.py:179`, `src/api/monitor.py:345`
- Use `or` coalescing: `(market_data.get('question') or '')` and `trade.get('title') or 'Unknown'`
- Risk: Very low (strictly safer)
- **This is the current production blocker — fix first**

**1. Fix Data Loss Bug (Critical 1)**
- File: `src/database/repository.py:40`
- Change to `(trade.wallet_address or 'unknown')[:10]`
- Risk: Very low (safer code)

**2. Fix Migration Stamp Logic (Critical 2)**
- File: `alembic/env.py:248-251`
- After stamping, still call `run_migrations_online()` instead of skipping
- Risk: Medium (requires testing on Railway)

### Priority 2: Major Fixes (Within 1 Week)

**8. Fix PostgreSQL Duplicate Detection (Major 8)**
- File: `src/database/repository.py:46`
- Add PostgreSQL error pattern alongside SQLite pattern
- Risk: Very low

**3. Add Null Guards in storage.py (Major 3)**
- File: `src/database/storage.py`
- Add validation at top of `store_trade()` for all NOT NULL fields
- Risk: Low (fail-fast behavior, better error messages)

**4. Validate on Write Path (Major 4)**
- Files: `src/database/storage.py`, `src/database/repository.py`
- Use validators on write operations, add null guards on read operations
- Risk: Low (stronger data integrity)

### Priority 3: Minor Fixes (Within 1 Month)

**9. Fix Silent Failure Masking (Minor 9)**
- Files: `src/database/storage.py:213-215`, `src/api/monitor.py:397-405`
- Re-raise non-duplicate errors from store_trade(); distinguish error from duplicate in monitor
- Risk: Low (better error visibility)

**5. Add Migration Idempotency (Minor 5)**
- File: `alembic/versions/d3080b390a2a_initial_schema.py`
- Add existence checks before create_table operations
- Risk: Very low (defensive programming)

**6. Fix __repr__ Methods (Minor 6)**
- File: `src/database/models.py`
- Add null guards in Trade and WalletMetrics __repr__
- Risk: Very low (defensive programming)

---

## Impact Assessment

### Data Integrity
- **Critical 1:** Potential data loss (trades successfully inserted but rolled back)
- **Critical 2:** Schema mismatches causing runtime errors
- **Major 3:** Database constraint violations with poor error messages
- **Major 4:** Invalid data can enter database (though currently caught by DB constraints)

### System Reliability
- **Critical 1:** Random trade drops when wallet_address is None
- **Critical 2:** Future deployments may silently skip migrations
- **Major 3 & 4:** Pipeline crashes on edge-case API responses

### Maintainability
- **Critical 2:** Migration issues difficult to diagnose and repair
- **Major 4:** Inconsistent validation patterns (read vs write)
- **Minor 5:** Manual migration recovery difficult if Alembic bookkeeping breaks

### Security
- **Major 4:** Bypassing validators could allow injection if code is refactored to use raw SQL
- All findings have security implications through data integrity issues

### Performance
- No direct performance impact from any finding
- Proper validation may slightly slow write operations (negligible)

---

## Testing Recommendations

### For Critical Fixes

**Test Case 1: Data Loss Bug**
```python
def test_create_trade_with_none_wallet():
    """Verify trade with None wallet_address doesn't cause rollback"""
    trade_data = {
        'transaction_hash': '0x123...',
        'wallet_address': None,  # This should not cause data loss
        'bet_size_usd': 1000,
        # ... other fields
    }

    with get_db_session() as session:
        trade = TradeRepository.create_trade(session, trade_data)
        # Should return None gracefully, not raise exception
        assert trade is None
```

**Test Case 2: Migration Stamp Logic**
```python
def test_migration_after_stamp():
    """Verify migrations run after stamping at initial revision"""
    # 1. Create database with initial_schema tables
    # 2. Drop alembic_version table
    # 3. Run alembic upgrade head
    # 4. Verify all columns from add_suspicious_wins exist
    # 5. Verify alembic_version is at latest revision
```

### For Major Fixes

**Test Case 3: Null Guards in storage.py**
```python
def test_store_trade_missing_required_fields():
    """Verify store_trade gracefully handles missing required fields"""
    # Missing transaction_hash
    result = DataStorageService.store_trade({'wallet_address': '0x123...', 'bet_size_usd': 1000})
    assert result is None

    # Missing wallet_address
    result = DataStorageService.store_trade({'transaction_hash': '0x123...', 'bet_size_usd': 1000})
    assert result is None

    # Missing market_id
    result = DataStorageService.store_trade({
        'transaction_hash': '0x123...',
        'wallet_address': '0x123...',
        'bet_size_usd': 1000
    })
    assert result is None
```

**Test Case 4: Write Path Validation**
```python
def test_create_trade_validates_inputs():
    """Verify create_trade rejects invalid wallet addresses"""
    trade_data = {
        'transaction_hash': '0x123...',
        'wallet_address': 'invalid',  # Should be rejected
        'bet_size_usd': 1000,
        # ... other fields
    }

    with get_db_session() as session:
        with pytest.raises(ValidationError):
            TradeRepository.create_trade(session, trade_data)
```

---

## Lessons Learned

### 1. Database Migration Management
- **Never** stamp a database without running migrations
- Stamping should only be used for databases that genuinely have all schema changes
- Consider stamping at the first migration, not the latest
- Always make migrations idempotent with existence checks

### 2. Null Safety
- API responses can have missing fields even if documented as required
- Validate required fields at the earliest boundary (API response parsing)
- Use null guards in logging/debugging code (defensive programming)
- Consider using Optional types in function signatures

### 3. Validation Patterns
- Validators should be used consistently on both read and write paths
- Write path is more critical (prevents invalid data from entering system)
- Read path validation provides better error messages
- Validators should have null guards or callers should guard against None

### 4. Error Handling
- Broad exception handlers (except Exception) can hide bugs
- Session rollback should only occur on database errors, not application errors
- Logging code should never cause data loss
- Consider separate exception types for different error categories

### 5. Code Review Process
- Post-incident reviews should examine similar patterns across codebase
- Look for repeated patterns (like [:10] slicing without null checks)
- Check consistency of defensive patterns across modules
- Verify that fixes address root cause, not just symptoms

---

## Related Documentation

- [CRITICAL_FIXES.md](./CRITICAL_FIXES.md) - Previous code review (January 12, 2026)
- [DATABASE.md](./DATABASE.md) - Database schema documentation
- [MIGRATIONS.md](./MIGRATIONS.md) - Migration guide (if exists)

---

## Implementation Log

### Fixes Applied — January 27, 2026

**Round 1: Pre-incident patches (wallet address + backfill migration)**
- `src/analysis/scoring.py` — Early return in `score_wallet_history()` for missing/invalid wallet addresses
- `src/database/storage.py` — Guard on `update_wallet_metrics` and `get_wallet_metrics` for invalid wallets
- `alembic/versions/fix_missing_suspicious_wins_columns.py` — Backfill migration for columns skipped by stamp

**Round 2: Critical fixes**
- **Finding 7** — `storage.py:179`: `market_data.get('question')` → `(market_data.get('question') or '')` (both `store_trade` and `store_trades_bulk`). `monitor.py:345`: `trade.get('title', 'Unknown')` → `trade.get('title') or 'Unknown'` (both occurrences)
- **Finding 1** — `repository.py:40`: `trade.wallet_address[:10]` → `(trade.wallet_address or 'unknown')[:10]`. Same fix applied to lines 294 and 359.
- **Finding 2** — `alembic/env.py`: Changed stamp logic to use initial revision (`d3080b390a2a`) instead of HEAD. Changed return to `False` so migrations always run forward. Removed dead `else` branch — `check_and_stamp_if_needed()` and `run_migrations_online()` now always both execute.
- **Finding 6** (minor, bundled) — `models.py`: Fixed `__repr__` on `Trade` (line 138), `WalletMetrics` (line 206), and `WalletWinHistory` (line 369) to guard against None `wallet_address`.

**Round 3: Major fixes**
- **Finding 8** — `repository.py:46`: Added PostgreSQL duplicate detection pattern (`'duplicate key value violates unique constraint'` + `'transaction_hash'`) alongside existing SQLite pattern.
- **Finding 3** — `storage.py` `store_trade()`: Extracted `transaction_hash`, `wallet_address`, `timestamp`, `bet_size_usd` into variables with explicit null/validity checks before building `db_trade_data`. Returns `None` with warning log if any required field is missing. Same guards added to `store_trades_bulk()`.
- **Finding 4** — `repository.py` `create_trade()`: Added `DatabaseInputValidator` calls for `transaction_hash`, `wallet_address`, and `market_id` before constructing the ORM object. `ValidationError` caught and returns `None`.

**Round 4: Minor fixes**
- **Finding 5** — Added idempotency guards (`_table_exists`, `_column_exists`, `_index_exists`, `_constraint_exists`) to both `d3080b390a2a_initial_schema.py` and `add_suspicious_wins_tables.py`. All `create_table`, `add_column`, `create_index`, and `create_constraint` calls are now wrapped in existence checks.
- **Finding 9** — `storage.py`: changed `store_trade()` to re-raise non-duplicate exceptions instead of swallowing them. `monitor.py`: added `try/except` around `store_trade()` call so the monitor logs real errors distinctly from duplicates. Log message changed from "likely duplicate" to "duplicate or skipped".

### Test Results
All 64 tests passing after all 9 fixes.

---

## Conclusion

This post-incident code review identified 9 issues (3 critical, 3 major, 3 minor). The most urgent is **Finding 7 (NULL market_title)** — the current production blocker causing trades to not be persisted at all. Findings 8 and 9 form a cascade with Finding 7: the IntegrityError is swallowed (9), misreported as a duplicate (8), and the trade is permanently lost.

The earlier findings (1-6) from the initial audit address migration safety, null resilience, validation consistency, and defensive programming.

All findings share a common theme: insufficient defensive programming and validation at system boundaries. The recommended fixes strengthen data integrity, improve error messages, and make the system more resilient to edge cases in API responses.

**Total Issues:** 9 (3 critical, 3 major, 3 minor)
**Resolved:** 9 of 9 — all issues fixed
**Tests:** 64/64 passing after all fixes

---

**Report Prepared By:** Code Review Team
**Date:** January 27, 2026
**Revision:** 4 (all 9 issues fixed)
**Status:** 9/9 Fixed — Complete
