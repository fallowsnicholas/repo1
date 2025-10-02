import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="EV Sports - MLB Dashboard",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for exact Honda-inspired design match
st.markdown("""
<style>
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    header[data-testid="stHeader"] {display: none;}
    
    /* Main container */
    .main .block-container {
        padding-top: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
        max-width: none;
    }
    
    /* Header Navigation */
    .header-nav {
        background: white;
        border-bottom: 1px solid #e5e7eb;
        padding: 0;
        margin: 0;
    }
    
    .header-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 4rem;
    }
    
    .logo {
        font-size: 1.5rem;
        font-weight: 700;
        color: #111827;
    }
    
    .last-updated {
        font-size: 0.875rem;
        color: #6b7280;
    }
    
    /* Ribbon 1: League Selection */
    .league-ribbon {
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .league-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
        display: flex;
        height: 3.5rem;
        align-items: center;
    }
    
    .league-tab {
        padding: 0 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: #374151;
        cursor: pointer;
        position: relative;
        display: flex;
        align-items: center;
        height: 100%;
        text-decoration: none;
        border: none;
        background: none;
    }
    
    .league-tab.active {
        color: #111827;
    }
    
    .league-tab.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: #111827;
    }
    
    .league-tab.disabled {
        color: #9ca3af;
        cursor: not-allowed;
    }
    
    /* Ribbon 2: View Selection */
    .view-ribbon {
        background: white;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .view-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 0 1.5rem;
        display: flex;
        height: 3.5rem;
        align-items: center;
    }
    
    .view-tab {
        padding: 0 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: #6b7280;
        cursor: pointer;
        position: relative;
        display: flex;
        align-items: center;
        height: 100%;
        text-decoration: none;
        border: none;
        background: none;
        margin-right: 2rem;
    }
    
    .view-tab:hover {
        color: #111827;
    }
    
    .view-tab.active {
        color: #111827;
    }
    
    .view-tab.active::after {
        content: '';
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: #111827;
    }
    
    /* Main Content Area */
    .main-content {
        max-width: 1280px;
        margin: 0 auto;
        padding: 3rem 1.5rem;
    }
    
    .content-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
    }
    
    .page-title {
        font-size: 1.875rem;
        font-weight: 300;
        color: #111827;
        margin: 0;
    }
    
    .result-count {
        font-size: 0.875rem;
        color: #6b7280;
    }
    
    /* Clean Table Styles */
    .clean-table {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.125rem;
        overflow: hidden;
        margin-top: 1.5rem;
    }
    
    .clean-table table {
        width: 100%;
        border-collapse: collapse;
    }
    
    .clean-table thead {
        background: #f9fafb;
    }
    
    .clean-table th {
        padding: 1rem 1.5rem;
        text-align: left;
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .clean-table th:last-child {
        text-align: right;
    }
    
    .clean-table td {
        padding: 1rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
        font-size: 0.875rem;
    }
    
    .clean-table td:last-child {
        text-align: right;
        font-weight: 600;
        color: #059669;
    }
    
    .clean-table tr:hover {
        background: #f9fafb;
    }
    
    /* Parlay Cards */
    .parlay-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.125rem;
        overflow: hidden;
        margin-bottom: 1.5rem;
    }
    
    .parlay-header {
        background: #f9fafb;
        padding: 0.75rem 1.5rem;
        border-bottom: 1px solid #e5e7eb;
        font-size: 0.75rem;
        font-weight: 500;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Action Buttons */
    .action-buttons {
        display: flex;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .action-btn {
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        color: #374151;
        background: white;
        border: 1px solid #d1d5db;
        border-radius: 0.125rem;
        cursor: pointer;
        transition: background-color 0.15s;
    }
    
    .action-btn:hover {
        background: #f9fafb;
    }
</style>
""", unsafe_allow_html=True)

class MLBDashboard:
    """Main dashboard class for reading and displaying MLB EV data"""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        
    # Remove caching decorator - keep only connection caching
    def connect_to_sheets(self):
        """Connect to Google Sheets with caching"""
        try:
            # Check if credentials are available
            if 'GOOGLE_SERVICE_ACCOUNT_CREDENTIALS' not in st.secrets:
                st.error("Google Service Account credentials not found in Streamlit secrets")
                return None
                
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Handle credentials stored as JSON string in Streamlit secrets
            creds_raw = st.secrets["GOOGLE_SERVICE_ACCOUNT_CREDENTIALS"]
            
            # Parse JSON string if needed
            if isinstance(creds_raw, str):
                service_account_info = json.loads(creds_raw)
            else:
                service_account_info = dict(creds_raw)
            
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)
            
            return client
            
        except Exception as e:
            st.error(f"Failed to connect to Google Sheets: {e}")
            st.error(f"Error details: {str(e)}")
            return None
    
    # Remove caching decorator to fix gspread session issues
    def read_sheet_with_metadata_skip(self, _client, sheet_name):
        """Read Google Sheets data while skipping metadata headers"""
        try:
            spreadsheet = _client.open("MLB_Splash_Data")
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Get all data
            all_data = worksheet.get_all_values()
            
            if not all_data:
                return pd.DataFrame()
            
            # Find header row - look for "Parlay_ID" specifically
            header_row_index = -1
            
            for i, row in enumerate(all_data):
                # Check if this row contains "Parlay_ID"
                if any('Parlay_ID' in str(cell) for cell in row):
                    header_row_index = i
                    break
            
            if header_row_index == -1:
                # Fallback: look for any header-like indicators
                header_indicators = ['Player', 'Name', 'Market', 'Line', 'Odds', 'Book', 'Team', 'EV', 'Pitcher']
                for i, row in enumerate(all_data):
                    if any(indicator in str(row) for indicator in header_indicators):
                        header_row_index = i
                        break
            
            if header_row_index == -1:
                header_row_index = 0
            
            # Extract headers and data
            headers = all_data[header_row_index]
            data_rows = all_data[header_row_index + 1:]
            
            # Filter out empty rows
            data_rows = [row for row in data_rows if any(cell.strip() if cell else '' for cell in row)]
            
            if not data_rows:
                return pd.DataFrame()
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            df = df.dropna(how='all')
            df = df.loc[:, df.columns != '']
            
            return df
            
        except Exception as e:
            st.error(f"Error reading {sheet_name}: {e}")
            return pd.DataFrame()
    
    def get_ev_opportunities(self, client):
        """Read EV opportunities from EV_RESULTS sheet"""
        df = self.read_sheet_with_metadata_skip(client, "EV_RESULTS")
        
        if df.empty:
            return df
        
        # Convert numeric columns
        numeric_columns = ['Splash_EV_Percentage', 'Num_Books_Used', 'Best_Odds', 'True_Prob']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Sort by EV descending
        if 'Splash_EV_Percentage' in df.columns:
            df = df.sort_values('Splash_EV_Percentage', ascending=False)
        
        return df
    
    def get_correlation_parlays(self, client):
        """Read correlation parlays from CORRELATION_PARLAYS sheet"""
        df = self.read_sheet_with_metadata_skip(client, "CORRELATION_PARLAYS")
        
        if df.empty:
            return df
        
        # Convert numeric columns
        numeric_columns = ['Pitcher_EV', 'Estimated_Parlay_EV', 'Total_Legs', 'Correlation_Strength']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Sort by estimated EV descending
        if 'Estimated_Parlay_EV' in df.columns:
            df = df.sort_values('Estimated_Parlay_EV', ascending=False)
        
        return df
    
    def get_pipeline_status(self, client):
        """Check the status of different pipeline sheets"""
        sheets_to_check = [
            ("MATCHUPS", "Step 1: Matchups"),
            ("ODDS_API", "Step 2: Odds Data"),
            ("SPLASH_MLB", "Step 3: Splash Data"),
            ("MATCHED_LINES", "Step 4: Matched Lines"),
            ("EV_RESULTS", "Step 5: EV Results"),
            ("PITCHER_ANCHORS", "Step 6: Pitcher Anchors"),
            ("CORRELATION_PARLAYS", "Step 7: Parlays")
        ]
        
        status_data = []
        for sheet_name, step_name in sheets_to_check:
            try:
                df = self.read_sheet_with_metadata_skip(client, sheet_name)
                if df.empty:
                    status = "❌ No Data"
                    color = "error"
                else:
                    status = f"✅ {len(df)} rows"
                    color = "success"
            except:
                status = "⚠️ Sheet Missing"
                color = "warning"
            
            status_data.append({
                "Step": step_name,
                "Status": status,
                "Color": color
            })
        
        return status_data

def main():
    """Main Streamlit app with exact Honda-inspired design"""
    
    # Header Navigation
    st.markdown("""
    <div class="header-nav">
        <div class="header-content">
            <div class="logo">EV Sports</div>
            <div class="last-updated">Last Updated: 2 hours ago</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # League Selection Ribbon
    st.markdown("""
    <div class="league-ribbon">
        <div class="league-content">
            <div class="league-tab active">MLB</div>
            <div class="league-tab disabled">NFL</div>
            <div class="league-tab disabled">NBA</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # View Selection Ribbon with working tabs
    view_options = ["Individual EVs", "Correlation Parlays", "Pipeline Status"]
    
    # Use session state to track active view
    if 'active_view' not in st.session_state:
        st.session_state.active_view = "Individual EVs"
    
    # Create clickable view tabs
    col1, col2, col3, col_spacer = st.columns([2, 2, 2, 6])
    
    with col1:
        if st.button("Individual EVs", key="view_individual", help="Individual EV Opportunities"):
            st.session_state.active_view = "Individual EVs"
    
    with col2:
        if st.button("Correlation Parlays", key="view_parlays", help="Correlation Parlays"):
            st.session_state.active_view = "Correlation Parlays"
    
    with col3:
        if st.button("Pipeline Status", key="view_status", help="Pipeline Status"):
            st.session_state.active_view = "Pipeline Status"
    
    # Style the active tab
    active_view = st.session_state.active_view
    st.markdown(f"""
    <div class="view-ribbon">
        <div class="view-content">
            <div class="view-tab {'active' if active_view == 'Individual EVs' else ''}">Individual EVs</div>
            <div class="view-tab {'active' if active_view == 'Correlation Parlays' else ''}">Correlation Parlays</div>
            <div class="view-tab {'active' if active_view == 'Pipeline Status' else ''}">Pipeline Status</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Main Content Area
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # Initialize dashboard
    dashboard = MLBDashboard()
    
    # Connect to Google Sheets
    with st.spinner("Connecting to data source..."):
        client = dashboard.connect_to_sheets()
    
    if not client:
        st.error("Unable to connect to Google Sheets. Please check your credentials.")
        st.info("Make sure GOOGLE_SERVICE_ACCOUNT_CREDENTIALS is set in Streamlit secrets.")
        return
    
    # Display content based on active view
    if active_view == "Individual EVs":
        show_individual_evs_clean(dashboard, client)
    elif active_view == "Correlation Parlays":
        show_correlation_parlays_clean(dashboard, client)
    elif active_view == "Pipeline Status":
        show_pipeline_status(dashboard, client)
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_individual_evs_clean(dashboard, client):
    """Display individual EV opportunities with clean table design"""
    
    with st.spinner("Loading EV opportunities..."):
        ev_df = dashboard.get_ev_opportunities(client)
    
    if ev_df.empty:
        st.markdown("""
        <div class="content-header">
            <h1 class="page-title">Individual EV Opportunities</h1>
            <span class="result-count">0 opportunities found</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("No EV opportunities found. Make sure Step 5 (calculate_ev.py) has been run.")
        st.info("💡 Run your pipeline to generate EV data")
        return
    
    # Format the dataframe for display
    display_df = ev_df.copy()
    
    # Select and rename columns for display
    display_columns = {}
    if 'Player' in display_df.columns:
        display_columns['Player'] = 'Player'
    elif 'Name' in display_df.columns:
        display_columns['Name'] = 'Player'
        
    if 'Market' in display_df.columns:
        display_columns['Market'] = 'Market'
    if 'Line' in display_df.columns:
        display_columns['Line'] = 'Line'
    if 'Splash_EV_Percentage' in display_df.columns:
        display_columns['Splash_EV_Percentage'] = 'EV %'
    
    # Select only available columns
    available_columns = {k: v for k, v in display_columns.items() if k in display_df.columns}
    display_df = display_df[list(available_columns.keys())].rename(columns=available_columns)
    
    # Format EV percentage
    if 'EV %' in display_df.columns:
        display_df['EV %'] = display_df['EV %'].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
    
    # Content header
    st.markdown(f"""
    <div class="content-header">
        <h1 class="page-title">Individual EV Opportunities</h1>
        <span class="result-count">{len(display_df)} opportunities found</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Clean table
    if not display_df.empty:
        # Create HTML table
        table_html = '<div class="clean-table"><table>'
        
        # Header
        table_html += '<thead><tr>'
        for col in display_df.columns:
            table_html += f'<th>{col}</th>'
        table_html += '</tr></thead>'
        
        # Body
        table_html += '<tbody>'
        for _, row in display_df.iterrows():
            table_html += '<tr>'
            for col in display_df.columns:
                value = row[col]
                if col == 'Player':
                    table_html += f'<td style="font-weight: 500; color: #111827;">{value}</td>'
                elif col == 'EV %':
                    table_html += f'<td style="text-align: right; font-weight: 600; color: #059669;">{value}</td>'
                else:
                    table_html += f'<td style="color: #6b7280;">{value}</td>'
            table_html += '</tr>'
        
        table_html += '</tbody></table></div>'
        
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("No opportunities match your current filters.")

def parse_compressed_batter(batter_string):
    """Parse compressed batter string: 'Name, Market, Line, Bet_Type, EV, Best_Odds'"""
    if not batter_string or str(batter_string).strip() == '':
        return None
    
    try:
        parts = [part.strip() for part in str(batter_string).split(',')]
        if len(parts) >= 6:
            return {
                'name': parts[0],
                'market': parts[1], 
                'line': parts[2],
                'bet_type': parts[3],
                'ev': float(parts[4]) if parts[4] != 'N/A' else 0,
                'best_odds': parts[5]
            }
    except:
        pass
    return None

def show_correlation_parlays_clean(dashboard, client):
    """Display correlation parlays with clean card design"""
    
    with st.spinner("Loading correlation parlays..."):
        parlay_df = dashboard.read_sheet_with_metadata_skip(client, "CORRELATION_PARLAYS")
    
    if parlay_df.empty:
        st.markdown("""
        <div class="content-header">
            <h1 class="page-title">Correlation Parlays</h1>
            <span class="result-count">0 parlays found</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("No correlation parlays found. Make sure Step 7 (build_parlays.py) has been run.")
        st.info("💡 Run your pipeline to generate parlay data")
        return
    
    # Check if this is an empty status sheet or has parlays
    if 'Parlay_ID' not in parlay_df.columns:
        st.markdown("""
        <div class="content-header">
            <h1 class="page-title">Correlation Parlays</h1>
            <span class="result-count">Status Update</span>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("📋 **Pipeline Status Update**")
        
        # Try to find status information
        for idx, row in parlay_df.head(10).iterrows():
            row_values = [str(val) for val in row.values if val and str(val).strip()]
            if len(row_values) >= 2:
                st.write(f"**{row_values[0]}:** {row_values[1]}")
        return
    
    # Filter out rows that don't have parlay data (metadata rows)
    parlay_df = parlay_df[
        (parlay_df['Parlay_ID'].notna()) & 
        (parlay_df['Parlay_ID'].astype(str).str.contains('PARLAY_', na=False))
    ]
    
    if parlay_df.empty:
        st.markdown("""
        <div class="content-header">
            <h1 class="page-title">Correlation Parlays</h1>
            <span class="result-count">0 parlays found</span>
        </div>
        """, unsafe_allow_html=True)
        st.info("📊 No parlay data found in sheet - likely no games today.")
        return
    
    # Content header
    st.markdown(f"""
    <div class="content-header">
        <h1 class="page-title">Correlation Parlays</h1>
        <span class="result-count">{len(parlay_df)} parlays found</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Action buttons
    st.markdown("""
    <div class="action-buttons">
        <button class="action-btn">Refresh</button>
        <button class="action-btn">Filter</button>
    </div>
    """, unsafe_allow_html=True)
    
    # Find compressed batter columns dynamically
    batter_columns = [col for col in parlay_df.columns if 'Batter_' in col]
    
    # Display each parlay as a card
    for idx, row in parlay_df.iterrows():
        parlay_id = row.get('Parlay_ID', f'Parlay {idx+1}')
        pitcher_name = row.get('Pitcher_Name', 'Unknown Pitcher')
        pitcher_market = row.get('Pitcher_Market', 'Unknown Market')
        pitcher_line = row.get('Pitcher_Line', 'N/A')
        pitcher_bet_type = row.get('Pitcher_Bet_Type', 'N/A')
        
        # Handle pitcher EV
        try:
            pitcher_ev = float(row.get('Pitcher_EV', 0))
        except (ValueError, TypeError):
            pitcher_ev = 0
        
        # Handle total legs
        try:
            total_legs = int(float(row.get('Total_Legs', 0)))
        except (ValueError, TypeError):
            total_legs = 0
        
        # Create parlay card HTML
        st.markdown(f"""
        <div class="parlay-card">
            <div class="parlay-header">
                {parlay_id} • {total_legs} Legs
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Create table for parlay legs
        table_html = '<div class="clean-table"><table>'
        
        # Header
        table_html += '''
        <thead>
            <tr>
                <th>Player</th>
                <th>Market</th>
                <th>Line</th>
                <th>EV %</th>
            </tr>
        </thead>
        <tbody>
        '''
        
        # Pitcher row
        table_html += f'''
        <tr>
            <td style="font-weight: 500; color: #111827;">{pitcher_name}</td>
            <td style="color: #6b7280;">{pitcher_market}</td>
            <td style="color: #6b7280;">{pitcher_line}</td>
            <td style="text-align: right; color: #6b7280;">{pitcher_ev:.1%}</td>
        </tr>
        '''
        
        # Batter rows
        for batter_col in batter_columns:
            if batter_col in row and row[batter_col]:
                batter_data = parse_compressed_batter(row[batter_col])
                
                if batter_data:
                    table_html += f'''
                    <tr>
                        <td style="font-weight: 500; color: #111827;">{batter_data['name']}</td>
                        <td style="color: #6b7280;">{batter_data['market']}</td>
                        <td style="color: #6b7280;">{batter_data['line']}</td>
                        <td style="text-align: right; color: #6b7280;">{batter_data['ev']:.1%}</td>
                    </tr>
                    '''
        
        table_html += '</tbody></table></div>'
        
        st.markdown(table_html, unsafe_allow_html=True)
        
        # Add spacing between cards
        st.markdown('<br>', unsafe_allow_html=True)

def show_pipeline_status(dashboard, client):
    """Display pipeline status"""
    
    with st.spinner("Checking pipeline status..."):
        status_data = dashboard.get_pipeline_status(client)
    
    st.markdown("### Pipeline Status Overview")
    st.markdown("Monitor the status of each step in your MLB EV pipeline:")
    
    # Display status as cards
    cols = st.columns(2)
    
    for idx, status_info in enumerate(status_data):
        col_idx = idx % 2
        
        with cols[col_idx]:
            status_class = f"status-{status_info['Color']}"
            
            st.markdown(f"""
            <div class="metric-card">
                <h4>{status_info['Step']}</h4>
                <span class="status-indicator {status_class}">{status_info['Status']}</span>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Pipeline instructions
    st.markdown("### Pipeline Execution")
    st.markdown("""
    To run the complete pipeline:
    
    1. **Step 1:** `python fetch_matchups.py` - Get today's MLB matchups
    2. **Step 2:** `python fetch_odds_data.py` - Fetch odds from multiple sportsbooks  
    3. **Step 3A:** `python fetch_splash_json.py` - Get Splash Sports data
    4. **Step 3B:** `python process_splash_data.py` - Process and save to sheets
    5. **Step 4:** `python match_lines.py` - Match Splash props to odds
    6. **Step 5:** `python calculate_ev.py` - Calculate expected values
    7. **Step 6:** `python find_pitcher_anchors.py` - Find pitcher anchors
    8. **Step 7:** `python build_parlays.py` - Build correlation parlays
    
    Or use the GitHub Actions workflow for automated execution.
    """)

if __name__ == "__main__":
    main()
