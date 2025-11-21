#!/usr/bin/env python3
"""
Calculate all team metrics using walk-forward methodology.
Populates team_game_stats table for all games from 2019-2025.

Usage:
    python calculate_metrics.py
"""

import sys
import os
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path so we can import nba_2x2x2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
from nba_2x2x2.data import DatabaseManager, MetricsCalculator


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def calculate_metrics():
    """Calculate metrics for all games."""
    logger.info("=" * 80)
    logger.info("NBA Metrics Calculator - Walk-Forward Methodology")
    logger.info("=" * 80)

    try:
        # Initialize database
        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()

        # Create table if not exists
        logger.info("Creating team_game_stats table...")
        from nba_2x2x2.data.models import Base
        Base.metadata.create_all(db_manager.engine)
        logger.info("Table created/verified successfully")

        # Get session and calculate metrics
        session = db_manager.get_session()
        calculator = MetricsCalculator(session)

        logger.info("\n" + "=" * 80)
        logger.info("CALCULATING METRICS")
        logger.info("=" * 80)

        calculator.calculate_all_metrics()

        logger.info("\n" + "=" * 80)
        logger.info("Metrics calculation completed successfully!")
        logger.info("=" * 80)

        # Verify
        from nba_2x2x2.data.models import TeamGameStats
        from sqlalchemy import func

        stats_count = session.query(func.count(TeamGameStats.id)).scalar()
        logger.info(f"Total team-game stats records: {stats_count}")

        # Cleanup
        session.close()
        db_manager.disconnect()

    except Exception as e:
        logger.error(f"Metrics calculation failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Setup logging
    setup_logging()

    # Calculate metrics
    calculate_metrics()


if __name__ == "__main__":
    main()
