"""
ETL (Extract, Transform, Load) module for NBA data.
Handles data validation, transformation, and database loading.
"""

from typing import List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from loguru import logger

from .models import Team, Game
from .api_client import BallDontLieClient


class NBADataETL:
    """Orchestrates ETL pipeline for NBA data."""

    def __init__(self, db_session: Session, api_client: BallDontLieClient):
        """
        Initialize ETL pipeline.

        Args:
            db_session: SQLAlchemy session for database operations
            api_client: BALLDONTLIE API client
        """
        self.session = db_session
        self.api_client = api_client

    def load_teams(self) -> Tuple[int, int]:
        """
        Fetch teams from API and load into database.

        Returns:
            Tuple of (new_teams_count, updated_teams_count)
        """
        logger.info("Loading teams from BALLDONTLIE API...")

        try:
            api_teams = self.api_client.get_teams()
            logger.info(f"Fetched {len(api_teams)} teams from API")

            new_count = 0
            updated_count = 0

            for api_team in api_teams:
                # Check if team already exists
                existing_team = self.session.query(Team).filter(
                    Team.id == api_team["id"]
                ).first()

                team_data = {
                    "id": api_team["id"],
                    "abbreviation": api_team["abbreviation"],
                    "city": api_team["city"],
                    "conference": api_team["conference"],
                    "division": api_team["division"],
                    "full_name": api_team["full_name"],
                    "name": api_team["name"],
                }

                if existing_team:
                    # Update existing team
                    for key, value in team_data.items():
                        setattr(existing_team, key, value)
                    updated_count += 1
                else:
                    # Create new team
                    team = Team(**team_data)
                    self.session.add(team)
                    new_count += 1

            self.session.commit()
            logger.info(f"Teams: {new_count} new, {updated_count} updated")
            return new_count, updated_count

        except Exception as e:
            logger.error(f"Failed to load teams: {e}")
            self.session.rollback()
            raise

    def load_games(
        self,
        start_season: int = 2019,
        end_season: Optional[int] = None,
    ) -> Tuple[int, int]:
        """
        Fetch games from API and load into database.

        Args:
            start_season: Starting season (default 2019)
            end_season: Ending season (default current season)

        Returns:
            Tuple of (new_games_count, updated_games_count)
        """
        logger.info(f"Loading games from season {start_season} onwards...")

        if end_season is None:
            # Determine current season (2024 for 2024-25 season, etc.)
            current_year = datetime.now().year
            current_month = datetime.now().month
            end_season = current_year if current_month >= 10 else current_year - 1

        new_count = 0
        updated_count = 0
        seasons = list(range(start_season, end_season + 1))

        logger.info(f"Fetching games for {len(seasons)} seasons: {seasons}")

        for season in seasons:
            logger.info(f"Fetching season {season}...")

            try:
                season_games = self.api_client.get_season_games(season)
                logger.info(f"Season {season}: {len(season_games)} games from API")

                for api_game in season_games:
                    # Check if game already exists
                    home_team_id = api_game["home_team"]["id"]
                    away_team_id = api_game["visitor_team"]["id"]
                    game_date = api_game["date"].split("T")[0]  # Extract date part

                    existing_game = self.session.query(Game).filter(
                        Game.home_team_id == home_team_id,
                        Game.away_team_id == away_team_id,
                        Game.game_date == game_date,
                    ).first()

                    game_data = {
                        "id": api_game["id"],
                        "home_team_id": home_team_id,
                        "away_team_id": away_team_id,
                        "home_team_score": api_game["home_team_score"],
                        "away_team_score": api_game["visitor_team_score"],
                        "game_date": game_date,
                        "game_datetime": api_game["date"],
                        "season": season,
                        "status": api_game["status"],
                        "period": api_game.get("period"),
                        "time": api_game.get("time"),
                        "postseason": 1 if api_game.get("postseason", False) else 0,
                    }

                    if existing_game:
                        # Update existing game (status, scores might change)
                        for key, value in game_data.items():
                            if key != "id":  # Don't update primary key
                                setattr(existing_game, key, value)
                        updated_count += 1
                    else:
                        # Create new game
                        game = Game(**game_data)
                        self.session.add(game)
                        new_count += 1

                self.session.commit()
                logger.info(f"Season {season}: {new_count} new games total")

            except Exception as e:
                logger.error(f"Failed to load games for season {season}: {e}")
                self.session.rollback()
                raise

        logger.info(
            f"Total games loaded: {new_count} new, {updated_count} updated"
        )
        return new_count, updated_count

    def validate_data(self) -> dict:
        """
        Validate data integrity in database.

        Returns:
            Dictionary with validation results
        """
        logger.info("Validating database integrity...")

        results = {
            "team_count": self.session.query(Team).count(),
            "game_count": self.session.query(Game).count(),
            "games_with_scores": self.session.query(Game)
            .filter(Game.home_team_score.isnot(None))
            .count(),
            "games_without_scores": self.session.query(Game)
            .filter(Game.home_team_score.is_(None))
            .count(),
        }

        logger.info(f"Validation results: {results}")
        return results

    def get_season_summary(self, season: int) -> dict:
        """
        Get summary statistics for a specific season.

        Args:
            season: NBA season year

        Returns:
            Dictionary with season statistics
        """
        games = self.session.query(Game).filter(Game.season == season).all()
        completed_games = [g for g in games if g.home_team_score is not None]

        return {
            "season": season,
            "total_games": len(games),
            "completed_games": len(completed_games),
            "scheduled_games": len(games) - len(completed_games),
        }
