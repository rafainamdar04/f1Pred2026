# F1 Race Predictions

Full-stack ML platform that generates pre- and post-qualifying race outcome predictions for the 2026 F1 season.

**Stack:** FastAPI · React/Vite · XGBoost · SQLite · APScheduler  
**Deploy:** Railway (backend) · Vercel (frontend)

---

## Local Development

### Backend

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt

export ADMIN_API_KEY=<any-string-for-dev>
python app/main.py
# API available at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local       # then set VITE_API_BASE_URL=http://localhost:8000
npm run dev
# UI available at http://localhost:5173
```

### Docker (full backend)

```bash
docker build -t f1racepred .
docker run -p 8000:8000 \
  -e ADMIN_API_KEY=$(openssl rand -hex 32) \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  f1racepred
```

---

## API Endpoints

### Public (no auth required)

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Liveness check |
| `GET /ready` | Readiness check (predictions + metrics exist) |
| `GET /api/calendar` | 2026 race schedule |
| `GET /api/status` | Pipeline status and scheduler state |
| `GET /api/predictions/next` | Latest post-quali predictions |
| `GET /api/predictions/{round}/prequali` | Pre-quali predictions for a round |
| `GET /api/predictions/{round}/postquali` | Post-quali predictions for a round |
| `GET /api/predictions/{round}/comparison` | Pre vs post ranking delta |
| `GET /api/standings/drivers` | WDC standings |
| `GET /api/standings/constructors` | WCC standings |
| `GET /api/metrics` | Model performance metrics |
| `GET /api/race-results` | Season race results |

### Admin (require `X-API-Key` header)

| Endpoint | Description |
|----------|-------------|
| `POST /api/refresh` | Run the full prediction pipeline |
| `POST /api/refresh/force` | Force-schedule the pipeline immediately |
| `POST /api/admin/trigger/{job_name}` | Trigger a specific scheduler job |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in values. Required for production:

| Variable | Description |
|----------|-------------|
| `ADMIN_API_KEY` | 32+ char secret — `openssl rand -hex 32` |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (e.g. your Vercel URL) |
| `ENV` | `production` or `development` |
| `DATABASE_URL` | SQLAlchemy URL, e.g. `sqlite:////app/data/f1ranker.db` |
| `DATA_DIR` | Path for data files and SQLite DB |
| `MODELS_DIR` | Path for XGBoost model files |

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step Railway + Vercel setup, volume configuration, first-run seeding, and common gotchas.
