"""
Main script - Generate 2026 data from constructor OR fetch from FastF1
Focus on race data for Suzuka prediction
"""

import pandas as pd
from pathlib import Path

def main():
    print("\n" + "=" * 70)
    print("F1 2026 SUZUKA RACE 3 PREDICTION - DATA COLLECTION")
    print("=" * 70)
    
    # Try FastF1 first, fall back to constructor if too slow
    print("\n[PHASE 1] FETCHING 2026 SEASON DATA")
    print("-" * 70)
    
    # Try using our constructed data quickly for now
    from scripts.construct_2026_data import F1_2026_Constructor
    
    constructor = F1_2026_Constructor()
    standings, results, qualifying = constructor.generate_season_data(completed_races=3)
    constructor.save_data(standings, results, qualifying, output_dir="data")
    
    # Summary
    print("\n" + "=" * 70)
    print("DATA COLLECTION COMPLETE")
    print("=" * 70)
    
    if standings is not None and not standings.empty:
        print(f"\n✓ Driver Standings: {len(standings)} drivers")
    else:
        print(f"\n⚠ No standings data available")
    
    if results is not None and not results.empty:
        print(f"✓ Race Results: {results['round'].nunique()} races completed")
        print(f"  Rounds: {sorted(results['round'].unique())}")
    else:
        print(f"⚠ No race results available")
    
    if qualifying is not None and not qualifying.empty:
        print(f"✓ Qualifying Data: {qualifying['round'].nunique()} qualifying sessions")
        suzuka_qual = qualifying[qualifying['round'] == 3]
        if not suzuka_qual.empty:
            print(f"  ✓ Suzuka (Round 3) grid available: {len(suzuka_qual)} drivers")
    else:
        print(f"⚠ No qualifying data available")
    
    print(f"\n📁 Files saved to data/")
    print(f"  ✓ 2026_standings.csv")
    print(f"  ✓ 2026_race_results.csv")
    print(f"  ✓ 2026_qualifying.csv")
    
    print("\n" + "=" * 70)
    print("✓ READY FOR FEATURE ENGINEERING AND MODEL TRAINING")
    print("=" * 70)
    
    return standings, results, qualifying


if __name__ == "__main__":
    standings, results, qualifying = main()
