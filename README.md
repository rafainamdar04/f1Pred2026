# F1 Race Prediction — 2026 Season

**Live:** https://frontend-pearl-chi-56.vercel.app/

A full-stack ML platform that ranks all 20 F1 drivers by predicted finishing position before and after qualifying for every race on the 2026 calendar. Two XGBoost LambdaRank models — one pre-qualifying, one post-qualifying — run automatically on a schedule and serve predictions through a FastAPI backend to a React frontend.

---

## The Problem

Predicting a Formula 1 race finishing order is fundamentally a **ranking problem**, not a regression or classification problem. You're not predicting a lap time or a binary outcome — you're ordering 20 drivers relative to each other under constraints (track character, current form, qualifying result) that shift every two weeks.

Most public F1 prediction attempts treat it as regression (predict finish position as a number) or use naive heuristics (championship standings → predicted order). This project uses **learning-to-rank** — specifically XGBoost's pairwise LambdaRank objective — which is trained to maximise the quality of the entire ranking rather than minimise per-driver position error.

---

## Accuracy

Evaluated on 6 completed rounds of the 2026 season:

| Model | NDCG@full | Top-3 Hit Rate | Mean Rank Error |
|---|---|---|---|
| Pre-qualifying | 0.9743 | 77.8% | ±2.3 positions |
| Post-qualifying | 0.9783 | 88.9% | ±2.1 positions |

- **NDCG** (Normalised Discounted Cumulative Gain) measures full-ranking quality; 1.0 is a perfect ordering.
- **Top-3 Hit Rate**: at least one of the actual top-3 finishers was predicted in the model's top 3.
- Post-qualifying is more accurate because grid position is a strong signal — the model correctly exploits it.

---

## Data & Features

**Sources:**
- [FastF1](https://github.com/theOehrly/Fast-F1) — live 2026 telemetry, qualifying gaps, and race results
- Historical races 2021–2025 (~250 races) for base model training
- Circuit-level overtaking indices hand-coded for all 26 venues

**Pre-qualifying features (8):**

| Feature | What it captures |
|---|---|
| `avg_finish_position` | Season baseline pace |
| `avg_points_per_race` | Points-weighted performance |
| `momentum` | Last-race points minus first-race points |
| `constructor_avg_points` | Team performance this season |
| `dnf_flag` | Historical reliability rate |
| `driver_track_history` | Mean finish at this specific circuit |
| `constructor_development_rate` | Recent 3 rounds vs prior 3 rounds |
| `track_overtaking_index` | Circuit-level overtaking difficulty (0.2 Monaco → 0.9 Monza) |

**Post-qualifying adds 3 more:**

| Feature | What it captures |
|---|---|
| `grid_position` | Qualifying result |
| `quali_gap_to_pole` | Raw pace gap to the fastest qualifier |
| `grid_position_weighted` | `grid × (1 − overtaking_index)` — grid matters more at Monaco than Monza |

**Training strategy:**

Two paired models per phase: one trained on 2021–2025 historical data (weighted by season recency), one fine-tuned on 2026 races only (with recency decay 0.85ⁿ so earlier rounds matter less as the season progresses). Final scores blend as `0.9 × score_2026 + 0.1 × score_historical` — alpha is grid-searched each run.

---

## Why One Global Model (Not Per-Circuit)

A natural instinct is to train a separate model for each of the 26 circuits, capturing circuit-specific patterns in full. The reason this project uses a single global model with circuit features instead:

**Data sparsity.** F1 visits each circuit once per year. Going back to 2021 gives you at most ~5 labelled examples per circuit — nowhere near enough to fit a ranking model that won't overfit to a handful of outlier races (weather, safety car, reliability cascades).

**Circuit awareness is already in the features.** The `track_overtaking_index` and `driver_track_history` features encode what matters most about each circuit — how much grid position matters, and which drivers have historically performed there. A global model learns how to use those signals across all circuits simultaneously, which is more data-efficient.

**Roster and regulation instability.** The 2026 season introduced new power unit regulations and two new constructors. A per-circuit model trained on 2021–2025 data would carry stale driver-team combinations with no way to discount them. The global model with season-specific 2026 fine-tuning handles this naturally.

**New and rotated venues.** The calendar adds and swaps circuits (Las Vegas in 2023, Madrid in 2026). A per-circuit model has zero history; the global model can still predict using current-form and team features.

Circuit-specific models — potentially trained on a longer history or using circuit cluster embeddings — are a clear future extension once more 2026 rounds accumulate.

---

## Architecture

```
FastF1 API ──┐
             ├── scripts/run_pipeline.py
Historical   │     ├── fastf1_scraper.py        (ingest)
CSV data  ───┘     ├── build_processed_features.py (feature engineering)
                   ├── train_prequali_model.py   (XGBoost LambdaRank × 2)
                   ├── train_postquali_model.py  (XGBoost LambdaRank × 2)
                   ├── evaluate_hybrid.py        (NDCG, alpha grid search)
                   └── predict_*.py              → data/predictions/round_N_*.json

data/predictions/ ──── app/ (FastAPI) ──── frontend/ (React + Vite)
                         │                   Pages: Home, Race Detail,
                  APScheduler                       Standings, Archive,
                  (auto-triggers                    Model Report
                   pre-quali / post-quali
                   / result ingestion)
```

**Stack:** FastAPI · SQLite (SQLAlchemy) · XGBoost 3.2 · APScheduler · React 19 · Vite · Tailwind 3  
**Deploy:** Railway (backend) · Vercel (frontend)

---

## Local Development

### Backend

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

export ADMIN_API_KEY=dev-key
uvicorn app.main:app --reload
# API at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

### Run the full pipeline

```bash
python scripts/run_pipeline.py          # both models
python scripts/run_pipeline.py --mode prequali
python scripts/run_pipeline.py --mode postquali
```

---

## API

Public endpoints (no auth):

| Endpoint | Description |
|---|---|
| `GET /api/calendar` | Full 2026 race calendar |
| `GET /api/predictions/prequali/{round}` | Pre-qualifying predictions |
| `GET /api/predictions/postquali/{round}` | Post-qualifying predictions |
| `GET /api/standings/drivers` | Current WDC standings |
| `GET /api/standings/constructors` | Current WCC standings |
| `GET /api/metrics` | Model evaluation metrics per round |
| `GET /api/status` | Pipeline health + last run timestamps |

Admin endpoints require `X-API-Key` header: `/health`, `/ready`, `/api/refresh`.

Prediction access is time-gated: pre-qualifying unlocks 3 days before the race; post-qualifying unlocks 90 minutes after qualifying ends.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ADMIN_API_KEY` | Yes | Protects admin endpoints |
| `VITE_API_URL` | Frontend | Backend base URL (default: `http://localhost:8000`) |
| `DATABASE_URL` | No | Defaults to `data/f1ranker.db` |
