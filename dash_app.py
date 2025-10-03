# dash_app.py - Real data integration with Google Sheets debugging
import dash
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
import os
import gspread
from google.oauth2.service_account import Credentials
import json
import logging

# Initialize the Dash app with server configuration
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # Expose server for deployment

# Inject custom CSS for fixed header
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            #header-fixed {
                position: fixed !important;
                top: 0 !important;
                left: 0 !important;
                right: 0 !important;
                width: 100% !important;
                z-index: 1000 !important;
            }
            #ribbons-fixed {
                position: fixed !important;
                top: 64px !important;
                left: 0 !important;
                right: 0 !important;
                width: 100% !important;
                z-index: 999 !important;
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_market_name(market):
    """Clean market name by removing pitcher/batter prefix and formatting"""
    if not market:
        return market
    
    # Remove "pitcher_" or "batter_" prefix (case insensitive)
    cleaned = market
    if cleaned.lower().startswith('pitcher_'):
        cleaned = cleaned[8:]
    elif cleaned.lower().startswith('batter_'):
        cleaned = cleaned[7:]
    
    # Replace underscores with spaces
    cleaned = cleaned.replace('_', ' ')
    
    # Capitalize each word
    cleaned = ' '.join(word.capitalize() for word in cleaned.split())
    
    return cleaned

def connect_to_sheets():
    """Connect to Google Sheets using service account"""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(credentials)
        logger.info("✅ Successfully connected to Google Sheets")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None

def read_ev_results():
    """Read Individual EV data from Google Sheets EV_RESULTS with detailed debugging"""
    try:
        client = connect_to_sheets()
        if not client:
            logger.error("Failed to get Google Sheets client")
            return []
        
        logger.info("📊 Attempting to open MLB_Splash_Data spreadsheet...")
        spreadsheet = client.open("MLB_Splash_Data")
        logger.info("✅ Successfully opened spreadsheet")
        
        logger.info("📋 Attempting to access EV_RESULTS worksheet...")
        ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
        logger.info("✅ Successfully accessed EV_RESULTS worksheet")
        
        # Get all data and skip metadata rows
        logger.info("📥 Reading all data from worksheet...")
        all_data = ev_worksheet.get_all_values()
        
        if not all_data:
            logger.warning("EV_RESULTS sheet is empty")
            return []
        
        # Debug: Show first 10 rows of raw data
        logger.info(f"Total rows in sheet: {len(all_data)}")
        for i, row in enumerate(all_data[:10]):
            logger.info(f"Row {i}: {row[:8]}")  # Show first 8 columns
        
        # Find header row (skip metadata) - be more flexible
        header_row_index = -1
        possible_headers = ['Player', 'Name', 'Market', 'Line', 'EV', 'Splash_EV_Percentage']
        
        for i, row in enumerate(all_data):
            if row and any(header in row for header in possible_headers):
                logger.info(f"Found potential header row at index {i}: {row}")
                header_row_index = i
                break
        
        if header_row_index == -1:
            logger.warning("Could not find header row in EV_RESULTS")
            logger.info("Looking for any row with multiple non-empty cells...")
            for i, row in enumerate(all_data):
                non_empty = [cell for cell in row if cell and str(cell).strip()]
                if len(non_empty) >= 5:
                    logger.info(f"Row {i} has {len(non_empty)} non-empty cells: {non_empty}")
                    if i <= 15:  # Only consider first 15 rows as potential headers
                        header_row_index = i
                        break
        
        if header_row_index == -1:
            logger.error("Still no header row found")
            return []
        
        # Extract headers and data
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        
        logger.info(f"Using headers from row {header_row_index}: {headers}")
        logger.info(f"Data rows available: {len(data_rows)}")
        
        # Show first few data rows
        for i, row in enumerate(data_rows[:3]):
            logger.info(f"Data row {i}: {row[:6]}")
        
        # Create DataFrame
        ev_df = pd.DataFrame(data_rows, columns=headers)
        
        # Debug DataFrame creation
        logger.info(f"DataFrame shape: {ev_df.shape}")
        logger.info(f"DataFrame columns: {list(ev_df.columns)}")
        
        # Look for Player column variations
        player_col = None
        for col in ev_df.columns:
            if 'player' in col.lower() or 'name' in col.lower():
                player_col = col
                break
        
        if not player_col:
            logger.error(f"No player column found. Available columns: {list(ev_df.columns)}")
            return []
        
        logger.info(f"Using player column: '{player_col}'")
        
        # Remove empty rows based on player column
        before_filter = len(ev_df)
        ev_df = ev_df[ev_df[player_col].notna() & (ev_df[player_col] != '')]
        after_filter = len(ev_df)
        
        logger.info(f"Rows after filtering: {after_filter} (removed {before_filter - after_filter})")
        
        if ev_df.empty:
            logger.warning("No EV data found after filtering")
            return []
        
        # Show sample of actual data
        logger.info(f"Sample data from first row:")
        if len(ev_df) > 0:
            first_row = ev_df.iloc[0]
            for col, val in first_row.items():
                logger.info(f"  {col}: {val}")
        
        # Convert to format expected by dash table
        individual_evs = []
        ev_col = None
        
        # Find EV column
        for col in ev_df.columns:
            if 'ev' in col.lower() and 'percentage' in col.lower():
                ev_col = col
                break
        
        if not ev_col:
            logger.warning("No EV percentage column found, looking for alternatives...")
            for col in ev_df.columns:
                if 'ev' in col.lower():
                    ev_col = col
                    logger.info(f"Using EV column: {col}")
                    break
        
        for _, row in ev_df.iterrows():
            # Format EV percentage
            ev_value = row.get(ev_col, 0) if ev_col else '0'
            try:
                ev_float = float(ev_value)
                ev_percent = f"{ev_float:.1%}"
            except (ValueError, TypeError):
                ev_percent = str(ev_value)
            
            # Clean the market name
            raw_market = row.get('Market', '')
            cleaned_market = clean_market_name(raw_market)
            
            individual_evs.append({
                'Player': row[player_col],
                'Market': cleaned_market,
                'Line': row.get('Line', ''),
                'EV %': ev_percent
            })
        
        logger.info(f"Successfully converted {len(individual_evs)} Individual EV opportunities")
        
        # Show first converted result
        if individual_evs:
            logger.info(f"First converted result: {individual_evs[0]}")
        
        return individual_evs
        
    except Exception as e:
        logger.error(f"Error reading EV results: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []

def read_correlation_parlays():
    """Read Correlation Parlays data from Google Sheets with detailed debugging"""
    try:
        client = connect_to_sheets()
        if not client:
            logger.error("❌ Failed to get Google Sheets client for parlays")
            return []
        
        logger.info("📊 Attempting to read Correlation Parlays...")
        spreadsheet = client.open("MLB_Splash_Data")
        
        # Log all available worksheets
        all_worksheets = spreadsheet.worksheets()
        logger.info(f"📋 Available worksheets: {[ws.title for ws in all_worksheets]}")
        
        # Try to find the correlation parlays sheet
        parlay_sheet_name = None
        for ws in all_worksheets:
            if 'correlation' in ws.title.lower() or 'parlay' in ws.title.lower():
                parlay_sheet_name = ws.title
                logger.info(f"✅ Found potential parlay sheet: '{parlay_sheet_name}'")
                break
        
        if not parlay_sheet_name:
            logger.error("❌ No worksheet with 'correlation' or 'parlay' in name found")
            logger.info("💡 Please check the exact sheet name in Google Sheets")
            return []
        
        parlay_worksheet = spreadsheet.worksheet(parlay_sheet_name)
        logger.info(f"✅ Successfully accessed '{parlay_sheet_name}' worksheet")
        
        all_data = parlay_worksheet.get_all_values()
        
        if not all_data:
            logger.warning("⚠️ Parlay sheet is empty")
            return []
        
        logger.info(f"📊 Total rows in parlay sheet: {len(all_data)}")
        
        # Show first 10 rows for debugging
        logger.info("🔍 First 10 rows of raw data:")
        for i, row in enumerate(all_data[:10]):
            logger.info(f"  Row {i}: {row[:10]}")  # Show first 10 columns
        
        # Find header row - look for row with actual column names (multiple fields)
        header_row_index = -1
        
        for i, row in enumerate(all_data[:20]):  # Check first 20 rows
            # A real header row should have multiple non-empty cells with _underscore column names
            non_empty = [cell for cell in row if cell and str(cell).strip()]
            
            # Check if this looks like a header row (has multiple column-like names)
            if len(non_empty) >= 5:  # At least 5 columns
                row_lower = [str(cell).lower() for cell in row]
                # Real headers have underscores or are proper column names like "Pitcher_Name", "Parlay_ID"
                has_underscore_cols = any('_' in str(cell) for cell in row if cell)
                has_id_col = any('id' in str(cell).lower() for cell in row if cell)
                has_pitcher_name = any('pitcher_name' in str(cell).lower() for cell in row if cell)
                
                if has_underscore_cols or (has_id_col and has_pitcher_name):
                    logger.info(f"🎯 Found actual header row at index {i}: {row}")
                    header_row_index = i
                    break
        
        if header_row_index == -1:
            logger.error("❌ Could not find header row in parlay sheet")
            logger.info("🔍 Looking for rows with multiple non-empty cells...")
            for i, row in enumerate(all_data[:15]):
                non_empty = [cell for cell in row if cell and str(cell).strip()]
                if len(non_empty) >= 3:
                    logger.info(f"  Row {i} has {len(non_empty)} non-empty cells: {non_empty[:10]}")
            return []
        
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        
        logger.info(f"📋 Using headers from row {header_row_index}:")
        logger.info(f"   All columns: {headers}")
        logger.info(f"📊 Data rows available: {len(data_rows)}")
        
        # Show first 3 data rows
        logger.info("🔍 First 3 data rows:")
        for i, row in enumerate(data_rows[:3]):
            logger.info(f"  Data row {i}: {row[:10]}")
        
        # Create DataFrame
        parlay_df = pd.DataFrame(data_rows, columns=headers)
        
        logger.info(f"📊 DataFrame shape: {parlay_df.shape}")
        logger.info(f"📋 DataFrame columns: {list(parlay_df.columns)}")
        
        # Remove empty rows based on first column
        before_filter = len(parlay_df)
        parlay_df = parlay_df[parlay_df.iloc[:, 0].notna() & (parlay_df.iloc[:, 0] != '')]
        after_filter = len(parlay_df)
        
        logger.info(f"🔍 Rows after filtering empty: {after_filter} (removed {before_filter - after_filter})")
        
        if parlay_df.empty:
            logger.warning("⚠️ No parlay data found after filtering")
            return []
        
        # Show sample of actual data
        logger.info(f"📊 Sample data from first row:")
        if len(parlay_df) > 0:
            first_row = parlay_df.iloc[0]
            for col, val in first_row.items():
                if val and str(val).strip():  # Only show non-empty values
                    logger.info(f"  {col}: {val}")
        
        # Parse parlays - each row is a parlay with anchor pitcher and batters
        parlays = []
        
        for idx, row in parlay_df.iterrows():
            logger.info(f"\n🔄 Processing parlay row {idx}...")
            try:
                # Get pitcher information from columns
                pitcher_name = row.get('Pitcher_Name', '')
                pitcher_team = row.get('Pitcher_Team', '')
                pitcher_market = row.get('Pitcher_Market', '')
                pitcher_line = row.get('Pitcher_Line', '')
                pitcher_bet_type = row.get('Pitcher_Bet_Type', '')
                pitcher_ev = row.get('Pitcher_EV', '')
                
                logger.info(f"  ✅ Pitcher Name: {pitcher_name}")
                logger.info(f"  ✅ Pitcher Market: {pitcher_market}")
                logger.info(f"  ✅ Pitcher Line: {pitcher_line}")
                logger.info(f"  ✅ Pitcher Bet Type: {pitcher_bet_type}")
                logger.info(f"  ✅ Pitcher EV: {pitcher_ev}")
                
                if not pitcher_name:
                    logger.warning(f"  ⚠️ No pitcher name found in row {idx}, skipping")
                    continue
                
                # Clean pitcher market name
                pitcher_market_clean = clean_market_name(pitcher_market) if pitcher_market else ""
                
                # Collect batter legs - they're in a compressed format in Batter_1, Batter_2 columns
                batter_legs = []
                batter_num = 1
                
                logger.info(f"  🔍 Looking for batters...")
                
                while batter_num <= 10:  # Check up to 10 batters
                    batter_col = f'Batter_{batter_num}'
                    batter_data = row.get(batter_col, '')
                    
                    if not batter_data or str(batter_data).strip() == '':
                        logger.info(f"  ⏹️ No data for {batter_col}, stopping")
                        break
                    
                    logger.info(f"  ✅ Found {batter_col}: {batter_data}")
                    
                    # Parse compressed format: "Name, Market, Line, Bet_Type, EV, Odds"
                    # Example: "Gabriel Arias, batter_hits, Under 0.5, under, 0.0419216616, -115"
                    try:
                        parts = [p.strip() for p in str(batter_data).split(',')]
                        if len(parts) >= 4:
                            batter_name = parts[0]
                            batter_market_raw = parts[1]
                            batter_line = parts[2]
                            batter_bet_type = parts[3] if len(parts) > 3 else ''
                            batter_ev = parts[4] if len(parts) > 4 else ''
                            batter_odds = parts[5] if len(parts) > 5 else ''
                            
                            # Clean batter market name
                            batter_market_clean = clean_market_name(batter_market_raw)
                            
                            # Format batter info into condensed string
                            batter_info = f"{batter_name} • {batter_market_clean} {batter_line}"
                            if batter_ev:
                                try:
                                    ev_float = float(batter_ev)
                                    batter_info += f" • EV: {ev_float:.1%}"
                                except:
                                    batter_info += f" • EV: {batter_ev}"
                            if batter_odds:
                                batter_info += f" • {batter_odds}"
                            
                            logger.info(f"  ✅ Parsed batter {batter_num}: {batter_info}")
                            
                            batter_legs.append({
                                'Batter': batter_info
                            })
                        else:
                            logger.warning(f"  ⚠️ Batter data doesn't have enough parts: {batter_data}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ Error parsing batter data: {e}")
                    
                    batter_num += 1
                
                if not batter_legs:
                    logger.warning(f"  ⚠️ No batters found for parlay {idx}")
                    continue
                
                logger.info(f"  ✅ Found {len(batter_legs)} batters for this parlay")
                
                # Calculate total EV
                total_ev = 0
                try:
                    if pitcher_ev:
                        total_ev += float(pitcher_ev)
                    
                    # Add batter EVs
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
                except Exception as e:
                    logger.warning(f"  ⚠️ Error calculating total EV: {e}")
                
                # Format pitcher info
                pitcher_info = {
                    'Player': pitcher_name,
                    'Market': pitcher_market_clean,
                    'Line': pitcher_line,  # Just the line without prepending bet_type
                    'EV': f"{float(pitcher_ev):.1%}" if pitcher_ev else "",
                    'Odds': row.get('Pitcher_Odds', '') or ""  # If odds column exists
                }
                
                parlay = {
                    'id': row.get('Parlay_ID', f"PARLAY_{idx + 1:03d}"),
                    'anchor': pitcher_info,
                    'batters': batter_legs,
                    'totalEV': f"{total_ev:.1%}" if total_ev else "N/A",
                    'leg_count': 1 + len(batter_legs)
                }
                
                parlays.append(parlay)
                logger.info(f"  ✅ Successfully created parlay: {parlay['id']} with {parlay['leg_count']} legs")
                
            except Exception as e:
                logger.error(f"  ❌ Error parsing parlay row {idx}: {e}")
                import traceback
                logger.error(f"  Full traceback: {traceback.format_exc()}")
                continue
        
        logger.info(f"\n✅ Successfully parsed {len(parlays)} parlays total")
        if parlays:
            logger.info(f"📊 Sample parlay: {parlays[0]}")
        
        return parlays
        
    except Exception as e:
        logger.error(f"❌ Error reading correlation parlays: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []

def get_individual_evs():
    """Get Individual EV data - try real data first, fallback to empty if fails"""
    real_data = read_ev_results()
    
    if real_data:
        return real_data
    else:
        # Return empty list if no data available
        logger.warning("No real EV data available, showing empty state")
        return []

def get_correlation_parlays():
    """Get Correlation Parlays data"""
    real_data = read_correlation_parlays()
    
    if real_data:
        return real_data
    else:
        logger.warning("No parlay data available, showing empty state")
        return []

# Load real data
individualEVs = get_individual_evs()
parlays = get_correlation_parlays()

# Get unique markets for filtering (handle empty data case)
all_markets = list(set([ev['Market'] for ev in individualEVs if ev.get('Market')])) if individualEVs else []

# Define the app layout with clean text buttons and modern font
app.layout = html.Div([
    # Add modern font import
    html.Link(
        rel='stylesheet',
        href='https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
    ),
    
    # Header with light grey line underneath
    html.Div([
        html.Div([
            html.H1("EV Sports", style={
                'margin': '0',
                'fontSize': '24px',
                'fontWeight': '800',
                'color': '#111827',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }),
            html.Span("Last Updated: 2 hours ago", style={
                'fontSize': '14px',
                'color': '#6b7280',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            })
        ], style={
            'maxWidth': '1280px',
            'margin': '0 auto',
            'padding': '0 24px',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'width': '100%'
        })
    ], style={
        'background': 'white',
        'borderBottom': '1px solid #e5e7eb',
        'height': '64px',
        'display': 'flex',
        'alignItems': 'center'
    }),
    
    # Two stacked ribbons underneath EV Sports (top left)
    html.Div([
        html.Div([
            # Ribbon 1: League Selection (stacked)
            html.Div([
                html.Button("MLB", 
                    id="league-mlb",
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#111827',
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'padding': '8px 0',
                        'marginRight': '32px',
                        'cursor': 'pointer',
                        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }
                ),
                html.Button("NFL", 
                    id="league-nfl",
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#9ca3af',
                        'fontSize': '14px',
                        'fontWeight': '400',
                        'padding': '8px 0',
                        'marginRight': '32px',
                        'cursor': 'pointer',
                        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }
                ),
                html.Button("NBA",
                    id="league-nba",
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#9ca3af',
                        'fontSize': '14px',
                        'fontWeight': '400',
                        'padding': '8px 0',
                        'cursor': 'pointer',
                        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
            
            # Ribbon 2: View Selection (stacked underneath)
            html.Div([
                html.Button("Individual EVs",
                    id="view-individual",
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#111827',
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'padding': '8px 0',
                        'marginRight': '32px',
                        'cursor': 'pointer',
                        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }
                ),
                html.Button("Correlation Parlays",
                    id="view-parlays",
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#9ca3af',
                        'fontSize': '14px',
                        'fontWeight': '400',
                        'padding': '8px 0',
                        'cursor': 'pointer',
                        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], style={
            'maxWidth': '1280px',
            'margin': '0 auto',
            'padding': '16px 24px'
        })
    ], style={
        'background': 'white',
        'borderBottom': '1px solid #f3f4f6'
    }),
    
    # Main Content Area - Always show Individual EVs
    html.Div([
        html.Div(id='main-content-fixed')
    ], style={
        'maxWidth': '1280px',
        'margin': '0 auto',
        'padding': '48px 24px',
        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    })
], style={
    'backgroundColor': 'white',
    'minHeight': '100vh',
    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
})

# Main callback to render content
@app.callback(
    [Output('main-content-fixed', 'children'),
     Output('view-individual', 'style'),
     Output('view-parlays', 'style')],
    [Input('view-individual', 'n_clicks'),
     Input('view-parlays', 'n_clicks')]
)
def render_main_content(individual_clicks, parlays_clicks):
    ctx = dash.callback_context
    
    # Determine which view button was clicked
    current_view = 'individual'
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'view-parlays':
            current_view = 'parlays'
    
    # Define button styles
    active_style = {
        'background': 'none',
        'border': 'none',
        'color': '#111827',
        'fontSize': '14px',
        'fontWeight': '600',
        'padding': '8px 0',
        'marginRight': '32px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }
    
    inactive_style = {
        'background': 'none',
        'border': 'none',
        'color': '#9ca3af',
        'fontSize': '14px',
        'fontWeight': '400',
        'padding': '8px 0',
        'marginRight': '32px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
    }
    
    # Render content based on current view
    if current_view == 'individual':
        content = render_individual_evs()
        individual_style = active_style
        parlays_style = inactive_style
    else:
        content = render_parlays()
        individual_style = inactive_style
        parlays_style = active_style
    
    return content, individual_style, parlays_style

def render_individual_evs():
    if not individualEVs:
        # Show empty state if no data
        return html.Div([
            html.Div([
                html.P("No EV opportunities found.", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }),
                html.P("Check the logs for Google Sheets connection details.", style={
                    'fontSize': '14px',
                    'color': '#9ca3af',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                })
            ], style={
                'textAlign': 'center',
                'padding': '48px 24px'
            })
        ])
    
    return html.Div([
        # Filter buttons (centered)
        html.Div([
            html.Button(
                "All",
                id="filter-all",
                n_clicks=0,
                style={
                    'background': 'none',
                    'border': 'none',
                    'color': '#111827',
                    'fontSize': '14px',
                    'fontWeight': '600',
                    'padding': '6px 16px',
                    'marginRight': '16px',
                    'cursor': 'pointer',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }
            )
        ] + [
            html.Button(
                market,
                id=f"filter-{market.replace(' ', '-').lower()}",
                n_clicks=0,
                style={
                    'background': 'none',
                    'border': 'none',
                    'color': '#9ca3af',
                    'fontSize': '14px',
                    'fontWeight': '400',
                    'padding': '6px 16px',
                    'marginRight': '16px',
                    'cursor': 'pointer',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }
            ) for market in all_markets
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'center',
            'marginBottom': '24px'
        }) if all_markets else html.Div(),
        
        # Data table
        html.Div(id='evs-table')
    ])

def render_parlays():
    """Render correlation parlays view"""
    if not parlays:
        return html.Div([
            html.Div([
                html.P("No correlation parlays found.", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }),
                html.P("Check the logs for Google Sheets connection details.", style={
                    'fontSize': '14px',
                    'color': '#9ca3af',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                })
            ], style={
                'textAlign': 'center',
                'padding': '48px 24px'
            })
        ])
    
    return html.Div([
        # Parlay cards
        html.Div([
            render_parlay_card(parlay) for parlay in parlays
        ])
    ])

def render_parlay_card(parlay):
    """Render a single parlay card with anchor pitcher and batters"""
    return html.Div([
        # Parlay header with ID and total EV
        html.Div([
            html.Span(f"{parlay['id']} • {parlay['leg_count']} Legs", style={
                'fontWeight': '500',
                'color': '#6b7280'
            }),
            html.Span(" • Total EV: ", style={'color': '#6b7280'}),
            html.Span(parlay['totalEV'], style={
                'color': '#059669',
                'fontWeight': '600'
            })
        ], style={
            'background': '#f9fafb',
            'padding': '12px 24px',
            'borderBottom': '1px solid #e5e7eb',
            'fontSize': '12px',
            'textTransform': 'uppercase',
            'letterSpacing': '0.5px',
            'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }),
        
        # Anchor Pitcher section
        html.Div([
            html.Div([
                html.Span(parlay['anchor']['Player'], style={
                    'fontWeight': '700',
                    'fontSize': '15px',
                    'color': '#111827'
                }),
                html.Span(f" • {parlay['anchor']['Market']} {parlay['anchor']['Line']}", style={
                    'fontSize': '14px',
                    'fontWeight': '700',
                    'color': '#374151'
                }),
                html.Span(f" • EV: {parlay['anchor']['EV']}", style={
                    'fontSize': '14px',
                    'color': '#111827',
                    'fontWeight': '700',
                    'marginLeft': '8px'
                }),
                html.Span(f" • {parlay['anchor']['Odds']}", style={
                    'fontSize': '14px',
                    'fontWeight': '700',
                    'color': '#6b7280',
                    'marginLeft': '8px'
                }) if parlay['anchor']['Odds'] else None
            ], style={
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                'padding': '12px 0',
                'borderBottom': '1px solid #e5e7eb'
            })
        ], style={'padding': '16px 24px'}),
        
        # Batters section
        html.Div([
            html.Div([
                html.Div([
                    html.Div(batter['Batter'], style={
                        'fontSize': '14px',
                        'color': '#374151',
                        'padding': '10px 0',
                        'borderBottom': '1px solid #f3f4f6' if i < len(parlay['batters']) - 1 else 'none',
                        'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    })
                ]) for i, batter in enumerate(parlay['batters'])
            ])
        ], style={'padding': '0 24px 24px 24px'})
        
    ], style={
        'background': 'white',
        'border': '1px solid #e5e7eb',
        'borderRadius': '8px',
        'overflow': 'hidden',
        'marginBottom': '24px',
        'boxShadow': '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    })
# Filtering callback for Individual EVs (only if we have markets)
if all_markets:
    @app.callback(
        [Output('evs-table', 'children')] +
        [Output(f"filter-{market.replace(' ', '-').lower()}", 'style') for market in all_markets] +
        [Output('filter-all', 'style')],
        [Input('filter-all', 'n_clicks')] +
        [Input(f"filter-{market.replace(' ', '-').lower()}", 'n_clicks') for market in all_markets]
    )
    def update_evs_table(*args):
        ctx = dash.callback_context
        
        # Determine which button was clicked
        if not ctx.triggered:
            selected_filter = 'All'
        else:
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'filter-all':
                selected_filter = 'All'
            else:
                # Extract market name from button ID
                selected_filter = next((m for m in all_markets if m.replace(' ', '-').lower() == button_id.replace('filter-', '')), 'All')
        
        # Filter data
        if selected_filter == 'All':
            filtered_data = individualEVs
        else:
            filtered_data = [ev for ev in individualEVs if ev['Market'] == selected_filter]
        
        # Create table
        table = dash_table.DataTable(
            data=filtered_data,
            columns=[
                {'name': 'Player', 'id': 'Player'},
                {'name': 'Market', 'id': 'Market'},
                {'name': 'Line', 'id': 'Line'},
                {'name': 'EV %', 'id': 'EV %'}
            ],
            style_header={
                'backgroundColor': '#f9fafb',
                'color': '#6b7280',
                'fontWeight': '500',
                'textTransform': 'uppercase',
                'fontSize': '12px',
                'letterSpacing': '0.5px',
                'padding': '16px 24px',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '16px 24px',
                'fontSize': '14px',
                'border': 'none',
                'borderBottom': '1px solid #e5e7eb',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            },
            style_data={
                'backgroundColor': 'white',
                'color': '#111827'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'Player'},
                    'fontWeight': '500'
                },
                {
                    'if': {'column_id': 'EV %'},
                    'color': '#059669',
                    'fontWeight': '600'
                }
            ],
            style_table={
                'background': 'white',
                'border': '1px solid #e5e7eb',
                'borderRadius': '4px',
                'overflow': 'hidden'
            }
        )
        
        # Update button styles
        active_style = {
            'background': 'none',
            'border': 'none',
            'color': '#111827',
            'fontSize': '14px',
            'fontWeight': '600',
            'padding': '6px 16px',
            'marginRight': '16px',
            'cursor': 'pointer',
            'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }
        
        inactive_style = {
            'background': 'none',
            'border': 'none',
            'color': '#9ca3af',
            'fontSize': '14px',
            'fontWeight': '400',
            'padding': '6px 16px',
            'marginRight': '16px',
            'cursor': 'pointer',
            'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }
        
        # Create styles list
        market_styles = []
        for market in all_markets:
            if market == selected_filter:
                market_styles.append(active_style)
            else:
                market_styles.append(inactive_style)
        
        all_style = active_style if selected_filter == 'All' else inactive_style
        
        return (
            table,
            *market_styles,
            all_style
        )
else:
    # Simple callback for when no markets available (no data case)
    @app.callback(
        Output('evs-table', 'children'),
        Input('view-individual', 'n_clicks')
    )
    def show_empty_table(n_clicks):
        return html.Div([
            html.P("No data available for filtering.", style={
                'fontSize': '14px',
                'color': '#9ca3af',
                'textAlign': 'center',
                'padding': '24px',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            })
        ])

# For deployment
if __name__ == '__main__':
    # Use PORT environment variable for deployment
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
