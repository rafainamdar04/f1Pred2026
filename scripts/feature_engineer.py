"""
Feature Engineering for F1 Suzuka Race 3 Prediction
Prepares data for XGBoost model
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from pathlib import Path

from config.settings import CURRENT_SEASON, FEATURE_CONSTANTS, PATHS

class SuzukaFeatureEngineer:
    """Engineer features for Suzuka prediction"""
    
    def __init__(self, data_dir=PATHS["data"]):
        self.data_dir = Path(data_dir)
        
    def load_data(self):
        """Load all 2026 data files"""
        standings = pd.read_csv(self.data_dir / f"{CURRENT_SEASON}_standings.csv")
        results = pd.read_csv(self.data_dir / f"{CURRENT_SEASON}_race_results.csv")
        qualifying = pd.read_csv(self.data_dir / f"{CURRENT_SEASON}_qualifying.csv")

        standings = self._ensure_id_columns(standings)
        results = self._ensure_id_columns(results)
        qualifying = self._ensure_id_columns(qualifying)

        return standings, results, qualifying

    def load_historical_results(self, filename="historical_races.csv"):
        results = pd.read_csv(self.data_dir / filename)
        results = self._ensure_id_columns(results)
        results = self._ensure_name_columns(results)
        results = self._coerce_round_season(results)
        return results

    def _ensure_id_columns(self, df):
        """Ensure driver_id and constructor_id exist for downstream joins."""
        if 'driver_id' not in df.columns and 'driver_code' in df.columns:
            df = df.copy()
            df['driver_id'] = df['driver_code']

        if 'constructor_id' not in df.columns:
            if 'constructor_name' in df.columns:
                df = df.copy()
                df['constructor_id'] = df['constructor_name']

        return df

    def _ensure_name_columns(self, df):
        if 'driver_name' not in df.columns:
            df = df.copy()
            df['driver_name'] = df['driver_id'] if 'driver_id' in df.columns else 'unknown'
        if 'driver_code' not in df.columns and 'driver_id' in df.columns:
            df = df.copy()
            df['driver_code'] = df['driver_id']
        if 'constructor_name' not in df.columns and 'constructor_id' in df.columns:
            df = df.copy()
            df['constructor_name'] = df['constructor_id']
        return df

    def _coerce_round_season(self, df):
        if 'round' in df.columns:
            df = df.copy()
            df['round'] = pd.to_numeric(df['round'], errors='coerce').astype('Int64')
        if 'season' in df.columns:
            df['season'] = pd.to_numeric(df['season'], errors='coerce').astype('Int64')
        return df

    def _compute_baselines(self, results):
        if results.empty:
            return {
                'median_finish': 999,
                'median_points': 0,
                'constructor_finish': {},
                'constructor_points': {},
            }

        median_finish = results['finish_position'].median()
        median_points = results['points'].median()
        constructor_finish = results.groupby('constructor_id')['finish_position'].mean().to_dict()
        constructor_points = results.groupby('constructor_id')['points'].mean().to_dict()
        return {
            'median_finish': median_finish,
            'median_points': median_points,
            'constructor_finish': constructor_finish,
            'constructor_points': constructor_points,
        }

    def _get_driver_pool(self, standings, results):
        """Build a driver list from standings or last completed race."""
        if not standings.empty:
            return standings[['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']].drop_duplicates()

        last_round = results['round'].max() if not results.empty else None
        if last_round is None:
            return pd.DataFrame(columns=['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name'])

        last_results = results[results['round'] == last_round]
        return last_results[['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']].drop_duplicates()

    def _build_standings_from_results(self, results):
        """Recreate standings from results to avoid future data leakage."""
        if results.empty:
            return pd.DataFrame(
                columns=[
                    'driver_id', 'driver_code', 'driver_name', 'constructor_id',
                    'constructor_name', 'points', 'wins', 'podiums', 'position'
                ]
            )

        results = self._ensure_id_columns(results)

        standings = results.groupby(
            ['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']
        ).agg({
            'points': 'sum',
            'finish_position': 'min',
        }).reset_index()

        wins = results[results['finish_position'] == 1].groupby('driver_id').size().rename('wins')
        podiums = results[results['finish_position'] <= 3].groupby('driver_id').size().rename('podiums')

        standings = standings.merge(wins, on='driver_id', how='left')
        standings = standings.merge(podiums, on='driver_id', how='left')
        standings['wins'] = standings['wins'].fillna(0).astype(int)
        standings['podiums'] = standings['podiums'].fillna(0).astype(int)
        standings = standings.sort_values('points', ascending=False).reset_index(drop=True)
        standings['position'] = range(1, len(standings) + 1)
        standings = standings.drop(columns=['finish_position'])

        return standings
    
    def engineer_features_for_race(self, race_round, standings, results, qualifying):
        """Create feature vector for drivers for a specific race"""
        
        # Get qualifying for this race
        race_qual = qualifying[qualifying['round'] == race_round].copy()
        
        # Get all drivers in grid
        all_drivers = race_qual[['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']].drop_duplicates()
        
        features_list = []
        
        for _, driver in all_drivers.iterrows():
            driver_id = driver['driver_id']
            
            # 1. CURRENT STANDINGS FEATURES
            driver_standing = standings[standings['driver_id'] == driver_id]
            current_points = driver_standing['points'].values[0] if len(driver_standing) > 0 else 0
            current_position = driver_standing['position'].values[0] if len(driver_standing) > 0 else 999
            wins = driver_standing['wins'].values[0] if len(driver_standing) > 0 and 'wins' in driver_standing.columns else 0
            
            # 2. QUALIFYING FEATURES FOR THIS RACE
            driver_qual = race_qual[race_qual['driver_id'] == driver_id]
            grid_position = driver_qual['grid_position'].values[0] if len(driver_qual) > 0 else 999
            qualifying_gap = (grid_position - 1) * FEATURE_CONSTANTS["grid_gap_estimate"]
            
            # 3. HISTORICAL RACE PERFORMANCE
            driver_races = results[results['driver_id'] == driver_id]
            if len(driver_races) > 0:
                avg_finish = driver_races['finish_position'].mean()
                avg_points = driver_races['points'].mean()
                races_completed = len(driver_races)
                podiums = len(driver_races[driver_races['finish_position'] <= 3])
                poles = 1 if driver_races['grid_position'].min() == 1 else 0
            else:
                avg_finish = 999
                avg_points = 0
                races_completed = 0
                podiums = 0
                poles = 0
            
            # 4. CONSTRUCTOR FEATURES
            constructor_id = driver['constructor_id']
            constructor_races = results[results['constructor_id'] == constructor_id]
            if len(constructor_races) > 0:
                constructor_avg_finish = constructor_races['finish_position'].mean()
                constructor_avg_points = constructor_races['points'].mean()
            else:
                constructor_avg_finish = 999
                constructor_avg_points = 0
            
            # 5. SUZUKA-SPECIFIC FEATURES (simulated based on current form)
            # At Suzuka, qualifying is very important
            suzuka_form = 1.0 / (grid_position + 0.5)  # Higher value = better grid position
            
            # 6. RECENT FORM (last race finish)
            last_race = driver_races[driver_races['round'] == driver_races['round'].max()] if len(driver_races) > 0 else pd.DataFrame()
            if len(last_race) > 0:
                last_finish = last_race['finish_position'].values[0]
                last_points = last_race['points'].values[0]
            else:
                last_finish = 999
                last_points = 0
            
            # 7. MOMENTUM (points trend)
            if races_completed >= 2:
                recent_races = driver_races.tail(1)
                early_races = driver_races.head(1)
                momentum = (
                    recent_races['points'].sum() - early_races['points'].sum()
                ) if len(recent_races) > 0 and len(early_races) > 0 else 0
            else:
                momentum = 0
            
            # Build feature vector
            feature_dict = {
                'driver_id': driver_id,
                'driver_code': driver['driver_code'],
                'driver_name': driver['driver_name'],
                'constructor_id': constructor_id,
                'constructor_name': driver['constructor_name'],
                'grid_position': grid_position,
                'current_points': current_points,
                'current_position': current_position,
                'wins': wins,
                'podiums': podiums,
                'poles': poles,
                'avg_finish_position': avg_finish,
                'avg_points_per_race': avg_points,
                'races_completed': races_completed,
                'last_race_finish': last_finish,
                'last_race_points': last_points,
                'momentum': momentum,
                'qualifying_gap': qualifying_gap,
                'suzuka_form': suzuka_form,
                'constructor_avg_finish': constructor_avg_finish,
                'constructor_avg_points': constructor_avg_points,
            }
            
            features_list.append(feature_dict)
        
        features_df = pd.DataFrame(features_list)
        return features_df

    def engineer_prequal_features_for_round(self, standings, results, rookie_penalty=1.5):
        """Create pre-qualifying feature vector for the next race."""
        standings = self._ensure_id_columns(standings)
        results = self._ensure_id_columns(results)
        results = self._ensure_name_columns(results)

        baselines = self._compute_baselines(results)

        all_drivers = self._get_driver_pool(standings, results)

        features_list = []

        for _, driver in all_drivers.iterrows():
            driver_id = driver['driver_id']

            driver_standing = standings[standings['driver_id'] == driver_id]
            current_points = driver_standing['points'].values[0] if len(driver_standing) > 0 else 0
            current_position = driver_standing['position'].values[0] if len(driver_standing) > 0 else 999
            wins = driver_standing['wins'].values[0] if len(driver_standing) > 0 and 'wins' in driver_standing.columns else 0

            driver_races = results[results['driver_id'] == driver_id]
            if len(driver_races) > 0:
                avg_finish = driver_races['finish_position'].mean()
                avg_points = driver_races['points'].mean()
                races_completed = len(driver_races)
                podiums = len(driver_races[driver_races['finish_position'] <= 3])
                poles = 1 if driver_races['grid_position'].min() == 1 else 0
            else:
                avg_finish = baselines['median_finish'] + rookie_penalty
                avg_points = baselines['median_points']
                races_completed = 0
                podiums = 0
                poles = 0

            constructor_id = driver['constructor_id']
            constructor_races = results[results['constructor_id'] == constructor_id]
            if len(constructor_races) > 0:
                constructor_avg_finish = constructor_races['finish_position'].mean()
                constructor_avg_points = constructor_races['points'].mean()
            else:
                constructor_avg_finish = baselines['constructor_finish'].get(constructor_id, baselines['median_finish'])
                constructor_avg_points = baselines['constructor_points'].get(constructor_id, baselines['median_points'])

            last_race = driver_races[driver_races['round'] == driver_races['round'].max()] if len(driver_races) > 0 else pd.DataFrame()
            if len(last_race) > 0:
                last_finish = last_race['finish_position'].values[0]
                last_points = last_race['points'].values[0]
            else:
                last_finish = baselines['median_finish'] + rookie_penalty
                last_points = 0

            if races_completed >= 2:
                recent_races = driver_races.tail(1)
                early_races = driver_races.head(1)
                momentum = (
                    recent_races['points'].sum() - early_races['points'].sum()
                ) if len(recent_races) > 0 and len(early_races) > 0 else 0
            else:
                momentum = 0

            feature_dict = {
                'driver_id': driver_id,
                'driver_code': driver['driver_code'],
                'driver_name': driver['driver_name'],
                'constructor_id': constructor_id,
                'constructor_name': driver['constructor_name'],
                'current_points': current_points,
                'current_position': current_position,
                'wins': wins,
                'podiums': podiums,
                'poles': poles,
                'avg_finish_position': avg_finish,
                'avg_points_per_race': avg_points,
                'races_completed': races_completed,
                'last_race_finish': last_finish,
                'last_race_points': last_points,
                'momentum': momentum,
                'constructor_avg_finish': constructor_avg_finish,
                'constructor_avg_points': constructor_avg_points,
            }

            features_list.append(feature_dict)

        return pd.DataFrame(features_list)

    def prepare_prequal_training_data_for_results(self, results):
        results = self._ensure_id_columns(results)
        results = self._ensure_name_columns(results)
        results = self._coerce_round_season(results)

        all_training_features = []

        seasons = sorted(results['season'].dropna().unique().tolist()) if 'season' in results.columns else [None]
        for season in seasons:
            season_results = results if season is None else results[results['season'] == season]
            completed_rounds = sorted(season_results['round'].dropna().unique())
            if season is not None:
                print(f"\nPreparing pre-qualifying training data for season {season}: {completed_rounds}")
            else:
                print(f"\nPreparing pre-qualifying training data for rounds: {completed_rounds}")

            for race_round in completed_rounds:
                past_results = season_results[season_results['round'] < race_round]
                round_standings = self._build_standings_from_results(past_results)

                if past_results.empty:
                    round_driver_pool = season_results[season_results['round'] == race_round][
                        ['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']
                    ].drop_duplicates()
                    round_driver_pool = self._ensure_id_columns(round_driver_pool)
                    round_standings = round_driver_pool.copy()
                    round_standings['points'] = 0
                    round_standings['wins'] = 0
                    round_standings['podiums'] = 0
                    round_standings['position'] = 999

                    race_features = self.engineer_prequal_features_for_round(round_standings, past_results)
                else:
                    race_features = self.engineer_prequal_features_for_round(round_standings, past_results)

                race_results = season_results[season_results['round'] == race_round]
                race_results = self._ensure_id_columns(race_results)
                merged = race_features.merge(
                    race_results[['driver_id', 'finish_position', 'points']],
                    on='driver_id',
                    how='left'
                )
                merged['is_podium'] = (merged['finish_position'] <= 3).astype(int)
                merged['race_round'] = race_round
                if season is not None:
                    merged['season'] = season

                all_training_features.append(merged)
                print(f"  ✓ Round {race_round}: {len(race_features)} drivers")

        if all_training_features:
            training_df = pd.concat(all_training_features, ignore_index=True)
            print(f"\n✓ Built pre-qualifying training data: {len(training_df)} total entries")
            return training_df

        print(f"\n⚠ No training data (no completed races with results)")
        return pd.DataFrame()

    def prepare_historical_prequal_features(self, standings, historical_results, rookie_penalty=1.5):
        standings = self._ensure_id_columns(standings)
        historical_results = self._ensure_id_columns(historical_results)
        historical_results = self._ensure_name_columns(historical_results)
        return self.engineer_prequal_features_for_round(
            standings,
            historical_results,
            rookie_penalty=rookie_penalty,
        )
    
    def prepare_suzuka_features(self):
        """Prepare features specifically for Suzuka (Race 3) prediction"""
        
        standings, results, qualifying = self.load_data()
        
        # Engineer features for Suzuka (Round 3)
        suzuka_features = self.engineer_features_for_race(3, standings, results, qualifying)
        
        # Sort by grid position
        suzuka_features = suzuka_features.sort_values('grid_position')
        
        # Save
        suzuka_features.to_csv(self.data_dir / "suzuka_race3_features.csv", index=False)
        print(f"✓ Saved Suzuka features: {len(suzuka_features)} drivers")
        
        return suzuka_features
    
    def prepare_training_data(self):
        """Prepare data for model training (races 1-2 with results)"""
        
        standings, results, qualifying = self.load_data()
        
        all_training_features = []
        
        # Get available race rounds (those with results)
        completed_rounds = sorted(results['round'].unique())
        
        print(f"\nPreparing training data for rounds: {completed_rounds}")
        
        for race_round in completed_rounds:
            race_features = self.engineer_features_for_race(race_round, standings, results, qualifying)
            
            # Add actual results as labels (podium = top 3)
            race_results = results[results['round'] == race_round]
            
            # Merge features with actual results
            merged = race_features.merge(
                race_results[['driver_id', 'finish_position', 'points']],
                on='driver_id',
                how='left'
            )
            
            # Create label: 1 if podium (top 3), 0 otherwise
            merged['is_podium'] = (merged['finish_position'] <= 3).astype(int)
            merged['race_round'] = race_round
            
            all_training_features.append(merged)
            print(f"  ✓ Round {race_round}: {len(race_features)} drivers")
        
        if all_training_features:
            training_df = pd.concat(all_training_features, ignore_index=True)
            training_df.to_csv(self.data_dir / "training_features.csv", index=False)
            print(f"\n✓ Saved training data: {len(training_df)} total entries")
            return training_df
        else:
            print(f"\n⚠ No training data (no completed races with results)")
            return pd.DataFrame()

    def prepare_prequal_training_data(self):
        """Prepare pre-qualifying training data for all completed rounds."""
        standings, results, qualifying = self.load_data()

        all_training_features = []

        completed_rounds = sorted(results['round'].unique())
        print(f"\nPreparing pre-qualifying training data for rounds: {completed_rounds}")

        for race_round in completed_rounds:
            past_results = results[results['round'] < race_round]
            round_standings = self._build_standings_from_results(past_results)

            if past_results.empty:
                round_driver_pool = results[results['round'] == race_round][
                    ['driver_id', 'driver_code', 'driver_name', 'constructor_id', 'constructor_name']
                ].drop_duplicates()
                round_driver_pool = self._ensure_id_columns(round_driver_pool)
                round_standings = round_driver_pool.copy()
                round_standings['points'] = 0
                round_standings['wins'] = 0
                round_standings['podiums'] = 0
                round_standings['position'] = 999

                race_features = self.engineer_prequal_features_for_round(round_standings, past_results)
            else:
                race_features = self.engineer_prequal_features_for_round(round_standings, past_results)

            race_results = results[results['round'] == race_round]
            race_results = self._ensure_id_columns(race_results)
            merged = race_features.merge(
                race_results[['driver_id', 'finish_position', 'points']],
                on='driver_id',
                how='left'
            )
            merged['is_podium'] = (merged['finish_position'] <= 3).astype(int)
            merged['race_round'] = race_round

            all_training_features.append(merged)
            print(f"  ✓ Round {race_round}: {len(race_features)} drivers")

        if all_training_features:
            training_df = pd.concat(all_training_features, ignore_index=True)
            print(f"\n✓ Built pre-qualifying training data: {len(training_df)} total entries")
            return training_df

        print(f"\n⚠ No training data (no completed races with results)")
        return pd.DataFrame()

    def prepare_next_race_prequal_features(self):
        """Prepare pre-qualifying features for the next race (Miami)."""
        standings, results, qualifying = self.load_data()
        next_race_features = self.engineer_prequal_features_for_round(standings, results)
        print(f"✓ Built next race pre-qualifying features: {len(next_race_features)} drivers")
        return next_race_features


def main():
    print("=" * 70)
    print("FEATURE ENGINEERING FOR F1 SUZUKA PREDICTION")
    print("=" * 70)
    
    engineer = SuzukaFeatureEngineer(data_dir=PATHS["data"])
    
    # Prepare Suzuka features
    print("\n[1] Preparing Suzuka (Race 3) Features")
    print("-" * 70)
    suzuka_features = engineer.prepare_suzuka_features()
    
    print(f"\n📊 Suzuka Feature Matrix ({len(suzuka_features)} drivers):")
    print(suzuka_features[['grid_position', 'driver_code', 'current_points', 'podiums', 
                           'avg_finish_position', 'suzuka_form']].to_string(index=False))
    
    # Prepare training data
    print("\n\n[2] Preparing Training Data (Races 1-2 Results)")
    print("-" * 70)
    training_data = engineer.prepare_training_data()
    
    if not training_data.empty:
        print(f"\n📊 Training Data Summary:")
        print(f"  Total samples: {len(training_data)}")
        print(f"  Podium finishes: {training_data['is_podium'].sum()}")
        print(f"  Podium percentage: {training_data['is_podium'].mean()*100:.1f}%")
        
        print(f"\n  Sample features:")
        print(training_data[['driver_code', 'grid_position', 'current_points', 
                            'avg_points_per_race', 'is_podium', 'finish_position']].head(10).to_string(index=False))
    
    print("\n" + "=" * 70)
    print("✓ FEATURE ENGINEERING COMPLETE")
    print("=" * 70)
    
    return suzuka_features, training_data


if __name__ == "__main__":
    suzuka_features, training_data = main()
