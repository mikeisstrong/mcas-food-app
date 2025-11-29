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


class TeamGameStats(Base):
    """Team statistics calculated for each game (walk-forward methodology)."""

    __tablename__ = "team_game_stats"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    is_home = Column(Integer, nullable=False)  # 1 if home team, 0 if away team

    # Aggregate statistics (cumulative)
    games_played = Column(Integer, nullable=False, default=0)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    win_pct = Column(Float)  # wins / games_played

    # Points
    points_for = Column(Float)  # PPF - average points scored
    points_against = Column(Float)  # PPA - average points allowed
    point_differential = Column(Float)  # PPF - PPA

    # Rolling averages (5, 10, 20-game windows)
    ppf_5game = Column(Float)  # 5-game rolling avg PPF
    ppa_5game = Column(Float)  # 5-game rolling avg PPA
    diff_5game = Column(Float)  # 5-game rolling avg differential

    ppf_10game = Column(Float)  # 10-game rolling avg PPF
    ppa_10game = Column(Float)  # 10-game rolling avg PPA
    diff_10game = Column(Float)  # 10-game rolling avg differential

    ppf_20game = Column(Float)  # 20-game rolling avg PPF
    ppa_20game = Column(Float)  # 20-game rolling avg PPA
    diff_20game = Column(Float)  # 20-game rolling avg differential

    ppf_100game = Column(Float)  # 100-game rolling avg PPF
    ppa_100game = Column(Float)  # 100-game rolling avg PPA
    diff_100game = Column(Float)  # 100-game rolling avg differential

    # ELO Rating
    elo_rating = Column(Float, nullable=False, default=1500.0)  # Starts at 1500

    # Rest indicators
    days_rest = Column(Integer)  # Days since last game (excluding rest days)
    back_to_back = Column(Integer, default=0)  # 1 if playing back-to-back, 0 otherwise

    # Game outcome (stored for reference but NOT used in feature calculation)
    game_won = Column(Integer)  # 1 if team won this game, 0 if lost

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game = relationship("Game", foreign_keys=[game_id])
    team = relationship("Team", foreign_keys=[team_id])

    # Unique constraint: one entry per team per game
    __table_args__ = (
        UniqueConstraint("game_id", "team_id", name="uq_team_game_stats"),
        Index("idx_team_game_date", "team_id", "game_id"),
    )

    def __repr__(self):
        return f"<TeamGameStats Team={self.team_id} Game={self.game_id} ELO={self.elo_rating:.1f}>"


class GamePrediction(Base):
    """Model predictions for each game."""

    __tablename__ = "game_predictions"

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, unique=True, index=True)

    # Home team win probability (blended: 70% LightGBM + 30% ELO)
    home_win_prob = Column(Float, nullable=False)

    # Away team win probability (1 - home_win_prob)
    away_win_prob = Column(Float, nullable=False)

    # Point differential prediction (home team perspective)
    # Positive = home team expected to win by X points
    # Negative = home team expected to lose by X points
    point_differential = Column(Float, nullable=False)

    # Component scores for transparency
    lightgbm_home_prob = Column(Float)  # 70% weight
    elo_home_prob = Column(Float)  # 30% weight

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game = relationship("Game", foreign_keys=[game_id])

    def __repr__(self):
        return f"<GamePrediction Game={self.game_id} HomeProb={self.home_win_prob:.1%} Diff={self.point_differential:+.1f}>"
