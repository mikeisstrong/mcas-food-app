#!/usr/bin/env python3
"""
Train game prediction models using complete metrics dataset.

Usage:
    python train_models.py

This script:
1. Loads team_game_stats from database
2. Builds feature matrix using FeatureEngineer
3. Performs time-based train/test split
4. Trains LightGBM and XGBoost models
5. Evaluates both models
6. Generates feature importance
7. Saves trained models to disk
"""

import sys
import os
from datetime import datetime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
import pandas as pd
from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.ml.features import FeatureEngineer
from nba_2x2x2.ml.models import GamePredictor


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def train_models():
    """Train game prediction models."""
    logger.info("=" * 80)
    logger.info("NBA Game Prediction - Model Training Pipeline")
    logger.info("=" * 80)

    try:
        # Initialize database
        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()

        # Get session for feature engineering
        session = db_manager.get_session()

        # Build feature matrix
        logger.info("\n" + "=" * 80)
        logger.info("FEATURE ENGINEERING")
        logger.info("=" * 80)

        engineer = FeatureEngineer(session)
        logger.info("Building feature dataset from team_game_stats...")
        X, y, dates = engineer.build_dataset(min_season=2019, max_season=2025)

        logger.info(f"Feature matrix built:")
        logger.info(f"  Shape: {X.shape}")
        logger.info(f"  Games: {len(X)}")
        logger.info(f"  Features: {len(X.columns)}")
        logger.info(f"  Target distribution: {y.value_counts().to_dict()}")
        logger.info(f"  Date range: {dates[0]} to {dates[-1]}")

        # Initialize predictor
        predictor = GamePredictor(model_dir="models")

        # Time-based train/test split
        logger.info("\n" + "=" * 80)
        logger.info("TRAIN/TEST SPLIT")
        logger.info("=" * 80)

        X_train, X_test, y_train, y_test = predictor.time_based_split(
            X, y, dates,
            train_cutoff_date="2024-01-01",
            test_cutoff_date="2025-01-01"
        )

        # Train LightGBM
        logger.info("\n" + "=" * 80)
        logger.info("LIGHTGBM TRAINING")
        logger.info("=" * 80)

        lgb_results = predictor.train_lightgbm(X_train, y_train, X_test, y_test)

        # Train XGBoost
        logger.info("\n" + "=" * 80)
        logger.info("XGBOOST TRAINING")
        logger.info("=" * 80)

        xgb_results = predictor.train_xgboost(X_train, y_train, X_test, y_test)
        if xgb_results is None:
            logger.warning("Skipping XGBoost - not installed")

        # Feature importance
        logger.info("\n" + "=" * 80)
        logger.info("FEATURE IMPORTANCE ANALYSIS")
        logger.info("=" * 80)

        logger.info("LightGBM - Top 20 Features:")
        lgb_importance = predictor.get_feature_importance("lightgbm", top_n=20)
        if lgb_importance is not None:
            for idx, row in lgb_importance.iterrows():
                logger.info(f"  {idx + 1:2d}. {row['feature']:30s} {row['importance']:8.1f}")

        logger.info("\nXGBoost - Top 20 Features:")
        xgb_importance = predictor.get_feature_importance("xgboost", top_n=20)
        if xgb_importance is not None:
            for idx, row in xgb_importance.iterrows():
                logger.info(f"  {idx + 1:2d}. {row['feature']:30s} {row['importance']:8.1f}")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("MODEL TRAINING SUMMARY")
        logger.info("=" * 80)

        if lgb_results:
            logger.info("LightGBM Results:")
            for metric, value in lgb_results.items():
                if metric != "model":
                    logger.info(f"  {metric:12s}: {value:.4f}")

        if xgb_results:
            logger.info("\nXGBoost Results:")
            for metric, value in xgb_results.items():
                if metric != "model":
                    logger.info(f"  {metric:12s}: {value:.4f}")

        logger.info("\n" + "=" * 80)
        logger.info("Model training completed successfully!")
        logger.info(f"Models saved to: models/")
        logger.info("=" * 80)

        # Cleanup
        session.close()
        db_manager.disconnect()

    except Exception as e:
        logger.error(f"Model training failed: {e}", exc_info=True)
        sys.exit(1)


def main():
    """Main entry point."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Setup logging
    setup_logging()

    # Train models
    train_models()


if __name__ == "__main__":
    main()
