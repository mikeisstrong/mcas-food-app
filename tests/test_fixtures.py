"""
Test that all fixtures are working correctly.
This validates the test infrastructure setup.
"""

import pytest
from sqlalchemy.orm import Session
from nba_2x2x2.data.models import Team, Game, TeamGameStats, GamePrediction


class TestDatabaseFixtures:
    """Test database fixtures work correctly."""

    @pytest.mark.unit
    def test_test_db_session_creates_connection(self, test_db_session: Session):
        """Verify test database session is available."""
        assert test_db_session is not None
        assert test_db_session.is_active

    @pytest.mark.unit
    def test_test_db_engine_creates_tables(self, test_db_session: Session):
        """Verify all tables are created in test database."""
        # Query should work without error
        teams = test_db_session.query(Team).all()
        assert teams == []

    @pytest.mark.unit
    def test_sample_teams_fixture(self, sample_teams):
        """Verify sample teams fixture creates test data."""
        assert len(sample_teams) == 5
        assert sample_teams[0].abbreviation == "BOS"
        assert sample_teams[1].abbreviation == "LAL"
        assert sample_teams[0].conference == "EAST"
        assert sample_teams[1].conference == "WEST"

    @pytest.mark.unit
    def test_sample_teams_persisted_to_db(self, test_db_session: Session, sample_teams):
        """Verify sample teams are actually in the database."""
        teams = test_db_session.query(Team).all()
        assert len(teams) == 5
        assert teams[0].abbreviation == "BOS"

    @pytest.mark.unit
    def test_sample_games_fixture(self, sample_games):
        """Verify sample games fixture creates test data."""
        assert len(sample_games) == 10
        assert sample_games[0].home_team_score == 105
        assert sample_games[0].away_team_score == 100
        assert sample_games[0].status == "final"

    @pytest.mark.unit
    def test_sample_games_persisted_to_db(self, test_db_session: Session, sample_games):
        """Verify sample games are actually in the database."""
        games = test_db_session.query(Game).all()
        assert len(games) == 10
        first_game = games[0]
        assert first_game.home_team_score > first_game.away_team_score

    @pytest.mark.unit
    def test_sample_team_game_stats_fixture(self, sample_team_game_stats):
        """Verify sample stats fixture creates test data."""
        assert len(sample_team_game_stats) == 20  # 10 games * 2 teams each
        assert sample_team_game_stats[0].is_home == 1
        assert sample_team_game_stats[1].is_home == 0

    @pytest.mark.unit
    def test_sample_predictions_fixture(self, sample_predictions):
        """Verify sample predictions fixture creates test data."""
        assert len(sample_predictions) == 10
        for pred in sample_predictions:
            assert 0 <= pred.home_win_prob <= 1
            assert 0 <= pred.away_win_prob <= 1
            assert abs((pred.home_win_prob + pred.away_win_prob) - 1.0) < 0.001

    @pytest.mark.unit
    def test_fixture_isolation(self, test_db_session: Session, sample_teams):
        """
        Verify that fixtures are isolated between tests.
        Each test should get a fresh database with fresh fixtures.
        """
        teams = test_db_session.query(Team).all()
        assert len(teams) == 5

    @pytest.mark.unit
    def test_cleanup_fixture_works(self, test_db_session: Session, cleanup_db, sample_teams):
        """Verify cleanup fixture can clear database."""
        # Add data
        teams = test_db_session.query(Team).all()
        assert len(teams) == 5

        # Call cleanup
        cleanup_db()

        # Verify data is cleared
        teams = test_db_session.query(Team).all()
        assert len(teams) == 0

    @pytest.mark.unit
    def test_config_fixture_available(self, config):
        """Verify Config fixture is available."""
        assert config is not None
        assert hasattr(config, "DB_HOST")
        assert hasattr(config, "DB_PORT")


class TestFixtureRelationships:
    """Test that fixtures properly maintain relationships."""

    @pytest.mark.unit
    def test_games_have_team_relationships(self, sample_games, sample_teams):
        """Verify games are properly linked to teams."""
        game = sample_games[0]
        assert game.home_team is not None
        assert game.away_team is not None
        assert game.home_team.abbreviation in ["BOS", "LAL", "MIA", "GS", "CHI"]
        assert game.away_team.abbreviation in ["BOS", "LAL", "MIA", "GS", "CHI"]

    @pytest.mark.unit
    def test_team_game_stats_relationships(self, sample_team_game_stats, sample_games):
        """Verify stats are linked to games and teams."""
        stats = sample_team_game_stats[0]
        assert stats.game is not None
        assert stats.team is not None
        assert stats.game_id in [g.id for g in sample_games]

    @pytest.mark.unit
    def test_predictions_linked_to_games(self, sample_predictions, sample_games):
        """Verify predictions are linked to games."""
        for pred in sample_predictions:
            assert pred.game is not None
            game_ids = [g.id for g in sample_games]
            assert pred.game_id in game_ids


class TestDatabaseIsolation:
    """Test that database changes don't persist between tests."""

    @pytest.mark.unit
    def test_first_test_isolation(self, test_db_session: Session):
        """First test starts with clean database."""
        teams = test_db_session.query(Team).all()
        assert len(teams) == 0

    @pytest.mark.unit
    def test_second_test_isolation(self, test_db_session: Session):
        """Second test also starts with clean database (no data from first test)."""
        teams = test_db_session.query(Team).all()
        assert len(teams) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
