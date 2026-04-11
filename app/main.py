from __future__ import annotations

import uvicorn

from app.api import app
from app.scheduler import shutdown_scheduler, start_scheduler


def main() -> None:
    app.add_event_handler("startup", start_scheduler)
    app.add_event_handler("shutdown", shutdown_scheduler)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
