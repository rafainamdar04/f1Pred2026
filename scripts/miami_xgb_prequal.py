"""
Train blended LambdaRank models (historical + 2026) and print Miami pre-qualifying
podium predictions to the terminal.
"""

from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import ndcg_score

from feature_engineer import SuzukaFeatureEngineer
from config.settings import CURRENT_SEASON, FEATURE_CONSTANTS, HISTORICAL_YEARS, PATHS, XGBOOST_PARAMS


def main():
    project_root = Path(__file__).resolve().parents[1]
    data_dir = project_root / PATHS["data"]

    engineer = SuzukaFeatureEngineer(data_dir=str(data_dir))
    standings_2026, results_2026, _ = engineer.load_data()
    historical_results = engineer.load_historical_results()

    feature_cols = [
        "current_points",
        "current_position",
        "wins",
        "podiums",
        "poles",
        "avg_finish_position",
        "avg_points_per_race",
        "races_completed",
        "last_race_finish",
        "last_race_points",
        "momentum",
        "constructor_avg_finish",
        "constructor_avg_points",
    ]

    target_round = 4

    def add_relevance_by_group(df, group_cols):
        df = df.copy()
        max_finish = df.groupby(group_cols)["finish_position"].transform("max")
        df["finish_position"] = df["finish_position"].fillna(max_finish + 1)
        df["relevance"] = (max_finish + 1) - df["finish_position"]
        return df

    def build_groups(df, group_cols):
        ordered = df.sort_values(group_cols + ["driver_id"]).reset_index(drop=True)
        group_sizes = ordered.groupby(group_cols, sort=True).size().tolist()
        group_keys = ordered[group_cols].drop_duplicates().itertuples(index=False, name=None)
        return ordered, group_sizes, list(group_keys)

    def season_decay_weight(season):
        years = sorted(HISTORICAL_YEARS)
        decay_values = [0.2, 0.3, 0.5, 0.7, 1.0]
        decay_map = dict(zip(years, decay_values[-len(years):]))
        weight = decay_map.get(int(season), 0.4)
        cutoff_year = years[1] if len(years) > 1 else years[0]
        if int(season) <= cutoff_year:
            weight *= 0.7
        return weight

    hist_training_df = engineer.prepare_prequal_training_data_for_results(historical_results)
    train_2026_df = engineer.prepare_prequal_training_data_for_results(results_2026)
    train_2026_df = train_2026_df[train_2026_df["race_round"] < target_round].copy()

    hist_training_df = add_relevance_by_group(hist_training_df, ["season", "race_round"])
    train_2026_df = add_relevance_by_group(train_2026_df, ["race_round"])

    hist_training_df, hist_groups, hist_group_keys = build_groups(hist_training_df, ["season", "race_round"])
    train_2026_df, train_2026_groups, _ = build_groups(train_2026_df, ["race_round"])

    X_hist = hist_training_df[feature_cols]
    y_hist = hist_training_df["relevance"]
    hist_group_weights = [season_decay_weight(season) for season, _ in hist_group_keys]

    X_2026 = train_2026_df[feature_cols]
    y_2026 = train_2026_df["relevance"]

    historical_model = xgb.XGBRanker(
        **XGBOOST_PARAMS,
        colsample_bytree=0.9,
        objective="rank:pairwise",
        eval_metric="ndcg",
        random_state=42,
        n_jobs=4,
        reg_lambda=1.0,
    )

    model_2026 = xgb.XGBRanker(
        **XGBOOST_PARAMS,
        colsample_bytree=0.9,
        objective="rank:pairwise",
        eval_metric="ndcg",
        random_state=42,
        n_jobs=4,
        reg_lambda=1.0,
    )

    if not hist_training_df.empty:
        historical_model.fit(X_hist, y_hist, group=hist_groups, sample_weight=hist_group_weights)
    if not train_2026_df.empty:
        model_2026.fit(X_2026, y_2026, group=train_2026_groups)

    if not train_2026_df.empty:
        eval_scores = model_2026.predict(X_2026)
        ndcg = ndcg_score([y_2026.to_numpy()], [eval_scores])
        print(f"{CURRENT_SEASON} pre-Miami ranking evaluation (Rounds < {target_round})")
        print("NDCG:", round(ndcg, 3))

    hist_features = engineer.prepare_historical_prequal_features(
        standings_2026,
        historical_results,
        rookie_penalty=1.5,
    )
    current_features = engineer.prepare_next_race_prequal_features()

    if not hist_training_df.empty:
        hist_scores = historical_model.predict(hist_features[feature_cols])
    else:
        hist_scores = pd.Series([0.0] * len(current_features))

    if not train_2026_df.empty:
        current_scores = model_2026.predict(current_features[feature_cols])
    else:
        current_scores = pd.Series([0.0] * len(current_features))

    current_scores = pd.Series(current_scores)
    hist_scores = pd.Series(hist_scores)

    if len(current_scores) > 0:
        low, high = current_scores.quantile(FEATURE_CONSTANTS["quantile_clip"])
        current_scores = current_scores.clip(lower=low, upper=high)

    alpha = 0.65
    predictions = current_features[[
        "driver_id",
        "driver_code",
        "driver_name",
        "constructor_name",
    ]].copy()
    predictions["score_2026"] = current_scores.values

    hist_map = pd.Series(hist_scores.values, index=hist_features["driver_id"]).to_dict()
    predictions["score_hist"] = predictions["driver_id"].map(hist_map).fillna(0.0)
    predictions["final_score"] = alpha * predictions["score_2026"] + (1 - alpha) * predictions["score_hist"]
    predictions = predictions.sort_values("final_score", ascending=False).reset_index(drop=True)

    podium = predictions.head(3).copy()
    podium_labels = ["P1", "P2", "P3"]
    podium.insert(0, "podium", podium_labels)

    print(f"\nMiami GP pre-qualifying podium prediction (Round {target_round}):")
    print(
        podium.to_string(
            index=False,
            formatters={
                "score_2026": "{:.3f}".format,
                "score_hist": "{:.3f}".format,
                "final_score": "{:.3f}".format,
            },
        )
    )


if __name__ == "__main__":
    main()
