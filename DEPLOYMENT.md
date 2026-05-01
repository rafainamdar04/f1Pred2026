# Deployment Guide

Split-stack deployment: **backend → Railway**, **frontend → Vercel**.

---

## Required Environment Variables

See `.env.example` for the full list. Minimum required for production:

| Variable | Description |
|----------|-------------|
| `ADMIN_API_KEY` | 32+ char hex secret. Generate: `openssl rand -hex 32` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins, e.g. `https://yourapp.vercel.app` |
| `ENV` | Set to `production` |
| `DATABASE_URL` | `sqlite:////app/data/f1ranker.db` (absolute path for volume mount) |
| `DATA_DIR` | `/app/data` (persistent volume mount path) |
| `MODELS_DIR` | `/app/models` (persistent volume mount path) |
| `SCHEDULER_ENABLED` | `true` to enable weekly APScheduler jobs |
| `CURRENT_SEASON` | `2026` |
| `PIPELINE_TIMEOUT_SECONDS` | `1800` (30 min) |

---

## Backend on Railway

1. **Connect repo** — New Project → Deploy from GitHub repo → select this repo.
2. **Set builder** — Railway auto-detects `railway.json` and uses the `Dockerfile`.
3. **Attach persistent volume** — Service → Volumes tab:
   - Mount `/app/data` — stores SQLite DB, CSVs, predictions, metrics, logs
   - Mount `/app/models` — stores XGBoost model files
4. **Set environment variables** — Service → Variables tab, add all variables from the table above.
5. **Deploy** — Railway deploys automatically on push to `main`.

> The `PORT` env var is injected by Railway automatically. `startCommand` in `railway.json` uses it.

---

## Frontend on Vercel

1. **Import repo** — vercel.com → Add New Project → Import Git Repository.
2. **Set root directory** — change from `/` to `frontend/`.
3. **Framework preset** — Vite (auto-detected).
4. **Set environment variable**:
   - `VITE_API_BASE_URL` = `https://<your-railway-service>.railway.app`
5. **Deploy** — Vercel builds and deploys automatically.

`frontend/vercel.json` handles SPA routing so direct links like `/race/3` work.

---

## First-Run Seeding

After deploying, the database and predictions directories will be empty. Seed them:

```bash
# Trigger the full pipeline via the API
curl -X POST https://<your-railway-url>/api/refresh \
  -H "X-API-Key: <your-ADMIN_API_KEY>"

# Or exec into the Railway container and run directly
railway run python scripts/run_pipeline.py
```

---

## Verifying Scheduler Jobs

```bash
curl https://<your-railway-url>/api/status
```

Expected response includes `next_scheduled` (non-null when `SCHEDULER_ENABLED=true`) and job names:
- `weekly_weekend_planner` — Monday 00:00 UTC, schedules the race weekend
- `weekend_prequali_r<N>` — Thursday ~12:00 UTC
- `weekend_ingest_quali_r<N>` — Saturday ~30 min after qualifying ends
- `weekend_ingest_results_r<N>` — Sunday ~1 hr after race ends

---

## Rollback

- **Railway** — Service → Deployments tab → click any previous deployment → Redeploy.
- **Vercel** — Project → Deployments tab → click any previous deployment → Promote to Production.

---

## Common Gotchas

| Problem | Fix |
|---------|-----|
| `FATAL: ENV=production requires ADMIN_API_KEY` | Set `ADMIN_API_KEY` to a 32+ char string in Railway variables |
| Frontend gets CORS errors | Ensure `ALLOWED_ORIGINS` on Railway includes your exact Vercel URL (no trailing slash) |
| Frontend calls `localhost:8000` in production | `VITE_API_BASE_URL` was not set before Vercel build — set it in Vercel env vars and redeploy |
| `/race/3` returns 404 on Vercel | `frontend/vercel.json` rewrites rule missing — already included in this repo |
| Predictions return 404 after deploy | Volume not mounted, or first-run seeding not done — run `/api/refresh` |
| SQLite "unable to open database" | `DATABASE_URL` uses relative path — use absolute `/app/data/f1ranker.db` in prod |
