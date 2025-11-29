# Frontend & Backend Setup Guide

This guide walks through setting up both the FastAPI backend and React frontend for the NBA Prediction Dashboard.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│             React Frontend (Port 5173)                  │
│   ├─ Daily Dashboard                                   │
│   ├─ History & Accuracy                                │
│   └─ Season Projections                                │
└─────────────────────────────────────────────────────────┘
                          ↕️ (Fetch)
┌─────────────────────────────────────────────────────────┐
│            FastAPI Backend (Port 8000)                  │
│   ├─ GET /api/report/daily                             │
│   ├─ GET /api/games                                    │
│   ├─ GET /api/metrics/summary                          │
│   └─ GET /api/projections/season                       │
└─────────────────────────────────────────────────────────┘
                          ↕️ (Query)
┌─────────────────────────────────────────────────────────┐
│          PostgreSQL Database                            │
│   ├─ games (8,797)                                     │
│   ├─ team_game_stats (15,664)                          │
│   ├─ game_predictions (8,797)                          │
│   └─ teams (44)                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Backend Setup (FastAPI)

### 1. Install Dependencies

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model
source .venv/bin/activate
pip install -r api/requirements.txt
```

### 2. Start the API Server

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model
source .venv/bin/activate
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 3. Verify API Endpoints

Test in browser or with curl:

```bash
# Test daily report
curl http://localhost:8000/api/report/daily

# Test games endpoint
curl http://localhost:8000/api/games?skip=0&limit=10

# Test metrics summary
curl http://localhost:8000/api/metrics/summary

# Test season projections
curl http://localhost:8000/api/projections/season?season=2025&basis=blend
```

**Expected Response:**
```json
{
  "query_date": "2025-11-22",
  "yesterday": {...},
  "today": {...},
  "summary_metrics": {...},
  "timestamp": "2025-11-22T10:20:00Z"
}
```

---

## Frontend Setup (React + Vite)

### 1. Install Node.js Dependencies

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model/frontend
npm install
```

This installs:
- React 18.2.0
- Vite 5.0.0 (build tool)
- Tailwind CSS 3.3.0
- Axios 1.6.0

### 2. Start Development Server

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model/frontend
npm run dev
```

**Expected Output:**
```
VITE v5.0.0  ready in 234 ms

➜  Local:   http://localhost:5173/
➜  press h + enter to show help
```

### 3. Open in Browser

Navigate to:
```
http://localhost:5173
```

You should see:
- Top nav bar: "Grey's NBA Model"
- Three tabs: Daily Dashboard, History & Accuracy, Season Projections
- Daily Dashboard loaded by default

---

## Full Stack Startup (Recommended)

### Terminal 1: Backend API

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model
source .venv/bin/activate
python -m uvicorn api.main:app --reload
```

### Terminal 2: Frontend Dev Server

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model/frontend
npm run dev
```

### Terminal 3: Tail logs (optional)

```bash
cd /Users/michaelstrong/2x2x2-nba-predictive-model
tail -f logs/*.log
```

Now both are running:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API proxy: Frontend automatically forwards `/api/*` calls to backend

---

## Testing the Integration

### 1. Daily Dashboard Test

1. Go to http://localhost:5173
2. Should see "Daily Dashboard" tab selected
3. Verify you see:
   - Date selector with date
   - Three metric chips (Yesterday Accuracy, Avg Error, High Conf Accuracy)
   - "Last Night's Results" table
   - "Today's Schedule" table

### 2. History & Accuracy Test

1. Click "History & Accuracy" tab
2. Should see:
   - Date range pickers (Start/End dates)
   - Quick preset buttons (7 days, 30 days, Season to Date)
   - Summary metrics cards
   - Games table with sortable columns
   - Pagination controls

### 3. Season Projections Test

1. Click "Season Projections" tab
2. Should see:
   - Season dropdown (2024-25 selected)
   - Projection basis radio buttons (Blended, ELO, LightGBM)
   - Table with team projections
   - Current record, remaining games, projected wins

### 4. Network Tab Test

1. Open browser DevTools (F12)
2. Go to Network tab
3. Click on any tab or apply filters
4. Should see API calls to `/api/report/daily`, `/api/games`, etc.
5. Response status should be 200

---

## Troubleshooting

### Backend Issues

**Error: "Failed to connect to database"**
```
Solution: Ensure PostgreSQL is running
ps aux | grep postgres
```

**Error: "Port 8000 already in use"**
```
Solution: Kill existing process or use different port
lsof -i :8000
kill -9 <PID>
# Or run on different port:
python -m uvicorn api.main:app --port 8001
```

**Error: "ImportError: No module named 'nba_2x2x2'"**
```
Solution: Ensure .venv is activated and src is in Python path
source .venv/bin/activate
python -c "import sys; print(sys.path)"
```

### Frontend Issues

**Error: "Cannot find module '@vitejs/plugin-react'"**
```
Solution: Re-run npm install
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Error: "API calls returning 404"**
```
Solution: Ensure backend is running on port 8000
Check vite.config.js proxy setting
```

**Port 5173 already in use:**
```
Solution: Kill process or let Vite use different port
lsof -i :5173
kill -9 <PID>
```

---

## Production Build

### Build Frontend

```bash
cd frontend
npm run build
```

Output: `frontend/dist/` folder

### Deploy Backend

```bash
# Using Gunicorn
pip install gunicorn
gunicorn api.main:app --workers 4 --host 0.0.0.0 --port 8000

# Using Docker (recommended)
# Create Dockerfile in api/
docker build -t nba-api .
docker run -p 8000:8000 nba-api
```

### Deploy Frontend

```bash
# Serve dist folder with any static server
cd frontend
npx serve dist

# Or deploy to Vercel, Netlify, etc.
```

---

## Environment Variables

Backend uses variables from `.env`:
```
DATABASE_URL=postgresql://user:pass@localhost:5432/nba_2x2x2
BALL_DONT_LIE_API_TOKEN=your_token
```

Frontend is static - no env vars needed (API proxy is configured in vite.config.js)

---

## API Endpoints Reference

### Daily Report
```
GET /api/report/daily?query_date=2025-11-22
```

Returns: Yesterday's games + today's schedule + summary metrics

### Games List
```
GET /api/games?start_date=2025-11-01&end_date=2025-11-30&confidence=High&skip=0&limit=50
```

Returns: Paginated list of games with predictions and results

### Metrics Summary
```
GET /api/metrics/summary?start_date=2025-11-01&end_date=2025-11-30
```

Returns: Accuracy stats, calibration by confidence, spread error analysis

### Season Projections
```
GET /api/projections/season?season=2025&basis=blend
```

Returns: Projected wins for all teams (basis: blend, lightgbm, elo)

---

## Next Steps

1. **Verify everything works** - Follow testing section above
2. **Customize styling** - Edit tailwind.config.js or src/index.css
3. **Add more endpoints** - Extend api/main.py with additional queries
4. **Deploy** - Use instructions in "Production Build" section
5. **Monitor** - Check logs in api/logs/ and browser console

---

## File Structure

```
2x2x2-nba-predictive-model/
├── api/
│   ├── main.py                 # FastAPI app with all endpoints
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── DailyDashboard.jsx
│   │   │   ├── HistoryAccuracy.jsx
│   │   │   └── SeasonProjections.jsx
│   │   ├── utils/
│   │   │   ├── api.js          # API client functions
│   │   │   └── formatters.js   # Utility formatters
│   │   ├── App.jsx             # Main app with tabs
│   │   ├── main.jsx            # React entry point
│   │   └── index.css           # Tailwind styles
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── index.html
└── scripts/
    ├── daily_workflow.py       # Existing prediction workflow
    ├── generate_daily_report.py
    ├── generate_game_predictions.py
    └── ...
```

---

## Quick Command Reference

```bash
# Start everything
# Terminal 1:
cd /Users/michaelstrong/2x2x2-nba-predictive-model && source .venv/bin/activate && python -m uvicorn api.main:app --reload

# Terminal 2:
cd /Users/michaelstrong/2x2x2-nba-predictive-model/frontend && npm run dev

# Open browser:
http://localhost:5173
```

That's it! You're ready to use the dashboard.
