"""
F1 API (f1api.dev) Scraper for 2026 Data
Real-time F1 data from https://f1api.dev
"""

import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
import time

from config.settings import CURRENT_SEASON, PATHS

class F1APIv1Scraper:
    """Fetch real F1 2026 data from f1api.dev"""
    
    BASE_URL = "https://api.f1api.dev/v1"
    
    def __init__(self, output_dir=PATHS["data"]):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({'Accept': 'application/json'})
    
    def get_current_season(self):
        """Get current season information"""
        try:
            url = f"{self.BASE_URL}/current"
            print(f"  Fetching: GET {url}")
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            print(f"  ✓ Response received")
            return data
        except Exception as e:
            print(f"  ✗ Error fetching current season: {e}")
            return {}
    
    def get_races(self, season=CURRENT_SEASON):
        """Fetch all races for a season"""
        try:
            url = f"{self.BASE_URL}/races"
            params = {'season': season}
            print(f"  Fetching: GET {url}?season={season}")
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            races = data.get('races', [])
            print(f"  ✓ Fetched {len(races)} races for season {season}")
            return races
        except Exception as e:
            print(f"  ✗ Error fetching races: {e}")
            return []
    
    def get_standings(self, season=CURRENT_SEASON, round_num=None):
        """Fetch standings for season or specific round"""
        try:
            if round_num:
                url = f"{self.BASE_URL}/standings"
                params = {'season': season, 'round': round_num}
                print(f"  Fetching: GET {url}?season={season}&round={round_num}")
            else:
                url = f"{self.BASE_URL}/standings"
                params = {'season': season}
                print(f"  Fetching: GET {url}?season={season}")
            
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            standings = data.get('standings', [])
            print(f"  ✓ Fetched standings")
            return standings
        except Exception as e:
            print(f"  ✗ Error fetching standings: {e}")
            return []
    
    def get_race_results(self, season=CURRENT_SEASON, round_num=1):
        """Fetch results for specific race"""
        try:
            url = f"{self.BASE_URL}/races/{round_num}/results"
            params = {'season': season}
            print(f"  Fetching: GET {url}?season={season}")
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get('results', [])
            print(f"  ✓ Fetched {len(results)} results for race {round_num}")
            return results
        except Exception as e:
            print(f"  ✗ Error fetching race results for round {round_num}: {e}")
            return []
    
    def get_qualifying_results(self, season=CURRENT_SEASON, round_num=1):
        """Fetch qualifying results for specific race"""
        try:
            url = f"{self.BASE_URL}/races/{round_num}/qualifying"
            params = {'season': season}
            print(f"  Fetching: GET {url}?season={season}")
            resp = self.session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            qualifying = data.get('results', [])
            print(f"  ✓ Fetched {len(qualifying)} qualifying results for race {round_num}")
            return qualifying
        except Exception as e:
            print(f"  ✗ Error fetching qualifying for round {round_num}: {e}")
            return []
    
    def parse_standings(self, standings_data):
        """Parse standings into DataFrame"""
        rows = []
        for standing in standings_data:
            driver = standing.get('driver', {})
            constructor = standing.get('constructor', {})
            
            row = {
                'position': standing.get('position'),
                'driver_id': driver.get('id'),
                'driver_code': driver.get('code'),
                'driver_name': driver.get('name'),
                'driver_number': driver.get('number'),
                'constructor_id': constructor.get('id'),
                'constructor_name': constructor.get('name'),
                'points': standing.get('points'),
                'wins': standing.get('wins'),
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def parse_race_results(self, season, round_num, race_name, circuit_name, results_data):
        """Parse race results into DataFrame"""
        rows = []
        for result in results_data:
            driver = result.get('driver', {})
            constructor = result.get('constructor', {})
            
            row = {
                'season': season,
                'round': round_num,
                'race_name': race_name,
                'circuit_name': circuit_name,
                'driver_id': driver.get('id'),
                'driver_code': driver.get('code'),
                'driver_name': driver.get('name'),
                'driver_number': driver.get('number'),
                'constructor_id': constructor.get('id'),
                'constructor_name': constructor.get('name'),
                'grid_position': result.get('grid'),
                'finish_position': result.get('position'),
                'points': result.get('points'),
                'status': result.get('status'),
                'time': result.get('time'),
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def parse_qualifying(self, season, round_num, race_name, circuit_name, qualifying_data):
        """Parse qualifying results into DataFrame"""
        rows = []
        for qual in qualifying_data:
            driver = qual.get('driver', {})
            constructor = qual.get('constructor', {})
            
            row = {
                'season': season,
                'round': round_num,
                'race_name': race_name,
                'circuit_name': circuit_name,
                'grid_position': qual.get('position'),
                'driver_id': driver.get('id'),
                'driver_code': driver.get('code'),
                'driver_name': driver.get('name'),
                'driver_number': driver.get('number'),
                'constructor_id': constructor.get('id'),
                'constructor_name': constructor.get('name'),
                'q1_time': qual.get('Q1'),
                'q2_time': qual.get('Q2'),
                'q3_time': qual.get('Q3'),
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def fetch_2026_season(self):
        """Fetch complete 2026 season data"""
        season = CURRENT_SEASON
        print(f"\n📊 Fetching {season} season data from f1api.dev...\n")
        
        # Get standings
        print("📋 STANDINGS:")
        standings_data = self.get_standings(season)
        standings_df = self.parse_standings(standings_data) if standings_data else pd.DataFrame()
        
        if not standings_df.empty:
            standings_df.to_csv(self.output_dir / f"{CURRENT_SEASON}_standings.csv", index=False)
            print(f"✓ Saved standings to {CURRENT_SEASON}_standings.csv\n")
        
        # Get all races
        print("🏁 RACES:")
        races = self.get_races(season)
        
        all_results = []
        all_qualifying = []
        
        for race in races:
            round_num = int(race.get('round', 0))
            race_name = race.get('raceName', f'Race {round_num}')
            circuit = race.get('circuit', {})
            circuit_name = circuit.get('circuitName', 'Unknown')
            race_date = race.get('date', '')
            
            print(f"\n  Round {round_num}: {race_name} ({race_date})")
            
            # Get race results (if race happened)
            results = self.get_race_results(season, round_num)
            if results:
                results_df = self.parse_race_results(season, round_num, race_name, circuit_name, results)
                all_results.append(results_df)
            
            # Get qualifying results
            qualifying = self.get_qualifying_results(season, round_num)
            if qualifying:
                qual_df = self.parse_qualifying(season, round_num, race_name, circuit_name, qualifying)
                all_qualifying.append(qual_df)
            
            time.sleep(0.5)  # Rate limiting
        
        # Combine all data
        results_df_full = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        qualifying_df_full = pd.concat(all_qualifying, ignore_index=True) if all_qualifying else pd.DataFrame()
        
        # Save
        if not results_df_full.empty:
            results_df_full.to_csv(self.output_dir / f"{CURRENT_SEASON}_race_results.csv", index=False)
            print(f"\n✓ Saved {len(results_df_full)} race results")
        
        if not qualifying_df_full.empty:
            qualifying_df_full.to_csv(self.output_dir / f"{CURRENT_SEASON}_qualifying.csv", index=False)
            print(f"✓ Saved {len(qualifying_df_full)} qualifying sessions")
        
        return standings_df, results_df_full, qualifying_df_full


def main():
    print("=" * 70)
    print("F1 API (f1api.dev) SCRAPER - 2026 REAL DATA")
    print("=" * 70)
    
    scraper = F1APIv1Scraper(output_dir=PATHS["data"])
    standings, results, qualifying = scraper.fetch_2026_season()
    
    print("\n" + "=" * 70)
    print("2026 SEASON DATA SUMMARY")
    print("=" * 70)
    
    if not standings.empty:
        print(f"\n📊 STANDINGS ({len(standings)} drivers):")
        print(standings[['position', 'driver_code', 'driver_name', 'constructor_name', 'points', 'wins']].head(12).to_string(index=False))
    else:
        print(f"\n⚠ No standings data available")
    
    if not results.empty:
        print(f"\n🏁 RACE RESULTS ({results['round'].nunique()} races completed):")
        print(f"   Rounds: {sorted(results['round'].unique())}")
        print(f"   Sample (First 5 from Round 1):")
        race_1 = results[results['round'] == 1].sort_values('finish_position')
        print(race_1[['driver_code', 'grid_position', 'finish_position', 'points']].head(5).to_string(index=False))
    else:
        print(f"\n⚠ No race results available")
    
    if not qualifying.empty:
        print(f"\n🏆 QUALIFYING DATA ({qualifying['round'].nunique()} sessions):")
        print(f"   Rounds: {sorted(qualifying['round'].unique())}")
        suzuka = qualifying[qualifying['round'] == 3]
        if not suzuka.empty:
            print(f"   Suzuka Grid (12 drivers):")
            print(suzuka[['grid_position', 'driver_code', 'driver_name', 'constructor_name']].head(12).to_string(index=False))
    else:
        print(f"\n⚠ No qualifying data available")
    
    return standings, results, qualifying


if __name__ == "__main__":
    standings, results, qualifying = main()
