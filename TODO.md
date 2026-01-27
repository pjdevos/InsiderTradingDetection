# TODO - Geopolitical Insider Trading Detection System

**Last Updated:** January 27, 2026
**Current Phase:** Phase 7 Planning (Suspicious Wins Detection)
**Next Milestone:** Implement Win/Loss Tracking & Suspicious Win Scoring
**Repository:** https://github.com/pjdevos/InsiderTradingDetection
**Deployment:** Railway (Dashboard + Monitor running)

---

## Legend

- ✅ Complete
- 🔄 In Progress
- ⏳ Planned
- ❌ Blocked
- 🔥 High Priority
- ⚠️ Medium Priority
- 💡 Nice to Have

---

## Phase 2: Database Integration ✅ COMPLETE

### Completed Items

- [x] ✅ **Integrate database storage with API monitor**
  - [x] Updated `monitor.py` to use `DataStorageService`
  - [x] Store trades automatically when detected
  - [x] Store market data on first detection
  - [x] Add error handling for storage failures
  - [x] Test end-to-end flow: API → Storage → Database

- [x] ✅ **Database integration tests**
  - [x] Test trade creation and deduplication
  - [x] Test market create/update logic
  - [x] Integration test scripts created
  - [x] All tests passing

- [x] ✅ **Database setup**
  - [x] SQLite database initialized
  - [x] Alembic migrations applied
  - [x] Storage service operational

### 💡 Nice to Have

- [ ] Switch from SQLite to PostgreSQL for production
- [ ] Add database backup script
- [ ] Create database health check endpoint
- [ ] Add database connection retry logic
- [ ] Implement database connection timeout handling

---

## Phase 3: Suspicion Scoring & Analysis Engine ✅ CORE COMPLETE

### Completed Features

- [x] ✅ **Suspicion Scoring Algorithm**
  - [x] Created `analysis/scoring.py` module (500+ lines)
  - [x] Implemented 7-factor scoring system:
    - [x] Factor 1: Bet Size (30 points max)
    - [x] Factor 2: Wallet History (40 points max)
    - [x] Factor 3: Market Category (15 points max)
    - [x] Factor 4: Timing Anomalies (15 points max)
    - [x] Factor 5: Price/Conviction (15 points max)
    - [x] Factor 7: Market Metadata (20 points max)
    - [ ] Factor 6: PizzINT Correlation (30 points) - Deferred
  - [x] Wrote comprehensive tests (20/20 passing)
  - [x] Integrated with monitor
  - [x] Score normalization (0-100)
  - [x] Alert level assignment

- [x] ✅ **Wallet Pattern Analysis (Basic)**
  - [x] Analyze wallet trading patterns
  - [x] Detect new wallet alerts
  - [x] Calculate wallet age (from database)
  - [x] Detect timing patterns (off-hours, weekend)
  - [x] Win/loss tracking
  - [x] ROI calculation (database ready)

### Optional Enhancements (Deferred)

- [ ] **PizzINT Data Scraper** (Future Phase 3+)
  - [ ] Research PizzINT website structure
  - [ ] Build scraper with Selenium/BeautifulSoup
  - [ ] Store operational intelligence data
  - [ ] Calculate activity baselines
  - [ ] Detect activity spikes
  - [ ] Schedule periodic scraping

- [ ] **Temporal Correlation Engine** (Future Phase 3+)
  - [ ] Correlate bet timing with PizzINT spikes
  - [ ] Calculate time deltas
  - [ ] Identify "smoking gun" patterns (bet before spike)
  - [ ] Weight correlation in suspicion score

- [ ] **Advanced Pattern Recognition** (Future Phase 3+)
  - [ ] ML-based anomaly detection
  - [ ] Complex pattern analysis
  - [ ] Clustering wallets by behavior

---

## Phase 4: Blockchain Verification ✅ CORE COMPLETE

### Completed Features

- [x] ✅ **Blockchain Integration**
  - [x] Set up Polygon Web3 connection
  - [x] Implement transaction verification by hash
  - [x] Build blockchain client module (600+ lines)
  - [x] Detect Tornado Cash / mixer funding
  - [x] Calculate actual wallet age from blockchain
  - [x] Verify trade amounts match blockchain (basic)
  - [x] Integrate with scoring system
  - [x] Optional enhancement (use_blockchain flag)

- [x] ✅ **On-Chain Forensics**
  - [x] Transaction verification
  - [x] Wallet age calculation
  - [x] Mixer detection (4 Tornado Cash contracts)
  - [x] Balance checking
  - [x] Transaction count tracking

### Optional Enhancements (Future Phase 4+)

- [ ] **Advanced Verification**
  - [ ] Add comprehensive blockchain tests
  - [ ] Implement CTF token contract event decoding
  - [ ] Cache blockchain results for performance
  - [ ] Integrate Polygonscan API for efficiency
  - [ ] Expand known mixers database
  - [ ] Add transaction graph analysis
  - [ ] Batch verification for multiple trades

---

## Phase 5: Alerts & Notifications ✅ COMPLETE

### Telegram Bot ✅ COMPLETE

- [x] ✅ Build Telegram bot handler
  - [x] Created `alerts/telegram_bot.py` (410 lines)
  - [x] TelegramAlertBot class with full functionality
  - [x] AlertRateLimiter class for spam prevention
  - [x] Async/sync bridge for monitor integration
  - [x] Error handling and logging
- [x] ✅ Create alert message templates
  - [x] Created `alerts/templates.py` (294 lines)
  - [x] Telegram alert message formatting
  - [x] Bot command responses (/start, /help, /status, /stats)
  - [x] HTML email templates
- [x] ✅ Implement alert levels:
  - [x] WATCH (50-69) - Telegram alert (rate limited)
  - [x] SUSPICIOUS (70-84) - Telegram + Email alerts
  - [x] CRITICAL (85-100) - Telegram (bypasses rate limits) + Email
- [x] ✅ Add alert rate limiting (prevent spam)
  - [x] Max 10 alerts per hour
  - [x] Min 60 seconds between alerts
  - [x] CRITICAL alerts always bypass
  - [x] Automatic history cleanup
- [x] ✅ Test Telegram delivery
  - [x] Created `scripts/test_telegram_bot.py` (257 lines)
  - [x] Message formatting test
  - [x] Bot configuration check
  - [x] Optional delivery test
- [x] ✅ Integration with monitoring system
  - [x] Integrated with `monitor.py`
  - [x] Automatic alert sending after scoring
  - [x] Error handling for alert failures

### Email Alerts ✅ COMPLETE

- [x] ✅ Set up SMTP configuration
  - [x] Added SMTP settings to config
  - [x] TLS encryption support
  - [x] Gmail App Password support
- [x] ✅ Create HTML email templates
  - [x] Professional HTML layout with CSS
  - [x] Plain text fallback
  - [x] Alert level color coding
- [x] ✅ Implement email sending
  - [x] Created `alerts/email_alerts.py` (420 lines)
  - [x] EmailAlertService class
  - [x] Multi-recipient support
  - [x] Error handling
- [x] ✅ Test email delivery
  - [x] Created `scripts/test_email_alerts.py` (350 lines)
  - [x] Configuration validation
  - [x] SMTP authentication test
  - [x] Test email sending
- [x] ✅ Integration with monitoring system
  - [x] Emails sent for SUSPICIOUS and CRITICAL alerts
  - [x] Automatic delivery after scoring

### Alert History Tracking ✅ COMPLETE

- [x] ✅ Create alert history tracking
  - [x] Alert model already exists in database
  - [x] Added storage methods to DataStorageService
  - [x] store_alert() method creates alert records
- [x] ✅ Store alerts in database with status
  - [x] Alert level, type, and message stored
  - [x] Evidence stored as JSON
  - [x] Links to trade and wallet maintained
- [x] ✅ Track alert delivery status (sent/failed)
  - [x] telegram_sent and email_sent flags
  - [x] update_alert_notification_status() method
  - [x] Automatic updates after delivery
- [x] ✅ Add alert timestamps
  - [x] created_at timestamp
  - [x] reviewed_at timestamp (for review workflow)

### Alert Management

- [ ] Build alert review interface
- [ ] Add alert status tracking (NEW, REVIEWED, DISMISSED)
- [ ] Implement alert search/filter
- [ ] Add alert notes/comments
- [ ] Create alert statistics

---

## Phase 6: Web Dashboard & Deployment ✅ COMPLETE

### Core Features

- [x] ✅ Set up Streamlit dashboard
- [x] ✅ Create dashboard layout with navigation
- [x] ✅ Overview page with metrics
- [x] ✅ Alert Feed page with filtering
- [x] ✅ Trade History page
- [x] ✅ Wallet Analysis page
- [x] ✅ Statistics page
- [x] ✅ Settings page

### Visualizations

- [x] ✅ Activity chart (trades per hour)
- [x] ✅ Score distribution histogram
- [x] ✅ Daily activity timeline
- [x] ✅ Alert level pie chart

### Features

- [x] ✅ Filtering by score, time period
- [x] ✅ Sorting options
- [x] ✅ Pagination for large datasets
- [x] ✅ Search functionality

### Railway Deployment (Jan 16, 2026)

- [x] ✅ Created Dockerfile for production
- [x] ✅ Created Railway configuration (railway.toml, railway.json, Procfile)
- [x] ✅ Added PostgreSQL database connection
- [x] ✅ Added DNS retry logic for Railway private networking
- [x] ✅ Fixed null market_id validation
- [x] ✅ Added psycopg2-binary to requirements.txt
- [x] ✅ Pushed code to GitHub repository
- [x] ✅ Dashboard and monitor services deployed

### Code Quality Fixes Applied (Jan 14, 2026)

- [x] ✅ Fixed SQL injection in dashboard search
- [x] ✅ Added input validation to blockchain methods
- [x] ✅ Added blockchain scanning limits (reduced API calls)
- [x] ✅ Fixed race condition in monitor polling
- [x] ✅ Fixed transaction boundaries in database storage
- [x] ✅ Replaced inefficient queries with SQL aggregations
- [x] ✅ Added pagination to alerts page
- [x] ✅ Fixed timestamp conversion (int → datetime)
- [x] ✅ Added blacklist for sports/esports false positives
- [x] ✅ Added word boundary matching for short keywords
- [x] ✅ Fixed API field mappings in storage
- [x] ✅ Added bet direction normalization (Yes/No/Up/Down → YES/NO)
- [x] ✅ Improved IntegrityError logging for debugging

### Future Enhancements (Nice to Have)

- [ ] Network Patterns page
- [ ] Scatter plot: bet size vs suspicion score
- [ ] Heatmap: trading activity by hour/day
- [ ] Network graph: wallet relationships
- [ ] Export data (CSV, JSON)
- [ ] Dark mode
- [ ] Authentication/authorization

---

## Phase 7: Suspicious Wins Detection 🔄 PLANNING

**Technical Specification:** `docs/SUSPICIOUS_WINS_SPEC.md` (660 lines)

### Completed (Resolution Detection Prep)

- [x] ✅ Created technical specification document
- [x] ✅ Added `infer_resolution_from_prices()` to BlockchainClient
- [x] ✅ Fixed JSON string parsing for API responses
- [x] ✅ Tested price inference with live Polymarket data
- [x] ✅ Confirmed blockchain queries don't work (using price inference instead)

### Database Schema Changes

- [ ] Create `market_resolutions` table
  - [ ] market_id, resolved_at, winning_outcome, outcome_prices
  - [ ] resolution_source (API vs blockchain)
- [ ] Create `wallet_win_history` table
  - [ ] trade_id, wallet_address, market_id
  - [ ] won (boolean), profit_loss_usd, payout_usd
  - [ ] resolution_delay_hours
- [ ] Add win tracking fields to `wallet_metrics`
  - [ ] total_wins, total_losses, win_rate
  - [ ] geopolitical_wins, geopolitical_win_rate
  - [ ] avg_profit_per_win, largest_win
- [ ] Create Alembic migration

### Market Resolution Monitoring

- [ ] Create `ResolutionMonitor` class
  - [ ] Poll Polymarket API for resolved markets
  - [ ] Use price inference (winner price → ~1.0)
  - [ ] Handle partial resolutions
- [ ] Create `ResolutionStorage` service
  - [ ] Store resolutions to database
  - [ ] Avoid duplicate processing
- [ ] Schedule polling (every 5 minutes)

### Win/Loss Calculation

- [ ] Create `WinLossCalculator` class
  - [ ] Match trades to resolved markets
  - [ ] Calculate win/loss per trade
  - [ ] Calculate profit/loss in USD
- [ ] Update wallet metrics after resolution
- [ ] Track win streaks

### Suspicious Win Scoring

- [ ] Create `SuspiciousWinScorer` class
- [ ] Implement scoring factors:
  - [ ] Overall win rate (suspicious if >70%)
  - [ ] Geopolitical win rate (suspicious if >75%)
  - [ ] Profit concentration (few big wins)
  - [ ] Win streak patterns
  - [ ] Pre-event timing (bet close to resolution)
  - [ ] Bet size on winning trades
- [ ] Define alert levels:
  - [ ] WATCH_WIN (60-74 points)
  - [ ] SUSPICIOUS_WIN (75-89 points)
  - [ ] CRITICAL_WIN (90-100 points)

### Integration

- [ ] Add win alerts to Telegram bot
- [ ] Add win alerts to email system
- [ ] Create dashboard page for suspicious winners
- [ ] Add "Top Winners" leaderboard

### Testing

- [ ] Unit tests for resolution detection
- [ ] Unit tests for win/loss calculation
- [ ] Unit tests for suspicious win scoring
- [ ] Integration test with live data

---

## Phase 8: Validation & Optimization (Future)

- [ ] Collect historical data for backtesting
- [ ] Backtest prediction accuracy
- [ ] Calculate success metrics:
  - [ ] Prediction accuracy (target: >70%)
  - [ ] Lead time (target: 24-48 hours)
  - [ ] False positive rate (target: <25%)
- [ ] Optimize scoring weights based on results
- [ ] Performance optimization
- [ ] Security audit
- [ ] Documentation review
- [ ] Monitoring setup
- [ ] Backup strategy

---

## Testing & Quality Assurance

### Unit Tests Needed

- [x] API client tests (13/13 passing)
- [x] Config tests (basic coverage)
- [ ] Database model tests
- [ ] Repository tests
- [ ] Storage service tests
- [ ] Monitor tests (currently 0%)
- [ ] Scoring algorithm tests
- [ ] Pattern detection tests

### Integration Tests Needed

- [x] API connection test (working)
- [ ] Database integration test
- [ ] End-to-end trade flow test
- [ ] Alert delivery test
- [ ] Blockchain verification test

### Performance Tests

- [ ] Database query performance
- [ ] API rate limit handling
- [ ] Concurrent trade processing
- [ ] Memory usage monitoring
- [ ] CPU usage profiling

---

## Documentation

### Code Documentation

- [x] API client docstrings
- [x] Config documentation
- [x] Database models documented
- [x] Repository layer documented
- [ ] Analysis module documentation (when built)
- [ ] Alert system documentation (when built)

### User Documentation

- [x] README.md (current)
- [x] PROJECT_SUMMARY.md (updated)
- [x] Installation guide
- [ ] User guide
- [ ] API documentation
- [ ] Deployment guide
- [ ] Troubleshooting guide

### Developer Documentation

- [x] Phase 1 completion docs
- [x] Critical fixes documentation
- [ ] Phase 2 completion docs (pending)
- [ ] Architecture diagram
- [ ] Database schema diagram
- [ ] Data flow diagram
- [ ] Contributing guide

---

## Code Quality Improvements

### High Priority Issues (From Code Review)

- [ ] 🔥 Add caching for market data (reduce API calls)
- [ ] 🔥 Write tests for monitor.py (currently 0% coverage)
- [ ] 🔥 Add error scenario tests (timeout, invalid responses)
- [ ] ⚠️ Fix race condition in timestamp handling
- [ ] ⚠️ Implement proper exponential backoff

### Medium Priority Issues

- [ ] Extract duplicated code into helper methods
- [ ] Add request ID logging for debugging
- [ ] Document actual API response formats
- [ ] Add metrics collection (call counts, response times)
- [ ] Implement rate limiting prevention (not just handling)

### Low Priority Issues

- [ ] Optimize session configuration
- [ ] Add user agent header
- [ ] Create constants for magic numbers
- [ ] Add detailed docstring examples
- [ ] Code coverage >80%

---

## Infrastructure & DevOps

### Development

- [x] ✅ Virtual environment setup
- [x] ✅ Dependencies managed (requirements.txt)
- [x] ✅ Git repository initialized
- [x] ✅ SQLite database for development
- [x] ✅ Docker containerization (Dockerfile)

### Production (Railway) ✅

- [x] ✅ PostgreSQL setup (Railway managed)
- [x] ✅ Production configuration (railway.toml, railway.json)
- [x] ✅ Environment variables management (Railway secrets)
- [x] ✅ Secrets management (Railway)
- [x] ✅ Logging configuration
- [x] ✅ GitHub repository: https://github.com/pjdevos/InsiderTradingDetection
- [ ] Monitoring setup (Prometheus/Grafana?)
- [ ] Error tracking (Sentry?)
- [ ] Backup strategy
- [ ] Disaster recovery plan

### CI/CD

- [x] ✅ GitHub repository connected
- [x] ✅ Railway auto-deploy on push
- [ ] GitHub Actions workflow
- [ ] Automated testing on commit
- [ ] Code quality checks (pylint, black)
- [ ] Security scanning

---

## Security & Compliance

- [x] API keys in environment variables
- [x] Input validation implemented
- [x] No hardcoded credentials
- [ ] Rate limiting to prevent abuse
- [ ] Authentication for dashboard
- [ ] Audit logging
- [ ] Data retention policy
- [ ] GDPR compliance review (if applicable)
- [ ] Security penetration testing

---

## Nice to Have Features

### Analytics

- [ ] Advanced pattern detection (ML/AI?)
- [ ] Anomaly detection
- [ ] Clustering wallets by behavior
- [ ] Prediction confidence scores
- [ ] Accuracy tracking over time

### Integrations

- [ ] Twitter sentiment analysis
- [ ] News API integration
- [ ] Additional blockchain networks
- [ ] More prediction markets (not just Polymarket)

### User Features

- [ ] Custom alerts
- [ ] Watchlists
- [ ] Email digest reports
- [ ] Mobile app
- [ ] API for external integrations

---

## Known Issues & Bugs

### 🔥 Code Review: Post-Incident Audit (Jan 27, 2026)

**Context:** Two production failures were discovered — a DB schema mismatch (stamped migration skipped column additions) and a pipeline crash on trades with missing wallet addresses. Both have been patched, but a broader review is needed to catch similar issues elsewhere.

**Assign to:** `code-reviewer` agent

- [ ] **Migration safety audit**
  - Review `alembic/env.py` `check_and_stamp_if_needed()` — verify the stamp logic cannot skip migrations that add columns/constraints (the root cause of `trade_result` missing)
  - Verify all migration files in `alembic/versions/` are idempotent (use `IF NOT EXISTS` / existence checks) so re-runs and stamped DBs don't break
  - Confirm the migration chain (`d3080b390a2a` → `add_suspicious_wins` → `add_monitor_tables` → `fix_missing_columns`) is sound and each revision's `down_revision` is correct
  - Check that `fix_missing_suspicious_wins_columns.py` covers every column, table, index, and constraint from `add_suspicious_wins_tables.py`

- [ ] **Null/missing field resilience across the pipeline**
  - Trace every field extracted from the Polymarket API in `src/api/monitor.py` (`wallet_address`, `market_id`, `transaction_hash`, `bet_size_usd`, `timestamp`, `outcome`, `price`) — verify each has a guard or fallback before reaching the DB layer
  - Review `src/database/storage.py` `store_trade()` — check that all fields in `db_trade_data` are safe when the API returns `None` (not just `wallet_address`)
  - Review `src/database/repository.py` `create_trade()` — confirm it handles `None` wallet_address gracefully (line 40 does `trade.wallet_address[:10]` which will crash on `None`)
  - Review `src/analysis/scoring.py` `calculate_score()` — verify all extracted fields (`bet_size_usd`, `wallet_address`, `timestamp`, `bet_price`, `bet_direction`) have safe defaults when missing

- [ ] **Validator vs caller contract**
  - Review `src/database/validators.py` `DatabaseInputValidator` — check whether strict validators (that raise on None/empty) are always called behind guards, or if any code path can reach them with invalid data
  - Specifically check all callers of `validate_wallet_address()`, `validate_market_id()`, and `validate_transaction_hash()`

- [ ] **ORM model vs DB schema alignment**
  - Compare every column in `src/database/models.py` against what the full migration chain actually creates — flag any column present in the ORM but not guaranteed by migrations
  - Check `nullable` and `default` values match between model definitions and migration `add_column` calls

---

### Current Issues (Jan 21, 2026)

1. **Dashboard Deprecation Warning** (Low Priority)
   - Streamlit `use_container_width` deprecated
   - Will be removed after 2025-12-31
   - Needs migration to `width='stretch'`

2. **Blockchain Query Limitations** (Info)
   - Conditional Tokens contract queries fail for Polymarket
   - Using price inference as workaround (works well)

### Resolved Issues ✅

**Jan 27, 2026 (Production Fixes):**
1. ~~DB schema mismatch: `trade_result` column missing from `trades`~~ → Added backfill migration `fix_missing_columns` that idempotently adds all skipped columns, tables, indexes, and constraints
2. ~~Pipeline crash on missing wallet address~~ → Added guards in `scoring.py` and `storage.py` to skip wallet metrics for invalid/missing addresses

**Jan 19, 2026 (Resolution Detection):**
1. ~~JSON string parsing in price inference~~ → Added JSON.loads() for API response

**Jan 16, 2026 (Railway Deployment):**
1. ~~Railway DNS resolution delays~~ → Added retry logic with exponential backoff
2. ~~Missing psycopg2~~ → Added psycopg2-binary to requirements.txt
3. ~~Build failures~~ → Created custom Dockerfile
4. ~~Null market_id errors~~ → Added validation to skip invalid markets

**Jan 14, 2026 (Code Quality):**
1. ~~SQL injection in dashboard search~~ → Fixed with escape characters
2. ~~Missing input validation in blockchain~~ → Added `_validate_address()`, `_validate_tx_hash()`
3. ~~Blockchain scanning resource exhaustion~~ → Added limits, reduced API calls from ~130 to ~6
4. ~~Race condition in monitor polling~~ → Capture time before fetch, added overlap buffer
5. ~~Missing transaction boundaries~~ → Pass session through storage methods
6. ~~Inefficient database queries~~ → SQL aggregations, pagination
7. ~~Timestamp int→datetime conversion~~ → Fixed in storage.py

### Future Considerations

- JSON columns not ideal for complex queries (consider separate tables)
- No caching layer (consider Redis for market data)
- No queue system for async processing (consider Celery/RabbitMQ)

---

## Immediate Next Steps

### Current Priority: Implement Suspicious Wins Detection (Phase 7)

1. **Database Schema** 🔥
   - [ ] Create `market_resolutions` table
   - [ ] Create `wallet_win_history` table
   - [ ] Add win tracking to `wallet_metrics`
   - [ ] Generate Alembic migration

2. **Resolution Monitoring**
   - [ ] Create `ResolutionMonitor` class
   - [ ] Implement market polling logic
   - [ ] Store resolutions to database

3. **Win/Loss Calculation**
   - [ ] Create `WinLossCalculator` class
   - [ ] Match trades to resolutions
   - [ ] Calculate profit/loss

4. **Documentation Updates**
   - [x] ✅ Update TODO.md
   - [x] ✅ Update PROJECT_SUMMARY.md
   - [x] ✅ Technical spec: docs/SUSPICIOUS_WINS_SPEC.md

---

## Long-Term Roadmap

### Q1 2026 (January-March) - IN PROGRESS
- ✅ Phase 1: API Integration (Complete - Jan 12)
- ✅ Phase 2: Database Integration (Complete - Jan 13)
- ✅ Phase 3: Suspicion Scoring (Core Complete - Jan 13)
- ✅ Phase 4: Blockchain Verification (Core Complete - Jan 13)
- ✅ Phase 5: Alerts & Notifications (Complete - Jan 13)
- ✅ Phase 6: Web Dashboard & Deployment (Complete - Jan 16)
- 🔄 Phase 7: Suspicious Wins Detection (Planning - Jan 21)

### Q2 2026 (April-June)
- ⏳ Phase 7: Suspicious Wins (Implementation)
- ⏳ Phase 8: Validation & Optimization
- ⏳ Advanced pattern recognition

### Q3 2026 (July-September)
- ⏳ ML-based anomaly detection
- ⏳ PizzINT integration (if available)
- ⏳ Feature enhancements based on usage

### Q4 2026 (October-December)
- ⏳ Advanced analytics
- ⏳ Additional integrations
- ⏳ Scale and performance optimization

---

## Questions & Decisions Needed

- [x] ✅ PostgreSQL vs SQLite for production? → **PostgreSQL (Railway)**
- [x] ✅ Self-hosted vs cloud deployment? → **Railway cloud deployment**
- [x] ✅ Open source or proprietary? → **GitHub public repo**
- [ ] Monetization strategy (if any)?
- [ ] User access model (single user vs multi-user)?
- [ ] Data retention period?
- [ ] Alert frequency limits?

---

## Success Metrics

### Technical Metrics
- **API Uptime:** >99.5%
- **Alert Delivery:** <30 seconds
- **Database Query Speed:** <100ms average
- **Test Coverage:** >80%
- **Code Quality:** A grade (pylint)

### Prediction Metrics
- **Accuracy:** >70% (target)
- **Lead Time:** 24-48 hours average
- **False Positive Rate:** <25%
- **Coverage:** >95% of $10k+ geopolitical bets tracked

### Performance Metrics
- **Memory Usage:** <500MB baseline
- **CPU Usage:** <20% average
- **Disk I/O:** <10MB/s
- **Network:** <1MB/s average

---

**Note:** This is a living document. Update regularly as tasks are completed and new requirements emerge.

**Last Updated:** January 27, 2026
