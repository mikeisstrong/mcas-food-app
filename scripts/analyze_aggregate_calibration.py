#!/usr/bin/env python3
"""
Analyze model prediction calibration at aggregate level across entire dataset.
Shows predicted probability vs actual win rate in 5% increments.

Usage:
    python analyze_aggregate_calibration.py
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

from nba_2x2x2.data import DatabaseManager
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
        f"logs/calibration_aggregate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
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


def analyze_aggregate_calibration(model, X, y, dates):
    """
    Analyze prediction calibration at aggregate level for entire dataset.

    Args:
        model: Trained LightGBM model
        X: Feature matrix
        y: Target values
        dates: Game dates
    """
    logger.info("=" * 100)
    logger.info("AGGREGATE PREDICTION CALIBRATION ANALYSIS (ENTIRE DATASET)")
    logger.info("=" * 100)

    # Get predictions
    y_pred_proba = model.predict(X)

    # Create results dataframe
    results = pd.DataFrame({
        'date': dates,
        'pred_proba': y_pred_proba,
        'actual': y.values,
    })

    # Define probability buckets (5% increments)
    buckets = [
        (0.45, 0.50, "45-50%"),
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

    print("\n" + "=" * 100)
    print("CALIBRATION ANALYSIS - ALL GAMES (2019-2025)")
    print("=" * 100)
    print(f"\nTotal games analyzed: {len(results):,}")
    print(f"Win rate (actual): {results['actual'].mean():.1%}")
    print(f"Average predicted probability: {results['pred_proba'].mean():.1%}")

    print("\n" + "-" * 100)
    print(f"{'Prob Bucket':<15} {'Games':<12} {'% of Total':<12} {'Pred Avg':<12} {'Actual %':<12} {'Diff':<12} {'Calibration':<20}")
    print("-" * 100)

    all_bucket_data = []

    for min_prob, max_prob, label in buckets:
        bucket_data = results[
            (results['pred_proba'] >= min_prob) &
            (results['pred_proba'] < max_prob)
        ]

        if len(bucket_data) == 0:
            print(f"{label:<15} {'0':<12} {'0.0%':<12} {'-':<12} {'-':<12} {'-':<12} {'-':<20}")
            continue

        games = len(bucket_data)
        pct_of_total = games / len(results)
        pred_avg = bucket_data['pred_proba'].mean()
        actual_pct = bucket_data['actual'].mean()
        diff = actual_pct - pred_avg

        # Calibration assessment
        if abs(diff) <= 0.02:
            calibration = "✓ Excellent"
        elif abs(diff) <= 0.05:
            calibration = "✓ Good"
        elif abs(diff) <= 0.10:
            calibration = "⚠ Fair"
        else:
            calibration = "✗ Poor"

        print(f"{label:<15} {games:<12} {pct_of_total:<12.1%} {pred_avg:<12.1%} {actual_pct:<12.1%} {diff:+<12.1%} {calibration:<20}")

        all_bucket_data.append({
            'bucket': label,
            'games': games,
            'pct_of_total': pct_of_total,
            'pred_avg': pred_avg,
            'actual_pct': actual_pct,
            'difference': diff,
        })

    # Calculate calibration metrics
    print("\n" + "=" * 100)
    print("CALIBRATION METRICS")
    print("=" * 100)

    # Expected Calibration Error (ECE)
    ece = 0
    max_error = 0
    for min_prob, max_prob, label in buckets:
        bucket_data = results[
            (results['pred_proba'] >= min_prob) &
            (results['pred_proba'] < max_prob)
        ]
        if len(bucket_data) > 0:
            pred_avg = bucket_data['pred_proba'].mean()
            actual_pct = bucket_data['actual'].mean()
            error = abs(actual_pct - pred_avg)
            ece += (len(bucket_data) / len(results)) * error
            max_error = max(max_error, error)

    print(f"\nExpected Calibration Error (ECE):        {ece:.4f}")
    print(f"  → Measures average difference between predicted and actual probabilities")
    print(f"  → Range: 0.0 (perfect) to 1.0 (worst)")
    print(f"  → Your model: {'Excellent' if ece < 0.05 else 'Good' if ece < 0.10 else 'Fair'}")

    print(f"\nMaximum Calibration Error:               {max_error:.4f}")
    print(f"  → Largest single bucket error")

    # Brier Score
    brier = ((results['pred_proba'] - results['actual']) ** 2).mean()
    print(f"\nBrier Score:                             {brier:.4f}")
    print(f"  → Measures average squared difference between predictions and outcomes")
    print(f"  → Range: 0.0 (perfect) to 0.25 (worst for binary classification)")

    # Log Loss
    epsilon = 1e-15
    log_loss = -(results['actual'] * np.log(results['pred_proba'] + epsilon) +
                 (1 - results['actual']) * np.log(1 - results['pred_proba'] + epsilon)).mean()
    print(f"\nLog Loss:                                {log_loss:.4f}")
    print(f"  → Penalizes confident wrong predictions heavily")
    print(f"  → Lower is better")

    # Accuracy at different thresholds
    print(f"\n" + "=" * 100)
    print("ACCURACY AT DIFFERENT DECISION THRESHOLDS")
    print("=" * 100)
    print(f"{'Threshold':<15} {'Predictions':<15} {'Accuracy':<15}")
    print("-" * 100)

    for threshold in [0.50, 0.52, 0.54, 0.56, 0.58, 0.60, 0.62, 0.64, 0.66]:
        preds = (results['pred_proba'] >= threshold).astype(int)
        accuracy = (preds == results['actual']).mean()
        num_preds = preds.sum()
        print(f">= {threshold:.0%}          {num_preds:<15,} {accuracy:<15.1%}")

    # Prediction distribution
    print(f"\n" + "=" * 100)
    print("PREDICTION DISTRIBUTION")
    print("=" * 100)
    print(f"Minimum predicted probability:           {results['pred_proba'].min():.1%}")
    print(f"25th percentile:                         {results['pred_proba'].quantile(0.25):.1%}")
    print(f"Median (50th percentile):                {results['pred_proba'].quantile(0.50):.1%}")
    print(f"75th percentile:                         {results['pred_proba'].quantile(0.75):.1%}")
    print(f"Maximum predicted probability:           {results['pred_proba'].max():.1%}")
    print(f"Standard deviation:                      {results['pred_proba'].std():.1%}")

    # Separate analysis for home team win predictions
    print(f"\n" + "=" * 100)
    print("SEPARATE ANALYSIS: HOME TEAM WIN PREDICTIONS")
    print("=" * 100)
    home_accuracy = results['actual'].mean()
    print(f"Empirical home team win rate:            {home_accuracy:.1%}")
    print(f"Model average prediction (all games):    {results['pred_proba'].mean():.1%}")
    print(f"Difference:                              {(results['pred_proba'].mean() - home_accuracy):+.1%}")

    return results, all_bucket_data


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
        results, bucket_data = analyze_aggregate_calibration(model, X, y, dates)

        # Cleanup
        session.close()
        db_manager.disconnect()

        logger.info("\nAggregate calibration analysis completed!")

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
