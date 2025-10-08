# Updated NFL section for sports_config.py

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
