"""Backfill missing columns from add_suspicious_wins (skipped by stamp)

Revision ID: fix_missing_columns
Revises: add_monitor_tables
Create Date: 2026-01-27

The add_suspicious_wins migration was skipped when the DB was stamped
at that revision without running its upgrade(). This migration
idempotently adds the columns, tables, indexes, and constraints
that should have been created.
"""
from alembic import op
from sqlalchemy import inspect, text
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_missing_columns'
down_revision = 'add_monitor_tables'
branch_labels = None
depends_on = None


def _column_exists(bind, table, column):
    """Check if a column exists in a table."""
    cols = [c['name'] for c in inspect(bind).get_columns(table)]
    return column in cols


def _table_exists(bind, table):
    return table in inspect(bind).get_table_names()


def _index_exists(bind, table, index_name):
    indexes = inspect(bind).get_indexes(table)
    return any(idx['name'] == index_name for idx in indexes)


def _constraint_exists(bind, table, constraint_name):
    """Check if a check constraint exists (PostgreSQL only)."""
    result = bind.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name = :table AND constraint_name = :name"
    ), {"table": table, "name": constraint_name})
    return result.fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # --- trades table: add missing columns ---
    trades_columns = {
        'trade_result': sa.Column('trade_result', sa.String(10), nullable=True),
        'profit_loss_usd': sa.Column('profit_loss_usd', sa.Float(), nullable=True),
        'hours_before_resolution': sa.Column('hours_before_resolution', sa.Float(), nullable=True),
        'resolution_id': sa.Column('resolution_id', sa.Integer(), nullable=True),
    }
    for col_name, col_def in trades_columns.items():
        if not _column_exists(bind, 'trades', col_name):
            op.add_column('trades', col_def)

    # Foreign key
    if not _constraint_exists(bind, 'trades', 'fk_trades_resolution'):
        if _column_exists(bind, 'trades', 'resolution_id'):
            op.create_foreign_key('fk_trades_resolution', 'trades', 'market_resolutions', ['resolution_id'], ['id'])

    # Check constraint
    if not _constraint_exists(bind, 'trades', 'check_trade_result'):
        op.create_check_constraint('check_trade_result', 'trades', "trade_result IN ('WIN', 'LOSS', 'PENDING', 'VOID') OR trade_result IS NULL")

    # Indexes on trades
    for idx_name, columns in [
        ('idx_trades_result', ['trade_result']),
        ('idx_trades_hours_before', ['hours_before_resolution']),
        ('idx_trades_resolution_id', ['resolution_id']),
    ]:
        if not _index_exists(bind, 'trades', idx_name):
            op.create_index(idx_name, 'trades', columns)

    # --- wallet_metrics table: add missing columns ---
    wm_columns = {
        'geopolitical_wins': sa.Column('geopolitical_wins', sa.Integer(), server_default='0'),
        'geopolitical_losses': sa.Column('geopolitical_losses', sa.Integer(), server_default='0'),
        'total_profit_loss_usd': sa.Column('total_profit_loss_usd', sa.Float(), server_default='0.0'),
        'early_win_count': sa.Column('early_win_count', sa.Integer(), server_default='0'),
        'win_streak_max': sa.Column('win_streak_max', sa.Integer(), server_default='0'),
        'win_streak_current': sa.Column('win_streak_current', sa.Integer(), server_default='0'),
        'suspicious_win_score': sa.Column('suspicious_win_score', sa.Integer(), nullable=True),
        'last_resolution_check': sa.Column('last_resolution_check', sa.DateTime(timezone=True), nullable=True),
    }
    for col_name, col_def in wm_columns.items():
        if not _column_exists(bind, 'wallet_metrics', col_name):
            op.add_column('wallet_metrics', col_def)

    # Indexes on wallet_metrics
    for idx_name, col_expr in [
        ('idx_wallet_metrics_suspicious_win', sa.text('suspicious_win_score DESC')),
        ('idx_wallet_metrics_profit', sa.text('total_profit_loss_usd DESC')),
    ]:
        if not _index_exists(bind, 'wallet_metrics', idx_name):
            op.create_index(idx_name, 'wallet_metrics', [col_expr])

    # --- market_resolutions table ---
    if not _table_exists(bind, 'market_resolutions'):
        op.create_table(
            'market_resolutions',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('market_id', sa.String(100), nullable=False),
            sa.Column('condition_id', sa.String(66), nullable=True),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('winning_outcome', sa.String(10), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=False),
            sa.Column('resolution_source', sa.String(20), nullable=False),
            sa.Column('final_yes_price', sa.Float(), nullable=True),
            sa.Column('final_no_price', sa.Float(), nullable=True),
            sa.Column('payout_numerators', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['market_id'], ['markets.market_id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('market_id'),
            sa.CheckConstraint("winning_outcome IN ('YES', 'NO', 'VOID')", name='chk_winning_outcome'),
            sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='chk_confidence'),
        )
        op.create_index('idx_resolutions_market', 'market_resolutions', ['market_id'])
        op.create_index('idx_resolutions_resolved_at', 'market_resolutions', [sa.text('resolved_at DESC')])
        op.create_index('idx_resolutions_outcome', 'market_resolutions', ['winning_outcome'])

    # --- wallet_win_history table ---
    if not _table_exists(bind, 'wallet_win_history'):
        op.create_table(
            'wallet_win_history',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('wallet_address', sa.String(42), nullable=False),
            sa.Column('market_id', sa.String(100), nullable=False),
            sa.Column('trade_id', sa.Integer(), nullable=True),
            sa.Column('resolution_id', sa.Integer(), nullable=True),
            sa.Column('bet_direction', sa.String(3), nullable=False),
            sa.Column('bet_size_usd', sa.Float(), nullable=False),
            sa.Column('bet_price', sa.Float(), nullable=False),
            sa.Column('winning_outcome', sa.String(10), nullable=False),
            sa.Column('trade_result', sa.String(10), nullable=False),
            sa.Column('profit_loss_usd', sa.Float(), nullable=True),
            sa.Column('hours_before_resolution', sa.Float(), nullable=True),
            sa.Column('is_geopolitical', sa.Boolean(), default=False),
            sa.Column('suspicion_score_at_bet', sa.Integer(), nullable=True),
            sa.Column('market_title', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['trade_id'], ['trades.id']),
            sa.ForeignKeyConstraint(['resolution_id'], ['market_resolutions.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint("trade_result IN ('WIN', 'LOSS', 'VOID')", name='chk_win_result'),
        )
        op.create_index('idx_win_history_wallet', 'wallet_win_history', ['wallet_address'])
        op.create_index('idx_win_history_result', 'wallet_win_history', ['wallet_address', 'trade_result'])
        op.create_index('idx_win_history_hours', 'wallet_win_history', ['hours_before_resolution'])
        op.create_index('idx_win_history_geopolitical', 'wallet_win_history', ['is_geopolitical', 'trade_result'])


def downgrade() -> None:
    # This is a backfill migration; downgrade is a no-op since the
    # original add_suspicious_wins downgrade handles removal.
    pass
