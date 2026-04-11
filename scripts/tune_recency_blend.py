"""
Tune recency decay and blend alpha using Japanese GP (round 3) as holdout.
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

from config.settings import (
    ALPHA_GRID,
    CURRENT_SEASON,
    FEATURE_CONSTANTS,
    HISTORICAL_YEARS,
    PATHS,
    XGBOOST_PARAMS,
)


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


def group_weights(
    df: pd.DataFrame,
    group_cols: list[str],
    extra_weight: pd.Series | None = None,
) -> list[float]:
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


def clip_scores(scores: pd.Series) -> pd.Series:
    if scores.empty:
        return scores
    low, high = scores.quantile(FEATURE_CONSTANTS["quantile_clip"])
    return scores.clip(lower=low, upper=high)


def scale_hist_to_current(hist_scores: pd.Series, current_scores: pd.Series) -> pd.Series:
    if hist_scores.empty:
        return hist_scores
    hist_mean = hist_scores.mean()
    hist_std = hist_scores.std(ddof=0)
    if hist_std == 0 or np.isnan(hist_std):
        return pd.Series([current_scores.mean()] * len(hist_scores), index=hist_scores.index)
    z = (hist_scores - hist_mean) / hist_std
    cur_mean = current_scores.mean()
    cur_std = current_scores.std(ddof=0)
    if cur_std == 0 or np.isnan(cur_std):
        cur_std = 1.0
    return z * cur_std + cur_mean


def evaluate_round(df: pd.DataFrame, scores: pd.Series) -> dict[str, float]:
    df = df.dropna(subset=["finish_position"]).copy()
    max_finish = df["finish_position"].max()
    relevance = (max_finish + 1) - df["finish_position"]
    ndcg = ndcg_score([relevance.to_numpy()], [scores.to_numpy()])

    pred_rank = df.assign(score=scores).sort_values("score", ascending=False).reset_index(drop=True)
    actual_rank = df.sort_values("finish_position", ascending=True).reset_index(drop=True)
    pred_top3 = set(pred_rank.head(3)["driver_id"])
    actual_top3 = set(actual_rank.head(3)["driver_id"])
    top3_hit = len(pred_top3 & actual_top3) / 3.0

    rank_map = pd.Series(range(1, len(pred_rank) + 1), index=pred_rank["driver_id"]).to_dict()
    df["pred_rank"] = df["driver_id"].map(rank_map)
    mae = (df["pred_rank"] - df["finish_position"]).abs().mean()

    return {"ndcg": float(ndcg), "top3_hit": float(top3_hit), "mae": float(mae)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune recency decay + blend for round 3")
    parser.add_argument("--data-dir", default=PATHS["data"].rstrip("/"), help="Project data directory")
    parser.add_argument("--processed-dir", default=None, help="Override processed data directory")
    parser.add_argument(
        "--target-round",
        type=int,
        default=3,
        help=f"{CURRENT_SEASON} round to hold out",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / args.data_dir
    processed_dir = (
        Path(args.processed_dir)
        if args.processed_dir
        else project_root / PATHS["processed"]
    )

    historical = load_processed(processed_dir, "historical")
    results_2026 = load_processed(processed_dir, str(CURRENT_SEASON))

    hist_train = add_relevance_by_group(historical, ["season", "round"])
    hist_train, hist_groups = build_groups(hist_train, ["season", "round"])

    X_hist = hist_train[FEATURE_COLS].fillna(0.0)
    y_hist = hist_train["relevance"]
    hist_group_weights = group_weights(hist_train, ["season", "round"])
    hist_model = fit_ranker(X_hist, y_hist, hist_groups, hist_group_weights)

    hist_scores = hist_model.predict(historical[FEATURE_COLS].fillna(0.0)) if not historical.empty else np.array([])
    hist_map = pd.Series(hist_scores, index=historical["driver_id"]).to_dict() if len(hist_scores) else {}

    target_round = args.target_round
    train_2026 = results_2026[results_2026["round"] < target_round].copy()
    target = results_2026[results_2026["round"] == target_round].copy()

    train_2026 = add_relevance_by_group(train_2026, ["round"])
    train_2026, train_groups = build_groups(train_2026, ["round"])

    X_2026 = train_2026[FEATURE_COLS].fillna(0.0)
    y_2026 = train_2026["relevance"]

    decays = np.round(np.arange(0.4, 0.96, 0.05), 2).tolist()
    alphas = np.round(
        np.linspace(ALPHA_GRID["min"], ALPHA_GRID["max"], ALPHA_GRID["steps"]),
        2,
    ).tolist()

    best = {"score": -np.inf}
    for decay in decays:
        max_round = train_2026["round"].max() if not train_2026.empty else 0
        recency = (decay ** (max_round - train_2026["round"])) if max_round else pd.Series(
            [1.0] * len(train_2026), index=train_2026.index
        )
        group_w = group_weights(train_2026, ["round"], extra_weight=recency)
        cur_model = fit_ranker(X_2026, y_2026, train_groups, group_w)

        cur_scores = pd.Series(cur_model.predict(target[FEATURE_COLS].fillna(0.0)), index=target.index)
        cur_scores = clip_scores(cur_scores)
        hist_scores_t = target["driver_id"].map(hist_map).fillna(0.0)
        hist_scaled = scale_hist_to_current(hist_scores_t, cur_scores)

        for alpha in alphas:
            blended = alpha * cur_scores + (1 - alpha) * hist_scaled
            metrics = evaluate_round(target, blended)
            score = metrics["ndcg"] - 0.1 * metrics["mae"] + 0.1 * metrics["top3_hit"]
            if score > best["score"]:
                best = {
                    "score": score,
                    "decay": decay,
                    "alpha": float(alpha),
                    "metrics": metrics,
                }

    print("Best settings for Round", target_round)
    print("  recency_decay:", best["decay"])
    print("  alpha:", round(best["alpha"], 3))
    print("  NDCG:", round(best["metrics"]["ndcg"], 3))
    print("  Top-3 hit:", round(best["metrics"]["top3_hit"], 3))
    print("  MAE:", round(best["metrics"]["mae"], 3))


if __name__ == "__main__":
    main()
