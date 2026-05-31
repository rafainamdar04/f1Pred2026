# CLAUDE.md — F1 Race Prediction (2026)

## Stack
- **Backend**: FastAPI · SQLite (SQLAlchemy) · XGBoost (LambdaRank) · APScheduler
- **Frontend**: React 19 · Vite · Tailwind 3 · React Router · TypeScript
- **Data**: FastF1, Ergast/Jolpica APIs, F1API SDK

## Commands
```bash
# Backend
uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev      # dev server
cd frontend && npm run build    # TypeScript check + Vite build
cd frontend && npm run lint

# Pipeline
python scripts/run_pipeline.py

# Tests
pytest tests/
```

## Backend layout
```
app/
  main.py       # startup + APScheduler init
  api.py        # all REST endpoints
  database.py   # SQLAlchemy schema
  scheduler.py  # background jobs
  schemas.py    # Pydantic models
  status.py     # health/status logic
config/
  settings.py   # env vars, XGBoost params, track indices
  grid_2026.yaml
scripts/        # data ingestion + ML pipeline
models/         # pre-trained *.json LambdaRank models
data/           # SQLite DB + prediction JSON files
```

## API endpoints
- **Public**: `/api/calendar`, `/api/predictions/*`, `/api/standings/*`, `/api/race-results`, `/api/metrics`, `/api/status`
- **Admin** (X-API-Key header): `/health`, `/ready`, `/api/refresh`
- Predictions on disk: `data/predictions/round_{N}_{prequali|postquali}_predictions.json`

## Frontend layout
```
frontend/src/
  App.jsx              # router — entry is main.tsx → App.jsx (NOT App.tsx, that's dead boilerplate)
  pages/               # Home, RaceDetail, Drivers, ModelReport, Archive
  components/          # OracleCard, WDCStandings, WCCStandings, Countdown, etc.
  constants/
    teamColors.js      # TEAM_COLORS, getTeamColor(), getTeamAbbr(), BASE_URL
    circuits.js        # CIRCUIT_SVG paths, getCircuitSvg()
  hooks/
```

## Key conventions
- **Styles**: inline styles for layout precision, not Tailwind classes. Tailwind only for utility resets.
- **Fonts**: Barlow Condensed 900 (display), DM Sans (body), DM Mono (mono) via Google Fonts.
- **Theme**: `#070707` background. Dark F1 aesthetic — reference `frontend/f1-predict-v2.html`.
- **Prediction rows**: sorted by `final_score` descending; index 0 = P1 predicted.
- **VITE_API_URL**: env var for API base (defaults to `http://localhost:8000`).

## Data gotchas
- Ergast API may not serve 2026 season data — prefer `data/2026_standings.csv` or Jolpica.
- Verify Ergast is responding before touching standings endpoints.
- SQLite is the sole DB; no migrations framework — schema lives in `database.py`.
