"""
Generate pre-qualifying predictions using pace-only features.
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

from config.settings import ALPHA_GRID, CURRENT_SEASON, FEATURE_CONSTANTS, PATHS, PRE_QUALI_FEATURES


ID_COLS = ["season", "round", "race_name", "circuit_id", "driver_id", "constructor_id"]


def load_processed(processed_dir: Path, name: str) -> pd.DataFrame:
    parquet_path = processed_dir / f"{name}_features.parquet"
    csv_path = processed_dir / f"{name}_features.csv"
    if parquet_path.exists():
        try:
            return pd.read_parquet(parquet_path)
        except ImportError:
            if csv_path.exists():
                return pd.read_csv(csv_path)
            raise
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


def _pick_best_alpha(results_df: pd.DataFrame, hist_map: dict[str, float], model: xgb.XGBRanker) -> float:
    completed = results_df.groupby("round")["finish_position"].apply(lambda s: s.notna().all())
    rounds = sorted(completed[completed].index.tolist())
    if not rounds:
        return 0.65

    alphas = np.linspace(ALPHA_GRID["min"], ALPHA_GRID["max"], ALPHA_GRID["steps"])
    best_alpha = 0.65
    best_score = -np.inf

    for alpha in alphas:
        scores = []
        for round_num in rounds:
            df = results_df[results_df["round"] == round_num].dropna(subset=["finish_position"]).copy()
            if df.empty:
                continue
            cur = pd.Series(model.predict(df[PRE_QUALI_FEATURES].fillna(0.0)), index=df.index)
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


def _rationale_from_features(
    target: pd.DataFrame,
    feature_cols: list[str],
    model: xgb.XGBRanker,
    top_k: int = 3,
) -> pd.Series:
    importance = model.get_booster().get_score(importance_type="gain")
    weights = pd.Series({col: float(importance.get(col, 0.0)) for col in feature_cols})
    if weights.sum() == 0:
        return pd.Series(["" for _ in range(len(target))], index=target.index)

    values = target[feature_cols].fillna(0.0)
    z = (values - values.mean()) / (values.std(ddof=0).replace(0, 1.0))
    contrib = z.mul(weights, axis=1)
    rationale = []
    for _, row in contrib.iterrows():
        top = row.reindex(row.abs().sort_values(ascending=False).index).head(top_k)
        parts = [f"{name}:{val:.2f}" for name, val in top.items()]
        rationale.append("; ".join(parts))
    return pd.Series(rationale, index=target.index)


def _prepare_prequal_target(results_df: pd.DataFrame, next_round: int, race_name: str) -> pd.DataFrame:
    latest = results_df.sort_values(["driver_id", "round"]).groupby("driver_id").tail(1).copy()
    latest["round"] = next_round
    latest["race_name"] = race_name
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate pre-qualifying predictions")
    parser.add_argument("--round", type=int, required=True, help="Round number to rank")
    parser.add_argument("--race-name", type=str, required=True, help="Race name label")
    parser.add_argument("--data-dir", default=PATHS["data"].rstrip("/"), help="Project data directory")
    parser.add_argument("--processed-dir", default=None, help="Override processed data directory")
    args = parser.parse_args()

    data_dir = PROJECT_ROOT / args.data_dir
    processed_dir = Path(args.processed_dir) if args.processed_dir else PROJECT_ROOT / PATHS["processed"]

    hist_path = PROJECT_ROOT / PATHS["models"] / "prequali_historical_lambdarank.json"
    cur_path = PROJECT_ROOT / PATHS["models"] / f"prequali_{CURRENT_SEASON}_lambdarank.json"

    historical = load_processed(processed_dir, "historical")
    results_current = load_processed(processed_dir, str(CURRENT_SEASON))

    hist_model = xgb.XGBRanker()
    hist_model.load_model(hist_path)
    cur_model = xgb.XGBRanker()
    cur_model.load_model(cur_path)

    if (results_current["round"] == args.round).any():
        target = results_current[results_current["round"] == args.round].copy()
    else:
        target = _prepare_prequal_target(results_current, args.round, args.race_name)

    hist_scores = hist_model.predict(historical[PRE_QUALI_FEATURES].fillna(0.0)) if not historical.empty else np.array([])
    if len(hist_scores):
        hist_scored = historical[["driver_id"]].copy()
        hist_scored["score"] = hist_scores
        hist_map = hist_scored.groupby("driver_id")["score"].mean().to_dict()
    else:
        hist_map = {}

    current_scores = cur_model.predict(target[PRE_QUALI_FEATURES].fillna(0.0))
    current_scores = pd.Series(current_scores, index=target.index)
    current_scores = _clip_scores(current_scores)

    alpha = _pick_best_alpha(results_current, hist_map, cur_model)

    output = target[ID_COLS].copy()
    output["score_2026"] = current_scores.values
    output["score_hist"] = output["driver_id"].map(hist_map).fillna(0.0)
    output["score_hist"] = _scale_hist_to_current(output["score_hist"], current_scores)
    output["final_score"] = _blend_scores(output["score_2026"], output["score_hist"], alpha)
    output["rationale"] = _rationale_from_features(target, PRE_QUALI_FEATURES, cur_model)
    output = output.sort_values("final_score", ascending=False).reset_index(drop=True)

    payload = {
        "round": int(args.round),
        "race_name": args.race_name,
        "mode": "prequali",
        "alpha": float(alpha),
        "rows": output.to_dict(orient="records"),
    }

    predictions_dir = PROJECT_ROOT / PATHS["predictions"]
    predictions_dir.mkdir(parents=True, exist_ok=True)
    out_path = predictions_dir / f"round_{args.round}_prequali_predictions.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)

    print(f"Saved prequali predictions to {out_path}")


if __name__ == "__main__":
    main()
