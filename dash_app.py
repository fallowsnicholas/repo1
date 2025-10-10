# dash_app.py - Modern, clean UI with sticky elements - FIXED
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

# Add custom CSS for proper sticky behavior - CRITICAL FIX
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
            /* Reset and base styles */
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
            
            /* Fix for proper stacking */
            #react-entry-point {
                position: relative;
                min-height: 100vh;
            }
            
            /* Ensure all fixed headers have solid backgrounds */
            [style*="position: fixed"] {
                background: white !important;
            }
            
            /* Remove button outlines */
            button {
                outline: none !important;
                -webkit-appearance: none !important;
                -moz-appearance: none !important;
            }
            
            /* Ensure table rows are white */
            .table-row {
                background-color: white !important;
            }
            
            .table-row:hover {
                background-color: #f9fafb !important;
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

def connect_to_sheets():
    """Connect to Google Sheets using service account"""
    try:
        print("Connecting to Google Sheets...")
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
        credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(credentials)
        logger.info("✅ Successfully connected to Google Sheets")
        print("✅ Google Sheets connection successful")
        return client
    except KeyError:
        logger.error("❌ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set")
        print("❌ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable not set", file=sys.stderr)
        return None
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        print(f"❌ Google Sheets connection failed: {e}", file=sys.stderr)
        return None

def read_ev_results(sport='MLB'):
    """Read Individual EV data from Google Sheets"""
    try:
        client = connect_to_sheets()
        if not client:
            return []
        
        spreadsheet_name = f"{sport}_Splash_Data"
        spreadsheet = client.open(spreadsheet_name)
        ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
        
        all_data = ev_worksheet.get_all_values()
        if not all_data:
            return []
        
        # Find header row
        header_row_index = -1
        possible_headers = ['Player', 'Name', 'Market', 'Line', 'EV', 'Splash_EV_Percentage']
        
        for i, row in enumerate(all_data):
            if row and any(header in row for header in possible_headers):
                header_row_index = i
                break
        
        if header_row_index == -1:
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
            return []
        
        # Remove empty rows
        ev_df = ev_df[ev_df[player_col].notna() & (ev_df[player_col] != '')]
        
        if ev_df.empty:
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
            
            raw_market = row.get('Market', '')
            cleaned_market = clean_market_name(raw_market)
            
            individual_evs.append({
                'Player': row[player_col],
                'Market': cleaned_market,
                'Line': row.get('Line', ''),
                'EV %': ev_percent
            })
        
        return individual_evs
        
    except Exception as e:
        logger.error(f"Error reading EV results: {e}")
        return []

def read_correlation_parlays(sport='MLB'):
    """Read Correlation Parlays data from Google Sheets"""
    if sport != 'MLB':
        return []
    
    try:
        client = connect_to_sheets()
        if not client:
            return []
        
        spreadsheet = client.open(f"{sport}_Splash_Data")
        parlay_worksheet = spreadsheet.worksheet("CORRELATION_PARLAYS")
        all_data = parlay_worksheet.get_all_values()
        
        if not all_data:
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
            return []
        
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        parlay_df = pd.DataFrame(data_rows, columns=headers)
        parlay_df = parlay_df[parlay_df.iloc[:, 0].notna() & (parlay_df.iloc[:, 0] != '')]
        
        if parlay_df.empty:
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
        
        return parlays
        
    except Exception as e:
        logger.error(f"Error reading correlation parlays: {e}")
        return []

# App Layout
print("Step 3: Building app layout...")
try:
    app.layout = html.Div([
        # Google Font
        html.Link(
            rel='stylesheet',
            href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
        ),
        
        # Store for current sport and view
        dcc.Store(id='current-sport', data='MLB'),
        dcc.Store(id='current-view', data='individual'),
        
        # 1. TITLE - STICKY
        html.Div([
            html.H1("EV SPORTS", style={
                'margin': '0',
                'fontSize': '24px',
                'fontWeight': '700',
                'color': '#000000',
                'fontFamily': 'Inter, sans-serif',
                'letterSpacing': '-0.5px'
            })
        ], style={
            'padding': '20px 40px',
            'backgroundColor': '#ffffff',
            'borderBottom': '1px solid #e5e7eb',
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'right': '0',
            'zIndex': '1000'
        }),
        
        # Spacer for title
        html.Div(style={'height': '64px'}),
        
        # 2. LEAGUE RIBBON - STICKY
        html.Div([
            html.Button("MLB", id="league-mlb", n_clicks=0, style={
                'background': 'none',
                'border': 'none',
                'color': '#000000',
                'fontSize': '14px',
                'fontWeight': '600',
                'padding': '12px 20px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, sans-serif'
            }),
            html.Button("NFL", id="league-nfl", n_clicks=0, style={
                'background': 'none',
                'border': 'none',
                'color': '#9ca3af',
                'fontSize': '14px',
                'fontWeight': '400',
                'padding': '12px 20px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, sans-serif'
            })
        ], style={
            'padding': '0 40px',
            'backgroundColor': '#ffffff',
            'borderBottom': '1px solid #e5e7eb',
            'display': 'flex',
            'gap': '8px',
            'position': 'fixed',
            'top': '64px',
            'left': '0',
            'right': '0',
            'zIndex': '999'
        }),
        
        # Spacer for league ribbon
        html.Div(style={'height': '48px'}),
        
        # 3. VIEW RIBBON - STICKY
        html.Div([
            html.Button("Individual EVs", id="view-individual", n_clicks=0, style={
                'background': 'none',
                'border': 'none',
                'color': '#000000',
                'fontSize': '14px',
                'fontWeight': '600',
                'padding': '12px 20px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, sans-serif'
            }),
            html.Button("Correlation Parlays", id="view-parlays", n_clicks=0, style={
                'background': 'none',
                'border': 'none',
                'color': '#9ca3af',
                'fontSize': '14px',
                'fontWeight': '400',
                'padding': '12px 20px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, sans-serif'
            })
        ], style={
            'padding': '0 40px',
            'backgroundColor': '#ffffff',
            'borderBottom': '1px solid #e5e7eb',
            'display': 'flex',
            'gap': '8px',
            'position': 'fixed',
            'top': '112px',
            'left': '0',
            'right': '0',
            'zIndex': '998'
        }),
        
        # Spacer for view ribbon
        html.Div(style={'height': '48px'}),
        
        # Main content area - CRITICAL FIX: added position relative and overflow hidden
        html.Div(id='main-content', style={
            'minHeight': 'calc(100vh - 160px)',
            'backgroundColor': '#ffffff',
            'position': 'relative',
            'overflow': 'hidden'
        })
        
    ], style={
        'backgroundColor': '#ffffff',
        'minHeight': '100vh',
        'fontFamily': 'Inter, sans-serif'
    })
    
    print("✅ App layout created successfully")
    
except Exception as e:
    print(f"❌ ERROR creating layout: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)

# Callbacks
print("Step 4: Registering callbacks...")

# Sport selection callback
@app.callback(
    [Output('current-sport', 'data'),
     Output('league-mlb', 'style'),
     Output('league-nfl', 'style')],
    [Input('league-mlb', 'n_clicks'),
     Input('league-nfl', 'n_clicks')]
)
def update_sport(mlb_clicks, nfl_clicks):
    ctx = dash.callback_context
    
    active_style = {
        'background': 'none',
        'border': 'none',
        'color': '#000000',
        'fontSize': '14px',
        'fontWeight': '600',
        'padding': '12px 20px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
    
    inactive_style = {
        'background': 'none',
        'border': 'none',
        'color': '#9ca3af',
        'fontSize': '14px',
        'fontWeight': '400',
        'padding': '12px 20px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
    
    if not ctx.triggered:
        return 'MLB', active_style, inactive_style
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'league-nfl':
        return 'NFL', inactive_style, active_style
    else:
        return 'MLB', active_style, inactive_style

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
    
    active_style = {
        'background': 'none',
        'border': 'none',
        'color': '#000000',
        'fontSize': '14px',
        'fontWeight': '600',
        'padding': '12px 20px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
    
    inactive_style = {
        'background': 'none',
        'border': 'none',
        'color': '#9ca3af',
        'fontSize': '14px',
        'fontWeight': '400',
        'padding': '12px 20px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
    
    if not ctx.triggered:
        return 'individual', active_style, inactive_style
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'view-parlays':
        return 'parlays', inactive_style, active_style
    else:
        return 'individual', active_style, inactive_style

# Main content callback
@app.callback(
    Output('main-content', 'children'),
    [Input('current-sport', 'data'),
     Input('current-view', 'data')]
)
def render_main_content(sport, view):
    if view == 'individual':
        return render_individual_evs(sport)
    else:
        return render_parlays(sport)

def render_individual_evs(sport):
    """Render individual EVs with market filters, banner, and table"""
    data = read_ev_results(sport)
    
    if not data:
        return html.Div([
            html.P(f"No {sport} EV opportunities found.", style={
                'textAlign': 'center',
                'padding': '60px 20px',
                'color': '#6b7280',
                'fontSize': '16px',
                'fontFamily': 'Inter, sans-serif'
            })
        ])
    
    # Get unique markets
    all_markets = sorted(list(set([ev['Market'] for ev in data if ev.get('Market')])))
    
    # MARKET FILTERS - STICKY
    filter_section = html.Div([
        html.Div([
            html.Button("All", id={'type': 'market-filter', 'index': 0}, style={
                'background': 'none',
                'border': 'none',
                'color': '#000000',
                'fontSize': '13px',
                'fontWeight': '600',
                'padding': '8px 16px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, sans-serif'
            })
        ] + [
            html.Button(market, id={'type': 'market-filter', 'index': i+1}, style={
                'background': 'none',
                'border': 'none',
                'color': '#9ca3af',
                'fontSize': '13px',
                'fontWeight': '400',
                'padding': '8px 16px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, sans-serif'
            }) for i, market in enumerate(all_markets)
        ], style={
            'display': 'flex',
            'justifyContent': 'center',
            'flexWrap': 'wrap',
            'gap': '4px',
            'padding': '16px 40px'
        })
    ], style={
        'backgroundColor': '#ffffff',
        'borderBottom': '1px solid #e5e7eb',
        'position': 'fixed',
        'top': '160px',
        'left': '0',
        'right': '0',
        'zIndex': '997'
    })
    
    # Spacer for filters
    filter_spacer = html.Div(style={'height': '56px'})
    
    # Space between market buttons and banner
    banner_top_spacer = html.Div(style={'height': '20px'})
    
    # TABLE WRAPPER - Contains both banner and table to share the same width
    table_wrapper = html.Div([
        # COLUMN HEADER BANNER
        html.Div([
            html.Div('NAME', style={
                'flex': '1',
                'padding': '12px 16px',
                'paddingLeft': '17px',  # Compensates for 1px border
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            }),
            html.Div('MARKET', style={
                'flex': '1',
                'padding': '12px 16px',
                'paddingLeft': '0px',  # ADD THIS
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            }),
            html.Div('LINE', style={
                'flex': '0 0 120px',
                'padding': '12px 16px',
                'paddingLeft': '0px',  # ADD THIS
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            }),
            html.Div('EV', style={
                'flex': '0 0 100px',
                'padding': '12px 16px',
                'paddingLeft': '0px',  # ADD THIS
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            })
        ], style={
            'display': 'flex',
            'border': '1px solid #e5e7eb',
            'borderBottom': 'none',
            'borderRadius': '8px 8px 0 0',
            'backgroundColor': '#f3f4f6'
        }),
        
        # TABLE CONTAINER - SCROLLABLE
        html.Div(
            id='evs-table-container',
            children=[create_evs_table(data)],
            style={
                'height': 'calc(100vh - 350px)',
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
    
    return html.Div([filter_section, filter_spacer, banner_top_spacer, header_banner, header_spacer, table])

# Market filter callback
@app.callback(
    [Output('evs-table-container', 'children'),
     Output({'type': 'market-filter', 'index': ALL}, 'style')],
    [Input({'type': 'market-filter', 'index': ALL}, 'n_clicks')],
    [State('current-sport', 'data')],
    prevent_initial_call=True
)
def update_market_filter(n_clicks, sport):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return dash.no_update, dash.no_update
    
    triggered_id = ctx.triggered[0]['prop_id']
    button_data = json.loads(triggered_id.split('.')[0])
    button_index = button_data['index']
    
    data = read_ev_results(sport)
    
    if not data:
        return html.Div([
            html.P("No data available.", style={
                'textAlign': 'center',
                'padding': '40px',
                'color': '#9ca3af',
                'fontFamily': 'Inter, sans-serif'
            })
        ]), dash.no_update
    
    all_markets = sorted(list(set([ev['Market'] for ev in data if ev.get('Market')])))
    
    # Filter data
    if button_index == 0:
        filtered_data = data
    else:
        selected_market = all_markets[button_index - 1]
        filtered_data = [ev for ev in data if ev['Market'] == selected_market]
    
    # Update button styles
    active_style = {
        'background': 'none',
        'border': 'none',
        'color': '#000000',
        'fontSize': '13px',
        'fontWeight': '600',
        'padding': '8px 16px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
    
    inactive_style = {
        'background': 'none',
        'border': 'none',
        'color': '#9ca3af',
        'fontSize': '13px',
        'fontWeight': '400',
        'padding': '8px 16px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
    }
    
    button_styles = []
    total_buttons = len(all_markets) + 1
    
    for i in range(total_buttons):
        if i == button_index:
            button_styles.append(active_style)
        else:
            button_styles.append(inactive_style)
    
    return create_evs_table(filtered_data), button_styles

def create_evs_table(data):
    """Create table WITHOUT any header - just player data rows"""
    if not data:
        return html.Div([
            html.P("No data matches this filter.", style={
                'textAlign': 'center',
                'padding': '40px',
                'color': '#9ca3af',
                'fontFamily': 'Inter, sans-serif'
            })
        ])
    
    return html.Div([
        # Table rows ONLY - NO HEADER
        html.Div([
            html.Div([
                html.Div(row['Player'], style={
                    'flex': '1',
                    'padding': '14px 16px',
                    'fontWeight': '500',
                    'color': '#111827',
                    'fontSize': '14px'
                }),
                html.Div(row['Market'], style={
                    'flex': '1',
                    'padding': '14px 16px',
                    'color': '#374151',
                    'fontSize': '14px'
                }),
                html.Div(row['Line'], style={
                    'flex': '0 0 120px',
                    'padding': '14px 16px',
                    'color': '#374151',
                    'fontSize': '14px'
                }),
                html.Div(row['EV %'], style={
                    'flex': '0 0 100px',
                    'padding': '14px 16px',
                    'fontWeight': '600',
                    'color': '#059669',
                    'fontSize': '14px'
                })
            ], className='table-row', style={
                'display': 'flex',
                'borderBottom': '1px solid #f3f4f6' if row != data[-1] else 'none',
                'backgroundColor': '#ffffff'
            })
            for row in data
        ], style={'fontFamily': 'Inter, sans-serif'})
    ], style={
        'border': '1px solid #e5e7eb',
        'borderRadius': '0 0 8px 8px',
        'borderTop': 'none',
        'overflow': 'hidden',
        'backgroundColor': '#ffffff'
    })

def render_parlays(sport):
    """Render correlation parlays"""
    if sport != 'MLB':
        return html.Div([
            html.P(f"{sport} correlation parlays coming soon!", style={
                'textAlign': 'center',
                'padding': '60px 20px',
                'color': '#6b7280',
                'fontSize': '16px',
                'fontFamily': 'Inter, sans-serif'
            })
        ])
    
    parlays = read_correlation_parlays(sport)
    
    if not parlays:
        return html.Div([
            html.P(f"No {sport} correlation parlays found.", style={
                'textAlign': 'center',
                'padding': '60px 20px',
                'color': '#6b7280',
                'fontSize': '16px',
                'fontFamily': 'Inter, sans-serif'
            })
        ])
    
    return html.Div([
        html.Div([
            render_parlay_card(parlay) for parlay in parlays
        ], style={
            'maxWidth': '1200px',
            'margin': '0 auto',
            'padding': '20px 40px 60px 40px',
            'height': 'calc(100vh - 220px)',
            'overflowY': 'auto',
            'position': 'relative'
        })
    ])

def render_parlay_card(parlay):
    """Render a single parlay card"""
    return html.Div([
        # Parlay header
        html.Div([
            html.Span(f"{parlay['id']} • {parlay['leg_count']} Legs • Total EV: ", style={
                'color': '#6b7280',
                'fontSize': '12px',
                'fontWeight': '500'
            }),
            html.Span(parlay['totalEV'], style={
                'color': '#059669',
                'fontSize': '12px',
                'fontWeight': '600'
            })
        ], style={
            'backgroundColor': '#f9fafb',
            'padding': '12px 20px',
            'borderBottom': '1px solid #e5e7eb',
            'fontFamily': 'Inter, sans-serif'
        }),
        
        # Anchor (pitcher)
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
                    'color': '#059669',
                    'fontWeight': '600',
                    'marginLeft': '8px'
                }) if parlay['anchor']['EV'] else None
            ])
        ], style={
            'padding': '16px 20px',
            'borderBottom': '1px solid #e5e7eb',
            'fontFamily': 'Inter, sans-serif'
        }),
        
        # Batters
        html.Div([
            html.Div([
                html.Div(batter['Batter'], style={
                    'fontSize': '14px',
                    'color': '#374151',
                    'padding': '10px 0',
                    'borderBottom': '1px solid #f3f4f6' if i < len(parlay['batters']) - 1 else 'none'
                })
                for i, batter in enumerate(parlay['batters'])
            ])
        ], style={
            'padding': '16px 20px',
            'fontFamily': 'Inter, sans-serif'
        })
        
    ], style={
        'backgroundColor': '#ffffff',
        'border': '1px solid #e5e7eb',
        'borderRadius': '8px',
        'overflow': 'hidden',
        'marginBottom': '20px'
    })

print("✅ All callbacks registered")
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
