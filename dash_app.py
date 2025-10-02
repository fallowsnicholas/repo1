# dash_app.py - Improved UI inspired by React design
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

# Define the app layout with React-inspired clean design
app.layout = html.Div([
    # Header Navigation - Clean and minimal
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
            'maxWidth': '1400px',
            'margin': '0 auto',
            'padding': '0 24px',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'height': '64px'
        })
    ], style={
        'background': 'white',
        'borderBottom': '1px solid #e5e7eb',
        'position': 'sticky',
        'top': '0',
        'zIndex': '100'
    }),
    
    # Ribbon 1: League Selection - Gray background
    html.Div([
        html.Div([
            html.Div([
                html.Button("MLB", 
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#111827',
                        'fontSize': '14px',
                        'fontWeight': '500',
                        'padding': '16px 0',
                        'marginRight': '32px',
                        'position': 'relative',
                        'cursor': 'pointer',
                        'borderBottom': '2px solid #111827'
                    }
                ),
                html.Button("NFL", 
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#9ca3af',
                        'fontSize': '14px',
                        'fontWeight': '500',
                        'padding': '16px 0',
                        'marginRight': '32px',
                        'cursor': 'not-allowed'
                    }
                ),
                html.Button("NBA",
                    style={
                        'background': 'none',
                        'border': 'none',
                        'color': '#9ca3af',
                        'fontSize': '14px',
                        'fontWeight': '500',
                        'padding': '16px 0',
                        'cursor': 'not-allowed'
                    }
                )
            ], style={'display': 'flex', 'alignItems': 'center'})
        ], style={
            'maxWidth': '1400px',
            'margin': '0 auto',
            'padding': '0 24px'
        })
    ], style={
        'background': '#f9fafb',
        'borderBottom': '1px solid #e5e7eb',
        'height': '56px',
        'display': 'flex',
        'alignItems': 'center'
    }),
    
    # Ribbon 2: View Selection - White background
    dcc.Tabs(
        id="main-tabs",
        value='individual',
        children=[
            dcc.Tab(
                label='Individual EVs', 
                value='individual',
                style={
                    'padding': '16px 24px',
                    'border': 'none',
                    'backgroundColor': 'transparent',
                    'color': '#6b7280',
                    'fontSize': '14px',
                    'fontWeight': '500'
                },
                selected_style={
                    'padding': '16px 24px',
                    'border': 'none',
                    'backgroundColor': 'transparent',
                    'color': '#111827',
                    'fontSize': '14px',
                    'fontWeight': '500',
                    'borderBottom': '2px solid #111827'
                }
            ),
            dcc.Tab(
                label='Correlation Parlays', 
                value='parlays',
                style={
                    'padding': '16px 24px',
                    'border': 'none',
                    'backgroundColor': 'transparent',
                    'color': '#6b7280',
                    'fontSize': '14px',
                    'fontWeight': '500'
                },
                selected_style={
                    'padding': '16px 24px',
                    'border': 'none',
                    'backgroundColor': 'transparent',
                    'color': '#111827',
                    'fontSize': '14px',
                    'fontWeight': '500',
                    'borderBottom': '2px solid #111827'
                }
            )
        ],
        style={
            'maxWidth': '1400px',
            'margin': '0 auto',
            'padding': '0 24px',
            'height': '56px',
            'borderBottom': '1px solid #e5e7eb'
        },
        colors={
            'border': 'transparent',
            'primary': 'transparent',
            'background': 'white'
        }
    ),
    
    # Main Content Area
    html.Div([
        html.Div(id='main-content')
    ], style={
        'maxWidth': '1400px',
        'margin': '0 auto',
        'padding': '48px 24px',
        'backgroundColor': 'white',
        'minHeight': 'calc(100vh - 176px)'
    })
], style={
    'backgroundColor': 'white',
    'minHeight': '100vh',
    'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
})

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
        # Header section
        html.Div([
            html.H1("Individual EV Opportunities", style={
                'fontSize': '32px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0',
                'lineHeight': '1.2'
            }),
            html.Span(f"{len(individualEVs)} opportunities found", style={
                'fontSize': '14px',
                'color': '#6b7280',
                'fontWeight': '600'
            })
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'marginBottom': '32px'
        }),
        
        # Clean table with minimal styling
        html.Div([
            dash_table.DataTable(
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
                    'fontSize': '12px',
                    'textTransform': 'uppercase',
                    'letterSpacing': '0.5px',
                    'padding': '16px 24px',
                    'border': 'none',
                    'borderBottom': '1px solid #e5e7eb'
                },
                style_cell={
                    'textAlign': 'left',
                    'padding': '16px 24px',
                    'fontSize': '14px',
                    'border': 'none',
                    'borderBottom': '1px solid #e5e7eb',
                    'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
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
                        'fontWeight': '600',
                        'textAlign': 'right'
                    }
                ],
                style_table={
                    'border': '1px solid #e5e7eb',
                    'borderRadius': '4px',
                    'overflow': 'hidden'
                }
            )
        ])
    ])

def render_parlays():
    return html.Div([
        # Header section
        html.Div([
            html.H1("Correlation Parlays", style={
                'fontSize': '32px',
                'fontWeight': '300',
                'color': '#111827',
                'margin': '0',
                'lineHeight': '1.2'
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
            'marginBottom': '32px'
        }),
        
        # Action buttons
        html.Div([
            html.Button("Refresh", style={
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
            html.Button("Filter", style={
                'padding': '8px 16px',
                'fontSize': '14px',
                'fontWeight': '500',
                'color': '#374151',
                'backgroundColor': 'white',
                'border': '1px solid #d1d5db',
                'borderRadius': '4px',
                'cursor': 'pointer'
            })
        ], style={'marginBottom': '32px'}),
        
        # Parlay cards
        html.Div([
            render_parlay_card(parlay) for parlay in parlays
        ])
    ])

def render_parlay_card(parlay):
    return html.Div([
        # Parlay header with gray background
        html.Div([
            html.Span([
                f"{parlay['id']} • {len(parlay['legs'])} Legs • Total EV: ",
                html.Strong(parlay['totalEV'], style={'color': '#059669'})
            ])
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
                'fontSize': '12px',
                'textTransform': 'uppercase',
                'letterSpacing': '0.5px',
                'padding': '12px 24px',
                'border': 'none'
            },
            style_cell={
                'textAlign': 'left',
                'padding': '16px 24px',
                'fontSize': '14px',
                'border': 'none',
                'borderBottom': '1px solid #e5e7eb',
                'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
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
                    'color': '#6b7280',
                    'textAlign': 'right'
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

# For deployment
if __name__ == '__main__':
    # Use PORT environment variable for deployment
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
