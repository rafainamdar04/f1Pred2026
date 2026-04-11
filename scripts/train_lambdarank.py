"""
Train blended LambdaRank models on preprocessed features.

Outputs:
- models/historical_lambdarank.json
- models/2026_lambdarank.json
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import ndcg_score

from config.settings import CURRENT_SEASON, HISTORICAL_YEARS, PATHS, XGBOOST_PARAMS


FEATURE_COLS = [
    "grid_position",
    "current_points",
    "current_position",
    "avg_points_per_race",
    "avg_finish_position",
    "races_completed",
    "wins",
    "podiums",
    "poles",
    "last_race_finish",
    "last_race_points",
    "momentum",
    "constructor_avg_finish",
    "constructor_avg_points",
    "season_weight",
]

ID_COLS = ["season", "round", "race_name", "circuit_id", "driver_id", "constructor_id"]
TARGET_COLS = ["finish_position", "points"]


def load_processed(processed_dir: Path, name: str) -> pd.DataFrame:
    parquet_path = processed_dir / f"{name}_features.parquet"
    csv_path = processed_dir / f"{name}_features.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(f"Missing processed dataset: {parquet_path} or {csv_path}")


def add_relevance_by_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    max_finish = df.groupby(group_cols)["finish_position"].transform("max")
    df["finish_position"] = df["finish_position"].fillna(max_finish + 1)
    df["relevance"] = (max_finish + 1) - df["finish_position"]
    return df


def build_groups(df: pd.DataFrame, group_cols: list[str]) -> tuple[pd.DataFrame, list[int]]:
    ordered = df.sort_values(group_cols + ["driver_id"]).reset_index(drop=True)
    group_sizes = ordered.groupby(group_cols, sort=True).size().tolist()
    return ordered, group_sizes


def group_weights(df: pd.DataFrame, group_cols: list[str], extra_weight: pd.Series | None = None) -> list[float]:
    weights = df.get("season_weight", pd.Series([1.0] * len(df), index=df.index)).astype(float)
    if "season" in df.columns:
        cutoff_year = sorted(HISTORICAL_YEARS)[1] if len(HISTORICAL_YEARS) > 1 else HISTORICAL_YEARS[0]
        weights = weights.where(df["season"].astype(float) > cutoff_year, weights * 0.7)
    if extra_weight is not None:
        weights = weights * extra_weight
    weighted = df.copy()
    weighted["_group_weight"] = weights
    return weighted.groupby(group_cols, sort=True)["_group_weight"].mean().tolist()


def fit_ranker(X: pd.DataFrame, y: pd.Series, group: list[int], group_weight: list[float]) -> xgb.XGBRanker:
    model = xgb.XGBRanker(
        **XGBOOST_PARAMS,
        colsample_bytree=0.9,
        objective="rank:pairwise",
        eval_metric="ndcg",
        random_state=42,
        n_jobs=4,
        reg_lambda=1.0,
    )
    model.fit(X, y, group=group, sample_weight=group_weight)
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train blended LambdaRank models")
    parser.add_argument("--data-dir", default="data", help="Project data directory")
    parser.add_argument("--processed-dir", default=None, help="Override processed data directory")
    parser.add_argument(
        "--target-round",
        type=int,
        default=None,
        help=f"Holdout round for {CURRENT_SEASON} (train on rounds < target)",
    )
    parser.add_argument(
        "--recency-decay",
        type=float,
        default=0.85,
        help=f"Per-round recency decay for {CURRENT_SEASON} (0-1)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / args.data_dir
    processed_dir = Path(args.processed_dir) if args.processed_dir else data_dir / "processed"
    models_dir = project_root / PATHS["models"]
    models_dir.mkdir(parents=True, exist_ok=True)

    historical = load_processed(processed_dir, "historical")
    results_2026 = load_processed(processed_dir, str(CURRENT_SEASON))

    hist_train = add_relevance_by_group(historical, ["season", "round"])
    if args.target_round is not None:
        train_2026 = results_2026[results_2026["round"] < args.target_round].copy()
    else:
        train_2026 = results_2026.copy()
    train_2026 = add_relevance_by_group(train_2026, ["round"])

    hist_train, hist_groups = build_groups(hist_train, ["season", "round"])
    train_2026, train_2026_groups = build_groups(train_2026, ["round"])

    X_hist = hist_train[FEATURE_COLS].fillna(0.0)
    y_hist = hist_train["relevance"]
    hist_group_weights = group_weights(hist_train, ["season", "round"])

    X_2026 = train_2026[FEATURE_COLS].fillna(0.0)
    y_2026 = train_2026["relevance"]
    max_round = train_2026["round"].max() if not train_2026.empty else 0
    recency = (args.recency_decay ** (max_round - train_2026["round"])) if max_round else pd.Series(
        [1.0] * len(train_2026), index=train_2026.index
    )
    weights_2026 = group_weights(train_2026, ["round"], extra_weight=recency)

    historical_model = fit_ranker(X_hist, y_hist, hist_groups, hist_group_weights)
    model_2026 = fit_ranker(X_2026, y_2026, train_2026_groups, weights_2026)

    historical_model.save_model(models_dir / "historical_lambdarank.json")
    model_2026.save_model(models_dir / f"{CURRENT_SEASON}_lambdarank.json")

    eval_scores = model_2026.predict(X_2026)
    ndcg = ndcg_score([y_2026.to_numpy()], [eval_scores]) if len(y_2026) else np.nan

    print("Saved models to:")
    print(models_dir / "historical_lambdarank.json")
    print(models_dir / f"{CURRENT_SEASON}_lambdarank.json")
    print(
        f"{CURRENT_SEASON} training NDCG:",
        round(float(ndcg), 3) if np.isfinite(ndcg) else "n/a",
    )


if __name__ == "__main__":
    main()
