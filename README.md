<div align="center">

# 🏎️ F1 Race Oracle

### A full-stack machine-learning platform that ranks all 20 Formula 1 drivers by predicted finishing order — before *and* after qualifying — for every round of the 2026 season.

[![Live Demo](https://img.shields.io/badge/live-demo-E10600?style=for-the-badge&logo=vercel&logoColor=white)](https://frontend-pearl-chi-56.vercel.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-1FA463?style=for-the-badge)](LICENSE)
[![Made with XGBoost](https://img.shields.io/badge/XGBoost-LambdaRank-7C4DCB?style=for-the-badge)](https://xgboost.readthedocs.io/)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Tailwind](https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss&logoColor=white)

**[🔮 Try it live](https://frontend-pearl-chi-56.vercel.app/)** · [How it works](#-how-it-works) · [Tech stack](#-tech-stack) · [Run it locally](#-run-it-locally)

</div>

---

## 💡 Why this project

Most "F1 predictor" projects are a single notebook that fits a regression on championship points and calls it a day. I wanted to build the **whole thing the way it would ship in production** — a real ML problem framed correctly, a training pipeline that defends against data leakage, an API, a scheduler that runs itself, and a polished frontend deployed on the open web.

It's the project I point to when someone asks *"can you take an idea from raw data all the way to a live product?"* — covering applied ML, backend engineering, frontend design, and deployment in one repo.

> **The core insight:** predicting a race result is a **ranking** problem, not a regression one. You're not guessing a lap time — you're ordering 20 drivers relative to each other under conditions that change every two weeks. So the model is trained to optimise the *quality of the whole ranking*, not per-driver error.

---

## ✨ Features

- 🥇 **Two prediction phases per race** — a *pre-qualifying* model (pure pace & form) and a *post-qualifying* model that folds in the starting grid.
- 🧠 **Learning-to-rank, done properly** — XGBoost's pairwise **LambdaRank** objective, optimising NDCG across the field instead of squared error per driver.
- 🔀 **Two-tower hybrid ensemble** — a "this-season" model blended with a "five-year-history" model at a weight the data picks itself via grid search.
- 🛡️ **Leak-free by construction** — every feature for round *R* is built **only** from rounds before it. No peeking at the future.
- 🤖 **Self-driving pipeline** — APScheduler ingests results, retrains, evaluates, and republishes predictions on a schedule with zero manual steps.
- 📊 **Explainable outputs** — each prediction ships a per-driver rationale (top contributing features) and a "pace vs grid" delta.
- 🌐 **Full-stack & deployed** — FastAPI service + React/Vite frontend, live on Vercel.

---

## 🧠 How it works

### 1. Framing it as a ranking problem

Each race is a small ranking contest. Finishing position is flipped into a **relevance score** (`relevance = (last_place + 1) − finish_position`), so the winner gets the highest target and DNFs sink to the bottom. The model learns to score drivers so that, *within a race*, faster finishers score higher — exactly what LambdaRank optimises.

### 2. Feature engineering (leak-free)

For any target round, form features are aggregated strictly from earlier rounds — average finish, momentum, win/podium/pole counts, a reliability (DNF) prior, championship standings, and circuit affinity.

**Pre-qualifying — 8 pace & form features**

| Feature | Captures |
|---|---|
| `avg_finish_position` | Season baseline pace |
| `avg_points_per_race` | Points-weighted performance |
| `momentum` | Trajectory across the season |
| `constructor_avg_points` | Car competitiveness |
| `dnf_flag` | Reliability prior |
| `driver_track_history` | Mean finish at this circuit |
| `constructor_development_rate` | Recent 3 rounds vs prior 3 |
| `track_overtaking_index` | How hard passing is (0.2 Monaco → 0.9 Monza) |

**Post-qualifying — adds 3 grid features**

| Feature | Captures |
|---|---|
| `grid_position` | Where the driver starts |
| `quali_gap_to_pole` | Raw pace deficit to the fastest qualifier (s) |
| `grid_position_weighted` | `grid × (1 − overtaking_index)` — a bad grid hurts far more at Monaco than Monza |

### 3. The two-tower ensemble

Train on 2026 alone and there's too little data early in the season; train on history alone and you miss this year's pecking order. So I train **both** and blend their scores:

```
final_score = α · score_2026  +  (1 − α) · score_history
```

The historical scores are z-normalised onto the 2026 scale so the two are comparable, and **α is grid-searched each run** to maximise ranking quality — leaning on history early in the season and on current form as 2026 data accumulates.

### 4. Evaluation

Models are scored with **NDCG** (full-ranking quality), **Top-3 hit rate** (podium accuracy), and **rank MAE** — all DNF-aware, so rating a retired car highly is correctly punished. The post-qualifying model consistently leads, because the grid is a genuinely strong signal and the model exploits it.

> ℹ️ Why one global model instead of one per circuit? F1 visits each track once a year — ~5 labelled races since 2021, far too sparse to fit 26 separate rankers without overfitting. Circuit character is instead encoded *as features* (`track_overtaking_index`, `driver_track_history`), which a single global model uses far more data-efficiently — and which still works for brand-new venues with zero history.

---

## 🏗️ Architecture

```
 FastF1 / Ergast ─┐
                  ├──►  run_pipeline.py
 Historical CSVs ─┘        │
   (2021–2025)             ├─ fastf1_scraper.py            ingest
                          ├─ build_processed_features.py   leak-free feature engineering
                          ├─ train_prequali_model.py       XGBoost LambdaRank ×2
                          ├─ train_postquali_model.py      XGBoost LambdaRank ×2
                          ├─ evaluate_hybrid.py            NDCG · Top-3 · MAE · α search
                          └─ predict_*.py        ──►  data/predictions/round_N_*.json
                                                            │
            data/predictions/  ──►  FastAPI  ──►  React + Vite frontend
                                       │            Home · Race Detail · Standings
                                  APScheduler       Archive · Model Report
                              (auto ingest / retrain
                               / republish on schedule)
```

---

## 🛠️ Tech stack

| Layer | Tools |
|---|---|
| **ML** | XGBoost 3.2 (LambdaRank), scikit-learn, pandas, NumPy, PyArrow |
| **Data** | FastF1, Ergast / Jolpica APIs |
| **Backend** | FastAPI, SQLAlchemy + SQLite, APScheduler, Pydantic |
| **Frontend** | React 19, Vite, TypeScript, Tailwind CSS, React Router |
| **Deploy** | Railway (API) · Vercel (frontend) |

---

## 🚀 Run it locally

### Backend

```bash
python -m venv .venv
source .venv/Scripts/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export ADMIN_API_KEY=dev-key          # any 32+ char string in prod
uvicorn app.main:app --reload         # → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                           # → http://localhost:5173
```

### Run the full ML pipeline

```bash
python scripts/run_pipeline.py                 # ingest → train → evaluate → predict
python scripts/run_pipeline.py --mode prequali
python scripts/run_pipeline.py --mode postquali
```

---

## 🔌 API

Public endpoints (no auth):

| Endpoint | Description |
|---|---|
| `GET /api/calendar` | Full 2026 race calendar |
| `GET /api/predictions/prequali/{round}` | Pre-qualifying predictions |
| `GET /api/predictions/postquali/{round}` | Post-qualifying predictions |
| `GET /api/standings/drivers` | Current WDC standings |
| `GET /api/standings/constructors` | Current WCC standings |
| `GET /api/metrics` | Model evaluation metrics |
| `GET /api/status` | Pipeline health + last-run timestamps |

Admin endpoints (`X-API-Key` header): `/health`, `/ready`, `/api/refresh`.

> Predictions are **time-gated**: pre-qualifying unlocks 3 days before the race; post-qualifying unlocks 90 minutes after qualifying ends — so the site never spoils a result it couldn't have known.

---

## 🔧 Environment variables

| Variable | Required | Description |
|---|---|---|
| `ADMIN_API_KEY` | Yes | Protects admin endpoints (32+ chars in production) |
| `VITE_API_URL` | Frontend | Backend base URL (default `http://localhost:8000`) |
| `DATABASE_URL` | No | Defaults to `data/f1ranker.db` |

---

## 🗺️ Roadmap

- [ ] Circuit-cluster embeddings once more 2026 rounds accumulate
- [ ] In-race chaos modelling (safety cars, weather, first-lap incidents)
- [ ] Probabilistic outputs — confidence intervals per predicted position
- [ ] Driver head-to-head and "what-if" grid simulator

---

<div align="center">

**Built by [Rafa Inamdar](https://github.com/)** · Licensed under [MIT](LICENSE)

If you find this interesting, a ⭐ is always appreciated.

</div>
