"""
Configuration management for NBA 2x2x2 Predictive Model.
Centralizes all environment-based configuration with validation.
"""

import os
from typing import List, Optional

try:
    from loguru import logger
except ImportError:
    # Fallback if loguru not available during import
    import logging
    logger = logging.getLogger(__name__)


class Config:
    """Centralized configuration management with validation."""

    # ===== DATABASE CONFIGURATION =====
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_NAME: str = os.getenv("DB_NAME", "nba_2x2x2")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_SSL_MODE: str = os.getenv("DB_SSL_MODE", "disable")
    DB_CONNECT_TIMEOUT: int = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

    # ===== EXTERNAL API CONFIGURATION =====
    BALLDONTLIE_API_KEY: str = os.getenv("BALLDONTLIE_API_KEY", "")
    API_RATE_LIMIT_DELAY: float = float(os.getenv("API_RATE_LIMIT_DELAY", "1.0"))

    # ===== LOGGING CONFIGURATION =====
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ===== API CONFIGURATION =====
    CORS_ORIGINS: List[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
    ]
    API_RATE_LIMIT_PER_MINUTE: int = int(os.getenv("API_RATE_LIMIT_PER_MINUTE", "60"))

    # ===== ML CONFIGURATION =====
    LIGHTGBM_NUM_LEAVES: int = int(os.getenv("LIGHTGBM_NUM_LEAVES", "31"))
    LIGHTGBM_LEARNING_RATE: float = float(os.getenv("LIGHTGBM_LEARNING_RATE", "0.05"))
    LIGHTGBM_MAX_DEPTH: int = int(os.getenv("LIGHTGBM_MAX_DEPTH", "10"))
    LIGHTGBM_MIN_DATA_IN_LEAF: int = int(os.getenv("LIGHTGBM_MIN_DATA_IN_LEAF", "20"))
    LIGHTGBM_FEATURE_FRACTION: float = float(os.getenv("LIGHTGBM_FEATURE_FRACTION", "0.8"))
    LIGHTGBM_BAGGING_FRACTION: float = float(os.getenv("LIGHTGBM_BAGGING_FRACTION", "0.8"))
    LIGHTGBM_BAGGING_FREQ: int = int(os.getenv("LIGHTGBM_BAGGING_FREQ", "5"))
    LIGHTGBM_NUM_BOOST_ROUND: int = int(os.getenv("LIGHTGBM_NUM_BOOST_ROUND", "500"))
    LIGHTGBM_EARLY_STOPPING_ROUNDS: int = int(os.getenv("LIGHTGBM_EARLY_STOPPING_ROUNDS", "50"))

    # ===== ELO CONFIGURATION =====
    ELO_K_FACTOR: float = float(os.getenv("ELO_K_FACTOR", "32"))
    ELO_INITIAL: float = float(os.getenv("ELO_INITIAL", "1500.0"))

    # ===== MODEL BLENDING CONFIGURATION =====
    LIGHTGBM_WEIGHT: float = float(os.getenv("LIGHTGBM_WEIGHT", "0.70"))
    ELO_WEIGHT: float = float(os.getenv("ELO_WEIGHT", "0.30"))

    @classmethod
    def validate(cls) -> bool:
        """
        Validate critical configuration settings.
        Returns True if valid, raises exception otherwise.
        """
        errors = []

        # Validate database settings
        if cls.DB_POOL_SIZE < 1:
            errors.append("DB_POOL_SIZE must be >= 1")
        if cls.DB_MAX_OVERFLOW < 0:
            errors.append("DB_MAX_OVERFLOW must be >= 0")

        # Validate API rate limiting
        if cls.API_RATE_LIMIT_DELAY <= 0:
            errors.append("API_RATE_LIMIT_DELAY must be > 0")
        if cls.API_RATE_LIMIT_PER_MINUTE < 1:
            errors.append("API_RATE_LIMIT_PER_MINUTE must be >= 1")

        # Validate ML configuration
        if cls.LIGHTGBM_LEARNING_RATE <= 0:
            errors.append("LIGHTGBM_LEARNING_RATE must be > 0")
        if cls.ELO_K_FACTOR <= 0:
            errors.append("ELO_K_FACTOR must be > 0")
        if cls.ELO_INITIAL <= 0:
            errors.append("ELO_INITIAL must be > 0")

        # Validate model blending weights sum to 1.0
        weights_sum = cls.LIGHTGBM_WEIGHT + cls.ELO_WEIGHT
        if abs(weights_sum - 1.0) > 0.001:  # Allow small floating point error
            errors.append(f"Model weights must sum to 1.0, got {weights_sum}")

        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of {valid_log_levels}")

        if errors:
            error_message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_message)
            raise ValueError(error_message)

        logger.info("Configuration validation passed")
        return True

    @classmethod
    def get_database_url(cls) -> str:
        """Generate SQLAlchemy database URL from configuration."""
        return (
            f"postgresql+psycopg2://{cls.DB_USER}:{cls.DB_PASSWORD}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    @classmethod
    def get_lightgbm_params(cls) -> dict:
        """Get LightGBM training parameters as dictionary."""
        return {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "num_leaves": cls.LIGHTGBM_NUM_LEAVES,
            "learning_rate": cls.LIGHTGBM_LEARNING_RATE,
            "max_depth": cls.LIGHTGBM_MAX_DEPTH,
            "min_data_in_leaf": cls.LIGHTGBM_MIN_DATA_IN_LEAF,
            "feature_fraction": cls.LIGHTGBM_FEATURE_FRACTION,
            "bagging_fraction": cls.LIGHTGBM_BAGGING_FRACTION,
            "bagging_freq": cls.LIGHTGBM_BAGGING_FREQ,
            "verbose": -1,
        }

    @classmethod
    def to_dict(cls) -> dict:
        """Export all configuration as dictionary (for debugging/logging)."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if not key.startswith("_") and key.isupper()
        }

    @classmethod
    def log_settings(cls) -> None:
        """Log all configuration settings (redacting passwords)."""
        settings = cls.to_dict()
        settings["DB_PASSWORD"] = "***REDACTED***"
        settings["BALLDONTLIE_API_KEY"] = "***REDACTED***"

        logger.info("Configuration loaded:")
        for key, value in sorted(settings.items()):
            logger.info(f"  {key}: {value}")

    @classmethod
    def get_rate_limit_string(cls, endpoint: str = "default") -> str:
        """
        Get rate limit string for slowapi decorator.

        Args:
            endpoint: Name of endpoint (default, games, metrics, projections)

        Returns:
            Rate limit string in format "X/minute"
        """
        limits = {
            "default": f"{cls.API_RATE_LIMIT_PER_MINUTE}/minute",
            "daily_report": f"{cls.API_RATE_LIMIT_PER_MINUTE}/minute",
            "games": f"{cls.API_RATE_LIMIT_PER_MINUTE}/minute",
            "metrics": f"{max(30, cls.API_RATE_LIMIT_PER_MINUTE // 2)}/minute",  # Heavier query
            "projections": f"{max(20, cls.API_RATE_LIMIT_PER_MINUTE // 3)}/minute",  # Heavier query
        }
        return limits.get(endpoint, limits["default"])


# Configuration validation is optional - call Config.validate() explicitly if needed
# This avoids startup errors if environment variables are not set
# Example: Config.validate()  # Call in main application startup
