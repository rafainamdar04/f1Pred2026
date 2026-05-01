from __future__ import annotations

from pathlib import Path

import uvicorn

from app.api import app
from app.scheduler import shutdown_scheduler, start_scheduler


def _startup_dirs() -> None:
    from config.settings import PATHS

    for path_str in PATHS.values():
        Path(path_str).mkdir(parents=True, exist_ok=True)
    (Path(PATHS["data"]) / "logs").mkdir(parents=True, exist_ok=True)


def _startup_orphan_scan() -> None:
    from app.database import scan_orphaned_pipelines

    try:
        scan_orphaned_pipelines()
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Orphan scan failed: %s", exc)


def main() -> None:
    app.add_event_handler("startup", _startup_dirs)
    app.add_event_handler("startup", _startup_orphan_scan)
    app.add_event_handler("startup", start_scheduler)
    app.add_event_handler("shutdown", shutdown_scheduler)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
