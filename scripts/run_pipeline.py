"""
Run the end-to-end pipeline:
refresh -> build -> train -> evaluate -> predict
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CURRENT_SEASON, PATHS


def _run_step(label: str, args: list[str]) -> None:
    print(f"\n[PIPELINE] {label}")
    print("  ", " ".join(args))
    subprocess.run(args, check=True)


def _completed_rounds(processed_path: Path) -> list[int]:
    df = pd.read_csv(processed_path)
    completed = df.groupby("round")["finish_position"].apply(lambda s: s.notna().all())
    return sorted(completed[completed].index.tolist())


def _round_race_name(df: pd.DataFrame, round_num: int) -> str:
    rows = df[df["round"] == round_num]
    if rows.empty:
        return f"Round {round_num}"
    name = rows["race_name"].dropna().unique()
    return name[0] if len(name) else f"Round {round_num}"


def _write_grid_file(df: pd.DataFrame, round_num: int, out_path: Path) -> None:
    grid_df = df[df["round"] == round_num][["driver_id", "grid_position", "quali_gap_to_pole"]].copy()
    grid_df.to_csv(out_path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the end-to-end pipeline")
    parser.add_argument(
        "--mode",
        choices=["prequali", "postquali", "both"],
        default="both",
        help="Prediction mode to run",
    )
    parser.add_argument(
        "--grid-file",
        default=None,
        help="Grid CSV for postquali predictions when needed",
    )
    args = parser.parse_args()

    project_root = PROJECT_ROOT
    python = sys.executable

    _run_step("refresh (FastF1)", [python, str(project_root / "scripts" / "fastf1_scraper.py")])
    _run_step("build features", [python, str(project_root / "scripts" / "build_processed_features.py")])
    _run_step("train prequali models", [python, str(project_root / "scripts" / "train_prequali_model.py")])
    _run_step("train postquali models", [python, str(project_root / "scripts" / "train_postquali_model.py")])
    _run_step("evaluate", [python, str(project_root / "scripts" / "evaluate_hybrid.py")])

    processed_path = project_root / PATHS["processed"] / f"{CURRENT_SEASON}_features.csv"
    if not processed_path.exists():
        raise FileNotFoundError(f"Missing processed features: {processed_path}")
    processed_df = pd.read_csv(processed_path)
    rounds = _completed_rounds(processed_path)

    if args.mode in ("prequali", "both"):
        for round_num in rounds:
            race_name = _round_race_name(processed_df, round_num)
            _run_step(
                f"predict prequali round {round_num}",
                [
                    python,
                    str(project_root / "scripts" / "predict_prequali.py"),
                    "--round",
                    str(round_num),
                    "--race-name",
                    race_name,
                ],
            )

    if args.mode in ("postquali", "both"):
        grid_file = args.grid_file
        for round_num in rounds:
            race_name = _round_race_name(processed_df, round_num)
            if not grid_file:
                temp_grid = project_root / "data" / "processed" / f"round_{round_num}_grid.csv"
                _write_grid_file(processed_df, round_num, temp_grid)
                grid_path = temp_grid
            else:
                grid_path = Path(grid_file)
            _run_step(
                f"predict postquali round {round_num}",
                [
                    python,
                    str(project_root / "scripts" / "predict_postquali.py"),
                    "--round",
                    str(round_num),
                    "--race-name",
                    race_name,
                    "--grid-file",
                    str(grid_path),
                ],
            )


if __name__ == "__main__":
    main()
