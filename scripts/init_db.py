#!/usr/bin/env python3
"""
Database initialization script.
Creates all tables and initializes the database schema.
"""

import sys
import os

# Add src to path so we can import nba_2x2x2
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
from nba_2x2x2.data import DatabaseManager, Base


def init_database():
    """Initialize the database with all required tables."""
    logger.info("Initializing NBA 2x2x2 database...")

    try:
        # Connect to database
        db_manager = DatabaseManager()
        db_manager.connect()

        if db_manager.engine is None:
            raise RuntimeError("Failed to create database engine")

        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(db_manager.engine)

        logger.info("Database initialization completed successfully!")
        logger.info("Tables created: teams, games")

        db_manager.disconnect()

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    init_database()
