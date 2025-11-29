#!/usr/bin/env python3
"""
Generate comprehensive game predictions for all games.
Includes:
1. LightGBM win probability (70% weight)
2. ELO-based win probability (30% weight)
3. Blended win probability
4. Point differential predictions (separate regression model)

Usage:
    python generate_game_predictions.py
"""

import sys
import os
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pickle
import pandas as pd
import numpy as np
from loguru import logger
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import Game, TeamGameStats, GamePrediction
from nba_2x2x2.ml.features import FeatureEngineer
from sqlalchemy.orm import Session


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def get_pre_game_elo(session: Session, team_id: int, game: Game) -> float:
    """
    Get the team's ELO rating BEFORE a specific game was played.

    CRITICAL: This prevents data leakage by using only pre-game ELO values.
    For a game on date D, we get the team's ELO from before date D.

    Uses the most recent TeamGameStats row before this game (by date and id)
    to avoid leaking post-game ELO from the game we're predicting.

    Args:
        session: Database session
        team_id: Team ID
        game: Game object to get pre-game ELO for

    Returns:
        Pre-game ELO rating (float), or 1500.0 if no prior games exist
    """
    stats = (
        session.query(TeamGameStats)
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
    return 1500.0  # ELO_INITIAL


def load_lightgbm_model(model_path):
    """Load trained LightGBM model."""
    try:
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load LightGBM model: {e}")
        return None


def train_point_differential_model(session, feature_engineer, X, y, dates):
    """
    Train a regression model to predict point differential.

    Uses time-based split to avoid temporal leakage:
    - Training: games through 2024-01-01
    - Test: games from 2025-01-01 onwards
    - Validation gap: 2024-01-02 to 2024-12-31 (not used)

    Args:
        session: Database session
        feature_engineer: FeatureEngineer instance
        X: Feature matrix
        y: Target values (win/loss)
        dates: Game dates

    Returns:
        Trained model and feature names
    """
    logger.info("=" * 80)
    logger.info("TRAINING POINT DIFFERENTIAL REGRESSION MODEL")
    logger.info("=" * 80)

    # Get actual point differentials from games
    games = session.query(Game).filter(Game.status == "Final").order_by(Game.game_date).all()

    game_differentials = {}
    game_dates = {}
    for game in games:
        diff = game.home_team_score - game.away_team_score
        game_differentials[game.id] = diff
        game_dates[game.id] = game.game_date

    # Build mapping of dataset indices to game IDs and dates
    # This replaces the fragile offset-based loop
    dataset_games = []
    for idx in range(len(X)):
        # Find the idx-th Final game ordered by date
        game = session.query(Game).filter(Game.status == "Final").order_by(Game.game_date).offset(idx).first()
        if game:
            dataset_games.append((idx, game.id, game.game_date))

    # Extract differentials and dates aligned with X
    differentials = []
    game_dates_aligned = []
    for idx, game_id, game_date in dataset_games:
        if game_id in game_differentials:
            differentials.append(game_differentials[game_id])
            game_dates_aligned.append(pd.Timestamp(game_date))

    if not differentials:
        logger.error("No game differentials found")
        return None

    # Create aligned dataframe
    X_diff = X.iloc[:len(differentials)].reset_index(drop=True)
    y_diff = pd.Series(differentials).reset_index(drop=True)
    dates_diff = pd.Series(game_dates_aligned).reset_index(drop=True)

    logger.info(f"Total data size: {len(X_diff)} games")
    logger.info(f"Point differential range: {y_diff.min():.1f} to {y_diff.max():.1f}")
    logger.info(f"Mean point differential: {y_diff.mean():.1f}")

    # Time-based split matching LightGBM approach
    train_cutoff = pd.to_datetime("2024-01-01")
    test_cutoff = pd.to_datetime("2025-01-01")

    train_mask = dates_diff <= train_cutoff
    test_mask = dates_diff >= test_cutoff

    X_train = X_diff[train_mask].reset_index(drop=True)
    X_test = X_diff[test_mask].reset_index(drop=True)
    y_train = y_diff[train_mask].reset_index(drop=True)
    y_test = y_diff[test_mask].reset_index(drop=True)

    logger.info(f"Train set: {len(X_train)} games (through {train_cutoff.date()})")
    logger.info(f"Test set: {len(X_test)} games (from {test_cutoff.date()} onwards)")
    logger.info(f"Train/Test mean differential: {y_train.mean():.2f} / {y_test.mean():.2f}")

    # Train GradientBoosting model for point differential
    logger.info("Training GradientBoostingRegressor...")
    model = GradientBoostingRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=7,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=42,
        verbose=0,
    )

    model.fit(X_train, y_train)

    # Evaluate
    y_pred_test = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
    r2 = r2_score(y_test, y_pred_test)

    logger.info(f"\nPoint Differential Model Results:")
    logger.info(f"  MAE (Mean Absolute Error):  {mae:.2f} points")
    logger.info(f"  RMSE (Root Mean Squared):   {rmse:.2f} points")
    logger.info(f"  R² Score:                   {r2:.4f}")

    # Save model
    os.makedirs("models", exist_ok=True)
    with open("models/point_diff_model.pkl", "wb") as f:
        pickle.dump(model, f)
    logger.info("Point differential model saved to models/point_diff_model.pkl")

    return model


def get_elo_win_probability(home_elo, away_elo):
    """
    Calculate win probability from ELO ratings.
    Formula: 1 / (1 + 10^((opponent_elo - team_elo) / 400))
    """
    expected_win_prob = 1.0 / (1.0 + 10 ** ((away_elo - home_elo) / 400.0))
    return expected_win_prob


def get_latest_team_stats(session, team_id, before_game_date=None):
    """
    Get the latest team stats for a team, optionally before a given date.
    Used as fallback when game-specific stats are missing.

    Args:
        session: Database session
        team_id: Team ID
        before_game_date: Only get stats before this date (optional)

    Returns:
        TeamGameStats or None
    """
    query = session.query(TeamGameStats).filter(
        TeamGameStats.team_id == team_id
    )

    if before_game_date:
        query = query.join(Game, TeamGameStats.game_id == Game.id).filter(
            Game.game_date < before_game_date
        )

    return query.order_by(TeamGameStats.id.desc()).first()


def generate_predictions(session, lightgbm_model, point_diff_model, X, y, dates, features):
    """
    Generate blended predictions for all games.

    Blend: 70% LightGBM + 30% ELO

    Handles games with missing team stats by using the latest available stats as fallback.
    """
    logger.info("=" * 80)
    logger.info("GENERATING GAME PREDICTIONS")
    logger.info("=" * 80)

    # Get LightGBM predictions
    lightgbm_probs = lightgbm_model.predict(X)

    # Get all games (not just Final - includes scheduled/future games)
    games = session.query(Game).order_by(Game.game_date).all()

    games_for_prediction = games
    if len(games) != len(lightgbm_probs):
        logger.warning(f"Game count mismatch: {len(games)} games vs {len(lightgbm_probs)} predictions")
        # For games beyond the training set, we'll generate predictions without LightGBM
        games_for_prediction = games

    # Clear existing predictions
    session.query(GamePrediction).delete()
    session.commit()

    predictions_created = 0
    predictions_skipped = 0

    for idx, game in enumerate(games_for_prediction):
        if idx % 1000 == 0:
            logger.info(f"Processing game {idx + 1}/{len(games_for_prediction)}")

        try:
            # Try to get game-specific team stats
            home_stats = session.query(TeamGameStats).filter_by(
                game_id=game.id, is_home=1
            ).first()
            away_stats = session.query(TeamGameStats).filter_by(
                game_id=game.id, is_home=0
            ).first()

            # Fallback: use latest team stats if game-specific stats are missing
            if not home_stats:
                home_stats = get_latest_team_stats(session, game.home_team_id, game.game_date)
            if not away_stats:
                away_stats = get_latest_team_stats(session, game.away_team_id, game.game_date)

            # Skip if we still can't find stats for either team
            if not home_stats or not away_stats:
                predictions_skipped += 1
                continue

            # LightGBM probability (70% weight)
            # Use model prediction if available, otherwise use neutral 0.5
            if idx < len(lightgbm_probs):
                lgb_home_prob = lightgbm_probs[idx]
            else:
                lgb_home_prob = 0.5
                logger.debug(f"Using neutral LightGBM prob (0.5) for game {game.id} (beyond training set)")

            # ELO probability (30% weight)
            # CRITICAL: Use PRE-GAME ELO to prevent data leakage
            # home_stats.elo_rating is POST-GAME from that game, so we calculate pre-game ELO
            pre_game_elo_home = get_pre_game_elo(session, game.home_team_id, game)
            pre_game_elo_away = get_pre_game_elo(session, game.away_team_id, game)

            elo_home_prob = get_elo_win_probability(
                pre_game_elo_home,
                pre_game_elo_away
            )

            # Blended probability
            blended_home_prob = (0.70 * lgb_home_prob) + (0.30 * elo_home_prob)

            # Point differential prediction
            if point_diff_model and idx < len(X):
                point_diff = point_diff_model.predict(X.iloc[[idx]])[0]
            else:
                # Fallback: estimate from team stats
                point_diff = (home_stats.point_differential - away_stats.point_differential) / 2

            # Create prediction
            prediction = GamePrediction(
                game_id=int(game.id),
                home_win_prob=float(max(0.0, min(1.0, blended_home_prob))),
                away_win_prob=float(max(0.0, min(1.0, 1.0 - blended_home_prob))),
                point_differential=float(point_diff),
                lightgbm_home_prob=float(lgb_home_prob),
                elo_home_prob=float(elo_home_prob),
            )

            session.add(prediction)
            predictions_created += 1

        except Exception as e:
            logger.warning(f"Failed to create prediction for game {game.id}: {str(e)}")
            predictions_skipped += 1
            continue

    session.commit()

    logger.info(f"\nPredictions created: {predictions_created}")
    logger.info(f"Predictions skipped: {predictions_skipped}")
    logger.info("Game predictions table updated successfully")


def main():
    """Main entry point."""
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    try:
        # Load models and data
        logger.info("Loading trained LightGBM model...")
        lightgbm_model = load_lightgbm_model("models/lightgbm_model.pkl")
        if lightgbm_model is None:
            logger.error("Failed to load LightGBM model. Run: python scripts/train_models.py")
            sys.exit(1)

        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()
        session = db_manager.get_session()

        # Create game_predictions table if it doesn't exist
        logger.info("Ensuring game_predictions table exists...")
        from nba_2x2x2.data.models import Base
        Base.metadata.create_all(db_manager.engine)

        # Build features
        logger.info("Building feature dataset...")
        feature_engineer = FeatureEngineer(session)
        X, y, dates = feature_engineer.build_dataset()
        features = FeatureEngineer.get_feature_columns()

        # Train point differential model
        logger.info("Training point differential regression model...")
        point_diff_model = train_point_differential_model(
            session, feature_engineer, X, y, dates
        )

        # Generate predictions
        logger.info("Generating blended predictions...")
        generate_predictions(session, lightgbm_model, point_diff_model, X, y, dates, features)

        # Cleanup
        session.close()
        db_manager.disconnect()

        logger.info("\n" + "=" * 80)
        logger.info("Game prediction generation completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Prediction generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
