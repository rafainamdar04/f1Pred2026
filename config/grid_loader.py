from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "PyYAML is required to load grid YAML files. Install with `pip install pyyaml`."
    ) from exc


def load_grid(season: int) -> list[dict]:
    """Load driver grid configuration for the provided season."""
    grid_path = Path(__file__).resolve().parent / f"grid_{season}.yaml"
    if not grid_path.exists():
        raise FileNotFoundError(f"Missing grid config: {grid_path}")

    with grid_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    drivers = payload.get("drivers", [])
    if not isinstance(drivers, list):
        raise ValueError("Grid config 'drivers' must be a list")

    return drivers
