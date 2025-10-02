# dash_app.py - Dash app configured for server deployment
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

# Define the app layout - same as before but with server optimization
app.layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.H1("EV Sports", style={
                'margin': '0',
                'fontSize': '24px',
                'fontWeight': '700',
                'color': '#111827'
            }),
            html.Span("Last Updated: 2 hours ago", style={
                'fontSize': '14px',
                'color': '#6b7280'
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
    
    # League Selection Ribbon
    html.Div([
        html.Div([
            html.Span("MLB", style={
                'color': '#111827',
                'fontWeight': '500',
                'fontSize': '14px',
                'marginRight': '32px'
            }),
            html.Span("NFL", style={
                'color': '#9ca3af',
                'fontSize': '14px',
                'marginRight': '32px'
            }),
            html.Span("NBA", style={
                'color': '#9ca3af',
                'fontSize': '14px'
            })
        ], style={
            'maxWidth': '1280px',
            'margin': '0 auto',
            'padding': '16px 24px'
        })
    ], style={
        'background': '#f9fafb',
        'borderBottom': '1px solid #e5e7eb',
        'height': '56px',
        'display': 'flex',
        'alignItems': 'center'
    }),
    
    # Main Navigation Tabs
    dcc.Tabs(
        id="main-tabs",
        value='individual',
        children=[
            dcc.Tab(label='Individual EVs', value='individual'),
            dcc.Tab(label='Correlation Parlays', value='parlays')
        ],
        style={
            'height': '56px',
            'borderBottom': '1px solid #e5e7eb'
        },
        colors={
            'border': '#e5e7eb',
            'primary': '#111827',
            'background': 'white'
        }
    ),
    
    # Main Content Area
    html.Div([
        html.Div(id='main-content')
    ], style={
        'maxWidth': '1280px',
        'margin': '0 auto',
        'padding': '48px 24px'
    })
])

# [Include all the callback functions from the previous code - same as before]

@app.callback(
    Output('main-content', 'children'),
    Input('main-tabs', 'value')
)
def render_content(active_tab):
    if active_tab == 'individual':
        return render_individual_evs()
    elif active_tab == 'parlays':
        return render_parlays()

def render_individual_evs():
    return html.Div([
        # Header with filter buttons
        html.Div([
            html.H2("Individual EV Opportunities", style={
                'fontSize': '30px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0',
                'marginRight': '24px'
            }),
            html.Div([
                html.Button(
                    "All",
                    id="filter-all",
                    n_clicks=0,
                    style={
                        'backgroundColor': '#111827',
                        'color': 'white',
                        'border': '1px solid #111827',
                        'borderRadius': '4px',
                        'padding': '6px 16px',
                        'fontSize': '14px',
                        'fontWeight': '500',
                        'marginRight': '8px',
                        'cursor': 'pointer'
                    }
                )
            ] + [
                html.Button(
                    market,
                    id=f"filter-{market.replace(' ', '-').lower()}",
                    n_clicks=0,
                    style={
                        'backgroundColor': 'white',
                        'color': '#6b7280',
                        'border': '1px solid #d1d5db',
                        'borderRadius': '4px',
                        'padding': '6px 16px',
                        'fontSize': '14px',
                        'fontWeight': '500',
                        'marginRight': '8px',
                        'cursor': 'pointer'
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
                'fontWeight': '600'
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
                'fontSize': '30px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0'
            }),
            html.Span(f"{len(parlays)} parlays found", style={
                'fontSize': '14px',
                'color': '#6b7280',
                'fontWeight': '600'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'marginBottom': '24px'
        }),
        
        # Action buttons
        html.Div([
            html.Button("🔄 Refresh", style={
                'padding': '8px 16px',
                'fontSize': '14px',
                'fontWeight': '500',
                'color': '#374151',
                'backgroundColor': 'white',
                'border': '1px solid #d1d5db',
                'borderRadius': '4px',
                'marginRight': '16px',
                'cursor': 'pointer'
            }),
            html.Button("🔍 Filter", style={
                'padding': '8px 16px',
                'fontSize': '14px',
                'fontWeight': '500',
                'color': '#374151',
                'backgroundColor': 'white',
                'border': '1px solid #d1d5db',
                'borderRadius': '4px',
                'cursor': 'pointer'
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
            'letterSpacing': '0.5px'
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
                'padding': '12px 24px'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '16px 24px',
                'fontSize': '14px',
                'border': 'none',
                'borderBottom': '1px solid #e5e7eb'
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

# Filtering callback (include the complete callback from previous code)
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
            'padding': '16px 24px'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '16px 24px',
            'fontSize': '14px',
            'border': 'none',
            'borderBottom': '1px solid #e5e7eb'
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
        'backgroundColor': '#111827',
        'color': 'white',
        'border': '1px solid #111827',
        'borderRadius': '4px',
        'padding': '6px 16px',
        'fontSize': '14px',
        'fontWeight': '500',
        'marginRight': '8px',
        'cursor': 'pointer'
    }
    
    inactive_style = {
        'backgroundColor': 'white',
        'color': '#6b7280',
        'border': '1px solid #d1d5db',
        'borderRadius': '4px',
        'padding': '6px 16px',
        'fontSize': '14px',
        'fontWeight': '500',
        'marginRight': '8px',
        'cursor': 'pointer'
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
