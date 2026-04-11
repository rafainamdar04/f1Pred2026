"""
Evaluate hybrid (historical + 2026) LambdaRank predictions against actual 2026 results.
"""

from __future__ import annotations

import argparse
import json
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
    PATHS,
    POST_QUALI_FEATURES,
    PRE_QUALI_FEATURES,
)


PRE_FEATURES = PRE_QUALI_FEATURES
POST_FEATURES = PRE_QUALI_FEATURES + POST_QUALI_FEATURES


def load_processed(processed_dir: Path, name: str) -> pd.DataFrame:
    parquet_path = processed_dir / f"{name}_features.parquet"
    csv_path = processed_dir / f"{name}_features.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(f"Missing processed dataset: {parquet_path} or {csv_path}")


def _clip_scores(scores: pd.Series) -> pd.Series:
    if scores.empty:
        return scores
    low, high = scores.quantile(FEATURE_CONSTANTS["quantile_clip"])
    return scores.clip(lower=low, upper=high)


def _scale_hist_to_current(hist_scores: pd.Series, current_scores: pd.Series) -> pd.Series:
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


def _blend_scores(current_scores: pd.Series, hist_scores: pd.Series, alpha: float) -> pd.Series:
    return alpha * current_scores + (1 - alpha) * hist_scores


def _pick_best_alpha(
    results_2026: pd.DataFrame,
    hist_map: dict[str, float],
    model: xgb.XGBRanker,
    feature_cols: list[str],
) -> float:
    completed = results_2026.groupby("round")["finish_position"].apply(lambda s: s.notna().all())
    rounds = sorted(completed[completed].index.tolist())
    if not rounds:
        return 0.65

    alphas = np.linspace(ALPHA_GRID["min"], ALPHA_GRID["max"], ALPHA_GRID["steps"])
    best_alpha = 0.65
    best_score = -np.inf

    for alpha in alphas:
        scores = []
        for round_num in rounds:
            df = results_2026[results_2026["round"] == round_num].dropna(subset=["finish_position"]).copy()
            if df.empty:
                continue
            cur = pd.Series(model.predict(df[feature_cols].fillna(0.0)), index=df.index)
            cur = _clip_scores(cur)
            hist = df["driver_id"].map(hist_map).fillna(0.0)
            hist = _scale_hist_to_current(hist, cur)
            blended = _blend_scores(cur, hist, alpha)
            max_finish = df["finish_position"].max()
            relevance = (max_finish + 1) - df["finish_position"]
            scores.append(float(ndcg_score([relevance.to_numpy()], [blended.to_numpy()])))
        if scores:
            avg_score = float(np.mean(scores))
            if avg_score > best_score:
                best_score = avg_score
                best_alpha = float(alpha)

    return best_alpha


def build_hist_score_map(
    hist_features: pd.DataFrame,
    model: xgb.XGBRanker,
    feature_cols: list[str],
) -> dict[str, float]:
    if hist_features.empty:
        return {}
    scores = model.predict(hist_features[feature_cols].fillna(0.0))
    scored = hist_features[["driver_id"]].copy()
    scored["score"] = scores
    return scored.groupby("driver_id")["score"].mean().to_dict()


def _effective_finish(df: pd.DataFrame) -> pd.Series:
    if "dnf_flag" not in df.columns:
        return df["finish_position"]
    max_finish = df["finish_position"].max()
    return np.where(df["dnf_flag"].fillna(0).astype(int) == 1, max_finish + 1, df["finish_position"])


def evaluate_round(
    df: pd.DataFrame,
    hist_map: dict[str, float],
    model: xgb.XGBRanker,
    alpha: float,
    feature_cols: list[str],
) -> dict:
    df = df.dropna(subset=["finish_position"]).copy()
    if df.empty:
        return {}

    scores_2026 = model.predict(df[feature_cols].fillna(0.0))
    scores_2026 = pd.Series(scores_2026, index=df.index)
    scores_2026 = _clip_scores(scores_2026)

    df["score_2026"] = scores_2026.values
    df["score_hist"] = df["driver_id"].map(hist_map).fillna(0.0)
    df["score_hist"] = _scale_hist_to_current(df["score_hist"], scores_2026)
    df["final_score"] = _blend_scores(df["score_2026"], df["score_hist"], alpha)

    effective_finish = pd.Series(_effective_finish(df), index=df.index)
    max_finish = effective_finish.max()
    relevance = (max_finish + 1) - effective_finish
    ndcg = ndcg_score([relevance.to_numpy()], [df["final_score"].to_numpy()])

    pred_rank = df.sort_values("final_score", ascending=False).reset_index(drop=True)
    actual_rank = df.assign(effective_finish=effective_finish).sort_values(
        "effective_finish", ascending=True
    ).reset_index(drop=True)

    pred_top3 = set(pred_rank.head(3)["driver_id"])
    actual_top3 = set(actual_rank.head(3)["driver_id"])
    top3_hit = len(pred_top3 & actual_top3) / 3.0

    rank_map = pd.Series(range(1, len(pred_rank) + 1), index=pred_rank["driver_id"]).to_dict()
    df["pred_rank"] = df["driver_id"].map(rank_map)
    df["abs_rank_error"] = (df["pred_rank"] - effective_finish).abs()
    mae = df["abs_rank_error"].mean()

    misses = df.sort_values("final_score", ascending=False).head(6)
    misses = misses[misses["finish_position"] > 10]

    # Debug: track top-3 details
    top3_detail = {
        "predicted": list(pred_top3),
        "actual": list(actual_top3),
        "intersection": list(pred_top3 & actual_top3),
        "precision_count": len(pred_top3 & actual_top3),
    }

    return {
        "ndcg": ndcg,
        "top3_hit": top3_hit,
        "mae": mae,
        "misses": misses[["driver_id", "constructor_id", "finish_position", "final_score"]],
        "top3_detail": top3_detail,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate hybrid predictions vs actual 2026 results")
    parser.add_argument("--data-dir", default=PATHS["data"].rstrip("/"), help="Project data directory")
    parser.add_argument("--processed-dir", default=None, help="Override processed data directory")
    parser.add_argument("--alpha", default="auto", help="Blend weight for 2026 scores or 'auto'")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / args.data_dir
    processed_dir = (
        Path(args.processed_dir)
        if args.processed_dir
        else project_root / PATHS["processed"]
    )

    pre_hist_path = project_root / PATHS["models"] / "prequali_historical_lambdarank.json"
    pre_cur_path = project_root / PATHS["models"] / f"prequali_{CURRENT_SEASON}_lambdarank.json"
    post_hist_path = project_root / PATHS["models"] / "postquali_historical_lambdarank.json"
    post_cur_path = project_root / PATHS["models"] / f"postquali_{CURRENT_SEASON}_lambdarank.json"

    historical = load_processed(processed_dir, "historical")
    results_2026 = load_processed(processed_dir, str(CURRENT_SEASON))

    pre_hist_model = xgb.XGBRanker()
    pre_hist_model.load_model(pre_hist_path)
    pre_cur_model = xgb.XGBRanker()
    pre_cur_model.load_model(pre_cur_path)
    post_hist_model = xgb.XGBRanker()
    post_hist_model.load_model(post_hist_path)
    post_cur_model = xgb.XGBRanker()
    post_cur_model.load_model(post_cur_path)

    pre_hist_map = build_hist_score_map(historical, pre_hist_model, PRE_FEATURES)
    post_hist_map = build_hist_score_map(historical, post_hist_model, POST_FEATURES)

    round_status = (
        results_2026.groupby("round")["finish_position"]
        .apply(lambda s: s.notna().all())
    )
    rounds = sorted(round_status[round_status].index.tolist())
    if not rounds:
        raise ValueError("No completed 2026 rounds found in processed data.")

    alpha = args.alpha
    if isinstance(alpha, str) and alpha.lower() == "auto":
        alpha_pre = _pick_best_alpha(results_2026, pre_hist_map, pre_cur_model, PRE_FEATURES)
        alpha_post = _pick_best_alpha(results_2026, post_hist_map, post_cur_model, POST_FEATURES)
    else:
        alpha_pre = float(alpha)
        alpha_post = float(alpha)

    pre_metrics = []
    post_metrics = []
    metrics_rows = []
    for round_num in rounds:
        round_df = results_2026[results_2026["round"] == round_num].copy()
        pre_result = evaluate_round(round_df, pre_hist_map, pre_cur_model, alpha_pre, PRE_FEATURES)
        post_result = evaluate_round(round_df, post_hist_map, post_cur_model, alpha_post, POST_FEATURES)
        if not pre_result or not post_result:
            continue
        pre_metrics.append(pre_result)
        post_metrics.append(post_result)

        metrics_rows.append({
            "round": int(round_num),
            "prequali": {
                "ndcg": float(pre_result["ndcg"]),
                "top3_hit": float(pre_result["top3_hit"]),
                "mae": float(pre_result["mae"]),
                "alpha": float(alpha_pre),
            },
            "postquali": {
                "ndcg": float(post_result["ndcg"]),
                "top3_hit": float(post_result["top3_hit"]),
                "mae": float(post_result["mae"]),
                "alpha": float(alpha_post),
            },
        })

        better = "prequali" if pre_result["ndcg"] >= post_result["ndcg"] else "postquali"
        print(f"Round {int(round_num)} metrics:")
        print(f"  Prequali NDCG@full: {pre_result['ndcg']:.3f}")
        print(f"  Postquali NDCG@full: {post_result['ndcg']:.3f}")
        print(f"  Better model: {better}")
        print(f"  Prequali Top-3 hit: {pre_result['top3_hit']:.3f}")
        print(f"  Postquali Top-3 hit: {post_result['top3_hit']:.3f}")
        print(f"  Prequali MAE: {pre_result['mae']:.2f}")
        print(f"  Postquali MAE: {post_result['mae']:.2f}")
        print()

    if pre_metrics and post_metrics:
        pre_avg_ndcg = float(np.mean([m["ndcg"] for m in pre_metrics]))
        pre_avg_top3 = float(np.mean([m["top3_hit"] for m in pre_metrics]))
        pre_avg_mae = float(np.mean([m["mae"] for m in pre_metrics]))
        post_avg_ndcg = float(np.mean([m["ndcg"] for m in post_metrics]))
        post_avg_top3 = float(np.mean([m["top3_hit"] for m in post_metrics]))
        post_avg_mae = float(np.mean([m["mae"] for m in post_metrics]))
        print("Overall metrics:")
        print(f"  Prequali Avg NDCG@full: {pre_avg_ndcg:.3f}")
        print(f"  Postquali Avg NDCG@full: {post_avg_ndcg:.3f}")

        metrics_dir = project_root / PATHS["metrics"]
        metrics_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "rounds": metrics_rows,
            "overall": {
                "prequali": {
                    "ndcg": pre_avg_ndcg,
                    "top3_hit": pre_avg_top3,
                    "mae": pre_avg_mae,
                    "alpha": float(alpha_pre),
                },
                "postquali": {
                    "ndcg": post_avg_ndcg,
                    "top3_hit": post_avg_top3,
                    "mae": post_avg_mae,
                    "alpha": float(alpha_post),
                },
            },
        }
        with (metrics_dir / "metrics_summary.json").open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
