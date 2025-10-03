# debug_dash_app.py - Test environment variables
import dash
from dash import html
import os
import logging

# Initialize the Dash app
app = dash.Dash(__name__)
server = app.server

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug environment variables
def debug_environment():
    """Debug what environment variables are available"""
    logger.info("=== ENVIRONMENT VARIABLE DEBUG ===")
    
    # Check if the variable exists
    creds_var = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    
    if creds_var:
        logger.info(f"✅ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS found!")
        logger.info(f"   Length: {len(creds_var)} characters")
        logger.info(f"   Starts with: {creds_var[:50]}...")
        logger.info(f"   Ends with: ...{creds_var[-50:]}")
    else:
        logger.error("❌ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS not found!")
        
        # Show all available environment variables
        logger.info("Available environment variables:")
        for key in sorted(os.environ.keys()):
            value = os.environ[key]
            if len(value) > 50:
                display_value = f"{value[:20]}...{value[-20:]}"
            else:
                display_value = value
            logger.info(f"   {key}: {display_value}")

# Run debug on startup
debug_environment()

# Simple layout to show debug info
app.layout = html.Div([
    html.H1("Environment Variable Debug"),
    html.Div(id="debug-info")
])

@app.callback(
    dash.dependencies.Output('debug-info', 'children'),
    dash.dependencies.Input('debug-info', 'id')
)
def show_debug_info(_):
    creds_var = os.environ.get('GOOGLE_SERVICE_ACCOUNT_CREDENTIALS')
    
    if creds_var:
        return [
            html.P("✅ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS found!"),
            html.P(f"Length: {len(creds_var)} characters"),
            html.P(f"Starts with: {creds_var[:50]}..."),
        ]
    else:
        env_vars = [html.Li(f"{k}: {v[:30]}..." if len(v) > 30 else f"{k}: {v}") 
                   for k, v in sorted(os.environ.items())]
        
        return [
            html.P("❌ GOOGLE_SERVICE_ACCOUNT_CREDENTIALS not found!"),
            html.P("Available environment variables:"),
            html.Ul(env_vars[:20])  # Show first 20 only
        ]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8050))
    app.run_server(debug=False, host='0.0.0.0', port=port)
