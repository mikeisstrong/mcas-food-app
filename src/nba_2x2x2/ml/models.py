"""
Model training and evaluation for game prediction.
Supports LightGBM and XGBoost with time-based cross-validation.
"""

from typing import Tuple, Dict, List
from datetime import datetime, timedelta
import pickle
import os
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score
from loguru import logger

from nba_2x2x2.config import Config

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False


class GamePredictor:
    """Train and evaluate game prediction models."""

    def __init__(self, model_dir: str = "models"):
        """Initialize predictor."""
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

        self.lgb_model = None
        self.xgb_model = None
        self.feature_names = None

    def time_based_split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dates: List,
        train_cutoff_date: str = "2024-01-01",
        test_cutoff_date: str = "2025-01-01",
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split data by time to avoid look-ahead bias.

        Args:
            X: Feature matrix
            y: Target vector
            dates: List of game dates
            train_cutoff_date: Last date to include in training (YYYY-MM-DD)
            test_cutoff_date: First date to include in test (YYYY-MM-DD)

        Returns:
            X_train, X_test, y_train, y_test
        """
        train_cutoff = pd.to_datetime(train_cutoff_date)
        test_cutoff = pd.to_datetime(test_cutoff_date)

        dates_series = pd.Series(dates)

        train_mask = dates_series <= train_cutoff
        test_mask = dates_series >= test_cutoff

        X_train = X[train_mask].reset_index(drop=True)
        y_train = y[train_mask].reset_index(drop=True)

        X_test = X[test_mask].reset_index(drop=True)
        y_test = y[test_mask].reset_index(drop=True)

        logger.info(f"Train set: {len(X_train)} games (through {train_cutoff_date})")
        logger.info(f"Test set: {len(X_test)} games (from {test_cutoff_date} onwards)")
        logger.info(f"Train/Test win rate: {y_train.mean():.3f} / {y_test.mean():.3f}")

        return X_train, X_test, y_train, y_test

    def train_lightgbm(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        params: Dict = None,
    ) -> Dict:
        """Train LightGBM model."""
        if not LIGHTGBM_AVAILABLE:
            logger.error("LightGBM not installed")
            return None

        logger.info("Training LightGBM model...")

        # Get default parameters from configuration
        default_params = Config.get_lightgbm_params()

        if params:
            default_params.update(params)

        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

        self.lgb_model = lgb.train(
            default_params,
            train_data,
            num_boost_round=Config.LIGHTGBM_NUM_BOOST_ROUND,
            valid_sets=[valid_data],
            valid_names=["test"],
            callbacks=[
                lgb.early_stopping(Config.LIGHTGBM_EARLY_STOPPING_ROUNDS),
                lgb.log_evaluation(period=0),
            ],
        )

        # Get predictions
        y_pred = self.lgb_model.predict(X_test)
        y_pred_binary = (y_pred > 0.5).astype(int)

        # Evaluate
        results = {
            "model": "LightGBM",
            "accuracy": accuracy_score(y_test, y_pred_binary),
            "auc": roc_auc_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred_binary),
            "recall": recall_score(y_test, y_pred_binary),
            "f1": f1_score(y_test, y_pred_binary),
        }

        logger.info(f"LightGBM Results:")
        logger.info(f"  Accuracy: {results['accuracy']:.4f}")
        logger.info(f"  AUC: {results['auc']:.4f}")
        logger.info(f"  Precision: {results['precision']:.4f}")
        logger.info(f"  Recall: {results['recall']:.4f}")
        logger.info(f"  F1-Score: {results['f1']:.4f}")

        # Save model
        model_path = os.path.join(self.model_dir, "lightgbm_model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(self.lgb_model, f)
        logger.info(f"LightGBM model saved to {model_path}")

        self.feature_names = X_train.columns.tolist()
        return results

    def train_xgboost(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        params: Dict = None,
    ) -> Dict:
        """Train XGBoost model."""
        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost not installed")
            return None

        logger.info("Training XGBoost model...")

        default_params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 10,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "min_child_weight": 1,
            "verbosity": 0,
        }

        if params:
            default_params.update(params)

        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=X_train.columns.tolist())
        dtest = xgb.DMatrix(X_test, label=y_test, feature_names=X_test.columns.tolist())

        evals = [(dtrain, "train"), (dtest, "test")]
        evals_result = {}

        self.xgb_model = xgb.train(
            default_params,
            dtrain,
            num_boost_round=500,
            evals=evals,
            evals_result=evals_result,
            early_stopping_rounds=50,
            verbose_eval=False,
        )

        # Get predictions
        y_pred = self.xgb_model.predict(dtest)
        y_pred_binary = (y_pred > 0.5).astype(int)

        # Evaluate
        results = {
            "model": "XGBoost",
            "accuracy": accuracy_score(y_test, y_pred_binary),
            "auc": roc_auc_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred_binary),
            "recall": recall_score(y_test, y_pred_binary),
            "f1": f1_score(y_test, y_pred_binary),
        }

        logger.info(f"XGBoost Results:")
        logger.info(f"  Accuracy: {results['accuracy']:.4f}")
        logger.info(f"  AUC: {results['auc']:.4f}")
        logger.info(f"  Precision: {results['precision']:.4f}")
        logger.info(f"  Recall: {results['recall']:.4f}")
        logger.info(f"  F1-Score: {results['f1']:.4f}")

        # Save model
        model_path = os.path.join(self.model_dir, "xgboost_model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(self.xgb_model, f)
        logger.info(f"XGBoost model saved to {model_path}")

        self.feature_names = X_train.columns.tolist()
        return results

    def get_feature_importance(self, model_type: str = "lightgbm", top_n: int = 20) -> pd.DataFrame:
        """Get feature importance from trained model."""
        if model_type == "lightgbm" and self.lgb_model:
            importances = self.lgb_model.feature_importance()
            features = self.feature_names
        elif model_type == "xgboost" and self.xgb_model:
            importances = self.xgb_model.get_score(importance_type="weight")
            features = list(importances.keys())
            importances = list(importances.values())
        else:
            return None

        df = pd.DataFrame(
            {"feature": features, "importance": importances}
        ).sort_values("importance", ascending=False)

        return df.head(top_n)

    def load_lightgbm_model(self):
        """Load LightGBM model from disk."""
        model_path = os.path.join(self.model_dir, "lightgbm_model.pkl")
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.lgb_model = pickle.load(f)
            logger.info(f"Loaded LightGBM model from {model_path}")
        else:
            logger.error(f"Model not found at {model_path}")

    def load_xgboost_model(self):
        """Load XGBoost model from disk."""
        model_path = os.path.join(self.model_dir, "xgboost_model.pkl")
        if os.path.exists(model_path):
            with open(model_path, "rb") as f:
                self.xgb_model = pickle.load(f)
            logger.info(f"Loaded XGBoost model from {model_path}")
        else:
            logger.error(f"Model not found at {model_path}")

    def predict(
        self, X: pd.DataFrame, model_type: str = "lightgbm"
    ) -> np.ndarray:
        """Generate predictions on new data."""
        if model_type == "lightgbm" and self.lgb_model:
            return self.lgb_model.predict(X)
        elif model_type == "xgboost" and self.xgb_model:
            dmatrix = xgb.DMatrix(X, feature_names=self.feature_names)
            return self.xgb_model.predict(dmatrix)
        else:
            logger.error(f"Model {model_type} not loaded")
            return None
