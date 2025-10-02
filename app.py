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
        """Read Google Sheets data while skipping metadata headers with enhanced debugging"""
        try:
            spreadsheet = _client.open("MLB_Splash_Data")
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Get all data
            all_data = worksheet.get_all_values()
            
            if not all_data:
                return pd.DataFrame()
            
            print(f"📊 Total rows in {sheet_name}: {len(all_data)}")
            print(f"📋 First 5 rows preview:")
            for i, row in enumerate(all_data[:5]):
                print(f"   Row {i}: {row[:5]}...")  # Show first 5 columns
            
            # Find header row - look for "Parlay_ID" specifically
            header_row_index = -1
            
            for i, row in enumerate(all_data):
                # Check if this row contains "Parlay_ID"
                if any('Parlay_ID' in str(cell) for cell in row):
                    print(f"✅ Found 'Parlay_ID' in row {i}: {row}")
                    header_row_index = i
                    break
            
            if header_row_index == -1:
                # Fallback: look for any header-like indicators
                header_indicators = ['Player', 'Name', 'Market', 'Line', 'Odds', 'Book', 'Team', 'EV', 'Pitcher']
                for i, row in enumerate(all_data):
                    if any(indicator in str(row) for indicator in header_indicators):
                        print(f"🔍 Found header indicators in row {i}: {row}")
                        header_row_index = i
                        break
            
            if header_row_index == -1:
                print("❌ No header row found, using row 0")
                header_row_index = 0
            
            # Extract headers and data
            headers = all_data[header_row_index]
            data_rows = all_data[header_row_index + 1:]
            
            print(f"📋 Using headers from row {header_row_index}: {headers}")
            print(f"📊 Data rows available: {len(data_rows)}")
            
            # Filter out empty rows
            data_rows = [row for row in data_rows if any(cell.strip() if cell else '' for cell in row)]
            
            if not data_rows:
                print("❌ No data rows after filtering")
                return pd.DataFrame()
            
            print(f"📈 Data rows after filtering: {len(data_rows)}")
            print(f"📋 First data row: {data_rows[0]}")
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers)
            df = df.dropna(how='all')
            df = df.loc[:, df.columns != '']
            
            print(f"✅ Final DataFrame: {df.shape}")
            print(f"📋 Final columns: {list(df.columns)}")
            
            return df
            
        except Exception as e:
            print(f"❌ Error reading {sheet_name}: {e}")
            import traceback
            traceback.print_exc()
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
    """Display correlation parlays from compressed single-cell format with enhanced debugging"""
    
    with st.spinner("Loading correlation parlays..."):
        st.write("🔍 **Debug: Starting to read CORRELATION_PARLAYS sheet...**")
        parlay_df = dashboard.read_sheet_with_metadata_skip(client, "CORRELATION_PARLAYS")
        st.write(f"📊 **Read result:** {parlay_df.shape} rows x {len(parlay_df.columns) if not parlay_df.empty else 0} columns")
    
    if parlay_df.empty:
        st.warning("❌ DataFrame is empty after reading")
        st.info("💡 Check Google Sheets permissions and sheet name")
        return
    
    # Show raw DataFrame info for debugging
    with st.expander("🔍 Debug: Raw DataFrame Info"):
        st.write("**Shape:**", parlay_df.shape)
        st.write("**Columns:**", list(parlay_df.columns))
        st.write("**First 5 rows:**")
        st.dataframe(parlay_df.head())
        
        if not parlay_df.empty:
            st.write("**Sample data from first row:**")
            first_row = parlay_df.iloc[0]
            for col, val in first_row.items():
                if val and str(val).strip():
                    st.write(f"   {col}: `{val}`")
    
    # Check if this is an empty status sheet or has parlays
    if 'Parlay_ID' not in parlay_df.columns:
        st.warning("❌ No 'Parlay_ID' column found")
        st.write("**Available columns:**", list(parlay_df.columns))
        
        # This might be a status-only sheet
        st.info("📋 **Treating as Pipeline Status Update**")
        
        # Try to find status information
        status_found = False
        for idx, row in parlay_df.head(10).iterrows():
            row_values = [str(val) for val in row.values if val and str(val).strip()]
            if len(row_values) >= 2:
                st.write(f"**{row_values[0]}:** {row_values[1]}")
                status_found = True
        
        if not status_found:
            st.write("Sheet exists but no clear status found.")
        return
    
    st.write("✅ **Found 'Parlay_ID' column!**")
    
    # Show all data before filtering
    st.write(f"📊 **Before filtering:** {len(parlay_df)} rows")
    
    # Filter out rows that don't have parlay data (metadata rows)
    original_count = len(parlay_df)
    parlay_df = parlay_df[
        (parlay_df['Parlay_ID'].notna()) & 
        (parlay_df['Parlay_ID'].astype(str).str.contains('PARLAY_', na=False))
    ]
    
    st.write(f"📊 **After filtering for PARLAY_ IDs:** {len(parlay_df)} rows (filtered out {original_count - len(parlay_df)})")
    
    if parlay_df.empty:
        st.warning("❌ No rows contain 'PARLAY_' in Parlay_ID")
        st.write("**All Parlay_ID values found:**")
        all_parlay_ids = dashboard.read_sheet_with_metadata_skip(client, "CORRELATION_PARLAYS")['Parlay_ID'].dropna().unique()
        for pid in all_parlay_ids:
            st.write(f"   - `{pid}`")
        return
    
    st.success(f"🎉 **Found {len(parlay_df)} valid parlays!**")
    
    # Show the actual parlay data
    with st.expander("📊 Debug: Parlay Data"):
        st.dataframe(parlay_df)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label="Total Parlays",
            value=len(parlay_df)
        )
    
    with col2:
        if 'Estimated_Parlay_EV' in parlay_df.columns:
            evs = pd.to_numeric(parlay_df['Estimated_Parlay_EV'], errors='coerce')
            best_parlay_ev = evs.max() if not evs.isna().all() else 0
            st.metric(
                label="Best Parlay EV",
                value=f"{best_parlay_ev:.1%}" if best_parlay_ev > 0 else "N/A"
            )
    
    with col3:
        if 'Total_Legs' in parlay_df.columns:
            legs = pd.to_numeric(parlay_df['Total_Legs'], errors='coerce')
            avg_legs = legs.mean() if not legs.isna().all() else 0
            st.metric(
                label="Avg Legs/Parlay",
                value=f"{avg_legs:.1f}" if avg_legs > 0 else "N/A"
            )
    
    st.markdown("---")
    
    # Find compressed batter columns dynamically
    batter_columns = [col for col in parlay_df.columns if 'Batter_' in col]
    st.write(f"🏏 **Found batter columns:** {batter_columns}")
    
    # Display each parlay with parsed batter information
    for idx, row in parlay_df.iterrows():
        parlay_id = row.get('Parlay_ID', f'Parlay {idx+1}')
        pitcher_name = row.get('Pitcher_Name', 'Unknown Pitcher')
        pitcher_team = row.get('Pitcher_Team', 'Unknown Team')
        pitcher_market = row.get('Pitcher_Market', 'Unknown Market')
        pitcher_line = row.get('Pitcher_Line', 'N/A')
        pitcher_bet_type = row.get('Pitcher_Bet_Type', 'N/A')
        
        # Handle pitcher EV
        pitcher_ev_raw = row.get('Pitcher_EV', 0)
        try:
            pitcher_ev = float(pitcher_ev_raw)
        except (ValueError, TypeError):
            pitcher_ev = 0
        
        opposing_team = row.get('Opposing_Team', 'Unknown Team')
        
        # Handle num batters
        num_batters_raw = row.get('Num_Batters', 0)
        try:
            num_batters = int(float(num_batters_raw))
        except (ValueError, TypeError):
            num_batters = 0
        
        correlation_type = row.get('Correlation_Type', 'Unknown')
        
        # Handle estimated EV
        estimated_ev_raw = row.get('Estimated_Parlay_EV', 0)
        try:
            estimated_ev = float(estimated_ev_raw)
        except (ValueError, TypeError):
            estimated_ev = 0
        
        # Handle total legs
        total_legs_raw = row.get('Total_Legs', 0)
        try:
            total_legs = int(float(total_legs_raw))
        except (ValueError, TypeError):
            total_legs = 0
        
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
                    if batter_col in row and row[batter_col]:
                        st.write(f"🔍 **Raw batter data in {batter_col}:** `{row[batter_col]}`")
                        batter_data = parse_compressed_batter(row[batter_col])
                        
                        if batter_data:
                            st.write(f"   • **{batter_data['name']}** ({opposing_team}) - {batter_data['market']} {batter_data['line']} ({batter_data['bet_type']})")
                            st.write(f"     EV: {batter_data['ev']:.3f} | Best Odds: {batter_data['best_odds']}")
                            batters_displayed += 1
                        else:
                            # Show why parsing failed
                            st.write(f"   ❌ Failed to parse: `{row[batter_col]}`")
                
                if batters_displayed == 0:
                    st.write("   ⚠️ No parseable batter data found")
            
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
