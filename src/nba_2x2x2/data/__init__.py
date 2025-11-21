"""
Data module: API integration, ETL, database loading, and metrics calculation.
Part 1: Data Collection & Database Population
Part 2: Metrics & Feature Calculation
"""

from .database import DatabaseManager
from .api_client import BallDontLieClient
from .models import Team, Game, TeamGameStats, Base
from .etl import NBADataETL
from .metrics import MetricsCalculator

__all__ = [
    "DatabaseManager",
    "BallDontLieClient",
    "Team",
    "Game",
    "TeamGameStats",
    "Base",
    "NBADataETL",
    "MetricsCalculator",
]
