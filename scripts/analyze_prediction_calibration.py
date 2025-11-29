#!/usr/bin/env python3
"""
Analyze model prediction calibration by probability buckets.
Shows predicted probability vs actual win rate for each season.

Usage:
    python analyze_prediction_calibration.py
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
from sqlalchemy.orm import Session

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import Game
from nba_2x2x2.ml.features import FeatureEngineer


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def load_model(model_path):
    """Load trained model from pickle file."""
    try:
        with open(model_path, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        logger.error(f"Failed to load model from {model_path}: {e}")
        return None


def get_season_from_date(game_date):
    """Get NBA season year from game date."""
    if game_date.month >= 10:  # Oct-Dec = start of season
        return game_date.year + 1
    else:  # Jan-Sep = end of season
        return game_date.year


def analyze_calibration(session: Session, model, X, y, dates, features):
    """
    Analyze prediction calibration by probability buckets.

    Args:
        session: Database session
        model: Trained LightGBM model
        X: Feature matrix
        y: Target values
        dates: Game dates
        features: Feature column names
    """
    logger.info("=" * 80)
    logger.info("PREDICTION CALIBRATION ANALYSIS")
    logger.info("=" * 80)

    # Get predictions
    y_pred_proba = model.predict(X)

    # Create results dataframe
    results = pd.DataFrame({
        'date': dates,
        'pred_proba': y_pred_proba,
        'actual': y.values,
        'season': [get_season_from_date(d) for d in dates]
    })

    # Define probability buckets (5% increments)
    buckets = [
        (0.50, 0.55, "50-55%"),
        (0.55, 0.60, "55-60%"),
        (0.60, 0.65, "60-65%"),
        (0.65, 0.70, "65-70%"),
        (0.70, 0.75, "70-75%"),
        (0.75, 0.80, "75-80%"),
        (0.80, 0.85, "80-85%"),
        (0.85, 0.90, "85-90%"),
        (0.90, 0.95, "90-95%"),
        (0.95, 1.00, "95-100%"),
    ]

    # Analysis by season
    seasons = sorted(results['season'].unique())

    print("\n" + "=" * 80)
    print("CALIBRATION BY SEASON AND PROBABILITY BUCKET")
    print("=" * 80)

    all_results = []

    for season in seasons:
        season_data = results[results['season'] == season]

        if len(season_data) == 0:
            continue

        print(f"\n{'SEASON ' + str(season):^80}")
        print("-" * 80)
        print(f"{'Prob Bucket':<15} {'Games':<10} {'Pred Avg':<12} {'Actual %':<12} {'Difference':<12}")
        print("-" * 80)

        for min_prob, max_prob, label in buckets:
            bucket_data = season_data[
                (season_data['pred_proba'] >= min_prob) &
                (season_data['pred_proba'] < max_prob)
            ]

            if len(bucket_data) == 0:
                print(f"{label:<15} {'0':<10} {'-':<12} {'-':<12} {'-':<12}")
                continue

            games = len(bucket_data)
            pred_avg = bucket_data['pred_proba'].mean()
            actual_pct = bucket_data['actual'].mean()
            diff = actual_pct - pred_avg

            print(f"{label:<15} {games:<10} {pred_avg:.1%} {'  ':<8} {actual_pct:.1%} {'  ':<8} {diff:+.1%}")

            all_results.append({
                'season': season,
                'bucket': label,
                'games': games,
                'pred_avg': pred_avg,
                'actual_pct': actual_pct,
                'difference': diff,
            })

    # Overall calibration
    print(f"\n{'OVERALL':^80}")
    print("-" * 80)
    print(f"{'Prob Bucket':<15} {'Games':<10} {'Pred Avg':<12} {'Actual %':<12} {'Difference':<12}")
    print("-" * 80)

    for min_prob, max_prob, label in buckets:
        bucket_data = results[
            (results['pred_proba'] >= min_prob) &
            (results['pred_proba'] < max_prob)
        ]

        if len(bucket_data) == 0:
            print(f"{label:<15} {'0':<10} {'-':<12} {'-':<12} {'-':<12}")
            continue

        games = len(bucket_data)
        pred_avg = bucket_data['pred_proba'].mean()
        actual_pct = bucket_data['actual'].mean()
        diff = actual_pct - pred_avg

        print(f"{label:<15} {games:<10} {pred_avg:.1%} {'  ':<8} {actual_pct:.1%} {'  ':<8} {diff:+.1%}")

    # Calculate calibration metrics
    print("\n" + "=" * 80)
    print("CALIBRATION METRICS")
    print("=" * 80)

    # Expected Calibration Error (ECE)
    ece = 0
    for min_prob, max_prob, label in buckets:
        bucket_data = results[
            (results['pred_proba'] >= min_prob) &
            (results['pred_proba'] < max_prob)
        ]
        if len(bucket_data) > 0:
            pred_avg = bucket_data['pred_proba'].mean()
            actual_pct = bucket_data['actual'].mean()
            ece += (len(bucket_data) / len(results)) * abs(actual_pct - pred_avg)

    print(f"Expected Calibration Error (ECE): {ece:.4f}")
    print(f"  (Lower is better - measures average difference between predicted and actual)")

    # Accuracy at different thresholds
    print(f"\nAccuracy at different prediction thresholds:")
    for threshold in [0.5, 0.55, 0.60, 0.65]:
        preds = (results['pred_proba'] >= threshold).astype(int)
        accuracy = (preds == results['actual']).mean()
        print(f"  Threshold >= {threshold:.0%}: {accuracy:.1%}")


def main():
    """Main entry point."""
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    try:
        # Load model
        logger.info("Loading trained model...")
        model = load_model("models/lightgbm_model.pkl")
        if model is None:
            logger.error("Failed to load model. Make sure to train first: python scripts/train_models.py")
            sys.exit(1)

        # Load data
        logger.info("Loading data...")
        db_manager = DatabaseManager()
        db_manager.connect()
        session = db_manager.get_session()

        # Build features
        feature_engineer = FeatureEngineer(session)
        X, y, dates = feature_engineer.build_dataset()
        features = FeatureEngineer.get_feature_columns()

        # Analyze calibration
        analyze_calibration(session, model, X, y, dates, features)

        # Cleanup
        session.close()
        db_manager.disconnect()

        logger.info("\nCalibration analysis completed!")

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
