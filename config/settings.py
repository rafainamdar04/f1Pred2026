import logging
import os
import sys

_logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "development")
CURRENT_SEASON = int(os.getenv("CURRENT_SEASON", "2026"))
HISTORICAL_YEARS = [2021, 2022, 2023, 2024, 2025]

ALPHA_GRID = {"min": 0.2, "max": 0.9, "steps": 15}
XGBOOST_PARAMS = {
    "max_depth": 4,
    "learning_rate": 0.08,
    "subsample": 0.9,
    "n_estimators": 300,
}
FEATURE_CONSTANTS = {
    "grid_gap_estimate": 0.25,
    "quantile_clip": [0.05, 0.95],
}
TRACK_OVERTAKING_INDEX = {
    "Australian Grand Prix": 0.6,
    "Chinese Grand Prix": 0.7,
    "Japanese Grand Prix": 0.4,
    "Bahrain Grand Prix": 0.8,
    "Saudi Arabian Grand Prix": 0.6,
    "Miami Grand Prix": 0.5,
    "Monaco Grand Prix": 0.2,
    "Canadian Grand Prix": 0.7,
    "Spanish Grand Prix": 0.4,
    "Barcelona Grand Prix": 0.4,
    "Austrian Grand Prix": 0.6,
    "British Grand Prix": 0.7,
    "Hungarian Grand Prix": 0.3,
    "Belgian Grand Prix": 0.8,
    "Dutch Grand Prix": 0.3,
    "Italian Grand Prix": 0.9,
    "Azerbaijan Grand Prix": 0.7,
    "Singapore Grand Prix": 0.2,
    "Japanese Grand Prix (Alternate)": 0.4,
    "Mexico City Grand Prix": 0.6,
    "United States Grand Prix": 0.7,
    "Sao Paulo Grand Prix": 0.6,
    "Las Vegas Grand Prix": 0.7,
    "Qatar Grand Prix": 0.5,
    "Abu Dhabi Grand Prix": 0.5,
}
PRE_QUALI_FEATURES = [
    "avg_finish_position",
    "avg_points_per_race",
    "momentum",
    "constructor_avg_points",
    "dnf_flag",
    "driver_track_history",
    "constructor_development_rate",
    "track_overtaking_index",
]
POST_QUALI_FEATURES = [
    "grid_position",
    "quali_gap_to_pole",
    "grid_position_weighted",
]

# ── Storage paths ─────────────────────────────────────────────────────────────
DATA_DIR = os.getenv("DATA_DIR", "data")
MODELS_DIR = os.getenv("MODELS_DIR", "models")

PATHS = {
    "data": DATA_DIR,
    "models": MODELS_DIR,
    "predictions": f"{DATA_DIR}/predictions",
    "metrics": f"{DATA_DIR}/metrics",
    "processed": f"{DATA_DIR}/processed",
}

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/f1ranker.db")

# ── Pipeline ──────────────────────────────────────────────────────────────────
PIPELINE_TIMEOUT_SECONDS = int(os.getenv("PIPELINE_TIMEOUT_SECONDS", "1800"))

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes", "on"}

# ── Security ──────────────────────────────────────────────────────────────────
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", os.getenv("API_KEY", ""))

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# Validate API key at startup — fail hard in production, warn in dev
if ENV == "production":
    if not ADMIN_API_KEY or len(ADMIN_API_KEY) < 32:
        print(
            "FATAL: ENV=production requires ADMIN_API_KEY to be set and at least 32 characters. "
            "Generate one with: openssl rand -hex 32",
            file=sys.stderr,
        )
        sys.exit(1)
elif not ADMIN_API_KEY or len(ADMIN_API_KEY) < 32:
    _logger.warning(
        "ADMIN_API_KEY is not set or too short (< 32 chars). "
        "Set a 32+ char secret before production deployment."
    )
