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

# Custom CSS for clean, Honda-inspired design
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 300;
        color: #1f2937;
        margin-bottom: 0;
    }
    
    .sub-header {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 0.375rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .parlay-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 0.375rem;
        margin-bottom: 1.5rem;
        overflow: hidden;
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
    
    .ev-positive {
        color: #059669;
        font-weight: 600;
    }
    
    .status-indicator {
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .status-success {
        background: #dcfce7;
        color: #166534;
    }
    
    .status-warning {
        background: #fef3c7;
        color: #92400e;
    }
    
    .status-error {
        background: #fee2e2;
        color: #dc2626;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
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
            
            # Find header row
            header_indicators = ['Player', 'Name', 'Market', 'Line', 'Odds', 'Book', 'Team', 'EV']
            header_row_index = -1
            
            for i, row in enumerate(all_data):
                if any(indicator in row for indicator in header_indicators):
                    header_row_index = i
                    break
            
            if header_row_index == -1:
                return pd.DataFrame()
            
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
    """Main Streamlit app"""
    
    # Header
    st.markdown('<h1 class="main-header">⚾ EV Sports - MLB Dashboard</h1>', unsafe_allow_html=True)
    
    # Initialize dashboard
    dashboard = MLBDashboard()
    
    # Connect to Google Sheets (fresh connection each time)
    with st.spinner("Connecting to data source..."):
        client = dashboard.connect_to_sheets()
    
    if not client:
        st.error("Unable to connect to Google Sheets. Please check your credentials.")
        st.info("Make sure GOOGLE_SERVICE_ACCOUNT_CREDENTIALS is set in Streamlit secrets.")
        return
    
    # League and View Selection
    col1, col2, col3 = st.columns([1, 1, 8])
    
    with col1:
        league = st.selectbox("League", ["MLB"], index=0, key="league_select")
    
    with col2:
        view = st.selectbox("View", ["Individual EVs", "Correlation Parlays", "Pipeline Status"], 
                           index=0, key="view_select")
    
    # Add refresh button
    col_refresh = st.columns([10, 1, 1])
    with col_refresh[-1]:
        if st.button("🔄 Refresh", help="Refresh data from Google Sheets"):
            st.cache_data.clear()
            st.rerun()
    
    # Last updated info
    st.markdown(f'<p class="sub-header">Last refreshed: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>', 
                unsafe_allow_html=True)
    
    # Main content based on selected view
    if view == "Individual EVs":
        show_individual_evs(dashboard, client)
    elif view == "Correlation Parlays":
        show_correlation_parlays(dashboard, client)
    elif view == "Pipeline Status":
        show_pipeline_status(dashboard, client)

def show_individual_evs(dashboard, client):
    """Display individual EV opportunities"""
    
    with st.spinner("Loading EV opportunities..."):
        ev_df = dashboard.get_ev_opportunities(client)
    
    if ev_df.empty:
        st.warning("No EV opportunities found. Make sure Step 5 (calculate_ev.py) has been run.")
        st.info("💡 Run your pipeline to generate EV data: `python calculate_ev.py`")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Opportunities",
            value=len(ev_df)
        )
    
    with col2:
        if 'Splash_EV_Percentage' in ev_df.columns:
            best_ev = ev_df['Splash_EV_Percentage'].max()
            st.metric(
                label="Best EV",
                value=f"{best_ev:.1%}" if not pd.isna(best_ev) else "N/A"
            )
    
    with col3:
        if 'Num_Books_Used' in ev_df.columns:
            avg_books = ev_df['Num_Books_Used'].mean()
            st.metric(
                label="Avg Books/Prop",
                value=f"{avg_books:.1f}" if not pd.isna(avg_books) else "N/A"
            )
    
    with col4:
        if 'Market' in ev_df.columns:
            unique_markets = ev_df['Market'].nunique()
            st.metric(
                label="Markets Covered",
                value=unique_markets
            )
    
    st.markdown("---")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        if 'Market' in ev_df.columns:
            markets = ['All'] + sorted(ev_df['Market'].unique().tolist())
            selected_market = st.selectbox("Filter by Market", markets)
            if selected_market != 'All':
                ev_df = ev_df[ev_df['Market'] == selected_market]
    
    with col2:
        if 'Splash_EV_Percentage' in ev_df.columns:
            min_ev = st.slider("Minimum EV %", 0.0, 20.0, 0.0, 0.1)
            ev_df = ev_df[ev_df['Splash_EV_Percentage'] >= min_ev/100]
    
    # Display the table
    if not ev_df.empty:
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
        if 'Bet_Type' in display_df.columns:
            display_columns['Bet_Type'] = 'Bet Type'
        if 'Splash_EV_Percentage' in display_df.columns:
            display_columns['Splash_EV_Percentage'] = 'EV %'
        if 'Num_Books_Used' in display_df.columns:
            display_columns['Num_Books_Used'] = 'Books'
        if 'Best_Sportsbook' in display_df.columns:
            display_columns['Best_Sportsbook'] = 'Best Book'
        if 'Best_Odds' in display_df.columns:
            display_columns['Best_Odds'] = 'Best Odds'
        if 'Team' in display_df.columns:
            display_columns['Team'] = 'Team'
        
        # Select only available columns
        available_columns = {k: v for k, v in display_columns.items() if k in display_df.columns}
        display_df = display_df[list(available_columns.keys())].rename(columns=available_columns)
        
        # Format percentage columns
        if 'EV %' in display_df.columns:
            display_df['EV %'] = display_df['EV %'].apply(lambda x: f"{x:.1%}" if pd.notna(x) else "N/A")
        
        # Format odds columns
        if 'Best Odds' in display_df.columns:
            display_df['Best Odds'] = display_df['Best Odds'].apply(lambda x: f"{x:+.0f}" if pd.notna(x) else "N/A")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )
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

def show_correlation_parlays(dashboard, client):
    """Display correlation parlays from compressed single-cell format"""
    
    with st.spinner("Loading correlation parlays..."):
        parlay_df = dashboard.read_sheet_with_metadata_skip(client, "CORRELATION_PARLAYS")
    
    if parlay_df.empty:
        st.warning("No correlation parlays found. Make sure Step 7 (build_parlays.py) has been run.")
        st.info("💡 Run your pipeline to generate parlay data: `python build_parlays.py`")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Parlays",
            value=len(parlay_df)
        )
    
    with col2:
        if 'Estimated_Parlay_EV' in parlay_df.columns:
            best_parlay_ev = pd.to_numeric(parlay_df['Estimated_Parlay_EV'], errors='coerce').max()
            st.metric(
                label="Best Parlay EV",
                value=f"{best_parlay_ev:.1%}" if not pd.isna(best_parlay_ev) else "N/A"
            )
    
    with col3:
        if 'Total_Legs' in parlay_df.columns:
            avg_legs = pd.to_numeric(parlay_df['Total_Legs'], errors='coerce').mean()
            st.metric(
                label="Avg Legs/Parlay",
                value=f"{avg_legs:.1f}" if not pd.isna(avg_legs) else "N/A"
            )
    
    st.markdown("---")
    
    # Find compressed batter columns
    batter_columns = [col for col in parlay_df.columns if col.startswith('Batter_') and col.replace('Batter_', '').isdigit()]
    batter_columns.sort(key=lambda x: int(x.replace('Batter_', '')))  # Sort numerically
    
    # Display each parlay with parsed batter information
    for idx, row in parlay_df.iterrows():
        parlay_id = row.get('Parlay_ID', f'Parlay {idx+1}')
        pitcher_name = row.get('Pitcher_Name', 'Unknown Pitcher')
        pitcher_team = row.get('Pitcher_Team', 'Unknown Team')
        pitcher_market = row.get('Pitcher_Market', 'Unknown Market')
        pitcher_line = row.get('Pitcher_Line', 'N/A')
        pitcher_bet_type = row.get('Pitcher_Bet_Type', 'N/A')
        pitcher_ev = row.get('Pitcher_EV', 0)
        opposing_team = row.get('Opposing_Team', 'Unknown Team')
        num_batters = row.get('Num_Batters', 0)
        correlation_type = row.get('Correlation_Type', 'Unknown')
        estimated_ev = pd.to_numeric(row.get('Estimated_Parlay_EV', 0), errors='coerce')
        total_legs = row.get('Total_Legs', 0)
        correlation_strength = row.get('Correlation_Strength', 'N/A')
        bet_logic = row.get('Bet_Logic', 'N/A')
        
        # Create enhanced parlay card
        with st.container():
            st.markdown(f"""
            <div class="parlay-card">
                <div class="parlay-header">
                    {parlay_id} • {total_legs} Legs • {correlation_type.title()} Correlation
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Pitcher anchor information
                st.write(f"**🎯 Pitcher Anchor:** {pitcher_name} ({pitcher_team})")
                st.write(f"**📊 Prop:** {pitcher_market} {pitcher_line} ({pitcher_bet_type}) - EV: {pitcher_ev:.3f}")
                st.write(f"**⚔️ vs {opposing_team}** ({num_batters} correlated batters)")
                
                # Parse and display compressed batter information
                st.write("**🏏 Correlated Batters:**")
                batters_displayed = 0
                
                for batter_col in batter_columns:
                    if batter_col in row:
                        batter_data = parse_compressed_batter(row[batter_col])
                        
                        if batter_data:
                            st.write(f"   • **{batter_data['name']}** ({opposing_team}) - {batter_data['market']} {batter_data['line']} ({batter_data['bet_type']})")
                            st.write(f"     EV: {batter_data['ev']:.3f} | Best Odds: {batter_data['best_odds']}")
                            batters_displayed += 1
                
                if batters_displayed == 0:
                    st.write("   ⚠️ No batter data found in compressed format")
                    
                    # Show raw data for debugging
                    st.write("**Debug - Available batter columns:**")
                    for batter_col in batter_columns[:3]:  # Show first 3 for debugging
                        if batter_col in row and row[batter_col]:
                            st.write(f"   {batter_col}: {row[batter_col]}")
            
            with col2:
                if estimated_ev > 0:
                    st.markdown(f'<div class="ev-positive">Total EV: {estimated_ev:.1%}</div>', unsafe_allow_html=True)
                else:
                    st.write(f"Total EV: {estimated_ev:.1%}")
                
                # Show correlation details
                st.write(f"**Correlation:** {correlation_strength}")
                st.write(f"**Logic:** {bet_logic}")
        
        st.markdown("---")

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
