#!/usr/bin/env python3
"""
Main data loading script.
Fetches all NBA games from 2019 onwards and loads into PostgreSQL.

Usage:
    python reload_clean_from_api.py [--start-season YEAR] [--end-season YEAR]

Example:
    python reload_clean_from_api.py --start-season 2019
    python reload_clean_from_api.py --start-season 2020 --end-season 2023
"""

import sys
import os
import argparse
from datetime import datetime

# Add src to path so we can import nba_2x2x2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
from nba_2x2x2.data import DatabaseManager, BallDontLieClient, NBADataETL


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/nba_loader_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def load_all_data(start_season: int = 2019, end_season: int = None):
    """
    Load all NBA data from API into database.

    Args:
        start_season: Starting season (default 2019)
        end_season: Ending season (default current season)
    """
    logger.info("=" * 80)
    logger.info("NBA Data Loader - BALLDONTLIE API")
    logger.info("=" * 80)
    logger.info(f"Start season: {start_season}")
    logger.info(f"End season: {end_season or 'Current'}")
    logger.info("=" * 80)

    try:
        # Initialize database
        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()

        # Initialize API client
        logger.info("Initializing BALLDONTLIE API client...")
        api_client = BallDontLieClient()

        # Check API health
        if not api_client.health_check():
            logger.error("BALLDONTLIE API is not accessible")
            sys.exit(1)
        logger.info("API is accessible")

        # Create ETL pipeline
        session = db_manager.get_session()
        etl = NBADataETL(session, api_client)

        # Load teams
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 1: Loading Teams")
        logger.info("=" * 80)
        new_teams, updated_teams = etl.load_teams()
        logger.info(f"Teams loaded: {new_teams} new, {updated_teams} updated")

        # Load games
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 2: Loading Games")
        logger.info("=" * 80)
        new_games, updated_games = etl.load_games(
            start_season=start_season,
            end_season=end_season,
        )
        logger.info(f"Games loaded: {new_games} new, {updated_games} updated")

        # Validate data
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 3: Validating Data")
        logger.info("=" * 80)
        validation = etl.validate_data()
        logger.info(f"Total teams: {validation['team_count']}")
        logger.info(f"Total games: {validation['game_count']}")
        logger.info(f"Games with scores: {validation['games_with_scores']}")
        logger.info(f"Games without scores (scheduled): {validation['games_without_scores']}")

        # Print season summaries
        logger.info("\n" + "=" * 80)
        logger.info("PHASE 4: Season Summaries")
        logger.info("=" * 80)

        current_year = datetime.now().year
        current_month = datetime.now().month
        current_season = current_year if current_month >= 10 else current_year - 1

        end = end_season or current_season
        for season in range(start_season, end + 1):
            summary = etl.get_season_summary(season)
            logger.info(
                f"Season {season}: {summary['completed_games']} completed, "
                f"{summary['scheduled_games']} scheduled ({summary['total_games']} total)"
            )

        logger.info("\n" + "=" * 80)
        logger.info("Data loading completed successfully!")
        logger.info("=" * 80)

        # Cleanup
        session.close()
        db_manager.disconnect()

    except Exception as e:
        logger.error(f"Data loading failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load NBA games from BALLDONTLIE API into PostgreSQL database"
    )
    parser.add_argument(
        "--start-season",
        type=int,
        default=2019,
        help="Starting season year (default: 2019)",
    )
    parser.add_argument(
        "--end-season",
        type=int,
        default=None,
        help="Ending season year (default: current season)",
    )

    args = parser.parse_args()

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Setup logging
    setup_logging()

    # Load data
    load_all_data(start_season=args.start_season, end_season=args.end_season)


if __name__ == "__main__":
    main()
