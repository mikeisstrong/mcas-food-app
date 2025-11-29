#!/usr/bin/env python3
"""
Analyze prediction accuracy against actual game outcomes.
Evaluates:
1. Win probability calibration in 5% increments (45%-100%)
2. Point differential prediction errors (+/-1, 2, 3... 15 points)

Usage:
    python analyze_prediction_accuracy.py
"""

import sys
import os
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
from loguru import logger

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import Game, GamePrediction, TeamGameStats


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/prediction_accuracy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def analyze_win_probability_accuracy(session):
    """
    Analyze win probability predictions vs actual outcomes in 5% increments.
    """
    logger.info("=" * 100)
    logger.info("WIN PROBABILITY PREDICTION ACCURACY")
    logger.info("=" * 100)

    # Get all predictions with actual game outcomes
    results = session.query(
        GamePrediction.home_win_prob,
        GamePrediction.lightgbm_home_prob,
        GamePrediction.elo_home_prob,
        GamePrediction.point_differential,
        Game.home_team_score,
        Game.away_team_score,
        Game.game_date,
    ).join(Game).all()

    if not results:
        logger.error("No prediction results found!")
        return None

    # Convert to dataframe
    df = pd.DataFrame([
        {
            'home_win_prob': r.home_win_prob,
            'lightgbm_prob': r.lightgbm_home_prob,
            'elo_prob': r.elo_home_prob,
            'pred_diff': r.point_differential,
            'home_score': r.home_team_score,
            'away_score': r.away_team_score,
            'actual_diff': r.home_team_score - r.away_team_score,
            'home_won': 1 if r.home_team_score > r.away_team_score else 0,
            'game_date': r.game_date,
        }
        for r in results
    ])

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

    print("\n" + "=" * 120)
    print("WIN PROBABILITY ACCURACY BY BUCKET (5% Increments)")
    print("=" * 120)
    print(f"{'Prob Bucket':<15} {'Games':<10} {'Pred Avg':<12} {'Actual %':<12} {'Diff':<12} {'Accuracy':<12} {'Brier':<12}")
    print("-" * 120)

    overall_correct = 0
    overall_total = 0
    bucket_data = []

    for min_prob, max_prob, label in buckets:
        bucket_df = df[
            (df['home_win_prob'] >= min_prob) &
            (df['home_win_prob'] < max_prob)
        ]

        if len(bucket_df) == 0:
            print(f"{label:<15} {'0':<10} {'-':<12} {'-':<12} {'-':<12} {'-':<12} {'-':<12}")
            continue

        games = len(bucket_df)
        pred_avg = bucket_df['home_win_prob'].mean()
        actual_pct = bucket_df['home_won'].mean()
        diff = actual_pct - pred_avg

        # Accuracy: how often we predicted correctly (using 50% threshold)
        predicted_wins = (bucket_df['home_win_prob'] >= 0.5).astype(int)
        accuracy = (predicted_wins == bucket_df['home_won']).mean()

        # Brier score: mean squared error of probability predictions
        brier = ((bucket_df['home_win_prob'] - bucket_df['home_won']) ** 2).mean()

        print(f"{label:<15} {games:<10} {pred_avg:<12.1%} {actual_pct:<12.1%} {diff:+<12.1%} {accuracy:<12.1%} {brier:<12.4f}")

        overall_correct += (predicted_wins == bucket_df['home_won']).sum()
        overall_total += games

        bucket_data.append({
            'bucket': label,
            'games': games,
            'pred_avg': pred_avg,
            'actual_pct': actual_pct,
            'diff': diff,
            'accuracy': accuracy,
            'brier': brier,
        })

    # Overall accuracy
    print("-" * 120)
    overall_accuracy = overall_correct / overall_total if overall_total > 0 else 0
    print(f"{'OVERALL':<15} {overall_total:<10} {'N/A':<12} {'N/A':<12} {'N/A':<12} {overall_accuracy:<12.1%} {'N/A':<12}")

    return df, bucket_data


def analyze_point_differential_accuracy(df):
    """
    Analyze point differential prediction errors.
    """
    logger.info("\n" + "=" * 100)
    logger.info("POINT DIFFERENTIAL PREDICTION ACCURACY")
    logger.info("=" * 100)

    # Calculate absolute errors
    df['pred_error'] = np.abs(df['pred_diff'] - df['actual_diff'])

    print("\n" + "=" * 100)
    print("POINT DIFFERENTIAL PREDICTION ERROR DISTRIBUTION")
    print("=" * 100)
    print(f"Total games analyzed: {len(df):,}")
    print(f"\nError Statistics:")
    print(f"  Mean Absolute Error (MAE):    {df['pred_error'].mean():.2f} points")
    print(f"  Median Absolute Error:        {df['pred_error'].median():.2f} points")
    print(f"  Std Dev:                      {df['pred_error'].std():.2f} points")
    print(f"  Min Error:                    {df['pred_error'].min():.2f} points")
    print(f"  Max Error:                    {df['pred_error'].max():.2f} points")

    # Error distribution
    print(f"\n" + "=" * 100)
    print("ERROR MAGNITUDE DISTRIBUTION")
    print("=" * 100)
    print(f"{'Error Range':<20} {'Games':<12} {'% of Total':<15} {'Cumulative %':<15}")
    print("-" * 100)

    error_ranges = [
        (0, 1, "0-1 points"),
        (1, 2, "1-2 points"),
        (2, 3, "2-3 points"),
        (3, 4, "3-4 points"),
        (4, 5, "4-5 points"),
        (5, 6, "5-6 points"),
        (6, 7, "6-7 points"),
        (7, 8, "7-8 points"),
        (8, 9, "8-9 points"),
        (9, 10, "9-10 points"),
        (10, 11, "10-11 points"),
        (11, 12, "11-12 points"),
        (12, 13, "12-13 points"),
        (13, 14, "13-14 points"),
        (14, 15, "14-15 points"),
        (15, 1000, "15+ points"),
    ]

    cumulative = 0
    for min_err, max_err, label in error_ranges:
        in_range = ((df['pred_error'] >= min_err) & (df['pred_error'] < max_err)).sum()
        pct = in_range / len(df)
        cumulative += pct

        print(f"{label:<20} {in_range:<12} {pct:<15.1%} {cumulative:<15.1%}")

    # Performance by actual margin
    print(f"\n" + "=" * 100)
    print("PREDICTION ACCURACY BY ACTUAL GAME MARGIN")
    print("=" * 100)
    print(f"{'Margin Range':<20} {'Games':<12} {'Avg Error':<15} {'Median Error':<15}")
    print("-" * 100)

    margin_ranges = [
        (0, 5, "0-5 points"),
        (5, 10, "5-10 points"),
        (10, 15, "10-15 points"),
        (15, 20, "15-20 points"),
        (20, 1000, "20+ points"),
    ]

    for min_margin, max_margin, label in margin_ranges:
        margin_df = df[
            (df['actual_diff'].abs() >= min_margin) &
            (df['actual_diff'].abs() < max_margin)
        ]

        if len(margin_df) == 0:
            print(f"{label:<20} {'0':<12} {'-':<15} {'-':<15}")
            continue

        avg_error = margin_df['pred_error'].mean()
        median_error = margin_df['pred_error'].median()

        print(f"{label:<20} {len(margin_df):<12} {avg_error:<15.2f} {median_error:<15.2f}")

    # Direction accuracy (did we predict the right winner?)
    print(f"\n" + "=" * 100)
    print("PREDICTION DIRECTION ACCURACY (Right Winner Predicted)")
    print("=" * 100)

    df['pred_winner_correct'] = (
        ((df['pred_diff'] > 0) & (df['actual_diff'] > 0)) |
        ((df['pred_diff'] < 0) & (df['actual_diff'] < 0)) |
        ((df['pred_diff'] == 0) & (df['actual_diff'] == 0))
    ).astype(int)

    correct_direction = df['pred_winner_correct'].mean()
    print(f"\nPredicted correct winner (sign of point differential): {correct_direction:.1%}")
    print(f"  ({df['pred_winner_correct'].sum():,} out of {len(df):,} games)")

    return df


def analyze_model_component_performance(session, df):
    """
    Compare performance of LightGBM vs ELO components.
    """
    logger.info("\n" + "=" * 100)
    logger.info("MODEL COMPONENT COMPARISON")
    logger.info("=" * 100)

    # Get predictions with component scores
    results = session.query(
        GamePrediction.lightgbm_home_prob,
        GamePrediction.elo_home_prob,
        Game.home_team_score,
        Game.away_team_score,
    ).join(Game).all()

    component_df = pd.DataFrame([
        {
            'lightgbm_prob': r.lightgbm_home_prob,
            'elo_prob': r.elo_home_prob,
            'home_won': 1 if r.home_team_score > r.away_team_score else 0,
        }
        for r in results
    ])

    print("\n" + "=" * 100)
    print("COMPONENT MODEL COMPARISON")
    print("=" * 100)

    # Accuracy at 50% threshold
    lgb_pred = (component_df['lightgbm_prob'] >= 0.5).astype(int)
    elo_pred = (component_df['elo_prob'] >= 0.5).astype(int)

    lgb_accuracy = (lgb_pred == component_df['home_won']).mean()
    elo_accuracy = (elo_pred == component_df['home_won']).mean()

    print(f"\nAccuracy (50% threshold):")
    print(f"  LightGBM (70% weight): {lgb_accuracy:.1%}")
    print(f"  ELO-based (30% weight): {elo_accuracy:.1%}")

    # Brier scores
    lgb_brier = ((component_df['lightgbm_prob'] - component_df['home_won']) ** 2).mean()
    elo_brier = ((component_df['elo_prob'] - component_df['home_won']) ** 2).mean()

    print(f"\nBrier Score (lower is better):")
    print(f"  LightGBM: {lgb_brier:.4f}")
    print(f"  ELO-based: {elo_brier:.4f}")

    # Calibration (Expected Calibration Error)
    buckets = [(0.5, 0.6, "50-60%"), (0.6, 0.7, "60-70%"), (0.7, 0.8, "70-80%"), (0.8, 0.9, "80-90%")]

    print(f"\nCalibration by probability bucket:")
    print(f"{'Bucket':<15} {'LGB Actual %':<15} {'ELO Actual %':<15}")
    print("-" * 50)

    for min_p, max_p, label in buckets:
        lgb_bucket = component_df[(component_df['lightgbm_prob'] >= min_p) & (component_df['lightgbm_prob'] < max_p)]
        elo_bucket = component_df[(component_df['elo_prob'] >= min_p) & (component_df['elo_prob'] < max_p)]

        lgb_actual = lgb_bucket['home_won'].mean() if len(lgb_bucket) > 0 else 0
        elo_actual = elo_bucket['home_won'].mean() if len(elo_bucket) > 0 else 0

        print(f"{label:<15} {lgb_actual:<15.1%} {elo_actual:<15.1%}")


def main():
    """Main entry point."""
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    try:
        # Connect to database
        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()
        session = db_manager.get_session()

        # Analyze win probability accuracy
        df, bucket_data = analyze_win_probability_accuracy(session)

        if df is not None:
            # Analyze point differential accuracy
            analyze_point_differential_accuracy(df)

            # Compare model components
            analyze_model_component_performance(session, df)

        # Cleanup
        session.close()
        db_manager.disconnect()

        logger.info("\n" + "=" * 100)
        logger.info("Prediction accuracy analysis completed!")
        logger.info("=" * 100)

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
