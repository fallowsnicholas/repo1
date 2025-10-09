# dash_app.py - Fixed version with comprehensive error logging
import sys
import traceback

print("=" * 60)
print("STARTING DASH APP")
print("=" * 60)

try:
    print("Step 1: Importing libraries...")
    import dash
    from dash import dcc, html, Input, Output, State, dash_table
    import pandas as pd
    import os
    import gspread
    from google.oauth2.service_account import Credentials
    import json
    import logging
    print("✅ All imports successful")

    # Initialize the Dash app with server configuration
    print("Step 2: Initializing Dash app...")
    app = dash.Dash(__name__)
    server = app.server  # Expose server for deployment
    print("✅ Dash app initialized")

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    print("✅ Logging configured")

except Exception as e:
    print(f"❌ FATAL ERROR DURING STARTUP: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    sys.exit(1)

def clean_market_name(market):
    """Clean market name by removing pitcher/batter/player prefix and formatting"""
    if not market:
        return market
    
    # Remove common prefixes (case insensitive)
    cleaned = market
    prefixes = ['pitcher_', 'batter_', 'player_', 'player_pass_', 'player_rush_', 'player_reception_']
    for prefix in prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    
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

def read_ev_results(sport='MLB'):
    """Read Individual EV data from Google Sheets EV_RESULTS for specified sport"""
    try:
        client = connect_to_sheets()
        if not client:
            logger.error("Failed to get Google Sheets client")
            return []
        
        spreadsheet_name = f"{sport}_Splash_Data"
        
        logger.info(f"📊 Attempting to open {spreadsheet_name} spreadsheet...")
        spreadsheet = client.open(spreadsheet_name)
        logger.info("✅ Successfully opened spreadsheet")
        
        logger.info("📋 Attempting to access EV_RESULTS worksheet...")
        ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
        logger.info("✅ Successfully accessed EV_RESULTS worksheet")
        
        all_data = ev_worksheet.get_all_values()
        
        if not all_data:
            logger.warning("EV_RESULTS sheet is empty")
            return []
        
        # Find header row (skip metadata)
        header_row_index = -1
        possible_headers = ['Player', 'Name', 'Market', 'Line', 'EV', 'Splash_EV_Percentage']
        
        for i, row in enumerate(all_data):
            if row and any(header in row for header in possible_headers):
                logger.info(f"Found potential header row at index {i}: {row}")
                header_row_index = i
                break
        
        if header_row_index == -1:
            logger.error("Could not find header row in EV_RESULTS")
            return []
        
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        
        ev_df = pd.DataFrame(data_rows, columns=headers)
        
        # Find Player column
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
        
        # Convert to format expected by dash table
        individual_evs = []
        ev_col = None
        
        # Find EV column
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
        
        logger.info(f"Successfully converted {len(individual_evs)} Individual EV opportunities for {sport}")
        return individual_evs
        
    except Exception as e:
        logger.error(f"Error reading EV results for {sport}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return []

def read_correlation_parlays(sport='MLB'):
    """Read Correlation Parlays data from Google Sheets (MLB only for now)"""
    if sport != 'MLB':
        logger.info(f"Correlation parlays not yet implemented for {sport}")
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
                            batter_odds = parts[5] if len(parts) > 5 else ''
                            
                            batter_market_clean = clean_market_name(batter_market_raw)
                            
                            batter_info = f"{batter_name} • {batter_market_clean} {batter_line}"
                            if batter_ev:
                                try:
                                    ev_float = float(batter_ev)
                                    batter_info += f" • EV: {ev_float:.1%}"
                                except:
                                    batter_info += f" • EV: {batter_ev}"
                            if batter_odds:
                                batter_info += f" • {batter_odds}"
                            
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
                    'EV': f"{float(row.get('Pitcher_EV', 0)):.1%}" if row.get('Pitcher_EV') else "",
                    'Odds': row.get('Pitcher_Odds', '') or ""
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

# Define the app layout
app.layout = html.Div([
    # Add modern font import
    html.Link(
        rel='stylesheet',
        href='https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap'
    ),
    
    # Store for current sport selection
    dcc.Store(id='current-sport', data='MLB'),
    
    # Header (FIXED)
    html.Div([
        html.Div([
            html.H1("EV Sports", style={
                'margin': '0',
                'fontSize': '24px',
                'fontWeight': '800',
                'color': '#111827',
                'fontFamily': 'Inter, sans-serif'
            }),
            html.Span("Last Updated: 2 hours ago", style={
                'fontSize': '14px',
                'color': '#6b7280',
                'fontFamily': 'Inter, sans-serif'
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
        'alignItems': 'center',
        'position': 'fixed',
        'top': '0',
        'left': '0',
        'right': '0',
        'width': '100%',
        'zIndex': '1000'
    }),
    
    # Two stacked ribbons (FIXED)
    html.Div([
        html.Div([
            # Ribbon 1: League Selection
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
                        'fontFamily': 'Inter, sans-serif'
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
                        'fontFamily': 'Inter, sans-serif'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '8px'}),
            
            # Ribbon 2: View Selection
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
                        'fontFamily': 'Inter, sans-serif'
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
                        'fontFamily': 'Inter, sans-serif'
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
        'borderBottom': '1px solid #f3f4f6',
        'position': 'fixed',
        'top': '64px',
        'left': '0',
        'right': '0',
        'width': '100%',
        'zIndex': '999'
    }),

    # Spacer for fixed headers
    html.Div(style={'height': '156px'}),
    
    # Main Content Area
    html.Div([
        html.Div(id='main-content-fixed')
    ], style={
        'maxWidth': '1280px',
        'margin': '0 auto',
        'padding': '24px 24px 48px 24px',
        'fontFamily': 'Inter, sans-serif'
    }),
    
    # Add hover effect CSS
    html.Style('''
        .table-row:hover {
            background-color: #f9fafb !important;
        }
    ''')
], style={
    'backgroundColor': 'white',
    'minHeight': '100vh',
    'fontFamily': 'Inter, sans-serif'
})

# Callback for sport selection
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
        'color': '#111827',
        'fontSize': '14px',
        'fontWeight': '600',
        'padding': '8px 0',
        'marginRight': '32px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
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
        'fontFamily': 'Inter, sans-serif'
    }
    
    if not ctx.triggered:
        return 'MLB', active_style, inactive_style
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'league-nfl':
        return 'NFL', inactive_style, active_style
    else:
        return 'MLB', active_style, inactive_style

# Main callback to render content
@app.callback(
    [Output('main-content-fixed', 'children'),
     Output('view-individual', 'style'),
     Output('view-parlays', 'style')],
    [Input('view-individual', 'n_clicks'),
     Input('view-parlays', 'n_clicks'),
     Input('current-sport', 'data')]
)
def render_main_content(individual_clicks, parlays_clicks, current_sport):
    ctx = dash.callback_context
    
    # Determine which view
    current_view = 'individual'
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'view-parlays':
            current_view = 'parlays'
    
    # Button styles
    active_style = {
        'background': 'none',
        'border': 'none',
        'color': '#111827',
        'fontSize': '14px',
        'fontWeight': '600',
        'padding': '8px 0',
        'marginRight': '32px',
        'cursor': 'pointer',
        'fontFamily': 'Inter, sans-serif'
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
        'fontFamily': 'Inter, sans-serif'
    }
    
    # Render content based on view and sport
    if current_view == 'individual':
        content = render_individual_evs(current_sport)
        individual_style = active_style
        parlays_style = inactive_style
    else:
        content = render_parlays(current_sport)
        individual_style = inactive_style
        parlays_style = active_style
    
    return content, individual_style, parlays_style

def render_individual_evs(sport):
    """Render individual EVs for the selected sport - FIXED VERSION"""
    individualEVs = read_ev_results(sport)
    
    if not individualEVs:
        return html.Div([
            html.Div([
                html.P(f"No {sport} EV opportunities found.", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, sans-serif'
                }),
                html.P("Run the pipeline to generate data.", style={
                    'fontSize': '14px',
                    'color': '#9ca3af',
                    'fontFamily': 'Inter, sans-serif'
                })
            ], style={
                'textAlign': 'center',
                'padding': '48px 24px'
            })
        ])
    
    # Get unique markets for filtering
    all_markets = sorted(list(set([ev['Market'] for ev in individualEVs if ev.get('Market')])))
    
    return html.Div([
        # Filter buttons (FIXED - truly sticky with centered content)
        html.Div([
            html.Div([
                html.Button(
                    "All",
                    id={'type': 'market-filter-btn', 'index': 'All', 'sport': sport},
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#111827',
                        'fontSize': '14px',
                        'fontWeight': '600',
                        'padding': '8px 16px',
                        'marginRight': '12px',
                        'cursor': 'pointer',
                        'borderRadius': '6px',
                        'transition': 'all 0.2s',
                        'fontFamily': 'Inter, sans-serif'
                    }
                )
            ] + [
                html.Button(
                    market,
                    id={'type': 'market-filter-btn', 'index': market, 'sport': sport},
                    n_clicks=0,
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#6b7280',
                        'fontSize': '14px',
                        'fontWeight': '400',
                        'padding': '8px 16px',
                        'marginRight': '12px',
                        'cursor': 'pointer',
                        'borderRadius': '6px',
                        'transition': 'all 0.2s',
                        'fontFamily': 'Inter, sans-serif'
                    }
                ) for market in all_markets
            ], style={
                'display': 'flex',
                'alignItems': 'center',
                'justifyContent': 'center',  # CENTERED
                'flexWrap': 'wrap',
                'gap': '4px',
                'maxWidth': '1280px',
                'margin': '0 auto',
                'padding': '16px 24px'
            })
        ], style={
            'background': 'white',
            'borderBottom': '1px solid #f3f4f6',
            'position': 'sticky',  # Changed to sticky
            'top': '156px',  # Below the two ribbons
            'left': '0',
            'right': '0',
            'zIndex': '998',
            'overflowX': 'auto'
        }),
        
        # Table container with data
        html.Div([
            html.Div(
                id=f'evs-table-container-{sport}',
                children=[create_evs_table(individualEVs, 'All')]
            )
        ], style={
            'marginTop': '0'
        })
    ])

def create_evs_table(data, selected_filter):
    """Create the EVs table with sticky header - FIXED VERSION"""
    # Filter data
    if selected_filter != 'All':
        filtered_data = [ev for ev in data if ev['Market'] == selected_filter]
    else:
        filtered_data = data
    
    # Create custom table structure with sticky header
    return html.Div([
        # Table header (sticky)
        html.Div([
            html.Div([
                html.Div('Player', style={
                    'flex': '1',
                    'minWidth': '200px',
                    'padding': '16px 24px',
                    'fontWeight': '500',
                    'textTransform': 'uppercase',
                    'fontSize': '12px',
                    'letterSpacing': '0.5px',
                    'color': '#6b7280'
                }),
                html.Div('Market', style={
                    'flex': '1',
                    'minWidth': '150px',
                    'padding': '16px 24px',
                    'fontWeight': '500',
                    'textTransform': 'uppercase',
                    'fontSize': '12px',
                    'letterSpacing': '0.5px',
                    'color': '#6b7280'
                }),
                html.Div('Line', style={
                    'flex': '0 0 120px',
                    'padding': '16px 24px',
                    'fontWeight': '500',
                    'textTransform': 'uppercase',
                    'fontSize': '12px',
                    'letterSpacing': '0.5px',
                    'color': '#6b7280'
                }),
                html.Div('EV %', style={
                    'flex': '0 0 100px',
                    'padding': '16px 24px',
                    'fontWeight': '500',
                    'textTransform': 'uppercase',
                    'fontSize': '12px',
                    'letterSpacing': '0.5px',
                    'color': '#6b7280'
                })
            ], style={
                'display': 'flex',
                'backgroundColor': '#f9fafb',
                'borderBottom': '1px solid #e5e7eb'
            })
        ], style={
            'position': 'sticky',
            'top': '220px',  # Below ribbons (156px) + filter buttons (~64px)
            'zIndex': '997',
            'background': 'white'
        }),
        
        # Table body (scrollable)
        html.Div([
            html.Div([
                html.Div([
                    html.Div(row['Player'], style={
                        'flex': '1',
                        'minWidth': '200px',
                        'padding': '16px 24px',
                        'fontWeight': '500',
                        'color': '#111827'
                    }),
                    html.Div(row['Market'], style={
                        'flex': '1',
                        'minWidth': '150px',
                        'padding': '16px 24px',
                        'color': '#374151'
                    }),
                    html.Div(row['Line'], style={
                        'flex': '0 0 120px',
                        'padding': '16px 24px',
                        'color': '#374151'
                    }),
                    html.Div(row['EV %'], style={
                        'flex': '0 0 100px',
                        'padding': '16px 24px',
                        'fontWeight': '600',
                        'color': '#059669'
                    })
                ], style={
                    'display': 'flex',
                    'borderBottom': '1px solid #e5e7eb',
                    'transition': 'background-color 0.15s',
                    'cursor': 'default'
                }, className='table-row')
            ]) for row in filtered_data
        ])
    ], style={
        'border': '1px solid #e5e7eb',
        'borderRadius': '4px',
        'overflow': 'hidden',
        'background': 'white'
    })

# FIXED Callback for market filtering
@app.callback(
    Output({'type': 'evs-table-container', 'sport': dash.MATCH}, 'children'),
    [Input({'type': 'market-filter-btn', 'index': dash.ALL, 'sport': dash.MATCH}, 'n_clicks')],
    [State('current-sport', 'data')],
    prevent_initial_call=True
)
def update_market_filter(n_clicks, current_sport):
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return dash.no_update
    
    # Get which button was clicked
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    button_data = json.loads(button_id)
    selected_market = button_data['index']
    
    # Reload data and filter
    individualEVs = read_ev_results(current_sport)
    
    return create_evs_table(individualEVs, selected_market)

def render_parlays(sport):
    """Render correlation parlays for the selected sport"""
    if sport != 'MLB':
        return html.Div([
            html.Div([
                html.P(f"{sport} correlation parlays coming soon!", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, sans-serif'
                }),
                html.P("Correlation strategies need to be defined for this sport.", style={
                    'fontSize': '14px',
                    'color': '#9ca3af',
                    'fontFamily': 'Inter, sans-serif'
                })
            ], style={
                'textAlign': 'center',
                'padding': '48px 24px'
            })
        ])
    
    parlays = read_correlation_parlays(sport)
    
    if not parlays:
        return html.Div([
            html.Div([
                html.P(f"No {sport} correlation parlays found.", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, sans-serif'
                })
            ], style={
                'textAlign': 'center',
                'padding': '48px 24px'
            })
        ])
    
    return html.Div([
        html.Div([
            render_parlay_card(parlay) for parlay in parlays
        ])
    ])

def render_parlay_card(parlay):
    """Render a single parlay card"""
    return html.Div([
        # Parlay header
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
            'fontFamily': 'Inter, sans-serif'
        }),
        
        # Anchor
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
                'fontFamily': 'Inter, sans-serif',
                'padding': '12px 0',
                'borderBottom': '1px solid #e5e7eb'
            })
        ], style={'padding': '16px 24px'}),
        
        # Batters
        html.Div([
            html.Div([
                html.Div([
                    html.Div(batter['Batter'], style={
                        'fontSize': '14px',
                        'color': '#374151',
                        'padding': '10px 0',
                        'borderBottom': '1px solid #f3f4f6' if i < len(parlay['batters']) - 1 else 'none',
                        'fontFamily': 'Inter, sans-serif'
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

# For deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
