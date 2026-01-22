"""Add suspicious wins tables and fields

Revision ID: add_suspicious_wins
Revises: d3080b390a2a
Create Date: 2026-01-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_suspicious_wins'
down_revision = 'd3080b390a2a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create market_resolutions table
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
    op.create_index('idx_resolutions_market', 'market_resolutions', ['market_id'])
    op.create_index('idx_resolutions_resolved_at', 'market_resolutions', [sa.text('resolved_at DESC')])
    op.create_index('idx_resolutions_outcome', 'market_resolutions', ['winning_outcome'])

    # Create wallet_win_history table
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
    op.create_index('idx_win_history_wallet', 'wallet_win_history', ['wallet_address'])
    op.create_index('idx_win_history_result', 'wallet_win_history', ['wallet_address', 'trade_result'])
    op.create_index('idx_win_history_hours', 'wallet_win_history', ['hours_before_resolution'])
    op.create_index('idx_win_history_geopolitical', 'wallet_win_history', ['is_geopolitical', 'trade_result'])

    # Add new columns to trades table
    op.add_column('trades', sa.Column('trade_result', sa.String(10), nullable=True))
    op.add_column('trades', sa.Column('profit_loss_usd', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('hours_before_resolution', sa.Float(), nullable=True))
    op.add_column('trades', sa.Column('resolution_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_trades_resolution', 'trades', 'market_resolutions', ['resolution_id'], ['id'])
    op.create_index('idx_trades_result', 'trades', ['trade_result'])
    op.create_index('idx_trades_hours_before', 'trades', ['hours_before_resolution'])

    # Add new columns to wallet_metrics table
    op.add_column('wallet_metrics', sa.Column('geopolitical_wins', sa.Integer(), default=0))
    op.add_column('wallet_metrics', sa.Column('geopolitical_losses', sa.Integer(), default=0))
    op.add_column('wallet_metrics', sa.Column('total_profit_loss_usd', sa.Float(), default=0.0))
    op.add_column('wallet_metrics', sa.Column('early_win_count', sa.Integer(), default=0))
    op.add_column('wallet_metrics', sa.Column('win_streak_max', sa.Integer(), default=0))
    op.add_column('wallet_metrics', sa.Column('win_streak_current', sa.Integer(), default=0))
    op.add_column('wallet_metrics', sa.Column('suspicious_win_score', sa.Integer(), nullable=True))
    op.add_column('wallet_metrics', sa.Column('last_resolution_check', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_wallet_metrics_suspicious_win', 'wallet_metrics', [sa.text('suspicious_win_score DESC')])
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
    op.drop_index('idx_trades_hours_before', 'trades')
    op.drop_index('idx_trades_result', 'trades')
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
