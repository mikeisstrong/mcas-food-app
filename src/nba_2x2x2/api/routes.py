"""
Flask routes for exposing NBA metrics and data.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from loguru import logger

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import TeamGameStats, Game, Team

# Create blueprint
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# Database manager (will be initialized in app.py)
db_manager = None


def init_db(app_db_manager):
    """Initialize database manager for routes."""
    global db_manager
    db_manager = app_db_manager


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "NBA Metrics API is running"})


@api_bp.route("/teams", methods=["GET"])
def get_teams():
    """Get all teams with basic info."""
    session = db_manager.get_session()
    try:
        teams = session.query(Team).all()
        return jsonify(
            [
                {
                    "id": t.id,
                    "abbreviation": t.abbreviation,
                    "full_name": t.full_name,
                    "city": t.city,
                    "division": t.division,
                    "conference": t.conference,
                }
                for t in teams
            ]
        )
    finally:
        session.close()


@api_bp.route("/team/<int:team_id>/stats", methods=["GET"])
def get_team_stats(team_id: int):
    """Get latest stats for a specific team."""
    session = db_manager.get_session()
    try:
        # Get latest stats for team
        latest_stats = (
            session.query(TeamGameStats)
            .filter(TeamGameStats.team_id == team_id)
            .order_by(desc(TeamGameStats.game_id))
            .first()
        )

        if not latest_stats:
            return jsonify({"error": "No stats found for team"}), 404

        team = session.query(Team).filter(Team.id == team_id).first()

        return jsonify(
            {
                "team_id": team_id,
                "team_name": team.full_name,
                "abbreviation": team.abbreviation,
                "games_played": latest_stats.games_played,
                "wins": latest_stats.wins,
                "losses": latest_stats.losses,
                "win_pct": round(latest_stats.win_pct, 3) if latest_stats.win_pct else 0,
                "points_for": round(latest_stats.points_for, 2)
                if latest_stats.points_for
                else 0,
                "points_against": round(latest_stats.points_against, 2)
                if latest_stats.points_against
                else 0,
                "point_differential": round(latest_stats.point_differential, 2)
                if latest_stats.point_differential
                else 0,
                "ppf_5game": round(latest_stats.ppf_5game, 2)
                if latest_stats.ppf_5game
                else None,
                "ppa_5game": round(latest_stats.ppa_5game, 2)
                if latest_stats.ppa_5game
                else None,
                "ppf_10game": round(latest_stats.ppf_10game, 2)
                if latest_stats.ppf_10game
                else None,
                "ppa_10game": round(latest_stats.ppa_10game, 2)
                if latest_stats.ppa_10game
                else None,
                "ppf_20game": round(latest_stats.ppf_20game, 2)
                if latest_stats.ppf_20game
                else None,
                "ppa_20game": round(latest_stats.ppa_20game, 2)
                if latest_stats.ppa_20game
                else None,
                "elo_rating": round(latest_stats.elo_rating, 1),
                "days_rest": latest_stats.days_rest,
                "back_to_back": latest_stats.back_to_back,
            }
        )
    finally:
        session.close()


@api_bp.route("/game/<int:game_id>/stats", methods=["GET"])
def get_game_stats(game_id: int):
    """Get stats for both teams in a game."""
    session = db_manager.get_session()
    try:
        game = session.query(Game).filter(Game.id == game_id).first()
        if not game:
            return jsonify({"error": "Game not found"}), 404

        home_stats = (
            session.query(TeamGameStats)
            .filter_by(game_id=game_id, is_home=1)
            .first()
        )
        away_stats = (
            session.query(TeamGameStats)
            .filter_by(game_id=game_id, is_home=0)
            .first()
        )

        def serialize_stats(stats, team):
            if not stats:
                return None
            return {
                "team_id": stats.team_id,
                "team_name": team.full_name,
                "abbreviation": team.abbreviation,
                "games_played": stats.games_played,
                "wins": stats.wins,
                "losses": stats.losses,
                "win_pct": round(stats.win_pct, 3) if stats.win_pct else 0,
                "elo_rating": round(stats.elo_rating, 1),
                "ppf_5game": round(stats.ppf_5game, 2) if stats.ppf_5game else None,
                "ppa_5game": round(stats.ppa_5game, 2) if stats.ppa_5game else None,
                "ppf_10game": round(stats.ppf_10game, 2) if stats.ppf_10game else None,
                "ppa_10game": round(stats.ppa_10game, 2) if stats.ppa_10game else None,
                "ppf_20game": round(stats.ppf_20game, 2) if stats.ppf_20game else None,
                "ppa_20game": round(stats.ppa_20game, 2) if stats.ppa_20game else None,
                "points_scored_in_game": stats.points_scored,
                "points_allowed_in_game": stats.points_allowed,
                "game_won": stats.game_won,
                "days_rest": stats.days_rest,
                "back_to_back": stats.back_to_back,
            }

        home_team = session.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = session.query(Team).filter(Team.id == game.away_team_id).first()

        return jsonify(
            {
                "game_id": game_id,
                "date": str(game.game_date),
                "home_team": serialize_stats(home_stats, home_team),
                "away_team": serialize_stats(away_stats, away_team),
                "home_score": game.home_team_score,
                "away_score": game.away_team_score,
                "status": game.status,
            }
        )
    finally:
        session.close()


@api_bp.route("/games", methods=["GET"])
def get_games():
    """Get games with optional filtering by date range and team."""
    session = db_manager.get_session()
    try:
        query = session.query(Game).filter(Game.status == "Final")

        # Filter by date range if provided
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if start_date:
            query = query.filter(Game.game_date >= start_date)
        if end_date:
            query = query.filter(Game.game_date <= end_date)

        # Limit results
        limit = min(int(request.args.get("limit", 50)), 500)
        games = query.order_by(desc(Game.game_date)).limit(limit).all()

        return jsonify(
            [
                {
                    "id": g.id,
                    "date": str(g.game_date),
                    "season": g.season,
                    "home_team": g.home_team.abbreviation,
                    "away_team": g.away_team.abbreviation,
                    "home_score": g.home_team_score,
                    "away_score": g.away_team_score,
                    "status": g.status,
                }
                for g in games
            ]
        )
    finally:
        session.close()


@api_bp.route("/leaderboard/elo", methods=["GET"])
def get_elo_leaderboard():
    """Get current ELO leaderboard."""
    session = db_manager.get_session()
    try:
        # Get latest ELO for each team
        latest_stats = (
            session.query(
                TeamGameStats.team_id,
                func.max(TeamGameStats.game_id).label("max_game_id"),
            )
            .group_by(TeamGameStats.team_id)
            .subquery()
        )

        leaders = (
            session.query(TeamGameStats, Team)
            .join(latest_stats, TeamGameStats.game_id == latest_stats.c.max_game_id)
            .join(Team, TeamGameStats.team_id == Team.id)
            .order_by(desc(TeamGameStats.elo_rating))
            .all()
        )

        return jsonify(
            [
                {
                    "rank": idx + 1,
                    "team": team.abbreviation,
                    "elo_rating": round(stats.elo_rating, 1),
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "win_pct": round(stats.win_pct, 3) if stats.win_pct else 0,
                }
                for idx, (stats, team) in enumerate(leaders)
            ]
        )
    finally:
        session.close()


@api_bp.route("/leaderboard/ppf", methods=["GET"])
def get_ppf_leaderboard():
    """Get points-for leaderboard."""
    session = db_manager.get_session()
    try:
        latest_stats = (
            session.query(
                TeamGameStats.team_id,
                func.max(TeamGameStats.game_id).label("max_game_id"),
            )
            .group_by(TeamGameStats.team_id)
            .subquery()
        )

        leaders = (
            session.query(TeamGameStats, Team)
            .join(latest_stats, TeamGameStats.game_id == latest_stats.c.max_game_id)
            .join(Team, TeamGameStats.team_id == Team.id)
            .order_by(desc(TeamGameStats.points_for))
            .all()
        )

        return jsonify(
            [
                {
                    "rank": idx + 1,
                    "team": team.abbreviation,
                    "ppf": round(stats.points_for, 2) if stats.points_for else 0,
                    "ppf_5game": round(stats.ppf_5game, 2)
                    if stats.ppf_5game
                    else None,
                }
                for idx, (stats, team) in enumerate(leaders)
            ]
        )
    finally:
        session.close()
