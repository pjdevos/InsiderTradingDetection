#!/usr/bin/env python
"""
Database migration script to create checkpoint and failed_trades tables.

Run this script to add the new tables for race condition prevention:
- monitor_checkpoints: Persistent checkpoint storage
- failed_trades: Dead-letter queue for failed trade processing

Usage:
    python scripts/migrate_add_checkpoint_tables.py

The script uses SQLAlchemy's create_all() which only creates tables
that don't already exist, so it's safe to run multiple times.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.connection import init_db, get_engine
from database.models import Base, MonitorCheckpoint, FailedTrade


def run_migration():
    """Run the database migration to create new tables."""
    print("=" * 60)
    print("Database Migration: Add Checkpoint Tables")
    print("=" * 60)
    print()

    print("Tables to create:")
    print("  - monitor_checkpoints (persistent checkpoint storage)")
    print("  - failed_trades (dead-letter queue)")
    print()

    try:
        print("Connecting to database...")
        engine = init_db()
        print("Connected successfully!")
        print()

        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        checkpoint_exists = 'monitor_checkpoints' in existing_tables
        failed_exists = 'failed_trades' in existing_tables

        if checkpoint_exists and failed_exists:
            print("Both tables already exist. Nothing to do.")
            return True

        print("Creating tables...")
        Base.metadata.create_all(engine)
        print()

        # Verify creation
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()

        if 'monitor_checkpoints' in new_tables:
            if checkpoint_exists:
                print("  [OK] monitor_checkpoints (already existed)")
            else:
                print("  [CREATED] monitor_checkpoints")
        else:
            print("  [ERROR] monitor_checkpoints - creation failed!")

        if 'failed_trades' in new_tables:
            if failed_exists:
                print("  [OK] failed_trades (already existed)")
            else:
                print("  [CREATED] failed_trades")
        else:
            print("  [ERROR] failed_trades - creation failed!")

        print()
        print("Migration completed successfully!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        print()
        print("If the database is not accessible, you can run this SQL manually:")
        print()
        print_sql_migration()
        return False


def print_sql_migration():
    """Print the raw SQL for manual migration."""
    sql = """
-- Monitor Checkpoints Table
CREATE TABLE IF NOT EXISTS monitor_checkpoints (
    monitor_name VARCHAR(100) PRIMARY KEY,
    last_checkpoint_time TIMESTAMP WITH TIME ZONE NOT NULL,
    total_trades_processed INTEGER DEFAULT 0,
    total_failures INTEGER DEFAULT 0,
    last_failure_time TIMESTAMP WITH TIME ZONE,
    last_failure_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Failed Trades Table (Dead-Letter Queue)
CREATE TABLE IF NOT EXISTS failed_trades (
    id SERIAL PRIMARY KEY,
    transaction_hash VARCHAR(66) NOT NULL,
    trade_data JSONB NOT NULL,
    failure_reason TEXT NOT NULL,
    failure_count INTEGER DEFAULT 1,
    first_failure_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_failure_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'PENDING',
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT
);

-- Indexes for failed_trades
CREATE INDEX IF NOT EXISTS idx_failed_trades_status ON failed_trades(status);
CREATE INDEX IF NOT EXISTS idx_failed_trades_next_retry ON failed_trades(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_failed_trades_tx_hash ON failed_trades(transaction_hash);
"""
    print(sql)


if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)
