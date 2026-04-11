"""
2026 F1 Season Data Constructor - Real Lineup
Creates realistic 2026 season data based on actual driver lineups
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config.settings import CURRENT_SEASON, PATHS

class F1_2026_Constructor:
    """
    Construct 2026 F1 season data based on actual driver lineups
    """
    
    def __init__(self):
        # 2026 Driver Lineup (Confirmed)
        self.teams_drivers = {
            'red_bull': {
                'name': 'Red Bull Racing',
                'drivers': [
                    {'id': 'verstappen', 'code': 'VER', 'name': 'Max Verstappen'},
                    {'id': 'hadjar', 'code': 'HAD', 'name': 'Isack Hadjar'},
                ]
            },
            'ferrari': {
                'name': 'Ferrari',
                'drivers': [
                    {'id': 'leclerc', 'code': 'LEC', 'name': 'Charles Leclerc'},
                    {'id': 'hamilton', 'code': 'HAM', 'name': 'Lewis Hamilton'},
                ]
            },
            'mercedes': {
                'name': 'Mercedes',
                'drivers': [
                    {'id': 'antonelli', 'code': 'ANT', 'name': 'Kimi Antonelli'},
                    {'id': 'russell', 'code': 'RUS', 'name': 'George Russell'},
                ]
            },
            'haas': {
                'name': 'Haas',
                'drivers': [
                    {'id': 'ocon', 'code': 'OCO', 'name': 'Esteban Ocon'},
                    {'id': 'bearman', 'code': 'BEA', 'name': 'Oliver Bearman'},
                ]
            },
            'audi': {
                'name': 'Audi',
                'drivers': [
                    {'id': 'hulkenberg', 'code': 'HUL', 'name': 'Nico Hulkenberg'},
                    {'id': 'bortoletto', 'code': 'BOR', 'name': 'Gabriel Bortoletto'},
                ]
            },
            'williams': {
                'name': 'Williams',
                'drivers': [
                    {'id': 'sainz', 'code': 'SAI', 'name': 'Carlos Sainz'},
                    {'id': 'albon', 'code': 'ALB', 'name': 'Alex Albon'},
                ]
            },
            'cadillac': {
                'name': 'Cadillac',
                'drivers': [
                    {'id': 'bottas', 'code': 'BOT', 'name': 'Valtteri Bottas'},
                    {'id': 'perez', 'code': 'PER', 'name': 'Sergio Perez'},
                ]
            },
            'mclaren': {
                'name': 'McLaren',
                'drivers': [
                    {'id': 'piastri', 'code': 'PIA', 'name': 'Oscar Piastri'},
                    {'id': 'norris', 'code': 'NOR', 'name': 'Lando Norris'},
                ]
            },
            'aston_martin': {
                'name': 'Aston Martin',
                'drivers': [
                    {'id': 'stroll', 'code': 'STR', 'name': 'Lance Stroll'},
                    {'id': 'alonso', 'code': 'ALO', 'name': 'Fernando Alonso'},
                ]
            },
            'alpine': {
                'name': 'Alpine',
                'drivers': [
                    {'id': 'gasly', 'code': 'GAS', 'name': 'Pierre Gasly'},
                    {'id': 'colapinto', 'code': 'COL', 'name': 'Franco Colapinto'},
                ]
            },
            'vcarb': {
                'name': 'Visa Cash App RB',
                'drivers': [
                    {'id': 'lawson', 'code': 'LAW', 'name': 'Liam Lawson'},
                    {'id': 'lindblad', 'code': 'LIN', 'name': 'Arvid Lindblad'},
                ]
            },
        }
        
        # Driver performance ratings (out of 1.0)
        self.driver_strength = {
            'verstappen': 1.00, 'leclerc': 0.92, 'hamilton': 0.90, 'norris': 0.88,
            'piastri': 0.86, 'russell': 0.85, 'sainz': 0.84, 'albon': 0.80,
            'alonso': 0.82, 'ocon': 0.76, 'gasly': 0.74, 'antonelli': 0.78,
            'stroll': 0.72, 'hulkenberg': 0.79, 'hadjar': 0.72, 'bearman': 0.68,
            'bortoletto': 0.70, 'bottas': 0.75, 'perez': 0.73, 'lawson': 0.71,
            'colapinto': 0.69, 'lindblad': 0.65,
        }
        
        # 2026 Circuit schedule (22 races)
        self.circuits = [
            {'round': 1, 'name': 'Australian Grand Prix', 'id': 'australia', 'date': '2026-03-08'},
            {'round': 2, 'name': 'Chinese Grand Prix', 'id': 'china', 'date': '2026-03-22'},
            {'round': 3, 'name': 'Japanese Grand Prix', 'id': 'japan', 'date': '2026-04-05'},  # Suzuka
            {'round': 4, 'name': 'Bahrain Grand Prix', 'id': 'bahrain', 'date': '2026-04-19'},
            {'round': 5, 'name': 'Saudi Arabian Grand Prix', 'id': 'saudi_arabia', 'date': '2026-05-03'},
            {'round': 6, 'name': 'Miami Grand Prix', 'id': 'miami', 'date': '2026-05-10'},
            {'round': 7, 'name': 'Monaco Grand Prix', 'id': 'monaco', 'date': '2026-05-24'},
            {'round': 8, 'name': 'Canadian Grand Prix', 'id': 'canada', 'date': '2026-06-14'},
            {'round': 9, 'name': 'Spanish Grand Prix', 'id': 'spain', 'date': '2026-06-28'},
            {'round': 10, 'name': 'Austrian Grand Prix', 'id': 'austria', 'date': '2026-07-12'},
            {'round': 11, 'name': 'British Grand Prix', 'id': 'uk', 'date': '2026-07-26'},
            {'round': 12, 'name': 'Hungarian Grand Prix', 'id': 'hungary', 'date': '2026-08-02'},
            {'round': 13, 'name': 'Belgian Grand Prix', 'id': 'belgium', 'date': '2026-08-30'},
            {'round': 14, 'name': 'Dutch Grand Prix', 'id': 'netherlands', 'date': '2026-09-06'},
            {'round': 15, 'name': 'Italian Grand Prix', 'id': 'italy', 'date': '2026-09-20'},
            {'round': 16, 'name': 'Singapore Grand Prix', 'id': 'singapore', 'date': '2026-10-04'},
            {'round': 17, 'name': 'Japanese Grand Prix (Alternate)', 'id': 'japan_2', 'date': '2026-10-11'},
            {'round': 18, 'name': 'Mexico City Grand Prix', 'id': 'mexico', 'date': '2026-10-25'},
            {'round': 19, 'name': 'United States Grand Prix', 'id': 'usa', 'date': '2026-11-01'},
            {'round': 20, 'name': 'São Paulo Grand Prix', 'id': 'brazil', 'date': '2026-11-15'},
            {'round': 21, 'name': 'Las Vegas Grand Prix', 'id': 'vegas', 'date': '2026-11-22'},
            {'round': 22, 'name': 'Abu Dhabi Grand Prix', 'id': 'uae', 'date': '2026-12-06'},
        ]
        
    def get_all_drivers(self):
        """Get list of all drivers with team info"""
        all_drivers = []
        for team_id, team_info in self.teams_drivers.items():
            for driver in team_info['drivers']:
                all_drivers.append({
                    'driver_id': driver['id'],
                    'driver_code': driver['code'],
                    'driver_name': driver['name'],
                    'constructor_id': team_id,
                    'constructor_name': team_info['name'],
                })
        return pd.DataFrame(all_drivers)
    
    def generate_race_results(self, round_num, race_name, circuit_id):
        """Generate realistic race results based on driver strength"""
        
        all_drivers = self.get_all_drivers()
        drivers_list = all_drivers.to_dict('records')
        
        # Score each driver for this race
        np.random.seed(round_num)  # Deterministic but different per race
        
        scored_drivers = []
        for driver in drivers_list:
            # Base strength + random variability
            base_strength = self.driver_strength.get(driver['driver_id'], 0.5)
            race_form = base_strength + np.random.normal(0, 0.08)
            race_form = max(0.3, min(1.0, race_form))  # Clamp to 0.3-1.0
            
            scored_drivers.append({
                **driver,
                'race_score': race_form,
            })
        
        # Sort by race score (best to worst)
        scored_drivers.sort(key=lambda x: x['race_score'], reverse=True)
        
        # Assign points (F1 2026 system: 25-18-15-12-10-8-6-4-2-1)
        points_table = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1] + [0] * 12
        
        results = []
        for position, driver in enumerate(scored_drivers, 1):
            # Grid position correlated with finish but with some overtaking
            grid_pos = max(1, position + np.random.randint(-5, 6))
            
            results.append({
                'season': CURRENT_SEASON,
                'round': round_num,
                'race_name': race_name,
                'circuit_id': circuit_id,
                'driver_id': driver['driver_id'],
                'driver_code': driver['driver_code'],
                'driver_name': driver['driver_name'],
                'constructor_id': driver['constructor_id'],
                'constructor_name': driver['constructor_name'],
                'grid_position': grid_pos,
                'finish_position': position,
                'points': points_table[position - 1],
            })
        
        return results
    
    def generate_qualifying_results(self, round_num, race_name, circuit_id):
        """Generate qualifying grid positions"""
        
        all_drivers = self.get_all_drivers()
        drivers_list = all_drivers.to_dict('records')
        
        np.random.seed(round_num + 1000)  # Different seed for qualifying
        
        scored_drivers = []
        for driver in drivers_list:
            base_strength = self.driver_strength.get(driver['driver_id'], 0.5)
            qual_form = base_strength + np.random.normal(0, 0.06)
            qual_form = max(0.3, min(1.0, qual_form))
            
            scored_drivers.append({
                **driver,
                'qual_score': qual_form,
            })
        
        scored_drivers.sort(key=lambda x: x['qual_score'], reverse=True)
        
        results = []
        for position, driver in enumerate(scored_drivers, 1):
            # Time gap from pole (in seconds)
            time_gap = (position - 1) * np.random.uniform(0.2, 0.4) + np.random.uniform(-0.1, 0.1)
            
            results.append({
                'season': CURRENT_SEASON,
                'round': round_num,
                'race_name': race_name,
                'circuit_id': circuit_id,
                'grid_position': position,
                'driver_id': driver['driver_id'],
                'driver_code': driver['driver_code'],
                'driver_name': driver['driver_name'],
                'constructor_id': driver['constructor_id'],
                'constructor_name': driver['constructor_name'],
                'qualifying_time_gap': time_gap,
            })
        
        return results
    
    def generate_season_data(self, completed_races=2):
        """
        Generate 2026 season data
        completed_races: number of races that have been completed (default 2 for March 29)
        """
        
        all_standings = []
        all_results = []
        all_qualifying = []
        
        print(f"Generating {CURRENT_SEASON} season data ({completed_races} races completed)...\n")
        
        # Generate data for completed and upcoming races
        for circuit in self.circuits[:completed_races + 1]:  # Include upcoming Suzuka for prediction
            round_num = circuit['round']
            race_name = circuit['name']
            circuit_id = circuit['id']
            
            if round_num <= completed_races:
                # Generate results for completed races
                results = self.generate_race_results(round_num, race_name, circuit_id)
                all_results.extend(results)
                print(f"  ✓ Generated race results for Round {round_num}: {race_name}")
            
            # Generate qualifying for all races (completed and upcoming)
            qualifying = self.generate_qualifying_results(round_num, race_name, circuit_id)
            all_qualifying.extend(qualifying)
            
            if round_num <= completed_races:
                print(f"    ✓ Generated qualifying for Round {round_num}")
            else:
                print(f"  ✓ Generated qualifying grid for upcoming Round {round_num}: {race_name}")
        
        # Calculate current driver standings (after completed races)
        results_df = pd.DataFrame(all_results)
        standings = results_df.groupby(['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']).agg({
            'points': 'sum',
        }).reset_index()
        standings.columns = ['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name', 'points']
        standings = standings.sort_values('points', ascending=False).reset_index(drop=True)
        standings['position'] = range(1, len(standings) + 1)
        
        return standings, results_df, pd.DataFrame(all_qualifying)
    
    def save_data(self, standings, results, qualifying, output_dir=PATHS["data"]):
        """Save generated data to CSV"""
        standings.to_csv(f"{output_dir}/{CURRENT_SEASON}_standings.csv", index=False)
        print(f"\n✓ Saved standings: {len(standings)} drivers")
        
        results.to_csv(f"{output_dir}/{CURRENT_SEASON}_race_results.csv", index=False)
        print(f"✓ Saved race results: {len(results)} entries")
        
        qualifying.to_csv(f"{output_dir}/{CURRENT_SEASON}_qualifying.csv", index=False)
        print(f"✓ Saved qualifying: {len(qualifying)} entries")
        
        return standings, results, qualifying


def main():
    print("=" * 70)
    print("F1 2026 SEASON DATA CONSTRUCTOR")
    print("=" * 70)
    
    constructor = F1_2026_Constructor()
    
    # Generate data (2 races completed as of March 29, 2026)
    standings, results, qualifying = constructor.generate_season_data(completed_races=2)
    
    # Save files
    standings, results, qualifying = constructor.save_data(
        standings,
        results,
        qualifying,
        output_dir=PATHS["data"],
    )
    
    # Display summaries
    print("\n" + "=" * 70)
    print("CURRENT STANDINGS (After Race 2)")
    print("=" * 70)
    print(standings[['position', 'driver_code', 'driver_name', 'constructor_name', 'points']].head(12).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("SUZUKA (RACE 3) QUALIFYING GRID")
    print("=" * 70)
    suzuka_qual = qualifying[qualifying['round'] == 3].sort_values('grid_position')
    print(suzuka_qual[['grid_position', 'driver_code', 'driver_name', 'constructor_name', 'qualifying_time_gap']].head(12).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("SAMPLE: Race 1 Results")
    print("=" * 70)
    race_1 = results[results['round'] == 1].sort_values('finish_position')
    print(race_1[['finish_position', 'driver_code', 'driver_name', 'grid_position', 'points']].head(10).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("✓ DATA READY FOR FEATURE ENGINEERING")
    print("=" * 70)
    
    return standings, results, qualifying


if __name__ == "__main__":
    standings, results, qualifying = main()
