# dash_app.py - Optimized with GitHub Actions remote trigger
import sys
import traceback

print("=" * 60)
print("STARTING DASH APP")
print("=" * 60)

try:
    print("Step 1: Importing libraries...")
    import dash
    from dash import dcc, html, Input, Output, State, ALL
    import pandas as pd
    import os
    import gspread
    from google.oauth2.service_account import Credentials
    import json
    import logging
    import time
    import requests
    from datetime import datetime, timedelta
    from functools import lru_cache
    print("✅ All imports successful")

    # Initialize the Dash app
    print("Step 2: Initializing Dash app...")
    app = dash.Dash(__name__)
    server = app.server
    print("✅ Dash app initialized")

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    print("✅ Logging configured")

except Exception as e:
    print(f"❌ FATAL ERROR DURING STARTUP: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)

# ============================================================================
# CONSTANTS - Single source of truth for all configuration
# ============================================================================

# Layout dimensions
LAYOUT = {
    'header_height': 72,  # Increased to accommodate refresh button with text
    'league_ribbon_height': 56,  # Increased from 48 to give more padding
    'view_ribbon_height': 48,
    'filter_height': 56,
    'header_banner_height': 30,
    'table_offset': 350
}

# Z-index layers
Z_INDEX = {
    'header': 1000,
    'league': 999,
    'view': 998,
    'filters': 997,
    'banner': 996,
    'notification': 9999
}

# Sports configuration
SPORTS = {
    'MLB': 'MLB',
    'NFL': 'NFL',
    'WNBA': 'WNBA'
}

# Colors
COLORS = {
    'primary_text': '#000000',
    'secondary_text': '#6b7280',
    'inactive_text': '#9ca3af',
    'success': '#059669',
    'warning': '#f59e0b',
    'error': '#dc2626',
    'border': '#e5e7eb',
    'light_bg': '#f3f4f6',
    'hover_bg': '#f9fafb',
    'background': '#ffffff',
    'black': '#000000'  # Added black color for refresh button
}

# Google Sheets configuration
SHEETS = {
    'EV_RESULTS': 'EV_RESULTS',
    'CORRELATION_PARLAYS': 'CORRELATION_PARLAYS'
}

# Data columns
COLUMNS = {
    'PLAYER': 'Player',
    'MARKET': 'Market',
    'LINE': 'Line',
    'EV': 'EV %'
}

# Cache configuration
CACHE_DURATION = timedelta(minutes=5)
MAX_RETRIES = 3

# Button style templates with adjusted padding
BUTTON_STYLES = {
    'active': {
        'background': 'none',
        'border': 'none',
        'color': COLORS['primary_text'],
        'fontSize': '14px',
        'fontWeight': '600',
        'padding': '16px 20px',  # Increased vertical padding
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    },
    'inactive': {
        'background': 'none',
        'border': 'none',
        'color': COLORS['inactive_text'],
        'fontSize': '14px',
        'fontWeight': '400',
        'padding': '16px 20px',  # Increased vertical padding
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
}

FILTER_BUTTON_STYLES = {
    'active': {
        'background': 'none',
        'border': 'none',
        'color': COLORS['primary_text'],
        'fontSize': '13px',
        'fontWeight': '600',
        'padding': '8px 16px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    },
    'inactive': {
        'background': 'none',
        'border': 'none',
        'color': COLORS['inactive_text'],
        'fontSize': '13px',
        'fontWeight': '400',
        'padding': '8px 16px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
}

# ============================================================================
# CACHE SYSTEM
# ============================================================================

_cache = {}
_cache_time = {}

# ============================================================================
# CUSTOM CSS
# ============================================================================

app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                margin: 0;
                padding: 0;
                font-family: 'Inter', sans-serif;
                background: white;
                overflow-x: hidden;
            }
            
            #react-entry-point {
                position: relative;
                min-height: 100vh;
            }
            
            [style*="position: fixed"] {
                background: white !important;
            }
            
            button {
                outline: none !important;
                -webkit-appearance: none !important;
                -moz-appearance: none !important;
            }
            
            .table-row {
                background-color: white !important;
            }
            
            .table-row:hover {
                background-color: #f9fafb !important;
            }
            
            #evs-table-container {
                scrollbar-width: none;
                -ms-overflow-style: none;
            }
            
            #evs-table-container::-webkit-scrollbar {
                display: none;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .notification-enter {
                animation: fadeIn 0.3s ease-out;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def clean_market_name(market):
    """Clean market name by removing prefixes and formatting"""
    if not market:
        return market
    
    cleaned = market
    prefixes = ['pitcher_', 'batter_', 'player_', 'player_pass_', 'player_rush_', 'player_reception_']
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    
    cleaned = cleaned.replace('_', ' ')
    cleaned = ' '.join(word.capitalize() for word in cleaned.split())
    
    return cleaned

def validate_ev_data(data):
    """Validate EV data structure to prevent rendering errors"""
    if not isinstance(data, list):
        logger.warning("EV data is not a list")
        return False
    
    if not data:
        return True
    
    required_keys = [COLUMNS['PLAYER'], COLUMNS['MARKET'], COLUMNS['LINE'], COLUMNS['EV']]
    
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"EV item {i} is not a dictionary")
            return False
        
        if not all(key in item for key in required_keys):
            logger.warning(f"EV item {i} missing required keys")
            return False
        
        if not item.get(COLUMNS['PLAYER']):
            logger.warning(f"EV item {i} has empty player name")
            return False
    
    logger.info(f"✅ Validated {len(data)} EV records")
    return True

def validate_parlay_data(data):
    """Validate parlay data structure"""
    if not isinstance(data, list):
        logger.warning("Parlay data is not a list")
        return False
    
    if not data:
        return True
    
    required_keys = ['id', 'anchor', 'batters', 'totalEV', 'leg_count']
    
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            logger.warning(f"Parlay item {i} is not a dictionary")
            return False
        
        if not all(key in item for key in required_keys):
            logger.warning(f"Parlay item {i} missing required keys")
            return False
    
    logger.info(f"✅ Validated {len(data)} parlay records")
    return True

@lru_cache(maxsize=32)
def get_unique_markets_cached(data_hash):
    """Get unique markets (cached) - data_hash is used for cache invalidation"""
    pass

def get_unique_markets(data):
    """Get unique markets from data"""
    if not data:
        return []
    
    data_hash = hash(str(len(data)) + str(data[0] if data else ''))
    get_unique_markets_cached(data_hash)
    
    return sorted(list(set([ev[COLUMNS['MARKET']] for ev in data if ev.get(COLUMNS['MARKET'])])))

# ============================================================================
# GITHUB ACTIONS TRIGGER FUNCTIONS
# ============================================================================

def trigger_github_pipeline(sport='MLB', pipeline=None):
    """
    Trigger GitHub Actions workflow remotely
    
    Args:
        sport: 'MLB', 'NFL', or 'WNBA'
        pipeline: 'full-pipeline', 'steps-1-5-data-only', etc. (if None, auto-determines based on sport)
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Auto-determine pipeline based on sport if not specified
        if pipeline is None:
            if sport == 'MLB':
                # MLB gets full pipeline including parlays (steps 1-7)
                pipeline = 'full-pipeline'
                logger.info(f"🎯 MLB selected - using full pipeline with parlays")
            else:
                # NFL and WNBA only get data steps (1-5) for now
                pipeline = 'steps-1-5-data-only'
                logger.info(f"⚡ {sport} selected - using data-only pipeline (parlays not yet implemented)")
        
        github_token = os.environ.get('GITHUB_TOKEN')
        repo_owner = os.environ.get('GITHUB_REPO_OWNER')
        repo_name = os.environ.get('GITHUB_REPO_NAME')
        
        if not all([github_token, repo_owner, repo_name]):
            logger.error("Missing GitHub credentials in environment variables")
            logger.error(f"GITHUB_TOKEN: {'✓' if github_token else '✗'}")
            logger.error(f"GITHUB_REPO_OWNER: {'✓' if repo_owner else '✗'}")
            logger.error(f"GITHUB_REPO_NAME: {'✓' if repo_name else '✗'}")
            return False
        
        # GitHub API endpoint for repository dispatch
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/dispatches"
        
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
        }
        
        # Payload to trigger workflow
        payload = {
            'event_type': pipeline,
            'client_payload': {
                'sport': sport,
                'triggered_by': 'dash_app',
                'timestamp': datetime.now().isoformat()
            }
        }
        
        logger.info(f"🚀 Triggering GitHub workflow: {sport} - {pipeline}")
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 204:
            logger.info(f"✅ Successfully triggered {sport} {pipeline}")
            return True
        else:
            logger.error(f"❌ GitHub API error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error triggering GitHub workflow: {e}")
        logger.error(traceback.format_exc())
        return False

def invalidate_cache(sport='MLB'):
    """Clear cached data for a sport to force refresh"""
    cache_keys = [f"ev_{sport}", f"parlays_{sport}"]
    for key in cache_keys:
        if key in _cache:
            del _cache[key]
            logger.info(f"🗑️ Deleted cache: {key}")
        if key in _cache_time:
            del _cache_time[key]
            logger.info(f"🗑️ Deleted cache time: {key}")
    logger.info(f"✅ Cache cleared for {sport}")

# ============================================================================
# GOOGLE SHEETS FUNCTIONS WITH RETRY LOGIC
# ============================================================================

def connect_to_sheets_with_retry(max_retries=MAX_RETRIES):
    """Connect to Google Sheets with retry logic"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Connecting to Google Sheets (attempt {attempt + 1}/{max_retries})...")
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            logger.info("✅ Successfully connected to Google Sheets")
            return client
            
        except KeyError as e:
            logger.error("❌ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set")
            raise
            
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Connection failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"All {max_retries} connection attempts failed: {e}")
                raise
    
    return None

def read_ev_results(sport='MLB'):
    """Read Individual EV data from Google Sheets"""
    try:
        client = connect_to_sheets_with_retry()
        if not client:
            return []
        
        spreadsheet_name = f"{sport}_Splash_Data"
        spreadsheet = client.open(spreadsheet_name)
        ev_worksheet = spreadsheet.worksheet(SHEETS['EV_RESULTS'])
        
        all_data = ev_worksheet.get_all_values()
        if not all_data:
            logger.warning(f"No data found in {SHEETS['EV_RESULTS']} sheet")
            return []
        
        # Find header row
        header_row_index = -1
        possible_headers = [COLUMNS['PLAYER'], 'Name', COLUMNS['MARKET'], COLUMNS['LINE'], 'EV', 'Splash_EV_Percentage']
        
        for i, row in enumerate(all_data):
            if row and any(header in row for header in possible_headers):
                header_row_index = i
                break
        
        if header_row_index == -1:
            logger.error("Could not find header row in EV_RESULTS")
            return []
        
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        ev_df = pd.DataFrame(data_rows, columns=headers)
        
        # Find player column
        player_col = None
        for col in ev_df.columns:
            if 'player' in col.lower() or 'name' in col.lower():
                player_col = col
                break
        
        if not player_col:
            logger.error(f"No player column found. Available columns: {list(ev_df.columns)}")
            return []
        
        # Remove empty rows
        ev_df = ev_df[ev_df[player_col].notna() & (ev_df[player_col] != '')]
        
        if ev_df.empty:
            logger.warning("No EV data found after filtering")
            return []
        
        # Convert to format for display
        individual_evs = []
        ev_col = None
        
        for col in ev_df.columns:
            if 'ev' in col.lower() and 'percentage' in col.lower():
                ev_col = col
                break
        
        if not ev_col:
            for col in ev_df.columns:
                if 'ev' in col.lower():
                    ev_col = col
                    break
        
        for _, row in ev_df.iterrows():
            ev_value = row.get(ev_col, 0) if ev_col else '0'
            try:
                ev_float = float(ev_value)
                ev_percent = f"{ev_float:.1%}"
            except (ValueError, TypeError):
                ev_percent = str(ev_value)
            
            raw_market = row.get(COLUMNS['MARKET'], '')
            cleaned_market = clean_market_name(raw_market)
            
            individual_evs.append({
                COLUMNS['PLAYER']: row[player_col],
                COLUMNS['MARKET']: cleaned_market,
                COLUMNS['LINE']: row.get(COLUMNS['LINE'], ''),
                COLUMNS['EV']: ev_percent
            })
        
        logger.info(f"Successfully read {len(individual_evs)} EV records for {sport}")
        return individual_evs
        
    except Exception as e:
        logger.error(f"Error reading EV results for {sport}: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []

def read_correlation_parlays(sport='MLB'):
    """Read Correlation Parlays data from Google Sheets"""
    if sport != SPORTS['MLB']:
        logger.info(f"Correlation parlays not yet implemented for {sport}")
        return []
    
    try:
        client = connect_to_sheets_with_retry()
        if not client:
            return []
        
        spreadsheet = client.open(f"{sport}_Splash_Data")
        parlay_worksheet = spreadsheet.worksheet(SHEETS['CORRELATION_PARLAYS'])
        all_data = parlay_worksheet.get_all_values()
        
        if not all_data:
            logger.warning("No data found in CORRELATION_PARLAYS sheet")
            return []
        
        # Find header row
        header_row_index = -1
        for i, row in enumerate(all_data[:20]):
            non_empty = [cell for cell in row if cell and str(cell).strip()]
            if len(non_empty) >= 5:
                has_underscore_cols = any('_' in str(cell) for cell in row if cell)
                has_id_col = any('id' in str(cell).lower() for cell in row if cell)
                has_pitcher_name = any('pitcher_name' in str(cell).lower() for cell in row if cell)
                
                if has_underscore_cols or (has_id_col and has_pitcher_name):
                    header_row_index = i
                    break
        
        if header_row_index == -1:
            logger.warning("Could not find header row in CORRELATION_PARLAYS")
            return []
        
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        parlay_df = pd.DataFrame(data_rows, columns=headers)
        parlay_df = parlay_df[parlay_df.iloc[:, 0].notna() & (parlay_df.iloc[:, 0] != '')]
        
        if parlay_df.empty:
            logger.warning("No parlay data found after filtering")
            return []
        
        parlays = []
        for idx, row in parlay_df.iterrows():
            try:
                pitcher_name = row.get('Pitcher_Name', '')
                if not pitcher_name:
                    continue
                
                pitcher_market = row.get('Pitcher_Market', '')
                pitcher_market_clean = clean_market_name(pitcher_market) if pitcher_market else ""
                
                batter_legs = []
                batter_num = 1
                
                while batter_num <= 10:
                    batter_col = f'Batter_{batter_num}'
                    batter_data = row.get(batter_col, '')
                    
                    if not batter_data or str(batter_data).strip() == '':
                        break
                    
                    try:
                        parts = [p.strip() for p in str(batter_data).split(',')]
                        if len(parts) >= 4:
                            batter_name = parts[0]
                            batter_market_raw = parts[1]
                            batter_line = parts[2]
                            batter_ev = parts[4] if len(parts) > 4 else ''
                            
                            batter_market_clean = clean_market_name(batter_market_raw)
                            
                            batter_info = f"{batter_name} • {batter_market_clean} {batter_line}"
                            if batter_ev:
                                try:
                                    ev_float = float(batter_ev)
                                    batter_info += f" • EV: {ev_float:.1%}"
                                except:
                                    batter_info += f" • EV: {batter_ev}"
                            
                            batter_legs.append({'Batter': batter_info})
                    except Exception as e:
                        logger.warning(f"Error parsing batter data: {e}")
                    
                    batter_num += 1
                
                if not batter_legs:
                    continue
                
                total_ev = 0
                try:
                    pitcher_ev = row.get('Pitcher_EV', '')
                    if pitcher_ev:
                        total_ev += float(pitcher_ev)
                    
                    for i in range(1, batter_num):
                        batter_col = f'Batter_{i}'
                        batter_data = row.get(batter_col, '')
                        if batter_data:
                            parts = str(batter_data).split(',')
                            if len(parts) > 4:
                                try:
                                    total_ev += float(parts[4].strip())
                                except:
                                    pass
                except:
                    pass
                
                pitcher_info = {
                    'Player': pitcher_name,
                    'Market': pitcher_market_clean,
                    'Line': row.get('Pitcher_Line', ''),
                    'EV': f"{float(row.get('Pitcher_EV', 0)):.1%}" if row.get('Pitcher_EV') else ""
                }
                
                parlay = {
                    'id': row.get('Parlay_ID', f"PARLAY_{idx + 1:03d}"),
                    'anchor': pitcher_info,
                    'batters': batter_legs,
                    'totalEV': f"{total_ev:.1%}" if total_ev else "N/A",
                    'leg_count': 1 + len(batter_legs)
                }
                
                parlays.append(parlay)
                
            except Exception as e:
                logger.error(f"Error parsing parlay row {idx}: {e}")
                continue
        
        logger.info(f"Successfully read {len(parlays)} parlays for {sport}")
        return parlays
        
    except Exception as e:
        logger.error(f"Error reading correlation parlays: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []

# ============================================================================
# CACHED VERSIONS WITH ERROR HANDLING
# ============================================================================

def read_ev_results_cached(sport='MLB'):
    """Cached version of read_ev_results with error handling"""
    cache_key = f"ev_{sport}"
    now = datetime.now()
    
    if (cache_key in _cache and 
        cache_key in _cache_time and 
        now - _cache_time[cache_key] < CACHE_DURATION):
        logger.info(f"✅ Using cached data for {sport} (age: {(now - _cache_time[cache_key]).seconds}s)")
        return _cache[cache_key]
    
    logger.info(f"📥 Fetching fresh data for {sport} from Google Sheets")
    
    try:
        data = read_ev_results(sport)
        
        if validate_ev_data(data):
            _cache[cache_key] = data
            _cache_time[cache_key] = now
            logger.info(f"💾 Cached {len(data)} valid records for {sport}")
            return data
        else:
            logger.error(f"Data validation failed for {sport}, not caching")
            return []
            
    except Exception as e:
        logger.error(f"Failed to fetch EV data for {sport}: {e}")
        if cache_key in _cache:
            logger.warning(f"Returning stale cache for {sport} due to error")
            return _cache[cache_key]
        return []

def read_correlation_parlays_cached(sport='MLB'):
    """Cached version of read_correlation_parlays with error handling"""
    cache_key = f"parlays_{sport}"
    now = datetime.now()
    
    if (cache_key in _cache and 
        cache_key in _cache_time and 
        now - _cache_time[cache_key] < CACHE_DURATION):
        logger.info(f"✅ Using cached parlays for {sport}")
        return _cache[cache_key]
    
    logger.info(f"📥 Fetching fresh parlays for {sport}")
    
    try:
        data = read_correlation_parlays(sport)
        
        if validate_parlay_data(data):
            _cache[cache_key] = data
            _cache_time[cache_key] = now
            logger.info(f"💾 Cached {len(data)} valid parlays for {sport}")
            return data
        else:
            logger.error(f"Parlay validation failed for {sport}, not caching")
            return []
            
    except Exception as e:
        logger.error(f"Failed to fetch parlay data for {sport}: {e}")
        if cache_key in _cache:
            logger.warning(f"Returning stale cache for {sport} due to error")
            return _cache[cache_key]
        return []

# ============================================================================
# APP LAYOUT
# ============================================================================

print("Step 3: Building app layout...")
try:
    app.layout = html.Div([
        # Google Font
        html.Link(
            rel='stylesheet',
            href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
        ),
        
        # Store for current sport and view
        dcc.Store(id='current-sport', data=SPORTS['MLB']),
        dcc.Store(id='current-view', data='individual'),
        dcc.Store(id='evs-data', data=[]),
        dcc.Store(id='parlays-data', data=[]),
        dcc.Store(id='refresh-status', data={'refreshing': False, 'message': '', 'timestamp': '', 'start_time': ''}),
        dcc.Interval(id='refresh-timer', interval=1000, disabled=True),  # Update every second
        
        # 1. TITLE - STICKY with Refresh Button
        html.Div([
            html.Div([
                html.H1("EV SPORTS", style={
                    'margin': '0',
                    'fontSize': '24px',
                    'fontWeight': '700',
                    'color': COLORS['primary_text'],
                    'fontFamily': 'Inter, sans-serif',
                    'letterSpacing': '-0.5px'
                }),
                html.Div([
                    html.Button([
                        "Refresh Data"
                    ], id='refresh-button', n_clicks=0, style={
                        'padding': '10px 20px',
                        'backgroundColor': COLORS['black'],
                        'color': 'white',
                        'border': 'none',
                        'borderRadius': '8px',
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'cursor': 'pointer',
                        'fontFamily': 'Inter, sans-serif',
                        'transition': 'all 0.2s ease',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                    }),
                    html.Div(id='refresh-status-text', style={
                        'fontSize': '11px',
                        'color': COLORS['secondary_text'],
                        'marginTop': '6px',
                        'fontFamily': 'Inter, sans-serif',
                        'textAlign': 'center',
                        'minHeight': '14px'  # Prevents layout shift
                    })
                ], style={
                    'marginLeft': 'auto',
                    'display': 'flex',
                    'flexDirection': 'column',
                    'alignItems': 'flex-end'
                })
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'space-between'
            })
        ], style={
            'padding': '16px 40px',  # Reduced padding to make room
            'backgroundColor': COLORS['background'],
            'borderBottom': f"1px solid {COLORS['border']}",
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'right': '0',
            'zIndex': str(Z_INDEX['header']),
            'height': f'{LAYOUT["header_height"]}px'
        }),
        
        # Spacer for title
        html.Div(style={'height': f"{LAYOUT['header_height']}px"}),
        
        # 2. LEAGUE RIBBON - STICKY with adjusted padding
        html.Div([
            html.Button(SPORTS['MLB'], id="league-mlb", n_clicks=0, style=BUTTON_STYLES['active']),
            html.Button(SPORTS['NFL'], id="league-nfl", n_clicks=0, style=BUTTON_STYLES['inactive']),
            html.Button(SPORTS['WNBA'], id="league-wnba", n_clicks=0, style=BUTTON_STYLES['inactive'])
        ], style={
            'padding': '4px 40px',  # Increased top/bottom padding
            'backgroundColor': COLORS['background'],
            'borderBottom': f"1px solid {COLORS['border']}",
            'display': 'flex',
            'gap': '8px',
            'position': 'fixed',
            'top': f"{LAYOUT['header_height']}px",
            'left': '0',
            'right': '0',
            'zIndex': str(Z_INDEX['league']),
            'height': f'{LAYOUT["league_ribbon_height"]}px',
            'alignItems': 'center'  # Center buttons vertically
        }),
        
        # Spacer for league ribbon
        html.Div(style={'height': f"{LAYOUT['league_ribbon_height']}px"}),
        
        # 3. VIEW RIBBON - STICKY
        html.Div([
            html.Button("Individual EVs", id="view-individual", n_clicks=0, style=BUTTON_STYLES['active']),
            html.Button("Correlation Parlays", id="view-parlays", n_clicks=0, style=BUTTON_STYLES['inactive'])
        ], style={
            'padding': '0 40px',
            'backgroundColor': COLORS['background'],
            'display': 'flex',
            'gap': '8px',
            'position': 'fixed',
            'top': f"{LAYOUT['header_height'] + LAYOUT['league_ribbon_height']}px",
            'left': '0',
            'right': '0',
            'zIndex': str(Z_INDEX['view'])
        }),
        
        # Spacer for view ribbon
        html.Div(style={'height': f"{LAYOUT['view_ribbon_height']}px"}),
        
        # Main content area
        html.Div(id='main-content', style={
            'minHeight': f"calc(100vh - {LAYOUT['header_height'] + LAYOUT['league_ribbon_height'] + LAYOUT['view_ribbon_height']}px)",
            'backgroundColor': COLORS['background'],
            'position': 'relative',
            'overflow': 'hidden'
        })
        
    ], style={
        'backgroundColor': COLORS['background'],
        'minHeight': '100vh',
        'fontFamily': 'Inter, sans-serif'
    })
    
    print("✅ App layout created successfully")
    
except Exception as e:
    print(f"❌ ERROR creating layout: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)

# ============================================================================
# CALLBACKS
# ============================================================================

print("Step 4: Registering callbacks...")

# Sport selection callback
@app.callback(
    [Output('current-sport', 'data'),
     Output('league-mlb', 'style'),
     Output('league-nfl', 'style'),
     Output('league-wnba', 'style')],
    [Input('league-mlb', 'n_clicks'),
     Input('league-nfl', 'n_clicks'),
     Input('league-wnba', 'n_clicks')]
)
def update_sport(mlb_clicks, nfl_clicks, wnba_clicks):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return SPORTS['MLB'], BUTTON_STYLES['active'], BUTTON_STYLES['inactive'], BUTTON_STYLES['inactive']
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'league-nfl':
        return SPORTS['NFL'], BUTTON_STYLES['inactive'], BUTTON_STYLES['active'], BUTTON_STYLES['inactive']
    elif button_id == 'league-wnba':
        return SPORTS['WNBA'], BUTTON_STYLES['inactive'], BUTTON_STYLES['inactive'], BUTTON_STYLES['active']
    else:
        return SPORTS['MLB'], BUTTON_STYLES['active'], BUTTON_STYLES['inactive'], BUTTON_STYLES['inactive']

# View selection callback
@app.callback(
    [Output('current-view', 'data'),
     Output('view-individual', 'style'),
     Output('view-parlays', 'style')],
    [Input('view-individual', 'n_clicks'),
     Input('view-parlays', 'n_clicks')]
)
def update_view(individual_clicks, parlays_clicks):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return 'individual', BUTTON_STYLES['active'], BUTTON_STYLES['inactive']
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'view-parlays':
        return 'parlays', BUTTON_STYLES['inactive'], BUTTON_STYLES['active']
    else:
        return 'individual', BUTTON_STYLES['active'], BUTTON_STYLES['inactive']

# Load data into stores when sport/view changes
@app.callback(
    [Output('evs-data', 'data'),
     Output('parlays-data', 'data')],
    [Input('current-sport', 'data'),
     Input('current-view', 'data')]
)
def load_data_to_store(sport, view):
    """Load data from Google Sheets (with caching and error handling) into browser store"""
    evs_data = []
    parlays_data = []
    
    try:
        if view == 'individual':
            evs_data = read_ev_results_cached(sport)
            logger.info(f"📊 Loaded {len(evs_data)} EV records for {sport} into store")
        elif view == 'parlays':
            parlays_data = read_correlation_parlays_cached(sport)
            logger.info(f"🎯 Loaded {len(parlays_data)} parlays for {sport} into store")
    except Exception as e:
        logger.error(f"Error loading data to store: {e}")
    
    return evs_data, parlays_data

# Refresh button callback with runtime tracking
@app.callback(
    [Output('refresh-status', 'data'),
     Output('refresh-button', 'children'),
     Output('refresh-button', 'disabled'),
     Output('refresh-button', 'style'),
     Output('refresh-timer', 'disabled')],
    [Input('refresh-button', 'n_clicks')],
    [State('current-sport', 'data'),
     State('refresh-button', 'style')],
    prevent_initial_call=True
)
def handle_refresh(n_clicks, sport, current_style):
    """Handle refresh button click"""
    if n_clicks > 0:
        logger.info(f"🔄 Refresh triggered for {sport} (click #{n_clicks})")
        
        # Update button to show loading (keep black, just change opacity)
        loading_style = current_style.copy()
        loading_style['backgroundColor'] = COLORS['black']
        loading_style['opacity'] = '0.7'
        loading_style['cursor'] = 'wait'
        
        # Trigger GitHub Actions - pipeline auto-selected based on sport
        success = trigger_github_pipeline(sport=sport)
        
        if success:
            # Clear cache so next load gets fresh data
            invalidate_cache(sport)
            
            refresh_data = {
                'refreshing': True,
                'message': '',  # No banner message
                'timestamp': datetime.now().isoformat(),
                'start_time': datetime.now().isoformat(),
                'sport': sport
            }
            
            success_style = current_style.copy()
            success_style['backgroundColor'] = COLORS['black']
            
            return (
                refresh_data,
                "Refreshing...",
                True,  # Disable button
                success_style,
                False  # Enable timer
            )
        else:
            error_data = {
                'refreshing': False,
                'message': '',
                'timestamp': datetime.now().isoformat(),
                'sport': sport,
                'error': True
            }
            
            error_style = current_style.copy()
            error_style['backgroundColor'] = COLORS['error']
            
            return (
                error_data,
                "Refresh Failed",
                False,
                error_style,
                True  # Keep timer disabled
            )
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Update runtime text
@app.callback(
    Output('refresh-status-text', 'children'),
    [Input('refresh-timer', 'n_intervals'),
     Input('refresh-status', 'data')]
)
def update_runtime_display(n_intervals, status):
    """Update the runtime display text below the refresh button"""
    if not status:
        return ""
    
    if status.get('error'):
        return "Failed to start refresh"
    
    if status.get('refreshing') and status.get('start_time'):
        # Calculate elapsed time
        start = datetime.fromisoformat(status['start_time'])
        elapsed = datetime.now() - start
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        
        return f"Run time: {minutes}:{seconds:02d}"
    
    elif status.get('completed') or status.get('timeout'):
        # Show completion time
        if status.get('timestamp'):
            completion_time = datetime.fromisoformat(status['timestamp'])
            # Only show if completed within last hour
            if datetime.now() - completion_time < timedelta(hours=1):
                time_str = completion_time.strftime("%-I:%M %p")
                return f"Run Complete as of: {time_str}"
    
    elif status.get('timestamp') and not status.get('refreshing'):
        # Show completion time if we have a recent completion
        completion_time = datetime.fromisoformat(status['timestamp'])
        # Only show if completed within last hour
        if datetime.now() - completion_time < timedelta(hours=1):
            time_str = completion_time.strftime("%-I:%M %p")
            return f"Run Complete as of: {time_str}"
    
    return ""

# Check for completion and reset button
@app.callback(
    [Output('refresh-status', 'data', allow_duplicate=True),
     Output('refresh-button', 'children', allow_duplicate=True),
     Output('refresh-button', 'disabled', allow_duplicate=True),
     Output('refresh-button', 'style', allow_duplicate=True),
     Output('refresh-timer', 'disabled', allow_duplicate=True),
     Output('evs-data', 'data', allow_duplicate=True),
     Output('parlays-data', 'data', allow_duplicate=True)],
    [Input('refresh-timer', 'n_intervals')],
    [State('refresh-status', 'data'),
     State('current-sport', 'data'),
     State('refresh-button', 'style'),
     State('current-view', 'data')],
    prevent_initial_call=True
)
def check_refresh_completion(n_intervals, status, sport, current_style, view):
    """Check if refresh is complete and reload data when done"""
    if not status or not status.get('refreshing'):
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    if status.get('start_time'):
        start = datetime.fromisoformat(status['start_time'])
        elapsed = datetime.now() - start
        
        # Check every 10 seconds after 2 minutes
        if elapsed.total_seconds() >= 120 and n_intervals % 10 == 0:
            # Try to reload data to check if new data is available
            try:
                # Clear cache to force fresh data check
                invalidate_cache(sport)
                
                # Try to load fresh data
                fresh_evs = read_ev_results(sport) if view == 'individual' else []
                fresh_parlays = read_correlation_parlays(sport) if view == 'parlays' and sport == 'MLB' else []
                
                # Check if we got new data (compare timestamps or data counts)
                data_updated = False
                
                # Simple check: if we have data and it wasn't empty before, assume update
                if fresh_evs or fresh_parlays:
                    logger.info(f"Fresh data detected: {len(fresh_evs)} EVs, {len(fresh_parlays)} parlays")
                    data_updated = True
                
                # Also check maximum expected time
                max_time = 300 if sport == 'MLB' else 240  # 5 min for MLB, 4 min for others
                
                if data_updated or elapsed.total_seconds() >= max_time:
                    # Mark as complete
                    updated_status = {
                        'refreshing': False,
                        'message': '',
                        'timestamp': datetime.now().isoformat(),
                        'sport': sport,
                        'completed': True
                    }
                    
                    reset_style = current_style.copy()
                    reset_style['backgroundColor'] = COLORS['black']
                    reset_style['opacity'] = '1'
                    reset_style['cursor'] = 'pointer'
                    
                    return (
                        updated_status,
                        "Refresh Data",
                        False,  # Re-enable button
                        reset_style,
                        True,  # Disable timer
                        fresh_evs if fresh_evs else dash.no_update,
                        fresh_parlays if fresh_parlays else dash.no_update
                    )
                    
            except Exception as e:
                logger.error(f"Error checking for completion: {e}")
        
        # Absolute maximum timeout - force completion
        if elapsed.total_seconds() >= 360:  # 6 minutes absolute max
            updated_status = {
                'refreshing': False,
                'message': '',
                'timestamp': datetime.now().isoformat(),
                'sport': sport,
                'timeout': True
            }
            
            reset_style = current_style.copy()
            reset_style['backgroundColor'] = COLORS['black']
            reset_style['opacity'] = '1'
            reset_style['cursor'] = 'pointer'
            
            # Try one final data reload
            try:
                invalidate_cache(sport)
                fresh_evs = read_ev_results_cached(sport) if view == 'individual' else []
                fresh_parlays = read_correlation_parlays_cached(sport) if view == 'parlays' and sport == 'MLB' else []
            except:
                fresh_evs = dash.no_update
                fresh_parlays = dash.no_update
            
            return (
                updated_status,
                "Refresh Data",
                False,
                reset_style,
                True,
                fresh_evs,
                fresh_parlays
            )
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

# Main content callback - uses stored data
@app.callback(
    Output('main-content', 'children'),
    [Input('current-sport', 'data'),
     Input('current-view', 'data'),
     Input('evs-data', 'data'),
     Input('parlays-data', 'data')]
)
def render_main_content(sport, view, evs_data, parlays_data):
    """Render content using data from store (no Google Sheets calls!)"""
    try:
        if view == 'individual':
            return render_individual_evs_from_store(sport, evs_data)
        else:
            return render_parlays_from_store(sport, parlays_data)
    except Exception as e:
        logger.error(f"Error rendering main content: {e}")
        return render_error_state("Failed to render content. Please refresh the page.")

# Market filter callback - uses stored data
@app.callback(
    [Output('evs-table-container', 'children'),
     Output({'type': 'market-filter', 'index': ALL}, 'style')],
    [Input({'type': 'market-filter', 'index': ALL}, 'n_clicks')],
    [State('evs-data', 'data')],
    prevent_initial_call=True
)
def update_market_filter(n_clicks, stored_data):
    """Filter data from store - NO GOOGLE SHEETS CALLS!"""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    try:
        triggered_id = ctx.triggered[0]['prop_id']
        button_data = json.loads(triggered_id.split('.')[0])
        button_index = button_data['index']
        
        if not stored_data or not validate_ev_data(stored_data):
            return render_empty_state("No valid data available"), dash.no_update
        
        # Get unique markets
        all_markets = get_unique_markets(stored_data)
        
        # Filter data
        if button_index == 0:
            filtered_data = stored_data
        else:
            selected_market = all_markets[button_index - 1]
            filtered_data = [ev for ev in stored_data if ev[COLUMNS['MARKET']] == selected_market]
        
        logger.info(f"🔍 Filtered to {len(filtered_data)} records")
        
        # Update button styles
        button_styles = []
        total_buttons = len(all_markets) + 1
        
        for i in range(total_buttons):
            if i == button_index:
                button_styles.append(FILTER_BUTTON_STYLES['active'])
            else:
                button_styles.append(FILTER_BUTTON_STYLES['inactive'])
        
        return create_evs_table(filtered_data), button_styles
        
    except Exception as e:
        logger.error(f"Error in market filter: {e}")
        return render_error_state("Error filtering data"), dash.no_update

print("✅ All callbacks registered")

# ============================================================================
# RENDER FUNCTIONS
# ============================================================================

def render_individual_evs_from_store(sport, data):
    """Render individual EVs using data from store"""
    
    if not data:
        return render_empty_state(f"No {sport} EV opportunities found.")
    
    if not validate_ev_data(data):
        return render_error_state("Invalid data format. Please refresh the page.")
    
    all_markets = get_unique_markets(data)
    
    filter_section = html.Div([
        html.Div([
            html.Button("All", id={'type': 'market-filter', 'index': 0}, style=FILTER_BUTTON_STYLES['active'])
        ] + [
            html.Button(market, id={'type': 'market-filter', 'index': i+1}, style=FILTER_BUTTON_STYLES['inactive']) 
            for i, market in enumerate(all_markets)
        ], style={
            'display': 'flex',
            'justifyContent': 'center',
            'flexWrap': 'wrap',
            'gap': '4px',
            'padding': '16px 40px'
        })
    ], style={
        'backgroundColor': COLORS['background'],
        'borderBottom': f"1px solid {COLORS['border']}",
        'position': 'fixed',
        'top': f"{LAYOUT['header_height'] + LAYOUT['league_ribbon_height'] + LAYOUT['view_ribbon_height']}px",
        'left': '0',
        'right': '0',
        'zIndex': str(Z_INDEX['filters'])
    })
    
    filter_spacer = html.Div(style={'height': f"{LAYOUT['filter_height']}px"})
    banner_top_spacer = html.Div(style={'height': '20px'})
    
    table_wrapper = html.Div([
        html.Div([
            html.Div('NAME', style={
                'flex': '1',
                'padding': '12px 16px',
                'paddingLeft': '17px',
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': COLORS['secondary_text'],
                'textTransform': 'uppercase'
            }),
            html.Div('MARKET', style={
                'flex': '1',
                'padding': '12px 16px',
                'paddingLeft': '17px',
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': COLORS['secondary_text'],
                'textTransform': 'uppercase'
            }),
            html.Div('LINE', style={
                'flex': '0 0 120px',
                'padding': '12px 16px',
                'paddingLeft': '17px',
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': COLORS['secondary_text'],
                'textTransform': 'uppercase'
            }),
            html.Div('EV', style={
                'flex': '0 0 100px',
                'padding': '12px 16px',
                'paddingLeft': '17px',
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': COLORS['secondary_text'],
                'textTransform': 'uppercase'
            })
        ], style={
            'display': 'flex',
            'border': f"1px solid {COLORS['border']}",
            'borderBottom': 'none',
            'borderRadius': '8px 8px 0 0',
            'backgroundColor': COLORS['light_bg']
        }),
        
        html.Div(
            id='evs-table-container',
            children=[create_evs_table(data)],
            style={
                'height': f"calc(100vh - {LAYOUT['table_offset']}px)",
                'overflowY': 'auto',
                'position': 'relative'
            }
        )
    ], style={
        'maxWidth': '1200px',
        'margin': '0 auto',
        'padding': '0 40px'
    })
    
    return html.Div([
        filter_section,
        filter_spacer,
        banner_top_spacer,
        table_wrapper
    ])

def create_evs_table(data):
    """Create table rows from data"""
    if not data:
        return render_empty_state("No data matches this filter.")
    
    return html.Div([
        html.Div([
            html.Div([
                html.Div(row[COLUMNS['PLAYER']], style={
                    'flex': '1',
                    'padding': '14px 16px',
                    'fontWeight': '500',
                    'color': '#111827',
                    'fontSize': '14px'
                }),
                html.Div(row[COLUMNS['MARKET']], style={
                    'flex': '1',
                    'padding': '14px 16px',
                    'color': '#374151',
                    'fontSize': '14px'
                }),
                html.Div(row[COLUMNS['LINE']], style={
                    'flex': '0 0 120px',
                    'padding': '14px 16px',
                    'color': '#374151',
                    'fontSize': '14px'
                }),
                html.Div(row[COLUMNS['EV']], style={
                    'flex': '0 0 100px',
                    'padding': '14px 16px',
                    'fontWeight': '600',
                    'color': COLORS['success'],
                    'fontSize': '14px'
                })
            ], className='table-row', style={
                'display': 'flex',
                'borderBottom': f"1px solid {COLORS['light_bg']}" if row != data[-1] else 'none',
                'backgroundColor': COLORS['background']
            })
            for row in data
        ], style={'fontFamily': 'Inter, sans-serif'})
    ], style={
        'border': f"1px solid {COLORS['border']}",
        'borderRadius': '0 0 8px 8px',
        'borderTop': 'none',
        'overflow': 'hidden',
        'backgroundColor': COLORS['background']
    })

def render_parlays_from_store(sport, parlays_data):
    """Render correlation parlays from stored data"""
    if sport not in [SPORTS['MLB']]:
        return render_empty_state(f"{sport} correlation parlays coming soon!")
    
    if not parlays_data:
        return render_empty_state(f"No {sport} correlation parlays found.")
    
    if not validate_parlay_data(parlays_data):
        return render_error_state("Invalid parlay data format. Please refresh the page.")
    
    return html.Div([
        html.Div([
            render_parlay_card(parlay) for parlay in parlays_data
        ], style={
            'maxWidth': '1200px',
            'margin': '0 auto',
            'padding': '20px 40px 60px 40px',
            'height': f"calc(100vh - 220px)",
            'overflowY': 'auto',
            'position': 'relative'
        })
    ])

def render_parlay_card(parlay):
    """Render a single parlay card"""
    return html.Div([
        html.Div([
            html.Span(f"{parlay['id']} • {parlay['leg_count']} Legs • Total EV: ", style={
                'color': COLORS['secondary_text'],
                'fontSize': '12px',
                'fontWeight': '500'
            }),
            html.Span(parlay['totalEV'], style={
                'color': COLORS['success'],
                'fontSize': '12px',
                'fontWeight': '600'
            })
        ], style={
            'backgroundColor': COLORS['hover_bg'],
            'padding': '12px 20px',
            'borderBottom': f"1px solid {COLORS['border']}",
            'fontFamily': 'Inter, sans-serif'
        }),
        
        html.Div([
            html.Div([
                html.Span(parlay['anchor']['Player'], style={
                    'fontWeight': '700',
                    'fontSize': '15px',
                    'color': '#111827'
                }),
                html.Span(f" • {parlay['anchor']['Market']} {parlay['anchor']['Line']}", style={
                    'fontSize': '14px',
                    'fontWeight': '600',
                    'color': '#374151'
                }),
                html.Span(f" • EV: {parlay['anchor']['EV']}", style={
                    'fontSize': '14px',
                    'color': COLORS['success'],
                    'fontWeight': '600',
                    'marginLeft': '8px'
                }) if parlay['anchor']['EV'] else None
            ])
        ], style={
            'padding': '16px 20px',
            'borderBottom': f"1px solid {COLORS['border']}",
            'fontFamily': 'Inter, sans-serif'
        }),
        
        html.Div([
            html.Div([
                html.Div(batter['Batter'], style={
                    'fontSize': '14px',
                    'color': '#374151',
                    'padding': '10px 0',
                    'borderBottom': f"1px solid {COLORS['light_bg']}" if i < len(parlay['batters']) - 1 else 'none'
                })
                for i, batter in enumerate(parlay['batters'])
            ])
        ], style={
            'padding': '16px 20px',
            'fontFamily': 'Inter, sans-serif'
        })
        
    ], style={
        'backgroundColor': COLORS['background'],
        'border': f"1px solid {COLORS['border']}",
        'borderRadius': '8px',
        'overflow': 'hidden',
        'marginBottom': '20px'
    })

def render_empty_state(message):
    """Render empty state with custom message"""
    return html.Div([
        html.P(message, style={
            'textAlign': 'center',
            'padding': '60px 20px',
            'color': COLORS['secondary_text'],
            'fontSize': '16px',
            'fontFamily': 'Inter, sans-serif'
        })
    ])

def render_error_state(message):
    """Render error state with custom message"""
    return html.Div([
        html.Div([
            html.P("⚠️ Error", style={
                'fontSize': '18px',
                'fontWeight': '600',
                'color': COLORS['error'],
                'marginBottom': '8px',
                'fontFamily': 'Inter, sans-serif'
            }),
            html.P(message, style={
                'fontSize': '14px',
                'color': COLORS['secondary_text'],
                'fontFamily': 'Inter, sans-serif'
            })
        ], style={
            'textAlign': 'center',
            'padding': '60px 20px',
            'maxWidth': '400px',
            'margin': '0 auto'
        })
    ])

print("=" * 60)
print("✅ DASH APP INITIALIZATION COMPLETE")
print("=" * 60)

if __name__ == '__main__':
    try:
        port = int(os.environ.get('PORT', 8050))
        print(f"Starting server on port {port}...")
        app.run_server(debug=False, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"❌ ERROR starting server: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)
