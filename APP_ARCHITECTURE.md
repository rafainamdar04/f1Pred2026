# F1RacePred Application Architecture

## 📊 App Structure Overview

Your F1RacePred application is a **full-stack machine learning prediction platform** with three main tiers:

```
┌─────────────────────────────────────────────────────────┐
│         FRONTEND (React/Vite/TypeScript)                │
│  Port: 5173 (dev) | Serves dashboard UI                │
│  - 5 pages, 10+ reusable components                     │
│  - Tailwind CSS + team color system                     │
│  - Lightweight: No Redux, just React Context + hooks    │
└─────────────────────────────────────────────────────────┘
                          ↕ JSON/REST API
┌─────────────────────────────────────────────────────────┐
│       BACKEND API (FastAPI/Python)                      │
│  Port: 8000 | 18+ endpoints                             │
│  - SQLite database (6 tables)                           │
│  - APScheduler (4 recurring jobs)                       │
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

#### 1. Routing (React Router v6)

```
/              → Home (dashboard)
/race          → RaceDetail (latest race)
/race/:round   → RaceDetail (specific round)
/drivers       → Drivers (performance profiles)
/model         → ModelReport (metrics dashboard)
/archive       → Archive (season history)
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

### Database Schema (6 Tables)

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

#### RaceResult - Final race results & points

```
id, round, driver_id, final_pos, points, created_at
```

#### ModelMetric - Performance metrics per round

```
id, round, top3_hit_rate, ndcg, mae, alpha, created_at
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
| `/api/standings/drivers` | GET | WDC standings computed from results |
| `/api/standings/constructors` | GET | WCC standings computed from results |
| `/api/race-results` | GET | All race results for season |
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

4 recurring jobs (disabled by default in Docker):

| Job | When | What | Frequency |
|-----|------|------|-----------|
| `run_prequali` | Thursday 12:00 UTC | Pre-quali predictions | Once per weekend |
| `ingest_quali` | Saturday 18:00 UTC | Ingest qualifying results | Once per weekend |
| `run_postquali` | Saturday 18:00 UTC | Post-quali predictions | Once per weekend |
| `score_predictions` | Sunday 20:00 UTC | Evaluate vs race results | Once per weekend |

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

### Performance Metrics

- **NDCG** (Normalized Discounted Cumulative Gain) - How well ranked the predictions are
- **Top 3 Hit Rate** - % of races where actual winner in top 3 predictions
- **MAE** - Mean absolute error in finishing positions
- **Per-driver accuracy** - Hit rates for each driver

### Real-Time Updates

- Hourly FastF1 cache refresh
- Thursday pre-quali predictions (before Friday qualifying)
- Saturday post-quali predictions (after qualifying)
- Sunday full retraining on race results

### Data Resilience

- Synthetic data fallback if APIs fail
- Hardcoded 2026 race calendar if FastF1 unavailable
- CSV-based standings if API fails
