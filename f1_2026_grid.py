"""
2026 F1 Driver Lineup - Official Grid
Based on verified 2026 season driver assignments
"""

import warnings

warnings.warn(
    "f1_2026_grid.py is deprecated; use config/grid_2026.yaml via "
    "config.grid_loader.load_grid instead.",
    DeprecationWarning,
    stacklevel=2,
)

DRIVERS_2026 = {
    # Red Bull Racing
    'verstappen': {
        'full_name': 'Max Verstappen',
        'code': 'VER',
        'number': 1,
        'team_id': 'red_bull',
        'team_name': 'Red Bull Racing',
        'nationality': 'Dutch'
    },
    'hadjar': {
        'full_name': 'Isaac Hadjar',
        'code': 'HAD',
        'number': 2,
        'team_id': 'red_bull',
        'team_name': 'Red Bull Racing',
        'nationality': 'Venezuelan'
    },
    
    # Ferrari
    'leclerc': {
        'full_name': 'Charles Leclerc',
        'code': 'LEC',
        'number': 16,
        'team_id': 'ferrari',
        'team_name': 'Ferrari',
        'nationality': 'Monegasque'
    },
    'hamilton': {
        'full_name': 'Lewis Hamilton',
        'code': 'HAM',
        'number': 44,
        'team_id': 'ferrari',
        'team_name': 'Ferrari',
        'nationality': 'British'
    },
    
    # Mercedes
    'antonelli': {
        'full_name': 'Kimi Antonelli',
        'code': 'ANT',
        'number': 12,
        'team_id': 'mercedes',
        'team_name': 'Mercedes',
        'nationality': 'Italian'
    },
    'russell': {
        'full_name': 'George Russell',
        'code': 'RUS',
        'number': 63,
        'team_id': 'mercedes',
        'team_name': 'Mercedes',
        'nationality': 'British'
    },
    
    # Haas
    'ocon': {
        'full_name': 'Esteban Ocon',
        'code': 'OCO',
        'number': 31,
        'team_id': 'haas',
        'team_name': 'Haas',
        'nationality': 'French'
    },
    'bearman': {
        'full_name': 'Oliver Bearman',
        'code': 'BEA',
        'number': 50,
        'team_id': 'haas',
        'team_name': 'Haas',
        'nationality': 'British'
    },
    
    # Audi
    'hulkenberg': {
        'full_name': 'Nico Hulkenberg',
        'code': 'HUL',
        'number': 27,
        'team_id': 'audi',
        'team_name': 'Audi',
        'nationality': 'German'
    },
    'bortoletto': {
        'full_name': 'Gabriel Bortoletto',
        'code': 'BOR',
        'number': 5,
        'team_id': 'audi',
        'team_name': 'Audi',
        'nationality': 'Brazilian'
    },
    
    # Williams
    'sainz': {
        'full_name': 'Carlos Sainz',
        'code': 'SAI',
        'number': 55,
        'team_id': 'williams',
        'team_name': 'Williams',
        'nationality': 'Spanish'
    },
    'albon': {
        'full_name': 'Alex Albon',
        'code': 'ALB',
        'number': 23,
        'team_id': 'williams',
        'team_name': 'Williams',
        'nationality': 'Thai-British'
    },
    
    # Cadillac
    'bottas': {
        'full_name': 'Valtteri Bottas',
        'code': 'BOT',
        'number': 77,
        'team_id': 'cadillac',
        'team_name': 'Cadillac',
        'nationality': 'Finnish'
    },
    'perez': {
        'full_name': 'Sergio Perez',
        'code': 'PER',
        'number': 11,
        'team_id': 'cadillac',
        'team_name': 'Cadillac',
        'nationality': 'Mexican'
    },
    
    # McLaren
    'piastri': {
        'full_name': 'Oscar Piastri',
        'code': 'PIA',
        'number': 81,
        'team_id': 'mclaren',
        'team_name': 'McLaren',
        'nationality': 'Australian'
    },
    'norris': {
        'full_name': 'Lando Norris',
        'code': 'NOR',
        'number': 4,
        'team_id': 'mclaren',
        'team_name': 'McLaren',
        'nationality': 'British'
    },
    
    # Aston Martin
    'stroll': {
        'full_name': 'Lance Stroll',
        'code': 'STR',
        'number': 18,
        'team_id': 'aston_martin',
        'team_name': 'Aston Martin',
        'nationality': 'Canadian'
    },
    'alonso': {
        'full_name': 'Fernando Alonso',
        'code': 'ALO',
        'number': 14,
        'team_id': 'aston_martin',
        'team_name': 'Aston Martin',
        'nationality': 'Spanish'
    },
    
    # Alpine
    'gasly': {
        'full_name': 'Pierre Gasly',
        'code': 'GAS',
        'number': 10,
        'team_id': 'alpine',
        'team_name': 'Alpine',
        'nationality': 'French'
    },
    'colapinto': {
        'full_name': 'Franco Colapinto',
        'code': 'COL',
        'number': 43,
        'team_id': 'alpine',
        'team_name': 'Alpine',
        'nationality': 'Argentine'
    },
    
    # Visa Cash App RB
    'lawson': {
        'full_name': 'Liam Lawson',
        'code': 'LAW',
        'number': 30,
        'team_id': 'vcarb',
        'team_name': 'Visa Cash App RB',
        'nationality': 'New Zealand'
    },
    'lindblad': {
        'full_name': 'Arvid Lindblad',
        'code': 'LIN',
        'number': 62,
        'team_id': 'vcarb',
        'team_name': 'Visa Cash App RB',
        'nationality': 'Swedish'
    },
}

TEAMS_2026 = {
    'red_bull': {'name': 'Red Bull Racing', 'drivers': ['verstappen', 'hadjar']},
    'ferrari': {'name': 'Ferrari', 'drivers': ['leclerc', 'hamilton']},
    'mercedes': {'name': 'Mercedes', 'drivers': ['antonelli', 'russell']},
    'haas': {'name': 'Haas', 'drivers': ['ocon', 'bearman']},
    'audi': {'name': 'Audi', 'drivers': ['hulkenberg', 'bortoletto']},
    'williams': {'name': 'Williams', 'drivers': ['sainz', 'albon']},
    'cadillac': {'name': 'Cadillac', 'drivers': ['bottas', 'perez']},
    'mclaren': {'name': 'McLaren', 'drivers': ['piastri', 'norris']},
    'aston_martin': {'name': 'Aston Martin', 'drivers': ['stroll', 'alonso']},
    'alpine': {'name': 'Alpine', 'drivers': ['gasly', 'colapinto']},
    'vcarb': {'name': 'Visa Cash App RB', 'drivers': ['lawson', 'lindblad']},
}

if __name__ == "__main__":
    print("=" * 70)
    print("2026 F1 DRIVER GRID")
    print("=" * 70)
    for team_id, team_info in TEAMS_2026.items():
        print(f"\n{team_info['name']}:")
        for driver_id in team_info['drivers']:
            driver = DRIVERS_2026[driver_id]
            print(f"  #{driver['number']} {driver['full_name']} ({driver['code']})")
    print(f"\nTotal drivers: {len(DRIVERS_2026)}")
    print(f"Total teams: {len(TEAMS_2026)}")
