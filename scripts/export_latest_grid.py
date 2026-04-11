"""
Export latest qualifying grid with gap-to-pole from stored qualifying data.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CURRENT_SEASON, PATHS


def _load_qualifying(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Qualifying file not found: {path}")
    df = pd.read_csv(path)
    return df


def _compute_grid(qualifying: pd.DataFrame, round_num: int) -> pd.DataFrame:
    round_df = qualifying[qualifying["round"] == round_num].copy()
    if round_df.empty:
        raise ValueError(f"No qualifying data for round {round_num}")

    round_df["best_time"] = round_df[["q3_time", "q2_time", "q1_time"]].bfill(axis=1).iloc[:, 0]
    round_df["best_time"] = pd.to_timedelta(round_df["best_time"], errors="coerce")
    pole_time = round_df["best_time"].min()
    round_df["quali_gap_to_pole"] = (round_df["best_time"] - pole_time).dt.total_seconds()

    return round_df[["driver_id", "grid_position", "quali_gap_to_pole"]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export latest grid from qualifying data")
    parser.add_argument("--round", type=int, default=None, help="Round number to export")
    parser.add_argument("--output", type=str, default=None, help="Output CSV path")
    args = parser.parse_args()

    qualifying_path = PROJECT_ROOT / PATHS["data"] / f"{CURRENT_SEASON}_qualifying.csv"
    qualifying = _load_qualifying(qualifying_path)

    round_num = args.round if args.round is not None else int(qualifying["round"].max())
    grid = _compute_grid(qualifying, round_num)

    output_path = Path(args.output) if args.output else PROJECT_ROOT / PATHS["data"] / "latest_grid.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(output_path, index=False)
    print(f"Saved grid to {output_path}")


if __name__ == "__main__":
    main()
