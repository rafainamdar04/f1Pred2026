from __future__ import annotations

import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from app.database import log_pipeline_finish, log_pipeline_start
from app.schemas import (
    ComparisonResponse,
    MetricsSummary,
    PostqualiRoundPredictions,
    PrequaliRoundPredictions,
    validate_metrics_file,
    validate_postquali_predictions_file,
    validate_prequali_predictions_file,
)
from app.scheduler import trigger_full_pipeline_now
from app.status import read_status_file
from config.settings import API_KEY, PATHS, SCHEDULER_ENABLED

app = FastAPI()

API_KEY_HEADER = "X-API-Key"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    if not API_KEY:
        return JSONResponse(status_code=503, content={"detail": "API_KEY not configured"})
    provided_key = request.headers.get(API_KEY_HEADER, "")
    if provided_key != API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return await call_next(request)


def _load_status_payload() -> dict:
    try:
        return read_status_file()
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _next_sunday_utc() -> str | None:
    if not SCHEDULER_ENABLED:
        return None
    now = datetime.now(timezone.utc)
    days_ahead = (6 - now.weekday()) % 7
    next_sunday = now + timedelta(days=days_ahead)
    next_sunday = next_sunday.replace(hour=20, minute=0, second=0, microsecond=0)
    if next_sunday <= now:
        next_sunday += timedelta(days=7)
    return next_sunday.isoformat()


def _newest_model_timestamp() -> str | None:
    models_dir = Path(PATHS["models"])
    if not models_dir.exists():
        return None
    newest = None
    for model_path in models_dir.glob("*.json"):
        mtime = model_path.stat().st_mtime
        if newest is None or mtime > newest[0]:
            newest = (mtime, model_path)
    if newest is None:
        return None
    return datetime.fromtimestamp(newest[0], tz=timezone.utc).isoformat()


def _prediction_path(round_num: int, mode: str) -> Path:
    suffix = "prequali" if mode == "prequali" else "postquali"
    return Path(PATHS["predictions"]) / f"round_{round_num}_{suffix}_predictions.json"


def _load_prequali_predictions(path: Path) -> PrequaliRoundPredictions:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Predictions file not found: {path}")
    try:
        return validate_prequali_predictions_file(str(path))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Predictions file failed validation: {path}",
        ) from exc


def _load_postquali_predictions(path: Path) -> PostqualiRoundPredictions:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Predictions file not found: {path}")
    try:
        return validate_postquali_predictions_file(str(path))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Predictions file failed validation: {path}",
        ) from exc


def _latest_prediction_path(mode: str) -> Path:
    predictions_dir = Path(PATHS["predictions"])
    if not predictions_dir.exists():
        raise HTTPException(status_code=404, detail=f"Predictions directory not found: {predictions_dir}")

    suffix = "prequali" if mode == "prequali" else "postquali"
    pattern = re.compile(rf"round_(\d+)_{suffix}_predictions\.json$")
    latest_round = None
    latest_path = None
    for path in predictions_dir.glob(f"round_*_{suffix}_predictions.json"):
        match = pattern.match(path.name)
        if not match:
            continue
        round_num = int(match.group(1))
        if latest_round is None or round_num > latest_round:
            latest_round = round_num
            latest_path = path

    if latest_path is None:
        raise HTTPException(status_code=404, detail="No prediction files found")
    return latest_path


def _load_metrics(path: Path) -> MetricsSummary:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Metrics file not found: {path}")
    try:
        return validate_metrics_file(str(path))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Metrics file failed validation: {path}",
        ) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
        metrics_path = Path(PATHS["metrics"]) / "metrics_summary.json"
        predictions_dir = Path(PATHS["predictions"])
        has_metrics = metrics_path.exists()
        has_predictions = predictions_dir.exists() and any(
                predictions_dir.glob("round_*_predictions.json")
        )
        if not has_metrics or not has_predictions:
                raise HTTPException(
                        status_code=503,
                        detail={
                                "metrics": has_metrics,
                                "predictions": has_predictions,
                        },
                )
        return {"status": "ready", "metrics": True, "predictions": True}


@app.get("/", response_class=HTMLResponse)
def landing_page() -> str:
        return """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>F1 Race Predictions API</title>
        <style>
            body {
                font-family: "Trebuchet MS", "Lucida Sans Unicode", "Lucida Grande", sans-serif;
                margin: 0;
                padding: 40px;
                background: radial-gradient(circle at top, #f2f2f2, #e6eef5);
                color: #1b2430;
            }
            .card {
                max-width: 720px;
                margin: 0 auto;
                background: #ffffff;
                border-radius: 16px;
                padding: 28px 32px;
                box-shadow: 0 20px 40px rgba(26, 36, 56, 0.12);
            }
            h1 {
                margin-top: 0;
                font-size: 32px;
            }
            p {
                line-height: 1.6;
            }
            code {
                background: #f3f6fb;
                padding: 2px 6px;
                border-radius: 6px;
            }
            ul {
                padding-left: 18px;
            }
            a {
                color: #2b5fb2;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>F1 Race Predictions API</h1>
            <p>Portfolio API for pre- and post-qualifying race outcome predictions.</p>
            <p>Provide an API key header on all <code>/api</code> requests:</p>
            <p><code>X-API-Key: YOUR_KEY</code></p>
            <h3>Quick Links</h3>
            <ul>
                <li><a href="/health">/health</a></li>
                <li><a href="/ready">/ready</a></li>
                <li><a href="/api/metrics">/api/metrics</a></li>
                <li><a href="/api/predictions/next/postquali">/api/predictions/next/postquali</a></li>
            </ul>
        </div>
    </body>
</html>
"""


@app.get("/api/metrics")
def get_metrics() -> dict:
    metrics_path = Path(PATHS["metrics"]) / "metrics_summary.json"
    metrics = _load_metrics(metrics_path)
    return metrics.model_dump()


@app.get("/api/predictions/next")
def get_next_predictions() -> dict:
    latest_path = _latest_prediction_path("postquali")
    predictions = _load_postquali_predictions(latest_path)
    return predictions.model_dump()


@app.get("/api/predictions/next/prequali")
def get_next_prequali_predictions() -> dict:
    latest_path = _latest_prediction_path("prequali")
    predictions = _load_prequali_predictions(latest_path)
    return predictions.model_dump()


@app.get("/api/predictions/next/postquali")
def get_next_postquali_predictions() -> dict:
    latest_path = _latest_prediction_path("postquali")
    predictions = _load_postquali_predictions(latest_path)
    return predictions.model_dump()


@app.get("/api/predictions/{round_num}/prequali")
def get_prequali_predictions(round_num: int) -> dict:
    predictions = _load_prequali_predictions(_prediction_path(round_num, "prequali"))
    return predictions.model_dump()


@app.get("/api/predictions/{round_num}/postquali")
def get_postquali_predictions(round_num: int) -> dict:
    predictions = _load_postquali_predictions(_prediction_path(round_num, "postquali"))
    return predictions.model_dump()


@app.get("/api/predictions/{round_num}/comparison")
def get_prediction_comparison(round_num: int) -> dict:
    pre = _load_prequali_predictions(_prediction_path(round_num, "prequali"))
    post = _load_postquali_predictions(_prediction_path(round_num, "postquali"))

    pre_rank = {row.driver_id: idx + 1 for idx, row in enumerate(pre.rows)}
    post_rank = {row.driver_id: idx + 1 for idx, row in enumerate(post.rows)}

    rows = []
    for row in post.rows:
        rows.append({
            "driver_id": row.driver_id,
            "prequali_rank": pre_rank.get(row.driver_id, 0),
            "postquali_rank": post_rank.get(row.driver_id, 0),
            "pace_vs_grid": pre_rank.get(row.driver_id, 0) - post_rank.get(row.driver_id, 0),
            "prequali_score": next(
                (r.final_score for r in pre.rows if r.driver_id == row.driver_id),
                0.0,
            ),
            "postquali_score": row.final_score,
        })

    response = ComparisonResponse(
        round=post.round,
        race_name=post.race_name,
        rows=rows,
    )
    return response.model_dump()


@app.get("/api/status")
def get_status() -> dict:
    status_payload = _load_status_payload()
    last_pipeline_run = status_payload.get("last_run")

    predictions_dir = Path(PATHS["predictions"])
    rounds_completed = len(list(predictions_dir.glob("round_*_predictions.json"))) if predictions_dir.exists() else 0

    return {
        "last_pipeline_run": last_pipeline_run,
        "next_scheduled": _next_sunday_utc(),
        "rounds_completed": rounds_completed,
        "model_version": _newest_model_timestamp(),
    }


@app.post("/api/refresh")
async def refresh_pipeline() -> dict:
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "run_pipeline.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Pipeline script not found: {script_path}")

    run_id = log_pipeline_start()
    predictions_dir = Path(PATHS["predictions"])
    rounds_completed = (
        len(list(predictions_dir.glob("round_*_predictions.json")))
        if predictions_dir.exists()
        else 0
    )

    try:
        subprocess.Popen([sys.executable, str(script_path)], cwd=str(project_root))
        log_pipeline_finish(run_id, "running", rounds_completed)
    except OSError as exc:
        log_pipeline_finish(run_id, "failed", rounds_completed, error_message=str(exc))
        raise HTTPException(status_code=500, detail="Failed to start pipeline") from exc

    return {
        "status": "pipeline started",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/refresh/force")
async def refresh_pipeline_force() -> dict:
    job_id = trigger_full_pipeline_now()
    return {
        "status": "pipeline scheduled",
        "job_id": job_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
