"""
SQLAlchemy ORM models for NBA data.
Defines tables for teams, games, and game statistics.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Team(Base):
    """NBA team information."""

    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    abbreviation = Column(String(3), unique=True, nullable=False, index=True)
    city = Column(String(50), nullable=False)
    conference = Column(String(10), nullable=False)  # EAST or WEST
    division = Column(String(20), nullable=False)
    full_name = Column(String(100), nullable=False)
    name = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    home_games = relationship(
        "Game",
        foreign_keys="Game.home_team_id",
        back_populates="home_team",
    )
    away_games = relationship(
        "Game",
        foreign_keys="Game.away_team_id",
        back_populates="away_team",
    )

    def __repr__(self):
        return f"<Team {self.abbreviation}: {self.full_name}>"


class Game(Base):
    """NBA game information and scores."""

    __tablename__ = "games"

    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_team_score = Column(Integer)
    away_team_score = Column(Integer)
    game_date = Column(Date, nullable=False, index=True)
    game_datetime = Column(DateTime, nullable=False)
    season = Column(Integer, nullable=False, index=True)  # e.g., 2023 for 2023-24 season
    status = Column(String(20), nullable=False, default="scheduled")  # scheduled, in_progress, final
    period = Column(Integer)  # Current period if in_progress
    time = Column(String(10))  # Time remaining if in_progress
    postseason = Column(Integer, default=0)  # 0 for regular season, 1 for postseason
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    home_team = relationship(
        "Team",
        foreign_keys=[home_team_id],
        back_populates="home_games",
    )
    away_team = relationship(
        "Team",
        foreign_keys=[away_team_id],
        back_populates="away_games",
    )

    # Unique constraint: each game should appear only once
    __table_args__ = (
        UniqueConstraint("home_team_id", "away_team_id", "game_date", name="uq_game"),
    )

    # Index for common queries
    Index("idx_game_date_season", "game_date", "season")

    def __repr__(self):
        return f"<Game {self.away_team.abbreviation}@{self.home_team.abbreviation} on {self.game_date}>"
