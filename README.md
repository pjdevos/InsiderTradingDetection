# Geopolitical Insider Trading Detection System

A comprehensive system that detects potential insider trading on Polymarket prediction markets by correlating large bets with operational signals (PizzINT Pentagon activity) and other OSINT indicators to predict geopolitical events 12-72 hours before they become public.

## Overview

This system combines multiple data sources to identify suspicious betting patterns that may indicate insider knowledge:

- **Financial Signals**: Polymarket API/blockchain data for large trades
- **Operational Signals**: PizzINT/Google Maps activity tracking Pentagon/government operations
- **Temporal Analysis**: Correlation between betting timing and real-world events

## Features

- Real-time monitoring of Polymarket trades via official APIs
- Blockchain verification on Polygon network
- Suspicion scoring engine for pattern detection
- PizzINT integration for operational signal tracking
- Automated alerts via Telegram and email
- Web dashboard for visualization and analysis

## Project Structure

```
InsiderTradingDetection/
├── src/
│   ├── api/              # Polymarket API integration
│   ├── blockchain/       # Polygon blockchain verification
│   ├── osint/           # PizzINT and OSINT data collection
│   ├── analysis/        # Suspicion scoring engine
│   ├── database/        # Database models and operations
│   ├── alerts/          # Telegram/email alert system
│   ├── dashboard/       # Web dashboard
│   └── config.py        # Configuration management
├── tests/               # Test suite
├── scripts/            # Utility scripts
├── docs/               # Documentation
├── data/               # Data storage
├── logs/               # Application logs
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
└── README.md
```

## Setup

### 1. Clone and Navigate

```bash
cd InsiderTradingDetection
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Edit `.env` file with your credentials:

```env
# Polymarket API
POLYMARKET_API_KEY=your_api_key_here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/geoint

# Blockchain (Polygon)
POLYGON_RPC_URL=https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY

# Alerts
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Thresholds
MIN_BET_SIZE_USD=10000
SUSPICION_THRESHOLD_CRITICAL=85
```

### 5. Database Setup

```bash
# Create database
createdb geoint

# Run migrations (when available)
alembic upgrade head
```

## Usage

### Start Monitoring

```bash
python -m src.main
```

### Run Dashboard

```bash
streamlit run src/dashboard/app.py
```

### Run Tests

```bash
pytest tests/
```

## Development Phases

- **Phase 1** (Week 1): Polymarket API Integration
- **Phase 2** (Week 2): Real-Time Monitoring
- **Phase 3** (Week 3): Scoring & Analysis Engine
- **Phase 4** (Week 4): Blockchain Verification
- **Phase 5** (Week 5-6): Alerts & Dashboard
- **Phase 6** (Week 7-8): Validation & Deployment

## Key Components

### 1. Polymarket API Client

- Monitors large trades (>$10k) on geopolitical markets
- Tracks wallet patterns and performance
- Categorizes markets by topic

### 2. Blockchain Verifier

- Verifies suspicious trades on Polygon
- Detects mixer funding and wallet age
- Provides forensic analysis

### 3. Scoring Engine

Calculates suspicion scores based on:
- Bet size and conviction
- Wallet history and performance
- Timing anomalies
- Market category
- PizzINT correlation

### 4. Alert System

- Telegram notifications for critical alerts (85+ score)
- Email reports for suspicious patterns (70+ score)
- Real-time monitoring dashboard

## Success Metrics

- **Technical**: >99.5% API uptime, <30s alert delivery
- **Accuracy**: >70% prediction accuracy, 24-48hr lead time
- **Coverage**: Track >95% of $10k+ geopolitical bets

## Contributing

1. Create a feature branch
2. Make changes with tests
3. Submit pull request

## Security

- Never commit `.env` files
- Keep API keys secure
- Use read-only blockchain access
- Review all alerts before public disclosure

## License

Internal use only

## Contact

For questions or issues, contact the development team.
