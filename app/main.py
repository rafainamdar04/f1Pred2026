from __future__ import annotations

from contextlib import asynccontextmanager
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


@asynccontextmanager
async def _lifespan(application):
    _startup_dirs()
    _startup_orphan_scan()
    start_scheduler()
    yield
    shutdown_scheduler()


# Wire lifespan at module level so it fires whether uvicorn imports app directly
# or main() is called — previously these were only registered inside main().
app.router.lifespan_context = _lifespan


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
