"""Add suspicious wins tables and fields

Revision ID: add_suspicious_wins
Revises: d3080b390a2a
Create Date: 2026-01-21

"""
from alembic import op
from sqlalchemy import inspect, text
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_suspicious_wins'
down_revision = 'd3080b390a2a'
branch_labels = None
depends_on = None


def _table_exists(bind, table):
    return table in inspect(bind).get_table_names()


def _column_exists(bind, table, column):
    cols = [c['name'] for c in inspect(bind).get_columns(table)]
    return column in cols


def _index_exists(bind, table, index_name):
    indexes = inspect(bind).get_indexes(table)
    return any(idx['name'] == index_name for idx in indexes)


def _constraint_exists(bind, table, constraint_name):
    result = bind.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE table_name = :table AND constraint_name = :name"
    ), {"table": table, "name": constraint_name})
    return result.fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # Create market_resolutions table
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
            sa.ForeignKeyConstraint(['market_id'], ['markets.market_id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('market_id'),
            sa.CheckConstraint("winning_outcome IN ('YES', 'NO', 'VOID')", name='chk_winning_outcome'),
            sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='chk_confidence'),
        )
    if _table_exists(bind, 'market_resolutions'):
        if not _index_exists(bind, 'market_resolutions', 'idx_resolutions_market'):
            op.create_index('idx_resolutions_market', 'market_resolutions', ['market_id'])
        if not _index_exists(bind, 'market_resolutions', 'idx_resolutions_resolved_at'):
            op.create_index('idx_resolutions_resolved_at', 'market_resolutions', [sa.text('resolved_at DESC')])
        if not _index_exists(bind, 'market_resolutions', 'idx_resolutions_outcome'):
            op.create_index('idx_resolutions_outcome', 'market_resolutions', ['winning_outcome'])

    # Create wallet_win_history table
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
            sa.ForeignKeyConstraint(['trade_id'], ['trades.id'], ),
            sa.ForeignKeyConstraint(['resolution_id'], ['market_resolutions.id'], ),
            sa.PrimaryKeyConstraint('id'),
            sa.CheckConstraint("trade_result IN ('WIN', 'LOSS', 'VOID')", name='chk_win_result'),
        )
    if _table_exists(bind, 'wallet_win_history'):
        if not _index_exists(bind, 'wallet_win_history', 'idx_win_history_wallet'):
            op.create_index('idx_win_history_wallet', 'wallet_win_history', ['wallet_address'])
        if not _index_exists(bind, 'wallet_win_history', 'idx_win_history_result'):
            op.create_index('idx_win_history_result', 'wallet_win_history', ['wallet_address', 'trade_result'])
        if not _index_exists(bind, 'wallet_win_history', 'idx_win_history_hours'):
            op.create_index('idx_win_history_hours', 'wallet_win_history', ['hours_before_resolution'])
        if not _index_exists(bind, 'wallet_win_history', 'idx_win_history_geopolitical'):
            op.create_index('idx_win_history_geopolitical', 'wallet_win_history', ['is_geopolitical', 'trade_result'])

    # Add new columns to trades table
    trades_columns = {
        'trade_result': sa.Column('trade_result', sa.String(10), nullable=True),
        'profit_loss_usd': sa.Column('profit_loss_usd', sa.Float(), nullable=True),
        'hours_before_resolution': sa.Column('hours_before_resolution', sa.Float(), nullable=True),
        'resolution_id': sa.Column('resolution_id', sa.Integer(), nullable=True),
    }
    for col_name, col_def in trades_columns.items():
        if not _column_exists(bind, 'trades', col_name):
            op.add_column('trades', col_def)

    if _column_exists(bind, 'trades', 'resolution_id'):
        if not _constraint_exists(bind, 'trades', 'fk_trades_resolution'):
            op.create_foreign_key('fk_trades_resolution', 'trades', 'market_resolutions', ['resolution_id'], ['id'])
    if not _constraint_exists(bind, 'trades', 'check_trade_result'):
        op.create_check_constraint('check_trade_result', 'trades', "trade_result IN ('WIN', 'LOSS', 'PENDING', 'VOID') OR trade_result IS NULL")
    if not _index_exists(bind, 'trades', 'idx_trades_result'):
        op.create_index('idx_trades_result', 'trades', ['trade_result'])
    if not _index_exists(bind, 'trades', 'idx_trades_hours_before'):
        op.create_index('idx_trades_hours_before', 'trades', ['hours_before_resolution'])
    if not _index_exists(bind, 'trades', 'idx_trades_resolution_id'):
        op.create_index('idx_trades_resolution_id', 'trades', ['resolution_id'])

    # Add new columns to wallet_metrics table
    wm_columns = {
        'geopolitical_wins': sa.Column('geopolitical_wins', sa.Integer(), default=0),
        'geopolitical_losses': sa.Column('geopolitical_losses', sa.Integer(), default=0),
        'total_profit_loss_usd': sa.Column('total_profit_loss_usd', sa.Float(), default=0.0),
        'early_win_count': sa.Column('early_win_count', sa.Integer(), default=0),
        'win_streak_max': sa.Column('win_streak_max', sa.Integer(), default=0),
        'win_streak_current': sa.Column('win_streak_current', sa.Integer(), default=0),
        'suspicious_win_score': sa.Column('suspicious_win_score', sa.Integer(), nullable=True),
        'last_resolution_check': sa.Column('last_resolution_check', sa.DateTime(timezone=True), nullable=True),
    }
    for col_name, col_def in wm_columns.items():
        if not _column_exists(bind, 'wallet_metrics', col_name):
            op.add_column('wallet_metrics', col_def)

    if not _index_exists(bind, 'wallet_metrics', 'idx_wallet_metrics_suspicious_win'):
        op.create_index('idx_wallet_metrics_suspicious_win', 'wallet_metrics', [sa.text('suspicious_win_score DESC')])
    if not _index_exists(bind, 'wallet_metrics', 'idx_wallet_metrics_profit'):
        op.create_index('idx_wallet_metrics_profit', 'wallet_metrics', [sa.text('total_profit_loss_usd DESC')])


def downgrade() -> None:
    # Remove indexes from wallet_metrics
    op.drop_index('idx_wallet_metrics_profit', 'wallet_metrics')
    op.drop_index('idx_wallet_metrics_suspicious_win', 'wallet_metrics')

    # Remove columns from wallet_metrics
    op.drop_column('wallet_metrics', 'last_resolution_check')
    op.drop_column('wallet_metrics', 'suspicious_win_score')
    op.drop_column('wallet_metrics', 'win_streak_current')
    op.drop_column('wallet_metrics', 'win_streak_max')
    op.drop_column('wallet_metrics', 'early_win_count')
    op.drop_column('wallet_metrics', 'total_profit_loss_usd')
    op.drop_column('wallet_metrics', 'geopolitical_losses')
    op.drop_column('wallet_metrics', 'geopolitical_wins')

    # Remove indexes and columns from trades
    op.drop_index('idx_trades_resolution_id', 'trades')
    op.drop_index('idx_trades_hours_before', 'trades')
    op.drop_index('idx_trades_result', 'trades')
    op.drop_constraint('check_trade_result', 'trades', type_='check')
    op.drop_constraint('fk_trades_resolution', 'trades', type_='foreignkey')
    op.drop_column('trades', 'resolution_id')
    op.drop_column('trades', 'hours_before_resolution')
    op.drop_column('trades', 'profit_loss_usd')
    op.drop_column('trades', 'trade_result')

    # Drop wallet_win_history table
    op.drop_index('idx_win_history_geopolitical', 'wallet_win_history')
    op.drop_index('idx_win_history_hours', 'wallet_win_history')
    op.drop_index('idx_win_history_result', 'wallet_win_history')
    op.drop_index('idx_win_history_wallet', 'wallet_win_history')
    op.drop_table('wallet_win_history')

    # Drop market_resolutions table
    op.drop_index('idx_resolutions_outcome', 'market_resolutions')
    op.drop_index('idx_resolutions_resolved_at', 'market_resolutions')
    op.drop_index('idx_resolutions_market', 'market_resolutions')
    op.drop_table('market_resolutions')
