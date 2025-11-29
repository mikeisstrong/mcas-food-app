# Complete Setup and Run Guide

## Quick Start (5 minutes)

### 1. Create Virtual Environment
```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies (Working Version)
```bash
pip install -r requirements-working.txt
```

### 3. Create `.env` File
```bash
cp .env.example .env
```

Edit `.env` with your database credentials:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nba_2x2x2
DB_USER=postgres
DB_PASSWORD=your_password
BALLDONTLIE_API_KEY=your_api_key
```

### 4. Start the API
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Visit: **http://localhost:8000/docs** (Swagger UI)

---

## Detailed Setup Instructions

### Prerequisites

- **Python 3.13+**
- **PostgreSQL 12+** (running locally or accessible)
- **Git** (optional, for version control)

### Step 1: Clone/Navigate to Project

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model
```

### Step 2: Create Virtual Environment

Create isolated Python environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

You should see `(.venv)` prefix in your terminal.

### Step 3: Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### Step 4: Install Dependencies

Use the **working requirements file** (avoids scikit-learn compilation issues):

```bash
pip install -r requirements-working.txt
```

**Why `requirements-working.txt` instead of `requirements.txt`?**
- `requirements.txt` has strict versions that cause compilation errors on macOS M1/M2
- `requirements-working.txt` uses pre-built wheels for faster installation
- All packages are compatible and tested

### Step 5: Configure Environment Variables

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nba_2x2x2
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_SSL_MODE=disable

# BALLDONTLIE API
BALLDONTLIE_API_KEY=your_api_key_here
API_RATE_LIMIT_DELAY=1.0

# Logging
LOG_LEVEL=INFO

# API Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
API_RATE_LIMIT_PER_MINUTE=60
```

### Step 6: Ensure PostgreSQL is Running

**On macOS with Homebrew:**

```bash
# Start PostgreSQL
brew services start postgresql

# Verify it's running
psql -U postgres -h localhost -d postgres -c "SELECT 1"
```

**On macOS with Docker:**

```bash
docker run --name postgres -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres
```

### Step 7: Create Database (First Time Only)

```bash
psql -U postgres -h localhost -c "CREATE DATABASE nba_2x2x2;"
```

Verify:

```bash
psql -U postgres -h localhost -d nba_2x2x2 -c "SELECT 1"
```

### Step 8: Initialize Database Schema

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from nba_2x2x2.data.database import DatabaseManager
from nba_2x2x2.data.models import Base

db = DatabaseManager()
db.connect()
Base.metadata.create_all(bind=db.engine)
print('✅ Database schema created successfully')
db.disconnect()
"
```

---

## Running the API

### Option A: Development Mode (with auto-reload)

```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Option B: Production Mode (no auto-reload)

```bash
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option C: Using Python directly

```bash
source .venv/bin/activate
python api/main.py
```

---

## Accessing the API

### 1. Swagger UI Documentation

**URL:** http://localhost:8000/docs

Browse all endpoints, view schemas, test requests interactively

### 2. ReDoc Documentation

**URL:** http://localhost:8000/redoc

Alternative documentation viewer

### 3. OpenAPI Schema

**URL:** http://localhost:8000/openapi.json

Raw OpenAPI specification (for code generation, etc.)

---

## Testing the API

### Test 1: Check Health

```bash
curl http://localhost:8000/docs
```

Should return Swagger UI (HTTP 200)

### Test 2: Get Daily Report

```bash
curl "http://localhost:8000/api/report/daily"
```

Response (example):
```json
{
  "query_date": "2025-11-22",
  "yesterday": {
    "date": "2025-11-21",
    "games": [],
    "accuracy": 0,
    "accuracy_by_confidence": {"High": {"correct": 0, "total": 0}, ...}
  },
  "today": {
    "date": "2025-11-22",
    "games": []
  },
  "summary_metrics": {...},
  "timestamp": "2025-11-22T15:00:00Z"
}
```

### Test 3: With Invalid Date (should return 400)

```bash
curl "http://localhost:8000/api/report/daily?query_date=invalid"
```

Response:
```json
{
  "detail": "Invalid date format. Use YYYY-MM-DD (e.g., 2025-11-22)"
}
```

### Test 4: Games List

```bash
curl "http://localhost:8000/api/games?limit=10"
```

### Test 5: CORS Security Check

```bash
curl -X DELETE http://localhost:8000/api/games
```

Should return CORS error (DELETE not allowed)

---

## Data Setup

### Option 1: Load Sample Data (Recommended)

```bash
python scripts/reload_clean_from_api.py
python scripts/calculate_metrics.py
python scripts/train_models.py
python scripts/generate_game_predictions.py
```

### Option 2: Manual Data Population

See `scripts/` directory for individual data loading scripts

---

## Troubleshooting

### Issue: "No module named 'sqlalchemy'"

**Solution:**
```bash
pip install sqlalchemy==2.0.44
```

### Issue: "psycopg2: Can't connect to PostgreSQL"

**Check:**
1. PostgreSQL is running: `psql -U postgres -h localhost -c "SELECT 1"`
2. Database exists: `psql -U postgres -h localhost -d nba_2x2x2 -c "SELECT 1"`
3. `.env` has correct credentials

### Issue: "Port 8000 already in use"

**Solution:**
```bash
# Use different port
uvicorn api.main:app --reload --port 8001
```

### Issue: "DeprecationWarning about on_event"

**Status:** Harmless warning - FastAPI suggests upgrading to lifespan events (feature coming in next update)

### Issue: "scikit-learn compilation error"

**Solution:** Use `requirements-working.txt` instead of `requirements.txt`
```bash
pip uninstall scikit-learn
pip install -r requirements-working.txt
```

---

## Directory Structure

```
.
├── api/                          # FastAPI backend
│   ├── main.py                  # API application
│   └── requirements.txt
│
├── src/nba_2x2x2/              # Python package
│   ├── config.py                # Configuration management
│   ├── data/                    # Data layer
│   │   ├── database.py
│   │   ├── api_client.py
│   │   ├── models.py
│   │   ├── metrics.py
│   │   └── etl.py
│   └── ml/                      # Machine learning
│       ├── features.py
│       └── models.py
│
├── scripts/                      # CLI entry points
│   ├── reload_clean_from_api.py
│   ├── calculate_metrics.py
│   ├── train_models.py
│   ├── generate_game_predictions.py
│   └── ...
│
├── models/                       # Saved model artifacts
│   ├── lightgbm_model.pkl
│   └── point_diff_model.pkl
│
├── .env                          # Environment variables (local)
├── .env.example                  # Environment template
├── requirements.txt              # Strict versions (may have issues)
├── requirements-working.txt      # Recommended - tested versions
└── README.md
```

---

## Common Commands

### Activate Virtual Environment
```bash
source .venv/bin/activate
```

### Install/Update Dependencies
```bash
pip install -r requirements-working.txt
pip install --upgrade -r requirements-working.txt
```

### Run API Server
```bash
uvicorn api.main:app --reload
```

### Run Tests (when available)
```bash
pytest tests/ -v
```

### Format Code
```bash
black src/ api/
```

### Lint Code
```bash
flake8 src/ api/
```

### Type Check
```bash
mypy src/ api/
```

### Deactivate Virtual Environment
```bash
deactivate
```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/docs` | Swagger UI Documentation |
| GET | `/redoc` | ReDoc Documentation |
| GET | `/openapi.json` | OpenAPI Schema |
| GET | `/api/report/daily` | Daily report (yesterday + today) |
| GET | `/api/games` | Game history with pagination |
| GET | `/api/metrics/summary` | Aggregated metrics |
| GET | `/api/projections/season` | Season win projections |

---

## Next Steps

1. **Start the API** and access `/docs`
2. **Load sample data** using scripts in `scripts/`
3. **Test endpoints** using Swagger UI
4. **Build frontend** (React at `frontend/`)
5. **Deploy to production** when ready

---

## Documentation

- `FORENSIC_CODE_REVIEW.md` - Detailed security audit and findings
- `IMPROVEMENTS_COMPLETED.md` - Summary of recent improvements
- `REMAINING_WORK.md` - Roadmap for test suite and rate limiting
- `IMPLEMENTATION_SUMMARY.txt` - Quick reference of changes made

---

## Support

For issues:
1. Check **Troubleshooting** section above
2. Review API logs (printed to console)
3. Check `.env` configuration
4. Verify PostgreSQL is running

---

**Status:** ✅ Ready to run
**Last Updated:** November 22, 2025
**Python Version:** 3.13+
**API Framework:** FastAPI
**Database:** PostgreSQL 12+

