"""
Jolpica API Scraper for F1 2026 Data
Real-time F1 data for current season
"""

import requests
import pandas as pd
import json
from datetime import datetime
from pathlib import Path

from config.settings import CURRENT_SEASON, PATHS

class JolpicaScraper:
    """Fetch real F1 2026 data from Jolpica API"""
    
    # Jolpica API endpoints
    BASE_URL = "https://api.jolpi.ca/ergast"
    
    def __init__(self, output_dir=PATHS["data"]):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        
    def get_current_season(self):
        """Get current season (2026)"""
        try:
            url = f"{self.BASE_URL}/currentSeason"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            season = data.get('season', CURRENT_SEASON)
            print(f"✓ Current season: {season}")
            return season
        except Exception as e:
            print(f"✗ Error: {e}, using {CURRENT_SEASON}")
            return CURRENT_SEASON
    
    def get_driver_standings(self, season=CURRENT_SEASON):
        """Fetch driver standings for season"""
        try:
            url = f"{self.BASE_URL}/{season}/driverStandings"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            standings_list = data.get('StandingsLists', [])
            if standings_list:
                standings = standings_list[0].get('DriverStandings', [])
                print(f"✓ Fetched {len(standings)} driver standings for {season}")
                return standings
            return []
        except Exception as e:
            print(f"✗ Error fetching driver standings: {e}")
            return []
    
    def get_races(self, season=CURRENT_SEASON):
        """Fetch all races for season"""
        try:
            url = f"{self.BASE_URL}/{season}/races"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            races = data.get('Races', [])
            print(f"✓ Fetched {len(races)} races for {season}")
            return races
        except Exception as e:
            print(f"✗ Error fetching races: {e}")
            return []
    
    def get_race_results(self, season=CURRENT_SEASON, round_num=1):
        """Fetch results for specific race"""
        try:
            url = f"{self.BASE_URL}/{season}/{round_num}/results"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            races = data.get('Races', [])
            if races:
                results = races[0].get('Results', [])
                print(f"✓ Fetched results for {season} R{round_num} ({len(results)} finishers)")
                return results
            return []
        except Exception as e:
            print(f"✗ Error fetching race results for R{round_num}: {e}")
            return []
    
    def get_qualifying(self, season=CURRENT_SEASON, round_num=1):
        """Fetch qualifying results for specific race"""
        try:
            url = f"{self.BASE_URL}/{season}/{round_num}/qualifying"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            races = data.get('Races', [])
            if races:
                qualifying = races[0].get('QualifyingResults', [])
                print(f"✓ Fetched qualifying for {season} R{round_num}")
                return qualifying
            return []
        except Exception as e:
            print(f"✗ Error fetching qualifying for R{round_num}: {e}")
            return []
    
    def parse_driver_standings(self, standings_data):
        """Parse standings into DataFrame"""
        rows = []
        for standing in standings_data:
            driver = standing.get('Driver', {})
            constructor = standing.get('Constructor', {})
            
            row = {
                'position': standing.get('position'),
                'driver_id': driver.get('driverId'),
                'driver_code': driver.get('code'),
                'driver_name': f"{driver.get('givenName', '')} {driver.get('familyName', '')}",
                'constructor_id': constructor.get('constructorId'),
                'constructor_name': constructor.get('name'),
                'points': standing.get('points'),
                'wins': standing.get('wins'),
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def parse_race_results(self, season, round_num, race_name, circuit_id, results_data):
        """Parse race results into DataFrame"""
        rows = []
        for result in results_data:
            driver = result.get('Driver', {})
            constructor = result.get('Constructor', {})
            
            row = {
                'season': season,
                'round': round_num,
                'race_name': race_name,
                'circuit_id': circuit_id,
                'driver_id': driver.get('driverId'),
                'driver_code': driver.get('code'),
                'driver_name': f"{driver.get('givenName', '')} {driver.get('familyName', '')}",
                'constructor_id': constructor.get('constructorId'),
                'constructor_name': constructor.get('name'),
                'grid_position': result.get('grid'),
                'finish_position': result.get('position'),
                'points': result.get('points'),
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def parse_qualifying(self, season, round_num, race_name, circuit_id, qualifying_data):
        """Parse qualifying results into DataFrame"""
        rows = []
        for qual in qualifying_data:
            driver = qual.get('Driver', {})
            constructor = qual.get('Constructor', {})
            
            # Get best qualifying time
            best_time = qual.get('Q3') or qual.get('Q2') or qual.get('Q1')
            
            row = {
                'season': season,
                'round': round_num,
                'race_name': race_name,
                'circuit_id': circuit_id,
                'grid_position': qual.get('position'),
                'driver_id': driver.get('driverId'),
                'driver_code': driver.get('code'),
                'driver_name': f"{driver.get('givenName', '')} {driver.get('familyName', '')}",
                'constructor_id': constructor.get('constructorId'),
                'constructor_name': constructor.get('name'),
                'q1_time': qual.get('Q1'),
                'q2_time': qual.get('Q2'),
                'q3_time': qual.get('Q3'),
                'best_qualifying_time': best_time,
            }
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def fetch_2026_season(self):
        """Fetch complete 2026 season data"""
        season = CURRENT_SEASON
        print(f"\n📊 Fetching {season} season data...")
        
        # Get standings
        standings_data = self.get_driver_standings(season)
        standings_df = self.parse_driver_standings(standings_data) if standings_data else pd.DataFrame()
        
        if not standings_df.empty:
            standings_df.to_csv(self.output_dir / f"{CURRENT_SEASON}_standings.csv", index=False)
            print(f"✓ Saved standings to {CURRENT_SEASON}_standings.csv")
        
        # Get all races for season
        races = self.get_races(season)
        
        all_results = []
        all_qualifying = []
        
        for race in races:
            round_num = int(race.get('round', 0))
            race_name = race.get('name', f'Race {round_num}')
            circuit = race.get('Circuit', {})
            circuit_id = circuit.get('circuitId', 'unknown')
            race_date = race.get('date', '')
            
            print(f"\n  Round {round_num}: {race_name} ({race_date})")
            
            # Get race results (if race happened)
            results = self.get_race_results(season, round_num)
            if results:
                results_df = self.parse_race_results(season, round_num, race_name, circuit_id, results)
                all_results.append(results_df)
            
            # Get qualifying results (if race happened)
            qualifying = self.get_qualifying(season, round_num)
            if qualifying:
                qual_df = self.parse_qualifying(season, round_num, race_name, circuit_id, qualifying)
                all_qualifying.append(qual_df)
        
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
    print("JOLPICA API SCRAPER - F1 2026 REAL DATA")
    print("=" * 70)
    
    scraper = JolpicaScraper(output_dir=PATHS["data"])
    standings, results, qualifying = scraper.fetch_2026_season()
    
    print("\n" + "=" * 70)
    print("2026 SEASON DATA SUMMARY")
    print("=" * 70)
    
    if not standings.empty:
        print(f"\n📊 Driver Standings ({len(standings)} drivers):")
        print(standings[['position', 'driver_code', 'driver_name', 'constructor_name', 'points', 'wins']].to_string(index=False))
    
    if not results.empty:
        print(f"\n🏁 Race Results ({results['round'].nunique()} races completed):")
        print(f"   Rounds: {sorted(results['round'].unique())}")
        print(f"   Sample race results (Round 1):")
        race_1 = results[results['round'] == 1][['driver_code', 'grid_position', 'finish_position', 'points']].head(5)
        print(race_1.to_string(index=False))
    
    if not qualifying.empty:
        print(f"\n🏆 Qualifying Data ({qualifying['round'].nunique()} sessions):")
        print(f"   Rounds with qualifying: {sorted(qualifying['round'].unique())}")
    
    return standings, results, qualifying


if __name__ == "__main__":
    standings, results, qualifying = main()
