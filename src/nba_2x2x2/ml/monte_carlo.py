"""
Monte Carlo simulation for season-end win projections.

Simulates the remaining season multiple times (typically 10,000 iterations)
with dynamic team rating updates after each simulated game to capture
team momentum, path dependence, and realistic season dynamics.
"""

import random
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class SimulatedGame:
    """Represents a game to be simulated."""
    home_team_id: int
    away_team_id: int
    home_win_prob: float


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation."""
    mean_wins: float
    median_wins: float
    std_dev: float
    percentile_10: float
    percentile_90: float
    distribution: List[int]  # Raw list of simulated final wins for analysis


def run_monte_carlo_simulation(
    current_wins: int,
    current_losses: int,
    remaining_games: List[Dict],
    num_simulations: int = 10000,
    team_id: int = None,
) -> SimulationResult:
    """
    Run Monte Carlo simulation of remaining season.

    Uses the blended win probabilities directly from the prediction model,
    rather than recalculating them from ratings. This preserves the model's
    calibration and prevents artificial rating inflation.

    Args:
        current_wins: Team's current wins
        current_losses: Team's current losses
        remaining_games: List of remaining games with format:
            {
                'home_team_id': int,
                'away_team_id': int,
                'home_win_prob': float,  # Blended probability (use directly)
                'elo_home_prob': float,  # For reference only
            }
        num_simulations: Number of season simulations to run (default 10,000)
        team_id: Optional team ID for filtering (when simulating specific team)

    Returns:
        SimulationResult with statistics from all simulations
    """
    simulated_final_wins = []

    # Run simulations
    for sim_num in range(num_simulations):
        # Reset for this simulation
        sim_wins = current_wins
        sim_losses = current_losses

        # Track recent performance for momentum adjustment
        # Use a 5-game rolling window to detect hot/cold streaks
        recent_results = []  # Last 5 game outcomes

        # Simulate each remaining game
        for game_idx, game in enumerate(remaining_games):
            home_team_id = game['home_team_id']
            away_team_id = game['away_team_id']
            blended_prob = game['home_win_prob']

            # Determine if this team is home or away
            if team_id is not None:
                if home_team_id == team_id:
                    # Team is home - use blended probability directly
                    team_win_prob = blended_prob
                elif away_team_id == team_id:
                    # Team is away - use away win probability (1 - home win prob)
                    team_win_prob = 1.0 - blended_prob
                else:
                    # Game doesn't involve this team, skip
                    continue
            else:
                # Simulating all teams - use blended probability directly
                team_win_prob = blended_prob

            # Apply small momentum adjustment based on recent results
            # If team won last 3 of 5, slightly boost win prob (up to +0.03)
            # If team lost last 3 of 5, slightly reduce win prob (down to -0.03)
            if len(recent_results) >= 5:
                recent_5_wins = sum(recent_results[-5:])
                if recent_5_wins >= 4:
                    # Hot streak: boost probability slightly
                    momentum_boost = 0.02
                elif recent_5_wins <= 1:
                    # Cold streak: reduce probability slightly
                    momentum_boost = -0.02
                else:
                    momentum_boost = 0.0
            else:
                momentum_boost = 0.0

            # Apply momentum adjustment (clamped to valid probability range)
            adjusted_prob = max(0.05, min(0.95, team_win_prob + momentum_boost))

            # Simulate game outcome probabilistically
            game_won = random.random() < adjusted_prob

            if game_won:
                sim_wins += 1
                recent_results.append(1)
            else:
                sim_losses += 1
                recent_results.append(0)

            # Keep only last 5 results
            if len(recent_results) > 5:
                recent_results = recent_results[-5:]

        simulated_final_wins.append(sim_wins)

    # Calculate statistics from simulations
    simulated_final_wins.sort()
    mean_wins = sum(simulated_final_wins) / len(simulated_final_wins)
    median_wins = simulated_final_wins[len(simulated_final_wins) // 2]

    # Calculate standard deviation
    variance = sum((w - mean_wins) ** 2 for w in simulated_final_wins) / len(simulated_final_wins)
    std_dev = variance ** 0.5

    # Calculate percentiles
    p10_idx = int(len(simulated_final_wins) * 0.10)
    p90_idx = int(len(simulated_final_wins) * 0.90)
    percentile_10 = simulated_final_wins[p10_idx]
    percentile_90 = simulated_final_wins[p90_idx]

    return SimulationResult(
        mean_wins=mean_wins,
        median_wins=median_wins,
        std_dev=std_dev,
        percentile_10=percentile_10,
        percentile_90=percentile_90,
        distribution=simulated_final_wins,
    )
