from __future__ import annotations

import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
import subprocess
import sys
from threading import Thread
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pandas as pd

from app.database import (
    log_job_finish,
    log_job_start,
    log_model_metrics,
    log_predictions_from_file,
    log_session_ingestion,
    upsert_race_results,
    upsert_session_data,
)
from app.status import write_status_file
from config.settings import CURRENT_SEASON, PATHS, SCHEDULER_ENABLED

scheduler = BackgroundScheduler(timezone=timezone.utc)

QUALI_RETRY_MINUTES = 15
QUALI_MAX_RETRIES = 3
RACE_RETRY_MINUTES = 15
RACE_MAX_RETRIES = 3
PREDICTION_RETRY_MINUTES = 15
PREDICTION_MAX_RETRIES = 3


class DataNotReadyError(RuntimeError):
    pass


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _count_rounds_completed() -> int:
    predictions_dir = _project_root() / PATHS["predictions"]
    if not predictions_dir.exists():
        return 0
    return len(list(predictions_dir.glob("round_*_postquali_predictions.json")))


def _run_script(args: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            args,
            cwd=str(_project_root()),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, str(exc)

    if result.returncode == 0:
        return True, (result.stdout or "").strip()

    message = (result.stderr or result.stdout or "").strip() or "Command failed"
    return False, message


def _parse_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _calendar_path() -> Path:
    return _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_calendar.json"


def _refresh_calendar_cache() -> list[dict]:
    import fastf1

    schedule = fastf1.get_event_schedule(CURRENT_SEASON)
    races: list[dict[str, Any]] = []

    for _, row in schedule.iterrows():
        round_num = row.get("RoundNumber")
        event_name = row.get("EventName")
        if pd.isna(round_num) or pd.isna(event_name) or int(round_num) <= 0:
            continue

        quali_start = _parse_utc(row.get("Session4DateUtc"))
        race_start = _parse_utc(row.get("Session5DateUtc"))
        event_date = _parse_utc(row.get("EventDate"))
        date_value = (event_date or race_start or quali_start)

        event_format = str(row.get("EventFormat", "conventional")).lower()
        is_sprint = event_format in ("sprint_shootout", "sprint")
        sprint_start = _parse_utc(row.get("Session3DateUtc")) if is_sprint else None

        races.append(
            {
                "round": int(round_num),
                "name": str(event_name),
                "short": str(event_name)[:3].upper(),
                "date": date_value.date().isoformat() if date_value else None,
                "is_sprint": is_sprint,
                "sprint_start_utc": sprint_start.isoformat() if sprint_start else None,
                "sprint_end_utc": (sprint_start + timedelta(hours=1)).isoformat() if sprint_start else None,
                "quali_start_utc": quali_start.isoformat() if quali_start else None,
                "quali_end_utc": (quali_start + timedelta(hours=1)).isoformat() if quali_start else None,
                "race_start_utc": race_start.isoformat() if race_start else None,
                "race_end_utc": (race_start + timedelta(hours=2)).isoformat() if race_start else None,
            }
        )

    races.sort(key=lambda item: int(item["round"]))
    payload = {"season": CURRENT_SEASON, "races": races}
    path = _calendar_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return races


def _load_calendar() -> list[dict]:
    path = _calendar_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("races"), list):
                races = payload["races"]
                if races:
                    return races
        except (ValueError, json.JSONDecodeError):
            pass

    try:
        return _refresh_calendar_cache()
    except Exception:
        return []


def _next_race_weekend(now: datetime | None = None) -> dict | None:
    now_utc = now or datetime.now(timezone.utc)
    races = _load_calendar()
    candidates: list[tuple[datetime, dict]] = []

    for race in races:
        race_end = _parse_utc(race.get("race_end_utc"))
        race_start = _parse_utc(race.get("race_start_utc"))
        anchor = race_end or race_start
        if anchor and anchor > now_utc:
            candidates.append((anchor, race))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def _write_status(status: str) -> None:
    write_status_file(datetime.now(timezone.utc), status, _count_rounds_completed())


def run_prequali(round_num: int, race_name: str, retry_count: int = 0) -> None:
    print(f"[run_prequali] start round={round_num} attempt={retry_count + 1}")
    run_id = log_job_start("run_prequali", round_num)

    failed_msg: str | None = None

    ok_build, err_build = _run_script(
        [sys.executable, str(_project_root() / "scripts" / "build_processed_features.py")]
    )
    if not ok_build:
        failed_msg = f"feature rebuild: {err_build}"
    else:
        ok, out = _run_script(
            [
                sys.executable,
                str(_project_root() / "scripts" / "predict_prequali.py"),
                "--round",
                str(round_num),
                "--race-name",
                race_name,
            ]
        )
        if ok:
            print(f"[run_prequali] success round={round_num}")
            prediction_file = _project_root() / PATHS["predictions"] / f"round_{round_num}_prequali_predictions.json"
            log_predictions_from_file(prediction_file, "pre")
            _write_status("success")
            log_job_finish(run_id, "success", error_message=out or None)
            return
        failed_msg = out

    if retry_count < PREDICTION_MAX_RETRIES:
        next_attempt = retry_count + 1
        print(f"[run_prequali] failed round={round_num}, retry {next_attempt}/{PREDICTION_MAX_RETRIES} in {PREDICTION_RETRY_MINUTES}min")
        scheduler.add_job(
            run_prequali,
            trigger="date",
            id=f"retry_run_prequali_r{round_num}_{next_attempt}",
            run_date=datetime.now(timezone.utc) + timedelta(minutes=PREDICTION_RETRY_MINUTES),
            kwargs={"round_num": round_num, "race_name": race_name, "retry_count": next_attempt},
            replace_existing=True,
        )
        log_job_finish(run_id, "retry", error_message=failed_msg)
        return

    print(f"[run_prequali] FAILED round={round_num} max retries exceeded: {failed_msg}")
    log_job_finish(run_id, "failed", error_message=failed_msg)
    _write_status("failed")


def run_postquali(round_num: int, race_name: str, retry_count: int = 0) -> None:
    print(f"[run_postquali] start round={round_num} attempt={retry_count + 1}")
    run_id = log_job_start("run_postquali", round_num)
    grid_script = _project_root() / "scripts" / "export_latest_grid.py"
    grid_file = _project_root() / PATHS["data"] / "latest_grid.csv"

    failed_msg: str | None = None

    ok_grid, grid_err = _run_script(
        [
            sys.executable,
            str(grid_script),
            "--round",
            str(round_num),
            "--output",
            str(grid_file),
        ]
    )
    if not ok_grid:
        failed_msg = f"grid export: {grid_err}"
    else:
        ok, out = _run_script(
            [
                sys.executable,
                str(_project_root() / "scripts" / "predict_postquali.py"),
                "--round",
                str(round_num),
                "--race-name",
                race_name,
                "--grid-file",
                str(grid_file),
            ]
        )
        if ok:
            print(f"[run_postquali] success round={round_num}")
            prediction_file = _project_root() / PATHS["predictions"] / f"round_{round_num}_postquali_predictions.json"
            log_predictions_from_file(prediction_file, "post")
            _write_status("success")
            log_job_finish(run_id, "success", error_message=out or None)
            return
        failed_msg = out

    if retry_count < PREDICTION_MAX_RETRIES:
        next_attempt = retry_count + 1
        print(f"[run_postquali] failed round={round_num}, retry {next_attempt}/{PREDICTION_MAX_RETRIES} in {PREDICTION_RETRY_MINUTES}min")
        scheduler.add_job(
            run_postquali,
            trigger="date",
            id=f"retry_run_postquali_r{round_num}_{next_attempt}",
            run_date=datetime.now(timezone.utc) + timedelta(minutes=PREDICTION_RETRY_MINUTES),
            kwargs={"round_num": round_num, "race_name": race_name, "retry_count": next_attempt},
            replace_existing=True,
        )
        log_job_finish(run_id, "retry", error_message=failed_msg)
        return

    print(f"[run_postquali] FAILED round={round_num} max retries exceeded: {failed_msg}")
    log_job_finish(run_id, "failed", error_message=failed_msg)
    _write_status("failed")


_CSV_COLUMN_DEFAULTS: dict[str, Any] = {
    "session_type": "R",
}


def _merge_csv_idempotent(path: Path, new_rows: pd.DataFrame, key_cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = pd.read_csv(path)
        # Backfill any key columns that didn't exist in the stored CSV
        for col in key_cols:
            if col not in existing.columns and col in _CSV_COLUMN_DEFAULTS:
                existing[col] = _CSV_COLUMN_DEFAULTS[col]
        merged = pd.concat([existing, new_rows], ignore_index=True)
    else:
        merged = new_rows.copy()

    merged = merged.drop_duplicates(subset=key_cols, keep="last")
    merged.to_csv(path, index=False)


def ingest_quali(round_num: int, race_name: str, retry_count: int = 0) -> None:
    print(f"[ingest_quali] start round={round_num} attempt={retry_count + 1}")
    run_id = log_job_start("ingest_quali", round_num)
    try:
        from scripts.fastf1_scraper import FastF1Scraper

        scraper = FastF1Scraper(output_dir=PATHS["data"])
        qual_df = scraper.get_qualifying_results(CURRENT_SEASON, round_num)
        if qual_df is None or qual_df.empty:
            raise DataNotReadyError("Qualifying data not available yet from FastF1")

        qual_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_qualifying.csv"
        _merge_csv_idempotent(qual_path, qual_df, ["season", "round", "driver_id"])
        upsert_session_data(round_num, "Q", qual_df)

        verify_err = _verify_quali_ingestion(round_num, qual_path)
        if verify_err:
            print(f"[ingest_quali] VERIFICATION FAILED round={round_num}: {verify_err}")
            log_job_finish(run_id, "failed", error_message=verify_err)
            _write_status("failed")
            return

        print(f"[ingest_quali] success round={round_num} rows={len(qual_df)}")
        log_job_finish(run_id, "success")
        run_postquali(round_num, race_name)
        return
    except DataNotReadyError as exc:
        if retry_count < QUALI_MAX_RETRIES:
            next_attempt = retry_count + 1
            print(f"[ingest_quali] not ready round={round_num}, retry {next_attempt}/{QUALI_MAX_RETRIES} in {QUALI_RETRY_MINUTES}min")
            scheduler.add_job(
                ingest_quali,
                trigger="date",
                id=f"retry_ingest_quali_r{round_num}_{next_attempt}",
                run_date=datetime.now(timezone.utc) + timedelta(minutes=QUALI_RETRY_MINUTES),
                kwargs={"round_num": round_num, "race_name": race_name, "retry_count": next_attempt},
                replace_existing=True,
            )
            log_job_finish(run_id, "retry", error_message=str(exc))
            return
        print(f"[ingest_quali] FAILED round={round_num} max retries exceeded: {exc}")
        log_job_finish(run_id, "failed", error_message=str(exc))
        _write_status("failed")
    except Exception as exc:
        print(f"[ingest_quali] FAILED round={round_num}: {exc}")
        log_job_finish(run_id, "failed", error_message=str(exc))
        _write_status("failed")


SPRINT_RETRY_MINUTES = 15
SPRINT_MAX_RETRIES = 3


def ingest_sprint(round_num: int, race_name: str, retry_count: int = 0) -> None:
    print(f"[ingest_sprint] start round={round_num} attempt={retry_count + 1}")
    run_id = log_job_start("ingest_sprint", round_num)
    try:
        from scripts.fastf1_scraper import FastF1Scraper

        scraper = FastF1Scraper(output_dir=PATHS["data"])
        sprint_df = scraper.get_sprint_results(CURRENT_SEASON, round_num)
        if sprint_df is None or sprint_df.empty:
            raise DataNotReadyError("Sprint results not available yet from FastF1")

        race_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_race_results.csv"
        _merge_csv_idempotent(race_path, sprint_df, ["season", "round", "driver_id", "session_type"])
        upsert_session_data(round_num, "S", sprint_df)
        upsert_race_results(round_num, sprint_df, session_type="S")

        verify_err = _verify_sprint_ingestion(round_num, race_path)
        if verify_err:
            print(f"[ingest_sprint] VERIFICATION FAILED round={round_num}: {verify_err}")
            log_job_finish(run_id, "failed", error_message=verify_err)
            _write_status("failed")
            return

        pts = float(pd.to_numeric(sprint_df.get("points", pd.Series([], dtype=float)), errors="coerce").fillna(0).sum())
        log_session_ingestion(round_num, "S", len(sprint_df), pts)
        print(f"[ingest_sprint] success round={round_num} rows={len(sprint_df)}")
        log_job_finish(run_id, "success")
        return
    except DataNotReadyError as exc:
        if retry_count < SPRINT_MAX_RETRIES:
            next_attempt = retry_count + 1
            print(f"[ingest_sprint] not ready round={round_num}, retry {next_attempt}/{SPRINT_MAX_RETRIES} in {SPRINT_RETRY_MINUTES}min")
            scheduler.add_job(
                ingest_sprint,
                trigger="date",
                id=f"retry_ingest_sprint_r{round_num}_{next_attempt}",
                run_date=datetime.now(timezone.utc) + timedelta(minutes=SPRINT_RETRY_MINUTES),
                kwargs={"round_num": round_num, "race_name": race_name, "retry_count": next_attempt},
                replace_existing=True,
            )
            log_job_finish(run_id, "retry", error_message=str(exc))
            return
        print(f"[ingest_sprint] FAILED round={round_num} max retries exceeded: {exc}")
        log_job_finish(run_id, "failed", error_message=str(exc))
        _write_status("failed")
    except Exception as exc:
        print(f"[ingest_sprint] FAILED round={round_num}: {exc}")
        log_job_finish(run_id, "failed", error_message=str(exc))
        _write_status("failed")


def score_predictions(round_num: int, retry_count: int = 0) -> None:
    print(f"[score_predictions] start round={round_num} attempt={retry_count + 1}")
    run_id = log_job_start("score_predictions", round_num)

    failed_msg: str | None = None

    ok_build, err_build = _run_script([sys.executable, str(_project_root() / "scripts" / "build_processed_features.py")])
    if not ok_build:
        failed_msg = f"build_features: {err_build}"
    else:
        ok_eval, err_eval = _run_script([sys.executable, str(_project_root() / "scripts" / "evaluate_hybrid.py")])
        if not ok_eval:
            failed_msg = f"evaluate: {err_eval}"
        else:
            metrics_path = _project_root() / PATHS["metrics"] / "metrics_summary.json"
            if metrics_path.exists():
                try:
                    payload = json.loads(metrics_path.read_text(encoding="utf-8"))
                    rounds = payload.get("rounds", []) if isinstance(payload, dict) else []
                    for row in rounds:
                        if int(row.get("round", -1)) == int(round_num):
                            post = row.get("postquali", {})
                            log_model_metrics(
                                round_num=round_num,
                                top3_hit_rate=float(post.get("top3_hit", 0.0)),
                                ndcg=float(post.get("ndcg", 0.0)),
                                mae=float(post.get("mae", 0.0)),
                                alpha=float(post.get("alpha", 0.0)),
                            )
                            break
                except Exception:
                    pass
            print(f"[score_predictions] success round={round_num}")
            log_job_finish(run_id, "success")
            return

    if retry_count < PREDICTION_MAX_RETRIES:
        next_attempt = retry_count + 1
        print(f"[score_predictions] failed round={round_num}, retry {next_attempt}/{PREDICTION_MAX_RETRIES} in {PREDICTION_RETRY_MINUTES}min")
        scheduler.add_job(
            score_predictions,
            trigger="date",
            id=f"retry_score_predictions_r{round_num}_{next_attempt}",
            run_date=datetime.now(timezone.utc) + timedelta(minutes=PREDICTION_RETRY_MINUTES),
            kwargs={"round_num": round_num, "retry_count": next_attempt},
            replace_existing=True,
        )
        log_job_finish(run_id, "retry", error_message=failed_msg)
        return

    print(f"[score_predictions] FAILED round={round_num} max retries exceeded: {failed_msg}")
    log_job_finish(run_id, "failed", error_message=failed_msg)


def retrain_model(round_num: int) -> None:
    print(f"[retrain_model] start round={round_num}")
    run_id = log_job_start("retrain_model", round_num)
    ok_pre, err_pre = _run_script([sys.executable, str(_project_root() / "scripts" / "train_prequali_model.py")])
    if not ok_pre:
        print(f"[retrain_model] FAILED train_prequali round={round_num}: {err_pre}")
        log_job_finish(run_id, "failed", error_message=f"prequali: {err_pre}")
        _write_status("failed")
        return

    ok_post, err_post = _run_script([sys.executable, str(_project_root() / "scripts" / "train_postquali_model.py")])
    if not ok_post:
        print(f"[retrain_model] FAILED train_postquali round={round_num}: {err_post}")
        log_job_finish(run_id, "failed", error_message=f"postquali: {err_post}")
        _write_status("failed")
        return

    print(f"[retrain_model] success round={round_num}")
    log_job_finish(run_id, "success")
    _write_status("success")


def ingest_results(round_num: int, race_name: str, retry_count: int = 0) -> None:
    print(f"[ingest_results] start round={round_num} attempt={retry_count + 1}")
    run_id = log_job_start("ingest_results", round_num)
    try:
        from scripts.fastf1_scraper import FastF1Scraper

        scraper = FastF1Scraper(output_dir=PATHS["data"])
        race_df = scraper.get_race_results(CURRENT_SEASON, round_num)
        if race_df is None or race_df.empty:
            raise DataNotReadyError("Race results not available yet from FastF1")

        race_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_race_results.csv"
        _merge_csv_idempotent(race_path, race_df, ["season", "round", "driver_id", "session_type"])
        upsert_session_data(round_num, "R", race_df)
        upsert_race_results(round_num, race_df, session_type="R")

        verify_err = _verify_race_ingestion(round_num, race_path)
        if verify_err:
            print(f"[ingest_results] VERIFICATION FAILED round={round_num}: {verify_err}")
            log_job_finish(run_id, "failed", error_message=verify_err)
            _write_status("failed")
            return

        pts = float(pd.to_numeric(race_df.get("points", pd.Series([], dtype=float)), errors="coerce").fillna(0).sum())
        log_session_ingestion(round_num, "R", len(race_df), pts)
        print(f"[ingest_results] success round={round_num} rows={len(race_df)}")
        log_job_finish(run_id, "success")
        score_predictions(round_num)
        retrain_model(round_num)
        return
    except DataNotReadyError as exc:
        if retry_count < RACE_MAX_RETRIES:
            next_attempt = retry_count + 1
            print(f"[ingest_results] not ready round={round_num}, retry {next_attempt}/{RACE_MAX_RETRIES} in {RACE_RETRY_MINUTES}min")
            scheduler.add_job(
                ingest_results,
                trigger="date",
                id=f"retry_ingest_results_r{round_num}_{next_attempt}",
                run_date=datetime.now(timezone.utc) + timedelta(minutes=RACE_RETRY_MINUTES),
                kwargs={"round_num": round_num, "race_name": race_name, "retry_count": next_attempt},
                replace_existing=True,
            )
            log_job_finish(run_id, "retry", error_message=str(exc))
            return
        print(f"[ingest_results] FAILED round={round_num} max retries exceeded: {exc}")
        log_job_finish(run_id, "failed", error_message=str(exc))
        _write_status("failed")
    except Exception as exc:
        print(f"[ingest_results] FAILED round={round_num}: {exc}")
        log_job_finish(run_id, "failed", error_message=str(exc))
        _write_status("failed")


def _weekend_schedule_times(
    race: dict,
) -> tuple[datetime, datetime | None, datetime, datetime] | None:
    """Return (prequali_run, sprint_ingest_run_or_None, quali_ingest_run, race_ingest_run)."""
    race_start = _parse_utc(race.get("race_start_utc"))
    quali_end = _parse_utc(race.get("quali_end_utc"))
    race_end = _parse_utc(race.get("race_end_utc"))
    race_date = race_start.date() if race_start else None
    if race_date is None:
        date_str = race.get("date")
        if not date_str:
            return None
        parsed = datetime.fromisoformat(f"{date_str}T00:00:00+00:00")
        race_date = parsed.date()

    prequali_date = race_date - timedelta(days=3)
    prequali_run = datetime.combine(prequali_date, time(hour=12, minute=0, tzinfo=timezone.utc))

    if not quali_end:
        return None
    if not race_end:
        race_end = (race_start + timedelta(hours=2)) if race_start else None
    if not race_end:
        return None

    sprint_ingest_run = None
    if race.get("is_sprint"):
        sprint_end = _parse_utc(race.get("sprint_end_utc"))
        if sprint_end:
            sprint_ingest_run = sprint_end + timedelta(minutes=90)

    quali_ingest_run = quali_end + timedelta(minutes=30)
    # 3-hour delay to allow post-race penalties/DSQs to be applied
    race_ingest_run = race_end + timedelta(hours=3)
    return prequali_run, sprint_ingest_run, quali_ingest_run, race_ingest_run


def schedule_next_race_weekend() -> None:
    try:
        _refresh_calendar_cache()
        print("[schedule_next_race_weekend] calendar cache refreshed")
    except Exception as exc:
        print(f"[schedule_next_race_weekend] calendar refresh failed, using cached: {exc}")

    race = _next_race_weekend()
    if race is None:
        return

    times = _weekend_schedule_times(race)
    if times is None:
        return
    prequali_run, sprint_ingest_run, quali_ingest_run, race_ingest_run = times

    round_num = int(race["round"])
    race_name = str(race["name"])

    scheduler.add_job(
        run_prequali,
        trigger="date",
        id=f"weekend_prequali_r{round_num}",
        run_date=prequali_run,
        kwargs={"round_num": round_num, "race_name": race_name},
        replace_existing=True,
    )
    if sprint_ingest_run is not None:
        scheduler.add_job(
            ingest_sprint,
            trigger="date",
            id=f"weekend_ingest_sprint_r{round_num}",
            run_date=sprint_ingest_run,
            kwargs={"round_num": round_num, "race_name": race_name},
            replace_existing=True,
        )
    scheduler.add_job(
        ingest_quali,
        trigger="date",
        id=f"weekend_ingest_quali_r{round_num}",
        run_date=quali_ingest_run,
        kwargs={"round_num": round_num, "race_name": race_name},
        replace_existing=True,
    )
    scheduler.add_job(
        ingest_results,
        trigger="date",
        id=f"weekend_ingest_results_r{round_num}",
        run_date=race_ingest_run,
        kwargs={"round_num": round_num, "race_name": race_name},
        replace_existing=True,
    )


RECOVERY_WINDOW_HOURS = 6


def _round_in_csv(path: Path, round_num: int) -> bool:
    if not path.exists():
        return False
    try:
        df = pd.read_csv(path, usecols=["round"])
        return int(round_num) in df["round"].astype(int).values
    except Exception:
        return False


def _round_session_in_csv(path: Path, round_num: int, session_type: str) -> bool:
    """Check if a specific round+session_type combination exists in the CSV."""
    if not path.exists():
        return False
    try:
        df = pd.read_csv(path)
        if "session_type" not in df.columns:
            # Legacy CSV with no session_type — treat all rows as 'R'
            if session_type == "R":
                return int(round_num) in df["round"].astype(int).values
            return False
        mask = (df["round"].astype(int) == int(round_num)) & (df["session_type"] == session_type)
        return mask.any()
    except Exception:
        return False


def _verify_race_ingestion(round_num: int, csv_path: Path) -> str | None:
    """Return an error string if post-race data looks wrong, None if OK."""
    try:
        df = pd.read_csv(csv_path)
        if "session_type" in df.columns:
            df = df[(df["round"].astype(int) == int(round_num)) & (df["session_type"] == "R")]
        else:
            df = df[df["round"].astype(int) == int(round_num)]
        row_count = len(df)
        if row_count != 22:
            return f"Round {round_num} race: expected 22 drivers, got {row_count}"
        total_pts = pd.to_numeric(df["points"], errors="coerce").fillna(0).sum()
        if total_pts not in (101, 102):
            return f"Round {round_num} race: expected 101 or 102 total points, got {total_pts}"
        return None
    except Exception as exc:
        return f"Round {round_num} race verification error: {exc}"


def _verify_sprint_ingestion(round_num: int, csv_path: Path) -> str | None:
    """Return an error string if sprint data looks wrong, None if OK."""
    try:
        df = pd.read_csv(csv_path)
        if "session_type" not in df.columns:
            return f"Round {round_num} sprint: CSV missing session_type column"
        df = df[(df["round"].astype(int) == int(round_num)) & (df["session_type"] == "S")]
        row_count = len(df)
        if row_count != 22:
            return f"Round {round_num} sprint: expected 22 drivers, got {row_count}"
        total_pts = pd.to_numeric(df["points"], errors="coerce").fillna(0).sum()
        if total_pts != 36:
            return f"Round {round_num} sprint: expected 36 total points, got {total_pts}"
        return None
    except Exception as exc:
        return f"Round {round_num} sprint verification error: {exc}"


def _verify_quali_ingestion(round_num: int, quali_path: Path) -> str | None:
    """Return an error string if quali data looks thin, None if OK."""
    try:
        df = pd.read_csv(quali_path)
        if "round" in df.columns:
            df = df[df["round"].astype(int) == int(round_num)]
        pos_col = "grid_position" if "grid_position" in df.columns else "qualifying_position" if "qualifying_position" in df.columns else None
        if pos_col is None:
            return None
        has_position = int(df[pos_col].notna().sum())
        if has_position < 20:
            return f"Round {round_num} quali: only {has_position} drivers have a recorded position (expected 20+)"
        return None
    except Exception as exc:
        return f"Round {round_num} quali verification error: {exc}"


def _recover_missed_jobs() -> None:
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(hours=RECOVERY_WINDOW_HOURS)
    races = _load_calendar()

    for race in races:
        round_num = int(race["round"])
        race_name = str(race["name"])
        quali_end = _parse_utc(race.get("quali_end_utc"))
        race_end = _parse_utc(race.get("race_end_utc"))
        sprint_end = _parse_utc(race.get("sprint_end_utc")) if race.get("is_sprint") else None

        if sprint_end and cutoff <= sprint_end < now_utc:
            results_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_race_results.csv"
            if not _round_session_in_csv(results_path, round_num, "S"):
                print(f"[recovery] sprint not ingested for round={round_num}, triggering ingest_sprint")
                Thread(
                    target=ingest_sprint,
                    kwargs={"round_num": round_num, "race_name": race_name},
                    daemon=True,
                ).start()

        if quali_end and cutoff <= quali_end < now_utc:
            qual_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_qualifying.csv"
            if not _round_in_csv(qual_path, round_num):
                print(f"[recovery] quali not ingested for round={round_num}, triggering ingest_quali")
                Thread(
                    target=ingest_quali,
                    kwargs={"round_num": round_num, "race_name": race_name},
                    daemon=True,
                ).start()

        if race_end and cutoff <= race_end < now_utc:
            results_path = _project_root() / PATHS["data"] / f"{CURRENT_SEASON}_race_results.csv"
            if not _round_session_in_csv(results_path, round_num, "R"):
                print(f"[recovery] results not ingested for round={round_num}, triggering ingest_results")
                Thread(
                    target=ingest_results,
                    kwargs={"round_num": round_num, "race_name": race_name},
                    daemon=True,
                ).start()


def get_next_scheduled_event() -> str | None:
    jobs = scheduler.get_jobs() if scheduler.running else []
    if not jobs:
        return None
    upcoming = [job.next_run_time for job in jobs if job.next_run_time is not None]
    if not upcoming:
        return None
    return min(upcoming).astimezone(timezone.utc).isoformat()


def start_scheduler() -> None:
    if not SCHEDULER_ENABLED:
        return
    if scheduler.running:
        return

    scheduler.add_job(
        schedule_next_race_weekend,
        CronTrigger(day_of_week="mon", hour=0, minute=0, timezone=timezone.utc),
        id="weekly_weekend_planner",
        replace_existing=True,
    )
    scheduler.start()
    schedule_next_race_weekend()
    _recover_missed_jobs()


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


def trigger_job_now(job_name: str, round_num: int | None = None, race_name: str | None = None) -> str:
    if not scheduler.running and SCHEDULER_ENABLED:
        scheduler.start()

    race = _next_race_weekend()
    resolved_round = round_num if round_num is not None else (int(race["round"]) if race else 1)
    resolved_name = race_name if race_name is not None else (str(race["name"]) if race else f"Round {resolved_round}")

    if job_name == "run_prequali":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(run_prequali, trigger="date", kwargs={"round_num": resolved_round, "race_name": resolved_name})
            return job.id
        Thread(target=run_prequali, kwargs={"round_num": resolved_round, "race_name": resolved_name}, daemon=True).start()
        return "manual-run"

    if job_name == "ingest_quali":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(ingest_quali, trigger="date", kwargs={"round_num": resolved_round, "race_name": resolved_name})
            return job.id
        Thread(target=ingest_quali, kwargs={"round_num": resolved_round, "race_name": resolved_name}, daemon=True).start()
        return "manual-run"

    if job_name == "ingest_sprint":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(ingest_sprint, trigger="date", kwargs={"round_num": resolved_round, "race_name": resolved_name})
            return job.id
        Thread(target=ingest_sprint, kwargs={"round_num": resolved_round, "race_name": resolved_name}, daemon=True).start()
        return "manual-run"

    if job_name == "run_postquali":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(run_postquali, trigger="date", kwargs={"round_num": resolved_round, "race_name": resolved_name})
            return job.id
        Thread(target=run_postquali, kwargs={"round_num": resolved_round, "race_name": resolved_name}, daemon=True).start()
        return "manual-run"

    if job_name == "ingest_results":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(ingest_results, trigger="date", kwargs={"round_num": resolved_round, "race_name": resolved_name})
            return job.id
        Thread(target=ingest_results, kwargs={"round_num": resolved_round, "race_name": resolved_name}, daemon=True).start()
        return "manual-run"

    if job_name == "score_predictions":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(score_predictions, trigger="date", kwargs={"round_num": resolved_round})
            return job.id
        Thread(target=score_predictions, kwargs={"round_num": resolved_round}, daemon=True).start()
        return "manual-run"

    if job_name == "retrain_model":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(retrain_model, trigger="date", kwargs={"round_num": resolved_round})
            return job.id
        Thread(target=retrain_model, kwargs={"round_num": resolved_round}, daemon=True).start()
        return "manual-run"

    if job_name == "schedule_weekend":
        if SCHEDULER_ENABLED:
            job = scheduler.add_job(schedule_next_race_weekend, trigger="date")
            return job.id
        Thread(target=schedule_next_race_weekend, daemon=True).start()
        return "manual-run"

    raise ValueError(f"Unknown job name: {job_name}")


def trigger_full_pipeline_now() -> str:
    return trigger_job_now("schedule_weekend")
