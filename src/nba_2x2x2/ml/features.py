"""
Feature engineering for game prediction models.
Extracts features from team_game_stats for home and away teams.
"""

from typing import Tuple, List
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from loguru import logger

from nba_2x2x2.data.models import Game, TeamGameStats, Team


class FeatureEngineer:
    """Extract and engineer features for model training."""

    ELO_INITIAL = 1500.0

    # Feature columns to use
    FEATURE_COLUMNS = [
        # Home team metrics
        'home_elo',
        'home_ppf',
        'home_ppa',
        'home_point_diff',
        'home_win_pct',
        'home_ppf_5game',
        'home_ppa_5game',
        'home_diff_5game',
        'home_ppf_10game',
        'home_ppa_10game',
        'home_diff_10game',
        'home_ppf_20game',
        'home_ppa_20game',
        'home_diff_20game',
        'home_days_rest',
        'home_back_to_back',

        # Away team metrics
        'away_elo',
        'away_ppf',
        'away_ppa',
        'away_point_diff',
        'away_win_pct',
        'away_ppf_5game',
        'away_ppa_5game',
        'away_diff_5game',
        'away_ppf_10game',
        'away_ppa_10game',
        'away_diff_10game',
        'away_ppf_20game',
        'away_ppa_20game',
        'away_diff_20game',
        'away_days_rest',
        'away_back_to_back',

        # Interaction features
        'elo_diff',
        'ppf_diff',
        'ppa_diff',
        'diff_5game_diff',
        'diff_10game_diff',
        'diff_20game_diff',
    ]

    def __init__(self, session: Session):
        """Initialize feature engineer."""
        self.session = session

    def _get_pre_game_elo(self, team_id: int, game: Game) -> float:
        """
        Get the team's ELO prior to the specified game.

        Uses the most recent TeamGameStats row before this game (by date and id)
        to avoid leaking post-game ELO from the game we're predicting.
        """
        stats = (
            self.session.query(TeamGameStats)
            .join(Game, TeamGameStats.game_id == Game.id)
            .filter(TeamGameStats.team_id == team_id)
            .filter(
                (Game.game_date < game.game_date)
                | ((Game.game_date == game.game_date) & (Game.id < game.id))
            )
            .order_by(Game.game_date.desc(), Game.id.desc())
            .first()
        )

        if stats:
            return stats.elo_rating
        return self.ELO_INITIAL

    def extract_features(self, game: Game) -> dict:
        """Extract features for a single game."""
        home_stats = (
            self.session.query(TeamGameStats)
            .filter_by(game_id=game.id, is_home=1)
            .first()
        )
        away_stats = (
            self.session.query(TeamGameStats)
            .filter_by(game_id=game.id, is_home=0)
            .first()
        )

        if not home_stats or not away_stats:
            return None

        features = {
            # Home team metrics
            'home_elo': self._get_pre_game_elo(game.home_team_id, game),
            'home_ppf': home_stats.points_for,
            'home_ppa': home_stats.points_against,
            'home_point_diff': home_stats.point_differential,
            'home_win_pct': home_stats.win_pct,
            'home_ppf_5game': home_stats.ppf_5game,
            'home_ppa_5game': home_stats.ppa_5game,
            'home_diff_5game': home_stats.diff_5game,
            'home_ppf_10game': home_stats.ppf_10game,
            'home_ppa_10game': home_stats.ppa_10game,
            'home_diff_10game': home_stats.diff_10game,
            'home_ppf_20game': home_stats.ppf_20game,
            'home_ppa_20game': home_stats.ppa_20game,
            'home_diff_20game': home_stats.diff_20game,
            'home_days_rest': home_stats.days_rest if home_stats.days_rest else 0,
            'home_back_to_back': home_stats.back_to_back,

            # Away team metrics
            'away_elo': self._get_pre_game_elo(game.away_team_id, game),
            'away_ppf': away_stats.points_for,
            'away_ppa': away_stats.points_against,
            'away_point_diff': away_stats.point_differential,
            'away_win_pct': away_stats.win_pct,
            'away_ppf_5game': away_stats.ppf_5game,
            'away_ppa_5game': away_stats.ppa_5game,
            'away_diff_5game': away_stats.diff_5game,
            'away_ppf_10game': away_stats.ppf_10game,
            'away_ppa_10game': away_stats.ppa_10game,
            'away_diff_10game': away_stats.diff_10game,
            'away_ppf_20game': away_stats.ppf_20game,
            'away_ppa_20game': away_stats.ppa_20game,
            'away_diff_20game': away_stats.diff_20game,
            'away_days_rest': away_stats.days_rest if away_stats.days_rest else 0,
            'away_back_to_back': away_stats.back_to_back,
        }

        # Add interaction features
        features['elo_diff'] = features['home_elo'] - features['away_elo']
        features['ppf_diff'] = features['home_ppf'] - features['away_ppf']
        features['ppa_diff'] = features['home_ppa'] - features['away_ppa']

        # Handle None values in rolling averages
        home_diff_5 = features['home_diff_5game'] if features['home_diff_5game'] is not None else 0
        away_diff_5 = features['away_diff_5game'] if features['away_diff_5game'] is not None else 0
        features['diff_5game_diff'] = home_diff_5 - away_diff_5

        home_diff_10 = features['home_diff_10game'] if features['home_diff_10game'] is not None else 0
        away_diff_10 = features['away_diff_10game'] if features['away_diff_10game'] is not None else 0
        features['diff_10game_diff'] = home_diff_10 - away_diff_10

        home_diff_20 = features['home_diff_20game'] if features['home_diff_20game'] is not None else 0
        away_diff_20 = features['away_diff_20game'] if features['away_diff_20game'] is not None else 0
        features['diff_20game_diff'] = home_diff_20 - away_diff_20

        return features

    def build_dataset(self, min_season: int = 2019, max_season: int = 2025) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """
        Build complete feature dataset.

        Returns:
            X: DataFrame with features
            y: Series with targets (1 if home team won, 0 if away team won)
            dates: List of game dates for time-based splitting
        """
        logger.info(f"Building feature dataset for seasons {min_season}-{max_season}...")

        games = (
            self.session.query(Game)
            .filter(Game.status == "Final")
            .filter(Game.season >= min_season)
            .filter(Game.season <= max_season)
            .order_by(Game.game_date)
            .all()
        )

        logger.info(f"Processing {len(games)} games...")

        X_list = []
        y_list = []
        dates = []

        for idx, game in enumerate(games):
            if (idx + 1) % 1000 == 0:
                logger.info(f"Processed {idx + 1}/{len(games)} games")

            features = self.extract_features(game)
            if features is None:
                continue

            X_list.append(features)
            # Target: 1 if home team won, 0 if away team won
            y_list.append(1 if game.home_team_score > game.away_team_score else 0)
            dates.append(pd.Timestamp(game.game_date))

        logger.info(f"Extracted features for {len(X_list)} games")

        # Create DataFrame
        X = pd.DataFrame(X_list)

        # Fill NaN values with 0 (from rolling averages that may not have enough games)
        X = X.fillna(0)

        y = pd.Series(y_list)

        logger.info(f"Feature matrix shape: {X.shape}")
        logger.info(f"Target distribution: {y.value_counts().to_dict()}")

        return X, y, dates

    @staticmethod
    def get_feature_columns() -> List[str]:
        """Get list of feature column names."""
        return FeatureEngineer.FEATURE_COLUMNS
