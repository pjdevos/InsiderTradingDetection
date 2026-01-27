"""Add monitor_checkpoints and failed_trades tables

Revision ID: add_monitor_tables
Revises: add_suspicious_wins
Create Date: 2026-01-27

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_monitor_tables'
down_revision = 'add_suspicious_wins'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = inspect(bind).get_table_names()

    if 'monitor_checkpoints' not in existing_tables:
        op.create_table(
            'monitor_checkpoints',
            sa.Column('monitor_name', sa.String(100), nullable=False),
            sa.Column('last_checkpoint_time', sa.DateTime(timezone=True), nullable=False),
            sa.Column('total_trades_processed', sa.Integer(), default=0),
            sa.Column('total_failures', sa.Integer(), default=0),
            sa.Column('last_failure_time', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_failure_reason', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('monitor_name'),
        )

    if 'failed_trades' not in existing_tables:
        op.create_table(
            'failed_trades',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('transaction_hash', sa.String(66), nullable=False),
            sa.Column('trade_data', sa.JSON(), nullable=False),
            sa.Column('failure_reason', sa.Text(), nullable=False),
            sa.Column('failure_count', sa.Integer(), default=1),
            sa.Column('first_failure_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('retry_count', sa.Integer(), default=0),
            sa.Column('max_retries', sa.Integer(), default=5),
            sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('status', sa.String(20), default='PENDING'),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('resolution_notes', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )

    existing_indexes = {idx['name'] for idx in inspect(bind).get_indexes('failed_trades')} if 'failed_trades' in inspect(bind).get_table_names() else set()
    if 'idx_failed_trades_status' not in existing_indexes:
        op.create_index('idx_failed_trades_status', 'failed_trades', ['status'])
    if 'idx_failed_trades_next_retry' not in existing_indexes:
        op.create_index('idx_failed_trades_next_retry', 'failed_trades', ['next_retry_at'])
    if 'idx_failed_trades_tx_hash' not in existing_indexes:
        op.create_index('idx_failed_trades_tx_hash', 'failed_trades', ['transaction_hash'])


def downgrade() -> None:
    op.drop_index('idx_failed_trades_tx_hash', 'failed_trades')
    op.drop_index('idx_failed_trades_next_retry', 'failed_trades')
    op.drop_index('idx_failed_trades_status', 'failed_trades')
    op.drop_table('failed_trades')
    op.drop_table('monitor_checkpoints')
