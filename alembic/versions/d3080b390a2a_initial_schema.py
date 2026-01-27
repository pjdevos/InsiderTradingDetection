"""initial_schema

Revision ID: d3080b390a2a
Revises:
Create Date: 2026-01-13 01:14:42.726386

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3080b390a2a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind, table):
    return table in inspect(bind).get_table_names()


def _index_exists(bind, table, index_name):
    indexes = inspect(bind).get_indexes(table)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if not _table_exists(bind, 'markets'):
        op.create_table('markets',
        sa.Column('market_id', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=True),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=True),
        sa.Column('closed', sa.Boolean(), nullable=True),
        sa.Column('volume_usd', sa.Float(), nullable=True),
        sa.Column('liquidity_usd', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('close_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_geopolitical', sa.Boolean(), nullable=True),
        sa.Column('risk_keywords', sa.JSON(), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('market_id')
        )
        op.create_index(op.f('ix_markets_active'), 'markets', ['active'], unique=False)
        op.create_index(op.f('ix_markets_is_geopolitical'), 'markets', ['is_geopolitical'], unique=False)
        op.create_index(op.f('ix_markets_slug'), 'markets', ['slug'], unique=True)

    if not _table_exists(bind, 'pizzint_data'):
        op.create_table('pizzint_data',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('location_name', sa.String(length=200), nullable=False),
        sa.Column('location_type', sa.String(length=50), nullable=True),
        sa.Column('activity_score', sa.Float(), nullable=False),
        sa.Column('baseline_score', sa.Float(), nullable=True),
        sa.Column('spike_detected', sa.Boolean(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('related_events', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_pizzint_spikes', 'pizzint_data', ['spike_detected', sa.literal_column('timestamp DESC')], unique=False)
        op.create_index('idx_pizzint_timestamp_desc', 'pizzint_data', [sa.literal_column('timestamp DESC')], unique=False)
        op.create_index(op.f('ix_pizzint_data_spike_detected'), 'pizzint_data', ['spike_detected'], unique=False)
        op.create_index(op.f('ix_pizzint_data_timestamp'), 'pizzint_data', ['timestamp'], unique=False)

    if not _table_exists(bind, 'wallet_metrics'):
        op.create_table('wallet_metrics',
        sa.Column('wallet_address', sa.String(length=42), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.Column('total_volume_usd', sa.Float(), nullable=True),
        sa.Column('winning_trades', sa.Integer(), nullable=True),
        sa.Column('losing_trades', sa.Integer(), nullable=True),
        sa.Column('pending_trades', sa.Integer(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('avg_hours_before_resolution', sa.Float(), nullable=True),
        sa.Column('trades_outside_hours', sa.Integer(), nullable=True),
        sa.Column('weekend_trades', sa.Integer(), nullable=True),
        sa.Column('suspicion_flags', sa.Integer(), nullable=True),
        sa.Column('mixer_funded', sa.Boolean(), nullable=True),
        sa.Column('wallet_age_days', sa.Integer(), nullable=True),
        sa.Column('roi', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('avg_bet_size_usd', sa.Float(), nullable=True),
        sa.Column('largest_bet_usd', sa.Float(), nullable=True),
        sa.Column('geopolitical_trades', sa.Integer(), nullable=True),
        sa.Column('geopolitical_accuracy', sa.Float(), nullable=True),
        sa.Column('first_trade_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_trade_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_calculated', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('wallet_address')
        )
        op.create_index('idx_wallet_metrics_suspicion', 'wallet_metrics', [sa.literal_column('suspicion_flags DESC')], unique=False)
        op.create_index('idx_wallet_metrics_volume', 'wallet_metrics', [sa.literal_column('total_volume_usd DESC')], unique=False)
        op.create_index('idx_wallet_metrics_win_rate', 'wallet_metrics', [sa.literal_column('win_rate DESC')], unique=False)

    if not _table_exists(bind, 'trades'):
        op.create_table('trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('api_trade_id', sa.String(length=100), nullable=True),
        sa.Column('transaction_hash', sa.String(length=66), nullable=False),
        sa.Column('block_number', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('wallet_address', sa.String(length=42), nullable=False),
        sa.Column('market_id', sa.String(length=100), nullable=False),
        sa.Column('bet_size_usd', sa.Float(), nullable=False),
        sa.Column('bet_direction', sa.String(length=3), nullable=False),
        sa.Column('bet_price', sa.Float(), nullable=False),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('market_title', sa.Text(), nullable=False),
        sa.Column('market_category', sa.String(length=50), nullable=True),
        sa.Column('market_slug', sa.String(length=200), nullable=True),
        sa.Column('market_volume_usd', sa.Float(), nullable=True),
        sa.Column('market_liquidity_usd', sa.Float(), nullable=True),
        sa.Column('market_close_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suspicion_score', sa.Integer(), nullable=True),
        sa.Column('alert_level', sa.String(length=20), nullable=True),
        sa.Column('blockchain_verified', sa.Boolean(), nullable=True),
        sa.Column('api_source', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("bet_direction IN ('YES', 'NO')", name='check_bet_direction'),
        sa.CheckConstraint('bet_size_usd > 0', name='check_bet_size_positive'),
        sa.CheckConstraint('suspicion_score >= 0 AND suspicion_score <= 100', name='check_score_range'),
        sa.ForeignKeyConstraint(['market_id'], ['markets.market_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_trade_id')
        )
        op.create_index('idx_trades_large_bets', 'trades', [sa.literal_column('bet_size_usd DESC')], unique=False)
        op.create_index('idx_trades_suspicion_high', 'trades', [sa.literal_column('suspicion_score DESC')], unique=False)
        op.create_index('idx_trades_timestamp_desc', 'trades', [sa.literal_column('timestamp DESC')], unique=False)
        op.create_index('idx_trades_wallet_timestamp', 'trades', ['wallet_address', sa.literal_column('timestamp DESC')], unique=False)
        op.create_index(op.f('ix_trades_market_id'), 'trades', ['market_id'], unique=False)
        op.create_index(op.f('ix_trades_suspicion_score'), 'trades', ['suspicion_score'], unique=False)
        op.create_index(op.f('ix_trades_timestamp'), 'trades', ['timestamp'], unique=False)
        op.create_index(op.f('ix_trades_transaction_hash'), 'trades', ['transaction_hash'], unique=True)
        op.create_index(op.f('ix_trades_wallet_address'), 'trades', ['wallet_address'], unique=False)

    if not _table_exists(bind, 'alerts'):
        op.create_table('alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alert_level', sa.String(length=20), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('trade_id', sa.Integer(), nullable=True),
        sa.Column('wallet_address', sa.String(length=42), nullable=True),
        sa.Column('market_id', sa.String(length=100), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('suspicion_score', sa.Integer(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('telegram_sent', sa.Boolean(), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['market_id'], ['markets.market_id'], ),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_alerts_level_time', 'alerts', ['alert_level', sa.literal_column('created_at DESC')], unique=False)
        op.create_index('idx_alerts_status_time', 'alerts', ['status', sa.literal_column('created_at DESC')], unique=False)
        op.create_index(op.f('ix_alerts_alert_level'), 'alerts', ['alert_level'], unique=False)
        op.create_index(op.f('ix_alerts_created_at'), 'alerts', ['created_at'], unique=False)
        op.create_index(op.f('ix_alerts_trade_id'), 'alerts', ['trade_id'], unique=False)
        op.create_index(op.f('ix_alerts_wallet_address'), 'alerts', ['wallet_address'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_alerts_wallet_address'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_trade_id'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_created_at'), table_name='alerts')
    op.drop_index(op.f('ix_alerts_alert_level'), table_name='alerts')
    op.drop_index('idx_alerts_status_time', table_name='alerts')
    op.drop_index('idx_alerts_level_time', table_name='alerts')
    op.drop_table('alerts')
    op.drop_index(op.f('ix_trades_wallet_address'), table_name='trades')
    op.drop_index(op.f('ix_trades_transaction_hash'), table_name='trades')
    op.drop_index(op.f('ix_trades_timestamp'), table_name='trades')
    op.drop_index(op.f('ix_trades_suspicion_score'), table_name='trades')
    op.drop_index(op.f('ix_trades_market_id'), table_name='trades')
    op.drop_index('idx_trades_wallet_timestamp', table_name='trades')
    op.drop_index('idx_trades_timestamp_desc', table_name='trades')
    op.drop_index('idx_trades_suspicion_high', table_name='trades')
    op.drop_index('idx_trades_large_bets', table_name='trades')
    op.drop_table('trades')
    op.drop_index('idx_wallet_metrics_win_rate', table_name='wallet_metrics')
    op.drop_index('idx_wallet_metrics_volume', table_name='wallet_metrics')
    op.drop_index('idx_wallet_metrics_suspicion', table_name='wallet_metrics')
    op.drop_table('wallet_metrics')
    op.drop_index(op.f('ix_pizzint_data_timestamp'), table_name='pizzint_data')
    op.drop_index(op.f('ix_pizzint_data_spike_detected'), table_name='pizzint_data')
    op.drop_index('idx_pizzint_timestamp_desc', table_name='pizzint_data')
    op.drop_index('idx_pizzint_spikes', table_name='pizzint_data')
    op.drop_table('pizzint_data')
    op.drop_index(op.f('ix_markets_slug'), table_name='markets')
    op.drop_index(op.f('ix_markets_is_geopolitical'), table_name='markets')
    op.drop_index(op.f('ix_markets_active'), table_name='markets')
    op.drop_table('markets')
    # ### end Alembic commands ###
