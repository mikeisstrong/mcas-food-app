"""
Metrics calculation engine for Part 2.
Walk-forward methodology: calculates metrics incrementally as games occur.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from .models import Game, Team, TeamGameStats


class MetricsCalculator:
    """Calculate team metrics using walk-forward methodology."""

    ELO_K = 32  # ELO rating adjustment factor
    ELO_INITIAL = 1500.0  # Starting ELO rating

    def __init__(self, session: Session):
        """Initialize metrics calculator."""
        self.session = session

    def calculate_all_metrics(self):
        """Calculate metrics for all games in chronological order."""
        logger.info("Starting walk-forward metrics calculation...")

        # Get all games ordered by date
        games = (
            self.session.query(Game)
            .filter(Game.status == "Final")
            .order_by(Game.game_date, Game.id)
            .all()
        )

        logger.info(f"Processing {len(games)} games for metrics calculation")

        for idx, game in enumerate(games):
            if (idx + 1) % 500 == 0:
                logger.info(f"Processing game {idx + 1}/{len(games)}")

            # Calculate metrics for both teams
            self._calculate_game_metrics(game)

        logger.info("Metrics calculation completed successfully")

    def _calculate_game_metrics(self, game: Game):
        """Calculate metrics for both teams in a game."""
        home_team = game.home_team
        away_team = game.away_team

        # Get all games played before this game (for rolling calculations)
        prev_games_home = self._get_prev_games(home_team.id, game.game_date)
        prev_games_away = self._get_prev_games(away_team.id, game.game_date)

        # Determine game outcome
        home_won = game.home_team_score > game.away_team_score
        away_won = not home_won

        # Calculate rest days
        home_rest = self._calculate_rest_days(home_team.id, game.game_date)
        away_rest = self._calculate_rest_days(away_team.id, game.game_date)

        # Determine back-to-back status
        home_b2b = self._is_back_to_back(home_team.id, game.game_date)
        away_b2b = self._is_back_to_back(away_team.id, game.game_date)

        # Home team stats (using only pre-game information)
        home_stats = self._calculate_team_stats(
            game_id=game.id,
            team_id=home_team.id,
            is_home=1,
            prev_games=prev_games_home,
            game_won=1 if home_won else 0,
            days_rest=home_rest,
            back_to_back=1 if home_b2b else 0,
            opponent_id=away_team.id,
            game_date=game.game_date,
        )

        # Away team stats (using only pre-game information)
        away_stats = self._calculate_team_stats(
            game_id=game.id,
            team_id=away_team.id,
            is_home=0,
            prev_games=prev_games_away,
            game_won=1 if away_won else 0,
            days_rest=away_rest,
            back_to_back=1 if away_b2b else 0,
            opponent_id=home_team.id,
            game_date=game.game_date,
        )

        # Check if records already exist
        existing_home = (
            self.session.query(TeamGameStats)
            .filter_by(game_id=game.id, team_id=home_team.id)
            .first()
        )
        existing_away = (
            self.session.query(TeamGameStats)
            .filter_by(game_id=game.id, team_id=away_team.id)
            .first()
        )

        # Create or update records
        if existing_home:
            for key, value in home_stats.items():
                setattr(existing_home, key, value)
        else:
            home_stats_obj = TeamGameStats(**home_stats)
            self.session.add(home_stats_obj)

        if existing_away:
            for key, value in away_stats.items():
                setattr(existing_away, key, value)
        else:
            away_stats_obj = TeamGameStats(**away_stats)
            self.session.add(away_stats_obj)

        self.session.commit()

    def _calculate_team_stats(
        self,
        game_id: int,
        team_id: int,
        is_home: int,
        prev_games: List[Dict],
        game_won: int,
        days_rest: int,
        back_to_back: int,
        opponent_id: int,
        game_date,
    ) -> Dict:
        """
        Calculate all stats for a team in a specific game.

        CRITICAL: Uses ONLY prior games to prevent data leakage.
        Current game outcome is stored but NOT used in calculations.
        """

        # Get opponent's ELO rating (pre-game)
        opponent_elo = self._get_latest_elo(opponent_id, game_date)

        # Calculate cumulative stats using ONLY prior games
        games_played = len(prev_games)
        wins = sum(1 for g in prev_games if g["won"])
        losses = games_played - wins
        win_pct = wins / games_played if games_played > 0 else 0.0

        # Calculate aggregate points using ONLY prior games
        total_pf = sum(g["pf"] for g in prev_games)
        total_pa = sum(g["pa"] for g in prev_games)
        ppf = total_pf / games_played if games_played > 0 else 0.0
        ppa = total_pa / games_played if games_played > 0 else 0.0
        point_diff = ppf - ppa

        # Calculate rolling averages using ONLY prior games (NO current game)
        ppf_5 = self._rolling_average([g["pf"] for g in prev_games[-5:]])
        ppa_5 = self._rolling_average([g["pa"] for g in prev_games[-5:]])
        diff_5 = ppf_5 - ppa_5 if ppf_5 is not None and ppa_5 is not None else None

        ppf_10 = self._rolling_average([g["pf"] for g in prev_games[-10:]])
        ppa_10 = self._rolling_average([g["pa"] for g in prev_games[-10:]])
        diff_10 = ppf_10 - ppa_10 if ppf_10 is not None and ppa_10 is not None else None

        ppf_20 = self._rolling_average([g["pf"] for g in prev_games[-20:]])
        ppa_20 = self._rolling_average([g["pa"] for g in prev_games[-20:]])
        diff_20 = ppf_20 - ppa_20 if ppf_20 is not None and ppa_20 is not None else None

        ppf_100 = self._rolling_average([g["pf"] for g in prev_games[-100:]])
        ppa_100 = self._rolling_average([g["pa"] for g in prev_games[-100:]])
        diff_100 = ppf_100 - ppa_100 if ppf_100 is not None and ppa_100 is not None else None

        # Get pre-game ELO rating
        team_elo = self._get_latest_elo(team_id, game_date)

        # Calculate post-game ELO (updated with this game's result)
        # This is what gets stored and retrieved for future games
        post_game_elo = self._calculate_elo(team_elo, opponent_elo, game_won)

        return {
            "game_id": game_id,
            "team_id": team_id,
            "is_home": is_home,
            "games_played": games_played,
            "wins": wins,
            "losses": losses,
            "win_pct": win_pct,
            "points_for": ppf,
            "points_against": ppa,
            "point_differential": point_diff,
            "ppf_5game": ppf_5,
            "ppa_5game": ppa_5,
            "diff_5game": diff_5,
            "ppf_10game": ppf_10,
            "ppa_10game": ppa_10,
            "diff_10game": diff_10,
            "ppf_20game": ppf_20,
            "ppa_20game": ppa_20,
            "diff_20game": diff_20,
            "ppf_100game": ppf_100,
            "ppa_100game": ppa_100,
            "diff_100game": diff_100,
            "elo_rating": post_game_elo,
            "days_rest": days_rest,
            "back_to_back": back_to_back,
            "game_won": game_won,
        }

    def _get_prev_games(self, team_id: int, game_date) -> List[Dict]:
        """Get all games played by team before a specific date."""
        games = (
            self.session.query(Game, TeamGameStats)
            .outerjoin(
                TeamGameStats,
                (Game.id == TeamGameStats.game_id)
                & (TeamGameStats.team_id == team_id),
            )
            .filter(
                (
                    (Game.home_team_id == team_id)
                    | (Game.away_team_id == team_id)
                )
                & (Game.game_date < game_date)
                & (Game.status == "Final")
            )
            .order_by(Game.game_date)
            .all()
        )

        result = []
        for game, stats in games:
            is_home = game.home_team_id == team_id
            pf = game.home_team_score if is_home else game.away_team_score
            pa = game.away_team_score if is_home else game.home_team_score
            won = 1 if pf > pa else 0

            result.append(
                {
                    "game_id": game.id,
                    "pf": pf,
                    "pa": pa,
                    "won": won,
                    "elo": stats.elo_rating if stats else self.ELO_INITIAL,
                }
            )

        return result

    def _calculate_rest_days(self, team_id: int, game_date) -> int:
        """Calculate days of rest since last game."""
        prev_game = (
            self.session.query(Game)
            .filter(
                ((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
                & (Game.game_date < game_date)
                & (Game.status == "Final")
            )
            .order_by(Game.game_date.desc())
            .first()
        )

        if not prev_game:
            return None

        rest_days = (game_date - prev_game.game_date).days
        return rest_days

    def _is_back_to_back(self, team_id: int, game_date) -> bool:
        """Check if team is playing back-to-back games."""
        prev_game = (
            self.session.query(Game)
            .filter(
                ((Game.home_team_id == team_id) | (Game.away_team_id == team_id))
                & (Game.game_date < game_date)
                & (Game.status == "Final")
            )
            .order_by(Game.game_date.desc())
            .first()
        )

        if not prev_game:
            return False

        # Back-to-back if games are 1 day apart
        return (game_date - prev_game.game_date).days == 1

    def _get_latest_elo(self, team_id: int, game_date) -> float:
        """Get team's ELO rating before a specific game date."""
        latest_stats = (
            self.session.query(TeamGameStats)
            .join(Game, TeamGameStats.game_id == Game.id)
            .filter(
                (TeamGameStats.team_id == team_id)
                & (Game.game_date < game_date)
            )
            .order_by(Game.game_date.desc())
            .first()
        )

        if latest_stats:
            return latest_stats.elo_rating
        return self.ELO_INITIAL

    def _calculate_elo(self, team_elo: float, opponent_elo: float, won: int) -> float:
        """Calculate new ELO rating after a game."""
        expected_win_prob = 1.0 / (1.0 + 10 ** ((opponent_elo - team_elo) / 400.0))
        actual_score = won  # 1 for win, 0 for loss
        elo_change = self.ELO_K * (actual_score - expected_win_prob)
        return team_elo + elo_change

    @staticmethod
    def _rolling_average(values: List[float]) -> Optional[float]:
        """Calculate rolling average from list of values."""
        if not values:
            return None
        return sum(values) / len(values)
