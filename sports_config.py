# sports_config.py - Central configuration for all sports
"""
Sports configuration file that controls all sport-specific settings.
This is the single source of truth for differences between sports.
"""

SPORTS_CONFIG = {
    'MLB': {
        # Data source configurations
        'spreadsheet_name': 'MLB_Splash_Data',
        'odds_api_sport': 'baseball_mlb',
        'espn_sport': 'baseball',
        'espn_league': 'mlb',
        'splash_league': 'mlb',
        
        # Active season months (March=3 through October=10)
        'season_active': [3, 4, 5, 6, 7, 8, 9, 10],
        
        # Days of week that games typically occur (0=Mon, 6=Sun)
        'game_days': [0, 1, 2, 3, 4, 5, 6],  # MLB plays daily
        
        # Market mappings (Splash Sports name -> Odds API name)
        'market_mappings': {
            'strikeouts': 'pitcher_strikeouts',
            'earned_runs': 'pitcher_earned_runs',
            'hits': 'batter_hits',
            'hits_allowed': 'pitcher_hits_allowed',
            'hits_plus_runs_plus_RBIs': 'hits_runs_rbis',
            'runs': 'batter_runs_scored',
            'batter_singles': 'batter_singles',
            'total_bases': 'batter_total_bases',
            'RBIs': 'batter_rbis',
            'total_outs': 'pitcher_outs',
            'singles': 'batter_singles',
            'walks': 'batter_walks',
            'stolen_bases': 'batter_stolen_bases'
        },
        
        # Markets to fetch from Odds API
        'odds_markets': [
            'pitcher_strikeouts', 
            'pitcher_hits_allowed', 
            'pitcher_outs',
            'pitcher_earned_runs', 
            'batter_total_bases', 
            'batter_hits',
            'batter_runs_scored', 
            'batter_rbis', 
            'batter_singles',
            'batter_walks',
            'batter_stolen_bases',
            'hits_runs_rbis'
        ],
        
        # Correlation definitions for parlays
        'correlations': {
            'pitcher_strikeouts': {
                'opposing_market': 'batter_hits',
                'correlation_strength': -0.70,
                'bet_logic': 'opposite',  # Over strikeouts → Under hits
                'description': 'More strikeouts means fewer hits for opposing batters'
            },
            'pitcher_earned_runs': {
                'opposing_market': 'batter_runs_scored',
                'correlation_strength': 0.70,
                'bet_logic': 'same',  # Over earned runs → Over runs scored
                'description': 'Pitcher allowing runs means opposing batters score'
            },
            'pitcher_hits_allowed': {
                'opposing_market': 'batter_hits',
                'correlation_strength': 0.75,
                'bet_logic': 'same',  # Over hits allowed → Over hits
                'description': 'Pitcher allowing hits means batters get hits'
            }
        },
        
        # EV calculation parameters
        'ev_params': {
            'min_books': 3,           # Minimum sportsbooks needed
            'min_true_prob': 0.50,    # Minimum true probability
            'ev_threshold': 0.01,     # 1% minimum EV
            'min_anchor_ev': 0.01,    # For pitcher anchors
            'min_batter_ev': 0.005,   # For batter legs
            'max_parlays': 10         # Max parlays to build
        },
        
        # Sportsbooks to include
        'sportsbooks': [
            'fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus',
            'betrivers', 'unibet', 'bovada', 'mybookieag', 'betus', 
            'williamhill_us', 'wynnbet', 'betway', 'foxbet'
        ]
    },
    
    'NFL': {
        # Data source configurations
        'spreadsheet_name': 'NFL_Splash_Data',
        'odds_api_sport': 'americanfootball_nfl',
        'espn_sport': 'football',
        'espn_league': 'nfl',
        'splash_league': 'nfl',
        
        # Active season months (September=9 through February=2)
        'season_active': [9, 10, 11, 12, 1, 2],
        
        # Days of week that games typically occur (0=Mon, 6=Sun)
        # Thursday=3, Sunday=6, Monday=0
        'game_days': [0, 3, 6],  # Mon, Thu, Sun
        
        # Market mappings (Splash Sports name -> Odds API name)
        'market_mappings': {
            'passing_yards': 'player_pass_yds',
            'passing_tds': 'player_pass_tds',
            'passing_completions': 'player_pass_completions',
            'receptions': 'player_receptions',
            'receiving_yards': 'player_reception_yds',
            'pass_rush_yards': 'player_pass_rush_yds',
            'rush_reception_yards': 'player_rush_reception_yds',
            'interceptions': 'player_pass_interceptions',
            'kicking_points': 'player_kicking_points',
            'field_goals': 'player_field_goals'
        },
        
        # Markets to fetch from Odds API - YOUR REQUIRED LIST
        'odds_markets': [
            'player_pass_yds',              # passing yards
            'player_pass_tds',              # passing TDs
            'player_pass_completions',      # pass completions
            'player_receptions',            # receptions
            'player_reception_yds',         # receiving yards
            'player_pass_rush_yds',         # pass + rushing yards (combined)
            'player_rush_reception_yds',    # rushes + receiving yards (combined)
            'player_pass_interceptions',    # interceptions
            'player_kicking_points',        # kicking pts
            'player_field_goals'            # field goals
        ],
        
        # Correlation definitions for parlays (can be refined later)
        'correlations': {
            # Same team positive correlations
            'player_pass_yds': {
                'opposing_market': 'player_reception_yds',
                'correlation_strength': 0.85,
                'bet_logic': 'same',
                'same_team': True,
                'description': 'QB passing yards correlate with receiver yards'
            },
            'player_pass_tds': {
                'opposing_market': 'player_anytime_td_scorer',
                'correlation_strength': 0.65,
                'bet_logic': 'same',
                'same_team': True,
                'description': 'QB TDs mean receivers/RBs score'
            },
            'player_pass_completions': {
                'opposing_market': 'player_receptions',
                'correlation_strength': 0.90,
                'bet_logic': 'same',
                'same_team': True,
                'description': 'Completions directly create receptions'
            }
        },
        
        # EV calculation parameters (slightly different from MLB)
        'ev_params': {
            'min_books': 3,
            'min_true_prob': 0.45,    # Lower threshold for NFL
            'ev_threshold': 0.015,    # 1.5% minimum EV
            'min_anchor_ev': 0.015,
            'min_batter_ev': 0.01,    # Called "batter" but means "secondary leg"
            'max_parlays': 10
        },
        
        # Sportsbooks to include
        'sportsbooks': [
            'fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus',
            'betrivers', 'unibet', 'bovada', 'mybookieag', 'betus',
            'williamhill_us', 'wynnbet', 'betway', 'foxbet', 'barstool'
        ]
    }
}

    'WNBA': {
            # Data source configurations
            'spreadsheet_name': 'WNBA_Splash_Data',
            'odds_api_sport': 'basketball_wnba',
            'espn_sport': 'basketball',
            'espn_league': 'wnba',
            'splash_league': 'wnba',
            
            # Active season months (May=5 through October=10)
            'season_active': [5, 6, 7, 8, 9, 10],
            
            # Days of week that games typically occur
            'game_days': [0, 1, 2, 3, 4, 5, 6],  # WNBA plays throughout the week
            
            # Market mappings (Splash Sports name -> Odds API name)
            'market_mappings': {
                'points': 'player_points',
                'rebounds': 'player_rebounds',
                'assists': 'player_assists',
                'threes': 'player_threes',
                'blocks': 'player_blocks',
                'steals': 'player_steals',
                'points_rebounds_assists': 'player_points_rebounds_assists',
                'points_rebounds': 'player_points_rebounds',
                'points_assists': 'player_points_assists',
                'rebounds_assists': 'player_rebounds_assists'
            },
            
            # Markets to fetch from Odds API
            'odds_markets': [
                'player_points',
                'player_rebounds',
                'player_assists',
                'player_threes',
                'player_blocks',
                'player_steals',
                'player_points_rebounds_assists',
                'player_points_rebounds',
                'player_points_assists',
                'player_rebounds_assists'
            ],
            
            # No correlations defined yet for WNBA (can add later)
            'correlations': {},
            
            # EV calculation parameters
            'ev_params': {
                'min_books': 3,
                'min_true_prob': 0.45,
                'ev_threshold': 0.01,
                'min_anchor_ev': 0.01,
                'min_batter_ev': 0.005,  # Not used for WNBA but keeping for consistency
                'max_parlays': 10
            },
            
            # Sportsbooks to include
            'sportsbooks': [
                'fanduel', 'draftkings', 'betmgm', 'caesars', 'pointsbetus',
                'betrivers', 'unibet', 'bovada', 'mybookieag', 'betus',
                'williamhill_us', 'wynnbet', 'betway', 'foxbet', 'barstool'
            ]
        }
    }
def get_sport_config(sport):
    """
    Get configuration for a specific sport.
    
    Args:
        sport (str): Sport name (MLB, NFL, etc.)
        
    Returns:
        dict: Configuration dictionary for the sport
    """
    sport = sport.upper()
    if sport not in SPORTS_CONFIG:
        raise ValueError(f"Sport '{sport}' not configured. Available sports: {list(SPORTS_CONFIG.keys())}")
    return SPORTS_CONFIG[sport]

def get_active_sports():
    """
    Get list of sports currently in season.
    
    Returns:
        list: List of active sport names
    """
    from datetime import datetime
    current_month = datetime.now().month
    current_day = datetime.now().weekday()  # 0=Monday, 6=Sunday
    
    active_sports = []
    
    for sport, config in SPORTS_CONFIG.items():
        # Check if sport is in season
        if current_month in config['season_active']:
            # Check if today is a game day for this sport
            if current_day in config['game_days']:
                active_sports.append(sport)
    
    return active_sports

def is_sport_active(sport):
    """
    Check if a specific sport is currently active.
    
    Args:
        sport (str): Sport name
        
    Returns:
        bool: True if sport is in season and has games today
    """
    return sport.upper() in get_active_sports()

# Make it easy to see config when running directly
if __name__ == "__main__":
    import json
    print("Available sports configurations:")
    for sport in SPORTS_CONFIG:
        print(f"\n{sport}:")
        print(f"  Spreadsheet: {SPORTS_CONFIG[sport]['spreadsheet_name']}")
        print(f"  Season months: {SPORTS_CONFIG[sport]['season_active']}")
        print(f"  Game days: {SPORTS_CONFIG[sport]['game_days']}")
        print(f"  Number of markets: {len(SPORTS_CONFIG[sport]['odds_markets'])}")
        print(f"  Number of correlations: {len(SPORTS_CONFIG[sport]['correlations'])}")
