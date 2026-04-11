"""
Hourly FastF1 historical refresh until coverage is complete.
"""

from pathlib import Path
import time

import pandas as pd
import fastf1

from fastf1_scraper import FastF1Scraper
from scrape_ergast_api import normalize_results, validate_schema
from config.settings import HISTORICAL_YEARS, PATHS

YEARS = HISTORICAL_YEARS
MIN_DRIVERS = 20
SLEEP_SECONDS = 3600
OUTPUT_FILE = Path(PATHS["data"]) / "historical_races.csv"


def load_existing():
    if OUTPUT_FILE.exists():
        df = pd.read_csv(OUTPUT_FILE)
        df = normalize_results(df, source="fastf1")
        validate_schema(df)
        return df
    return pd.DataFrame()


def expected_rounds(season):
    schedule = fastf1.get_event_schedule(season)
    rounds = schedule["RoundNumber"].dropna().astype(int)
    rounds = rounds[rounds > 0].tolist()
    return schedule, rounds


def missing_rounds(existing, season):
    schedule, rounds = expected_rounds(season)
    if existing.empty:
        return schedule, rounds

    season_rows = existing[existing["season"] == season]
    counts = season_rows.groupby("round")["driver_id"].nunique().to_dict()
    missing = [rnd for rnd in rounds if counts.get(rnd, 0) < MIN_DRIVERS]
    return schedule, missing


def fetch_missing_rounds(season, schedule, rounds):
    scraper = FastF1Scraper(output_dir=PATHS["data"])
    new_rows = []

    for rnd in rounds:
        race_results = scraper.get_race_results(season, rnd)
        if race_results is None or race_results.empty:
            continue
        race_date = None
        row = schedule[schedule["RoundNumber"].astype(int) == int(rnd)]
        if not row.empty:
            race_date = row.iloc[0].get("EventDate") or row.iloc[0].get("Session1Date")
        race_results["race_date"] = race_date
        new_rows.append(race_results)

    if not new_rows:
        return pd.DataFrame()

    df = pd.concat(new_rows, ignore_index=True)
    df = normalize_results(df, source="fastf1")
    validate_schema(df)
    return df


def merge_results(existing, incoming):
    if existing.empty:
        return incoming
    combined = pd.concat([existing, incoming], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["season", "round", "driver_id"],
        keep="last",
    )
    return combined


def main():
    while True:
        existing = load_existing()
        all_missing = []

        for season in YEARS:
            schedule, missing = missing_rounds(existing, season)
            if missing:
                all_missing.append((season, schedule, missing))

        if not all_missing:
            print(
                f"Historical coverage complete for {min(HISTORICAL_YEARS)}-"
                f"{max(HISTORICAL_YEARS)}. Stopping."
            )
            return

        for season, schedule, missing in all_missing:
            print(f"Season {season}: missing rounds {missing}")
            new_rows = fetch_missing_rounds(season, schedule, missing)
            if not new_rows.empty:
                existing = merge_results(existing, new_rows)

        if not existing.empty:
            existing.to_csv(OUTPUT_FILE, index=False)
            print(f"Saved {len(existing)} rows to {OUTPUT_FILE}")

        print(f"Waiting {SLEEP_SECONDS} seconds before next retry...")
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
