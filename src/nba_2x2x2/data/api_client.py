"""
BALLDONTLIE NBA API client.
Handles fetching teams, games, and player stats from the public API.
"""

import os
import time
from typing import Optional, List, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from loguru import logger


class BallDontLieClient:
    """Client for fetching data from the BALLDONTLIE NBA API."""

    BASE_URL = "https://api.balldontlie.io/api/v1"

    def __init__(self, api_key: Optional[str] = None, rate_limit_delay: float = 0.1):
        """
        Initialize API client.

        Args:
            api_key: BALLDONTLIE API key (defaults to env var)
            rate_limit_delay: Delay in seconds between API requests
        """
        self.api_key = api_key or os.getenv("BALLDONTLIE_API_KEY", "")
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0

        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": self.api_key} if self.api_key else {}
        )

        # Configure retries for rate limiting
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def _rate_limit_wait(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def get_teams(self) -> List[Dict[str, Any]]:
        """
        Fetch all NBA teams.

        Returns:
            List of team dictionaries with id, abbreviation, city, conference, division, etc.
        """
        try:
            self._rate_limit_wait()
            response = self.session.get(f"{self.BASE_URL}/teams")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data.get('data', []))} teams")
            return data.get("data", [])
        except requests.RequestException as e:
            logger.error(f"Failed to fetch teams: {e}")
            raise

    def get_games(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        season: Optional[int] = None,
        per_page: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch NBA games with optional filtering.

        Args:
            start_date: ISO format start date (YYYY-MM-DD)
            end_date: ISO format end date (YYYY-MM-DD)
            season: NBA season year (e.g., 2023 for 2023-24 season)
            per_page: Results per page (max 100)

        Returns:
            List of game dictionaries
        """
        params = {"per_page": per_page}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if season:
            params["season"] = season

        all_games = []
        page = 0

        try:
            while True:
                params["page"] = page
                self._rate_limit_wait()
                response = self.session.get(f"{self.BASE_URL}/games", params=params)
                response.raise_for_status()
                data = response.json()

                games = data.get("data", [])
                if not games:
                    break

                all_games.extend(games)
                logger.info(
                    f"Fetched page {page + 1}: {len(games)} games (total: {len(all_games)})"
                )

                if data.get("meta", {}).get("current_page") >= data.get("meta", {}).get(
                    "total_pages", 1
                ):
                    break

                page += 1

            logger.info(f"Total games fetched: {len(all_games)}")
            return all_games

        except requests.RequestException as e:
            logger.error(f"Failed to fetch games: {e}")
            raise

    def get_game_by_id(self, game_id: int) -> Dict[str, Any]:
        """
        Fetch a single game by ID.

        Args:
            game_id: Game ID from BALLDONTLIE

        Returns:
            Game dictionary with full details
        """
        try:
            self._rate_limit_wait()
            response = self.session.get(f"{self.BASE_URL}/games/{game_id}")
            response.raise_for_status()
            return response.json().get("data", {})
        except requests.RequestException as e:
            logger.error(f"Failed to fetch game {game_id}: {e}")
            raise

    def get_season_games(self, season: int) -> List[Dict[str, Any]]:
        """
        Fetch all games from a specific season.

        Args:
            season: NBA season year (e.g., 2023 for 2023-24 season)

        Returns:
            List of all games in the season
        """
        logger.info(f"Fetching all games for season {season}")
        return self.get_games(season=season)

    def health_check(self) -> bool:
        """
        Check if API is accessible.

        Returns:
            True if API is reachable, False otherwise
        """
        try:
            self._rate_limit_wait()
            response = self.session.get(f"{self.BASE_URL}/teams")
            return response.status_code == 200
        except requests.RequestException:
            return False
