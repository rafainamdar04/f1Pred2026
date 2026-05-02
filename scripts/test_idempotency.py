"""
Idempotency test: running sprint ingestion for Round 2 twice must not produce duplicate rows.
Tests the CSV merge logic directly without hitting FastF1.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.scheduler import _merge_csv_idempotent


def _make_sprint_rows(round_num: int = 2, n_drivers: int = 22) -> pd.DataFrame:
    sprint_points = [8, 7, 6, 5, 4, 3, 2, 1] + [0] * 14
    rows = []
    for i in range(n_drivers):
        rows.append({
            "season": 2026,
            "round": round_num,
            "driver_id": f"driver_{i + 1:02d}",
            "driver_name": f"Driver {i + 1}",
            "constructor_id": f"team_{(i // 2) + 1:02d}",
            "constructor_name": f"Team {(i // 2) + 1}",
            "finish_position": i + 1,
            "points": sprint_points[i],
            "session_type": "S",
        })
    return pd.DataFrame(rows)


def run_test() -> None:
    key_cols = ["season", "round", "driver_id", "session_type"]

    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "2026_race_results.csv"
        sprint_df = _make_sprint_rows(round_num=2, n_drivers=22)

        print("Pass 1: ingesting 22 sprint rows for Round 2...")
        _merge_csv_idempotent(csv_path, sprint_df, key_cols)
        df_after_pass1 = pd.read_csv(csv_path)
        sprint_rows_pass1 = df_after_pass1[(df_after_pass1["round"] == 2) & (df_after_pass1["session_type"] == "S")]
        print(f"  Row count after pass 1: {len(sprint_rows_pass1)}")
        assert len(sprint_rows_pass1) == 22, f"Expected 22 rows after pass 1, got {len(sprint_rows_pass1)}"

        print("Pass 2: ingesting same 22 sprint rows again (idempotency check)...")
        _merge_csv_idempotent(csv_path, sprint_df, key_cols)
        df_after_pass2 = pd.read_csv(csv_path)
        sprint_rows_pass2 = df_after_pass2[(df_after_pass2["round"] == 2) & (df_after_pass2["session_type"] == "S")]
        print(f"  Row count after pass 2: {len(sprint_rows_pass2)}")
        assert len(sprint_rows_pass2) == 22, f"Expected 22 rows after pass 2, got {len(sprint_rows_pass2)}"

        print("\nVerifying total points = 36 (8+7+6+5+4+3+2+1+0*14)...")
        total_pts = pd.to_numeric(sprint_rows_pass2["points"], errors="coerce").fillna(0).sum()
        print(f"  Total sprint points: {total_pts}")
        assert total_pts == 36, f"Expected 36 total sprint points, got {total_pts}"

        print("\nAll idempotency checks passed.")
        print(f"  Round 2 sprint rows remain at {len(sprint_rows_pass2)} after two ingestion passes.")


if __name__ == "__main__":
    run_test()
