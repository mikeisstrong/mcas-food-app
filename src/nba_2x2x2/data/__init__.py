"""
Data module: API integration, ETL, and database loading.
Part 1: Data Collection & Database Population
"""

from .database import DatabaseManager
from .api_client import BallDontLieClient
from .models import Team, Game, Base
from .etl import NBADataETL

__all__ = ["DatabaseManager", "BallDontLieClient", "Team", "Game", "Base", "NBADataETL"]
