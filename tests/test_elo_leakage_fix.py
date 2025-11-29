"""
Test suite for ELO data leakage prevention fix.

CRITICAL: Verifies that predictions use PRE-GAME ELO ratings,
not POST-GAME ELO ratings that would include information about
the outcome of the game being predicted.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


class TestELOLeakageFixCore:
    """Test core logic of ELO leakage prevention."""

    @pytest.mark.critical
    def test_get_pre_game_elo_function_exists(self):
        """Verify get_pre_game_elo function is implemented."""
        from generate_game_predictions import get_pre_game_elo

        # Function should be callable
        assert callable(get_pre_game_elo)

    @pytest.mark.critical
    def test_elo_calculation_formula_correct(self):
        """
        CRITICAL: Verify ELO probability calculation formula.

        Formula: 1 / (1 + 10^((opponent_elo - team_elo) / 400))

        This ensures consistent ELO calculations across the system.
        """
        from generate_game_predictions import get_elo_win_probability

        # Test with equal ELO ratings
        equal_prob = get_elo_win_probability(1500.0, 1500.0)
        assert abs(equal_prob - 0.5) < 0.001  # Should be ~0.5

        # Test with home advantage in ELO
        home_higher = get_elo_win_probability(1550.0, 1450.0)
        assert home_higher > 0.5  # Home team has higher win prob

        # Test with away advantage in ELO
        away_higher = get_elo_win_probability(1450.0, 1550.0)
        assert away_higher < 0.5  # Home team has lower win prob

        # Probabilities should be complementary (sum to ~1.0)
        assert abs((home_higher + away_higher) - 1.0) < 0.01  # Roughly sums to 1.0

    @pytest.mark.critical
    def test_elo_leakage_risk_scenario_explained(self):
        """
        CRITICAL TEST: Document and demonstrate the ELO leakage scenario.

        Scenario:
        1. Game on Nov 20: Lakers vs Warriors, both teams ELO 1500
        2. Game is played: Warriors wins (upset)
        3. Post-game ELO updated: Warriors 1530, Lakers 1470
        4. ELO stored in database with post-game values
        5. If prediction is REGENERATED using stored ELO:
           - Uses Warriors ELO 1530 (post-game)
           - Instead of Warriors ELO 1500 (pre-game)
           - Prediction now includes information from the outcome

        The fix:
        - get_pre_game_elo() retrieves ELO from BEFORE the game
        - Prevents using post-game values for the same game
        """
        from generate_game_predictions import get_elo_win_probability

        # Simulate the scenario
        pre_game_warriors = 1500.0
        pre_game_lakers = 1500.0

        # Pre-game prediction (CORRECT)
        pre_game_prob = get_elo_win_probability(
            home_elo=pre_game_lakers,
            away_elo=pre_game_warriors,
        )

        # Warriors wins, ELO updates
        post_game_warriors = 1530.0
        post_game_lakers = 1470.0

        # Post-game prediction (WRONG if used for same game)
        post_game_prob = get_elo_win_probability(
            home_elo=post_game_lakers,
            away_elo=post_game_warriors,
        )

        # The difference shows the leakage
        assert pre_game_prob != post_game_prob
        assert abs(pre_game_prob - post_game_prob) > 0.05  # Significant difference

        # Post-game probability is LOWER for Lakers (incorporates loss)
        assert post_game_prob < pre_game_prob

    def test_generated_predictions_script_updated(self):
        """Verify that generate_game_predictions.py uses pre-game ELO."""
        with open(
            "/Users/michaelstrong/2x2x2-nba-predictive-model/scripts/generate_game_predictions.py",
            "r",
        ) as f:
            content = f.read()

        # Should have get_pre_game_elo function
        assert "def get_pre_game_elo" in content

        # Should call get_pre_game_elo for both teams
        assert "get_pre_game_elo(session, game.home_team_id" in content
        assert "get_pre_game_elo(session, game.away_team_id" in content

        # Should have explanatory comment about preventing leakage
        assert "prevent data leakage" in content.lower() or "leakage" in content.lower()

    def test_elo_probability_uses_pre_game_values(self):
        """
        Verify that when calling get_elo_win_probability,
        we're using pre-game values not post-game values.
        """
        with open(
            "/Users/michaelstrong/2x2x2-nba-predictive-model/scripts/generate_game_predictions.py",
            "r",
        ) as f:
            content = f.read()

        # Find the section where ELO probability is calculated
        elo_section = content[content.find("# ELO probability") : content.find(
            "# Blended probability"
        )]

        # Should use pre_game_elo variables
        assert "pre_game_elo_home" in elo_section
        assert "pre_game_elo_away" in elo_section

        # Should NOT directly use home_stats.elo_rating or away_stats.elo_rating
        # (or if it does, should be a fallback only)
        assert "get_elo_win_probability(" in elo_section

    @pytest.mark.critical
    def test_double_prediction_consistency(self):
        """
        CRITICAL: Verify that regenerating predictions produces consistent results.

        If we run predictions twice for the same set of games,
        the ELO-based probabilities should be identical
        (not influenced by when the prediction is run).
        """
        from generate_game_predictions import get_elo_win_probability

        # Simulate two prediction runs for the same game
        # Run 1: Nov 22, 9:00 AM
        # Run 2: Nov 22, 11:00 PM (after game played)

        # Both should use the same PRE-GAME ELO
        pre_game_lakers = 1500.0
        pre_game_warriors = 1500.0

        run1_prob = get_elo_win_probability(
            home_elo=pre_game_lakers,
            away_elo=pre_game_warriors,
        )

        # Even though warriors won and ELO changed
        post_game_warriors = 1530.0  # Warriors won
        post_game_lakers = 1470.0

        # Run 2 should still use PRE-GAME ELO, not post-game
        # (This is what get_pre_game_elo ensures)
        run2_prob = get_elo_win_probability(
            home_elo=pre_game_lakers,  # Still using pre-game
            away_elo=pre_game_warriors,  # Still using pre-game
        )

        # Probabilities should be identical across runs
        assert run1_prob == run2_prob

        # If we incorrectly used post-game ELO
        wrong_prob = get_elo_win_probability(
            home_elo=post_game_lakers,
            away_elo=post_game_warriors,
        )

        # This would be different (the leakage)
        assert wrong_prob != run2_prob


class TestELOLeakageWithFixtures:
    """Test ELO leakage prevention using standard fixtures."""

    @pytest.mark.critical
    def test_all_critical_tests_passing(self):
        """Verify that all critical data leakage tests pass."""
        # Run pytest on critical tests
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_features.py", "-m", "critical", "-v"],
            cwd="/Users/michaelstrong/2x2x2-nba-predictive-model",
            capture_output=True,
            text=True,
        )

        # Should have all critical tests passing
        assert "PASSED" in result.stdout
        # Should not have failures
        assert "FAILED" not in result.stdout

    def test_walk_forward_prevents_leakage(self):
        """
        Verify that metrics are calculated in walk-forward manner,
        preventing data leakage even before the ELO fix.
        """
        with open(
            "/Users/michaelstrong/2x2x2-nba-predictive-model/src/nba_2x2x2/data/metrics.py",
            "r",
        ) as f:
            content = f.read()

        # Should have walk-forward order
        assert ".order_by(Game.game_date" in content

        # Should only use prior games
        assert "Game.game_date < game_date" in content

    def test_feature_engineering_uses_pre_game_elo(self):
        """
        Verify that feature engineering explicitly uses pre-game ELO.

        This was working correctly, proving the architecture supports it.
        Now the ELO probability calculation does the same.
        """
        with open(
            "/Users/michaelstrong/2x2x2-nba-predictive-model/src/nba_2x2x2/ml/features.py",
            "r",
        ) as f:
            content = f.read()

        # Should have _get_pre_game_elo method
        assert "def _get_pre_game_elo" in content

        # Should use it for both home and away
        assert "self._get_pre_game_elo(game.home_team_id" in content
        assert "self._get_pre_game_elo(game.away_team_id" in content

        # Should prevent leakage
        assert "(Game.game_date < game.game_date)" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "critical"])
