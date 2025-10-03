# dash_app.py - Real data integration for Individual EVs only
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
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        return None

def read_ev_results():
    """Read Individual EV data from Google Sheets EV_RESULTS"""
    try:
        client = connect_to_sheets()
        if not client:
            return []
        
        spreadsheet = client.open("MLB_Splash_Data")
        ev_worksheet = spreadsheet.worksheet("EV_RESULTS")
        
        # Get all data and skip metadata rows
        all_data = ev_worksheet.get_all_values()
        
        if not all_data:
            logger.warning("EV_RESULTS sheet is empty")
            return []
        
        # Find header row (skip metadata)
        header_row_index = -1
        for i, row in enumerate(all_data):
            if row and any(col in row for col in ['Player', 'Name', 'Market']):
                header_row_index = i
                break
        
        if header_row_index == -1:
            logger.warning("Could not find header row in EV_RESULTS")
            return []
        
        # Extract headers and data
        headers = all_data[header_row_index]
        data_rows = all_data[header_row_index + 1:]
        
        # Create DataFrame
        ev_df = pd.DataFrame(data_rows, columns=headers)
        
        # Remove empty rows
        ev_df = ev_df[ev_df['Player'].notna() & (ev_df['Player'] != '')]
        
        if ev_df.empty:
            logger.warning("No EV data found after filtering")
            return []
        
        # Convert to format expected by dash table
        individual_evs = []
        for _, row in ev_df.iterrows():
            # Format EV percentage
            ev_value = row.get('Splash_EV_Percentage', 0)
            try:
                ev_float = float(ev_value)
                ev_percent = f"{ev_float:.1%}"
            except (ValueError, TypeError):
                ev_percent = str(ev_value)
            
            individual_evs.append({
                'Player': row['Player'],
                'Market': row.get('Market', ''),
                'Line': row.get('Line', ''),
                'EV %': ev_percent
            })
        
        logger.info(f"Successfully loaded {len(individual_evs)} Individual EV opportunities")
        return individual_evs
        
    except Exception as e:
        logger.error(f"Error reading EV results: {e}")
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

# Load real data
individualEVs = get_individual_evs()

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
            
            # Ribbon 2: View Selection (stacked underneath) - Only Individual EVs for now
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
        render_individual_evs()
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

def render_individual_evs():
    if not individualEVs:
        # Show empty state if no data
        return html.Div([
            html.H2("Individual EV Opportunities", style={
                'fontSize': '32px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0',
                'marginBottom': '24px',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }),
            html.Div([
                html.P("No EV opportunities found.", style={
                    'fontSize': '16px',
                    'color': '#6b7280',
                    'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }),
                html.P("Run your pipeline to populate data.", style={
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
        # Header with filter buttons (clean text style)
        html.Div([
            html.H2("Individual EV Opportunities", style={
                'fontSize': '32px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0',
                'marginRight': '24px',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }),
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
            ], style={'display': 'flex', 'alignItems': 'center'}) if all_markets else html.Div()
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'marginBottom': '24px'
        }),
        
        # Opportunities count
        html.Div(
            id='opportunities-count',
            children=f"{len(individualEVs)} opportunities found",
            style={
                'fontSize': '14px',
                'color': '#6b7280',
                'marginBottom': '24px',
                'fontWeight': '600',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }
        ),
        
        # Data table
        html.Div(id='evs-table')
    ])

# Filtering callback for Individual EVs (only if we have markets)
if all_markets:
    @app.callback(
        [Output('evs-table', 'children'),
         Output('opportunities-count', 'children')] +
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
            f"{len(filtered_data)} opportunities found",
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
