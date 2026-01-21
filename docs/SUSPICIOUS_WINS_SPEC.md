# Technical Specification: Suspicious Wins Monitoring

**Version:** 1.0
**Date:** January 2026
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose
Extend the Insider Trading Detection System to track market resolutions and identify users who consistently WIN on geopolitical prediction markets, not just those who make suspicious bets.

### 1.2 Problem Statement
Current system detects suspicious **betting patterns** but cannot determine if those bets were **correct**. A wallet that places suspicious bets AND consistently wins provides stronger evidence of insider knowledge than suspicious bets alone.

### 1.3 Key Insight from API Testing
- **Blockchain queries fail** for most Polymarket conditions (not prepared on-chain)
- **Price inference works**: When markets resolve, winning outcome price → ~1.0, losing → ~0.0
- **Primary method**: Use `outcomePrices` from Polymarket API to infer outcomes

---

## 2. Data Sources

### 2.1 Resolution Data (Primary: API Price Inference)

**Source:** Polymarket Gamma API `/markets` endpoint

**Fields Used:**
| Field | Type | Purpose |
|-------|------|---------|
| `closed` | boolean | Market halted (prerequisite for resolution) |
| `outcomePrices` | JSON string | `["0.001", "0.999"]` indicates NO won |
| `outcomes` | array | `["Yes", "No"]` - outcome labels |
| `endDate` | datetime | Scheduled resolution date |

**Resolution Inference Logic:**
```
IF closed = true AND max(outcomePrices) >= 0.95:
    winning_index = index of max price
    winning_outcome = outcomes[winning_index]  # "Yes" or "No"
    resolved = true
ELSE:
    resolved = false
```

### 2.2 Resolution Data (Backup: Blockchain)

**Source:** Polygon Conditional Tokens Contract
**Address:** `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`
**Method:** `payoutNumerators(bytes32 conditionId)`

**Note:** Most conditions return "execution reverted" - use only as fallback verification for high-stakes cases.

### 2.3 Trade Data (Existing)

**Source:** Current `trades` table

**Fields Needed for Win/Loss:**
| Field | Purpose |
|-------|---------|
| `market_id` | Link to market resolution |
| `bet_direction` | "YES" or "NO" |
| `bet_size_usd` | Calculate profit/loss |
| `bet_price` | Entry price for P&L calculation |
| `timestamp` | Calculate hours before resolution |

---

## 3. Database Schema Changes

### 3.1 New Table: `market_resolutions`

```sql
CREATE TABLE market_resolutions (
    id SERIAL PRIMARY KEY,

    -- Market identification
    market_id VARCHAR(100) NOT NULL UNIQUE,
    condition_id VARCHAR(66),

    -- Resolution data
    resolved_at TIMESTAMP WITH TIME ZONE,
    winning_outcome VARCHAR(10) NOT NULL,  -- "YES", "NO", "VOID"

    -- Confidence & source
    confidence FLOAT NOT NULL,  -- 0.0 to 1.0
    resolution_source VARCHAR(20) NOT NULL,  -- "price_inference", "blockchain", "manual"

    -- Raw data for audit
    final_yes_price FLOAT,
    final_no_price FLOAT,
    payout_numerators JSONB,  -- From blockchain if available

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT chk_winning_outcome CHECK (winning_outcome IN ('YES', 'NO', 'VOID')),
    CONSTRAINT chk_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE INDEX idx_resolutions_market ON market_resolutions(market_id);
CREATE INDEX idx_resolutions_resolved_at ON market_resolutions(resolved_at DESC);
CREATE INDEX idx_resolutions_outcome ON market_resolutions(winning_outcome);
```

### 3.2 Trade Table Modifications

**New Columns:**
```sql
ALTER TABLE trades ADD COLUMN trade_result VARCHAR(10);  -- WIN, LOSS, PENDING, VOID
ALTER TABLE trades ADD COLUMN profit_loss_usd FLOAT;
ALTER TABLE trades ADD COLUMN hours_before_resolution FLOAT;
ALTER TABLE trades ADD COLUMN resolution_id INTEGER REFERENCES market_resolutions(id);

CREATE INDEX idx_trades_result ON trades(trade_result);
CREATE INDEX idx_trades_hours_before ON trades(hours_before_resolution);
```

**Constraints:**
```sql
ALTER TABLE trades ADD CONSTRAINT chk_trade_result
    CHECK (trade_result IN ('WIN', 'LOSS', 'PENDING', 'VOID', NULL));
```

### 3.3 New Table: `wallet_win_history`

```sql
CREATE TABLE wallet_win_history (
    id SERIAL PRIMARY KEY,

    -- Relationships
    wallet_address VARCHAR(42) NOT NULL,
    market_id VARCHAR(100) NOT NULL,
    trade_id INTEGER REFERENCES trades(id),
    resolution_id INTEGER REFERENCES market_resolutions(id),

    -- Trade details (denormalized for query performance)
    bet_direction VARCHAR(3) NOT NULL,
    bet_size_usd FLOAT NOT NULL,
    bet_price FLOAT NOT NULL,

    -- Resolution details
    winning_outcome VARCHAR(10) NOT NULL,
    trade_result VARCHAR(10) NOT NULL,
    profit_loss_usd FLOAT,
    hours_before_resolution FLOAT,

    -- Context
    is_geopolitical BOOLEAN DEFAULT FALSE,
    suspicion_score_at_bet INTEGER,
    market_title TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT chk_win_result CHECK (trade_result IN ('WIN', 'LOSS', 'VOID'))
);

CREATE INDEX idx_win_history_wallet ON wallet_win_history(wallet_address);
CREATE INDEX idx_win_history_result ON wallet_win_history(wallet_address, trade_result);
CREATE INDEX idx_win_history_hours ON wallet_win_history(hours_before_resolution);
CREATE INDEX idx_win_history_geopolitical ON wallet_win_history(is_geopolitical, trade_result);
```

### 3.4 WalletMetrics Table Updates

**Existing fields to populate:**
```sql
-- These fields already exist but are currently NULL
winning_trades        -- Count of WIN results
losing_trades         -- Count of LOSS results
win_rate             -- winning / (winning + losing)
geopolitical_accuracy -- Win rate on geopolitical markets only
avg_hours_before_resolution  -- Average timing
```

**New fields:**
```sql
ALTER TABLE wallet_metrics ADD COLUMN geopolitical_wins INTEGER DEFAULT 0;
ALTER TABLE wallet_metrics ADD COLUMN geopolitical_losses INTEGER DEFAULT 0;
ALTER TABLE wallet_metrics ADD COLUMN total_profit_loss_usd FLOAT DEFAULT 0;
ALTER TABLE wallet_metrics ADD COLUMN early_win_count INTEGER DEFAULT 0;  -- Wins on bets <48h before resolution
ALTER TABLE wallet_metrics ADD COLUMN win_streak_max INTEGER DEFAULT 0;
ALTER TABLE wallet_metrics ADD COLUMN last_resolution_check TIMESTAMP WITH TIME ZONE;
```

---

## 4. New Components

### 4.1 Resolution Monitor Service

**File:** `src/api/resolution_monitor.py`

**Class:** `ResolutionMonitor`

**Responsibilities:**
1. Poll Polymarket API for closed markets
2. Infer resolution outcomes from prices
3. Store resolutions in database
4. Trigger win/loss calculation for affected trades

**Methods:**
```python
class ResolutionMonitor:
    def __init__(self, api_client, poll_interval_minutes=30):
        """Initialize with API client and polling interval"""

    def poll_closed_markets(self, limit=100) -> List[Dict]:
        """Fetch recently closed markets from API"""

    def infer_resolution(self, market_data: Dict) -> Optional[Dict]:
        """Infer resolution from market's outcomePrices"""

    def store_resolution(self, resolution_data: Dict) -> MarketResolution:
        """Store resolution in database"""

    def get_unresolved_markets(self) -> List[str]:
        """Get market_ids with trades but no resolution"""

    def process_new_resolutions(self) -> int:
        """Main loop: find and process new resolutions"""
```

**Polling Strategy:**
- Check every 30 minutes for newly closed markets
- Only process geopolitical markets (filter by stored market data)
- Use `endDate` to prioritize markets near resolution
- Backfill: On startup, check all markets with pending trades

### 4.2 Win/Loss Calculator Service

**File:** `src/analysis/win_calculator.py`

**Class:** `WinLossCalculator`

**Responsibilities:**
1. Match trades to market resolutions
2. Determine WIN/LOSS/VOID for each trade
3. Calculate profit/loss in USD
4. Update trades and wallet metrics

**Methods:**
```python
class WinLossCalculator:
    def calculate_trade_result(self, trade: Trade, resolution: MarketResolution) -> Dict:
        """
        Determine trade outcome

        Returns:
            {
                'result': 'WIN' | 'LOSS' | 'VOID',
                'profit_loss_usd': float,
                'hours_before_resolution': float
            }
        """

    def process_market_resolution(self, resolution: MarketResolution) -> int:
        """Process all trades for a resolved market, return count"""

    def update_wallet_metrics(self, wallet_address: str) -> WalletMetrics:
        """Recalculate wallet win metrics"""

    def calculate_profit_loss(self, bet_size: float, bet_price: float,
                              bet_direction: str, winning_outcome: str) -> float:
        """
        Calculate P&L for a trade

        Formula:
        - If WIN: profit = bet_size * (1 - bet_price) / bet_price
        - If LOSS: loss = -bet_size
        """
```

**Win/Loss Logic:**
```
IF resolution.winning_outcome == 'VOID':
    result = 'VOID'
    profit_loss = 0
ELIF trade.bet_direction == resolution.winning_outcome:
    result = 'WIN'
    profit_loss = bet_size * (1 - bet_price) / bet_price
ELSE:
    result = 'LOSS'
    profit_loss = -bet_size
```

### 4.3 Suspicious Win Scorer

**File:** `src/analysis/win_scoring.py`

**Class:** `SuspiciousWinScorer`

**Scoring Factors (100 points max):**

| Factor | Points | Threshold | Description |
|--------|--------|-----------|-------------|
| Win Rate Anomaly | 30 | >60% on 5+ markets | Significantly above 50% baseline |
| Timing Pattern | 25 | >50% wins on bets <48h | Consistently bets close to resolution |
| Geopolitical Accuracy | 20 | >70% on geopolitical | High accuracy on insider-prone markets |
| Profit Consistency | 15 | >$10k profit, >60% win | Consistent profitability |
| Low Volume Accuracy | 10 | >80% on <20 trades | High accuracy with few bets (harder to fake) |

**Methods:**
```python
class SuspiciousWinScorer:
    def calculate_win_score(self, wallet_address: str) -> Dict:
        """
        Calculate suspicious win score for a wallet

        Returns:
            {
                'total_score': int (0-100),
                'alert_level': 'WATCH' | 'SUSPICIOUS' | 'CRITICAL' | None,
                'breakdown': {
                    'win_rate_anomaly': {'score': int, 'max': 30, 'reason': str},
                    'timing_pattern': {'score': int, 'max': 25, 'reason': str},
                    ...
                },
                'stats': {
                    'total_resolved': int,
                    'wins': int,
                    'losses': int,
                    'win_rate': float,
                    'avg_hours_before_resolution': float,
                    'total_profit_loss': float
                }
            }
        """

    def get_alert_level(self, score: int) -> Optional[str]:
        """Map score to alert level"""
        # WATCH: 50+
        # SUSPICIOUS: 70+
        # CRITICAL: 85+
```

**Alert Thresholds:**
```python
WIN_ALERT_THRESHOLDS = {
    'WATCH': 50,       # Win rate >60% OR timing pattern detected
    'SUSPICIOUS': 70,  # Win rate >70% AND multiple factors
    'CRITICAL': 85     # Win rate >80% OR timing+geopolitical combo
}
```

### 4.4 Combined Scoring Integration

**Modify:** `src/analysis/scoring.py`

**New Combined Score:**
```python
def calculate_combined_score(trade_data, wallet_address) -> Dict:
    """
    Combine bet-time suspicion with historical win analysis

    Total = (Bet Score * 0.6) + (Win Score * 0.4)

    But: If wallet has CRITICAL win score, minimum combined = 70
    """
```

---

## 5. API & Dashboard Updates

### 5.1 New API Endpoints (if using FastAPI)

```python
# Resolution data
GET /api/resolutions                    # List recent resolutions
GET /api/resolutions/{market_id}        # Single resolution details

# Win analysis
GET /api/wallets/{address}/win-history  # Wallet's trade results
GET /api/wallets/{address}/win-score    # Suspicious win score

# Leaderboard
GET /api/leaderboard/winners            # Top winning wallets
GET /api/leaderboard/suspicious-winners # High win rate + suspicious
```

### 5.2 Dashboard Updates

**New Page: "Win Analysis"**
- Table of resolved markets with outcomes
- Win/loss statistics by wallet
- Timing analysis visualization (bets vs resolution time)

**Enhanced Wallet View:**
- Win rate and profit/loss stats
- Trade history with outcomes (WIN/LOSS/PENDING)
- Suspicious win score breakdown

**New Alerts Section:**
- "Suspicious Winner" alerts (separate from "Suspicious Bet" alerts)
- Combined view showing wallets that are suspicious AND winning

---

## 6. Data Flow

### 6.1 Resolution Detection Flow

```
┌─────────────────┐
│ Polymarket API  │
│ /markets?closed │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ResolutionMonitor│
│ poll_closed()   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ infer_resolution│
│ from prices     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Store in        │
│ market_resolutions│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ WinLossCalculator│
│ process trades  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Update trades   │
│ wallet_metrics  │
│ wallet_win_history│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SuspiciousWinScorer│
│ check for alerts│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Send Alert      │
│ (if threshold)  │
└─────────────────┘
```

### 6.2 Trade Lifecycle

```
1. Trade Detected
   └─► trade_result = 'PENDING'

2. Bet-Time Scoring
   └─► suspicion_score calculated
   └─► Alert sent if threshold met

3. Market Closes
   └─► ResolutionMonitor detects

4. Resolution Inferred
   └─► market_resolutions record created

5. Win/Loss Calculated
   └─► trade_result = 'WIN' | 'LOSS' | 'VOID'
   └─► profit_loss_usd calculated
   └─► hours_before_resolution calculated

6. Wallet Metrics Updated
   └─► win_rate recalculated
   └─► geopolitical_accuracy updated

7. Win Score Calculated
   └─► SuspiciousWinScorer analyzes wallet
   └─► Alert sent if threshold met
```

---

## 7. Implementation Phases

### Phase 1: Database Schema (Week 1)
- [ ] Create Alembic migration for new tables
- [ ] Add new columns to trades table
- [ ] Add new columns to wallet_metrics table
- [ ] Test migration on development database

### Phase 2: Resolution Monitor (Week 1-2)
- [ ] Implement ResolutionMonitor class
- [ ] Implement price inference (already done in BlockchainClient)
- [ ] Add resolution storage service
- [ ] Create backfill script for historical markets

### Phase 3: Win/Loss Calculator (Week 2)
- [ ] Implement WinLossCalculator class
- [ ] Add profit/loss calculation
- [ ] Add timing calculation
- [ ] Integrate with resolution monitor

### Phase 4: Win Scoring (Week 3)
- [ ] Implement SuspiciousWinScorer class
- [ ] Define scoring factors and weights
- [ ] Add alert generation for suspicious winners
- [ ] Integrate with existing alert system

### Phase 5: Dashboard & Testing (Week 3-4)
- [ ] Add Win Analysis page to dashboard
- [ ] Update Wallet view with win stats
- [ ] Add unit tests for all new components
- [ ] Integration testing with live data

### Phase 6: Deployment & Tuning (Week 4)
- [ ] Deploy to Railway
- [ ] Monitor for false positives/negatives
- [ ] Tune scoring thresholds based on real data
- [ ] Document operational procedures

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# test_resolution_monitor.py
- test_infer_resolution_yes_wins()
- test_infer_resolution_no_wins()
- test_infer_resolution_undetermined()
- test_infer_resolution_void()

# test_win_calculator.py
- test_calculate_win_result()
- test_calculate_loss_result()
- test_profit_loss_calculation()
- test_hours_before_resolution()

# test_win_scoring.py
- test_win_rate_anomaly_score()
- test_timing_pattern_score()
- test_combined_score()
- test_alert_thresholds()
```

### 8.2 Integration Tests

```python
# test_resolution_flow.py
- test_full_resolution_flow()
- test_backfill_historical_resolutions()
- test_wallet_metrics_update()
```

### 8.3 Manual Testing

1. **Historical Validation:**
   - Pick 10 known resolved markets
   - Verify price inference matches actual outcomes
   - Check profit/loss calculations

2. **Alert Testing:**
   - Create test wallet with known win pattern
   - Verify alert triggers at correct thresholds

---

## 9. Monitoring & Observability

### 9.1 Metrics to Track

| Metric | Description |
|--------|-------------|
| `resolutions_processed` | Count of market resolutions detected |
| `trades_resolved` | Count of trades with WIN/LOSS assigned |
| `win_alerts_sent` | Count of suspicious winner alerts |
| `avg_resolution_lag` | Time between market close and detection |
| `inference_confidence` | Average confidence of price inference |

### 9.2 Alerts

| Alert | Condition |
|-------|-----------|
| Resolution backlog | >100 unresolved markets with trades |
| Low inference confidence | Average confidence <0.90 |
| Win scorer errors | Error rate >1% |

---

## 10. Security Considerations

1. **Rate Limiting:** Respect Polymarket API limits during polling
2. **Data Integrity:** Verify resolution data before calculating P&L
3. **Audit Trail:** Log all resolution decisions for review
4. **False Positives:** Require minimum trade count before alerting

---

## 11. Open Questions

1. **Historical Depth:** How far back should we backfill resolutions?
2. **Void Handling:** How to handle voided/cancelled markets?
3. **Multi-Outcome Markets:** Support markets with >2 outcomes?
4. **Alert Fatigue:** How to prevent too many win alerts?

---

## 12. Appendix

### A. Example Resolution Inference

**Market:** "Will Trump win 2020 election?"
**API Response:**
```json
{
  "closed": true,
  "outcomePrices": "[\"0.00000004\", \"0.99999996\"]",
  "outcomes": ["Yes", "No"]
}
```

**Inference:**
```
yes_price = 0.00000004
no_price = 0.99999996
max_price = 0.99999996 (index 1)
confidence = 0.99999996
winning_outcome = outcomes[1] = "No"
```

### B. Profit/Loss Example

**Trade:**
- bet_direction: "YES"
- bet_size_usd: $1,000
- bet_price: 0.30 (30 cents per share)

**Resolution:** NO wins

**Calculation:**
```
result = LOSS (bet YES, NO won)
profit_loss = -$1,000 (lost entire bet)
```

**If YES had won:**
```
result = WIN
shares = $1,000 / $0.30 = 3,333 shares
payout = 3,333 * $1.00 = $3,333
profit = $3,333 - $1,000 = $2,333
```
