# Daily Prediction Update Workflow

## Overview

This document describes the automated daily workflow for updating NBA game predictions and evaluating model accuracy.

## Architecture

```
Daily Workflow (3:00 AM - 4:30 AM EST)
│
├─ Step 1: API Sync (3:00 AM) [reload_clean_from_api.py]
│  └─ Download latest games from Ball Don't Lie API
│  └─ Update games table with new completed games
│
├─ Step 2: Metrics Calculation (3:30 AM) [calculate_metrics.py]
│  └─ Walk-forward calculation of team stats
│  └─ ELO rating updates
│  └─ PPF, PPA, pace, etc. (using only prior games)
│
├─ Step 3: Prediction Generation (4:00 AM) [generate_game_predictions.py]
│  └─ LightGBM predictions (70% weight)
│  └─ ELO-based predictions (30% weight)
│  └─ Blended win probabilities
│  └─ Point differential predictions
│
└─ Step 4: Daily Report (4:30 AM) [generate_daily_report.py]
   └─ Analyze yesterday's accuracy
   └─ Show today's schedule & predictions
   └─ Display model insights
```

## Running the Workflow

### Manual Execution

**Run full workflow:**
```bash
python scripts/daily_workflow.py
```

**Run with specific steps skipped:**
```bash
python scripts/daily_workflow.py --skip-api --skip-metrics
```

**Skip options:**
- `--skip-api` - Skip API sync (use cached data)
- `--skip-metrics` - Skip metrics calculation
- `--skip-predictions` - Skip prediction generation
- `--skip-accuracy` - Skip accuracy analysis

### Automated Scheduling

**Setup automatic daily updates:**

1. Install the schedule library:
```bash
pip install schedule
```

2. Start the scheduler:
```bash
python scripts/schedule_daily_tasks.py
```

3. Run in background with nohup:
```bash
nohup python scripts/schedule_daily_tasks.py > logs/scheduler.log 2>&1 &
```

4. Run in background with screen:
```bash
screen -S nba_scheduler -d -m python scripts/schedule_daily_tasks.py
```

**Default Schedule (EST):**
- **03:00** - Sync games from API
- **03:30** - Calculate team metrics
- **04:00** - Generate predictions
- **04:30** - Generate daily report

## Individual Scripts

### 1. reload_clean_from_api.py
**Purpose:** Sync new games from Ball Don't Lie API

**What it does:**
- Fetches latest games by season
- Validates data integrity
- Stores games in database

**Usage:**
```bash
python scripts/reload_clean_from_api.py
python scripts/reload_clean_from_api.py --start-season 2019 --end-season 2025
```

**Time:** ~30-60 seconds

---

### 2. calculate_metrics.py
**Purpose:** Calculate team stats using walk-forward methodology

**What it does:**
- Computes stats using only **prior games** (prevents data leakage)
- Calculates ELO ratings before each game
- Computes PPF, PPA, pace, efficiency metrics
- Updates team_game_stats table

**Key Features:**
- Walk-forward evaluation prevents information leakage
- ELO ratings updated after each game (K=32, initial=1500)
- All metrics calculated using only historical data

**Usage:**
```bash
python scripts/calculate_metrics.py
```

**Time:** ~1-2 minutes

---

### 3. generate_game_predictions.py
**Purpose:** Generate predictions for all games

**What it does:**
- Trains GradientBoosting regression model for point differential
- Calculates LightGBM win probabilities
- Calculates ELO-based win probabilities
- Blends: 70% LightGBM + 30% ELO
- Stores predictions in game_predictions table

**Blend Formula:**
```
home_win_prob = 0.70 * lightgbm_prob + 0.30 * elo_prob
point_diff = gradient_boosting_regression(features)
```

**Model Performance:**
- Win prediction accuracy: 71.4% (overall)
- Point differential MAE: 7.15 points
- High confidence (≥65%) accuracy: 90.6%

**Usage:**
```bash
python scripts/generate_game_predictions.py
```

**Time:** ~3-5 minutes

---

### 4. generate_daily_report.py
**Purpose:** Generate daily performance report

**What it does:**
- Analyzes yesterday's prediction accuracy
- Shows today's schedule with predictions
- Displays model insights and diagnostics

**Report Sections:**
1. **Yesterday's Performance**
   - Win prediction accuracy
   - Point differential error analysis
   - Game-by-game breakdown

2. **Today's Games**
   - Scheduled games
   - Home win probabilities
   - Point differential predictions

3. **Model Insights**
   - Accuracy by confidence level
   - Point differential accuracy distribution
   - Component model comparison (LightGBM vs ELO)

**Usage:**
```bash
python scripts/generate_daily_report.py
```

**Time:** ~30-60 seconds

---

### 5. analyze_prediction_accuracy.py
**Purpose:** Detailed accuracy analysis (called by daily_workflow.py)

**What it does:**
- Win probability calibration analysis (5% buckets)
- Point differential error distribution
- Direction accuracy (correct winner prediction)
- Component model comparison

**Analysis Metrics:**
- Expected Calibration Error (ECE)
- Brier Score
- Accuracy at various probability thresholds
- Error magnitude distribution

**Usage:**
```bash
python scripts/analyze_prediction_accuracy.py
```

---

## Database Schema

### game_predictions Table
```sql
CREATE TABLE game_predictions (
    id INTEGER PRIMARY KEY,
    game_id INTEGER NOT NULL UNIQUE,
    home_win_prob FLOAT NOT NULL,
    away_win_prob FLOAT NOT NULL,
    point_differential FLOAT NOT NULL,
    lightgbm_home_prob FLOAT,
    elo_home_prob FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (game_id) REFERENCES games(id)
);
```

### Team Metrics (team_game_stats)
Contains pre-game metrics for each team in each game:
- ELO rating
- PPF (Points For), PPA (Points Allowed)
- Pace
- Efficiency metrics
- Recent game averages

## Error Handling

The workflow includes robust error handling:

1. **API Sync Failures**
   - Continues with cached data if API sync fails
   - Logs all errors

2. **Metrics Calculation Failures**
   - Logs errors but continues to next step
   - Non-critical for prediction generation

3. **Prediction Generation Failures**
   - Critical step - workflow fails if this step fails
   - Ensures predictions are always up-to-date

4. **Accuracy Analysis Failures**
   - Non-critical for workflow
   - Helps diagnose model performance issues

## Monitoring

### Log Files
All scripts create timestamped log files in the `logs/` directory:
- `daily_workflow_*.log` - Main workflow orchestration
- `prediction_accuracy_*.log` - Accuracy analysis
- `daily_report_*.log` - Report generation
- `scheduler.log` - Scheduler daemon (rotates daily)

### View Latest Logs
```bash
tail -f logs/daily_workflow_*.log
tail -f logs/scheduler.log
```

### Check Scheduler Status
```bash
ps aux | grep schedule_daily_tasks.py
pgrep -f "schedule_daily_tasks.py"
```

## Model Performance Summary

| Metric | Value |
|--------|-------|
| Win Prediction Accuracy | 71.4% |
| High Confidence Accuracy (≥65%) | 90.6% |
| Point Differential MAE | 7.15 points |
| Points Within 5 Points | 45.9% |
| Points Within 10 Points | 75.3% |
| Correct Winner Prediction | 82.0% |

## Calibration Analysis

### Win Probability Buckets (45%-100%)
| Bucket | Games | Pred Avg | Actual % | Accuracy |
|--------|-------|----------|----------|----------|
| 45-50% | 889 | 47.6% | 38.0% | 62.0% |
| 50-55% | 1,064 | 52.5% | 50.3% | 50.3% |
| 55-60% | 1,131 | 57.5% | 64.8% | 64.8% |
| 60-65% | 1,143 | 62.4% | 78.0% | 78.0% |
| 65-70% | 911 | 67.3% | 87.2% | 87.2% |
| 70-75% | 543 | 72.2% | 94.5% | 94.5% |
| 75-80% | 163 | 76.6% | 96.9% | 96.9% |

**Key Insight:** Model is well-calibrated in 55-80% range, conservative in 45-55% range.

## Troubleshooting

### Scheduler Not Running
```bash
# Check if process is running
ps aux | grep schedule_daily_tasks.py

# Check logs
tail -f logs/scheduler.log

# Restart scheduler
python scripts/schedule_daily_tasks.py
```

### API Sync Failures
- Check internet connection
- Verify Ball Don't Lie API token in .env
- Check API rate limits

### Metrics Calculation Issues
- Ensure database is running and accessible
- Check PostgreSQL connection in .env
- Verify all required tables exist

### Memory Issues
- Large datasets may require more memory
- Monitor with: `watch -n 1 'free -h'`
- Increase available system memory or run during off-peak hours

## Next Steps for Production

1. **Configure Cron Job** (Alternative to Python scheduler)
   ```bash
   # Add to crontab -e
   0 3 * * * cd /path/to/project && source .venv/bin/activate && python scripts/daily_workflow.py
   ```

2. **Add Email Alerts**
   - Modify daily_workflow.py to email reports
   - Send alerts on critical failures

3. **Add Slack Integration**
   - Post daily reports to Slack channel
   - Alert on model performance changes

4. **Retrain Model Weekly**
   - Add weekly script to retrain LightGBM model
   - Add weekly script to recalibrate blending weights

5. **Dashboard**
   - Build web dashboard showing predictions
   - Display accuracy trends over time
   - Compare vs sportsbooks

## Questions?

Refer to individual script comments and docstrings for more details.
