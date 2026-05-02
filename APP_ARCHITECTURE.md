# F1RacePred Application Architecture

## 📊 App Structure Overview

Your F1RacePred application is a **full-stack machine learning prediction platform** with three main tiers:

```
┌─────────────────────────────────────────────────────────┐
│   UNIFIED SERVER (FastAPI + React Static Files)         │
│  Port: 8000 | Serves both API & frontend                │
│  - React built to: frontend/dist/                       │
│  - Served as static files from /                        │
│  - 20+ REST API endpoints at /api/*                     │
│  - SQLite database (7 tables with sprint tracking)      │
│  - APScheduler (5+ recurring jobs including sprints)    │
│  - Security: X-API-Key auth for admin endpoints         │
└─────────────────────────────────────────────────────────┘
                          ↕ Subprocess calls
┌─────────────────────────────────────────────────────────┐
│    DATA PIPELINE (Python Scripts)                       │
│  - Data collection (FastF1, Ergast APIs)               │
│  - Feature engineering                                  │
│  - XGBoost model training                               │
│  - Prediction generation                                │
│  - Metrics evaluation                                   │
└─────────────────────────────────────────────────────────┘
```

---

## 🎨 FRONTEND ARCHITECTURE

### Core Structure

```
frontend/src/
├── pages/              # 5 route-level page components
│   ├── Home.jsx       # Dashboard landing page (predictions overview)
│   ├── RaceDetail.jsx # Single race with pre/post-quali comparison
│   ├── Drivers.jsx    # Driver profiles & performance stats
│   ├── ModelReport.jsx # Model metrics & accuracy analysis
│   └── Archive.jsx    # Historical races & season leaderboard
│
├── components/        # 10 reusable UI components
│   ├── OracleCard.jsx # Next race prediction card
│   ├── WDCStandings.jsx # Driver championship standings
│   ├── WCCStandings.jsx # Team championship standings
│   ├── ModelSnapshot.jsx # Key metrics display
│   ├── Countdown.jsx  # Race countdown timer
│   ├── ConfidenceMeter.jsx # Confidence visualization
│   ├── DeltaShift.jsx # Position change indicators
│   ├── MissCard.jsx   # Prediction miss analysis
│   ├── SeasonLeaderboard.jsx # Season-wide standings
│   └── WeekendFeed.jsx # Live weekend updates
│
├── hooks/             # Custom React hooks
│   ├── useApi.js      # Data fetching hook (handles loading/errors)
│   └── useCountdown.js # Countdown timer logic
│
├── constants/
│   ├── teamColors.js  # Team color mappings, BASE_URL config
│   └── circuits.js    # SVG circuit layouts
│
├── App.jsx/.tsx       # Main router setup & navigation bar
├── main.tsx           # Entry point
└── index.css          # Global styles
```

### How the Frontend Works

#### 1. Routing (React Router v6 + SPA Catch-All)

```
/              → Home (dashboard)
/race          → RaceDetail (latest race)
/race/:round   → RaceDetail (specific round)
/drivers       → Drivers (performance profiles)
/model         → ModelReport (metrics dashboard)
/archive       → Archive (season history)

Server Configuration:
- /api/*       → Routed to FastAPI endpoints (priority)
- /           → Serves React static files (SPA catch-all)
```

#### 2. Data Fetching Pattern

All components use a custom `useApi()` hook:

```javascript
// In any component:
const { data, loading, error } = useApi('/api/predictions/next');

// The hook:
// - Fetches from BASE_URL (default: http://localhost:8000)
// - Handles loading/error states automatically
// - Cleans up on unmount (prevents memory leaks)
// - Skips fetch if URL is null (conditional fetching)
```

#### 3. API Endpoints Called from Frontend

| Endpoint | Purpose | Called From |
|----------|---------|-------------|
| `/api/calendar` | 2026 race schedule | Home, RaceDetail |
| `/api/status` | Pipeline status | Home, all pages |
| `/api/predictions/next` | Latest race prediction | Home, OracleCard |
| `/api/predictions/{round}/prequali` | Pre-quali scores | RaceDetail |
| `/api/predictions/{round}/postquali` | Post-quali scores | RaceDetail |
| `/api/predictions/{round}/comparison` | Pre vs Post ranking | RaceDetail |
| `/api/standings/drivers` | WDC standings | Home, Drivers |
| `/api/standings/constructors` | WCC standings | Home |
| `/api/race-results` | Actual results | Archive, RaceDetail |
| `/api/metrics` | Model performance | ModelReport |

#### 4. State Management

- **No Redux** — Lightweight approach for MVP
- **Local State**: `useState()` for UI (selected race, timezone, filters)
- **Data State**: Managed by `useApi()` hook
- **URL State**: `useParams()` for route parameters
- **Navigation**: `useNavigate()` for programmatic navigation

#### 5. Styling

- **Inline styles** with shared constants (team colors, themes)
- **Tailwind CSS** for modern grid/flex utilities
- **Dark theme** with F1 red accent (`#E10600`)
- **Team colors**: Ferrari red, Mercedes silver, McLaren orange, etc.

### Frontend Pages

#### Home.jsx (Dashboard)

- Race countdown to next event
- Latest prediction card (pre/post-quali)
- WDC & WCC standings
- Model performance snapshot

#### RaceDetail.jsx (Race Deep Dive)

- Select any completed or upcoming race
- Side-by-side comparison: Pre-quali vs Post-quali vs Actual results
- Position deltas (who moved up/down between qualifying and race)
- Individual driver scores and confidence levels

#### Drivers.jsx (Driver Profiles)

- Per-driver performance metrics
- Hit rate (% in top 3 predictions)
- Accuracy over season
- Confidence visualization

#### ModelReport.jsx (Model Metrics)

- NDCG (ranking quality)
- Top 3 Hit Rate (% correct top 3)
- MAE (mean absolute error in finishing positions)
- Alpha blending analysis (how much to weight pre vs post-quali)

#### Archive.jsx (Historical)

- Season-long leaderboard
- All completed races
- Driver/team historical stats
- Season trends

---

## 🔧 BACKEND API ARCHITECTURE

### Core Structure

```
app/
├── main.py           # Entry point (uvicorn + scheduler setup)
├── api.py            # 18+ FastAPI endpoints
├── database.py       # SQLAlchemy ORM + 6 tables
├── scheduler.py      # APScheduler jobs
├── schemas.py        # Pydantic validation models
└── status.py         # Pipeline status tracking

config/
└── settings.py       # Centralized configuration
```

### Database Schema (7 Tables)

#### PipelineRun - Pipeline execution tracking

```
id, job_name, round, started_at, finished_at, status, rounds_completed, error_message
```

#### PredictionLog - Individual driver predictions

```
id, round, race_name, prediction_type (pre/post), driver_id, constructor_id, 
predicted_pos, final_score, alpha (blending weight), created_at
```

#### SessionData - Practice/qualifying session positions

```
id, round, session, driver_id, position, lap_time, created_at
```

#### RaceResult - Final race results & points (SPRINT-AWARE)

```
id, round, driver_id, final_pos, points, session_type ("R" or "S"), created_at

Key: (round, driver_id, session_type) uniquely identifies each result
- "R" = Main race result
- "S" = Sprint race result (new)
```

#### ModelMetric - Performance metrics per round

```
id, round, top3_hit_rate, ndcg, mae, alpha, created_at
```

#### SessionLog - Sprint-specific ingestion tracking (new)

```
id, round, session_type, drivers_processed, points_distributed, created_at
```

### API Endpoints (18+)

#### Public Endpoints (no API key required)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Landing page (HTML) |
| `/api/calendar` | GET | 2026 race schedule + session times |
| `/api/metrics` | GET | Model performance summary |
| `/api/predictions/next` | GET | Latest race post-quali predictions |
| `/api/predictions/next/prequali` | GET | Latest pre-quali predictions |
| `/api/predictions/next/postquali` | GET | Latest post-quali predictions |
| `/api/predictions/{round}/prequali` | GET | Pre-quali for specific round |
| `/api/predictions/{round}/postquali` | GET | Post-quali for specific round |
| `/api/predictions/{round}/comparison` | GET | Pre vs Post ranking delta |
| `/api/standings/drivers` | GET | WDC standings computed from results (race + sprint) |
| `/api/standings/drivers/sprints` | GET | Driver standings sprint-only (new) |
| `/api/standings/constructors` | GET | WCC standings computed from results (race + sprint) |
| `/api/standings/constructors/sprints` | GET | Constructor standings sprint-only (new) |
| `/api/calendar/sprints` | GET | Sprint races only from 2026 schedule (new) |
| `/api/race-results` | GET | All race results for season (includes sprint rows) |
| `/api/status` | GET | Pipeline status & rounds completed |

#### Admin Endpoints (require `X-API-Key` header)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check if API is alive |
| `/ready` | GET | Check if predictions/metrics available |
| `/api/refresh` | POST | Trigger full pipeline run |
| `/api/refresh/force` | POST | Force pipeline execution |
| `/api/admin/trigger-job/{job_name}` | POST | Trigger specific scheduler job |

### Security Model

**CORS**: Allows all origins (for frontend development flexibility)

**Authentication Levels**:

1. **Public** - No auth required (predictions, calendar, standings, metrics)
2. **Admin** - Requires `X-API-Key` header matching `ADMIN_API_KEY` env var
3. **Middleware** - All requests go through API key guard

```python
# Example admin request:
curl -H "X-API-Key: dev-key" http://localhost:8000/api/refresh
```

### Scheduling (APScheduler)

5+ recurring jobs (disabled by default in Docker):

| Job | When | What | Frequency |
|-----|------|------|----------|
| `run_prequali` | Thursday 12:00 UTC | Pre-quali predictions | Once per weekend |
| `ingest_quali` | Saturday 18:00 UTC | Ingest qualifying results | Once per weekend |
| `ingest_sprint` | Saturday ~17:30 UTC | Ingest sprint results (if sprint race) | If weekend is sprint |
| `run_postquali` | Saturday 18:00 UTC | Post-quali predictions | Once per weekend |
| `score_predictions` | Sunday 20:00 UTC | Evaluate vs race results | Once per weekend |

**Sprint Detection**: Automatically detects sprint races via FastF1's EventFormat field. If sprint detected, schedules `ingest_sprint` job ~30 min after sprint end.

Plus hourly FastF1 data refresh via `scripts/hourly_fastf1_refresh.py`

### Key Configuration

`config/settings.py`:

```python
CURRENT_SEASON = 2026
HISTORICAL_YEARS = [2021, 2022, 2023, 2024, 2025]
ALPHA_GRID = {min: 0.2, max: 0.9, steps: 15}  # Blend weights

# Pre-qualifying features
PRE_QUALI_FEATURES = [
    'avg_finish', 'momentum', 'constructor_avg', 
    'dnf_flag', 'track_history', 'dev_rate', 'overtaking_index'
]

# Post-qualifying features (grid position is huge)
POST_QUALI_FEATURES = [
    'grid_position', 'quali_gap_to_pole', 'grid_position_weighted'
]

# Model hyperparameters (XGBoost)
XGBOOST_PARAMS = {
    'max_depth': 4,
    'learning_rate': 0.08,
    'n_estimators': 300
}

# Directories
PATHS = {
    'data': 'data/',
    'models': 'models/',
    'predictions': 'data/predictions/',
    'metrics': 'data/metrics/',
    'processed': 'data/processed/'
}
```

**Environment Variables**:

```
ADMIN_API_KEY=<required>         # Secret for admin endpoints
SCHEDULER_ENABLED=false          # Enable auto-scheduling (default: off)
CURRENT_SEASON=2026              # Year (default: 2026)
```

---

## 🔄 How Frontend & Backend Communicate

### 1. Frontend Startup

```
1. Browser loads http://localhost:5173
2. React Router initializes
3. Home page mounts
4. useApi hooks fire for: /api/calendar, /api/status, /api/predictions/next
5. Components render with loading states
6. Data arrives, UI updates
```

### 2. User Navigation

```
User clicks: "Race Detail" → Link to /race/3
  ↓
RaceDetail.jsx mounts with useParams() = {round: 3}
  ↓
Fetches:
  - /api/predictions/3/prequali
  - /api/predictions/3/postquali
  - /api/predictions/3/comparison
  ↓
Renders pre/post comparison table
```

### 3. Admin Trigger

```
Admin clicks: "Refresh Predictions"
  ↓
Frontend POST to /api/refresh (with X-API-Key)
  ↓
Backend: subprocess.Popen([python, scripts/run_pipeline.py])
  ↓
Pipeline collects data, trains, generates predictions
  ↓
Writes: data/predictions/round_N_*.json
  ↓
Frontend refetches /api/predictions/next
  ↓
Dashboard updates with new predictions
```

---

## 📊 Data Flow

```
┌─ Raw Data Sources ─────────────────────────────────┐
│  FastF1 (2026) | Ergast (2023-2025) | f1api.dev  │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─ Normalize & Cache ────────────────────────────────┐
│  data/*.csv files (race results, standings)       │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─ Feature Engineering ──────────────────────────────┐
│  Build momentum, track history, constructor avg   │
│  Output: data/processed/2026_features.csv         │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─ Model Training ────────────────────────────────────┐
│  Train pre-quali & post-quali XGBoost models      │
│  Output: models/pre*.json, models/post*.json      │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─ Generate Predictions ──────────────────────────────┐
│  Apply models to grid position data                │
│  Output: data/predictions/round_N_*.json           │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─ Evaluate ──────────────────────────────────────────┐
│  Compare predictions vs actual results             │
│  Calculate: NDCG, Top3 Hit, MAE, Alpha blend      │
│  Output: data/metrics/metrics_summary.json         │
└───────────────────┬─────────────────────────────────┘
                    ↓
┌─ Store in Database ────────────────────────────────┐
│  SQLite: predictions_log, model_metrics tables    │
│  Location: data/f1ranker.db                        │
└────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features & Capabilities

### Prediction Model

- Generates 2-stage predictions: pre-qualifying & post-qualifying
- Pre-quali: Based on 7 features (form, history, team performance, overtaking index)
- Post-quali: Based on 3 features (grid position is dominant)
- Alpha blending: Intelligently weights pre & post predictions based on track characteristics

### Sprint Race Support (NEW)

- **Auto-Detection**: Detects sprint races from FastF1's EventFormat field
- **Auto-Scheduling**: Automatically schedules sprint data ingestion ~30 min after sprint ends
- **Points Tracking**: Sprint points (top 8 scoring) separate from race points (top 10)
- **Standings Include Sprint**: WDC/WCC standings combine race + sprint points automatically
- **Sprint-Only API**: New endpoints to query sprint-only standings and calendar
- **Data Format**: `session_type` column distinguishes "R" (race) from "S" (sprint)
- **Deduplication**: Idempotent CSV merge prevents duplicate sprint entries

**2026 Sprint Races**:
- Round 2 (China): Sprint completed, data ingested ✓
- Round 5 (Miami): Sprint scheduled
- Additional sprints auto-detected from FastF1 schedule

### Performance Metrics

- **NDCG** (Normalized Discounted Cumulative Gain) - How well ranked the predictions are
- **Top 3 Hit Rate** - % of races where actual winner in top 3 predictions
- **MAE** - Mean absolute error in finishing positions
- **Per-driver accuracy** - Hit rates for each driver

### Real-Time Updates

- Hourly FastF1 cache refresh (via background task)
- Thursday pre-quali predictions (before Friday qualifying)
- Saturday sprint results ingestion (if sprint weekend)
- Saturday post-quali predictions (after qualifying)
- Sunday full retraining on race results

### Data Resilience

- Synthetic data fallback if APIs fail
- Hardcoded 2026 race calendar if FastF1 unavailable
- CSV-based standings computation if API fails
- Sprint recovery: Auto-triggers if missed within 6-hour window

---

## 🚀 Unified Server Deployment

### Architecture: Single Port (8000)

The application runs as a **single FastAPI server** on port 8000:

```
Client Browser
     ↓
http://localhost:8000
     ↓
FastAPI Server (app/main.py)
     ├─ /api/*          → Python handlers (predictions, standings, calendar)
     ├─ /health, /ready → Admin endpoints
     └─ /               → React static files (SPA)
```

### How It Works

1. **React Build**: TypeScript/Vite compiles to `frontend/dist/`
2. **Server Setup**: FastAPI serves static files from `frontend/dist/` at `/`
3. **Routing Priority**:
   - `/api/*` → Handled by Python endpoints first
   - `/*` → Catch-all returns `index.html` for React Router (SPA behavior)
4. **CORS**: Configured to allow all origins (no CORS issues)

### Build & Run

```bash
# Build frontend
cd frontend
npm run build

# Run unified server (includes React static + API)
cd .. && python app/main.py
# Accessible at: http://localhost:8000
```

### Why Unified?

- **Simpler deployment**: Single process vs frontend + backend separately
- **No CORS issues**: Same origin for API and UI
- **Production-ready**: Docker/Railway deployment handles one service
- **Development-friendly**: Frontend changes auto-rebuild with npm run build

---

## 📊 Current Data State (as of 2026-05-02)

### Season Progress

- **Rounds Completed**: 2 (Australia race + China sprint+race)
- **Total CSV Rows**: 88 (66 race rows + 22 sprint rows)
- **Drivers in Database**: 22
- **Constructors in Database**: 11

### Standings After Round 2 with Sprint

**Top 5 Drivers (WDC)**:
1. Kimi Antonelli - 72 pts (68 race + 4 sprint)
2. George Russell - 63 pts (55 race + 8 sprint) *China sprint winner*
3. Charles Leclerc - 49 pts (42 race + 7 sprint)
4. Lewis Hamilton - 41 pts (35 race + 6 sprint)
5. Lando Norris - 25 pts (20 race + 5 sprint)

**Top 3 Constructors (WCC)**:
1. Mercedes - 135 pts (123 race + 12 sprint)
2. Ferrari - 90 pts (77 race + 13 sprint)
3. McLaren - 46 pts (38 race + 8 sprint)

### Sprint Data Integration

**China (Round 2) Sprint - Completed**:
- Date: 2026-05-03
- Top 3 finishers: Russell (8pts), Leclerc (7pts), Hamilton (6pts)
- 22 drivers completed sprint
- Data ingested to: `data/2026_race_results.csv` with `session_type='S'`

### Data Pipeline Status

| Component | Status | Details |
|-----------|--------|---------|
| Calendar Cache | ✓ Active | 22 races, 2026 F1 schedule loaded |
| Race Results CSV | ✓ Updated | 66 rows (3 rounds × 22 drivers) |
| Sprint Results CSV | ✓ Ingested | 22 rows from China sprint |
| Standings Computation | ✓ Working | Combines race + sprint points |
| Sprint-Only Endpoints | ✓ Available | `/api/standings/drivers/sprints`, etc. |
| Scheduler | ✓ Ready | Auto-detects sprints for future rounds |

### Key Files

```
data/
├── 2026_race_results.csv          # 88 rows (R=66, S=22) - source of truth
├── 2026_calendar.json              # Sprint races flagged with is_sprint=true
├── 2026_standings.csv              # Generated from race_results.csv
└── 2026_driver_standings.csv       # Generated from race_results.csv

models/
├── prequali_2026_lambdarank.json   # Pre-qualifying model
├── postquali_2026_lambdarank.json  # Post-qualifying model
└── ...lambdarank files            # Historical + blended models

app/
├── api.py                          # 20+ endpoints (includes sprint endpoints)
├── scheduler.py                    # Auto-detects & schedules sprint jobs
└── database.py                     # Handles session_type for sprint/race distinction
```

---

## 🔄 API Usage Examples

### Get Combined Standings (Race + Sprint)

```bash
curl http://localhost:8000/api/standings/drivers | jq '.drivers[0:3]'

# Response includes sprint_points breakdown:
{
  "driver_name": "Kimi Antonelli",
  "points": 72,           # Total: race + sprint
  "race_points": 68,
  "sprint_points": 4
}
```

### Get Sprint-Only Standings

```bash
curl http://localhost:8000/api/standings/drivers/sprints | jq '.drivers[0:5]'

# Response: Only drivers with sprint points
{
  "driver_name": "George Russell",
  "points": 8      # Sprint points only
}
```

### Get Sprint Races from Calendar

```bash
curl http://localhost:8000/api/calendar/sprints | jq '.'

# Response:
{
  "season": 2026,
  "sprint_races": [
    {
      "round": 2,
      "name": "Chinese Grand Prix",
      "is_sprint": true,
      "sprint_start_utc": "...",
      "sprint_end_utc": "..."
    }
  ],
  "total_sprints": 2  # Will grow as season progresses
}
```

### Get Race Results (Including Sprint Rows)

```bash
curl http://localhost:8000/api/race-results | jq '.results[] | select(.round==2)'

# Response includes both race and sprint entries:
[
  { "round": 2, "driver": "Kimi Antonelli", "session_type": "R", "points": 25 },
  { "round": 2, "driver": "George Russell", "session_type": "S", "points": 8 }
]
```

---

## 📝 Future Enhancements

### Planned Features
- [ ] Driver/Team comparison dashboard
- [ ] Historical trend analysis across seasons
- [ ] Weather impact analysis for sprint weekends
- [ ] Detailed session replay integration
- [ ] Advanced filtering for standings view

### Sprint-Related Improvements
- [ ] Sprint-specific prediction model (different feature importance)
- [ ] Sprint vs Race performance correlation analysis
- [ ] Sprint damage/incident tracking
- [ ] Sprint-to-race momentum indicators
