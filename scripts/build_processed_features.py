"""
Build processed feature datasets from FastF1-sourced CSVs.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (
    CURRENT_SEASON,
    PATHS,
    POST_QUALI_FEATURES,
    PRE_QUALI_FEATURES,
    TRACK_OVERTAKING_INDEX,
)


def _ensure_ids(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "driver_id" not in df.columns and "driver_code" in df.columns:
        df["driver_id"] = df["driver_code"]
    if "constructor_id" not in df.columns and "constructor_name" in df.columns:
        df["constructor_id"] = df["constructor_name"]
    return df


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _status_to_dnf(status: object) -> int:
    if status is None or (isinstance(status, float) and np.isnan(status)):
        return 0
    text = str(status).strip().lower()
    if not text:
        return 0
    return int(
        "dnf" in text
        or "dns" in text
        or "did not" in text
        or "disqualified" in text
        or "retired" in text
    )


def _normalize_circuit_name(name: object) -> str:
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return "unknown"
    text = str(name)
    return text.replace("São", "Sao")


def _data_quality_report(df: pd.DataFrame, label: str) -> None:
    if df.empty:
        print(f"[DATA QUALITY] {label}: empty dataset")
        return

    missing_grid = int(df["grid_position"].isna().sum()) if "grid_position" in df.columns else 0
    missing_finish = int(df["finish_position"].isna().sum()) if "finish_position" in df.columns else 0
    duplicates = 0
    if {"season", "round", "driver_id"}.issubset(df.columns):
        duplicates = int(df.duplicated(subset=["season", "round", "driver_id"]).sum())

    status_cols = [col for col in ["status", "statusId", "status_id", "result_status"] if col in df.columns]
    status_counts = {}
    if status_cols:
        status_col = status_cols[0]
        status_counts = df[status_col].value_counts().head(5).to_dict()

    print(f"[DATA QUALITY] {label} rows={len(df)}")
    print(f"  missing grid_position: {missing_grid}")
    print(f"  missing finish_position: {missing_finish}")
    print(f"  duplicate (season, round, driver_id): {duplicates}")
    if status_counts:
        print(f"  status sample: {status_counts}")


def _season_weights(seasons: list[int]) -> dict[int, float]:
    if not seasons:
        return {}
    if len(seasons) == 1:
        return {seasons[0]: 1.0}
    weights = np.linspace(0.2, 1.0, num=len(seasons))
    return {season: float(weight) for season, weight in zip(seasons, weights)}


def _constructor_development_rate(constructor_hist: pd.DataFrame) -> float:
    if constructor_hist.empty:
        return np.nan
    by_round = constructor_hist.groupby("round", as_index=False)["points"].sum()
    if by_round.shape[0] < 2:
        return np.nan

    points = by_round.sort_values("round")["points"].tolist()
    recent = points[-3:]
    previous = points[-6:-3] if len(points) >= 6 else points[:-3]
    if not previous:
        return float(np.mean(recent))
    return float(np.mean(recent) - np.mean(previous))


def _quali_gap_from_row(row: pd.Series) -> float:
    for key in ["quali_gap_to_pole", "qualifying_time_gap", "quali_gap"]:
        value = row.get(key)
        if value is not None and not (isinstance(value, float) and np.isnan(value)):
            return float(value)
    return np.nan


def _compute_quali_gaps(qualifying: pd.DataFrame) -> pd.DataFrame:
    qualifying = qualifying.copy()
    qualifying["best_time"] = qualifying[["q3_time", "q2_time", "q1_time"]].bfill(axis=1).iloc[:, 0]
    qualifying["best_time"] = pd.to_timedelta(qualifying["best_time"], errors="coerce")
    qualifying["pole_time"] = qualifying.groupby("round")["best_time"].transform("min")
    qualifying["quali_gap_to_pole"] = (
        (qualifying["best_time"] - qualifying["pole_time"]).dt.total_seconds()
    )
    return qualifying[["season", "round", "driver_id", "quali_gap_to_pole"]]


def _build_features(
    results: pd.DataFrame,
    season_weights: dict[int, float],
    driver_track_history_map: dict[tuple[str, str], float],
    driver_fallback_history: dict[str, float],
) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame()

    results = _ensure_ids(results)
    results = _coerce_numeric(results, ["season", "round", "grid_position", "finish_position", "points"])
    results = results.dropna(subset=["season", "round", "driver_id", "constructor_id"]).copy()
    results["season"] = results["season"].astype(int)
    results["round"] = results["round"].astype(int)
    status_cols = [col for col in ["status", "statusId", "status_id", "result_status"] if col in results.columns]
    status_col = status_cols[0] if status_cols else None

    feature_rows: list[dict] = []

    for season in sorted(results["season"].unique()):
        season_df = results[results["season"] == season].copy()
        rounds = sorted(season_df["round"].unique())

        for round_num in rounds:
            race_df = season_df[season_df["round"] == round_num].copy()
            history_df = season_df[season_df["round"] < round_num].copy()

            if history_df.empty:
                standings_map: dict[str, int] = {}
            else:
                standings = history_df.groupby("driver_id", as_index=False).agg(
                    points_sum=("points", "sum"),
                    wins=("finish_position", lambda s: int((s == 1).sum())),
                    podiums=("finish_position", lambda s: int((s <= 3).sum())),
                    avg_finish=("finish_position", "mean"),
                )
                standings = standings.sort_values(
                    ["points_sum", "wins", "podiums", "avg_finish"],
                    ascending=[False, False, False, True],
                ).reset_index(drop=True)
                standings["current_position"] = range(1, len(standings) + 1)
                standings_map = dict(zip(standings["driver_id"], standings["current_position"]))

            for _, row in race_df.iterrows():
                driver_id = row["driver_id"]
                constructor_id = row["constructor_id"]

                driver_hist = history_df[history_df["driver_id"] == driver_id]
                constructor_hist = history_df[history_df["constructor_id"] == constructor_id]

                races_completed = int(driver_hist.shape[0])
                points_sum = float(driver_hist["points"].fillna(0.0).sum()) if races_completed else 0.0
                current_position = standings_map.get(driver_id, 999)

                avg_points = points_sum / races_completed if races_completed else np.nan
                avg_finish = float(driver_hist["finish_position"].mean()) if races_completed else np.nan

                wins = int((driver_hist["finish_position"] == 1).sum()) if races_completed else 0
                podiums = int((driver_hist["finish_position"] <= 3).sum()) if races_completed else 0
                poles = int((driver_hist["grid_position"] == 1).sum()) if races_completed else 0
                recent_top3_rate = (podiums / races_completed) if races_completed else np.nan

                if races_completed:
                    last_race = driver_hist.sort_values("round").iloc[-1]
                    last_finish = last_race["finish_position"]
                    last_points = last_race["points"]
                else:
                    last_finish = np.nan
                    last_points = np.nan

                if races_completed >= 2:
                    first_race = driver_hist.sort_values("round").iloc[0]
                    momentum = float(last_points) - float(first_race["points"])
                else:
                    momentum = np.nan

                constructor_avg_finish = (
                    float(constructor_hist["finish_position"].mean())
                    if not constructor_hist.empty
                    else np.nan
                )
                constructor_avg_points = (
                    float(constructor_hist["points"].mean())
                    if not constructor_hist.empty
                    else np.nan
                )

                circuit_name = _normalize_circuit_name(
                    row.get("circuit_name") or row.get("race_name")
                )
                track_overtaking_index = TRACK_OVERTAKING_INDEX.get(circuit_name, 0.5)
                track_key = (driver_id, circuit_name)
                driver_track_history = driver_track_history_map.get(
                    track_key,
                    driver_fallback_history.get(driver_id, np.nan),
                )
                constructor_development_rate = _constructor_development_rate(constructor_hist)
                quali_gap_to_pole = _quali_gap_from_row(row)
                grid_position = row.get("grid_position")
                if grid_position is None or (isinstance(grid_position, float) and np.isnan(grid_position)):
                    grid_position_weighted = np.nan
                else:
                    grid_position_weighted = float(grid_position) * (1.0 - track_overtaking_index)

                feature_rows.append({
                    "season": season,
                    "round": round_num,
                    "race_name": row.get("race_name"),
                    "circuit_id": row.get("circuit_id"),
                    "circuit_name": circuit_name,
                    "driver_id": driver_id,
                    "constructor_id": constructor_id,
                    "grid_position": row.get("grid_position"),
                    "quali_gap_to_pole": quali_gap_to_pole,
                    "grid_position_weighted": grid_position_weighted,
                    "current_points": points_sum,
                    "current_position": current_position,
                    "avg_points_per_race": avg_points,
                    "avg_finish_position": avg_finish,
                    "races_completed": races_completed,
                    "wins": wins,
                    "podiums": podiums,
                    "poles": poles,
                    "recent_top3_rate": recent_top3_rate,
                    "last_race_finish": last_finish,
                    "last_race_points": last_points,
                    "momentum": momentum,
                    "constructor_avg_finish": constructor_avg_finish,
                    "constructor_avg_points": constructor_avg_points,
                    "driver_track_history": driver_track_history,
                    "constructor_development_rate": constructor_development_rate,
                    "track_overtaking_index": track_overtaking_index,
                    "season_weight": season_weights.get(season, 1.0),
                    "finish_position": row.get("finish_position"),
                    "points": row.get("points"),
                    "dnf_flag": _status_to_dnf(row.get(status_col)) if status_col else np.nan,
                })

    return pd.DataFrame(feature_rows)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / PATHS["data"]
    processed_dir = project_root / PATHS["processed"]
    processed_dir.mkdir(parents=True, exist_ok=True)

    historical_path = data_dir / "historical_races.csv"
    current_path = data_dir / f"{CURRENT_SEASON}_race_results.csv"

    if not historical_path.exists():
        raise FileNotFoundError(f"Missing historical data at {historical_path}")
    if not current_path.exists():
        raise FileNotFoundError(f"Missing {CURRENT_SEASON} race results at {current_path}")

    historical = pd.read_csv(historical_path)
    current = pd.read_csv(current_path)

    qualifying_path = data_dir / f"{CURRENT_SEASON}_qualifying.csv"
    if qualifying_path.exists():
        qualifying = pd.read_csv(qualifying_path)
        qualifying = _ensure_ids(qualifying)
        qualifying = _coerce_numeric(qualifying, ["season", "round"])
        gaps = _compute_quali_gaps(qualifying)
        current = current.merge(gaps, on=["season", "round", "driver_id"], how="left")

    _data_quality_report(historical, "historical_races")
    _data_quality_report(current, f"{CURRENT_SEASON}_race_results")

    historical = _ensure_ids(historical)
    current = _ensure_ids(current)

    historical_seasons = sorted(pd.to_numeric(historical["season"], errors="coerce").dropna().unique().astype(int))
    historical_weights = _season_weights(historical_seasons)

    hist_tracks = historical.dropna(subset=["driver_id"]).copy()
    hist_tracks["circuit_name"] = hist_tracks.get("circuit_name", pd.Series(["unknown"] * len(hist_tracks)))
    hist_track_history = (
        hist_tracks.groupby(["driver_id", "circuit_name"], as_index=False)["finish_position"]
        .mean()
        .rename(columns={"finish_position": "driver_track_history"})
    )
    driver_track_history = {
        (row["driver_id"], row["circuit_name"]): float(row["driver_track_history"])
        for _, row in hist_track_history.iterrows()
    }
    driver_fallback_history = (
        hist_tracks.groupby("driver_id")["finish_position"].mean().to_dict()
        if not hist_tracks.empty
        else {}
    )

    historical_features = _build_features(
        historical,
        historical_weights,
        driver_track_history,
        driver_fallback_history,
    )
    current_features = _build_features(
        current,
        {CURRENT_SEASON: 1.0},
        driver_track_history,
        driver_fallback_history,
    )

    historical_features.to_csv(processed_dir / "historical_features.csv", index=False)
    current_features.to_csv(processed_dir / f"{CURRENT_SEASON}_features.csv", index=False)
    historical_features.to_parquet(processed_dir / "historical_features.parquet", index=False)
    current_features.to_parquet(processed_dir / f"{CURRENT_SEASON}_features.parquet", index=False)

    print(f"Saved historical features: {len(historical_features)} rows")
    print(f"Saved {CURRENT_SEASON} features: {len(current_features)} rows")


if __name__ == "__main__":
    main()
