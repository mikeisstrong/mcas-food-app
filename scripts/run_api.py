#!/usr/bin/env python3
"""
Run Flask API server for NBA metrics.

Usage:
    python run_api.py

Server will be available at:
    http://localhost:5000/api/v1/health
"""

import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flask import Flask
from loguru import logger

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.api.routes import api_bp, init_db


def create_app():
    """Create and configure Flask app."""
    app = Flask(__name__)

    # Initialize database manager
    db_manager = DatabaseManager()
    db_manager.connect()
    init_db(db_manager)

    # Register API blueprint
    app.register_blueprint(api_bp)

    logger.info("Flask app created successfully")
    return app


if __name__ == "__main__":
    # Setup logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO",
    )

    logger.info("=" * 80)
    logger.info("NBA Metrics API - Starting Flask Server")
    logger.info("=" * 80)

    app = create_app()

    logger.info("API Server running on http://localhost:5000")
    logger.info("Available endpoints:")
    logger.info("  GET  /api/v1/health - Health check")
    logger.info("  GET  /api/v1/teams - List all teams")
    logger.info("  GET  /api/v1/team/<id>/stats - Team latest stats")
    logger.info("  GET  /api/v1/game/<id>/stats - Game stats for both teams")
    logger.info("  GET  /api/v1/games - Recent games with optional filters")
    logger.info("  GET  /api/v1/leaderboard/elo - ELO ratings leaderboard")
    logger.info("  GET  /api/v1/leaderboard/ppf - Points-for leaderboard")
    logger.info("=" * 80)

    app.run(debug=True, host="0.0.0.0", port=5000)
