#!/usr/bin/env python3
"""
Database migration to remove game outcome data from team_game_stats table.
Removes: points_scored, points_allowed, ortg, drtg, net_rtg, efg_pct, tov_ratio, orb_pct, ft_rate

These columns caused data leakage because they included information about the current game,
which should not be available when making predictions.

Usage:
    python migrate_remove_game_outcome_data.py
"""

import sys
import os

# Load environment variables from .env file FIRST
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from datetime import datetime

# Add src to path so we can import nba_2x2x2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
from sqlalchemy import text
from nba_2x2x2.data import DatabaseManager


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/migrate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def migrate_remove_outcome_data(db_manager):
    """Remove game outcome data columns from team_game_stats table."""
    logger.info("=" * 80)
    logger.info("Database Migration: Remove Game Outcome Data (Prevent Data Leakage)")
    logger.info("=" * 80)

    # Get connection
    connection = db_manager.engine.connect()

    try:
        logger.info("Removing columns that caused data leakage...")

        # Columns to remove
        columns_to_remove = [
            "points_scored",
            "points_allowed",
            "ortg",
            "drtg",
            "net_rtg",
            "efg_pct",
            "tov_ratio",
            "orb_pct",
            "ft_rate",
        ]

        for col_name in columns_to_remove:
            try:
                # Check if column exists
                inspector_query = text(f"""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'team_game_stats' AND column_name = '{col_name}'
                """)
                result = connection.execute(inspector_query)
                if not result.fetchone():
                    logger.info(f"  ✓ Column {col_name} does not exist (skipped)")
                    continue

                alter_query = text(f"""
                    ALTER TABLE team_game_stats
                    DROP COLUMN {col_name}
                """)
                connection.execute(alter_query)
                connection.commit()
                logger.info(f"  ✓ Dropped column: {col_name}")
            except Exception as e:
                logger.warning(f"  ! Error dropping {col_name}: {e}")
                connection.rollback()
                continue

        logger.info("\n" + "=" * 80)
        logger.info("Migration completed successfully!")
        logger.info("=" * 80)
        logger.info("IMPORTANT: You must recalculate metrics for all games.")
        logger.info("Run: python scripts/calculate_metrics.py")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        connection.rollback()
        raise
    finally:
        connection.close()


def main():
    """Main entry point."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Setup logging
    setup_logging()

    try:
        # Initialize database
        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()

        # Run migration
        migrate_remove_outcome_data(db_manager)

        # Cleanup
        db_manager.disconnect()

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
