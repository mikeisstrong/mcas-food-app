# Remaining Work: Test Suite & Rate Limiting

**Overall Progress:** 55% Complete
**Time Invested:** ~4-5 hours
**Remaining Effort:** ~9-18 hours
**Target Completion:** 1-2 weeks

---

## REMAINING HIGH-PRIORITY WORK

### HP4: Comprehensive Test Suite (8-16 hours)

**Current Status:** NOT STARTED
**Priority:** CRITICAL - No regression detection
**Approach:** 3-phase implementation

#### Phase 1: Test Infrastructure (2-3 hours)

**Files to Create:**
- `tests/__init__.py` - Package marker
- `tests/conftest.py` - Pytest fixtures and database setup

**Key Fixtures Needed:**
1. Database fixtures:
   - `test_db_session` - In-memory SQLite for tests
   - `test_db_manager` - DatabaseManager instance
   - `cleanup_db` - Teardown and cleanup

2. Data fixtures:
   - `sample_teams` - Create 3-5 test NBA teams
   - `sample_games` - Create games with known outcomes
   - `sample_predictions` - Create predictions for testing

3. Client fixtures:
   - `api_client` - Test FastAPI client
   - `mock_balldontlie_client` - Mocked external API

**Example conftest.py structure:**
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="function")
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    # Create tables
    # Yield session
    # Cleanup

@pytest.fixture
def sample_teams(test_db):
    """Create test NBA teams."""
    teams = [
        Team(abbreviation="BOS", full_name="Boston Celtics"),
        Team(abbreviation="LAL", full_name="Los Angeles Lakers"),
        # ...
    ]
    return teams

@pytest.fixture
def api_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from api.main import app
    return TestClient(app)
```

#### Phase 2: Unit Tests (4-6 hours)

**Files to Create:**
- `tests/test_metrics.py` - MetricsCalculator tests
- `tests/test_features.py` - FeatureEngineer tests
- `tests/test_models.py` - GamePredictor tests
- `tests/test_api.py` - API endpoint tests

**Test Coverage Targets:**

**1. `test_metrics.py` - MetricsCalculator (15-20 tests)**
```python
# Tests needed:
def test_elo_initialization():
    """Verify teams start with ELO 1500."""

def test_elo_calculation_formula():
    """Test ELO calculation is correct."""

def test_walk_forward_no_leakage():
    """CRITICAL: Ensure no future games used in past predictions."""

def test_rolling_average_calculation():
    """Verify 5, 10, 20-game rolling averages."""

def test_rest_days_calculation():
    """Test rest day counting between games."""

def test_back_to_back_detection():
    """Verify back-to-back flag accuracy."""

def test_metrics_chronological_order():
    """Ensure metrics calculated in game date order."""

def test_null_handling():
    """Test handling of missing/null metrics."""
```

**2. `test_features.py` - FeatureEngineer (15-20 tests)**
```python
def test_feature_count():
    """Verify exactly 38 features extracted."""

def test_no_future_data_leakage():
    """CRITICAL: Verify only pre-game stats used."""

def test_feature_scaling_reasonable():
    """Ensure features are in reasonable ranges."""

def test_null_feature_handling():
    """Test None value handling in features."""

def test_interaction_features_calculated():
    """Verify difference features computed correctly."""

def test_feature_consistency():
    """Same game produces same features each time."""

def test_early_season_games():
    """Verify handling of early games with few rolling avgs."""

def test_feature_engineering_preserves_order():
    """Ensure game ordering preserved in output."""
```

**3. `test_models.py` - GamePredictor (15-20 tests)**
```python
def test_lightgbm_training():
    """Verify LightGBM model trains without error."""

def test_lightgbm_prediction_range():
    """Predictions should be [0, 1] probabilities."""

def test_model_persistence():
    """Can save and load model from disk."""

def test_time_based_split_no_leakage():
    """Verify train/test split is temporal."""

def test_feature_importance_extraction():
    """Feature importance can be extracted."""

def test_model_prediction_consistency():
    """Same input produces same prediction."""

def test_early_stopping_activates():
    """Verify early stopping prevents overfitting."""

def test_accuracy_metrics_computed():
    """Accuracy, AUC, precision, recall calculated."""
```

**4. `test_api.py` - API Endpoints (20-30 tests)**
```python
def test_daily_report_endpoint():
    """GET /api/report/daily returns data."""

def test_daily_report_date_filtering():
    """Can query specific date."""

def test_daily_report_invalid_date():
    """Invalid date returns 400 error."""

def test_games_list_pagination():
    """Pagination works correctly."""

def test_games_list_filtering_by_date():
    """Date range filtering works."""

def test_games_list_filtering_by_confidence():
    """Confidence filtering works."""

def test_metrics_summary_endpoint():
    """GET /api/metrics/summary returns metrics."""

def test_season_projections_endpoint():
    """GET /api/projections/season returns 30 teams."""

def test_cors_headers_present():
    """CORS headers in responses."""

def test_cors_options_rejected():
    """DELETE/PATCH methods rejected by CORS."""

def test_api_response_format():
    """API responses match expected schema."""

def test_error_responses_format():
    """Error responses have proper format."""

def test_performance_no_n_plus_one():
    """Verify query count is reasonable (< 10 queries)."""
```

#### Phase 3: Integration Tests (2-3 hours)

**Files to Create:**
- `tests/test_integration_etl.py` - ETL pipeline tests
- `tests/test_integration_api.py` - Full API flow tests

**Integration Tests:**
```python
def test_full_etl_pipeline():
    """End-to-end: API sync -> metrics -> predictions."""

def test_prediction_generation_pipeline():
    """Full prediction workflow."""

def test_api_with_real_data():
    """API endpoints with actual database data."""

def test_concurrent_api_requests():
    """Handle multiple simultaneous requests."""

def test_database_connection_pooling():
    """Verify connection pool works correctly."""
```

---

### MP3: API Rate Limiting (1-2 hours)

**Status:** NOT STARTED
**Priority:** MEDIUM - Prevents abuse

**Implementation Steps:**

1. **Install slowapi:**
```bash
pip install slowapi
```

2. **Update requirements.txt:**
```
slowapi==0.1.9
```

3. **Implement rate limiting in api/main.py:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Apply global limit
@app.get("/api/games")
@limiter.limit("60/minute")
def get_games(...):
    pass

# Or apply to app
app.include_middleware(middleware_class)
```

4. **Configuration via environment:**
```bash
# .env
API_RATE_LIMIT_PER_MINUTE=60
API_RATE_LIMIT_BURST=10
```

5. **Endpoints to protect:**
- `GET /api/report/daily` - 60/minute
- `GET /api/games` - 60/minute
- `GET /api/metrics/summary` - 30/minute (heavier query)
- `GET /api/projections/season` - 20/minute (heavier query)

---

## WORK BREAKDOWN STRUCTURE

### Phase 1: Infrastructure (Week 1, Days 1-2)
- [ ] Create `tests/` directory structure
- [ ] Create `tests/conftest.py` with database fixtures
- [ ] Create sample team and game data
- [ ] Create API test client fixture
- [ ] Verify fixtures work with pytest

**Deliverable:** Working test infrastructure with 5+ fixtures

### Phase 2: Unit Tests (Week 1, Days 3-5)
- [ ] Write metrics tests (15-20 tests)
- [ ] Write features tests (15-20 tests)
- [ ] Write models tests (15-20 tests)
- [ ] Write API tests (20-30 tests)
- [ ] Aim for 70%+ coverage

**Deliverable:** 65-90 unit tests, 70%+ code coverage

### Phase 3: Integration & Rate Limiting (Week 2, Days 1-2)
- [ ] Write ETL integration tests
- [ ] Write API integration tests
- [ ] Install slowapi library
- [ ] Implement rate limiting middleware
- [ ] Configure per-endpoint limits
- [ ] Test rate limit behavior

**Deliverable:** 10+ integration tests, working rate limiter

### Phase 4: CI/CD & Documentation (Week 2, Days 3-4)
- [ ] Create GitHub Actions workflow
- [ ] Run tests on every push
- [ ] Generate coverage reports
- [ ] Update README with testing info
- [ ] Document test running locally

**Deliverable:** Automated testing pipeline

---

## TEST EXECUTION

### Run All Tests
```bash
pytest tests/ -v --tb=short
```

### Run Specific Test Module
```bash
pytest tests/test_api.py -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html
```

### Run Tests in Watch Mode (auto-rerun on changes)
```bash
pytest-watch tests/
```

---

## SUCCESS CRITERIA

**HP4 Phase 1 Complete When:**
- [ ] conftest.py has 5+ working fixtures
- [ ] Database fixtures create and teardown properly
- [ ] Sample data fixtures return valid objects
- [ ] API test client can be instantiated
- [ ] At least 1 sample test passes

**HP4 Phase 2 Complete When:**
- [ ] 65+ unit tests written
- [ ] 70%+ code coverage achieved
- [ ] All critical paths tested (walk-forward, features, API)
- [ ] All tests pass
- [ ] No warnings or deprecations

**HP4 Phase 3 Complete When:**
- [ ] 10+ integration tests written
- [ ] Rate limiting installed and working
- [ ] Per-endpoint limits enforced
- [ ] Rate limit headers returned
- [ ] All tests pass

**MP3 Complete When:**
- [ ] Slowapi installed
- [ ] Rate limiter configured
- [ ] 4 main endpoints protected
- [ ] Rate limits configurable via .env
- [ ] Exceeded limits return 429 Too Many Requests

---

## ESTIMATED TIMELINE

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| HP4 Phase 1 | 2-3 hrs | Day 1 | Day 2 | ⏳ TODO |
| HP4 Phase 2 | 4-6 hrs | Day 2 | Day 4 | ⏳ TODO |
| HP4 Phase 3 | 2-3 hrs | Day 5 | Day 6 | ⏳ TODO |
| MP3 Rate Limiting | 1-2 hrs | Day 6 | Day 7 | ⏳ TODO |
| **TOTAL** | **9-14 hrs** | **Day 1** | **Day 7** | **⏳ TODO** |

---

## CRITICAL TESTS

These tests MUST pass before production deployment:

1. **`test_walk_forward_no_leakage`** (metrics)
   - Ensures model never sees future data
   - Most important test for model validity

2. **`test_no_future_data_leakage`** (features)
   - Verifies features only use pre-game stats
   - Critical for realistic accuracy

3. **`test_time_based_split_no_leakage`** (models)
   - Confirms train/test temporal split
   - Validates evaluation methodology

4. **`test_api_response_format`** (API)
   - Ensures API contracts are maintained
   - Critical for frontend compatibility

---

## RESOURCES

**Testing Libraries Already Installed:**
- pytest==7.4.3
- pytest-cov (install: `pip install pytest-cov`)

**Recommended Additional Tools:**
- pytest-watch: `pip install pytest-watch`
- pytest-benchmark: `pip install pytest-benchmark`
- responses (mock HTTP): `pip install responses`

**Testing Documentation:**
- [Pytest Official Docs](https://docs.pytest.org/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/faq/testing.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-databases/)

---

## NOTES

- Tests should be independent (no shared state between tests)
- Use fixtures to manage setup/teardown
- Mock external APIs (Ball Don't Lie) in tests
- In-memory SQLite for fast test database
- Aim for at least 70% code coverage (80%+ for critical modules)
- Test both happy path and error cases

