"""
Generate hybrid (historical + 2026) LambdaRank predictions and print to terminal.
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

from config.settings import ALPHA_GRID, CURRENT_SEASON, FEATURE_CONSTANTS, PATHS


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


def _pick_best_alpha(results_2026: pd.DataFrame, hist_map: dict[str, float], model: xgb.XGBRanker) -> float:
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
            feature_cols = model.get_booster().feature_names or FEATURE_COLS
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


def _prepare_prequal_target(results_2026: pd.DataFrame, next_round: int) -> pd.DataFrame:
    latest = (
        results_2026.sort_values(["driver_id", "round"]).groupby("driver_id").tail(1).copy()
    )
    latest["round"] = next_round
    latest["race_name"] = f"Round {next_round}"
    latest["grid_position"] = np.nan
    return latest


def main() -> None:
    parser = argparse.ArgumentParser(description="Print hybrid LambdaRank predictions")
    parser.add_argument("--data-dir", default=PATHS["data"].rstrip("/"), help="Project data directory")
    parser.add_argument("--processed-dir", default=None, help="Override processed data directory")
    parser.add_argument(
        "--round",
        type=int,
        default=None,
        help=f"{CURRENT_SEASON} round to rank (default: latest)",
    )
    parser.add_argument("--alpha", default="auto", help="Blend weight for 2026 scores or 'auto'")
    parser.add_argument("--top", type=int, default=20, help="Rows to print")
    parser.add_argument(
        "--mode",
        choices=["race", "prequal"],
        default="race",
        help="Prediction mode: race uses grid if available; prequal ignores grid",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / args.data_dir
    processed_dir = (
        Path(args.processed_dir)
        if args.processed_dir
        else project_root / PATHS["processed"]
    )

    hist_path = project_root / PATHS["models"] / "historical_lambdarank.json"
    cur_path = project_root / PATHS["models"] / f"{CURRENT_SEASON}_lambdarank.json"

    historical = load_processed(processed_dir, "historical")
    results_2026 = load_processed(processed_dir, str(CURRENT_SEASON))

    if results_2026.empty:
        raise ValueError(f"{CURRENT_SEASON} features are empty. Run preprocessing first.")

    if args.mode == "prequal":
        next_round = int(results_2026["round"].max()) + 1
        round_num = args.round or next_round
        target = _prepare_prequal_target(results_2026, round_num)
    else:
        round_num = args.round or int(results_2026["round"].max())
        target = results_2026[results_2026["round"] == round_num].copy()

    if target.empty:
        raise ValueError(f"No {CURRENT_SEASON} features for round {round_num}")

    hist_model = xgb.XGBRanker()
    hist_model.load_model(hist_path)
    cur_model = xgb.XGBRanker()
    cur_model.load_model(cur_path)

    feature_cols = cur_model.get_booster().feature_names or FEATURE_COLS
    hist_scores = hist_model.predict(historical[feature_cols].fillna(0.0)) if not historical.empty else np.array([])
    
    # Properly aggregate historical scores by driver (average across all their races)
    if len(hist_scores):
        hist_scored = historical[["driver_id"]].copy()
        hist_scored["score"] = hist_scores
        hist_map = hist_scored.groupby("driver_id")["score"].mean().to_dict()
    else:
        hist_map = {}

    current_scores = cur_model.predict(target[feature_cols].fillna(0.0))
    current_scores = pd.Series(current_scores, index=target.index)
    current_scores = _clip_scores(current_scores)

    alpha = args.alpha
    if isinstance(alpha, str) and alpha.lower() == "auto":
        alpha = _pick_best_alpha(results_2026, hist_map, cur_model)
    alpha = float(alpha)
    output = target[ID_COLS].copy()
    output["score_2026"] = current_scores.values
    output["score_hist"] = output["driver_id"].map(hist_map).fillna(0.0)
    output["score_hist"] = _scale_hist_to_current(output["score_hist"], current_scores)
    output["final_score"] = _blend_scores(output["score_2026"], output["score_hist"], alpha)
    output["rationale"] = _rationale_from_features(target, feature_cols, cur_model)
    output = output.sort_values("final_score", ascending=False).reset_index(drop=True)

    race_name = output["race_name"].dropna().iloc[0] if "race_name" in output.columns else "unknown"
    mode_label = "pre-qual" if args.mode == "prequal" else "race"
    print(f"Hybrid predictions for {CURRENT_SEASON} Round {round_num} ({mode_label}): {race_name}")
    print(f"Blend alpha: {alpha:.3f}")
    print(output.head(args.top).to_string(index=False, formatters={
        "score_2026": "{:.3f}".format,
        "score_hist": "{:.3f}".format,
        "final_score": "{:.3f}".format,
    }))

    predictions_dir = project_root / PATHS["predictions"]
    predictions_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "round": int(round_num),
        "race_name": race_name,
        "mode": mode_label,
        "alpha": float(alpha),
        "rows": output.to_dict(orient="records"),
    }
    with (predictions_dir / f"round_{round_num}_predictions.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)


if __name__ == "__main__":
    main()
