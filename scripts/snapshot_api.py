"""
Snapshot every public API GET response to static JSON under frontend/public/api/.

This lets the React app run as a fully static site (Option A deploy): the SPA
fetches these files instead of a live FastAPI server. Time-gated prediction
endpoints that 404 (a race not yet at its appointed phase) are simply skipped,
so the static site never exposes a prediction before its appointed time.

Files are written with a .json extension; the frontend appends ".json" when
built with VITE_STATIC_API=true. The extension also avoids file-vs-directory
collisions (e.g. /api/predictions/next and /api/predictions/next/prequali).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.api import app  # noqa: E402

OUT_ROOT = PROJECT_ROOT / "frontend" / "public"

# Parameterless public endpoints the frontend consumes.
STATIC_PATHS = [
    "/api/calendar",
    "/api/calendar/sprints",
    "/api/metrics",
    "/api/status",
    "/api/pipeline/status",
    "/api/race-results",
    "/api/standings/drivers",
    "/api/standings/constructors",
    "/api/standings/drivers/sprints",
    "/api/standings/constructors/sprints",
    "/api/predictions/history",
    "/api/predictions/accuracy",
    "/api/predictions/next",
    "/api/predictions/next/prequali",
    "/api/predictions/next/postquali",
]

# Per-round prediction views: /api/predictions/{round}/{kind}
PER_ROUND_KINDS = ["prequali", "postquali", "comparison", "accuracy"]

# These change every race weekend (next race pointer shifts after each result).
# Delete before the snapshot loop so a backend 404 leaves no stale file on disk.
VOLATILE_PATHS = [
    "/api/predictions/next",
    "/api/predictions/next/prequali",
    "/api/predictions/next/postquali",
]


def _write(path: str, payload: object) -> None:
    out = OUT_ROOT / (path.lstrip("/") + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload), encoding="utf-8")


def main() -> None:
    client = TestClient(app)

    rounds: list[int] = []
    cal = client.get("/api/calendar")
    if cal.status_code == 200:
        rounds = [int(r["round"]) for r in cal.json().get("races", []) if r.get("round")]

    driver_ids: list[str] = []
    dr = client.get("/api/standings/drivers")
    if dr.status_code == 200:
        driver_ids = [d["driver_id"] for d in dr.json().get("drivers", []) if d.get("driver_id")]

    paths = list(STATIC_PATHS)
    for rnd in rounds:
        paths.extend(f"/api/predictions/{rnd}/{kind}" for kind in PER_ROUND_KINDS)
    for did in driver_ids:
        paths.append(f"/api/drivers/{did}")

    # Remove volatile files before writing so stale versions don't survive a 404.
    deleted = 0
    for path in VOLATILE_PATHS:
        out = OUT_ROOT / (path.lstrip("/") + ".json")
        if out.exists():
            out.unlink()
            deleted += 1

    written, skipped = 0, 0
    for path in paths:
        resp = client.get(path)
        if resp.status_code == 200:
            _write(path, resp.json())
            written += 1
        else:
            skipped += 1

    print(f"[snapshot] deleted {deleted} volatile, wrote {written}, skipped {skipped} (gated/missing) -> {OUT_ROOT / 'api'}")


if __name__ == "__main__":
    main()
