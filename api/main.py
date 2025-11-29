"""
FastAPI backend for NBA prediction dashboard.
Serves data to React frontend.
"""

from fastapi import FastAPI, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, date
from typing import List, Optional
import sys
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import Game, GamePrediction, Team, TeamGameStats
from nba_2x2x2.config import Config
from nba_2x2x2.ml.monte_carlo import run_monte_carlo_simulation
from sqlalchemy import func

# Import rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

app = FastAPI(
    title="NBA Prediction API",
    version="1.0.0",
    description="Predicts NBA game outcomes using a blended ensemble of LightGBM (70%) and ELO rating system (30%). Provides daily reports, game history, and season projections.",
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
)

# Configure rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    """Handle rate limit exceeded with proper JSON response."""
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )

# Configure CORS with restricted methods and headers for production security
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
cors_origins = [origin.strip() for origin in cors_origins]  # Remove whitespace

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,  # Only needed if using auth cookies
    allow_methods=["GET"],  # Only allow GET for read-only endpoints
    allow_headers=["Content-Type", "Accept"],  # Whitelist specific headers
)

# Initialize database
db_manager = DatabaseManager()
db_manager.connect()


@app.on_event("shutdown")
def shutdown():
    """Close database connection on shutdown."""
    db_manager.disconnect()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _load_teams_by_id(session, team_ids: List[int]) -> dict:
    """
    Batch load teams to avoid N+1 queries.
    Returns dictionary mapping team_id to Team object.
    """
    if not team_ids:
        return {}
    teams = session.query(Team).filter(Team.id.in_(team_ids)).all()
    return {team.id: team for team in teams}


# ============================================================================
# DAILY DASHBOARD ENDPOINTS
# ============================================================================

@app.get(
    "/api/report/daily",
    tags=["Dashboard"],
    summary="Daily Report",
    response_description="Complete daily analysis with previous day results, today's schedule, and metrics"
)
@limiter.limit(Config.get_rate_limit_string("daily_report"))
def get_daily_report(request: Request, query_date: Optional[str] = None):
    """
    Get comprehensive daily report combining yesterday's results with today's schedule.

    Includes:
    - Yesterday's game predictions vs. actual outcomes
    - Accuracy metrics broken down by confidence level (High/Medium/Low)
    - Today's scheduled games with predictions
    - Summary statistics (overall accuracy, point spread error)

    Args:
        query_date: Date in YYYY-MM-DD format. Defaults to today.
            Example: "2025-11-22"

    Returns:
        Daily report containing:
        - query_date: The date being reported on
        - yesterday: Previous day's games with predictions and results
        - today: Today's scheduled games with predictions
        - summary_metrics: Overall accuracy and error statistics
        - timestamp: ISO 8601 timestamp of report generation

    Returns:
        {
            "query_date": "2025-11-22",
            "yesterday": {
                "date": "2025-11-21",
                "games": [
                    {
                        "game_id": 123,
                        "home_team": "Boston Celtics",
                        "away_team": "Brooklyn Nets",
                        "home_team_abbr": "BOS",
                        "away_team_abbr": "BRK",
                        "home_score": 105,
                        "away_score": 113,
                        "pred_home_win_pct": 0.82,
                        "pred_spread": -8.0,
                        "actual_spread": 8.0,
                        "correct": false,
                        "error": 16.0,
                        "confidence_bucket": "High"
                    },
                    ...
                ],
                "accuracy": 0.556,
                "accuracy_by_confidence": {
                    "High": {"correct": 3, "total": 4, "pct": 0.75},
                    "Medium": {"correct": 2, "total": 3, "pct": 0.667},
                    "Low": {"correct": 0, "total": 2, "pct": 0.0}
                }
            },
            "today": {
                "date": "2025-11-22",
                "games": [
                    {
                        "game_id": 124,
                        "time": "19:30",
                        "home_team": "Charlotte Hornets",
                        "away_team": "LA Clippers",
                        "home_team_abbr": "CHA",
                        "away_team_abbr": "LAC",
                        "pred_home_win_pct": 0.413,
                        "pred_spread": -4.33,
                        "favorite": "LAC",
                        "confidence_bucket": "Low"
                    },
                    ...
                ]
            },
            "summary_metrics": {
                "yesterday_accuracy": 0.556,
                "avg_error": 19.65,
                "high_confidence_accuracy": 0.75
            },
            "timestamp": "2025-11-22T10:20:00Z"
        }
    """
    session = db_manager.get_session()

    try:
        # Parse query date with proper validation
        if query_date:
            try:
                target_date = datetime.strptime(query_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-22)"
                )
        else:
            target_date = datetime.now().date()

        yesterday_date = target_date - timedelta(days=1)
        today_date = target_date

        # === YESTERDAY'S GAMES ===
        yesterday_games_query = session.query(
            Game.id,
            Game.game_date,
            Game.home_team_id,
            Game.away_team_id,
            Game.home_team_score,
            Game.away_team_score,
            GamePrediction.home_win_prob,
            GamePrediction.point_differential,
            Team.id.label("home_team_id_"),
            Team.full_name.label("home_team_name"),
            Team.abbreviation.label("home_team_abbr"),
            TeamGameStats.points_for.label("home_ppf"),
            TeamGameStats.points_against.label("home_ppa"),
            TeamGameStats.point_differential.label("home_point_diff"),
            TeamGameStats.elo_rating.label("home_elo"),
            TeamGameStats.days_rest.label("home_days_rest"),
            TeamGameStats.back_to_back.label("home_back_to_back"),
        ).join(GamePrediction).join(
            Team, Team.id == Game.home_team_id
        ).outerjoin(
            TeamGameStats, (TeamGameStats.game_id == Game.id) & (TeamGameStats.team_id == Game.home_team_id) & (TeamGameStats.is_home == 1)
        ).filter(
            Game.game_date >= yesterday_date,
            Game.game_date < yesterday_date + timedelta(days=1),
            Game.home_team_score.isnot(None),  # Only completed games
        ).all()

        # Batch load all away teams to avoid N+1 queries
        away_team_ids = [game.away_team_id for game in yesterday_games_query]
        away_teams_map = _load_teams_by_id(session, away_team_ids)

        # Batch load away team stats
        game_ids = [game.id for game in yesterday_games_query]
        away_team_stats_query = session.query(TeamGameStats).filter(
            TeamGameStats.game_id.in_(game_ids),
            TeamGameStats.is_home == 0
        ).all()
        away_stats_map = {stats.game_id: stats for stats in away_team_stats_query}

        yesterday_games = []
        yesterday_correct = 0
        yesterday_total = 0
        accuracy_by_confidence = {"High": {"correct": 0, "total": 0},
                                   "Medium": {"correct": 0, "total": 0},
                                   "Low": {"correct": 0, "total": 0}}

        for game in yesterday_games_query:
            # Use pre-loaded away team from cache (no query)
            away_team = away_teams_map.get(game.away_team_id)
            away_name = away_team.full_name if away_team else f"Team {game.away_team_id}"
            away_abbr = away_team.abbreviation if away_team else str(game.away_team_id)

            # Calculate correctness
            actual_spread = game.home_team_score - game.away_team_score
            pred_correct = (game.home_win_prob >= 0.5 and game.home_team_score > game.away_team_score) or \
                          (game.home_win_prob < 0.5 and game.home_team_score < game.away_team_score)
            error = abs(game.point_differential - actual_spread)

            # Determine confidence bucket
            if game.home_win_prob >= 0.65:
                confidence_bucket = "High"
            elif game.home_win_prob >= 0.55:
                confidence_bucket = "Medium"
            else:
                confidence_bucket = "Low"

            # Track accuracy by confidence
            accuracy_by_confidence[confidence_bucket]["total"] += 1
            if pred_correct:
                accuracy_by_confidence[confidence_bucket]["correct"] += 1

            yesterday_total += 1
            if pred_correct:
                yesterday_correct += 1

            # Build home and away team stats objects
            home_stats = None
            if game.home_ppf is not None:
                home_stats = {
                    "points_for": float(game.home_ppf),
                    "points_against": float(game.home_ppa),
                    "point_differential": float(game.home_point_diff),
                    "elo_rating": float(game.home_elo),
                    "days_rest": int(game.home_days_rest) if game.home_days_rest is not None else 0,
                    "back_to_back": bool(game.home_back_to_back) if game.home_back_to_back is not None else False,
                }

            away_stats = None
            if game.id in away_stats_map:
                stats = away_stats_map[game.id]
                away_stats = {
                    "points_for": float(stats.points_for) if stats.points_for is not None else None,
                    "points_against": float(stats.points_against) if stats.points_against is not None else None,
                    "point_differential": float(stats.point_differential) if stats.point_differential is not None else None,
                    "elo_rating": float(stats.elo_rating) if stats.elo_rating is not None else None,
                    "days_rest": int(stats.days_rest) if stats.days_rest is not None else 0,
                    "back_to_back": bool(stats.back_to_back) if stats.back_to_back is not None else False,
                }

            yesterday_games.append({
                "game_id": game.id,
                "home_team": game.home_team_name,
                "away_team": away_name,
                "home_team_abbr": game.home_team_abbr,
                "away_team_abbr": away_abbr,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "home_score": int(game.home_team_score),
                "away_score": int(game.away_team_score),
                "pred_home_win_pct": round(float(game.home_win_prob), 3),
                "pred_spread": round(float(game.point_differential), 2),
                "actual_spread": round(float(actual_spread), 1),
                "correct": pred_correct,
                "error": round(float(error), 2),
                "confidence_bucket": confidence_bucket,
                "home_team_stats": home_stats,
                "away_team_stats": away_stats,
            })

        # Calculate accuracy percentages
        for bucket in accuracy_by_confidence:
            if accuracy_by_confidence[bucket]["total"] > 0:
                accuracy_by_confidence[bucket]["pct"] = round(
                    accuracy_by_confidence[bucket]["correct"] / accuracy_by_confidence[bucket]["total"],
                    3
                )
            else:
                accuracy_by_confidence[bucket]["pct"] = 0

        yesterday_accuracy = round(yesterday_correct / yesterday_total, 3) if yesterday_total > 0 else 0

        # === TODAY'S GAMES ===
        today_games_query = session.query(
            Game.id,
            Game.game_date,
            Game.home_team_id,
            Game.away_team_id,
            GamePrediction.home_win_prob,
            GamePrediction.point_differential,
            Team.id.label("home_team_id_"),
            Team.full_name.label("home_team_name"),
            Team.abbreviation.label("home_team_abbr"),
            TeamGameStats.points_for.label("home_ppf"),
            TeamGameStats.points_against.label("home_ppa"),
            TeamGameStats.point_differential.label("home_point_diff"),
            TeamGameStats.elo_rating.label("home_elo"),
            TeamGameStats.days_rest.label("home_days_rest"),
            TeamGameStats.back_to_back.label("home_back_to_back"),
        ).join(Team, Team.id == Game.home_team_id).outerjoin(
            GamePrediction
        ).outerjoin(
            TeamGameStats, (TeamGameStats.game_id == Game.id) & (TeamGameStats.team_id == Game.home_team_id) & (TeamGameStats.is_home == 1)
        ).filter(
            Game.game_date >= today_date,
            Game.game_date < today_date + timedelta(days=1),
            Game.home_team_score.is_(None),  # Only unplayed/upcoming games
        ).order_by(Game.game_date).all()

        # Batch load all away teams to avoid N+1 queries
        today_away_team_ids = [game.away_team_id for game in today_games_query]
        today_away_teams_map = _load_teams_by_id(session, today_away_team_ids)

        # Batch load MOST RECENT away team stats (for unplayed games, use latest stats)
        today_away_team_ids = [game.away_team_id for game in today_games_query]
        today_home_team_ids = [game.home_team_id for game in today_games_query]
        all_team_ids = list(set(today_away_team_ids + today_home_team_ids))

        # Get the most recent stats for each team (regardless of home/away)
        # For upcoming games, we use the team's most recent stats regardless of location
        recent_away_stats_query = session.query(TeamGameStats).filter(
            TeamGameStats.team_id.in_(today_away_team_ids)
        ).order_by(
            TeamGameStats.team_id,
            TeamGameStats.id.desc()
        ).all()
        # Group by team_id, keeping only the most recent one
        today_away_stats_map_by_team = {}
        for stats in recent_away_stats_query:
            if stats.team_id not in today_away_stats_map_by_team:
                today_away_stats_map_by_team[stats.team_id] = stats

        recent_home_stats_query = session.query(TeamGameStats).filter(
            TeamGameStats.team_id.in_(today_home_team_ids)
        ).order_by(
            TeamGameStats.team_id,
            TeamGameStats.id.desc()
        ).all()
        # Group by team_id, keeping only the most recent one
        today_home_stats_map_by_team = {}
        for stats in recent_home_stats_query:
            if stats.team_id not in today_home_stats_map_by_team:
                today_home_stats_map_by_team[stats.team_id] = stats

        today_games = []
        for game in today_games_query:
            # Use pre-loaded away team from cache (no query)
            away_team = today_away_teams_map.get(game.away_team_id)
            away_name = away_team.full_name if away_team else f"Team {game.away_team_id}"
            away_abbr = away_team.abbreviation if away_team else str(game.away_team_id)

            time_str = game.game_date.strftime("%H:%M") if game.game_date else "TBD"

            # Build home and away team stats objects using most recent stats
            home_stats = None
            if game.home_team_id in today_home_stats_map_by_team:
                stats = today_home_stats_map_by_team[game.home_team_id]
                home_stats = {
                    "points_for": float(stats.points_for) if stats.points_for is not None else None,
                    "points_against": float(stats.points_against) if stats.points_against is not None else None,
                    "point_differential": float(stats.point_differential) if stats.point_differential is not None else None,
                    "elo_rating": float(stats.elo_rating) if stats.elo_rating is not None else None,
                    "days_rest": int(stats.days_rest) if stats.days_rest is not None else 0,
                    "back_to_back": bool(stats.back_to_back) if stats.back_to_back is not None else False,
                }

            away_stats = None
            if game.away_team_id in today_away_stats_map_by_team:
                stats = today_away_stats_map_by_team[game.away_team_id]
                away_stats = {
                    "points_for": float(stats.points_for) if stats.points_for is not None else None,
                    "points_against": float(stats.points_against) if stats.points_against is not None else None,
                    "point_differential": float(stats.point_differential) if stats.point_differential is not None else None,
                    "elo_rating": float(stats.elo_rating) if stats.elo_rating is not None else None,
                    "days_rest": int(stats.days_rest) if stats.days_rest is not None else 0,
                    "back_to_back": bool(stats.back_to_back) if stats.back_to_back is not None else False,
                }

            # Determine confidence bucket and favorite
            if game.home_win_prob is not None:
                home_prob = float(game.home_win_prob)
                if home_prob >= 0.65:
                    confidence_bucket = "High"
                elif home_prob >= 0.55:
                    confidence_bucket = "Medium"
                else:
                    confidence_bucket = "Low"

                favorite = "Home" if home_prob >= 0.5 else "Away"
                pred_spread = float(game.point_differential)
                pred_home_win_pct = round(home_prob, 3)
            else:
                confidence_bucket = "Unknown"
                favorite = "Unknown"
                pred_spread = None
                pred_home_win_pct = None

            today_games.append({
                "game_id": game.id,
                "time": time_str,
                "home_team": game.home_team_name,
                "away_team": away_name,
                "home_team_abbr": game.home_team_abbr,
                "away_team_abbr": away_abbr,
                "home_team_id": game.home_team_id,
                "away_team_id": game.away_team_id,
                "pred_home_win_pct": pred_home_win_pct,
                "pred_spread": round(pred_spread, 2) if pred_spread is not None else None,
                "favorite": favorite,
                "confidence_bucket": confidence_bucket,
                "home_team_stats": home_stats,
                "away_team_stats": away_stats,
            })

        # === SUMMARY METRICS ===
        # Calculate avg error from yesterday's games only
        total_errors = []
        for game in yesterday_games_query:
            actual_diff = game.home_team_score - game.away_team_score
            error = abs(game.point_differential - actual_diff)
            total_errors.append(error)

        avg_error = round(sum(total_errors) / len(total_errors), 2) if total_errors else 0

        return {
            "query_date": str(target_date),
            "yesterday": {
                "date": str(yesterday_date),
                "games": yesterday_games,
                "accuracy": yesterday_accuracy,
                "accuracy_by_confidence": accuracy_by_confidence,
            },
            "today": {
                "date": str(today_date),
                "games": today_games,
            },
            "summary_metrics": {
                "yesterday_accuracy": yesterday_accuracy,
                "avg_error": avg_error,
                "high_confidence_accuracy": accuracy_by_confidence.get("High", {}).get("pct", 0),
            },
            "timestamp": datetime.now().isoformat() + "Z",
        }

    finally:
        session.close()


# ============================================================================
# HISTORY & ACCURACY ENDPOINTS
# ============================================================================

@app.get(
    "/api/games",
    tags=["History"],
    summary="Game History",
    response_description="Paginated list of games with predictions and actual results"
)
@limiter.limit(Config.get_rate_limit_string("games"))
def get_games(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    team: Optional[str] = None,
    confidence: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """
    Get paginated games history with predictions and actual outcomes.

    Supports filtering by date range, team, and prediction confidence level.
    Results are ordered by most recent first.

    Args:
        start_date: Filter by start date (YYYY-MM-DD). Example: "2025-01-01"
        end_date: Filter by end date (YYYY-MM-DD). Example: "2025-11-22"
        team: Filter by team name or abbreviation (optional). Example: "BOS"
        confidence: Filter by prediction confidence ("High", "Medium", "Low")
        skip: Pagination offset (default 0)
        limit: Results per page, max 100 (default 50)

    Returns:
        Paginated list with:
        - games: Array of game predictions and results
        - total: Total matching games
        - skip: Current offset
        - limit: Results per page
        - returned: Number of games in this response
    """
    session = db_manager.get_session()

    try:
        query = session.query(
            Game.id,
            Game.game_date,
            Game.season,
            Game.home_team_id,
            Game.away_team_id,
            Game.home_team_score,
            Game.away_team_score,
            GamePrediction.home_win_prob,
            GamePrediction.point_differential,
        ).join(GamePrediction, isouter=True)

        # Date filters with validation
        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(Game.game_date >= start)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format. Use YYYY-MM-DD (e.g., 2025-11-22)"
                )

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(Game.game_date <= end)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format. Use YYYY-MM-DD (e.g., 2025-11-22)"
                )

        # Get total count before pagination
        total = query.count()

        # Pagination
        limit = min(limit, 100)  # Max 100 per page
        games = query.order_by(Game.game_date.desc()).offset(skip).limit(limit).all()

        # Batch load all teams to avoid N+1 queries
        team_ids = set()
        for game in games:
            team_ids.add(game.home_team_id)
            team_ids.add(game.away_team_id)
        teams_map = _load_teams_by_id(session, list(team_ids))

        results = []
        for game in games:
            home_team = teams_map.get(game.home_team_id)
            away_team = teams_map.get(game.away_team_id)

            home_name = home_team.full_name if home_team else f"Team {game.home_team_id}"
            away_name = away_team.full_name if away_team else f"Team {game.away_team_id}"
            home_abbr = home_team.abbreviation if home_team else str(game.home_team_id)
            away_abbr = away_team.abbreviation if away_team else str(game.away_team_id)

            # Determine correctness and confidence
            if game.home_team_score is not None:
                actual_diff = game.home_team_score - game.away_team_score
                pred_correct = (game.home_win_prob >= 0.5 and game.home_team_score > game.away_team_score) or \
                              (game.home_win_prob < 0.5 and game.home_team_score < game.away_team_score)
                error = abs(game.point_differential - actual_diff)

                if game.home_win_prob >= 0.65:
                    confidence_bucket = "High"
                elif game.home_win_prob >= 0.55:
                    confidence_bucket = "Medium"
                else:
                    confidence_bucket = "Low"
            else:
                error = None
                pred_correct = None
                confidence_bucket = "Unknown"

            # Filter by confidence if requested
            if confidence and confidence_bucket != confidence:
                continue

            results.append({
                "game_id": game.id,
                "date": str(game.game_date),
                "season": game.season,
                "home_team": home_name,
                "away_team": away_name,
                "home_team_abbr": home_abbr,
                "away_team_abbr": away_abbr,
                "pred_home_win_pct": round(float(game.home_win_prob), 3) if game.home_win_prob else None,
                "pred_spread": round(float(game.point_differential), 2) if game.point_differential else None,
                "home_score": int(game.home_team_score) if game.home_team_score else None,
                "away_score": int(game.away_team_score) if game.away_team_score else None,
                "correct": pred_correct,
                "error": round(float(error), 2) if error else None,
                "confidence_bucket": confidence_bucket,
            })

        return {
            "games": results,
            "total": total,
            "skip": skip,
            "limit": limit,
            "returned": len(results),
        }

    finally:
        session.close()


@app.get(
    "/api/metrics/summary",
    tags=["Analytics"],
    summary="Aggregated Metrics",
    response_description="Calibration and accuracy metrics for a date range"
)
@limiter.limit(Config.get_rate_limit_string("metrics"))
def get_metrics_summary(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """
    Get aggregated prediction metrics for a date range.

    Provides overall accuracy, calibration analysis by confidence level,
    and point spread error distribution.

    Args:
        start_date: Filter by start date (YYYY-MM-DD). Example: "2025-01-01"
        end_date: Filter by end date (YYYY-MM-DD). Example: "2025-11-22"

    Returns:
        Metrics object containing:
        - overall_accuracy: Win prediction accuracy [0,1]
        - total_games: Number of completed games
        - by_confidence: Accuracy breakdown by confidence bucket
        - spread_error: Point differential prediction error statistics
    """
    session = db_manager.get_session()

    try:
        query = session.query(
            GamePrediction.home_win_prob,
            GamePrediction.point_differential,
            Game.home_team_score,
            Game.away_team_score,
        ).join(Game).filter(
            Game.home_team_score.isnot(None)
        )

        if start_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                query = query.filter(Game.game_date >= start)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid start_date format. Use YYYY-MM-DD (e.g., 2025-11-22)"
                )

        if end_date:
            try:
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                query = query.filter(Game.game_date <= end)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid end_date format. Use YYYY-MM-DD (e.g., 2025-11-22)"
                )

        games = query.all()

        if not games:
            return {
                "overall_accuracy": 0,
                "by_confidence": {},
                "spread_error": {},
            }

        # Calculate metrics
        overall_correct = 0
        errors = []
        by_confidence = {"High": {"correct": 0, "total": 0},
                        "Medium": {"correct": 0, "total": 0},
                        "Low": {"correct": 0, "total": 0}}

        for game in games:
            actual_diff = game.home_team_score - game.away_team_score
            pred_correct = (game.home_win_prob >= 0.5 and game.home_team_score > game.away_team_score) or \
                          (game.home_win_prob < 0.5 and game.home_team_score < game.away_team_score)

            if pred_correct:
                overall_correct += 1

            error = abs(game.point_differential - actual_diff)
            errors.append(error)

            # By confidence
            if game.home_win_prob >= 0.65:
                bucket = "High"
            elif game.home_win_prob >= 0.55:
                bucket = "Medium"
            else:
                bucket = "Low"

            by_confidence[bucket]["total"] += 1
            if pred_correct:
                by_confidence[bucket]["correct"] += 1

        # Calculate percentages
        for bucket in by_confidence:
            if by_confidence[bucket]["total"] > 0:
                by_confidence[bucket]["pct"] = round(
                    by_confidence[bucket]["correct"] / by_confidence[bucket]["total"], 3
                )

        overall_accuracy = round(overall_correct / len(games), 3)

        errors.sort()
        within_5 = sum(1 for e in errors if e <= 5)
        within_10 = sum(1 for e in errors if e <= 10)

        return {
            "overall_accuracy": overall_accuracy,
            "total_games": len(games),
            "by_confidence": by_confidence,
            "spread_error": {
                "mean_absolute_error": round(sum(errors) / len(errors), 2),
                "median_error": round(errors[len(errors) // 2], 2),
                "std_dev": round((sum((e - (sum(errors) / len(errors))) ** 2 for e in errors) / len(errors)) ** 0.5, 2),
                "within_5_points": round(within_5 / len(errors), 3),
                "within_10_points": round(within_10 / len(errors), 3),
            },
        }

    finally:
        session.close()


# ============================================================================
# SEASON PROJECTIONS ENDPOINTS
# ============================================================================

@app.get(
    "/api/projections/season",
    tags=["Projections"],
    summary="Season Projections",
    response_description="Projected final season record for all 30 NBA teams"
)
def get_season_projections():
    """
    Get season-end win projections for all 30 NBA teams.

    Combines actual game results to date with predictions for remaining games
    using the blended ensemble model (70% LightGBM + 30% ELO).

    Returns:
        Season projections sorted by projected wins (descending):
        - team_id: Internal team ID
        - team_name: Full team name (e.g., "Boston Celtics")
        - team_abbr: 3-letter abbreviation (e.g., "BOS")
        - current_wins: Games won to date
        - current_losses: Games lost to date
        - remaining_games: Games left to play
        - projected_remaining_wins: Expected wins in remaining games
        - projected_total_wins: Final projected wins (current + remaining)
        - projected_total_losses: Final projected losses
        - projected_win_pct: Final projected win percentage
    """
    session = db_manager.get_session()

    # Always use current season (2025 = 2025-26 season)
    season = 2025
    basis = "blend"

    try:
        # Get all teams
        teams = session.query(Team).order_by(Team.full_name).all()

        projections = []

        from datetime import datetime
        today = datetime.now().date()

        for team in teams:
            # Get current record (completed games only through today)
            played_games = session.query(
                Game.home_team_id,
                Game.away_team_id,
                Game.home_team_score,
                Game.away_team_score,
            ).filter(
                ((Game.home_team_id == team.id) | (Game.away_team_id == team.id)),
                Game.season == season,
                Game.game_date <= today,
                Game.home_team_score.isnot(None),
            ).all()

            wins = 0
            losses = 0
            for game in played_games:
                if game.home_team_id == team.id:
                    if game.home_team_score > game.away_team_score:
                        wins += 1
                    else:
                        losses += 1
                else:
                    if game.away_team_score > game.home_team_score:
                        wins += 1
                    else:
                        losses += 1

            # Get remaining games and their predictions (scheduled games only)
            remaining_games_query = session.query(
                GamePrediction.home_win_prob,
                GamePrediction.elo_home_prob,
                GamePrediction.lightgbm_home_prob,
                Game.home_team_id,
                Game.away_team_id,
            ).select_from(Game).outerjoin(GamePrediction).filter(
                ((Game.home_team_id == team.id) | (Game.away_team_id == team.id)),
                Game.season == season,
                Game.status == "scheduled",
            ).all()

            remaining_count = len(remaining_games_query)

            # Probability summation: sum win probabilities for each remaining game
            # Expected value of wins = sum of individual game win probabilities
            projected_remaining_wins = 0.0
            remaining_strength_sum = 0.0  # For SOS calculation

            # Prepare data for Monte Carlo simulation
            mc_games = []

            for game in remaining_games_query:
                # Skip if no prediction exists yet
                if game.home_win_prob is None:
                    continue

                if game.home_team_id == team.id:
                    # Team is home - use home win probability
                    prob = game.home_win_prob
                    # Opponent strength = away team's win prob (1 - home win prob)
                    opponent_win_prob = 1 - game.home_win_prob
                else:
                    # Team is away - use away win probability (1 - home win prob)
                    prob = 1 - game.home_win_prob
                    # Opponent strength = home team's win prob
                    opponent_win_prob = game.home_win_prob

                projected_remaining_wins += float(prob)
                # Track opponent strength (higher prob = stronger opponent)
                remaining_strength_sum += float(opponent_win_prob)

                # Add to Monte Carlo simulation games
                mc_games.append({
                    'home_team_id': game.home_team_id,
                    'away_team_id': game.away_team_id,
                    'home_win_prob': float(game.home_win_prob),
                    'elo_home_prob': float(game.elo_home_prob),
                })

            # Calculate average opponent strength for remaining schedule
            if remaining_count > 0:
                remaining_avg_opponent_strength = remaining_strength_sum / remaining_count
                # League average opponent strength should be ~0.5 (50% win prob)
                # If remaining_avg_opponent_strength > 0.5, they face stronger opponents
                # Adjustment: scale by ratio to league average
                schedule_adjustment = 0.5 / remaining_avg_opponent_strength if remaining_avg_opponent_strength > 0 else 1.0
                projected_remaining_wins *= schedule_adjustment
            else:
                schedule_adjustment = 1.0

            # Calculate projections using probability summation
            projected_wins = wins + projected_remaining_wins
            projected_losses = 82 - projected_wins  # Total season is 82 games
            projected_win_pct = round(projected_wins / 82, 3)

            # Run Monte Carlo simulation for confidence intervals
            mc_result = None
            if len(mc_games) > 0:
                mc_result = run_monte_carlo_simulation(
                    current_wins=wins,
                    current_losses=losses,
                    remaining_games=mc_games,
                    num_simulations=10000,
                    team_id=team.id,
                )

            # Build projection result
            projection = {
                "team_id": team.id,
                "team_name": team.full_name,
                "team_abbr": team.abbreviation,
                "current_wins": wins,
                "current_losses": losses,
                "remaining_games": remaining_count,
                "projected_remaining_wins": round(projected_remaining_wins, 1),
                "projected_total_wins": round(projected_wins),
                "projected_total_losses": round(projected_losses),
                "projected_win_pct": projected_win_pct,
                "schedule_adjustment": round(schedule_adjustment, 3),  # SOS transparency
                # Monte Carlo results for confidence intervals
                "monte_carlo": {
                    "mean_wins": round(mc_result.mean_wins) if mc_result else None,
                    "median_wins": mc_result.median_wins if mc_result else None,
                    "percentile_10": mc_result.percentile_10 if mc_result else None,
                    "percentile_90": mc_result.percentile_90 if mc_result else None,
                    "std_dev": round(mc_result.std_dev, 2) if mc_result else None,
                } if mc_result else None,
            }
            projections.append(projection)

        # Sort by projected wins descending
        projections.sort(key=lambda x: x["projected_total_wins"], reverse=True)

        return {
            "season": season,
            "season_display": "2025-26",
            "basis": basis,
            "projections": projections,
            "timestamp": datetime.now().isoformat() + "Z",
        }

    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
