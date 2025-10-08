# dash_app.py - Multi-sport dashboard with Google Sheets integration
import dash
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
import os
import gspread
from google.oauth2.service_account import Credentials
import json
import logging

# Initialize the Dash app with server configuration
app = dash.Dash(__name__)
server = app.server  # Expose server for deployment

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Determine spreadsheet name based on sport
        spreadsheet_name = f"{sport}_Splash_Data"
        
        logger.info(f"📊 Attempting to open {spreadsheet_name} spreadsheet...")
        spreadsheet = client.open(spreadsheet_name)
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
        
        # Extract headers and data
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        
        logger.info(f"Using headers from row {header_row_index}: {headers}")
        logger.info(f"Data rows available: {len(data_rows)}")
        
        # Create DataFrame
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
        
        logger.info(f"Using player column: '{player_col}'")
        
        # Remove empty rows
        before_filter = len(ev_df)
        ev_df = ev_df[ev_df[player_col].notna() & (ev_df[player_col] != '')]
        after_filter = len(ev_df)
        
        logger.info(f"Rows after filtering: {after_filter} (removed {before_filter - after_filter})")
        
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
            logger.warning("No EV percentage column found")
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
            logger.error("❌ Failed to get Google Sheets client for parlays")
            return []
        
        logger.info("📊 Attempting to read Correlation Parlays...")
        spreadsheet = client.open(f"{sport}_Splash_Data")
        
        parlay_worksheet = spreadsheet.worksheet("CORRELATION_PARLAYS")
        logger.info(f"✅ Successfully accessed CORRELATION_PARLAYS worksheet")
        
        all_data = parlay_worksheet.get_all_values()
        
        if not all_data:
            logger.warning("⚠️ Parlay sheet is empty")
            return []
        
        logger.info(f"📊 Total rows in parlay sheet: {len(all_data)}")
        
        # Find header row
        header_row_index = -1
        
        for i, row in enumerate(all_data[:20]):
            non_empty = [cell for cell in row if cell and str(cell).strip()]
            
            if len(non_empty) >= 5:
                row_lower = [str(cell).lower() for cell in row]
                has_underscore_cols = any('_' in str(cell) for cell in row if cell)
                has_id_col = any('id' in str(cell).lower() for cell in row if cell)
                has_pitcher_name = any('pitcher_name' in str(cell).lower() for cell in row if cell)
                
                if has_underscore_cols or (has_id_col and has_pitcher_name):
                    logger.info(f"🎯 Found actual header row at index {i}: {row}")
                    header_row_index = i
                    break
        
        if header_row_index == -1:
            logger.error("❌ Could not find header row in parlay sheet")
            return []
        
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        
        logger.info(f"📋 Using headers from row {header_row_index}")
        logger.info(f"📊 Data rows available: {len(data_rows)}")
        
        # Create DataFrame
        parlay_df = pd.DataFrame(data_rows, columns=headers)
        
        # Remove empty rows
        before_filter = len(parlay_df)
        parlay_df = parlay_df[parlay_df.iloc[:, 0].notna() & (parlay_df.iloc[:, 0] != '')]
        after_filter = len(parlay_df)
        
        logger.info(f"🔍 Rows after filtering empty: {after_filter} (removed {before_filter - after_filter})")
        
        if parlay_df.empty:
            logger.warning("⚠️ No parlay data found after filtering")
            return []
        
        # Parse parlays
        parlays = []
        
        for idx, row in parlay_df.iterrows():
            try:
                pitcher_name = row.get('Pitcher_Name', '')
                pitcher_market = row.get('Pitcher_Market', '')
                pitcher_line = row.get('Pitcher_Line', '')
                pitcher_bet_type = row.get('Pitcher_Bet_Type', '')
                pitcher_ev = row.get('Pitcher_EV', '')
                
                if not pitcher_name:
                    continue
                
                pitcher_market_clean = clean_market_name(pitcher_market) if pitcher_market else ""
                
                # Collect batter legs
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
                        logger.warning(f"  ⚠️ Error parsing batter data: {e}")
                    
                    batter_num += 1
                
                if not batter_legs:
                    continue
                
                # Calculate total EV
                total_ev = 0
                try:
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
                except Exception as e:
                    logger.warning(f"  ⚠️ Error calculating total EV: {e}")
                
                pitcher_info = {
                    'Player': pitcher_name,
                    'Market': pitcher_market_clean,
                    'Line': pitcher_line,
                    'EV': f"{float(pitcher_ev):.1%}" if pitcher_ev else "",
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
                logger.error(f"  ❌ Error parsing parlay row {idx}: {e}")
                continue
        
        logger.info(f"\n✅ Successfully parsed {len(parlays)} parlays total")
        return parlays
        
    except Exception as e:
        logger.error(f"❌ Error reading correlation parlays: {e}")
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
    
    # Header
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
    ], className='header-fixed-class', style={
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
    
    # Two stacked ribbons
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
    ], className='ribbons-fixed-class', style={
        'background': 'white',
        'borderBottom': '1px solid #f3f4f6',
        'position': 'fixed',
        'top': '64px',
        'left': '0',
        'right': '0',
        'width': '100%',
        'zIndex': '999'
    }),

    # Spacer
    html.Div(style={'height': '156px'}),
    
    # Main Content Area
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
    """Render individual EVs for the selected sport"""
    individualEVs = read_ev_results(sport)
    
    if not individualEVs:
        return html.Div([
            html.Div([
                html.P(f"No {sport} EV opportunities found.", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }),
                html.P("Run the pipeline to generate data.", style={
                    'fontSize': '14px',
                    'color': '#9ca3af',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                })
            ], style={
                'textAlign': 'center',
                'padding': '48px 24px'
            })
        ])
    
    # Get unique markets for filtering
    all_markets = list(set([ev['Market'] for ev in individualEVs if ev.get('Market')]))
    
    # Create table
    table = dash_table.DataTable(
        data=individualEVs,
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
    
    return html.Div([table])

def render_parlays(sport):
    """Render correlation parlays for the selected sport"""
    if sport != 'MLB':
        return html.Div([
            html.Div([
                html.P(f"{sport} correlation parlays coming soon!", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }),
                html.P("Correlation strategies need to be defined for this sport.", style={
                    'fontSize': '14px',
                    'color': '#9ca3af',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
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
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
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
            'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
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
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
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

# For deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
