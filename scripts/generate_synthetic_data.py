"""
Synthetic Historical F1 Data Generator (2023-2025)
Generates realistic historical data when API is unavailable
Based on actual F1 racing patterns and driver performance trends
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config.settings import HISTORICAL_YEARS, PATHS
np.random.seed(42)

class SyntheticF1DataGenerator:
    """Generate realistic F1 race data for 2023-2025"""
    
    def __init__(self):
        # Core drivers in F1
        self.drivers = [
            'verstappen', 'norris', 'leclerc', 'sainz', 'hamilton', 'russell',
            'alonso', 'stroll', 'piastri', 'perez', 'tsunoda', 'bottas',
            'ocon', 'magnussen', 'ricciardo', 'colapinto', 'gasly', 'hulkenberg',
            'sargent', 'zhou'
        ]
        
        self.driver_codes = {
            'verstappen': 'VER', 'norris': 'NOR', 'leclerc': 'LEC', 'sainz': 'SAI',
            'hamilton': 'HAM', 'russell': 'RUS', 'alonso': 'ALO', 'stroll': 'STR',
            'piastri': 'PIA', 'perez': 'PER', 'tsunoda': 'TSU', 'bottas': 'BOT',
            'ocon': 'OCO', 'magnussen': 'MAG', 'ricciardo': 'RIC', 'colapinto': 'COL',
            'gasly': 'GAS', 'hulkenberg': 'HUL', 'sargent': 'SAR', 'zhou': 'ZHO'
        }
        
        self.constructors = {
            'verstappen': ('red_bull', 'Red Bull Racing'), 'perez': ('red_bull', 'Red Bull Racing'),
            'norris': ('mclaren', 'McLaren'), 'piastri': ('mclaren', 'McLaren'),
            'leclerc': ('ferrari', 'Ferrari'), 'sainz': ('ferrari', 'Ferrari'),
            'hamilton': ('mercedes', 'Mercedes'), 'russell': ('mercedes', 'Mercedes'),
            'alonso': ('aston_martin', 'Aston Martin'), 'stroll': ('aston_martin', 'Aston Martin'),
            'gasly': ('alpine', 'Alpine'), 'ocon': ('alpine', 'Alpine'),
            'tsunoda': ('racing_bulls', 'Racing Bulls'), 'ricciardo': ('racing_bulls', 'Racing Bulls'),
            'bottas': ('alfa_romeo', 'Alfa Romeo'), 'zhou': ('alfa_romeo', 'Alfa Romeo'),
            'magnussen': ('haas', 'Haas'), 'hulkenberg': ('haas', 'Haas'),
            'colapinto': ('williams', 'Williams'), 'sargent': ('williams', 'Williams'),
        }
        
        # Circuits for 2023-2025 seasons (realistic F1 calendar)
        self.circuits = [
            ('bahrain', 'Bahrain Grand Prix'),
            ('saudi_arabia', 'Saudi Arabian Grand Prix'),
            ('australia', 'Australian Grand Prix'),
            ('japan', 'Japanese Grand Prix'),  # Suzuka
            ('china', 'Chinese Grand Prix'),
            ('miami', 'Miami Grand Prix'),
            ('monaco', 'Monaco Grand Prix'),
            ('canada', 'Canadian Grand Prix'),
            ('spain', 'Spanish Grand Prix'),
            ('austria', 'Austrian Grand Prix'),
            ('uk', 'British Grand Prix'),
            ('hungary', 'Hungarian Grand Prix'),
            ('belgium', 'Belgian Grand Prix'),
            ('netherlands', 'Dutch Grand Prix'),
            ('italy', 'Italian Grand Prix'),
            ('singapore', 'Singapore Grand Prix'),
            ('mexico', 'Mexican Grand Prix'),
            ('usa', 'United States Grand Prix'),
            ('brazil', 'Brazilian Grand Prix'),
            ('uae', 'Abu Dhabi Grand Prix'),
        ]
        
        # Driver strength (for realistic race order)
        self.driver_strength = {
            'verstappen': 1.0, 'norris': 0.92, 'leclerc': 0.88, 'sainz': 0.85,
            'hamilton': 0.87, 'russell': 0.82, 'alonso': 0.80, 'piastri': 0.81,
            'stroll': 0.70, 'perez': 0.78, 'tsunoda': 0.72, 'bottas': 0.68,
            'ocon': 0.70, 'magnussen': 0.65, 'ricciardo': 0.68, 'colapinto': 0.62,
            'gasly': 0.70, 'hulkenberg': 0.68, 'sargent': 0.60, 'zhou': 0.64
        }
    
    def generate_race_positions(self, season, round_num, circuit_id):
        """Generate realistic race positions based on driver strength"""
        
        # Shuffle drivers and apply performance multiplier
        positions_data = []
        drivers_shuffled = np.random.permutation(self.drivers)
        
        # Apply skill-based ranking
        strength_scores = [(d, self.driver_strength[d] + np.random.normal(0, 0.05)) for d in drivers_shuffled]
        strength_scores.sort(key=lambda x: x[1], reverse=True)
        
        for finish_pos, (driver_id, _) in enumerate(strength_scores, 1):
            points = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1] + [0] * 10
            driver_points = points[finish_pos - 1] if finish_pos <= len(points) else 0
            
            # Grid position correlated with finish
            grid_pos = max(1, finish_pos + np.random.randint(-3, 5))
            
            const_id, const_name = self.constructors.get(driver_id, ('unknown', 'Unknown'))
            
            positions_data.append({
                'season': season,
                'round': round_num,
                'circuit_id': circuit_id,
                'circuit_name': next((name for cid, name in self.circuits if cid == circuit_id), 'Unknown'),
                'driver_id': driver_id,
                'driver_code': self.driver_codes.get(driver_id, 'N/A'),
                'constructor_id': const_id,
                'constructor_name': const_name,
                'grid_position': grid_pos,
                'finish_position': finish_pos,
                'points': driver_points,
                'race_date': (datetime(season, 1, 1) + timedelta(days=round_num * 15)).strftime('%Y-%m-%d'),
            })
        
        return positions_data
    
    def generate_seasons(self, years=None):
        """Generate complete race data for multiple seasons"""
        if years is None:
            years = HISTORICAL_YEARS
        all_races = []
        
        for year in years:
            print(f"  Generating {year} season ({len(self.circuits)} races)...", end=" ")
            for round_num, (circuit_id, circuit_name) in enumerate(self.circuits, 1):
                race_positions = self.generate_race_positions(year, round_num, circuit_id)
                all_races.extend(race_positions)
            print(f"✓ ({round_num} races)")
        
        df = pd.DataFrame(all_races)
        return df


def main():
    print("=" * 70)
    print(
        "GENERATING SYNTHETIC F1 HISTORICAL DATA "
        f"({min(HISTORICAL_YEARS)}-{max(HISTORICAL_YEARS)})"
    )
    print("=" * 70)
    print("(Using synthetic data due to API unavailability)\n")
    
    generator = SyntheticF1DataGenerator()
    df = generator.generate_seasons(years=HISTORICAL_YEARS)
    
    # Save data
    df.to_csv(f"{PATHS['data']}historical_races.csv", index=False)
    
    print("\n" + "=" * 70)
    print("SYNTHETIC DATA SUMMARY")
    print("=" * 70)
    print(f"Total records: {len(df)}")
    print(f"Seasons: {sorted(df['season'].unique())}")
    print(f"Races per season: {len(df) // 3 // len(generator.circuits)} races ({len(generator.circuits)} circuits)")
    print(f"Total drivers: {df['driver_id'].nunique()}")
    print(f"Total constructors: {df['constructor_id'].nunique()}")
    print(f"\nColumns: {list(df.columns)}\n")
    
    print("Sample data (first 10 records):")
    print(df[['season', 'round', 'circuit_name', 'driver_code', 'constructor_name', 
              'grid_position', 'finish_position', 'points']].head(10).to_string(index=False))
    
    print(f"\n✓ Saved to {PATHS['data']}historical_races.csv")


if __name__ == "__main__":
    main()
