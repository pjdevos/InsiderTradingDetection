"""
Database models for Geopolitical Insider Trading Detection System
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    Text, ForeignKey, Index, CheckConstraint, JSON
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class Market(Base):
    """
    Market metadata from Polymarket
    """
    __tablename__ = 'markets'

    # Primary key
    market_id = Column(String(100), primary_key=True)

    # Market details
    slug = Column(String(200), unique=True, index=True)
    question = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(String(50))
    tags = Column(JSON)

    # Market state
    active = Column(Boolean, default=True, index=True)
    closed = Column(Boolean, default=False)
    volume_usd = Column(Float)
    liquidity_usd = Column(Float)

    # Timing
    created_at = Column(DateTime(timezone=True))
    close_time = Column(DateTime(timezone=True))
    resolved_at = Column(DateTime(timezone=True))

    # Analysis flags
    is_geopolitical = Column(Boolean, default=False, index=True)
    risk_keywords = Column(JSON)

    # Metadata
    last_updated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    trades = relationship("Trade", back_populates="market")

    def __repr__(self):
        return f"<Market(id={self.market_id}, question={self.question[:50]}...)>"


class Trade(Base):
    """
    Individual trade/bet on Polymarket
    """
    __tablename__ = 'trades'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # From Polymarket API
    api_trade_id = Column(String(100), unique=True)
    transaction_hash = Column(String(66), unique=True, nullable=False, index=True)
    block_number = Column(Integer)

    # Trade details
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    wallet_address = Column(String(42), nullable=False, index=True)
    market_id = Column(String(100), ForeignKey('markets.market_id'), nullable=False, index=True)

    # Trade specifics
    bet_size_usd = Column(Float, nullable=False)
    bet_direction = Column(String(3), nullable=False)  # YES/NO
    bet_price = Column(Float, nullable=False)
    outcome = Column(Text)

    # Market context (cached for performance)
    market_title = Column(Text, nullable=False)
    market_category = Column(String(50))
    market_slug = Column(String(200))
    market_volume_usd = Column(Float)
    market_liquidity_usd = Column(Float)
    market_close_date = Column(DateTime(timezone=True))

    # Analysis
    suspicion_score = Column(Integer, index=True)
    alert_level = Column(String(20))  # WATCH, SUSPICIOUS, CRITICAL

    # Verification
    blockchain_verified = Column(Boolean, default=False)
    api_source = Column(String(20))  # data_api, clob_api, blockchain

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    market = relationship("Market", back_populates="trades")

    # Constraints
    __table_args__ = (
        CheckConstraint('bet_size_usd > 0', name='check_bet_size_positive'),
        CheckConstraint("bet_direction IN ('YES', 'NO')", name='check_bet_direction'),
        CheckConstraint('suspicion_score >= 0 AND suspicion_score <= 100', name='check_score_range'),
        Index('idx_trades_timestamp_desc', timestamp.desc()),
        Index('idx_trades_suspicion_high', suspicion_score.desc()),
        Index('idx_trades_large_bets', bet_size_usd.desc()),
        Index('idx_trades_wallet_timestamp', wallet_address, timestamp.desc()),
    )

    def __repr__(self):
        return f"<Trade(id={self.id}, wallet={self.wallet_address[:10]}..., size=${self.bet_size_usd})>"


class WalletMetrics(Base):
    """
    Performance metrics and analysis for wallet addresses
    """
    __tablename__ = 'wallet_metrics'

    # Primary key
    wallet_address = Column(String(42), primary_key=True)

    # Trading statistics
    total_trades = Column(Integer, default=0)
    total_volume_usd = Column(Float, default=0.0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    pending_trades = Column(Integer, default=0)
    win_rate = Column(Float)  # Calculated: winning_trades / (winning_trades + losing_trades)

    # Timing patterns
    avg_hours_before_resolution = Column(Float)
    trades_outside_hours = Column(Integer, default=0)  # Trades outside 9am-9pm
    weekend_trades = Column(Integer, default=0)

    # Risk indicators
    suspicion_flags = Column(Integer, default=0)
    mixer_funded = Column(Boolean, default=False)
    wallet_age_days = Column(Integer)

    # Performance metrics
    roi = Column(Float)  # Return on investment %
    sharpe_ratio = Column(Float)  # Risk-adjusted returns
    avg_bet_size_usd = Column(Float)
    largest_bet_usd = Column(Float)

    # Geopolitical focus
    geopolitical_trades = Column(Integer, default=0)
    geopolitical_accuracy = Column(Float)

    # Metadata
    first_trade_at = Column(DateTime(timezone=True))
    last_trade_at = Column(DateTime(timezone=True))
    last_calculated = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # Indexes
    __table_args__ = (
        Index('idx_wallet_metrics_suspicion', suspicion_flags.desc()),
        Index('idx_wallet_metrics_win_rate', win_rate.desc()),
        Index('idx_wallet_metrics_volume', total_volume_usd.desc()),
    )

    def __repr__(self):
        return f"<WalletMetrics(wallet={self.wallet_address[:10]}..., trades={self.total_trades}, win_rate={self.win_rate})>"


class Alert(Base):
    """
    Generated alerts for suspicious trades
    """
    __tablename__ = 'alerts'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Alert details
    alert_level = Column(String(20), nullable=False, index=True)  # WATCH, SUSPICIOUS, CRITICAL
    alert_type = Column(String(50), nullable=False)  # LARGE_TRADE, NEW_WALLET, HIGH_SCORE, etc.

    # Related entities
    trade_id = Column(Integer, ForeignKey('trades.id'), index=True)
    wallet_address = Column(String(42), index=True)
    market_id = Column(String(100), ForeignKey('markets.market_id'))

    # Alert content
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    suspicion_score = Column(Integer, nullable=False)

    # Evidence
    evidence = Column(Text)  # JSON string with detailed evidence

    # Status
    status = Column(String(20), default='NEW')  # NEW, REVIEWED, DISMISSED, CONFIRMED
    reviewed_at = Column(DateTime(timezone=True))
    reviewed_by = Column(String(100))
    notes = Column(Text)

    # Notification status
    telegram_sent = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Indexes
    __table_args__ = (
        Index('idx_alerts_level_time', alert_level, created_at.desc()),
        Index('idx_alerts_status_time', status, created_at.desc()),
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, level={self.alert_level}, score={self.suspicion_score})>"


class PizzINTData(Base):
    """
    Operational intelligence data from PizzINT
    """
    __tablename__ = 'pizzint_data'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Location data
    location_name = Column(String(200), nullable=False)
    location_type = Column(String(50))  # Pentagon, State Dept, Military Base, etc.

    # Activity metrics
    activity_score = Column(Float, nullable=False)
    baseline_score = Column(Float)
    spike_detected = Column(Boolean, default=False, index=True)

    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)

    # Context
    notes = Column(Text)
    related_events = Column(Text)  # JSON string

    # Metadata
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Indexes
    __table_args__ = (
        Index('idx_pizzint_timestamp_desc', timestamp.desc()),
        Index('idx_pizzint_spikes', spike_detected, timestamp.desc()),
    )

    def __repr__(self):
        return f"<PizzINTData(location={self.location_name}, score={self.activity_score})>"
