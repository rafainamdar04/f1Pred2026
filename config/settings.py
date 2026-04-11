import os

CURRENT_SEASON = 2026
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
PATHS = {
    "data": "data/",
    "models": "models/",
    "predictions": "data/predictions/",
    "metrics": "data/metrics/",
    "processed": "data/processed/",
}
SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes", "on"}
API_KEY = os.getenv("API_KEY", "")
