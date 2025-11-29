#!/usr/bin/env python
"""
Migration script to add 100-game rolling average metrics to team_game_stats table.
"""

import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sqlalchemy import text
from nba_2x2x2.data import DatabaseManager

def migrate():
    """Add 100-game metric columns to team_game_stats table."""
    db = DatabaseManager()
    db.connect()

    try:
        with db.engine.begin() as connection:
            # Check if columns already exist using PostgreSQL information schema
            result = connection.execute(
                text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name='team_game_stats' AND column_name IN ('ppf_100game', 'ppa_100game', 'diff_100game')
                """)
            )
            existing_columns = {row[0] for row in result}

            # Add columns if they don't exist
            if 'ppf_100game' not in existing_columns:
                print("Adding ppf_100game column...")
                connection.execute(text("ALTER TABLE team_game_stats ADD COLUMN ppf_100game FLOAT"))

            if 'ppa_100game' not in existing_columns:
                print("Adding ppa_100game column...")
                connection.execute(text("ALTER TABLE team_game_stats ADD COLUMN ppa_100game FLOAT"))

            if 'diff_100game' not in existing_columns:
                print("Adding diff_100game column...")
                connection.execute(text("ALTER TABLE team_game_stats ADD COLUMN diff_100game FLOAT"))

            print("Migration completed successfully!")

    except Exception as e:
        print(f"Error during migration: {e}")
        raise

    finally:
        db.disconnect()

if __name__ == "__main__":
    migrate()
