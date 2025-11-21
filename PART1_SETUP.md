# Part 1: Data Collection & Database Population - Setup Guide

This guide walks you through setting up and running the data collection pipeline to load all NBA games from 2019 onwards into PostgreSQL.

## Prerequisites

- Python 3.9+
- PostgreSQL 12+ (with a database named `nba_2x2x2`)
- BALLDONTLIE API key (provided)

## Setup Steps

### 1. Install Dependencies

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model

# Activate virtual environment
source .venv/bin/activate

# Install core dependencies
pip install -r requirements-core.txt
```

### 2. Configure Database Connection

Edit the `.env` file with your PostgreSQL credentials:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nba_2x2x2
DB_USER=postgres
DB_PASSWORD=your_password_here
```

Your API key is already configured in `.env`:
```
BALLDONTLIE_API_KEY=b6b19d37-1aac-4cca-b56d-aa3b23b2601f
```

### 3. Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create the database
CREATE DATABASE nba_2x2x2;

# Exit psql
\q
```

### 4. Initialize Database Schema

This creates the `teams` and `games` tables with proper constraints and indexes:

```bash
python scripts/init_db.py
```

Expected output:
```
INFO | nba_2x2x2.data.database - Connected to PostgreSQL: postgres@localhost:5432/nba_2x2x2
INFO | nba_2x2x2.data.database - Disconnected from PostgreSQL
Database initialization completed successfully!
Tables created: teams, games
```

### 5. Load NBA Data from API

Run the main data loading script to fetch all games from 2019 onwards:

```bash
python scripts/reload_clean_from_api.py
```

Or specify custom season range:

```bash
# Load only 2023-2024 season
python scripts/reload_clean_from_api.py --start-season 2023

# Load 2020-2023
python scripts/reload_clean_from_api.py --start-season 2020 --end-season 2023
```

## Expected Output

The script logs detailed progress:

```
================================================================================
NBA Data Loader - BALLDONTLIE API
================================================================================
Start season: 2019
End season: Current
================================================================================

================================================================================
PHASE 1: Loading Teams
================================================================================
INFO | nba_2x2x2.data.data.etl - Loading teams from BALLDONTLIE API...
INFO | nba_2x2x2.data.data.etl - Fetched 30 teams from API
INFO | nba_2x2x2.data.data.etl - Teams: 30 new, 0 updated

================================================================================
PHASE 2: Loading Games
================================================================================
INFO | nba_2x2x2.data.data.etl - Loading games from season 2019 onwards...
INFO | nba_2x2x2.data.data.etl - Fetching all games for season 2019...
INFO | nba_2x2x2.data.data.etl - Fetched page 1: 100 games (total: 100)
...
```

The script will:
1. Fetch all 30 NBA teams and insert/update them
2. Fetch all games for each season (2019, 2020, ..., current)
3. Insert new games or update existing ones if scores/status changed
4. Validate data integrity
5. Print summary statistics per season

## Database Schema

### teams table
```sql
id INTEGER PRIMARY KEY
abbreviation VARCHAR(3) UNIQUE -- e.g., 'LAL', 'BOS'
city VARCHAR(50)               -- e.g., 'Los Angeles', 'Boston'
conference VARCHAR(10)         -- 'EAST' or 'WEST'
division VARCHAR(20)           -- e.g., 'Pacific', 'Atlantic'
full_name VARCHAR(100)         -- e.g., 'Los Angeles Lakers'
name VARCHAR(50)               -- e.g., 'Lakers'
created_at TIMESTAMP
updated_at TIMESTAMP
```

### games table
```sql
id INTEGER PRIMARY KEY
home_team_id INTEGER FOREIGN KEY  -- Reference to teams.id
away_team_id INTEGER FOREIGN KEY  -- Reference to teams.id
home_team_score INTEGER           -- Final/current score
away_team_score INTEGER           -- Final/current score
game_date DATE                    -- Game date (indexed)
game_datetime TIMESTAMP           -- Full datetime
season INTEGER                    -- Season year (indexed, e.g., 2023)
status VARCHAR(20)                -- 'scheduled', 'in_progress', 'final'
period INTEGER                    -- Current period (if in_progress)
time VARCHAR(10)                  -- Time remaining (if in_progress)
postseason INTEGER                -- 0 for regular season, 1 for postseason
created_at TIMESTAMP
updated_at TIMESTAMP

UNIQUE CONSTRAINT: (home_team_id, away_team_id, game_date)
```

## Verification

After loading data, verify it in PostgreSQL:

```bash
psql -U postgres -d nba_2x2x2

# Count teams
SELECT COUNT(*) FROM teams;
-- Expected: 30

# Count all games
SELECT COUNT(*) FROM games;
-- Expected: 1500+ (varies by current season)

# Count games with scores (completed)
SELECT COUNT(*) FROM games WHERE home_team_score IS NOT NULL;

# Sample recent games
SELECT away_team_id, home_team_id, game_date, away_team_score, home_team_score
FROM games
WHERE game_date > '2024-01-01'
LIMIT 5;

# Games by season
SELECT season, COUNT(*) as total_games
FROM games
GROUP BY season
ORDER BY season;
```

## Troubleshooting

### API Rate Limiting
If you see `429 Too Many Requests`, the script includes automatic backoff and retry logic. It will wait and retry automatically.

### Database Connection Error
```
psycopg2.OperationalError: could not connect to server
```

Check your `.env` file DB_HOST, DB_PORT, DB_USER, and DB_PASSWORD. Verify PostgreSQL is running:
```bash
psql -U postgres -c "SELECT 1"
```

### Table Already Exists
If you run `init_db.py` twice, it's safe - SQLAlchemy won't recreate tables.

### Partial Data Load
If the script stops partway:
1. The `.env` and script automatically track which page it was on
2. Simply run `reload_clean_from_api.py` again - it will skip existing games and update completed games with scores

## Next Steps

Once Part 1 is complete:
- **Part 2**: Calculate metrics and features (rolling stats, ELO, differentials)
- **Part 3**: Train LightGBM model and build ELO predictor
- **Part 4**: Set up evaluation metrics and analysis
- **Part 5**: Implement daily automation pipeline
- **Part 6**: Build Streamlit and REST API frontends

## Logging

All runs are logged to `logs/nba_loader_YYYYMMDD_HHMMSS.log` with full debug information. Check these files if you need to diagnose issues.

## Performance Notes

Loading all games from 2019-2024 typically takes:
- **10-15 minutes** with default rate limiting
- Respects BALLDONTLIE API rate limits (approx 120 req/minute)
- Database insertions are batched for efficiency
