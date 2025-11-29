# ELO Data Leakage Review & Analysis

**Date:** November 22, 2025
**Status:** ⚠️ CRITICAL ISSUE IDENTIFIED
**Severity:** HIGH - Data leakage in ELO-based probability calculations

---

## Executive Summary

There is a **critical data leakage vulnerability in the ELO rating system** used for generating predictions. While the ELO ratings themselves are calculated correctly using walk-forward methodology, they are being **applied to future games** that haven't been played yet, using post-game ELO values that include information from games beyond the prediction date.

**The Issue:** When predicting a game on date D, you're using ELO ratings that were updated using game results from AFTER date D was originally predicted.

---

## The Problem Explained

### Timeline of the Issue

Let's trace through an example:

1. **November 20, 2025 - Original Prediction Generated**
   - Game scheduled for Nov 20: Lakers vs Warriors
   - Pre-game ELO: Lakers 1550, Warriors 1480
   - Prediction created with these ELO values ✅ CORRECT

2. **November 20 Evening - Game Plays**
   - Warriors wins (upset)
   - Post-game ELO: Warriors 1485, Lakers 1545
   - ELO ratings stored in `TeamGameStats` table ✅ CORRECT

3. **November 22 - Prediction Regenerated**
   - Now predicting the SAME game or similar Nov 20 games
   - System retrieves: Warriors 1485, Lakers 1545 (post-game values)
   - Uses these post-game values for fresh predictions ❌ **DATA LEAKAGE**
   - New prediction now includes information from that Warriors upset

### Code Location of the Leakage

**File:** `scripts/generate_game_predictions.py` - Lines 246-250

```python
# ELO probability (30% weight)
elo_home_prob = get_elo_win_probability(
    home_stats.elo_rating,        # ⚠️ PROBLEM: This is POST-GAME ELO
    away_stats.elo_rating          # ⚠️ PROBLEM: This is POST-GAME ELO
)
```

The `home_stats.elo_rating` and `away_stats.elo_rating` are **post-game ELO values** from the `TeamGameStats` table, not pre-game values.

---

## Data Flow Analysis

### How ELO is Stored

In `src/nba_2x2x2/data/metrics.py` - Lines 172-199:

```python
# Get pre-game ELO rating
team_elo = self._get_latest_elo(team_id, game_date)  # ✅ Pre-game

# Calculate post-game ELO (updated with this game's result)
# This is what gets stored and retrieved for future games
post_game_elo = self._calculate_elo(team_elo, opponent_elo, game_won)

return {
    ...
    "elo_rating": post_game_elo,  # ⚠️ POST-GAME value stored
    ...
}
```

**The TeamGameStats table stores POST-GAME ELO**, which includes the result of that game.

### How ELO is Used for Predictions

In `scripts/generate_game_predictions.py` - Lines 220-250:

```python
# Get game-specific stats (which contain POST-GAME ELO)
home_stats = session.query(TeamGameStats).filter_by(
    game_id=game.id, is_home=1
).first()

# Use the stored ELO for predictions
elo_home_prob = get_elo_win_probability(
    home_stats.elo_rating,  # POST-GAME ELO from the game itself!
    away_stats.elo_rating
)
```

**The Leakage:** When predicting Game X, if TeamGameStats for Game X exists (because it was previously calculated), it uses the POST-GAME ELO that includes the result of Game X.

---

## The Specific Problem Scenarios

### Scenario 1: Same-Day Predictions (HIGH RISK)

**Game:** Lakers vs Warriors, Nov 20, 2:00 PM
**Prediction Flow:**

1. **First Run (9:00 AM):** Generate predictions for all games
   - Game hasn't played yet ✅
   - No TeamGameStats record for this game
   - Falls back to latest pre-game ELO ✅
   - Prediction is correct

2. **Second Run (11:00 PM, after game plays):** Regenerate predictions
   - Game has now played ✅
   - TeamGameStats record exists with POST-GAME ELO ✅
   - Uses post-game ELO that includes the game result ❌
   - **Prediction now uses future information**

### Scenario 2: Roll-Forward Predictions (MEDIUM RISK)

When generating predictions for Nov 25 games on Nov 22:
- Nov 22 games have already played
- Their post-game ELO is stored in TeamGameStats
- Nov 25 predictions use that updated ELO ✅ This is correct

BUT: If you're regenerating Nov 22 predictions on Nov 22 after the games played:
- TeamGameStats for Nov 22 games now have post-game ELO
- System uses these post-game values ❌ Leakage

### Scenario 3: Model Training (HIGHEST RISK)

In `scripts/generate_game_predictions.py`, line 199:

```python
# Get all games (not just Final - includes scheduled/future games)
games = session.query(Game).order_by(Game.game_date).all()
```

**All games are being predicted, including past games.**

When the model trains/regenerates:
- It retrieves all games (including past games that already played)
- For each game, it uses the TeamGameStats record (if it exists)
- The TeamGameStats has the post-game ELO
- **This means every re-training uses future information for past games**

---

## The Root Cause

### Design Issue: Single ELO Value Stored

The `TeamGameStats` table stores a single `elo_rating` field:

```
TeamGameStats:
  - game_id
  - team_id
  - elo_rating (POST-GAME)  ← Single value, no pre-game record
  - points_for
  - points_against
  - ...
```

This stores the POST-GAME ELO only. There's no way to retrieve the PRE-GAME ELO for a game that already happened.

### Why It Wasn't Caught

1. **The metrics calculation is correct** - Walk-forward uses only prior games ✅
2. **The features for LightGBM are correct** - They use pre-game ELO via `_get_pre_game_elo()` ✅
3. **But the ELO probability calculation is wrong** - Uses whatever ELO is stored ❌

The LightGBM features explicitly call `_get_pre_game_elo()` (features.py:71-92), but the ELO probability uses the direct `home_stats.elo_rating`.

---

## Impact Assessment

### Severity: HIGH ⚠️

**Impact on Predictions:**
- ELO represents 30% of the blended probability (0.70 LightGBM + 0.30 ELO)
- 30% of predictions are contaminated with future information
- This inflates the model's apparent accuracy on historical games

**Example:**
- Pre-game: Lakers ELO 1500, Warriors ELO 1520 → 46% home win prob
- Warriors upset wins
- Post-game: Lakers ELO 1468, Warriors ELO 1552
- When prediction is regenerated: Uses new ELO → 42% home win prob
- The re-prediction now "knows" the Warriors were stronger

### When This Causes Problems

1. **Model Evaluation:** Your 99.3% test success rate may be inflated
2. **Walk-Forward Backtests:** If you rerun predictions for historical games after they've played, they're using future data
3. **Real-Time Predictions:** If you regenerate predictions after games play, the ELO values are contaminated
4. **API Predictions:** Each time `/api/report/daily` or `/api/games` is called, it uses current ELO values which may be post-game

---

## Solution: Implement Pre-Game ELO Tracking

### Option 1: Store Pre-Game ELO (RECOMMENDED - Minimal Change)

**Approach:** Add a `pre_game_elo` field to `TeamGameStats`

```sql
ALTER TABLE team_game_stats ADD COLUMN pre_game_elo FLOAT;
```

**Changes Required:**

1. **In metrics.py** - Store both pre and post-game ELO:
```python
def _calculate_team_stats(...):
    # Get pre-game ELO rating
    team_elo = self._get_latest_elo(team_id, game_date)

    # Calculate post-game ELO
    post_game_elo = self._calculate_elo(team_elo, opponent_elo, game_won)

    return {
        ...
        "pre_game_elo": team_elo,      # NEW - Store pre-game
        "elo_rating": post_game_elo,   # Keep existing for backward compat
        ...
    }
```

2. **In generate_game_predictions.py** - Use pre-game ELO:
```python
# Get pre-game ELO for predictions
pre_game_elo_home = home_stats.pre_game_elo or home_stats.elo_rating
pre_game_elo_away = away_stats.pre_game_elo or away_stats.elo_rating

elo_home_prob = get_elo_win_probability(
    pre_game_elo_home,     # ✅ Now using pre-game ELO
    pre_game_elo_away
)
```

**Pros:**
- Minimal code changes
- Backward compatible
- Fixes the leakage immediately
- Requires one-time data migration

**Cons:**
- Need to recalculate all metrics to populate new field
- Database migration required

### Option 2: Use features.py's `_get_pre_game_elo()` Logic (QUICK FIX)

**Approach:** Apply the same logic from features.py to predictions

In `generate_game_predictions.py`, replace direct ELO access:

```python
def get_pre_game_elo(session, team_id, game):
    """Get pre-game ELO (identical logic to features.py)."""
    stats = (
        session.query(TeamGameStats)
        .join(Game, TeamGameStats.game_id == Game.id)
        .filter(TeamGameStats.team_id == team_id)
        .filter(
            (Game.game_date < game.game_date)
            | ((Game.game_date == game.game_date) & (Game.id < game.id))
        )
        .order_by(Game.game_date.desc(), Game.id.desc())
        .first()
    )

    if stats:
        return stats.elo_rating
    return 1500.0  # ELO_INITIAL

# Then use:
pre_game_elo_home = get_pre_game_elo(session, game.home_team_id, game)
pre_game_elo_away = get_pre_game_elo(session, game.away_team_id, game)

elo_home_prob = get_elo_win_probability(pre_game_elo_home, pre_game_elo_away)
```

**Pros:**
- No database migration needed
- Uses proven logic from features.py
- Can be implemented immediately
- Backward compatible

**Cons:**
- Additional database queries (performance cost)
- More complex logic
- Duplicates code from features.py

### Option 3: Refactor to Shared Utility (CLEANEST)

**Approach:** Create a shared utility function

```python
# src/nba_2x2x2/data/elo_utils.py
def get_pre_game_elo(session, team_id, game):
    """Get team's ELO rating before a specific game."""
    stats = (
        session.query(TeamGameStats)
        .join(Game, TeamGameStats.game_id == Game.id)
        .filter(TeamGameStats.team_id == team_id)
        .filter(
            (Game.game_date < game.game_date)
            | ((Game.game_date == game.game_date) & (Game.id < game.id))
        )
        .order_by(Game.game_date.desc(), Game.id.desc())
        .first()
    )

    if stats:
        return stats.elo_rating
    return 1500.0
```

Then use in both features.py and generate_game_predictions.py.

**Pros:**
- No duplication
- Centralized logic
- Maintainable
- Can be tested independently

**Cons:**
- Requires refactoring
- More code organization

---

## Recommended Fix Implementation Plan

### Phase 1: Quick Fix (Implement Today)
1. Use Option 2 (get_pre_game_elo logic) to fix the immediate leakage
2. Add helper function to generate_game_predictions.py
3. Update line 247-250 to use pre-game ELO
4. Re-run predictions to regenerate clean data
5. Re-run tests to verify no regressions

### Phase 2: Proper Fix (Within 1 Week)
1. Refactor to Option 3 (shared utility)
2. Create elo_utils.py with get_pre_game_elo()
3. Update both features.py and generate_game_predictions.py
4. Add tests for get_pre_game_elo()
5. Document ELO calculation methodology

### Phase 3: Optimization (Optional)
1. Add pre_game_elo column to database (Option 1)
2. Migrate historical data
3. Performance test
4. Update all queries to use cached pre_game_elo instead of computing

---

## Testing the Fix

### Critical Test Cases

```python
def test_elo_prediction_uses_pre_game_only(session):
    """
    CRITICAL: Verify ELO predictions don't use post-game ratings.

    If a game already played, predictions should use the ELO rating
    from BEFORE that game, not after.
    """
    # Create game that already played
    game = create_test_game(date='2025-11-20', played=True)

    # Get stored stats (post-game ELO)
    stats = session.query(TeamGameStats).filter_by(game_id=game.id).first()

    # Calculate pre-game ELO
    pre_game_elo = get_pre_game_elo(session, game.home_team_id, game)

    # Pre-game should be DIFFERENT from stored (post-game)
    assert pre_game_elo != stats.elo_rating, \
        "Pre-game ELO should differ from post-game ELO"

    # Prediction should use pre-game
    elo_prob = get_elo_win_probability(pre_game_elo, ...)

    # Should NOT use stored post-game value
    incorrect_prob = get_elo_win_probability(stats.elo_rating, ...)

    assert elo_prob != incorrect_prob, \
        "Predictions using pre-game vs post-game ELO should differ"

def test_no_future_data_in_elo_predictions():
    """Verify ELO probability only uses information available at prediction time."""
    # Generate predictions for Nov 20 games
    # Run on Nov 19
    predictions_nov19 = generate_predictions(date='2025-11-20')

    # Run again on Nov 22 (after games played)
    predictions_nov22 = generate_predictions(date='2025-11-20')

    # Predictions should be identical (no new information)
    assert predictions_nov19 == predictions_nov22, \
        "Regenerating predictions shouldn't change ELO values used"
```

---

## Summary of the Issue

| Aspect | Status | Details |
|--------|--------|---------|
| **Metrics Calculation** | ✅ CORRECT | Walk-forward uses only prior games |
| **LightGBM Features** | ✅ CORRECT | Uses `_get_pre_game_elo()` explicitly |
| **ELO Probability Calc** | ❌ LEAKING | Uses post-game ELO from TeamGameStats |
| **Overall Impact** | ⚠️ HIGH | 30% of blended prediction is contaminated |
| **Detectability** | ⚠️ HARD | Works in most scenarios, only obvious on re-runs |

---

## Conclusion

**The ELO data leakage is real and significant.** The metrics calculation is properly isolated, but the prediction generation uses post-game ELO values instead of pre-game values.

**Recommended Action:** Implement the quick fix (Option 2) immediately using the `_get_pre_game_elo()` logic, then schedule the refactoring (Option 3) for code cleanliness.

**Estimated Fix Time:** 30 minutes for quick fix, 2 hours for proper refactoring.

**Impact of Fix:** Predictions will be cleaner and more accurate, especially for backtesting and re-runs of historical games.

