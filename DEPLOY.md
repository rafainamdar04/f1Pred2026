# Deployment Guide — F1 Race Prediction (Option A: Static Frontend)

## Architecture

```
GitHub repo
  ├── frontend/public/api/*.json   ← pre-generated API snapshot
  ├── seed/                        ← baseline data/models for CI cold-start
  └── .github/workflows/
        refresh-demo.yml           ← daily cron: ingest → predict → snapshot → commit
```

The frontend is a fully static Vite build. No live backend is required.
Each race weekend, a GitHub Actions workflow runs the full ML pipeline,
snapshots all public API responses to `frontend/public/api/`, commits them,
and the static host redeploys automatically.

---

## Deploy to Vercel (recommended)

1. **Import repo** at vercel.com/new → "Import Git Repository"
2. **Root directory**: `frontend`
3. **Framework preset**: Vite (auto-detected)
4. **Build command**: `npm run build` (default)
5. **Output directory**: `dist` (default)
6. **Environment variables** (Settings → Environment Variables):

   | Key | Value |
   |-----|-------|
   | `VITE_STATIC_API` | `true` |
   | `VITE_API_BASE_URL` | *(leave empty)* |

7. Click **Deploy**.

The `vercel.json` at `frontend/vercel.json` is already configured to route
all non-API paths to `index.html` while serving `/api/*.json` as real files.

---

## Deploy to Netlify (alternative)

1. **New site from Git** → connect repo
2. **Base directory**: `frontend`
3. **Build command**: `npm run build`
4. **Publish directory**: `frontend/dist`
5. **Environment variables**:

   | Key | Value |
   |-----|-------|
   | `VITE_STATIC_API` | `true` |
   | `VITE_API_BASE_URL` | *(leave empty)* |

`frontend/public/_redirects` is already in place for Netlify SPA routing.

---

## Enable the GitHub Actions cron

1. Go to **Actions** tab in GitHub → confirm Actions are enabled for the repo.
2. The workflow `.github/workflows/refresh-demo.yml` runs automatically:
   - **Daily at 06:00 UTC** (catches overnight race results)
   - **Manual trigger**: Actions → "Refresh demo data" → "Run workflow"
3. The workflow needs write access to commit the snapshot. No extra secrets
   are required — it uses the built-in `GITHUB_TOKEN`.

> The first time you run it manually after deployment, it will generate a
> fresh snapshot from the seeded data and commit it, triggering a redeploy.

---

## How prediction lifecycle works on the static site

Race-weekend phases (upcoming / prequali / postquali / completed) are computed
**client-side** from the UTC timestamps embedded in the calendar JSON
(`prequali_at_utc`, `postquali_at_utc`, `result_at_utc`). This means:

- No backend is needed to gate content.
- The daily cron regenerates the snapshot with updated timestamps and
  new prediction files as each phase opens.
- `frontend/src/utils/phase.js` mirrors the backend gating logic exactly.

---

## Updating predictions manually

```bash
# From repo root (requires Python venv active):
python scripts/refresh_demo.py
# Then commit frontend/public/api/ and push.
```
