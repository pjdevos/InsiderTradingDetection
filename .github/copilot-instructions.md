# Copilot Instructions for Geopolitical Insider Trading Detection

## Project Overview

This is a **Python-based geopolitical insider trading detection system** (Phase 6 complete, Phase 7 in development). It monitors Polymarket prediction markets for suspicious large bets that may indicate insider knowledge of geopolitical events, combining financial signals (trades), operational signals (PizzINT), and blockchain verification. Phase 7 adds "suspicious wins" detection - tracking market resolutions and identifying wallets with abnormally profitable trading patterns.

**Key Statistics:**
- ~5,500+ lines of production code
- 8 major service modules (API, blockchain, analysis, database, alerts, dashboard, patterns, win tracking)
- 20+ test files + 19 integration test scripts
- Deployed on Railway with PostgreSQL backend
- Advanced pattern detection: repeat offenders, coordinated trading, temporal patterns, sybil networks

---

## Architecture Overview

### High-Level Data Flow

```
Polymarket APIs → PolymarketAPIClient → RealTimeTradeMonitor
       ↓                                        ↓
   Market Data              SuspicionScorer (7-factor)
       ↓                            ↓
Blockchain Verification    DataStorageService → Database
       ↓                            ↓
   Polygon RPC          [Market Resolution Monitor]
                               ↓
                    WinLossCalculator (Phase 7)
                               ↓
                    SuspiciousWinScorer (Phase 7)
                               ↓
    Alerts: Telegram Bot + Email + Dashboard
```

### Service Boundaries (Know What Lives Where)

| Module | Responsibility | Key Files | LOC |
|--------|-----------------|-----------|-----|
| **API** | Fetch trades, markets, wallet history; manage checkpoints | `src/api/client.py`, `monitor.py`, `resolution_monitor.py` | 1,500+ |
| **Analysis** | Multi-factor suspicion scoring, pattern detection, win detection | `src/analysis/scoring.py`, `patterns.py`, `win_calculator.py`, `win_scoring.py` | 2,000+ |
| **Blockchain** | Verify transactions on Polygon, detect mixer funding, rate limiting | `src/blockchain/client.py`, `rate_limiter.py` | 700+ |
| **Database** | ORM models, repositories, migrations, validation | `src/database/{models,repository,storage,connection,validators}.py` + Alembic | 1,400+ |
| **Alerts** | Telegram bot (4 commands), email alerts, rate limiting, credential validation | `src/alerts/{telegram_bot,email_alerts,templates,credential_validator}.py` | 1,200+ |
| **Dashboard** | Streamlit web UI with 6+ pages, SQL aggregations, analytics | `dashboard.py` (876 lines), **deployed on Railway** | 876 |

---

## Critical Developer Patterns

### 1. Data Validation & Input Security

**Pattern:** ALL external inputs validated before use. Examples:
- `_validate_wallet_address()` - EIP-55 checksum validation via Web3.to_checksum_address()
- `_validate_market_id()`, `_validate_tx_hash()` - Length, format checks
- Dashboard SQL injection prevention via regex escaping
- `CredentialValidator` - Placeholder pattern detection to prevent silent credential failures

**When to Apply:** Adding any endpoint/API that accepts user input or reading credentials.

**Files:** `src/api/client.py` (lines 60-100), `src/blockchain/client.py`, `src/alerts/credential_validator.py` (255 lines)

**Example:**
```python
from alerts.credential_validator import CredentialValidator

is_valid, errors = CredentialValidator.validate_telegram_credentials(
    bot_token=token,
    chat_id=chat_id,
    required=config.ALERTS_REQUIRED  # Fail fast or log warnings
)
```

### 2. Timezone-Aware Datetime Handling

**Pattern:** Always use `datetime(..., tzinfo=timezone.utc)` or `datetime.now(timezone.utc)`. Never use `datetime.utcnow()` (deprecated in Python 3.12+).

**Why:** Prevents timezone confusion bugs. System handles UTC internally, converts for display.

**Example:**
```python
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)  # ✅ Always use this
```

**Affected:** All scoring, storage, timing logic, and pattern analysis.

### 3. Database Session Management with Context Managers

**Pattern:** Always use `with get_db_session() as session:` for database operations.

```python
from src.database.connection import get_db_session
from src.database.repository import TradeRepository

with get_db_session() as session:
    repo = TradeRepository(session)
    trade = repo.get_by_id(trade_id)  # Auto-commits on success, rolls back on error
```

**Why:** Ensures connections are closed, transactions are managed, no resource leaks.

**Files:** `src/database/connection.py` (context manager), `src/database/repository.py` (usage examples)

### 4. Wallet Address Handling - Guard Against Missing Values

**Pattern:** Check for valid wallet before database operations:

```python
# In scoring.py and storage.py - skip trades with invalid wallets
if not wallet_address or not isinstance(wallet_address, str):
    logger.warning(f"Skipping trade with invalid wallet: {wallet_address}")
    return None
```

**Why:** API can return trades with missing/null wallet addresses. Prevents pipeline crashes.

**Example Bug Fix:** Jan 27, 2026 - Added guards in `scoring.py` line ~85 and `storage.py` line ~120.

### 5. Rate Limiting for Telegram Alerts

**Pattern:** Use `AlertRateLimiter` to prevent spam (max 10/hour, 60s between alerts):

```python
from src.alerts.telegram_bot import get_rate_limiter

rate_limiter = get_rate_limiter()
if rate_limiter.should_rate_limit(alert_level="CRITICAL"):
    # CRITICAL alerts bypass rate limiting
    send_alert()
else:
    # WATCH/SUSPICIOUS alerts subject to limits
    send_alert()
```

**Why:** Telegram has rate limits; prevents cascade failures.

**Files:** `src/alerts/telegram_bot.py` (AlertRateLimiter class, ~100 lines)

### 6. Scoring Integration Points - Trade Suspicion

**Pattern:** Scoring happens AFTER storage, with optional blockchain verification:

```python
from src.analysis.scoring import SuspicionScorer

# Calculate score (blockchain check optional)
result = SuspicionScorer.calculate_score(
    trade_data,
    market_data,
    use_blockchain=False  # Set True for enhanced wallet history
)

# Returns: {score, alert_level, breakdown, blockchain_verified}
```

**Alert Levels:**
- `NONE` (<50): No alert
- `WATCH` (50-69): Telegram only (rate limited)
- `SUSPICIOUS` (70-84): Telegram + Email
- `CRITICAL` (85-100): Telegram (bypasses rate limits) + Email

**Files:** `src/analysis/scoring.py` (lines 1-100 for constants, 531 lines total)

### 7. Win Score Integration - Suspicious Wins (Phase 7)

**Pattern:** After market resolution, calculate win scores using `SuspiciousWinScorer`:

```python
from src.analysis.win_scoring import SuspiciousWinScorer, WIN_ALERT_THRESHOLDS

scorer = SuspiciousWinScorer()
result = scorer.calculate_win_score(wallet_address, session)

# Returns: {
#   score: 0-100,
#   alert_level: 'WATCH_WIN'|'SUSPICIOUS_WIN'|'CRITICAL_WIN'|'NONE',
#   breakdown: {factor_name: points_breakdown},
#   min_trades_met: bool
# }
```

**Win Alert Thresholds:**
- `WATCH_WIN` (50+): Win rate >60% OR timing pattern
- `SUSPICIOUS_WIN` (70+): Win rate >70% AND multiple factors
- `CRITICAL_WIN` (85+): Win rate >80% OR timing+geopolitical combo

**Files:** `src/analysis/win_scoring.py` (525 lines), `src/analysis/win_calculator.py` (445 lines)

### 8. Pattern Analysis - Detect Coordinated/Repeat Offenders

**Pattern:** Use `analyze_wallet()` for individual wallets, `find_repeat_offenders()` for network analysis:

```python
from src.analysis.patterns import (
    analyze_wallet,
    find_repeat_offenders,
    find_suspicious_networks,
    TemporalPattern
)

# Analyze single wallet
profile = analyze_wallet(wallet_address, session)
print(f"Win rate: {profile.win_rate}, Early trades: {profile.early_trade_ratio}")

# Find coordinated trading
networks = find_suspicious_networks(session, min_wallets=2, time_window_minutes=30)
for network in networks:
    print(f"Pattern: {network.pattern_type} - {network.trade_count} trades")
```

**Pattern Types:** 'coordinated', 'copycat', 'sybil', 'temporal'

**Files:** `src/analysis/patterns.py` (560 lines), includes `WalletProfile`, `NetworkPattern`, `TemporalPattern` dataclasses

### 9. Repository Pattern for Data Access

**Pattern:** Always use Repository classes, never raw SQLAlchemy queries in business logic.

**Available Repositories:**
- `TradeRepository` - Get/create trades, query by wallet/market/score
- `MarketRepository` - Markets and resolutions
- `WalletRepository` - Wallet metrics and profiles
- `AlertRepository` - Alerts and delivery tracking
- `CheckpointRepository` - Monitor state (prevents race conditions)
- `FailedTradeRepository` - Error tracking
- `WalletWinHistoryRepository` - Win/loss tracking (Phase 7)

**Example:**
```python
from src.database.repository import TradeRepository
from src.database.connection import get_db_session

with get_db_session() as session:
    repo = TradeRepository(session)
    recent = repo.get_trades_by_wallet(wallet_address, limit=100)
    suspicious = repo.get_suspicious_trades(min_score=70, limit=50)
```

**Files:** `src/database/repository.py` (1,000+ lines)

---

## Testing Patterns

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_scoring.py -v

# Run specific test
pytest tests/test_scoring.py::test_bet_size_scoring -v

# Show print statements and coverage
pytest tests/ -v -s --cov=src

# Run integration tests (manual validation)
python scripts/test_scoring_integration.py
python scripts/test_suspicious_wins.py
```

**Config:** `pytest.ini` - Uses `testpaths = tests`, strict markers

### Test Files Overview

**Unit Tests:**
- `tests/test_api_client.py` - API client validation, input handling, error cases
- `tests/test_scoring.py` - 7-factor scoring algorithm (20 tests)
- `tests/test_blockchain_integration.py` - Polygon Web3 interaction
- `tests/test_rate_limiter.py` - Telegram alert rate limiting (10/hour, 60s between)
- `tests/test_config.py` - Configuration loading and validation

**Integration Tests (scripts/):**
- `scripts/test_scoring_integration.py` - End-to-end scoring + database
- `scripts/test_suspicious_wins.py` - Win/loss calculation + win scoring
- `scripts/test_telegram_bot.py` - Bot message formatting and delivery
- `scripts/test_email_alerts.py` - SMTP and HTML formatting
- `scripts/test_database_integration.py` - Full database pipeline
- `scripts/test_api_connection.py` - Live Polymarket API connectivity
- `scripts/test_resolution_fetch.py` - Market resolution detection
- `scripts/test_startup_validation.py` - Startup checks and credential validation

### Writing New Tests

**Location:** `tests/test_*.py` (follows pattern: `test_<module>.py`)

**Structure:**
```python
def test_feature_name():
    """Clear description of what is tested"""
    # Arrange
    test_data = {...}
    
    # Act
    result = function_under_test(test_data)
    
    # Assert
    assert result.score == expected_value
```

**Testing Phase 7 Features:**
```python
from analysis.win_calculator import WinLossCalculator
from analysis.win_scoring import SuspiciousWinScorer

def test_win_loss_calculation():
    """Test trade outcome calculation after resolution"""
    calc = WinLossCalculator()
    result = calc.calculate_trade_result(trade, resolution)
    assert result['result'] in ['WIN', 'LOSS', 'VOID']

def test_suspicious_win_scoring():
    """Test win pattern scoring"""
    scorer = SuspiciousWinScorer()
    result = scorer.calculate_win_score(wallet_address)
    assert 0 <= result['score'] <= 100
```

---

## Configuration & Environment

### Environment Variables

**Critical (must set):**
```bash
POLYMARKET_API_KEY=...          # From https://docs.polymarket.com
DATABASE_URL=postgresql://...   # For production (SQLite used for dev)
POLYGON_RPC_URL=https://...     # From Alchemy/Infura
```

**Alerts:**
```bash
TELEGRAM_BOT_TOKEN=...          # From @BotFather
TELEGRAM_CHAT_ID=...            # Chat ID where alerts go
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=...               # Gmail App Password
EMAIL_TO=...                    # Comma-separated recipients
```

**Configuration File:** `src/config.py` (531 lines, includes `SecureString` masking for logs)

**Loading:** Uses `python-dotenv` to load `.env` automatically.

---

## Building & Deployment

### Local Development

```bash
# Setup
python -m venv venv
venv\Scripts\activate           # Windows
pip install -r requirements.txt

# Validate setup
python scripts/validate_setup.py

# Run database migrations
alembic upgrade head

# Start monitor
python scripts/start_monitoring.py

# Start dashboard (separate terminal)
streamlit run dashboard.py
```

### Production (Railway)

**Deployed Services:**
1. **Dashboard** (Streamlit) - http://geoint-dashboard.railway.app
2. **Monitor** (Background job) - Runs continuously

**Deployment Files:**
- `Dockerfile` - Container image
- `railway.json` - Railway configuration
- `Procfile` - Service definitions
- `.env.railway` - Production secrets (on Railway, not in git)

**Key Issue Solved (Jan 16, 2026):** Railway private networking DNS delays → Added retry logic with exponential backoff in database connection.

---

## Common Workflows

### Adding a New Alert Type

1. **Create template** in `src/alerts/templates.py`:
   ```python
   def telegram_new_alert_message(data) -> str:
       return f"🆕 New Alert: {data['title']}"
   ```

2. **Integrate with monitor** in `src/api/monitor.py`:
   ```python
   from alerts import send_trade_alert
   # Alert already integrated at line ~180
   ```

3. **Test** via `scripts/test_telegram_bot.py`

### Adding a Scoring Factor

1. **Update weights** in `src/analysis/scoring.py`:
   ```python
   WEIGHT_NEW_FACTOR = 25  # Add to class constants
   MAX_SCORE = 135 + 25    # Adjust total
   ```

2. **Implement scoring method**:
   ```python
   def _score_new_factor(self, trade_data, market_data) -> tuple:
       points = ...  # Calculate
       breakdown = {
           "factor_name": "New Factor",
           "points_earned": points,
           "max_points": 25,
           "reasoning": "..."
       }
       return points, breakdown
   ```

3. **Add to composite score** in `calculate_score()` method

4. **Test** via `pytest tests/test_scoring.py -v`

### Implementing Phase 7 Features (Suspicious Wins)

**1. Market Resolution Monitoring:**
```python
from src.api.resolution_monitor import ResolutionMonitor
from src.api.client import PolymarketAPIClient

# In monitor loop:
monitor = ResolutionMonitor(api_client)
resolved_markets = monitor.check_resolved_markets()
for market in resolved_markets:
    resolution = monitor.infer_resolution(market)  # Uses price inference
    store_resolution(market_id, resolution)
```

**2. Win/Loss Calculation:**
```python
from src.analysis.win_calculator import WinLossCalculator

calc = WinLossCalculator()
trades = get_trades_for_market(market_id)
for trade in trades:
    result = calc.calculate_trade_result(trade, resolution)
    # result = {result: 'WIN'|'LOSS'|'VOID', profit_loss_usd: float, hours_before_resolution: float}
    store_win_history(trade.wallet_address, result)
```

**3. Suspicious Win Scoring:**
```python
from src.analysis.win_scoring import SuspiciousWinScorer, WIN_ALERT_THRESHOLDS

scorer = SuspiciousWinScorer()
result = scorer.calculate_win_score(wallet_address, session)
if result['alert_level'] in ['SUSPICIOUS_WIN', 'CRITICAL_WIN']:
    send_win_alert(wallet_address, result)
```

### Debugging API Issues

**Check API connection:**
```bash
python scripts/test_api_connection.py
```

**Trace API calls:**
- Look at logs in `logs/` directory
- `PolymarketAPIClient` has detailed logging at each step
- Sensitive data (API keys, wallet addresses) masked in logs via `SecureString`

**Common Issues:**
- 429 (rate limited) → Retry with exponential backoff (already implemented)
- 401 (auth failed) → Check `POLYMARKET_API_KEY` in `.env`
- 500 (server error) → Check Polymarket status page
- Missing resolution data → Use `infer_resolution_from_prices()` (price → 1.0 = winning outcome)

---

## Key Files Quick Reference

| Task | File |
|------|------|
| Add API endpoint | `src/api/client.py` |
| Add scoring factor | `src/analysis/scoring.py` |
| Add database table | `src/database/models.py` + Alembic migration |
| Add alert format | `src/alerts/templates.py` |
| Configure thresholds | `src/config.py` |
| Modify dashboard | `dashboard.py` |
| Add test | `tests/test_*.py` |
| Check what's deployed | `Dockerfile`, `Procfile`, `railway.json` |

---

## Known Limitations & Deferred Work

### Phase 7 (In Planning)

- **Suspicious Wins Detection** - Track market resolutions and detect abnormally profitable traders
- **Technical Spec:** `docs/SUSPICIOUS_WINS_SPEC.md` (660 lines, ready for implementation)
- **Already implemented:** `BlockchainClient.infer_resolution_from_prices()` - Ready for win detection

### Deferred Scoring Factors

- **PizzINT Correlation (30 points)** - Requires Pentagon activity data scraper (deferred, not counted in current max score)
- **Current System:** 135 points active (will be 165 when PizzINT added)

### Known Issues

- **Blockchain Query Limitations** - Conditional Tokens contract queries fail for Polymarket; using price inference as workaround (works well)
- **Streamlit Deprecation** - `use_container_width` deprecated; needs migration to `width='stretch'` after 2025-12-31

---

## Code Review Standards (From Jan 26-27)

When reviewing/writing code, ensure:
- ✅ All external inputs validated (wallet addresses, market IDs, etc.)
- ✅ Timezone-aware datetime (never `utcnow()`)
- ✅ Database operations use context managers
- ✅ Sensitive data masked in logs
- ✅ Tests included for new features
- ✅ Integration tests in `scripts/` for API-dependent features
- ✅ Error handling with clear messages
- ✅ Type hints on all public methods

**Reference:** `docs/CRITICAL_FIXES_JAN26.md`, `docs/CODE_REVIEW_JAN27.md`

---

## Documentation Index

- **Project Overview:** `PROJECT_SUMMARY.md` (2,000+ lines, comprehensive)
- **Phase Completion:** `docs/PHASE1-6_COMPLETION.md` (status of each phase)
- **Technical Specs:** `docs/SUSPICIOUS_WINS_SPEC.md` (Phase 7 ready for implementation)
- **Security Fixes:** `docs/CRITICAL_FIXES_JAN26.md`, `docs/SQL_INJECTION_FIX.md`, `docs/RACE_CONDITION_FIX.md`
- **GitHub:** https://github.com/pjdevos/InsiderTradingDetection

---

## Questions This Guide Answers

- ❓ **"Where does a new alert message format go?"** → `src/alerts/templates.py`
- ❓ **"How do I add a scoring factor?"** → `src/analysis/scoring.py` (constants + method + composite)
- ❓ **"Why am I getting timezone errors?"** → Use `datetime.now(timezone.utc)` not `utcnow()`
- ❓ **"How do I validate wallet addresses?"** → Use `_validate_wallet_address()` in client.py
- ❓ **"What's the data flow?"** → API → Monitor → Scorer → Storage → Alerts → Dashboard
- ❓ **"How are alerts sent?"** → Telegram (immediate, rate-limited) + Email (high-severity only)
- ❓ **"What's deployed on Railway?"** → Dashboard + Monitor (both running in production)
