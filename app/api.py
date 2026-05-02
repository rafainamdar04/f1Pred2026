from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import threading

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import (
    PredictionLog,
    SessionLocal,
    get_latest_job_runs,
    log_pipeline_finish,
    log_pipeline_start,
    update_pipeline_pid,
)
from app.schemas import (
    ComparisonResponse,
    MetricsSummary,
    PostqualiRoundPredictions,
    PrequaliRoundPredictions,
    validate_metrics_file,
    validate_postquali_predictions_file,
    validate_prequali_predictions_file,
)
from app.scheduler import get_next_scheduled_event, trigger_full_pipeline_now, trigger_job_now
from app.status import read_status_file
from config.settings import (
    ADMIN_API_KEY,
    ALLOWED_ORIGINS,
    CURRENT_SEASON,
    PATHS,
    PIPELINE_TIMEOUT_SECONDS,
    SCHEDULER_ENABLED,
)

app = FastAPI()

API_KEY_HEADER = "X-API-Key"

PUBLIC_API_PATHS = {
    "/api/calendar",
    "/api/calendar/sprints",
    "/api/metrics",
    "/api/race-results",
    "/api/status",
    "/api/standings",
    "/api/standings/drivers",
    "/api/standings/constructors",
    "/api/standings/drivers/sprints",
    "/api/standings/constructors/sprints",
}
PUBLIC_API_PREFIXES = (
    "/api/predictions",
)
ADMIN_ONLY_PATHS: set[str] = set()  # /health and /ready are public for infra use

ADMIN_TRIGGERABLE_JOBS = {
    "run_prequali",
    "ingest_quali",
    "ingest_sprint",
    "run_postquali",
    "ingest_results",
    "score_predictions",
    "retrain_model",
    "schedule_weekend",
}

_SHORT_CODE_MAP = {
    "Australian Grand Prix": "AUS",
    "Chinese Grand Prix": "CHN",
    "Bahrain Grand Prix": "BHR",
    "Japanese Grand Prix": "JPN",
    "Saudi Arabian Grand Prix": "KSA",
    "Miami Grand Prix": "MIA",
    "Monaco Grand Prix": "MON",
    "Canadian Grand Prix": "CAN",
    "Spanish Grand Prix": "ESP",
    "Austrian Grand Prix": "AUT",
    "British Grand Prix": "GBR",
    "Belgian Grand Prix": "BEL",
    "Hungarian Grand Prix": "HUN",
    "Dutch Grand Prix": "NED",
    "Italian Grand Prix": "ITA",
    "Azerbaijan Grand Prix": "AZE",
    "Singapore Grand Prix": "SGP",
    "United States Grand Prix": "USA",
    "Mexico City Grand Prix": "MEX",
    "Sao Paulo Grand Prix": "BRA",
    "Las Vegas Grand Prix": "LVS",
    "Qatar Grand Prix": "QAT",
    "Abu Dhabi Grand Prix": "UAE",
}

_SPRINT_VENUES = {
    "Chinese Grand Prix",
    "Miami Grand Prix",
    "Canadian Grand Prix",
    "British Grand Prix",
    "Dutch Grand Prix",
    "Singapore Grand Prix",
}

_FALLBACK_CALENDAR = [
    {"round": 1, "name": "Australian Grand Prix", "short": "AUS", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 2, "name": "Chinese Grand Prix", "short": "CHN", "date": None, "is_sprint": True, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 3, "name": "Bahrain Grand Prix", "short": "BHR", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 4, "name": "Japanese Grand Prix", "short": "JPN", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 5, "name": "Saudi Arabian Grand Prix", "short": "KSA", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 6, "name": "Miami Grand Prix", "short": "MIA", "date": None, "is_sprint": True, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 7, "name": "Monaco Grand Prix", "short": "MON", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 8, "name": "Canadian Grand Prix", "short": "CAN", "date": None, "is_sprint": True, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 9, "name": "Spanish Grand Prix", "short": "ESP", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 10, "name": "Austrian Grand Prix", "short": "AUT", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 11, "name": "British Grand Prix", "short": "GBR", "date": None, "is_sprint": True, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 12, "name": "Belgian Grand Prix", "short": "BEL", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 13, "name": "Hungarian Grand Prix", "short": "HUN", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 14, "name": "Dutch Grand Prix", "short": "NED", "date": None, "is_sprint": True, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 15, "name": "Italian Grand Prix", "short": "ITA", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 16, "name": "Azerbaijan Grand Prix", "short": "AZE", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 17, "name": "Singapore Grand Prix", "short": "SGP", "date": None, "is_sprint": True, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 18, "name": "United States Grand Prix", "short": "USA", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 19, "name": "Mexico City Grand Prix", "short": "MEX", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 20, "name": "Sao Paulo Grand Prix", "short": "BRA", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 21, "name": "Las Vegas Grand Prix", "short": "LVS", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 22, "name": "Qatar Grand Prix", "short": "QAT", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
    {"round": 23, "name": "Abu Dhabi Grand Prix", "short": "UAE", "date": None, "is_sprint": False, "sprint_start_utc": None, "sprint_end_utc": None},
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_public_api(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if method != "GET":
        return False
    if path in PUBLIC_API_PATHS:
        return True
    return path.startswith(PUBLIC_API_PREFIXES)


def _requires_admin(path: str) -> bool:
    if path in ADMIN_ONLY_PATHS:
        return True
    return path.startswith("/api/refresh") or path.startswith("/api/admin")


def _admin_guard(request: Request) -> JSONResponse | None:
    if not ADMIN_API_KEY:
        return JSONResponse(status_code=503, content={"detail": "ADMIN_API_KEY not configured"})
    provided_key = request.headers.get(API_KEY_HEADER, "")
    if provided_key != ADMIN_API_KEY:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    return None


@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    path = request.url.path
    if _requires_admin(path):
        denied = _admin_guard(request)
        if denied:
            return denied
        return await call_next(request)

    if path.startswith("/api/") and not _is_public_api(path, request.method):
        denied = _admin_guard(request)
        if denied:
            return denied

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


def _estimate_weekend_sessions(race: dict[str, Any]) -> dict[str, str | None]:
    date_str = race.get("date")
    if not date_str:
        return {
            "prequali_run_utc": None,
            "quali_ingest_run_utc": None,
            "race_ingest_run_utc": None,
        }

    try:
        race_day = datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
    except ValueError:
        return {
            "prequali_run_utc": None,
            "quali_ingest_run_utc": None,
            "race_ingest_run_utc": None,
        }

    prequali = (race_day - timedelta(days=3)).replace(hour=12, minute=0)
    quali_ingest = (race_day - timedelta(days=1)).replace(hour=16, minute=30)
    race_start = race_day.replace(hour=14, minute=0)
    race_ingest = race_day.replace(hour=18, minute=0)
    return {
        "prequali_run_utc": prequali.isoformat(),
        "quali_ingest_run_utc": quali_ingest.isoformat(),
        "race_start_utc": race_start.isoformat(),
        "race_ingest_run_utc": race_ingest.isoformat(),
    }


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


def _calendar_cache_path() -> Path:
    return Path(PATHS["data"]) / f"{CURRENT_SEASON}_calendar.json"


def _load_calendar_cache() -> list[dict] | None:
    path = _calendar_cache_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict):
        races = payload.get("races")
        return races if isinstance(races, list) else None
    return payload if isinstance(payload, list) else None


def _write_calendar_cache(races: list[dict]) -> None:
    path = _calendar_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"season": CURRENT_SEASON, "races": races}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _short_code_for_event(name: str) -> str:
    if name in _SHORT_CODE_MAP:
        return _SHORT_CODE_MAP[name]
    words = [word for word in name.split() if word.lower() not in {"grand", "prix"}]
    if not words:
        return name[:3].upper()
    return "".join(word[0] for word in words[:3]).upper()


def _fetch_calendar_fastf1() -> list[dict] | None:
    try:
        import fastf1
        import pandas as pd
    except Exception:
        return None

    schedule = fastf1.get_event_schedule(CURRENT_SEASON)
    if schedule is None or len(schedule) == 0:
        return None

    races: list[dict] = []
    for _, row in schedule.iterrows():
        round_num = row.get("RoundNumber")
        event_name = row.get("EventName")
        if round_num is None or event_name is None:
            continue
        if int(round_num) <= 0:
            continue
        date_value = None
        for key in ("EventDate", "Session1Date", "Session1DateUtc"):
            if key in row and pd.notna(row[key]):
                date_value = row[key]
                break
        date = None
        if date_value is not None:
            try:
                date = pd.to_datetime(date_value).date().isoformat()
            except Exception:
                date = str(date_value)

        quali_start = None
        race_start = None
        if "Session4DateUtc" in row and pd.notna(row["Session4DateUtc"]):
            quali_start = pd.to_datetime(row["Session4DateUtc"], utc=True).isoformat()
        if "Session5DateUtc" in row and pd.notna(row["Session5DateUtc"]):
            race_start = pd.to_datetime(row["Session5DateUtc"], utc=True).isoformat()

        quali_end = None
        race_end = None
        if quali_start:
            quali_end = (pd.to_datetime(quali_start) + pd.Timedelta(hours=1)).isoformat()
        if race_start:
            race_end = (pd.to_datetime(race_start) + pd.Timedelta(hours=2)).isoformat()

        event_format = str(row.get("EventFormat", "conventional")).lower()
        is_sprint = event_format in ("sprint_shootout", "sprint")
        sprint_start = None
        sprint_end = None
        if is_sprint and "Session3DateUtc" in row and pd.notna(row["Session3DateUtc"]):
            sprint_start = pd.to_datetime(row["Session3DateUtc"], utc=True).isoformat()
            sprint_end = (pd.to_datetime(sprint_start) + pd.Timedelta(hours=1)).isoformat()

        name = str(event_name)
        race = {
            "round": int(round_num),
            "name": name,
            "short": _short_code_for_event(name),
            "date": date,
            "is_sprint": is_sprint,
            "sprint_start_utc": sprint_start,
            "sprint_end_utc": sprint_end,
            "quali_start_utc": quali_start,
            "quali_end_utc": quali_end,
            "race_start_utc": race_start,
            "race_end_utc": race_end,
        }
        race.update(_estimate_weekend_sessions(race))
        races.append(race)

    races.sort(key=lambda item: item["round"])
    return races


def _get_calendar() -> list[dict]:
    cached = _load_calendar_cache()
    if cached:
        # Bust stale cache that predates sprint field support
        if cached and "is_sprint" not in cached[0]:
            cached = None
            _calendar_cache_path().unlink(missing_ok=True)
    if cached:
        filtered = [race for race in cached if int(race.get("round", 0)) > 0]
        if len(filtered) != len(cached):
            _write_calendar_cache(filtered)
        for race in filtered:
            for key, value in _estimate_weekend_sessions(race).items():
                if key not in race or race[key] is None:
                    race[key] = value
        return filtered
    fetched = _fetch_calendar_fastf1()
    if fetched:
        _write_calendar_cache(fetched)
        return fetched

    fallback = list(_FALLBACK_CALENDAR)
    for race in fallback:
        race.update(_estimate_weekend_sessions(race))
    return fallback


def _inject_prediction_created_at(payload: dict, mode: str) -> dict:
    round_num = int(payload.get("round", 0))
    if round_num <= 0:
        payload["created_at"] = None
        return payload

    with SessionLocal() as session:
        row = (
            session.query(PredictionLog)
            .filter(
                PredictionLog.round == round_num,
                PredictionLog.prediction_type == mode,
            )
            .order_by(PredictionLog.created_at.desc())
            .first()
        )
    payload["created_at"] = row.created_at.isoformat() if row and row.created_at else None
    return payload


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
                predictions_dir.glob("round_*_postquali_predictions.json")
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


# Landing page will be served from frontend/dist via SPA routing below


@app.get("/api/metrics")
def get_metrics() -> dict:
    metrics_path = Path(PATHS["metrics"]) / "metrics_summary.json"
    metrics = _load_metrics(metrics_path)
    return metrics.model_dump()


@app.get("/api/calendar")
def get_calendar() -> dict:
    return {
        "season": CURRENT_SEASON,
        "races": _get_calendar(),
    }


@app.get("/api/calendar/sprints")
def get_sprint_calendar() -> dict:
    """Get only sprint races from the calendar."""
    all_races = _get_calendar()
    sprint_races = [race for race in all_races if race.get("is_sprint", False)]
    return {
        "season": CURRENT_SEASON,
        "sprint_races": sprint_races,
        "total_sprints": len(sprint_races),
    }


def _next_race_round() -> int:
    """Return the round number of the latest prequali file — this is always the active race week."""
    path = _latest_prediction_path("prequali")
    return int(re.search(r"round_(\d+)_", path.name).group(1))


@app.get("/api/predictions/next")
def get_next_predictions() -> dict:
    round_num = _next_race_round()
    predictions = _load_postquali_predictions(_prediction_path(round_num, "postquali"))
    return _inject_prediction_created_at(predictions.model_dump(), "post")


@app.get("/api/predictions/next/prequali")
def get_next_prequali_predictions() -> dict:
    latest_path = _latest_prediction_path("prequali")
    predictions = _load_prequali_predictions(latest_path)
    return _inject_prediction_created_at(predictions.model_dump(), "pre")


@app.get("/api/predictions/next/postquali")
def get_next_postquali_predictions() -> dict:
    round_num = _next_race_round()
    predictions = _load_postquali_predictions(_prediction_path(round_num, "postquali"))
    return _inject_prediction_created_at(predictions.model_dump(), "post")


@app.get("/api/predictions/{round_num}/prequali")
def get_prequali_predictions(round_num: int) -> dict:
    predictions = _load_prequali_predictions(_prediction_path(round_num, "prequali"))
    return _inject_prediction_created_at(predictions.model_dump(), "pre")


@app.get("/api/predictions/{round_num}/postquali")
def get_postquali_predictions(round_num: int) -> dict:
    predictions = _load_postquali_predictions(_prediction_path(round_num, "postquali"))
    return _inject_prediction_created_at(predictions.model_dump(), "post")


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
@app.get("/api/pipeline/status")
def get_status() -> dict:
    status_payload = _load_status_payload()
    last_pipeline_run = status_payload.get("last_run")

    predictions_dir = Path(PATHS["predictions"])
    rounds_completed = len(list(predictions_dir.glob("round_*_postquali_predictions.json"))) if predictions_dir.exists() else 0

    try:
        jobs = get_latest_job_runs()
    except Exception:
        jobs = {}

    return {
        "status": status_payload.get("status", "idle"),
        "last_pipeline_run": last_pipeline_run,
        "next_scheduled": get_next_scheduled_event() or _next_sunday_utc(),
        "rounds_completed": rounds_completed,
        "model_version": _newest_model_timestamp(),
        "jobs": jobs,
    }


def _standings_from_results() -> tuple[list[dict], list[dict]]:
    """Compute driver and constructor standings from the ingested race results file."""
    import pandas as pd

    results_file = Path(PATHS["data"]) / f"{CURRENT_SEASON}_race_results.csv"
    if not results_file.exists():
        raise FileNotFoundError(f"Race results file not found: {results_file}")

    df = pd.read_csv(results_file)
    df["finish_position"] = pd.to_numeric(df["finish_position"], errors="coerce")
    df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0.0)
    if "session_type" not in df.columns:
        df["session_type"] = "R"

    # Wins and podiums count only main race finishes, not sprint races
    race_df = df[df["session_type"] == "R"]

    # ── Driver standings ──────────────────────────────────────────────────────
    driver_meta = (
        df.sort_values("round", ascending=False)
        .groupby("driver_id")
        .first()
        .reset_index()[["driver_id", "driver_name", "driver_number", "constructor_id", "constructor_name"]]
    )

    driver_pts = df.groupby("driver_id")["points"].sum().reset_index(name="points")
    sprint_df = df[df["session_type"] == "S"]
    driver_sprint_pts = sprint_df.groupby("driver_id")["points"].sum().reset_index(name="sprint_points")
    driver_race_pts = race_df.groupby("driver_id")["points"].sum().reset_index(name="race_points")
    driver_wins = (
        race_df[race_df["finish_position"] == 1.0].groupby("driver_id").size().reset_index(name="wins")
    )
    driver_podiums = (
        race_df[race_df["finish_position"] <= 3.0].groupby("driver_id").size().reset_index(name="podiums")
    )

    drv = (
        driver_meta
        .merge(driver_pts, on="driver_id", how="left")
        .merge(driver_sprint_pts, on="driver_id", how="left")
        .merge(driver_race_pts, on="driver_id", how="left")
        .merge(driver_wins, on="driver_id", how="left")
        .merge(driver_podiums, on="driver_id", how="left")
    )
    drv["points"] = drv["points"].fillna(0.0)
    drv["sprint_points"] = drv["sprint_points"].fillna(0.0)
    drv["race_points"] = drv["race_points"].fillna(0.0)
    drv["wins"] = drv["wins"].fillna(0).astype(int)
    drv["podiums"] = drv["podiums"].fillna(0).astype(int)
    drv = drv.sort_values("points", ascending=False).reset_index(drop=True)
    drv["position"] = drv.index + 1

    drivers = []
    for _, row in drv.iterrows():
        drivers.append({
            "position": int(row["position"]),
            "driver_id": str(row["driver_id"]).lower(),
            "driver_name": str(row["driver_name"]) if pd.notna(row["driver_name"]) else "",
            "driver_number": int(row["driver_number"]) if pd.notna(row.get("driver_number")) else None,
            "constructor_id": str(row["constructor_id"]).lower() if pd.notna(row["constructor_id"]) else "",
            "constructor_name": str(row["constructor_name"]) if pd.notna(row["constructor_name"]) else "",
            "points": float(row["points"]),
            "sprint_points": float(row["sprint_points"]),
            "race_points": float(row["race_points"]),
            "wins": int(row["wins"]),
            "podiums": int(row["podiums"]),
        })

    # ── Constructor standings ─────────────────────────────────────────────────
    con_pts = df.groupby(["constructor_id", "constructor_name"])["points"].sum().reset_index(name="points")
    con_sprint_pts = sprint_df.groupby("constructor_id")["points"].sum().reset_index(name="sprint_points")
    con_race_pts = race_df.groupby("constructor_id")["points"].sum().reset_index(name="race_points")
    con_wins = (
        race_df[race_df["finish_position"] == 1.0]
        .groupby("constructor_id").size().reset_index(name="wins")
    )

    con = (
        con_pts
        .merge(con_sprint_pts, on="constructor_id", how="left")
        .merge(con_race_pts, on="constructor_id", how="left")
        .merge(con_wins, on="constructor_id", how="left")
    )
    con["sprint_points"] = con["sprint_points"].fillna(0.0)
    con["race_points"] = con["race_points"].fillna(0.0)
    con["wins"] = con["wins"].fillna(0).astype(int)
    con = con.sort_values("points", ascending=False).reset_index(drop=True)
    con["position"] = con.index + 1

    constructors = []
    for _, row in con.iterrows():
        constructors.append({
            "position": int(row["position"]),
            "constructor_id": str(row["constructor_id"]).lower() if pd.notna(row["constructor_id"]) else "",
            "constructor_name": str(row["constructor_name"]) if pd.notna(row["constructor_name"]) else "",
            "points": float(row["points"]),
            "sprint_points": float(row["sprint_points"]),
            "race_points": float(row["race_points"]),
            "wins": int(row["wins"]),
        })

    return drivers, constructors


@app.get("/api/standings/drivers")
def get_driver_standings() -> dict:
    try:
        drivers, _ = _standings_from_results()
        return {
            "drivers": drivers,
            "season": CURRENT_SEASON,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute driver standings: {exc}")


@app.get("/api/standings/constructors")
def get_constructor_standings() -> dict:
    try:
        _, constructors = _standings_from_results()
        return {
            "constructors": constructors,
            "season": CURRENT_SEASON,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute constructor standings: {exc}")


@app.get("/api/standings/drivers/sprints")
def get_sprint_driver_standings() -> dict:
    """Get driver standings based on sprint results only."""
    try:
        import pandas as pd

        results_file = Path(PATHS["data"]) / f"{CURRENT_SEASON}_race_results.csv"
        if not results_file.exists():
            raise FileNotFoundError(f"Race results file not found: {results_file}")

        df = pd.read_csv(results_file)
        df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0.0)
        if "session_type" not in df.columns:
            df["session_type"] = "R"

        # Filter for sprint races only
        sprint_df = df[df["session_type"] == "S"]
        if sprint_df.empty:
            return {
                "drivers": [],
                "season": CURRENT_SEASON,
                "message": "No sprint races completed yet",
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        driver_meta = (
            sprint_df.sort_values("round", ascending=False)
            .groupby("driver_id")
            .first()
            .reset_index()[["driver_id", "driver_name", "driver_number", "constructor_id", "constructor_name"]]
        )

        driver_pts = sprint_df.groupby("driver_id")["points"].sum().reset_index(name="points")
        driver_wins = (
            sprint_df[sprint_df["finish_position"] == 1.0].groupby("driver_id").size().reset_index(name="wins")
        )

        drv = (
            driver_meta
            .merge(driver_pts, on="driver_id", how="left")
            .merge(driver_wins, on="driver_id", how="left")
        )
        drv["points"] = drv["points"].fillna(0.0)
        drv["wins"] = drv["wins"].fillna(0).astype(int)
        drv = drv.sort_values("points", ascending=False).reset_index(drop=True)
        drv["position"] = drv.index + 1

        drivers = []
        for _, row in drv.iterrows():
            drivers.append({
                "position": int(row["position"]),
                "driver_id": str(row["driver_id"]).lower(),
                "driver_name": str(row["driver_name"]) if pd.notna(row["driver_name"]) else "",
                "driver_number": int(row["driver_number"]) if pd.notna(row.get("driver_number")) else None,
                "constructor_id": str(row["constructor_id"]).lower() if pd.notna(row["constructor_id"]) else "",
                "constructor_name": str(row["constructor_name"]) if pd.notna(row["constructor_name"]) else "",
                "points": float(row["points"]),
                "wins": int(row["wins"]),
            })

        return {
            "drivers": drivers,
            "season": CURRENT_SEASON,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute sprint driver standings: {exc}")


@app.get("/api/standings/constructors/sprints")
def get_sprint_constructor_standings() -> dict:
    """Get constructor standings based on sprint results only."""
    try:
        import pandas as pd

        results_file = Path(PATHS["data"]) / f"{CURRENT_SEASON}_race_results.csv"
        if not results_file.exists():
            raise FileNotFoundError(f"Race results file not found: {results_file}")

        df = pd.read_csv(results_file)
        df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0.0)
        if "session_type" not in df.columns:
            df["session_type"] = "R"

        # Filter for sprint races only
        sprint_df = df[df["session_type"] == "S"]
        if sprint_df.empty:
            return {
                "constructors": [],
                "season": CURRENT_SEASON,
                "message": "No sprint races completed yet",
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

        con_pts = sprint_df.groupby(["constructor_id", "constructor_name"])["points"].sum().reset_index(name="points")
        con_wins = (
            sprint_df[sprint_df["finish_position"] == 1.0]
            .groupby("constructor_id").size().reset_index(name="wins")
        )

        con = con_pts.merge(con_wins, on="constructor_id", how="left")
        con["wins"] = con["wins"].fillna(0).astype(int)
        con = con.sort_values("points", ascending=False).reset_index(drop=True)
        con["position"] = con.index + 1

        constructors = []
        for _, row in con.iterrows():
            constructors.append({
                "position": int(row["position"]),
                "constructor_id": str(row["constructor_id"]).lower() if pd.notna(row["constructor_id"]) else "",
                "constructor_name": str(row["constructor_name"]) if pd.notna(row["constructor_name"]) else "",
                "points": float(row["points"]),
                "wins": int(row["wins"]),
            })

        return {
            "constructors": constructors,
            "season": CURRENT_SEASON,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to compute sprint constructor standings: {exc}")


@app.get("/api/race-results")
def get_race_results() -> dict:
    """Fetch race results for the current season"""
    try:
        import pandas as pd
        
        results_file = Path(PATHS["data"]) / f"{CURRENT_SEASON}_race_results.csv"
        if not results_file.exists():
            raise HTTPException(status_code=404, detail="Race results file not found")
        
        df = pd.read_csv(results_file)
        if "session_type" not in df.columns:
            df["session_type"] = "R"

        result_cols = ['driver_name', 'constructor_name', 'finish_position', 'points']

        # Group by round — each round may have a main race row and a sprint row
        races = []
        for round_num in sorted(df['round'].unique()):
            round_data = df[df['round'] == round_num]
            race_name = round_data['race_name'].iloc[0]

            race_rows = round_data[round_data['session_type'] == 'R']
            sprint_rows = round_data[round_data['session_type'] == 'S']

            top_10 = race_rows.nsmallest(10, 'finish_position')[result_cols].to_dict('records') if not race_rows.empty else []
            winners = race_rows[race_rows['finish_position'] == 1.0]

            sprint_top_8 = sprint_rows.nsmallest(8, 'finish_position')[result_cols].to_dict('records') if not sprint_rows.empty else []

            races.append({
                "round": int(round_num),
                "name": race_name,
                "winner": winners.iloc[0]['driver_name'] if not winners.empty else None,
                "podium": top_10,
                "sprint_podium": sprint_top_8,
                "is_sprint": len(sprint_rows) > 0,
                "status": "completed",
            })
        
        return {
            "season": CURRENT_SEASON,
            "races": races,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch race results: {str(e)}")


def _kill_process_tree(pid: int) -> None:
    import psutil
    try:
        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def _run_pipeline_background(run_id: int, script_path: Path, project_root: Path) -> None:
    log_dir = Path(PATHS["data"]) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"pipeline_all_{ts}.log"

    status = "failed"
    error: str | None = None

    try:
        log_file = open(log_path, "w", encoding="utf-8")  # noqa: WPS515
        try:
            proc = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(project_root),
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        finally:
            log_file.close()

        update_pipeline_pid(run_id, proc.pid)

        try:
            proc.wait(timeout=PIPELINE_TIMEOUT_SECONDS)
            if proc.returncode == 0:
                status = "success"
            else:
                status = "failed"
                error = f"exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            _kill_process_tree(proc.pid)
            status = "timeout"
            error = f"Pipeline killed after {PIPELINE_TIMEOUT_SECONDS}s timeout"

    except OSError as exc:
        status = "failed"
        error = str(exc)

    predictions_dir = Path(PATHS["predictions"])
    rounds_completed = (
        len(list(predictions_dir.glob("round_*_postquali_predictions.json")))
        if predictions_dir.exists()
        else 0
    )
    log_pipeline_finish(run_id, status, rounds_completed, error_message=error)


@app.post("/api/refresh")
async def refresh_pipeline(background_tasks: BackgroundTasks) -> dict:
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "run_pipeline.py"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail=f"Pipeline script not found: {script_path}")

    run_id = log_pipeline_start()
    background_tasks.add_task(_run_pipeline_background, run_id, script_path, project_root)

    return {
        "status": "pipeline started",
        "run_id": run_id,
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


@app.post("/api/admin/trigger/{job_name}")
@app.post("/api/admin/trigger-job/{job_name}")
async def trigger_admin_job(job_name: str, round: int | None = None, race_name: str | None = None) -> dict:
    if job_name not in ADMIN_TRIGGERABLE_JOBS:
        raise HTTPException(status_code=404, detail=f"Unknown job '{job_name}'")
    try:
        job_id = trigger_job_now(job_name=job_name, round_num=round, race_name=race_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "job_scheduled",
        "job": job_name,
        "job_id": job_id,
        "round": round,
        "race_name": race_name,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/predictions/history")
def get_predictions_history() -> list:
    """Fetch all historical predictions from database"""
    try:
        from app.database import SessionLocal, PredictionLog
        from sqlalchemy import select
        
        with SessionLocal() as session:
            stmt = select(PredictionLog).order_by(PredictionLog.created_at.desc())
            logs = session.execute(stmt).scalars().all()
            
            predictions = []
            for log in logs:
                predictions.append({
                    "round": log.round,
                    "race_name": log.race_name,
                    "driver_id": log.driver_id,
                    "constructor_id": log.constructor_id,
                    "type": log.prediction_type,
                    "predicted_pos": log.predicted_pos,
                    "final_score": log.final_score,
                    "alpha": log.alpha,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                })
            
            return predictions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch prediction history: {str(e)}")


# ════════════════════════════════════════════════════════════════════════════════════
# SPA ROUTING - Serve React frontend from dist/
# Mount static files and setup SPA fallback to index.html
# Must be LAST to avoid shadowing API routes
# ════════════════════════════════════════════════════════════════════════════════════

FRONTEND_BUILD_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if FRONTEND_BUILD_DIR.exists() and (FRONTEND_BUILD_DIR / "index.html").exists():
    # Serve static assets with long-lived cache
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_BUILD_DIR / "assets"), html=False),
        name="assets"
    )
    
    # Catch-all route for SPA: any non-API request returns index.html
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def catch_all_spa(full_path: str):
        # Don't serve index.html for static files or known non-SPA paths
        if full_path.startswith("assets/") or full_path in ("favicon.svg", "favicon.ico", "icons.svg"):
            # Let StaticFiles handle these
            raise HTTPException(status_code=404)
        # Serve index.html for all other paths (SPA routing)
        index_path = FRONTEND_BUILD_DIR / "index.html"
        return index_path.read_text()
else:
    # Fallback if dist doesn't exist
    @app.get("/", response_class=HTMLResponse)
    def landing_page_fallback() -> str:
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
            <p><strong>⚠️ Frontend build not found</strong></p>
            <p>Build the frontend first by running:</p>
            <code>cd frontend && npm run build</code>
            <h3>API Links (backend only)</h3>
            <ul>
                <li><a href="/health">/health</a></li>
                <li><a href="/ready">/ready</a></li>
                <li><a href="/api/calendar">/api/calendar</a></li>
                <li><a href="/api/metrics">/api/metrics</a></li>
                <li><a href="/api/predictions/next">/api/predictions/next</a></li>
            </ul>
        </div>
    </body>
</html>
"""
