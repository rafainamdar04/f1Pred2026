"""
Ergast API Scraper for F1 Historical Data (2023-2025)
Fetches driver standings, race results, and qualifying data
"""

import requests
import pandas as pd
import time
from pathlib import Path

from config.settings import HISTORICAL_YEARS, PATHS

BASE_URL = "http://ergast.com/api/f1"

CANONICAL_COLUMNS = [
    "season",
    "round",
    "race_date",
    "race_name",
    "circuit_id",
    "circuit_name",
    "driver_id",
    "driver_code",
    "constructor_id",
    "constructor_name",
    "grid_position",
    "finish_position",
    "points",
    "source",
]


def normalize_results(df, source):
    df = df.copy()

    if "driver_id" not in df.columns and "driver_code" in df.columns:
        df["driver_id"] = df["driver_code"]
    if "constructor_id" not in df.columns and "constructor_name" in df.columns:
        df["constructor_id"] = df["constructor_name"]

    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    df["source"] = source

    for col in ["season", "round", "grid_position", "finish_position"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0.0)

    return df[CANONICAL_COLUMNS]


def validate_schema(df):
    missing = [col for col in CANONICAL_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df

class ErgastScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        
    def get_season_races(self, year):
        """Fetch all races for a given season"""
        url = f"{BASE_URL}/{year}.json"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            races = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
            print(f"✓ Fetched {len(races)} races for {year}")
            return races
        except Exception as e:
            print(f"✗ Error fetching races for {year}: {e}")
            return []
    
    def get_race_results(self, year, round_num):
        """Fetch race results for a specific round"""
        url = f"{BASE_URL}/{year}/{round_num}/results.json"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])[0].get('Results', [])
            return results
        except Exception as e:
            print(f"  ✗ Error fetching results for {year} R{round_num}: {e}")
            return []
    
    def get_qualifying_results(self, year, round_num):
        """Fetch qualifying results for a specific round"""
        url = f"{BASE_URL}/{year}/{round_num}/qualifying.json"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            qualifying = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])[0].get('QualifyingResults', [])
            return qualifying
        except Exception as e:
            print(f"  ✗ Error fetching qualifying for {year} R{round_num}: {e}")
            return []
    
    def get_driver_standings(self, year, round_num=None):
        """Fetch driver standings for a season or after specific round"""
        if round_num:
            url = f"{BASE_URL}/{year}/{round_num}/driverStandings.json"
        else:
            url = f"{BASE_URL}/{year}/driverStandings.json"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            standings = data.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
            return standings
        except Exception as e:
            print(f"  ✗ Error fetching standings for {year}: {e}")
            return []
    
    def get_constructor_standings(self, year, round_num=None):
        """Fetch constructor standings for a season or after specific round"""
        if round_num:
            url = f"{BASE_URL}/{year}/{round_num}/constructorStandings.json"
        else:
            url = f"{BASE_URL}/{year}/constructorStandings.json"
        try:
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            standings = data.get('MRData', {}).get('StandingsTable', {}).get('StandingsLists', [])
            return standings
        except Exception as e:
            print(f"  ✗ Error fetching constructor standings for {year}: {e}")
            return []
    
    def build_comprehensive_dataset(self, years=None):
        """Build comprehensive dataset combining all data"""
        if years is None:
            years = HISTORICAL_YEARS
        all_races_data = []
        
        for year in years:
            print(f"\n📊 Processing {year}...")
            races = self.get_season_races(year)
            
            for race in races:
                round_num = race.get('round')
                race_name = race.get('name', 'Unknown')
                race_date = race.get('date', 'N/A')
                circuit = race.get('Circuit', {})
                circuit_name = circuit.get('circuitName', 'Unknown')
                circuit_id = circuit.get('circuitId', 'unknown')
                
                print(f"  Round {round_num}: {race_name} ({race_date})")
                
                # Get results
                results = self.get_race_results(year, round_num)
                qualifying = self.get_qualifying_results(year, round_num)
                
                # Build qualifying lookup
                qual_lookup = {}
                for qual in qualifying:
                    driver_id = qual.get('Driver', {}).get('driverId')
                    grid_pos = qual.get('position')
                    q3_time = qual.get('Q3', qual.get('Q2', qual.get('Q1')))
                    qual_lookup[driver_id] = {'grid': grid_pos, 'best_time': q3_time}
                
                # Process results
                for result in results:
                    driver_id = result.get('Driver', {}).get('driverId')
                    driver_code = result.get('Driver', {}).get('code', 'N/A')
                    constructor_id = result.get('Constructor', {}).get('constructorId')
                    constructor_name = result.get('Constructor', {}).get('name')
                    
                    position = result.get('position', 'N/A')
                    points = result.get('points', 0)
                    grid = result.get('grid', 'N/A')
                    
                    qual_info = qual_lookup.get(driver_id, {})
                    grid_pos = qual_info.get('grid', grid)
                    
                    race_record = {
                        'season': year,
                        'round': round_num,
                        'race_date': race_date,
                        'race_name': race_name,
                        'circuit_id': circuit_id,
                        'circuit_name': circuit_name,
                        'driver_id': driver_id,
                        'driver_code': driver_code,
                        'constructor_id': constructor_id,
                        'constructor_name': constructor_name,
                        'grid_position': int(grid_pos) if grid_pos != 'N/A' else None,
                        'finish_position': int(position) if position != 'N/A' else None,
                        'points': float(points),
                    }
                    all_races_data.append(race_record)
                
                time.sleep(0.1)  # Be nice to the API
        
        df = pd.DataFrame(all_races_data)
        df = normalize_results(df, source="ergast")
        validate_schema(df)
        return df
    
    def save_data(self, df, filename="historical_races.csv"):
        """Save dataframe to CSV"""
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        print(f"\n✓ Saved {len(df)} records to {filepath}")
        return filepath


def main():
    print("=" * 60)
    print("F1 ERGAST API SCRAPER (2023-2025)")
    print("=" * 60)
    
    scraper = ErgastScraper(output_dir=PATHS["data"])
    
    # Scrape comprehensive dataset
    df = scraper.build_comprehensive_dataset(years=HISTORICAL_YEARS)
    
    # Save
    scraper.save_data(df, "historical_races.csv")
    
    # Display summary
    print("\n" + "=" * 60)
    print("DATA SUMMARY")
    print("=" * 60)
    print(f"Total records: {len(df)}")
    print(f"Seasons: {sorted(df['season'].unique())}")
    print(f"Races per season: {df.groupby('season')['round'].max().to_dict()}")
    print(f"Total drivers: {df['driver_id'].nunique()}")
    print(f"Total constructors: {df['constructor_id'].nunique()}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nFirst rows:\n{df.head(10)}")
    print(f"\nData types:\n{df.dtypes}")


if __name__ == "__main__":
    main()
