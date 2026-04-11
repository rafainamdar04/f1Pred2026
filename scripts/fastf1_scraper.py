"""
FastF1 Scraper for 2026 F1 Data
Uses the FastF1 Python library for real race data
"""

import fastf1
import pandas as pd
from pathlib import Path
import sys
import warnings
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.scrape_ergast_api import normalize_results, validate_schema
from config.settings import CURRENT_SEASON, HISTORICAL_YEARS, PATHS
warnings.filterwarnings('ignore')

# Enable caching for faster subsequent requests (use temp directory)
cache_dir = Path(tempfile.gettempdir()) / "fastf1_cache"
cache_dir.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(cache_dir))

def _session_has_happened(row, session_col, now_utc):
    session_date = row.get(session_col)
    if pd.isna(session_date):
        return False
    session_ts = pd.to_datetime(session_date, utc=True)
    return session_ts <= now_utc

class FastF1Scraper:
    """Fetch real F1 2026 data using FastF1 library"""
    
    def __init__(self, output_dir=PATHS["data"]):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def get_2026_season_schedule(self):
        """Get 2026 season schedule"""
        try:
            print("[SCHEDULE] Fetching 2026 season schedule...")
            # FastF1 loads schedule
            schedule = fastf1.get_event_schedule(CURRENT_SEASON)
            print(f"[OK] Found {len(schedule)} races in {CURRENT_SEASON}")
            return schedule
        except Exception as e:
            print(f"[ERROR] Error fetching schedule: {e}")
            return None
    
    def get_driver_standings(self, season=CURRENT_SEASON):
        """Get current driver standings for season"""
        try:
            print(f"[STANDINGS] Fetching driver standings for {season}...")
            # Use the last completed race to get standings
            schedule = fastf1.get_event_schedule(season)
            
            standings_list = []
            for idx, row in schedule.iterrows():
                if pd.notna(row['Session3DateUtc']):  # Race has happened
                    round_num = row['RoundNumber']
                    gp_name = row['EventName']
                else:
                    continue  # Skip future races
            
            print(f"[OK] Loaded standings data")
            return standings_list
        except Exception as e:
            print(f"[ERROR] Error fetching standings: {e}")
            return []
    
    def get_race_results(self, season=CURRENT_SEASON, round_num=1):
        """Get results for a specific race"""
        try:
            print(f"\n  [RACE] Fetching race results for Round {round_num}...")
            session = fastf1.get_session(season, round_num, 'R')
            session.load()

            column_map = {
                'DriverNumber': 'driver_number',
                'Abbreviation': 'driver_code',
                'FullName': 'driver_name',
                'DriverId': 'driver_id',
                'TeamName': 'constructor_name',
                'TeamId': 'constructor_id',
                'GridPosition': 'grid_position',
                'Position': 'finish_position',
                'Points': 'points',
            }
            available_cols = [col for col in column_map if col in session.results.columns]
            results = session.results[available_cols].copy()
            results.rename(columns={col: column_map[col] for col in available_cols}, inplace=True)
            for expected_col in column_map.values():
                if expected_col not in results.columns:
                    results[expected_col] = pd.NA
            
            results["season"] = season
            results["round"] = round_num
            results["race_name"] = session.event.get("EventName") if hasattr(session, "event") else None

            circuit_id = None
            circuit_name = None
            event = session.event if hasattr(session, "event") else None
            if isinstance(event, dict):
                circuit = event.get("Circuit", {})
                circuit_id = circuit.get("CircuitId") or circuit.get("circuitId")
                circuit_name = circuit.get("CircuitName") or circuit.get("circuitName")
            elif event is not None:
                circuit = event.get("Circuit") if hasattr(event, "get") else None
                if isinstance(circuit, dict):
                    circuit_id = circuit.get("CircuitId") or circuit.get("circuitId")
                    circuit_name = circuit.get("CircuitName") or circuit.get("circuitName")

            results["circuit_id"] = circuit_id
            results["circuit_name"] = circuit_name
            results["source"] = "fastf1"
            
            print(f"    [OK] Loaded {len(results)} results")
            return results
        except Exception as e:
            print(f"    [ERROR] Error: {e}")
            return None

    def fetch_historical_results(self, seasons):
        """Fetch historical race results for multiple seasons using FastF1."""
        all_results = []

        for season in seasons:
            try:
                schedule = fastf1.get_event_schedule(season)
            except Exception as e:
                print(f"[ERROR] Could not fetch schedule for {season}: {e}")
                continue

            print(f"[HIST] Fetching {season} results ({len(schedule)} races)")
            for _, row in schedule.iterrows():
                round_num = int(row["RoundNumber"])
                race_results = self.get_race_results(season, round_num)
                if race_results is not None and not race_results.empty:
                    race_date = None
                    if hasattr(row, "get"):
                        race_date = row.get("EventDate") or row.get("Session1Date")
                    race_results["race_date"] = race_date
                    all_results.append(race_results)

        if not all_results:
            return pd.DataFrame()

        results_df = pd.concat(all_results, ignore_index=True)
        results_df = normalize_results(results_df, source="fastf1")
        validate_schema(results_df)
        return results_df
    
    def get_qualifying_results(self, season=CURRENT_SEASON, round_num=1):
        """Get qualifying results for a specific race"""
        try:
            print(f"  [QUAL] Fetching qualifying for Round {round_num}...")
            session = fastf1.get_session(season, round_num, 'Q')
            session.load()

            column_map = {
                'DriverNumber': 'driver_number',
                'Abbreviation': 'driver_code',
                'FullName': 'driver_name',
                'DriverId': 'driver_id',
                'TeamName': 'constructor_name',
                'TeamId': 'constructor_id',
                'Position': 'qualifying_position',
                'GridPosition': 'grid_position',
                'Q1': 'q1_time',
                'Q2': 'q2_time',
                'Q3': 'q3_time',
            }
            available_cols = [col for col in column_map if col in session.results.columns]
            qualifying = session.results[available_cols].copy()
            qualifying.rename(columns={col: column_map[col] for col in available_cols}, inplace=True)
            for expected_col in column_map.values():
                if expected_col not in qualifying.columns:
                    qualifying[expected_col] = pd.NA

            if 'grid_position' in qualifying.columns and 'qualifying_position' in qualifying.columns:
                if qualifying['grid_position'].isna().all():
                    qualifying['grid_position'] = qualifying['qualifying_position']
            
            qualifying['season'] = season
            qualifying['round'] = round_num
            qualifying['race_name'] = session.event['EventName']
            
            print(f"    [OK] Loaded {len(qualifying)} qualifying results")
            return qualifying
        except Exception as e:
            print(f"    [ERROR] Error: {e}")
            return None
    
    def fetch_2026_season(self):
        """Fetch complete 2026 season data"""
        print("=" * 70)
        print("FASTF1 SCRAPER - F1 2026 REAL DATA")
        print("=" * 70)
        print("[INFO] Using FastF1 to fetch official F1 2026 season data")
        
        season = CURRENT_SEASON
        
        # Get schedule
        schedule = self.get_2026_season_schedule()
        if schedule is None or len(schedule) == 0:
            print("[ERROR] Could not fetch 2026 schedule")
            return None, None, None
        
        all_results = []
        all_qualifying = []
        
        print(f"\n[DATA] FETCHING RACE DATA ({len(schedule)} races)")
        print("-" * 70)
        
        now_utc = pd.Timestamp.now(tz="UTC")

        # Fetch data for each race
        for idx, row in schedule.iterrows():
            round_num = int(row['RoundNumber'])
            gp_name = row['EventName']

            # Check if sessions have happened
            has_race = _session_has_happened(row, 'Session5DateUtc', now_utc)
            has_qualifying = _session_has_happened(row, 'Session4DateUtc', now_utc)

            race_date = row['Session1Date'] if pd.notna(row['Session1Date']) else 'TBD'
            
            print(f"\nRound {round_num}: {gp_name} ({race_date})")
            
            if has_race:
                # Get race results
                race_results = self.get_race_results(season, round_num)
                if race_results is not None:
                    all_results.append(race_results)

            # Get qualifying (only if session has happened)
            if has_qualifying:
                qual_results = self.get_qualifying_results(season, round_num)
                if qual_results is not None:
                    all_qualifying.append(qual_results)
        
        # Combine data
        results_df = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        qualifying_df = pd.concat(all_qualifying, ignore_index=True) if all_qualifying else pd.DataFrame()
        
        # Save files
        print("\n" + "=" * 70)
        print("SAVING DATA")
        print("=" * 70)
        
        if not results_df.empty:
            results_df.to_csv(self.output_dir / f"{CURRENT_SEASON}_race_results.csv", index=False)
            print(f"\n[OK] Saved race results: {len(results_df)} entries from {results_df['round'].nunique()} races")
        else:
            print(f"\n[WARN] No race results available")
        
        if not qualifying_df.empty:
            qualifying_df.to_csv(self.output_dir / f"{CURRENT_SEASON}_qualifying.csv", index=False)
            print(f"[OK] Saved qualifying data: {len(qualifying_df)} entries from {qualifying_df['round'].nunique()} sessions")
        else:
            print(f"[WARN] No qualifying data available")
        
        # Get standings from last race
        standings = None
        if not results_df.empty:
            latest_round = results_df['round'].max()

            # Aggregate points across all races
            standings = results_df.groupby(
                ['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']
            ).agg({
                'points': 'sum',
                'driver_number': 'first',
                'finish_position': 'min',
            }).reset_index()

            wins = results_df[results_df['finish_position'] == 1].groupby(
                ['driver_id']
            ).size().rename('wins')

            podiums = results_df[results_df['finish_position'] <= 3].groupby(
                ['driver_id']
            ).size().rename('podiums')

            standings = standings.merge(wins, on='driver_id', how='left')
            standings = standings.merge(podiums, on='driver_id', how='left')
            standings['wins'] = standings['wins'].fillna(0).astype(int)
            standings['podiums'] = standings['podiums'].fillna(0).astype(int)

            standings = standings.sort_values('points', ascending=False).reset_index(drop=True)
            standings['position'] = range(1, len(standings) + 1)
            standings = standings.drop(columns=['finish_position'])

            standings.to_csv(self.output_dir / f"{CURRENT_SEASON}_standings.csv", index=False)
            print(f"[OK] Saved standings: {len(standings)} drivers (updated after Round {int(latest_round)})")
        else:
            print(f"[WARN] Could not create standings (no race results)")
        
        return standings, results_df, qualifying_df


def main():
    scraper = FastF1Scraper(output_dir=PATHS["data"])
    standings, results, qualifying = scraper.fetch_2026_season()
    
    print("\n" + "=" * 70)
    print("2026 SEASON DATA SUMMARY")
    print("=" * 70)
    
    if standings is not None and not standings.empty:
        print(f"\n📊 DRIVER STANDINGS ({len(standings)} drivers):")
        print(standings[['position', 'driver_code', 'driver_name', 'constructor_name', 'points']].head(12).to_string(index=False))
    
    if results is not None and not results.empty:
        print(f"\n🏁 RACE RESULTS ({results['round'].nunique()} races completed):")
        print(f"   Rounds: {sorted(results['round'].unique())}")
        if 1 in results['round'].values:
            race_1 = results[results['round'] == 1].sort_values('finish_position')
            print(f"   Race 1 Sample (top 5):")
            print(race_1[['driver_code', 'grid_position', 'finish_position', 'points']].head(5).to_string(index=False))
    
    if qualifying is not None and not qualifying.empty:
        print(f"\n🏆 QUALIFYING DATA ({qualifying['round'].nunique()} sessions):")
        print(f"   Rounds: {sorted(qualifying['round'].unique())}")
        if 3 in qualifying['round'].values:
            suzuka = qualifying[qualifying['round'] == 3].sort_values('grid_position')
            print(f"   Suzuka Grid (Round 3, top 12):")
            print(suzuka[['grid_position', 'driver_code', 'driver_name', 'constructor_name']].head(12).to_string(index=False))
    
    return standings, results, qualifying


if __name__ == "__main__":
    standings, results, qualifying = main()
