"""
Main data collection script - Combines Ergast API and 2026 season data
"""

from scripts.scrape_ergast_api import ErgastScraper
from scripts.scrape_2026_season import F1_2026_Scraper
from scripts.generate_synthetic_data import SyntheticF1DataGenerator
from scripts.fastf1_scraper import FastF1Scraper
import pandas as pd


def _standardize_driver_code(df):
    df = df.copy()
    if "driver_code" not in df.columns and "driver_id" in df.columns:
        df["driver_code"] = df["driver_id"]
    if "driver_code" in df.columns:
        df["driver_code"] = df["driver_code"].astype(str).str.upper()
    return df


def _combine_historical(primary_df, fallback_df):
    if primary_df is None or primary_df.empty:
        return fallback_df
    if fallback_df is None or fallback_df.empty:
        return primary_df

    primary_df = _standardize_driver_code(primary_df)
    fallback_df = _standardize_driver_code(fallback_df)

    combined = pd.concat(
        [
            primary_df.assign(_source_priority=0),
            fallback_df.assign(_source_priority=1),
        ],
        ignore_index=True,
    )
    combined = combined.sort_values("_source_priority").drop_duplicates(
        subset=["season", "round", "driver_code"],
        keep="first",
    )
    return combined.drop(columns=["_source_priority"])

def main():
    print("\n" + "=" * 70)
    print("F1 2026 RACE WINNER PREDICTION - DATA COLLECTION")
    print("=" * 70)
    
    # Phase 1a: Scrape historical data
    print("\n[PHASE 1a] SCRAPING HISTORICAL DATA (2021-2025)")
    print("-" * 70)
    years = [2021, 2022, 2023, 2024, 2025]

    fastf1_hist = FastF1Scraper(output_dir="data")
    fastf1_hist_df = fastf1_hist.fetch_historical_results(seasons=years)

    ergast = ErgastScraper(output_dir="data")
    ergast_df = ergast.build_comprehensive_dataset(years=years)

    historical_df = _combine_historical(fastf1_hist_df, ergast_df)
    
    # If API fails, use synthetic data
    if len(historical_df) == 0:
        print("⚠ API unavailable, generating realistic synthetic data instead...")
        generator = SyntheticF1DataGenerator()
        historical_df = generator.generate_seasons(years=years)
    
    ergast.save_data(historical_df, "historical_races.csv")
    
    # Phase 1b: Scrape 2026 season data
    print("\n[PHASE 1b] SCRAPING 2026 SEASON DATA")
    print("-" * 70)
    
    scraper_2026 = F1_2026_Scraper()
    standings, qualifying, practice, history = scraper_2026.save_2026_data(output_dir="data")
    
    # Print summary
    print("\n" + "=" * 70)
    print("DATA COLLECTION COMPLETE")
    print("=" * 70)
    
    print("\n📊 DATASET SUMMARY:")
    print(f"  • Historical races (2021-2025): {len(historical_df)} records")
    print(f"  • Seasons covered: {sorted(historical_df['season'].unique())}")
    print(f"  • Race rounds per season: {list(historical_df.groupby('season')['round'].max())}")
    print(f"  • Unique drivers in history: {historical_df['driver_id'].nunique()}")
    print(f"  • Unique constructors: {historical_df['constructor_id'].nunique()}")
    
    print(f"\n🏁 2026 SEASON DATA (as of March 29, 2026):")
    print(f"  • Current standings: {len(standings)} drivers")
    print(f"  • Suzuka qualifying grid: {len(qualifying)} drivers")
    print(f"  • Practice session data collected: ✓")
    print(f"  • Suzuka track history: {len(history)} years")
    
    print("\n📁 Files saved to data/:")
    print("  ✓ historical_races.csv (2023-2025 all races)")
    print("  ✓ 2026_driver_standings.csv")
    print("  ✓ 2026_suzuka_qualifying.csv")
    print("  ✓ 2026_suzuka_practice.csv")
    print("  ✓ suzuka_track_history.csv")
    
    # Display sample data
    print("\n" + "=" * 70)
    print("SAMPLE: Historical Race Data (First 5 records)")
    print("=" * 70)
    print(historical_df[['season', 'round', 'race_name', 'driver_code', 
                         'constructor_name', 'grid_position', 'finish_position', 'points']].head().to_string(index=False))
    
    print("\n" + "=" * 70)
    print("SAMPLE: 2026 Current Driver Standings")
    print("=" * 70)
    print(standings[['rank', 'driver_code', 'driver_name', 'constructor_name', 'points', 'wins']].head(10).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("SAMPLE: Suzuka Qualifying Grid (Race 3)")
    print("=" * 70)
    print(qualifying[['position', 'driver_code', 'driver_name', 'constructor_name', 'quali_gap']].head(10).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("✓ READY FOR FEATURE ENGINEERING")
    print("=" * 70)


if __name__ == "__main__":
    main()
