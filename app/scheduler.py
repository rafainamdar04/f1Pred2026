from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.database import log_pipeline_finish, log_pipeline_start
from app.status import write_status_file
from config.settings import CURRENT_SEASON, PATHS, SCHEDULER_ENABLED

scheduler = BackgroundScheduler(timezone=timezone.utc)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _count_rounds_completed() -> int:
    predictions_dir = Path(PATHS["predictions"])
    if not predictions_dir.exists():
        return 0
    return len(list(predictions_dir.glob("round_*_predictions.json")))


def _next_round_info() -> tuple[int, str]:
    processed_path = _project_root() / PATHS["processed"] / f"{CURRENT_SEASON}_features.csv"
    if not processed_path.exists():
        return 1, "Round 1"
    import pandas as pd

    df = pd.read_csv(processed_path)
    if df.empty:
        return 1, "Round 1"
    max_round = int(df["round"].max())
    next_round = max_round + 1
    race_name = f"Round {next_round}"
    return next_round, race_name


def run_full_pipeline() -> None:
    run_id = log_pipeline_start()
    project_root = _project_root()
    script_path = project_root / "scripts" / "run_pipeline.py"

    status = "failed"
    error_message = None

    if not script_path.exists():
        error_message = f"Pipeline script not found: {script_path}"
    else:
        try:
            result = subprocess.run(
                [sys.executable, str(script_path), "--mode", "both"],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                status = "success"
            else:
                error_message = (result.stderr or result.stdout or "").strip()
                if not error_message:
                    error_message = "Pipeline failed with non-zero exit code."
        except OSError as exc:
            error_message = str(exc)

    rounds_completed = _count_rounds_completed()
    log_pipeline_finish(run_id, status, rounds_completed, error_message=error_message)
    write_status_file(datetime.now(timezone.utc), status, rounds_completed)


def run_data_refresh() -> None:
    project_root = _project_root()
    script_path = project_root / "scripts" / "hourly_fastf1_refresh.py"
    if not script_path.exists():
        return
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )


def run_prequali_predictions() -> None:
    project_root = _project_root()
    script_path = project_root / "scripts" / "predict_prequali.py"
    if not script_path.exists():
        return
    round_num, race_name = _next_round_info()
    subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--round",
            str(round_num),
            "--race-name",
            race_name,
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )


def run_postquali_predictions() -> None:
    project_root = _project_root()
    grid_script = project_root / "scripts" / "export_latest_grid.py"
    script_path = project_root / "scripts" / "predict_postquali.py"
    if not script_path.exists():
        return
    grid_file = project_root / PATHS["data"] / "latest_grid.csv"
    if grid_script.exists():
        subprocess.run(
            [sys.executable, str(grid_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
    round_num, race_name = _next_round_info()
    args = [
        sys.executable,
        str(script_path),
        "--round",
        str(round_num),
        "--race-name",
        race_name,
        "--grid-file",
        str(grid_file),
    ]
    if not grid_file.exists():
        return
    subprocess.run(
        args,
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )


def start_scheduler() -> None:
    if not SCHEDULER_ENABLED:
        return
    if scheduler.running:
        return

    scheduler.add_job(
        run_prequali_predictions,
        CronTrigger(day_of_week="thu", hour=12, minute=0),
        id="thursday_prequali",
        replace_existing=True,
    )
    scheduler.add_job(
        run_postquali_predictions,
        CronTrigger(day_of_week="sat", hour=18, minute=0),
        id="saturday_postquali",
        replace_existing=True,
    )
    scheduler.add_job(
        run_full_pipeline,
        CronTrigger(day_of_week="sun", hour=20, minute=0),
        id="sunday_full_retrain",
        replace_existing=True,
    )
    scheduler.add_job(
        run_data_refresh,
        IntervalTrigger(hours=1),
        id="hourly_refresh",
        replace_existing=True,
    )
    scheduler.start()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def trigger_full_pipeline_now() -> str:
    if SCHEDULER_ENABLED:
        if not scheduler.running:
            scheduler.start()
        job = scheduler.add_job(run_full_pipeline, trigger="date")
        return job.id

    Thread(target=run_full_pipeline, daemon=True).start()
    return "manual-run"
