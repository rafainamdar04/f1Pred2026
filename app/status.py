from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config.settings import PATHS


def _status_path() -> Path:
    return Path(PATHS["data"]) / "pipeline_status.json"


def write_status_file(
    last_run: datetime,
    status: str,
    rounds_completed: int,
) -> None:
    payload = {
        "last_run": last_run.astimezone(timezone.utc).isoformat(),
        "status": status,
        "rounds_completed": rounds_completed,
    }
    path = _status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_status_file() -> dict:
    path = _status_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Status file is invalid JSON: {path}") from exc
