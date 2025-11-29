#!/usr/bin/env python3
"""
Generate daily report on prediction performance.

Includes:
1. Yesterday's prediction accuracy
2. Win probability calibration trends
3. Point differential error analysis
4. Model component comparison
5. Upcoming games today

Usage:
    python generate_daily_report.py
"""

import sys
import os
from datetime import datetime, timedelta

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pandas as pd
import numpy as np
from loguru import logger

from nba_2x2x2.data import DatabaseManager
from nba_2x2x2.data.models import Game, GamePrediction, Team


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO",
    )
    os.makedirs("logs", exist_ok=True)
    logger.add(
        f"logs/daily_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
    )


def get_yesterdays_games(session):
    """Get all games from yesterday with predictions."""
    yesterday = datetime.now().date() - timedelta(days=1)

    games = session.query(
        Game.game_date,
        Game.id,
        Game.home_team_id,
        Game.away_team_id,
        Game.home_team_score,
        Game.away_team_score,
        GamePrediction.home_win_prob,
        GamePrediction.point_differential,
        GamePrediction.lightgbm_home_prob,
        GamePrediction.elo_home_prob,
    ).join(GamePrediction).filter(
        Game.game_date >= yesterday,
        Game.game_date < yesterday + timedelta(days=1),
        Game.status == "Final"
    ).all()

    return games


def analyze_yesterdays_performance(session):
    """Analyze prediction accuracy for yesterday's games."""
    logger.info("=" * 120)
    logger.info("YESTERDAY'S PREDICTION PERFORMANCE")
    logger.info("=" * 120)

    games = get_yesterdays_games(session)

    if not games:
        print("\n" + "=" * 120)
        print("NO COMPLETED GAMES YESTERDAY")
        print("=" * 120)
        return None

    # Get team names for each game
    games_data = []
    for g in games:
        home_team = session.query(Team).filter(Team.id == g.home_team_id).first()
        away_team = session.query(Team).filter(Team.id == g.away_team_id).first()
        games_data.append({
            'date': g.game_date,
            'home_team': home_team.full_name if home_team else f"Team {g.home_team_id}",
            'away_team': away_team.full_name if away_team else f"Team {g.away_team_id}",
            'home_score': g.home_team_score,
            'away_score': g.away_team_score,
            'actual_diff': g.home_team_score - g.away_team_score,
            'home_won': 1 if g.home_team_score > g.away_team_score else 0,
            'pred_home_prob': g.home_win_prob,
            'pred_diff': g.point_differential,
            'lgb_prob': g.lightgbm_home_prob,
            'elo_prob': g.elo_home_prob,
        })

    df = pd.DataFrame(games_data)

    print("\n" + "=" * 120)
    # Handle both datetime and date objects
    game_date = df['date'].iloc[0]
    if hasattr(game_date, 'date'):
        game_date_str = str(game_date.date())
    else:
        game_date_str = str(game_date)
    print(f"GAMES FROM {game_date_str}")
    print("=" * 120)
    print(f"\nTotal games: {len(df)}")

    # Win prediction accuracy
    correct_winner = (
        ((df['pred_home_prob'] >= 0.5) & (df['home_won'] == 1)) |
        ((df['pred_home_prob'] < 0.5) & (df['home_won'] == 0))
    ).sum()
    win_accuracy = correct_winner / len(df)

    print(f"Win Prediction Accuracy: {win_accuracy:.1%} ({correct_winner}/{len(df)})")

    # Point differential analysis
    df['diff_error'] = np.abs(df['pred_diff'] - df['actual_diff'])
    mae = df['diff_error'].mean()
    median_error = df['diff_error'].median()

    print(f"\nPoint Differential Predictions:")
    print(f"  Mean Absolute Error: {mae:.2f} points")
    print(f"  Median Error: {median_error:.2f} points")
    print(f"  Std Dev: {df['diff_error'].std():.2f} points")

    # Game-by-game breakdown
    print(f"\n" + "-" * 190)
    print(f"{'#':<3} {'Home Team':<25} {'Away Team':<25} {'Home Win %':<12} {'Score':<10} {'Actual Diff':<12} {'Pred Diff':<12} {'Error':<8} {'Correct':<10}")
    print("-" * 190)

    for idx, row in df.iterrows():
        score = f"{row['home_score']}-{row['away_score']}"
        actual = row['actual_diff']
        pred = row['pred_diff']
        error = row['diff_error']
        home_win_pct = f"{row['pred_home_prob']:.1%}"
        correct = "✓" if ((row['pred_home_prob'] >= 0.5) == (row['home_won'] == 1)) else "✗"

        print(f"{idx+1:<3} {row['home_team']:<25} {row['away_team']:<25} {home_win_pct:<12} {score:<10} {actual:+<12.1f} {pred:+<12.1f} {error:<8.2f} {correct:<10}")

    print("-" * 190)

    return df


def get_todays_games(session):
    """Get all games scheduled for today."""
    today = datetime.now().date()

    games = session.query(
        Game.id,
        Game.game_date,
        Game.home_team_id,
        Game.away_team_id,
        GamePrediction.home_win_prob,
        GamePrediction.point_differential,
    ).outerjoin(GamePrediction).filter(
        Game.game_date >= today,
        Game.game_date < today + timedelta(days=1)
    ).all()

    return games


def show_todays_schedule(session):
    """Show upcoming games for today."""
    logger.info("=" * 120)
    logger.info("TODAY'S GAMES & PREDICTIONS")
    logger.info("=" * 120)

    games = get_todays_games(session)

    if not games:
        print("\n" + "=" * 120)
        print("NO GAMES SCHEDULED TODAY")
        print("=" * 120)
        return

    print("\n" + "=" * 120)
    print(f"GAMES FOR {datetime.now().date()}")
    print("=" * 120)
    print(f"\nTotal games: {len(games)}")
    print(f"\n" + "-" * 140)
    print(f"{'#':<3} {'Time':<8} {'Home Team':<25} {'Away Team':<25} {'Home Win %':<14} {'Predicted Diff':<15} {'Favorite':<15}")
    print("-" * 140)

    for idx, game in enumerate(games, 1):
        # Get team names
        home_team = session.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = session.query(Team).filter(Team.id == game.away_team_id).first()
        home_name = home_team.full_name if home_team else f"Team {game.home_team_id}"
        away_name = away_team.full_name if away_team else f"Team {game.away_team_id}"

        time_str = game.game_date.strftime("%H:%M") if game.game_date else "TBD"

        # Handle missing predictions
        if game.home_win_prob is not None:
            home_prob = game.home_win_prob
            diff = game.point_differential
            favorite = f"Home {home_prob:.1%}" if home_prob >= 0.5 else f"Away {1-home_prob:.1%}"
            prob_str = f"{home_prob:<14.1%}"
            diff_str = f"{diff:+<15.2f}"
        else:
            favorite = "No Prediction"
            prob_str = "N/A           "
            diff_str = "N/A            "

        print(f"{idx:<3} {time_str:<8} {home_name:<25} {away_name:<25} {prob_str} {diff_str} {favorite:<15}")

    print("-" * 140)


def show_model_insights(session):
    """Show interesting insights about model performance."""
    logger.info("=" * 120)
    logger.info("MODEL INSIGHTS & DIAGNOSTICS")
    logger.info("=" * 120)

    # Get all completed games with predictions
    games = session.query(
        Game.home_team_score,
        Game.away_team_score,
        GamePrediction.home_win_prob,
        GamePrediction.point_differential,
        GamePrediction.lightgbm_home_prob,
        GamePrediction.elo_home_prob,
    ).join(GamePrediction).filter(
        Game.status == "Final"
    ).all()

    if not games:
        print("\nNo completed games to analyze")
        return

    df = pd.DataFrame([
        {
            'home_won': 1 if g.home_team_score > g.away_team_score else 0,
            'home_prob': g.home_win_prob,
            'diff_error': abs(g.point_differential - (g.home_team_score - g.away_team_score)),
            'lgb_prob': g.lightgbm_home_prob,
            'elo_prob': g.elo_home_prob,
        }
        for g in games
    ])

    print("\n" + "-" * 120)
    print("OVERALL STATISTICS (All Time)")
    print("-" * 120)

    # Accuracy by confidence level
    high_conf = df[df['home_prob'] >= 0.65]
    medium_conf = df[(df['home_prob'] >= 0.55) & (df['home_prob'] < 0.65)]
    low_conf = df[df['home_prob'] < 0.55]

    print(f"\nAccuracy by Confidence Level:")
    print(f"  High (≥65%):    {(high_conf['home_won'].mean()):.1%} ({high_conf['home_won'].sum()}/{len(high_conf)} games)")
    print(f"  Medium (55-65%): {(medium_conf['home_won'].mean()):.1%} ({medium_conf['home_won'].sum()}/{len(medium_conf)} games)")
    print(f"  Low (<55%):     {(low_conf['home_won'].mean()):.1%} ({low_conf['home_won'].sum()}/{len(low_conf)} games)")

    # Point differential accuracy
    within_5 = (df['diff_error'] <= 5).sum()
    within_10 = (df['diff_error'] <= 10).sum()

    print(f"\nPoint Differential Accuracy:")
    print(f"  Within 5 points:  {(within_5/len(df)):.1%} ({within_5} games)")
    print(f"  Within 10 points: {(within_10/len(df)):.1%} ({within_10} games)")

    # Component comparison
    lgb_wins = (df['lgb_prob'] >= 0.5)
    elo_wins = (df['elo_prob'] >= 0.5)

    lgb_accuracy = (lgb_wins == (df['home_won'] == 1)).mean()
    elo_accuracy = (elo_wins == (df['home_won'] == 1)).mean()

    print(f"\nComponent Model Performance:")
    print(f"  LightGBM (70% weight): {lgb_accuracy:.1%} accuracy")
    print(f"  ELO-based (30% weight): {elo_accuracy:.1%} accuracy")

    print("-" * 120)


def main():
    """Main entry point."""
    os.makedirs("logs", exist_ok=True)
    setup_logging()

    try:
        # Connect to database
        logger.info("Connecting to database...")
        db_manager = DatabaseManager()
        db_manager.connect()
        session = db_manager.get_session()

        # Generate report sections
        analyze_yesterdays_performance(session)
        show_todays_schedule(session)
        show_model_insights(session)

        # Cleanup
        session.close()
        db_manager.disconnect()

        logger.info("\n" + "=" * 120)
        logger.info("Daily report generated successfully!")
        logger.info("=" * 120)

    except Exception as e:
        logger.error(f"Report generation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
