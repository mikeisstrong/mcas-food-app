"""
Database connection and management for PostgreSQL.
Handles initialization, connection pooling, and ORM setup.
"""

from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from loguru import logger

from nba_2x2x2.config import Config


class DatabaseManager:
    """Manages PostgreSQL connections and database operations."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize database manager.

        Args:
            host: Database host (defaults to config)
            port: Database port (defaults to config)
            database: Database name (defaults to config)
            user: Database user (defaults to config)
            password: Database password (defaults to config)
        """
        self.host = host or Config.DB_HOST
        self.port = port or Config.DB_PORT
        self.database = database or Config.DB_NAME
        self.user = user or Config.DB_USER
        self.password = password or Config.DB_PASSWORD

        self.engine = None
        self.session_factory = None
        self._is_connected = False

    def connect(self) -> None:
        """Establish database connection and create engine."""
        try:
            connection_string = (
                f"postgresql+psycopg2://{self.user}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )

            connect_args = {
                "connect_timeout": Config.DB_CONNECT_TIMEOUT,
            }

            # Add SSL mode if not disabled
            if Config.DB_SSL_MODE != "disable":
                connect_args["sslmode"] = Config.DB_SSL_MODE

            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=Config.DB_POOL_SIZE,
                max_overflow=Config.DB_MAX_OVERFLOW,
                echo=False,
                connect_args=connect_args,
            )

            self.session_factory = sessionmaker(bind=self.engine)

            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            self._is_connected = True
            logger.info(
                f"Connected to PostgreSQL: {self.user}@{self.host}:{self.port}/{self.database}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            self._is_connected = False
            logger.info("Disconnected from PostgreSQL")

    def get_session(self) -> Session:
        """Get a new SQLAlchemy session."""
        if not self._is_connected or self.session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self.session_factory()

    def execute_query(self, query: str) -> list:
        """
        Execute a raw SQL query and return results.

        Args:
            query: SQL query string

        Returns:
            List of result rows
        """
        if not self._is_connected or self.engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        with self.engine.connect() as conn:
            result = conn.execute(text(query))
            return result.fetchall()

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._is_connected
