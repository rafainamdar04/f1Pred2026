"""
Single entrypoint the GitHub Actions cron runs to refresh the static demo.

Replaces the in-process APScheduler for the Option A (static) deploy:
  1. seed an empty checkout from seed/ (the committed baseline)
  2. run the full pipeline (FastF1 ingest -> features -> train -> predict)
  3. generate the upcoming (next not-yet-raced) round's pre/post-quali
  4. snapshot every public API response to frontend/public/api/*.json

Each step is best-effort (check=False): if FastF1 is unavailable, the seed /
previously committed data still produces a valid snapshot.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
SCRIPTS = ROOT / "scripts"


def run(*args: str) -> None:
    print(f"\n[refresh_demo] $ {' '.join(str(a) for a in args)}")
    subprocess.run([PY, *map(str, args)], cwd=ROOT, check=False)


def seed_if_missing() -> None:
    """Copy seed/{data,models} into place where files don't already exist."""
    seed = ROOT / "seed"
    if not seed.exists():
        return
    copied = 0
    for sub in ("data", "models"):
        src_root = seed / sub
        if not src_root.exists():
            continue
        for src in src_root.rglob("*"):
            if not src.is_file():
                continue
            dst = ROOT / sub / src.relative_to(src_root)
            if not dst.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
    print(f"[refresh_demo] seeded {copied} files from seed/")


def _calendar() -> list[tuple[int, str]]:
    path = ROOT / "data" / "2026_calendar.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return []
    races = payload.get("races") if isinstance(payload, dict) else payload
    out: list[tuple[int, str]] = []
    for race in races or []:
        if isinstance(race, dict) and race.get("round"):
            out.append((int(race["round"]), race.get("name") or race.get("raceName") or f"Round {race['round']}"))
    return sorted(out)


def _raced_rounds() -> set[int]:
    path = ROOT / "data" / "2026_race_results.csv"
    if not path.exists():
        return set()
    rounds: set[int] = set()
    with path.open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("session_type", "R") == "R":
                try:
                    rounds.add(int(float(row["round"])))
                except (TypeError, ValueError, KeyError):
                    continue
    return rounds


def generate_upcoming() -> None:
    """Pre-race predictions for the next not-yet-raced round (mirrors scheduler)."""
    raced = _raced_rounds()
    upcoming = next(((r, n) for r, n in _calendar() if r not in raced), None)
    if not upcoming:
        print("[refresh_demo] no upcoming round to predict")
        return
    rnd, name = upcoming
    print(f"[refresh_demo] upcoming round {rnd}: {name}")
    run(SCRIPTS / "build_processed_features.py")
    run(SCRIPTS / "predict_prequali.py", "--round", rnd, "--race-name", name)

    grid = ROOT / "data" / "processed" / f"round_{rnd}_grid.csv"
    run(SCRIPTS / "export_latest_grid.py", "--round", rnd, "--output", grid)
    if grid.exists():
        run(SCRIPTS / "predict_postquali.py", "--round", rnd, "--race-name", name, "--grid-file", grid)


def main() -> None:
    seed_if_missing()
    run(SCRIPTS / "run_pipeline.py")   # ingest -> features -> train -> predict completed rounds
    generate_upcoming()
    run(SCRIPTS / "snapshot_api.py")   # publish static JSON for the frontend
    print("\n[refresh_demo] done")


if __name__ == "__main__":
    main()
