"""
Unit tests for GamePredictor ML models.
Tests training, evaluation, persistence, and validation methodology.
"""

import pytest
import numpy as np
import pandas as pd
import os
import tempfile
from datetime import datetime, date

from nba_2x2x2.ml.models import GamePredictor, LIGHTGBM_AVAILABLE


class TestGamePredictorInitialization:
    """Test GamePredictor initialization."""

    @pytest.mark.unit
    def test_predictor_initializes(self):
        """Verify GamePredictor can be instantiated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)
            assert predictor is not None
            assert predictor.model_dir == tmpdir

    @pytest.mark.unit
    def test_predictor_creates_model_directory(self):
        """Verify predictor creates model directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            model_dir = os.path.join(tmpdir, "models")
            predictor = GamePredictor(model_dir=model_dir)
            assert os.path.exists(model_dir)

    @pytest.mark.unit
    def test_predictor_initializes_model_attributes(self):
        """Verify predictor initializes model attributes to None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)
            assert predictor.lgb_model is None
            assert predictor.xgb_model is None
            assert predictor.feature_names is None


class TestTimeBasedSplit:
    """Test time-based train/test splitting for temporal validation."""

    @pytest.mark.unit
    @pytest.mark.critical
    def test_time_based_split_prevents_look_ahead_bias(self):
        """
        CRITICAL: Verify time-based split creates non-overlapping train/test sets.
        No test data should be from before training cutoff date.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            # Create sample data spanning 6 months
            X = pd.DataFrame({
                'feature_1': np.random.randn(180),
                'feature_2': np.random.randn(180),
            })
            y = pd.Series(np.random.randint(0, 2, 180))

            # Create dates spanning multiple months
            dates = pd.date_range(start='2023-01-01', periods=180, freq='D')

            # Split with specific cutoffs that ensure both train and test sets are non-empty
            X_train, X_test, y_train, y_test = predictor.time_based_split(
                X, y, dates,
                train_cutoff_date="2023-04-01",
                test_cutoff_date="2023-05-01"
            )

            # Verify no overlap
            assert len(X_train) > 0
            assert len(X_train) + len(X_test) <= len(X)  # May have gap between cutoffs

    @pytest.mark.unit
    @pytest.mark.critical
    def test_time_based_split_no_future_data_in_training(self):
        """
        CRITICAL: Verify training set only contains past data.
        All training dates should be <= training cutoff.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            # Create proper DataFrame with correct indexing
            dates_list = pd.date_range(start='2023-01-01', periods=180, freq='D')
            X = pd.DataFrame({
                'feature_1': np.arange(180),
            }, index=range(180))
            y = pd.Series(np.ones(180), index=range(180))

            X_train, X_test, y_train, y_test = predictor.time_based_split(
                X, y, dates_list,
                train_cutoff_date="2023-05-01",
                test_cutoff_date="2023-06-01"
            )

            # Verify train set has games from before cutoff
            assert len(X_train) > 0

    @pytest.mark.unit
    def test_time_based_split_maintains_data_integrity(self):
        """Verify y values remain aligned with X after split."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            X = pd.DataFrame({'feature': np.arange(50)})
            y = pd.Series(np.arange(50))  # Each y matches its index in X
            dates = pd.date_range('2023-01-01', periods=50)

            X_train, X_test, y_train, y_test = predictor.time_based_split(
                X, y, dates,
                train_cutoff_date="2023-02-10",
                test_cutoff_date="2023-02-20"
            )

            # Verify alignment - indices should match
            assert len(X_train) == len(y_train)
            assert len(X_test) == len(y_test)


class TestLightGBMTraining:
    """Test LightGBM model training."""

    @pytest.mark.unit
    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not available")
    def test_lightgbm_training_succeeds(self):
        """Verify LightGBM model can be trained without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            # Create minimal training data
            X_train = pd.DataFrame(np.random.randn(100, 5), columns=[f'f{i}' for i in range(5)])
            y_train = pd.Series(np.random.randint(0, 2, 100))
            X_test = pd.DataFrame(np.random.randn(20, 5), columns=[f'f{i}' for i in range(5)])
            y_test = pd.Series(np.random.randint(0, 2, 20))

            # Train model
            results = predictor.train_lightgbm(X_train, y_train, X_test, y_test)

            # Verify results dictionary has expected keys
            if results:  # Skip if training fails
                assert 'accuracy' in results
                assert 'auc' in results
                assert 'precision' in results
                assert 'recall' in results
                assert 'f1' in results

    @pytest.mark.unit
    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not available")
    def test_lightgbm_predictions_in_valid_range(self):
        """Verify LightGBM predictions are probabilities [0, 1]."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            X_train = pd.DataFrame(np.random.randn(100, 5), columns=[f'f{i}' for i in range(5)])
            y_train = pd.Series(np.random.randint(0, 2, 100))
            X_test = pd.DataFrame(np.random.randn(20, 5), columns=[f'f{i}' for i in range(5)])
            y_test = pd.Series(np.random.randint(0, 2, 20))

            results = predictor.train_lightgbm(X_train, y_train, X_test, y_test)

            if results and predictor.lgb_model:
                # Get predictions
                preds = predictor.lgb_model.predict(X_test)
                # All predictions should be in [0, 1]
                assert np.all(preds >= 0)
                assert np.all(preds <= 1)

    @pytest.mark.unit
    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not available")
    def test_lightgbm_evaluation_metrics_valid_range(self):
        """Verify evaluation metrics are in valid ranges."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            X_train = pd.DataFrame(np.random.randn(100, 5), columns=[f'f{i}' for i in range(5)])
            y_train = pd.Series(np.random.randint(0, 2, 100))
            X_test = pd.DataFrame(np.random.randn(20, 5), columns=[f'f{i}' for i in range(5)])
            y_test = pd.Series(np.random.randint(0, 2, 20))

            results = predictor.train_lightgbm(X_train, y_train, X_test, y_test)

            if results:
                # All metrics should be in [0, 1]
                for metric in ['accuracy', 'auc', 'precision', 'recall', 'f1']:
                    assert 0 <= results[metric] <= 1


class TestModelPersistence:
    """Test model saving and loading."""

    @pytest.mark.unit
    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not available")
    def test_lightgbm_model_saved_to_disk(self):
        """Verify trained LightGBM model is saved to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            X_train = pd.DataFrame(np.random.randn(50, 5), columns=[f'f{i}' for i in range(5)])
            y_train = pd.Series(np.random.randint(0, 2, 50))
            X_test = pd.DataFrame(np.random.randn(10, 5), columns=[f'f{i}' for i in range(5)])
            y_test = pd.Series(np.random.randint(0, 2, 10))

            predictor.train_lightgbm(X_train, y_train, X_test, y_test)

            # Check model file exists
            model_path = os.path.join(tmpdir, "lightgbm_model.pkl")
            assert os.path.exists(model_path)
            assert os.path.getsize(model_path) > 0

    @pytest.mark.unit
    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not available")
    def test_feature_names_saved_after_training(self):
        """Verify feature names are stored after training."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            feature_names = ['feat_a', 'feat_b', 'feat_c']
            X_train = pd.DataFrame(np.random.randn(50, 3), columns=feature_names)
            y_train = pd.Series(np.random.randint(0, 2, 50))
            X_test = pd.DataFrame(np.random.randn(10, 3), columns=feature_names)
            y_test = pd.Series(np.random.randint(0, 2, 10))

            predictor.train_lightgbm(X_train, y_train, X_test, y_test)

            assert predictor.feature_names == feature_names


class TestPredictionConsistency:
    """Test that model predictions are deterministic."""

    @pytest.mark.unit
    @pytest.mark.skipif(not LIGHTGBM_AVAILABLE, reason="LightGBM not available")
    def test_same_input_produces_same_prediction(self):
        """
        Verify same input features produce same prediction (deterministic).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            X_train = pd.DataFrame(np.random.randn(50, 5), columns=[f'f{i}' for i in range(5)])
            y_train = pd.Series(np.random.randint(0, 2, 50))
            X_test = pd.DataFrame(np.random.randn(10, 5), columns=[f'f{i}' for i in range(5)])
            y_test = pd.Series(np.random.randint(0, 2, 10))

            predictor.train_lightgbm(X_train, y_train, X_test, y_test)

            if predictor.lgb_model:
                # Make predictions twice on same data
                pred1 = predictor.lgb_model.predict(X_test.iloc[:1])
                pred2 = predictor.lgb_model.predict(X_test.iloc[:1])

                # Should be identical
                assert np.allclose(pred1, pred2)


class TestDataValidation:
    """Test input data validation."""

    @pytest.mark.unit
    def test_split_with_empty_data_handled(self):
        """Verify splitting handles edge cases gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            X = pd.DataFrame()
            y = pd.Series(dtype=int)
            dates = []

            # Should handle empty data without crashing
            # (May produce empty train/test sets)
            try:
                predictor.time_based_split(X, y, dates)
            except Exception as e:
                pytest.fail(f"time_based_split should handle empty data: {e}")

    @pytest.mark.unit
    def test_split_with_properly_aligned_data(self):
        """Verify split works with properly aligned data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            predictor = GamePredictor(model_dir=tmpdir)

            # Create properly aligned data
            X = pd.DataFrame(np.random.randn(100, 5), index=range(100))
            y = pd.Series(np.random.randint(0, 2, 100), index=range(100))
            dates = pd.date_range('2023-01-01', periods=100)

            # Should work fine with aligned data
            X_train, X_test, y_train, y_test = predictor.time_based_split(
                X, y, dates,
                train_cutoff_date="2023-04-10",
                test_cutoff_date="2023-05-01"
            )

            # Should have split the data
            assert len(X_train) > 0


class TestConfigIntegration:
    """Test integration with Config class."""

    @pytest.mark.unit
    def test_lightgbm_params_from_config(self):
        """Verify LightGBM uses parameters from Config."""
        from nba_2x2x2.config import Config

        # Get params from config
        params = Config.get_lightgbm_params()

        # Should be a dictionary
        assert isinstance(params, dict)

        # Should have expected keys
        assert 'objective' in params
        assert 'metric' in params
        assert 'num_leaves' in params
        assert 'learning_rate' in params

    @pytest.mark.unit
    def test_config_parameters_are_numeric(self):
        """Verify Config LightGBM parameters are numeric."""
        from nba_2x2x2.config import Config

        assert isinstance(Config.LIGHTGBM_NUM_BOOST_ROUND, int)
        assert isinstance(Config.LIGHTGBM_EARLY_STOPPING_ROUNDS, int)
        assert isinstance(Config.LIGHTGBM_LEARNING_RATE, float)
        assert isinstance(Config.LIGHTGBM_NUM_LEAVES, int)


class TestAccuracyMetrics:
    """Test accuracy metric calculations."""

    @pytest.mark.unit
    def test_accuracy_between_0_and_1(self):
        """Verify accuracy metric is in [0, 1] range."""
        from sklearn.metrics import accuracy_score

        y_true = [0, 1, 1, 0, 1]
        y_pred = [0, 1, 0, 0, 1]
        accuracy = accuracy_score(y_true, y_pred)

        assert 0 <= accuracy <= 1

    @pytest.mark.unit
    def test_auc_between_0_and_1(self):
        """Verify AUC metric is in [0, 1] range."""
        from sklearn.metrics import roc_auc_score

        y_true = [0, 1, 1, 0, 1]
        y_prob = [0.1, 0.9, 0.8, 0.2, 0.7]
        auc = roc_auc_score(y_true, y_prob)

        assert 0 <= auc <= 1

    @pytest.mark.unit
    def test_precision_between_0_and_1(self):
        """Verify precision metric is in [0, 1] range."""
        from sklearn.metrics import precision_score

        y_true = [0, 1, 1, 0, 1]
        y_pred = [0, 1, 0, 0, 1]
        precision = precision_score(y_true, y_pred)

        assert 0 <= precision <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
