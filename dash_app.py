# dash_app.py - Updated with clean text buttons and modern font
import dash
from dash import dcc, html, Input, Output, callback, dash_table
import pandas as pd
import os

# Initialize the Dash app with server configuration
app = dash.Dash(__name__)
server = app.server  # Expose server for deployment

# Test data - same as before
individualEVs = [
    {'Player': 'Shohei Ohtani', 'Market': 'Total Bases', 'Line': '2.5', 'EV %': '8.4%'},
    {'Player': 'Aaron Judge', 'Market': 'Hits', 'Line': '1.5', 'EV %': '7.2%'},
    {'Player': 'Mookie Betts', 'Market': 'Runs Scored', 'Line': '0.5', 'EV %': '6.8%'},
    {'Player': 'Juan Soto', 'Market': 'RBIs', 'Line': '1.5', 'EV %': '5.9%'},
    {'Player': 'Ronald Acuña Jr.', 'Market': 'Total Bases', 'Line': '1.5', 'EV %': '5.3%'},
]

parlays = [
    {
        'id': 'PARLAY_001',
        'legs': [
            {'Player': 'Gerrit Cole', 'Market': 'Strikeouts', 'Line': '6.5', 'EV %': '4.2%'},
            {'Player': 'Pete Alonso', 'Market': 'Hits', 'Line': '1.5', 'EV %': '3.8%'},
            {'Player': 'Francisco Lindor', 'Market': 'Total Bases', 'Line': '1.5', 'EV %': '3.5%'}
        ],
        'totalEV': '12.1%'
    },
    {
        'id': 'PARLAY_002',
        'legs': [
            {'Player': 'Spencer Strider', 'Market': 'Strikeouts', 'Line': '7.5', 'EV %': '5.1%'},
            {'Player': 'Freddie Freeman', 'Market': 'Hits', 'Line': '1.5', 'EV %': '4.2%'}
        ],
        'totalEV': '9.8%'
    }
]

# Get unique markets for filtering
all_markets = list(set([ev['Market'] for ev in individualEVs]))

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
    
    # Main Content Area
    html.Div([
        html.Div(id='main-content')
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

# State management for active views
current_view = 'individual'

@app.callback(
    [Output('main-content', 'children'),
     Output('view-individual', 'style'),
     Output('view-parlays', 'style')],
    [Input('view-individual', 'n_clicks'),
     Input('view-parlays', 'n_clicks')]
)
def update_view(individual_clicks, parlays_clicks):
    global current_view
    ctx = dash.callback_context
    
    # Determine which view button was clicked
    if ctx.triggered:
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'view-individual':
            current_view = 'individual'
        elif button_id == 'view-parlays':
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
            ], style={'display': 'flex', 'alignItems': 'center'})
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

def render_parlays():
    return html.Div([
        # Header
        html.Div([
            html.H2("Correlation Parlays", style={
                'fontSize': '32px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }),
            html.Span(f"{len(parlays)} parlays found", style={
                'fontSize': '14px',
                'color': '#6b7280',
                'fontWeight': '600',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'marginBottom': '24px'
        }),
        
        # Action buttons (clean text style)
        html.Div([
            html.Button("🔄 Refresh", style={
                'background': 'none',
                'border': 'none',
                'fontSize': '14px',
                'fontWeight': '500',
                'color': '#374151',
                'marginRight': '24px',
                'cursor': 'pointer',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }),
            html.Button("🔍 Filter", style={
                'background': 'none',
                'border': 'none',
                'fontSize': '14px',
                'fontWeight': '500',
                'color': '#374151',
                'cursor': 'pointer',
                'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            })
        ], style={'marginBottom': '24px'}),
        
        # Parlay cards
        html.Div([
            render_parlay_card(parlay) for parlay in parlays
        ])
    ])

def render_parlay_card(parlay):
    return html.Div([
        # Parlay header
        html.Div([
            html.Strong(f"{parlay['id']} • {len(parlay['legs'])} Legs • Total EV: "),
            html.Span(parlay['totalEV'], style={
                'color': '#059669',
                'fontWeight': '600'
            })
        ], style={
            'background': '#f9fafb',
            'padding': '12px 24px',
            'borderBottom': '1px solid #e5e7eb',
            'fontSize': '12px',
            'fontWeight': '500',
            'color': '#6b7280',
            'textTransform': 'uppercase',
            'letterSpacing': '0.5px',
            'fontFamily': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
        }),
        
        # Parlay legs table
        dash_table.DataTable(
            data=parlay['legs'],
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
                'padding': '12px 24px',
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
                }
            ]
        )
    ], style={
        'background': 'white',
        'border': '1px solid #e5e7eb',
        'borderRadius': '4px',
        'overflow': 'hidden',
        'marginBottom': '24px'
    })

# Filtering callback for Individual EVs
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

# For deployment
if __name__ == '__main__':
    # Use PORT environment variable for deployment
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
