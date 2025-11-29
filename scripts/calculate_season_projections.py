#!/usr/bin/env python3
"""
Calculate season-end win projections for all NBA teams.

Methodology:
1. Get current season record (wins/losses from completed games)
2. For each remaining game:
   - Sum up the probability of winning (1 * probability) for each game
3. Project total wins = current wins + sum of probabilities
4. Project total losses = 82 - projected total wins
5. Calculate projected win percentage

This uses the blended model predictions (70% LightGBM + 30% ELO).

Usage:
    python calculate_season_projections.py
"""

import sys
import os
from datetime import datetime
import json

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from loguru import logger
from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import Game, Team, GamePrediction
from nba_2x2x2.ml.monte_carlo import run_monte_carlo_simulation


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        f"logs/season_projections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def calculate_season_projections(session, season=2025):
    """
    Calculate season-end projections for all teams.

    Args:
        session: Database session
        season: NBA season year (e.g., 2025 for 2025-26 season)

    Returns:
        List of team projections with current record and projected final record
    """
    logger.info("=" * 80)
    logger.info("CALCULATING SEASON PROJECTIONS")
    logger.info("=" * 80)
    logger.info(f"Season: {season}-{season + 1}")

    # Get all teams
    teams = session.query(Team).order_by(Team.full_name).all()
    logger.info(f"Processing {len(teams)} teams...")

    projections = []

    for team in teams:
        # Get current record (completed games)
        played_games = session.query(
            Game.home_team_id,
            Game.away_team_id,
            Game.home_team_score,
            Game.away_team_score,
        ).filter(
            ((Game.home_team_id == team.id) | (Game.away_team_id == team.id)),
            Game.season == season,
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

        # Get remaining games and their predictions
        # Use status field to identify scheduled (future) games
        remaining_games = session.query(
            GamePrediction.home_win_prob,
            GamePrediction.elo_home_prob,
            GamePrediction.lightgbm_home_prob,
            Game.home_team_id,
            Game.away_team_id,
            Game.id,
        ).select_from(Game).outerjoin(GamePrediction).filter(
            ((Game.home_team_id == team.id) | (Game.away_team_id == team.id)),
            Game.season == season,
            Game.status == "scheduled",
        ).all()

        remaining_count = len(remaining_games)

        # Probability summation: sum win probabilities for each remaining game
        # Expected value of wins = sum of individual game win probabilities
        projected_remaining_wins = 0.0
        remaining_strength_sum = 0.0  # For SOS calculation

        # Prepare data for Monte Carlo simulation
        mc_games = []

        for game_result in remaining_games:
            # Handle both Game and GamePrediction data from join
            if not game_result or not game_result[0]:  # No prediction yet
                continue

            home_win_prob = game_result[0]
            elo_home_prob = game_result[1]
            home_team_id = game_result[3]
            away_team_id = game_result[4]

            if home_team_id == team.id:
                # Team is home - use home win probability
                prob = float(home_win_prob)
                # Opponent strength = away team's win prob (1 - home win prob)
                opponent_win_prob = 1.0 - float(home_win_prob)
            else:
                # Team is away - use away win probability (1 - home win prob)
                prob = 1.0 - float(home_win_prob)
                # Opponent strength = home team's win prob
                opponent_win_prob = float(home_win_prob)

            projected_remaining_wins += prob
            # Track opponent strength (higher prob = stronger opponent)
            remaining_strength_sum += opponent_win_prob

            # Add to Monte Carlo simulation games
            mc_games.append({
                'home_team_id': home_team_id,
                'away_team_id': away_team_id,
                'home_win_prob': float(home_win_prob),
                'elo_home_prob': float(elo_home_prob),
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
        # Total games in regular season = 82
        total_games_played = wins + losses
        projected_total_wins = wins + projected_remaining_wins
        projected_total_losses = 82 - projected_total_wins
        projected_win_pct = round(projected_total_wins / 82.0, 3)

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
            "games_played": total_games_played,
            "remaining_games": remaining_count,
            "projected_remaining_wins": round(projected_remaining_wins, 2),
            "projected_total_wins": round(projected_total_wins, 2),
            "projected_total_losses": round(projected_total_losses, 2),
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

    logger.info("\n" + "=" * 80)
    logger.info("SEASON PROJECTIONS RESULTS")
    logger.info("=" * 80)
    logger.info(
        f"{'Rank':<5} {'Team':<25} {'W':<4} {'L':<4} {'Proj W':<8} {'Proj L':<8} {'Win %':<8}"
    )
    logger.info("-" * 80)

    for idx, proj in enumerate(projections, 1):
        logger.info(
            f"{idx:<5} {proj['team_abbr']:<25} {proj['current_wins']:<4} "
            f"{proj['current_losses']:<4} {proj['projected_total_wins']:<8.1f} "
            f"{proj['projected_total_losses']:<8.1f} {proj['projected_win_pct']:<8.1%}"
        )

    logger.info("=" * 80)
    logger.info(f"Season projections calculated for {len(teams)} teams")
    logger.info("=" * 80)

    return projections


def main():
    """Main entry point."""
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    db_manager = DatabaseManager()
    db_manager.connect()
    session = db_manager.get_session()

    try:
        # Get season projections
        projections = calculate_season_projections(session, season=2025)

        # Save to JSON file for easy access
        output_file = f"logs/season_projections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(
                {
                    "season": 2025,
                    "season_display": "2025-26",
                    "timestamp": datetime.now().isoformat() + "Z",
                    "projections": projections,
                },
                f,
                indent=2,
            )
        logger.info(f"Projections saved to {output_file}")

    finally:
        db_manager.disconnect()


if __name__ == "__main__":
    main()
