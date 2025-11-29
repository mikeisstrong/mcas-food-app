"""
Pytest configuration and fixtures for NBA Prediction Model tests.
Provides database fixtures, test data, and API client setup.
"""

import sys
import os
from datetime import datetime, timedelta, date
from typing import List, Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nba_2x2x2.data.models import Base, Team, Game, TeamGameStats, GamePrediction
from nba_2x2x2.data.database import DatabaseManager
from nba_2x2x2.config import Config


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def test_db_engine():
    """
    Create an in-memory SQLite database for testing.
    Uses StaticPool to maintain connection across all test operations.
    """
    # Create in-memory SQLite engine for fast tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign keys in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.
    Automatically rolls back all changes after test completes.
    """
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_db_manager(test_db_engine) -> DatabaseManager:
    """
    Create a DatabaseManager instance using the test database.
    """
    # This is a simplified version that uses the test engine
    db = DatabaseManager()
    db.engine = test_db_engine
    db.session_factory = sessionmaker(bind=test_db_engine)
    db._is_connected = True
    return db


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_teams(test_db_session: Session) -> List[Team]:
    """
    Create sample NBA teams for testing.
    Returns 5 teams: 2 from East, 2 from West, 1 from other division.
    """
    teams_data = [
        Team(
            abbreviation="BOS",
            city="Boston",
            conference="EAST",
            division="Atlantic",
            full_name="Boston Celtics",
            name="Celtics",
        ),
        Team(
            abbreviation="LAL",
            city="Los Angeles",
            conference="WEST",
            division="Pacific",
            full_name="Los Angeles Lakers",
            name="Lakers",
        ),
        Team(
            abbreviation="MIA",
            city="Miami",
            conference="EAST",
            division="Southeast",
            full_name="Miami Heat",
            name="Heat",
        ),
        Team(
            abbreviation="GS",
            city="Golden State",
            conference="WEST",
            division="Pacific",
            full_name="Golden State Warriors",
            name="Warriors",
        ),
        Team(
            abbreviation="CHI",
            city="Chicago",
            conference="EAST",
            division="Central",
            full_name="Chicago Bulls",
            name="Bulls",
        ),
    ]

    for team in teams_data:
        test_db_session.add(team)
    test_db_session.commit()

    return teams_data


@pytest.fixture
def sample_games(test_db_session: Session, sample_teams: List[Team]) -> List[Game]:
    """
    Create sample games with known outcomes and dates.
    Creates 10 games over a 2-week period.
    """
    base_date = date(2025, 11, 1)
    games_data = []

    # Create games with alternating teams
    team_pairs = [
        (sample_teams[0], sample_teams[1]),  # BOS vs LAL
        (sample_teams[2], sample_teams[3]),  # MIA vs GS
        (sample_teams[1], sample_teams[4]),  # LAL vs CHI
        (sample_teams[0], sample_teams[2]),  # BOS vs MIA
        (sample_teams[3], sample_teams[4]),  # GS vs CHI
        (sample_teams[0], sample_teams[3]),  # BOS vs GS
        (sample_teams[1], sample_teams[2]),  # LAL vs MIA
        (sample_teams[4], sample_teams[3]),  # CHI vs GS
        (sample_teams[2], sample_teams[0]),  # MIA vs BOS
        (sample_teams[1], sample_teams[3]),  # LAL vs GS
    ]

    for i, (home_team, away_team) in enumerate(team_pairs):
        game_date = base_date + timedelta(days=i)
        game = Game(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_team_score=105 + i,  # Home team scores 105, 106, 107, etc.
            away_team_score=100 + i,  # Away team scores 100, 101, 102, etc.
            game_date=game_date,
            game_datetime=datetime.combine(game_date, datetime.min.time()),
            season=2024,
            status="final",
            postseason=0,
        )
        games_data.append(game)
        test_db_session.add(game)

    test_db_session.commit()
    return games_data


@pytest.fixture
def sample_team_game_stats(
    test_db_session: Session, sample_games: List[Game], sample_teams: List[Team]
) -> List[TeamGameStats]:
    """
    Create TeamGameStats records for sample games.
    Simulates walk-forward calculated metrics.
    """
    stats_list = []

    for game in sample_games:
        # Home team stats
        home_stats = TeamGameStats(
            game_id=game.id,
            team_id=game.home_team_id,
            is_home=1,
            games_played=10,
            wins=7,
            losses=3,
            win_pct=0.700,
            points_for=108.5,
            points_against=102.3,
            point_differential=6.2,
            ppf_5game=107.0,
            ppa_5game=101.5,
            diff_5game=5.5,
            ppf_10game=106.8,
            ppa_10game=102.1,
            diff_10game=4.7,
            ppf_20game=105.5,
            ppa_20game=103.2,
            diff_20game=2.3,
            elo_rating=1520.0,
            days_rest=1,
            back_to_back=0,
            game_won=1,  # Home team won
        )
        stats_list.append(home_stats)
        test_db_session.add(home_stats)

        # Away team stats
        away_stats = TeamGameStats(
            game_id=game.id,
            team_id=game.away_team_id,
            is_home=0,
            games_played=10,
            wins=6,
            losses=4,
            win_pct=0.600,
            points_for=102.1,
            points_against=106.3,
            point_differential=-4.2,
            ppf_5game=100.8,
            ppa_5game=105.1,
            diff_5game=-4.3,
            ppf_10game=101.2,
            ppa_10game=104.8,
            diff_10game=-3.6,
            ppf_20game=102.3,
            ppa_20game=104.5,
            diff_20game=-2.2,
            elo_rating=1480.0,
            days_rest=2,
            back_to_back=0,
            game_won=0,  # Away team lost
        )
        stats_list.append(away_stats)
        test_db_session.add(away_stats)

    test_db_session.commit()
    return stats_list


@pytest.fixture
def sample_predictions(
    test_db_session: Session, sample_games: List[Game]
) -> List[GamePrediction]:
    """
    Create sample game predictions for testing.
    """
    predictions = []

    for i, game in enumerate(sample_games):
        # Create predictions with varying confidence
        home_prob = 0.55 + (i * 0.03)  # Range from 0.55 to 0.82
        home_prob = min(home_prob, 0.95)  # Cap at 0.95

        prediction = GamePrediction(
            game_id=game.id,
            home_win_prob=home_prob,
            away_win_prob=1.0 - home_prob,
            point_differential=2.0 + i,  # Point spread prediction
            lightgbm_home_prob=home_prob + 0.02,
            elo_home_prob=home_prob - 0.02,
        )
        predictions.append(prediction)
        test_db_session.add(prediction)

    test_db_session.commit()
    return predictions


# ============================================================================
# API FIXTURES
# ============================================================================


@pytest.fixture
def api_client():
    """
    Create a FastAPI test client for testing API endpoints.
    """
    from fastapi.testclient import TestClient

    # Import api.main after sys.path is set
    api_path = os.path.join(os.path.dirname(__file__), "..", "api")
    sys.path.insert(0, api_path)

    try:
        from main import app

        return TestClient(app)
    except ImportError:
        pytest.skip("API module not available for testing")


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_balldontlie_response():
    """
    Provide mock responses for Ball Don't Lie API calls.
    """
    return {
        "data": [
            {
                "id": 1,
                "date": "2025-11-01",
                "home_team": {"id": 1, "abbreviation": "BOS", "full_name": "Boston Celtics"},
                "away_team": {"id": 2, "abbreviation": "LAL", "full_name": "Los Angeles Lakers"},
                "home_team_score": 105,
                "away_team_score": 100,
                "status": "Final",
            },
        ],
        "meta": {"total_count": 1, "current_page": 1, "per_page": 25},
    }


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture
def cleanup_db(test_db_session: Session):
    """
    Provides cleanup function for database between tests.
    Explicitly called when needed for additional cleanup.
    """

    def _cleanup():
        """Clear all tables in test database."""
        test_db_session.query(GamePrediction).delete()
        test_db_session.query(TeamGameStats).delete()
        test_db_session.query(Game).delete()
        test_db_session.query(Team).delete()
        test_db_session.commit()

    return _cleanup


# ============================================================================
# SESSION-SCOPED CONFIGURATION
# ============================================================================


@pytest.fixture(scope="session")
def config():
    """
    Provide Config instance (session-scoped since Config reads environment).
    """
    return Config


# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================


def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test (database isolated)",
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test (multiple components)",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running",
    )
    config.addinivalue_line(
        "markers",
        "critical: mark test as critical (must pass before production)",
    )
