"""
Train pre-qualifying LambdaRank models using pace-only features.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import ndcg_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import CURRENT_SEASON, PATHS, PRE_QUALI_FEATURES, XGBOOST_PARAMS


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
    if extra_weight is not None:
        weights = weights * extra_weight
    weighted = df.copy()
    weighted["_group_weight"] = weights
    return weighted.groupby(group_cols, sort=True)["_group_weight"].mean().tolist()


def fit_ranker(X: pd.DataFrame, y: pd.Series, group: list[int], group_weight: list[float]) -> xgb.XGBRanker:
    model = xgb.XGBRanker(
        **XGBOOST_PARAMS,
        objective="rank:pairwise",
        eval_metric="ndcg",
        random_state=42,
        n_jobs=4,
        reg_lambda=1.0,
    )
    model.fit(X, y, group=group, sample_weight=group_weight)
    return model


def main() -> None:
    parser = argparse.ArgumentParser(description="Train pre-qualifying LambdaRank models")
    parser.add_argument("--data-dir", default=PATHS["data"].rstrip("/"), help="Project data directory")
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

    data_dir = PROJECT_ROOT / args.data_dir
    processed_dir = Path(args.processed_dir) if args.processed_dir else PROJECT_ROOT / PATHS["processed"]
    models_dir = PROJECT_ROOT / PATHS["models"]
    models_dir.mkdir(parents=True, exist_ok=True)

    historical = load_processed(processed_dir, "historical")
    results_current = load_processed(processed_dir, str(CURRENT_SEASON))

    hist_train = add_relevance_by_group(historical, ["season", "round"])
    if args.target_round is not None:
        train_current = results_current[results_current["round"] < args.target_round].copy()
    else:
        train_current = results_current.copy()
    train_current = add_relevance_by_group(train_current, ["round"])

    hist_train, hist_groups = build_groups(hist_train, ["season", "round"])
    train_current, current_groups = build_groups(train_current, ["round"])

    X_hist = hist_train[PRE_QUALI_FEATURES].fillna(0.0)
    y_hist = hist_train["relevance"]
    hist_group_weights = group_weights(hist_train, ["season", "round"])

    X_current = train_current[PRE_QUALI_FEATURES].fillna(0.0)
    y_current = train_current["relevance"]
    max_round = train_current["round"].max() if not train_current.empty else 0
    recency = (args.recency_decay ** (max_round - train_current["round"])) if max_round else pd.Series(
        [1.0] * len(train_current), index=train_current.index
    )
    current_weights = group_weights(train_current, ["round"], extra_weight=recency)

    historical_model = fit_ranker(X_hist, y_hist, hist_groups, hist_group_weights)
    current_model = fit_ranker(X_current, y_current, current_groups, current_weights)

    historical_model.save_model(models_dir / "prequali_historical_lambdarank.json")
    current_model.save_model(models_dir / f"prequali_{CURRENT_SEASON}_lambdarank.json")

    eval_scores = current_model.predict(X_current)
    ndcg = ndcg_score([y_current.to_numpy()], [eval_scores]) if len(y_current) else np.nan

    print("Saved prequali models to:")
    print(models_dir / "prequali_historical_lambdarank.json")
    print(models_dir / f"prequali_{CURRENT_SEASON}_lambdarank.json")
    print(
        f"{CURRENT_SEASON} prequali training NDCG:",
        round(float(ndcg), 3) if np.isfinite(ndcg) else "n/a",
    )


if __name__ == "__main__":
    main()
