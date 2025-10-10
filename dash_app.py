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
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            }),
            html.Div('MARKET', style={
                'flex': '1',
                'padding': '12px 16px',
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            }),
            html.Div('LINE', style={
                'flex': '0 0 120px',
                'padding': '12px 16px',
                'fontWeight': '600',
                'fontSize': '11px',
                'letterSpacing': '0.5px',
                'color': '#6b7280',
                'textTransform': 'uppercase'
            }),
            html.Div('EV', style={
                'flex': '0 0 100px',
                'padding': '12px 16px',
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
