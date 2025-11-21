"""
Flask routes for exposing NBA metrics and data.
"""

from flask import Blueprint, jsonify, request
from sqlalchemy import func, desc
from loguru import logger
import pandas as pd

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import TeamGameStats, Game, Team
from nba_2x2x2.ml.models import GamePredictor
from nba_2x2x2.ml.features import FeatureEngineer

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


@api_bp.route("/predict/game", methods=["POST"])
def predict_game():
    """Predict outcome of a game given home and away team IDs."""
    session = db_manager.get_session()
    try:
        data = request.get_json()
        if not data or "home_team_id" not in data or "away_team_id" not in data:
            return jsonify({"error": "Missing home_team_id or away_team_id"}), 400

        home_team_id = data["home_team_id"]
        away_team_id = data["away_team_id"]

        # Get latest stats for both teams
        home_stats = (
            session.query(TeamGameStats)
            .filter(TeamGameStats.team_id == home_team_id)
            .order_by(desc(TeamGameStats.game_id))
            .first()
        )
        away_stats = (
            session.query(TeamGameStats)
            .filter(TeamGameStats.team_id == away_team_id)
            .order_by(desc(TeamGameStats.game_id))
            .first()
        )

        if not home_stats or not away_stats:
            return jsonify({"error": "Stats not found for one or both teams"}), 404

        # Build feature vector
        features = {
            # Home team metrics
            'home_elo': home_stats.elo_rating,
            'home_ppf': home_stats.points_for,
            'home_ppa': home_stats.points_against,
            'home_point_diff': home_stats.point_differential,
            'home_win_pct': home_stats.win_pct,
            'home_ppf_5game': home_stats.ppf_5game or 0,
            'home_ppa_5game': home_stats.ppa_5game or 0,
            'home_diff_5game': home_stats.diff_5game or 0,
            'home_ppf_10game': home_stats.ppf_10game or 0,
            'home_ppa_10game': home_stats.ppa_10game or 0,
            'home_diff_10game': home_stats.diff_10game or 0,
            'home_ppf_20game': home_stats.ppf_20game or 0,
            'home_ppa_20game': home_stats.ppa_20game or 0,
            'home_diff_20game': home_stats.diff_20game or 0,
            'home_days_rest': home_stats.days_rest or 0,
            'home_back_to_back': home_stats.back_to_back,
            # Away team metrics
            'away_elo': away_stats.elo_rating,
            'away_ppf': away_stats.points_for,
            'away_ppa': away_stats.points_against,
            'away_point_diff': away_stats.point_differential,
            'away_win_pct': away_stats.win_pct,
            'away_ppf_5game': away_stats.ppf_5game or 0,
            'away_ppa_5game': away_stats.ppa_5game or 0,
            'away_diff_5game': away_stats.diff_5game or 0,
            'away_ppf_10game': away_stats.ppf_10game or 0,
            'away_ppa_10game': away_stats.ppa_10game or 0,
            'away_diff_10game': away_stats.diff_10game or 0,
            'away_ppf_20game': away_stats.ppf_20game or 0,
            'away_ppa_20game': away_stats.ppa_20game or 0,
            'away_diff_20game': away_stats.diff_20game or 0,
            'away_days_rest': away_stats.days_rest or 0,
            'away_back_to_back': away_stats.back_to_back,
        }

        # Add interaction features
        features['elo_diff'] = features['home_elo'] - features['away_elo']
        features['ppf_diff'] = features['home_ppf'] - features['away_ppf']
        features['ppa_diff'] = features['home_ppa'] - features['away_ppa']
        features['diff_5game_diff'] = features['home_diff_5game'] - features['away_diff_5game']
        features['diff_10game_diff'] = features['home_diff_10game'] - features['away_diff_10game']
        features['diff_20game_diff'] = features['home_diff_20game'] - features['away_diff_20game']

        # Create DataFrame and make prediction
        X = pd.DataFrame([features])
        predictor = GamePredictor(model_dir="models")
        predictor.load_lightgbm_model()

        if predictor.lgb_model is None:
            return jsonify({"error": "Model not loaded"}), 500

        # Get prediction
        pred_prob = predictor.predict(X, model_type="lightgbm")[0]
        pred_binary = 1 if pred_prob > 0.5 else 0

        home_team = session.query(Team).filter(Team.id == home_team_id).first()
        away_team = session.query(Team).filter(Team.id == away_team_id).first()

        return jsonify(
            {
                "home_team": {
                    "id": home_team_id,
                    "name": home_team.full_name if home_team else "Unknown",
                    "abbreviation": home_team.abbreviation if home_team else "?",
                },
                "away_team": {
                    "id": away_team_id,
                    "name": away_team.full_name if away_team else "Unknown",
                    "abbreviation": away_team.abbreviation if away_team else "?",
                },
                "prediction": {
                    "home_team_win_probability": round(pred_prob, 4),
                    "away_team_win_probability": round(1 - pred_prob, 4),
                    "predicted_winner": home_team.abbreviation if pred_binary == 1 else away_team.abbreviation,
                    "confidence": round(max(pred_prob, 1 - pred_prob), 4),
                },
                "model": "LightGBM",
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
