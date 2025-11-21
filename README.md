# 2x2x2 NBA Predictive Model

A comprehensive NBA game outcome prediction system combining LightGBM machine learning and ELO ratings for accurate game predictions, calibrated confidence scores, and historical performance analysis.

## Project Structure

```
2x2x2-nba-predictive-model/
├── src/nba_2x2x2/
│   ├── data/              # API integration, ETL, database loading
│   ├── features/          # Metric & feature engineering (ELO, rolling stats)
│   ├── models/            # LightGBM, ELO, blended predictor, walk-forward engine
│   ├── evaluation/        # Accuracy, log loss, Brier, AUC, calibration metrics
│   ├── pipeline/          # Daily update & orchestration
│   ├── api/               # Flask REST API
│   └── frontend/          # Streamlit + static HTML/JS
├── scripts/               # CLI-style entrypoints
├── tests/                 # Unit and integration tests
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
└── README.md
```

## 6 Major Parts

### Part 1: Data Collection & Database Population
- BALLDONTLIE NBA API integration
- Loading teams and games into PostgreSQL
- Initial ETL and data validation
- Scripts: `reload_clean_from_api.py`

### Part 2: Metric & Feature Calculation
- Rolling averages and differentials
- ELO rating system
- Team game stats population
- Feature engineering for model training

### Part 3: Predictive Modeling (LightGBM + ELO + Ensemble)
- LightGBM model training and persistence
- ELO system maintenance
- 70/30 blended predictor
- Walk-forward validation and calibration

### Part 4: Results Analysis & Historical Evaluation
- REST endpoints for prediction queries
- Accuracy, log loss, Brier, AUC metrics
- Confidence-bucket performance analysis
- Historical archives and advanced queries

### Part 5: Daily Update & Automation Pipeline
- Nightly game sync
- Metric recalculation and ELO updates
- Prediction generation for upcoming games
- Logging, error handling, and scheduling (Prefect/cron)

### Part 6: Frontends & User Interfaces
- Streamlit dashboard (Today's Picks, Game Details, Historical Archive, Model Performance, Kelly)
- HTML/JS frontend (REST API integration)
- Direct REST API access for integrations

## Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- BALLDONTLIE API key (free at https://balldontlie.io)

### Installation

1. Clone/navigate to the repository:
   ```bash
   cd /Users/michaelstrong/2x2x2-nba-predictive-model
   ```

2. Create and activate virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment:
   ```bash
   cp .env.example .env
   # Edit .env with your PostgreSQL and BALLDONTLIE credentials
   ```

5. Initialize database (when Part 1 is complete):
   ```bash
   python scripts/init_db.py
   ```

## Current Status

**Part 1 (Data Collection & Database Population)**: In progress
- Project structure initialized
- Database manager created
- BALLDONTLIE API client created
- Ready for ETL script development

## Usage

```python
# Basic usage example (to be expanded in Part 1)
from src.nba_2x2x2.data import DatabaseManager, BallDontLieClient

# Initialize API client
api_client = BallDontLieClient()
teams = api_client.get_teams()

# Initialize database
db = DatabaseManager()
db.connect()
session = db.get_session()
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/ scripts/ tests/
flake8 src/ scripts/ tests/
```

### Type Checking
```bash
mypy src/
```

## License

TBD

## Contact

Created for NBA game prediction and analysis.
